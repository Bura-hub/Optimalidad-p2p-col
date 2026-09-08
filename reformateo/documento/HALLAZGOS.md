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

**Estado: CORREGIDO el 2026-09-06 por C-136, primera parte, con compuerta en
verde. Descubierto el mismo día al estrechar la banda en la sonda de CAL-47.
El arranque se reparte ahora sobre la banda y no sobre el techo, y solo
cuando la forma original cae fuera, de modo que el caso base y el canon
quedan idénticos bit a bit. AMPLIADO el 2026-09-07 por H-45: con techos
distintos el arranque tiene que caer dentro de la banda de CADA comprador, no
dentro de la del techo mayor; ver C-143.**

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

**Estado: CORREGIDO el 2026-09-06 por C-136, segunda parte, con compuerta en
verde. Afecta al reparto, nunca al agregado. El paso de integración se
comprueba en vez de heredarse: la comprobación es OPCIONAL y por defecto está
desactivada, de modo que el comportamiento sin activarla es exactamente el
histórico. **La corrida canónica debe activarla.****

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

**Una cuarta discrepancia, hallada el mismo día al inventariar las
figuras.** Las dos publicaciones tampoco comparten la recompensa del
vendedor. La arbitrada la escribe negativa y con logaritmo en el
denominador, que es lo que este proyecto implementa; el documento extenso la
escribe como el producto del precio por la energía, que es lo natural. Y las
barras de «costos frente a recompensa» que el artículo arbitrado dibuja para
sus dos horas de ejemplo **no son ninguna de las dos**: su texto las define
como la energía transada por su precio, que es la magnitud de la restricción
de cobertura de costos. De modo que en el mismo artículo conviven dos
recompensas distintas, la de la ecuación y la de la figura.

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

**RECTIFICACIÓN del 2026-09-06, y es importante.** La tabla de arriba
compara contra el artículo arbitrado, y **esa no era la comparación buena**.
El modelo base tiene dos publicaciones con casos y parámetros distintos, y
el repositorio sigue al **documento extenso**, no al arbitrado. Comprobado:

| | Repositorio | Documento extenso |
|---|---|---|
| Coeficiente cuadrático | 2,1668 · 0,420 · 0 · 0 · 0 · 0 | **idéntico** |
| Coeficiente lineal | 1.243,8 · 194,8 · 286,1 · 225,2 · 0 · 0 | **idéntico** |
| Cotas de precio | 114 y 1.250 | **idénticas** |
| Factor de competencia | 0,1 | **idéntico** |

El escalado por 6,0865 con los factores de 4 y 3,93, que este hallazgo llamó
injustificado, **es exactamente la forma en que el fichero en Matlab codifica
la Tabla I del documento extenso**. La afirmación de que «no está
justificado» era mía y era falsa.

**Lo que sí se sostiene** es la última fila: los perfiles de demanda y
generación del repositorio son una reconstrucción sintética y **no coinciden
con ninguna de las dos publicaciones**. Medido a las 14:00, el límite de
generación del repositorio da 2,844 · 3,303 · 2,308 · 1,193 frente al
2,844 · 3,738 · 0,539 · 0,624 de la tabla del documento extenso, y los
papeles salen distintos: el repositorio hace vendedores al 2 y al 3, y la
publicación al 1 y al 2. El primer agente coincide porque su límite es la
raíz de la ecuación de costos y no depende de la hora.

De modo que la validación «contra el modelo base» se hace hoy con **los
parámetros correctos y unos perfiles inventados**.

**Y hay una consecuencia que abre trabajo**: el documento extenso publica
sus resultados en tablas, con la matriz de flujos, los precios y la energía
por comprador para las 14:00 y las 22:00. Eso permite una comparación
**numérica**, no solo de afirmaciones cualitativas como la que este hallazgo
hizo contra el artículo arbitrado.

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

**Estado: CORREGIDO el 2026-09-07 por C-151, con compuerta y verificado
contra la sonda. Es un defecto del mecanismo, no de la traduccion, y no lo
causa la forma del termino de competencia. La causa resulto ser la
heterogeneidad de comercializador, que da pisos dispares a los vendedores;
ver H-47 y H-48.**

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

### Cómo hay que implementarlo en el motor, con la trampa señalada

**Estado de la implementación al 2026-09-07:** el criterio está corregido y
medido en la sonda (C-149), el piso por vendedor ya llega al juego y a la
liquidación (C-148), y **la restricción de participación sigue sin estar en
el motor**. Lo que sigue es el diseño, con la trampa que se encontró al
prepararlo.

**La trampa.** La forma obvia de implementarlo es resolver con el conjunto
reducido de vendedores, es decir quitar al retirado de la lista. **No se debe
hacer así.** La liquidación calcula lo que cada vendedor exporta a la red
recorriendo únicamente los vendedores de esa lista, de modo que un vendedor
ausente de ella **desaparece de la cuenta**: su excedente no se exporta, se
evapora.

Es exactamente el mismo defecto que la auditoría encontró en la sonda del
escenario, donde la factura sin mercado excluía a los retirados y sesgaba la
comparación en un 76,8 %. Dos apariciones del mismo error en el mismo día
bastan para darle nombre: **quien sale del mercado no sale de la
contabilidad.**

**La forma correcta.** Resolver con el conjunto reducido, y después
**reincrustar el resultado en la matriz del tamaño original poniendo a cero
las filas de los retirados**, conservando la lista de vendedores intacta.
Así:

- el retirado exporta todo su excedente a la red, que es lo que hace en la
  realidad;
- su prima sale cero, que es correcto porque no vendió;
- y nada de lo que hay aguas abajo cambia de forma.

**Por qué no hace falta hacerlo opcional.** Con un piso escalar, todos los
vendedores tienen el mismo piso y el precio ya está acotado por debajo a ese
valor, de modo que el ingreso ponderado nunca queda por debajo y **no se
retira nadie jamás**. La restricción es automáticamente inerte cuando las
cotas son uniformes, que es el caso del modelo base y del caso sintético. No
necesita bandera: se activa sola cuando los pisos difieren, que es justo
cuando hace falta.

**Lo que hay que verificar al implementarlo**, y no es poco: que el caso
sintético y el modelo base queden idénticos bit a bit; que la hora 2387 de la
frontera principal reproduzca lo que la sonda mide, es decir un vendedor
retirado, el mismo volumen y una prima de +994,6; y que la suma de lo
exportado más lo transado siga cuadrando con el excedente neto de cada
agente.

### Las dos salidas que se consideraron

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

### Cuánto cuesta la primera salida, medido el 2026-09-07

Al construir el lector único de hora apareció el número, y es grande. La
sonda del paso a paso ya aplica la primera salida, la de filtrar la entrada,
y la de eficiencia no. En la hora 37 de la frontera principal la
participación **retira tres vendedores y el volumen cae de 3,902 a 1,424
kilovatios hora**, un 63 %.

**Consecuencia que hay que declarar:** las cifras de eficiencia de H-39, el
80,0 % y el 88,5 %, están calculadas **sin** la restricción de
participación. En las horas donde muerde, sobrestiman el volumen que el
mercado movería si ningún vendedor aceptara vender por debajo de su
alternativa. No invalida la comparación entre las dos vías del solucionador,
que se hizo con el mismo criterio en las dos, pero sí acota lo que significa
ese «100 % de volumen».

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

## H-45 · Tres de cada cuatro compradores pagan exactamente su techo, y su ahorro es cero

**Estado: CORREGIDO el 2026-09-07 por C-143, con compuerta. La causa que
este hallazgo daba por buena resultó ser un síntoma; la real está en el
arranque y se explica abajo. Queda abierta la pregunta regulatoria de si el
techo debe ser uno solo, que es del asesor y no del código.**

Salió al construir la factura comparada, que es lo que se pidió en la
reunión: qué le liquida la normativa base a cada institución y qué le
liquidaría el mercado. Sobre el 2 de mayo de 2025 en la frontera principal:

| Institución | Compra dentro | Beneficio |
|---|---:|---:|
| Mariana | 16,84 kWh | **0,0 COP** |
| UCC | 16,84 kWh | **0,0 COP** |
| CESMAG | 15,15 kWh | 353,8 COP |

Mariana y la UCC **participan del mercado y no ganan nada**. No es que no
compren: compran casi diecisiete kilovatios hora cada una y su factura sale
idéntica a la que tendrían sin mercado.

### La causa está en el código, y es una que ya estaba señalada

El precio de cada comprador, hora a hora:

| Hora | Mariana | UCC | HUDN | CESMAG |
|---|---|---|---|---|
| 08:00 a 15:00 | 731,1 sobre techo 731,1 | 731,1 sobre 731,1 | 731,1 sobre 731,1 | 756,1 sobre **777,2** |

Los tres primeros pagan **exactamente su techo**, en las ocho horas. El
único que consigue precio interior es CESMAG, y la razón es que **tiene otro
comercializador**: su techo es 777,2 en lugar de 731,1.

El mecanismo es este. El solucionador acoplado recibe **un techo escalar**,
el mayor de todos los compradores de esa hora, y el techo propio de cada uno
se aplica **después, como recorte**. A los tres que comparten el techo más
bajo el precio les sale por encima y el recorte los deja **justo encima de
él**, que es donde el ahorro vale cero.

Es la consecuencia práctica de algo que el inventario del proyecto ya había
señalado: la vía alternada admite techo vectorial y la acoplada no.

### Por qué importa

1. **El mercado no les da nada a dos de las cinco instituciones**, y sin
   embargo aparecen como participantes. En un análisis de deserción eso es
   exactamente el caso que hay que detectar.
2. **El excedente comunitario del día, 2.821 pesos en la frontera principal,
   se lo llevan dos agentes**: Udenar 2.275 como vendedora y CESMAG 354 como
   compradora. Los otros tres se reparten 192.
3. **Que la única beneficiada del lado comprador sea la del otro
   comercializador no es una casualidad**, es el efecto de tener dos techos.
   Refuerza lo que CAL-47 estableció: la banda no es uniforme porque hay dos
   comercializadores, y ahí es donde el emparejamiento decide algo.

### Qué habría que hacer

Pasar el techo por comprador **al solucionador acoplado**, en lugar de
aplicarlo como recorte posterior. La vía alternada ya lo admite desde
CAL-47; la acoplada, no. Mientras no se haga, cualquier hora con dos techos
distintos deja a los compradores del techo bajo sin excedente, por
construcción y no por competencia.

**No invalida el agregado**, por la identidad de H-33: el excedente total es
el ancho de la banda por la energía. Lo que cambia es **a quién le toca**, y
eso es justo lo que la factura comparada existe para enseñar.

### CORREGIDO el 2026-09-07, y la causa no era la que aquí se dijo

Al implementar el arreglo apareció que **el recorte posterior no era la
causa**, sino un síntoma. La causa está un paso antes, en el arranque.

El bloque comprador arranca repartiendo el presupuesto de los techos entre
los compradores y el jugador virtual. Cuando esa forma cae fuera de la banda
se aplica el respaldo de C-136, que reparte la banda del **techo mayor**.
Con las cotas de permuta, en la hora de las diez de la frontera principal,
eso da un arranque en 760,3 (COP/kWh) para una banda que empieza en 692,7 y
termina en 731,1 para tres de los cuatro compradores. **Nacen por encima de
su propio techo.** Ahí el peso de barrera vale cero, su precio no se mueve
en toda la integración, y el recorte los deja exactamente en 731,1, que es
donde el ahorro vale cero.

Es la patología de H-32 por el extremo de arriba, y solo aparece cuando se
juntan las dos cosas: la banda estrecha de CAL-47 y dos comercializadores.

**El arreglo, en C-143:** el techo entra al solucionador como vector, y cada
comprador arranca dentro de **su** banda. Con techos iguales las dos formas
coinciden y el resultado es idéntico bit a bit.

### Lo que cambia, medido

Cuatro regímenes del techo sobre las mismas horas, evaluando el ahorro
siempre contra el techo **real** de cada institución, que es lo único que
los hace comparables. Muestra de 60 horas activas al azar por frontera.

