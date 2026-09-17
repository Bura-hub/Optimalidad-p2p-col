# Los parámetros del modelo, y cómo defender cada uno

**Estado al 2026-09-08, ampliado el 2026-09-17** con los cuatro parámetros de la
vía por reposo (D48 a D62; CAL-53, que es el ADR 0060) y, el mismo día por la
tarde, con la regla del **piso del vendedor marginal** (D63 a D70; H-91,
C-199; la enmienda del 2026-09-17 al ADR 0060). Material de sustentación. Un
apartado por parámetro, con lo que vale, de dónde sale, qué evidencia lo
respalda y **qué contestar si lo preguntan**.

Compañero de `MODELO_DEFINITIVO.md`, que dice qué es el modelo, y de
`HALLAZGOS.md`, que dice qué se encontró.

---

## El titular, y conviene abrir con él

> **De los parámetros libres del modelo base, ninguno gobierna el resultado.
> Medido resolviendo la partida con valores extremos: tres dan cero exacto y
> los otros tres se quedan por debajo de la tolerancia del integrador. Lo que
> decide el resultado son las dos cotas y el lado corto, y las cotas salen de
> la regulación y del tarifario.**

Eso no es una defensa retórica: cada afirmación tiene su medición y está abajo.

**Salvedad desde el 2026-09-17.** El titular habla de los parámetros heredados
del modelo base. La vía por reposo añade uno declarado que **sí gobierna el
nivel del precio y el reparto del excedente**, aunque no el volumen: el
presupuesto de precios σ. No es un parámetro libre escondido: es una primitiva
del mecanismo, se declara y se barre. Está en «Los parámetros del reposo».

---

## Probado resolviendo, no leyendo firmas (H-62)

La primera versión de este documento se apoyaba en leer las firmas de las
rutinas. **Leer una firma no es una prueba.** El 2026-09-08 se volvió a jugar
la partida entera con cada parámetro sustituido por valores extremos:

| Parámetro | Rango probado | Peor dif. precio | Peor dif. volumen |
|---|---|---:|---:|
| preferencia de autoconsumo | de 1 a 10.000 | **0** | **0** |
| saciedad | de 0,01 a 2.500 | **0** | **0** |
| competencia | de 0 a 50 | 3,1·10⁻³ | 8·10⁻¹⁵ |
| costo fijo | de 1 a 1.000 | **0** | **0** |
| costo cuadrático | de 0,01 a 10 | 2,3·10⁻⁹ | 8·10⁻¹⁵ |
| costo lineal | de la mitad al doble | 7,2·10⁻⁸ | 1,9·10⁻¹⁴ |

**Tres dan cero binario**, con factores de variación de hasta diez mil. Cero
exacto significa que **no participan en el cálculo**, no que su efecto sea
pequeño.

**Cautela que hay que decir si se presenta esta tabla:** está medida sobre
**una hora**, y que ni el costo lineal la mueva apunta a que en esa hora el
precio está pegado a una cota. Repetirlo sobre una muestra con precios
interiores está pendiente y va al servidor.

## Dónde SÍ tienen efecto, y es la pregunta fina

El modelo base tiene **dos solucionadores**, y el matiz importa:

**En su dinámica de replicador no tienen efecto.** Comprobado en su fichero:
los calcula y **no vuelve a usarlos**. Lo que aparece en la aptitud es el
multiplicador de Lagrange, que se llama parecido y es otra cosa.

**En su solucionador estático sí.** Ese maximiza directamente la suma de
bienestares, y sus parámetros están dentro de la función objetivo.

> **Si lo preguntan:** «Gobiernan el óptimo centralizado de referencia. No
> gobiernan el mercado descentralizado, que es lo que esta tesis simula. Y
> nosotros usamos como referencia centralizada el problema de transporte, que
> **es** el óptimo del bienestar cuasilineal con la disposición a pagar igual
> al techo y el costo de oportunidad igual al piso. De modo que la calibración
> correcta está elegida, aunque no la escribiéramos como parámetros.»

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

**Qué es.** El costo marginal de generar. **Es el que más peso tiene en la
aptitud del vendedor**, porque entra en ella directamente como su costo
marginal.

**De dónde sale.** No es un supuesto: es el **costo nivelado de la energía
solar medido por inversor**, con la corrección de irradiancia de Pasto. CAL-6.

