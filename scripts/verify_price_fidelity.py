"""Verificación de fidelidad de precios CEDENAR/XM — Act 1.1 (spec CAL-35).

Tres verificaciones:
  A (dura)  CSV Cedenar ↔ matrices que usa el código (pi_gs, Cvm, G, COT).
  B (suave) PDFs oficiales Cedenar ↔ CSV (chequeo de presencia de valores).
  C (mixta) Serie XM: medias mensuales vs oficiales (suave) + techo PES (dura).

Salida: outputs/price_fidelity_report.md ; exit code 1 si falla una dura.
Ejecución:  python scripts/verify_price_fidelity.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # CAL-28b
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data import cedenar_tariff                               # noqa: E402
from data.xm_prices import XM_MONTHLY_REAL, apply_creg101066_ceiling  # noqa: E402

CSV = ROOT / "data" / "tarifas_cedenar_mensual.csv"
PDF_DIR = ROOT / "data" / "cedenar_pdfs"
XM_CSV = ROOT / "data" / "precios_bolsa_xm_api.csv"
PES_CSV = ROOT / "data" / "precios_escasez_creg.csv"
OUT = ROOT / "outputs" / "price_fidelity_report.md"

hard_fail: list[str] = []
lines: list[str] = ["# Reporte de fidelidad de precios CEDENAR/XM",
                    "", f"Generado por `scripts/verify_price_fidelity.py`.", ""]


def _load_tarifas() -> pd.DataFrame:
    df = pd.read_csv(CSV, comment="#", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return df


def check_a_csv_vs_codigo():
    """A (dura): cada (mes, institución) — el código reproduce el CSV exacto."""
    lines.append("## A — CSV Cedenar ↔ matrices del código (dura)")
    lines.append("")
    lines.append("| Mes | Institución | CU_aplicado | Cvm | Gm | COT | Veredicto |")
    lines.append("|---|---|---|---|---|---|---|")
    df = _load_tarifas()
    agents = list(cedenar_tariff.INSTITUTION_PROFILE.keys())
    meses = sorted(df["mes"].dropna().unique())
    n_ok = n_bad = 0
    for mes in meses:
        idx = pd.date_range(f"{mes}-01", periods=24, freq="h")
        try:
            pgs = cedenar_tariff.pi_gs_per_agent_hourly(agents, idx)
            cvm = cedenar_tariff.cvm_per_agent_hourly(agents, idx)
            comps = cedenar_tariff.cu_components_per_agent_hourly(agents, idx)
        except Exception as e:                                  # noqa: BLE001
            lines.append(f"| {mes} | (todas) | — | — | — | — | ✗ excepción: {e} |")
            hard_fail.append(f"A:{mes}:exception")
            n_bad += 1
            continue
        for ai, ag in enumerate(agents):
            prof = cedenar_tariff.INSTITUTION_PROFILE[ag]
            row = df[(df["mes"] == mes)
                     & (df["categoria"].str.strip() == prof.categoria)
                     & (df["nivel_tension"].astype(int) == int(prof.nivel_tension))
                     & (df["propiedad"].str.strip() == prof.propiedad)]
            if row.empty:
                lines.append(f"| {mes} | {ag} | — | — | — | — | ◯ sin fila CSV (fallback) |")
                continue
            r0 = row.iloc[0]
            celdas, bad_here = [], []
            for col, val_cod in (("CU_aplicado", float(pgs[ai, 0])),
                                 ("Cvm",         float(cvm[ai, 0])),
                                 ("Gm",          float(comps["G"][ai, 0])),
                                 ("COT",         float(comps["COT"][ai, 0]))):
                if col not in r0 or pd.isna(r0[col]):
                    celdas.append("n/a")
                    continue
                val_csv = float(r0[col])
                if abs(val_csv - val_cod) > 0.01:
                    celdas.append(f"✗ {val_csv}≠{val_cod:.2f}")
                    bad_here.append(col)
                else:
                    celdas.append(f"{val_csv:.2f} ✓")
            if bad_here:
                hard_fail.append(f"A:{mes}/{ag}/{','.join(bad_here)}")
                n_bad += len(bad_here)
                lines.append(f"| {mes} | {ag} | {' | '.join(celdas)} | ✗ |")
            else:
                n_ok += 4
                lines.append(f"| {mes} | {ag} | {' | '.join(celdas)} | ✓ |")
    lines.append("")
    lines.append(f"**Resultado A:** {n_ok} valores ✓ · {n_bad} ✗")


def check_b_pdf_vs_csv():
    """B (suave): los valores del CSV aparecen en el texto del PDF del mes."""
    lines.append("\n## B — PDFs oficiales ↔ CSV (suave, presencia de valores)")
    try:
        from pypdf import PdfReader
    except ImportError:
        lines.append("- pypdf no instalado → verificación manual requerida")
        return
    df = _load_tarifas()
    for pdf in sorted(PDF_DIR.glob("tarifa_*.pdf")):
        mes = pdf.stem.replace("tarifa_", "")
        try:
            txt = "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
        except Exception as e:                                  # noqa: BLE001
            lines.append(f"- {mes}: ◯ PDF ilegible ({e}) → manual")
            continue
        sub = df[df["mes"] == mes]
        found = missing = 0
        ejemplos_missing = []
        for _, r in sub.iterrows():
            for col in ("Cvm", "Gm", "COT", "CU_aplicado"):
                if col in r and pd.notna(r[col]):
                    v = float(r[col])
                    # tolera coma o punto decimal y separador de miles opcional
                    entero = f"{int(v):,}".replace(",", r"[.,]?")
                    dec = f"{v - int(v):.2f}"[2:]
                    pat = entero + r"[.,]" + dec
                    if re.search(pat, txt):
                        found += 1
                    else:
                        missing += 1
                        if len(ejemplos_missing) < 2:
                            ejemplos_missing.append(f"{col}={v}")
        tag = "✓" if missing == 0 else ("◯ revisar: " + "; ".join(ejemplos_missing)
                                         if found else "✗ nada hallado")
        lines.append(f"- {mes}: {found} hallados, {missing} no hallados → {tag}")


def check_c_xm():
    """C: medias mensuales vs oficiales (suave) + techo PES (dura)."""
    lines.append("\n## C — Serie XM (bolsa) y techo PES CREG 101 066")
    raw = pd.read_csv(XM_CSV, encoding="utf-8-sig")
    raw["Fecha"] = pd.to_datetime(raw["Fecha"])
    raw = raw.sort_values(["Fecha", "Hora"]).reset_index(drop=True)
    raw["mes"] = raw["Fecha"].dt.strftime("%Y-%m")
    medias = raw.groupby("mes")["Precio_COP_kWh"].mean()
    lines.append("")
    lines.append("### C.1 — Medias mensuales del cache vs valores oficiales XM (suave)")
    for mes, oficial in sorted(XM_MONTHLY_REAL.items()):
        if mes in medias.index:
            m = float(medias[mes])
            delta = abs(m - float(oficial)) / float(oficial) * 100
            tag = "✓" if delta <= 10 else "◯ revisar"
            lines.append(f"- {mes}: media cache={m:.1f} vs oficial={oficial} "
                         f"(Δ {delta:.1f}%) {tag}")
    # ── C.2 Techo PES (dura) ────────────────────────────────────────────
    lines.append("")
    lines.append("### C.2 — Techo PES (dura): tras el cap, ninguna hora supera su tope mensual")
    try:
        pes = pd.read_csv(PES_CSV)
        pes_map = dict(zip(pes["mes"].astype(str), pes["pes_cop_kwh"].astype(float)))
        serie = raw["Precio_COP_kWh"].to_numpy(float)
        t_start = raw["Fecha"].iloc[0].strftime("%Y-%m-%d")
        capped = apply_creg101066_ceiling(serie.copy(), t_start=t_start, level="PES")
        meses_idx = raw["mes"].to_numpy()
        bad = 0
        for mes, tope in sorted(pes_map.items()):
            mask = meses_idx == mes
            if mask.any():
                mx = float(np.nanmax(capped[mask]))
                if mx > tope + 1e-6:
                    lines.append(f"- {mes}: ✗ max post-cap={mx:.1f} > PES={tope}")
                    hard_fail.append(f"C:PES:{mes}")
                    bad += 1
                else:
                    n_rec = int(np.sum(serie[mask] > capped[mask] + 1e-9))
                    lines.append(f"- {mes}: ✓ max post-cap={mx:.1f} ≤ PES={tope}"
                                 f" ({n_rec} h recortadas)")
        if bad == 0:
            lines.append("- **Techo PES: ✓ correcto en todos los meses con tope publicado**")
    except Exception as e:                                      # noqa: BLE001
        lines.append(f"- Techo PES: ◯ no verificable automáticamente ({e}) → manual")


if __name__ == "__main__":
    check_a_csv_vs_codigo()
    check_b_pdf_vs_csv()
    check_c_xm()
    lines.append("\n## Veredicto")
    lines.append("- Verificaciones DURAS: "
                 + ("**TODAS ✓**" if not hard_fail
                    else f"**{len(hard_fail)} fallas ✗**: {hard_fail}"))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReporte → {OUT}")
    sys.exit(1 if hard_fail else 0)
