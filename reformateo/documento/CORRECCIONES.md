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

## C-60 · Se evaluó figura para la unidad y el recorte, y se descartó

**2026-08-26 · tipo: `figura` · aplicada (como prosa, no como figura)**

Él pidió para este párrafo el mismo tratamiento que para el anterior, es
decir, una figura con dato real. El diseño lo exploró un agente aislado con
el encargo explícito de decir que no si no había nada que enseñar. Dijo que
no, y la medición lo sostiene.

**Por qué no hay figura.** Las tres afirmaciones del párrafo son, medidas,
sucesos sin varianza:

| Afirmación | Lo medido | Por qué no se dibuja |
|---|---|---|
| La potencia del inversor se divide entre mil | 4.092 W a 4,092 kW | **Ya está dibujado** en la figura de la etapa, sobre una hora real |
| Dividir y promediar conmutan | máx. diferencia 3,553·10⁻¹⁵ kW | Dos curvas idénticas y un panel de ruido en la decimoquinta cifra |
| El recorte a no negativos no actúa | mínimo exacto 0 W en los siete | Siete marcas sobre la misma línea del cero |

El capítulo ya tiene el precedente correcto para esta clase de hecho: las
tres anomalías que nunca ocurren se resuelven en prosa con su cifra, sin
figura. Este párrafo pertenece a esa clase.

**Lo que sí faltaba, y es de fondo.** El párrafo decía que el recorte
«tampoco llega a actuar» y callaba dónde actúa. En el código se aplica
sobre la **serie ya horaria**, no sobre las muestras crudas, y a diferencia
de la división **el recorte no conmuta con la media**: una lectura negativa
dentro de una hora de media positiva no se recortaría y rebajaría el valor
horario. Hoy la distinción es inocua, pero por un hecho más fuerte que el
que la etapa necesita, no por la etapa misma. Ahora se dice.

**Lo medido, verificado por mí contra el dato crudo** (no heredado del
agente): 793.981 lecturas de los siete inversores en el horizonte, mínimo
**exactamente 0 W** en los siete dentro y fuera del horizonte, cero
lecturas negativas, y entre 3.575 y 91.971 ceros por equipo.

**Una frase del agente que no sobrevivió a comprobarla.** Proponía que los
siete tocan el cero «cada noche». Medido por días con dato, se cumple en
255 de 255, 255 de 255, 103 de 103, 254 de 255, 254 de 254, 253 de 255 y
254 de 255. Casi, pero no. La redacción pasa a «lo tocan miles de veces»,
que es cierto para los siete.

**Compuerta añadida.** El párrafo cita cifras y no tiene figura que las
ate, de modo que el guion del capítulo gana una comprobación que no dibuja
nada y se detiene si el conteo, los mínimos o la conmutación dejan de
reproducir.

**Un aviso para quien verifique.** El conteo de 793.981 son filas crudas.
El medidor del inversor de la UCC trae 50 instantes duplicados en el
horizonte, de modo que quien cuente sobre la serie ya fundida obtendrá
793.931 y creerá ver un error.

---

## C-61 · El párrafo de la unidad pasa a lengua llana y su aparato baja al anexo

**2026-08-26 · tipo: `redaccion` · aplicada**

Él dijo, sobre la versión que C-60 acababa de dejar: «sigo sin entender
nada de esto». Tenía razón, y el defecto era de destinatario.

**El diagnóstico.** Los dos párrafos estaban escritos para un revisor de
código y no para un lector. Los dos seguían la misma forma, «aquí hay una
sutileza sobre el orden de las operaciones, pero medida da igual», de modo
que el lector recibía dos avisos seguidos y ningún hecho. Tres defectos
concretos:

1. «El orden entre las dos operaciones» no decía cuáles, y una de ellas,
   promediar, no aparecía en el párrafo: estaba dos párrafos más arriba.
2. «Conmuta con la media» es jerga soltada sin traducir, y «se enuncia como
   se ejecuta» no significa nada para quien no ha visto el código.
3. «Un hecho más fuerte que el que la etapa necesita» era una manera
   retorcida de decir que no hay ni una lectura negativa.

**La causa de fondo.** Los párrafos contestaban una objeción que el lector
no tiene. Nadie se pregunta si dividir entre mil antes o después de
promediar cambia algo. Eso es contabilidad interna del cargador.

**Lo aplicado.** Se quedan los dos hechos que el lector necesita, en lengua
llana y en cinco líneas: que los dos equipos no hablan en la misma unidad y
por eso la del inversor se divide entre mil, y que la potencia que un
inversor inyecta no puede ser negativa, con el recorte que nunca actúa y su
cifra medida. De 190 palabras a 95.

**Lo que bajó al Anexo A**, junto al resto del procedimiento que no se
ejerce: que el cargador promedia primero y divide después; que para la
división el orden es indiferente porque dividir entre una constante y
promediar se pueden intercambiar; y que **para el recorte no lo es**,
porque una lectura negativa dentro de una hora de media positiva
sobreviviría al promedio. El anexo lo dice en lengua llana también, sin la
palabra conmutar.

**La medición no cambia**, sigue siendo la de C-60: mínimo exactamente
0 W en los siete inversores sobre 793.981 lecturas, y conmutación en la
decimoquinta cifra decimal. Lo que cambia es dónde se cuenta y a quién.

---

## C-62 · Barrido de los capítulos 2 y 3 con la lente de C-61

**2026-08-26 · tipo: `redaccion` · aplicada**

Él pidió revisar los dos capítulos «bajo estos mismos ojos», es decir, con
la lente que C-61 dejó fijada: destinatario equivocado, aparato que no hace
trabajo, jerga sin traducir y nombres de código en la prosa. Siete
hallazgos, todos aplicados.

**1. El capítulo imprimía los nombres internos del código, y su propio
código decía que no.** `net`, `net partial` y `gross` aparecían diez veces
en el Capítulo 3: en el diagrama de los tres tipos, en su pie, en las cinco
filas de la tabla y en la prosa de la reconstrucción, más dos como
subíndice. Lo que lo convierte en hallazgo y no en preferencia es que el
código lleva la tabla de traducción con el comentario explícito de que **no
deben imprimirse** (`estilo.py:367`, `gen_cap03.py:36`). Comprobado:
`TIPO_MEDIDOR_ES` no se usa en ninguna parte y `TIPO_ES` se usa una sola
vez, de modo que una figura decía «medidor neto» y el texto de al lado
«net». Ahora el documento dice neto, neto parcial y bruto en los diez
sitios, y la correspondencia con el canon baja al Anexo A para que quien
audite el código no la tenga que adivinar.

**2. El texto nombraba a su lector, y no era el lector.** Decía «conviene
cuantificarlo **antes de que lo haga un revisor**». Es el defecto de C-61
dicho en voz alta. La cifra que sigue se queda; sobraba media frase.

**3. Aparato matemático que no intervenía en el argumento.** El Capítulo 2
soltaba `S = P + jQ`, `|S| = √(P²+Q²)` y `P = |S|cos φ` antes de concluir
que solo la activa transfiere energía neta. Ninguna de las tres se usa en
ese razonamiento ni vuelve a aparecer. Fuera las tres. De paso se corrigió
que la reactiva y la aparente «habrían servido igual de bien», que es
justo lo contrario de lo que el párrafo demuestra, y se añadió por qué la
aparente tampoco sirve, que antes no se decía.

**4 y 7. Dos pies de figura nombraban identificadores de código**, una
constante de configuración y una función de limpieza. Nombrar el archivo es
la convención y se queda; nombrar el identificador cruza la raya.

**5. La norma de cifras, incumplida en seis sitios** del Capítulo 3, todos
con dígitos de 0 a 9 sin un 10 o más en la misma serie que lo justificara.
Los «27 dispositivos: 20 medidores y 7 inversores» se quedan como están,
porque ahí la regla de no mezclar manda.

**6. P-19 CERRADA.** La limpieza decía aplicar «3 tratamientos en cascada»
y describía cuatro: el residuo a cero no llevaba ordinal. Ahora son cuatro
y el cuarto lo lleva.

**Comprobado tras aplicar**: ni un nombre interno en la prosa de los dos
capítulos, ni una cifra suelta de las señaladas, 81 páginas, cero errores y
cero desbordes.

---

## C-63 · Un medidor no entrega kilovatios, los registra

**2026-08-26 · tipo: `redaccion` · aplicada**

Él preguntó si el párrafo de las unidades cumplía la norma de C-21, la de
los paréntesis. **No le aplica**, y conviene dejar por qué: C-21 gobierna
el patrón *Magnitud (símbolo)*, que es lo que pide la guía IEEE al escribir
«Magnetization (A/m)». Ese párrafo no anota una magnitud con su símbolo,
sino que nombra las unidades como sustantivos comunes. La forma con
paréntesis sería además incorrecta ahí por la norma de cifras, porque un
símbolo de unidad exige ir con cifra y en esa frase no hay ningún número.

Al comprobarlo apareció un defecto distinto, en el verbo: decía «el
medidor **entrega** kilovatios». Un medidor no entrega potencia, la mide;
el verbo valía para el inversor, que sí inyecta, y era falso aplicado al
medidor. Pasa a «el medidor **registra en** kilovatios y el inversor **en**
vatios», que es además el verbo que el Capítulo 2 ya usa para los
medidores.

---

## C-64 · Las cuatro comprobaciones que dan cero, juntas y una sola vez

**2026-08-26 · tipo: `metodo` · aplicada · norma investigada, no supuesta**

Él planteó una duda de fondo: si una etapa del preprocesamiento no tiene
ningún efecto sobre el dato, ¿debe reportarse? La duda venía cargada,
porque ya había borrado etapas del diagrama y del texto justamente por eso,
y pidió que no se contestara de memoria.

**La norma, investigada.** El estándar más directo es REFORMS, para ciencia
basada en datos. Su Módulo 4 lleva un ítem que es literalmente este caso:

> **4b. How impossible or corrupt samples are dealt with.** «A dataset may
> contain erroneous or undesirable data points. Data may be impossible
> (e.g., a person whose height is recorded as 10 feet)… our checklist asks
> authors to report such steps.»

Una potencia de inyección negativa es un dato imposible, de modo que **la
regla que lo trata es de declaración obligatoria**, haya actuado o no. Pero
el mismo estándar añade que los autores deben indicar «the section or page
number where the item is reported», es decir, **lo exigible es que exista y
se encuentre, no que esté en la narración**. Un anexo cumple.

A eso se suma la convención de los diagramas de flujo de CONSORT y STROBE,
que reportan los conteos de cada etapa **incluidos los ceros**. La razón es
la que decide: si el cero no se reporta, el lector no puede distinguir «se
comprobó y no había» de «no se comprobó».

**Lo que se borró estuvo bien.** Contrastadas las supresiones anteriores
contra esa norma, todas separaron igual: se fue el procedimiento, se quedó
la cifra. La cascada de codificaciones y la tolerancia de nombres al anexo,
pero «ni una fecha ilegible en 2.813.305 registros» en el capítulo. No se
borró información sino descripción de programa.

**Dónde sí había un problema.** Las cuatro comprobaciones que dan cero
estaban repartidas en dos párrafos consecutivos con la misma forma, «una
salvaguarda que nunca actúa, y su cero». No sobraba contenido: sobraba la
repetición de la forma, que es lo que las hacía sonar a justificación.
Ahora se dicen juntas y una sola vez, con el «ninguna» delante de la
enumeración.

**Y la frase del piso por fin dice para qué está.** «Los siete registran el
cero miles de veces» quedaba en el aire; ahora cierra el argumento: la
ausencia de valores negativos no es que el equipo no alcance esa zona, sino
que la zona no existe. Descarta el artefacto de instrumento.

**La regla que queda fijada, en tres partes:**

1. El procedimiento va al anexo, siempre.
2. La cifra medida se queda en el capítulo **solo si sostiene una
   afirmación que el documento haga**. Aquí la sostiene: el capítulo afirma
   que las matrices son no negativas por construcción, y estos ceros son su
   prueba.
3. **Todas las cifras de esa clase van juntas, una sola vez, no
   repartidas.** Es la parte nueva y la que resuelve la incomodidad.

Fuentes: REFORMS (arXiv 2308.07832); STROBE Explanation and Elaboration
(PLOS Medicine); «Seven steps toward more transparency in statistical
practice» (Nature Human Behaviour).

---

## C-65 · La figura de la demanda negativa enseñaba lo contrario de lo que el texto afirma

**2026-08-26 · tipo: `figura` · aplicada · evaluada contra estándar de visualización**

Él dijo que la sección le gustaba pero que en la figura no se distinguían
las instituciones. Al evaluarla apareció un defecto mayor que el de
legibilidad.

**El defecto de fondo.** El panel izquierdo dibujaba el perfil medio de las
cinco instituciones. Medido:

| Institución | Horas negativas | Mínimo del perfil medio | ¿El promedio cruza el cero? |
|---|---:|---:|---|
| Udenar | 1.517 | −10,95 kW | **sí** |
| Mariana | 213 | **+5,51 kW** | no |
| UCC | 94 | **+8,73 kW** | no |

Es decir, **la media escondía el fenómeno en dos de las tres instituciones
afectadas**. La figura decía «esto es cosa de Udenar» mientras el texto
decía «tres de las cinco». Promediar 256 jornadas ahoga un suceso que
ocurre en el 3,5 % de las horas de Mariana.

**El defecto que él señaló, y su nombre.** Cinco series categóricas con
cuatro apiladas en una banda estrecha. El estándar de visualización lo
llama por su nombre y da la cura: cuando una serie es el asunto y el resto
es contexto, la forma correcta es **emphasis**, una sola serie destacada, no
cinco colores compitiendo. La guía es explícita en que lo categórico
«puede enterrar el único dato que importa».

**Un tercer defecto, de redundancia.** El panel derecho daba horas y
mínimos por institución, que es exactamente lo que la Tabla de los tipos de
medidor repite dos páginas después. Era una tabla dibujada como barras.

**Lo aplicado.** Izquierda: los cinco perfiles, con Udenar en su color de
institución y las otras cuatro en gris de contexto, más la zona imposible y
el mínimo anotado. La primera versión dejaba a Udenar sola y él lo objetó
con razón: quitar las otras resolvía el amontonamiento pero perdía el
contraste, que es el argumento del párrafo, y además es la mitad de la
forma que el estándar llama emphasis, una serie destacada y el resto en
gris, no el resto fuera. Derecha: **el
conteo de horas negativas por hora del día, apilado por las tres
instituciones afectadas**. Ese segundo panel es el argumento del capítulo
—que el valor negativo no es ruido porque sigue al sol— y hasta ahora
solo existía enunciado en el texto. Dibuja una campana que empieza a las 7,
culmina en 288 horas a las 12 y se apaga a las 17.

**Dos cifras corregidas de paso.** La caja de lectura daba «223 casos a las
13 y 218 a las 12» como si fueran totales; son los de Udenar sola. Los
totales son **288 a las 12 y 282 a las 13**, de modo que el máximo estaba
además en la hora equivocada.

**Sobre la paleta.** Las tres instituciones se validaron con el comprobador
del estándar: separación para daltonismo ΔE 16,1 frente a un objetivo de 8,
y suelo de visión normal 18,2. Pasa con holgura. El único reparo es que el
azul de Udenar queda por debajo del piso de croma y tira a gris; **no se
cambia**, porque repintar la paleta de instituciones tocaría las 39 figuras
y es una decisión de documento, no de esta figura.

**Adaptación a la otra frontera.** En M3 ningún promedio cruza el cero y
solo Mariana registra negativos, de modo que el panel izquierdo pasa a
dibujar el mínimo de cada hora y el título lo declara.

---

## C-66 · La nota al pie y la caja de lectura pasan a cuerpo del texto

**2026-08-26 · tipo: `redaccion` · aplicada · verificada por agente aislado**

Él pidió integrar como contenido los dos bloques que rodeaban a la figura de
la demanda negativa, la nota al pie con el alcance y la caja de lectura con
el argumento del reloj. La integración la verificó punto por punto un agente
aislado, con acceso al caché y a las normas del proyecto.

**La progresión que se buscaba**, y que ahora existe: cuántas horas son,
cuándo ocurren, y por qué eso identifica la causa. Tres párrafos que suben
una escalera, con el «sin embargo» y el «ese patrón» de costura, y un cierre
en bisagra que entrega la subsección siguiente.

**Lo que la caja escondía y la integración destapó.** Su última frase y la
apertura de «Tres tipos de medidor» decían lo mismo, que el patrón apunta al
medidor y no a una avería. En un aparte el lector no lo notaba; en cuerpo de
texto, dos párrafos seguidos con la misma conclusión no se sostienen. La
subsección siguiente entra ahora directa en la topología.

**El hallazgo de fondo del verificador.** El párrafo del alcance, al
ascender de nota a cuerpo, pasó a **duplicar entera la Tabla de los tipos de
medidor**, que tres páginas después da fila por fila institución, horas bajo
cero y mínimo. Choca con C-64 regla 3, con C-65, que unas horas antes retiró
de la figura ese mismo contenido por ese mismo motivo, y con el propio
docstring del generador. Comprobado y cierto. El párrafo se queda con lo que
la tabla no dice, que son las dos participaciones y la concentración, y
remite a ella para el detalle. Se resuelve de paso una ambigüedad: el pie
daba −11,0 kW y el cuerpo −33,57 kW, dos mínimos distintos de la misma
institución a diez líneas, sin decir que uno es la media horaria y el otro la
peor hora.

**Una construcción prohibida que se había colado.** «El panel derecho de la
figura muestra» es exactamente lo que la guía prohíbe y lo que el medidor de
estilo vigila con un contador que vale cero en los cuatro capítulos. Pasa a
«Lo que se cuenta hora a hora es lo contrario», que además arregla una
discordancia que arrastraba, singular en el verbo y plural dos cláusulas
después.

**Dos costuras menores.** La subsección siguiente tomaba su sujeto del
encabezado, «La explicación es de topología eléctrica», y ahora lo lleva
dentro. Y dos párrafos abrían con la misma palabra a tres páginas de
distancia.

**Once cifras verificadas contra el caché, sin una sola desviación**, incluida
la comprobación de que las 288 horas de las 12 y las 282 de las 13 son
totales de las tres instituciones y no de una sola, y de que la suma de las
horas entre las 18 y las 6 es exactamente cero.

**Lo que NO se aplicó del informe.** Pedía devolver el `uente{}` al pie de
la figura, por la regla 4 de la guía. **No se toca**: él quitó a mano la
fuente y la nota de esa figura, y las notas y fuentes son decisión suya
declarada. Queda para que él decida.

**Un aviso que sube de rango.** P-18 sigue abierta, y ahora pesa más: el
argumento de que las negativas se concentran a las 12 descansa en que las
marcas de tiempo vienen en hora local, y eso no se declara en ninguna parte.
Mientras vivía en una caja era un aparte; en el cuerpo es la prueba central
de la subsección.

---

## C-67 · Fuera «aguas arriba» y «aguas abajo»

**2026-08-26 · tipo: `redaccion` · aplicada**

Él pidió no usar el término porque así no se entiende. Aparecía **cuatro
veces** en el Capítulo 3, y el reparo es de fondo: el término pide que el
lector ya sepa por dónde circula la energía, que es exactamente lo que el
párrafo está tratando de explicarle. Explicar la causa con un término que
presupone la causa no funciona.

**Lo llamativo es que el vocabulario llano ya estaba en el documento**, y
en el sitio más visible: los rótulos del diagrama de los tres tipos decían
«el medidor queda antes de la inyección» y «queda después». Es decir, la
figura hablaba llano y el texto de al lado hablaba en jerga.

**Comprobada la topología antes de reescribir**, en el propio diagrama: en
el medidor neto el inversor llega al nudo de la carga, o sea que entra
entre el medidor y ella; en el bruto llega al nudo de la red, o sea que
entra antes del medidor. Las cuatro apariciones eran además coherentes
entre sí, de modo que no había ningún error de lógica escondido, solo de
vocabulario.

**Lo aplicado**, con la misma formulación en los cuatro sitios y en los dos
rótulos del diagrama: *el inversor entra entre el medidor y la carga*
frente a *el inversor entra antes del medidor*. El párrafo de la causa gana
además la glosa que le faltaba, «o dicho de otro modo, de en qué punto del
circuito se conecta cada inversor», y explica por qué eso hace que el
medidor vea la diferencia: la energía del inversor no llega a pasar por él.

**Los rótulos del diagrama se cortaron a mano** porque el justificado
partía «medi-dor».

---

## C-68 · No son tres tipos de medidor, son dos tratamientos y una gradación

**2026-08-26 · tipo: `metodo` · aplicada**

Él preguntó por qué tres tipos y qué hace tan diferente al neto del neto
parcial. La respuesta salió del código, no de la prosa, y obligó a corregir
una afirmación estructural del capítulo.

**El pipeline se bifurca en dos, no en tres.** En `data/preprocessing.py`
la rama es literalmente `if kind in ("net", "net_partial")`, de modo que
los dos primeros tipos recorren el mismo camino y salen con la misma
fórmula. Lo único que `net_partial` cambia en toda la corrida es **el
rótulo que se imprime en el registro**. Y la reconstrucción no consulta el
tipo para saber qué inversores sumar: los toma de una lista aparte.

**Lo que de verdad los separa es una magnitud**, medida sobre el canon: la
generación que queda detrás del medidor frente a lo que ese circuito
consume.

| Institución | Generación detrás | Horas con flujo invertido | Mínimo |
|---|---:|---:|---:|
| Udenar | **73,8 %** | 1.517 (24,7 %) | −33,57 kW |
| Mariana | **21,3 %** | 213 (3,5 %) | −2,41 kW |
| UCC | **11,7 %** | 94 (1,5 %) | −5,91 kW |
| HUDN y CESMAG | 0 % | 0 | — |

La escalera es monótona y explica sola el fenómeno del capítulo: a 73,8 %
el flujo se invierte una cuarta parte del tiempo, a 21,3 % y 11,7 %
ocasionalmente, a cero nunca.

**Una explicación que engañaba.** El pie del diagrama decía que el neto
parcial «netea un solo inversor de peso menor frente a la carga». La
primera mitad es cierta pero desorienta: Mariana y la UCC **solo tienen un
inversor cada una**, de modo que no es un neteo parcial de su parque sino
un neteo completo de un parque pequeño. Lo parcial no es el alcance sino
el efecto.

**Y una afirmación que sobraba.** El capítulo decía que los medidores «se
clasifican en tres tipos, y esa clasificación gobierna todo lo que sigue».
Lo que gobierna es binario.

**Su precisión, que cambió la redacción.** Advirtió que en Udenar hay tres
inversores porque hacen falta para reconstruir a lo largo del horizonte, y
no porque tener tres lo haga distinto. Es exacto, y el tercero entra solo
desde septiembre. El número de inversores queda por tanto como dato de
reproducibilidad y **se dice explícitamente que no explica la gradación**.

**Lo aplicado.** La afirmación de los tres tipos pasa a decir que el
tratamiento se bifurca en dos y que el caso intermedio se distingue por el
grado. El pie del diagrama se corrige. La Tabla de los tipos **gana la
columna de la fracción**, que es la cantidad que la ordena y que no estaba
en ninguna parte del documento, y su pie lo declara. El párrafo del reparto
se reescribe alrededor de esa fracción en vez de alrededor del recuento de
inversores, y gana un párrafo que desactiva la lectura causal del recuento.

**Nota de forma.** La columna de inversores pasa de palabras a cifras, que
es lo que corresponde en una columna numérica alineada a la derecha; la
norma RAE de escribir de 0 a 9 en palabras rige la prosa, no las tablas. La
cabecera va a dos líneas y el cuerpo a cuerpo menor porque la sexta columna
desbordaba la caja por 8,8 puntos.

---

## C-69 · La gradación del neteo, dibujada como forma

**2026-08-27 · tipo: `figura` · aplicada**

Él pidió una figura para el pasaje de la gradación. El diseño lo exploró un
agente aislado con el aviso de que en esa misma subsección ya viven un
diagrama de topología y una tabla, y de que la subsección siguiente ya
dibuja el mecanismo para Udenar.

**El hueco que sí existía.** La tabla da la gradación en números y el
diagrama da su causa en topología, pero **ninguno la da en forma**: por qué
una fracción del 73,8 % hunde la lectura y una del 11,7 % apenas la roza.

**El corte elegido, y por qué no hay día de ejemplo.** Curvas de duración,
es decir, las lecturas de cada medidor ordenadas de la mayor a la menor.
El motivo es severo: el fenómeno ocupa el 24,7 % de las horas de Udenar
pero el 3,5 % de las de Mariana y el 1,5 % de las de la UCC, de modo que
cualquier día concreto o no lo muestra o lo sobrerrepresenta, que es
exactamente la trampa que C-65 documentó con el promedio. La curva de
duración es el único corte donde un suceso del 25 %, uno del 3,5 % y uno
del 1,5 % conviven sin elegir ejemplo.

**Lo que la figura enseña**, y está verificado: los tres cruces por cero
llegan en el orden que la fracción predice, al 74,9 %, al 96,5 % y al
98,4 % del recorrido, y las dos instituciones sin generación detrás no
cruzan nunca. El HUDN ni se acerca, con un piso de 6,12 kW, y CESMAG llega
a rozar el cero en su hora de carga mínima, 0,195 kW, **sin cruzarlo
jamás**. Ese último es el control del experimento: ni la carga más baja
invierte un flujo que no tiene generación detrás.

**Dos diseños descartados con medición, no con gusto.** Uno enfrentaba la
campana solar a la carga en tres paneles, pero el promedio de generación
solo cruza al de demanda en Udenar, de manera que habría enseñado «aquí no
se invierte» en dos casos donde sí se invierte. Otro pintaba un mapa de
días contra horas, cuyo mensaje ya lo da el panel de la campana de la
figura anterior y que además no muestra la profundidad.

**La figura no imprime ni un numeral** de las clases que ya viven en la
tabla y en la prosa. La geometría los lleva y el pie los dice en palabras,
«a tres cuartas partes de su recorrido», «casi al final», con lo que C-64
queda respetada y **ninguna cifra del texto sobra**.

**Siete compuertas** detienen la corrida antes que dibujar un ejemplo
falso, y una de ellas amarra los conteos **a la tabla impresa del
capítulo** y no solo al caché, de modo que un caché regenerado no puede
producir una figura incoherente con la página de al lado.

**Composición.** Dos tirajes de corrección: los rótulos flotantes del panel
ampliado cruzaban las curvas de la UCC y de Mariana, y pasaron a etiqueta
al final de cada curva, que es lo propio de una curva de duración y no
puede chocar con nada.

---

## C-70 · En M3 el fenómeno sí deja huella, heredada

**2026-08-27 · tipo: `dato` · aplicada · hallazgo colateral del diseño**

El capítulo cerraba diciendo que en la frontera M3 la clasificación no hace
falta «porque allí los cinco medidores son brutos y ninguna institución
requiere reconstrucción». Cierto, pero daba a entender que allí el fenómeno
no deja huella, y eso es falso.

**Medido**: la serie de Mariana en M3 se construye escalando la de su
primer medidor, y la razón entre las dos es **exactamente 0,3000 en toda la
serie**, comprobado punto a punto. Hereda por tanto sus mismas **213 horas
negativas**, ya reducidas, con un mínimo de −0,723 kW que es exactamente
0,3 × −2,41. Como en esa frontera está clasificada como bruta y no se
reconstruye nada, el recorte defensivo se las lleva a cero y elimina
**46,72 kWh**, el 0,33 % de su demanda en esa frontera.

Es el mismo recorte que en M1 cuesta 1.013,3 kWh en Udenar, y su signo es
el mismo: subestima la demanda, de modo que apunta en la dirección
restrictiva que la subsección del sesgo reúne.

---

## C-71 · La ecuación hacía pasar por identidad física un supuesto de imputación

**2026-08-31 · tipo: `metodo` · aplicada · dictamen de tres revisores**

Nace de contrastar el capítulo contra una reunión con el asesor. Él
distingue dos maneras de pasar de las muestras de dos minutos a la energía
horaria y llama exacta a la segunda; medido, **en horas completas son la
misma expresión**. Pero su inquietud apuntaba a un sitio real que el
capítulo no cubría: las horas incompletas. La medición está en H-18.

**El defecto de fondo.** La ecuación definía el ancho del rectángulo como
el cociente entre la hora y el número de muestras, y lo glosaba como «el
intervalo que cada muestra representa». Esas dos cosas coinciden solo si
las muestras teselan la hora. En las 835 horas incompletas ese cociente
sale mayor que dos minutos y la muestra sigue representando dos, de modo
que la glosa era literal justo donde la decisión no importa y falsa donde
sí. Peor: la ecuación **aparentaba resolver** la cuestión de la hora
incompleta mientras introducía calladamente una imputación que no
declaraba.

**Y refutaba a un adversario que nadie propone.** El párrafo atacaba fijar
el ancho en una hora, error de factor treinta ya desmentido, y **nunca
nombraba la alternativa real**, que es sumar los rectángulos observados sin
extenderlos. Un revisor que conozca el problema veía que lo esquivábamos.

**Lo aplicado.** La ecuación separa ahora los dos pasos: el ancho queda
fijo en dos minutos, el número de muestras es el que la hora trae, y el
supuesto sobre el tramo no observado se enuncia aparte y se declara como
supuesto. Las dos alternativas se descartan por razones distintas.

**Una cita que hubo que acotar antes de dejarla.** La primera redacción
decía que el relleno con ceros es algo «que el Código de Medida tampoco
admite», como si la norma nos obligara. Comprobado el texto literal, **no
nos obliga**: el artículo 38 se activa «mientras se reparan o reponen los
elementos de los sistemas de medición que se encuentran en falla o hayan
sido hurtados» y sus métodos rigen «para el caso de las fronteras con
reporte al ASIC». Nuestros equipos no son fronteras comerciales y lo que
hay no es un sistema en falla sino un corte de telemetría. Queda citado
como criterio del regulador que apunta en la misma dirección, con su ámbito
declarado. La fuente oficial de la CREG se trunca antes del artículo, de
modo que el texto se tomó del Acuerdo CNO 700 de 2014, que lo transcribe, y
se contrastó contra una segunda fuente independiente.

**El recuadro cambia de prueba.** Antes se apoyaba en que sumar da treinta
veces el contador, que es el adversario fácil. Ahora carga la prueba que
decide: sobre 718 cortes de telemetría el contador avanza 809 kWh, suponer
que el equipo siguió consumiendo predice 812 y suponer energía nula predice
288.

**La decisión se declara donde toca, y es la incómoda.** La subsección de
los sesgos enumeraba cuatro decisiones y cerraba diciendo que ninguna infla
el resultado. **Esta sí lo infla**, entre 0,26 % y 0,55 %. Entra como quinta
y se dice que apunta al revés, con su cota y con la razón por la que no se
elige por su signo. Una sección de conservadurismo que solo enumera
decisiones favorables es menos creíble que una que nombra la única que va
en contra y la acota.

**Tres cifras corregidas.** Las horas incompletas son 835 y no 840, porque
el corte inclusivo del cargador deja entrar una muestra suelta del 16 de
diciembre que el reindexado descarta después. Las 5.810 horas del contraste
son las que tienen lectura de contador en los dos bordes, no las horas
completas del medidor, que son 5.821. Y la mejora del trapecio existe pero
vale 0,01 kWh, de modo que decir que no mejora era impreciso.

---

## C-72 · P-20 aplicada: el umbral de cobertura, como prueba y no como regla

**2026-08-31 · tipo: `metodo` · aplicada · P-20 CERRADA**

El revisor normativo propuso declarar un umbral de completitud, es decir,
considerar válida solo la hora que traiga al menos el \pct{75} de sus
muestras, y sustituir las que no lleguen en vez de estimarlas. Medido, el
umbral **es prácticamente inerte**, y eso decide cómo aplicarlo.

**Lo medido.** Incumplen el umbral **147 horas** del horizonte, el 0,49 %
de las 30.153 horas-institución con dato, repartidas entre 24 y 36 por
institución. De ellas, 61 traen entre 17 y 22 muestras y solo 2 traen una
sola. Tratarlas como huecos y rellenarlas con las reglas de la etapa de
limpieza, en vez de estimarlas con la media de lo observado, mueve la
demanda comunitaria en **65,6 kWh sobre 254.949, es decir el 0,026 %**. Por
institución: Udenar −0,417 %, CESMAG −0,035 %, UCC −0,008 %, Mariana
−0,004 % y el HUDN −0,000 %.

**Por qué NO se cambia el pipeline.** Aplicar el umbral dentro de
`data/preprocessing.py` alteraría el valor de esas 147 horas y, con él, la
serie que consume el modelo. Eso invalidaría el canon congelado, las
figuras publicadas, la tesis, el artículo y los informes mensuales ya
firmados, y obligaría a rehacer la corrida completa y el análisis de
sensibilidad global. **A cambio de mover el agregado un 0,026 %.** La
proporción entre coste y efecto no lo justifica, y el canon es el contrato
con todo lo que hay aguas abajo.

**Cómo se aplica en esta corrida.** El umbral entra como **prueba de
fragilidad declarada**, con su cifra publicada, porque la corrida canónica
es anterior a la adopción del criterio y rehacerla solo por esto no se
justifica.

**Pero se adopta, y su aplicación queda como deuda, no como descarte.**
Decisión suya del 2026-08-31: el criterio es correcto y debe aplicarse. En
consecuencia deja de ser una sensibilidad y pasa a ser una **declaración de
honestidad metodológica** en el capítulo, que ahora enumera cuatro
elecciones y no tres, y a **P-21** como tarea con su alcance. La diferencia
importa: una sensibilidad medida cierra una pregunta, una deuda declarada
la deja abierta a la vista.

---

## C-73 · Siete marcadores estaban tapados por los rótulos de la figura

**2026-08-31 · tipo: `figura` · aplicada · revisada por revisor de gráficos**

Él señaló que el rótulo de la media tapaba el gráfico, que los duplicados
deberían ir en otro color, que todo eso debería ir a una leyenda, y que la
rejilla y las marcas del eje vertical necesitaban más granularidad. Se pasó
por un revisor profesional antes de implementar, y el dictamen aprobó dos,
recortó uno y **rechazó dos con argumento**.

**El defecto era peor de lo que se veía, y está medido.** Proyectando los
valores del CSV hermano sobre el PNG y contando píxeles del gris de
marcador: **siete puntos ocluidos, seis borrados del todo**. Tres en el
panel del medidor (minutos 34, 48 y 58) y **cuatro en el del inversor**
(44, 46, 48 y 50), que es el panel donde nadie estaba mirando. Verificado
de forma independiente antes de aceptar el dictamen, y comprobado en cero
después de corregir. La opacidad del 88 % de las cajas era justo lo que
hacía el defecto indetectable.

**Rechazado: los duplicados en rojo relleno.** Dos razones independientes.
Un instante duplicado **no tiene un valor distinto**, de modo que
rellenarlo de otro color lo convierte en una segunda serie categórica y
dice algo falso; el anillo hueco es la convención de «este punto,
señalado». Y en escala de grises el relleno rojo y el gris quedan separados
por 29 niveles de 255, indistinguibles en un marcador de 3,7 puntos,
mientras que el anillo sobrevive porque es una diferencia de **geometría**.
Lo que la petición quería de verdad, saber qué significa el anillo, lo da
la leyenda.

**Rechazado: más rejilla.** El trazo conector estaba en un gris a **veinte
niveles** de la rejilla, de modo que añadir rejilla habría enterrado el
dato. El arreglo es el inverso y es el aplicado: oscurecer el conector para
que la rejilla retroceda sola. La jerarquía queda en marcadores 140,
conector 192 y rejilla 224.

**Aprobado con alcance recortado: la leyenda.** Dos entradas y no tres,
solo en el panel del medidor. No se rotula el punto gris a propósito:
rotularlo daría al contexto el mismo peso que al asunto y aplanaría la
figura en dos categorías simétricas, que es el fallo que C-65 nombra. Va
dibujada a mano en el hueco vacío para que el símbolo del duplicado lo
produzca la misma llamada que lo produce en el gráfico.

**Aprobado con alcance recortado: las marcas.** Menores **sin rótulo**,
cada 2,5 kW, 250 W, 5 kW y 2 kW según el panel, y el de la serie del
medidor pasa de tres rótulos a cinco. Leer valores exactos sobre el papel
no es tarea de la figura: para eso está el CSV hermano con seis decimales,
que es justamente para lo que se escribe.

**Y un defecto que nadie había visto.** La flecha de llamada era una curva
roja de 0,8 puntos subiendo dentro de un panel cuyo asunto es una serie
temporal: en blanco y negro **se lee como una serie de datos que no
existe**. Además apuntaba a uno solo de los ocho duplicados. Se borra, y la
leyenda la sustituye sin contradicción.

**De paso.** La línea de la media adelgaza a 1,1 puntos y pasa **por detrás
del dato** al que se refiere; desaparecen las dos notas en cursiva que
repetían lo que el cuerpo ya dice, por C-64 regla 3; y la función queda sin
un solo literal de color, que era una infracción de la norma del proyecto.

**El pie.** Él lo dejó en la frase de identificación y mandó la descripción
banda por banda al Anexo~A. Queda anotado que, así, **nada lleva al lector
desde la figura hasta esa guía**: el anexo cumple función de registro y no
de lectura, salvo que se añada una remisión al pie.

---

## C-74 · Bloques que se conservan en la fuente y no se imprimen

**2026-08-31 · tipo: `tecnico` · aplicada**

Él pidió poder apartar bloques sin que salgan en el compilado. Se instala
el paquete `comment` con dos entornos gemelos, `guardado` para lo que puede
volver y `descartado` para lo que se conserva por trazabilidad, más un
interruptor en el preámbulo que hace visible de una vez todo lo apartado.
Comprobado en las dos direcciones: 82 páginas con el material dentro, 81
sin él.

Es mejor que comentar con el signo de porcentaje: el material queda legible
con su sangrado y este registro puede remitir a él. Primer bloque apartado:
la caja del Capítulo 2 sobre la imposibilidad aritmética del umbral del
10 % con cinco participantes. **Aviso anotado**: ese argumento sostiene
CAL-41/42 y la corrección de una cifra ya firmada en julio, de modo que si
sale del Capítulo 2 conviene comprobar que siga vivo en el capítulo de
escenarios, que es a donde el propio bloque remitía.

---

## C-75 · La figura del horizonte se retira: el Gantt ya la contenía

**2026-09-01 · tipo: `figura` · aplicada · pasó por revisor de gráficos y
por corrector de estilo, y el desenlace no fue de ninguno de los dos**

Él dijo que la figura no le gustaba, que probablemente fuera por la
cantidad de colores en los rótulos del eje vertical, que no se explicaba
sola y que no le parecía hecha bajo un estándar. Se pasó por dos revisores
en paralelo y **los dos dictámenes chocaron**: el de gráficos mandó
sustituirla por una escalera acumulada que contara instituciones, el de
estilo corrigió los textos dando por buena la forma.

**Se probaron cuatro formas y la buena era no tener figura.**

| Forma | Quién la propuso | Por qué cayó |
|---|---|---|
| Catorce filas, una por fuente, rótulos en color de institución | la que había | El eje vertical no llevaba variable |
| Escalera acumulada de instituciones | revisor de gráficos | Él pidió el subcampeón |
| Cinco filas, una por institución | subcampeón del dictamen | «Se entiende aún menos» |
| El Gantt ampliado a la ventana de entrada | yo, siguiendo su encargo de copiar el estilo del capítulo | La ampliación no aportaba al argumento |
| **Ninguna: el argumento va al Gantt** | **él** | **Es la que quedó** |

