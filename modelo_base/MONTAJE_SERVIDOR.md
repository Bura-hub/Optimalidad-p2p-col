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
| Código del proyecto | ~15 MB | **GitHub**, rama `main` |
| `MedicionesMTE_v3/` | 1,7 GB · 73 CSV | **Copiar a mano** (nunca se commitea, por diseño). Va en la raíz y con ese nombre: es lo que los cargadores buscan por defecto |
| `Documentos/copy/` | 208 KB · 17 ficheros | **Copiar a mano**. Solo lo necesitan dos compuertas, no las mediciones |
| `data/ASC_pdfs/` | 1,8 MB | **Opcional**, y solo si se van a reextraer tarifas. El CSV derivado sí viene del repositorio |
| `data/XM_Energía y Precios transados en contratos con destino a Mercado Regulado y No Regulado.xlsx` | 3,6 KB | **Copiar a mano**, con ese nombre exacto (el `.gitignore` excluye los `.xlsx`). Es la serie de precios de contratos de XM que usa C5; sin ella, toda corrida con `--include-c5` falla al arrancar con `FileNotFoundError`, y la matriz lleva `--include-c5` en sus trece casos. Lo encontró el humo de Linux del 2026-09-14. Huella MD5: `a700a88cae95b07696d421a83bc5b9ed` |

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
git checkout main
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
git checkout main
git pull --ff-only origin main
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

## El entorno exacto (H-84)

Antes de cualquier acción del subproyecto 2, el servidor corre con el mismo
entorno que la máquina de trabajo. Con datos de entrada idénticos al bit, la
hora 4184 con la generación por siete terminaba en la máquina de trabajo
(Python 3.13.7, numpy 2.4.4, scipy 1.17.1) y fallaba en el servidor (Python
3.10.12, numpy 2.2.6, scipy 1.15.3): `requirements.txt` deja las versiones
libres, y cada máquina instalaba lo que su Python admitía (scipy 1.16 en
adelante pide Python 3.11 o superior). `requirements-lock.txt` fija las
versiones exactas de la máquina de trabajo.

El servidor solo tiene Python 3.10, de modo que el 3.13.7 se instala con
`uv`, sin tocar el Python del sistema. Desde la raíz del repositorio:

```bash
mv .venv .venv_py310
.venv_py310/bin/python -m pip install uv
.venv_py310/bin/uv python install 3.13.7
.venv_py310/bin/uv venv --seed --python 3.13.7 .venv
.venv_py310/bin/uv pip install --python .venv/bin/python -r requirements-lock.txt
```

- El primer paso conserva el entorno viejo con otro nombre, por si hay que
  volver a él. Sus guiones (`.venv_py310/bin/pip` y los demás) llevan escrita
  en su primera línea la ruta vieja del intérprete, y al renombrar la carpeta
  dejan de funcionar. Por eso el segundo paso llama a pip como
  `python -m pip`, que no depende de ellos.
- `uv python install` descarga un Python 3.13.7 completo en la carpeta de
  `uv`, fuera del repositorio.
- `--seed` deja `pip` dentro del entorno nuevo, para quien lo necesite.
- `--python .venv/bin/python` fija explícitamente el entorno donde instala
  `uv pip install`. Sin esa opción tomaría el entorno activado o, si no hay
  ninguno, el `.venv` del directorio actual; con ella el destino queda
  escrito en la orden y no depende de desde dónde se corra.

La comprobación de versiones:

```bash
.venv/bin/python -c "import sys, numpy, scipy, pandas; print(sys.version.split()[0], numpy.__version__, scipy.__version__, pandas.__version__)"
```

Tiene que imprimir `3.13.7 2.4.4 1.17.1 3.0.2`. El lanzador toma
`.venv/bin/python` por su cuenta, de modo que nada más cambia. La acción
`entorno` del lanzador instala `requirements.txt`, con las versiones libres:
no se corre sobre este entorno.

**Las cifras entre máquinas se comparan solo con el mismo entorno.** Con
versiones distintas, una diferencia entre el servidor y la máquina de trabajo
no dice nada del modelo: puede ser el integrador. Con el mismo entorno, H-84
mostró además que la hora 4184 explotaba o no según el último decimal de la
entrada; el piso de P del acoplado (C-192) lo corrige, y en la máquina de
trabajo la hora ya da el mismo equilibrio con la base y con diez
perturbaciones de un ulp. En el servidor queda por medir, con la sonda de
H-79 y la semana de E4.

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

Ahora corre además el motor nuevo: veintiuna pruebas de pytest (Anexo 4,
umbrales del escalado, P2P residual del artículo 25, C4 mensual, P2P
colectivo, C5 de la Resolución 101 099, suma mensual, coincidencia, costos de
C3, plazo por hora, análisis ligero, cumplimiento de FA-3, el numeral 2 del
análisis, las dos palancas del acoplado, el oráculo del Anexo 4 con los
factores uno y siete, el presupuesto de la parada por estacionario con el
código de salida, D36 a D38, el piso de P del acoplado, H-84 con D40 a
D42, cuya prueba lenta tarda unos 3 a 4 (min) en la máquina de trabajo, y
el arranque factible del acoplado con la herramienta que compara los dos
arranques, H-85 con D45 y D46, cuya prueba lenta tarda unos 4 (min) en la
máquina de trabajo, y el criterio de parada sobre el reparto con el censo de
la campaña, H-86 con D47), y la compuerta C-165 con 48 horas en vez
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
En los pasos 3 y 4, además de `[D24]`, mira `[D37]` (horas sin mercado
porque la primera vuelta del integrador no terminó con éxito, entre ellas las
que corta D41 al primer valor no finito) y, en el paso 4, el «fallo_vuelta»
de `[D26]` (horas que conservaron la vuelta anterior buena). Con D41 la hora
que explota ya no vence el plazo, así que las vencidas bajan por
construcción; por eso D38 cuenta las vencidas más las sin éxito (D44), y su
línea da las dos cifras por separado y la suma.
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
salidas, si hubo alguna hora con excepción, o si las horas vencidas por el
plazo más las que quedaron sin éxito del integrador pasan del 1 % de las
horas de mercado (D44: con D41 la hora que explota ya no vence, se corta y
queda sin éxito, y tiene que seguir contando). El lanzador dice entonces que
se miren las líneas `[D24]`, `[D37]`, `[C-190]` y `[D38]` del registro de ese
caso; con la palanca del horizonte activa, también el «fallo_vuelta» de
`[D26]`. Se retoma sin repetir los que ya corrieron:

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

