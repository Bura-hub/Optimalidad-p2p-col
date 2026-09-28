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
_CON_HUECOS = {"c5_banda_hora", "c4_generacion_udenar"}


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
