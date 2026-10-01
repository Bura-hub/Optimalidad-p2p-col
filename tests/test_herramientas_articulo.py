"""Pruebas de las herramientas de control del artículo (Tarea 2 del plan
`docs/superpowers/plans/2026-09-29-articulo-latam.md`).

Casos sintéticos en un directorio temporal: no leen el canon ni escriben en
`outputs/` ni en `graficas/`, y la red de Crossref se sustituye con
`monkeypatch`. Se corren solas:

    .venv/Scripts/python.exe -m pytest tests/test_herramientas_articulo.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "reformateo" / "documento" / "scripts" / "articulo"))
sys.path.insert(0, str(RAIZ / "reformateo" / "documento" / "scripts"))

import herramientas_articulo as ha  # noqa: E402
import compuerta_vetadas as cv  # noqa: E402

CABECERA = "clave,valor,unidad,texto_en,definicion,fuente,seccion_canon\n"


def _csv(tmp_path: Path, filas: list[tuple[str, str]]) -> Path:
    """Escribe un cifras.csv mínimo con (clave, texto_en)."""
    p = tmp_path / "cifras.csv"
    cuerpo = "".join(f'{c},0,MCOP,"{t}",def,fuente,§6\n' for c, t in filas)
    p.write_text(CABECERA + cuerpo, encoding="utf-8")
    return p


def _tex(tmp_path: Path, cuerpo: str, nombre: str = "a.tex") -> Path:
    p = tmp_path / nombre
    p.write_text("\\documentclass[10pt,journal]{IEEEtran}\n"
                 "\\begin{document}\n" + cuerpo + "\n\\end{document}\n",
                 encoding="utf-8")
    return p


def _formas(huerfanos):
    return [h.texto for h in huerfanos]


# ── cifras ────────────────────────────────────────────────────────────────
def test_cifras_solo_marca_la_que_no_esta(tmp_path):
    tabla = _csv(tmp_path, [("vend", "0.542")])
    tex = _tex(tmp_path, "The seller share is 0.542 and not 0.543.")
    h = ha.chequeo_cifras_tex(tex, tabla)
    assert _formas(h) == ["0.543"]
    assert h[0].linea == 3
    assert ha.main(["cifras", str(tex), str(tabla)]) == 1


def test_cifras_lista_blanca(tmp_path):
    tabla = _csv(tmp_path, [("vend", "0.542")])
    tex = _tex(tmp_path,
               "In 2025, the 5 institutions of Pasto under CREG Resolution\n"
               "101 072 and Law 1715 (Art.~18) had 0.542; Resolution CREG~101\\,099\n"
               "of 2026, Law 142 of 1994, Arts. 19--21, CREG 101\\,072/2025,\n"
               "received September 29, 2026 (BPIN 2021000100499), 07:00--17:00.")
    assert ha.chequeo_cifras_tex(tex, tabla) == []
    assert ha.main(["cifras", str(tex), str(tabla)]) == 0


def test_cifras_formato_espanol_y_otro_redondeo_son_huerfanos(tmp_path):
    tabla = _csv(tmp_path, [("vend", "0.542"), ("e0", "46.50")])
    tex = _tex(tmp_path, "Shares of 0,542 and 0.54; benefit 46,50 and 46.5.")
    assert _formas(ha.chequeo_cifras_tex(tex, tabla)) == [
        "0,542", "0.54", "46,50", "46.5"]


def test_cifras_normaliza_signo_millares_y_porcentaje(tmp_path):
    tabla = _csv(tmp_path, [("a", "-0.96 %"), ("b", "6,144"), ("c", "17 of 18"),
                            ("d", "1.69 %"), ("e", "-17,689"), ("f", "20.47 %")])
    tex = _tex(tmp_path,
               "Gaps of $-$0.96\\,\\% and \\textminus 0.96~\\% and −0.96\\%,\n"
               "and $-0.96$\\% over 6{,}144 h and 6,144 h; 17 of 18 hours;\n"
               "1.69\\% and --17{,}689 COP; from 1.1--20.47\\,\\%.")
    # 1.1 no está en la tabla: es el único huérfano.
    assert _formas(ha.chequeo_cifras_tex(tex, tabla)) == ["1.1"]


def test_cifras_millares_con_espacio_fino_no_coinciden(tmp_path):
    tabla = _csv(tmp_path, [("b", "6,144")])
    tex = _tex(tmp_path, "Over 6\\,144 h, not 6,144 h.")
    assert _formas(ha.chequeo_cifras_tex(tex, tabla)) == ["6\\,144"]


def test_cifras_porcentaje_exige_forma_con_porcentaje(tmp_path):
    tabla = _csv(tmp_path, [("a", "46.50")])
    tex = _tex(tmp_path, "A benefit of 46.50 MCOP, never 46.50\\,\\%.")
    assert _formas(ha.chequeo_cifras_tex(tex, tabla)) == ["46.50\\,\\%"]


def test_cifras_ignora_comentarios_matematica_citas_y_bibliografia(tmp_path):
    tabla = _csv(tmp_path, [("vend", "0.542")])
    tex = _tex(tmp_path,
               "% a comment with 0.777\n"
               "Text 0.542 \\cite{Chacon2025EMS} in Fig.~\\ref{fig:99}.\\label{s:77}\n"
               "\\begin{equation}\n x = 0.333 \\label{eq:1}\n\\end{equation}\n"
               "\\begin{figure}[!t]\\includegraphics[width=0.95\\columnwidth]{fig44.pdf}"
               "\\end{figure}\n"
               "$C_{4}$ and E0, CV2 and P2P, x_{77}\n"
               "\\begin{thebibliography}{10}\n\\bibitem{a} vol. 45, pp. 102114, 2026.\n"
               "\\end{thebibliography}")
    assert ha.chequeo_cifras_tex(tex, tabla) == []


def test_cifras_marca_cifra_ok(tmp_path):
    tabla = _csv(tmp_path, [("vend", "0.542")])
    tex = _tex(tmp_path, "A tolerance of 1e-6, i.e. 0.000001 % cifra-ok: tolerancia H-51")
    assert ha.chequeo_cifras_tex(tex, tabla) == []


# ── cifras-es (versión de entrega de la tesis) ────────────────────────────
def _md(tmp_path: Path, texto: str, nombre: str = "tesis.md") -> Path:
    p = tmp_path / nombre
    p.write_text(texto, encoding="utf-8")
    return p


def test_cifras_es_presente_y_huerfano(tmp_path):
    fuente = _md(tmp_path, "La parte del vendedor es 0,542 en E0.\n")
    tex = _tex(tmp_path, "La parte del vendedor es 0,542.\nNo es 0,543.")
    h = ha.chequeo_cifras_es(tex, [fuente])
    assert _formas(h) == ["0,543"]
    assert h[0].linea == 4
    assert ha.main(["cifras-es", str(tex), str(fuente)]) == 1
    limpio = _tex(tmp_path, "La parte del vendedor es 0,542.", "b.tex")
    assert ha.chequeo_cifras_es(limpio, [fuente]) == []
    assert ha.main(["cifras-es", str(limpio), str(fuente)]) == 0


def test_cifras_es_el_redondeo_cuenta(tmp_path):
    fuente = _md(tmp_path, "Beneficio de 46,50 MCOP y parte de 0,542.\n")
    tex = _tex(tmp_path, "Beneficio de 46,5 y 46,50; parte de 0,54.")
    assert _formas(ha.chequeo_cifras_es(tex, [fuente])) == ["46,5", "0,54"]


@pytest.mark.parametrize("en_fuente", ["6144", "6.144", "6 144", "6\u202f144"])
def test_cifras_es_separadores_de_miles(tmp_path, en_fuente):
    fuente = _md(tmp_path, f"El horizonte tiene {en_fuente} horas.\n")
    tex = _tex(tmp_path, "Durante 6\\,144 h, es decir, 6 144 horas, 6~144 y 6144;\n"
                         "también $6\\,144$ y 6.144 horas.")
    assert ha.chequeo_cifras_es(tex, [fuente]) == []


def test_cifras_es_menos_y_porcentaje(tmp_path):
    fuente = _md(tmp_path, "La brecha queda entre el −0,96 % (I1) y el +1,6 %.\n")
    tex = _tex(tmp_path,
               "Brechas de $-0{,}96$\\,\\%, de $-$0,96\\,\\%, de \\textminus 0,96~\\%,\n"
               "de −0,96\\% y de -0,96\\%; C4 supera a C1 en 0,96 y en 1,6\\,\\%.\n"
               "Nunca $-1{,}6$\\,\\% ni 0,96 MCOP con signo: $-0{,}97$.")
    assert _formas(ha.chequeo_cifras_es(tex, [fuente])) == ["-1{,}6$\\,\\%", "-0{,}97"]


def test_cifras_es_porcentaje_exige_fuente_con_porcentaje(tmp_path):
    fuente = _md(tmp_path, "Un beneficio de 46,50 MCOP.\n")
    tex = _tex(tmp_path, "Un beneficio de 46,50 MCOP, nunca 46,50\\,\\%.")
    assert _formas(ha.chequeo_cifras_es(tex, [fuente])) == ["46,50\\,\\%"]


def test_cifras_es_lista_blanca(tmp_path):
    fuente = _md(tmp_path, "0,542\n")
    tex = _tex(tmp_path,
               "En 2025, las 5 instituciones, según el art. 25 y el artículo 18 de la\n"
               "Resolución CREG 101~072 de 2025, los arts.~19 a 21, la Ley 1715 de 2014,\n"
               "la Ley 142 de 1994, el Decreto 1073 de 2015, el numeral 2, literal 3,\n"
               "la CREG 174 y el Acuerdo 021 de 2020, el 29 de septiembre de 2026,\n"
               "el 2025-07-30 a las 07:00, dan 0,542 en los 13 casos.")
    assert ha.chequeo_cifras_es(tex, [fuente]) == []
    assert ha.main(["cifras-es", str(tex), str(fuente)]) == 0


def test_cifras_es_lista_blanca_no_cubre_lo_que_sigue(tmp_path):
    """La secuencia del artículo no se traga una cifra que viene detrás."""
    fuente = _md(tmp_path, "0,542\n")
    tex = _tex(tmp_path, "Según el art. 25, 0,777 y 2031 no están.")
    assert _formas(ha.chequeo_cifras_es(tex, [fuente])) == ["0,777", "2031"]


def test_cifras_es_punto_decimal_es_huerfano(tmp_path):
    fuente = _md(tmp_path, "0,542 y 1.1% en el resumen en inglés\n")
    tex = _tex(tmp_path, "La parte es 0.542 y 1.1 no; 0,542 sí.")
    h = ha.chequeo_cifras_es(tex, [fuente])
    assert _formas(h) == ["0.542", "1.1"]
    assert all("punto decimal" in x.forma for x in h)


def test_cifras_es_marca_cifra_ok_y_limpieza(tmp_path):
    fuente = _md(tmp_path, "0,542\n")
    tex = _tex(tmp_path,
               "% un comentario con 0,777\n"
               "Texto 0,542 \\cite{Chacon2025EMS} en la Fig.~\\ref{fig:99}.\\label{s:77}\n"
               "\\begin{equation}\n x = 0{,}333\n\\end{equation}\n"
               "Una tolerancia de 0,000001 % cifra-ok: tolerancia H-51\n"
               "\\begin{thebibliography}{10}\n\\bibitem{a} vol. 45, pp. 102114.\n"
               "\\end{thebibliography}")
    assert ha.chequeo_cifras_es(tex, [fuente]) == []


def test_cifras_es_csv_valor_crudo_y_texto_en(tmp_path):
    csv_ = tmp_path / "cifras.csv"
    csv_.write_text(
        "clave,valor,unidad,texto_en,definicion\n"
        "a,0.29565156068086623,MCOP,,resta\n"
        "b,6.458950214708952,%,,cv\n"
        "c,0.1809763582292419,fracción,,autosuficiencia\n"
        "d,-17689.4,COP,,brecha\n"
        "e,x,%,-0.96 %,brecha en texto\n"
        "f,f_cv 0.976 (±0.044),ST,,dominante\n",
        encoding="utf-8")
    tex = _tex(tmp_path,
               "Brecha de 0,30 y 0,296 MCOP; CV de 6,46\\,\\% y 6,5\\,\\%; SS de\n"
               "0,18 o 18,1\\,\\%; brecha de $-17\\,689$ COP y de 17\\,689,4; de\n"
               "$-0{,}96$\\,\\%; índice de 0,976 (\\textpm 0,044).\n"
               "Huérfanos: 0,31, 6,47\\,\\%, 0,30\\,\\%, 17\\,690.")
    h = ha.chequeo_cifras_es(tex, [csv_])
    assert _formas(h) == ["0,31", "6,47\\,\\%", "0,30\\,\\%", "17\\,690"]
    assert h[0].linea == 6


def test_cifras_es_varias_fuentes_y_errores(tmp_path):
    a = _md(tmp_path, "0,542\n", "a.md")
    b = _md(tmp_path, "46,50\n", "b.md")
    tex = _tex(tmp_path, "0,542 y 46,50.")
    assert ha.chequeo_cifras_es(tex, [a, b]) == []
    assert _formas(ha.chequeo_cifras_es(tex, [a])) == ["46,50"]
    with pytest.raises(FileNotFoundError):
        ha.chequeo_cifras_es(tex, [tmp_path / "no.md"])
    malo = tmp_path / "malo.csv"
    malo.write_text("clave,otra\nx,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ha.chequeo_cifras_es(tex, [malo])


# ── similitud ─────────────────────────────────────────────────────────────
TEXTO = ("the peer-to-peer market leaves the community better off than "
         "individual selfgeneration and the collective scheme in all cases")


def test_similitud_identico_y_disjunto(tmp_path):
    ms = _tex(tmp_path, "The \\emph{peer-to-peer} market leaves the community better off "
                        "than individual self-generation, and the collective scheme, "
                        "in all cases \\cite{x}.")
    igual = tmp_path / "igual.txt"
    igual.write_text(TEXTO, encoding="utf-8")
    otro = tmp_path / "otro.txt"
    otro.write_text(" ".join(f"palabra{i}" for i in range(40)), encoding="utf-8")
    r = ha.similitud(ms, [igual, otro])
    assert r.por_fuente[str(igual)] == pytest.approx(100.0)
    assert r.por_fuente[str(otro)] == pytest.approx(0.0)
    assert r.union == pytest.approx(100.0)
    assert ha.main(["similitud", str(ms), str(igual)]) == 1
    assert ha.main(["similitud", str(ms), str(otro)]) == 0


def test_similitud_rango_de_lineas(tmp_path):
    ms = _tex(tmp_path, TEXTO)
    fuente = tmp_path / "tesis.md"
    fuente.write_text("uno dos tres cuatro cinco seis siete ocho nueve\n" + TEXTO + "\n",
                      encoding="utf-8")
    r = ha.similitud(ms, [f"{fuente}:1-1"])
    assert r.union == pytest.approx(0.0)
    r = ha.similitud(ms, [f"{fuente}:2-2"])
    assert r.union == pytest.approx(100.0)


# ── dois ──────────────────────────────────────────────────────────────────
BIB = r"""
@article{Buena,
  title = {An optimal peer-to-peer market in energy communities:
           A game-theoretic approach with replicator dynamics},
  doi   = {10.1016/j.segan.2025.102114}
}
@article{Mala,
  title = {Peer-to-peer energy trading in {Colombia}},
  doi   = {https://doi.org/10.9999/otro}
}
@misc{Norma,
  title = {Resolucion CREG 101 072},
  url   = {https://creg.gov.co}
}
@misc{Norma2,
  title = {Resolucion CREG 174},
  note  = {\url{https://gestornormativo.creg.gov.co}, accessed 27 July 2026}
}
@misc{Huerfana,
  title = {Sin nada}
}
"""


def test_dois_con_red_sustituida(tmp_path, monkeypatch):
    bib = tmp_path / "r.bib"
    bib.write_text(BIB, encoding="utf-8")
    titulos = {
        "10.1016/j.segan.2025.102114": "An optimal peer-to-peer market in energy "
        "communities: A game-theoretic approach with replicator dynamics",
        "10.9999/otro": "Deep learning for image segmentation",
    }
    monkeypatch.setattr(ha, "consulta_crossref", lambda doi: titulos.get(doi))
    r = ha.verifica_dois(bib)
    estado = {e.clave: e.ok for e in r}
    assert estado == {"Buena": True, "Mala": False, "Norma": True, "Norma2": True,
                      "Huerfana": False}
    assert ha.main(["dois", str(bib)]) == 1


def test_dois_fallo_de_red_es_fallo(tmp_path, monkeypatch):
    bib = tmp_path / "r.bib"
    bib.write_text("@article{A, title={X y z}, doi={10.1/a}}\n", encoding="utf-8")

    def cae(doi):
        raise OSError("sin red")

    monkeypatch.setattr(ha, "consulta_crossref", cae)
    r = ha.verifica_dois(bib)
    assert [e.ok for e in r] == [False]
    assert "sin red" in r[0].motivo
    assert ha.main(["dois", str(bib)]) == 1


@pytest.mark.parametrize("latex", [
    r"Optimizaci{\'o}n de costos con din{\'a}micas en Espa{\~n}a y M{\"u}nster",
    r"Optimizaci\'{o}n de costos con din\'amicas en Espa\~{n}a y M\"{u}nster",
    r"Optimizaci\'on de costos con din{\'a}micas en Espa\~na y M{\"u}nster",
    r"Optimizaci{\'o}n de costos con din{\'{a}}micas en Espa{\~{n}}a y M{\"{u}}nster",
])
def test_normaliza_titulo_quita_acentos_latex(latex):
    """Tarea 4, ronda 1: un acento LaTeX de símbolo seguido de letra ({\\'o})
    partía la palabra en dos y el título igual al de Crossref fallaba."""
    utf8 = "Optimización de costos con dinámicas en España y Münster"
    assert ha.jaccard(ha.normaliza_titulo(latex), ha.normaliza_titulo(utf8)) == 1.0


def test_normaliza_titulo_acentos_de_letra_e_i_sin_punto():
    assert ha.normaliza_titulo(r"Gon{\c{c}}alves y Garc{\'\i}a y \v{S}koda") == \
        ha.normaliza_titulo("Gonçalves y García y Škoda")


def test_dois_todo_bien_sale_cero(tmp_path, monkeypatch):
    bib = tmp_path / "r.bib"
    bib.write_text("@article{A, title={Game {T}heory and markets}, doi={10.1/a}}\n",
                   encoding="utf-8")
    monkeypatch.setattr(ha, "consulta_crossref", lambda d: "Game theory and <i>markets</i>")
    assert ha.main(["dois", str(bib)]) == 0


def test_dois_tesis_sin_doi_ni_url_se_permite(tmp_path, monkeypatch, capsys):
    """Tarea 6, ronda 1: una @mastersthesis o @phdthesis sin DOI ni URL se
    lista como permitida y no hace fallar `dois`; cualquier otro tipo sí."""
    bib = tmp_path / "r.bib"
    bib.write_text(
        "@mastersthesis{M, author={A. B}, title={Una tesis}, school={U}, year={2026}}\n"
        "@PhDThesis{D, author={C. D}, title={Otra}, school={U}, year={2020}}\n",
        encoding="utf-8")

    def no_llamar(doi):
        raise AssertionError("una tesis sin DOI no consulta Crossref")

    monkeypatch.setattr(ha, "consulta_crossref", no_llamar)
    r = ha.verifica_dois(bib)
    assert [(e.clave, e.ok, e.motivo) for e in r] == [
        ("M", True, "tesis sin DOI (permitido)"),
        ("D", True, "tesis sin DOI (permitido)")]
    assert ha.main(["dois", str(bib)]) == 0
    assert "tesis sin DOI (permitido)" in capsys.readouterr().out
    bib.write_text("@techreport{T, title={Informe}, year={2026}}\n", encoding="utf-8")
    assert ha.main(["dois", str(bib)]) == 1


def test_dois_libro_con_isbn_sin_doi_ni_url_se_permite(tmp_path, monkeypatch, capsys):
    """Tesis de entrega, Tarea 1, ronda 1: un @book sin DOI ni URL pero con
    `isbn` se lista como permitido y no hace fallar `dois`; sin ISBN, o si el
    tipo no es @book aunque lleve ISBN, sigue fallando."""
    bib = tmp_path / "r.bib"
    bib.write_text(
        "@book{L, author={A. B}, title={Un libro}, publisher={P}, year={2010},\n"
        "  isbn={978-0-262-19587-4}}\n"
        "@Book{K, author={C. D}, title={Otro}, publisher={P}, year={1912}, ISBN={978-1-2345-6789-7}}\n",
        encoding="utf-8")

    def no_llamar(doi):
        raise AssertionError("un libro sin DOI no consulta Crossref")

    monkeypatch.setattr(ha, "consulta_crossref", no_llamar)
    r = ha.verifica_dois(bib)
    assert [(e.clave, e.ok, e.motivo) for e in r] == [
        ("L", True, "libro con ISBN (permitido)"),
        ("K", True, "libro con ISBN (permitido)")]
    assert ha.main(["dois", str(bib)]) == 0
    assert "libro con ISBN (permitido)" in capsys.readouterr().out
    bib.write_text("@book{S, title={Sin ISBN}, publisher={P}, year={2010}}\n", encoding="utf-8")
    assert ha.main(["dois", str(bib)]) == 1
    bib.write_text("@article{A, title={Art}, journal={J}, year={2010}, isbn={978-0-262-19587-4}}\n",
                   encoding="utf-8")
    assert ha.main(["dois", str(bib)]) == 1


def test_dois_manuscrito_sin_doi_ni_url_se_permite(tmp_path, monkeypatch, capsys):
    """Tesis de entrega, Tarea 4, ronda 1: un @unpublished sin DOI ni URL se
    lista como «manuscrito (permitido)» y no hace fallar `dois`; un @misc sin
    DOI ni URL sigue fallando aunque su nota diga «Manuscrito»."""
    bib = tmp_path / "r.bib"
    bib.write_text(
        "@unpublished{U, author={S. Ch}, title={Energy management system}, year={2025},\n"
        "  note={Manuscrito}}\n"
        "@Unpublished{V, author={A. B}, title={Otro manuscrito}, year={2024}, note={Manuscrito}}\n",
        encoding="utf-8")

    def no_llamar(doi):
        raise AssertionError("un manuscrito sin DOI no consulta Crossref")

    monkeypatch.setattr(ha, "consulta_crossref", no_llamar)
    r = ha.verifica_dois(bib)
    assert [(e.clave, e.ok, e.motivo) for e in r] == [
        ("U", True, "manuscrito (permitido)"),
        ("V", True, "manuscrito (permitido)")]
    assert ha.main(["dois", str(bib)]) == 0
    assert "manuscrito (permitido)" in capsys.readouterr().out
    bib.write_text("@misc{M, title={Manuscrito}, year={2025}, note={Manuscrito}}\n",
                   encoding="utf-8")
    assert ha.main(["dois", str(bib)]) == 1


def test_dois_fuente_interna_sin_doi_ni_url_se_permite(tmp_path, monkeypatch, capsys):
    """Tesis de entrega, ronda del jurado (I-10): un @techreport o un @misc
    sin DOI ni URL cuya `note` lo declara interno se lista como «fuente interna
    (permitido)»; sin `note`, con una `note` que no lo declara o con otro tipo,
    sigue fallando."""
    bib = tmp_path / "r.bib"
    bib.write_text(
        "@techreport{T, author={P. F}, title={Informe 4}, institution={U}, year={2026},\n"
        "  note={Documento interno del proyecto (fuente interna)}}\n"
        "@Misc{C, author={S. Ch}, title={C{\\'o}digo}, year={2025},\n"
        "  note={Facilitado por la autora; no publicado (Fuente Interna)}}\n",
        encoding="utf-8")

    def no_llamar(doi):
        raise AssertionError("una fuente interna sin DOI no consulta Crossref")

    monkeypatch.setattr(ha, "consulta_crossref", no_llamar)
    r = ha.verifica_dois(bib)
    assert [(e.clave, e.ok, e.motivo) for e in r] == [
        ("T", True, "fuente interna (permitido)"),
        ("C", True, "fuente interna (permitido)")]
    assert ha.main(["dois", str(bib)]) == 0
    assert "fuente interna (permitido)" in capsys.readouterr().out
    for mala in ("@techreport{T, title={Informe}, year={2026}}\n",
                 "@misc{M, title={Dato}, year={2026}, note={Archivado en el repositorio}}\n",
                 "@article{A, title={Art}, journal={J}, year={2026}, note={fuente interna}}\n",
                 "@misc{N, title={Dato}, year={2026}, note={Internacional}}\n"):
        bib.write_text(mala, encoding="utf-8")
        assert ha.main(["dois", str(bib)]) == 1, mala


# ── vetadas en inglés ─────────────────────────────────────────────────────
def test_vetadas_ingles_detecta_rango_y_no_35_kw(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("covering 35 to 89 % of the energy\n"
                 "a plant of 35 kW\n", encoding="utf-8")
    h = cv.revisa_ingles(f)
    assert [(n, v.aviso) for n, v, _ in h] == [(1, False)]
    assert cv.main(["--ingles", str(f)]) == 1


def test_vetadas_ingles_patrones_y_avisos(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("hours reached by the dynamics\n"          # 1
                 "a bootstrap interval\n"                    # 2
                 "the M3 meter and hourly C4\n"              # 3
                 "since C2 = C3\n"                           # 4
                 "the Stackelberg equilibrium structure\n"   # 5: sin aviso
                 "the Stackelberg equilibrium is unique\n"   # 6: aviso
                 "the exemption from network charges\n"      # 7: aviso
                 "Decree 3087 of 1997\n"                     # 8
                 "see entrega_gsa_directo_2026-09-27/\n"     # 9
                 "see entrega_gsa_directo_completo_2026-09-27/\n"  # 10: vale
                 "35--89\\,\\% % vetada-ok: historia\n",     # 11: exceptuada
                 encoding="utf-8")
    h = cv.revisa_ingles(f)
    lineas = sorted({n for n, _, _ in h})
    assert lineas == [1, 2, 3, 4, 6, 7, 8, 9]
    avisos = sorted({n for n, v, _ in h if v.aviso})
    assert avisos == [6, 7]


@pytest.mark.parametrize("texto, aviso", [
    ("the hours reached by the\ndynamics are few\n", False),
    ("no verified\nregime exists\n", False),
    ("the Stackelberg\nequilibrium is unique\n", True),
])
def test_vetadas_ingles_frase_partida_por_salto(tmp_path, texto, aviso):
    f = tmp_path / "a.tex"
    f.write_text("intro\n" + texto, encoding="utf-8")
    h = cv.revisa_ingles(f)
    assert [(n, v.aviso) for n, v, _ in h] == [(2, aviso)]


def test_vetadas_ingles_partida_con_structure_y_excepcion(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("the Stackelberg\nequilibrium\nstructure holds\n"
                 "reached by the % vetada-ok: historia\ndynamics\n", encoding="utf-8")
    assert cv.revisa_ingles(f) == []


def test_vetadas_ingles_limites_de_palabra_en_35_89(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("from 135 to 89 % and 35 to 890 kW\n", encoding="utf-8")
    assert cv.revisa_ingles(f) == []


def test_vetadas_ingles_solo_avisos_sale_cero(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("the Stackelberg equilibrium is unique\n", encoding="utf-8")
    assert cv.main(["--ingles", str(f)]) == 0


# ── vetadas en español sobre un .tex (--fichero) ──────────────────────────
def test_vetadas_fichero_detecta_35_y_el_89_y_no_35_kw(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("una planta de 35 kW\n"                          # 1: vale
                 "entre el 35 y el 89 de la energía\n"            # 2
                 "entre el 35\\% y el\n89\\% de la energía\n"     # 3: partida
                 "del 35--89 por ciento\n"                        # 5
                 "del 135 al 890 por ciento\n"                    # 6: vale
                 "del 35 y el 89 % vetada-ok: historia\n",        # 7: exceptuada
                 encoding="utf-8")
    h = cv.revisa_tex_es(f)
    assert [n for n, _, _ in h] == [2, 3, 5]
    assert cv.main(["--fichero", str(f)]) == 1
    g = tmp_path / "b.tex"
    g.write_text("una planta de 35 kW y 89 horas\n", encoding="utf-8")
    assert cv.revisa_tex_es(g) == []
    assert cv.main(["--fichero", str(g)]) == 0


def test_vetadas_fichero_patrones_espanoles_y_avisos(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("un intervalo bootstrap\n"                  # 1
                 "la frontera M3\n"                           # 2
                 "el reparto por C4_mensual\n"                # 3
                 "horas alcanzadas por la\ndinámica\n"        # 4: partida
                 "ningún régimen verificado\n"                # 6
                 "el equilibrio de Stackelberg\n"             # 7: aviso
                 "la estructura del juego de Stackelberg\n"   # 8: vale
                 "el Decreto 3087 de 1997\n"                  # 9
                 "un 4,3\\,\\% de precio\n"                   # 10: rompe babel
                 "una prima de 0,937\n",                      # 11
                 encoding="utf-8")
    h = cv.revisa_tex_es(f)
    assert sorted({n for n, _, _ in h}) == [1, 2, 3, 4, 6, 7, 9, 10, 11]
    assert sorted({n for n, v, _ in h if v.aviso}) == [7]
    solo_aviso = tmp_path / "b.tex"
    solo_aviso.write_text("el equilibrio de Stackelberg\n", encoding="utf-8")
    assert cv.main(["--fichero", str(solo_aviso)]) == 0


def test_vetadas_fichero_sin_ruta_es_uso_incorrecto():
    assert cv.main(["--fichero"]) == 2


def test_vetadas_sin_ingles_conserva_el_uso(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("una cobertura del 35 al 89 %\nsin nada\n", encoding="utf-8")
    assert cv.main([str(f)]) == 1
    g = tmp_path / "b.md"
    g.write_text("hours reached by the dynamics\n", encoding="utf-8")
    assert cv.main([str(g)]) == 0
