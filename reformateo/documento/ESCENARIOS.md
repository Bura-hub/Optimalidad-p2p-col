# Los cinco escenarios regulatorios, auditados contra la norma

**Estado al 2026-09-13**, con la revisión contra la forma de liquidar al final
del documento. La ficha del contrato se reescribió tras CAL-52. Una ficha por escenario: qué artículo lo sostiene, la
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

**La fórmula, corregida el 2026-09-13 (C-175).** Al cierre de cada mes se
comparan el excedente acumulado y la importación **del mes completo**. Lo que no
la supera es **permuta** y vale la tarifa menos el componente de comercializar;
lo que la supera se liquida a la bolsa de cada hora desde el corte, que es la
regla transitoria vigente. Es la liquidación del Anexo 4 de la Resolución CREG
101 072 para el autogenerador de hasta 100 kW, que es el tramo de las cinco
plantas. El corte es la hora en que la inyección acumulada desde el primer día
alcanza la importación total del mes.

Antes se comparaba contra el retiro acumulado hasta cada hora, y un adelanto
momentáneo mandaba a bolsa el resto del mes (H-69).

**Granularidad: mensual con corte horario.** El cupo y el crédito son del mes;
la hora del corte se determina con el acumulado horario, y el exceso se valora
a la bolsa de cada hora desde ella. MCm aplicará cuando la CREG expida la
metodología de traslado (H-73).

**Supuesto declarado.** El tramo se cuenta sobre el excedente bruto. Aquí es
correcto, porque sin mercado interno todo el excedente se entrega al
comercializador; la discusión de H-53 es propia del mercado entre pares.

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

**Granularidad: dos versiones publicadas**, horaria y mensual.

**Revisión del 2026-09-13.** La mensual ya compara contra la importación del mes,
como manda el artículo 25. **La horaria no corresponde a la norma**, que liquida
al cierre del período, y queda pendiente decidir si se retira o se conserva como
cota declarada. El porcentaje de reparto se calcula con la generación medida y
no con la capacidad que dice su rótulo (H-71). Y el excedente sobrante se valora
a la bolsa media del mes, cuando la regla vigente es la bolsa de cada hora: en la
frontera secundaria lo sobrevalora un 12,5 % (H-73).

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

**Revisión del 2026-09-13.** La Resolución CREG 101 099 no compensa: vende la
generación al mercado mayorista y atiende el consumo por contrato, y su reparto
horario con porcentaje fijo es solo para devolver el cargo por confiabilidad.
Ver H-72, pendiente de decisión.

---

## El mercado por la vía del colectivo · escenario nuevo (D8, H-76)

**Norma.** Resolución CREG 101 072, artículos 19 a 21, por la arquitectura de
dos niveles que describe la presentación del asesor regulatorio en el foro
(H-76): en el primer nivel la comunidad es un autogenerador colectivo que
liquida con la 101 072; en el segundo, el mercado entre pares decide hora a
hora quién recibe qué energía y a qué precio, y el dinero se ajusta entre los
miembros por contrato.

**Qué modela.** Cuánto del valor del mercado entre pares sobrevive si se lleva
a la práctica por la única vía legal disponible hoy, en vez de suponer que el
intercambio entre pares no paga los cargos del comercializador.

**Cómo se liquida**, copiado del docstring de `scenarios/scenario_p2p_colectivo.py`:

1. El porcentaje de cada miembro en cada mes es la energía que termina siendo
   suya dentro del fondo común: la comprada dentro más la exportada sin
   colocar, sobre el total exportado por la comunidad. Suma cien por
   construcción y se puede reportar cada mes (artículo 19).
2. La liquidación regulatoria es la del colectivo mensual con ese porcentaje,
   contra la importación que registra el medidor de cada miembro, con lo que
   el artículo 20 cobre sobre lo permutado.
3. El ajuste por contrato son los pagos internos del mercado, al precio de
   cada intercambio con el techo del comprador (CAL-35). Suman cero: no
   cambian el total, reparten.

**Granularidad: mensual con corte horario**, igual que el colectivo del que
hereda la liquidación (4.6).

**Lo que se espera, y la corrida debe confirmarlo o desmentirlo.** Con la
misma tarifa y sin cupos agotados, reasignar créditos entre miembros no crea
valor, porque un kWh permutado vale lo mismo lo reciba quien lo reciba; con
cinco fronteras el caso caro debería dejarlo por debajo de la autogeneración
individual.

**Dónde.** `scenarios/scenario_p2p_colectivo.py` (especificación del motor,
apartado 4.10).

---

## Lo que hace comparables a los seis

Dos convenciones, y conviene nombrarlas porque el documento las usa sin
declararlas:

**La primera.** El beneficio es ahorro más ingreso, **sin restar la factura
residual a la red**. Es una decisión avalada por la asesoría y declarada en
cinco módulos.

