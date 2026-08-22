# Relevo nocturno — instrucciones de ejecución autónoma

El autor no está disponible. Puedes **ejecutar la secuencia de abajo y decidir según
lo que encuentres**, dentro de los límites de este documento. Fuera de ellos, para y
reporta.

Lee también `INSTRUCCIONES_AGENTE.md` (vigilancia) y `MONTAJE_SERVIDOR.md` (contexto).
Este documento manda sobre ambos donde se contradigan.

---

## PASO 0 — ¿Puedes ejecutar? Compruébalo antes de nada

Tú corres en un contenedor; la calibración se hizo en el host. Si lanzas desde aquí, la
corrida arranca **aquí**, en un entorno que nadie ha verificado.

```bash
bash gsa_real/run_servidor.sh entorno
```

- **Sale con 0 y dice `ENTORNO LISTO`** → puedes ejecutar todo lo de abajo.
- **Sale con 1, o falta el `.venv`, o `MTE_ROOT` no tiene los 73 CSV** → **NO ejecutes
  nada más**. Reporta exactamente qué falló y limítate a vigilar ficheros. En ese caso
  el autor tendrá que lanzar desde el host cuando vuelva.

Anota los núcleos que reporta. Deben ser **32 (usando 30)**. Si dice 1, el guion no
tiene el parche de `nproc` — para y reporta.

---

## PASO 1 — La compuerta: ¿son robustos los resultados? *(bloqueante)*

Hay una duda abierta sobre el integrador que **debe resolverse antes de gastar 16 h**.
Resumen: `core/replicator_sellers.py:157` fija `_max_step = 2e-4` justificándolo con
`VEL_GRAD_GSA=1e3`, pero producción corre con `VEL_GRAD=1e6` (línea 62, porque
`_fast_mode=False`). El comentario cita un régimen que no se usa. Además LSODA emite
avisos con `tolsf = NaN`, que **demuestran** estado no finito — la cota
`tolsf ≤ eps/rtol ≈ 2,2e-10` hace imposible ese mensaje con estado sano.

**Ya hay un resultado previo de esta compuerta**, obtenido en otra máquina (scipy 1.17.1;
el servidor tiene 1.15.3, y por eso hay que repetirlo aquí):

| configuración | ganancia | sc | ie |
|---|---:|---:|---:|
| producción | 7 384 672,917 | 0,212297 | 0,423569 |
| **sin `max_step`** | **7 384 672,917** | **0,212297** | **0,423569** |
| tol 1e-9/1e-12 | 7 381 933,418 | 0,212202 | 0,420137 |
| BDF | 1,26e11 | **3733,6** | 0,426282 |
| Radau | 1,11e13 | **323772,2** | 0,423173 |

Dos lecturas, y la segunda es una trampa que hay que evitar:

1. **Quitar el techo de `max_step` no cambia nada** (idéntico hasta 1,1e-14). La hipótesis
   del `_max_step` queda descartada: el techo nunca está activo porque LSODA elige pasos
   más pequeños por su cuenta. El comentario de la línea 157 está desactualizado pero es
   inocuo. Apretando tolerancias, la ganancia se mueve 0,037 % y el autoconsumo 0,045 %.
2. **BDF y Radau dan `sc` de 3 733 y 323 772.** El autoconsumo es un COCIENTE acotado en
   [0, 1]: esos valores son físicamente imposibles. No son respuestas alternativas, son
   basura — el lado derecho no es suave (lleva proyecciones al símplex y recortes) y el
   Newton de los métodos implícitos diverge sobre él. **No los tomes como referencia.**
   El guion ya los descarta automáticamente y los marca `INAPLICABLE`.

Lo que **no** está establecido es si eso cambia algún número publicado. Eso es lo que
mide este diagnóstico, contrastando cuatro integradores independientes:

```bash
export MTE_ROOT=$PWD/MedicionesMTE_v3 OMP_NUM_THREADS=1
.venv/bin/python gsa_real/diagnostico_robustez_solver.py \
    --cobertura M1 --horizonte mes:2025-08 --punto centro \
    2>&1 | tee gsa_real/salidas/robustez_centro.log
```

Tarda 15–40 min. **Decide por su código de salida:**

