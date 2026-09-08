"""
Lo que la tabla agregada del régimen del piso esconde (H-52, H-53).

TRES PREGUNTAS que el total no responde:

  1. ¿El ahorro de la lectura residual está repartido o lo hacen unas pocas
     horas? Si lo hacen pocas, el resultado es frágil.
  2. ¿Cuándo cruzan a bolsa los vendedores? El cruce es acumulativo dentro
     del mes, de modo que debería concentrarse al final de cada mes y en los
     meses de más sol.
  3. ¿La equidad se mueve igual todo el año?

EL CALENDARIO. El horizonte es contiguo y horario desde el 4 de abril de
2025, de modo que la hora k corresponde a esa fecha más k horas. Es la misma
convención que usa el corte por sub-períodos.

Uso:
    python reformateo/documento/scripts/sonda/piso_por_mes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI.parents[1] / "validacion_horaria"
INICIO = pd.Timestamp("2025-04-04 00:00")


def carga(muestra: int = 3000) -> pd.DataFrame:
    f = SALIDA / f"regimen_piso_muestra{muestra}.csv"
    if not f.exists():
        raise SystemExit(f"no esta {f}")
    d = pd.read_csv(f)
    d = d[d.resuelta.fillna(False)]
    d["fecha"] = INICIO + pd.to_timedelta(d.hora, unit="h")
    d["mes"] = d.fecha.dt.strftime("%Y-%m")
    d["hdia"] = d.fecha.dt.hour
    return d


def main() -> int:
    d = carga()
    filas = []
    for cob in ("m1", "m3"):
        t = d[d.cobertura == cob]
        if t.empty:
            continue
        p = t.pivot(index="hora", columns="regimen",
                    values=["factura_con", "ahorro_comprador",
                            "ingreso_vendedor", "volumen"])
        dif = p["factura_con"]["residual"] - p["factura_con"]["tramo"]
        mes = (INICIO + pd.to_timedelta(dif.index.to_series(),
                                        unit="h")).dt.strftime("%Y-%m")

        print(flush=True)
        print(f"  frontera {cob.upper()}", flush=True)
        print("  " + "=" * 78, flush=True)

        # 1 · concentracion
        v = dif[dif.abs() > 1e-6].sort_values()
        tot = float(dif.sum())
        print(f"  1 · el ahorro de la lectura residual, {tot:+.1f} (COP)",
              flush=True)
        if len(v):
            top = float(v.head(max(1, len(v) // 10)).sum())
            print(f"      lo mueven {len(v)} horas de {len(dif)}; el decil "
                  f"que mas aporta pone {100*top/tot:5.1f} %", flush=True)
            print(f"      por hora: mediana {v.median():+8.1f} · peor "
                  f"{v.min():+9.1f} · mejor {v.max():+8.1f} (COP)", flush=True)

        # 2 y 3 · mes a mes
        print(flush=True)
        print(f"  2 · mes a mes", flush=True)
        print(f"      {'mes':>8s} {'horas':>6s} {'dif factura':>13s} "
              f"{'% del total':>11s} {'equidad tramo':>14s} "
              f"{'equidad resid':>14s} {'retir tramo':>12s} "
              f"{'retir resid':>12s}", flush=True)
        for m in sorted(mes.unique()):
            sel = mes == m
            dm = float(dif[sel.to_numpy()].sum())
            tt = t[(t.mes == m)]
            def ie(g):
                u = tt[tt.regimen == g]
                a, i = u.ahorro_comprador.sum(), u.ingreso_vendedor.sum()
                return (a - i) / (a + i) if abs(a + i) > 1e-12 else np.nan
            rt = int(tt[tt.regimen == "tramo"].retirados.sum())
            rr = int(tt[tt.regimen == "residual"].retirados.sum())
            print(f"      {m:>8s} {int(sel.sum()):6d} {dm:13.1f} "
                  f"{100*dm/tot if tot else 0:10.1f}% {ie('tramo'):14.4f} "
                  f"{ie('residual'):14.4f} {rt:12d} {rr:12d}", flush=True)
            filas.append(dict(cobertura=cob, mes=m, horas=int(sel.sum()),
                              dif_factura=round(dm, 4),
                              equidad_tramo=round(float(ie("tramo")), 6),
                              equidad_residual=round(float(ie("residual")), 6),
                              retirados_tramo=rt, retirados_residual=rr))

    csv = SALIDA / "regimen_piso_por_mes.csv"
    pd.DataFrame(filas).to_csv(csv, index=False, encoding="utf-8")
    nota = (
        "Generado por reformateo/documento/scripts/sonda/piso_por_mes.py",
        "Desglose mensual de la medicion del regimen del piso. La hora k",
        "corresponde al 2025-04-04 00:00 mas k horas. Ver H-52 y H-53.",
    )
    (SALIDA / "regimen_piso_por_mes.fuente.txt").write_text(
        chr(10).join(nota) + chr(10), encoding="utf-8")
    print(chr(10) + f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
