"""
Las cinco tablas del régimen del piso (H-52, H-53, H-57).

La tabla que imprime el juntador resume; estas cinco desglosan, y cada una
responde una pregunta que el resumen no contesta:

  T1  la factura DESCOMPUESTA en sus dos canales. Es la tabla que explica el
      mecanismo: cuánto cambia lo que la red paga por el excedente exportado
      y cuánto devuelve el mercado de esa mejora.
  T2  energía y participación, para ver que más volumen no es mejor factura.
  T3  el reparto entre las dos partes, que es la métrica del autor del modelo.
  T4  mes a mes, que es donde se descubre que el efecto vive en dos meses.
  T5  la concentración, que dice si el resultado lo hacen pocas horas.

LO QUE T1 ENSEÑA Y NO SE VE EN EL RESUMEN. El mercado **absorbe** la mayor
parte de cualquier mejora en la alternativa externa. En la frontera principal
la lectura residual hace que la red pague 1.084.664 (COP) más por lo
exportado, pero el mercado aporta 849.499 menos: el 78 % se compensa solo, y
el neto son 235.165. Es la identidad de H-33 vista por el lado de la factura.

EL CALENDARIO de T4: la hora k corresponde al 2025-04-04 00:00 más k horas.

Uso:
    python reformateo/documento/scripts/sonda/tablas_regimen.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

from piso_por_mes import carga  # noqa: E402

SALIDA = AQUI.parents[1] / "validacion_horaria"
ORDEN = ("tramo", "permuta", "bolsa", "residual")
NL = chr(10)


def indice(u: pd.DataFrame) -> float:
    """El índice de equidad de Chacón sobre las SUMAS del periodo.

    Sobre las sumas y no promediando por hora: es un cociente, y la media de
    cocientes no es el cociente de las sumas.
    """
    a, i = u.ahorro_comprador.sum(), u.ingreso_vendedor.sum()
    return (a - i) / (a + i) if abs(a + i) > 1e-12 else float("nan")


def _t1(t, fs0, ex0, fc0, cob, H, filas):
    print(NL + "T1 · la factura, descompuesta (COP)", flush=True)
    print(f"{'regimen':>9s} {'sin mercado':>14s} {'aporta mercado':>15s} "
          f"{'con mercado':>14s} {'dif sin':>13s} {'dif aporte':>13s} "
          f"{'dif con':>12s}", flush=True)
    for g in ORDEN:
        u = t[t.regimen == g]
        fs, ex, fc = u.factura_sin.sum(), u.excedente.sum(), u.factura_con.sum()
        print(f"{g:>9s} {fs:14.1f} {ex:15.1f} {fc:14.1f} {fs - fs0:+13.1f} "
              f"{ex - ex0:+13.1f} {fc - fc0:+12.1f}", flush=True)
        filas.append(dict(
            tabla="T1", cobertura=cob, regimen=g, horas=H,
            factura_sin=round(float(fs), 4),
            aporta_mercado=round(float(ex), 4),
            factura_con=round(float(fc), 4),
            dif_factura_sin=round(float(fs - fs0), 4),
            dif_aporte=round(float(ex - ex0), 4),
            dif_factura_con=round(float(fc - fc0), 4)))


def _t2(t, p, v0, cob, H, filas):
    print(NL + "T2 · energia y participacion", flush=True)
    print(f"{'regimen':>9s} {'piso medio':>11s} {'precio medio':>13s} "
          f"{'volumen kWh':>12s} {'dif vol':>9s} {'retirados':>10s} "
          f"{'horas dif':>10s}", flush=True)
    for g in ORDEN:
        u = t[t.regimen == g]
        nd = 0 if g == "tramo" else int((p[g] - p["tramo"]).abs().gt(1e-6).sum())
        v = u.volumen.sum()
        print(f"{g:>9s} {u.piso_medio.mean():11.1f} "
              f"{u.precio_medio.mean():13.1f} {v:12.2f} "
              f"{100 * (v - v0) / v0:+8.2f}% {int(u.retirados.sum()):10d} "
              f"{nd:10d}", flush=True)
        filas.append(dict(
            tabla="T2", cobertura=cob, regimen=g, horas=H,
            piso_medio=round(float(u.piso_medio.mean()), 4),
            precio_medio=round(float(u.precio_medio.mean()), 4),
            volumen=round(float(v), 6),
            dif_volumen_pct=round(float(100 * (v - v0) / v0), 6),
            retirados=int(u.retirados.sum()), horas_que_cambian=nd))


def _t3(t, cob, H, filas):
    print(NL + "T3 · reparto entre las partes (metrica de Chacon)", flush=True)
    print(f"{'regimen':>9s} {'ahorro compr':>14s} {'ingreso vend':>14s} "
          f"{'suma':>14s} {'indice':>9s} {'% compr':>8s} {'% vend':>8s}",
          flush=True)
    for g in ORDEN:
        u = t[t.regimen == g]
        a, i = u.ahorro_comprador.sum(), u.ingreso_vendedor.sum()
        print(f"{g:>9s} {a:14.1f} {i:14.1f} {a + i:14.1f} {indice(u):9.4f} "
              f"{100 * a / (a + i):7.2f}% {100 * i / (a + i):7.2f}%",
              flush=True)
        filas.append(dict(
            tabla="T3", cobertura=cob, regimen=g, horas=H,
            ahorro_comprador=round(float(a), 4),
            ingreso_vendedor=round(float(i), 4),
            suma=round(float(a + i), 4),
            indice_equidad=round(indice(u), 6),
            reparto_comprador=round(float(100 * a / (a + i)), 4)))


def _t4(t, cob, filas):
    print(NL + "T4 · mes a mes", flush=True)
    print(f"{'mes':>8s} {'horas':>6s} {'fact tramo':>13s} {'fact resid':>13s} "
          f"{'diferencia':>12s} {'IE tramo':>9s} {'IE resid':>9s} "
          f"{'ret tr':>7s} {'ret re':>7s} {'vol tramo':>10s}", flush=True)
    for m in sorted(t.mes.unique()):
        s = t[t.mes == m]
        tr, re = s[s.regimen == "tramo"], s[s.regimen == "residual"]
        dm = re.factura_con.sum() - tr.factura_con.sum()
        print(f"{m:>8s} {tr.hora.nunique():6d} {tr.factura_con.sum():13.1f} "
              f"{re.factura_con.sum():13.1f} {dm:+12.1f} {indice(tr):9.4f} "
              f"{indice(re):9.4f} {int(tr.retirados.sum()):7d} "
              f"{int(re.retirados.sum()):7d} {tr.volumen.sum():10.2f}",
              flush=True)
        filas.append(dict(
            tabla="T4", cobertura=cob, mes=m, horas=int(tr.hora.nunique()),
            factura_tramo=round(float(tr.factura_con.sum()), 4),
            factura_residual=round(float(re.factura_con.sum()), 4),
            diferencia=round(float(dm), 4),
            indice_tramo=round(indice(tr), 6),
            indice_residual=round(indice(re), 6),
            retirados_tramo=int(tr.retirados.sum()),
            retirados_residual=int(re.retirados.sum()),
            volumen_tramo=round(float(tr.volumen.sum()), 6)))


def _t5(p, cob, H, filas):
    print(NL + "T5 · concentracion de la diferencia (residual menos tramo)",
          flush=True)
    dif = (p["residual"] - p["tramo"]).sort_values()
    nz = dif[dif.abs() > 1e-6]
    print(f"  horas con diferencia {len(nz)} de {H} ({100 * len(nz) / H:.1f} %)",
          flush=True)
    if not len(nz):
        return
    q = nz.quantile([0, .25, .5, .75, 1])
    print(f"  cuartiles (COP)  min {q.iloc[0]:.1f} · Q1 {q.iloc[1]:.1f} · "
          f"mediana {q.iloc[2]:.1f} · Q3 {q.iloc[3]:.1f} · max {q.iloc[4]:.1f}",
          flush=True)
    f = dict(tabla="T5", cobertura=cob, horas=H, horas_con_diferencia=len(nz),
             minimo=round(float(q.iloc[0]), 4),
             mediana=round(float(q.iloc[2]), 4),
             maximo=round(float(q.iloc[4]), 4))
    for k in (1, 5, 10, 25):
        n = max(1, int(len(nz) * k / 100))
        cuota = 100 * nz.head(n).sum() / nz.sum()
        print(f"  el {k:2d} % de horas que mas aporta pone {cuota:5.1f} % "
              f"del total", flush=True)
        f[f"cuota_decil_{k}"] = round(float(cuota), 4)
    filas.append(f)


def main() -> int:
    d = carga()
    filas: list = []
    for cob in ("m1", "m3"):
        t = d[d.cobertura == cob]
        if t.empty:
            continue
        H = t.hora.nunique()
        b = t[t.regimen == "tramo"]
        fs0, fc0 = b.factura_sin.sum(), b.factura_con.sum()
        ex0, v0 = b.excedente.sum(), b.volumen.sum()
        p = t.pivot(index="hora", columns="regimen", values="factura_con")
        print(NL + NL + f"##### {cob.upper()} · {H} horas #####", flush=True)
        _t1(t, fs0, ex0, fc0, cob, H, filas)
        _t2(t, p, v0, cob, H, filas)
        _t3(t, cob, H, filas)
        _t4(t, cob, filas)
        _t5(p, cob, H, filas)

    csv = SALIDA / "regimen_piso_tablas.csv"
    pd.DataFrame(filas).to_csv(csv, index=False, encoding="utf-8")
    nota = (
        "Generado por reformateo/documento/scripts/sonda/tablas_regimen.py",
        "Cinco tablas por frontera sobre la corrida del horizonte completo.",
        "La columna tabla dice a cual pertenece cada fila. Ver H-52, H-53 y",
        "H-57.",
    )
    (SALIDA / "regimen_piso_tablas.fuente.txt").write_text(
        NL.join(nota) + NL, encoding="utf-8")
    print(NL + f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
