# GSA sobre datos reales — plan de ejecución en el servidor

**Para los agentes que ejecuten esto: lean esta sección entera antes de correr nada.**

---

## Qué problema resuelve

`analysis/global_sensitivity.py` **no corre sobre el caso de estudio**. Corre sobre el
caso sintético de 6 agentes y 24 horas del modelo base. No está oculto — el propio
orquestador lo declara y rechaza la combinación:

```python
# main_simulation.py:1505
ap.error("--gsa corre el modelo de referencia sintético y es "
         "incompatible con --full/--analysis/--include-c5/--paper-meters/--day")
```

El problema es que **la tesis (§7.1, §7.10) y el artículo lo narran como si
caracterizara el benchmark de 6 144 h**. Los índices publicados son reales y están bien
calculados; lo que no es cierto es sobre qué se calcularon.

---

## El diseño: cinco parámetros, no siete

El GSA sintético barre siete. Aquí se barren **cinco**, y las dos exclusiones no son un
atajo: son consecuencias del caso de estudio que hay que reportar.

| Parámetro | Soporte | Nota |
|---|---|---|
| `PGB` | [114, 500] COP/kWh | idéntico al sintético porque el 114 **es** el piso adimensional del modelo base; cota de estrés declarada, no normativa (CAL-42) |
| `PGS` | **[600, 1000]** COP/kWh | **ampliado**: el escalar real del juego es **906,27** y quedaba fuera del [500,750]. Ver las tres salvedades abajo |
| `factor_PV` | [0.5, 2.0] | idéntico |
| `factor_D` | [0.7, 1.5] | idéntico |
| `b_mean` | [150, 400] COP/kWh | idéntico; el real es 225–241 |

**`alpha_mean` se excluye.** El orquestador **no pasa `alpha`** en datos reales, de modo
que el programa de respuesta a la demanda queda apagado — es la premisa «SIN DR» de toda
la tesis. Barrerlo mediría un mecanismo que el caso no tiene, y activaría en cada muestra
un SLSQP de N·T variables que sobre 6 144 h vuelve la evaluación impracticable.
**Consecuencia para el manuscrito: del caso de estudio no se puede afirmar nada sobre
flexibilidad de demanda.** El ST de 0,008 que hoy se publica es del caso sintético.

**`pi_ppa` se excluye.** Solo entra en C2 y ninguna de las tres salidas viene de C2: su
índice es cero *por construcción*, no por medición. Barrerlo gastaría una dimensión en
ruido.

**Tres salvedades del soporte de PGS**, que hay que declarar al publicar su índice porque
no son neutrales:

1. **Bajo el barrido** la matriz de liquidación recorre **[512,1 – 1081,8]**, no el
   [773,5 – 980,4] del nominal.
2. **Es asimétrico.** El nominal 906,27 cae en el **percentil 76,6** del soporte: el diseño
   explora −33,8 % por debajo y solo +10,3 % por encima, de modo que el índice de PGS queda
   gobernado por la rama descendente.
3. **El tramo [600, 671] no es alcanzable.** Con los cargos regulados reales
   (T+D+PR+Rm+Cvm+COT = 492,44 COP/kWh sobre un CU base NT2 de 797,04) el piso físico es
   559,9, y PGS=600 exigiría una generación de 35,25 COP/kWh — por debajo del mínimo
   horario de bolsa observado (97,86). Es el 17,8 % del ancho del soporte.

En conjunto: **el índice de PGS mide respuesta a un rango contrafactual de estrés, no a la
incertidumbre tarifaria real** — los 13 meses del CSV Cedenar solo recorren [871,9 – 928,9],
un ±3 %. Legítimo, pero hay que decirlo.

**Alcance del desdoble de `pi_gs`.** De las tres salidas **solo `ganancia` ve la matriz de
liquidación**: `sc` es física (volúmenes) e `ie` sale de `r.IE`, que usa exclusivamente el
escalar. Es fiel a producción, donde el IE también es escalar.

**Tamaño del diseño:** con `calc_second_order=False` (S2 no se usa en el informe),
`M = n_base × (D+2) = n_base × 7`. Con `n_base=128` son **896 evaluaciones**.

---

## Qué más cambia respecto del GSA sintético