**Su pregunta era la correcta y desmonta las cuatro anteriores.** La
Figura 2.2 ya llevaba el argumento entero dibujado: la banda del
horizonte, el anillo sobre el inversor del HUDN y la llamada «fija el
inicio». Lo único que la segunda figura añadía era resolver el orden de
las tres entradas de febrero, **y ese orden no interviene en el
argumento**, que depende solo de la última. Era una página entera por una
curiosidad.

El revisor de gráficos había llegado a rozar esta conclusión en su punto
sobre si la figura era necesaria, y se quedó en «sí, pero por poco»
porque valoró la ampliación como un servicio real. Lo era, pero a una
pregunta que nadie hace.

**Qué se hizo para que el Gantt lo sostenga solo.** Su llamada pasa de
«fija el inicio» a «fija el inicio del horizonte», y su pie deja de
describir solo el periodo cubierto para nombrar la banda y el anillo. La
prosa del apartado recoge lo que el anillo decía sin palabras: que la
última en registrar es **un inversor y no un medidor**, porque dentro del
HUDN los dos medidores empiezan la víspera, de modo que lo que faltaba
para completar la comunidad era la generación.

**Lección, y es la segunda vez que aparece en esta sesión.** Antes de
rediseñar una figura hay que mirar a sus hermanas del mismo capítulo. Los
dos revisores trabajaron sobre la figura aislada y los dos vieron defectos
reales, pero ninguno se preguntó si el capítulo ya la contenía. Primero se
perdió una vuelta por no copiar el estilo del capítulo, y luego otra por
no comprobar que la figura vecina ya hacía el trabajo.

**Lo que sobrevive del trabajo, porque eran defectos y no forma:**

1. **«Primer registro» y nunca «entrada en servicio».** El censo da la
   marca de tiempo más antigua hallada en los archivos, que no es la fecha
   de instalación: las fuentes de Udenar empiezan el 1 de enero a las
   00:00:00, que es el borde de la exportación, mientras que Mariana y el
   HUDN traen el escalonamiento de minutos de una instalación real.
2. **Los dos formateadores de fecha crudos** del capítulo, que eran los
   últimos que quedaban, corregidos al pasar por el Gantt.
3. **El gris de las bandas alternas**, que vivía como literal dentro del
   Gantt y pasa a `FONDO_BANDA` en la fuente única.
4. **Dos modos nuevos en la fuente única**, `mes_anio` y `dia_corto`, que
   quedan disponibles aunque la figura que los pidió ya no exista.
5. **El recuento de fuentes**, que es H-19 y es lo más valioso que salió
   de todo esto: el capítulo publicaba 13 cuando 13 es el complemento.
6. **El desfase de seis horas** entre el arranque del horizonte y el
   primer registro del inversor del HUDN, que es H-20 y ahora está dicho
   en la prosa.

**Un fallo mío al implementar**, anotado porque es reincidente:
`ax.grid(axis="x", which="major")` sin `visible` **alterna** el estado, de
modo que apagó la rejilla en vez de encenderla. Se ve solo mirando el
render, no leyendo el código.

**Queda una figura menos en el capítulo 2**, que pasa de cuatro a tres. No
hay renumeración que arrastrar: las dos figuras siguientes del generador
viven en el Anexo~A6 y se numeran por él.
---

## C-76 · La figura de cobertura era una tabla disfrazada de gráfico

**2026-09-01 · tipo: `figura` · aplicada**

Él dijo que tampoco se entendía. El defecto era de codificación y está
medido: **19 de los 20 medidores caben en 1,7 puntos porcentuales**, que
sobre una barra que arranca en cero son 0,07 pulgadas, es decir, cinco
puntos tipográficos. Las barras no podían mostrar esa diferencia, de modo
que toda la información acababa en una columna de cifras al margen y el
gráfico solo servía de soporte.

El propio código lo confesaba sin decirlo: `xlim` hasta 118 y hasta 145
para hacer sitio al texto, y un comentario que explicaba que las cifras
iban alineadas aparte porque «con veinte barras contiguas no hay ningún
hueco donde poner una caja de texto».

**La magnitud pasa a ser el complemento**, las horas que faltan, que van
de 31 a 204. Un factor de siete, que la barra sí dibuja. Y es además la
cantidad que importa, porque es la que alimenta la imputación del
Capítulo~3.

**Y al medirlo apareció algo peor, que es H-21.** La cobertura se
calculaba sobre las 6.144 horas del horizonte completo, de modo que las
dos «excepciones» que el capítulo nombraba no eran fallos de adquisición
sino arranques tardíos. Medidas sobre el periodo en servicio, las 27
fuentes caen entre el 96,7 % y el 98,8 % y no queda excepción alguna. El
texto decía que el Medidor 4 de Udenar bajaba «por una racha larga de
ausencia», y lo que hubo fue una instalación el 29 de abril.

**Dos arreglos de composición.** Los siete inversores se repartían el alto
de los veinte medidores, con lo que sus barras salían tres veces más
gruesas y los dos paneles parecían dos clases de gráfico distintas; ahora
comparten paso y el hueco que queda aloja la nota. Y los avisos de
arranque tardío no caben en línea: medido sobre el render, el área de
datos mide 1,2 pulgadas y 0,8, de modo que un aviso de treinta caracteres
se sale del panel. Se marcan las dos barras con un asterisco.

**De paso**, el gris de lo auxiliar vivía como literal en dos figuras y
con **dos valores distintos**, `#CFCFCF` en una y `#D5D5D5` en la otra.
Pasa a `APAGADO` en la fuente única.

---

## C-77 · Los cierres de capítulo recitaban cifras ya publicadas

**2026-09-01 · tipo: `redaccion` · aplicada · cuatro casos de seis, él eligió**

Él señaló que los dos párrafos del cierre del apartado de cobertura
repetían información y podían compactarse, y pidió que antes se revisara
todo el documento por si el defecto estaba en más sitios, para decidir él
cuáles atacar.

**Se buscó mecánicamente**, con tres sondas: la misma cifra publicada más
de una vez dentro de un mismo apartado, dos oraciones del mismo apartado
con solape léxico por encima del 42 %, y pie de figura cuyas palabras ya
estuvieran en el párrafo anterior. Aparecieron seis candidatos y **un
patrón**: los párrafos de cierre de capítulo, los que empiezan por «En
resumen» o «En síntesis», vuelven a recitar cifras que la tabla, la figura
o un párrafo anterior ya habían publicado.

| Caso | Qué repetía | Decisión |
|---|---|---|
| Cierre del Capítulo 2 | El «superior al 97 %», literal, 20 líneas más arriba | **aplicado**, de 87 a 47 palabras |
| Cierre del Capítulo 4 | El 19,1 % y el 91,2 %, 13 líneas antes | **aplicado**, de 57 a 23 palabras |
| «Tres tipos de medidor», Capítulo 3 | La columna de la tabla: 73,8 %, 21,3 % y 11,7 %, en el mismo orden | **aplicado** |
| Pie de la figura de cobertura | El 57 % de sus palabras estaban en el párrafo anterior | **aplicado**, de 50 a 35 palabras |
| «El precio al que la red vende», Capítulo 5 | El 38,3 % y el 22,0 %, dos veces | no, decisión suya |
| Cierre del Capítulo 5 | La banda de \uni{182.5}{} a \uni{792.06}{COP/kWh} | no, decisión suya |

**El caso del Capítulo 3 no se compacta, se sustituye.** La prosa recitaba
tres cifras que la tabla ya daba, y en su lugar dice ahora la relación
entre ellas, que la tabla no da: Udenar encabeza la columna, y en Mariana
la fracción es más de tres veces menor y en la UCC más de seis. El
argumento del apartado es que la diferencia es de grado, y una relación lo
sostiene mejor que tres valores absolutos.

**El cierre del Capítulo 4 desaparece entero.** Enunciaba una regla que el
párrafo inmediatamente anterior ya enuncia con más detalle, de modo que
solo queda la bisagra hacia el capítulo de precios.

**Uno de los seis era mío y de esta misma sesión**, el pie de la figura de
cobertura: al hacer explícito el denominador a petición suya, quedó dicho
tres veces, en el párrafo, en el pie y en la nota de dentro de la figura.
El pie se queda solo con lo que el cuerpo no dice, que las dos clases de
equipo se miden sobre bases distintas.

**Dos falsos positivos que conviene no volver a perseguir.** Los solapes
del 100 % entre líneas de `\fuente{}` son la convención de atribución, no
un defecto. Y el \num{6031} del Anexo~A6 aparece en dos tablas donde
significa cosas distintas.

**Los dos párrafos que originaron la revisión** pasan de 186 a 132
palabras. Se les quitó la contraposición entre periodo en servicio y
horizonte completo, que ya estaba en el párrafo de entrada y en el pie; el
98,7 % y el 97,7 %, que quedan subsumidos en el rango que viene dos líneas
después; los «25 días», que el lector calcula con el 4 de abril que acaba
de leer; y la frase sobre el papel del Inversor MTE, que ya está en el
apartado del horizonte y además la rotula la propia figura.

---

## C-78 · El apartado de la energía horaria estaba escrito al revés

**2026-09-01 · tipo: `contenido` · aplicada · tres agentes en paralelo**

Él dijo que el apartado no se entiende, que tampoco queda claro lo que su
asesor propuso, y planteó su propia objeción: **que calcular la energía con
los tramos de dos minutos es más preciso que promediar las treinta
muestras**. Se despacharon tres frentes: la transcripción de la reunión, el
código y el dato, y la referencia normativa.

**El defecto de fondo es el orden.** El apartado presentaba la media como
el método y la integral como justificación, cuando es al revés. La energía
**es** la integral; lo que autoriza a calcularla como una media es que el
paso de muestreo sea uniforme. Escrito en ese orden, la objeción se
disuelve sola, y por eso el apartado no se entendía: pedía aceptar como
decisión lo que es una identidad.

**Su objeción es correcta en la formulación y no cambia el número.**
Medido: el paso vale exactamente 2,0000 minutos en el 99,69 % al 99,91 %
de los intervalos, sobre 1.117.638 registros de cuatro medidores. Con paso
uniforme, la suma de los tramos y la media por la duración son la misma
expresión. Contrastadas contra el contador del propio equipo sobre 8.380
horas completas, las dos dan **el mismo error absoluto medio hasta la
cuarta cifra**. Y sobre la hora del ejemplo coinciden hasta el último
dígito: 30,493333 kWh las dos.

**El asesor propuso exactamente eso, y lo dijo en 108 segundos.** Cita
literal: «cada dato de potencia / multiplicarlo por el delta t»; «es una
sumatoria / de la potencia / por lo que valen dos minutos en horas»;
«sumas todos esos / **y eso te da ahí sí la integral**». Y calificó al
método que se le mostró: «sacamos la media de toda la hora y ya tenemos el
kilovatio / que es aproximado / **pero no es exacto**». Tres cosas que
**no** dijo, y que por tanto no se le pueden atribuir: nada sobre la hora
incompleta, nada sobre los contadores de energía del medidor, y ninguna
cifra.

**Dos figuras nuevas.** La primera dibuja las treinta lecturas como
rectángulos de dos minutos y encima el rectángulo único de la hora a la
altura de la media: la misma área, el mismo número. La segunda lleva el
asunto al único punto donde sí hay que decidir, con una hora real de 18
muestras cuya media da 8,98 kWh contra los 9,00 kWh que marcó el contador,
mientras que truncar daría 5,39; y con el agregado sobre las 384 horas
incompletas de los tres medidores con contador fiable, donde la media
queda al −0,2 % del contador y truncar al −7,1 %.

**Un error mío, y es el mismo que el texto inducía.** Al medir el
contraste del contador obtuve −0,367 % donde el documento publica 0,04 %, y
llegué a reportarlo como discrepancia. La causa: comparé una serie de
potencia **neta con signo** contra un contador de **importada sola**. Los
371 kWh que la UCC exporta explican la diferencia entera. La cifra
publicada es correcta. El texto lo inducía porque decía «sus propios
contadores de energía importada y exportada» y nunca decía que el contraste
usa **la diferencia**; ahora lo dice, en una nota de figura.

**Y por el mismo error dije que el contador de Udenar estaba mal
escalado.** Su ×0,393 era exportación: 16.084 kWh en 1.461 horas de media
negativa. Compuesto en neto vale 0,998. Los tres genuinamente mal escalados
son Mariana M1, HUDN M3 y Cesmag, y los tres coinciden con su razón de
transformadores.

**La cita normativa: verificada, y mejorada.** El artículo 38 se comprobó
por dos vías independientes que coinciden palabra por palabra, porque la
fuente oficial de la CREG se trunca en el artículo 28. Tres arreglos. El
ámbito pasa de «fronteras comerciales» a **las que reportan al ASIC**, que
es a quienes rigen esos dos medios. El «no contempla asignarles cero», que
era un argumento de silencio presentado como hecho, pasa a «**ninguno de
los medios que enumera consiste en asignar cero**», que dice lo mismo y se
comprueba leyendo la lista. Y se incorpora la segunda rama del artículo,
que para las fronteras sin reporte al ASIC remite al artículo 31 de la
Resolución CREG 108 de 1997 y ordena estimar **por consumos promedios del
mismo usuario**: es literalmente nuestro método, y era mejor analogía que
la que se estaba usando.

**C-71 no se había propagado.** La subsección de sesgos seguía diciendo que
truncar «está descartado por el Código de Medida», es decir, en forma de
obligación, ciento treinta líneas después de que el capítulo dijera que la
norma no rige aquí. Corregido.

**Dos cantidades que se confundían.** Las 835 horas incompletas
**contienen** 8.100 kWh, el 3,2 % de la demanda, pero lo que el supuesto
**imputa** es solo el tramo que falta: 1.054 kWh, el 0,41 %. Un factor de
ocho. Se añade la razón: el 55,6 % de esas horas pierde una sola muestra de
las treinta y el 77 % pierde cuatro o menos.

---

## C-79 · Cuatro pasajes que no se entendían, y el apartado partido en tres

**2026-09-01 · tipo: `redaccion` · aplicada · él señaló los cuatro**

Después de C-78 él fue señalando, uno a uno, los pasajes del apartado que
seguían sin entenderse. Los cuatro tenían defectos distintos y ninguno era
de contenido, de modo que quedan aquí como catálogo de lo que hay que
evitar.

**1. El texto hablando de sí mismo.** «Es importante derivarlo en el orden
correcto, porque el inverso hace parecer una decisión lo que es una
identidad» era una nota mía sobre cómo está escrito el párrafo, colada en
el párrafo. Le pedía al lector que se fijara en el orden de la exposición
cuando lo que quiere saber es cómo se calcula la energía, y encima era
elíptica dos veces: «derivarlo» no decía qué y «el inverso» obligaba a
reconstruir cuál. Pasa a decir la afirmación de frente: **la media no es
una elección de método, sale de la definición de energía**.

**2. El acertijo.** «La alternativa es detenerse en los rectángulos
observados, y no consiste en abstenerse de suponer nada, como podría
parecer, sino en suponer que...» decía en forma de doble negación con
concesión dentro algo sencillo. Y remataba con «el único árbitro
disponible», que nombra un objeto que el lector todavía no sabe cuál es.
Pasa a: **contar solo los minutos medidos y no añadir nada por los que
faltan**, y el árbitro se nombra donde se le pide que arbitre.

**3. El hombre de paja.** «Conceder una hora entera a cada lectura de dos
minutos devuelve un valor treinta veces mayor» presentaba como alternativa
descartada lo que es un error de implementación que nadie plantea. Fuera, y
con él el «las dos alternativas quedan descartadas por razones distintas»
que lo sostenía. Alternativa de verdad solo hay una.

**4. El sujeto colgando.** «No obliga a este trabajo, porque estos equipos
son instrumentación de investigación...» venía detrás de una frase que
termina en «el criterio que aquí se aplica», de modo que se leía como si
fuera el criterio el que no obliga; el tono se volvía defensivo de golpe; y
«pero apunta en la misma dirección» repetía lo que la primera frase ya
decía. Pasa a **«Rige sobre fronteras comerciales y no sobre
instrumentación de investigación como esta, de modo que se invoca como
criterio y no como obligación»**, con el sujeto expreso y la consecuencia
ligada por una causa.

**5. Tres casos en prosa corrida.** Los tres casos que una hora puede traer
iban en un párrafo con las cifras intercaladas, y se abrían con un «conviene
enunciar» que es el defecto 1 otra vez. Pasan a lista con el formato que el
capítulo ya usa dos veces, y «el segundo caso», que obligaba a volver a
contar, pasa a «la segunda» justo debajo de la lista.

**El apartado se parte en tres.** Sostenía tres figuras y cuatro temas,
contra la regla del documento de una idea, una subsección, una figura.
Queda en «Del archivo a la serie horaria», que se lleva los duplicados, las
unidades y las salvaguardas; «La energía de la hora»; y «La hora
incompleta». Las unidades y las salvaguardas suben desde el final porque
hablan de leer el archivo y no de integrar, y el remite al anexo baja al
cierre porque el anexo cubre la etapa entera.

**Y el aparato normativo baja al anexo.** El párrafo de la CREG cargaba
tres artículos de dos resoluciones y dos ramas en una sola oración de 116
palabras. El cuerpo se queda con la afirmación, en 86 palabras, y el
articulado, su alcance y la nota de que la publicación oficial se trunca en
el artículo 28 quedan en `sub:repro-norma`.

---

## C-80 · Auditoría del apartado contra el código

**2026-09-01 · tipo: `dato` · aplicada · a petición suya**

Él pidió que todo lo que el capítulo afirma se corresponda con lo que el
código hace. Se comprobó frase por frase contra `data/preprocessing.py` y
`data/xm_data_loader.py`. Salieron tres cosas.

**Las cifras de duplicados eran sobre el archivo completo, no sobre el
horizonte, y el texto no lo decía.** Dentro del horizonte son 27 y 29, no
3.099 y 3.622. La cifra del archivo completo es la correcta para describir
la operación, porque el cargador funde antes de recortar, pero el lector
asume el horizonte, que es sobre lo que va todo lo demás del capítulo.
Ahora se dice cuál es cuál.

**Las cifras publicadas no eran las que mide el dato de hoy.** Medidas
sobre los diez medidores que el modelo lee, son \num{3108} en la frontera
principal y \num{3588} en la secundaria, con \num{6696} en total, contra
3.099, 3.622 y 6.721.

**Casi todos los duplicados son de un solo equipo**, y eso no se decía:
\num{3073} de los \num{3108} de la frontera principal son del medidor de
la UCC, y en las otras cuatro instituciones no pasan de 30 apariciones en
todo el archivo. Es la razón de que el ejemplo de la figura sea de la UCC.

**Lo verificado y confirmado**: que las lecturas duplicadas coinciden hasta
el último dígito, cero discrepantes de \num{6696}; el remuestreo por media;
las 835 horas incompletas y las 567 vacías; el relleno de la etapa de
limpieza; la división entre mil solo para el inversor; y que ninguna línea
del cargador consulta el número de muestras de la hora.

**Una discrepancia viva, que es decisión suya.** El apartado abre diciendo
que «la primera etapa no interviene sobre el valor medido», y cuando dos
archivos del mismo medidor comparten un instante el código los **suma**.
Son 5 instantes por frontera. Está registrado como P-17 pero no se dice en
este apartado: o se declara aquí o se corrige el cargador.

---

## C-81 · El instante repetido gana figura, y una cifra se cae al medirla

**2026-09-03 · tipo: `figura` y `dato` · aplicada · figura encargada a un
agente con todo el material de estilo cargado**

Él pidió una figura detallada para ver mejor las estadísticas de los
instantes repetidos. Se despachó con las reglas de figuras y de claridad,
las cuatro reglas permanentes, la norma de cifras, el perfil de escritura,
`estilo.py` y las siete entradas de este registro que son jurisprudencia
sobre figuras. Las cifras publicadas se le dieron **como compuerta**, con
orden de detenerse si su código no las reproducía.

**Y una no reprodujo.** El texto decía que dentro del horizonte «solo
quedan 27 en la frontera principal y **29** en la secundaria». Los 29 no
son instantes sino **lecturas de más**: dos instantes de dentro del
horizonte traen tres lecturas y no dos, de modo que 27 instantes producen
29 sobrantes. La frase habla de instantes, luego son **27 en las dos
fronteras**. En la principal las dos cuentas coinciden en 27, que es la
razón de que el defecto pasara desapercibido.

**El error es mío y estaba en mi propia medición.** La salida que produje al
auditar el apartado imprimía las dos columnas, «lecturas de más 29» e
«instantes con copia 27», y reporté la primera como si fuera la segunda.
Sobre el archivo completo las dos cuentas se separan mucho más, 6.796 y
11.609 lecturas de más contra 3.108 y 3.588 instantes, de modo que esas dos
cifras sí eran instantes y el enunciado mezclaba dos unidades en la misma
frase.

**Tres hechos, tres formas.** La figura los enseña a la vez y cada uno pide
una codificación distinta.

1. **Cuándo ocurren**, con una curva acumulada por frontera. Es lo más
   revelador y no estaba en ninguna parte: la curva va plana durante todo
   el horizonte y **salta a 100 % en marzo de 2026**, tres meses después de
   que el horizonte cierre. Se descartó la barra mensual lineal porque los
   meses del horizonte medirían menos de un punto tipográfico, que es el
   defecto que C-76 documentó.
2. **Un carril de días** debajo, porque la curva dice cuánto y no cuándo, y
   los 27 de dentro son escalones invisibles. La distinción dentro y fuera
   **no la lleva el color sino la geometría**, marca del doble de alto,
   porque en escala de grises el acento y el gris quedan a 29 niveles.
3. **De qué equipo son**, con puntos en escala logarítmica y **no barras**:
   la longitud de una barra logarítmica depende de dónde se ponga el
   origen, de modo que miente sobre la razón entre dos valores. La frontera
   se distingue además por forma de marca, para que sobreviva impresa.

El cero discrepante de 6.696 va como cifra y no como gráfico, porque una
barra de altura cero no dice nada.

**Dos hallazgos que la figura destapó.** Cinco de los 27 no son de ningún
medidor en particular: son **la costura entre archivos**. El instante del 1
de junio a las 00:00 está repetido en las cinco instituciones y en las dos
fronteras, que es exactamente el suceso que P-17 describe. Los otros 22 son
de la UCC. Y los 27 **viven en ocho días sueltos**, con multiplicidad de
hasta 73 lecturas en un mismo instante en el Medidor 3 de la UCC.

**Subsección propia.** Los tres párrafos pasan a «El instante que llega
repetido», porque la subsección anterior ya sostenía la Figura~3.1 y tres
asuntos, y colgarle una segunda figura repetía el defecto que C-79 acababa
de corregir partiéndola en tres.

---

## C-82 · Pasada de claridad sobre los cuatro capítulos redactados

**2026-09-03 · tipo: `redaccion` · aplicada · él fijó el criterio**

Él pidió aplicar el criterio de C-79 a los capítulos 2 y 3 y después a los
4 y 5, y nombró el hábito que quería fuera: **«lo de conviene»**. Se
construyó un detector de los cinco defectos que él había ido señalando y se
pasó sobre los cuatro capítulos.

**Fuera los 24 «conviene»** de los cuatro capítulos. Casi todos eran
anuncios de propósito o el texto hablando de sí mismo: «conviene decir con
precisión qué son», «conviene subrayar cuánto se descarta», «conviene
distinguir dos papeles del inversor», «conviene nombrarla aquí y no
esconderla». Cada uno pasa a decir su afirmación de frente. Cayó también el
último «es importante delimitar el alcance», que era el mismo movimiento
con otras palabras, y el «Aquí empieza la parte interesante» que abría la
subsección de la lectura negativa.

**Dos cuentas anunciadas que iban en prosa pasan a lista.** Los cuatro
tratamientos de la limpieza, que se narraban «Primero… Segundo… Tercero… Y
cuarto…», y las cuatro salvaguardas, que iban juntas con puntos y coma y
obligaban al lector a hacer la aritmética para encontrar cuatro. Las
salvaguardas quedan además separadas de verdad, porque fechas ilegibles y
valores no numéricos eran dos y se contaban como una.

**Una ambigüedad que él detectó.** «La demanda tal como llega del medidor»
admitía dos lecturas, las muestras crudas de dos minutos o la serie horaria
que sale de la primera etapa. Comprobado en el generador: la figura dibuja
la salida de la primera etapa. Ahora lo dice.

**Y otra.** «La rellena desde las horas vecinas» comprimía dos operaciones
que no hacen lo mismo, interpolar entre las horas de los dos lados y copiar
el valor de la más próxima. Se nombran las dos. De paso se corrigió una
mezcla de «tres horas» en palabras con «24 horas» en cifras dentro de la
misma serie.

**Los cuatro capítulos quedan sin un solo META, LISTA ni PAJA** en el
detector. Los cuatro «no es X sino Y» que sobreviven son contrastes cortos
y legítimos, que sí están en su registro.

---

## C-83 · El capítulo 3 se puede seguir contra el mapa del pipeline

**2026-09-03 · tipo: `estructura` · aplicada**

Él dijo que la figura del pipeline define seis etapas, que al principio el
capítulo las va tratando y que más adelante se pierde, sin saber en qué
punto va ni si ya terminaron. Tenía razón, y por tres causas.

**Los títulos dejaban de sonar a la figura.** Al principio coinciden
palabra por palabra y a partir de la etapa 2 se despegan: la figura dice
«Clasificar el medidor» y el título decía «Tres tipos de medidor»; la
figura dice «Ensamblar y verificar» y el título decía «El resultado».
Los dos vuelven a nombrar su etapa.

**Faltaba el mapa.** Un párrafo al cierre de la subsección del pipeline
dice ahora cómo se reparten las seis etapas en lo que sigue y avisa de
dónde el capítulo deja de describir etapas y pasa a leer el resultado. Ese
aviso importa: después de la última etapa quedan cuatro subsecciones que ya
no son etapas, y quien siga contando se desorienta.

**Y la etapa 6 no se trataba nunca**, de modo que quien contara no llegaba
a seis. Es P-18, ahora cerrada. Antes de escribirla se comprobó la
suposición que encierra, porque de ella dependen dos argumentos del
capítulo: **el máximo de generación cae entre las 11 y las 12 en las cinco
instituciones**, que es el mediodía solar de Pasto, y no entre las 16 y las
17 como aparecería si las marcas vinieran en tiempo universal. En el código
es `tz_localize` y no `tz_convert`, es decir, da por hecho que las marcas ya
vienen en hora local en vez de convertirlas. La subsección deja dicho de
qué depende eso y que las dos salvaguardas de horario de verano nunca
actúan, porque Colombia no lo aplica.

---

## C-84 · La curva de duración se retira; la gradación pasa a la profundidad de la lectura

**2026-09-03 · tipo: `figura` · aplicada · medida sobre el render anterior**

Él dijo de la figura de la gradación que «no se entiende nada». El defecto
tenía tres causas y las tres están medidas sobre el PNG que había.

**1. El eje horizontal no era una magnitud sino un orden.** Dibujaba las
lecturas de cada medidor ordenadas de la mayor a la menor y ponía debajo el
percentil de horas, es decir, la posición dentro de esa ordenación. El
lector llega a esa página desde la figura de la demanda negativa, cuyo eje
horizontal es la hora del día, y nada anunciaba el cambio de marco. Las dos
figuras se parecen en forma, curvas de kilovatios sobre un eje que corre de
izquierda a derecha, y significan cosas distintas.

**2. La codificación no podía dibujar lo que la figura afirmaba.** Medido
sobre el render: el 80 % de las lecturas de las cinco instituciones, de
2,73 a 15,08 kW, cabía en 0,22 pulgadas del panel izquierdo, que son 15
puntos tipográficos de sus 1,85 pulgadas de alto, es decir el 12 % del
panel, y ahí se repartían cinco curvas de 1,6 puntos de grosor. El
recorrido entero del HUDN entre sus percentiles 5 y 95 medía 0,06
pulgadas, cuatro puntos. En el panel ampliado, los cruces del cero de
Mariana y de la UCC quedaban a 1,97 puntos porcentuales, que son 9,6
puntos tipográficos, con un marcador de 4,5: los dos casos intermedios,
que son justamente los que la subsección llama neto parcial, no se podían
separar. Es el defecto que C-65 nombró con cinco series apiladas en una
banda estrecha y que C-76 midió con las barras de cobertura, reaparecido.

**3. Un borde del marco se leía como dato.** El panel ampliado llegaba
hasta 113 con los datos acabados en 100, de modo que el 30 % de su ancho
era sitio para rótulos, y la banda de la zona imposible estaba recortada
justo en 100. Esa arista vertical caía encima de la caída final de la UCC y
de CESMAG, y no había manera de saber cuál de las dos verticales era la
lectura.

**Se consideró retirarla, que es lo que hizo C-75 con la figura del
horizonte, y no procede.** La tabla de los tipos publica el conteo de horas
bajo cero y el mínimo, y el mínimo es un extremo. No dice a qué profundidad
se invierte el flujo de ordinario, y la diferencia es grande: la mitad
central de las lecturas negativas de Udenar cae entre −15,1 y −3,9 kW, con
mediana de −8,7 kW, mientras que el mínimo publicado, −33,6 kW, es 3,9
veces esa mediana. En Mariana la mediana de las negativas es −0,59 kW y en
la UCC −1,94 kW. Eso no está en ninguna otra parte del documento.

**Lo aplicado.** Un solo panel, una fila por institución en el orden fijo,
y una sola magnitud en el eje horizontal, los kilovatios, que es la misma
del eje vertical de las dos figuras vecinas: el marco no cambia, solo gira.
Cada fila lleva tres marcas, la lectura mediana del medidor, el recorrido
desde esa mediana hasta su lectura más baja, y la mitad central de sus
lecturas negativas cuando las tiene. La comparación entre las dos
longitudes de un mismo renglón, lo que el medidor marca de ordinario frente
a hasta dónde desciende, es la gradación. El tipo que la subsección asigna
a cada medidor va en una segunda columna de rótulos a la derecha, fuera del
área de dato, para que quede al lado de la geometría que lo justifica.

**La identidad de cada fila la llevan su rótulo y su posición, no el
color.** Comprobado convirtiendo el PNG a escala de grises: no se pierde
ninguna distinción.

**Lo que la figura no dice, y por qué.** Los conteos de horas. Los da la
tabla, y C-65 los retiró de la figura vecina por ese mismo motivo. El pie
remite a ella, porque una profundidad sin su frecuencia se lee mal.

**Dos rótulos rechazados en el propio render.** El que daba la mediana de
las lecturas negativas de Udenar dentro del panel: la prueba de oclusión lo
cazó tapando su caja, y arriba de la primera fila no cabe una línea de
texto. Va al pie y al CSV hermano, que es donde C-73 dejó dicho que van los
valores exactos. Y el que decía «roza el cero» sobre la fila de CESMAG:
quedaba en el mismo renglón que la columna de tipos y las dos cosas se
leían como una sola línea. La marca del mínimo puesta sobre la línea del
cero lo dice sin palabras.

**Dos defectos del código que se retira.** Una comprobación anulada,
`assert ... or True`, que no comprobaba nada desde que se escribió. Y el
CSV hermano, que pesaba 885 kB con las cinco curvas enteras, unas 30.000
filas; el nuevo tiene cinco filas, una por institución.

**Un fallo mío al implementar, anotado porque es de la misma familia que el
de C-75.** La prueba de oclusión tomaba la caja en pantalla de cada artista
con `get_window_extent`, y la de una colección de líneas no es fiable:
devolvía una caja que no correspondía a la marca, de modo que la prueba
fallaba sobre un objeto equivocado. Ahora las marcas se registran en
coordenadas de dato y se llevan a pantalla con la transformación del eje.

**Queda por aplicar en la fuente del capítulo**, que no se toca aquí: el
nombre de archivo pasa de `f3_02b_gradacion_m1` a `f3_02b_profundidad_m1`,
y el pie, la nota y la frase que presenta la figura cambian con él. Ver
P-24.

---

## C-85 · La tabla de los tipos deja de comparar peras con manzanas

**2026-09-03 · tipo: `dato` · aplicada · él planteó la objeción**

Él señaló que la razón del \pct{73.8} suma **tres inversores para Udenar y
uno para las demás**, dentro de una columna cuyo propósito es comparar
instituciones, y que la columna de inversores induce a leer que Udenar
aporta tres al modelo. Lo segundo es falso: el modelo usa uno por
institución, y los tres son los que inyectan entre ese medidor y su carga.

**Cambiar la razón a un inversor por entidad no era la salida, y está
medido.** Con ese criterio el HUDN sale al \pct{23.6} y CESMAG al
\pct{25.1}, **por encima de Mariana y de la UCC, y ninguno de los dos tiene
una sola hora negativa**. La columna dejaría de explicar nada, porque sus
inversores existen pero inyectan fuera del tramo que ese medidor vigila.

**La salida es que la tabla no lleve razón ninguna.** Todo lo que necesita
se lee directamente sobre la serie que el medidor entrega, sin reconstruir
nada: horas bajo cero, la fracción que representan sobre sus horas con
dato, la lectura mínima y la energía que salió del circuito hacia la red.

| | Horas bajo cero | Sobre sus horas | Lectura mínima | Energía hacia la red |
|---|---:|---:|---:|---:|
| Udenar | 1.517 | 25,1 % | −33,57 kW | **15.348 kWh** |
| Mariana | 213 | 3,5 % | −2,41 kW | 156 kWh |
| UCC | 94 | 1,6 % | −5,91 kW | 200 kWh |
| HUDN | 0 | 0 % | +6,12 kW | 0 |
| CESMAG | 0 | 0 % | +0,20 kW | 0 |

La última columna zanja el asunto sin cocientes: **un factor de cien entre
Udenar y las otras dos**. Y el mínimo del HUDN y de CESMAG entra en la
tabla en vez de una raya, de modo que el **+0,20 kW de CESMAG dice por sí
solo que su circuito roza el cero sin cruzarlo**, que era lo que la figura
de la gradación intentaba enseñar.

La explicación deja de ser una cantidad y pasa a ser la posición: si la
generación entra entre el medidor y la carga, el medidor no la ve llegar;
si entra del lado de la red, la ve pasar. Eso lo dibuja la figura de los dos
casos y no necesita ningún número.

**Se retira el párrafo de los tres inversores**, que defendía contra una
lectura que la columna retirada inducía y cuyos hechos están dichos en la
subsección de la reconstrucción y en el Capítulo~2.

---

## C-86 · Tres pasos del cargador que el capítulo no contaba

**2026-09-03 · tipo: `contenido` · dos aplicados, uno pendiente de decisión**

Él pidió comprobar que el documento describa a detalle el proceso que el
código ejecuta. Se recorrió el camino entero, de la fila del CSV a la
matriz que el modelo recibe. **El capítulo lo describe bien salvo en tres
puntos, y los tres son del lado del documento: ninguno exige tocar el
código canónico.**

**1. La generación que falta se pone a cero antes de la limpieza.** El
cargador aplica `fillna(0)` sobre la generación antes de llamar a la etapa
de limpieza, de modo que **los pasos de interpolación y de arrastre no
llegan a actuar nunca sobre ella**, aunque el capítulo describa la cascada
como si se aplicara igual a la demanda y a la generación. Medido: de las
horas vacías de generación, unas \num{12700} son de noche y ponerlas a cero
es correcto, pero **\num{285} son de sol**, y ahí lo que hubo fue una avería
de registro y la serie dice que no se generó nada. Como recorta generación,
recorta mercado: entra como **sexta decisión que sesga en contra**, y el
recuento de esa subsección pasa de cinco a seis.

**2. La demanda que falta se pone a cero antes de devolverle la
generación.** Una hora sin lectura de medidor pero con lectura de inversor
sale con demanda igual a la generación devuelta. Ocurre en **7 horas del
horizonte, todas de Udenar, y suma \uni{34.1}{kWh}**. Inmaterial, pero es
un valor construido y ahora se declara en la subsección de la
reconstrucción.

**3. El solape entre archivos se suma, y sigue sin declararse.** Es P-17,
registrado desde hace tiempo: cuando dos tramos del mismo medidor comparten
un instante, el cargador los suma en vez de fundirlos. Son 5 instantes por
frontera y contradice la frase que abre la etapa 1, «no interviene sobre el
valor medido». **Queda pendiente de su decisión**: declararlo en el
capítulo o corregir el cargador.

**De paso.** El exponente $+$ de la ecuación de la reconstrucción estaba
definido, pero como símbolo y sin decir para qué hace falta. Ahora se nombra
en palabras y remite a la subsección que mide el exceso que obliga a
recortar.


---

## C-87 · Los tramos solapados se funden, no se suman

**2026-09-03 · tipo: `código` · aplicada**

Cierra P-17. En `data/preprocessing.py` la composición de los tramos de un
mismo medidor pasa de `pd.concat(parts, axis=1).sum(axis=1, min_count=1)` a
`.mean(axis=1)`.

**Por qué es un fallo y no una decisión de método.** Dentro de un archivo
los duplicados ya se fundían promediando. No hay razón para tratar distinto
el solape entre dos archivos del mismo medidor: en los dos casos es el
mismo instante leído dos veces, no dos lecturas que sumar.

**Comprobado equivalente en todo lo demás.** Para un instante presente en un
solo tramo la suma y la media dan idéntico valor, y una fila entera vacía
sigue dando `NaN` con las dos. Solo difieren en la costura, que es el caso
que estaba mal.

**Efecto medido.** La demanda comunitaria pasa de 254.949,9 a 254.948,7 kWh:
1,2 kWh, el 0,0005 %. **Ninguna cifra publicada cambia**, porque las dos
redondean a 254.949.

**Estado del canon.** El código queda por delante del canon hasta la próxima
corrida. La caché de preproceso NO se regeneró a propósito, para que el
canon vigente siga siendo reproducible mientras tanto.

---

## C-88 · Los tres inversores de Udenar, justificados por el dato

**2026-09-03 · tipo: `contenido` · aplicada**

Él preguntó dos cosas sobre la ecuación de reconstrucción: si el recorte a
cero del exponente `+` llega a actuar alguna vez, y por qué en Udenar la
suma incluye tres inversores, que el capítulo afirmaba sin justificar.

**El recorte actúa.** Medido con el cargador ya corregido: 353 horas y
1.013,3 kWh en Udenar, 6 horas y 0,6 kWh en Mariana, ninguna en la UCC. En
el HUDN y CESMAG, que son brutos, el recorte defensivo no actúa nunca
porque sus lecturas no bajan de cero. El capítulo publicaba las 353 horas
tres subsecciones más adelante, sin decir en la ecuación que el recorte
ocurre y sin mencionar a Mariana. Ahora lo dice en los dos sitios.

**Los tres inversores tienen justificación física y medible.** Un medidor no
puede devolver a la red más energía de la que se genera detrás de él, de
modo que el criterio es cuántas horas siguen saliendo negativas al devolver
los inversores de uno en uno:

| Se devuelve | Horas aún negativas | kWh sin explicar |
|---|---:|---:|
| Fronius 1 | 1.056 | 6.875,1 |
| + Fronius 2 | 527 | 1.472,7 |
| + Inversor MTE | 353 | 1.013,3 |

