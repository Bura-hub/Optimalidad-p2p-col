# -*- coding: utf-8 -*-
"""Mide texto LaTeX contra el perfil de estilo del autor.

Uso:
    python medir_estilo.py                      # los capítulos de sections/
    python medir_estilo.py FICHERO.tex [...]    # cualquier fichero LaTeX

Sin argumentos mide, como siempre, los capítulos 02, 03, 04, 05 y 07 del
documento de proceso. Con argumentos mide los ficheros dados, uno por fila,
y un total si son varios. La guía que acompaña a estas cifras está en
reformateo/documento/ESTILO_AUTOR.md; el perfil, en GUIA.md §10.1.

Qué se mide: solo el cuerpo que el lector lee. Se quitan el preámbulo (todo
lo anterior a \\begin{document}, si lo hay), los comentarios, lo apartado
(guardado, descartado), los flotantes (figure, figure*, table, table*), el
dibujo (tikzpicture), las ecuaciones de bloque (equation, equation*, align,
align*, gather, gather*, multline, multline*, eqnarray), los entornos de
IEEEtran que no son prosa del cuerpo (IEEEkeywords, IEEEbiography,
IEEEbiographynophoto), la parte en inglés (otherlanguage), la bibliografía
(\\bibliography, \\bibliographystyle, thebibliography) y los campos de la
portada (\\title, \\author, \\thanks, \\markboth). El resumen se mide, porque
es prosa en español.

Dos convenciones que conviene conocer al leer las cifras: una referencia
cruzada (\\ref, \\eqref, \\cite) cuenta como una palabra, que es lo que el
lector ve impreso en su lugar («3», «[12]»); y el entorno longtable no se
excluye, de modo que la tabla larga del capítulo 2 cuenta como texto (se deja
así para que la medición sin argumentos no cambie).
"""
import re
import sys
from pathlib import Path

try:  # la consola de Windows no siempre habla UTF-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

BASE = Path(r"C:\Users\burav\Documentos\MaIE - UDENAR\Proyectos\SistemaBL"
            r"\reformateo\documento\sections")

# Perfil medido del autor (corpus 2026, tres informes MTE)
PERFIL = {
    "raya_larga_por_1000": 0.0,
    "pal_por_oracion": 24.6,
    "pct_oraciones_largas": 12.0,
    "pal_por_parrafo": 74.0,
    "oraciones_por_parrafo": 3.2,
    "es_decir_por_1000": 1.24,
    "punto_y_coma_por_1000": 2.5,      # 51/20238*1000
}

# Entornos que no son prosa del cuerpo y que los capítulos de sections/ no
# usan: quitarlos no altera la medición sin argumentos.
ENTORNOS_NUEVOS = (
    "otherlanguage", "IEEEkeywords", "IEEEbiography", "IEEEbiographynophoto",
    "thebibliography", "figure*", "table*", "equation*", "align", "align*",
    "gather", "gather*", "multline", "multline*", "eqnarray", "eqnarray*",
)

# Macros de portada y bibliografía que se quitan con sus argumentos.
MACROS_FUERA = {
    "title": 1, "author": 1, "thanks": 1, "markboth": 2, "tituloingles": 1,
    "bibliography": 1, "bibliographystyle": 1,
}


def _fin_grupo(t: str, i: int, abre: str, cierra: str) -> int:
    """Índice tras el grupo balanceado que empieza en t[i] == abre."""
    nivel, j = 0, i
    while j < len(t):
        c = t[j]
        if c == "\\":          # carácter escapado: «\{», «\}», «\%»...
            j += 2
            continue
        if c == abre:
            nivel += 1
        elif c == cierra:
            nivel -= 1
            if nivel == 0:
                return j + 1
        j += 1
    return len(t)


def quitar_macro(t: str, nombre: str, nargs: int) -> str:
    """Quita \\nombre[opc]{arg}...{arg}, con llaves anidadas."""
    patron = re.compile(r"\\" + nombre + r"\*?(?![a-zA-Z])")
    salida, pos = [], 0
    for m in patron.finditer(t):
        if m.start() < pos:
            continue
        salida.append(t[pos:m.start()])
        k = m.end()
        while k < len(t) and t[k] in " \t\n":
            k += 1
        if k < len(t) and t[k] == "[":
            k = _fin_grupo(t, k, "[", "]")
        for _ in range(nargs):
            while k < len(t) and t[k] in " \t\n":
                k += 1
            if k < len(t) and t[k] == "{":
                k = _fin_grupo(t, k, "{", "}")
        salida.append(" ")
        pos = k
    salida.append(t[pos:])
    return "".join(salida)


def cuerpo(texto: str) -> str:
    """El cuerpo del documento, sin preámbulo ni comentarios."""
    m = re.search(r"\\begin\{document\}(.*?)(?:\\end\{document\}|\Z)",
                  texto, flags=re.S)
    t = m.group(1) if m else texto
    # Comentarios de línea entera y al final de línea; «\%» no es comentario.
    return re.sub(r"(?m)(?<!\\)%.*$", "", t)


