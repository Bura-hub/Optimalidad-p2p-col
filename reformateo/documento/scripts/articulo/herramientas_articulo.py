"""
herramientas_articulo.py — Controles del manuscrito del artículo para IEEE Latin
America Transactions (canon 2026-09).
===============================================================================
Tarea 2 del plan `docs/superpowers/plans/2026-09-29-articulo-latam.md`. No
simula ni escribe nada: lee el `.tex`, la tabla de cifras, las fuentes previas
o el `.bib` y dice qué falla. Cuatro subórdenes, cada una sale con código 1 si
encuentra un fallo (y con 2 si el uso es incorrecto):

``cifras <tex> <cifras.csv>``
    Extrae los números de la prosa (sin preámbulo, comentarios `%`, entornos
    matemáticos de presentación, `\\cite`, `\\ref`, `\\label`, opciones de
    maquetación ni la bibliografía), normaliza el menos (`-`, `$-$`,
    `\\textminus`, `−`, `--`), el porcentaje (`\\%`, `\\,\\%`, `~\\%`) y la coma de
    millares (`,` o `{,}`), y marca como huérfano todo número que no esté en la
    columna `texto_en` de `SALIDAS_SERVIDOR/cifras_articulo_2026-09-29/cifras.csv`
    ni en la lista blanca `LISTA_BLANCA`. Reglas de la coincidencia:

    * el redondeo cuenta: `46.5` no es `46.50`, y un número escrito con coma
      decimal española (`0,542`) nunca coincide;
    * un número con `%` en el `.tex` tiene que estar en la tabla con `%`; uno
      sin `%` vale contra cualquier forma de la tabla (el primer extremo de un
      rango, `1.1--20.5\\,\\%`, no lleva el signo);
    * un número con signo menos tiene que estar en la tabla con signo menos;
      uno sin signo vale también contra el valor absoluto de uno negativo (la
      prosa dice «C4 exceeds C1 by 0.96» sin signo);
    * un `texto_en` compuesto aporta cada número que contiene («17 of 18»
      aporta 17 y 18).

    Una línea que lleve el comentario `% cifra-ok: <motivo>` se acepta entera.

``cifras-es <tex> <fuente> [<fuente> ...]``
    La versión en español (Tarea 2 del plan
    `docs/superpowers/plans/2026-09-29-tesis-entrega.md`), para el documento de
    entrega de la tesis. Extrae los números de la prosa con la misma limpieza
    que `cifras` y los normaliza al formato español: coma decimal (`,` o
    `{,}`); millares con espacio, espacio duro o fino, `\\,`, `~` o punto; menos
    como `-`, `$-$`, `\\textminus`, `−` o `--`; porcentaje `\\%`, `\\,\\%` o
    `~\\%`. Las fuentes son:

    * un `.md` u otro texto (`tesis.md`, `CANON.md`), leído en formato español
      (un número ambiguo como «6.144» o «6,144» aporta sus dos lecturas);
    * un `.csv` con la columna `texto_en` (redondeado, formato inglés) y/o la
      columna `valor` (punto decimal, a menudo sin redondear: el número del
      `.tex` vale si el valor, redondeado a sus mismos decimales, da el mismo
      número; con `unidad` = «fracción» vale también ×100 como porcentaje).

    Las reglas de coincidencia son las de `cifras` (el redondeo cuenta; con `%`
    exige fuente con `%`; con signo exige fuente con signo), y el separador de
    millares no cuenta (`6\\,144` = `6 144` = `6144` = `6.144`). Un punto
    decimal en la prosa (`0.542`) es huérfano siempre. La lista blanca es la de
    `cifras` más «art.», «artículo», «Resolución», «Ley», «Decreto», «CREG»,
    «numeral», «literal» (y «parágrafo», «Acuerdo») con sus secuencias, y las
    fechas en español; la marca `% cifra-ok:` vale igual.

``similitud <tex> <fuente> [<fuente> ...]``
    8-gramas de palabras en minúscula, sin puntuación, sin comandos LaTeX y sin
    la bibliografía. Da el porcentaje de 8-gramas distintos del manuscrito que
    están en cada fuente y en su unión. Falla si la unión pasa del 15 % o si
    una fuente pasa del 8 %. Una fuente puede llevar un rango de líneas,
    `fichero:22-29` (p. ej. el resumen inglés de `tesis.md`).

``dois <bib>``
    Para cada entrada con `doi` consulta `https://api.crossref.org/works/<doi>`
    y compara el título normalizado con el del `.bib` (Jaccard de palabras
    ≥ 0,8). Lista las entradas sin `doi` y sin `url`, que son fallo, salvo
    las `@mastersthesis` y `@phdthesis`, que se listan como «tesis sin DOI
    (permitido)», los `@book` con `isbn`, que se listan como «libro con
    ISBN (permitido)», los `@unpublished`, que se listan como «manuscrito
    (permitido)», y los `@techreport` y `@misc` cuya `note` los declara
    internos («fuente interna», «documento interno»), que se listan como
    «fuente interna (permitido)». Un error
    de red o un DOI que Crossref no conoce es fallo, no se traga.

Uso:
    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/herramientas_articulo.py cifras <tex> <cifras.csv>
    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/herramientas_articulo.py cifras-es <tex> <fuente>...
    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/herramientas_articulo.py similitud <tex> <fuente>...
    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/herramientas_articulo.py dois <bib>

Actividades 3.3 y 4.2.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from decimal import (ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation,
                     localcontext)
from pathlib import Path

# ── Parámetros ───────────────────────────────────────────────────────────────
UMBRAL_UNION = 15.0      # % de 8-gramas del manuscrito presentes en la unión
UMBRAL_FUENTE = 8.0      # % en una sola fuente
N_GRAMA = 8
UMBRAL_JACCARD = 0.8
# Tipos del .bib que pueden ir sin DOI ni URL sin que `dois` falle.
TIPOS_TESIS = ("mastersthesis", "phdthesis")
# Tipos que pueden ir sin DOI ni URL si llevan `isbn`.
TIPOS_LIBRO = ("book",)
# Manuscritos sin publicar: no tienen DOI ni URL pública (p. ej. el documento
# extenso del modelo base, que la ética del reglamento obliga a citar).
TIPOS_MANUSCRITO = ("unpublished",)
# Informes y datos sin URL pública: pasan si su `note` los declara «fuente
# interna» (o «documento interno»), es decir, si la nota dice que son internos.
TIPOS_FUENTE_INTERNA = ("techreport", "misc")
PATRON_INTERNA = re.compile(r"\bintern[oa]s?\b", re.IGNORECASE)
AGENTE = "SistemaBL-articulo/1.0"
PLAZO_RED_S = 20
CROSSREF = "https://api.crossref.org/works/"

# Lista blanca del chequeo de cifras: lo que no es una cifra del canon.
LISTA_BLANCA = {
    "anios": (2000, 2030),        # años sueltos, sin signo, decimal ni %
    "conteos": (1, 13),           # conteos de 1 a 13 (13 casos, 5 instituciones)
    # Números de artículo, resolución, ley, decreto o proyecto precedidos de su
    # palabra clave, con las secuencias («Arts. 19--21», «CREG 101 072»).
    "claves": r"\bArts?\.|\bArticles?\b|\bResolutions?\b|\bLaws?\b|\bCREG\b"
              r"|\bDecrees?\b|\bBPIN\b",
    # Fechas y horas del reloj: «September 29, 2026», «2025-07-30», «07:00».
    "fechas": r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?"
              r"|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?"
              r"|Dec(?:ember)?)\.?[\s~]+\d{1,2}(?:st|nd|rd|th)?\b(?:,?[\s~]+\d{4})?"
              r"|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b",
}

# ── Limpieza del .tex ───────────────────────────────────────────────────────
# Comandos cuyo contenido no es prosa: nombre -> argumentos obligatorios.
COMANDOS_FUERA = {
    "cite": 1, "citep": 1, "citet": 1, "citeauthor": 1, "nocite": 1,
    "ref": 1, "eqref": 1, "autoref": 1, "cref": 1, "Cref": 1, "pageref": 1,
    "label": 1, "url": 1, "href": 1, "includegraphics": 1, "input": 1,
    "include": 1, "bibliography": 1, "bibliographystyle": 1, "orcidlink": 1,
    "autororcid": 1,     # envoltorio del ORCID en la línea de autores (I-4)
    "vspace": 1, "hspace": 1, "setlength": 2, "addtolength": 2, "setcounter": 2,
    "addtocounter": 2, "resizebox": 2, "scalebox": 1, "rule": 2, "fontsize": 2,
    "linespread": 1, "renewcommand": 2, "newcommand": 2, "providecommand": 2,
    "graphicspath": 1, "hyphenation": 1, "multicolumn": 1, "multirow": 1,
    "cline": 1, "cmidrule": 1,
}
ENTORNOS_FUERA = (r"thebibliography|equation|align|gather|multline|eqnarray"
                  r"|flalign|alignat|displaymath|IEEEeqnarray")
# Especificación de columnas de las tablas: entorno -> argumentos a blanquear.
ENTORNOS_TABLA = {"tabular": 1, "tabular*": 2, "tabularx": 2, "array": 1,
                  "longtable": 1}


def _blanco(s: str) -> str:
    """Sustituye todo carácter por un espacio y conserva los saltos de línea,
    de modo que posiciones y números de línea no cambian."""
    return re.sub(r"[^\n]", " ", s)


def _fin_grupo(t: str, i: int, abre: str = "{", cierra: str = "}") -> int:
    """`t[i] == abre`; índice justo después de su cierre balanceado (o -1)."""
    prof = 0
    k = i
    while k < len(t):
        c = t[k]
        if c == "\\":
            k += 2
            continue
        if c == abre:
            prof += 1
        elif c == cierra:
            prof -= 1
            if prof == 0:
                return k + 1
        k += 1
    return -1


def _salta_espacio(t: str, k: int) -> int:
    while k < len(t) and t[k] in " \t\n":
        k += 1
    return k


def _fin_argumentos(t: str, k: int, n_llaves: int, parentesis: bool = False) -> int:
    """Desde `k`, salta opciones `[...]` (y `(...)` si se pide) y `n_llaves`
    grupos `{...}`; devuelve el final."""
    while True:
        j = _salta_espacio(t, k)
        if j < len(t) and t[j] == "[":
            f = _fin_grupo(t, j, "[", "]")
        elif parentesis and j < len(t) and t[j] == "(":
            f = _fin_grupo(t, j, "(", ")")
        else:
            break
        if f < 0:
            break
        k = f
    for _ in range(n_llaves):
        j = _salta_espacio(t, k)
        if j >= len(t) or t[j] != "{":
            break
        f = _fin_grupo(t, j)
        if f < 0:
            break
        k = f
    return k


def _blanquea_tramos(t: str, tramos: list[tuple[int, int]]) -> str:
    buf = list(t)
    for a, b in tramos:
        for k in range(a, b):
            if buf[k] != "\n":
                buf[k] = " "
    return "".join(buf)


def _quita_comentarios(t: str) -> str:
    return re.sub(r"(?<!\\)%[^\n]*", lambda m: _blanco(m.group(0)), t)


def _solo_cuerpo(t: str) -> str:
    """Blanquea el preámbulo y lo que sigue a `\\end{document}`, si existen."""
    m = re.search(r"\\begin\{document\}", t)
    if m:
        t = _blanco(t[:m.end()]) + t[m.end():]
    m = re.search(r"\\end\{document\}", t)
    if m:
        t = t[:m.start()] + _blanco(t[m.start():])
    return t


def limpia_tex(t: str) -> str:
    """Deja solo la prosa del cuerpo (y las tablas), con posiciones intactas."""
    t = _quita_comentarios(t)
    t = _solo_cuerpo(t)
    # Entornos matemáticos de presentación y bibliografía.
    t = re.sub(r"\\begin\{(" + ENTORNOS_FUERA + r")(\*?)\}.*?\\end\{\1\2\}",
               lambda m: _blanco(m.group(0)), t, flags=re.S)
    t = re.sub(r"\\\[.*?\\\]|\$\$.*?\$\$", lambda m: _blanco(m.group(0)), t, flags=re.S)
    tramos = []
    # Comandos que no son prosa, con sus argumentos.
    for m in re.finditer(r"\\(" + "|".join(sorted(COMANDOS_FUERA, key=len, reverse=True))
                         + r")(?![A-Za-z@])\*?", t):
        fin = _fin_argumentos(t, m.end(), COMANDOS_FUERA[m.group(1)],
                              parentesis=m.group(1) == "cmidrule")
        tramos.append((m.start(), fin))
    # Opciones y especificación de columnas de los entornos.
    for m in re.finditer(r"\\begin\{([A-Za-z*]+)\}", t):
        fin = _fin_argumentos(t, m.end(), ENTORNOS_TABLA.get(m.group(1), 0))
        tramos.append((m.end(), fin))
    # Opciones de cualquier otro comando (`\\[2pt]`, `\item[a)]`).
    for m in re.finditer(r"(?:\\[A-Za-z@]+\*?|\\\\)(?=\s*\[)", t):
        tramos.append((m.end(), _fin_argumentos(t, m.end(), 0)))
    # Índices y exponentes (`C_{4}`, `x_t`, `10^{-6}`).
    for m in re.finditer(r"[_^](?:\{[^{}\n]*\}|\\?[A-Za-z0-9])", t):
        tramos.append((m.start(), m.end()))
    # Medidas de maquetación (`3.5in`, `0.95\columnwidth`).
    for m in re.finditer(r"-?\d*\.?\d+(?:pt|in|cm|mm|em|ex|bp|sp|pc)\b"
                         r"|-?\d*\.?\d+\s*\\(?:columnwidth|linewidth|textwidth|hsize"
                         r"|textheight|baselineskip)", t):
        tramos.append((m.start(), m.end()))
    return _blanquea_tramos(t, tramos)


# ── Números ─────────────────────────────────────────────────────────────────
NUMERO = re.compile(r"""
    (?<![\w.])
    (?P<num>
        \d{1,3}(?:\\,\d{3})+(?!\d)(?:\.\d+)?           # millares con \, (nunca coincide)
      | \d{1,3}(?:(?:,|\{,\})\d{3})+(?!\d)(?:\.\d+)?   # millares con coma
      | \d+(?:,|\{,\})\d+                              # coma decimal española
      | \d+(?:\.\d+)?
    )
    (?P<pct>\$?[ \t]*(?:\\,|~|\\[ ]|\\thinspace[ \t]*)?[ \t]*\\?%)?
