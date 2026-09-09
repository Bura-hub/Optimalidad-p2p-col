# Los parámetros del modelo, y cómo defender cada uno

**Estado al 2026-09-08.** Material de sustentación. Un apartado por parámetro,
con lo que vale, de dónde sale, qué evidencia lo respalda y **qué contestar si
lo preguntan**.

Compañero de `MODELO_DEFINITIVO.md`, que dice qué es el modelo, y de
`HALLAZGOS.md`, que dice qué se encontró.

---

## El titular, y conviene abrir con él

> **De los parámetros libres del modelo base, ninguno gobierna el resultado.
> Cinco son inertes, invariantes o cero, y el único que mueve algo es un costo
> medido. Lo que decide el resultado son las dos cotas, y las dos salen de la
> regulación y del tarifario.**

Eso no es una defensa retórica: cada afirmación tiene su medición y está abajo.

---

## Quién entra en el juego y quién no

Comprobado en las firmas de las dos rutinas de la dinámica:

| Entra en la dinámica | No entra |
|---|---|
| los costos de generación | la preferencia de autoconsumo |
| el coeficiente de competencia | la saciedad |
| la constante del filtro | |
| las dos cotas de la banda | |

**La preferencia y la saciedad no son argumentos de ninguna de las dos
rutinas.** Solo aparecen en las funciones que informan el bienestar. Es la
razón de que su calibración heredada no haya estropeado ningún resultado.

---

## Uno por uno

### La preferencia de autoconsumo · vale 100

**Qué es.** El coeficiente lineal de la utilidad cuadrática. En una lectura
económica sería el precio de reserva, es decir lo que el agente valora el
primer kilovatio hora.

**De dónde sale.** Heredado del fichero original, que lo pone uniforme en 100
para sus seis agentes.

**Evidencia.** CAL-33 demuestra su **invariancia analítica** con el programa de
demanda desactivado: sin él, la demanda óptima la fijan los datos y no depende
de este parámetro. Y no es argumento de ninguna rutina del juego.

**Si lo preguntan.** «No entra en la dinámica; solo en el informe. Y sabemos
que su valor heredado es incoherente con nuestra escala de precios, porque
dice que un comprador valora la energía en 100 mientras la tarifa se la cobra a
730. Por eso el bienestar que reportamos no es el del modelo base sino el
excedente, que sí está bien planteado. Está en H-61.»

### La saciedad · vale 0,5

**Qué es.** La curvatura de la utilidad. Gobernaría la elasticidad de la
demanda.

**Evidencia.** CAL-5 lo midió con 0,5 y con 10, es decir un factor veinte, y
**el autoconsumo y la autosuficiencia no se mueven ni un dígito**. No afecta a
ninguna de las dos rutinas del juego.

**Si lo preguntan.** «Medido con un factor veinte de diferencia: el resultado
no cambia. Las dos fuentes del modelo base discrepan en su valor, y la
discrepancia no tiene consecuencias.»

### El coeficiente de competencia, que es donde vive la aversión al riesgo · vale 0,1

**Qué es.** Pondera el término de rivalidad entre compradores. El modelo base
lo presenta como la urgencia por conseguir la energía, y su resumen habla de
que los consumidores fijan precios «según su demanda y su aversión al riesgo».

**Evidencia.** CAL-2 lo barrió entre 0,01 y 5,0, dos órdenes de magnitud, y lo
declara **operacionalmente inerte**: el término es numéricamente despreciable
frente a los demás de la aptitud. Las dos fuentes del modelo base tampoco
coinciden, 0,1 en una y 1,0 en la otra, y la discrepancia **no tiene
consecuencias**.

**Si lo preguntan por la aversión al riesgo, que es la pregunta incómoda.**
«Está nombrada en el modelo y aparece en dos sitios. En este coeficiente, que
medimos inerte en dos órdenes de magnitud. Y en la forma logarítmica del
término de pago, que el modelo base justifica citando la aversión relativa al
riesgo. Esa justificación **no se sostiene**: la aversión relativa es una
propiedad de una utilidad sobre la riqueza y bajo incertidumbre, y aquí el
argumento del logaritmo es el precio de una transacción determinista. Además,
las cuatro referencias que el propio modelo base invoca para ese término lo
modelan de forma lineal. Está en H-61.»

