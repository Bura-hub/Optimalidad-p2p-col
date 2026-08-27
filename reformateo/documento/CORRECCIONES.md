# Registro de correcciones

Toda corrección que se aplique al documento se anota aquí, esté aplicada o
pendiente. El registro existe por dos razones: porque una corrección sin
registrar se vuelve a cometer, y porque varias de estas afectan también a
la tesis y al artículo, de modo que hay que poder rastrearlas.

**Formato de cada entrada:** identificador, fecha, qué decía, qué dice
ahora, por qué, y dónde se aplicó. Los tipos son: `nombre` (nombre propio
o denominación oficial), `dato` (cifra o hecho), `estilo` (registro de
redacción), `técnico` (LaTeX, código o figura).

---

## C-1 · «el programa» era ambiguo
**2026-08-22 · tipo: `nombre` · aplicada**

Decía «el orden fijo que emplea el programa». En una tesis de la Maestría
en Ingeniería Electrónica, «el programa» se lee primero como el programa
académico. Se quería decir el código.

Se sustituyó por una referencia a la constante `AGENTS` de
`data/xm_data_loader.py`, con la intención de añadir trazabilidad.
**Esa solución resultó peor que el problema y quedó revertida en C-12**:
citar un identificador de código en la prosa introduce un ruido que el
registro del autor no tiene.

Aplicado en `02-dato-crudo.tex` y, por el mismo motivo, en las otras dos
apariciones de `03-preprocesamiento.tex` («el código las ejecuta», «la
ejecución se detiene»), que sí se conservan porque ahí la palabra se
sustituyó sin añadir nada.

---

## C-2 · Universidad CESMAG, no Institución Universitaria
**2026-08-22 · tipo: `nombre` · aplicada**

Decía «la Institución Universitaria Cesmag». Ese nombre dejó de ser válido
el 12 de abril de 2019, cuando la Resolución 004012 del Ministerio de
Educación Nacional reconoció a la entonces Institución Universitaria
Centro de Estudios Superiores María Goretti como universidad y dispuso que
pasara a denominarse **Universidad CESMAG**, con sigla **UNICESMAG**.

Además va en mayúsculas sostenidas. La propia universidad cometió el error
de escribir «Universidad Cesmag» en su Acuerdo 001 de 2019 y lo corrigió
expresamente con el **Acuerdo 015 del 8 de septiembre de 2022**.

Aplicado en `02-dato-crudo.tex`.

---

## C-3 · El HUDN lleva E.S.E. en la razón social
**2026-08-22 · tipo: `nombre` · aplicada**

Decía «el Hospital Universitario Departamental de Nariño». Falta el
**E.S.E.**, que forma parte de la razón social y es justamente lo que
marca su naturaleza pública: se constituyó como Empresa Social del Estado
por la Ordenanza 067 del 10 de diciembre de 1994 de la Asamblea
Departamental de Nariño. Ese dato importa aquí porque la naturaleza
jurídica de cada entidad se usa para distinguir la categoría tarifaria
oficial de la comercial.

Aplicado en `02-dato-crudo.tex`.

---

## C-4 · La UCC dice «campus», no «sede»
**2026-08-22 · tipo: `nombre` · aplicada**

Decía «la Universidad Cooperativa de Colombia» sin precisar la sede. La
propia universidad adoptó el modelo *multicampus* entre 2021 y 2022 y desde
entonces denomina **campus** a lo que antes eran sedes. Se escribe, pues,
«campus Pasto». Conviene además no llamarla «seccional»: el campus Pasto
no tiene código de institución propio en el registro del Ministerio.

Aplicado en `02-dato-crudo.tex`.

---

## C-5 · No todas las entidades están en el casco urbano
**2026-08-22 · tipo: `dato` · aplicada**

Decía «cinco entidades del casco urbano de Pasto». Es falso: el sistema
fotovoltaico de la Universidad CESMAG está en el **Campus Universitario
San Damián**, en el corregimiento de **Catambuco**, fuera del perímetro
urbano.

Ahora dice «cinco entidades del municipio de Pasto», y un párrafo nuevo
precisa que cuatro de los cinco sistemas están en el casco urbano y uno
fuera.

Aplicado en `02-dato-crudo.tex`.

---

## C-6 · Dónde está realmente cada sistema fotovoltaico
**2026-08-22 · tipo: `dato` · aplicada**

En dos de los cinco casos la instalación no está en la sede principal de
la entidad, y el documento no lo decía. Importa porque de la ubicación
depende **qué carga acompaña a la generación**, que es de lo que trata el
capítulo 4 entero.

| Entidad | Dónde está el sistema |
|---|---|
| Udenar | Bloque Sur de la sede Torobajo, que es un edificio del campus y no una sede aparte |
| Mariana | **Campus Deportivo Alvernia**, sector occidental, no el campus académico de Versalles |
| UCC | Campus Pasto, sector Torobajo |
| HUDN | Sede única, Parque Bolívar |
| CESMAG | **Campus Universitario San Damián**, corregimiento de Catambuco |

El caso de Mariana explica un detalle que estaba a la vista sin leerse:
los equipos se llaman `Medidor 1 - Alvernia` y `Fronius - Alvernia` porque
están en el campus deportivo. Encaja con que la tesis aproxime su demanda
M3 escalando por 0,3 «la carga de la única facultad servida por su sistema
fotovoltaico (sede Alvernia)».

Aplicado en `02-dato-crudo.tex`.

---

## C-7 · La raya larga no es del registro del autor
**2026-08-22 · tipo: `estilo` · aplicada**

El texto usaba 58 rayas largas en cuatro capítulos, a razón de 8,46 por
mil palabras. El corpus del autor registra **cero en 20.238 palabras**: sus
incisos van entre comas o entre paréntesis, y la raya corta la reserva
para rangos numéricos.

Convertidas las 58: 20 incisos a paréntesis (cuando llevaban comas
internas o iban seguidos de «y») y 10 a comas. Es el rasgo que más
delataba que el texto no lo había escrito él.

Aplicado en los cuatro capítulos.

---

## C-8 · Faltaban los tres rasgos de figura del autor
**2026-08-22 · tipo: `estilo` · aplicada**

El corpus del autor tiene tres hábitos que el documento no seguía:

1. Referir cada figura como «La Figura N + verbo» al final del párrafo que
   la motiva, con verbo transitivo (ubica, reúne, muestra, pone, resume,
   presenta, cruza). Nunca «(Figura N)», «se observa» ni «véase». Había 2
   casos; ahora 9.
2. Un párrafo que empieza por **«Nota.»** bajo cada figura, que dice lo
   que la figura revela y el texto no, y cierra con la procedencia. Había
   0; ahora 17, mediante el comando `\notafig{}`.
3. Cerrar cada capítulo con un párrafo bisagra que recoge la cifra clave y
   anuncia el capítulo siguiente. Había 0; ahora 3.

---

## C-9 · La serie de bolsa se promediaba fuera del horizonte
**2026-08-22 · tipo: `dato` · aplicada**

El archivo `data/precios_bolsa_xm_api.csv` cubre hasta enero de 2026,
mientras que el horizonte del estudio termina el 16 de diciembre de 2025.
Las figuras del capítulo 5 promediaban el archivo completo y daban
**193,6 COP/kWh** en vez de **182,5**, una diferencia del 6,1 % que se
habría propagado a toda comparación con la tarifa.

El recorte lo aplica ahora el propio lector `datos.precios_bolsa()`, para
que no dependa de que cada script lo recuerde.

---

## C-10 · Dos defectos de figura que anulaban su argumento
**2026-08-22 · tipo: `técnico` · aplicada**

En `f11_08_lado_corto` el panel derecho rotulaba «lo escaso es el recurso»
en las dos coberturas, con lo que la figura contradecía lo que pretendía
mostrar. En las dos la generación es el lado corto; lo que cambia es
cuánto. Ahora declara la razón G/D y dice, en M1, que la demanda queda tan
por encima que moverla no cambia el volumen, y en M3, que las dos
magnitudes se acercan y la demanda empieza a limitar.

En `f3_08_perfiles_instituciones` la demanda de la UCC salía del mismo
verde que la curva de generación. Se cambió el color de la UCC a vino en
la paleta, dejando anotado en `estilo.py` por qué ninguna institución
puede llevar el verde de C5.

---

## C-11 · Cuatro tropiezos del entorno LaTeX
**2026-08-22 · tipo: `técnico` · aplicada**

1. **`siunitx` no sirve aquí.** MiKTeX 24.1 distribuye un `expl3` anterior
   al `siunitx` que instala, y falla con
   `\l_siunitx_quantity_prefix_mode_str` indefinido. Se usa `numprint`.
2. **`\pct` solo funciona en modo texto.** `babel-spanish` redefine el
   símbolo de porcentaje con una macro que inspecciona `\lastskip`, y
   dentro de `$...$` aborta con «Incompatible glue units». Escribir
   `$\pm$\,\pct{0.3}`, nunca `$\pm\pct{0.3}$`.
3. **`\cal` está tomado** por LaTeX 2.09 como fuente caligráfica.
   El macro de decisiones técnicas se llama `\CAL`.
4. **Las llaves de TikZ abomban hacia la izquierda del sentido de avance.**
   Para que una llave horizontal quede debajo de lo que agrupa hay que
   trazarla de este a oeste.

---

## C-12 · Nombres de código en la prosa
**2026-08-22 · tipo: `estilo` · aplicada**

Al corregir C-1 se pasó de un extremo al otro: se quitó la ambigüedad de
«el programa» citando la constante `AGENTS` y el archivo
`data/xm_data_loader.py`, y eso metió ruido en un capítulo que trata de
las instituciones. El corpus del autor no cita nombres de variables en
prosa; cita normas, resoluciones y fuentes.

El pasaje justifica ahora el orden fijo por lo que de verdad le importa al
lector, que es poder leer las tablas: «como cada resultado se reporta bajo
las dos coberturas de medición, mantener fija la posición de cada
institución permite comparar los dos paneles sin volver a buscar quién
ocupa cada fila».

Por el mismo motivo se retiró del pie de una figura la mención a las
constantes `T_START` y `T_END`. Las rutas de datos que quedan en los
`uente{}` sí se conservan: son atribución de procedencia, que es
exactamente el hábito del autor al cerrar sus notas con «Elaboración
propia a partir del Formato 1».

**Regla que se deriva:** en la prosa se cita la fuente del dato, no el
identificador del código. Si el detalle de implementación hace falta, va
al anexo de reproducibilidad.

---

## C-13 · CESMAG en mayúsculas también en las figuras
**2026-08-22 · tipo: `estilo` · aplicada**

Corregido el nombre en el texto (C-2), las figuras seguían rotulando
«Cesmag», que es la clave interna heredada de los CSV del canon. CESMAG es
una sigla y va en mayúsculas.

Se añadió a `estilo.py` un mapa de etiquetas de presentación,
`etiqueta_institucion()`, separado de la clave interna: los CSV y los
artefactos del canon no se tocan, solo cambia el rótulo. Regeneradas las
figuras de los capítulos 3, 4, 10 y 12, incluidas las notas al pie que
llevaban el nombre incrustado.

---

## C-14 · El conjunto de entidades no se eligió, viene dado
**2026-08-22 · tipo: `dato` · aplicada**

Decía «La elección del conjunto no es de conveniencia. Reúne dos
condiciones que un mercado entre pares necesita y que rara vez coinciden».
Eso presenta como criterio de diseño lo que fue una condición del
contexto, y es un defecto de fondo, no de redacción: enunciar los
criterios después de conocer el conjunto que los cumple es una
racionalización hacia atrás, y es de las primeras cosas que un jurado
hostil busca.

Lo que ocurre en realidad es que estas cinco son **las entidades que el
proyecto MTE instrumentó** y de las que, por tanto, existen series
numéricas de generación y consumo. La propia propuesta de tesis lo plantea
así al fijar su alcance de datos: «la validación utilizará datos empíricos
de una comunidad energética específica con sistemas fotovoltaicos
instalados. **Se asume la disponibilidad** de datos de generación,
consumo y parámetros meteorológicos». Asume el conjunto; no propone
seleccionarlo.

El pasaje reescrito invierte el argumento en tres movimientos. Primero
declara que el conjunto viene dado y que la investigación se construye
alrededor de las entidades que tienen medición, no al revés. Segundo,
explica por qué conviene decirlo de entrada. Tercero, mantiene las dos
condiciones que el conjunto sí cumple, pero **como constatación posterior
y no como criterio**.

Se añadió además un `trampabox` con la consecuencia que el párrafo
anterior escondía: cinco es un número pequeño con efectos normativos. Los
umbrales que se definen sobre la participación relativa de cada miembro
exigen al menos once participantes para que ninguno supere el diez por
ciento, de modo que con cinco ese umbral es aritméticamente inalcanzable.
No hubo margen para ampliar el conjunto ni para controlar su composición.

**Regla que se deriva:** distinguir siempre entre lo que se eligió y lo
que vino dado. Cuando algo vino dado, decirlo y declarar qué limita; la
adecuación posterior se presenta como constatación, nunca como criterio.

---

