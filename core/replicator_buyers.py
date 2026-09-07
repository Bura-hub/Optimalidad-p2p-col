"""
replicator_buyers.py  (v3)
--------------------------
Fiel a ReplicadorWiSol2 de JoinFinal.m con integración numérica estable.

El problema del comprador en JoinFinal.m usa escalas muy diferentes
(VelWi=0.1, VelGPC=1e5) que generan sistemas stiff. Se usa Euler
explícito con paso fijo pequeño como en el solver ode15s de MATLAB,
que maneja bien sistemas stiff.

Nota de auditoría (A2, 2026-04-17) — CORREGIDA por H-42 el 2026-09-06
--------------------------------------------------------------------
El término de competencia en ``solve_buyers`` usa la forma agregada
``compe = etha_s * sum_Pji`` con ``etha_s = mean(etha_i)`` (línea del
bucle de integración). El modelo base ``JoinFinal.m:187-200`` define
``matriz = ones(I,I) - eye(I)`` y ``compe = etha * matriz``.

**La nota original afirmaba que ese producto se resolvía por indexación
lineal y daba ``compe(i=1)=0`` y ``compe(i>1)=etha``. Es falso.** En
``JoinFinal.m:27``, ``etha0`` es un **vector fila** de seis elementos, de
modo que ``etha * matriz`` es el producto ordinario vector por matriz y
produce ``compe(i) = suma_{k != i} etha_k``, uniforme entre compradores.
Con factor uniforme vale ``etha*(I-1)``, de manera que **la forma agregada
se queda corta por el factor (I-1)**.

Hay una tercera forma, y es la que importa: la línea **comentada** de
``JoinFinal.m:188`` y la ecuación (11) de la versión arbitrada escriben
``compe_i = beta_i * suma_{k != i} pi_k * suma_j P_jk``, que es la única en
la que **el precio de los demás entra en la aptitud de un comprador**. Las
otras dos no contienen ningún precio, de modo que el mecanismo de respuesta
al precio ajeno, que el artículo declara como contribución, no existe en
ellas. Medido: solo esa forma reproduce los resultados del caso publicado.
Ver H-42.

Nótese la incoherencia que eso deja hoy en pie: la función
``buyer_welfare`` (abajo) **sí** usa la forma publicada, mientras la
dinámica usa la agregada. Es decir, el módulo informa de un bienestar que
no corresponde al que su propia dinámica persigue. Adoptar la forma
publicada en la dinámica alinea las dos.

H-39 / H-40 (2026-09-06): **las fuentes del modelo base no coinciden**
en el índice de la energía de ese término. La versión arbitrada (*IEEE
Latin America Transactions* 23(8), agosto de 2025, ecuación 11), el
documento extenso y la línea comentada de ``JoinFinal.m:188``
multiplican por la energía del comprador AJENO; ``Bienestar6p.py``
multiplica por la PROPIA. Esta traducción sigue a la versión arbitrada,
y lo mismo para el término del pago. Compuerta en
``tests/gate_c138_bienestar_comprador.py``, que fija la forma elegida y
cuantifica la discrepancia. No afecta a la dinámica: esta función solo
informa.

El equilibrio agregado (``P_total``, ``pi_i`` dentro de ``[PGB, PGS]``,
vaciado de demanda) reproduce al oráculo SLSQP dentro de las
tolerancias declaradas en ``tests/golden_test_sofia.py``
(``atol = 0.15 kWh``, ``rtol = 5 %`` demanda). La corrida
``outputs/run_day_2025-08-06_1458.log`` muestra ``Σ W_i = +1 318.93``
u.o. y convergencia RD+Stackelberg sin warnings.

ADR-0038 (campaña de smokes, 2026-06-10): la forma matricial queda
disponible como flag opt-in ``buyer_competition="matrix"`` (default
``"aggregate"`` = comportamiento histórico bit a bit). El smoke A2 de
la campaña (`scripts/smoke_solver_robustness.py`) cuantifica el diff
numérico sobre sintético + horizonte completo para cerrar o escalar
esta deuda. El parámetro ``pi0`` (default None = CI histórica de
JoinFinal.m) habilita el multi-start del smoke S2 (unicidad del
equilibrio); ningún caller de producción lo usa.
"""

from typing import Optional

import numpy as np

VEL_WI  = 0.1
VEL_GPC = 1e5

