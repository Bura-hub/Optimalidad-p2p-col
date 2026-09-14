# Mediciones del modelo base — montaje en el servidor

Léelo entero antes de empezar: son cuatro pasos y el orden importa.

**Contexto en una frase.** Hay que decidir qué fuente del modelo base se
traduce, porque el modelo publicado y el modelo programado **no son el mismo
modelo**, y la medición que lo decide es cara: cada hora de mercado cuesta
unos 47 segundos por la vía acoplada. El detalle está en `HALLAZGOS.md`,
hallazgos H-39 a H-42, y la decisión en `docs/adr/0049-…`.

---

## Qué se mide, y qué decide cada cosa

| Acción | Cuesta | Qué decide |
|---|---|---|
| `compuertas` | segundos | Que el código llegó entero. Si falla algo, para. |
| `caso` | ~5 min | Cuántas de las doce afirmaciones del artículo reproduce cada una de las tres formas. **No necesita los datos del MTE.** |
| `eficiencia` | ~1 h por frontera | Cuánto del ahorro alcanzable captura el mercado, con muestra grande |
| `competencia` | ~2 h por frontera | **La que decide.** Si la forma publicada deja los precios pegados a las cotas con datos reales |

La cuestión que `competencia` resuelve es esta: la forma publicada es la
única que reproduce el caso del artículo, pero allí sus precios cayeron
pegados a las cotas, que es justo el defecto que la vía acoplada venía a
corregir. Si con datos reales pasa lo mismo, no sirve, y estaríamos
cambiando un defecto por otro.

---

## Qué necesita, y de dónde sale cada cosa

| Pieza | Tamaño | De dónde |
|---|---|---|
| Código del proyecto | ~15 MB | **GitHub**, rama `feature/cal43-depuracion-fase-a` |
| `MedicionesMTE_v3/` | 1,7 GB · 73 CSV | **Copiar a mano** (nunca se commitea, por diseño). Va en la raíz y con ese nombre: es lo que los cargadores buscan por defecto |
| `Documentos/copy/` | 208 KB · 17 ficheros | **Copiar a mano**. Solo lo necesitan dos compuertas, no las mediciones |
| `data/ASC_pdfs/` | 1,8 MB | **Opcional**, y solo si se van a reextraer tarifas. El CSV derivado sí viene del repositorio |

`Documentos/` está gitignorado por la política del repositorio público, de
modo que no llega con el clon. Sin él, la prueba dorada **salta sus siete
comprobaciones** y la compuerta del bienestar del comprador no puede
verificar nada. Ninguna de las dos cosas impide medir, pero conviene copiarlo
para que las compuertas sirvan de algo:

```bash
rsync -av Documentos/copy/ servidor:/home/…/sistemabl/Documentos/copy/
```

La acción `caso` no necesita nada de eso: el caso publicado trae sus propios
datos, en las tablas del artículo. Si solo quieres la respuesta rápida,
corre esa.

---

## Paso 1 — Clonar y montar el entorno

```bash
cd /home/brayan_lopez
git clone https://github.com/Bura-hub/Optimalidad-p2p-col.git sistemabl
cd sistemabl
git checkout feature/cal43-depuracion-fase-a
git log --oneline -1

bash modelo_base/run_servidor.sh entorno
```

El lanzador detecta `.venv/bin/python` por su cuenta; no hace falta
activarlo.

## Paso 2 — Copiar las mediciones

**El nombre de la carpeta importa.** Tanto el orquestador como las sondas
buscan por defecto `MedicionesMTE_v3` en la raíz del repositorio, no
`MedicionesMTE`. Con ese nombre no hace falta exportar nada; con cualquier
otro, la variable de entorno es obligatoria y olvidarla produce un fallo de
carga que no dice cuál es la causa.

Desde tu máquina:

```bash
rsync -av --progress MedicionesMTE_v3/       servidor:/home/brayan_lopez/sistemabl/MedicionesMTE_v3/
```

En el servidor, exportar la variable de todas formas, porque la corrida
canónica la exige explícitamente y para si falta:

```bash
export MTE_ROOT=/home/brayan_lopez/sistemabl/MedicionesMTE_v3
```

Conviene dejarla en el perfil, para que sobreviva a una sesión nueva:

```bash
echo 'export MTE_ROOT=/home/brayan_lopez/sistemabl/MedicionesMTE_v3' >> ~/.bashrc
```

## Paso 3 — Medir

```bash
bash modelo_base/run_servidor.sh compuertas     # primero, siempre
bash modelo_base/run_servidor.sh caso           # barato, y ya responde bastante
bash modelo_base/run_servidor.sh todo 60        # lo demás, ~6 h
```

Cada sonda escribe su log fechado en `modelo_base/logs/` y su tabla en
`reformateo/documento/scripts/sonda/salidas/`. Las tablas se guardan **hora a
hora**, de modo que si algo se corta no se pierde lo hecho.

**Aviso sobre el costo.** La vía acoplada no tiene cota de tiempo por hora:
sobre el caso base hay una hora que no termina en 420 segundos mientras otra
igual resuelve en 47. Si un log lleva más de quince minutos sin línea nueva,
no es un cuelgue del sistema, es esa patología. Anótalo y sigue.

Con `nohup` para que sobreviva a la sesión:

```bash
nohup bash modelo_base/run_servidor.sh todo 60 > modelo_base/logs/todo.log 2>&1 &
tail -f modelo_base/logs/todo.log
```

## Paso 4 — Traer los resultados

```bash
bash modelo_base/run_servidor.sh recoger
```

Deja un `modelo_base/resultados_<fecha>.tar.gz` con las tablas y los logs.
Tráelo y descomprímelo en la raíz del repositorio, en tu máquina.

---

## Qué mirar al recibirlos

1. **`caso_*.log`** — cuántas de las doce afirmaciones reproduce cada forma.
   Medido en local: agregada 8, publicada 11. Si el servidor da otra cosa,
   eso es un hallazgo.
2. **`competencia_*.csv`** — las columnas `pegados` y `pos_media`. Si la
   forma publicada pega los precios a las cotas mucho más que la agregada,
   **no se adopta** y hay que buscar otra salida.
3. **`eficiencia_*.csv`** — la columna `efvol_aco` debe salir 100 % en todas
   las horas, las dos formas. Si no, es un hallazgo.

---

## La corrida oficial — 9 de septiembre

Es la que produce las cifras publicables y, sobre todo, **el almacén del que
sale cualquier figura de cualquier hora sin volver a simular**. Sustituye a la
acción canónica: hace lo mismo y cuatro cosas más.

### Antes de nada, traer el código nuevo

El repositorio ya está clonado de la tanda anterior, de modo que solo hay que
avanzar la rama:

```bash
cd /home/brayan_lopez/sistemabl
git fetch origin
git checkout feature/cal43-depuracion-fase-a
git pull --ff-only origin feature/cal43-depuracion-fase-a
git log --oneline -1        # debe decir C-169
```

**Con avance rápido a propósito.** Si el tirón falla porque la rama del
servidor tiene algo encima, no se fuerza: se mira qué es. Un `pull` que
fusiona en silencio es la forma más cómoda de correr un código que no es el
que se revisó.

Y comprobar que la variable de las mediciones sigue puesta, porque la corrida
se detiene si falta:

```bash
echo "$MTE_ROOT"
ls "$MTE_ROOT" | head -3
```

### La corrida

```bash
bash modelo_base/run_servidor.sh oficial
```

Una sola orden. Encadena en este orden y **para en el primer fallo**:

| | Qué hace | Cuánto |
|---|---|---|
| 1 | las diecisiete compuertas | ~2 min |
| 2 | la corrida acoplada de las dos fronteras, con el almacén | ~89 min |
| 3 | la liquidación por institución y la equidad por mes, hora del día y día de la semana | ~2 min |
| 4 | las figuras del foro, los cuatro grupos | ~10 min |
| 5 | la recogida en un solo fichero comprimido | ~1 min |

Conviene lanzarla dentro de una sesión que sobreviva a la desconexión, porque
son cerca de dos horas:

```bash
tmux new -s oficial
bash modelo_base/run_servidor.sh oficial 2>&1 | tee modelo_base/logs/oficial.txt
```

y se sale con `Ctrl-b d`; se vuelve con `tmux attach -t oficial`.

### Qué mirar en los primeros treinta segundos

Al arrancar imprime la máquina que va a usar. **Son cuatro cifras y hay que
mirarlas**, porque son las que contestan si se está usando todo el servidor:

```
=== CORRIDA OFICIAL ===
    nucleos que la maquina declara : 32
    nucleos UTILES (afinidad)      : 32
    procesos del mercado           : 32
    hilos de algebra por proceso   : 1
```

Si la segunda fila fuera menor que la primera, la afinidad está restringiendo
la máquina y el mercado se ajusta solo, avisando. Y si se quiere dejar holgura
para entrar por consola mientras corre:

```bash
PROCS_PEDIDO=1 PROCS=30 bash modelo_base/run_servidor.sh oficial
```

Después, las compuertas. **Si alguna falla, para ahí**: la corrida se detiene
sola y ninguna cifra posterior vale.

### Qué mirar al terminar

Tres cosas, en este orden:

**Una, que la recogida no avisó de nada.** Si dice que falta el almacén o las
figuras, algo se cayó por el camino sin detener la corrida. Ese aviso importa
más de lo que parece: un almacén ausente no se notaría hasta intentar dibujar
una figura de vuelta acá, y para entonces la máquina que lo produjo ya no tiene
el dato.

**Dos, las dos compuertas del canon**, que imprimen su «intacto».

**Tres, el ordenamiento de la tabla regulatoria**, y con una advertencia: **ya
no gana el mismo mecanismo para todas las instituciones**. Al vendedor grande
le conviene el mercado y al comprador puro puede convenirle el colectivo. Eso
es un resultado, no un fallo.

### Traerlo de vuelta

La acción deja el fichero comprimido y dice su nombre. Desde tu máquina:

```bash
scp servidor:/home/brayan_lopez/sistemabl/modelo_base/resultados_*.tar.gz .
tar xzf resultados_*.tar.gz
```

Se descomprime en la raíz del repositorio. Dentro viene, además de lo de
siempre, la carpeta del almacén y la de las figuras del foro.

### Lo que esta corrida deja abierto

**H-65.** Si en más horas la integración termina antes de que el precio se
asiente, la cifra publicada sería un punto del transitorio y no el equilibrio.
En la hora medida la diferencia fue del 22 %. Esta misma corrida da con qué
medirlo a escala, y la decisión sobre la constante del filtro va como consulta
al asesor, junto con las de H-53 y H-63.

---

## La tanda del 7 de septiembre

Se añaden tres mediciones y la corrida canónica. Las tres primeras son
independientes entre sí y de lo anterior, de modo que se pueden lanzar en
cualquier orden.

| Acción | Cuesta | Qué decide |
|---|---|---|
| `techo 200` | ~2 h | **H-45.** Si el límite superior del precio va por comprador o es uno solo |
| `escenario 200` | ~3 h | **H-47.** Qué pasaría si las cinco compraran al mismo comercializador |
| `pesovirtual 200` | ~2 h | **H-46.** Si adoptar la forma del fichero original cambia algún resultado |
| `canonica` | ~2 h por frontera | La corrida entera, que ya acumula cuatro motivos |

```bash
bash modelo_base/run_servidor.sh compuertas
nohup bash modelo_base/run_servidor.sh tanda 200       > modelo_base/logs/tanda.log 2>&1 &
tail -f modelo_base/logs/tanda.log
```

Las tres escriben en `reformateo/documento/validacion_horaria/`, no en la
carpeta de salidas de las sondas anteriores. El recogedor ya se lleva las
dos.

### Qué mirar en cada una

**`techo_n200`.** La columna de horas con comprador sin ahorro. Con el
régimen que entró el 7 de septiembre tiene que salir **cero en todas las
horas**; medido sobre 60 horas por frontera daba 88 y 2 antes del arreglo.
Si aparece alguna, es un hallazgo. El excedente puede subir o bajar según la
hora, y eso está previsto: el criterio no es el excedente.