## La medición del arranque (H-85, D45 y D46)

Contexto en una frase: la matriz de trece corridas dejó nueve horas sin
resolver por el arranque del solucionador acoplado (H-85), que reparte la
oferta de cada vendedor a partes iguales; el arranque factible (la oferta
repartida en proporción al déficit de cada comprador, opción
`--arranque-acoplado factible`, apagada por defecto) se mide aquí antes de
decidir si pasa a ser el defecto y se repite la matriz (D45), y la misma
campaña mide en cuántas horas el precio por comprador no queda determinado
y cuánto mueve lo que paga cada uno (D46).

```bash
SECO=1 bash modelo_base/run_servidor.sh arranque   # antes: imprime las órdenes
bash modelo_base/run_servidor.sh arranque
```

Pide `MTE_ROOT`, como `matriz`, y toma `PROCS` del entorno. En orden:

1. un `bash -n` del lanzador, de cortesía. Las compuertas no se repiten: ya
   pasaron con este código;
2. cuatro corridas de la semana del 5 al 11 de mayo de 2025
   (`--desde 2025-05-05 --hasta 2025-05-12`, que contiene la hora 753 de E4):
   E0 (sin factor) y E4 (`--factor-generacion 7`), cada una con
   `--arranque-acoplado iguales` y con `--arranque-acoplado factible`, y las
   opciones de la matriz sin el análisis (`--data real --full --include-c5
   --no-regulado --metodo acoplado --plazo-hora 15
   --horizonte-max-acoplado 0.4`). Cada una con su almacén y su `--out-dir`
   en `SALIDAS_SERVIDOR/arranque/<caso>_<regla>`. **No se detiene por el
   código 3 de D38**: la semana de E4 con el arranque de hoy lo dará, por la
   hora 753. La acción imprime el código de cada corrida y, al final, todos
   juntos;
3. `reformateo/documento/scripts/sonda/compara_arranque.py` para E0 y para
   E4: un resumen en su registro (`modelo_base/logs/arranque_compara_<caso>_<fecha>.log`),
   el CSV hora a hora en `SALIDAS_SERVIDOR/arranque/compara_arranque_<caso>.csv`
   y el detalle por hora y comprador en `..._<caso>_compradores.csv`. Es
   una medición, no una compuerta: sale con 0 sea cual sea el resultado;
4. la recogida (`recoger arranque`), que comprueba los cuatro almacenes y
   los dos CSV, y que quedaron en el fichero comprimido.

**Qué mirar**, en el resumen de cada comparación (A es el arranque de hoy, B
el factible):

- **las horas sin resolver de cada arranque**, con su motivo. En E4, con el
  de hoy, debe salir la hora 753 (en la semana es la hora 9, el 5 de mayo a
  las 9:00) como «integrador sin exito»; con el factible, ninguna. Si el
  factible deja horas sin resolver que el de hoy resolvía, eso es un
  hallazgo;
- **cuántas horas cambian**: alguna entrega por comprador no coincide (su
  diferencia pasa de max(1e-4 (kWh), 1e-5 por la mayor de sus dos
  entregas)) o algún precio por comprador se mueve más de 1e-3 (COP/kWh), o
  la hora resolvió con un solo arranque; y el máximo y la media de esas
  diferencias, y el pago de cada comprador con cada arranque sumado sobre
  las horas que resolvieron los dos (una hora que resolvió uno solo, como
  la 753 de E4, no entra en esa suma y se lee en el CSV hora a hora);
- **las horas de precio indeterminado (D46)**: entregas iguales y algún
  precio distinto, como la hora 4184 de H-85. Para ellas, cuánto se mueve el
  pago de cada comprador y si la suma de lo que pagan los compradores se
  conserva (su diferencia no pasa de max(1e-3 (COP/kWh) por la energía de
  la hora, 1e-5 por la mayor de las dos sumas)).

Por qué la tolerancia de las entregas es combinada: el almacén guarda los
números en precisión sencilla (float32), y cerca de 20 (kWh) su paso es de
unos 1,9e-6 (kWh). Con una tolerancia absoluta de 1e-6 (kWh), una hora de
precio indeterminado podría salir como «entregas_distintas» por un solo
redondeo; 1e-5 relativo son unas 84 unidades de redondeo y cubre también
las energías de cientos de kWh de la matriz. La del precio sigue absoluta:
cerca de 400 (COP/kWh) el paso de float32 es de unos 3e-5. El resumen y la
primera línea de cada CSV (precedida de «#»; se lee con
`pd.read_csv(..., comment="#")`) dicen qué tolerancias se usaron, y la
comparación se repite en casa, en segundos, con otras (`--tol-kwh`,
`--tol-rel`, `--tol-precio`).

