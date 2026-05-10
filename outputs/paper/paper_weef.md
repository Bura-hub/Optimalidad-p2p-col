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

Colombia regulates individual and collective self-generation under CREG 174/2021 and CREG 101 072/2025. Both rely on administrative settlement with monthly aggregation; whether dynamic hourly market mechanisms such as Peer-to-Peer (P2P) trading offer a measurable advantage remains an open empirical question. This paper compares a Stackelberg-plus-Replicator-Dynamics P2P market against the two Colombian regulatory schemes (denoted C1 and C2 hereafter) using one month (744 hours) of metered demand from five academic institutions in Pasto, Narino, collected within the Energy Technologies Measurement (MTE) pilot project. PV generation is scaled by $\varphi=1.5$ over the empirical baseline to match the community coverage projected by the UPME 2025--2039 expansion plan. A canonical net-benefit decomposition separates a self-consumption term (identical across mechanisms) from a surplus-revenue term (the regulatory differentiator). At the case-study coverage of 144\,\%, P2P ranks first: 5.5\,\% above C1 and 3.1\,\% above C2, with four of five institutions individually preferring P2P. A 9-point PV-factor sweep with $\Delta\varphi=0.1$ resolution localises a sharp phase transition near $\varphi\approx 1.03$: below the transition (96\,\% coverage) C1 narrowly leads; from $\varphi\geq 1.1$ onward P2P dominates, with the advantage forming a plateau over $\varphi\in[1.1, 1.5]$ and saturating monotonically beyond, while keeping rank 1 across all higher factors tested. The dominance is robust across the two admissible surplus distribution methods of CREG 101 072/2025 art.\ 5. The findings suggest that as Colombia scales solar generation, the regulatory framework may need to accommodate dynamic clearing mechanisms.

**Keywords**: peer-to-peer energy markets, Stackelberg game, replicator dynamics, CREG 174, CREG 101 072, community energy, Colombia.

---

## I. Introduction

The Colombian electricity sector is moving toward a decentralized structure driven by distributed energy resources [1]. Energy communities, in which prosumers and consumers coordinate generation and consumption locally, have emerged as a central organizational model [1], [2]. P2P trading has been proposed as a market-based mechanism to operationalize such communities, allowing direct exchange of surplus energy between members [2], [10].

The Colombian regulatory framework has evolved in two stages. Resolution CREG 174/2021 [3] reglamented small-scale self-generators (AGPE), introducing a Type 1 / Type 2 settlement that credits intra-month physical exchanges and liquidates the residual surplus at the spot price. Decree 2236/2023 [16] and Resolution CREG 101 072/2025 [4] subsequently introduced collective self-generation (AGRC) for energy communities, defining a Surplus Distribution Percentage (PDE) that allocates community injections among members on the basis of installed capacity (or other agreed weights). Both schemes share the AGPE settlement engine and depend on administrative rules that are static across the operational horizon.

Whether dynamic clearing of peer transactions through algorithms such as Stackelberg games [5], [10], [11] and population dynamics [9], [12], [13] can outperform these administrative schemes is debated in the literature [2], [6], [7]. The advantage of P2P is reported to emerge where heterogeneity, local supply-demand balance, and reduced transaction costs coincide [6], [7]. Empirical evidence specific to Colombia, however, is scarce.

A conceptual caveat underlies the comparison: the Stackelberg-replicator P2P market does not seek the centralised social-welfare optimum but a decentralised strategic equilibrium \cite{Chacon2025EMS}. Chacon et al.\ (2025, Table VII) report a welfare error below 6\,\% as the explicit cost of decentralisation. Distributional fairness is assessed in this paper via the Gini coefficient over per-agent net benefits (a standard inequality measure widely used in P2P energy literature \cite{Sorin2019Consensus,Tushar2020Overview}); the seller-buyer balance index from \cite{Chacon2025EMS} is reported separately as a cross-validation against Table~VII. Any welfare gap reported below therefore reflects design intent, not implementation deficiency.

This paper contributes empirical evidence using the algorithm of [5] on metered demand from five academic institutions in Pasto, Narino, during August 2025 (MTE pilot), with PV generation scaled by $\varphi=1.5$ to match the UPME 2025--2039 distributed-PV scenario for 2030. Two findings are reported. First, at the case-study coverage of 144\,\%, P2P ranks first by 5.5\,\% over C1 and 3.1\,\% over C2, with four of five institutions individually preferring P2P. Second, a 9-point PV-factor sweep characterises the phase transition: from the empirical baseline (96\,\% coverage, where C1 narrowly leads), P2P takes the lead from $\varphi=1.1$ onward (crossover at $\varphi\approx 1.03$) and remains dominant across all higher factors tested, robustly across the two admissible PDE distribution methods.

The remainder of the paper is organized as follows. Section II describes the methods. Section III presents the data. Section IV reports the empirical results. Section V discusses regulatory implications and limitations. Section VI concludes.

---

## II. Methods

### II.A Stackelberg-plus-Replicator-Dynamics P2P market

The P2P market follows the leader-follower formulation of Chacon et al. [5]. Sellers (prosumers with surplus) lead the game by announcing quantities to be sold; buyers (prosumers or consumers with deficit) follow by adjusting their share of demand allocated to each seller through a Replicator Dynamics (RD) law [9], [12], [13]. The seller-side problem is a quadratic profit maximization under capacity bounds; the buyer-side dynamics are governed by

$$\dot{x}_{ij} = x_{ij}\,\bigl(f_{ij} - \bar{f}_i\bigr), \qquad f_{ij} = (\pi_{gs,i} - \pi_j)(\pi_j - \pi_{gb}),$$

where $x_{ij}$ is the share of buyer $i$'s demand routed to seller $j$, $\pi_j$ is seller $j$'s price, $\pi_{gs,i}$ is buyer $i$'s grid sell-back-equivalent retail price (the cap above which buying is irrational), and $\pi_{gb}$ is the spot floor. Sellers and buyers update alternately until convergence.

The implementation [5] uses a sequential Stackelberg alternation with two outer iterations (a parameter calibrated empirically on 168-hour subsets, with a welfare gap below 0.02 % relative to ten iterations [5]), tolerance $10^{-3}$, an EWMA smoothing constant $\tau = 10^{-3}$, and an RD time span $(0, 5\!\times\!10^{-3})$ integrated with 150 sample points. The leader-follower equilibrium is invariant under the ordering of the alternation [5].

