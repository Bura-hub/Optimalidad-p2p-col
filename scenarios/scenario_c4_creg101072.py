"""
scenario_c4_creg101072.py
-------------------------
Escenario C4: Autogeneración Colectiva (AGRC)
Resolución CREG 101 072 de 2025 + Decreto 2236 de 2023

Este es el escenario más relevante para la tesis: representa la
alternativa regulatoria vigente contra la cual se compara el mercado
P2P dinámico.

Mecanismo - Porcentaje de Distribución de Excedentes (PDE):
  - Los excedentes de generación de la comunidad se distribuyen
    administrativamente entre los miembros según ponderadores PDE_n.
  - La distribución es ESTÁTICA: no responde a preferencias individuales
    ni a condiciones de oferta/demanda en tiempo real.
  - El PDE es un PORCENTAJE DE REPARTO ACORDADO entre los miembros que
    debe sumar 100 % (art. 19). NO es una cuota de demanda ni de
    capacidad: confundirlo con ellas es el error que corrigió CAL-41.

Marco regulatorio (CAL-15, 2026-05-01; renumeración corregida CAL-31,
2026-05-03; Caso aplicable corregido CAL-41, 2026-08-06):
  El Decreto 2236/2023 art. 4 y la CREG 101 072/2025 art. 19 (PDE) +
  art. 20 establecen que cada miembro AGRC se liquida bajo el régimen de
  Generador Distribuido y AGPE. Por linealidad regulatoria C4 hereda
  CREG 174/2021 art. 25, y CUÁL de sus dos numerales aplica lo decide el
  art. 20 (texto vigente tras el art. 13 de la CREG 101-087/2025):

    Caso 1 (num. 1) — exige las TRES condiciones:
        i.   fuentes FNCER y suma de capacidades <= límite AGPE (UPME 281)
        ii.  capacidad instalada POR USUARIO <= 100 kW
        iii. PDE < 10 % PARA CADA UNO de los usuarios
      => permuta liquidada a (pi_gs - Cvm,i,j)          [art. 25 num. 1]

    Caso 2 (num. 2) — si la capacidad por usuario > 100 kW O el PDE de
      ALGÚN usuario >= 10 %:
      => permuta a (pi_gs - (T + D + Cvm + PR + Rm))    [art. 25 num. 2]

    Exportación residual (Tipo 2) → pi_bolsa[k] horario, en ambos casos.

  CONSECUENCIA ARITMÉTICA (CAL-41): como sum(PDE) = 100 % por el art. 19,
  exigir PDE < 10 % para cada uno de U usuarios obliga a U >= 11. Una
  comunidad de cinco fronteras comerciales —la composición MTE— NO PUEDE
  estar en el Caso 1 bajo ningún reparto acordado. `resolve_caso_art20`
  deriva el Caso en vez de fijarlo, para que el motor sea correcto en
  cualquier composición.

ALCANCE — Art. 13 CREG 101 072 (Informe 4 MTE, Fajardo 2026-05-27):
  El Art. 13 de la 101 072 pospone a resolución aparte la metodología
  para el traslado del costo de compras de los AC/GDC a la tarifa
  regulada (componente G del CU). El crédito PDE que este módulo modela
  (arts. 19-21, por remisión a los arts. 25-26 de la CREG 174) SÍ está
  plenamente definido; lo pendiente es el canal tarifario del
  comercializador. Por tanto el `net_benefit` de C4 debe leerse como
  **benchmark bajo el supuesto de herencia CREG 174 (CAL-15)**, cuya
  materialización plena en factura está supeditada a la reglamentación
  del Art. 13. Ver auditoría Capa 2.6 y Capa 5.

El modo horario (mode="creg174_inheritance") queda como opción no
normativa que el orquestador ya no invoca (D4); el modo que rige es
`monthly_hx` (arts. 19 a 21, cruce Hx del Anexo 4 por agente, ver
`_run_c4_monthly_hx`).

Referencia regulatoria (numeración verificada 2026-05-03 vs gestornormativo.creg.gov.co):
    Decreto 2236 de 2023 art. 4 (marco AGRC, hereda AGPE).
    Resolución CREG 101 072 de 2025 art. 19 (PDE) + art. 20 caso 1
        (capacidad ≤ 100 kW). Modificada por CREG 101-087/2025 art. 13
        (caso 4 amplía a no-FNCER, no aplica a MTE solar).
    Resolución CREG 174 de 2021 art. 25 (créditos energía + valoración
        horaria del residual; "Tipo 1/Tipo 2/Hx" son denominaciones
        didácticas del sector, no cita literal CREG).
    Resolución CREG 119 de 2007 art. 11 (definición Cvm,i,j; modificada
        por CREG 101 028/2023).
    Resolución CREG 101 066 de 2024 art. 3 (PES referencial mensual,
        aplicado horario via min(pi_bolsa[k], PES_mes) — CAL-14).

Historico:
    Pre-CAL-15: créditos PDE valorados a pi_gs completo, sin distinción
    Tipo 1 / Tipo 2, modo `pde_only` por defecto silenciaba la
    exportación a bolsa. CAL-15 (2026-05-01) corrige a la lectura
    legalmente consistente.

Actividad 2.2.
"""

