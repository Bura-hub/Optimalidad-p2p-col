# Hallazgos — sesión 2026-08-21 (montaje del documento de proceso)

Hallazgos surgidos al construir la infraestructura del documento. Se vuelcan
aquí aplicados o no, según el protocolo del proyecto.

---

## H-1 · El docstring de `data/preprocessing.py` tiene cifras desfasadas

**Estado: acotado. La tesis ya lo había resuelto; el código no.**

> **Corrección respecto a la primera versión de esta nota.** Se registró como
> hallazgo nuevo, y no lo es del todo: `Documentos/FinalTesisV2/tesis.md`
> §4.4 ya declara las cifras medidas (1.517, 213 y 94 h), ya señala que las
> de 989, 216 y 112 «no reproducen contra el código y los datos vigentes» y
> ya las da por reemplazadas. Lo que aquí se aporta es una verificación
> independiente por un tercer camino —el caché instrumentado— y la
> constatación de que **el docstring del código sigue sin actualizarse**.
> El texto que sigue conserva la medición; lo que cambia es a quién se
> atribuye el desfase.

El docstring del módulo declara, en su sección «Tipos»:

> `"net"` : neteo agresivo (Udenar, **989 h** con D<0 sobre el horizonte v3).
> `"net_partial"` : neteo leve (Mariana **216 h**, UCC **112 h** con D<0).

Medido sobre el horizonte canónico (2025-04-04 → 2025-12-16, 6.144 h), con las
funciones del propio pipeline y verificando que las series finales coinciden
al bit con `build_demand_generation()`:

| Institución | Docstring | Medido | Mínimo alcanzado |
|---|---:|---:|---:|
| Udenar | 989 h | **1.517 h** (24,7 %) | −33,57 kW |
| Mariana | 216 h | **213 h** (3,5 %) | −2,41 kW |
| UCC | 112 h | **94 h** (1,5 %) | −5,91 kW |

El docstring además **se contradice a sí mismo**: su sección «Problema que
resuelve» dice que Udenar tiene «~20 % de las horas con valor negativo», lo
que no cuadra con 989/6144 = 16,1 % pero sí se acerca a la medición real
(24,7 % del horizonte; 25,1 % de las horas con dato).

También difiere el mínimo: el docstring cita −34,6 kW y lo medido es
−33,57 kW.

**Verificación de que la medición es correcta.** El caché instrumentado
reproduce las diez series finales del pipeline con `max|dif| = 0` exacto, de
modo que recorre exactamente el mismo camino. Y el patrón temporal confirma
la interpretación: las horas negativas de Udenar se concentran entre las 11
y las 15 h (223 casos a las 13 h, 218 a las 12 h), que es la franja de
producción solar. Es neteo, no ruido.

**Acción tomada.** `reformateo/documento/scripts/datos.py` ya no fija estos
conteos: los lee siempre del caché medido (`conteo_negativas()`). El
documento cita las cifras medidas.

**Acción pendiente (decisión del autor).** Actualizar el docstring de
`data/preprocessing.py`, que es código del repositorio principal y no se ha
tocado en esta sesión. Conviene comprobar antes de qué corrida salían las
989 h: podrían corresponder a `MedicionesMTE` v2 o a un horizonte anterior,
en cuyo caso bastaría con datar la cifra en vez de reemplazarla.

---

## H-2 · Las figuras de la presentación salen del canon superado

**Estado: sin acción en esta sesión; afecta a `Presentacion/tesis_p2p/`.**

Las 20 figuras de la presentación Beamer se generan desde
`Presentacion/tesis_p2p/datos/canonica_m{1,3}/`, que es una copia del canon
de **junio**, no del vigente de agosto. En consecuencia:

- `fig_ranking.png`, `fig_giro_agr.png`, `fig_institucion.png` publican C4 en
  **Caso 1** (52.219.945 / 32.372.584), que `VERSIONES.md` §3 marca como «no
  publicar».
- `fig_bootstrap.png` publica el bootstrap viejo (5.020,57 / 8.161,82) en vez
  del vigente (8.114,14 / 10.579,11).
- `fig_giro_agr.png` rotula «C5≈C4 — la regla AGR no agrega valor», mientras
  que el frame 42 del `.tex`, parchado el 2026-08-07, afirma lo contrario.
  **La figura contradice al pie de su propia diapositiva.**
- `datos/canonica_m3/daily_series_20260611_0253.csv` es el contaminante ya
  identificado: una copia de M1 dentro de la carpeta M3. La cuarentena limpió
  el canon pero no esta copia.
- `presentacion.pdf` en disco es del 2026-07-27, anterior al parche del
  `.tex`, de modo que el PDF compilado sigue llevando la lectura refutada.

**Implicación asumida.** El documento de proceso no reutiliza ninguna figura
existente; todas se regeneran desde el canon de agosto. Queda como decisión
aparte si se corrige la presentación.

---

## H-3 · La compuerta del canon y el hash de la corrida

**Estado: confirmado, ya recogido en la guía.**

