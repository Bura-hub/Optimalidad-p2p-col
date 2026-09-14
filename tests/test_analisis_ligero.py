"""D27: el modo ligero corre la factibilidad y no resuelve el mercado otra vez."""
import pytest


def test_el_modo_ligero_no_corre_los_barridos(monkeypatch, tmp_path):
    import analysis.sensitivity as S
    import analysis.subperiod as SP

    def _prohibido(*a, **k):
        raise AssertionError("el modo ligero no debe correr barridos")

    for nombre in ("run_sensitivity_pgb", "run_sensitivity_pv",
                   "run_sensitivity_pgs", "run_sensitivity_ppa"):
        monkeypatch.setattr(S, nombre, _prohibido)
    monkeypatch.setattr(SP, "run_subperiod_analysis", _prohibido)
    import main_simulation as ms
    ms.main(use_real_data=False, run_analysis=True, analisis_ligero=True,
            out_dir=str(tmp_path))
    assert any((tmp_path / "graficas").glob("fig14*"))
