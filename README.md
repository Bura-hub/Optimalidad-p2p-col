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

El mercado es un juego de Stackelberg entre vendedores y compradores, resuelto
por dinámica de replicador con relajación lagrangiana, e integrado como un solo
sistema de ecuaciones diferenciales, igual que el modelo base.

**Estado (septiembre de 2026).** La revisión regulatoria de septiembre cambió la
forma de liquidar el crédito de energía (el cupo es la importación del mes
completo, C-175), de modo que las cifras publicadas antes dejaron de valer. La
corrida oficial nueva, una matriz de trece casos de escalado, está en curso.
Este documento no publica cifras de resultados hasta que el canon nuevo quede
verificado.

---

## El modelo

**El motor es el del modelo base.** Juego de Stackelberg con dinámica de
replicador y relajación lagrangiana, por la **vía acoplada**, es decir
integrando precios y cantidades juntos, como el fichero original. Integrador
LSODA con tolerancias relativa y absoluta de 1e-6, las del original. La
fidelidad se comprueba con una prueba dorada contra el caso publicado.

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
  mercado le paga menos que su alternativa;
- el **techo por comprador en la liquidación**, para que nadie pague dentro de
  la comunidad más de lo que le costaría la misma energía en la red;
- un **paso de tiempo explícito**.

**Y lo que se añadió para que la integración sea robusta:**

- **Parada por estacionario.** Si el precio no se ha asentado en el horizonte
  de producción (0,05), la hora se vuelve a resolver con el horizonte doble,
  hasta 0,4, dentro de un presupuesto de evaluaciones del integrador.
- **Piso de 1e-10 para la oferta dentro de la dinámica.** La ecuación de
  replicador solo conserva la oferta no negativa en aritmética exacta; sin el
  piso, una hora con un comprador de déficit muy pequeño podía explotar según
  el último decimal (H-84).
- **Corte al primer valor no finito.** La hora queda sin mercado, con su
  motivo, en vez de ocupar un proceso hasta el plazo.
- **Plazo de 15 minutos por hora** en el lazo paralelo.
- **Código de salida 3** si hubo alguna excepción o si las horas perdidas pasan
  del 1 % de las horas de mercado, para que una cadena de corridas se detenga.

---

## Los escenarios regulatorios

| Columna | Qué liquida | Norma |
|---|---|---|
| **P2P** | El mercado entre pares. El excedente que no se coloca recibe el mismo trato que en C1. | |
| **P2P colectivo** | El mismo mercado liquidado por la vía de la autogeneración colectiva, en dos niveles. | CREG 101 072 |
| **C1** | Autogeneración individual: crédito con la importación del mes, corte en la hora en que la inyección acumulada la alcanza y exceso a la bolsa horaria. Se deduce el componente de comercialización hasta 100 (kW) de capacidad (numeral 1), y además transmisión, distribución, pérdidas y restricciones entre 100 (kW) y 1 (MW) (numeral 2). | CREG 174, art. 25; CREG 101 072, Anexo 4 |
| **C2** | Contrato bilateral interno a precio pactado, liquidado hora a hora. | CREG 174, art. 23 num. 2 lit. a; art. 26 lit. c |
| **C3** | Exposición íntegra a la bolsa de cada hora, descontados los costos del mercado mayorista. Es el contrafáctico declarado. | |
| **C4** | Autogeneración colectiva, liquidada mes a mes, con el exceso valorado a la bolsa de la hora del corte y reparto igual entre los miembros. | CREG 101 072 |
| **C5** | Autogeneración remota: cada hora se despacha por contrato el mínimo entre la inyección y la importación agregadas, al precio de contratos de XM. | CREG 101 099, arts. 16 a 21 |

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

# Un día con datos reales
python main_simulation.py --day 2025-07-15 --metodo acoplado

# Un caso completo, con la configuración de la corrida oficial
python -u main_simulation.py --data real --full --include-c5 --no-regulado \
    --metodo acoplado --analisis-ligero --plazo-hora 15 \
    --horizonte-max-acoplado 0.4 \
    --almacen SALIDAS_SERVIDOR/matriz/E0/almacen --out-dir SALIDAS_SERVIDOR/matriz/E0
