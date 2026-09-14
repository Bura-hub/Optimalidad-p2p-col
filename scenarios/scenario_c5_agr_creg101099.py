"""C5 — Autogeneración remota (AGR), Resolución CREG 101 099 de 2026 (D6, C-179).

La mecánica de los artículos 16 a 21, con la elegibilidad SUPUESTA y
declarada: hoy las cinco no son sujeto (el productor marginal exige control
societario y el autogenerador remoto atiende sus propias sedes; la cláusula
del CIIU del art. 17 va como consulta al asesor).

  1. Autoconsumo embebido (art. 21), a la tarifa de su hora, como en todos.
  2. El contrato despachado cada hora (art. 19, «pague lo contratado»): el
     mínimo entre la inyección agregada de la cartera y la importación
     agregada de las fronteras asociadas. Simplificación declarada: la cartera
     de las cinco plantas actúa como el activo; la norma habla de un activo
     por relación y no dice cómo asignar plantas a consumidores.
  3. Su valor para la comunidad es la compra que los consumidores evitan como
     usuarios no regulados (art. 16 ii), a la tasa de CAL-16:
     G + Cv + α·COT − MEM. El PRECIO DEL CONTRATO reparte ese valor entre el
     generador y los consumidores y no cambia el total. Sale de la serie
     mensual de XM de contratos con destino al mercado no regulado
     (`data/precios_contratos.py`); sin ella se conserva el reparto por
     fracción f de CAL-37, declarado.
  4. Lo que sobra de la generación se entrega al mercado mayorista (art. 16 i)
     a la bolsa de su hora menos los costos del mercado.
  5. La devolución del cargo por confiabilidad (art. 18): el CERE sobre la
     generación de cada hora que no supere el consumo de cada frontera, con
     un porcentaje fijo por frontera. Sin la serie del CERE se declara
     omitida: es de segundo orden y a favor de la comunidad.
  6. La línea base de consumo (art. 20), solo diagnóstico.

La cantidad despachada coincide con la que el escenario viejo llamaba
compensación (H-72); lo que cambia es el precio y la devolución.

Actividad 2.2.
"""
from typing import Optional, Union

import numpy as np

from ._pi_gs import as_pi_gs_array


