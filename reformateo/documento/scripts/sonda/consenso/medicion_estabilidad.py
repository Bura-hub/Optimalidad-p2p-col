"""M-D: si el reposo en forma cerrada es ESTABLE para la dinamica regularizada.

QUE DECIDE. La frase con que se enuncia el resultado en la tesis. Si todas las
direcciones son estables, el reposo es «el reposo al que la dinamica llega»; si
alguna no lo es, la frase pasa a «unico reposo, estable en lo medido», con la
lista de horas donde no.

COMO. En cada hora de la muestra: se arma el estado en el reposo cerrado (el
reparto P y los precios del nucleo, el jugador virtual en su techo, y los
multiplicadores y filtros en su arranque de siempre, como hace
`tests/gate_reposo_cero_dinamica.py`), y se calcula por diferencias centradas
el jacobiano del sistema REDUCIDO: el bloque de los precios y el del reparto,
con el termino entropico (mu = 1) y sin acelerar. De ahi, sus valores propios.

LAS DOS DIRECCIONES NEUTRAS son conocidas y no cuentan: la suma de los precios
de los I+1 jugadores se conserva exactamente (la aptitud media del replicador
la anula), y la suma del reparto tambien (el termino entropico la conserva y el
replicador la deja quieta sobre el simplejo). Un valor propio nulo en esas dos
direcciones es la conservacion, no una inestabilidad.

EL RESIDUO, que hay que leer antes que los valores propios. Los multiplicadores
de capacidad no tienen reposo: crecen mientras la restriccion muerda, de modo
que en las horas rigidas el estado armado NO es un punto de reposo del sistema
completo, aunque lo sea del reducido. Por eso cada hora publica el residuo
|dP/dt| y |dpi/dt| en ese punto: donde el residuo es grande, el jacobiano
describe la vecindad de un punto por el que la trayectoria pasa, no de uno en
el que se queda, y el resultado se lee con esa reserva. Las cifras de la
compuerta (0 en la hora 853, 3,0e-4 en la 2120, 86,3 en la 874 y 32,7 en la
4766) dicen exactamente eso.

    python -u medicion_estabilidad.py \\
        --horas SALIDAS_SERVIDOR/validacion_reposo \\
        --salida SALIDAS_SERVIDOR/validacion_reposo/m_d_estabilidad.json \\
        --por-regimen 10

ACEPTACION: partes reales negativas fuera de las direcciones neutras en el
100 % de las horas.

COSTO. Unas cuarenta evaluaciones del lado derecho por hora y un problema de
valores propios de veinte por veinte: segundos para las cincuenta horas.
"""
import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import numpy as np                                    # noqa: E402
import arnes as A                                     # noqa: E402
import preparacion as PR                              # noqa: E402

MEDICION = "M-D"
QUE_DECIDE = "si el reposo en forma cerrada es estable"

GRUPOS = ("interiores", "topados", "suma_no_cabe", "mixto", "dos_vendedores",
          "compradores_cortos_sin_cesmag")
CASOS = ("E0", "K1", "E4", "E5")
MU = 1.0
# Un valor propio con parte real por debajo de esto, en relacion con el radio
# espectral, cuenta como neutro y no como inestable.
TOL_NEUTRO = 1e-8
# Cuanto tiene que alinearse un vector propio con una direccion conservada
# para darlo por esa direccion.
TOL_ALINEADO = 0.9


def estado_en_el_reposo(e, cerrada, precios0) -> np.ndarray:
    """El estado completo del arnes con el reparto y los precios del reposo."""
    I, J = len(e["dn"]), len(e["gn"])
    virtual = (float(precios0[-1]) if precios0 is not None
               else float(np.max(e["techo"])))
    pi_all = np.append(np.asarray(cerrada["p"], float), virtual)
    P = np.asarray(cerrada["P"], float)
    return np.concatenate([pi_all, 0.1 * np.ones(J), np.ones(J), P.ravel(),
                           0.1 * np.ones(J), 0.1 * np.ones(I),
                           np.zeros(J), np.zeros(I)])


def jacobiano_reducido(rhs, X, ix):
    """Diferencias centradas sobre los bloques de precios y de reparto."""
    I, J = ix["I"], ix["J"]
    n_pi = I + 1
    i_P = ix["P"].start
    idx = np.concatenate([np.arange(0, n_pi),
                          np.arange(i_P, i_P + J * I)])
    n = idx.size
    Jac = np.zeros((n, n))
    for c, k in enumerate(idx):
        h = max(1e-6, 1e-6 * abs(float(X[k])))
        Xp = X.copy(); Xp[k] += h
        Xm = X.copy(); Xm[k] -= h
        Jac[:, c] = (np.asarray(rhs(0.0, Xp), float)[idx]
                     - np.asarray(rhs(0.0, Xm), float)[idx]) / (2.0 * h)
    return Jac, idx


