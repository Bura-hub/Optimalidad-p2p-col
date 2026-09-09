# Los cinco escenarios regulatorios, auditados contra la norma

**Estado al 2026-09-08**, con la ficha del contrato reescrita tras CAL-52. Una ficha por escenario: qué artículo lo sostiene, la
fórmula tal como está programada, qué precios usa y con qué granularidad, y
**qué supuestos no vienen de la norma**.

Regla que este documento impone: **ningún escenario se toca hasta tener su
ficha escrita.** Compañero de `MODELO_DEFINITIVO.md` y de `PARAMETROS.md`.

---

## Son cinco escenarios y siete columnas

| Columna | Qué es |
|---|---|
| P2P | el mercado entre pares, que es lo que la tesis estudia |
| C1 | autogeneración individual |
| C2 | contrato bilateral **interno**, a precio pactado |
| C3 | exposición al mercado mayorista |
| C4 | autogeneración colectiva, **en dos granularidades** |
| C5 | autogeneración remota |

La séptima es la segunda granularidad del colectivo, horaria y mensual, y las
dos son resultados legítimos que no se pueden fusionar.

---

## El hallazgo que reordena los dos primeros

**La cita del contrato bilateral está equivocada en cinco sitios del
repositorio, y un test la exige.** Verificado en el texto oficial de la
Resolución CREG 174, artículo 23 tal como quedó modificado por el artículo 27
de la Resolución CREG 101 072 de 2025:

> **Numeral 1. Si es un AGPE que NO utiliza FNCER.**
> a) A generadores o comercializadores con destino a usuarios no regulados. El
> precio de venta **es pactado libremente**.
> b) Al comercializador que atiende su consumo. El precio horario es el MCm.
>
> **Numeral 2. Si es un AGPE que SÍ utiliza FNCER.**
> a) A generadores o comercializadores con destino a usuarios no regulados. El
> precio de venta **es pactado libremente**.
> b) Al comercializador. **El crédito de energía del artículo 25.**

Las cinco instalaciones son solares, es decir fuentes no convencionales, luego
les aplica el **numeral 2**. El repositorio invoca el numeral 1.

**Y de ahí sale la estructura que faltaba:**

> **C1 es el numeral 2 literal b. C2 es el numeral 2 literal a. Son los dos
> destinos alternativos del mismo excedente de la misma planta.**

No son dos mundos distintos: son la elección que el artículo le ofrece al mismo
agente. Eso es lo que los separa, y es lo que hoy no está modelado.

---

## C1 · Autogeneración individual

**Norma.** Resolución CREG 174, artículo 25, es decir el **numeral 2 literal b**
del artículo 23. Decreto 2469 de 2014 y la estructura del costo unitario de la
Resolución CREG 119 de 2007.

**Qué modela.** Cada institución liquida sus excedentes contra su propia
frontera, sin agregación. Tres flujos con valoraciones distintas: el
autoconsumo, la permuta y el excedente que cruza el umbral.

**La fórmula.** Dentro de cada mes se acumulan inyección y retiro hora a hora.
Mientras la inyección no supere al retiro, el excedente es **permuta** y vale la
tarifa menos el componente de comercialización. En la hora del cruce se parte, y
a partir de ahí todo va a **bolsa horaria**.

**Granularidad: mixta.** La permuta se valora a la media mensual de la tarifa;
el excedente posterior al cruce, a la bolsa de su hora; y la búsqueda del cruce
es horaria acumulada dentro del mes.

**Supuesto declarado que no viene de la norma.** El tramo se cuenta sobre el
**excedente bruto**, es decir como si todo cruzara la frontera. Ver H-53, que lo
mide y lo eleva a consulta.

---

## C2 · Contrato bilateral interno

**Norma.** Resolución CREG 174, artículo 23 **numeral 2 literal a**: venta a
precio **pactado libremente**. La comunidad es el destino de esa venta, y la
condición de usuario no regulado la sostienen la Ley 143 de 1994 y la
Resolución CREG 086 de 1996.

**Qué modela, y es la comparación que le faltaba a la tesis.** Los mismos
vecinos intercambian **la misma energía** que intercambiarían en el mercado
entre pares, pero a un precio pactado de antemano en vez de a uno formado por el
juego. Es lo que un contrato de suministro hace: fijar el precio y quitar la
incertidumbre.

Aísla exactamente lo que aporta el mecanismo dinámico. Mismos flujos, misma
comunidad, misma energía: lo único que cambia es cómo se forma el precio. Si el
contrato diera lo mismo, la dinámica de replicador y la relajación lagrangiana
no estarían aportando nada, y eso hay que saberlo antes de que lo pregunte un
jurado.

**El precio, y no tiene parámetros libres.** Cada pareja contrata en el punto
medio de su propia banda, a mitad de camino entre lo que el comprador pagaría a
la red y lo que la red le pagaría al vendedor. Reparte la banda a la mitad, de
modo que el ahorro del comprador y la prima del vendedor son iguales por
construcción.

De ahí la propiedad que lo vuelve un patrón útil: **su índice de reparto vale
cero exacto**, y el mercado entre pares se mide contra él. Medido sobre el 2 de
mayo de 2025, el mercado desplaza **15,38 puntos porcentuales** del excedente
hacia los vendedores frente al reparto a la mitad.

**Granularidad: horaria**, y el precio cambia con la banda de cada pareja en
cada hora.

