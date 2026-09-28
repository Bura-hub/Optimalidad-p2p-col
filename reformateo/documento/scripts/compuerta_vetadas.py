"""Compuerta de cifras, rutas y citas vetadas sobre el manuscrito (punto F3).

Preparación antes de redactar, 2026-09-27; C-221.

`tesis.md` se escribió sobre los canon de junio y agosto, y el canon vigente
(`Documentos/canon_2026-09/`) superó muchas de sus cifras, rutas y citas. Esta
compuerta busca en un fichero Markdown (por defecto
`Documentos/FinalTesisV2/tesis.md`) cada patrón vetado y dice dónde aparece,
por qué está vetado y de dónde sale lo que lo sustituye. Sale con código 0 si
no encuentra ninguno y con 1 si encuentra alguno. Se corre antes de dar por
terminado un capítulo y, al final, sobre el manuscrito entero.

Una coincidencia no siempre es un error (una cifra vieja citada a propósito,
como historia, con su aclaración); en ese caso se marca la línea con el
comentario HTML `<!-- vetada-ok: <motivo> -->` y la compuerta la acepta.

Uso:
    .venv/Scripts/python.exe reformateo/documento/scripts/compuerta_vetadas.py [fichero.md ...]
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
POR_DEFECTO = RAIZ / "Documentos" / "FinalTesisV2" / "tesis.md"
EXCEPCION = re.compile(r"<!--\s*vetada-ok:\s*[^>]+-->")


@dataclass(frozen=True)
class Vetada:
    patron: str
    motivo: str
    fuente: str
    ignora_mayusculas: bool = False


VETADAS = [
    # ── Cifras de canon superados ──────────────────────────────────────────
    Vetada(r"53[,.]62", "beneficio del P2P del canon de junio (M1)",
           "CANON.md §6 (E0: 46,50 MCOP)"),
    Vetada(r"34[,.]55", "beneficio del canon de junio (M3)",
           "CANON.md §6; M3 retirada (D10)"),
    Vetada(r"5[ .]?021|8[ .]?162", "cifras del bootstrap (C-218: retirado)",
           "probabilidad de inversión del GSA (CANON §13.3), mes a mes (D72)"),
    Vetada(r"0[,.]1513", "Gini del P2P del canon de junio",
           "hoja PoF_Fairness del canon (E0: 0,1207)"),
    Vetada(r"0[,.]0215", "precio de la justicia del canon de junio",
           "precio_justicia_2026-09-27 (C-208; E0: 4,3 %)"),
    Vetada(r"0[,.]3669", "índice de equidad del canon de junio",
           "C-214: la equidad entre mecanismos se cita con el Gini"),
    Vetada(r"0[,.]84[67]|0[,.]879", "índices de Sobol del GSA de junio",
           "CANON §13 (GSA directo)"),
    Vetada(r"1[ .]?004[,.]4", "spread de ineficiencia estática horario (retirado)",
           "spread_estatico_2026-09-27 (C-209, H-100)"),
    Vetada(r"0[,.]1876|0[,.]9806", "autoconsumo y autosuficiencia del canon de agosto",
           "regla 3 de CLAUDE.md y C-214"),
    Vetada(r"0[,.]937", "parte del vendedor medida contra la bolsa (no publicable)",
           "regla 2: la del almacén (E0: 0,542)"),
    Vetada(r"n_?base\s*=\s*128|n\s*=\s*128\b", "GSA de junio (n = 128)",
           "CANON §13 (n = 2 048 y 512)"),
    # ── Rutas y objetos superados ──────────────────────────────────────────
    Vetada(r"entrega_canonica|entrega_matriz_2026-09-15|matriz_reposo_2026-09-17",
           "entregas superadas (regla 1 del canon)",
           "SALIDAS_SERVIDOR/entrega_matriz_reposo_2026-09-19/"),
    Vetada(r"entrega_gsa_directo_2026-09-27(?!_)", "entrega del GSA superada",
           "entrega_gsa_directo_completo_2026-09-27 (CANON §13.8.5)"),
    Vetada(r"gsa_real|--paper-meters", "GSA viejo y opción retirada (D79, D10)",
           "gsa_directo/"),
    Vetada(r"\bM3\b", "segunda frontera retirada (D10, H-77)",
           "matriz de escalado sobre M1 (D10 a D12)"),
    Vetada(r"C4_mensual", "alias exacto de C4 (regla 4, C-218)",
           "C4"),
    Vetada(r"fig13_desglose|prima_vendedor_COP", "desglose no citable (C-216)",
           "descomposicion_p2p_2026-09-27 (H-101)"),
    Vetada(r"\bFA-?1b?\b|\bFA-?3\b", "instrumentos de factibilidad retirados (C-216)",
           "D67, H-103 (deserción) y H-106 (retiro)"),
    # ── Métodos y lecturas superadas ───────────────────────────────────────
    Vetada(r"v[ií]a acoplada|solucionador acoplado|alternad[ao]",
           "método de producción anterior al reposo (D48)",
           "el reposo en forma cerrada (D48, MODELO_DEFINITIVO.md)",
           ignora_mayusculas=True),
    Vetada(r"C4 horario|variante horaria|colectivo horario",
           "colectivo horario retirado (D4, C-175)", "C4 mensual (arts. 19 a 21)",
           ignora_mayusculas=True),
    Vetada(r"C2\s*=\s*C3", "identidad del canon de agosto",
           "regla 5: el agregado de P2P y C2 coinciden (CAL-52)"),
    Vetada(r"bootstrap", "retirado para cifras publicables (C-218)",
           "probabilidad de inversión del GSA, mes a mes, subperíodos",
           ignora_mayusculas=True),
    # ── Citas normativas corregidas (C-217) ────────────────────────────────
    Vetada(r"art(?:\.|ículo)\s*26\s+de\s+la\s+(?:Resolución\s+)?(?:CREG\s+)?101[ .]?097",
           "cita no sostenida: la 101 097 trata la función del precio de escasez",
           "art. 1 (lit. i y ii) y art. 4 de la CREG 101 087; art. 28 de la 101 072",
           ignora_mayusculas=True),
    Vetada(r"C2[^.\n]{0,80}(?:numeral\s*2\s*literal\s*a|num\.\s*2\s*lit\.\s*a)",
           "C2 no es el art. 23 num. 2 lit. a (venta a comercializadores)",
           "C-163 y C-217: contrato interno, no escenario regulado",
           ignora_mayusculas=True),
    Vetada(r"importaci[oó]n acumulada hasta", "hx contra la importación acumulada (error de C-175)",
           "Anexo 4: hx contra la importación TOTAL del mes",
           ignora_mayusculas=True),
    Vetada(r"única frontera comercial", "el colectivo no tiene una única frontera (arts. 9, 10, 18)",
           "auditoría del objetivo 2, §3.3", ignora_mayusculas=True),
    # ── Compilación (F5) ───────────────────────────────────────────────────
    Vetada(r"\\,\\%", "rompe la compilación con babel en español "
           "(Incompatible glue units en \\es@sppercent)",
           "escribir \\% sin el espacio fino delante"),
    Vetada("[\x00-\x08\x0b\x0c\x0e-\x1f]", "carácter de control en el texto "
           "(p. ej. un \\v de \\varphi que un heredoc convirtió en tabulador)",
           "reescribir el comando con la herramienta de edición"),
    # ── Claves bibliográficas renombradas (F4) ─────────────────────────────
    Vetada(r"@BernalTorres2020Solar", "clave renombrada en references.bib",
           "@Castano2020Solar"),
    Vetada(r"@Tietjen2021Retail", "clave renombrada en references.bib",
           "@McRae2021Retail"),
    Vetada(r"@Colombia2022P2P", "clave renombrada en references.bib",
           "@Cardenas2022P2P (el experimento de elección discreta colombiano; "
           "no es de Peña-Bello)"),
]


def revisa(fichero: Path) -> list[tuple[int, Vetada, str]]:
    if not fichero.is_file():
        raise FileNotFoundError(f"no existe {fichero}")
    hallados = []
    compilados = [(v, re.compile(v.patron, re.IGNORECASE if v.ignora_mayusculas
                                 else 0)) for v in VETADAS]
    for n, linea in enumerate(fichero.read_text(encoding="utf-8").splitlines(), 1):
        if EXCEPCION.search(linea):
            continue
        for v, rx in compilados:
            m = rx.search(linea)
            if m:
                hallados.append((n, v, m.group(0)))
    return hallados


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ficheros = [Path(a) for a in argv] or [POR_DEFECTO]
    total = 0
    for f in ficheros:
        h = revisa(f)
        total += len(h)
        print(f"== {f}: {len(h)} coincidencias")
        por_motivo: dict[str, list] = {}
        for n, v, txt in h:
            por_motivo.setdefault(v.motivo, []).append((n, txt, v.fuente))
        for motivo, casos in sorted(por_motivo.items(), key=lambda x: -len(x[1])):
            lineas = ", ".join(str(n) for n, _, _ in casos[:12])
            mas = f" y {len(casos) - 12} más" if len(casos) > 12 else ""
            print(f"  [{len(casos):3d}] {motivo}\n        líneas {lineas}{mas}"
                  f"\n        sustituto: {casos[0][2]}")
    print("COMPUERTA DE VETADAS: " + ("LIMPIA" if total == 0 else
                                       f"{total} COINCIDENCIAS"))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
