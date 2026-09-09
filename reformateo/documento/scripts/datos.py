"""
datos.py — Única puerta de entrada a los datos del documento.
==============================================================
Ningún script de figuras lee un archivo por su cuenta: todo pasa por
aquí. El motivo no es comodidad sino higiene. El árbol del proyecto
contiene varias corridas con nombres casi idénticos y una carpeta de
cuarentena, y ya hubo publicaciones con cifras de un canon superado.
Centralizar la lectura permite:

  * fijar una sola raíz canónica (``CANON``) y que ninguna figura pueda
    apuntar a otra sin que se note;
  * ejecutar la compuerta de verificación antes de dibujar nada;
  * dejar registrada la procedencia de cada dato en el sibling
    ``.fuente.txt`` que escribe ``estilo.guardar()``.

Fuente numérica vigente
-----------------------
``SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_m{1,3}/``
(corrida de la Fase B, 6 144 h, 2026-08-08). El canon de junio
(``entrega_canonica/``) es **referencia histórica**: válido salvo en C4,
y es contra él que se verificó esta corrida.

Prohibido leer desde aquí
-------------------------
``_retirado_2026-08-07/``            cuarentena
``outputs/`` de la raíz             lo sobrescribe ``pytest tests/``
``Presentacion/tesis_p2p/datos/``   copia del canon de JUNIO
``Documentos/auditoria_2026-08-06/caso2_c4/``  validado y retirado

Tres trampas documentadas
-------------------------
1. Las columnas ``SC`` y ``SS`` de la hoja ``Resumen`` están
   **intercambiadas** respecto a su semántica (``core/settlement.py``).
   Usar ``resumen()``, que las devuelve ya corregidas y renombradas a
   ``autoconsumo`` / ``autosuficiencia``.
2. **M1 y M3 invierten los papeles de los agentes.** Cualquier
   superlativo se comprueba con ``reparto_p2p()``, que devuelve el
   reparto real por cobertura.
3. **C4 tiene tres versiones.** ``C4`` es la horaria y ``C4_mensual`` la
   que rige. La del Caso 1 no está en este canon y no se publica como
   resultado.
"""

from __future__ import annotations

import json
import subprocess
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

# ── Rutas ────────────────────────────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parents[3]          # …/SistemaBL
CANON = RAIZ / "SALIDAS_SERVIDOR" / "entrega_canonica_2026-08"
CANON_JUNIO = RAIZ / "SALIDAS_SERVIDOR" / "entrega_canonica"   # solo contraste
AUDITORIA = RAIZ / "Documentos" / "auditoria_artefactos_2026-08-07"
GSA_REAL = RAIZ / "gsa_real" / "salidas"
DATA = RAIZ / "data"
CACHE = Path(__file__).resolve().parent.parent / "datos_cache"

COBERTURAS = ("m1", "m3")

# Orden fijo de instituciones (data/xm_data_loader.py::AGENTS). Las hojas
# Resumen/Por_agente del canon las anonimizan como A1..A5 en este mismo orden.
AGENTES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
ANONIMO_A_AGENTE = {f"A{i + 1}": a for i, a in enumerate(AGENTES)}

# Horizonte canónico
T_START, T_END, N_HORAS = "2025-04-04", "2025-12-16", 6144

# Tipo de medidor de demanda por institución (data/preprocessing.py).
#
# El conteo de horas con demanda negativa NO se fija aquí a propósito. El
# docstring de data/preprocessing.py llegó a citar 989 h para Udenar, 216
# para Mariana y 112 para UCC, cifras que no correspondían al horizonte
# canónico (2025-04-04..2025-12-16, 6.144 h); se corrigieron a 1.517, 213 y
# 94 con CAL-44. La regla se mantiene aunque la fuente ya esté al día: el
# conteo se lee siempre del caché medido, no de una constante que pueda
# volver a quedarse atrás. Ver `conteo_negativas()`.
TIPO_MEDIDOR = {
    "Udenar":  "net",
    "Mariana": "net_partial",
    "UCC":     "net_partial",
    "HUDN":    "gross",
    "Cesmag":  "gross",
}


def _canon(cobertura: str) -> Path:
    if cobertura not in COBERTURAS:
        raise ValueError(f"cobertura debe ser 'm1' o 'm3', no {cobertura!r}")
    return CANON / f"canonica_{cobertura}"


def ruta_salida(cobertura: str, archivo: str) -> Path:
    return _canon(cobertura) / "outputs" / archivo


def ruta_grafica(cobertura: str, archivo: str) -> Path:
    return _canon(cobertura) / "graficas" / archivo


def rel(p: Path) -> str:
    """Ruta relativa a la raíz del proyecto, para el registro de procedencia."""
    try:
        return str(Path(p).resolve().relative_to(RAIZ)).replace("\\", "/")
    except ValueError:
        return str(p)