## C-15 · Dos afirmaciones que no se sostenían
**2026-08-22 · tipo: `dato` · aplicada**

**«La pregunta que se investiga».** El texto apelaba a una pregunta que
ningún capítulo había enunciado todavía: va en el capítulo 1, que sigue
pendiente. Un lector no podría saber a qué se refiere. Se reformuló sin
apelar a ella, diciendo directamente qué característica del conjunto
interesa y dónde se comprueba.

**«Las cinco entidades comparten sistema de distribución, es decir, están
eléctricamente próximas».** No es demostrable con lo que hay. Lo único
verificable es que comparten comercializador, y de ahí no se sigue que
estén en el mismo circuito ni en la misma subestación; el proyecto no
documenta la topología eléctrica, y la Universidad CESMAG está en
Catambuco, a varios kilómetros de las demás.

La afirmación además no hacía falta. La propuesta de tesis excluye
expresamente el análisis de flujos de potencia en la red de distribución,
de modo que la distancia eléctrica entre participantes no interviene en
ningún resultado del trabajo. Se sustituyó por un `detallebox` que declara
qué **no** se afirma y por qué no se necesita.

**Regla que se deriva:** antes de escribir una condición favorable,
comprobar dos cosas: que se pueda demostrar y que el modelo la use. Una
condición indemostrable que además no interviene en ningún cálculo es puro
riesgo.

---

## C-16 · Reorganización de la subsección de instituciones
**2026-08-22 · tipo: `estilo` · aplicada**

Tras la poda del autor, los párrafos supervivientes quedaron en un orden
que no seguía ningún hilo. Se reordenaron en cinco movimientos: quiénes
son las cinco; por qué son estas y no otras, con la consecuencia de que
sean cinco en un `trampabox`; dónde está cada sistema; qué las diferencia,
que es lo que hace posible el intercambio, con el `detallebox` de C-15; y
la asimetría regulatoria, que enlaza con el capítulo 5.

Al reorganizar se perdió por descuido el `trampabox` sobre el tamaño del
conjunto, que el autor no había eliminado. Quedó restaurado.

---

## C-17 · El umbral del 10 % es sobre el PDE, no sobre la participación
**2026-08-22 · tipo: `dato` · aplicada · verificada contra la norma**

El `trampabox` decía que «algunos umbrales de la regulación colombiana se
definen sobre la participación relativa de cada miembro». Tres
imprecisiones en una frase: el umbral no es sobre la participación, no es
«algunos» sino uno concreto, y no es la única condición del caso.

Verificado contra el texto de la Resolución CREG 101 072 de 2025:

- **Artículo 20, numeral 1, condición iii:** «El Porcentaje de
  Distribución de Excedentes, del que trata el artículo 19 de esta
  Resolución, sea **inferior al 10 %** para cada uno de los usuarios del
  AC.» Desigualdad estricta, y es la tercera de tres condiciones; las
  otras dos son de capacidad instalada.
- **Artículo 19:** el PDE «será informado por el representante del AC» y
  «acordado por los integrantes», con la restricción explícita
  «**Deberá cumplirse que: Σ PDE = 100 %**».

La conclusión sí se sostiene: con todos los usuarios por debajo del 10 %,
la suma es inferior a diez veces el número de usuarios, de modo que
alcanzar el 100 % exige once participantes o más. Con cinco es
inalcanzable.

Lo que cambia es la naturaleza del argumento, y a mejor. El PDE es un
reparto **acordado y declarado**, no una magnitud física, así que la
objeción inmediata sería que la comunidad puede elegirlo a conveniencia.
No puede: la restricción del artículo 19 lo impide. Decirlo con precisión
hace el argumento más difícil de rebatir que la versión vaga anterior.

**Regla que se deriva:** toda afirmación sobre lo que exige una norma se
comprueba contra el texto de la norma, no contra el código que la
implementa ni contra un documento anterior del proyecto. El código de C4
traía la interpretación correcta, pero era una interpretación.

---

## C-18 · «Comparten comercializador» era falso
**2026-08-22 · tipo: `dato` · aplicada**

El `detallebox` del capítulo 2 afirmaba que las cinco entidades comparten
comercializador y que eso permite compararlas contra una misma estructura
tarifaria. No es cierto: la mayoría contrata con ASC Ingeniería, no con el
operador de red. Se retiró la afirmación y en su lugar se dice lo que
ocurre, que las cinco se liquidan contra la tarifa de CEDENAR por
supuesto y no por contrato.

La decisión se declara donde se construyen las tarifas, en el capítulo 5,
con el desglose de qué componentes del costo unitario dependen del
comercializador y cuáles no. **El autor cerró el punto el mismo día**: se
usan las tarifas de CEDENAR por ser la única fuente disponible, pública y
auditable, de modo que no es una pendiente sino una decisión, y así se
redacta. Está escalado a `HALLAZGOS.md` como H-8 porque la tesis y el
artículo siguen presentando esa tarifa como la del comercializador de las
cinco.

**Regla que se deriva:** en un trabajo con datos de terceros, distinguir
siempre lo que consta de lo que se supone. Este es el segundo caso en dos
días, después de H-7, en que una magnitud resulta no ser lo que su rótulo
dice. Ante cualquier dato del contexto que no se haya verificado, la
formulación por defecto es «se asume», no «es».

---

## C-19 · Las dos coberturas no son lo que su nombre decía
**2026-08-22 · tipo: `dato` · aplicada · verificada contra el inventario**

El inventario de medidores del proyecto, hasta ahora sin usar, establece
qué mide cada equipo. Desmiente los dos nombres que el proyecto empleaba y
que este documento había heredado: «totalizadores de campus» para M1 y
«submedidores del circuito fotovoltaico» para M3.

Ninguno de los cinco Medidor 1 totaliza una institución. En Mariana, la
UCC y el HUDN mide el **circuito de inyección**; en Udenar y CESMAG,
**un bloque**. Ninguno de los Medidor 3 es el circuito alimentado por el
fotovoltaico: son circuitos secundarios, el totalizador de un piso y, en
el HUDN, la **UPS de ginecología**.

Cambios aplicados:

- Los rótulos de las 39 figuras pasan a «M1, circuito principal o de
  inyección» y «M3, circuito secundario», con la razón G/D en lugar de la
  palabra «cobertura», que sugería autosuficiencia institucional.
- La subsección de fuentes del capítulo 2 incorpora una tabla con el
  circuito medido por cada equipo, y dos `trampabox`: uno con la
  corrección de los nombres y otro con la cuestión abierta de la escala.
- Corregidas las menciones sueltas en la nomenclatura y en los capítulos 3
  y 4.
- El archivo se movió de la raíz a `data/inventario/`, junto a los demás
  documentos que describen el dato.

Queda registrado como H-7 en `HALLAZGOS.md` y en memoria, porque afecta
también a la tesis (§4.2) y al artículo.

**Regla que se deriva:** antes de describir qué mide un dato, buscar el
documento de instalación. Un nombre de archivo o de variable describe cómo
se llama la serie, no qué representa; y en este proyecto llevaban dos
descripciones incorrectas heredadas de documento en documento.

---

## C-20 · El mapa de ubicación separa dos proximidades
**2026-08-22 · tipo: `dato` · aplicada**

El autor aportó el mapa oficial de localización del proyecto MTE (abril de
2026, escala 1:80.000, MAGNA-SIRGAS 2018), que hasta ahora no se había
usado. Entra como Figura 2.1 en la subsección de las cinco instituciones,
que es donde respalda lo que el texto afirma.

Confirma dos afirmaciones que hasta ahora descansaban en la palabra del
documento: que la Universidad CESMAG queda fuera del área urbana, al sur
del municipio, y que las otras cuatro caen dentro. Añade una tercera que
el texto no decía: la Universidad de Nariño y la Universidad Cooperativa
están prácticamente contiguas, lo que concuerda con que ambas se ubiquen
en el sector Torobajo.

Y permite afinar el `detallebox` de C-15. Antes decía, a secas, que el
trabajo no afirma proximidad eléctrica. Ahora distingue las dos
proximidades: el mapa **acredita la geográfica**, que es considerable, y
de ahí no se sigue la eléctrica, que sería la relevante para hablar de un
mismo circuito y que el proyecto no documenta. La distinción es más útil
que la negación anterior, porque nombra lo que sí se sabe.

El archivo se movió de la raíz a `figuras/f2_01_mapa_ubicacion.pdf`,
siguiendo la convención de nombres, con su `.fuente.txt`. **No es
elaboración propia**: lo elaboraron Miguel Andrade y Jenny Chapal para el
proyecto, y así se atribuye en el pie.

---

## C-21 · Las unidades van entre paréntesis, no entre corchetes
**2026-08-22 · tipo: `estilo` · aplicada · verificada contra la guía IEEE**

El texto escribía «la potencia activa total, en kilovatios» y las figuras
rotulaban los ejes con corchetes: «Potencia [kW]», «Ganancia neta [COP]».
Verificado contra la guía editorial de IEEE, que es la que rige el formato
de este documento:

> «Write the quantity *Magnetization (A/m)*, not just *M*.»
> «Do not label axes only with units.»
> «The International System of Units (SI units) is advocated for use in
> IEEE publications.»

**Paréntesis**, por tanto, no corchetes ni barra de cociente. El corchete
es un uso extendido en la literatura técnica en inglés, alemán y polaco,
pero no es lo que pide IEEE; y la barra que recomienda la norma ISO
—escribir la magnitud dividida por su unidad— está expresamente
desaconsejada por la propia guía.

Cambios: el párrafo pasa a «la potencia activa total (kW)» y «la potencia
de corriente alterna entregada (W)», y se añade que la segunda se
convierte a kilovatios para operar con la primera, que era información que
faltaba. En las figuras se sustituyeron **35 rótulos** de corchete a
paréntesis y se regeneraron las 39.

---

## C-22 · Auditoría y rehechura de la figura de cobertura temporal
**2026-08-22 · tipo: `técnico` · aplicada**

La figura arrastraba ocho defectos: instituciones en orden alfabético en
vez del orden fijo del documento; inversores antes que medidores, porque
«inversor» precede a «medidor» en el alfabeto; nombres crudos y truncados
del tipo `Bloque Sur - Medidor 1 - electricM`; ninguna distinción visual
entre medidor e inversor; veintisiete barras sin agrupación; la etiqueta
del horizonte desplazada abajo por el eje invertido; ninguna señal de qué
fuente fija el inicio; y el gris de las auxiliares confundible con las
barras poco saturadas.

**La decisión de orden, que es lo que el autor pidió argumentar.** Se
agrupa por institución, y dentro de cada una van primero los medidores y
después los inversores. La razón es que el modelo necesita de cada sitio
un medidor **y** un inversor: sin generación no hay prosumidor y sin
demanda no hay agente, de modo que la fecha que importa es cuándo quedó
completa cada institución. Separando todos los medidores de todos los
inversores, comprobar si un sitio está operativo obligaría a saltar entre
dos bloques distantes.

Hay además una prueba concreta de que la agrupación importa: el HUDN fija
el inicio del horizonte, y dentro del HUDN **lo último en entrar es el
inversor**, no el medidor. Que lo que faltaba fuera la generación y no la
medida solo se ve si el inversor está junto a sus medidores.

**Un error propio detectado al auditar.** La primera versión rehecha
señalaba como fuente que fija el inicio al tercer inversor de Udenar, que
entra en septiembre. Es falso: ese equipo solo interviene en la
reconstrucción de la demanda y no condiciona el arranque. El cálculo pasa
a hacerse sobre las fuentes **esenciales**, es decir, el medidor de cada
cobertura y el inversor que define la generación.

Etiquetas normalizadas a «Entidad - Medidor N» y «Entidad - Inversor N».
Los inversores se numeran por orden dentro de cada institución, lo que
deja al de Udenar que entró tarde en tercer lugar.

---

## C-23 · Auditoría de las treinta y ocho figuras restantes
**2026-08-22 · tipo: `técnico` · aplicada**

Se auditaron y corrigieron las treinta y ocho figuras que quedaban, en
tres lotes paralelos con el mismo criterio que se usó en la del Gantt:
por delante de la legibilidad, comprobar que la figura no afirme algo que
sus datos no sostienen.

**Nueve defectos de fondo, que son los que importan.**

1. *Perfiles por cobertura.* El pie afirmaba que la curva de generación es
   la misma en los dos paneles y los paneles tenían escalas verticales
   independientes, de modo que la misma curva se veía cinco veces más
   grande a un lado que al otro. La figura desmentía su propio pie.
2. *Inicio del horizonte.* Señalaba como causante al inversor auxiliar de
   Udenar, que entra en septiembre. Es el mismo defecto que ya se corrigió
   en la del Gantt, en otra figura. El inicio lo fija el inversor del HUDN.
3. *Banda de precios.* Sombreaba de un solo color desde la mediana de
   bolsa hasta la tarifa comercial y lo rotulaba como el tramo donde vive
   el precio de equilibrio. Eso es la unión de las bandas y no la banda:
   en los 159 COP/kWh que separan la tarifa oficial de la comercial, los
   compradores oficiales ya perderían.
