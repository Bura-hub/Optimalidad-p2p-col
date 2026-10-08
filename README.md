# Análisis de optimalidad y validación regulatoria de mercados P2P en Colombia

Código de la tesis de maestría y del artículo que se deriva de ella.

- **Tesis:** *Análisis de optimalidad y validación regulatoria de mercados P2P
  en Colombia*. Maestría en Ingeniería Electrónica, Universidad de Nariño, 2026.
- **Artículo:** *Peer-to-Peer Energy Markets for Colombian Energy Communities:
  Network Charges, Settlement Rules, and a Collective Alternative*, preparado para
  IEEE Latin America Transactions.
- **Autor:** Brayan S. López-Méndez. **Asesores:** Andrés Pantoja y Germán Obando.
- **Modelo base:** Chacón et al. (2025), el mercado entre pares por dinámica de
  replicador y relajación lagrangiana.
- **Datos:** proyecto MTE, «Desarrollo de un modelo transaccional de energía no
  convencional de múltiples agentes para el departamento de Nariño» (BPIN
  2021000100499).

Un solo repositorio sirve a la tesis y al artículo, porque los dos usan el
mismo motor, la misma liquidación y el mismo conjunto de resultados. El
artículo toma 5 de los 13 casos de la tesis (sección
[Cómo reproducir el artículo](#cómo-reproducir-el-artículo)).

---

## Qué hace

Simula un mercado de energía entre pares (P2P) en una comunidad de cinco
instituciones de Pasto con generación solar y lo compara con los mecanismos
que la regulación colombiana ofrece para el mismo excedente. Cada mecanismo se
liquida como lo liquida su norma, hora a hora o mes a mes, con las mediciones
del proyecto MTE (abril a diciembre de 2025, 6144 horas).

La pregunta es qué parte de la ventaja del mercado sobre la autogeneración
colectiva viene del mercado y qué parte de dos supuestos de liquidación que la
regulación vigente no contempla: que el residual de cada miembro se liquide
por su cuenta y que el intercambio interno no pague cargos de red. De ahí sale
una regla propuesta, el **P2P colectivo**, que da esas dos respuestas dentro
de la autogeneración colectiva.

**Qué es público y qué no.** Este repositorio publica el código y su
documentación de proceso. Las mediciones del MTE son datos del proyecto sobre
instituciones concretas, así que no se publican. Tampoco el conjunto de
resultados con huella (el canon, `Documentos/canon_2026-09/`, con las entregas
del servidor en `SALIDAS_SERVIDOR/`) ni los manuscritos, que los contienen
institución por institución. Por eso `Documentos/`, `SALIDAS_SERVIDOR/` y
`MedicionesMTE_v3/` están en `.gitignore`. Las mediciones se pueden pedir a los
autores, con las condiciones del proyecto. Este documento no publica cifras de
resultados.

---

## El modelo

**El juego es el del modelo base.** Vendedores y compradores con dinámica de
replicador y relajación lagrangiana, con las dos poblaciones integradas en una
sola ecuación diferencial, como el fichero original. El modelo base lo
presenta como un juego de Stackelberg. La tesis muestra que su condición de
equilibrio tiene estructura de Nash. La fidelidad se comprueba con una prueba
dorada contra el caso publicado (7 de 7, por la vía alternada, el defecto de <!-- vetada-ok: la prueba dorada corre por la alternada -->
`SolverParams`), con dos apartamientos declarados: la forma agregada del
término de competencia y el peso del jugador virtual.

**El mercado de cada hora se resuelve en el reposo, no integrando** (D48,
CAL-53, ADR 0060). Con un vendedor y varios compradores, la dinámica oscila
alrededor de un reposo que no alcanza (H-87). Con una regularización entrópica
en el replicador del vendedor, de μ = 1 (COP/kWh), sí llega (H-90). El motor
calcula ese reposo directamente (`--metodo reposo`, el defecto con datos
reales):

- **El piso del juego es el del vendedor marginal** (D63), el último que hace
  falta para cubrir la demanda. Los vendedores despachan por su alternativa
  regulada. Una caminata competitiva sobre los pisos decide quién entra y
  cuánta energía se transa. La hora sin ganancia posible queda sin mercado.
- **El nivel del precio lo fija un presupuesto**, que suma, por comprador, el
  piso más una fracción σ de su banda, con σ = (I − 1)/I por defecto y un
  barrido de σ (D50). El presupuesto decide el reparto, no el beneficio de la
  comunidad.
- **Cada comprador liquida al precio uniforme de la hora** que conserva el
  ingreso del reposo, sin pasar de su techo (D51).
- **En las horas frágiles, la rama cuantal** (D71). Donde la forma cerrada no
  es un reposo estable de la dinámica regularizada, se publica el reposo con
  μ = 1. En las horas reales cambia solo el reparto entre compradores.
  `--mu-cuantal 0` apaga la rama.

**La dinámica solo valida.** La vía **acoplada**, que integra precios y
cantidades juntos (LSODA con tolerancias relativa y absoluta de 1e-6, las del
original, H-51), queda para validar el reposo y dibujar su convergencia. Con
el criterio fijado de antemano (95 % de las horas de cada régimen dentro de
tolerancia, con cinco como mínimo), ningún régimen quedó verificado, ni en la
primera muestra de E0 ni en la validación ampliada a los 13 casos (C-368). La
forma cerrada es, por tanto, una **regla adoptada** en todos los regímenes.
Donde la dinámica no llega, lo que se aparta es sobre todo el precio, no la
energía transada.

**La banda de precios es aporte de esta tesis.** Donde el modelo base tiene
dos constantes exógenas, aquí hay dos cotas medidas de la regulación:

- **El techo** es el costo unitario de prestación del servicio (CU) de cada
  comprador, mes a mes.
- **El piso** es la alternativa regulada de cada vendedor, según el artículo 25
  de la Resolución CREG 174 y el Anexo 4 de la Resolución CREG 101 072. El
  excedente se reconoce como crédito hasta la importación del mes. Desde la
  hora en que la inyección acumulada la alcanza, se valora a la bolsa de cada
  hora.

Con esas dos cotas, para una planta de hasta 100 (kW) el ancho de la banda es
exactamente el componente de comercialización de la tarifa. Entre 100 (kW) y
1 (MW) se le suman los cargos de transmisión, distribución, pérdidas y
restricciones.

**Lo que se añadió para que el modelo funcione con datos reales:**

- una **restricción de participación**, por la que un vendedor se retira si el
  mercado le paga menos que su alternativa. Con el piso del vendedor marginal
  queda como **guarda inerte** (D67): los retiros deben ser cero, y uno solo
  detiene la corrida;
- el **techo por comprador en la liquidación**, para que nadie pague dentro de
  la comunidad más de lo que le costaría la misma energía en la red;
- un **paso de tiempo explícito**.

**Lo que protege la corrida:**

- **Plazo de 15 minutos por hora** en el lazo paralelo, en cualquier vía (una
  hora por reposo tarda milisegundos).
- **Código de salida 3** si alguna hora terminó con excepción, si la
  participación retiró a algún vendedor o si las horas vencidas por el plazo
  pasan del 1 %, para que una cadena de corridas se detenga.
- En la vía acoplada, **parada por estacionario** con horizonte doble hasta <!-- vetada-ok: la acoplada queda para validar -->
  0,4 dentro de un presupuesto de evaluaciones, **piso de 1e-10 para la oferta
  dentro de la dinámica** (H-84) y **corte al primer valor no finito**.

---

## Los mecanismos que se comparan

Los nombres son los de la tesis y el artículo. La última columna dice dónde
se calcula cada uno.

| Mecanismo | Qué liquida | Norma | Dónde |
|---|---|---|---|
| **Mercado P2P** | El mercado entre pares. El residual de cada miembro se liquida como en C1 y el intercambio interno no paga cargos: los dos supuestos que la regulación vigente no contempla. | | `main_simulation.py`, columna `P2P` |
| **P2P colectivo** | La regla propuesta. El intercambio no paga cargos ni entra al fondo común. Al fondo va solo el residual, repartido como en C4, sin la regla del 10 %. | propuesta sobre la CREG 101 072 | `reformateo/documento/scripts/articulo/p2p_comunitario.py` (`P2Pcom`) |
| **P2P mutualizado** | Escenario hipotético. Deduce cada kWh del fondo con el numeral de la planta que lo inyectó y solo exime del Cv al intercambio del numeral 1. | propuesta | `reformateo/documento/scripts/articulo/hibrido_por_planta.py` (`H1`) |
| **C1** | Autogeneración individual: crédito con la importación del mes, corte en la hora en que la inyección acumulada la alcanza y exceso a la bolsa horaria. Se deduce el Cv hasta 100 (kW) (numeral 1), y también transmisión, distribución, pérdidas y restricciones entre 100 (kW) y 1 (MW) (numeral 2). | CREG 174, art. 25; CREG 101 072, Anexo 4; CREG 101 087, art. 1 lit. i | `scenarios/scenario_c1_creg174.py` |
| **C2** | El contrato PPA de la propuesta: cada institución vende todo su excedente horario a precio pactado, sin crédito. | CREG 174, art. 23 | `reformateo/documento/scripts/articulo/c2_ppa.py` (`C2ppa`) |
| **C3** | Escenario hipotético sin norma: el excedente a la bolsa de cada hora, menos los costos del mercado mayorista. | | `scenarios/scenario_c3_spot.py` |
| **C4** | Autogeneración colectiva, liquidada mes a mes, con el fondo repartido en partes iguales y la deducción del caso del art. 20. | CREG 101 072; CREG 101 087, art. 1 lit. ii | `scenarios/scenario_c4_creg101072.py` |
| **C5** | Autogeneración remota: cada hora se despacha por contrato el mínimo entre la inyección y la importación agregadas. Es una referencia del régimen horario, **no elegible** para esta comunidad (C-228). | CREG 101 099, arts. 16 a 21 | `scenarios/scenario_c5_agr_creg101099.py` |

C2, C3 y C5 son referencias secundarias, sin crédito. El P2P colectivo, el
P2P mutualizado y el PPA se calculan como derivados del canon, sin volver a
simular el mercado: leen los flujos del mercado P2P de cada hora y
comprueban la huella de cada artefacto antes de leerlo.

**Columnas heredadas.** Los libros de `main_simulation.py` llevan todavía
tres columnas que la tesis ya no usa con ese nombre:
- `C2`, el contrato bilateral interno al punto medio de la banda (`scenario_c2_bilateral.py`), que la tesis sustituyó por el PPA de la propuesta;
- `P2P colectivo`, el mercado liquidado por la vía del colectivo en dos niveles (`scenario_p2p_colectivo.py`), que la tesis sustituyó por la regla del `P2Pcom`;
- `C4_mensual`, que desde C-175 es un alias exacto de C4 y no se cuenta aparte (C-218). <!-- vetada-ok: se declara como alias -->

La ficha de cada escenario, con su fórmula, sus precios y los supuestos que no
vienen de la norma, está en
[`reformateo/documento/ESCENARIOS.md`](reformateo/documento/ESCENARIOS.md).

---

## Instalación

**El entorno es exacto.** Con versiones distintas del integrador, el mismo dato
puede dar un resultado distinto (H-84), así que las corridas usan las versiones
fijadas en `requirements-lock.txt`, con **Python 3.13.7**:

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
```

Donde no haya Python 3.13, `uv` lo instala en el directorio del usuario, sin
permisos de administrador. La receta está en
[`modelo_base/MONTAJE_SERVIDOR.md`](modelo_base/MONTAJE_SERVIDOR.md), sección
«El entorno exacto (H-84)». `requirements.txt` queda con las versiones libres,
para desarrollo.

**Los datos no están en el repositorio.**

- **Mediciones del proyecto MTE.** Van en la carpeta `MedicionesMTE_v3/` de la
  raíz, o donde indique la variable de entorno `MTE_ROOT`.
- **Serie de precios de contratos de XM.** Va en
  `data/XM_Energía y Precios transados en contratos con destino a Mercado Regulado y No Regulado.xlsx`.
  Es pública, del portal de XM, pero el `.gitignore` excluye los `.xlsx`. Sin
  ella falla toda corrida que incluya C5.
- **Ficheros del modelo base.** La prueba dorada los necesita. Sin ellos salta
  sus comprobaciones y lo dice.

---

## Uso

```bash
# Caso sintético del modelo base, para comprobar la instalación (segundos)
python main_simulation.py

# Un día con datos reales (por el reposo, el defecto con datos reales)
python main_simulation.py --day 2025-07-15

# Un caso completo, con la orden de la matriz canónica (caso E0)
python -u main_simulation.py --data real --full --include-c5 --no-regulado \
    --metodo reposo --modo-presupuesto sigma --regla-precio uniforme \
    --despacho-vendedores piso --analisis-ligero \
    --almacen SALIDAS_SERVIDOR/matriz_reposo/E0/almacen \
    --out-dir SALIDAS_SERVIDOR/matriz_reposo/E0
```

Las opciones principales (todas en `python main_simulation.py --help`):

| Opción | Qué hace |
|---|---|
| `--metodo reposo` | El reposo del juego regularizado, en forma cerrada: el defecto con `--data real` o `--day`. `acoplado` integra la dinámica, para validar; `alternado` es el defecto del caso sintético. <!-- vetada-ok: opciones del motor --> |
| `--modo-presupuesto sigma`, `--sigma-nivel S` | El presupuesto de precios del reposo; `S` entre 0 y 1, o `base`, que es (I − 1)/I (D50). |
| `--regla-precio uniforme` | Liquida a cada comprador al precio uniforme de la hora (D51); `puja` es la sensibilidad. |
| `--despacho-vendedores piso` | Despacho por el piso de cada vendedor, con el piso del juego en el vendedor marginal (D63 a D65). |
| `--mu-cuantal MU` | La μ de la rama cuantal de las horas frágiles; 1 por defecto, 0 la apaga (D71). |
| `--include-c5` | Añade la autogeneración remota a la comparación. |
| `--no-regulado` | Trata a las cinco instituciones como usuarios no regulados. |
| `--analisis-ligero` | Factibilidad, robustez y las figuras que no vuelven a resolver el mercado. |
| `--almacen CARPETA` | Guarda la corrida entera en Parquet, para leer o dibujar cualquier hora sin volver a simular. |
| `--out-dir CARPETA` | Carpeta de las salidas, para no pisar las de otra corrida. |
| `--factor-generacion F`, `--factor-demanda F` | Escalan la comunidad (aceptan fracciones, como `1/7`). |
| `--escala-agente NOMBRE:F`, `--neto-cero`, `--excluir-agente NOMBRE`, `--factor-cv F` | Los demás casos de escalado. |
| `--desde`, `--hasta` | Una ventana acotada del horizonte. |
| `--procesos N` | Cuántos procesos abre el mercado. En el servidor, como mucho 16. |

En la máquina de trabajo se corren solo pruebas, compuertas y humos de un
día. Las corridas completas van al servidor por su lanzador.

---

## La matriz de escalado

La comparación se corre sobre trece casos que escalan la misma comunidad, cada
uno una corrida completa:

| Caso | Qué cambia |
|---|---|
| E0 | nada: la comunidad medida |
| E1, E2, E3, E4, E5 | la generación por 3, 4, 5,6, 7 y 10 |
| P1 | la demanda dividida por 7 |
| P2 | la generación y la demanda por 7 |
| K1 | la demanda por 2 |
| I1 | la UCC a consumo anual neto cero |
| N1 | cada institución a consumo anual neto cero |
| CV2 | el componente de comercialización por 2 |
| SINU | la comunidad sin la Universidad de Nariño |

Se corren en un servidor Linux con `modelo_base/run_servidor.sh`:

```bash
export MTE_ROOT=$PWD/MedicionesMTE_v3
bash modelo_base/run_servidor.sh compuertas          # las pruebas y compuertas del motor
bash modelo_base/run_servidor.sh matriz_reposo       # las trece corridas por el reposo, cada una con su compuerta de salida
bash modelo_base/run_servidor.sh barrido_sigma       # las trece con σ = 0, 0,5 y 1
MATRIZ_CANON=SALIDAS_SERVIDOR/matriz_reposo \
  bash modelo_base/run_servidor.sh gsa_directo       # el Sobol directo sobre el reposo (D73 a D79)
MATRIZ_CANON=SALIDAS_SERVIDOR/matriz_reposo \
  bash modelo_base/run_servidor.sh tarifa_extrema    # el CU de la mitad al doble, en los trece casos
MATRIZ_CANON=SALIDAS_SERVIDOR/matriz_reposo \
  bash modelo_base/run_servidor.sh validacion_ampliada   # el reposo frente a la dinámica, hasta 40 horas por régimen
bash modelo_base/run_servidor.sh recoger <accion>    # el tar de vuelta, con su comprobación
```

- `DESDE=<caso>` retoma `matriz_reposo` desde ese caso, y `RETOMA=<k>` retoma
  `validacion_ampliada` desde la integración `k` de su plan.
- Con `SECO=1` delante, cualquier acción imprime las órdenes que correría sin
  ejecutar ni escribir nada.
- Cada registro abre con el commit en uso, el número de ficheros versionados
  con cambios y la orden exacta (C-369).
- Las acciones `matriz`, `sonda79` y `humo_linux` son de la vía acoplada: <!-- vetada-ok: acciones históricas del lanzador -->
  produjeron la matriz del 15 de septiembre, superada, y se conservan para
  comparar.

**El servidor es compartido con una plataforma en producción.** El lanzador se
contiene solo: se vuelve a lanzar encerrado en la mitad alta de los núcleos,
con `nice 19`, `ionice` ociosa y un tope duro de memoria, y recorta a esa mitad
un `PROCS` mayor. Si el usuario no tiene `linger`, se niega a arrancar fuera de
`tmux` o `screen`, porque el tope de memoria moriría al cerrar la sesión. La
validación ampliada se niega a arrancar de día salvo con `DIA_OK=1`. Nada pesado
se lanza en ese servidor fuera del lanzador.

El montaje completo, qué mirar en cada paso y cómo retomar una cadena
detenida están en
[`modelo_base/MONTAJE_SERVIDOR.md`](modelo_base/MONTAJE_SERVIDOR.md).

---

## Las mediciones derivadas

Buena parte de los resultados no vuelve a correr la matriz. Son guiones que
leen los almacenes del canon, comprueban antes su huella contra
`Documentos/canon_2026-09/HUELLAS.csv` y fallan en voz alta. Por eso solo
corren donde está el canon, que no es público.

En [`reformateo/documento/scripts/articulo/`](reformateo/documento/scripts/articulo/):

| Guion | Qué calcula |
|---|---|
| `p2p_comunitario.py`, `p2pcom_exacto.py`, `p2p_colectivo_derivados.py` | El P2P colectivo, la regla propuesta. |
| `hibrido_por_planta.py`, `h2_exacto.py` | El P2P mutualizado (H1) y su segunda etapa. |
| `c2_ppa.py` | El contrato PPA de la propuesta. |
| `atribucion_supuestos.py` | Cuánto de la ventaja del mercado sobre C4 se atribuye a cada supuesto, en los dos órdenes. |
| `corte_fondo_derivados.py`, `prevision_corte.py` | El corte del crédito y el fondo común. |
| `intangibles_autoconsumo.py` | El beneficio intangible y el incentivo a consumir en el sitio (actividad 3.3). |
| `cifras_articulo.py` | La tabla de cifras con huella de la que sale toda cifra del artículo. |
| `gen_figuras_articulo_es.py`, `gen_figuras_articulo.py` | Las figuras del artículo, en español y en inglés. |

En [`reformateo/documento/scripts/`](reformateo/documento/scripts/) están las
demás: la descomposición, el spread, los subperíodos, el retiro de un miembro,
el umbral de 100 (kW), la deserción y el peso de la regla de despacho, entre
otras. En [`gsa_directo/`](gsa_directo/) están el análisis de sensibilidad
global y la tarifa en niveles extremos. En
[`reformateo/documento/scripts/sonda/consenso/`](reformateo/documento/scripts/sonda/consenso/)
está la validación de la forma cerrada con la dinámica.

---

## Cómo reproducir el artículo

El artículo usa 5 de los 13 casos: **E0, E3, E4, I1 y SINU**. Todas sus cifras
salen de una sola tabla con huella, y todas sus figuras de un solo guion:

```bash
# 1. La matriz y los derivados del canon (en el servidor, ver arriba)
# 2. La tabla de cifras del artículo, desde el canon
python -u reformateo/documento/scripts/articulo/cifras_articulo.py
# 3. Las figuras, desde esa tabla
python -u reformateo/documento/scripts/articulo/gen_figuras_articulo_es.py
```

La versión del código que acompaña al envío queda marcada con una etiqueta de
git, `articulo-latam-v1`. Para reproducir el artículo meses después, se parte
de esa etiqueta y no de `main`:

```bash
git checkout articulo-latam-v1
```

Sin las mediciones del MTE, que se piden a los autores, se pueden correr el
caso sintético, las pruebas y las compuertas que no leen el canon.

---

## Pruebas y compuertas

```bash
bash modelo_base/run_servidor.sh compuertas
```

corre las compuertas del motor (la prueba dorada entre ellas), sus ficheros de
pruebas y las dos horas rápidas de la compuerta de la dinámica regularizada, y
se detiene en la primera que falle. Cada prueba también se puede correr sola:

```bash
python -m pytest tests/test_piso_P.py -q
```

**No se corre `pytest tests/` entero.** `tests/test_full_simulation_preflight.py`
contiene una corrida con datos reales que escribe en `outputs/` y `graficas/`.
Se corre solo con su filtro:

```bash
python -m pytest tests/test_full_simulation_preflight.py -q -k "suma or banner or propaga or construye or pasa"
```

**Antes de citar una cifra,** el canon se comprueba con sus verificadores
(`Documentos/canon_2026-09/verificar_canon_2026-09.py`, que debe imprimir
`CANON 2026-09 INTACTO`). `reformateo/documento/scripts/compuerta_vetadas.py`
busca en un manuscrito cifras, rutas y citas de resultados superados (C-221).

---

## Salidas

- **`outputs/`**: los libros de Excel de la comparación y del análisis, el
  desglose del mercado hora a hora y el reporte de avance.
- **`graficas/`**: las figuras, cada una con su tabla `.csv` y su `.mat`
  hermanos para reproducirla en MATLAB.
- **El almacén** (con `--almacen`): en Parquet, las tablas de horas, flujos
  entre pares, agentes y liquidación por escenario, más un `almacen.json`. La
  vía acoplada escribe también las trayectorias de la integración. La del <!-- vetada-ok: la acoplada queda para validar -->
  reposo no integra y no las escribe.

Con `--out-dir`, todo va a esa carpeta en vez de la raíz.

---

## Estructura

```
main_simulation.py     el orquestador: carga, mercado, escenarios, análisis y figuras
core/                  el motor: juego, reposo en forma cerrada, integrador acoplado, liquidación, almacén
scenarios/             C1 a C5 y las columnas heredadas
data/                  cargadores de las mediciones, tarifas, bolsa, escalado y capacidad
analysis/              factibilidad, optimalidad, equidad, sensibilidad
gsa_directo/           el análisis de sensibilidad global y la tarifa en niveles extremos
visualization/         figuras
tests/                 pruebas y compuertas
modelo_base/           el lanzador del servidor y su montaje
reformateo/documento/  el documento de proceso, sus registros y los guiones de cifras y derivados
```

---

## Documentación del proceso

En [`reformateo/documento/`](reformateo/documento/):

| Fichero | Qué contiene |
|---|---|
| `HALLAZGOS.md` | Lo que se encontró, numerado (H-xx), aplicado o no. |
| `CORRECCIONES.md` | Cada corrección del código, de la tesis y del artículo, numerada (C-xxx), con su prueba. |
| `ESCENARIOS.md` | La ficha de cada escenario contra su norma. |
| `MODELO_DEFINITIVO.md` | Qué es el modelo hoy: el reposo, el piso marginal y la rama cuantal. |
| `PARAMETROS.md` | De dónde sale cada parámetro y cómo se defiende. |
| `main.tex` y `sections/` | El documento de proceso. |

---

## Cómo citar

Tesis:

```
B. S. López-Méndez, «Análisis de optimalidad y validación regulatoria de
mercados P2P en Colombia», tesis de maestría, Maestría en Ingeniería
Electrónica, Universidad de Nariño, Pasto, 2026.
```

Código (con la etiqueta de la versión usada):

```
B. S. López-Méndez, Optimalidad-p2p-col, código de la tesis y del artículo,
2026. [En línea]. Disponible: https://github.com/Bura-hub/Optimalidad-p2p-col
```

La cita del artículo se añadirá cuando se publique.
