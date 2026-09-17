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

import multiprocessing
import os
import sys
import time
import warnings
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
# D36 (arreglo final, revision del conjunto): a nivel de modulo y no dentro
# de la rama acoplada. Alli el `import` quedaba DENTRO del `try` de C-190, de
# modo que un modulo ausente o viejo se convertia en un motivo por hora
# («excepcion del acoplado: ImportError...») en cada hora con mercado, en vez
# de tumbar la corrida en voz alta al arrancar.
from .coupled_ode_convergence import (ARRANQUES, solve_coupled_for_hour,
                                      valida_opciones_dinamica)
# D48: la via de produccion con datos reales resuelve cada hora en el reposo
# del juego regularizado, en forma cerrada. El nucleo es puro y no conoce el
# motor; aqui se le pasan las entradas de la hora y se le anade lo que vive en
# el motor: la participacion de los vendedores (C-151, paso 7) y las cotas de
# optimalidad calculadas DESPUES de ella (D55).
from .reposo_mercado import (DESPACHOS_VENDEDORES, MODOS_PRESUPUESTO,
                             REGLAS_PRECIO, TOL_COBERTURA_REL,
                             captura as captura_reposo,
                             cotas_optimalidad, resuelve_reposo)

# CAL-48 y D48: las tres vias del mercado. Un nombre mal escrito caia antes en
# la alternada sin avisar, porque el trabajador solo preguntaba por
# "acoplado"; con tres vias eso ya no es aceptable.
METODOS = ("alternado", "acoplado", "reposo")

# D48: el principio del motivo de una hora del reposo que acabo en excepcion.
# El recuento de la linea final [D48] lo busca por este prefijo.
PREFIJO_EXCEPCION_REPOSO = "excepcion del reposo"

# D64 (2026-09-17): "merito" era el nombre del despacho por costo b_j (D52),
# que ahora se llama "costo"; el defecto pasa a "piso". Decision del
# controlador: el nombre viejo se acepta como ALIAS de "costo", con un aviso,
# para no romper ordenes ni tuplas guardadas. El nucleo no lo admite: la
# traduccion vive aqui y en la linea de ordenes.
ALIAS_DESPACHO = {"merito": "costo"}


def tol_participacion(metodo: str, piso: float) -> float:
    """C-151 y D67: con que holgura se compara el ingreso medio de un vendedor
    contra su piso antes de retirarlo.

    Por la via del REPOSO es la MISMA tolerancia con que el nucleo da la hora
    por buena, `TOL_COBERTURA_REL` relativa al piso (unos 7e-7 (COP/kWh) con
    un piso de 700): con dos tolerancias distintas quedaba una ventana en la
    que el nucleo no veia nada y el motor retiraba, y con D67 un retiro
    detiene la corrida (revision de la tarea 5a, menor 1).

    Por las vias acoplada y alternada se conserva la absoluta de 1e-9 de
    siempre, para que sigan IDENTICAS AL BIT: sus literales de a392cbd se
    calcularon con ella.
    """
    if metodo == "reposo":
        return TOL_COBERTURA_REL * max(1.0, abs(float(piso)))
    return 1e-9


def normaliza_despacho(despacho_vendedores):
    """D64: traduce el alias "merito" a "costo", con un aviso; cualquier otro
    valor pasa tal cual (lo valida `_valida_reposo`)."""
    if isinstance(despacho_vendedores, str) and \
            despacho_vendedores in ALIAS_DESPACHO:
        nuevo = ALIAS_DESPACHO[despacho_vendedores]
        warnings.warn(
            f"despacho_vendedores={despacho_vendedores!r} es el nombre viejo "
            f"del despacho por costo b_j (D52): se usa {nuevo!r}. El defecto "
            f"de produccion es 'piso', el piso del vendedor marginal (D63, "
            f"D64)", UserWarning, stacklevel=3)
        return nuevo
    return despacho_vendedores

# D48: el polvo de redondeo de los netos. `classify_agents` deja como comprador
# a un agente con demanda por debajo de 1e-9 (kWh) y una generacion aun menor,
# con un deficit NEGATIVO de ese orden; lo mismo, simetrico, del lado de los
# vendedores. El nucleo rechaza toda cantidad negativa (y la hora saldria con
# excepcion, cuando el acoplado la absorbia), de modo que ese polvo se lleva a
# cero. Una cantidad mas negativa no es polvo: pasa tal cual y el nucleo lanza.
TOL_NETO_REPOSO = 1e-9


def _entradas_reposo(a_j, G_net_j, D_net_i) -> tuple:
    """D48: las entradas del nucleo del reposo, comprobadas.

    CAL-32: el nucleo supone costos lineales, a_j = 0, y con el despacho por
    costo ordena solo por b_j. Un a_j no nulo (el caso sintetico del modelo
    base lo trae)
    se rechaza con ValueError en vez de ignorarlo; el ramal lo convierte en
    el motivo de la hora (C-190). Los netos se devuelven en copias, con el
    polvo negativo de `TOL_NETO_REPOSO` llevado a cero.
    """
    a_j = np.asarray(a_j, dtype=float)
    if np.any(a_j != 0.0):
        raise ValueError(f"CAL-32: la via por reposo supone costo cuadratico "
                         f"nulo (a_j = 0) y los vendedores de la hora traen "
                         f"a_j = {a_j.tolist()}")

    def _sin_polvo(x):
        x = np.array(x, dtype=float, copy=True)
        x[(x < 0.0) & (x >= -TOL_NETO_REPOSO)] = 0.0
        return x

    return _sin_polvo(G_net_j), _sin_polvo(D_net_i)


def _valida_reposo(modo_presupuesto, sigma_nivel, regla_precio,
                   despacho_vendedores) -> None:
    """D48: las cuatro opciones del reposo, en voz alta (H-50, C-190).

    La usan `SolverParams` y la tupla del trabajador, de modo que un valor
    desconocido se rechaza antes de someter ninguna hora y tambien cuando la
    tupla se arma a mano. `sigma_nivel` es None (la sigma de produccion,
    (I-1)/I con I los compradores en el juego) o un numero finito en [0, 1],
    y solo tiene sentido con el presupuesto "sigma": el nucleo lo rechazaria
    hora por hora.
    """
    if modo_presupuesto not in MODOS_PRESUPUESTO:
        raise ValueError(f"modo_presupuesto={modo_presupuesto!r}; use uno de "
                         f"{MODOS_PRESUPUESTO} (D50)")
    if regla_precio not in REGLAS_PRECIO:
        raise ValueError(f"regla_precio={regla_precio!r}; use uno de "
                         f"{REGLAS_PRECIO} (D51)")
    if despacho_vendedores not in DESPACHOS_VENDEDORES:
        raise ValueError(f"despacho_vendedores={despacho_vendedores!r}; use "
                         f"uno de {DESPACHOS_VENDEDORES} (D64; 'merito' se "
                         f"admite como alias de 'costo')")
    if sigma_nivel is None:
        return
    if (isinstance(sigma_nivel, bool)
            or not isinstance(sigma_nivel, (int, float, np.integer,
                                            np.floating))
            or not np.isfinite(sigma_nivel)
            or not 0.0 <= float(sigma_nivel) <= 1.0):
        raise ValueError(f"sigma_nivel={sigma_nivel!r}; tiene que ser None "
                         f"((I-1)/I, el caso central de D50) o un numero "
                         f"finito entre 0 y 1")
    if modo_presupuesto != "sigma":
        raise ValueError(f"sigma_nivel={sigma_nivel!r} solo aplica al "
                         f"presupuesto 'sigma', no a {modo_presupuesto!r}")


