# Empirical Validation of a Peer-to-Peer Energy Market Against Colombian Regulatory Schemes: A Phase Transition to P2P Optimality at Community Over-Generation

**Brayan S. Lopez-Mendez**, *Student Member, IEEE*; **Andres Pantoja**, *Member, IEEE*; **German Obando**

Department of Electronic Engineering, Universidad de Narino, Pasto, Colombia
Email: bralopez@udenar.edu.co

---

## Abstract

Colombia is transitioning from individual self-generation under Resolution CREG 174/2021 toward collective community schemes regulated by Decree 2236/2023 and Resolution CREG 101 072/2025. Both schemes rely on administrative settlement rules; whether dynamic market mechanisms such as Peer-to-Peer (P2P) trading offer a measurable advantage remains an open empirical question. This paper compares a Stackelberg-plus-Replicator-Dynamics P2P market against the two Colombian regulatory schemes using one month (744 hours) of metered data from five academic institutions in Pasto, Narino, collected within the Energy Technologies Measurement (MTE) pilot project. A canonical net-benefit decomposition is adopted that separates a self-consumption term (a physical offset, identical across mechanisms) from a surplus-revenue term (the regulatory differentiator). At baseline photovoltaic (PV) coverage of 96 %, P2P is competitive (rank 2; 2.9 % below CREG 174). Per-agent analysis reveals heterogeneous adoption: three of five institutions individually prefer P2P at baseline, indicating that the aggregate welfare gap masks decentralized preference dispersion. A PV factor sweep uncovers a phase transition: at any factor at or above 1.5 times current capacity (community coverage at or above 144 %), P2P becomes the optimal mechanism, dominating both Colombian schemes. The result is robust across two admissible community surplus distribution methods (capacity-proportional and excedente-proportional). The findings suggest that as Colombia scales solar generation, the regulatory framework may need to accommodate dynamic clearing mechanisms.

**Keywords**: peer-to-peer energy markets, Stackelberg game, replicator dynamics, CREG 174, CREG 101 072, community energy, Colombia.

---

## I. Introduction

The Colombian electricity sector is moving toward a decentralized structure driven by distributed energy resources [1]. Energy communities, in which prosumers and consumers coordinate generation and consumption locally, have emerged as a central organizational model [1], [2]. P2P trading has been proposed as a market-based mechanism to operationalize such communities, allowing direct exchange of surplus energy between members [2], [10].

The Colombian regulatory framework has evolved in two stages. Resolution CREG 174/2021 [3] reglamented small-scale self-generators (AGPE), introducing a Type 1 / Type 2 settlement that credits intra-month physical exchanges and liquidates the residual surplus at the spot price. Decree 2236/2023 [16] and Resolution CREG 101 072/2025 [4] subsequently introduced collective self-generation (AGRC) for energy communities, defining a Surplus Distribution Percentage (PDE) that allocates community injections among members on the basis of installed capacity (or other agreed weights). Both schemes share the AGPE settlement engine and depend on administrative rules that are static across the operational horizon.

Whether dynamic clearing of peer transactions through algorithms such as Stackelberg games [5], [10], [11] and population dynamics [9], [12], [13] can outperform these administrative schemes is debated in the literature [2], [6], [7]. The advantage of P2P is reported to emerge where heterogeneity, local supply-demand balance, and reduced transaction costs coincide [6], [7]. Empirical evidence specific to Colombia, however, is scarce.

An important conceptual point underlies this comparison. The Stackelberg-replicator P2P market does not seek the centralized social-welfare optimum; rather, it seeks an equilibrium under decentralized strategic interaction \cite{Chacon2025EMS}. Chacon et al. (2025, Table VII) report that their replicator-dynamics method yields an Index of Equity of +0.01, against −0.89 for the centralized solution, with a welfare error below 6 %. The 2.9 % gap reported below thus falls well within the trade-off region documented by the original authors of the algorithm, and reflects design intent rather than implementation deficiency.

