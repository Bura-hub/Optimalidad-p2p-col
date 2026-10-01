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

Con `--ingles` (Tarea 2 del plan del artículo para IEEE Latin America
Transactions, 2026-09-29) aplica, en lugar de los patrones en español, la lista
`VETADAS_INGLES` (las mismas lecturas vetadas escritas en inglés) más las rutas
vetadas, a los ficheros dados (típicamente el `.tex` del artículo). Algunos
patrones son solo avisos: se imprimen, pero no cambian el código de salida. En
un `.tex` la excepción se marca con el comentario `% vetada-ok: <motivo>` en la
misma línea (también vale la forma HTML).

Con `--fichero` (Tarea 2 del plan de la versión de entrega de la tesis,
2026-09-29) aplica los patrones en español (`VETADAS_TEX_ES`: la lista española,
con el rango 35–89 también en su forma LaTeX, más las lecturas que veta la
inglesa) a los ficheros dados, típicamente el `.tex` en español, con las reglas
de `--ingles`: búsqueda sobre el texto entero (una frase partida por un salto de
línea se ve), avisos que no cambian el código de salida y la excepción
`% vetada-ok: <motivo>`. Sin opciones, el uso es el de siempre.

Uso:
    .venv/Scripts/python.exe reformateo/documento/scripts/compuerta_vetadas.py [fichero.md ...]
    .venv/Scripts/python.exe reformateo/documento/scripts/compuerta_vetadas.py --ingles fichero.tex [...]
    .venv/Scripts/python.exe reformateo/documento/scripts/compuerta_vetadas.py --fichero fichero.tex [...]
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
POR_DEFECTO = RAIZ / "Documentos" / "FinalTesisV2" / "tesis.md"
EXCEPCION = re.compile(r"<!--\s*vetada-ok:\s*[^>]+-->")
# En un .tex la excepción va en un comentario LaTeX (la forma HTML también vale).
EXCEPCION_TEX = re.compile(r"<!--\s*vetada-ok:\s*[^>]+-->|(?<!\\)%\s*vetada-ok:\s*\S")


@dataclass(frozen=True)
class Vetada:
    patron: str
    motivo: str
    fuente: str
    ignora_mayusculas: bool = False
    aviso: bool = False  # True: se informa, pero no cuenta como coincidencia


# Rutas vetadas (Global Constraints del plan del artículo y regla 1 del canon);
# las comparten la lista en español y la inglesa.
RUTAS_VETADAS = [
    Vetada(r"entrega_canonica|entrega_matriz_2026-09-15|matriz_reposo_2026-09-17",
           "entregas superadas (regla 1 del canon)",
           "SALIDAS_SERVIDOR/entrega_matriz_reposo_2026-09-19/"),
    Vetada(r"entrega_gsa_directo_2026-09-27(?!_)", "entrega del GSA superada",
           "entrega_gsa_directo_completo_2026-09-27 (CANON §13.8.5)"),
]

_MOTIVO_35_89 = ("«cobertura» de la validación que dice más de lo medido (C-225): "
                 "ningún régimen pasó el criterio de bloque")
_V35_89 = Vetada(r"35\s*(?:y el|al|a)\s*89|35\s*[–-]\s*89", _MOTIVO_35_89,
                 "CANON §9 y §14.5: regla declarada en todos los regímenes; 17 de 18 "
                 "horas integradas en la muestra de E0")

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
    _V35_89,
    Vetada(r"alcanzad[oa]s? por la dinámica", "rótulo retirado de la validación (C-225)",
           "CANON §14.5, partición por grupo de regímenes", ignora_mayusculas=True),
    # ── Rutas y objetos superados ──────────────────────────────────────────
    *RUTAS_VETADAS,
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
           "cita mal atribuida: el art. 26 de la 101 097 modifica el parágrafo 1 "
           "del art. 25 (tope de escasez sobre el MCm), no fija la bolsa horaria (C-224)",
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