def direcciones_neutras(I: int, J: int) -> np.ndarray:
    """Las dos sumas que la dinamica conserva, como vectores unitarios.

    Tienen soportes disjuntos (precios y reparto), de modo que son ortogonales
    y forman una base ortonormal del espacio de lo conservado."""
    n = (I + 1) + J * I
    v1 = np.zeros(n); v1[:I + 1] = 1.0            # suma de los precios
    v2 = np.zeros(n); v2[I + 1:] = 1.0            # suma del reparto
    return np.array([v1 / np.linalg.norm(v1), v2 / np.linalg.norm(v2)])


def alineacion(w, neutras) -> float:
    """Que fraccion de la norma de w cae en el espacio de lo conservado.

    Es la norma de la proyeccion sobre la base ortonormal `neutras`, CON SIGNO:
    un vector de signos alternos y suma cero da 0, aunque su valor absoluto
    fuera paralelo a la suma. La version anterior tomaba `np.abs` del vector
    propio y, ademas, el maximo sobre las dos direcciones en vez de la norma de
    la proyeccion; con las dos cosas, una direccion ortogonal a lo conservado
    se descartaba como neutra y M-D podia publicar «estable» siendo inestable
    (grave 2 de la revision de 4c).
    """
    w = np.asarray(w, dtype=float)
    nw = float(np.linalg.norm(w))
    if nw == 0.0:
        return 0.0
    return float(np.linalg.norm(neutras @ (w / nw)))


def clasifica_valores_propios(Jac, I: int, J: int) -> dict:
    """Los valores propios del reducido, separando lo conservado de lo inestable.

    Un valor propio con parte real por debajo de TOL_NEUTRO veces el radio
    espectral no cuenta. Uno por encima es NEUTRO solo si su subespacio
    invariante cae en el de lo conservado:
      - valor propio real: su vector propio (la parte real o la imaginaria del
        que devuelve `eig`, la de mayor norma, porque `eig` puede devolverlo
        con una fase compleja);
      - par conjugado: el subespacio invariante es el plano {Re w, Im w}, y es
        neutro solo si LAS DOS partes estan alineadas con lo conservado. El par
        se cuenta una vez.
    Devuelve dict(inestables, mayores, radio).
    """
    vals, vecs = np.linalg.eig(np.asarray(Jac, dtype=float))
    radio = max(float(np.max(np.abs(vals))), 1e-300)
    tol = TOL_NEUTRO * radio
    neutras = direcciones_neutras(I, J)
    inestables = []
    for k in range(vals.size):
        re = float(vals[k].real)
        im = float(vals[k].imag)
        if re <= tol:
            continue
        w = vecs[:, k]
        if abs(im) > tol:
            if im < 0.0:
                continue                   # el conjugado ya se conto
            alin = min(alineacion(w.real, neutras), alineacion(w.imag, neutras))
        else:
            v = (w.real if np.linalg.norm(w.real) >= np.linalg.norm(w.imag)
                 else w.imag)
            alin = alineacion(v, neutras)
        if alin >= TOL_ALINEADO:
            continue
        inestables.append(dict(re=re, im=im, alineacion=alin))
    orden = np.argsort(-vals.real)
    return dict(inestables=inestables, radio=radio,
                mayores=[dict(re=float(vals[k].real), im=float(vals[k].imag))
                         for k in orden[:6]])


def analiza(spec) -> dict:
    pre = PR.prepara(spec)
    if pre["sin_mercado"]:
        return dict(spec=spec, sin_mercado=True, avisos=pre["avisos"])
    e = pre["e"]
    cerrada = pre["referencias"]["cerrada"]
    rhs, _X0, ix = A.construye(e, mu_ent=MU, precios0=pre["precios0"])
    I, J = ix["I"], ix["J"]
    X = estado_en_el_reposo(e, cerrada, pre["precios0"])
    d = np.asarray(rhs(0.0, X), float)
    residuo_pi = float(np.max(np.abs(d[:I])))
    residuo_P = float(np.max(np.abs(d[ix["P"]])))
    Jac, _idx = jacobiano_reducido(rhs, X, ix)
    if not np.all(np.isfinite(Jac)):
        return dict(spec=spec, sin_mercado=False, error="jacobiano no finito",
                    residuo_pi=residuo_pi, residuo_P=residuo_P)
    c = clasifica_valores_propios(Jac, I, J)
    inestables = c["inestables"]
    return dict(spec=spec, sin_mercado=False,
                regimen=cerrada["regimen"], E=float(cerrada["E"]),
                I=I, J=J, radio=c["radio"],
                residuo_pi=residuo_pi, residuo_P=residuo_P,
                n_inestables=len(inestables), inestables=inestables[:10],
                mayores=c["mayores"],
                quieta=bool(residuo_P <= 1e-3 * max(float(cerrada["E"]), 1e-12)),
                estable=bool(not inestables),
                recorte_movio=bool(pre.get("recorte_movio", False)))


