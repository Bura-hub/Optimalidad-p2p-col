# GSA sobre el caso de estudio — resultados verificados

**Estado: campaña cerrada.** Dos coberturas, 1 792 evaluaciones, cero fallos.

---

## 1. Qué se corrió, y por qué existía este ejercicio

`analysis/global_sensitivity.py` no corre sobre el caso de estudio: corre sobre el caso
sintético de 6 agentes y 24 horas del modelo base. El propio orquestador lo declara y
rechaza la combinación (`main_simulation.py:1505`). El problema era que **la tesis (§7.1,
§7.10) y el artículo lo narraban como si caracterizara el benchmark de 6 144 h**. Los
índices publicados eran reales y estaban bien calculados; lo que no era cierto es sobre
qué se calcularon.

Esta campaña los calcula sobre el caso de estudio.

| | M1 | M3 |
|---|---|---|
| Cobertura G/D | 19,1 % (totalizadores de campus) | 91,2 % (submedidores del circuito PV) |
| Horizonte | 6 144 h (abr–dic 2025) | 6 144 h |
| Evaluaciones | 896 = 128 × (5+2) | 896 |
| Fallos | **0** | **0** |
| Bloques descartados | **0,00 %** en las tres salidas | **0,00 %** |
| Peor evaluación | 1 047,8 s (timeout 12 820 s) | 773,5 s (timeout 8 466 s) |
| Coste | 137,9 h-CPU en 2,28 h de reloj | 112,0 h-CPU en 3,83 h |
| Huella de datos | `0f72cd5bd3caf7cf` | `34ab9b7ea624a0d0` |

Semilla de muestreo 42, remuestreo 42 con 1 000 réplicas, `calc_second_order=False`.
Procedencia verificada regenerando la matriz de Saltelli desde la semilla y comparándola
fila a fila con las columnas del CSV.

**Reproducción independiente.** El análisis se re-ejecutó en una máquina distinta
(Windows, Python 3.13, scipy 1.17.1) sobre los mismos CSV producidos en el servidor
(Linux, Python 3.10.12, scipy 1.15.3): **los índices coinciden dígito por dígito**. Y en
el contraste de robustez del solucionador, el modelo devuelve el mismo valor en ambas
plataformas hasta once cifras significativas (7 384 672,916877 frente a 7 384 672,916825).

---

## 2. Los índices

Semiancho = intervalo de confianza al 95 % por remuestreo con semilla fija.

### Ganancia neta del P2P

| parámetro | M1 · S1 | M1 · ST | M3 · S1 | M3 · ST |
|---|---:|---:|---:|---:|
| PGB | −0,0000 ± 0,0001 | **0,0000 ± 0,0000** | −0,0001 ± 0,0001 | **0,0000 ± 0,0000** |
| PGS | 0,1609 ± 0,0980 | 0,1838 ± 0,0489 | 0,1965 ± 0,1103 | 0,2330 ± 0,0596 |
| **factor_PV** | 0,8274 ± 0,2031 | **0,8473 ± 0,1745** | 0,6368 ± 0,1974 | **0,6673 ± 0,1508** |
| factor_D | 0,0126 ± 0,0249 | 0,0094 ± 0,0038 | 0,1556 ± 0,0998 | 0,1593 ± 0,0436 |
| **b_mean** | −0,0000 ± 0,0001 | **0,0000 ± 0,0000** | −0,0001 ± 0,0001 | **0,0000 ± 0,0000** |

### Autoconsumo

| parámetro | M1 · S1 | M1 · ST | M3 · S1 | M3 · ST |
|---|---:|---:|---:|---:|
| PGB | −0,0000 ± 0,0001 | 0,0000 | −0,0002 ± 0,0002 | 0,0000 |
| PGS | 0,0000 ± 0,0001 | 0,0000 | −0,0000 ± 0,0002 | 0,0000 |
| **factor_PV** | 0,7454 ± 0,1894 | **0,7368 ± 0,1709** | 0,7991 ± 0,2021 | **0,7956 ± 0,1875** |
| factor_D | 0,2570 ± 0,1195 | 0,2691 ± 0,0647 | 0,2116 ± 0,0883 | 0,2325 ± 0,0718 |
| b_mean | −0,0000 ± 0,0001 | 0,0000 | −0,0001 ± 0,0002 | 0,0000 |

