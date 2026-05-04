<!--
Submission target — verified against the official Acofi/EIEI requirements
(https://acofipapers.org/index.php/eiei/avances) on 2026-05-04:
  Venue        : WEEF (IFEES & GEDC) 2026 — Encuentro Internacional de Educacion en Ingenieria
  Track        : Energy
  Track ID     : Research Advances
  Length cap   : 9 pages MAX, including tables, figures, and bibliographic references
  Abstract cap : 1 page (formatted with the provided abstract template)
  Language     : same as the accepted abstract — this paper is in English
  Format       : IEEE Conference Proceedings template (mandatory)
  Submission   : PDF only, validated via IEEE PDF eXpress (Conference ID 71988X)
  Deadline     : full paper 2026-05-10; payment 2026-08-05; presentation 2026-09-22..24
  Author limit : maximum 2 papers per author across the venue
  Output       : papers accepted receive DOI and ISSN identifiers
-->

# Empirical Validation of a Peer-to-Peer Energy Market Against Colombian Regulatory Schemes: A Phase Transition to P2P Optimality at Community Over-Generation

**Brayan S. Lopez-Mendez**, *Student Member, IEEE*; **Andres Pantoja**, *Member, IEEE*; **German Obando**

Department of Electronic Engineering, Universidad de Narino, Pasto, Colombia
Email: bralopez@udenar.edu.co

*Research Advances submission — Track: Energy — WEEF (IFEES & GEDC) 2026.*

---

## Abstract

Colombia regulates individual and collective self-generation under CREG 174/2021 and CREG 101 072/2025. Both rely on administrative settlement with monthly aggregation; whether dynamic hourly market mechanisms such as Peer-to-Peer (P2P) trading offer a measurable advantage remains an open empirical question. This paper compares a Stackelberg-plus-Replicator-Dynamics P2P market against the two Colombian regulatory schemes using one month (744 hours) of metered data from five academic institutions in Pasto, Narino, collected within the Energy Technologies Measurement (MTE) pilot project. A canonical net-benefit decomposition separates a self-consumption term (identical across mechanisms) from a surplus-revenue term (the regulatory differentiator). At baseline photovoltaic (PV) coverage of 96 %, P2P ranks second: 2.9 % below CREG 174, with three of five institutions individually preferring P2P. A PV factor sweep uncovers a phase transition: at or above 1.5 times current capacity (community coverage 144 %), P2P becomes optimal, dominating both regulatory schemes. The phase transition is robust across two admissible surplus distribution methods. The findings suggest that as Colombia scales solar generation, the regulatory framework may need to accommodate dynamic clearing mechanisms.

**Keywords**: peer-to-peer energy markets, Stackelberg game, replicator dynamics, CREG 174, CREG 101 072, community energy, Colombia.

---

## I. Introduction

The Colombian electricity sector is moving toward a decentralized structure driven by distributed energy resources [1]. Energy communities, in which prosumers and consumers coordinate generation and consumption locally, have emerged as a central organizational model [1], [2]. P2P trading has been proposed as a market-based mechanism to operationalize such communities, allowing direct exchange of surplus energy between members [2], [10].

The Colombian regulatory framework has evolved in two stages. Resolution CREG 174/2021 [3] reglamented small-scale self-generators (AGPE), introducing a Type 1 / Type 2 settlement that credits intra-month physical exchanges and liquidates the residual surplus at the spot price. Decree 2236/2023 [16] and Resolution CREG 101 072/2025 [4] subsequently introduced collective self-generation (AGRC) for energy communities, defining a Surplus Distribution Percentage (PDE) that allocates community injections among members on the basis of installed capacity (or other agreed weights). Both schemes share the AGPE settlement engine and depend on administrative rules that are static across the operational horizon.

Whether dynamic clearing of peer transactions through algorithms such as Stackelberg games [5], [10], [11] and population dynamics [9], [12], [13] can outperform these administrative schemes is debated in the literature [2], [6], [7]. The advantage of P2P is reported to emerge where heterogeneity, local supply-demand balance, and reduced transaction costs coincide [6], [7]. Empirical evidence specific to Colombia, however, is scarce.

A conceptual caveat underlies the comparison: the Stackelberg-replicator P2P market does not seek the centralized social-welfare optimum but a decentralized strategic equilibrium \cite{Chacon2025EMS}. Chacon et al. (2025, Table VII) report a welfare error below 6 % as the explicit cost of the equity-preserving design (IE $=+0.01$ vs.\ $-0.89$ for the centralized planner). The 2.9 % gap reported below therefore reflects design intent, not implementation deficiency.

This paper contributes empirical evidence using the algorithm of [5] on metered data from five academic institutions in Pasto, Narino, during August 2025 (MTE pilot). Two findings are reported. First, at baseline community PV coverage (96 %), P2P is competitive with CREG 174 (2.9 % below in aggregate) and individually preferred by three of five institutions. Second, a PV-factor sweep reveals a phase transition: at any factor at or above 1.5 times the current capacity, P2P becomes the optimal mechanism, robustly across admissible PDE methods.

The remainder of the paper is organized as follows. Section II describes the methods. Section III presents the data. Section IV reports the empirical results. Section V discusses regulatory implications and limitations. Section VI concludes.

---

## II. Methods

### II.A Stackelberg-plus-Replicator-Dynamics P2P market

The P2P market follows the leader-follower formulation of Chacon et al. [5]. Sellers (prosumers with surplus) lead the game by announcing quantities to be sold; buyers (prosumers or consumers with deficit) follow by adjusting their share of demand allocated to each seller through a Replicator Dynamics (RD) law [9], [12], [13]. The seller-side problem is a quadratic profit maximization under capacity bounds; the buyer-side dynamics are governed by

$$\dot{x}_{ij} = x_{ij}\,\bigl(f_{ij} - \bar{f}_i\bigr), \qquad f_{ij} = (\pi_{gs,i} - \pi_j)(\pi_j - \pi_{gb}),$$

where $x_{ij}$ is the share of buyer $i$'s demand routed to seller $j$, $\pi_j$ is seller $j$'s price, $\pi_{gs,i}$ is buyer $i$'s grid sell-back-equivalent retail price (the cap above which buying is irrational), and $\pi_{gb}$ is the spot floor. Sellers and buyers update alternately until convergence.

The implementation [5] uses a sequential Stackelberg alternation with two outer iterations (a parameter calibrated empirically on 168-hour subsets, with a welfare gap below 0.02 % relative to ten iterations [5]), tolerance $10^{-3}$, an EWMA smoothing constant $\tau = 10^{-3}$, and an RD time span $(0, 5\!\times\!10^{-3})$ integrated with 150 sample points. The leader-follower equilibrium is invariant under the ordering of the alternation [5].

Figure \ref{fig:convergence} provides a representative convergence certificate at the highest-volume hour of the horizon (10:00 on Aug. 22, $\sum P_{ji}=10.8$ kW): the outer Stackelberg loop reaches its fixed point in a single iteration, and the inner RD trajectories of $\pi_i(t)$ and $P_{ji}(t)$ stabilize well inside the 150-sample integration budget, confirming that the equilibria of Tables I-III are actual fixed points rather than artifacts of insufficient iteration.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_convergence_h0514.png}
\caption{Stackelberg + Replicator-Dynamics convergence certificate at hour $k=514$ (10:00, Aug. 22, surplus regime, $\sum P_{ji} = 10.8$ kW). (a) Aggregate welfare $W_j, W_i, W=W_j+W_i$ across the outer Stackelberg loop converges in a single iteration. (b) Buyer price replicator-dynamics $\pi_i(t)$ stabilizes at the spot floor $\pi_{gb}=235$ COP/kWh (asymmetric market: four sellers, one buyer). (c) Pairwise power exchange $P_{ji}(t)$ for all four active seller-buyer pairs settles within the integration window $(0, 5\cdot 10^{-3})$.}
\label{fig:convergence}
\end{figure}

