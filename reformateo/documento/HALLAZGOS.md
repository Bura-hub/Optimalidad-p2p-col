# Hallazgos — sesión 2026-08-21 (montaje del documento de proceso)

Hallazgos surgidos al construir la infraestructura del documento. Se vuelcan
aquí aplicados o no, según el protocolo del proyecto.

---

## H-1 · El docstring de `data/preprocessing.py` tiene cifras desfasadas

**Estado: acotado. La tesis ya lo había resuelto; el código no.**

> **Corrección respecto a la primera versión de esta nota.** Se registró como
> hallazgo nuevo, y no lo es del todo: `Documentos/FinalTesisV2/tesis.md`
> §4.4 ya declara las cifras medidas (1.517, 213 y 94 h), ya señala que las
> de 989, 216 y 112 «no reproducen contra el código y los datos vigentes» y
> ya las da por reemplazadas. Lo que aquí se aporta es una verificación
> independiente por un tercer camino —el caché instrumentado— y la
> constatación de que **el docstring del código sigue sin actualizarse**.
> El texto que sigue conserva la medición; lo que cambia es a quién se
> atribuye el desfase.

El docstring del módulo declara, en su sección «Tipos»:

> `"net"` : neteo agresivo (Udenar, **989 h** con D<0 sobre el horizonte v3).
> `"net_partial"` : neteo leve (Mariana **216 h**, UCC **112 h** con D<0).

Medido sobre el horizonte canónico (2025-04-04 → 2025-12-16, 6.144 h), con las
funciones del propio pipeline y verificando que las series finales coinciden
al bit con `build_demand_generation()`:

| Institución | Docstring | Medido | Mínimo alcanzado |
|---|---:|---:|---:|
| Udenar | 989 h | **1.517 h** (24,7 %) | −33,57 kW |
| Mariana | 216 h | **213 h** (3,5 %) | −2,41 kW |
| UCC | 112 h | **94 h** (1,5 %) | −5,91 kW |

El docstring además **se contradice a sí mismo**: su sección «Problema que
resuelve» dice que Udenar tiene «~20 % de las horas con valor negativo», lo
que no cuadra con 989/6144 = 16,1 % pero sí se acerca a la medición real
(24,7 % del horizonte; 25,1 % de las horas con dato).

También difiere el mínimo: el docstring cita −34,6 kW y lo medido es
−33,57 kW.

**Verificación de que la medición es correcta.** El caché instrumentado
reproduce las diez series finales del pipeline con `max|dif| = 0` exacto, de
modo que recorre exactamente el mismo camino. Y el patrón temporal confirma
la interpretación: las horas negativas de Udenar se concentran entre las 11
y las 15 h (223 casos a las 13 h, 218 a las 12 h), que es la franja de
producción solar. Es neteo, no ruido.

**Acción tomada.** `reformateo/documento/scripts/datos.py` ya no fija estos
conteos: los lee siempre del caché medido (`conteo_negativas()`). El
documento cita las cifras medidas.

**Acción pendiente (decisión del autor).** Actualizar el docstring de
`data/preprocessing.py`, que es código del repositorio principal y no se ha
tocado en esta sesión. Conviene comprobar antes de qué corrida salían las
989 h: podrían corresponder a `MedicionesMTE` v2 o a un horizonte anterior,
en cuyo caso bastaría con datar la cifra en vez de reemplazarla.

---

## H-2 · Las figuras de la presentación salen del canon superado

**Estado: sin acción en esta sesión; afecta a `Presentacion/tesis_p2p/`.**

Las 20 figuras de la presentación Beamer se generan desde
`Presentacion/tesis_p2p/datos/canonica_m{1,3}/`, que es una copia del canon
de **junio**, no del vigente de agosto. En consecuencia:

- `fig_ranking.png`, `fig_giro_agr.png`, `fig_institucion.png` publican C4 en
  **Caso 1** (52.219.945 / 32.372.584), que `VERSIONES.md` §3 marca como «no
  publicar».
- `fig_bootstrap.png` publica el bootstrap viejo (5.020,57 / 8.161,82) en vez
  del vigente (8.114,14 / 10.579,11).
- `fig_giro_agr.png` rotula «C5≈C4 — la regla AGR no agrega valor», mientras
  que el frame 42 del `.tex`, parchado el 2026-08-07, afirma lo contrario.
  **La figura contradice al pie de su propia diapositiva.**
- `datos/canonica_m3/daily_series_20260611_0253.csv` es el contaminante ya
  identificado: una copia de M1 dentro de la carpeta M3. La cuarentena limpió
  el canon pero no esta copia.
- `presentacion.pdf` en disco es del 2026-07-27, anterior al parche del
  `.tex`, de modo que el PDF compilado sigue llevando la lectura refutada.

**Implicación asumida.** El documento de proceso no reutiliza ninguna figura
existente; todas se regeneran desde el canon de agosto. Queda como decisión
aparte si se corrige la presentación.

---

## H-3 · La compuerta del canon y el hash de la corrida

**Estado: confirmado, ya recogido en la guía.**

Ambas compuertas pasan en limpio (`CANON 2026-08 INTACTO` y `CANON INTACTO`).
Se confirma también lo que advierte `CANON.md` §6: las hojas `Diagnostico` de
los dos libros canónicos registran `git_hash = dc7c0e7`, pero el commit con el
que se reproduce la corrida es **`5c5baa2`**. El anexo de reproducibilidad
debe citar el segundo.

---

## H-8 · Las cinco entidades no comparten comercializador

**Estado: CERRADO como decisión metodológica (2026-08-22). Queda
pendiente propagarlo a la tesis y al artículo.**

> **Decisión del autor.** Se liquidan las cinco entidades con la tarifa
> publicada por CEDENAR, por ser la única fuente disponible, pública y
> auditable. Las condiciones contratadas por cada entidad con su
> comercializador no son públicas y no se dispuso de ellas. Lo que el
> hallazgo exige, por tanto, no es una consulta previa sino que la
> decisión quede declarada donde se usan las cifras.

Todo el aparato económico del trabajo liquida a las cinco entidades contra
la tarifa publicada por CEDENAR. El autor informa que **la mayoría de
ellas contrata su suministro con ASC Ingeniería**, es decir, con un
comercializador distinto del operador de red, cosa que la regulación
colombiana permite.

**El supuesto no está declarado en ninguna parte.** Un barrido del
repositorio no encuentra una sola mención a ASC Ingeniería en código,
documentación ni manuscritos. La tesis, por el contrario, presenta el dato
como si fuera un hecho: §5.5 habla de la calibración «con datos y
referencias verificables para Colombia, tarifas reales del
comercializador», y §3.3 titula «Estructura del costo unitario desde la
factura del comercializador». Ninguna de las dos advierte que se trata de
un comercializador supuesto y no del real.

**Por qué importa, componente por componente.** El costo unitario se
descompone en siete piezas y no todas dependen de quién comercialice:

| Componente | Peso medio | ¿Depende del comercializador? |
|---|---:|---|
| Generación (G) | 38,6 % | **Sí.** La propia tesis lo llama «el único componente cuyo valor se origina en transacciones de mercado y, por ello, el único que admite ser negociado por la vía de sustituir las compras del comercializador» (§3.3) |
| Comercialización (Cvm) | 22,0 % | **Sí.** Remunera la actividad minorista de ese comercializador |
| Distribución, transmisión, pérdidas, restricciones | 34,1 % | No. Las fija el operador de red |
| Otros cargos (COT) | 5,2 % | Parcialmente |

Es decir, **las dos componentes de mayor peso, que suman el 60,6 % del
costo unitario, dependen justamente del contrato de comercialización**.

**Qué NO invalida.** El ordenamiento entre mecanismos. Los seis se
liquidan contra la misma tarifa, de modo que una desviación de esa tarifa
respecto de la real afecta a todos por igual. La comparación es interna y
se sostiene.

**Qué SÍ invalida.** Toda lectura de las cifras absolutas como factura
real de alguna de las cinco entidades. Y debilita cualquier afirmación
sobre ahorro monetario efectivo, que es distinta de una afirmación sobre
ventaja relativa entre mecanismos.

**Paralelismo con H-7.** Es el segundo hallazgo de la misma familia: una
magnitud del modelo que no es lo que su rótulo dice. Allí, la cobertura
M1 no es el campus; aquí, la tarifa CEDENAR no es la que factura la
mayoría. En los dos casos el ordenamiento sobrevive y el valor absoluto
no, y en los dos la resolución exige preguntar al proyecto MTE.

**Acción tomada.** El Capítulo 2 deja de afirmar que comparten
comercializador y remite a la decisión. El Capítulo 5 la declara en un
`trampabox` que dice qué se decidió, por qué, qué componentes afecta y qué
sobrevive: entre una tarifa auditable que no es exactamente la que se
factura y una tarifa exacta que nadie puede comprobar, se optó por la
primera.

**Acción pendiente.** Propagar la declaración a la tesis (§3.3 y §5.5) y
al artículo, que hoy presentan la tarifa como la del comercializador de
las cinco. Contrastar contra las facturas efectivas queda recomendado para
una fase posterior, no como condición de este trabajo.

### Ampliación 2026-09-06 · son exactamente cuatro, y lo confirman dos vías independientes

El hallazgo decía «la mayoría». Ahora se sabe cuáles y son **cuatro de las
cinco**, confirmado por dos fuentes que no se conocen entre sí:

1. **La transcripción de la reunión con los asesores.** Un asesor las
   enumera: «son cuatro, UDENAR, hospital, Mariana y UCC, todas transan con
   la ASC a través de contratos bilaterales».
2. **El propio archivo de consumos de ASC**, entregado con las
   recomendaciones. Su censo de 162 clientes contiene la Universidad de
   Nariño en dos fronteras, Torobajo y VIPRI, la Universidad Mariana en dos,
   la principal y sus laboratorios, la Universidad Cooperativa y el Hospital
   Departamental. **No contiene al CESMAG.**

**Tres cosas más que la transcripción aporta y que el registro no tenía.**

**El asesor avala expresamente el precio de referencia**, que era el punto
más débil de la decisión: «ese no lo pasaron, por eso es que Brian toma un
precio de referencia». La objeción de que la tarifa no es la contratada
queda así reconocida por quien conoce el asunto, y no pendiente.

**El asesor avala también el techo por agente**, que hasta ahora era una
decisión interna sin respaldo externo: «esa tarifa va a ser como los techos
para cada uno, nunca van a sobrepasar el tope de la tarifa regulada, eso es
lo que haría que el mercado sea dinámico y sea eficiente».

**Y da una receta concreta para mejorar la fuente**: tomar la estructura del
costo unitario, sustituir el componente de generación por el precio de
contratos del mercado no regulado que publica el operador del mercado, y
conservar el resto, que son cargos regulados. La maquinaria ya existe porque
los componentes están desglosados; lo que falta es el dato.

**Consecuencia práctica.** La tarifa publicada por ASC pasa a ser la fuente
preferente, y sustituirá a la actual sin cambiar nada del diseño: el costo
unitario que un comercializador publica para un mercado **ya lleva dentro
los cargos de red del operador**, de modo que no hay que mezclar dos
fuentes. Queda como supuesto nuevo, más pequeño que el actual y en la
dirección correcta, aplicarle esa tarifa también al CESMAG, que no es
cliente de ASC.

**Un matiz que corrige el hallazgo original.** Este decía que las
condiciones contratadas «no son públicas». Es cierto del contrato bilateral,
pero **no de la tarifa publicada**: ASC reporta al sistema único de
información y figura en el boletín tarifario del regulador, aunque allí sale
promediada entre mercados porque atiende varios. Existe, por tanto, una vía
pública y auditable que el hallazgo daba por cerrada.

---

## H-7 · Ni M1 es el campus ni M3 es el circuito fotovoltaico

**Estado: RESUELTO por el inventario de medidores (2026-08-22). Obliga a
renombrar las dos coberturas en todo el proyecto.**

El documento, la tesis y el artículo describen las dos coberturas de
medición como «totalizadores de campus» (M1) y «submedidores del circuito
fotovoltaico» (M3). El archivo `Inventario_Medidores_MTE.xlsx`, que cruza
la plataforma MTE con el inventario de instalación, el SCADA local y las
conexiones reportadas por el instalador, establece qué mide realmente cada
equipo. Ninguna de las dos descripciones se sostiene.

### Qué mide el «Medidor 1», que el trabajo llama cobertura M1

| Institución | Circuito según el inventario | Ubicación del tablero |
|---|---|---|
| Udenar | Circuito principal, tablero subestación | subestación del **bloque Sur** |
| Mariana | **Circuito inyección**, totalizador principal | estación eléctrica, campus Alvernia |
| UCC | **Circuito inyección**, totalizador principal | cuarto técnico, piso 0, **bloque A** |
| HUDN | **Circuito inyección principal** | subestación, piso 3, bloque principal |
| CESMAG | Circuito principal-totalizador | cuarto técnico **bloque B** |

**Ninguno es un totalizador de institución.** Tres de los cinco son
circuitos de inyección, es decir, el punto por donde entra la generación;
los otros dos totalizan un bloque concreto y no el campus. Esto explica de
forma directa la anomalía que motivó este hallazgo: los 9,09 kW medios del
HUDN no son el consumo de un hospital de nivel III, sino el tránsito por
su circuito de inyección.

### Qué mide el «Medidor 3», que el trabajo llama cobertura M3

| Institución | Circuito según el inventario |
|---|---|
| Udenar | Circuito secundario, **piso 1A** |
| Mariana | **No tiene.** Se aproxima con el Medidor 1 escalado por 0,3 |
| UCC | **Totalizador piso 2** |
| HUDN | **UPS de ginecología** |
| CESMAG | Circuito principal-totalizador, cuarto técnico **bloque A** |

**Ninguno es «el circuito alimentado por el fotovoltaico».** Son circuitos
secundarios, totalizadores de un piso y, en el caso del HUDN, la
alimentación ininterrumpida de un servicio clínico concreto. La cobertura
M3 no es, por tanto, una frontera homogénea entre instituciones: es
simplemente el tercer medidor de cada sitio.

### Qué NO invalida

El ordenamiento entre mecanismos. Los seis se liquidan sobre la misma
serie de demanda en cada cobertura, de modo que la comparación es interna
y se sostiene con independencia de qué circuito represente esa serie.

### Qué SÍ invalida

1. Los nombres de las dos coberturas, que deben dejar de usarse.
2. Toda lectura de la cobertura del 19,1 % o del 91,2 % como
   autosuficiencia de la institución. Es la razón entre la generación y el
   consumo **del circuito medido**.
3. La contraposición «campus completo frente a ramal fotovoltaico» sobre
   la que se explicaba la bifurcación. Lo que hay son dos circuitos
   distintos de cada sitio, y su relación con el consumo institucional
   está por establecer.

### Nombres propuestos

Se sustituye «totalizador de campus» y «submedidor del circuito
fotovoltaico» por una descripción de lo que son: **M1, circuito principal
o de inyección**, y **M3, circuito secundario**. Ambas se acompañan de la
razón entre generación y consumo medido, que es lo único que la cifra
significa.

### Una cuestión abierta que el inventario deja planteada

El mismo archivo documenta que cada medidor tiene un transformador de
corriente y una escala de conversión, y advierte que el valor leído del
equipo «puede diferir del instalador». En Mariana y CESMAG la diferencia
es de dos órdenes de magnitud: el instalador reporta 800 y 1.600 A de
escala mientras que la verificación lee 10 A. La portada describe además
un procedimiento de corrección, `correct_mediciones_mte.py`, que produce
archivos `*_corregido.csv` a partir de los originales.

**Ni la carpeta `Analizador/` ni ningún archivo `*_corregido.csv` están en
este repositorio**, y no se pudo determinar si `MedicionesMTE_v3/` es
anterior o posterior a esa corrección. Queda abierto, y conviene
resolverlo antes que cualquier otra cosa: si las series estuvieran sin
corregir, el efecto sobre las magnitudes no sería menor.

---

## H-6 · El horizonte termina cuatro meses antes de donde llega el dato

**Estado: abierto; el documento lo declara, no lo resuelve.**

El horizonte canónico va del 2025-04-04 al 2025-12-16 (\num{6144} h). El
inicio está plenamente justificado por el dato: lo impone el HUDN, cuyo
medidor arranca el 2025-04-03 a las 20:58 y cuyo inversor lo hace al día
siguiente a las 05:58. Antes de esa fecha la comunidad no está completa y
no hay mercado de cinco que simular.

El cierre no tiene esa justificación. Al censar las 27 fuentes crudas
resulta que **todas ellas contienen datos hasta abril de 2026**:

| Fuente | Último registro |
|---|---|
| Medidores de Udenar, Mariana, UCC y Cesmag | 2026-04-25 |
| Inversores Fronius de Udenar | 2026-04-10 |
| Medidores e inversor del HUDN | 2026-04-11 |
| Inversor MTE de Udenar | 2026-04-24 |

Es decir, hay aproximadamente **cuatro meses de medición sin usar**. El
repositorio no registra por qué el horizonte se detuvo en diciembre; la
constante `T_END` de `data/xm_data_loader.py` lleva el comentario de que
«HUDN + Fronius Udenar caen ~17-Dic», pero el censo no lo confirma: esas
fuentes cubren el \pct{98} del horizonte y siguen registrando después.

**Qué significa y qué no.** No invalida ninguna cifra: el estudio es
correcto sobre el horizonte que declara. Lo que hace es dejar sobre la
mesa una ampliación del orden del \pct{45} en tamaño de muestra, que
además incorporaría un ciclo estacional más completo. Extenderlo obligaría
a repetir la corrida canónica entera y a rehacer toda la verificación
numérica, de modo que no es una tarea menor.

**Acción tomada.** El Capítulo 2 del documento lo declara en un
`trampabox`, distinguiendo el estatuto del inicio (impuesto por el dato)
del estatuto del cierre (corte administrativo), para que el lector no
atribuya al dato una limitación que no tiene.

---

## H-5 · El canon no es autosuficiente para regenerar sus propias figuras

**Estado: abierto; el documento lo rodea, no lo resuelve.**

La entrega canónica acompaña casi todas sus figuras con un `.csv` hermano
que contiene los datos dibujados, de modo que se pueden reconstruir sin
volver a correr nada. Pero no todas: de las **22 figuras** de
`entrega_canonica_2026-08/canonica_m1/graficas/`, **cinco no tienen ningún
sibling de datos**, y sus valores tampoco aparecen en las hojas de los tres
libros de resultados:

| Figura | Qué muestra | Dónde estaría el dato |
|---|---|---|
| `fig10_sensibilidad_ppa` | Barrido del precio del contrato bilateral | no hay hoja SA-PPA |
| `fig11_sensibilidad_pgs` | Barrido de la tarifa minorista | no hay hoja SA3 |
| `fig14_optimalidad_horaria` | Dominancia hora a hora frente al colectivo | falta la serie horaria de C4 |
| `fig16_subperiod` | Cortes por sub-período | no hay hoja de sub-períodos |
| `fig22_convergencia_h0683` | Trayectorias de una hora | sin datos exportados |

Las tres primeras y la quinta son recuperables volviendo a correr el
análisis; la cuarta ya estaba señalada como no reproducible en trabajos
anteriores.