# Las mismas lecturas vetadas, escritas en inglés (artículo IEEE LatAm; Tarea 2
# del plan 2026-09-29-articulo-latam), más las rutas vetadas.
VETADAS_INGLES = [
    Vetada(r"\b35(?:\s*\\?,?\s*\\?%)?\s*(?:–|—|--|-|to|and|\\textendash)\s*89\b",
           "«cobertura» de la validación que dice más de lo medido (C-225): "
           "ningún régimen pasó el criterio de bloque",
           "CANON §9 y §14.5: regla declarada en todos los regímenes; 17 de 18 "
           "horas integradas en la muestra de E0 («17 of 18 hours»)",
           ignora_mayusculas=True),
    Vetada(r"reached by the dynamics", "rótulo retirado de la validación (C-225)",
           "CANON §14.5, partición por grupo de regímenes", ignora_mayusculas=True),
    Vetada(r"verified regime", "ningún régimen se verificó con el criterio de "
           "bloque (C-225)", "CANON §9: regla declarada en todos los regímenes",
           ignora_mayusculas=True),
    Vetada(r"bootstrap", "retirado para cifras publicables (C-218)",
           "probabilidad de inversión del GSA, mes a mes, subperíodos",
           ignora_mayusculas=True),
    Vetada(r"\bM3\b", "segunda frontera retirada (D10, H-77)",
           "matriz de escalado sobre M1 (D10 a D12)"),
    Vetada(r"hourly C4", "colectivo horario retirado (D4, C-175)",
           "C4 mensual (arts. 19 a 21)", ignora_mayusculas=True),
    Vetada(r"C2\s*\$?\s*=\s*\$?\s*C3", "identidad del canon de agosto",
           "regla 5: el agregado de P2P y C2 coinciden (CAL-52)"),
    Vetada(r"Stackelberg equilibrium(?!\s+structure)",
           "el artículo conserva la estructura del juego de Stackelberg; "
           "«equilibrium» a secas puede decir más de lo que se calcula",
           "«Stackelberg equilibrium structure» o «Stackelberg game structure»",
           ignora_mayusculas=True, aviso=True),
    Vetada(r"exemption from (?:network )?charges",
           "lectura que requiere su salvedad (D-1, Fase E)",
           "revisar la redacción contra CANON.md", ignora_mayusculas=True,
           aviso=True),
    Vetada(r"Decree 3087", "decreto derogado (tarifas)",
           "Ley 142 de 1994, art. 89", ignora_mayusculas=True),
    *RUTAS_VETADAS,
]

# Los patrones en español aplicados a un `.tex` en español (versión de entrega
# de la tesis; Tarea 2 del plan 2026-09-29-tesis-entrega): toda la lista
# española, con el rango 35–89 en su forma LaTeX (`35\,\% y el 89`, `35--89`),
# más las lecturas que la lista inglesa veta y la española no tenía.
VETADAS_TEX_ES = [v for v in VETADAS if v is not _V35_89] + [
    Vetada(r"\b35(?:\s*\\?,?\s*\\?%)?\s*(?:y el|al|a|–|—|--|-|\\textendash)\s*89\b",
           _MOTIVO_35_89, _V35_89.fuente, ignora_mayusculas=True),
    Vetada(r"r[ée]gimen(?:es)? verificad[oa]s?", "ningún régimen se verificó con el "
           "criterio de bloque (C-225)", "CANON §9: regla declarada en todos los "
           "regímenes", ignora_mayusculas=True),
    Vetada(r"equilibrio de Stackelberg",
           "la tesis conserva la estructura del juego de Stackelberg; «equilibrio» "
           "a secas puede decir más de lo que se calcula (el reposo es de Nash)",
           "«estructura del juego de Stackelberg»", ignora_mayusculas=True,
           aviso=True),
    Vetada(r"exenci[óo]n de (?:los )?cargos", "lectura que requiere su salvedad "
           "(D-1, Fase E)", "revisar la redacción contra CANON.md",
           ignora_mayusculas=True, aviso=True),
    Vetada(r"Decreto 3087", "decreto derogado (tarifas)", "Ley 142 de 1994, art. 89",
           ignora_mayusculas=True),
]


def _espacios_flexibles(patron: str) -> str:
    """Cada espacio literal fuera de una clase `[...]` vale por cualquier blanco
    (saltos de línea incluidos); los de dentro de una clase no se tocan."""
    salida, en_clase, k = [], False, 0
    while k < len(patron):
        c = patron[k]
        if c == "\\":
            salida.append(patron[k:k + 2])
            k += 2
            continue
        if c == "[" and not en_clase:
            en_clase = True
        elif c == "]" and en_clase:
            en_clase = False
        salida.append(r"\s+" if c == " " and not en_clase else c)
        k += 1
    return "".join(salida)