import warnings as _warnings
import numpy as np
from typing import Literal, Optional, Union

from ._pi_gs import as_pi_gs_array, as_component_c_array
from core.opciones_externas import reparto_anexo4


def validate_pde(
    pde: np.ndarray,
    tol: float = 1e-6,
) -> bool:
    """Verifica que los PDE sumen 1 y sean no negativos."""
    return bool(np.all(pde >= 0) and abs(np.sum(pde) - 1.0) < tol)


def compute_pde_weights(
    metric: np.ndarray,       # (N,) métrica de ponderación según method
    method: str = "capacity_proportional",
) -> np.ndarray:
    """
    Calcula los ponderadores PDE.

    Métodos disponibles:
        'capacity_proportional'    : PDE_n = cap_n / sum(cap)  (default, CREG 101 072 art. 19)
            metric esperada: capacidad instalada en kW.
        'equal'                    : PDE_n = 1/N
            metric ignorada (se usa solo para tamaño N).
        'excedentes_proportional'  : PDE_n = exc_n / sum(exc)  (CAL-26, opt-in)
            metric esperada: excedentes acumulados en kWh
            (use ``compute_excedentes_acumulados(G, D)`` para construirlos).

    Fallback: si ``sum(metric) <= 0`` (e.g., comunidad sin generación),
    devuelve PDE uniforme 1/N en todos los métodos proporcionales.

    En la práctica, la CREG 101 072 art. 19 permite ponderadores acordados
    entre miembros; los listados aquí son referencias.

    CAL-26 (ADR-0026): ``excedentes_proportional`` es opt-in. El default
    sigue siendo ``capacity_proportional``. Para el paper IEEE WEEF se
    reportan ambos lado a lado como sensibilidad de robustez.
    """
    if method == "capacity_proportional" or method == "excedentes_proportional":
        total = float(np.sum(metric))
        if total < 1e-10:
            return np.ones(len(metric)) / len(metric)
        return np.asarray(metric, dtype=float) / total
    elif method == "equal":
        N = len(metric)
        return np.ones(N) / N
    else:
        raise ValueError(
            f"Método PDE desconocido: {method!r}. "
            f"Use 'capacity_proportional' (default), 'equal' "
            f"o 'excedentes_proportional' (CAL-26 opt-in)."
        )


# CAL-41: límite de potencia para ser AGPE, Resolución UPME 281 de 2015.
# Lo invocan el art. 20 num. 1 i y num. 2 i de la CREG 101 072 como cota a
# la SUMA de capacidades del AC. Por encima aplica el Caso 3 (reglas de las
# CREG 024/2015 y 096/2019), que este módulo no implementa.
AGPE_LIMIT_KW = 1000.0


def resolve_caso_art20(
    pde: np.ndarray,
    capacity: Optional[np.ndarray] = None,
    max_capacity_kw: float = 100.0,
    pde_limit: float = 0.10,
) -> int:
    """
    Decide si un AC cae en el Caso 1 o en el Caso 2 del art. 20 de la
    CREG 101 072/2025 (texto vigente tras el art. 13 de la 101-087/2025).

    CAL-41 (ADR-0041). Literal de la norma:

      num. 1 iii — "El Porcentaje de Distribución de Excedentes [...] sea
        inferior al 10% para cada uno de los usuarios del AC."
      num. 2 ii  — "La Capacidad Instalada por Usuario [...] sea mayor a
        100 kW o el Porcentaje de Distribución de Excedentes [...] sea
        superior o igual al 10% para algún usuario del AC."

    El PDE es la condición dominante y no admite ambigüedad: como el
    art. 19 obliga a que sume 100 %, `max(pde) >= 0.10` determina el
    Caso 2 por sí solo, sea cual sea la capacidad. La condición de
    capacidad solo puede empujar hacia el Caso 2, nunca hacia el Caso 1.

    Parámetros
    ----------
    pde : (N,) fracciones que suman 1.0.
    capacity : (N,) capacidad instalada POR USUARIO en kW. Si el llamador
        pasa un proxy (p. ej. generación media) la prueba de capacidad
        queda del lado permisivo; el PDE sigue siendo determinante.
        `None` omite esa prueba.
    max_capacity_kw : límite por usuario del num. 1 ii.
    pde_limit : umbral del num. 1 iii.

    Retorna
    -------
    1 o 2 — el numeral del art. 25 de la CREG 174/2021 que aplica.
    """
    pde_arr = np.asarray(pde, dtype=float)
    if float(np.max(pde_arr)) >= pde_limit:
        return 2
    if capacity is not None:
        cap = np.asarray(capacity, dtype=float)
        if cap.size and float(np.max(cap)) > max_capacity_kw:
            return 2
    return 1


