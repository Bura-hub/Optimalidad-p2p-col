# Guía de redacción — Documento de proceso

Este archivo es el encargo de trabajo. Cada capítulo tiene aquí lo que debe
contar, con qué figuras, de qué archivo salen los números, qué tiene que
justificar y qué trampa debe evitar. Quien redacte una sección **no necesita
explorar el repositorio**: todo lo que necesita saber está en su ficha.

---

## 1. Invariantes del documento

Estas diez reglas valen para todas las secciones. Romper una es un defecto,
no una variante de estilo.

1. **Narrativa dato → proceso → resultado.** El documento nunca adelanta una
   cifra de resultado antes del capítulo 10. Los capítulos 1 a 9 explican
   cómo se construyó el número; no lo revelan.

2. **Una idea = una subsección = una figura.** Es el patrón medido en
   `presSar.pptx`: allí el acondicionamiento de una señal ocupa siete
   diapositivas, una por etapa. Aquí, cada transformación del dato ocupa su
   propia subsección con su propia figura. No se agrupan dos
   transformaciones en un párrafo.

3. **Títulos `Raíz: Subtema`.** La `\section` lleva la raíz, la
   `\subsection` el subtema. No se repite la raíz en la subsección.

4. **Toda figura declara su procedencia.** El `\caption` termina con
   `\fuente{...}` diciendo de qué artefacto salió. Cada figura del proyecto
   tiene además un `figuras/<nombre>.fuente.txt` generado automáticamente
   con la ruta exacta; el texto del `\caption` debe coincidir con él.

5. **M1 y M3 siempre en paralelo.** Ninguna cifra se presenta sin decir a
   qué frontera de medición pertenece. Cuando las dos coberturas dan
   lecturas opuestas, se dicen las dos; no se elige la favorable.

6. **Ningún superlativo sin comprobarlo.** «El mayor vendedor», «solo dos»,
   «ninguno»: cada una de esas frases se verifica contra
   `datos.reparto_p2p(cobertura)` para la frontera correcta, porque M1 y M3
   invierten los papeles de los agentes.

7. **Una sola fuente numérica.** `SALIDAS_SERVIDOR/entrega_canonica_2026-08/`.
   Se accede siempre por `scripts/datos.py`, nunca abriendo un archivo
   directamente. Ningún dato del texto proviene de un docstring, un README o
   una versión anterior del manuscrito: si una cifra no se puede rastrear a
   un artefacto canónico, no se escribe.

8. **Registro de lenguaje.** El del autor, medido sobre su corpus real:
   los siete archivos LaTeX de las carpetas `Semestre`, sus dos informes
   en PDF de Semestre 10 y los tres informes MTE de julio de 2026. Las
   reglas y las cifras objetivo están en la sección 9. **Rige para todo lo
   que se redacte y para todo lo que se corrija**, sin excepción: un
   pasaje reescrito debe salir en ese registro, no en el de quien lo
   reescribe. Antes de dar un capítulo por cerrado se mide con
   `scripts/medir_estilo.py`.

9. **Toda corrección se anota.** Cada cambio sobre texto ya redactado se
   registra en `CORRECCIONES.md` con su identificador, qué decía, qué dice
   ahora, por qué y dónde se aplicó. No es burocracia: varias de estas
   correcciones afectan también a la tesis y al artículo, y una corrección
   sin registrar se vuelve a cometer. Los tipos son `nombre`, `dato`,
   `estilo` y `técnico`. Lo que no se pueda aplicar todavía va a la tabla
   de pendientes del mismo archivo, no se pierde.