def prosa(texto: str) -> str:
    """Deja solo el cuerpo argumentativo."""
    t = cuerpo(texto)
    for env in ENTORNOS_NUEVOS:
        e = re.escape(env)
        t = re.sub(r"\\begin\{" + e + r"\}.*?\\end\{" + e + r"\}", " ", t,
                   flags=re.S)
    for nombre, nargs in MACROS_FUERA.items():
        t = quitar_macro(t, nombre, nargs)
    # \IEEEPARstart{L}{a} es la palabra «La», no dos.
    t = re.sub(r"\\IEEEPARstart\{([^}]*)\}\{([^}]*)\}", r"\1\2", t)
    # Lo apartado no se imprime, de modo que tampoco cuenta para el
    # estilo: medirlo falseaba el perfil con texto que nadie lee.
    for env in ("guardado", "descartado"):
        t = re.sub(r"\\begin\{" + env + r"\}.*?\\end\{" + env + r"\}",
                   " ", t, flags=re.S)
    t = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", " ", t,
               flags=re.S)
    t = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", " ", t, flags=re.S)
    t = re.sub(r"\\begin\{table\}.*?\\end\{table\}", " ", t, flags=re.S)
    t = re.sub(r"\\begin\{equation\}.*?\\end\{equation\}", " ", t, flags=re.S)
    t = re.sub(r"\\(uni|pct|num)\{([^}]*)\}(\{[^}]*\})?", r"\2", t)
    t = re.sub(r"\\(section|subsection|label|justifying|includegraphics)"
               r"(\[[^\]]*\])?(\{[^}]*\})?", " ", t)
    t = re.sub(r"\\(begin|end)\{[^}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", t)      # resto de macros
    t = re.sub(r"[{}$~]", " ", t)
    return re.sub(r"[ \t]+", " ", t)


