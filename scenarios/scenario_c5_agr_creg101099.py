"""C5 — Autogeneración Remota (AGR), CREG 101 099/2026 (CAL-37, ADR-0037).

Benchmark ADMINISTRATIVO del régimen AGR para el ecosistema MTE; el P2P es el
clearing de mercado dentro del mismo régimen (auditoría Capa 2: el clearing
dinámico no es admisible bajo CREG 174 ni 101 072; su hogar es la 101 099).

Mecánica horaria:
  1. Autoconsumo local a ``pi_gs[n,k]`` (offset común a todos los escenarios).
  2. Compensación inter-fronteras: ``E_comp[k] = min(Σ surplus, Σ deficit)``
     (doble límite de despacho, informe Fajardo §3.7.1 — opera como
     COMPENSACIÓN, no comercialización), asignada DINÁMICAMENTE proporcional
     a los déficits horarios de los mismos agentes (lección del artefacto C2,
     auditoría §7.5: no hay consumidores puros estáticos en MTE) y valorada a
     la TASA NO-REGULADA (CAL-16): ``g + cvm + cot_alpha·cot − mem``
     (~506 COP/kWh). La exclusión CERE/FAZNI del autoconsumo (CREG 101 099,
     Hoja 10: "Estos cargos no aplicarán para los autoconsumos...") está
     contenida en esta tasa (CERE vive en G; FAZNI en MEM). El kWh compensado
     viaja por la red → T+D+PR se siguen pagando (Art. 2.2.3.2.4.1 deja la
     exoneración de T a reglamentación futura — supuesto S6).
     El TOTAL comunitario es invariante al split contractual ``f_split``
     ("pague lo contratado", CREG 024/1995; análogo a la invariancia CAL-21).
  3. Excedente residual no compensado → ``pi_bolsa[k]`` HORARIO menos la
     comisión MEM (lección artefacto C2: nunca una constante plana).
  4. LBC (Art. 20) + PES: SOLO DIAGNÓSTICO — no altera ``net_benefit``.
     LBC_i = media móvil de ``lbc_window_days`` días (Anexo 1 CREG 101 019/
     2022; percentil/método = supuesto S4, gated a asesores). Trigger:
     ``pi_bolsa[k] > pi_escasez[k]`` (PES superior mensual replicado horario,
     supuesto S3).

Precisiones del Informe 4 MTE (Fajardo, 2026-05-27) y texto oficial:
  - **Supuesto declarado**: el activo MTE (87.75 kWp) NO participa en
    mecanismos del cargo por confiabilidad, ni en el mercado secundario,
    ni tiene asignaciones de OEF — condición habilitante del tratamiento
    de los arts. 18/36 de la 101 099.
  - **CERE**: la norma define una devolución específica ``CERE × ERMIC``
    (arts. 18/36/56: energía registrada que máximo iguala el consumo
    horario, valorada al CERE del cargo por confiabilidad CREG 071/2006)
    del agente generador al AGR/PMR. Aquí se asume embebida en G
    (supuesto S1, ampliado en auditoría — pregunta a asesores); es de
    segundo orden frente a la tasa CAL-16.

Supuestos S1–S6 declarables en Métodos: ver spec
``docs/superpowers/specs/2026-06-09-cal37-c5-agr-design.md`` y ADR-0037.

Filosofía A (validada con Pantoja): ``net_benefit = autoconsumo +
compensación (receptor+generador) + residual_bolsa``; los costos del consumo
residual a red no se restan (se incurrirían igual sin el esquema).
"""
from typing import Optional, Union

import numpy as np

from ._pi_gs import as_pi_gs_array