10. **El artefacto técnico no entra en la prosa salvo que sea el asunto.**
    Nombres de constantes, de variables, de funciones y rutas de archivo
    interrumpen la lectura, y el registro del autor no los usa: sus
    informes citan normas, resoluciones y fuentes de dato, no
    identificadores de código. La prosa dice **de dónde sale el dato**,
    no **cómo se llama en el programa**.

    Dónde sí cabe, y solo ahí:

    - En la atribución de procedencia de una figura o una tabla, dentro
      de `\fuente{}` o al cerrar un `\notafig{}`. Citar la carpeta de
      datos o el artefacto canónico es justamente el hábito del autor
      al escribir «Elaboración propia a partir del Formato 1».
    - Cuando la pieza de software es el objeto de la subsección. El
      capítulo 3 trata del pipeline y el 6 del solucionador, de modo que
      ahí nombrar el módulo informa en vez de estorbar. Aun así con
      moderación: el nombre del módulo, no el de cada constante.
    - En el Anexo A, que existe para eso.

    Dónde no cabe: en prosa corriente, y sobre todo como justificación de
    algo que se justifica mejor por su razón de fondo. El caso que
    originó esta regla está en C-12: el orden de las instituciones no se
    justifica diciendo qué constante lo fija, sino diciendo que
    mantenerlo fijo permite comparar los dos paneles de cada figura sin
    volver a buscar quién ocupa cada fila.

    Prueba rápida: si al quitar el nombre técnico la frase sigue diciendo
    lo mismo, sobraba.

---

## 2. Cómo se trabaja

**Antes de tocar nada, correr la compuerta.** Todo script de figuras empieza
con `datos.verificar_canon()`. Si sale en rojo, se detiene el trabajo: es
preferible no generar figura a generarla desde un artefacto movido.

**Acceso a los datos.** Solo por `scripts/datos.py`:

| Necesito | Llamada |
|---|---|
| Ganancia y métricas por mecanismo | `datos.resumen('m1')` — SC/SS ya corregidos |
| Ganancia por institución | `datos.por_agente('m3')` — A1..A5 ya traducidos |
| Quién vende y quién compra | `datos.reparto_p2p('m1')` |
| Flujos hora a hora | `datos.flujos_p2p('m3')` |
| Datos de una figura canónica | `datos.sibling('m1', 'fig5_comparacion_regulatoria')` |
| Estados del preprocesamiento | `datos.preproceso('m1')` |
| Conteos medidos del pipeline | `datos.conteo_negativas('m1')` |
| Cualquier hoja de los libros | `datos.hoja('m1', 'analisis', 'SA1_PGB')` |
| Serie diaria / bootstrap | `datos.serie_diaria('m1')`, `datos.bootstrap('m1')` |
| Índices de Sobol | `datos.indices_sobol('m1')` |

**Dibujo.** Solo por `scripts/estilo.py`: `E.figura()`, `E.figura_m1_m3()`,
`E.figura_antes_despues()`, y siempre `E.guardar(fig, nombre, datos=...,
procedencia=[...])`. Nunca `plt.savefig` a mano: se perdería el rastro.

**Compilación.**

```powershell
cd reformateo/documento
pdflatex --enable-installer -interaction=nonstopmode main
bibtex main
pdflatex --enable-installer -interaction=nonstopmode main
pdflatex --enable-installer -interaction=nonstopmode main
```

**Redacción.** Se puede reaprovechar prosa de `Documentos/FinalTesisV2/tesis.md`
donde ya dice lo correcto, pero **recortándola y reordenándola**: la tesis
está escrita en orden clásico y este documento está en orden de proceso. Todo
el detalle de pipeline —los capítulos 2 a 5 y el 9— hay que escribirlo de
cero, porque hoy no existe en ninguna parte.

---

## 3. Trampas documentadas

Van en `\begin{trampabox}` cuando aparecen en el texto.