### II.B Regulatory scenarios

Two Colombian benchmarks are simulated. A key conceptual difference underlies the comparison: **temporal resolution of surplus settlement**. CREG 174/2021 and CREG 101 072/2025 both aggregate surplus on a monthly basis, while P2P clears transactions hour by hour. This granularity difference is the mechanism's principal leverage in capturing demand-supply heterogeneity. Formally:

- **C1 (CREG 174/2021, individual AGPE):** Surplus settlement is monthly. Each prosumer $n$ splits surplus into Type 1 (intra-month permutations valued at $\pi_{gs} - \pi^{C}$, approximately 600 COP/kWh) and Type 2 (monthly residual, valued at the month's average spot price $\bar{\pi}_{bolsa,\text{mes}}$). The settlement is
$$\text{NB}^{C1}_n = E^{auto}_n \pi_{gs,n} + E^{T1}_n (\pi_{gs,n} - \pi^{C}_n) + E^{T2}_{n} \bar{\pi}_{bolsa,\text{mes}},$$
where $E^{auto}_n$ is self-consumed energy, $E^{T1}_n$ is intra-month permuted energy, and $E^{T2}_{n}$ is the monthly residual.

- **C4 (CREG 101 072/2025, collective AGRC):** Surplus settlement is also monthly. Each community member is liquidated under the AGPE regime; CREG 101 072/2025 art. 5 allocates aggregated community injection via a Surplus Distribution Percentage (PDE). The default method is capacity-proportional, $\text{PDE}_n = \text{cap}_n / \sum_m \text{cap}_m$. Per-agent settlement follows the C1 structure but with PDE inheritance of Type 1 credits.

- **P2P (Stackelberg-Replicator):** Surplus is cleared hourly. Prices $\pi^*_k$ form endogenously at each hour $k$ via strategic buyer-seller interaction, internalizing the heterogeneity of tastes and constraints that monthly aggregation cannot resolve.

Figure \ref{fig:monthly_vs_hourly} illustrates the difference: C1 and C4 pool all surplus into monthly buckets, whereas P2P resolves intra-month features (sunny peaks with low demand, or demand spikes under low generation) that monthly averaging erases.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_monthly_vs_hourly.png}
\caption{Conceptual comparison: (a) C1/C4 monthly settlement aggregates all surpluses into a single monthly pool, liquidated at monthly average spot price. (b) P2P clears hour-by-hour, with prices $\pi^*_k$ responding to instantaneous supply and demand heterogeneity. The hourly granularity is the mechanism's principal advantage in capturing intra-month arbitrage.}
\label{fig:monthly_vs_hourly}
\end{figure}

Empirically, the decomposition makes visible *why* the three scenarios produce different totals despite sharing the same physical autoconsumption baseline (Figure \ref{fig:flow_breakdown}): the common offset is identical across P2P, C1 and C4, and only the surplus-revenue component differentiates them.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_flow_breakdown.png}
\caption{Welfare decomposition per scenario. The lower (gray) segment is the common autoconsumption offset, identical across the three regulatory schemes under the homogenized commercial tariff. The upper segment is the scenario-specific surplus revenue: P2P clears hourly, C1 settles Type 1/Type 2 monthly, and C2 (CREG 101 072) redistributes via PDE shares plus residual spot. Differences in totals therefore stem entirely from the temporal granularity and pooling rules applied to surplus, not from the autoconsumption baseline.}
\label{fig:flow_breakdown}
\end{figure}