**Consecuencia práctica.** El capítulo 11 pierde dos de sus barridos y el
capítulo 10 pierde la figura de optimalidad horaria, salvo que se acepte
re-correr. Mientras tanto, esas cinco se incorporan al documento **usando el
PNG canónico tal cual**, con una nota en el pie que diga que no se
re-estilizó porque el canon no conserva los datos. Es preferible a
re-correr, que arriesgaría mover cifras ya publicadas.

**Recomendación para futuras corridas.** Que el exportador escriba el
sibling de datos de *todas* las figuras, sin excepción. El coste es
despreciable y es lo que permite auditar sin ejecutar.

---

## H-4 · Los rótulos SC/SS, confirmados por física

**Estado: confirmado y neutralizado en el código del documento.**

`CANON.md` §5bis advierte que las columnas `SC` y `SS` de la hoja `Resumen`
están intercambiadas respecto a su semántica. Queda confirmado por un
argumento independiente del código: en M1 la cobertura de generación sobre
demanda es del 19,1 %, de modo que la fracción de demanda cubierta con
generación propia no puede valer 0,98. El valor 0,1876 rotulado `SC` es
autosuficiencia y el 0,9806 rotulado `SS` es autoconsumo.

`datos.resumen()` los devuelve ya renombrados a `autosuficiencia` y
`autoconsumo`, de modo que ninguna figura del documento pueda heredar el
rótulo equivocado.

---

## H-9 · El precio de bolsa supera al de escasez en doce horas del horizonte

**Estado: verificado. Obliga a replantear la figura del techo antes de
dibujarla.**

Al comprobar un rótulo de la figura de la serie de bolsa apareció que el
máximo del horizonte, 2.224,01 COP/kWh el 15 de agosto de 2025 a las 19:00,
no roza el precio de escasez de ese mes sino que lo multiplica por 2,48. El
de agosto vale 898,02 COP/kWh.

El barrido completo contra el precio de escasez mes a mes da **doce horas
por encima**, el 0,19 % del horizonte, repartidas entre julio y noviembre de
2025 y concentradas en agosto, que aporta cinco. El mayor exceso llega a
1.326 COP/kWh sobre el valor del mes.

**Consecuencia.** El plan preveía una figura que dibujara el precio de
escasez como techo sobre la serie de bolsa. No puede presentarse así,
porque la serie lo atraviesa. El precio de escasez es el que activa las
obligaciones de energía firme, no un límite superior del precio de bolsa, y
la figura tiene que decir eso o no dibujarse. Se resuelve cuando se
construya, que todavía no ha ocurrido.

**Qué no cambia.** Ninguna cifra publicada depende de esto. El horizonte
promedia 182,69 COP/kWh y su mediana es 114,59, de modo que las doce horas
no mueven el agregado. Es un asunto de cómo se rotula, no de cuánto vale.

---

## H-10 · El capítulo de robustez no parte de la cifra del capítulo de resultados

**Estado: causa identificada y documentada en el código. Obliga a declarar
la diferencia allí donde las dos cifras convivan.**

Al auditar las figuras de sensibilidad apareció que el barrido del piso de
precio no pasa por el resultado publicado. Con el valor nominal de 280
COP/kWh el barrido da una ganancia del mercado entre pares de 54,41
millones de pesos en la cobertura del circuito principal, frente a los
53,62 del libro de comparación, y de 38,06 millones en la del circuito
secundario, frente a 34,55. La desviación es del 1,5 % en la primera y del
**10,2 %** en la segunda.

**Lo que descarta que sea un problema de qué punto se mira.** En la
cobertura del circuito principal, el valor del esquema colectivo mensual es
*exactamente constante* a lo largo de todo el barrido, 52 952 520 pesos,
y aun así difiere en un 1,5 % del publicado. Como esa magnitud no depende
del parámetro barrido, el parámetro no puede explicar la diferencia. Se
comprobó además que ningún punto del barrido reproduce el valor publicado.

**Lo que descarta que sea un problema del juego.** El índice de equidad
coincide hasta el sexto decimal en las dos coberturas, y las horas de
mercado y la energía transada coinciden exactamente. La solución del
mercado es el mismo objeto en los dos sitios. Lo que difiere es la
contabilidad monetaria.

**La causa, que está escrita en el código.** El comentario de los
parámetros del caso base lo dice sin ambigüedad: el valor de 280 COP/kWh es
un promedio conservador *para los barridos*, que trabajan con un precio de
compra de la red constante, mientras que la corrida con datos reales emplea
la serie horaria. No es un defecto sino una decisión de método, pero está
enterrada en un comentario y ninguna de las dos capas del documento la
declara.

**Consecuencia para el documento.** Las cifras del capítulo de robustez no
son comparables al peso con las del capítulo de resultados, y si aparecen
juntas hay que decir por qué. Lo que el barrido sí sostiene son las
pendientes y los cruces, es decir, el comportamiento frente al parámetro,
que es para lo que está.

**Un desprendimiento.** El mismo comentario cifra el promedio empírico de
bolsa en unos 222 COP/kWh. No se reproduce: el horizonte promedia 182,69,
los meses de abril a diciembre completos 190,76 y la serie entera 193,60.
El valor nominal de 280 es, por tanto, 1,53 veces la media del horizonte.
Que sea conservador es defendible y está declarado; que la referencia
empírica citada no reproduzca es del mismo tipo que [[H-1]] y conviene
corregirlo en el código.

---

## H-11 · El modelo no representa la energía reactiva, y la regulación sí la cobra

**Estado: CIFRADO (2026-08-23). La tarifa que hacía falta sí estaba: el
cargo va a uso de redes, de modo que el precio aplicable es el de
transmisión más distribución, que el canon tarifario ya trae.**

Al fundamentar por qué el modelo toma la potencia activa y no la reactiva
ni la aparente apareció que la respuesta física, que solo la activa
transfiere energía neta, no agota el asunto económico. La regulación
colombiana factura el consumo reactivo inductivo que supera el cincuenta
por ciento de la energía activa entregada en el mismo periodo horario, y
cobra el exceso como si fuera energía activa dentro de los cargos por uso
de las redes.

**Medido sobre el horizonte, agregando a energía horaria como hace la
regla y no contando instantes**, el exceso aparece en el 15,0 % de las
horas con consumo de la cobertura del circuito principal y en el 65,7 %
de las del circuito secundario. El reparto es muy desigual: el circuito
secundario del Hospital lo presenta en el 99,8 % de sus horas y el de la
Universidad CESMAG en el 80,8 %, mientras que el circuito principal del
Hospital no lo presenta nunca y el de CESMAG en el 0,8 %.

**Consecuencia.** La factura que sirve de referencia está subestimada. No
se puede cifrar cuánto con lo que hay, porque la tarifa del reactivo no
está entre las que se recuperaron de las facturas.

**Lo que conviene no dar por supuesto.** El cargo recae sobre el uso de
las redes, y en este modelo el mercado entre pares está exento de esos
cargos mientras que los demás mecanismos los pagan. Eso hace pensar que
incluirlo ensancharía el margen del mercado entre pares, pero no se ha
comprobado y no debe afirmarse: la exención se aplica a la energía
transada entre pares, no al consumo remanente de cada institución, que
sigue viniendo de la red. Queda abierto.

---

## H-12 · La lectura del lado continuo del inversor no describe el arreglo completo

**Estado: medido sobre los siete inversores. No afecta a ningún resultado,
porque el modelo nunca usó esa lectura, pero cierra la pregunta de por qué
no la usa.**

Al catalogar las variables apareció que la potencia del lado de corriente
alterna **supera a la del lado de corriente continua en el 100 % de las
lecturas** de cinco de los siete equipos, con una razón mediana de 1,82.
En el sexto y el séptimo, los dos primeros inversores de Udenar, no hay
muestras que cumplan los filtros mínimos.

**No es un error de escala del registro.** La potencia continua coincide
exactamente con el producto de la tensión por la corriente continuas, con
razón 1,000 en los cinco equipos, de modo que el trío del lado continuo es
internamente coherente.

**La explicación que queda.** Un inversor no puede entregar más de lo que
recibe, así que la lectura continua no cubre el arreglo completo sino una
de las entradas del equipo. Las tres variables del lado continuo sirven
para diagnosticar una cadena de módulos y no para medir cuánto genera la
institución. La razón se mantiene entre 1,78 y 1,83 en las cinco, lo que
sugiere un reparto estable entre entradas y no un fallo intermitente.

**Consecuencia.** Refuerza la elección de la potencia del lado alterno,
que hasta ahora se sostenía solo en el argumento de que es lo que la
institución puede vender. Cualquier trabajo que quiera usar el lado
continuo tiene que resolver antes esta discrepancia.

---

## H-13 · Ocho de las cincuenta y cuatro variables del medidor no varían nunca

**Estado: medido sobre los veinte medidores. Sin consecuencia para los
resultados; importa para quien quiera extender el trabajo.**

Cinco variables son constantes en los veinte equipos y en todo el
horizonte: el estado de salida y los cuatro registros de energía reactiva,
positiva y negativa, en sus palabras baja y alta. Otras tres son la palabra
alta de registros de dos palabras que nunca llegan a desbordar, de modo que
también valen siempre cero.

**Lo que esto cierra.** El catálogo contiene registros que parecen permitir
leer la energía acumulada sin integrar la potencia, que es lo primero que
preguntaría un revisor. Los de energía reactiva están muertos, y la
variable llamada acumulada recorre el mismo rango que la potencia
instantánea, es decir, no se comporta como un contador.

> **Corregido el 2026-08-26.** La última frase de esta entrada decía que
> integrar la potencia era «la única vía disponible». Eso vale para la
> reactiva y **no** para la activa. Los registros de energía activa
> importada y exportada **sí están vivos**: la palabra baja varía en los
> diez medidores que el modelo emplea, la alta desborda en cuatro de ellos
> y en uno la de exportación también, y componen como alta por diez mil más
> baja, en kilovatios hora. Se comportan como un contador de verdad. Se
> usan en el Capítulo~3 como referencia independiente para contrastar el
> promedio horario, y el contraste sale limpio. Integrar la potencia sigue
> siendo lo correcto, pero por otras dos razones: el contador es entero, con
> lo que su resolución de 1 kWh es peor que la de la potencia sobre una hora
> de unos 19 kWh, y en cinco medidores está mal escalado (ver H-16).

---

## H-14 · Hay cinco estaciones meteorológicas, no cuatro

**Estado: corregido en el documento.**

El censo de fuentes recorría una ruta de cuatro niveles y la estación de
Udenar cuelga un nivel más arriba, sin la carpeta intermedia de equipo que
tienen las otras cuatro. El recuento la perdía. Son cinco, una por
institución. Ninguna se emplea, de modo que no afecta a ningún resultado,
pero la afirmación estaba mal.

### Cierre de H-11 · el cargo, cifrado

La objeción que dejaba abierto este hallazgo era que no se podía cifrar
porque faltaba la tarifa del reactivo. Era un error de planteamiento: la
norma no cobra el exceso a una tarifa propia, lo cobra **como si fuera
energía activa dentro de los cargos por uso de las redes**, de modo que el
precio aplicable es el de transmisión más distribución, que el canon
tarifario trae mes a mes. Promedia 213 COP/kWh sobre el horizonte en el
nivel de tensión que el trabajo supone.

El exceso acumulado vale 8.851 kvarh en el circuito principal y 5.730 en
el secundario, lo que da **1.877.304 y 1.215.258 pesos**.

**La cifra que obliga a declararlo.** En el circuito principal ese cargo
supera al margen que separa a los dos mecanismos mejor situados, que vale
1.426.142 pesos. La razón es de 1,32.

**Lo que no cambia.** El ordenamiento. Es un cargo por uso de redes que
todos los mecanismos pagan sobre el mismo consumo, de modo que en primera
aproximación desplaza a todos por igual.

**Lo que queda abierto, y no debe darse por resuelto.** La norma compara el
reactivo contra la energía activa *entregada al usuario*. Un mecanismo que
cambie cuánta energía activa llega desde la red cambia esa razón y por
tanto el cargo. Cuantificar ese segundo orden exige modelar el reactivo.

**Un desprendimiento sobre el reparto.** El exceso no está repartido y no
lo aporta la misma institución en las dos fronteras: en el principal lo
concentra la Universidad Mariana con el 67 %, y en el secundario la
Universidad CESMAG con el 62 %. Y no es episódico: el Hospital, en el
circuito secundario, se mantiene por encima del umbral en el 99,8 % de sus
horas, con una razón plana a cualquier hora y en cualquier mes.

---

## H-15 · El 40 % del reactivo facturable nace donde no hay consumo activo

**Estado: medido. No cambia ninguna cifra publicada; cambia cómo se lee la
tabla y refuerza el argumento.**

La regulación cobra el reactivo inductivo cuando supera la mitad de la
activa entregada en el periodo horario **y también cuando se registra en
ausencia de consumo activo**. La segunda mitad de la regla pesa mucho más
de lo que parece en esta comunidad.

En el circuito principal, 3.495 de los 8.851 kvarh en exceso, es decir el
40 %, se registran en horas que no tienen consumo activo apreciable. La
mayoría son horas de Udenar exportando: su medidor lee negativo el 25,2 %
del horizonte, hasta −33,6 kW, y en esas horas la instalación sigue
tomando reactiva de la red aunque entregue activa.

**Por qué importa.** Es un caso en que generar más empeora la posición
frente a la norma. La generación fotovoltaica descuenta consumo activo sin
descontar demanda de reactiva, de modo que empuja la razón hacia arriba y,
cuando la activa llega a cero, deja el reactivo entero como facturable. La
comunidad que este trabajo estudia es precisamente una que genera.

**Lo que no se afirma.** Que el mercado entre pares agrave o alivie eso.
Depende de cómo redistribuya la energía activa entre las fronteras, y
cuantificarlo exige modelar el reactivo. Queda abierto, como en [[H-11]].

**Cuidado al leer la tabla del capítulo 2.** La fracción de horas en
exceso se calcula sobre las horas con consumo apreciable; la energía y el
cargo, sobre todas. No son la misma población y la tabla lo declara.

### Cierre parcial de H-15 · el precio de generar, cifrado

La pregunta de si estas series son las crudas o las procesadas permitió
medir lo que este hallazgo enunciaba. La reactiva no tiene versión
procesada, porque el pipeline solo lee potencia activa. Pero la activa sí,
y comparar contra una u otra responde a preguntas distintas.

Contra la lectura del medidor, que es lo que factura el comercializador,
las horas en exceso del circuito principal valen 6,3 % en Udenar, 62,7 %
en Mariana y 4,9 % en la UCC. Contra la demanda reconstruida, es decir
contra lo que el edificio consume de verdad, bajan a 3,0 %, 49,1 % y
0,2 %. El Hospital y la Universidad CESMAG no se mueven, porque sus
medidores no descuentan generación.

**La diferencia es el precio de generar.** Las tres instituciones cuyo
medidor resta la generación propia incumplen entre el doble y veinticinco
veces más de lo que incumplirían por su consumo real. El fotovoltaico no
aumenta la demanda de reactiva; reduce la activa contra la que se compara.

**Lo que sigue abierto.** Cuánto de esto mueve cada mecanismo de mercado.
El mercado entre pares redistribuye energía activa entre fronteras y por
tanto altera esas razones, pero medirlo exige llevar el reactivo al
modelo, cosa que este trabajo no hace.

### Cierre definitivo del segundo orden de H-11 y H-15

Lo que estos dos hallazgos dejaban abierto era si el mecanismo de mercado
puede alterar el cargo por reactivo lo bastante para cambiar el
ordenamiento. Ya está medido y la respuesta es que no.

El mercado entre pares reduce la energía activa que cada comprador toma de
la red. Como el umbral de la norma es la mitad de esa energía, el umbral
baja y una parte mayor del reactivo pasa a facturarse. Calculado **por
usuario**, que es como aplica la norma, el cargo sube de 1.877.304 a
1.974.776 pesos en el circuito principal y de 1.215.258 a 1.275.040 en el
secundario. La diferencia vale 97.471 y 59.782 pesos.

Frente al margen que separa al mercado del colectivo mensual, eso es el
6,8 % en el circuito principal y el 1,3 % de la brecha en el secundario.
**Estrecha la ventaja y no la invierte.**

**El nivel de agregación importa y por poco lo erro.** Calculado sobre el
agregado de la comunidad en vez de por usuario, el cargo base sale de
303.654 pesos en lugar de 1.877.304, porque el exceso de una institución
se compensa con el consumo activo de otra. La norma se aplica por usuario,
de modo que el agregado no vale.

**Consecuencia para el documento.** La decisión de trabajar solo con
energía activa queda sostenida por cuatro razones de principio y por esta
medida de que la omisión no compromete la comparación. Ver C-34.

---

## H-16 · Cinco medidores tienen la potencia y el contador de energía a escalas distintas, y el inventario predice cuál

**Estado: medido y corroborado por dos fuentes independientes. Afecta a
P-6, que hasta hoy estaba planteado sin cuantificar. No cambia ninguna
cifra publicada, pero acota la duda que P-6 dejaba abierta.**

Al contrastar el promedio horario contra el contador de energía del propio
medidor (ver H-13 corregido), cuatro medidores cuadran al 0,05 % y cinco no
cuadran en absoluto. La discrepancia no es ruido: **es un factor de escala
limpio, y el inventario de instalación lo predice**.

El inventario trae dos columnas que hasta ahora no se habían usado, el
transformador de corriente instalado y el verificado. Su cociente predice
el desajuste medido:

| Institución | Medidor | Instalado (A) | Verificado (A) | Razón predicha | Razón medida |
|---|---|---:|---:|---:|---:|
| Udenar | M1 | 400 | 400 | 1,0 | **1,00** |
| UCC | M1 | 400 | 400 | 1,0 | **1,00** |
| UCC | M3 | 100 | 100 | 1,0 | **1,00** |
| HUDN | M1 | 200 | 200 | 1,0 | **1,00** |
| Mariana | M1 | 400 | 10 | 40,0 | **39,51** |
| HUDN | M3 | 400 | 10 | 40,0 | **38,61** |
| Cesmag | M1 | 800 | 10 | 80,0 | **78,45** |
| Cesmag | M3 | 800 | 10 | 80,0 | **78,48** |

Nueve de diez medidores. (Udenar M3 mide 1,49 frente a 1,0 predicho, pero
su contador solo acumula 4.167 kWh y la cuantización entera domina;
Mariana M3 acumula 51 kWh y no es interpretable.) Donde el transformador
instalado coincide con el verificado, los dos canales cuadran; donde no
coincide, **se separan justo por ese cociente**, y en Cesmag el valor es
idéntico en sus dos medidores, que es lo que cabe esperar de una misma
instalación.

**La dirección.** La columna de potencia lleva la corrección del
transformador y el contador interno no. Lo respalda la magnitud: el
contador de Cesmag daría 332 kWh en ocho meses para el circuito principal
de un campus, es decir 1,4 kWh al día, que es imposible; la potencia da
unos 107 kWh al día, que es plausible. El canal que el pipeline usa es, por
tanto, el bueno.

**Lo que esto NO cierra.** Que la potencia sea el canal correcto en
términos relativos no prueba que su escala absoluta lo sea. Si el
transformador instalado no fuera el que el inventario declara, la potencia
arrastraría ese error y el contraste seguiría cuadrando igual, porque las
dos fuentes de este hallazgo son la misma instalación. Cerrar P-6 del todo
exige una comprobación en campo.