**La segunda, revisada el 2026-09-13 por decisión del autor.** Al excedente
que el mercado entre pares **no coloca** se le da el trato que la norma da al
excedente de un autogenerador: crédito de energía hasta el cupo del mes y la
bolsa de cada hora desde el corte, igual que su piso. Antes iba a bolsa horaria, lo que castigaba al
mercado con el mismo disparo que C-175 corrigió en la autogeneración
individual.

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

**Tres.** ~~El coeficiente de Gini, el precio de la equidad y el cociente frente
al colectivo solo existen agregados al horizonte.~~ **Cerrado** con C-165: cada
mecanismo anota su dinero en la hora que lo genera, esa anotación suma
exactamente el total publicado, y de ahí salen las tres métricas por mes, por
día, por hora del día y por día de la semana.

---

## Y dos defectos menores, encontrados de paso · **los dos cerrados**

**El primero.** ~~En el corte por sub-períodos, un campo llamado como el índice de
equidad guarda en realidad el coeficiente de Gini.~~ Cerrado con C-164: son dos
campos, y de paso el índice de equidad entra por fin a ese corte, donde
sencillamente no se guardaba.

**El segundo.** ~~El autoconsumo y la autosuficiencia llevan el nombre del otro, y
la capa de lectura del documento lo parchea al abrir el libro.~~ Cerrado con
C-164: corregido en el origen, en las cuatro funciones. Aviso: los artefactos
anteriores tienen las dos columnas intercambiadas.

---

## La revisión del 2026-09-13, contra la forma de liquidar

La pregunta que la ordena es del autor: **cómo liquida de verdad cada norma**, y
no solo qué artículo la sostiene. Tres textos la deciden. El artículo 26 de la
Resolución CREG 174, en la redacción del artículo 29 de la Resolución CREG
101 072 de 2025, liquida al autogenerador con cantidades del mes. Su literal c
liquida hora a hora el precio pactado. Y los artículos 16 y 18 de la Resolución
CREG 101 099 venden y atienden por contrato.

| Mecanismo | Qué se corrigió o se decidió | Qué queda abierto |
|---|---|---|
| C1 | el cupo es la importación del mes completo y el corte es la hora en que la inyección acumulada la alcanza (C-175); el exceso, a bolsa horaria, que es la regla transitoria vigente | nada nuevo |
| C2 | hereda el piso corregido; el literal c del artículo 26 confirma que el precio pactado se liquida por hora | nada nuevo |
| C3 | contrafáctico declarado, sin cambio | nada |
| C4 | la versión mensual ya compara contra la importación del mes | la horaria, el porcentaje de reparto (H-71) y el exceso, a bolsa horaria y no a la media del mes (H-73) |
| C5 | nada todavía | la norma no compensa (H-72) |
| P2P | el piso usa el cupo del mes (C-175); el residual se valora por el artículo 25, igual que el piso | programar el corte sobre el residual del mercado (H-74, resuelto en lo normativo) |

**Y la transición que sigue vigente.** La norma definitiva valora el exceso a
MCm, pero el parágrafo del artículo 25 lo mantiene a bolsa hasta que la CREG
expida el traslado, y los conceptos CREG 3018 y 3023 de abril de 2026 confirman
que no se ha expedido. Los Anexos 3 y 4 de la Resolución CREG 101 072 son, por
tanto, la regla que se modela: crédito con el total del mes, corte horario y
exceso a la bolsa de cada hora.

**Regla que se añade:** ningún escenario se liquida con una granularidad
distinta de la de su norma sin declararlo en su ficha.

**Y una lección sobre las pruebas.** Ninguna de las que había distinguía las dos
lecturas del cupo, porque ninguno de sus casos tenía un adelanto que después se
revirtiera. La compuerta de C-175 incluye ese caso.

### Lo que el motor hace desde el plan del 2026-09-13

Con las correcciones C-177 a C-182 (`CORRECCIONES.md`), sin corrida oficial
todavía:

- **C1**: el corte hx y la deducción por capacidad del artículo 25 pasan por
  la función única del Anexo 4, y la capacidad instalada que decide su tramo
  es la real de cada planta, escalable (C-177, C-180).
- **C2**: hereda el mismo piso que C1 y cobra el precio completo de la energía
  que vende, no solo la prima sobre su alternativa (C-177, C-181).
- **C3**: sin cambios; sigue siendo el contrafáctico declarado de exposición
  íntegra a la bolsa de cada hora.
- **C4**: es solo la versión mensual, con el exceso valorado a la bolsa de la
  hora del corte y el reparto igual como base (C-178).
- **C5**: el contrato despachado cada hora es el mínimo entre la inyección y
  la importación agregadas, con el precio de contrato de XM (C-179).
- **El mercado por la vía del colectivo**: escenario nuevo, que liquida el
  mercado entre pares con la arquitectura de dos niveles del asesor
  regulatorio (especificación del motor, apartado 4.10).