def compute_excedentes_acumulados(
    G: np.ndarray,    # (N, T) generación bruta [kWh]
    D: np.ndarray,    # (N, T) demanda [kWh]
) -> np.ndarray:
    """
    Computa el vector (N,) de excedentes brutos acumulados por agente
    sobre toda la ventana de tiempo:

        exc_n = sum_t max(G_n(t) - D_n(t), 0)

    Útil como ``metric`` para
    ``compute_pde_weights(metric, method="excedentes_proportional")``
    según CAL-26 (ADR-0026).

    Devuelve (N,) en kWh.
    """
    G = np.asarray(G, dtype=float)
    D = np.asarray(D, dtype=float)
    if G.shape != D.shape:
        raise ValueError(
            f"G shape {G.shape} != D shape {D.shape}"
        )
    surplus = np.maximum(G - D, 0.0)
    return surplus.sum(axis=1)


def pde_por_regla(regla: str, G: np.ndarray, D: np.ndarray,
                  month_labels: Optional[np.ndarray] = None) -> dict:
    """Porcentaje de distribucion de cada mes segun una regla (spec 4.6, D5).

    El articulo 19 de la Resolucion CREG 101 072 deja el porcentaje a lo que
    acuerden los miembros, con suma cien y cambiable cada mes. La base es el
    reparto igual; estas son las alternativas del analisis:

      igual       un N-esimo a cada una.
      consumo     la demanda del mes.
      aporte      el excedente del mes; un mes sin excedente cae al igual.
      generacion  la generacion media medida del horizonte, constante.

    Devuelve {etiqueta de mes como int: (N,)}; sin etiquetas, la clave es 0.
    """
    G = np.maximum(np.asarray(G, dtype=float), 0.0)
    D = np.maximum(np.asarray(D, dtype=float), 0.0)
    N, T = G.shape
    etiquetas = (np.zeros(T, dtype=int) if month_labels is None
                 else np.asarray(month_labels))
    gen = G.mean(axis=1)
    out = {}
    for mes in np.unique(etiquetas):
        idx = np.flatnonzero(etiquetas == mes)
        if regla == "igual":
            out[int(mes)] = compute_pde_weights(np.ones(N), method="equal")
            continue
        if regla == "consumo":
            m = D[:, idx].sum(axis=1)
        elif regla == "aporte":
            m = np.maximum(G[:, idx] - D[:, idx], 0.0).sum(axis=1)
        elif regla == "generacion":
            m = gen
        else:
            raise ValueError(f"regla de porcentaje desconocida: {regla!r}")
        out[int(mes)] = compute_pde_weights(m, method="excedentes_proportional")
    return out