> **En resumen: la aversión al riesgo está declarada en el modelo y no tiene
> efecto medible. Decirlo es más fuerte que fingir que lo tiene.**

### El costo cuadrático de generación · vale cero

**Qué es.** El término cuadrático del costo de generar.

**De dónde sale.** Se fija en cero para fotovoltaica pura: el panel no tiene
costo marginal creciente.

**Evidencia.** CAL-32 y la invariancia del equilibrio.

**Si lo preguntan.** «Fotovoltaica sin almacenamiento no tiene costo marginal
creciente. Ponerlo distinto de cero exigiría un mecanismo físico que aquí no
hay.»

### El costo lineal de generación · entre 225 y 241, por institución

**Qué es.** El costo marginal de generar. **Es el único parámetro que de verdad
mueve el resultado**, porque entra en la aptitud del vendedor como su costo
marginal.

**De dónde sale.** No es un supuesto: es el **costo nivelado de la energía
solar medido por inversor**, con la corrección de irradiancia de Pasto. CAL-6.

**Si lo preguntan.** «Es lo único del modelo base que gobierna el resultado, y
por eso no lo heredamos: lo medimos. Sale del costo nivelado de cada
instalación.»

### El costo fijo · vale cero

**Evidencia.** CAL-32 lo declara **invariante en el equilibrio**: el reparto,
el precio, la equidad y el precio de la equidad no cambian con él.

### La constante del filtro · vale 0,001

**Qué es.** El filtro de paso bajo sobre los multiplicadores, que el modelo base
introduce para acelerar la convergencia.

**De dónde sale.** Del fichero original, y su figura 3 enseña por qué hace
falta: sin él el sistema **oscila de forma permanente** alrededor del óptimo.

**Pendiente declarado.** Reproducir esa comparación con y sin filtro está en el
plan del aparato de figuras. Los parámetros existen y nadie los ha puesto a
cero todavía.

### Las iteraciones del juego · valen dos

**Evidencia.** CAL-1: la primera fija en esencia el volumen transado y la
segunda refina el precio. Verificado en los dos regímenes de datos.

### Las dos cotas de la banda · medidas

**Y aquí está lo que de verdad decide.** No son parámetros calibrados: son
**cotas medidas de la regulación colombiana**. El techo es el costo unitario de
cada comprador mes a mes; el piso, su alternativa según los artículos 22 y 23 de
la Resolución CREG 174. CAL-47.

**Si lo preguntan.** «El modelo base dejaba las dos como constantes exógenas sin
origen. Ese es el aporte: ponerles la regulación detrás. Y de ahí sale la
identidad que ordena todo, que el ancho de la banda es el cargo de
comercializar.»

---

## La tabla, para una diapositiva

| Parámetro | Valor | ¿Entra al juego? | Evidencia |
|---|---|---|---|
| preferencia de autoconsumo | 100 | **no** | invariante con demanda fija |
| saciedad | 0,5 | **no** | medido con factor veinte, sin efecto |
| competencia y aversión al riesgo | 0,1 | sí, pero **inerte** | barrido de dos órdenes de magnitud |
| costo cuadrático | 0 | sí | fotovoltaica pura |
| **costo lineal** | **225 a 241** | **sí, y manda** | **costo nivelado medido** |
| costo fijo | 0 | sí | invariante en el equilibrio |
| filtro | 0,001 | sí | del modelo base |
| iteraciones | 2 | sí | verificado en dos regímenes |
| **techo y piso** | **medidos** | **sí, y deciden** | **tarifario y CREG 174** |

---

## La frase que cierra el asunto

> **La calibración no gobierna el ordenamiento.** Ya está probado por otra vía:
> el análisis de sensibilidad global mostró que el efecto total del costo lineal
> sobre la brecha entre mecanismos es de 8·10⁻⁵, con un margen de setenta y ocho
> veces. Si el resultado dependiera de los parámetros heredados, ese número
> sería otro.

Ver `MODELO_DEFINITIVO.md`, y en `HALLAZGOS.md` los apartados H-40, H-44, H-55,
H-58, H-59, H-60 y H-61.