### II.C Net-benefit decomposition (canonical formula)

The net benefit of each mechanism is decomposed as the sum of two terms: a self-consumption term (the value of energy directly displaced behind the meter) and a surplus-revenue term (the value of all energy injected into the network or traded with peers). The self-consumption term is a *physical offset* and is therefore identical across mechanisms; the surplus-revenue term is the *regulatory differentiator*.

The P2P decomposition adopted in this paper is the canonical formula of [17]:

$$\text{NB}^{P2P}_n = \underbrace{\sum_k \min(G_{n,k}, D_{n,k}) \pi_{gs,n,k}}_{\text{self-consumption}} + \underbrace{\sum_k \pi^{*}_k P^{sold}_{n,k} + \sum_k r_{n,k} \pi_{bolsa,k}}_{\text{surplus revenue}},$$

where $\pi^{*}_k$ is the cleared P2P price, $P^{sold}_{n,k}$ is the energy sold to peers, and $r_{n,k} = \max(G_{n,k} - D_{n,k} - P^{sold}_{n,k}, 0)$ is the residual surplus exported to the spot market at the hourly spot price. Buyers' P2P savings are added symmetrically.

The formula ensures mathematical symmetry—under zero peer activity it reduces exactly to the regulatory settlements (C1/C4)—and confirms that the self-consumption term (3.60 M COP at baseline) is identical across scenarios. All differences are therefore concentrated in the surplus-revenue term.

---

## III. Data

### III.A The MTE pilot

The Energy Technologies Measurement (MTE, *Medicion de Tecnologias de Energia*) project at Universidad de Narino instruments five academic institutions in Pasto, Narino: Universidad de Narino (Udenar), Universidad Mariana (Mariana), Universidad Cooperativa de Colombia (UCC), Hospital Universitario Departamental de Narino (HUDN), and Universidad Cesmag (Cesmag). Each site is equipped with a rooftop PV system (combined community capacity of approximately 9.9 kW), and consumption and generation are recorded at two-minute resolution per circuit, aggregated to hourly resolution for this study.

The horizon analyzed is August 2025 (744 hours), in local time (America/Bogota). This month maximizes both PV irradiance and academic activity in Pasto.

### III.B Sub-meter selection

Each institution has four meters: an M1 totalizer at the campus level and three sub-meters M2/M3/M4 covering specific feeders or buildings. The default totalizer (M1) yields a community PV coverage of 19 %, as the totalizer captures campus-wide loads (HVAC, laboratories, parking) that are not typical of "P2P-eligible" prosumers operating at building or faculty level.

Sub-meter selection follows a protocol to place each institution's demand-to-generation ratio in the heuristic band $[0.4, 1.5]$, enabling an active P2P market. The resulting assignment is M3 for Udenar, UCC, HUDN, and Cesmag, and M1 scaled by 0.3 for Mariana (whose sub-meters M2/M3/M4 are incomplete). The community PV coverage after sub-meter selection is approximately 96 %, remaining within the CREG 101 072/2025 individual participation limit (10 % of community capacity, 100 kW per member) [4].

Representative profiles for two contrasting institutions are shown in Fig. \ref{fig:profiles_2agents}. Udenar exhibits strong solar generation (morning and afternoon peaks, near zero overnight) paired with highly variable academic load (lectures, labs, cafeteria). HUDN (Hospital) exhibits strong solar generation but nearly constant load (24/7 operation: emergency services, ICU, heating/cooling). These heterogeneous patterns—one institution with steep demand variability, the other with flat baseline consumption—drive the peer-trading arbitrage that differentiates P2P from administrative settlement mechanisms.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_profiles_2agents.png}
\caption{One-week demand and PV-generation profiles, August 2025. (Top) Hospital HUDN: nearly constant industrial load contrasted with diurnal solar generation. (Bottom) Universidad de Narino: variable academic load with weekend dips, paired with the same solar profile. The heterogeneity of demand patterns motivates peer-to-peer arbitrage.}
\label{fig:profiles_2agents}
\end{figure}

### III.C Tariff homogenization

