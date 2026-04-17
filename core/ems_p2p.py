"""
ems_p2p.py
----------
Motor del EMS P2P para la tesis de Brayan López.

Implementa el EMS completo del modelo base de Chacón et al. (2025):
  Pipeline: G_klim (Alg.1 pasos 1-14) → DR program (Alg.1 pasos 15-22)
            → GDR → Stackelberg (RD+LR, Alg.2-3) → liquidación → métricas.

Si AgentParams.alpha = 0 (o no se pasa):
  El DR program devuelve D sin modificar (equivalente al caso "SIN DR"
  para datos reales donde la demanda es insumo fijo observado).
Si AgentParams.alpha > 0:
  El DR program optimiza la demanda flexible sobre el horizonte completo.
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
from .dr_program         import run_dr_program, compute_price_signal

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
    # DR Program (Algoritmo 1, pasos 15-22)
    # alpha_n ∈ [0,1]: fracción máxima de demanda flexible por agente.
    # 0.0 (defecto) = demanda fija (datos reales MTE sin gestión de carga).
    # >0            = demanda gestionable (datos sintéticos / validación Chacón).
    alpha: Optional[np.ndarray] = None

    def __post_init__(self):
        if self.alpha is None:
            self.alpha = np.zeros(self.N)


@dataclass
class GridParams:
    pi_gs: float = 1250.0
    pi_gb: float =  114.0


@dataclass
class SolverParams:
    # Parámetros calibrados contra JoinFinal.m de Chacón et al. (2025):
    #   t_span  = [0, 0.01]  →  10 constantes de tiempo del filtro (τ=0.001)
    #   n_points = 500        →  densidad de la integración numérica
    #   tau_sellers = 0.001  →  filtro de paso bajo λ/β (Generadoresfiltro.m)
    #   tau_buyers  = 0.01   →  tau3 de JoinFinal.m (bloque comprador)
    tau:               float = 0.001    # filtro vendedores (τ en JoinFinal.m)
    tau_buyers:        float = 0.01     # tau3 en JoinFinal.m (escala comprador)
    t_span:            tuple = (0.0, 0.01)   # iguala t_span=[0,0.01] de JoinFinal.m
    n_points:          int   = 500           # linspace(0,0.01,500) de JoinFinal.m
    stackelberg_iters: int   = 2    # iteraciones mínimas (min_iter)
    stackelberg_tol:   float = 1e-3  # tolerancia relativa ||P_new - P_old|| / (||P_old|| + ε)
    stackelberg_max:   int   = 10    # iteraciones máximas
    parallel:          bool  = True


@dataclass
class ConvergenceData:
    """
    Trayectorias del algoritmo RD+Stackelberg para una hora representativa.
    Permite graficar la convergencia del juego (equivalente a Figs 9-11 de Sofía).

    Campos
    ------
    hour            : índice de hora en el horizonte
    seller_ids / buyer_ids : agentes activos en esa hora
    G_net_j / D_net_i      : excedentes/déficits netos [kW]
    welfare_iters   : bienestar (Wj, Wi) por iteración Stackelberg
    P_star_iters    : P_star (J,I) por iteración
    pi_star_iters   : pi_star (I,) por iteración
    t_sellers       : eje de tiempo ODE vendedores (última iteración)
    P_traj          : (J, I, n_t)  trayectoria de potencias
    t_buyers        : eje de tiempo Euler compradores (última iteración)
    pi_traj         : (I, n_t)  trayectoria de precios
    """
    hour:           int
    seller_ids:     list
    buyer_ids:      list
    G_net_j:        np.ndarray
    D_net_i:        np.ndarray
    welfare_iters:  list   # [(Wj, Wi), ...]  longitud = n_iters
    P_star_iters:   list   # [P_star_array, ...]
    pi_star_iters:  list   # [pi_star_array, ...]
    t_sellers:      np.ndarray
    P_traj:         np.ndarray   # (J, I, n_t)
    t_buyers:       np.ndarray
    pi_traj:        np.ndarray   # (I, n_t)


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
    iters_used: int   = 0    # iteraciones Stackelberg efectivas (diagnóstico convergencia)
    seller_ids: list  = field(default_factory=list)
    buyer_ids:  list  = field(default_factory=list)
    G_klim_k:   Optional[np.ndarray] = None
    D_k:        Optional[np.ndarray] = None


# ── Worker (top-level para pickle en multiprocessing) ────────────────────────

def _run_hour_worker(args):
    (k, G_klim_k, D_k, G_raw_k, seller_ids, buyer_ids,
     a_all, b_all, lam_all, theta_all, etha_all,
     pi_gs, pi_gb, tau, tau_buyers, t_span, n_points,
     min_iter, tol, max_iter) = args

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

    iter_count = 0
    P_old = np.zeros_like(P_star)
    while iter_count < max_iter:
        P_old  = P_star.copy()
        # Algoritmo 2: RD vendedores (tau = τ de JoinFinal.m)
        P_star = solve_sellers(pi_i, G_net_j, D_net_i, a_j, b_j,
                               tau=tau, t_span=t_span, n_points=n_points)
        # Algoritmo 3: RD compradores (tau_buyers = tau3 de JoinFinal.m)
        pi_i   = solve_buyers(P_star, a_j, b_j, etha_i,
                              pi_gs=pi_gs, pi_gb=pi_gb,
                              tau=tau_buyers, t_span=t_span, n_points=n_points)
        pi_i   = np.clip(pi_i, pi_gb, pi_gs)
        iter_count += 1
        norm_rel = (np.linalg.norm(P_star - P_old)
                    / (np.linalg.norm(P_old) + 1e-9))
        if iter_count >= min_iter and norm_rel < tol:
            break

    res.P_star = P_star; res.pi_star = pi_i; res.iters_used = iter_count

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
    res.Wj_total = seller_welfare(P_star, G_net_j, a_j, b_j, lam_j, theta_j, pi_i)
    res.Wi_total = buyer_welfare(pi_i, P_star, G_klim_i, lam_i, theta_i, etha_i)
    return res


# ── Motor principal ───────────────────────────────────────────────────────────

class EMSP2P:
    """
    EMS P2P para la tesis de Brayan López.

    Implementa el Algoritmo 1 completo de Chacón et al. (2025):
      Paso 1-14 : cálculo de G_klim (límite de generación)
      Paso 15-22: programa DR → D* (demanda óptima)
    Seguido de los Algoritmos 2-3 (RD + Stackelberg).

    Si agents.alpha == 0 (defecto): el DR retorna D sin modificar,
    equivalente al modo datos-reales donde D es insumo fijo observado.
    """

    def __init__(self, agents: AgentParams, grid: GridParams,
                 solver: Optional[SolverParams] = None):
        self.agents = agents
        self.grid   = grid
        self.solver = solver or SolverParams()

    def run(self, D: np.ndarray, G: np.ndarray,
            verbose_dr: bool = False) -> tuple:
        """
        D : (N, T) demanda base [kW]  (medida o sintética)
        G : (N, T) generación bruta [kW]
        Retorna (results: list[HourlyResult], G_klim: ndarray(N,T), D_star: ndarray(N,T))

        D_star == D cuando alpha==0 (sin DR).
        D_star != D cuando alpha>0  (con DR activo).
        """
        N, T = D.shape
        ag = self.agents; gr = self.grid; sv = self.solver

        # ── Algoritmo 1, pasos 1-14: límite de generación ────────────────
        G_klim = np.zeros((N, T))
        for k in range(T):
            G_klim[:, k] = compute_generation_limit(
                G[:, k], ag.a, ag.b, ag.c, gr.pi_gs)

        # ── Algoritmo 1, pasos 15-22: programa DR ────────────────────────
        # Si alpha=0 en todos los agentes, run_dr_program devuelve D sin cambios.
        pi_k   = compute_price_signal(D, G_klim, gr.pi_gs, gr.pi_gb)
        D_star = run_dr_program(D, G_klim, pi_k, ag.alpha, verbose=verbose_dr)

        # Empaquetar trabajos por hora (usa D_star como demanda)
        jobs = []
        for k in range(T):
            _, sids, bids = classify_agents(G_klim[:, k], D_star[:, k])
            jobs.append((k, G_klim[:, k].copy(), D_star[:, k].copy(), G[:, k].copy(),
                         sids, bids,
                         ag.a, ag.b, ag.lam, ag.theta, ag.etha,
                         gr.pi_gs, gr.pi_gb,
                         sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
                         sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max))

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
        return results, G_klim, D_star

    def run_convergence(
        self,
        D:       np.ndarray,
        G:       np.ndarray,
        G_klim:  np.ndarray,
        p2p_results: list,
        n_iters_conv: int = 8,
        max_hours:    int = 2,
    ) -> list:
        """
        Captura las trayectorias ODE del algoritmo RD+Stackelberg para
        horas representativas. Usado para las gráficas de convergencia
        (equivalente a Figs 9-11 del modelo base de Sofía Chacón).

        Selecciona automáticamente:
          - La hora con mayor volumen P2P transado (caso excedente)
          - La hora con mayor déficit comunitario (caso déficit)

        Parámetros
        ----------
        p2p_results   : salida de run(), para seleccionar horas representativas
        n_iters_conv  : iteraciones Stackelberg (más que en run() para ver convergencia)
        max_hours     : número de horas a analizar (1 ó 2)

        Retorna
        -------
        lista de ConvergenceData, una por hora representativa
        """
        ag = self.agents; gr = self.grid; sv = self.solver
        N, T = D.shape

        # ── Selección de horas representativas ───────────────────────────
        active = [(r.k, float(np.sum(r.P_star))) for r in p2p_results
                  if r.P_star is not None and np.sum(r.P_star) > 1e-6]

        if not active:
            return []

        # Hora con más kWh P2P (caso excedente comunitario)
        hour_surplus = max(active, key=lambda x: x[1])[0]

        # Hora con mayor déficit comunitario (caso importación)
        deficit_by_hour = [
            (k, float(np.sum(np.maximum(D[:, k] - G_klim[:, k], 0))))
            for k in range(T)
        ]
        hour_deficit = max(deficit_by_hour, key=lambda x: x[1])[0]

        hours_to_run = list(dict.fromkeys(
            [hour_surplus, hour_deficit][:max_hours]))

        # ── Captura por hora ──────────────────────────────────────────────
        conv_list = []

        for k in hours_to_run:
            G_klim_k = G_klim[:, k]
            D_k      = D[:, k]
            G_raw_k  = G[:, k]

            _, sids, bids = classify_agents(G_klim_k, D_k)
            J = len(sids); I = len(bids)

            if J == 0 or I == 0:
                continue

            a_j    = ag.a[sids];    b_j    = ag.b[sids]
            lam_j  = ag.lam[sids];  theta_j = ag.theta[sids]
            lam_i  = ag.lam[bids];  theta_i = ag.theta[bids]
            etha_i = ag.etha[bids]

            G_net_j = np.array([G_klim_k[j] - D_k[j] for j in sids])
            D_net_i = np.array([D_k[i] - G_klim_k[i] for i in bids])
            D_j     = D_k[sids]
            G_klim_i = G_klim_k[bids]

            # Condición inicial
            if np.sum(G_net_j) >= np.sum(D_net_i):
                P_star = np.tile(D_net_i / J, (J, 1))
            else:
                P_star = np.tile(G_net_j / I, (I, 1)).T
            P_star = np.clip(P_star, 1e-10, None)
            pi_i   = np.full(I, gr.pi_gb)

            welfare_iters  = []
            P_star_iters   = []
            pi_star_iters  = []
            t_sellers_last = np.array([])
            P_traj_last    = np.zeros((J, I, 1))
            t_buyers_last  = np.array([])
            pi_traj_last   = np.zeros((I, 1))

            for it in range(n_iters_conv):
                capture = (it == n_iters_conv - 1)   # solo última iteración

                P_star, t_s, P_traj = solve_sellers(
                    pi_i, G_net_j, D_net_i, a_j, b_j,
                    tau=sv.tau, t_span=sv.t_span, n_points=sv.n_points,
                    return_traj=True,
                )
                pi_i, t_b, pi_traj = solve_buyers(
                    P_star, a_j, b_j, etha_i,
                    pi_gs=gr.pi_gs, pi_gb=gr.pi_gb,
                    tau=sv.tau, t_span=sv.t_span, n_points=sv.n_points,
                    return_traj=True,
                )
                pi_i = np.clip(pi_i, gr.pi_gb, gr.pi_gs)

                Wj = seller_welfare(P_star, G_net_j, a_j, b_j, lam_j, theta_j, pi_i)
                Wi = buyer_welfare(pi_i, P_star, G_klim_i, lam_i, theta_i, etha_i)
                welfare_iters.append((Wj, Wi))
                P_star_iters.append(P_star.copy())
                pi_star_iters.append(pi_i.copy())

                if capture:
                    t_sellers_last = t_s
                    P_traj_last    = P_traj
                    t_buyers_last  = t_b
                    pi_traj_last   = pi_traj

            conv_list.append(ConvergenceData(
                hour=k,
                seller_ids=sids,
                buyer_ids=bids,
                G_net_j=G_net_j,
                D_net_i=D_net_i,
                welfare_iters=welfare_iters,
                P_star_iters=P_star_iters,
                pi_star_iters=pi_star_iters,
                t_sellers=t_sellers_last,
                P_traj=P_traj_last,
                t_buyers=t_buyers_last,
                pi_traj=pi_traj_last,
            ))

        return conv_list

    def run_single_hour(self, k: int, D: np.ndarray, G: np.ndarray) -> HourlyResult:
        ag = self.agents; gr = self.grid; sv = self.solver
        G_klim_k = compute_generation_limit(G[:, k], ag.a, ag.b, ag.c, gr.pi_gs)
        _, sids, bids = classify_agents(G_klim_k, D[:, k])
        return _run_hour_worker((k, G_klim_k, D[:, k].copy(), G[:, k].copy(),
                                  sids, bids, ag.a, ag.b, ag.lam, ag.theta, ag.etha,
                                  gr.pi_gs, gr.pi_gb,
                                  sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
                                  sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max))