| # | Cambio | Por qué |
|---|---|---|
| 1 | Datos reales del MTE, cobertura M1 o M3 | Es el punto del ejercicio |
| 2 | Solucionador **idéntico al del orquestador** en datos reales (`main_simulation.py:259`) | Lo que el sintético relaja no es la ODE —usa los *defaults*, más caros— sino el criterio de Stackelberg (`tol=5e-3, max=4` frente a `1e-3, 10`) |
| 3 | `a = c = 0` | Convención del caso de estudio (CAL-32) |
| 4 | `prosumer_ids = range(N)` **fijo** | Clasificar dinámicamente cambiaría la *definición* de la métrica dentro del hipercubo: donde hay poco sol la lista se encoge y la ganancia salta decenas de puntos, y Sobol lo atribuiría al modelo |
| 5 | `pi_bolsa` = serie real **sin reescalar**; `PGB` mueve solo el piso del juego | Reescalarla derogaba en silencio el techo CREG 101 066 y producía precios de hasta 6 094 COP/kWh, ocho veces la tarifa |
| 6 | Semilla fija en el remuestreo de los IC | El canónico no la fijaba y sus intervalos no eran reproducibles |
| 7 | Caché en `.npz` | Sin ella cada evaluación relee 609 MB del dataset |
| 8 | Huella del diseño + verificación de procedencia | Impide que dos corridas distintas se mezclen bajo los mismos índices |
| 9 | `pi_gs` **desdoblado**: escalar al juego, matriz `(N,T)` a la liquidación, movida proporcionalmente por el barrido | Es lo que hace producción (`main:104-119`). Colapsarlo en un escalar valoraba el autoconsumo —el 93 % de la ganancia P2P— a una tarifa que ninguna institución paga, y desplazaba la ganancia del punto nominal en torno a un 1 % |

---

## Requisitos

```bash
cd /home/brayan_lopez/sistemabl
export MTE_ROOT=/home/brayan_lopez/sistemabl/MedicionesMTE_v3
python -c "import SALib, numpy, pandas, scipy; print('OK')"
python -c "import multiprocessing as m; print('arranque:', m.get_start_method())"
```

El lanzador exporta por su cuenta `PYTHONIOENCODING=utf-8` y limita los hilos de BLAS a
uno por proceso. No hace falta hacerlo a mano.

**Comprobación de traslado, antes de nada.** `gsa_real/` no está bajo control de versiones,
así que si el traslado fue por scp/WinSCP en modo texto o por ZIP, el `.gitattributes` de la
carpeta no interviene y el `.sh` puede llegar con CRLF. Un `\r` dentro de una asignación
rompe el lanzador con un «no such file» desconcertante:

```bash
grep -c $'\r' gsa_real/run_servidor.sh    # tiene que ser 0
# si no lo es:  sed -i 's/\r$//' gsa_real/run_servidor.sh
```

**Cuántos procesos abre.** Cada worker lanza a su vez un hijo que es el que calcula — así se
impone el timeout por muestra —, de modo que el árbol tiene **2·workers + 1** procesos, no
`workers`. La CPU la consumen solo los nietos (≈ `workers` núcleos), pero la RAM la ocupan
los `2·workers` intérpretes con numpy/scipy cargados. Dimensionar `--workers` por memoria,
no por núcleos. Y si el OOM-killer mata a un worker, su nieto **sobrevive huérfano**: tras
un `POOL ROTO`, revisar con `pgrep -f 2_correr_gsa.py` y matar lo que quede antes de
reanudar.

---

## Los tres pasos

### Paso 1 — Calibrar. **No se salta.**

```bash
bash gsa_real/run_servidor.sh calibrar M1 full 128
```

Cinco sondas reales cronometradas, de la más barata a la más cara, **cada una con
timeout de 30 min** para que ninguna bloquee el paso. Proyecta el costo total y
recomienda el timeout de producción.

Al final imprime una de dos cosas: el comando exacto a lanzar, o las opciones si no cabe
en 12 h. **Preferir acortar el horizonte antes que bajar `n_base`**: con `n_base` bajo
los intervalos salen tan anchos que la comparación deja de informar.

### Paso 2 — Correr

```bash
# el 5º argumento es el timeout que recomendó el paso 1
bash gsa_real/run_servidor.sh correr M1 full 128 1800
```

**Antes de lanzar nada, el lanzador corre una corrida de humo real** con `n_base=1`
(7 evaluaciones, semilla 999 para no colisionar) y aborta si falla. No es paranoia: el
preflight anterior solo hacía `--help`, que no ejecuta el cuerpo de `main()`, y por eso dejó
pasar un desempaquetado desajustado que reventaba tras 14 s de carga —con el paso 1 dando
«CABE, lanzar…» justo antes. Cuesta unos minutos y cubre el camino entero: firmas, caché,
escritura del CSV.

Queda en segundo plano. El lanzador **espera hasta 180 s a que el bucle arranque de
verdad** — la carga del dataset tarda decenas de segundos, así que comprobar a los 5 s
vería vivo un proceso que va a morir leyendo. Si murió al arrancar, muestra el log y sale
con error en vez de decir que va todo bien. También pone un cerrojo: dos corridas
simultáneas sobre el mismo CSV lo truncan y lo reescriben a la vez, y quedan índices
duplicados que dejan el fichero inanalizable.

```bash
tail -f gsa_real/salidas/run_gsa_M1_full_n128_s42.log
wc -l gsa_real/salidas/muestras_M1_full_n128_s42.csv        # progreso
grep -c '\[xm_csv\]' gsa_real/salidas/workers/*.log          # debería ser ~0
```

