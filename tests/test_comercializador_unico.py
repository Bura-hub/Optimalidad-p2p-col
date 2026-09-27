"""El contrafactico de un solo comercializador en el evaluador del GSA (A2,
H-97): `prepara_caso(..., comercializador=)`.

Actividad 2.2.

- con el defecto (None) la preparacion es la de siempre, al bit;
- con "asc" solo cambia Cesmag, y con "cedenar" solo las otras cuatro;
- el reparto real se restituye al salir, tambien si la preparacion falla, y
  la excepcion no se traga.

Las de datos reales usan un dia (`dia=`) y se saltan sin MedicionesMTE_v3.
"""
import os
import sys
from dataclasses import fields
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from gsa_directo import comun, evaluador  # noqa: E402

MTE = Path(os.environ.get("MTE_ROOT", RAIZ / "MedicionesMTE_v3"))
HAY_DATOS = MTE.is_dir() and any(MTE.iterdir())
DIA = "2025-08-01"
datos_reales = pytest.mark.skipif(not HAY_DATOS,
                                  reason="sin MedicionesMTE_v3")


def _reparto():
    from data.cedenar_tariff import INSTITUTION_PROFILE
    return {k: v.comercializador for k, v in INSTITUTION_PROFILE.items()}


def _reparto_real_no_regulado():
    from data.cedenar_tariff import INSTITUTION_PROFILE, _PERFIL_NO_REGULADO
    return dict(INSTITUTION_PROFILE) == _PERFIL_NO_REGULADO


def _datos_sinteticos(T=24):
    idx = pd.date_range("2025-08-01", periods=T, freq="h",
                        tz="America/Bogota")
    return (np.full((5, T), 10.0), np.full((5, T), 5.0), idx)


def test_restituye_el_reparto_si_la_preparacion_falla(monkeypatch):
    import data.escalado as escalado
    visto = {}

    def revienta(*a, **k):
        visto["reparto"] = _reparto()
        raise RuntimeError("fallo a proposito")

    monkeypatch.setattr(escalado, "escala_comunidad", revienta)
    with pytest.raises(RuntimeError, match="fallo a proposito"):
        evaluador.prepara_caso("E0", _datos_sinteticos(),
                               comercializador="cedenar")
    # Durante la preparacion, las cinco estaban con CEDENAR ...
    assert set(visto["reparto"].values()) == {"cedenar"}
    # ... y al salir, con la excepcion propagada, vuelve el reparto real.
    assert _reparto_real_no_regulado()


def test_comercializador_desconocido_falla_y_deja_el_reparto_real():
    with pytest.raises(ValueError):
        evaluador.prepara_caso("E0", _datos_sinteticos(),
                               comercializador="epm")
    assert _reparto_real_no_regulado()


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    if not HAY_DATOS:
        pytest.skip("sin MedicionesMTE_v3")
    return evaluador.carga_mte(str(MTE),
                               tmp_path_factory.mktemp("cache_mte"))


def _iguales(a, b) -> bool:
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return (a is None) == (b is None) and np.array_equal(
            np.asarray(a), np.asarray(b))
    return a == b


@datos_reales
def test_el_defecto_no_cambia_nada(datos):
    antes = evaluador.prepara_caso("E0", datos, dia=DIA)
    con_none = evaluador.prepara_caso("E0", datos, dia=DIA,
                                      comercializador=None)
    for f in fields(evaluador.Insumos):
        assert _iguales(getattr(antes, f.name), getattr(con_none, f.name)), \
            f.name
    assert antes.comercializador is None
    assert _reparto_real_no_regulado()


@datos_reales
def test_forzar_mueve_solo_a_quien_cambia_de_comercializador(datos):
    real = evaluador.prepara_caso("E0", datos, dia=DIA)
    ces = real.nombres.index("Cesmag")
    otras = [i for i in range(real.N) if i != ces]
    for com, cambian, quedan in (("asc", [ces], otras),
                                 ("cedenar", otras, [ces])):
        ins = evaluador.prepara_caso("E0", datos, dia=DIA,
                                     comercializador=com)
        assert ins.comercializador == com
        assert _reparto_real_no_regulado()
        for serie in ("cvm", "pi_gs", "cu_Cvm", "cu_G"):
            a, b = getattr(real, serie), getattr(ins, serie)
            np.testing.assert_array_equal(a[quedan], b[quedan])
            assert not np.array_equal(a[cambian], b[cambian]), (com, serie)
        # T+D+PR+R: T y D los fija el operador de red, pero PR y R vienen en
        # la tabla de cada comercializador (H-97); los que no cambian de
        # comercializador conservan los suyos.
        np.testing.assert_array_equal(real.tolls[quedan], ins.tolls[quedan])
        # Con un solo comercializador, las cinco comparten Cv.
        assert np.ptp(ins.cvm, axis=0).max() == 0.0
    # Y lo que se prepara despues vuelve a ser el canon.
    otra = evaluador.prepara_caso("E0", datos, dia=DIA)
    np.testing.assert_array_equal(otra.cvm, real.cvm)
    np.testing.assert_array_equal(otra.pi_gs, real.pi_gs)