def specs(horas, por_regimen=10):
    fuera = []
    for grupo in GRUPOS:
        n = 0
        for caso in CASOS:
            for h in horas.get(caso, {}).get(grupo, []):
                fuera.append(dict(medicion=MEDICION, caso=caso,
                                  fecha=h["fecha"], grupo=grupo,
                                  etq="jacobiano en el reposo",
                                  nivel="sigma", piso_juego="marginal"))
                n += 1
                if n >= por_regimen:
                    break
            if n >= por_regimen:
                break
    return fuera


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horas", default="SALIDAS_SERVIDOR/validacion_reposo")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--por-regimen", type=int, default=10)
    args = ap.parse_args(argv)

    from corre_mediciones import carga_horas, limpia, banner_vacia
    horas = carga_horas(Path(args.horas).resolve())
    tareas = specs(horas, args.por_regimen)
    print(f"M-D: {QUE_DECIDE} - {len(tareas)} horas", flush=True)
    if not tareas:
        # Medio 1: una medicion planificada sin ninguna hora no es un exito.
        print(banner_vacia(MEDICION, Path(args.horas)), flush=True)
        return 3
    resultados = []
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    for n, sp in enumerate(tareas):
        try:
            r = analiza(sp)
        except Exception as exc:                            # noqa: BLE001
            print(f"  [{n}] FALLA {sp['caso']} {sp['fecha']}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
            r = dict(spec=sp, error=f"{type(exc).__name__}: {exc}")
        resultados.append(r)
        salida.write_text(json.dumps(limpia(resultados)), encoding="utf-8")
        if r.get("sin_mercado") or r.get("error"):
            continue
        print(f"  [{n}] {sp['caso']} {sp['fecha']} {r['regimen']:<20s} "
              f"I={r['I']} J={r['J']} residuo |dpi|={r['residuo_pi']:.2e} "
              f"|dP|={r['residuo_P']:.2e} mayor Re={r['mayores'][0]['re']:.3e} "
              f"inestables={r['n_inestables']} "
              f"{'ESTABLE' if r['estable'] else 'NO ESTABLE'}", flush=True)
    utiles = [r for r in resultados if not r.get("sin_mercado")
              and not r.get("error")]
    # Medio 5: una hora cuyo recorte movio el reposo no cuenta; se dice.
    movidas = [r for r in utiles if r.get("recorte_movio")]
    utiles = [r for r in utiles if not r.get("recorte_movio")]
    # m2 de la re-revision: una hora que cae en dos grupos de la muestra se
    # analiza dos veces (el plan no se toca, para no desincronizarlo de la
    # noche ya lanzada); en el resumen cuenta una sola.
    vistas, unicas = set(), []
    for r in utiles:
        clave = (r["spec"]["caso"], r["spec"]["fecha"])
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(r)
    if len(unicas) < len(utiles):
        print(f"  {len(utiles) - len(unicas)} horas repetidas (caen en dos "
              f"grupos) cuentan una sola vez", flush=True)
    utiles = unicas
    if movidas:
        print(f"  {len(movidas)} horas fuera del veredicto porque el recorte "
              f"movio su reposo:", flush=True)
        for r in movidas[:10]:
            print(f"    {r['spec']['caso']} {r['spec']['fecha']}", flush=True)
    porreg = {}
    for r in utiles:
        # Una hora cuenta para el veredicto solo si el punto ES de reposo
        # tambien para el sistema completo, es decir si el residuo es pequeno
        # frente al volumen de la hora. Donde no lo es, el jacobiano describe
        # otra cosa y se cuenta aparte.
        quieta = r["residuo_P"] <= 1e-3 * max(r["E"], 1e-12)
        n, ok, fuera = porreg.get(r["regimen"], (0, 0, 0))
        porreg[r["regimen"]] = (n + 1, ok + (1 if (quieta and r["estable"])
                                            else 0),
                                fuera + (0 if quieta else 1))
    print("", flush=True)
    print("  ESTABILIDAD POR REGIMEN", flush=True)
    for reg, (n, ok, fuera) in sorted(porreg.items()):
        peor = max((x["residuo_P"] for x in utiles if x["regimen"] == reg),
                   default=0.0)
        quietas = n - fuera
        # Medio 8: con menos de PR.MIN_MUESTRA horas quietas no hay rotulo.
        if quietas < PR.MIN_MUESTRA:
            rotulo = f"muestra insuficiente (n = {quietas})"
        elif ok == quietas:
            rotulo = f"estable en todas (n = {quietas})"
        else:
            rotulo = f"NO estable en {quietas - ok} (n = {quietas})"
        print(f"    {reg:<22s} {ok}/{quietas} estables de las que estan "
              f"quietas ({fuera} con residuo grande, aparte) - peor residuo "
              f"|dP| = {peor:.2e} (kWh por unidad de tiempo) - {rotulo}",
              flush=True)
    print("    Una hora con residuo grande no desmiente el reposo: dice que "
          "sus multiplicadores", flush=True)
    print("    todavia se mueven en ese punto, que es lo que ya sabia la "
          "compuerta de la dinamica.", flush=True)
    print(f"  escrito {salida}", flush=True)
    if not utiles:
        print("  NINGUNA HORA SE PUDO JUZGAR: mira los FALLA y los sin mercado "
              "de arriba", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