def run_c4_creg101072(
    D: np.ndarray,              # (N, T) demanda [kWh]
    G: np.ndarray,              # (N, T) generación bruta [kWh]
    pi_gs: Union[float, np.ndarray],  # escalar, (N,) o (N, T) — CAL-9
    pi_bolsa: np.ndarray,       # (T,) precio de bolsa $/kWh
    pde: np.ndarray,            # (N,) Porcentaje de Distribución de Excedentes
    capacity: Optional[np.ndarray] = None,    # (N,) kW instalados (validación)
    max_capacity_kw: float = 100.0,           # límite por usuario, art. 20 num. 1 ii
    component_c: Union[str, float, np.ndarray, None] = "auto",  # CAL-15
    mode: Literal[
        "creg174_inheritance", "monthly_hx",
        "pde_only", "pde_plus_residual_export",
    ] = "creg174_inheritance",
    month_labels: Optional[np.ndarray] = None,  # (T,) etiqueta período YYYYMM (CAL-27)
    tolls: Union[float, np.ndarray, None] = None,   # CAL-41: T+D+PR+Rm
    caso: Union[int, str] = "auto",                 # CAL-41: 1, 2 o "auto"
    # CAL-46: duración del paso en horas. Las matrices llevan potencia media
    # del paso (kW) y los precios COP/kWh. La prueba del artículo 20 compara
    # capacidad instalada y porcentajes, de modo que es invariante al paso.
    dt: float = 1.0,
    # C-178: porcentaje distinto en cada mes (art. 19). Solo en modo mensual.
    pde_mensual: Optional[dict] = None,
) -> dict:
    """
    Simula el esquema AGRC (CREG 101 072) con distribución PDE.

    Parámetros nuevos en CAL-15 (2026-05-01):
      component_c : igual contrato que C1 (`scenarios._pi_gs.as_component_c_array`):
        - "auto" (default): pi_C = pi_gs * C_FRACTION (~13.85 %)
        - None / 0.0       : sin descuento (legacy pre-CAL-15)
        - float            : COP/kWh fijo
        - ndarray (N,)/(T,)/(N,T) : per-agente / temporal / completo

    Parámetros nuevos en CAL-41 (2026-08-06):
      tolls : peajes regulados T + D + PR + Rm en COP/kWh, mismo contrato
        de forma que `component_c`. Solo se usan si el Caso resuelto es el 2
        (art. 25 num. 2, que cobra el agregado T+D+Cvm+PR+Rm sobre la
        permuta, y no solo Cvm). `data.cedenar_tariff.tolls_per_agent_hourly`
        los entrega como matriz (N, T).
      caso : 1, 2 o "auto" (default). Con "auto" se deriva del art. 20 vía
        `resolve_caso_art20(pde, capacity, max_capacity_kw)`. Fijarlo a mano
        solo tiene sentido para contrafácticos declarados.

      Si el Caso resuelto es el 2 y no se pasan `tolls`, la permuta queda
      liquidada como en el Caso 1 —lo que SOBRESTIMA el beneficio de C4— y
      se emite un UserWarning nombrando esa consecuencia. El pipeline
      canónico siempre pasa los peajes.

    El dict retornado incluye `caso_art20` con el numeral aplicado y
    `tolls_aplicados` (bool), para que la trazabilidad no dependa del
    llamador.

    Modos:
      creg174_inheritance (default, CAL-15):
        Algoritmo Tipo 1 / Tipo 2 hora a hora derivado de Decreto 2236
        + CREG 101 072 + CREG 174 art. 25. Permuta intracomunitaria a
        (pi_gs - Cvm); excedente residual a pi_bolsa[k] horario.

      pde_only (DEPRECATED desde CAL-15):
        Comportamiento pre-CAL-15: créditos a pi_gs completo, sin
        exportación residual. Conservado para regression-test y
        comparación histórica. Emite DeprecationWarning.

      pde_plus_residual_export (DEPRECATED desde CAL-15):
        Comportamiento pre-CAL-15 con exportación residual a bolsa
        agregada (no per-agente). Subsumido por
        creg174_inheritance que es per-agente y por hora.
    """
    if mode in ("pde_only", "pde_plus_residual_export"):
        _warnings.warn(
            f"C4: mode='{mode}' es legacy pre-CAL-15. "
            "Use mode='creg174_inheritance' (default) que aplica "
            "CREG 174 art. 25 sobre permuta intracomunitaria. "
            "Ver docs/adr/0015-cal15-c4-creg101072-tipo-1-2-cvm.md",
            DeprecationWarning,
            stacklevel=2,
        )
        return _run_c4_legacy(
            D, G, pi_gs, pi_bolsa, pde, capacity,
            max_capacity_kw, mode, dt=dt,
        )

    # ── CAL-41: resolver el Caso del art. 20 y plegar los peajes ─────────
    # Se pliegan aquí, una sola vez, y las tres implementaciones reciben la
    # deducción ya completa: `as_component_c_array` deja pasar una (N, T)
    # tal cual, de modo que ninguna de ellas necesita cambiar.
    if pde_mensual is not None and mode != "monthly_hx":
        raise ValueError("pde_mensual solo tiene sentido en mode='monthly_hx'")
    # Con un porcentaje por mes, el caso se resuelve con el mayor porcentaje
    # que tuvo cada miembro en el horizonte: si algun mes alguno llega al 10 %,
    # la comunidad esta en el caso 2 ese mes, y se declara para todo el
    # horizonte. Con cinco miembros no cambia nada: siempre es el caso 2.
    pde_caso = (pde if pde_mensual is None
                else np.max(np.vstack(list(pde_mensual.values())), axis=0))
    caso_res = (resolve_caso_art20(pde_caso, capacity, max_capacity_kw)
                if caso == "auto" else int(caso))
    if caso_res not in (1, 2):
        raise ValueError(f"caso debe ser 1, 2 o 'auto'; se recibió {caso!r}")

    N_, T_ = D.shape
    ded = as_component_c_array(component_c, as_pi_gs_array(pi_gs, N_, T_), N_, T_)
    tolls_aplicados = False
    if caso_res == 2:
        if tolls is None:
            _warnings.warn(
                "C4: el art. 20 num. 2 aplica a esta comunidad (PDE >= 10 % "
                "en algún usuario o capacidad por usuario > 100 kW), pero no "
                "se pasaron `tolls`. La permuta queda liquidada solo con Cvm, "
                "como en el Caso 1, lo que SOBRESTIMA el beneficio de C4. "
                "Ver docs/adr/0041-cal41-c4-caso2-art20.md",
                UserWarning,
                stacklevel=2,
            )
        else:
            ded = ded + as_component_c_array(
                tolls, as_pi_gs_array(pi_gs, N_, T_), N_, T_)
            tolls_aplicados = True

    if mode == "monthly_hx":
        # CAL-27 (ADR-0027): agregación mensual + cruce Hx por agente.
        res = _run_c4_monthly_hx(
            D, G, pi_gs, pi_bolsa, pde, capacity,
            max_capacity_kw, ded, month_labels, dt=dt,
            pde_mensual=pde_mensual,
        )
    else:
        res = _run_c4_creg174_inheritance(
            D, G, pi_gs, pi_bolsa, pde, capacity,
            max_capacity_kw, ded, dt=dt,
        )

    res["caso_art20"] = caso_res
    res["tolls_aplicados"] = tolls_aplicados
    return res