Ambas compuertas pasan en limpio (`CANON 2026-08 INTACTO` y `CANON INTACTO`).
Se confirma también lo que advierte `CANON.md` §6: las hojas `Diagnostico` de
los dos libros canónicos registran `git_hash = dc7c0e7`, pero el commit con el
que se reproduce la corrida es **`5c5baa2`**. El anexo de reproducibilidad
debe citar el segundo.

---

## H-6 · El horizonte termina cuatro meses antes de donde llega el dato

**Estado: abierto; el documento lo declara, no lo resuelve.**

El horizonte canónico va del 2025-04-04 al 2025-12-16 (\num{6144} h). El
inicio está plenamente justificado por el dato: lo impone el HUDN, cuyo
medidor arranca el 2025-04-03 a las 20:58 y cuyo inversor lo hace al día
siguiente a las 05:58. Antes de esa fecha la comunidad no está completa y
no hay mercado de cinco que simular.

El cierre no tiene esa justificación. Al censar las 27 fuentes crudas
resulta que **todas ellas contienen datos hasta abril de 2026**:

| Fuente | Último registro |
|---|---|
| Medidores de Udenar, Mariana, UCC y Cesmag | 2026-04-25 |
| Inversores Fronius de Udenar | 2026-04-10 |
| Medidores e inversor del HUDN | 2026-04-11 |
| Inversor MTE de Udenar | 2026-04-24 |

Es decir, hay aproximadamente **cuatro meses de medición sin usar**. El
repositorio no registra por qué el horizonte se detuvo en diciembre; la
constante `T_END` de `data/xm_data_loader.py` lleva el comentario de que
«HUDN + Fronius Udenar caen ~17-Dic», pero el censo no lo confirma: esas
fuentes cubren el \pct{98} del horizonte y siguen registrando después.

**Qué significa y qué no.** No invalida ninguna cifra: el estudio es
correcto sobre el horizonte que declara. Lo que hace es dejar sobre la
mesa una ampliación del orden del \pct{45} en tamaño de muestra, que
además incorporaría un ciclo estacional más completo. Extenderlo obligaría
a repetir la corrida canónica entera y a rehacer toda la verificación
numérica, de modo que no es una tarea menor.

**Acción tomada.** El Capítulo 2 del documento lo declara en un
`trampabox`, distinguiendo el estatuto del inicio (impuesto por el dato)
del estatuto del cierre (corte administrativo), para que el lector no
atribuya al dato una limitación que no tiene.

---

## H-5 · El canon no es autosuficiente para regenerar sus propias figuras

**Estado: abierto; el documento lo rodea, no lo resuelve.**

La entrega canónica acompaña casi todas sus figuras con un `.csv` hermano
que contiene los datos dibujados, de modo que se pueden reconstruir sin
volver a correr nada. Pero no todas: de las **22 figuras** de
`entrega_canonica_2026-08/canonica_m1/graficas/`, **cinco no tienen ningún
sibling de datos**, y sus valores tampoco aparecen en las hojas de los tres
libros de resultados:

| Figura | Qué muestra | Dónde estaría el dato |
|---|---|---|
| `fig10_sensibilidad_ppa` | Barrido del precio del contrato bilateral | no hay hoja SA-PPA |
| `fig11_sensibilidad_pgs` | Barrido de la tarifa minorista | no hay hoja SA3 |
| `fig14_optimalidad_horaria` | Dominancia hora a hora frente al colectivo | falta la serie horaria de C4 |
| `fig16_subperiod` | Cortes por sub-período | no hay hoja de sub-períodos |
| `fig22_convergencia_h0683` | Trayectorias de una hora | sin datos exportados |

Las tres primeras y la quinta son recuperables volviendo a correr el
análisis; la cuarta ya estaba señalada como no reproducible en trabajos
anteriores.

**Consecuencia práctica.** El capítulo 11 pierde dos de sus barridos y el
capítulo 10 pierde la figura de optimalidad horaria, salvo que se acepte
re-correr. Mientras tanto, esas cinco se incorporan al documento **usando el
PNG canónico tal cual**, con una nota en el pie que diga que no se
re-estilizó porque el canon no conserva los datos. Es preferible a
re-correr, que arriesgaría mover cifras ya publicadas.

**Recomendación para futuras corridas.** Que el exportador escriba el
sibling de datos de *todas* las figuras, sin excepción. El coste es
despreciable y es lo que permite auditar sin ejecutar.

---

## H-4 · Los rótulos SC/SS, confirmados por física

**Estado: confirmado y neutralizado en el código del documento.**

`CANON.md` §5bis advierte que las columnas `SC` y `SS` de la hoja `Resumen`
están intercambiadas respecto a su semántica. Queda confirmado por un
argumento independiente del código: en M1 la cobertura de generación sobre
demanda es del 19,1 %, de modo que la fracción de demanda cubierta con
generación propia no puede valer 0,98. El valor 0,1876 rotulado `SC` es
autosuficiencia y el 0,9806 rotulado `SS` es autoconsumo.

`datos.resumen()` los devuelve ya renombrados a `autosuficiencia` y
`autoconsumo`, de modo que ninguna figura del documento pueda heredar el
rótulo equivocado.