**`escenario_n200`.** Dos columnas, y **ordenan al revés**. El escenario de
mayor excedente de mercado es el de peor factura, porque el ancho de la
banda es el cargo de comercializar y el mercado solo lo recupera sobre el
lado corto. Lo que se comprueba es que el orden por factura sea el mismo que
en local, es decir todas con ASC mejor que el reparto real y este mejor que
todas con Cedenar. Mirar también la columna de vendedores retirados: el
escenario real retira más del doble que los uniformes, y por eso mueve menos
energía.

**`pesovirtual_n200`.** Lo que decide es si el volumen y el excedente se
mueven. Si no se mueven, la elección es de fidelidad al modelo base y no de
resultado, y entonces conviene adoptar la forma del original. Medido en la
compuerta sintética: el volumen no se mueve, con una diferencia de
1,1·10⁻¹³ (kWh), y los precios suben unos 23 (COP/kWh), es decir que el
efecto es de reparto entre vendedor y comprador.

### La corrida canónica

```bash
export MTE_ROOT=/ruta/a/MedicionesMTE
bash modelo_base/run_servidor.sh canonica
```

**Va por la vía alternada a propósito.** La acoplada cuesta unos 47 segundos
por hora de mercado, y el horizonte son 6144 horas por frontera (así lo
imprimen el humo de E0 del 2026-09-13, `outputs/run_2026-09-13_humo_e0.log`,
y la corrida canónica de junio, `T=6144h`): ni con
dieciséis núcleos es viable. El servidor permite muestras grandes, no el
horizonte por la vía acoplada.

Acumula cuatro motivos que la obligan, y cada uno invalida el canon por su
cuenta: la generación de Udenar reconstruida, el guardia físico de atípicos,
la banda de precios medida y el techo por comprador. Deja sus salidas en
`SALIDAS_SERVIDOR/canonica_m1/` y `.../canonica_m3/`.

Al recibirla, correr las dos compuertas del canon **antes de citar ninguna
cifra**. Van a fallar, y eso es lo esperado, porque el canon cambia; lo que
hay que mirar es qué cambia y si el cambio se explica por los cuatro
motivos.

---

## La tanda del 8 de septiembre — la decisión del piso

Es la que motiva este paquete. **Una sola orden la corre entera:**

```bash
bash modelo_base/run_servidor.sh decision 200
```

Encadena las compuertas, la sonda barata del tramo y la medición de los
cuatro regímenes con su tabla emparejada. Con doscientas horas por frontera
son 1.600 tareas.

### La pregunta

El piso de cada vendedor depende de en qué tramo de la Resolución CREG 174
está: permuta mientras su inyección acumulada del mes no supere su retiro, y
bolsa a partir de ahí. **El modelo cuenta ese tramo sobre el excedente
completo**, es decir como si todo cruzara la frontera comercial. El artículo
23 de la Resolución CREG 101 072 lo cuenta sobre los excedentes *asignables*
a cada usuario tras el reparto, y la energía que un vendedor coloca dentro de
la comunidad no se la entregó al comercializador.

Las dos lecturas son defendibles y la ambigüedad va al asesor. Lo que esta
medición aporta es **el precio de cada una**.

### Los cuatro regímenes

| Régimen | Qué es |
|---|---|
| **tramo** | la alternativa real según la CREG 174. Es lo que el modelo hace hoy |
| **permuta** | todos con el piso de permuta. Contrafactual, para medir |
| **bolsa** | todos con el piso de bolsa. Contrafactual, para medir |
| **residual** | el tramo contado sobre lo que de verdad cruza la frontera. Es la lectura del artículo 23, y **la única de las tres alternativas que corresponde a algo que la comunidad podría de verdad hacer** |

### Cómo se lee la tabla, y esto importa más que la tabla

