# El modelo definitivo

**Estado al 2026-09-17.** Recoge la configuración con la que el modelo quedó
tras la jornada del régimen del piso (2026-09-08), comprobada contra el código
y no contra la memoria, con los cambios del 2026-09-16 y el 2026-09-17. Cada
afirmación lleva dónde se verifica.

**Qué cambió el 2026-09-16 y el 2026-09-17.** El autor decidió resolver el
mercado de cada hora en el reposo del juego regularizado, en forma cerrada
(D48 a D62; CAL-53, ADR 0060). El núcleo está hecho (C-197) y conectado al
motor (C-198): **con datos reales, el reposo es la vía por defecto**. La
sección «Cómo se resuelve el mercado de cada hora» dice qué cambia, y las
filas que ese cambio afecta lo anotan. Se corrigieron además la atribución del
peso del jugador virtual y la de la forma de competencia.

**Y qué cambió el 2026-09-17, por la tarde.** Medido que el piso mínimo
dejaba a los vendedores de piso alto cobrando bajo su alternativa, y que la
participación los retiraba con su energía (hasta el 60 % de lo transado en
E2), **el piso del juego pasa a ser el del vendedor marginal** y el despacho
ordena por la alternativa de cada vendedor, no por su costo nivelado (D63 a
D70; H-91, C-199; la enmienda del 2026-09-17 al ADR 0060). Las tres filas de
la sección del mercado que eso toca lo dicen, y la restricción de
participación pasa a ser una guarda que debe quedar inerte.

Este documento es el compañero de `HALLAZGOS.md` y `CORRECCIONES.md`: aquellos
registran lo que se encontró y lo que se corrigió; este dice **qué es el
modelo hoy**.

---

## El motor, que es de Chacón

Juego de Stackelberg entre vendedores y compradores, resuelto por **dinámica
de replicador con relajación lagrangiana**, integrando **el sistema conjunto**
de las dos poblaciones en una sola ecuación diferencial. **En producción ya no
se integra: se calcula en forma cerrada el reposo de esa misma dinámica**, con
la regularización entrópica que la hace llegar (D48, D49); la integración
queda para validarlo y dibujar su convergencia. Ver la sección siguiente.

| | Elección | Se verifica en |
|---|---|---|
| Vía | **reposo en forma cerrada** con datos reales (`--metodo reposo`, el defecto, D48), empezando por la matriz de `matriz_reposo`; la **acoplada**, la integración conjunta del original, queda para validar el reposo y dibujar su convergencia, y es la que produjo la matriz del 15 de septiembre (ver la sección «Cómo se resuelve el mercado de cada hora»; la conexión con el motor se registra en C-198) | ADR 0048, CAL-50, ADR 0059 |
| Integrador | LSODA con tolerancias 10⁻⁶ y 10⁻⁶, las del fichero de la autora | H-51 |
| Término de competencia | forma **agregada**, la de esta traducción: con β iguales, la del código de la autora sin el factor (I − 1); la publicada, β_i·Σ_{k≠i} π_k·Σ_j P_jk, queda disponible | ADR 0049, H-90, `gate_cal49_competencia` |
| Peso del jugador virtual | **barrera**, la de la ecuación (24) del documento extenso de la autora (H-61); el fichero original usa el precio | H-46, H-88, `gate_h46_peso_virtual` |

La fidelidad al original está probada pieza por pieza, con dos apartamientos
declarados en la tabla: la forma de competencia y el peso del jugador virtual
no son los del fichero original. Con esa salvedad, la prueba dorada pasa
**7 de 7** y la traducción se validó contra el MATLAB de la autora con una
diferencia del −1,56 %.

---

## Cómo se resuelve el mercado de cada hora (decidido el 2026-09-16; en producción desde C-198)

**En el reposo del juego, calculado en forma cerrada**, y no en el estado que
deja la integración en un instante. Con un vendedor y varios compradores, la
dinámica de la tabla anterior oscila alrededor de un reposo que no alcanza
(H-87). Con una exploración entrópica en el replicador del vendedor, de
μ = 1 (COP/kWh), sí llega a ese reposo y se queda en las horas medidas (H-90).
De modo que el reposo se calcula directo, sin integrar, y la vía acoplada
queda para validarlo y dibujarlo (D48, D49).