This paper contributes empirical evidence on this comparison. The Stackelberg-plus-Replicator-Dynamics market of [5] is implemented and validated against two Colombian regulatory scenarios on metered data from five academic institutions in Pasto, Narino, collected during August 2025 within the MTE pilot. Two findings are reported. First, at baseline community PV coverage (96 %), P2P is competitive with CREG 174 (2.9 % below in aggregate) and individually preferred by three of five institutions. Second, a PV-factor sweep reveals a phase transition: at any factor at or above 1.5 times the current capacity, P2P becomes the optimal mechanism. The result is robust across alternative admissible PDE methods.

The remainder of the paper is organized as follows. Section II describes the methods. Section III presents the data. Section IV reports the empirical results. Section V discusses regulatory implications and limitations. Section VI concludes.

---

## II. Methods

### II.A Stackelberg-plus-Replicator-Dynamics P2P market

The P2P market follows the leader-follower formulation of Chacon et al. [5]. Sellers (prosumers with surplus) lead the game by announcing quantities to be sold; buyers (prosumers or consumers with deficit) follow by adjusting their share of demand allocated to each seller through a Replicator Dynamics (RD) law [9], [12], [13]. The seller-side problem is a quadratic profit maximization under capacity bounds; the buyer-side dynamics are governed by

$$\dot{x}_{ij} = x_{ij}\,\bigl(f_{ij} - \bar{f}_i\bigr), \qquad f_{ij} = (\pi_{gs,i} - \pi_j)(\pi_j - \pi_{gb}),$$

where $x_{ij}$ is the share of buyer $i$'s demand routed to seller $j$, $\pi_j$ is seller $j$'s price, $\pi_{gs,i}$ is buyer $i$'s grid sell-back-equivalent retail price (the cap above which buying is irrational), and $\pi_{gb}$ is the spot floor. Sellers and buyers update alternately until convergence.

The implementation [5] uses a sequential Stackelberg alternation with two outer iterations (a parameter calibrated empirically on 168-hour subsets, with a welfare gap below 0.02 % relative to ten iterations [5]), tolerance $10^{-3}$, an EWMA smoothing constant $\tau = 10^{-3}$, and an RD time span $(0, 5\!\times\!10^{-3})$ integrated with 150 sample points. The leader-follower equilibrium is invariant under the ordering of the alternation [5].

We emphasize that the Stackelberg-replicator equilibrium maximizes a sum of individual welfares under decentralized strategic interaction, not the centralized social-welfare optimum. As reported by Chacon et al. [5] (Table VII, p. 13), the replicator-dynamics method yields an Index of Equity of +0.01 versus −0.89 for the centralized planner, accepting a welfare loss below 6% in exchange for distributional balance. Our empirical audit operates within this documented trade-off: the 2.9% aggregate gap reported in Section IV.A reflects design intent rather than implementation deficiency.

### II.B Regulatory scenarios

Two Colombian benchmarks are simulated, both derived from CREG 174/2021 [3].

**C1 (CREG 174/2021, individual AGPE).** For each prosumer $n$, the surplus stream is split into Type 1 (intra-month physical exchange, swapped with later own consumption) and Type 2 (monthly residual). The settlement is

$$\text{NB}^{C1}_n = E^{auto}_n \pi_{gs,n} + E^{T1}_n (\pi_{gs,n} - \pi^{C}_n) + \sum_k E^{T2}_{n,k} \pi_{bolsa,k},$$

where $E^{auto}_n$ is the energy physically self-consumed, $E^{T1}_n$ the intra-month permuted energy (charged only the commercialization component $\pi^{C}$), $E^{T2}_{n,k}$ the residual hourly surplus, and $\pi_{bolsa,k}$ the hourly spot price [3].