**La factura manda.** Está en pesos y contiene lo que la red paga por el
excedente exportado, que es lo único que el régimen cambia. Se compara **en
pesos, nunca en porcentaje por hora**: en la frontera secundaria la base ronda
el cero y cambia de signo, y el cociente da valores como −231,60 % sin
contenido.

**La equidad es la métrica del autor del modelo.** El índice de Chacón es la
diferencia entre el ahorro de los compradores y el ingreso de los vendedores,
sobre su suma. Cerca de cero es equitativo, hacia −1 favorece al vendedor y
hacia +1 al comprador. Su Tabla VII da −0,8913 para el método centralizado, con
un 94,56 % para el vendedor, y ese es el argumento de su artículo. **Se mueve
con el piso**, porque el ingreso del vendedor se mide contra su piso.

**El bienestar no arbitra.** Los términos de pago del vendedor y del comprador
se cancelan al sumar los dos lados, de modo que lo único que le queda del
precio es la penalización de competencia, negativa y proporcional al precio.
Prefiere el piso más bajo **por construcción**. Se informa porque es la función
del modelo base, no porque decida. La compuerta lo comprueba.

**El excedente engaña.** Crece cuando la alternativa empeora, no cuando la
comunidad mejora.

### Lo que la medición local de 40 horas ya insinúa

Para que el servidor confirme o desmienta, no para darlo por hecho:

- en la frontera principal gana el **tramo**, es decir lo que el modelo ya
  hace, y la lectura residual sería la peor de las tres;
- en la secundaria gana la **permuta** con mucha diferencia;
- y en la secundaria, pasar de un tramo a otro mueve unas **tres veces y media**
  más dinero que la existencia misma del mercado entre pares.

### El plazo por tarea, que es nuevo

La vía acoplada no tiene cota por hora: unas pocas horas no resuelven nunca.
Antes el plazo era **total**, de modo que tres horas atascadas costaron media
hora con siete de diez procesos ociosos. Ahora corta cuando pasan seis minutos
**sin que termine ninguna tarea**, que es lo que distingue «va lento» de «está
atascado». Se ajusta con el tercer argumento:

```bash
bash modelo_base/run_servidor.sh piso 200 8      # ocho minutos por tarea
```

Una hora que no resuelve **es un dato**, queda anotada como no resuelta y la
medición sigue.

---

## El subproyecto 2 (2026-09-14): humo, sonda y matriz

Contexto en una frase: la corrida oficial de septiembre (`oficial`) se deja tal
cual; para el subproyecto 2 (Anexo 4 de la CREG 101 072, escalado, H-79) la
reemplaza `matriz`, que agrega las palancas del acoplado (D35, D26) y las
trece corridas de la matriz de escalado (D18) en vez de las dos fronteras
M1/M3 (M3 está retirada, D10). El orden es fijo y no se salta ningún paso:

```bash
bash modelo_base/run_servidor.sh compuertas
bash modelo_base/run_servidor.sh humo_linux
bash modelo_base/run_servidor.sh sonda79
bash modelo_base/run_servidor.sh matriz
```

**Antes de correr nada de verdad**, la comprobación en seco imprime cada
orden completa sin ejecutar ninguna, en cualquier máquina (no hace falta
Linux ni los datos del MTE):

```bash
SECO=1 bash modelo_base/run_servidor.sh matriz
```

### 1 · `compuertas`

Ahora corre además el motor nuevo: dieciséis pruebas de pytest (Anexo 4,
umbrales del escalado, P2P residual del artículo 25, C4 mensual, P2P
colectivo, C5 de la Resolución 101 099, suma mensual, coincidencia, costos de
C3, plazo por hora, análisis ligero, cumplimiento de FA-3, el numeral 2 del
análisis, las dos palancas del acoplado, el oráculo del Anexo 4 con los
factores uno y siete, y el presupuesto de la parada por estacionario con el
código de salida, D36 a D38), y la compuerta C-165 con 48 horas en vez
de las 72 de su defecto: con 72, la hora rígida del caso sintético vence el
plazo por hora (H-81).

**Qué mirar.** Que todo pase. Si algo falla, PARA: ni el humo ni la sonda ni
la matriz valen nada corridos sobre un motor que no pasa sus propias
compuertas.