| # | Trampa | Consecuencia para quien redacta |
|---|---|---|
| T1 | Las columnas `SC` y `SS` del libro canónico están **intercambiadas** respecto a su semántica. | Usar `datos.resumen()`, que devuelve `autoconsumo` y `autosuficiencia` con el nombre correcto. Se comprueba por física: en M1, con 19,1 % de cobertura, 0,98 no puede ser autosuficiencia. |
| T2 | **M1 y M3 invierten los papeles.** En M1 Udenar aporta el 76,3 % de lo vendido y UCC absorbe el 36,3 % de lo comprado; en M3 vende HUDN (33,9 %) y Cesmag absorbe el 70,9 %. | Cualquier frase con superlativo se comprueba con `reparto_p2p()` para esa cobertura. |
| T3 | **C4 tiene tres versiones**: Caso 1 horario (superada, no se publica como resultado), Caso 2 horario (`C4`) y Caso 2 mensual (`C4_mensual`, la que rige). | Al citar C4 siempre se dice cuál. La del Caso 1 solo aparece en el capítulo 9, rotulada como decisión superada. |
| T4 | **En M3, `C4_mensual` supera al P2P** (39,09 M frente a 34,55 M COP). | Es un hallazgo, no un error. Se reporta explícitamente. |
| T5 | **`C2` y `C3` son idénticos por construcción** tras corregir C2 a bolsa horaria. | No se presentan como dos resultados independientes; se explica por qué coinciden. |
| T6 | El `git_hash` que registran las hojas `Diagnostico` es `dc7c0e7`, pero el commit reproducible del canon es **`5c5baa2`**. | El anexo de reproducibilidad cita `5c5baa2`. |
| T7 | El docstring de `data/preprocessing.py` cita **989 h** de demanda negativa para Udenar; medido sobre el horizonte canónico son **1.517 h** (24,7 %). El propio docstring es inconsistente (su primer párrafo dice «~20 %»). | Se citan las cifras medidas, que salen de `conteo_negativas()`. Nunca las del docstring. |
| T8 | Las figuras de `Presentacion/tesis_p2p/` salen del canon de **junio**: llevan C4 en Caso 1 y el bootstrap viejo. | No se reutiliza ninguna. Todas se regeneran. |

---

## 4. Estado de la infraestructura

Listo y verificado:

- `scripts/estilo.py` — paleta, tipografía, formato español, constructores
  de figura, guardado con rastro.
- `scripts/datos.py` — puerta única a los datos, con compuerta del canon y
  corrección de los rótulos SC/SS.
- `scripts/cache_crudo.py` — estados intermedios del preprocesamiento.
  **Verificado contra el pipeline real: `max|dif| = 0` en las diez series.**
- `scripts/bootstrap_remuestras.py` — recupera las 10.000 réplicas del
  remuestreo. **Reproduce el canon dígito a dígito en las diez cifras.**
- `main.tex` + 21 archivos de sección — compila limpio con bibliografía IEEE.
- `datos_cache/` — caché del preprocesamiento y réplicas del remuestreo.

**39 figuras generadas**, todas con su `.csv` y su `.fuente.txt`:

| Script | Figuras | Qué cubre |
|---|---|---|
| `gen_cap02.py` | 3 | censo de fuentes, cobertura, horizonte |
| `gen_cap03.py` | 11 | preprocesamiento, perfiles, matrices, ritmos |
| `gen_cap04.py` | 4 | cobertura, perfiles M1/M3, inversión de papeles, embudo |
| `gen_cap05.py` | 4 | bolsa, costo unitario, categorías tarifarias, banda |
| `gen_cap09.py` | 2 | las tres versiones de C4, reproducibilidad entre corridas |
| `gen_cap10.py` | 4 | mercado horario, mensual, ranking, por institución |
| `gen_cap11.py` | 4 | barridos locales, Sobol, aditividad, lado corto |
| `gen_cap12.py` | 4 | cumplimiento, racionalidad individual, equidad, escala |
| `gen_cap13.py` | 3 | serie diaria, remuestreo, tamaño del efecto |

Pendientes de generar: los 17 diagramas TikZ restantes y las 6 figuras de
MATLAB. Cinco figuras del canon **no son regenerables** por falta de datos;
ver H-5 en `HALLAZGOS.md`.
las 27 fuentes crudas), los 17 diagramas TikZ, y las 6 figuras de MATLAB.
Cinco figuras del canon **no son regenerables** por falta de datos; ver
H-5 en `HALLAZGOS.md`.

---

## 5. Encargo por capítulo

Notación de la columna «estado»: **N** = figura nueva, hay que crearla ·
**R** = existe en el canon, hay que regenerarla con el estilo unificado ·
**T** = diagrama TikZ, se dibuja en LaTeX · **✓** = ya generada.

### Capítulo 1 — Introducción y pregunta regulatoria

Contexto de transición energética y comunidades energéticas; el problema
(¿un mercado dinámico entre pares rinde más que la asignación administrativa
que fija la regulación?); la pregunta-columna, formulada admitiendo que la
respuesta podría ser que no; objetivos y actividades; aportes; y el mapa del
proceso, que prefigura el documento entero.