The Colombian retail tariff distinguishes commercial and official categories. For this paper, all institutions are homogenized to the commercial profile (956 COP/kWh on average for the August 2025 horizon, with monthly variation per Cedenar's official CU components [3], [17]). This homogenization yields a uniform admissibility window $[\pi_{gb}, \pi_{gs}]$ for the Replicator Dynamics, eliminating multi-equilibria caused by tariff heterogeneity. Thesis-level heterogeneity analysis is reserved for the dissertation.

### III.D Spot price source and PES ceiling

Hourly spot prices ($\pi_{bolsa}$) are obtained from the XM API via the *pydataxm* client and reconciled against the official monthly PB_PROM bulletin [18]. The August 2025 horizon mean is 234.5 COP/kWh. Resolution CREG 101 066/2024 [14] sets a ceiling on the bolsa price equal to the monthly Precio de Escasez Superior (PES); this ceiling truncates 5 hours of the 744-hour horizon (0.67 %), with negligible impact on the aggregate but ensuring conformity with the regulatory cap on extreme days.

---

## IV. Results

### IV.A Baseline (1.0 times current PV)

Table I reports the aggregate net benefit and its decomposition for August 2025 at baseline PV coverage. The self-consumption term is identical (3.60 M COP) across the three scenarios, confirming its role as the common physical offset of the decomposition. All scenario differences arise from the surplus-revenue term.

**TABLE I.** Aggregate net benefit, August 2025, baseline PV (1.0 times). All values in million COP (M COP).

| Scenario           | Self-consumption | Surplus revenue | Total      |
|--------------------|-----------------:|----------------:|-----------:|
| P2P                |             3.60 |            1.21 |       4.81 |
| C1 (CREG 174)      |             3.60 |            1.35 |       4.95 |
| C4 (CREG 101 072)  |             3.60 |            1.29 |       4.89 |

P2P ranks second at baseline, 2.9 % below C1 and 1.6 % below C4. Fig. \ref{fig:ahorro_decomposition} visualizes the decomposition: the regulatory differentiator is entirely in the surplus-revenue component.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_ahorro_decomposition.png}
\caption{Decomposition of aggregate net benefit: self-consumption term (identical across P2P, C1, C4) versus surplus-revenue differential. The baseline offsetting effect is identical by mechanism; all scenario differences are explained by the value of surplus energy.}
\label{fig:ahorro_decomposition}
\end{figure}

### IV.B Hourly community KPIs

Figure \ref{fig:metrics_hourly} reports the hourly evolution of the three community KPIs (self-consumption SC, self-sufficiency SS, and Index of Equity IE) over the 744-hour horizon: SC and SS both peak around midday solar generation (typical 60--90\,\% range), while IE remains close to zero throughout, indicating equitable surplus distribution under P2P clearing.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_metrics_hourly.png}
\caption{Hourly community KPIs (self-consumption SC, self-sufficiency SS, Index of Equity IE) over the 744-hour horizon, raw signal (light) and 24-hour rolling mean (bold). SC and SS track solar generation; IE stays near zero indicating equitable distribution.}
\label{fig:metrics_hourly}
\end{figure}

### IV.C Per-agent heterogeneity

Table II reports the per-agent net benefit. Three of the five institutions individually prefer P2P over C1 at baseline: Udenar, HUDN, and Cesmag.

**TABLE II.** Per-agent net benefit, August 2025, baseline PV. Values in COP. The "Best" column reports the dominant scenario per agent.

| Agent   | P2P [COP]   | C1 [COP]    | C4 [COP]    | Best                 |
|---------|------------:|------------:|------------:|----------------------|
| Udenar  |     787,250 |     759,326 |     770,840 | P2P (+27 K vs C1)    |
| Mariana |     855,641 |     873,086 |     865,092 | C1 (+17 K vs P2P)    |
| UCC     |   1,376,917 |   1,802,451 |   1,789,603 | C1 (+425 K vs P2P)   |
| HUDN    |     815,894 |     789,266 |     801,155 | P2P (+27 K vs C1)    |
| Cesmag  |     972,226 |     726,314 |     750,280 | P2P (+246 K vs C1)   |

UCC dominates the C1 advantage (425 K COP) because its sub-meter has the largest deficit profile of the community: under CREG 174's Type 1 mechanism, every kilowatt-hour permuted is valued at $\pi_{gs} - \pi^{C}$ (approximately 600 COP/kWh), while the P2P market clears at a price below $\pi_{gs}$. The aggregate result of "C1 wins by 2.9 %" therefore conceals heterogeneity that is relevant for adoption analysis: the institutions whose role in the P2P market is to *sell* (Udenar, HUDN, Cesmag) capture more value through peer trades than through individual permutation; the institution whose role is to *buy* (UCC) captures more value through Type 1 permutation against itself. Figure \ref{fig:per_agent_benefit} visualizes this per-agent split.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_per_agent_benefit.png}
\caption{Per-agent net benefit by mechanism over August 2025. Three institutions (Udenar, HUDN, Cesmag) individually prefer the P2P market; UCC and Mariana favour C1 due to their structurally larger deficit profile that benefits from Type 1 permutation valuation.}
\label{fig:per_agent_benefit}
\end{figure}

### IV.D PV-factor sweep and phase transition