def run_c5_agr_creg101099(
    D: np.ndarray,                 # (N, T) demanda [kWh/h]
    G: np.ndarray,                 # (N, T) generación [kWh/h]
    pi_gs: Union[float, np.ndarray],
    pi_bolsa: np.ndarray,          # (T,) bolsa horaria (con techo PES CAL-14)
    g_component:   Union[float, np.ndarray] = 0.0,
    cvm_component: Union[float, np.ndarray] = 0.0,
    cot_component: Union[float, np.ndarray] = 0.0,
    mem_costs:     Union[float, np.ndarray] = 0.0,
    cot_alpha: float = 1.0,
    f_split: float = 0.5,          # reparto contractual generador↔receptor
    pi_escasez: Optional[np.ndarray] = None,   # (T,) PES mensual→horario
    lbc_window_days: int = 60,     # ventana LBC (Anexo 1 CREG 101 019/2022)
    prosumer_ids: Optional[list] = None,       # informativo (todos en MTE)
) -> dict:
    """Simula el régimen AGR (CREG 101 099/2026). Ver docstring del módulo.

    Retorna dict con la estructura estándar de C1–C4:
    ``{per_agent, aggregate, hourly, regulatory, params}``.
    """
    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)
    g_v   = as_pi_gs_array(g_component, N, T)
    cvm_v = as_pi_gs_array(cvm_component, N, T)
    cot_v = as_pi_gs_array(cot_component, N, T)
    mem_v = as_pi_gs_array(mem_costs, N, T)
    pb = np.asarray(pi_bolsa, dtype=float).reshape(-1)
    tasa = g_v + cvm_v + cot_alpha * cot_v - mem_v   # (N,T) no-regulada CAL-16

    G_pos = np.maximum(G, 0.0)
    D_pos = np.maximum(D, 0.0)
    auto    = np.minimum(G_pos, D_pos)
    surplus = np.maximum(G_pos - D_pos, 0.0)
    deficit = np.maximum(D_pos - G_pos, 0.0)

    sur_tot = surplus.sum(axis=0)                    # (T,)
    def_tot = deficit.sum(axis=0)
    e_comp  = np.minimum(sur_tot, def_tot)           # doble límite (Fajardo)

    # Asignación dinámica proporcional a déficits / aporte proporcional a surplus
    with np.errstate(divide="ignore", invalid="ignore"):
        comp_rec = np.where(def_tot > 1e-12,
                            deficit * (e_comp / def_tot), 0.0)   # (N,T) recibido
        comp_gen = np.where(sur_tot > 1e-12,
                            surplus * (e_comp / sur_tot), 0.0)   # (N,T) aportado

    residual = surplus - comp_gen                                # (N,T) → bolsa

    # Valoración: el valor de cada kWh compensado es la tasa del RECEPTOR;
    # f_split lo reparte contractualmente (total invariante a f_split).
    valor_k = (comp_rec * tasa).sum(axis=0)                      # (T,) valor/h
    rec_val = (1.0 - f_split) * (comp_rec * tasa)                # (N,T) receptor
    # gen_share normaliza por la energía COMPENSADA (e_comp), no por el
    # surplus total: Σ_n gen_share = 1 cuando hay compensación, garantizando
    # la invariancia del total a f_split (el test de invariancia atrapó el
    # bug de normalizar por sur_tot, que perdía valor con residual > 0).
    with np.errstate(divide="ignore", invalid="ignore"):
        gen_share = np.where(e_comp > 1e-12, comp_gen / e_comp, 0.0)
    gen_val = f_split * gen_share * valor_k[None, :]             # (N,T) generador

    savings_auto   = (auto * pi_gs_v).sum(axis=1)
    comp_receptor  = rec_val.sum(axis=1)
    comp_generador = gen_val.sum(axis=1)
    residual_bolsa = (residual * np.maximum(pb[None, :] - mem_v, 0.0)).sum(axis=1)

    net = savings_auto + comp_receptor + comp_generador + residual_bolsa

    # ── LBC/PES: SOLO diagnóstico (S4 gated a asesores) ──────────────────
    lbc_active_hours = 0
    exp_kwh = 0.0
    exp_cop = 0.0
    if pi_escasez is not None:
        pes = np.asarray(pi_escasez, dtype=float).reshape(-1)
        win = min(lbc_window_days * 24, T)
        lbc = np.array([float(np.mean(D_pos[n, :win])) for n in range(N)])
        trig = pb > pes
        lbc_active_hours = int(trig.sum())
        if lbc_active_hours:
            exceso = np.maximum(D_pos[:, trig] - lbc[:, None], 0.0)
            exp_kwh = float(exceso.sum())
            exp_cop = float((exceso * np.maximum(
                pb[None, trig] - pi_gs_v[:, trig], 0.0)).sum())

    per_agent = {
        n: {
            "savings_autoconsumo": float(savings_auto[n]),
            "comp_receptor":  float(comp_receptor[n]),
            "comp_generador": float(comp_generador[n]),
            "residual_bolsa": float(residual_bolsa[n]),
            "net_benefit":    float(net[n]),
        } for n in range(N)
    }
    return {
        "per_agent": per_agent,
        "aggregate": {
            "total_net_benefit":    float(net.sum()),
            "total_autoconsumo":    float(savings_auto.sum()),
            "total_compensacion":   float((comp_receptor + comp_generador).sum()),
            "total_residual_bolsa": float(residual_bolsa.sum()),
            "kwh_compensados":      float(e_comp.sum()),
        },
        "hourly": {"e_comp": e_comp, "surplus_pool": sur_tot,
                   "deficit_pool": def_tot},
        "regulatory": {
            "creg_ref": "101 099/2026 (AGR)",
            "lbc_active_hours": lbc_active_hours,
            "lbc_exposicion_kwh": exp_kwh,
            "lbc_exposicion_cop": exp_cop,
            "lbc_afecta_beneficio": False,   # gated a asesores (S4)
        },
        "params": {"f_split": f_split, "cot_alpha": cot_alpha,
                   "tasa_media": float(tasa.mean()),
                   "lbc_window_days": lbc_window_days},
    }
