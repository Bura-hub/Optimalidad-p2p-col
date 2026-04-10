"""
base_case_data.py  (v2)
-----------------------
Parámetros exactamente como en JoinFinal.m y Bienestar6p.py de Sofía.

Valores que aparecen en el código fuente:
  Pgs = 1250,  Pgb = 114          (JoinFinal.m)
  theta = 0.5 * ones(6)           (JoinFinal.m / OptimizacinCon.m)
  lamda = 100 * ones(6)           (JoinFinal.m)
  etha0 = 0.1 * ones(6)          (JoinFinal.m / OptimizacinCon.m)
  a = 6.0865 * [4*0.089, 0.069, 0, 0, 0, 0]
  b = 6.0865 * [3.93*52, 32, 47, 37, 0, 0]

Bienestar6p.py (versión 6 agentes artículo Latin):
  Pgs = 1650,  Pgb = 50
  theta = 10*ones(6), lamda = 100*ones(6), etha0 = 1*ones(6)
  a = [0.089, 0.110, 0.069, 0, 0, 0]
  b = [52, 58, 40, 37, 32, 0]

Se usa la versión JoinFinal.m (6 agentes, Pgs=1250) que es la del artículo
publicado y el modelo base de referencia de la tesis.
"""

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Parámetros de red  (JoinFinal.m)
# ─────────────────────────────────────────────────────────────────────────────
PGS = 1250.0
PGB = 114.0

GRID_PARAMS = {"pi_gs": PGS, "pi_gb": PGB}

# ─────────────────────────────────────────────────────────────────────────────
# Coeficientes de costo  (JoinFinal.m, 6 agentes)
# ─────────────────────────────────────────────────────────────────────────────
SCALE = 6.0865

a_raw = np.array([4 * 0.089, 0.069, 0.0, 0.0, 0.0, 0.0])
b_raw = np.array([3.93 * 52,  32.0, 47.0, 37.0, 0.0, 0.0])

A = SCALE * a_raw   # [2.169, 0.420, 0, 0, 0, 0]
B = SCALE * b_raw   # [1243.7, 194.8, 286.1, 225.2, 0, 0]
C = np.zeros(6)     # coef. independiente (para G_klim)

# ─────────────────────────────────────────────────────────────────────────────
# Parámetros de agentes  (JoinFinal.m / OptimizacinCon.m)
# ─────────────────────────────────────────────────────────────────────────────

def get_agent_params() -> dict:
    """
    Parámetros de los 6 agentes.
    No incluye 'alpha' (fracción DR) porque Brayan no implementa DR.
    La demanda D se usa directamente de los datos reales.
    """
    return {
        "N":    6,
        "a":    A.copy(),
        "b":    B.copy(),
        "c":    C.copy(),
        "lam":  100.0 * np.ones(6),
        "theta": 0.5  * np.ones(6),
        "etha":  0.1  * np.ones(6),
    }

# ─────────────────────────────────────────────────────────────────────────────
# Perfiles de generación y demanda (24 h, 6 agentes)
# Aproximan el Excel 'Demandaóptima_Comunidad6pp' usado por Sofía.
# Agente 1 = No renovable (generación casi plana, caro)
# Agente 2 = Solar+Eólica  (perfil diurno)
# Agentes 3,4 = prosumidores con generación solar/eólica
# Agentes 5,6 = consumidores puros (G=0)
# ─────────────────────────────────────────────────────────────────────────────

def _gaussian(peak, center, sigma, hours=24):
    t = np.arange(hours)
    return peak * np.exp(-0.5 * ((t - center) / sigma)**2)

def get_generation_profiles() -> np.ndarray:
    G = np.zeros((6, 24))
    # Agente 1: No renovable — generación constante escalada
    G[0, :] = np.array([2.0]*6 + [3.0]*6 + [4.0]*6 + [2.0]*6)
    # Agente 2: Solar+Eólica
    G[1, :] = np.clip(_gaussian(3.5, 12, 3.0) + 0.5, 0, None)
    G[1, :6] = 0; G[1, 19:] = 0
    # Agente 3: Fotovoltaica
    G[2, :] = np.clip(_gaussian(2.5, 13, 2.5), 0, None)
    G[2, :7] = 0; G[2, 19:] = 0
    # Agente 4: Eólica
    rng = np.random.default_rng(7)
    G[3, :] = np.clip(1.2 + rng.normal(0, 0.25, 24), 0, None)
    # Agentes 5,6: consumidores puros
    return np.clip(G, 0, None)

def get_demand_profiles() -> np.ndarray:
    D = np.zeros((6, 24))
    D[0, :] = [1.0,0.9,0.9,0.9,1.0,1.2,1.8,2.5,3.0,3.2,3.0,2.8,
               2.5,2.8,3.0,3.2,3.5,3.8,3.5,3.0,2.5,2.0,1.5,1.2]
    D[1, :] = [0.4,0.3,0.3,0.3,0.4,0.8,1.2,0.9,0.7,0.5,0.5,0.6,
               0.7,0.6,0.5,0.5,0.7,1.0,1.3,1.4,1.2,0.9,0.6,0.5]
    D[2, :] = [0.2]*4 + [0.2,0.4,0.8,0.6,0.5,0.4,0.4,0.5,
               0.6,0.5,0.4,0.4,0.6,0.9,1.1,1.0,0.8,0.5,0.3,0.2]
    D[3, :] = [0.0]*5 + [0.1,2.0,3.5,3.8,4.0,4.0,3.8,
               3.5,3.5,3.8,4.0,3.5,2.5,0.1] + [0.0]*5
    D[4, :] = [0.1]*5 + [0.2,0.4,0.3,0.3,0.2,0.2,0.2,
               0.3,0.3,0.2,0.2,0.3,0.5,0.6,0.6,0.5,0.3,0.2,0.1]
    D[5, :] = [0.1]*5 + [0.1,0.3,0.2,0.2,0.1,0.1,0.2,
               0.2,0.2,0.1,0.1,0.2,0.4,0.5,0.5,0.4,0.2,0.1,0.1]
    return D

def get_hourly_prices() -> np.ndarray:
    """Precios aproximados para el programa DR."""
    t = np.arange(24)
    return np.clip(
        PGB + (PGS - PGB) * 0.3 * (
            np.exp(-0.5*((t-18)/2.0)**2) + 0.5*np.exp(-0.5*((t-8)/1.5)**2)
        ), PGB, PGS)

def get_pde_weights() -> np.ndarray:
    """PDE proporcional a capacidad instalada aproximada."""
    cap = np.array([3.0, 4.0, 3.0, 2.0, 0.0, 0.0])
    return cap / cap.sum()