# ── Compuerta ────────────────────────────────────────────────────────────────
def verificar_canon(estricto: bool = True) -> bool:
    """
    Corre las dos compuertas del proyecto. Debe imprimirse
    ``CANON 2026-08 INTACTO`` y ``CANON INTACTO``.

    Se llama al principio de cada script de figuras. Si falla, con
    ``estricto=True`` aborta: es preferible no generar figura a generarla
    desde un artefacto que alguien movió.
    """
    ok = True
    for script, sello in (
        ("verificar_canon_2026-08.py", "CANON 2026-08 INTACTO"),
        ("verificar_canon.py", "CANON INTACTO"),
    ):
        r = subprocess.run([sys.executable, str(AUDITORIA / script)],
                           capture_output=True, text=True, cwd=str(RAIZ),
                           encoding="utf-8", errors="replace")
        paso = sello in (r.stdout or "")
        print(f"  [canon] {script}: {'OK' if paso else 'FALLA'}")
        ok &= paso
    if not ok and estricto:
        raise SystemExit("Compuerta del canon en rojo. No se generan figuras.")
    return ok


# ── Lectores del canon ───────────────────────────────────────────────────────
def resumen(cobertura: str) -> pd.DataFrame:
    """
    Hoja ``Resumen`` con los rótulos SC/SS **ya corregidos**.

    Las dos columnas venían intercambiadas respecto de su semántica estándar.
    Se comprobaba por física: con 20,0 % de cobertura, la fracción de demanda
    cubierta con generación propia no puede ser 0,98. **El cruce se corrigió
    en el origen (C-164)** y aquí solo se traducen los rótulos.

    AVISO PARA LOS ARTEFACTOS ANTERIORES A ESA CORRECCIÓN: en ellos las dos
    columnas siguen intercambiadas, de modo que compararlos con una corrida
    nueva exige cambiarlas de sitio antes.
    """
    df = pd.read_excel(ruta_salida(cobertura, "resultados_comparacion.xlsx"),
                       sheet_name="Resumen")
    df = df.rename(columns={
        "Ganancia_neta_COP": "ganancia_COP",
        # C-164: el cruce se corrigio en el origen. Las columnas del libro ya
        # dicen lo que son, y aqui solo se traducen al castellano.
        "SC": "autoconsumo",
        "SS": "autosuficiencia",
        "IE": "ie",
        "Escenario": "mecanismo",
    })
    return df[["mecanismo", "ganancia_COP", "autoconsumo", "autosuficiencia", "ie"]]


def por_agente(cobertura: str) -> pd.DataFrame:
    """Hoja ``Por_agente`` con los A1..A5 traducidos a nombre de institución."""
    df = pd.read_excel(ruta_salida(cobertura, "resultados_comparacion.xlsx"),
                       sheet_name="Por_agente")
    df["Agente"] = df["Agente"].map(lambda a: ANONIMO_A_AGENTE.get(a, a))
    return df.rename(columns={"Agente": "institucion"})


def hoja(cobertura: str, libro: str, nombre: str) -> pd.DataFrame:
    """Lector genérico. ``libro`` ∈ {comparacion, analisis, tests}."""
    archivo = {"comparacion": "resultados_comparacion.xlsx",
               "analisis": "resultados_analisis.xlsx",
               "tests": "resultados_tests.xlsx"}[libro]
    return pd.read_excel(ruta_salida(cobertura, archivo), sheet_name=nombre)


def flujos_p2p(cobertura: str) -> pd.DataFrame:
    """
    ``p2p_breakdown_flujos.csv``: una fila por (hora, vendedor, comprador).
    Es byte-idéntico entre el canon de junio y el de agosto — el mercado
    P2P reproduce exactamente; lo único que cambió fue C4.
    """
    return pd.read_csv(ruta_salida(cobertura, "p2p_breakdown_flujos.csv"))


def resumen_horario_p2p(cobertura: str) -> pd.DataFrame:
    return pd.read_csv(ruta_salida(cobertura, "p2p_breakdown_resumen_horario.csv"))


def serie_diaria(cobertura: str) -> pd.DataFrame:
    """Serie diaria de ganancia por mecanismo (base del bootstrap)."""
    cands = sorted((_canon(cobertura) / "outputs").glob("daily_series_*.csv"))
    if not cands:
        raise FileNotFoundError(f"sin daily_series en canonica_{cobertura}")
    return pd.read_csv(cands[-1])


def bootstrap(cobertura: str) -> dict:
    return json.loads(ruta_salida(cobertura, "bootstrap_42.json")
                      .read_text(encoding="utf-8"))


def diagnostico(cobertura: str) -> pd.Series:
    """Metadatos de la corrida: comando, horizonte, fuente de bolsa, hash."""
    return hoja(cobertura, "comparacion", "Diagnostico").iloc[0]


def preproceso(cobertura: str):
    """
    Devuelve (dict_de_series, indice_horario) con los estados intermedios
    del preprocesamiento que guardó ``cache_crudo.py``.

    Claves por institución: ``D_raw``, ``G_recon``, ``D_recon``,
    ``D_limpia``, ``G_ems``, ``G_limpia``, ``mask_out_D``, ``mask_imp_D``,
    ``mask_out_G``, ``mask_imp_G``.
    """
    import numpy as np
    p = CACHE / f"preproceso_{cobertura}.npz"
    if not p.exists():
        raise FileNotFoundError(
            f"Falta {p.name}. Generarlo con: python scripts/cache_crudo.py")
    z = np.load(p, allow_pickle=True)
    horas = pd.to_datetime(z["__horas"])
    series = {k: pd.Series(z[k], index=horas)
              for k in z.files if not k.startswith("__")}
    return series, horas