def _valida_dinamica(mu_entropia, nivel_acoplado) -> None:
    """D49 / D50: las dos opciones de la dinamica regularizada del acoplado,
    en voz alta (H-50, C-190), con el mismo patron que `_valida_reposo`.

    La usan `SolverParams` y la tupla del trabajador, de modo que un valor
    invalido se rechaza antes de someter ninguna hora y tambien cuando la
    tupla se arma a mano. La regla es la de `solve_coupled_for_hour`
    (`valida_opciones_dinamica`): `mu_entropia` finito y no negativo (COP/kWh),
    `nivel_acoplado` uno de NIVELES. Solo actuan por la via acoplada.
    """
    valida_opciones_dinamica(mu_entropia, nivel_acoplado,
                             nombre_nivel="nivel_acoplado")

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
    # D48: "reposo" resuelve cada hora en el reposo del juego regularizado,
    # en forma cerrada (`core/reposo_mercado.py`), sin integrar nada. Es la
    # via de produccion con datos reales desde el 2026-09-17; el defecto de
    # esta clase NO cambia, para que ningun llamador antiguo cambie en
    # silencio: lo decide la linea de ordenes.
    metodo:            str   = "alternado"   # uno de METODOS
    t_span_acoplado:   float = 0.05   # horizonte del acoplado; a 0,05 dos
                                      # tercios de las horas llegan a
                                      # estacionario y la corrida cuesta
                                      # 1,4 h con once procesos
    # D35: la sonda de H-79 corre en el servidor antes de la matriz y decide
    # si el reparto o el excedente dependen del integrador. Si la palanca es
    # la tolerancia relativa, produccion la aprieta a 1e-7. Apagada por
    # defecto: 1e-6 es identica a la de hoy, y es el mismo valor que
    # `solve_coupled_for_hour` ya trae por omision. La tolerancia absoluta
    # NO se expone (regla principal de CLAUDE.md, H-51): bajarla de 1e-6
    # cuelga el integrador.
    rtol_acoplado:     float = 1e-6
    # D26: si la palanca de H-79 es el horizonte, el acoplado para por
    # estacionario en vez de horizonte fijo: dobla `t_span_acoplado` hasta
    # que el precio se mueva menos del 1 % de su recorrido en el ultimo
    # decimo (TOL_ESTACIONARIO), o hasta pasar este tope. Apagada por
    # defecto (None): una sola resolucion con `t_span_acoplado`, identica a
    # la de hoy.
    horizonte_max_acoplado: Optional[float] = None
    # D36: tope de trabajo de la parada por estacionario, en evaluaciones del
    # integrador (`nfev`) sumadas sobre las vueltas de una hora. Antes de
    # doblar el horizonte se estima lo que costaria la vuelta siguiente y, si
    # no cabe, la hora se queda con la ultima vuelta buena. None es la
    # constante de modulo `PRESUPUESTO_EVAL_ACOPLADO`. Solo actua con la
    # parada activa: con `horizonte_max_acoplado=None` hay una sola
    # resolucion, identica al bit a la de antes.
    presupuesto_eval_acoplado: Optional[int] = None
    # H-85 / D45, RESUELTA el 2026-09-16: con que oferta arranca el acoplado.
    # "factible" es el DEFECTO DE PRODUCCION desde esta fecha: reparte en
    # proporcion al lado corto, de modo que ningun comprador arranca con mas de
    # su deficit ni ningun vendedor con mas de su excedente. "iguales" es el
    # arranque del modelo base, que reparte a partes iguales como JoinFinal.m.
    #
    # POR QUE SE CAMBIO EL DEFECTO, con la medicion del servidor delante
    # (H-86): el factible resuelve la hora 753 de E4, que con el de siempre
    # desborda el multiplicador de demanda; mueve menos del 1 % los pagos de
    # E4; y sobre todo, el arranque a partes iguales cae en algunas horas sobre
    # un conjunto SIMETRICO del que la dinamica no sale (hora 152 de E0: el
    # mismo reparto, hasta el quinto decimal, a tres compradores con deficits
    # de 2,79, 3,66 y 7,85 (kWh), ni siquiera al horizonte 2,0), y cuesta hasta
    # mil veces mas (17 340 641 evaluaciones frente a 79 762).
    #
    # AVISO DE FIDELIDAD: es un apartamiento declarado de `JoinFinal.m`, con
    # esa evidencia. `solve_coupled_for_hour`, la funcion de bajo nivel,
    # conserva su propio defecto "iguales", de modo que quien la llame directa
    # (las compuertas que comparan contra el modelo base, las sondas) sigue
    # obteniendo el arranque del modelo base sin pedirlo.
    #
    # Solo actua por la via acoplada.
    arranque_acoplado: str = "factible"
    # D47 (H-86): que mira el criterio de parada por estacionario. "precio"
    # (defecto) es el de D26, identico al bit; "precio_y_reparto" exige ademas
    # que el reparto entre compradores este quieto. El defecto NO cambia en
    # esta tarea: el horizonte de produccion se fija con el costo medido por la
    # campana `convergencia` del lanzador, no adivinado. Solo actua con la
    # parada por estacionario activa (`horizonte_max_acoplado`).
    criterio_estacionario: str = "precio"
    # D47: umbral de la medida del reparto, como fraccion de la energia
    # transada de la hora. Solo actua con `criterio_estacionario` en
    # "precio_y_reparto".
    tol_reparto: float = 0.01
    # C-161: si se pide, cada hora conserva su trayectoria con los
    # multiplicadores en vez de tirarla. Es lo que llena el almacen y lo que
    # permite dibujar la convergencia de cualquier hora sin volver a simular.
    # Opt-in: por omision la corrida queda identica bit a bit.
    guarda_trayectorias: bool = False
    # D24: plazo POR HORA del lazo paralelo, en segundos, medido desde que la
    # hora empieza a correr en un trabajador y no desde que se somete. La hora
    # que lo pasa se anota como no resuelta, con su motivo, y la corrida
    # sigue con las demas. Es red de seguridad: las horas que no terminaban
    # eran H-51, ya resuelto, pero los casos de escalado del servidor no se
    # han probado nunca. None lo desactiva. La rama secuencial no tiene plazo.
    plazo_hora_s: Optional[float] = 900.0
    # D48 a D52: las opciones de la via por reposo. Solo actuan con
    # `metodo="reposo"`; con las otras vias son inertes.
    #   modo_presupuesto     "sigma" (produccion, D50), "algoritmo3" (literal
    #                        del articulo, techo escalar) o "c136" (el
    #                        arranque de hoy del acoplado, solo comparacion)
    #   sigma_nivel          None = (I-1)/I, el caso central; o el valor del
    #                        barrido en [0, 1]. Solo con "sigma"
    #   regla_precio         "uniforme" (D51, el precio marginal que conserva
    #                        el ingreso) o "puja" (sensibilidad)
    #   despacho_vendedores  "piso" (D63 a D65, el defecto: despacho por el
    #                        piso de cada vendedor con la caminata
    #                        competitiva, y el piso del juego el del vendedor
    #                        marginal), "costo" (el merito por b_j de D52, de
    #                        comparacion) o "llenado". "merito" se admite como
    #                        alias de "costo", con aviso
    modo_presupuesto: str = "sigma"
    sigma_nivel: Optional[float] = None
    regla_precio: str = "uniforme"
    despacho_vendedores: str = "piso"
    # D49 / D50: la dinamica regularizada, como opciones APAGADAS de la via
    # acoplada. No son la via de produccion (esa es el reposo en forma
    # cerrada, D48): sirven para validar el reposo y dibujar la convergencia.
    #   mu_entropia     exploracion entropica del replicador del vendedor
    #                   (COP/kWh); 0.0 la apaga, identico al bit
    #   nivel_acoplado  "c136" (el arranque de precios de siempre, identico al
    #                   bit) o "sigma" (el presupuesto del reposo, con el
    #                   jugador virtual en su techo)
    # Solo actuan con `metodo="acoplado"`; con las otras vias son inertes.
    mu_entropia: float = 0.0
    nivel_acoplado: str = "c136"

    def __post_init__(self):
        # D48: la via se valida al construir. Antes un nombre desconocido
        # resolvia por la alternada sin decir nada.
        if self.metodo not in METODOS:
            raise ValueError(f"metodo={self.metodo!r}; use uno de {METODOS}")
        # D64: el alias "merito" pasa a "costo", con aviso, antes de validar.
        self.despacho_vendedores = normaliza_despacho(
            self.despacho_vendedores)
        _valida_reposo(self.modo_presupuesto, self.sigma_nivel,
                       self.regla_precio, self.despacho_vendedores)
        # D49 / D50: y las dos opciones de la dinamica regularizada.
        _valida_dinamica(self.mu_entropia, self.nivel_acoplado)
        # D36: un presupuesto que no es un entero positivo no se corrige en
        # silencio. Se rechaza al construir, antes de someter ninguna hora:
        # dentro del trabajador se convertiria en una excepcion por hora.
        p = self.presupuesto_eval_acoplado
        if p is not None:
            if isinstance(p, bool) or int(p) != p or int(p) <= 0:
                raise ValueError(
                    f"presupuesto_eval_acoplado={p!r}; tiene que ser un "
                    f"entero positivo (evaluaciones del integrador) o None "
                    f"para la constante de modulo")
            self.presupuesto_eval_acoplado = int(p)
        # H-85 / D45: una regla de arranque desconocida se rechaza al
        # construir, no dentro del trabajador (seria una excepcion por hora).
        if self.arranque_acoplado not in ARRANQUES:
            raise ValueError(
                f"arranque_acoplado={self.arranque_acoplado!r}; use "
                f"'factible' (el defecto de produccion, D45) o 'iguales' "
                f"(el del modelo base, como JoinFinal.m)")
        # D47: lo mismo con el criterio de parada y su umbral. Un criterio
        # desconocido dentro del trabajador seria una excepcion por hora
        # (C-190), y un umbral no finito dejaria pasar cualquier vuelta.
        if self.criterio_estacionario not in CRITERIOS_ESTACIONARIO:
            raise ValueError(
                f"criterio_estacionario={self.criterio_estacionario!r}; use "
                f"'precio' (el de siempre, D26) o 'precio_y_reparto' "
                f"(H-86, D47)")
        t = self.tol_reparto
        if not (isinstance(t, (int, float)) and not isinstance(t, bool)
                and np.isfinite(t) and t > 0):
            raise ValueError(
                f"tol_reparto={t!r}; tiene que ser un numero finito y "
                f"positivo (fraccion de la energia transada de la hora)")


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
    # D24: por que el motor dejo la hora sin resolver, por ejemplo porque
    # vencio el plazo por hora. Vacio es lo de siempre: resuelta, o sin
    # mercado porque faltaba un lado. La hora con motivo llega sin P_star ni
    # ids, de modo que la liquidacion la trata como hora sin mercado.
    motivo:     str   = ""
    # D26: el horizonte con que de verdad se resolvio esta hora por la via
    # acoplada. Con `horizonte_max_acoplado=None` (defecto) vale siempre
    # `t_span_acoplado`, porque hay una sola resolucion; con la parada por
    # estacionario activa, puede ser ese mismo valor doblado una o mas
    # veces. 0.0 es lo de siempre: via alternada, o sin mercado esa hora.
    # D36: es el horizonte de la vuelta que se CONSERVO, no el de la ultima
    # que se intento.
    horizonte_usado: float = 0.0
    # D36/D37: por que paro el acoplado en esta hora. "una_vuelta" con la
    # parada por estacionario apagada (una sola resolucion, la de siempre);
    # con ella activa, "estacionario", "tope" (llego al horizonte maximo sin
    # estacionario), "presupuesto" (la vuelta siguiente no cabia en el
    # presupuesto de evaluaciones) o "fallo_vuelta" (una vuelta no termino
    # con exito y se conservo la anterior, o fallo la primera y la hora
    # queda sin mercado con su motivo). Vacio en la via alternada.
    parada_acoplado: str = ""
    # D47 (H-86): cuanto se movia el REPARTO entre compradores en el ultimo
    # decimo de la vuelta que se conservo, como fraccion de la energia transada
    # de la hora (`_movimiento_relativo(tr.P_t, "energia")`). Se guarda SIEMPRE
    # que la hora se resuelva por la via acoplada, se use o no en el criterio
    # de parada: es barato, y sin el no se puede censar cuantas horas quedaron
    # con el reparto en marcha sin repetir la corrida entera. 0.0 por la via
    # alternada o en la hora sin mercado.
    residuo_reparto: float = 0.0
    # D47: LO QUE COSTO la hora por la via acoplada, que es lo que hay que
    # poner al lado del residuo para decidir el horizonte de produccion y hoy
    # no se puede leer sin volver a correrlo.
    #
    #   segundos      TIEMPO DE PARED del trabajador que la resolvio, medido
    #                 alrededor de la resolucion. Y hay que leerlo por lo que
    #                 es: mientras esa hora corre hay otras `PROCS` corriendo
    #                 en la misma maquina, de modo que NO es tiempo de
    #                 procesador ni lo que costaria esa hora corrida sola. La
    #                 mediana sale inflada frente a una hora aislada, y la SUMA
    #                 de la columna no es la duracion de la corrida sino del
    #                 orden de `PROCS` veces esa duracion. Entre dos
    #                 configuraciones de la MISMA campana, con los mismos
    #                 procesos y la misma maquina, la comparacion si es justa,
    #                 que es para lo que esta.
    #   evaluaciones  evaluaciones del lado derecho sumadas sobre TODAS las
    #                 vueltas de la hora, fallidas incluidas (el `gastado` de
    #                 `_resuelve_acoplado`). **Es la cifra que no depende de la
    #                 maquina**, y la misma cuenta con la que D36 hace su
    #                 presupuesto: la que se cita cuando se compara entre
    #                 maquinas o se publica.
    #
    # Ninguna de las dos decide nada dentro del motor: son mediciones.
    #
    # Con la restriccion de participacion (H-43) las dos suman lo del conjunto
    # completo mas lo del reducido, porque las dos resoluciones las pago esa
    # hora.
    #
    # CUANTO VALEN SIN MERCADO. Valen 0.0 y 0 por la via alternada, que no pasa
    # por aqui, y en la hora que no tiene vendedores o no tiene compradores,
    # que vuelve antes de resolver nada. En cambio la hora que SI se intento y
    # no dio mercado (el integrador sin exito, el guardia de NaN, el conjunto
    # reducido que no resuelve, todos a perdida) guarda su costo de verdad, a
    # proposito: se gasto igual. Ese costo NO TIENE CONSUMIDOR HOY, porque esas
    # horas se anotan en el almacen por `sin_resolver`, que escribe el motivo y
    # nada mas; queda en el resultado por si alguna vez se quiere contar, y
    # quien lo busque en el CSV del censo no lo va a encontrar. No se perdio:
    # nunca se escribio.
    segundos: float = 0.0
    evaluaciones: int = 0
    # D48 a D55, D61 y D63 a D69: lo que la via por reposo sabe de la hora. Los
    # valores por defecto son neutros, de modo que las otras vias no cambian.
    # Los indices son IDENTIFICADORES DE AGENTE, como `retirados`, y no
    # posiciones dentro de la hora. Con participacion (C-151) todo sale del
    # conjunto final de vendedores, el de la vuelta que produjo el resultado.
    #
    #   regimen               uno de `reposo_mercado.REGIMENES`; "" fuera de
    #                         la via por reposo
    #   presupuesto           S, la suma de los precios del reposo (COP/kWh)
    #   precio_comun          ell, el precio del grupo interior o del
    #                         marginal; 0.0 sin mercado (COP/kWh)
    #   precio_uniforme       p_u, el precio marginal uniforme (D51) (COP/kWh)
    #   pi_reposo             precio de cada comprador en el reposo, el pago
    #                         segun puja, forma (I,); `pi_star` es el liquidado
    #   piso_juego            el piso del juego, el del vendedor marginal
    #                         (D63) (COP/kWh)
    #   piso_marginal         igual a `piso_juego`, con el nombre de D63
    #   excluidos             compradores en su techo sin energia («no cabe»)
    #   excluidos_bajo_piso   compradores fuera de la hora por tener el techo
    #                         bajo el piso del juego (D61 parcial)
    #   vendedores_excluidos  vendedores sin ganancia posible con nadie (D61)
    #   vendedores_no_despachados  vendedores con ganancia posible y el piso
    #                         sobre el nivel de cierre de la caminata (D65)
    #   orden_merito          vendedores en el orden de despacho: por piso
    #                         con "piso" (D64), por costo b_j con las otras
    #   n_soluciones          cuantos reposos tiene la hora (D53)
    #   renta_inframarginal   sum_j (p* - piso_j)·s_j (D69) (COP)
    #   parte_juego           (p_medio - p*)·E (D69) (COP)
    #   excedente_optimo      el mejor reparto del mismo volumen (D55) (COP)
    #   excedente_peor        el peor reparto del mismo volumen (D55) (COP)
    #   captura               excedente del reposo / optimo, calculada DESPUES
    #                         de la participacion
    #   retiros_reposo        D67: vendedores que la participacion retiro en
    #                         la via por reposo, sumados los de las vueltas
    #                         reducidas y los de la hora en que se retiran
    #                         todos. Con el piso marginal DEBE SER 0 (teorema
    #                         de cobertura); uno solo es un hallazgo y la
    #                         corrida sale con el codigo 3 de D38. 0 en las
    #                         otras vias
    regimen: str = ""
    presupuesto: float = 0.0
    precio_comun: float = 0.0
    precio_uniforme: float = 0.0
    pi_reposo: Optional[np.ndarray] = None
    piso_juego: float = 0.0
    piso_marginal: float = 0.0
    excluidos: list = field(default_factory=list)
    excluidos_bajo_piso: list = field(default_factory=list)
    vendedores_excluidos: list = field(default_factory=list)
    vendedores_no_despachados: list = field(default_factory=list)
    orden_merito: list = field(default_factory=list)
    n_soluciones: int = 0
    renta_inframarginal: float = 0.0
    parte_juego: float = 0.0
    excedente_optimo: float = 0.0
    excedente_peor: float = 0.0
    captura: float = 0.0
    retiros_reposo: int = 0