**Tiempo esperado.** Cuatro semanas de mercado, del orden de 5 a 15 (min)
cada una con 31 procesos (la semana de E4 del censo de H-84 tardó 5 min 56 s
de mercado con el piso de P), más la comparación, que tarda segundos. Es
decir, entre veinte minutos y una hora en total.

## La campaña de convergencia (H-86, D47)

Contexto en una frase: el criterio de parada del solucionador acoplado mira **el
precio**, y en muchas horas el precio ya está quieto mientras el reparto entre
compradores sigue moviéndose entero, de modo que el detalle por institución del
horizonte de producción es transitorio y no equilibrio (H-86). Esta campaña mide
**qué cuesta** mirar también el reparto, para fijar el horizonte de producción
con el costo medido delante. No cambia ese horizonte y no repite la matriz.

```bash
bash modelo_base/run_servidor.sh compuertas            # SÍ, en este paquete
SECO=1 bash modelo_base/run_servidor.sh convergencia   # antes: imprime las órdenes
bash modelo_base/run_servidor.sh convergencia
```

**Las compuertas hay que correrlas antes**, al revés que en la medición del
arranque. Este paquete mueve el defecto del arranque del acoplado a «factible»
(D45) y edita `tests/gate_almacen_cruzado.py`, que es la compuerta que compara
el motor contra el camino independiente de la sonda, es decir la que se
enteraría si los dos dejaran de arrancar igual; ninguna de las dos cosas ha
pasado todavía por una corrida de compuertas en el servidor. La acción no las
corre sola, para no encadenar una hora de pruebas a una campaña de una noche,
pero lo avisa en su paso 1.

Pide `MTE_ROOT`, como `matriz`, y toma `PROCS` del entorno. En orden:

1. un `bash -n` del lanzador, y el aviso de las compuertas;
2. **seis corridas** de la semana del 5 al 11 de mayo de 2025
   (`--desde 2025-05-05 --hasta 2025-05-12`): dos casos, E0 (sin factor) y K1
   (`--factor-demanda 2`, el caso de la matriz con menos horas estacionarias,
   el 33 %), cada uno con tres configuraciones del criterio de parada:
   - **hoy**: `--criterio-estacionario precio --horizonte-max-acoplado 0.4`,
     con el presupuesto y el plazo de la matriz (`--plazo-hora 15`);
   - **reparto a 0,4**: `--criterio-estacionario precio_y_reparto
     --horizonte-max-acoplado 0.4`;
   - **reparto a 2,0**: `--criterio-estacionario precio_y_reparto
     --horizonte-max-acoplado 2.0`.

   Las dos del criterio nuevo aflojan los topes a propósito (`--plazo-hora 60`
   y `--presupuesto-eval-acoplado 100000000`): la campaña existe **para ver el
   costo, no para acotarlo**, y una hora que hoy se corta por presupuesto es
   justo la que hay que medir. Las seis con `--arranque-acoplado factible`, que
   es el defecto desde D45 y el barato, cada una con su almacén y su `--out-dir`
   en `SALIDAS_SERVIDOR/convergencia/<caso>_<configuración>`. **No se detienen
   por el código 3 de D38**; la acción imprime el código de cada una y, al
   final, todos juntos;
3. las comparaciones de repartos con `compara_arranque.py`, la herramienta de
   D46: de cada caso, «hoy» contra «reparto a 2,0» y «reparto a 0,4» contra
   «reparto a 2,0». Aquí A y B no son dos arranques sino dos criterios, y las
   diferencias siguen siendo B menos A; la acción pasa `--etiqueta-a` y
   `--etiqueta-b` con el nombre de cada configuración, de modo que el resumen y
   la primera línea de los CSV dicen qué se comparó y no hablan de arranques;
4. el censo del costo,
   `reformateo/documento/scripts/sonda/censo_convergencia.py`, que lee los seis
   almacenes y escribe `SALIDAS_SERVIDOR/convergencia/censo_convergencia.csv`;
5. la recogida (`recoger convergencia`), que comprueba los seis almacenes, los
   cuatro CSV de las comparaciones y el censo.

**Qué mirar.**

- En el censo, por caso y configuración: cuántas horas pararon por cada motivo
  (estacionario, tope, presupuesto, vuelta fallida) y **cuántas quedaron con el
  reparto todavía en marcha**, es decir con su residuo del reparto por encima
  del 1 % de la energía de la hora. Esa es la cifra que dice cuánto del detalle
  por institución es transitorio.
- En el censo también, **lo que costó**: los segundos y las evaluaciones del
  integrador por hora (mediana, percentil 90, máximo y suma). El almacén los
  guarda desde D47, una fila por hora resuelta. **Los segundos son tiempo de
  pared del trabajador**, medidos mientras otras `PROCS` horas corren en la
  misma máquina: no son tiempo de procesador ni lo que costaría esa hora
  corrida sola. De ahí dos consecuencias prácticas: la mediana sale inflada
  frente a una hora aislada, y la suma de la columna no es la duración de la
  corrida, sino del orden de `PROCS` veces esa duración (la duración real está
  en el registro). Entre dos configuraciones de la misma campaña, con los
  mismos procesos y la misma máquina, la comparación sí es justa, que es
  exactamente para lo que está. **La cifra que no depende de la máquina es
  `evaluaciones`**, y es la que se cita al comparar con el servidor o al
  publicar. Si un almacén es anterior a D47 y no trae alguna de estas
  columnas, el censo dice «NO MEDIDO» en vez de contar ceros.
- En el registro de cada corrida, las líneas `[D26]` (horas por horizonte usado
  y por motivo de parada, y las que pararon con el reparto moviéndose),
  `[D47]` (el criterio, cuando es el nuevo) y `[D45]` (el arranque), más los
  segundos del mercado entero que imprime el paso 2 de la corrida.