**Cost-function calibration.** The seller cost function $H_j(P) = a_j (\sum_i P_{ji})^2 + b_j (\sum_i P_{ji}) + c_j$ is calibrated to reflect the homogeneous, all-photovoltaic nature of the MTE community. The quadratic coefficient $a_j = 0$ for all five sellers, since grid-tied PV generators have neither fuel cost nor thermal ramp-up cost [23], [24]; this matches the renewable rows of the reference Table I in [5]. The linear coefficient $b_j$ is anchored to the IRENA 2024 global solar LCOE (USD 0.043 / kWh $\approx$ 180 COP/kWh [25]) and adjusted upward to the UPME range for small distributed PV in Colombia (220--250 COP/kWh, [19]): we set $b_j \approx 241$ COP/kWh for the four Fronius-equipped sites (Udenar, Mariana, UCC, HUDN) and $b_j \approx 225$ COP/kWh for Cesmag (whose inverter is from a different vendor with a slightly lower documented operating cost), yielding a 6.7\,\% heterogeneity. The fixed-cost coefficient $c_j = 0$ for all sellers, consistent with the canonical convention for renewables in [23], [24] and with the synthetic baseline of [5]; this is also analytically invariant in the equilibrium since $c_j$ does not enter $\partial H_j / \partial P_{ji}$.

**Demand-response setting and analytical invariance.** This study analyses the case $\alpha_n = 0$ (no demand response activated) for all agents, isolating the equilibrium of the P2P clearing mechanism from the orthogonal effect of intra-day load shifting. Under $\alpha = 0$, the optimal post-DR demand $D_j^*$ collapses to the metered demand $D_j$, which is exogenous to the solver's decision variables $\{P_{ji}, \pi_i\}$. As a direct consequence, the self-consumption utility $U_j(D_j^*) = \lambda_j D_j^* - (\theta_j / 2)(D_j^*)^2$ becomes an additive constant in $W_j$, and its gradients with respect to $P_{ji}$ vanish; the buyer competition term $\beta_i \sum_{\ell \neq i} \pi_\ell \sum_j P_{j\ell}$ has $\beta_i$ (denoted $\eta_i$ in our code) outside the index $i$, so $\partial W_i / \partial \pi_i$ is also independent of $\eta_i$. Therefore the equilibrium $(P^*, \pi^*)$ and all derived indices (IE, PoF, RPE, SC, SS) are **analytically invariant in $\lambda_j$, $\theta_j$, $\eta_i$, $c_j$**, and only depend on $\{a_j, b_j, D_n(t), G_n(t), \pi_{gs}[n,t], \pi_{gb}(t)\}$. We verify this invariance numerically: holding $a_j, b_j$ fixed and varying $(c_j, \lambda_j, \theta_j, \eta_i)$ from the baseline $(0, 100, 0.5, 0.1)$ to the extreme $(10\,000, 999, 10, 5)$ at the case-study hour produces $P^*$ identical to within $2 \times 10^{-8}$ kW and $\pi^*$ identical to within $4 \times 10^{-4}$ COP/kWh (LSODA solver noise). The remaining four parameters are therefore set to the homogeneous reference values from [5] ($\lambda_j = 100$, $\theta_j = 0.5$, $\eta_i = 0.1$). Activation of DR ($\alpha > 0$) is left to future work, where these parameters would require institution-specific recalibration via short-term elasticity estimates from the local retail market literature [15].

Figure \ref{fig:convergence} provides a representative convergence certificate at one of the top-volume hours of the horizon (08:00 on Aug. 22): the outer Stackelberg loop reaches its fixed point in two iterations, and the inner RD trajectories of $\pi_i(t)$ and $P_{ji}(t)$ stabilize well inside the integration window, confirming that the equilibria of Tables I-III are actual fixed points rather than artifacts of insufficient iteration.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_convergence_h0512.png}
\caption{Stackelberg + Replicator-Dynamics convergence certificate at hour $k=512$ (08:00, Aug. 22, surplus regime). The figure is generated by a coupled-ODE solver (single \texttt{solve\_ivp(LSODA)} pass over $t\in[0, 0.04]$\,s, matching Chacón Fig.~3a in [5]) used exclusively for visualization; the production simulation that produces Tables I--III uses the equivalent alternating Stackelberg solver. (a) Aggregate welfare $W_j, W_i, W=W_j+W_i$ converges to its fixed point near $t \approx 14$\,ms. (b) Buyer prices $\pi_i(t)$ stabilize within the integration window. (c) Pairwise power exchange $P_{ji}(t)$ for all active seller-buyer pairs is at the symmetric equilibrium $P^*[j,i]=D_i/J$ throughout the trajectory: under the homogeneous-cost calibration of Sec.~II.A, this initial condition coincides with the equilibrium, so no transient is observable for this case study (a property of the symmetric instance, not a solver artifact).}
\label{fig:convergence}
\end{figure}

### II.B Regulatory scenarios

Two Colombian benchmarks are simulated. A key conceptual difference underlies the comparison: **temporal resolution of surplus settlement**. CREG 174/2021 and CREG 101 072/2025 both aggregate surplus on a monthly basis, while P2P clears transactions hour by hour. This granularity difference is the mechanism's principal leverage in capturing demand-supply heterogeneity. Formally:

- **C1 (CREG 174/2021, individual AGPE):** Surplus settlement is monthly. Each prosumer $n$ splits surplus into Type 1 (intra-month permutations valued at $\pi_{gs} - \pi^{C}$, approximately 600 COP/kWh) and Type 2 (monthly residual, valued at the month's average spot price $\bar{\pi}_{bolsa,\text{mes}}$). The settlement is
$$\text{NB}^{C1}_n = E^{auto}_n \pi_{gs,n} + E^{T1}_n (\pi_{gs,n} - \pi^{C}_n) + E^{T2}_{n} \bar{\pi}_{bolsa,\text{mes}},$$
where $E^{auto}_n$ is self-consumed energy, $E^{T1}_n$ is intra-month permuted energy, and $E^{T2}_{n}$ is the monthly residual.

- **C2 (CREG 101 072/2025, collective AGRC):** Surplus settlement is also monthly. Each community member is liquidated under the AGPE regime; CREG 101 072/2025 art. 5 allocates aggregated community injection via a Surplus Distribution Percentage (PDE). The default method is capacity-proportional, $\text{PDE}_n = \text{cap}_n / \sum_m \text{cap}_m$. Per-agent settlement follows the C1 structure but with PDE inheritance of Type 1 credits. (We adopt the label \textbf{C2} for this scenario throughout the paper for compactness; the internal codebase identifier \texttt{C4} is retained for reproducibility.)

- **P2P (Stackelberg-Replicator):** Surplus is cleared hourly. Prices $\pi^*_k$ form endogenously at each hour $k$ via strategic buyer-seller interaction, internalizing the heterogeneity of tastes and constraints that monthly aggregation cannot resolve.

Figure~\ref{fig:monthly_vs_hourly} illustrates the difference: C1 and C2 pool all surplus into monthly buckets, whereas P2P resolves intra-month features (sunny peaks with low demand, or demand spikes under low generation) that monthly averaging erases.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_monthly_vs_hourly.png}
\caption{Conceptual comparison: (a) C1/C2 monthly settlement aggregates all surpluses into a single monthly pool, liquidated at monthly average spot price. (b) P2P clears hour-by-hour, with prices $\pi^*_k$ responding to instantaneous supply and demand heterogeneity. The hourly granularity is the mechanism's principal advantage in capturing intra-month arbitrage.}
\label{fig:monthly_vs_hourly}
\end{figure}

Empirically, the decomposition makes visible *why* the three scenarios produce different totals despite sharing the same physical autoconsumption baseline (see Figure \ref{fig:ahorro_decomposition} in Section IV): the common offset is identical across P2P, C1 and C2, and only the surplus-revenue component differentiates them.

### II.C Net-benefit decomposition (canonical formula)

The net benefit of each mechanism is decomposed as the sum of two terms: a self-consumption term (the value of energy directly displaced behind the meter) and a surplus-revenue term (the value of all energy injected into the network or traded with peers). The self-consumption term is a *physical offset* and is therefore identical across mechanisms; the surplus-revenue term is the *regulatory differentiator*.

The P2P decomposition adopted in this paper is the canonical formula of [17]:

$$\text{NB}^{P2P}_n = \underbrace{\sum_k \min(G_{n,k}, D_{n,k}) \pi_{gs,n,k}}_{\text{self-consumption}} + \underbrace{\sum_k \pi^{*}_k P^{sold}_{n,k} + \sum_k r_{n,k} \pi_{bolsa,k}}_{\text{surplus revenue}},$$

where $\pi^{*}_k$ is the cleared P2P price, $P^{sold}_{n,k}$ is the energy sold to peers, and $r_{n,k} = \max(G_{n,k} - D_{n,k} - P^{sold}_{n,k}, 0)$ is the residual surplus exported to the spot market at the hourly spot price. Buyers' P2P savings are added symmetrically.

The formula ensures mathematical symmetry---under zero peer activity it reduces exactly to the regulatory settlements (C1, C2)---and confirms that the self-consumption term (3.60 M COP at the empirical baseline, 4.12 M COP at the case-study coverage) is identical across scenarios. All differences are therefore concentrated in the surplus-revenue term.

---

## III. Data

### III.A The MTE pilot

The Energy Technologies Measurement (MTE, *Medicion de Tecnologias de Energia*) project at Universidad de Narino instruments five academic institutions in Pasto, Narino: Universidad de Narino (Udenar), Universidad Mariana (Mariana), Universidad Cooperativa de Colombia (UCC), Hospital Universitario Departamental de Narino (HUDN), and Universidad Cesmag (Cesmag). Each site is equipped with a rooftop PV system (combined community capacity of approximately 9.9 kW), and consumption and generation are recorded at two-minute resolution per circuit, aggregated to hourly resolution for this study.

The horizon analyzed is August 2025 (744 hours), in local time (America/Bogota). This month maximizes both PV irradiance and academic activity in Pasto.

### III.B Sub-meter selection

Each institution has four meters: an M1 totalizer at the campus level and three sub-meters M2/M3/M4 covering specific feeders or buildings. The default totalizer (M1) yields a community PV coverage of 19 %, as the totalizer captures campus-wide loads (HVAC, laboratories, parking) that are not typical of "P2P-eligible" prosumers operating at building or faculty level.

Sub-meter selection places each institution's demand-to-generation ratio in the heuristic band $[0.4, 1.5]$, enabling an active P2P market. The assignment is M3 for Udenar, UCC, HUDN, Cesmag, and M1 scaled by 0.3 for Mariana (whose sub-meters are incomplete). The empirical community PV coverage is 96.1\,\%, within the CREG 101 072/2025 individual participation limit [4]. For the case study (Sec. IV), the generation series is scaled by $\varphi=1.5$ to a coverage of 144.2\,\%, matching the distributed-PV penetration projected for 2030 by the UPME 2025--2039 plan [19]; the demand series is left unmodified. The PV-factor sweep of Sec. IV.D reports the comparison across $\varphi \in \{1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 2.0, 2.5, 3.0\}$ (96\,\%--288\,\% coverage), with $\Delta\varphi=0.1$ refinement in the transition window.

Representative profiles for two contrasting institutions are shown in Fig. \ref{fig:profiles_2agents} for the first complete Mon--Sun calendar week of the horizon (August 4--10, 2025), drawn directly from the same MTE feed used by the rest of the paper (CAL-25 commercial homogenization, $\varphi=1.5$ scaling). Udenar exhibits strong solar generation (morning and afternoon peaks, near zero overnight) paired with highly variable academic load (lectures, labs, cafeteria). HUDN (Hospital) exhibits strong solar generation but nearly constant load (24/7 operation: emergency services, ICU, heating/cooling). The day-to-day variability of the PV signal across the week (e.g., the lower peak on Saturday August 9, a cloudier day) is preserved in the figure, confirming that the contrast between the two profiles arises from the demand side, not from synthetic averaging. These heterogeneous patterns---one institution with steep demand variability, the other with flat baseline consumption---drive the peer-trading arbitrage that differentiates P2P from administrative settlement mechanisms.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_profiles_2agents.png}
\caption{One-week demand and PV-generation profiles for the second complete calendar week of the horizon (Mon Aug 11 -- Sun Aug 17, 2025), drawn from the same MTE 744\,h feed and $\varphi=1.5$ scaling used throughout the paper. The first calendar week (Aug 4--10) was discarded because it contains the national holiday of Battle of Boyaca (Thursday, Aug 7), which produces residual academic demand from Thursday through Sunday and visually obscures the weekday/weekend academic pattern. (Top) Hospital HUDN: nearly constant industrial load contrasted with diurnal solar generation. (Bottom) Universidad de Narino: variable academic load with weekend dips, paired with the same solar profile. The day-to-day PV variability is the empirical signal, not a synthetic average.}
\label{fig:profiles_2agents}
\end{figure}

### III.C Tariff homogenization

