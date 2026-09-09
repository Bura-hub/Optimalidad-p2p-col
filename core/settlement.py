"""
settlement.py  (v3 — SS unificada)
------------------------------------
Liquidación residual y métricas de desempeño.

CORRECCIÓN v3 — Métrica SS unificada (punto 3 de "qué sigue"):
  Versión anterior: SS_P2P = sum(P_star) / G_total
    Solo contaba energía intercambiada en mercado, ignoraba autoconsumo.
  
  Versión nueva: SS = (autoconsumo_local + intercambio_P2P) / G_total
    Alineada con la definición de C1–C4, permite comparación equitativa.
    
  SS_P2P_total(k) = [sum_n min(G_klim_n, D_n) + sum(P_star)] / sum(G_klim)
"""

import numpy as np


def residual_settlement(
    P_star:     np.ndarray,
    G_net_j:    np.ndarray,
    D_net_i:    np.ndarray,
    G_klim_k:   np.ndarray,
    D_star_k:   np.ndarray,
    pi_gs:      float,
    pi_gb:      float,
    seller_ids: list,
    buyer_ids:  list,
    dt:         float = 1.0,
) -> dict:
    """
    `dt` (CAL-46) es la duración del paso en horas. Las cantidades del juego
    son potencia media del paso (kW) y los precios COP/kWh, de modo que la
    energía liquidada es potencia por duración. Este es el sitio donde el
    supuesto de que un paso dura una hora estaba implícito: antes de CAL-46
    el producto se hacía sin factor, y a quince minutos toda cifra monetaria
    habría salido multiplicada por cuatro sin error ni excepción.
    """
    J, I = P_star.shape
    P_ext = np.array([max(0.0, G_net_j[j] - float(np.sum(P_star[j, :])))
                      for j in range(J)])
    P_int = np.array([max(0.0, D_net_i[i] - float(np.sum(P_star[:, i])))
                      for i in range(I)])
    return {
        "P_int":               P_int,
        "P_ext":               P_ext,
        "cost_grid_purchases": float(np.sum(P_int)) * pi_gs * dt,
        "revenue_grid_sales":  float(np.sum(P_ext)) * pi_gb * dt,
    }


def self_consumption_index(P_star, D_k, G_klim_k=None) -> float:
    """
    SC = (autoconsumo_local + intercambio_P2P) / D_total
    Si G_klim_k se provee, incluye el autoconsumo local de cada nodo.
    """
    p2p_energy = float(np.sum(P_star))
    if G_klim_k is not None:
        N = len(G_klim_k)
        D_arr = D_k if hasattr(D_k, '__len__') else np.array([D_k])
        G_arr = G_klim_k
        autoconsumo = float(np.sum(np.minimum(
            np.maximum(G_arr, 0), np.maximum(D_arr, 0))))
        numerator = autoconsumo + p2p_energy
    else:
        numerator = p2p_energy
    denom = float(np.sum(np.maximum(D_k, 0)))
    return numerator / denom if denom > 1e-10 else 0.0


def self_sufficiency_index(P_star, G_klim_k, D_k=None) -> float:
    """
    SS = (autoconsumo_local + intercambio_P2P) / G_total
    Incluye autoconsumo para ser comparable con C1–C4 (punto 3).
    """
    p2p_energy = float(np.sum(P_star))
    G_arr = np.maximum(G_klim_k, 0)

    if D_k is not None:
        D_arr = np.maximum(D_k if hasattr(D_k,'__len__') else np.array([D_k]), 0)
        autoconsumo = float(np.sum(np.minimum(G_arr, D_arr)))
        numerator   = autoconsumo + p2p_energy
    else:
        numerator = p2p_energy

    denom = float(np.sum(G_arr))
    return numerator / denom if denom > 1e-10 else 0.0


def compute_savings(P_star, pi_star, pi_gs, pi_gb, dt: float = 1.0):
    """`dt` (CAL-46): duración del paso en horas. Ver `residual_settlement`.

    CAL-47: las dos cotas admiten **escalar o vector**. El techo se indexa
    por comprador, porque es lo que cada comprador paga a la red; el piso se
    indexa por vendedor, porque es lo que la red le paga a cada vendedor por
    inyectar, y bajo la Resolución CREG 174 eso depende de si su inyección
    acumulada del mes ya superó su retiro. Con escalares el resultado es
    idéntico bit a bit al histórico.
    """
    I = len(pi_star); J = P_star.shape[0]
    gs = np.broadcast_to(np.asarray(pi_gs, dtype=float), (I,))
    gb = np.broadcast_to(np.asarray(pi_gb, dtype=float), (J,))
    S_i  = np.array([(gs[i] - pi_star[i]) * float(np.sum(P_star[:, i]))
                     for i in range(I)])
    SR_j = np.array([float(np.sum((pi_star - gb[j]) * P_star[j, :]))
                     for j in range(J)])
    if dt != 1.0:
        S_i = S_i * dt
        SR_j = SR_j * dt
    return S_i, SR_j