| | Elección | Se verifica en |
|---|---|---|
| Reparto | prioridad por precio; llenado por niveles del grupo marginal; topados y excluidos en su techo; regla de saturación cuando la suma no cabe sobre el piso | H-90, D53 |
| Emparejamiento | de rango uno: cada vendedor reparte en proporción a lo que recibe cada comprador | H-90 |
| Nivel del precio | presupuesto que suma, por comprador, el piso más (I − 1)/I de su banda, con barrido; con un solo comprador, el piso del vendedor marginal, que es el precio competitivo del lado vendedor | D50, D66, H-90, H-91 |
| Liquidación | precio uniforme de la hora que conserva el ingreso del reposo | D51 |
| Vendedores sobrantes | despachan por su **alternativa piso_j** creciente, con llenado por niveles en los empates; el costo nivelado b_j queda como opción de comparación, y M-B se reformula para decidir cuál de los dos usa la dinámica | D64, H-89, H-91 |
| Piso del juego | el del **vendedor marginal**, el último que hace falta para cubrir la demanda; una caminata competitiva sobre los pisos fija quién entra y cuánta energía se transa; la hora sin ganancia posible queda sin mercado | D61, D63, D65, H-91 |

**El nivel del precio es una primitiva del mecanismo, no un resultado de la
puja.** El bloque de precios solo redistribuye un presupuesto que se conserva
(H-90), y con las tarifas colombianas el único ancla del modelo base, la
cobertura del costo del vendedor, queda bajo el piso (H-88). Por eso el nivel
se declara y se barre.

Se verifica en CAL-53 (ADR 0060), ADR 0059 y C-197.

**El piso del juego es el del vendedor marginal** (D63, desde el 2026-09-17).
Con pisos distintos por vendedor y un precio uniforme, anclar el juego al piso
mínimo dejaba a los vendedores de piso alto cobrando bajo su alternativa, y la
restricción de participación los retiraba con toda su energía: hasta el 60 %
de lo transado en E2, y siempre existía un precio uniforme que los cubría a
todos. Con el piso marginal esa energía se recupera entera, y el excedente
queda mayor o igual en los trece casos, con K1 sin cambio. **Las dos cifras
están medidas como contrafáctico**, es decir con el núcleo sustituido por una
copia del borrador y con el lazo anterior, no con la caminata competitiva que
quedó implementada: comprobarlo sobre los trece casos es M-F y M-I, que las
comparan al 0,1 (kWh). La medición, el diagnóstico y la regla están en H-91;
la implementación, en C-199.

La conexión con el motor está hecha (C-198, C-199): con datos reales, el
reposo es la vía por defecto, y la acoplada, que produjo la matriz del 15 de
septiembre, queda para validar y dibujar. Quedan dos cosas en curso. La matriz
de trece casos con el reposo (`matriz_reposo`), que sustituye a la del 15 de
septiembre (D57) y que es la única fuente de cifras por institución con la
regla nueva. Y la validación del reposo contra la dinámica regularizada, por
régimen, que son las mediciones M-A a M-H de H-90, con M-B reformulada y M-I a
M-K añadidas por H-91.

---

## La banda, que es aporte de esta tesis

Donde el modelo base tiene **dos constantes exógenas**, que su ecuación (8)
describe como «los precios de compra y venta de la red principal» sin decir de
dónde salen, aquí hay dos cotas medidas de la regulación colombiana.

### El techo es el costo unitario de cada comprador

Mes a mes, y no un escalar comunitario.

Con el escalar, **109 de 200 horas** medidas de la frontera principal dejaban
a algún comprador con beneficio exactamente cero, porque su precio se resolvía
contra un techo ajeno y luego se recortaba al propio. Con el techo propio son
**cero horas**. En la frontera secundaria, de cuatro a cero.

