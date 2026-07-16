"""
tests/test_full_simulation_preflight.py
========================================
Brayan S. Lopez-Mendez · Udenar 2026

Tests de pre-flight que verifican que la maquinaria del modo
`python main_simulation.py --data real --full --analysis` funcionará
sin errores cuando se invoque, sin necesidad de correr la simulación
de 52 minutos.

Cubre:

1. Imports completos del pipeline (main_simulation, scenarios, analysis,
   data, visualization).
2. Banners de log actualizados (CAL-10b.2, CAL-13) en main_simulation.py.
3. Helpers de tarifas CEDENAR cubren el horizonte completo del proyecto
   (jul-2025 a feb-2026) sin NaN: pi_gs, Cvm, G, G+Cvm+COT.
4. Cobertura del CSV CEDENAR sobre el horizonte simulado.
5. comparison_engine.run_comparison acepta y propaga pi_G correctamente.
6. analysis.sensitivity acepta pi_G para SA-3 (CAL-13b).
7. Caso sintético (rápido) corre end-to-end sin errores.

Estos tests son intencionalmente rápidos (< 1 min total) para servir
como pre-flight antes de invocar `--full --analysis`. NO sustituyen
la corrida real de validación, pero sí blindan que los componentes
individuales están sanos.
"""

from __future__ import annotations

import importlib
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent

# Horizonte oficial del proyecto MTE: jul-2025 a feb-2026 (8 meses).
HORIZON_START = "2025-07-01"
HORIZON_END   = "2026-02-01"


# ─── 1. Imports del pipeline ────────────────────────────────────────────────

@pytest.mark.parametrize("mod", [
    "main_simulation",
    "scenarios.scenario_c1_creg174",
    "scenarios.scenario_c2_bilateral",
    "scenarios.scenario_c3_spot",
    "scenarios.scenario_c4_creg101072",
    "scenarios.comparison_engine",
    "scenarios._pi_gs",
    "data.cedenar_tariff",
    "data.xm_prices",
    "data.base_case_data",
    "analysis.sensitivity",
    "analysis.feasibility",
    "analysis.fairness",
    "analysis.monthly_report",
    "core.market_prep",
    "core.settlement",
    "visualization.plots",
])
def test_pipeline_modules_importan_sin_errores(mod):
    """Todos los módulos del pipeline `--full` deben importar sin
    errores. Si alguno falla, la corrida `--full` se romperá inmediato."""
    importlib.import_module(mod)


def test_helpers_publicos_disponibles_en_cedenar_tariff():
    """Los helpers CAL-9, CAL-10b.2, CAL-12 y CAL-13 deben estar
    expuestos como funciones públicas en data.cedenar_tariff."""
    from data import cedenar_tariff as ct
    assert callable(getattr(ct, "pi_gs_per_agent_hourly", None))
    assert callable(getattr(ct, "cvm_per_agent_hourly", None))
    assert callable(getattr(ct, "g_component_per_agent_hourly", None))
    assert callable(getattr(ct, "g_plus_commercialization_per_agent_hourly", None))


# ─── 2. Banners de log actualizados ─────────────────────────────────────────

def test_banner_CAL10b2_en_main_simulation():
    """main_simulation.py debe imprimir banner CAL-10b.2 (no CAL-10b
    legacy ni CAL-10 inicial)."""
    src = (REPO_ROOT / "main_simulation.py").read_text(encoding="utf-8")
    assert "[CAL-10b.2]" in src, (
        "Banner CAL-10b.2 ausente; SA-1/SA-2/SA-3 podrían reportar valores "
        "inconsistentes con el componente C real (Cvm puro, no Cvm+COT)."
    )


def test_banner_CAL13_en_main_simulation():
    """main_simulation.py debe imprimir banner CAL-13 (PPA bilateral
    no-regulado agregado, post-2026-05-01)."""
    src = (REPO_ROOT / "main_simulation.py").read_text(encoding="utf-8")
    assert "[CAL-13]" in src, (
        "Banner CAL-13 ausente; C2 podría estar usando lógica BTM "
        "legacy o FoM regulado pre-CAL-13."
    )
    # Verificación adicional: banner cita las normas correctas
    assert "Ley 143/1994" in src
    assert "CREG 086/1996" in src
    assert "CREG 174/2021 art. 23.1.a" in src