| Frontera | Régimen | Volumen (kWh) | Excedente (COP) | Horas-comprador sin ahorro | Con pérdida |
|---|---|---:|---:|---:|---:|
| M1 | escalar, lo de antes | 214,73 | 45.016,2 | **88** | 0 |
| M1 | **techo propio** | 214,73 | **46.596,6** | **0** | 0 |
| M1 | techo único bajo | 214,73 | 45.016,1 | 0 | 0 |
| M1 | techo único alto | 214,73 | 45.016,2 | 88 | **88** |
| M3 | escalar | 131,68 | 80.292,3 | 2 | 0 |
| M3 | **techo propio** | 131,68 | 80.205,3 | **0** | 0 |
| M3 | techo único bajo | 131,25 | 80.080,1 | 0 | 0 |
| M3 | techo único alto | 131,68 | 80.292,3 | 2 | 2 |

Tres cosas que conviene separar.

**Primera, el volumen apenas se mueve, y no por el precio.** Sobre 60 horas
la mayor diferencia entre regímenes era de 5,2·10⁻¹³ (kWh), es decir
precisión de máquina. **Sobre 400 horas deja de serlo**: la frontera
principal pasa de 779,23 (kWh) con el régimen anterior a 778,16 con el techo
propio, un 0,14 %.

La causa no es el precio sino la restricción de participación: al cambiar
los precios, se retiran vendedores distintos. No contradice D-7, porque el
volumen sigue siendo el mínimo de los dos lados **dado quién participa**; lo
que cambia es quién participa. Ver H-43, con el que esto se enlaza.

**Segunda, el arreglo elimina las horas sin ahorro.** Las 88 de la frontera
principal y las 2 de la secundaria pasan a cero. Ese es el criterio que
decide, porque un comprador que participa y no gana nada es un defecto del
mecanismo, no un resultado.

### Confirmado sobre 400 horas en el servidor, el 2026-09-07

Doscientas horas activas al azar por frontera, con las mismas semillas y el
mismo criterio de evaluación.

| Frontera | Régimen | Volumen (kWh) | Excedente (COP) | Ahorro comprador | Sin ahorro | Con pérdida |
|---|---|---:|---:|---:|---:|---:|
| M1 | escalar, lo de antes | 779,23 | 199.307,4 | 93.281,6 | **283** | 0 |
| M1 | **propio** | 778,16 | **204.318,8** | **110.904,7** | **0** | 0 |
| M1 | único bajo | 777,72 | 198.827,9 | 110.382,6 | 0 | 0 |
| M1 | único alto | 779,23 | 199.307,4 | 82.497,6 | 283 | **283** |
| M3 | escalar | 483,52 | 294.492,5 | 210.001,5 | 6 | 0 |
| M3 | **propio** | 483,02 | 294.478,5 | 216.683,4 | **0** | 0 |
| M3 | único bajo | 483,02 | 294.605,3 | 216.760,1 | 0 | 0 |
| M3 | único alto | 483,52 | 294.492,5 | 209.942,2 | 6 | **6** |

**El hallazgo queda cerrado.** Las 283 horas-comprador sin ahorro de la
frontera principal y las 6 de la secundaria pasan a cero, sin excepción. La
factura comparada por institución se puede publicar.

Contado por horas en vez de por horas-comprador, el defecto era más grave de
lo que la primera cifra sugería: **109 de las 200 horas de la frontera
principal tenían al menos un comprador con beneficio exactamente cero**, es
decir más de la mitad. En la secundaria eran 4. Con el techo propio son cero
en las dos.

Por horas, el excedente mejora en 107, empeora en 22 y no se mueve en 71 en
la principal, con mediana del 0,00 % y un máximo del +109,8 %. En la
secundaria empeora más veces de las que mejora, 49 contra 20, con un rango
del −4,5 al +16,1 %. **Confirma que el agregado no es el argumento**: lo que
decide son los ceros.

**El techo único alto queda descartado sin discusión:** 283 horas con
pérdida, es decir compradores pagando por encima de lo que la red les cobra.

Dos cifras más, que conviene tener a mano. El excedente sube un 2,5 % en la
frontera principal y queda igual en la secundaria, con un 0,005 % de
diferencia, de modo que **el agregado sigue sin ser el argumento**. Y el
ahorro del lado comprador sube un 18,9 %, de 93.281,6 a 110.904,7 (COP), con
la tajada del vendedor bajando del 67,8 al 55,0 %: el arreglo traslada
excedente del vendedor al comprador.

**Tercera, el efecto sobre el excedente es pequeño y no uniforme.** En la
frontera principal el techo propio gana un 3,5 % en el agregado, pero por
horas gana en 31, pierde en 10 y empata en 19, con mediana del 0,00 % y un
rango del −3,5 % al +84,8 %. En la secundaria pierde un 0,1 %, ganando en 5
horas y perdiendo en 23. **El agregado no es el argumento**; el argumento es
que ningún comprador se quede en cero.

### De dónde sale la ganancia, cuando la hay

A las diez de la mañana del 2 de mayo, con 8,2381 (kWh) que mover en los
cuatro regímenes:

| Régimen | Institución | Techo | Precio | Compra (kWh) | Ahorro (COP) |
|---|---|---:|---:|---:|---:|
| escalar | Mariana, UCC, HUDN | 731,13 | 731,13 | 2,060 cada una | **0,00** |
| escalar | CESMAG | 777,17 | 756,05 | 2,060 | 43,50 |
| propio | Mariana, UCC, HUDN | 731,13 | 722,36 | 1,204 cada una | 10,55 |
| propio | CESMAG | 777,17 | 746,62 | **4,626** | 141,34 |

Con un techo común los cuatro compradores parecen iguales y la energía se
reparte en partes iguales. Con el techo de cada uno, la energía escasa va a
quien tiene la alternativa más cara, es decir a quien compra al otro
comercializador. Eso desplaza la compra a red más costosa y el excedente de
la hora sube de 411,4 a 529,6 (COP), un 28,7 %, sin mover un kilovatio hora
más. No es un reparto distinto del mismo excedente, es una asignación mejor.

### El techo único alto queda descartado

Deja a las tres instituciones de ASC pagando 756,05 (COP/kWh) contra un
techo propio de 731,13, es decir comprando más caro que en la red. Ahorro de
−51,33 (COP) cada una. Ningún régimen que obligue a un participante a pagar
por encima de su alternativa externa es admisible, y por eso las 88 horas
con pérdida lo cierran.

### Lo que sigue abierto, y es del asesor

Quedan dos candidatos, y el criterio los separa. El techo propio da 46.596,6
(COP) de excedente en la frontera principal y concentra el 82 % del ahorro
del lado comprador en el CESMAG. El techo único bajo da 45.016,1 y reparte
más parejo. **Gana en eficiencia y pierde en equidad.**

La consulta a Pablo Fajardo de junio de 2026 no zanja esto, aunque lo
parezca. Él afirma tres veces que el costo unitario base es el mismo para
todos, pero está contestando por **clase de usuario**, es decir comercial
frente a oficial dentro de un mismo comercializador, y eso ya se aplicó al
quitar la contribución del 20 % en CAL-47. Lo que hoy parte el techo es el
**comercializador**, y de ese eje no se le preguntó. Ver el anexo de
preguntas al comité.

**El cambio de código no depende de la respuesta.** Con techos iguales el
vector se reduce al escalar bit a bit, de modo que si la respuesta es el
techo único, el código ya la admite sin tocar nada.

### Una corrección al propio hallazgo

Este hallazgo decía que la vía alternada ya admitía techo vectorial desde
CAL-47 y la acoplada no. Admitirlo lo admite, pero **en producción nadie le
pasaba un vector a ninguna de las dos**, porque el parámetro viaja como
número suelto desde los parámetros de red. El único sitio que arma el vector
es la sonda. La liquidación sí lo usa, y esa asimetría entre el juego y la
liquidación es lo que producía el cero exacto.

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

---

## H-46 · El peso del jugador virtual no es el que usa el modelo base

**Estado: ABIERTO, con la opción implementada y su compuerta en verde el
2026-09-07. El defecto sigue siendo la forma de esta traducción; la del
fichero original es opt-in. Falta la medición sobre muestra grande, que va
al servidor. Una sonda de tres horas ya avisa de algo, y está abajo.**

El bloque comprador es una dinámica de replicador sobre los precios, con una
estrategia más que compradores: el jugador virtual, que absorbe el resto del
presupuesto. Cada estrategia entra en la aptitud media con un peso, y ese
peso es lo que mantiene el precio dentro de su banda, porque se anula en las
dos cotas.

En el fichero original el peso se arma en dos piezas. Para los compradores
reales es el producto de barrera, es decir el techo menos el precio por el
precio menos el piso. **Para el jugador virtual no**: es su propio precio.

Esta traducción le aplica la barrera también a él, en las dos vías, la
alternada y la acoplada.

### Cuánto importa

No es cosmético. Con las cotas del modelo base y un arranque en 1.000
(COP/kWh), la barrera vale 221.500 y el precio vale 1.000, es decir un
factor de 221. Con las cotas de permuta el factor baja pero sigue siendo de
orden 5. El peso entra en la aptitud media, y la aptitud media entra en la
deriva de **todos** los precios, de modo que la diferencia no se queda en el
jugador virtual.

### Por qué no se corrige todavía

Tres razones. La primera es que cambiarlo dentro de C-143 rompería la
identidad bit a bit que hace defendible esa corrección. La segunda es que la
versión arbitrada del modelo base **no tiene jugador virtual**: resuelve el
bloque comprador con un optimizador acotado, de modo que la fuente que zanja
las discrepancias no zanja esta. La tercera es que hay que medirlo antes,
como se midió todo lo demás.

### Qué habría que hacer, y qué ya se hizo

La opción está implementada en el solucionador acoplado, con la compuerta
`tests/gate_h46_peso_virtual.py` en verde. Exige cuatro cosas: que el
defecto siga siendo la forma de esta traducción bit a bit; que la otra forma
sea alcanzable y distinta; que un valor desconocido se rechace en vez de
caer en silencio en el defecto; y que el volumen no cambie entre las dos.

Falta la medición sobre muestra grande. La sonda es `peso_virtual.py` y va
al servidor con la tanda del 7 de septiembre.

### Aviso de una sonda de tres horas, que no decide pero orienta

Sobre tres horas activas de la frontera principal, con la banda de permuta:

| Forma del peso | Volumen (kWh) | Excedente (COP) | Tajada del vendedor | Posición media en la banda | Precios pegados |
|---|---:|---:|---:|---:|---:|
| barrera, la de esta traducción | 7,212 | 738,5 | 41,2 % | 0,457 | **0** |
| precio, la del fichero original | 7,212 | 730,8 | 11,6 % | 0,117 | **6** |

El volumen no se mueve, con 2,3·10⁻¹⁴ (kWh) de diferencia, y el excedente
apenas, como se esperaba. Pero **la forma del original deja seis precios
pegados a una cota y hunde la posición media de 0,457 a 0,117**, es decir
los empuja contra el piso.

Eso importa mucho, porque el precio pegado a las cotas es justo el defecto
que H-38 atribuyó al lazo alternado y que la vía acoplada venía a corregir.
Adoptar la forma del original por fidelidad podría reintroducirlo.

**No es concluyente**: son tres horas, y en el caso sintético con banda
ancha la forma del original da precios interiores. La diferencia sugiere que
el efecto aparece solo con la banda estrecha, igual que en H-32 y H-45. La
muestra de doscientas horas lo decide.

### Decidido sobre 400 horas en el servidor, el 2026-09-07

| Frontera | Forma del peso | Volumen (kWh) | Excedente (COP) | Tajada del vendedor | Posición en la banda | Precios pegados | Vendedores retirados |
|---|---|---:|---:|---:|---:|---:|---:|
| M1 | barrera, la de esta traducción | 778,160 | 204.318,8 | 55,0 % | 0,644 | **9** | 66 |
| M1 | precio, la del fichero original | 705,090 | 197.892,2 | 12,3 % | 0,150 | **489** | 85 |
| M3 | barrera | 483,017 | 294.478,5 | 31,5 % | 0,346 | 17 | 67 |
| M3 | precio | 481,980 | 294.094,7 | 31,9 % | 0,350 | 16 | 68 |

