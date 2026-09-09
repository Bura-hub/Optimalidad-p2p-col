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

Nota de auditoría (A3, 2026-04-17) — alternancia vs ODE conjunta
----------------------------------------------------------------
El bucle Stackelberg de este módulo (L230-244) se resuelve por
alternancia: un paso completo de RD de vendedores (`solve_sellers`,
con su propia integración ODE interna) seguido de un paso completo
de RD de compradores (`solve_buyers`, ídem), iterando hasta
‖P_new − P_old‖ / (‖P_old‖ + 1e-9) < tol. En contraste,
`Documentos/copy/JoinFinal.m:139` integra el sistema acoplado
`[consumer_state, seller_state]` con `ode15s` en una sola llamada.

Ambas formulaciones convergen al mismo equilibrio de Nash en el
límite (el punto fijo es invariante bajo la factorización del
operador), pero producen trayectorias transitorias distintas. El
criterio de parada adaptativo se valida en
`tests/test_stackelberg_convergence.py` (norma relativa bajo
tolerancia al salir del bucle). Esta divergencia debe citarse como
elección de implementación en la sección de Métodos de la tesis.
Ver también `Documentos/notas_modelo_tesis.md §7 CAL-7`.
"""

import os
import sys
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import (ProcessPoolExecutor, FIRST_COMPLETED, wait,
                                as_completed)  # noqa: F401 (as_completed: API)

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
            # Fix CAL-28b (2026-05-06): caracteres ASCII puros para
            # evitar UnicodeEncodeError bajo stdout cp1252 (Windows)
            # cuando un script auxiliar importa EMSP2P sin wrapear stdout.
            # Antes: "█"*done + "░"*(W-done) (caracteres no-ASCII)
            bar   = "#" * done + "-" * (self._W - done)
            ela   = time.time() - self.t0
            rem   = (ela / pct - ela) if pct > 1e-6 else 0.0
            rate  = f"{self.n/ela:.1f}h/s" if ela > 0.1 else "---"
            ela_s = f"{int(ela//60):02d}:{int(ela%60):02d}"
            rem_s = f"{int(rem//60):02d}:{int(rem%60):02d}"
            line  = (f"\r  {self.desc}: {int(pct*100):3d}%|{bar}| "
                     f"{self.n}/{self.total}h "
                     f"[{ela_s}<{rem_s}, {rate}]  ")
            try:
                sys.stdout.write(line)
                sys.stdout.flush()
            except UnicodeEncodeError:
                # Defense-in-depth: si el stdout no acepta el line,
                # fallback silencioso (no rompe el solver).
                pass
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

    # H-45 / C-146: el techo de CADA agente, matriz (N, T), o None.
    #
    # Hasta el 2026-09-07 el juego recibia un unico escalar comunitario
    # mientras la LIQUIDACION recibia la matriz por agente. Esa asimetria era
    # la que producia el cero exacto: el ahorro de un comprador es su techo
    # menos el precio, y el precio se resolvia contra un techo ajeno.
    #
    # Con `None` el comportamiento es el historico, bit a bit. Con la matriz,
    # el juego usa el techo de cada comprador y el limite economico de
    # generacion el de cada agente, igual que la liquidacion.
    #
    # AVISO DE FIDELIDAD: el modelo base no contempla esto. Su ecuacion (5)
    # escribe las dos cotas como escalares globales. El techo por agente es
    # una extension de esta tesis, justificada porque la comunidad tiene dos
    # comercializadores dentro de un mismo mercado de comercializacion, que
    # es lo que la Resolucion CREG 101 072 de 2025 permite expresamente al
    # indexar sus formulas por comercializador. Ver H-48.
    pi_gs_agente: Optional[np.ndarray] = None

    # H-49 / C-148: el piso de CADA vendedor, matriz (N, T), o None.
    #
    # Es la otra mitad de CAL-47 y no habia llegado nunca: en produccion el
    # piso valia 280 COP/kWh constante para todos los agentes y todas las
    # horas, la misma constante escrita a mano que CAL-47 venia a sustituir.
    # Con el techo ya corregido, eso sobrestimaba el ancho de la banda hasta
    # doce veces, y por la identidad de H-33 el excedente con el.
    #
    # ASIMETRIA QUE HAY QUE ENTENDER, y no es un descuido: el precio tiene
    # indice de COMPRADOR y el piso tiene indice de VENDEDOR. No cabe un piso
    # por vendedor en una dinamica cuyo estado es un precio por comprador sin
    # cambiar el modelo. De modo que al juego entra **el menor de los pisos
    # de los vendedores activos**, que es lo que ya hace la sonda, y la
    # liquidacion recibe el vector entero, que si lo admite desde CAL-47.
    #
    # Lo que ese minimo NO resuelve es que un vendedor de piso alto venda por
    # debajo del suyo. Eso es H-43 y se resuelve con la restriccion de
    # participacion, que decide QUIEN ENTRA en vez de acotar el precio.
    pi_gb_agente: Optional[np.ndarray] = None


@dataclass
class SolverParams:
    # Parámetros calibrados contra JoinFinal.m de Chacón et al. (2025):
    #   t_span  = [0, 0.01]  →  10 constantes de tiempo del filtro (τ=0.001)
    #   n_points = 300       →  Euler compradores, dt=3.33e-5 (validado por
    #                           tests con t_span=(0,0.005)+n_points=150 que dan
    #                           el MISMO dt). Reducir a 150 con t_span=0.01
    #                           genera dt=6.67e-5 e invierte el signo de IE
    #                           (VEL_GPC=1e5 exige dt ≲ 4e-5 para Euler estable).
    #                           En vendedores LSODA es adaptativo y no depende.
    #   tau_sellers = 0.001  →  filtro de paso bajo λ/β (Generadoresfiltro.m)
    #   tau_buyers  = 0.01   →  tau3 de JoinFinal.m (bloque comprador)
    #   ode_method  = LSODA  →  análogo a ode15s de MATLAB (JoinFinal.m:139),
    #                           stiff-aware (VelGrad=1e6 genera stiffness en λ/β)
    tau:               float = 0.001    # filtro vendedores (τ en JoinFinal.m)
    tau_buyers:        float = 0.01     # tau3 en JoinFinal.m (escala comprador)
    t_span:            tuple = (0.0, 0.01)   # iguala t_span=[0,0.01] de JoinFinal.m
    n_points:          int   = 300           # Euler compradores; dt=3.33e-5
    # Default `iters=2`, `tol=1e-3`, `max=10` sustentados por CAL-1 (sintetico)
    # y CAL-19 (empirico MTE 168h). Ver `docs/adr/0019-cal19-stackelberg-
    # convergencia-empirica.md` y `analysis/stackelberg_convergence_real.py`.
    # Trade-off: |Δwelfare(iters=2) - welfare(iters=10)| < 0.02% con 2.4×
    # speedup vs iters=10 sobre el subset.
    stackelberg_iters: int   = 2    # iteraciones mínimas (min_iter)
    stackelberg_tol:   float = 1e-3  # tolerancia relativa ||P_new - P_old|| / (||P_old|| + ε)
    stackelberg_max:   int   = 10    # iteraciones máximas (red de seguridad)
    parallel:          bool  = True
    # C-169: CUANTOS OBREROS. Con None el ejecutor toma su valor por defecto,
    # que es el numero de nucleos que `os.cpu_count` declara. Y ese numero
    # **no respeta la afinidad ni los limites del contenedor**: en una maquina
    # compartida o dentro de un cgroup puede ser mayor que los nucleos que de
    # verdad se pueden usar, y entonces los procesos se pelean; o el operador
    # puede querer dejar holgura y no tiene como pedirla.
    #
    # Con un entero se fija. El lanzador del servidor lo pasa desde su propia
    # cuenta, que si mira la afinidad.
    procesos:          object = None
    ode_method:        str   = "LSODA"   # solver de scipy para solve_sellers
    # ADR-0038 (campaña de smokes): forma del término de competencia de
    # compradores. "aggregate" (default) = histórico bit a bit; "matrix" =
    # forma matricial de JoinFinal.m:187-200 (smoke A2). Solo afecta a
    # solve_buyers; ningún caller de producción cambia.
    buyer_competition: str   = "aggregate"
    # CAL-48 / H-38. "alternado" (defecto) = comportamiento historico bit a
    # bit. "acoplado" = la via del modelo base, que integra precios y
    # cantidades juntos con un solo solver, como hace JoinFinal.m:139.
    # Medido sobre dato real: el alternado deja el 72 % de los precios
    # pegados a una cota y el acoplado solo el 1,2 %.
    metodo:            str   = "alternado"   # "alternado" | "acoplado"
    t_span_acoplado:   float = 0.05   # horizonte del acoplado; a 0,05 dos
                                      # tercios de las horas llegan a
                                      # estacionario y la corrida cuesta
                                      # 1,4 h con once procesos
    # C-161: si se pide, cada hora conserva su trayectoria con los
    # multiplicadores en vez de tirarla. Es lo que llena el almacen y lo que
    # permite dibujar la convergencia de cualquier hora sin volver a simular.
    # Opt-in: por omision la corrida queda identica bit a bit.
    guarda_trayectorias: bool = False


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

    Campos coupled-ODE (opcionales, populados cuando run_convergence se
    llama con use_coupled_ode=True). Vienen del solver acoplado en
    `core.coupled_ode_convergence.solve_coupled_for_hour`, que replica
    JoinFinal.m linea 139 (single ode15s sobre [P, pi]).
    coupled_t       : (n_t,) eje tiempo s ∈ [0, 0.01]
    coupled_pi_t    : (I, n_t) precios continuos
    coupled_P_t     : (J, I, n_t) potencias continuas
    coupled_Wj_t    : (n_t,) welfare sellers continuo W_j(t)
    coupled_Wi_t    : (n_t,) welfare buyers  continuo W_i(t)
    coupled_W_t     : (n_t,) welfare total    W(t) = W_j(t) + W_i(t)
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
    coupled_t:      Optional[np.ndarray] = None
    coupled_pi_t:   Optional[np.ndarray] = None
    coupled_P_t:    Optional[np.ndarray] = None
    coupled_Wj_t:   Optional[np.ndarray] = None
    coupled_Wi_t:   Optional[np.ndarray] = None
    coupled_W_t:    Optional[np.ndarray] = None
    # Cotas admisibles efectivas usadas por el solver P2P en esta hora
    # (escalares; ver CAL-9 + memo coupled-ODE para por que NO son hora-a-hora).
    pi_gs:          Optional[float] = None
    pi_gb:          Optional[float] = None


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
    iters_used: int   = 0    # iteraciones Stackelberg efectivas; 0 cuando J=0 o I=0 (sin mercado)
    norm_rel_final: float = 0.0  # ‖ΔP‖ / (‖P‖+ε) al salir del loop; 0.0 cuando sin mercado (A6)
    seller_ids: list  = field(default_factory=list)
    buyer_ids:  list  = field(default_factory=list)
    G_klim_k:   Optional[np.ndarray] = None
    D_k:        Optional[np.ndarray] = None

    # H-43 / C-151: vendedores que la restriccion de participacion dejo fuera
    # de esta hora, por identificador de agente.
    #
    # NO salen de `seller_ids`: siguen ahi con su fila de energia a cero. Es
    # la unica forma de que la liquidacion los siga contando, porque recorre
    # los vendedores de esa lista para calcular lo que cada uno exporta a la
    # red. Un vendedor ausente de la lista no exportaria: se evaporaria.
    retirados:  list  = field(default_factory=list)
    # La trayectoria de la hora, opt-in. Hasta hoy el trabajador la obtenia
    # entera, con sus multiplicadores ya integrados, y se quedaba con dos
    # matrices y un escalar: todo lo demas moria al salir de la funcion. Sin
    # ella no hay forma de dibujar la convergencia de una hora elegida sin
    # volver a simular. Ver el almacen y la fase 2 del plan.
    tr:         object = None


# ── Worker (top-level para pickle en multiprocessing) ────────────────────────

def nucleos_disponibles() -> int:
    """Los nucleos que este proceso PUEDE usar de verdad.

    POR QUE NO BASTA `os.cpu_count`. Devuelve los nucleos que la maquina
    declara, no los que este proceso tiene permitido usar. En un servidor
    compartido, dentro de un contenedor, o con la afinidad restringida, los
    dos numeros difieren, y lanzar mas procesos que nucleos utiles no acelera
    nada: los hace pelearse por el mismo tiempo de procesador.

    Se prefieren, en este orden:

      1. la afinidad del proceso, que es lo unico que refleja una restriccion
         real y solo existe en sistemas de tipo Unix;
      2. la cuenta que el sistema declara;
      3. ocho, que es un valor prudente si ninguna de las dos responde.
    """
    try:
        return len(os.sched_getaffinity(0))          # solo en Unix
    except AttributeError:
        pass
    return os.cpu_count() or 8


def _cuantos_obreros(pedidos) -> Optional[int]:
    """Cuantos procesos abrir, avisando en voz alta de lo que se elige.

    Un numero que no se imprime no se puede comprobar, y la pregunta de si la
    corrida esta usando toda la maquina se ha hecho ya varias veces sin que la
    salida diera con que contestarla.
    """
    hay = nucleos_disponibles()
    if pedidos is None:
        n = hay
        motivo = "todos los disponibles"
    else:
        n = max(1, int(pedidos))
        if n > hay:
            motivo = (f"pedidos {n}, pero solo hay {hay} utiles; se abren "
                      f"{hay} para no sobresuscribir")
            n = hay
        else:
            motivo = f"pedidos de los {hay} utiles"
    hilos = os.environ.get("OMP_NUM_THREADS", "sin fijar")
    print(f"    [C-169] {n} procesos ({motivo}) · {hilos} hilo(s) de álgebra "
          f"por proceso", flush=True)
    return n


def _run_hour_worker(args):
    """
    Resuelve el equilibrio Nash-Stackelberg para una hora k.

    Debe ser top-level (no método) para ser serializable por pickle en
    ProcessPoolExecutor (Windows requiere esto). Retorna HourlyResult con
    P_star=None si no hay vendedores o compradores en esa hora.

    El loop Stackelberg corre al menos min_iter veces y sale antes si
    ||P_new - P_old|| / (||P_old|| + ε) < tol (convergencia relativa).
    """
    # CAL-48 anadio dos campos al final. Se aceptan tuplas de la longitud
    # anterior para no romper a los llamadores que la construyen a mano
    # (varios tests de humo y de convergencia lo hacen); esos siguen
    # resolviendo por alternancia, que es su comportamiento historico.
    args = tuple(args)
    if len(args) == 22:
        args = args + ("alternado", 0.05)
    # H-49 anadio el piso por vendedor al final. Se acepta la longitud
    # anterior para no romper a los llamadores que arman la tupla a mano.
    if len(args) == 24:
        args = args + (None,)
    # Y el almacen anade el ultimo: si se pide, la hora devuelve su
    # trayectoria entera en vez de tirarla. Opt-in, para que el
    # comportamiento por omision quede identico bit a bit.
    if len(args) == 25:
        args = args + (False,)

    (k, G_klim_k, D_k, G_raw_k, seller_ids, buyer_ids,
     a_all, b_all, lam_all, theta_all, etha_all,
     pi_gs, pi_gb, tau, tau_buyers, t_span, n_points,
     min_iter, tol, max_iter, ode_method, buyer_competition,
     metodo, t_span_aco, pi_gb_j, guarda_tr) = args

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

    # CAL-48 / H-38: la vía del modelo base integra precios y cantidades
    # JUNTOS, no alterna. El lazo alternado es una aproximación de esta
    # traducción y deja el precio pegado a una cota en el 72 % de los casos,
    # frente al 1,2 % del acoplado. Medido sobre el dato real: el acoplado
    # cuesta 26,3 s por hora en mediana al horizonte que se conserva, es
    # decir 1,4 h de corrida completa con once procesos.
    if metodo == "acoplado":
        from core.coupled_ode_convergence import solve_coupled_for_hour
        try:
            tr = solve_coupled_for_hour(
                G_net_j=G_net_j, D_net_i=D_net_i, a_j=a_j, b_j=b_j,
                lam_j=lam_j, theta_j=theta_j, G_klim_i=G_klim_i,
                lam_i=lam_i, theta_i=theta_i, etha_i=etha_i,
                pi_gs=pi_gs, pi_gb=pi_gb, tau_sellers=tau,
                tau_buyers=tau_buyers, t_span=(0.0, float(t_span_aco)),
                n_points=n_points,
                # CAL-49: la via acoplada no recibia la forma del termino de
                # competencia, de modo que elegirla no la afectaba y las dos
                # vias podian correr con formas distintas sin avisar.
                buyer_competition=buyer_competition,
                # Los multiplicadores dicen QUE RESTRICCION esta mordiendo.
                # Sin ellos, la figura de convergencia enseña el precio
                # deteniendose sin poder decir por que se detiene ahi.
                devuelve_multiplicadores=bool(guarda_tr))
        except Exception:
            return res
        # El integrador avisa cuando no logra resolver. Antes de CAL-48 esa
        # bandera no se miraba y la hora entraba igual con lo que el solver
        # tuviera a mano. Se marca como sin mercado, que es lo que ya hace
        # esta funcion con las horas que producen NaN.
        if not bool(getattr(tr, "success", True)):
            return res
        P_star = np.asarray(tr.P_star, dtype=float)
        pi_i = np.clip(np.asarray(tr.pi_star, dtype=float), pi_gb, pi_gs)
        # Cuánto se mueve el precio en el último décimo frente a todo su
        # recorrido: cerca de cero es estacionario. Se guarda donde el lazo
        # alternado guardaba su residuo, para que el diagnóstico de la
        # corrida siga teniendo una sola columna de convergencia.
        traj = tr.pi_t
        cola = int(max(1, traj.shape[1] // 10))
        mov = float(np.max(np.abs(traj[:, -1] - traj[:, -cola])))
        rec = float(np.max(np.abs(traj.max(axis=1) - traj.min(axis=1))))
        iter_count = int(traj.shape[1])
        norm_rel = mov / rec if rec > 1e-12 else 0.0
        if guarda_tr:
            res.tr = tr
    else:
        iter_count = 0
        P_old = np.zeros_like(P_star)
        norm_rel = 0.0
        while iter_count < max_iter:
            P_old  = P_star.copy()
            # Algoritmo 2: RD vendedores (tau = τ de JoinFinal.m)
            P_star = solve_sellers(pi_i, G_net_j, D_net_i, a_j, b_j,
                                   tau=tau, t_span=t_span, n_points=n_points,
                                   method=ode_method)
            # Algoritmo 3: RD compradores (tau_buyers = tau3 de JoinFinal.m)
            pi_i   = solve_buyers(P_star, a_j, b_j, etha_i,
                                  pi_gs=pi_gs, pi_gb=pi_gb,
                                  tau=tau_buyers, t_span=t_span, n_points=n_points,
                                  buyer_competition=buyer_competition)
            pi_i   = np.clip(pi_i, pi_gb, pi_gs)
            iter_count += 1
            norm_rel = (np.linalg.norm(P_star - P_old)
                        / (np.linalg.norm(P_old) + 1e-9))
            if iter_count >= min_iter and norm_rel < tol:
                break

    # Guard: si el ODE produjo NaN (~0.2% de horas con G_net minúsculos +
    # VelGrad=1e6 generan inestabilidad puntual), marcar la hora como sin
    # mercado. Un solo NaN contamina toda la agregación aguas abajo (IE,
    # net_benefit, W_sellers/buyers, etc.).
    if np.isnan(P_star).any() or np.isnan(pi_i).any():
        return res

    # ── Restriccion de participacion (H-43 / C-151) ──────────────────────
    #
    # Un vendedor no entra si el mercado le paga MENOS QUE SU ALTERNATIVA por
    # el conjunto de lo que coloca. El criterio es su ingreso ponderado por
    # energia, que es lo mismo que exigir que su prima no sea negativa: es lo
    # que decide un vendedor racional (C-149).
    #
    # SE ACTIVA SOLA, y por eso no lleva bandera. Con un piso escalar todos
    # los vendedores tienen el mismo, el precio ya esta acotado por debajo a
    # ese valor, y el ingreso ponderado nunca queda por debajo: no se retira
    # nadie jamas. La restriccion es inerte cuando las cotas son uniformes,
    # que es el caso del modelo base y del sintetico, y muerde solo cuando
    # los pisos difieren, que es cuando hace falta.
    #
    # LA TRAMPA, señalada en H-43 antes de implementar esto: resolver con el
    # conjunto reducido y quitar al retirado de `seller_ids` haria que la
    # liquidacion **no lo contara**, porque recorre esa lista para calcular
    # lo que cada vendedor exporta. Su excedente no se exportaria: se
    # evaporaria. Es el mismo error que la auditoria encontro en la sonda del
    # escenario, donde sesgaba la comparacion de facturas en un 76,8 %.
    #
    # De ahi que se resuelva con el conjunto reducido y **se reincruste el
    # resultado en la matriz del tamaño original poniendo a cero las filas de
    # los retirados**, conservando la lista intacta. Asi el retirado exporta
    # todo a la red, su prima sale cero, y nada de lo que hay aguas abajo
    # cambia de forma.
    if pi_gb_j is not None and J > 1:
        piso_v = np.asarray(pi_gb_j, dtype=float)
        fuera = []
        for u in range(J):
            colocado = float(P_star[u, :].sum())
            if colocado <= 1e-9:
                continue
            ingreso = float(np.dot(P_star[u, :], pi_i)) / colocado
            if ingreso < piso_v[u] - 1e-9:
                fuera.append(u)

        if fuera and len(fuera) < J:
            quedan = [u for u in range(J) if u not in fuera]
            sub = _run_hour_worker(
                (k, G_klim_k, D_k, G_raw_k,
                 [seller_ids[u] for u in quedan], buyer_ids,
                 a_all, b_all, lam_all, theta_all, etha_all,
                 pi_gs, float(np.min(piso_v[quedan])),
                 tau, tau_buyers, t_span, n_points,
                 min_iter, tol, max_iter, ode_method, buyer_competition,
                 metodo, t_span_aco, piso_v[quedan]))
            # Si el conjunto reducido no resuelve, la hora se queda sin
            # mercado, que es lo que esta funcion ya hace con las que no
            # convergen. Mejor sin mercado que con uno que nadie aceptaria.
            if sub.P_star is None:
                return res
            P_completo = np.zeros((J, I))
            P_completo[quedan, :] = sub.P_star
            P_star   = P_completo
            pi_i     = sub.pi_star
            iter_count = sub.iters_used
            norm_rel = sub.norm_rel_final
            # La llamada anidada hace su propia vuelta, de modo que el bucle
            # se cierra solo. Sus retirados se suman a los de esta vuelta.
            res.retirados = ([seller_ids[u] for u in fuera]
                             + list(sub.retirados))
        elif fuera:
            # Todos a perdida: no hay mercado que valga esa hora.
            return res

    res.P_star = P_star; res.pi_star = pi_i; res.iters_used = iter_count
    res.norm_rel_final = float(norm_rel)

    settle = residual_settlement(P_star, G_net_j, D_net_i,
                                  G_klim_k, G_raw_k, pi_gs, pi_gb,
                                  seller_ids, buyer_ids)
    res.P_int = settle["P_int"]; res.P_ext = settle["P_ext"]

    # C-164: los dos indices llevaban el nombre del otro. El autoconsumo se
    # mide contra la generacion y la autosuficiencia contra la demanda.
    res.SC = self_consumption_index(P_star, G_klim_k, D_k)
    res.SS = self_sufficiency_index(P_star, D_k, G_klim_k)
    # H-49: la prima de cada vendedor se mide contra SU piso, no contra el
    # menor de la hora. Es lo unico que hace visible a un vendedor que vende
    # por debajo de su alternativa, que es H-43. El juego usa el minimo; la
    # liquidacion, el vector.
    S_i, SR_j = compute_savings(P_star, pi_i, pi_gs,
                                pi_gb if pi_gb_j is None else pi_gb_j)
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

        # ── El techo, por agente y hora si se dio ─────────────────────────
        # C-146: con la matriz presente, el techo de cada agente gobierna su
        # limite economico de generacion y el precio de cada comprador. Sin
        # ella, el escalar de siempre y el resultado es identico bit a bit.
        techo_m = gr.pi_gs_agente
        if techo_m is not None:
            techo_m = np.asarray(techo_m, dtype=float)
            if techo_m.ndim == 1:                  # (N,) — perfil sin calendario
                techo_m = np.tile(techo_m[:, None], (1, T))
            if techo_m.shape != (N, T):
                raise ValueError(
                    f"pi_gs_agente tiene forma {techo_m.shape}; se esperaba "
                    f"({N}, {T}) o ({N},)")

        def _techo(k: int):
            """El techo que rige la hora k: vector por agente o el escalar."""
            return gr.pi_gs if techo_m is None else techo_m[:, k]

        # ── Y el piso, por vendedor si se dio (H-49) ──────────────────────
        piso_m = gr.pi_gb_agente
        if piso_m is not None:
            piso_m = np.asarray(piso_m, dtype=float)
            if piso_m.ndim == 1:
                piso_m = np.tile(piso_m[:, None], (1, T))
            if piso_m.shape != (N, T):
                raise ValueError(
                    f"pi_gb_agente tiene forma {piso_m.shape}; se esperaba "
                    f"({N}, {T}) o ({N},)")

        # ── Algoritmo 1, pasos 1-14: límite de generación ────────────────
        G_klim = np.zeros((N, T))
        for k in range(T):
            G_klim[:, k] = compute_generation_limit(
                G[:, k], ag.a, ag.b, ag.c, _techo(k))

        # ── Algoritmo 1, pasos 15-22: programa DR ────────────────────────
        # Si alpha=0 en todos los agentes, run_dr_program devuelve D sin cambios.
        pi_k   = compute_price_signal(D, G_klim, gr.pi_gs, gr.pi_gb)
        D_star = run_dr_program(D, G_klim, pi_k, ag.alpha, verbose=verbose_dr)

        # Empaquetar trabajos por hora (usa D_star como demanda)
        jobs = []
        for k in range(T):
            _, sids, bids = classify_agents(G_klim[:, k], D_star[:, k])
            # C-146: al trabajo de la hora entra el techo de SUS compradores.
            # Todo lo que lo recibe admite vector desde CAL-47 y C-143: el
            # bloque comprador, el solucionador acoplado y la liquidacion.
            techo_k = (gr.pi_gs if techo_m is None
                       else techo_m[bids, k] if bids else gr.pi_gs)
            # H-49: al juego entra el MENOR de los pisos de los vendedores de
            # la hora, porque por debajo de el no vende nadie. No es el piso
            # de cada vendedor: eso no cabe en una dinamica indexada por
            # comprador, y es lo que H-43 resuelve por otra via.
            piso_k = (gr.pi_gb if piso_m is None
                      else float(np.min(piso_m[sids, k])) if sids else gr.pi_gb)
            jobs.append((k, G_klim[:, k].copy(), D_star[:, k].copy(), G[:, k].copy(),
                         sids, bids,
                         ag.a, ag.b, ag.lam, ag.theta, ag.etha,
                         techo_k, piso_k,
                         sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
                         sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
                         sv.ode_method, sv.buyer_competition,
                         sv.metodo, sv.t_span_acoplado,
                         # el vector por vendedor viaja aparte, solo para la
                         # liquidacion: al juego entra el minimo, arriba
                         None if (piso_m is None or not sids)
                         else piso_m[sids, k].copy(),
                         # El almacen: si se pide, cada hora devuelve su
                         # trayectoria con multiplicadores en vez de tirarla.
                         # Opt-in, para que la corrida sin almacen quede
                         # identica bit a bit. Ver C-161.
                         bool(getattr(sv, "guarda_trayectorias", False))))

        # ── Ejecutar con barra de progreso ────────────────────────────
        rmap = {}
        desc = f"  Mercado P2P ({T}h)"

        if sv.parallel:
            # CAL-43e — VENTANA ACOTADA DE SOMETIMIENTO. No es una optimizacion:
            # evita un INTERBLOQUEO PERMANENTE, diagnosticado en el servidor el
            # 2026-08-08 (tres cuelgues: SA-2 a las 16:01, SA-3 a las 16:50).
            #
            # La version anterior sometia las T horas DE GOLPE antes de drenar
            # el primer resultado. Cada `submit()` escribe 4 bytes en la tuberia
            # interna de despertar del pool (`_ThreadWakeup.wakeup()` ->
            # `send_bytes(b"")`, CPython 3.11 `concurrent/futures/process.py`).
            # Cuando esa tuberia se llena, `submit()` bloquea el hilo principal;
            # el hilo gestor no la vacia porque a su vez esta bloqueado
            # empujando trabajo a la cola de llamadas, tambien llena; y los
            # workers quedan ociosos esperando trabajo que nadie les entrega.
            # Interbloqueo cerrado: 33 procesos vivos, 0 jiffies de CPU, log
            # congelado, sin error ni aborto.
            #
            # POR QUE DEPENDE DEL USUARIO, no de la maquina ni del azar. El
            # tamano de tuberia se raciona por UID via `fs.pipe-user-pages-soft`.
            # Medido en el mismo instante en el servidor:
            #     uid 0 (root, con el que corre el contenedor):  8192 B
            #     uid 1001 (dueno del repo):                    65536 B
            # Con 8192 B caben 2048 avisos: la hora 2049 bloquea, y T=6144 lo
            # cruza SIEMPRE. Con 65536 B caben 16384 y no se llena nunca. Por eso
            # la corrida canonica de junio, ejecutada COMO uid 1001, completo con
            # este mismo codigo. **No era una carrera con suerte variable: es
            # determinista, y lo decide el usuario que ejecuta.**
            #
            # La ventana mantiene los avisos pendientes en ~4*workers*4 bytes
            # (~480 B de 8192), dos ordenes de margen, e independiente del
            # tamano de tuberia. `rmap` se sigue indexando por hora y se
            # reordena al final: el resultado numerico es identico, solo cambia
            # el ritmo de sometimiento. Medido: M1 480 s vs 471,8 s de junio
            # (+1,7 %) y M3 320 s vs 323,5 s (-1 %) — dentro del ruido.
            with _make_bar(total=T, desc=desc) as bar:
                with ProcessPoolExecutor(
                        max_workers=_cuantos_obreros(sv.procesos)) as ex:
                    ventana = max(4 * (getattr(ex, "_max_workers", 0) or 1), 64)
                    pendientes = iter(jobs)
                    activos = set()
                    for j in pendientes:
                        activos.add(ex.submit(_run_hour_worker, j))
                        if len(activos) >= ventana:
                            break
                    while activos:
                        hechos, activos = wait(activos,
                                               return_when=FIRST_COMPLETED)
                        for f in hechos:
                            r = f.result()
                            rmap[r.k] = r
                            bar.update(1)
                            j = next(pendientes, None)
                            if j is not None:
                                activos.add(ex.submit(_run_hour_worker, j))
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
        use_coupled_ode: bool = True,
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
                    return_traj=True, method=sv.ode_method,
                )
                pi_i, t_b, pi_traj = solve_buyers(
                    P_star, a_j, b_j, etha_i,
                    pi_gs=gr.pi_gs, pi_gb=gr.pi_gb,
                    # CAL-40a (H-A-011): tau_buyers (=tau3 JoinFinal), no el
                    # tau de sellers — el error solo afectaba la TRAYECTORIA
                    # de visualización (el worker de producción y el solver
                    # acoplado siempre usaron el correcto).
                    tau=sv.tau_buyers, t_span=sv.t_span,
                    n_points=sv.n_points,
                    return_traj=True,
                    buyer_competition=sv.buyer_competition,
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

            cd = ConvergenceData(
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
                pi_gs=float(gr.pi_gs),
                pi_gb=float(gr.pi_gb),
            )

            # ── Coupled-ODE solver (replica JoinFinal.m:139) ────────────
            # Se ejecuta en paralelo al alternante para obtener trayectoria
            # continua de welfare W(t) sobre Time(s), matching Chacon Fig 3a.
            # P_star coincide con alternante <1e-5 kW. pi_star puede diferir
            # <200 COP/kWh en horas con clip activo.
            #
            # Override t_span/n_points: el pipeline del paper usa
            # sv.t_span=(0, 0.005) — demasiado corto para mostrar el
            # transitorio P_ji visible en Chacon Fig 3a (x-axis [0, 0.04]s).
            # Con factores 0.08/10 aplicados (matching JoinFinal.m:160-161),
            # el transitorio seller necesita ~0.03-0.04s para visualizarse.
            # Esto SOLO afecta la figura de convergencia, no las 16 figuras
            # que usan el solver alternante de produccion.
            COUPLED_T_SPAN_VIS   = (0.0, 0.04)   # x-axis Chacon Fig 3a
            COUPLED_N_POINTS_VIS = 400            # 100 us resolution
            if use_coupled_ode:
                try:
                    from core.coupled_ode_convergence import solve_coupled_for_hour
                    coupled = solve_coupled_for_hour(
                        G_net_j=G_net_j, D_net_i=D_net_i,
                        a_j=a_j, b_j=b_j, lam_j=lam_j, theta_j=theta_j,
                        G_klim_i=G_klim_i, lam_i=lam_i, theta_i=theta_i,
                        etha_i=etha_i,
                        pi_gs=gr.pi_gs, pi_gb=gr.pi_gb,
                        tau_sellers=sv.tau, tau_buyers=sv.tau_buyers,
                        t_span=COUPLED_T_SPAN_VIS, n_points=COUPLED_N_POINTS_VIS,
                        method=sv.ode_method,
                        buyer_competition=sv.buyer_competition,   # CAL-49
                    )
                    if coupled.success:
                        cd.coupled_t    = coupled.t
                        cd.coupled_pi_t = coupled.pi_t
                        cd.coupled_P_t  = coupled.P_t
                        cd.coupled_Wj_t = coupled.Wj_t
                        cd.coupled_Wi_t = coupled.Wi_t
                        cd.coupled_W_t  = coupled.W_t
                except Exception as exc:
                    print(f"  [coupled-ODE] hour {k} skipped: {exc}")

            conv_list.append(cd)

        return conv_list

    def run_single_hour(self, k: int, D: np.ndarray, G: np.ndarray,
                        devuelve_trayectoria: bool = False) -> HourlyResult:
        """Una hora suelta, para diagnostico.

        C-146 y C-148: honra las mismas cotas por agente que `run`. Si no se
        hiciera, esta via daria un resultado distinto del de la corrida y el
        diagnostico dejaria de diagnosticar la corrida.

        Con `devuelve_trayectoria` el resultado trae ademas la trayectoria
        entera de la hora, con sus multiplicadores. Hasta hoy **ninguna via de
        produccion devolvia la trayectoria de una hora elegida**: la que las
        guarda escoge las horas sola por heuristica y solo dos, y esta
        devolvia escalares. Era la razon de que toda figura de convergencia
        tuviera que pasar por las sondas, fuera del motor y de sus cotas.
        """
        ag = self.agents; gr = self.grid; sv = self.solver
        te = (gr.pi_gs if gr.pi_gs_agente is None
              else np.asarray(gr.pi_gs_agente, dtype=float)[:, k])
        G_klim_k = compute_generation_limit(G[:, k], ag.a, ag.b, ag.c, te)
        _, sids, bids = classify_agents(G_klim_k, D[:, k])
        pj = (None if gr.pi_gb_agente is None or not sids
              else np.asarray(gr.pi_gb_agente, dtype=float)[sids, k].copy())
        return _run_hour_worker((k, G_klim_k, D[:, k].copy(), G[:, k].copy(),
                                  sids, bids, ag.a, ag.b, ag.lam, ag.theta, ag.etha,
                                  (gr.pi_gs if gr.pi_gs_agente is None or not bids
                                   else np.asarray(gr.pi_gs_agente,
                                                   dtype=float)[bids, k]),
                                  (gr.pi_gb if pj is None else float(np.min(pj))),
                                  sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
                                  sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
                                  sv.ode_method, sv.buyer_competition,
                                  sv.metodo, sv.t_span_acoplado, pj,
                                  bool(devuelve_trayectoria)))
