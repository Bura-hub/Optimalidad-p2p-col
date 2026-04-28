"""
base_case_data.py  (v3)
-----------------------
Parámetros para datos sintéticos de validación (JoinFinal.m / Bienestar6p.py).

PRECIOS — dos conjuntos:
  GRID_PARAMS_BASE   : precios originales del modelo de Sofía (adimensionales)
                       Usar con datos sintéticos para reproducir resultados base.
  GRID_PARAMS_REAL   : precios calibrados Colombia 2025 (COP/kWh)
                       Usar con datos reales MTE para comparación regulatoria.
"""

import numpy as np

# ── Precios modelo base (Sofía/JoinFinal.m) ───────────────────────────────────
PGS = 1250.0   # precio venta red al usuario (adimensional)
PGB = 114.0    # precio compra red al usuario (adimensional)
GRID_PARAMS = {"pi_gs": PGS, "pi_gb": PGB}

# ── Precios calibrados Colombia 2025 (COP/kWh) ───────────────────────────────
# CAL-8 (2026-04-28): la calibración real del precio de venta al usuario
# pasó al módulo data/cedenar_tariff.py, que carga la tarifa Cedenar mensual
# diferenciada por categoría (oficial 797 / comercial 956 COP/kWh) desde
# data/tarifas_cedenar_mensual.csv y data/cedenar_pdfs/. main_simulation.py
# con --data real reemplaza GRID_PARAMS_REAL["pi_gs"] por el promedio
# comunitario ponderado por demanda (≈ 906 COP/kWh).
#
# PGS_COP = 650 queda como DEFAULT_PI_GS_FALLBACK únicamente para meses sin
# PDF Cedenar disponible (hoy ninguno tras la cobertura abr-2025 → abr-2026)
# y como referencia escalar del modo sintético.
#
# PGB_COP: precio de bolsa XM, promedio Abr-Dic 2025.
#   Promedio empírico ≈ 222 COP/kWh (XM API).
#   Valor usado: 280 COP/kWh (promedio conservador para barridos SA-1 con
#   pi_gb constante; el modo --data real usa la serie horaria real).
#
# Ver Documentos/notas_modelo_tesis.md §CAL-8 para la trazabilidad completa.
PGS_COP = 650.0   # legacy/fallback; CAL-8 usa Cedenar mensual per-agente
PGB_COP = 280.0
GRID_PARAMS_REAL = {"pi_gs": PGS_COP, "pi_gb": PGB_COP}

# ── Coeficientes de costo (JoinFinal.m) ──────────────────────────────────────
SCALE = 6.0865
A = SCALE * np.array([4 * 0.089, 0.069, 0.0, 0.0, 0.0, 0.0])
B = SCALE * np.array([3.93 * 52, 32.0, 47.0, 37.0, 0.0, 0.0])
C = np.zeros(6)

def get_agent_params() -> dict:
    return {
        "N": 6, "a": A.copy(), "b": B.copy(), "c": C.copy(),
        "lam":   100.0 * np.ones(6),
        "theta":   0.5 * np.ones(6),
        "etha":    0.1 * np.ones(6),
        # DR Program: fracción de demanda flexible por agente (Algoritmo 1, paso 15-22)
        # Agentes 0-3 (prosumidores): 20% de flexibilidad (carga gestionable).
        # Agentes 4-5 (consumidores): 10% de flexibilidad (baja gestión de carga).
        # Referencia: Chacón et al. (2025) §III-A, perfil típico EC académica.
        "alpha": np.array([0.20, 0.20, 0.20, 0.20, 0.10, 0.10]),
    }

def get_generation_profiles() -> np.ndarray:
    import numpy as np
    from numpy.random import default_rng
    G = np.zeros((6, 24))
    t = np.arange(24)
    G[0, :] = np.array([2.]*6+[3.]*6+[4.]*6+[2.]*6)
    G[1, :] = np.clip(3.5*np.exp(-0.5*((t-12)/3)**2)+0.5, 0, None)
    G[1, :6] = 0; G[1, 19:] = 0
    G[2, :] = np.clip(2.5*np.exp(-0.5*((t-13)/2.5)**2), 0, None)
    G[2, :7] = 0; G[2, 19:] = 0
    G[3, :] = np.clip(1.2+default_rng(7).normal(0, 0.25, 24), 0, None)
    return G

def get_demand_profiles() -> np.ndarray:
    D = np.zeros((6, 24))
    D[0,:] = [1.0,0.9,0.9,0.9,1.0,1.2,1.8,2.5,3.0,3.2,3.0,2.8,
              2.5,2.8,3.0,3.2,3.5,3.8,3.5,3.0,2.5,2.0,1.5,1.2]
    D[1,:] = [0.4,0.3,0.3,0.3,0.4,0.8,1.2,0.9,0.7,0.5,0.5,0.6,
              0.7,0.6,0.5,0.5,0.7,1.0,1.3,1.4,1.2,0.9,0.6,0.5]
    D[2,:] = [0.2]*4+[0.2,0.4,0.8,0.6,0.5,0.4,0.4,0.5,
              0.6,0.5,0.4,0.4,0.6,0.9,1.1,1.0,0.8,0.5,0.3,0.2]
    D[3,:] = [0.]*5+[0.1,2.0,3.5,3.8,4.0,4.0,3.8,
              3.5,3.5,3.8,4.0,3.5,2.5,0.1]+[0.]*5
    D[4,:] = [0.1]*5+[0.2,0.4,0.3,0.3,0.2,0.2,0.2,
              0.3,0.3,0.2,0.2,0.3,0.5,0.6,0.6,0.5,0.3,0.2,0.1]
    D[5,:] = [0.1]*5+[0.1,0.3,0.2,0.2,0.1,0.1,0.2,
              0.2,0.2,0.1,0.1,0.2,0.4,0.5,0.5,0.4,0.2,0.1,0.1]
    return D

def get_hourly_prices() -> np.ndarray:
    t = np.arange(24)
    return np.clip(
        PGB + (PGS-PGB)*0.3*(np.exp(-0.5*((t-18)/2)**2)
                              + 0.5*np.exp(-0.5*((t-8)/1.5)**2)),
        PGB, PGS)

def get_pde_weights() -> np.ndarray:
    cap = np.array([3., 4., 3., 2., 0., 0.])
    return cap / cap.sum()
