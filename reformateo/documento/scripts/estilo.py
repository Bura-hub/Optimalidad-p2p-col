"""
estilo.py — Identidad visual única del documento de proceso.
=============================================================
Todas las figuras del documento se dibujan a través de este módulo. El
objetivo es que las ~75 figuras generadas por scripts distintos se lean
como un solo sistema: misma paleta, misma tipografía, mismos tamaños,
mismo formato de número.

Convenciones que fija este módulo
---------------------------------
1. **Ancho físico.** El documento es ``article`` 12pt con
   ``geometry margin=1in``, de modo que el ancho de caja es 6,5 in. Las
   figuras se incrustan al 95 % de ese ancho. Dibujarlas a
   ANCHO_COMPLETO = 6,5 in las deja prácticamente a escala 1:1, así que
   una etiqueta de 9 pt en la figura se imprime a ~9 pt en la página.

2. **Formato de número español.** Miles con punto, decimales con coma,
   igual que en los informes del autor («4.839,52 kg», «12,0 tCO2/año»).
   Matplotlib no lo hace solo: usar ``fmt_miles`` / ``fmt_cop`` /
   ``fmt_pct`` o el localizador ``eje_espanol()``.

3. **Dos coberturas siempre.** Casi toda figura del documento se
   presenta como panel M1 | M3. ``figura_m1_m3()`` construye ese par ya
   rotulado, para que ninguna figura pueda publicarse sin declarar de
   qué frontera de medición habla.

4. **Trazabilidad.** ``guardar()`` escribe el PNG y, junto a él, un
   ``.csv`` con los datos que se dibujaron y un ``.fuente.txt`` con la
   procedencia (ruta del artefacto canónico). Un revisor puede auditar
   cualquier figura sin ejecutar el proyecto.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

# ── Geometría ────────────────────────────────────────────────────────────────
ANCHO_COMPLETO = 6.5    # in — ancho de caja del documento (article 12pt, 1in)
ANCHO_MEDIO    = 3.15   # in — media caja
ALTO_ESTANDAR  = 3.4
ALTO_BAJO      = 2.4
ALTO_ALTO      = 4.6
DPI            = 300

DIR_FIGURAS = Path(__file__).resolve().parent.parent / "figuras"

# ── Paleta ───────────────────────────────────────────────────────────────────
# El P2P es el protagonista y lleva el único azul saturado; los mecanismos
# regulatorios ocupan una familia cálida, de modo que la comparación siga
# siendo legible impresa en escala de grises (el P2P queda como el más
# oscuro de su grupo y C4_mensual como el más oscuro de los cálidos).
MECANISMOS = {
    "P2P":        "#1F6F8B",   # azul petróleo — el mecanismo propuesto
    "C1":         "#8C8C8C",   # gris medio    — autogeneración individual
    "C2":         "#9B6BA8",   # violeta       — PPA bilateral
    "C3":         "#B78FC2",   # violeta claro — bolsa (C2 == C3 por construcción)
    "C4":         "#E0A458",   # ámbar claro   — colectivo, base horaria
    "C4_mensual": "#C1642A",   # ámbar oscuro  — colectivo, base mensual (la que rige)
    "C5":         "#5B8C5A",   # verde         — autogeneración remota (AGR)
}

# Etiquetas legibles. El documento nunca imprime el nombre interno a secas.
ETIQUETAS = {
    "P2P":        "P2P",
    "C1":         "C1 · individual",
    # CAL-52: ya no es un contrato con un tercero a precio de mercado, sino el
    # contrato INTERNO de la comunidad al punto medio de la banda.
    "C2":         "C2 · contrato interno",
    "C3":         "C3 · bolsa",
    "C4":         "C4 · colectivo (horario)",
    "C4_mensual": "C4 · colectivo (mensual)",
    "C5":         "C5 · AGR",
}

# Orden de presentación: el propuesto primero, luego los regulatorios en el
# orden en que los introduce el capítulo 8.
ORDEN_MECANISMOS = ["P2P", "C1", "C2", "C3", "C4", "C4_mensual", "C5"]

# Instituciones, en el orden fijo de data/xm_data_loader.py::AGENTS.
# Ninguna reutiliza el verde de C5: en las figuras de perfil ese verde ya
# está tomado por la curva de generación, y una institución del mismo color
# haría ilegible el panel. Por eso UCC lleva vino y no verde.
INSTITUCIONES = {
    "Udenar":  "#2C5F7C",   # azul pizarra
    "Mariana": "#C1642A",   # naranja quemado
    "UCC":     "#8B3A62",   # vino
    "HUDN":    "#9B6BA8",   # lavanda
    "Cesmag":  "#B0913B",   # mostaza
}
ORDEN_INSTITUCIONES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]

# Como se imprime cada institucion. La clave interna viene de los CSV del
# canon y no se toca; lo que cambia es el rotulo. CESMAG va en mayusculas
# porque es una sigla, la del Centro de Estudios Superiores Maria Goretti,
# y la propia universidad corrigio esa grafia por acuerdo en 2022.
ETIQUETA_INSTITUCION = {"Udenar": "Udenar", "Mariana": "Mariana",
                        "UCC": "UCC", "HUDN": "HUDN", "Cesmag": "CESMAG"}


def etiqueta_institucion(nombre: str) -> str:
    return ETIQUETA_INSTITUCION.get(nombre, nombre)

# Semántica de proceso: el par antes/después que recorre el capítulo 3.
ANTES   = "#B4534B"   # rojo apagado  — el dato tal como llegó
DESPUES = "#1F6F8B"   # azul petróleo — el dato ya tratado
NEUTRO  = "#8C8C8C"
APOYO   = "#D8D2C4"   # relleno de fondo, bandas, sombreados
ALERTA  = "#C1642A"

# Coberturas
COBERTURAS = {"m1": "#2C5F7C", "m3": "#C1642A"}
# Los rotulos describen lo que los medidores SON, segun el inventario de
# instalacion, y no lo que se creyo que eran. El Medidor 1 no totaliza el
# campus en ninguna de las cinco instituciones: en tres es el circuito de
# inyeccion y en dos el totalizador de un bloque. El Medidor 3 tampoco es
# el circuito alimentado por el fotovoltaico: son circuitos secundarios, un
# totalizador de piso y, en el HUDN, la UPS de ginecologia. Ver H-7 en
# HALLAZGOS.md y data/inventario/Inventario_Medidores_MTE.xlsx.
# El porcentaje es la razon generacion/consumo DEL CIRCUITO MEDIDO, no la
# autosuficiencia de la institucion.
# Fuente unica: el nombre y la razon se escriben una sola vez y de ahi se
# derivan todas las formas. Antes el titulo largo vivia aqui y la version de
# dos lineas estaba escrita a mano dentro de figura_m1_m3(), de modo que
# podian divergir sin que nadie lo notara.
COBERTURA_NOMBRE = {
    "m1": "M1 · circuito principal o de inyección",
    "m3": "M3 · circuito secundario",
}
_GD_RESPALDO = {"m1": "20,0 %", "m3": "95,3 %"}


def _razon_gd() -> dict:
    """Razón entre generación y demanda de cada frontera, desde la caché.

    Estuvo escrita a mano y se quedó atrás cuando cambió la generación de
    Udenar: el texto decía una cosa y los títulos de las figuras otra. Se
    calcula del mismo sitio del que salen las series, de modo que no puede
    volver a divergir.
    """
    import numpy as np
    salida = {}
    for c in ("m1", "m3"):
        p = (Path(__file__).resolve().parent.parent
             / "datos_cache" / f"preproceso_{c}.npz")
        if not p.exists():
            # C-171: la ruta que este aviso daba no existe. El guion vive en
            # esta misma carpeta, y quien leyera el aviso en el servidor lo
            # buscaba donde no está.
            print(f"  AVISO estilo: falta {p.name}; la razón G/D de {c.upper()} "
                  "sale del respaldo. No es un fallo: la figura sale igual y "
                  "solo esa razón viene de un valor de reserva. Para "
                  "calcularla, correr "
                  "reformateo/documento/scripts/cache_crudo.py")
            salida[c] = _GD_RESPALDO[c]
            continue
        z = np.load(p, allow_pickle=True)
        g = sum(z[k].sum() for k in z.files if k.endswith("__G_limpia"))
        d = sum(z[k].sum() for k in z.files if k.endswith("__D_limpia"))
        salida[c] = f"{100 * g / d:.1f} %".replace(".", ",")
    return salida


COBERTURA_GD = _razon_gd()

TITULO_COBERTURA = {
    k: f"{COBERTURA_NOMBRE[k]} (G/D = {COBERTURA_GD[k]})"
    for k in COBERTURA_NOMBRE
}
# Forma corta, para marcas de eje y leyendas donde el nombre largo no cabe.
# Se nombra la razon generacion/consumo y no «cobertura», que invitaba a
# leerlo como autosuficiencia de la institucion.
COBERTURA_CORTA = {
    k: f"{k.upper()} · G/D = {COBERTURA_GD[k]}" for k in COBERTURA_NOMBRE
}


def titulo_cobertura(cob: str, dos_lineas: bool = False) -> str:
    """Titulo de cobertura; en dos lineas cuando va como titulo de panel."""
    c = cob.lower()
    if dos_lineas:
        return f"{COBERTURA_NOMBRE[c]}" + "\n" + f"(G/D = {COBERTURA_GD[c]})"
    return TITULO_COBERTURA[c]


def rotulo_cobertura(fig, cob: str, y: float = 1.0) -> None:
    """
    Declara la frontera de medicion de una figura de un solo panel.

    Las figuras que se generan por separado para cada cobertura son casi
    identicas entre si, de modo que sin este rotulo el lector no puede
    saber cual esta mirando.
    """
    c = cob.lower()
    fig.suptitle(TITULO_COBERTURA[c], color=COBERTURAS[c],
                 fontweight="bold", fontsize=9, y=y)


# ── rcParams ─────────────────────────────────────────────────────────────────
def aplicar_estilo() -> None:
    """Fija los rcParams del documento. Idempotente; se llama al importar."""
    plt.rcParams.update({
        # Tipografía con serifa, para que la figura no choque con el cuerpo
        # del texto (Computer Modern). CMU Serif si está instalada; si no,
        # DejaVu Serif, que viene con matplotlib y siempre existe.
        "font.family":       "serif",
        "font.serif":        ["CMU Serif", "DejaVu Serif", "Times New Roman"],
        "mathtext.fontset":  "cm",
        # cmr10 no trae el signo menos Unicode; con esto se usa el ASCII.
        "axes.unicode_minus": False,

        "font.size":         9,
        "axes.titlesize":    9.5,
        "axes.labelsize":    9,
        "xtick.labelsize":   8,
        "ytick.labelsize":   8,
        "legend.fontsize":   8,
        "figure.titlesize":  10.5,

        "axes.grid":         True,
        "grid.color":        "#DDDDDD",
        "grid.linewidth":    0.6,
        "grid.alpha":        0.9,
        "axes.axisbelow":    True,

        "axes.spines.top":   False,
        "axes.spines.right": False,
        "axes.edgecolor":    "#555555",
        "axes.linewidth":    0.8,

        "lines.linewidth":   1.5,
        "lines.markersize":  4,

        "legend.frameon":    False,
        "figure.facecolor":  "white",
        "savefig.facecolor": "white",
        "savefig.dpi":       DPI,
        "savefig.bbox":      "tight",
        "savefig.pad_inches": 0.02,
    })


# ── Formato de número español ────────────────────────────────────────────────
def fmt_miles(x, decimales: int = 0) -> str:
    """1234567.8 -> '1.234.568'. Miles con punto, decimales con coma."""
    s = f"{x:,.{decimales}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def fmt_cop(x, decimales: int = 0) -> str:
    return fmt_miles(x, decimales) + " COP"


def fmt_millones(x, decimales: int = 2, sufijo: bool = True) -> str:
    """
    53619160 -> '53,62 M'.

    Con sufijo=False devuelve '53,62' a secas, que es lo que corresponde
    cuando el rotulo del eje ya dice «(millones de COP)». Mezclar el
    multiplicador con la unidad produce ejes que imprimen «53,62 M» bajo
    un rotulo que dice «(COP)», y ademas gasta ancho en los ejes apretados.
    """
    s = fmt_miles(x / 1e6, decimales)
    return s + " M" if sufijo else s


# Rotulos de eje que acompanan a cada formato monetario. Se nombran aqui
# para que ninguna figura invente el suyo.
ROTULO_COP      = "Ganancia neta (COP)"
ROTULO_MILLONES = "Ganancia neta (millones de COP)"


def fmt_pct(x, decimales: int = 1) -> str:
    return fmt_miles(x, decimales) + " %"


def eje_espanol(ax, eje: str = "y", modo: str = "miles", decimales: int = 0):
    """Aplica el formato español al eje indicado ('x', 'y' o 'ambos')."""
    func = {"miles": fmt_miles, "millones": fmt_millones, "pct": fmt_pct}[modo]
    f = FuncFormatter(lambda v, _: func(v, decimales))
    if eje in ("y", "ambos"):
        ax.yaxis.set_major_formatter(f)
    if eje in ("x", "ambos"):
        ax.xaxis.set_major_formatter(f)
    return ax


# ── Constructores de figura ──────────────────────────────────────────────────
def figura(alto: float = ALTO_ESTANDAR, ancho: float = ANCHO_COMPLETO):
    """Figura de un solo eje, a ancho de caja."""
    fig, ax = plt.subplots(figsize=(ancho, alto))
    return fig, ax


def figura_m1_m3(alto: float = ALTO_ESTANDAR, compartir_y: bool = False,
                 titulos: bool = True):
    """
    El par canónico del documento: panel izquierdo M1, panel derecho M3.

    Devuelve (fig, ax_m1, ax_m3). Los títulos declaran la cobertura y su
    porcentaje, de modo que la figura no pueda leerse fuera de contexto.
    """
    fig, axes = plt.subplots(1, 2, figsize=(ANCHO_COMPLETO, alto),
                             sharey=compartir_y)
    if titulos:
        for ax, cob in zip(axes, ("m1", "m3")):
            ax.set_title(titulo_cobertura(cob, dos_lineas=True),
                         color=COBERTURAS[cob], fontweight="bold", pad=8)
    return fig, axes[0], axes[1]


def figura_antes_despues(alto: float = ALTO_ESTANDAR, compartir_y: bool = True):
    """El par del capítulo 3: el dato como llegó | el dato ya tratado."""
    fig, axes = plt.subplots(1, 2, figsize=(ANCHO_COMPLETO, alto),
                             sharey=compartir_y)
    axes[0].set_title("Antes", color=ANTES, fontweight="bold", pad=8)
    axes[1].set_title("Después", color=DESPUES, fontweight="bold", pad=8)
    return fig, axes[0], axes[1]


def color_mecanismo(nombre: str) -> str:
    return MECANISMOS.get(nombre, NEUTRO)


def etiqueta_mecanismo(nombre: str) -> str:
    return ETIQUETAS.get(nombre, nombre)


def color_institucion(nombre: str) -> str:
    return INSTITUCIONES.get(nombre, NEUTRO)


def eje_instituciones(ax, orden=None, eje: str = "y"):
    """
    Fija marcas, rotulos y sentido del eje de instituciones de una vez.

    Existe por un fallo mudo que ya reordeno tres figuras: cuando los dos
    paneles comparten el eje vertical, llamar a invert_yaxis() dentro del
    bucle lo invierte dos veces y la segunda deshace la primera, de modo
    que las instituciones salen al reves del orden fijo sin que nada avise.
    Aqui el sentido se fija con set_ylim, que es idempotente: da igual
    cuantas veces se llame.
    """
    orden = list(orden or ORDEN_INSTITUCIONES)
    pos = range(len(orden))
    etiquetas = [etiqueta_institucion(i) for i in orden]
    if eje == "y":
        ax.set_yticks(list(pos))
        ax.set_yticklabels(etiquetas)
        ax.set_ylim(len(orden) - 0.5, -0.5)   # primera arriba, siempre
    else:
        ax.set_xticks(list(pos))
        ax.set_xticklabels(etiquetas)
        ax.set_xlim(-0.5, len(orden) - 0.5)
    return ax


def rotulo_x_comun(fig, texto: str, rect=(0, 0.03, 1, 1)):
    """
    Un solo rotulo de eje x para los dos paneles.

    El rotulo centrado bajo el panel derecho se sale de la caja de 6,5 in y
    el recorte ajustado del guardado lo corta en vez de ensanchar la
    figura, de modo que sale truncado. Afecto a cinco figuras antes de
    detectarse.
    """
    fig.supxlabel(texto)
    fig.tight_layout(rect=rect)
    return fig


# ── Vocabulario en espanol ───────────────────────────────────────────────────
# matplotlib no localiza los nombres de mes ni de dia, y cualquier eje
# temporal del documento los necesita. Estaban duplicados en dos generadores.
MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre",
                "diciembre"]
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes",
           "sábado", "domingo"]


def fmt_fecha(ts, modo: str = "mes") -> str:
    """
    Fecha en espanol. modo: 'mes' -> 'jul 25' · 'mes_anio' -> 'jul 2025' ·
    'mes_largo' -> 'julio' · 'dia_corto' -> '16 de julio de 2025' ·
    'dia' -> 'miércoles 16 de julio de 2025'.

    El modo 'mes' es para ejes estrechos, donde el ano de dos cifras ahorra
    el sitio que no hay; 'mes_anio' para ejes anchos, donde el ano completo
    se lee sin ambiguedad. 'dia_corto' es 'dia' sin el dia de la semana,
    que en un titulo es ruido.
    """
    if modo == "dia_corto":
        return f"{ts.day} de {MESES_LARGOS[ts.month - 1]} de {ts.year}"
    if modo == "mes":
        return f"{MESES_ES[ts.month - 1]} {ts.year % 100:02d}"
    if modo == "mes_anio":
        return f"{MESES_ES[ts.month - 1]} {ts.year}"
    if modo == "mes_largo":
        return MESES_LARGOS[ts.month - 1]
    return (f"{DIAS_ES[ts.weekday()]} {ts.day} de "
            f"{MESES_LARGOS[ts.month - 1]} de {ts.year}")


# Los tres tipos de medidor, en el vocabulario que usa el texto. El nombre
# interno viene del canon y no se toca; lo que no puede es imprimirse.
TIPO_MEDIDOR_ES = {"net": "neto", "net_partial": "neto parcial",
                   "gross": "bruto"}


# Forma corta de cada mecanismo, para marcas de eje. Acortar el rotulo largo
# cortando por el separador colapsa las dos versiones del colectivo en un
# mismo «C4», de modo que el eje imprimia dos categorias distintas con
# identico rotulo y el lector no podia saber cual rige. C2 y C3 son el mismo
# resultado por construccion y se presentan fusionados.
ETIQUETA_CORTA = {
    "P2P":        "P2P",
    "C1":         "C1 individual",
    "C2":         "C2 = C3",
    "C3":         "C2 = C3",
    "C4":         "C4 horario",
    "C4_mensual": "C4 mensual",
    "C5":         "C5 AGR",
}


def etiqueta_corta(nombre: str) -> str:
    return ETIQUETA_CORTA.get(nombre, nombre)


# Colores semanticos de papel, independientes de la identidad de los
# mecanismos. Antes «vende» tomaba prestado el verde de C5 y «compra» el
# violeta de C2, con lo que un mismo color significaba dos cosas.
VENDE      = "#2C6E6B"   # verde azulado
COMPRA     = "#8B3A62"   # vino
GENERACION = "#5B8C5A"   # verde — la curva de generacion del capitulo 3

# Tinta: el gris muy oscuro de la serie principal cuando la serie no es una
# magnitud del mercado. La curva de demanda del capitulo 3 es este mismo
# tono, de modo que DEMANDA queda como alias y ninguna figura se repinta.
TINTA      = "#3A3A3A"
# Gris de las bandas alternas que separan los bloques de una figura
# agrupada, y gris del rotulo de lo que la figura no emplea.
FONDO_BANDA = "#F4F4F4"
# Relleno de lo que la figura muestra pero el modelo no emplea.
APAGADO     = "#D5D5D5"
DEMANDA    = TINTA


# ── Guardado con trazabilidad ────────────────────────────────────────────────
def guardar(fig, nombre: str, datos=None, procedencia=None,
            cerrar: bool = True) -> Path:
    """
    Guarda la figura y su rastro.

    Escribe hasta tres archivos hermanos en ``figuras/``:
      - ``<nombre>.png``          la figura
      - ``<nombre>.csv``          los datos exactos que se dibujaron
      - ``<nombre>.fuente.txt``   de qué artefacto canónico salieron

    El tercero es el que permite auditar la figura sin ejecutar el
    proyecto: dice literalmente qué archivo se leyó.
    """
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    png = DIR_FIGURAS / f"{nombre}.png"
    fig.savefig(png)

    if datos is not None:
        df = datos if isinstance(datos, pd.DataFrame) else pd.DataFrame(datos)
        df.to_csv(DIR_FIGURAS / f"{nombre}.csv", index=False,
                  encoding="utf-8-sig")

    if procedencia is not None:
        rutas = [procedencia] if isinstance(procedencia, str) else list(procedencia)
        (DIR_FIGURAS / f"{nombre}.fuente.txt").write_text(
            "Figura: " + nombre + "\n"
            "Artefactos leidos:\n" + "\n".join(f"  - {r}" for r in rutas) + "\n",
            encoding="utf-8")

    if cerrar:
        plt.close(fig)
    print(f"  [figura] {png.name}")
    return png


aplicar_estilo()