La forma del original **no es adoptable**, y no por gusto sino por lo que
hace:

1. **Pega 489 precios a una cota, frente a 9.** Es cincuenta y cuatro veces
   más, y la posición media en la banda se hunde de 0,644 a 0,150, es decir
   los empuja contra el piso.
2. **Cuesta el 9,4 % del volumen transado**, de 778,16 a 705,09 (kWh). No es
   un efecto de precio: al empujar el precio contra el piso, diecinueve
   vendedores más quedan por debajo de su alternativa externa y no entran.
   Los retirados pasan de 66 a 85.
3. **Hunde la tajada del vendedor del 55,0 al 12,3 %**, y en alguna hora el
   excedente se desvanece casi entero: la mayor diferencia relativa medida es
   del 97,2 %.

El precio pegado a las cotas es justamente el defecto que H-38 atribuyó al
lazo alternado y que la vía acoplada existe para corregir. Adoptar la forma
del original por fidelidad sería cambiar un defecto por otro peor.

### La frontera secundaria lo confirma por la vía negativa

Y esta es la comprobación que cierra el asunto, porque **en la secundaria las
dos formas dan prácticamente lo mismo**: el volumen difiere un 0,2 %, el
excedente un 0,13 %, la posición media del precio es 0,346 contra 0,350 y los
precios pegados 17 contra 16.

El mismo código, el mismo modelo y los mismos agentes se rompen en una
frontera y no en la otra. **Lo único que las distingue es el ancho de la
banda**: 228,1 (COP/kWh) en la principal contra 598,7 en la secundaria, es
decir 2,6 veces más. En la secundaria el piso es la bolsa, unos 108
(COP/kWh) contra un techo de unos 740, de modo que el supuesto del modelo
base, que el piso sea despreciable frente al techo, **sigue valiendo**. En la
principal el piso es la permuta, unos 693 contra 740, y deja de valer.

No es una conjetura sobre por qué falla: es la misma pieza medida en los dos
regímenes, funcionando en uno y fallando en el otro, con el ancho de la banda
como única diferencia.

Y el contraste es aún más nítido contado por horas. En la principal, la forma
de esta traducción pega algún precio en **8 de 200 horas** y la del original
en **139**. En la secundaria las cifras se invierten: 16 contra 8, es decir
que allí la del original es incluso marginalmente mejor.

El costo en volumen tiene la misma forma. En la principal la del original
mueve menos en 17 horas, con un caso extremo en que el mercado de esa hora se
desvanece casi entero, un **−98,7 %**. En la secundaria ocurre en una sola
hora.

**Decisión: se conserva la forma de esta traducción**, y la discrepancia con
el fichero original se declara en el documento en vez de resolverse a su
favor. La opción queda implementada y con compuerta, de modo que la
afirmación es verificable y no un dicho.

### Y con esto son tres, que es lo que de verdad importa

Este hallazgo cierra un patrón que ya no admite duda. **Tres piezas del
modelo base suponen que el piso es despreciable frente al techo**, que es el
régimen en el que fue calibrado, con 114 contra 1.250:

| Pieza | Hallazgo | Qué pasa con la banda medida |
|---|---|---|
| La condición inicial del bloque comprador | H-32 | nace por debajo del piso |
| El techo, tratado como escalar | H-45 | nace por encima del techo propio de tres compradores |
| El peso del jugador virtual | H-46 | empuja el precio contra el piso |

Las tres son inertes con banda ancha y las tres se rompen cuando la banda se
estrecha al cargo de comercializar, que es lo que CAL-47 midió. **No es que
el modelo base esté mal: es que no es transferible sin revisar sus supuestos
de escala.** Esa es una conclusión metodológica del trabajo, y conviene que
figure como tal y no repartida en tres notas.


---

## H-47 · El escenario que más excedente produce es el que peor factura deja

**Estado: MEDIDO el 2026-09-07 sobre un día completo y sobre una muestra de
veinte horas por frontera. Nace de la pregunta abierta de H-45 y la
desborda: no es sobre el techo del juego, es sobre con qué se mide un
escenario. Contiene la rectificación de una afirmación que el día solo
sostenía y la muestra desmiente.**

La pregunta de partida era institucional. Cuatro instituciones compran a un
comercializador y la quinta a otro, de modo que cabe preguntarse qué pasaría
si las cinco compraran al mismo. Se midió sustituyendo el **perfil
tarifario** entero, no solo el número que entra al juego, con lo que el
cambio viaja al techo, al piso de permuta, al límite económico de
generación, a la clasificación en papeles y a la liquidación.

### Lo que los dos comercializadores se intercambian

Componentes del costo unitario en mayo de 2025, en (COP/kWh):

| Escenario | Techo | Comercialización | Generación | Redes |
|---|---:|---:|---:|---:|
| real | 740,34 | 66,95 | 387,74 | 277,26 |
| todas con ASC | 731,13 | **38,43** | 415,61 | 277,08 |
| todas con CEDENAR | 777,17 | **181,03** | 276,27 | 277,96 |

Los cargos de red coinciden en los tres, como debe ser, porque los fija el
operador y no el comercializador. Eso valida que la sustitución hace lo que
dice. Lo que los dos se intercambian es generación por comercialización: ASC
compra la energía más cara y cobra mucho menos por comercializarla.

### El ordenamiento invertido

El 2 de mayo de 2025, ocho horas con mercado en la frontera principal:

| Escenario | Banda | Excedente del mercado | Factura sin mercado | Factura con mercado |
|---|---:|---:|---:|---:|
| todas con ASC | 38,4 | 2.123,5 | 284.846,4 | **282.722,9** |
| real | 50,9 | 3.195,4 | 286.737,1 | 283.541,7 |
| todas con CEDENAR | 181,0 | **10.002,2** | 310.529,8 | 300.527,6 |

**Por excedente del mercado gana CEDENAR, con 4,7 veces el de ASC. Por
factura pagada pierde, con 17.804,7 (COP) más en ocho horas.** Los dos
ordenamientos están exactamente invertidos, y el orden se repite en la
frontera secundaria, de modo que no es casualidad de una.

La razón está en la identidad de H-33 y en CAL-47 juntas. El excedente del
mercado es el ancho de la banda por la energía transada, y el ancho de la
banda **es** el cargo de comercializar. El mercado entre pares recupera ese
cargo, pero solo sobre la energía que se transa, que es el lado corto. La
comunidad lo paga sobre todo lo que compra.

**La consecuencia metodológica, que es el hallazgo:** medir un escenario por
lo que el mercado ahorra lleva a elegir el proveedor equivocado. Toda
comparación entre escenarios tiene que informar la factura, no solo el
excedente. Afecta a cómo se presentan los resultados frente a la regulación.

Dicho en positivo, y así conviene decirlo en el documento: **el mercado
entre pares vale más justamente donde el minorista es peor**, porque lo que
ahorra es el cargo de comercializar que evita.

### El volumen sí se mueve, y por una razón que no es el precio

**Rectificación.** Con el día solo, este hallazgo afirmaba que el volumen no
se movía en absoluto, con diferencias de 4,0·10⁻¹³ (kWh). Sobre la muestra
de veinte horas por frontera resulta falso en la frontera principal: el
volumen pasa de 58,21 (kWh) en el escenario real a 60,21 con todas en ASC y
61,43 con todas en Cedenar. **El escenario real mueve menos energía que
cualquiera de los dos uniformes.**

La causa no es el precio ni el límite económico de generación, que
efectivamente no muerde: con costos marginales del orden de 80 a 200
(COP/kWh) contra techos de 731 a 777, ningún generador queda fuera por
antieconómico. La causa es **la restricción de participación**, y con ella
este hallazgo se enlaza con H-43.

| Escenario | Vendedores retirados en 19 horas | Volumen (kWh) |
|---|---:|---:|
| todas con ASC | 4 | 60,21 |
| todas con CEDENAR | 3 | 61,43 |
| **real** | **9** | **58,21** |

El escenario real retira más del doble de vendedores que cualquiera de los
uniformes. La hora 4406 lo enseña en limpio: con tarifas uniformes no se
retira nadie y se mueven 3,40 (kWh); con las tarifas reales se retiran dos
de los tres vendedores y el volumen cae a 1,39, un 59 % menos.

El mecanismo es el de H-43. El piso del juego es el menor de los pisos de
los vendedores activos. Con dos comercializadores los pisos difieren, en esa
hora 677,3 y 616,5 (COP/kWh), y un precio admisible para el vendedor de piso
bajo queda por debajo del piso del otro, que entonces no entra. Con tarifas
uniformes los pisos coinciden y el problema desaparece.

**La heterogeneidad de comercializador es, por tanto, una de las causas de
H-43**, y le cuesta energía a la comunidad. Es un tercer criterio, distinto
del excedente y de la factura, y apunta en el mismo sentido que la factura.

En la frontera secundaria el volumen sí es idéntico en los tres escenarios,
sin una sola diferencia por encima de 10⁻⁹ (kWh), porque allí el piso es la
bolsa y la bolsa es la misma para todos.

### El orden se confirma sobre la muestra

Veinte horas activas al azar por frontera, tomadas de todo el horizonte.

| Frontera | Escenario | Volumen | Excedente | Factura con mercado |
|---|---|---:|---:|---:|
| M1 | todas con ASC | 60,21 | 15.348,8 | **320.471,5** |
| M1 | real | 58,21 | 16.455,9 | 331.841,2 |
| M1 | todas con CEDENAR | 61,43 | **22.872,7** | 352.284,0 |
| M3 | todas con ASC | 36,43 | 21.529,4 | **14.882,6** |
| M3 | real | 36,43 | 22.873,0 | 16.474,8 |
| M3 | todas con CEDENAR | 36,43 | **24.134,4** | 18.168,0 |

El ordenamiento invertido se sostiene en las cuatro mediciones, es decir las
dos fronteras del día y las dos de la muestra: **por excedente gana siempre
Cedenar y por factura gana siempre ASC**, sin una sola excepción.

### Confirmado sobre 400 horas en el servidor, el 2026-09-07

Doscientas horas activas al azar por frontera.

| Frontera | Escenario | Volumen (kWh) | Banda | Excedente (COP) | Factura con mercado |
|---|---|---:|---:|---:|---:|
| M1 | todas con ASC | **803,26** | 205,3 | 186.027,5 | **2.728.480,4** |
| M1 | real | 778,16 | 228,1 | 204.318,8 | 2.782.893,7 |
| M1 | todas con CEDENAR | **810,00** | 316,0 | **281.493,8** | 3.028.777,0 |
| M3 | todas con ASC | 483,02 | 563,2 | 272.832,8 | **169.718,8** |
| M3 | real | 483,02 | 598,7 | 294.478,5 | 184.067,4 |
| M3 | todas con CEDENAR | 483,52 | 634,0 | **306.382,6** | 202.105,1 |

**El ordenamiento invertido queda establecido**: seis mediciones
independientes, es decir las dos fronteras del día, las dos de la muestra
local y las dos del servidor, y en las seis gana Cedenar por excedente y ASC
por factura. Ni una excepción en el agregado.

Hora a hora la constancia es desigual y conviene decirlo. El excedente ordena
a favor de Cedenar en 197 de 200 horas en la principal y en **200 de 200** en
la secundaria. La factura ordena a favor de ASC en 189 de 200 en la principal
pero solo en **129 de 200** en la secundaria, donde el agregado sigue siendo
claro porque las horas en que ASC gana pesan más. De modo que **la afirmación
se sostiene sobre el total facturado y no sobre el recuento de horas**, y así
hay que enunciarla.

Las magnitudes ya no son marginales. En la frontera principal el excedente
del mercado con Cedenar supera al de ASC en un **51,3 %**, y su factura es un
**11,0 %** más cara. En la secundaria, un 12,3 % más de excedente contra un
19,1 % más de factura.

### El porcentaje de ahorro tampoco sirve como criterio