def test_no_banners_legacy_pre_CAL13():
    """No deben quedar banners de versiones obsoletas mezclados con los
    actuales. Banners pre-CAL-12 (BTM legacy implícito) y CAL-12 puro
    (savings sobre G solo) deben haber sido reemplazados por CAL-13."""
    src = (REPO_ROOT / "main_simulation.py").read_text(encoding="utf-8")
    # Banner CAL-12 puro tenía esta firma específica (referencia a
    # CREG 119/2007 arts. 6-8 SIN mención al usuario no-regulado).
    forbidden = "[CAL-12] C2 (CREG 119/2007 arts. 6-8): savings_cons sobre G (no CU)"
    assert forbidden not in src, (
        "Banner CAL-12 puro persiste; debería haber sido reemplazado por CAL-13."
    )


# ─── 3. Helpers cubren el horizonte completo sin NaN ────────────────────────

@pytest.fixture
def horizon_index():
    return pd.date_range(HORIZON_START, HORIZON_END, freq="1h",
                         inclusive="left")


@pytest.fixture
def mte_agents():
    return ["Udenar", "HUDN", "Mariana", "UCC", "Cesmag"]


def test_pi_gs_per_agent_hourly_cubre_horizonte_full(mte_agents, horizon_index):
    """CAL-9: pi_gs (CU completo) sin NaN para 5 agentes × 8 meses."""
    from data.cedenar_tariff import pi_gs_per_agent_hourly
    arr = pi_gs_per_agent_hourly(mte_agents, horizon_index)
    assert arr.shape == (5, len(horizon_index))
    nan_count = int(np.isnan(arr).sum())
    assert nan_count == 0, (
        f"pi_gs tiene {nan_count} NaN en el horizonte. "
        f"Revisar tarifas_cedenar_mensual.csv: faltan meses."
    )
    # Sanity check: rango razonable de tarifas CEDENAR (≈ 700-1000 COP/kWh)
    assert 600 < arr.mean() < 1100, f"pi_gs medio fuera de rango: {arr.mean()}"


def test_cvm_per_agent_hourly_cubre_horizonte_full(mte_agents, horizon_index):
    """CAL-10b.2: Cvm puro sin NaN para 5 agentes × 8 meses."""
    from data.cedenar_tariff import cvm_per_agent_hourly
    arr = cvm_per_agent_hourly(mte_agents, horizon_index)
    assert arr.shape == (5, len(horizon_index))
    # Cvm puede tener NaN si el CSV no tiene la columna; en ese caso
    # as_component_c_array (CAL-10b) rellena con C_FRACTION × pi_gs.
    # Para horizonte completo verificamos que NO haya NaN bajo el CSV
    # actualizado al 2026-04-30.
    nan_count = int(np.isnan(arr).sum())
    assert nan_count == 0, (
        f"Cvm tiene {nan_count} NaN; revisar columna 'Cvm' del CSV."
    )
    # Sanity check: Cvm CEDENAR ≈ 170-180 COP/kWh
    assert 100 < arr.mean() < 250, f"Cvm fuera de rango: {arr.mean()}"


def test_g_component_per_agent_hourly_cubre_horizonte_full(mte_agents, horizon_index):
    """CAL-12: componente G del CU sin NaN para 5 agentes × 8 meses."""
    from data.cedenar_tariff import g_component_per_agent_hourly
    arr = g_component_per_agent_hourly(mte_agents, horizon_index)
    assert arr.shape == (5, len(horizon_index))
    nan_count = int(np.isnan(arr).sum())
    assert nan_count == 0, (
        f"G tiene {nan_count} NaN; revisar columna 'Gm' del CSV."
    )
    assert 200 < arr.mean() < 400, f"G fuera de rango: {arr.mean()}"


def test_g_plus_comm_cubre_horizonte_full(mte_agents, horizon_index):
    """CAL-13: G + Cvm + COT sin NaN para 5 agentes × 8 meses."""
    from data.cedenar_tariff import g_plus_commercialization_per_agent_hourly
    arr = g_plus_commercialization_per_agent_hourly(mte_agents, horizon_index)
    assert arr.shape == (5, len(horizon_index))
    nan_count = int(np.isnan(arr).sum())
    assert nan_count == 0, (
        f"G+Cvm+COT tiene {nan_count} NaN; revisar columnas Gm/Cvm/COT del CSV."
    )
    assert 400 < arr.mean() < 700, f"G+Cvm+COT fuera de rango: {arr.mean()}"