Ese último comando comprueba que la caché funciona: si sale un número grande, cada
evaluación está releyendo el dataset y hay que revisarlo.

**Si se interrumpe:**

```bash
bash gsa_real/run_servidor.sh reanudar M1 full 128 1800
```

Retoma lo que falta **y reintenta las que fallaron** — a diferencia de una versión
anterior, donde reanudar las saltaba y el consejo de «subir el timeout y reanudar» no
podía funcionar.

**Guardas que ya están puestas:** correr sin `--reanudar` sobre un fichero con datos
**aborta** en vez de truncarlo; reanudar con otra semilla, otro `n_base` u otro horizonte
**aborta** en vez de mezclar diseños; reanudar con **otros datos** bajo `MTE_ROOT`
también aborta, porque la huella del dataset queda registrada en el `.meta.json`.

Si un worker muere por OOM, `ProcessPoolExecutor` **no lo reemplaza**: rompe el pool
entero. La corrida lo detecta, corta la tanda dejando válido lo escrito, y lo dice. La
salida en ese caso es **bajar `--workers` y relanzar con `reanudar`**, no repetir el
mismo comando.

### Paso 3 — Analizar

```bash
bash gsa_real/run_servidor.sh analizar M1 full 128
```

**La semilla no es el 5.º argumento.** Ese hueco es siempre el timeout y solo lo usan
`correr`/`reanudar`. Si hiciera falta otra semilla, va por entorno y hay que usar la
misma en los tres pasos:

```bash
SEMILLA=7 bash gsa_real/run_servidor.sh correr   M1 full 128 1800
SEMILLA=7 bash gsa_real/run_servidor.sh analizar M1 full 128
```

**Antes de calcular nada verifica la procedencia:** que haya exactamente `n_base × 7`
filas, que los índices sean 0..M−1 sin huecos ni duplicados, y que las columnas de
parámetros coincidan con la matriz regenerada con la semilla declarada. Si algo no cuadra,
aborta.

Ojo con el alcance de esa comprobación: la matriz regenerada depende **solo** de
(soportes, `n_base`, semilla), de modo que es idéntica para M1 y M3, para `full` y para un
mes suelto, y para cualquier `MTE_ROOT`. Verificarla **no dice nada sobre qué datos se
corrieron**. Eso solo consta en el `.meta.json`, así que el análisis lo lee, contrasta
cobertura y horizonte contra el nombre del fichero, y arrastra la huella de datos al
informe.

---

## Qué mirar en el informe

**1. ¿Se conserva el parámetro dominante de cada salida?** Y ojo: el informe dice si el
dominante está **separado del segundo** por sus intervalos. Si no lo está, con este
diseño no se puede afirmar cuál domina.

**2. ¿Se sostiene la cota del 0,9 %?** Se adjudica contra el **extremo superior del
intervalo**, no contra el valor puntual. Si el intervalo cruza el umbral, el informe dice
que la afirmación **no es resoluble** en vez de inventar un veredicto. Y aplica la misma
regla a la referencia sintética que originó la afirmación: allí `b_mean` da extremo
superior 1,15 % y `alpha_mean` 1,73 %, de modo que **la cota ya era no resoluble sobre los
propios datos que la produjeron**. Lo que salga aquí no es un descubrimiento del caso
real.

**3. ¿Cuántas barras tienen IC que contiene el cero?** El artículo declara 17 de 36. Con
cinco parámetros el denominador cambia (30, no 36); el informe da el recuento nuevo.

**Y antes que todo lo anterior: el código de salida.** `analizar` devuelve **3** si hay
alarmas de convergencia o si la corrida no cumple las condiciones de validez, y **0** solo
si las cumple. `correr` devuelve 4 si se rompió el pool, 5 si quedó incompleta, 6 si se
interrumpió. Un 0 es la única señal legible por máquina de que la corrida sirve.

**4. La comparación con el sintético es por solapamiento de intervalos**, no por una
diferencia fija — un umbral fijo estaría por debajo del error de Monte Carlo. `PGS` sale
marcado como no comparable, porque su soporte cambió.

---

## Qué devolver

Todo `gsa_real/salidas/`, y sobre todo estos dos juntos:

```
muestras_<tag>.csv        ← las evaluaciones crudas: el activo real
muestras_<tag>.meta.json  ← sin él, el análisis se niega a correr
```

Los índices se recalculan de ellos en segundos; regenerarlos cuesta la corrida entera.

---

## Advertencias

- **No modificar `analysis/global_sensitivity.py`.** El sintético se conserva: es la
  referencia de comparación y el *golden test* depende de él.
- **No esperar que `main_simulation.py --data real --full` haga el GSA.** No lo hace, y
  por diseño lo rechaza.
- Si algo falla en la carga de datos, el paso 1 lo detecta de inmediato: para eso existe.
