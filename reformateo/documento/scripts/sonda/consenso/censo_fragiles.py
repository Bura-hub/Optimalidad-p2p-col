"""M-E, el censo de las horas FRAGILES frente a mu (tarea 4e): las horas en que
la forma cerrada (el limite mu -> 0) y el reposo de la dinamica regularizada
con mu = 1 se apartan en mas de 1e-3·E.

POR QUE SE REDEFINE. El censo anterior (`medicion_mu.censo`, la letra del plan)
contaba toda hora con dos techos o dos pisos a menos de 3·mu, CON la diferencia
cero. Los cuatro compradores de ASC tienen el mismo techo al bit todos los
meses, de modo que salia el 100 % de la energia, y un empate exacto es inocuo:
con precios iguales la respuesta cuantal es el llenado por niveles de la forma
cerrada. La fragilidad real esta en otro sitio: el precio comun del grupo
interior a pocos (COP/kWh) del techo de un comprador que no recibe (regimen
«excluidos»), o un piso de bolsa pegado a uno de permuta. En la hora 12 de E0
la brecha es de 1,59 (COP/kWh) y la dinamica con mu = 1 aparta un 26 % de E.
Ver `.superpowers/sdd/2026-09-16-reposo/investigacion-me-md.md`, secciones 1.e
a 1.g.

LA DEFINICION (seccion 1.g de la investigacion). Con el reposo cerrado de la
hora (el de produccion: presupuesto sigma, precio uniforme, despacho por piso)
y mu = 1, una hora es FRAGIL si

    max( max_i |q~_i - q_i| , max_j |s~_j - s_j| ) > 1e-3·E,

  q~_i = min(d_i, exp((pi_i - C)/mu)), sum q~ = E, sobre los compradores en el
         juego (d_i > 0 y fuera de `excluidos_bajo_piso`), con pi_i los precios
         del reposo (`pi_reposo`);
  s~_j = min(s_j, exp((-c_j - C')/mu)), sum s~ = E, sobre los que pueden
         vender (fuera de `vendedores_excluidos` y de
         `vendedores_no_despachados`), con c_j el piso del vendedor (la clave
         de D64, y la de la dinamica con el costo de la alternativa, D68).

C y C' salen de una biseccion monotona. Cada lado solo pesa en su rama: con
vendedores cortos, s~ = s; con compradores cortos, q~ = d. Es la prueba de
primer orden de que la forma cerrada es el reposo con mu = 1: si q~ = q, el
bloque del reparto esta en reposo con multiplicadores admisibles.

LO QUE PUBLICA, por caso: las horas con mercado y las frágiles, la energia
frágil (la de esas horas) y su porcentaje de la energia del caso, la energia que cambiaria de manos
(sum ½·(sum_i |q~ - q| + sum_j |s~ - s|)), y el desglose por regimen y por mes.

COMO SE LEE EL ALMACEN. Cada hora se reconstruye de la tabla `agentes` (papel
«vendedor» con su sobrante y su piso, «comprador» con su faltante y su techo),
se resuelve con `core.reposo_mercado.resuelve_reposo` (microsegundos) y SE
COMPRUEBA contra lo que el almacen guardo: el regimen, el volumen y lo que
recibe cada comprador en `flujos`. Una hora que no se reproduce no se juzga y
se cuenta aparte. El almacen guarda en float32, de modo que la comprobacion
admite ese redondeo.

    python -u censo_fragiles.py \\
        --raiz SALIDAS_SERVIDOR/entrega_validacion_2026-09-19/SALIDAS_SERVIDOR/matriz_reposo \\
        --casos E0 K1 E4 --salida censo_fragiles.json

LA RAMA CUANTAL (D71, 2026-09-19). Desde D71 el nucleo publica el reposo
cuantal en las horas fragiles, y su `resuelve_reposo` por defecto ya no es la
forma cerrada. El censo MIDE SIEMPRE SOBRE LA FORMA CERRADA
(`mu_cuantal=0.0`): la fragilidad es una propiedad de la hora, y su definicion
es la de arriba. La guarda contra el almacen usa la forma con que se escribio:
un almacen de la rama cuantal trae la columna `mu_cuantal` en la tabla de
horas y se compara con el nucleo con esa mu; uno anterior (la matriz del 17),
con la forma cerrada. Y en cada hora se cruza el censo con el nucleo: con la
mu del censo, el nucleo tiene que decir «cuantal» exactamente en las horas
fragiles y con el mismo apartamiento (1e-9 relativo); si no, la hora va a
`discrepancias`, que debe quedar vacia. Publica ademas la sensibilidad del
conteo al umbral (5e-4, 1e-3, 2e-3 y 5e-3 de E, con la mu del censo) y a mu
(0,5, 1 y 2, con el umbral del censo): horas, energia fragil y energia que
cambiaria de manos (sec. 8.1 y 8.4 del diseno).

COSTO. Segundos por caso: no integra nada.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ_REPO = AQUI.parents[4]
for _p in (RAIZ_REPO, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

MU = 1.0
TOL_REL = 1e-3
# La regla del plan era: si la energia fragil pasa del 2 %, la forma cerrada
# adopta en esas horas el reposo con mu = 1. Con D71 (2026-09-19) queda sin
# funcion: el nucleo publica el reposo cuantal en cada hora fragil, sea cual
# sea el peso del caso. El 2 % queda solo como diagnostico en la tabla.
UMBRAL_ENERGIA = 0.02
SIN_MERCADO = ("", "None", "sin_mercado", "sin_ganancia")
# La comprobacion contra el almacen, que guarda en float32.
TOL_GUARDA = 1e-4
# D71: la sensibilidad del conteo al umbral y a mu (sec. 8.1 y 8.4 del
# diseno de la rama cuantal).
UMBRALES = (5e-4, 1e-3, 2e-3, 5e-3)
MUS = (0.5, 1.0, 2.0)
# D71: el apartamiento del nucleo frente al del censo, relativo. Las dos
# bisecciones son la misma salvo el reparto del resto del nucleo (1e-11).
TOL_CRUCE_REL = 1e-9


def respuesta_cuantal(E, cap, z, mu=MU):
    """min(cap_k, exp((z_k - C)/mu)) con suma E, por biseccion en C.

    Es la respuesta regularizada de un bloque del reparto con capacidades:
    con z iguales es el llenado por niveles, min(cap_k, L). Si E cubre todas
    las capacidades, devuelve las capacidades."""
    cap = np.asarray(cap, float)
    z = np.asarray(z, float)
    if cap.size == 0:
        return cap.copy()
    if E >= cap.sum() * (1.0 - 1e-12):
        return cap.copy()

    def suma(C):
        return np.minimum(cap, np.exp(np.minimum((z - C) / mu, 700.0)))
    lo = float(z.min()) - mu * (60.0 + abs(np.log(max(float(cap.max()),
                                                        1e-300))))
    hi = float(z.max()) + mu * (60.0 + abs(np.log(max(float(E), 1e-300))))
    for _ in range(200):
        C = 0.5 * (lo + hi)
        if suma(C).sum() > E:
            lo = C
        else:
            hi = C
    return suma(0.5 * (lo + hi))


def fragilidad(r, s, d, piso_j, mu=MU, tol_rel=TOL_REL) -> dict:
    """La prueba de una hora, con su reposo cerrado `r` (`ReposoHora`) y sus
    entradas. Devuelve dict(fragil, dq, ds, movida, lado, E): `dq` y `ds` en
    (kWh), la mayor diferencia de cada lado; `movida`, la energia que
    cambiaria de manos; `lado`, «compradores», «vendedores» o «»."""
    E = float(r.E)
    if E <= 0.0:
        return dict(fragil=False, dq=0.0, ds=0.0, movida=0.0, lado="", E=E)
    s = np.asarray(s, float)
    d = np.asarray(d, float)
    piso_j = np.asarray(piso_j, float)
    fuera_i = set(int(k) for k in r.excluidos_bajo_piso)
    dentro = np.array([i for i in range(d.size)
                       if d[i] > 0 and i not in fuera_i], int)
    fuera_j = (set(int(k) for k in r.vendedores_excluidos)
               | set(int(k) for k in r.vendedores_no_despachados))
    pueden = np.array([j for j in range(s.size)
                       if s[j] > 0 and j not in fuera_j], int)
    q = np.asarray(r.q, float)
    sd = np.asarray(r.s_despachado, float)
    pi = np.asarray(r.pi_reposo, float)
    qs = respuesta_cuantal(E, d[dentro], pi[dentro], mu)
    ss = respuesta_cuantal(E, s[pueden], -piso_j[pueden], mu)
    dif_q = np.abs(qs - q[dentro])
    dif_s = np.abs(ss - sd[pueden])
    dq = float(dif_q.max()) if dif_q.size else 0.0
    ds = float(dif_s.max()) if dif_s.size else 0.0
    fragil = max(dq, ds) > tol_rel * E
    lado = ("" if not fragil else
            ("compradores" if dq >= ds else "vendedores"))
    return dict(fragil=bool(fragil), dq=dq, ds=ds, lado=lado, E=E,
                movida=float(0.5 * (dif_q.sum() + dif_s.sum())),
                q_cuantal=qs.tolist(), s_cuantal=ss.tolist())


# ── el almacen ──────────────────────────────────────────────────────────
def lee_almacen(almacen, cobertura="m1"):
    """(agentes, flujos, horas) del almacen, con `core.almacen.lee`."""
    from core.almacen import lee
    alm = Path(almacen)
    return (lee(alm, cobertura, "agentes"), lee(alm, cobertura, "flujos"),
            lee(alm, cobertura, "horas"))


def entradas_de_hora(sub) -> dict:
    """Las entradas del nucleo de UNA hora, de sus filas de `agentes`:
    vendedores (papel «vendedor») con su sobrante y su piso, compradores
    («comprador») con su faltante y su techo, en el orden del almacen."""
    v = sub[sub["papel"] == "vendedor"]
    c = sub[sub["papel"] == "comprador"]
    return dict(vend=[str(x) for x in v["agente"]],
                comp=[str(x) for x in c["agente"]],
                s=v["sobrante"].to_numpy(dtype=float),
                d=c["faltante"].to_numpy(dtype=float),
                piso_j=v["piso"].to_numpy(dtype=float),
                techo=c["techo"].to_numpy(dtype=float),
                nombres=[str(x) for x in sub["agente"]])


def hora_del_almacen(sub, fecha="") -> dict:
    """La hora armada para el arnes (la forma de `arnes.entradas`) a partir de
    sus filas de `agentes`, sin cargar las mediciones del caso (tarea 4e, para
    M-D). El costo b_j es el de los datos reales por nombre
    (`get_b_for_real_data`), que no depende de la hora."""
    from data.xm_prices import get_b_for_real_data
    nombres = [str(x) for x in sub["agente"]]
    papel = [str(x) for x in sub["papel"]]
    sj = [k for k, x in enumerate(papel) if x == "vendedor"]
    bi = [k for k, x in enumerate(papel) if x == "comprador"]
    b_all = np.asarray(get_b_for_real_data(len(nombres), nombres), float)
    sob = sub["sobrante"].to_numpy(dtype=float)
    fal = sub["faltante"].to_numpy(dtype=float)
    gen = sub["generacion"].to_numpy(dtype=float)
    techo = sub["techo"].to_numpy(dtype=float)
    piso = sub["piso"].to_numpy(dtype=float)
    piso_j = piso[sj]
    return dict(s=sj, bb=bi, vend=[nombres[j] for j in sj],
                comp=[nombres[i] for i in bi], gn=sob[sj], dn=fal[bi],
                a=np.zeros(len(sj)), b=b_all[sj], gk=gen[bi],
                techo=techo[bi], piso_j=piso_j,
                piso=float(np.min(piso_j)) if len(sj) else float("nan"),
                fecha=fecha)


def horas_del_almacen(almacen, fechas, cobertura="m1") -> dict:
    """{fecha: hora armada} de un almacen, leyendo `agentes` una sola vez."""
    from core.almacen import lee
    agentes = lee(Path(almacen), cobertura, "agentes")
    quiero = set(fechas)
    fuera = {}
    for _h, sub in agentes.groupby("hora"):
        fecha = str(sub["fecha"].iloc[0])[:16]
        if fecha in quiero:
            fuera[fecha] = hora_del_almacen(sub, fecha)
    return fuera


def comprueba(r, ent, fila_hora, flujos_hora) -> str:
    """Vacio si el reposo recalculado reproduce lo que el almacen guardo; si
    no, el motivo."""
    reg = str(fila_hora.get("regimen", ""))
    if r.regimen != reg:
        return f"regimen {r.regimen} frente a {reg}"
    E = float(r.E)
    tol = TOL_GUARDA * max(1.0, E)
    vol = float(fila_hora.get("volumen", np.nan))
    if not abs(E - vol) <= tol:
        return f"volumen {E:.6f} frente a {vol:.6f}"
    recibe = (flujos_hora.groupby("comprador")["kwh"].sum().to_dict()
              if len(flujos_hora) else {})
    for i, nombre in enumerate(ent["comp"]):
        guardado = float(recibe.get(nombre, 0.0))
        if not abs(float(r.q[i]) - guardado) <= tol:
            return (f"{nombre} recibe {float(r.q[i]):.6f} frente a "
                    f"{guardado:.6f}")
    return ""


def _acumula(dic, clave, E, fragil, movida=0.0):
    x = dic.setdefault(clave, dict(horas=0, E=0.0, fragiles=0, E_fragil=0.0,
                                   movida=0.0))
    x["horas"] += 1
    x["E"] += E
    if fragil:
        x["fragiles"] += 1
        x["E_fragil"] += E
        x["movida"] += movida


def censo_almacen(almacen, cobertura="m1", mu=MU, tol_rel=TOL_REL,
                  tablas=None) -> dict:
    """El censo de un almacen. `tablas` = (agentes, flujos, horas) ya leidas,
    para las pruebas; si no, se leen del almacen.

    D71: mide con la forma cerrada (`mu_cuantal=0.0`); guarda contra el
    almacen con la forma con que se escribio (la columna `mu_cuantal` de la
    tabla de horas, o la cerrada si no la trae); y cruza cada hora con el
    nucleo con la mu del censo (`discrepancias`)."""
    from core.reposo_mercado import TOL_FRAGIL_REL, resuelve_reposo
    agentes, flujos, horas = tablas if tablas is not None else \
        lee_almacen(almacen, cobertura)
    posterior = "mu_cuantal" in horas.columns
    cruza = float(tol_rel) == float(TOL_FRAGIL_REL)
    ag_h = {int(h): sub for h, sub in agentes.groupby("hora")}
    fl_h = ({int(h): sub for h, sub in flujos.groupby("hora")}
            if len(flujos) else {})
    vacio = flujos.iloc[0:0] if len(flujos) else flujos
    por_hora = {}
    total = dict(horas=0, E=0.0, fragiles=0, E_fragil=0.0, movida=0.0,
                 no_reproduce=0)
    por_regimen, por_mes, no_repro = {}, {}, []
    por_umbral, por_mu, discrepancias = {}, {}, []
    for fila in horas.to_dict("records"):
        reg = str(fila.get("regimen", "") or "")
        if not bool(fila.get("resuelta", False)) or reg in SIN_MERCADO:
            continue
        h = int(fila["hora"])
        sub = ag_h.get(h)
        if sub is None:
            continue
        ent = entradas_de_hora(sub)
        if not ent["vend"] or not ent["comp"]:
            continue
        args = (ent["s"], ent["d"], np.zeros(len(ent["vend"])),
                ent["techo"], ent["piso_j"])
        # D71: la forma cerrada, que es lo que se mide; el nucleo con la mu
        # del censo, para el cruce; y la guarda con la forma del almacen.
        r = resuelve_reposo(*args, mu_cuantal=0.0)
        r_mu = resuelve_reposo(*args, mu_cuantal=float(mu))
        mu_alm = float(fila.get("mu_cuantal", 0.0)) if posterior else 0.0
        if mu_alm == 0.0:
            guarda = r
        elif mu_alm == float(mu):
            guarda = r_mu
        else:
            guarda = resuelve_reposo(*args, mu_cuantal=mu_alm)
        motivo = comprueba(guarda, ent, fila, fl_h.get(h, vacio))
        fecha = str(fila.get("fecha", ""))[:16]
        mes = str(fila.get("mes", ""))
        if motivo:
            total["no_reproduce"] += 1
            no_repro.append(dict(hora=h, fecha=fecha, motivo=motivo))
            continue
        f = fragilidad(r, ent["s"], ent["d"], ent["piso_j"], mu, tol_rel)
        E = float(r.E)
        total["horas"] += 1
        total["E"] += E
        for clave, dic in ((r.regimen, por_regimen), (mes, por_mes)):
            _acumula(dic, clave, E, f["fragil"], f["movida"])
        if f["fragil"]:
            total["fragiles"] += 1
            total["E_fragil"] += E
            total["movida"] += f["movida"]
        # D71: la sensibilidad al umbral (con la mu del censo) y a mu (con el
        # umbral del censo).
        a = max(f["dq"], f["ds"])
        for u in UMBRALES:
            _acumula(por_umbral, f"{u:g}", E, a > u * E, f["movida"])
        for m in MUS:
            fm = (f if m == float(mu) else
                  fragilidad(r, ent["s"], ent["d"], ent["piso_j"], m, tol_rel))
            _acumula(por_mu, f"{m:g}", E, fm["fragil"], fm["movida"])
        # D71: el cruce con el nucleo. Con la mu del censo, «cuantal» en las
        # fragiles y en ninguna mas; en las fragiles, con el mismo
        # apartamiento. En las demas el apartamiento es ruido de las dos
        # bisecciones (1e-15 a 1e-11) y no se compara.
        a_rel = a / E if E > 0 else 0.0
        dif = abs(float(r_mu.apartamiento) - a_rel)
        if cruza and ((r_mu.regimen == "cuantal") != bool(f["fragil"])
                      or (f["fragil"] and dif > TOL_CRUCE_REL * a_rel)):
            discrepancias.append(dict(
                hora=h, fecha=fecha, fragil=bool(f["fragil"]),
                regimen_nucleo=r_mu.regimen,
                apartamiento_nucleo=float(r_mu.apartamiento),
                apartamiento_censo=float(a_rel)))
        por_hora[h] = dict(hora=h, fecha=fecha, mes=mes, regimen=r.regimen,
                           E=E, fragil=f["fragil"], dq=f["dq"], ds=f["ds"],
                           lado=f["lado"], movida=f["movida"],
                           regimen_nucleo=r_mu.regimen,
                           apartamiento_nucleo=float(r_mu.apartamiento))
    fraccion = total["E_fragil"] / total["E"] if total["E"] > 0 else 0.0
    return dict(almacen=str(almacen), cobertura=cobertura, mu=float(mu),
                tol_rel=float(tol_rel), horas_con_mercado=total["horas"],
                horas_fragiles=total["fragiles"], energia=total["E"],
                energia_fragil=total["E_fragil"], fraccion=fraccion,
                pasa_del_2=bool(fraccion > UMBRAL_ENERGIA),
                energia_movida=total["movida"],
                no_reproduce=total["no_reproduce"],
                no_reproduce_ejemplos=no_repro[:20],
                almacen_cuantal=bool(posterior),
                discrepancias=len(discrepancias),
                discrepancias_ejemplos=discrepancias[:20],
                sensibilidad_umbral=por_umbral, sensibilidad_mu=por_mu,
                por_regimen=por_regimen, por_mes=por_mes, por_hora=por_hora)


def fila_tabla(caso, c) -> str:
    return (f"  {caso:<6s} {c['horas_con_mercado']:>7d} {c['horas_fragiles']:>8d} "
            f"{c['energia']:>11.1f} {c['energia_fragil']:>10.1f} "
            f"{100 * c['fraccion']:>7.2f} % {c['energia_movida']:>9.2f} "
            f"{'SI' if c['pasa_del_2'] else 'no':>6s} {c['no_reproduce']:>6d}")


CABECERA = (f"  {'caso':<6s} {'horas':>7s} {'fragiles':>8s} {'E (kWh)':>11s} "
            f"{'E fragil':>10s} {'% de E':>9s} {'movida':>9s} {'> 2 %':>6s} "
            f"{'no rep':>6s}")


def desglose(c) -> list:
    lineas = ["    por regimen: " + "; ".join(
        f"{reg} {x['fragiles']}/{x['horas']} h, {x['E_fragil']:.1f} de "
        f"{x['E']:.1f} kWh"
        for reg, x in sorted(c["por_regimen"].items()) if x["horas"])]
    meses = [f"{m} {x['fragiles']}/{x['horas']} h, {x['E_fragil']:.1f} kWh"
             for m, x in sorted(c["por_mes"].items()) if x["fragiles"]]
    lineas.append("    por mes (solo los que tienen frágiles): "
                  + ("; ".join(meses) if meses else "ninguno"))
    # D71: la sensibilidad y el cruce con el nucleo.
    if c.get("sensibilidad_umbral"):
        lineas.append("    umbral (x E): " + "; ".join(
            f"{u} {x['fragiles']} h, {x['E_fragil']:.1f} kWh, movida "
            f"{x['movida']:.2f}"
            for u, x in c["sensibilidad_umbral"].items()))
    if c.get("sensibilidad_mu"):
        lineas.append("    mu (COP/kWh): " + "; ".join(
            f"{m} {x['fragiles']} h, {x['E_fragil']:.1f} kWh, movida "
            f"{x['movida']:.2f}"
            for m, x in c["sensibilidad_mu"].items()))
    if "discrepancias" in c:
        lineas.append(f"    cruce con el nucleo (D71): {c['discrepancias']} "
                      f"discrepancias"
                      + (" <- HALLAZGO" if c["discrepancias"] else ""))
    return lineas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raiz", help="carpeta con un almacen por caso "
                                   "(<raiz>/<caso>/almacen)")
    ap.add_argument("--casos", nargs="*", default=[])
    ap.add_argument("--almacen", help="un solo almacen, en vez de --raiz")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--mu", type=float, default=MU)
    ap.add_argument("--salida", required=True)
    args = ap.parse_args(argv)
    trabajos = []
    if args.almacen:
        trabajos.append((args.casos[0] if args.casos else "?", args.almacen))
    elif args.raiz:
        casos = args.casos or sorted(p.parent.name for p in
                                     Path(args.raiz).glob("*/almacen"))
        trabajos = [(c, str(Path(args.raiz) / c / "almacen")) for c in casos]
    if not trabajos:
        print("  nada que censar: pasa --raiz (y --casos) o --almacen")
        return 2
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    fuera = {}
    print(f"  CENSO DE HORAS FRAGILES frente a mu = {args.mu:g} (1e-3·E; "
          f"tarea 4e)", flush=True)
    print(CABECERA, flush=True)
    for caso, alm in trabajos:
        c = censo_almacen(alm, args.cobertura, args.mu)
        c["caso"] = caso
        fuera[caso] = c
        print(fila_tabla(caso, c), flush=True)
        for linea in desglose(c):
            print(linea, flush=True)
    guarda = {caso: {k: v for k, v in c.items() if k != "por_hora"}
              for caso, c in fuera.items()}
    for caso, c in fuera.items():
        guarda[caso]["horas_fragiles_lista"] = [
            x for x in c["por_hora"].values() if x["fragil"]]
    salida.write_text(json.dumps(guarda, indent=1, default=float),
                      encoding="utf-8")
    print(f"  escrito {salida}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
