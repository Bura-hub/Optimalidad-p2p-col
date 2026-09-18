# La validación del reposo: qué mide cada guion, qué escribe y qué cuesta

La matriz de trece casos ya corrió con el mercado resuelto en el reposo
(`--metodo reposo`, D48). Lo que falta es decidir **cómo se cuenta eso en la
tesis**: si cada régimen se publica como «el reposo al que la dinámica llega»
o como «regla declarada». Eso son las mediciones M-A a M-G, y aquí están sus
guiones.

No se hacen con el motor. Integrar la dinámica hasta el reposo en una hora
rígida cuesta del orden de 1e9 evaluaciones del lado derecho, y por eso se
hacen con el **arnés acelerado** que ya midió el consenso el 2026-09-16
(`.superpowers/sdd/2026-09-16-sonda-equilibrio/consenso-report.md`).

**Nada de esto se corre en la máquina de trabajo.** La noche entera va al
servidor, con la acción `validacion_reposo` de `modelo_base/run_servidor.sh`.
En local solo se corren las pruebas de `tests/test_arnes_consenso.py` y el
seco del lanzador.

---

## Lo primero, y lo que hace creíble todo lo demás

`arnes.py` es una copia del lado derecho del motor. Si se hubiera desviado, la
medición no diría nada sobre el motor. Por eso lo primero que corre la noche
es la comprobación de que **no** se desvió:

```bash
python -u reformateo/documento/scripts/sonda/consenso/arnes.py \
    E0 "2025-05-09 13:00" E0 "2025-05-10 10:00" K1 "2025-05-11 08:00" \
    E4 "2025-05-07 07:00"
```

El lado derecho del arnés tiene que coincidir **al bit** con el que el motor
evalúa en diez ramas: las cuatro combinaciones de peso del jugador virtual y
de arranque, el término entrópico (μ = 1), el costo del vendedor por su
alternativa (el que sostiene M-B), el piso del vendedor marginal (el ancla de
M-A), las tres juntas y las dos configuraciones de M-G (el código de la
autora: competencia `matlab` y oferta a partes iguales). Los estados probados
se perturban de forma aditiva, con escala por bloque, desde el arranque y desde
un estado con los filtros de los multiplicadores cargados, para que se ejerzan
los ocho bloques del estado. Si difiere, dice en qué bloque y cuánto, y sale
con código distinto de cero.
Siempre corre sobre el caso publicado de Chacón y sobre una hora sintética de
pisos distintos (la que ejerce de verdad el piso marginal), que no necesitan
datos reales; los argumentos añaden horas reales.

---

## Los guiones

| Guion | Qué mide | Qué escribe | Qué cuesta |
|---|---|---|---|
| `arnes.py` | el arnés: el lado derecho del motor con ganchos, la aceleración k, el cargador de horas y el integrador con tope. Ejecutado solo, la comprobación contra el motor | nada (imprime) | segundos |
| `caso_publicado_chacon.py` | los literales de las Tablas II y IV del artículo base | nada | — |
| `preparacion.py` | la hora lista para integrar: el reposo cerrado con que se compara, el piso del vendedor marginal, los precios del presupuesto sigma y el recorte a los agentes que están en el juego | nada | — |
| `selecciona_horas.py` | escoge y **comprueba** las horas de cada régimen sobre el almacén de un caso | `horas_<caso>.json` | ~1 (min) por caso (carga los datos) |
| `corre_mediciones.py` | el que corre: integra cada hora con su variante y mide su distancia al reposo en cada punto de control | el JSON de la medición | lo de la medición |
| `veredicto.py` | lee esos JSON y dice qué régimen queda como reposo verificado y cuál como regla declarada | texto | segundos |
| `medicion_regimenes.py` | **M-A**: la forma cerrada frente a la dinámica, régimen por régimen, acelerada y, en los grupos libres, sin acelerar | `m_a_regimenes.json` | 140 corridas (120 aceleradas de 1 a 10 (min), 20 sin acelerar del orden de un minuto); tope 3 600 (s) cada una |
| `medicion_merito_vendedores.py` | **M-B**: con qué regla reparte la dinámica cuando sobran vendedores (D64) | `m_b_merito.json` | 120 corridas, igual |
| `medicion_suma_no_cabe.py` | **M-C**: si la regla del régimen «la suma no cabe» es el reposo, desde cuatro arranques (D53) | `m_c_no_cabe.json` | 260 corridas (28 horas de E0 y 37 de CV2, por cuatro arranques), de las baratas; tope 1 800 (s) |
| `medicion_estabilidad.py` | **M-D**: los valores propios del reducido en el reposo, con su residuo | `m_d_estabilidad.json` | segundos |
| `medicion_mu.py` | **M-E**: sensibilidad a μ, y el censo de empates por debajo de 3 μ | `m_e_mu.json`, `m_e_empates_<caso>.json` | 36 corridas (6 grupos × 2 horas × 3 μ); el censo, segundos |
| `medicion_chacon.py` | **M-G**: el caso publicado con las dos formas del jugador virtual | `m_g_chacon.json` | 8 corridas |