**Y sin embargo tampoco movió el resultado en la medición de H-62**: con la
mitad y con el doble de su valor, la diferencia en el precio fue de 7·10⁻⁸ y en
el volumen de 2·10⁻¹⁴. Es la observación que hace sospechar que en esa hora el
precio está pegado a una cota, y la razón de que el barrido haya que repetirlo
sobre horas de precio interior.

**Si lo preguntan.** «Es el parámetro con más peso en la dinámica, y por eso no
lo heredamos: lo medimos, del costo nivelado de cada instalación. Aun así, en
la hora que barrimos ni él movió el resultado, porque el precio topaba en una
cota. Repetir ese barrido sobre horas de precio interior está pendiente y
declarado.»

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

## Los parámetros del reposo (añadidos el 2026-09-17)

Desde D48, el mercado de cada hora con datos reales se resuelve en el reposo
del juego regularizado, calculado en forma cerrada (`--metodo reposo`). Cinco
decisiones fijan cómo, y cada una tiene su opción en la línea de órdenes,
salvo el piso del juego, que no se elige: lo fija la caminata competitiva. Las
fuentes son las decisiones D48 a D70 (ADR 0059, con la enmienda del
2026-09-17 al ADR 0060), la calibración CAL-53 y los hallazgos H-89, H-90 y
H-91.

### El presupuesto de precios, σ · vale (I − 1)/I, con barrido

**Qué es.** La suma de los precios de los I compradores de la hora,
S = Σ_i [piso + σ·(techo_i − piso)]. Con bandas iguales, el precio común es
piso + σ·banda. Con un solo comprador, el precio es el piso, que desde el
2026-09-17 es el del vendedor marginal y no el mínimo: es el precio
competitivo del lado vendedor, y los vendedores inframarginales cobran su
renta (D54, reinterpretada por D66; H-91).

**De dónde sale.** Es el presupuesto de puja del Algoritmo 3 del documento
extenso de la autora (H-61), que su ecuación (24) conserva al clavar el
jugador virtual en su techo, generalizado a la banda como en H-32 y sin el
interruptor de C-136 (D50). Opción: `--modo-presupuesto sigma` con
`--sigma-nivel` en [0, 1], o sin ella para la sigma base.

**Evidencia.** El bloque de precios es un replicador sobre un presupuesto que
se conserva: la dinámica **redistribuye** el nivel entre compradores, pero no
lo fija, y con las tarifas colombianas el único ancla del modelo base, la
cobertura del costo del vendedor, queda bajo el piso (H-88; H-90, puntos 2 y
3). Con bandas iguales, el vendedor se lleva (I − 1)/I del excedente. El
barrido σ ∈ {0; 0,5; (I − 1)/I; 1} es la acción `barrido_sigma` del
lanzador.

**Si lo preguntan.** «El nivel del precio no lo produce la negociación: es una
primitiva del mecanismo, como el costo del vendedor en el caso de la autora.
La única regla de nivel que está en el modelo es su presupuesto de puja, y
esa es la que se adopta. Se declara y se barre, y con σ = 0 todos quedan en
el piso, que es lo que da su código con las tarifas colombianas (H-88).»

### La exploración entrópica, μ · vale 1 (COP/kWh), solo para validar

**Qué es.** Un término −μ·P·(ln P − ⟨ln P⟩) en el replicador del vendedor, que
empuja suavemente hacia el reparto uniforme: una fricción (D49).

**De dónde sale.** Es un apartamiento declarado, análogo en espíritu al filtro
que la autora añadió en la sección III-E de su documento extenso para mejorar
la convergencia. **Se añade como opción apagada de la vía acoplada**, y solo
allí, para validar el reposo y dibujar su convergencia; al escribir esto está
en implementación. La forma cerrada no lo usa: toma el límite μ → 0⁺, es
decir prioridad estricta y empates solo exactos (ADR 0060).

**Evidencia.** Sin el término, con un vendedor y varios compradores la
dinámica oscila sin llegar (H-87). Con él llega al reposo y se queda en las
horas medidas, y **μ solo cambia la velocidad**: en la hora 109 de la semana
de E0, con μ de 0,3 a 5 el reposo es el mismo, y con 0,05 no llega a t = 40
(H-90, punto 5). La sensibilidad a μ y los empates a menos de 3μ son la
medición M-E, pendiente.