4. *Las tres versiones del esquema colectivo.* Barras con el eje
   arrancando muy por encima de cero hacían leer como cinco a uno lo que
   está en trece por ciento.
5. *Cumplimiento del umbral.* Dibujaba la cuota de cobertura contra la
   línea del diez por ciento y concluía que las cinco instituciones
   cumplen, cuando la columna de veredicto del propio canon dice lo
   contrario para las cinco y en las dos coberturas. Ver C-24.
6. *Escalamiento.* Multiplicaba la cuota por dos y por tres contra esa
   misma línea, que es precisamente la prueba que se retiró al pasar al
   Caso 2: el reparto de excedentes es un cociente de capacidades y
   escalar a todos por igual lo deja idéntico. Rehecha sobre la cota de
   capacidad por usuario, que sí muerde al crecer.
7. *Mercado horario.* Los dos paneles estaban desfasados una hora entre
   sí, porque la columna de hora del canon empieza en uno y el otro panel
   se indexa por posición.
8. *Serie mensual.* El desplome de diciembre se leía como estacionalidad
   siendo aritmética: el horizonte cierra el día 16 y ese mes aporta 360
   horas frente a las 744 de uno completo.
9. *Precio de escasez.* Un rótulo decía que dos horas rozan el techo. Ver
   [[H-9]] en el registro de hallazgos: lo multiplican por 2,48.

**Dos categorías con el mismo rótulo**, que es lo que la ronda 4 del
artículo ya había señalado como motivo de rechazo. El eje de la figura de
equidad imprimía dos veces «C4» porque el acortador corta por el
separador, y el lector no podía saber cuál rige. También se fusionaron las
columnas de los dos escenarios que son idénticos por construcción, que se
leían como dos comprobaciones independientes.

**Un fallo mudo de la infraestructura**, que reordenó instituciones en
tres figuras sin dar error: cuando los dos paneles comparten el eje
vertical, invertirlo dentro del bucle lo invierte dos veces y la segunda
deshace la primera.

**Lo demás fue legibilidad**, y era abundante: leyendas encima justo de
los objetos que la figura quiere mostrar, rótulos de eje truncados por el
borde derecho, cifras ilegibles sobre celdas oscuras, ejes que llegaban
muy por delante del dato y meses en formato numérico donde el argumento
necesitaba reconocer el receso de julio.

Ninguna cifra del canon se alteró.

---

## C-24 · El umbral de reparto no se había propagado a las figuras
**2026-08-22 · tipo: `contenido` · aplicada**

C-17 corrigió en el texto que el diez por ciento del artículo 20 acota el
porcentaje de distribución de excedentes, no la participación en energía,
y que como el artículo 19 obliga a que ese reparto sume cien, con cinco
usuarios el Caso 1 es inalcanzable. **La corrección se quedó en el texto.**
Dos figuras seguían dibujando la cuota de cobertura contra la línea del
diez por ciento.

Comprobado contra el canon: el reparto proporcional a la capacidad da
21,7, 20,6, 25,3, 21,2 y 11,1 por ciento, que suma cien y deja a las cinco
por encima del umbral. Eso reproduce exactamente la columna de veredicto
del canon, que vale falso para las cinco en las dos coberturas.

**La lección, que no es sobre esta figura.** Una corrección anotada en el
texto no está aplicada hasta que se busca en las figuras, en los scripts y
en los artefactos derivados. Conviene que toda entrada futura de este
registro diga a qué capas hay que llevarla.

---

## C-25 · Se decía qué unidad se usa, sin sustentar por qué
**2026-08-23 · tipo: `contenido` · aplicada**

La subsección de las fuentes declaraba que el modelo toma la potencia
activa total (kW) del medidor y la potencia de corriente alterna (W) del
inversor, pero no sustentaba ninguna de las dos elecciones. El medidor
ofrece además la potencia reactiva y la aparente, y el inversor ofrece
también la lectura del lado de corriente continua, de modo que las tres
decisiones eran afirmaciones sin argumento.

Se añaden tres razones y una salvedad.

**Por qué la activa.** El mercado intercambia energía y la energía es la
integral de la potencia en el tiempo, así que la magnitud buscada es la
que integra a los kilovatios hora que se facturan. De las tres potencias
solo la activa lo cumple: por la relación entre ellas, la reactiva oscila
entre la fuente y la carga y su transferencia a lo largo de un ciclo se
anula.

**Por qué el lado alterno del inversor.** Lo que la institución puede
consumir o vender es lo que sale ya convertido, después de las pérdidas
de conversión. La lectura del lado continuo describe lo que entrega el
arreglo y sobrestimaría la generación disponible.

**Por qué kilovatios.** Las dos unidades son de fábrica y la conversión
entre ellas es exacta, un factor de mil, de modo que ninguna se pierde
nada. Lo que fija la unidad de trabajo no es el equipo sino el precio: la
tarifa colombiana se denomina en pesos por kilovatio hora y todo resultado
del trabajo acaba siendo una cifra de dinero.

**La salvedad, medida.** Que la reactiva no entregue trabajo no significa
que no se pague. Ver [[H-11]]: el exceso que la norma cobra aparece en el
15,0 % de las horas de una cobertura y en el 65,7 % de las de la otra.
Queda declarado en una caja de trampa.

---

## C-26 · Catálogo completo de las variables de cada equipo
**2026-08-23 · tipo: `contenido` · aplicada**

A raíz de C-25 se añaden dos tablas con el catálogo entero de lo que
entrega cada clase de equipo, agrupado por familia y con la unidad de cada
magnitud, para que la elección de la potencia activa pueda contrastarse
contra las alternativas en lugar de creerse. Las variables que solo se
repiten por fase ocupan una línea, con el número de columnas que llenan en
el archivo.

Del censo salieron cuatro correcciones de hecho:

1. **Son cinco estaciones meteorológicas, no cuatro.** Ver [[H-14]].
2. **El recuento de variables incluía la marca de tiempo.** El fichero trae
   55 y 19 columnas, pero una de cada par es la fecha, que no es una
   magnitud medida. La prosa pasa a 54 y 18, y el total de 74 a 72.
3. **Ocho de las cincuenta y cuatro del medidor no varían nunca.** Ver
   [[H-13]]. Se declaran en la propia tabla.
4. **La lectura del lado continuo del inversor no cubre el arreglo
   completo.** Ver [[H-12]]. Se incorpora al argumento como evidencia
   empírica, además de la razón de principio.

La tabla del medidor pasó a componerse como tabla larga porque no cabe en
una página y se imprimía encima del pie.

---

## C-27 · Cifras o palabras: se fija la norma y se barre el documento
**2026-08-23 · tipo: `estilo` · aplicada · norma permanente**

Lo planteó él al notar que «se obtienen veintisiete dispositivos: veinte
medidores y siete inversores» se lee peor que «27 dispositivos: 20
medidores y 7 inversores», y pidió averiguar cuál es el criterio formal en
lugar de decidirlo por gusto.

**La autoridad es la RAE, no el manual de IEEE.** El formato del documento
es IEEE, pero la prosa es española y la ortografía de las expresiones
numéricas la fija la RAE. IEEE gobierna la bibliografía y la maquetación.

**Lo que dice la RAE.** Distingue por tipo de texto. En obras literarias y
textos no técnicos prefiere las palabras. En textos científicos y técnicos
prefiere las cifras por concisión y claridad, y las da por obligadas cuando
el manejo de números es constante y constituye parte fundamental de lo
escrito, que es el caso de inventarios, cómputos estadísticos, tablas y
gráficos. Este documento es exactamente eso. Añade dos normas más: las
cifras son obligadas cuando sigue un símbolo de unidad, y no conviene
mezclar cifras y palabras en un mismo enunciado.

**Las cuatro reglas que quedan fijadas.**

1. De cero a nueve, palabras, siempre que no siga un símbolo de unidad.
2. De diez en adelante, cifras.
3. Cifras siempre que siga un símbolo de unidad, sea cual sea el número.
4. No mezclar dentro de un enunciado o serie. Si un miembro pasa a cifras,
   pasan todos.

**Dos excepciones.** Los títulos y subtítulos van en palabras, porque allí
el número no es dato sino parte del enunciado, de modo que «Veintisiete
fuentes, dos magnitudes» se queda como está. Y nunca se abre una oración
con cifra.

**Lo aplicado.** 44 sustituciones automáticas más 5 arreglos de serie que
la máquina no podía juzgar. La regla 4 corrigió tres mezclas que ya
estaban: «once participantes» convivía con «10 %» y «100 %» en la misma
oración; «ocho participan y doce quedan»; y «Cinco de las 54», que además
abría oración con la mezcla al revés. Esa última se reescribió entera para
no abrir con cifra.

Queda en memoria como norma permanente para la tesis, el artículo y sus
derivados.

---

## C-28 · La columna de recuento de las tablas de variables sobraba
**2026-08-23 · tipo: `estilo` · aplicada**

Las dos tablas del catálogo llevaban una tercera columna con el número de
columnas que cada magnitud ocupa en el archivo. Él la señaló como
sobrante, y lo es: la propia entrada ya lo declara. «Corriente de fase (A,
B, C)» dice que son tres y «palabras baja y alta» que son dos, de modo que
la columna repetía lo que el lector acababa de leer.

Retirada de las dos tablas, junto con la fila de total, que sin el
recuento no tiene de qué sumar. El total sigue estando en el pie de cada
tabla y en la prosa. La columna de la variable se ensancha de 8,1 a 9,6
centímetros con el espacio liberado, con lo que dejan de partirse en dos
líneas varias entradas largas.

**Dos defectos que solo aparecieron al renderizar la página**, y que
conviene recordar como método: revisar el archivo fuente no basta.

1. Un encabezado de familia podía quedar solo al pie de una página con sus
   filas en la siguiente. Se protege con la forma del terminador de fila
   que impide la ruptura justo después.
2. Al partir en dos la oración de las tres potencias, en C-25, quedó una
   coma donde debía ir un punto. Llevaba dos compilaciones sin detectarse
   porque el archivo fuente se lee sin reparar en ello.

---

## C-29 · El aviso sobre el reactivo pasa a subsección con figuras
**2026-08-23 · tipo: `contenido` · aplicada**

Él señaló que la caja de trampa sobre la energía reactiva era demasiado
importante para quedarse en un aviso, y pidió sostenerla con figuras que
mostraran el peso sobre cada institución a lo largo del tiempo.

Pasa a subsección propia con dos figuras nuevas y con el cargo cifrado.

**Lo que las figuras muestran y el aviso no podía.**

1. *El exceso no está repartido, y no lo aporta la misma institución en
   cada frontera.* Lo concentra la Universidad Mariana en el circuito
   principal y la Universidad CESMAG en el secundario. Un promedio de
   comunidad ocultaba las dos cosas.
2. *Frecuencia y magnitud no son la misma pregunta.* El Hospital no supera
   el umbral ni una hora en el circuito principal pese a mantener una
   razón alta, mientras que Udenar lo supera pocas veces y acumula más
   energía en exceso, porque cuando lo supera lo hace por mucho.
3. *No es episódico.* La razón se mantiene sobre el umbral a cualquier
   hora y en cualquier mes en las instalaciones que incumplen, que es lo
   que distingue un problema estructural de una punta.

**El cargo, cifrado.** Ver [[H-11]]. Se cerró la objeción que lo dejaba
abierto, que era un error de planteamiento: la norma no cobra el exceso a
una tarifa propia sino como energía activa dentro de los cargos por uso de
redes, y esa tarifa sí estaba recuperada.

**Una cautela deliberada.** No se afirma que incluir el cargo favorezca al
mercado entre pares. Invita a pensarlo, porque ese mecanismo está exento
de cargos de red, pero la exención recae sobre la energía transada entre
pares y no sobre el consumo remanente. Queda declarado como abierto en vez
de resuelto de oído.

Infraestructura nueva: `scripts/cache_reactiva.py`, que deja la serie
horaria de potencia activa y reactiva de los diez medidores del modelo.

---

## C-30 · El párrafo del criterio de medida entraba sin antecedente, y era falso
**2026-08-23 · tipo: `contenido` · aplicada**

Él señaló que el párrafo sobre cómo se mide el exceso de reactivo no decía
gran cosa. Tenía dos defectos, y el segundo es mío y de fondo.

**Entraba sin antecedente.** Empezaba por «la comparación se hace sobre la
energía de cada hora», cuando el lector todavía no sabía que hubiera una
medición en marcha. El sujeto no se refería a nada dicho antes.

**Y afirmaba algo que no se sostiene.** Decía que contar las muestras de
dos minutos «da un número más alto». Comprobado con el mismo filtro y la
misma población, por muestras sale el 35,8 % y por horas el 36,4 %, de
modo que ni es más alto ni difiere apreciablemente. La cifra del 38,96 %
que yo tenía en la cabeza venía de una agregación defectuosa, un promedio
de porcentajes por medidor ponderado por número de muestras, que no es lo
mismo que el porcentaje del conjunto.