Es la trampa en su forma más fina, y solo aparece con las dos fronteras
delante. En la principal el ahorro relativo ordena Cedenar primero con el
8,50 %, luego el reparto real con el 6,84 % y ASC último con el 6,38 %. En la
secundaria **ordena al revés**: ASC primero con el 61,65 %, el real con el
61,54 % y Cedenar último con el 60,25 %.

Es decir que el ahorro relativo elige el proveedor equivocado en una frontera
y el correcto en la otra, sin que nada avise de cuál es cuál. **Solo la
factura ordena igual en las dos.** Cualquier comparación entre escenarios que
se presente en porcentaje de ahorro y no en pesos pagados está expuesta a
esto.

### La heterogeneidad cuesta energía, y ahora se mide

Sobre 400 horas el efecto es mucho mayor que el que se vio con veinte. En la
frontera principal:

| Escenario | Volumen (kWh) | Frente al real |
|---|---:|---:|
| real, dos comercializadores | 778,16 | — |
| todas con ASC | 803,26 | **+3,2 %** |
| todas con CEDENAR | 810,00 | **+4,1 %** |

**El escenario real mueve entre un 3 y un 4 % menos energía que cualquiera de
los dos uniformes.** No es el precio ni el límite económico de generación: es
la restricción de participación de H-43.

**Y está concentrado**, que es lo que hay que decir para no exagerarlo. De
las 200 horas, el escenario real mueve menos que el uniforme en **8**, y en
las 190 restantes el volumen coincide. Los 25,1 (kWh) de diferencia salen de
esas ocho, a razón de unos tres cada una, de modo que no es una merma
repartida sino un puñado de horas donde el mercado se rompe. Los vendedores
retirados lo acompañan: 66 en el escenario real contra 52 con todas en ASC y
40 con todas en Cedenar. Con dos comercializadores los pisos
de los vendedores difieren, el piso del juego es el menor de ellos, y el
vendedor de piso alto no entra.

En la secundaria el volumen es prácticamente idéntico en los tres, porque
allí el piso es la bolsa y la bolsa no depende del comercializador.

**Ese 4 % es el costo de la heterogeneidad**, y es un tercer criterio,
distinto del excedente y de la factura, que apunta en el mismo sentido que
la factura.

### Por qué la frontera secundaria apenas distingue

Allí el piso no es la permuta sino la bolsa, 107,9 (COP/kWh) en los tres
escenarios, porque sus vendedores inyectan más de lo que retiran en el mes.
**El precio de bolsa no depende del comercializador.** Con un piso tan bajo
la banda supera los 600 y el cargo de comercializar deja de gobernarla: los
tres escenarios dan entre el 57,4 y el 57,8 % de ahorro y el orden por
factura se sostiene solo por el techo.

### Qué queda

Confirmar el orden fuera de este día con una muestra, y decidir si el
escenario de consolidación de comercializador entra en el documento o se
queda como nota. La sonda es `escenario_comercializador.py` y el interruptor
es la función que fuerza el comercializador en la capa de tarifas.


---

## H-48 · Los dos comercializadores no impiden la comunidad, y la norma lo dice en sus fórmulas

**Estado: ESTABLECIDO el 2026-09-07 con fuente primaria. Responde por
adelantado a una objeción previsible y cierra la pregunta que H-45 dejaba
abierta para el comité.**

Nace de una observación de Sofía Chacón: que al cambiar de transformador se
cambia de zona de frontera comercial, que alguna resolución explica qué pasa
con comercializadores distintos, y que si se cambia de zona no se podía
hacer mercado, con lo que las comunidades energéticas tendrían que estar en
la misma zona. De ser así, un mercado entre pares puramente virtual quedaría
desvirtuado, porque cada par estaría atado al transformador por el que entra
o sale su energía.

**La restricción existe, pero no es la que se recuerda.** Y la diferencia
decide si esta comunidad es admisible.

### Lo que exige la norma

La Resolución CREG 101 072 de 2025 recoge el límite de dispersión: la
capacidad de generación y sus usuarios deben pertenecer al **mismo mercado
de comercialización** y estar inmersos en el **mismo Sistema de Distribución
Local**.

Y «mercado de comercialización» está definido en la Resolución CREG 015 de
2018 como el «conjunto de usuarios regulados y no regulados conectados a un
mismo STR y/o SDL, **servido por un mismo OR**».

**El mercado lo define el operador de red, no el comercializador.** No es el
transformador ni la frontera comercial de cada usuario: es el área del
operador.

### La norma contempla expresamente varios comercializadores

Es la prueba más fuerte y está en su propio articulado. Las fórmulas de
liquidación del autogenerador colectivo indexan cada cantidad por tres
cosas: el usuario, el mercado de comercialización y **el comercializador**.
El porcentaje de distribución de excedentes se define «para el punto de
conexión del usuario u, en el mercado de comercialización j y que es
**atendido por el comercializador i**».

Si un colectivo tuviera que compartir comercializador, ese índice sobraría.
Está ahí porque la norma da por supuesto que puede no compartirlo.

### Quién es quién, según el registro de XM

Consultado el listado de agentes registrados ante el Mercado de Energía
Mayorista:

| Código | Actividad | Agente | NIT |
|---|---|---|---|
| ASCC | **COMERCIALIZADOR** | A.S.C. Ingeniería S.A. E.S.P. | 814.002.979-7 |
| CDNC | COMERCIALIZADOR | Centrales Eléctricas de Nariño S.A. E.S.P. | 891.200.200-8 |
| CDND | **OPERADOR DE RED** | Centrales Eléctricas de Nariño S.A. E.S.P. | 891.200.200-8 |
| CDNG | GENERADOR | Centrales Eléctricas de Nariño S.A. E.S.P. | 891.200.200-8 |

ASC está inscrita como comercializador desde el 14 de marzo de 2003 y **no
tiene registro como operador de red**. Centrales Eléctricas de Nariño lo
tiene bajo el mismo número de identificación con el que figura además como
comercializador, que es la figura del comercializador integrado con el
operador a la que se refiere la Resolución CREG 174 de 2021.

De modo que las cinco instituciones, todas en Pasto y todas conectadas al
sistema de distribución de Nariño, **están en el mismo mercado de
comercialización y en el mismo sistema de distribución local**, con dos
comercializadores distintos. Cumplen.

### Tres confirmaciones más, por si la primera no bastara

1. **La hoja tarifaria de ASC** se publica «en cumplimiento del inciso
   segundo del artículo 125 de la Ley 142 de 1994», que es la obligación del
   comercializador de dar a conocer sus tarifas, y se dirige a «los usuarios
   regulados del Departamento de Nariño».
2. **Su estructura de costos distingue la propiedad de los activos de red** y
   trae una fila del operador, es decir que paga cargos de uso de red a un
   tercero en vez de fijarlos.
3. **Nuestra propia medición**: los cargos de red de las dos tablas
   coinciden, 277,08 contra 277,96 (COP/kWh) en mayo de 2025. Es lo que se
   espera si el operador es el mismo, porque los fija él. Lo que difiere es
   generación y comercialización.

### Lo contrario de lo que se temía

La armonización de las comunidades energéticas introduce la **agregación
virtual de fronteras** justamente para integrar usuarios dispersos
geográficamente, con la condición de que estén en el mismo mercado de
comercialización y el mismo sistema de distribución local. No desvirtúa el
mercado virtual: lo habilita, y le pone por límite el área del operador de
red en vez del transformador.

### Qué se sigue para el modelo

**El techo por comprador es la configuración correcta**, y ahora por tres
razones y no por una: es lo que dice el dato, es lo que la norma permite de
forma expresa, y es lo que elimina las horas con comprador sin beneficio.

Los dos escenarios uniformes de H-47 **dejan de ser candidatos y quedan como
análisis de sensibilidad**. Sirven para cifrar cuánto pesa la
heterogeneidad, que es un 4 % de la energía transada y un 11 % de la
factura, y para sostener el ordenamiento invertido. No son configuraciones
alternativas.

Y la caja de decisión pendiente sobre techo único frente a techo por agente
**queda resuelta**, con norma y registro, en vez de quedar al criterio del
comité.


---

## H-49 · El piso medido nunca llegó a la corrida, y sobrestimaría el excedente por un factor de doce

**Estado: ESTABLECIDO el 2026-09-07 con el código en la mano. BLOQUEA LA
CORRIDA CANÓNICA. Es el hallazgo de mayor consecuencia práctica de la
jornada.**

Salió de diagnosticar H-43, y lo desborda.

### Lo que se creía

CAL-47 estableció que las dos cotas del juego eran constantes escritas a
mano y las sustituyó por cotas medidas: el techo es el costo unitario
mensual de cada agente y el piso es la permuta, es decir el techo menos el
cargo de comercializar, o la bolsa cuando el vendedor ya superó su retiro
del mes. La corrección C-137 se registró como «CAL-47 pasa al código».

### Lo que hay

**El techo sí llegó**, primero a la liquidación y hoy al juego con C-146.

**El piso no.** En la corrida de producción vale **280 (COP/kWh), constante
para los cinco agentes y las 5.160 horas**. Es el promedio de bolsa de
abril a diciembre de 2025 escrito a mano en la capa de datos, exactamente la
constante que CAL-47 venía a sustituir. Nadie construye el piso por vendedor
fuera de las sondas: la función que lo calcula existe en el módulo de
opciones externas y **la llaman dos sondas y nadie más**. Ni el orquestador,
ni el motor, ni los escenarios.

### Lo que cuesta, y es lo que obliga a parar

Por la identidad de H-33 el excedente del mercado es el ancho de la banda
por la energía transada. Con el techo por agente que hoy sí entra:

| | Banda que vería el juego | Banda que CAL-47 mide | Sobrestimación |
|---|---:|---:|---:|
| Agentes de ASC | 451,1 | 38,4 | **12 veces** |
| El del otro comercializador | 497,2 | 181,0 | **2,7 veces** |

**Lanzar hoy la corrida canónica produciría un excedente de mercado
sobrestimado en un orden de magnitud en la frontera principal**, y encima
con el techo ya corregido, que es la peor combinación posible: parecería más
fiable que el canon viejo y sería igual de falsa por el otro extremo.

### Por qué no se vio antes

Porque las tres sondas de hoy y todo el aparato de validación horaria
construyen sus cotas por su cuenta, con la función medida, y por eso sus
cifras son correctas. La discrepancia solo aparece al comparar lo que mide
el documento con lo que correría el canon, y eso no lo hacía nadie.

### Una afirmación del registro que hay que corregir

La corrección C-137, en su punto tercero, dice que las dos cotas admiten
vector «el techo por comprador y el piso por vendedor, **en el bloque
comprador**, en la liquidación y en el límite económico de generación».

**La parte del piso en el bloque comprador es falsa.** Comprobado: el bloque
comprador acepta un techo vectorial y **rechaza un piso vectorial**, tanto
indexado por vendedor como por comprador. La liquidación sí lo acepta. De
modo que lo que C-137 dejó hecho para el piso es la mitad de lo que dice.

### Y no es un descuido, es estructural

El precio tiene índice de **comprador** y el piso tiene índice de
**vendedor**. No hay forma de meter un piso por vendedor en una dinámica
cuyo estado es un precio por comprador sin cambiar el modelo. Por eso el
piso comunitario del juego es el menor de los pisos activos, y por eso la
única salida coherente es la restricción de participación: no acotar el
precio por vendedor, sino decidir **quién entra**.

Es exactamente lo que H-43 plantea, de modo que **H-43 y este hallazgo son
el mismo trabajo en dos pasos**: primero llevar el piso medido al juego, que
hoy no está, y después la participación.

### Qué hay que hacer, en orden

1. **El piso por vendedor entra a los parámetros de red**, como el techo con
   C-146, y el orquestador lo construye antes del mercado. Hace falta subir
   el cálculo del cargo de comercializar, que hoy se hace después del
   mercado, y añadir el tramo de permuta, que en producción no se calcula.
2. **El juego recibe el mínimo de los pisos activos** de la hora, que es lo
   que ya hace la sonda, en vez de la constante.
