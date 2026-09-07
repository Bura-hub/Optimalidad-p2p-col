# El mercado hora a hora, sobre un día concreto

**2026-09-07** · Aparato de validación horaria · Actividad 2.1 y 3.1

Este informe se puede leer sin abrir el código. Responde a lo que se pidió
en la reunión preparatoria del foro: qué le liquida la regulación a cada
institución y qué le liquidaría el modelo, y cómo funciona el mercado por
dentro en horas concretas.

---

## Lo primero, porque cambia cómo se lee todo lo demás

**Dos de las cinco instituciones participan del mercado y no ganan nada.**

El 2 de mayo de 2025, en la frontera principal, Mariana y la Universidad
Cooperativa compran cada una casi diecisiete kilovatios hora dentro de la
comunidad, y su factura sale **idéntica** a la que tendrían sin mercado.

No es que compren poco. Es que pagan **exactamente su techo**, 731,1 pesos
por kilovatio hora contra un techo de 731,1, en las ocho horas en que hay
mercado. El ahorro de un comprador es su techo menos el precio, y ahí vale
cero.

La única compradora que consigue precio interior es el CESMAG, que paga
756,1 sobre un techo de 777,2, al 75 % de su banda. Y la razón es que
**tiene otro comercializador**.

La causa está en el código y es concreta: el solucionador recibe **un techo
escalar**, el mayor de todos los compradores de la hora, y el techo propio
de cada uno se aplica después como recorte. A los tres que comparten el
techo más bajo el recorte los deja justo encima de él. Queda registrado como
hallazgo H-45, con lo que habría que hacer.

---

## Qué días, y por qué

| | Día | Horas con mercado | Energía transable | Excedente en juego |
|---|---|---|---|---|
| **Principal** | 2025-05-02 | 8 en M1, 11 en M3 | 55,3 y 61,0 kWh | 2.821 y 40.400 COP |
| Contraste | 2025-04-16 | 10 y 12 | 41,9 y 5,2 kWh | menor |

El principal se eligió por tener **el mayor excedente en juego del
horizonte**, doce veces el de los días de abril. El de contraste, por ser el
de más horas con mercado en las dos fronteras a la vez, y sirve para
responder a la objeción previsible: ¿y si hubieras elegido otro día?

Las dos fronteras se leen en paralelo porque **invierten los papeles**: en
la principal Udenar vende el grueso; en la secundaria el CESMAG compra el
grueso.

## Qué horas se desarrollan, y por qué esas

El criterio se declara, y **las categorías que no se dan ese día se dicen**
en vez de sustituirlas por otra hora, que es como se cuelan los ejemplos
escogidos a conveniencia.

| Categoría | Criterio | 2 de mayo, M1 | 2 de mayo, M3 |
|---|---|---|---|
| Central | mayor volumen transado | 11:00 · 2 vendedores, 3 compradores | 10:00 · 4 y 1 |
| Déficit | mayor racionamiento | 08:00 · 1 y 4 | 16:00 · 1 y 4 |
| Excedente | mayor sobrante | **no se da** | 11:00 · 4 y 1 |
| Patológica | vendedores retirados por su piso | **no se da** | **no se da** |

En la frontera principal el día entero es de déficit: la demanda neta supera
a la oferta en las ocho horas, de modo que no hay hora de excedente que
enseñar. Y la restricción de participación **no muerde** en ninguno de los
cuatro recorridos, así que tampoco hay hora patológica. Existen en el
horizonte —la hora 37 de la frontera principal retira tres vendedores y el
volumen cae un 63 %— pero no en estos dos días.

## Qué se ve en cada figura

**El panorama del día.** Tres bandas por frontera: la energía que se ofrece,
se pide y se mueve; dónde cae el precio dentro de su banda; y cómo se
reparte el excedente. Lo que salta es el contraste entre fronteras: en la
principal los precios están **pegados al techo**, con dos o tres clavados
cada hora, y el vendedor se lleva el 90 %; en la secundaria flotan **en
mitad de la banda**, ninguno pegado, y el comprador se lleva entre el 60 y
el 80 %.

**Quién vende y quién compra.** La inversión de papeles, hora a hora y por
institución.

**La factura comparada.** Lo que cada una deja de pagar, separando lo que
gana como vendedora de lo que gana como compradora.

**El índice de ganancia.** Lo anterior normalizado por el rango admisible de
cada agente, que es la única forma de comparar instituciones de tamaños muy
distintos. Para un vendedor el peor caso es exportarlo todo a la red y el
mejor colocarlo al techo más alto de la hora; para un comprador el peor es
comprarlo todo a la red, que le deja cero ahorro, y el mejor comprarlo al
piso más bajo. Las dos cotas salen de la banda **real** de cada hora.

**El mosaico de cada hora testigo**, con seis paneles: quién es quién, la
banda y el acuerdo, los flujos por pareja, cómo llegó el precio con sus
multiplicadores, dónde cae el mercado entre el peor reparto y el óptimo, y
qué cobra cada vendedor comparado con la normativa base.

## La factura, en cifras

El 2 de mayo de 2025.

| Institución | Frontera principal | Frontera secundaria |
|---|---:|---:|
| Udenar | 2.275,6 como vendedora | 4.902,2 como vendedora |
| Mariana | **0,0** | 2.071,9 |
| UCC | **0,0** | 2.435,0 |
| HUDN | 191,6 | 2.439,6 |
| CESMAG | 353,8 como compradora | 28.550,9 como compradora |
| **Comunidad** | **2.821,0** | **40.399,6** |

**Se benefician los dos lados**, que es lo que la reunión predecía, pero no
todos: en la frontera principal el excedente se lo llevan dos agentes y los
otros tres se reparten 192 pesos.

---

## Los límites, que se declaran y no se esconden

1. **La vía es la acoplada, y no es la de las cifras publicadas.** El canon
   se corrió con la vía alternada. Toda figura lo declara. La acoplada es la
   del modelo base y la que produce precios interiores, pero cualquier
   número de este informe es de un método distinto al de los resultados
   publicados.
2. **El escenario colectivo mensual no tiene valor horario** por
   construcción: su bolsa y su cruce son mensuales. El contraste hora a hora
   solo se puede hacer contra la normativa base.
3. **El contrato bilateral y el régimen de generación agregada no devuelven
   reparto por agente y hora.** No entran en este informe.
4. **El precio de una hora no es un objeto robusto.** Con costo lineal el
   reparto es un problema de transporte cuyos duales forman un poliedro. El
   volumen sí lo es.
5. **Las cifras de eficiencia se calculan sin la restricción de
   participación** en las sondas previas, y con ella en este aparato. Donde
   muerde, no son comparables.

## Qué queda abierto

- Pasar el techo por comprador **al solucionador acoplado** en vez de
  aplicarlo como recorte posterior (H-45). Mientras no se haga, los
  compradores del techo bajo se quedan sin excedente por construcción.
- Enseñar una hora patológica, que existe en el horizonte pero no en estos
  dos días.
- La corrida canónica, que ya acumula sus motivos.