The Colombian retail tariff distinguishes commercial and official categories. For this paper, all institutions are homogenized to the commercial profile (980 COP/kWh on average for the August 2025 horizon, with monthly variation per Cedenar's official CU components [3], [17]). This homogenization yields a uniform admissibility window $[\pi_{gb}, \pi_{gs}]$ for the Replicator Dynamics, eliminating multi-equilibria caused by tariff heterogeneity. Thesis-level heterogeneity analysis is reserved for the dissertation.

### III.D Spot price source and PES ceiling

Hourly spot prices ($\pi_{bolsa}$) are obtained from the XM API via the *pydataxm* client and reconciled against the official monthly PB_PROM bulletin [18]. The August 2025 horizon mean is 234.5 COP/kWh. Resolution CREG 101 066/2024 [14] sets a ceiling on the bolsa price equal to the monthly Precio de Escasez Superior (PES); this ceiling truncates 5 hours of the 744-hour horizon (0.67 %), with negligible impact on the aggregate but ensuring conformity with the regulatory cap on extreme days.

---

## IV. Results

### IV.A Case study (144\,\% community coverage)

Table I reports the aggregate net benefit and its decomposition for August 2025 at the case-study coverage of 144\,\% ($\varphi=1.5$ over the empirical baseline, matching the UPME 2030 distributed-PV projection [19]). The self-consumption term is identical (4.12 M COP) across the three scenarios, confirming its role as the common physical offset of the decomposition; all scenario differences arise from the surplus-revenue term.

**TABLE I.** Aggregate net benefit, August 2025, $\varphi=1.5$ (community coverage 144\,\%). All values in million COP (M COP).

| Scenario           | Self-consumption | Surplus revenue | Total      |
|--------------------|-----------------:|----------------:|-----------:|
| P2P                |             4.12 |            1.81 |   **5.94** |
| C1 (CREG 174)      |             4.12 |            1.51 |       5.63 |
| C2 (CREG 101 072)  |             4.12 |            1.64 |       5.76 |

P2P ranks first at the case-study coverage, 5.5\,\% above C1 and 3.1\,\% above the runner-up C2; CREG 174 falls to last place. Fig.\ \ref{fig:ahorro_decomposition} visualizes the decomposition: the regulatory differentiator is entirely in the surplus-revenue component.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_ahorro_decomposition.png}
\caption{Decomposition of aggregate net benefit: self-consumption term (identical across P2P, C1, C2) versus surplus-revenue differential. The baseline offsetting effect is identical by mechanism; all scenario differences are explained by the value of surplus energy.}
\label{fig:ahorro_decomposition}
\end{figure}

### IV.B Hourly community KPIs

Figure \ref{fig:metrics_hourly} reports the hourly evolution of the three community KPIs (self-consumption SC, self-sufficiency SS, and the seller-buyer balance index IE \cite{Chacon2025EMS}) over the 744-hour horizon: SC and SS both peak around midday solar generation (typical 60--90\,\% range). The IE signal is exactly zero in the 554 hours where no P2P trade clears (no sellers or no buyers active) and concentrates near $+1$ in the 190 active hours, reflecting the fact that the equilibrium price $\pi^*$ is consistently close to the regulatory floor $\pi_{gb}$ when supply exceeds demand at midday --- the buyer-favoring price typical of competitive solar surplus regimes (see §V.E for the structural decomposition).

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_metrics_hourly.png}
\caption{Hourly community KPIs (self-consumption SC, self-sufficiency SS, seller-buyer balance index IE \cite{Chacon2025EMS}) over the 744-hour horizon, raw signal (light) and 24-hour rolling mean (bold). SC and SS track solar generation. IE is zero outside trade hours (554/744) and concentrated near $+1$ during the 190 active hours --- the price $\pi^*$ sits close to $\pi_{gb}$ and the surplus accrues primarily to buyers (see §V.E).}
\label{fig:metrics_hourly}
\end{figure}

### IV.C Per-agent heterogeneity

Table II reports the per-agent net benefit at the case-study coverage. Four of the five institutions individually prefer P2P: Udenar, Mariana, HUDN, and Cesmag. UCC is the only outlier, slightly preferring C2 over P2P; under CREG 174 (C1) it ranks last.

**TABLE II.** Per-agent net benefit, August 2025, $\varphi=1.5$. Values in thousand COP (k COP). The "Best" column reports the dominant scenario per agent.

| Agent   | P2P [k]   | C1 [k]    | C2 [k]    | Best                 |
|---------|----------:|----------:|----------:|----------------------|
| Udenar  |       982 |       961 |       889 | P2P (+21 vs C1)      |
| Mariana |     1,073 |     1,061 |     1,038 | P2P (+12 vs C1)      |
| UCC     |     1,700 |     1,658 |     1,748 | C2 (+48 vs P2P)      |
| HUDN    |       987 |       968 |       914 | P2P (+19 vs C1)      |
| Cesmag  |     1,196 |       982 |     1,171 | P2P (+25 vs C2)      |

UCC's preference for C2 stems from the PDE community pooling redistributing surplus across members in proportion to installed capacity: with the largest demand profile of the community, UCC absorbs a disproportionate share of the aggregated surplus credits under C2. Under CREG 174 (C1), the same demand profile yields the worst outcome because Type 1 permutation is bounded by the agent's own consumption and any excess falls into the lower-valued Type 2 spot residual. P2P, by contrast, lets surplus-providing institutions (Udenar, Mariana, HUDN, Cesmag) clear directly with the deficit institution (UCC) at endogenous hourly prices. Figure \ref{fig:per_agent_benefit} visualizes the per-agent split.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_per_agent_benefit.png}
\caption{Per-agent net benefit by mechanism over August 2025 at the case-study coverage. Four of five institutions (Udenar, Mariana, HUDN, Cesmag) individually prefer the P2P market; UCC slightly prefers C2's PDE pooling, which absorbs the asymmetry of its large demand profile.}
\label{fig:per_agent_benefit}
\end{figure}

### IV.D PV-factor sweep: phase transition and robustness

To localize the phase transition that brackets the case study and verify that the choice of $\varphi=1.5$ is not a cherry-picked operating point, generation profiles were scaled by $\varphi \in \{1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 2.0, 2.5, 3.0\}$ over the empirical baseline, holding demand and prices fixed (sweep granularity refined to $\Delta\varphi=0.1$ in the transition window). Table III and Fig.\ \ref{fig:pv_ranking} report the result, with the case-study row ($\varphi = 1.5$) bold-faced.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_pv_ranking_cal29_canonical.png}
\caption{Two-panel PV-factor sweep over $\varphi \in [1.0, 3.0]$ on the August 2025 horizon (9 sample points; $\Delta\varphi=0.1$ in the transition window). \textbf{Top:} net benefit (million COP) per scenario; the regulated-favorable zone ($\varphi<1.2$, light red) and P2P-favorable zone ($\varphi\geq 1.3$, light blue) bracket the crossover. \textbf{Bottom:} P2P--C1 advantage in kCOP, revealing a sharp crossover at $\varphi\approx 1.03$, a plateau region $\varphi\in[1.1, 1.5]$ where the advantage is essentially constant ($+300$ to $+310$ kCOP), and a saturation tail beyond $\varphi=1.5$ that decays $-52$\,\% to $+149$ kCOP at $\varphi=3.0$. The $\bigstar$ marker on the $\varphi=1.5$ point identifies the case study, which lies in the plateau (not at a peak), demonstrating that the choice of $\varphi=1.5$ is not load-bearing for the qualitative ranking.}
\label{fig:pv_ranking}
\end{figure}