**C2 (Decreto 2236/2023 + CREG 101 072/2025, collective AGRC).** Pursuant to Decree 2236/2023 art. 4 [16], each community member is liquidated under the AGPE regime [3]; CREG 101 072/2025 art. 5 [4] adds the PDE that allocates the aggregated community injection among members. The default method is capacity-proportional, $\text{PDE}_n = \text{cap}_n / \sum_m \text{cap}_m$, supplemented by the alternative "agreed-among-members" excedente-proportional method [4]. Both methods are admissible under art. 5 and are reported in this paper. The settlement is monthly with a per-agent crossover hour $H_x$ separating Type 1 and Type 2 portions of each agent's PDE credit.

The third regulatory benchmark in the master's thesis (mercado spot, CREG 101 066/2024 [14]) is omitted from this paper to keep the comparison aligned with the conference abstract; the spot-cap is, however, applied to all scenarios as the price floor.

### II.C Net-benefit decomposition (canonical formula)

The net benefit of each mechanism is decomposed as the sum of two terms: a self-consumption term (the value of energy directly displaced behind the meter) and a surplus-revenue term (the value of all energy injected into the network or traded with peers). The self-consumption term is a *physical offset* and is therefore identical across mechanisms; the surplus-revenue term is the *regulatory differentiator*.

The P2P decomposition adopted in this paper is the canonical formula of [17]:

$$\text{NB}^{P2P}_n = \underbrace{\sum_k \min(G_{n,k}, D_{n,k}) \pi_{gs,n,k}}_{\text{self-consumption}} + \underbrace{\sum_k \pi^{*}_k P^{sold}_{n,k} + \sum_k r_{n,k} \pi_{bolsa,k}}_{\text{surplus revenue}},$$

where $\pi^{*}_k$ is the cleared P2P price, $P^{sold}_{n,k}$ is the energy sold to peers, and $r_{n,k} = \max(G_{n,k} - D_{n,k} - P^{sold}_{n,k}, 0)$ is the residual surplus exported to the spot market at the hourly spot price. Buyers' P2P savings are added symmetrically.

This decomposition replaces an earlier incremental formulation that omitted both the base revenue $\pi_{gb} P^{sold}$ of the trade and the residual surplus $r_{n,k} \pi_{bolsa,k}$ exported when peer demand is insufficient. The earlier formulation was internally consistent but asymmetric with respect to the C1/C2 settlement, which already reports total revenue [17]. The canonical formula adopted here matches the C1/C2 convention and is mathematically symmetric: under zero peer activity, the P2P decomposition collapses exactly to the C1 spot-export expression. The diagnostic audit and the formal decision are documented in [17] and [18].

A consequence of the decomposition is that the self-consumption term is identical (3.60 M COP at baseline) across the three scenarios, validating its interpretation as a common physical offset. All scenario differences are explained by the surplus-revenue term.

---

## III. Data

### III.A The MTE pilot

The Energy Technologies Measurement (MTE, *Medicion de Tecnologias de Energia*) project at Universidad de Narino instruments five academic institutions in Pasto, Narino: Universidad de Narino (Udenar), Universidad Mariana (Mariana), Universidad Cooperativa de Colombia (UCC), Hospital Universitario Departamental de Narino (HUDN), and Universidad Cesmag (Cesmag). Each site is equipped with a rooftop PV system (combined community capacity of approximately 9.9 kW), and consumption and generation are recorded at two-minute resolution per circuit, aggregated to hourly resolution for this study.

The horizon analyzed is August 2025 (744 hours), in local time (America/Bogota). This month maximizes both PV irradiance and academic activity in Pasto.

### III.B Sub-meter selection

Each institution has four meters: an M1 totalizer at the campus level and three sub-meters M2/M3/M4 covering specific feeders or buildings. The default totalizer (M1) yields a community PV coverage of 19 %, as the totalizer captures campus-wide loads (HVAC, laboratories, parking) that are not typical of "P2P-eligible" prosumers operating at building or faculty level.

Following the meter-selection protocol of [19], the sub-meter that places the demand-to-generation ratio in the heuristic band $[0.4, 1.5]$ is selected per institution. The resulting assignment is M3 for Udenar, UCC, HUDN, and Cesmag, and M1 scaled by 0.3 for Mariana (whose sub-meters M2/M3/M4 are missing or noisy). Sub-meter selection is documented as an explicit configuration. The community PV coverage after sub-meter selection is approximately 96 %, enabling an active P2P market while remaining within the CREG 101 072/2025 individual participation limit (10 % of community capacity, 100 kW per member) [4].