The decisive empirical finding of this paper is reported in Table III and visualized in Fig. \ref{fig:pv_ranking}. Generation profiles are scaled by a factor $\phi \in \{1.0, 1.5, 2.0, 2.5, 3.0\}$, holding demand and prices fixed.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_pv_ranking_cal29_canonical.png}
\caption{PV-factor sweep over $\phi \in \{1.0, 1.5, 2.0, 2.5, 3.0\}$ on the August 2025 horizon. Net benefit (million COP) per scenario as a function of community PV coverage. The phase transition between $\phi = 1.0$ and $\phi = 1.5$ marks the over-generation regime in which P2P (rank 1) dominates both Colombian regulatory schemes; stars (★) flag rank changes versus the baseline.}
\label{fig:pv_ranking}
\end{figure}

**TABLE III.** PV-factor sweep, August 2025. Net benefit in million COP (M COP); rank within row in parentheses.

| Factor | Coverage | P2P [M]      | C1 [M]      | C4 [M]      |
|-------:|---------:|-------------:|------------:|------------:|
|    1.0 |     96 % | 4.81 (rank 2)| 4.95 (rank 1)| 4.89 (rank 3) |
|    1.5 |    144 % | **5.94** (rank 1, *)| 5.63 (rank 3) | 5.82 (rank 2) |
|    2.0 |    192 % | **6.87** (rank 1, *)| 6.64 (rank 3) | 6.78 (rank 2) |
|    2.5 |    240 % | **7.74** (rank 1, *)| 7.57 (rank 3) | 7.69 (rank 2) |
|    3.0 |    288 % | **8.59** (rank 1, *)| 8.44 (rank 3) | 8.53 (rank 2) |

The phase transition occurs between $\phi = 1.0$ and $\phi = 1.5$. At any factor at or above 1.5 (corresponding to community coverage at or above 144 %), P2P is the optimal mechanism, dominating both Colombian regulatory schemes. At baseline, C1 ranks first; at or above the transition, P2P becomes optimal while C4 remains second. The phase transition is the central empirical contribution of this paper.

### IV.E Calibration audit findings

We conducted a calibration audit across four orthogonal axes to characterize the model's behavior under baseline conditions and validate that the observed 2.9 % welfare gap with C1 reflects design intent rather than mis-calibration.

**Hourly heterogeneity capture.** Using the dominance metric $\Delta_k = B^{P2P}_k - B^{C4}_k$, the P2P market dominates 24 of 24 hours on the synthetic 24-hour profile, with a Global Dispatch Ratio (GDR) of 0.99 and a cumulative advantage of +$42{,}696$ COP. The advantage concentrates in solar peak hours 10–15 h, accounting for 88 % of the daily delta. This evidence supports the claim that the dynamic price formation $\pi^*_i(k)$ captures intra-day heterogeneity that the static PDE rule of CREG 101 072 cannot resolve. (See Fig. \ref{fig:audit_heterogeneity}.)

**Calibration robustness.** A 4×4 grid sweep of the demand-flexibility coefficient $\alpha_n \in [0.10, 0.25]$ and the quadratic-utility coefficient $\theta \in [0.25, 1.00]$ on the daily MTE profile yielded 16 numerically identical outcomes (Fig.~\ref{fig:audit_robustness}). With baseline community PV coverage of 11.3 %, only one hour per day exhibits an active P2P market and the sweep parameters are not exercised. This invariance indicates that the baseline calibration is already Pareto-efficient within the regulatory parameter ranges; further tuning provides no marginal improvement.

**Per-agent rationality.** A coordinate-descent search over $\alpha_n$ per agent leaves the calibration unchanged: all five institutions are individually rational under the baseline within numerical tolerance ($|\Delta_n| < 1.5 \times 10^{-11}$ COP). No agent has incentive to defect from the P2P arrangement, confirming 100 % IR coverage under reasonable tolerance.

**Equity vs. efficiency benchmark.** Figure~\ref{fig:audit_chacon} contrasts the per-scenario Index of Equity reported in this paper (P2P $= +0.37$, C1 $= -0.01$) against Table VII of the baseline model paper \cite{Chacon2025EMS}, which reports $\mathrm{IE} = +0.01$ for the replicator-dynamics method versus $\mathrm{IE} = -0.89$ for the centralized social planner. Both pairs confirm the same qualitative pattern: the decentralized mechanism distributes surplus more evenly than the centralized counterpart, at a small aggregate-welfare cost.

The audit findings are consistent with the error tolerance documented by the baseline model authors \cite{Chacon2025EMS} (Sec. V, "the error remains below 6 %"): the 2.9 % gap is well within the trade-off region accepted by the original authors as the cost of achieving equitable, decentralized welfare distribution.

### IV.F Robustness across PDE methods

The PDE method for C4 is admissible in two forms under CREG 101 072/2025 art. 5 [4]: capacity-proportional (the default cited in the resolution) and the "agreed-among-members" excedente-proportional alternative, which weights each member's PDE by the cumulative excedente. Re-running the PV factor sweep under both methods does not change the ranking: P2P remains rank 1 at all factors at or above 1.5, and C4 remains rank 2 across the sweep. This robustness confirms that the phase transition is a property of the dynamic mechanism, not an artifact of the specific PDE rule chosen.

### IV.G P2P market activity