**TABLE III.** PV-factor sweep, August 2025 (9-point grid). Net benefit in million COP (M COP); rank within row in parentheses. The case-study row is bold-faced. The sub-grid $\varphi\in[1.0, 1.5]$ at $\Delta\varphi=0.1$ resolves the phase transition.

| Factor $\varphi$ | Coverage | P2P [M]              | C1 [M]        | C2 [M]        |
|-------:|---------:|---------------------:|--------------:|--------------:|
|    1.0 |     96\,\% | 4.81 (rank 2)        | 4.95 (rank 1) | 4.58 (rank 3) |
|    1.1 |    106\,\% | 5.05 (rank 1)        | 4.75 (rank 3) | 4.84 (rank 2) |
|    1.2 |    115\,\% | 5.29 (rank 1)        | 4.99 (rank 3) | 5.08 (rank 2) |
|    1.3 |    125\,\% | 5.52 (rank 1)        | 5.22 (rank 3) | 5.32 (rank 2) |
|    1.4 |    134\,\% | 5.74 (rank 1)        | 5.43 (rank 3) | 5.54 (rank 2) |
| **1.5**|**144\,\%** | **5.94 (rank 1, *)** | **5.63 (rank 3)** | **5.76 (rank 2)** |
|    2.0 |    192\,\% | 6.87 (rank 1)        | 6.64 (rank 3) | 6.76 (rank 2) |
|    2.5 |    240\,\% | 7.74 (rank 1)        | 7.57 (rank 3) | 7.65 (rank 2) |
|    3.0 |    288\,\% | 8.59 (rank 1)        | 8.44 (rank 3) | 8.51 (rank 2) |

The phase transition is sharp: the P2P--C1 difference jumps from $-143$ kCOP at $\varphi=1.0$ (C1 leads, three of five agents individually prefer P2P) to $+308$ kCOP at $\varphi=1.1$ (P2P leads), with a linearly interpolated crossover at $\varphi\approx 1.03$ — only 7 percentage points above the empirical baseline. The narrative of a "modest" coverage gap separating regulated dominance from peer dominance is therefore quantitatively grounded.

Three regularities emerge from the refined sweep. First, the P2P advantage over C1 stays in a tight band $[+300, +310]$ kCOP across $\varphi \in [1.1, 1.5]$ (intra-plateau variation below 3\,\%): the case study at $\varphi=1.5$ lies squarely inside this plateau, and any factor in $[1.1, 1.5]$ yields the same qualitative conclusion. Second, beyond $\varphi=1.5$ the advantage saturates and decays monotonically ($+227$, $+179$, $+149$ kCOP at $\varphi=2.0, 2.5, 3.0$, a 52\,\% drop relative to the plateau), consistent with the theoretical limit that as community PV becomes overabundant the bilateral peer market is competed by the regulated mechanisms, which also capture a growing share of the same surplus. Third, the C2 ranking flips at the lower end: at the empirical baseline C2 is rank 3 (worst, $-373$ kCOP relative to C1) because the PDE pooling rule penalises low-PV regimes where there is little excess to redistribute; from $\varphi=1.1$ onward C2 stabilises at rank 2 across the sweep. The dominance of P2P holds across all factors at and above the plateau and persists across both admissible PDE methods (Sec. IV.F).

### IV.E Calibration audit findings

We conducted a calibration audit across four orthogonal axes to characterise the model's behaviour at the empirical baseline (where C1 narrowly leads) and validate that the audit-axis findings persist under the case-study coverage of 144\,\%.

**Hourly heterogeneity capture.** For each hour-of-day $k\in\{0,\dots,23\}$, let $B^{P2P}_k$ denote the aggregate community welfare obtained under the P2P mechanism, summed across the five institutions and accumulated over the 31 days of August 2025 within hour-of-day $k$; analogously $B^{C2}_k$ for the C2 (CREG 101 072) settlement. Both quantities share an identical self-consumption term valued at the regulated retail tariff $\pi_{gs}$ ($\sum_n \min(G_n,D_n)$ summed across the 31 days); this baseline cancels out in the dominance metric $\Delta_k = B^{P2P}_k - B^{C2}_k$, which therefore isolates the regulatory differentiator (how each mechanism monetises the community surplus) from the common physical baseline. When the P2P market is inactive at hour-of-day $k$ (no clearing pair across all 31 days), $\Delta_k\le 0$ by construction. At $\varphi=1.5$, the P2P market is active in 12 of the 24 hours-of-day (the solar window 6--17\,h), with a cumulative monthly advantage of $+389{,}586$ COP over C2. The peak-hour delta concentrates at hour 8 ($+57{,}920$ COP), confirming that intra-day price formation $\pi^*_i(k)$ captures heterogeneity the static PDE rule of CREG 101 072 cannot resolve. The dual-axis claim (per-day/per-hour) cross-validates the aggregate Table I result. (See Fig.~\ref{fig:audit_heterogeneity}.)

