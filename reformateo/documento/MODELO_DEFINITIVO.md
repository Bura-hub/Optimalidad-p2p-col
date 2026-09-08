# El modelo definitivo

**Estado al 2026-09-08.** Recoge la configuración con la que el modelo queda
tras la jornada del régimen del piso, comprobada contra el código y no contra
la memoria. Cada afirmación lleva dónde se verifica.

Este documento es el compañero de `HALLAZGOS.md` y `CORRECCIONES.md`: aquellos
registran lo que se encontró y lo que se corrigió; este dice **qué es el
modelo hoy**.

---

## El motor, que es de Chacón

Juego de Stackelberg entre vendedores y compradores, resuelto por **dinámica
de replicador con relajación lagrangiana**, integrando **el sistema conjunto**
de las dos poblaciones en una sola ecuación diferencial.

| | Elección | Se verifica en |
|---|---|---|
| Vía | **acoplada**, la integración conjunta del original | ADR 0048, CAL-50 |
| Integrador | LSODA con tolerancias 10⁻⁶ y 10⁻⁶, las del fichero de la autora | H-51 |
| Término de competencia | forma **agregada**, la del artículo publicado | ADR 0049, `gate_cal49_competencia` |
| Peso del jugador virtual | **barrera**, la del fichero original | H-46, `gate_h46_peso_virtual` |

La fidelidad al original está probada pieza por pieza: la prueba dorada pasa
**7 de 7** y la traducción se validó contra el MATLAB de la autora con una
diferencia del −1,56 %.

---

## La banda, que es aporte de esta tesis

Donde el modelo base tiene **dos constantes exógenas** —su ecuación (8) las
describe como «los precios de compra y venta de la red principal», sin decir
de dónde salen—, aquí hay dos cotas medidas de la regulación colombiana.

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
externa. **No existe en el modelo base** —buscado en su artículo, cero
apariciones— y es consecuencia inevitable de tener pisos distintos.

Es inerte cuando las cotas son uniformes, y muerde cuando difieren, que es
cuando hace falta. Se verifica en C-151 y `gate_c151_participacion_motor`.

**El techo por agente en la liquidación**, para que ningún comprador pague
dentro de la comunidad más de lo que le costaría la misma energía en la red.
Se verifica en CAL-35.

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
compuertas y la prueba dorada en 7 de 7.

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

## Lo único abierto

**La lectura del tramo de permuta.** Si el excedente colocado dentro de la
comunidad agota o no la permuta del vendedor.

Vale 235.165,2 (COP) en la frontera principal y 74.770,4 en la secundaria, y
cuesta 0,158 de índice de equidad en contra. Aparece solo en los meses en que
un agente cruza a bolsa: **junio y julio** en la principal, **abril y agosto**
en la secundaria. En los demás meses los dos regímenes son el mismo.

Se conserva la lectura bruta porque es la que el medidor registra y **la que
no favorece a la tesis**: si el asesor confirma la otra, los resultados solo
pueden mejorar.

**Con eso el modelo está listo para la corrida canónica.**

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