- En las comparaciones, cuánto se mueve la entrega de cada comprador entre una
  configuración y otra. Si «hoy» y «reparto a 2,0» dieran lo mismo en las horas
  que las dos resuelven, el transitorio no sesgaría el reparto y D47 quedaría
  sin objeto; la medición de H-86 dice lo contrario (entre el 16 % y el 53 % de
  la energía de la hora en siete horas de E0).

**Tiempo esperado: del orden de una noche**, y hay que decirlo así. Las cuatro
corridas del criterio nuevo integran hasta que el reparto se quieta, y en la
medición de H-86 hubo horas de hasta **3 609 (s) con 28,7 millones de
evaluaciones** cada una, frente a los 26,3 (s) de la hora mediana al horizonte
de producción. La configuración «hoy» de cada caso es una semana normal, del
orden de 5 a 15 (min) con 31 procesos; las otras cuatro son las caras, y por eso
llevan plazo de 60 (min) por hora.

## La matriz con el reposo (D48 a D69; M-F y M-H)

Contexto en una frase: desde el 2026-09-17 el mercado de cada hora con datos
reales se resuelve en el reposo del juego regularizado, calculado en forma
cerrada (`--metodo reposo`; CAL-53, ADR 0060), y la matriz de trece casos se
repite una sola vez por esa vía (D57); la del 15 de septiembre, por la vía
acoplada, se queda en `SALIDAS_SERVIDOR/matriz` como foto de referencia, no
citada, y es contra la que se compara.

**La regla del piso (D63 a D69, 2026-09-17).** El piso del juego es el del
**vendedor marginal**: los vendedores despachan por su piso y una caminata
competitiva decide quién entra de cada lado (`--despacho-vendedores piso`, el
defecto). Con la regla anterior (D62, el piso mínimo de los que despachan) el
vendedor en permuta quedaba bajo su piso y la participación lo retiraba aunque
algún comprador le pagaría (E1 perdía 5 977 (kWh) frente a 10 625 transados).
Con el piso marginal todo despachado cobra al menos su piso, de modo que la
participación queda como guarda inerte (D67): **los retiros deben ser 0**, un
solo retiro hace salir la corrida con código 3 y la compuerta de salida lo
vuelve a comprobar. La prima de los vendedores se publica descompuesta en renta
inframarginal y parte del juego (D69). `merito`, el nombre viejo del despacho
por costo, se acepta como alias de `costo`, con aviso.

```bash
SECO=1 bash modelo_base/run_servidor.sh matriz_reposo   # antes: imprime las órdenes
bash modelo_base/run_servidor.sh matriz_reposo
# después, y aparte, cuando las cifras base ya estén:
SECO=1 bash modelo_base/run_servidor.sh barrido_sigma
bash modelo_base/run_servidor.sh barrido_sigma
```

**Antes de lanzarla.** El paquete trae dos ficheros del núcleo que el clon no
tiene al día: `core/reposo_mercado.py`, el reposo en forma cerrada, y
`core/almacen.py`, que gana la columna `precio_reposo` en los flujos. Sin el
segundo, la corrida por reposo muere al anotar la primera hora. El entorno es
el de `requirements-lock.txt` (H-84). **No hace falta `sonda79`**: la vía por
reposo no integra, y la acción no lee veredictos ni pone palancas del
acoplado.

### `matriz_reposo`

Pide `MTE_ROOT`, toma `PROCS` del entorno y comprueba `DESDE` antes de gastar
nada. En orden, y **para en el primer fallo**:

1. las compuertas, con seis pruebas más que en la campaña de convergencia:
   el núcleo del reposo (`test_reposo_mercado`), la vía por reposo en el motor
   (`test_reposo_motor`), la compuerta de salida
   (`test_compuertas_matriz_reposo`), la comparación
   (`test_compara_matriz_reposo`), la dinámica regularizada
   (`test_dinamica_regularizada`) y su compuerta
   (`gate_reposo_cero_dinamica`, con `-k "not lenta"`). **La compuerta de la
   dinámica solo ejerce ahí sus dos horas rápidas** (853 y 2120): las dos
   lentas (874 y 4766) cuestan horas, van aparte y sus órdenes exactas están
   escritas en el docstring de la propia compuerta;
2. las trece corridas, cada una en `SALIDAS_SERVIDOR/matriz_reposo/<caso>`
   con su almacén y su `--out-dir`, con las opciones de la matriz
   (`--data real --full --include-c5 --no-regulado --analisis-ligero` y las
   de cada caso) y las del reposo **escritas en la orden aunque sean los
   defectos**: `--metodo reposo --modo-presupuesto sigma --regla-precio
   uniforme --despacho-vendedores piso`, sin `--sigma-nivel`, es decir con
   la sigma base (I − 1)/I y el piso del vendedor marginal (D63 a D65). La
   corrida sale con código 3 si alguna hora terminó con excepción, si la
   participación retiró a algún vendedor (D67) o si las vencidas pasan del
   1 %. No lleva `--plazo-hora`: el motor no lo exige con
   el reposo, y su defecto de 15 (min) sigue de guardia en el lazo paralelo
   (D24). Detrás de cada corrida va **su compuerta de salida**, que para la
   cadena si falla;
3. la liquidación por institución y la equidad por mes, hora del día y día
   de la semana de cada caso;