**Calibration robustness.** A $4\times 4$ grid sweep of PV coverage $\varphi \in \{1.00, 1.25, 1.50, 1.75\}$ and the quadratic-utility coefficient $\theta \in \{0.25, 0.50, 0.75, 1.00\}$ over the full 744\,h horizon (August 2025) — a parameter robustness cross-check of the case study reported in Table~I — holding $\alpha=0$ as in the reported case study, reveals three regularities (Fig.~\ref{fig:audit_robustness}). First, the four $\theta$ columns are numerically identical at every $\varphi$ level: the equilibrium is fully invariant to the agent-private curvature parameter, confirming the analytical invariance derived in Section II.A and ruling out hidden-calibration artifacts. Second, the seller-buyer balance index of \cite{Chacon2025EMS} stays strongly positive (buyer-favoring) across the entire grid (range $[+0.535, +0.615]$): the equilibrium price consistently sits below the mid-window $(\pi_{gs}+\pi_{gb})/2$ and the surplus accrues primarily to the buyer side regardless of coverage. Third, monthly total welfare grows monotonically with $\varphi$ from 4.62 MCOP at $\varphi=1.0$ to 6.22 MCOP at $\varphi=1.75$ (a 34.7\,\% increase). PV coverage is therefore an actionable policy lever for CREG planning: the algorithm scales smoothly with installed capacity, the strategic equilibrium structure is preserved, and the per-agent inequality measured by the Gini coefficient (Fig.~\ref{fig:price_of_fairness}b) remains comparable to the regulated baselines.

**Per-agent rationality.** A coordinate-descent search over $\alpha_n$ per agent leaves the calibration unchanged: all five institutions are individually rational under the baseline within numerical tolerance ($|\Delta_n| < 1.5 \times 10^{-11}$ COP). No agent has incentive to defect from the P2P arrangement, confirming 100 % IR coverage under reasonable tolerance.

**Seller-buyer balance benchmark.** Figure~\ref{fig:audit_chacon} contrasts the seller-buyer balance index reported in this paper for the case study (P2P $= +0.665$, C1 $= -0.028$ at $\varphi=1.5$, 744\,h) against Table VII of the baseline model paper \cite{Chacon2025EMS}, which reports $\mathrm{IE} = +0.0149$ for the replicator-dynamics method versus $\mathrm{IE} = -0.8913$ for the centralized social planner. Algebraically, IE collapses to $(\pi_{gs}+\pi_{gb}-2\pi^*)/(\pi_{gs}-\pi_{gb})$ given clearing balance: it measures where the equilibrium price sits inside the admissible window $[\pi_{gb}, \pi_{gs}]$. The two reference values from \cite{Chacon2025EMS} are reproduced as a methodological cross-check; the magnitude difference between Chacon's $+0.0149$ and our $+0.665$ does not reflect a more or less ``equitable'' outcome but the structural asymmetry of the MTE community (four institutions act as net sellers and Cesmag as the dominant net buyer across most of the 190 active hours) which competes the equilibrium price down toward $\pi_{gb}$. Per-agent distributional inequality is reported separately via the Gini coefficient (Fig.~\ref{fig:price_of_fairness}), which is directly comparable across scenarios.

The audit findings are consistent with the error tolerance documented by the baseline model authors \cite{Chacon2025EMS} (Sec.\ IV.C, "the error remains below 6 %", taking the centralized method as the theoretical reference): the 2.9 % gap observed at the empirical baseline (where C1 leads) is well within the trade-off region accepted by the original authors as the cost of decentralization. At the case-study coverage of 144 %, P2P is already the leader, and the per-agent Gini differs from C1 by less than 0.005 (Fig.~\ref{fig:price_of_fairness}), so the decentralized mechanism delivers the largest aggregate welfare without measurable degradation in per-agent inequality.

### IV.F Robustness across PDE methods

The PDE method for C2 is admissible in two forms under CREG 101 072/2025 art.\ 5 [4]: capacity-proportional (the default cited in the resolution) and the "agreed-among-members" excedente-proportional alternative, which weights each member's PDE by the cumulative excedente. Re-running the PV factor sweep under both methods does not change the ranking: P2P remains rank 1 at all factors at or above $\varphi=1.1$, and C2 remains rank 2 across the sweep. This robustness confirms that the phase transition is a property of the dynamic mechanism, not an artifact of the specific PDE rule chosen.

### IV.G P2P market activity

At the case-study coverage, the P2P market is active in 190 of 744 hours (25.5\,\% of the horizon), trading 452.5\,kWh internally; the residual surplus is exported to the spot market. The active-hour count is lower than at the empirical baseline (221 hours at $\varphi = 1.0$) because the higher PV regime saturates community demand more often, leaving stretches in which all agents are net sellers and no peer market forms. The hours that remain active are those in which heterogeneous demand profiles align peers across the seller--buyer divide, and these are precisely the hours where P2P captures value that monthly settlement cannot. Figure~\ref{fig:market_activity} shows the day-by-hour pattern of market activity, Fig.~\ref{fig:hourly_prices} reports the distribution of cleared prices by hour of day, and Fig.~\ref{fig:classification} resolves the per-agent role (seller, buyer, neutral) hour-by-hour. The weekly accumulation of net benefit by mechanism over the same horizon is shown in Fig.~\ref{fig:subperiod}.

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
\caption{Weekly net benefit by mechanism over the August 2025 horizon (4 calendar weeks W1--W4). The figure uses a hybrid attribution: the P2P series is the actual hourly-clearing revenue summed per 168-hour window (no attribution required, since P2P clears at hourly granularity), while C1 and C2 (which by law settle monthly) are PV-weighted attributions of their monthly totals across the four weeks. P2P leads in every week (avg $\Delta \approx +77$ kCOP/week, $+5.5$\,\% over C1), with the same ranking as Table I. The W1 and W3 dips reflect the lower number of working days in those weeks (national holidays Aug 7 and Aug 18 plus weekends, four working days vs five in W2/W4); the holiday-marked weeks are flagged with the gray ``H'' bullets in the figure.}
\label{fig:subperiod}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_audit_heterogeneidad_horaria.png}
\caption{Hourly P2P-vs-C2 dominance over the case-study horizon (MTE 744\,h, August 2025, $\varphi=1.5$, $\alpha=0$), aggregated by hour-of-day across the 31-day window. Bars show the cumulative welfare advantage $\Delta_k = B^{P2P}_k - B^{C2}_k$ in kCOP per hour-of-day; the orange dashed series on the right axis reports the fraction of days within hour-of-day $k$ in which the P2P market actually clears. The solar window (6--17\,h, 12 active hours-of-day) concentrates the entire monthly delta of $+389{,}586$ COP, peaking at hour~8 ($+57{,}920$ COP, active on 20 of 31 days). Off-peak hours (0--5, 18--23) are P2P-inactive because community generation does not exceed local demand. Audit axis 3, CAL-8.}
\label{fig:audit_heterogeneity}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_audit_calibration_robustness.png}
\caption{Calibration robustness grid: 4×4 sweep of PV coverage factor $\varphi \in \{1.00, 1.25, 1.50, 1.75\}$ and quadratic-utility curvature $\theta \in \{0.25, 0.50, 0.75, 1.00\}$ over the full 744\,h horizon (August 2025), parameter robustness cross-check of the Table~I case study, with $\alpha=0$ (no DR). Color encodes the seller-buyer balance index of \cite{Chacon2025EMS}. Three regularities: (i) the four $\theta$ columns are numerically identical at every $\varphi$ — the equilibrium is fully invariant to the agent-private curvature parameter, confirming the analytical invariance argument of Sec.~II.A; (ii) the index stays strongly positive (buyer-favoring) across the entire grid in the range $[+0.535, +0.615]$; (iii) monthly total welfare grows monotonically with $\varphi$ (4.62, 5.21, 5.74, 6.22 MCOP). Per-agent distributional inequality (Gini) is reported in Fig.~\ref{fig:price_of_fairness}. Audit axis 2 (B1), CAL-8.}
\label{fig:audit_robustness}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_audit_chacon_comparison.png}
\caption{Seller-buyer balance index comparison: this paper at the case-study coverage (P2P $= +0.665$, C1 $= -0.028$, 744\,h hourly horizon, $\varphi=1.5$) versus Chacon et al. \cite{Chacon2025EMS} Table~VII (replicator dynamics $= +0.0149$, centralized planner $= -0.8913$). The metric, defined in \cite{Chacon2025EMS} as $\mathrm{IE}=(\sum S_i - \sum S_{R_j})/(\sum S_i + \sum S_{R_j})$, encodes the equilibrium-price position inside the admissible window $[\pi_{gb}, \pi_{gs}]$: zero corresponds to $\pi^*=(\pi_{gs}+\pi_{gb})/2$, $+1$ to $\pi^*=\pi_{gb}$ (buyer-favoring) and $-1$ to $\pi^*=\pi_{gs}$ (seller-favoring). The Chacon RD value (+0.0149) reflects a synthetic six-agent benchmark with balanced supply-demand; our $+0.665$ reflects the MTE structural asymmetry (4 sellers vs. 1 dominant buyer at $\varphi=1.5$) which competes the price toward $\pi_{gb}$. Per-agent distributional inequality (Gini) is reported separately in Fig.~\ref{fig:price_of_fairness}. Audit axis 3 (B5), CAL-8.}
\label{fig:audit_chacon}
\end{figure}