Con un solo inversor hay 1.056 horas en las que el medidor reporta una
exportación que ningún equipo produjo, lo que es físicamente imposible: la
energía devuelta tuvo que generarse en alguna parte. Cada equipo añadido da
cuenta de una porción de esa devolución, y el residuo con los tres es
exactamente el que la subsección del costo ya analizaba. La carpeta de
Udenar contiene tres inversores instrumentados, de modo que no hay un
cuarto que añadir.

**El inventario no sirve para esto.** `Inventario_Medidores_MTE.xlsx`
cataloga los 20 medidores, no los inversores, así que la justificación
tiene que ser del dato y no documental.


---

## C-89 · Los tres inversores de Udenar: papeles distintos, y el residuo al derecho

**2026-09-03 · tipo: `contenido` · aplicada · sustituye la justificación de C-88**

Él corrigió el supuesto de fondo: los dos Fronius no alimentan los medidores
del proyecto. Están instalados en Udenar y sirven **solo** como referencia
para reconstruir la curva del inversor del MTE hacia atrás, porque ese
equipo entró tarde. **No deben entrar en ningún cálculo por sí mismos.**

**Lo medido, que sostiene su relato.**

| Inversor | Horas con dato | % del horizonte | Primera |
|---|---:|---:|---|
| Fronius 1 | 6.066 | 98,7 % | 2025-04-04 |
| Fronius 2 | 6.066 | 98,7 % | 2025-04-04 |
| Inversor MTE | 1.409 | 22,9 % | **2025-09-03** |

**Y el hallazgo que lo cierra.** Desde que el inversor del proyecto
registra, devolver los tres deja **cero** horas negativas. Las 353 horas
del residuo caen **todas** antes del 3 de septiembre, es decir, en el tramo
que ese inversor no cubre.

**Se retira la justificación de C-88.** Argumentaba que los tres están
físicamente detrás del medidor porque el descenso de horas negativas
(1.056 → 527 → 353) lo exigía. El descenso es real, pero no prueba lo que
se le hacía decir: los dos Fronius pueden estar reduciendo el negativo
sin ser lo que el medidor descontó.

**Corrección de signo, independiente de lo anterior.** El capítulo explicaba
el residuo diciendo que la suma «sobrestima la generación que el medidor
realmente descontó». Es al revés. Como
$D_{\text{recon}} = D_{\text{bruta}} - G_{\text{real}} + \sum G$, el
resultado solo sale negativo si $\sum G < G_{\text{real}}$, es decir, si la
suma **se queda corta**. Si sobrara, el resultado sería más positivo. La
causa correcta es de cobertura, y coincide con lo anterior: antes de
septiembre falta el inversor del proyecto en la suma.


---

## C-90 · La generación que Udenar negocia pasa al inversor del proyecto

**2026-09-03 · tipo: `código` · aplicada · CAL-44 · EXIGE CORRIDA NUEVA**

Cierra H-23. Hasta hoy el modelo negociaba para Udenar la serie del
**Fronius 1**, un equipo ajeno al proyecto, sobre las 6.144 horas. El
inversor del MTE no entraba en ningún cálculo.

**El cambio.** El inversor designado de Udenar pasa a ser el del proyecto.
Como entra en servicio el 3 de septiembre de 2025 y cubre el 22,9 % del
horizonte, las horas que le faltan se extienden desde un inversor de
referencia declarado en `EMS_INVERTER_BACKFILL_CONFIG`, escalado por la
razón de energías del solape. Sobre las 1.409 horas comunes las dos curvas
correlacionan **r = 0,997**, con perfil diario de idéntica forma, y la
razón de energías es **1,2053**.

**Efecto medido.**

| | Antes | Después | |
|---|---:|---:|---|
| Generación de Udenar | 13,2 MWh | 15,9 MWh | +20,5 % |
| Cobertura G/D en M1 | 19,14 % | **19,99 %** | +0,85 pt |
| Cobertura G/D en M3 | 91,20 % | **95,26 %** | +4,07 pt |
| Cobertura propia de Udenar (M1) | 29,8 % | 36,0 % | +6,2 pt |
| Excedente vendible comunitario (M1) | 4,8 MWh | 6,0 MWh | +25 % |
| Excedente vendible comunitario (M3) | 31,9 MWh | 34,4 MWh | +7,8 % |

**Lo que no cambia, comprobado:** la demanda de las dos fronteras
(318.044,8 y 66.733,7 kWh), la generación de las otras cuatro
instituciones (47,6 MWh), la igualdad de $G$ entre fronteras, y la
reconstrucción net→bruta, que sigue devolviendo los tres inversores porque
es lo que el medidor restó.

**Por qué no se tocan los dos usos de los Fronius.** Son preguntas
distintas. Cuál generación negocia la comunidad es una elección, y debe ser
la del proyecto. Cuánto restó el medidor no es una elección: se comprobó
que con un solo inversor quedan 957 horas en que el Medidor 1 exportó más
de lo que ese inversor generó, y que la demanda resultante deja a Udenar en
**cero exacto durante 1.047 horas**, 837 de ellas entre las 9 y las 15, en
199 días de 256. Un campus no consume nada al mediodía en 137 días.

**Contrapartida que hay que declarar.** El 77,1 % del horizonte de la
generación de Udenar pasa a ser reconstruido, no medido: solo 1.409 de
6.144 horas vienen del inversor del proyecto. Se cambia medición del equipo
equivocado por reconstrucción del equipo correcto. Va a la declaración de
honestidad metodológica del Capítulo 3.

**Lo que la corrida debe recalcular en el documento.** Las dos razones de
cobertura, publicadas en la nomenclatura, en las etiquetas de la figura de
cobertura del Capítulo 4, en su nota y en dos pasajes más; la generación
comunitaria (60.860 kWh); el censo de fuentes del Capítulo 2 («5 definen la
generación… los otros 2 solo reconstrucción»), que se invierte; y el
párrafo del arranque del horizonte, que excluía del cómputo el inversor del
proyecto por empezar en septiembre. **Ninguno se toca hasta la corrida:
hoy las cifras publicadas siguen siendo las del canon vigente.**

**Trampa operativa.** Las figuras del documento leen de `datos_cache/preproceso_m{1,3}.npz`, del 21 de agosto, de modo que hoy siguen mostrando el canon. Quien vuelva a correr `cache_crudo.py` arrastrara CAL-44 a las figuras mientras el texto sigue citando cifras viejas. Esa cache se regenera **con** la corrida canonica, no antes.

**De paso.** Tres cifras del encabezado del módulo estaban desfasadas
(Udenar 989 h con demanda negativa, Mariana 216, UCC 112). Medidas hoy:
1.517, 213 y 94. Corregidas.

### Escalado al resto del código (mismo día, a petición suya)

Se revisaron **uno a uno** los nueve puntos del repositorio que tocan la
designación del inversor. Tres exigían adecuación y se aplicaron:

| Archivo | Qué pasaba | Qué se hizo |
|---|---|---|
| `data/xm_data_loader.py` | No exponía la configuración de referencia, de modo que un llamador que sobreescribiera el inversor designado se comía el backfill de Udenar sin poder desactivarlo | Se añade `ems_inverter_backfill_config` y se pasa al pipeline; `None` deja el default, `{}` lo desactiva |
| `scripts/cache_crudo.py` | **Duplicaba** la lógica del pipeline en vez de llamarla, y leía el inversor designado en crudo. Tras CAL-44 habría dado 1.409 horas y ceros en el resto: la caché del documento mostraría una generación que el modelo no usa | Pasa a llamar `_read_ems_generation`, el mismo lector del pipeline, para que no vuelva a desviarse |
| `scripts/cache_fuentes.py` | Etiquetaba cada inversor como EMS o reconstrucción. Faltaba el tercer papel, el de referencia, que es justo el que los Fronius de Udenar pasan a cumplir | Tres papeles: EMS, referencia, reconstrucción, combinables con `+` como ya se hacía con los medidores |

**Dos defectos hallados al verificar el escalado**, ninguno de ellos de
CAL-44 sino destapado por ella: `cache_fuentes.py` usaba
`RECONSTRUCTION_INVERTERS_CONFIG` sin importarlo, y `cache_crudo.py` quedaba
con un import sin uso. Corregidos.

**Los seis restantes no necesitan tocarse**, y se comprobó por qué:

- `scripts/plot_coverage_gantt.py` y `scripts/plot_perfiles_DG_actualizados.py`
  leen la configuración por defecto: recogen CAL-44 solos y correctamente. En
  el Gantt el asterisco del inversor designado se mueve del Fronius 1 al del
  proyecto, que es lo que debe pasar.
- `Presentacion/tesis_p2p/scripts/make_profile_figures.py` y
  `make_scaling_figures.py` también, aunque esas figuras ya venían del canon
  de junio y estaban marcadas como desfasadas por otra razón.
- `tests/test_preprocessing.py` **pasa sin cambios (8 de 8)**, y su docstring
  ya afirmaba que «EMS solo expone Inversor MTE»: era falso hasta hoy y CAL-44
  lo vuelve cierto. La razón G_recon/G_ems pasa de 2,48 a 2,06, dentro de la
  banda [1,5; 6,0] que el test exige.
- `tests/test_fast_mode_equivalence.py` usa las series reales para comparar
  dos rutas de código, sin afirmar valores de generación.

**Verificación estática de los cuatro archivos tocados**: todos los nombres
globales resuelven y la sintaxis compila. Ninguna de las dos cachés se
regeneró, de modo que el documento sigue mostrando el canon.



---

## C-91 · CAL-44 y P-17, propagadas al documento

**2026-09-03 · tipo: `contenido` + `figuras` · aplicada**

Regeneradas las dos cachés y **las 47 figuras**, y actualizado el texto. La
caché era del 21 de agosto, anterior a P-17, de modo que al regenerarla
entran las dos correcciones a la vez.

**La caché se verifica contra el pipeline: `max|dif| = 0` en D y en G, en
las dos fronteras.** Esa comprobación es justo la que habría fallado si no
se hubiera adaptado `cache_crudo.py` (ver C-90).

**Un defecto que CAL-44 introdujo en una figura y hubo que arreglar.** El
Gantt marca con un anillo la última fuente esencial en entrar en servicio,
y tomaba como esencial el inversor designado de cada institución. Al pasar
el de Udenar a ser el del proyecto, que entra el 3 de septiembre, **el
anillo se movió a él y la figura decía que el horizonte empieza en
septiembre**. Corregido en `gen_cap02.py`: lo que hace falta para que
Udenar tenga generación desde el primer día no es su inversor designado
—que se reconstruye hacia atrás— sino el de referencia. Con el criterio
nuevo siguen siendo 14 las fuentes esenciales y la última en entrar vuelve
a ser el inversor del HUDN, el 4 de abril a las 05:58. La figura resultante
es **byte a byte idéntica** a la anterior.

**Cifras actualizadas** (recalculadas desde la caché nueva):

| | Antes | Ahora | Causa |
|---|---:|---:|---|
| Generación comunitaria | 60.860 kWh | 63.574 kWh | CAL-44 |
| Cobertura M1 | 19,1 % | 20,0 % | CAL-44 |
| Cobertura M3 | 91,2 % | 95,3 % | CAL-44 |
| Demanda comunitaria M1 | 318.046 kWh | 318.045 kWh | P-17 |
| Horas con generación | 3.353 | 3.354 | P-17 |
| Horas con excedente M1 | 1.047 | 1.131 | CAL-44 |
| Horas con excedente M3 | 2.512 | 2.567 | CAL-44 |

Tocadas en la nomenclatura, en las dos etiquetas del esquema de fronteras,
en la nota de la figura de cobertura, en la caja de lectura, en la nota del
embudo y en el cierre del capítulo 4.

**Una cifra que parecía desfasada y no lo estaba.** Los \uni{33705}{kWh}
que la reconstrucción devuelve a Udenar no salen de la suma de inversores
(32.691) sino de la diferencia sobre la serie **con signo**, que sigue
dando 33.704,7. Se comprobó antes de cambiarla.

**Prosa del capítulo 2, reescrita.** El censo de fuentes y el pasaje del
arranque del horizonte describían los papeles al revés. Ahora dicen que la
fuente esencial de Udenar es el inversor de referencia, y que el del
proyecto queda fuera del cómputo porque su serie se reconstruye hacia
atrás.

**Balance de figuras: 17 cambian, 30 quedan idénticas.** Que las 30
canónicas —capítulos 9 a 13— salgan byte a byte iguales confirma de paso
que son reproducibles.

**Dos figuras mezclan el preproceso nuevo con el canon viejo y quedan
señaladas:**

- `f4_05_embudo_horas`: sus dos escalones intermedios ya llevan CAL-44 y el
  último sale de los flujos liquidados de la corrida anterior. La cadena
  sigue siendo coherente, porque 1.131 horas con excedente siguen siendo
  más que las 1.029 transadas, pero el último escalón crecerá con la
  corrida. **Declarado en la nota de la figura.**
- `f11_08_lado_corto`: mismo cruce, con los índices de Sobol. Su capítulo
  es todavía una plantilla, de modo que no se publica; se revisará cuando
  se redacte.

**Estado**: el documento compila limpio en 87 páginas, sin desbordes, y el
estilo se mantiene en 24,7 palabras por oración frente a las 24,6 del
perfil, sin una sola raya larga.


---

## C-92 · La razón G/D deja de estar escrita a mano

**2026-09-03 · tipo: `figuras` · aplicada**

Él avisó de que **varias figuras seguían diciendo 19,1 % y 91,2 %** aunque
el texto ya dijera 20,0 % y 95,3 %. La causa estaba en `estilo.py`:

```python
COBERTURA_GD = {"m1": "19,1 %", "m3": "91,2 %"}     # escrito a mano
```

De esa constante salen `TITULO_COBERTURA`, la forma corta de los ejes y el
título de dos líneas, es decir, **el rótulo de todas las figuras de dos
paneles**. El texto se actualizó y las figuras no, porque la cifra vivía en
dos sitios.

**La corrección no es cambiar el número, es quitar el número.** Ahora se
calcula del mismo `npz` del que salen las series, con respaldo y aviso si
la caché falta. No puede volver a divergir.

Además llevaban la cifra escrita a mano el rótulo del eje de
`f11_08_lado_corto` —que es texto dibujado, no comentario— y cuatro
docstrings (`datos.py`, `gen_cap04.py`, `gen_cap11.py`, `gen_cap12.py`).
Corregidos.

**Regeneradas las 47 figuras otra vez.** Ahora cambian 31 de 47 frente al
punto de partida, y no 17: el título con la razón nueva alcanza también a
las de los capítulos canónicos.

**Salvedad anotada.** Las figuras de los capítulos 9 a 13 dibujan
resultados de la corrida anterior y ahora llevan en el título la razón
nueva. Sus capítulos son todavía plantillas, de modo que no se publica esa
mezcla, y la corrida las regenera enteras.

**Auditoría numérica completa tras la corrección**: se recalcularon desde
la caché los 25 valores publicados que dependen del preprocesamiento —
agregados de frontera, embudo de horas, reconstrucción y recorte, tabla de
tipos de medidor y generación por institución— y se contrastaron contra el
texto. **Cero desfases, y ningún valor recalculado ausente.** El guion de
auditoría comprueba las dos cosas: que aparezca el valor nuevo y que no
sobreviva el viejo.


---

## C-93 · Auditoría de estructura y reorganización de la reconstrucción

**2026-09-03 · tipo: `estructura` · aplicada**

Él señaló que los párrafos de la reconstrucción no se entienden y que no
parecen seguir ninguna estructura, y pidió auditar el documento entero
hasta ese punto.

**La estructura mayor está sana.** El Capítulo 3 sigue las seis etapas del
canal en orden, con su mapa de reparto («la primera ocupa cuatro
subsecciones…»), y el Capítulo 2 va de la extensión temporal al corte y de
ahí a la completitud dentro del corte. El fallo era local.

**Qué le pasaba a esa subsección.** Se había ido formando por parches
sucesivos y mezclaba cuatro asuntos sin orden: la glosa de la fórmula,
a quién se le aplica, por qué en Udenar son tres y el caso de borde. El
segundo párrafo **empezaba dos veces** («En Udenar la suma incluye tres
inversores» e inmediatamente «Los tres equipos de Udenar no cumplen el
mismo papel»), y los medidores brutos quedaban en el tercero, lejos del
párrafo que reparte los casos.

**Estructura nueva, un asunto por párrafo**: qué dice la fórmula · a quién
se le aplica · el caso difícil, que es Udenar · cuándo actúa el recorte ·
el caso de borde · la figura.

**Barrido de párrafos acumulados en los cuatro capítulos escritos.** El
criterio: más de 120 palabras o más de 6 oraciones sobre un perfil medido
de 74 palabras y 3,2 oraciones. Salieron cinco; dos eran reales y se
partieron:

- Capítulo 2, el arranque del horizonte. Lo había hecho crecer ese mismo
  día a 130 palabras al reescribirlo para CAL-44: juntaba el principio, la
  cuenta de fuentes esenciales, el caso de Udenar y el remite a la figura.
- Capítulo 3, el sesgo que apunta al revés. 151 palabras y cuatro asuntos,
  y además decía «se nombra aquí en vez de esconderla», que es **el texto
  hablando de sí mismo**, contra la primera regla de claridad. Se retiró la
  cláusula.

Quedan tres marcados y se dejan: uno está justo en el umbral y los otros
dos son listas separadas por punto y coma, que el contador de oraciones lee
mal.

**Estilo tras la reorganización**: 24,4 palabras por oración frente a 24,6
del perfil, 70,7 por párrafo frente a 74, y ninguna raya larga.

**Comprobación de figuras, a petición suya.** Las 45 figuras que el
documento usa se regeneraron **después** del arreglo de `estilo.py`
(23:21:17), y ninguna figura referenciada por el texto falta. Dos archivos
de la carpeta no se regeneraron porque son huérfanos: ningún `.tex` los
cita y ningún generador los produce ya. Son
`f3_02b_gradacion_m1.png`, retirada por C-84 y sustituida por la de
profundidad, y `f2_05_reactiva_instituciones.png`, sustituida por la de
series. **Se dejan en su sitio a la espera de su palabra**, porque
borrarlos no es reversible y no estorban a la compilación.


---

## C-94 · Auditoria numerica del Capitulo 2

**2026-09-04 · tipo: `verificacion` · sin desfases**

El pidio verificar cada cifra del capitulo. Son 71 lineas con afirmacion
numerica; 21 son comprobables contra una fuente y **las 21 verifican**.

| Bloque | Comprobado |
|---|---|
| Censo | 20 medidores, 7 inversores, 27 fuentes |
| Magnitudes | 54 por medidor, 18 por inversor, 72 en total |
| Uso en el modelo | 9 medidores de frontera, 11 auxiliares, 5 inversores de generacion, 2 auxiliares, 16 empleadas, 14 esenciales |
| Fechas | Medidor 4 de Udenar el 29 de abril, Inversor MTE el 3 de septiembre, inversor del HUDN el 4 de abril a las 05:58 |
| Cobertura | 88,7 % y 39,3 % sobre el horizonte; 98,7 % y 97,7 % descontadas las previas; el conjunto entre 96,7 % y 98,8 %; 204 horas el peor, que es auxiliar; 126 el peor en uso; todas las usadas por encima del 97 %; horas que faltan de 31 a 204 |

**Tres falsos positivos, todos mios.** Conte las carpetas de medidor con
una comparacion literal y la de Cesmag lleva una errata de la plataforma
(`eletricMeter`), de modo que perdi cuatro medidores y salieron 16 en vez
de 20. Y medi la cobertura sobre el horizonte cuando el capitulo la mide
sobre el periodo en servicio de cada equipo. **El documento tenia razon en
las tres.** La leccion: contrastar contra el CSV hermano que la figura
escribe, no contra un recalculo propio que puede repetir el error.

**Hallazgo colateral.** La subseccion de la energia reactiva del Capitulo 2
esta dentro de un bloque `guardado`, de modo que **no se imprime**. Sus
cinco cifras (15,0 %, 65,7 %, 1.865.016 COP, 1.210.145 COP y 6,8 %) estan
guardadas, no publicadas. La medicion completa vive en el Anexo A6, que si
se imprime y queda pendiente de auditar.


---

## C-95 · Pasada sobre el Capitulo 3 desde la reconstruccion hasta el cierre

**2026-09-04 · tipo: `estructura` + `contenido` · aplicada**

El pidio continuar la revision desde la linea 645 con todos los criterios
acumulados. Nueve arreglos.

**El grave: una cuenta rota.** «Las decisiones que sesgan en contra»
anunciaba una lista de elecciones, ponia **cuatro**, y despues un parrafo
suelto decia «hay una **sexta** que el capitulo no habia declarado». El
cierre, en cambio, afirmaba «cinco de las seis recortan el resultado». El
lector contaba cuatro y le hablaban de una sexta. La quinta —la generacion
que se pone a cero antes de la limpieza— baja a la lista, donde le
tocaba, y el arranque dice la cuenta: cinco apuntan a recortar, tres del
pipeline y dos del modelo, y la sexta apunta al reves.

**Enumeraciones que eran prosa.** Los tres criterios de relleno del
proyecto se soltaban en un parrafo corrido dentro de una caja de trampa.
Pasan a lista de tres, y la valoracion queda aparte: de las dos
diferencias solo una se sostiene.

**Repeticion con la tabla nueva.** «Lo que cuesta reconstruir» volvia a
dar el reparto por institucion que la Tabla~
ef{tab:prep-reconstruccion}
ya muestra. Se queda con lo que la tabla no dice: el mecanismo, la
magnitud y el signo.

**El texto hablando de si mismo, cuatro veces.** «Se declara aqui antes de
que el lector lo advierta», «es la mas corta de las seis y la que mas
facilmente pasa inadvertida», «la subseccion anterior ya usa esa
alineacion», y el arranque «un capitulo que describe seis etapas debe
responder a una objecion». Retiradas.

**Parentesis de glosa**, que no son la forma del autor: dos en el cierre
de la honestidad metodologica, pasadas a coma y a dos puntos.

**Un intento retirado.** Se quitaron un «conviene» del mapa del canal y un
«es importante definirla ahora» de la excepcion de Mariana, los dos en la
zona que el daba por depurada. **El aviso de que algunos estan puestos a
proposito porque funcionan donde estan, y se restauraron.** La regla vale
para el texto nuevo, no para revisar hacia atras lo que el ya dio por
bueno.

**Estado**: 24,2 palabras por oracion frente a 24,6 del perfil, 69,7 por
parrafo frente a 74, ninguna raya larga; compila en 87 paginas sin
desbordes; auditoria numerica en cero desfases.

---

## C-114 · Pasada de revision: repeticion, estilo y un error de hecho

**2026-09-04 · tipo: `contenido` · aplicada**

Revision de lo escrito con cuatro comprobaciones, una de ellas nueva: un
detector de cifras repetidas, que es la que el pidio.

**Un error de hecho.** El texto decia que los minimos de Mariana y la UCC
son «veinte veces menos profundos» que el de Udenar. Medido: 13,9 y 5,7
veces. Corregido a «entre seis y catorce».

**Dos parrafos que recitaban la tabla de tipos celda a celda.** Mismo
patron que ya se corrigio en la reconstruccion: la prosa enumeraba lo que
la tabla muestra, de modo que el lector leia dos veces lo mismo. Se queda
la interpretacion, que es lo que la tabla no dice.

**El caso de Mariana bajo M3, explicado tres veces.** En la subseccion de
la demanda negativa, tras la tabla de tipos y al cerrar la clasificacion.
La tercera repetia la explicacion entera solo para poder añadir el costo
de llevar esas horas a cero. Se queda la explicacion junto a la tabla, que
es donde el lector ve la anomalia, y la tercera se reduce a lo que
aportaba. La cifra 213 baja de seis apariciones a cuatro, de las cuales
dos son las dos filas de la tabla.

**Un parrafo mio de 126 palabras**, el del acotamiento del relleno,
partido en la objecion y sus dos cotas.

**Lo que se reviso y se deja como esta.** La raya larga que el detector
marca en la nomenclatura esta en un comentario y no se imprime. Los
«conviene» y el «es importante» de los capitulos 2 y 3 son los que el dejo
a proposito. Los ocho pies por encima de 55 palabras describen y no
argumentan, que es la norma de C-109.

**Lo que queda fuera de esta pasada**: las repeticiones de `182,5` en el
Capitulo 5 y de `1.865.016` en el Anexo A6, mas los nueve «este capitulo»
del Capitulo 5 y los seis «conviene» de A6. Los dos capitulos siguen sin
auditar.

**Estado**: 94 paginas, sin errores, sin desbordes, sin referencias sin
resolver; auditoria numerica en cero desfases; estilo en 24,3 palabras por
oracion frente a 24,6 del perfil y sin una sola raya larga en el texto
impreso.

---

## C-113 · La matriz de sensibilidad del preprocesamiento (paso 4 de 4)

**2026-09-04 · tipo: `contenido` · aplicada**

Cierra la respuesta a la critica externa. El reparo decia que admitir «no
se construyo una matriz de sensibilidad» y relegarla a trabajo futuro es
inadmisible para este nivel de grado. Tenia razon, y ademas resulto barato:
los cuatro parametros viven en la etapa de limpieza, cuya entrada esta
cacheada.

**Que se mide y por que esa magnitud.** No basta el efecto sobre el dato:
la critica exige el efecto sobre la conclusion economica. El puente ya
estaba probado en el proyecto, y es que el volumen transado es el lado
corto, de modo que el excedente vendible acota lo que puede transarse. Se
barre cada parametro de uno en uno y se mide la desviacion en la demanda,
en la generacion y en ese excedente, tomando el peor caso de las dos
fronteras.

| Parametro | Rango | Demanda | Generacion | Excedente |
|---|---|---:|---:|---:|
| Multiplicador del primer criterio | 1,5 a 10 | 0,024 % | 0,052 % | **0,059 %** |
| Factor del segundo criterio | 1,0 a 1,5 | 0,318 % | 0 % | 0,005 % |
| Limite de interpolacion | 1 a 12 h | 0,048 % | 0 % | 0,003 % |
| Limite de arrastre | 6 a 72 h | 0,511 % | 0 % | 0 % |

**Ninguna variacion mueve el excedente mas de seis partes en diez mil**, y
eso incluye llevar el multiplicador al clasico de 1,5, cuadruplicar el
limite de interpolacion o reducir el arrastre a la cuarta parte.

**La lectura**: lo que sostiene el preprocesamiento no es el acierto de
cada eleccion sino su irrelevancia. **La cautela**, dicha en el documento:
el barrido acota las entradas y el excedente, no el resultado del mercado,
que exigiria repetir la corrida por combinacion.

**Dos frases que caducaron y se corrigieron.** El punto tercero de la
declaracion de honestidad decia que la matriz no se habia construido. Y la
cota global del ±0,3 % se presentaba como «una estimacion declarada y no un
valor calculado, sin matriz que la respalde»; ahora tiene una medida
debajo, un orden de magnitud menor, y se conserva solo porque cubre ademas
lo que el barrido no alcanza.

**Con esto la critica externa queda respondida en sus seis puntos**: dos se
invirtieron al medirlos, uno estaba ya contestado en el documento y mal
colocado, dos se declararon como alcance con su argumento, y este se
construyo.

---

## C-112 · Respuesta medida a la critica externa (pasos 1 y 2 de 4)

**2026-09-04 · tipo: `contenido` · aplicada**

Una revision externa objeto seis puntos a los capitulos 2 y 3. Dos de
ellos cambian de signo al medirlos, y esa es la respuesta que entra en el
documento.

### El multiplicador «sin sustento», medido

El reparo decia que el 5 del primer criterio es arbitrario y que el
segundo es «un parche». Barrido el multiplicador entre 1,5 y 7, **con los
dos criterios la energia retirada va del 0,083 % al 0,021 % de la
demanda**: entre el clasico y el elegido hay cuatro horas de diferencia
sobre 122.880 horas de serie. El multiplicador no gobierna nada.

Y la segunda columna del barrido **invierte el reparo**: sin el segundo
criterio, el 1,5 clasico retiraria el 13,4 % de la demanda y ni un 7
bajaria del 2,4 %. El segundo criterio no cubre un fallo del primero, hace
que el primero deje de importar. Nueva `tab:prep-sensibilidad`.

La declaracion de honestidad decia «ni analisis de sensibilidad sobre su
valor», que dejo de ser cierto y se corrigio.

### Las mesetas que «contaminan irremediablemente», acotadas

El reparo decia que insertar mesetas planas de hasta 24 h contamina la
coincidencia entre el pico solar y el valle de demanda. La cota es doble y
esta ahora publicada: **la generacion no se rellena ni una sola hora** en
ninguna frontera, de modo que el pico solar nunca se fabrica; y del lado
de la demanda son 121 y 300 horas de serie en la franja diurna sobre
30.720, el 0,39 % y el 0,98 %.

### El mosaico de la reconstruccion, y dos defectos que destapo

Entra `f3_03b_reconstruccion_mosaico` con las diez series. Siete paneles
salen sin banda y ese vacio es el hallazgo: la fila de M3 funciona como
control de la de M1.

**Defecto 1, una banda que no existia.** La primera version dibujaba banda
de 0,10 kW en el Hospital y 0,04 en CESMAG. No era generacion: la serie
reconstruida conserva el hueco donde el medidor no trajo lectura y la de
la lectura lo lleva relleno con cero, de modo que **las dos curvas se
promediaban sobre conjuntos de horas distintos**, con 113 y 117 horas de
diferencia.

**Defecto 2, un aserto que no comprobaba lo que decia.** La identidad de
la reconstruccion se verificaba con el maximo de pandas sobre una
diferencia con huecos, y ese maximo los descarta en silencio: la prueba se
saltaba justo las horas que importaban. Misma familia que el
`assert ... or True` de C-84.

**Una cifra nueva**: bajo M3 la Universidad Mariana no recibe generacion y
sin embargo el recorte a cero todavia le quita 46,7 kWh, que son los 156
de M1 por el mismo factor 0,3 con que se construye su serie secundaria.

### Lo que queda de la critica

Pendiente el paso 3, nominalizar los titulos, y el paso 4, la matriz de
sensibilidad completa del preprocesamiento, que va con la corrida. Y la
declaracion de alcance sobre topologia electrica y capacidad de red, que
es el reparo mas fuerte y no tiene respuesta preparada.

---

## C-110 · La atribucion de fuente sale de los pies

**2026-09-04 · tipo: `norma` · aplicada**

Retiradas las **42** apariciones del macro `uente{}` de todas las
figuras y tablas del documento: 21 en los capitulos escritos y 21 en las
plantillas de los que aun no lo estan. El borrado cuenta llaves, porque
varias llevaban `ile{}` o `\code{}` anidados dentro.

**La trazabilidad no se pierde**, solo deja de imprimirse. Cada figura
conserva su `figuras/<nombre>.fuente.txt` con la ruta exacta del artefacto,
su CSV hermano, y la fila correspondiente en la tabla maestra de `GUIA.md`.
Lo que sale es la linea de la pagina.

**Efecto**: el documento pasa de 93 a 91 paginas.

`GUIA.md` queda al dia: su norma 4 decia que «el `\caption` termina con
`uente{...}`», que ya no es cierto, y la excepcion que permitia citar
rutas dentro de ese macro se reduce ahora al cierre de un `
otafig{}`.

**Pendiente de su palabra.** Sobreviven **18 «Elaboracion propia»** dentro
de notas de figura, que son ahora la unica atribucion impresa del
documento. El pidio borrar la fuente de las figuras, y esas frases lo son
aunque no usen el macro. Se dejan hasta que lo confirme, porque quitarlas
es otra decision y no la que pidio literalmente. El macro sigue definido en
el preambulo por si decide recuperarlo.

---

## C-109 · El pie describe; el parrafo siguiente explica

**2026-09-04 · tipo: `norma` · aplicada, y guardada como regla**

El lo pidio como regla y no como caso: el pie lleva la descripcion directa
y corta de lo que se ve, y lo que haya que seguir explicando baja al
parrafo siguiente, que en este documento es la nota de figura.

**Los pies habian crecido solos**, porque cada revision añadia una frase y
ninguna la quitaba. Medidos: 198 palabras la profundidad, 190 la escalera,
174 la anatomia y 148 el umbral, con la descripcion, el argumento, las
cifras del caso y los remites mezclados. Los cuatro eran de esta misma
sesion.

Despues de partirlos: **44, 61, 93 y 92**, y ninguno argumenta ya. Lo que
salio del pie no se perdio: bajo a la nota, salvo en la profundidad, donde
el pie repetia entero lo que el parrafo siguiente ya decia sobre la mitad
central de Udenar y bastaba con cortar.

La regla queda en `GUIA.md` con su comprobacion: un pie de mas de un
centenar de palabras casi siempre lleva algo que no le toca.

---

## C-108 · La demanda negativa y la profundidad, en las dos fronteras

**2026-09-04 · tipo: `figuras` + `contenido` · aplicada**

Siguen el criterio de C-106. Dos figuras mas que pasan a un archivo unico
con las dos fronteras, y con ello el capitulo pierde una figura y gana
coherencia.

**`f3_02_demanda_negativa`.** Fundir aqui no era apilar: las dos versiones
no dibujaban lo mismo a la izquierda, porque en M1 era el perfil medio y en
M3 el minimo de cada hora, ya que alli ninguna media llega a ser negativa.
Se resolvio dibujando **las dos curvas de la institucion afectada**,
promedio y minimo, en cada fila. El contraste entre filas es ahora el
argumento: bajo M1 el promedio de Udenar entra en la zona imposible y baja
a −11,0 kW a las 13, de modo que el neteo no arrastra casos sueltos sino la
media entera; bajo M3 ningun promedio la alcanza y solo el minimo la roza.

**Un defecto que la fusion destapo.** En la version M3 la curva destacada
era el minimo y las cuatro de contexto seguian siendo promedios, sin que
nada lo dijera. Eran objetos distintos comparados en el mismo par de ejes,
que es lo que C-84 dejo prohibido, y llevaba ahi desde que se creo.

**`f3_02b_profundidad`.** Dos paneles con escalas independientes, no una
sola: el recorrido dibujado abarca 51 kW en M1 y 3,8 en M3, un factor de
13, y con escala comun las cinco filas de la derecha caben en el 7 % del
ancho. Lo que se compara entre paneles no es una longitud sino **si el
recorrido cruza el cero**. En M3 lo cruza una sola institucion y las otras
cuatro nunca se acercan, que es lo que sostiene la afirmacion del capitulo
de que la lectura imposible es un asunto de la frontera principal.

**Lo que NO se hizo, y por que.** El autor pidio tambien la version M3 de
`f3_03_reconstruccion`. **Medido: bajo M3 no hay nada que reconstruir.** La
generacion devuelta es 0,0 kWh en las cinco instituciones y la demanda
reconstruida coincide con la lectura recortada a cero, con diferencia
maxima de 0,00e+00, porque en el circuito secundario los cinco medidores
son brutos. Una figura M3 seria dos curvas superpuestas y una banda de
altura cero. El dato de M3 esta reportado de otra forma: la tabla de tipos
lo dice con sus cinco «bruto» y la de la reconstruccion al no tener ese
bloque.

**Tres desfases de arrastre, corregidos**: la etiqueta `fig:prep-gradacion`
sobrevivia con dos referencias que habrian impreso «??»; el texto decia que
la profundidad pone la gradacion «en una sola escala», y ahora son dos
paneles; y el Anexo A1 decia «los cinco medidores de la frontera
principal», cuando ya son los diez.

**Estado**: 93 paginas, sin errores, sin desbordes y sin referencias sin
resolver; auditoria numerica en cero desfases.

---

## C-106 · Todo el dato, para todas las entidades, en las dos fronteras

**2026-09-04 · tipo: `contenido` + `figuras` · aplicada**

Criterio que el fijo: «deberiamos ir reportando todos los datos para todas
las entidades». Aplicado a las tres piezas de la etapa.

**`tab:prep-tipos` pasa a las dos fronteras.** El bloque de M3 no es
relleno: dice que en el circuito secundario **los cinco medidores son
brutos**, de modo que la frontera no cambia solo cuanta carga se mide sino
la semantica del propio equipo. La unica excepcion aparente es Mariana, que
no tiene medidor secundario y reutiliza el del principal escalado, y con el
hereda sus 213 horas negativas ya reducidas: -0,72 kW es -2,41 x 0,3 y los
47 kWh son 156 x 0,3.

**`f3_04b` pasa a diez paneles en un archivo**, cinco instituciones por dos
fronteras. Fue posible porque la tabla de C-103 se llevo los valores y la
figura pudo quedarse con la geometria.

**`f3_06` pasa a las dos fronteras**, y aqui el motivo era mas grave que el
criterio. Su franja del presupuesto **afirmaba que Udenar y la UCC no
tenian ninguna hora tratada**, lo que es falso sobre el dato: bajo M3
tienen 97 y 126. En M1 sus huecos los habia borrado el `fillna(0)` de la
reconstruccion antes de que la limpieza los viera, que es H-25. Ahora esos
ceros dicen «0 · huecos cerrados antes» y la figura lleva la explicacion
debajo, no solo en el pie. El tercer peldaño pasa ademas a ser el hueco mas
largo **del estudio**, 49 h de la UCC bajo M3, que es el que prueba que ni
el mayor alcanza el techo de 51.

**Los dos archivos pierden el sufijo de frontera**, porque cubrirlas las dos
lo habria vuelto falso y el generador habria emitido duplicados identicos.

**Quedan tres figuras huerfanas en disco** de versiones retiradas:
`f3_02b_gradacion_m1`, `f3_05_outliers_imputacion_m1` y `_m3`. Ningun `.tex`
las cita y ningun generador las produce. Se dejan a la espera de su palabra,
porque borrarlas no es reversible.

---

## C-103 · El rango intercuartilico, tabulado por entidad

**2026-09-04 · tipo: `contenido` · aplicada**

Su objecion, sobre la figura de anatomia: «no lo comprendo ya que ese valor
no se reporta en ningun lugar para cada entidad». Tenia razon. El cuadro de
la figura representa el rango intercuartilico, pero ese valor solo aparecia
en los titulos de los tres paneles dibujados y en dos cifras sueltas del
texto. **Udenar y Mariana no lo tenian en ninguna parte.**

Nueva `tab:prep-umbral`, con la anatomia completa de las diez series de
demanda en las dos fronteras: rango, distancia de la cola en rangos, los
dos candidatos con el que se aplica en negrita, y horas retiradas. Las
series de generacion no entran porque en las diez manda el primer criterio
y ninguna retira una sola hora, y asi queda dicho.

La columna de la cola es la que explica el reparto, y en la tabla se ve en
dos filas contiguas: bajo M1 el HUDN y CESMAG tienen rangos casi iguales,
1,40 y 1,27 kW, y el umbral de cada uno lo fija un criterio distinto porque
la cola cae a 1,2 rangos en uno y a 8,2 en el otro.

La tabla permite ademas recortar prosa: las cifras que el texto venia
soltando sueltas dejan de repetirse.

**Sobre el tamaño del cuadro**, que fue lo que disparo la pregunta: su
altura es el dato, el rango entre el primer y el tercer cuartil, y el ancho
no significa nada, esta solo para que las cinco copias se reconozcan como
copias. La pila completa mide seis rangos, de modo que el cuadro ocupa
siempre un sexto y los tres paneles se parecen aunque los rangos reales
difieran casi veinte veces. Es el precio de las escalas independientes.
**Medido sobre las diez series** al pasar la figura a las dos fronteras: los
rangos reales difieren por un factor de **76,7**, de 24,35 kW en la UCC bajo
M1 a 0,318 kW en el Hospital bajo M3, mientras que la altura con que se
dibuja el cuadro solo difiere por un factor de **5,5**, del 15,1 % del panel
al 2,7 %. No es un descuido del dibujo: cuando manda el primer criterio, la
pila ocupa casi todo el panel y el cuadro es un sexto de ella sea cual sea
el rango.

