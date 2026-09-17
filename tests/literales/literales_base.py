"""Literales de la identidad al bit de las vias alternada y acoplada, calculados
con el CODIGO BASE de la tarea 2 del reposo, el commit a392cbd.

Imprime el bloque de literales que va en `tests/test_reposo_motor.py`
(`HUELLA_BASE` y `BASE_BIT`). Uso, desde la raiz del repositorio, con una
carpeta fuera de el:
    git archive a392cbd core data | tar -x -C <carpeta>
    python -u tests/literales/literales_base.py <carpeta>
`git archive` solo lee. El guion comprueba que importa el codigo de esa
carpeta y no el del repositorio. Ver README.md.
"""
import hashlib
import platform
import sys
from pathlib import Path

import numpy as np
import scipy

BASE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(BASE))

import core.ems_p2p as motor  # noqa: E402
from core.ems_p2p import SolverParams, _run_hour_worker  # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402

assert Path(motor.__file__).resolve().is_relative_to(BASE), motor.__file__
assert not hasattr(motor, "METODOS"), "no es el codigo base"

PGS, PGB = 1250.0, 114.0
T_ACO = 0.002
PISO_H43 = np.array([600.0, 300.0])


def _caso(N=5, T=72, semilla=19):
    # Copia literal de tests/gate_c165_desglose_horario._caso (ese modulo
    # pone la raiz del repositorio en sys.path al importarse, y con ella el
    # codigo nuevo).
    rng = np.random.default_rng(semilla)
    D = rng.uniform(3.0, 14.0, (N, T))
    G = np.zeros((N, T))
    for k in range(T):
        h = k % 24
        if 6 <= h <= 18:
            G[:, k] = rng.uniform(0.0, 20.0, N) * np.sin(np.pi * (h - 6) / 12)
    return D, G


def _hora():
    # Copia de tests/test_criterio_reparto._hora.
    D, G = _caso(T=24)
    N = D.shape[0]
    a = np.zeros(N); b = np.full(N, 225.0); c = np.zeros(N)
    lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)
    for k in range(D.shape[1]):
        g_klim = compute_generation_limit(G[:, k], a, b, c, PGS)
        _, sids, bids = classify_agents(g_klim, D[:, k])
        if sids and bids:
            return dict(k=k, g_klim=g_klim, d_k=D[:, k].copy(),
                        g_k=G[:, k].copy(), sids=sids, bids=bids, a=a, b=b,
                        c=c, lam=lam, theta=theta, etha=etha, D=D, G=G)


def huella(h):
    m = hashlib.sha256()
    for clave in ("g_klim", "d_k", "g_k", "a", "b", "lam", "theta", "etha"):
        m.update(np.ascontiguousarray(h[clave], dtype=np.float64).tobytes())
    m.update(np.array([h["k"]] + list(h["sids"]) + [-1] + list(h["bids"]),
                      dtype=np.int64).tobytes())
    m.update(np.array([PGS, PGB, T_ACO, *PISO_H43], dtype=np.float64)
             .tobytes())
    return m.hexdigest()[:16]


def _args32(h, metodo, pi_gb_j=None):
    sv = SolverParams()
    return (h["k"], h["g_klim"], h["d_k"], h["g_k"], h["sids"], h["bids"],
            h["a"], h["b"], h["lam"], h["theta"], h["etha"],
            PGS, PGB, sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
            sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
            sv.ode_method, sv.buyer_competition,
            metodo, T_ACO, pi_gb_j, False,
            1e-6, None, None, "factible", "precio", 0.01)


def _hex(x):
    return [float(v).hex() for v in np.ravel(np.asarray(x, dtype=float))]


def main():
    h = _hora()
    print(f"# huella {huella(h)}; {platform.system()} {platform.python_version()}"
          f" numpy {np.__version__} scipy {scipy.__version__}")
    print("BASE_BIT = {")
    for metodo in ("alternado", "acoplado"):
        for nombre, piso in (("sin_piso", None), ("con_h43", PISO_H43)):
            r = _run_hour_worker(_args32(h, metodo, pi_gb_j=piso))
            print(f"    ({metodo!r}, {nombre!r}): dict(")
            if r.P_star is None:
                print("        P_star=None, pi_star=None,")
            else:
                print(f"        forma={tuple(np.shape(r.P_star))!r},")
                print(f"        P_star={_hex(r.P_star)!r},")
                print(f"        pi_star={_hex(r.pi_star)!r},")
            print(f"        escalares={[float(getattr(r, c)).hex() for c in ('SC', 'SS', 'IE', 'PS', 'PSR', 'Wj_total', 'Wi_total', 'norm_rel_final', 'horizonte_usado', 'residuo_reparto')]!r},")
            print(f"        retirados={list(map(int, r.retirados))!r}, "
                  f"iters_used={int(r.iters_used)}, "
                  f"evaluaciones={int(r.evaluaciones)},")
            print(f"        motivo={r.motivo!r}, "
                  f"parada_acoplado={r.parada_acoplado!r}),")
    print("}")


if __name__ == "__main__":
    main()