def _validate_capacity(
    capacity: Optional[np.ndarray],
    max_capacity_kw: float,
) -> None:
    """
    Validaciones regulatorias del art. 20 de la CREG 101 072.

    CAL-41 corrige a qué se aplica cada límite. El art. 20 impone DOS
    cotas distintas y la versión previa las confundía en una sola:

      num. 1 i  / num. 2 i  — la SUMA de capacidades <= límite AGPE de la
        Resolución UPME 281 de 2015 (1 MW).
      num. 1 ii / num. 2 ii — la capacidad POR USUARIO frente a los 100 kW,
        que no es una prohibición sino el criterio que separa el Caso 1 del
        Caso 2. Superarlo NO invalida el AC: lo manda al Caso 2, y de eso
        se encarga `resolve_caso_art20`.

    Antes de CAL-41 esta función abortaba si la suma superaba 100 kW, lo
    que habría rechazado como inválida a una comunidad perfectamente legal
    de, por ejemplo, doce miembros de 20 kW.
    """
    if capacity is None:
        return
    total_cap = float(np.sum(capacity))
    if total_cap > AGPE_LIMIT_KW:
        raise ValueError(
            f"Capacidad total {total_cap:.1f} kW excede el límite AGPE de "
            f"{AGPE_LIMIT_KW:.0f} kW (UPME 281/2015; art. 20 num. 1 i). "
            "Por encima de ese límite aplica el Caso 3 del art. 20, que "
            "este módulo no implementa."
        )
    pos_cap = capacity[capacity > 0]
    if len(pos_cap) > 1:
        ratio = float(np.max(pos_cap)) / float(np.min(pos_cap))
        if ratio > 10.0:
            _warnings.warn(
                f"C4: relación capacidad máx/mín = {ratio:.1f}× > 10×. "
                "Verificar restricción de composición CREG 101 072.",
                UserWarning,
                stacklevel=3,
            )


