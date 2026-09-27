"""El evaluador del GSA directo: una evaluacion completa del modelo por reposo
(piso, mercado de las 6 144 horas en un solo proceso, C1 a C5, el colectivo y
el P2P por la via del colectivo) en un punto de las seis entradas (D73, D74).

Actividad 4.1.

REPLICA `main()` DE `main_simulation.py` SIN MODIFICARLO, para la orden de la
matriz canonica:

    main_simulation.py --data real --full --include-c5 --no-regulado
      --metodo reposo --modo-presupuesto sigma --regla-precio uniforme
      --despacho-vendedores piso <opcion del caso>

en dos partes:

- `prepara_caso` hace, una vez por proceso, lo que `main()` hace antes del
  mercado y lo que no depende de las entradas del GSA: la carga del MTE, la
  exclusion y el escalado del caso, la capacidad instalada, las tarifas, la
  bolsa CRUDA, los peajes, los componentes del costo unitario, el PES y el
  precio del contrato de C5;
- `evalua` aplica los seis factores del apartado 4 del diseno y hace el
  resto: el piso por vendedor, el mercado (`parallel=False`), la
  liquidacion de los ocho escenarios y las salidas del apartado 5.

La deriva entre este fichero y `main()` la detecta la compuerta del punto
base (`compuerta_punto_base.py`), que reproduce al peso la hoja `Resumen` de
los trece casos del canon con todos los factores en 1.

Donde se aplica cada factor (apartado 4 del diseno):

- f_cv: el componente de comercializar en la deduccion del piso
  (`deduccion_art25`), en `component_c` de C1, C4, el colectivo, el residual
  del mercado y el del contrato. Es exactamente donde `main()` aplica
  `--factor-cv` (D7), de modo que f_cv = 2 en E0 reproduce el caso CV2. NO
  escala `cvm_component` (la descomposicion de C2 que usa C5) ni `pi_upper`,
  igual que `main()`; ver el informe de la tarea G.
- f_bolsa: la serie CRUDA de 2025 por el factor, y el techo PES de la
  101 066 DESPUES.
- f_tarifa: el techo (N, T) de cada comprador y el escalar comunitario, que
  con el reposo es inerte y se escala por coherencia.
- f_peaje: T+D+PR+R en la deduccion del numeral 2 y en `tolls` de la
  comparacion (colectivo en el caso 2).
- e_G, e_D: la generacion y la demanda tras el escalado del caso. La
  capacidad instalada no cambia: es la placa.
"""
from __future__ import annotations

import contextlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from gsa_directo import comun

RAIZ = comun.RAIZ


# ── Carga del MTE, con cache por huella del dato ────────────────────────────
def carga_mte(mte_root: Optional[str] = None, cache_dir=None,
              verbose: bool = False):
    """(D, G, index) del horizonte completo, como `main()` los carga
    (`MTEDataLoader(mte_root).load(paso=1.0)`). Con `cache_dir`, guarda y
    reutiliza un `.npz` cuyo nombre lleva la huella del dato: si el dato o
    `data/` cambian, la huella cambia y la carga se rehace."""
    mte_root = mte_root or comun.mte_root_defecto()
    ruta = None
    if cache_dir is not None:
        huella = comun.huella_datos(mte_root)
        ruta = Path(cache_dir) / f"carga_mte_{huella}.npz"
        if ruta.exists():
            with np.load(ruta, allow_pickle=False) as z:
                idx = pd.DatetimeIndex(z["idx"].astype("datetime64[ns]"))
                tz = str(z["tz"])
                if tz:
                    idx = idx.tz_localize(tz)
                return np.array(z["D"]), np.array(z["G"]), idx
    from data.xm_data_loader import MTEDataLoader
    with _silencio(not verbose):
        D, G, idx = MTEDataLoader(mte_root).load(verbose=verbose, paso=1.0)
    if ruta is not None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = ruta.with_name(ruta.stem + f".tmp{os.getpid()}.npz")
        tz = "" if idx.tz is None else str(idx.tz)
        sin_zona = idx.tz_localize(None) if idx.tz is not None else idx
        np.savez(tmp, D=np.asarray(D, dtype=float),
                 G=np.asarray(G, dtype=float),
                 idx=sin_zona.to_numpy(dtype="datetime64[ns]"),
                 tz=np.asarray(tz, dtype="U64"))
        os.replace(tmp, ruta)
    return D, G, idx


