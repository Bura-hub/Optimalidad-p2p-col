# -*- coding: utf-8 -*-
"""Mide los capítulos redactados contra el perfil de estilo del autor."""
import re
from pathlib import Path

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


def prosa(texto: str) -> str:
    """Deja solo el cuerpo argumentativo."""
    t = re.sub(r"(?m)^%.*$", "", texto)                     # comentarios
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


def medir(t: str) -> dict:
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", t) if len(p.split()) > 25]
    palabras = t.split()
    n = len(palabras)
    oraciones = [o for o in re.split(r"(?<=[.!?])\s+", t) if len(o.split()) >= 4]
    largos = [len(o.split()) for o in oraciones]
    return {
        "palabras": n,
        "raya_larga_por_1000": 1000 * t.count("—") / n,
        "pal_por_oracion": sum(largos) / len(largos),
        "pct_oraciones_largas": 100 * sum(1 for x in largos if x > 40) / len(largos),
        "pal_por_parrafo": sum(len(p.split()) for p in parrafos) / len(parrafos),
        "oraciones_por_parrafo": sum(
            len([o for o in re.split(r"(?<=[.!?])\s+", p) if len(o.split()) >= 4])
            for p in parrafos) / len(parrafos),
        "es_decir_por_1000": 1000 * len(re.findall(r"es decir|esto es,|entendid[oa] como", t, re.I)) / n,
        "punto_y_coma_por_1000": 1000 * t.count(";") / n,
    }


todo = ""
print(f"{'capítulo':<26} {'palabras':>8} {'—/1000':>8} {'pal/or':>7} "
      f"{'%>40':>6} {'pal/par':>8} {'or/par':>7} {'esdecir':>8} {';/1000':>7}")
for f in sorted(BASE.glob("0[2345]-*.tex")):
    t = prosa(f.read_text(encoding="utf-8"))
    todo += t + "\n\n"
    m = medir(t)
    print(f"{f.stem:<26} {m['palabras']:>8} {m['raya_larga_por_1000']:>8.2f} "
          f"{m['pal_por_oracion']:>7.1f} {m['pct_oraciones_largas']:>6.1f} "
          f"{m['pal_por_parrafo']:>8.1f} {m['oraciones_por_parrafo']:>7.1f} "
          f"{m['es_decir_por_1000']:>8.2f} {m['punto_y_coma_por_1000']:>7.2f}")

m = medir(todo)
print("-" * 92)
print(f"{'MÍO (total)':<26} {m['palabras']:>8} {m['raya_larga_por_1000']:>8.2f} "
      f"{m['pal_por_oracion']:>7.1f} {m['pct_oraciones_largas']:>6.1f} "
      f"{m['pal_por_parrafo']:>8.1f} {m['oraciones_por_parrafo']:>7.1f} "
      f"{m['es_decir_por_1000']:>8.2f} {m['punto_y_coma_por_1000']:>7.2f}")
print(f"{'BRAYAN (perfil 2026)':<26} {'20238':>8} "
      f"{PERFIL['raya_larga_por_1000']:>8.2f} {PERFIL['pal_por_oracion']:>7.1f} "
      f"{PERFIL['pct_oraciones_largas']:>6.1f} {PERFIL['pal_por_parrafo']:>8.1f} "
      f"{PERFIL['oraciones_por_parrafo']:>7.1f} {PERFIL['es_decir_por_1000']:>8.2f} "
      f"{PERFIL['punto_y_coma_por_1000']:>7.2f}")

# Cómo refiero las figuras
print("\n=== Referencia a figuras en mi texto ===")
crudo = "\n".join(f.read_text(encoding="utf-8") for f in sorted(BASE.glob("0[2345]-*.tex")))
patrones = {
    "La Figura N + verbo (el suyo)": r"[Ll]a Figura~?\\ref\{[^}]*\}\s+[a-záéíóúñ]+",
    "(Figura N) pospuesto": r"\(Figura~?\\ref",
    "se observa / se aprecia / véase": r"(se observa|se aprecia|véase|puede verse)",
    "El panel ... de la Figura": r"[Ee]l panel [^.]{0,40}Figura",
}
for nom, pat in patrones.items():
    print(f"  {nom:<34} {len(re.findall(pat, crudo)):>3}")
print(f"  parrafos 'Nota.' bajo figura       {len(re.findall(r'Nota[.]', crudo)):>3}")