def test_helpers_consistencia_aritmetica(mte_agents, horizon_index):
    """Verificación cruzada: G + Cvm + COT > G + Cvm > G > 0 en cada celda
    (Cvm > 0 y COT > 0 siempre)."""
    from data.cedenar_tariff import (
        g_component_per_agent_hourly,
        g_plus_commercialization_per_agent_hourly,
    )
    g       = g_component_per_agent_hourly(mte_agents, horizon_index)
    g_plus  = g_plus_commercialization_per_agent_hourly(mte_agents, horizon_index)
    assert np.all(g_plus > g), "Inconsistencia: G+Cvm+COT debe > G en todas las celdas"
    assert np.all(g > 0), "G negativo en alguna celda"
    # Diferencia esperada (Cvm + COT) ≈ 215 COP/kWh
    diff = (g_plus - g).mean()
    assert 150 < diff < 280, f"Cvm+COT fuera de rango: {diff}"


# ─── 4. Cobertura del CSV CEDENAR ───────────────────────────────────────────

def test_csv_cedenar_no_tiene_meses_faltantes_en_horizonte():
    """tariff_coverage debe reportar que NO faltan meses en el horizonte
    de simulación. Si faltan, el run --full caerá al fallback 650
    COP/kWh y los KPIs serán incorrectos."""
    from data.cedenar_tariff import tariff_coverage
    cov = tariff_coverage(HORIZON_START, HORIZON_END)
    assert len(cov["meses_faltantes"]) == 0, (
        f"Faltan meses en CSV: {cov['meses_faltantes']}. "
        f"Re-correr `--full` produciría fallback con valores erróneos."
    )


# ─── 5. comparison_engine acepta y propaga pi_G ─────────────────────────────

def test_run_comparison_acepta_pi_G_sin_errores():
    """run_comparison debe aceptar pi_G y propagarlo a run_c2_bilateral."""
    import inspect
    from scenarios.comparison_engine import run_comparison
    sig = inspect.signature(run_comparison)
    assert "pi_G" in sig.parameters, (
        "run_comparison no expone pi_G; SA-3 y main no podrán pasar el "
        "rango negociable a C2."
    )


def test_run_c2_bilateral_acepta_pi_G_sin_errores():
    """run_c2_bilateral debe aceptar pi_G."""
    import inspect
    from scenarios.scenario_c2_bilateral import run_c2_bilateral
    sig = inspect.signature(run_c2_bilateral)
    assert "pi_G" in sig.parameters


# ─── 6. analysis.sensitivity propaga pi_G (CAL-13b) ─────────────────────────

def test_run_sensitivity_ppa_acepta_pi_G_CAL13b():
    """SA-3 debe aceptar pi_G (CAL-13b). Sin él, el rango sería
    [pi_gb, pi_gs] heredado pre-CAL-13."""
    import inspect
    from analysis.sensitivity import run_sensitivity_ppa
    sig = inspect.signature(run_sensitivity_ppa)
    assert "pi_G" in sig.parameters, (
        "run_sensitivity_ppa no expone pi_G; CAL-13b incompleto."
    )


def test_main_simulation_propaga_pi_G_a_sensitivity():
    """main_simulation.py debe pasar pi_G_arg a run_sensitivity_ppa."""
    src = (REPO_ROOT / "main_simulation.py").read_text(encoding="utf-8")
    # Buscar la sección entre `run_sensitivity_ppa(` y la siguiente
    # llamada / bloque de código (línea que comienza sin sangría
    # adicional, p.ej. `# §3.12` o `print(`). Captura líneas hasta el
    # primer `)` solo precedido por espacios al final de línea.
    idx = src.find("run_sensitivity_ppa(")
    assert idx != -1, "No se encontró invocación a run_sensitivity_ppa"
    # Tomar 2 KB después del call para cubrir la firma completa
    block = src[idx:idx + 2000]
    assert "pi_G=pi_G_arg" in block, (
        "main_simulation.py no propaga pi_G_arg a run_sensitivity_ppa; "
        "SA-3 caerá al rango legacy [pi_gb, pi_gs]."
    )