4. las figuras del foro de E0: los grupos C, D y E de `gen_foro.py`
   (`--grupo CDE`). **El grupo A no sale**: lee la tabla de trayectorias, que
   la vía por reposo no escribe, y `gen_foro.py` se cae con `FileNotFoundError`
   en su primera figura (medido en la tarea 4b sobre un almacén por reposo;
   con `--grupo CDE` salen las seis figuras). **El grupo B tampoco se corre**
   (`gen_foro_b.py`): vuelve a simular el modelo base con otros parámetros, no
   lee el almacén ni depende de la vía, y ya salió con la matriz vieja. Las
   figuras no detienen la cadena: en la matriz vieja, una figura rota la
   detuvo antes de la recogida;
5. la comparación con la matriz vieja,
   `reformateo/documento/scripts/sonda/compara_matriz_reposo.py`, de los
   casos que tengan `SALIDAS_SERVIDOR/matriz/<caso>/almacen`. Si no hay
   ninguno, avisa, imprime la orden para hacerla en casa y sigue; tampoco
   detiene la cadena si falla;
6. la recogida (`recoger matriz_reposo`), que comprueba el almacén de cada
   caso, el registro de su compuerta de salida (el más reciente, porque
   `corre()` le pone la fecha al nombre), las figuras de E0 y, si había matriz
   vieja, el CSV de la comparación. **Estar no basta**: avisa en voz alta si
   la carpeta de figuras está vacía (el lanzador la crea antes de dibujar) o si
   el registro de una compuerta no termina `EN VERDE`, pero recoge igual,
   porque lo que hay sirve también cuando algo falló.

Ninguna corrida usa `--modo-presupuesto c136`. **Toda acción que lo use
tiene que lanzarse con `PARA_EN_FALLO=0`**: con ese presupuesto la corrida
sale siempre con código 3, por H-32, en unas 451 horas (medidas con D62; con
el piso marginal la cuenta puede cambiar) en las que el núcleo rechaza el
presupuesto en voz alta.

**Lo mismo con `--despacho-vendedores costo`, y por eso M-K también va con
`PARA_EN_FALLO=0`.** Con el piso máximo de los despachados, el lazo que
excluye a los compradores bajo ese piso ya no es monótono y en cerca del 2,7 %
de las horas sintéticas oscila: el núcleo lo dice en voz alta, la hora queda
con su motivo y la corrida sale con código 3. Es el comportamiento esperado,
no un fallo. **Las horas que oscilen se reportan como no comparables** en la
comparación de M-K (mérito por piso frente a mérito por costo en horas de
compradores cortos), y el resto se compara igual.

**Segunda salvedad de M-K: el polvo que el motor sí mira.** Con `costo` (y con
`llenado`) el despacho puede dejar a un vendedor una cantidad de polvo, por
debajo de 1e-9 de lo despachado en la hora: el núcleo no lo cuenta para el
piso del juego ni para la cobertura, pero **el motor sí lo mira**, porque su
umbral es `colocado <= 1e-9` absoluto, y si su piso queda sobre el precio
medio **la participación lo retira**. Entonces la corrida sale con código 3 y
la compuerta de salida falla `cero_retiros`. Con `PARA_EN_FALLO=0` eso es lo
esperado en M-K, no un hallazgo: se anota el caso y se sigue. **Con `piso`, el
modo de la matriz, no puede pasar:** solo despachan vendedores de piso menor o
igual al marginal, de modo que todos cobran al menos su piso y la guarda es
inerte por construcción.

**Tercera salvedad de M-K: el polvo que cobra bajo su piso.** En los modos
`costo` y `llenado`, un
vendedor despachado al que el filtro de polvo descarta puede acabar cobrando
por debajo de su piso: buscándolo a propósito en 80 000 horas, lo peor son
4,9e-5 (COP) con `costo` y 4,7e-5 con `llenado` (re-revisión de la tarea 5a,
`.superpowers/sdd/2026-09-16-reposo/task-5a-rereview.md`). **Con `piso`, que
es el modo de la matriz y el de producción, lo peor en esa misma búsqueda son
1,2e-11 (COP)**, es decir redondeo: **es imposible por construcción**, porque
pueden vender solo los de piso menor o igual que p\* y el ingreso medio del
rango uno nunca queda bajo p\*. Esa desigualdad no depende del filtro de
polvo, que es justamente lo que rompe la igualdad entre el piso y el mayor de
los despachados en `costo` y `llenado` (D63; H-91). No invalida la comparación
de M-K, pero si su registro muestra un vendedor bajo su piso con `costo`, es
esto y no un defecto nuevo.

### La compuerta de salida

`reformateo/documento/scripts/sonda/compuertas_matriz_reposo.py <almacén>
--cobertura m1` lee las tablas de horas, flujos, agentes y escenarios y
comprueba, hora a hora salvo la última, que es del caso entero:

| Identidad | Qué exige | Tolerancia nominal |
|---|---|---|
| volumen | la suma de los flujos es E = min(oferta de los vendedores que pueden vender, demanda de los compradores que siguen), descontando `vendedores_excluidos`, `vendedores_no_despachados` (D65), los retirados y `excluidos_bajo_piso` | 1e-6 (kWh) |
| excedente | captura × óptimo y la suma de ahorro más prima de los flujos valen Σ (techo − piso)·P | 0,01 (COP) |
| ingreso | Σ precio liquidado × q = Σ precio del reposo × q | 1e-9 relativo |
| precios | ningún precio de un comprador servido fuera de [piso del juego, su techo]; el uniforme y el común de la hora, dentro de [piso, techo mayor] | 1e-6 (COP/kWh) |
| vendedores | ningún despachado cobra en promedio bajo **su** piso (el del vendedor en sus flujos, no el del juego: el teorema de cobertura de D63); la parte de los vendedores no es negativa | 1e-9 |
| captura | en [0, 1] cuando el óptimo es positivo | 1e-6 |
| finitud | ningún NaN ni infinito en las columnas del reposo de las horas, en las de los flujos, en el sobrante y el faltante de los agentes ni en el valor de los escenarios | |
| sin mercado | las horas sin mercado no tienen flujos | |
| estado | toda hora resuelta tiene régimen; ninguna quedó sin resolver por excepción o plazo; las listas nombran agentes de esa hora; ningún vendedor está a la vez en `vendedores_excluidos` y en `vendedores_no_despachados` | |
| cero retiros | D67: ninguna hora tiene vendedores con papel «retirado» | |
| prima descompuesta | D69: en las horas resueltas, renta inframarginal + parte del juego = Σ (precio − piso del vendedor)·kWh de los flujos | 0,01 (COP) |
| P2P frente a C2 | del caso entero (síntesis §6): el beneficio P2P y el de C2 no coinciden en **todas** las instituciones con energía P2P; si coinciden en todas, es el síntoma del defecto viejo y falla; si solo en algunas, lo informa sin fallar | 1 (COP) o 1e-6 del mayor |

**El almacén guarda en precisión sencilla** (float32), con un redondeo
relativo de unos 6e-8 por valor. En las horas grandes, eso es más grueso que
la tolerancia nominal: con cientos de kWh, el excedente recalculado se mueve
centésimas de peso. Por eso cada comprobación usa la tolerancia nominal más
una cota del redondeo calculada para esa hora, y el resumen dice cuántas horas
pasan la nominal y quedan dentro de esa cota, para que ninguna se esconda en
ella. El motor ya comprueba las mismas identidades en doble precisión con las
tolerancias nominales; la compuerta comprueba lo que quedó escrito.

**Qué imprime.** Un resumen por régimen (horas, energía y la peor desviación
de cada identidad, con la de la prima descompuesta), los retiros de la
participación (deben ser 0 vendedores en 0 horas), la prima de los vendedores
de las horas resueltas en renta inframarginal más parte del juego frente a la
de los flujos, lo que se descontó de la oferta y la demanda por cada causa, en
horas y energía, P2P frente a C2 por institución, y termina con `COMPUERTA
MATRIZ REPOSO <caso> EN VERDE` o con la lista de fallos. Sale con 0 en verde,
1 si alguna hora o el caso no cumple y 2 si el almacén no se puede comprobar
(no está, no trae las columnas del reposo o las de D63 y D69, **no tiene
ninguna hora resuelta**, o sus escenarios no traen P2P y C2: un almacén de la
vía acoplada, o uno por reposo anterior al piso marginal, sale con 2). El caso
de ninguna hora resuelta importa porque sin horas resueltas ninguna identidad
mira nada: la compuerta saldría en verde sin haber comprobado nada, así que
sale con 2 y lo dice. Si aparece, lo que hay que mirar es el registro de la
corrida, `[C-190]`, `[D24]` y `[D38]`.

**Probada en la máquina de trabajo** sobre almacenes en parquet reconstruidos
por la vía por reposo a partir de la tabla de agentes de la matriz vieja (E0,
E1, E4, I1 y P2, con el motor hora a hora y la clase del almacén): en verde en
los cinco, y con los recuentos de régimen y de retiros de la compuerta de la
participación de la tarea 2. Esa prueba es de la regla D62; las identidades
de D63 a D69 (cero retiros, prima descompuesta y el descuento de los no
despachados) solo están probadas sobre el almacén sintético de
`tests/test_compuertas_matriz_reposo.py`: los trece almacenes reales los da la
matriz.

**Salvedad sobre P2P frente a C2.** En esos cinco almacenes reconstruidos solo
se rehicieron las horas del mercado; **la tabla `escenarios` es la que dejó la
corrida por la vía acoplada del 15 de septiembre**. Es decir, la identidad
«P2P frente a C2» se ejerció con los escenarios de la vía acoplada, no con los
que escribe la vía por reposo. Que esté en verde dice que la compuerta lee y
compara bien, no que los escenarios del reposo la vayan a pasar: eso lo dice
la matriz.

### Qué mirar