| Código | Veredicto | Qué haces |
|---|---|---|
| **0** | ROBUSTO, o robusto con matiz | **Sigue al paso 2.** Anota las dos discrepancias. |
| **1** | El **VOLUMEN** se mueve >0,1 % | **PARA. No lances nada.** Reporta la tabla. |
| **2** | SIN VEREDICTO | **PARA.** Reporta cuál configuración falló. |

El veredicto juzga **volumen** (`ganancia`, `sc`) y **reparto** (`ie`) por separado, y eso
es deliberado. Si el `ie` se mueve más que el volumen —esperable— **no frena nada**: la
tesis ya documenta que el ciclo de período 2 deja el reparto indeterminado mientras el
volumen es robusto. Sale por código 0 con la nota correspondiente.

Si sale 1, el hallazgo es grave y excede al GSA: las corridas canónicas de la tesis usan
el mismo módulo. No intentes arreglarlo. Reporta y detente.

Con el resultado previo de la otra máquina, **lo esperable aquí es 0**. Si te sale 1,
compara tu tabla con la de arriba antes de nada: si la diferencia está en BDF/Radau,
algo va mal en el descarte de inaplicables y hay que reportarlo, no obedecerlo.

Si sale 0, repítelo en la esquina degenerada para acotar el peor caso —**no es
bloqueante**, solo informativo; si tarda demasiado o falla, sigue igualmente:

```bash
.venv/bin/python gsa_real/diagnostico_robustez_solver.py \
    --cobertura M1 --horizonte mes:2025-08 --punto minimos \
    2>&1 | tee gsa_real/salidas/robustez_minimos.log
```

---

## PASO 2 — Calibrar M3 *(si no está hecho)*

```bash
ls gsa_real/salidas/calibracion_M3_full.json 2>/dev/null && echo "YA HECHA"
```

Si no existe:

```bash
bash gsa_real/run_servidor.sh calibrar M3 full 128
```

Tarda 1–2 h (M3 tiene 91,2 % de cobertura frente al 19,1 % de M1: mucho más mercado
activo, que es lo que encarece). Al terminar, **saca el timeout recomendado**:

```bash
grep -a "TIMEOUT RECOMENDADO\|CABE\|NO CABE" gsa_real/salidas/calibrar_M3_full.log
```

- Si dice **`NO CABE`** → no lances M3. Reporta y sigue solo con M1.
- Si dice **`CABE`** → usa el timeout que indique. **No reutilices el 12820 de M1.**

---

## PASO 3 — Correr M1

```bash
bash gsa_real/run_servidor.sh correr M1 full 128 12820
```

Ese 12820 sale de la calibración de M1, ya hecha (mediana 586,3 s, máxima 854,7 s,
5/5 sondas sin fallos, proyección 4,9 h con 30 procesos). **Espera 7–9 h reales** por la
contención, que la calibración no mide porque cronometra en secuencia.

El lanzador hace un preflight de segundos, deja el proceso en segundo plano y espera
hasta 180 s a que arranque el bucle. Si te dice `EL PROCESO MURIO AL ARRANCAR`, reporta
el log y para.

**Vigilancia** (por ficheros, que es lo que tienes):

```bash
wc -l  gsa_real/salidas/muestras_M1_full_n128_s42.csv   # crece hasta 897 (cabecera + 896)
date -r gsa_real/salidas/muestras_M1_full_n128_s42.csv  # cuándo se escribió la última fila
cat /proc/loadavg                                        # ~30 mientras corre
tail -5 gsa_real/salidas/run_gsa_M1_full_n128_s42.log
```

Comprueba cada 20–30 min. **Está viva si el CSV crece.** Un `pgrep` que no la encuentra
no prueba nada: puede estar en otro espacio de PIDs.

## PASO 4 — Analizar M1

Cuando el CSV llegue a 897 líneas y el log imprima el resumen:

```bash
bash gsa_real/run_servidor.sh analizar M1 full 128
```

| Código | Significa | Qué haces |
|---|---|---|
| **0** | cumple las condiciones de validez | sigue al paso 5 |
| **3** | hay alarmas, o no las cumple | **sigue igualmente al paso 5.** Guarda el informe. |
| **1** | abortó por procedencia | reporta y para |