**Cómo reproducirlo.** Componer la energía neta como
`(importada_alta - exportada_alta) * 10000 + (importada_baja - exportada_baja)`,
leerla **en las marcas de hora en punto** (no del primer al último instante
de la hora, que son 58 minutos y sesgan el resultado un 3 %), y comparar su
diferencia con la media horaria de la potencia activa.

---

## H-17 · Los siete inversores comparten clase de potencia y trabajan pegados a su tope

**Estado: medido. No se usa en el capítulo 3 y no cambia ninguna cifra. Se
anota porque pertenece al asunto del recorte solar, no al de la unidad.**

Los máximos de los siete inversores sobre el horizonte caen todos en la
banda 15.144 a 15.180 (W): Udenar 15.155, 15.157 y 15.154; Mariana 15.180;
UCC 15.166; HUDN 15.144; CESMAG 15.151. Una dispersión del 0,24 % entre
siete equipos de cinco instituciones distintas no es casualidad: apunta a
que las siete máquinas son de la misma clase y alcanzan su tope.

**Lo que NO está verificado.** Que sean «de 15 kW» nominales. No se ha
contrastado contra ficha técnica ni contra el inventario de instalación.
Solo está medido el rango de los máximos observados.

**Dónde importaría.** Si las siete trabajan contra su tope, parte de la
generación disponible se estaría recortando en el propio inversor, antes de
que ningún medidor la vea. Eso afectaría a la lectura de la generación como
recurso, no a su medición. Es materia del capítulo del instrumento.

---

## H-18 · Qué se hace con las horas parcialmente muestreadas, y por qué

**Estado: medido. La decisión que el pipeline toma es la correcta, y hasta
hoy no estaba declarada en ninguna parte. Tres revisores independientes
tienen el dictamen pendiente.**

Nace de una reunión con el asesor (transcripción del 28 de agosto de 2026,
`Modulo Blockchain Transaccion/Whisper/`). Al describir cómo pasar de las
muestras de dos minutos a la energía horaria, él distingue dos métodos y
llama exacto al segundo:

> «tenemos la media de la hora... **esa es la forma simple** de hacerlo»
> ... «**que es aproximado, pero no es exacto**»
>
> «cada dato de potencia **multiplicarlo por el delta t**... es una
> sumatoria de la potencia por lo que valen dos minutos en horas... y eso
> te da **ahí sí** la integral»

**Los dos métodos son el mismo número, y la distinción no existe.** En una
hora completa, `suma(P) por 2/60` y `(1/30) por suma(P)` son la misma
expresión. Medida sobre las 5.810 horas completas del medidor principal de
la UCC, la diferencia máxima es **1,4e-14 kWh**, que es el último bit de la
coma flotante.

**Pero su inquietud apuntaba a algo real, situado en otro sitio.** Los dos
métodos sí divergen en las **horas incompletas**, que él no mencionó. Su
fórmula fija el ancho en dos minutos y suma solo las muestras que hay, de
modo que una hora con veinte muestras aporta cuarenta minutos de energía.
La media reparte lo observado sobre la hora entera.

| Institución | Horas con dato | Incompletas | Media (A) | Suma fija (B) | B menos A |
|---|---:|---:|---:|---:|---:|
| Udenar | 6.048 | 164 | 10.611,1 | 10.557,6 | −0,504 % |
| Mariana | 6.031 | 125 | 46.299,2 | 46.179,7 | −0,258 % |
| UCC | 6.019 | 198 | 116.248,4 | 115.685,7 | −0,484 % |
| HUDN | 6.032 | 163 | 54.744,1 | 54.544,1 | −0,365 % |
| CESMAG | 6.028 | 190 | 27.077,6 | 26.928,7 | −0,550 % |

Son **840 horas** en total, entre el 2 % y el 3 % del horizonte de cada
medidor.

**El contador del propio equipo arbitra, y le da la razón a la media.**
Restringido a horas parciales y a los tres medidores cuyo contador está
bien escalado (ver H-16):

| | Horas parciales | Sesgo de la media | Sesgo de la suma fija |
|---|---:|---:|---:|
| UCC | 148 | **+0,065 kWh** | −1,738 kWh |
| Udenar | 69 | **−0,117 kWh** | −0,454 kWh |
| HUDN | 122 | **−0,009 kWh** | −0,490 kWh |

En la UCC el contador registra 3.241 kWh en esas horas, la media da 3.251 y
la suma fija 2.984: el método del asesor **subestimaría esas horas en un
8 % de su energía**, y en las tres instituciones su error medio es del
orden del triple.

**Una cuadratura mejor existe y tampoco ayuda.** Se midió la regla del
trapecio, que cierra cada hora con la primera muestra de la siguiente en
vez de ignorarla. Frente al contador: gana en la UCC por 0,002 puntos
porcentuales (−0,0392 % contra −0,0415 %), **pierde en Udenar** (−0,2009 %
contra −0,1972 %) y empata en el HUDN. No hay mejora sistemática. El
residuo que queda lo pone **la resolución entera del contador**, de 1 kWh
sobre horas de unos 19, no la regla de cuadratura.

**Una arruga en la ecuación del Capítulo 3.** El documento escribe la
aproximación con `delta = dt/N` y la glosa diciendo que cada muestra vale
por el intervalo que representa. En hora completa `delta` vale dos minutos
y la glosa es literal. En hora incompleta `delta` sale mayor que dos
minutos y la muestra sigue representando dos, de modo que la glosa se
estira. La ecuación sigue siendo el estimador correcto; lo que no es
literal es su lectura física cuando la hora no está llena.

**DICTAMEN DE TRES REVISORES INDEPENDIENTES (2026-08-31).** Cerrado. La
decisión es correcta, pero cuatro cosas de arriba estaban mal dichas.

**1. Son 835 horas, no 840.** La hora sobrante es la misma en las cinco: el
cargador recorta con un corte inclusivo por los dos extremos, de modo que
la única muestra de las 00:00 del 16 de diciembre crea un contenedor con
una sola muestra. El reindexado posterior lo descarta y **nunca llega al
modelo**. Verificado.

**2. La primera conclusión es álgebra, no medición.** Que la media y la
suma ponderada coincidan no es un resultado empírico: media = suma entre
30, y suma por 2/60 = suma entre 30, son la misma expresión. El 1,4e-14 es
ruido de coma flotante y no debe presentarse como si midiera algo.

**3. La columna de sesgo de la media era ruido con tres decimales.** Con el
error típico del contador, el +0,065 kWh de la UCC no se distingue de cero
(p = 0,238) y el −0,009 del HUDN tampoco (p = 0,839). Lo que sí resiste es
la **comparación**, porque el error del contador se cancela al restar: la
diferencia entre los dos métodos da t = 7,4 / 8,4 / 11,4 y la media gana en
el 71 al 73 % de las horas, con Wilcoxon por debajo de 4e-5. Publíquese la
tasa de acierto o el error cuadrático, nunca el sesgo.

**4. El contraste del contador solo juzgaba el tercio fácil.** Cubre entre
el 31 % y el 48 % de la diferencia entre los dos métodos, y justo donde
apenas difieren: las horas juzgadas tienen 28 muestras de 30, las no
juzgadas 19 a 22.

**LA PRUEBA QUE SÍ CARGA EL PESO**, verificada por mí después de que la
propusiera el revisor hostil. Para cada corte de telemetría se compara
cuánto avanzó el contador interno contra dos hipótesis:

| | Cortes | Contador | Siguió consumiendo | No hubo energía |
|---|---:|---:|---:|---:|
| UCC | 262 | 580 kWh | 603 (0,96×) | 205 (**2,82×**) |
| Udenar | 362 | 108 kWh | 93 (1,17×) | 36 (**2,97×**) |
| HUDN | 152 | 121 kWh | 117 (1,03×) | 47 (**2,60×**) |
| **Total** | **718** | **809 kWh** | **812 (1,00×)** | **288 (2,81×)** |

Y empeora monótonamente con la duración del corte: la razón contra el
relleno con ceros va de 1,99 con una muestra ausente a 25,7 con dieciséis o
más. **El equipo sigue integrando durante los cortes**, de modo que
atribuirles energía nula falla por física, no por estadística. Esta prueba
no depende de marcas de reloj ni de filtros, y cubre el régimen que el
contraste horario no veía.

**LAS HORAS INCOMPLETAS SÍ ESTÁN SESGADAS, PERO EL ESTIMADOR NO.** Es la
distinción que salva la decisión:

- *Sesgada la cobertura*: la tasa de horas incompletas es 3,78 % entre las
  8 y las 17 contra 1,74 % de madrugada, razón 2,17 con p = 5e-16; en
  diciembre sube al 7,44 %; y hay **18 horas con las cinco instituciones
  incompletas a la vez contra 0,00 esperadas** bajo independencia, lo que
  apunta a la plataforma de adquisición y no al equipo.
- *No sesgado el estimador*: aplicando la ventana observada de cada hora
  incompleta a horas completas comparables de la misma institución, hora
  del día y mes, el sesgo es indistinguible de cero en las cinco y suma
  **+0,0007 %** de la demanda del horizonte. El desnivel es una propiedad
  de **qué horas fallan**, no de **cómo se estiman**.

Decir «los faltantes son aleatorios» sería falso y un revisor lo
desmontaría en una tarde.

**LA LIMPIEZA NO CORRIGE NINGUNA.** De las 835, cero marcadas como atípicas
y cero imputadas. No hay red de seguridad aguas abajo: lo que decide esta
etapa es lo que ve el modelo.

**EL MARGEN DEL MERCADO AGUANTA.** La elasticidad del volumen transado a la
demanda es de −0,6, de modo que medio punto de demanda mueve el margen unos
3.600 COP sobre 1.154.118. Aun aplicando 5 % solo a las 835 horas, el
movimiento es de unos 1.600 COP. Tres órdenes de magnitud de holgura.

**EL TRAPECIO, BIEN ENCUADRADO.** Decir que «no mejora» era impreciso: sí
reduce el error horario de forma estadísticamente sólida (2,3 % en la UCC
con p = 1e-9), pero la magnitud es de 0,01 kWh sobre horas de 9 a 19, es
decir, irrelevante. Y hay un error de encuadre propio: tal como estaba
codificado, el trapecio en horas parciales **es el método del asesor con
una corrección de borde**, hereda el relleno con ceros y por tanto nunca
fue candidato a resolver la cuestión.

**LA NORMA, Y SU LÍMITE.** El artículo 38 de la Resolución CREG 038 de 2014
se titula «Estimación de lecturas» y ordena estimarlas «integrando la
medida de potencia activa» o por curvas típicas; **el cero no figura entre
los métodos admisibles**. Pero **no nos obliga, y conviene no citarlo como
si lo hiciera**: su texto lo activa «mientras se reparan o reponen los
elementos de los sistemas de medición que se encuentran en falla o hayan
sido hurtados», y sus métodos se aplican «para el caso de las fronteras con
reporte al ASIC». Nuestros equipos no son fronteras comerciales sino
instrumentación de investigación, y lo que hay no es un sistema en falla
sino un corte de telemetría en un equipo que siguió integrando, cosa que la
tabla de arriba prueba. Vale como **criterio del regulador por analogía**,
que es como lo cita el capítulo. Coinciden el operador de Ontario, donde un intervalo en cero
dispara una alarma de validación, el mercado australiano y la guía ASHRAE
14. En cambio **IEC 61000-4-30 no cubre el caso**: su marcado es para
eventos y la Clase A exige medición sin huecos, de modo que no debe
citarse. Ninguna norma eléctrica fija umbral de completitud; si se quiere
uno, se declara como decisión propia. Ver P-20.

---

## H-19 · El capítulo publicaba el complemento como si fuera lo que el modelo emplea

**2026-09-01 · destapado al replantear la figura del horizonte · corregido**

El resumen del Capítulo 2 decía «la base empírica la forman 27 fuentes
instrumentadas, de las cuales el modelo emplea 13». Contado sobre el
censo, **13 es exactamente el complemento de lo que la frase quiere
decir**:

| | Medidores | Inversores | Total |
|---|---|---|---|
| Instrumentadas | 20 | 7 | **27** |
| Esenciales, es decir, sin las cuales la comunidad no está completa | 9 | 5 | **14** |
| Que el modelo lee, contando la reconstrucción | 9 | 7 | **16** |
| Sin uso alguno | 11 | 0 | **11** |

Los nueve medidores son uno por institución en cada frontera salvo en
Mariana, donde un solo equipo sirve a las dos, que es lo que hace que sean
nueve y no diez. El complemento de los 14 esenciales son 13, once
medidores auxiliares y los dos inversores que Udenar aporta solo a la
reconstrucción, y esa es la cifra que se había publicado.

Se corrige a **16**, que es la que corresponde al verbo «emplea», porque
los dos inversores de reconstrucción sí se leen aunque no entren en la
matriz de generación. El aviso apartado del mismo capítulo arrastraba el
mismo error en su forma parcial, «8 participan y 12 quedan como
auxiliares», y se corrige a 9 y 11 aunque hoy no se imprima: está dentro
de un entorno `guardado`, que es «lo que puede volver», y volvería con el
error dentro.

**Por qué no se vio antes.** La cifra era coherente consigo misma y con
nada más. La figura de cobertura ya imprimía nueve barras en color y once
en gris, de modo que la figura contradecía al texto desde el principio.

---

## H-20 · El horizonte empieza seis horas antes que su última fuente

**2026-09-01 · abierto · señalado por los dos revisores de forma independiente**

La constante de inicio del horizonte es el 4 de abril de 2025 a las 00:00
y el primer registro del inversor del HUDN es ese mismo día a las
**05:58:04**. Las primeras cinco horas y cincuenta y ocho minutos del
horizonte no tienen registro de generación de esa institución.

**El efecto sobre las cifras es previsiblemente inmaterial**, porque son
horas de noche y el equipo mide generación fotovoltaica, que a esa hora es
nula. Lo que no resistía es la redacción: el capítulo decía «el 4 de abril
como primer día completo con las cinco instituciones operativas», y la
figura del horizonte, diez centímetros más arriba, imprimía la hora que lo
desmentía. Se reescribió a «primer día del horizonte, el primero en que
las cinco instituciones tienen registro en sus medidores y en su
inversor», que es lo que hay, y la hora pasó al cuerpo del texto cuando
esa figura se retiró por C-75.

Queda abierto lo que la reescritura no resuelve: **si esas seis horas se
imputan o se dejan como hueco**, y si la etapa de limpieza las trata como
tales. Se cruza con P-21, porque cualquier decisión aquí toca el mismo
punto del cargador.

---

## H-21 · Las dos «excepciones» de cobertura no eran fallos, eran arranques tardíos

**2026-09-01 · destapado al replantear la figura de cobertura · corregido**

El censo calcula la cobertura sobre las \num{6144} horas del horizonte
completo (`cache_fuentes.py`, el índice se construye entre `T_START` y
`T_END`). En consecuencia, **cualquier equipo que entra en servicio
después del inicio del horizonte acumula como dato faltante las horas en
que todavía no existía**, y la figura lo presentaba como un defecto de
adquisición.

| Fuente | Sobre el horizonte | Horas previas | Sobre su servicio |
|---|---|---|---|
| Udenar · Medidor 4 | 88,7 % | 623 h | **98,7 %** |
| Udenar · Inversor MTE | 39,3 % de sol | 1.989 h de sol | **97,7 %** |

Medidas sobre el periodo en servicio, **las 27 fuentes caen entre el
96,7 % y el 98,8 % y no queda ninguna excepción que acotar**. Lo que el
capítulo llamaba «una racha larga de ausencia» en el Medidor 4 de Udenar
era la instalación del equipo el 29 de abril, 25 días después de que
empezara el horizonte.

**Consecuencia para el Capítulo 3.** La magnitud que importa para la
imputación son las horas que de verdad faltan, y son pocas: de 31 a 204
según la fuente, y como mucho 126 en los equipos que el modelo emplea. Las
\num{1989} horas del Inversor MTE **no se imputan**, porque no son huecos;
esa fuente sencillamente no participa antes de septiembre.

**Por qué no se vio antes.** La cifra del 88,7 % era correcta como
cobertura sobre el horizonte; lo que estaba mal era la causa que se le
atribuía. Es el mismo patrón de H-19: un número bien calculado y mal
interpretado.

---

## H-22 · El umbral de cobertura reintroduciría el cero que el capítulo rechaza

**2026-09-01 · abierto · destapado al explicar P-21**

P-21 propone marcar como ausente la hora que trae menos de 23 de sus 30
muestras, para que la etapa de limpieza la impute como hueco en vez de
estimarla con la media de lo observado. La idea es buena y el cambio de
estimador es defendible: la limpieza estima desde las horas vecinas, y eso
encaja mejor con el artículo 31 de la Resolución CREG 108 de 1997, que
habla de consumos promedios de **otros períodos** del mismo usuario, que la
media dentro de la propia hora.

**Lo que no se había visto es dónde caen esas horas.** Anularlas las pega a
los huecos que ya existen y alarga la racha. Medido sobre los cinco
medidores de la frontera principal, de las 147 horas afectadas:

| Cómo las recogería la limpieza | Horas |
|---|---:|
| Interpolación, racha de hasta 3 h | 77 |
| Arrastre del valor vecino, hasta 24 h | 63 |
| **Relleno con cero, racha de más de 24 h** | **7** |

La racha mayor llega a 52 h en la UCC y a 43 h en las otras cuatro.

**Siete horas acabarían en cero**, que es exactamente lo que la subsección
del archivo a la serie horaria argumenta que no debe hacerse, con la prueba
del contador detrás, y lo que el criterio del regulador excluye. El umbral,
tal como está escrito, se contradiría a sí mismo.

**La corrección.** El umbral debe entregar la hora a un estimador mejor y
nunca a uno peor. La condición para anularla no es solo que tenga menos de
23 muestras, sino además que la etapa de limpieza vaya a estimarla de
verdad, es decir, que no quede dentro de una racha que supere el alcance
del arrastre. En las horas que sí lo superen se conserva la media, que es
la decisión que el capítulo ya sostiene.

**No urge.** P-21 sigue esperando a la próxima corrida canónica, y esto
solo cambia la línea que habrá que escribir cuando llegue.


---

## H-23 · La generación que el modelo negocia para Udenar es un Fronius, no el inversor del proyecto

**2026-09-03 · CERRADO el mismo día por C-90 (CAL-44) · pendiente solo de la corrida**

`EMS_INVERTER_CONFIG` designa para Udenar `Fronius Inverter 1`. Es decir, la
serie $G$ que el modelo compra y vende para Udenar sobre las 6.144 horas
(13,2 MWh) es la de un Fronius, no la del inversor del MTE (6,5 MWh en sus
1.409 horas). Él ha dicho que los Fronius **no deben usarse para ningún
cálculo**, solo como referencia para reconstruir el del MTE.

**Dos huecos, no uno.**

1. El inversor que el modelo negocia es el equivocado según ese criterio.
2. **La reconstrucción del inversor del MTE a partir de los Fronius no
   existe en el código.** No hay tal función; el pipeline solo suma
   (`_sum_inverter_reconstruction`) y designa (`EMS_INVERTER_CONFIG`).
   Cubrir el 77,1 % del horizonte que le falta exige escribirla.