def _opciones_reposo(sv) -> tuple:
    """D48: las cuatro opciones del reposo para la tupla del trabajador, en su
    orden. El respaldo del `getattr` es el defecto de `SolverParams`, que solo
    actua con `metodo="reposo"`: un objeto sin los campos es de antes de D48 y
    no pedia esa via."""
    return (getattr(sv, "modo_presupuesto", "sigma"),
            getattr(sv, "sigma_nivel", None),
            getattr(sv, "regla_precio", "uniforme"),
            # D64: el defecto es "piso"; un objeto con "merito" lo traduce el
            # trabajador (alias de "costo", con aviso).
            getattr(sv, "despacho_vendedores", "piso"))


def _opciones_dinamica(sv) -> tuple:
    """D49 / D50: las dos opciones de la dinamica regularizada para la tupla
    del trabajador, en su orden. El respaldo del `getattr` es el defecto de
    `SolverParams`, identico al bit: un objeto sin los campos es de antes de
    D49 y no las pedia."""
    return (getattr(sv, "mu_entropia", 0.0),
            getattr(sv, "nivel_acoplado", "c136"))


# D48: los campos del reposo, en el orden de `HourlyResult`. La recursion de la
# participacion los copia del conjunto reducido con esta lista.
CAMPOS_REPOSO = ("regimen", "presupuesto", "precio_comun", "precio_uniforme",
                 "pi_reposo", "piso_juego", "piso_marginal", "excluidos",
                 "excluidos_bajo_piso", "vendedores_excluidos",
                 "vendedores_no_despachados", "orden_merito", "n_soluciones",
                 "renta_inframarginal", "parte_juego",
                 "excedente_optimo", "excedente_peor", "captura")


def _anota_reposo(res: "HourlyResult", rep, seller_ids, buyer_ids) -> None:
    """D48: pasa el reposo del nucleo al resultado de la hora, con los indices
    del nucleo (posiciones dentro de la hora) traducidos a identificadores de
    agente. Las cotas de optimalidad y la captura no: esas se calculan despues
    de la participacion."""
    res.regimen = str(rep.regimen)
    res.presupuesto = float(rep.S)
    res.precio_comun = 0.0 if rep.ell is None else float(rep.ell)
    res.precio_uniforme = float(rep.p_u)
    res.pi_reposo = np.asarray(rep.pi_reposo, dtype=float).copy()
    res.piso_juego = float(rep.piso)
    res.piso_marginal = float(rep.piso_marginal)
    res.excluidos = [buyer_ids[i] for i in rep.excluidos]
    res.excluidos_bajo_piso = [buyer_ids[i] for i in rep.excluidos_bajo_piso]
    res.vendedores_excluidos = [seller_ids[j]
                                for j in rep.vendedores_excluidos]
    res.vendedores_no_despachados = [seller_ids[j] for j in
                                     rep.vendedores_no_despachados]
    res.orden_merito = [seller_ids[j] for j in rep.orden_merito]
    res.n_soluciones = int(rep.n_soluciones)
    # D69: la prima descompuesta.
    res.renta_inframarginal = float(rep.renta_inframarginal)
    res.parte_juego = float(rep.parte_juego)


# ── Worker (top-level para pickle en multiprocessing) ────────────────────────

# D26: umbral de la parada por estacionario del solucionador acoplado. El
# precio se considera estacionario cuando se mueve menos de esta fraccion de
# su recorrido total en el ultimo decimo de la trayectoria, la misma medida
# que el motor ya guarda como `norm_rel_final`. Constante de modulo: la
# funcion que decide la parada (`_resuelve_acoplado`) la toma como valor por
# defecto de su argumento `tol_estacionario`, y quien necesite otro valor
# para una prueba pasa ese argumento, nunca mutando esta constante.
TOL_ESTACIONARIO = 0.01

# D47 (H-86): umbral de la medida del REPARTO, la otra mitad del criterio de
# parada. El reparto se considera quieto cuando la mayor pareja (j, i) se mueve,
# en el ultimo decimo de la trayectoria, menos de esta fraccion de la energia
# transada de la hora. Misma regla que TOL_ESTACIONARIO: constante de modulo,
# valor por defecto del argumento de `_resuelve_acoplado`, y quien necesite otro
# umbral lo pasa en vez de mutarla.
TOL_REPARTO = 0.01

# D47: que mira el criterio de parada del acoplado. "precio" es el de siempre
# (D26), identico al bit; "precio_y_reparto" exige que las DOS medidas esten
# quietas, porque un precio quieto no implica un reparto quieto: en la matriz de
# trece corridas, la hora 109 de E0 paro por estacionario con residuo 0,0065 y
# su reparto estaba lejos del punto final (H-86).
CRITERIOS_ESTACIONARIO = ("precio", "precio_y_reparto")