Todo sale en `SALIDAS_SERVIDOR/validacion_reposo/`.

## Cómo se corre una medición a mano

```bash
python -u reformateo/documento/scripts/sonda/consenso/corre_mediciones.py \
    --medicion medicion_regimenes \
    --salida SALIDAS_SERVIDOR/validacion_reposo/m_a_regimenes.json \
    --procesos 16 --tope-total 14400
python -u reformateo/documento/scripts/sonda/consenso/veredicto.py \
    SALIDAS_SERVIDOR/validacion_reposo/m_a_regimenes.json
```

El JSON se escribe **después de cada corrida**, de modo que una parada no deja
la noche en blanco; si el tope total corta, el propio guion dice con qué
`--desde` se retoma y en qué fichero, y `veredicto.py` acepta los dos juntos.

**Un trabajador muerto no tumba la medición** (tarea 4d, noche del
2026-09-18):

- el registro imprime la memoria de la máquina y el RSS de los trabajadores;
- las corridas en vuelo sin terminar vuelven a la cola. Solo las que podían
  estar corriendo (las `procesos + 1` primeras por orden de sometimiento) son
  sospechosas: vuelven **una vez** y corren de una en una, para aislar a la
  que revienta la memoria. Las demás estaban en espera y vuelven sin más;
- la sospechosa que cae en dos muertes se anota como FALLA, con la causa
  «trabajador muerto (probable falta de memoria)», y no se reencola más;
- se abre un pool nuevo y se sigue;
- con tres muertes en la misma medición, se para con código 1 y lista los
  índices que faltan;
- en `validacion_reposo`, cada medición va envuelta en `timeout` (su tope más
  3 900 (s)): un cuelgue del gestor del pool sale con 124 y se anota como
  fallo;
- el veredicto sigue contando esas FALLA en el denominador, y dice cuántas de
  las fallidas son de la máquina (la columna `muerto`).

Antes de abrir cada pool, los procesos se reducen si `MemAvailable` no da
1,5 GB a cada uno (`--memoria-por-proceso`, o `MEMORIA_POR_PROCESO_GB`; 0 lo
quita).

## Cómo se escribe un guion de medición

Un módulo con tres cosas: `MEDICION` (el rótulo), `QUE_DECIDE` (una línea) y
`specs(horas)`, que devuelve la lista de especificaciones. `horas` es lo que
`selecciona_horas.py` dejó escrito, `{caso: {grupo: [...]}}`. Cada
especificación dice qué hora (`caso`, `fecha`), con qué variante del arnés
(`var`: `mu_ent`, `k_lento`, `b_vend`, `peso`, `arranque`), en qué puntos de
control (`cortes`, en tiempo sin equivalencia: el equivalente es t·k), con qué
tope (`tope`, en segundos), desde qué arranque de precios (`nivel`), con qué
piso del juego (`piso_juego`) y contra qué reposo se compara (`cerrada` y
`referencias`). Además, `medicion` (el rótulo, con que `veredicto.py` sabe qué
juicio le toca), `familia` (el modelo que se prueba: ver «Familia» abajo) y,
si la medición declara la suya, `tolerancia` (`tol_q_rel`, `tol_p`). Si la
medición tiene un juicio propio, su guion trae `veredicto(resultados)`.

## Los criterios, fijados antes de medir

- **Consenso**: la hora llega al reposo en t si en t y en el punto de control
  siguiente el reparto y los precios están dentro de la tolerancia y las
  derivadas, por unidad de tiempo equivalente, valen menos de 1e-3.
- **Tolerancia**: max|q − q_cerrada| ≤ 1e-3·E (kWh) y max|p − p_cerrada| ≤ 0,05
  (COP/kWh) con compradores libres y sin acelerar; 1 % de E y 0,5 (COP/kWh) con
  topados o con aceleración, porque la aceleración solo es exacta con libres.
  M-C y M-E **declaran** la suya (1e-3·E y 0,5 (COP/kWh)), y se usa esa.
- **Familia**: el veredicto cuenta por régimen, referencia y familia. La
  familia es el modelo que se prueba: las dos aceleraciones de M-A van juntas
  (todas sus corridas dentro); los dos costos de M-B, los tres μ de M-E y las
  dos formas del jugador virtual de M-G, aparte. M-C se lee solo por su juicio
  propio, que separa sus dos arranques de precios (H-90).
