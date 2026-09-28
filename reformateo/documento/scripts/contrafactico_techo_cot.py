"""
contrafactico_techo_cot.py — El techo de la bolsa del Anexo 4 de la CREG
101 072 y el COT en la deduccion de la permuta (H-107, 2026-09-28).
==========================================================================
Dos lecturas de la norma que el modelo no sigue al pie de la letra (revision
del capitulo 3, hallazgo m1 y discrepancia 1):

1. El Anexo 4 de la CREG 101 072 (hoja 47 del PDF) define el precio de bolsa
   de la liquidacion «siempre y cuando no supere el precio de escasez
   ponderado». El modelo topa la bolsa con el precio de escasez SUPERIOR
   mensual de la 101 066 (`data/xm_prices.py`, `apply_creg101066_ceiling`).
   El precio de escasez ponderado (PEpm; CREG 140 de 2017, art. 1, y CREG
   101 066 de 2024, art. 1, que reescriben las definiciones del art. 2 de la
   CREG 071 de 2006) es el promedio de los precios de escasez de cada planta
   ponderado por su obligacion de energia firme. XM lo publica como
   `PrecEscaPon` («Precio Escasez Ponderado por Sistema ... Resolucion CREG
   140 de 2017»). La serie `PrecEsca` de `data/precios_escasez_creg.csv`
   (columna `pe_cop_kwh`) NO es el ponderado: es el «Precio Escasez por
   Sistema», el que fija la CREG y se actualiza cada mes con un indice de
   combustibles (Anexo 1 de la 071). Se miden las dos: la literal
   (`PrecEscaPon`) y la cota del encargo (`PrecEsca`, mas baja).
2. El art. 5 de la CREG 101 028 de 2023 reescribe el art. 11 de la 119 y
   suma el COT dentro del termino de comercializacion. El modelo deduce solo
   el Cv (CAL-10b.2). Afecta solo a Cesmag, que atiende CEDENAR.

El canon NO cambia. Variantes, en el punto base del GSA (seis factores en 1,
mu = 1) con `evaluador.evalua_comparacion`:

    real             el canon (debe reproducirlo al peso)
    techo_ponderado  la bolsa CRUDA topada cada hora con min(bolsa, PEpm del
                     mes) antes de todo; el techo PES de despues no la mueve
                     (se comprueba)
    techo_pe         igual, con PrecEsca (la cota del encargo)
    cot              la deduccion del art. 25 (piso de permuta y
                     `component_c`) con Cv + COT en CEDENAR y solo Cv en ASC
                     (`prepara_caso(..., cot_en_deduccion=True)`); C5 no se
                     toca, ya lleva el COT en su tasa
    ambos            techo_ponderado y cot juntas

Compuerta: la variante `real` tiene que reproducir al peso el canon de los
trece casos con las comprobaciones de `gsa_directo/compuerta_punto_base.py`.
Si no, se detiene sin escribir nada.

La energia a bolsa en las horas afectadas, por mecanismo, se mide como la
diferencia del beneficio horario (`neto_horario`, C-165) entre la variante
sin techo y la topada, dividida por la baja del precio en cada hora
afectada. En C1, C3, C4 y C5 es exactamente la energia que el mecanismo
valora a bolsa en esas horas (las cantidades no dependen del precio); en
P2P, C2 y el colectivo incluye ademas la reaccion del mercado al piso, y es
una energia equivalente (`dCOP_fuera_afectadas_*` mide lo que esa reaccion
mueve fuera de las horas afectadas).

La serie de precios de escasez de XM (PrecEscaInf, PrecEsca, PrecEscaPon,
PrecEscaSup, PrecEscaMarg; entidad Sistema, un valor por mes) se lee de
`precios_escasez_xm.csv` en la carpeta de salida; si no esta, se descarga del
API de XM (servapibi.xm.com.co/daily) y se escribe junto con las salidas. Las
columnas PEI, PE y PES tienen que coincidir con `data/precios_escasez_creg.csv`.

Escribe en SALIDAS_SERVIDOR/contrafactico_techo_cot_2026-09-28/:

    mecanismos_13casos.csv   caso, variante, beneficio de cada mecanismo, su
                             diferencia con real (COP y %) y la energia a
                             bolsa en las horas afectadas
    brechas_13casos.csv      seis brechas de comunidad con su signo y si
                             cambia respecto de real
    por_institucion.csv      P2P - C1, P2P - C4 y P2P - C5 por institucion,
                             con su signo y si cambia
    horas_afectadas.csv      por caso y mes, las horas con la bolsa por encima
                             de cada techo y la energia en ellas
    compuerta_real.csv       las comprobaciones de la variante real
    precios_escasez_xm.csv   el insumo de XM
    procedencia.txt          commit, versiones, orden, dato, PrecEsca y su
                             fuente

No escribe en `outputs/` ni en `graficas/`.

    python -u reformateo/documento/scripts/contrafactico_techo_cot.py

Actividad 2.2.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gsa_directo import comun  # noqa: E402

VARIANTES = ("real", "techo_ponderado", "techo_pe", "cot", "ambos")
# variante -> (COT en la deduccion, techo de la bolsa cruda o None)
DEF_VARIANTE = {
    "real": (False, None),
    "techo_ponderado": (False, "pon"),
    "techo_pe": (False, "pe"),
    "cot": (True, None),
    "ambos": (True, "pon"),
}
# variante -> (variante sin techo, variante con techo) para la energia a
# bolsa en las horas afectadas
PAR_ENERGIA = {
    "real": ("real", "techo_ponderado"),
    "techo_ponderado": ("real", "techo_ponderado"),
    "techo_pe": ("real", "techo_pe"),
    "cot": ("cot", "ambos"),
    "ambos": ("cot", "ambos"),
}
MECANISMOS = ("P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5")
BRECHAS = {                      # nombre -> (minuendo, sustraendo)
    "P2P_menos_C1": ("P2P", "C1"),
    "P2P_menos_C4": ("P2P", "C4"),
    "P2P_menos_C5": ("P2P", "C5"),
    "P2Pcol_menos_C1": ("P2P_colectivo", "C1"),
    "C4_menos_C1": ("C4", "C1"),
    "P2Pcol_menos_C4": ("P2P_colectivo", "C4"),
}
BRECHAS_INST = ("P2P_menos_C1", "P2P_menos_C4", "P2P_menos_C5")
TOL_PESO = 0.5
MATRIZ_CANON = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
                / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "contrafactico_techo_cot_2026-09-28"
TABLA_PES = RAIZ / "data" / "precios_escasez_creg.csv"
API_XM = "https://servapibi.xm.com.co/daily"
METRICAS_XM = {"PrecEscaInf": "pei_cop_kwh", "PrecEsca": "pe_cop_kwh",
               "PrecEscaPon": "pon_cop_kwh", "PrecEscaSup": "pes_cop_kwh",
               "PrecEscaMarg": "pme_cop_kwh"}
DEFINICION_PRECESCA = (
    "PrecEsca (API de XM, «Precio Escasez por Sistema»): «Establecido por la "
    "CREG y actualizado mensualmente con base en la variacion de un indice de "
    "precios de combustibles»; es el precio de escasez del Anexo 1 de la CREG "
    "071 de 2006, NO el ponderado. El precio de escasez ponderado (PEpm) lo "
    "publica XM aparte como PrecEscaPon («Precio Escasez Ponderado del "
    "Sistema calculado de acuerdo a la Resolucion CREG 140 de 2017»). "
    "Definicion normativa del ponderado: CREG 140 de 2017, art. 1 (modifica "
    "las definiciones del art. 2 de la CREG 071 de 2006), y CREG 101 066 de "
    "2024, art. 1: «Precio de escasez ponderado (PEpm): es el valor promedio "
    "ponderado de los precios de escasez mensual», PEpm = sum(PE_i,j,m * "
    "OEF_i,j,m) / sum(OEF_i,j,m), con PE_i,j,m el precio de escasez de la "
    "planta (superior o inferior segun la 101 066) y OEF_i,j,m su obligacion "
    "mensual de energia firme. Fuentes: gestornormativo.creg.gov.co "
    "resolucion_creg_0140_2017.htm y resolucion_creg_101-66_2024.htm; "
    "listado de metricas del API servapibi.xm.com.co/lists (ListadoMetricas), "
    "consultados el 2026-09-28.")


def signo(v: float) -> str:
    """'+', '-' o '0' (dentro de medio peso)."""
    if not np.isfinite(v):
        raise ValueError(f"brecha no finita: {v!r}")
    return "0" if abs(v) <= TOL_PESO else ("+" if v > 0 else "-")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                       text=True, check=True)
    return r.stdout.rstrip("\n")


# ── El insumo de XM ─────────────────────────────────────────────────────────
def _pide_xm(metrica: str, ini: str, fin: str) -> list:
    cuerpo = json.dumps({"MetricId": metrica, "StartDate": ini,
                         "EndDate": fin, "Entity": "Sistema"}).encode()
    req = urllib.request.Request(API_XM, data=cuerpo, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    return [(it["Date"][:10], float(e["Value"]))
            for it in d.get("Items", []) for e in it["DailyEntities"]]


def descarga_xm(meses: list) -> pd.DataFrame:
    """Un valor por mes y metrica; falla si un mes no tiene dato o tiene mas
    de un valor, o si no cubre todos los dias del mes."""
    filas = []
    for mes in meses:
        p = pd.Period(mes, "M")
        ini, fin = p.start_time.strftime("%Y-%m-%d"), p.end_time.strftime(
            "%Y-%m-%d")
        fila = {"mes": mes}
        for met, col in METRICAS_XM.items():
            vals = _pide_xm(met, ini, fin)
            dias = {d for d, _ in vals}
            unicos = sorted({v for _, v in vals})
            if len(dias) != p.days_in_month or len(unicos) != 1:
                raise ValueError(f"XM {met} {mes}: {len(dias)} dias de "
                                 f"{p.days_in_month} y {len(unicos)} valores "
                                 f"distintos; se esperaba un valor unico")
            fila[col] = unicos[0]
        fila["fuente"] = (f"{API_XM} Entity=Sistema, descargado "
                          f"{dt.date.today().isoformat()}; valor unico en los "
                          f"{p.days_in_month} dias del mes")
        filas.append(fila)
    return pd.DataFrame(filas)


def lee_o_descarga_xm(ruta: Path, meses: list):
    """(tabla, descargada). Comprueba PEI, PE y PES contra la tabla del
    modelo y que PEI < PE, PEI < PEpm <= PES en cada mes."""
    if ruta.exists():
        tabla, nueva = pd.read_csv(ruta, dtype={"mes": str}), False
    else:
        tabla, nueva = descarga_xm(meses), True
    faltan = sorted(set(meses) - set(tabla["mes"]))
    if faltan:
        raise ValueError(f"{ruta.name}: faltan los meses {faltan}")
    tabla = tabla.set_index("mes").loc[meses]
    num = tabla[list(METRICAS_XM.values())].to_numpy(dtype=float)
    if not np.all(np.isfinite(num)):
        raise ValueError("precios de escasez de XM no finitos")
    modelo = pd.read_csv(TABLA_PES, dtype={"mes": str}).set_index("mes")
    for col in ("pei_cop_kwh", "pe_cop_kwh", "pes_cop_kwh"):
        d = np.abs(tabla[col].to_numpy(float)
                   - modelo.loc[meses, col].to_numpy(float))
        if d.max() > 1e-4:
            raise ValueError(f"{col}: XM y {TABLA_PES.name} difieren "
                             f"({d.max():.6f} COP/kWh)")
    t = tabla
    if not ((t.pei_cop_kwh < t.pe_cop_kwh).all()
            and (t.pei_cop_kwh < t.pon_cop_kwh).all()
            and (t.pon_cop_kwh <= t.pes_cop_kwh).all()):
        raise ValueError("el orden PEI < PE, PEI < PEpm <= PES no se cumple")
    return tabla.reset_index(), nueva


# ── Las variantes ───────────────────────────────────────────────────────────
def bolsa_topada(ins, techo_mes: dict) -> np.ndarray:
    """La bolsa CRUDA topada cada hora con el techo de su mes (hora local)."""
    techo = np.array([techo_mes[m] for m in ins.mes_m], dtype=float)
    return np.minimum(np.asarray(ins.bolsa_cruda, float), techo), techo


def exige_techo_pes_inerte(evaluador, cruda_top: np.ndarray, t0: str):
    """El techo PES de `aplica_bolsa` no cambia la serie ya topada."""
    final = evaluador.aplica_bolsa(cruda_top, 1.0, t0)
    if not np.array_equal(final, cruda_top):
        n = int(np.sum(final != cruda_top))
        raise RuntimeError(f"el techo PES de despues cambio {n} horas de la "
                           f"serie topada")
    return final


def energia_afectada(cr_sin, cr_con, b_sin, b_con, nombres) -> dict:
    """Por mecanismo: energia (kWh) valorada a bolsa en las horas en que la
    bolsa baja, y lo que se mueve fuera de esas horas (COP), que tiene que
    ser nulo salvo en los mecanismos con mercado."""
    dp = np.asarray(b_sin, float) - np.asarray(b_con, float)
    if (dp < -1e-12).any():
        raise ValueError("la bolsa topada supera a la sin tope")
    afect = dp > 1e-9
    out = {}
    for m in MECANISMOS:
        a, b = cr_sin.neto_horario.get(m), cr_con.neto_horario.get(m)
        if a is None or b is None:
            raise ValueError(f"{m}: falta neto_horario")
        a, b = np.asarray(a, float), np.asarray(b, float)
        if a.shape != (len(nombres), dp.size) or a.shape != b.shape:
            raise ValueError(f"{m}: neto_horario {a.shape} / {b.shape}")
        d = (a - b).sum(axis=0)
        if not np.all(np.isfinite(d)):
            raise ValueError(f"{m}: neto_horario no finito")
        out[f"E_bolsa_afectadas_{m}_kWh"] = float(
            (d[afect] / dp[afect]).sum()) if afect.any() else 0.0
        out[f"dCOP_fuera_afectadas_{m}"] = float(np.abs(d[~afect]).sum())
    return out


def evalua(evaluador, ins, cruda):
    out, cr = evaluador.evalua_comparacion(ins, comun.PUNTO_BASE,
                                           bolsa_cruda=cruda)
    return out, cr


def main(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--matriz", default=str(MATRIZ_CANON))
    ap.add_argument("--salida", default=str(SALIDA))
    ap.add_argument("--casos", nargs="+", default=list(comun.ORDEN_CASOS))
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None,
                    help="carpeta de cache de la carga del MTE (opcional)")
    ap.add_argument("--precios-escasez", default=None,
                    help="CSV de XM (por defecto, en la carpeta de salida; "
                         "si falta, se descarga)")
    args = ap.parse_args(argv)

    from gsa_directo import evaluador
    from gsa_directo import compuerta_punto_base as cpb
    from data.xm_prices import apply_creg101066_ceiling

    malos = [c for c in args.casos if c not in comun.CASOS]
    if malos:
        raise SystemExit(f"casos desconocidos: {malos}")
    matriz = Path(args.matriz)
    registros = cpb._registros_de(matriz, None)
    if registros is None:
        raise SystemExit(f"no se hallan los registros D71 junto a {matriz}")
    ajenos = [c for c in args.casos
              if cpb.huella_libro(matriz / c) != cpb.HUELLAS_CANON[c]]
    if ajenos:
        raise SystemExit(f"la matriz no es la del canon 2026-09 en {ajenos}")
    mte_root = args.mte_root or comun.mte_root_defecto()
    if not Path(mte_root).is_dir():
        raise SystemExit(f"MTE_ROOT no es una carpeta: {mte_root}")
    salida = Path(args.salida)
    ruta_xm = (Path(args.precios_escasez) if args.precios_escasez
               else salida / "precios_escasez_xm.csv")

    print("=" * 72)
    print("CONTRAFACTICO: TECHO DE LA BOLSA DEL ANEXO 4 Y COT EN LA "
          "DEDUCCION, punto base")
    print("=" * 72)
    print(f"  matriz     {matriz}")
    print(f"  registros  {registros}")
    print(f"  MTE_ROOT   {mte_root}")
    t0 = time.time()
    datos = evaluador.carga_mte(mte_root, args.cache)
    print(f"  carga del MTE en {time.time() - t0:.1f} s")

    mec, brechas, inst, horas, compuerta = [], [], [], [], []
    tabla_xm = None
    for caso in args.casos:
        ins_r = evaluador.prepara_caso(caso, datos)
        ins_c = evaluador.prepara_caso(caso, datos, cot_en_deduccion=True)
        if ins_r.cot_en_deduccion or not ins_c.cot_en_deduccion:
            raise RuntimeError(f"{caso}: el indicador del COT no casa")
        if not np.array_equal(ins_r.bolsa_cruda, ins_c.bolsa_cruda):
            raise RuntimeError(f"{caso}: el COT movio la bolsa")
        if tabla_xm is None:
            meses = sorted(set(ins_r.mes_m))
            tabla_xm, xm_nueva = lee_o_descarga_xm(ruta_xm, meses)
            techos = {k: dict(zip(tabla_xm["mes"], tabla_xm[f"{k}_cop_kwh"]))
                      for k in ("pon", "pe", "pes")}
            print(f"  precios de escasez de XM: {ruta_xm.name} "
                  f"({'descargado' if xm_nueva else 'leido'}), meses "
                  f"{meses[0]} a {meses[-1]}")
        # La bolsa final de cada variante.
        b_final_real = evaluador.aplica_bolsa(ins_r.bolsa_cruda, 1.0, ins_r.t0)
        crudas, finales = {None: None}, {None: b_final_real}
        for k in ("pon", "pe"):
            top, techo = bolsa_topada(ins_r, techos[k])
            finales[k] = exige_techo_pes_inerte(evaluador, top, ins_r.t0)
            crudas[k] = top
        # Con PrecEsca, la funcion del modelo con level="PE" da lo mismo.
        pe_mod = np.asarray(apply_creg101066_ceiling(
            ins_r.bolsa_cruda, ins_r.t0, level="PE"), float)
        if not np.allclose(pe_mod, finales["pe"], rtol=0, atol=1e-4):
            raise RuntimeError(f"{caso}: min(bolsa, PrecEsca) no casa con "
                               f"apply_creg101066_ceiling(level='PE')")

        res = {}
        base = {}
        for variante in VARIANTES:
            cot, techo = DEF_VARIANTE[variante]
            ins = ins_c if cot else ins_r
            t1 = time.time()
            out, cr = evalua(evaluador, ins, crudas[techo])
            seg = time.time() - t1
            res[variante] = (out, cr, finales[techo])
            if variante == "real":
                canon = cpb.lee_canon(matriz / caso, ins.nombres, registros,
                                      caso, canon_fijo=True)
                pa = {e: np.asarray(v, dtype=float)
                      for e, v in cr.net_benefit_per_agent.items()}
                net = {e: float(v) for e, v in cr.net_benefit.items()}
                filas = cpb.compara(caso, out, pa, net, canon, ins.nombres)
                compuerta.extend(filas)
                malas = [f for f in filas if not f[6]]
                if malas:
                    for f in malas:
                        print(f"  COMPUERTA {caso} DIFIERE {f[1]}: canon "
                              f"{f[2]:,.6f}  evaluado {f[3]:,.6f}")
                    print("CONTRAFACTICO TECHO/COT: la variante real NO "
                          "reproduce el canon; se detiene sin escribir")
                    return 1
            print(f"  {caso:<5} {variante:<16} {seg:5.1f} s  P2P "
                  f"{out['P2P'] / 1e6:9.3f}  C1 {out['C1'] / 1e6:9.3f}  C4 "
                  f"{out['C4'] / 1e6:9.3f}  C5 {out['C5'] / 1e6:9.3f}  col "
                  f"{out['P2P_colectivo'] / 1e6:9.3f} MCOP"
                  + ("  canon al peso" if variante == "real" else ""))

        energias = {}
        for variante in VARIANTES:
            sin, con = PAR_ENERGIA[variante]
            clave = (sin, con)
            if clave not in energias:
                energias[clave] = energia_afectada(
                    res[sin][1], res[con][1], res[sin][2], res[con][2],
                    ins_r.nombres)

        real_out = res["real"][0]
        for variante in VARIANTES:
            out, cr, bfin = res[variante]
            cot, techo = DEF_VARIANTE[variante]
            sin, con = PAR_ENERGIA[variante]
            dp = np.asarray(res[sin][2], float) - np.asarray(res[con][2], float)
            fila = dict(caso=caso, variante=variante, cot_en_deduccion=cot,
                        techo_bolsa={None: "PES (101 066)", "pon": "PrecEscaPon",
                                     "pe": "PrecEsca"}[techo],
                        horas_afectadas=int((dp > 1e-9).sum()))
            for m in MECANISMOS:
                v, r = float(out[m]), float(real_out[m])
                fila[m] = v
                fila[f"d_{m}_COP"] = v - r
                if r == 0:
                    raise ValueError(f"{caso} {m}: beneficio real nulo")
                fila[f"d_{m}_pct"] = 100.0 * (v - r) / abs(r)
            fila.update(energia_kWh=float(out["energia"]),
                        horas_cuantales=int(out["n_cuantal"]))
            fila.update(energias[(sin, con)])
            no_finitos = [k for k, v in fila.items()
                          if isinstance(v, float) and not np.isfinite(v)]
            if no_finitos:
                raise ValueError(f"{caso} {variante}: no finitos en "
                                 f"{no_finitos}")
            mec.append(fila)

            fb = dict(caso=caso, variante=variante)
            for b, (a, c) in BRECHAS.items():
                v = float(out[a]) - float(out[c])
                s = signo(v)
                if variante == "real":
                    base[b] = s
                fb[b] = v
                fb[f"d_{b}_COP"] = v - (float(real_out[a])
                                        - float(real_out[c]))
                fb[f"signo_{b}"] = s
                fb[f"cambia_{b}"] = bool(s != base[b])
            brechas.append(fb)

            for nombre in ins_r.nombres:
                fi = dict(caso=caso, variante=variante, institucion=nombre)
                for b in BRECHAS_INST:
                    v = float(out[f"{b}__{nombre}"])
                    s = signo(v)
                    if variante == "real":
                        base[(nombre, b)] = s
                    fi[b] = v
                    fi[f"d_{b}_COP"] = v - float(real_out[f"{b}__{nombre}"])
                    fi[f"signo_{b}"] = s
                    fi[f"cambia_{b}"] = bool(s != base[(nombre, b)])
                inst.append(fi)

        # Horas afectadas por mes: la bolsa FINAL del modelo (topada al PES)
        # por encima de cada techo, y la energia en ellas.
        exc = np.maximum(ins_r.G - ins_r.D, 0.0).sum(axis=0)
        e_c1 = {}
        for k, var in (("pon", "techo_ponderado"), ("pe", "techo_pe")):
            a = np.asarray(res["real"][1].neto_horario["C1"], float).sum(0)
            b = np.asarray(res[var][1].neto_horario["C1"], float).sum(0)
            dp = b_final_real - finales[k]
            with np.errstate(invalid="ignore", divide="ignore"):
                e_c1[k] = np.where(dp > 1e-9, (a - b) / np.where(
                    dp > 1e-9, dp, 1.0), 0.0)
        cruda = np.asarray(ins_r.bolsa_cruda, float)
        for mes in sorted(set(ins_r.mes_m)):
            sel = ins_r.mes_m == mes
            fh = dict(caso=caso, mes=mes, horas_mes=int(sel.sum()),
                      PrecEscaPon=float(techos["pon"][mes]),
                      PrecEsca=float(techos["pe"][mes]),
                      PES=float(techos["pes"][mes]))
            for k, et in (("pon", "PrecEscaPon"), ("pe", "PrecEsca")):
                h = sel & (b_final_real > finales[k] + 1e-9)
                fh[f"horas_bolsa_sobre_{et}"] = int(h.sum())
                fh[f"excedente_fisico_{et}_kWh"] = float(exc[h].sum())
                fh[f"E_bolsa_C1_{et}_kWh"] = float(e_c1[k][h].sum())
                fh[f"baja_media_precio_{et}_COP_kWh"] = (
                    float((b_final_real - finales[k])[h].mean())
                    if h.any() else 0.0)
            fh["horas_bolsa_cruda_sobre_PES"] = int(
                (sel & (cruda > np.array([techos["pes"][m]
                                          for m in ins_r.mes_m]))).sum())
            horas.append(fh)

    dm = pd.DataFrame(mec)
    db = pd.DataFrame(brechas)
    di = pd.DataFrame(inst)
    dh = pd.DataFrame(horas)
    dc = pd.DataFrame(compuerta, columns=["caso", "comprobacion", "canon",
                                          "evaluado", "dif", "tol", "ok"])
    for nombre, df in (("mecanismos", dm), ("brechas", db),
                       ("por_institucion", di), ("horas_afectadas", dh)):
        num = df.select_dtypes(include=[np.number])
        if not np.all(np.isfinite(num.to_numpy(dtype=float))):
            raise ValueError(f"{nombre}: hay valores no finitos")

    salida.mkdir(parents=True, exist_ok=True)
    if xm_nueva:
        tabla_xm.to_csv(ruta_xm, index=False, float_format="%.5f")
    dm.to_csv(salida / "mecanismos_13casos.csv", index=False,
              float_format="%.6f")
    db.to_csv(salida / "brechas_13casos.csv", index=False,
              float_format="%.6f")
    di.to_csv(salida / "por_institucion.csv", index=False,
              float_format="%.6f")
    dh.to_csv(salida / "horas_afectadas.csv", index=False,
              float_format="%.6f")
    dc.to_csv(salida / "compuerta_real.csv", index=False,
              float_format="%.6f")

    resumen = []
    for variante in VARIANTES[1:]:
        dbv = db[db.variante == variante]
        div = di[di.variante == variante]
        cb = int(dbv[[f"cambia_{b}" for b in BRECHAS]].to_numpy().sum())
        ci = int(div[[f"cambia_{b}" for b in BRECHAS_INST]].to_numpy().sum())
        dmv = dm[dm.variante == variante]
        mx = {m: float(dmv[f"d_{m}_pct"].abs().max()) for m in MECANISMOS}
        resumen.append((variante, cb, ci, mx))

    orden = " ".join([Path(sys.executable).name, "-u",
                      "reformateo/documento/scripts/contrafactico_techo_cot.py"]
                     + (argv if argv is not None else sys.argv[1:]))
    sucio = git("status", "--short", "--", "scenarios", "analysis", "core",
                "gsa_directo", "data", "main_simulation.py")
    import scipy
    with open(salida / "procedencia.txt", "w", encoding="utf-8") as fh:
        fh.write("H-107: techo de la bolsa del Anexo 4 (CREG 101 072) y COT "
                 "en la deduccion (CREG 101 028, art. 5)\n")
        fh.write(f"fecha: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("arbol de trabajo (codigo) con cambios sin commit:\n"
                 + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}"
                 f", scipy {scipy.__version__}, pandas {pd.__version__}\n")
        fh.write(f"orden: {orden}\n")
        fh.write(f"MTE_ROOT: {mte_root}\n")
        fh.write(f"huella del dato: {comun.huella_datos(mte_root)}\n")
        fh.write(f"canon de comparacion: {matriz}\n")
        fh.write("punto: seis factores en 1, mu = 1 (evaluador del GSA "
                 "directo, evalua_comparacion; techo: bolsa_cruda topada; "
                 "COT: prepara_caso(cot_en_deduccion=True))\n")
        fh.write(f"variantes: {' '.join(VARIANTES)}\n")
        fh.write(f"casos: {' '.join(args.casos)}\n")
        fh.write(f"precios de escasez: {ruta_xm.name} "
                 f"({'descargado en esta corrida' if xm_nueva else 'leido'})"
                 "\n")
        fh.write(f"definicion de PrecEsca y fuente: {DEFINICION_PRECESCA}\n")
        fh.write(f"compuerta de la variante real: {len(dc)} comprobaciones, "
                 f"todas al peso\n")
        for variante, cb, ci, mx in resumen:
            fh.write(f"{variante}: brechas de comunidad con signo distinto "
                     f"del real {cb}; por institucion {ci}; mayor |cambio| % "
                     + ", ".join(f"{m} {v:.4f}" for m, v in mx.items())
                     + "\n")
    print(f"\n  escrito en {salida}")
    print(f"  compuerta de la variante real: {len(dc)} comprobaciones, todas "
          f"al peso")
    for variante, cb, ci, mx in resumen:
        print(f"  {variante:<16} signos que cambian: {cb} de comunidad, {ci} "
              f"por institucion; mayor |%| "
              + ", ".join(f"{m} {v:.3f}" for m, v in mx.items()))
    print(f"CONTRAFACTICO TECHO/COT: variante real al peso con el canon en "
          f"{len(args.casos)} casos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
