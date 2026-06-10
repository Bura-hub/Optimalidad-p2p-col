"""
test_price_monotonicity_in_imbalance.py — P1 corto (ADR-0038, tier 0).

Versión pytest de la hipótesis económica del precio. Tras el tier 1
(2026-06-10) el criterio se reestructuró: la propiedad GARANTIZADA por la
teoría es el orden de extremos (escasez alta paga más que exceso alto) y
la pertenencia a la banda [π_gb, π_gs]; la monotonía fina punto a punto
muestrea la "coordenada lenta" del precio del replicador (se observó un
atractor intermedio ~493 en SYN, dependiente de plataforma/ventana) y se
evalúa como SOFT en el smoke P1 (`scripts/smoke_price_dynamics.py`), no
aquí.
"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import numpy as np

from smoke_price_dynamics import _fixture_h14, _solve_fixture_hour


def test_extremos_y_banda():
    G_net, D_net, a_j, b_j, etha_i, pgs, pgb = _fixture_h14()
    band = pgs - pgb
    base = float(np.sum(D_net) / np.sum(G_net))
    pis = {}
    for r_target in (0.5, 4.0):
        _, pi = _solve_fixture_hour(G_net, D_net * (r_target / base),
                                    a_j, b_j, etha_i, pgs, pgb)
        assert pi is not None, f"solver NaN en r={r_target}"
        m = float(np.mean(pi))
        assert pgb - 1e-6 <= m <= pgs + 1e-6, \
            f"π*={m:.0f} fuera de banda en r={r_target}"
        pis[r_target] = m
    assert pis[4.0] > pis[0.5] + 0.05 * band, (
        f"escasez alta (r=4 → π*={pis[4.0]:.0f}) debe pagar más que "
        f"exceso alto (r=0.5 → π*={pis[0.5]:.0f}) por ≥5% de banda")