Lo que si se hizo, porque era el fallo de fondo, es **decir en el pie que
se compara**: con escalas independientes, entre paneles no se comparan
alturas sino una relacion, si la cola con su prolongacion queda por encima
o por debajo de la quinta copia. Sin esa instruccion el lector intenta
comparar alturas y no le cuadra.

**La distorsion queda sin corregir a la espera de su decision.** De las tres
salidas propuestas, la vineta con los rangos sobre un eje comun es la unica
que no obliga a renunciar a las escalas independientes.

---

## C-102 · La anatomia del umbral, y la metrica que la sostiene

**2026-09-04 · tipo: `figuras` + `contenido` · aplicada**

El pidio una figura para entender el IQR de forma grafica en cada factor.
Lo que faltaba era la anatomia de la formula: el panel derecho de `f3_05`
dice quien manda en cada serie, pero el lector veia `Q75 + 5·IQR` como
notacion y nunca veia el rango como una longitud que se multiplica por
cinco.

**`f3_04b_anatomia_umbral`**, nueva. Tres series de demanda con escalas
independientes, porque sus rangos van de 1,3 a 24,4 kW bajo M1. En cada
una: la caja de la mitad central, **cinco copias exactas de esa misma
caja** apiladas sobre el tercer cuartil y numeradas del 1 al 5, de modo que
la multiplicacion se cuenta con el ojo, el percentil 99,5 con su
prolongacion del 20 %, el umbral aplicado con trazo lleno y el candidato
perdedor discontinuo.

**La cifra que faltaba y que resulta ser el argumento entero**: a cuantos
rangos intercuartilicos del tercer cuartil cae el percentil 99,5. Bajo M1,
el Hospital a 1,2 y CESMAG a 8,2, **con rangos casi iguales, 1,4 y 1,3 kW**.
Bajo M3 el contraste llega a 1,5 frente a 23,2. Es la contrapartida
numerica de lo que C-100 dejo dicho en prosa, que el peligro no lo trae el
rango estrecho sino el perfil de dos modas, y el texto la adopta: donde
antes se afirmaba, ahora se mide.

**Numeracion**: el prefijo `f3_04` estaba libre en disco pero el numero 3.4
lo ocupa el diagrama de los tres tipos de medidor, que se dibuja en LaTeX y
por eso no tiene archivo. Se usa la letra, que es la convencion que ya
siguen otras cuatro figuras del capitulo.

**Un defecto que el cambio de vocabulario habia introducido.** Al renombrar
el rotulo de `f3_05` a «segundo criterio: 1,2 × P99,5» paso a medir 1,13
pulgadas, justo lo que hay entre su vertical y la columna de umbrales, y
**se imprimia sobre la cifra de la primera fila**. La prueba de oclusion lo
cazo en las dos fronteras. El nombre bajo a la leyenda y `f3_05` se
regenero.

**Estado**: 91 paginas, sin errores ni desbordes; cero choques de oclusion
en las seis figuras de la etapa; auditoria numerica en cero desfases.

---

## C-100 · La etapa de limpieza describía mal tres de sus cuatro pasos

**2026-09-04 · tipo: `dato` + `figuras` + `estructura` · aplicada**

Él pidió una figura por cada uno de los cuatro pasos. Al medirlos con dos
agentes, uno de análisis y otro de diseño, y verificarlo yo por mi cuenta,
resultó que **el documento describía mal tres de los cuatro**. La
corrección del texto iba antes que cualquier figura: dibujar el cuarto paso
habría sido dibujar algo que no ocurre.

### Los tres errores, todos confirmados dos veces

**El paso 2 no rellena «los huecos de hasta 3 horas».** `interpolate` acota
los NaN *consecutivos*, de modo que rellena **las tres primeras horas de
cualquier hueco**. Uno de cinco horas recibe tres y deja dos. Comprobado
con casos mínimos de 2 a 6 horas y sobre el dato real, donde los 55 huecos
que necesitan relleno posterior tienen exactamente tres horas interpoladas.

**El paso 4 no actúa nunca.** `ffill(24).bfill(24)`, después de las tres
horas del paso anterior, alcanza **51 horas**. El hueco más largo del
estudio mide 49, en la demanda de la UCC bajo M3. Cero horas rellenas con
cero en las 20 series, en las dos fronteras.

**El paso 3 no copia «el valor de la hora vecina más próxima».** El
arrastre hacia adelante propaga **la tercera hora interpolada**, que es un
valor fabricado, no la última lectura del equipo. Y repite un escalar: en
un hueco de 42 horas del Hospital la demanda queda plana en 10,1228 kW
durante 24 horas seguidas. No replica «el patrón del día operativo
anterior», lo destruye.

### Una imprecisión más, en el paso que sí estaba bien

La explicación de CESMAG atribuía el peligro de la cerca de Tukey al rango
intercuartílico pequeño. **El HUDN tiene el menor de todo el estudio,
0,318 kW bajo M3, y no le pasa nada**, porque su carga es tan plana que
nunca se acerca a la cerca. El mecanismo real es el perfil de dos modas,
base muy estable con picos operativos raros de gran amplitud.

Lo que sí se sostiene, y con holgura, es la afirmación de fondo: sin el
piso del percentil, la demanda de CESMAG perdería 451 horas bajo M1, que
concentran el 20,7 % de su energía, y 927 bajo M3, que concentran el
**52,5 %**.

### El censo, verificado dos veces de forma independiente

De 808 horas que la cascada trata en las 20 series: 11 atípicos, 233
interpoladas, 575 arrastradas (el 71,2 %) y **cero puestas a cero**. Las
diez series de generación no reciben ningún tratamiento en ninguna
frontera.

### La subsección se parte en dos, con una figura cada una

«Valores atípicos y huecos» pasa a «El umbral de los atípicos» y «La
escalera de los huecos». **Dos figuras y no cuatro**, porque los pasos 2, 3
y 4 no son tres ideas sino tres tramos de una: el filtro se aplica hora a
hora dentro del hueco y no clasifica huecos por longitud, de modo que el
caso puro del paso 3 no existe en el dato y el del paso 4 tampoco. Tres
figuras separadas habrían fingido una separación que el canal no hace.

- **`f3_05_umbral_atipicos`** sustituye a la figura vieja. A la izquierda,
  la hora retirada con su antes y su después sobre tres días. A la derecha,
  las diez series con el eje en múltiplos del percentil 99,5, de modo que
  el `max()` se lee como geometría: manda el piso justamente en las filas
  cuya cerca de Tukey cae a la izquierda de la vertical de 1,2.
- **`f3_06_escalera_huecos`** es nueva. Tres huecos reales de longitud
  creciente con el eje en horas desde el inicio, llaves que miden cada
  tramo, y la referencia punteada de la última lectura observada, que
  enseña que la meseta no se queda en ella.

**Se retira el reparto por mes** de la figura vieja: el mes no decide nada,
y el «cuándo» ya lo lleva el Gantt del Capítulo 2.

### Y una declaración que faltaba

Tomar como nula la demanda de partida en la reconstrucción convierte en
cero **330 horas bajo M1**: 90 de Udenar, 114 de Mariana y 126 de la UCC.
Entran al modelo como consumo nulo sin pasar por la limpieza, que ya no las
ve, y sin que ninguna marca las distinga de una hora medida. Declarado
donde ocurre y añadido a la lista del sesgo, **que pasa de seis decisiones
a siete**: seis recortan y una amplía.

### De paso

Se corrigieron otros dos sitios que arrastraban el error: la descripción
adelantada en «la hora incompleta», que decía «le pone cero más allá», y el
remite de la zona horaria, que se apoyaba en que la limpieza distingue el
cero nocturno de la generación del hueco de medida. **Eso no ocurre**,
porque las series de generación no reciben tratamiento; ahora se apoya en
la banda solar de la matriz.

### El pasaje del umbral, reordenado y renombrado (mismo dia)

El siguio sin entenderlo, y con razon. Dos fallos:

**Nombraba los dos criterios antes de decir que hacen** y no explicaba lo
esencial, que al tomar el MAYOR de los dos se aplica siempre el mas
permisivo, y que el segundo solo entra cuando el primero se ha vuelto
demasiado estricto. Un «piso» sobre un techo es ademas una doble negacion
que nadie descifra al vuelo. Reordenado por la logica: la tension que hay
que resolver, que hace el primer criterio, donde falla, para que existe el
segundo, la prueba de CESMAG con su mitad central de 1,273 kW frente a un
corte en 10,6 kW, y solo entonces el matiz del HUDN.

**Y «cerca de Tukey» sale del documento.** El preguntó si estaba bien
decirlo. No lo estaba: en español «cerca» es sustantivo y adverbio, y el
pasaje usaba los dos con dos líneas de diferencia («el corte queda cerca de
esa base» y «la cerca cae en 10,6 kW»), y más abajo «le basta la cerca,
porque su carga es tan plana que nunca llega a acercársele». La solución no
fue buscar sinónimo sino no necesitar el sustantivo: el pasaje ya nombra
los dos candidatos como primer y segundo criterio. Tukey se menciona una
vez, como procedencia, glosado con los bigotes del diagrama de caja.

Los rótulos de la figura se alinearon con el texto y se regeneró: «Corte
del primer criterio» y «segundo criterio: 1,2 × P99,5». Un objeto, un
nombre, el mismo en los dos sitios.

De paso se cazó un énfasis escrito en formato markdown dentro del `.tex`,
que habría impreso los asteriscos. Comprobado que no queda ninguno suelto
en ninguna sección.

**Estado**: 90 páginas, sin errores ni desbordes; auditoría numérica en
cero desfases; estilo en 23,8 palabras por oración frente a 24,6 del
perfil.

---

## C-98 · «Lo que cuesta reconstruir» se aparta del documento principal

**2026-09-04 · tipo: `estructura` · aplicada**

El aviso: la subseccion no es importante en el documento principal. Se
aparta con `guardado`, 238 palabras, siguiendo el precedente del Capitulo 2,
que ya tiene una subseccion entera dentro de uno de esos bloques.

**Por que sobraba.** Sus dos cifras centrales, las 353 horas y los 1.013,3
kWh, quedaron en la Tabla de la reconstruccion cuando esa enumeracion paso
de prosa a tabla (C-93). El argumento del signo lo recoge entera la
subseccion del sesgo, que lo pone como primero de seis. Lo unico propio que
quedaba eran tres porcentajes y el enunciado del mecanismo, que el parrafo
de la reconstruccion ya da.

**Dos referencias reconectadas antes de apartar**, porque la etiqueta queda
dentro del bloque y LaTeX habria impreso «??»:

- El parrafo de la reconstruccion remitia a ella para «medir cuanto
  cuesta». Se retira el remite: la tabla ya lo mide.
- El primer punto de la lista del sesgo remitia a ella. Ahora remite a la
  Tabla~
ef{tab:prep-reconstruccion}.

Comprobado que no queda ninguna referencia rota.

**Efecto sobre H-24.** La frase «lo que eso elimina de la serie de demanda»
sale de imprenta con la subseccion. Queda impresa una sola vez, en el primer
punto de la lista del sesgo: «el recorte de la reconstruccion elimina
1.013,3 kWh de la demanda de Udenar». El hallazgo sigue abierto, pero ahora
se resuelve tocando una sola frase.

**Estado**: 87 paginas, sin errores ni desbordes; el Capitulo 3 pasa de
5.340 a 5.035 palabras publicadas; estilo en 24,1 palabras por oracion
frente a 24,6 del perfil.

---

## C-97 · La nota de la figura se aparta, y el medidor de estilo deja de medir lo apartado

**2026-09-04 · tipo: `contenido` + `herramienta` · aplicada**

El aviso: la nota de la figura de la reconstruccion es demasiado para algo
que la figura rediseñada ya dice, y ademas parte de su contenido ya estaba
puesto.

**Lo que se aparta.** La forma del perfil se lee en la curva azul y el
desglose en energia esta en la franja inferior de la figura. Las dos frases
bajan a un bloque `guardado`, de modo que el texto sigue en el fichero y
fuera del PDF.

**Lo que sobrevive.** Una sola frase, la del argumento, que no es
descripcion sino razonamiento y no se lee sola en el dibujo: la lectura se
hunde exactamente cuando la banda se ensancha, y ninguna averia de sensor
produciria eso. Sube al parrafo que presenta la figura, que es su sitio.

**La caja de las dos capas se queda, corregida.** Es el unico lugar del
documento donde se dice que la generacion que el modelo negocia y la que
se devuelve al medidor son conjuntos distintos, que es precisamente la
confusion de la que salio CAL-44. Estaba ademas incompleta: no decia cual
es el inversor designado de Udenar, que desde CAL-44 es el del proyecto.

**Hallazgo en la herramienta.** `medir_estilo.py` **no excluia los bloques
`guardado` ni `descartado`**, de modo que el perfil de estilo se calculaba
sobre texto que el lector no ve. Corregido. El efecto no era menor: se
median 1.114 palabras de mas, el 9 % del total, y el Capitulo 2 pasa de
2.799 a 2.081 palabras publicadas, es decir, mas de una cuarta parte estaba
apartada.

**Estilo real, ya sin lo apartado**: 24,1 palabras por oracion frente a
24,6 del perfil, 67,5 por parrafo frente a 74, ninguna raya larga.

---

## C-96 · La reconstrucción se dibuja como la operación, y cambia de día

**2026-09-04 · tipo: `figura` · aplicada, con el pie pendiente de aplicar**

La figura de la reconstrucción dibujaba tres series pero no la operación
que las une. La generación iba en beige desde el eje cero, como una serie
independiente, y para comprobar que la lectura más la generación
daban la demanda reconstruida había que sumar de cabeza, hora por hora.

**La generación pasa a ser la banda entre las dos curvas.** Se dibuja
entre la lectura del medidor y la demanda reconstruida, no desde cero, de
modo que la curva azul es literalmente la roja levantada por la banda y la
igualdad se lee sin aritmética. Una cota vertical mide la banda en la hora
de lectura más baja y dice cuánto mide, 35,1 kW.

**El día cambia: del 16 de julio al viernes 7 de noviembre de 2025.** Él
lo detectó solo, «se ve muy poca demanda al mediodía, es raro», y tenía
razón. El 16 de julio cae **antes del 3 de septiembre**, cuando el
inversor del proyecto todavía no registraba: la suma iba incompleta, la
reconstrucción se quedaba corta y ese día la demanda reconstruida bajaba a
0,0 kW a las 13 y a 1,3 kW a las 15, con la hora de las 13 recortada a
cero. La figura ilustraba el método con un día en que el método falla a la
vista, y el lector concluía que la reconstrucción está rota. El 7 de
noviembre pertenece al tramo con los tres inversores registrando, no tiene
ninguna hora recortada y el medidor pasa 10 horas bajo cero, con lo que
el fenómeno se ve mejor y la demanda reconstruida da un perfil de campus
creíble: base nocturna de 5,2 kW, ascenso hasta 20,1 a las 11, valle de
almuerzo de 11,8 a las 12 y tarde estable en torno a 10 u 11 kW.

**El día se fija en el generador y no se busca por código.** Dos asertos
lo comprueban antes de dibujar, que sea posterior al 3 de septiembre y que
ninguna de sus horas llegue al recorte; si dejaran de cumplirse, la
corrida se detiene en vez de publicar una figura que afirma una igualdad
que no se cumple. Hay 70 días hábiles que cumplen las dos condiciones.

**Los dos paneles comparten escala vertical.** Antes tenían escalas
distintas y no se comparaban. El panel del promedio queda con la mitad
superior vacía, que es el precio de poder comparar, y a cambio se ve que
el día escogido repite la forma del promedio con mayor amplitud.

**La caja de estadísticas se retira y en su lugar entra la cuenta en
energía.** Aquella caja citaba hechos de todo el horizonte, 1.517 horas
bajo cero y un mínimo de -33,6 kW, sobre un panel que muestra un perfil
medio, y la correspondencia no era evidente. Las dos cifras siguen
publicadas en la tabla de la subsección de la demanda negativa, y no
se pierde nada. La franja nueva cierra la igualdad sobre las 6.144
horas: 10.606 kWh de lectura del medidor más 32.691 kWh de generación
devuelta más 1.013 kWh de recorte a cero dan los 44.311 kWh de demanda
reconstruida.

**Un hallazgo de la franja.** La nota al pie de la figura dice que la
reconstrucción devuelve 33.705 kWh, y es cierto, pero **esa cifra no es
generación**: son los 32.691 kWh que entregaron los tres inversores más
los 1.013 kWh que añade el recorte a cero. La franja lo separa; la nota
conviene que lo diga.

**Anotaciones retiradas del área de dibujo.** La llamada de cuatro líneas
«el medidor reporta menos energía de la que el edificio gastó» invadía el
panel y su contenido es cosa del pie. El panel izquierdo llegaba a -20 en
el eje con un dato que no baja de -14; ahora el margen se calcula del
dato.

**Cifras nuevas que la figura publica**, todas regenerables desde
`datos_cache/preproceso_m1.npz` y volcadas al `.csv` hermano: 35,1 kW,
10.606 kWh, 32.691 kWh y 44.311 kWh. El recorte de 1.013 kWh ya estaba en
la tabla de la reconstrucción.

**Pendiente**: aplicar el pie nuevo y revisar la nota al pie, que sigue
diciendo «el área beige alcanza su máximo» cuando la generación ya no se
dibuja desde cero.



### Pie y nota aplicados (coordinador, 2026-09-04)

Verificadas contra la cache las cinco cifras que la figura publica, y
cierran: 10.605,83 + 32.691,41 + 1.013,30 = 44.310,54. La altura de la
banda a las 12 del 7 de noviembre es 35,07 kW y ese dia no tiene ninguna
hora recortada.

**El dia lo detecto el autor mirando la figura**: «se ve muy poca demanda
al mediodia, es raro». Tenia razon, y el fallo no era del dibujo. El dia
anterior (2025-07-16) caia en el tramo sin el inversor del proyecto, donde
la suma va incompleta: la demanda reconstruida daba 0,00 kW a las 13 y
1,25 kW a las 15. **La figura ilustraba el metodo con un dia en que el
metodo falla**, y el lector concluia que la reconstruccion estaba rota.

El pie nuevo dice de donde sale el dia, que es lo que evita esa lectura.

**Correccion de la nota.** Decia que la reconstruccion «devuelve 33.705
kWh a la serie de demanda». Es cierto que la levanta en esa cantidad, pero
no todo es generacion: son 32.691 kWh de generacion devuelta mas 1.013 que
proceden del recorte a cero. La franja inferior de la figura los separa y
la nota ahora tambien. Y «el area beige alcanza su maximo» dejo de
describir el dibujo, porque la generacion ya no se traza desde cero.

---

## C-99 · La limpieza pasa a dos figuras, y el cuarto tratamiento resulta no tener ningún caso

**2026-09-04 · tipo: `figura` · aplicada · él aprobó la partición**

Él pidió que después de cada uno de los cuatro pasos de la limpieza hubiera
una figura con un ejemplo real. Se propuso agruparlos en dos y lo aprobó,
porque los pasos segundo, tercero y cuarto operan sobre el mismo objeto,
que es un hueco, y solo se distinguen por su longitud: repartidos en tres
figuras, lo único que los diferencia viajaría entre páginas, que es donde
peor se compara. La subsección se parte en dos, una por idea.

**Lo que la figura antigua no podía sostener.** Su panel izquierdo dibujaba
una línea horizontal sobre las 6.144 horas del horizonte y afirmaba en el
pie que la distancia entre el umbral y la masa de la serie acredita el
criterio. El umbral es el máximo de dos candidatos y el panel dibujaba uno
solo, de modo que no se veía cuál de los dos mandaba ni por qué el máximo
hace falta; y la masa de una serie de 6.144 puntos trazada como línea
continua es una maraña de la que solo se lee la envolvente. Es el defecto
que C-76 midió sobre las barras de cobertura y C-84 sobre la curva de
duración, reaparecido por tercera vez.

**Figura 3.5, el umbral.** A la izquierda, la hora retirada sobre una
ventana de tres días, con el valor que entró, el umbral y el valor con que
quedó, unidos por una cota. A la derecha, una fila por serie con su mitad
central, su cola hasta el máximo observado y los dos candidatos del
umbral. El eje va en múltiplos del percentil 99,5 de cada serie y no en
kilovatios, y la razón está medida: los diez umbrales de la frontera
principal van de 10,2 a 154,8 kW, es decir, más de un orden de magnitud,
de modo que en kilovatios las filas pequeñas no dibujarían ninguna
diferencia. Normalizados, el piso es una sola vertical en 1,2 común a las
diez filas y basta ver a qué lado cae la cerca de Tukey para saber cuál
manda.

**El caso se elige por regla y no a dedo.** Entre las horas retiradas, las
aisladas, y de esas la que más sobresale del umbral en términos
relativos. Sale la del 1 de octubre de 2025 en la Universidad Mariana, que
entra con 39,9 kW frente a un umbral de 35,1 y sale con 28,2 por
interpolación entre sus vecinas. El tramo del 24 de abril queda descartado
por la propia regla, y conviene que así sea: son tres horas seguidas de la
rampa de mañana, la primera sobresale un 1,3 % y enseñaría un criterio
que apenas discrimina.

**Manda la cerca en 16 de las 20 series y el piso en 4**, todas de
demanda, que son Mariana y CESMAG en las dos fronteras. Lo que el piso
evita está medido: sin él, la demanda de CESMAG perdería 451 horas en M1
y 927 en M3, es decir, el 20,7 % y el 52,5 % de su energía.

**Figura 3.6, la escalera.** Tres huecos reales de longitud creciente, con
el eje horizontal en horas desde el inicio del hueco, que es la magnitud
de la que depende la regla. Los tres van fijados en el generador y
comprobados con asertos de longitud y de reparto antes de dibujar, como el
día de la reconstrucción en C-96, y el tercero se comprueba además contra
el hueco más largo de su frontera. Abajo, el presupuesto de horas por
institución.

**La cascada no clasifica huecos por longitud: actúa hora a hora dentro de
cada uno.** El texto anterior decía que los huecos de hasta 3 horas se
interpolan y los de hasta 24 se rellenan con el vecino, como si fueran
casos disjuntos, y no lo son. Un hueco de 13 horas sale con sus 3 primeras
horas interpoladas y las 10 restantes arrastradas. Y el arrastre propaga
la tercera hora interpolada, no la última lectura observada: en el hueco
del 12 de diciembre la meseta se queda en 10,09 kW cuando la última
lectura fue 9,89, es decir, en un valor que ninguna hora observada tuvo.
La figura lo dibuja con una referencia punteada, y solo cuando la
separación pasa del 4 % del alto del panel, porque por debajo de eso las
dos líneas se imprimirían una encima de la otra.

**El cuarto tratamiento no tiene ningún caso, y eso es el hallazgo.** La
cascada alcanza 51 horas, que son 3 de interpolación más 24 de arrastre
hacia adelante más 24 hacia atrás, y el hueco más largo del estudio mide
49, en la demanda de la UCC bajo M3, entre el 11 y el 13 de diciembre. En
las 20 series de las dos fronteras hay cero horas rellenas con cero. Se
publica como cifra, con el mismo recurso que C-81 usó para los instantes
repetidos sin discrepancia, y no se omite. De paso cae la frase que
atribuía ese relleno a las horas nocturnas de la generación: las diez
series de generación no reciben ningún tratamiento en ninguna de las dos
fronteras.

**El panel mensual se retira.** El mes no es la variable que decide el
tratamiento, la longitud del hueco sí, y el cuándo ya lo lleva el Gantt de
cobertura del Capítulo 2. En su lugar entra el reparto por mecanismo, que
es lo que la subsección explica: en M1, 74 horas interpoladas y 160
arrastradas; en M3, 159 y 415. El arrastre es el 71,2 % de todo lo
tratado.

**Compuerta.** Las dos figuras replican la limpieza del pipeline paso a
paso y comparan la serie resultante contra la del propio pipeline antes de
dibujar: si `max|dif|` dejara de ser cero, la corrida se detiene en vez de
publicar una figura que describe otro cálculo.

**Comprobaciones de cierre.** Cero solapamientos de rótulo en las cuatro
figuras, medidos sobre el render y descontando las marcas de eje que
matplotlib conserva fuera del rango visible. Conversión a escala de
grises: la distinción la llevan la geometría, que es rampa frente a
meseta, y la forma del marcador, que es círculo, cuadrado y triángulo, de
modo que no se pierde nada. Los CSV hermanos tienen 11 y 9 filas.

**Dos defectos de composición que la prueba de oclusión cazó y que se
anotan porque son recurrentes.** La leyenda de figura fijada a una altura
elegida a ojo se imprimía sobre los dos rótulos de eje; ahora se coloca
después de componer y por debajo del rótulo más bajo, medido sobre el
render. Y la cabecera de la columna de umbrales, puesta dentro del área de
dato, caía sobre la cifra de la primera fila.

**Cifras nuevas que las figuras publican**, todas regenerables desde el
caché de estados intermedios y volcadas a los CSV hermanos: los diez
umbrales de cada frontera con sus dos candidatos, las 4 y 7 horas
retiradas, el reparto por mecanismo de las 234 y 574 horas tratadas, el
hueco más largo de cada frontera y las tres ternas de reparto de los
peldaños.

**Pendiente**: el texto de las dos subsecciones nuevas, que redacta el
coordinador, y retirar los seis archivos de la figura antigua
(`f3_05_outliers_imputacion_{m1,m3}` con su PNG, su CSV y su fuente) en
cuanto la fuente del capítulo deje de citarlos.

---

## C-101 · El umbral gana una figura de anatomía, y el par que hace el argumento

**2026-09-04 · tipo: `figura` · aplicada · él pidió que el rango intercuartílico se entendiera de forma gráfica en cada factor**

> Es el mismo cambio que registra C-102, visto desde el generador. C-102
> es la entrada de referencia; esta añade el detalle de implementación y
> las comprobaciones. La figura pasó después a las diez series por C-104,
> que retira de aquí la nota del par y los rótulos de valor.

La figura del umbral dice quién manda en cada serie, pero no cómo se
construye ninguno de los dos candidatos. El lector veía `Q75 + 5 · IQR`
como notación y en ningún sitio veía el rango intercuartílico como lo que
es, es decir, una longitud que se multiplica por cinco y se apila sobre el
tercer cuartil. Entra una figura antes que aquella, dedicada solo a la
anatomía de la fórmula.

**El recurso central son las cinco copias.** La caja de la mitad central se
dibuja una vez sobre el tercer cuartil y luego cinco veces más encima,
todas del mismo ancho y del mismo alto, numeradas. La multiplicación deja
de ser una operación y pasa a ser una distancia que se cuenta con el ojo.
Al lado, la cola: una línea de puntos que sube desde el tercer cuartil
hasta el percentil 99,5 y, sobre ella, el bloque de su prolongación del
20 %. El máximo de la fórmula se lee entonces sin aritmética, porque gana
el que queda más alto y es el que va pintado en ámbar y con trazo lleno,
mientras el que pierde queda en gris y discontinuo.

**Es la prueba geométrica del mecanismo que C-100 identificó.** Allí quedó
medido que el peligro no lo trae el rango intercuartílico pequeño, porque
el Hospital tiene el menor de todo el estudio y no le pasa nada, sino el
perfil de dos modas. Esta figura lo dibuja.

**El par que hace el argumento.** El Hospital y CESMAG tienen rangos
intercuartílicos casi iguales en la frontera principal, \uni{1.4}{kW} y
\uni{1.3}{kW}, es decir, una diferencia del \pct{10}, y sin embargo el
umbral de cada uno lo fija un criterio distinto. Lo que los separa no es
la dispersión del cuerpo sino dónde cae la cola respecto de él: el
percentil 99,5 del Hospital está a 1,2 rangos por encima de su tercer
cuartil y el de CESMAG a 8,2. Eso es la bimodalidad que el texto afirmaba
y que hasta ahora no se veía. La tercera serie, la UCC, es el contraste de
escala: rango intercuartílico de \uni{24.4}{kW}, el más ancho de las
cinco, y el primer criterio gana con holgura.

**La frase del par solo se imprime cuando es cierta.** La razón entre los
dos rangos se calcula y se compara contra 1,15: en la frontera principal
vale 1,10 y la figura lo dice; en la otra vale 1,76 y la figura calla. El
argumento del par es de M1, y la nota no se hereda a M3 escribiéndola a
mano.

**Escalas independientes, y por qué no es una trampa.** Los rangos van de
1,3 a 24,4 kW en la frontera principal, de modo que una escala común
aplastaría tres de las cinco series. Lo que se compara entre paneles no es
una altura sino una relación, que es si la cola con su prolongación queda
por encima o por debajo de la quinta copia. Esa relación es invariante a
la escala de cada panel.

**Lo que la frontera M3 enseña de más.** En CESMAG la cola cae a 23,2
rangos del cuerpo y el cuerpo mide \uni{0.6}{kW}, de modo que la pila de
seis cajas ocupa la parte baja del panel y la línea de puntos lo recorre
entero. Los ordinales de las copias no se imprimen ahí, porque cada una
mide menos de nueve puntos tipográficos y el número saldría fuera de su
caja; la condición se evalúa sobre la geometría del render y no se decide
a ojo. El panel se ve extremo porque el caso lo es, y es justo el caso que
explica que sin el segundo criterio esa serie perdería 927 horas, es
decir, el \pct{52.5} de su energía.

**Numeración.** El archivo es `f3_04b_anatomia_umbral`, con la letra que ya
usan otras cuatro figuras del capítulo, y no `f3_04`: el número 3.4 lo
ocupa el diagrama de los tres tipos de medidor, que se dibuja en LaTeX y
por eso no tiene archivo, y dos filas con el mismo número en la tabla
maestra se prestan a error. La letra deja la figura donde va, que es
después de aquel diagrama y antes de la del umbral.

**Vocabulario.** Se usan «primer criterio» y «segundo criterio», que es la
denominación que el texto acaba de fijar. El percentil se marca con una
raya y no con un círculo hueco, porque el círculo hueco significa otra
cosa en la figura siguiente, que es el corte del primer criterio, y dos
figuras vecinas no pueden dar dos sentidos a la misma marca.

**Un defecto que el cambio de vocabulario introdujo en la figura vecina.**
Al renombrar el segundo criterio, su rótulo pasó a medir 1,13 pulgadas,
que es exactamente lo que hay entre su vertical y la columna de umbrales
en kilovatios, y se imprimía sobre la cifra de la primera fila. La prueba
de oclusión lo cazó. El nombre baja a la leyenda, que pasa de cuatro
entradas a cinco.

**Comprobaciones de cierre.** Cero solapamientos de rótulo en las seis
figuras de la etapa. Escala de grises: la caja medida y sus copias se
distinguen por el relleno y por el borde, y los dos criterios por trazo
lleno frente a discontinuo. El CSV hermano tiene cinco filas, una por
institución, con las dos que no se dibujan marcadas como tales.

**Cifras que la figura publica**, todas regenerables desde el caché: por
institución, los dos cuartiles, el rango intercuartílico, los dos
candidatos, el percentil 99,5, el umbral aplicado, el máximo observado y a
cuántos rangos del tercer cuartil cae la cola.

---

## C-104 · La anatomía del umbral pasa a las diez series, porque la tabla se quedó con los valores

**2026-09-04 · tipo: `figura` · aplicada · él pidió las cinco entidades en las dos fronteras, en una sola imagen · continúa C-102 y usa la tabla de C-103**

Lo que ataba la figura a tres paneles no era el argumento sino los
rótulos: cada uno arrastraba los dos candidatos con su fórmula y su valor,
y esos rótulos ocupaban más ancho que el dibujo. La tabla del umbral, que
C-103 publicó, cambia el reparto: **la tabla lleva los valores y la figura
se queda con la geometría.** Sin rótulos largos caben diez paneles donde
antes cabían tres, y Udenar y la Universidad Mariana dejan de faltar
también en la figura.

**La retícula.** Dos filas por cinco columnas, las instituciones en el
orden fijo a lo ancho y las fronteras apiladas, de modo que comparar una
institución entre M1 y M3 sea mirar hacia abajo. La frontera rotula la
fila entera, en su color y con su razón entre generación y consumo, fuera
del área de dato. En cada panel queda escrito lo que identifica y lo que
la escala no dice: el nombre de la institución, una vez por columna, y el
rango intercuartílico.

**Los ordinales sobreviven, y se decidió midiendo.** Con diez paneles cada
uno queda en 1,2 pulgadas de ancho por 1,8 de alto, de modo que había que
comprobar si el número de cada copia seguía cabiendo. La condición se
evalúa sobre el render ya compuesto, con la posición real del eje después
de componer y no con la que tiene antes: **se imprimen 45 de los 50**, y
los cinco que faltan son los de CESMAG bajo M3, donde cada copia mide 3,6
puntos tipográficos. Se conserva la numeración porque sobrevive en nueve
de los diez paneles; si hubiera caído en la mayoría, habría que haberla
sustituido por una sola marca al margen de cada pila.

**Un solo archivo, sin sufijo de frontera.** La figura cubre las dos, de
modo que `f3_04b_anatomia_umbral_m1` sería un nombre falso y el generador
emitiría dos archivos idénticos. La función ya no recibe cobertura.

**Lo que se retira.** La nota que declaraba el par del Hospital y CESMAG:
esa comparación la sostienen ahora dos columnas contiguas y la publica la
tabla con sus cifras. Con ella sale la condición que solo la imprimía
cuando la razón entre los dos rangos bajaba de 1,15. También salen los
rótulos de valor de cada panel y la selección de tres series con sus
asertos, que ya no tiene objeto.

**Lo que este cambio NO resuelve, con la medida que faltaba.** El reparo
del tamaño del cuadro que C-103 dejó abierto sigue en pie, y ahora se
puede cuantificar sobre las diez series: los rangos reales difieren por un
factor de **76,7**, de 24,35 kW en la UCC bajo M1 a 0,318 kW en el
Hospital bajo M3, mientras que la altura con que se dibuja el cuadro solo
difiere por un factor de **5,5**, del \pct{15.1} del panel al \pct{2.7}.
La compresión no es un descuido del dibujo sino la consecuencia aritmética
de la escala independiente: cuando manda el primer criterio la pila ocupa
casi todo el panel y el cuadro es un sexto de ella, sea cual sea el rango.
Con diez paneles el efecto se nota más que con tres, porque hay más pilas
parecidas a la vista. **No se toca a la espera de su decisión**, que es lo
que C-103 dejó dicho; de las tres salidas propuestas allí, la viñeta con
los rangos sobre un eje común es la única que no obliga a renunciar a las
escalas independientes.

**Comprobaciones de cierre.** Cero solapamientos de rótulo. Escala de
grises: el criterio que fija el umbral se distingue del descartado por
trazo lleno frente a discontinuo, y las tres marcas horizontales por su
longitud y su posición, que es el ancho del panel para los criterios, el
carril de la cola para el percentil y el carril del cuadro para el máximo.
El CSV hermano tiene diez filas, una por serie y frontera.

**Ninguna cifra nueva respecto de la tabla.** El CSV añade los dos
cuartiles y el máximo observado, que la tabla no trae y que la figura sí
dibuja.

---

## C-105 · La escalera pasa a las dos fronteras, porque la versión de M1 sostenía una lectura falsa

**2026-09-04 · tipo: `figura` + `dato` · aplicada · criterio general del autor, reportar todos los datos para todas las entidades**

La franja del presupuesto de la versión de M1 imprimía «ninguna» junto a
Udenar y a la UCC, y esa palabra es falsa como afirmación sobre el dato:
bajo M3 esas dos instituciones acumulan 97 y 126 horas tratadas. La causa
está declarada en el capítulo y es H-25: en la frontera principal las dos
llevan medidor neto y el recorte a cero de la reconstrucción cierra sus
huecos antes de que la limpieza los vea. Un lector que solo viera M1
concluiría que no tuvieron cortes, y los tuvieron.

**La franja pasa a las diez series de demanda**, cinco instituciones con
sus dos fronteras en barras contiguas, de modo que el contraste entre 0 y
97 esté en el mismo renglón. La frontera de cada barra va rotulada en su
color a la izquierda del origen.

**Los ceros dejan de leerse como ausencia.** Donde no hay barra, el rótulo
dice «0 · huecos cerrados antes» en el color de aviso, y bajo la franja
una línea explica de qué cero se trata: en M1, Udenar y la UCC llevan
medidor neto y la reconstrucción cerró sus huecos antes de la limpieza. La
nota va en la figura y no solo en el pie, porque quien mira el dibujo
tiene que poder leerla ahí.

**El tercer peldaño cambia de caso.** Al dejar de haber una figura por
frontera, ya no es «el hueco más largo de esta frontera» sino el más largo
del estudio, que son las 49 horas de la demanda de la UCC bajo M3, del 11
al 13 de diciembre, con su reparto de 3 más 24 más 22. Es además el que
cierra el argumento, porque prueba que ni el mayor de todos alcanza el
techo de 51 horas. Un aserto comprueba que sigue siendo el más largo de
las dos fronteras, no solo de la suya. Los dos primeros peldaños siguen
siendo del Hospital bajo M1, y cada panel declara ahora su frontera,
porque los tres ya no salen de la misma.

**Por qué los dos primeros se quedan en M1.** El hueco de tres horas sube
un \pct{30} entre sus anclas bajo M1 y baja un \pct{3} bajo M3, de modo
que allí la recta de la interpolación no se distinguiría de una línea
plana. El de trece horas se lee en las dos: la separación entre la meseta
y la última lectura observada mide el \pct{13.7} del alto del panel bajo
M1 y el \pct{21.4} bajo M3. Se conservan los dos de M1 para que los
peldaños primero y segundo pertenezcan al mismo medidor; si se prefiere la
separación mayor, el segundo puede pasar a M3 cambiando una línea.

**Un archivo, sin sufijo**, porque la figura cubre las dos fronteras y la
función ya no recibe cobertura. Se retiran los dos anteriores.

**Un defecto de composición corregido de paso.** La banda de las llaves
queda bajo el dato y no es área de medida, pero el eje seguía imprimiendo
sus marcas dentro de ella: en el hueco de 49 horas la marca del cero caía
en la banda e invitaba a leer que la serie había bajado hasta ahí. Las
marcas se recortan al recorrido del dato.

**Comprobaciones de cierre.** Cero solapamientos de rótulo en las cuatro
figuras de la etapa. Escala de grises: la geometría sigue llevando la
distinción, que es rampa frente a meseta en los paneles y orden fijo de
los dos tramos en la franja. El CSV hermano tiene catorce filas, tres de
peldaño, diez de presupuesto y una de resumen.

**Cifras que la figura publica**, todas verificadas contra el caché antes
de dibujar: 234 horas tratadas en M1, de ellas 74 interpoladas y 160
arrastradas, y 574 en M3, de ellas 159 y 415; el reparto por institución
de la tabla de arriba; cero horas rellenas con cero en las veinte series;
y el hueco más largo del estudio en 49 horas frente a un alcance de 51.

---

## C-107 · La demanda negativa y la profundidad pasan a las dos fronteras, y una de ellas comparaba objetos distintos

