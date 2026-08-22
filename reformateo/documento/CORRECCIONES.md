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

## Pendientes

| Id | Qué | Estado |
|---|---|---|
| P-1 | Pasada de vocabulario: el texto usa 3 de los 21 giros característicos del autor. Faltan «asciende a», «se sitúa entre», «conforme a», «línea base», «por transparencia metodológica». | pendiente de decisión |
| P-2 | «es decir» está en 0,89 por mil frente al 1,24 del objetivo. | pendiente |
| P-3 | Abreviaturas: el autor escribe UDENAR, UNIMAR, UCC, UNICESMAG, HUDN. El documento ya usa CESMAG (C-13); quedan por decidir UDENAR frente a Udenar y UNIMAR frente a Mariana. La infraestructura para cambiarlo ya existe: basta editar `ETIQUETA_INSTITUCION` en `estilo.py` y regenerar. | pendiente de decisión |
| P-4 | Capítulo 4: reescribir la contraposición «campus completo frente a ramal fotovoltaico», que H-7 desmiente. Los rótulos ya están corregidos; falta el argumento del capítulo. | pendiente |
| P-6 | Establecer si `MedicionesMTE_v3/` es anterior o posterior a la corrección de escala que describe el inventario. Es prioritario. | pendiente |
| P-5 | Propagar a la tesis (§3.3 y §5.5) y al artículo la declaración de que la tarifa CEDENAR se usa por decisión y no porque sea la de los cinco comercializadores. | pendiente |