| Fig. | Qué muestra | Estado | Fuente |
|---|---|---|---|
| 1.1 | Mapa del proceso completo, de la medición a la cifra | T | — |
| 1.2 | Jerarquía normativa colombiana | T | `Documentos/regulacion/` |

Justifica: por qué cinco instituciones de Pasto y no un caso sintético; qué
aporta frente a Chacón et al.; el alcance y lo que queda fuera.
Fuente de prosa: `tesis.md` §1, `Documentos/PropuestaTesis.txt`.
**No** incluye ninguna cifra de resultado.

### Capítulo 2 — El dato crudo

Qué se midió, dónde y con qué instrumento. Veinte medidores eléctricos
(`totalActivePower`, kW, resolución de 2 min) y siete inversores
(`acPower`, W) repartidos en cinco instituciones. Por qué el horizonte
empieza el 2025-04-04 y termina el 2025-12-16: el inversor de HUDN arranca
esa fecha y los Fronius de Udenar caen a mediados de diciembre.

| Fig. | Qué muestra | Estado | Fuente |
|---|---|---|---|
| 2.1 | Las cinco instituciones y su instrumentación | T | `data/preprocessing.py` |
| 2.2 | Gantt de cobertura de las 27 fuentes | N | `scripts/plot_coverage_gantt.py` |
| 2.3 | Cobertura por medidor e inversor | N | `Documentos/reporte_calidad_datos_MTE.md` |
| 2.4 | El recorte del horizonte y su motivo | N | caché + `xm_data_loader.py` |

Justifica: por qué un solo medidor de demanda y un solo inversor por
institución, y no la suma de todos los CSV de la carpeta.
Declara con honestidad: el inversor «MTE — Udenar» solo cubre el 39,3 % del
horizonte porque arrancó en septiembre.

### Capítulo 3 — La domesticación del dato

El capítulo central. Una subsección por etapa del pipeline, cada una con su
antes y su después.

| Fig. | Qué muestra | Estado | Fuente |
|---|---|---|---|
| 3.1 | El pipeline en seis etapas | T | `data/preprocessing.py` |
| 3.1b | **Una hora real, del archivo a la serie** | ✓ | `MedicionesMTE_v3/UCC/` + caché |
| 3.2 | La demanda que llega en negativo | ✓ | `f3_02_demanda_negativa_{m1,m3}` |
| 3.2b | **La gradación del neteo, en lecturas ordenadas** | ✓ | caché de estados intermedios |
| 3.3 | **Reconstrucción net→bruta: antes y después** | ✓ | `f3_03_reconstruccion_m1` |
| 3.4 | Los tres tipos de medidor | T | `DEMAND_METER_CONFIG` |
| 3.5 | Atípicos e imputación | ✓ | `f3_05_outliers_imputacion_{m1,m3}` |
| 3.7 | Las matrices D y G resultantes (hora × día) | N | caché |
| 3.8 | Perfiles por institución | N | caché |
| 3.9 | Ritmo semanal: hábil frente a fin de semana | N | caché |
| 3.10 | Ritmo anual: hora × mes | N | caché |

Cifras medidas, ya disponibles en `conteo_negativas()`:

- Udenar, medidor `net`: **1.517 h** bajo cero (24,7 % del horizonte),
  mínimo **−33,57 kW**, concentradas entre las 11 y las 15 h.
- Mariana, `net_partial`: 213 h. UCC, `net_partial`: 94 h.
- HUDN y Cesmag, `gross`: ninguna.

Justifica: (i) por qué un valor negativo prueba que el medidor netea y no
que hay ruido —se concentra al mediodía solar—; (ii) por qué se revierte
sumando los inversores en vez de descartar las horas; (iii) el umbral de
atípicos `max(Q75 + 5·IQR, P99,5 × 1,2)` y por qué el piso evita recortar
picos operativos legítimos; (iv) los límites de imputación de 3 h y 24 h;
(v) la no-negatividad como contrato verificado, no como aspiración.

Cierra con la subsección **«Las decisiones que sesgan en contra del P2P»**:
el conjunto de elecciones conservadoras que hacen que la ventaja medida sea
una cota inferior. Es el argumento de credibilidad del documento.

### Capítulo 4 — La frontera de medición: M1 y M3

