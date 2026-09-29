# Análisis de optimalidad y validación regulatoria de mercados P2P en Colombia

Tesis de maestría en Ingeniería Electrónica, Universidad de Nariño, 2026.

- **Autor:** Brayan S. Lopez-Mendez
- **Asesores:** M.Sc. Andrés Pantoja y M.Sc. Germán Obando
- **Modelo base:** Chacón et al. (2025), el mercado entre pares por dinámica de replicador

---

## Qué hace este repositorio

Simula un mercado de energía entre pares (P2P) en una comunidad de cinco
instituciones de Pasto con generación solar, y lo compara con los mecanismos
que la regulación colombiana ofrece para el mismo excedente: la autogeneración
individual, el contrato bilateral, la venta en bolsa, la autogeneración
colectiva y la autogeneración remota. Cada mecanismo se liquida como lo
liquida su norma, hora a hora o mes a mes, con las mediciones reales del
proyecto MTE (abril a diciembre de 2025, 6144 horas).

El mercado es el juego de Stackelberg entre vendedores y compradores del
modelo base, con dinámica de replicador y relajación lagrangiana. Con datos
reales, el mercado de cada hora se resuelve en el **reposo de ese juego,
regularizado y calculado en forma cerrada**; la integración de la dinámica
queda para validarlo y dibujar su convergencia.

**Estado (28 de septiembre de 2026).** La corrida canónica es la **matriz de
trece casos del 19 de septiembre**, por la vía del reposo. Sobre ella se
registraron después el análisis de sensibilidad global (GSA directo, D73 a
D79) y las mediciones del 27 y el 28 de septiembre. Todo ello forma el canon
de la tesis, que se comprueba con huellas `sha256` antes de citar cualquier
cifra. Este documento no publica cifras de resultados: salen de ese canon.

**El canon, las mediciones del MTE y el manuscrito no son públicos.** Las
mediciones son datos del proyecto MTE sobre instituciones concretas, y el
canon (`Documentos/canon_2026-09/`, con las entregas del servidor en
`SALIDAS_SERVIDOR/`) y el manuscrito (`Documentos/FinalTesisV2/`) los
contienen institución por institución. Por esa privacidad, `Documentos/`,
`SALIDAS_SERVIDOR/` y `MedicionesMTE_v3/` están en `.gitignore`, y este
repositorio publica solo el código y su documentación de proceso.

---

## El modelo

**El juego es el del modelo base.** Juego de Stackelberg con dinámica de
replicador y relajación lagrangiana, con las dos poblaciones integradas en
una sola ecuación diferencial, como el fichero original. La fidelidad se
comprueba con una prueba dorada contra el caso publicado (7 de 7, por la vía
alternada, que es el defecto de `SolverParams`), con dos apartamientos <!-- vetada-ok: la prueba dorada corre por la alternada -->
declarados: la forma agregada del término de competencia y el peso del
jugador virtual.

**El mercado de cada hora se resuelve en el reposo, no integrando** (D48,
CAL-53, ADR 0060). Con un vendedor y varios compradores, la dinámica oscila
alrededor de un reposo que no alcanza (H-87); con una regularización
entrópica en el replicador del vendedor, de μ = 1 (COP/kWh), sí llega (H-90).
El motor calcula ese reposo directamente (`--metodo reposo`, el defecto con
datos reales):

- **El piso del juego es el del vendedor marginal** (D63), el último que hace
  falta para cubrir la demanda. Los vendedores despachan por su alternativa
  regulada, y una caminata competitiva sobre los pisos decide quién entra y
  cuánta energía se transa; la hora sin ganancia posible queda sin mercado.
- **El nivel del precio es una primitiva declarada**: un presupuesto que suma,
  por comprador, el piso más una fracción σ de su banda, con σ = (I − 1)/I
  por defecto y un barrido de σ (D50).
- **Cada comprador liquida al precio uniforme de la hora** que conserva el
  ingreso del reposo, sin pasar de su techo (D51).
- **En las horas frágiles, la rama cuantal** (D71). Donde la forma cerrada no
  es un reposo estable de la dinámica regularizada, se publica el reposo con
  μ = 1; en las horas reales cambia solo el reparto entre compradores.
  `--mu-cuantal 0` apaga la rama.