3. **La restricción de participación entra al motor**, con el criterio de
   retiro por decidir. El de la sonda retira al vendedor cuyas ventas queden
   TODAS por debajo de su piso, y conviene revisar si no debería ser que su
   prima agregada resulte negativa.
4. **La liquidación recibe el piso por vendedor**, que ya lo admite.

**Hasta que esto esté, la corrida canónica no debe lanzarse.**


---

## H-50 · La corrida de un día devolvía una tabla entera de valores no numéricos, y salía con código cero

**Estado: CORREGIDO el 2026-09-07 por C-148, con dos guardas. Es el fallo más
silencioso que este proyecto ha encontrado.**

Salió de perseguir el piso de H-49. Al llevarlo a la corrida, el aviso decía
que el piso iba «de nan a nan». El piso no era el culpable.

### Qué pasaba

El techo de escasez de la Resolución CREG 101 066 se carga de una tabla
mensual. **Esa tabla no tiene fila para abril, mayo ni junio de 2025**: la
primera es julio. El cargador rellena los meses ausentes interpolando entre
los que sí tienen valor, y ahí estaba el defecto: **interpolaba solo dentro
de la ventana pedida**.

- Pidiendo de abril de 2025 a enero de 2026, mayo se rellenaba desde julio y
  valía 865,22 (COP/kWh). Correcto.
- Pidiendo solo mayo, quedaba **un único hueco sin nada de donde
  interpolar**, y devolvía un valor no numérico.

Quien lo consume aplica el techo con un mínimo, y el mínimo **propaga el
valor no numérico sin avisar**. La serie de bolsa entera quedaba inservible.

### Hasta dónde llegaba

Hasta el final, sin que nada fallara. La corrida de un día del 2 de mayo de
2025 imprimió:

    PGB=nan COP/kWh (promedio bolsa)
    P2P (Stackelberg + RD)        $   nan   0.174   1.000   0.1296   nan
    C1  Individual CREG 174/2021  $   nan   0.132   0.758   0.0000   nan
    C2  Bilateral PPA             $   nan   0.132   0.758   0.0000   nan

**Y terminó con código de salida cero.** Ciento sesenta y seis apariciones
del valor no numérico en el registro de la corrida.

### Qué alcanza y qué no

**El canon está a salvo.** La corrida de horizonte completo pide de abril de
2025 a enero de 2026, de modo que la ventana incluye julio y la
interpolación funciona. Solo falla el modo de un día, y solo en los meses sin
fila propia, que son los tres primeros del horizonte.

Pero el modo de un día es el que se usa para diagnosticar, y **cualquier
diagnóstico hecho sobre abril, mayo o junio de 2025 con ese modo no vale
nada**. No hay forma de saber cuántos se hicieron.

### El arreglo, en tres piezas

1. **La interpolación se hace sobre la unión** del rango pedido con el índice
   del fichero, de modo que el techo de un mes es el mismo se pida como se
   pida. Comprobado: mayo vale 865,22 en las tres ventanas que antes daban
   resultados distintos.
2. **El cargador falla en voz alta** si aun así queda un mes sin valor.
3. **El orquestador comprueba la serie de bolsa** antes de seguir, que es
   donde se sabe, y se detiene en vez de producir una tabla de valores no
   numéricos.

### La lección, que ya estaba escrita y volvió a morder

Es la de CAL-43: **mirar el código de salida equivocado**. Una corrida que
termina no es una corrida que funcione. Aquí ni siquiera hacía falta leer el
código de salida: bastaba mirar la tabla, y la tabla llevaba la respuesta en
la cara.

Conviene extraer la norma general: **cuando un valor ausente se rellena por
interpolación, el resultado no puede depender de la ventana que se pida.** Si
depende, hay dos respuestas distintas para la misma pregunta y una de las dos
está mal.


---

## H-51 · La tolerancia del integrador no era la del modelo base, y de ahí salían las horas que no resolvían

**Estado: CORREGIDO el 2026-09-07, medido sobre nueve horas. Rectifica lo que
H-42 daba por establecido sobre el costo de la vía acoplada.**

Lo señaló el autor: que Chacón le ponía un límite de tiempo para que la
integración no se alargara. Buscarlo en el fichero original llevó a otra
cosa, más simple y más grave.

### La discrepancia

El fichero original fija las dos tolerancias del integrador en el mismo
valor:

    options = odeset('RelTol',1e-6, 'AbsTol',1e-6);

Esta traducción usa la relativa del original y **la absoluta mil veces más
estricta**, en 10⁻⁹.

**Rectificación, porque este hallazgo afirmaba que no había decisión detrás y
sí la hubo.** La batería de validación de convergencia del 2026-07-22 probó
la tolerancia del original y encontró que el integrador no completaba: tiempo
agotado y valores no numéricos. Lo dejó escrito en el código, «con atol=1e-6,
espejo de AbsTol de MATLAB, LSODA no completa», y en su informe, «atol
corregido de 1e-6 a 1e-9 tras hallazgo de tiempo agotado». De modo que el
valor no quedó escrito por descuido: se eligió, y con una razón medida.

**Y esa razón no se sostiene, por dos motivos.**

El primero lo dice el propio informe de julio dos párrafos más abajo: sobre
el caso donde 10⁻⁶ fallaba, **10⁻⁹ también agota el tiempo sin converger**.
Las dos fallaban allí, de modo que el cambio no consiguió lo que buscaba.

El segundo se midió hoy sobre las horas del caso base, que es donde la
objeción tendría que aparecer:

| Hora del modelo base | Con 10⁻⁹ | Con 10⁻⁶ | Volumen |
|---:|---|---|---:|
| 13 | 7,7 s, éxito | 8,7 s, éxito | idéntico, 3,0326 |
| 14 | 5,2 s, éxito | 5,4 s, éxito | idéntico, 3,0631 |
| 19 | 0,2 s, éxito | 0,2 s, éxito | idéntico, 0,8776 |

Las dos resuelven, sin valores no numéricos y con el mismo resultado.

De modo que la conclusión es más matizada que la primera versión de este
hallazgo: **10⁻⁶ nunca resultó peor y a veces es mucho mejor**, y la decisión
de julio se tomó sobre un caso donde ninguna de las dos funcionaba.

Y hay una línea más, comentada justo debajo en el original, que prueba que
allí se topó con el mismo asunto: fija las dos tolerancias en 10⁻⁹ y le añade
una función de eventos, que es el mecanismo para detener la integración antes
de tiempo. **Está comentada.** Es decir que probó las tolerancias estrictas,
necesitó un freno para convivir con ellas, y acabó quedándose con las
holgadas. Nosotros heredamos el problema sin heredar la respuesta.

### Por qué manda la absoluta y no la relativa

Porque gobierna cuando las variables son pequeñas, y el estado del sistema
lleva cantidades de energía recortadas a 10⁻¹⁰. Con una tolerancia absoluta
de 10⁻⁹, esas componentes obligan al integrador a achicar el paso sin que
haya nada que resolver ahí. Con 10⁻⁶ dejan de gobernar.

### Lo que se midió

**En la hora que no resolvía**, la 4741 de la frontera principal, con un
vendedor y cuatro compradores:

| Tolerancia absoluta | Resultado |
|---|---|
| la nuestra, 10⁻⁹ | **no resuelve** en más de cuarenta minutos de procesador |
| la del modelo base, 10⁻⁶ | **resuelve en 2,2 segundos**, con precios interiores |

**En ocho horas al azar resueltas con las dos:**

| Hora | Con 10⁻⁹ | Con 10⁻⁶ | Diferencia de volumen (kWh) | Diferencia de precio (COP/kWh) |
|---:|---:|---:|---:|---:|
| 182 | 0,3 s | 0,2 s | 3,7·10⁻¹⁴ | 6,0·10⁻⁴ |
| 3445 | 61,5 | 60,8 | 4,2·10⁻¹⁴ | 1,6·10⁻⁹ |
| 560 | 89,6 | 88,2 | 1,4·10⁻¹³ | 7,3·10⁻¹⁰ |
| 2894 | 18,9 | 17,8 | 9,1·10⁻¹⁴ | 3,7·10⁻⁸ |
| 2842 | 0,3 | 0,2 | 0 | 2,3·10⁻⁵ |
| 4187 | 0,3 | 0,2 | 2,7·10⁻¹⁵ | 2,4·10⁻³ |
| 537 | 1,6 | 0,2 | 6,7·10⁻¹⁶ | 3,6·10⁻⁴ |
| 2462 | 36,3 | 19,7 | 2,0·10⁻¹⁴ | 6,6·10⁻³ |

**No cambia la respuesta**: el volumen coincide dentro de 1,4·10⁻¹³ (kWh) y
el precio dentro de 6,6·10⁻³ (COP/kWh) sobre precios del orden de 700.

**Y no es una aceleración general.** Conviene decirlo así porque es fácil
venderlo mal, y se vendió mal la primera vez: en seis de las ocho horas las
dos tolerancias tardan lo mismo. Lo que hace es **rescatar las horas que se
atascaban**, sin penalizar las demás.

### Qué rectifica

H-42 registró que la vía acoplada «cuesta 74 veces y **no tiene cota**». La
segunda mitad hay que corregirla: **sí tenía cota, la del modelo base, y se
había perdido al traducir**. Las horas que «no acababan en 3.500 segundos»
que midió la sonda del costo son el mismo artefacto.

Lo que sí se sostiene es que la vía acoplada es cara: la hora corriente de la
frontera principal cuesta entre 60 y 90 segundos, no los 47 que estaban
anotados.

### Qué desbloquea

La corrida canónica acoplada, decidida el mismo día, dejaba una duda
razonable: sobre las 1.126 horas con mercado del horizonte cabía esperar del
orden de catorce horas que no resolvieran y que la bloquearan sin cota. Con
la tolerancia del modelo base **esa duda desaparece**.

La cota de tiempo que C-150 llevó a las sondas se queda igualmente, pero
pasa de ser la solución a ser lo que debe ser: una red de seguridad.

### La lección

Es una variante de la que ya lleva tres apariciones hoy: **un valor que nadie
decidió gobierna un comportamiento que a todos sorprende**. Aquí el valor ni
siquiera venía del modelo base; se escribió al traducir y nadie volvió a
mirarlo. Conviene revisar si hay más constantes del solucionador en esa
situación.


---

## H-52 · El precio interno de la comunidad no está regulado, pero el piso no se elige

**Estado: PLANTEADO el 2026-09-08, con la norma comprobada y la predicción
escrita ANTES de medir, para que se pueda desmentir. La medición va aparte.**

La pregunta la puso el autor, y tiene tres partes que conviene separar porque
se responden de forma distinta: qué permite la norma, qué significa
económicamente, y si conviene medirlo.

### Qué permite la norma, y es lo primero porque acota la pregunta

Dos disposiciones importan, y las dos son favorables.

**El precio interno no está regulado.** La Resolución CREG 101 072 de 2025
establece, para la venta de excedentes a comercializadores que atienden
usuarios no regulados, que **«el precio de venta es pactado libremente»**. Y
las cinco instituciones son usuarias no reguladas desde CAL-47.

**El reparto interno del colectivo tampoco.** El porcentaje de distribución de
excedentes «será informado por el representante» y **«acordado por los
integrantes»**. La norma exige que se declare, no fija su valor.

**Conclusión: nada impide negociar el precio que se quiera.** La norma
gobierna quién puede estar en la comunidad y cómo se liquida lo que cruza su
frontera, no el precio de dentro. Los tres regímenes que se plantean abajo son
admisibles, y la pregunta es cuál conviene, no cuál se permite.

### Pero el piso no es una elección, es un dato

El piso no es un precio que se fije: es **la alternativa externa del
vendedor**, lo que la red le pagaría si no vendiera dentro.

La condición que lo cambia está en los artículos 22 y 23 de la Resolución
CREG 174, y es concreta. Dentro de **cada mes** se acumulan hora a hora la
inyección, es decir lo que le sobra, y el retiro, lo que le falta. **En cuanto
la inyección acumulada supera al retiro acumulado, el agente pasa a mercado
mayorista para el resto del mes**, y el contador se reinicia el mes siguiente.