# CAL-47 / H-37: cuántas veces puede partirse el paso al comprobar que el
# resultado no depende de él. Cuatro duplicaciones son un paso 16 veces más
# fino, que es el margen dentro del cual se midió que el reparto se estabiliza.
MAX_REFINOS_PASO = 4
PGB     = 114.0
PGS     = 1250.0


def solve_buyers(
    P_mat:       np.ndarray,   # (J, I)
    a_j:         np.ndarray,
    b_j:         np.ndarray,
    etha_i:      np.ndarray,   # (I,)
    pi_gs:       float = PGS,
    pi_gb:       float = PGB,
    tau:         float = 0.001,
    t_span:      tuple = (0.0, 0.01),
    n_points:    int   = 500,
    return_traj: bool  = False,
    # ── ADR-0038 (opt-in, defaults = comportamiento histórico) ──────────
    buyer_competition: str = "aggregate",   # "aggregate" | "matrix"
    pi0:         Optional[np.ndarray] = None,  # CI de precios (I,) o (I+1,)
    # ── CAL-47 / H-37 (opt-in, default = comportamiento histórico) ──────
    tol_paso:    Optional[float] = None,
):
    """
    Resuelve la dinámica de compradores con Euler EXPLÍCITO de paso fijo
    (dt pequeño constante; CAL-40a corrige el docstring que decía
    "implícito" — H-A-004 del code review 2026-06-10).
    Retorna pi_star (I,).
    Si return_traj=True, retorna (pi_star, t_arr, pi_traj) donde
      t_arr   : (n_points,)  eje de tiempo
      pi_traj : (I, n_points)  trayectoria de precios de compradores reales

    buyer_competition (ADR-0038):
      "aggregate" (default) — término histórico ``etha_s * sum_Pji``.
      "matrix"              — forma matricial de JoinFinal.m:187-200 /
                              Welfarei: ``compe_i = etha_i[i] *
                              Σ_{k≠i} π_k · ΣP_·k`` (consistente con
                              ``buyer_welfare`` de este módulo).
    pi0 (ADR-0038): condición inicial de precios para multi-start.
      None (default) = CI de JoinFinal.m (simétrica simple/(I+1)).
      Acepta (I,) — el jugador virtual conserva su CI histórica — o (I+1,).
    """
    J, I  = P_mat.shape

    # CAL-47: el techo admite escalar o vector por comprador, porque es lo
    # que cada comprador paga a la red. El precio ya está indexado por
    # comprador, de modo que la generalización es directa. El jugador
    # virtual toma el mayor de los techos, que con un escalar es el propio
    # escalar, y así el caso base queda idéntico bit a bit.
    gs_i = np.broadcast_to(np.asarray(pi_gs, dtype=float), (I,))
    pi_gs_all = np.append(gs_i, float(np.max(gs_i)))
    pi_gs_max = float(np.max(gs_i))

    # `simple` reparte el presupuesto de los techos entre los compradores y
    # el jugador virtual; con techos iguales vale exactamente pi_gs * I.
    simple = float(np.sum(gs_i))

    # H-42: tres formas, las tres presentes en las fuentes del modelo base.
    #   "aggregate"  media(etha) * sum_Pji        histórico de esta traducción
    #   "matlab"     (sum_{k!=i} etha_k) * sum_Pji  la línea ACTIVA del MATLAB
    #   "matrix"     etha_i * (matriz @ (pi * sum_Pji))  la línea COMENTADA y
    #                la ecuación (11) arbitrada; la única con precios dentro
    if buyer_competition not in ("aggregate", "matlab", "matrix"):
        raise ValueError(f"buyer_competition={buyer_competition!r}; use "
                         "'aggregate', 'matlab' o 'matrix'")

    # ---- Condiciones iniciales (JoinFinal.m; pi0 opcional ADR-0038) ----
    #
    # CAL-47 / H-37: el arranque de JoinFinal.m reparte un presupuesto de
    # pi_gs*I entre los I compradores y el jugador virtual. Esa forma supone
    # que el piso es despreciable frente al techo, que es el regimen del
    # modelo base (114 frente a 1250) y el del canon (280 frente a 906). En
    # cuanto la banda se estrecha el arranque puede nacer FUERA de ella: con
    # el piso de permuta cae por debajo en el 75,9 % de las horas activas,
    # el clip lo devuelve al borde, y alli pi_hat vale ~0 y la dinamica no
    # arranca nunca.
    #
    # La generalizacion fiel reparte LA BANDA en lugar del techo, y solo se
    # aplica cuando la forma original cae fuera. Asi el caso base, el canon
    # y toda banda ancha quedan IDENTICOS BIT A BIT.
    ci = simple / (I + 1)
    if not (pi_gb < ci < pi_gs_max):
        ci = pi_gb + (pi_gs_max - pi_gb) * I / (I + 1)
    pi_all   = np.full(I + 1, ci)                 # incluye jugador virtual
    if pi0 is not None:
        pi0 = np.asarray(pi0, dtype=float).reshape(-1)
        if pi0.shape[0] == I:
            pi_all[:I] = np.clip(pi0, pi_gb, gs_i)
        elif pi0.shape[0] == I + 1:
            pi_all = np.clip(pi0.copy(), pi_gb, pi_gs_all)
        else:
            raise ValueError(f"pi0 debe ser (I,) o (I+1,); recibido {pi0.shape}")
    matriz   = (np.ones((I, I)) - np.eye(I)) if buyer_competition == "matrix" else None
    # (I,) = suma_{k != i} etha_k, que es lo que da `etha * matriz` en MATLAB
    etha_fila = ((np.ones((I, I)) - np.eye(I)).T @ np.asarray(etha_i, float)
                 if buyer_competition == "matlab" else None)
    etha_s = float(np.mean(etha_i))
    t0 = t_span[0]
    pi_ci = pi_all.copy()          # condición inicial, para poder reintegrar

    def _integra(n_pts: int, guarda_traj: bool = False):
        """Integra el bloque con Euler explícito de paso fijo, n_pts pasos.

        Se aísla en una función para poder reintegrar con el paso partido y
        comprobar que el resultado no depende de él (CAL-47 / H-37).
        """
        pi_all = pi_ci.copy()
        gamma  = 0.1 * np.ones(J)
        y_filt = np.ones(J)
        dt     = (t_span[1] - t_span[0]) / n_pts
        hist   = np.zeros((I, n_pts)) if guarda_traj else None
        t_arr  = np.zeros(n_pts) if guarda_traj else None

        for step in range(n_pts):
            pi_real = pi_all[:I]
            pi_p    = pi_all[I]

            # Suma de potencias recibidas por cada comprador
            sum_Pji = np.array([float(np.sum(P_mat[:, i])) for i in range(I)])

            # pagos = -Pgb * sum_Pji / (pi_i + 1)
            pagos = -pi_gb * sum_Pji / (pi_real + 1.0)

            # trestris = sum_j(y_filt_j * P_ji)  ← señal de costo filtrada
            trestris = np.array([float(np.dot(y_filt, P_mat[:, i]))
                                 for i in range(I)])

            # competencia (A2): forma agregada histórica vs matricial
            # JoinFinal.m (flag opt-in ADR-0038; ver docstring).
            if etha_fila is not None:
                compe = etha_fila * sum_Pji                # "matlab"
            elif matriz is None:
                compe = etha_s * sum_Pji                   # "aggregate"
            else:
                # "matrix": compe_i = etha_i[i] * Σ_{k≠i} π_k · ΣP_·k
                compe = etha_i * (matriz @ (pi_real * sum_Pji))

            # fitness compradores reales
            dwi = pagos - compe + trestris

            # jugador virtual
            dwi_all = np.append(dwi, 1.0 * (simple - pi_p))

            # pi_hat = (Pgs - pi) * (-Pgb + pi)
            pi_hat = (pi_gs_all - pi_all) * (-pi_gb + pi_all)
            pi_hat = np.clip(pi_hat, 1e-12, None)

            # fitness promedio
            sum_ph = float(np.sum(pi_hat))
            F_bar  = (float(np.dot(pi_hat, dwi_all)) / sum_ph
                      if sum_ph > 1e-14 else 0.0)

            # dpi
            d_pi = pi_hat * VEL_WI * (dwi_all - F_bar)
            pi_all = pi_all + dt * d_pi
            pi_all = np.clip(pi_all, pi_gb, pi_gs_all)

            # ingresos y costos por generador
            re = np.array([float(np.dot(pi_all[:I], P_mat[j, :]))
                           for j in range(J)])
            Hj = np.array([a_j[j] * float(np.sum(P_mat[j, :]))**2
                           + b_j[j] * float(np.sum(P_mat[j, :]))
                           for j in range(J)])

            # dinámica gamma
            raw_gamma = VEL_GPC * gamma * (Hj - re) + 1000.0
            gamma = gamma + dt * raw_gamma
            gamma = np.clip(gamma, 0.0, 1e8)

            # filtro
            d_filt = (raw_gamma - y_filt) / tau
            y_filt = y_filt + dt * d_filt

            if guarda_traj:
                hist[:, step] = np.clip(pi_all[:I], pi_gb, gs_i)
                t_arr[step] = t0 + (step + 1) * dt

        return pi_all, t_arr, hist

    if tol_paso is None:
        # Comportamiento histórico, bit a bit: una sola integración.
        pi_all, t_arr, pi_history = _integra(n_points, return_traj)
    else:
        # CAL-47 / H-37. El paso de producción está calibrado para una banda
        # ancha y deja de bastar cuando la banda se estrecha: medido sobre la
        # banda de permuta, partirlo en cuatro más que duplica la tajada del
        # vendedor. Aquí se comprueba, y solo se refina si hace falta.
        #
        # Si la primera comprobación pasa se devuelve la integración GRUESA,
        # de modo que el resultado es idéntico bit a bit al histórico siempre
        # que el paso heredado sea suficiente. El coste es entonces el doble;
        # cuando no basta, se duplica hasta cumplir o agotar el margen.
        umbral = float(tol_paso) * (pi_gs_max - pi_gb)
        n_pts = n_points
        pi_all, t_arr, pi_history = _integra(n_pts, return_traj)
        for _ in range(MAX_REFINOS_PASO):
            n_fino = 2 * n_pts
            pi_fino, t_fino, hist_fino = _integra(n_fino, return_traj)
            if float(np.max(np.abs(pi_fino[:I] - pi_all[:I]))) <= umbral:
                break
            n_pts = n_fino
            pi_all, t_arr, pi_history = pi_fino, t_fino, hist_fino

    pi_star = np.clip(pi_all[:I], pi_gb, gs_i)

    if return_traj:
        return pi_star, t_arr, pi_history

    return pi_star