def _run_c4_creg174_inheritance(
    D, G, pi_gs, pi_bolsa, pde, capacity,
    max_capacity_kw, component_c, dt=1.0,
):
    """Implementación CAL-15: Tipo 1 a (pi_gs-Cvm), Tipo 2 a pi_bolsa."""
    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)
    pi_C    = as_component_c_array(component_c, pi_gs_v, N, T)

    if not validate_pde(pde):
        raise ValueError(f"PDE inválido: debe sumar 1.0, suma={np.sum(pde):.4f}")

    _validate_capacity(capacity, max_capacity_kw)
    _warnings.warn(
        "C4: se asume un único comercializador de respaldo. "
        "Verificar con admin MTE antes de publicar.",
        UserWarning,
        stacklevel=3,
    )

    # Flujos individuales hora a hora.
    G_pos       = np.maximum(G, 0.0)
    D_pos       = np.maximum(D, 0.0)
    autoconsumo = np.minimum(G_pos, D_pos)              # (N, T)
    surplus_ind = np.maximum(G_pos - D_pos, 0.0)        # (N, T) al pool
    deficit_ind = np.maximum(D_pos - G_pos, 0.0)        # (N, T) de la red

    # Inyección comunitaria total: lo que cruza la frontera comunitaria.
    # CAL-15: se distribuye vía PDE como dato BRUTO (no neto), porque
    # ese es el monto que el comercializador ve en el medidor de la
    # planta colectiva (Decreto 2236/2023 art. 4).
    inyeccion_total = surplus_ind.sum(axis=0)           # (T,)

    # Crédito PDE administrativo per agente.
    credit = pde[:, None] * inyeccion_total[None, :]    # (N, T)

    # Tipo 1 / Tipo 2 / compra residual a la red.
    permuta_t1   = np.minimum(credit, deficit_ind)              # (N, T)
    excedente_t2 = np.maximum(credit - deficit_ind, 0.0)        # (N, T)
    grid_buy     = np.maximum(deficit_ind - credit, 0.0)        # (N, T)

    # Valoración (CAL-10b.2 inheritance: solo Cvm,i,j en permuta).
    savings   = (autoconsumo  * pi_gs_v).sum(axis=1)            # (N,)
    pde_t1    = (permuta_t1   * (pi_gs_v - pi_C)).sum(axis=1)   # (N,)
    surplus   = (excedente_t2 * pi_bolsa[None, :]).sum(axis=1)  # (N,)
    grid_cost = (grid_buy     * pi_gs_v).sum(axis=1)            # (N,)

    # C-165: el beneficio a la hora que lo genera, con los mismos factores
    # antes de sumar por filas. Aqui es exacto porque toda la valoracion de
    # esta rama es horaria.
    neto_horario = (autoconsumo * pi_gs_v
                    + permuta_t1 * (pi_gs_v - pi_C)
                    + excedente_t2 * pi_bolsa[None, :])

    # CAL-46: de potencia a energía.
    if dt != 1.0:
        neto_horario = neto_horario * dt
        savings = savings * dt
        pde_t1 = pde_t1 * dt
        surplus = surplus * dt
        grid_cost = grid_cost * dt

    net_benefit = savings + pde_t1 + surplus

    # Diagnóstico horario agregado (compatibilidad con código existente).
    hourly_community_surplus = np.maximum(
        inyeccion_total - deficit_ind.sum(axis=0), 0.0)         # neto a bolsa
    hourly_distribution      = credit                           # (N, T)

    results_per_agent = {}
    for n in range(N):
        results_per_agent[n] = {
            "savings":         float(savings[n]),
            "pde_credits":     float(pde_t1[n]),
            "surplus_revenue": float(surplus[n]),
            "grid_cost":       float(grid_cost[n]),
            "net_benefit":     float(net_benefit[n]),
            "pde_weight":      float(pde[n]),
        }

    # C-165: matriz (N, T); su suma por filas es el beneficio por agente.
    # Aqui es exacta porque la valoracion de esta rama es horaria en sus tres
    # componentes.
    return {
        "per_agent": results_per_agent,
        "neto_horario": neto_horario,
        "aggregate": {
            "total_savings":         float(savings.sum()),
            "total_pde_credits":     float(pde_t1.sum()),
            "total_surplus_revenue": float(surplus.sum()),
            "total_grid_cost":       float(grid_cost.sum()),
            "total_net_benefit":     float(net_benefit.sum()),
        },
        "hourly": {
            "community_surplus":    hourly_community_surplus,
            "pde_distribution":     hourly_distribution,
            "inyeccion_total":      inyeccion_total,
            "permuta_t1":           permuta_t1,
            "excedente_t2":         excedente_t2,
            "grid_buy":             grid_buy,
        },
        "regulatory": {
            "pde_weights":          pde,
            "static_mechanism":     True,
            "creg174_inheritance":  True,         # CAL-15
        },
        "params": {
            "mode":            "creg174_inheritance",
            "max_capacity_kw": max_capacity_kw,
        },
    }