Reescrito para abrir con el resultado, el \pct{15,0} y el \pct{65,7} de
horas en exceso de cada frontera, y para declarar el criterio por lo que
es: fidelidad a cómo la norma define la comparación, no una elección que
mueva la cifra. Se dice explícitamente que medir por instantes deja el
resultado a menos de un punto porcentual, lo que además desactiva la
objeción antes de que se formule.

**La lección.** Una afirmación comparativa escrita de memoria, sin volver
a medir, es exactamente el tipo de cosa que este documento existe para
evitar.

---

## C-31 · Los números a una tabla y la serie completa a una figura
**2026-08-23 · tipo: `contenido` · aplicada**

Él propuso sustituir la figura de barras por una tabla con las cifras, y
dibujar aparte la serie temporal entera de cada entidad con la línea del
umbral, para poder ver todos los sistemas. Es mejor reparto: la barra
codificaba dos números por institución que una tabla da con más precisión
y sin escala que interpretar, y ninguna de las dos podía mostrar el
recorrido.

La tabla añade la razón mediana y el cargo en pesos, que en la figura no
cabían. La serie es una retícula de diez paneles, uno por institución y
frontera, con la mediana diaria sobre la mancha de las horas sueltas y el
área sombreada donde la norma cobra.

**Lo que la serie muestra y el resumen no podía.** El incumplimiento tiene
formas distintas. Mariana se instala sobre el umbral desde el primer día;
la UCC lo cruza en cada ciclo diario, de modo que su 44,1 % no es un
periodo malo sino la mitad de todos los días; el Hospital dibuja una banda
estrecha y constante justo encima, que es la forma de una carga
permanente.

**Tres afirmaciones mías que no resistieron la comprobación**, escritas
mirando la figura en vez de midiendo:

1. «Ninguna de las diez series presenta un tramo sin dato.» Falso. Las
   diez tienen entre 103 y 126 horas ausentes de las 6.168, con rachas de
   hasta 49 horas.
2. «La razón de CESMAG se mantiene cerca de 1,0 hasta agosto y sube
   entonces a 1,3.» El escalón existe, pero va de mayo a junio y de 0,78 a
   1,0. Leí mal la figura.
3. La atribución del pico de mediodía de Mariana a la generación propia se
   enunciaba como hecho. Medido: la activa cae de 9,1 a 6,2 kilovatios
   entre las nueve y las trece mientras la reactiva baja solo de 5,8 a 5,3
   kilovar. Ahora se dan las cifras y la causa se enuncia como lo que cabe
   esperar, no como comprobado.

**El hallazgo que sobrevive a la corrección.** La instalación de la
Universidad CESMAG en el circuito secundario empeora a mitad de horizonte
y se queda así: las horas en exceso pasan del 68 % de mayo al 98 % de
junio. No se puede determinar la causa desde aquí.

---

## C-32 · Por qué dos instituciones tienen tan pocas horas con consumo
**2026-08-23 · tipo: `contenido` · aplicada**

Él preguntó por qué Udenar y Mariana tienen tan pocas horas con consumo en
la tabla del reactivo. La columna invitaba a la pregunta y el texto no la
respondía. Son tres causas distintas y solo una es un defecto del dato.

1. **Udenar, circuito principal: no es poco consumo, es exportación.** El
   25,2 % de sus horas registra potencia negativa, hasta −33,6 kW, porque
   ese medidor descuenta la generación propia de la lectura. Es el mismo
   fenómeno que el capítulo del preprocesamiento reconstruye.
2. **Udenar, circuito secundario: es un ramal pequeño.** Ni una hora
   negativa, pero el 61 % se queda entre cero y 0,5 kW, con mediana de
   0,38 kW.
3. **Mariana, circuito secundario: el medidor no sirve.** El 90,5 % de las
   horas por debajo de 0,5 kW, mediana 0,02 kW y máximo 2,52 kW. Coincide
   con que el inventario lo declare inexistente como segunda frontera.

**Lo que la pregunta destapó.** Las dos primeras columnas de la tabla y
las dos últimas no cuentan la misma población: la fracción de horas en
exceso se calcula sobre las horas con consumo apreciable, mientras que la
energía y el cargo recogen todas. Y así lo exige la norma, que cobra el
reactivo cuando supera la mitad de la activa **y también cuando se
registra sin consumo activo alguno**. En el circuito principal eso no es
menor: 3.495 de los 8.851 kvarh, el 40 % del exceso facturable, nacen en
horas que el recuento porcentual deja fuera, y son en su mayoría las de
exportación de Udenar. Ver [[H-15]].

Se comprobó que las cifras de coste ya publicadas no cambian: el cálculo
del exceso recorría todas las horas desde el principio.

---

## C-33 · Se declara que las series del reactivo son las crudas
**2026-08-23 · tipo: `contenido` · aplicada**

Él preguntó si estas series son las finales o si el preprocesamiento las
cambia después. La subsección no lo decía y hacía falta, porque el
capítulo siguiente somete el dato a diez transformaciones.

**La respuesta tiene dos mitades.**

1. **No existe una versión procesada de la reactiva.** El pipeline lee una
   sola columna de cada medidor, la potencia activa total, de modo que la
   reactiva nunca entra en él. La única serie disponible es la que el
   equipo registró.
2. **Para la pregunta regulatoria, la lectura cruda es la correcta.** La
   norma compara el reactivo contra la energía activa entregada al
   usuario, y lo entregado es lo que cruza el medidor, no lo que el
   edificio consume por dentro. La reconstrucción recupera esto último,
   que es lo que el mercado necesita, pero no es lo que factura el
   comercializador.

**Lo que la pregunta permitió cifrar.** Comparando contra la demanda
reconstruida en vez de contra la lectura del medidor, las horas en exceso
de Udenar bajan del 6,3 % al 3,0 %, las de Mariana del 62,7 % al 49,1 % y
las de la UCC del 4,9 % al 0,2 %, todas en el circuito principal. El
Hospital y la Universidad CESMAG no se mueven, porque sus medidores no
descuentan generación.

Esa distancia es el precio de generar, medido: las tres instituciones cuyo
medidor resta la generación propia incumplen entre el doble y veinticinco
veces más de lo que incumplirían por su consumo real. Es el segundo orden
que [[H-15]] había dejado enunciado sin cuantificar.

**Cautela.** La serie del segundo medidor de Mariana queda fuera de esa
comparación: el modelo la aproxima escalando el primero, de modo que
contrastar su reactivo contra esa demanda no significaría nada.

---

## C-34 · Por qué el trabajo entero se hace sobre energía activa
**2026-08-23 · tipo: `contenido` · aplicada · decisión metodológica**

Él preguntó si, a la vista de lo medido, el trabajo debería usar activa y
reactiva o solo activa, y por qué razón. Es la pregunta que un jurado hace
después de leer esta subsección, y no estaba respondida.

**La decisión es solo activa, con cuatro razones.**

1. **Solo la activa transfiere energía.** El mercado intercambia
   kilovatios hora y el reactivo no mueve energía neta a lo largo de un
   ciclo, de modo que no hay nada que vender.
2. **Los regímenes que se comparan están escritos en energía activa.** La
   autogeneración, los excedentes y su reparto se miden en kilovatios hora
   en las tres resoluciones implementadas. Comparar sobre otra magnitud
   sería comparar objetos distintos, que es el defecto que la ronda 4 del
   artículo señaló como motivo de rechazo.
3. **Repartir reactivo exigiría representar la red.** La compensación es
   local; afirmar que fluye entre instituciones necesita impedancias y
   flujos de potencia. El modelo no representa la red y ya declara que
   tampoco afirma proximidad eléctrica.
4. **El modelo base está formulado sobre potencia activa.** Incorporar el
   reactivo no sería añadir una columna sino reescribir el juego y perder
   la fidelidad al modelo que se valida.

**Y se cierra con cifra el único camino por el que el reactivo podía
alterar la comparación.** El mercado reduce la energía activa que cada
comprador toma de la red, con lo que baja el umbral y crece la parte
facturable del reactivo. Calculado por usuario, que es como aplica la
norma, el mercado eleva el cargo en 97.471 pesos en el circuito principal
y en 59.782 en el secundario: el 6,8 % del margen frente al colectivo
mensual en el primero y el 1,3 % de la brecha en el segundo. **Estrecha la
ventaja y no la invierte.**

**Un error de cálculo detectado y corregido en el camino.** El primer
intento cruzó la serie de reactivo con los flujos del mercado usando
niveles de índice con nombres distintos, `institucion` y `comprador`.
Pandas alineó solo por la hora y devolvió un producto cruzado que
multiplicaba el cargo base por 2,17, de 1.877.304 a 4.081.213 pesos. Se
detectó porque la cifra sin mercado dejó de reconciliar con la ya
publicada. El generador lleva ahora una comprobación del número de filas
que impide repetirlo.

---

## C-35 · Una duplicación silenciosa de casi cuatrocientas líneas
**2026-08-23 · tipo: `técnico` · reparada**

Al convertir el aviso del reactivo en subsección propia, el reemplazo
localizó el cierre del aviso buscando desde el principio del fichero y
encontró el de **otro aviso anterior**, el de las cinco instituciones. El
punto de corte quedó por delante del de inicio, de modo que toda la región
intermedia se escribió dos veces.

Quedaron duplicadas dos subsecciones enteras y el cierre de una tercera,
casi cuatrocientas líneas, con seis etiquetas repetidas.

**Por qué no saltó antes.** El documento siguió compilando sin error, sin
desbordes y con un número de páginas verosímil. La única señal era un aviso
de etiquetas repetidas al final del registro de compilación, que no se
estaba mirando. Se descubrió al leer la subsección para revisarla y ver el
mismo párrafo dos veces.

**Lo que casi se pierde.** La copia vieja contenía material que la nueva no
tenía, la caja de las setenta y dos magnitudes y la subsección de qué mide
cada equipo con la tabla del inventario de medidores, porque seguían al
aviso original y se quedaron con él. Borrar la copia entera habría
eliminado la tabla que sostiene [[H-7]].

**Cómo se reparó.** Se conservó la versión nueva, se rescató de la vieja el
bloque que solo estaba allí y se devolvió a su sitio dentro de las
veintisiete fuentes, y se eliminó el resto. La reparación comprueba antes y
después el número de apariciones de cada rótulo, y falla si alguno queda
repetido.

**Dos normas que se derivan.**

1. Al cortar un tramo por sus extremos, el extremo final se busca **a
   partir** del inicial, nunca desde el principio del fichero.
2. La compuerta de compilación pasa a mirar también el aviso de etiquetas
   repetidas, no solo los errores y los desbordes. Es la señal que hubo
   durante tres compilaciones sin que nadie la leyera.

---

## C-36 · El material del reactivo pasa a un anexo
**2026-08-23 · tipo: `estructura` · aplicada**

Él preguntó si de verdad valía la pena incluir todo el detalle de la
energía reactiva. Medido, ocupaba el **39 %** de las palabras del capítulo
del dato crudo, 3 de sus 10 figuras y tablas, y cuatro cajas, para
concluir que la comparación entre mecanismos no cambia.

**El material se conserva; lo que estaba mal era el sitio.** Cuatro
razones:

1. Seis páginas que terminan en «no compromete la comparación» son un
   retorno pobre para la atención que piden.
2. El capítulo 2 responde qué se midió, con qué y durante cuánto. Esto es
   un hallazgo sobre el lado de costos del marco regulatorio, no sobre el
   inventario del dato.
3. Desequilibra la columna del documento, que es dato, proceso y
   resultado. Una digresión de ese tamaño en el capítulo de cimientos la
   debilita.
4. Abre una puerta que luego se cierra a mano: enseñar 1,88 millones y
   «generar empeora tu posición» invita a pedir que se modele.

**Lo aplicado.** En el capítulo 2 queda un párrafo de 162 palabras con las
cifras que un lector necesita ahí mismo, justo donde se dice que de 54
magnitudes el modelo usa una. La medición completa pasa al Anexo F, «Lo
que el modelo no representa», dividido en cinco apartados: el cargo, la
forma del incumplimiento, cuánto cuesta, por qué solo se usa activa y la
trampa de agregación.

El reactivo baja del 39 % al 5 % del capítulo. Se eligió un anexo y no el
capítulo de precios porque ese trata de los precios que el modelo **usa**,
y esto es un cargo que **no usa**. Además es donde un revisor va a
buscarlo.

**Nota sobre el proceso.** El material creció pregunta a pregunta, y cada
una abrió algo real, pero nadie comprobó la proporción hasta que él la
preguntó. Conviene medir el peso de una sección contra su capítulo antes
de darla por cerrada, no después.

---

## C-37 · Revisión de forma del capítulo 2
**2026-08-23 · tipo: `estilo` · aplicada**

Pasada de ortografía, gramática y estilo sobre el capítulo ya depurado por
el autor, sin añadir ni quitar contenido. Trece correcciones.

**Ortografía**, todas en el mismo pasaje del alcance: «abarco» por
«abarcó», «ningun» por «ningún» y «en escenario» por «el escenario».