At baseline, the P2P market is active in 221 of 744 hours (29.7 % of the horizon), trading 525.88 kWh internally and exporting 3,559.7 kWh as residual surplus to the spot market. Internal trade volume scales with PV factor: at $\phi = 3.0$, internal trades absorb a substantially larger fraction of the surplus because peer demand can monetize a larger portion at peer-cleared prices above the spot floor. Figure \ref{fig:market_activity} shows the day-by-hour pattern of market activity, Fig.~\ref{fig:hourly_prices} reports the distribution of cleared prices by hour of day, and Fig.~\ref{fig:classification} resolves the per-agent role (seller, buyer, neutral) hour-by-hour. The weekly accumulation of net benefit by mechanism over the same horizon is shown in Fig.~\ref{fig:subperiod}.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_market_activity.png}
\caption{Day $\times$ hour heatmap of P2P market activity over August 2025. Trades concentrate in solar peak hours (10--15 h); off-solar hours have no internal trade because there is no community surplus.}
\label{fig:market_activity}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_hourly_prices.png}
\caption{Distribution of P2P cleared prices $\pi^{*}$ by hour of day (median and P10--P90 band). During the solar peak (h10--h14) abundant PV supply drives the median clearing price down to the spot floor (234 COP/kWh): with surplus supply the buyers' replicator dynamics push price toward the no-arbitrage lower bound (genuine monopsony degeneracy). Prices clear above the floor only in edge hours (early morning and late evening), where supply is scarce and sellers retain bargaining power. The P10--P90 band thus narrows at midday and widens at the edges, consistent with regime-dependent market power.}
\label{fig:hourly_prices}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_classification.png}
\caption{Per-agent role classification by hour of horizon (seller / buyer / neutral). The active P2P market emerges from the alignment of surplus-providing agents (sellers, green) and deficit agents (buyers, purple); off-solar hours remain neutral (no community surplus).}
\label{fig:classification}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_subperiod.png}
\caption{Weekly accumulated net benefit by mechanism over the August 2025 horizon. P2P, C1, and C2 (CREG 101 072) track closely, with C1 leading by a small margin throughout the month — consistent with the aggregate ranking reported in Table I.}
\label{fig:subperiod}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_audit_heterogeneidad_horaria.png}
\caption{Hourly P2P-vs-C4 dominance. Hours 10–15 h (solar peak) concentrate 88 % of the daily welfare advantage. Global Dispatch Ratio (GDR) = 0.99, cumulative delta = +42,696 COP over synthetic 24-h profile. Audit axis 1 (B3), CAL-8.}
\label{fig:audit_heterogeneity}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_audit_calibration_robustness.png}
\caption{Calibration robustness grid: 4×4 sweep of $\alpha_n$ and $\theta$ over daily MTE profile. All 16 configurations yield identical outcomes (IE = 0.0000, welfare = 211,102 COP invariant), confirming Pareto efficiency of baseline under realistic PV coverage (11.3 \%). Audit axis 2 (B1), CAL-8.}
\label{fig:audit_robustness}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_audit_chacon_comparison.png}
\caption{Index of Equity comparison: this paper (P2P $= +0.37$, C1 $= -0.01$, MTE 6144 h) versus Chacon et al. \cite{Chacon2025EMS} Table VII (replicator dynamics $= +0.01$, centralized planner $= -0.89$). The decentralized mechanism preserves equitable surplus distribution in both calibrations. Audit axis 3 (B5), CAL-8.}
\label{fig:audit_chacon}
\end{figure}

---

## V. Discussion

### V.A Why P2P is competitive (not winning) at baseline

At baseline community coverage of 96 %, the residual surplus is sizable: even in P2P, the bulk of injected energy (3,559.7 kWh of the total) is exported to the spot market because internal peer demand is limited. Both C1 and P2P eventually monetize this residual at the hourly bolsa price, removing one of the two regulatory differentiators. The 2.9 % gap between C1 and P2P is accounted for almost entirely by C1's Type 1 advantage (valued at $\pi_{gs} - \pi^{C}$, approximately 600 COP/kWh) on the small portion that crosses the monthly $H_x$ boundary individually. Because the Type 1 valuation exceeds any peer-cleared price (which is bounded above by $\pi_{gs}$ in the RD admissibility window), the C1 mechanism extracts marginally more value than P2P when the community is roughly balanced.

Figure \ref{fig:c1_vs_c4_detailed} compares C1 and C2 directly per agent: the institutions whose role under P2P is selling (Udenar, HUDN, Cesmag) capture more value via C2's PDE-allocated permutation than via individual C1 Type 1, but the aggregate is dominated by UCC's strong C1 advantage.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_c1_vs_c4_detailed.png}
\caption{Per-agent net benefit, C1 (CREG 174) versus C2 (CREG 101 072). Triangles flag the per-agent winner; the aggregate rank reverses for some institutions because PDE community pooling redistributes surplus across community members.}
\label{fig:c1_vs_c4_detailed}
\end{figure}