def _run_c4_monthly_hx(
    D, G, pi_gs, pi_bolsa, pde, capacity,
    max_capacity_kw, component_c, month_labels, dt=1.0, pde_mensual=None,
):
    """
    El colectivo liquidado como lo manda la norma (CAL-27, C-178).

    Articulos 19 a 21 de la Resolucion CREG 101 072: cada mes el fondo comun
    es la inyeccion de todos, y a cada miembro le corresponde su porcentaje.
    Esa asignacion se clasifica como la de un autogenerador (art. 25 de la
    CREG 174): credito hasta igualar la importacion del mes del miembro, y lo
    que la supera a la bolsa de cada hora desde el corte hx del Anexo 4.

    Supuesto declarado: la norma asigna con cantidades mensuales y el Anexo 4
    pide horas. El perfil horario de la asignacion de cada miembro es su
    porcentaje por la inyeccion horaria del colectivo. Antes (CAL-27) el
    exceso se valoraba a la media mensual de la bolsa, lo que lo sobrevaloraba
    un 12,5 % en la frontera secundaria (H-73).

    Devuelve tambien `neto_horario` (N, T): autoconsumo a la tarifa de su
    hora, credito a la tarifa media del mes menos la deduccion media, y
    exceso a la bolsa de su hora. Su suma por filas es el total por agente.
    """
    from collections import defaultdict

    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)
    pi_C    = as_component_c_array(component_c, pi_gs_v, N, T)
    pb      = np.asarray(pi_bolsa, dtype=float).reshape(-1)

    _validate_capacity(capacity, max_capacity_kw)
    _warnings.warn(
        "C4: se asume un único comercializador de respaldo. "
        "Verificar con admin MTE antes de publicar.",
        UserWarning,
        stacklevel=3,
    )

    if month_labels is None:
        period_hours: dict[int, list[int]] = {0: list(range(T))}
    else:
        period_hours = defaultdict(list)
        for k, m in enumerate(month_labels):
            period_hours[int(m)].append(k)

    G_pos       = np.maximum(G, 0.0)
    D_pos       = np.maximum(D, 0.0)
    autoconsumo = np.minimum(G_pos, D_pos)
    surplus_ind = np.maximum(G_pos - D_pos, 0.0)
    deficit_ind = np.maximum(D_pos - G_pos, 0.0)

    savings = np.zeros(N)
    pde_t1 = np.zeros(N)
    surplus_rev = np.zeros(N)
    grid_cost = np.zeros(N)
    neto_horario = np.zeros((N, T))
    permuta_t1_total = 0.0
    excedente_t2_total = 0.0
    pesos_usados = {}

    for mes, hours in period_hours.items():
        h = np.asarray(hours, dtype=int)
        pde_m = np.asarray(pde if pde_mensual is None else pde_mensual[mes],
                           dtype=float)
        if not validate_pde(pde_m):
            raise ValueError(
                f"PDE inválido en el mes {mes}: suma={np.sum(pde_m):.4f}")
        pesos_usados[mes] = pde_m
        asign = pde_m[:, None] * surplus_ind[:, h].sum(axis=0)[None, :]
        credito, exceso, _ = reparto_anexo4(asign, deficit_ind[:, h])
        pi_gs_mes = pi_gs_v[:, h].mean(axis=1)
        precio = pi_gs_mes - pi_C[:, h].mean(axis=1)
        auto_v = autoconsumo[:, h] * pi_gs_v[:, h]
        cred_v = credito * precio[:, None]
        exc_v = exceso * pb[None, h]
        neto_horario[:, h] = auto_v + cred_v + exc_v
        savings += auto_v.sum(axis=1)
        pde_t1 += cred_v.sum(axis=1)
        surplus_rev += exc_v.sum(axis=1)
        grid_cost += np.maximum(deficit_ind[:, h].sum(axis=1)
                                - credito.sum(axis=1), 0.0) * pi_gs_mes
        permuta_t1_total += float(credito.sum())
        excedente_t2_total += float(exceso.sum())

    if dt != 1.0:
        savings = savings * dt
        pde_t1 = pde_t1 * dt
        surplus_rev = surplus_rev * dt
        grid_cost = grid_cost * dt
        neto_horario = neto_horario * dt
        permuta_t1_total *= dt
        excedente_t2_total *= dt

    net_benefit = savings + pde_t1 + surplus_rev
    pde_ref = np.asarray(pde, dtype=float)
    results_per_agent = {
        n: {
            "savings":         float(savings[n]),
            "pde_credits":     float(pde_t1[n]),
            "surplus_revenue": float(surplus_rev[n]),
            "grid_cost":       float(grid_cost[n]),
            "net_benefit":     float(net_benefit[n]),
            "pde_weight":      float(pde_ref[n]),
        } for n in range(N)
    }
    return {
        "per_agent": results_per_agent,
        "neto_horario": neto_horario,
        "aggregate": {
            "total_savings":         float(savings.sum()),
            "total_pde_credits":     float(pde_t1.sum()),
            "total_surplus_revenue": float(surplus_rev.sum()),
            "total_grid_cost":       float(grid_cost.sum()),
            "total_net_benefit":     float(net_benefit.sum()),
            "total_E_permuta_t1":    permuta_t1_total,
            "total_E_excedente_t2":  excedente_t2_total,
        },
        "regulatory": {
            "pde_weights":            pde_ref,
            "pde_por_mes":            pesos_usados,
            "static_mechanism":       pde_mensual is None,
            "monthly_hx_inheritance": True,
        },
        "params": {
            "mode":            "monthly_hx",
            "max_capacity_kw": max_capacity_kw,
            "n_periods":       len(period_hours),
        },
    }