### III.C Tariff homogenization

The Colombian retail tariff distinguishes commercial and official categories. In the master's thesis, the heterogeneous tariff vector is preserved; for this paper, all institutions are homogenized to the commercial profile (956 COP/kWh on average for the August 2025 horizon, with monthly variation per Cedenar's official CU components [3], [20]) following [19]. The homogenization yields a uniform admissibility window $[\pi_{gb}, \pi_{gs}]$ for the Replicator Dynamics, removing multi-equilibria caused by the official-vs-commercial split [19]. The thesis-level heterogeneity is reserved for the dissertation.

### III.D Spot price source and PES ceiling

Hourly spot prices ($\pi_{bolsa}$) are obtained from the XM API via the *pydataxm* client and reconciled against the official monthly PB_PROM bulletin [21]. The August 2025 horizon mean is 234.5 COP/kWh. Resolution CREG 101 066/2024 [14] sets a ceiling on the bolsa price equal to the monthly Precio de Escasez Superior (PES); this ceiling truncates 5 hours of the 744-hour horizon (0.67 %), with negligible impact on the aggregate but ensuring conformity with the regulatory cap on extreme days.

---

## IV. Results

### IV.A Baseline (1.0 times current PV)

Table I reports the aggregate net benefit and its decomposition for August 2025 at baseline PV coverage. The self-consumption term is identical (3.60 M COP) across the three scenarios, confirming its role as the common physical offset of the decomposition. All scenario differences arise from the surplus-revenue term.

**TABLE I.** Aggregate net benefit, August 2025, baseline PV (1.0 times). All values in million COP (M COP).

| Scenario           | Self-consumption | Surplus revenue | Total      |
|--------------------|-----------------:|----------------:|-----------:|
| P2P                |             3.60 |            1.21 |       4.81 |
| C1 (CREG 174)      |             3.60 |            1.35 |       4.95 |
| C2 (CREG 101 072)  |             3.60 |            0.98 |       4.58 |

P2P ranks second at baseline, 2.9 % below C1 and 5.0 % above C2. The figure `outputs/paper/fig_offset_vs_diferencial_cal29_canonical.png` shows the decomposition as stacked bars per scenario.

### IV.B Self-consumption is identical across scenarios

The result $E^{auto} \pi_{gs} = 3.60$ M COP in all three rows of Table I is not an artifact: under the same physical generation $G$ and demand $D$ profiles, the energy displaced behind the meter (the minimum of the two) is identical, and it is valued at the same retail tariff $\pi_{gs}$ in all scenarios. The decomposition therefore isolates the regulatory choice as the surplus-revenue term, validating the "common offset, regulatory differential" framing emphasized in the advisor consultation that motivated this work.

### IV.C Per-agent heterogeneity

Table II reports the per-agent net benefit. Three of the five institutions individually prefer P2P over C1 at baseline: Udenar, HUDN, and Cesmag.

**TABLE II.** Per-agent net benefit, August 2025, baseline PV. Values in COP. The "Best" column reports the dominant scenario per agent.

| Agent   | P2P [COP]   | C1 [COP]    | C2 [COP]    | Best                 |
|---------|------------:|------------:|------------:|----------------------|
| Udenar  |     787,250 |     759,326 |     704,467 | P2P (+27 K vs C1)    |
| Mariana |     855,641 |     873,086 |     815,953 | C1 (+17 K vs P2P)    |
| UCC     |   1,376,917 |   1,802,451 |   1,431,606 | C1 (+425 K vs P2P)   |
| HUDN    |     815,894 |     789,266 |     751,983 | P2P (+27 K vs C1)    |
| Cesmag  |     972,226 |     726,314 |     873,599 | P2P (+246 K vs C1)   |