Se verifica en H-45, C-146 y `gate_c146_techo_en_el_juego`.

### El piso es la alternativa de cada vendedor

Según los artículos 22 y 23 de la Resolución CREG 174: **permuta** mientras su
inyección acumulada del mes no supere su retiro acumulado, y **bolsa** a partir
de ahí. De modo que el piso depende del agente y de su estado dentro del mes.

El tramo se cuenta sobre el **excedente bruto**, es decir como si todo cruzara
la frontera comercial. **Queda declarado como simplificación y pendiente de
consulta al asesor**; la alternativa, contarlo sobre el excedente asignado,
está medida y vale 235.165,2 (COP) en la frontera principal y 74.770,4 en la
secundaria.

Se verifica en CAL-47, H-49, C-148, H-53 y `gate_cal47_solucionador`.

### Y de ahí la identidad que ordena todo

Si el comprador paga a la red el costo unitario completo y el vendedor recibe
ese mismo costo unitario menos el componente de comercialización, **el ancho de
la banda es exactamente el cargo de comercializar**.

Son unos 175 (COP/kWh) de media, con un recorrido del 5,3 % en los nueve meses.

---

## Lo que se añadió porque la banda dejó de ser única

**La restricción de participación.** Un vendedor se retira si el mercado le
paga, por el conjunto de lo que coloca, menos que su propia alternativa
externa. **No existe en el modelo base** (buscado en su documento extenso,
H-61, con cero apariciones) y es consecuencia inevitable de tener pisos
distintos.

Es inerte cuando las cotas son uniformes, y muerde cuando difieren, que es
cuando hace falta. Se verifica en C-151 y `gate_c151_participacion_motor`.

**Con el piso del vendedor marginal queda como guarda inerte** (D67, desde el
2026-09-17). El emparejamiento de rango uno paga a todos los vendedores el
mismo ingreso medio, y ese ingreso no puede quedar por debajo del piso
marginal, que es el mayor de los que despachan: **ningún vendedor despachado
cobra bajo su alternativa, de modo que ninguno se retira**. Es un teorema, no
una medición, y la re-revisión lo ejerció sobre 141 136 horas adversarias sin
una sola violación. La restricción se conserva porque es la alarma: cero
retiros es compuerta de la matriz, y un retiro detiene la corrida y es un
hallazgo (H-91, C-199).

**El techo por agente en la liquidación**, para que ningún comprador pague
dentro de la comunidad más de lo que le costaría la misma energía en la red.
Se verifica en CAL-35. **Con la liquidación uniforme del reposo queda
inerte**: cada comprador paga el mínimo entre el precio uniforme de la hora y
su techo, de modo que ningún precio liquidado lo supera y el recorte no llega
a actuar (D51; CAL-53, ADR 0060). En la vía acoplada se conserva; ver la
sección «Cómo se resuelve el mercado de cada hora».

**El paso de tiempo explícito**, que la formulación original no lleva. Se
verifica en CAL-46 y `gate_cal46_paso_horario`.

---

## Los parámetros

| Parámetro | Valor | Origen |
|---|---|---|
| Costo cuadrático del vendedor | 0 | fotovoltaica pura, CAL-32 |
| Costo lineal del vendedor | costo nivelado por institución | calibrado, CAL-6 |
| Dotación | 100 | modelo base |
| Saciedad | 0,5 | modelo base |
| Aversión al riesgo | 0,1 | modelo base |
| Respuesta a la demanda | **desactivada** con datos reales | decisión propia |

La respuesta a la demanda está implementada y es fiel, pero va desactivada con
datos reales, de modo que la demanda que entra al mercado es literalmente la
serie medida. **Sesga en contra de la tesis**: excluye toda ganancia por
desplazamiento de consumo, que en el modelo base vale un 24 % menos de energía
vendida a la red y un 53 % menos comprada.

---

## Los datos

Cinco instituciones reales de Pasto, **6.144 horas** de abril a diciembre de
2025, y dos escenarios de cobertura fotovoltaica.

