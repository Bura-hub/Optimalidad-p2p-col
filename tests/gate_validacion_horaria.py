"""
Compuerta del aparato de validacion horaria.

Vigila tres cosas, y la segunda es la que de verdad importa:

  1. que los multiplicadores del solucionador acoplado sean opt-in y que
     pedirlos no mueva el equilibrio ni un bit;
  2. que el lector unico de hora devuelva LOS MISMOS NUMEROS que las sondas
     ya validadas sobre las mismas horas;
  3. que la factura comparada cuadre: la energia que alguien vende en el
     mercado alguien la compra, el beneficio se parte en dos lados y suma, y
     el indice normalizado vive dentro de su rango.

La segunda existe porque el proyecto ya tiene SIETE resolvedores por hora
repartidos entre las sondas, todos repitiendo la misma preparacion. El
lector nuevo es el octavo, y sin esta comprobacion se separaria de los demas
sin que nadie se entere.

Las comprobaciones se saltan por separado si su pieza todavia no existe, de
modo que la compuerta sirve durante la implementacion y no solo al final.

Uso:
    python tests/gate_validacion_horaria.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
SONDA = RAIZ / "reformateo" / "documento" / "scripts" / "sonda"
SCRIPTS = RAIZ / "reformateo" / "documento" / "scripts"
SALIDAS = SONDA / "salidas"
for p in (RAIZ, SONDA, SCRIPTS):
    sys.path.insert(0, str(p))

from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402


def caso(semilla=3, J=3, I=4):
    rng = np.random.default_rng(semilla)
    return dict(
        G_net=rng.uniform(1.0, 4.0, J), D_net=rng.uniform(1.0, 4.0, I),
        a=np.zeros(J), b=rng.uniform(80.0, 200.0, J),
        lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
        G_klim=rng.uniform(0.0, 2.0, I), lam_i=np.full(I, 100.0),
        theta_i=np.full(I, 0.5), etha=rng.uniform(0.05, 0.5, I))


def _acoplado(d, multiplicadores=False):
    return solve_coupled_for_hour(
        G_net_j=d["G_net"], D_net_i=d["D_net"], a_j=d["a"], b_j=d["b"],
        lam_j=d["lam_j"], theta_j=d["theta_j"], G_klim_i=d["G_klim"],
        lam_i=d["lam_i"], theta_i=d["theta_i"], etha_i=d["etha"],
        pi_gs=900.0, pi_gb=200.0, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.01), n_points=200,
        devuelve_multiplicadores=multiplicadores)


# ── 1 · los multiplicadores ─────────────────────────────────────────────
def prueba_multiplicadores() -> list:
    fallos = []
    d = caso()
    sin = _acoplado(d, multiplicadores=False)
    hay_campo = hasattr(sin, "lam_t")
    print(f"  1 · la trayectoria tiene los campos                {'ok' if hay_campo else 'FALLA'}")
    if not hay_campo:
        return ["la trayectoria acoplada no expone los multiplicadores"]

    vacio = sin.lam_t is None and sin.bet_t is None
    print(f"      por defecto no vienen                          {'ok' if vacio else 'FALLA'}")
    if not vacio:
        fallos.append("los multiplicadores vienen sin pedirlos")

    con = _acoplado(d, multiplicadores=True)
    J, I, n_t = len(d["G_net"]), len(d["D_net"]), len(con.t)
    formas = (con.lam_t.shape == (J, n_t) and con.bet_t.shape == (I, n_t)
              and con.lam_filt_t.shape == (J, n_t)
              and con.bet_filt_t.shape == (I, n_t))
    print(f"      pidiendolos, con la forma correcta             {'ok' if formas else 'FALLA'}")
    if not formas:
        fallos.append("los multiplicadores no tienen la forma esperada")

    igual = (np.array_equal(sin.pi_star, con.pi_star)
             and np.array_equal(sin.P_star, con.P_star))
    print(f"      el equilibrio no se mueve, bit a bit           {'ok' if igual else 'FALLA'}")
    if not igual:
        fallos.append("pedir los multiplicadores mueve el equilibrio")
    return fallos


# ── 2 · el lector reconcilia con las sondas ─────────────────────────────
def prueba_lector() -> list:
    try:
        from validacion import hora as H          # noqa: F401
        from paso_a_paso import carga
        import pandas as pd
    except ImportError as e:
        print(f"  2 · el lector unico                             (aun no existe: {e})")
        return []

    tabla = SALIDAS / "eficiencia_m1.csv"
    if not tabla.exists():
        print("  2 · el lector unico              (falta eficiencia_m1.csv, se salta)")
        return []

    fallos = []
    ef = pd.read_csv(tabla)
    dat = carga("m1")
    print("  2 · el lector devuelve lo mismo que las sondas")
    print("      (la sonda de eficiencia NO aplica la restricción de")
    print("       participación y el lector sí; donde muerde, no son")
    print("       comparables y lo que se exige es que el volumen BAJE)")
    n_comp, n_part = 0, 0
    for k in ef.k.head(8):
        h = H.lee(dat, int(k))
        fila = ef[ef.k == k].iloc[0]
        d_vol = abs(h.volumen - float(fila.vol_aco))
        d_ef = abs(h.eficiencia - float(fila.ef_aco))
        if h.retirados:
            # la participación retiró a alguien: el lector mueve menos
            n_part += 1
            ok = h.volumen < float(fila.vol_aco) + 1e-9
            print(f"      hora {int(k):5d}  participación retira "
                  f"{len(h.retirados)}  volumen {h.volumen:8.3f} < "
                  f"{float(fila.vol_aco):8.3f}   {'ok' if ok else 'FALLA'}")
            if not ok:
                fallos.append(f"con participación el volumen no baja en la hora {int(k)}")
        else:
            n_comp += 1
            ok = (d_vol < 1e-6 and d_ef < 1e-3
                  and h.J == int(fila.J) and h.I == int(fila.I))
            print(f"      hora {int(k):5d}  volumen {d_vol:.2e}  eficiencia "
                  f"{d_ef:.2e}   {'ok' if ok else 'FALLA'}")
            if not ok:
                fallos.append(f"el lector no reconcilia en la hora {int(k)}")
    print(f"      {n_comp} horas comparables · {n_part} con participación activa")
    if n_comp == 0:
        fallos.append("ninguna hora comparable; la compuerta no vigila nada")
    return fallos


# ── 3 · la factura cuadra ───────────────────────────────────────────────
def prueba_factura() -> list:
    try:
        from validacion import dia as Dia, factura as F
        from paso_a_paso import carga
    except ImportError as e:
        print(f"  3 · la factura comparada                        (aun no existe: {e})")
        return []

    fallos = []
    dat = carga("m1")
    _, horas = Dia.recorre("m1", "2025-05-02", presupuesto_s=120)
    f = F.calcula(dat, horas)

    d_e = abs(float(f.kwh_vende_p2p.sum() - f.kwh_compra_p2p.sum()))
    ok_e = d_e < 1e-6
    print(f"  3 · lo que unos venden, otros lo compran   dif {d_e:.2e}   "
          f"{'ok' if ok_e else 'FALLA'}")
    if not ok_e:
        fallos.append("la factura no cuadra la energia del mercado")

    ok_b = np.allclose(f.beneficio,
                       f.beneficio_vendedor + f.beneficio_comprador, atol=1e-6)
    print(f"      el beneficio se parte en dos y suma            {'ok' if ok_b else 'FALLA'}")
    if not ok_b:
        fallos.append("el beneficio no se parte correctamente")

    act = f[f.rango_max > f.rango_min]
    ok_i = bool((act.indice >= -1e-9).all() and (act.indice <= 1 + 1e-9).all())
    print(f"      el indice normalizado queda en su rango        {'ok' if ok_i else 'FALLA'}")
    if not ok_i:
        fallos.append("el indice normalizado se sale de [0, 1]")
    return fallos


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("  Compuerta del aparato de validación horaria")
    print("=" * 70)
    fallos = prueba_multiplicadores() + prueba_lector() + prueba_factura()
    print()
    if fallos:
        for f in fallos:
            print(f"  FALLA: {f}")
        return 1
    print("  COMPUERTA DE VALIDACIÓN HORARIA EN VERDE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