### Índice de equidad

| parámetro | M1 · S1 | M1 · ST | M3 · S1 | M3 · ST |
|---|---:|---:|---:|---:|
| **PGB** | 0,3764 ± 0,1754 | **0,8794 ± 0,3069** | 0,5390 ± 0,1733 | **0,8337 ± 0,2710** |
| PGS | 0,0580 ± 0,1370 | 0,3848 ± 0,1436 | 0,0408 ± 0,0935 | 0,1420 ± 0,0584 |
| factor_PV | 0,0696 ± 0,1019 | 0,1405 ± 0,0525 | 0,0033 ± 0,0290 | 0,0158 ± 0,0069 |
| factor_D | −0,0117 ± 0,0558 | 0,0548 ± 0,0219 | −0,0083 ± 0,0239 | 0,0055 ± 0,0025 |
| b_mean | 0,1112 ± 0,1779 | 0,2027 ± 0,1181 | 0,1898 ± 0,1908 | 0,4066 ± 0,1644 |

### Estructura de la varianza

| salida | ΣS1 M1 | interacción M1 | ΣS1 M3 | interacción M3 |
|---|---:|---:|---:|---:|
| ganancia | 1,001 | ~0 — **aditiva** | 0,989 | ~1 % — **aditiva** |
| autoconsumo | 1,002 | ~0 — **aditiva** | 1,010 | ~0 — **aditiva** |
| equidad | 0,603 | **39,7 %** | 0,765 | **23,5 %** |

Barras cuyo IC contiene el cero: **10 de 30** en M1, **7 de 30** en M3 (una barra = un
índice; 5 parámetros × 2 índices × 3 salidas). *No recalcular desde `indices_*.csv`*: ese
fichero guarda con `%.6f` y los índices de orden 10⁻⁷ se redondean a cero, lo que da un
recuento distinto y equivocado.

---

## 3. Los cuatro resultados

### 3.1 La cota sobre la calibración interna queda establecida

El artículo afirma que ningún parámetro de calibración interna explica más del **0,9 %**
de la varianza de la ganancia. Sobre el caso de estudio, `b_mean` —el único parámetro
interno que sobrevive al diseño— da **ST = 0,0000** con extremo superior del intervalo en
**0,01 %** en ambas coberturas. La cota **se sostiene con dos órdenes de margen**.

Y hay que decirlo en positivo, porque es el resultado del ejercicio: sobre el GSA
sintético que originó la afirmación, ese mismo extremo daba **1,15 %** para `b_mean` y
**1,73 %** para `alpha_mean` — es decir, **la cota era indeterminable sobre los datos que
la produjeron y queda establecida sobre el caso de estudio**.

### 3.2 El recurso solar gobierna, y eso se conserva

`factor_PV` domina la ganancia y el autoconsumo en ambas coberturas, y sus intervalos
solapan con los del sintético. La afirmación central del artículo —que el valor lo
determina el recurso y no la calibración del modelo— sobrevive medida sobre datos reales.

### 3.3 Volumen y reparto se separan, y ahora está cuantificado

`PGB` da **ST = 0,0000 sobre la ganancia** y **ST = 0,879 sobre la equidad**. El piso de
la banda de precio no mueve un solo kWh del volumen transado y gobierna casi por completo
cómo se reparte el excedente.

Lo refuerza la estructura de la varianza: la ganancia y el autoconsumo son **aditivos**
—cada parámetro actúa por su cuenta— mientras la equidad está dominada por
**interacciones**, que se comen el 39,7 % de su varianza en M1. Es la misma separación que
la tesis ya documenta por la vía del ciclo de período 2, ahora con un mecanismo distinto.

Y depende de la cobertura: la interacción en equidad cae del **39,7 % al 23,5 %** al pasar
de M1 a M3, mientras el S1 de `PGB` sube de 0,376 a 0,539. Con poca cobertura el reparto
depende de cómo se combinan los parámetros; con cobertura alta el precio de bolsa lo
explica cada vez más por sí solo.