### 2 · `humo_linux`

Se corre **una vez**, en el servidor (porque es Linux), antes de E5 y antes
de `matriz`. Cuatro pasos:

1. `test_plazo_por_hora` bajo el arranque de Linux. `core/ems_p2p.py` abre el
   pool con `multiprocessing.get_context()` sin argumento, es decir con el
   método de la plataforma; en Linux ya es `fork`, y es el único que nunca se
   ha probado (el arreglo del hilo del pool viejo, tarea 18). No hace falta
   forzar ninguna variable de entorno: basta con correr esto en el servidor.
2. La compuerta C-165 con sus 72 horas de defecto (no las 48 de
   `compuertas`), a propósito: ejerce un vencimiento real del plazo por hora
   y la renovación del pool, la hora 56 del caso sintético (H-81). Su
   resumen `[D24]` debe verse en el registro de esta corrida.
3. Un día de E5 (factor de generación 10) con datos reales
   (`--desde 2025-07-15 --hasta 2025-07-16`), modo ligero y plazo por hora,
   en `SALIDAS_SERVIDOR/humo_linux_e5`.
4. El mismo día de E5 con las dos palancas del acoplado encendidas
   (`--rtol-acoplado 1e-7 --horizonte-max-acoplado 0.4`), en
   `SALIDAS_SERVIDOR/humo_linux_e5_palancas`. Existe para ver en su registro,
   antes de las trece corridas, las líneas `[D24]` (plazo por hora), `[D26]`
   (horas por horizonte usado y por motivo de parada: estacionario, tope,
   presupuesto o vuelta fallida) y `[D38]` (el código de salida).

**Qué mirar.** Que las cuatro pasen. El paso 4 puede salir con código 3
(D38): se imprime, pero no detiene el humo, y su línea `[D38]` dice por qué.
**Tiempo esperado:** el humo de un día a
×7 con `--analysis` completo tardó 29 minutos en local; con el modo ligero
(`--analisis-ligero`, D27) es bastante menos, porque solo corre FA-1 a FA-4
y las figuras 14 y 20.

### 3 · `sonda79`

D25: la sonda de H-79
(`reformateo/documento/scripts/sonda/reparto_vs_integrador.py`) mide si el
reparto o el excedente dependen del integrador acoplado, en dos casos de la
matriz de escalado: E0 (factor de generación 1) y E4 (factor 7), 20 horas
cada uno. Dos variantes candidatas: apretar solo la tolerancia relativa (a
1e-7) o doblar el horizonte del acoplado.

Escribe un veredicto en JSON por caso, en `SALIDAS_SERVIDOR/sonda79/`:

```json
{"reparto_depende": false, "excedente_cambia": false, "palanca": []}
```

`palanca` es la lista de variantes que superó alguno de los dos criterios
fijados antes de medir (1 punto porcentual de la tajada del vendedor, 0,1 %
del excedente): `["tolerancia"]`, `["horizonte"]`, las dos, o ninguna.

**El código de salida 2 de la sonda es un veredicto, no un fallo**: esta
acción no se detiene por él, aunque el resto de la cadena (`oficial`,
`matriz`) sí tiene `set -e`.

Antes de correr la sonda de cada caso, la acción borra su veredicto viejo.
Si la sonda falla sin escribir, `matriz` no encuentra el JSON de una vez
anterior y se detiene, en vez de fijar las palancas con un veredicto que no
es de este código.

**Qué mirar.** Los dos JSON, `veredicto_E0.json` y `veredicto_E4.json`.
Conviene leerlos a mano antes de correr `matriz`.

### 4 · `matriz`

D18, D24, D27. Reemplaza a `oficial` para esta tanda. En orden:

1. las compuertas (el paso 1, otra vez);
2. lee los dos veredictos de `sonda79` y fija la **unión** de sus palancas:
   si alguno trae `tolerancia`, agrega `--rtol-acoplado 1e-7` (D35) a las
   trece corridas; si alguno trae `horizonte`, agrega
   `--horizonte-max-acoplado 0.4` (D26: para por estacionario en vez de
   horizonte fijo, hasta ocho veces el horizonte de producción). Si los
   veredictos no existen, se detiene y pide correr `sonda79` primero;