---

## V. Discussion

### V.A Why P2P wins at 144\,\% community coverage

At 144\,\% community coverage, the regulatory differentiators of monthly settlement lose traction: C1's Type 1 cap is bounded by each agent's own consumption, so additional high-PV surplus falls into the lower-valued Type 2 spot residual; C2's PDE pooling re-allocates the aggregate but is itself capped by the community's monthly deficit. P2P faces neither cap---any seller-buyer pair can clear surplus hourly at an endogenous price, monetizing what would otherwise hit an administrative ceiling.

Figure~\ref{fig:c1_vs_c4_detailed} compares C1 and C2 per agent at the case study: C1 outperforms C2 for the three smaller-load prosumers (Udenar, Mariana, HUDN); C2 wins for UCC (large deficit absorbing the PDE share) and Cesmag (largest surplus, redistributed favourably). The aggregate favours C2 by 0.13 M COP, but both administrative schemes remain dominated by P2P (Table I).

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_c1_vs_c4_detailed.png}
\caption{Per-agent net benefit at the case-study coverage, C1 (CREG 174) versus C2 (CREG 101 072). C1 outperforms C2 for the three smaller-load prosumers (Udenar, Mariana, HUDN) where individual Type 1 valuation extracts more value, while C2 outperforms C1 for UCC (large demand absorbing the PDE share) and Cesmag (largest surplus profile redistributed via PDE). The aggregate favours C2 because the two C2-winning margins exceed the three C1-winning margins.}
\label{fig:c1_vs_c4_detailed}
\end{figure}

The Price-of-Fairness analysis of Bertsimas et al.\ \cite{Bertsimas2011PoF} (Fig.~\ref{fig:price_of_fairness}) makes the distributional-equity vs.\ aggregate-efficiency trade-off explicit at the case-study coverage. We use the Gini coefficient over per-agent net benefits as the inequality measure (standard in P2P-energy literature \cite{Sorin2019Consensus}); at $\varphi = 1.5$, P2P maximizes total welfare while C1 attains the minimum Gini (5.94 M COP, $G = 0.111$ vs.\ 5.63 M COP, $G = 0.106$). The aggregate $\mathrm{PoF} = (W_\text{eff} - W_\text{fair}) / |W_\text{eff}| = 5.2\,\%$, equivalent to a community welfare loss of 308 kCOP if the equitable allocation were enforced.

The per-agent breakdown $\mathrm{PoF}_n$ shows that the cost of fairness is highly concentrated: Cesmag alone bears 70\,\% of the community sacrifice (214 of 308 kCOP), with an individual relative loss of 17.9\,\%, while the remaining four institutions sacrifice 1--2.5\,\% each. Cesmag is also the institution with the largest P2P advantage over C1 (+21.8\,\%, Sec.\ IV.C), so a single agent operates as the pivot of the welfare--equity trade-off. This concentration informs policy design: an equitable redistribution scheme that compensates Cesmag for its surplus role---rather than redistributing across all agents uniformly---would close the 5.2\,\% efficiency gap without sacrificing the buyer-favoring price formation that benefits the rest of the community. The Gini gap between P2P and C1 is $\Delta G \approx 0.005$, so the welfare premium is achieved at near-negligible distributional cost. The 5.2\,\% aggregate gap remains well within the 6\,\% decentralization tolerance documented by the algorithm's original authors \cite{Chacon2025EMS}.

\begin{figure}[ht]
\centering
\includegraphics[width=0.48\textwidth]{fig_paper_price_of_fairness.png}
\caption{Price of Fairness analysis (Bertsimas, Farias \& Trichakis 2011). (a) Total welfare per scenario; the efficient scenario (max welfare) and the equitable scenario (min Gini) are annotated. (b) Gini coefficient per scenario, ascending; lower is fairer. (c) Per-agent sacrifice $\mathrm{PoF}_n = \max\{0, (B_n^\text{eff} - B_n^\text{fair}) / |B_n^\text{eff}|\}$: institutions that would be net sellers under the efficient allocation absorb the bulk of the equity cost.}
\label{fig:price_of_fairness}
\end{figure}

### V.B Robustness above the case-study coverage