**Alcance.** Cambiar $G$ de Udenar mueve toda la cifra publicada: Udenar es
el mayor vendedor en M1. Invalida el canon y exige corrida nueva. No se
toca nada hasta que él decida.

**Lo que arrastra el documento.** Dos pasajes describen fielmente el código
y quedarían al revés si se cambia la designación:

- Capítulo 2, el censo de fuentes: «de los 7 inversores, 5 definen la
  generación que ve el modelo y los otros 2 intervienen solo en la
  reconstrucción de la demanda de Udenar».
- Capítulo 2, el arranque del horizonte: «quedan fuera de la cuenta los dos
  inversores que Udenar aporta solo a la reconstrucción de su demanda,
  porque uno de ellos empieza a registrar en septiembre». Ese es justamente
  el del proyecto.

Ninguno se toca todavía: hoy dicen la verdad sobre el código. Si él decide
el cambio, ambos se reescriben y el arranque del horizonte hay que
recalcularlo, porque el inversor del proyecto pasaría a ser fuente esencial
y su primera fecha es el 3 de septiembre, no el 4 de abril.

### Ampliación 2026-09-03 · auditoría completa del pipeline, punta a punta

Él describió lo que creía que hacía el código: inversor del MTE donde
está disponible, y antes de esa fecha un Fronius de curva parecida que lo
extienda hacia atrás; nunca los tres a la vez. **No es lo que hace.** Se
recorrió `build_demand_generation` entero y `xm_data_loader`, que es
pasarela pura sin escalamiento.

**Lo que hace hoy, en dos lugares distintos:**

1. **La generación que el modelo negocia.** `G = _clean(G_ems)`, y `G_ems`
   es un solo inversor: para Udenar, el Fronius 1, sobre las 6.144 horas,
   13,2 MWh. El inversor del proyecto **no entra en ningún cálculo**.
2. **La reconstrucción de la demanda.** `_sum_inverter_reconstruction` suma
   los tres en todo instante, rellenando con cero fuera de la ventana de
   cada uno. Desde el 3 de septiembre suma 3,82 + 3,78 + 4,60 = 12,2 kW de
   media donde él quiere 4,60.

**El empalme que él describe no existe en ninguna parte del repositorio.**

**La reconstrucción que pide está bien fundada.** En las 1.409 horas de
solape, el inversor del proyecto correlaciona r = 0,997 con cualquiera de
los dos Fronius, con perfil diario de idéntica forma y razón de energía
1,205 frente al Fronius 1. Reconstruido así, el inversor del proyecto da
15,9 MWh sobre el horizonte completo, frente a los 13,2 MWh que el modelo
usa hoy.

**Pero son dos preguntas distintas y solo una tiene esa respuesta.**

| | h con demanda < 0 | kWh recortados | Demanda bruta de Udenar |
|---|---:|---:|---:|
| Los tres a la vez (hoy) | 353 | 1.013,3 | 44,3 MWh |
| Un solo inversor reconstruido | **957** | **5.517,6** | **32,1 MWh** |

Deshacer el neteo exige devolver **lo que el medidor restó**, sea de quien
sea el panel. Con un solo inversor quedan 957 horas en que el medidor
exportó más de lo que ese inversor generó, lo que no es posible si no hay
más generación detrás. La demanda bruta de Udenar cambiaría un 27,5 %.

**Conclusión operativa.** El punto 1 es suyo sin discusión: la generación
negociada debe ser el inversor del proyecto reconstruido, no un Fronius. El
punto 2 es una pregunta física sobre qué hay detrás del Medidor 1 (circuito
principal, subestación), y el dato dice que hay más de un inversor. Pendiente
de su palabra antes de tocar nada.


**CIERRE.** Él decidió el 2026-09-03: inversor del proyecto donde registra,
Fronius escalado antes, un solo inversor en todo instante. Aplicado en
`data/preprocessing.py` como CAL-44 y verificado end to end. La
reconstrucción de la demanda se mantiene con los tres, por lo medido arriba.
Queda pendiente únicamente la corrida canónica, que va con P-17, P-21 y H-20.

---

## H-24 · El recorte no «elimina» energia de la serie: la anade

**2026-09-04 · abierto · decision suya, afecta al argumento del sesgo**

Al separar la cuenta de la figura aparece una imprecision de signo que el
capitulo repite en tres sitios.

**La aritmetica.** Sin recorte, la serie sumaria
`D_raw + G_recon` = 10.605,83 + 32.691,41 = **43.297,24 kWh**. Con recorte
suma **44.310,54**. El recorte, por tanto, **anade 1.013,30 kWh** al total;
no los quita.

**Lo que el capitulo dice.** «El recorte lleva a cero la diferencia,
eliminando energia de la serie de demanda»; «lo que eso elimina de la serie
de demanda queda acotado»; y en la lista del sesgo, «el recorte de la
reconstruccion elimina 1.013,3 kWh de la demanda de Udenar».

**Que es realmente 1.013,3 kWh.** La magnitud total de las excursiones
negativas, es decir, cuanto se quedo corta la generacion devuelta frente a
lo que el medidor habia restado. No es la demanda que se pierde: la demanda
verdadera de esas 353 horas es positiva y desconocida, y lo que se registra
en su lugar es cero.

**La direccion del sesgo NO cambia.** Registrar cero donde hubo consumo
subestima la demanda de Udenar en horas solares, de modo que el argumento
de que el sesgo es restrictivo se sostiene. Lo que no se sostiene es
atribuir a esa subestimacion la cifra de 1.013,3 kWh, que mide otra cosa.

**Por que no se corrige de oficio.** Toca el primer punto de la lista de
decisiones que sesgan en contra, que es un argumento central del capitulo,
y la redaccion correcta depende de que se quiera afirmar. Pendiente de su
palabra.

---

## H-26 · Mariana entra en M3 como neta y en M1 como bruta: las dos fronteras miden cosas distintas para la misma institución

**2026-09-04 · confirmado en el código y medido · pendiente de decisión, invalida el canon**

Apareció al preparar la comparación M1 frente a M3 de la figura de los
perfiles. El perfil normalizado de Mariana, que debería ser idéntico en
las dos fronteras porque su serie secundaria es la principal multiplicada
por un factor, correlaciona **0,21**.

**Lo que ocurre.** Mariana tiene un solo medidor y es **neto**: por eso la
configuración de la frontera principal lo declara `net_partial` y le
aplica reconstrucción, que le devuelve la generación descontada y le sube
la energía un **27,1 %**. La configuración de la frontera secundaria
reutiliza *ese mismo medidor* multiplicado por 0,3, pero lo declara
**`gross`**, de modo que no recibe reconstrucción: solo el recorte a cero,
que le suma un 0,34 %. El comentario del propio bloque de configuración
dice «todos son gross» y la excepción de Mariana rompe esa premisa sin que
se advierta.

**Comprobado de tres formas.** La serie reconstruida de M3 coincide con
`0,3 × (serie cruda de M1)` recortada a cero con `max|dif| = 0` en las
6.144 horas, y **no** coincide con `0,3 ×` la serie reconstruida, de la
que difiere en 3.265 horas. El perfil normalizado de M3 conserva el
hundimiento solar que M1 pierde: al mediodía vale 0,79 en M3 y 1,29 en M1,
y el pico se queda a las 8 en vez de moverse a las 9. Y en el contraste,
las otras cuatro instituciones suben exactamente 0,00 % con la
reconstrucción en M3 y no tienen ni una hora negativa en crudo, mientras
Mariana arrastra 213.

**Lo que vale.** Corregirlo, es decir, construir la serie secundaria desde
la principal ya reconstruida, sube la demanda de Mariana en M3 de
14.111,1 a 17.652,3 kWh, un **+25,1 %**; sube la demanda de la comunidad
en esa frontera un **+5,3 %**, de 66.733,7 a 70.274,9 kWh; y baja la
cobertura G/D de M3 del **95,3 % al 90,5 %**.

**Por qué importa más allá de la cifra.** La demanda es el lado corto en
esta frontera, y el volumen transado es el lado corto, de modo que
subestimar la demanda de una de las cinco instituciones un 25 % no es un
detalle de presentación. Además, la serie de M3 conserva justamente el
artefacto que el capítulo entero argumenta que hay que quitar: un perfil
con hundimiento solar no es demanda, es demanda menos generación.

**La decisión no es mía.** Corregirlo invalida el canon vigente y obliga a
rehacer la corrida en las dos fronteras. Va a la misma lista que el
multiplicador del umbral y que P-21: **hacerlo junto con la próxima
corrida canónica**, no abrir una solo para esto. Mientras tanto el
documento no debe afirmar que en la frontera secundaria los cinco
medidores son brutos, porque uno no lo es.


## H-25 · Las 330 horas de demanda que entran como cero

**2026-09-04 · declarado en el documento · pendiente de decidir si se corrige**

`preprocessing.py` hace `D_recon = (D_raw.fillna(0.0) + G_recon).clip(0)`
para los medidores netos. Ese `fillna(0.0)` convierte en cero toda hora sin
lectura, **antes** de la limpieza, de modo que la cascada no las ve y
ninguna máscara las registra.

Bajo M1 son 330 horas: Udenar 90, Mariana 114, UCC 126.

**El sesgo va en la dirección conservadora**, porque menos demanda es menos
déficit y un mercado más pequeño, y así queda declarado en la lista de
decisiones que sesgan en contra. Pero es una imputación silenciosa: esas
horas son indistinguibles de un consumo realmente medido de 0 kW.

**La alternativa** sería dejarlas como faltantes y que la limpieza las
trate como trata las de los medidores brutos, es decir, interpolación y
arrastre. Cambiaría la demanda de tres instituciones bajo M1 e invalida el
canon, de modo que iría con la corrida nueva. **No se toca sin su palabra.**


## H-27 · Un medidor publica su tensión bajo dos escalas incompatibles

**2026-09-05 · descubierto al medir el guardia físico · no toca ninguna cifra
publicada · abierto**

El cuarto medidor de CESMAG tiene cuatro ficheros de origen, y el cuarto de
ellos se solapa entero con el segundo. Entre el 1 de junio y el 15 de diciembre
hay **114.897 instantes que aparecen dos veces con lecturas distintas**, y la
diferencia no es ruido: en el solape un fichero informa una tensión de fase A
con mediana de **129,7 V** y el otro de **745,5 V**, es decir, un factor de
5,748. La potencia activa, en cambio, apenas cambia entre los dos, −0,024 frente
a −0,034 kW, de modo que lo que difiere es el ajuste de relación del
transformador de tensión y no el de corriente.

**El promedio de duplicados fabrica un medidor que no existe.** Desde P-17 la
carga funde los instantes repetidos promediándolos, y la media de 129,7 y 745,5
es 437,6. Por eso la mediana mensual de tensión de ese medidor salta de 127,1 V
en abril, mayo y junio a 432,6 V en julio y a 438,8 V de agosto en adelante, y
por eso al elegirle un nominal entre los tres del parque le corresponde 440 V.
**Ese medidor no opera a 440 V**: el número es el promedio de dos registros
incompatibles.

**No toca ninguna cifra publicada.** La frontera principal lee el medidor 1 de
CESMAG y la secundaria el 3; el 4 no entra en ningún cálculo. Pero sí toca al
guardia, porque un medidor con dos escalas superpuestas pasa la comprobación de
tensión sin marcar nada, es decir, el guardia no lo ve precisamente donde más
haría falta.

**Conecta con el asunto abierto de la escala de los transformadores** que dejó
el inventario de medidores. Es la primera evidencia directa, dentro del propio
árbol de datos, de que un registro se publicó bajo dos configuraciones
distintas. Antes de aplicar el guardia hay que decidir qué fichero es el bueno
para ese medidor, y de paso comprobar si algún otro tiene el mismo solape.

## H-28 · El paso horario sobrestima el autoconsumo, y afecta a los seis mecanismos

**2026-09-05 · medido en la sonda CAL-46 · no invalida el canon · declararlo
en el documento**

El autoconsumo es el mínimo entre generación y demanda, y **el mínimo de dos
promedios es mayor o igual que el promedio de los mínimos**. Al promediar la
hora antes de tomar el mínimo, el pipeline sobrestima cuánta generación se
consume en el sitio. No es un error de programación sino una consecuencia de
la desigualdad de Jensen sobre una función cóncava, y estaba sin declarar.

**Cuánto.** Medido sobre julio de 2025, comparando la misma corrida a paso
horario y a cuartos de hora:

| | Circuito principal | Circuito secundario |
|---|---|---|
| Autoconsumo del P2P | **−1,53 %** | **−2,67 %** |
| Índice de autoconsumo | 0,266 → 0,264 | 0,528 → 0,522 |
| Índice de autosuficiencia | 0,961 → 0,955 | 0,427 → 0,423 |

**Por qué importa y por qué no cambia el veredicto.** El autoconsumo pesa el
89,6 % del beneficio en la frontera principal y el 96,3 % en la secundaria, de
modo que la sobrestimación arrastra el agregado de **los seis mecanismos por
igual**: todos usan las mismas matrices y todos valoran el autoconsumo a la
misma tarifa. Por eso el orden se conserva y ninguna comparación queda tocada.
Lo que queda tocado es la **magnitud absoluta**, y ahí el documento debe
declarar una cota: entre el 1,5 y el 2,7 % según la frontera.

**Va en la dirección conservadora para la tesis.** Los términos de mercado se
mueven al revés, es decir, suben al afinar el paso, y suben mucho más: la prima
del vendedor un 7,19 % en la principal y un 40,46 % en la secundaria, y el
ahorro del comprador un 3,67 % y un 28,77 %. De modo que el paso horario
**infravalora justamente la parte que el mercado P2P aporta** y sobrevalora la
que comparte con todos los demás. Ver el registro de la decisión CAL-46.

### La cota por arriba, medida el 2026-09-05

Las cifras de arriba son las de quince minutos y acotan el sesgo **por
abajo**. El barrido de convergencia lo lleva hasta la resolución nativa de dos
minutos, sobre las horas con las treinta ranuras presentes en las cinco
instituciones a la vez, 5.338 y 5.327 de 6.144, y **sin pasar por la etapa de
limpieza**, cuya cascada está escrita en conteos de pasos (ver H-29):

| Contra el valor nativo | Circuito principal | Circuito secundario |
|---|---|---|
| El paso horario sobrestima el autoconsumo en | **+4,24 %** | **+6,98 %** |
| El paso horario subestima el lado corto en | **−27,15 %** | **−17,87 %** |
| Con cuartos de hora, el autoconsumo | +2,64 % | +3,93 % |

**La curva no se ha aplanado en los dos minutos.** El último tramo, de cuatro
a dos minutos, todavía aporta el 28 % del sesgo total en la principal y el
22 % en la secundaria, de modo que estas cifras siguen siendo cotas
inferiores: el sesgo verdadero es mayor. Dos minutos es lo más fino que el
dato permite, no el límite del fenómeno.

**Y la razón entre las dos ramas es la cifra que resume el asunto.** La
fracción de la oportunidad física que es mercado y no autoconsumo pasa del
7,74 % al 11,08 % en la frontera principal al afinar de la hora al dato
nativo, y del 15,00 % al 19,53 % en la secundaria: un 43,1 % y un 30,3 % más.
El paso horario no reparte su error por igual, **esconde sobre todo la parte
que solo el mercado puede capturar**.

## H-29 · La cascada de limpieza está escrita en pasos y no en horas

**2026-09-05 · descubierto al preparar el barrido de convergencia · no toca
ninguna cifra publicada · corregir antes de cualquier corrida subhoraria**

La etapa de limpieza documenta «interpolación para huecos de hasta 3 h» y
«arrastre de hasta 24 h», pero el código escribe esos límites como **conteos
de pasos**: `interpolate(limit=3)` y `ffill(limit=24)`. Con el paso horario
las dos lecturas coinciden y por eso el defecto llevaba invisible desde
siempre. Con cualquier paso más fino dejan de coincidir: a quince minutos
esos límites valen 45 minutos y 6 horas, y a dos minutos, 6 minutos y 48
minutos.

Lo mismo pasa con el guardia de solape de la reconstrucción del inversor,
que exige `int(solape.sum()) < 24` pensando en veinticuatro horas.

**Cuánto contamina la sonda de quince minutos, medido.** En julio la
cobertura es buena y los huecos son cortos: bajo la frontera principal hay
4 horas sin ninguna muestra, el 0,5 %, que a quince minutos son 28 cuartos,
el 0,9 %. Un hueco de cuatro horas mide dieciséis pasos de quince minutos,
por debajo de los veinticuatro del arrastre, de modo que **sigue quedando
imputado y ninguna hora cae al relleno con cero**. Lo que cambia es cuál de
los dos tratamientos lo recoge, en menos del 1 % de los pasos. La sonda se
sostiene, y el sesgo del promedio queda confirmado además por un camino que
no pasa por la limpieza, el barrido de convergencia.

**Qué hay que hacer.** Antes de correr nada por debajo de la hora en serio,
los límites tienen que expresarse en duración y derivar el conteo del paso
del eje, igual que ya hace el remuestreo desde CAL-46. No corre prisa
mientras el canon sea horario, pero queda anotado para que no vuelva a
descubrirse por casualidad.

---

## H-30 · Las dos cotas del juego son constantes escritas a mano, y el precio vive pegado a ellas

**Estado: MEDIDO el 2026-09-05. Da origen a CAL-47. PARCIALMENTE CORREGIDO
por H-38 el 2026-09-06: la lectura de que el precio pegado a las cotas es
estructural del modelo es FALSA. Lo es del lazo alternado que usa
producción; el sistema acoplado del modelo base converge a un punto
interior. Todo lo que este hallazgo dice sobre el REPARTO hay que leerlo a
traves de H-38. Lo que dice sobre la BANDA sigue en pie.**

### Qué son las cotas en el modelo base, que no es lo que parecía

En el modelo original de Chacón las dos cotas valen 1.250 y 114, y no son
un recorte. Aparecen como las raíces de un producto que **multiplica la
dinámica del precio**:

    peso = (techo − precio) · (precio − piso)

Ese peso vale cero en los dos extremos y es máximo en el punto medio, de
modo que el precio no se sale de la banda porque **al llegar al borde la
dinámica se apaga**. La traducción a Python lo reproduce fielmente. De ahí
se siguen dos cosas que cambian cómo hay que leer todo el capítulo del
modelo:

1. **Los dos extremos son equilibrios absorbentes.** No hay que buscar una
   explicación numérica al precio degenerado: está en la forma de la
   ecuación.
2. **Las cotas no son calibración, son la teoría de precios del modelo.**
   Si el precio se queda casi siempre en un borde, el borde es el
   resultado.

### Lo que se mide sobre el canon

En la frontera principal, **el 51,1 % de las transacciones cierra
exactamente en el piso** y el 32,6 % exactamente en el techo; queda un
16,3 % interior. En la secundaria el piso se lleva el 66,5 %. Es decir,
**el 83,7 % del mercado está pegado a una cota**.

El piso vale 280 COP/kWh, escrito a mano. La serie real de bolsa del
horizonte promedia 182,7 y su mediana es 114,6, de modo que el piso está
un **53 % por encima de la media** y es **2,4 veces la mediana**. La razón
entre techo y piso vale 3,24 en el modelo actual, 10,96 en el modelo base
y 6,97 con las cotas medidas: **el valor vigente es el atípico**, no el
propuesto.

