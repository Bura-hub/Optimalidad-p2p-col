# `gsa_directo/` — el análisis de sensibilidad global, directo y sin emulador

Actividad 4.1 (y 4.2 por las brechas). Decisiones D73 a D79, aprobadas por el autor
el 2026-09-26. Diseño: `docs/superpowers/specs/2026-09-26-gsa-directo-design.md`.

## Qué es

El Sobol de Saltelli de segundo orden sobre **el modelo publicado**: cada evaluación
resuelve el mercado de las 6 144 horas por reposo en forma cerrada (D48), con los
defectos de producción (`sigma`, `uniforme`, `piso`, μ = 1), y liquida los ocho
escenarios, igual que la orden de la matriz canónica. No hay emulador ni integrador:
dos evaluaciones del mismo punto son idénticas al bit.

- **Seis entradas uniformes** (D74): `f_cv` [0,25; 2], `f_bolsa` [0,75; 4,0] (el techo
  PES va después del factor), `f_tarifa` [0,90; 1,10], `f_peaje` [0,85; 1,15], `e_G` y
  `e_D` [0,95; 1,05].
- **`f_cv` se rotula «descuento de comercializar sobre la permuta (art. 25)»** en todas
  las salidas (índices, S2, informe, meta, réplica). **No es el Cv de la tarifa**: es el
  factor sobre el componente de comercializar que el art. 25 descuenta de la permuta
  para el piso del vendedor, el mismo que usan C1, C4, el colectivo y los residuales.
- **Catorce salidas de comunidad** (D75); C2 y los conteos para las identidades; las
  brechas por institución solo con su probabilidad de inversión.
- **n = 2 048** en E0, E2 y E4; **512** en los otros nueve (D77). Los bloques son
  anidados: la curva de convergencia sale de la misma corrida.
- **El Sobol corre en doce casos, no en trece: CV2 queda fuera** (ronda de arreglos de
  la tarea G, I-1). CV2 es E0 con el costo de comercializar ×2, y el Sobol de E0 ya
  recorre `f_cv` ∈ [0,25; 2]; sobre CV2, `f_cv` volvería a multiplicar un Cv que ya
  viene ×2 y lo sacaría del rango aprobado (6 de 512 bloques con el piso de Cesmag
  negativo, 1,17 %, que detiene el análisis). CV2 sigue en la compuerta del punto base
  (el contraste con E0 a `f_cv = 2`, al peso) y en las deterministas. `correr.py` y el
  lanzador lo rechazan; `comun.CASOS_SOBOL` es la lista, y una prueba falla si vuelve.

## Qué no es

- No es el GSA de agosto: ese está en `_cuarentena/2026-09-26/gsa_real/` (D79), midió la
  vía alternada con PGB y sus índices son del canon de agosto. **No se cita.**
- No barre μ, σ, la cobertura ni el tamaño: μ va aparte (`deterministas.py`, D76), σ en
  `barrido_sigma`, y la cobertura y el tamaño son los ejes de la matriz.
- Nada de lo que produce es canon hasta que se registre en `Documentos/canon_2026-09/`.

## Las piezas

| Fichero | Qué hace |
|---|---|
| `comun.py` | entradas, rangos, salidas, los trece casos (la misma opción que `CASOS_MATRIZ` del lanzador), n por caso, huellas, la muestra |
| `evaluador.py` | `prepara_caso` (lo que `main()` hace antes del mercado, una vez por proceso) y `evalua` (una evaluación en un punto) |
| `correr.py` | la muestra de un caso, con pool de ventana acotada en orden de índice, CSV con `fsync`, `.meta.json`, `--reanudar`, `--humo`, `--verificar` (evaluador falso) y la parada temprana por bloques fallidos (código 8) |
| `analizar.py` | procedencia, descarte por bloques (umbral 1 %), índices anidados, S2, convergencia, probabilidad de inversión, CV, identidades e informe |
| `compuerta_punto_base.py` | los trece casos con los factores en 1 contra el canon, al peso; `--matriz` obligatoria y comprobada contra las huellas del canon 2026-09 |
| `replica.py` | ocho puntos (el base, el extremo **superior** de cada entrada y el vértice de máximos), dos veces en pools distintos: al bit. El 6.2 del diseño decía «los seis extremos»; basta uno por entrada para medir el determinismo, y se declara |
| `deterministas.py` | μ ∈ {0,5; 1; 2} y la bolsa de 2024 desplazada, en los trece casos |

## Cómo se corre

En el servidor, solo con el lanzador, que pone la contención:

```bash
export MATRIZ_CANON=SALIDAS_SERVIDOR/matriz_reposo    # la del 19 de septiembre; se comprueba
SECO=1 bash modelo_base/run_servidor.sh gsa_directo
CASOS="E0 E2" bash modelo_base/run_servidor.sh gsa_directo
```

La sección «El GSA directo» de `modelo_base/MONTAJE_SERVIDOR.md` tiene el detalle. En
local solo pruebas y humos cortos, siempre con `--salidas` y `--cache` en una carpeta
temporal:

```bash
python -m pytest tests/test_gsa_directo_*.py -q -k "not lenta"
python -u gsa_directo/correr.py --caso E0 --dia 2025-08-01 --humo 4 --procesos 2 \
    --salidas <tmp> --cache <tmp>
python -u gsa_directo/compuerta_punto_base.py --sin-escribir --cache <tmp> \
    --matriz SALIDAS_SERVIDOR/entrega_matriz_reposo_2026-09-19/SALIDAS_SERVIDOR/matriz_reposo
```

## Reglas de la corrida

- **Parada temprana.** `correr.py` cuenta los bloques con alguna evaluación fallida
  mientras escribe y para con **código 8** por uno de dos motivos, que distingue:
  **SEGURO**, en cuanto pasan del 1 % de los n_base del caso (el análisis lo rechazará),
  o **TASA**, si tras `max(16, min(n/4, 256))` bloques terminados los fallidos
  terminados pasan de 4 veces el umbral (sugiere un fallo sistemático; el análisis aún
  podría aceptarlo). El 4 sale del Monte Carlo de la ronda 2 (R-1): cero falsos
  positivos con un 0,5 % de fallos, y un caso roto al 5 % se detecta igual de pronto.
  Las evaluaciones son deterministas: `--reanudar` volvería a parar en el mismo punto,
  así que primero se miran los motivos; `--tolera-fallos` (`TOLERA_FALLOS=1` en el
  lanzador) sigue hasta el final y deja decidir al análisis.
- **El plan de la noche** corre los casos de diseño con su n (2 048) y aplaza a la noche
  siguiente, con su n, el que no cabe; solo recorta si el primero ni solo cabe.
- **Un caso no se amplía reutilizando sus filas.** Si el humo recortó E0 a 1 024 y luego
  se quiere 2 048, `correr.py` rechaza la corrida nueva (código 2) mientras exista la de
  1 024 en la carpeta del caso: la muestra de 2 048 se corre **entera**, tras mover la
  anterior. El lanzador retoma cada caso con el n con que empezó y avisa si no es el del
  plan.
- **No se hace `git pull` con un caso a medias**: las filas nuevas y las viejas serían de
  dos versiones del modelo. La meta guarda la lista de versiones del código
  (`codigos`) y `--reanudar` avisa si cambió.
- **La matriz del canon se pasa explícita** (`MATRIZ_CANON` en el lanzador, `--matriz`
  en la compuerta), y la compuerta comprueba la huella del libro de cada caso contra el
  canon 2026-09. Una comprobación sin dato de referencia cuenta como diferencia, salvo
  `OMITIR_SIN_REFERENCIA=1` (`--permite-omitir`), que la deja pasar con aviso.
- **Nada más escribe en `modelo_base/` ni en `SALIDAS_SERVIDOR/`** mientras corre la
  acción: la prueba del lanzador compara sus listados y pararía la noche.

## Lo que hay que saber al leer los resultados

- **P2P − C1 es una identidad** (H-70): ancho de banda por energía. Su ST sobre `f_cv`
  es una comprobación.
- Los niveles los gobierna la tarifa (ST ≈ 1); la robustez se lee en el coeficiente de
  variación y en las brechas.
- `f_cv` se aplica donde `main()` aplica `--factor-cv` (el piso, C1, C4, el colectivo,
  los residuales del mercado y del contrato), **no** en `cvm_component` de C5: así E0 con
  `f_cv = 2` reproduce CV2 al peso.
- **El piloto del diseño no es comparable en P2P − C5.** El piloto de 62 días escalaba
  también C5 (y el precio de su contrato) con `f_cv`; la corrida no, igual que `main()`
  según D7. Su índice total de 0,18 de `f_cv` sobre P2P − C5 no es un antecedente de lo
  que dará la corrida, y la lectura del apartado 3.2 del diseño sobre esa brecha cambiará
  en esa columna.
- La energía transada **sí** depende de `f_cv` (el piso decide quién entra), así que esa
  «identidad» del apartado 6.5 del diseño se informa y no detiene.