3. las trece corridas completas de la matriz de escalado (E0-E5, P1, P2, K1,
   I1, N1, CV2, SINU; spec 4.11 y 4.12), cada una con su propio almacén y su
   propio `--out-dir` en `SALIDAS_SERVIDOR/matriz/<caso>`;
4. la liquidación por institución y la equidad por mes, hora del día y día
   de la semana, de cada caso (cobertura `m1`: M3 está retirada, D10);
5. las figuras del foro, solo de E0;
6. la recogida.

Un caso que falla detiene la cadena, como en `oficial`. También uno que sale
con código 3 (D38): la corrida lo devuelve, después de escribir todas sus
salidas, si hubo alguna hora con excepción o más del 1 % de las horas de
mercado vencidas por el plazo. El lanzador dice entonces que se miren las
líneas `[D24]`, `[C-190]` y `[D38]` del registro de ese caso. Se retoma sin
repetir los que ya corrieron:

```bash
DESDE=P1 bash modelo_base/run_servidor.sh matriz
```

**Tiempo esperado.** Cada corrida es un horizonte completo de una sola
frontera por la vía acoplada y en modo ligero. El cargador da 6144 horas, del
2025-04-04 al 2025-12-16: así lo imprime el humo de E0 del 2026-09-13
(`outputs/run_2026-09-13_humo_e0.log`) y la corrida canónica de junio
(`T=6144h`), la misma cifra que da la sección de la tanda del 7 de
septiembre. La única fuente de
tiempo del servidor para la vía acoplada es la corrida oficial de septiembre:
el comentario de la acción `oficial` en `run_servidor.sh` dice «13,9 s por
hora de mercado con 32 procesos, de modo que las dos fronteras del horizonte
completo son unos 89 minutos», y la tabla de `oficial` de este documento da
unos 89 (min) a su paso 2, las dos fronteras con el almacén. Esa corrida tenía
6144 horas por frontera (C-173, en `core/almacen.py`), y las dos cifras
cuadran así: 2 × 6144 × 13,9 / 32 ≈ 89 (min). No son 89 minutos por
frontera, como decía antes esta línea: al mismo ritmo, una frontera de 6144
horas son 6144 × 13,9 / 32 ≈ 44,5 (min) de mercado por corrida, la mitad, más
el análisis ligero, que no se ha medido en el servidor. En la máquina de trabajo no hay
registro de aquella corrida con que confirmar el 13,9.

Con la palanca del horizonte activa (D26), las horas que no llegan al
estacionario en el horizonte de producción vuelven a resolverse con el
horizonte doble, y su tiempo de mercado crece. Lo acota el presupuesto de
D36: una hora no empieza una vuelta que no quepa en 5,3 millones de
evaluaciones del integrador, que en la máquina de trabajo son unos 584 (s),
el 65 % del plazo por hora de 15 (min). Las trece corridas se lanzan en
secuencia, no en paralelo entre sí (el paralelismo es interno a cada una,
entre horas), de modo que el total escala con las trece.

**Qué mirar al terminar.** Que la recogida no avise de nada: tras `matriz`
comprueba el almacén de cada uno de los trece casos y las figuras de E0, y
que hayan quedado en el fichero comprimido. Y qué palancas activó el paso 2: cambian la tolerancia o el
horizonte del acoplado de las trece corridas a la vez, de modo que conviene
saber si se activaron antes de leer ninguna cifra.

---

## Lo que este paquete NO hace

- **No decide por ti.** Las tres mediciones nuevas dejan cifras; la
  interpretación va en `HALLAZGOS.md`, hallazgos H-45 a H-47.
- **No responde la pregunta regulatoria.** Si el techo debe ser uno solo o
  uno por comercializador es del comité, y está planteada con sus cifras en
  el anexo de preguntas abiertas.
- **No toca el canon vigente.** Lo sustituye entero cuando la corrida
  canónica termine y se verifique.