def conteo_negativas(cobertura: str = "m1") -> pd.DataFrame:
    """
    Resumen medido del preprocesamiento: horas con demanda negativa,
    mínimo alcanzado, atípicos e imputaciones por institución.

    Se lee del caché, nunca del docstring del pipeline: las cifras que
    ese docstring cita quedaron desfasadas respecto al horizonte
    canónico y el documento no debe heredarlas.
    """
    p = CACHE / f"preproceso_{cobertura}_resumen.csv"
    if not p.exists():
        raise FileNotFoundError(
            f"Falta {p.name}. Generarlo con: python scripts/cache_crudo.py")
    return pd.read_csv(p, encoding="utf-8-sig")


def sibling(cobertura: str, nombre: str) -> pd.DataFrame:
    """
    Lee el ``.csv`` hermano de una figura canónica, p. ej.
    ``sibling('m1', 'fig1_perfiles')``. Es la vía preferida para
    regenerar: evita reabrir los libros y conserva exactamente los
    valores que ya se publicaron.
    """
    p = ruta_grafica(cobertura, f"{nombre}.csv")
    return pd.read_csv(p, encoding="utf-8-sig")


def reparto_p2p(cobertura: str) -> pd.DataFrame:
    """
    Reparto real de energía vendida y comprada, por institución.

    Existe para que ningún superlativo del texto se escriba de memoria:
    en M1 Udenar aporta el 76,3 % de lo vendido y UCC absorbe el 36,3 %
    de lo comprado; en M3 los papeles se invierten y Cesmag absorbe el
    70,9 %. Toda frase con «el mayor» se comprueba contra esta tabla.
    """
    f = flujos_p2p(cobertura)
    total = f["kWh_transados"].sum()
    v = f.groupby("vendedor")["kWh_transados"].sum() / total * 100
    c = f.groupby("comprador")["kWh_transados"].sum() / total * 100
    out = pd.DataFrame({"vende_pct": v, "compra_pct": c}).reindex(AGENTES)
    out.index.name = "institucion"
    return out.reset_index()


# ── Series de precio y tarifa (capítulo 5) ───────────────────────────────────
def precios_bolsa(solo_horizonte: bool = True) -> pd.DataFrame:
    """
    Serie horaria de precio de bolsa, con una marca de tiempo ya montada.

    El archivo de caché va **más allá del horizonte del estudio**: cubre
    hasta enero de 2026, mientras que el horizonte canónico termina el
    2025-12-16. Por defecto se recorta, porque una figura que promediara
    la serie completa daría \\SI{193.6}{} COP/kWh en vez de los
    \\SI{182.5}{} que corresponden a las 6.144 horas del estudio, y esa
    diferencia se propagaría a cualquier comparación con la tarifa.
    """
    b = pd.read_csv(DATA / "precios_bolsa_xm_api.csv")
    b["ts"] = pd.to_datetime(b["Fecha"]) + pd.to_timedelta(b["Hora"] - 1, "h")
    if solo_horizonte:
        b = b[(b["ts"] >= T_START) & (b["ts"] < T_END)]
    return b.sort_values("ts").reset_index(drop=True)


def precios_escasez() -> pd.DataFrame:
    return pd.read_csv(DATA / "precios_escasez_creg.csv")


def tarifas_cedenar() -> pd.DataFrame:
    """
    Tarifas CEDENAR mes a mes, transcritas de los PDF oficiales.

    El archivo lleva una cabecera larga de comentarios con el
    procedimiento de transcripción, de modo que hay que leerlo saltando
    las líneas que empiezan por almohadilla. Las filas sin ``CU_aplicado``
    son marcadores de meses pendientes y se descartan, igual que hace
    ``data/cedenar_tariff.py``.
    """
    df = pd.read_csv(DATA / "tarifas_cedenar_mensual.csv", comment="#")
    df = df[df["CU_aplicado"].notna()].copy()
    df["mes"] = df["mes"].astype(str)
    return df


# ── Sensibilidad global (capítulo 11) ────────────────────────────────────────
def indices_sobol(cobertura: str) -> pd.DataFrame:
    """Índices Sobol sobre datos reales (896 evaluaciones por cobertura)."""
    return pd.read_csv(GSA_REAL / f"indices_{cobertura.upper()}_full_n128_s42.csv")


def muestras_sobol(cobertura: str) -> pd.DataFrame:
    return pd.read_csv(GSA_REAL / f"muestras_{cobertura.upper()}_full_n128_s42.csv")


if __name__ == "__main__":
    print("Raíz:", RAIZ)
    print("Canon:", rel(CANON), "->", "existe" if CANON.exists() else "NO EXISTE")
    verificar_canon()
    for c in COBERTURAS:
        r = resumen(c)
        print(f"\n== {c.upper()} ==")
        print(r.to_string(index=False))
        print(reparto_p2p(c).to_string(index=False))