**Régimen preposicional y léxico.** «Supera al margen» pasa a «supera el
margen», porque el complemento es inanimado y no lleva preposición; la
misma corrección se aplicó en el anexo. «Matemáticamente no alcanzables»
pasa a «inalcanzables», que es la forma que ya usaba la caja del umbral.
«La base empírica queda delimitada en 27 fuentes» pasa a «la forman 27
fuentes».

**Norma de cifras (C-27), tres mezclas dentro de un mismo enunciado.**
«Dos de las 72 magnitudes» pasa a «2 de las 72». «El modelo lee uno por
institución» convivía con 20, 8 y 12 en la misma oración, y pasa a «lee un
equipo por institución», que resuelve la mezcla con un artículo. Y la
oración del inventario, que empezaba en 27, 20 y 7 y terminaba en «tres» y
«uno», se parte en dos para que sean enunciados distintos.

**Repeticiones y giros torpes.** «Cualquier conclusión más adelante» pasa
a «posterior». «En consecuencia» seguido de «por lo tanto» en oraciones
consecutivas pierde el segundo. «Se han nombrado como los nombra la
plataforma» pasa a «se han citado con el nombre que les da la plataforma».

**Coherencia.** «El medidor 4 de Udenar» pasa a «Medidor 4», que es como
se nombra el resto de equipos, y la cabecera del fichero pierde su raya
larga.

**Comprobado y no corregido.** El documento mezcla dos formas de escribir
el separador decimal dentro de las órdenes de número, punto en los
capítulos antiguos y coma en los nuevos. Se verificó con un documento de
prueba que ambas producen la misma salida, de modo que no es un defecto y
unificarlo no cambiaría ni una página.

---

## C-38 · El caché del reactivo incluía un día que el modelo no ve
**2026-08-23 · tipo: `dato` · aplicada**

El análisis del anexo marcó que allí se hablaba de «las 6.168 horas del
horizonte» mientras el resto del documento dice 6.144. Tenía razón, y el
error era mío.

El pipeline recorta el horizonte con **límite derecho exclusivo**, de modo
que llega hasta el 15 de diciembre a las 23:00. El caché del reactivo
recortaba hasta el 16 inclusive, veinticuatro horas que el modelo no ve.

**Lo que se mueve y lo que no.** Las fracciones aguantan: 15,0 % y 65,7 %
de horas en exceso, 67 % y 62 % de cuota de la institución dominante,
0,7 % de horas por encima del tope gráfico. Las magnitudes absolutas
bajan: 8.851 a 8.792 kvarh y 5.730 a 5.705, con lo que el cargo pasa de
1.877.304 a 1.865.016 pesos y de 1.215.258 a 1.210.145. El efecto del
mercado sobre el cargo no cambia en absoluto, 97.471 y 59.782 pesos,
porque las horas con transacción caen todas dentro del horizonte.

**La afirmación que sostenía el asunto sobrevive**: el cargo del circuito
principal sigue superando el margen entre los dos mecanismos mejor
situados, ahora por un factor de 1,31 en vez de 1,32.

Actualizadas la tabla del anexo, sus cuatro párrafos con cifra, el párrafo
del capítulo 2 y las dos figuras, que se regeneraron.

---

## C-39 · La prosa del capítulo 5 se quedó con trece meses de tarifa
**2026-08-23 · tipo: `dato` · aplicada**

Segunda cascada de la misma clase, y también propia. La auditoría de
figuras (C-23) recortó la serie tarifaria al horizonte, de trece meses a
nueve, porque promediar hasta abril de 2026 metía cuatro meses que el
estudio no cubre. La figura pasó a nueve barras y **la prosa se quedó con
los promedios de trece**.

Lo detectó el análisis del capítulo 5 al ver que el texto hablaba de «13
meses» y que la nota daba un mínimo «en enero de 2026», fuera del
horizonte.

Recalculado sobre los nueve meses: el costo unitario medio oficial pasa de
792,06 a 795,68 pesos por kilovatio hora, el recorrido de 50,18 a 43,46,
el mínimo se mueve de enero de 2026 a diciembre de 2025, y el reparto por
componentes se corrige entero, con la generación en 38,3 % y no 38,6 %.

**Dos comprobaciones que aguantan.** La razón entre la tarifa comercial y
la oficial vale 1,2000 en los nueve meses, sin una sola excepción, igual
que valía en los trece. Y la lectura de fondo se mantiene, aunque su cifra
cambie: la generación explica el 38,3 % de lo que se paga, de modo que el
resto es más del 60 %. Decía «casi dos tercios», que para un 61,7 % era
generoso.

---

## C-40 · P-4 cerrado: la contraposición campus contra ramal
**2026-08-23 · tipo: `contenido` · aplicada · cierra un pendiente**

El capítulo 4 seguía explicando las dos fronteras de medición como
«totalizador de campus» frente a «submedidor que aísla el circuito
fotovoltaico». H-7 desmintió las dos cosas contra el inventario de
instalación: en tres de las cinco instituciones el Medidor 1 es el
circuito de inyección y no un totalizador, y el Medidor 3 del Hospital es
la alimentación ininterrumpida de ginecología, no un ramal fotovoltaico.
Los rótulos de las figuras se habían corregido en C-19; el argumento del
capítulo, no.

Corregidos cinco pasajes de prosa y el diagrama, que era el más visible
porque rotulaba literalmente «Campus completo» y «Circuito fotovoltaico»,
y afirmaba que M1 «mide todo el campus». Se redibuja con los nombres
correctos y con la inyección sobre el circuito principal, que es donde
ocurre en tres de las cinco, con la salvedad declarada en el pie: el
esquema es una idealización y la posición del punto de inyección varía
entre instituciones.

**La reescritura más de fondo** es la de las dos preguntas. Decían que M1
es «la pregunta del rector que firma la factura» y M3 «la del ingeniero
que dimensionó la instalación». Ninguna de las dos identificaciones se
sostiene: M1 no es la institución entera ni M3 el circuito electrificado
con sol. Pasan a ser dos regímenes de recurso relativo, una carga grande
frente a poca generación y una carga del orden de la propia generación,
con la relación de cada circuito con el consumo institucional declarada
como pendiente.

---

## C-41 · Revisión de forma de los capítulos 3, 4 y 5 y del anexo
**2026-08-23 · tipo: `estilo` · aplicada**

Análisis con un modelo distinto del que aplica, contra las normas ya
registradas y no contra criterio nuevo. Ochenta y tres correcciones.

**Tres contradicciones físicas en el capítulo 3**, que son lo más grave.
La oración de referencia dice bien que el inversor «inyecta aguas abajo
del punto de medición», pero las tres formulaciones hechas desde el
medidor están invertidas: decían que el medidor está aguas abajo de la
inyección cuando netea, y aguas arriba cuando no. Un medidor aguas abajo
de la inyección no la descuenta. Afectaba al pie de una figura, a la
explicación de Udenar y a la del Hospital y CESMAG.

**Cuatro pasajes que reintroducían lo que H-7 desmintió**, hablando de «la
demanda de la institución» y de «la carga del campus» donde corresponde el
circuito medido.

**Una referencia interna rota**: el texto remitía al «punto (iii)» de una
lista que se imprime en números arábigos.

**Dos menciones al autor en tercera persona**, «el investigador» y «el
autor», contra la regla de impersonal puro.

**Un artefacto de código en la prosa**, el nombre de una función, que sin
él dejaba una frase que no decía nada.

El resto son la norma de cifras (nueve mezclas dentro de un mismo
enunciado), la sigla CESMAG en siete sitios, «kilovatio hora» sin guion,
concordancias, régimen preposicional y repeticiones.

**Lo único que añade texto** es el cierre bisagra del capítulo 4, que
terminaba en seco sin recoger la cifra clave ni anunciar el siguiente,
contra el rasgo medido del autor.

**No se tocó** ninguna nota al pie de figura ni ninguna línea de fuente,
por decisión suya.

---

## C-42 · El nivel de tensión: se mantiene el 2 y se deja de minimizar la discrepancia
**2026-08-23 · tipo: `contenido` · aplicada · cierra P-8**

El capítulo declaraba el nivel de tensión 2 y, en la misma oración, decía
que «la revisión regulatoria del proyecto» lo sitúa en el nivel 1,
presentando la discrepancia como «únicamente la verificación».

**Lo comprobado.** El nivel 2 es el que usa el trabajo, confirmado por el
autor y por el módulo de tarifas, que lo declara como supuesto para las
cinco instituciones y remite a la factura para verificarlo. El nivel 1 no
es una hipótesis suelta: lo cita el asesor regulatorio del proyecto en su
informe, y la auditoría de agosto lo registra como declarado y sin
resolver.

**Lo que la frase escondía.** Entre los dos niveles median 18,7 puntos
porcentuales del costo unitario, 944,7 frente a 795,7 pesos por kilovatio
hora, y la diferencia está entera en el cargo de distribución, que pasa de
266,5 a 156,7. Llamar «únicamente una verificación» a una discrepancia que
mueve casi una quinta parte de todas las cifras económicas la
empequeñecía.

Reescrito en tres párrafos: el nivel que se usa y qué lo respalda; la
discrepancia con su magnitud y su origen; y por qué no altera el
ordenamiento.

**Una promesa que se acotó.** El párrafo final afirmaba que el capítulo de
robustez «muestra que el ordenamiento sobrevive a variaciones de ese techo
muy superiores a la diferencia entre los dos niveles». Ese capítulo aún no
está escrito, de modo que la afirmación no se puede comprobar hoy. Lo que
sí consta es el rango del barrido del techo en el análisis de sensibilidad
global, más ancho que la distancia entre los dos niveles, y eso es lo que
la frase dice ahora.

---

## C-43 · La apertura del capítulo 3 nombraba dos cosas que el lector no tenía
**2026-08-23 · tipo: `contenido` · aplicada**

Él señaló que el párrafo de apertura del capítulo 3 dejaba cosas al aire
respecto del capítulo anterior, y preguntó qué es «la plataforma de
monitoreo» y qué es «la matriz que consume el modelo».

Comprobado: **ninguno de los dos términos está establecido**. «Plataforma»
aparece una sola vez en el capítulo 2, de pasada y sin definirse, al decir
que los equipos se citan con el nombre que ella les da. «Matriz» aparece
otra vez, también de pasada, en una nota sobre un inversor. El párrafo
nombraba los dos extremos del recorrido con dos términos opacos, de modo
que no decía de dónde a dónde se va, que es justo lo que un capítulo de
proceso debe decir en su primera línea.

Reescrito con lo que hay de verdad en cada extremo, y que el capítulo 2 sí
dejó establecido: de un lado, los archivos que escribe cada uno de los 27
equipos, con una lectura cada dos minutos y huecos allí donde la
adquisición falló; del otro, cuánto consumió y cuánto generó cada
institución en cada una de las 6.144 horas del horizonte.

**La palabra «matriz» se deja para donde corresponde**, que es la
subsección del resultado del pipeline, donde el objeto se define. Y
«adquisición» enlaza con la figura de cobertura del capítulo 2, que usa
ese mismo término.

---

## C-44 · Revisión de claridad del capítulo 3 completo
**2026-08-23 · tipo: `contenido` · aplicada**

Aplicado a todo el capítulo el criterio con que él corrigió la apertura en
C-43: buscar lo que llega sin que el lector lo tenga. Trece correcciones.

**Cuatro términos que el lector no tenía.**

1. «La plataforma de origen» seguía apareciendo en la subsección de
   localización, con el mismo defecto que se corrigió en la apertura y sin
   definirse en ninguna parte. El ejemplo que sigue ya dice de qué se
   habla, de modo que basta con nombrar las carpetas.
2. «Las matrices resultantes» aparecía al hablar de la agregación
   horaria, veinte páginas antes de que las matrices se definan. Pasa a
   «las series resultantes», que el lector sí tiene.
3. «Las 10 series» se citaba tres veces sin decir nunca cuáles son.
   Ahora se dice: la demanda y la generación de cada institución.
4. «El integrador» y «la rigidez numérica» llegaban sin glosa, y el modelo
   que los emplea es cosa de tres capítulos más adelante. Pasan a «el
   método numérico que resuelve el equilibrio de una hora no converge».

**Un antecedente que colgaba de una caja.** La subsección de los tipos de
medidor abría con «La explicación es de topología eléctrica», y aquello
que se explicaba solo estaba dicho en una caja de lectura, que un lector
puede saltarse sin perder el hilo. Se antepone la frase que lo sostiene.

**Una cuenta interna que no cuadraba.** El texto anunciaba «las
principales elecciones del pipeline, y la única del modelo», y enumeraba
dos del modelo, la ausencia de gestión de la demanda y el descarte de las
horas difíciles.

**Una desigualdad que solo valía para una institución.** «La generación
expuesta al mercado es menor que la instalada en el sitio» solo es cierta
en Udenar, que aporta tres inversores y expone uno; en las otras cuatro el
equipo designado es el único, de modo que coinciden. Cierra P-11.

**Lo demás.** Un pie de figura que no decía de qué institución era la
serie que dibuja, y ahora nombra a la Universidad Mariana, que es la de
más valores atípicos; «un piso del 20 % por encima del percentil», que se
leía como un piso del 20 %; una aposición que se leía como un miembro más
de la enumeración; y dos referencias con una notación de sección que el
documento no usa en ningún otro sitio.