def _media(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def medir(t: str) -> dict:
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", t) if len(p.split()) > 25]
    palabras = t.split()
    n = len(palabras) or 1
    oraciones = [o for o in re.split(r"(?<=[.!?])\s+", t) if len(o.split()) >= 4]
    largos = [len(o.split()) for o in oraciones]
    return {
        "palabras": len(palabras),
        "raya_larga_por_1000": 1000 * t.count("—") / n,
        "pal_por_oracion": _media(largos),
        "pct_oraciones_largas": (100 * sum(1 for x in largos if x > 40) / len(largos)
                                 if largos else float("nan")),
        "pal_por_parrafo": _media([len(p.split()) for p in parrafos]),
        "oraciones_por_parrafo": _media([
            len([o for o in re.split(r"(?<=[.!?])\s+", p) if len(o.split()) >= 4])
            for p in parrafos]),
        "es_decir_por_1000": 1000 * len(re.findall(r"es decir|esto es,|entendid[oa] como", t, re.I)) / n,
        "punto_y_coma_por_1000": 1000 * t.count(";") / n,
    }


def fila(nombre: str, m: dict) -> str:
    return (f"{nombre:<26} {m['palabras']:>8} {m['raya_larga_por_1000']:>8.2f} "
            f"{m['pal_por_oracion']:>7.1f} {m['pct_oraciones_largas']:>6.1f} "
            f"{m['pal_por_parrafo']:>8.1f} {m['oraciones_por_parrafo']:>7.1f} "
            f"{m['es_decir_por_1000']:>8.2f} {m['punto_y_coma_por_1000']:>7.2f}")


# --- Primera persona (el registro técnico del autor es impersonal) ---------
# Verbos en -amos/-emos/-imos sin tilde, salvo los sustantivos y adjetivos
# del dominio que terminan igual; y los imperfectos y condicionales en
# -íamos/-ábamos. Heurística: imprime las formas para revisarlas a ojo.
NO_VERBOS = {
    "tramos", "ramos", "gramos", "kilogramos", "extremos", "remos", "primos",
    "reclamos", "supremos", "racimos",
}

# Abreviaturas tras las que un número no abre oración («art. 25», «Fig. 3»).
ABREVIATURAS = {"art", "arts", "fig", "figs", "núm", "num", "ec", "sec",
                "secs", "cap", "tab", "p", "pp", "no", "n", "vol"}


def abre_con_cifra(t: str) -> int:
    """Oraciones que empiezan por cifra (C-27: nunca se abre con cifra)."""
    partes = re.split(r"(?<=[.!?])\s+", t)
    n = 0
    for prev, cur in zip([""] + partes, partes):
        if re.match(r"\d", cur.strip()):
            ult = re.findall(r"([A-Za-zÁÉÍÓÚáéíóúñ]+)\.$", prev.strip())
            if ult and ult[-1].lower() in ABREVIATURAS:
                continue
            n += 1
    return n


def primera_persona(t: str) -> list:
    formas = []
    for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", t):
        wl = w.lower()
        if re.fullmatch(r"nuestr[oa]s?|nosotr[oa]s", wl):
            formas.append(wl)
        elif re.search(r"(íamos|ábamos)$", wl):
            formas.append(wl)
        elif (re.search(r"(amos|emos|imos)$", wl) and len(wl) > 5
              and not re.search(r"[áéíóú]", wl) and wl not in NO_VERBOS):
            formas.append(wl)
    return formas


def pies(texto: str) -> list:
    """Longitud en palabras de cada \\caption{...} del cuerpo."""
    t = cuerpo(texto)
    largos = []
    for m in re.finditer(r"\\caption(?![a-zA-Z])", t):
        k = m.end()
        if k < len(t) and t[k] == "[":
            k = _fin_grupo(t, k, "[", "]")
        if k < len(t) and t[k] == "{":
            fin = _fin_grupo(t, k, "{", "}")
            largos.append(len(prosa(t[k + 1:fin - 1]).split()))
    return largos


def main(argv: list) -> None:
    if argv:
        ficheros = [Path(a) for a in argv]
        faltan = [str(f) for f in ficheros if not f.is_file()]
        if faltan:
            sys.exit("No existe: " + ", ".join(faltan))
        rotulo_total = "TOTAL" if len(ficheros) > 1 else None
    else:
        ficheros = sorted(BASE.glob("0[23457]-*.tex"))
        rotulo_total = "MÍO (total)"

    todo = ""
    print(f"{'capítulo':<26} {'palabras':>8} {'—/1000':>8} {'pal/or':>7} "
          f"{'%>40':>6} {'pal/par':>8} {'or/par':>7} {'esdecir':>8} {';/1000':>7}")
    for f in ficheros:
        t = prosa(f.read_text(encoding="utf-8"))
        todo += t + "\n\n"
        print(fila(f.stem, medir(t)))

    print("-" * 92)
    if rotulo_total:
        print(fila(rotulo_total, medir(todo)))
    print(f"{'BRAYAN (perfil 2026)':<26} {'20238':>8} "
          f"{PERFIL['raya_larga_por_1000']:>8.2f} {PERFIL['pal_por_oracion']:>7.1f} "
          f"{PERFIL['pct_oraciones_largas']:>6.1f} {PERFIL['pal_por_parrafo']:>8.1f} "
          f"{PERFIL['oraciones_por_parrafo']:>7.1f} {PERFIL['es_decir_por_1000']:>8.2f} "
          f"{PERFIL['punto_y_coma_por_1000']:>7.2f}")

    # Cómo se refieren las figuras
    print("\n=== Referencia a figuras en mi texto ===")
    crudo = "\n".join(f.read_text(encoding="utf-8") for f in ficheros)
    patrones = {
        "La Figura N + verbo (el suyo)": r"[Ll]a Figura~?\\ref\{[^}]*\}\s+[a-záéíóúñ]+",
        "(Figura N) pospuesto": r"\(Figura~?\\ref",
        "se observa / se aprecia / véase": r"(se observa|se aprecia|véase|puede verse)",
        "El panel ... de la Figura": r"[Ee]l panel [^.]{0,40}Figura",
    }
    for nom, pat in patrones.items():
        print(f"  {nom:<34} {len(re.findall(pat, crudo)):>3}")
    print(f"  parrafos 'Nota.' bajo figura       {len(re.findall(r'Nota[.]', crudo)):>3}")

    # Lo que añade la versión por fichero: convención IEEE («Fig.»), notas
    # de figura, pies largos y lo que no es suyo. Sobre el cuerpo, sin
    # comentarios.
    cuerpos = "\n".join(cuerpo(f.read_text(encoding="utf-8")) for f in ficheros)
    extra = {
        "La Fig. N + verbo (IEEE)": r"[Ll]a\s+Fig\.~?\\ref\{[^}]*\}\s+[a-záéíóúñ]+",
        "(Fig. N) pospuesto": r"\((?:[^()]{0,40}\s)?Fig\.~?\\ref",
        "\\notafig{} (nota de figura)": r"\\notafig\{",
    }
    for nom, pat in extra.items():
        print(f"  {nom:<34} {len(re.findall(pat, cuerpos)):>3}")
    lp = [x for f in ficheros for x in pies(f.read_text(encoding="utf-8"))]
    if lp:
        print(f"  pies de figura/tabla: {len(lp)}, mediana {sorted(lp)[len(lp)//2]} "
              f"palabras, máximo {max(lp)}, de más de 100: {sum(x > 100 for x in lp)}")

    print("\n=== Lo que no es suyo (debe dar cero en texto nuevo) ===")
    prosa_total = todo
    vetados = {
        "conviene": r"\b[Cc]onviene\b",
        "cabe destacar / mencionar": r"\b[Cc]abe (destacar|mencionar)",
        "es importante": r"\b[Ee]s importante\b",
        "aguas arriba / abajo": r"aguas (arriba|abajo)",
        "grandilocuencia 2023": r"se erige|abre la puerta|sienta las bases|"
                                r"juega un papel|es imperativo",
    }
    for nom, pat in vetados.items():
        print(f"  {nom:<34} {len(re.findall(pat, prosa_total)):>3}")
    print(f"  {'oración que abre con cifra':<34} {abre_con_cifra(prosa_total):>3}")
    pp = primera_persona(prosa_total)
    print(f"  {'primera persona (heurística)':<34} {len(pp):>3}"
          + (f"  [{', '.join(sorted(set(pp))[:12])}]" if pp else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
