"""Pruebas del caso de la autora repetido con el tope suficiente (CA,
2026-10-07): las especificaciones de `medicion_autora.py` son las de M-G
(`medicion_chacon.py`) salvo el tope, el brazo k = 1 000 y la ausencia del
brazo k = 1, y el juicio que les aplica `veredicto.py` es el de M-G.
Actividad 1.1. Sin corridas; segundos.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CONSENSO = RAIZ / "reformateo" / "documento" / "scripts" / "sonda" / "consenso"
for _p in (RAIZ, CONSENSO.parent, CONSENSO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import medicion_autora as MAU                         # noqa: E402
import medicion_chacon as MG                          # noqa: E402


def test_ca_son_las_especificaciones_de_m_g_con_otro_tope(monkeypatch):
    monkeypatch.delenv("AUTORA_TOPE_S", raising=False)
    sp = MAU.specs()
    assert [(s["fecha"], s["familia"], s["var"]["k_lento"]) for s in sp] == [
        (h, f, k) for h, f, k in MAU.ORDEN]
    assert len(sp) == 8 and all(s["medicion"] == "M-G" for s in sp)
    assert not any(s["var"]["k_lento"] == 1.0 for s in sp)
    assert all(s["tope"] == 25200.0 for s in sp)
    assert all(s["cortes"][-1] * s["var"]["k_lento"] == pytest.approx(160.0)
               for s in sp)
    # Las de k = 100 son las de M-G, campo por campo, salvo el tope.
    mg = {(s["fecha"], s["familia"]): s for s in MG.specs()
          if s["var"]["k_lento"] == 100.0}
    for s in sp:
        if s["var"]["k_lento"] != 100.0:
            continue
        ref = dict(mg[(s["fecha"], s["familia"])])
        assert ref["tope"] == 3600.0
        ref.pop("tope")
        assert {k: v for k, v in s.items() if k != "tope"} == ref
    # Las de k = 1 000, las mismas salvo k y sus cortes (los de M-A2).
    import medicion_ampliada as MA
    for s in sp:
        if s["var"]["k_lento"] == 1000.0:
            assert s["cortes"] == MA.CORTES[1000.0]
            ref = mg[(s["fecha"], s["familia"])]
            assert {k: v for k, v in s["var"].items() if k != "k_lento"} == \
                {k: v for k, v in ref["var"].items() if k != "k_lento"}
            assert s["referencias"] == ref["referencias"]
    # El juicio que aplica veredicto.py es el de M-G.
    import veredicto as V
    assert V.GUIONES[MAU.MEDICION] == "medicion_chacon"
    monkeypatch.setenv("AUTORA_TOPE_S", "0")
    with pytest.raises(ValueError):
        MAU.specs()