---

## C-45 · Adaptación del párrafo de apertura reescrito por el autor
**2026-08-23 · tipo: `estilo` · aplicada**

Él reescribió el párrafo de apertura del capítulo 3 y pidió comprobarlo
contra la norma. Siete cosas.

**Tres de gramática.** «Los archivos en los que escriben cada uno de los
27 equipos» no concuerda, porque el sujeto es «cada uno» y va en
singular. «Una lecturas cada dos minutos» tampoco. Y «Asi» iba sin tilde
y sin la coma que pide un conector antepuesto.

**Una unión de oraciones sin nexo.** «La distancia entre los dos extremos
es bastante amplia, de un lado están los archivos» junta dos oraciones
independientes con una coma. Se resuelve con dos puntos, que además es lo
que la relación pide: lo segundo explica lo primero.

**Un término nuevo para algo que el capítulo ya nombra.** «10 fases»
introduce una tercera palabra para lo mismo, cuando la figura dice
«etapas» y el párrafo siguiente «transformación». Se unifica en
«transformaciones», que enlaza con lo que viene inmediatamente después.

**Una atribución de causa que no consta.** «Huecos donde la transmisión de
los datos falló» dice por qué faltan los datos, y eso no está establecido
en ninguna parte. Vuelve a «la adquisición», que es el término neutro que
usa la figura de cobertura del capítulo 2.

**Dos giros que decían otra cosa.** «Cada una determina una decisión
fundamental»: una transformación no determina una decisión, la encierra, y
«fundamental» generaliza lo que no vale para las diez. Y «analizar con
solidez las cifras» no es lo que se quiere decir, que es juzgar si las
cifras son sólidas.

**Lo que se conserva de su versión**, porque es suyo y funciona: el giro
«Del otro lado», el cierre impersonal en lugar de la figura del lector, y
la idea de que la distancia entre los extremos es amplia, que él prefirió
a la formulación anterior.

El párrafo queda en 24,5 palabras por oración, contra las 24,6 del perfil.

---

## C-46 · Los nombres de fichero salen de la prosa del capítulo 3
**2026-08-23 · tipo: `estilo` · aplicada**

Él pidió el mismo tratamiento que se dio al capítulo 2: no nombrar
archivos de código en el texto corrido, y decirlo de otra forma. Es la
norma C-12, que este párrafo incumplía.

**Sobraban, además, por una razón concreta.** El pie de la figura que
viene cuatro líneas más abajo ya declara los dos módulos como procedencia,
que es uno de los tres sitios donde la norma los admite. Quien quiera los
nombres los tiene ahí; quien lea la prosa no tropieza con ellos.

**Lo que se conserva es la sustancia**, que es el reparto de
responsabilidades: una genérica, que no sabe de instituciones y se ocupa
de localizar, leer y limpiar; y otra propia de esta comunidad, que decide
qué punto físico se mide en cada institución y garantiza que la demanda no
llegue negativa al modelo.

**Y se añade el dato que hace útil la distinción**, que antes no estaba: de
las tres etapas que alteran el valor del dato, dos pertenecen a la
segunda. Sin eso, el reparto es una curiosidad de implementación; con eso,
dice dónde se juega la fidelidad.

También pierde su ruta la caja del docstring, que pasa a nombrar el papel
del módulo y no su ubicación. Ahí la norma sí lo admitiría, porque el
objeto de la caja es ese mismo texto, pero el papel se lee mejor.

**Lo que queda y por qué.** En la prosa siguen los nombres de las cuatro
codificaciones y el rango de bytes donde se corrompen las tildes. No son
artefactos del programa sino estándares, como una resolución citada por su
número, y el objeto de esa subsección es precisamente el orden en que se
prueban. Igual ocurre con el nombre de la carpeta que llega con una
errata, que es de lo que habla el párrafo.

---

## C-47 · El párrafo del mapa prometía una cosa y entregaba otra
**2026-08-23 · tipo: `contenido` · aplicada**

Él lo describió como un caos y pidió compararlo contra el capítulo 2 y
contra lo que le precede. El problema no estaba en las frases sino en el
orden.

**Anunciaba el mapa y no lo daba.** Abría con «antes del detalle conviene
tener el mapa» y gastaba tres oraciones en una propiedad concreta, la
bifurcación, antes de llegar a la figura. El anuncio y lo anunciado
quedaban separados por todo el párrafo, cuando el resto del documento
cierra con la figura el párrafo que la motiva.

**Arrancaba en frío.** «La bifurcación» llegaba sin que nada anterior
hubiera dicho que el proceso se separa en dos, y el capítulo 2 tampoco lo
dice: nombra las dos coberturas, pero no que el trabajo entero se recorra
dos veces.

**Usaba vocabulario que aún no tocaba.** «Qué subcarpeta de medidor se
lee» es lenguaje de sistema de archivos treinta líneas antes de que se
explique la estructura de carpetas, y el lector no tiene con qué
entenderlo.

**Y duplicaba el pie de la figura**, que ya dice que la bifurcación ocurre
en la etapa 1 y cuáles son las tres etapas resaltadas.

Se separa en dos párrafos. El primero motiva la figura y termina en ella,
diciendo lo que el pie no dice: que las diez no son de la misma clase y
que saber cuáles alteran el valor es lo que permite discutir después la
fidelidad sin revisarlo todo. El segundo, detrás de la figura, saca la
consecuencia, que es lo único que quedaba sin decir en ninguna parte: como
los dos recorridos se separan en la primera etapa y solo en ella,
cualquier diferencia entre M1 y M3 es atribuible a qué se mide y no a cómo
se procesa. Y se declara de paso que el trabajo se recorre dos veces, que
hasta aquí se daba por sabido.

---

## C-48 · Una frase vaga, y el hueco que apareció al concretarla
**2026-08-23 · tipo: `contenido` · aplicada**

Él preguntó qué quería decir «saber cuáles son las primeras es lo que
permite discutir después la fidelidad del resultado sin revisarlo todo».
La pregunta estaba bien hecha: la frase no decía cuántas son ni qué se
ahorra, de modo que enunciaba una ventaja sin cuantificarla.

Concretado: de las 10 etapas, solo 3 alteran el valor del dato y las otras
7 lo ubican, lo convierten o lo verifican, de manera que una objeción
sobre la fidelidad de las cifras solo puede dirigirse a esas 3. También se
unificó «fase» con «etapa», que convivían en la misma oración.

**Y al concretarlo apareció que el capítulo se contradecía.** Sostiene que
las cinco primeras etapas no tocan el valor, y la cuarta recorta la salida
del inversor a valores no negativos, que es una alteración en toda regla.
Si un revisor lo nota, la afirmación de que solo tres etapas mueven cifras
se cae.

Medido sobre los siete inversores y todos sus registros: **cero lecturas
por debajo de cero**. El recorte es defensivo y no llega a actuar nunca,
de modo que la afirmación se sostiene, pero solo porque el dato no la pone
a prueba. Eso se dice ahora en el párrafo de las unidades, que era donde
faltaba.

---

## C-49 · El diagrama del pipeline, rehecho
**2026-08-25 · tipo: `técnico` · aplicada**

La figura 3.1 decía casi lo que dice ahora, pero lo decía mal. Las diez
etapas iban en tres filas de cajas iguales, de modo que los tres grupos de
que habla el texto (las cinco que localizan, las tres que alteran el valor
y las dos que ensamblan) no se distinguían: el corte entre grupos caía en
mitad de una fila. La única marca era el color de tres cajas y una llave
que hubo que trazar de este a oeste para que no cruzara las cajas que
pretendía agrupar. Y la propiedad que sostiene todo el capítulo 4, es
decir que las dos coberturas se separan en la etapa 1 y solo en ella, se
enunciaba en una nota al margen: no se veía.

Se sustituyó solo el bloque `tikzpicture`; el pie y el texto que rodean la
figura quedaron intactos. El diagrama es ahora de tres carriles, uno por
grupo, cada uno con su rótulo a la izquierda y su fondo propio, y el del
medio resaltado. La bifurcación se dibuja: dos marcas, M1 y M3, con los
mismos colores que el esquema de fronteras del capítulo 4, entran en la
etapa 1 y no vuelven a aparecer. La salida se declara con su dimensión y
con la propiedad que se verifica, que es la no negatividad.

Dos rótulos cambiaron de palabra. La etapa 10 decía «Localizar zona
horaria», que repetía el verbo de la etapa 1 con otro sentido y era un
calco del nombre de la función; ahora dice «Fijar la zona horaria». La 5
decía «Agregar a una hora» y dice «Agregar a paso horario», que es como la
nombra el propio texto.

Comprobado contra `data/xm_data_loader.py` y `data/preprocessing.py`: las
diez etapas existen, están en ese orden salvo lo que recoge P-14, y las
tres resaltadas son las que mueven cifras. Compila sin errores y sin
desbordes, y la figura sigue cayendo en la página 15.

---

## C-50 · P-15 cerrada: la bifurcación no era solo la etapa 1
**2026-08-23 · tipo: `dato` · aplicada · cierra un pendiente**

El agente que rehízo el diagrama comprobó el pipeline contra el código y
encontró que la afirmación del capítulo 3 es más fuerte de lo que el
código sostiene. Verificado aparte antes de aceptarlo.

**Lo que dice el código.** La configuración de medidores lleva tres
campos, no uno: la subcarpeta que se lee, el tipo de medidor declarado y
un factor de escala. En la frontera principal los tipos son neto, neto
parcial, neto parcial, bruto y bruto; **en la secundaria los cinco son
brutos**, de modo que la reconstrucción de la etapa 7 no llega a
ejecutarse. Y la demanda de Mariana en la frontera secundaria **se
multiplica por 0,3**, con el mismo medidor que en la principal, porque esa
institución no tiene un segundo medidor que leer.

**Por qué importaba.** El capítulo decía «lo único que cambia es de qué
medidor se lee, y el tratamiento posterior es idéntico», y la anotación
dentro de la figura repetía «aquí, y solo aquí». Ninguna de las dos se
sostiene: el factor de escala no es una propiedad del medidor.

**Lo que sí se sostiene, y se conserva**, es el argumento de fondo. El
tipo de medidor sí es una propiedad del punto de medida, de manera que la
diferencia de reconstrucción se sigue de qué se mide y no de cómo se
procesa. Reescrito el párrafo con esa distinción y con la excepción de
Mariana declarada, que el capítulo 4 ya recogía y el 3 contradecía sin
saberlo. La anotación de la figura pierde el «y solo aquí».

---

## C-49bis · La figura del pipeline, revisada tras el rediseño
**2026-08-23 · tipo: `técnico` · aplicada**

El rediseño resolvió el defecto de fondo: el texto describe tres grupos de
etapas, 5, 3 y 2, y la disposición anterior en filas de cuatro, cuatro y
tres partía los grupos por la mitad, de modo que no se veían. Ahora son
tres carriles con fondo propio y rótulo, y la bifurcación pasa de nota al
margen a objeto gráfico, con las marcas M1 y M3 en los mismos colores que
el esquema de fronteras del capítulo 4.

Se conserva la corrección de dos rótulos: «Localizar zona horaria» pasa a
«Fijar la zona horaria», porque repetía el verbo de la etapa 1 con otro
sentido y calcaba el nombre de una función, y «Agregar a una hora» pasa a
«Agregar a paso horario», que es como lo llama el texto.

---

## C-51 · «Cobertura» significaba dos cosas; ahora frontera y cobertura
**2026-08-23 · tipo: `estilo` · aplicada · norma permanente**

Él preguntó si las coberturas M1 y M3 estaban definidas en el capítulo 2.
La comprobación destapó dos problemas distintos.

**Primero, la palabra tenía dos sentidos.** En el capítulo 2 domina el de
fracción de horas con registro, con una subsección y una figura enteras
dedicadas a la cobertura de adquisición. En los capítulos 3 y 4 significa
la frontera de medición, es decir, qué circuito se lee. Y en una nota del
capítulo 4 aparecía un tercer sentido, porque llamaba «las dos coberturas»
a las razones 19,1 % y 91,2 %, que C-19 ya había establecido que son razón
entre generación y demanda del circuito medido.

**Decisión suya:** frontera para el circuito, cobertura solo para las
horas. Aplicadas 28 sustituciones en los capítulos 2, 3 y 4, incluidas las
de pies y notas, porque dejar allí el término viejo produciría justo la
incoherencia que se quiere evitar. También en la nomenclatura, que definía
las dos entradas como «cobertura de medición», y en un pie que llamaba
«cobertura de generación» a la razón.

Quedan tres usos de «cobertura», los tres en el sentido de fracción de
horas con registro.

**Segundo, y menos grave de lo que pareció.** M1 y M3 **sí** están
definidos, en la tabla de nomenclatura, que precede a la introducción. Lo
verifiqué mal en la primera lectura y hay que decirlo. Lo que faltaba es
otra cosa: en el texto corrido del capítulo 2 aparecen solo en el
encabezado de una tabla, y el capítulo 3 los usa diez veces dando por
sabido algo que la narración nunca recoge. Una entrada de nomenclatura es
una consulta, no una presentación.