### La consecuencia que nadie había mirado

En las 2.441 transacciones que cierran en el piso de la frontera
principal, **la prima del vendedor suma exactamente cero pesos**. No es un
defecto de cuenta: la prima se define como lo que el precio supera al
piso, y si el precio es el piso, el modelo declara que al vendedor le da
igual vender al vecino que exportar.

De ahí sale el reparto del excedente: **26,8 % al vendedor y 73,2 % al
comprador** en la frontera principal, **10,2 frente a 89,8** en la
secundaria.

Pero ese cero descansa en suponer que la red le paga al vendedor 280.
**Le paga el precio de bolsa.** Recontabilizando la prima contra la bolsa
real de cada hora, con el juego congelado, la prima crece **×1,9** en la
frontera principal y **×2,9** en la secundaria, y el reparto pasa a
40,4/59,6 y 25,0/75,0. Es una cota del efecto contable, no una predicción
de la corrida.

### El código ya sabía que estas dos magnitudes son la misma

El motor de comparación, cuando no recibe la serie de bolsa, la sustituye
por un vector constante con el valor del piso. Es decir, **el árbol trata
el piso y el precio de bolsa como la misma magnitud en todas partes menos
dentro del juego**, donde usa el sustituto siempre. Los cuatro escenarios
regulados y el residual del propio P2P valoran la exportación a bolsa
horaria; solo el juego usa la constante.

### Qué NO invalida

El volumen transado, que es el lado corto y reproduce entre métodos
distintos, y por tanto el bienestar agregado. El ordenamiento entre
mecanismos tampoco depende de esto de forma directa.

### Qué SÍ invalida

Toda afirmación sobre **el reparto** entre quien vende y quien compra: el
índice de posición del precio, los porcentajes de vendedor y comprador,
los umbrales de deserción y el precio del acuerdo. Y explica por qué el
índice de desigualdad publicado no distingue los mecanismos: véase H-31.

### Trabajo abierto

La banda medida se invierte **133 horas de 6.144, el 2,16 %**,
concentradas en agosto y septiembre, que es el pico seco de la bolsa. Ahí
el mayorista supera al costo unitario y ninguna transacción conviene a las
dos partes, de modo que **el mercado no debe abrir esa hora**. Hay que
programarlo y declararlo, no dejar que un recorte lo tape.

---

### Cierre parcial · la sonda, ejecutada el 2026-09-05

Tres configuraciones sobre los mismos datos: las cotas de hoy, solo el piso
medido, y la banda completa. El lazo de la sonda se validó antes contra el
motor: 380 flujos, **diferencia máxima 0,000e+00** en energía y en precio.

| | Principal, julio | Principal, septiembre | Secundaria, septiembre |
|---|---:|---:|---:|
| Bolsa mediana del mes | 112,90 | 245,56 | 245,56 |
| Excedente con las cotas de hoy | 644.510 | 125.922 | 384.987 |
| Excedente con la banda medida | 719.661 | 104.371 | 354.341 |
| Variación | **+11,7 %** | **−17,1 %** | **−8,0 %** |
| Tajada del vendedor, hoy | 24,7 % | 30,1 % | 15,1 % |
| Tajada del vendedor, banda | **32,4 %** | 30,7 % | **20,1 %** |

**El volumen no se mueve.** Idéntico en las tres configuraciones, los dos
meses y las dos fronteras. Cambiar las cotas no mueve energía, solo dinero.

**La tajada del vendedor mejora siempre**, entre 2 y 5 puntos.

**El nivel del excedente cambia de signo según el mes.** Cuando la bolsa
está barata, exportar es mal negocio y venderle al vecino vale mucho;
cuando está cara, exportar ya es buen negocio. El piso constante **borraba
esa estacionalidad**. El cambio no corrige un sesgo direccional: habilita
una señal que el modelo hoy no puede ver.

**Lo que no cambia:** el precio sigue clavado en las cotas, del 89,2 % al
85,5 % en julio. La degeneración es estructural y no se arregla poniendo
cotas con sentido.

Decidido y especificado en `docs/adr/0047-cal47-banda-de-precios-medida.md`.
**Invalida el canon**, de modo que entra en la misma corrida que CAL-45,
H-26 y P-21.

**Aviso sobre la comprobación.** La sonda **no puede** compararse contra el
canon: el canon se produjo el 2026-08-08 y el pipeline lleva encima CAL-44 y
CAL-45, de modo que los datos de entrada ya no son los mismos. En julio son
968 flujos frente a 1.028 y en la secundaria 1.060 frente a 1.132; la brecha
es mayor en la frontera principal porque CAL-44 tocó justamente la
generación de Udenar, que es allí el vendedor dominante. La comprobación que
sí vale, y la que se pasó, es contra el motor de hoy.

---

## H-31 · El índice de desigualdad mide la dotación y no el mecanismo

**Estado: ABIERTO. Medido el 2026-09-05.**

El índice publicado se calcula sobre el beneficio **absoluto en pesos** de
cada institución, que está dominado por el autoconsumo valorado a tarifa,
idéntico en los siete mecanismos. Resultado: los siete caen entre 0,136 y
0,176, indistinguibles, y **el mercado entre pares sale peor que el
escenario regulado C1** en la frontera principal, 0,1513 frente a 0,1473.

Calculado sobre **lo que cada mecanismo reparte de verdad**, es decir la
diferencia contra el escenario de bolsa pura, el mismo índice se abre de
0,21 a 0,66 y **reordena los mecanismos**: C1 pasa de parecer el más
equitativo a ser el menos.

Y hay una afirmación que no necesita índice ninguno: **bajo el mercado
entre pares ganan las cinco instituciones**, la peor sube 353 mil pesos en
la frontera principal y 296 mil en la secundaria; **bajo el esquema
colectivo alguna pierde**, 348 mil pesos abajo en la principal y 289 mil
en la secundaria.

### La medida que pidió el autor, y lo que dice

Pesos capturados por cada kWh que la institución movió en el mercado:

| Institución | Principal, kWh | Principal, COP/kWh | Secundaria, kWh | Secundaria, COP/kWh |
|---|---:|---:|---:|---:|
| Udenar | 2.866 | 184,89 | 1.393 | 96,30 |
| Mariana | 851 | 396,00 | 1.196 | 149,05 |
| UCC | 1.390 | 497,08 | 1.216 | 309,49 |
| HUDN | 1.129 | 299,51 | 1.531 | 104,26 |
| CESMAG | 1.048 | 431,97 | 3.130 | 627,98 |

La dispersión es de **2,7 veces** en la principal y **6,5 veces** en la
secundaria. Y va al revés de lo que cabría temer: **Udenar mueve el 39 %
de la energía de la frontera principal y es quien menos captura por
unidad**. La causa está en H-30, porque quien vende cobra el piso.

### Decisión tomada

El documento publica **dos** medidas con papeles distintos: lo ganado por
kWh aportado como principal, por interpretable, y el índice sobre lo que
cada mecanismo reparte para ordenar los siete entre sí. El índice sobre el
nivel se conserva solo para explicar por qué se sustituyó.

---

## H-32 · La condición inicial del bloque comprador está calibrada para una banda ancha

**Estado: ABIERTO. Descubierto el 2026-09-06 al estrechar la banda en la
sonda de CAL-47.**

El bloque comprador arranca con todos los precios en

    arranque = techo · I / (I + 1)

con `I` el número de compradores de esa hora. Viene literalmente del modelo
base, donde reparte un presupuesto de `techo · I` entre los `I` compradores
y el jugador virtual.

**Por qué nunca dio problema.** En el modelo base el piso vale 114 y el
techo 1.250, de modo que el arranque cae entre 625 y 1.042 según el número
de compradores, siempre holgadamente dentro de la banda. En el modelo con
datos reales el piso vale 280 y el techo 906, y el arranque cae entre 453 y
725: también dentro. **La fórmula solo falla cuando el piso deja de ser
despreciable frente al techo**, y eso no había ocurrido nunca.

**Por qué falla ahora.** Con el piso de permuta de CAL-47 la banda mide unos
175 COP/kWh y empieza en unos 620. El arranque, que se calcula sobre el
techo y no sobre la banda, **nace por debajo del piso** en cuanto hay pocos
compradores:

| Compradores | Horas | Arranque | ¿Dentro de la banda? |
|---:|---:|---:|---|
| 1 | 88 | 398,97 | **No** |
| 2 | 41 | 531,96 | **No** |
| 3 | 51 | 598,46 | **No** |
| 4 | 57 | 638,35 | Sí, apenas |

Medido sobre la frontera secundaria en septiembre, **el 75,9 % de las horas
activas nace por debajo del piso**. El código recorta ese valor hasta el
piso, y allí el peso que gobierna la dinámica,
`(techo − precio)·(precio − piso)`, vale exactamente cero. **La dinámica no
arranca y el precio queda congelado en el piso.**

Esa es la explicación completa de lo que la sonda mostró: 99,5 % de los
flujos en el piso y una tajada del 0,1 % para el vendedor. No es una
decisión del mercado, es una condición inicial que nació fuera del dominio.

### Qué invalida y qué no

**No invalida** las configuraciones de banda ancha, que son las tres
primeras de la sonda de CAL-47 y el canon entero: en todas ellas el arranque
cae dentro. Tampoco invalida la prueba dorada ni el caso base.

**Sí invalida** cualquier lectura de la banda estrecha, es decir del piso de
permuta, hasta que se corrija. La conclusión de que el mercado casi no vale
nada bajo la alternativa regulada correcta **no está medida**.

### El arreglo, y por qué así

La generalización fiel reparte **la banda** en vez del techo:

    arranque = piso + (techo − piso) · I / (I + 1)

que recupera la fórmula del modelo base cuando el piso es despreciable
frente al techo, que es justamente el régimen en que se calibró.

Para no mover nada de lo ya publicado, la regla se aplica **solo cuando el
arranque del modelo base cae fuera de la banda**. Así el caso base, el canon
y las tres configuraciones de banda ancha quedan idénticos bit a bit, y solo
cambia donde estaba roto.

### Lección

Es la tercera vez en este trabajo que una constante heredada del modelo base
resulta estar calibrada para un régimen que ya no es el nuestro: antes fue el
paso de tiempo, que no existía, y el piso de precios, que era una constante
escrita a mano. **Conviene revisar el resto de constantes del solucionador
contra el régimen de los datos reales antes de la corrida canónica.**

---

## H-33 · El excedente del mercado es el ancho de la banda por la energía, y el precio no interviene

**Estado: MEDIDO y COMPROBADO el 2026-09-06. Es una identidad, no un
resultado empírico.**

La prima que se lleva el vendedor es `(precio − piso)·q` y el ahorro que se
lleva el comprador es `(techo − precio)·q`. Al sumarlas **el precio se
cancela**:

    excedente total = (techo − piso) · energía transada

Comprobado sobre las salidas de la sonda de CAL-47, al último decimal:

| Configuración | kWh | Excedente | Excedente por kWh | Ancho de la banda |
|---|---:|---:|---:|---:|
| M1 julio, cotas de hoy | 1.029,111 | 644.509,50 | 626,278 | 906,28 − 280 = **626,28** |
| M3 septiembre, piso de permuta | 608,539 | 108.386,83 | 178,110 | 797,94 − 619,83 = **178,11** |
| M1 julio, piso de permuta | 1.036,670 | 180.546,44 | 174,160 | 814,91 − 640,75 = **174,16** |

Cuando el piso varía hora a hora, la columna del medio es la media del
ancho ponderada por energía, y también cuadra.

### La anatomía del modelo, completa

1. **La energía** la fija el lado corto. Medido invariante a las cotas en
   seis comparaciones de la sonda: mismos flujos y mismos kWh al decimal.
2. **El excedente total** es el ancho de la banda por esa energía.
   Aritmética pura.
3. **El precio**, es decir todo el aparato del replicador, el lazo de
   Stackelberg y las ecuaciones diferenciales, determina **únicamente el
   reparto** entre quien vende y quien compra.

### Por qué importa, y mucho

**Ninguna constante del solucionador puede mover el agregado.** El
bienestar total, la comparación entre mecanismos y el ordenamiento son
aritmética sobre la banda y el volumen. Las velocidades heredadas del
modelo base, el presupuesto de integración, el número de iteraciones del
lazo externo y la condición inicial de H-32 solo pueden mover el reparto.

Eso acota de golpe el alcance de tres hallazgos abiertos y hace innecesaria
una revisión exhaustiva de constantes: basta comprobar la convergencia del
**reparto**.

Y acota H-32: corregir el arranque mueve la tajada del vendedor de 0,1 a
6,6 % y **no toca el excedente ni un peso**.

### Es la forma fuerte de un hallazgo que ya existía

La ronda 3 había establecido que el volumen transado es el lado corto y que
por tanto el juego no determina el agregado. Esta identidad lo cierra: no
solo el volumen, **el excedente entero** es independiente del juego. La
tesis de Juan B. Medina llega a lo mismo por otra vía, al observar que los
pagos bilaterales se cancelan entre comprador y vendedor y el bienestar se
reduce al volumen transado.

### Consecuencia para la redacción

El capítulo del modelo tiene que decir esto donde presenta el mecanismo, no
esconderlo en robustez. Que el aparato dinámico gobierne el reparto y no el
agregado **no es una debilidad**: es lo que hace que el ordenamiento entre
mecanismos sea robusto, y es la razón por la que el precio degenerado de
H-30 no invalida los resultados agregados.

---

## H-34 · Con datos reales el reparto es un programa lineal, y de ahí sale el precio degenerado

**Estado: ESTABLECIDO el 2026-09-06. Explica hallazgos anteriores; no obliga
a cambiar nada.**

### El costo del vendedor pierde su curvatura en modo real

El costo de generar es `a·(ΣP)² + b·(ΣP) + c`. En el modelo base el
coeficiente cuadrático vale `[2,167 · 0,420 · 0 · 0 · 0 · 0]`, de modo que
**dos de los seis vendedores tienen curvatura**. En modo con datos reales
vale **cero para los cinco**, junto con el término independiente.

**La justificación es correcta y está escrita**: un arreglo fotovoltaico no
tiene costo de combustible, su costo marginal es constante y la curvatura
sobra. Lo que no estaba escrito es la consecuencia matemática.

### Qué problema resuelve entonces cada bloque

**El vendedor, dadas las cotas: convexo.** Maximiza ingreso menos costo
sobre un poliedro de transporte, con la capacidad de cada vendedor y la
demanda neta de cada comprador. Con curvatura no negativa es maximizar una
función cóncava sobre un convexo.

**Pero sin curvatura es lineal.** El objetivo queda `Σ (precio − b)·P`, es
decir vender a quien más pague hasta agotar capacidad, y todo el reparto se
vuelve **un problema de transporte lineal**.

**El bloque comprador no optimiza.** Su función de aptitud no es cóncava en
el precio; es una dinámica de replicador, no la solución de un problema.

**El problema conjunto no es convexo.** Son dos niveles anidados resueltos
por respuesta óptima alternada, y un problema de dos niveles es no convexo
en general aunque cada nivel lo sea.

### La consecuencia, que explica tres hallazgos previos de golpe

Un programa lineal tiene **valor óptimo único**, pero su conjunto de
soluciones es una cara y sus **variables duales, que aquí son los precios,
forman un poliedro** cuando el primal es degenerado.

Eso es literalmente lo que la batería de validación había medido sin
nombrarlo así:

- el volumen reproduce entre tres métodos hasta la decimotercera cifra;
- el precio sale **distinto en los tres**;
- el lazo alternado cicla entre dos vectores de precio en torno al 21 % de
  las horas no triviales, que es lo típico cuando el nivel de abajo tiene
  un óptimo plano y el de arriba salta entre vértices.

**El precio degenerado no es un defecto numérico ni un fallo de la
traducción: es el comportamiento esperado de un mercado con costo lineal.**

### Es la misma afirmación que H-33, vista por el otro lado

Que el excedente total sea el ancho de la banda por la energía transada
equivale a decir que **el primal fija el valor y el dual no es único**. Las
dos observaciones son la misma propiedad.

### Qué hacer con esto

Nada en el código. Todo en la redacción. Convierte tres cosas que hoy
parecen debilidades del trabajo en una sola propiedad bien entendida, y da
la frase que ordena el capítulo del modelo:

> La optimización fija cuánta energía se mueve y cuánto vale el
> intercambio; la dinámica y las cotas solo deciden quién se lleva ese
> valor.

Conviene decirlo donde se presenta el mecanismo y no esconderlo en el
capítulo de robustez, porque es también la razón por la que el ordenamiento
entre mecanismos sobrevive al precio degenerado.

---

## H-35 · Las dos fronteras tienen ritmos semanales opuestos, y en una el mercado se queda sin comprador

**Estado: MEDIDO el 2026-09-05. Pendiente de redactar en el capítulo de
resultados.**

La Actividad 4.1 de la propuesta comprometió evaluar el desempeño «en
distintas semanas o días», y ese corte no existía. Lo que había era un corte
sintético que multiplica la demanda por 0,65 y un corte real que solo mira
energía, no transacciones ni beneficios.

El canon no lleva marca de tiempo, sus columnas de hora y día son enteros,
pero el horizonte es contiguo y horario: la hora k es el 2025-04-04 a las
00:00 más k horas, son 6.144 horas, es decir 256 días exactos, y el 4 de
abril de 2025 cae en viernes. Con ese mapeo el corte sale como post-proceso,
sin re-correr nada.

| | Principal | Secundaria |
|---|---:|---:|
| Horas activas en día hábil | 12,2 % | 30,5 % |
| Horas activas en fin de semana | **28,0 %** | 23,7 % |
| Energía transada el fin de semana | **49,1 %** del total | **6,2 %** del total |
| Cobertura en día hábil | 16,9 % | 79,3 % |
| Cobertura en fin de semana | 28,8 % | **146,2 %** |

**En la frontera principal el fin de semana es el 28,9 % del calendario y
concentra casi la mitad de la energía transada.** La demanda se desploma y
la generación no, de modo que sobra excedente y todavía queda quien lo
compre.

**En la secundaria ocurre lo contrario, y la causa está en la última fila.**
La cobertura supera el 100 %: todos generan más de lo que consumen, todos
quieren vender y **no queda comprador**. El mercado no cierra por falta de
contraparte, no por falta de energía.

> Es la demostración más directa que este trabajo tiene de que **un mercado
> entre pares necesita heterogeneidad y no solo excedente**.

**Dos consecuencias en el reparto.** El precio mediano del fin de semana en
la principal es exactamente el piso, frente a 378,93 en día hábil: con más
oferta relativa los vendedores compiten y el precio cae hasta abajo. Y por
eso su tajada empeora, del 28,3 al 25,1 %. Por institución, la UCC captura
el 55,2 % de su excedente en fines de semana; el CESMAG, en la otra
frontera, solo el 3,7 %.

**Límite que hay que declarar y no esconder.** El corte solo vale para el
mercado entre pares. Para los mecanismos regulados el canon guarda únicamente
totales de horizonte por agente, y los que liquidan por neteo mensual no
admiten el corte sin inventar una regla de atribución. Se reporta lo que se
puede y se declara lo que no.