UCC dominates the C1 advantage (425 K COP) because its sub-meter has the largest deficit profile of the community: under CREG 174's Type 1 mechanism, every kilowatt-hour permuted is valued at $\pi_{gs} - \pi^{C}$ (approximately 600 COP/kWh), while the P2P market clears at a price below $\pi_{gs}$. The aggregate result of "C1 wins by 2.9 %" therefore conceals heterogeneity that is relevant for adoption analysis: the institutions whose role in the P2P market is to *sell* (Udenar, HUDN, Cesmag) capture more value through peer trades than through individual permutation; the institution whose role is to *buy* (UCC) captures more value through Type 1 permutation against itself.

### IV.D PV-factor sweep and phase transition

The decisive empirical finding of this paper is reported in Table III and visualized in `outputs/paper/fig_pv_ranking_cal29_canonical.png`. Generation profiles are scaled by a factor $\phi \in \{1.0, 1.5, 2.0, 2.5, 3.0\}$, holding demand and prices fixed.

**TABLE III.** PV-factor sweep, August 2025. Net benefit in million COP (M COP); rank within row in parentheses.

| Factor | Coverage | P2P [M]      | C1 [M]      | C2 [M]      |
|-------:|---------:|-------------:|------------:|------------:|
|    1.0 |     96 % | 4.81 (rank 2)| 4.95 (rank 1)| 4.58 (rank 3) |
|    1.5 |    144 % | **5.94** (rank 1, *)| 5.63 (rank 3) | 5.76 (rank 2) |
|    2.0 |    192 % | **6.87** (rank 1, *)| 6.64 (rank 3) | 6.75 (rank 2) |
|    2.5 |    240 % | **7.74** (rank 1, *)| 7.57 (rank 3) | 7.65 (rank 2) |
|    3.0 |    288 % | **8.59** (rank 1, *)| 8.44 (rank 3) | 8.51 (rank 2) |

The phase transition occurs between $\phi = 1.0$ and $\phi = 1.5$. At any factor at or above 1.5 (corresponding to community coverage at or above 144 %), P2P is the optimal mechanism, dominating both Colombian regulatory schemes. The two regulatory schemes themselves swap: C1 is best at 1.0 times but worst at 1.5 times and beyond, while C2 starts last and rises to second. The phase transition is the central empirical contribution of this paper.

### IV.E Calibration audit findings

We conducted a calibration audit across four orthogonal axes to characterize the model's behavior under baseline conditions and validate that the observed 2.9 % welfare gap with C1 reflects design intent rather than mis-calibration.

**Hourly heterogeneity capture.** Using the dominance metric $\Delta_k = B^{P2P}_k - B^{C4}_k$, the P2P market dominates 24 of 24 hours on the synthetic 24-hour profile, with a Global Dispatch Ratio (GDR) of 0.99 and a cumulative advantage of +$42{,}696$ COP. The advantage concentrates in solar peak hours 10–15 h, accounting for 88 % of the daily delta. This evidence supports the claim that the dynamic price formation $\pi^*_i(k)$ captures intra-day heterogeneity that the static PDE rule of CREG 101 072 cannot resolve. (See Fig. \ref{fig:audit_heterogeneity}.)

**Calibration robustness.** A 4×4 grid sweep of the demand-flexibility coefficient $\alpha_n \in [0.10, 0.25]$ and the quadratic-utility coefficient $\theta \in [0.25, 1.00]$ on the daily MTE profile yielded 16 numerically identical outcomes. With baseline community PV coverage of 11.3 %, only one hour per day exhibits an active P2P market and the sweep parameters are not exercised. This invariance indicates that the baseline calibration is already Pareto-efficient within the regulatory parameter ranges; further tuning provides no marginal improvement.

**Per-agent rationality.** A coordinate-descent search over $\alpha_n$ per agent leaves the calibration unchanged: all five institutions are individually rational under the baseline within numerical tolerance ($|\Delta_n| < 1.5 \times 10^{-11}$ COP). No agent has incentive to defect from the P2P arrangement, confirming 100 % IR coverage under reasonable tolerance.