Dos coberturas que responden preguntas distintas, no dos versiones de la
misma. La bifurcación es en sí un resultado.

| Fig. | Qué muestra | Estado | Fuente |
|---|---|---|---|
| 4.1 | Las dos fronteras sobre el esquema eléctrico | T | configs de medidores |
| 4.2 | Cobertura 19,1 % frente a 91,2 % | N | caché (medido, no fijo) |
| 4.3 | Perfiles M1 y M3 lado a lado | N | caché |
| 4.4 | **La inversión de papeles** | N | `reparto_p2p()` |
| 4.5 | El embudo de horas de mercado | N | flujos + caché |

Cifras: M1 vende Udenar 76,3 % / compra UCC 36,3 %; M3 vende HUDN 33,9 % y
Udenar 30,5 % / compra Cesmag 70,9 %.
Justifica: Mariana no tiene submedidor en M3 y se representa escalando su
totalizador por 0,3 (una facultad). Hay que declararlo, no esconderlo.

### Capítulo 5 — La otra mitad del dato: los precios

| Fig. | Qué muestra | Estado | Fuente |
|---|---|---|---|
| 5.1 | Serie de bolsa XM | N | `datos.precios_bolsa()` |
| 5.2 | El techo de escasez sobre la serie | N | `datos.precios_escasez()` |
| 5.3 | Desglose del costo unitario | N | `datos.tarifas_cedenar()` |
| 5.4 | Tarifa mensual: oficial frente a comercial | N | ídem |
| 5.5 | **De escalar a matriz mensual: el impacto** | N | canon + `README.md` |
| 5.6 | Costo nivelado solar y el parámetro *b* | N | `data/xm_prices.py` |
| 5.7 | La banda de precios del juego | N | tarifas + bolsa |

Justifica la decisión más sutil del modelo: en el **juego** entra un precio
escalar comunitario, mientras que en la **liquidación** entra una matriz por
agente y por mes. Hay que explicar por qué, y qué implicaría no hacerlo.
Nota: 5.3, 5.4 y 5.7 hoy existen en la presentación con valores fijos en el
código; aquí se calculan desde el CSV.

### Capítulo 6 — El modelo P2P

Formulación pieza por pieza. Nueve subsecciones, una por elemento.

| Fig. | Qué muestra | Estado |
|---|---|---|
| 6.1 | La arena multiagente | T |
| 6.2 | Del recurso disponible al límite económico | N |
| 6.3 | Clasificación por relación generación/demanda | R (`fig2_clasificacion`) |
| 6.4 | El simplex y la conservación de la dinámica | T |
| 6.5 | Relajación lagrangiana: el precio sombra | T |
| 6.6 | Trayectorias de asignación | R (`fig22_convergencia_*`) |
| 6.7 | Trayectorias de precio | R (ídem) |
| 6.8 | Bienestar frente a iteración | N |
| 6.9 | El techo de liquidación por agente | N |

Justifica: alternancia frente a integración conjunta; dos iteraciones y su
semántica de mejor respuesta; ausencia de programa de respuesta a la
demanda con datos reales; invariancia del equilibrio que permite fijar dos
de los parámetros de costo en cero.

### Capítulo 7 — Verificación del solucionador

| Fig. | Qué muestra | Estado | Fuente |
|---|---|---|---|
| 7.1 | Prueba dorada contra el oráculo | N | `Documentos/copy/reference_h14.json` |
| 7.2 | **MATLAB frente a Python, caso 1** | N (MATLAB) | `validacion_convergencia/` |
| 7.3 | **MATLAB frente a Python, caso 2** | N (MATLAB) | ídem |
| 7.4 | El ciclo de período dos | N (MATLAB) | ídem |
| 7.5 | Volumen reproducible, precio degenerado | N | ídem |
| 7.6 | Sensibilidad al horizonte de integración | N | `t2_tspan_sensibilidad.py` |

Justifica el resultado más incómodo y más honesto del capítulo: el volumen
transado reproduce entre implementaciones con diferencia del orden de
10⁻¹², pero el precio no, porque el equilibrio es degenerado dentro del
ciclo. Es un resultado sobre el modelo, no un fallo de la traducción.

### Capítulo 8 — Los escenarios como algoritmos