def revisa(fichero: Path, patrones: list[Vetada] | None = None,
           excepcion: re.Pattern = EXCEPCION) -> list[tuple[int, Vetada, str]]:
    if not fichero.is_file():
        raise FileNotFoundError(f"no existe {fichero}")
    hallados = []
    compilados = [(v, re.compile(v.patron, re.IGNORECASE if v.ignora_mayusculas
                                 else 0))
                  for v in (VETADAS if patrones is None else patrones)]
    for n, linea in enumerate(fichero.read_text(encoding="utf-8").splitlines(), 1):
        if excepcion.search(linea):
            continue
        for v, rx in compilados:
            m = rx.search(linea)
            if m:
                hallados.append((n, v, m.group(0)))
    return hallados


def _revisa_texto_entero(fichero: Path, patrones: list[Vetada]
                         ) -> list[tuple[int, Vetada, str]]:
    """Patrones sobre el texto entero; excepción `% vetada-ok:` o HTML.

    En un `.tex` una frase se corta con el salto de línea («reached by the» /
    «dynamics»), así que se busca sobre el texto entero: cada espacio literal
    del patrón vale por cualquier blanco, saltos incluidos, y la coincidencia se
    atribuye a su línea de inicio. Las líneas exceptuadas se blanquean antes
    (conservan su longitud), de modo que no aportan ni cierran coincidencias."""
    if not fichero.is_file():
        raise FileNotFoundError(f"no existe {fichero}")
    lineas = fichero.read_text(encoding="utf-8").split("\n")
    texto = "\n".join(" " * len(l) if EXCEPCION_TEX.search(l) else l for l in lineas)
    hallados = []
    for v in patrones:
        rx = re.compile(_espacios_flexibles(v.patron),
                        re.IGNORECASE if v.ignora_mayusculas else 0)
        for m in rx.finditer(texto):
            hallados.append((texto.count("\n", 0, m.start()) + 1, v,
                             " ".join(m.group(0).split())))
    hallados.sort(key=lambda x: x[0])
    return hallados


def revisa_ingles(fichero: Path) -> list[tuple[int, Vetada, str]]:
    """Patrones en inglés y rutas vetadas (artículo IEEE LatAm)."""
    return _revisa_texto_entero(fichero, VETADAS_INGLES)


def revisa_tex_es(fichero: Path) -> list[tuple[int, Vetada, str]]:
    """Patrones en español (`VETADAS_TEX_ES`) sobre un `.tex` en español, con
    las mismas reglas que `revisa_ingles`: excepción `% vetada-ok:` (o HTML) y
    frases partidas por el salto de línea."""
    return _revisa_texto_entero(fichero, VETADAS_TEX_ES)


def main_ingles(ficheros: list[Path]) -> int:
    return _main_texto_entero(ficheros, revisa_ingles, "inglés")


def main_fichero(ficheros: list[Path]) -> int:
    return _main_texto_entero(ficheros, revisa_tex_es, "español, fichero")


def _main_texto_entero(ficheros: list[Path], revisor, rotulo_modo: str) -> int:
    total = avisos = 0
    for f in ficheros:
        h = revisor(f)
        duros = [x for x in h if not x[1].aviso]
        blandos = [x for x in h if x[1].aviso]
        total += len(duros)
        avisos += len(blandos)
        print(f"== {f}: {len(duros)} coincidencias, {len(blandos)} avisos")
        for rotulo, grupo in (("", duros), ("AVISO ", blandos)):
            for n, v, txt in grupo:
                print(f"  {rotulo}línea {n}: «{txt}» — {v.motivo}"
                      f"\n        sustituto: {v.fuente}")
    print(f"COMPUERTA DE VETADAS ({rotulo_modo}): "
          + ("LIMPIA" if total == 0 else f"{total} COINCIDENCIAS")
          + (f" ({avisos} avisos)" if avisos else ""))
    return 0 if total == 0 else 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("--ingles", "--fichero"):
        if len(argv) < 2:
            print(f"uso: compuerta_vetadas.py {argv[0]} fichero [...]", file=sys.stderr)
            return 2
        modo = main_ingles if argv[0] == "--ingles" else main_fichero
        return modo([Path(a) for a in argv[1:]])
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # cp1252 no tiene «−» (CAL-28b)
    sys.exit(main())