**2026-09-04 · tipo: `figura` + `dato` · aplicada · aplica a estas dos piezas el criterio que registra C-106**

Las dos figuras de la demanda negativa se funden en una, con una fila por
frontera, y la de la profundidad pasa a dos paneles. Se mantienen como
figuras separadas y no se funden entre sí: la primera queda ya con dos
filas de dos paneles y meterle una tercera pieza la haría ilegible.

**Un defecto que la fusión destapó.** En la versión secundaria de la
demanda negativa la curva destacada era el mínimo de cada hora, porque
allí ningún promedio baja de cero, mientras que las cuatro de contexto
seguían siendo promedios, y nada en la figura lo decía. Eran objetos
distintos comparados en el mismo par de ejes, que es lo que C-84 dejó
prohibido. Ahora cada fila dibuja las dos curvas de la institución
afectada, promedio y mínimo de cada hora, rotuladas, sobre cuatro
promedios de contexto.

**Por qué caben las dos curvas, medido.** Dibujar el mínimo estira el
recorrido vertical de la fila principal de 42,3 a 64,9 kW, es decir, un
factor de 1,53, y la excursión negativa del promedio de Udenar pasa de
ocupar el \pct{25.9} del alto de su panel a ocupar el \pct{16.9}. Sigue
siendo legible, de modo que no hay que elegir entre las dos lecturas: se
ve que el neteo arrastra la media entera de una institución y se ve hasta
dónde llega el caso extremo. En la frontera secundaria la relación es la
misma con otro reparto, 3,59 a 5,97 kW, y allí el promedio se queda
fuera de la zona imposible, que es justamente lo que esa fila enseña.

**Lo que cada figura conserva y lo que suelta.** La tabla de los tipos ya
publica, en las dos fronteras, las horas bajo cero de cada institución, su
fracción, la lectura mínima y la energía hacia la red. Ninguna de las dos
figuras repite esas columnas. La de la demanda negativa se queda con la
forma de la campana solar y con el único valor que no está en la tabla,
que es el mínimo del promedio horario, \uni{-11.0}{kW} a las 13 en Udenar.
La de la profundidad se queda con a qué profundidad ocurre la inversión de
ordinario frente a ese mínimo que es un extremo: la mitad central de las
negativas de Udenar cae entre −15,1 y −3,9 kW con mediana de −8,7,
mientras el mínimo publicado, −33,6, es casi cuatro veces esa mediana.

**El vacío de la frontera secundaria es el hallazgo.** Bajo M3 solo la
Universidad Mariana cruza el cero, y con un recorrido de \uni{-0.72}{kW}
frente a los \uni{-33.57}{kW} de Udenar bajo M1. Los otros cuatro
circuitos nunca se acercan. La figura lo hace visible dejando cuatro filas
enteras a la derecha del cero y rotulando la banda vacía, en vez de
disimularlo. La razón está declarada en el capítulo y es que la
Universidad Mariana no tiene medidor secundario y se representa escalando
su totalizador.

**Las dos escalas de la profundidad son independientes, y tienen que
serlo.** El recorrido dibujado abarca 51 kW en la frontera principal y 3,8
en la secundaria, un factor de 13. Con escala común las cinco filas de la
derecha cabrían en el \pct{7} del ancho y la figura no podría dibujar lo
que afirma. Es la misma razón que en la anatomía del umbral, y como allí,
lo que se compara entre paneles no es una longitud sino una relación: si
el recorrido cruza el cero o no.

**Tres rótulos recolocados sobre el render.** La glosa de la zona
imposible la cruzaban las dos curvas, porque el mínimo de cada hora
recorre la banda entera de las 6 a las 18; queda reducida a dos palabras
en el único hueco, que son las horas de noche, y la glosa pasa al pie. El
rótulo del promedio que no entra en la zona imposible se imprimía sobre la
leyenda; va sobre el tramo final de su propia curva. Y en la profundidad,
el rótulo del panel derecho no cabía horizontal en ninguna fila sin tocar
un recorrido, de modo que va girado dentro de la banda; la prueba de
oclusión lo cazó contra el de CESMAG.

**Una cabecera nueva.** La columna de tipos del panel izquierdo cae en el
hueco entre los dos paneles y podía leerse como propia del derecho. Lleva
ahora cabecera, y dice que el tipo es de la frontera principal.

**Un archivo cada una, sin sufijo**, y las funciones dejan de recibir
cobertura. Se retiran los tres anteriores.

**Comprobaciones de cierre.** Cero solapamientos de rótulo en las seis
figuras de la etapa. La compuerta de asertos de la profundidad se extiende
a la segunda frontera: conteos, mínimos, medianas de las negativas y sus
cajas, más la comprobación de que allí cruza el cero una sola institución.
Escala de grises: la identidad de cada fila la llevan su rótulo y su
posición, no el color. Los CSV hermanos tienen 82 y 10 filas.

**Un fallo de la prueba de oclusión, anotado porque es de la misma familia
que el de C-84.** Un eje gemelo, el que aloja la columna de tipos, oculta
su eje horizontal pero conserva los objetos de marca, de modo que la
prueba los encontraba solapados consigo mismos y daba seis choques
inexistentes. La prueba salta ahora los ejes cuyo eje no está visible.

---

## C-111 · El mosaico de la reconstrucción, y una banda que no existía

**2026-09-04 · tipo: `figura` + `dato` · aplicada · él pidió la reconstrucción de todas las entidades en un mosaico aparte**

Entra `f3_03b_reconstruccion_mosaico`, diez paneles con el perfil medio
horario de las 6.144 horas, cinco instituciones por dos fronteras. La
figura del caso, el viernes de Udenar hora a hora, se queda intacta: son
dos trabajos distintos, y el del mosaico es enseñar a quién se le aplica la
reconstrucción y a quién no.

**Siete paneles de diez salen sin banda, y ese es el contenido.** En la
frontera principal el Hospital y CESMAG entregan lectura bruta y no hay
generación que devolverles; en la secundaria no la entrega ninguno de los
cinco. La fila de abajo es el control de la de arriba: prueba de un
vistazo que la reconstrucción es un asunto de la frontera principal, que
es algo que el capítulo venía afirmando en prosa. Para que ese vacío no se
lea como una figura a medio hacer, cada panel dice lo que le pasa: los
tres que reciben generación llevan cuánta, y los otros siete dicen que su
medidor no netea.

**Una banda que no existía, y por qué apareció.** La primera versión
dibujaba banda en los siete paneles planos, de 0,10 kW en el Hospital y
0,04 en CESMAG. No era generación devuelta: la serie reconstruida conserva
el hueco donde el medidor no trajo lectura y no hay nada que sumarle,
mientras que la de la lectura lo lleva relleno con cero, de modo que las
dos curvas se estaban promediando sobre conjuntos de horas distintos, 113
y 117 horas de diferencia. Ahora las dos se promedian sobre el mismo
relleno y las curvas coinciden exactamente donde tienen que coincidir, lo
que a su vez pasa a comprobarse con un aserto.

**Un aserto que no comprobaba lo que decía, anotado porque es de la misma
familia que el `assert ... or True` de C-84.** La comprobación de la
identidad de la reconstrucción usaba el máximo de pandas sobre una
diferencia con huecos, y el máximo de pandas los descarta en silencio: la
prueba se saltaba justo las horas que aquí importaban. Ahora se compara
sobre las series ya rellenas y se exige además que la diferencia sea
finita en las 6.144 horas.

**Un caso intermedio que la revisión destapó.** Bajo M3 la Universidad
Mariana no recibe generación pero la reconstrucción todavía muerde,
porque el recorte a cero le quita 46,7 kWh, que son los mismos 156 de la
frontera principal escalados. Su panel lo dice, y no se le pone la
etiqueta de los otros seis.

**Escalas verticales independientes por panel.** Medido sobre los perfiles
medios: con una escala común a los diez, el recorrido entero del Hospital
ocuparía el \pct{4.8} del alto de su panel y el de CESMAG el \pct{10}, de
modo que las filas quedarían planas por aplastamiento y no por ausencia de
banda, que es justo la distinción que la figura existe para enseñar. Lo
que se compara entre paneles no es una altura sino si hay banda o no, y
eso no depende de la escala. La energía devuelta va escrita en cada panel
para que el ancho de la banda no se lea como magnitud.

**Numeración.** El prefijo `f3_03b` estaba libre en disco y el número 3.3b
no lo ocupa ningún diagrama de LaTeX; los dos que dibuja el capítulo son
el del canal y el de los tipos de medidor. La comprobación se hace ahora
siempre, después de lo que pasó con `f3_04`.

**Comprobaciones de cierre.** Cero solapamientos de rótulo en las siete
figuras de la etapa. Escala de grises: la banda se distingue de las dos
curvas por relleno frente a trazo, y las curvas entre sí por grosor. El
CSV hermano trae los diez perfiles dibujados y el resumen por institución.

**Cifras que la figura publica y que no estaban.** La generación devuelta
por institución, las horas en que se devuelve y el recorte de cada una:
Udenar 32.691,4 kWh en 3.261 horas con recorte de 1.013,3; la Universidad
Mariana 12.549,1 en 3.265 con 0,6; la UCC 15.378,0 en 3.209 sin recorte;
el Hospital y CESMAG, nada. Y en la frontera secundaria, cero en las cinco
salvo el recorte de 46,7 kWh de la Universidad Mariana.

---

## C-115 · El panel del criterio se retira: hacía lo que hace la anatomía, y peor

**2026-09-04 · tipo: `figura` · aplicada · él dijo que la figura no se entendía**

La figura del umbral tenía dos paneles y el problema estaba entero en el de
la derecha, el del criterio de las diez series. Se retira, y la figura
queda en el caso, que es lo único que no hace ninguna otra pieza. Pasa a
llamarse `f3_05_umbral_caso` y funde las dos fronteras en un archivo, con
una fila cada una.

**Las cinco razones, y las tres primeras son de lectura.** El eje decía
«múltiplos del percentil 99,5 de la propia serie», es decir, que cada fila
usaba su propia normalización, de modo que un eje compartido invitaba a
comparar magnitudes que no lo son: el 2,37 de la UCC y el 1,35 de CESMAG
no significan lo mismo. El círculo del corte del primer criterio solo
asomaba en dos filas de diez, porque en las otras ocho coincide con el
rombo y quedaba debajo, sin que nada lo advirtiera. Y el rombo se llamaba
umbral aplicado pero su posición no era el umbral sino el umbral dividido
por el percentil de su serie, de manera que **el mismo objeto aparecía dos
veces, dibujado y en la columna del margen, con dos valores distintos y
ninguna relación visible entre ellos**; la cifra del margen, que es la
única comparable entre filas, no era la que estaba dibujada.

**La quinta es la decisiva.** La anatomía del umbral construye los dos
candidatos en kilovatios reales, con las cinco copias apiladas, para las
diez series y las dos fronteras, y la tabla del umbral publica los valores.
Aquel panel era una versión comprimida y normalizada de lo mismo. Llegó
antes que las otras dos piezas y se quedó por inercia.

**El caso se sigue eligiendo por regla y no por fecha.** Entre las horas
retiradas se toman las aisladas y de esas la de mayor exceso relativo
sobre el umbral. Bajo las dos fronteras sale la misma hora, el 1 de
octubre en la Universidad Mariana, que es lo esperable porque su serie
secundaria es la principal escalada: entra con \uni{39.9}{kW} sobre un
umbral de \uni{35.1}{kW} y sale con \uni{28.2}{kW} en la principal, y con
\uni{10.3}{kW} sobre \uni{9.1}{kW} para salir con \uni{7.2}{kW} en la
secundaria.

**Y se prepara para que ese caso desaparezca.** Está abierta la decisión de
llevar el multiplicador del primer criterio de 5 a 7, y con 7 la frontera
principal no retiraría ninguna hora, de modo que su panel se quedaría sin
objeto. En vez de fallar, el panel imprime que esa frontera no tiene
ninguna hora retirada; la corrida solo se detiene si no la tuviera ninguna
de las dos. Comprobado forzando el caso vacío: la figura se dibuja igual.

**Dos asertos nuevos sobre lo que se dibuja.** Que la hora sobresale del
umbral, y que el valor con que quedó es el punto medio de sus dos vecinas.
Lo segundo se sigue de la primera regla: al exigir que la hora esté
aislada, el hueco que deja mide una hora y la interpolación lo cierra por
la recta entre las dos anclas. Si algún día dejara de cumplirse, sería que
el caso no es el que la figura dice.

**Un rótulo colocado midiendo.** El de la frontera se sitúa a partir de la
caja real del eje y no a una fracción fija: los dos paneles tienen marcas
de distinto ancho y a fracción fija el rótulo se montaba sobre el del eje.
La prueba de oclusión lo cazó en las dos filas.

**Comprobaciones de cierre.** Cero solapamientos en las seis figuras de la
etapa. El CSV hermano tiene dos filas, una por frontera. Se retiran los dos
archivos anteriores.

## C-116 · La subseccion de los huecos, reorganizada, con diagrama de flujo

**2026-09-04 · tipo: `contenido` · aplicada**

El autor: «parecen parrafos tirados que no son capaces de entenderse por
si mismos». Seis defectos, y dos de bulto.

**El de bulto primero: dos reparticiones del mismo total con cifras casi
iguales y sin decir que eran distintas.** El texto imprimia 233
interpoladas y 575 arrastradas, que es el reparto por mecanismo, y dos
parrafos despues 234 bajo M1 y 574 bajo M3, que es el reparto por
frontera. Las cuatro cifras son correctas, comprobadas contra el cache,
pero puestas asi el lector concluye que hay una errata. Pasan a una tabla
de doble entrada, `tab:prep-huecos`, donde reconcilian por suma en los dos
sentidos: 74 + 160 = 234, 159 + 415 = 574, 233 + 575 = 808.

**El segundo de bulto: anunciaba cuatro tratamientos y no los listaba.**
Los parrafos siguientes los describian sin numerarlos, de modo que la
cuenta anunciada no se cerraba nunca. Van a lista enumerada, contra la
regla de que una cuenta anunciada es una lista.

**Diagrama de flujo nuevo, `fig:prep-cascada`.** El autor lo pidio. Sitúa
los cuatro tratamientos sobre las horas de un hueco de 51 horas, con la
flecha de cada arrastre indicando desde que lado propaga. Hace visible de
una vez lo que la prosa tardaba tres parrafos en decir: 3 + 24 + 24 = 51,
y el cuarto tratamiento apagado porque no llega a actuar.

**Cuatro defectos menores.** La advertencia mas dificil, que el
tratamiento se decide hora a hora y no hueco a hueco, llegaba antes de que
existiera un tratamiento del que hablar. Un acertijo: «el valor que se
repite no es el que cabria esperar» decia lo que no es antes de lo que es.
Decia que las 808 horas se reparten entre las 20 series y dos parrafos
despues decia que la generacion no se toca: viven enteras en las 10 series
de demanda. Y la base del porcentaje no estaba nombrada: las 30.720 horas
son las cinco series de demanda de una frontera, no las diez de la
frontera.

## C-117 · La zona horaria deja de ser etapa y su comprobacion se salva

**2026-09-04 · tipo: `estructura` · aplicada**

El autor propuso borrar la subseccion entera y sacarla del diagrama de
fases. Tiene razon en lo de la etapa: localizar un indice no altera ningun
valor, y en un documento que muestra que le pasa al dato, una etapa que no
le hace nada no es una etapa.

Pero dentro habia una medida que carga peso y que ademas estaba
duplicada. La caja de lectura de las matrices ya AFIRMA que un error de
zona horaria desplazaria la banda solar; la subseccion lo MEDIA. Eran el
mismo argumento partido en dos sitios. La comprobacion se muda a la
subseccion de las matrices, junto a la figura que la ensena, y lo demas se
va: el aparato del horario de verano, cuyas dos salvaguardas nunca llegan
a ejecutarse en Colombia, y la lista de argumentos dependientes, que era
el texto hablando de si mismo.

El pipeline pasa a **cinco etapas**. Corregidas las seis menciones a la
cuenta, el rotulo del carril, el fondo del carril y las flechas del
diagrama. Se retira ademas el parrafo que repartia subsecciones por etapa:
era el texto describiendose a si mismo y ya estaba desfasado, porque decia
que las tres ultimas ocupan una subseccion cada una y la de atipicos y
huecos ocupa dos.

## C-118 · La comprobacion de la zona horaria, sobre una medida que no se voltea

**2026-09-04 · tipo: `numerica` · aplicada**

Al mudar la comprobacion escribi que el maximo de generacion cae entre las
11 y las 12. Es cierto, pero **por 0,09 kW**: el intervalo de las 11 vale
33,30 kW y el de las 12 vale 33,21 kW, un margen del 0,3 %. Cualquier
retoque menor del preprocesamiento lo voltea y obliga a reescribir la
frase. Y como los intervalos van etiquetados por su borde izquierdo,
«entre las 11 y las 12» significa de 11:00 a 13:00, que no es lo que el
lector entiende.

Pasa a la hora media ponderada por la energia, que no tiene esa
fragilidad: **12:06 en la comunidad y entre las 12:03 y las 12:11 en las
cinco instituciones**, identica en las dos fronteras porque la generacion
es la misma serie en las dos. Es ademas mas fuerte, porque el mediodia
solar de Pasto cae justo ahi.

## C-119 · Las quince atribuciones de fuente que quedaban

**2026-09-04 · tipo: `norma` · aplicada**

La regla dice que la atribucion de fuente no se imprime, y sobrevivian
quince «Elaboracion propia» dentro de notas de figura, en los capitulos 3,
4, 5 y el anexo A6. Retiradas todas.

**Con un incidente que conviene dejar anotado.** El primer barrido uso
`[^.}]*` para acotar la frase, y el punto de «precios\_bolsa\_xm\_api.csv»
cerraba la coincidencia antes de tiempo: se comio el `\file{` y dejo el
cierre huerfano en cuatro notas. Cuatro errores «Too many }'s» en la
compilacion. Se revirtieron los tres ficheros afectados con la compuerta
de control de versiones, y el barrido se rehizo con una compuerta de
cuadre de llaves antes de escribir. **Leccion: un barrido con expresion
regular sobre LaTeX comprueba el cuadre de llaves antes de guardar.**


---

## C-120 · Los dos mapas de calor se retiran: no podían sostener las tres comprobaciones que se les atribuían

**2026-09-05 · tipo: `figura` + `dato` · aplicada · tres agentes la auditaron por separado y coinciden**

`f3_07_matrices` se rehace entera. Los dos mapas de hora contra día daban
0,21 mm de papel por día, de modo que un fin de semana medía 0,43 mm: el
eje de días no era legible, era una trama. Y ninguna de las tres
comprobaciones que la caja de lectura les atribuía se podía hacer sobre
ellos con una vara.

**Las tres, una por una.** La zona horaria se juzgaba a ojo entre dos
marcas separadas 17,7 mm. El difuminado de la banda solar no tenía unidad,
y además un desfase sistemático la *desplaza* en vez de difuminarla, de
manera que la imagen no separaba las dos hipótesis que decía separar. Y la
semana laboral es una estructura diaria que sobrevive a cualquier error de
agregación horaria, de modo que el criterio y su prueba no hablaban de lo
mismo: barajar los 256 días al azar da una imagen indistinguible de la
real.

**Dos defectos más.** Todo iba codificado en luminosidad, que es el peor
canal para juzgar cantidad, y la figura llevaba una nota advirtiendo que
sus dos escalas no son comparables, advertencia que en gris deja de
funcionar porque lo único que avisaba de las dos escalas era el tono. Y la
generación es byte a byte idéntica en las dos fronteras, de modo que medio
panel se dibujaba dos veces para nada.

**Lo que entra.** Tres bandas que comparten el eje de días, de manera que
una anomalía se lee verticalmente en las tres a la vez, y cada una con su
vara dibujada:

- **El mediodía medido contra el solar.** Para cada día, la hora media de
  la generación ponderada por la energía, y encima la curva del mediodía
  solar de Pasto calculada desde la longitud y la ecuación del tiempo, que
  es una referencia externa al dato y por tanto no circular. Dos reglas a
  una hora de esa curva, que es lo que valdría un huso mal puesto. El
  desfase medio es de \uni{2.4}{min} y 253 de los 255 días con generación
  caen dentro de la vara; los dos que se salen se fijan al borde con otra
  marca en vez de ocultarse, y los dos son días con horas repuestas, cosa
  que la tercera banda enseña en la misma vertical.
- **Qué fracción del día cubre el sol.** La razón entre generación y
  demanda del día, que es adimensional y por eso admite las dos fronteras
  en un mismo eje, cosa que los kilovatios no. La mediana diaria vale 0,20
  en M1 y 1,01 en M3, y M3 pasa de 1 en 129 de los 256 días mientras que
  M1 no lo pasa ninguno.
- **Las horas que la limpieza repuso**, en mariposa, hacia arriba M1 y
  hacia abajo M3, sobre las máscaras del caché que la figura anterior no
  usaba. Es lo único de la figura que no hace ninguna otra, y hace que el
  8 de diciembre aparezca marcado en vez de tapado: 48 horas en M1 y 120
  en M3, que son las cinco instituciones el día entero.

**La distinción entre fronteras la lleva la geometría** y no el color,
porque el contraste medido entre los dos tonos de cobertura es de 1,69 a
1, muy por debajo del 3 a 1 útil: continua contra discontinua, círculo
contra triángulo, relleno hacia arriba contra hueco hacia abajo.
Comprobado en escala de grises.

**El hermano tiene 256 filas, una por día**, con las nueve magnitudes
dibujadas. El anterior tenía 48 filas para 12.288 celdas, de modo que no
regeneraba la figura.

**Un aserto detiene la corrida si la generación deja de coincidir entre
fronteras**, porque es la premisa de la primera banda y del rótulo que la
acompaña.

**Lo que se pierde.** La matriz como objeto: hoy se veían las 6.144 celdas
de una vez y esto son tres lecturas derivadas. La pérdida es real pero
menor de lo que parece, porque aquella vista de conjunto no soportaba
ninguna afirmación con vara; lo que se pierde es la impresión de completud,
no una comprobación. Queda anotado por si el autor prefiere conservar un
mapa reducido en el anexo.

## C-121 · El texto de la figura de cierre, rehecho con la figura

**2026-09-05 · tipo: `contenido` · aplicada**

C-120 sustituye los dos mapas de calor por tres bandas sobre el eje de
dias. El texto que los acompanaba prometia tres comprobaciones que la
figura vieja no hacia con vara ninguna, de modo que se rehace entero: la
frase de entrada, el pie, tres parrafos, uno por banda, y la caja de
lectura.

**Lo que dice ahora la caja** es que cada banda trae su vara y no solo su
forma: la franja de una hora, que es lo que valdria un huso mal puesto;
que la nube no se ensanche ni se corra a lo largo del horizonte; y que las
intervenciones de la limpieza se concentren en dias identificables en vez
de repartirse por el recorrido.

**Cifras nuevas que publica**: el desfase medio de 2,4 minutos y los 253 de
255 dias dentro de la vara; las medianas diarias de la razon entre
generacion y demanda, 0,20 y 1,01; los 129 de 256 dias en que el circuito
secundario se cubre a si mismo y los cero del principal; y el reparto del 8
de diciembre, 48 horas repuestas en la frontera principal y 120 en la
secundaria.

## C-122 · H-26 propagado: la excepcion de Mariana se declara y se cifra

**2026-09-05 · tipo: `numerica` · aplicada**

El texto afirmaba que en el circuito secundario «los cinco medidores son
brutos» y que «la unica excepcion aparente es Mariana, y no es tal».
**Si lo es**, y H-26 lo prueba en el codigo y en el dato: bajo la frontera
principal se le devuelve la generacion descontada y bajo la secundaria no,
porque la configuracion declara bruto el mismo aparato que la otra declara
neto.

Corregido el parrafo, que ahora dice cuatro de cinco y explica el quinto
entero. La declaracion de honestidad metodologica pasa de cuatro
elecciones a cinco, y la nueva va cifrada: la demanda de esa institucion
en esa frontera resulta un 25,1 % menor de lo que seria si se
reconstruyera, la de la comunidad un 5,3 % menor, y la razon entre
generacion y demanda de la frontera pasaria del 95,3 % al 90,5 %.

**Y alcanza a una cifra de la figura de cierre**, cosa que se declara en
el propio parrafo en vez de dejarla en pie: corregida la serie, la mediana
diaria del circuito secundario baja de 1,01 a 0,95 y los dias que se
cubren a si mismos pasan de 129 a 116, es decir, de algo mas de la mitad a
algo menos. La del circuito principal no se mueve.

El pipeline **no se toca**: la correccion invalida el canon vigente y entra
con la proxima corrida canonica, junto con el multiplicador del umbral y
con P-21.


---

## C-123 · Los perfiles se normalizan, y la figura del umbral gana el antes que su pie prometía

**2026-09-05 · tipo: `figura` · aplicada · él pidió los perfiles con la mayor precisión y con la comparación en M3**

**Los perfiles.** La subsección se titula «Cinco ritmos distintos» y su
afirmación es sobre la forma del perfil, pero la figura daba a cada panel
su propia escala vertical y lo advertía al pie: «lo comparable entre ellos
es la forma del perfil, no su altura». Pedía comparar formas y las
dibujaba a escalas distintas, que es lo que impide compararlas; la nota no
salvaba el problema, lo confesaba. Es el mismo vicio que C-115 quitó del
panel del criterio y C-120 de los mapas de calor.

Cada perfil pasa a ir dividido por su propia media diaria, de manera que
los cinco caen sobre un mismo eje y la diferencia de forma es geometría.
El nivel absoluto no se pierde: se declara en la columna del sexto panel,
que da la media diaria de cada institución en las dos fronteras.

**La evidencia del título entra en la figura.** El sexto panel mide a qué
distancia media queda la forma de cada institución de las otras cuatro,
sobre los perfiles ya normalizados. El Hospital es el caso aparte y no por
poco: 0,34 frente a valores entre 0,20 y 0,26 de las demás. El par más
lejano es el Hospital contra la UCC, 0,45, y el más parecido la
Universidad Mariana con CESMAG, 0,11. Se resume por institución y no como
matriz de diez celdas porque lo que la afirmación necesita es el resumen.

**Las dos fronteras, en el mismo panel de cada institución.** La cifra que
acompaña a cada título es la correlación entre los dos perfiles
normalizados: 0,99 en la UCC, 0,98 en CESMAG, 0,96 en Udenar, 0,63 en el
Hospital y 0,21 en la Universidad Mariana.

**Una cautela sobre esa cifra, medida.** Mide si las subidas y bajadas
caen en las mismas horas, no la amplitud, y las dos cosas se separan en
este conjunto: Udenar conserva la forma con 0,96 pero su recorrido pasa de
1,10 a 1,96, de modo que sus dos curvas se ven muy distintas; el Hospital
tiene 0,63 y sus dos curvas casi se tocan, porque las dos son planas y la
diferencia media entre ellas vale 0,05. La figura dibuja las dos curvas y
la cifra dice otra cosa que también es cierta, de manera que el texto no
debe leer el 0,63 como un cambio grande de nivel sino como un cambio de
patrón dentro de una banda estrecha: bajo la frontera principal el
Hospital sube por la tarde y bajo la secundaria sube por la mañana.

**La Universidad Mariana lleva asterisco.** Su fila de M3 hunde el
mediodía, 0,79 contra 1,29 en la principal, y adelanta el pico de las 9 a
las 8. No se maquilla: es H-26, su medidor único y neto recibe
reconstrucción bajo una frontera y no bajo la otra. El asterisco remite a
la declaración de honestidad, con la misma convención que C-76 usó para
los arranques tardíos.

**La figura del umbral gana el antes que su pie prometía.** Él lo señaló:
«aquí debería verse la serie antes del proceso». La única curva dibujada
era la serie ya limpia, es decir, la salida, y el antes eran dos
marcadores sueltos. Entra la serie que el umbral mira, que es la
reconstruida y no la cruda, porque la diferencia entre cruda y
reconstruida es asunto de la figura de la reconstrucción y aquí solo
metería ruido. Va por debajo y con trazo propio, discontinua y más fina,
de modo que la salida sigue mandando en grosor.

**El premio de hacerlo, medido.** Las dos curvas coinciden en toda la
ventana menos en una hora: **1 de las 73 horas** en cada frontera. Eso
prueba lo que la figura solo afirmaba, que el tratamiento es puntual y no
un alisado de la serie entera. La expectativa de que la frontera
secundaria mostrara más divergencias no se cumple en esta ventana: esa
institución arrastra 119 horas tratadas en todo el horizonte, pero
ninguna cae en estos tres días. El rótulo publica la cuenta en las dos
filas, de manera que si el caso cambia la cifra cambia con él.

**Comprobaciones de cierre.** Cero solapamientos en las ocho figuras del
capítulo. Escala de grises: en los perfiles, M1 continua con círculos
frente a M3 discontinua con triángulos; en el umbral, la salida en trazo
lleno y grueso frente a la entrada discontinua y fina. Los hermanos tienen
135 y 2 filas.

---

## C-124 · Los ritmos pasan a las dos fronteras, y la asimetría del fin de semana resulta valer cosas distintas en cada una

**2026-09-05 · tipo: `figura` + `dato` · aplicada · era la última del capítulo que incumplía la regla de las dos fronteras**

`f3_09_ritmos` pasa a un archivo único con las dos fronteras. El panel del
ritmo semanal se parte en dos filas, una por frontera, porque sus demandas
medias se separan por un factor de casi cinco y en un solo eje la
secundaria quedaría aplastada. El eje sigue en kilovatios y no
normalizado, a propósito: lo que el panel tiene que dejar ver es si la
generación cruza a la demanda, y eso solo se ve con las dos magnitudes en
la misma escala.

**La asimetría no vale lo mismo en las dos, y eso es contenido nuevo.** La
demanda cae el \pct{42.5} el fin de semana en el circuito principal y el
\pct{46.8} en el secundario, mientras la generación baja el \pct{1.7} en
las dos, porque es la misma serie. Pero la consecuencia es distinta: en
las horas de sol, de 8 a 16, la generación se queda \uni{58.9}{kW} por
debajo de la demanda el día hábil y \uni{10.5}{kW} el fin de semana en el
circuito principal, de modo que allí no hay excedente agregado ni siquiera
el domingo; en el secundario la supera en \uni{7.5}{kW} el día hábil y en
\uni{19.5}{kW} el fin de semana, es decir, dos veces y media más. La
frase del capítulo, que el fin de semana es periodo de excedente, se
sostiene en la frontera secundaria y no en la principal, y el panel lo
enseña como cruce de curvas.

**El panel mensual se conserva, y hay una medida que lo justifica.** Se
solapa en parte con la segunda banda de la figura de cierre, que recorre
el horizonte día a día, pero aquella lleva la razón entre generación y
demanda y una razón no dice cuál de sus dos términos se movió. Medido: la
demanda mensual recorre un factor de 1,76 en el circuito principal y de
1,58 en el secundario, y la generación solo 1,11. El vaivén de la razón
es, por tanto, el de la demanda. Y hay un segundo aporte que la banda
diaria no puede dar: en el circuito secundario la demanda mensual y la
generación van casi montadas la una sobre la otra, que es la forma visible
de una razón próxima a uno. La fila 3.10 de la tabla maestra, que pedía
una figura aparte para el ritmo anual, queda absorbida por este panel.

**Fuera las dos líneas de prosa del panel izquierdo.** Queda una sola
cifra por fila, la caída de la demanda, junto a la geometría que nombra,
que es la distancia entre sus dos curvas. Lo demás lo dice el párrafo.

**Un rótulo colocado midiendo.** Las tres etiquetas del margen del panel
mensual acaban el horizonte muy juntas, la demanda del circuito secundario
y la generación a \uni{1.1}{kW} una de otra, que sobre ese eje son tres
puntos tipográficos para dos rótulos de dos líneas. Se reparten con el
mismo auxiliar que ya usa la anatomía del umbral.

**Comprobaciones de cierre.** Cero solapamientos en las nueve figuras del
capítulo. Escala de grises: demanda en tinta y generación en verde, que en
gris quedan a distinta luminosidad, y dentro de cada una el día hábil en
trazo lleno y el fin de semana discontinuo; en el panel mensual, círculo,
triángulo y cuadrado. El hermano tiene 125 filas.

## C-125 · Los perfiles, normalizados, y el «antes» que faltaba en el umbral

**2026-09-05 · tipo: `contenido` · aplicada**

**Los perfiles.** La subseccion se titula «Cinco ritmos distintos» y su
afirmacion es sobre la FORMA del dia, pero la figura daba a cada uno de
los seis paneles su propia escala vertical y lo advertia al pie: «lo
comparable entre ellos es la forma del perfil, no su altura». Es decir,
pedia comparar formas y las dibujaba a escalas distintas. La nota no
salvaba el problema, lo confesaba. Es el mismo vicio de C-120.

Cada perfil pasa a dividirse por su propia media diaria, con lo que los
cinco quedan sobre un eje comun y la diferencia de forma pasa a ser
geometria. Entran las dos fronteras superpuestas en cada panel y el sexto
trae la evidencia que faltaba, que es a que distancia media queda la forma
de cada institucion de las otras cuatro, con el nivel absoluto al margen.

**Una cautela que se escribe porque la cifra y el dibujo dicen cosas
distintas y las dos son ciertas.** La correlacion entre fronteras mide si
las subidas caen en las mismas horas, no la amplitud. Udenar la conserva
con 0,96 y su recorrido casi se dobla entre fronteras, de 1,10 a 1,96; el
HUDN baja a 0,63 y sus dos curvas casi se tocan, porque las dos son planas
y su diferencia media vale 0,05. El parrafo dice cual de las dos esta
leyendo.

**El umbral.** La unica curva que se dibujaba era la serie ya limpia, o
sea la salida, y el «antes» eran dos marcadores sueltos: el pie prometia
un antes y un despues y entregaba el despues con una marca encima. Lo
señalo el autor. Entra la serie que el umbral mira, y con ella una cuenta
que demuestra lo que antes solo se afirmaba: **las dos curvas coinciden en
toda la ventana menos en una hora de 73**, en las dos fronteras, de modo
que el tratamiento es puntual y no un alisado de la serie.

## C-126 · El ritmo semanal, con las dos fronteras, y lo que aparece al medir la segunda

**2026-09-05 · tipo: `contenido` · aplicada**

La figura imprimia solo la frontera principal y tenia la secundaria
huerfana en disco, contra la regla de las dos fronteras en una sola
imagen. Era la ultima del capitulo que la incumplia.

**Al medir la segunda aparece que la asimetria no produce lo mismo en las
dos.** La demanda cae el 42,5 % con el fin de semana en el circuito
principal y el 46,8 % en el secundario, y la generacion baja 1,7 % en los
dos porque es la misma serie. Pero en horas de sol la generacion se queda
58,9 kW por debajo de la demanda el dia habil en el principal y 10,5 kW el
fin de semana, es decir, **alli el fin de semana acerca las dos curvas sin
llegar a cruzarlas**; en el secundario las cruza en los dos casos, con
7,5 kW el dia habil y 19,5 kW el fin de semana.

**Se añade una cautela que el agente no acoto y que importa.** Que el
agregado no cruce en el circuito principal no dice que alli no haya nada
que intercambiar: el intercambio ocurre entre instituciones dentro de cada
hora y no entre agregados. Lo que la resta indica es de donde procede el
excedente que se transa, del desajuste entre unas y otras en el principal
y ademas de un sobrante del conjunto en el secundario.

El panel mensual se conserva, y con razon medida: la banda diaria de la
figura de cierre lleva la razon entre generacion y demanda, y **una razon
no dice cual de sus dos terminos se movio**. Aqui se ve, porque la demanda
recorre un factor de 1,76 en el principal y 1,58 en el secundario y la
generacion solo 1,11.

**Con esto el capitulo queda entero en archivos unicos con las dos
fronteras.** Las dos referencias con sufijo que sobreviven son legitimas:
el recorrido de una hora del archivo a la serie, que es un solo medidor y
no tiene version secundaria, y el caso detallado de la reconstruccion, que
va precedido del mosaico de las diez series en las dos fronteras.


---

## C-127 · La segunda fila del caso del umbral dibujaba el mismo medidor de la primera, escalado

**2026-09-05 · tipo: `figura` + `dato` · aplicada · él lo vio: «estás usando los mismos medidores pero escalados»**

Las dos filas de la figura del caso dibujaban la misma hora del mismo
aparato con otro eje, porque la serie secundaria de la Universidad Mariana
es la principal multiplicada por 0,3. La segunda fila no comprobaba nada;
era la primera repetida.

**Lo que falla es la regla, no la fecha.** La selección tomaba la hora
retirada aislada de mayor exceso relativo, y esa regla no excluía las
series que no son una medición propia de su frontera. Se le añade esa
condición, y se comprueba sobre el dato en vez de declararla a mano: una
serie queda fuera cuando su cociente con la de la otra frontera es
constante en todo el horizonte y su valor es la fracción, que es la que se
obtuvo multiplicando. La Universidad Mariana bajo M3 da un cociente de
0,3 con desviación 5,9e-18; en las otras cuatro el cociente varía entre
0,08 y 2,5, de modo que la prueba las distingue sin ambigüedad. Las series
que se comparan son las que ve el umbral, es decir, la lectura del medidor
y la generación tal como entra al filtro; con la generación devuelta el
cociente valdría cero en las cinco de la frontera secundaria y la prueba
las marcaría todas.

**Excluida esa, solo queda una candidata en la frontera secundaria y es la
mejor posible.** Las horas retiradas allí son las dos de CESMAG, las dos
aisladas: el 4 de abril con un exceso del \pct{2.5} y el 9 de mayo con el
\pct{9.0}. Gana el **9 de mayo de 2025 a las 9, que entra con
\uni{19.2}{kW} sobre un umbral de \uni{17.6}{kW} y sale con
\uni{17.2}{kW}**, interpolada entre 17,53 y 16,81.

**Dos razones más para que sea esa.** CESMAG es la institución donde manda
el segundo criterio, de modo que la fila secundaria pasa a ilustrar el
criterio que el capítulo defiende en vez de repetir el primero. Y
sobrevive a la decisión pendiente del multiplicador: con 7, CESMAG
conserva sus dos horas bajo M3 mientras la frontera principal se queda sin
ninguna, caso que el respaldo de la figura ya contempla.

**Lo que cambia en el texto.** El pie y el párrafo decían que las dos
filas dibujan la misma hora porque una serie es la otra escalada. Deja de
ser cierto y pasa a ser lo contrario: cada fila es una institución, un
medidor y una fecha distintos, y por eso la figura comprueba dos veces en
vez de una.

## C-128 · El texto del caso del umbral, con dos medidores distintos

**2026-09-05 · tipo: `numerica` · aplicada**

C-127 cambia la regla de seleccion de la figura, no su fecha: excluye las
series que no son una medicion propia de su frontera. El texto se ajusta
en tres sitios y **cambia una afirmacion por su contraria**: donde decia
que las dos filas dibujan la misma hora porque la serie secundaria es la
principal escalada, ahora dice que cada fila comprueba en un aparato
distinto, que era el defecto que el autor señalo.

**Cuatro cifras retiradas y cuatro nuevas.** Salen las de Mariana bajo la
frontera secundaria, 10,3 / 9,1 / 13,9 % / 7,2, que no deben publicarse
porque eran las de la principal multiplicadas por 0,3. Entran las de
CESMAG el 9 de mayo: entra con 19,2 kW sobre un umbral de 17,6 kW, un
exceso del 9,0 %, y sale con 17,2 kW. Verificadas contra el hermano de la
figura.