**Robusto a CAL-47.** Como el volumen no depende de las cotas (H-33), el
reparto semanal de la energía sobrevive al cambio de banda. Solo se moverán
las cifras de excedente, y en proporción conocida.

---

## H-36 · Las fronteras del proyecto son una fracción pequeña de las instituciones reales

**Estado: MEDIDO el 2026-09-05 sobre los datos de ASC. Refuerza H-7.**

Los archivos de consumos entregados con las recomendaciones contienen la
medida del comercializador para cuatro de las cinco instituciones, a paso de
quince minutos. Comparados con lo que el modelo llama la institución:

| Frontera de ASC | kW medios, enero 2025 | El modelo, frontera principal |
|---|---:|---:|
| Hospital Departamental | **231,5** | 9,1 |
| Universidad Mariana | 39,5 | — |
| Universidad Cooperativa | 19,9 | — |
| Universidad de Nariño, VIPRI | 13,1 | — |
| Universidad de Nariño, Torobajo | 4,2 | — |
| Mariana, laboratorios | 6,0 | — |

**El hospital real es unas veinticinco veces mayor que el hospital del
modelo.** Eso confirma y cuantifica H-7, que había establecido que la
frontera principal no es el campus sino el circuito de inyección.

**Y hay un aviso dentro del propio dato.** Los 4,2 kW medios de la sede de
Torobajo son implausibles para un campus universitario, de modo que **las
fronteras de ASC tampoco son la institución entera**. Sirven para acotar el
orden de magnitud, no para sustituir la medida del proyecto.

**Lo que contienen y lo que no.** Consumo activo y reactivo en los dos
sentidos, con código de frontera y serial de medidor, a quince minutos. **No
contienen generación, ni tarifa, ni nivel de tensión.** Son, exactamente,
lo que el autor anticipó: «los consumos nada más».

**Unidades por confirmar.** La magnitud es consistente con energía por
intervalo de quince minutos, pero no se verificó contra una fuente
independiente. El contraste decisivo está disponible y no se ha hecho:
comparar una frontera de ASC contra el medidor del proyecto de la misma
institución en el mismo mes, usando uno de los archivos que cae dentro del
horizonte del estudio.

**Para qué sirve.** Es la única vía a la vista para construir el caso del
consumidor grande y del comprador puro, que hoy no existe en el dato real:
las cinco instituciones son prosumidores de escala parecida, con generación
media entre 1,1 y 2,5 kW, y las cinco venden en algún momento.

---

## H-37 · El paso de integración del bloque comprador es marginal, y con banda estrecha deja de bastar

**Estado: MEDIDO el 2026-09-06. Afecta al reparto, nunca al agregado.**

Al estrechar la banda quedaba por saber si el precio se queda abajo porque
el mercado lo decide o porque no le da tiempo a moverse. Se probó con cinco
presupuestos sobre las mismas 720 horas, con la condición inicial ya
corregida de H-32.

| Variante | Horizonte | Pasos | Iteraciones | En el piso | Tajada del vendedor |
|---|---:|---:|---:|---:|---:|
| Producción | 0,005 | 150 | 2 | 64,1 % | 6,6 % |
| Horizonte ×2 | 0,010 | 300 | 2 | 67,3 % | 6,8 % |
| Horizonte ×4 | 0,020 | 600 | 2 | 69,5 % | 6,1 % |
| Iteraciones ×4 | 0,005 | 150 | 8 | 64,6 % | 6,5 % |
| **Paso ×4** | 0,005 | 600 | 2 | **39,4 %** | **14,9 %** |

**El excedente sale idéntico en las cinco, 108.387 COP, y el volumen
también.** Es la quinta confirmación de H-33 y garantiza que nada de esto
puede tocar el agregado.

### Lo que dice el cuadro

**No es el horizonte.** Alargarlo dos y cuatro veces no mueve el reparto:
la dinámica ya había convergido en el tiempo que se le daba.

**No son las iteraciones del lazo externo.** Cuadruplicarlas tampoco.

**Es el paso de integración.** Afinarlo cuatro veces, a horizonte constante,
**más que duplica la tajada del vendedor**, del 6,6 al 14,9 %, y baja del
64,1 al 39,4 % la fracción de transacciones pegadas al piso.

### El mecanismo

El bloque comprador se integra con Euler explícito de paso fijo. Una de sus
velocidades vale cien mil y el propio código documenta que **exige un paso
por debajo de cuatro centésimas de milésima para ser estable**. El paso de
producción vale tres coma tres centésimas de milésima, es decir **queda
justo por debajo del límite**.

Con la banda ancha eso basta. Con la banda estrecha el peso que gobierna la
dinámica cae doce veces, el sistema se vuelve relativamente más rígido, y un
paso marginal **sobrepasa la cota**. El recorte lo devuelve al borde, y allí
el peso vale cero y el precio queda absorbido. Por eso un paso más grueso
produce sistemáticamente **más precios pegados al piso**: no es que el
mercado los lleve ahí, es que el integrador los deja ahí.

Es H-32 en su versión de segundo orden: allí la condición inicial nacía
fuera de la banda, aquí la trayectoria se sale de ella por error de
truncamiento.

### Qué invalida

**Nada del agregado**, por H-33. Ni el bienestar, ni la comparación entre
mecanismos, ni el ordenamiento, que son aritmética sobre la banda y el
volumen.

**Sí toca todo lo que depende del reparto**: el índice de posición del
precio, los porcentajes de vendedor y comprador, la equidad y los umbrales
de deserción.

### Cuánto toca al canon, medido

La misma batería sobre la banda ancha con que se produjo el canon:

| Variante | En el piso | Tajada del vendedor |
|---|---:|---:|
| Producción | 57,9 % | **16,3 %** |
| Horizonte ×2 | 59,7 % | 16,1 % |
| Horizonte ×4 | 60,7 % | 14,9 % |
| Paso ×4 | 53,0 % | 17,0 % |
| Iteraciones ×4 | 58,1 % | 16,0 % |

El excedente sale idéntico en las cinco, 384.987 COP. Es la sexta
confirmación de H-33.

| | Recorrido de la tajada | En relativo |
|---|---|---|
| Banda ancha, el canon | 14,9 a 17,0 % | **−9 % a +4 %** |
| Banda estrecha, CAL-47 | 6,1 a 14,9 % | **−8 % a +126 %** |

**El canon no queda invalidado.** Sus cifras de reparto llevan una
incertidumbre numérica de aproximadamente **un punto sobre la tajada del
vendedor**, que conviene declarar como cota de precisión donde se publiquen,
igual que ya se hizo con el índice de posición del precio en la sensibilidad
global. No hay nada que rehacer.

**La banda estrecha es unas catorce veces más sensible en términos
relativos y no se puede publicar sin arreglar antes el paso.** El defecto
existe siempre; solo muerde cuando la banda se estrecha.

**Un detalle que refuerza el diagnóstico.** Con la banda ancha, alargar el
horizonte **baja** la tajada del vendedor y afinar el paso la **sube**: los
dos errores tiran en direcciones contrarias y en producción se compensan en
parte. Con la banda estrecha esa compensación desaparece y el error del paso
queda al descubierto.

### Qué hacer

Antes de la corrida canónica, **fijar el paso por criterio de estabilidad y
no por número de puntos**: derivarlo del límite documentado y del ancho de
la banda, en vez de heredar un valor calibrado para otro régimen. Es el
mismo patrón que CAL-46 aplicó al paso de tiempo del modelo, y la cuarta
constante heredada que resulta estar calibrada para un régimen que ya no es
el nuestro.

---

## H-38 · El lazo alternado no resuelve el modelo base, y por eso el precio se pega a las cotas

**Estado: ESTABLECIDO el 2026-09-06. Es el hallazgo más grave de esta
tanda. Corrige a H-30.**

### Lo que se creía

H-30 concluyó que el precio pegado a las cotas era **estructural**: los dos
extremos son equilibrios absorbentes del replicador, luego el precio
degenerado sería una propiedad del modelo y no un defecto. Se apoyaba en
que el modelo base también pega el precio a las cotas cuando se le corre
por la vía de producción.

**Eso último es cierto y la conclusión es falsa**, porque la vía de
producción no es la del modelo base.

### El modelo base no alterna

`JoinFinal.m` construye un estado combinado con precios y cantidades y lo
integra de una sola vez con `ode15s`, tolerancias 1e-6, sobre un horizonte
declarado. **La alternancia entre bloques es una aproximación de la
traducción**, y en producción corre con **dos** iteraciones.

El artículo publica precios **interiores**: en el caso de las 22:00 un
**Matiz del 2026-09-06 (ver H-39).** Ese 380,30 es del caso de las 22:00.
La tabla III, que es la del caso de las 14:00, publica los cuatro precios en
114,000 · 1.250,000 · 114,000 · 114,000: **los cuatro en una cota**. El
modelo base también los pega, de modo que este hallazgo mide una proporción
y no una diferencia cualitativa.

comprador paga **380,30** con la banda en [114, 1250], y en el análisis de
sensibilidad el precio de un agente sube de 114 a **402** al aumentar su
urgencia. Es decir, el mecanismo **diferencia precios entre compradores**,
que es lo que se espera de una negociación.

### Las tres vías, sobre la misma hora del caso base

La batería de validación del proyecto ya lo tenía medido y archivado como
«el precio es degenerado» en vez de como «la alternancia no resuelve»:

| Vía | Precios | Volumen |
|---|---|---|
| Alternante, la de producción | `[1250, 1250, 114]` | 3,032617 |
| **Acoplado, el del modelo base** | **`[1250, 1250, 1136,0]`** | 3,032617 |
| Oráculo estático | `[212,24, 114, 114]` | 3,032617 |

Tres vectores distintos, **volumen idéntico al sexto decimal**. El precio
es genuinamente indeterminado, y en eso H-34 acierta; pero **entre los
óptimos, cada método escoge otro**, y el alternante escoge sistemáticamente
las esquinas.

### El acoplado converge, y a un punto interior

Medido sobre la hora 14 del caso base, con dos vendedores y cuatro
compradores, banda [114, 1250]:

| Horizonte | Segundos | Precios | Movimiento en la cola |
|---|---:|---|---:|
| 0,01, el del artículo | 5,4 | 1058,52 · 573,15 · 1052,78 · 1065,56 | 7,8 % |
| 0,05 | 54,2 | 1207,74 · 126,20 · 1202,05 · 1214,00 | 0,2 % |
| 0,10 | 130,2 | 1208,12 · 125,08 · 1203,17 · 1213,64 | **0,0 %** |
| 0,40 | 951,2 | 1208,33 · 124,90 · 1207,81 · 1208,96 | 0,1 % |

**Hay equilibrio interior y es estable.** De 0,05 en adelante los precios no
se mueven, y cuadruplicar el horizonte cuarenta veces los deja igual.
Ninguno de los cuatro toca una cota. Y hay diferenciación entre
compradores, uno cerca del piso y tres cerca del techo, que es
cualitativamente lo que describe el artículo.

### Pero el artículo para el reloj antes de tiempo

A su horizonte de 0,01 la cola todavía se mueve un 7,8 % y el segundo
comprador marca **573** cuando el equilibrio son **125**, un factor de más
de cuatro. **Los precios publicados en el modelo base son un transitorio,
no el equilibrio de su propio sistema.** No invalida aquel trabajo, pero
impide copiarle el horizonte: hay que integrar hasta converger.

### Qué invalida

**Todo el reparto publicado**: el índice de posición del precio, los
porcentajes de vendedor y comprador, la equidad, los umbrales de deserción,
el precio del acuerdo, y las conclusiones sobre la tajada del vendedor que
se derivaron de las sondas de CAL-47.

**Y obliga a releer H-30 y H-37.** El pinning no es estructural sino un
artefacto del método; y el ciclo de período dos que H-37 daba por
característico del problema es, en realidad, el lazo alternado sin
converger.

### El coste de converger no está repartido, está concentrado

Primer intento de medirlo sobre el dato real, con parada adaptativa que
dobla el horizonte hasta converger, 36 horas de la frontera principal y
seis procesos:

    las 10 primeras horas ....    16 s
    las 10 siguientes ........   499 s
    las 10 siguientes ........ 1.432 s
    las 6 ultimas ............ sin acabar en 3.500 s

**Un tercio de las horas converge en segundos y la cola no cierra.**
Extrapolado a las 6.144 horas del horizonte, exigir convergencia estricta
se va por encima de las treinta horas de reloj y con la cola abierta, de
modo que **no es viable tal cual**.

La consecuencia práctica es que la pregunta útil no es cuánto cuesta
converger sino **qué horizonte se puede pagar y qué fracción converge
ahí**, y qué se hace con las horas que se resisten. Medirlo es el paso
previo a cualquier cambio en producción.

### Qué NO invalida, y no es poco

El **volumen**, idéntico en las tres vías al sexto decimal. Y con él, por la
identidad del excedente (H-33), **el excedente total, el bienestar
agregado, la comparación entre mecanismos y el ordenamiento**. La
conclusión principal del trabajo sobrevive intacta.

Tampoco toca nada de la banda: el techo como costo unitario, el piso como
permuta o bolsa según el estado del vendedor, ni la condición de existencia
frente a los cargos de red. Todo eso es aritmética sobre las series y no
pasa por el solucionador.

---

## H-39 · Con qué mide el modelo base su propia calidad, y qué pasa al aplicarlo aquí

**Estado: MEDIDO el 2026-09-06. Contiene la rectificación de un diagnóstico
propio equivocado, una discrepancia entre las fuentes del modelo base que
queda ABIERTA para el asesor, y una medida nueva que el proyecto no tenía.**

Nace de una pregunta que el proyecto nunca se había hecho: **con qué
parámetro mide el modelo base la calidad de su propia solución**. El
artículo la responde: compara contra un método centralizado y publica el
error normalizado, **0,316 % de media y por debajo del 6 % en el peor caso**.
Nuestro proyecto no tenía esa comprobación, y el oráculo que hay en el
repositorio no sirve para hacerla, porque es un lazo de Stackelberg con
optimizador dentro y no un centralizado.

### Qué mide de verdad ese 0,316 %

**Acotado por H-40 el mismo día.** Lo que sigue vale para el documento
extenso del modelo base. La versión arbitrada y publicada usa **otra
métrica y otro número**, el error sobre la suma de bienestares y 0,23 % de
media, y hay que leer las dos cosas juntas.

El documento extenso define el error sobre dos cantidades, no sobre el
bienestar:

    ahorro del comprador   S_i  = (techo − precio_i) · energía comprada
    prima del vendedor     SR_j = (precio_i − piso) · energía vendida

Su suma es **el ancho de la banda por la energía transada**, que es la
identidad de H-33. Y el volumen está fijado por las restricciones del propio
modelo. De modo que el total es idéntico para todos los métodos, y el error
**no mide eficiencia económica**: mide cuánto se parece el **reparto** entre
vendedores y compradores al que produce el centralizado.

Conviene decirlo con esas palabras, porque el nombre «error de bienestar»
sugiere otra cosa.

### Rectificación: la suma de bienestares no se puede maximizar libremente

Un primer intento de construir el centralizado devolvió uno que **no
transaba nada**, y la métrica salía indefinida. El diagnóstico que di
entonces fue que el objetivo era decreciente en lo transado, y esa parte del
álgebra es cierta: los dos bienestares llevan el pago con signos opuestos,

    vendedor   − Σ_ji P_ji / log(1 + π_i)
    comprador  + Σ_i (Σ_j P_ji) / log(|π_i| + 1)

y **se cancelan exactamente**, comprobado a precisión de máquina,
4,4 · 10⁻¹⁶ sobre un valor de 2,25. Es lo que debe pasar: un pago entre dos
miembros de la comunidad es una transferencia interna.

**Pero la conclusión que saqué de ahí era falsa.** El álgebra no es
vinculante, porque **el modelo base no deja elegir cuánto transar**: fija el
volumen al lado corto con una restricción de **igualdad**, sus ecuaciones 11
y 12. Si sobra oferta, cada comprador recibe exactamente su déficit; si
falta, se coloca toda la generación. El error estaba en mi sonda, que usaba
desigualdades en los dos lados y por eso permitía cerrar el mercado.

Corregido en `error_centralizado.py`, el centralizado transa.

### La discrepancia que queda abierta

Al comparar término a término apareció otra cosa, y esta **no se resuelve
desde el repositorio**. El término que penaliza competir con los demás
compradores está escrito de dos formas distintas en las fuentes del modelo
base:

| Fuente | Forma | Energía que multiplica |
|---|---|---|
| Artículo, ecuación 14 | `−β_i Σ_{ℓ≠i} π_ℓ Σ_j P_jℓ` | la del comprador **ajeno** |
| `JoinFinal.m`, línea comentada | la misma | la del **ajeno** |
| El script en Python del modelo base | `Σ_{k≠i} π_k Σ_j P_ji` | la **propia** |

Coinciden exactamente cuando todos los compradores compran lo mismo, que es
el caso de las pruebas sintéticas con que se validó en su día, y divergen en
cuanto no. Medido sobre cuatro compradores con cantidades distintas, la
diferencia mayor asciende a **1.755,95** unidades sobre valores del orden de
2.500, y el agregado del día de prueba pasa de −725,47 a −3.587,30.

**Decisión: se sigue al artículo**, que es la especificación publicada y
coincide con el MATLAB. **CONFIRMADA el mismo día por H-40**: la versión
arbitrada en *IEEE Latin America Transactions* escribe esa misma forma en su
ecuación (11), de modo que la elección deja de necesitar consulta y la
discrepancia queda confinada al guion en Python.

**No mueve nada más.** Comprobado sobre el día completo con la compuerta del
paso horario: de los **672 números de la huella difieren 25**, y los
veinticinco son bienestar del comprador, las veinticuatro horas y el
agregado. Flujos, precios, volúmenes y liquidación quedan **idénticos bit a
bit**. La función solo informa: ninguna función de resolución la llama,
comprobado sobre el árbol sintáctico de los tres módulos del núcleo.

Hay una segunda discrepancia del mismo tipo: el documento extenso escribe el
término del pago como `π_gb · Σ_j P_ji · ln(1/(π_i+1))` y el script lo
escribe como `Σ_j P_ji / ln(|π_i|+1)`, sin el factor del piso y con la
operación invertida. **Resuelta por H-40**: la versión publicada escribe la
segunda forma, que es la que el proyecto ya usaba.

### El artículo también publica precios en las cotas

Conviene dejarlo dicho, porque el registro venía argumentando lo contrario.
La tabla III del artículo, el caso de las 14:00, publica los cuatro precios
así: **114,000 · 1.250,000 · 114,000 · 114,000**, con la banda en
[114; 1.250]. **Los cuatro están exactamente en una cota.** El valor
interior de 380,30 que el registro venía citando pertenece a otro caso, el
de las 22:00.

Eso no anula el argumento de CAL-48, porque el modelo base sí produce
precios interiores en ese otro caso y en el análisis de sensibilidad, donde
un precio sube de 114 a 402. Pero **sí obliga a matizarlo**: que el precio
se pegue a una cota no es exclusivo de nuestra traducción.

### La medida que sí sirve, y lo que dice

