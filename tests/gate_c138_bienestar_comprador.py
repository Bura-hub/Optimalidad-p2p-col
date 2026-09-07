"""
Compuerta de H-39: el bienestar del comprador y las fuentes que no coinciden.

El termino que penaliza competir con los demas compradores esta escrito de
dos formas distintas en las fuentes del modelo base:

    IEEE Latin America Trans. 23(8) 2025, ec. (11)
                                  -beta_i * sum_{k != i} pi_k * sum_j P_jk
    documento extenso, ec. (14)   la misma forma
    JoinFinal.m:188 (comentada)   la misma forma
    Bienestar6p.py, Welfarei      sum_{k != i} pi_k * sum_j P_ji

Las tres primeras multiplican por la energia del comprador AJENO; la cuarta,
por la PROPIA. Coinciden exactamente cuando todos los compradores compran lo
mismo, y divergen en cuanto no.

**El proyecto sigue a la version arbitrada**, que es la especificacion
publicada y coincide con el MATLAB (H-40). Esta compuerta fija esa eleccion, mide el tamano de
la discrepancia para que no se pierda, y comprueba que la eleccion no puede
mover ningun flujo ni ningun precio.

Uso:
    python tests/gate_c138_bienestar_comprador.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.replicator_buyers import buyer_welfare, solve_buyers  # noqa: E402
from core.replicator_sellers import solve_sellers  # noqa: E402

ORIGEN = RAIZ / "Documentos" / "copy" / "Bienestar6p.py"


def welfarei_del_script():
    """Extrae `Welfarei` del script del modelo base sin ejecutar el resto.

    Ese fichero lee un libro de cálculo al cargarse, de modo que no se puede
    importar; se compila solo la definición que interesa.
    """
    arbol = ast.parse(ORIGEN.read_text(encoding="utf-8", errors="replace"))
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "Welfarei":
            ambito: dict = {"np": np, "sum": sum, "range": range}
            exec(compile(ast.Module([nodo], []), str(ORIGEN), "exec"), ambito)
            return ambito["Welfarei"]
    raise AssertionError("no se encontró Welfarei en el script del modelo base")


def forma_del_articulo(pi_i, P_mat, G_klim_i, lam_i, theta_i, etha_i):
    """La ecuación (11) de la versión arbitrada, aparte para poder compararla."""
    I = len(pi_i)
    matriz = np.ones((I, I)) - np.eye(I)
    compe = [sum(matriz[i][k] * pi_i[k] * float(np.sum(P_mat[:, k]))
                 for k in range(I)) for i in range(I)]
    return sum(
        lam_i[i] * G_klim_i[i] - theta_i[i] * G_klim_i[i]**2
        + float(np.sum(P_mat[:, i])) / (np.log(abs(pi_i[i]) + 1) + 1e-12)
        - compe[i] * etha_i[i]
        for i in range(I))


def caso(semilla=7, J=3, I=4):
    rng = np.random.default_rng(semilla)
    return dict(
        pi_i=rng.uniform(150.0, 900.0, I),
        # energías deliberadamente distintas entre compradores: es justo ahí
        # donde las dos formas del término dejan de coincidir
        P_mat=rng.uniform(0.05, 4.0, (J, I)),
        G_klim_i=rng.uniform(0.0, 3.0, I),
        lam_i=np.full(I, 100.0), theta_i=np.full(I, 0.5),
        etha_i=rng.uniform(0.05, 0.5, I))


def main() -> int:
    fallos = []
    d = caso()
    I, J = len(d["pi_i"]), d["P_mat"].shape[0]
    args = (d["pi_i"], d["P_mat"], d["G_klim_i"], d["lam_i"], d["theta_i"],
            d["etha_i"])

    # ---- 1 · seguimos la forma del artículo -----------------------------
    art = forma_del_articulo(*args)
    nuestro = buyer_welfare(*args)
    dif = abs(nuestro - art)
    ok = dif <= 1e-9 * max(1.0, abs(art))
    print(f"  1 · seguimos la ecuación (11) arbitrada    dif {dif:.3e}   "
          f"{'ok' if ok else 'FALLA'}")
    print(f"      arbitrada {art:.10f} · nuestro {nuestro:.10f}")
    if not ok:
        fallos.append("el bienestar del comprador se apartó de la ecuación (11)")

    # ---- 2 · el script del modelo base discrepa, y cuánto ---------------
    orig = welfarei_del_script()
    # el script devuelve -sum(Wi); nuestra función devuelve +sum(Wi)
    script = -float(orig(d["pi_i"], d["P_mat"], I, range(J), range(I),
                         d["etha_i"], d["lam_i"], d["G_klim_i"], d["theta_i"]))
    brecha = abs(script - art)
    hay = brecha > 1e-6
    print(f"  2 · el script del modelo base discrepa      dif {brecha:.3e}   "
          f"{'ok' if hay else 'FALLA'}")
    print(f"      script   {script:.10f} · arbitrada {art:.10f}")
    if not hay:
        fallos.append("la compuerta no distingue las dos formas; ya no vigila nada")

    # ---- 3 · la elección no puede mover la dinámica ---------------------
    rng = np.random.default_rng(11)
    G_net = rng.uniform(0.5, 4.0, J)
    D_net = rng.uniform(0.5, 4.0, I)
    a = np.zeros(J); b = rng.uniform(80.0, 200.0, J)
    pi_gb, pi_gs = 200.0, 900.0
    pi = np.full(I, pi_gb)
    P = np.clip(np.tile(D_net / J, (J, 1)), 1e-10, None)
    for _ in range(3):
        P = solve_sellers(pi, G_net, D_net, a, b, tau=0.001,
                          t_span=(0.0, 0.005), n_points=150, method="LSODA")
        pi = np.clip(solve_buyers(P, a, b, d["etha_i"], pi_gs=pi_gs,
                                  pi_gb=pi_gb, tau=0.01, t_span=(0.0, 0.005),
                                  n_points=150), pi_gb, pi_gs)
    # se comprueba sobre el árbol sintáctico, no sobre el texto, porque el
    # nombre aparece en comentarios que no son llamadas
    llamantes = []
    for fichero in ("replicator_buyers.py", "replicator_sellers.py",
                    "coupled_ode_convergence.py"):
        arbol = ast.parse((RAIZ / "core" / fichero).read_text(
            encoding="utf-8", errors="replace"))
        for nodo in ast.walk(arbol):
            if not (isinstance(nodo, ast.FunctionDef)
                    and nodo.name.startswith("solve_")):
                continue
            for hijo in ast.walk(nodo):
                if (isinstance(hijo, ast.Call)
                        and getattr(hijo.func, "id", None) == "buyer_welfare"):
                    llamantes.append(f"{fichero}:{nodo.name}")
    aislado = not llamantes
    print(f"  3 · ninguna dinámica llama al bienestar               "
          f"{'ok' if aislado else 'FALLA'}")
    print(f"      precios en {pi.min():.2f} … {pi.max():.2f} · "
          f"volumen {P.sum():.4f} kWh")
    if llamantes:
        print(f"      lo llaman: {', '.join(sorted(set(llamantes)))}")
        fallos.append("el bloque de precios usa el bienestar")

    print()
    if fallos:
        for f in fallos:
            print(f"  FALLA: {f}")
        return 1
    print("  COMPUERTA H-39 SUPERADA")
    print("  La discrepancia entre la versión arbitrada y el script del "
          "modelo base sigue abierta;")
    print("  el proyecto sigue a la arbitrada. Ver H-40.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