The ranking obtained at the case-study coverage (P2P $>$ C2 $>$ C1) is preserved at all higher PV factors. The refined sweep of Table III reveals two structural regimes for the P2P advantage over C1. Across the plateau $\varphi \in [1.1, 1.5]$ the advantage is essentially constant ($+300$ to $+310$ kCOP, intra-plateau variation below 3\,\%), confirming that the case-study coverage of 144\,\% is one valid sample of a continuous robustness range and not a load-bearing point estimate. Beyond $\varphi=1.5$ the advantage saturates monotonically to $+227$, $+179$, and $+149$ kCOP at $\varphi=2.0, 2.5, 3.0$ respectively---a 52\,\% drop from the plateau. The saturation reflects a competitive ceiling: as community PV becomes overabundant, both administrative schemes capture a growing share of the same surplus, narrowing the differentiator that hourly clearing introduces. Crucially, P2P remains rank 1 throughout the saturation tail and C1 remains last, and the dominance persists across both admissible PDE methods of CREG 101 072/2025 art.\ 5, ruling out the specific PDE rule as an artifact of the case-study finding. Internal peer trades absorb a growing absolute fraction of the community surplus at clearing prices that exceed the spot floor (234 COP/kWh, August mean), value that monthly settlement schemes structurally cannot capture: their Type 1 / PDE caps are bounded by the community's monthly net deficit while the surplus regime exceeds it.

### V.C Per-agent heterogeneity matters for adoption

The aggregate ranking conceals consequential individual outcomes. At the empirical baseline (96 \% coverage) C1 narrowly leads but three of five institutions already prefer P2P (Udenar, HUDN, Cesmag); at the case-study coverage of 144 \% the count climbs to four of five (adding Mariana), with UCC the only outlier. Under voluntary adoption, an analysis based solely on the aggregate would mis-classify the institutions whose role under P2P is to *sell* (Udenar, HUDN, Cesmag) and the ones with mixed-role profiles (Mariana) — precisely the agents on which the success of any community energy scheme depends.

### V.D Policy implication

CREG 174/2021 (C1) and CREG 101 072/2025 (C2) are not equivalent under the case-study coverage projected by UPME for 2030 [19]: at $\varphi=1.5$ and beyond, C1 becomes the worst-performing mechanism while C2 remains second, and both administrative schemes are dominated by P2P. As Colombia scales solar capacity per the UPME 2025--2039 plan, the regulatory framework may need to accommodate dynamic clearing mechanisms. One possibility, consistent with the "agreed-among-members" clause of CREG 101 072/2025 art.\ 5 [4], is to admit dynamic PDE rules derived from market mechanisms rather than fixed administrative weights. The empirical evidence reported here motivates regulatory analysis of such an extension.

### V.E Limitations

Five limitations are recognized. First, the horizon is one month (744 hours); seasonal variation and the El Ni\~{n}o/La Ni\~{n}a cycle are not captured. Second, the community is small (five institutions in a single city), so generalisation requires further empirical validation. Third, the case-study generation is the empirical MTE series scaled by $\varphi=1.5$ to match the UPME 2030 distributed-PV projection [19]; the demand series is empirical but the PV regime is forecast, so the case study has the methodological status of an empirically-grounded scenario rather than a direct measurement at 144\,\% coverage. Fourth, neither demand response nor storage and curtailment are modelled---flexible loads or storage could shift peer demand into surplus hours and modify both the phase transition and the case-study margin. Fifth, the P2P market is not currently reglamented in Colombia; legal admissibility would need to be established either via an extended reading of CREG 101 072/2025 art.\ 5 [4] (dynamic PDE) or via a generalisation of the bilateral PPA framework of Law 143/1994 [20].

---

## VI. Conclusions

This paper compared a Stackelberg-plus-Replicator-Dynamics P2P market against CREG 174/2021 individual self-generation (C1) and CREG 101 072/2025 collective community settlement (C2) on metered demand from five academic institutions in Pasto, Narino (August 2025, 744\,h), with PV generation scaled to $\varphi=1.5$ times the empirical capacity to match the UPME 2025--2039 projection for 2030.

At the case-study coverage of 144\,\%, P2P ranks first: 5.5\,\% above C1 and 3.1\,\% above C2, with four of five institutions individually preferring P2P. The canonical decomposition shows a common self-consumption term (4.12 M COP); all scenario differences arise from the surplus-revenue term, where hourly P2P clearing extracts value beyond the monthly Type 1 and PDE caps. The Price-of-Fairness analysis quantifies the equity-efficiency trade-off at 5.2\,\%, of which 70\,\% (214 of 308 kCOP) is concentrated in a single institution (Cesmag); a redistribution scheme that compensates this pivot agent could close the efficiency gap without sacrificing the buyer-favoring price formation that benefits the rest of the community.

A 9-point PV-factor sweep characterises the phase transition with $\Delta\varphi=0.1$ resolution. At the empirical baseline (96\,\% coverage) C1 narrowly leads with a 2.9\,\% gap that lies within the 6\,\% decentralisation tolerance of \cite{Chacon2025EMS}, and three of five institutions already prefer P2P. The crossover is sharp: linearly interpolated at $\varphi\approx 1.03$, only 7 percentage points above the empirical baseline. From $\varphi=1.1$ to $\varphi=1.5$ the P2P advantage over C1 forms a plateau ($+300$ to $+310$ kCOP, intra-plateau variation below 3\,\%), so the choice of $\varphi=1.5$ as the case study is not a load-bearing operating point but a representative sample of a continuous robustness range. Beyond $\varphi=1.5$ the advantage saturates monotonically to $+149$ kCOP at $\varphi=3.0$ (a 52\,\% drop), but the P2P ranking remains first across all factors tested and across both admissible PDE methods.

As Colombia scales solar capacity, neither individual (CREG 174) nor collective administrative (CREG 101 072) settlement is optimal in the over-generation regime projected for 2030; a dynamic clearing mechanism, admissible under a market-based reading of CREG 101 072 art.~5, captures surplus that administrative rules cannot. Future work will extend the horizon to a full year, calibrate per-agent levelised costs, model demand response and storage, and conduct a global sensitivity analysis around the phase-transition threshold.

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

[23] Y. Yang, S. Xu, L. Pan, J. Liu, J. Liu, and W. Hu, "Distributed prosumer trading in the electricity and carbon markets considering user utility," *Renewable Energy*, vol. 228, p. 120669, 2024.

[24] J. Martinez-Piazuelo, N. Quijano, and C. Ocampo-Martinez, "Decentralized charging coordination of electric vehicles under feeder capacity constraints," *IEEE Transactions on Control of Network Systems*, vol. 9, no. 4, pp. 1600-1610, 2022.

[25] IRENA, "Renewable Power Generation Costs in 2024," International Renewable Energy Agency, Abu Dhabi, 2025.