**Y el caso nuevo aporta lo que el viejo no.** CESMAG es la institucion
donde manda el segundo criterio, de modo que la figura pasa a ilustrar los
dos criterios en vez de repetir el primero. Sobrevive ademas a la decision
del multiplicador que sigue abierta: con 7 conserva sus dos horas, mientras
la frontera principal se queda sin ninguna.


## C-129 · El guardia físico, medido: se queda en tres comprobaciones y no en cuatro

**2026-09-05 · tipo: `dato` · medida hecha, aún no aplicada al documento**

La decisión de sustituir el umbral distribucional por un guardia físico
llevaba una condición: **medir qué marcaría antes de fijarle ninguna
banda**, porque fijar un número y ver después qué recoge es exactamente el
error del piso del percentil. La medición está hecha sobre el crudo de dos
minutos de los veinte medidores, 122.880 horas-serie, y **corrige dos de
las cuatro comprobaciones que la decisión traía**.

**El factor de potencia sale.** Con el umbral regulatorio marca 64.823 de
las 122.880 horas-serie, más de la mitad del horizonte, y 32.374 aun
restringido a las horas con más de 1 kW de carga. Un factor de potencia
bajo es lo que parece un edificio poco cargado de madrugada. La
comprobación no distingue nada.

**La banda de tensión pasa de asimétrica a simétrica.** La de la norma de
calidad, −10 % y +5 %, marca 5.920 horas-serie, y casi todas son el primer
medidor del Hospital por encima del +5 % de madrugada, hasta el 34,5 % de
las muestras de las 3. La simétrica de ±10 % marca 17.

**La banda de frecuencia se ensancha.** La regulatoria marca 103
horas-serie, pero 25 de las 35 que tocan a las series del modelo son
excursiones del sistema interconectado, vistas por los veinte medidores en
el mismo instante. En una excursión real de la red el medidor mide bien.
La banda de ±0,5 Hz deja pasar todo evento de sistema, cuya desviación
mayor fue 0,30 Hz, y aísla el único fallo de sincronismo del horizonte.

**La afirmación que había que corregir es mía.** El registro de la decisión
decía que el guardia no tocaría ninguna de las once horas y lo apoyaba en
que el factor de potencia se movía «entre 0,87 y 1,00». Ese 0,866 está por
debajo del umbral regulatorio, de modo que bajo la tabla que el propio
registro proponía **el guardia sí habría marcado cinco de las once**. Con
las tres comprobaciones corregidas no marca ninguna, y por una razón mejor:
la discrepancia de la suma de fases no se juzga en kilovatios sino en pasos
del propio registro del medidor, y en las once no pasa de 1,975 pasos
contra una banda de 3.

**Qué marca.** Sobre las 61.440 horas-serie de las diez series del modelo,
67, el 0,11 %: 44 en la frontera principal y 23 en la secundaria. Son tres
sucesos legibles, y el mayor es el hundimiento de tensión de la Universidad
Mariana del 28 al 29 de agosto, con dos fases en 19,0 y 33,3 V mientras la
tercera se mantiene en 128. De las 67, cuatro cruzan el umbral de cobertura
por causa del guardia y 51 pierden una sola muestra.

**Lo que la medición añade al argumento.** Durante ese hundimiento el
medidor informa −0,098 kW, es decir, prácticamente nada, y un número
pequeño **nunca sobresale de la cola de su propia distribución**. El filtro
viejo retiraba once horas de consumo cierto y dejaba pasar el único fallo
de equipo del horizonte, de modo que se equivocaba en las dos direcciones a
la vez. Eso, y no el multiplicador, es lo que justifica el cambio.

**No se aplica todavía al documento**, que sigue describiendo el umbral
distribucional, porque el cambio entra con la corrida canónica junto a H-26
y P-21. Ver el registro de la decisión y H-27.

## C-130 · La sonda de quince minutos: el paso horario se sostiene, y sesga en contra

**2026-09-05 · tipo: `dato` + `codigo` · medida hecha, aún no aplicada al documento**

El paso horario del modelo no venía de ninguna decisión: se heredó del
Excel de veinticuatro filas del modelo base. La sonda lo pone a prueba
corriendo julio de 2025 en las dos fronteras, a paso horario y a cuartos
de hora, con los cinco escenarios y el P2P.

**Primero hubo que hacer explícito el factor de duración**, que estaba
supuesto en una hora y no se escribía en ninguna parte. Toca la
liquidación, los cinco escenarios, el motor de comparación, el techo de
escasez y el cargador. Va con una compuerta que prueba que el camino
horario no se mueve, y **pasa con 672 números idénticos bit a bit**. La
compuerta encontró de paso un defecto real que yo había dejado: las tres
implementaciones internas del escenario colectivo no recibían el factor.

**Los seis mecanismos pierden valor al afinar**, entre el 0,60 y el 1,99 %.
El P2P es el que menos pierde en las dos fronteras.

**La caída no contradice la medición previa, la explica.** Dentro del P2P
los dos efectos van en direcciones opuestas: los términos de mercado
**suben**, la prima del vendedor un 7,19 % en la frontera principal y un
40,46 % en la secundaria, que es el mecanismo que la medición anticipaba;
y el autoconsumo **baja**, un 1,53 % y un 2,67 %, por la desigualdad de
Jensen sobre un mínimo. Como el autoconsumo pesa del 90 al 96 % del total,
su caída manda. Ver H-28.

**Ningún veredicto cambia.** El orden de los seis es idéntico en la
frontera principal. En la secundaria lo único que se mueve es que el
régimen AGR y el par bilateral/bolsa se intercambian, y están separados por
el 0,3 %.

**Y el paso horario sesga en contra de la tesis.** El rendimiento relativo
del P2P frente al colectivo **crece** al afinar: de 0,0901 a 0,0950 en la
principal y de 0,0261 a 0,0343 en la secundaria. Las cifras publicadas son
el punto más adverso, que es donde conviene estar.

**No se aplica al documento todavía.** La sonda no invalida el canon y el
paso horario se conserva; lo que entra al documento es la declaración de
por qué se conserva, con la cota de H-28. Registro completo en el ADR de
CAL-46.

## C-131 · Las dos figuras de la decisión del umbral, y un objeto que no era el mismo

**2026-09-05 · tipo: `figura` · construidas, pendientes de que el texto cambie**

El registro de CAL-45 pide dos figuras que no existen: las treinta muestras
de dos minutos de una hora retirada, y el fallo de tensión que el criterio
distribucional no puede ver. Se construyen ya, para que el día que el
capítulo cambie no haya que inventarlas con prisa.

**El error que la primera versión destapó.** Dibujé la lectura del medidor
y el umbral juzga la **demanda reconstruida**. En las instituciones de
medidor neto parcial esas dos series difieren justo a las horas de sol, que
son las de los once casos, de modo que mi figura contaba nueve muestras
sobre el umbral donde el censo cuenta trece. Comparar objetos comparables:
el caché nativo suma ahora el inversor a su propia resolución con la misma
cuenta que el pipeline hace por horas, y **reproduce el censo exactamente**,
14, 13, 22 y 29 muestras en las cuatro horas del caso.

**La primera figura enseña el caso débil junto al fuerte.** A la izquierda
la hora que menos sobresale de las once, 13 de 30 muestras sobre el umbral;
a la derecha la que más, 29 de 30 en una racha seguida de 58 minutos. Si ni
siquiera el más flojo tiene forma de espiga, ninguno la tiene. De regalo se
ve la arbitrariedad del corte: en CESMAG la hora anterior tiene 19 de 30
sobre el umbral y **sobrevive**, porque su media queda seis centésimas por
debajo.

**La segunda resultó más fuerte que lo que el registro anticipaba.** No es
solo un hundimiento de tensión: el medidor deja de informar **ocho horas
seguidas** y después informa una potencia constante de −0,10 kW durante
**seis horas más**, incluso cuando la tensión ya volvió. Un número pequeño
no sobresale de la cola de ninguna distribución, y ahí está el punto ciego
que justifica el cambio.

## C-132 · La curva de convergencia del paso, y la cota que faltaba

**2026-09-05 · tipo: `dato` + `figura` · medida hecha, figura construida**

La sonda dejó el sesgo del paso horario acotado **por abajo**, con las
cifras de quince minutos. El barrido de convergencia lo acota por arriba
recorriendo el mismo dato a nueve ventanas de promedio, de una hora a los
dos minutos nativos.

**Tres decisiones de método, y las tres eran necesarias.** No corre el
modelo, porque el autoconsumo y el lado corto son aritmética sobre las
matrices. No pasa por la limpieza, porque su cascada está escrita en
conteos de pasos y a dos minutos «huecos de hasta 3 h» valdría seis
minutos, con lo que se mezclaría el sesgo del promedio con un cambio de
criterio de imputación; ver H-29. Y solo entran las horas con las treinta
ranuras presentes en las cinco instituciones a la vez, porque sin esa
restricción una ventana fina «pierde» energía que la hora sí recoge y el
resultado confundiría el sesgo con la cobertura.

**El resultado.** Contra el valor nativo, la hora sobrestima el
autoconsumo un 4,24 % en la frontera principal y un 6,98 % en la
secundaria, y subestima el lado corto un 27,15 % y un 17,87 %.

**Y la curva no se ha aplanado.** El tramo de cuatro a dos minutos todavía
aporta el 28 % y el 22 % del sesgo, de modo que son cotas inferiores y no
el límite del fenómeno. Eso hay que decirlo, porque la tentación es
presentar el valor nativo como «el verdadero».

**La figura enseña lo que ninguna cifra suelta enseña.** Al afinar, las dos
ramas **se separan**: baja lo que los seis mecanismos comparten y sube el
techo de lo único que el mercado aporta por encima de ellos. La fracción de
la oportunidad física que es mercado pasa del 7,74 % al 11,08 % en la
principal y del 15,00 % al 19,53 % en la secundaria. El paso horario no
reparte su error por igual: esconde sobre todo la parte del P2P.

**Lo que la medida NO justifica**, y conviene dejarlo escrito para que
nadie lo lea al revés: correr el juego a dos minutos. Un mercado no liquida
más fino que el más grueso de tres relojes institucionales, la medida
certificada, el precio y el período de liquidación. Los dos minutos del
proyecto son telemetría, no medida comercial de frontera. El dato nativo
sirve de instrumento para medir el error del paso que sí se puede liquidar,
y para nada más.

## C-133 · CAL-45 aplicada: el umbral sale del código y del capítulo

**2026-09-05 · tipo: `dato` + `codigo` + `figura` · aplicada**

El criterio distribucional de atípicos se retira del pipeline y el
capítulo 3 pierde su subsección, su ecuación, su figura de anatomía, su
tabla por entidad y su figura del caso: **185 líneas**. En su lugar entra
la del guardia físico, con la tabla de sus tres comprobaciones y las dos
figuras que son la prueba de la decisión.

**En el código.** El guardia descarta la **lectura** y no la hora, de modo
que vive dentro del lector de medidor y actúa antes del remuestreo; la
etapa de limpieza pierde su primer paso y conserva la cascada de huecos.
El caché instrumentado del capítulo guarda ahora dos lecturas del mismo
medidor, con guardia y sin él, para que las figuras puedan enseñar
exactamente qué retira.

**La compuerta que el registro de la decisión pedía, pasada.** El guardia
programado reproduce al guardia medido: **44 horas y 151 lecturas** en la
frontera principal y **23 y 134** en la secundaria, las mismas cifras que
la medición previa. Y el caché sigue siendo fiel al pipeline con
`max|dif| = 0` en las diez series.

**Cinco cifras publicadas se movieron, y las cinco las atrapó una
aserción del generador**, que es exactamente para lo que estaban:

| Cifra | Antes | Ahora | Por qué |
|---|---|---|---|
| Horas negativas de Mariana | 213 | **210** | Tres eran el hundimiento de tensión, no flujo inverso |
| Mediana de las negativas de Mariana bajo M1 | −0,590 | −0,596 | Arrastra el cambio anterior |
| Mediana bajo M3 | −0,177 | −0,179 | Ídem |
| **Mínimo de demanda de CESMAG** | **0,195 kW** | **2,588 kW** | El mínimo publicado **era el propio fallo** del 17 de junio |
| Censo de la limpieza | 808 | **803** | Ver abajo |

La cuarta merece un renglón aparte. La demanda horaria mínima que el
capítulo publicaba de CESMAG no era un valle de consumo sino el episodio
de tensión hundida de las 6 de la mañana del 17 de junio. Retirado el
fallo, el mínimo real de esa serie es más de trece veces mayor.

**El censo pasa de 808 a 803, y la cuenta cuadra al detalle.** Ya no hay
horas retiradas por umbral; las 803 son todas dato ausente. Son las 797
que ya faltaban más las **seis** que el guardia vacía y que llegan hasta
la limpieza. El guardia vacía **diez**, pero cuatro no llegan: son de la
Universidad Mariana bajo la frontera principal, donde el relleno con cero
de la reconstrucción las convierte en consumo nulo antes de que la
limpieza las vea. **El guardia las detecta y H-25 las tapa**, y así queda
declarado en el capítulo en vez de disimularse.

**La matriz de sensibilidad pierde dos de sus cuatro filas**, las del
multiplicador y las del piso, porque esos parámetros dejaron de existir.
Las bandas del guardia no las sustituyen en esa tabla: vienen de fuera del
dato y barrerlas mediría la sensibilidad a una norma. La única que sí es
una elección de este trabajo, la de la suma de fases en pasos del
registro, se declara y se acota en la declaración de honestidad.

**Lo que queda pendiente y hay que tener presente.** El capítulo 3 y el 4
describen ya el pipeline nuevo; los capítulos de resultados siguen citando
el canon, que se produjo con el criterio viejo. La demanda comunitaria se
mueve un \pct{0.015} bajo M1 y un \pct{0.058} bajo M3, de modo que la
inconsistencia es pequeña, pero existe hasta la corrida canónica que
aplique además H-26 y P-21.

---

## C-134 · El costo unitario medio aparecía con dos valores en el mismo capítulo

**2026-09-05 · tipo: `cifra` · aplicada**

El capítulo 5 imprimía **795,68 COP/kWh** en la nota de una figura y
**792,06** dos párrafos más abajo, para la misma magnitud: el costo
unitario medio de la categoría oficial en nivel de tensión 2. La segunda
reaparecía además en el cierre del capítulo.

**De dónde salía la diferencia.** El archivo de tarifas cubre trece meses,
de abril de 2025 a abril de 2026, y el horizonte del estudio tiene nueve.
Promediar el archivo entero da 792,06; promediar el horizonte da 795,68.
Es la misma trampa que la puerta de datos ya declara para la serie de
bolsa, donde el caché llega hasta enero de 2026 y hay que recortarlo antes
de promediar.

**Lo que hace que esto sea una corrección y no un descuido menor:** el
generador de la figura **ya estaba arreglado**, y su propio comentario
menciona las dos cifras. Lo que quedó viejo fue la prosa. El rastro de la
figura de la banda dice 795,68 y el párrafo siguiente decía 792,06, de
modo que el capítulo se contradecía consigo mismo a dos párrafos de
distancia. Es precisamente lo que la norma de que ninguna cifra derivada
se escriba a mano existe para evitar: la cifra estaba escrita a mano y
sobrevivió al arreglo del generador.

**Aplicado.** Las dos apariciones de 792,06 pasan a 795,68. La banda del
capítulo queda entonces de 182,5 a 795,68 COP/kWh.

**Aviso para la revisión final.** Conviene un barrido de las cifras de
tarifa del documento contra el rastro de su figura, porque este caso
prueba que arreglar el generador no arregla el texto.

---

## C-135 · La banda de precios estaba mal delimitada por abajo, y su ancho resulta ser el cargo de comercializar

**2026-09-06 · tipo: `cifra` + `argumento` · aplicada**

El capítulo 5 delimitaba la banda de ganancia mutua entre la media de bolsa
y el costo unitario, y afirmaba que entre ambos «hay un factor superior a
cuatro». **El principio estaba bien enunciado y la cifra estaba mal.**

**Lo que el vendedor obtiene de la red no es el precio de bolsa.** La
Resolución CREG 174 liquida el excedente en dos tramos: mientras la
inyección acumulada del mes no supere el retiro, la permuta se valora a la
tarifa menos el componente de comercialización, y solo lo que excede ese
cruce va al mercado mayorista. Medido sobre el horizonte, la permuta absorbe
el **100 %** del excedente de Mariana, la UCC, el hospital y el CESMAG, y el
**61,9 %** del de Udenar, porque con una cobertura del 20 % ninguna
institución inyecta en un mes más de lo que retira.

**La identidad que aparece al corregirlo.** Si el comprador paga el costo
unitario completo y el vendedor recibe ese mismo costo unitario menos la
comercialización, la distancia entre ambos es exactamente ese componente:

| | Con piso de bolsa, como decía | Con piso de permuta, corregido |
|---|---:|---:|
| Piso | 182,50 | **620,76** |
| Techo | 795,68 | 795,68 |
| Ancho | 613,18 | **174,92** |

**El ancho de la banda es el cargo de comercializar.** Son 174,92 COP/kWh de
media y notablemente estables, entre 171,95 y 181,03 en los nueve meses, un
recorrido del 5,3 %. La versión anterior sobrestimaba el espacio del
mercado en un factor de 3,5.

**Comprobación cruzada que cierra el asunto.** El propio capítulo ya
publicaba, en el desglose del costo unitario, una comercialización media de
**174,9 COP/kWh**. Es la misma cifra a la que llega la identidad por otra
vía. La banda estaba escrita en el capítulo desde el principio; nadie la
había reconocido.

**Aplicado.** El párrafo de la amplitud se sustituye por dos subsecciones,
una que mide el reparto entre tramos y otra que enuncia la identidad con su
ecuación, más una caja de lectura que traduce el resultado: el margen no
viene de generar más barato ni de consumir menos, **viene de ahorrarse un
intermediario**.

**La caja de trampas gana un cuarto papel.** Antes distinguía tres cifras
del «precio al que la red compra»: el piso de la dinámica, la serie de
liquidación y el nominal de los barridos. Ahora son cuatro, porque el piso
económico de la banda, que es la permuta, no coincide con el piso de la
dinámica, que es la constante heredada. La caja declara la discrepancia y
remite a la corrida canónica pendiente.

**Lo que esto cambia aguas abajo.** El excedente del mercado es el ancho de
la banda por la energía transada, es decir H-33, de modo que corregir el
ancho **divide el excedente medido por 3,5**. Es el efecto más grande de
toda esta tanda y va en contra de la tesis, lo que obliga a tomarlo en
serio. Se aplicará con CAL-47 en la próxima corrida canónica.

Ver H-30, H-33, H-34 y `docs/adr/0047-cal47-banda-de-precios-medida.md`.

---

## C-136 · Las dos correcciones quirúrgicas del solucionador

**2026-09-06 · tipo: `codigo` · aplicada, con compuerta**

Las dos nacen de medir el modelo con la banda estrecha de CAL-47, y ninguna
puede tocar el agregado, porque el excedente es el ancho de la banda por la
energía transada. Solo mueven el reparto.

### Primera · el arranque se reparte sobre la banda y no sobre el techo

El bloque comprador arrancaba en `techo · I/(I+1)`, con I compradores. Esa
forma viene del modelo base y supone que el piso es despreciable frente al
techo. Con la banda de permuta **nace por debajo del piso**, el recorte lo
devuelve al borde, y allí el peso que mueve la dinámica vale prácticamente
cero y el precio queda congelado.

La corrección reparte **la banda** en lugar del techo, y **solo cuando la
forma original cae fuera**. Comprobado en la compuerta:

| Banda | Compradores | Arranque original | ¿Dispara? |
|---|---:|---:|---|
| Modelo base | 1 a 4 | 625,00 a 1.000,00 | **No**, en ninguno |
| Canon | 1 a 4 | 453,14 a 725,02 | **No**, en ninguno |
| Permuta | 1 | 398,97 | **Sí** |
| Permuta | 2 | 531,96 | **Sí** |
| Permuta | 3 | 598,46 | **Sí** |
| Permuta | 4 | 638,35 | No, ya cae dentro |

**El caso base y el canon quedan idénticos bit a bit**, que era la condición.

### Segunda · el paso de integración se comprueba en vez de heredarse

El paso estaba fijado por número de puntos sobre un horizonte, es decir
heredado de una calibración hecha para otra banda. Medido con banda
estrecha, partirlo en cuatro **más que duplica la tajada del vendedor**.

Se añade una comprobación **opcional**, siguiendo el patrón de las decisiones
previas del proyecto: por defecto desactivada y el comportamiento es
exactamente el histórico. Cuando se activa, el bloque se integra con el paso
heredado y con el paso partido; si la diferencia cae por debajo de la
tolerancia se devuelve **la integración gruesa**, de modo que el resultado
sigue siendo idéntico bit a bit siempre que el paso heredado sea suficiente.
Cuando no lo es, se duplica hasta cumplir o agotar cuatro refinos.

La corrida canónica debe activarla. El coste es el doble cuando el paso
basta y hasta dieciséis veces cuando no.

### Compuerta

`tests/gate_cal47_solucionador.py`, en verde. Comprueba que el arranque
usado siempre cae dentro de la banda, que las dos bandas anchas reproducen,
y que la comprobación de paso con tolerancia holgada devuelve exactamente el
resultado histórico.

**Las dos pruebas doradas siguen pasando**, 8 de 8 y 7 de 7.

**Límite de la compuerta, que hay que declarar.** El caso sintético prueba
que las correcciones son inertes donde deben serlo, pero **no reproduce el
fallo de exactitud**, que solo aparece con la rigidez de los datos reales.
La validación de que la primera corrección hace lo que promete se hizo sobre
el dato real, no sobre el sintético.

Ver H-32, H-37 y `docs/adr/0047-cal47-banda-de-precios-medida.md`.

---

## C-137 · CAL-47 y CAL-48 pasan al código, y la clase del usuario deja de confundirse con la fila que se lee

**2026-09-06 · tipo: `codigo` · aplicada, con compuerta**

Cuatro cambios, todos **desactivados por defecto** para que ninguna cifra se
mueva en silencio, y todos expuestos en la línea de órdenes.

### 1 · Las cinco instituciones son usuarios NO REGULADOS

**La corrección la señaló el autor y era conceptual, no de cifra.** El
proyecto las clasificaba entre «oficial» y «comercial», que son **clases del
mercado regulado**. Estas cinco no pertenecen a ninguna: compran por
contrato bilateral. Poner las cinco en «oficial», como se hizo en un primer
intento, daba el número correcto por el motivo equivocado.

Ahora existe la clase `no_regulado` y una función que traduce **la clase del
usuario** a **la fila que se lee como referencia**. Un usuario no regulado no
tiene fila propia en una tabla de regulados, de modo que se le lee la fila
sin contribución de solidaridad. El código dice ahora lo que se decidió, y
no otra cosa que dé el mismo número.

Comprobado: el costo unitario por agente pasa de `797,06 · 956,47 · 956,47 ·
797,06 · 956,47` a **`797,06` para las cinco**.

El fundamento normativo queda escrito junto al código: Decreto 3087 de 1997
artículo 6, que no incluye al sector oficial entre los sujetos pasivos, y su
parágrafo 1, que exime a hospitales y centros educativos sin ánimo de lucro
**que así lo soliciten**; más la Ley 30 de 1992 artículo 98, que obliga a que
toda universidad privada colombiana sea sin ánimo de lucro. **Queda
declarado que la exención se supone solicitada.**

### 2 · El mercado se puede resolver acoplado

El motor gana el método y su horizonte. Con `acoplado` la hora se resuelve
integrando precios y cantidades juntos, como hace el modelo base, en vez de
alternar entre bloques. El residuo de convergencia se guarda donde el
alternado guardaba el suyo, así que el diagnóstico de la corrida conserva
una sola columna.

Se añade además la comprobación de la bandera de éxito del integrador, que
**no se estaba mirando**: una hora que el solver no logra resolver se marca
ahora como sin mercado, igual que ya se hacía con las que producen valores
no numéricos.

### 3 · Las dos cotas admiten vector

El techo por comprador y el piso por vendedor, en el bloque comprador, en la
liquidación y en el límite económico de generación. Con escalares el
resultado es idéntico bit a bit.

### 4 · Las dos correcciones del solucionador

El arranque del bloque comprador se reparte sobre la banda y no sobre el
techo, y solo cuando la forma original cae fuera; y el paso de integración
se puede comprobar en vez de heredarse. Ver C-136.

### Compuerta

`tests/gate_cal47_solucionador.py` en verde, con seis comprobaciones que
incluyen la identidad bit a bit del escalar frente al vector constante. Las
dos pruebas doradas siguen pasando, 8 de 8 y 7 de 7.

### Lo que queda pendiente y hay que decir

Nada de esto ha entrado todavía en una corrida canónica. Cuando entre,
**invalida el canon**, junto con CAL-45, H-26 y P-21. Y cambiará **todo el
reparto publicado**, aunque no el agregado, por la identidad del excedente.

---

## C-138 · La nota de auditoría del bienestar del comprador daba por buena una traducción que las fuentes contradicen

**2026-09-06 · tipo: `registro` · aplicada, con compuerta**

El módulo del bloque comprador llevaba desde 2026-04-17 una nota de
auditoría que afirmaba que la función de bienestar «sí usa la forma
matricial correcta» y que eso era «consistente con la definición de
bienestar» del modelo base. La afirmación era incompleta en un punto que
importa: la matriz sí era la correcta, pero **las fuentes del modelo base no
coinciden en el índice de la energía que multiplica**, y la nota no lo decía
porque nadie las había enfrentado.

El artículo publicado y la línea comentada del MATLAB multiplican por la
energía del comprador ajeno; el script en Python del modelo base multiplica
por la propia. Coinciden solo cuando todos compran lo mismo. El detalle,
las cifras y la decisión están en H-39.

**Qué se corrige.** La nota pasa a decir lo que hay: que existen dos formas,
cuál sigue el proyecto y por qué, y que la elección queda anotada para el
asesor. Se añade la compuerta `tests/gate_c138_bienestar_comprador.py`, que
fija la forma del artículo, comprueba que el script discrepa —de modo que la
compuerta puede fallar y no es un adorno— y verifica sobre el árbol
sintáctico que ninguna función de resolución llama al bienestar.

**El código no cambia.** Se probó a adoptar la forma del script y se midió
el efecto antes de descartarla: de los 672 números de la huella del día
completo **difieren 25**, y los veinticinco son bienestar del comprador, las
veinticuatro horas y el agregado. Ningún flujo, precio o valor de
liquidación se mueve. El agregado del día habría pasado de −725,47 a
−3.587,30 unidades.

**Rectificación, que conviene dejar escrita.** Presenté primero esta
discrepancia como un defecto de nuestra traducción y llegué a aplicarla como
tal. Al comprobar la ecuación 14 del artículo y la línea comentada del
MATLAB, la traducción resultó ser la que sigue a las dos fuentes publicadas,
y la que discrepa es el script. El cambio se revirtió.

Ver H-39.

---

## C-139 · El capítulo de verificación recibe la medida que al proyecto le faltaba

**2026-09-06 · tipo: `documento` · aplicada**

El capítulo estaba en esqueleto y su encargo no mencionaba ninguna medida de
calidad de la solución, porque el proyecto no tenía ninguna. Se añaden sus
dos primeras subsecciones y su primera figura.

**Por qué no se adopta la medida del modelo de referencia.** Su error
normalizado se calcula sobre el ahorro del comprador y la prima del
vendedor, cuya suma es el ancho de la banda por la energía transada, y la
energía está fijada por una restricción de igualdad. De modo que ese total
vale lo mismo en todos los métodos y el número mide el reparto, no la
eficiencia. El capítulo lo dice y explica por qué hace falta otra cosa.

**La medida que entra.** Cuánto del ahorro alcanzable captura el mercado,
tomando como referencia lo que la comunidad deja de pagarle a la red. Se
parte en volumen y emparejamiento, porque las dos preguntas tienen
respuestas muy distintas.

**La figura.** `f7_01_eficiencia_emparejamiento`, panel doble por frontera.
Cada hora es un segmento que va del peor reparto posible al óptimo, con dos
marcas dentro: un círculo hueco para un reparto proporcional ciego y un
rombo lleno para el mercado. Las horas van ordenadas por la ventaja del
segundo sobre el primero, de modo que el signo recorra el eje una sola vez y
la inversión entre fronteras se lea sin contar puntos. El tramo entre las
dos marcas es continuo cuando el mercado gana y discontinuo cuando pierde,
para que la distinción sobreviva impresa en gris.

**Dos defectos de la primera versión, corregidos antes de publicarla.** La
leyenda y el rótulo del eje salieron superpuestos, porque el ayudante de
rótulo común llama al ajuste automático y la leyenda acababa encima; se
colocan a mano en dos renglones propios. Y el recuadro elegido llevaba
título fijo y no admitía argumento, de modo que el título que le pasé se
habría impreso como texto corriente del cuerpo.

**Cifras.** Volumen del \pct{100,0} en las sesenta horas medidas, las dos
fronteras y las dos vías. Emparejamiento: M1 \pct{81,8} de media y
\pct{94,0} ponderado, contra \pct{73,9} del reparto ciego, ganando en 22 de
30 horas; M3 \pct{88,8} y \pct{90,9}, contra \pct{90,9} del reparto ciego,
perdiendo en 17 de 30.

**Un ajuste de herramienta, de paso.** El medidor de estilo solo recorría
los capítulos 2 a 5 y ahora incluye el 7. La primera pasada delató un abuso
de la glosa característica del autor, 5,85 por mil frente a 1,24 del perfil,
que se corrigió hasta 2,36.

Ver H-39.

---

## C-140 · Aparece la versión arbitrada del modelo base y obliga a rehacer tres pasajes

**2026-09-06 · tipo: `registro` · aplicada, con compuerta**

Dos artículos del grupo que no estaban en el árbol resultaron decisivos: la
versión arbitrada del modelo base, publicada en *IEEE Latin America
Transactions* en agosto de 2025, y su precedente multimicrorred de
*TecnoLógicas* de 2024. Lo medido está en H-40; aquí queda lo que hubo que
corregir.

**Primero, dos preguntas del anexo dejan de serlo.** La subsección que
planteaba al comité cuál de las dos formas del término de competencia era la
buena, y lo mismo para el término del pago, se reescribe: la ecuación (11)
de la versión arbitrada escribe las dos formas que el proyecto ya usaba. La
entrada se conserva como nota documental, porque el desacuerdo entre fuentes
sigue existiendo y conviene que conste cuál se siguió, y deja abierto lo
único que sigue sin respuesta, que es si el guion en Python recoge una
versión anterior o una corrección posterior.

**Segundo, el capítulo de verificación afirmaba de menos.** Su primera
subsección decía que la métrica del modelo de referencia mide el reparto y
no la eficiencia. Eso vale para el documento extenso, que reporta
\pct{0,316}, pero **no para la versión arbitrada, que mide sobre la suma de
los bienestares y reporta \pct{0,23}**. La subsección se rehace para
recoger las dos, y el argumento acaba siendo más fuerte: la segunda métrica
tampoco discrimina, porque la suma de bienestares manda todos los precios al
piso por una razón analítica. Medido en cinco horas de tres conjuntos de
datos, la distancia al piso resulta exactamente nula.

**Tercero, el código y la compuerta citaban la autoridad equivocada.** El
comentario del módulo del bloque comprador y la compuerta nombraban «el
artículo» sin distinguir cuál, cuando hay tres documentos que no coinciden.
Pasan a citar la versión arbitrada con su referencia completa y a enumerar
las cuatro fuentes con lo que dice cada una.

**Una hipótesis mía descartada de paso.** Al ver que la versión arbitrada
normaliza sobre el bienestar total, supuse que su \pct{0,23} salía pequeño
porque el denominador está dominado por la utilidad de autoconsumo, que no
depende del mercado. Lo medí antes de escribirlo y **es falso**: la parte
sensible al mercado pesa entre el \pct{145} y el \pct{296} del total, porque
el total es una diferencia pequeña entre términos grandes de signo opuesto.
La explicación correcta es la degeneración en el precio.

**Cuarto, un antecedente para la pregunta regulatoria abierta.** El trabajo
de *TecnoLógicas* modela una penalización, o costo de transmisión, cuando un
recurso envía energía a una microrred vecina. Se añade al anexo, junto a la
pregunta de si la energía intercambiada dentro de la comunidad paga cargos
por uso de redes, porque sitúa esa conversación en terreno conocido.

Ver H-40.

---

## C-141 · La nota de auditoría del término de competencia afirmaba algo falso del código original

**2026-09-06 · tipo: `codigo` · aplicada**

El módulo del bloque comprador llevaba desde el 17 de abril una nota de
auditoría que describía qué hace el fichero en Matlab con el término de
competencia. Decía que el producto se resolvía por indexación lineal y que
eso producía un término nulo para el primer comprador y el factor para los
demás.

**Es falso.** El factor se define en ese fichero como un vector fila de seis
elementos, de modo que el producto es el ordinario entre vector y matriz y
produce, para cada comprador, la suma de los factores de los demás. Con
factor uniforme eso vale el factor por el número de compradores menos uno.

La consecuencia práctica es que **la traducción se quedaba corta por ese
factor**, con dos compradores en nada y con cuatro en tres veces.

**Qué se corrige.** La nota pasa a describir lo que el fichero hace, y se
añade la forma faltante al bloque comprador y al solucionador acoplado, que
no tenía ninguna de las dos alternativas. Las tres formas quedan
disponibles, **con la histórica por defecto**, de modo que ninguna cifra
publicada se mueve mientras no se decida.

Se añade también, en el mismo comentario, la incoherencia que el módulo
arrastra y que conviene tener a la vista: la función que informa del
bienestar usa la forma publicada mientras la dinámica usa la agregada, es
decir, el módulo reporta un bienestar que no corresponde al que su propia
dinámica persigue.

**Efecto medido del arreglo del factor: ninguno de fondo.** Sobre el caso
publicado, a las 13:00 los resultados coinciden al decimal, porque con dos
compradores el factor vale uno; a las 19:00 los precios se mueven algo y el
reparto no se mueve nada.

Las pruebas doradas siguen pasando, 7 de 7, y las dos compuertas del núcleo
siguen en verde.

Ver H-42 y `docs/adr/0049-cal49-termino-de-competencia.md`.

---

## C-142 · El capítulo de verificación recibe la reproducción del caso publicado

**2026-09-06 · tipo: `documento` · pendiente de la medición en curso**

El capítulo tenía dos subsecciones, sobre con qué se mide la calidad y sobre
cuánto del ahorro alcanzable se captura. Le falta la que ordena a las dos, y
que ahora por fin se puede escribir: **la reproducción del caso publicado**.

Hasta hoy no era posible, porque el fichero en Matlab carga un libro de
cálculo que no está en el repositorio y los perfiles del proyecto son una
reconstrucción sintética. La versión arbitrada trae sus datos de entrada
completos.

Queda por redactar hasta que cierre la medición sobre las dos fronteras, que
es la que decide si se adopta la forma publicada. El material está en H-41 y
H-42 y las sondas son `caso_publicado.py` y `competencia_real.py`.

---

## C-143 · El techo de cada comprador entra al solucionador, y el arranque nace dentro de su banda

**2026-09-07 · tipo: `codigo` · aplicada, con compuerta**

Corrige H-45. El solucionador acoplado recibía el techo como un número
suelto, el mayor de los compradores de la hora, y el techo propio se
aplicaba después como recorte. Tres de los cuatro compradores pagaban
exactamente su techo y su ahorro valía cero.

### La causa no era el recorte

Es lo primero que se comprobó al implementar, y obliga a rectificar lo que
H-45 daba por bueno. Pasar el techo como vector **no arregla nada por sí
solo**. El arranque del bloque comprador se calcula sobre el techo mayor, y
con la banda estrecha de CAL-47 nace en 760,3 (COP/kWh) para compradores
cuya banda termina en 731,1. Nacen **por encima de su propio techo**, donde
el peso de barrera vale cero, y su precio no se mueve en toda la
integración. El recorte solo los deja donde ya estaban.

Es la patología de H-32 por el extremo de arriba. Aparece únicamente cuando
coinciden la banda estrecha y dos comercializadores, y por eso no se había
visto antes.

### Qué se cambió

En el solucionador acoplado, el techo pasa de escalar a admitir también un
vector de compradores, con cinco sitios afectados: el presupuesto que
reparte el jugador virtual, que es la suma de los techos; el arranque; el
peso de barrera que multiplica la dinámica del precio; la proyección en la
frontera superior; y el recorte de la trayectoria. El jugador virtual toma
el mayor de los techos.

El arranque se calcula **por comprador**: la forma original si cae dentro de
su banda, y si no, el reparto de su propia banda. Con techos iguales las dos
formas coinciden.

En la sonda del paso a paso, el techo entra al solucionador en vez del
máximo, y el recorte posterior queda como guarda inerte. La sonda gana
además un selector de régimen, para poder medir la pregunta que sigue
abierta con el asesor.

### Fidelidad al modelo base, que hay que declarar

**El techo por comprador no está en el modelo de origen.** La ecuación (5)
del artículo publicado escribe las dos cotas como escalares globales, y el
fichero original las fija a mano. Es una extensión de esta tesis, nacida de
que la comunidad tiene dos comercializadores.

Lo que sí ampara la forma es la versión arbitrada, que formula las cotas del
precio como **vectores** de longitud igual al número de compradores, aunque
los llene con el mismo valor. La generalización respeta esa forma.

### Compuerta

`tests/gate_h45_techo_por_comprador.py`, en verde. Exige que un vector
constante dé un resultado idéntico bit a bit al escalar de ese valor, en las
tres bandas de interés y con tres semillas cada una; que con techos
distintos ningún precio salga de su propia banda; y que el comprador del
techo bajo deje de estar pegado a él.

Se comprobó además contra el fichero anterior extraído del control de
versiones: **con techo escalar el resultado es idéntico bit a bit** en las
nueve combinaciones de banda y semilla.

### Lo que cambia en los resultados

Medido sobre 60 horas activas al azar por frontera, en la tabla de H-45.
Tres cosas: el volumen no se mueve en absoluto, con diferencias de orden
10⁻¹³ (kWh); las 88 horas-comprador sin ahorro de la frontera principal y
las 2 de la secundaria pasan a cero; y el excedente sube un 3,5 % en la
principal y baja un 0,1 % en la secundaria, de modo que **el agregado no es
el argumento**.

Ver H-45 y H-32.

---

## C-144 · El paquete del servidor llevaba finales de línea de Windows

**2026-09-07 · tipo: `codigo` · aplicada, comprobada sobre el paquete**

El montaje en el servidor se detuvo en seco al arrancar el entorno, con este
mensaje:

    : invalid option namedor.sh: line 31: set: pipefail

El mensaje parece corrupto y lo está, pero por una razón que es la propia
causa: el intérprete lee un retorno de carro pegado a la última opción de la
línea que fija el modo estricto, no la reconoce, y al imprimir el error ese
mismo retorno de carro devuelve el cursor al principio de la línea y se come
la primera mitad del mensaje.

### La causa no era lo que parecía