```

Opciones que conviene conocer (todas en `python main_simulation.py --help`):

| Opción | Qué hace |
|---|---|
| `--metodo acoplado` | La vía del modelo base. La alternada solo queda para comparar. |
| `--include-c5` | Añade la autogeneración remota a la comparación. |
| `--no-regulado` | Trata a las cinco instituciones como usuarios no regulados. |
| `--analisis-ligero` | Factibilidad, robustez y las figuras que no vuelven a resolver el mercado. |
| `--almacen CARPETA` | Guarda la corrida entera, trayectorias incluidas, para dibujar cualquier hora sin volver a simular. |
| `--out-dir CARPETA` | Carpeta de las salidas, para no pisar las de otra corrida. |
| `--factor-generacion F`, `--factor-demanda F` | Escalan la comunidad (aceptan fracciones, como `1/7`). |
| `--escala-agente NOMBRE:F`, `--neto-cero`, `--excluir-agente NOMBRE`, `--factor-cv F` | Los demás casos de escalado. |
| `--desde`, `--hasta` | Una ventana acotada del horizonte. |
| `--procesos N` | Cuántos procesos abre el mercado. |

La corrida completa de un caso tarda del orden de 20 minutos a 3 horas con 31
procesos, según cuántas horas tienen mercado y cuán pesadas son.

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
bash modelo_base/run_servidor.sh compuertas   # las pruebas y compuertas del motor
bash modelo_base/run_servidor.sh humo_linux   # un humo corto en Linux
bash modelo_base/run_servidor.sh sonda79      # decide las palancas del integrador
bash modelo_base/run_servidor.sh matriz       # las trece corridas y la recogida
```

Con `SECO=1` delante, cualquier acción imprime las órdenes que correría sin
ejecutar ni escribir nada. El montaje completo, qué mirar en cada paso y cómo
retomar una cadena detenida están en
[`modelo_base/MONTAJE_SERVIDOR.md`](modelo_base/MONTAJE_SERVIDOR.md).

---

## Pruebas y compuertas

```bash
bash modelo_base/run_servidor.sh compuertas
```

corre las dieciocho compuertas y las diecisiete pruebas del motor, y se detiene
en la primera que falle. Cada prueba también se puede correr sola:

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

## Salidas

- **`outputs/`**: los libros de Excel de la comparación y del análisis, el
  desglose del mercado hora a hora y el reporte de avance.
- **`graficas/`**: las figuras, cada una con su tabla `.csv` y su `.mat`
  hermanos para reproducirla en MATLAB.
- **El almacén** (con `--almacen`): en parquet, las tablas de horas, flujos
  entre pares, trayectorias de la integración y liquidación por escenario.

Con `--out-dir`, todo va a esa carpeta en vez de la raíz.

---

## Estructura

```
main_simulation.py     el orquestador: carga, mercado, escenarios, análisis y figuras
core/                  el motor: juego, integrador acoplado, liquidación, almacén
scenarios/             C1 a C5 y el mercado por la vía del colectivo
data/                  cargadores de las mediciones, tarifas, bolsa, escalado y capacidad
analysis/              factibilidad, optimalidad, equidad, sensibilidad
visualization/         figuras
tests/                 pruebas y compuertas
modelo_base/           el lanzador del servidor y su montaje
reformateo/documento/  el documento de proceso y sus registros
```

---

## Documentación del proceso

En [`reformateo/documento/`](reformateo/documento/):

| Fichero | Qué contiene |
|---|---|
| `HALLAZGOS.md` | Lo que se encontró, numerado (H-xx), aplicado o no. |
| `CORRECCIONES.md` | Cada corrección del código, numerada (C-xxx), con su prueba. |
| `ESCENARIOS.md` | La ficha de cada escenario contra su norma. |
| `MODELO_DEFINITIVO.md` | La configuración del modelo al 2026-09-08; las correcciones posteriores están en `CORRECCIONES.md`. |
| `PARAMETROS.md` | De dónde sale cada parámetro y cómo se defiende. |
| `main.tex` y `sections/` | El documento de proceso. |