**Un 3 NO es un fallo tuyo y no hay que arreglarlo.** Es el módulo negándose a emitir un
veredicto que los datos no sostienen. No toques nada para «hacer que pase».

## PASO 5 — Correr y analizar M3

Igual que 3 y 4, con `M3` y su propio timeout. Otras 8–14 h.

```bash
bash gsa_real/run_servidor.sh correr   M3 full 128 <timeout de su calibración>
# ...cuando termine:
bash gsa_real/run_servidor.sh analizar M3 full 128
```

**NUNCA solapes M1 y M3.** Cada una pide 30 de 32 núcleos; juntas son 122 procesos, con
26 GB libres eso aprieta, y si entra el OOM-killer te llevas las dos.

---

## Fallos: qué hacer sin preguntar

**`POOL ROTO` en el log, o `correr` devuelve 4.** Un worker murió (OOM). El pool entero
se rompe y el proceso *nieto* que calculaba **sobrevive huérfano** comiendo un núcleo.

```bash
pkill -f 2_correr_gsa.py 2>/dev/null || true
rm -f gsa_real/salidas/.lock_*
WORKERS=20 bash gsa_real/run_servidor.sh reanudar M1 full 128 12820
```

Baja `WORKERS`, nunca lo subas. Si se rompe otra vez, baja a 12 y **reporta**. A la
tercera, para. Si no puedes ejecutar `pkill` (no está en tu contenedor), **no reanudes**:
reporta y para, porque relanzar sobre huérfanos vivos empeora las cosas.

**El CSV no crece en 60 min y el `loadavg` cayó a ~1.** Murió. Relanza:

```bash
bash gsa_real/run_servidor.sh reanudar <COB> full 128 <mismo timeout>
```

`reanudar` retoma lo que falta y reintenta lo que falló. Es seguro repetirlo.

**Muchos `timeout` en la columna `motivo`.**

```bash
cut -d, -f11 gsa_real/salidas/muestras_M1_full_n128_s42.csv | sort | uniq -c
```

Con el timeout en 12820 s esto no debería pasar. Si pasa en más del 10 % del diseño,
reporta: significa que hay una región del hipercubo que no resuelve, y eso es un
resultado, no una avería.

---

## Prohibiciones. Ninguna tiene excepción

1. **No modifiques nada de `core/`, `scenarios/`, `data/` ni `analysis/`.** Es el núcleo
   validado contra el MATLAB original con una diferencia de 1,3×10⁻¹² kW. Un cambio ahí
   invalida la trazabilidad de la tesis entera, aunque sea «solo una optimización».
2. **No modifiques los guiones de `gsa_real/`.** Pasaron cuatro rondas de auditoría. Si
   encuentras un fallo, repórtalo; no lo arregles a mitad de corrida.
3. **No borres ni edites nada de `gsa_real/salidas/`.** El `.csv` de muestras es el
   activo real; el `.meta.json` es imprescindible para analizarlo.
4. **No subas `WORKERS` por encima de 30.** Es la «optimización» obvia al ver 32 núcleos
   y es contraproducente: el árbol ya son 61 procesos.
5. **No uses GPU ni intentes acelerar el solucionador.** El estado que integra son ~30
   flotantes; el lanzamiento de un kernel cuesta más que la aritmética.
6. **No cambies el diseño**: ni `n_base`, ni la semilla (42), ni los soportes, ni
   `calc_second_order`. Cambiar cualquiera invalida la comparación con el GSA sintético.
7. **Si dudas, para y reporta.** Nada de esto es urgente. Una noche perdida cuesta una
   noche; un número equivocado en la tesis cuesta mucho más.

---

## Qué reportar al final

Sin interpretarlo:

1. El código de salida de **cada** comando que ejecutaste, en orden.
2. El veredicto del paso 1 con su tabla de discrepancias.
3. Para cada cobertura: las últimas 30 líneas del log, el recuento de `motivo`, y el
   `INFORME_<TAG>.md` **completo**.
4. `ls -la gsa_real/salidas/`.
5. Cualquier decisión que tomaste y por qué.

**No saques conclusiones sobre los índices de Sobol.** Esa lectura la hace el autor
contra la tesis y el artículo, que es donde está el contexto para saber qué significan.