def run_c5_agr_creg101099(
    D: np.ndarray,
    G: np.ndarray,
    pi_gs: Union[float, np.ndarray],
    pi_bolsa: np.ndarray,
    g_component:   Union[float, np.ndarray] = 0.0,
    cvm_component: Union[float, np.ndarray] = 0.0,
    cot_component: Union[float, np.ndarray] = 0.0,
    mem_costs:     Union[float, np.ndarray] = 0.0,
    cot_alpha: float = 1.0,
    f_split: float = 0.5,          # solo sin precio de contrato (CAL-37)
    pi_escasez: Optional[np.ndarray] = None,
    lbc_window_days: int = 60,
    prosumer_ids: Optional[list] = None,
    dt: float = 1.0,
    pi_contrato: Union[float, np.ndarray, None] = None,   # (T,) o escalar
    cere: Union[float, np.ndarray, None] = None,          # (T,) o escalar
    pde_agr: Optional[np.ndarray] = None,                 # (N,), art. 18
) -> dict:
    """Simula la autogeneración remota. Ver el docstring del módulo."""
    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)
    g_v   = as_pi_gs_array(g_component, N, T)
    cvm_v = as_pi_gs_array(cvm_component, N, T)
    cot_v = as_pi_gs_array(cot_component, N, T)
    mem_v = as_pi_gs_array(mem_costs, N, T)
    pb = np.asarray(pi_bolsa, dtype=float).reshape(-1)
    tasa = g_v + cvm_v + cot_alpha * cot_v - mem_v

    G_pos = np.maximum(G, 0.0)
    D_pos = np.maximum(D, 0.0)
    auto    = np.minimum(G_pos, D_pos)
    surplus = np.maximum(G_pos - D_pos, 0.0)
    deficit = np.maximum(D_pos - G_pos, 0.0)

    iny_tot = surplus.sum(axis=0)
    imp_tot = deficit.sum(axis=0)
    q = np.minimum(iny_tot, imp_tot)                       # art. 19
    with np.errstate(divide="ignore", invalid="ignore"):
        q_rec = np.where(imp_tot > 1e-12, deficit * (q / imp_tot), 0.0)
        q_gen = np.where(iny_tot > 1e-12, surplus * (q / iny_tot), 0.0)
    sobrante = surplus - q_gen

    if pi_contrato is not None:
        pc = np.broadcast_to(np.asarray(pi_contrato, dtype=float), (T,))
        gen_val = q_gen * pc[None, :]
        rec_val = q_rec * (tasa - pc[None, :])
        fuente_precio = "XM, contratos con destino al mercado no regulado"
    else:
        valor_k = (q_rec * tasa).sum(axis=0)
        rec_val = (1.0 - f_split) * (q_rec * tasa)
        with np.errstate(divide="ignore", invalid="ignore"):
            gen_share = np.where(q > 1e-12, q_gen / q, 0.0)
        gen_val = f_split * gen_share * valor_k[None, :]
        fuente_precio = f"reparto por fraccion f={f_split} (sin precio de contrato)"

    bolsa_neta = np.maximum(pb[None, :] - mem_v, 0.0)
    resid_val = sobrante * bolsa_neta

    if cere is None:
        cere_val = np.zeros((N, T))
    else:
        pa = (np.full(N, 1.0 / N) if pde_agr is None
              else np.asarray(pde_agr, dtype=float))
        if abs(float(pa.sum()) - 1.0) > 1e-9 or (pa < 0).any():
            raise ValueError("el porcentaje del art. 18 debe sumar 1")
        ermic = np.minimum(pa[:, None] * iny_tot[None, :], deficit)
        cere_val = ermic * np.broadcast_to(
            np.asarray(cere, dtype=float), (T,))[None, :]

    neto_horario = auto * pi_gs_v + rec_val + gen_val + resid_val + cere_val

    savings_auto   = (auto * pi_gs_v).sum(axis=1)
    comp_receptor  = rec_val.sum(axis=1)
    comp_generador = gen_val.sum(axis=1)
    residual_bolsa = resid_val.sum(axis=1)
    devolucion     = cere_val.sum(axis=1)
    e_auto, e_contrato, e_sobrante = (auto.sum(axis=1), q_gen.sum(axis=1),
                                      sobrante.sum(axis=1))

    if dt != 1.0:
        neto_horario = neto_horario * dt
        savings_auto = savings_auto * dt
        comp_receptor = comp_receptor * dt
        comp_generador = comp_generador * dt
        residual_bolsa = residual_bolsa * dt
        devolucion = devolucion * dt
        e_auto, e_contrato, e_sobrante = e_auto * dt, e_contrato * dt, e_sobrante * dt

    net = savings_auto + comp_receptor + comp_generador + residual_bolsa + devolucion

    # ── LBC/PES: SOLO diagnóstico (S4 gated a asesores) ──────────────────
    lbc_active_hours = 0
    exp_kwh = 0.0
    exp_cop = 0.0
    if pi_escasez is not None:
        pes = np.asarray(pi_escasez, dtype=float).reshape(-1)
        # CAL-46: la ventana está en días, de modo que su longitud en pasos
        # depende de la duración del paso. Es el único sitio de C5 que no es
        # homogéneo y por eso no basta escalar el dinero al final.
        win = min(int(round(lbc_window_days * 24 / dt)), T)
        lbc = np.array([float(np.mean(D_pos[n, :win])) for n in range(N)])
        trig = pb > pes
        lbc_active_hours = int(trig.sum())
        if lbc_active_hours:
            exceso = np.maximum(D_pos[:, trig] - lbc[:, None], 0.0)
            exp_kwh = float(exceso.sum()) * dt
            exp_cop = float((exceso * np.maximum(
                pb[None, trig] - pi_gs_v[:, trig], 0.0)).sum()) * dt

    per_agent = {
        n: {
            "savings_autoconsumo": float(savings_auto[n]),
            "contrato_receptor":   float(comp_receptor[n]),
            "contrato_generador":  float(comp_generador[n]),
            "comp_receptor":       float(comp_receptor[n]),    # alias CAL-37
            "comp_generador":      float(comp_generador[n]),   # alias CAL-37
            "residual_bolsa":      float(residual_bolsa[n]),
            "devolucion_cere":     float(devolucion[n]),
            "E_auto":              float(e_auto[n]),
            "E_contrato":          float(e_contrato[n]),
            "E_sobrante":          float(e_sobrante[n]),
            "net_benefit":         float(net[n]),
        } for n in range(N)
    }
    total_contrato = float((comp_receptor + comp_generador).sum())
    return {
        "per_agent": per_agent,
        "neto_horario": neto_horario,
        "aggregate": {
            "total_net_benefit":     float(net.sum()),
            "total_autoconsumo":     float(savings_auto.sum()),
            "total_contrato":        total_contrato,
            "total_compensacion":    total_contrato,          # alias CAL-37
            "total_residual_bolsa":  float(residual_bolsa.sum()),
            "total_devolucion_cere": float(devolucion.sum()),
            "kwh_contrato":          float(q.sum()) * dt,
            "kwh_compensados":       float(q.sum()) * dt,     # alias CAL-37
        },
        "hourly": {"contrato": q, "e_comp": q, "surplus_pool": iny_tot,
                   "deficit_pool": imp_tot},
        "regulatory": {
            "creg_ref": "101 099/2026 (AGR), arts. 16 a 21",
            "precio_contrato": fuente_precio,
            "cere_omitido": cere is None,
            "lbc_active_hours": lbc_active_hours,
            "lbc_exposicion_kwh": exp_kwh,
            "lbc_exposicion_cop": exp_cop,
            "lbc_afecta_beneficio": False,
        },
        "params": {"f_split": f_split, "cot_alpha": cot_alpha,
                   "tasa_media": float(tasa.mean()),
                   "lbc_window_days": lbc_window_days},
    }