**Si lo preguntan.** «No entra en las cifras: las cifras salen de la forma
cerrada. Entra en la validación, para que la dinámica llegue al punto que la
forma cerrada calcula, y su valor solo cambia cuánto tarda en llegar.»

### La liquidación · uniforme, que conserva el ingreso

**Qué es.** Cada comprador servido paga min(p_u, techo_i), con el precio
uniforme p_u de la hora fijado para que Σ_i min(p_u, techo_i)·q_i sea igual al
ingreso del reposo, Σ_i π_i·q_i (D51). Opción: `--regla-precio uniforme`; con
`puja`, cada uno paga su precio del reposo, que el almacén guarda siempre en
`precio_reposo`.

**De dónde sale.** De la bolsa de XM, que liquida a un solo precio por hora.
El vendedor recibe exactamente lo que el juego le da, y ningún comprador paga
más que su alternativa. Por eso el techo de liquidación de CAL-35 queda
inerte (ADR 0060).

**Evidencia.** La conservación del ingreso se comprueba en cada hora, en el
núcleo al 1e-9 relativo y, sobre el almacén, en la compuerta de salida de la
matriz. El pago según puja se publica como sensibilidad.

**Si lo preguntan.** «Las dos reglas le dan al vendedor lo mismo; cambian el
reparto entre compradores. Se eligió la del mercado mayorista colombiano. Un
comprador cuyo techo queda bajo el precio uniforme paga su techo y no ahorra:
está en su punto de indiferencia, y esa energía se cuenta aparte.»

### El despacho de vendedores sobrantes · por la alternativa de cada uno

**Qué es.** Cuando la oferta supera la demanda, qué vende cada vendedor:
primero el de **piso más bajo**, es decir el de menor costo de oportunidad, y
entre vendedores de piso igual, llenado por niveles (D64, desde el
2026-09-17). Opción: `--despacho-vendedores piso`, que es el defecto y el
modo de la matriz. Los otros dos valores, `costo` y `llenado`, son de
comparación: `costo` es el orden de mérito por el costo nivelado b_j, que fue
el defecto hasta el 2026-09-17 (D52), y `llenado` reparte por niveles entre
todos. **`merito` se acepta como alias de `costo`**, con un aviso `[D64]`
antes de cargar nada; el núcleo no lo admite, y la traducción vive en la línea
de órdenes y en el motor (C-199).

**De dónde sale.** Del piso del juego. Con pisos distintos por vendedor, un
solo piso de juego y emparejamiento de rango uno, todos los vendedores cobran
el mismo ingreso medio, y ordenar por b_j dejaba fuera al de alternativa baja
para despachar al de alternativa alta, que después quedaba cobrando por debajo
de ella. Ordenar por piso_j es lo que hace la subasta de precio uniforme: el
último despachado fija el precio, y es el que define el piso marginal (D63,
D65; H-91).

**Evidencia.** Medido en la hora 133 de E4 (2025-04-09 13:00): con el mérito
por costo vendía Cesmag a 330,15 (COP/kWh) mientras Udenar, con alternativa
147,46, no vendía; con el mérito por piso vende Udenar a 147,46, y el
excedente de la hora pasa de 1 694,38 a 2 460,29 (COP). Sobre los trece casos,
el cambio de regla recupera toda la energía que la participación retiraba,
entre el 0,2 % y el 60,2 % de lo transado según el caso (H-91). **Cuál de los
dos costos usa la dinámica sigue sin medirse:** es M-B reformulada, que ahora
enfrenta c_j = piso_j a c_j = b_j en la aptitud del vendedor, con 20 horas de
E4 y 10 de E5 en el servidor.

**Si lo preguntan.** «El vendedor entra al mercado por lo que le cuesta no
entrar, que es su alternativa regulada, y no por su costo nivelado, que apenas
varía entre instituciones: de 225 a 241,07 (COP/kWh), mientras la alternativa
va de 147 a 415 en una misma hora. Con el costo nivelado el orden dejaba a
vendedores cobrando bajo su alternativa y el mercado los expulsaba; con la
alternativa, no. Si la medición de la dinámica dice que el costo que manda es
el nivelado, se cambia la opción sin tocar el código, y esa comparación es la
medición **M-B reformulada**, que enfrenta c_j = piso_j a c_j = b_j en la
aptitud del vendedor.» Cuántas horas de compradores cortos despachan distinto
los dos criterios, y cuánta energía y cuánto excedente mueven, es otra
medición, **M-K**. Las cifras por institución de esas horas se citan con esa
salvedad (H-89, H-91).