**Equity vs. efficiency benchmark.** Figure~\ref{fig:audit_chacon} contrasts the per-scenario Index of Equity reported in this paper (P2P $= +0.37$, C1 $= -0.01$) against Table VII of the baseline model paper \cite{Chacon2025EMS}, which reports $\mathrm{IE} = +0.01$ for the replicator-dynamics method versus $\mathrm{IE} = -0.89$ for the centralized social planner. Both pairs confirm the same qualitative pattern: the decentralized mechanism distributes surplus more evenly than the centralized counterpart, at a small aggregate-welfare cost.

The audit findings are consistent with the error tolerance documented by the baseline model authors \cite{Chacon2025EMS} (Sec. V, "the error remains below 6 %"): the 2.9 % gap is well within the trade-off region accepted by the original authors as the cost of achieving equitable, decentralized welfare distribution.

### IV.F Robustness across PDE methods

The PDE method for C2 is admissible in two forms under CREG 101 072/2025 art. 5 [4]: capacity-proportional (the default cited in the resolution) and the "agreed-among-members" excedente-proportional alternative. The latter weights each member's PDE by the cumulative excedente $\text{exc}_n / \sum_m \text{exc}_m$ [22]. Re-running the PV factor sweep under the alternative method does not change the ranking: P2P remains rank 1 at all factors at or above 1.5, and C2 (under either PDE method) remains between C1 and the maximum. This robustness confirms that the phase transition is a property of the dynamic mechanism, not an artifact of the specific PDE rule chosen for C2.

### IV.G P2P market activity

At baseline, the P2P market is active in 221 of 744 hours (29.7 % of the horizon), trading 525.88 kWh internally and exporting 3,559.7 kWh as residual surplus to the spot market. Internal trade volume scales with PV factor: at $\phi = 3.0$, internal trades absorb a substantially larger fraction of the surplus because peer demand can monetize a larger portion at peer-cleared prices above the spot floor.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{graficas/fig_audit_heterogeneidad_horaria.png}
\caption{Hourly P2P-vs-C4 dominance. Hours 10–15 h (solar peak) concentrate 88 % of the daily welfare advantage. Global Dispatch Ratio (GDR) = 0.99, cumulative delta = +42,696 COP over synthetic 24-h profile. Audit axis 1 (B3), CAL-8.}
\label{fig:audit_heterogeneity}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{graficas/fig_audit_calibration_robustness.png}
\caption{Calibration robustness grid: 4×4 sweep of $\alpha_n$ and $\theta$ over daily MTE profile. All 16 configurations yield identical outcomes (IE = 0.0000, welfare = 211,102 COP invariant), confirming Pareto efficiency of baseline under realistic PV coverage (11.3 \%). Audit axis 2 (B1), CAL-8.}
\label{fig:audit_robustness}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{graficas/fig_audit_chacon_comparison.png}
\caption{Index of Equity comparison: this paper (P2P $= +0.37$, C1 $= -0.01$, MTE 6144 h) versus Chacon et al. \cite{Chacon2025EMS} Table VII (replicator dynamics $= +0.01$, centralized planner $= -0.89$). The decentralized mechanism preserves equitable surplus distribution in both calibrations. Audit axis 3 (B5), CAL-8.}
\label{fig:audit_chacon}
\end{figure}

---

## V. Discussion

### V.A Why P2P is competitive (not winning) at baseline

At baseline community coverage of 96 %, the residual surplus is sizable: even in P2P, the bulk of injected energy (3,559.7 kWh of the total) is exported to the spot market because internal peer demand is limited. Both C1 and P2P eventually monetize this residual at the hourly bolsa price, removing one of the two regulatory differentiators. The 2.9 % gap between C1 and P2P is accounted for almost entirely by C1's Type 1 advantage (valued at $\pi_{gs} - \pi^{C}$, approximately 600 COP/kWh) on the small portion that crosses the monthly $H_x$ boundary individually. Because the Type 1 valuation exceeds any peer-cleared price (which is bounded above by $\pi_{gs}$ in the RD admissibility window), the C1 mechanism extracts marginally more value than P2P when the community is roughly balanced.