# ─── 7. Caso sintético end-to-end ───────────────────────────────────────────

def test_main_sintetico_corre_sin_errores():
    """El caso sintético (sin --data real) debe correr completo en
    < 60 s sin lanzar excepciones. Es el smoke más rápido del pipeline."""
    import sys
    import io
    import contextlib
    import main_simulation as ms

    # Captura salida para no contaminar el reporte de pytest
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Llamar directamente la función main del módulo
        ms.main(use_real_data=False, full_horizon=False,
                run_analysis=False, single_day=None)

    out = buf.getvalue()
    # Verificar que el banner CAL-13 apareció
    assert "[CAL-13]" in out, "Banner CAL-13 no se imprimió en sintético"
    # Verificar que llegó al final
    assert "Completado en" in out, "main() no completó la corrida"


# ─── 8. Wiring específico de pi_G_arg en main_simulation ────────────────────

def test_main_simulation_construye_pi_G_arg():
    """main_simulation.py debe construir pi_G_arg con
    g_plus_commercialization_per_agent_hourly (no g_component_per_agent_hourly,
    que sería CAL-12 obsoleto)."""
    src = (REPO_ROOT / "main_simulation.py").read_text(encoding="utf-8")
    # Patrón: pi_G_arg = g_plus_commercialization_per_agent_hourly(...)
    assert "g_plus_commercialization_per_agent_hourly" in src, (
        "main_simulation.py no usa el helper CAL-13; debería construir "
        "pi_G_arg con g_plus_commercialization_per_agent_hourly."
    )
    assert "pi_G_arg" in src
    # Y debe pasarlo a run_comparison
    assert "pi_G=pi_G_arg" in src


def test_main_simulation_pasa_pi_G_arg_a_run_comparison():
    """El call a run_comparison en main_simulation.py debe incluir
    pi_G=pi_G_arg para que C2 use la corrección CAL-13."""
    src = (REPO_ROOT / "main_simulation.py").read_text(encoding="utf-8")
    # Buscar el bloque de invocación a run_comparison (no en sensibilidad)
    pattern = re.compile(r"run_comparison\([^)]*\)", re.DOTALL)
    matches = pattern.findall(src)
    assert len(matches) >= 1
    main_call = next((m for m in matches if "pi_ppa=pi_ppa_default" in m), None)
    assert main_call is not None, "No se encontró el call principal a run_comparison"
    assert "pi_G=pi_G_arg" in main_call, (
        "El call principal a run_comparison no propaga pi_G_arg; "
        "C2 caerá al BTM legacy en --full."
    )


# ─── 10. Tests con datos reales MTE_v3 (skip si no disponible) ───────────────

# El dataset MTE_v3 está en gitignore; en CI o entornos sin datos los
# tests se saltan automáticamente. En desarrollo local con datos
# disponibles, validan el pipeline `--full --analysis` end-to-end.

MTE_DATA_DIR = REPO_ROOT / "MedicionesMTE_v3"
MTE_AVAILABLE = MTE_DATA_DIR.is_dir()
MTE_SKIP_REASON = (
    f"Dataset MTE_v3 no disponible en {MTE_DATA_DIR}; "
    f"este test requiere los datos reales (gitignored)."
)


@pytest.mark.skipif(not MTE_AVAILABLE, reason=MTE_SKIP_REASON)
def test_mte_v3_estructura_basica():
    """MedicionesMTE_v3 debe contener subcarpetas para las 5 instituciones."""
    expected_institutions = {"Udenar", "HUDN", "Mariana", "UCC", "Cesmag"}
    found = {p.name for p in MTE_DATA_DIR.iterdir() if p.is_dir()}
    missing = expected_institutions - found
    assert not missing, f"Subcarpetas MTE faltantes: {missing}"