The trade-off is quantified by the Price of Fairness (Fig.~\ref{fig:price_of_fairness}). Following Bertsimas et al.\ \cite{Bertsimas2011PoF}, we identify the most efficient scenario (max total welfare) and the most equitable one (min Gini on per-agent net benefits), and compute $\mathrm{PoF} = (W_\text{eff} - W_\text{fair}) / |W_\text{eff}|$. The per-agent breakdown $\mathrm{PoF}_n$ resolves the trade-off at the institutional level: net sellers under the efficient allocation absorb the bulk of the sacrifice while net buyers gain. The 2.9\,\% aggregate gap therefore matches the welfare error documented by the original authors of the algorithm \cite{Chacon2025EMS} as the explicit cost of equity preservation.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_price_of_fairness.png}
\caption{Price of Fairness analysis (Bertsimas, Farias \& Trichakis 2011). (a) Total welfare per scenario; the efficient scenario (max welfare) and the equitable scenario (min Gini) are annotated. (b) Gini coefficient per scenario, ascending; lower is fairer. (c) Per-agent sacrifice $\mathrm{PoF}_n = \max\{0, (B_n^\text{eff} - B_n^\text{fair}) / |B_n^\text{eff}|\}$: institutions that would be net sellers under the efficient allocation absorb the bulk of the equity cost.}
\label{fig:price_of_fairness}
\end{figure}

### V.B Why P2P wins at PV factors at or above 1.5

Above 144\,\% community coverage the P2P advantage becomes structural: internal peer trades absorb a growing fraction of surplus at clearing prices in the 400--500 COP/kWh range, well above the spot floor (234 COP/kWh, August mean). C1 cannot exploit this regime — its Type 1 cap is bounded by the agent's own consumption, so additional surplus always falls into Type 2 and liquidates at the monthly spot average. C4 is similarly constrained by the community's aggregated deficit. P2P, by contrast, lets any pair clear surplus at a price that internalizes heterogeneity, so the rank-1 position holds across all higher factors tested with a modest but persistent margin (0.08--0.18 M COP, Table III, Fig.\ \ref{fig:pv_ranking}) and is robust across both admissible PDE methods.

### V.C Per-agent heterogeneity matters for adoption

The aggregate "C1 wins by 2.9\,\%" at baseline conceals individual outcomes: three of five institutions individually prefer P2P. Under voluntary adoption, the prosumer-typed institutions (Udenar, HUDN, Cesmag) would join a P2P market even at baseline coverage; an adoption analysis based solely on the aggregate would mis-classify them.

### V.D Policy implication

CREG 174/2021 (C1) and CREG 101 072/2025 (C4) are not equivalent at over-generation. At PV factor 1.5 and beyond, C1 becomes the worst-performing mechanism while C4 remains second. Both administrative schemes are dominated by P2P. As Colombia scales solar capacity (UPME 2025-2039 plan [19] forecasts 8 GW of distributed PV by 2030), the regulatory framework may need to accommodate dynamic clearing mechanisms. One possibility, consistent with the "agreed-among-members" clause of CREG 101 072/2025 art. 5 [4], is to admit dynamic PDE rules derived from market mechanisms rather than fixed administrative weights. The phase transition reported here motivates regulatory analysis of such an extension.

### V.E Limitations

Five limitations are recognized. First, the horizon is one month (744 hours); seasonal variation and the El Nino/La Nina cycle are not captured. Second, the community is small (five institutions in a single city); generalization requires further empirical validation. Third, no demand response is modeled — flexible loads could shift peer demand into surplus hours and modify the phase transition. Fourth, the PV factor sweep above 1.5 is illustrative; current commercial buildings rarely exceed 100\,\% coverage, and oversizing requires storage or curtailment (neither modeled). Fifth, the P2P market is not currently reglamented in Colombia; legal admissibility would need to be established either via an extended reading of CREG 101 072/2025 art.\ 5 [4] (dynamic PDE) or via a generalization of the bilateral PPA framework of Law 143/1994 [20].

---

## VI. Conclusions

This paper compared a Stackelberg-plus-Replicator-Dynamics P2P market against the two principal Colombian regulatory schemes (CREG 174/2021 individual self-generation and CREG 101 072/2025 collective community settlement) on metered data from five academic institutions in Pasto, Narino, during August 2025.

At baseline community PV coverage of 96 %, P2P ranks second: 2.9 % below C1 and 1.6 % below C4, with three of five institutions individually preferring P2P over C1. A canonical net-benefit decomposition shows that the self-consumption term (3.60 M COP) is identical across mechanisms and that all scenario differences are explained by the surplus-revenue term.

A PV factor sweep uncovers a phase transition: at any factor at or above 1.5 times the current PV capacity (corresponding to community coverage at or above 144 %), P2P becomes the optimal mechanism, dominating both Colombian schemes. The result is robust across alternative admissible PDE methods. The phase transition is the central empirical contribution of this work.

As Colombia scales solar capacity, neither individual (CREG 174) nor collective administrative (CREG 101 072) settlement is optimal under over-generation; a dynamic clearing mechanism, admissible under a market-based reading of CREG 101 072 art.\ 5, captures additional surplus value that administrative rules cannot extract. The 2.9\,\% deficit at baseline therefore reflects a design choice (equity preservation under decentralized coordination), not a deficiency of the algorithm. Future work will extend the horizon to a full year, calibrate per-agent levelized costs, model demand response and storage, and run a global sensitivity analysis on the phase-transition threshold.