Cada escenario con su norma, su pseudocódigo horario y su diagrama.

| Fig. | Qué muestra | Estado |
|---|---|---|
| 8.1 | Los seis mecanismos sobre una misma vara | T |
| 8.2 | C1: excedente Tipo 1 y Tipo 2 | T |
| 8.3 | C2: la cadena de refinamiento regulatorio | T |
| 8.4 | **C4: el árbol de decisión del artículo 20** | T |
| 8.5 | C4: participación de cada institución | N |
| 8.6 | C5: la compensación remota | T |
| 8.7 | P2P: la liquidación del residual | T |

El argumento central de 8.4: con cinco fronteras comerciales, el Caso 2 del
artículo 20 es aritméticamente inevitable, porque exigir que ningún usuario
supere el 10 % de participación requiere al menos once. Conviene mostrarlo
como desigualdad, no afirmarlo.

### Capítulo 9 — Cómo evolucionó el modelo

Solo las decisiones que movieron cifras, cada una en un `decisionbox` con su
figura de antes y después. El registro completo va al Anexo B.

| Fig. | Qué muestra | Estado |
|---|---|---|
| 9.1 | Línea de tiempo de las decisiones | N |
| 9.2 | Tarifa escalar frente a matriz mensual | N |
| 9.3 | **Las tres versiones de C4** | N |
| 9.4 | La depuración de artefactos | T |
| 9.5 | Reproducibilidad entre corridas | N |

Incluye una subsección de **hallazgos que se cayeron al comprobarlos**. Es
lo que distingue una memoria de proceso de un informe de resultados: se
documenta lo que se creyó y resultó falso, con la prueba que lo refutó.

### Capítulos 10 a 13 — La evidencia

Aquí sí aparecen los resultados, y en orden estrictamente ascendente: hora,
día, mes, agregado. Casi todas las figuras son regeneración de siblings del
canon; el detalle está en la tabla maestra de la sección 6.

Las tres figuras que **no existen** y hay que crear:

- **11.8** — el mecanismo del lado corto: por qué la sensibilidad a la
  demanda se multiplica por 17 al pasar de M1 a M3. Fue una predicción
  enunciada antes de medirla, y se cumplió; conviene contarlo en ese orden.
- **13.2** — histograma del remuestreo con su intervalo. Requiere
  `scripts/bootstrap_remuestras.py`, que vuelve a correr el remuestreo con
  semilla 42 guardando las réplicas. Es determinista y **debe reproducir**
  8.114,14 (M1) y 10.579,11 (M3).
- **13.1** — la serie diaria de la diferencia, que es la entrada del
  remuestreo.

### Capítulos 14 y 15 — Cierre

Discusión y conclusiones. Se hereda y reordena `tesis.md` §8 y §9. Las
conclusiones van en espejo con los objetivos específicos, una por objetivo,
en pretérito.

---

## 6. Tabla maestra de figuras

Recuento por capítulo y estado. Total estimado: **≈75 figuras**, la mayoría
de dos paneles M1 | M3.

| Cap. | Nuevas | Regeneradas | TikZ | Ya hechas | Total |
|---|---|---|---|---|---|
| 1 | — | — | 2 | — | 2 |
| 2 | 3 | — | 1 | — | 4 |
| 3 | 4 | — | 2 | 3 | 9 |
| 4 | 4 | — | 1 | — | 5 |
| 5 | 7 | — | — | — | 7 |
| 6 | 3 | 3 | 3 | — | 9 |
| 7 | 6 | — | — | — | 6 |
| 8 | 1 | — | 6 | — | 7 |
| 9 | 4 | — | 1 | — | 5 |
| 10 | 1 | 11 | — | — | 12 |
| 11 | 2 | 6 | — | — | 8 |
| 12 | 1 | 6 | — | — | 7 |
| 13 | 3 | — | — | — | 3 |
| 14–15 | 1 | — | 1 | — | 2 |
| | **40** | **26** | **17** | **3** | **86** |

---

## 7. Verificación antes de dar por cerrada una sección

1. Compila sin error nuevo.
2. **Se midió con `scripts/medir_estilo.py`** y las cifras caen dentro
   de la tolerancia de la sección 10.1. Cero rayas largas, sin excepción.