**Lo que NO entra aquí.** Que la comunidad compre su déficit por contrato. Eso
ya está en la capa tarifaria y aplica a los seis mecanismos por igual; meterlo
otra vez aquí contaría dos veces el mismo beneficio.

**Y una guarda que hoy no muerde.** Cuando el piso del vendedor queda por encima
del techo del comprador la banda está invertida y ese contrato no se firma; la
energía va a bolsa con el resto del sobrante. Medido en H-64: pasa en el 0,036 %
y el 1,900 % de las parejas-hora, pero en ninguna con papeles compatibles.

**La variante que quedó medida y no adoptada.** Vender el excedente a un tercero
al precio que XM publica para los contratos del mercado mayorista. H-63 encontró
que ese precio domina a la bolsa por partida doble, con media de 287,4 frente a
181,8 y desviación de 3,6 frente a 139,6, lo que dejaba el escenario de mercado
mayorista trivialmente peor. El cargador y sus pruebas se conservan.

---

## C3 · Exposición al mercado mayorista

**Norma.** No es un artículo: es el precio de bolsa, con el techo de escasez de
la Resolución CREG 101 066 de 2024. Es el **contrafáctico declarado**, no un
régimen que la comunidad elija.

**La fórmula.** Autoconsumo valorado a la tarifa del agente, y todo el excedente
a la bolsa de su hora. Sin componentes tarifarios.

**Granularidad: horaria pura.**

**Lo que aporta y conviene decir.** Es el único que reporta **riesgo**:
volatilidad del precio y pérdida esperada en la cola. C2 no lo reporta, y por
eso hoy no habría con qué contrastarlos ni aunque dieran cifras distintas.

---

## C4 · Autogeneración colectiva

**Norma.** Decreto 2236 de 2023 artículo 4, y Resolución CREG 101 072 de 2025
artículos 19 y 20, con la modificación del artículo 13 de la Resolución
CREG 101 087 de 2025. Hereda del artículo 25 de la 174.

**Qué modela.** El excedente del colectivo se reparte entre los miembros según
un porcentaje acordado, y cada fracción se permuta contra la importación de su
titular; el remanente va a bolsa.

**La aritmética que decide el régimen.** El artículo 19 obliga a que los
porcentajes sumen cien, y el artículo 20 exige que ninguno llegue al diez por
ciento para el caso favorable. Con cinco fronteras es imposible: harían falta
**once**. De modo que la comunidad cae necesariamente en el otro caso, donde la
permuta se liquida contra el agregado de peajes y no solo contra el cargo de
comercializar.

**Granularidad: dos versiones publicadas**, horaria y mensual. Las dos son
legítimas y no se fusionan.

---

## C5 · Autogeneración remota

**Norma.** Resolución CREG 101 099 de 2026, con sus artículos sobre la
devolución del cargo por confiabilidad y el límite de balance.

**Qué modela.** Compensación **hora a hora** entre fronteras de generación y de
consumo no contiguas, valorada a la tasa de usuario no regulado.

**Granularidad: horaria**, salvo la ventana del límite de balance, que es en
días y **solo diagnóstico**: no afecta al beneficio.

**Lo que hay que declarar.** El régimen está cerrado a esta comunidad por
vinculación económica entre sus miembros, según la revisión externa. Se modela
como vía prospectiva, no como opción disponible hoy.

---

## Lo que hace comparables a los seis

Dos convenciones, y conviene nombrarlas porque el documento las usa sin
declararlas:

**La primera.** El beneficio es ahorro más ingreso, **sin restar la factura
residual a la red**. Es una decisión avalada por la asesoría y declarada en
cinco módulos.

**La segunda.** Al excedente que el mercado entre pares **no coloca** se le da
el mismo trato que los demás mecanismos dan al suyo: precio de bolsa horario.
Sin eso, el mercado se compararía consigo mismo y no con ellos.

**Y la base física común:** el autoconsumo es idéntico en los seis, porque no
depende del mecanismo. Lo que varía es el valor que cada uno asigna a la energía
que pasa por la red.

---

## Los tres defectos que la auditoría deja abiertos

**Uno.** ~~La cita del artículo 23 está equivocada en cinco sitios y un test la
exige.~~ **Cerrado** con C-162: la cita quedó en el numeral 2 y el test corregido.

**Dos.** El índice de equidad tiene **dos definiciones distintas**: una por hora
para el mercado entre pares y otra agregada para los escenarios, esta con una
partición por la mediana del cociente entre generación y demanda. Comparar una
con la otra no es comparar lo mismo.

Acotado, no resuelto. La columna de la tabla usa **una sola** de las dos, la
agregada, para los seis mecanismos, de modo que sus celdas son comparables entre
sí. El reparto entre las dos partes de cada intercambio, que es la otra
definición, se reporta aparte para el mercado y para el contrato interno, y ahí
sí son comparables el uno con el otro. Lo que sigue sin poder hacerse es leer
una columna contra la otra.

**Tres.** El coeficiente de Gini, el precio de la equidad y el cociente frente
al colectivo **solo existen agregados al horizonte**. No hay versión mensual ni
horaria, de modo que hoy no se puede decir en qué meses el mercado reparte mejor.

---

## Y un defecto menor, encontrado de paso

En el corte por sub-períodos, un campo llamado como el índice de equidad guarda
en realidad el coeficiente de Gini. Quien lo lea por su nombre leerá otra cosa.
