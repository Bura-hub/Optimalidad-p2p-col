"""
Junta las tandas del régimen del piso y produce la tabla emparejada (H-52).

POR QUE HACE FALTA UN JUNTADOR. La muestra la fija la semilla, de modo que
correr un régimen suelto da exactamente las mismas horas que la tanda
anterior. Eso permite añadir un régimen sin repetir los ya medidos, pero
deja el resultado repartido en varios ficheros. Este los junta.

POR QUE EN PESOS Y NO EN PORCENTAJE, que es C-155. En la frontera secundaria
la factura ronda el cero y cambia de signo, de modo que un cociente por hora
da valores como -231,60 % sin contenido.

POR QUE SOLO LAS HORAS COMPLETAS. Una hora que no resolvió en un régimen
sesgaría la suma de ese régimen frente a los demás. Solo entran las horas con
TODOS los regímenes resueltos, y la tabla dice cuántas son.

Y EL BIENESTAR NO ARBITRA, que es H-55: los términos de pago se cancelan
entre los dos lados y lo único que le queda al bienestar del precio es la
penalización de competencia, de modo que prefiere el piso más bajo por
construcción. Se informa; no decide. Decide la factura.

Uso:
    python reformateo/documento/scripts/sonda/compara_regimenes.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI.parents[1] / "validacion_horaria"
ORDEN = ("tramo", "permuta", "bolsa", "residual")


def carga_tandas(muestra: int = 40) -> pd.DataFrame:
    ficheros = sorted(SALIDA.glob(f"regimen_piso_muestra{muestra}*.csv"))
    if not ficheros:
        raise SystemExit(f"no hay tandas en {SALIDA}")
    d = pd.concat([pd.read_csv(f) for f in ficheros], ignore_index=True)
    print(f"  {len(ficheros)} tanda(s), {len(d)} filas", flush=True)
    print(flush=True)
    for f in ficheros:
        print(f"    {f.name}", flush=True)
    return d[d.resuelta.fillna(False)].drop_duplicates(
        subset=["cobertura", "hora", "regimen"])


def main() -> int:
    # El tamano de la muestra tiene que venir por argumento: el servidor corre
    # con 200 y el juntador buscaba «muestra40» a secas, de modo que no habria
    # encontrado ninguna tanda y habria salido diciendo que no hay nada.
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=40)
    args = ap.parse_args()
    d = carga_tandas(args.muestra)
    presentes = [g for g in ORDEN if g in set(d.regimen)]
    n = d.groupby(["cobertura", "hora"]).regimen.nunique()
    completas = n[n == len(presentes)].index
    s = d.set_index(["cobertura", "hora"]).loc[completas].reset_index()

    filas = []
    for cob in ("m1", "m3"):
        t = s[s.cobertura == cob]
        if t.empty:
            continue
        H = t.hora.nunique()
        base = t[t.regimen == "tramo"]
        fb, vb = base.factura_con.sum(), base.volumen.sum()
        print(flush=True)
        print(f"  frontera {cob.upper()} · {H} horas con los "
              f"{len(presentes)} regímenes resueltos", flush=True)
        print("  " + "=" * 104, flush=True)
        print(f"  {'régimen':>9s} {'piso medio':>11s} {'bienestar':>11s} "
              f"{'FACTURA (COP)':>15s} {'dif factura':>13s} "
              f"{'volumen kWh':>12s} {'dif vol':>9s} {'retir':>6s} "
              f"{'excedente':>11s} {'EQUIDAD':>9s} {'% compr':>8s}",
              flush=True)
        for g in presentes:
            u = t[t.regimen == g]
            f, v = u.factura_con.sum(), u.volumen.sum()
            # El indice de equidad de Chacon y el reparto entre las dos
            # partes, agregados sobre las SUMAS del periodo. Son cocientes, y
            # la media de cocientes no es el cociente de las sumas.
            ac = float(u.ahorro_comprador.sum()) if "ahorro_comprador"                 in u.columns else float("nan")
            iv = float(u.ingreso_vendedor.sum()) if "ingreso_vendedor"                 in u.columns else float("nan")
            tt = ac + iv
            ie = (ac - iv) / tt if abs(tt) > 1e-12 else float("nan")
            ps = 100.0 * ac / tt if abs(tt) > 1e-12 else float("nan")
            print(f"  {g:>9s} {u.piso_medio.mean():11.1f} "
                  f"{u.bienestar.sum():11.1f} {f:15.1f} {f - fb:+13.1f} "
                  f"{v:12.2f} {100 * (v - vb) / vb:+8.2f}% "
                  f"{int(u.retirados.sum()):6d} {u.excedente.sum():11.1f} "
                  f"{ie:9.4f} {ps:7.2f}%", flush=True)
            filas.append(dict(
                cobertura=cob, regimen=g, horas=H,
                piso_medio=round(float(u.piso_medio.mean()), 4),
                bienestar=round(float(u.bienestar.sum()), 4),
                factura_con=round(float(f), 4),
                dif_factura=round(float(f - fb), 4),
                volumen=round(float(v), 6),
                dif_volumen_pct=round(float(100 * (v - vb) / vb), 6),
                retirados=int(u.retirados.sum()),
                excedente=round(float(u.excedente.sum()), 4),
                ahorro_comprador=round(ac, 4), ingreso_vendedor=round(iv, 4),
                equidad=round(ie, 6), reparto_comprador=round(ps, 4),
                reparto_vendedor=round(100.0 - ps, 4)))

        p = t.pivot(index="hora", columns="regimen",
                    values=["factura_con", "volumen"])
        for g in presentes:
            if g == "tramo":
                continue
            df = p["factura_con"][g] - p["factura_con"]["tramo"]
            mueve = int((df.abs() > 1e-6).sum())
            med = float(df[df.abs() > 1e-6].median()) if mueve else 0.0
            print(f"    {g:>8s}: cambia la factura en {mueve:2d} de {H} "
                  f"horas, mediana {med:+9.1f} (COP)", flush=True)
            filas[[i for i, r in enumerate(filas)
                   if r["cobertura"] == cob and r["regimen"] == g][0]].update(
                horas_que_cambian=mueve, dif_mediana_hora=round(med, 4))

    csv = SALIDA / "regimen_piso_comparado.csv"
    pd.DataFrame(filas).to_csv(csv, index=False, encoding="utf-8")
    nota = (
        "Generado por reformateo/documento/scripts/sonda/compara_regimenes.py",
        "Junta las tandas de regimen_piso y empareja por hora. Solo entran",
        "las horas con TODOS los regimenes resueltos. Las diferencias van en",
        "pesos, no en porcentaje por hora (C-155). El bienestar se informa",
        "pero no arbitra (H-55). Ver H-52 y H-53.",
    )
    (SALIDA / "regimen_piso_comparado.fuente.txt").write_text(
        chr(10).join(nota) + chr(10), encoding="utf-8")
    print(chr(10) + f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