Se añade en el capítulo 2, junto a la tabla del inventario, el párrafo que
faltaba: que el modelo lee uno de los dos medidores de cada institución,
que el trabajo entero se recorre dos veces, y que a esos dos recorridos se
los llama M1 y M3 por el número del medidor que emplean.

**Lo que no se tocó.** Las etiquetas internas y los nombres de fichero de
figura conservan la palabra vieja. No son prosa y renombrarlos obligaría a
tocar los generadores sin cambiar una sola línea impresa. Queda anotado.

---

## C-52 · El párrafo de la propiedad del mapa era denso y prematuro
**2026-08-23 · tipo: `contenido` · aplicada**

Él lo señaló como ambiguo y denso. Medido: **141 palabras y seis
oraciones**, cuando los párrafos del capítulo van por unas 70 y tres. Una
sola de sus oraciones tenía 36 palabras y otra 30.

**El defecto de fondo no era la longitud sino el orden de presentación.**
El párrafo apoyaba su único dato concreto en dos términos que el capítulo
define más adelante: «los cinco son brutos», y el tipo de medidor se
define en la subsección siguiente; y «la reconstrucción de la etapa 7»,
que se explica dos subsecciones después. El lector tenía que aceptar a
crédito el vocabulario con que se le demostraba la afirmación.

Partido en dos párrafos, uno por idea. El primero enuncia la propiedad y
por qué se sostiene, que el tipo de medidor es una propiedad del punto
donde está puesto y no una decisión de proceso. El segundo saca la
conclusión y declara la excepción de Mariana.

**El dato concreto no se pierde: se muda.** «En la frontera M3 los cinco
medidores son brutos y ninguna institución requiere reconstrucción» pasa
al final de la subsección de los tipos de medidor, que es donde «bruto»
acaba de definirse y donde el lector se pregunta justamente qué ocurre en
la otra frontera, porque esa subsección se declara explícitamente
restringida a M1.

También se retiró una remisión al Capítulo 4 que aparecía dos veces en el
mismo párrafo.

---

## C-53 · «Lo demás se sigue de esa elección» no decía qué ni por qué
**2026-08-23 · tipo: `contenido` · aplicada**

Él preguntó qué significaba. La frase decía «lo demás se sigue de esa
elección, porque el tipo de medidor no es una decisión de proceso sino una
propiedad del punto donde está puesto», y falla por dos sitios.

**«Lo demás» no tenía referente.** Podía ser el resto del proceso o el
resto de las diferencias entre las dos fronteras, que no es lo mismo.

**Y la justificación se apoyaba en vocabulario prematuro.** «Tipo de
medidor» se define dos subsecciones más adelante. Es el mismo defecto que
C-52 acababa de corregir en ese párrafo: al sacar el dato concreto quedó
una justificación abstracta que se apoyaba en el mismo término que aún no
existe.

Reescrito sin ese apoyo y diciendo lo que se quería decir: «de ahí en
adelante el tratamiento es el mismo para las dos: si algo sale distinto es
porque el medidor elegido lo provoca, no porque se le aplique una regla
diferente». Eso es exactamente lo que sostiene la conclusión del párrafo
siguiente, y se entiende sin haber leído nada posterior.

**La lección, que ya va por la tercera vez.** Al quitar de un pasaje un
término que llega demasiado pronto, hay que comprobar que la frase que
queda no se apoye también en él.

---

## C-54 · Las etapas del pipeline pasan de diez a nueve
**2026-08-23 · tipo: `estructura` · aplicada**

Él señaló que las etapas de localización y lectura le parecían
irrelevantes para este documento. Un agente aislado juzgó las diez contra
tres criterios, con acceso al código, y midió sobre el dato crudo antes de
opinar. Le dio la razón, y con más motivo del que él suponía, pero la
recomendación no fue borrar dos sino **fundirlas en una**.

**Lo medido, que es lo que decide.**

| Lo que el capítulo argumentaba | Lo que ocurre |
|---|---|
| Cuatro codificaciones en orden, y por qué una antes que otra | Los 73 archivos resuelven en la primera; ni un byte por encima de 127 |
| Búsqueda tolerante a diferencias de escritura | Las diez carpetas coinciden exactas con lo configurado |

Es decir, las seis líneas que argumentaban el orden de decodificación
describen un camino de código que **no se ejecuta ni una vez**, y sobre
dos columnas que además son ASCII. Una decodificación equivocada no habría
movido una cifra.

**Por qué fundir y no borrar.** Las dos etapas cargaban dos cosas que sí
valen y que no están dichas en ningún otro sitio: el aviso incondicional
cuando un archivo es ilegible, que contesta a «¿cómo sabe que no perdió
una institución entera sin enterarse?», y la declaración de que el
registro de un equipo llega partido en varios archivos. La etapa fusionada
se queda con las dos, en 78 palabras contra las 221 de antes.

**El argumento del capítulo mejora.** De «3 de 10» pasa a **3 de 9**, que
se dice «una de cada tres». Los tres carriles siguen valiendo y el rótulo
del primero sigue siendo literal, porque la etapa fusionada localiza y
decodifica.

**Un defecto de hecho corregido de paso.** El texto decía que los tramos
de un mismo medidor «se leen y concatenan». El código no concatena: alinea
sobre el eje del tiempo y **suma**. Comprobado sobre el medidor principal
de Udenar, los tres tramos se solapan en dos instantes exactos, uno de
ellos dentro del horizonte, de modo que esa hora se cuenta dos veces. El
texto pasa a decir «se alinean sobre el eje del tiempo».

**Y una contradicción interna.** El capítulo decía a la vez que las diez
etapas encierran «cada una una decisión que puede cambiar el resultado» y
que solo tres alteran el valor, a nueve líneas de distancia. La primera
pasa a «ninguna es automática: en todas se decidió algo», que no
contradice a la segunda. También se afinó «las cinco primeras etapas no
cambian ningún valor», que era falso porque la quinta calcula una media:
ahora dice que no intervienen sobre el valor medido.

**Lo que bajó al anexo.** La cascada de codificaciones y la errata de la
carpeta van al Anexo~A, cada una con la medida que la hace prescindible.
Se documentan porque el orden es una decisión deliberada del cargador y
porque otro conjunto de datos sí podría ejercerla.

**Coste pagado.** Seis sitios de prosa, cinco cajas renumeradas y dos
flechas en la figura, la ficha de la guía y este registro. La única
remisión externa, la del capítulo 4 al decir que la bifurcación ocurre en
la primera etapa, sobrevive intacta porque la fusión respeta que la etapa
1 siga siendo la 1.

---

## C-56 · La etapa de las marcas de tiempo pasa a tabla de casos

**2026-08-26 · tipo: `estructura` · aplicada**

Él pidió que cada etapa recibiera un tratamiento formal, código, pseudocódigo
o diagrama, empezando por esta. Se probó el pseudocódigo en dos vueltas y la
segunda la descartó él: «es claro pero no me parece la estructura adecuada
para explicar esta etapa». Tenía razón, y el motivo es de fondo.

**Por qué el pseudocódigo no servía aquí.** La etapa no es un procedimiento:
es una secuencia recta con tres guardas, sin bucles ni anidamiento. Escrita
como algoritmo degenera en una lista numerada con ceremonia alrededor. Lo que
la etapa realmente tiene son **tres casos con tres tratamientos**, y eso es
una tabla.

**Dos vueltas fallidas que conviene no repetir.** La primera versión estaba
escrita en notación de conjuntos, con cuatro letras sueltas y dos nombres de
función inventados, y encima usaba la misma letra como columna en una línea y
como función en la siguiente. La segunda ya se entendía, pero mezclaba dos
formas de condicional sin motivo. La lección es que **la ceremonia formal no
añade precisión cuando lo formalizado no tiene estructura**; solo añade una
capa que el lector debe decodificar.

**Lo que la tabla gana sobre la prosa anterior.** Absorbe las cifras que
estaban sueltas en el párrafo de cierre, y un conteo por frontera se lee en
una columna mucho mejor que en una frase. Queda así:

| Lo que puede venir mal | Qué se hace con ello | M1 | M3 |
|---|---|---|---|
| La fecha no se deja interpretar | La lectura se descarta entera | 0 | 0 |
| El valor no se deja interpretar | El valor queda en blanco y la lectura se conserva | 0 | 0 |
| Dos lecturas comparten el mismo instante | Se sustituyen por una sola, con el promedio | 3.099 | 3.622 |

**Un defecto de hecho corregido de paso.** El texto anterior describía dos
operaciones y el cargador hace cuatro: omitía que **la columna de valor
también se convierte en modo tolerante**, no solo la de fecha. Y omitía la
asimetría, que es lo único que un lector podría entender al revés: la fecha
ausente descarta la lectura entera, el valor ausente no, porque se conserva
en blanco hasta la limpieza.

**Lo medido**, sobre los 2.813.305 registros crudos de los diez medidores que
el modelo emplea: ni una sola fecha ilegible, ni un solo valor no numérico.
Las dos primeras ramas nunca se ejecutan. La tercera sí, concentrada en la
UCC, que aporta 3.071 de los instantes repetidos de M1 y 3.551 de los de M3;
el resto son decenas en Mariana. La dispersión entre lecturas que comparten
instante es de 0,000 kW en los diez casos, de modo que promediar equivale a
quedarse con una.

**Infraestructura añadida.** El preámbulo carga el aparato de pseudocódigo
(paquetes de algoritmo con las palabras clave en español y colocación
forzada) y el paquete que impide separar un párrafo de su tabla. El primero
queda cargado pero **sin uso por ahora**: se reserva para las etapas que sí
tienen ramificación, que son clasificar el medidor, reconstruir la demanda
bruta, y atípicos y huecos.

**Criterio que queda fijado.** El vehículo se elige por la forma de la etapa,
no por uniformidad: tabla cuando son casos, algoritmo cuando hay
ramificación, prosa cuando es una sola operación con su justificación.

> **Superada por C-57.** La tabla que aquí se construye desaparece: al pedir
> él la justificación de la regla de fusión se comprobó que la etapa entera
> no mueve ninguna cifra, y las tres primeras etapas se fundieron en una. Lo
> que sobrevive de esta entrada es el criterio de elección del vehículo y la
> medida de las tres anomalías.

---

## C-57 · Las tres primeras etapas se funden en una, y el pipeline queda en seis

**2026-08-26 · tipo: `estructura` · aplicada**

Él pidió dos cosas sobre la etapa de marcas de tiempo: que se justificara
sobre los casos reales **por qué el promedio y no una de las dos lecturas**,
y que se evaluara fundirla con la siguiente y bajar el procedimiento
completo al anexo. El principio que enunció gobierna la decisión: «no vale
de nada reportar en este documento algo que no se aplica realmente».

**La justificación pedida no existe, y comprobarlo es el hallazgo.** Medido
sobre el dato crudo con el orden real del cargador, que funde duplicados
dentro de cada archivo antes de alinear los tramos:

| | M1 | M3 |
|---|---|---|
| Instantes con más de una lectura | 3.099 | 3.622 |
| De ellos, con lecturas idénticas al bit | 3.099 (100 %) | 3.622 (100 %) |
| Diferencia entre promediar y quedarse con la primera | 0,000000 kW | 0,000000 kW |
| Máximo de lecturas en un mismo instante | 11 | 73 |

Es decir, **las tres reglas de fusión posibles dan el mismo número**, y la
pregunta «por qué el promedio» no tiene respuesta analítica. El motivo que
el propio cargador anota es de forma: el índice ha de ser único para poder
superponer los tramos de un mismo medidor.

**Consecuencia sobre la tabla de C-56.** De sus tres filas, dos no
ocurrían nunca y la tercera describía una decisión sin consecuencia. La
etapa completa no movía una sola cifra del documento, de modo que no
merecía ni etapa propia ni tabla.

**Lo aplicado.** Se funden las tres primeras etapas —marcas de tiempo,
unidades y agregación horaria— en una sola, que es como la subsección ya se
llamaba: *Del archivo a la serie horaria*. Es una única idea, convertir
muestras de dos minutos en una serie horaria en las unidades del modelo. El
pipeline pasa de 9 etapas a **6**, y el argumento del capítulo mejora al
concentrarse: de «3 de 9 alteran el valor» a **«3 de 6»**, la mitad.

**Cierra P-14.** El cargador convierte la unidad *después* de promediar a la
hora, y el documento lo exponía al revés. Dentro de una etapa única el orden
se enuncia como se ejecuta, y se dice además por qué da igual: dividir entre
una constante conmuta con la media.

**Lo que bajó al Anexo A**, con su medida: la conversión tolerante de fecha
y valor, con la asimetría entre las dos columnas y sus cero casos sobre
2.813.305 registros; la fusión de instantes repetidos, con la tabla por
institución y frontera y la equivalencia de las tres reglas; y el orden
exacto de las ocho operaciones del cargador.

