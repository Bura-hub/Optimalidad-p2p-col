"""
cifras_datos_cap04.py — Las cifras descriptivas del dato que cita el capítulo 4
de la tesis (Datos y tratamiento) y que no están ya en el canon (C-229).
===============================================================================
Decisión del controlador, ronda 2 del capítulo 4 (2026-09-28): toda cifra
descriptiva del dato que el capítulo cite y que no esté en `CANON.md` sale de
este guion. Se calculan, sin simular nada, con:

- las funciones del propio cargador (`data/preprocessing.py`,
  `data/xm_data_loader.py`) sobre `MTE_ROOT` (por defecto
  `MedicionesMTE_v3/`), con y sin el guardia físico;
- el almacén de E0 (y el de los trece casos, para la capacidad escalada) de la
  matriz canónica, `SALIDAS_SERVIDOR/entrega_matriz_reposo_2026-09-19/
  SALIDAS_SERVIDOR/matriz_reposo/<caso>/almacen/m1/agentes`;
- los CSV de `data/` (tarifas de ASC y de CEDENAR, costos del mercado
  mayorista, bolsa, precios de escasez, contratos de XM);
- para H-92, la caché de bolsa y la tabla de techos anteriores a C-200, leídas
  del historial de git (`f21205e^` y `3fdff5e^`).

Compuertas, antes de escribir nada:
1. La demanda y la generación que devuelve `build_demand_generation` sobre
   `MTE_ROOT` reproducen, institución por institución, las sumas de la tabla
   `agentes` del almacén de E0 (a 0,5 kWh: el almacén guarda en float32).
2. Las horas sin muestra que cuenta este guion son exactamente los NaN de
   `_read_single_meter` con el guardia, y la generación extendida de Udenar es
   exactamente la de `_read_ems_generation`.
3. La bolsa del horizonte con el techo coincide con `get_pi_bolsa` sobre la
   caché canónica.

Falla en voz alta: ningún `except` que trague, ningún NaN rellenado, y una
cifra no finita o una clave repetida es un error.

Escribe en SALIDAS_SERVIDOR/cifras_datos_2026-09-28/:

    cifras.csv        clave, valor, unidad, definicion, fuente
    procedencia.txt   commit, estado del árbol, versiones, orden, MTE_ROOT y
                      huella del dato

No escribe en `outputs/` ni en `graficas/`.

    PYTHONUNBUFFERED=1 python -u reformateo/documento/scripts/cifras_datos_cap04.py

Actividades 1.0 y 3.1.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import io
import math
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from data import preprocessing as P                         # noqa: E402
from data.xm_data_loader import (AGENTS, COL_DEMAND, INVERTER_FOLDER,  # noqa: E402
                                 METER_FOLDER, T_END, T_START, _clean,
                                 _read_one)
from data.xm_prices import (XM_MONTHLY_REAL, _lee_csv_precios,  # noqa: E402
                            apply_creg101066_ceiling, get_pi_bolsa,
                            load_xm_prices)
from data.precios_contratos import precio_horario            # noqa: E402
from data.capacidad_instalada import KWP_POR_PLANTA          # noqa: E402
from gsa_directo.comun import huella_datos, mte_root_defecto  # noqa: E402

SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "cifras_datos_2026-09-28"
MATRIZ = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
          / "SALIDAS_SERVIDOR" / "matriz_reposo")
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
F_ALM = "almacén E0, tabla agentes (matriz canónica)"
F_CARG = "funciones del cargador sobre MTE_ROOT"
F_TAR = "data/tarifas_asc_mensual.csv y data/tarifas_cedenar_mensual.csv"
F_BOLSA = "data/precios_bolsa_xm_api.csv y data/precios_escasez_creg.csv"

# El tercer medidor de cada institución: la segunda frontera, retirada por
# D10. Solo se lee para medir por qué se retiró (H-77).
TERCER_MEDIDOR = {
    "Udenar": "Bloque Sur - Medidor 3 - electricMeter",
    "Mariana": "Medidor 3 - Alvernia - electricMeter",
    "UCC": "Medidor 3 - UCC - electricMeter",
    "HUDN": "Medidor 3 - HUDN - electricMeter",
    "Cesmag": "Medidor 3 - Cesmag - electricMeter",
}
# Los tres medidores de la frontera cuyo contador está a la escala de la
# potencia (H-16).
CONTADOR_BIEN_ESCALADO = ("UCC", "Udenar", "HUDN")
COLS_CONT = ["date", "totalActivePower",
             "importedActivePowerLow", "importedActivePowerHigh",
             "exportedActivePowerLow", "exportedActivePowerHigh"]

FILAS: list[dict] = []


class CifraError(RuntimeError):
    pass


def pon(clave: str, valor, unidad: str, definicion: str, fuente: str) -> None:
    """Añade una cifra. Falla si no es finita o si la clave ya existe."""
    if any(f["clave"] == clave for f in FILAS):
        raise CifraError(f"clave repetida: {clave}")
    if isinstance(valor, (int, float, np.integer, np.floating)):
        v = float(valor)
        if not math.isfinite(v):
            raise CifraError(f"{clave}: valor no finito {valor!r}")
        valor = int(valor) if float(v).is_integer() and isinstance(
            valor, (int, np.integer)) else v
    elif not isinstance(valor, str) or not valor:
        raise CifraError(f"{clave}: valor vacío o de tipo {type(valor)}")
    FILAS.append(dict(clave=clave, valor=valor, unidad=unidad,
                      definicion=definicion, fuente=fuente))


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise CifraError(msg)


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                       text=True, check=True)
    return r.stdout.rstrip("\n")


def git_bytes(ref_path: str) -> bytes:
    r = subprocess.run(["git", "show", ref_path], cwd=RAIZ,
                       capture_output=True, check=True)
    return r.stdout


# ── El eje y las carpetas ───────────────────────────────────────────────────
IDX = pd.date_range(T_START, T_END, freq="1h", inclusive="left")
T0, T1 = pd.Timestamp(T_START), pd.Timestamp(T_END)


def carpeta_medidor(root: Path, inst: str, sub: str) -> Path:
    adir = P._find_subdir(root, inst)
    mroot = P._find_subdir(adir, METER_FOLDER[inst])
    d = P._find_subdir(mroot, sub)
    exige(d is not None, f"no está la carpeta del medidor {inst}/{sub}")
    return d


def carpeta_inversor(root: Path, inst: str, sub: str) -> Path:
    adir = P._find_subdir(root, inst)
    iroot = P._find_subdir(adir, INVERTER_FOLDER[inst])
    d = P._find_subdir(iroot, sub)
    exige(d is not None, f"no está la carpeta del inversor {inst}/{sub}")
    return d


_MEMO: dict = {}


def muestras(folder: Path, col: str) -> pd.Series:
    """Todas las muestras de un equipo, fundidas como las funde el cargador
    (duplicados dentro del fichero y costuras entre ficheros, por la media)."""
    k = (str(folder), col)
    if k not in _MEMO:
        _MEMO[k] = _muestras(folder, col)
    return _MEMO[k]


def _muestras(folder: Path, col: str) -> pd.Series:
    partes = [s for s in (_read_one(p, col) for p in sorted(folder.rglob("*.csv")))
              if s is not None and len(s) > 0]
    exige(len(partes) > 0, f"sin muestras de {col} en {folder}")
    return pd.concat(partes, axis=1).mean(axis=1).sort_index()


def en_horizonte(s: pd.Series) -> pd.Series:
    return s[(s.index >= T0) & (s.index < T1)]


def por_hora(s: pd.Series) -> pd.Series:
    return s.resample("1h").count().reindex(IDX, fill_value=0).astype(int)


def primera_hora(s: pd.Series) -> str:
    v = s.dropna()
    exige(len(v) > 0, "serie vacía")
    return v.index[0].floor("1h").strftime("%Y-%m-%d %H:%M")


# ── 1. Los medidores de la frontera ─────────────────────────────────────────
def medidores(root: Path) -> dict:
    """Horas incompletas, sin muestra, del guardia, negativas, recortes y
    cascada, por institución, sobre la lectura del medidor 1."""
    out = {}
    tot = dict(inc_c=0, inc_m=0, una=0, con_dato=0, p21=0, p21_netos=0,
               sin_c_netos=0, sin_m_netos=0, vac=0, g_mues=0, g_horas=0,
               cero_netos=0, gen_devuelta=0)
    for inst in AGENTS:
        cfg = P.DEMAND_METER_CONFIG[inst]
        kind = cfg["kind"]
        carp = carpeta_medidor(root, inst, cfg["subfolder"])
        todo = muestras(carp, COL_DEMAND)
        pon(f"primera_hora_medidor__{inst}", primera_hora(todo), "fecha",
            "primera hora con alguna muestra del medidor 1, desde el inicio "
            "de la entrega", F_CARG)
        h = en_horizonte(todo)
        marca = P._guardia_fisico(carp, verbose=False)
        exige(marca is not None, f"el guardia no tiene canales en {inst}")
        m_h = en_horizonte(marca)
        fuera = marca.reindex(h.index)
        exige(not fuera.isna().any(),
              f"{inst}: hay muestras de potencia sin fila del guardia")
        hg = h[~fuera.astype(bool).values]
        cnt_c, cnt_g = por_hora(h), por_hora(hg)

        # Compuerta 2: los NaN del cargador son las horas sin muestra.
        d_carg = P._read_single_meter(carp, COL_DEMAND, IDX, guardia=True,
                                      etiqueta=inst)
        d_crudo = P._read_single_meter(carp, COL_DEMAND, IDX, guardia=False)
        exige(bool((d_carg.isna().values == (cnt_g == 0).values).all()),
              f"{inst}: las horas sin muestra no casan con el cargador")

        inc_c = int(((cnt_c > 0) & (cnt_c < 30)).sum())
        inc_m = int(((cnt_g > 0) & (cnt_g < 30)).sum())
        sin_c, sin_m = int((cnt_c == 0).sum()), int((cnt_g == 0).sum())
        vac = int(((cnt_c > 0) & (cnt_g == 0)).sum())
        p21 = int(((cnt_c > 0) & (cnt_c < 23)).sum())
        pon(f"incompletas_crudo__{inst}", inc_c, "h",
            "horas del horizonte con 1 a 29 muestras en la lectura cruda", F_CARG)
        pon(f"incompletas_modelo__{inst}", inc_m, "h",
            "horas con 1 a 29 muestras después del guardia: las que la serie "
            "del modelo estima por la media", F_CARG)
        pon(f"sin_muestra_crudo__{inst}", sin_c, "h",
            "horas sin ninguna muestra en la lectura cruda", F_CARG)
        pon(f"sin_muestra_modelo__{inst}", sin_m, "h",
            "horas sin ninguna muestra después del guardia", F_CARG)
        pon(f"vaciadas_guardia__{inst}", vac, "h",
            "horas con muestras que el guardia deja sin ninguna", F_CARG)
        s_g = int(m_h.sum())
        h_g = int(m_h[m_h.astype(bool)].index.floor("1h").nunique())
        pon(f"guardia_muestras__{inst}", s_g, "muestras",
            "muestras del horizonte que retira el guardia físico", F_CARG)
        pon(f"guardia_horas__{inst}", h_g, "h",
            "horas del horizonte con alguna muestra retirada por el guardia", F_CARG)
        neg_c, neg_g = int((d_crudo < 0).sum()), int((d_carg < 0).sum())
        pon(f"negativas_crudo__{inst}", neg_c, "h",
            "horas con lectura media negativa, sin guardia", F_CARG)
        pon(f"negativas_modelo__{inst}", neg_g, "h",
            "horas con lectura media negativa, con guardia", F_CARG)
        # El paso del registro, sobre todas las muestras del equipo, como
        # lo calcula el guardia.
        fa = muestras(carp, "activePowerPhaseA")
        paso = P._paso_registro(pd.DataFrame({"activePowerPhaseA": fa}))
        exige(math.isfinite(paso) and paso > 0, f"{inst}: paso no finito")
        pon(f"paso_registro__{inst}", round(paso, 4), "kW",
            "salto menor entre valores distintos de la potencia de fase A "
            "(mediana), sobre todas las muestras del equipo", F_CARG)
        # La media frente a la suma fija de dos minutos, sobre la lectura
        # cruda en las horas con dato (H-18).
        med = h.resample("1h").mean().reindex(IDX)
        ok = cnt_c > 0
        a = float(med[ok].sum())
        b = float((med[ok] * cnt_c[ok] / 30.0).sum())
        pon(f"suma_fija_menos_media_pct__{inst}", round(100 * (b - a) / a, 3),
            "%", "energía de la suma de muestras por dos minutos menos la de "
            "la media horaria, sobre la media, en las horas con dato (lectura "
            "cruda)", F_CARG)

        tot["inc_c"] += inc_c
        tot["inc_m"] += inc_m
        tot["una"] += int((cnt_c == 29).sum())
        tot["con_dato"] += int((cnt_c > 0).sum())
        tot["p21"] += p21
        tot["vac"] += vac
        tot["g_mues"] += s_g
        tot["g_horas"] += h_g

        res = dict(cnt_c=cnt_c, med=med, d_carg=d_carg, kind=kind)
        adir = P._find_subdir(root, inst)
        if kind in ("net", "net_partial"):
            tot["p21_netos"] += p21
            tot["sin_c_netos"] += sin_c
            tot["sin_m_netos"] += sin_m
            g_rec = P._sum_inverter_reconstruction(
                adir, P.RECONSTRUCTION_INVERTERS_CONFIG[inst], IDX).fillna(0.0)
            s = d_carg.fillna(0.0) + g_rec
            rec = s < 0
            pon(f"recorte_horas__{inst}", int(rec.sum()), "h",
                "horas en que la lectura más la generación devuelta sale "
                "negativa y se lleva a cero (con guardia)", F_CARG)
            pon(f"recorte_kWh__{inst}", round(float(-s[rec].sum()), 1), "kWh",
                "energía que quita ese recorte", F_CARG)
            if rec.any():
                pon(f"recorte_ultima_hora__{inst}",
                    s[rec].index[-1].strftime("%Y-%m-%d %H:%M"), "fecha",
                    "última hora con recorte", F_CARG)
            sin_con_g = int((d_carg.isna() & (g_rec > 0)).sum())
            sin_cero = int((d_carg.isna() & (g_rec <= 0)).sum())
            tot["gen_devuelta"] += sin_con_g
            tot["cero_netos"] += sin_cero
            pon(f"sin_muestra_modelo_cero__{inst}", sin_cero, "h",
                "horas sin muestra que entran con demanda cero", F_CARG)
            pon(f"sin_muestra_modelo_gen_devuelta__{inst}", sin_con_g, "h",
                "horas sin muestra que entran con demanda igual a la "
                "generación devuelta", F_CARG)
            if inst == "Mariana":
                # El fallo de tensión del 29 de agosto de 2025 (ADR 0045).
                v = (IDX >= pd.Timestamp("2025-08-29 00:00")) & (IDX < pd.Timestamp("2025-08-30 00:00"))
                d_fin = s.clip(lower=0.0)
                pon("fallo_mariana_horas_demanda_cero", int((d_fin[v] == 0).sum()), "h",
                    "horas del 29 de agosto de 2025 en que la demanda de Mariana que "
                    "recibe el modelo es cero", F_CARG)
                pon("fallo_mariana_negativas_crudo", int((d_crudo[v] < 0).sum()), "h",
                    "horas negativas de Mariana el 29 de agosto, sin guardia", F_CARG)
                pon("fallo_mariana_negativas_modelo", int((d_carg[v] < 0).sum()), "h",
                    "horas negativas de Mariana el 29 de agosto, con guardia", F_CARG)
            if inst == "Udenar":
                arranque = pd.Timestamp("2025-09-03 18:00")
                pon("negativas_tras_suma_desde_arranque_MTE__Udenar",
                    int((s[s.index >= arranque] < 0).sum()), "h",
                    "horas negativas tras sumar los tres inversores desde que "
                    "registra el del proyecto", F_CARG)
        else:
            d_rec = d_carg.clip(lower=0.0)
            na = d_rec.isna()
            s1 = d_rec.interpolate(method="time", limit=3)
            s2 = s1.ffill(limit=24).bfill(limit=24)
            exige(bool(np.allclose(s2.fillna(0.0).values,
                                   _clean(d_rec).values, equal_nan=False)),
                  f"{inst}: la cascada instrumentada no reproduce _clean")
            rach = (na != na.shift()).cumsum()
            pon(f"cascada_huecos__{inst}", int(na.sum()), "h",
                "horas vacías que recibe la cascada de huecos", F_CARG)
            pon(f"cascada_interpoladas__{inst}", int((na & s1.notna()).sum()),
                "h", "horas rellenadas por interpolación (hasta 3 h)", F_CARG)
            pon(f"cascada_arrastradas__{inst}",
                int((s1.isna() & s2.notna()).sum()), "h",
                "horas rellenadas por arrastre (hasta 24 h por lado)", F_CARG)
            pon(f"cascada_cero__{inst}", int(s2.isna().sum()), "h",
                "horas que llegan al cero de la cascada", F_CARG)
            pon(f"cascada_hueco_max__{inst}", int(na.groupby(rach).sum().max()),
                "h", "hueco más largo que recibe la cascada", F_CARG)
        out[inst] = res

    pon("incompletas_crudo__total", tot["inc_c"], "h",
        "horas incompletas de los cinco medidores, lectura cruda", F_CARG)
    pon("incompletas_modelo__total", tot["inc_m"], "h",
        "horas estimadas por la media en la serie del modelo", F_CARG)
    pon("incompletas_una_muestra__total", tot["una"], "h",
        "horas incompletas a las que les falta una sola muestra (cruda)", F_CARG)
    pon("horas_con_dato_crudo__total", tot["con_dato"], "h",
        "horas-medidor del horizonte con alguna muestra (cruda)", F_CARG)
    pon("incompletas_sobre_con_dato_pct", round(100 * tot["inc_c"] / tot["con_dato"], 2),
        "%", "horas incompletas sobre horas con dato (cruda)", F_CARG)
    pon("p21_menos_de_23__total", tot["p21"], "h",
        "horas con 1 a 22 muestras (umbral P-21), cruda", F_CARG)
    pon("p21_menos_de_23_pct", round(100 * tot["p21"] / tot["con_dato"], 2), "%",
        "las anteriores sobre las horas con dato", F_CARG)
    pon("p21_menos_de_23__netos", tot["p21_netos"], "h",
        "las del umbral P-21 que caen en los tres medidores netos", F_CARG)
    pon("sin_muestra_crudo__netos", tot["sin_c_netos"], "h",
        "horas sin muestra en los tres medidores netos, cruda", F_CARG)
    pon("sin_muestra_modelo__netos", tot["sin_m_netos"], "h",
        "horas sin muestra en los tres medidores netos, serie del modelo", F_CARG)
    pon("sin_muestra_modelo_cero__netos", tot["cero_netos"], "h",
        "de ellas, las que entran con demanda cero", F_CARG)
    pon("sin_muestra_modelo_gen_devuelta__netos", tot["gen_devuelta"], "h",
        "de ellas, las que entran igual a la generación devuelta", F_CARG)
    pon("vaciadas_guardia__total", tot["vac"], "h",
        "horas que el guardia deja sin muestra en los cinco medidores", F_CARG)
    pon("guardia_muestras__total", tot["g_mues"], "muestras",
        "muestras retiradas por el guardia en el horizonte", F_CARG)
    pon("guardia_horas__total", tot["g_horas"], "h",
        "horas con alguna muestra retirada por el guardia", F_CARG)
    exige(tot["sin_m_netos"] == tot["cero_netos"] + tot["gen_devuelta"],
          "las horas sin muestra de los netos no suman")
    return out


def cobertura_sesgada(res: dict) -> None:
    """H-18: qué horas fallan (tasas por franja y horas simultáneas), en la
    lectura cruda."""
    inc = pd.DataFrame({i: (r["cnt_c"] > 0) & (r["cnt_c"] < 30) for i, r in res.items()})
    dato = pd.DataFrame({i: r["cnt_c"] > 0 for i, r in res.items()})
    hh = IDX.hour
    dia = (hh >= 8) & (hh <= 17)
    mad = hh <= 5
    pon("incompletas_tasa_8a17_pct",
        round(100 * inc[dia].values.sum() / dato[dia].values.sum(), 2), "%",
        "horas incompletas sobre horas con dato, de las 8:00 a las 17:59 (cruda)", F_CARG)
    pon("incompletas_tasa_0a5_pct",
        round(100 * inc[mad].values.sum() / dato[mad].values.sum(), 2), "%",
        "lo mismo de las 0:00 a las 5:59 (cruda)", F_CARG)
    pon("incompletas_cinco_a_la_vez", int(inc.all(axis=1).sum()), "h",
        "horas con los cinco medidores incompletos a la vez (cruda)", F_CARG)


def sesgo_ventana(root: Path) -> None:
    """H-18: la ventana observada de cada hora incompleta aplicada a horas
    completas comparables (misma institución, hora del día y mes). El sesgo
    del estimador de la media es la diferencia media entre la media de la
    ventana y la de la hora entera. Lectura cruda, sin guardia."""
    sesgo_total, demanda_total = 0.0, 0.0
    n_juzgadas = 0
    for inst in AGENTS:
        carp = carpeta_medidor(root, inst, P.DEMAND_METER_CONFIG[inst]["subfolder"])
        h = en_horizonte(muestras(carp, COL_DEMAND))
        df = pd.DataFrame({"v": h.values}, index=h.index)
        df["hora"] = df.index.floor("1h")
        seg = (df.index.to_series() - df["hora"]).dt.total_seconds().to_numpy()
        df["ranura"] = (seg // 120).astype(int)
        df = df.drop_duplicates(["hora", "ranura"])
        cnt = df.groupby("hora")["v"].size()
        demanda_total += float(df.groupby("hora")["v"].mean().sum())
        comp = cnt[cnt == 30].index
        mat = (df[df["hora"].isin(comp)]
               .pivot(index="hora", columns="ranura", values="v"))
        exige(mat.shape[1] == 30 and not mat.isna().any().any(),
              f"{inst}: horas completas con ranuras incompletas")
        media_hora = mat.mean(axis=1)
        h_m, m_m = mat.index.hour, mat.index.month
        incs = cnt[(cnt > 0) & (cnt < 30)].index
        ranuras_por_hora = df[df["hora"].isin(incs)].groupby("hora")["ranura"].apply(
            lambda x: sorted(x.unique()))
        for hr in incs:
            ranuras = ranuras_por_hora.loc[hr]
            cmp_ = mat.index[(h_m == hr.hour) & (m_m == hr.month)]
            if len(cmp_) == 0:
                raise CifraError(f"{inst} {hr}: sin horas completas comparables")
            dif = mat.loc[cmp_, ranuras].mean(axis=1) - media_hora.loc[cmp_]
            sesgo_total += float(dif.mean())
            n_juzgadas += 1
    pon("sesgo_ventana_horas", n_juzgadas, "h",
        "horas incompletas juzgadas con su ventana sobre horas completas "
        "comparables (cruda)", F_CARG)
    pon("sesgo_ventana_pct_demanda", round(100 * sesgo_total / demanda_total, 5), "%",
        "suma del sesgo estimado de la media en las horas incompletas, sobre la "
        "demanda del horizonte de los cinco medidores (lectura cruda)", F_CARG)


def contadores(root: Path) -> None:
    """H-16 (escala del contador frente a la potencia), el bloque de Mariana
    del ADR 0045 y los cortes de telemetría de H-18."""
    razones = {}
    for inst in AGENTS:
        carp = carpeta_medidor(root, inst, P.DEMAND_METER_CONFIG[inst]["subfolder"])
        partes = [pd.read_csv(p, usecols=COLS_CONT, low_memory=False)
                  for p in sorted(carp.rglob("*.csv"))]
        d = pd.concat(partes, ignore_index=True)
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        exige(int(d["date"].isna().sum()) == 0, f"{inst}: fechas ilegibles")
        d = d.groupby("date").mean(numeric_only=True).sort_index()
        d = d[(d.index >= T0) & (d.index <= T1)]
        d["neto"] = ((d["importedActivePowerHigh"] - d["exportedActivePowerHigh"]) * 1e4
                     + (d["importedActivePowerLow"] - d["exportedActivePowerLow"]))
        marcas = pd.date_range(T_START, T_END, freq="1h")
        c = d["neto"].reindex(marcas)
        avance = (c.shift(-1) - c).iloc[:-1]
        g = d["totalActivePower"].groupby(d.index.floor("1h"))
        media = g.mean().reindex(IDX)
        n = g.size().reindex(IDX, fill_value=0)
        ok = avance.notna().values & media.notna().values & (n == 30).values
        r = float(media[ok].sum() / avance[ok].sum())
        razones[inst] = r
        pon(f"razon_potencia_contador__{inst}", round(r, 3), "adimensional",
            "energía de la media horaria de potencia sobre el avance del contador "
            "neto entre marcas de hora, en horas completas", F_CARG)
        pon(f"razon_potencia_contador_horas__{inst}", int(ok.sum()), "h",
            "horas completas con contador en las dos marcas", F_CARG)
        if inst == "Mariana":
            t_a, t_b = pd.Timestamp("2025-04-24 06:00"), pd.Timestamp("2025-04-24 12:00")
            cuentas = float(c.loc[t_b] - c.loc[t_a])
            e_pot = float(media.loc[t_a:t_b - pd.Timedelta("1h")].sum())
            pon("bloque_mariana_cuentas", cuentas, "cuentas",
                "avance del contador neto de Mariana del 2025-04-24 entre las marcas de 06:00 y 12:00 (las horas de 6 a 11)", F_CARG)
            pon("bloque_mariana_contador_kWh", round(cuentas * r, 1), "kWh",
                "ese avance por la razón medida de Mariana", F_CARG)
            pon("bloque_mariana_potencia_kWh", round(e_pot, 1), "kWh",
                "suma de las medias horarias de potencia de las horas de 6 a 11", F_CARG)
            pon("bloque_mariana_dif_pct",
                round(100 * abs(e_pot - cuentas * r) / e_pot, 1), "%",
                "diferencia entre las dos, sobre la de potencia", F_CARG)
        if inst in CONTADOR_BIEN_ESCALADO:
            t = d.index.to_series()
            dt = (t.shift(-1) - t).dt.total_seconds() / 3600.0
            p0 = d["totalActivePower"]
            adv = d["neto"].shift(-1) - d["neto"]
            sel = ((dt > 2.5 / 60) & (dt <= 1.0) & adv.notna() & p0.notna()
                   & p0.shift(-1).notna() & (t.shift(-1) < T1)).values
            razones[f"_cortes_{inst}"] = (int(sel.sum()), float(adv[sel].sum()),
                                          float((p0 * dt)[sel].sum()),
                                          float((p0 * 2 / 60)[sel].sum()))
    n = sum(v[0] for k, v in razones.items() if k.startswith("_cortes_"))
    cont = sum(v[1] for k, v in razones.items() if k.startswith("_cortes_"))
    sig = sum(v[2] for k, v in razones.items() if k.startswith("_cortes_"))
    nada = sum(v[3] for k, v in razones.items() if k.startswith("_cortes_"))
    defc = ("cortes de telemetría de hasta una hora (dos muestras consecutivas "
            "separadas más de 2,5 min) en los medidores de UCC, Udenar y HUDN")
    pon("cortes_n", n, "cortes", defc, F_CARG)
    pon("cortes_contador_kWh", round(cont, 1), "kWh",
        "avance del contador neto a través de esos cortes", F_CARG)
    pon("cortes_siguio_consumiendo_kWh", round(sig, 1), "kWh",
        "potencia de la última muestra por la duración del corte", F_CARG)
    pon("cortes_sin_energia_kWh", round(nada, 1), "kWh",
        "solo el rectángulo de dos minutos de la última muestra", F_CARG)


# ── 2. La generación ────────────────────────────────────────────────────────
def generacion(root: Path) -> dict:
    out = {}
    diurnas_tot = 0
    for inst in AGENTS:
        des = P.EMS_INVERTER_CONFIG[inst]
        carp = carpeta_inversor(root, inst, des)
        pon(f"primera_hora_inversor__{inst}", primera_hora(muestras(carp, "acPower")),
            "fecha", "primera hora con alguna muestra del inversor designado", F_CARG)
        g = P._read_single_inverter(carp, IDX)
        ref = P.EMS_INVERTER_BACKFILL_CONFIG.get(inst)
        g_ext = g.copy()
        if ref is not None:
            r = P._read_single_inverter(carpeta_inversor(root, inst, ref), IDX)
            sol = g.notna() & r.notna()
            k = float(g[sol].sum() / r[sol].sum())
            falta = g.isna()
            g_ext[falta] = k * r[falta]
            arranque = g.first_valid_index()
            rec_e = float((k * r[falta]).sum())
            total = float(g_ext.fillna(0.0).sum())
            pon("udenar_factor_extension", round(k, 4), "adimensional",
                "razón de energías del inversor del proyecto y del primer Fronius "
                "en el solape", F_CARG)
            pon("udenar_solape_horas", int(sol.sum()), "h",
                "horas en que registran los dos", F_CARG)
            pon("udenar_solape_correlacion", round(float(np.corrcoef(g[sol], r[sol])[0, 1]), 4),
                "adimensional", "correlación de las dos series en el solape", F_CARG)
            pon("udenar_arranque_MTE", arranque.strftime("%Y-%m-%d %H:%M"), "fecha",
                "primera hora del horizonte con dato del inversor del proyecto", F_CARG)
            pon("udenar_horas_con_MTE", int(g.notna().sum()), "h",
                "horas del horizonte con dato del inversor del proyecto", F_CARG)
            pon("udenar_horas_sin_MTE", int(falta.sum()), "h",
                "horas sin dato del inversor del proyecto", F_CARG)
            pon("udenar_horas_sin_MTE_antes", int((falta & (IDX < arranque)).sum()), "h",
                "de ellas, anteriores a su arranque", F_CARG)
            pon("udenar_horas_sin_MTE_despues", int((falta & (IDX >= arranque)).sum()), "h",
                "de ellas, posteriores a su arranque", F_CARG)
            pon("udenar_energia_sin_MTE_despues_kWh",
                round(float((k * r[falta & (IDX >= arranque)]).sum()), 3), "kWh",
                "energía extendida en las horas posteriores al arranque", F_CARG)
            pon("udenar_horas_sin_ninguno", int((falta & r.isna()).sum()), "h",
                "horas sin dato de ninguno de los dos, que quedan en cero", F_CARG)
            pon("udenar_horas_reconstruidas_pct", round(100 * falta.sum() / len(IDX), 1), "%",
                "horas sin dato del inversor del proyecto sobre las del horizonte", F_CARG)
            pon("udenar_energia_reconstruida_kWh", round(rec_e, 1), "kWh",
                "energía de Udenar tomada del Fronius escalado", F_CARG)
            pon("udenar_energia_reconstruida_pct", round(100 * rec_e / total, 1), "%",
                "esa energía sobre la generación de Udenar del horizonte", F_CARG)
        g_mod = P._read_ems_generation(P._find_subdir(P._find_subdir(root, inst),
                                                      INVERTER_FOLDER[inst]),
                                       des, ref, IDX, verbose=False)
        exige(bool(np.allclose(g_ext.fillna(0.0).values, g_mod.values)),
              f"{inst}: la generación extendida no reproduce el cargador")
        hh = IDX.hour
        diurnas = int((g_ext.isna() & (hh >= 6) & (hh <= 18)).sum())
        diurnas_tot += diurnas
        pon(f"generacion_sin_dato_diurna__{inst}", diurnas, "h",
            "horas de 06:00 a 18:59 sin dato del inversor (ya extendido), que "
            "entran en cero", F_CARG)
        out[inst] = g_mod
    pon("generacion_sin_dato_diurna__total", diurnas_tot, "h",
        "las anteriores, en las cinco instituciones", F_CARG)
    return out


def tercer_medidor(root: Path, D: np.ndarray) -> None:
    """La segunda frontera, retirada (D10): cuántas veces menor es la demanda
    del tercer medidor que la del primero."""
    razones = []
    for n, inst in enumerate(AGENTS):
        carp = carpeta_medidor(root, inst, TERCER_MEDIDOR[inst])
        d3 = _clean(P._read_single_meter(carp, COL_DEMAND, IDX, guardia=True,
                                         etiqueta=inst).clip(lower=0.0))
        e3 = float(d3.sum())
        exige(e3 > 0, f"{inst}: tercer medidor sin energía")
        pon(f"tercer_medidor_kWh__{inst}", round(e3, 1), "kWh",
            "demanda del tercer medidor en el horizonte (bruta, con guardia y cascada)",
            F_CARG)
        pon(f"tercer_medidor_media_kW__{inst}", round(e3 / len(IDX), 2), "kW",
            "su media horaria", F_CARG)
        r = float(D[n].sum()) / e3
        pon(f"tercer_medidor_razon__{inst}", round(r, 1), "adimensional",
            "demanda del medidor 1 sobre la del tercer medidor", F_CARG)
        if inst != "Mariana":
            razones.append(r)
    pon("tercer_medidor_razon_min_sin_mariana", round(min(razones), 1), "adimensional",
        "menor razón entre las cuatro instituciones distintas de Mariana", F_CARG)
    pon("tercer_medidor_razon_max_sin_mariana", round(max(razones), 1), "adimensional",
        "mayor razón entre las cuatro instituciones distintas de Mariana", F_CARG)


# ── 3. El almacén de E0 y de los trece casos ────────────────────────────────
def almacen(D: np.ndarray, G: np.ndarray) -> None:
    df = pd.read_parquet(MATRIZ / "E0" / "almacen" / "m1" / "agentes")
    exige(len(df) == 5 * len(IDX), "el almacén de E0 no tiene 5 × 6 144 filas")
    s = df.groupby("agente")[["demanda", "generacion", "sobrante"]].sum()
    # Compuerta 1: el cargador reproduce el almacén, hora a hora (el almacén
    # guarda en float32; 1e-3 kW de holgura) y en las sumas.
    for col, M in (("demanda", D), ("generacion", G)):
        piv = df.pivot(index="hora", columns="agente", values=col).sort_index()
        exige(len(piv) == len(IDX), f"el almacén de E0 no tiene {len(IDX)} horas de {col}")
        for n, inst in enumerate(AGENTS):
            dif = float(np.max(np.abs(piv[inst].to_numpy(float) - M[n])))
            exige(dif < 1e-3, f"{inst}: la {col} del cargador difiere del almacén "
                              f"hora a hora en {dif:.3g} kW")
    for n, inst in enumerate(AGENTS):
        exige(abs(float(D[n].sum()) - float(s.loc[inst, "demanda"])) < 0.5,
              f"{inst}: la demanda del cargador no reproduce el almacén")
        exige(abs(float(G[n].sum()) - float(s.loc[inst, "generacion"])) < 0.5,
              f"{inst}: la generación del cargador no reproduce el almacén")
    T = len(IDX)
    pon("horizonte_horas", T, "h", "horas del horizonte", "almacén E0")
    pon("horizonte_dias", T // 24, "días", "días del horizonte", "almacén E0")
    pon("horizonte_inicio", str(pd.Timestamp(df["fecha"].min())), "fecha",
        "primera hora", "almacén E0")
    pon("horizonte_fin", str(pd.Timestamp(df["fecha"].max())), "fecha",
        "última hora", "almacén E0")
    capacidad = KWP_POR_PLANTA * T
    for inst in AGENTS + ["comunidad"]:
        if inst == "comunidad":
            d_, g_, cap = float(s.demanda.sum()), float(s.generacion.sum()), capacidad * 5
        else:
            d_, g_, cap = float(s.loc[inst, "demanda"]), float(s.loc[inst, "generacion"]), capacidad
        pon(f"demanda_kWh__{inst}", round(d_, 1), "kWh", "demanda del horizonte", F_ALM)
        pon(f"generacion_kWh__{inst}", round(g_, 1), "kWh", "generación del horizonte", F_ALM)
        pon(f"demanda_media_kW__{inst}", round(d_ / T, 2), "kW", "demanda media", F_ALM)
        pon(f"generacion_media_kW__{inst}", round(g_ / T, 2), "kW", "generación media", F_ALM)
        pon(f"generacion_sobre_demanda__{inst}", round(g_ / d_, 3), "adimensional",
            "generación sobre demanda del circuito medido", F_ALM)
        pon(f"factor_capacidad__{inst}", round(g_ / cap, 3), "adimensional",
            "energía de corriente alterna sobre la placa (17,55 kWp) por 6 144 h",
            F_ALM + "; data/capacidad_instalada.py")
    sob = float(s.sobrante.sum())
    pon("excedente_propio_kWh__comunidad", round(sob, 1), "kWh",
        "generación por encima de la propia demanda, sumada sobre las cinco", F_ALM)
    pon("excedente_propio_parte_udenar_pct", round(float(100 * s.loc["Udenar", "sobrante"] / sob), 1),
        "%", "parte de Udenar en ese excedente", F_ALM)
    h = df.groupby("hora")[["generacion", "sobrante", "demanda"]].sum()
    pon("horas_con_generacion__comunidad", int((h.generacion > 0).sum()), "h",
        "horas con generación comunitaria positiva", F_ALM)
    pon("horas_con_excedente", int((h.sobrante > 1e-9).sum()), "h",
        "horas en que alguna institución tiene excedente", F_ALM)
    df["finde"] = pd.to_datetime(df["fecha"]).dt.dayofweek >= 5
    hf = df.groupby(["hora", "finde"])[["demanda", "generacion"]].sum().reset_index()
    m = hf.groupby("finde")[["demanda", "generacion"]].mean()
    pon("finde_caida_demanda_pct", round(float(100 * (1 - m.loc[True, "demanda"] / m.loc[False, "demanda"])), 1),
        "%", "caída de la demanda media comunitaria del fin de semana frente al día hábil", F_ALM)
    pon("finde_caida_generacion_pct",
        round(float(100 * (1 - m.loc[True, "generacion"] / m.loc[False, "generacion"])), 1),
        "%", "lo mismo para la generación", F_ALM)
    for inst, gdf in list(df.groupby("agente")) + [("comunidad", df)]:
        mh = float((gdf.hora_del_dia * gdf.generacion).sum() / gdf.generacion.sum()) + 0.5
        pon(f"hora_media_generacion__{inst}", f"{int(mh):02d}:{int(round((mh % 1) * 60)):02d}",
            "hora", "hora media de la generación ponderada por la energía (etiqueta "
            "de la hora más media hora)", F_ALM)
        if inst != "comunidad":
            pon(f"pico_demanda_kW__{inst}", round(float(gdf.demanda.max()), 2), "kW",
                "demanda horaria máxima", F_ALM)
    df["mes_"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m")
    mm = df.groupby(["agente", "mes_"]).demanda.sum() / 1000.0
    llenos = [f"2025-{m:02d}" for m in range(5, 12)]
    media_llenos = mm[mm.index.get_level_values(1).isin(llenos)].groupby(level=0).mean()
    pon("demanda_mensual_media_min_MWh", round(float(media_llenos.min()), 1), "MWh",
        "menor media mensual de demanda entre instituciones, meses completos (mayo a noviembre)", F_ALM)
    pon("demanda_mensual_media_max_MWh", round(float(media_llenos.max()), 1), "MWh",
        "mayor media mensual, meses completos", F_ALM)
    pon("demanda_mensual_max_MWh", round(float(mm.max()), 1), "MWh",
        "mayor demanda de una institución en un mes", F_ALM)
    # Los trece casos: capacidad escalada y pares que agotan el crédito.
    g0 = s["generacion"]
    for caso in CASOS:
        a = pd.read_parquet(MATRIZ / caso / "almacen" / "m1" / "agentes")
        gm = a.groupby(["agente", "mes"])[["sobrante", "faltante"]].sum()
        pon(f"pares_agotan_credito__{caso}", int((gm.sobrante > gm.faltante).sum()), "pares",
            "pares institución-mes con inyección del mes mayor que su importación",
            f"almacén {caso}, tabla agentes")
        pon(f"pares_total__{caso}", int(len(gm)), "pares", "pares institución-mes",
            f"almacén {caso}, tabla agentes")
        cap = KWP_POR_PLANTA * a.groupby("agente").generacion.sum() / g0.reindex(
            a.agente.unique())
        exige(not cap.isna().any(), f"{caso}: capacidad no finita")
        for inst, v in cap.items():
            pon(f"capacidad_kW__{caso}__{inst}", round(float(v), 2), "kW",
                "17,55 kWp por la generación del caso sobre la de E0",
                f"almacén {caso} y E0")
        pon(f"capacidad_suma_kW__{caso}", round(float(cap.sum()), 2), "kW",
            "suma de capacidades", f"almacén {caso} y E0")


# ── 4. Tarifas, costos del mercado y contratos ──────────────────────────────
def tarifas() -> None:
    w = pd.Series(1, IDX).groupby(IDX.strftime("%Y-%m")).sum()
    medias = {}
    for com, f in [("ASC", "tarifas_asc_mensual.csv"), ("CEDENAR", "tarifas_cedenar_mensual.csv")]:
        t = pd.read_csv(RAIZ / "data" / f, comment="#")
        t = t[(t.categoria == "oficial") & (t.nivel_tension == 2)
              & (t.propiedad == "cedenar")].set_index("mes")
        exige(set(w.index) <= set(t.index), f"{com}: faltan meses del horizonte")
        t = t.loc[w.index]
        cols = ["Gm", "Tm", "Dnm", "Cvm", "PR", "Rm", "COT", "CU_aplicado"]
        exige(not t[cols].isna().any().any(), f"{com}: componentes vacíos")
        t["Theta"] = t.Tm + t.Dnm + t.PR + t.Rm
        for c in cols + ["Theta"]:
            v = float((t[c] * w).sum() / w.sum())
            medias[(com, c)] = v
            pon(f"tarifa_media__{com}__{c}", round(v, 2), "COP/kWh",
                f"media del horizonte ponderada por horas de {c}, fila oficial, nivel 2", F_TAR)
            pon(f"tarifa_media_simple__{com}__{c}", round(float(t[c].mean()), 2), "COP/kWh",
                f"media simple de los nueve meses de {c}", F_TAR)
        pon(f"cu_min__{com}", round(float(t.CU_aplicado.min()), 2), "COP/kWh",
            f"menor CU mensual ({t.CU_aplicado.idxmin()})", F_TAR)
        pon(f"cu_max__{com}", round(float(t.CU_aplicado.max()), 2), "COP/kWh",
            f"mayor CU mensual ({t.CU_aplicado.idxmax()})", F_TAR)
        dif = (t[["Gm", "Tm", "Dnm", "Cvm", "PR", "Rm", "COT"]].sum(axis=1) - t.CU_aplicado).abs().max()
        pon(f"cu_menos_suma_max__{com}", float(dif), "COP/kWh",
            "mayor diferencia entre la suma de componentes y el CU impreso", F_TAR)
        for c in ["Gm", "Cvm"]:
            pon(f"peso_{c}__{com}", round(100 * medias[(com, c)] / medias[(com, "CU_aplicado")], 1),
                "%", f"peso de {c} en el CU, medias ponderadas", F_TAR)
        mem = pd.read_csv(RAIZ / "data" / "mem_costs_no_regulado.csv").set_index("mes").loc[w.index]
        tasa = mem.fazni_cop_kwh + 0.04 * t.Gm + mem.comision_representante_cop_kwh
        pon(f"costos_mercado_media__{com}", round(float((tasa * w).sum() / w.sum()), 2), "COP/kWh",
            "FAZNI + 4 % de G + representante, media ponderada", "data/mem_costs_no_regulado.csv; " + F_TAR)
    pon("cv_razon_cedenar_asc", round(medias[("CEDENAR", "Cvm")] / medias[("ASC", "Cvm")], 2),
        "adimensional", "Cv de CEDENAR sobre Cv de ASC, medias ponderadas", F_TAR)
    pon("theta_cedenar_menos_asc", round(medias[("CEDENAR", "Theta")] - medias[("ASC", "Theta")], 2),
        "COP/kWh", "diferencia de T+D+PR+R, medias ponderadas", F_TAR)
    pon("cu_cedenar_menos_asc", round(medias[("CEDENAR", "CU_aplicado")] - medias[("ASC", "CU_aplicado")], 2),
        "COP/kWh", "diferencia de CU, medias ponderadas", F_TAR)
    pc = precio_horario(IDX)
    exige(bool(np.isfinite(pc).all()), "precio de contrato no finito")
    pon("contrato_min", round(float(pc.min()), 2), "COP/kWh", "menor precio de contrato mensual",
        "data/precios_contratos.py (XM, PPP Mercado No Regulado)")
    pon("contrato_max", round(float(pc.max()), 2), "COP/kWh", "mayor precio de contrato mensual",
        "data/precios_contratos.py (XM, PPP Mercado No Regulado)")
    pon("contrato_media", round(float(pc.mean()), 2), "COP/kWh", "media horaria del horizonte",
        "data/precios_contratos.py (XM, PPP Mercado No Regulado)")


# ── 5. La bolsa ─────────────────────────────────────────────────────────────
def _techo_viejo(tabla: pd.DataFrame, meses: pd.PeriodIndex) -> pd.Series:
    """El techo como lo aplicaba el código anterior a C-200 (defecto 3): los
    meses fuera de la tabla toman el más cercano, y los huecos interiores se
    interpolan."""
    s = tabla.set_index(pd.PeriodIndex(tabla["mes"], freq="M"))["pes_cop_kwh"].astype(float)
    todos = pd.period_range(min(s.index.min(), meses.min()), max(s.index.max(), meses.max()), freq="M")
    s = s.reindex(todos).interpolate(method="linear", limit_direction="both")
    return s


def bolsa() -> None:
    cache = RAIZ / "data" / "precios_bolsa_xm_api.csv"
    serie = _lee_csv_precios(cache)
    pon("bolsa_cache_horas", int(len(serie)), "h", "horas de la caché canónica", str(cache.name))
    pon("bolsa_cache_inicio", serie.index[0].strftime("%Y-%m-%d"), "fecha", "primera fecha", cache.name)
    pon("bolsa_cache_fin", serie.index[-1].strftime("%Y-%m-%d"), "fecha", "última fecha", cache.name)
    p = load_xm_prices(str(cache), T_START, T_END, estricto=True)
    exige(p is not None and len(p) == len(IDX), "la caché no cubre el horizonte")
    c, diag = apply_creg101066_ceiling(p, T_START, return_diagnostics=True)
    ref = get_pi_bolsa(len(IDX), T_START, T_END)
    exige(bool(np.allclose(ref, c)), "la bolsa topada no reproduce get_pi_bolsa")
    pon("bolsa_media_cruda", round(float(p.mean()), 2), "COP/kWh", "media sin techo", F_BOLSA)
    pon("bolsa_mediana_cruda", round(float(np.median(p)), 2), "COP/kWh", "mediana sin techo", F_BOLSA)
    pon("bolsa_min", round(float(p.min()), 2), "COP/kWh", "mínimo sin techo", F_BOLSA)
    pon("bolsa_max", round(float(p.max()), 2), "COP/kWh", "máximo sin techo", F_BOLSA)
    pon("bolsa_media_topada", round(float(c.mean()), 2), "COP/kWh", "media con el techo PES", F_BOLSA)
    pon("bolsa_horas_recortadas", int(diag["hours_capped"]), "h", "horas recortadas por el PES", F_BOLSA)
    sc, sr = pd.Series(c, IDX), pd.Series(p, IDX)
    mes = IDX.strftime("%Y-%m")
    for m_, v in sc.groupby(mes).mean().items():
        pon(f"bolsa_media_topada__{m_}", round(float(v), 2), "COP/kWh", "media mensual topada", F_BOLSA)
    for m_, v in sr.groupby(mes).mean().items():
        pon(f"bolsa_media_cruda__{m_}", round(float(v), 2), "COP/kWh", "media mensual sin techo", F_BOLSA)
    for m_, v in diag["by_month"].items():
        pon(f"bolsa_horas_recortadas__{m_}", int(v["hours_capped"]), "h", "horas recortadas", F_BOLSA)
    pes = pd.read_csv(RAIZ / "data" / "precios_escasez_creg.csv").set_index("mes").loc[sorted(set(mes))]
    pon("pes_min", round(float(pes.pes_cop_kwh.min()), 2), "COP/kWh",
        f"menor PES del horizonte ({pes.pes_cop_kwh.idxmin()})", "data/precios_escasez_creg.csv")
    pon("pes_max", round(float(pes.pes_cop_kwh.max()), 2), "COP/kWh",
        f"mayor PES del horizonte ({pes.pes_cop_kwh.idxmax()})", "data/precios_escasez_creg.csv")
    pon("piso_280_sobre_bolsa_pct", round(100 * (280.0 / float(c.mean()) - 1), 1), "%",
        "cuánto supera el piso escalar de 280 COP/kWh a la media topada", F_BOLSA)
    pon("xm_oficial_nov_2025", float(XM_MONTHLY_REAL["2025-11"]), "COP/kWh",
        "promedio oficial de XM de noviembre de 2025", "data/xm_prices.py, XM_MONTHLY_REAL")

    # H-92: la caché y la tabla de techos anteriores a C-200, del historial.
    viejo = git_bytes("f21205e^:data/precios_bolsa_xm_api.csv")
    tmp = SALIDA / "_cache_vieja_f21205e.csv"
    tmp.write_bytes(viejo)
    try:
        sv = _lee_csv_precios(tmp)
    finally:
        tmp.unlink()
    pv = sv.reindex(IDX)
    exige(not pv.isna().any(), "la caché vieja no cubre el horizonte")
    pv = pv.to_numpy(float)
    tabla_v = pd.read_csv(io.BytesIO(git_bytes("3fdff5e^:data/precios_escasez_creg.csv")))
    per = IDX.to_period("M")
    tv = _techo_viejo(tabla_v, per)
    cv = np.minimum(pv, tv.reindex(per).to_numpy(float))
    igual = (pv == p)
    primeras = int(np.argmax(~igual)) if (~igual).any() else len(IDX)
    pon("h92_primeras_horas_identicas", primeras, "h",
        "horas del inicio del horizonte en que la caché vieja y la nueva coinciden",
        "git f21205e^:data/precios_bolsa_xm_api.csv; caché canónica")
    pon("h92_horas_distintas_cache", int((~igual).sum()), "h",
        "horas del horizonte en que la caché vieja y la nueva difieren", "idem")
    distintas = ~np.isclose(cv, c, rtol=0, atol=1e-9)
    pon("h92_horas_distintas_total", int(distintas.sum()), "h",
        "horas en que difiere la bolsa topada, caché y tabla viejas frente a las nuevas",
        "idem; git 3fdff5e^:data/precios_escasez_creg.csv")
    pon("h92_horas_distintas_solo_techo", int((distintas & igual).sum()), "h",
        "de ellas, las que cambian solo por la tabla de techos", "idem")
    pon("h92_media_vieja_topada", round(float(cv.mean()), 2), "COP/kWh",
        "media del horizonte con la caché y la tabla viejas", "idem")
    pon("h92_dif_absoluta_media", round(float(np.abs(cv - c).mean()), 2), "COP/kWh",
        "diferencia absoluta media hora a hora, topadas", "idem")
    pon("h92_primera_hora_distinta", IDX[primeras].strftime("%Y-%m-%d %H:%M"), "fecha",
        "primera hora en que difieren las cachés", "idem")


# ── Principal ───────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--mte-root", default=mte_root_defecto())
    a = ap.parse_args(argv)
    root = Path(a.mte_root)
    exige(root.is_dir(), f"MTE_ROOT no es una carpeta: {root}")
    SALIDA.mkdir(parents=True, exist_ok=True)
    print(f"[cifras] MTE_ROOT {root}")
    print("[cifras] matrices del cargador (build_demand_generation)")
    D, G, _ = P.build_demand_generation(root, verbose=False)
    print("[cifras] almacén de E0 y de los trece casos")
    almacen(D, G)
    print("[cifras] medidores de la frontera")
    res = medidores(root)
    cobertura_sesgada(res)
    print("[cifras] sesgo de la ventana (H-18)")
    sesgo_ventana(root)
    print("[cifras] contadores (H-16, ADR 0045, H-18)")
    contadores(root)
    print("[cifras] generación (CAL-44)")
    generacion(root)
    print("[cifras] tercer medidor (D10)")
    tercer_medidor(root, D)
    print("[cifras] tarifas")
    tarifas()
    print("[cifras] bolsa (H-92)")
    bolsa()

    out = pd.DataFrame(FILAS, columns=["clave", "valor", "unidad", "definicion", "fuente"])
    out.to_csv(SALIDA / "cifras.csv", index=False, encoding="utf-8")
    sucio = git("status", "--short", "--", "data", "reformateo/documento/scripts/cifras_datos_cap04.py")
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8") as fh:
        fh.write("cifras_datos_cap04.py: cifras descriptivas del dato del capítulo 4 (C-229)\n")
        fh.write(f"fecha: {_dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("arbol de trabajo (data/ y este guion) con cambios sin commit:\n")
        fh.write((sucio or "(ninguno)") + "\n")
        import scipy
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, "
                 f"scipy {scipy.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + " ".join([Path(sys.argv[0]).as_posix()] + sys.argv[1:]) + "\n")
        fh.write(f"MTE_ROOT: {root}\n")
        fh.write(f"huella del dato: {huella_datos(root)}\n")
        fh.write(f"almacenes: {MATRIZ}\n")
        fh.write("historial para H-92: f21205e^:data/precios_bolsa_xm_api.csv, "
                 "3fdff5e^:data/precios_escasez_creg.csv\n")
        fh.write(f"cifras: {len(out)}\n")
    print(f"[cifras] {len(out)} cifras en {SALIDA / 'cifras.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