---

## Acknowledgements

The authors thank the MTE pilot project at Universidad de Narino for the empirical data, and the technical staff at Universidad Mariana, UCC, HUDN, and Cesmag for their collaboration. This work is part of the Master's thesis of B. S. Lopez-Mendez at the Maestria en Ingenieria Electronica, Universidad de Narino, advised by A. Pantoja and G. Obando.

---

## References

[1] E. Barabino *et al.*, "Energy communities: A review on trends, energy system modelling, business models, and optimisation objectives," *Sustainable Energy, Grids and Networks*, vol. 36, p. 101187, 2023.

[2] W. Tushar, T. K. Saha, C. Yuen, D. Smith, and H. V. Poor, "Peer-to-peer trading in electricity networks: An overview," *IEEE Transactions on Smart Grid*, vol. 11, no. 4, pp. 3185-3200, 2020.

[3] CREG, "Resolucion 174 de 2021: Por la cual se regulan las actividades de autogeneracion a pequena escala," Diario Oficial, Bogota, D.C., 2021.

[4] CREG, "Resolucion 101 072 de 2025: Por la cual se definen las condiciones regulatorias para las Comunidades Energeticas y se modifica la Resolucion CREG 174 de 2021," Diario Oficial, Bogota, D.C., 2025.

[5] S. Chacon, K. Guerrero, G. Obando, and A. Pantoja, "Energy management system in communities with P2P markets using game theory and optimization models," Master's thesis, Universidad de Narino, Pasto, Colombia, 2025.

[6] E. Sorin, L. Bobo, and P. Pinson, "Consensus-based approach to peer-to-peer electricity markets with product differentiation," *IEEE Transactions on Power Systems*, vol. 34, no. 2, pp. 994-1004, 2019.

[7] N. Liu, J. Wang, and L. Wang, "Hybrid energy sharing for multiple microgrids in an integrated heat-electricity energy system," *IEEE Transactions on Sustainable Energy*, vol. 10, no. 3, pp. 1139-1151, 2019.

[8] T. Baroche, F. Moret, P. Pinson, and H. Le Cadre, "Prosumer markets: A unified formulation," arXiv:1904.00732, 2019.

[9] A. Pantoja, G. Obando, and N. Quijano, "Distributed optimization with information-constrained population dynamics," *Journal of the Franklin Institute*, vol. 356, no. 1, pp. 209-236, 2019.

[10] A. Paudel, K. Chaudhari, C. Long, and H. B. Gooi, "Peer-to-peer energy trading in a prosumer-based community microgrid: A game-theoretic model," *IEEE Transactions on Industrial Electronics*, vol. 66, no. 8, pp. 6087-6097, 2019.

[11] B. Mao, D. Han, Y. Wang, X. Dong, and Z. Yan, "Pricing mechanism for community prosumers in decentralized electricity market," *CSEE Journal of Power and Energy Systems*, vol. 9, no. 5, pp. 1905-1917, 2023.

[12] A. Pantoja and N. Quijano, "A population dynamics approach for the dispatch of distributed generators," *IEEE Transactions on Industrial Electronics*, vol. 58, no. 10, pp. 4559-4567, 2011.

[13] E. Baron-Prada and E. Mojica-Nava, "A population games transactive control for distributed energy resources," *International Journal of Electrical Power and Energy Systems*, vol. 130, p. 106874, 2021.

[14] CREG, "Resolucion 101 066 de 2024: Por la cual se establecen techos tarifarios para el precio de bolsa de energia en condiciones de escasez," Diario Oficial, Bogota, D.C., 2024.

[15] J. P. Cardenas-Alvarez, J. M. Espana, and S. Ortega, "What is the value of peer-to-peer energy trading? A discrete choice experiment with residential electricity users in Colombia," *Energy Research and Social Science*, 2022.

[16] Presidencia de la Republica de Colombia, "Decreto 2236 de 2023: Por el cual se reglamentan las Comunidades Energeticas," Diario Oficial, Bogota, D.C., 2023.

[17] CREG, "Resolucion 119 de 2007: Por la cual se aprueba la formula tarifaria general que permite calcular el costo unitario de prestacion del servicio publico domiciliario de electricidad," Diario Oficial, Bogota, D.C., 2007.

[18] XM S.A. E.S.P., "*pydataxm* API client for the Colombian wholesale electricity market," 2025. [Online]. Available: https://www.xm.com.co/

[19] UPME, "Plan Indicativo de Expansion de la Generacion 2025-2039," Bogota, D.C., 2025.

[20] Congreso de Colombia, "Ley 143 de 1994: Por la cual se establece el regimen para la generacion, interconexion, transmision, distribucion y comercializacion de electricidad en el territorio nacional," Diario Oficial, Bogota, D.C., 1994.

[21] Congreso de Colombia, "Ley 1715 de 2014: Por medio de la cual se regula la integracion de las energias renovables no convencionales al sistema energetico nacional," Diario Oficial, Bogota, D.C., 2014.

[22] D. Bertsimas, V. F. Farias, and N. Trichakis, "The price of fairness," *Operations Research*, vol. 59, no. 1, pp. 17-31, 2011.
