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
por hora de mercado, y el horizonte son 5.160 horas por frontera: ni con
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

## Lo que este paquete NO hace

- **No decide por ti.** Las tres mediciones nuevas dejan cifras; la
  interpretación va en `HALLAZGOS.md`, hallazgos H-45 a H-47.
- **No responde la pregunta regulatoria.** Si el techo debe ser uno solo o
  uno por comercializador es del comité, y está planteada con sus cifras en
  el anexo de preguntas abiertas.
- **No toca el canon vigente.** Lo sustituye entero cuando la corrida
  canónica termine y se verifique.
