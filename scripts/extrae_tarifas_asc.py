"""
Construye data/tarifas_asc_mensual.csv desde los PDF de ASC Ingenieria.

CAL-47. ASC Ingenieria S.A. E.S.P. es el comercializador de cuatro de las cinco
instituciones, confirmado por tres vias: el asesor regulatorio las enumera
en reunion, el archivo de consumos que ASC entrego contiene exactamente esas
cuatro, y el autor confirma que el comercializador del CESMAG es CEDENAR.
La comunidad tiene por tanto DOS comercializadores.

Hasta ahora el trabajo liquidaba contra la tabla de CEDENAR, que es el
operador de red y no el comercializador. Los cargos de red coinciden entre
las dos tablas, como debe ser porque los fija el operador; lo que difiere es
lo que el comercializador negocia, es decir generacion y comercializacion.

**La diferencia no es menor.** ASC cobra por comercializar 38,37 COP/kWh de
media donde CEDENAR cobra 174,92. Y como el ancho de la banda del mercado
entre pares ES el cargo de comercializacion, el espacio economico del
mecanismo se divide por 4,6 al usar el comercializador correcto.

El formato de salida es el mismo que el de CEDENAR para que el cargador
existente lo lea sin cambios.

Una diferencia de forma que hay que declarar: **la tabla de ASC no desglosa
el cargo adicional por separado**; la suma de sus seis componentes da
exactamente su costo unitario publicado. Se emite entonces con ese cargo en
cero, y no se inventa un reparto.

Uso:
    python scripts/extrae_tarifas_asc.py
    python scripts/extrae_tarifas_asc.py --verifica
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PDFS = RAIZ / "data" / "ASC_pdfs"
SALIDA = RAIZ / "data" / "tarifas_asc_mensual.csv"

# Las filas de componentes: nivel, texto opcional de propiedad, seis numeros.
_FILA = re.compile(
    r"^(?P<nivel>[123])\s+(?P<txt>[A-Za-z%\s.]*?)\s*"
    r"(?P<g>\d+\.\d+)\s+(?P<t>\d+\.\d+)\s+(?P<d>\d+\.\d+)\s+"
    r"(?P<cv>\d+\.\d+)\s+(?P<pr>\d+\.\d+)\s+(?P<r>\d+\.\d+)\s*$",
    re.M)

CABECERA = """# Tarifas ASC Ingenieria S.A. E.S.P. — CU mensual por nivel de tension
# =====================================================================
# Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0 · CAL-47
#
# La comunidad MTE tiene DOS comercializadores, no uno:
#   ASC Ingenieria  -> Universidad de Narino, Universidad Mariana,
#                      Universidad Cooperativa y Hospital Departamental
#   CEDENAR         -> CESMAG
# De modo que las cinco NO comparten techo, y el techo por agente de CAL-35
# sigue haciendo falta. La heterogeneidad es un dato, no un supuesto.
#
# Generado por scripts/extrae_tarifas_asc.py desde data/ASC_pdfs/.
# NO editar a mano: volver a correr el script.
#
# Diferencias con la tabla de CEDENAR, medidas sobre el horizonte:
#   - los cargos de red coinciden (270,96 frente a 274,16), como debe ser
#     porque los fija el operador de red y no el comercializador;
#   - la generacion de ASC es mas cara (412,92 frente a 304,65);
#   - la comercializacion de ASC es 4,6 veces mas barata (38,37 frente
#     a 174,92), y ESE es el ancho de la banda del mercado entre pares.
#
# La tabla de ASC no desglosa el cargo adicional por separado: la suma de
# sus seis componentes da exactamente su costo unitario. Se emite con ese
# cargo en cero en vez de inventar un reparto.
#
# La categoria "oficial" es la fila SIN contribucion de solidaridad, que es
# la que corresponde a un usuario no regulado exento; "comercial" lleva el
# 20 %. Ver data/cedenar_tariff.py y ADR-0047.
"""

COLS = ("mes,categoria,nivel_tension,propiedad,Gm,Tm,Dnm,Cvm,PR,Rm,COT,"
        "CU_aplicado,fuente")


def _propiedad(nivel: int, texto: str) -> str:
    """Traduce el rotulo de propiedad del activo al vocabulario del proyecto."""
    if nivel != 1:
        return "cedenar"
    t = texto.upper()
    if "USUARIO" in t:
        return "usuario"
    if "50" in t:
        return "compartida"
    return "cedenar"


def lee_mes(pdf: Path) -> list[dict]:
    from pypdf import PdfReader
    mes = pdf.stem.replace("tarifa_", "")
    texto = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
    filas = []
    vistos = set()
    for m in _FILA.finditer(texto):
        nivel = int(m.group("nivel"))
        prop = _propiedad(nivel, m.group("txt"))
        if (nivel, prop) in vistos:
            continue
        vistos.add((nivel, prop))
        v = {k: float(m.group(k)) for k in ("g", "t", "d", "cv", "pr", "r")}
        cu = sum(v.values())
        filas.append(dict(mes=mes, nivel=nivel, propiedad=prop,
                          Gm=v["g"], Tm=v["t"], Dnm=v["d"], Cvm=v["cv"],
                          PR=v["pr"], Rm=v["r"], CU=cu, fuente=pdf.name))
    return filas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verifica", action="store_true",
                    help="solo comprueba la lectura, no escribe")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    pdfs = sorted(PDFS.glob("tarifa_*.pdf"))
    if not pdfs:
        raise SystemExit(f"sin PDF en {PDFS}")

    todo = []
    for p in pdfs:
        filas = lee_mes(p)
        if not filas:
            print(f"  AVISO: {p.name} sin filas legibles")
            continue
        todo.extend(filas)
        nt2 = [f for f in filas if f["nivel"] == 2]
        if not nt2:
            print(f"  AVISO: {p.name} sin nivel de tension 2")
        else:
            f = nt2[0]
            print(f"  {f['mes']}  {len(filas)} filas · NT2 "
                  f"CU {f['CU']:8.2f} · comercializacion {f['Cvm']:6.2f}")

    if args.verifica:
        print(f"\n{len(todo)} filas leidas de {len(pdfs)} archivos. "
              f"No se escribio nada.")
        return

    lineas = [CABECERA.rstrip(), COLS]
    for f in todo:
        for cat, factor in (("oficial", 1.0), ("comercial", 1.2)):
            lineas.append(
                f"{f['mes']},{cat},{f['nivel']},{f['propiedad']},"
                f"{f['Gm']:.4f},{f['Tm']:.4f},{f['Dnm']:.4f},{f['Cvm']:.4f},"
                f"{f['PR']:.4f},{f['Rm']:.4f},0.0000,"
                f"{f['CU'] * factor:.4f},{f['fuente']}")
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nEscrito {SALIDA.relative_to(RAIZ)} con {len(todo) * 2} filas "
          f"de {len(pdfs)} meses.")


if __name__ == "__main__":
    main()