3. **Las correcciones aplicadas quedaron anotadas en `CORRECCIONES.md`**
   y lo que no se pudo aplicar está en su tabla de pendientes.
4. Cada figura se refiere en el texto como «La Figura N + verbo», lleva
   su párrafo `\notafig{}`, y el capítulo cierra con párrafo bisagra.
5. Toda figura tiene `\fuente{}` y su `.fuente.txt` coincide.
6. Toda cifra se rastrea a un artefacto canónico.
7. Ningún superlativo sin comprobar contra la frontera correcta.
8. M1 y M3 aparecen los dos.
9. Las trampas que toca la sección están declaradas en su `trampabox`.
10. Todo nombre propio de entidad se comprueba contra `CORRECCIONES.md`
    antes de escribirlo: cuatro de las cinco han cambiado de
    denominación o llevan un componente que suele omitirse.
11. **Ningún nombre de constante, variable, función o ruta en la prosa**,
    salvo los tres casos que admite el invariante 10. Al releer, quitar
    cada uno y comprobar si la frase pierde algo; si no lo pierde, sobraba.
11. Al terminar todas: barrido de superlativos sobre el documento
    completo y recuento de `\ref` rotas.

---
## 8. Estado de la redaccion

| Cap. | Estado | Notas |
|---|---|---|
| 1 | pendiente | requiere los dos diagramas TikZ de apertura |
| **2** | **redactado** | 3 figuras + 1 trampabox (H-6) |
| **3** | **redactado** | 5 figuras + 2 TikZ + 1 tabla; el mas largo |
| **4** | **redactado** | 4 figuras + 1 TikZ |
| **5** | **redactado** | 4 figuras |
| 6-15 | pendiente | figuras ya listas para 9, 10, 11, 12 y 13 |

La Parte I (el dato) esta completa. El documento compila limpio, sin
referencias cruzadas rotas, en 59 paginas.

### Notas del entorno LaTeX

1. **No usar `siunitx`.** MiKTeX 24.1 distribuye un `expl3` anterior al
   `siunitx` que instala, de modo que falla con
   `\l_siunitx_quantity_prefix_mode_str` indefinido. El documento usa
   `numprint` con los macros `\num`, `\uni` y `\pct`.
2. **`\pct` solo funciona en modo texto.** `babel-spanish` redefine el
   simbolo de porcentaje con una macro que inspecciona `\lastskip`, y
   dentro de `$...$` aborta la compilacion con «Incompatible glue
   units». Escribir `$\pm$\,\pct{0.3}`, nunca `$\pm\pct{0.3}$`.
3. **`\cal` esta tomado** por LaTeX 2.09 (fuente caligrafica). El macro
   de decisiones tecnicas se llama `\CAL`.
4. **Llaves de TikZ.** La decoracion `brace` abomba hacia la izquierda
   del sentido de avance: para que una llave horizontal quede *debajo*
   de lo que agrupa, hay que trazarla de este a oeste.

---

## 10. Perfil de estilo del autor (medido)

Perfil obtenido de su corpus real: siete fuentes LaTeX de 2022-2024,
dos informes en PDF de 2024 y los tres informes MTE de julio de 2026
(~52.700 palabras de prosa, autoría verificada dentro de cada archivo).
**Su registro actual es el de 2026**, que difiere bastante del de 2023;
es ese el que hay que imitar.

### 10.1 Cifras objetivo

| Rasgo | Objetivo | Tolerancia |
|---|---:|---|
| Palabras por oración | 24,6 | 22-27 |
| Oraciones de más de 40 palabras | 12 % | hasta 15 % |
| Palabras por párrafo | 74 | 60-90, nunca >130 |
| Oraciones por párrafo | 3,2 | 3-4 |
| «es decir» por mil palabras | 1,24 | no bajar de 0,9 |
| Punto y coma por mil | 2,5 | más alto solo si hay enumeraciones largas |
| **Raya larga (—) por mil** | **0,00** | **cero, sin excepción** |

Medir con `scratchpad/medir_estilo.py` antes de dar un capítulo por
cerrado.

### 10.2 Las diez reglas