Como la métrica del artículo mide el reparto y no la eficiencia, se añade la
que faltaba: **cuánto del ahorro alcanzable captura el mecanismo**. La
referencia es lo que la comunidad deja de pagarle a la red, es decir, por
cada kWh del vendedor `j` al comprador `i`, su techo menos su piso. El costo
de generar no entra, porque el panel genera igual se venda al vecino o se
exporte. Eso convierte el óptimo en un **problema de transporte lineal**,
coherente con H-34.

El cociente se parte en dos, porque mezcla dos preguntas: cuánta energía se
movió, y cuánto vale en promedio cada kWh movido.

**Primer resultado, y es el fuerte: el volumen es del 100,0 % en las sesenta
horas medidas, en las dos fronteras y por las dos vías.** El mecanismo mueve
siempre el lado corto. Es la forma medida de D-7.

**Segundo: todo el margen está en el emparejamiento, y ahí el resultado se
invierte entre fronteras.** Sobre 30 horas por frontera, contra un reparto
proporcional ciego que mueve el mismo volumen:

**Cifras definitivas, medidas en el servidor sobre 120 horas por frontera.**
Las de la primera tanda, con 30, decían lo mismo con más ruido.

| Sobre 120 horas por frontera | M1 | M3 |
|---|---:|---:|
| Mecanismo acoplado, media | 80,0 % | 88,5 % |
| Mecanismo acoplado, ponderado por excedente | **90,5 %** | **90,8 %** |
| Reparto proporcional ciego, media | 74,8 % | 91,1 % |
| Peor reparto del mismo volumen, media | 68,2 % | 76,1 % |
| Horas en que el juego supera al ciego | **88** | **23** |
| Horas en que empata | 18 | 43 |
| Horas en que pierde | 14 | **54** |

Descontando las horas de banda uniforme, donde el emparejamiento no puede
decidir nada, quedan **109 horas en M1 con 78,1 % contra 72,3 %** y **87 en
M3 con 84,3 % contra 87,8 %**.

**El volumen sale del 100,0 % en las 240 horas, con mínimo 100,0 %.** No es
una media que oculte casos malos: no hay ni una hora en que el mercado deje
energía sin mover.

La figura `f7_01_eficiencia_emparejamiento` lo dibuja hora a hora: el
segmento gris es el rango que el emparejamiento puede decidir, el círculo
hueco es el reparto ciego y el rombo lleno es el mercado.

Es decir: **en la frontera principal el juego aporta, y en la secundaria
no**. Encaja con la inversión de papeles que el proyecto ya tiene
documentada: en M1 hay un vendedor dominante repartiendo entre compradores
heterogéneos, que es donde emparejar decide; en M3 hay un comprador
dominante, y con un solo comprador no hay nada que emparejar salvo el orden
de los vendedores.

### En el caso base del artículo la pregunta no se puede hacer

Medido sobre sus doce horas: **en las doce el margen del emparejamiento es
cero**. Todos los compradores comparten techo, 1.250, y todos los vendedores
comparten piso, 114, de modo que cada kWh vale lo mismo venga de donde
venga y **cualquier reparto del mismo volumen vale exactamente igual**.

De ahí que el caso base no pueda distinguir mecanismos por esta vía, y de
ahí también que nuestra comunidad sí pueda: tiene dos comercializadores.

### Qué queda pendiente

1. ~~Preguntar al asesor cuál de las dos formas del término de competencia
   es la buena, y lo mismo para el término del pago.~~ **CERRADO por H-40**:
   la versión arbitrada escribe las dos formas que el proyecto ya usaba.
2. La comparación directa contra el 0,316 % **no procede**, porque no miden
   lo mismo. Y la comparación contra el 0,23 % de la versión publicada
   tampoco, por otra razón: H-40 mide que la suma de bienestares manda todos
   los precios al piso, de modo que no discrimina mecanismos de precio.
3. El lazo alternado incumple ligeramente una restricción cuando se corta en
   dos iteraciones: hasta **1,4 · 10⁻² kWh** en la peor de las 30 horas de
   M1. Es despreciable para cualquier cifra publicada, pero explica que
   alguna hora dé por encima del 100 %.
4. **El costo del solucionador acoplado no está acotado, y eso bloquea
   CAL-48.** Sobre el caso base, la hora 4 no termina en 420 segundos
   mientras la hora 1 resuelve en 47, con el mismo tamaño de problema y una
   rigidez inicial del mismo orden. No es un fallo numérico: el lado derecho
   es finito en las dos. Sobre datos reales las sesenta horas medidas
   resolvieron a unos 80 segundos, pero una corrida de 5.160 horas no puede
   apoyarse en eso. Registrado en la decisión correspondiente: la activación
   necesita presupuesto de tiempo por hora y alternativa declarada.

---

## H-40 · La versión publicada del modelo base zanja las discrepancias, y su métrica resulta degenerada en el precio

**Estado: MEDIDO y COMPROBADO el 2026-09-06 contra la fuente publicada.
Cierra dos preguntas que H-39 dejó abiertas para el asesor, y corrige dos
afirmaciones de H-39.**

Aparecieron dos artículos más del grupo que no estaban en el árbol:

1. **Chacón, Guerrero, Obando y Pantoja**, «Welfare Optimization in Energy
   Communities with P2P Markets», *IEEE Latin America Transactions*,
   vol. 23, n.º 8, agosto de 2025. Es **la versión arbitrada y publicada**
   del modelo base, y además está en la revista objetivo de esta tesis.
2. **Chacón, Benavides, Pantoja y Obando**, «Optimización de costos en un
   escenario de mercado entre pares multimicrorred con dinámicas de
   replicadores», *TecnoLógicas*, vol. 27, n.º 60, 2024. Es el precedente
   multimicrorred del mismo grupo.

### Las dos preguntas del anexo quedan respondidas

La ecuación (11) de la versión publicada dice, literalmente:

    W_i = U_i(G_i) + [ Σ_j P_ji ] / ln(π_i + 1) − β_i Σ_{k≠i} π_k Σ_j P_jk

Es decir, **las dos formas que este proyecto había elegido son las
publicadas**:

| Asunto | Lo que sigue el proyecto | La versión publicada |
|---|---|---|
| Término del pago | división por el logaritmo | **división**, ec. (11) |
| Índice de la energía en la competencia | la del comprador **ajeno** | **la del ajeno**, ec. (11) |
| Recompensa del vendedor | negativa | **negativa**, ec. (4) |
| Volumen | fijado por igualdad | **igualdad**, ec. (10) |

De modo que la traducción coincide con la fuente arbitrada en los cuatro
puntos. Lo que discrepa es el guion en Python que acompaña al modelo, y solo
en el índice de la energía. **Las dos preguntas del anexo dejan de ser
preguntas** y pasan a ser una nota documental.

### Hay dos métricas distintas, no una

H-39 afirmaba que la métrica del modelo base mide el reparto y no la
eficiencia. **Eso vale para uno de los dos documentos, no para el otro.**

| Documento | Sobre qué se calcula el error | Valor publicado |
|---|---|---|
| El documento extenso del modelo base | el ahorro del comprador y la prima del vendedor | 0,316 % de media, máximo por debajo del 6 % |
| **La versión publicada** | **la suma de los bienestares**, contra punto interior | **0,23 % de media**, por debajo del 1,00 % en 23 de las 24 horas, máximo 1,65 % a las 19:00 |

De modo que la afirmación de H-39 hay que acotarla al primero. Sobre el
segundo hace falta otra cosa, y es lo que sigue.

### La suma de bienestares siempre manda todos los precios al piso

Es un resultado analítico, no un accidente numérico. Los dos términos del
pago se cancelan exactamente, de manera que **la suma de los bienestares
depende del precio únicamente a través del término de competencia**,

    − Σ_i β_i Σ_{k≠i} π_k Σ_j P_jk

que es lineal y estrictamente decreciente en cada precio, con coeficiente
negativo para todos ellos. Un centralizado que maximice esa suma tiene, por
tanto, una única respuesta posible en la dimensión del precio: **el piso,
siempre, para todos los compradores**.

Comprobado en cinco horas de tres conjuntos de datos distintos, y la
distancia al piso sale **exactamente cero** en todas:

| Datos | Hora | Piso | Precios del centralizado |
|---|---:|---:|---|
| Caso base | 1 | 114 | 114 · 114 · 114 · 114 |
| Caso base | 9 | 114 | 114 · 114 · 114 · 114 |
| M1 | 2342 | 640,75 | 640,75 en los tres |
| M1 | 344 | 695,68 | 695,68 en los cuatro |
| M3 | 424 | 114,28 | 114,28 en los cuatro |

Y el volumen coincide al cuarto decimal con el del mercado, porque la
restricción de igualdad lo fija.

**Consecuencia.** Maximizar la suma de bienestares no sirve como referencia
para un mercado cuyo trabajo entero es fijar un precio: su respuesta es
siempre «todo el excedente al comprador». Medido en la hora 1 del caso base,
el centralizado alcanza 5,52 unidades de bienestar con los cuatro precios en
114, y el mercado −273,74 con los suyos cerca del techo. El error
normalizado sobre el bienestar asciende entonces a más del 5.000 %, no al
0,23 % publicado.

### Cómo se explica entonces el 0,23 %

Con lo medido aquí no se puede determinar, y conviene decirlo así en vez de
conjeturar. Lo que sí se puede señalar es que **el propio artículo publicado
lo advierte**: reconoce que la optimización puede tener máximos locales, que
por eso establece un criterio de desempate, y que **hay horas en las que su
método alcanza un óptimo superior al del punto interior**, concretamente a
las 20:00. Un método descentralizado que supera a su propia referencia
centralizada es señal de que la referencia no está en el óptimo global.

De modo que el 0,23 % documenta el acuerdo entre dos solucionadores que caen
en óptimos locales parecidos, y no la cercanía al óptimo global. Eso no le
resta valor al modelo, pero **sí lo descarta como medida de calidad
importable a este trabajo**, y refuerza la medida propia de H-39, que es la
eficiencia del emparejamiento sobre el ahorro alcanzable.

### El precedente del costo de transmisión

El artículo de *TecnoLógicas* de 2024 modela una comunidad repartida en
varias microrredes y **cobra una penalización, o costo de transmisión,
cuando un recurso envía energía a una microrred vecina**. Es un precedente
del propio grupo para la pregunta regulatoria que sigue abierta, la de si la
energía intercambiada dentro de la comunidad paga cargos por uso de redes.
Conviene llevarlo a esa conversación: el grupo ya ha modelado que el
transporte entre zonas se cobra.

---

## H-41 · El caso publicado ya es reproducible, y no es el que el repositorio llama caso base

**Estado: MEDIDO el 2026-09-06. Cierra un pendiente que llevaba abierto toda
la validación: hasta hoy el caso del modelo base no se podía reproducir.**

El código en Matlab del modelo base carga un libro de cálculo que **no está
en el repositorio**, de modo que su caso de estudio nunca se pudo rehacer. Lo
que el proyecto llama caso base es una **reconstrucción sintética hecha a
mano**, con perfiles escritos como constantes y gaussianas.

La versión arbitrada del modelo, en *IEEE Latin America Transactions* 23(8)
de agosto de 2025, **publica sus datos de entrada completos** en sus tablas
II y III. Con eso el caso se arma exactamente.

### Lo primero que aparece: no son el mismo caso

| | Repositorio | Publicado |
|---|---|---|
| Demanda a las 13:00 | 2,8 · 0,6 · 0,5 · 3,5 · 0,3 · 0,2 | 1,24 · 0,46 · 0,12 · 3,17 · 0,06 · 1,03 |
| Generación a las 13:00 | 4,00 · 3,81 · 2,50 · 0,97 · 0 · 0 | 2,00 · 2,60 · 0,89 · 0,30 · 0,61 · 0 |
| Demanda a las 19:00 | 3,0 · 1,4 · 1,0 · 0 · 0,6 · 0,5 | 3,34 · 0,68 · 0,25 · 1,06 · 0,07 · 0,66 |
| Generación a las 19:00 | 2,00 · 0 · 0 · 0,88 · 0 · 0 | 2,00 · 1,58 · 0,49 · 0,48 · 0,96 · 0 |
| Coeficiente cuadrático | 2,167 · 0,420 · 0 · 0 · 0 · 0 | 0,089 · 0,110 · 0,069 · 0 · 0 · 0 |
| Coeficiente lineal | 1.243,8 · 194,8 · 286,1 · 225,2 · 0 · 0 | 52 · 58 · 40 · 37 · 32 · 0 |
| Factor de competencia | 0,1 | **1** |

**No coincide ninguna de las siete filas.** Los coeficientes de costo del
repositorio son los publicados multiplicados por un factor de escala de
6,0865, con factores adicionales de 4 y 3,93 sobre el primer agente y con un
valor de 47 que no aparece en la tabla publicada. Nada de eso está
justificado en el módulo que los define.

De modo que la validación que el proyecto venía haciendo «contra el modelo
base» se hacía contra una reconstrucción, no contra el caso publicado.

### La reproducción: ocho de doce afirmaciones

Se armó el caso con los datos publicados y se enfrentó a las afirmaciones
que el artículo hace de él. Las cotas no las publica; se toman las del
modelo base, 114 y 1.250.

**A las 13:00, con excedente de generación, se reproduce todo salvo una
cosa:**

| Afirmación del artículo | ¿Se reproduce? |
|---|---|
| Vendedores 1, 2, 3 y 5; compradores 4 y 6 | **Sí** |
| Toda la demanda de la comunidad se suple dentro | **Sí**, 2,870 y 1,030 al milésimo |
| Los generadores 1, 3 y 5 se despachan al máximo | **Sí** |
| El generador 2, el más costoso, queda con exceso | **Sí**, coloca 1,820 de 2,140 |
| El comprador 4, el de mayor demanda, paga más | **No**, paga 118,30 frente a 1.131,70 |
| La recompensa de cada vendedor supera sus costos | **Sí** |

**A las 19:00, con déficit, se reproduce el volumen pero no a quién se
raciona:**

| Afirmación del artículo | ¿Se reproduce? |
|---|---|
| Vendedores 2, 3 y 5; compradores 1, 4 y 6 | **Sí** |
| Todos los vendedores se despachan en su totalidad | **Sí**, 2,030 kWh |
| El comprador 1 cubre toda su demanda dentro | **No**, recibe 0,790 de 1,340 |
| Los compradores 4 y 6 no la cubren | **No**, la cubren íntegra |
| La recompensa de cada vendedor supera sus costos | **Sí** |

### Lo que fallan las cuatro es siempre lo mismo

**H-42 encontró la causa el mismo día, y no es la que este hallazgo suponía.**
Lo que sigue describe correctamente el síntoma, pero la explicación buena
está allí: las cuatro se deben a que la dinámica usaba una forma del término
de competencia **sin precios**, y no la de la ecuación publicada. Con la
forma publicada, las dos afirmaciones centrales sí se reproducen.

Las cuatro discrepancias caen en la dimensión del precio y del reparto entre
compradores, que es **exactamente la que H-33 y H-34 habían mostrado
degenerada**. Las que se reproducen son las de volumen, despacho y
cobertura de costos, que son las robustas.

Y para las de las 19:00 se puede afirmar algo más fuerte que «difieren». Con
banda uniforme el excedente de la comunidad es el ancho por el volumen, y el
volumen es el lado corto en las dos asignaciones. Medido:

| Reparto del déficit de 0,550 kWh | Excedente de la comunidad |
|---|---:|
| El del artículo: el comprador 1 pleno, se raciona a 4 y 6 | **2.306,08** |
| El nuestro: 4 y 6 plenos, se raciona al comprador 1 | **2.306,08** |

**Idénticos.** Las dos asignaciones son óptimas para la comunidad y lo que
las separa es a quién le toca el racionamiento, que el problema de
transporte deja indeterminado. No es que una esté bien y la otra mal.

### La prueba de sensibilidad del artículo, en la dirección correcta

El artículo sube el factor de competencia del agente 6 de 1 a 100 y publica
que su precio sube en 25,22. Nuestra reproducción también lo sube, pero
121,29, es decir unas cinco veces más, y sin que cambie la energía que ese
agente recibe. La dirección se reproduce; la magnitud no.

### Las discrepancias no vienen de las cotas que se eligieron

Es la objeción obvia, porque el artículo arbitrado no publica las cotas, y
se midió antes de concluir nada. Con tres bandas muy distintas el patrón
sale **idéntico**:

| Cotas | 13:00 | 19:00 |
|---|---|---|
| [114; 1.250] | comprador 4 a 118,3 · comprador 6 a 1.131,7 | comprador 1 cubre el 59,0 % |
| [50; 1.650] | comprador 4 a 51,0 · comprador 6 a 1.599,0 | comprador 1 cubre el 59,0 % |
| [280; 906] | comprador 4 a 289,4 · comprador 6 a 616,6 | comprador 1 cubre el 59,0 % |

En los tres casos el comprador grande queda pegado al piso y el pequeño
arriba, y **la cobertura del comprador racionado es exactamente la misma**,
59,0 %, lo que vuelve a confirmar que el reparto no depende de las cotas. De
modo que las cuatro discrepancias son estructurales y no un artefacto de la
banda elegida.

### De paso, la evidencia de CAL-48 sobre datos publicados

El mismo barrido corrió la vía alternada con las cotas del modelo base, y el
contraste es el que CAL-48 venía sosteniendo sobre datos propios, ahora
sobre los del artículo:

| Vía | 13:00 | 19:00 |
|---|---|---|
| Acoplada | 118,3 y 1.131,7, **las dos interiores** | 714,7 · 930,7 · 854,6, **las tres interiores** |
| Alternada | **114,0 y 1.250,0**, las dos en una cota | **114,0** · 1.210,4 · **114,0** |

La vía alternada clava cinco de los seis precios exactamente en una cota, y
además deja un incumplimiento de restricción visible, con un comprador
cubierto al 100,1 %. La acoplada no.

---

## H-42 · El modelo publicado y el modelo programado no son el mismo, y esta traducción seguía al programado

**Estado: MEDIDO el 2026-09-06. Es el hallazgo de mayor alcance de la tanda,
porque explica de una vez las cuatro discrepancias de H-41 y obliga a
decidir qué se traduce.**

El compromiso del trabajo era reproducir el modelo base tal como funciona y
solo después adaptarlo. H-41 dejó cuatro afirmaciones del artículo sin
reproducir, todas de precio y reparto. Buscando la causa apareció algo más
grande.

### Tres formas del mismo término, y las tres están en las fuentes

El bienestar del comprador incluye un término que penaliza competir con los
demás. Las fuentes del modelo base lo escriben de tres maneras distintas:

| Nombre | Expresión | Dónde vive |
|---|---|---|
| Agregada | `media(β) · Σ_j P_ji` | lo que esta traducción usa, por defecto |
| Del código | `(Σ_{k≠i} β_k) · Σ_j P_ji` | **la línea activa** de `JoinFinal.m` |
| Publicada | `β_i · Σ_{k≠i} π_k Σ_j P_jk` | **la línea comentada** del mismo fichero, y la ecuación (11) de la versión arbitrada |

La diferencia entre las dos primeras es un factor, y la diferencia con la
tercera es de naturaleza: **en las dos primeras el término no contiene
ningún precio**. Un comprador no puede responder al precio de los demás
porque el precio de los demás no aparece en su aptitud.