Dicho en llano: la permuta es un trueque, y mientras haya consumo propio que
descontar el excedente vale la tarifa menos el cargo de comercializar. Cuando
ya se descontó todo lo consumido en el mes, no queda nada contra qué permutar,
y lo que sobra es energía que se vende de verdad, a precio de bolsa.

No es un umbral arbitrario: es el punto donde el agente deja de ser un
consumidor que compensa y pasa a ser un generador que vende.

**De ahí que forzar el piso de permuta a quien ya cruzó sea modelar a un
vendedor que rechaza precios que aceptaría de buena gana.** Sobre el 2 de mayo
eso significaría rechazar entre 110 y 692 (COP/kWh). No es un mercado más
favorable: es un vendedor irracional.

### Y lo que de verdad decide, que no es lo que parece

**El precio interno no afecta al resultado agregado de la comunidad.**

La cuenta de la comunidad es lo que paga menos lo que recibe. En una venta
dentro, el comprador paga y el vendedor cobra **lo mismo**: se cancela. Es una
transferencia entre miembros.

    cuenta = suma(D_neta · techo) − suma(G_neta · piso) − suma(P · (techo − piso))

Los dos primeros términos son la cuenta sin mercado, y el tercero es el
excedente. **El precio no aparece.** Es la identidad de H-33 leída por el otro
lado.

Lo único que mueve la posición agregada es cuánta energía se mueve dentro en
vez de cruzar la frontera, y los precios a los que cruza lo que sobra, que son
el techo y el piso, y esos los fija la red.

### Entonces, ¿el piso de bolsa beneficia?

**Por la métrica del excedente, sí**, y es una trampa. Un piso más bajo
ensancha la banda y el excedente sale mayor. Pero es **exactamente lo de
H-47**: el excedente crece porque la alternativa empeora, no porque la
comunidad esté mejor.

**Hay un canal por el que sí importa de verdad.** Un piso más bajo hace que
más vendedores acepten participar, porque su alternativa es peor y el mercado
la bate con más facilidad. Y más participación es más volumen, y el volumen sí
mueve la posición agregada.

Ese canal es real, es medible y **no se ha medido**.

### Lo que se va a medir

Tres regímenes del piso, los tres admisibles porque el precio interno es
libre:

| Régimen | Qué representa |
|---|---|
| **tramo** | la alternativa real de cada vendedor según la CREG 174. Es lo actual |
| **permuta** | todos negocian con el piso de permuta, ignorando que algunos ya cruzaron |
| **bolsa** | todos negocian con el piso de bolsa, la alternativa más baja |

Y **cuatro métricas informadas por separado**, porque esta jornada enseñó que
se contradicen:

| Métrica | Qué es |
|---|---|
| **Bienestar** | la suma del bienestar de vendedores y compradores. Es **la función que el modelo base maximiza**, y por tanto la métrica del autor del modelo |
| **Factura** | lo que la comunidad paga de verdad |
| **Volumen y retirados** | el canal por el que el piso puede mover la factura |
| Excedente | la banda por la energía. **Engaña**, y se informa solo para enseñar que engaña |

La primera entra por indicación del autor, y con razón: el modelo base no
maximiza ni la factura ni el excedente, maximiza el bienestar comunitario.

### La predicción, escrita antes de medir

Para que se pueda desmentir:

> La factura apenas se moverá salvo por el cambio de volumen, y el régimen de
> bolsa moverá más energía porque retira menos vendedores. Si es así, **el
> piso de bolsa sería mejor para la comunidad, pero por participación y no por
> precio.**

Si la medición la contradice, se anota la contradicción y no la predicción.

### Lo que no se decide aquí

Que el modelo **conserve** el régimen de tramo, que es el que describe la
alternativa real. Los otros dos existen para medir cuánto pesa la regla de la
CREG 174 sobre el resultado, no para sustituirla. Si la medición mostrara que
otro régimen conviene, eso sería una **recomendación** sobre cómo debería
negociar la comunidad, no un cambio en lo que el modelo describe. Es la misma
distinción que H-48 estableció con el comercializador.


---

## H-53 · El tramo de permuta se calcula sobre el excedente bruto, y la norma lo calcula sobre lo asignado

**Estado: PLANTEADO el 2026-09-08. Lo destapó una pregunta del autor: si la
regla de la Resolución CREG 174 aplica dentro del mercado entre pares o solo
cuando la energía sale de la comunidad. Aplica fuera, y nuestro cálculo la
mete dentro.**

### La regla es de la frontera, no del mercado interno

La Resolución CREG 174 gobierna **la liquidación entre el agente y su
comercializador**. Es una regla sobre lo que cruza el medidor, no sobre lo que
dos miembros de la comunidad acuerdan entre ellos.

La Resolución CREG 101 072 lo confirma para el colectivo. Su artículo 23 dice
que los excedentes se tratan **asociando cada frontera comercial de forma
independiente**, «con la misma forma en que se trata un AGPE». Y define el
reparto en dos tramos **sobre lo asignado a cada usuario**:

- **`Exc1`**: los excedentes del colectivo asignables al usuario **hasta el
  valor de sus importaciones**, es decir la permuta.
- **`Exc2`**: los que quedan **por encima** de esas importaciones, es decir la
  bolsa.

La palabra que decide es **asignables**. Los tramos se cuentan sobre lo que le
toca a cada usuario tras el reparto del colectivo, no sobre su producción
bruta.

### Lo que hace nuestro código

En los tres sitios que lo usan, el orquestador y dos sondas, el tramo se
calcula así:

    tramo_permuta(G, D, mes)

Con la generación y la demanda **brutas**, como si todo el excedente fuera
entregado al comercializador. **Ignora que parte de ese excedente se queda
dentro de la comunidad.**

### Qué implica, y por qué puede favorecer a la comunidad

Si un vendedor coloca energía dentro de la comunidad, esa energía **no agota
su permuta**, porque no se la entregó al comercializador. De modo que el
vendedor **se queda en permuta más tiempo** del que el modelo supone.

Eso sube su piso, y subir el piso cambia tres cosas a la vez: el ancho de la
banda, el reparto entre vendedor y comprador, y quién participa. **No se sabe
de qué tamaño es el efecto ni en qué dirección queda el neto.**

### La circularidad, que es lo que hace el problema interesante

**El tramo depende de cuánto se vendió dentro, y cuánto se vende dentro
depende del piso, que depende del tramo.**

Nuestro cálculo evita esa circularidad resolviéndola por el lado bruto, que es
la respuesta que se obtiene si se supone que no hay mercado interno. **Es una
simplificación, y nadie la había declarado.**

Resolverla de verdad exige un punto fijo: calcular el tramo, resolver el
mercado, recalcular el tramo con lo que quedó sin vender dentro, volver a
resolver, y repetir hasta que el tramo deje de moverse. Como todo punto fijo,
puede no converger, y hará falta una cota de vueltas y declarar qué se hace
cuando se agota.

### Una distinción que conviene no perder

**Ninguna condición saca a un vendedor del mercado entre pares por el tramo.**
El tramo solo cambia su piso, es decir cuánto vale su alternativa. Lo que lo
saca del mercado es la **restricción de participación** de C-151: se retira si
el mercado le paga menos que esa alternativa por el conjunto de lo que coloca.

> **El tramo dice cuánto vale su alternativa. La participación dice si el
> mercado la bate.**

Son dos mecanismos distintos y confundirlos lleva a buscar la causa de un
retiro en el sitio equivocado.

### La circularidad se deshace sola, y eso abarata el arreglo

La sospecha era que hacía falta un punto fijo caro. **No hace falta.** Por
D-7, el volumen transado en una hora es el lado corto, el mínimo entre la
oferta y la demanda netas, y **no depende del precio**. De modo que cuánto
coloca la comunidad dentro se sabe sin jugar la partida: se reparte el lado
corto entre los vendedores en proporción a su excedente.

Queda un único lazo de verdad, y es de segundo orden: el piso decide quién se
retira por la restricción de participación, y un retiro cambia el volumen. Ese
canal vale del orden del 0,5 % del volumen, medido el 2026-09-07.

### Las tres lecturas, porque no son dos

Al medirlo aparece una distinción que la pregunta original no tenía. El piso
no es un precio: es **el punto de amenaza**, lo que el vendedor obtiene si no
negocia. Y la posición acumulada del mes es un hecho, no una hipótesis:

1. **Bruto**, lo actual. Todo el excedente, pasado y presente, cuenta como
   inyectado. Es la respuesta que sale si se supone que no hay mercado
   interno.
2. **Residual puro.** Solo cuenta lo que de verdad cruzó el medidor. Es lo que
   la Resolución CREG 101 072 liquida.
3. **Historia residual, margen bruto.** La posición acumulada es la real, es
   decir la residual; y con esa posición se pregunta qué le pagarían por el
   kWh de esta hora si no lo vendiera dentro. **Es el punto de amenaza
   correcto**, y coincide con la contabilidad de la norma en todo salvo la
   hora en curso, que sobre un acumulado mensual es despreciable.

La tercera es la que este hallazgo defiende. La medición de abajo la estima.

### Lo medido, y desmiente lo que este hallazgo suponía

Se supuso que la lectura residual favorece a la comunidad. **En una frontera
sí y en la otra no**, y por una razón que conviene entender.

| Sobre el horizonte completo | Principal (M1) | Secundaria (M3) |
|---|---:|---:|
| Horas-vendedor | 1.792 | 8.968 |
| En bolsa según el excedente **bruto** | 339 · 18,9 % | 7.733 · 86,2 % |
| En bolsa según el excedente **residual** | **0 · 0,0 %** | **7.791 · 86,9 %** |
| Horas-vendedor que cambian de tramo | 339 · 18,9 % | 294 · 3,3 % |
| Piso medio ponderado por excedente, bruto | 506,5 | 210,8 |
| Piso medio ponderado por excedente, residual | **684,2** | **203,8** |
| Ancho de banda medio ponderado, bruto | 223,2 | 516,1 |
| Ancho de banda medio ponderado, residual | **45,5** | **523,1** |
| Bandas invertidas | 0 | 0 |

Todo en (COP/kWh).

**En la principal el cambio es enorme y va en un sentido; en la secundaria es
pequeño y va en el contrario.** El motivo está en el lado corto. En la
principal la oferta es escasa, de modo que casi todo el excedente se coloca
dentro y **nadie llega a agotar su permuta**: ningún vendedor pisa la bolsa en
todo el horizonte. En la secundaria la oferta sobra: el mercado interno agota
el déficit mucho antes que el excedente, y como el retiro de la red también
encoge, **el cruce llega antes**, no después.

### Y la consecuencia que hay que leer con H-47 en la mano

En la principal el ancho de banda cae de 223,2 a 45,5, es decir **un 80 %**. Y
por la identidad de H-33, el excedente del mercado es el ancho por la energía
transada. De modo que la lectura residual **recortaría el excedente medido del
mercado entre pares a una quinta parte en la frontera principal**.

Sería un error leer eso como que la comunidad pierde. Es justo lo que H-47
advierte: **el excedente crece cuando la alternativa empeora, no cuando la
comunidad mejora**. Bajo la lectura residual la red le paga permuta al
vendedor por todo, en vez de pagarle bolsa el 19 % de las veces; la comunidad
está mejor y el mercado aporta menos, porque queda menos que arreglar.

Cuál de las dos cosas se reporta, y con qué palabras, es una decisión del
documento y no del código.

### Qué se decide y qué no

**No se cambia el cálculo todavía.** Es una ambigüedad regulatoria de las que
este proyecto manda consultar en vez de resolver por cuenta propia, y las dos
primeras lecturas son defendibles: la bruta es la que el medidor registra,
porque la energía del mercado entre pares **sí cruza físicamente la
frontera**; la residual es la que la letra del artículo 23 sugiere, porque
habla de excedentes **asignables** tras el reparto.

**Va como pregunta al asesor**, con la tabla de arriba delante, que es lo que
la vuelve una pregunta concreta. Mientras tanto queda declarada como
simplificación, y el orquestador la imprime en cada corrida.