1. **Impersonal con «se», siempre.** «Se calculó», «se identificaron»,
   «se deja recomendado». Cero primera persona, cero «el autor». En su
   corpus de 2026 no hay una sola excepción en 20.238 palabras.
2. **Prohibida la raya larga (—).** Los incisos van entre comas o entre
   paréntesis. La raya corta (–) solo para rangos: «1,6–3,3 años».
3. **Glosar en lengua llana** todo término técnico o cifra opaca, con
   «es decir,» / «entendido como» / «esto es,», inmediatamente después.
   Es su tic más reconocible.
4. **Referir las figuras como «La Figura N + verbo»**, al final del
   párrafo que la motiva. Verbos que usa: ubica, reúne, muestra, pone,
   resume, presenta, cruza. **Nunca** «(Figura N)», «se observa en la
   Figura N» ni «véase».
5. **Párrafo `\notafig{}` bajo cada figura**, que diga lo que la figura
   revela y el texto no, y cierre con la procedencia («Elaboración
   propia a partir de…»).
6. **Cerrar cada capítulo con un párrafo bisagra** que empiece por «En
   síntesis,», «Con todo lo anterior,», «En conjunto,», «De esta
   manera,» o «En consecuencia,», recoja la cifra clave y **anuncie
   explícitamente el capítulo siguiente**.
7. **Enumeraciones con ordinales explícitos** («Primero… Segundo…
   Tercero…») y punto y coma para separar miembros largos.
8. **Coma decimal y punto de miles, un decimal por norma.** Usar
   `\num{}`, `\uni{}` y `\pct{}`.
8b. **Las unidades van entre paréntesis, nunca entre corchetes ni tras
    barra.** Es la norma editorial de IEEE, que rige el formato de este
    documento: «Write the quantity *Magnetization (A/m)*, not just *M*»,
    y advierte expresamente contra rotular un eje con la barra de
    cociente. Vale igual para el texto y para los rótulos de figura:
    «la potencia activa total (kW)», «Ganancia neta (COP)»; nunca
    «[kW]» ni «Magnetization/K». Se usa el sistema internacional. En un
    rótulo de eje se nombra siempre la magnitud, no solo la unidad.
9. **Adjuntar la fuente a cada cifra** y **declarar las limitaciones en
   voz alta**: «tiene carácter ilustrativo…, no constituye…», «se trata
   de un análisis simplificado: … excede el alcance de… y se deja
   recomendado para…», «por transparencia metodológica, …».
10. **Anglicismos: español primero, inglés entre paréntesis**, glosa si
    hace falta. «topología de centro y radios (hub-and-spoke)».

### 10.3 Lo que NO es suyo (no escribirlo)

- «cabe destacar», «cabe mencionar», «es importante mencionar»: 2 y 0
  apariciones en todo el corpus. No son suyas.
- La grandilocuencia de su etapa 2023: «se erige como», «abre la puerta
  a», «sienta las bases», «juega un papel fundamental», «es imperativo
  destacar». La abandonó.
- Remates de sección con aforismo. Los suyos son **lectura del dato**,
  apoyados en dos puntos: «*…el 1,8 % del total: es el intervalo en que
  el plan puede operar con recursos mínimos*». Y el cierre de sección
  propiamente dicho es **largo y bisagra**, no corto.
- Punto decimal, viñetas de conclusiones, decimales espurios
  («70.2751 bpm»). Todo eso es de 2023.

### 10.4 Estado del ajuste

Los capítulos 2 a 5 pasaron el ajuste de registro el 2026-08-22:
58 rayas largas convertidas a paréntesis o comas, 17 párrafos
`\notafig{}` añadidos, 9 referencias «La Figura N + verbo» y 3 cierres
bisagra. Residuo conocido: «es decir» queda en 0,89 por mil frente a
1,24 del objetivo; forzarlo más sonaría artificial.

11. **Cifras o palabras (norma RAE, ver C-27).** El texto es técnico, de
    modo que la base son las cifras. De cero a nueve, palabras, salvo que
    siga un símbolo de unidad. De diez en adelante, cifras. Cifras siempre
    con símbolo de unidad. No mezclar en un mismo enunciado ni en una
    serie: si un miembro pasa a cifras, pasan todos. Los títulos van en
    palabras y ninguna oración se abre con cifra.
