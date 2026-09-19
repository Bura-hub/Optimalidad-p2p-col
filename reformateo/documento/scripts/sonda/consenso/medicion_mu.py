"""M-E: cuanto depende el reposo del parametro de la regularizacion, y en
cuantas horas lo mueve (el censo de horas frágiles).

QUE DECIDE. Si mu (la exploracion entropica del vendedor, D49) es solo un
parametro de velocidad, como se midio en la hora 109, o si mueve el reposo. Y,
si lo mueve, en cuantas horas: el reposo en forma cerrada es el limite mu -> 0,
con prioridad estricta y empate solo exacto, y discrepa de la regularizacion
donde un precio del reposo queda a pocos mu de otro que decide el reparto
(por ejemplo, el precio comun del grupo interior a menos de unos 7·mu del
techo de un comprador que no recibe). No en los empates exactos de techos, que
son inocuos (tarea 4e).

COMO, dos partes.

1. LA SENSIBILIDAD (esta es la que corre el lanzador). Dos horas de cada
   regimen de la muestra de M-A, integradas con mu en 0,3, 1 y 3, con k = 1 000
   hasta teq 160, contra el mismo reposo en forma cerrada.

       python -u corre_mediciones.py --medicion medicion_mu --salida <json>

   ACEPTACION: el mismo reposo dentro de 1e-3·E (kWh), salvo en las horas
   FRAGILES del censo (punto 2).

2. EL CENSO DE HORAS FRAGILES (tarea 4e), que se lee del almacen y no integra
   nada:

       python -u medicion_mu.py --censo --almacen <ruta> --caso E0 \\
           --salida <json>

   Es `censo_fragiles.censo_almacen`: una hora es fragil si la respuesta
   cuantal con mu = 1 y los precios del reposo se aparta del reparto cerrado
   en mas de 1e-3·E (ver el docstring de `censo_fragiles.py`). Con D71
   (2026-09-19) el nucleo publica en CADA hora fragil el reposo con mu = 1
   (regimen «cuantal»), sea cual sea el peso del caso: la regla del 2 % del
   plan, que decidia por caso, queda sin funcion y el porcentaje se publica
   solo como diagnostico.

   ANTES contaba las horas con dos techos o dos pisos a menos de 3·mu,
   diferencia cero incluida, y salia el 100 % de la energia: los cuatro
   compradores de ASC tienen el mismo techo al bit, y un empate exacto es
   inocuo (investigacion-me-md.md, sec. 1). Con aquel censo, ademas, la
   excepcion de la aceptacion de la parte 1 cubria el 100 % de las horas y no
   podia fallar.

COSTO. La sensibilidad son seis grupos por dos horas por tres mu, treinta y
seis corridas de 1 a 10 (min). El censo son segundos: lee tres tablas del
almacen y resuelve cada hora en forma cerrada.
"""
import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[4]
for _p in (RAIZ, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

GRUPOS = ("interiores", "topados", "suma_no_cabe", "mixto", "dos_vendedores",
          "compradores_cortos_sin_cesmag")
CASOS = ("E0", "K1", "E4", "E5")
POR_GRUPO = 2
MUS = (0.3, 1.0, 3.0)
K = 1000.0
TOPE = 3600.0
CORTES = [0, 2e-3, 5e-3, 1e-2, 2e-2, 4e-2, 8e-2, 0.16]

MEDICION = "M-E"
QUE_DECIDE = "si mu solo cambia la velocidad, y donde puede cambiar el reposo"

# La tolerancia que el plan fija para M-E (medio 3 de la revision de 4c): el
# reposo dentro de 1e-3·E en reparto. En precio el plan no da cifra; se usa la
# de las corridas aceleradas, 0,5 (COP/kWh), porque estas van con k = 1 000.
TOLERANCIA = dict(tol_q_rel=1e-3, tol_p=0.5, clase="declarada M-E",
                  motivo="la del plan para M-E: 1e-3*E; en precio, 0,5 "
                         "(COP/kWh), la de las aceleradas")


def specs(horas):
    fuera = []
    for grupo in GRUPOS:
        elegidas = []
        for caso in CASOS:
            for h in horas.get(caso, {}).get(grupo, []):
                elegidas.append((caso, h["fecha"]))
                if len(elegidas) >= POR_GRUPO:
                    break
            if len(elegidas) >= POR_GRUPO:
                break
        for caso, fecha in elegidas:
            for mu in MUS:
                fuera.append(dict(
                    # Cada mu es un modelo distinto: se juzga aparte (critico 1).
                    medicion=MEDICION, familia=f"mu {mu:g}",
                    caso=caso, fecha=fecha, grupo=grupo,
                    etq=f"mu {mu:g} k{K:g}",
                    var=dict(mu_ent=mu, k_lento=K),
                    cortes=CORTES, tope=TOPE, tolerancia=TOLERANCIA,
                    nivel="sigma", piso_juego="marginal"))
    return fuera


TEQ_FINAL = 160.0


def entre_mus(corridas, tol=TOLERANCIA) -> dict:
    """Los tres mu de UNA hora comparados entre si (N4 de la re-revision).

    Cada mu es una familia, y con dos horas por grupo la tabla generica solo
    puede decir «muestra insuficiente» en cada fila. Lo que M-E pregunta es
    otra cosa: si en una misma hora los tres mu llegan al MISMO sitio. Entra
    cada mu que llego a teq 160 con el estado quieto (`veredicto.esta_quieta`,
    como en M-C). Si un mu tiene varias corridas (una hora que cae en dos
    grupos de la muestra, m2, o una corrida rehecha y su JSON de retomada), se
    queda con la QUIETA en teq 160 si la hay; si no, con la primera que no sea
    FALLA; y solo si no hay otra, con la FALLA (M3 de la revision de 4d:
    antes se quedaba con la primera, aunque fuera una FALLA o un transitorio
    y hubiera otra quieta). Devuelve los mu que llegaron, los que no, la mayor
    diferencia de reparto y de precio entre dos de los que llegaron, y si
    coinciden.
    """
    import numpy as np
    from veredicto import es_falla, esta_quieta

    def llego(c):
        return bool(c.get("filas") and not c.get("cortada")
                    and abs(float(c["filas"][-1]["teq"]) - TEQ_FINAL) < 1e-6
                    and esta_quieta(c))

    candidatas = {}
    for c in corridas:
        mu = c.get("spec", {}).get("var", {}).get("mu_ent")
        if mu is not None:
            candidatas.setdefault(mu, []).append(c)
    por_mu = {}
    for mu, cs in candidatas.items():
        elegida = (next((c for c in cs if llego(c)), None)
                   or next((c for c in cs if not es_falla(c)), None)
                   or cs[0])
        por_mu[mu] = elegida if llego(elegida) else None
    llegaron = {mu: c for mu, c in por_mu.items() if c is not None}
    E = max(float(corridas[0].get("E", 0.0)), 1e-12) if corridas else 1e-12
    dq = dp = 0.0
    mus = sorted(llegaron)
    for a in range(len(mus)):
        for b in range(a + 1, len(mus)):
            fa = llegaron[mus[a]]["filas"][-1]
            fb = llegaron[mus[b]]["filas"][-1]
            dq = max(dq, float(np.max(np.abs(np.asarray(fa["q"], float)
                                             - np.asarray(fb["q"], float)))))
            dp = max(dp, float(np.max(np.abs(np.asarray(fa["p"], float)
                                             - np.asarray(fb["p"], float)))))
    comparable = len(llegaron) >= 2
    coinciden = bool(comparable and dq <= tol["tol_q_rel"] * E
                     and dp <= tol["tol_p"])
    return dict(llegaron=mus, no_llegaron=sorted(m for m, c in por_mu.items()
                                                  if c is None),
                comparable=comparable, coinciden=coinciden, dq=dq, dp=dp, E=E)


def veredicto(resultados) -> str:
    """N4: si mu solo cambia la velocidad, hora por hora."""
    horas = {}
    for res in resultados:
        sp = res.get("spec", {})
        if sp.get("medicion") != MEDICION or res.get("recorte_movio"):
            continue
        horas.setdefault((sp["caso"], sp["fecha"]), []).append(res)
    lineas = ["", "  M-E - LOS TRES MU DE CADA HORA ENTRE SI (1e-3*E y 0,5 "
              "(COP/kWh), sobre el estado final quieto en teq 160)", ""]
    if not horas:
        return "\n".join(lineas + ["  ninguna corrida de M-E"])
    from veredicto import es_falla, es_muerto, texto_muertas
    coinciden, mueven, no_comp, fallidas = [], [], [], []
    for (caso, fecha), corridas in sorted(horas.items()):
        # m-b de la re-revision 2: una hora cuyas corridas fallaron todas
        # cuenta en el denominador, como «falla».
        if all(es_falla(c) for c in corridas):
            fallidas.append((caso, fecha))
            continue
        r = entre_mus([c for c in corridas if not es_falla(c)])
        if not r["comparable"]:
            no_comp.append((caso, fecha, r))
        elif r["coinciden"]:
            coinciden.append((caso, fecha, r))
        else:
            mueven.append((caso, fecha, r))
    lineas.append(f"  {len(horas)} horas: en {len(coinciden)} los mu que "
                  f"llegaron coinciden; en {len(mueven)} el reposo CAMBIA con "
                  f"mu; {len(no_comp)} no se pueden comparar (menos de dos mu "
                  f"quietos en teq 160); {len(fallidas)} FALLARON en todos sus "
                  f"mu" + texto_muertas(sum(
                      1 for h in fallidas
                      if all(es_muerto(c) for c in horas[h]))))
    for caso, fecha, r in mueven[:20]:
        lineas.append(f"    MU MUEVE EL REPOSO {caso} {fecha}: max|dq| = "
                      f"{r['dq']:.3e} (kWh, E = {r['E']:.4f}), max|dp| = "
                      f"{r['dp']:.3f} (COP/kWh), mu {r['llegaron']}")
    for caso, fecha, r in no_comp[:10]:
        lineas.append(f"    no comparable {caso} {fecha}: llegaron mu "
                      f"{r['llegaron']}, no llegaron mu {r['no_llegaron']}")
    incompletas = [h for h in coinciden if len(h[2]["llegaron"]) < len(MUS)]
    if incompletas:
        lineas.append(f"  ({len(incompletas)} de las que coinciden lo hacen con "
                      f"solo dos mu: el tercero no llego)")
    if mueven:
        lineas.append("  => mu NO es solo un parametro de velocidad en esas "
                      "horas: cruzalas con el censo de horas frágiles "
                      "(m_e_empates_<caso>.json; censo_fragiles.py)")
    elif coinciden and len(coinciden) >= 5:
        lineas.append("  => en las horas comparables, mu solo cambia la velocidad")
    else:
        lineas.append(f"  => muestra insuficiente para decirlo: "
                      f"{len(coinciden)} horas comparables (hacen falta 5)")
    return "\n".join(lineas)


# ─────────────────────────────── el censo ──────────────────────────────────
def censo(almacen, cobertura: str, mu: float) -> dict:
    """El censo de horas frágiles de un almacen (tarea 4e): el de
    `censo_fragiles.censo_almacen`, sin la lista hora a hora."""
    from censo_fragiles import censo_almacen
    c = censo_almacen(almacen, cobertura, mu)
    fragiles = [x for x in c.pop("por_hora").values() if x["fragil"]]
    c["horas"] = fragiles[:500]
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--censo", action="store_true",
                    help="censa las horas frágiles; sin esto no hay nada que "
                         "hacer "
                         "aqui, porque la sensibilidad la corre "
                         "corre_mediciones.py")
    ap.add_argument("--almacen", required=True)
    ap.add_argument("--caso", default="")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--mu", type=float, default=1.0)
    ap.add_argument("--salida", required=True)
    args = ap.parse_args(argv)
    if not args.censo:
        print("  este guion ejecutado solo hace el censo de horas "
              "frágiles: pasa "
              "--censo. La sensibilidad a mu la corre corre_mediciones.py "
              "--medicion medicion_mu")
        return 2
    r = censo(args.almacen, args.cobertura, args.mu)
    r["caso"] = args.caso
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(f"  {args.caso or args.almacen}: {r['horas_fragiles']} horas "
          f"frágiles frente a mu = {r['mu']:g} (1e-3·E) de "
          f"{r['horas_con_mercado']} con mercado", flush=True)
    print(f"  energia de esas horas {r['energia_fragil']:.1f} de "
          f"{r['energia']:.1f} (kWh) = {100 * r['fraccion']:.2f} %; la que "
          f"cambiaria de manos, {r['energia_movida']:.2f} (kWh)", flush=True)
    if r["no_reproduce"]:
        print(f"  AVISO: {r['no_reproduce']} horas no se reproducen desde el "
              f"almacen y no se juzgan", flush=True)
    if r["pasa_del_2"]:
        print("  pasa del 2 % (diagnostico): con D71 el nucleo ya publica el "
              "reposo con mu = 1 en cada hora fragil, sea cual sea el peso "
              "del caso", flush=True)
    print(f"  escrito {salida}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
