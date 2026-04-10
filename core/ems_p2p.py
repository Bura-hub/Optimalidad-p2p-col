"""
ems_p2p.py
----------
Motor del EMS P2P para la tesis de Brayan López.

SIN programa DR. D es insumo fijo (datos reales).
Pipeline: G_klim → GDR → Stackelberg (RD+LR) → liquidación → métricas.
"""

import sys
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

from .market_prep        import compute_generation_limit, classify_agents, net_quantities
from .replicator_sellers import solve_sellers, seller_welfare
from .replicator_buyers  import solve_buyers, buyer_welfare
from .settlement         import (
    residual_settlement, self_consumption_index, self_sufficiency_index,
    compute_savings, equity_index, welfare_distribution,
)

# ── Barra de progreso ─────────────────────────────────────────────────────────
# Usa tqdm si está instalado; si no, implementación propia sin dependencias.

try:
    from tqdm import tqdm as _tqdm
    def _make_bar(total, desc):
        return _tqdm(total=total, desc=desc, unit="h", ncols=72,
                     bar_format="{desc}: {percentage:3.0f}%|{bar}| "
                                "{n_fmt}/{total_fmt}h "
                                "[{elapsed}<{remaining}, {rate_fmt}]")
except ImportError:
    class _make_bar:
        """Barra de progreso manual — no requiere tqdm."""
        _W = 28  # ancho de la barra

        def __init__(self, total, desc):
            self.total = total
            self.desc  = desc
            self.n     = 0
            self.t0    = time.time()
            self._last_pct = -1
            self._draw(force=True)

        def update(self, n=1):
            self.n += n
            pct = int(self.n / self.total * 100) if self.total else 100
            if pct != self._last_pct:
                self._last_pct = pct
                self._draw()

        def _draw(self, force=False):
            pct   = self.n / self.total if self.total else 1.0
            done  = int(pct * self._W)
            bar   = "█" * done + "░" * (self._W - done)
            ela   = time.time() - self.t0
            rem   = (ela / pct - ela) if pct > 1e-6 else 0.0
            rate  = f"{self.n/ela:.1f}h/s" if ela > 0.1 else "---"
            ela_s = f"{int(ela//60):02d}:{int(ela%60):02d}"
            rem_s = f"{int(rem//60):02d}:{int(rem%60):02d}"
            line  = (f"\r  {self.desc}: {int(pct*100):3d}%|{bar}| "
                     f"{self.n}/{self.total}h "
                     f"[{ela_s}<{rem_s}, {rate}]  ")
            sys.stdout.write(line)
            sys.stdout.flush()
            if self.n >= self.total:
                sys.stdout.write("\n")
                sys.stdout.flush()

        def close(self):
            if self.n < self.total:
                sys.stdout.write("\n")
                sys.stdout.flush()

        def __enter__(self): return self
        def __exit__(self, *_): self.close()


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class AgentParams:
    N:     int
    a:     np.ndarray
    b:     np.ndarray
    c:     np.ndarray
    lam:   np.ndarray
    theta: np.ndarray
    etha:  np.ndarray


@dataclass
class GridParams:
    pi_gs: float = 1250.0
    pi_gb: float =  114.0


@dataclass
class SolverParams:
    tau:               float = 0.001
    t_span:            tuple = (0.0, 0.005)
    n_points:          int   = 150
    stackelberg_iters: int   = 2
    parallel:          bool  = True


@dataclass
class HourlyResult:
    k:          int
    P_star:     Optional[np.ndarray] = None
    pi_star:    Optional[np.ndarray] = None
    P_int:      Optional[np.ndarray] = None
    P_ext:      Optional[np.ndarray] = None
    SC:         float = 0.0
    SS:         float = 0.0
    IE:         float = 0.0
    PS:         float = 0.0
    PSR:        float = 0.0
    Wj_total:   float = 0.0
    Wi_total:   float = 0.0
    seller_ids: list  = field(default_factory=list)
    buyer_ids:  list  = field(default_factory=list)
    G_klim_k:   Optional[np.ndarray] = None
    D_k:        Optional[np.ndarray] = None


# ── Worker (top-level para pickle en multiprocessing) ────────────────────────

