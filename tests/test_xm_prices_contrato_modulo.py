"""
Lo que el modulo de la plataforma MTE importa de `data/xm_prices.py` (tarea P,
commit P1; informe del modulo del 2026-09-17, defectos 2 a 6). Actividad 4.2.

El modulo fijo el nucleo sobre 05ed9c3 y llama a dos funciones:

  - `apply_creg101066_ceiling(np.full(24, p), "YYYY-MM-DD", level="PES",
    csv_path=<tabla de UNA fila con ese mes>)` en cada hora que resuelve;
  - `get_b_for_real_data(N, nombres)` con los cinco nombres canonicos.

INVARIANTE DEL AVISO AL MODULO. Con esas dos llamadas, el resultado tiene que
ser el MISMO AL BIT que el de 05ed9c3. Se comprueba de dos formas:
  - contra literales hexadecimales sacados una vez de 05ed9c3 (corren siempre);
  - contra 05ed9c3 cargado como modulo aparte con `git show` (se saltan, con el
    motivo, donde no hay historia de git).

Lo demas son los defectos del informe: el final del horizonte truncado (2),
los meses inventados fuera de la tabla (3), los nombres que caian al valor por
defecto y el relleno sin ajustar (4a, 4b, 4d), la serie con NaN (5) y la fecha
con zona (6). Ninguna prueba toca datos reales ni escribe en `outputs/`.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from data.xm_prices import (  # noqa: E402
    B_CALIBRATED,
    INVERTER_BY_AGENT,
    apply_creg101066_ceiling,
    calibrate_b_parameters,
    get_b_for_real_data,
    load_creg_ceiling,
)

COMMIT_MODULO = "05ed9c3"
CINCO = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
TABLA = RAIZ / "data" / "precios_escasez_creg.csv"
CABECERA = "mes,pei_cop_kwh,pe_cop_kwh,pes_cop_kwh,fuente,nota\n"

# get_b_for_real_data(5, CINCO) en 05ed9c3, al bit.
B_05ED9C3_HEX = ["0x1.e224924924924p+7"] * 4 + ["0x1.c200000000000p+7"]

# El techo superior (PES) de la tabla de la tesis, en los meses que usan las
# pruebas de abajo. Solo estas cifras dependen del contenido de la tabla.
PES = {"2025-04": 928.33, "2025-05": 891.22, "2025-06": 858.79,
       "2025-11": 829.00, "2025-12": 864.91, "2026-01": 830.34}
PEI_ABR_JUN = [336.12, 338.54, 345.38]
PE_ABR_JUN = [739.80, 724.31, 673.74]

# Filas de UNA sola fila como las escribe el modulo con su propia tabla
# (`mercado.tope_creg`): son suyas, no de la tesis, y no cambian cuando cambia
# la tabla de la tesis. La de mayo de 2026 es de un mes que la tabla de la
# tesis no tiene, con un valor de precision completa.
FILAS_MODULO = {
    "2025-07": (350.08, 699.17, 865.22),
    "2025-11": (332.00, 659.00, 829.00),
    "2025-12": (329.43, 625.20, 864.91),
    "2026-01": (327.67, 590.56, 830.34),
    "2026-05": (321.12345, 601.54321, 812.98765),
}


# ─── 05ed9c3 como modulo aparte ─────────────────────────────────────────────

def _git_show(ruta: str) -> str | None:
    try:
        r = subprocess.run(["git", "show", f"{COMMIT_MODULO}:{ruta}"],
                           cwd=str(RAIZ), capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8")


@pytest.fixture(scope="module")
def viejo(tmp_path_factory):
    """El modulo xm_prices de 05ed9c3, cargado aparte."""
    fuente = _git_show("data/xm_prices.py")
    if fuente is None:
        pytest.skip(f"sin historia de git para {COMMIT_MODULO}: la "
                    f"comparacion al bit la cubren los literales")
    d = tmp_path_factory.mktemp("xm_prices_05ed9c3")
    (d / "xm_prices_05ed9c3.py").write_text(fuente, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "xm_prices_05ed9c3", d / "xm_prices_05ed9c3.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _una_fila(tmp_path, mes: str) -> str:
    """Tabla de una sola fila con ese mes, como la escribe el modulo."""
    pei, pe, pes = FILAS_MODULO[mes]
    ruta = tmp_path / f"tope_{mes}.csv"
    ruta.write_text(CABECERA + f"{mes},{pei},{pe},{pes},modulo,una fila\n",
                    encoding="utf-8")
    return str(ruta)


def _al_bit(a, b) -> bool:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return a.shape == b.shape and a.tobytes() == b.tobytes()


# ─── El invariante: lo que ve el modulo, al bit ─────────────────────────────

def test_b_de_las_cinco_al_bit_contra_los_literales():
    b = get_b_for_real_data(5, CINCO)
    assert b.dtype == np.float64 and b.shape == (5,)
    assert _al_bit(b, [float.fromhex(h) for h in B_05ED9C3_HEX])


def test_b_de_las_cinco_al_bit_contra_05ed9c3(viejo):
    mod = viejo
    for nombres in (CINCO, CINCO[1:], ["Cesmag"], ["UCC", "Udenar"]):
        n = len(nombres)
        assert _al_bit(get_b_for_real_data(n, list(nombres)),
                       mod.get_b_for_real_data(n, list(nombres))), nombres


# Las filas del modulo: dia 1 y ultimo dia, un precio bajo el tope, uno
# encima y el tope exacto.
MESES_MODULO = list(FILAS_MODULO)


def _dias(mes: str):
    p = pd.Period(mes, freq="M")
    return [p.start_time.strftime("%Y-%m-%d"), p.end_time.strftime("%Y-%m-%d")]


@pytest.mark.parametrize("mes", MESES_MODULO)
def test_llamada_exacta_del_modulo_al_bit_contra_05ed9c3(viejo, tmp_path, mes):
    mod = viejo
    csv = _una_fila(tmp_path, mes)
    tope = FILAS_MODULO[mes][2]
    for dia in _dias(mes):
        for p in (150.0, 1000.0, tope, 2224.00946):
            nuevo = apply_creg101066_ceiling(np.full(24, float(p)), dia,
                                             level="PES", csv_path=csv)
            antes = mod.apply_creg101066_ceiling(np.full(24, float(p)), dia,
                                                 level="PES", csv_path=csv)
            assert _al_bit(nuevo, antes), (mes, dia, p)
            assert _al_bit(nuevo, np.full(24, min(p, tope))), (mes, dia, p)


def test_24_horas_desde_medianoche_con_la_tabla_entera_al_bit(viejo):
    """Cada dia de la tabla de la tesis, la MISMA tabla para las dos versiones.

    Prueba el codigo, no los datos: cuando la tabla cambia de valores, las dos
    versiones siguen dando lo mismo con ella.
    """
    mod = viejo
    rng = np.random.default_rng(20260918)
    for dia in pd.date_range("2025-04-01", "2026-01-31", freq="D"):
        pi = np.concatenate([rng.uniform(50.0, 1500.0, 23), [2224.00946]])
        d = dia.strftime("%Y-%m-%d")
        nuevo = apply_creg101066_ceiling(pi, d, level="PES")
        antes = mod.apply_creg101066_ceiling(pi, d, level="PES",
                                             csv_path=str(TABLA))
        assert _al_bit(nuevo, antes), d


def test_llamada_exacta_del_modulo_contra_literales(tmp_path):
    """Sin git: el tope de cada mes es el de su fila, y bajo el tope nada cambia."""
    for mes, (_, _, tope) in FILAS_MODULO.items():
        csv = _una_fila(tmp_path, mes)
        for dia in _dias(mes):
            assert _al_bit(apply_creg101066_ceiling(
                np.full(24, 1000.0), dia, level="PES", csv_path=csv),
                np.full(24, tope))
            assert _al_bit(apply_creg101066_ceiling(
                np.full(24, 150.0), dia, level="PES", csv_path=csv),
                np.full(24, 150.0))


# ─── Defecto 2: el final del horizonte ──────────────────────────────────────

@pytest.mark.parametrize("T, t_start, dt, esperado", [
    (1, "2025-12-01", 1.0, [PES["2025-12"]]),
    (23, "2025-12-01", 1.0, [PES["2025-12"]] * 23),
    (6, "2025-12-01 13:00", 1.0, [PES["2025-12"]] * 6),
    (24, "2025-11-30 12:00", 1.0, [PES["2025-11"]] * 12 + [PES["2025-12"]] * 12),
    (24, "2025-12-01", 1.0, [PES["2025-12"]] * 24),
    (96, "2025-12-01", 0.25, [PES["2025-12"]] * 96),
])
def test_defecto_2_los_seis_casos_del_informe(T, t_start, dt, esperado):
    r = apply_creg101066_ceiling(np.full(T, 1000.0), t_start, dt=dt)
    assert _al_bit(r, esperado)


def test_defecto_2_horizonte_vacio_es_error_claro():
    with pytest.raises(ValueError, match="vacia"):
        apply_creg101066_ceiling(np.array([]), "2025-12-01")
    with pytest.raises(ValueError, match="Horizonte vacio"):
        load_creg_ceiling("2025-12-01 05:00", "2025-12-01 05:00")


def test_defecto_2_load_creg_ceiling_con_final_exclusivo_y_con_hora():
    assert list(load_creg_ceiling("2025-12-01", "2025-12-01 01:00").index) \
        == [pd.Period("2025-12", "M")]
    assert list(load_creg_ceiling("2025-07-01", "2026-02-01").index) \
        == list(pd.period_range("2025-07", "2026-01", freq="M"))


# ─── Defecto 3: nada fuera de la tabla ──────────────────────────────────────

def test_defecto_3_la_tabla_cubre_el_horizonte_de_la_tesis():
    """Abril a junio de 2025, del API de XM (PrecEscaInf, PrecEsca, PrecEscaSup)."""
    s = load_creg_ceiling("2025-04-04", "2025-12-16", level="PES")
    for mes in ("2025-04", "2025-05", "2025-06"):
        assert s.loc[pd.Period(mes, "M")] == PES[mes]
    assert load_creg_ceiling("2025-04-01", "2025-07-01", level="PEI").tolist() \
        == PEI_ABR_JUN
    assert load_creg_ceiling("2025-04-01", "2025-07-01", level="PE").tolist() \
        == PE_ABR_JUN


@pytest.mark.parametrize("t_start", ["2025-03-10", "2026-03-10", "2026-02-01"])
def test_defecto_3_un_mes_fuera_de_la_tabla_es_error(t_start):
    with pytest.raises(ValueError, match="no esta publicado"):
        apply_creg101066_ceiling(np.full(24, 1000.0), t_start)


def test_defecto_3_la_llamada_del_modulo_con_otro_mes_es_error(tmp_path):
    csv = _una_fila(tmp_path, "2025-11")
    with pytest.raises(ValueError, match="no esta publicado"):
        apply_creg101066_ceiling(np.full(24, 1000.0), "2025-12-01",
                                 level="PES", csv_path=csv)


def _tabla_con_hueco(tmp_path) -> str:
    csv = tmp_path / "hueco.csv"
    csv.write_text(CABECERA
                   + "2025-07,350.0,700.0,800.0,t,jul\n"
                   + "2025-10,380.0,760.0,830.0,t,oct\n", encoding="utf-8")
    return str(csv)


def test_defecto_3_el_hueco_interior_se_interpola_igual_se_pida_como_se_pida(
        tmp_path):
    """Agosto y septiembre no estan en el fichero: 810 y 820, pidan lo que pidan."""
    csv = _tabla_con_hueco(tmp_path)
    solo_ago = load_creg_ceiling("2025-08-01", "2025-09-01", csv_path=csv)
    ago_sep = load_creg_ceiling("2025-08-01", "2025-10-01", csv_path=csv)
    assert solo_ago.loc[pd.Period("2025-08", "M")] == pytest.approx(810.0)
    assert ago_sep.loc[pd.Period("2025-08", "M")] == pytest.approx(810.0)
    assert ago_sep.loc[pd.Period("2025-09", "M")] == pytest.approx(820.0)


def test_defecto_3_diag_dice_que_meses_son_de_la_tabla(tmp_path):
    csv = _tabla_con_hueco(tmp_path)
    T = 24 * (31 + 31 + 30 + 31)
    _, diag = apply_creg101066_ceiling(np.full(T, 1000.0), "2025-07-01",
                                       csv_path=csv, return_diagnostics=True)
    assert diag["meses_tabla"] == ["2025-07", "2025-10"]
    assert diag["meses_interpolados"] == ["2025-08", "2025-09"]
    _, diag = apply_creg101066_ceiling(np.full(24, 1000.0), "2025-12-01",
                                       return_diagnostics=True)
    assert diag["meses_tabla"] == ["2025-12"]
    assert diag["meses_interpolados"] == []


# ─── Defecto 4: el vector b ─────────────────────────────────────────────────

def test_defecto_4a_un_nombre_desconocido_es_error():
    with pytest.raises(ValueError, match="sin inversor conocido"):
        get_b_for_real_data(5, [n.lower() for n in CINCO])
    with pytest.raises(ValueError, match="Agente 1"):
        get_b_for_real_data(2, ["Udenar", "Agente 1"])


def test_defecto_4a_el_b_de_cesmag_difiere_del_resto():
    b = get_b_for_real_data(5, CINCO)
    assert len(set(b[:4].tolist())) == 1 and b[4] != b[0]


def test_defecto_4b_el_relleno_lleva_el_mismo_ajuste():
    b = get_b_for_real_data(7, CINCO)
    adj = b[0] / B_CALIBRATED["Udenar_fronius"]
    assert b[5] == b[6] == B_CALIBRATED["default_pasto"] * adj
    assert _al_bit(b[:5], get_b_for_real_data(5, CINCO))


def test_defecto_4c_el_docstring_dice_lo_que_devuelve():
    doc = calibrate_b_parameters.__doc__
    assert "241,07 × 4; 225,00" in doc
    assert get_b_for_real_data(5, CINCO).round(2).tolist() \
        == [241.07] * 4 + [225.0]


def test_defecto_4d_capacity_kw_ya_no_se_acepta():
    with pytest.raises(TypeError):
        calibrate_b_parameters(CINCO, capacity_kw=[10.0] * 5)
    with pytest.raises(TypeError):
        calibrate_b_parameters(CINCO, [10.0] * 5)


def test_inverter_by_agent_nombra_los_cinco():
    assert list(INVERTER_BY_AGENT) == CINCO
    assert all(v in B_CALIBRATED for v in INVERTER_BY_AGENT.values())


# ─── Defecto 5: la serie de bolsa ───────────────────────────────────────────

@pytest.mark.parametrize("malo", [np.nan, np.inf, -np.inf])
def test_defecto_5_una_serie_no_finita_es_error(malo):
    pi = np.full(24, 200.0)
    pi[7] = malo
    with pytest.raises(ValueError, match="no finitos"):
        apply_creg101066_ceiling(pi, "2025-12-01")
    with pytest.raises(ValueError, match="no finitos"):
        apply_creg101066_ceiling(np.full(24, np.nan), "2025-12-01")


# ─── Defecto 6: la hora local ───────────────────────────────────────────────

def test_defecto_6_una_fecha_sin_zona_no_se_reinterpreta():
    """23:00 del ultimo dia del mes, sin zona: tope de ese mes, no del siguiente."""
    assert _al_bit(apply_creg101066_ceiling(np.full(1, 1000.0),
                                            "2025-11-30 23:00"), [PES["2025-11"]])
    assert _al_bit(apply_creg101066_ceiling(np.full(1, 1000.0),
                                            "2026-01-31 23:00"), [PES["2026-01"]])


def test_defecto_6_una_fecha_con_zona_se_convierte_a_bogota():
    # 04:00 UTC del 1 de diciembre son las 23:00 del 30 de noviembre en Bogota.
    r = apply_creg101066_ceiling(np.full(2, 1000.0),
                                 "2025-12-01T04:00:00+00:00")
    assert _al_bit(r, [PES["2025-11"], PES["2025-12"]])
    r = apply_creg101066_ceiling(np.full(1, 1000.0),
                                 pd.Timestamp("2025-12-01", tz="America/Bogota"))
    assert _al_bit(r, [PES["2025-12"]])