**Coste de implementarla, ahora que se sabe que no hace falta punto fijo:** un
paso más sobre los datos y ninguna partida de más. Se calcula el lado corto
por hora, se reparte entre vendedores, se acumula sobre lo residual y se
evalúa el tramo. Del orden de treinta líneas en el módulo de opciones
externas y un cambio en los tres sitios que lo llaman. La versión exacta,
la que usa el reparto verdadero en vez del proporcional, cuesta **una
corrida completa de más**, porque necesita el reparto del mercado que solo
existe después de jugarlo.

Ver H-52, que mide los regímenes del piso, y H-47, que explica por qué el
excedente engaña.

---

## H-54 · La sonda y la corrida no negociaban con el mismo precio de bolsa

**Estado: CORREGIDO el 2026-09-08 por C-154, con el efecto medido antes de
tocar nada: es nulo, y se explica por qué.**

La sonda de paso a paso y el orquestador leen el mismo fichero de precios de
bolsa. El orquestador le aplica después el techo de escasez de la Resolución
CREG 101 066; la sonda no. Dos caminos que se creían equivalentes daban
precios distintos en las horas de punta.

**Medido:** el techo muerde en 20 horas de 6.144, y **ninguna de las veinte
tiene un vendedor** en ninguna de las dos fronteras. La razón no es el azar:
el techo muerde en punta nocturna y el excedente fotovoltaico es diurno.

De modo que nada de lo que la sonda ha medido cambia, incluido el experimento
del régimen del piso. Se corrige igual, porque una coincidencia que depende
del dato no es una garantía.

**Lo que conviene retener:** cuando dos caminos calculan lo mismo por
separado, la comprobación no es que coincidan en el resultado publicado, sino
que **coincidan en las entradas**. Aquí coincidían en el resultado por una
propiedad del clima solar.

---

## H-55 · El bienestar del modelo base no puede arbitrar una pregunta sobre el piso

**Estado: PROBADO el 2026-09-08, algebraicamente y a precisión de máquina. Lo
abrió una pregunta del autor: «¿el bienestar en qué unidades lo estás
midiendo?».**

### Primero, las unidades, porque la respuesta es que no hay una

La función que el modelo base maximiza suma términos de dimensiones distintas:

| Término | Qué multiplica |
|---|---|
| dotación | un coeficiente adimensional por potencia |
| cuadrático | potencia al cuadrado |
| costo del vendedor | un costo nivelado (COP/kWh) por potencia |
| competencia | un precio (COP/kWh) por potencia |
| pago | **energía dividida por el logaritmo del precio** |

El último es el que más llama la atención: el pago no es precio por energía,
sino energía **dividida por el logaritmo del precio**, con el precio metido
dentro del logaritmo como si fuera un número puro. De modo que el resultado
**no está en pesos ni en kilovatios hora**: es un índice de utilidad en
unidades mixtas, y no es comparable con la factura.

Eso ya bastaría para no enfrentarlo a la factura en una misma tabla. Pero hay
algo más.

### El pago se cancela entre los dos lados

El término de pago del vendedor es la energía que coloca dividida por el
logaritmo del precio, **con signo negativo**; el del comprador es la energía
que recibe dividida por el mismo logaritmo, **con signo positivo**. Sumados
sobre las dos poblaciones son la misma suma con signo opuesto.

Comprobado, también con precios distintos por comprador y reparto asimétrico:

| Precios (COP/kWh) | Pago del vendedor | Pago del comprador | Suma |
|---|---:|---:|---:|
| 523,1 · 455,9 · 577,7 | −1,74578 | +1,74578 | −2,8·10⁻¹³ |
| 121,2 · 879,3 · 352,8 | −1,54160 | +1,54160 | −2,6·10⁻¹³ |
| 671,4 · 411,9 · 190,9 | −1,74866 | +1,74866 | −3,0·10⁻¹³ |

Y reconstruyendo el bienestar total **sin** los términos de pago se obtiene el
mismo número, con diferencia de 1,1·10⁻¹³.

### Lo que queda, y por qué decide el resultado

Cancelado el pago, la **única** dependencia del bienestar respecto del precio
es la penalización de competencia, que es negativa y proporcional al precio.

> **De donde se sigue que el bienestar total crece siempre que el precio baja,
> y el precio baja siempre que el piso baja.**

**El régimen de bolsa no gana en bienestar: gana por construcción.** Esa
columna del experimento de H-52 no mide que la comunidad esté mejor, mide que
el piso es más bajo.

### Qué se hace con esto

**El bienestar se sigue informando**, porque es la función que el modelo base
maximiza y el lector la espera. Pero **no arbitra la elección del régimen del
piso**, y la tabla tiene que decirlo donde se publique.

Quien arbitra es la **factura**, que sí está en pesos y sí contiene lo que la
red paga por el excedente que se exporta. Ver H-52 para el resultado y H-47
para la misma trampa vista desde el excedente.

### Verificacion

`tests/gate_h55_bienestar_precio.py`, en verde, con las tres comprobaciones
sobre casos al azar:

| | Medido |
|---|---|
| Los pagos se cancelan, 200 casos con precios y repartos distintos | peor resto 7,5·10⁻¹³ |
| El total reconstruido sin los pagos coincide | peor resto 1,8·10⁻¹² |
| El bienestar baja al subir el precio, 50 casos × 40 precios | cero excepciones |

**Alcance, y conviene acotarlo:** esto no invalida el modelo base ni los
resultados publicados. El bienestar sigue sirviendo para lo que se usa en el
resto del documento, que es comparar configuraciones **con la misma banda**.
Deja de servir en cuanto la banda es lo que cambia entre las alternativas que
se comparan, que es exactamente el caso de H-52 y de H-53.

---

## H-52 · MEDIDO el 2026-09-08: la predicción acierta la mitad

La medición de los tres regímenes del piso, sobre una muestra de 40 horas por
frontera sorteada con semilla fija, con la vía acoplada y la configuración de
CAL-50. De 240 tareas resolvieron 237; las tres que no son la hora 3394 de la
frontera principal en dos regímenes y la 2913 en el tercero, y quedan anotadas
como no resueltas conforme a H-51.

**Un aviso sobre cómo NO leerla.** La sonda imprime además variaciones por
hora en porcentaje, y en la frontera secundaria no significan nada: allí la
factura ronda el cero y cambia de signo, de modo que el cociente da valores
como −231,60 % sin contenido. La comparación válida es en pesos y sobre horas
emparejadas, que es la que sigue.

### Frontera principal · 38 horas con los tres regímenes

| Régimen | Piso medio | Bienestar | Factura (COP) | Dif. factura | Volumen (kWh) | Dif. vol. | Retirados | Excedente |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| tramo | 484,7 | 27.918,7 | **540.856,3** | — | 154,34 | — | 7 | 42.301,8 |
| permuta | 674,5 | 25.968,3 | 545.115,7 | **+4.259,5** | 147,93 | −4,15 % | 4 | 9.962,9 |
| bolsa | 168,5 | 35.523,1 | 541.282,8 | +426,5 | 155,59 | +0,81 % | 0 | 94.548,8 |

### Frontera secundaria · 40 horas con los tres regímenes

| Régimen | Piso medio | Bienestar | Factura (COP) | Dif. factura | Volumen (kWh) | Dif. vol. | Retirados | Excedente |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| tramo | 165,2 | 31.030,6 | −16.568,4 | — | 97,93 | — | 14 | 60.568,4 |
| permuta | 673,9 | 29.732,5 | **−180.376,8** | **−163.808,4** | 96,73 | −1,23 % | 10 | 9.058,1 |
| bolsa | 165,2 | 35.549,2 | −27.888,0 | −11.319,6 | 101,28 | +3,42 % | 0 | 62.368,1 |

Los pisos medios de tramo y bolsa coinciden en la secundaria porque allí el
89,1 % del excedente ya se liquida en bolsa, de modo que forzar el régimen
cambia poco el piso y mucho quién participa.

### La predicción, contrastada

Decía: «la factura apenas se moverá salvo por el cambio de volumen, y el
régimen de bolsa moverá más energía porque retira menos vendedores. Si es así,
el piso de bolsa sería mejor para la comunidad, pero por participación y no por
precio».

| Parte | Veredicto |
|---|---|
| El régimen de bolsa no retira a nadie | **acierta**, cero retirados en las dos |
| Y mueve más energía | **acierta**, +0,81 % y +3,42 % |
| La factura apenas se moverá salvo por volumen | **falla** |
| El piso de bolsa sería el mejor para la comunidad | **falla** |

**Dónde falla el razonamiento, que es lo que hay que retener.** El argumento de
que el precio se cancela es cierto para lo que se negocia dentro, y H-33 lo
prueba. Pero el piso **no es solo el precio de dentro**: es además el precio al
que la red compra lo que sobra, y eso no se cancela con nada. En la frontera
secundaria ese canal mueve 163.808 (COP) en cuarenta horas, **diez veces la
factura entera del régimen actual**.

### Dos canales, y gana uno distinto en cada frontera

**En la principal manda el volumen.** La oferta es escasa y casi no queda
excedente que exportar, de modo que subir el piso no cobra casi nada de la red
y en cambio estrecha la banda hasta cerrar el mercado en algunas horas: la
permuta pierde un 4,15 % de energía y sale la peor de las tres, **aun teniendo
menos vendedores retirados que el régimen actual**. Gana el tramo, que es lo
que el modelo ya hace.

**En la secundaria manda el precio.** Sobra excedente, se exporta mucho, y que
la red lo pague a permuta en vez de a bolsa vale mucho más que cualquier cosa
que el volumen pueda mover. Gana la permuta con diferencia.

### El bienestar no arbitra, y eso está probado aparte

El bienestar señala el régimen de bolsa en las dos fronteras. **No hay que
hacerle caso aquí**, y no por desconfianza sino porque H-55 demuestra que la
función solo depende del precio a través de la penalización de competencia, de
modo que prefiere el piso más bajo por construcción. La columna se informa
porque es la función del modelo base, no porque decida.

### Qué se decide

**El modelo conserva el régimen de tramo**, que ya era lo previsto y ahora
tiene respaldo: es el mejor de los tres en la frontera principal y describe,
además, la alternativa real de cada vendedor.

Lo que la medición añade es una **recomendación para la comunidad**, que no es
lo mismo que un cambio de modelo: en una frontera de cobertura alta, negociar
con el piso de permuta valdría mucho dinero, y eso depende de la lectura del
tramo que H-53 deja abierta.

### Lo que le hace a H-53

La lectura por excedente asignado deja a la frontera principal **sin ningún
vendedor en bolsa**, es decir en el régimen de permuta, que aquí resulta ser
**el peor de los tres**: costaría 4.259,5 (COP) en treinta y ocho horas, un
0,79 % más de factura.

**De modo que cambiar el cálculo del tramo no es gratis ni es obviamente
mejor.** Sale a favor donde sobra excedente y en contra donde escasea. La
pregunta al asesor sigue en pie, y ahora va con el precio puesto.

---

## H-56 · Contra qué mide su mejora el modelo base, y por qué importa aquí

**Estado: REVISADO en la fuente el 2026-09-08, a petición del autor. No es un
defecto: es el estándar con el que hay que juzgar las mediciones del piso, y
no lo estábamos aplicando entero.**

### Lo que el modelo maximiza

El bienestar de la comunidad, es decir la suma del de vendedores y el de
compradores. Eso es el objetivo de los tres algoritmos del artículo.

### Lo que el artículo EVALÚA, que no es lo mismo

De su apartado de conclusiones, tres perspectivas, y **ninguna es una
factura**:

1. **Autosuficiencia y autoconsumo**, con y sin el programa de respuesta a la
   demanda. El resultado que reporta es físico: un 24 % menos de energía
   vendida a la red y un 53 % menos comprada.
2. **El bienestar frente a otro algoritmo**, el suyo contra el de referencia.
   Es una comparación algorítmica, no regulatoria.
3. **El índice de equidad y el reparto del bienestar**, contra el método
   centralizado.

**El modelo base no tiene una factura.** La comparación monetaria contra la
regulación colombiana es aporte de esta tesis, no del modelo que traduce.