### El piso del juego · el del vendedor marginal

**Qué es.** El precio por debajo del cual el juego no reparte nada: el piso
del **último vendedor que hace falta** para cubrir la demanda de la hora
(D63). Lo fija una caminata competitiva sobre los pisos distintos: p\* es el
menor nivel de piso que maximiza el mínimo entre la oferta con piso ≤ p y la
demanda con techo ≥ p (D65). No tiene opción en la línea de órdenes; se
mueve con `--despacho-vendedores`, porque los modos de comparación ponen el
piso en el máximo de los despachados.

**De dónde sale.** De que la tesis dio a cada vendedor su propio piso
(CAL-47, H-49) mientras el juego conserva uno solo. Hasta el 2026-09-17 ese
piso era el mínimo de los que despachan (D62), y el resultado era que el
vendedor de piso alto cobraba por debajo de su alternativa y la participación
lo retiraba. Con el piso marginal eso es imposible por construcción, y la
participación queda como guarda inerte (D67).

**Evidencia.** En las 4 886 horas con retiro de los trece casos siempre
existía un precio uniforme que cubría a todos, con brechas de mediana por caso
entre 1,7 y 262,4 (COP/kWh). Con el piso marginal se recupera el 100 % de la
energía retirada y el excedente queda mayor o igual en los trece casos, con K1
sin cambio (E1 de 1,363 a 1,669 millones de (COP)). **Las dos cosas están
medidas como contrafáctico**, con el núcleo sustituido y el lazo anterior, no
con la caminata que quedó implementada; comprobarlas sobre los trece casos es
M-F y M-I, al 0,1 (kWh). El teorema de cobertura, que ningún despachado cobre
bajo su piso, sí está ejercido sobre el núcleo nuevo: 141 136 horas
adversarias sin una sola violación (H-91, C-199).

**Si lo preguntan.** «Es el precio de cierre de una subasta de precio
uniforme, el mismo mecanismo que justifica nuestra regla de liquidación.
Coincide con el piso de siempre, y no cambia nada, por tres motivos: con un
solo vendedor; con todos los pisos iguales; y cuando el vendedor de piso menor
cubre él solo la demanda, que es el caso de la hora 4766. Entre los tres se
llevan once de las catorce horas reales que fijan las pruebas del núcleo, que
dan lo mismo al bit. Lo que cuesta es que los vendedores de
alternativa baja cobran por encima de ella, es decir renta inframarginal, y
por eso la prima se publica descompuesta en renta y parte del juego (D69).»

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
| **presupuesto de precios σ** | **(I − 1)/I, con barrido** | **sí: nivel y reparto, no volumen** | **Algoritmo 3 y ec. (24) del documento extenso; D50, H-90** |
| exploración entrópica μ | 1 (COP/kWh) | solo en la validación | D49, H-90: solo cambia la velocidad |
| liquidación | uniforme, conserva el ingreso | sí: reparto entre compradores | D51; CAL-53 (ADR 0060) |
| despacho de sobrantes | por la alternativa piso_j (`piso`, el defecto; `costo` y `llenado`, de comparación; `merito` es alias de `costo`) | sí: quién vende | D64, H-91; M-B decide qué costo usa la dinámica |
| **piso del juego** | **el del vendedor marginal** | **sí: nivel del precio y quién entra** | **D63, D65, H-91: teorema de cobertura** |

---

## La frase que cierra el asunto

> **La calibración no gobierna el ordenamiento.** Ya está probado por otra vía:
> el análisis de sensibilidad global mostró que el efecto total del costo lineal
> sobre la brecha entre mecanismos es de 8·10⁻⁵, con un margen de setenta y ocho
> veces. Si el resultado dependiera de los parámetros heredados, ese número
> sería otro.

Ver `MODELO_DEFINITIVO.md`, y en `HALLAZGOS.md` los apartados H-40, H-44, H-55,
H-58, H-59, H-60 y H-61.