def _run_hour_worker(args):
    (k, G_klim_k, D_k, G_raw_k, seller_ids, buyer_ids,
     a_all, b_all, lam_all, theta_all, etha_all,
     pi_gs, pi_gb, tau, t_span, n_points, n_iters) = args

    J = len(seller_ids); I = len(buyer_ids)
    res = HourlyResult(k=k, seller_ids=seller_ids, buyer_ids=buyer_ids,
                       G_klim_k=G_klim_k, D_k=D_k)
    if J == 0 or I == 0:
        return res

    a_j    = a_all[seller_ids];    b_j    = b_all[seller_ids]
    lam_j  = lam_all[seller_ids];  theta_j = theta_all[seller_ids]
    lam_i  = lam_all[buyer_ids];   theta_i = theta_all[buyer_ids]
    etha_i = etha_all[buyer_ids]

    G_net_j  = np.array([G_klim_k[j] - D_k[j] for j in seller_ids])
    D_net_i  = np.array([D_k[i]      - G_klim_k[i] for i in buyer_ids])
    D_j      = D_k[seller_ids]
    G_klim_i = G_klim_k[buyer_ids]

    P_star = (np.tile(D_net_i / J, (J, 1)) if np.sum(G_net_j) >= np.sum(D_net_i)
              else np.tile(G_net_j / I, (I, 1)).T)
    P_star = np.clip(P_star, 1e-10, None)
    pi_i   = np.full(I, pi_gb)

    for _ in range(n_iters):
        P_star = solve_sellers(pi_i, G_net_j, D_net_i, a_j, b_j,
                               tau=tau, t_span=t_span, n_points=n_points)
        pi_i   = solve_buyers(P_star, a_j, b_j, etha_i,
                              pi_gs=pi_gs, pi_gb=pi_gb,
                              tau=tau, t_span=t_span, n_points=n_points)
        pi_i   = np.clip(pi_i, pi_gb, pi_gs)

    res.P_star = P_star; res.pi_star = pi_i

    settle = residual_settlement(P_star, G_net_j, D_net_i,
                                  G_klim_k, G_raw_k, pi_gs, pi_gb,
                                  seller_ids, buyer_ids)
    res.P_int = settle["P_int"]; res.P_ext = settle["P_ext"]

    res.SC = self_consumption_index(P_star, D_k, G_klim_k)
    res.SS = self_sufficiency_index(P_star, G_klim_k, D_k)
    S_i, SR_j = compute_savings(P_star, pi_i, pi_gs, pi_gb)
    res.IE = equity_index(S_i, SR_j)
    dist   = welfare_distribution(S_i, SR_j)
    res.PS = dist["PS"]; res.PSR = dist["PSR"]
    res.Wj_total = seller_welfare(P_star, D_j, a_j, b_j, lam_j, theta_j, pi_i)
    res.Wi_total = buyer_welfare(pi_i, P_star, G_klim_i, lam_i, theta_i, etha_i)
    return res


# ── Motor principal ───────────────────────────────────────────────────────────

class EMSP2P:
    """EMS P2P sin DR para la tesis de Brayan López."""

    def __init__(self, agents: AgentParams, grid: GridParams,
                 solver: Optional[SolverParams] = None):
        self.agents = agents
        self.grid   = grid
        self.solver = solver or SolverParams()

    def run(self, D: np.ndarray, G: np.ndarray) -> tuple:
        """
        D : (N, T) demanda real fija [kW]
        G : (N, T) generación bruta [kW]
        Retorna (results: list[HourlyResult], G_klim: ndarray(N,T))
        """
        N, T = D.shape
        ag = self.agents; gr = self.grid; sv = self.solver

        # G_klim para todo el horizonte
        G_klim = np.zeros((N, T))
        for k in range(T):
            G_klim[:, k] = compute_generation_limit(
                G[:, k], ag.a, ag.b, ag.c, gr.pi_gs)

        # Empaquetar trabajos por hora
        jobs = []
        for k in range(T):
            _, sids, bids = classify_agents(G_klim[:, k], D[:, k])
            jobs.append((k, G_klim[:, k].copy(), D[:, k].copy(), G[:, k].copy(),
                         sids, bids,
                         ag.a, ag.b, ag.lam, ag.theta, ag.etha,
                         gr.pi_gs, gr.pi_gb,
                         sv.tau, sv.t_span, sv.n_points, sv.stackelberg_iters))

        # ── Ejecutar con barra de progreso ────────────────────────────
        rmap = {}
        desc = f"  Mercado P2P ({T}h)"

        if sv.parallel:
            with _make_bar(total=T, desc=desc) as bar:
                with ProcessPoolExecutor() as ex:
                    futs = {ex.submit(_run_hour_worker, j): j[0] for j in jobs}
                    for f in as_completed(futs):
                        r = f.result()
                        rmap[r.k] = r
                        bar.update(1)
        else:
            with _make_bar(total=T, desc=desc) as bar:
                for j in jobs:
                    r = _run_hour_worker(j)
                    rmap[r.k] = r
                    bar.update(1)

        results = [rmap[k] for k in range(T)]
        return results, G_klim

    def run_single_hour(self, k: int, D: np.ndarray, G: np.ndarray) -> HourlyResult:
        ag = self.agents; gr = self.grid; sv = self.solver
        G_klim_k = compute_generation_limit(G[:, k], ag.a, ag.b, ag.c, gr.pi_gs)
        _, sids, bids = classify_agents(G_klim_k, D[:, k])
        return _run_hour_worker((k, G_klim_k, D[:, k].copy(), G[:, k].copy(),
                                  sids, bids, ag.a, ag.b, ag.lam, ag.theta, ag.etha,
                                  gr.pi_gs, gr.pi_gb,
                                  sv.tau, sv.t_span, sv.n_points, sv.stackelberg_iters))