# D36: el presupuesto de la parada por estacionario, calibrado el 2026-09-14
# en la maquina de trabajo sobre la hora mas lenta medida, la 4184 de la
# frontera M1 con la generacion por siete (`paso_a_paso.carga`, parametros de
# produccion: rtol = atol = 1e-6, 150 puntos, un solo proceso, una sola
# resolucion por horizonte):
#
#   horizonte 0,05:  141,4 (s)   1 292 398 evaluaciones   34 564 jacobianas
#   horizonte 0,1:   365,9 (s)   3 310 324 evaluaciones   87 627 jacobianas
#
# Doblar el horizonte multiplica el trabajo por 3 310 324 / 1 292 398 = 2,56:
# es FACTOR_CRECIMIENTO_DOBLEZ, lo que se supone que costara la vuelta
# siguiente cuando solo hay una vuelta medida. Con dos o mas se usa el
# cociente medido entre las dos ultimas.
#
# La velocidad medida es de unas 9 073 evaluaciones por segundo (4 602 722 en
# 507,3 (s)), de modo que 5 300 000 evaluaciones son unos 584 (s), el 65 % del
# plazo por hora de 15 (min) (D24): una hora que agota el presupuesto termina
# antes de que el plazo la mate, y conserva su ultima vuelta buena. Es un
# conteo y no un reloj: corta en el mismo sitio en cualquier maquina, aunque
# los segundos cambien con ella. El plazo por hora queda como red.
FACTOR_CRECIMIENTO_DOBLEZ = 2.56
PRESUPUESTO_EVAL_ACOPLADO = 5_300_000

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


# ── Plazo por hora del lazo paralelo (D24) ───────────────────────────────────
#
# POR QUE UN TABLERO Y NO `future.running()`. El ejecutor marca un futuro como
# `running()` en cuanto lo pasa a su cola de llamadas, que admite
# `max_workers + 1` trabajos, antes de que ningun trabajador lo tome. Medido
# el 2026-09-13 con un trabajador y cuatro horas de 1,5 s: la cuarta aparece
# `running()` a los 1,84 s y empieza de verdad a los 4,84 s. Con el plazo
# contado desde `running()`, tres de las cuatro vencerian sin haberse
# atascado. Por eso el propio trabajador marca en un arreglo compartido, una
# casilla por hora, que EMPIEZA a resolverla, y el lazo toma como arranque el
# primer latido en que ve la marca. El retraso es de un latido a lo sumo, y
# solo alarga el plazo: nunca hace vencer una hora antes de tiempo.

_TABLERO = None


def _abre_tablero(tablero):
    """Inicializador de cada trabajador (D24): recibe el tablero compartido."""
    global _TABLERO
    _TABLERO = tablero


def _corre_y_marca(funcion, i, job):
    """Envoltura del trabajo (D24): marca que la hora i empieza y la resuelve."""
    _TABLERO[i] = 1
    return funcion(job)


def _mata_trabajadores(ex):
    """Cierra el pool matando a sus trabajadores, como C-156.

    Un trabajador atascado esta dentro del integrador, es decir en codigo
    nativo, y no atiende la cancelacion: con `shutdown` a secas el interprete
    lo esperaria para siempre al salir. Se toca la interioridad del ejecutor a
    proposito, porque no expone otra via.
    """
    procesos = list((getattr(ex, "_processes", None) or {}).values())
    # Bajo `fork` (Linux, el servidor) el hilo gestor del pool viejo tiene que
    # haber terminado antes de abrir el nuevo: si sigue vivo, los hijos del
    # pool nuevo heredan el extremo de lectura de su tuberia, y Python 3.12 o
    # posterior avisa de bifurcar un proceso con varios hilos. Se guarda antes
    # del cierre porque `shutdown` suelta la referencia (tarea 18, fix1, C.4).
    gestor = getattr(ex, "_executor_manager_thread", None)
    for p in procesos:
        if p.is_alive():
            p.terminate()
    for p in procesos:
        p.join(timeout=10)
        if p.is_alive():
            print(f"    [D24] AVISO: el trabajador {p.pid} sigue vivo tras "
                  f"terminarlo", flush=True)
    ex.shutdown(wait=False, cancel_futures=True)
    if gestor is not None:
        gestor.join(timeout=30)
        if gestor.is_alive():
            print("    [D24] AVISO: el hilo gestor del pool viejo sigue vivo "
                  "tras 30 (s); el pool nuevo se abre igual", flush=True)


def _resuelve_con_plazo(funcion, jobs, procesos, plazo_s, hace_vencida,
                        latido: float = 5.0, bar=None):
    """Resuelve las horas en un pool con plazo POR HORA (D24).

    Conserva la ventana acotada de sometimiento de CAL-43e. El plazo se mide
    desde que la hora empieza a correr, no desde que se somete: con la
    ventana hay horas esperando en cola que, si no, vencerian sin empezar. El
    arranque lo marca el propio trabajador en el tablero; ver arriba por que
    `future.running()` no sirve para eso.

    La hora vencida no se espera: `hace_vencida(job)` fabrica su resultado
    (sin mercado, con motivo) y la corrida sigue con las demas. Y el pool se
    renueva en el acto: se matan sus trabajadores, como en C-156, y las horas
    que estaban en vuelo se someten de nuevo a un pool nuevo. Sin eso, el
    trabajador atascado ocuparia su plaza hasta el final, la corrida perderia
    un trabajador por cada hora vencida y, vencidas tantas como trabajadores,
    esperaria para siempre horas que ya no pueden empezar. Rehacer una hora da
    el mismo resultado, porque el trabajo es determinista; solo se pierde lo
    que llevaba hecho.

    Al cerrar, si alguna vencio, se matan los trabajadores; si no, el cierre
    es el normal. Con `plazo_s=None` es exactamente el lazo de antes: sin
    tablero, sin envoltura, sin latido y sin renovar.

    Devuelve `({k: resultado}, [k de las horas vencidas, en orden])`.
    `jobs[i][0]` es `k`, como en los argumentos de `_run_hour_worker`.
    """
    jobs = list(jobs)
    rmap, vencidas = {}, []
    con_plazo = plazo_s is not None
    ctx = multiprocessing.get_context()
    tablero = ctx.RawArray("b", len(jobs)) if con_plazo else None

    def _abre():
        if not con_plazo:
            return ProcessPoolExecutor(max_workers=procesos)
        return ProcessPoolExecutor(max_workers=procesos, mp_context=ctx,
                                   initializer=_abre_tablero,
                                   initargs=(tablero,))

    ex = _abre()
    try:
        ventana = max(4 * (getattr(ex, "_max_workers", 0) or 1), 64)
        pendientes = iter(enumerate(jobs))
        activos = {}                       # futuro -> (i, job)
        arranque = {}                      # futuro -> instante en que corre

        def _somete(i, j):
            f = (ex.submit(_corre_y_marca, funcion, i, j) if con_plazo
                 else ex.submit(funcion, j))
            activos[f] = (i, j)

        def _llena():
            while len(activos) < ventana:
                siguiente = next(pendientes, None)
                if siguiente is None:
                    return
                _somete(*siguiente)

        def _anota(r):
            rmap[r.k] = r
            if bar is not None:
                bar.update(1)

        _llena()
        while activos:
            hechos, _ = wait(set(activos),
                             timeout=latido if con_plazo else None,
                             return_when=FIRST_COMPLETED)
            for f in hechos:
                activos.pop(f)
                arranque.pop(f, None)
                _anota(f.result())
            _llena()
            if not con_plazo:
                continue

            ahora = time.monotonic()
            vencen = []
            for f, (i, _j) in activos.items():
                if f not in arranque and tablero[i]:
                    arranque[f] = ahora
                if f in arranque and ahora - arranque[f] > plazo_s:
                    vencen.append(f)
            # Un resultado que llego entre la espera y esta comprobacion ya
            # esta hecho: se recoge como terminado y no se tira (tarea 18,
            # fix1, C.5). Al sacarlo de `activos` queda sitio en la ventana, y
            # hay que rellenarla: si no, el lazo podria vaciarse con horas aun
            # sin someter.
            listos = [f for f in vencen if f.done()]
            for f in listos:
                activos.pop(f)
                arranque.pop(f, None)
                _anota(f.result())
            vencen = [f for f in vencen if f not in listos]
            if listos:
                _llena()
            if not vencen:
                continue

            for f in vencen:
                _i, j = activos.pop(f)
                arranque.pop(f)
                r = hace_vencida(j)
                _anota(r)
                vencidas.append(r.k)
            # Lo que termino entre el latido y ahora se recoge antes de matar;
            # lo que sigue en vuelo o en cola vuelve a someterse, en su orden.
            relanza = []
            for f, ij in list(activos.items()):
                if f.done():
                    _anota(f.result())
                else:
                    relanza.append(ij)
            _mata_trabajadores(ex)
            activos.clear()
            arranque.clear()
            ex = _abre()
            for i, j in sorted(relanza, key=lambda ij: ij[0]):
                tablero[i] = 0             # su arranque anterior ya no cuenta
                _somete(i, j)
            _llena()
    finally:
        if vencidas:
            _mata_trabajadores(ex)
        else:
            ex.shutdown(wait=True)
    return rmap, sorted(vencidas)


def _horas_representativas(p2p_results, D, G_klim, max_hours: int = 2):
    """Las horas que `run_convergence` vuelve a resolver para dibujarlas.

    La de mayor volumen P2P (caso excedente) y la de mayor deficit
    comunitario (caso importacion), sin repetir y en ese orden.

    NUNCA UNA HORA VENCIDA (D24; tarea 18, fix1, C.3). `run_convergence`
    resuelve en el proceso principal, sin plazo. Si eligiera la hora que el
    plazo dio por perdida, colgaria la corrida justo ahi, bajo `--analysis`.
    La de mayor volumen ya la excluia sin querer, porque la hora vencida no
    trae `P_star`; la de mayor deficit no. Se saltan las dos por el motivo.
    Sin horas vencidas la eleccion es la de antes.
    """
    vencidas = {int(r.k) for r in p2p_results if getattr(r, "motivo", "")}
    activas = [(r.k, float(np.sum(r.P_star))) for r in p2p_results
               if r.P_star is not None and np.sum(r.P_star) > 1e-6
               and int(r.k) not in vencidas]
    if not activas:
        return []
    # Hora con mas kWh P2P (caso excedente comunitario)
    horas = [max(activas, key=lambda x: x[1])[0]]
    # Hora con mayor deficit comunitario (caso importacion)
    deficit = [(k, float(np.sum(np.maximum(D[:, k] - G_klim[:, k], 0))))
               for k in range(D.shape[1]) if k not in vencidas]
    if deficit:
        horas.append(max(deficit, key=lambda x: x[1])[0])
    return list(dict.fromkeys(horas[:max_hours]))


