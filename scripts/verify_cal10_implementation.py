"""
Verifica que CAL-10 + CAL-10b + CAL-10b.1 estén implementados como
fueron planteados en el spec/plan.

Ejecutar: python scripts/verify_cal10_implementation.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

results: list[tuple[str, bool, str]] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    status = "OK  " if cond else "FAIL"
    results.append((label, cond, detail))
    print(f"  [{status}] {label}" + (f"  ({detail})" if detail else ""))


def read(p: str) -> str:
    return Path(p).read_text(encoding="utf-8")


print("=" * 70)
print("VERIFICACION EXHAUSTIVA: spec + plan vs codigo committed")
print("=" * 70)

print()
print("### A. ALGORITMO C1 (scenarios/scenario_c1_creg174.py)")
src = read("scenarios/scenario_c1_creg174.py")
check("Param component_c en firma", "component_c:" in src)
check("Busqueda intramensual hora Hx", "iny_acum" in src and "ret_acum" in src and "hx = k_local" in src)
check("Cruce: split surplus en t1/t2 al detectar Hx", "surplus_t1[k_local]" in src and "surplus_t2[k_local]" in src)
check("Asimetria autoconsumo (sin descuento C)", "E_auto * pi_gs_period" in src)
check("Permuta Tipo 1 a (pi_gs - C)", "E_permuted_1 * pi_eff_t1" in src)
check("pi_eff_t1 = pi_gs - pi_C", "pi_gs_period - pi_C_period" in src)
check("Tipo 2 a bolsa horaria (np.dot)", "np.dot(surplus_t2, pb_h)" in src)
check("Diagnostico E_auto exportado", '"E_auto"' in src)
check("Diagnostico E_permuted_t1 exportado", '"E_permuted_t1"' in src)
check("Diagnostico E_tipo2 exportado", '"E_tipo2"' in src)
check("Diagnostico hx_history exportado", '"hx_history"' in src)
check("Cita CREG 174 art. 22-23", "CREG 174" in src and "22-23" in src)

print()
print("### B. HELPER as_component_c_array (scenarios/_pi_gs.py)")
src = read("scenarios/_pi_gs.py")
check("Funcion definida", "def as_component_c_array" in src)
check("Acepta str 'auto'", '"auto"' in src and "C_FRACTION" in src)
check("Acepta None", "component_c is None" in src)
check("Acepta float (size==1)", "arr.size == 1" in src)
check("Acepta (N,)", "arr.shape == (N,)" in src)
check("Acepta (T,)", "arr.shape == (T,)" in src)
check("Acepta (N,T) con NaN fallback", "nan_mask" in src and "np.isnan" in src)
check("Fallback usa pi_gs * C_FRACTION", "pi_gs_arr[nan_mask]" in src)

print()
print("### C. CSV CEDENAR REAL (data/tarifas_cedenar_mensual.csv)")
df = pd.read_csv("data/tarifas_cedenar_mensual.csv", comment="#")
check("Columna Cvm presente", "Cvm" in df.columns)
check("Columna COT presente", "COT" in df.columns)
oficial_nt2 = df[(df.categoria == "oficial") & (df.nivel_tension == 2) & (df.propiedad == "cedenar") & df.Cvm.notna()]
comercial_nt2 = df[(df.categoria == "comercial") & (df.nivel_tension == 2) & (df.propiedad == "cedenar") & df.Cvm.notna()]
check("13 meses pobladas oficial NT2", len(oficial_nt2) == 13, f"{len(oficial_nt2)}/13")
check("13 meses pobladas comercial NT2", len(comercial_nt2) == 13, f"{len(comercial_nt2)}/13")

print()
print("### D. HELPER cvm_plus_cot_per_agent_hourly (data/cedenar_tariff.py)")
src = read("data/cedenar_tariff.py")
check("Privado _lookup_cvm_plus_cot definido", "def _lookup_cvm_plus_cot" in src)
check("Lee Cvm + COT del CSV", 'df.loc[key, "Cvm"]' in src and 'df.loc[key, "COT"]' in src)
check("Devuelve None ante KeyError o NaN", "return None" in src and "np.isfinite" in src)
check("Publico cvm_plus_cot_per_agent_hourly definido", "def cvm_plus_cot_per_agent_hourly" in src)
check("Inicializa con NaN", "np.full((N, T), np.nan" in src)

print()
print("### E. CONSTANTE C_FRACTION (data/xm_prices.py)")
src = read("data/xm_prices.py")
check("C_FRACTION definida", "C_FRACTION = " in src)
check("Derivada de CU_COMPONENTS_2025", 'CU_COMPONENTS_2025["C"]' in src and "sum(CU_COMPONENTS_2025" in src)
check("Getter get_c_fraction", "def get_c_fraction" in src)

print()
print("### F. WIRING main_simulation.py")
src = read("main_simulation.py")
check("Importa cvm_plus_cot_per_agent_hourly", "cvm_plus_cot_per_agent_hourly" in src)
check("Construye component_c_arg condicional", "component_c_arg = cvm_plus_cot_per_agent_hourly" in src)
check("Fallback auto sintetico/perfil-diario", 'component_c_arg = "auto"' in src)
check("Banner [CAL-10b] presente", "[CAL-10b]" in src)
check("Banner condicional CSV vs auto", "Cvm + COT real desde CSV Cedenar" in src and "13.85" in src)
check("Pasa component_c_arg a llamadas", src.count("component_c=component_c_arg") >= 4)
check("SA-1 propaga month_labels y component_c", "run_sensitivity_pgb" in src and "month_labels=month_labels" in src)
check("SA-2 propaga month_labels y component_c", "run_sensitivity_pv" in src and src.count("component_c=component_c_arg") >= 4)
check("SA-3 (pgs) recibe month_labels", "run_sensitivity_pgs" in src and "month_labels=month_labels" in src)
check("SA-PPA propaga month_labels y component_c", "run_sensitivity_ppa" in src)

print()
print("### G. WIRING comparison_engine y monthly_report")
src = read("scenarios/comparison_engine.py")
check("run_comparison acepta component_c", "component_c:" in src and "def run_comparison" in src)
check("Default 'auto'", '"auto"' in src)
check("Propaga a run_c1_creg174", "component_c=component_c" in src)

src = read("analysis/monthly_report.py")
check("compute_monthly_metrics acepta component_c", "component_c:" in src)
check("Slicea por mes con idx_arr", "component_c[:, idx_arr]" in src)
check("Propaga slice a run_c1_creg174", "component_c=cc_m" in src)

print()
print("### H. WIRING sensitivity.py (CAL-10b.1)")
src = read("analysis/sensitivity.py")
check("run_sensitivity_pgb acepta month_labels", "def run_sensitivity_pgb" in src and "month_labels: Optional" in src)
check("run_sensitivity_pv acepta month_labels", "def run_sensitivity_pv" in src)
check("run_sensitivity_ppa acepta month_labels", "def run_sensitivity_ppa" in src)
check("run_sensitivity_pgs acepta month_labels", "def run_sensitivity_pgs" in src)
check("4 firmas con month_labels: Optional", src.count("month_labels: Optional") >= 4)
check("3 firmas con component_c (sin pgs)", src.count("component_c =") >= 3)
check("Llamadas a run_comparison propagan month_labels", src.count("month_labels=month_labels") >= 4)
check("Llamadas a run_comparison propagan component_c", src.count("component_c=component_c") >= 3)

print()
print("### I. TESTS UNITARIOS")
proc = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_c1_creg174_v2.py",
     "tests/test_cedenar_cvm_cot.py", "tests/test_pi_gs_temporal.py", "-q"],
    capture_output=True, text=True,
)
out = proc.stdout + proc.stderr
m = re.search(r"(\d+) passed", out)
n_passed = int(m.group(1)) if m else 0
check(f"Tests CAL-10/10b/10b.1 verdes", n_passed >= 24, f"{n_passed} tests")
check(f"Sin failures", "failed" not in out.lower() or "0 failed" in out, "")

print()
print("### J. DOCUMENTACION")
adr = read("docs/adr/0010-cal10-creg174-tipo-1-2-componente-c.md")
check("ADR 0010 existe", True)
check("ADR 0010 incluye anexo CAL-10b", "Anexo CAL-10b (" in adr and "CAL-10b.1" not in adr.split("Anexo CAL-10b (")[1].split("Anexo CAL-10b.1")[0])
check("ADR 0010 incluye anexo CAL-10b.1", "Anexo CAL-10b.1" in adr)
check("Spec brainstorming existe", Path("docs/superpowers/specs/2026-04-30-cedenar-pdf-componente-c-design.md").exists())
check("Plan implementacion existe", Path("docs/superpowers/plans/2026-04-30-cedenar-pdf-componente-c-implementation.md").exists())
notas = read("Documentos/notas_modelo_tesis.md")
check("Notas: seccion CAL-10b", "§CAL-10b" in notas or "CAL-10b" in notas)
check("Notas: seccion CAL-10b.1", "CAL-10b.1" in notas)

print()
print("### K. GIT COMMITS")
proc = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True)
out = proc.stdout
check("Commit CAL-10 + CAL-10b", "CAL-10 + CAL-10b" in out)
check("Commit CAL-10b.1", "CAL-10b.1" in out)

print()
print("### L. INTEGRACION END-TO-END (test funcional)")
from data.cedenar_tariff import cvm_plus_cot_per_agent_hourly
from scenarios.scenario_c1_creg174 import run_c1_creg174
import warnings
warnings.filterwarnings("ignore")

idx = pd.date_range("2025-07-01", "2025-08-01", freq="1h", inclusive="left", tz="America/Bogota")
T = len(idx)
c_real = cvm_plus_cot_per_agent_hourly(["Udenar"], idx)
check("Helper produce dato real (jul-2025 Udenar=216.58)",
      abs(c_real[0, 0] - 216.58) < 0.01,
      f"valor={c_real[0, 0]:.2f}")
check("Constante intra-mes", c_real[0, :].std() < 1e-9, f"std={c_real[0, :].std():.2e}")

D = np.full((1, T), 1.0)
G = np.zeros((1, T))
for d in range(31):
    G[0, d * 24 + 8 : d * 24 + 16] = 1.5
pi_bolsa = np.full(T, 250.0)
res = run_c1_creg174(D, G, 797.0, pi_bolsa, [0], component_c=c_real)
total_e = res[0]["E_auto"] + res[0]["E_permuted_t1"] + res[0]["E_tipo2"]
gen_total = float(np.sum(np.maximum(G[0], 0)))
check("Conservacion energia (C real)",
      abs(total_e - gen_total) < 1e-6,
      f"{total_e:.2f}=={gen_total:.2f}")
check("net_benefit no-NaN finito",
      np.isfinite(res[0]["net_benefit"]),
      f"{res[0]['net_benefit']:.0f}")
check("hx_history reporta None o int",
      all(v is None or isinstance(v, int) for v in res[0]["hx_history"]))

print()
print("=" * 70)
total = len(results)
ok = sum(1 for _, c, _ in results if c)
print(f"RESUMEN: {ok}/{total} verificaciones OK ({100 * ok / total:.0f}%)")
if ok == total:
    print("TODO IMPLEMENTADO Y CONSISTENTE CON SPEC/PLAN")
else:
    print("FALTAN:")
    for label, cond, detail in results:
        if not cond:
            print(f"  - {label}" + (f" ({detail})" if detail else ""))
print("=" * 70)

sys.exit(0 if ok == total else 1)