**Un dato lateral que se anota y no se explota.** El medidor secundario de
la UCC llega a volcar 73 lecturas idénticas en un mismo instante, y el
principal 11. Es un rasgo del equipo y no del método. Queda en el anexo
porque no altera ninguna cifra; si alguna vez se quiere en el Capítulo 2,
es material de calidad del dato crudo.

**Coste pagado.** La figura del pipeline rehecha a 6 cajas en tres carriles,
el recuento reconciliado en los 4 sitios donde se enuncia, la subsección 3.2
reescrita entera, el anexo ampliado, la ficha de la guía y este registro.
La remisión del Capítulo 4 sobrevive intacta, porque la bifurcación entre
fronteras sigue ocurriendo en la etapa 1.

---

## C-58 · La etapa 1 se enseña sobre una hora real

**2026-08-26 · tipo: `figura` · aplicada**

Él señaló que la subsección de la primera etapa seguía sin entenderse y
pidió trazar el flujo con datos reales de un día o una hora de alguna
institución. El diseño lo exploró un agente aislado con acceso al dato
crudo; la implementación y la comprobación son de esta sesión.

**El ejemplo elegido: la UCC, medidor principal, jueves 6 de noviembre de
2025, 13 horas.** No es una elección de conveniencia, y el motivo es
severo:

- **Es la única hora del conjunto donde la fusión de instantes se puede
  ver dentro del horizonte.** Udenar, el HUDN y Cesmag no tienen ni un
  duplicado dentro de archivo. La UCC concentra 3.071 de los 3.099 de M1,
  pero casi todos viven en el tramo de 2026, que el recorte descarta:
  dentro del horizonte solo quedan unas decenas, y **ocho caen en esta
  misma hora**.
- **Es hora solar**, de modo que el inversor lleva vatios con sentido
  (3.577 a 5.221 W) y la división entre mil se ve sobre un número real.
- **La media del inversor es 4.092 W exactos**, que entre mil da
  4,092 kW: el mismo número con el separador corrido tres lugares. Es la
  demostración más intuitiva posible de esa conversión.
- **El medidor de la UCC está partido en tres archivos**, uno que empieza
  antes del horizonte y otro que cae entero después, de modo que el
  recorte y la alineación de tramos, que en otras instituciones son un no
  evento, aquí actúan y se pueden dibujar.

**La figura, en tres bandas.** Arriba, el calendario de los archivos con el
horizonte sombreado y lo que queda fuera rotulado. En el centro, la hora
ampliada en cada equipo, con los ocho instantes duplicados anillados y la
media trazada. Abajo, esa media ocupando su lugar entre las 24 horas del
día. Se lee como un embudo: meses, una hora, un valor.

**M1 solo, y con motivo.** El tratamiento de esta etapa es idéntico en las
dos fronteras y lo único que cambia es qué medidor se lee, cosa que ya dice
la figura del pipeline. Un panel M3 gemelo repetiría la mecánica con otros
números sin enseñar una idea nueva y robaría la mitad del ancho. La
frontera se declara con el rótulo de cobertura.

**El generador se detiene antes que mentir.** Comprueba cinco cosas: que la
hora trae 38 filas, 30 instantes y 8 duplicados; que el inversor trae 30
lecturas; que ninguna es negativa; que las repetidas son idénticas; y que
las dos medias reproducen al bit lo que el caché del preprocesamiento
guarda para esa hora. Si el dato crudo cambia de versión, cosa que P-6
deja abierta, la figura no se genera.

**Una precisión que la figura permite y la prosa no daba.** Cuál de las
tres reglas de fusión se use da igual, y eso ya lo decía C-57. Fundir o no
fundir no da igual: si las repetidas contaran cada una por su lado, esa
hora pesaría 30,10 kW en vez de 30,49 kW, porque los duplicados arrastran
la media hacia su propio valor. La nota al pie lo separa explícitamente
para que no se lea como una contradicción.

**Lo que la figura NO dice, deliberadamente.** El valor de 30,49 kW no es
la celda final de la matriz de demanda: la UCC es medidor neto parcial y
la reconstrucción lo lleva más arriba. Ni el pie ni ningún rótulo dicen
«matriz» ni «celda»; siempre «la serie horaria», que es lo que la etapa 1
entrega. Tampoco se anota que los tramos primero y segundo comparten el
instante del 1 de junio y el cargador los suma, que es P-17 y sigue
pendiente de su decisión; si la toma, esta línea de tiempo es el lugar
natural para declararlo.

**Coste pagado.** Generador nuevo en el guion del capítulo 3, con su tabla
hermana de 112 filas y su archivo de procedencia; el párrafo de apertura de
la subsección remite a la figura; ficha en la guía y este registro. Dos
tiraje s de corrección de composición: rótulos que se pisaban en el
calendario, tramos que se veían pegados, cifras que caían sobre los puntos
y flechas entre bandas que cruzaban los rótulos de eje, estas últimas
retiradas.

---

## C-59 · La integral de la potencia se introduce como es, y el capítulo 2 se corrige

**2026-08-26 · tipo: `metodo` · aplicada**

Él preguntó si promediar las 30 muestras es de verdad lo correcto para
determinar el consumo de una hora, qué significa cada lectura de potencia
activa, y por qué sabemos que responde bien el promedio y no la suma.
Luego pidió contrastar lo medido contra lo que dice el capítulo 2 e
introducir correctamente la integral.

**Qué es cada lectura, comprobado.** Es potencia en kilovatios, una
magnitud absoluta e instantánea. No es energía, no es un acumulado y no se
mide contra ningún valor pasado. La serie sube y baja, mientras que los
contadores acumulados que el mismo archivo trae solo crecen y dan la vuelta
en diez mil; y si cada lectura fuese la energía de sus dos minutos, la
potencia implícita sería treinta veces mayor.

**El promedio, verificado contra el propio equipo.** Sobre las 5.810 horas
completas del circuito principal de la UCC:

| | |
|---|---|
| Sesgo medio (contador − promedio) | +0,008 kWh sobre horas de 19,20 kWh |
| Acumulado, contador | 111.608 kWh |
| Acumulado, suma de las medias | 111.562 kWh (−0,04 %) |
| Si se sumara en vez de promediar | 30,0 veces el contador |

El factor es exactamente el número de muestras. Se confirma igual en
Udenar M1, HUDN M1 y UCC M3, todos con razón 1,00.

**Un sesgo propio, detectado y corregido.** La primera medición leía el
contador del primer al último instante de la hora, que son 58 minutos, y
daba −0,63 kWh de sesgo sistemático. Leído en las marcas de hora en punto,
el sesgo cae a +0,008 kWh. La cifra publicada es la segunda.

**Lo que el capítulo 2 decía y ahora se corrige.**

1. La tabla de las 54 variables daba la unidad de los ocho registros de
   energía acumulada como desconocida. Los cuatro de energía activa son
   **kilovatios hora**, medido; los cuatro de reactiva llevan la unidad que
   les corresponde, aunque lleguen vacíos.
2. La subsección de la reactiva no decía de dónde sale su medición, y no
   puede salir del contador porque está muerto. Ahora dice que procede de
   integrar la potencia reactiva hora a hora.
3. H-13 concluía que integrar la potencia era «la única vía disponible».
   Corregido allí: vale para la reactiva, no para la activa.

**La integral, bien introducida.** El capítulo 3 enunciaba la ecuación
desde cero, repitiendo la del capítulo 2 sin remitirse a ella, y dejaba sin
escribir el paso donde de verdad vive la confusión, que es el discreto.
Ahora remite a la ecuación del capítulo 2 y añade la suya: con $N$ muestras
uniformes de ancho $\delta = \Delta t / N$, la regla de rectángulos da
$\sum P_k \delta = \overline{P}\,\Delta t$. **La media sale del ancho del
rectángulo, no de una convención de agregación**, y sumar equivale a fijar
$\delta$ en una hora, es decir, a conceder una hora entera a cada lectura
de dos minutos. Se conserva además el matiz de que el error de la suma no
sería constante, porque una hora con muestreo incompleto se multiplicaría
por un $N$ menor.

**Y un hallazgo mayor de propina**, en H-16: el contraste destapó que cinco
medidores tienen la potencia y el contador a escalas distintas, por un
factor que el inventario predice en nueve de diez casos. Es P-6, hasta hoy
planteado sin cuantificar.

---

## Pendientes

| Id | Qué | Estado |
|---|---|---|
| P-14 | ~~Capítulo 3: el texto y la figura presentaban la conversión de unidades antes de la agregación horaria, y el código promedia primero.~~ **CERRADA por C-57**: las tres etapas se funden en una y el orden se enuncia como se ejecuta. | cerrada |
| P-15 | La bifurcación entre coberturas no es solo la etapa 1. | **cerrada 2026-08-23** por C-50: reescrito el párrafo y la anotación de la figura, con la excepción de Mariana declarada |
| P-1 | Pasada de vocabulario: el texto usa 3 de los 21 giros característicos del autor. Faltan «asciende a», «se sitúa entre», «conforme a», «línea base», «por transparencia metodológica». | pendiente de decisión |
| P-2 | «es decir» está en 0,89 por mil frente al 1,24 del objetivo. | **cerrada 2026-08-23**: 1,26 tras C-25; el conjunto queda en 24,0 palabras por oración, 11,2 % largas y 74,4 por párrafo, contra 24,6 / 12,0 / 74,0 del perfil |
| P-3 | Abreviaturas: el autor escribe UDENAR, UNIMAR, UCC, UNICESMAG, HUDN. El documento ya usa CESMAG (C-13); quedan por decidir UDENAR frente a Udenar y UNIMAR frente a Mariana. La infraestructura para cambiarlo ya existe: basta editar `ETIQUETA_INSTITUCION` en `estilo.py` y regenerar. | pendiente de decisión |
| P-4 | Capítulo 4: reescribir la contraposición «campus completo frente a ramal fotovoltaico». | **cerrada 2026-08-23** por C-40: cinco pasajes y el diagrama |
| P-6 | Establecer si `MedicionesMTE_v3/` es anterior o posterior a la corrección de escala que describe el inventario. Es prioritario. | pendiente |
| P-7 | Cifrar el cargo del reactivo. | **cerrada 2026-08-23**: no hacía falta una tarifa propia; la norma lo cobra como energía activa en los cargos por uso de redes. 1.877.304 y 1.215.258 pesos. Ver C-29 |
| P-8 | Nivel de tensión del capítulo 5. | **cerrada 2026-08-23** por C-42: se mantiene el nivel 2 y se declara la discrepancia con su magnitud, 18,7 % del costo unitario. La verificación contra facturas sigue abierta |
| P-9 | Capítulo 5: «la agencia internacional de energías renovables» y «el plan indicativo de expansión» no llevan nombre ni cita, de modo que las tres cifras del rango de costo nivelado no se pueden rastrear. Parecen IRENA y la UPME. | pendiente |
| P-10 | Anexo F: una nota dice que el Hospital no rebasa el umbral «ni una sola hora» en el circuito principal, y la tabla le registra 1 hora y 2 pesos. O se redondea en la prosa o la fila está mal. Está dentro de una nota, de modo que la decisión es del autor. | pendiente de decisión |
| P-11 | Capítulo 3: la generación expuesta frente a la instalada. | **cerrada 2026-08-23** por C-44: se distingue Udenar del resto y se enuncia sobre el agregado |
| P-12 | Capítulo 3: la explicación posicional del caso bruto para el Hospital no está probada. Cero horas negativas no demuestran posición: una carga hospitalaria siempre mayor que la generación tampoco invertiría el flujo aunque el medidor neteara. | pendiente |
| P-13 | Quedan dentro de notas al pie de figura, que no se tocan por decisión del autor: «Cesmag» en minúsculas en los capítulos 3, 4 y 5; mezclas de cifras y palabras contrarias a la norma; y en el capítulo 4, dos notas que sostienen la contraposición que C-40 retiró del cuerpo. | pendiente de decisión |
| P-16 | Las etiquetas internas y los nombres de fichero de dos figuras conservan «cobertura» en el sentido de frontera (`fig:frontera-cobertura`, `f4_02_cobertura.png`). No son prosa y no cambian nada impreso; renombrarlos obliga a tocar los generadores. | pendiente |
| P-17 | Los tramos de un mismo medidor se solapan en un instante exacto y el código los suma, de modo que 1 hora de las 6.144 queda contada dos veces en cada institución y en cada frontera. Medido en Udenar: 0,156 kW de error en esa hora. Inmaterial en la cifra; decidir si se declara o se corrige el cargador. | pendiente de decisión |
| P-18 | La etapa que fija la zona horaria no tiene una sola palabra de prosa, y la suposición que encierra, que las marcas de tiempo vienen en hora local, no se declara en ninguna parte. De ella depende el argumento de que las lecturas negativas se concentran al mediodía. | pendiente |
| P-19 | Capítulo 3: la limpieza dice aplicar «3 tratamientos en cascada» y describe cuatro, porque el residuo a cero no lleva ordinal. | pendiente |
| P-5 | Propagar a la tesis (§3.3 y §5.5) y al artículo la declaración de que la tarifa CEDENAR se usa por decisión y no porque sea la de los cinco comercializadores. | pendiente |
