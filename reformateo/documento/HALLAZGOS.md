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