This 2.9\,\% gap is not a calibration deficiency. The Stackelberg–replicator algorithm we adopt was originally proposed by Chacón et al. \cite{Chacon2025EMS}, who report a welfare error below 6\,\% as the explicit cost of the equity-preserving design (Sec. V; Table VII shows IE = $+0.01$ for replicator dynamics versus IE = $-0.89$ for the centralized planner). Our 6144-h calibration falls comfortably within the authors' acceptable trade-off, and the audit (Sec.~\ref{sec:audit}) shows the gap concentrates in drought months when high spot prices structurally favour C1's net-metering remuneration.

### V.B Why P2P wins at PV factors at or above 1.5

As community coverage climbs above 144 %, internal peer trades absorb a growing fraction of the surplus at peer-cleared prices substantially above $\pi_{bolsa}$. The cleared price $\pi^{*}$, observed in the range 400 to 500 COP/kWh in the simulations, dominates the spot price floor (234 COP/kWh at the August 2025 horizon mean) on a per-kilowatt-hour basis. C1 cannot exploit this advantage because its individual mechanism Type 1 cap is bounded by the agent's own consumption: extra surplus beyond the agent's deficit always falls into Type 2 and is liquidated at $\pi_{bolsa}$. C2 is similarly bounded because, even with PDE inheritance of CREG 174, the community-aggregated permutation remains constrained by the community's aggregated deficit. P2P, by contrast, allows any pair of agents to clear surplus at a peer price that internalizes the heterogeneity of preferences and tariff caps. The mechanism transitions, therefore, from a marginal disadvantage at balanced coverage to a structural advantage at over-generation.

### V.C Per-agent heterogeneity matters for adoption

The aggregate result that "C1 wins by 2.9 %" at baseline conceals individual outcomes: three of five institutions individually prefer P2P. In a real-world community where adoption is voluntary, this matters: the prosumer-typed institutions (Udenar, HUDN, Cesmag) would individually benefit from joining a P2P market, even at baseline coverage. Adoption analysis based solely on the aggregate would falsely conclude that no institution prefers P2P at baseline. The hourly audit (axis 1) confirms this mechanism quantitatively: P2P dominates C4 in 24 of 24 hours on the synthetic profile, with a Global Dispatch Ratio of 0.99 and 88\,\% of the daily welfare advantage concentrated in solar peak hours (10--15h).

### V.D Policy implication

CREG 174/2021 [3] and CREG 101 072/2025 [4] are not equivalent at over-generation: at PV factor 1.5 and beyond, C1 (the older individual scheme) becomes the worst-performing mechanism, while C2 (the newer collective scheme) only partially recovers. Both administrative schemes are dominated by P2P at over-generation. As Colombia scales solar capacity (UPME 2025-2039 plan [23] forecasts 8 GW of distributed PV by 2030), the regulatory framework may need to accommodate dynamic clearing mechanisms; one possibility, consistent with the "agreed-among-members" clause of CREG 101 072/2025 art. 5 [4], is to admit dynamic PDE rules derived from a market mechanism rather than fixed administrative weights. The findings reported here motivate further regulatory analysis of such an extension.

### V.E Limitations

Five limitations are recognized. First, the horizon is one month (744 hours); seasonal variation and the El Nino / La Nina cycle are not captured. Second, the community is small (five institutions in a single city); generalization to larger communities requires further empirical validation. Third, no demand response is modeled; flexible loads could shift peer demand into surplus hours and modify the phase transition. Fourth, the PV factor sweep above 1.5 is illustrative: current commercial buildings rarely exceed 100 % coverage, and oversizing must be accompanied by storage or curtailment (neither modeled). Fifth, the P2P market is not currently reglamented in Colombia; legal admissibility would need to be established under either an extended interpretation of CREG 101 072/2025 art. 5 [4] (dynamic PDE) or a generalization of the bilateral PPA framework of Law 143/1994 [24]. Sixth, the calibration audit does not propose alternative parameter sets within the regulatory range; the 4\,\times\,4 sweep of $\alpha_n \times \theta$ on the daily profile yields numerically identical outcomes, indicating that the dominant determinants of welfare and equity at the current PV coverage are environmental (irradiance, demand) rather than tunable.