### 3.4 El mecanismo del lado corto: predicción enunciada y verificada

`factor_D` sobre la ganancia era la **única discrepancia** con el sintético en M1:

| | ST (factor_D, ganancia) | vs sintético 0,1001 ± 0,044 |
|---|---|---|
| M1 (19,1 %) | 0,0094 ± 0,0038 | **NO solapa** |
| M3 (91,2 %) | 0,1593 ± 0,0436 | **solapa** |

La explicación se enunció antes de tener M3: con 19,1 % de cobertura el lado corto son
siempre los vendedores, de modo que variar la demanda apenas mueve el volumen transable;
el cuello de botella es la generación. La predicción era que con 91,2 % `factor_D`
recuperaría peso. **Recupera un factor 17 y aterriza exactamente sobre el valor del
sintético**, que es el régimen donde ambos lados están largos. `factor_PV` cede en
paralelo (0,847 → 0,667) y `PGS` sube (0,184 → 0,233).

Con M3, **las tres comparables del panel de ganancia solapan**: no queda ninguna
discrepancia real/sintético sin explicar.

---

## 4. Qué hay que cambiar en el artículo y en la tesis

### 4.1 Números a sustituir (§III-E y §IV-B del artículo, §7.10 de la tesis)

| Publicado | Medido sobre el caso de estudio (M1) |
|---|---|
| `factor_PV` S1 = 0,732 ± 0,208 · ST = 0,817 ± 0,207 | **S1 = 0,827 ± 0,203 · ST = 0,847 ± 0,174** |
| autoconsumo ST = 0,871 ± 0,253 | **0,737 ± 0,171** |
| `factor_D` en autoconsumo ST = 0,243 | **0,269 ± 0,065** |
| `PGB` en equidad S1 = 0,673 · ST = 0,916 ± 0,259 | **S1 = 0,376 ± 0,175 · ST = 0,879 ± 0,307** |
| `b_mean` ST = 0,004 | **0,0000 ± 0,0000** |
| «17 de 36 barras con IC que cruza cero» | **10 de 30** (M1) · **7 de 30** (M3) |
| cota del 0,9 % | **0,01 %**, sostenida en el extremo superior |

### 4.2 Afirmaciones a eliminar, no a actualizar

**`alpha_mean` con ST = 0,008.** No existe en el caso de estudio: el orquestador no pasa
`alpha` en datos reales (`main_simulation.py:252-257`), el programa de respuesta a la
demanda está apagado. Ese número es del caso sintético. Consecuencia que hay que declarar:
**del caso de estudio no se puede afirmar nada sobre flexibilidad de demanda.**

**`pi_ppa` con «cero exacto».** Su índice es cero *por construcción*, no por medición:
solo entra en C2 y ninguna de las tres salidas proviene de C2. Presentarlo como hallazgo
es presentar una tautología como evidencia.

### 4.3 Añadir

- El mecanismo del lado corto (§3.4), con la predicción y su verificación.
- La separación volumen/reparto cuantificada (§3.3).
- La reproducción independiente entre plataformas (§1).

---

## 5. Limitaciones a declarar

**Seis diferencias simultáneas con el sintético.** Los datos, el hipercubo (5 parámetros
frente a 7), el soporte de PGS, `a = c = 0`, la clasificación de prosumidores y la serie
de bolsa. Una discrepancia no es atribuible a los datos sin más análisis.

**El soporte de PGS es un barrido de estrés, no la incertidumbre tarifaria real.** Bajo el
barrido la matriz de liquidación recorre [512,1 – 1081,8]; el nominal 906,27 cae en el
percentil 76,6, de modo que el diseño explora −33,8 % por debajo y solo +10,3 % por
encima; y el tramo [600, 671] no es alcanzable con los cargos regulados vigentes. Los 13
meses del CSV Cedenar solo recorren [871,9 – 928,9], un ±3 %.

**No hay índices de segundo orden.** Con `calc_second_order=False` se sabe *cuánta*
interacción hay en la equidad pero no *entre qué parámetros*. Medirlo costaría 1 536
evaluaciones por cobertura.

