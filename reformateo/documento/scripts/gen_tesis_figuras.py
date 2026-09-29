"""
gen_tesis_figuras.py — Figuras de los capítulos 4, 5 y 6 de la tesis.
=====================================================================
Encargo del 2026-09-28 (`.superpowers/sdd/2026-09-16-reposo/redaccion/
figuras-cap04-06-brief.md`). Una función por figura; ``main`` las genera
todas o las que se pidan por nombre:

    .venv/Scripts/python.exe -u reformateo/documento/scripts/gen_tesis_figuras.py
    .venv/Scripts/python.exe -u reformateo/documento/scripts/gen_tesis_figuras.py c5_banda_hora

Las figuras van a ``Documentos/FinalTesisV2/figuras/``, cada una con su
``.csv`` (los datos exactos que se dibujan), su ``.mat`` y su
``.fuente.txt`` (el artefacto leído y su huella).

Reglas que el guion hace cumplir
--------------------------------
1. **Solo datos del canon o de ficheros con huella.** Los almacenes de la
   matriz canónica del 19 de septiembre, las comparaciones del barrido de
   sigma y ``cifras_datos_2026-09-28/cifras.csv``. Cada uno se comprueba
   contra ``Documentos/canon_2026-09/HUELLAS.csv`` antes de leerlo. Los
   datos crudos (``MedicionesMTE_v3`` por el cargador, ``data/``) solo
   entran en las figuras descriptivas del capítulo 4, y su ``.fuente.txt``
   lo dice.
2. **Compuertas antes de dibujar.** Toda figura que muestra una cifra que
   el texto cita la reproduce antes desde su fuente, y se detiene si no
   coincide. No se simula nada: no se llama al motor.
3. **Fallar en voz alta.** Ningún ``except`` silencioso, ningún NaN
   rellenado para dibujar.

Actividades de la propuesta: 1.0 y 3.1 (capítulo 4), 1.1 y 1.2
(capítulo 5), 2.1 (capítulo 6).
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import estilo as E                                           # noqa: E402

RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ))

DIR_TESIS = RAIZ / "Documentos" / "FinalTesisV2" / "figuras"
SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
ENTREGA = SALIDAS / "entrega_matriz_reposo_2026-09-19"
MATRIZ = ENTREGA / "SALIDAS_SERVIDOR" / "matriz_reposo"
SIGMA = SALIDAS / "entrega_barrido_sigma_2026-09-27"
CIFRAS = SALIDAS / "cifras_datos_2026-09-28" / "cifras.csv"
HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
CACHE = AQUI.parent / "datos_cache"
MAPA_PDF = AQUI.parent / "figuras" / "f2_01_mapa_ubicacion.pdf"

CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
AGENTS = E.ORDEN_INSTITUCIONES          # el orden fijo del cargador
NBSP = " "


class FiguraError(RuntimeError):
    pass


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise FiguraError(msg)


# ── Tipografía de la tesis ───────────────────────────────────────────────────
# La tesis compila con Times New Roman (compila_tesis.ps1). Las figuras usan
# la misma letra para no chocar con el cuerpo; el resto del estilo es el del
# documento de proceso.
def _estilo_tesis() -> None:
    E.aplicar_estilo()
    plt.rcParams.update({
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 9.5,
        "axes.labelsize": 9.5,
        "axes.titlesize": 9.5,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.5,
    })


# ── Número en español, como en el texto de la tesis ──────────────────────────
def num(x: float, dec: int = 0) -> str:
    """6144.0 -> '6 144'; 1013.3 -> '1 013,3'. Miles con espacio, como el
    texto de la tesis, y coma decimal."""
    exige(np.isfinite(x), f"número no finito: {x!r}")
    s = f"{x:,.{dec}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", NBSP)


def eje_num(ax, eje: str = "y", dec: int = 0) -> None:
    f = FuncFormatter(lambda v, _: num(v, dec))
    (ax.yaxis if eje == "y" else ax.xaxis).set_major_formatter(f)


# ── Huellas ──────────────────────────────────────────────────────────────────
_HUELLAS: pd.DataFrame | None = None


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def con_huella(p: Path) -> str:
    """Comprueba el fichero contra HUELLAS.csv y devuelve su línea de rastro.

    Falla si el fichero no está registrado o si su contenido cambió."""
    global _HUELLAS
    if _HUELLAS is None:
        _HUELLAS = pd.read_csv(HUELLAS)
    pos = p.resolve().as_posix()
    filas = _HUELLAS[[pos.endswith("/" + r) for r in _HUELLAS["ruta"]]]
    exige(len(filas) == 1, f"{p} no tiene una huella única en HUELLAS.csv "
                           f"({len(filas)} coincidencias)")
    sha = _sha256(p)
    exige(sha == filas["sha256"].iloc[0],
          f"{p}: la huella no coincide con HUELLAS.csv")
    return f"{p.relative_to(RAIZ).as_posix()} (sha256 {sha[:16]}…, en HUELLAS.csv)"


def almacen(caso: str, tabla: str) -> tuple[pd.DataFrame, list[str]]:
    """Una tabla del almacén de un caso de la matriz canónica, con huellas."""
    d = MATRIZ / caso / "almacen" / "m1" / tabla
    partes = sorted(d.glob("*.parquet"))
    exige(len(partes) > 0, f"no hay partes en {d}")
    rastro = [con_huella(p) for p in partes]
    df = pd.concat([pd.read_parquet(p) for p in partes], ignore_index=True)
    return df, rastro


_CIFRAS: pd.DataFrame | None = None


def cifra(clave: str):
    """Una cifra de cifras_datos_2026-09-28 (C-229), por su clave."""
    global _CIFRAS
    if _CIFRAS is None:
        con_huella(CIFRAS)
        _CIFRAS = pd.read_csv(CIFRAS, dtype={"valor": str}).set_index("clave")
    exige(clave in _CIFRAS.index, f"cifras.csv no tiene la clave {clave}")
    v = _CIFRAS.loc[clave, "valor"]
    try:
        return float(v)
    except ValueError:
        return v


def igual(a: float, b: float, tol: float, que: str) -> None:
    exige(abs(float(a) - float(b)) <= tol,
          f"compuerta: {que}: {a!r} frente a {b!r} (tolerancia {tol})")


def guardar(fig, nombre: str, datos: pd.DataFrame, procedencia: list[str]):
    exige(not datos.select_dtypes("number").isna().any().any()
          or nombre in _CON_HUECOS,
          f"{nombre}: hay NaN en los datos dibujados")
    return E.guardar(fig, nombre, datos=datos, procedencia=procedencia,
                     directorio=DIR_TESIS, mat=True)


# Figuras cuyo CSV lleva huecos declarados (columna que solo aplica a
# algunas filas). Cualquier otra con NaN se detiene.
_CON_HUECOS = {"c5_banda_hora", "c4_generacion_udenar", "c7_brechas_institucion",
               "c8_infactibilidad_desercion"}


# ═════════════════════════════════════════════════════════════════════════════
# Capítulo 4
# ═════════════════════════════════════════════════════════════════════════════
def c4_mapa_instituciones():
    """Figura 4.1 — El mapa del proyecto MTE, reutilizado sin cambios.

    No es elaboración propia: lo elaboraron Miguel Andrade y Jenny Chapal
    para el proyecto MTE (abril de 2026). Se convierte el PDF del documento
    de proceso a PNG de 300 ppp con pdftoppm, sin tocar su contenido.
    """
    exige(MAPA_PDF.is_file(), f"no está {MAPA_PDF}")
    pdftoppm = shutil.which("pdftoppm")
    exige(pdftoppm is not None, "falta pdftoppm (MiKTeX) para convertir el mapa")
    DIR_TESIS.mkdir(parents=True, exist_ok=True)
    base = DIR_TESIS / "c4_mapa_instituciones"
    r = subprocess.run([pdftoppm, "-png", "-r", "300", "-singlefile",
                        str(MAPA_PDF), str(base)], capture_output=True, text=True)
    exige(r.returncode == 0, f"pdftoppm falló: {r.stderr}")
    exige(base.with_suffix(".png").is_file(), "pdftoppm no escribió el PNG")
    fuente_proceso = (AQUI.parent / "figuras" / "f2_01_mapa_ubicacion.fuente.txt")
    texto = fuente_proceso.read_text(encoding="utf-8")
    (DIR_TESIS / "c4_mapa_instituciones.fuente.txt").write_text(
        "Figura: c4_mapa_instituciones\n"
        "Reutilizada sin cambios de reformateo/documento/figuras/"
        f"f2_01_mapa_ubicacion.pdf (sha256 {_sha256(MAPA_PDF)[:16]}…), "
        "convertida a PNG de 300 ppp con pdftoppm.\n"
        "No lleva CSV: no dibuja datos del modelo.\n"
        "Procedencia del documento de proceso:\n" + texto, encoding="utf-8")
    print("  [figura] c4_mapa_instituciones.png")


# ── Figura 4.2: el periodo de registro de las 27 fuentes ─────────────────────
def _censo_fuentes() -> pd.DataFrame:
    p = CACHE / "fuentes.csv"
    exige(p.is_file(), "falta datos_cache/fuentes.csv (scripts/cache_fuentes.py)")
    d = pd.read_csv(p, encoding="utf-8-sig")
    d["inicio"] = pd.to_datetime(d["inicio"])
    d["fin"] = pd.to_datetime(d["fin"])
    return d


def c4_fuentes_registro():
    """Figura 4.2 — Periodo de registro de las 27 fuentes y el horizonte.

    Sustituye a f2_02_gantt_fuentes del documento de proceso, que pintaba el
    tercer medidor como empleado por el modelo: desde D10 la segunda frontera
    está retirada y el modelo lee 12 fuentes, el medidor 1 de cada
    institución y los siete inversores. El censo es el de
    ``datos_cache/fuentes.csv`` (MedicionesMTE_v3), comprobado antes contra
    las primeras horas de cifras_datos_2026-09-28.
    """
    d = _censo_fuentes()
    exige(len(d) == 27, f"el censo tiene {len(d)} fuentes y no 27")
    exige((d.clase == "medidor").sum() == 20 and (d.clase == "inversor").sum() == 7,
          "el censo no tiene 20 medidores y 7 inversores")

    # Qué lee el modelo hoy: el medidor 1 de cada institución y los siete
    # inversores (el designado, y en Udenar también los dos de la
    # reconstrucción). El papel «M3» del censo es la frontera retirada.
    d["n_med"] = d["fuente"].str.extract(r"Medidor\s*(\d+)").astype(float)
    d["usado"] = ((d.clase == "inversor")
                  | ((d.clase == "medidor") & (d.n_med == 1)))
    exige(int(d.usado.sum()) == 12, "el modelo no lee 12 fuentes según el censo")

    # Compuerta: la primera hora de cada fuente usada coincide con la de
    # cifras_datos_2026-09-28 (leída del crudo por el cargador).
    from data.preprocessing import EMS_INVERTER_CONFIG
    for inst in AGENTS:
        m1 = d[(d.institucion == inst) & (d.clase == "medidor") & (d.n_med == 1)]
        exige(len(m1) == 1, f"{inst}: no hay un medidor 1 en el censo")
        igual(0, (m1.inicio.iloc[0].floor("1h")
                  - pd.Timestamp(cifra(f"primera_hora_medidor__{inst}"))).total_seconds(),
              0, f"primera hora del medidor 1 de {inst}")
        inv = d[d.fuente == EMS_INVERTER_CONFIG[inst]]
        exige(len(inv) == 1, f"{inst}: el inversor designado no está en el censo")
        igual(0, (inv.inicio.iloc[0].floor("1h")
                  - pd.Timestamp(cifra(f"primera_hora_inversor__{inst}"))).total_seconds(),
              0, f"primera hora del inversor designado de {inst}")

    ini = pd.Timestamp(cifra("horizonte_inicio"))
    fin = pd.Timestamp(cifra("horizonte_fin")) + pd.Timedelta(hours=1)

    # La fuente que fija el inicio: la última en entrar de las que el modelo
    # necesita desde el primer día. En Udenar el designado se extiende hacia
    # atrás con el primer Fronius, de modo que el designado no cuenta.
    from data.preprocessing import EMS_INVERTER_BACKFILL_CONFIG
    reconstruidos = {EMS_INVERTER_CONFIG[i] for i in EMS_INVERTER_BACKFILL_CONFIG}
    esenciales = d[d.usado & ~d.fuente.isin(reconstruidos)]
    i_tope = esenciales.inicio.idxmax()
    exige(d.loc[i_tope, "institucion"] == "HUDN" and d.loc[i_tope, "clase"] == "inversor",
          "la fuente que fija el inicio no es el inversor del HUDN")
    exige(d.loc[i_tope, "inicio"].floor("D") == ini.floor("D"),
          "el inicio del horizonte no es el día de entrada del inversor del HUDN")

    # Rótulos: los del texto del capítulo.
    ref = EMS_INVERTER_BACKFILL_CONFIG["Udenar"]
    filas = []
    for inst in AGENTS:
        sub = d[d.institucion == inst]
        nom = E.etiqueta_institucion(inst)
        for _, f in sub[sub.clase == "medidor"].sort_values("n_med").iterrows():
            filas.append({**f, "etiqueta": f"{nom} · medidor {int(f.n_med)}"})
        inv = sub[sub.clase == "inversor"]
        for _, f in inv.iterrows():
            if inst != "Udenar":
                et = f"{nom} · inversor"
            elif f.fuente == EMS_INVERTER_CONFIG["Udenar"]:
                et = f"{nom} · inversor del proyecto"
            elif f.fuente == ref:
                et = f"{nom} · Fronius 1"
            else:
                et = f"{nom} · Fronius 2"
            filas.append({**f, "etiqueta": et})
        if inst == "Udenar":
            # Orden de los inversores de Udenar: los dos Fronius y el del
            # proyecto, como los presenta el texto.
            orden = {"Udenar · Fronius 1": 0, "Udenar · Fronius 2": 1,
                     "Udenar · inversor del proyecto": 2}
            cola = [x for x in filas if x["etiqueta"] in orden]
            filas = [x for x in filas if x["etiqueta"] not in orden]
            filas += sorted(cola, key=lambda x: orden[x["etiqueta"]])
    t = pd.DataFrame(filas).reset_index(drop=True)
    i_tope_t = int(t.index[t.fuente == d.loc[i_tope, "fuente"]][0])

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 5.9))
    y0 = 0
    for k, inst in enumerate(AGENTS):
        n = int((t.institucion == inst).sum())
        if k % 2 == 0:
            ax.axhspan(y0 - 0.5, y0 + n - 0.5, color=E.FONDO_BANDA, zorder=0)
        y0 += n
    azul = E.MECANISMOS["P2P"]
    ax.axvspan(ini, fin, color=azul, alpha=0.10, zorder=1)
    for v in (ini, fin):
        ax.axvline(v, color=azul, linewidth=1.2, zorder=5)

    colores_y = []
    for i, f in t.iterrows():
        color = E.color_institucion(f.institucion) if f.usado else E.APAGADO
        es_inv = f.clase == "inversor"
        ax.barh(i, (f.fin - f.inicio).total_seconds() / 86400.0, left=f.inicio,
                height=0.62, color=color, zorder=3,
                hatch="///" if es_inv else None,
                edgecolor="white" if es_inv else "none", linewidth=0.0)
        colores_y.append(color if f.usado else "#8F8F8F")
    ax.plot([t.loc[i_tope_t, "inicio"]], [i_tope_t], marker="o", markersize=9,
            markerfacecolor="none", markeredgecolor=E.ALERTA,
            markeredgewidth=1.6, zorder=7)
    # El rótulo va en el hueco blanco a la izquierda de las barras del HUDN,
    # que empiezan en abril: ahí no pisa ninguna barra.
    ax.annotate("fija el inicio\ndel horizonte",
                xy=(t.loc[i_tope_t, "inicio"], i_tope_t),
                xytext=(-14, 30), textcoords="offset points", ha="right",
                va="center", fontsize=8.5, color=E.ALERTA, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=E.ALERTA, lw=1.0,
                                shrinkB=6))

    ax.set_yticks(range(len(t)))
    ax.set_yticklabels(t.etiqueta, fontsize=7.6)
    for tick, c in zip(ax.get_yticklabels(), colores_y):
        tick.set_color(c)
    ax.set_ylim(len(t) - 0.5, -0.5)
    ax.set_xlim(pd.Timestamp("2024-12-15"), pd.Timestamp("2026-05-10"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(FuncFormatter(
        lambda v, _: E.fmt_fecha(mdates.num2date(v), "mes_anio")))
    ax.xaxis.set_minor_locator(mdates.MonthLocator())
    ax.tick_params(axis="x", which="minor", length=2, width=0.6)
    ax.grid(axis="y", visible=False)
    ax.text(ini + (fin - ini) / 2, -0.95, "horizonte del estudio", color=azul,
            fontsize=8.5, fontweight="bold", ha="center", va="bottom")
    ax.legend(handles=[
        Patch(facecolor=E.NEUTRO, label="medidor"),
        Patch(facecolor=E.NEUTRO, hatch="///", edgecolor="white", label="inversor"),
        Patch(facecolor=E.APAGADO, label="no lo lee el modelo"),
    ], loc="upper center", bbox_to_anchor=(0.42, -0.045), ncol=3, frameon=False)
    fig.tight_layout()

    datos = t[["institucion", "clase", "fuente", "etiqueta", "usado", "inicio",
               "fin"]].copy()
    datos["inicio"] = datos.inicio.dt.strftime("%Y-%m-%d %H:%M:%S")
    datos["fin"] = datos.fin.dt.strftime("%Y-%m-%d %H:%M:%S")
    datos["fija_inicio_horizonte"] = datos.index == i_tope_t
    return guardar(fig, "c4_fuentes_registro", datos, [
        "reformateo/documento/datos_cache/fuentes.csv (censo de MedicionesMTE_v3 "
        "por scripts/cache_fuentes.py; dato crudo, figura descriptiva)",
        "compuerta: la primera hora del medidor 1 y del inversor designado de cada "
        "institución coincide con " + con_huella(CIFRAS),
        "usado = medidor 1 de cada institución y los siete inversores (D10: el "
        "tercer medidor ya no se lee)",
    ])


# ── Figura 4.3: la reconstrucción de la demanda de Udenar ────────────────────
def c4_reconstruccion_udenar(dia: str = "2025-11-07"):
    """Figura 4.3 — La demanda de Udenar que el medidor netea, reconstruida.

    Es la f3_03 del documento de proceso sin el rótulo de frontera (que ya
    no hace falta, porque hay una sola) y con el número de la tesis. El día
    es el mismo, el viernes 7 de noviembre de 2025: posterior al 3 de
    septiembre, con los tres inversores registrando y sin horas recortadas,
    y el guion lo comprueba antes de dibujar. Las series salen de la caché
    del preprocesamiento (``cache_crudo.py``, que llama a las funciones del
    cargador), comprobada hora a hora contra el almacén de E0.
    """
    z = np.load(CACHE / "preproceso_m1.npz", allow_pickle=True)
    horas = pd.DatetimeIndex(z["__horas"])
    s = lambda k: pd.Series(z[f"Udenar__{k}"], index=horas)      # noqa: E731
    D_raw, G_rec, D_rec, D_lim = s("D_raw"), s("G_recon"), s("D_recon"), s("D_limpia")

    ag, rastro = almacen("E0", "agentes")
    u = ag[ag.agente == "Udenar"].sort_values("hora")
    exige(len(u) == len(horas) == 6144, "horas distintas entre caché y almacén")
    dif = float(np.max(np.abs(u.demanda.to_numpy(float) - D_lim.to_numpy(float))))
    exige(dif < 1e-3, f"la caché no reproduce la demanda de Udenar del almacén ({dif:.3g})")
    exige(float((D_rec - D_lim).abs().max()) < 1e-9,
          "en Udenar la demanda reconstruida no es la limpia")

    D_neto = D_raw.fillna(0.0)
    recorte = (-(D_neto + G_rec)).clip(lower=0.0)
    exige(float((D_rec - (D_neto + G_rec + recorte)).abs().max()) < 1e-9,
          "la reconstrucción no cierra: D = max(0, lectura + inversores)")
    igual(round(float(recorte.sum()), 1), cifra("recorte_kWh__Udenar"), 0.05,
          "energía del recorte a cero de Udenar")
    igual(int((recorte > 0).sum()), cifra("recorte_horas__Udenar"), 0,
          "horas con recorte en Udenar")
    igual(round(float(D_rec.sum()), 1), cifra("demanda_kWh__Udenar"), 0.05,
          "demanda de Udenar en el horizonte")

    d0 = pd.Timestamp(dia)
    sl = slice(d0, d0 + pd.Timedelta(hours=23))
    x = np.arange(24)
    dr, gr, dd = (D_neto[sl].to_numpy(float), G_rec[sl].to_numpy(float),
                  D_rec[sl].to_numpy(float))
    exige(len(dr) == 24, "el día no tiene 24 horas")
    exige(not D_raw[sl].isna().any(), f"{dia}: hay horas sin lectura")
    exige(d0 >= pd.Timestamp(cifra("udenar_arranque_MTE")).floor("D") + pd.Timedelta(days=1),
          f"{dia} no es posterior al arranque del inversor del proyecto")
    exige(float(recorte[sl].sum()) < 1e-9, f"{dia} tiene horas recortadas")

    fig = plt.figure(figsize=(E.ANCHO_COMPLETO, 4.9))
    gs = fig.add_gridspec(2, 2, width_ratios=(1.42, 1.0), height_ratios=(1.0, 0.32))
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1], sharey=ax1)
    axb = fig.add_subplot(gs[1, :])
    ax2.tick_params(labelleft=False)

    ax1.axhline(0, color="#333333", linewidth=0.9, zorder=3)
    ax1.fill_between(x, dr, dd, color=E.APOYO, zorder=1)
    ax1.plot(x, dd, color=E.DESPUES, linewidth=2.2, zorder=4)
    ax1.plot(x, dr, color=E.ANTES, linewidth=1.4, zorder=5)
    lo, hi = float(min(dr.min(), dd.min())), float(max(dr.max(), dd.max()))
    alto = hi - lo
    ax1.set_ylim(lo - 0.09 * alto, hi + 0.13 * alto)
    h = int(np.argmin(dr))
    ax1.annotate("", xy=(h, dd[h]), xytext=(h, dr[h]), zorder=6,
                 arrowprops=dict(arrowstyle="<->", color=E.TINTA, lw=0.9,
                                 shrinkA=0, shrinkB=0))
    ax1.text(h - 0.45, (dr[h] + dd[h]) / 2, f"{num(gr[h], 1)} kW\ndevueltos",
             ha="right", va="center", fontsize=8.2, color=E.TINTA, zorder=6)
    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Potencia media (kW)")
    ax1.set_title(f"{E.fmt_fecha(d0, 'dia')}", pad=6)
    ax1.set_xticks(range(0, 24, 3))
    ax1.set_xlim(-0.6, 23.6)

    idx = np.arange(24)
    grp = lambda s_: s_.groupby(s_.index.hour).mean().to_numpy(float)   # noqa: E731
    p_neto, p_gen, p_rec, p_cor = grp(D_neto), grp(G_rec), grp(D_rec), grp(recorte)
    exige(bool(np.allclose(p_rec, p_neto + p_gen + p_cor, atol=1e-9)),
          "el perfil medio no cierra")
    ax2.axhline(0, color="#333333", linewidth=0.9, zorder=3)
    ax2.fill_between(idx, p_neto, p_neto + p_gen, color=E.APOYO, zorder=1)
    ax2.fill_between(idx, p_neto + p_gen, p_rec, color=E.NEUTRO, alpha=0.65, zorder=2)
    ax2.plot(idx, p_rec, color=E.DESPUES, linewidth=2.2, zorder=4)
    ax2.plot(idx, p_neto, color=E.ANTES, linewidth=1.4, zorder=5)
    ax2.set_xlabel("Hora del día")
    ax2.set_title(f"perfil medio de las {num(len(horas))} horas", pad=6)
    ax2.set_xticks(range(0, 24, 6))
    ax2.set_xlim(-0.6, 23.6)

    e_neto, e_gen, e_cor, e_rec = (float(D_neto.sum()), float(G_rec.sum()),
                                   float(recorte.sum()), float(D_rec.sum()))
    exige(abs(e_neto + e_gen + e_cor - e_rec) < 1e-6, "la cuenta de energía no cierra")
    hueco = 0.0025 * e_rec
    tramos = [("lectura del medidor", e_neto, E.ANTES, 0.80),
              ("generación devuelta", e_gen, E.APOYO, 1.00),
              ("recorte a cero", e_cor, E.NEUTRO, 0.65)]
    izq = 0.0
    for k, (_, valor, color, opac) in enumerate(tramos):
        ancho = valor - (hueco if k < len(tramos) - 1 else 0.0)
        axb.barh(0, ancho, left=izq, height=0.46, color=color, alpha=opac, zorder=3)
        izq += valor
    axb.plot([0, e_rec], [-0.52, -0.52], color=E.DESPUES, lw=2.0,
             solid_capstyle="butt", zorder=3)
    for xx in (0.0, e_rec):
        axb.plot([xx, xx], [-0.66, -0.38], color=E.DESPUES, lw=2.0, zorder=3)
    axb.text(e_rec / 2, -0.80, f"demanda reconstruida del horizonte: {num(e_rec, 1)} kWh",
             ha="center", va="top", fontsize=8.5, color=E.DESPUES)
    izq = 0.0
    for k, (nombre, valor, _c, _o) in enumerate(tramos):
        centro = izq + valor / 2
        if k < 2:
            axb.text(centro, 0.36, f"{nombre}: {num(valor, 1)} kWh",
                     ha="center", va="bottom", fontsize=8.5, color=E.TINTA)
        else:
            axb.annotate(f"{nombre}: {num(valor, 1)} kWh", xy=(centro, 0.25),
                         xytext=(e_rec, 1.05), ha="right", va="bottom",
                         fontsize=8.5, color=E.TINTA,
                         arrowprops=dict(arrowstyle="-", color=E.NEUTRO, lw=0.7,
                                         shrinkA=2, shrinkB=1,
                                         connectionstyle="arc3,rad=-0.25"))
        izq += valor
    axb.set_xlim(-0.012 * e_rec, 1.012 * e_rec)
    axb.set_ylim(-1.15, 1.45)
    axb.set_axis_off()
    fig.legend(handles=[
        Line2D([], [], color=E.ANTES, lw=1.6, label="lectura del medidor"),
        Patch(facecolor=E.APOYO, label="generación devuelta"),
        Patch(facecolor=E.NEUTRO, alpha=0.65, label="recorte a cero"),
        Line2D([], [], color=E.DESPUES, lw=2.2, label="demanda reconstruida"),
    ], loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=4, frameon=False,
        columnspacing=1.4, handlelength=1.8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))

    filas = []
    for k in range(24):
        filas += [dict(bloque="dia", clave=str(k), serie=n_, valor=float(v_), unidad="kW")
                  for n_, v_ in (("lectura_medidor", dr[k]), ("generacion_devuelta", gr[k]),
                                 ("demanda_reconstruida", dd[k]))]
        filas += [dict(bloque="perfil_medio", clave=str(k), serie=n_, valor=float(v_), unidad="kW")
                  for n_, v_ in (("lectura_medidor", p_neto[k]), ("generacion_devuelta", p_gen[k]),
                                 ("recorte_a_cero", p_cor[k]), ("demanda_reconstruida", p_rec[k]))]
    filas += [dict(bloque="energia_horizonte", clave="total", serie=n_, valor=v_, unidad="kWh")
              for n_, v_ in (("lectura_medidor", e_neto), ("generacion_devuelta", e_gen),
                             ("recorte_a_cero", e_cor), ("demanda_reconstruida", e_rec))]
    return guardar(fig, "c4_reconstruccion_udenar", pd.DataFrame(filas), [
        "reformateo/documento/datos_cache/preproceso_m1.npz (scripts/cache_crudo.py "
        "sobre MedicionesMTE_v3, con las funciones del cargador; dato crudo, "
        "figura descriptiva)",
        "compuerta: la demanda limpia de Udenar de la caché reproduce hora a hora "
        "la del almacén de E0 (< 1e-3 kW):",
        *[f"  {r}" for r in rastro],
        "compuerta: recorte (1 013,3 kWh, 353 h) y demanda de Udenar (44 310,5 kWh) "
        "iguales a " + con_huella(CIFRAS),
        f"día del panel izquierdo: {dia} (posterior al 3 de septiembre de 2025, "
        "tres inversores registrando, sin horas recortadas)",
        "regla: D = max(0, lectura del medidor + suma de los tres inversores), "
        "ecuación (4.2); data/preprocessing.py",
    ])


# ── Figura 4.4: la generación de Udenar reconstruida ─────────────────────────
def c4_generacion_udenar():
    """Figura 4.4 — La generación diaria de Udenar: reconstruida y medida.

    La serie que negocia el modelo para Udenar es la del inversor del
    proyecto donde registra y el primer Fronius escalado por alfa donde no.
    Se lee con las funciones del cargador sobre MedicionesMTE_v3 y se
    comprueba contra cifras_datos_2026-09-28 (alfa, solape, energía
    reconstruida) y contra la generación del almacén de E0.
    """
    from data import preprocessing as P
    from data.xm_data_loader import INVERTER_FOLDER
    import cifras_datos_cap04 as CD
    from gsa_directo.comun import mte_root_defecto
    root = Path(mte_root_defecto())
    exige(root.is_dir(), f"MTE_ROOT no es una carpeta: {root}")
    IDX = CD.IDX
    des = P.EMS_INVERTER_CONFIG["Udenar"]
    ref = P.EMS_INVERTER_BACKFILL_CONFIG["Udenar"]
    g = P._read_single_inverter(CD.carpeta_inversor(root, "Udenar", des), IDX)
    r = P._read_single_inverter(CD.carpeta_inversor(root, "Udenar", ref), IDX)
    sol = g.notna() & r.notna()
    alfa = float(g[sol].sum() / r[sol].sum())
    falta = g.isna()
    ext = g.copy()
    ext[falta] = alfa * r[falta]
    g_mod = P._read_ems_generation(P._find_subdir(P._find_subdir(root, "Udenar"),
                                                  INVERTER_FOLDER["Udenar"]),
                                   des, ref, IDX, verbose=False)
    exige(bool(np.allclose(ext.fillna(0.0).to_numpy(), g_mod.to_numpy())),
          "la serie extendida no reproduce la del cargador")
    igual(round(alfa, 4), cifra("udenar_factor_extension"), 0, "factor alfa")
    igual(int(sol.sum()), cifra("udenar_solape_horas"), 0, "horas de solape")
    rec_e = float((alfa * r[falta]).sum())
    igual(round(rec_e, 1), cifra("udenar_energia_reconstruida_kWh"), 0.05,
          "energía reconstruida de Udenar")
    total = float(g_mod.sum())
    igual(round(100 * rec_e / total, 1), cifra("udenar_energia_reconstruida_pct"), 0.05,
          "porcentaje reconstruido")
    ag, rastro = almacen("E0", "agentes")
    u = ag[ag.agente == "Udenar"].sort_values("hora")
    dif = float(np.max(np.abs(u.generacion.to_numpy(float) - g_mod.to_numpy(float))))
    exige(dif < 1e-3, f"la generación del cargador difiere del almacén ({dif:.3g} kW)")
    arranque = g.first_valid_index()
    igual(0, (arranque.floor("1h") - pd.Timestamp(cifra("udenar_arranque_MTE"))).total_seconds(),
          0, "arranque del inversor del proyecto")

    # Por día: la energía medida (inversor del proyecto), la reconstruida
    # (Fronius escalado donde el del proyecto no registra) y, desde el
    # arranque, el Fronius escalado que habría ocupado su lugar.
    medida = g.fillna(0.0)
    reconstruida = (alfa * r[falta]).reindex(IDX).fillna(0.0)
    fron_escalado = (alfa * r).where(IDX >= arranque.floor("D"))
    dia = IDX.floor("D")
    dd = pd.DataFrame({
        "medida_kWh": medida.groupby(dia).sum(),
        "reconstruida_kWh": reconstruida.groupby(dia).sum(),
        "fronius_escalado_kWh": fron_escalado.groupby(dia).sum(min_count=1),
    })
    igual(round(float(dd.reconstruida_kWh.sum()), 1), round(rec_e, 1), 0.05,
          "suma diaria de la energía reconstruida")
    antes = dd.index < arranque.floor("D")
    exige(float(dd.medida_kWh[antes].sum()) == 0.0, "hay energía medida antes del arranque")
    # Desde el día siguiente al arranque, ninguna energía reconstruida
    # (las horas sin dato del proyecto son noches: 0,0 kWh, cifras.csv).
    igual(cifra("udenar_energia_sin_MTE_despues_kWh"), 0.0, 1e-9,
          "energía reconstruida después del arranque")

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 2.9))
    x = dd.index + pd.Timedelta(hours=12)
    c_u = E.color_institucion("Udenar")
    ax.fill_between(x, 0, dd.reconstruida_kWh, step="mid", color=E.APOYO,
                    linewidth=0, zorder=2)
    ax.fill_between(x, 0, dd.medida_kWh, step="mid", color=c_u, alpha=0.85,
                    linewidth=0, zorder=3)
    post = dd.index >= arranque.floor("D")
    ax.step(x[post], dd.fronius_escalado_kWh[post], where="mid", color=E.TINTA,
            lw=0.8, zorder=4)
    ax.axvline(arranque.floor("D"), color=E.TINTA, lw=0.9, ls="--", zorder=5)
    eje_num(ax, "y")
    ax.set_ylabel("Energía generada (kWh/día)")
    ax.set_xlim(IDX[0].floor("D") - pd.Timedelta(days=1), IDX[-1].floor("D") + pd.Timedelta(days=2))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(
        lambda v, _: E.fmt_fecha(mdates.num2date(v), "mes")))
    ax.grid(axis="x", visible=False)
    tope = float(max(dd.reconstruida_kWh.max(), dd.medida_kWh.max()))
    ax.set_ylim(0, tope * 1.32)
    ax.annotate(f"entra el inversor del proyecto,\n{E.fmt_fecha(arranque, 'dia_corto')}",
                xy=(arranque.floor("D"), tope * 1.18), xytext=(-6, 0),
                textcoords="offset points", ha="right", va="center", fontsize=8.5,
                color=E.TINTA)
    ax.legend(handles=[
        Patch(facecolor=E.APOYO, label=f"primer Fronius × {num(alfa, 4)} (reconstruida)"),
        Patch(facecolor=c_u, alpha=0.85, label="inversor del proyecto (medida)"),
        Line2D([], [], color=E.TINTA, lw=0.8, label=f"primer Fronius × {num(alfa, 4)}, en el solape"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False,
        fontsize=8.2, handlelength=1.6, columnspacing=1.4)
    fig.tight_layout()

    datos = dd.reset_index(names="dia")
    datos["dia"] = datos.dia.dt.strftime("%Y-%m-%d")
    return guardar(fig, "c4_generacion_udenar", datos, [
        f"MedicionesMTE_v3/Udenar/ (inversor del proyecto «{des}» y primer Fronius "
        f"«{ref}») leídos con _read_single_inverter y _read_ems_generation del "
        "cargador (dato crudo, figura descriptiva)",
        "compuerta: la serie del cargador reproduce la generación de Udenar del "
        "almacén de E0 (< 1e-3 kW):",
        *[f"  {x_}" for x_ in rastro],
        "compuerta: alfa 1,2053, solape de 1 409 h, 9 447,4 kWh reconstruidos "
        "(59,3 %) iguales a " + con_huella(CIFRAS),
        "fronius_escalado_kWh va vacío en los días anteriores al arranque (no se dibuja)",
    ])


# ── Figura 4.5: los perfiles de E0 ───────────────────────────────────────────
def c4_perfiles_e0():
    """Figura 4.5 — Perfil medio por hora del día de la demanda y la
    generación de cada institución en E0, día hábil y fin de semana.

    Del almacén de E0 (tabla agentes). Fin de semana es sábado y domingo,
    como en cifras_datos_cap04.py; los festivos cuentan como hábiles.
    """
    ag, rastro = almacen("E0", "agentes")
    exige(len(ag) == 5 * 6144, "el almacén de E0 no tiene 5 × 6 144 filas")
    ag["finde"] = pd.to_datetime(ag.fecha).dt.dayofweek >= 5
    tot = ag.groupby("agente")[["demanda", "generacion"]].sum()
    for inst in AGENTS:
        igual(round(float(tot.loc[inst, "demanda"]), 1), cifra(f"demanda_kWh__{inst}"), 0.05,
              f"demanda de {inst}")
        igual(round(float(tot.loc[inst, "generacion"]), 1), cifra(f"generacion_kWh__{inst}"),
              0.05, f"generación de {inst}")
    hf = ag.groupby(["hora", "finde"])[["demanda", "generacion"]].sum().reset_index()
    m = hf.groupby("finde")[["demanda", "generacion"]].mean()
    igual(round(float(100 * (1 - m.loc[True, "demanda"] / m.loc[False, "demanda"])), 1),
          cifra("finde_caida_demanda_pct"), 0, "caída de la demanda el fin de semana")
    igual(round(float(100 * (1 - m.loc[True, "generacion"] / m.loc[False, "generacion"])), 1),
          cifra("finde_caida_generacion_pct"), 0, "caída de la generación el fin de semana")

    p = (ag.groupby(["agente", "finde", "hora_del_dia"])[["demanda", "generacion"]]
         .mean().reset_index())
    fig, ejes = plt.subplots(1, 5, figsize=(E.ANCHO_COMPLETO, 2.55), sharey=True)
    for ax, inst in zip(ejes, AGENTS):
        for finde, ls in ((False, "-"), (True, (0, (2.2, 1.4)))):
            q = p[(p.agente == inst) & (p.finde == finde)].sort_values("hora_del_dia")
            ax.plot(q.hora_del_dia, q.demanda, color=E.TINTA, lw=1.4, ls=ls)
            ax.plot(q.hora_del_dia, q.generacion, color=E.GENERACION, lw=1.4, ls=ls)
        ax.set_title(E.etiqueta_institucion(inst), color=E.color_institucion(inst),
                     fontweight="bold", pad=4)
        ax.set_xticks([0, 6, 12, 18])
        ax.set_xlim(0, 23)
    ejes[0].set_ylabel("Potencia media (kW)")
    ejes[0].set_ylim(0, None)
    fig.supxlabel("Hora del día", y=0.105, fontsize=9.5)
    fig.legend(handles=[
        Line2D([], [], color=E.TINTA, lw=1.4, label="demanda, día hábil"),
        Line2D([], [], color=E.TINTA, lw=1.4, ls=(0, (2.2, 1.4)), label="demanda, fin de semana"),
        Line2D([], [], color=E.GENERACION, lw=1.4, label="generación, día hábil"),
        Line2D([], [], color=E.GENERACION, lw=1.4, ls=(0, (2.2, 1.4)),
               label="generación, fin de semana"),
    ], loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.01),
        columnspacing=1.2, handlelength=2.0, fontsize=8.0)
    fig.tight_layout(rect=(0, 0.13, 1, 1), w_pad=0.6)

    datos = p.rename(columns={"demanda": "demanda_kW", "generacion": "generacion_kW"})
    datos["dia"] = np.where(datos.finde, "fin_de_semana", "habil")
    datos = datos.drop(columns="finde")
    return guardar(fig, "c4_perfiles_e0", datos, [
        *rastro,
        "tabla agentes del almacén de E0 (matriz canónica del 19 de septiembre): "
        "media por institución, tipo de día y hora del día; fin de semana = sábado "
        "y domingo",
        "compuerta: totales por institución y caída del fin de semana (42,5 % y "
        "1,7 %) iguales a " + con_huella(CIFRAS),
    ])


# ── Figura 4.6: la bolsa del horizonte ───────────────────────────────────────
def c4_bolsa():
    """Figura 4.6 — La bolsa horaria del horizonte, topada, con su media
    diaria y el precio de escasez superior de cada mes.

    Dato de ``data/`` leído con las funciones del cargador (load_xm_prices,
    apply_creg101066_ceiling), comprobado contra cifras_datos_2026-09-28.
    """
    from data.xm_prices import load_xm_prices, apply_creg101066_ceiling, get_pi_bolsa
    from data.xm_data_loader import T_END, T_START
    IDX = pd.date_range(T_START, T_END, freq="1h", inclusive="left")
    cache = RAIZ / "data" / "precios_bolsa_xm_api.csv"
    p = load_xm_prices(str(cache), T_START, T_END, estricto=True)
    exige(p is not None and len(p) == len(IDX), "la caché no cubre el horizonte")
    c, diag = apply_creg101066_ceiling(p, T_START, return_diagnostics=True)
    exige(bool(np.allclose(get_pi_bolsa(len(IDX), T_START, T_END), c)),
          "la bolsa topada no reproduce get_pi_bolsa")
    p = pd.Series(np.asarray(p, float), IDX)
    c = pd.Series(np.asarray(c, float), IDX)
    igual(round(float(p.mean()), 2), cifra("bolsa_media_cruda"), 0.005, "media sin techo")
    igual(round(float(c.mean()), 2), cifra("bolsa_media_topada"), 0.005, "media topada")
    recortadas = p > c + 1e-9
    igual(int(recortadas.sum()), cifra("bolsa_horas_recortadas"), 0, "horas recortadas")
    pes = pd.read_csv(RAIZ / "data" / "precios_escasez_creg.csv").set_index("mes")
    meses = sorted(set(IDX.strftime("%Y-%m")))
    pes = pes.loc[meses, "pes_cop_kwh"].astype(float)
    igual(pes.min(), cifra("pes_min"), 0.005, "precio de escasez mínimo")
    igual(pes.max(), cifra("pes_max"), 0.005, "precio de escasez máximo")
    exige(bool(np.allclose(c[recortadas].to_numpy(),
                           pes.reindex(IDX[recortadas].strftime("%Y-%m")).to_numpy())),
          "las horas recortadas no quedan en el precio de escasez de su mes")

    diaria = c.groupby(IDX.floor("D")).mean()
    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 3.0))
    ax.plot(IDX, c.to_numpy(), color="#B9B9B9", lw=0.35, zorder=2)
    ax.plot(diaria.index + pd.Timedelta(hours=12), diaria.to_numpy(), color=E.TINTA,
            lw=1.2, zorder=4)
    # El precio de escasez superior, escalón mensual (el último mes, hasta el
    # final del horizonte).
    fin = IDX[-1] + pd.Timedelta(hours=1)
    for k, mes in enumerate(meses):
        a = max(pd.Timestamp(mes + "-01"), IDX[0])
        b = min(pd.Timestamp(mes + "-01") + pd.offsets.MonthBegin(1), fin)
        ax.plot([a, b], [pes[mes], pes[mes]], color=E.ALERTA, lw=1.3, zorder=3,
                solid_capstyle="butt")
    ax.plot(IDX[recortadas], c[recortadas].to_numpy(), ls="none", marker="x",
            color=E.ALERTA, markersize=4.5, mew=1.1, zorder=5)
    media = float(c.mean())
    ax.axhline(media, color=E.MECANISMOS["P2P"], lw=0.9, ls=(0, (4, 2)), zorder=3)
    ax.text(IDX[-1] + pd.Timedelta(days=2), media, f"media\n{num(media, 2)}",
            ha="left", va="center", fontsize=8.2, color=E.MECANISMOS["P2P"])
    ax.text(IDX[-1] + pd.Timedelta(days=2), float(pes.iloc[-1]),
            "precio de\nescasez\nsuperior", ha="left", va="center", fontsize=8.2,
            color=E.ALERTA)
    ax.set_xlim(IDX[0], fin)
    ax.set_ylim(0, 1000)
    eje_num(ax, "y")
    ax.set_ylabel("Precio de bolsa (COP/kWh)")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(
        lambda v, _: E.fmt_fecha(mdates.num2date(v), "mes")))
    ax.grid(axis="x", visible=False)
    ax.legend(handles=[
        Line2D([], [], color="#B9B9B9", lw=0.8, label="horaria, topada"),
        Line2D([], [], color=E.TINTA, lw=1.2, label="media diaria"),
        Line2D([], [], ls="none", marker="x", color=E.ALERTA, mew=1.1,
               label=f"{int(recortadas.sum())} horas recortadas por el techo"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False, ncol=3,
        fontsize=8.2)
    fig.tight_layout()

    datos = pd.DataFrame({"hora": IDX.strftime("%Y-%m-%d %H:%M"),
                          "bolsa_xm_COP_kWh": p.to_numpy(),
                          "bolsa_topada_COP_kWh": c.to_numpy(),
                          "pes_superior_COP_kWh": pes.reindex(IDX.strftime("%Y-%m")).to_numpy(),
                          "recortada": recortadas.to_numpy(),
                          "media_diaria_topada_COP_kWh":
                              diaria.reindex(IDX.floor("D")).to_numpy()})
    return guardar(fig, "c4_bolsa", datos, [
        f"data/precios_bolsa_xm_api.csv (sha256 {_sha256(cache)[:16]}…) y "
        f"data/precios_escasez_creg.csv (sha256 "
        f"{_sha256(RAIZ / 'data' / 'precios_escasez_creg.csv')[:16]}…), leídos con "
        "load_xm_prices y apply_creg101066_ceiling (data/xm_prices.py); dato de "
        "entrada, figura descriptiva",
        "compuerta: medias 181,95 y 181,33 COP/kWh, 18 horas recortadas y precio "
        "de escasez de 829,27 a 928,33 COP/kWh iguales a " + con_huella(CIFRAS),
    ])


# ═════════════════════════════════════════════════════════════════════════════
# Capítulo 5
# ═════════════════════════════════════════════════════════════════════════════
def _tarifas() -> dict:
    out = {}
    for com, f in (("ASC", "tarifas_asc_mensual.csv"), ("CEDENAR", "tarifas_cedenar_mensual.csv")):
        t = pd.read_csv(RAIZ / "data" / f, comment="#")
        t = t[(t.categoria == "oficial") & (t.nivel_tension == 2)
              & (t.propiedad == "cedenar")].set_index("mes")
        out[com] = t
    return out


def _comercializador(inst: str) -> str:
    return "CEDENAR" if inst == "Cesmag" else "ASC"


def _elige_hora_banda(h: pd.DataFrame, f: pd.DataFrame) -> int:
    """La primera hora de E0 que enseña a la vez las dos cotas y las dos
    reglas: régimen interiores o topados, dos vendedores con pisos distintos
    y el piso del juego por encima del menor (vendedor marginal), tres o más
    compradores, compradores en dos posiciones de precio y al menos uno en
    el precio interior."""
    for k in h[h.regimen.isin(["interiores", "topados"])].sort_values("hora").hora:
        x = f[f.hora == k]
        pis = x.groupby("vendedor").piso_vendedor.first()
        pos = x.groupby("comprador").precio_reposo.first().round(2)
        tec = x.groupby("comprador").techo_comprador.first().round(2)
        pj = float(h.loc[h.hora == k, "piso_juego"].iloc[0])
        interior = ((pos > pj + 0.01) & (pos < tec - 0.01)).any()
        if (len(pis) >= 2 and pis.nunique() >= 2 and pj > pis.min() + 1e-3
                and x.comprador.nunique() >= 3 and pos.nunique() >= 2 and interior):
            return int(k)
    raise FiguraError("ninguna hora de E0 cumple el criterio de la figura de la banda")


def c5_banda_hora():
    """Figura 5.1 — La banda de precios en una hora de la comunidad medida.

    Del almacén de E0 (tablas horas, flujos y agentes). La hora se elige
    por un criterio fijo (``_elige_hora_banda``), no por lo favorable. Las
    compuertas comprueban, en esa hora, el techo y el piso contra las
    tarifas publicadas (Tabla 4.5), el presupuesto (5.6), el piso del juego
    como piso de un vendedor despachado, la conservación del ingreso (5.11)
    y la descomposición de la prima (5.13).
    """
    h, r_h = almacen("E0", "horas")
    f, r_f = almacen("E0", "flujos")
    ag, r_a = almacen("E0", "agentes")
    k = _elige_hora_banda(h, f)
    hh = h[h.hora == k].iloc[0]
    x = f[f.hora == k]
    a = ag[ag.hora == k].set_index("agente")
    mes = str(hh.mes)
    tar = _tarifas()

    vend = x.groupby("vendedor").agg(piso=("piso_vendedor", "first"), kwh=("kwh", "sum"))
    comp = x.groupby("comprador").agg(techo=("techo_comprador", "first"),
                                      reposo=("precio_reposo", "first"),
                                      liquidado=("precio", "first"), kwh=("kwh", "sum"))
    exige(bool((x.groupby("comprador").precio.nunique() == 1).all()),
          "un comprador con dos precios liquidados")
    for j, v in vend.iterrows():
        t = tar[_comercializador(j)].loc[mes]
        igual(v.piso, float(t.CU_aplicado - t.Cvm), 0.01, f"piso de {j} = permuta (CU − Cv)")
        igual(v.kwh, float(a.loc[j, "vende_p2p"]), 1e-3, f"energía que vende {j}")
    for i, c in comp.iterrows():
        igual(c.techo, float(tar[_comercializador(i)].loc[mes, "CU_aplicado"]), 0.01,
              f"techo de {i} = su costo unitario")
        igual(c.kwh, float(a.loc[i, "compra_p2p"]), 1e-3, f"energía que compra {i}")
        igual(c.liquidado, min(float(hh.precio_uniforme), c.techo), 1e-3,
              f"precio liquidado de {i} = min(uniforme, techo)")
    pj = float(hh.piso_juego)
    exige(any(abs(pj - v) < 1e-3 for v in vend.piso), "el piso del juego no es el de un vendedor")
    exige(bool((vend.piso <= pj + 1e-3).all()), "un vendedor despachado con piso sobre el del juego")
    n = len(comp)
    sigma = (n - 1) / n
    pres = float((pj + sigma * (comp.techo - pj)).sum())
    igual(pres, float(hh.presupuesto), 0.05, "presupuesto (5.6)")
    igual(float(comp.reposo.sum()), pres, 0.05, "los precios del reposo suman el presupuesto")
    igual(float((comp.liquidado * comp.kwh).sum()), float((comp.reposo * comp.kwh).sum()), 0.05,
          "conservación del ingreso (5.11)")
    prima = float(x.prima_vendedor.sum())
    igual(prima, float(hh.renta_inframarginal + hh.parte_juego), 0.05,
          "prima = renta inframarginal + parte del juego (5.13)")

    # ── Dibujo ────────────────────────────────────────────────────────────
    vend = vend.loc[[i for i in AGENTS if i in vend.index]]
    comp = comp.loc[[i for i in AGENTS if i in comp.index]]
    filas_v = list(vend.index)
    filas_c = list(comp.index)
    y_v = {j: i for i, j in enumerate(filas_v)}
    y_c = {c_: len(filas_v) + 1.0 + i for i, c_ in enumerate(filas_c)}
    pu = float(hh.precio_uniforme)

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 3.25))
    lo = float(vend.piso.min()) - 12
    hi = float(comp.techo.max()) + 12
    # Banda de cada comprador: del piso del juego a su techo.
    for i, c in comp.iterrows():
        y = y_c[i]
        ax.plot([pj, c.techo], [y, y], color=E.APOYO, lw=9, solid_capstyle="butt", zorder=1)
        ax.plot([c.techo], [y], marker="|", markersize=13, mew=2.0, color=E.TINTA, zorder=4)
        ax.plot([c.reposo], [y], marker="o", markersize=7, mfc="white", mec=E.TINTA,
                mew=1.4, zorder=5)
        ax.plot([c.liquidado], [y], marker="D", markersize=5.5, color=E.MECANISMOS["P2P"],
                zorder=6)
        ax.text(hi + 1, y, f"recibe {num(c.kwh, 2)} kWh", ha="left", va="center",
                fontsize=8.2, color=E.TINTA)
    for j, v in vend.iterrows():
        y = y_v[j]
        ax.plot([v.piso], [y], marker="^", markersize=8, color=E.TINTA, zorder=5)
        ax.text(hi + 1, y, f"vende {num(v.kwh, 2)} kWh", ha="left", va="center",
                fontsize=8.2, color=E.TINTA)
        if v.piso < pj - 1e-3:
            ax.annotate("", xy=(pj, y), xytext=(v.piso, y),
                        arrowprops=dict(arrowstyle="-|>", color=E.NEUTRO, lw=1.0,
                                        shrinkA=5, shrinkB=0), zorder=3)
            ax.text((v.piso + pj) / 2, y - 0.22, "renta inframarginal",
                    ha="center", va="bottom", fontsize=8.2, color=E.NEUTRO)
    ax.axvline(pj, color=E.TINTA, lw=0.9, ls=(0, (3, 2)), zorder=2)
    ax.axvline(pu, color=E.MECANISMOS["P2P"], lw=1.0, zorder=2)
    ytop = -0.95
    ax.text(pj, ytop, f"piso del juego\n{num(pj, 2)}", ha="right", va="bottom",
            fontsize=8.2, color=E.TINTA)
    ax.text(pu, ytop, f" precio uniforme\n {num(pu, 2)}", ha="left", va="bottom",
            fontsize=8.2, color=E.MECANISMOS["P2P"])

    etiquetas = ([E.etiqueta_institucion(j) for j in filas_v]
                 + [E.etiqueta_institucion(i) for i in filas_c])
    ys = [y_v[j] for j in filas_v] + [y_c[i] for i in filas_c]
    ax.set_yticks(ys)
    ax.set_yticklabels(etiquetas)
    for tick, inst in zip(ax.get_yticklabels(), filas_v + filas_c):
        tick.set_color(E.color_institucion(inst))
        tick.set_fontweight("bold")
    ax.set_ylim(max(ys) + 0.7, ytop - 0.05)
    ax.axhline(len(filas_v) + 0.0, color="#CCCCCC", lw=0.6)
    ax.text(lo + 1, -0.62, "vendedores", fontsize=8.2, color=E.NEUTRO,
            style="italic", va="center")
    ax.text(lo + 1, len(filas_v) + 0.38, "compradores", fontsize=8.2, color=E.NEUTRO,
            style="italic", va="center")
    ax.set_xlim(lo, hi)
    eje_num(ax, "x")
    ax.set_xlabel("Precio (COP/kWh)")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[
        Line2D([], [], ls="none", marker="^", markersize=7, color=E.TINTA,
               label="piso del vendedor (permuta)"),
        Line2D([], [], ls="none", marker="|", markersize=11, mew=2.0, color=E.TINTA,
               label="techo del comprador (costo unitario)"),
        Patch(facecolor=E.APOYO, label="banda del comprador en el juego"),
        Line2D([], [], ls="none", marker="o", markersize=6.5, mfc="white", mec=E.TINTA,
               mew=1.4, label="precio del reposo"),
        Line2D([], [], ls="none", marker="D", markersize=5, color=E.MECANISMOS["P2P"],
               label="precio liquidado"),
    ], loc="upper center", bbox_to_anchor=(0.46, -0.2), ncol=3, frameon=False,
        fontsize=8.0, columnspacing=1.2, handletextpad=0.5)
    fig.tight_layout()

    filas = []
    for j, v in vend.iterrows():
        filas.append(dict(papel="vendedor", institucion=j, piso_COP_kWh=v.piso,
                          techo_COP_kWh=np.nan, precio_reposo_COP_kWh=np.nan,
                          precio_liquidado_COP_kWh=np.nan, kWh=v.kwh))
    for i, c in comp.iterrows():
        filas.append(dict(papel="comprador", institucion=i, piso_COP_kWh=np.nan,
                          techo_COP_kWh=c.techo, precio_reposo_COP_kWh=c.reposo,
                          precio_liquidado_COP_kWh=c.liquidado, kWh=c.kwh))
    datos = pd.DataFrame(filas)
    datos["hora"] = str(hh.fecha)
    datos["regimen"] = str(hh.regimen)
    datos["piso_juego_COP_kWh"] = pj
    datos["precio_uniforme_COP_kWh"] = pu
    datos["presupuesto_COP_kWh"] = float(hh.presupuesto)
    return guardar(fig, "c5_banda_hora", datos, [
        *r_h, *r_f, *r_a,
        f"hora {k} de E0 ({hh.fecha}), elegida con _elige_hora_banda: la primera del "
        "horizonte en régimen interiores o topados con dos vendedores de pisos "
        "distintos, piso del juego por encima del menor, tres o más compradores y "
        "compradores en dos posiciones de precio",
        "compuerta: pisos = CU − Cv y techos = CU de data/tarifas_*_mensual.csv (fila "
        "oficial, nivel 2; Tabla 4.5); presupuesto (5.6); precio liquidado = "
        "min(uniforme, techo); conservación del ingreso (5.11); prima = renta "
        "inframarginal + parte del juego (5.13)",
        "las columnas piso, techo y precios del CSV van vacías donde no aplican al papel",
    ])


def c5_barrido_sigma():
    """Figura 5.2 — La parte del vendedor en los 13 casos con cada sigma.

    De las comparaciones del barrido (CANON §14.4): la columna
    ``parte_vendedor_nueva`` de la fila «comunidad» de compara_sigma{0,05,1}
    y, para la base, ``parte_vendedor_vieja``, que es la del canon. Las
    compuertas reproducen la Tabla 5.4 y la cabecera de CANON §4.
    """
    rastro = []
    tablas = {}
    for s_, nom in (("0", "compara_sigma0.csv"), ("0,5", "compara_sigma05.csv"),
                    ("1", "compara_sigma1.csv")):
        p = SIGMA / nom
        rastro.append(con_huella(p))
        t = pd.read_csv(p, comment="#")
        t = t[t.institucion == "comunidad"].set_index("caso")
        exige(set(t.index) == set(CASOS), f"{nom}: no están los 13 casos")
        tablas[s_] = t
    base = tablas["0"].parte_vendedor_vieja
    for s_ in ("0,5", "1"):
        exige(bool(np.allclose(tablas[s_].parte_vendedor_vieja.loc[CASOS], base.loc[CASOS])),
              "las tres comparaciones no tienen la misma base")
    canon = pd.read_csv(ENTREGA / "compara_matriz_reposo.csv", comment="#")
    rastro.append(con_huella(ENTREGA / "compara_matriz_reposo.csv"))
    canon = canon[canon.institucion == "comunidad"].set_index("caso")
    exige(bool(np.allclose(canon.parte_vendedor_nueva.loc[CASOS], base.loc[CASOS])),
          "la base del barrido no es la parte del vendedor del canon")
    d = pd.DataFrame({"sigma_0": tablas["0"].parte_vendedor_nueva,
                      "sigma_0,5": tablas["0,5"].parte_vendedor_nueva,
                      "base": base,
                      "sigma_1": tablas["1"].parte_vendedor_nueva}).loc[CASOS]
    exige(not d.isna().any().any(), "parte del vendedor no finita")
    # Tabla 5.4 y CANON §4.
    for col, v in (("sigma_0", 0.049), ("sigma_0,5", 0.405), ("base", 0.542), ("sigma_1", 0.962)):
        igual(round(float(d.loc["E0", col]), 3), v, 0, f"parte del vendedor de E0, {col}")
    for col, (cmin, vmin, cmax, vmax) in (("sigma_0", ("K1", 0.000, "E2", 0.364)),
                                          ("sigma_0,5", ("E5", 0.112, "K1", 0.487)),
                                          ("sigma_1", ("E5", 0.389, "K1", 1.000))):
        exige(d[col].idxmin() == cmin and d[col].idxmax() == cmax,
              f"{col}: el menor o el mayor no es el de la Tabla 5.4")
        igual(round(float(d[col].min()), 3), vmin, 0, f"{col}, menor")
        igual(round(float(d[col].max()), 3), vmax, 0, f"{col}, mayor")
    for caso, v in (("E1", 0.472), ("E5", 0.132), ("K1", 0.628), ("SINU", 0.483)):
        igual(round(float(d.loc[caso, "base"]), 3), v, 0, f"parte del vendedor de {caso}, canon")
    for s_ in ("0", "0,5", "1"):
        exige(float(tablas[s_].kwh_transada_dif.abs().max()) < 1e-5,
              f"sigma {s_}: la energía cambia")

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 3.6))
    y = np.arange(len(CASOS))
    tonos = {"sigma_0": "#C9D6DE", "sigma_0,5": "#7FA3B8", "sigma_1": "#1F3F52"}
    for i, caso in enumerate(CASOS):
        fila = d.loc[caso]
        ax.plot([fila.min(), fila.max()], [i, i], color="#D0D0D0", lw=1.0, zorder=1)
    for col, lab in (("sigma_0", r"$\sigma = 0$"), ("sigma_0,5", r"$\sigma = 0{,}5$"),
                     ("sigma_1", r"$\sigma = 1$")):
        ax.plot(d[col], y, ls="none", marker="o", markersize=6.3, color=tonos[col],
                mec="#555555", mew=0.5, zorder=3, label=lab)
    # La base va en tinta y con otra forma: el naranja es de Mariana en la
    # figura vecina del capítulo.
    ax.plot(d["base"], y, ls="none", marker="D", markersize=6.8, mfc="white",
            mec=E.TINTA, mew=1.6, zorder=4,
            label=r"base, $\sigma = (|\mathcal{I}^{*}_k|-1)/|\mathcal{I}^{*}_k|$")
    ax.set_yticks(y)
    ax.set_yticklabels(CASOS)
    ax.set_ylim(len(CASOS) - 0.5, -0.5)
    ax.set_xlim(-0.02, 1.02)
    ax.xaxis.set_major_locator(MultipleLocator(0.2))
    eje_num(ax, "x", 1)
    ax.set_xlabel("Parte del vendedor")
    ax.set_ylabel("Caso")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=4, frameon=False,
              handletextpad=0.3, columnspacing=1.2)
    fig.tight_layout()

    datos = d.reset_index(names="caso")
    for s_, t in tablas.items():
        datos[f"kwh_dif_max_sigma_{s_}"] = float(t.kwh_transada_dif.abs().max())
    return guardar(fig, "c5_barrido_sigma", datos, [
        *rastro,
        "fila «comunidad» de cada comparación: parte_vendedor_nueva (sigma) y "
        "parte_vendedor_vieja (base del canon, igual a parte_vendedor_nueva de "
        "compara_matriz_reposo.csv); CANON §14.4 y §4",
        "compuerta: E0 0,049, 0,405, 0,542 y 0,962; menor y mayor de cada sigma como "
        "en la Tabla 5.4; energía transada sin cambio (< 1e-5 kWh)",
    ])


# ═════════════════════════════════════════════════════════════════════════════
# Capítulo 6
# ═════════════════════════════════════════════════════════════════════════════
def _particion_anexo4(s_: pd.Series, d_: pd.Series):
    """(c, x, hx) de (6.4) y (6.5) sobre las series de un mes."""
    imp = float(d_.sum())
    acum = s_.cumsum()
    hit = acum[acum >= imp]
    x = s_ * 0.0
    if len(hit) == 0:
        return s_.copy(), x, None, imp, acum
    hx = hit.index[0]
    x[s_.index > hx] = s_[s_.index > hx]
    x[hx] = float(acum[hx]) - imp
    return s_ - x, x, hx, imp, acum


def c6_corte_hx(caso: str = "E1", inst: str = "Udenar"):
    """Figura 6.1 — El corte h_x del Anexo 4 en un mes concreto.

    Series brutas de la autogeneración individual (C1) del almacén del caso.
    El mes se elige por criterio: el primer mes completo del horizonte en
    que el corte deja como exceso más de una cuarta parte de la inyección
    del mes. La compuerta recalcula la ganancia de C1 de cada par
    institución-mes del caso con (6.4), (6.5) y (6.9) y exige que reproduzca
    la columna C1 de la tabla escenarios del almacén; y que los pares que
    agotan el crédito sean los de la Tabla 4.3.
    """
    from data.xm_prices import get_pi_bolsa
    from data.xm_data_loader import T_END, T_START
    IDX = pd.date_range(T_START, T_END, freq="1h", inclusive="left")
    pb = pd.Series(get_pi_bolsa(len(IDX), T_START, T_END), IDX)
    ag, r_a = almacen(caso, "agentes")
    es, r_e = almacen(caso, "escenarios")
    c1 = es[es.escenario == "C1"].groupby(["agente", "mes"]).valor.sum()
    tar = _tarifas()
    # La deducción de (6.9) es la del numeral 1 solo si ninguna planta del
    # caso pasa de 100 kW (Tabla 4.3).
    for a_ in ag.agente.unique():
        exige(cifra(f"capacidad_kW__{caso}__{a_}") <= 100,
              f"{caso}: la planta de {a_} es del numeral 2")
    agotan = 0
    peor = 0.0
    elegido = None
    for a_, x_ in ag.groupby("agente"):
        x_ = x_.set_index("fecha").sort_index()
        s_ = (x_.generacion - x_.demanda).clip(lower=0)
        d_ = (x_.demanda - x_.generacion).clip(lower=0)
        au = np.minimum(x_.generacion, x_.demanda)
        for mes, xm in x_.groupby("mes"):
            t = tar[_comercializador(a_)].loc[mes]
            cc, xx, hx, imp, acum = _particion_anexo4(s_[xm.index], d_[xm.index])
            v = float((au[xm.index] * t.CU_aplicado + cc * (t.CU_aplicado - t.Cvm)
                       + xx * pb[xm.index]).sum())
            peor = max(peor, abs(v - float(c1.loc[(a_, mes)])))
            if hx is not None:
                agotan += 1
            completo = xm.index[0].day == 1 and (xm.index[-1] + pd.Timedelta(hours=1)).day == 1
            if (a_ == inst and elegido is None and hx is not None and completo
                    and float(xx.sum()) > 0.25 * float(s_[xm.index].sum())):
                elegido = (mes, cc, xx, hx, imp, acum, s_[xm.index], d_[xm.index])
    exige(peor < 1.0, f"la partición no reproduce C1 del almacén ({peor:.3f} COP)")
    igual(agotan, cifra(f"pares_agotan_credito__{caso}"), 0, f"pares que agotan el crédito en {caso}")
    exige(elegido is not None, f"{inst} no tiene en {caso} un mes que cumpla el criterio")
    mes, cc, xx, hx, imp, acum, s_m, d_m = elegido

    horas = acum.index
    t_dias = (horas - horas[0]) / pd.Timedelta(days=1) + 1.0
    t_hx = float((hx - horas[0]) / pd.Timedelta(days=1) + 1.0)
    credito = np.minimum(acum.to_numpy(), imp)
    iny = float(s_m.sum())
    exc = float(xx.sum())
    igual(float(cc.sum()), imp, 1e-3, "el crédito del mes es la importación")

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 3.0))
    c_cred = E.VENDE
    c_exc = E.ALERTA
    ax.fill_between(t_dias, 0, credito, color=c_cred, alpha=0.22, lw=0, zorder=1)
    ax.fill_between(t_dias, imp, acum.to_numpy(), where=acum.to_numpy() >= imp,
                    color=c_exc, alpha=0.30, lw=0, zorder=1, interpolate=True)
    ax.plot(t_dias, acum.to_numpy(), color=E.TINTA, lw=1.5, zorder=3)
    ax.axhline(imp, color=E.TINTA, lw=0.9, ls=(0, (4, 2)), zorder=2)
    ax.axvline(t_hx, color=c_exc, lw=1.0, zorder=2)
    ultimo = float(t_dias[-1])
    ax.text(1.6, imp + 40, f"importación del mes: {num(imp, 1)} kWh", ha="left",
            va="bottom", fontsize=8.5, color=E.TINTA)
    ax.text(t_hx - 0.3, iny * 1.19, f"corte $h_x$: {E.fmt_fecha(hx, 'dia_corto')}, "
            f"{hx.hour}:00", ha="right", va="center", fontsize=8.5, color=c_exc)
    ax.text((t_hx + ultimo) / 2, imp * 0.5, f"crédito: {num(imp, 1)} kWh\na la permuta",
            ha="center", va="center", fontsize=8.5, color=E.VENDE)
    ax.annotate(f"exceso: {num(exc, 1)} kWh\na la bolsa de cada hora",
                xy=(ultimo - 2.5, imp + 0.62 * (iny - imp) - 250),
                xytext=(t_hx - 0.6, imp + 0.62 * (iny - imp)),
                ha="right", va="center", fontsize=8.5, color=c_exc,
                arrowprops=dict(arrowstyle="-", color=c_exc, lw=0.8, shrinkA=2))
    ax.text(ultimo + 0.4, iny, f"inyección\nacumulada\n{num(iny, 1)} kWh", ha="left",
            va="center", fontsize=8.5, color=E.TINTA)
    ax.set_xlim(0.8, ultimo + 0.2)
    ax.set_ylim(0, iny * 1.28)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.set_xlabel(f"Día de {E.fmt_fecha(pd.Timestamp(mes + '-01'), 'mes_largo')} de "
                  f"{mes[:4]}")
    ax.set_ylabel("Energía (kWh)")
    eje_num(ax, "y")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()

    datos = pd.DataFrame({"hora": horas.strftime("%Y-%m-%d %H:%M"),
                          "inyeccion_kWh": s_m.to_numpy(float),
                          "importacion_kWh": d_m.to_numpy(float),
                          "inyeccion_acumulada_kWh": acum.to_numpy(float),
                          "credito_kWh": cc.to_numpy(float),
                          "exceso_kWh": xx.to_numpy(float)})
    datos["importacion_mes_kWh"] = imp
    datos["hora_corte"] = hx.strftime("%Y-%m-%d %H:%M")
    return guardar(fig, "c6_corte_hx", datos, [
        *r_a, *r_e,
        f"caso {caso}, {inst}, mes {mes}: series brutas de C1 (inyección = max(G − D, 0), "
        "importación = max(D − G, 0)) de la tabla agentes",
        "mes elegido: el primer mes completo en que el corte deja como exceso más de "
        "una cuarta parte de la inyección",
        "compuerta: con (6.4), (6.5) y (6.9), la ganancia de C1 de los 45 pares "
        "institución-mes reproduce la columna C1 de la tabla escenarios del almacén "
        f"(mayor diferencia {peor:.3f} COP); pares que agotan el crédito iguales a "
        + con_huella(CIFRAS),
        "bolsa: get_pi_bolsa (data/xm_prices.py); tarifas: data/tarifas_*_mensual.csv",
    ])


# ═════════════════════════════════════════════════════════════════════════════
# Capítulo 7
# ═════════════════════════════════════════════════════════════════════════════
# Reglas del capítulo: C4_mensual no aparece (alias de C4); el P2P y C2 van
# fundidos en el agregado (coinciden, CANON §6.1); C5 se rotula como
# referencia no elegible y se dibuja hueco; los signos frágiles que el texto
# declara se marcan; ninguna dominancia hora a hora.
CIFRAS7 = SALIDAS / "cifras_cap07_2026-09-28" / "cifras.csv"
D72 = ENTREGA / "optimalidad_D72"
SUBP = SALIDAS / "subperiodos_2026-09-27"
GSA = SALIDAS / "entrega_gsa_directo_completo_2026-09-27" / "SALIDAS_SERVIDOR" / "gsa_directo"

# Mecanismos del capítulo 7: color y forma. La forma lleva la distinción
# que tiene que sobrevivir impresa.
MEC7 = {
    "P2P":           ("#1F6F8B", "o", "P2P (y C2)"),
    "P2P_colectivo": ("#7DB3C6", "s", "P2P por el colectivo"),
    "C1":            ("#8C8C8C", "^", "C1"),
    "C3":            ("#9B6BA8", "v", "C3"),
    "C4":            ("#D08A2E", "D", "C4"),
    "C5":            ("#5B8C5A", "P", "C5 (referencia no elegible)"),
}
_CIFRAS7: pd.DataFrame | None = None


def cifra7(clave: str):
    """Una cifra de cifras_cap07_2026-09-28 (§14.18, C-230), por su clave."""
    global _CIFRAS7
    if _CIFRAS7 is None:
        con_huella(CIFRAS7)
        _CIFRAS7 = pd.read_csv(CIFRAS7, dtype={"valor": str}).set_index("clave")
    exige(clave in _CIFRAS7.index, f"cifras_cap07 no tiene la clave {clave}")
    v = _CIFRAS7.loc[clave, "valor"]
    try:
        return float(v)
    except ValueError:
        return v


def _hoja(caso: str, hoja: str) -> tuple[pd.DataFrame, str]:
    p = MATRIZ / caso / "outputs" / "resultados_comparacion.xlsx"
    return pd.read_excel(p, sheet_name=hoja), con_huella(p)


def _resumen_13() -> tuple[pd.DataFrame, list[str]]:
    """Ganancia neta de la comunidad (COP) por caso y mecanismo, hoja Resumen."""
    filas, rastro = {}, []
    for caso in CASOS:
        r, h = _hoja(caso, "Resumen")
        rastro.append(h)
        filas[caso] = r.set_index("Escenario")["Ganancia_neta_COP"].astype(float)
    t = pd.DataFrame(filas).T.loc[CASOS]
    exige(not t.isna().any().any(), "Resumen con valores vacíos")
    # Las dos identidades del canon (§6.1), comprobadas antes de fundir.
    exige(float((t.P2P - t.C2).abs().max()) < 1e-3, "P2P y C2 no coinciden en el agregado")
    exige(float((t.C4 - t.C4_mensual).abs().max()) == 0.0, "C4_mensual no es alias de C4")
    return t, rastro


def _marcar(ax, x, y, estilo: str = "solido", r: float = 9.0) -> None:
    """Anillo de signo frágil alrededor de un punto."""
    ax.plot([x], [y], ls="none", marker="o", markersize=r, mfc="none",
            mec=E.TINTA, mew=1.0 if estilo == "solido" else 0.8,
            zorder=6)


def c7_brechas_comunidad():
    """Figura 7.1 — La ganancia neta de cada mecanismo frente a C1, por caso.

    En porcentaje de la ganancia de C1 y no en MCOP: con MCOP la fila de E0
    (brechas de décimas) quedaría aplastada contra el cero por la de E3 (de
    decenas). Los valores en MCOP van en el CSV. Anillos: signos frágiles
    que el texto declara (sección 7.2): C4 − C1 en E4, E5 e I1 y el colectivo
    − C1 en E4 y E5 (P de inversión > 50 %), y P2P − C5 en E4 y E5.
    """
    t, rastro = _resumen_13()
    for caso in CASOS:
        for k, a, b in (("P2P_menos_C1", "P2P", "C1"), ("P2P_menos_C4", "P2P", "C4"),
                        ("P2P_menos_C5", "P2P", "C5"), ("P2P_menos_C3", "P2P", "C3"),
                        ("colectivo_menos_C1", "P2P_colectivo", "C1")):
            igual((t.loc[caso, a] - t.loc[caso, b]) / 1e6,
                  cifra7(f"comunidad__{caso}__{k}"), 1e-6, f"{caso} {k}")
        igual(100 * (t.loc[caso, "P2P"] - t.loc[caso, "C1"]) / t.loc[caso, "C1"],
              cifra7(f"comunidad__{caso}__P2P_menos_C1_pct_C1"), 1e-6, f"{caso} P2P−C1 %")
    exige(cifra7("orden__casos_C4_segundo") == "E4, E5, I1", "C4 segundo no es E4, E5, I1")
    fragil = {}
    for item in str(cifra7("fragiles__comunidad__lista_mayor_50")).split(";"):
        caso, brecha, _p = item.split()
        mec = {"C4_menos_C1": "C4", "P2Pcol_menos_C1": "P2P_colectivo"}[brecha]
        fragil.setdefault(caso, set()).add(mec)
    exige(fragil == {"E4": {"C4", "P2P_colectivo"}, "E5": {"C4", "P2P_colectivo"},
                     "I1": {"C4"}}, f"frágiles de comunidad inesperados: {fragil}")
    # P2P − C5 frágil en E4 y E5 (texto, sección 7.2.3; CANON §13.3 y §13.6).
    for caso in ("E4", "E5"):
        fragil[caso].add("C5")

    mecs = ["C3", "C5", "C4", "P2P_colectivo", "P2P"]
    pct = pd.DataFrame({m: 100 * (t[m] - t.C1) / t.C1 for m in mecs})
    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 4.1))
    y = np.arange(len(CASOS))
    for i, caso in enumerate(CASOS):
        ax.plot([pct.loc[caso].min(), pct.loc[caso].max()], [i, i], color="#DDDDDD",
                lw=0.9, zorder=1)
    ax.axvline(0, color=E.TINTA, lw=1.0, zorder=2)
    for m in mecs:
        c, mk, lab = MEC7[m]
        hueco = m == "C5"
        # C4 y el colectivo casi coinciden en varios casos: el rombo de C4 va
        # más grande y el cuadrado encima, más pequeño, para que se vean los dos.
        tam = {"P2P": 7, "C4": 8.2, "P2P_colectivo": 4.8}.get(m, 6.2)
        ax.plot(pct[m], y, ls="none", marker=mk, markersize=tam,
                mfc="white" if hueco else c, mec=c, mew=1.4 if hueco else 0.4,
                zorder=4, label=lab)
    for caso, ms in fragil.items():
        for m in ms:
            _marcar(ax, pct.loc[caso, m], CASOS.index(caso), r=12)
    ax.set_yticks(y)
    ax.set_yticklabels(CASOS)
    ax.set_ylim(len(CASOS) - 0.5, -0.5)
    eje_num(ax, "x")
    ax.set_xlabel("Ganancia neta frente a C1 (% de la ganancia de C1)")
    ax.grid(axis="y", visible=False)
    ax.text(0.4, -0.85, "C1", ha="left", va="bottom", fontsize=8.5, color=E.TINTA)
    manejadores, _ = ax.get_legend_handles_labels()
    manejadores = manejadores[::-1]
    manejadores.append(Line2D([], [], ls="none", marker="o", markersize=11, mfc="none",
                              mec=E.TINTA, mew=1.0, label="signo frágil"))
    ax.legend(handles=manejadores, loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=3, frameon=False, fontsize=8.2, columnspacing=1.2)
    fig.tight_layout()

    datos = pd.DataFrame({"caso": CASOS})
    for m in mecs:
        datos[f"{m}_menos_C1_MCOP"] = ((t[m] - t.C1) / 1e6).to_numpy()
        datos[f"{m}_menos_C1_pct_C1"] = pct[m].to_numpy()
        datos[f"{m}_fragil"] = [m in fragil.get(c_, set()) for c_ in CASOS]
    return guardar(fig, "c7_brechas_comunidad", datos, [
        *rastro,
        "hoja Resumen, columna Ganancia_neta_COP; C2 fundido con el P2P (diferencia "
        "< 1e-3 COP comprobada) y sin C4_mensual (alias exacto comprobado)",
        "compuerta: brechas y P2P − C1 en % iguales a " + con_huella(CIFRAS7),
        "frágiles: fragiles__comunidad__lista_mayor_50 de cifras_cap07 y P2P − C5 en "
        "E4 y E5 (texto, sección 7.2.3; CANON §13.3 y §13.6)",
    ])


def c7_descomposicion():
    """Figura 7.2 — P2P − C1 partido en la banda y la reclasificación."""
    p = SALIDAS / "descomposicion_p2p_2026-09-27" / "descomposicion_13casos.csv"
    rastro = [con_huella(p)]
    d = pd.read_csv(p)
    d = d[d.agente == "comunidad"].set_index("caso").loc[CASOS]
    t, r2 = _resumen_13()
    rastro += r2
    tabla74 = {"E0": (0.296, 0.296, 0.000), "E1": (2.571, 1.666, 0.905),
               "E2": (4.846, 2.523, 2.322), "E3": (6.765, 4.150, 2.614),
               "E4": (6.167, 5.796, 0.370), "E5": (3.240, 4.509, -1.270),
               "P1": (0.764, 0.623, 0.142), "P2": (10.659, 10.659, 0.000),
               "K1": (0.284, 0.284, 0.000), "I1": (7.340, 6.163, 1.177),
               "N1": (1.123, 0.980, 0.143), "CV2": (0.482, 0.482, 0.000),
               "SINU": (0.079, 0.079, 0.000)}
    for caso, (tot, ban, rec) in tabla74.items():
        igual(round(d.loc[caso, "P2P_menos_C1"] / 1e6, 3), tot, 0.0015, f"{caso} P2P − C1")
        igual(round(d.loc[caso, "banda"] / 1e6, 3), ban, 0.0015, f"{caso} banda")
        igual(round(d.loc[caso, "reclasificacion"] / 1e6, 3), rec, 0.0015, f"{caso} reclasificación")
        # El almacén guarda en float32: a 322 MCOP (P2) su paso es de 32 COP.
        igual(d.loc[caso, "P2P_menos_C1"], t.loc[caso, "P2P"] - t.loc[caso, "C1"],
              max(5.0, 2e-7 * t.loc[caso, "P2P"]), f"{caso} P2P − C1 frente a Resumen")
        igual(d.loc[caso, "banda"] + d.loc[caso, "reclasificacion"],
              d.loc[caso, "P2P_menos_C1"], 1.0, f"{caso} banda + reclasificación")

    ban, rec, tot = d.banda / 1e6, d.reclasificacion / 1e6, d.P2P_menos_C1 / 1e6
    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 3.8))
    y = np.arange(len(CASOS))
    c_b, c_r = "#8FBCCC", E.ALERTA
    ax.barh(y, ban, height=0.62, color=c_b, zorder=2, label="banda repartida")
    izq = np.where(rec >= 0, ban, 0.0)
    ax.barh(y, rec, left=izq, height=0.62, color=c_r, alpha=0.85, zorder=2,
            label="reclasificación del crédito")
    ax.plot(tot, y, ls="none", marker="D", markersize=5.5, color=E.TINTA, zorder=4,
            label="P2P − C1")
    for i, caso in enumerate(CASOS):
        ax.text(max(tot[caso], ban[caso]) + 0.15, i, num(tot[caso], 3), va="center",
                ha="left", fontsize=8.0, color=E.TINTA)
    ax.axvline(0, color=E.TINTA, lw=0.9, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(CASOS)
    ax.set_ylim(len(CASOS) - 0.5, -0.5)
    ax.set_xlim(-1.6, 12.2)
    eje_num(ax, "x")
    ax.set_xlabel("Lo que el mercado le gana a C1 (MCOP)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", frameon=False, fontsize=8.2)
    fig.tight_layout()
    datos = pd.DataFrame({"caso": CASOS, "P2P_menos_C1_MCOP": tot.to_numpy(),
                          "banda_MCOP": ban.to_numpy(), "reclasificacion_MCOP": rec.to_numpy(),
                          "banda_vendedor_MCOP": (d.banda_vendedor / 1e6).to_numpy(),
                          "banda_comprador_MCOP": (d.banda_comprador / 1e6).to_numpy()})
    return guardar(fig, "c7_descomposicion", datos, [
        *rastro,
        "filas «comunidad» de descomposicion_13casos.csv (CANON §14.8, H-101, C-210)",
        "compuerta: los 13 casos de la Tabla 7.4 a tres decimales; P2P − C1 igual a "
        "la hoja Resumen (float32 del almacén: hasta 2e-7 del beneficio); banda + reclasificación = "
        "P2P − C1",
    ])


def c7_optimalidad_mensual():
    """Figura 7.3 — P2P − C4 de la comunidad mes a mes en los 13 casos (D72).

    Solo mes y horizonte; ninguna lectura hora a hora (CANON §9 y §12).
    """
    rastro, filas = [], []
    for caso in CASOS:
        p = D72 / f"{caso}_mensual.csv"
        rastro.append(con_huella(p))
        m = pd.read_csv(p)
        m = m[m.agente == "Comunidad"].sort_values("mes")
        exige(len(m) == 9, f"{caso}: no hay nueve meses de la comunidad")
        igual(float(m.delta_COP.sum()) / 1e6, cifra7(f"comunidad__{caso}__P2P_menos_C4"), 1e-6,
              f"{caso}: la suma de los meses no da P2P − C4 del horizonte")
        for _, f in m.iterrows():
            filas.append(dict(caso=caso, mes=f.mes, P2P_menos_C4_MCOP=f.delta_COP / 1e6,
                              domina=f.domina))
    datos = pd.DataFrame(filas)
    neg = datos[datos.P2P_menos_C4_MCOP < 0]
    exige(len(datos) == 117 and len(neg) == 1, "no son 116 de 117 meses a favor del mercado")
    exige(neg.caso.iloc[0] == "I1" and neg.mes.iloc[0] == "2025-12", "el mes en contra no es I1 dic")
    igual(round(neg.P2P_menos_C4_MCOP.iloc[0] * 1e6), -41804, 0.5, "el mes en contra, −41 804 COP")

    meses = sorted(datos.mes.unique())
    piv = datos.pivot(index="caso", columns="mes", values="P2P_menos_C4_MCOP").loc[CASOS, meses]
    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 4.2))
    from matplotlib.colors import LogNorm
    import matplotlib as mpl
    cmap = mpl.colors.LinearSegmentedColormap.from_list("azul", ["#F2F7F9", "#1F6F8B"])
    pos = piv.where(piv > 0)
    ax.imshow(pos.to_numpy(), cmap=cmap, norm=LogNorm(vmin=0.01, vmax=float(piv.max().max())),
              aspect="auto")
    for i, caso in enumerate(CASOS):
        for j, mes in enumerate(meses):
            v = float(piv.loc[caso, mes])
            if v < 0:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor=E.ALERTA,
                                           alpha=0.35, edgecolor=E.ALERTA, lw=1.6))
            oscuro = v > 0 and np.log10(v / 0.01) / np.log10(piv.max().max() / 0.01) > 0.6
            # Tres decimales bajo 0,01 MCOP: «0,00» se leería como empate.
            ax.text(j, i, num(v, 3 if abs(v) < 0.01 else 2), ha="center", va="center",
                    fontsize=7.4,
                    color="white" if oscuro else E.TINTA)
    ax.set_xticks(range(len(meses)))
    ax.set_xticklabels([E.fmt_fecha(pd.Timestamp(m_ + "-01"), "mes")
                        + ("*" if m_ in ("2025-04", "2025-12") else "") for m_ in meses])
    ax.set_yticks(range(len(CASOS)))
    ax.set_yticklabels(CASOS)
    ax.tick_params(length=0)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("Mes (* incompleto: abril desde el 4, diciembre hasta el 15)")
    fig.tight_layout()
    return guardar(fig, "c7_optimalidad_mensual", datos, [
        *rastro,
        "filas «Comunidad» de optimalidad_D72/<caso>_mensual.csv (CANON §12, D72): "
        "beneficio liquidado, mes a mes; ninguna lectura hora a hora",
        "compuerta: la suma de los nueve meses de cada caso es P2P − C4 del horizonte "
        "de " + con_huella(CIFRAS7) + "; 116 de 117 meses positivos; I1, diciembre "
        "de 2025, −41 804 COP (CANON §12 y §14.9)",
        "color: escala logarítmica sobre los meses positivos; el mes negativo, "
        "sombreado aparte",
    ])


def c7_subperiodos():
    """Figura 7.4 — Por tercil del mes y del día (CANON §14.9, C-211).

    Panel 1: P2P − C4 medio por mes de cada tercil (39 meses por tercil de los
    13 casos). Paneles 2 a 4: la mediana entre los 13 casos, por tercil de
    día, de la banda por kWh, la parte del vendedor y la energía por día. La
    columna parte_regla_declarada no se dibuja (C-225).
    """
    pm, pd_ = SUBP / "meses_condicion.csv", SUBP / "resumen_dias.csv"
    rastro = [con_huella(pm), con_huella(pd_)]
    m = pd.read_csv(pm)
    dd = pd.read_csv(pd_)
    exige(len(m) == 117, "meses_condicion no tiene 117 meses")
    niveles = ["bajo", "medio", "alto"]
    conds = [("generacion", "generación"), ("demanda", "demanda"), ("bolsa", "bolsa")]
    mes = {c: (m.groupby(f"t_{c}").P2P_menos_C4.mean() / 1e6).loc[niveles] for c, _ in conds}
    mes1 = {c: (m.groupby(f"t_{c}").P2P_menos_C1.mean() / 1e6).loc[niveles] for c, _ in conds}
    for c, vals in (("generacion", (1.12, 1.27, 1.35)), ("bolsa", (1.41, 1.23, 1.11))):
        for n_, v in zip(niveles, vals):
            igual(round(float(mes[c][n_]), 2), v, 0, f"Tabla 7.7, P2P − C4, {c} {n_}")
    for c, vals in (("generacion", (0.31, 0.40, 0.44)), ("bolsa", (0.45, 0.35, 0.33))):
        for n_, v in zip(niveles, vals):
            igual(round(float(mes1[c][n_]), 2), v, 0, f"Tabla 7.7, P2P − C1, {c} {n_}")
    for n_ in niveles:
        igual(float(mes["demanda"][n_]), cifra7(f"subperiodos__demanda_{n_}__P2P_menos_C4"),
              1e-9, f"demanda {n_}")
    dia = dd.groupby(["condicion", "nivel"])[["banda_por_kwh", "parte_vendedor",
                                             "kwh_por_dia"]].median()
    for n_, v in zip(niveles, (253, 167, 121)):
        igual(round(float(dia.loc[("bolsa", n_), "banda_por_kwh"])), v, 0, f"banda, bolsa {n_}")
    for n_, v in zip(niveles, (0.53, 0.48, 0.41)):
        igual(round(float(dia.loc[("generacion", n_), "parte_vendedor"]), 2), v, 0,
              f"parte del vendedor, generación {n_}")

    estilo_c = {"generacion": (E.GENERACION, "o", "-"), "demanda": (E.TINTA, "s", "--"),
                "bolsa": (E.ALERTA, "D", ":")}
    fig, ejes = plt.subplots(1, 4, figsize=(E.ANCHO_COMPLETO, 2.6))
    paneles = [("P2P − C4 medio\npor mes (MCOP)", None),
               ("Banda por kWh,\npor día (COP/kWh)", "banda_por_kwh"),
               ("Parte del vendedor,\npor día", "parte_vendedor"),
               ("Energía transada,\npor día (kWh)", "kwh_por_dia")]
    x = np.arange(3)
    filas = []
    for ax, (tit, col) in zip(ejes, paneles):
        for c, lab in conds:
            color, mk, ls = estilo_c[c]
            v = (mes[c].to_numpy() if col is None
                 else np.array([float(dia.loc[(c, n_), col]) for n_ in niveles]))
            ax.plot(x, v, color=color, marker=mk, ls=ls, lw=1.2, markersize=4.5, label=lab)
            for n_, vv in zip(niveles, v):
                filas.append(dict(panel=col or "P2P_menos_C4_MCOP_por_mes", condicion=c,
                                  tercil=n_, valor=float(vv)))
        ax.set_title(tit, fontsize=8.6, pad=4)
        ax.set_xticks(x)
        ax.set_xticklabels(["bajo", "medio", "alto"], fontsize=8)
        ax.set_xlim(-0.3, 2.3)
        ax.tick_params(axis="y", labelsize=8)
        eje_num(ax, "y", 2 if col in (None, "parte_vendedor") else 0)
    ejes[0].set_ylim(0, None)
    ejes[2].set_ylim(0, 0.7)
    ejes[1].set_ylim(0, None)
    ejes[3].set_ylim(0, None)
    fig.supxlabel("Tercil del mes (primer panel) o del día, dentro de cada caso", y=0.12,
                  fontsize=8.8)
    h_, l_ = ejes[0].get_legend_handles_labels()
    fig.legend(h_, ["tercil de generación", "tercil de demanda", "tercil de bolsa"],
               loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.01),
               fontsize=8.2)
    fig.tight_layout(rect=(0, 0.14, 1, 1), w_pad=0.9)
    return guardar(fig, "c7_subperiodos", pd.DataFrame(filas), [
        *rastro,
        "panel 1: media de P2P − C4 sobre los 39 meses de cada tercil de los 13 casos "
        "(meses_condicion.csv); paneles 2 a 4: mediana entre los 13 casos de "
        "resumen_dias.csv por condición y tercil (CANON §14.9)",
        "compuerta: Tabla 7.7 (P2P − C1 y P2P − C4 por generación y por bolsa, con las "
        "celdas corregidas de H-102), demanda contra " + con_huella(CIFRAS7)
        + "; banda 253, 167 y 121 COP/kWh por bolsa y parte del vendedor 0,53, 0,48 y "
        "0,41 por generación (CANON §14.9, «Días»)",
        "no se dibuja parte_regla_declarada (C-225)",
    ])


def _fragiles_institucion() -> dict:
    """Pares institución-caso con signo frágil que declara el texto (7.5.1)."""
    out = {"C4": {}, "C1": {}}
    for item in str(cifra7("fragiles__P2P_menos_C4__lista_mayor_25")).split(";"):
        caso, inst, p = item.split()
        out["C4"][(caso, inst)] = float(p)
    exige(int(cifra7("fragiles__P2P_menos_C4__p_mayor_50")) == 4
          and int(cifra7("fragiles__P2P_menos_C4__p_25_a_50")) == 6,
          "frágiles frente a C4 distintos de 4 y 6")
    # Frente a C1: los cuatro que declara el texto, de la caja del GSA.
    for caso, inst, v in (("E4", "HUDN", 38.62), ("E4", "Cesmag", 35.06),
                          ("E5", "Cesmag", 21.19), ("E4", "Mariana", 17.46)):
        p = GSA / caso / f"inversion_{caso}.csv"
        con_huella(p)
        t = pd.read_csv(p).set_index("salida")
        pr = 100 * float(t.loc[f"P2P_menos_C1__{inst}", "p_inversion"])
        igual(round(pr, 2), v, 0.005, f"P(inversión) de P2P − C1, {caso} {inst}")
        out["C1"][(caso, inst)] = pr
    return out


def c7_brechas_institucion():
    """Figura 7.5 — P2P − C1 y P2P − C4 de cada institución en los 13 casos."""
    p = ENTREGA / "compara_matriz_reposo.csv"
    rastro = [con_huella(p)]
    c = pd.read_csv(p, comment="#")
    c = c[c.institucion != "comunidad"]
    tabs = {}
    for k in ("C1", "C4"):
        tabs[k] = (c.pivot(index="caso", columns="institucion", values=f"P2P_menos_{k}_nueva")
                   .reindex(index=CASOS, columns=AGENTS) / 1e3)
    exige(int((tabs["C4"] < 0).sum().sum()) == int(cifra7("institucion__P2P_menos_C4__negativos")),
          "pares bajo C4 distintos de 25")
    exige(int((tabs["C1"] < 0).sum().sum()) == 0, "algún par bajo C1")
    for caso in CASOS:
        for inst in AGENTS:
            if caso == "SINU" and inst == "Udenar":
                exige(np.isnan(tabs["C4"].loc[caso, inst]), "SINU con Udenar")
                continue
            igual(tabs["C4"].loc[caso, inst] * 1e3,
                  cifra7(f"institucion__{caso}__{inst}__P2P_menos_C4"), 1.0,
                  f"{caso} {inst} P2P − C4")
    igual(tabs["C1"].min().min() * 1e3, cifra7("institucion__P2P_menos_C1__min"), 1.0, "mínimo C1")
    igual(tabs["C1"].max().max() * 1e3, cifra7("institucion__P2P_menos_C1__max"), 1.0, "máximo C1")
    frag = _fragiles_institucion()
    rastro.append(con_huella(CIFRAS7))
    rastro += [con_huella(GSA / c_ / f"inversion_{c_}.csv") for c_ in ("E4", "E5")]

    import matplotlib as mpl
    from matplotlib.colors import SymLogNorm
    cmap = mpl.colors.LinearSegmentedColormap.from_list(
        "div", [E.ALERTA, "#FFFFFF", "#1F6F8B"])
    lim = float(max(tabs["C4"].abs().max().max(), tabs["C1"].abs().max().max()))
    norm = SymLogNorm(linthresh=100, vmin=-lim, vmax=lim, base=10)
    fig, ejes = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 4.5), sharey=True)
    filas = []
    for ax, k, tit in ((ejes[0], "C1", "P2P − C1"), (ejes[1], "C4", "P2P − C4")):
        v = tabs[k]
        ax.imshow(v.to_numpy(), cmap=cmap, norm=norm, aspect="auto")
        for i, caso in enumerate(CASOS):
            for j, inst in enumerate(AGENTS):
                x_ = v.loc[caso, inst]
                if np.isnan(x_):
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, color=E.APAGADO))
                    continue
                oscuro = abs(norm(x_) - 0.5) > 0.36
                ax.text(j, i, num(x_), ha="center", va="center", fontsize=6.6,
                        color="white" if oscuro else E.TINTA)
                pf = frag[k].get((caso, inst))
                if pf is not None:
                    ax.add_patch(plt.Rectangle(
                        (j - 0.46, i - 0.44), 0.92, 0.88, fill=False, edgecolor=E.TINTA,
                        lw=1.6 if pf > 50 else 0.9, ls="-" if pf > 50 else (0, (2, 1.5))))
                filas.append(dict(brecha=f"P2P_menos_{k}", caso=caso, institucion=inst,
                                  miles_COP=float(x_), p_inversion_pct=pf if pf else np.nan))
        ax.set_xticks(range(5))
        ax.set_xticklabels([E.etiqueta_institucion(i_) for i_ in AGENTS], fontsize=8,
                           rotation=0)
        for tick, i_ in zip(ax.get_xticklabels(), AGENTS):
            tick.set_color(E.color_institucion(i_))
        ax.set_title(tit, fontsize=9.5, pad=5)
        ax.tick_params(length=0)
        ax.grid(False)
        for s_ in ax.spines.values():
            s_.set_visible(False)
    ejes[0].set_yticks(range(len(CASOS)))
    ejes[0].set_yticklabels(CASOS)
    fig.legend(handles=[
        Patch(facecolor="white", edgecolor=E.TINTA, lw=1.6,
              label="signo minoritario en la caja del capítulo 8 (inversión > 50 %)"),
        Patch(facecolor="white", edgecolor=E.TINTA, lw=0.9, ls=(0, (2, 1.5)),
              label="signo frágil declarado (inversión del 17 al 50 %)"),
    ], loc="lower center", ncol=1, frameon=False, bbox_to_anchor=(0.5, -0.01), fontsize=8.0)
    fig.tight_layout(rect=(0, 0.09, 1, 1), w_pad=1.0)
    return guardar(fig, "c7_brechas_institucion", pd.DataFrame(filas), [
        *rastro,
        "compara_matriz_reposo.csv, filas por institución, columnas P2P_menos_C1_nueva y "
        "P2P_menos_C4_nueva (CANON §5), en miles de COP",
        "compuerta: los 64 pares de P2P − C4 iguales a cifras_cap07 (< 1 COP), 25 "
        "negativos, ningún par bajo C1, mínimo y máximo frente a C1",
        "frágiles frente a C4: fragiles__P2P_menos_C4__lista_mayor_25 (cuatro de más "
        "del 50 %, seis entre el 25 y el 50 %); frente a C1: los cuatro que declara el "
        "texto (E4 HUDN, E4 CESMAG, E5 CESMAG, E4 Mariana), leídos de inversion_<caso>.csv "
        "del GSA completo (CANON §13.5 y §14.10)",
        "color: escala logarítmica simétrica (lineal entre −100 y 100 miles de COP); "
        "SINU no tiene a Udenar",
    ])


def c7_equidad():
    """Figura 7.6 — Gini del P2P y de C4 y precio de la justicia, por caso."""
    p = SALIDAS / "precio_justicia_2026-09-27" / "pof_p2p_c4_13casos.csv"
    rastro = [con_huella(p)]
    d = pd.read_csv(p).set_index("caso").loc[CASOS]
    tabla = {"E0": ("intercambio", 4.3, 0.121, 0.115), "E1": ("P2P domina", 13.9, 0.121, 0.143),
             "E2": ("P2P domina", 17.0, 0.122, 0.161), "E3": ("P2P domina", 16.9, 0.157, 0.184),
             "E4": ("P2P domina", 1.8, 0.188, 0.194), "E5": ("intercambio", 1.2, 0.196, 0.189),
             "P1": ("P2P domina", 15.7, 0.181, 0.194), "P2": ("P2P domina", 3.4, 0.115, 0.115),
             "K1": ("intercambio", 2.9, 0.121, 0.107), "I1": ("intercambio", 5.6, 0.499, 0.350),
             "N1": ("intercambio", 13.6, 0.240, 0.227), "CV2": ("P2P domina", 5.0, 0.119, 0.119),
             "SINU": ("P2P domina", 1.1, 0.125, 0.127)}
    for caso, (cl, pj, gp, gc) in tabla.items():
        exige(d.loc[caso, "clase"] == cl, f"{caso}: clase")
        igual(round(100 * d.loc[caso, "PoF_P2P_a_C4"], 1), pj, 0, f"{caso}: precio de la justicia")
        igual(round(d.loc[caso, "gini_P2P"], 3), gp, 0, f"{caso}: Gini P2P")
        igual(round(d.loc[caso, "gini_C4"], 3), gc, 0, f"{caso}: Gini C4")
    t, r2 = _resumen_13()
    rastro += r2
    exige(bool(np.allclose(d.W_P2P, t.P2P, atol=1e-3) and np.allclose(d.W_C4, t.C4, atol=1e-3)),
          "W no es la ganancia de la hoja Resumen")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.9), sharey=True,
                                 gridspec_kw=dict(width_ratios=(1.35, 1.0)))
    y = np.arange(len(CASOS))
    cp, mp, _ = MEC7["P2P"]
    c4, m4, _ = MEC7["C4"]
    for i, caso in enumerate(CASOS):
        a1.plot([d.loc[caso, "gini_P2P"], d.loc[caso, "gini_C4"]], [i, i], color="#CCCCCC",
                lw=1.0, zorder=1)
    a1.plot(d.gini_C4, y, ls="none", marker=m4, color=c4, markersize=6, zorder=3, label="C4")
    a1.plot(d.gini_P2P, y, ls="none", marker=mp, color=cp, markersize=6.5, zorder=4,
            label="P2P")
    for caso in ("P2", "CV2"):
        a1.text(float(d.loc[caso, "gini_P2P"]) + 0.022, CASOS.index(caso), "iguales a\n3 decimales",
                va="center", fontsize=6.8, color=E.NEUTRO, linespacing=0.9)
    a1.set_xlabel("Índice de Gini del beneficio\npor institución")
    eje_num(a1, "x", 1)
    a1.legend(loc="lower right", frameon=False, fontsize=8.2)
    a1.grid(axis="y", visible=False)
    col = {"P2P domina": cp, "intercambio": E.ALERTA}
    for i, caso in enumerate(CASOS):
        cl = d.loc[caso, "clase"]
        a2.barh(i, 100 * d.loc[caso, "PoF_P2P_a_C4"], height=0.6,
                color=col[cl] if cl == "intercambio" else "white",
                edgecolor=col[cl], lw=1.2, hatch=None, zorder=2)
    a2.set_xlabel("$(W_{\\mathrm{P2P}}-W_{\\mathrm{C4}})/W_{\\mathrm{P2P}}$ (%)")
    eje_num(a2, "x")
    a2.grid(axis="y", visible=False)
    a2.legend(handles=[
        Patch(facecolor=E.ALERTA, edgecolor=E.ALERTA,
              label="intercambio: precio de la justicia"),
        Patch(facecolor="white", edgecolor=cp, lw=1.2,
              label="P2P domina: ventaja en eficiencia"),
    ], loc="upper center", bbox_to_anchor=(0.35, -0.2), frameon=False, fontsize=8.0)
    a1.set_yticks(y)
    a1.set_yticklabels(CASOS)
    a1.set_ylim(len(CASOS) - 0.5, -0.5)
    fig.tight_layout()
    datos = d.reset_index()[["caso", "W_P2P", "W_C4", "gini_P2P", "gini_C4",
                             "PoF_P2P_a_C4", "clase"]]
    return guardar(fig, "c7_equidad", datos, [
        *rastro,
        "pof_p2p_c4_13casos.csv (CANON §14.6, C-208): Gini de la hoja PoF_Fairness, W de "
        "la hoja Resumen (comprobado); la columna perdida_asignacion_D55 no se dibuja "
        "(es la captura, no el precio de la justicia)",
        "compuerta: clase, precio de la justicia y los dos Gini de la Tabla 7.10",
    ])


def c7_coincidencia():
    """Figura 7.7 — Factor de coincidencia de cada mecanismo en los 13 casos."""
    rastro, filas = [], {}
    for caso in CASOS:
        h, r_ = _hoja(caso, "Coincidencia")
        rastro.append(r_)
        v = h.set_index("escenario")["valor"]
        exige(np.isnan(v["C3"]), f"{caso}: C3 con factor de coincidencia")
        exige(abs(v["P2P"] - v["C2"]) < 1e-12 and abs(v["C4"] - v["C4_mensual"]) < 1e-12,
              f"{caso}: identidades del factor")
        exige(v["C1"] == 0.0 and v["C5"] == 1.0, f"{caso}: C1 = 0 y C5 = 1")
        for m in ("C1", "C4", "P2P_colectivo", "P2P", "C5"):
            igual(v[m], cifra7(f"coincidencia__{caso}__{m}"), 1e-9, f"{caso} {m}")
        filas[caso] = v[["C1", "C4", "P2P_colectivo", "P2P", "C5"]].astype(float)
    t = pd.DataFrame(filas).T.loc[CASOS]
    exige(int((t.P2P >= t[["C1", "C4", "P2P_colectivo"]].max(axis=1)).sum()) ==
          int(cifra7("coincidencia__casos_P2P_max_sin_C5")), "P2P máximo sin C5")

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 3.9))
    y = np.arange(len(CASOS))
    for i, caso in enumerate(CASOS):
        ax.plot([0, 1], [i, i], color="#EEEEEE", lw=0.8, zorder=1)
    for m in ("C1", "C4", "P2P_colectivo", "P2P", "C5"):
        c, mk, lab = MEC7[m]
        hueco = m == "C5"
        ax.plot(t[m], y, ls="none", marker=mk, markersize=6.5, mfc="white" if hueco else c,
                mec=c, mew=1.4 if hueco else 0.4, zorder=3, label=lab)
    ax.set_yticks(y)
    ax.set_yticklabels(CASOS)
    ax.set_ylim(len(CASOS) - 0.5, -0.5)
    ax.set_xlim(-0.04, 1.04)
    ax.xaxis.set_major_locator(MultipleLocator(0.2))
    eje_num(ax, "x", 1)
    ax.set_xlabel("Factor de coincidencia")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False,
              fontsize=8.2, columnspacing=1.2)
    fig.tight_layout()
    datos = t.reset_index(names="caso")
    return guardar(fig, "c7_coincidencia", datos, [
        *rastro,
        "hoja Coincidencia de cada caso (D20, C-183; CANON §10.0, trampa 1); C2 = P2P y "
        "C4_mensual = C4 comprobados y no dibujados; C3 sin factor",
        "compuerta: los 65 valores iguales a " + con_huella(CIFRAS7),
    ])


# ═════════════════════════════════════════════════════════════════════════════
# Capítulo 8
# ═════════════════════════════════════════════════════════════════════════════
# Reglas: CV2 fuera del Sobol; los nueve casos de n = 512 con su semiancho
# visible (D77); las cinco celdas de empate de la Tabla 8.5 marcadas; nada de
# mu dentro de la caja; la deserción sin sugerir un umbral general.
CIFRAS8 = SALIDAS / "cifras_cap08_2026-09-28" / "cifras.csv"
INFDES = SALIDAS / "infactibilidad_desercion_2026-09-27"
RETIRO = SALIDAS / "retiro_miembro_2026-09-27"
CASOS8 = ["E0", "E2", "E4", "E1", "E3", "E5", "P1", "P2", "K1", "I1", "N1", "SINU"]
N_BASE = {c: (2048 if c in ("E0", "E2", "E4") else 512) for c in CASOS8}
BRECHAS8 = [("P2P_menos_C1", "P2P − C1"), ("P2P_menos_C4", "P2P − C4"),
            ("P2Pcol_menos_C1", "P2P colectivo − C1"), ("C4_menos_C1", "C4 − C1"),
            ("P2P_menos_C5", "P2P − C5")]
ENTRADAS8 = {  # clave del GSA: (rótulo mathtext, color, marcador)
    "f_cv":     (r"$f_{\mathrm{Cv}}$", "#2C6E6B", "o"),
    "f_bolsa":  (r"$f_{\mathrm{B}}$", "#B4534B", "s"),
    "f_tarifa": (r"$f_{\mathrm{CU}}$", "#3A3A3A", "D"),
    "f_peaje":  (r"$f_{\Theta}$", "#6B8E23", "^"),
    "e_G":      (r"$\varepsilon_G$", "#5DA5DA", "v"),
    "e_D":      (r"$\varepsilon_D$", "#A0A0A0", "P"),
}
_CIFRAS8: pd.DataFrame | None = None


def cifra8(clave: str):
    """Una cifra de cifras_cap08_2026-09-28 (CANON §14.19, grupo e1/Q)."""
    global _CIFRAS8
    if _CIFRAS8 is None:
        con_huella(CIFRAS8)
        _CIFRAS8 = pd.read_csv(CIFRAS8, dtype={"valor": str}).set_index("clave")
    exige(clave in _CIFRAS8.index, f"cifras_cap08 no tiene la clave {clave}")
    v = _CIFRAS8.loc[clave, "valor"]
    try:
        return float(v)
    except ValueError:
        return v


def _rotulo_caso8(c: str) -> str:
    return f"{c} ({num(N_BASE[c])})"


def c8_probabilidad_inversion():
    """Figura 8.1 — Probabilidad de inversión de las brechas de la comunidad.

    Filas A y B de la muestra (inversion_<caso>.csv del GSA completo), con su
    intervalo al 95 %. Comprueba cada celda de la Tabla 8.4.
    """
    t84 = {("E4", "P2Pcol_menos_C1"): 56.25, ("E4", "C4_menos_C1"): 56.40,
           ("E4", "P2P_menos_C5"): 19.68, ("E5", "P2Pcol_menos_C1"): 74.71,
           ("E5", "C4_menos_C1"): 75.29, ("E5", "P2P_menos_C5"): 17.48,
           ("P2", "P2Pcol_menos_C1"): 13.09, ("P2", "C4_menos_C1"): 13.87,
           ("I1", "P2Pcol_menos_C1"): 8.20, ("I1", "C4_menos_C1"): 76.37,
           ("I1", "P2P_menos_C5"): 2.73, ("N1", "P2P_menos_C5"): 1.56}
    rastro, filas = [], []
    for caso in CASOS8:
        p = GSA / caso / f"inversion_{caso}.csv"
        rastro.append(con_huella(p))
        t = pd.read_csv(p).set_index("salida")
        exige(int(t.loc["P2P_menos_C1", "n_filas"]) == 2 * N_BASE[caso], f"{caso}: n_filas")
        for b, _ in BRECHAS8:
            pi, lo, hi = (100 * float(t.loc[b, k]) for k in ("p_inversion", "p_inf", "p_sup"))
            igual(round(pi, 2), t84.get((caso, b), 0.0), 0.005, f"Tabla 8.4, {caso} {b}")
            filas.append(dict(caso=caso, n=N_BASE[caso], brecha=b, p_inversion_pct=pi,
                              ic95_inf_pct=lo, ic95_sup_pct=hi))
    d = pd.DataFrame(filas)
    e4 = d[(d.caso == "E4") & (d.brecha == "P2Pcol_menos_C1")].iloc[0]
    igual(round(e4.ic95_inf_pct, 2), 54.61, 0.005, "intervalo de E4")
    igual(round(e4.ic95_sup_pct, 2), 57.71, 0.005, "intervalo de E4")

    fig, ejes = plt.subplots(1, 5, figsize=(E.ANCHO_COMPLETO, 3.5), sharey=True)
    y = np.arange(len(CASOS8))
    for ax, (b, tit) in zip(ejes, BRECHAS8):
        s = d[d.brecha == b].set_index("caso").loc[CASOS8]
        ax.axvline(50, color=E.ALERTA, lw=0.8, ls=(0, (3, 2)), zorder=1)
        cero = s.p_inversion_pct == 0
        ax.plot(s.p_inversion_pct[cero], y[cero.to_numpy()], ls="none", marker="o",
                markersize=3.2, mfc="white", mec="#9A9A9A", mew=0.8, zorder=2)
        nz = ~cero.to_numpy()
        ax.errorbar(s.p_inversion_pct[nz], y[nz],
                    xerr=[(s.p_inversion_pct - s.ic95_inf_pct)[nz],
                          (s.ic95_sup_pct - s.p_inversion_pct)[nz]],
                    fmt="o", color=E.TINTA, markersize=4.5, elinewidth=1.4, capsize=2.2,
                    zorder=3)
        ax.set_title(tit, fontsize=8.6, pad=4)
        ax.set_xlim(-4, 104)
        ax.set_xticks([0, 50, 100])
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="y", visible=False)
    ejes[0].set_yticks(y)
    ejes[0].set_yticklabels([_rotulo_caso8(c) for c in CASOS8], fontsize=8)
    ejes[0].set_ylim(len(CASOS8) - 0.5, -0.5)
    for ax in ejes:
        ax.axhspan(2.5, len(CASOS8) - 0.5, color=E.FONDO_BANDA, zorder=0)
    fig.supxlabel("Probabilidad de inversión en la caja de entradas (%)", fontsize=9, y=0.17)
    fig.legend(handles=[
        Line2D([], [], ls="none", marker="o", markersize=3.2, mfc="white", mec="#9A9A9A",
               label="cero"),
        Line2D([], [], color=E.TINTA, marker="o", markersize=4.5, lw=1.4,
               label="distinta de cero, con su intervalo al 95 %"),
        Line2D([], [], color=E.ALERTA, lw=0.8, ls=(0, (3, 2)),
               label="50 %: el signo del punto base pasa a minoritario"),
    ], loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.01), fontsize=7.8,
        columnspacing=1.0, handletextpad=0.4)
    fig.tight_layout(rect=(0, 0.2, 1, 1), w_pad=0.5)
    return guardar(fig, "c8_probabilidad_inversion", d, [
        *rastro,
        "filas A y B de la muestra de Saltelli (CANON §13.2 y §13.3); CV2 fuera del "
        "análisis (§13.8.4); fondo gris: los nueve casos de n = 512",
        "compuerta: las 60 celdas de la Tabla 8.4 y el intervalo de E4 (54,61 a 57,71 %)",
    ])


def c8_sobol():
    """Figura 8.2 — Índices totales de las seis entradas sobre las cinco brechas.

    Por brecha y caso, las dos entradas de mayor índice total, en color y con
    su semiancho al 95 %; las otras cuatro, en gris y sin barra. Los casos de
    n = 512 van sobre fondo gris; los cinco empates de la Tabla 8.5, marcados.
    """
    rastro, filas = [], []
    for caso in CASOS8:
        p = GSA / caso / f"indices_{caso}.csv"
        rastro.append(con_huella(p))
        t = pd.read_csv(p)
        t = t[(t.n == N_BASE[caso]) & (t.salida.isin([b for b, _ in BRECHAS8]))]
        exige(len(t) == 5 * 6, f"{caso}: faltan índices con n = {N_BASE[caso]}")
        exige(not t[["ST", "ST_conf"]].isna().any().any(), f"{caso}: índices vacíos")
        for _, f in t.iterrows():
            filas.append(dict(caso=caso, n=N_BASE[caso], brecha=f.salida, entrada=f.entrada,
                              ST=float(f.ST), ST_semiancho=float(f.ST_conf)))
    d = pd.DataFrame(filas)
    # Compuerta: la dominante y la segunda de cada celda, contra cifras_cap08
    # (que el guion del capítulo comprobó contra CANON §13.4).
    empates = set()
    for item in str(cifra8("dominante__no_separadas__lista")).split(";"):
        caso, b, *_ = item.split()
        empates.add((caso, b))
    exige(len(empates) == int(cifra8("dominante__no_separadas__n")) == 5, "empates distintos de 5")
    for caso in CASOS8:
        for b, _ in BRECHAS8:
            s = d[(d.caso == caso) & (d.brecha == b)].sort_values("ST", ascending=False)
            for k, clave in ((0, f"dominante__{caso}__{b}"), (1, f"dominante__{caso}__{b}__segunda")):
                ent, st, sa = str(cifra8(clave)).replace("(", "").replace(")", "").replace(
                    "±", "").split()
                exige(s.entrada.iloc[k] == ent, f"{clave}: entrada {s.entrada.iloc[k]} y no {ent}")
                igual(round(s.ST.iloc[k], 3), float(st), 0, f"{clave}: ST")
                igual(round(s.ST_semiancho.iloc[k], 3), float(sa), 0, f"{clave}: semiancho")
            no_sep = (s.ST.iloc[0] - s.ST.iloc[1]) < (s.ST_semiancho.iloc[0] + s.ST_semiancho.iloc[1])
            exige(no_sep == ((caso, b) in empates), f"{caso} {b}: empate mal clasificado")
    d["empate"] = [(c_, b_) in empates for c_, b_ in zip(d.caso, d.brecha)]

    fig, ejes_ = plt.subplots(2, 3, figsize=(E.ANCHO_COMPLETO, 6.6), sharex=True)
    ejes = ejes_.ravel()
    y = np.arange(len(CASOS8))
    for ax, (b, tit) in zip(ejes, BRECHAS8):
        ax.axhspan(2.5, len(CASOS8) - 0.5, color=E.FONDO_BANDA, zorder=0)
        for i, caso in enumerate(CASOS8):
            s = d[(d.caso == caso) & (d.brecha == b)].sort_values("ST", ascending=False)
            resto = s.iloc[2:]
            ax.plot(resto.ST, [i] * len(resto), ls="none", marker="|", markersize=5,
                    color="#B5B5B5", zorder=2)
            for k, off in ((0, -0.17), (1, 0.17)):
                f = s.iloc[k]
                lab, col, mk = ENTRADAS8[f.entrada]
                ax.errorbar([f.ST], [i + off], xerr=[f.ST_semiancho], fmt=mk, color=col,
                            markersize=4.2, elinewidth=1.1, capsize=1.6, zorder=3)
            if (caso, b) in empates:
                ax.text(1.03, i, "(e)", ha="left", va="center", fontsize=7.6,
                        color=E.ALERTA, fontweight="bold")
        ax.set_title(tit, fontsize=9, pad=4)
        ax.set_xlim(-0.03, 1.12)
        ax.set_xticks([0, 0.5, 1])
        eje_num(ax, "x", 1)
        ax.set_yticks(y)
        ax.set_yticklabels([_rotulo_caso8(c) for c in CASOS8], fontsize=7.4)
        ax.set_ylim(len(CASOS8) - 0.5, -0.5)
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="x", labelsize=8)
    for ax in (ejes[3], ejes[4]):
        ax.set_xlabel("Índice total $S_T$")
    ejes[5].axis("off")
    manejadores = [Line2D([], [], ls="none", marker=mk, color=col, markersize=5, label=lab)
                   for lab, col, mk in ENTRADAS8.values()]
    manejadores += [
        Line2D([], [], ls="none", marker="|", color="#B5B5B5", markersize=6,
               label="las otras cuatro entradas"),
        Patch(facecolor=E.FONDO_BANDA, edgecolor="#DDDDDD", label="$n = 512$"),
        Line2D([], [], ls="none", marker="$(e)$", color=E.ALERTA, markersize=11,
               label="empate: no se separa\nde la segunda"),
    ]
    ejes[5].legend(handles=manejadores, loc="center", frameon=False, fontsize=8.2,
                   title="Las dos entradas de mayor $S_T$,\ncon su semiancho al 95 %",
                   title_fontsize=8.2, ncol=1, handletextpad=0.6, labelspacing=0.55)
    fig.tight_layout(h_pad=1.2, w_pad=0.8)
    return guardar(fig, "c8_sobol", d, [
        *rastro,
        "indices_<caso>.csv con n = n_base (2 048 en E0, E2 y E4; 512 en los otros nueve), "
        "salidas de brecha; CV2 fuera (CANON §13.8.4); los nueve de n = 512 no cierran la "
        "convergencia y van con su semiancho (D77, §13.8.1)",
        "compuerta: la dominante y la segunda de las 60 celdas, con ST y semiancho a tres "
        "decimales, iguales a " + con_huella(CIFRAS8) + " (claves dominante__*); los "
        "cinco empates (dominante__no_separadas__lista) son exactamente las celdas cuya "
        "diferencia es menor que la suma de semianchos",
    ])


def c8_infactibilidad_desercion():
    """Figura 8.3 — Cercanía a la infactibilidad y deserción hacia C1, por tramo
    del nivel de la bolsa.

    Paneles: energía media relativa, horas sin ganancia medias, deserción de
    los seis pares de más del 5 % y deserción de los tres pares pequeños que
    el texto nombra (Udenar en N1, CESMAG en E3 y en E2), en su propia
    escala. No se dibuja ninguna línea en «dos veces la bolsa»: ese umbral
    vale para E4, no en general (H-103, precisado).
    """
    pc, pdd = INFDES / "cercania_por_fbolsa.csv", INFDES / "desercion_c1_por_fbolsa.csv"
    rastro = [con_huella(pc), con_huella(pdd), con_huella(CIFRAS8)]
    c = pd.read_csv(pc)
    de = pd.read_csv(pdd)
    tramos = ["(0.749, 1.0]", "(1.0, 1.5]", "(1.5, 2.0]", "(2.0, 3.0]", "(3.0, 4.0]"]
    claves_t = ["075_1", "1_15", "15_2", "2_3", "3_4"]
    rot_t = ["0,75–1", "1–1,5", "1,5–2", "2–3", "3–4"]
    for caso, e34, sg1, sg34 in (("E5", 72.9, 0.4, 210.4), ("P1", 82.6, 2.5, 159.4),
                                  ("E4", 83.2, 0.6, 157.0)):
        s = c[c.caso == caso].set_index("tramo")
        igual(round(100 * s.loc[tramos[-1], "energia_rel_media"], 1), e34, 0, f"Tabla 8.10 {caso}")
        igual(round(s.loc[tramos[0], "sin_ganancia_media"], 1), sg1, 0, f"Tabla 8.10 {caso}")
        igual(round(s.loc[tramos[-1], "sin_ganancia_media"], 1), sg34, 0, f"Tabla 8.10 {caso}")
    exige(int(c.evaluaciones_fallidas_caso.max()) == 0 and float(c.retiros_max_caso.max()) == 0,
          "evaluaciones fallidas o retiros en la caja")
    de_p = de.pivot_table(index=["caso", "institucion"], columns="tramo",
                          values="p_desercion")[tramos] * 100
    for (caso, inst), vals in {("E4", "HUDN"): (None, None, None, 27.2, 98.2),
                               ("E4", "Cesmag"): (None, None, None, 33.0, 81.3)}.items():
        for k in (3, 4):
            igual(round(de_p.loc[(caso, inst)].iloc[k], 1), vals[k], 0, f"deserción {caso} {inst}")
    for caso, inst in (("E5", "Cesmag"), ("E5", "HUDN"), ("P1", "HUDN"), ("N1", "Udenar"),
                       ("E3", "Cesmag"), ("E2", "Cesmag")):
        for k, ct in enumerate(claves_t):
            igual(de_p.loc[(caso, inst)].iloc[k], cifra8(f"desercion__{caso}__{inst}__{ct}"),
                  1e-9, f"deserción {caso} {inst} {ct}")

    grandes = [("E4", "HUDN"), ("E4", "Cesmag"), ("E5", "Cesmag"), ("E4", "Mariana"),
               ("E5", "HUDN"), ("P1", "HUDN")]
    pequenas = [("N1", "Udenar"), ("E3", "Cesmag"), ("E2", "Cesmag")]
    x = np.arange(5)
    fig, ejes_ = plt.subplots(2, 2, figsize=(E.ANCHO_COMPLETO, 5.4))
    a1, a2, a3, a4 = ejes_.ravel()
    destacados = {"E5": "#B4534B", "E4": "#2C6E6B", "P1": "#6B8E23", "E0": E.TINTA,
                  "SINU": "#7A7A7A"}
    filas = []
    for caso in CASOS8:
        s = c[c.caso == caso].set_index("tramo").loc[tramos]
        col = destacados.get(caso)
        kw = dict(color=col, lw=1.4, marker="o", markersize=3.2, zorder=3) if col else \
            dict(color="#D2D2D2", lw=0.9, zorder=1)
        a1.plot(x, 100 * s.energia_rel_media, **kw)
        a2.plot(x, s.sin_ganancia_media, **kw)
        for t_, e_, h_ in zip(rot_t, 100 * s.energia_rel_media, s.sin_ganancia_media):
            filas.append(dict(panel="cercania", caso=caso, institucion="", tramo_fB=t_,
                              energia_rel_media_pct=float(e_), sin_ganancia_media=float(h_),
                              desercion_pct=np.nan))
        # E4 y P1 terminan casi en el mismo punto: sus rótulos se separan.
        if col and caso in ("E5", "E4", "P1"):
            a1.text(4.12, 100 * s.energia_rel_media.iloc[-1] + {"E4": 1.8, "P1": -1.8}.get(caso, 0),
                    caso, va="center", fontsize=7.8, color=col)
        if col:
            a2.text(4.12, s.sin_ganancia_media.iloc[-1] + {"E4": -9, "P1": 9}.get(caso, 0),
                    caso, va="center", fontsize=7.8, color=col)
    a1.set_ylabel("Energía media\n(% del punto base)")
    a1.set_ylim(60, 105)
    a2.set_ylabel("Horas sin ganancia\npor evaluación")
    a2.set_ylim(0, None)
    for ax, pares, tope in ((a3, grandes, 105), (a4, pequenas, 15)):
        for caso, inst in pares:
            v = de_p.loc[(caso, inst)].to_numpy()
            ls = {"E4": "-", "E5": "--", "P1": ":", "N1": "-", "E3": "--", "E2": ":"}[caso]
            ax.plot(x, v, color=E.color_institucion(inst), lw=1.5, ls=ls, marker="o",
                    markersize=3.2)
            # Rótulo al final de la curva, salvo Udenar en N1 (lo rotula la
            # llamada del origen) y el HUDN en E5 y P1, que acaban juntos.
            rot = {("E5", "HUDN"): "HUDN, E5 y P1", ("P1", "HUDN"): None,
                   ("N1", "Udenar"): None}.get((caso, inst), f"{E.etiqueta_institucion(inst)}, {caso}")
            if rot:
                ax.text(4.12, v[-1], rot, va="center", fontsize=7.4,
                        color=E.color_institucion(inst))
            for t_, vv in zip(rot_t, v):
                filas.append(dict(panel="desercion", caso=caso, institucion=inst, tramo_fB=t_,
                                  energia_rel_media_pct=np.nan, sin_ganancia_media=np.nan,
                                  desercion_pct=float(vv)))
        ax.set_ylim(-tope * 0.03, tope)
        ax.set_ylabel("Prefiere C1\n(% de los puntos)")
    # N1: el máximo, con la bolsa barata, se rotula en el origen de la curva.
    a4.annotate("Udenar, N1: más con la bolsa barata", xy=(0, cifra8("desercion__N1__Udenar__075_1")),
                xytext=(0.35, 10.5), fontsize=7.4, color=E.color_institucion("Udenar"),
                arrowprops=dict(arrowstyle="-", color=E.color_institucion("Udenar"), lw=0.7))
    a3.set_title("Deserción que crece con la bolsa\n(los seis pares de más del 5 %)", fontsize=8.6)
    a4.set_title("Deserciones pequeñas que nombra el texto", fontsize=8.6)
    a1.set_title("Energía transada", fontsize=8.6)
    a2.set_title("Horas sin ganancia", fontsize=8.6)
    for ax in (a1, a2, a3, a4):
        ax.set_xticks(x)
        ax.set_xticklabels(rot_t, fontsize=7.8)
        ax.set_xlim(-0.25, 5.1)
        ax.tick_params(axis="y", labelsize=8)
    for ax in (a3, a4):
        ax.set_xlabel("Nivel de la bolsa, $f_{\\mathrm{B}}$ (tramo)")
    fig.tight_layout(h_pad=1.4, w_pad=1.2)
    return guardar(fig, "c8_infactibilidad_desercion", pd.DataFrame(filas), [
        *rastro,
        "cercania_por_fbolsa.csv (12 casos) y desercion_c1_por_fbolsa.csv, fracción de "
        "todas las filas de la muestra por tramo de f_bolsa (CANON §14.10, H-103 precisado)",
        "compuerta: Tabla 8.10, E4 HUDN y CESMAG entre 2 y 3 y entre 3 y 4 (CANON §14.10), "
        "y E5, P1, N1, E3 y E2 por tramo contra cifras_cap08 (claves desercion__*)",
        "pares dibujados: los seis de más del 5 % en total y los tres que el texto nombra "
        "por no crecer con la bolsa; el HUDN en E3 no se dibuja porque el texto no lo cita",
        "en gris claro, los demás casos de la energía y de las horas sin ganancia",
    ])


def c8_retiro():
    """Figura 8.4 — El retiro de un miembro: cuánto se mueve el beneficio de
    cada institución que se queda, con el mercado frente a con C4."""
    pq, pc = RETIRO / "quienes_quedan.csv", RETIRO / "comunidad.csv"
    rastro = [con_huella(pq), con_huella(pc)]
    q = pd.read_csv(pq)
    com = pd.read_csv(pc)
    exige(len(q) == 216, "no son 216 pares")
    menos = (q.perdida_P2P.abs() < q.perdida_C4.abs())
    exige(int(menos.sum()) == 182 and bool(((q.mas_estable == "P2P") == menos).all()),
          "no son 182 de 216")
    igual(round(100 * q.perdida_rel_P2P.abs().median(), 2), 0.25, 0, "mediana relativa P2P")
    igual(round(100 * q.perdida_rel_C4.abs().median(), 2), 1.73, 0, "mediana relativa C4")
    t812 = {"Udenar": (82, 879, 43), "Mariana": (18, 88, 27), "UCC": (135, 588, 30),
            "HUDN": (32, 368, 41), "Cesmag": (81, 743, 41)}
    for inst, (mp, mc, n_) in t812.items():
        s = q[q.retirada == inst]
        igual(round(s.perdida_P2P.abs().median() / 1e3), mp, 0, f"Tabla 8.12 P2P {inst}")
        igual(round(s.perdida_C4.abs().median() / 1e3), mc, 0, f"Tabla 8.12 C4 {inst}")
        igual(int(((s.perdida_P2P.abs() < s.perdida_C4.abs())).sum()), n_, 0, f"Tabla 8.12 {inst}")
    c4 = com[com.retirada != "ninguna"]
    exige(len(c4) == 54, "no son 54 comunidades de cuatro")
    igual(int((c4.perdida_quedan_P2P.abs() < c4.perdida_quedan_C4.abs()).sum()), 50, 0,
          "50 de 54 comunidades")
    exige(float(q.perdida_C1.abs().max()) == 0.0, "la pérdida con C1 no es cero")

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 4.2))
    xm, ym = q.perdida_C4.abs() / 1e3, q.perdida_P2P.abs() / 1e3
    lo, hi = 0.1, 2e4
    ax.plot([lo, hi], [lo, hi], color=E.TINTA, lw=0.9, zorder=1)
    ax.fill_between([lo, hi], [lo, lo], [lo, hi], color=E.FONDO_BANDA, zorder=0)
    formas = {"Udenar": "o", "Mariana": "s", "UCC": "D", "HUDN": "^", "Cesmag": "v"}
    for inst in AGENTS:
        s = q.retirada == inst
        ax.scatter(xm[s], ym[s], s=16, marker=formas[inst], color=E.color_institucion(inst),
                   edgecolor="white", linewidth=0.3, zorder=3,
                   label=f"sale {E.etiqueta_institucion(inst)}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    for eje in (ax.xaxis, ax.yaxis):
        eje.set_major_formatter(FuncFormatter(lambda v, _: num(v, 1 if v < 1 else 0)))
    ax.set_xlabel("Cambio del beneficio de quien se queda con C4\n(miles de COP, valor absoluto)")
    ax.set_ylabel("Con el mercado\n(miles de COP, valor absoluto)")
    ax.text(2e3, 0.4, f"se mueve menos con el mercado:\n{int(menos.sum())} de {len(q)} pares",
            ha="center", va="center", fontsize=8.2, color=E.TINTA)
    ax.text(0.3, 3e3, "se mueve menos con C4", ha="left", va="center", fontsize=8.2,
            color=E.NEUTRO)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, fontsize=8.2,
              handletextpad=0.3)
    fig.tight_layout()
    datos = q[["caso", "retirada", "institucion", "perdida_P2P", "perdida_C4",
               "perdida_rel_P2P", "perdida_rel_C4"]].copy()
    return guardar(fig, "c8_retiro", datos, [
        *rastro,
        "quienes_quedan.csv (CANON §14.13, H-106, C-215): pérdida = beneficio con la "
        "comunidad completa menos sin la que sale, por par; se dibuja su valor absoluto",
        "compuerta: 182 de 216 pares se mueven menos con el mercado; medianas relativas "
        "0,25 y 1,73 %; las medianas y recuentos por institución que sale de la Tabla 8.12; "
        "50 de 54 comunidades (comunidad.csv); pérdida con C1 cero exacto",
    ])


# ═════════════════════════════════════════════════════════════════════════════
# Capítulo 2 (ilustrativa, sintética)
# ═════════════════════════════════════════════════════════════════════════════
def _logit_topado(precios, d, E_, mu):
    """q_i = min(d_i, exp((π_i − C)/μ)), con C tal que Σ q_i = E (5.3)."""
    precios, d = np.asarray(precios, float), np.asarray(d, float)
    lo, hi = precios.min() - 60 * mu - 1e3, precios.max() + 60 * mu
    for _ in range(300):
        C = (lo + hi) / 2
        q = np.minimum(d, np.exp(np.clip((precios - C) / mu, -700, 700)))
        if q.sum() > E_:
            lo = C
        else:
            hi = C
    exige(abs(q.sum() - E_) < 1e-9 * max(1.0, E_), "la bisección no cerró")
    return q


def c2_respuesta_logit():
    """Figura 2.1 — Respuesta logit topada de un vendedor frente a μ.

    Sintética: no usa datos del canon. Un vendedor con 8 kWh reparte entre
    tres compradores con déficit de 8 kWh cada uno, con dos juegos de
    precios. Se dibuja la parte de la energía de cada comprador frente a μ,
    con la prioridad estricta (μ → 0) como referencia.
    """
    E_, d = 8.0, [8.0, 8.0, 8.0]
    juegos = {"A": [800.0, 760.0, 720.0], "B": [760.0, 757.0, 720.0]}
    mus = np.logspace(-1, 2, 241)
    filas = []
    fig, ejes = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 2.9), sharey=True)
    tonos = ["#1F6F8B", "#C1642A", "#8C8C8C"]
    formas = ["-", "--", ":"]
    for ax, (k, pr) in zip(ejes, juegos.items()):
        Q = np.array([_logit_topado(pr, d, E_, m) for m in mus]) / E_
        estricta = np.array([1.0, 0.0, 0.0])
        for i in range(3):
            ax.plot(mus, Q[:, i], color=tonos[i], ls=formas[i], lw=1.6,
                    label=["comprador de precio más alto", "segundo precio",
                           "tercer precio"][i])
        ax.axvline(1.0, color=E.TINTA, lw=0.8, ls=(0, (1, 2)))
        q1 = _logit_topado(pr, d, E_, 1.0) / E_
        dlt = float(np.max(np.abs(q1 - estricta)))
        ax.text(1.12, 0.52, f"$\\mu = 1$: se aparta\n{num(100 * dlt, 1 if dlt > 1e-3 else 0)} % "
                "de la\nprioridad estricta" if dlt > 1e-6 else
                "$\\mu = 1$: igual a la\nprioridad estricta", fontsize=7.8, va="center",
                color=E.TINTA)
        ax.set_xscale("log")
        ax.set_xlim(0.1, 100)
        ax.set_ylim(-0.03, 1.03)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: num(v, 1 if v < 1 else 0)))
        ax.set_xlabel("Temperatura $\\mu$ (COP/kWh)")
        ax.set_title("precios de 800, 760 y 720 (COP/kWh)" if k == "A"
                     else "precios de 760, 757 y 720 (COP/kWh)", fontsize=8.8, pad=4)
        for m, qq in zip(mus, Q):
            filas.append(dict(juego=k, mu=float(m), parte_1=float(qq[0]), parte_2=float(qq[1]),
                              parte_3=float(qq[2])))
    ejes[0].set_ylabel("Parte de la energía\ndel vendedor")
    eje_num(ejes[0], "y", 1)
    h_, l_ = ejes[0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="lower center", ncol=3, frameon=False, fontsize=8.0,
               bbox_to_anchor=(0.5, -0.01), handlelength=2.2)
    fig.tight_layout(rect=(0, 0.09, 1, 1), w_pad=1.0)
    return guardar(fig, "c2_respuesta_logit", pd.DataFrame(filas), [
        "FIGURA SINTÉTICA E ILUSTRATIVA: no usa datos del canon ni de la comunidad.",
        "Respuesta logit topada de (5.3) del lado de los compradores: "
        "q_i = min(d_i, exp((pi_i - C)/mu)), con C por bisección tal que sum q_i = E.",
        "Parámetros: E = 8 kWh (un vendedor); tres compradores con d_i = 8 kWh; "
        "juego A: precios 800, 760 y 720 COP/kWh; juego B: 760, 757 y 720 COP/kWh; "
        "mu de 0,1 a 100 COP/kWh en 241 puntos logarítmicos; mu = 1 marcado (el de la tesis).",
        "La prioridad estricta (mu -> 0) da toda la energía al comprador de precio más alto.",
    ])


# ═════════════════════════════════════════════════════════════════════════════
FIGURAS = {
    "c4_mapa_instituciones": c4_mapa_instituciones,
    "c4_fuentes_registro": c4_fuentes_registro,
    "c4_reconstruccion_udenar": c4_reconstruccion_udenar,
    "c4_generacion_udenar": c4_generacion_udenar,
    "c4_perfiles_e0": c4_perfiles_e0,
    "c4_bolsa": c4_bolsa,
    "c5_banda_hora": c5_banda_hora,
    "c5_barrido_sigma": c5_barrido_sigma,
    "c6_corte_hx": c6_corte_hx,
    "c7_brechas_comunidad": c7_brechas_comunidad,
    "c7_descomposicion": c7_descomposicion,
    "c7_optimalidad_mensual": c7_optimalidad_mensual,
    "c7_subperiodos": c7_subperiodos,
    "c7_brechas_institucion": c7_brechas_institucion,
    "c7_equidad": c7_equidad,
    "c7_coincidencia": c7_coincidencia,
    "c8_probabilidad_inversion": c8_probabilidad_inversion,
    "c8_sobol": c8_sobol,
    "c8_infactibilidad_desercion": c8_infactibilidad_desercion,
    "c8_retiro": c8_retiro,
    "c2_respuesta_logit": c2_respuesta_logit,
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Figuras de los capítulos 4 a 6 de la tesis")
    ap.add_argument("nombres", nargs="*", help="figuras a generar (todas si se omite)")
    a = ap.parse_args(argv)
    nombres = a.nombres or list(FIGURAS)
    desconocidas = [n for n in nombres if n not in FIGURAS]
    exige(not desconocidas, f"figuras desconocidas: {desconocidas}")
    _estilo_tesis()
    for n in nombres:
        print(f"[tesis] {n}")
        FIGURAS[n]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