Eso importa porque el artículo arbitrado enuncia entre sus contribuciones,
con estas palabras, «incluir un factor de competencia que permite a los
consumidores responder a los precios establecidos por otros, según su
necesidad energética». **En las dos primeras formas esa contribución no está
implementada.**

### Un error de traducción, medido, que no explica la inversión

La forma del código no es la que esta traducción usa. El fichero en Matlab
define el factor como un **vector fila**, de modo que `β · matriz` es un
producto vector por matriz y da `Σ_{k≠i} β_k`, uniforme entre compradores.
Con factor uniforme eso vale `β·(I−1)`, y la traducción usa `media(β)`, es
decir **le falta el factor (I−1)**, con I compradores.

De paso cae una afirmación que llevaba desde el 17 de abril en el registro
de auditoría del módulo: decía que la indexación lineal de Matlab producía
un término nulo para el primer comprador y `β` para los demás. **Es falso**:
el factor es un vector fila y el producto es el ordinario.

Corregido y medido sobre el caso publicado, **no cambia nada de fondo**:

| Forma | 13:00 | 19:00 |
|---|---|---|
| Agregada | comprador 4 a 118,3 · comprador 6 a 1.131,7 | el comprador 1 cubre el 59,0 % |
| Del código, con el factor corregido | **118,3 · 1.131,7**, idéntico | 701,0 · 941,6 · 857,5, y el 1 cubre **el mismo 59,0 %** |

A las 13:00 coinciden al decimal, porque con dos compradores el factor vale
uno. A las 19:00 los precios se mueven algo y **el reparto no se mueve**.

### La forma publicada sí reproduce el artículo

Y lo hace en las dos afirmaciones que H-41 había dejado caídas:

| Forma | ¿El comprador grande paga más, a las 13:00? | ¿El comprador 1 se cubre entero, a las 19:00? |
|---|---|---|
| Agregada | **No**, 118,3 contra 1.131,7 | **No**, 59,0 % |
| Del código | **No**, 118,3 contra 1.131,7 | **No**, 59,0 % |
| **Publicada** | **Sí**, 1.136,0 contra 114,0 | **Sí**, 100,0 % |

Contadas las doce afirmaciones que H-41 enfrenta, la forma publicada
reproduce **once**, frente a las ocho de la agregada y las ocho de la del
código. La única que sigue cayendo es menor: el artículo dice que a las
19:00 el comprador 6 no cubre su demanda dentro de la comunidad, y aquí la
cubre.

**Reproducido en otra máquina.** Las tres cuentas, 8, 8 y 11, salen iguales
en un servidor Linux con Python 3.10 que en la máquina de trabajo con
Windows y Python 3.13, y los valores del bienestar de la compuerta coinciden
hasta el último decimal. La traducción no depende de la plataforma.

### Pero la prueba de sensibilidad del artículo se invierte

Y hay que decirlo, porque es lo que impide cerrar el asunto con la forma
publicada sin más. El artículo sube el factor del agente 6 de 1 a 100 y
publica que **ese agente sube su precio** en 25,22 y **recibe más energía**,
de 0,2630 a 0,5316 kilovatios hora.

| Forma | Precio del agente 6 | Energía que recibe |
|---|---|---|
| Agregada | sube 121,29 · dirección correcta, cinco veces la magnitud | no cambia |
| Del código | sube 392,53 · dirección correcta, quince veces la magnitud | no cambia |
| **Publicada** | **baja 1.022,00** · dirección contraria | **baja** de 0,660 a 0,110 |

**Ninguna de las tres reproduce el 25,22 publicado.** Las dos que aciertan la
dirección se pasan por un factor de cinco y de quince, y la que reproduce
todo lo demás va al revés.

Tiene explicación, y es que el factor entra en la ecuación publicada
**multiplicando el castigo**: subirlo penaliza más a ese comprador, su
aptitud cae y su precio con ella. La narración del artículo lo trata en
cambio como una medida de urgencia, que debería empujar el precio hacia
arriba. **La ecuación publicada y la narración del artículo no coinciden en
el papel de ese factor.**

De modo que ninguna de las tres formas reproduce el experimento de
sensibilidad. Conviene llevarlo a la conversación con el asesor junto con lo
demás.

### Por qué las dos primeras invierten el resultado

No es un accidente numérico. En las dos, el castigo es proporcional a **la
energía propia** del comprador. Quien más compra recibe más castigo, su
aptitud baja y su precio cae hacia el piso. De ahí sale exactamente lo que
mide H-41: el comprador grande pegado al piso y el pequeño arriba.

En la forma publicada el castigo depende del **precio y la energía de los
demás**, no de la propia, y entonces el comprador con más necesidad puede
pujar sin castigarse a sí mismo.

### Lo que esto significa para el trabajo

1. **El modelo publicado y el modelo programado no son el mismo modelo.** No
   difieren en un coeficiente: difieren en si existe o no el mecanismo de
   respuesta al precio ajeno.
2. **Esta traducción venía siguiendo al programado**, y encima con un factor
   de menos. De modo que la afirmación de que el proyecto «reproduce el
   modelo base» hay que acotarla: reproduce el código, no el artículo.
3. Las cuatro discrepancias de H-41 **tienen una sola causa**, y no son un
   defecto de la traducción sino de qué fuente se tradujo.
4. La función de bienestar que el proyecto **reporta** ya usa la forma
   publicada, mientras la dinámica usa la agregada. Es decir, **hoy el
   código informa de un bienestar que no corresponde al que su propia
   dinámica persigue**. Adoptar la forma publicada alinea las dos.

### La decisión, y la cautela que la condiciona

**Se recomienda adoptar la forma publicada**, porque es la especificación
arbitrada, es la única que reproduce el caso publicado y es la única que
implementa una contribución que el artículo declara.

**La cautela era que con la forma publicada los precios del caso publicado
cayeron pegados a las cotas**, que es justo el defecto que la vía acoplada
venía a corregir. Medido sobre 120 horas por frontera en el servidor,
**la cautela se confirma**:

| Frontera | Precios pegados a una cota, agregada | Publicada |
|---|---:|---:|
| M1 | 46,3 % | **55,6 %** |
| M3 | 7,5 % | **24,2 %** |

En M1 pega nueve puntos más y en M3 **más del triple**. Y no es un promedio
que oculte compensaciones: en M3 hay 32 horas donde la publicada pega más y
**ninguna** donde pegue menos.

**Rectificación.** Con la primera de las dieciséis particiones, ocho horas,
las dos formas daban 46,4 % y dije que la cautela no se materializaba. Era
una coincidencia de esa muestra. Con las 120 horas no se sostiene.

### Lo que la forma publicada no toca, y lo que sí

| | M1 agregada | M1 publicada | M3 agregada | M3 publicada |
|---|---:|---:|---:|---:|
| Volumen transado | 498,71 | 498,71 | 329,61 | 329,61 |
| Eficiencia | 80,1 % | 79,3 % | 88,6 % | 88,8 % |
| Tajada del vendedor | 65,1 % | **75,9 %** | 19,8 % | **33,3 %** |
| Precios pegados | 46,3 % | 55,6 % | 7,5 % | 24,2 % |

El volumen coincide al orden de 10⁻⁷ y 10⁻¹⁰ kilovatios hora, y la
eficiencia se mueve menos de un punto. **Lo que la forma decide es el
reparto**, y lo mueve mucho: la tajada del vendedor sube once puntos en M1 y
trece y medio en M3. Es exactamente lo que predice H-33.

### La decisión: se mantiene la forma agregada

**Tomada por el autor el 2026-09-06**, sobre las 240 horas medidas, con el
criterio de cuál opera mejor como mercado. Queda formalizada en
`docs/adr/0049-cal49-termino-de-competencia.md`.

Se sostiene en tres cosas. El beneficio de la comunidad es un empate, con
−1,44 % en M1 y +0,38 % en M3, de modo que no se pierde nada; el reparto
queda mucho más equilibrado, 51/49 en M1 frente al 85/15 de la forma
publicada; y se pegan menos precios a las cotas, en las dos direcciones y en
las dos fronteras.

El único criterio en que la publicada gana, dejar menos vendedores bajo su
piso, **no cuenta**, porque H-43 establece que la causa de eso es otra: el
precio se acota con el piso mínimo de la comunidad y no con el de cada
vendedor. Arreglarlo donde corresponde elimina esa ventaja.

**Lo que la decisión cuesta, y hay que declararlo.** El trabajo no puede
afirmar que reproduce el modelo publicado: con la forma agregada reproduce
ocho de las doce afirmaciones, frente a once. Y el mecanismo de respuesta al
precio ajeno, que el artículo declara entre sus contribuciones, no queda
implementado. Lo que sí puede afirmar, que es lo que pide el primer objetivo
específico de la propuesta, es que analizó el modelo de referencia, encontró
que sus fuentes discrepan, midió las tres formas sobre datos reales y eligió
con evidencia.

La forma publicada queda implementada, medida y alcanzable, y el documento
la presenta como la alternativa fiel a la fuente arbitrada.

La forma del código no es una alternativa: es la corrección de higiene de la
agregada, conviene aplicarla, y ya está medido que no cambia ninguna
conclusión.

### Lo aplicado hasta ahora

Las tres formas quedan disponibles en el solucionador acoplado, **con la
histórica por defecto**, de modo que ninguna cifra publicada se mueve
mientras no se decida. El bloque alternado ya tenía dos de las tres.

---

## H-43 · Hay vendedores que salen perdiendo: el precio cae por debajo de su propio piso

**Estado: MEDIDO el 2026-09-06 sobre 120 horas por frontera. Es un defecto
del mecanismo, no de la traduccion, y no lo causa la forma del termino de
competencia.**

Apareció al mirar el reparto del excedente entre quien vende y quien compra.
En algunas horas **la tajada del vendedor sale negativa**, lo que significa
que el precio acordado quedó por debajo del piso de algún vendedor: ese
vendedor habría ganado más exportando su energía a la red que vendiéndosela
al vecino.

| Frontera | Horas con vendedor bajo su piso | La peor |
|---|---:|---:|
| M1 | **7 de 120**, con la forma agregada | −168,9 % |
| M1 | 3 de 120, con la forma publicada | −168,9 % |
| M3 | **33 de 120**, con la forma agregada | −186,4 % |
| M3 | 31 de 120, con la forma publicada | −186,4 % |

En la frontera secundaria eso es **más de una hora de cada cuatro**.

### No lo causa la forma del término de competencia

Es lo primero que se comprobó, y queda descartado: de las horas afectadas,
31 de 33 en M3 y 3 de 7 en M1 lo están con las dos formas, y **la publicada
no añade ninguna**. Al contrario, arregla cuatro en M1 y dos en M3.

### La causa es que el precio se acota con el piso de la comunidad

El precio de cada comprador se recorta al intervalo entre **el menor de los
pisos de los vendedores activos** y su propio techo. Cuando los vendedores
tienen pisos distintos, un precio admisible para el de piso más bajo puede
estar por debajo del piso de otro.

Las horas afectadas lo confirman: todas tienen **muchos vendedores y pocos
compradores**, J entre 3 y 4 con I entre 1 y 2. Con un solo comprador el
precio es uno solo, y tiene que servir a la vez para vendedores con
alternativas externas distintas.

### Qué habría que hacer

El proyecto ya tiene la pieza: `piso_por_vendedor` calcula el piso de cada
uno por separado. Lo que falta es que el mecanismo lo respete, y hay dos
salidas que conviene medir antes de elegir:

1. **Filtrar la entrada.** Un vendedor cuyo piso quede por encima del precio
   no participa esa hora. Es la restricción de participación en su forma
   literal, y reduce el volumen.
2. **Acotar por pareja.** El precio de la pareja se recorta al piso de ese
   vendedor concreto y no al mínimo comunitario. Conserva el volumen pero
   rompe el precio único por comprador.

La segunda encaja mejor con lo que ya sabemos, porque el volumen es el lado
corto y el excedente el ancho de la banda por la energía, de modo que
tocar el volumen sería lo caro.

**No invalida lo publicado**, porque el excedente agregado y el volumen no
dependen de esto, pero **sí toca el reparto por agente**, que es lo que se
usa para la deserción y para el índice de equidad.

---

## H-44 · La dinámica del modelo base no deriva de su bienestar publicado

**Estado: MEDIDO el 2026-09-06, con compuerta. Es una propiedad del modelo de
origen, no un defecto de esta traducción.**

Salió al preguntarse por qué la función que informa del bienestar del
comprador usa una forma del término de competencia y la dinámica usa otra.
La respuesta resultó ser más de fondo que la pregunta.

### Lo medido

El bloque de precios mueve cada precio según una aptitud. Esa aptitud **sí
es un gradiente**, pero no del bienestar que el proyecto reporta:

| | Valor sobre cuatro compradores |
|---|---|
| Aptitud que mueve los precios | −2,9215 · −1,3158 · −1,9339 · −1,2173 |
| Gradiente del bienestar del **documento extenso** | −2,9215 · −1,3158 · −1,9339 · −1,2173 |
| Gradiente del bienestar de la **versión arbitrada** | −0,000376 · −0,000151 · −0,000213 · −0,000161 |

La primera coincide con la segunda hasta la precisión del cálculo, y difiere
de la tercera **por un factor de 7.778**.

De modo que la aptitud se descompone así:

    aptitud = gradiente del bienestar del documento extenso
              − competencia            ← no es el gradiente de nada
              + señal de restricción    ← tampoco

### Y el término de competencia no entra en el gradiente, en ninguna forma

Es el segundo hallazgo de la misma medición, y explica por qué el asunto de
CAL-49 no tiene efecto por esta vía: **las tres formas dan exactamente el
mismo gradiente**, porque en ninguna de las tres interviene el precio propio
del comprador. El término aparece en la aptitud restado a mano, no derivado.

### Qué significa

**La dinámica del modelo base no maximiza su bienestar publicado.** No es que
lo aproxime: persigue el gradiente de otra cosa, y encima le añade dos
términos que no son gradientes. Está así en el fichero original de la
autora, y esta traducción reproduce las dos piezas correctamente por
separado: la compuerta del bienestar demuestra que reproduce la ecuación (11)
al bit, y la huella del paso horario demuestra que la dinámica reproduce el
Matlab.

Lo que no existe, ni aquí ni en el original, es la correspondencia entre las
dos.

### Qué se hizo, y qué no

**No se cambia ninguna fórmula.** Inventar una cuarta función de bienestar
que sí case con la dinámica sería peor, porque no correspondería a ninguna
fuente. Las dos piezas se quedan como están, fieles cada una a la suya.

**Se cambió el rótulo de la salida.** La comparación imprimía esa suma bajo
un encabezado de «bienestar de optimización» y una nota que afirmaba que
«los valores W guían la dinámica de replicador». Eso es literalmente lo que
esta medición desmiente. Ahora dice lo que es: la definición de bienestar de
la versión arbitrada evaluada en el equilibrio, que no es lo que la dinámica
maximiza ni una medida de calidad, con el reenvío a H-39 para la que sí lo
es.

**Se añadió la compuerta** `tests/gate_h44_aptitud_gradiente.py`, que fija
las tres relaciones y además comprueba que la fórmula de la aptitud sigue
siendo la que el núcleo tiene escrita. Si alguien «arregla» uno de los dos
lados, la compuerta falla antes de que el documento quede afirmando algo
falso.

### Dónde va

Al **capítulo del modelo**, donde se presentan el bienestar y la dinámica. Es
del tipo de resultado que justifica un trabajo de validación: no se descubre
leyendo el artículo, sino implementándolo y midiendo.

---

## Dónde queda cada hallazgo de la tanda de las recomendaciones (2026-09-05/06)

Los siete salieron de revisar `Recomendaciones.txt` contra el código y los
artefactos. Ninguno se descubrió leyendo: todos se midieron.

**H-30 · Las cotas del juego son constantes escritas a mano.** Da origen a
**CAL-47**. Declarado ya en el capítulo 5, en la caja de trampas ampliada
por C-135, que ahora distingue cuatro papeles del «precio al que la red
compra» en vez de tres. La corrección al código entra en la corrida
canónica pendiente.

**H-31 · El índice de desigualdad mide la dotación y no el mecanismo.**
Toca el capítulo 12, que está por escribir, de modo que **no corrige nada
publicado**: fija el encargo. El documento publicará dos medidas con
papeles distintos, lo ganado por kWh aportado como principal y el índice
sobre lo que cada mecanismo reparte para ordenar los siete.

**H-32 · La condición inicial del bloque comprador.** **No entra en el
documento.** Es un defecto latente que solo aparece con la banda estrecha,
y como el documento aún no publica ningún resultado con banda estrecha, no
hay nada que corregir. Queda aquí como condición previa de CAL-47 y como
aviso para quien vuelva a tocar el solucionador.

**H-33 · El excedente es el ancho de la banda por la energía.** Va al
**capítulo 6**, donde se presenta el mecanismo, y no al de robustez. Es la
propiedad que ordena el capítulo entero y la que explica por qué el
ordenamiento entre mecanismos sobrevive al precio degenerado.

**H-34 · Con datos reales el reparto es un programa lineal.** Va al mismo
sitio que H-33 y al **capítulo 7**, donde vive la verificación del
solucionador. Convierte el precio degenerado, el ciclo de período dos y la
indiferencia del agregado al juego en una sola propiedad bien entendida en
vez de tres rarezas.

**H-35 · Ritmos semanales opuestos entre las dos fronteras.** Va al
**capítulo 10**. Cumple un compromiso explícito de la Actividad 4.1 de la
propuesta que estaba sin cumplir.

**H-36 · La escala real de las instituciones.** Refuerza H-7 y va donde ya
está declarado el asunto de la frontera, es decir el **capítulo 4** y el
anexo de lo no representado. La ingesta completa de esos datos queda como
trabajo futuro.

---

## Dónde quedó cada hallazgo de esta tanda

**H-26 · La serie de Mariana en la frontera secundaria no es bruta.** Toca
cifras publicadas y por eso está **declarado en el capítulo 3**, con la
excepción escrita donde el texto enumera los tipos de medidor. Se corrige
con la próxima corrida canónica.

**H-27 · El cuarto medidor de CESMAG publica su tensión bajo dos escalas.**
**No entra en el documento.** Ese medidor no participa en ninguna de las dos
fronteras, de modo que ninguna cifra publicada depende de él y mencionarlo
solo añadiría ruido a un capítulo que ya es largo. Queda aquí, que es donde
sirve: como aviso para quien vuelva a tocar el árbol de datos y como la
primera evidencia directa del asunto abierto de la escala de los
transformadores.

**H-28 · El paso horario sobrestima el autoconsumo.** Toca la magnitud
absoluta de dos índices publicados, de modo que **se declara dos veces**: en
la lista de decisiones que sesgan del capítulo 3, como la octava, y en la
subsección del paso de tiempo del capítulo de robustez, con su figura.

**H-29 · La cascada de limpieza cuenta pasos y no horas.** **CERRADO el
2026-09-05 y no entra en el documento.** Se arregló en el código: los dos
límites se expresan en horas y el conteo se deriva del propio eje. A paso
horario el arreglo es inerte, comprobado con `max|dif| = 0` sobre las
diez series contra el caché, de modo que no hay nada que contar al lector:
ninguna cifra publicada cambia y el defecto solo habría aparecido en una
corrida subhoraria que todavía no existe.