**La equidad es un balance con signo, no una fracción.**
`equity_index = (ΣS_i − ΣSR_j)/(ΣS_i + ΣSR_j)`, acotado en [−1, +1]. Los valores negativos
—25 muestras (2,8 %) en M1, 50 (5,6 %) en M3, mínimos de −0,595 y −0,729— significan que
los vendedores capturaron más excedente que los compradores. Se doblan al subir la
cobertura, lo que es coherente con que haya más excedente que repartir. **En M3 el
dominante de la equidad no separa del segundo** (margen −0,0083): no debe citarse un
dominante para esa salida en esa cobertura.

**Incertidumbre numérica del solucionador.** Apretando tolerancias tres órdenes, el
volumen se mueve 0,068 % y el reparto 0,160 %. Quitar el techo de `max_step` no cambia
nada (idéntico hasta 1,4×10⁻¹⁴). BDF y Radau no son aplicables a este sistema —dan
autoconsumos de 2 205 y 264 093, imposibles para un cociente en [0,1]— porque el lado
derecho no es suave.

**Corrección de criterio declarada.** M3 disparaba dos alarmas `S1<0` sobre
`ganancia/b_mean` y `sc/PGB` por márgenes de 1,1×10⁻⁵ y 2,7×10⁻⁵, en parámetros cuyo ST es
1,19×10⁻⁷ y 7,65×10⁻⁷. Se añadió un suelo de resolución —el mismo 0,05 que el módulo ya
usaba para declarar un par «irresoluble»— que clasifica esas alarmas como **inmateriales**:
siguen listadas en el informe, pero no bloquean el veredicto. **La corrección se
identificó después de ver M3**, se aplicó a ambas coberturas y **no altera ningún índice**
(verificado). M1 satisfacía el criterio original por +8×10⁻⁵, un margen del mismo orden:
el criterio decidía la validez de 896 evaluaciones en el quinto decimal.

---

## 6. Deuda técnica del módulo (no afecta a ningún número)

1. **`comun.py` · `huella_datos`** mete la ruta absoluta en el hash, de modo que el mismo
   volumen visto desde dos puntos de montaje da huellas distintas y una corrida no se puede
   reanudar entre ellos. Debería hashear solo el inventario relativo y los tamaños.
2. **`core/replicator_sellers.py:157`** justifica `_max_step = 2e-4` citando
   `VEL_GRAD_GSA = 1e3`, pero producción corre con `VEL_GRAD = 1e6` (línea 62, porque
   `_fast_mode = False`). Verificado inocuo; el comentario induce a error.
3. **`core/replicator_sellers.py:158-165`** usa `sol.y[:, -1]` sin comprobar finitud. Y
   `sol.success` no serviría: LSODA devuelve `True` con el estado en NaN (verificado).
   Haría falta `np.isfinite(sol.y)`.
4. **`analysis/global_sensitivity.py:9`** describe `ie_p2p` como «fracción» cuando es un
   balance con signo en [−1, +1].
5. **`3_analizar.py`** escribe `indices_*.csv` con `%.6f`, lo que redondea a cero los
   índices de orden 10⁻⁷ y hace que un recuento hecho desde el CSV no coincida con el del
   informe. Debería usar formato significativo.

---

## 7. Los ficheros

Irreemplazables, van siempre en pareja:

```
muestras_M1_full_n128_s42.csv + .meta.json
muestras_M3_full_n128_s42.csv + .meta.json
```

Derivados, se regeneran en segundos con `analizar`: `indices_*.csv`,
`comparacion_*.csv`, `INFORME_*.md`.

El `.meta.json` de M1 lleva una `nota_procedencia`: la corrida se inició en un contenedor
(`/proyecto/MedicionesMTE_v3`) y se reanudó desde el host tras 487 de 896 evaluaciones. Se
verificó que N, T, cobertura, media de bolsa, `pi_gs` y la huella de diseño coincidían
antes de actualizar la huella de datos. La reanudación quedó además validada de forma
independiente: el análisis regenera la matriz de Saltelli desde la semilla y la compara
fila a fila, y pasa.