""", re.X)
MILLARES_VALIDOS = re.compile(r"[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?")
SIGNOS = ("--", "−", "–", "-")


def _canoniza_menos(t: str) -> str:
    t = re.sub(r"\$[ \t]*--?[ \t]*\$", "−", t)
    return re.sub(r"\\textminus(?:\{\})?[ \t]*", "−", t)


@dataclass(frozen=True)
class Numero:
    inicio: int
    texto: str        # tal como aparece (tras canonizar el menos)
    signo: str        # "-" o ""
    num: str          # sin coma de millares; con coma si es formato español
    pct: bool

    @property
    def forma(self) -> str:
        return f"{self.signo}{self.num}{' %' if self.pct else ''}"


def extrae_numeros(t: str) -> list[Numero]:
    """Números de un texto ya limpio (o de un `texto_en`)."""
    salida = []
    for m in NUMERO.finditer(t):
        crudo = m.group("num").replace("{,}", ",")
        if "," in crudo and MILLARES_VALIDOS.fullmatch(crudo):
            num = crudo.replace(",", "")
        else:
            num = crudo           # sin comas, o con coma decimal (nunca coincide)
        signo, ini = "", m.start()
        for s in SIGNOS:
            if t[max(0, ini - len(s)):ini] == s:
                antes = t[ini - len(s) - 1] if ini - len(s) - 1 >= 0 else ""
                if not (antes and (antes.isalnum() or antes in "._)}]")):
                    signo, ini = "-", ini - len(s)
                break
        salida.append(Numero(ini, t[ini:m.end()].strip(), signo, num,
                             m.group("pct") is not None))
    return salida


def _tramos_blancos(t: str) -> list[tuple[int, int]]:
    """Tramos de la lista blanca por posición: claves normativas y fechas."""
    # «101 072», «101~072», «101\,072»; listas y rangos; «of 1994» o «/2025».
    grupo = r"\d+(?:(?:[ ~]|\\,)\d{3})*"
    secuencia = (grupo + r"(?:[\s~]*(?:,|and|to|y|--|–|-|&)[\s~]*" + grupo + r")*"
                 r"(?:[\s~]+of[\s~]+\d{4}|/\d{4})?")
    tramos = [(m.start(), m.end()) for m in re.finditer(
        r"(?:" + LISTA_BLANCA["claves"] + r")[\s~]*(?:No\.[\s~]*)?" + secuencia,
        t, flags=re.I)]
    tramos += [(m.start(), m.end()) for m in re.finditer(LISTA_BLANCA["fechas"], t)]
    return tramos


def _en_lista_blanca(n: Numero, tramos: list[tuple[int, int]]) -> bool:
    if any(a <= n.inicio < b for a, b in tramos):
        return True
    if n.signo or n.pct or not n.num.isdigit():
        return False
    v = int(n.num)
    a0, a1 = LISTA_BLANCA["anios"]
    c0, c1 = LISTA_BLANCA["conteos"]
    return a0 <= v <= a1 or c0 <= v <= c1


@dataclass(frozen=True)
class Huerfano:
    linea: int
    texto: str
    forma: str


def lee_tabla(cifras_csv: Path) -> list[str]:
    with open(cifras_csv, encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        if not lector.fieldnames or "texto_en" not in lector.fieldnames:
            raise ValueError(f"{cifras_csv} no tiene la columna texto_en")
        textos = [fila["texto_en"] for fila in lector]
    if not textos:
        raise ValueError(f"{cifras_csv} está vacío")
    return textos


def chequeo_cifras_tex(tex: Path, cifras_csv: Path) -> list[Huerfano]:
    """Números de la prosa de `tex` que no están en `texto_en` ni en la lista
    blanca, en orden de aparición."""
    todos, con_pct = set(), set()
    for texto in lee_tabla(cifras_csv):
        for n in extrae_numeros(texto):
            todos.add((n.signo, n.num))
            if n.pct:
                con_pct.add((n.signo, n.num))
    abs_todos = {num for _, num in todos}
    abs_pct = {num for _, num in con_pct}

    original = tex.read_text(encoding="utf-8")
    exentas = {i for i, linea in enumerate(original.splitlines(), 1)
               if re.search(r"(?<!\\)%.*cifra-ok:\s*\S", linea)}
    t = _canoniza_menos(limpia_tex(original))
    tramos = _tramos_blancos(t)
    huerfanos = []
    for n in extrae_numeros(t):
        linea = t.count("\n", 0, n.inicio) + 1
        if linea in exentas or _en_lista_blanca(n, tramos):
            continue
        clave = (n.signo, n.num)
        if n.pct:
            ok = clave in con_pct or (not n.signo and n.num in abs_pct)
        else:
            ok = clave in todos or (not n.signo and n.num in abs_todos)
        if not ok:
            huerfanos.append(Huerfano(linea, n.texto, n.forma))
    return huerfanos


def _orden_cifras(a) -> int:
    tex, tabla = Path(a.tex), Path(a.cifras)
    h = chequeo_cifras_tex(tex, tabla)
    print(f"== {tex} contra {tabla}")
    for x in h:
        print(f"  línea {x.linea}: «{x.texto}» (forma {x.forma})")
    print("CHEQUEO DE CIFRAS: " + ("LIMPIO" if not h else f"{len(h)} HUÉRFANOS"))
    return 1 if h else 0


# ── Cifras en español (versión de entrega de la tesis) ──────────────────────
# Tarea 2 del plan `docs/superpowers/plans/2026-09-29-tesis-entrega.md`.
# Separadores de miles admitidos en español: espacio (normal, duro o fino),
# `\,`, `{\,}`, `\thinspace`, `\ `, `~` y punto. La coma (o `{,}`) es decimal.
_SEP_MILES = (r"(?:\\,|\{\\,\}|\\thinspace[ \t]*|\\[ ]|~|\.|[    ])")
_DEC = r"(?:,|\{,\})"
NUMERO_ES = re.compile(
    r"(?<![\w.,])"
    r"(?P<num>"
    r"[1-9]\d{0,2}(?:" + _SEP_MILES + r"\d{3})+(?!\d)(?:" + _DEC + r"\d+)?"
    r"|\d+(?:" + _DEC + r"\d+)?(?P<punto>\.\d+)?"
    r")"
    r"(?P<pct>\$?[ \t~   ]*(?:\\,|\{\\,\}|\\[ ]|\\thinspace[ \t]*)?"
    r"[ \t~   ]*\\?%)?")
_MILES_ES = re.compile(r"[1-9]\d{0,2}(?:" + _SEP_MILES + r"\d{3})+(?:" + _DEC + r"\d+)?")
_MILES_COMA = re.compile(r"[1-9]\d{0,2}(?:,\d{3})+")        # «6,144» inglés en una fuente
SIGNOS_ES = ("--", "−", "–", "-")

# Lista blanca en español: la de `cifras` más las claves normativas españolas,
# las fechas en español y los mismos años y conteos.
CLAVES_ES = (r"\barts?\.|\bart[íi]culos?\b|\bresoluci[óo]n(?:es)?\b|\bley(?:es)?\b"
             r"|\bdecretos?\b|\bCREG\b|\bnumerales?\b|\bnum\.|\bliterales?\b|\blit\."
             r"|\bpar[áa]grafos?\b|\bacuerdos?\b"
             # Referencias internas y de la propuesta: «actividad 1.1», «sección
             # 6.2», «Tabla 7.3»; no son cifras (y admiten el punto).
             r"|\bactividad(?:es)?\b|\bsecci[óo]n(?:es)?\b|\bsubsecci[óo]n(?:es)?\b"
             r"|\btablas?\b|\bfiguras?\b|\bfigs?\.|\bcap[íi]tulos?\b|\banexos?\b"
             r"|\bapartados?\b|\becuaci[óo]n(?:es)?\b|§")
FECHAS_ES = (r"\b\d{1,2}(?:[\s~]+de)?[\s~]+(?:enero|febrero|marzo|abril|mayo|junio"
             r"|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b"
             r"(?:[\s~]+del?[\s~]+\d{4})?")


@dataclass(frozen=True)
class NumeroEs:
    inicio: int
    texto: str        # tal como aparece (tras canonizar el menos)
    signo: str        # "-" o ""
    entero: str       # sin separadores ni ceros a la izquierda
    decimales: str    # "" si no hay parte decimal; su longitud es el redondeo
    pct: bool
    punto: bool = False   # punto decimal (formato inglés) en la prosa española

    @property
    def clave(self) -> tuple[str, str, str]:
        return (self.signo, self.entero, self.decimales)

    @property
    def forma(self) -> str:
        dec = f",{self.decimales}" if self.decimales else ""
        return f"{self.signo}{self.entero}{dec}{' %' if self.pct else ''}"


def _clave(signo: str, entero: str, decimales: str) -> tuple[str, str, str]:
    return (signo, entero.lstrip("0") or "0", decimales)


def _signo_delante(t: str, ini: int) -> tuple[str, int]:
    """Signo menos delante de `t[ini]` (no el guion de «H-51» ni el de «19--21»)."""
    for s in SIGNOS_ES:
        if t[max(0, ini - len(s)):ini] == s:
            antes = t[ini - len(s) - 1] if ini - len(s) - 1 >= 0 else ""
            if not (antes and (antes.isalnum() or antes in "._)}]")):
                return "-", ini - len(s)
            break
    return "", ini


def extrae_numeros_es(t: str, fuente: bool = False) -> list[NumeroEs]:
    """Números de un texto en formato español (un `.tex` limpio o un `.md`).

    Con `fuente=True` un número ambiguo aporta sus dos lecturas: «6.144» vale
    6144 y 6,144, y «6,144» (un pasaje en inglés de `tesis.md`) vale 6,144 y
    6144; un punto decimal («1.1») se lee como decimal. En el `.tex` (sin
    `fuente`) el punto seguido de grupos de tres cifras es de millares y
    cualquier otro punto decimal se marca con `punto=True`."""
    salida = []
    for m in NUMERO_ES.finditer(t):
        crudo = m.group("num")
        signo, ini = _signo_delante(t, m.start())
        pct = m.group("pct") is not None
        texto = t[ini:m.end()].strip()
        lecturas: list[tuple[str, str, bool]] = []    # (entero, decimales, punto)
        if _MILES_ES.fullmatch(crudo) and m.group("punto") is None:
            # La coma decimal no es la de `\,` ni la de `{\,}`.
            md = re.search(r"(?<!\\)(?:,|\{,\})(\d+)$", crudo)
            dec = md.group(1) if md else ""
            ent = crudo[:md.start()] if md else crudo
            lecturas.append((re.sub(r"\D", "", ent), dec, False))
            if fuente and not dec and re.fullmatch(r"\d{1,3}\.\d{3}", ent):
                a, _, b = ent.partition(".")
                lecturas.append((a, b, False))             # «6.144» como 6,144
        else:
            base = crudo.replace("{,}", ",")
            punto = m.group("punto")
            if punto is not None:
                base = base[:len(base) - len(punto)]
            ent, _, dec = base.partition(",")
            if punto is not None and not dec:
                lecturas.append((ent, punto[1:], not fuente))
            else:
                lecturas.append((ent, dec, False))
            if fuente and _MILES_COMA.fullmatch(base):
                lecturas.append((base.replace(",", ""), "", False))
        for ent, dec, pto in lecturas:
            e, d = _clave(signo, ent, dec)[1:]
            salida.append(NumeroEs(ini, texto, signo, e, d, pct, pto))
    return salida


def _clave_de_decimal(v) -> tuple[str, str, str]:
    signo = "-" if v < 0 else ""
    ent, _, dec = f"{abs(v):f}".partition(".")
    return _clave(signo, ent, dec)


@dataclass
class FuentesEs:
    """Números de las fuentes verificadas, normalizados al formato español."""
    exactos: set = field(default_factory=set)       # claves (signo, entero, dec)
    exactos_pct: set = field(default_factory=set)
    crudos: list = field(default_factory=list)      # (Decimal, pct) de `valor`
    por_fuente: dict = field(default_factory=dict)  # fuente -> números leídos
    _redondeos: dict = field(default_factory=dict)

    def agrega(self, clave: tuple[str, str, str], pct: bool) -> None:
        self.exactos.add(clave)
        if pct:
            self.exactos_pct.add(clave)

    def redondeados(self, d: int) -> tuple[set, set]:
        """Claves de los valores crudos redondeados a `d` decimales (mitad al
        par y mitad hacia arriba: un empate vale con las dos reglas)."""
        if d not in self._redondeos:
            q = Decimal(1).scaleb(-d)
            todos, con_pct = set(), set()
            with localcontext() as ctx:
                ctx.prec = 100
                for v, pct in self.crudos:
                    for regla in (ROUND_HALF_EVEN, ROUND_HALF_UP):
                        k = _clave_de_decimal(v.quantize(q, rounding=regla))
                        todos.add(k)
                        if pct:
                            con_pct.add(k)
            self._redondeos[d] = (todos, con_pct)
        return self._redondeos[d]

    def presente(self, n: NumeroEs) -> bool:
        # Sin signo vale también contra el valor absoluto de uno negativo («C4
        # supera a C1 en 0,96»); con signo tiene que estar con signo.
        claves = [n.clave] if n.signo else [n.clave, ("-", n.entero, n.decimales)]
        todos_r, pct_r = self.redondeados(len(n.decimales))
        conjuntos = (self.exactos_pct, pct_r) if n.pct else (self.exactos, todos_r)
        return any(k in c for k in claves for c in conjuntos)


def _lee_csv_es(ruta: Path, f: FuentesEs) -> int:
    with open(ruta, encoding="utf-8", newline="") as fh:
        lector = csv.DictReader(fh)
        campos = lector.fieldnames or []
        if "valor" not in campos and "texto_en" not in campos:
            raise ValueError(f"{ruta} no tiene la columna valor ni texto_en")
        filas = list(lector)
    if not filas:
        raise ValueError(f"{ruta} está vacío")
    cuenta = 0
    for fila in filas:
        for n in extrae_numeros(fila.get("texto_en") or ""):
            ent, _, dec = n.num.replace(",", ".").partition(".")
            f.agrega(_clave(n.signo, ent, dec), n.pct)
            cuenta += 1
        valor = (fila.get("valor") or "").strip()
        if not valor:
            continue
        unidad = (fila.get("unidad") or "").strip().lower()
        try:
            v = Decimal(valor)
        except InvalidOperation:
            v = None
        if v is not None and v.is_finite():
            pct = "%" in unidad
            f.crudos.append((v, pct))
            f.agrega(_clave_de_decimal(v), pct)
            if unidad == "fracción":                    # 0,1810 se cita como 18,1 %
                f.crudos.append((v * 100, True))
            cuenta += 1
        else:
            # Valor compuesto («f_cv 0.976 (±0.044)», «UCC -201522; ...»): sus
            # números, ya redondeados, en formato inglés.
            for n in extrae_numeros(valor):
                ent, _, dec = n.num.replace(",", ".").partition(".")
                f.agrega(_clave(n.signo, ent, dec), n.pct or "%" in unidad)
                cuenta += 1
    return cuenta


def lee_fuentes_es(fuentes: list) -> FuentesEs:
    """`.csv`: columnas `valor` (punto decimal; crudo, se compara redondeado) y
    `texto_en` (ya redondeado). Cualquier otro fichero (`tesis.md`, `CANON.md`)
    se lee como texto en formato español."""
    f = FuentesEs()
    if not fuentes:
        raise ValueError("hace falta al menos una fuente")
    for espec in fuentes:
        ruta = Path(espec)
        if not ruta.is_file():
            raise FileNotFoundError(f"no existe {ruta}")
        if ruta.suffix.lower() == ".csv":
            cuenta = _lee_csv_es(ruta, f)
        else:
            t = _canoniza_menos(ruta.read_text(encoding="utf-8"))
            nums = extrae_numeros_es(t, fuente=True)
            for n in nums:
                f.agrega(n.clave, n.pct)
            cuenta = len(nums)
        if cuenta == 0:
            raise ValueError(f"{ruta} no aporta ningún número")
        f.por_fuente[str(ruta)] = cuenta
    return f


def _tramos_blancos_es(t: str) -> list[tuple[int, int]]:
    """Claves normativas (inglesas y españolas) con sus secuencias, y fechas."""
    # «101 072», «101~072», «101\,072», o numeración con punto («3.7.2»).
    grupo = (r"(?:\d+(?:\.\d+)+|\d+(?:(?:[ ~  ]|\\,)\d{3})*)"
             r"(?!\d|(?:,|\{,\})\d)")
    enlace = r"(?:,|y|e|o|a|al|and|to|--|–|-|&)"
    secuencia = (grupo + r"(?:[\s~]*" + enlace + r"[\s~]*" + grupo + r")*"
                 r"(?:[\s~]+(?:of|de)[\s~]+\d{4}|/\d{4})?")
    claves = LISTA_BLANCA["claves"] + "|" + CLAVES_ES
    tramos = [(m.start(), m.end()) for m in re.finditer(
        r"(?:" + claves + r")[\s~]*(?:No\.[\s~]*|N\.[ºo][\s~]*)?" + secuencia,
        t, flags=re.I)]
    # Los meses ingleses sin re.I («mar», «may» son palabras españolas).
    tramos += [(m.start(), m.end()) for m in re.finditer(LISTA_BLANCA["fechas"], t)]
    tramos += [(m.start(), m.end()) for m in re.finditer(FECHAS_ES, t, flags=re.I)]
    return tramos


def _en_lista_blanca_es(n: NumeroEs, tramos: list[tuple[int, int]]) -> bool:
    if any(a <= n.inicio < b for a, b in tramos):
        return True
    if n.signo or n.pct or n.decimales or n.punto:
        return False
    v = int(n.entero)
    a0, a1 = LISTA_BLANCA["anios"]
    c0, c1 = LISTA_BLANCA["conteos"]
    return a0 <= v <= a1 or c0 <= v <= c1


def chequeo_cifras_es(tex: Path, fuentes: list) -> list[Huerfano]:
    """Números de la prosa de `tex` (en español) que no están, con su mismo
    redondeo, en ninguna fuente ni en la lista blanca, en orden de aparición.
    Un punto decimal en la prosa es huérfano siempre (formato inglés)."""
    return _chequeo_cifras_es(tex, lee_fuentes_es(fuentes))


def _chequeo_cifras_es(tex: Path, f: FuentesEs) -> list[Huerfano]:
    original = tex.read_text(encoding="utf-8")
    exentas = {i for i, linea in enumerate(original.splitlines(), 1)
               if re.search(r"(?<!\\)%.*cifra-ok:\s*\S", linea)}
    t = _canoniza_menos(limpia_tex(original))
    tramos = _tramos_blancos_es(t)
    huerfanos = []
    for n in extrae_numeros_es(t):
        linea = t.count("\n", 0, n.inicio) + 1
        if linea in exentas or _en_lista_blanca_es(n, tramos):
            continue
        if n.punto:
            huerfanos.append(Huerfano(linea, n.texto, "punto decimal: se escribe "
                                                      "con coma en español"))
        elif not f.presente(n):
            huerfanos.append(Huerfano(linea, n.texto, n.forma))
    return huerfanos


def _orden_cifras_es(a) -> int:
    tex = Path(a.tex)
    f = lee_fuentes_es(a.fuentes)
    h = _chequeo_cifras_es(tex, f)
    print(f"== {tex} contra {len(a.fuentes)} fuentes")
    for ruta, cuenta in f.por_fuente.items():
        print(f"  fuente {ruta}: {cuenta} números")
    for x in h:
        print(f"  línea {x.linea}: «{x.texto}» (forma {x.forma})")
    print("CHEQUEO DE CIFRAS (español): "
          + ("LIMPIO" if not h else f"{len(h)} HUÉRFANOS"))
    return 1 if h else 0


# ── Similitud ───────────────────────────────────────────────────────────────
def _fuente_y_rango(espec: str) -> tuple[Path, tuple[int, int] | None]:
    m = re.fullmatch(r"(.+):(\d+)-(\d+)", espec)
    if m and not Path(espec).exists():
        return Path(m.group(1)), (int(m.group(2)), int(m.group(3)))
    return Path(espec), None


def palabras(espec: str | Path) -> list[str]:
    """Palabras en minúscula de una fuente (`.tex` limpio de comandos)."""
    ruta, rango = _fuente_y_rango(str(espec))
    if not ruta.is_file():
        raise FileNotFoundError(f"no existe {ruta}")
    t = ruta.read_text(encoding="utf-8")
    if rango:
        lineas = t.splitlines()
        if rango[0] < 1 or rango[1] > len(lineas) or rango[0] > rango[1]:
            raise ValueError(f"rango {rango} fuera de {ruta} ({len(lineas)} líneas)")
        t = "\n".join(lineas[rango[0] - 1:rango[1]])
    if ruta.suffix.lower() == ".tex":
        t = _quita_comentarios(t)
        t = _solo_cuerpo(t)
        t = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", " ", t,
                   flags=re.S)
        t = limpia_tex(t)
        t = re.sub(r"\\[A-Za-z@]+\*?|\\.", " ", t)
    # El guion dentro de palabra une («self-generation» = «selfgeneration», como
    # lo deja el texto extraído del PDF de WEEF); el resto de la puntuación separa.
    t = re.sub(r"(?<=[^\W_])-(?=[^\W_])", "", t)
    return re.findall(r"[^\W_]+", t.lower())


def ngramas(ps: list[str], n: int = N_GRAMA) -> set[tuple[str, ...]]:
    return {tuple(ps[i:i + n]) for i in range(len(ps) - n + 1)}


@dataclass
class Similitud:
    n_gramas: int
    por_fuente: dict[str, float] = field(default_factory=dict)
    union: float = 0.0


def similitud(tex: Path, fuentes: list) -> Similitud:
    propios = ngramas(palabras(tex))
    if not propios:
        raise ValueError(f"{tex} tiene menos de {N_GRAMA} palabras")
    r = Similitud(len(propios))
    todos = set()
    for f in fuentes:
        comunes = propios & ngramas(palabras(f))
        todos |= comunes
        r.por_fuente[str(f)] = 100.0 * len(comunes) / len(propios)
    r.union = 100.0 * len(todos) / len(propios)
    return r


def _orden_similitud(a) -> int:
    r = similitud(Path(a.tex), a.fuentes)
    print(f"== {a.tex}: {r.n_gramas} {N_GRAMA}-gramas distintos")
    fallo = False
    for f, p in r.por_fuente.items():
        marca = " > umbral" if p > UMBRAL_FUENTE else ""
        fallo |= p > UMBRAL_FUENTE
        print(f"  {p:6.2f} %  {f}{marca} ({UMBRAL_FUENTE:g} %)")
    fallo |= r.union > UMBRAL_UNION
    print(f"  {r.union:6.2f} %  unión{' > umbral' if r.union > UMBRAL_UNION else ''}"
          f" ({UMBRAL_UNION:g} %)")
    print("SIMILITUD: " + ("FALLA" if fallo else "DENTRO DE LOS UMBRALES"))
    return 1 if fallo else 0


# ── DOI ─────────────────────────────────────────────────────────────────────
def lee_bib(t: str) -> list[dict]:
    """Entradas de un .bib: [{'tipo', 'clave', 'campos': {nombre: valor}}]."""
    entradas = []
    for m in re.finditer(r"@(\w+)\s*\{", t):
        tipo = m.group(1).lower()
        if tipo in ("comment", "string", "preamble"):
            continue
        ini = m.end() - 1
        fin = _fin_grupo(t, ini)
        if fin < 0:
            raise ValueError(f"entrada sin cerrar en la posición {m.start()}")
        cuerpo = t[ini + 1:fin - 1]
        clave, _, resto = cuerpo.partition(",")
        campos = {}
        k = 0
        while True:
            mc = re.compile(r"\s*([A-Za-z][\w-]*)\s*=\s*").match(resto, k)
            if not mc:
                break
            nombre, k = mc.group(1).lower(), mc.end()
            if k < len(resto) and resto[k] == "{":
                f = _fin_grupo(resto, k)
                valor, k = resto[k + 1:f - 1], f
            elif k < len(resto) and resto[k] == '"':
                f = resto.index('"', k + 1)
                valor, k = resto[k + 1:f], f + 1
            else:
                mv = re.compile(r"[^,\s}]+").match(resto, k)
                valor, k = (mv.group(0), mv.end()) if mv else ("", k)
            campos[nombre] = " ".join(valor.split())
            mcoma = re.compile(r"\s*,?").match(resto, k)
            k = mcoma.end()
        entradas.append({"tipo": tipo, "clave": clave.strip(), "campos": campos})
    return entradas


def normaliza_titulo(t: str) -> set[str]:
    t = re.sub(r"<[^>]+>", " ", t)                    # etiquetas de Crossref
    # Acentos LaTeX. Los de símbolo (\' \` \" \^ \~ \= \.) se quitan aunque
    # los siga una letra: «{\'o}», «\'{o}» y «\'o» dejan la «o» (antes, el
    # lookahead los dejaba y «Optimizaci{\'o}n» se partía en dos palabras).
    # Los de letra (\u \v \H \c \k \b \d \r \t) solo delante de «{» o de un
    # espacio y una letra, para no comerse \cite o \textbf. \i y \j (sin punto)
    # quedan como i y j.
    t = re.sub(r"\\[`'\"^~=.]", "", t)
    t = re.sub(r"\\[uvHckbdrt](?:(?=\s*\{)|\s+(?=[A-Za-z]))", "", t)
    t = re.sub(r"\\([ij])(?![A-Za-z])", r"\1", t)
    t = re.sub(r"\\[A-Za-z]+", " ", t)
    t = t.replace("{", "").replace("}", "")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+", t.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def normaliza_doi(d: str) -> str:
    d = d.strip()
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I)


def consulta_crossref(doi: str) -> str | None:
    """Título que Crossref da al DOI; None si Crossref no lo conoce (404).
    Cualquier otro error (red, plazo, respuesta rara) se propaga."""
    url = CROSSREF + urllib.parse.quote(doi, safe="/:;()._-")
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=PLAZO_RED_S) as r:
            datos = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    titulos = datos["message"].get("title") or []
    return titulos[0] if titulos else ""


@dataclass(frozen=True)
class Entrada:
    clave: str
    ok: bool
    motivo: str
    doi: str = ""


def _declara_interna(campos: dict) -> bool:
    """La `note` de la entrada dice que es una fuente interna."""
    return bool(PATRON_INTERNA.search(campos.get("note", "")))


def verifica_dois(bib: Path) -> list[Entrada]:
    salida = []
    for e in lee_bib(bib.read_text(encoding="utf-8")):
        c, campos = e["clave"], e["campos"]
        doi = normaliza_doi(campos.get("doi", ""))
        if not doi:
            # La URL vale en el campo `url` o como `\url{...}` en `note` o
            # `howpublished` (así van las normas en referencias.bib).
            if campos.get("url") or any("\\url{" in v for v in campos.values()):
                salida.append(Entrada(c, True, "sin DOI; con URL"))
            elif e["tipo"] in TIPOS_TESIS:
                # Una tesis no tiene DOI y a menudo tampoco URL pública: se
                # lista, no falla (decisión del controlador, Tarea 6, ronda 1).
                salida.append(Entrada(c, True, "tesis sin DOI (permitido)"))
            elif e["tipo"] in TIPOS_LIBRO and campos.get("isbn"):
                # Un libro sin DOI ni URL se identifica por su ISBN (decisión
                # del controlador, tesis de entrega, Tarea 1, ronda 1).
                salida.append(Entrada(c, True, "libro con ISBN (permitido)"))
            elif e["tipo"] in TIPOS_MANUSCRITO:
                # Un manuscrito sin publicar se cita sin DOI ni URL (decisión
                # del controlador, tesis de entrega, Tarea 4, ronda 1).
                salida.append(Entrada(c, True, "manuscrito (permitido)"))
            elif e["tipo"] in TIPOS_FUENTE_INTERNA and _declara_interna(campos):
                # Un informe o un dato sin URL pública que el trabajo usó se
                # cita igual (art. 22 del reglamento), con una `note` que lo
                # declara fuente interna (tesis de entrega, ronda del jurado,
                # I-10). Una `note` que no lo declara sigue fallando.
                salida.append(Entrada(c, True, "fuente interna (permitido)"))
            else:
                salida.append(Entrada(c, False, "sin DOI y sin URL"))
            continue
        titulo = campos.get("title", "")
        if not titulo:
            salida.append(Entrada(c, False, "sin título en el .bib", doi))
            continue
        try:
            remoto = consulta_crossref(doi)
        except Exception as exc:          # se informa como fallo, no se traga
            salida.append(Entrada(c, False, f"error al consultar Crossref: "
                                            f"{type(exc).__name__}: {exc}", doi))
            continue
        if remoto is None:
            salida.append(Entrada(c, False, "Crossref no conoce el DOI (404)", doi))
            continue
        j = jaccard(normaliza_titulo(titulo), normaliza_titulo(remoto))
        if j >= UMBRAL_JACCARD:
            salida.append(Entrada(c, True, f"título coincide (Jaccard {j:.2f})", doi))
        else:
            salida.append(Entrada(c, False, f"título distinto (Jaccard {j:.2f}): "
                                            f"Crossref dice «{remoto}»", doi))
    return salida


def _orden_dois(a) -> int:
    r = verifica_dois(Path(a.bib))
    malas = [e for e in r if not e.ok]
    print(f"== {a.bib}: {len(r)} entradas, {len(malas)} fallos")
    for e in r:
        print(f"  {'OK   ' if e.ok else 'FALLO'} {e.clave}"
              f"{' [' + e.doi + ']' if e.doi else ''}: {e.motivo}")
    print("DOI: " + ("TODOS VERIFICADOS" if not malas else f"{len(malas)} FALLOS"))
    return 1 if malas else 0


# ── Orden ───────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = p.add_subparsers(dest="orden", required=True)
    c = sub.add_parser("cifras")
    c.add_argument("tex")
    c.add_argument("cifras")
    c.set_defaults(fn=_orden_cifras)
    ce = sub.add_parser("cifras-es")
    ce.add_argument("tex")
    ce.add_argument("fuentes", nargs="+")
    ce.set_defaults(fn=_orden_cifras_es)
    s = sub.add_parser("similitud")
    s.add_argument("tex")
    s.add_argument("fuentes", nargs="+")
    s.set_defaults(fn=_orden_similitud)
    d = sub.add_parser("dois")
    d.add_argument("bib")
    d.set_defaults(fn=_orden_dois)
    try:
        a = p.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as e:
        return int(e.code or 0) if e.code not in (None, 0) else 0
    return a.fn(a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
