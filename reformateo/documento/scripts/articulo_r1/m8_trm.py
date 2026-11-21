"""
m8_trm.py — M8: la tasa representativa del mercado (TRM) media del horizonte y
las cifras del artículo en dólares
===============================================================================
Comentarios B-1 y J-1 de la revisión r1. No simula.

LA SERIE. La TRM diaria la certifica la Superintendencia Financiera de Colombia
y la publica el Banco de la República. Se lee del conjunto «Tasa de Cambio
Representativa del Mercado - Histórico» de datos.gov.co (identificador
mcec-87by), descargado el 2026-11-21 con

    https://www.datos.gov.co/resource/mcec-87by.csv
        ?$where=vigenciahasta >= '2025-04-01T00:00:00' AND vigenciadesde <= '2025-12-20T00:00:00'
        &$order=vigenciadesde&$limit=5000

y guardado en `insumos/trm_datosgov_mcec-87by.csv`. El guion comprueba su
tamaño y su sha256. Cada fila rige de `vigenciadesde` a `vigenciahasta`, de modo
que los fines de semana y festivos llevan la tasa del último día hábil.

LA MEDIA. Media simple de los 256 días calendario del horizonte, del 4 de abril
al 15 de diciembre de 2025, cada uno con la tasa vigente ese día.

LAS CONVERSIONES. MCOP → USD (valor · 10⁶ / TRM) y COP/kWh → USD/MWh
(valor · 10³ / TRM), para las cifras en pesos que el artículo da en el resumen,
los resultados y las conclusiones (claves de `cifras_articulo_2026-09-30`).

Si el fichero de la serie no está, el guion se detiene y dice dónde ponerlo.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/m8_trm.py
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

import ar1_comun as C

REL = "SALIDAS_SERVIDOR/articulo_r1_2026-11-21/insumos/trm_datosgov_mcec-87by.csv"
TRM_BYTES = 11729
TRM_SHA256 = "af2265587413df5589e19f3f8995734070151e5e5041b83fbb9ba480a1fdb05f"
D0, D1 = "2025-04-04", "2025-12-15"
FUENTE = "datos.gov.co, conjunto mcec-87by (TRM histórica, Superintendencia Financiera de Colombia), descarga del 2026-11-21"

# Cifras en pesos del resumen, los resultados y las conclusiones del artículo.
MCOP_CASO = ["P2P", "C1", "C4", "P2Pcom", "P2P_C4", "P2P_C1", "C1_C4", "banda", "reclas", "P2Pcom_C4", "P2Pcom_P2P"]
SUELTAS = ["atr__E0__shapley_s1", "atr__E0__shapley_s2", "pcom__E0__sh_sin10", "pcom__E0__sh_intercambio",
           "ppa__PP_media", "bolsa_media_topada", "e0__ancho_efectivo", "corte__E3__ancho_antes",
           "corte__E3__ancho_tras", "kwh__2025-04__ancho_CEDENAR_compra_ASC", "kwh__2025-04__ancho_CEDENAR_vende_ASC",
           "descP2Pcom__I1__numeral_sh", "descP2Pcom__I1__total"]
TABLA_II = [f"kwh__{com}__2025-04__{k}" for com in ("ASC", "CEDENAR") for k in ("CU", "Cv", "Theta", "C1", "C4")]


def main() -> int:
    med = C.Medicion("m8", "TRM media del horizonte y cifras en dólares")
    p = C.RAIZ / REL
    if not p.is_file():
        raise SystemExit(f"[ar1:m8] falta la serie de la TRM. Ponga en {REL} un CSV con las columnas valor, "
                         "vigenciadesde y vigenciahasta (formato del conjunto mcec-87by de datos.gov.co) y actualice "
                         "TRM_BYTES y TRM_SHA256 en este guion. No se usa ninguna tasa de memoria.")
    datos = p.read_bytes()
    med.exige(len(datos) == TRM_BYTES and hashlib.sha256(datos).hexdigest() == TRM_SHA256,
              "la serie de la TRM no es la descargada el 2026-11-21 (tamaño o sha256 distintos)")
    med.insumos.append((REL, len(datos), TRM_SHA256))
    t = pd.read_csv(p, parse_dates=["vigenciadesde", "vigenciahasta"])
    med.exige(list(t.columns) == ["valor", "unidad", "vigenciadesde", "vigenciahasta"] and (t.unidad == "COP").all(),
              "columnas o unidad inesperadas en la serie de la TRM")
    dias = pd.date_range(D0, D1, freq="D")
    v = pd.Series(np.nan, index=dias)
    veces = pd.Series(0, index=dias)
    for f in t.itertuples():
        r = pd.date_range(f.vigenciadesde.normalize(), f.vigenciahasta.normalize(), freq="D").intersection(dias)
        v[r] = f.valor
        veces[r] += 1
    med.exige(len(dias) == 256 and bool((veces == 1).all()) and bool(np.isfinite(v).all()) and bool((v > 0).all()),
              "la serie no cubre cada día del horizonte exactamente una vez")
    med.ok("la serie cubre los 256 días calendario del 2025-04-04 al 2025-12-15, cada uno con una sola tasa")
    trm = float(v.mean())
    habiles = t[(t.vigenciadesde >= D0) & (t.vigenciadesde <= D1)]
    med.di(f"  TRM media del horizonte: {trm:.2f} COP/USD (mínima {v.min():.2f} el {v.idxmin():%Y-%m-%d}, "
           f"máxima {v.max():.2f} el {v.idxmax():%Y-%m-%d}); {len(habiles)} tasas publicadas")
    med.pon("trm__media_horizonte", trm, "COP/USD", FUENTE)
    med.pon("trm__dias", len(dias), "días", FUENTE)
    med.pon("trm__tasas_publicadas", len(habiles), "tasas", FUENTE)
    med.pon("trm__min", float(v.min()), "COP/USD", FUENTE)
    med.pon("trm__max", float(v.max()), "COP/USD", FUENTE)
    med.pon("trm__media_dias_habiles", float(habiles.valor.mean()), "COP/USD", FUENTE + "; media de las tasas publicadas, sin repetir fines de semana")
    mens = v.groupby(v.index.strftime("%Y-%m")).mean()
    for m, x in mens.items():
        med.pon(f"trm__{m}", float(x), "COP/USD", FUENTE + "; media de los días del mes dentro del horizonte")
    diaria = pd.DataFrame({"fecha": dias.strftime("%Y-%m-%d"), "trm_COP_USD": v.to_numpy()})
    med.tabla(diaria, "m8_trm_diaria.csv")

    # Conversiones
    cif = C.cifras_articulo()
    full = pd.read_csv(C.AS.lee(C.F_CIFRAS, "e1/L")).set_index("clave")
    claves = [f"com__{c}__{k}" for c in C.CINCO for k in MCOP_CASO] + SUELTAS + TABLA_II
    filas = []
    for k in claves:
        med.exige(k in full.index, f"falta la clave {k} en cifras.csv del artículo")
        val, uni = float(full.valor[k]), full.unidad[k]
        med.exige(uni in ("MCOP", "COP/kWh"), f"{k}: unidad {uni}")
        usd, u2 = (val * 1e6 / trm, "USD") if uni == "MCOP" else (val * 1e3 / trm, "USD/MWh")
        filas.append(dict(clave=k, valor_pesos=val, unidad_pesos=uni, valor_usd=usd, unidad_usd=u2))
        med.pon(f"usd__{k}", usd, u2, f"{k} de cifras_articulo_2026-09-30 (e1/L) entre trm__media_horizonte")
    # El C4 hipotético de 11 fronteras (CANON §14.2), que no tiene clave en e1/L
    cf = pd.read_csv(C.AS.lee("contrafacticos_art18_2026-09-27/contrafacticos_13casos.csv", "e1/A1"))
    c11 = cf[cf.contrafactico == "C4_11_fronteras"].set_index("caso").total_COP / C.M
    for caso, contra, esperado in (("E0", "C4", 1.66), ("E4", "P2P", 33.99), ("I1", "P2P", 11.52)):
        b = float(c11[caso]) - float(cif[f"com__{caso}__{contra}"])
        med.exige(round(b, 2) == esperado, f"C4 de 11 fronteras menos {contra} en {caso}: {b:.4f}, el canon dice {esperado}")
        k = f"c4_11f__{caso}__menos_{contra}"
        filas.append(dict(clave=k, valor_pesos=b, unidad_pesos="MCOP", valor_usd=b * 1e6 / trm, unidad_usd="USD"))
        med.pon(k, b, "MCOP", "contrafacticos_art18_2026-09-27/contrafacticos_13casos.csv (e1/A1) menos com__*")
        med.pon(f"usd__{k}", b * 1e6 / trm, "USD", f"{k} entre trm__media_horizonte")
    med.ok("el C4 de 11 fronteras menos C4 en E0 y menos el mercado P2P en E4 e I1 da 1,66, 33,99 y 11,52 MCOP, como CANON §14.2")
    T = pd.DataFrame(filas)
    med.tabla(T, "m8_cifras_usd.csv")
    e0 = T.set_index("clave").valor_usd
    med.di(f"  E0: P2P − C4 = {e0['com__E0__P2P_C4']:.0f} USD; cargos evitados = {e0['com__E0__C1_C4']:.0f} USD; "
           f"ahorro del intercambio = {e0['com__E0__banda']:.0f} USD; P2P colectivo − C4 = {e0['com__E0__P2Pcom_C4']:.0f} USD")
    med.cierra()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