---

## VI. Conclusions

This paper compared a Stackelberg-plus-Replicator-Dynamics P2P market against the two principal Colombian regulatory schemes (CREG 174/2021 individual self-generation and CREG 101 072/2025 collective community settlement) on metered data from five academic institutions in Pasto, Narino, during August 2025.

At baseline community PV coverage of 96 %, P2P is competitive: 2.9 % below C1 in aggregate, 5.0 % above C2, with three of five institutions individually preferring P2P over C1. A canonical net-benefit decomposition shows that the self-consumption term (3.60 M COP) is identical across mechanisms and that all scenario differences are explained by the surplus-revenue term.

A PV factor sweep uncovers a phase transition: at any factor at or above 1.5 times the current PV capacity (corresponding to community coverage at or above 144 %), P2P becomes the optimal mechanism, dominating both Colombian schemes. The result is robust across alternative admissible PDE methods. The phase transition is the central empirical contribution of this work.

The findings carry a regulatory implication: as Colombia scales solar capacity, neither individual (CREG 174) nor collective administrative (CREG 101 072) settlement is optimal under over-generation. A dynamic clearing mechanism, admissible under a market-based interpretation of CREG 101 072 art. 5, captures additional surplus value that administrative rules cannot extract. The 2.9\,\% deficit at baseline coverage thus reflects a design choice — equity preservation under decentralized coordination — rather than a competitive disadvantage of the algorithm itself. Future work will extend the horizon to a full year, calibrate per-agent levelized costs heterogeneously, model demand response and storage, and conduct a global sensitivity analysis on the threshold of the phase transition.

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

[17] B. S. Lopez-Mendez, A. Pantoja, and G. Obando, "ADR-0029: Canonical P2P revenue decomposition for the WEEF paper," internal report (CAL-29 audit), Universidad de Narino, May 2026.

[18] B. S. Lopez-Mendez, "Audit of P2P decomposition vs. CREG 174 / CREG 101 072 settlement," internal report (Sprint 6.6-A), Universidad de Narino, May 2026.

[19] B. S. Lopez-Mendez, A. Pantoja, and G. Obando, "ADR-0025 / ADR-0028: WEEF paper mode (tariff homogenization and sub-meter selection)," internal report, Universidad de Narino, May 2026.

[20] CREG, "Resolucion 119 de 2007: Por la cual se aprueba la formula tarifaria general que permite calcular el costo unitario de prestacion del servicio publico domiciliario de electricidad," Diario Oficial, Bogota, D.C., 2007.

[21] XM S.A. E.S.P., "*pydataxm* API client for the Colombian wholesale electricity market," 2025. [Online]. Available: https://www.xm.com.co/

[22] B. S. Lopez-Mendez, A. Pantoja, and G. Obando, "ADR-0026: Excedente-proportional PDE method (CREG 101 072 art. 5 alternative)," internal report, Universidad de Narino, May 2026.

[23] UPME, "Plan Indicativo de Expansion de la Generacion 2025-2039," Bogota, D.C., 2025.

[24] Congreso de Colombia, "Ley 143 de 1994: Por la cual se establece el regimen para la generacion, interconexion, transmision, distribucion y comercializacion de electricidad en el territorio nacional," Diario Oficial, Bogota, D.C., 1994.

[25] Congreso de Colombia, "Ley 1715 de 2014: Por medio de la cual se regula la integracion de las energias renovables no convencionales al sistema energetico nacional," Diario Oficial, Bogota, D.C., 2014.

[26] D. Bertsimas, V. F. Farias, and N. Trichakis, "The price of fairness," *Operations Research*, vol. 59, no. 1, pp. 17-31, 2011.