def _run_c4_legacy(
    D, G, pi_gs, pi_bolsa, pde, capacity,
    max_capacity_kw, mode, dt=1.0,
):
    """
    Implementación legacy pre-CAL-15 (mode='pde_only' o
    'pde_plus_residual_export'). Conservada para regression-test;
    no debe usarse en producción.
    """
    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)

    if not validate_pde(pde):
        raise ValueError(f"PDE inválido: debe sumar 1.0, suma={np.sum(pde):.4f}")

    _validate_capacity(capacity, max_capacity_kw)
    _warnings.warn(
        "C4: se asume un único comercializador de respaldo. "
        "Verificar con admin MTE antes de publicar.",
        UserWarning,
        stacklevel=4,
    )

    savings       = np.zeros(N)
    credits_pde   = np.zeros(N)
    grid_cost     = np.zeros(N)
    surplus_sell  = np.zeros(N)
    neto_horario  = np.zeros((N, T))          # C-165
    hourly_community_surplus = np.zeros(T)
    hourly_distribution      = np.zeros((N, T))

    for k in range(T):
        total_gen = float(np.sum(np.maximum(G[:, k], 0)))
        total_dem = float(np.sum(np.maximum(D[:, k], 0)))
        autoconsumo_k = np.minimum(np.maximum(G[:, k], 0),
                                    np.maximum(D[:, k], 0))
        deficit_k = np.maximum(D[:, k] - G[:, k], 0.0)

        community_surplus = max(0.0, total_gen - total_dem)
        hourly_community_surplus[k] = community_surplus
        credits_k = pde * community_surplus
        hourly_distribution[:, k] = credits_k
        deficit_after_pde = np.maximum(deficit_k - credits_k, 0.0)

        for n in range(N):
            savings[n]      += autoconsumo_k[n] * pi_gs_v[n, k]
            credits_pde[n]  += min(credits_k[n], deficit_k[n]) * pi_gs_v[n, k]
            grid_cost[n]    += deficit_after_pde[n] * pi_gs_v[n, k]
            # C-165: el mismo dinero, a su hora.
            neto_horario[n, k] += (autoconsumo_k[n] * pi_gs_v[n, k]
                                   + min(credits_k[n], deficit_k[n])
                                   * pi_gs_v[n, k])

        if mode == "pde_plus_residual_export":
            total_deficit_k = float(np.sum(deficit_k))
            residual_export = max(0.0, community_surplus - total_deficit_k)
            if residual_export > 0:
                for n in range(N):
                    surplus_sell[n] += pde[n] * residual_export * pi_bolsa[k]
                    neto_horario[n, k] += (pde[n] * residual_export
                                           * pi_bolsa[k])

    # CAL-46: de potencia a energía.
    if dt != 1.0:
        neto_horario = neto_horario * dt
        savings = savings * dt
        credits_pde = credits_pde * dt
        surplus_sell = surplus_sell * dt
        grid_cost = grid_cost * dt

    net_benefit = savings + credits_pde + surplus_sell

    results_per_agent = {}
    for n in range(N):
        results_per_agent[n] = {
            "savings":         float(savings[n]),
            "pde_credits":     float(credits_pde[n]),
            "surplus_revenue": float(surplus_sell[n]),
            "grid_cost":       float(grid_cost[n]),
            "net_benefit":     float(net_benefit[n]),
            "pde_weight":      float(pde[n]),
        }
    return {
        "per_agent": results_per_agent,
        "neto_horario": neto_horario,   # C-165
        "aggregate": {
            "total_savings":         float(np.sum(savings)),
            "total_pde_credits":     float(np.sum(credits_pde)),
            "total_surplus_revenue": float(np.sum(surplus_sell)),
            "total_grid_cost":       float(np.sum(grid_cost)),
            "total_net_benefit":     float(np.sum(net_benefit)),
        },
        "hourly": {
            "community_surplus": hourly_community_surplus,
            "pde_distribution":  hourly_distribution,
        },
        "regulatory": {
            "pde_weights":         pde,
            "static_mechanism":    True,
            "creg174_inheritance": False,
        },
        "params": {
            "mode":            mode,
            "max_capacity_kw": max_capacity_kw,
        },
    }


def regulatory_risk_c4(
    agent_capacities: np.ndarray,   # (N,) kW
    max_total_kw: float = 100.0,
) -> dict:
    """
    Evalúa riesgos regulatorios del esquema C4:
      - Violación del límite de 100 kW
      - Violación de la regla del 10 % de participación

    Este análisis es parte del Objetivo 4 de la tesis.
    """
    N = len(agent_capacities)
    total_cap = float(np.sum(agent_capacities))
    max_share = float(np.max(agent_capacities)) / total_cap if total_cap > 0 else 0.0

    risks = {
        "capacity_exceeded":      total_cap > max_total_kw,
        "total_capacity_kw":      total_cap,
        "max_single_share":       max_share,
        "concentration_risk":     max_share > 0.10,
        "n_agents":               N,
        "min_agents_for_stability": int(np.ceil(1 / 0.10)) if max_share > 0 else N,
    }
    return risks


def static_spread_c4_vs_p2p(
    D: np.ndarray,
    G: np.ndarray,
    pde: np.ndarray,
) -> np.ndarray:
    """
    Calcula el 'spread de ineficiencia estática' por hora:
    cuánta energía podría reasignarse dinámicamente pero el
    mecanismo PDE no puede capturar.

    Retorna array (T,) con el spread horario [kWh].
    """
    N, T = D.shape
    spread = np.zeros(T)

    for k in range(T):
        deficit_agents  = np.sum(np.maximum(D[:, k] - G[:, k], 0))
        surplus_agents  = np.sum(np.maximum(G[:, k] - D[:, k], 0))

        if deficit_agents > 0 and surplus_agents > 0:
            pde_to_surplus_agents = float(
                np.dot(pde, np.maximum(G[:, k] - D[:, k], 0))
            )
            spread[k] = pde_to_surplus_agents

    return spread