Lo primero que supuse es que la habían introducido mis ediciones, porque
escribir un fichero de texto en Windows traduce los saltos de línea sin
avisar. Al comprobarlo resultó más general: **el árbol entero está en CRLF**,
incluidos ficheros que nadie ha tocado, porque así los deja el checkout. El
empaquetador los metía tal cual en el archivo comprimido y llegaban así a
Linux, donde el intérprete de guiones no los tolera.

Que hubiera funcionado la vez anterior no contradice nada: entonces el guion
llegó por el clon del repositorio, donde el control de versiones ya lo
entrega con el final de línea del sistema de destino.

### El arreglo, y por qué va en el empaquetador

Se normaliza a un solo salto de línea **al armar el paquete**, no en el árbol
de trabajo. Es el sitio correcto por dos razones: el árbol local se queda
como el checkout lo dejó, y lo que viaja es siempre válido en el destino sea
cual sea la máquina que empaqueta.

La huella que el manifiesto publica pasa a calcularse sobre el contenido
normalizado, es decir sobre lo que de verdad viaja, para que se pueda
verificar en el destino. Y los guiones salen con el permiso de ejecución
puesto.

### Comprobación

Sobre el paquete armado: **32 ficheros, ninguno con retorno de carro**. El
guion extraído del propio archivo comprimido pasa la comprobación de sintaxis
del intérprete, y la línea que fallaba se lee ya sin el carácter sobrante.

### Un tropiezo de paso, que es la lección C-119 otra vez

El primer intento de aplicar esta corrección se escribió desde un documento
en línea del intérprete de órdenes, que **interpretó las barras invertidas** y
dejó retornos de carro de verdad dentro de los literales del código, partiendo
un comentario y una llamada en dos. El fichero dejó de compilar.

Se reparó con un guion aparte que trabaja sobre bytes y construye los dos
literales con la función que devuelve un carácter por su código, de modo que
ningún intermediario pueda tocarlos. **Cualquier cosa con barras invertidas se
edita con la herramienta de edición, nunca desde un documento en línea.**

---

## C-145 · Tres defectos que hacían que las mediciones tardaran de más

**2026-09-07 · tipo: `codigo` · aplicada, comprobada en el servidor**

Ninguno toca el modelo y ninguno cambia una cifra. Los tres falseaban el
tiempo, y dos de ellos también la interpretación, porque una corrida que no
termina se acaba cortando y entonces se concluye sobre media muestra.

Salieron de que el autor preguntara si se estaban aprovechando los recursos.
La respuesta era que no, y por tres motivos distintos.

### Primero, los hilos de la biblioteca de álgebra lineal

Las bibliotecas de álgebra lineal abren por defecto tantos hilos como
núcleos ven. Cuando el trabajo se reparte además en tantos **procesos** como
núcleos, eso multiplica: en un servidor de treinta y dos núcleos serían
treinta y dos procesos por treinta y dos hilos peleando por treinta y dos
núcleos, y el tiempo se va en esperas entre hilos que no tienen nada que
calcular.

Aquí no aportarían nada aunque no estorbaran. El sistema que el solucionador
integra tiene del orden de treinta y siete estados, demasiado pequeño para
que repartir una operación entre hilos compense.

Se fija un hilo por proceso. **Tiene que hacerse antes de que numpy cargue su
biblioteca**, de modo que el módulo que lo hace se importa en la primera
línea de cada sonda, antes que ningún otro.

### Segundo, el reparto de tareas en bloques

El repartidor entregaba las tareas en bloques fijos al arrancar. Un
trabajador al que le tocaban dos horas difíciles molía mientras los demás
terminaban y se paraban. Medido el mismo día: dos procesos a pleno
rendimiento, dos completamente parados, y el contador de avance detenido en
diez de ochenta durante cuarenta y nueve minutos, porque los resultados se
recogían en orden de envío y la primera hora lenta retenía toda la cuenta.

Se pasa a entregar de una en una y a recoger por terminación. Y la unidad de
trabajo deja de ser la hora entera para ser **la hora y el régimen**, con lo
que las cuatrocientas tareas del régimen del techo pasan a mil seiscientas y
el reparto se equilibra solo.

Efecto medido: la misma medición que llevaba cuarenta y nueve minutos sin
pasar de la décima tarea se completó entera en veintidós con el reparto
nuevo.

### Tercero, y es el sutil: `nproc` obedece al límite de hilos

Su manual lo dice, aunque no es lo que uno espera: si la variable que limita
los hilos está puesta, determina el valor **mínimo** que devuelve.

El lanzador hacía dos cosas en este orden: contar los núcleos y exportar el
límite de un hilo por proceso. Correcto mientras se ejecute una sola vez.
Pero la acción que corre las tres sondas seguidas **vuelve a invocar el
lanzador** para cada una, y en esa segunda invocación la variable ya venía
puesta a uno desde la primera. La cuenta devolvía uno, y treinta procesos se
quedaban en uno.

En el servidor se vio con toda claridad: la cabecera anunciaba «32 núcleos ·
30 procesos» y la sonda, invocada por ella, declaraba «1 procesos». Son dos
invocaciones distintas y la segunda venía contaminada por la primera. La
carga del sistema lo confirmaba en 1,17.

Se cuenta con la variable limpiada para esa llamada concreta, y la cuenta se
exporta para que las invocaciones anidadas la hereden en vez de rehacerla.

**Y cada sonda declara ahora con cuántos procesos arranca**, que es lo que
convierte un defecto invisible en uno que salta a la vista.

### Comprobación

Reproducido y verificado en las dos máquinas. Con el límite puesto la cuenta
devuelve uno; limpiada, devuelve los doce de la máquina de trabajo y los
treinta y dos del servidor. La invocación anidada hereda el mismo valor que
la primera.

En el servidor, tras la corrección: **1.600 tareas repartidas entre 30
procesos**, treinta y un procesos vivos y carga del sistema subiendo a 25,3.
Antes de ella, un proceso y carga 1,17.

### La lección, que vale fuera de este proyecto

Un lanzador que fija un límite de hilos y luego se invoca a sí mismo se
cuenta un solo núcleo. No es un error de este código: es una interacción
entre una herramienta del sistema y una convención de las bibliotecas
numéricas, y muerde a cualquiera que las junte en ese orden.

Ver C-144, que es del mismo día y de la misma familia: cosas que no tocan el
modelo pero impiden medirlo.

---

## C-146 · El techo por agente llega al juego, no solo a la liquidación

**2026-09-07 · tipo: `codigo` · aplicada, con compuerta**

Propaga al camino de producción lo que C-143 había arreglado por hora. Es la
segunda mitad de la corrección de H-45 y sin ella el arreglo no llegaba a
ninguna cifra publicable.

### La asimetría, ahora al nivel de la corrida

El orquestador construía la matriz del costo unitario por agente y hora, y
se la pasaba a **la liquidación, la comparación de escenarios, el informe
mensual y la serie diaria**. Al juego le pasaba un único escalar comunitario.

Como el ahorro de un comprador es su techo menos el precio, y el precio se
resolvía contra un techo que no era el suyo, la resta salía cero para los del
techo más bajo. La liquidación hacía bien su cuenta sobre un precio que el
juego había formado mal.

### Qué se cambió

Los parámetros de red admiten ahora, además del escalar, **el techo de cada
agente como matriz**. Con ella presente gobierna dos cosas: el límite
económico de generación de cada agente y el precio de cada comprador. Sin
ella, el escalar de siempre y el resultado es idéntico bit a bit.

El orquestador arma esa matriz **antes** del mercado, no después, y más abajo
la reutiliza en vez de recalcularla. Y anuncia por pantalla el rango de
techos que el juego está usando, para que la asimetría no pueda volver
inadvertida.

Nada de lo que recibe el vector necesitaba tocarse: el bloque comprador y la
liquidación lo admiten desde CAL-47, y el solucionador acoplado desde C-143.

### Compuerta

`tests/gate_c146_techo_en_el_juego.py`, en verde. Exige que una matriz
constante reproduzca el escalar; que con techos distintos ningún precio
supere el suyo; que ningún comprador quede con ahorro nulo; y que una matriz
de forma equivocada se rechace en vez de deformarse en silencio.

La prueba dorada sigue en 7 de 7 y el caso sintético completo no cambia.

### Un límite que hay que declarar, y que la compuerta destapó

La propiedad de que ningún comprador quede con ahorro nulo **solo se cumple
sobre la vía acoplada**. Al escribir la compuerta la corrí primero por la
alternada y falló con siete compradores en cero, lo que al principio parecí
un defecto del cambio y no lo es: la vía alternada deja el precio pegado a
una cota por razones ajenas, que son las de H-38.

Importa porque **la corrida canónica va por la vía alternada**, ya que la
acoplada cuesta unos 47 segundos por hora de mercado contra 5.160 horas por
frontera. De modo que el canon heredará el techo por agente pero no la
ausencia de ceros, y así hay que decirlo en el capítulo de resultados.

Ver H-45, H-48 y `docs/adr/0050-cal50-configuracion-elegida.md`.

---

## C-147 · Tres sondas conservaban el defecto del techo, y sus cifras están registradas

**2026-09-07 · tipo: `codigo` · aplicada**

Salió de revisar carpeta por carpeta si la decisión de CAL-50 había llegado a
todo lo que corre el modelo. No había llegado: **tres sondas seguían pasando
al solucionador el mayor de los techos de la hora** y recortando después, que
es exactamente el defecto de H-45.

Importa porque no son sondas cualquiera. Son las que producen cifras que
están en el registro:

| Sonda | Qué produce | Dónde está citada |
|---|---|---|
| competencia real | el reparto y los precios pegados con las tres formas | H-42, decisión de CAL-49 |
| eficiencia | el ahorro capturado frente al alcanzable | H-39, el 80,0 % y el 88,5 % |
| error centralizado | la distancia al óptimo centralizado | H-39 |

En las tres, el techo de cada comprador entra ahora al solucionador. El
escalar se conserva únicamente como guarda para descartar la hora de banda
vacía, que es lo que siempre fue.

**Consecuencia que hay que asumir:** las cifras que esas tres sondas
produjeron se calcularon bajo el régimen superado. No se sabe cuánto se
mueven hasta volver a correrlas. Por la identidad de H-33 el agregado no
debería moverse, pero **el emparejamiento sí**, y eso es justo lo que la
sonda de eficiencia mide. Queda pendiente rehacerlas.

### Lo que se revisó y está bien

Para que la revisión sirva de algo, conviene decir también dónde NO había que
tocar y por qué.

- **Los escenarios regulatorios no rehacen el juego**: consumen el resultado
  del mercado y ya recibían la matriz del costo unitario por agente. Nunca
  tuvieron la asimetría.
- **Las visualizaciones no corren el modelo.**
- **Los análisis que reciben los parámetros de red de la corrida heredan la
  matriz sin tocar nada**: el barrido del piso, los dos de generación y el de
  sub-períodos. Se comprobó además que el de sub-períodos escala la demanda
  sin cambiar el eje temporal, de modo que la matriz le sigue cuadrando.
- **El barrido del techo conserva el escalar a propósito**, porque el techo es
  justamente la variable que barre. **Pero su punto central ya no coincide con
  el canon**, y eso hay que declararlo donde se publique.
- **El análisis de sensibilidad global conserva el escalar**, por la misma
  razón: muestrea el techo como parámetro incierto. Cambiarlo sería rediseñar
  el análisis, no propagar una decisión.
- **Las compuertas y las pruebas conservan el escalar**, que es la condición
  para que sigan comprobando identidad bit a bit contra el modelo base.
- **La sonda del arranque de banda y la del coste del acoplado** conservan el
  escalar con razón: la primera barre bandas por diseño y la segunda mide
  tiempo de convergencia, no economía.

Ver H-45, C-143, C-146 y `docs/adr/0050-cal50-configuracion-elegida.md`.

---

## C-148 · El piso medido llega al juego, y de camino aparece un fallo mudo

**2026-09-07 · tipo: `codigo` · aplicada**

Corrige H-49 y, al hacerlo, destapa H-50.

### El piso, que era la mitad de CAL-47 que faltaba

CAL-47 sustituyó las dos cotas escritas a mano por cotas medidas. El techo
llegó, primero a la liquidación y con C-146 al juego. **El piso no había
llegado nunca:** en la corrida valía 280 (COP/kWh), constante para los cinco
agentes y las 5.160 horas, que es exactamente la constante que CAL-47 venía a
sustituir.

Los parámetros de red admiten ahora el piso de cada vendedor como matriz, y
el orquestador la construye antes del mercado. Eso obligó a subir el cálculo
del cargo de comercializar, que se hacía después, y a añadir el tramo de
permuta, que en producción no se calculaba.

**Cómo entra, que es lo que hay que entender.** El precio tiene índice de
comprador y el piso tiene índice de vendedor. No cabe un piso por vendedor en
una dinámica cuyo estado es un precio por comprador. De modo que **al juego
entra el menor de los pisos de los vendedores activos**, que es lo que ya
hacía la sonda, y **la liquidación recibe el vector entero**, que sí lo
admite desde CAL-47. Con eso la prima de cada vendedor se mide contra su
propio piso, que es lo único que hace visible a quien vende por debajo de su
alternativa.

Lo que ese mínimo **no** resuelve es que ese vendedor exista. Eso es H-43 y
se resuelve decidiendo quién entra, no acotando el precio.

Comprobado sobre el 2 de mayo de 2025: el juego pasa de un piso de 280,0
constante a **un piso medido entre 107,9 y 692,7 (COP/kWh)**, que son
exactamente los dos tramos, bolsa y permuta, que la sonda mide.

> **Cómo hay que leer ese rango, y C-153 lo corrige.** Los dos extremos son
> pisos de verdad **de ese día**, porque ese día hay cuatro horas-vendedor en
> bolsa y el resto en permuta. Pero el aviso los sacaba de la matriz entera,
> que guarda un valor también para las horas en que el agente **no vende**, y
> ahí ese valor no es el piso de nadie. Sobre el horizonte completo el aviso
> habría dicho «de 97,9 a 898,0», con un máximo por encima de todos los
> techos, cuando los pisos que actúan van de 103,7 a 714,1. Ver C-153.

El perfil diario promedio **no lo lleva**, y con razón: el tramo de permuta
depende del mes y ese modo no tiene calendario. Ahí el piso sigue siendo el
escalar, y la corrida lo declara por pantalla.

### Y el fallo mudo que apareció al comprobarlo

El aviso decía que el piso iba «de nan a nan». No era el piso: era la serie
de bolsa, y la causa está en H-50. El techo de escasez se interpolaba **solo
dentro de la ventana pedida**, de modo que un rango de un mes sin fila propia
devolvía un valor no numérico que el mínimo propagaba a toda la serie.

Tres piezas lo cierran: la interpolación pasa a hacerse sobre la unión del
rango con el índice del fichero, de modo que el techo de un mes no dependa de
la ventana; el cargador falla en voz alta si aun así queda un hueco; y el
orquestador comprueba la serie de bolsa antes de seguir.

**Efecto medido.** La misma corrida de un día que antes imprimía la tabla
comparativa entera en valores no numéricos y salía con código cero, ahora da
cifras: 168.194 el mercado entre pares, 153.956 el escenario individual,
132.970 el bilateral y 143.279 el colectivo horario.

### Las tres granularidades, comprobadas en producción

El autor señaló que la permuta varía mes a mes y la bolsa hora a hora, y que
había que asegurarse de que el camino de producción lo respetara. Comprobado
sobre las 6.144 horas del horizonte:

| | Medido |
|---|---|
| La permuta cambia de mes | 695,7 en abril, 692,7 en mayo, 714,1 en junio, 666,0 en julio, y constante dentro de cada mes |
| La bolsa cambia de hora | 1.417 valores distintos, de 97,9 a 898,0, con desviación de 139,6 |
| El tramo cambia dentro del mes | en junio y en julio, un agente de cinco pasa de permuta a bolsa sin esperar al mes siguiente |

Lo tercero es la Resolución CREG 174 funcionando: el tramo depende de la
inyección **acumulada** contra el retiro, de modo que un vendedor puede
cambiar de alternativa externa a mitad de mes. El piso lo recoge.

### La banda invertida, que se temía y no se da

El precio de bolsa llega a 898,0 (COP/kWh), por encima de los techos, que van
de 731,1 a 777,2. Con el piso ya dentro del juego, una hora así invertiría la
banda y el peso de barrera cambiaría de signo.

Medido sobre las **1.126 horas con mercado del horizonte: cero horas con la
banda invertida**. Las 164 horas en que la bolsa supera al menor de los
techos no coinciden con horas que tengan vendedor y comprador y cuyo piso
comunitario venga de un vendedor en tramo de bolsa. La razón es que el piso
del juego es el **menor** de los activos, y basta un vendedor en permuta o
con bolsa baja para que la banda siga en pie.

La cautela que el plan pedía declarar antes de mirar resultados **queda
resuelta por medición y no por criterio**: no hace falta decidir qué hacer en
esas horas porque no se dan. Si un horizonte futuro las trajera, el peso de
barrera lo delataría, de modo que conviene dejar la comprobación escrita.

### Lo que queda por hacer, y no es menor

La restricción de participación **sigue sin estar en el motor**. Con el piso
por vendedor en la liquidación, un vendedor que venda por debajo del suyo
aparecerá ahora con prima negativa en vez de quedar oculto, que es una mejora
de diagnóstico pero no una corrección del mecanismo. Ver H-43.

Ver H-43, H-49, H-50 y `docs/adr/0050-cal50-configuracion-elegida.md`.

---

## C-149 · El criterio de participación miraba el mejor precio y no el ingreso

**2026-09-07 · tipo: `codigo` · aplicada, medida sobre 80 horas**

Un vendedor no entra al mercado si el mercado le paga menos que su
alternativa de fuera. El criterio que decidía eso estaba mal planteado.

### Qué hacía

Retiraba a un vendedor solo si **todas** sus parejas quedaban bajo su piso,
mirando el **mejor** de sus precios. Bastaba entonces con colocar una
cantidad ínfima a un comprador que pagara bien para quedarse vendiendo el
grueso a pérdida.

Lo destapó una auditoría de las tablas del servidor: **16 filas con prima
negativa y cero vendedores retirados**. La peor, la hora 2387 de la frontera
principal, con una prima de −394 (COP) y una tajada del vendedor del
−12,1 %, sin que la restricción de participación retirara a nadie.

### Qué hace ahora

Se retira si su **ingreso ponderado por energía** queda bajo su piso, que es
lo mismo que exigir que su prima no sea negativa:

    suma de P por precio, dividida por la energía colocada  <  su piso

Es lo que decide un vendedor racional: comparar lo que el mercado le paga por
el conjunto de lo que coloca contra lo que le pagaría la red. El criterio
anterior queda alcanzable para contrastar.

### Lo que cuesta, y es la sorpresa

Las primeras cuatro horas que miré, que eran las patológicas que la auditoría
había señalado, daban caídas de volumen del 77 al 92 %. Parecía que el
criterio correcto iba a encoger el mercado.

**Sobre 80 horas al azar no es así.**

| Frontera | Criterio | Volumen (kWh) | Excedente (COP) | Retirados | Vendedores a pérdida |
|---|---|---:|---:|---:|---:|
| M1 | anterior | 167,33 | 42.823,9 | 6 | **1** |
| M1 | **ingreso** | 167,30 | 42.822,8 | 7 | **0** |
| M3 | anterior | 97,93 | 60.568,4 | 13 | 0 |
| M3 | **ingreso** | 97,93 | 60.568,4 | 13 | 0 |

**El criterio nuevo retira más en 1 de 38 horas en la principal y en ninguna
de las 39 de la secundaria.** La mediana del efecto sobre el volumen es del
0,0 % y el peor caso del −0,5 %.

Es decir: **la corrección es prácticamente gratis.** Elimina el vendedor que
vendía a pérdida y cuesta medio punto de volumen en la única hora donde
muerde. Las caídas del 77 al 92 % eran de horas escogidas por ser
patológicas, no la regla.

Conviene decirlo así porque la conclusión contraria habría sido razonable a
partir de las cuatro primeras, y habría sido falsa.

### Una cautela que se declara

Retirar a un vendedor cambia el precio, y ese precio puede volver no rentable
a otro. El bucle itera hasta que nadie más se retira, con tope de tantas
vueltas como vendedores, de modo que **siempre termina**. Pero eso no
garantiza que el conjunto final sea un equilibrio del juego de participación:
podría haber ciclos. La primera vuelta sin retiros es una respuesta
razonable, no necesariamente la única.

### Y falta lo principal

Esto corrige el criterio **en la sonda**. La restricción de participación
**sigue sin estar en el motor**, de modo que la corrida canónica no la tiene.
Ver H-43.

Ver H-43, H-49 y C-148.

---

## C-150 · Las sondas perdían la medición entera por una hora que no resuelve

**2026-09-07 · tipo: `codigo` · aplicada, con la pieza compartida**

Una medición de 160 tareas resolvió 158 en 17,7 minutos y se quedó bloqueada
en las dos últimas, que consumieron **81 minutos de procesador cada una** sin
acabar mientras los otros ocho procesos esperaban parados.

Son dos defectos distintos y ninguno es de la máquina.

**No había cota de tiempo.** La vía acoplada no la tiene, y eso ya estaba
medido: sobre datos reales hay horas que resuelven en 47 segundos y horas que
no acaban en 3.500. Una hora que el integrador no resuelve **es un dato**, no
un motivo para perder la medición.

**No había escritura incremental.** El fichero se escribía solo al final, de
modo que cortar costaba las 158 horas ya resueltas.

Los dos se corrigen en una pieza común que recoge por terminación, escribe
cada fila según llega y, al agotarse el plazo, devuelve lo que hay anotando
las tareas que no llegaron.

Comprobado en la corrida siguiente: **158 de 160 en el plazo, y las dos que
faltaron anotadas con su motivo.** Son la misma hora bajo los dos criterios,
la 4741 de la frontera principal, lo que confirma que el problema es de esa
hora y no del criterio.

### Consecuencia para la corrida canónica, que hay que atender antes

Sobre 80 horas al azar, **una no la resuelve la vía acoplada**, es decir un
1,3 %. Sobre las 1.126 horas con mercado del horizonte serían del orden de
**catorce horas rebeldes por frontera**.

Con la corrida canónica en la vía alternada eso no importaba. Acoplada sí:
sin cota, esas horas pueden bloquear indefinidamente una corrida de horas. El
motor necesita la misma cota que ahora tienen las sondas, **y hay que
ponérsela antes de lanzarla, no después**.

---

## Pendientes

| Id | Qué | Estado |
|---|---|---|
| P-24 | ~~La figura de la gradación cambió de forma y de nombre por C-84.~~ **CERRADA el mismo día**: aplicados el archivo, el pie, la nota y la frase de presentación. | cerrada |
| P-14 | ~~Capítulo 3: el texto y la figura presentaban la conversión de unidades antes de la agregación horaria, y el código promedia primero.~~ **CERRADA por C-57**: las tres etapas se funden en una y el orden se enuncia como se ejecuta. | cerrada |
| P-15 | La bifurcación entre coberturas no es solo la etapa 1. | **cerrada 2026-08-23** por C-50: reescrito el párrafo y la anotación de la figura, con la excepción de Mariana declarada |
| P-22 | No pude reproducir la prueba de los 718 cortes de telemetría. Con la definición registrada en H-18, rachas maximales de ranuras sin muestra en los tres medidores con contador fiable, obtengo 800 cortes y 3.201 kWh frente a los 718 y 809 publicados. Los recuentos de rachas se parecen, de modo que la definición es esa y lo que difiere es el filtrado. La prueba se verificó de forma independiente en su día y la cifra sigue publicada; **pero no es regenerable hoy desde el repositorio**, y por eso la figura nueva usa la evidencia equivalente sobre horas incompletas, que sí lo es. | pendiente |
| P-23 | El documento **no tiene ni una cita**, cero `\cite` en los 22 ficheros, y aun así `main.tex` emite la bibliografía: imprime un encabezado «Referencias» sin nada debajo y lo lista en el índice. O se cita de verdad, empezando por las normas, o se retiran esas dos líneas. Si se elige citar, antes hay que depurar `referencias.bib`, que tiene 17 fuentes duplicadas bajo dos convenciones de clave y ninguna entrada para la CREG 038 de 2014. | pendiente de decisión |
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
| P-17 | ~~Los tramos de un mismo medidor se solapan en un instante exacto y el código los suma.~~ **CERRADA el 2026-09-03 por C-87**: `pd.concat(parts, axis=1).sum(axis=1, min_count=1)` pasa a `.mean(axis=1)` en `data/preprocessing.py`. Equivalencia comprobada en todo lo demás. Efecto medido: la demanda comunitaria pasa de 254.949,9 a 254.948,7 kWh, 1,2 kWh, el 0,0005 %, y **ninguna cifra publicada cambia porque las dos redondean a 254.949**. El código queda por delante del canon hasta la próxima corrida. | cerrada |
| P-18 | ~~La etapa que fija la zona horaria no tiene una sola palabra de prosa.~~ **CERRADA por C-83** y **reabierta y recerrada de otra forma por C-117 y C-118**: la subsección propia se retira, porque localizar un índice no es una etapa, y la comprobación se muda a la subsección de las matrices, sobre la hora media ponderada por la energía (12:06) en vez del máximo, que se decidía por 0,09 kW. | cerrada |
| P-20 | ~~Declarar un umbral de cobertura para la hora incompleta.~~ **CERRADA por C-72**: aplicado como prueba de fragilidad, no como regla, porque mover el agregado 0,026 % no justifica invalidar el canon. | cerrada |
| P-21 | **Aplicar el umbral de cobertura del 75 % en el pipeline.** Decisión tomada: debe hacerse. Cambio: en `_read_single_meter` marcar como ausente la hora con menos de 23 de 30 muestras, para que la etapa de limpieza la impute como hueco en vez de estimarla con la media de lo observado. Alcance: afecta a 147 horas y mueve la demanda comunitaria 0,026 % (Udenar 0,42 %, el resto por debajo de 0,04 %). **Coste: invalida el canon vigente**, de modo que obliga a rehacer la corrida completa en las dos fronteras, el bootstrap y el análisis de sensibilidad global, a repasar las dos compuertas de verificación, y a propagar a las figuras, la tesis, el artículo y los informes mensuales. **Hacerlo junto con la próxima corrida canónica que se necesite por otro motivo**, donde el coste marginal es nulo; no abrir una corrida solo para esto. Medición y contexto en C-72 y H-18. **AVISO 2026-09-01, la especificación es defectuosa y hay que corregirla antes de ejecutarla**: anular esas horas las pega a los huecos que ya existen, y medido sobre la frontera principal, de las 147 quedarían 77 recogidas por interpolación, 63 por arrastre del vecino y **7 dentro de rachas de más de 24 horas, donde el último recurso de la etapa de limpieza es el relleno con cero**. Eso es justamente lo que la subsección `sub:prep-lectura` argumenta que no debe hacerse y lo que el criterio del regulador excluye. La regla correcta es anular la hora solo cuando la limpieza vaya a estimarla, y conservar la media cuando quedaría más allá del alcance del arrastre. Ver H-22. | pendiente, acordada, con la especificación por corregir |
| P-19 | ~~Capítulo 3: la limpieza dice aplicar «3 tratamientos en cascada» y describe cuatro.~~ **CERRADA por C-62.** | cerrada |
| P-5 | Propagar a la tesis (§3.3 y §5.5) y al artículo la declaración de que la tarifa CEDENAR se usa por decisión y no porque sea la de los cinco comercializadores. | pendiente |

## C-151 · La restricción de participación entra al motor

**2026-09-07 · tipo: `codigo` · aplicada, con compuerta y verificada contra
la sonda**

Cierra H-43. Hasta hoy la restricción solo existía en la sonda, de modo que
el documento medía un mercado en el que ningún vendedor vende por debajo de
su alternativa y **la corrida canónica producía otro en el que sí**.

### Qué hace

Retira al vendedor cuyo **ingreso ponderado por energía** queda por debajo de
su propio piso, que es lo mismo que exigir que su prima no sea negativa. Es
el criterio de C-149, ahora en el motor.

Resuelve con el conjunto reducido y **reincrusta el resultado en la matriz
del tamaño original poniendo a cero las filas de los retirados**, conservando
la lista de vendedores intacta. La llamada anidada hace su propia vuelta, de
modo que el bucle se cierra solo.

### La trampa, que se señaló antes de escribir el código

La forma obvia habría sido quitar al retirado de la lista de vendedores. **No
se puede.** La liquidación recorre esa lista para calcular lo que cada
vendedor exporta a la red, de modo que un vendedor ausente de ella no
exportaría: su excedente se evaporaría.

Es el mismo error que la auditoría encontró el mismo día en la sonda del
escenario, donde sesgaba la comparación de facturas en un 76,8 %. Dos
apariciones bastan para darle nombre, y queda escrito en H-43: **quien sale
del mercado no sale de la contabilidad.**

Haber escrito el diseño **antes** de programar, con la trampa dentro, es lo
que evitó pisarla. Conviene repetir esa forma de trabajar donde el cambio
toca el núcleo.

### Por qué no lleva bandera

Porque se activa sola. Con un piso escalar todos los vendedores tienen el
mismo, el precio ya está acotado por debajo a ese valor, y el ingreso
ponderado nunca queda por debajo: no se retira nadie. **La restricción es
inerte cuando las cotas son uniformes por construcción, no por
configuración**, y muerde solo cuando los pisos difieren, que es cuando hace
falta.

### Verificación

`tests/gate_c151_participacion_motor.py`, en verde, con las tres
comprobaciones que se dejaron especificadas en H-43 **antes** de escribir el
código:

| | |
|---|---|
| Con piso uniforme, idéntico y sin retiros | ok |
| El retirado sigue exportando a la red | ok, 0,00 (kWh) evaporados |
| Ningún vendedor por debajo de su piso | ok, cero |

Y la que de verdad valía, contra la sonda, sobre la hora 2387 de la frontera
principal, que era el caso patológico de la auditoría:

| | Retirados | Volumen (kWh) | Prima (COP) | Ahorro (COP) |
|---|---:|---:|---:|---:|
| la sonda | 1 | 7,8000 | 994,6 | 3.643,6 |
| el motor | 1 | 7,8000 | 994,6 | 3.643,6 |

Dos implementaciones independientes, escritas con semanas de diferencia y por
caminos distintos, dan lo mismo. Antes de la corrección esa hora daba una
prima de −394 (COP) y una tajada del vendedor del −12,1 %.

La prueba dorada sigue en 7 de 7.

### Lo que desbloquea

La corrida canónica. Sus cinco motivos quedan atendidos: la generación de
Udenar, el guardia físico de atípicos, la banda medida, el techo por
comprador y el piso con su restricción de participación.

---


## C-153 · El aviso del piso medía la matriz entera, no los pisos que actúan

**Lo destapó una pregunta del autor sobre el propio aviso: «¿por qué decimos
que ahora vale entre 107,9 y 692,7?».**

### Qué decía y qué medía

El orquestador imprimía el rango del piso tomando el mínimo y el máximo de la
matriz completa de vendedores por horas. Esa matriz guarda un valor **también
para las horas en que el agente no vende**, y ahí el número no es el piso de
nadie: es lo que la red le pagaría por un excedente que no tiene.

En el día de prueba los dos extremos coincidían con pisos reales y el aviso
parecía correcto. **Sobre el horizonte completo no lo es.**

| Frontera principal, 6.144 horas | Rango del aviso (COP/kWh) |
|---|---|
| Matriz completa, que es lo que se imprimía | 97,9 a **898,0** |
| Solo las 1.792 horas-vendedor, que son los pisos que actúan | 103,7 a **714,1** |

El máximo de la matriz, 898,0, está **por encima de todos los techos**, que
van de 731,1 a 777,2. Un lector razonable habría concluido que la banda estaba
invertida durante el horizonte, cuando lo que ocurre es que ese valor sale de
horas nocturnas sin excedente, donde el piso no llega a actuar.

### La corrección

El aviso pasa a medir sobre las horas en que el agente tiene excedente, y a
decir cuántas son. Y se le añade una segunda línea que declara el supuesto de
H-53, es decir que el tramo se evalúa sobre el excedente bruto, con el número
de horas-vendedor que caen en bolsa por esa cuenta.

**La norma general, que ya tiene dos apariciones en este registro:** un
resumen se calcula sobre las celdas que el modelo usa, no sobre las que la
matriz tiene. Es la misma familia del error de la sonda del escenario, donde
promediar sobre celdas inertes sesgaba la comparación.

Ver H-49, H-53 y C-148.

---

## C-154 · La sonda leía la bolsa sin el techo de escasez

**Encontrado al comprobar C-153, comparando la serie de la sonda con la de
producción.**

Las dos leen el mismo fichero de precios de bolsa. La corrida le aplica
después el techo de escasez de la Resolución CREG 101 066 en su nivel
superior; **la sonda no**. De modo que la sonda negociaba, en las horas en que
el techo muerde, con un piso más alto del que la corrida usa.

### Cuánto pesa, medido antes de arreglarlo

| | |
|---|---|
| Horas en que el techo muerde | **20** de 6.144 |
| Bolsa sin techo | 97,9 a **2.224,0** (COP/kWh) |
| Bolsa con techo | 97,9 a **898,0** (COP/kWh) |
| De esas 20 horas, cuántas tienen algún vendedor | **cero**, en las dos fronteras |

**El efecto sobre todo lo que la sonda ha medido es nulo**, y no por suerte:
el techo muerde en horas de punta nocturna y el excedente fotovoltaico es
diurno, de modo que los dos conjuntos no se cruzan. Se corrige igualmente,
porque la coincidencia depende del dato y no de la construcción.

Alcanza también al experimento del régimen del piso de H-52, cuyo régimen
forzado a bolsa usa esa serie en **todas** las horas-vendedor. Como ninguna de
las 20 tiene vendedor, el experimento no cambia.

Ver H-50 y H-54.

---

## C-155 · La comparación de regímenes iba en porcentaje por hora, y ahí no significa nada

**Lo destapó la propia medición de H-52 al imprimir «−231,60 %».**

La sonda comparaba cada régimen contra el actual con la variación relativa por
hora y su mediana. **Sobre la factura eso no es una medida.** En la frontera
secundaria la factura de una hora ronda el cero y cambia de signo, de modo que
el cociente se dispara sin que el numerador sea grande. Las medianas salían
«+0,00 %» en casi todo y «−231,60 %» en un sitio, y ninguna de las dos cosas
describía lo que pasaba.

Lo que sí pasaba, en pesos: la permuta mueve la factura de la frontera
secundaria en **−163.808,4 (COP)** sobre cuarenta horas, es decir diez veces la
factura entera del régimen actual.

### Las tres reglas que entran

1. **En pesos, no en porcentaje**, siempre que la base pueda cruzar el cero.
2. **Sobre horas emparejadas.** Solo entran las horas con todos los regímenes
   resueltos. Una hora que no resolvió en un régimen sesgaría la suma de ese
   régimen frente a los demás, y con la vía acoplada eso pasa.
3. **Se dice en cuántas horas cambia algo.** Que la mediana por hora sea cero y
   el total sea grande no es una contradicción: significa que el piso solo
   muerde en una minoría de horas, y eso es información, no ruido.

### Lo que se añade de paso

Un juntador, `compara_regimenes.py`, y la posibilidad de correr **un régimen
suelto**. La muestra la fija la semilla, de modo que una tanda nueva cae sobre
exactamente las mismas horas y la comparación sigue emparejada sin repetir lo
ya medido. Añadir el cuarto régimen costó 80 tareas en vez de 320.

Ver H-52 y H-55.

---

## C-156 · El plazo de la recogida era total, y con eso una hora atascada cuesta media medición

**Medido el 2026-09-08 sobre la propia tanda de H-52.**

La vía acoplada no tiene cota por hora: unas pocas horas no resuelven nunca.
La recogida ya lo contemplaba, pero con un plazo **total**. El resultado:

| | |
|---|---|
| 240 tareas, de las que resolvieron | 237 |
| Tiempo hasta la última hora sana | **26 minutos** |
| Tiempo total de la medición | **55 minutos** |
| Procesos ociosos durante los otros 29 | **siete de diez** |

**Entra un plazo POR TAREA**, medido desde la última terminación, que es lo que
distingue «va lento» de «está atascado»: mientras sigan llegando resultados hay
trabajo sano en curso; en cuanto dejan de llegar, lo que queda no va a llegar.
Con seis minutos, esa misma medición habría cerrado en 26.

El mecanismo de corte es el mismo, porque es el único que funciona: un
trabajador atascado está dentro del integrador, en código nativo, y no atiende
la cancelación. Hay que terminar el proceso.

### Y de paso, qué tienen esas horas

Medido sobre las dos que se atascaron en la frontera principal. La hora 3394
tiene la oferta y la demanda **casi empatadas**, con un 5,4 % de diferencia
frente a una mediana del 78,4 % en la muestra: es la hora más ajustada del
conjunto. Cuando el lado corto es casi un empate el reparto queda indeterminado
y el integrador reduce el paso sin que haya nada que resolver. Es el mismo
fenómeno que la batería de convergencia documentó.

**La segunda no se explica con eso**, y no se le atribuye causa: su holgura es
normal y se atascó en uno solo de los tres regímenes. Haría falta su
trayectoria.

### Verificación

`tests/gate_c156_plazo_por_tarea.py`, en verde, con cuatro comprobaciones:

| | Medido |
|---|---|
| Sin atascos, cierra sola | 8 filas en 1,5 s |
| Con una atascada, corta por el plazo por tarea | a los 31,4 s, con un plazo total de 600 |
| La atascada queda anotada | 6 resueltas y 1 sin resolver |
| No sobrevive ningún trabajador | cero |

---

## C-157 · El juntador buscaba una muestra de cuarenta, y el servidor corre con doscientas

**Lo destapó el ensayo de humo previo al empaquetado, que es para lo que
sirve.**

El juntador de tandas tenía el tamaño de la muestra escrito en el código.
Habría salido en el servidor diciendo que no encuentra ninguna tanda, después
de la medición y no antes. Pasa a recibirlo por argumento, y el lanzador se lo
pasa.

De paso entran en su tabla el índice de equidad y el reparto entre las dos
partes, que sin ellos no estaban donde se lee el resultado.

**La norma que esto confirma:** un ensayo de humo antes de empaquetar cuesta
minuto y medio y encuentra los fallos que en el servidor cuestan una tanda
entera. Es la tercera vez que lo hace en dos jornadas.

---

## C-158 · La recogida de resultados llevaba tres argumentos inexistentes y se callaba

**Encontrado al repasar el paso a paso del servidor, antes de escribirlo.**

La orden que arma el archivo de vuelta tenía **una barra con ene literal**
donde debía ir una continuación de línea. El intérprete la convierte en el
carácter «n» a secas, de modo que al empaquetador le llegaban tres argumentos
llamados «n» que no son ninguna carpeta.

**No fallaba, y eso es lo grave.** El error iba al vacío y la orden terminaba
con un «o verdadero» al final, de modo que la recogida decía «hecho» y contaba
sus ficheros aunque faltara una carpeta entera de resultados. Una medición de
horas se habría perdido en el viaje de vuelta **sin un solo aviso**.

Pasa a armar la lista antes, comprobar que cada carpeta existe, decir en voz
alta cuáles recoge y avisar de la que falte. Probado: recoge las cuatro y 2.969
ficheros.

**Es la misma familia de C-149**, el aviso mudo del empaquetado: un carácter
mal escapado que sobrevive porque el error está silenciado. La norma que se
repite es que **un silenciador de errores necesita justificación escrita**, y
ninguno de los dos la tenía.