**La dinámica solo valida.** La vía **acoplada**, que integra precios y
cantidades juntos (LSODA con tolerancias relativa y absoluta de 1e-6, las del
original, H-51), queda para validar el reposo y dibujar su convergencia. La
validación contra la dinámica regularizada no verificó ningún régimen con el
criterio fijado de antemano, de modo que la forma cerrada es una **regla
declarada** en todos los regímenes, con confirmación puntual en una muestra
de E0 (C-225).

**La banda de precios es aporte de esta tesis.** Donde el modelo base tiene dos
constantes exógenas, aquí hay dos cotas medidas de la regulación:

- **El techo** es el costo unitario de prestación del servicio (CU) de cada
  comprador, mes a mes.
- **El piso** es la alternativa regulada de cada vendedor, según el artículo 25
  de la Resolución CREG 174 y el Anexo 4 de la Resolución CREG 101 072: el
  excedente se reconoce como crédito hasta la importación del mes y, desde la
  hora en que la inyección acumulada la alcanza, se valora a la bolsa de cada
  hora.

Con esas dos cotas, para una planta de hasta 100 (kW) el ancho de la banda es
exactamente el componente de comercialización de la tarifa; entre 100 (kW) y
1 (MW) se le suman los cargos de transmisión, distribución, pérdidas y
restricciones.

**Lo que se añadió para que el modelo funcione con datos reales:**

- una **restricción de participación**, por la que un vendedor se retira si el
  mercado le paga menos que su alternativa. Con el piso del vendedor marginal
  queda como **guarda inerte** (D67): los retiros deben ser cero, y uno solo
  detiene la corrida;
- el **techo por comprador en la liquidación**, para que nadie pague dentro de
  la comunidad más de lo que le costaría la misma energía en la red. Con la
  liquidación uniforme del reposo no llega a actuar; en la vía acoplada se <!-- vetada-ok: la acoplada queda para validar -->
  conserva;
- un **paso de tiempo explícito**.

**Y lo que protege la corrida:**

- **Plazo de 15 minutos por hora** en el lazo paralelo, en cualquier vía (una
  hora por reposo tarda milisegundos).
- **Código de salida 3** si alguna hora terminó con excepción, si la
  participación retiró a algún vendedor o si las horas vencidas por el plazo
  pasan del 1 %, para que una cadena de corridas se detenga.
- En la vía acoplada, además: **parada por estacionario** con horizonte <!-- vetada-ok: la acoplada queda para validar -->
  doble hasta 0,4 dentro de un presupuesto de evaluaciones, **piso de 1e-10
  para la oferta dentro de la dinámica** (H-84) y **corte al primer valor no
  finito**.

---

## Los escenarios regulatorios

| Columna | Qué liquida | Norma |
|---|---|---|
| **P2P** | El mercado entre pares. El excedente que no se coloca recibe el mismo trato que en C1. | |
| **P2P colectivo** | El mismo mercado liquidado por la vía de la autogeneración colectiva, en dos niveles. | CREG 101 072 |
| **C1** | Autogeneración individual: crédito con la importación del mes, corte en la hora en que la inyección acumulada la alcanza y exceso a la bolsa horaria. Se deduce el componente de comercialización hasta 100 (kW) de capacidad (numeral 1), y además transmisión, distribución, pérdidas y restricciones entre 100 (kW) y 1 (MW) (numeral 2). | CREG 174, art. 25; CREG 101 072, Anexo 4; CREG 101 087, art. 1 lit. i |
| **C2** | Contrato bilateral interno entre los miembros, al punto medio de la banda de cada pareja, liquidado hora a hora. Lo que el contrato no firma sigue el art. 25, como el residual del mercado. | Ninguna propia; no es el art. 23 num. 2 lit. a de la CREG 174 (C-217) |
| **C3** | Exposición íntegra a la bolsa de cada hora, descontados los costos del mercado mayorista. Es el contrafáctico declarado. | |
| **C4** | Autogeneración colectiva, liquidada mes a mes, con el exceso valorado a la bolsa de la hora del corte y reparto igual entre los miembros. | CREG 101 072; CREG 101 087, art. 1 lit. ii |
| **C5** | Autogeneración remota: cada hora se despacha por contrato el mínimo entre la inyección y la importación agregadas, al precio de contratos de XM. Queda como referencia del régimen horario, **no elegible** para esta comunidad (C-228). | CREG 101 099, arts. 16 a 21 |