- **Las dos líneas `[D48]`** de cada `matriz_reposo_<caso>_<fecha>.log`. La
  del principio dice con qué reglas se resolvió:

  ```
  [D48] Mercado por reposo en forma cerrada: presupuesto sigma, sigma base ((I-1)/I), liquidacion uniforme, despacho piso
  ```

  La del final lleva, en una sola línea y con las cifras del caso en lugar de
  `<n>` y `<x>` (energías en kWh, con punto decimal):

  ```
  [D48] Horas por regimen: interiores <n> h (<x> kWh), topados <n> h (<x> kWh), excluidos <n> h (<x> kWh), mixto <n> h (<x> kWh), suma_no_cabe <n> h (<x> kWh), compradores_cortos <n> h (<x> kWh), un_comprador <n> h (<x> kWh), sin_mercado <n> h (<x> kWh), sin_ganancia <n> h (<x> kWh) (en las horas SIN MERCADO, la energia POSIBLE, no transada); horas que perdieron el mercado tras un retiro: <n> h (<x> kWh posibles, sin transar); horas del reposo con excepcion, fuera de los regimenes: <n> (ver [C-190]); compradores excluidos: <n> h (<x> kWh de deficit sin recibir), excluidos_bajo_piso: <n> h (<x> kWh); vendedores_excluidos: <n> h (<x> kWh de excedente); energia liquidada al techo (ahorro cero) <x> kWh y al piso <x> kWh de <x> kWh transados; energia topada en el reposo (precio del reposo igual al techo, antes de la liquidacion) <x> kWh; energia en horas con un solo comprador <x> kWh; vendedores retirados por la participacion: <n> en <n> h, con <x> kWh ofrecidos por los retirados (su excedente neto, sin transar), de los que <x> kWh eran comerciables (algun comprador con deficit sin cubrir y techo sobre el piso del retirado); retiros de la via por reposo: <n>, debe ser 0 (D67); prima de los vendedores descompuesta (D69): renta inframarginal <x> COP y parte del juego <x> COP
  ```

  Es decir: horas y energía por régimen, con la advertencia de que **en las
  horas sin mercado la energía es la posible, no la transada** (en
  `sin_ganancia` de D61, y en la que perdió el mercado porque la participación
  retiró a los vendedores que hacían falta, que además se cuenta aparte con su
  energía posible); las horas del reposo que acabaron
  en excepción, fuera de los regímenes; los excluidos, los excluidos bajo el
  piso y los vendedores excluidos; la energía liquidada al techo (ahorro
  cero) y al piso; la energía topada en el reposo; la de las horas con un solo
  comprador; los retirados por la participación, con **la energía que
  ofrecían** (su excedente neto) y **la parte comerciable** (la que algún
  comprador con déficit sin cubrir y techo sobre el piso del retirado habría
  comprado); **los retiros de la vía por reposo, que deben ser 0** (D67: con el
  piso marginal todo despachado cobra al menos su piso; cuentan también las
  horas que acabaron con motivo); y **la prima de los vendedores descompuesta**
  (D69) en renta inframarginal (lo que cobran sobre su piso los de piso menor
  que el marginal) y parte del juego (lo que el presupuesto de los compradores
  sube el precio medio sobre el piso marginal), en (COP).
- **`[C-190]`, `[C-151]`, `[D24]` y `[D38]`.** Por reposo, el código 3 sale si
  alguna hora terminó con excepción del núcleo, **si la participación retiró a
  algún vendedor** (la línea `[D38]` lo dice y cita D67) o si las horas
  vencidas por el plazo (D24) pasan del 1 % de las horas de mercado; la cadena
  se detiene, el lanzador dice qué mirar y cómo retomar. Un retiro es un
  hallazgo, no ruido: con el piso marginal no debería ocurrir.
- **La compuerta de salida** de cada caso, en
  `matriz_reposo_compuerta_<caso>_<fecha>.log`: la línea final y, si falla,
  la lista de fallos, que va al final del registro. **Esta compuerta es solo
  para almacenes por reposo**: uno de la vía acoplada o alternada sale con 2
  porque ninguna de sus horas resueltas trae régimen, y los almacenes de la
  matriz del 15 de septiembre salen con 2 porque les faltan los cuatro campos
  de D63 y D69. En los dos casos es lo correcto, no un fallo: esos almacenes
  se comprueban con las compuertas de la matriz vieja.
- **La comparación** (M-F), en `matriz_reposo_compara_<fecha>.log` y en
  `SALIDAS_SERVIDOR/matriz_reposo/compara_matriz_reposo.csv`: por caso y por
  institución, la energía transada, el precio medio ponderado por energía, la
  parte del vendedor y el beneficio P2P, vieja y nueva; de la nueva, la energía
  al techo, al piso, excluida y en horas de un solo comprador, y la captura
  media y agregada; y los órdenes P2P frente a C1 a C5 y P2P colectivo frente a
  C4, con la columna que marca si el signo cambió. «Al techo» y «al piso» usan
  la misma regla y la misma tolerancia que la línea `[D48]`, 1e-6 (COP/kWh)
  absoluta. Los escenarios no se recalculan: salen de la tabla `escenarios`
  del almacén, la misma que suma `liquidacion.py` y que la compuerta C-165 ata
  al total del motor. La comparación falla en voz alta, con código 2, si lo que
  suma trae algún valor no finito. La primera línea del CSV, precedida de «#»,
  dice qué se comparó y con qué tolerancia de empate (1 (COP) o 1e-6 del
  beneficio); se lee con `pd.read_csv(..., comment="#")`.

  Si en el servidor no estaba la matriz vieja, la comparación se hace en casa,
  en segundos. `--nueva` es la carpeta `SALIDAS_SERVIDOR/matriz_reposo` que
  sale del tar de la recogida, desempaquetado en su carpeta de entrega:

  ```bash
  python -u reformateo/documento/scripts/sonda/compara_matriz_reposo.py \
      --vieja SALIDAS_SERVIDOR/entrega_matriz_2026-09-15/SALIDAS_SERVIDOR/matriz \
      --nueva SALIDAS_SERVIDOR/entrega_<nombre>/SALIDAS_SERVIDOR/matriz_reposo \
      --salida SALIDAS_SERVIDOR/entrega_<nombre>/compara_matriz_reposo.csv
  ```
- **M-H, sin guion aparte.** La línea final `[D48]` de cada caso ya da la
  energía en horas con un solo comprador sobre la energía transada, y de los
  retirados, **la energía ofrecida y la comerciable**; el resumen de la
  comparación imprime además el porcentaje de un solo comprador por caso. Se
  leen las tres cantidades frente a la energía transada. **Aceptación: si la
  energía de las horas con un solo comprador pasa del 5 % de la energía
  transada de algún caso, D54 se reabre.** La comerciable de los retirados es
  la que la participación deja sin transar aunque algún comprador la habría
  pagado por encima del piso del retirado; con D63 no debe haber retirados y
  las dos cantidades deben salir en 0,00. D54 se conserva reinterpretada
  (D66): el comprador único paga el piso marginal, y los inframarginales cobran
  su renta.

### Cómo retomar