def buyer_welfare(pi_i, P_mat, G_klim_i, lam_i, theta_i, etha_i) -> float:
    """
    W_i total (fiel a Welfarei de Bienestar6p.py):
    Wi = lam*Gi - theta*Gi^2 + sum_j(P_ji)/log(|pi_i|+1) - etha*compe

    H-39 / H-40: las fuentes del modelo base NO coinciden en el termino de
    competencia, y esta traduccion sigue a la VERSION ARBITRADA.

        IEEE Latin America Transactions 23(8), ago-2025, ec. (11):
                               -beta_i * sum_{k != i} pi_k * sum_j P_jk
        documento extenso, ec. (14)   la misma forma
        JoinFinal.m:188        la misma forma, en la linea comentada
        Bienestar6p.py         sum_{k != i} pi_k * sum_j P_ji

    Las tres primeras multiplican por la energia del comprador AJENO; la
    cuarta, por la PROPIA. Coinciden solo cuando todos compran lo mismo, y
    con datos reales divergen: medido, hasta 1.755,95 unidades sobre un
    valor del orden de 2.500.

    El termino del pago sigue tambien a la version arbitrada, que lo escribe
    como `sum_j P_ji / ln(pi_i + 1)`, division sin factor del piso. El
    documento extenso introduce ahi un factor `pi_gb` que ni el articulo
    publicado ni el guion contemplan.

    Compuerta en `tests/gate_c138_bienestar_comprador.py`.

    La eleccion no toca la dinamica, porque esta funcion solo informa: ni el
    bloque de precios ni el de reparto la llaman.
    """
    I = len(pi_i)
    J = P_mat.shape[0]
    matriz = np.ones((I, I)) - np.eye(I)
    compe = [sum(matriz[i][k] * pi_i[k] * float(np.sum(P_mat[:, k]))
                 for k in range(I))
             for i in range(I)]
    Wi = [
        lam_i[i] * G_klim_i[i] - theta_i[i] * G_klim_i[i]**2
        + float(np.sum(P_mat[:, i])) / (np.log(abs(pi_i[i]) + 1) + 1e-12)
        - compe[i] * etha_i[i]
        for i in range(I)
    ]
    return sum(Wi)