@dataclass
class Insumos:
    """Todo lo que una evaluacion necesita y no depende de las entradas."""
    caso: str
    nombres: list
    D: np.ndarray
    G: np.ndarray
    t0: str
    cap: np.ndarray
    pi_gs: np.ndarray
    pi_gs_eff: float
    b: np.ndarray
    month_labels: Optional[np.ndarray]
    mes_m: np.ndarray
    bolsa_cruda: np.ndarray
    cvm: np.ndarray
    cu_G: np.ndarray
    cu_Cvm: np.ndarray
    cu_COT: np.ndarray
    tolls: np.ndarray
    mem: np.ndarray
    pi_G: np.ndarray
    pes: Optional[np.ndarray]
    pi_c5: np.ndarray
    pi_gb: float
    pi_ppa: float
    fuente_bolsa: str
    dia: Optional[str] = None
    fechas: list = field(default_factory=list)
    # A2 (2026-09-27): el comercializador forzado para las cinco al preparar
    # el caso (contrafactico del art. 10 num. 1 de la CREG 101 072), o None
    # con el reparto real (cuatro con ASC, Cesmag con CEDENAR), que es el
    # canon.
    comercializador: Optional[str] = None

    @property
    def N(self) -> int:
        return int(self.D.shape[0])

    @property
    def T(self) -> int:
        return int(self.D.shape[1])


def prepara_caso(caso: str, datos=None, mte_root: Optional[str] = None,
                 cache_dir=None, dia: Optional[str] = None,
                 comercializador: Optional[str] = None) -> Insumos:
    """Replica `main()` (lineas 656-970 y 1412-1580 del 2026-09-26) para
    `--data real --full --include-c5 --no-regulado` y la opcion del caso.
    Con `dia`, replica `--day` en vez de `--full` (la prueba de un dia).

    `comercializador` (A2, contrafactico del art. 10 num. 1 de la CREG
    101 072): con "asc" o "cedenar", las cinco se preparan con ese
    comercializador (`data.cedenar_tariff.forzar_comercializador`, llamado
    justo DESPUES del regimen no regulado, que reescribe el perfil). Mueve el
    techo, el Cv del piso y de la liquidacion, los componentes del CU, el
    precio del contrato del colectivo y el escalar comunitario; `evalua` no
    vuelve a leer tarifas, de modo que los `Insumos` llevan todo el cambio. El
    reparto real se RESTITUYE al salir, tambien si algo falla (la excepcion
    sigue su curso). Con None (el defecto) no se llama a nada nuevo y el
    resultado es el de siempre, al bit: es el canon."""
    if comercializador is None:
        return _prepara_caso(caso, datos, mte_root, cache_dir, dia, None)
    from data.cedenar_tariff import forzar_comercializador
    try:
        return _prepara_caso(caso, datos, mte_root, cache_dir, dia,
                             comercializador)
    finally:
        forzar_comercializador(None)