def _trayectoria_finita(tr) -> bool:
    """D37 (re-revision del arreglo final): cierto si los precios de la
    trayectoria (`pi_t`), las cantidades finales (`P_star`) y la trayectoria
    del reparto (`P_t`) son todos finitos. Una vuelta con `success=True` y un
    precio no finito daba un recorrido `nan`, que la comprobacion de
    estacionario contaba como estacionario: la vuelta rota desplazaba a la
    buena.

    D47: `P_t` entra en la tupla porque desde entonces NO es un adorno de la
    trayectoria: decide la parada con el criterio nuevo y viaja al almacen como
    residuo del reparto. Un no finito ahi daria una medida `nan`, que no es
    menor ni mayor que el umbral, de modo que ninguna vuelta seria estacionaria
    y la hora quemaria el presupuesto entero sin que nada dijera por que; y con
    el criterio de hoy, esa hora podria acabar marcada como no resuelta aunque
    el motor la hubiera resuelto."""
    for nombre in ("pi_t", "P_star", "P_t"):
        v = getattr(tr, nombre, None)
        if v is None:
            continue
        v = np.asarray(v, dtype=float)
        if v.size and not np.all(np.isfinite(v)):
            return False
    return True


def _movimiento_relativo(traj, normaliza: str = "recorrido") -> float:
    """Cuanto se mueve una trayectoria en su ULTIMO DECIMO, en relativo (D47).

    `traj` admite las dos formas del acoplado: el precio, (I, n_t), y el
    reparto, (J, I, n_t), que se aplana a una fila por pareja (j, i). El
    movimiento es el mayor cambio de una fila entre la ultima columna y la de
    un decimo antes, la misma cola que el criterio de D26 usaba para el precio.

    QUE CAMBIA SEGUN LA MAGNITUD, y no es un detalle:

      "recorrido" divide por el mayor recorrido de una fila (su maximo menos su
          minimo). Es la medida del PRECIO de D26, y esta funcion la reproduce
          operacion por operacion, de modo que con el criterio "precio" el
          resultado es identico al bit al de antes de D47.
      "energia" divide por la ENERGIA TRANSADA de la hora, la suma de la ultima
          columna. Es la medida del REPARTO, y la eleccion importa: el reparto
          no tiene un recorrido propio que signifique algo (una pareja que
          nunca recibio nada tiene recorrido cero y otra que se lo lleva todo
          lo tiene enorme), mientras que lo que decide si la hora esta hecha es
          CUANTA ENERGIA SE SIGUE MOVIENDO frente a la que se reparte. Con la
          suma casi nula, el divisor se acota a 1e-12 en vez de dividir por
          cero; esa hora no tiene mercado que repartir y el llamador ya la
          trata aparte.

    Con un solo punto (la trayectoria que D41 corta) la cola vale uno, el
    movimiento es cero y la medida es cero, igual que antes.
    """
    a = np.asarray(traj, dtype=float)
    if a.ndim == 3:                      # (J, I, n_t) -> una fila por pareja
        a = a.reshape(-1, a.shape[-1])
    cola = int(max(1, a.shape[1] // 10))
    mov = float(np.max(np.abs(a[:, -1] - a[:, -cola])))
    if normaliza == "recorrido":
        rec = float(np.max(np.abs(a.max(axis=1) - a.min(axis=1))))
        return mov / rec if rec > 1e-12 else 0.0
    if normaliza != "energia":
        raise ValueError(f"normaliza={normaliza!r}; use 'recorrido' (el "
                         f"precio, D26) o 'energia' (el reparto, D47)")
    return mov / max(float(np.sum(a[:, -1])), 1e-12)


def _resuelve_acoplado(
        *, G_net_j, D_net_i, a_j, b_j, lam_j, theta_j, G_klim_i, lam_i,
        theta_i, etha_i, pi_gs, pi_gb, tau, tau_buyers, n_points,
        buyer_competition, guarda_tr, t_span_aco, rtol_aco,
        horizonte_max_aco, tol_estacionario: float = TOL_ESTACIONARIO,
        presupuesto_eval: Optional[int] = None,
        factor_crecimiento: float = FACTOR_CRECIMIENTO_DOBLEZ,
        arranque: str = "iguales",
        criterio: str = "precio", tol_reparto: float = TOL_REPARTO,
        mu_entropia: float = 0.0, nivel: str = "c136"):
    """Resuelve una hora por la via acoplada (CAL-48), con las dos palancas
    de la sonda de H-79 (D35, D26).

    `mu_entropia` y `nivel` (D49, D50) son las opciones de la dinamica
    regularizada de `solve_coupled_for_hour`, las mismas en todas las
    vueltas; con sus defectos (0.0, "c136") la resolucion es la de siempre,
    al bit.

    `rtol_aco` aprieta la tolerancia relativa del integrador
    (`solve_coupled_for_hour`); la absoluta no se toca (H-51). Con
    `horizonte_max_aco=None` hay una sola resolucion con `t_span_aco`,
    identica a la de antes de D26. Con `horizonte_max_aco` activo, la parada
    es por estacionario: cada vuelta resuelve DESDE EL ARRANQUE con el
    horizonte doble (no hace falta arranque en caliente, el resultado es
    determinista) hasta que el precio se mueva menos de `tol_estacionario`
    de su recorrido en el ultimo decimo, o hasta pasar `horizonte_max_aco`.

    `tol_estacionario` tiene por defecto la constante de modulo
    `TOL_ESTACIONARIO`; una prueba que necesite otro umbral pasa este
    argumento, sin mutar la constante (que seguiria rigiendo cualquier otra
    hora que se resolviera en el mismo proceso).

    D36, LA VUELTA BUENA Y EL PRESUPUESTO. Con la parada activa, la funcion
    guarda la ultima vuelta que resolvio bien y suma las evaluaciones del
    integrador (`nfev`) de cada una. Antes de doblar estima lo que costaria
    la vuelta siguiente (las evaluaciones de la ultima por un factor de
    crecimiento: el cociente medido entre las dos ultimas si hay dos, nunca
    menor que uno; si solo hay una, `factor_crecimiento`) y NO LA EMPIEZA si
    lo gastado mas lo estimado pasa de `presupuesto_eval` (None: la
    constante `PRESUPUESTO_EVAL_ACOPLADO`). Asi ninguna hora con mercado
    llega al plazo por hora (D24) por culpa de D26: el trabajador que el
    plazo mata no tiene canal para devolver la vuelta que ya tenia.

    D37, LA VUELTA QUE FALLA. Si una vuelta devuelve `success=False`, o una
    trayectoria con precios o cantidades no finitos (`_trayectoria_finita`),
    la hora se queda con la ultima vuelta buena. Si fallo la primera no hay
    ninguna,
    y se devuelve la trayectoria fallida: el llamador la deja sin mercado,
    con su motivo. Una EXCEPCION no se atrapa aqui: sube al trabajador, que
    la anota (C-190) y la corrida la cuenta para su codigo de salida (D38).

    El presupuesto y el factor solo actuan con la parada activa. Con
    `horizonte_max_aco=None` hay una sola resolucion, identica al bit a la de
    antes de D26.

    `arranque` (H-85, D45) es la regla de la oferta inicial del acoplado, la
    misma en todas las vueltas: "iguales" (defecto, el de siempre) o
    "factible".

    D47, QUE MIRA EL CRITERIO. Con `criterio="precio"` (defecto) la hora es
    estacionaria cuando el precio se mueve poco, que es el criterio de D26,
    identico al bit. Con "precio_y_reparto" lo es solo si ADEMAS el reparto
    entre compradores esta quieto, medido con `_movimiento_relativo` sobre
    `tr.P_t` y normalizado por la energia transada de la hora, contra
    `tol_reparto`. Existe porque un precio quieto no implica un reparto
    quieto: en la hora 109 de E0 el precio se movia de 721,5 a 725,7
    (COP/kWh) entre los horizontes 0,05 y 2,0 mientras el reparto pasaba de
    cuatro compradores casi iguales a uno solo con todo (H-86). El resto de
    la maquinaria (doblar, tope, presupuesto, vuelta buena) no cambia: lo
    unico que cambia es CUANDO se declara estacionaria una vuelta.

    Devuelve `(tr, h, parada, gastado)`: la trayectoria que se conserva
    (`CoupledTrajectory`), el horizonte de ESA vuelta, para
    `HourlyResult.horizonte_usado`; por que paro, para
    `HourlyResult.parada_acoplado`: "una_vuelta" (parada apagada),
    "estacionario", "tope", "presupuesto" o "fallo_vuelta"; y las
    evaluaciones del integrador que gasto la hora en TODAS sus vueltas,
    fallidas incluidas, para que el reintento de H-43 reciba solo lo que
    queda del presupuesto (re-revision del arreglo final).
    """
    # D47: un criterio mal escrito no puede degradar en silencio al criterio
    # flojo, que es lo que haria la comparacion de mas abajo con un valor
    # desconocido. Las dos entradas de produccion (`SolverParams` y la tupla
    # del trabajador) ya lo validan; esto cubre a quien llame aqui directo.
    if criterio not in CRITERIOS_ESTACIONARIO:
        raise ValueError(f"criterio={criterio!r}; use 'precio' (el de siempre, "
                         f"D26) o 'precio_y_reparto' (H-86, D47)")
    h = float(t_span_aco)
    presupuesto = (PRESUPUESTO_EVAL_ACOPLADO if presupuesto_eval is None
                   else int(presupuesto_eval))
    buena = None          # (tr, h) de la ultima vuelta que resolvio bien
    evals = []            # nfev de cada vuelta buena, en orden
    gastado = 0
    while True:
        tr = solve_coupled_for_hour(
            G_net_j=G_net_j, D_net_i=D_net_i, a_j=a_j, b_j=b_j,
            lam_j=lam_j, theta_j=theta_j, G_klim_i=G_klim_i,
            lam_i=lam_i, theta_i=theta_i, etha_i=etha_i,
            pi_gs=pi_gs, pi_gb=pi_gb, tau_sellers=tau,
            tau_buyers=tau_buyers, t_span=(0.0, h),
            n_points=n_points, rtol=rtol_aco,
            # CAL-49: la via acoplada no recibia la forma del termino de
            # competencia, de modo que elegirla no la afectaba y las dos
            # vias podian correr con formas distintas sin avisar.
            buyer_competition=buyer_competition,
            # Los multiplicadores dicen QUE RESTRICCION esta mordiendo. Sin
            # ellos, la figura de convergencia enseña el precio deteniendose
            # sin poder decir por que se detiene ahi.
            devuelve_multiplicadores=bool(guarda_tr),
            # H-85 / D45: la regla del arranque; "iguales" es el de siempre.
            arranque=arranque,
            # D49 / D50: la dinamica regularizada; apagada por defecto.
            mu_entropia=mu_entropia, nivel=nivel)
        n = int(getattr(tr, "nfev", 0) or 0)
        gastado += n
        if horizonte_max_aco is None:
            # La parada apagada: una sola resolucion, la de siempre. Si no
            # termino con exito, el llamador deja la hora sin mercado.
            return tr, h, "una_vuelta", gastado
        if (not bool(getattr(tr, "success", True))
                or not _trayectoria_finita(tr)):
            # D37: la vuelta fallida no reemplaza a la buena. Tampoco la que
            # termino "con exito" con precios o cantidades no finitos: su
            # recorrido `nan` pasaria por estacionario (re-revision).
            if buena is None:
                return tr, h, "fallo_vuelta", gastado
            return buena[0], buena[1], "fallo_vuelta", gastado
        evals.append(n)
        buena = (tr, h)
        # La medida del precio, la de D26, con la misma cuenta de siempre.
        estacionario = (_movimiento_relativo(tr.pi_t, "recorrido")
                        <= tol_estacionario)
        # D47: con el criterio nuevo, tambien la del reparto. Las dos, o
        # ninguna: la hora no esta hecha mientras la energia siga cambiando
        # de manos, aunque el precio ya no se mueva.
        if estacionario and criterio == "precio_y_reparto":
            estacionario = (_movimiento_relativo(tr.P_t, "energia")
                            <= tol_reparto)
        if estacionario:
            return tr, h, "estacionario", gastado
        if 2.0 * h > horizonte_max_aco + 1e-12:
            return tr, h, "tope", gastado
        # D36: lo que costaria la vuelta siguiente, que no se empieza si no
        # cabe. El cociente medido nunca baja de uno: doblar el horizonte no
        # abarata la integracion, y un cociente menor seria ruido.
        if len(evals) >= 2 and evals[-2] > 0:
            crece = max(1.0, evals[-1] / evals[-2])
        else:
            crece = float(factor_crecimiento)
        if gastado + evals[-1] * crece > presupuesto:
            return tr, h, "presupuesto", gastado
        h *= 2.0


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
    # D35/D26: las dos palancas del acoplado que activa el veredicto de la
    # sonda de H-79. Apagadas por defecto (1e-6, None) e identicas al bit a
    # los llamadores que aun no las conocen.
    if len(args) == 26:
        args = args + (1e-6, None)
    # D36: el presupuesto de evaluaciones de la parada por estacionario. None
    # es la constante de modulo, y solo actua con la parada activa, de modo
    # que una tupla de 28 campos resuelve igual que antes.
    if len(args) == 28:
        args = args + (None,)
    # H-85 / D45: la regla del arranque del acoplado. El shim rellena con
    # "iguales", que era el defecto cuando esas tuplas se escribieron: una
    # tupla de 29 campos resuelve hoy igual que antes de D45, aunque el defecto
    # de `SolverParams` haya pasado a "factible". Es lo que hace que las
    # pruebas que arman la tupla a mano sigan midiendo lo que median.
    if len(args) == 29:
        args = args + ("iguales",)
    # D47: el criterio de parada y su umbral. "precio" es el de siempre, de
    # modo que una tupla de 30 campos resuelve igual que antes de D47.
    if len(args) == 30:
        args = args + ("precio", TOL_REPARTO)
    # D48: las cuatro opciones de la via por reposo. El shim rellena con los
    # defectos de `SolverParams`, que solo actuan con `metodo="reposo"`: una
    # tupla de 32 campos resuelve exactamente igual que antes de D48 por las
    # otras vias. D64 (2026-09-17): el despacho que rellena pasa de "merito" a
    # "piso", el defecto de produccion; una tupla que traiga "merito" escrito
    # lo resuelve como "costo" (alias, con aviso).
    if len(args) == 32:
        args = args + ("sigma", None, "uniforme", "piso")
    # D49 / D50: las dos opciones de la dinamica regularizada del acoplado. El
    # shim rellena con sus defectos, que la apagan: una tupla de 36 campos
    # resuelve exactamente igual que antes de D49.
    if len(args) == 36:
        args = args + (0.0, "c136")

    (k, G_klim_k, D_k, G_raw_k, seller_ids, buyer_ids,
     a_all, b_all, lam_all, theta_all, etha_all,
     pi_gs, pi_gb, tau, tau_buyers, t_span, n_points,
     min_iter, tol, max_iter, ode_method, buyer_competition,
     metodo, t_span_aco, pi_gb_j, guarda_tr,
     rtol_aco, horizonte_max_aco, presupuesto_aco, arranque_aco,
     criterio_aco, tol_reparto_aco,
     modo_pres, sigma_nivel, regla_precio, despacho_vend,
     mu_entropia, nivel_aco) = args
    # D48: la via y las opciones del reposo, en todas las horas y antes de
    # mirar si hay mercado, como el arranque y el criterio de abajo. D64: el
    # alias "merito" pasa a "costo" antes de validar.
    if metodo not in METODOS:
        raise ValueError(f"metodo {metodo!r}; use uno de {METODOS}")
    despacho_vend = normaliza_despacho(despacho_vend)
    _valida_reposo(modo_pres, sigma_nivel, regla_precio, despacho_vend)
    # D49 / D50: y las de la dinamica regularizada, igual.
    _valida_dinamica(mu_entropia, nivel_aco)
    # H-85 / D45: una regla desconocida falla en voz alta en todas las horas,
    # tambien en las que no tienen mercado, y no como excepcion del acoplado
    # por hora (C-190). `SolverParams` ya la valida; esto cubre la tupla
    # armada a mano.
    if arranque_aco not in ARRANQUES:
        raise ValueError(f"arranque del acoplado {arranque_aco!r}; use "
                         f"'factible' o 'iguales' (H-85, D45)")
    # D47: y lo mismo con el criterio de parada.
    if criterio_aco not in CRITERIOS_ESTACIONARIO:
        raise ValueError(f"criterio del acoplado {criterio_aco!r}; use "
                         f"'precio' o 'precio_y_reparto' (H-86, D47)")

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
    # D36 (re-revision): las evaluaciones del integrador que lleva gastadas
    # esta hora, para que el reintento de H-43 reciba solo lo que queda.
    gastado_hora = 0
    # D47: cuanto se movia el reparto en la vuelta que se conserva. Cero por la
    # via alternada, que no produce trayectoria de la que medirlo.
    residuo_rep = 0.0
    # D47: y lo que costo la hora, en tiempo de reloj y en evaluaciones.
    segundos_hora = 0.0
    evaluaciones_hora = 0
    if metodo == "acoplado":
        _reloj = time.monotonic()
        try:
            tr, h, parada, gastado_hora = _resuelve_acoplado(
                G_net_j=G_net_j, D_net_i=D_net_i, a_j=a_j, b_j=b_j,
                lam_j=lam_j, theta_j=theta_j, G_klim_i=G_klim_i,
                lam_i=lam_i, theta_i=theta_i, etha_i=etha_i,
                pi_gs=pi_gs, pi_gb=pi_gb, tau=tau, tau_buyers=tau_buyers,
                n_points=n_points, buyer_competition=buyer_competition,
                guarda_tr=guarda_tr, t_span_aco=t_span_aco,
                rtol_aco=rtol_aco, horizonte_max_aco=horizonte_max_aco,
                presupuesto_eval=presupuesto_aco,
                # H-85 / D45: la regla del arranque de la oferta.
                arranque=arranque_aco,
                # D47: que mira el criterio de parada, y con que umbral.
                criterio=criterio_aco, tol_reparto=tol_reparto_aco,
                # D49 / D50: la dinamica regularizada; apagada por defecto.
                mu_entropia=mu_entropia, nivel=nivel_aco)
        except Exception as e:
            # Fallar en voz alta (regla principal de CLAUDE.md, fila
            # "cifras que salen sin error pero son falsas"): antes esta hora
            # volvia "sin mercado" indistinguible de J=0/I=0 o del guardia
            # de NaN, sin dejar rastro de que revento. Una hora que falla no
            # puede tumbar la corrida (5160 horas), pero tampoco puede
            # quedar muda. `motivo` no vacio hace que la liquidacion y el
            # almacen la traten como "sin resolver" con su causa, igual que
            # ya hacen con las horas que vencen el plazo (D24).
            res.motivo = (f"excepcion del acoplado: "
                         f"{type(e).__name__}: {e}")[:200]
            res.horizonte_usado = 0.0
            # D47: el tiempo si se sabe; las evaluaciones no, porque la
            # excepcion se lleva por delante la cuenta que devolvia.
            res.segundos = time.monotonic() - _reloj
            return res
        segundos_hora = time.monotonic() - _reloj
        evaluaciones_hora = int(gastado_hora)
        # D36/D37: por que paro el acoplado ("una_vuelta" con la parada
        # apagada). Se anota tambien en la hora que sale sin mercado.
        res.parada_acoplado = parada
        # El integrador avisa cuando no logra resolver. Antes de CAL-48 esa
        # bandera no se miraba y la hora entraba igual con lo que el solver
        # tuviera a mano. Se marca como sin mercado, que es lo que ya hace
        # esta funcion con las horas que producen NaN.
        #
        # D37: aqui solo llega la PRIMERA vuelta fallida (la unica, con la
        # parada apagada): si fallo una posterior, `_resuelve_acoplado` ya
        # devolvio la ultima vuelta buena. Hasta D37 esta hora volvia sin
        # motivo, indistinguible de una sin vendedores o sin compradores. Los
        # numeros no cambian, sigue sin mercado; ahora dice por que.
        #
        # Re-revision: con la parada activa, una trayectoria no finita cuenta
        # como vuelta fallida (D37); aqui solo llega si era la primera. Con la
        # parada apagada no se mira aqui: esa hora sigue por el guardia de NaN
        # de mas abajo, como siempre, identica al bit.
        fallida = (not bool(getattr(tr, "success", True))
                   or (horizonte_max_aco is not None
                       and not _trayectoria_finita(tr)))
        if fallida:
            res.motivo = f"integrador sin exito al horizonte {h:g}"
            res.horizonte_usado = 0.0
            # D47: la hora no da mercado, pero COSTO lo que costo, y eso es
            # parte del precio de la configuracion que se este midiendo.
            res.segundos = float(segundos_hora)
            res.evaluaciones = int(evaluaciones_hora)
            return res
        P_star = np.asarray(tr.P_star, dtype=float)
        pi_i = np.clip(np.asarray(tr.pi_star, dtype=float), pi_gb, pi_gs)
        # Cuánto se mueve el precio en el último décimo frente a todo su
        # recorrido: cerca de cero es estacionario. Se guarda donde el lazo
        # alternado guardaba su residuo, para que el diagnóstico de la
        # corrida siga teniendo una sola columna de convergencia.
        iter_count = int(tr.pi_t.shape[1])
        norm_rel = _movimiento_relativo(tr.pi_t, "recorrido")
        # D47: y la misma medida sobre el REPARTO, que se guarda siempre,
        # entre en el criterio de parada o no. Es lo que permite censar
        # despues cuantas horas quedaron con la energia todavia cambiando de
        # manos (H-86), sin volver a resolverlas.
        residuo_rep = _movimiento_relativo(tr.P_t, "energia")
        # D26: el horizonte con que de verdad se resolvio esta hora.
        res.horizonte_usado = h
        if guarda_tr:
            res.tr = tr
    elif metodo == "reposo":
        # D48: el reposo del juego regularizado en forma cerrada (sec. 5.1 de
        # la especificacion, pasos 1 a 6 y 8), con LAS MISMAS ENTRADAS que
        # recibe la via acoplada en esta hora: el excedente neto de cada
        # vendedor, el deficit neto de cada comprador, el costo b_j, el techo
        # de cada comprador (`pi_gs`, vector o escalar, C-146) y el piso de
        # cada vendedor (`pi_gb_j`, H-49). Sin el vector, el escalar de
        # siempre. La diferencia con el acoplado es el piso del JUEGO: al
        # acoplado entra el minimo de todos los vendedores de la hora (el
        # escalar `pi_gb`), y el nucleo toma el del vendedor MARGINAL (D63) a
        # partir del vector.
        #
        # Nada que integrar: `iters_used`, `norm_rel_final`,
        # `residuo_reparto`, `horizonte_usado` y `evaluaciones` quedan en
        # cero, y la parada se anota como "reposo".
        _reloj = time.monotonic()
        res.parada_acoplado = "reposo"
        piso_rep = (np.asarray(pi_gb_j, dtype=float) if pi_gb_j is not None
                    else float(pi_gb))
        try:
            # CAL-32 (a_j = 0) y el polvo negativo de los netos, antes del
            # nucleo y dentro del mismo `try`: un a_j no nulo sale por C-190.
            s_rep, d_rep = _entradas_reposo(a_j, G_net_j, D_net_i)
            rep = resuelve_reposo(
                s_rep, d_rep, b_j, pi_gs, piso_rep,
                modo_presupuesto=modo_pres, sigma=sigma_nivel,
                # El Algoritmo 3 literal exige techo escalar; el nucleo
                # comprueba que todos los techos sean ese valor.
                pi_gs=(float(np.max(pi_gs)) if modo_pres == "algoritmo3"
                       else None),
                regla_precio=regla_precio,
                despacho_vendedores=despacho_vend)
        except ValueError as e:
            # Fallar en voz alta sin tumbar la corrida, como C-190: el nucleo
            # lanza ValueError cuando se rompe una identidad de la hora
            # (`_comprueba`) o cuando el presupuesto no cabe en la banda (el
            # modo "c136" con H-32). La hora queda sin mercado con su motivo,
            # la linea [C-190] la cuenta y el codigo de salida de D38 es 3.
            # Solo ValueError: cualquier otra excepcion es un defecto del
            # motor y sube.
            res.motivo = (f"{PREFIJO_EXCEPCION_REPOSO}: "
                          f"{type(e).__name__}: {e}")[:200]
            res.segundos = time.monotonic() - _reloj
            # El reposo no integra nada: las evaluaciones del integrador son
            # cero, como en el resto del ramal (revision final, menor 4).
            res.evaluaciones = 0
            return res
        segundos_hora = time.monotonic() - _reloj
        _anota_reposo(res, rep, seller_ids, buyer_ids)
        if rep.regimen in ("sin_mercado", "sin_ganancia"):
            # D61: la hora sin ganancia posible no tiene mercado, sin error y
            # con su causa en `regimen`. Vuelve como la hora sin mercado de
            # siempre (sin `P_star`), para que la liquidacion la trate igual.
            res.segundos = float(segundos_hora)
            return res
        P_star = np.asarray(rep.P, dtype=float)
        # El precio con que se liquida a cada comprador (D51): el uniforme
        # conservador del ingreso, o el de puja si se pidio. El del reposo
        # queda en `pi_reposo`.
        pi_i = np.asarray(rep.p_liquidado, dtype=float)
        iter_count = 0
        norm_rel = 0.0
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
        # D47: esta hora no da mercado, pero COSTO lo que costo, igual que sus
        # hermanas de mas arriba. Un cero aqui seria un «no se midio» disfrazado
        # de «no costo nada», que es la clase de cifra que el censo acaba de
        # dejar de escribir.
        res.segundos = float(segundos_hora)
        res.evaluaciones = int(evaluaciones_hora)
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
    #
    # D48, POR LA VIA DEL REPOSO (paso 7, sin cambio de criterio): el precio
    # es el LIQUIDADO de cada comprador (`pi_i`), y el conjunto reducido se
    # vuelve a pasar por el nucleo, porque sin el retirado cambian el piso
    # del juego y con el el presupuesto S. Un vendedor que el nucleo no
    # despacho (fila en cero: sin ganancia posible, D61, o no despachado por
    # la caminata, D65) no coloca nada y no se mira.
    #
    # D67 (2026-09-17): con el piso del vendedor marginal (D63), todo
    # despachado cobra al menos su piso (teorema de cobertura del rango uno,
    # que el nucleo comprueba), de modo que por la via del reposo este bloque
    # es una GUARDA QUE DEBE QUEDAR INERTE. No cambia: si alguna vez retira,
    # retira como siempre, y la cuenta va a `retiros_reposo`, que la linea
    # [D48] publica y que hace salir la corrida con el codigo 3 (D38). La
    # holgura de la comparacion la da `tol_participacion`: por reposo, la
    # misma del nucleo; por las otras vias, la absoluta de siempre.
    if pi_gb_j is not None and J > 1:
        piso_v = np.asarray(pi_gb_j, dtype=float)
        fuera = []
        for u in range(J):
            colocado = float(P_star[u, :].sum())
            if colocado <= 1e-9:
                continue
            ingreso = float(np.dot(P_star[u, :], pi_i)) / colocado
            if ingreso < piso_v[u] - tol_participacion(metodo, piso_v[u]):
                fuera.append(u)
        if metodo == "reposo":
            res.retiros_reposo = len(fuera)

        if fuera and len(fuera) < J:
            quedan = [u for u in range(J) if u not in fuera]
            # D36 (re-revision): el reintento con el conjunto reducido recibe
            # SOLO lo que queda del presupuesto de la hora, no uno entero. Con
            # uno entero, una hora que gasto casi todo en el conjunto completo
            # gastaria dos presupuestos (unos 1168 (s) a la velocidad medida),
            # el plazo por hora la mataria con las dos soluciones dentro, que
            # es justo lo que D36 viene a impedir; y la recursion se anida. Con
            # max(1, ...) la primera vuelta del conjunto reducido corre
            # siempre: el peor caso es un presupuesto mas una vuelta al
            # horizonte de produccion. Con la parada apagada, o por la via
            # alternada, el presupuesto es inerte y pasa tal cual.
            if metodo == "acoplado" and horizonte_max_aco is not None:
                total = (PRESUPUESTO_EVAL_ACOPLADO if presupuesto_aco is None
                         else int(presupuesto_aco))
                queda = max(1, total - int(gastado_hora))
            else:
                queda = presupuesto_aco
            sub = _run_hour_worker(
                (k, G_klim_k, D_k, G_raw_k,
                 [seller_ids[u] for u in quedan], buyer_ids,
                 a_all, b_all, lam_all, theta_all, etha_all,
                 pi_gs, float(np.min(piso_v[quedan])),
                 tau, tau_buyers, t_span, n_points,
                 min_iter, tol, max_iter, ode_method, buyer_competition,
                 metodo, t_span_aco, piso_v[quedan], False,
                 # D35/D26: las mismas palancas de esta vuelta, para que el
                 # conjunto reducido no resuelva con otra tolerancia u otro
                 # horizonte que el resto de la hora. D36: y solo lo que
                 # queda del presupuesto de la hora (arriba).
                 rtol_aco, horizonte_max_aco, queda,
                 # H-85 / D45: el mismo arranque que el conjunto completo.
                 arranque_aco,
                 # D47: y el mismo criterio de parada, por la misma razon.
                 criterio_aco, tol_reparto_aco,
                 # D48: y las mismas opciones del reposo, para que el
                 # conjunto reducido se resuelva con la misma regla.
                 modo_pres, sigma_nivel, regla_precio, despacho_vend,
                 # D49 / D50: y la misma dinamica regularizada.
                 mu_entropia, nivel_aco))
            # D47: las dos resoluciones las pago esta hora, de modo que su
            # costo es la suma. Se acumula antes de mirar si el conjunto
            # reducido dio mercado, porque lo que gasto lo gasto igual.
            segundos_hora += float(getattr(sub, "segundos", 0.0))
            evaluaciones_hora += int(getattr(sub, "evaluaciones", 0))
            # D67: y los retiros de la vuelta reducida se suman, antes de
            # mirar si dio mercado.
            res.retiros_reposo += int(getattr(sub, "retiros_reposo", 0))
            # D36: la parada que cuenta es la de la vuelta que produjo el
            # resultado final (o su falta), la del conjunto reducido.
            res.parada_acoplado = sub.parada_acoplado
            # D48: y lo mismo con el reposo: el regimen, los precios, los
            # excluidos y las cotas son los del conjunto final, el reducido,
            # que ya paso por su propia participacion y calculo sus cotas.
            if metodo == "reposo":
                for campo in CAMPOS_REPOSO:
                    setattr(res, campo, getattr(sub, campo))
            # Si el conjunto reducido no resuelve, la hora se queda sin
            # mercado, que es lo que esta funcion ya hace con las que no
            # convergen. Mejor sin mercado que con uno que nadie aceptaria.
            if sub.P_star is None:
                # D26: el horizonte del intento con el conjunto completo,
                # que la restriccion de participacion descarto, no significa
                # nada si al final no hay mercado.
                #
                # D67 (revision final): por la via del reposo la hora nombra
                # igual a sus retirados, los de esta vuelta y los de la
                # reducida. Sin esto, el retiro llegaba a `retiros_reposo`, a
                # la linea [D48] y al codigo de D38, pero el almacen no
                # anotaba a nadie con el papel «retirado» y la compuerta
                # `cero_retiros` salia en verde: un retiro sin rastro donde lo
                # mira el revisor. Va guardado por la via, como el de la rama
                # de abajo, para que la acoplada y la alternada sigan
                # IDENTICAS AL BIT.
                if metodo == "reposo":
                    res.retirados = ([seller_ids[u] for u in fuera]
                                     + list(sub.retirados))
                res.horizonte_usado = 0.0
                res.segundos = float(segundos_hora)
                res.evaluaciones = int(evaluaciones_hora)
                # C-190: si el reintento reventó, su motivo tiene que subir.
                # Sin esto, `res` (el marco exterior, `motivo=""` de fabrica)
                # volveria "sin mercado" muda, el mismo fallo mudo que cierra
                # C-190, solo que un nivel mas arriba.
                if sub.motivo:
                    res.motivo = sub.motivo
                return res
            P_completo = np.zeros((J, I))
            P_completo[quedan, :] = sub.P_star
            P_star   = P_completo
            pi_i     = sub.pi_star
            iter_count = sub.iters_used
            norm_rel = sub.norm_rel_final
            # D47: el residuo del reparto que cuenta es el de la vuelta que
            # produjo el resultado final, la del conjunto reducido.
            residuo_rep = sub.residuo_reparto
            # D26: el horizonte que de verdad produjo este resultado es el
            # de la vuelta anidada, no el del intento con el conjunto
            # completo que la restriccion de participacion descarto.
            res.horizonte_usado = sub.horizonte_usado
            # La llamada anidada hace su propia vuelta, de modo que el bucle
            # se cierra solo. Sus retirados se suman a los de esta vuelta.
            res.retirados = ([seller_ids[u] for u in fuera]
                             + list(sub.retirados))
        elif fuera:
            # Todos a perdida: no hay mercado que valga esa hora. Sin
            # mercado, el horizonte del intento acoplado que la restriccion
            # de participacion descarto no significa nada (D26).
            if metodo == "reposo":
                # D67: por la via del reposo la hora nombra a sus retirados,
                # para que el almacen los anote con su papel y la compuerta
                # de cero retiros los vea. Las otras vias quedan como estaban.
                res.retirados = [seller_ids[u] for u in fuera]
            res.horizonte_usado = 0.0
            res.segundos = float(segundos_hora)
            res.evaluaciones = int(evaluaciones_hora)
            return res

    # D55: las cotas de optimalidad y la captura del reposo, DESPUES de la
    # participacion y sobre el conjunto final de vendedores. Con el piso
    # minimo (D62) el excedente podia ser negativo antes de ella (un
    # despachado de piso alto vendiendo por debajo del suyo) y `captura` lo
    # rechaza en voz alta; con el piso marginal (D63) ya no puede, y despues
    # de la participacion tampoco: con todo despachado cobrando al menos su
    # piso y todo comprador pagando a lo sumo su techo, excedente = ahorro +
    # prima >= 0. Si hubo retiros, el conjunto reducido ya las calculo en su
    # propia vuelta y se copiaron arriba.
    #
    # LAS COTAS SE MIDEN SOBRE QUIEN PUEDE COMERCIAR AL FINAL (revision de la
    # tarea 2, y de la tarea 5a para la tercera lista). Entran a las cotas con
    # cantidad cero las TRES listas de quien no comercia esa hora:
    #   · `vendedores_excluidos`, sin ganancia posible con nadie (D61);
    #   · `vendedores_no_despachados`, a los que la caminata competitiva deja
    #     fuera por su piso (D65), que es la misma oferta que descuenta la
    #     compuerta de salida al reconstruir E;
    #   · `excluidos_bajo_piso`, los compradores con el techo bajo el piso del
    #     juego (D61 parcial).
    # El optimo nunca los usaria, pero el peor reparto los usaria primero
    # (pisos altos, techos bajos) y mediria un mercado que no existe. Los
    # retirados por la participacion ya no estan en el conjunto reducido. Asi
    # el peor se mide siempre sobre el mismo conjunto, haya retiro o no. Las
    # longitudes no cambian y el volumen E sigue siendo a lo sumo el lado
    # corto de lo que queda.
    if metodo == "reposo" and not res.retirados:
        s_cota = s_rep.copy()
        s_cota[np.asarray(rep.vendedores_excluidos, dtype=int)] = 0.0
        s_cota[np.asarray(rep.vendedores_no_despachados, dtype=int)] = 0.0
        d_cota = d_rep.copy()
        d_cota[np.asarray(rep.excluidos_bajo_piso, dtype=int)] = 0.0
        try:
            optimo, peor = cotas_optimalidad(s_cota, d_cota, pi_gs,
                                             piso_rep, rep.E)
            cap = captura_reposo(rep.excedente, optimo)
        except ValueError as e:
            # Como el resto del ramal: la hora queda sin mercado con su
            # motivo y cuenta para el codigo de salida (C-190, D38).
            res.motivo = (f"{PREFIJO_EXCEPCION_REPOSO}: "
                          f"{type(e).__name__}: {e}")[:200]
            res.segundos = float(segundos_hora)
            # Menor 4 de la revision final: coherencia con la via acoplada,
            # que anota siempre las dos medidas del costo de la hora.
            res.evaluaciones = int(evaluaciones_hora)
            return res
        res.excedente_optimo = float(optimo)
        res.excedente_peor = float(peor)
        res.captura = float(cap)

    res.P_star = P_star; res.pi_star = pi_i; res.iters_used = iter_count
    res.norm_rel_final = float(norm_rel)
    res.residuo_reparto = float(residuo_rep)
    res.segundos = float(segundos_hora)
    res.evaluaciones = int(evaluaciones_hora)

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
                         bool(getattr(sv, "guarda_trayectorias", False)),
                         # D35/D26: las dos palancas del acoplado, apagadas
                         # por defecto (identicas al bit a lo de hoy). D36:
                         # el presupuesto, que solo actua con la parada.
                         sv.rtol_acoplado, sv.horizonte_max_acoplado,
                         getattr(sv, "presupuesto_eval_acoplado", None),
                         # H-85 / D45: el arranque del acoplado. El respaldo
                         # del `getattr` es "iguales" por la misma razon que
                         # el shim de la tupla: lo que se rellena por
                         # compatibilidad es el defecto de cuando se escribio
                         # este camino, no el de hoy. Un objeto sin el campo
                         # es de antes de D45 y esperaba el arranque de antes.
                         getattr(sv, "arranque_acoplado", "iguales"),
                         # D47: el criterio de parada y su umbral; "precio"
                         # (defecto) es el de D26, identico al bit.
                         getattr(sv, "criterio_estacionario", "precio"),
                         getattr(sv, "tol_reparto", TOL_REPARTO),
                         # D48: las opciones de la via por reposo; inertes
                         # en las otras dos. El respaldo es el defecto.
                         *_opciones_reposo(sv),
                         # D49 / D50: la dinamica regularizada del acoplado;
                         # apagada por defecto, identica al bit.
                         *_opciones_dinamica(sv)))

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
            #
            # La ventana vive ahora dentro de `_resuelve_con_plazo`, que ademas
            # pone el plazo por hora de D24: la hora que lo pasa, contado desde
            # que empieza a correr, queda sin resolver con su motivo, y la
            # corrida sigue. Sin horas vencidas el resultado es el de antes.
            plazo = getattr(sv, "plazo_hora_s", None)
            plazo_txt = ("" if plazo is None
                         else f"{plazo/60:.0f} min" if plazo >= 60
                         else f"{plazo:.0f} s")

            def hace_vencida(j):
                return HourlyResult(
                    k=j[0], motivo=f"vencio el plazo por hora de {plazo_txt}")

            with _make_bar(total=T, desc=desc) as bar:
                rmap, vencidas = _resuelve_con_plazo(
                    _run_hour_worker, jobs, _cuantos_obreros(sv.procesos),
                    plazo, hace_vencida, bar=bar)
            if vencidas:
                muestra = ", ".join(str(k) for k in vencidas[:20])
                resto = (f" y {len(vencidas) - 20} mas"
                         if len(vencidas) > 20 else "")
                print(f"    [D24] {len(vencidas)} horas vencieron el plazo por "
                      f"hora de {plazo_txt} y quedan sin resolver: "
                      f"{muestra}{resto}", flush=True)
        else:
            # Sin plazo por hora (D24): la rama secuencial resuelve en este
            # mismo proceso, y una hora atascada en codigo nativo no se puede
            # interrumpir sin otro proceso que la mate.
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
        # La de mayor volumen y la de mayor deficit, saltando las horas que
        # vencieron el plazo por hora: aqui se resuelven sin plazo, en este
        # mismo proceso, y la vencida colgaria la corrida (D24; tarea 18,
        # fix1, C.3). Ver `_horas_representativas`.
        hours_to_run = _horas_representativas(p2p_results, D, G_klim,
                                              max_hours)
        if not hours_to_run:
            return []

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
                                  bool(devuelve_trayectoria),
                                  sv.rtol_acoplado, sv.horizonte_max_acoplado,
                                  getattr(sv, "presupuesto_eval_acoplado",
                                          None),
                                  # H-85 / D45: el arranque del acoplado; el
                                  # respaldo es el defecto de cuando se
                                  # escribio este camino, como en el shim.
                                  getattr(sv, "arranque_acoplado",
                                          "iguales"),
                                  # D47: el criterio de parada y su umbral.
                                  getattr(sv, "criterio_estacionario",
                                          "precio"),
                                  getattr(sv, "tol_reparto", TOL_REPARTO),
                                  # D48: las opciones de la via por reposo.
                                  *_opciones_reposo(sv),
                                  # D49 / D50: la dinamica regularizada.
                                  *_opciones_dinamica(sv)))