def bienestar_cuasilineal(S_i, SR_j) -> float:
    """El bienestar de la comunidad, bien planteado (H-61).

    Es la suma del ahorro de los compradores y la prima de los vendedores, es
    decir **el excedente**, que este proyecto ya calculaba sin llamarlo por su
    nombre. Vale la pena escribir por que ES un bienestar y no una cifra
    contable.

    QUE ES. Para el par (j, i) que intercambia un kilovatio hora al precio pi:

        ahorro del comprador   (techo_i - pi)      lo que deja de pagarle a la red
        prima del vendedor     (pi - piso_j)       lo que cobra de mas que la red
        suma                   (techo_i - piso_j)  el ANCHO DE LA BANDA

    El precio **se cancela**, porque es una transferencia entre dos miembros de
    la misma comunidad. Es la identidad de H-33.

    POR QUE ES EL BIENESTAR CORRECTO. La forma cuasilineal `U(q) - pi*q` es la
    que hace que la suma de bienestares sea un excedente bien definido: las
    transferencias se cancelan y queda utilidad menos costo. Y esta suma **es
    exactamente esa forma**, con la disposicion a pagar del comprador igual a
    **su techo**, que es su alternativa de red, y el costo de oportunidad del
    vendedor igual a **su piso**, que es la suya.

    Es la formulacion de las fuentes que el propio modelo base cita para su
    utilidad cuadratica, y la unica de las tres que **sube al transar**.

    POR QUE NO SIRVEN LAS DOS DE LA AUTORA (H-58, H-59, H-61). La publicada no
    tiene el dinero dentro: su termino de pago se cancela entre los dos lados y
    solo quedan costos crecientes, de modo que se maximiza sin transar. La
    extensa crea o destruye dinero, porque el vendedor cobra precio por energia
    y el comprador paga el piso por el logaritmo del precio, que no es la misma
    cantidad. Y el logaritmo de un precio **no es dimensionalmente admisible**:
    el modelo daria equilibrios distintos corrido en pesos o en dolares.

    Las dos se conservan en `replicator_sellers` y `replicator_buyers` porque
    reproducen el caso publicado y sostienen la prueba de fidelidad. Para
    **comparar algoritmos entre si**, que es lo que la autora hace, sirven: el
    sesgo es el mismo en todas las columnas. Para responder si a la comunidad
    le conviene el mercado, que es lo que esta tesis pregunta, no.
    """
    return float(np.sum(S_i) + np.sum(SR_j))


def equity_index(S_i, SR_j) -> float:
    num   = float(np.sum(S_i) - np.sum(SR_j))
    denom = float(np.sum(S_i) + np.sum(SR_j))
    return num / denom if abs(denom) > 1e-12 else 0.0


def welfare_distribution(S_i, SR_j) -> dict:
    total = float(np.sum(S_i) + np.sum(SR_j))
    if total < 1e-12:
        return {"PS": 50.0, "PSR": 50.0}
    return {"PS":  100.0 * float(np.sum(S_i))  / total,
            "PSR": 100.0 * float(np.sum(SR_j)) / total}


def compute_net_benefit(savings: np.ndarray, revenues: np.ndarray) -> np.ndarray:
    """
    Filosofía A: ganancia_neta = savings + revenues.

    Definición validada por asesor Pantoja (reunión WEEF,
    Documentos/conversacion_WEEF.txt, min 22-26):
        ganancia_neta = costo_línea_base − costo_con_sistema

    El costo residual de compra a la red NO se resta porque el agente
    incurriría en él igual sin participar en el mercado.
    """
    return np.asarray(savings, dtype=float) + np.asarray(revenues, dtype=float)


def gini_index(values: np.ndarray) -> float:
    """
    Coeficiente de Gini sobre beneficios netos por agente.

    Mide la desigualdad en la distribución del beneficio económico
    entre los N agentes de la comunidad energética.

    Rango: [0, 1]
      0 → distribución perfectamente igualitaria (todos ganan lo mismo)
      1 → máxima desigualdad (un agente captura todo el beneficio)

    Referencia: propuesta de tesis §VI.C, Nivel 2 — Equidad.
    Se evalúa sobre valores absolutos para capturar dispersión incluyendo
    agentes con beneficio cero (consumidores puros sin PV).

    Parámetro
    ---------
    values : (N,)  beneficio neto por agente [$/período]
    """
    v = np.abs(np.asarray(values, dtype=float))
    v = np.sort(v)
    n = len(v)
    if n == 0 or np.sum(v) < 1e-12:
        return 0.0
    # Fórmula: G = (2 Σ i·v_i) / (n Σ v_i) − (n+1)/n
    idx  = np.arange(1, n + 1)
    gini = (2.0 * np.dot(idx, v)) / (n * np.sum(v)) - (n + 1.0) / n
    return float(np.clip(gini, 0.0, 1.0))
