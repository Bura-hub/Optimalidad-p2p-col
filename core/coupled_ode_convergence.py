"""
coupled_ode_convergence.py
---------------------------
Solver acoplado tipo ``JoinFinal.m:join()`` que integra simultaneamente la
dinamica de vendedores (P_ji + multiplicadores Lagrangianos λ/β filtrados)
y compradores (π_i + filtros γ) como UN solo sistema de EDOs continuo
sobre [0, 0.01] s, usando ``scipy.integrate.solve_ivp(method='LSODA')``
(analogo a ``ode15s`` de MATLAB que usa Chacon en JoinFinal.m linea 139).

Diseñado UNICAMENTE para generar ``fig_paper_convergence`` — la metodologia
de produccion (``EMSP2P.run()`` + ``run_convergence``) usa el solver
alternante (sellers RD → buyers RD → repeat) por eficiencia. Ambos
convergen al mismo equilibrio Nash; verificable con ``equilibrium_match``.

Factores de escala (matching JoinFinal.m:160-161)
-------------------------------------------------
* En ``_rhs()`` se aplican los factores ``0.08`` al bloque de buyers
  (d_pi_all, d_gamma, d_y_filt) y ``10`` al bloque de sellers
  (dP, Glam, Gbet, d_lam_filt, d_bet_filt). Esto preserva la
  separacion temporal Stackelberg del modelo base: sellers ~125x mas
  rapidos que buyers, lo que hace que en t_span=[0, 0.01]s ambos
  alcancen el equilibrio dentro de la ventana visible y la trayectoria
  P_ji(t) muestre el transitorio (Chacon Fig 3a). Sin estos factores
  los buyers convergen en ~1ms pero los sellers apenas se mueven.
* Los factores no afectan el equilibrio (zeros del RHS son invariantes
  bajo escalado positivo); solo afectan la velocidad del transitorio.
* La inicializacion ``pi_all_0 = pi_gs*I/(I+1)`` matchea JoinFinal.m
  linea 103.

Trazabilidad: Plan 2026-05-04 — alineacion fig_paper_convergence con
JoinFinal.m. Referencias:
  - JoinFinal.m:139 (single ode15s call)
  - JoinFinal.m:146-166 (join function — RHS acoplado)
  - core/replicator_sellers.py:_sellers_ode
  - core/replicator_buyers.py:solve_buyers (Euler loop body)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from core.replicator_sellers import VEL_GRAD, BGRANDE, VEL_RD
from core.replicator_buyers import VEL_WI, VEL_GPC, PGB, PGS
# D50: el presupuesto de precios del reposo. El arranque `nivel="sigma"` lo
# toma del nucleo en vez de repetir la formula. El nucleo es puro y no importa
# nada del motor, de modo que no hay importacion circular.
from core.reposo_mercado import presupuesto_precios


class _LadoDerechoNoFinito(Exception):
    """D41 (H-84): el lado derecho del acoplado recibio o produjo un valor no
    finito, y la integracion se corta en esa misma evaluacion.

    La lanza `_rhs` y la atrapa SOLO `solve_coupled_for_hour`, alrededor de
    `solve_ivp`, que devuelve entonces una trayectoria con `success=False`.
    Nunca sale de este modulo: si escapara, llegaria al `except` de C-190 en
    el motor, contaria como excepcion y detendria la matriz (D38), cuando lo
    que ocurre es un integrador sin exito, que tiene su propio camino (D37).

    Por que cortar. Con scipy 1.17 LSODA no se detiene al aparecer un NaN: en
    el servidor la hora 4184 con la generacion por siete siguio unos catorce
    millones de evaluaciones en 15 (min) sin avanzar en el tiempo, y en la
    maquina de trabajo una perturbacion de un ulp termino con «exito» y el
    estado entero en NaN (H-84).
    """

    def __init__(self, t: float, evaluacion: int, donde: str):
        self.t = float(t)
        self.evaluacion = int(evaluacion)
        self.donde = donde
        super().__init__(f"lado derecho no finito en t={self.t:.6e} "
                         f"({donde} de la evaluacion {self.evaluacion})")


@dataclass
class CoupledTrajectory:
    """Resultado del solver coupled-ODE para una hora.

    Atributos
    ---------
    t        : (n_t,) tiempo en segundos sobre [t_span[0], t_span[1]]
    pi_t     : (I, n_t) trayectoria precios reales (sin virtual player)
    P_t      : (J, I, n_t) trayectoria potencias por par (j, i)
    Wj_t     : (n_t,) welfare agregado de vendedores W_j(t) en cada t
    Wi_t     : (n_t,) welfare agregado de compradores W_i(t) en cada t
    W_t      : (n_t,) welfare total = Wj_t + Wi_t
    pi_star  : (I,) precios en steady-state (t = t_span[1])
    P_star   : (J, I) potencias en steady-state
    success  : bool, indica si el ODE termino sin error
    message  : descripcion del status del solver
    """
    t:        np.ndarray
    pi_t:     np.ndarray
    P_t:      np.ndarray
    Wj_t:     np.ndarray
    Wi_t:     np.ndarray
    W_t:      np.ndarray
    pi_star:  np.ndarray
    P_star:   np.ndarray
    success:  bool = True
    message:  str  = ""

    # Los multiplicadores. Se integran desde siempre como parte del estado y
    # se descartaban al salir. Son los que dicen QUE RESTRICCION esta
    # mordiendo, de modo que sin ellos se ve el precio detenerse sin poder
    # decir por que se detiene ahi. Opt-in, con
    # `devuelve_multiplicadores=True`, para que el comportamiento por defecto
    # quede identico bit a bit.
    #   lam_t : (J, n_t) capacidad del vendedor, sum_i P_ji <= G_net_j
    #   bet_t : (I, n_t) necesidad del comprador, sum_j P_ji <= D_net_i
    #   *_filt_t : sus versiones filtradas, que son las que entran en la
    #              aptitud del vendedor
    lam_t:      Optional[np.ndarray] = None
    bet_t:      Optional[np.ndarray] = None
    lam_filt_t: Optional[np.ndarray] = None
    bet_filt_t: Optional[np.ndarray] = None

    # D36: cuanto trabajo le costo la hora al integrador, tal como lo cuenta
    # `solve_ivp` (`sol.nfev`: evaluaciones del lado derecho, incluidas las
    # de la jacobiana por diferencias; `sol.njev`: jacobianas). Es lo que el
    # presupuesto de la parada por estacionario suma, porque no depende de
    # la maquina como los segundos. Cero en el caso degenerado, que no
    # integra nada. Solo se anade: el resto de la salida no cambia.
    # D41: en la trayectoria cortada por un lado derecho no finito, `nfev`
    # son las evaluaciones hechas hasta el corte, esa incluida, y `njev` es
    # cero, porque `solve_ivp` no llega a devolver su cuenta.
    nfev:       int = 0
    njev:       int = 0


# H-85 / D45: las reglas con que arranca la oferta P del acoplado. La primera
# es el defecto y es la de siempre.
ARRANQUES = ("iguales", "factible")


def _arranque_P0(G_net_j, D_net_i, regla: str = "iguales") -> np.ndarray:
    """La oferta P (J, I) con que arranca el acoplado (H-85, D45).

    "iguales" es el arranque de siempre, identico al bit: si la oferta cubre
    la demanda (sum_G >= sum_D), cada comprador recibe su deficit repartido a
    partes iguales entre los J vendedores; si no, cada vendedor reparte su
    excedente a partes iguales entre los I compradores. Asi arranca
    `JoinFinal.m`, y un comprador de deficit pequeno puede arrancar con
    varias veces lo que necesita: en la hora 753 de E4 (generacion por siete)
    el comprador 1, con un deficit de 1,90 (kWh), recibe 10,45 al empezar; su
    multiplicador de demanda crece en proporcion a si mismo y desborda el
    mayor numero de coma flotante hacia t = 7,2e-6, antes de que la
    correccion alcance a actuar (H-85).

    "factible" reparte en proporcion al lado corto:
      - si sum_G >= sum_D, P0 = outer(G_net_j / sum_G, D_net_i): la columna
        de cada comprador suma exactamente su deficit, y la fila de cada
        vendedor suma G_net_j · sum_D / sum_G <= G_net_j;
      - si no, P0 = outer(G_net_j, D_net_i / sum_D): la fila de cada vendedor
        suma exactamente su excedente, y la columna de cada comprador suma
        D_net_i · sum_G / sum_D <= D_net_i.
    Es decir, ningun comprador arranca con mas de lo que necesita y ningun
    vendedor ofrece mas de lo que tiene: el arranque cumple las dos
    restricciones de capacidad del juego, y los multiplicadores no nacen
    empujando.

    Las dos terminan con el mismo recorte a 1e-10 de siempre (el piso de P
    del lado derecho, D40, es el mismo).

    Aviso de fidelidad: `JoinFinal.m` reparte a partes iguales; el arranque
    factible es una extension de esta traduccion, opcional y apagada por
    defecto hasta medirla (D45).
    """
    G_net_j = np.asarray(G_net_j, dtype=float)
    D_net_i = np.asarray(D_net_i, dtype=float)
    J = len(G_net_j)
    I = len(D_net_i)
    sum_G = float(np.sum(G_net_j))
    sum_D = float(np.sum(D_net_i))
    if regla == "iguales":
        if sum_G >= sum_D:
            P0 = np.tile(D_net_i / J, (J, 1))
        else:
            P0 = np.tile(G_net_j / I, (I, 1)).T
    elif regla == "factible":
        # El reparto divide por el lado largo o por el corto; con una suma
        # que no es positiva no hay mercado, y el llamador ya lo trata como
        # caso degenerado antes de arrancar. Aqui se falla en voz alta en vez
        # de devolver un NaN.
        if not (sum_G > 0.0 and sum_D > 0.0):
            raise ValueError(f"arranque factible sin oferta o sin demanda: "
                             f"sum_G={sum_G!r}, sum_D={sum_D!r}")
        if sum_G >= sum_D:
            P0 = np.outer(G_net_j / sum_G, D_net_i)
        else:
            P0 = np.outer(G_net_j, D_net_i / sum_D)
    else:
        raise ValueError(f"arranque={regla!r}; use 'iguales' (el de siempre, "
                         "como JoinFinal.m) o 'factible' (H-85, D45)")
    return np.clip(P0, 1e-10, None)


# D49 / D50: las reglas con que arrancan los precios del acoplado. La primera
# es el defecto y es la de siempre (C-136, H-32, H-45).
NIVELES = ("c136", "sigma")

# D49: las claves de `estado_inicial`, las dos obligatorias. Los
# multiplicadores y los filtros arrancan siempre en su valor de siempre. Eso
# basta en las horas NO rigidas: arrancando desde el reposo, el reparto sale
# quieto o casi (max |dP/dt| = 0 en la hora 853 y 3,0e-4 (kWh por unidad de
# tiempo) en la 2120) y el transitorio medido por
# `tests/gate_reposo_cero_dinamica.py` no pasa de 2,2e-6 (kWh) en la 853 ni de
# 3e-10 en la 2120. En las rigidas no: max |dP/dt| = 86,3 en la 874 (topados)
# y 32,7 en la 4766 (compradores cortos), porque sus multiplicadores de demanda
# arrancan lejos de su valor, y no se ha medido si darlos cambiaria el
# resultado. Las cuatro cifras son de la revision de la tarea 3; las fija
# `tests/test_dinamica_regularizada.py`.
CLAVES_ESTADO = ("P", "pi")


def valida_opciones_dinamica(mu_entropia, nivel,
                             nombre_nivel: str = "nivel") -> None:
    """D49 / D50: las dos opciones de la dinamica regularizada, en voz alta.

    `mu_entropia` es un numero real finito y no negativo (COP/kWh); 0 apaga el
    termino. `nivel` es uno de NIVELES. La usan `solve_coupled_for_hour` y,
    por `core/ems_p2p.py`, `SolverParams` y la tupla del trabajador, que la
    llaman con `nombre_nivel="nivel_acoplado"` para que el mensaje nombre su
    campo.
    """
    if (isinstance(mu_entropia, bool)
            or not isinstance(mu_entropia, (int, float, np.integer,
                                            np.floating))
            or not np.isfinite(mu_entropia) or float(mu_entropia) < 0.0):
        raise ValueError(f"mu_entropia={mu_entropia!r}; tiene que ser un "
                         f"numero finito y no negativo (COP/kWh); 0 apaga la "
                         f"exploracion entropica (D49)")
    if nivel not in NIVELES:
        raise ValueError(f"{nombre_nivel}={nivel!r}; use 'c136' (el arranque "
                         f"de precios de siempre) o 'sigma' (el presupuesto "
                         f"del reposo, D50)")


def _precios_sigma(gs_i: np.ndarray, pi_gb: float) -> np.ndarray:
    """D50: los precios reales con que arranca `nivel="sigma"`.

    Cada comprador abre en piso + sigma_I·(techo_i - piso), con
    sigma_I = (I-1)/I, y el jugador virtual (fuera de esta funcion) en su
    techo, donde la barrera lo congela. La suma de estos precios es el
    presupuesto `presupuesto_precios(techo, piso, modo="sigma")` del nucleo, y
    la dinamica la conserva (H-87 sec. 6, H-90 punto 2). Cada precio sale del
    propio nucleo, aplicado a ese comprador solo con la sigma de la hora, para
    no duplicar la formula. Un techo bajo el piso lo rechaza el nucleo
    (ValueError): esta regla no tiene el interruptor de C-136.
    """
    I = gs_i.size
    sigma = (I - 1) / I
    pi0 = np.array([presupuesto_precios(gs_i[i:i + 1], pi_gb, modo="sigma",
                                        sigma=sigma) for i in range(I)])
    S = presupuesto_precios(gs_i, pi_gb, modo="sigma")
    if abs(float(np.sum(pi0)) - S) > 1e-9 * max(1.0, abs(S)):
        raise AssertionError(f"el arranque sigma suma {np.sum(pi0)!r} y el "
                             f"presupuesto del nucleo es {S!r}")
    return pi0


def _valida_estado_inicial(estado, J: int, I: int, gs_i: np.ndarray,
                           pi_gb: float) -> dict:
    """D49: el estado desde el que arranca la integracion, comprobado.

    Devuelve un diccionario con copias float64 de las dos claves, las dos
    obligatorias: "P", forma (J, I), finita y no negativa (kWh), y "pi",
    forma (I,), finita y dentro de [pi_gb, techo_i] (COP/kWh). Una clave que
    falta o sobra, una forma que no cuadra o un valor fuera de rango se
    rechazan con ValueError.
    """
    if not isinstance(estado, dict):
        raise ValueError(f"estado_inicial tiene que ser un diccionario con "
                         f"las claves {CLAVES_ESTADO}; llego {type(estado)}")
    if set(estado) != set(CLAVES_ESTADO):
        raise ValueError(f"estado_inicial tiene las claves "
                         f"{sorted(estado)}; tiene que tener exactamente "
                         f"{CLAVES_ESTADO}")
    formas = dict(P=(J, I), pi=(I,))
    salida = {}
    for clave in CLAVES_ESTADO:
        try:
            arr = np.array(estado[clave], dtype=float, copy=True)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"estado_inicial[{clave!r}] no es numerico: "
                             f"{exc}") from None
        if arr.shape != formas[clave]:
            raise ValueError(f"estado_inicial[{clave!r}] tiene forma "
                             f"{arr.shape}; se esperaba {formas[clave]}")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"estado_inicial[{clave!r}] tiene valores no "
                             f"finitos")
        salida[clave] = arr
    if np.any(salida["P"] < 0.0):
        raise ValueError("estado_inicial['P'] tiene energias negativas")
    pi = salida["pi"]
    if np.any(pi < pi_gb) or np.any(pi > gs_i):
        raise ValueError(f"estado_inicial['pi'] = {pi} fuera de la banda "
                         f"[{pi_gb}, techo] con techo {gs_i}")
    return salida


def solve_coupled_for_hour(
    G_net_j:     np.ndarray,
    D_net_i:     np.ndarray,
    a_j:         np.ndarray,
    b_j:         np.ndarray,
    lam_j:       np.ndarray,
    theta_j:     np.ndarray,
    G_klim_i:    np.ndarray,
    lam_i:       np.ndarray,
    theta_i:     np.ndarray,
    etha_i:      np.ndarray,
    pi_gs:       object = PGS,   # escalar o (I,) por comprador — H-45
    pi_gb:       float = PGB,
    tau_sellers: float = 0.001,
    tau_buyers:  float = 0.01,
    t_span:      Tuple[float, float] = (0.0, 0.01),
    n_points:    int   = 500,
    method:      str   = "LSODA",
    rtol:        float = 1e-6,
    # H-51: la tolerancia absoluta del MODELO BASE, que es 1e-6 y no 1e-9.
    #
    # El fichero original fija `odeset('RelTol',1e-6,'AbsTol',1e-6)`. Esta
    # traduccion heredo 1e-6 en la relativa y escribio 1e-9 en la absoluta,
    # mil veces mas estricta, sin que nadie lo decidiera.
    #
    # La absoluta manda cuando las variables son pequenas, y el estado lleva
    # cantidades recortadas a 1e-10: justo el rango donde 1e-9 obliga al
    # integrador a achicar el paso sin necesidad. Medido sobre la hora 4741
    # de la frontera principal: con 1e-9 no resuelve en cuarenta minutos de
    # procesador; con 1e-6 resuelve en 2,2 segundos.
    #
    # No es una aceleracion general y conviene no venderla como tal: en la
    # hora corriente las dos tolerancias tardan lo mismo. Lo que hace es
    # RESCATAR las horas que se atascaban.
    #
    # Y no cambia la respuesta. Sobre ocho horas al azar resueltas con las
    # dos, el volumen coincide dentro de 1,4e-13 (kWh) y el precio dentro de
    # 6,6e-3 (COP/kWh), sobre precios del orden de 700.
    atol:        float = 1e-6,
    buyer_competition: str = "aggregate",
    devuelve_multiplicadores: bool = False,
    peso_virtual: str = "barrera",
    # H-85 / D45: la regla del arranque de la oferta P (`_arranque_P0`).
    # "iguales" (defecto) es el de siempre, identico al bit.
    arranque:    str = "iguales",
    # D49: exploracion entropica del replicador del vendedor (COP/kWh). 0.0
    # (defecto) la apaga y el lado derecho es el de siempre, al bit.
    mu_entropia: float = 0.0,
    # D50: como arrancan los precios. "c136" (defecto) es el de siempre, al
    # bit; "sigma" arranca en el presupuesto del reposo.
    nivel:       str = "c136",
    # D49: arrancar desde un estado dado (`_valida_estado_inicial`). None
    # (defecto) es el arranque de siempre, al bit.
    estado_inicial: Optional[dict] = None,
) -> CoupledTrajectory:
    """Integra el sistema acoplado [buyer_state ; seller_state] en una sola
    llamada ``solve_ivp``, replicando estructuralmente JoinFinal.m:join().

    Parametros
    ----------
    G_net_j  : (J,) excedente neto del seller j (kW)
    D_net_i  : (I,) deficit neto del buyer i (kW)
    a_j, b_j : (J,) coeficientes costo cuadratico H_j = a_j*P^2 + b_j*P
    lam_j    : (J,) preferencia self-consumption seller (eq 7 Chacon)
    theta_j  : (J,) curvatura utilidad seller (eq 7)
    G_klim_i : (I,) generacion limite buyer (eq 14, U_i)
    lam_i    : (I,) preferencia self-consumption buyer
    theta_i  : (I,) curvatura utilidad buyer
    etha_i   : (I,) factor competencia (β_i en eq 14)
    pi_gs    : COP/kWh, precio venta a la red (limite superior π). Admite
               escalar o vector (I,) con el techo de cada comprador (H-45).
               Con escalar el resultado es identico bit a bit al historico.
    peso_virtual : con que peso entra el jugador virtual en la aptitud media
               (H-46). "barrera" es el defecto de esta traduccion y aplica el
               producto de barrera a las I+1 estrategias; "precio" reproduce
               el fichero original, donde el jugador virtual entra con su
               propio precio. Opt-in, para medir sin mover el defecto.
    arranque : con que oferta P arranca la integracion (H-85, D45).
               "iguales" (defecto) reparte a partes iguales, como
               JoinFinal.m, identico al bit al historico; "factible" reparte
               en proporcion al lado corto, de modo que ningun comprador
               arranca con mas de su deficit ni ningun vendedor con mas de su
               excedente. Ver `_arranque_P0`.
    mu_entropia : D49, exploracion entropica del replicador del vendedor
               (COP/kWh). Con mu > 0 el bloque de P recibe
               -mu·P·(ln P - <ln P>), con <ln P> = sum P ln P / sum P, que
               conserva la suma de P y hace que la dinamica llegue al reposo
               del juego regularizado (H-90 punto 5). 0.0 (defecto) lo apaga:
               lado derecho identico al bit. Apartamiento declarado de
               JoinFinal.m, para validar el reposo en forma cerrada y dibujar
               la convergencia; no es la via de produccion (D48).
    nivel    : D50, como arrancan los precios. "c136" (defecto) es el
               arranque de siempre, identico al bit. "sigma" arranca cada
               comprador en piso + (I-1)/I·(techo_i - piso) y el jugador
               virtual en su techo, de modo que la suma de los precios reales
               es el presupuesto `presupuesto_precios(modo="sigma")` del
               nucleo del reposo. Sin el interruptor de C-136: un techo bajo
               el piso lanza ValueError. Solo con `peso_virtual="barrera"`:
               con "precio" la suma no se conserva (H-46, H-90) y se rechaza
               con ValueError.
    estado_inicial : D49, arranca la integracion desde un estado dado: un
               diccionario con la oferta por pareja "P" (J, I) (kWh) y los
               precios reales "pi" (I,) (COP/kWh), las dos obligatorias (ver
               `_valida_estado_inicial`). El jugador virtual arranca segun
               `nivel`, y los multiplicadores y filtros como siempre. P se
               respeta tal cual, sin el recorte a 1e-10 de los arranques (el
               lado derecho ya la lee con ese piso, D40). No se combina con
               `arranque="factible"` (ValueError). None (defecto): identico
               al bit.
    pi_gb    : COP/kWh, precio compra a la red (limite inferior π)
    tau_sellers : tau filtro Lagrange (matching JoinFinal.m linea 132)
    tau_buyers  : tau3 filtro buyer (matching JoinFinal.m linea 133)
    t_span      : intervalo integracion (matching JoinFinal.m linea 128)
    n_points    : puntos t_eval (matching JoinFinal.m linea 129 = 500)
    method      : solver scipy (LSODA = stiff-aware ~ ode15s)

    Estado X (concatenado, dim total = J*I + 4*J + 3*I + 1)
    --------------------------------------------------------
    [0           : I+1                ]  pi_all (I real prices + virtual player p)
    [I+1         : I+1+J              ]  gamma  (auxiliar buyer)
    [I+1+J       : I+1+2J             ]  y_filt (filtro buyer en gamma)
    [I+1+2J      : I+1+2J+J*I         ]  P_ji (potencias, flat row-major)
    [I+1+2J+J*I  : I+1+3J+J*I         ]  lam_ub (Lagrange seller, capacity)
    [I+1+3J+J*I  : I+1+3J+J*I+I       ]  bet_ub (Lagrange seller, demand)
    [I+1+3J+J*I+I: I+1+4J+J*I+I       ]  lam_filt (filtro lam_ub)
    [I+1+4J+J*I+I: I+1+4J+J*I+2I      ]  bet_filt (filtro bet_ub)
    """
    G_net_j  = np.asarray(G_net_j,  dtype=float)
    D_net_i  = np.asarray(D_net_i,  dtype=float)
    a_j      = np.asarray(a_j,      dtype=float)
    b_j      = np.asarray(b_j,      dtype=float)
    lam_j    = np.asarray(lam_j,    dtype=float)
    theta_j  = np.asarray(theta_j,  dtype=float)
    G_klim_i = np.asarray(G_klim_i, dtype=float)
    lam_i    = np.asarray(lam_i,    dtype=float)
    theta_i  = np.asarray(theta_i,  dtype=float)
    etha_i   = np.asarray(etha_i,   dtype=float)

    # H-85 / D45: una regla desconocida se rechaza antes de nada, tambien en
    # la hora sin mercado, que vuelve antes de arrancar.
    if arranque not in ARRANQUES:
        raise ValueError(f"arranque={arranque!r}; use 'iguales' (el de "
                         "siempre, como JoinFinal.m) o 'factible' (H-85, D45)")
    # D49 / D50: lo mismo con las opciones de la dinamica regularizada y con
    # el estado inicial, tambien en la hora sin mercado.
    valida_opciones_dinamica(mu_entropia, nivel)
    mu = float(mu_entropia)
    if nivel == "sigma" and peso_virtual == "precio":
        # Menor 4 de la revision de la tarea 3: con el peso de precio el
        # jugador virtual no se congela en su techo, absorbe el presupuesto y
        # la suma de los precios reales deja de conservarse, de modo que el
        # nivel no seria el presupuesto del nucleo que `sigma` promete.
        raise ValueError("nivel='sigma' no se combina con "
                         "peso_virtual='precio': sin la barrera el jugador "
                         "virtual no se congela en su techo, la suma de los "
                         "precios reales no se conserva (H-46; H-90, punto "
                         "2) y el nivel deja de ser el presupuesto sigma del "
                         "nucleo del reposo")

    J = len(G_net_j)
    I = len(D_net_i)
    sum_G = float(np.sum(G_net_j))
    sum_D = float(np.sum(D_net_i))
    simplex = min(sum_G, sum_D)

    estado = None
    if estado_inicial is not None:
        if arranque == "factible":
            raise ValueError("estado_inicial ya fija la oferta P con que "
                             "arranca la integracion; no se combina con "
                             "arranque='factible' (D49)")
        estado = _valida_estado_inicial(
            estado_inicial, J, I,
            np.broadcast_to(np.asarray(pi_gs, dtype=float), (I,)),
            float(pi_gb))

    # Caso degenerado: sin mercado P2P
    if simplex < 1e-10 or J == 0 or I == 0:
        t = np.linspace(t_span[0], t_span[1], n_points)
        return CoupledTrajectory(
            t=t,
            pi_t=np.full((I, n_points), pi_gb),
            P_t=np.zeros((J, I, n_points)),
            Wj_t=np.zeros(n_points),
            Wi_t=np.zeros(n_points),
            W_t=np.zeros(n_points),
            pi_star=np.full(I, pi_gb),
            P_star=np.zeros((J, I)),
            success=True,
            message="No P2P market (simplex < 1e-10)",
        )

    # ── El techo, por comprador ───────────────────────────────
    # H-45: el techo es lo que CADA comprador le paga a la red, y en esta
    # comunidad no es uno solo porque hay dos comercializadores. Hasta aqui
    # el solucionador recibia un ESCALAR, el mayor de los techos de la hora,
    # y el techo propio se aplicaba DESPUES como recorte. El resultado
    # medido el 2026-09-07 es que los compradores del techo bajo salian
    # justo encima de el, y como su ahorro es su techo menos el precio, les
    # quedaba exactamente cero.
    #
    # Se generaliza igual que en core/replicator_buyers.py con CAL-47: el
    # techo admite escalar o vector de compradores. El jugador virtual toma
    # el mayor, que con un escalar es el propio escalar, de modo que el caso
    # base y el canon quedan IDENTICOS BIT A BIT.
    #
    # Aviso de fidelidad: el modelo base no contempla esto. La ecuacion (5)
    # del articulo publicado fija pi_gb <= pi_i <= pi_gs con las dos cotas
    # escalares y globales, y el codigo original las escribe a mano. El
    # techo por comprador es una extension de esta tesis.
    if peso_virtual not in ("barrera", "precio"):
        raise ValueError(f"peso_virtual={peso_virtual!r}; use 'barrera' "
                         "(el defecto de esta traduccion) o 'precio' (H-46, "
                         "la forma del fichero original)")

    gs_i      = np.broadcast_to(np.asarray(pi_gs, dtype=float), (I,)).copy()
    pi_gs_all = np.append(gs_i, float(np.max(gs_i)))
    pi_gs_max = float(np.max(gs_i))

    # ── Indices del estado ────────────────────────────────────
    n_pi_all = I + 1
    idx0_gamma    = n_pi_all
    idx0_yfilt    = idx0_gamma + J
    idx0_P        = idx0_yfilt + J
    idx0_lam      = idx0_P + J*I
    idx0_bet      = idx0_lam + J
    idx0_lamfilt  = idx0_bet + I
    idx0_betfilt  = idx0_lamfilt + J
    n_total       = idx0_betfilt + I

    # ── Condiciones iniciales (matching JoinFinal.m) ──────────
    # `simple` reparte el presupuesto de los techos entre los compradores y
    # el jugador virtual; con techos iguales vale exactamente pi_gs * I.
    simple = float(np.sum(gs_i))
    # CAL-47 / H-32: el arranque de JoinFinal.m reparte un presupuesto de
    # pi_gs*I entre los compradores y el jugador virtual. Esa forma supone
    # que el piso es despreciable frente al techo, que es el regimen del
    # modelo base (114 frente a 1250). Con las cotas medidas la banda se
    # estrecha y el arranque puede nacer POR DEBAJO del piso: el clip lo
    # devuelve al borde, alli el peso (pi_gs-pi)(pi-pi_gb) vale cero y la
    # dinamica no arranca nunca. Medido en la hora 2342 de la frontera
    # principal: banda [640,75 · 703,63] y arranque en 527,72, con lo que el
    # precio se quedaba clavado y el recorrido era exactamente cero.
    #
    # La generalizacion fiel reparte LA BANDA en lugar del techo, y solo se
    # aplica cuando la forma original cae fuera. Con banda ancha el
    # resultado es identico bit a bit. Misma correccion que en
    # core/replicator_buyers.py.
    ci = simple / n_pi_all
    # H-45: con techos distintos el arranque tiene que caer dentro de la
    # banda de CADA comprador, no dentro de la del techo mayor. Si nace por
    # ENCIMA de su propio techo, el peso de barrera vale cero justo ahi y su
    # precio no se mueve nunca: es la misma patologia de H-32 por el otro
    # extremo. Con techos iguales las dos formas coinciden y el arranque es
    # el escalar de siempre, bit a bit.
    if nivel == "sigma":
        # D50: el presupuesto del reposo. Los compradores en
        # piso + (I-1)/I·(techo_i - piso), del nucleo, y el virtual en su
        # techo, donde la barrera lo congela: la suma de los precios reales es
        # el presupuesto sigma y la dinamica la conserva.
        pi_all_0 = np.append(_precios_sigma(gs_i, float(pi_gb)), pi_gs_max)
    else:
        ci_i = np.where((pi_gb < ci) & (ci < gs_i), ci,
                        pi_gb + (gs_i - pi_gb) * I / n_pi_all)
        ci_v = (ci if pi_gb < ci < pi_gs_max
                else pi_gb + (pi_gs_max - pi_gb) * I / n_pi_all)
        pi_all_0 = np.append(ci_i, ci_v)
    gamma_0  = 0.1 * np.ones(J)
    y_filt_0 = np.ones(J)

    # H-85 / D45: la oferta inicial. Con "iguales" es exactamente el reparto
    # de JoinFinal.m de siempre, al bit; con "factible", el reparto en
    # proporcion al lado corto: las sumas por columna no pasan del deficit
    # de cada comprador y las sumas por fila no pasan del excedente de cada
    # vendedor. Las dos llevan el recorte a 1e-10 de siempre.
    P0 = _arranque_P0(G_net_j, D_net_i, arranque)

    lam_ub_0   = 0.1 * np.ones(J)
    bet_ub_0   = 0.1 * np.ones(I)
    lam_filt_0 = np.zeros(J)
    bet_filt_0 = np.zeros(I)

    if estado is not None:
        # D49: la oferta y los precios reales del estado dado; el jugador
        # virtual segun `nivel`, y los multiplicadores y filtros como siempre.
        pi_all_0 = np.append(estado["pi"], pi_all_0[I])
        P0 = estado["P"]

    X0 = np.concatenate([
        pi_all_0, gamma_0, y_filt_0,
        P0.ravel(), lam_ub_0, bet_ub_0, lam_filt_0, bet_filt_0,
    ])
    assert X0.shape[0] == n_total, "state-vector dim mismatch"

    # H-42: el termino de competencia admite tres formas, y las tres estan
    # en las fuentes del modelo base.
    #
    #   "aggregate"  etha_s * sumP_i             historico de esta traduccion
    #   "matlab"     (sum_{k!=i} etha_k) * sumP_i   la LINEA ACTIVA de
    #                JoinFinal.m:189, `compe = etha * matriz` con etha
    #                vector fila, es decir un producto vector-matriz. Con
    #                etha uniforme vale etha*(I-1)*sumP_i, de modo que la
    #                forma historica se queda corta por el factor (I-1).
    #   "matrix"     etha_i * (matriz @ (pi_real * sumP_i))   la linea
    #                COMENTADA de JoinFinal.m:188 y la ecuacion (11) de la
    #                version arbitrada, la unica que hace que un comprador
    #                responda al PRECIO de los demas.
    #
    # El defecto es el historico, para no mover ninguna cifra publicada.
    if buyer_competition not in ("aggregate", "matlab", "matrix"):
        raise ValueError(f"buyer_competition={buyer_competition!r}; use "
                         "'aggregate', 'matlab' o 'matrix'")
    etha_s = float(np.mean(etha_i))
    matriz = np.ones((I, I)) - np.eye(I)
    etha_fila = matriz.T @ etha_i          # (I,) = sum_{k != i} etha_k

    # D41: las evaluaciones del lado derecho en esta resolucion. Son el `nfev`
    # de la trayectoria cortada, porque la cuenta de `solve_ivp` no llega.
    evaluaciones = [0]

    def _rhs(t: float, X: np.ndarray) -> np.ndarray:
        evaluaciones[0] += 1
        # D41: un estado no finito no se evalua; la integracion se corta aqui.
        if not np.all(np.isfinite(X)):
            raise _LadoDerechoNoFinito(t, evaluaciones[0], "estado")
        pi_all   = X[:n_pi_all]
        gamma    = X[idx0_gamma:idx0_yfilt]
        y_filt   = X[idx0_yfilt:idx0_P]
        # H-84 / D40: P se LEE con un piso de 1e-10; el estado integrado no
        # se toca. La dinamica de replicador (dP = P*(F - F_bar)) conserva
        # P >= 0 solo en aritmetica exacta. Con un comprador de deficit muy
        # pequeno frente a lo que le asigna el arranque, su multiplicador de
        # demanda (VEL_GRAD = 1e6) empuja su columna de P a cero con una
        # fuerza del orden de 1e7, el integrador cruza el cero y, con P
        # negativa, el replicador se alimenta a si mismo hasta desbordar: la
        # hora 4184 con la generacion por siete explotaba o no segun el
        # ultimo decimal de la entrada. La P negativa que sobrevivia la
        # borraba despues el recorte a cero de la salida, e inflaba lo que
        # recibe ese comprador (0,2319 frente a un deficit de 0,1218 (kWh)).
        # Es el mismo piso de 1e-10 del arranque (`P0`, mas arriba). No es
        # cero a proposito: con piso cero la columna seria absorbente (P = 0
        # da dP = 0 para siempre) y ese comprador no podria volver a recibir.
        # Aviso de fidelidad: JoinFinal.m (join, lineas 146 a 166) no lleva
        # este piso; es una salvaguarda de esta traduccion.
        P        = np.maximum(X[idx0_P:idx0_lam].reshape(J, I), 1e-10)
        lam_ub   = X[idx0_lam:idx0_bet]
        bet_ub   = X[idx0_bet:idx0_lamfilt]
        lam_filt = X[idx0_lamfilt:idx0_betfilt]
        bet_filt = X[idx0_betfilt:]

        pi_real = pi_all[:I]
        pi_p    = pi_all[I]

        sumP_i = P.sum(axis=0)   # (I,) suma sobre j
        sumP_j = P.sum(axis=1)   # (J,) suma sobre i

        # ── BUYER DYNAMICS (replicating solve_buyers loop body) ──
        pagos = -pi_gb * sumP_i / (pi_real + 1.0)
        trestris = (y_filt[:, None] * P).sum(axis=0)
        if buyer_competition == "aggregate":
            compe = etha_s * sumP_i
        elif buyer_competition == "matlab":
            compe = etha_fila * sumP_i
        else:
            compe = etha_i * (matriz @ (pi_real * sumP_i))
        dwi_real = pagos - compe + trestris
        dwi_all = np.append(dwi_real, simple - pi_p)

        # H-45: el peso de barrera lleva el techo de CADA comprador. Es lo
        # que hace que el precio de un comprador se detenga en SU techo y no
        # en el mayor de la hora.
        pi_hat = (pi_gs_all - pi_all) * (-pi_gb + pi_all)
        # H-46: en el fichero original el jugador virtual NO lleva la
        # barrera, lleva su propio precio. Esta traduccion se la aplica a el
        # tambien. Opt-in para medir la diferencia sin mover el defecto.
        if peso_virtual == "precio":
            pi_hat = np.concatenate((pi_hat[:I], pi_all[I:I + 1]))
        pi_hat = np.clip(pi_hat, 1e-12, None)
        sum_ph = float(np.sum(pi_hat))
        F_bar_buyers = float(np.dot(pi_hat, dwi_all)) / sum_ph if sum_ph > 1e-14 else 0.0
        d_pi_all = pi_hat * VEL_WI * (dwi_all - F_bar_buyers)
        # Projeccion en frontera (matching solve_buyers:118 que clipea pi
        # despues de cada Euler step). Sin esto, la barrera pi_hat ~0 deja
        # pi_i flotando dentro pero no hace cumplir pi_gb estricto en la
        # presencia de ruido numerico. La proyeccion garantiza que el
        # equilibrio del solver coupled coincida con el alternante en pi_i.
        at_low_real  = (pi_all[:I] <= pi_gb + 1e-9) & (d_pi_all[:I] < 0)
        at_high_real = (pi_all[:I] >= gs_i - 1e-9) & (d_pi_all[:I] > 0)
        d_pi_all[:I] = np.where(at_low_real | at_high_real, 0.0, d_pi_all[:I])

        re = (P * pi_real[None, :]).sum(axis=1)
        Hj_buyer = a_j * sumP_j**2 + b_j * sumP_j
        raw_gamma = VEL_GPC * gamma * (Hj_buyer - re) + 1000.0
        d_gamma = raw_gamma
        d_y_filt = (raw_gamma - y_filt) / tau_buyers

        # ── SELLER DYNAMICS (replicating _sellers_ode) ──
        H = 2.0 * a_j * sumP_j + b_j
        F = (pi_real[None, :] - H[:, None]
             - lam_filt[:, None] - bet_filt[None, :] + BGRANDE)
        F_bar_sellers = float(np.sum(P * F)) / simplex
        dP = P * VEL_RD * (F - F_bar_sellers)

        Glam = VEL_GRAD * lam_ub * (sumP_j - G_net_j) + 1000.0
        Gbet = VEL_GRAD * bet_ub * (sumP_i - D_net_i) + 1000.0
        d_lam_filt = (Glam - lam_filt) / tau_sellers
        d_bet_filt = (Gbet - bet_filt) / tau_sellers

        # Factores de escala matching JoinFinal.m:160-161:
        #   WI = 0.08 * Replicator_buyers   → 0.08 sobre bloque buyers
        #   WJ = 10   * Replicator_sellers  → 10   sobre bloque sellers
        # Equilibrio invariante (cero del RHS). Recupera transitorio
        # visible de P_ji(t) en t_span=[0, 0.01]s.
        dP_salida = 10.0 * dP.ravel()
        if mu > 0.0:
            # D49: exploracion entropica del replicador del vendedor, el
            # termino V3a que llevo la dinamica al reposo en la sonda del
            # consenso: `scratchpad/consenso/arnes.py`, lineas 251 a 255
            # (`dP_eff = escala_v * dP.ravel()` y, con `mu_ent`, `lnP`, `m` y
            # `dP_eff - mu_ent * (P * (lnP - m)).ravel()`), con escala_v = 10
            # y sin aceleracion. Se resta DESPUES del factor 10, como alli, y
            # sobre la P leida con el piso de 1e-10 (D40), de modo que ln P es
            # finito. Conserva la suma de P: sum P·(ln P - m) = 0. Con mu = 0
            # esta rama no corre y la salida es la de siempre, al bit.
            lnP = np.log(P)
            m = float(np.sum(P * lnP)) / float(np.sum(P))
            dP_salida = dP_salida - mu * (P * (lnP - m)).ravel()
        salida = np.concatenate([
            0.08 * d_pi_all,    # I+1   (buyer pi)
            0.08 * d_gamma,     # J     (buyer auxiliar)
            0.08 * d_y_filt,    # J     (buyer filtro)
            dP_salida,          # J*I   (seller P_ji; D49 con mu > 0)
            10.0 * Glam,        # J     (seller capacity multiplier)
            10.0 * Gbet,        # I     (seller demand multiplier)
            10.0 * d_lam_filt,  # J     (seller lam filtro)
            10.0 * d_bet_filt,  # I     (seller bet filtro)
        ])
        # D41: el primer valor no finito del lado derecho corta la
        # integracion (ver `_LadoDerechoNoFinito`).
        if not np.all(np.isfinite(salida)):
            raise _LadoDerechoNoFinito(t, evaluaciones[0], "salida")
        return salida

    # ── Integracion ──────────────────────────────────────────
    t_eval = np.linspace(t_span[0], t_span[1], n_points)
    try:
        sol = solve_ivp(
            _rhs, t_span, X0, method=method,
            t_eval=t_eval, rtol=rtol, atol=atol,
        )
    except _LadoDerechoNoFinito as corte:
        # D41: la integracion se detuvo en el primer valor no finito. La
        # trayectoria lleva solo el punto inicial, con las formas de siempre
        # (un punto en el eje del tiempo), y `success=False`: el motor la
        # trata como integrador sin exito (D37), con la parada activa
        # conserva la vuelta anterior buena y, si era la primera, deja la
        # hora sin mercado con su motivo. Solo se atrapa esta excepcion.
        t_sol = np.array([float(t_span[0])])
        y_sol = X0[:, None].copy()
        exito = False
        mensaje = str(corte)
        nfev, njev = corte.evaluacion, 0
    else:
        t_sol, y_sol = sol.t, sol.y
        exito = bool(sol.success)
        mensaje = str(sol.message)
        # D36: el trabajo del integrador, para el presupuesto de la parada.
        nfev = int(getattr(sol, "nfev", 0) or 0)
        njev = int(getattr(sol, "njev", 0) or 0)

    n_t = y_sol.shape[1]
    pi_t_real = np.clip(y_sol[:I, :], pi_gb, gs_i[:, None])
    P_t = np.clip(
        y_sol[idx0_P:idx0_lam, :].reshape(J, I, n_t),
        0.0, None,
    )

    pi_star = pi_t_real[:, -1]
    P_star  = P_t[:, :, -1]

    # ── Welfare a lo largo de la trayectoria ─────────────────
    Wj_t, Wi_t = _compute_welfare_trajectory(
        P_t=P_t, pi_t=pi_t_real,
        a_j=a_j, b_j=b_j, lam_j=lam_j, theta_j=theta_j, G_net_j=G_net_j,
        G_klim_i=G_klim_i, lam_i=lam_i, theta_i=theta_i, etha_i=etha_i,
    )
    W_t = Wj_t + Wi_t

    # CAL-49 / validación horaria: los multiplicadores solo se extraen si se
    # piden. El estado ya los lleva; aquí se rebanan del resultado.
    mult = {}
    if devuelve_multiplicadores:
        mult = dict(
            lam_t=y_sol[idx0_lam:idx0_bet, :],
            bet_t=y_sol[idx0_bet:idx0_lamfilt, :],
            lam_filt_t=y_sol[idx0_lamfilt:idx0_betfilt, :],
            bet_filt_t=y_sol[idx0_betfilt:, :],
        )

    return CoupledTrajectory(
        t=t_sol,
        pi_t=pi_t_real,
        P_t=P_t,
        Wj_t=Wj_t,
        Wi_t=Wi_t,
        W_t=W_t,
        pi_star=pi_star,
        P_star=P_star,
        success=exito,
        message=mensaje,
        # D36: el trabajo del integrador, para el presupuesto de la parada.
        # D41: en la trayectoria cortada, las evaluaciones hasta el corte.
        nfev=nfev,
        njev=njev,
        **mult,
    )


def _compute_welfare_trajectory(
    P_t:      np.ndarray,   # (J, I, n_t)
    pi_t:     np.ndarray,   # (I, n_t)
    a_j:      np.ndarray,
    b_j:      np.ndarray,
    lam_j:    np.ndarray,
    theta_j:  np.ndarray,
    G_net_j:  np.ndarray,
    G_klim_i: np.ndarray,
    lam_i:    np.ndarray,
    theta_i:  np.ndarray,
    etha_i:   np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Welfare W_j(t), W_i(t) en cada paso t usando ``seller_welfare`` y
    ``buyer_welfare`` (formulas Chacon eqs 6, 14)."""
    from core.replicator_sellers import seller_welfare
    from core.replicator_buyers  import buyer_welfare

    J, I, n_t = P_t.shape
    Wj_t = np.zeros(n_t)
    Wi_t = np.zeros(n_t)
    for k in range(n_t):
        P_k  = P_t[:, :, k]
        pi_k = pi_t[:, k]
        Wj_t[k] = seller_welfare(P_k, G_net_j, a_j, b_j, lam_j, theta_j, pi_k)
        Wi_t[k] = buyer_welfare(pi_k, P_k, G_klim_i, lam_i, theta_i, etha_i)
    return Wj_t, Wi_t


def equilibrium_match(
    coupled:   CoupledTrajectory,
    pi_alt:    np.ndarray,    # (I,) pi_star del solver alternante
    P_alt:     np.ndarray,    # (J, I) P_star del solver alternante
    pi_tol:    float = 1.0,   # COP/kWh
    P_tol:     float = 0.01,  # kW
) -> dict:
    """Compara steady-state coupled vs alternating. Retorna dict con
    diff_pi_max, diff_P_max, y flag ``match``.

    Uso esperado: validar que el solver coupled converge al mismo
    equilibrio Nash que el solver alternante (sanity check pre-PR).
    """
    diff_pi = np.abs(coupled.pi_star - pi_alt)
    diff_P  = np.abs(coupled.P_star  - P_alt)
    return {
        "diff_pi_max":   float(diff_pi.max()),
        "diff_P_max":    float(diff_P.max()),
        "diff_pi_mean":  float(diff_pi.mean()),
        "diff_P_mean":   float(diff_P.mean()),
        "match_pi":      bool(diff_pi.max() < pi_tol),
        "match_P":       bool(diff_P.max()  < P_tol),
        "match":         bool(diff_pi.max() < pi_tol and diff_P.max() < P_tol),
    }
