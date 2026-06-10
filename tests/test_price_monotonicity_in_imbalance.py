"""
test_price_monotonicity_in_imbalance.py — P1 corto (ADR-0038, tier 0).

Versión pytest (4 puntos) de la hipótesis económica nunca testeada: el
precio de clearing π* debe ser no-decreciente en el ratio de escasez
r = ΣD_net/ΣG_net (escasez → π*↑; exceso → π*↓). El barrido completo de
10 puntos vive en `scripts/smoke_price_dynamics.py` (P1).
"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import numpy as np

from smoke_price_dynamics import (
    _fixture_h14, _solve_fixture_hour, _spearman,
)


def test_monotonia_4_puntos():
    G_net, D_net, a_j, b_j, etha_i, pgs, pgb = _fixture_h14()
    band = pgs - pgb
    base = float(np.sum(D_net) / np.sum(G_net))
    pis, used = [], []
    for r_target in (0.5, 1.0, 2.0, 4.0):
        _, pi = _solve_fixture_hour(G_net, D_net * (r_target / base),
                                    a_j, b_j, etha_i, pgs, pgb)
        assert pi is not None, f"solver NaN en r={r_target}"
        pis.append(float(np.mean(pi)))
        used.append(r_target)
    rho = _spearman(np.array(used), np.array(pis))
    assert rho >= 0.95, f"Spearman={rho:.3f} (<0.95): π* no crece con escasez"
    for i in range(1, len(pis)):
        drop = (pis[i - 1] - pis[i]) / band
        assert drop <= 0.01, \
            f"descenso de π* {drop:.3%} banda entre r={used[i-1]} y r={used[i]}"