| | |
|---|---|
| Generación de Udenar | reconstruida desde el inversor del proyecto (CAL-44) |
| Atípicos | guardia físico de tres bandas medidas (CAL-45) |
| Régimen tarifario | las cinco como usuarias **no reguladas** (CAL-47) |
| Comercializadores | los **dos reales**, cuatro con uno y una con el otro (CAL-50) |

---

## Las tres cosas que hay que saber decir de él

**Es fiel al motor de Chacón y está probado pieza por pieza**, con once
compuertas y la prueba dorada en 7 de 7, salvo los apartamientos declarados:
la forma de competencia y el peso del jugador virtual de la tabla del motor, y
el mercado resuelto en el reposo del juego regularizado.

**Su banda no es la de Chacón, y por eso puede responder preguntas que él no
puede.** La del régimen del piso, sin ir más lejos, no existe en el modelo
base: allí el piso es una constante.

**Y sabe cuándo callarse.** Tres métricas quedan expresamente descalificadas
para ciertas preguntas, y las tres con medición y compuerta:

| Métrica | Cuándo no sirve | Por qué |
|---|---|---|
| Bienestar | para elegir el piso | los términos de pago se cancelan entre los dos lados, y lo único que le queda del precio es la penalización de competencia: prefiere el piso más bajo **por construcción** (H-55) |
| Excedente | cuando cambia la alternativa externa | crece porque la alternativa empeora, no porque la comunidad mejore (H-47) |
| Índice de equidad global | al comparar regímenes | es un cociente de sumas y se pondera solo: hay que mirar si los denominadores pesan lo mismo (H-57) |

Quien arbitra es **la factura**, en pesos, porque contiene lo que la red paga
por el excedente que se exporta, que es lo único que el régimen cambia.

---

## Lo que queda abierto

**La lectura del tramo de permuta.** Si el excedente colocado dentro de la
comunidad agota o no la permuta del vendedor.

Vale 235.165,2 (COP) en la frontera principal y 74.770,4 en la secundaria, y
cuesta 0,158 de índice de equidad en contra. Aparece solo en los meses en que
un agente cruza a bolsa: **junio y julio** en la principal, **abril y agosto**
en la secundaria. En los demás meses los dos regímenes son el mismo.

Se conserva la lectura bruta porque es la que el medidor registra y **la que
no favorece a la tesis**: si el asesor confirma la otra, los resultados solo
pueden mejorar.

**La validación del reposo.** Las mediciones M-A a M-H de H-90, en el
servidor: la forma cerrada frente a la dinámica regularizada por régimen
(M-A), el costo del vendedor con vendedores sobrantes (M-B, reformulada por
H-91: la alternativa piso_j frente al costo nivelado b_j), la regla de la
suma que no cabe sobre el piso (M-C), la estabilidad (M-D), la sensibilidad a
μ y los empates (M-E), la matriz de trece casos con el reposo (M-F), el caso
de Chacón (M-G), y el peso de las horas de un solo comprador y los retiros
con la liquidación nueva (M-H). H-91 añade M-I a M-K: los trece casos con el
núcleo nuevo, la descomposición de la prima y las horas en que los dos
criterios de despacho difieren.

**Ninguna de las dos bloquea la matriz con el reposo (H-90, punto 9).** La
primera se conserva en su lectura bruta. La segunda ya no decide la regla, que
está decidida y aplicada (D63 a D70): decide si cada régimen se publica como
reposo verificado o como regla declarada, y M-B, cuál de los dos costos del
vendedor se cita como el de la dinámica.

---

## Cómo regenerar lo que sostiene este documento

```
python reformateo/documento/scripts/sonda/tramo_residual.py
python reformateo/documento/scripts/sonda/regimen_piso.py --muestra 3000
python reformateo/documento/scripts/sonda/compara_regimenes.py --muestra 3000
python reformateo/documento/scripts/sonda/tablas_regimen.py
python reformateo/documento/scripts/sonda/piso_por_mes.py
```

En el servidor, las tres primeras van encadenadas:

```
bash modelo_base/run_servidor.sh decision 3000
```