---

## C-159 · El plazo total no llegaba a la medición del piso, y la habría cortado por la mitad

**Encontrado con la corrida ya lanzada en el servidor.**

La acción del lanzador pasaba a la sonda el número de horas, los procesos y el
plazo por tarea, **pero no el plazo total**. La sonda lo tiene por omisión en
45 minutos, que era razonable para una muestra de cuarenta horas y absurdo para
las 1.600 tareas de una muestra de doscientas: habría cortado la medición a la
mitad, con el aviso correcto y el resultado incompleto.

Corregido: el plazo total se pasa y queda en 1.440 minutos por omisión. Puede
ser generoso porque **el guardia de verdad es el plazo por tarea** de C-156,
que corta lo que está atascado sin castigar lo que va lento.

### Y de paso, las dos palancas para usar la máquina entera

Quedan escritas en el propio lanzador, porque el servidor tiene núcleos que la
configuración por omisión no aprovecha:

| Palanca | Qué hace |
|---|---|
| Fijar los procesos por variable de entorno | Sube de los núcleos menos dos a los que se quiera |
| Pedir un tamaño de muestra mayor que las horas disponibles | Mide **todas** las horas activas |

La segunda es la que importa. Las horas activas son 1.126 en la frontera
principal y 1.811 en la secundaria, es decir **2.937 horas y 11.748 tareas**.
Con eso **desaparece la cautela de que los resultados salen de una muestra**,
que es la limitación más seria de todo lo medido hoy.

---

## C-160 · Una solución no finita se anotaba como hora resuelta

**Lo destapó la corrida del servidor, al ver los avisos del integrador pasar
por el registro.**

El integrador emite dos avisos distintos y solo uno es benigno:

| Aviso | Qué significa |
|---|---|
| «*t + h = t on the next step, solver will continue anyway*» | el paso se hizo tan pequeño que ya no mueve el reloj. **Continúa**, y el resultado sirve |
| «*too much accuracy requested, tolsf = NaN*» | el factor de escala de la tolerancia **no es un número**, es decir el estado ya lo es |

El segundo **no lanza excepción**. La sonda recogía la solución tal cual, la
anotaba como **resuelta**, y sus métricas quedaban no numéricas.

### Por qué eso sesga en silencio

Las sumas de la biblioteca de datos **descartan los valores no numéricos sin
avisar**. De modo que el régimen afectado saldría con menos horas dentro de su
suma que los demás, y la tabla compararía objetos distintos con el mismo
rótulo. Nada en la salida lo diría.

Es la misma familia de H-50, el fallo más silencioso que este proyecto ha
encontrado, y la misma norma: **una hora que no resuelve es un dato**, no una
fila que se cuela.

### Las dos guardas

En la sonda, una solución no finita se anota como **no resuelta**, con su
motivo, igual que una hora que agota el plazo.

En el juntador, y esto importa porque actúa **sobre mediciones ya hechas**, se
retira la **hora entera** de todos los regímenes, no solo la fila afectada: la
comparación es emparejada y una hora a medias sesga igual. Y se dice en voz
alta cuántas y cuáles.

---

## C-161 · El almacén de la corrida, y la trayectoria que el motor tiraba

**Fase 1 y 2 del plan del aparato de datos.**

### Lo que se tiraba

`core/ems_p2p.py` obtenía, para cada hora, la trayectoria completa de la
integración con sus multiplicadores ya calculados, y **se quedaba con dos
matrices y un escalar**. Todo lo demás moría al salir de la función.

Con dos consecuencias que se arrastraban desde el principio:

- **Ninguna figura de convergencia podía dibujarse sin volver a simular.** Y
  las que existen no persisten ni el precio ni las potencias en el tiempo: la
  única que exporta algo guarda cuatro columnas de bienestar de una sola hora.
- **Ninguna vía de producción devolvía la trayectoria de una hora elegida.** La
  que las guarda escoge las horas sola por heurística y solo dos; la que acepta
  una hora devolvía escalares. Por eso toda figura de convergencia pasaba por
  las sondas, **fuera del motor y de sus cotas**.

### El almacén

Cuatro tablas en parquet, con la cobertura, la hora y la fecha como llave:
**horas**, **flujos**, **trayectorias** y **escenarios**. Se escribe **por
partes**, un fichero cada tantas horas, por la lección que este proyecto ya
pagó dos veces: una medición larga que solo escribe al final cuesta la tanda
entera cuando algo se cae.

**Tres cosas que ahora salen y antes no:** los retirados por hora, el piso y el
techo de cada agente, y el estado del integrador.

**Y los flujos entran sin filtrar los pares de energía casi nula**, que el
desglose de producción descarta bajo un umbral. Con ellos se perdía la prueba
de que el par existió y de que el mercado lo consideró.

**Las dos guardas**, las dos de fallos reales: una hora que no resuelve se
anota **como no resuelta con su motivo**, y una solución no finita **nunca**
entra como resuelta, porque las sumas descartan esos valores en silencio
(C-160).

### Y la trayectoria, ahora a petición

El resultado por hora puede traer la suya, **con los multiplicadores**, que son
los que dicen qué restricción está mordiendo. Sin ellos una figura de
convergencia enseña el precio deteniéndose sin poder decir por qué.

Es **opt-in**, de modo que el comportamiento por omisión queda idéntico bit a
bit.

### La comprobación que de verdad prueba el almacén

Un almacén que mienta pasa desapercibido para siempre: sus tablas se leen
bonitas y nadie las compara contra lo que el modelo hace. La compuerta cruzada
resuelve la misma hora **por el motor y por la sonda**, que son dos caminos
escritos con semanas de diferencia:

| | Medido |
|---|---|
| El precio coincide | **0,00e+00** |
| El reparto coincide | **0,00e+00** |
| La trayectoria se guarda entera | 150 de 150 pasos |
| El último paso es el estacionario | 2,0·10⁻⁸ |
| Los multiplicadores llegan | 10 columnas |

### Cableado al orquestador, y probado sobre un día

Con la bandera del almacén, la corrida lo llena sola. Probado sobre el 2 de
mayo de 2025 por la vía acoplada:

| | |
|---|---|
| Horas anotadas | 24, de las cuales **8 resueltas** y el resto sin mercado, cada una con su motivo |
| Flujos | 36 filas, **con los pares de energía casi nula** |
| Trayectorias | **1.200 pasos**, es decir 150 por hora resuelta |
| Columnas de precio y multiplicadores en una hora | 16 |

Y la comprobación que da sentido a todo: **cualquier hora se recupera de la
carpeta con su trayectoria, sus multiplicadores y sus flujos, sin volver a
simular**. La hora de más volumen del día, con dos vendedores y tres
compradores, sale con sus seis pares, su prima y su ahorro por pareja.

La tabla de escenarios queda vacía a propósito: se llena en la fase que audita
los cinco mecanismos, y hasta entonces es mejor que se note que falta.

### Una diferencia de convención que la compuerta destapó

Las dos vías **no listan igual a un vendedor retirado**. El motor lo
**conserva** en su lista con la fila a cero, que es lo que H-43 exige, «quien
sale del mercado no sale de la contabilidad»; la sonda lo quita de la suya.

Comparar por posición daba un desacuerdo del 100 % donde no lo había. **La
compuerta compara por identidad de agente**, y queda escrito para que nadie
vuelva a leerlo como un defecto.

---

## C-162 · El contrato bilateral recibe su precio, y deja de ser una copia del mercado mayorista

**CAL-51. El defecto más viejo de los escenarios y el que peor se veía, porque
se presentaba como una propiedad.**

### Lo que pasaba

Los dos escenarios daban **el mismo resultado al último dígito**, y el registro
lo daba por bueno: «son idénticos por construcción». Pero la causa no era una
propiedad, era **una ausencia**.

En el caso real las cinco instituciones son prosumidoras y **no hay ningún
consumidor puro**, de modo que la rama del contrato **nunca se ejecutaba** y el
escenario caía a una rama que calcula autoconsumo más excedente a bolsa
horaria. Que es literalmente el otro escenario.

Con la consecuencia de que **todos** sus parámetros quedaban inertes: el precio
del contrato, el factor de reparto y los cuatro componentes tarifarios. La
tesis tenía **cinco mecanismos con una etiqueta de seis**.

### La norma, verificada en el texto oficial

El artículo 23 de la Resolución CREG 174, tal como quedó modificado por el
artículo 27 de la Resolución CREG 101 072 de 2025, distingue:

> **Numeral 1**, para los AGPE que **no** usan fuentes no convencionales.
> **Numeral 2**, para los que **sí**. Su literal a: venta a un tercero con
> destino a usuarios no regulados, **«el precio de venta es pactado
> libremente»**. Su literal b: el crédito de energía del artículo 25.

Las cinco instalaciones son solares. **El repositorio citaba el numeral 1 en
cinco sitios, y un test lo exigía.** Corregido.

Y de ahí la estructura que faltaba: **el primer escenario es el literal b y el
segundo es el literal a. Son los dos destinos alternativos del mismo excedente
de la misma planta.**

### El precio no se postula

Lo publica XM como promedio ponderado de los contratos por tipo de mercado. El
asesor lo señaló en la reunión con su ruta exacta, y **el fichero llevaba meses
en el repositorio sin que ninguna línea lo leyera**.

Cubre el horizonte **entero, los nueve meses, sin huecos**, contra lo que se
temía. Va de 283,3 a 295,2 (COP/kWh), con media de 287,4.

Eso **sustituye el postulado del factor de reparto**, que era el parámetro
libre más atacable de la tesis, por una serie pública, mensual y citable.

### Lo que se midió al separarlos

Sobre el 2 de mayo de 2025, en producción:

| | Contrato | Bolsa |
|---|---:|---:|
| Beneficio (COP) | **142.768** | 132.970 |
| Índice de equidad | −0,2472 | −0,1917 |
| Coeficiente de Gini | 0,2070 | 0,2471 |

**No solo cambia el beneficio: cambian las dos métricas de reparto.** Antes las
dos columnas eran el mismo objeto con dos rótulos.

### Las cinco comprobaciones

`tests/gate_cal51_contrato.py`, en verde:

| | Medido |
|---|---|
| Sin precio de contrato, idéntico a lo de siempre | dif **0,00e+00** |
| Con el precio igualado al de bolsa, los dos coinciden | dif **0,00e+00** |
| La separación es el excedente por la diferencia de precios | dif **1,1·10⁻¹⁰** |
| El escenario de bolsa no se mueve | igualdad de matrices |
| La serie cubre el horizonte | 9 de 9 meses |

La segunda es la que convierte **la igualdad de antes en una propiedad
demostrada de un caso límite**, en vez de un accidente que había que explicar.

Y la tercera es una **identidad, no un umbral**: la diferencia entre los dos
escenarios es exactamente el excedente por la diferencia de precios, al último
decimal. Es el mismo estilo de la identidad de H-33.

### Qué se rompe

Solo las cifras del escenario del contrato. Los otros cinco mecanismos **no se
mueven ni un dígito**, y eso está demostrado por igualdad de matrices, no
argumentado.

**Y reventará una compuerta a propósito:** hay un generador de figuras que
afirma hoy que los dos escenarios son iguales, con el mensaje «eso es un
hallazgo». Se diseñó para reventar el día que dejaran de serlo.

Ver la ficha de los cinco escenarios y H-40.

---
## C-163 · El contrato bilateral pasa a ser interno, y con eso el escenario responde a la pregunta que importa

**CAL-52. Sustituye en producción a C-162, que se conserva porque lo que midió
sigue siendo válido y porque explica por qué había que llegar hasta aquí.**

### La pregunta que el escenario anterior no contestaba

C-162 le puso al contrato bilateral el precio que XM publica para los contratos
del mercado mayorista, y con eso dejó de ser una copia del escenario de bolsa.
Estaba bien y sigue en pie. Pero H-63, midiéndolo, encontró que ese precio
**domina a la bolsa por partida doble**: paga más, con media de 287,4 frente a
181,8, y varía menos, con desviación de 3,6 frente a 139,6. La bolsa solo lo
supera en el 11,6 % de las horas.

Un escenario cuyo resultado está decidido antes de correrlo no informa nada. Y
peor: usar el promedio de los contratos entre grandes generadores y
comercializadores como el precio que recibiría una instalación solar
institucional es un supuesto generoso que nadie puede sostener con una fuente.

### Lo que el autor decidió, y por qué reordena el escenario

Consultado con las dos alternativas sobre la mesa, el autor eligió **el
contrato interno**, pactado **en el punto medio de la banda**.

Y eso cambia lo que el escenario mide. Ya no es «a cuánto vendo el excedente
afuera», que es una pregunta de precio de mercado, sino:

> **Los mismos vecinos, la misma energía, los mismos flujos. Lo único que
> cambia es que el precio se pacta de antemano en vez de formarse en el juego.
> ¿Qué aporta entonces el mecanismo dinámico?**

Es la comparación que le faltaba a la tesis, porque es la única que aísla el
mecanismo de todo lo demás.

### El precio, y no tiene parámetros libres

Cada pareja contrata en el punto medio de su propia banda:

$$\pi_{ji} = \frac{\text{techo}_i + \text{piso}_j}{2}$$

A mitad de camino entre lo que el comprador pagaría a la red y lo que la red le
pagaría al vendedor. **Reparte la banda a la mitad**, de modo que el ahorro del
comprador y la prima del vendedor son iguales por construcción.

De ahí la propiedad que lo vuelve un patrón útil: **su índice de reparto vale
cero exacto**. Es el reparto perfectamente equitativo, y el mercado entre pares
se mide contra él.

**El factor de reparto, que era el parámetro libre más atacable de la tesis, ya
no existe.** No se calibra ni se barre: sale de la aritmética.

### Y por la identidad de H-33, el excedente no cambia

El ancho de la banda por la energía transada es el mismo se pacte el precio que
se pacte. Lo que cambia es **quién se lo lleva**. De modo que la comparación
mide si el mecanismo reparte mejor o peor que una regla fija, que es justo la
pregunta que el modelo base plantea con su índice de equidad.

### Lo que se midió, sobre el 2 de mayo de 2025 en producción

| Escenario | Beneficio (COP) | Índice de equidad | Gini |
|---|---:|---:|---:|
| Mercado entre pares | 168.194 | −0,3465 | 0,1589 |
| Autogeneración individual | 153.956 | −0,3019 | 0,1719 |
| **Contrato interno** | **141.575** | −0,1840 | 0,2276 |
| Mercado mayorista | 132.970 | −0,1917 | 0,2471 |
| Colectivo horario | 143.279 | −0,1462 | 0,2846 |

Y el reparto del excedente, que es lo que este escenario existe para contrastar:

| | Compradores | Vendedores |
|---|---:|---:|
| Mercado entre pares | 34,62 % | 65,38 % |
| **Contrato interno** | **50,00 %** | **50,00 %** |

**El mercado desplaza 15,38 puntos porcentuales del excedente hacia los
vendedores frente al reparto a la mitad.** Esa cifra es el aporte del mecanismo
dinámico, dicho en la única unidad en que se puede decir.

### El índice de equidad de la tabla NO es ese cero, y conviene decir por qué

La columna de equidad de la tabla mide otra cosa: agrega el beneficio de cada
agente, lo parte en dos grupos por su cobertura solar, y compara los grupos.
Escribir el cero del contrato en esa columna dejaría **una celda que no
significa lo mismo que sus vecinas**, que es justamente el defecto que la ficha
de los escenarios ya tiene anotado.

De modo que la columna se queda uniforme y la propiedad del contrato se reporta
aparte, donde puede comprobarse sin contaminar la comparación.

### La pareja que no firma

Nada garantiza que el techo del comprador esté por encima del piso del
vendedor: son dos agentes con dos tarifas. Con la banda invertida no hay precio
que deje a los dos mejor que yendo a la red, y ese contrato no se firma; la
energía se trata como la que el mercado no coloca y va a bolsa. Medido en
H-64.

### Las cinco comprobaciones

`tests/gate_cal52_contrato_interno.py`, en verde:

| | Medido |
|---|---|
| El reparto es exacto a la mitad | índice **6,1·10⁻¹⁷** |
| El excedente es el ancho de la banda por la energía | dif **2,9·10⁻¹¹** |
| La banda invertida no se firma | 6 de 104 parejas, forzadas a propósito |
| El excedente no depende del precio pactado | dif **0,00e+00**; la cuota del vendedor sí se mueve 33,3 pp |
| Nada se pierde ni se inventa | firmados + sin firmar = asignados |

La cuarta es la que convence: movido el reparto a un tercio y a dos tercios de
la banda, **el total no se mueve un solo dígito** y solo cambia quién se lo
lleva. Es la comprobación directa de que este escenario mide reparto y no
tamaño de la torta.

### Qué queda del escenario anterior

El precio de contrato de XM y su cargador **se conservan y siguen probados**.
El escenario los acepta por parámetro y sin él reproduce lo de antes bit a bit.
Queda disponible como variante, medido en H-63, y como consulta al asesor.

---

## C-164 · El autoconsumo y la autosuficiencia llevaban el nombre del otro

**En tres sitios del núcleo, y parcheado en un cuarto.** Es el defecto que la
auditoría de escenarios había anotado como menor y que resultó ser sistémico.

### La convención, que es la estándar

| | Se divide entre | Responde a |
|---|---|---|
| Autoconsumo | la **generación** | qué fracción de lo que genero se aprovecha |
| Autosuficiencia | la **demanda** | qué fracción de lo que consumo cubro sin la red |

Es la convención de la literatura de fotovoltaica en edificios, y la que el
lector de una tesis va a suponer.

### Lo que había

Las dos funciones del módulo de liquidación y las dos del motor de comparación
dividían al revés, y el resultado por hora heredaba el cruce. La capa de lectura
del documento **lo parcheaba al abrir el libro**, renombrando las columnas al
vuelo, de modo que el texto salía bien y el código seguía mal.

Ese parche llevaba una nota que decía exactamente por qué se sabía: con una
cobertura solar del 20 %, la fracción de demanda cubierta con generación propia
**no puede valer 0,98**. Se sabía y se rodeaba, en vez de corregirse.

### Y un cuarto sitio, en el corte por sub-períodos

Un campo llamado como el índice de equidad guardaba en realidad el
**coeficiente de Gini**. Quien lo leyera por su nombre leería otra cosa. Ahora
son dos campos, cada uno con lo suyo, y de paso **el índice de equidad entra por
fin al corte por sub-períodos**, donde antes sencillamente no se guardaba. Los
dos salen ya en la tabla.

### Lo que cambia en los números

Nada de fondo: las dos cantidades se calculaban bien, con el nombre cambiado.
Lo que cambia es **qué columna lleva cuál**. Sobre el 2 de mayo de 2025:

| | Antes | Ahora |
|---|---:|---:|
| Autoconsumo del escenario individual | 0,132 | **0,758** |
| Autosuficiencia del escenario individual | 0,758 | **0,132** |
| Autoconsumo del mercado entre pares | 0,174 | **1,000** |
| Autosuficiencia del mercado entre pares | 1,000 | **0,174** |

Y ahora se leen solas: el mercado entre pares **aprovecha toda la generación**,
que es lo que un mercado hace, y cubre el 17,4 % de la demanda, que es lo que
una cobertura solar de ese tamaño permite.

### El aviso que hay que llevar puesto

**Los artefactos anteriores a esta corrección tienen las dos columnas
intercambiadas.** Compararlos con una corrida nueva exige cambiarlas de sitio
antes, o las dos saldrán discrepantes sin que nada esté mal. Queda escrito en la
capa de lectura, que es donde alguien va a tropezar con ello.

### La comprobación

`tests/gate_c164_autoconsumo_autosuficiencia.py`, cinco en verde, y las dos
primeras son las que importan porque **no se pueden satisfacer con los nombres
cruzados**:

| | Medido |
|---|---|
| Con generación escasa, autoconsumo alto y autosuficiencia baja | 1,0000 y 0,1727 |
| Con generación abundante, al revés | 0,2227 y 1,0000 |
| Los dos viven entre cero y uno | sí |
| Autoconsumo × generación = autosuficiencia × demanda | dif 0,00e+00 |
| Liquidación y comparación coinciden sin mercado | dif 0,00e+00 |

---

## C-165 · El beneficio se anota en la hora que lo genera, y de ahí salen las métricas por período

**El defecto que dejaba muda a media tesis.** El beneficio de cada mecanismo
solo existía **agregado al horizonte entero**. De modo que se podía decir que el
mercado reparte de tal manera en nueve meses, pero no en cuáles: ni en qué meses
reparte mejor, ni a qué horas del día, ni si el reparto de un lunes se parece al
de un domingo.

Es media pregunta del capítulo de equidad y toda la de la discusión de precios.
Y era también la razón por la que **la cuarta tabla del almacén llevaba días
declarada y vacía**: no había de dónde llenarla.

### Cómo se hizo, y por qué así

Cada escenario anota su dinero **en la hora que lo genera**, con los mismos
vectores con los que ya calculaba el total, **antes de sumarlos**. No hay una
segunda implementación que pueda derivar de la primera: hay una sola cuenta que
además guarda el paso intermedio.

Es la diferencia entre añadir una capacidad y añadir un riesgo.

### La que falta a propósito

La segunda granularidad del colectivo valora contra promedios **mensuales**.
Repartir su dinero entre las horas del mes sería inventar una precisión que la
liquidación no tiene, de modo que **no tiene desglose horario**, lo declara, y
la compuerta comprueba que no lo finge.

### La comprobación, y es la que convence

`tests/gate_c165_desglose_horario.py`: para cada mecanismo, la matriz suma por
filas **exactamente** el beneficio por agente que el motor publica.

| Mecanismo | Diferencia relativa |
|---|---:|
| Mercado entre pares | 3,7·10⁻¹⁶ |
| Autogeneración individual | 1,1·10⁻¹⁶ |
| Contrato interno | 2,6·10⁻¹⁶ |
| Mercado mayorista | 1,3·10⁻¹⁶ |
| Colectivo horario | 1,2·10⁻¹⁶ |

Es decir, al último bit que la aritmética de coma flotante permite.

Y en producción, sobre el 2 de mayo de 2025, el agregado del día reconstruido
desde el almacén reproduce la tabla publicada **al peso y el coeficiente de Gini
al cuarto decimal**: 168.194 y 0,1589 para el mercado, 153.956 y 0,1719 para la
autogeneración individual, 141.575 y 0,2276 para el contrato, 132.970 y 0,2471
para el mercado mayorista, 143.279 y 0,2846 para el colectivo.

### Lo que ahora se puede decir y antes no

`analysis/equidad_periodo.py` agrega esa tabla por mes, por día, por hora del día
o por día de la semana, y calcula para cada período el coeficiente de Gini, el
cociente frente al colectivo y el precio de la equidad.

Un ejemplo del mismo día, que da idea de para qué sirve: a las once de la mañana
el mecanismo más eficiente es el mercado y el más equitativo es la
autogeneración individual, con un precio de la equidad de 0,0253; **al mediodía y
hasta las tres de la tarde el mercado es a la vez el más eficiente y el más
equitativo**, y el precio de la equidad se anula. Esa distinción entre horas no
se podía formular antes.

### Una cautela declarada

El índice de equidad de los escenarios parte a los agentes en dos grupos por su
cobertura solar, y esa partición se calcula **una sola vez sobre el horizonte
entero**. Cambiarla en cada mes haría que el índice de enero y el de julio
hablaran de grupos distintos y dejarían de ser comparables. Se conserva la
partición global, y queda dicho.

---

## C-166 · La liquidación por institución, que es lo que el asesor pidió ver

**La pieza central de la ponencia, y la que no existía.** El asesor la pidió en
la reunión preparatoria del foro con estas palabras:

> «con lo regulatorio está saliéndole a 900 pesos, al usuario le están cobrando
> 900 pesos, pero los excedentes se los están pagando a 200. Mientras que en el
> óptimo, al vendedor le están pagando mucho más»
>
> «Así sea que tuvieras los resultados **para una entidad**, ¿cómo hacer esa
> verificación?»

El mínimo exigible era una sola institución. Están las cinco, y además la misma
cuenta para los cinco mecanismos regulatorios y no solo para el mercado.

### Lo que faltaba para poder hacerla

**Una quinta tabla en el almacén.** Las cuatro que había describen el mercado
—quién transó con quién, a qué precio, cómo convergió— pero **ninguna describe
al agente**. Sin la energía, la banda y el papel de cada institución hora a
hora, no hay con qué decir cuánto le cobra la red por lo que importa ni a cuánto
le paga lo que exporta.

La tabla nueva se llena **también en las horas sin mercado**, y eso importa: una
institución que esa hora no transó sigue comprándole a la red, y la liquidación
tiene que verlo.

El papel se anota como palabra —vendedor, comprador, retirado o inactivo— porque
es lo que se lee en una figura, y porque **un vendedor retirado por el criterio
de participación no es lo mismo que uno que no tenía excedente**. Confundirlos
borra el efecto que ese criterio produce.

### Dos tasas de red, y no una

Preguntan cosas distintas, y la distinción se ve en el primer día que se mira:

- **la efectiva**, lo que la red le cobró y le pagó de verdad por la energía que
  sí cruzó la frontera;
- **la contrafáctica**, lo que le habría cobrado y pagado por todo su faltante y
  todo su sobrante, es decir si no hubiera mercado.

La que hay que comparar contra el precio de dentro es la segunda. Una
institución que coloca **todo** su excedente dentro de la comunidad no le vende
nada a la red y su tasa efectiva no existe; decir que no existe sería cierto y
sería inútil. Lo que hay que decir es a cuánto se lo habrían pagado.

Y las dos van ponderadas por energía, no por hora: la media simple del techo a
lo largo del día pesa igual una hora en la que la institución mueve treinta
kilovatios y una en la que no mueve ninguno, y sale un precio al que nadie
compró ni vendió nada.

### Lo que sale, sobre el 2 de mayo de 2025

| Institución | le cobraría la red | le pagaría la red | compra dentro | vende dentro | se ahorra |
|---|---:|---:|---:|---:|---:|
| Cesmag | 777,2 | — | 683,7 | — | 1.620 |
| HUDN | 731,1 | 692,7 | 573,4 | 724,9 | 1.036 |
| Mariana | 731,1 | — | 666,8 | — | 1.036 |
| UCC | 731,1 | — | 666,8 | — | 1.036 |
| Udenar | 731,1 | **464,1** | — | **657,2** | 9.846 |

Precios en (COP/kWh) y ahorro en (COP).

**La última fila es la frase del asesor, medida.** A Udenar la red le pagaría su
excedente a 464,1 y dentro de la comunidad lo coloca a 657,2. La diferencia no
es un supuesto: es el ancho de su banda repartido por el juego.

### Y la comparación que una ponencia necesita

La segunda tabla pone al lado lo que cada mecanismo le dejaría a esa institución
en ese período, y **no gana siempre el mismo**:

| Institución | mejor mecanismo |
|---|---|
| Udenar | mercado entre pares |
| HUDN | mercado entre pares |
| Cesmag | contrato interno |
| Mariana | colectivo |
| UCC | colectivo |

Eso es un resultado, no un defecto del modelo: **al vendedor grande le conviene
el mercado y al comprador puro le conviene el colectivo**, que reparte el
excedente por porcentaje acordado en vez de por negociación. Es exactamente la
tensión que el capítulo de equidad tiene que explicar.

### Lo que no hace

**No vuelve a simular.** Cada cifra es una agregación de filas que la corrida
escribió, de modo que no puede discrepar de la tabla publicada.

---

## C-167 · El aparato de figuras del foro, y la regla que lo gobierna

**Para proyectar en una ponencia, no para imprimir en un artículo.** De ahí el
diseño: una idea por figura, pocas series, rótulos grandes. Una figura que se
entiende en veinte segundos de pie desde la última fila.

### La regla, y es la que le da valor

**Ninguna vuelve a simular y ninguna cifra se escribe a mano.** Todas leen del
almacén, que es lo que la corrida oficial escribió, y cada una deja su tabla de
datos y su nota de procedencia al lado. Una figura de este conjunto se puede
auditar sin ejecutar el proyecto: el fichero hermano dice literalmente de qué
tabla salió.

### Las horas protagonistas se eligen por criterio medido

No por conveniencia narrativa. Cuatro categorías fijadas de antemano, que el
almacén resuelve solo y que **cada figura declara en su pie**:

| Categoría | Criterio |
|---|---|
| típica | la mediana por volumen de las horas con al menos dos vendedores y tres compradores |
| escasez de oferta | la de menor cociente entre oferta y demanda netas |
| exceso de oferta | la de mayor cociente |
| patológica | precio pegado a una cota de su banda, u oferta y demanda casi empatadas |

Y la frase del pie **la genera el mismo código que aplicó el criterio**, no el
pie. Así la figura no puede afirmar un criterio distinto del que se usó.

El día del grupo C se elige igual: el de mayor recorrido del precio acordado
entre sus horas de mercado.

### Los grupos

**A · cómo se acuerda el precio.** La trayectoria con la banda medida de cada
agente y el multiplicador de la restricción del vendedor en el eje gemelo; el
reparto del excedente frente al patrón del contrato interno; y las potencias por
pareja a lo largo de la integración, que muestran que **la energía se reparte
antes que el precio**.

**C · la discusión de precios en un día.** Las veinticuatro horas con su banda,
su acuerdo, y abajo cuántos venden, cuántos compran y **cuántos se retiraron**,
que es lo que el criterio de participación produce y que ninguna figura del
proyecto mostraba.

**D · la comparación regulatoria.** Lo que le cuesta a cada institución la
energía que compra, dentro y fuera; y qué le deja cada mecanismo, con el mejor
señalado. Esta última es la que impide la conclusión fácil: **no gana el mismo
mecanismo para todos**.

**El grupo B no vive aquí** —el sistema sin filtrar y el barrido del término de
rivalidad— porque no se puede leer del almacén: exige correr el modelo con otros
parámetros. Va en su propio guion, para que la regla de esta carpeta siga siendo
cierta sin excepciones.

### Cuatro defectos de lectura que el primer ensayo destapó

Se anotan porque son la clase de cosa que sobrevive impresa si nadie mira la
figura terminada:

**Uno.** Los rótulos de techo se imprimían uno por agente, y como tres
instituciones comparten comercializador, tres rótulos caían sobre el mismo píxel
y no se leía ninguno. Ahora se dibuja **una línea por techo distinto**, rotulada
con quiénes lo comparten.

**Dos.** Dos compradores con el mismo techo acuerdan el mismo precio, y la
última curva dibujada tapaba a las anteriores: **la leyenda prometía cuatro
series donde solo se veían dos**. Ahora las que nunca se separan más de medio
peso por kilovatio hora se dibujan juntas y la leyenda lo dice. El criterio es
visual y no exacto a propósito: exigir igualdad al bit dejaría el defecto intacto
por diferencias que nadie puede ver.

**Tres.** La tabla de trayectorias es la unión de todas las horas, y los papeles
cambian de una a otra. Una institución que compra a las once y vende a las doce
aporta columnas de las dos clases, y en la hora en que no juega ese papel su
columna está vacía. Dibujarla no pintaba nada pero **sí añadía una entrada a la
leyenda**, y una leyenda que promete una serie que no está es peor que una serie
de menos: el lector la busca.

**Cuatro.** El pie afirmaba «horizonte completo» sin haberlo mirado. Ahora lo
**lee del dato**: un almacén de un día de prueba y uno de nueve meses producen la
misma figura, y el pie es lo único que los distingue.

### Y un rótulo que había quedado atrás

El mecanismo del contrato seguía apareciendo como «C2 · PPA» en la paleta común
después de CAL-52, cuando ya no es un contrato con un tercero a precio de mercado
sino el contrato interno de la comunidad al punto medio de la banda.

---

## C-168 · Un plazo que estaba escrito y no mordía

**Encontrado al construir el barrido del término de rivalidad**, y merece
entrada propia porque el patrón se repite en todo el proyecto: **un plazo que no
mata el trabajo no es un plazo**.

### El primer intento

Un ejecutor de procesos con un solo obrero, y una espera con plazo sobre cada
tarea. Parece correcto y no lo es, por una razón que la documentación dice y que
es fácil pasar por alto: **un ejecutor no puede cancelar una tarea que ya está
corriendo**. Cancelar solo funciona sobre las que aún esperan en la cola.

De modo que al vencer el plazo, la tarea seguía ocupando al único obrero, el
valor siguiente quedaba en cola detrás de ella, y al cerrar el ejecutor la
espera era infinita. El barrido llevaba quince minutos parado **sin decir en qué
valor**, que es lo peor de las dos cosas.

### El segundo intento, y por qué tampoco bastó

Un proceso propio por valor, que sí se puede terminar. Correcto en la forma, y
aun así **todos los valores agotaban el plazo**, incluidos los que un momento
antes resolvían en segundos.

La causa: en esta plataforma cada proceso hijo arranca de cero y reimporta el
módulo entero, de modo que **volvía a cargar el conjunto completo de mediciones
antes de integrar nada**. El plazo se consumía leyendo ficheros. Con el ejecutor
esto no se notaba porque el obrero se reutilizaba y solo el primer valor pagaba
la carga.

### Lo que quedó

Un proceso por valor, terminable, **y el dato cargado una vez en el padre y
pasado al hijo**. Así el plazo mide lo que debe medir, que es la integración.

Y el valor que no resuelve dentro del plazo **se anota como tal**: queda en la
tabla de datos de la figura y se cuenta en su pie. Un hueco declarado es un
resultado; un barrido que nunca termina, no.

### Por qué se registra

Porque la lección de C-156 —el plazo por tarea— se había aplicado en la
recogida de las sondas y aquí se volvió a escribir mal. La regla, en una línea:

> **Comprueba que el plazo mata el trabajo, y que lo que el plazo mide es el
> trabajo y no el arranque.**

---

## C-169 · La cuenta de núcleos del servidor no llegaba al mercado

**La pregunta «¿estamos usando toda la máquina?» se ha hecho varias veces en
este proyecto y la salida no daba con qué contestarla.** Ahora sí, y de paso
había un defecto real detrás.

### Lo que pasaba

El lanzador del servidor calcula su cuenta de núcleos con cuidado, esquivando
incluso una trampa por la que el contador del sistema obedece a la variable de
hilos y devolvía uno. La exporta, y **ninguna línea del mercado la leía**.

El ejecutor de procesos se abría sin decir cuántos obreros quería, de modo que
tomaba su valor por defecto: el número de núcleos que la máquina declara.

### Por qué eso no es lo mismo que los núcleos utilizables

El número que la máquina declara **no respeta la afinidad ni los límites del
contenedor**. En un servidor compartido, dentro de un cgroup, o con la afinidad
restringida, los dos números difieren. Y abrir más procesos que núcleos útiles
no acelera nada: los hace pelearse por el mismo tiempo de procesador.

De modo que la corrida podía estar sobresuscribiendo la máquina sin que nada lo
dijera, o quedándose corta, y en ninguno de los dos casos había forma de
saberlo mirando la salida.

### Lo que se hizo

**Tres cosas, y la tercera es la que contesta la pregunta.**

**Una.** El mercado acepta cuántos procesos abrir. La bandera manda; si no
está, se lee del entorno, que es donde el lanzador la deja; y si tampoco, se
toman **todos los núcleos útiles**.

**Dos.** Los núcleos útiles se cuentan con la afinidad del proceso, que es lo
único que refleja una restricción real, y solo si eso no existe se recurre a lo
que la máquina declara. Un número pedido por encima de los útiles **se recorta
y se avisa**, en vez de sobresuscribir en silencio.

**Tres.** La corrida **imprime lo que eligió y por qué**: cuántos procesos,
sobre cuántos útiles, y cuántos hilos de álgebra lleva cada uno. Un número que
no se imprime no se puede comprobar.

### Y la corrida oficial toma toda la máquina

Para las sondas se reservan dos núcleos, para que el servidor siga respondiendo
mientras se mide. **La corrida oficial no**: es lo único que corre y es la que
se quiere lo más corta posible, de modo que toma todos. Quien quiera dejar
holgura la pide de forma explícita, y entonces la acción no la pisa.

Sin este cambio habría pasado lo contrario de lo que se busca: al empezar a leer
la variable del entorno, la corrida oficial habría usado **dos núcleos menos**
que antes.

### La comprobación

Sobre el 2 de mayo de 2025, en producción, con cinco procesos y con seis:

| | Cinco procesos | Seis procesos |
|---|---:|---:|
| Mercado entre pares | 168.194 | 168.194 |
| Autogeneración individual | 153.956 | 153.956 |
| Contrato interno | 141.575 | 141.575 |
| Mercado mayorista | 132.970 | 132.970 |
| Colectivo horario | 143.279 | 143.279 |

**Idénticas.** El número de obreros mueve el reloj y no el resultado, que es lo
que hay que poder afirmar antes de cambiarlo.

---

## C-170 · Una compuerta de la corrida oficial no verificaba nada, y lo aparentaba

**Encontrado leyendo la salida de la corrida oficial en el servidor**, el 9 de
septiembre, mientras pasaba. La compuerta del paso de tiempo imprimía:

> `huella con 672 numeros`
> `nada que hacer: use --escribe o --compara`

y salía con **código cero**, de modo que el lanzador la daba por buena y
escribía `ok` debajo.

### Por qué estaba así

Se escribió como herramienta de desarrollo, no como compuerta: compara la
corrida de antes de un cambio contra la de después, y para eso necesita que
alguien le pase un fichero de referencia. Al entrar en la lista del servidor se
invocó sin argumentos, y entonces no hace nada.

Es la misma clase de fallo que el proyecto ya conocía —el lanzador tiene un
guardia para las pruebas que saltan todas y salen con cero— aplicada a un caso
que ese guardia no cubría.

### Lo que se hizo, y evita el fichero de referencia

**La propiedad de la decisión se puede comprobar sin referencia y sin depender
de la máquina.** Lo que se afirma es que con paso horario el resultado no se
mueve ni un bit cuando el factor de duración viaja explícito. De modo que basta
correr la misma huella dos veces en el mismo proceso —una con el factor
implícito y otra con el mismo factor explícito— y exigir que coincidan.

Las dos mitades corren en la misma máquina y en el mismo instante, así que no
hay nada que un servidor distinto pueda mover.

Y **sin banderas ya no sale con cero sin verificar**: hace esa comprobación.

### Que la comprobación muerde, y se midió

No basta con que pase: hay que saber que fallaría si tuviera que fallar. Con el
factor de duración puesto en dos en vez de en uno, **79 de los 672 números
cambian**. La comprobación tiene dientes.

Y con el factor en uno, los 672 coinciden bit a bit.

### Y las otras diecisiete, auditadas

Si una salía con cero sin verificar, había que mirar el resto antes de volver a
correr. **Era la única.** Las diecisiete restantes devuelven código de fallo de
verdad: o acumulan sus fallos y salen con uno si hay alguno, o lo hacen con la
prueba dorada, que declara sus siete comprobaciones una por una.

### Qué significa para la corrida del 9 de septiembre

**La propiedad de CAL-46 no quedó verificada en esa corrida.** Las otras
dieciséis compuertas sí corrieron y sí verificaron; esta no. No invalida las
cifras —el paso horario es el que la corrida usa, y es el que la decisión
declara conservador— pero la afirmación de que el camino explícito es idéntico
al histórico se apoya, para esa corrida, en la medición del día en que se tomó
la decisión y no en una comprobación de esa misma corrida.

Queda verificada desde la siguiente.

---