### Las dos métricas, literales

El índice de equidad global:

> IE = (suma del ahorro de los compradores − suma del ingreso de los
> vendedores) / (suma de los dos)

Cerca de cero es equitativo; hacia −1 favorece desproporcionadamente a los
vendedores y hacia +1 a los compradores. Y el reparto en porcentaje es cada
sumando sobre el total.

Su Tabla VII, que es el resultado que sostiene el artículo:

| Método | Índice | % comprador | % vendedor |
|---|---:|---:|---:|
| Replicador | 0,0149 | 50,747 | 49,253 |
| Lagrangiano | 0,0006 | 50,028 | 49,972 |
| Centralizado | **−0,8913** | 5,436 | **94,564** |

El argumento es ese: el centralizado entrega el 94,6 % al vendedor y
desincentivaría la participación de los consumidores; los descentralizados
reparten casi mitad y mitad.

### Por qué esto cambia la lectura del experimento del piso

**El ahorro del comprador y el ingreso del vendedor son exactamente los dos
sumandos que en nuestro código forman el excedente.** Y el segundo se mide
**contra el piso**. De modo que el índice de equidad **se mueve con el régimen
del piso**: bajarlo ensancha el margen del vendedor sobre su alternativa y
empuja el índice hacia su lado.

Es decir, **la métrica con la que el autor del modelo juzgaría precisamente
esta pregunta faltaba en el experimento**. La sonda guardaba la suma de los dos
sumandos y no cada uno.

Corregido: la sonda informa ahora el índice y el reparto, agregados sobre las
sumas del periodo y no promediando cocientes por hora.

### Y la advertencia que hay que llevar junta

El índice de equidad **no es equidad distributiva entre agentes**: es un
balance entre los dos bandos. Dos comunidades con el mismo índice pueden
repartir de forma muy distinta entre sus miembros. Por eso este trabajo usa
además el coeficiente de Gini, y por eso conviene no traducir «índice cercano a
cero» por «reparto justo».

Ver H-52 para el experimento, H-55 para por qué el bienestar no arbitra, y
H-31, que queda pendiente sobre el índice.

---

## H-52 y H-53 · CERRADOS el 2026-09-08 sobre el horizonte completo

**Medido en el servidor con 32 procesos: las 2.937 horas activas de las dos
fronteras, bajo los cuatro regímenes del piso, con la vía acoplada. 11.748
partidas, todas resueltas, ninguna hora perdida y ninguna métrica no
numérica.**

Esto **sustituye** la medición de muestra del mismo día, y la contradice en lo
principal. Se deja constancia de las dos porque la lección importa.

### Frontera principal · 1.126 horas

| Régimen | Piso | Bienestar | Factura (COP) | Dif. | Volumen (kWh) | Dif. | Retir. | Excedente | Equidad | % compr. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tramo | 504,4 | 880.779,5 | 16.725.977,1 | — | 4.182,83 | — | 348 | 1.124.150,8 | **−0,0212** | 48,94 |
| permuta | 673,8 | 817.109,9 | **16.490.811,9** | **−235.165,2** | 4.110,69 | −1,72 % | 170 | 274.651,9 | −0,1793 | 41,03 |
| bolsa | 151,4 | 995.529,1 | 16.762.643,0 | +36.665,9 | 4.592,75 | +9,80 % | 0 | 2.738.188,7 | 0,0133 | 50,67 |
| **residual** | 673,8 | 817.109,9 | **16.490.811,9** | **−235.165,2** | 4.110,69 | −1,72 % | 170 | 274.651,9 | −0,1793 | 41,03 |

### Frontera secundaria · 1.811 horas

| Régimen | Piso | Bienestar | Factura (COP) | Dif. | Volumen (kWh) | Dif. | Retir. | Excedente | Equidad | % compr. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tramo | 165,0 | 1.204.010,6 | 1.387.424,2 | — | 4.479,95 | — | 534 | 2.753.228,6 | 0,5032 | 75,16 |
| permuta | 677,7 | 1.148.862,3 | −4.898.490,4 | −6.285.914,5 | 4.380,07 | −2,23 % | 508 | 414.001,0 | **0,3951** | 69,75 |
| bolsa | 158,8 | 1.347.702,2 | 1.085.084,7 | −302.339,5 | 4.529,25 | +1,10 % | 0 | 2.797.795,0 | 0,5024 | 75,12 |
| **residual** | 166,3 | 1.229.846,0 | **1.312.653,8** | **−74.770,4** | 4.492,99 | +0,29 % | 456 | 2.746.156,3 | 0,5030 | 75,15 |

### H-53 confirmado: en la frontera principal nadie cruza

**El régimen residual es idéntico al de permuta, cifra por cifra**, en la
factura, el volumen, los retirados y el índice. Bajo la lectura por excedente
asignado **ningún vendedor de la frontera principal llega a agotar su permuta
en todo el horizonte**, que es exactamente lo que la sonda barata predijo sin
resolver una sola partida.

### La muestra se equivocaba, y en el sentido contrario

| Frontera principal | Con 38 horas | Con 1.126 horas |
|---|---|---|
| Mejor factura | el **tramo**, es decir lo actual | el **residual**, por 235.165,2 (COP) |
| Peor factura | la permuta | la bolsa |

**Con la muestra se concluyó lo contrario de lo que sale con el horizonte.**
No fue un error de método, fue tamaño: 38 horas de 1.126 no representan el
reparto entre tramos a lo largo de nueve meses, porque el cruce a bolsa es un
fenómeno **acumulativo dentro del mes** y depende de dónde caiga la hora.

**La norma que se lleva de aquí:** una muestra al azar sirve para acotar el
orden de magnitud de un efecto, **no para ordenar alternativas que difieren
poco entre sí**. Los tres regímenes se separaban en la muestra por menos del
1 % de la factura, y ese margen está por debajo de lo que 38 horas resuelven.

### La factura prefiere la lectura residual en las DOS fronteras

| | Ahorro de la lectura residual |
|---|---|
| Principal | **−235.165,2 (COP)**, un 1,41 % de la factura |
| Secundaria | **−74.770,4 (COP)**, un 5,39 % |

### Pero la equidad dice lo contrario en la principal, y hay que decirlo

| Índice de equidad | tramo | permuta | bolsa | residual |
|---|---:|---:|---:|---:|
| Principal | **−0,0212** | −0,1793 | 0,0133 | −0,1793 |
| Secundaria | 0,5032 | 0,3951 | 0,5024 | 0,5030 |

**En la frontera principal el régimen actual es el más equitativo de los
cuatro**, con un reparto de 48,94 contra 51,06 entre compradores y vendedores.
Está prácticamente en el punto que el modelo base persigue: el método de
replicador de Chacón da 0,0149 en su Tabla VII. La lectura residual lo
desplaza a −0,1793, es decir hacia el vendedor.

En la secundaria la equidad no distingue: 0,5032 frente a 0,5030.

> **El dilema, con cifras: la lectura residual paga mejor y reparte peor.** En
> la frontera principal gana 235.165 (COP) y pierde 0,158 de índice.

**Eso es lo que va al asesor**, y ya no como pregunta abstracta.

### Los seis millones de la permuta forzada no están disponibles

Es la trampa de la tabla y conviene señalarla. En la secundaria la permuta
forzada da −6.285.914,5, pero **no es alcanzable**: modela a un vendedor que
rechaza el precio de bolsa cuando ya agotó su permuta.

La única vía real a ese terreno es la lectura residual, y allí el tramo apenas
se mueve, un 3,3 % de las horas-vendedor. **Lo que la comunidad puede capturar
de verdad en la secundaria son 74.770 (COP), no seis millones.**

### Tres cosas más que la tabla enseña

**Los retiros los manda la DISPERSIÓN del piso, no su nivel.** En la principal
el tramo retira 348 vendedores; la permuta, con un piso mucho más alto, solo
170; y la bolsa, con el piso más bajo pero **uniforme**, no retira a ninguno.
Confirma lo que C-151 anticipó al escribirla: la restricción es inerte cuando
las cotas son uniformes por construcción.

**Más volumen no es mejor factura.** En la principal el régimen de bolsa mueve
un 9,80 % más de energía que el actual y aun así **paga más**: 36.665,9 (COP)
de más. El volumen no es el objetivo, y quien lo use como tal se equivocará de
signo.

**En la secundaria el régimen del piso pesa más que el mercado entero.** El
mercado aporta 2.753.228,6 y cambiar de régimen mueve 6.285.914,5. Son **2,3
veces**, no las 3,5 que estimó la muestra. Sigue siendo una conclusión
incómoda para el documento y hay que escribirla.

### Qué se decide

**El modelo conserva el régimen de tramo.** Describe la alternativa real de
cada vendedor y es el más equitativo en la frontera principal.

**La lectura del tramo va al asesor con la tabla delante**, porque su
respuesta vale 235.165 (COP) en una frontera, 74.770 en la otra, y 0,158 de
índice de equidad en contra.

**Y el bienestar no participó en ninguna de estas decisiones**, por H-55.

---

## H-57 · El índice de equidad global del régimen actual lo dominan dos meses

**Estado: MEDIDO el 2026-09-08, al desglosar por mes la corrida del horizonte
completo. Rectifica una lectura que se dio por buena horas antes en este mismo
registro.**

### Lo que se había concluido, y era falso

Que en la frontera principal el régimen de tramo es «el más equitativo de los
cuatro, prácticamente en el punto que el modelo base persigue», por su índice
global de −0,0212 frente al −0,1793 de la lectura residual.

### Lo que el desglose enseña

**El efecto vive en dos meses de nueve.** En siete de los nueve meses la
diferencia entre el tramo y la lectura residual es **exactamente cero**: nadie
cruza a bolsa bajo la lectura bruta, de modo que los dos regímenes **son el
mismo régimen**. Todo el ahorro de 235.165,2 (COP) sale de junio y julio, y el
98,3 % lo aporta un decil de las horas.

Y de ahí el artefacto:

| Frontera principal | Índice global | Sin junio ni julio | Peso de esos dos meses |
|---|---:|---:|---:|
| tramo | **−0,0212** | **−0,1785** | **83,9 %** |
| permuta | −0,1793 | −0,1785 | 34,1 % |
| bolsa | 0,0133 | 0,0058 | 39,3 % |
| residual | −0,1793 | −0,1785 | 34,1 % |

**Fuera de esos dos meses los dos regímenes dan el mismo índice**, −0,1785,
como tiene que ser. Lo que ocurre es que bajo el tramo esos dos meses
concentran el **83,9 %** del excedente total, frente al 34,1 % bajo la lectura
residual.

### El mecanismo, que es el de siempre

En junio y julio el tramo manda a un vendedor a bolsa. Su piso se desploma, la
banda se ensancha y el excedente de esos dos meses se dispara. Como el índice
es un cociente sobre la **suma** del ahorro y el ingreso, esos dos meses
arrastran el agregado hacia su propio valor.

> **El −0,0212 no describe un mercado más equitativo. Describe dos meses de
> excedente enorme repartido a medias.**

Es la trampa de H-47 aplicada al índice en vez de al excedente: **la métrica
mejora cuando la alternativa externa empeora.**

### La norma que se deriva, y este proyecto ya la tiene dos veces

**Un índice que es cociente de sumas se pondera solo, y hay que preguntarle
por qué.** Antes de comparar dos índices globales hay que mirar si sus
denominadores pesan lo mismo. Aquí no lo hacían ni de lejos: 83,9 % contra
34,1 %.

Se suma a la lección de la frontera correcta y a la de los objetos distintos
con el mismo rótulo. Las tres son la misma familia: **comparar cosas que no
son comparables porque el agregado las hizo parecer así.**

### Qué queda en pie

El dilema entre factura y equidad **sigue existiendo pero acotado**: en junio y
julio la lectura residual paga mejor y reparte peor. En los otros siete meses
de la frontera principal **no hay nada que decidir**, porque los dos regímenes
son idénticos.

En la frontera secundaria no hay artefacto: excluir sus dos meses activos mueve
los cuatro índices por igual, de 0,50 a 0,48.

Ver H-52, H-47 y H-56.