Un caso que sale con código distinto de cero, o cuya compuerta de salida
falla, detiene la cadena con sus salidas escritas. Se retoma sin repetir los
que ya corrieron:

```bash
DESDE=P1 bash modelo_base/run_servidor.sh matriz_reposo
```

`DESDE` repite las compuertas del paso 1. Un `DESDE` que no es ninguno de los
trece casos se rechaza antes de correrlas.

### `barrido_sigma`

D50: el presupuesto de precios del reposo con σ = 0 (todos en el piso, el
caso «Chacón fiel»), 0,5 y 1 (todos en su techo); la sigma base es la de
`matriz_reposo`. Va aparte para tener primero las cifras base, y después de
ella: no repite las compuertas, que ya pasaron con este código. **Por eso se
lanza con el mismo paquete que `matriz_reposo`**, sin traer código entre las
dos; si llegó código nuevo, antes `bash modelo_base/run_servidor.sh
compuertas`. El paso 1 del barrido lo recuerda.

Corre los trece casos por sigma en
`SALIDAS_SERVIDOR/matriz_reposo/<caso>_sigma<0|05|1>`, con las mismas
opciones que `matriz_reposo` más `--sigma-nivel`, cada uno con su compuerta
de salida, y termina con `recoger barrido_sigma`, que busca lo que exista y
avisa de lo que falte (y, como la de `matriz_reposo`, de las compuertas de
salida que no terminaron en verde). Recorre una sigma entera antes de pasar a
la siguiente. `SIGMAS` acota la lista (por defecto `"0 0.5 1"`; solo se
aceptan esas tres formas, `0`, `0.5` y `1`, porque `1.0` o `0.50` darían otra
carpeta) y
`DESDE` salta hasta ese caso **en la primera sigma de la lista**; las
siguientes corren enteras. Si se detiene, el lanzador imprime la orden exacta
para retomar:

```bash
SIGMAS="0.5 1" DESDE=P1 bash modelo_base/run_servidor.sh barrido_sigma
```

No hace liquidación, figuras ni comparación. La comparación de cada sigma
contra la base se hace en casa, en segundos. Las dos raíces son la carpeta
`SALIDAS_SERVIDOR/matriz_reposo` que sale del tar, desempaquetado en su
carpeta de entrega:

```bash
python -u reformateo/documento/scripts/sonda/compara_matriz_reposo.py \
    --vieja SALIDAS_SERVIDOR/entrega_<nombre>/SALIDAS_SERVIDOR/matriz_reposo \
    --nueva SALIDAS_SERVIDOR/entrega_<nombre>/SALIDAS_SERVIDOR/matriz_reposo \
    --sufijo-nueva _sigma05 --salida SALIDAS_SERVIDOR/entrega_<nombre>/compara_sigma05.csv
```

Si algún orden P2P frente a C_k cambia de signo dentro del barrido, se
publica como empate dentro de la sensibilidad (M-F).

### Tiempo esperado

No hay medición de la vía por reposo en el servidor. La estimación sale de
tres fuentes, y cada cifra dice de cuál:

- **Compuertas: unos 26 (min) más las cuatro pruebas nuevas.** La corrida de
  compuertas de la campaña de convergencia fue de las 08:41 a las 09:07 del
  16 de septiembre (nombres de sus registros y hora del fichero de consola,
  `SALIDAS_SERVIDOR/entrega_convergencia_2026-09-16/modelo_base/logs/`). De
  las cuatro nuevas, en la máquina de trabajo `test_reposo_motor` tardó unos
  42 (s) y las dos de esta tarea unos 4 (s) juntas; `test_reposo_mercado` no
  se midió por separado.
- **Las trece corridas: del orden de 15 a 25 (min).** En la matriz vieja, del
  inicio de E0 (21:55) al final de SINU (09:44:08) pasaron 11 (h) y 49 (min), de los
  que el mercado acoplado fue 41 826 (s), la suma de la línea
  «s | horas mercado» de los trece registros
  (`SALIDAS_SERVIDOR/entrega_matriz_2026-09-15/modelo_base/logs/matriz_<caso>_<fecha>.log`).
  Lo que no es mercado (carga de datos, escenarios, análisis ligero, almacén y
  figuras de cada corrida) suma entre 663 y 722 (s) para los trece, unos
  51 a 56 (s) por caso; el margen es el minuto que el nombre del registro
  redondea. Por reposo, el mercado no integra: en la máquina de trabajo, las
  6 144 horas de un caso pasan por el motor, en un solo proceso y con la
  escritura del almacén, en 5 a 8 (s). La compuerta de salida de un caso
  tarda unos 2 (s).
- **Lo demás.** En la matriz vieja, la liquidación y la equidad de los trece
  casos tardaron un minuto y medio (09:44 a 09:45:21), y las figuras de E0
  que leen el almacén, unos 30 (s); el grupo B, que tardaba unos 7 (min), ya
  no se corre. La comparación de los trece casos tarda unos 6 (s) en la
  máquina de trabajo.

En total, **del orden de una hora**, casi toda de compuertas. El barrido son
39 corridas sin compuertas: del orden de 40 (min) a 1 (h).

---

## Lo que este paquete NO hace

- **No decide por ti.** Las tres mediciones nuevas dejan cifras; la
  interpretación va en `HALLAZGOS.md`, hallazgos H-45 a H-47.
- **No responde la pregunta regulatoria.** Si el techo debe ser uno solo o
  uno por comercializador es del comité, y está planteada con sus cifras en
  el anexo de preguntas abiertas.
- **No toca el canon vigente.** Lo sustituye entero cuando la corrida
  canónica termine y se verifique.