Los libros de resultados llevan además la columna `C4_mensual`, que desde <!-- vetada-ok: se declara como alias -->
C-175 es un alias exacto de C4 y no se cuenta aparte (C-218).

La ficha de cada escenario, con su fórmula, sus precios y los supuestos que no
vienen de la norma, está en [`reformateo/documento/ESCENARIOS.md`](reformateo/documento/ESCENARIOS.md).

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
  raíz, o donde indique la variable de entorno `MTE_ROOT`. Son datos del
  proyecto y no se publican.
- **Serie de precios de contratos de XM.** Va en
  `data/XM_Energía y Precios transados en contratos con destino a Mercado Regulado y No Regulado.xlsx`.
  Es pública, del portal de XM, pero el `.gitignore` excluye los `.xlsx`. Sin
  ella falla toda corrida que incluya C5.
- **Ficheros del modelo base.** La prueba dorada los necesita; sin ellos salta
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

Opciones que conviene conocer (todas en `python main_simulation.py --help`):

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

En la matriz canónica, con 16 procesos en el servidor, cada caso completo tardó
entre 58,6 y 70,1 (s). En la máquina de trabajo se corren solo pruebas,
compuertas y humos de un día; las corridas completas van al servidor por su
lanzador.

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

Se corren en un servidor Linux con `modelo_base/run_servidor.sh`, en este orden:

```bash
export MTE_ROOT=$PWD/MedicionesMTE_v3
bash modelo_base/run_servidor.sh compuertas          # las pruebas y compuertas del motor
bash modelo_base/run_servidor.sh matriz_reposo       # las trece corridas por el reposo, cada una con su compuerta de salida
bash modelo_base/run_servidor.sh barrido_sigma       # las trece con σ = 0, 0,5 y 1
bash modelo_base/run_servidor.sh validacion_reposo   # el reposo frente a la dinámica regularizada (M-A a M-G)
MATRIZ_CANON=SALIDAS_SERVIDOR/matriz_reposo \
  bash modelo_base/run_servidor.sh gsa_directo       # el Sobol directo sobre el reposo (D73 a D79)
bash modelo_base/run_servidor.sh recoger matriz_reposo   # el tar de vuelta, con su comprobación
```

`DESDE=<caso>` retoma `matriz_reposo` desde ese caso. Con `SECO=1` delante,
cualquier acción imprime las órdenes que correría sin ejecutar ni escribir
nada. Las acciones `matriz`, `sonda79` y `humo_linux` son de la vía acoplada: <!-- vetada-ok: acciones históricas del lanzador -->
produjeron la matriz del 15 de septiembre, superada, y se conservan para
comparar.

**El servidor es compartido con una plataforma en producción.** El lanzador se
contiene solo: se vuelve a lanzar encerrado en la mitad alta de los núcleos,
con `nice 19`, `ionice` ociosa y un tope duro de memoria, y recorta a esa mitad
un `PROCS` mayor. Nada pesado se lanza en ese servidor fuera del lanzador.

El montaje completo, qué mirar en cada paso y cómo retomar una cadena
detenida están en
[`modelo_base/MONTAJE_SERVIDOR.md`](modelo_base/MONTAJE_SERVIDOR.md).

De las mediciones del 27 y el 28 de septiembre, solo el barrido de σ corrió
en el servidor (`barrido_sigma`). Las demás no vuelven a correr la matriz:
son guiones de `reformateo/documento/scripts/` que leen los almacenes del
canon o llaman al evaluador del GSA, y se corrieron en local.

---

## Pruebas y compuertas

```bash
bash modelo_base/run_servidor.sh compuertas
```

corre las dieciocho compuertas (la prueba dorada entre ellas), los veintiséis
ficheros de pruebas del motor y las dos horas rápidas de la compuerta de la
dinámica regularizada, y se detiene en la primera que falle. Cada prueba
también se puede correr sola:

```bash
python -m pytest tests/test_piso_P.py -q
```

**No conviene correr `pytest tests/` entero.** `tests/test_full_simulation_preflight.py`
contiene una corrida con datos reales que escribe en `outputs/` y `graficas/`;
se corre solo con su filtro:

```bash
python -m pytest tests/test_full_simulation_preflight.py -q -k "suma or banner or propaga or construye or pasa"
```

---

## Las cifras y las figuras de la tesis

Toda cifra de la tesis que el canon no escribe tal cual sale de un guion de
[`reformateo/documento/scripts/`](reformateo/documento/scripts/). Ninguno
simula: leen artefactos del canon, comprueban antes su huella contra
`Documentos/canon_2026-09/HUELLAS.csv` y fallan en voz alta. Por eso solo
corren donde está el canon, que no es público.

| Guion | Qué hace |
|---|---|
| `cifras_datos_cap04.py` | Las cifras descriptivas del dato del capítulo 4, desde el cargador y el almacén de E0 (C-229). |
| `cifras_cap07.py` | Las cifras derivadas del capítulo 7, la comparación de desempeño (C-230). |
| `cifras_cap08.py` | Las cifras derivadas del capítulo 8, la sensibilidad y la robustez, desde el GSA (C-231). |
| `gen_tesis_figuras.py` | Las figuras de los capítulos 4 a 6, cada una con su `.csv`, su `.mat` y su `.fuente.txt`. |
| `compuerta_vetadas.py` | Busca en un Markdown cifras, rutas y citas de canon superados; sale con 1 si encuentra alguna (C-221). |
| `compila_tesis.ps1` | Compila el manuscrito a PDF o a Word con pandoc (C-222). |

```bash
PYTHONUNBUFFERED=1 python -u reformateo/documento/scripts/cifras_cap07.py
python reformateo/documento/scripts/compuerta_vetadas.py [fichero.md ...]
powershell -File reformateo/documento/scripts/compila_tesis.ps1           # PDF
powershell -File reformateo/documento/scripts/compila_tesis.ps1 -Word     # .docx
```

---

## Salidas

- **`outputs/`**: los libros de Excel de la comparación y del análisis, el
  desglose del mercado hora a hora y el reporte de avance.
- **`graficas/`**: las figuras, cada una con su tabla `.csv` y su `.mat`
  hermanos para reproducirla en MATLAB.
- **El almacén** (con `--almacen`): en Parquet, las tablas de horas, flujos
  entre pares, agentes y liquidación por escenario, más un `almacen.json`. La
  vía acoplada escribe además las trayectorias de la integración; la del <!-- vetada-ok: la acoplada queda para validar -->
  reposo no integra y no las escribe.

Con `--out-dir`, todo va a esa carpeta en vez de la raíz.

---

## Estructura

```
main_simulation.py     el orquestador: carga, mercado, escenarios, análisis y figuras
core/                  el motor: juego, reposo en forma cerrada, integrador acoplado, liquidación, almacén
scenarios/             C1 a C5 y el mercado por la vía del colectivo
data/                  cargadores de las mediciones, tarifas, bolsa, escalado y capacidad
analysis/              factibilidad, optimalidad, equidad, sensibilidad
visualization/         figuras
tests/                 pruebas y compuertas
modelo_base/           el lanzador del servidor y su montaje
reformateo/documento/  el documento de proceso, sus registros y los guiones de cifras
```

---

## Documentación del proceso

En [`reformateo/documento/`](reformateo/documento/):

| Fichero | Qué contiene |
|---|---|
| `HALLAZGOS.md` | Lo que se encontró, numerado (H-xx), aplicado o no. |
| `CORRECCIONES.md` | Cada corrección del código, numerada (C-xxx), con su prueba. |
| `ESCENARIOS.md` | La ficha de cada escenario contra su norma. |
| `MODELO_DEFINITIVO.md` | Qué es el modelo hoy: la configuración al 2026-09-19 (el reposo, el piso marginal y la rama cuantal), con las precisiones fechadas del 27 y el 28 de septiembre. |
| `PARAMETROS.md` | De dónde sale cada parámetro y cómo se defiende. |
| `main.tex` y `sections/` | El documento de proceso. |
