"""
market_prep.py
--------------
Preparación del mercado P2P sin programa DR.

En la tesis de Brayan López la demanda es un insumo fijo (datos reales
de la comunidad energética). No se desplazan ni optimizan cargas.

El pipeline se reduce a tres pasos previos al mercado:
  1. Límite de generación G_klim  (Ecuación 1 del modelo base)
     → Protege la viabilidad del mercado ante generadores costosos
  2. Clasificación vendedor / comprador via GDR
  3. Cálculo de generación y demanda netas para el mercado P2P

La demanda D se usa tal cual viene de los datos reales.
"""

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# 1. Límite de generación  (Ecuación 1 del modelo base — sin cambios)
# ─────────────────────────────────────────────────────────────────────────────

def compute_generation_limit(
    G_k:   np.ndarray,   # (N,) generación bruta en el instante k [kW]
    a:     np.ndarray,   # (N,) coef. cuadrático de costo
    b:     np.ndarray,   # (N,) coef. lineal de costo
    c:     np.ndarray,   # (N,) coef. independiente de costo
    pi_gs: float,        # precio de venta de la red $/kWh
) -> np.ndarray:
    """
    Para cada agente n calcula G_klim resolviendo:
        a_n*x^2 + (b_n - pi_gs)*x + c_n = 0  →  raíz positiva máxima

    Reglas (Algoritmo 1 del modelo base):
      costo(G_k) < pi_gs*G_k  →  G_klim = G_k        (sin restricción)
      costo(G_k) >= pi_gs*G_k y G_k >= raíz  →  G_klim = raíz
      costo(G_k) >= pi_gs*G_k y G_k < raíz   →  G_klim = G_k
      sin raíz real positiva                  →  G_klim = 0
    """
    N = len(G_k)
    G_klim = np.zeros(N)

    for n in range(N):
        an, bn, cn, gn = a[n], b[n], c[n], G_k[n]
        cost_gk = an * gn**2 + bn * gn + cn

        if cost_gk < pi_gs * gn:
            G_klim[n] = gn
            continue

        if an == 0.0:
            denom = bn - pi_gs
            root  = -cn / denom if abs(denom) > 1e-12 else gn
        else:
            disc = (bn - pi_gs)**2 - 4.0 * an * cn
            if disc < 0:
                G_klim[n] = 0.0
                continue
            root = (-(bn - pi_gs) + np.sqrt(disc)) / (2.0 * an)
            root = max(root, 0.0)

        G_klim[n] = root if gn >= root else gn

    return G_klim


# ─────────────────────────────────────────────────────────────────────────────
# 2. Clasificación vendedor / comprador via GDR
# ─────────────────────────────────────────────────────────────────────────────

def classify_agents(
    G_klim_k: np.ndarray,   # (N,) límite de generación en instante k
    D_k:      np.ndarray,   # (N,) demanda REAL (fija, sin DR)
) -> tuple[np.ndarray, list, list]:
    """
    GDR_n = G_klim_n / D_n

    Vendedor  (J):  GDR > 1  →  genera más de lo que consume
    Comprador (I):  GDR < 1  →  consume más de lo que genera
    Neutral       :  GDR = 1  →  no participa en el mercado P2P

    Retorna:
        gdr        : (N,)  ratio de generación a demanda
        seller_ids : lista de índices de vendedores
        buyer_ids  : lista de índices de compradores
    """
    D_safe = np.where(D_k < 1e-9, 1e-9, D_k)
    gdr    = G_klim_k / D_safe

    seller_ids = [n for n in range(len(D_k)) if gdr[n] > 1.0]
    buyer_ids  = [n for n in range(len(D_k)) if gdr[n] < 1.0]

    return gdr, seller_ids, buyer_ids


# ─────────────────────────────────────────────────────────────────────────────
# 3. Generación y demanda netas para el mercado P2P
# ─────────────────────────────────────────────────────────────────────────────

def net_quantities(
    G_klim_k:   np.ndarray,   # (N,)
    D_k:        np.ndarray,   # (N,) demanda real fija
    seller_ids: list,
    buyer_ids:  list,
) -> tuple[np.ndarray, np.ndarray]:
    """
    G_net_j = G_klim_j - D_j   (excedente neto del vendedor j)
    D_net_i = D_i  - G_klim_i  (déficit neto del comprador i)

    Retorna:
        G_net : (N,)  positivo solo en vendedores
        D_net : (N,)  positivo solo en compradores
    """
    N = len(D_k)
    G_net = np.zeros(N)
    D_net = np.zeros(N)

    for j in seller_ids:
        G_net[j] = max(0.0, G_klim_k[j] - D_k[j])
    for i in buyer_ids:
        D_net[i] = max(0.0, D_k[i]      - G_klim_k[i])

    return G_net, D_net


# ─────────────────────────────────────────────────────────────────────────────
# 4. Pipeline completo de preparación para un instante k
# ─────────────────────────────────────────────────────────────────────────────

def prepare_hour(
    G_k:   np.ndarray,   # (N,) generación bruta hora k
    D_k:   np.ndarray,   # (N,) demanda real hora k  (fija)
    a:     np.ndarray,
    b:     np.ndarray,
    c:     np.ndarray,
    pi_gs: float,
) -> dict:
    """
    Ejecuta los pasos 1-3 para una hora y retorna todo lo necesario
    para alimentar al motor del mercado P2P.
    """
    G_klim_k             = compute_generation_limit(G_k, a, b, c, pi_gs)
    gdr, seller_ids, buyer_ids = classify_agents(G_klim_k, D_k)
    G_net, D_net         = net_quantities(G_klim_k, D_k, seller_ids, buyer_ids)

    return {
        "G_klim":     G_klim_k,
        "D":          D_k,          # demanda real, sin modificar
        "gdr":        gdr,
        "seller_ids": seller_ids,
        "buyer_ids":  buyer_ids,
        "G_net":      G_net,
        "D_net":      D_net,
    }