- **Aceptación por régimen**: el 95 % o más de **todas** las horas del grupo
  dentro, en el tiempo equivalente 80 y en el 160. Una hora se juzga con sus
  corridas que llegaron a teq 160; si ninguna llegó, sigue en el denominador y
  cuenta como «no llega». Con menos de cinco horas, «muestra insuficiente», y
  siempre con el n. Una hora cuyo recorte movió el reposo no cuenta.
- **M-B, M-C, M-E y M-G tienen además su juicio propio** (la función
  `veredicto` de su guion), que `veredicto.py` imprime después de la tabla:
  - **M-B**: una regla gana solo si reproduce el 95 % de las horas que
    **discriminan** (el piso y el costo despachan distinto, a más de 1e-3·E), y
    hacen falta al menos cinco; si no, «ninguna regla alcanza el 95 %» o
    «muestra insuficiente». Dice cuántas horas se apartaron y cuántas no
    llegaron.
  - **M-C** juzga en tres partes, porque sus dos arranques de precios no son el
    mismo modelo (la dinámica conserva la suma de precios que fija el arranque,
    H-90): la multiplicidad, solo entre las dos ofertas de un mismo arranque de
    precios, informada por arranque (sigma y medio por separado); los
    arranques sigma frente a la forma cerrada, sobre todas las horas; y
    «medio» frente a sigma como dependencia del presupuesto, que no cuenta
    contra D53. **El par sigma es la prueba de unicidad**: una hora está en el
    «mismo sitio» solo si se comparó su par sigma (el par medio no la suma), y
    cuenta «dentro» de la forma cerrada solo si **las dos** ofertas sigma
    llegaron a teq 160 y están dentro; con una sola, es «no llega» (o «falla»),
    y esas horas se cuentan aparte.
  - **M-E** compara los tres μ de cada hora entre sí. **M-G** se juzga contra
    la tabla publicada, con la tolerancia de la tabla también para la quietud,
    y solo en las magnitudes que la tabla lee: q, p y la parte del vendedor en
    el brazo de barrera; el nivel ponderado y la parte en el de precio, cuyo
    reparto puede seguir convergiendo como 1/t con los precios ya quietos en
    el piso. Su brazo k = 1, que termina en teq 40 por diseño, se juzga entre
    teq 20 y 40.
  - En los tres, solo cuentan los estados **quietos** (derivadas bajo 1e-3 en
    los dos últimos puntos): se separa «no llegaron» de «llegaron a sitios
    distintos».
- **Medición incompleta**: si el tope dejó corridas del plan sin hacer,
  `corre_mediciones.py` sale con 4 y `veredicto.py` imprime «MEDICIÓN
  INCOMPLETA: N de M» encima de la tabla y también sale con 4. Los JSON guardan
  `plan_total`; en los que no (la primera noche), el plan se deduce de los
  `horas_<caso>.json` y del guion.

## Dos cosas que no hay que «arreglar»

- **M-G arranca los precios con `c136`, no con el presupuesto sigma.** Las
  predicciones de la sección 11 del plan (833,3 (COP/kWh) en tres compradores y
  1 250 en dos) están escritas contra el presupuesto del Algoritmo 3, que en la
  banda del modelo base vale S = (I − 1)·1 250 = 5 000. Con el arranque sigma
  el presupuesto sería 5 · [114 + 0,8·1 136] = 5 114 y las cifras no
  compararían con las del artículo. Es deliberado.
- **El caso CV2 del arnés** sale de `paso_a_paso.carga(..., factor_cv=2)`, que
  multiplica el componente de comercializar en el piso y en nada más. En
  producción, `--factor-cv 2` lo multiplica en dos sitios: en el piso y en
  `component_c_arg`, que alimenta la liquidación de C1, de C4 y de los
  residuales. Al arnés le basta el piso, porque el mercado de una hora solo ve
  la demanda, la generación, el techo y el piso, y el segundo sitio cambia lo
  que cada escenario paga, no el reparto ni el precio. Sin el factor, la carga
  es idéntica al bit a la de siempre, y eso lo fija
  `tests/test_arnes_consenso.py`.

## Una hora que cae en dos grupos

Una hora «interiores» con dos vendedores entra en el grupo «interiores» y en
«dos_vendedores», y se integra dos veces (m2 de la re-revisión). No se corrige
en la muestra, porque cambiar `specs()` desincronizaría la deducción del plan
de una noche ya lanzada. No afecta a los veredictos: la tabla y los juicios
propios cuentan cada hora una sola vez (la clave es el caso y la fecha), y el
resumen de M-D también. Solo cuesta tiempo de máquina.

## Lo que esta medición NO alcanza

- **Las horas rígidas sin acelerar.** Con topados o con varios vendedores no
  caben, y por eso la tolerancia se afloja. Es una limitación declarada, no un
  descuido.
- **M-F y M-H** no están aquí: M-F es la matriz entera, que ya corrió con sus
  compuertas de salida, y la segunda mitad de M-H es la compuerta de cero
  retiros.