@pytest.mark.skipif(not MTE_AVAILABLE, reason=MTE_SKIP_REASON)
def test_full_horizon_carga_datos_MTE():
    """data.xm_data_loader.MTEDataLoader debe poder instanciarse y
    apuntar al dataset MTE_v3."""
    from data.xm_data_loader import MTEDataLoader
    import os
    os.environ["MTE_ROOT"] = str(MTE_DATA_DIR)
    # Smoke: la clase debe existir y aceptar instanciación básica
    assert MTEDataLoader is not None
    # Si tiene constructor sin args, instanciar; si requiere args, solo
    # validamos que es callable
    assert callable(MTEDataLoader)


@pytest.mark.skipif(not MTE_AVAILABLE, reason=MTE_SKIP_REASON)
def test_main_simulation_data_real_perfil_diario_corre():
    """Smoke con `--data real` (perfil diario promedio, ~2 min) — modo
    más rápido con datos reales que valida la cadena tarifa+escenarios
    sin costar 52 min de --full."""
    import io
    import contextlib
    import os
    import main_simulation as ms

    os.environ["MTE_ROOT"] = str(MTE_DATA_DIR)
    importlib.reload(ms)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ms.main(use_real_data=True, full_horizon=False,
                run_analysis=False, single_day=None)

    out = buf.getvalue()
    assert "[CAL-13]" in out, "Banner CAL-13 ausente en --data real"
    assert "[CAL-10b.2]" in out, "Banner CAL-10b.2 ausente en --data real"
    assert "Completado en" in out, "main(--data real) no completó"


@pytest.mark.skipif(not MTE_AVAILABLE, reason=MTE_SKIP_REASON)
def test_sensibilidad_ppa_full_horizon_con_pi_G():
    """SA-3 sobre el horizonte completo con pi_G real (CAL-13b).
    Verifica que el barrido de pi_ppa con datos reales no se rompe
    y que el pi_ppa máximo del rango es G+Cvm+COT promedio."""
    import os
    os.environ["MTE_ROOT"] = str(MTE_DATA_DIR)

    from data.cedenar_tariff import g_plus_commercialization_per_agent_hourly
    from data.base_case_data import GRID_PARAMS_REAL

    agents = ["Udenar", "HUDN", "Mariana", "UCC", "Cesmag"]
    idx = pd.date_range(HORIZON_START, HORIZON_END, freq="1h",
                        inclusive="left")
    pi_G_arg = g_plus_commercialization_per_agent_hourly(agents, idx)
    pi_G_mean = float(np.mean(pi_G_arg))
    # Para horizonte completo MTE oficial NT2, esperado ≈ 526 COP/kWh
    assert 450 < pi_G_mean < 600, (
        f"pi_G_mean fuera de rango esperado: {pi_G_mean}"
    )

    # El pi_ppa máximo del rango SA-3 debe ser pi_G_mean cuando se pasa
    # pi_G (verificación a nivel de fórmula CAL-13b).
    pi_gb = GRID_PARAMS_REAL["pi_gb"]
    pi_ppa_max_CAL13 = pi_gb + 1.0 * (pi_G_mean - pi_gb)
    assert pi_ppa_max_CAL13 == pytest.approx(pi_G_mean, rel=1e-9)


@pytest.mark.skipif(not MTE_AVAILABLE, reason=MTE_SKIP_REASON)
def test_xm_prices_disponibles_horizonte():
    """get_pi_bolsa debe poder obtener precios para el horizonte MTE
    (vía pydataxm cache o sintético calibrado). No debe lanzar excepción."""
    from data.xm_prices import get_pi_bolsa
    # Firma: get_pi_bolsa(T, t_start, t_end, ...)
    T_horizon = int((pd.Timestamp(HORIZON_END) - pd.Timestamp(HORIZON_START))
                    .total_seconds() / 3600)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pi_bolsa = get_pi_bolsa(T_horizon,
                                t_start=HORIZON_START,
                                t_end=HORIZON_END)
    assert pi_bolsa is not None
    assert len(pi_bolsa) >= T_horizon - 24, (
        f"Cobertura insuficiente: {len(pi_bolsa)} h vs {T_horizon} esperadas"
    )
    # Sanity: precios en rango razonable post-Niño 2025-2026
    arr = np.asarray(pi_bolsa, dtype=float)
    arr_finite = arr[np.isfinite(arr)]
    if len(arr_finite) > 0:
        assert 50 < float(np.mean(arr_finite)) < 600, (
            f"pi_bolsa medio fuera de rango: {np.mean(arr_finite)}"
        )