def _prepara_caso(caso, datos, mte_root, cache_dir, dia,
                  comercializador) -> Insumos:
    from data.xm_prices import get_pi_bolsa, get_b_for_real_data
    import data.xm_prices as _xmp
    from data.cedenar_tariff import (
        aplicar_regimen_no_regulado, community_effective_pi_gs,
        cvm_per_agent_hourly, pi_gs_per_agent_hourly,
        g_plus_commercialization_per_agent_hourly,
        cu_components_per_agent_hourly, mem_costs_per_agent_hourly)
    from data.base_case_data import GRID_PARAMS_REAL
    from data.escalado import escala_comunidad, lee_escala_agente
    from data.capacidad_instalada import capacidad_instalada
    from data.precios_contratos import precio_horario

    op = comun.opciones_caso(caso)
    if datos is None:
        datos = carga_mte(mte_root, cache_dir)
    D_full, G_full, index_full = datos
    D_full = np.array(D_full, dtype=float, copy=True)
    G_full = np.array(G_full, dtype=float, copy=True)

    todos = list(comun.INSTITUCIONES[:D_full.shape[0]])
    fuera = [n.strip() for n in (op["excluir_agente"] or "").split(",")
             if n.strip()]
    malos = [n for n in fuera if n not in todos]
    if malos:
        raise ValueError(f"excluir_agente: {malos} no esta entre {todos}")
    if fuera:
        quedan = [i for i, n in enumerate(todos) if n not in fuera]
        D_full, G_full = D_full[quedan], G_full[quedan]

    # --no-regulado (CAL-47): estado GLOBAL; va antes de cualquier tarifa.
    aplicar_regimen_no_regulado(True)
    if comercializador is not None:
        # A2: despues del regimen (que reescribe el perfil) y antes de la
        # primera tarifa. `prepara_caso` lo restituye al salir.
        from data.cedenar_tariff import forzar_comercializador
        forzar_comercializador(comercializador)

    N = D_full.shape[0]
    nombres = [n for n in todos if n not in fuera][:N]

    D_full, G_full, factores_g = escala_comunidad(
        D_full, G_full, nombres,
        factor_generacion=op["factor_generacion"],
        factor_demanda=op["factor_demanda"],
        generacion_por_agente=lee_escala_agente(op["escala_agente"]),
        neto_cero=op["neto_cero"])
    cap = capacidad_instalada(nombres, factores_g)

    t_start_cal = index_full[0]
    t_end_cal = index_full[-1] + pd.Timedelta(hours=1)
    pi_gs_eff = float(community_effective_pi_gs(
        nombres, t_start_cal, t_end_cal, weights=D_full.mean(axis=1)))
    b_cal = get_b_for_real_data(N, nombres)

    if dia:
        from data.xm_data_loader import slice_horizon
        fin = (pd.Timestamp(dia) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        D, G, idx = slice_horizon(D_full, G_full, index_full, dia, fin)
        month_labels = None
    else:
        D, G, idx = D_full, G_full, index_full
        month_labels = np.array([ts.year * 100 + ts.month for ts in idx],
                                dtype=int)
    T = D.shape[1]

    xm_csv = RAIZ / "data" / "xm_precios_bolsa.csv"
    t_start_xm = idx[0].strftime("%Y-%m-%d")
    t_end_xm = (idx[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")
    with _silencio(True):
        bolsa_cruda = np.asarray(get_pi_bolsa(
            T, t_start=t_start_xm, t_end=t_end_xm,
            csv_path=str(xm_csv) if xm_csv.exists() else None,
            scenario="2025_normal", apply_ceiling=False, dt=1.0), dtype=float)
    fuente = _xmp.ULTIMA_FUENTE or "desconocida"
    _exige_finito("bolsa cruda", bolsa_cruda)

    pi_gs_arg = np.asarray(pi_gs_per_agent_hourly(nombres, idx), dtype=float)
    # D7: `main()` escala el mismo Cv en el piso y en `component_c`.
    cvm = (np.asarray(cvm_per_agent_hourly(nombres, idx), dtype=float)
           * op["factor_cv"])
    cu = cu_components_per_agent_hourly(nombres, idx)
    tolls = cu["T"] + cu["D"] + cu["PR"] + cu["R"]
    mes_m = pd.Series(idx).dt.strftime("%Y-%m").to_numpy()
    pi_G = g_plus_commercialization_per_agent_hourly(nombres, idx)
    mem = mem_costs_per_agent_hourly(nombres, idx)

    pi_gb = float(GRID_PARAMS_REAL["pi_gb"])
    g_mean = float(np.nanmean(cu["G"]))
    cvm_mean = float(np.nanmean(cu["Cvm"]))
    cot_mean = float(np.nanmean(cu["COT"]))
    mem_mean = float(np.nanmean(mem))
    pi_upper = g_mean + cvm_mean + 1.0 * cot_mean - mem_mean
    pi_ppa = pi_gb + 0.5 * (pi_upper - pi_gb)

    pes = None
    if isinstance(month_labels, np.ndarray):
        pes_df = pd.read_csv(RAIZ / "data" / "precios_escasez_creg.csv")
        pes_map = {int(str(m).replace("-", "")): float(v)
                   for m, v in zip(pes_df["mes"], pes_df["pes_cop_kwh"])}
        faltan = sorted({int(m) for m in month_labels} - set(pes_map))
        if faltan:
            raise ValueError(f"[CAL-37] data/precios_escasez_creg.csv no tiene "
                             f"el PES de los meses {faltan}")
        pes = np.array([pes_map[int(m)] for m in month_labels])
    pi_c5 = np.asarray(precio_horario(idx), dtype=float)

    return Insumos(
        caso=caso, nombres=nombres, D=np.asarray(D, float),
        G=np.asarray(G, float), t0=t_start_xm, cap=np.asarray(cap, float),
        pi_gs=pi_gs_arg, pi_gs_eff=pi_gs_eff, b=np.asarray(b_cal, float),
        month_labels=month_labels, mes_m=mes_m, bolsa_cruda=bolsa_cruda,
        cvm=cvm, cu_G=np.asarray(cu["G"], float),
        cu_Cvm=np.asarray(cu["Cvm"], float),
        cu_COT=np.asarray(cu["COT"], float), tolls=np.asarray(tolls, float),
        mem=np.asarray(mem, float), pi_G=np.asarray(pi_G, float), pes=pes,
        pi_c5=pi_c5, pi_gb=pi_gb, pi_ppa=float(pi_ppa), fuente_bolsa=fuente,
        dia=dia, fechas=[str(idx[0]), str(idx[-1])],
        comercializador=comercializador)


def inicia_proceso() -> None:
    """Inicializador de cada proceso del pool: el regimen no regulado es
    ESTADO GLOBAL de `data.cedenar_tariff`, y un proceso nuevo no lo hereda
    en Windows (spawn)."""
    from data.cedenar_tariff import aplicar_regimen_no_regulado
    aplicar_regimen_no_regulado(True)


# ── Los factores ────────────────────────────────────────────────────────────
def aplica_bolsa(bolsa_cruda: np.ndarray, f_bolsa: float, t0: str
                 ) -> np.ndarray:
    """La serie cruda por el factor y el techo PES de la 101 066 DESPUES."""
    from data.xm_prices import apply_creg101066_ceiling
    cruda = np.asarray(bolsa_cruda, dtype=float) * float(f_bolsa)
    return np.asarray(apply_creg101066_ceiling(cruda, t0, level="PES"),
                      dtype=float)


def aplica_factores(ins: Insumos, x, bolsa_cruda=None) -> dict:
    """Las series que cambian con las seis entradas; funcion pura."""
    x = np.asarray(x, dtype=float).reshape(-1)
    if x.size != comun.D_ENTRADAS or not np.all(np.isfinite(x)):
        raise ValueError(f"entrada no valida: {x!r}")
    f_cv, f_b, f_t, f_p, e_g, e_d = (float(v) for v in x)
    cruda = ins.bolsa_cruda if bolsa_cruda is None else bolsa_cruda
    cruda = np.asarray(cruda, dtype=float)
    if cruda.shape != (ins.T,):
        raise ValueError(f"bolsa {cruda.shape}, se esperaba ({ins.T},)")
    return dict(
        G=ins.G * e_g, D=ins.D * e_d,
        bolsa=aplica_bolsa(cruda, f_b, ins.t0),
        techo=ins.pi_gs * f_t, pi_gs_eff=ins.pi_gs_eff * f_t,
        cvm=ins.cvm * f_cv, tolls=ins.tolls * f_p)


# ── La evaluacion ───────────────────────────────────────────────────────────
def evalua(ins: Insumos, x, mu: float = 1.0, bolsa_cruda=None,
           b_factor: float = 1.0, silencio: bool = True) -> dict:
    """Una evaluacion completa. Devuelve un dict con `comun.columnas_salida`.

    Falla en voz alta (ValueError) con una entrada o una salida no finita, un
    piso negativo en una hora-vendedor, o una hora que termino con excepcion
    del nucleo (C-190) o sin resolver: no se imputa nada."""
    with _silencio(silencio):
        return _evalua(ins, x, mu, bolsa_cruda, b_factor)[0]


def _evalua(ins, x, mu, bolsa_cruda, b_factor) -> dict:
    from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
    from core.opciones_externas import deduccion_art25, piso_residual
    from data.base_case_data import GRID_PARAMS_REAL
    from scenarios import run_comparison
    from scenarios.scenario_c4_creg101072 import compute_pde_weights
    from main_simulation import cuenta_para_salida, cuenta_retiros_reposo

    f = aplica_factores(ins, x, bolsa_cruda)
    G, D, bolsa, techo = f["G"], f["D"], f["bolsa"], f["techo"]
    for nombre in ("G", "D", "bolsa", "techo", "cvm", "tolls"):
        _exige_finito(nombre, f[nombre])
    N, T = D.shape

    ded = deduccion_art25(f["cvm"], f["tolls"], ins.cap)
    piso, _en_permuta = piso_residual(G, D, techo, ded, bolsa, ins.mes_m)
    vende = np.maximum(G - D, 0.0) > 1e-9
    if (np.asarray(piso)[vende] < 0).any():
        raise ValueError(f"piso negativo en {int((piso[vende] < 0).sum())} "
                         f"horas-vendedor")

    grid = GridParams(**{**GRID_PARAMS_REAL, "pi_gs": f["pi_gs_eff"]},
                      pi_gs_agente=techo, pi_gb_agente=piso)
    agents = AgentParams(N=N, a=np.zeros(N), b=ins.b * float(b_factor),
                         c=np.zeros(N), lam=np.full(N, 100.0),
                         theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    # Los mismos argumentos que `main()`; los del acoplado son inertes con
    # el reposo y van con el defecto de `main()`. `parallel=False`: una
    # evaluacion es un proceso, y el pool es el del GSA.
    solver = SolverParams(
        tau=0.001, t_span=(0.0, 0.005), n_points=150, stackelberg_iters=2,
        parallel=False, metodo="reposo", t_span_acoplado=0.05,
        rtol_acoplado=1e-6, horizonte_max_acoplado=None,
        presupuesto_eval_acoplado=None, arranque_acoplado="factible",
        criterio_estacionario="precio", tol_reparto=0.01,
        modo_presupuesto="sigma", sigma_nivel=None, regla_precio="uniforme",
        despacho_vendedores="piso", mu_entropia=0.0, nivel_acoplado="c136",
        costo_vendedor="lcoe", piso_juego="minimo", mu_cuantal=float(mu),
        buyer_competition="aggregate", guarda_trayectorias=False,
        procesos=None, plazo_hora_s=None)
    res, G_klim, D_star = EMSP2P(agents, grid, solver).run(D, G)

    malas = [r for r in res if (getattr(r, "motivo", "") or "")]
    if malas:
        raise ValueError(f"{len(malas)} horas sin resolver por el nucleo; la "
                         f"primera, hora {malas[0].k}: {malas[0].motivo}"[:300])
    if np.any(agents.alpha > 1e-9):          # sin DR en datos reales
        D = D_star

    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G, p2p_results=res,
        pi_gs=techo, pi_gb=ins.pi_gb, pi_bolsa=bolsa,
        prosumer_ids=list(range(N)), consumer_ids=[],
        pde=compute_pde_weights(np.ones(N), method="equal"),
        pi_ppa=ins.pi_ppa, piso_agente=piso, pi_contrato=None,
        capacity=ins.cap, month_labels=ins.month_labels,
        component_c=f["cvm"], tolls=f["tolls"], pi_G=ins.pi_G,
        g_component=ins.cu_G, cvm_component=ins.cu_Cvm,
        cot_component=ins.cu_COT, mem_costs=ins.mem, cot_alpha=1.0,
        include_c5=True, pi_escasez=ins.pes, pi_contrato_c5=ins.pi_c5,
        dt=1.0)

    # La parte del vendedor DEL ALMACEN (trampa 2 del canon): la prima contra
    # el piso del vendedor en el juego, sobre las mismas horas y los mismos
    # pares que `anota_flujos` escribe en `main()`.
    prima = ahorro = energia = 0.0
    for r in res:
        if not r.seller_ids or not r.buyer_ids:
            continue
        if r.P_star is None:
            continue
        P = np.asarray(r.P_star, dtype=float)
        pi = np.asarray(r.pi_star, dtype=float)
        if not (np.all(np.isfinite(P)) and np.all(np.isfinite(pi))):
            raise ValueError(f"hora {r.k}: solucion no finita")
        tb = techo[r.buyer_ids, r.k]
        pj = np.asarray(piso)[r.seller_ids, r.k]
        energia += float(P.sum())
        ahorro += float(((tb - pi)[None, :] * P).sum())
        prima += float(((pi[None, :] - pj[:, None]) * P).sum())
    excedente = prima + ahorro

    nb = cr.net_benefit
    out = {k: float(nb[k]) for k in ("P2P", "P2P_colectivo", "C1", "C2",
                                     "C3", "C4", "C5")}
    out["energia"] = energia
    out["excedente"] = excedente
    out["parte_vendedor"] = (prima / excedente if excedente > 0
                             else float("nan"))
    for b, (a, c) in comun.BRECHAS.items():
        out[b] = out[a] - out[c]
    n_mercado = cuenta_para_salida(res)[0]
    regs = [str(getattr(r, "regimen", "") or "") for r in res]
    out["n_horas_mercado"] = float(n_mercado)
    out["n_cuantal"] = float(sum(1 for g in regs if g == "cuantal"))
    out["n_sin_ganancia"] = float(sum(1 for g in regs if g == "sin_ganancia"))
    out["retiros"] = float(cuenta_retiros_reposo(res))
    pa = cr.net_benefit_per_agent
    for n, nombre in enumerate(ins.nombres):
        for b, (a, c) in comun.BRECHAS_INSTITUCION.items():
            out[f"{b}__{nombre}"] = float(pa[a][n] - pa[c][n])

    cols = comun.columnas_salida(ins.nombres)
    faltan = [c for c in cols if c not in out]
    if faltan:
        raise ValueError(f"faltan salidas: {faltan}")
    no_finitas = [c for c in cols if not np.isfinite(out[c])]
    if no_finitas:
        raise ValueError(f"salida no finita: {', '.join(no_finitas)}")
    return {c: out[c] for c in cols}, cr


def evalua_detalle(ins: Insumos, x, mu: float = 1.0, bolsa_cruda=None,
                   silencio: bool = True) -> tuple:
    """Como `evalua`, y ademas el beneficio por institucion de los ocho
    escenarios, para la compuerta del punto base (hoja `Por_agente`)."""
    with _silencio(silencio):
        return _evalua_con_agentes(ins, x, mu, bolsa_cruda)


def evalua_comparacion(ins: Insumos, x, mu: float = 1.0, bolsa_cruda=None,
                       silencio: bool = True) -> tuple:
    """Como `evalua`, y ademas el `ComparisonResult` de `run_comparison`
    entero (p. ej. `cr.contrafacticos`), sin tocar lo que devuelven `evalua`
    ni `evalua_detalle` (C-206)."""
    with _silencio(silencio):
        return _evalua(ins, x, mu, bolsa_cruda, 1.0)


def _evalua_con_agentes(ins, x, mu, bolsa_cruda):
    out, cr = _evalua(ins, x, mu, bolsa_cruda, 1.0)
    por_agente = {e: np.asarray(v, dtype=float).copy()
                  for e, v in cr.net_benefit_per_agent.items()}
    return out, por_agente, {e: float(v) for e, v in cr.net_benefit.items()}


# ── Utilidades ──────────────────────────────────────────────────────────────
def _exige_finito(nombre: str, x) -> None:
    a = np.asarray(x, dtype=float)
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{nombre}: {int(np.sum(~np.isfinite(a)))} de "
                         f"{a.size} valores no finitos (H-50)")


@contextlib.contextmanager
def _silencio(activo: bool):
    """Calla stdout y stderr del nucleo y de la comparacion (la barra de
    progreso, los avisos de cada escenario), que en 28 672 evaluaciones
    llenarian el registro. Las excepciones pasan igual."""
    if not activo:
        yield
        return
    with open(os.devnull, "w", encoding="utf-8") as nulo, \
            contextlib.redirect_stdout(nulo), contextlib.redirect_stderr(nulo):
        yield
