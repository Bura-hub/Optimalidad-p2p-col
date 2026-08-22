# Montaje en el servidor, desde cero

El servidor no tiene nada. Esto lo deja listo. Léelo entero antes de empezar: son
cuatro pasos y el orden importa.

**Contexto en una frase:** vas a correr un análisis global de sensibilidad (Sobol/Saltelli)
sobre los datos reales del MTE, porque el que hay publicado se calculó sobre un caso
sintético de 6 agentes y 24 horas, y la tesis y el artículo lo narran como si
caracterizara el *benchmark* de 6 144 h. El detalle está en `LEEME.md`.

---

## Qué necesita el módulo, y de dónde sale cada cosa

| Pieza | Tamaño | De dónde |
|---|---|---|
| Código del proyecto (`core/`, `scenarios/`, `data/`, `analysis/`, `main_simulation.py`) | ~15 MB | **GitHub** — verificado: los 20 módulos que carga una evaluación están todos versionados |
| `gsa_real/` | 130 KB | **Copiar a mano** (no está en git) |
| `validacion_convergencia/salidas/sensibilidad/sobol_intervalos.csv` | 2,3 KB | **Copiar a mano** (gitignorado) |
| `MedicionesMTE_v3/` | 1,7 GB · 73 CSV | **Copiar a mano** (nunca se commitea, por diseño) |

El CSV de la referencia sintética no es imprescindible —el análisis lo detecta y omite la
comparación— pero **sin él se pierde el contraste con el GSA sintético, que es el motivo de
todo el ejercicio**. Cópialo.

---

## Paso 1 — Clonar y montar el entorno

```bash
cd /home/brayan_lopez
git clone https://github.com/Bura-hub/Optimalidad-p2p-col.git sistemabl
cd sistemabl
git log --oneline -1          # debe decir dc7c0e7

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

El lanzador detecta `.venv/bin/python` por su cuenta; no hace falta activarlo.

## Paso 2 — Copiar las tres piezas que no vienen del repo

Desde tu máquina:

```bash
# 1 y 2: el módulo y la referencia (juntos, ~132 KB)
tar czf gsa_paquete.tgz \
    gsa_real/ \
    validacion_convergencia/salidas/sensibilidad/sobol_intervalos.csv
scp gsa_paquete.tgz brayan_lopez@<servidor>:/home/brayan_lopez/sistemabl/

# 3: los datos (1,7 GB). rsync y no scp: reanuda si se corta.
rsync -avP MedicionesMTE_v3/ \
    brayan_lopez@<servidor>:/home/brayan_lopez/sistemabl/MedicionesMTE_v3/
```

En el servidor:

```bash
cd /home/brayan_lopez/sistemabl
tar xzf gsa_paquete.tgz && rm gsa_paquete.tgz

# El .sh corre en Linux: un CRLF lo rompe con un «no such file» desconcertante.
# El tar preserva los bytes, pero compruébalo igual — cuesta un segundo.
grep -c $'\r' gsa_real/run_servidor.sh          # tiene que ser 0
# si no lo es:  sed -i 's/\r$//' gsa_real/run_servidor.sh
```

## Paso 3 — Verificar el entorno. **No lo saltes.**

```bash
bash gsa_real/run_servidor.sh entorno
```

Comprueba en segundos: las cuatro dependencias, que el cierre de imports del proyecto está
completo, que `MTE_ROOT` tiene los 73 CSV y las cinco instituciones, que están los cuatro
CSV de tarifas y precios que vienen del repo, y que existe la referencia sintética. Además
imprime núcleos, RAM y disco, y cuántos procesos abriría el árbol.

Sale con **0** si está listo y con **1** si no. Cada cosa que falla aquí cuesta segundos;
descubierta a mitad de una corrida de 17 h cuesta la corrida.

## Paso 4 — Los tres pasos del análisis, por cobertura

Vas a correr **M1 y M3**. Son dos corridas independientes y hay que hacerlas **en
secuencia**: lanzarlas a la vez las hace competir por los mismos núcleos y no se gana nada.

```bash
# ── M1 (totalizadores de campus, 19,1 % de cobertura) ──
bash gsa_real/run_servidor.sh calibrar M1 full 128
bash gsa_real/run_servidor.sh correr   M1 full 128 <timeout del paso anterior>
bash gsa_real/run_servidor.sh analizar M1 full 128

# ── M3 (submedidores del circuito fotovoltaico, 91,2 %) ──
bash gsa_real/run_servidor.sh calibrar M3 full 128
bash gsa_real/run_servidor.sh correr   M3 full 128 <timeout del paso anterior>
bash gsa_real/run_servidor.sh analizar M3 full 128
```

**`calibrar` no se salta**, y hay que correrlo **para cada cobertura**: M3 tiene otra matriz
de demanda y otro costo por evaluación.

> ### El paso 1 subestima el tiempo, y conviene saberlo antes
>
> `calibrar` cronometra sus cinco sondas **en secuencia**, una detrás de otra, sin
> competencia por la CPU. La corrida real lanza `nproc−2` evaluaciones a la vez.
>
> Medido: sobre 744 h una evaluación tarda **120 s sola** y **200–320 s con cuatro
> concurrentes**. Es decir, la proyección de `calibrar` se queda corta por un factor de
> aproximadamente **2**.
>
> Si te dice «cabe en 12 h», cuenta con más. Si no cabe, **acorta el horizonte antes que
> bajar `n_base`**: con `n_base` bajo los intervalos de confianza salen tan anchos que la
> comparación con el sintético deja de distinguir nada, y entonces la corrida no responde
> la pregunta que la motivó.

---

## Mientras corre

```bash
tail -f gsa_real/salidas/run_gsa_M1_full_n128_s42.log
wc -l  gsa_real/salidas/muestras_M1_full_n128_s42.csv    # progreso
grep -c '\[xm_csv\]' gsa_real/salidas/workers/*.log      # debería ser ~0
```

Ese último comprueba que la caché funciona. Si sale un número grande, cada evaluación está
releyendo 1,7 GB y hay que parar y revisarlo.

## Los códigos de salida son la señal legible por máquina

| Acción | Código | Significa |
|---|---|---|
| `entorno` | 0 / 1 | listo / faltan cosas |
| `correr` | 0 | terminó completa |
| | 4 | **se rompió el pool** (un worker muerto por OOM) |
| | 5 | quedó incompleta |
| | 6 | se interrumpió |
| `analizar` | 0 | la corrida cumple las condiciones de validez |
| | 3 | hay alarmas, o no las cumple — **léete el informe antes de citar nada** |

**Si `correr` devuelve 4**, hay un detalle que importa: `ProcessPoolExecutor` no reemplaza
workers, y al morir uno se rompe el pool entero. Peor: el proceso *nieto* que estaba
calculando **sobrevive huérfano** comiendo un núcleo. Antes de reanudar:

```bash
pgrep -f 2_correr_gsa.py        # revisar y matar lo que quede
WORKERS=<menos> bash gsa_real/run_servidor.sh reanudar M1 full 128 <timeout>
```

`reanudar` retoma lo que falta **y reintenta las que fallaron**.

---

## Qué devolver

Todo `gsa_real/salidas/`, y de ahí estos dos por cobertura, **juntos**:

```
muestras_M1_full_n128_s42.csv        ← el activo real: regenerarlo cuesta la corrida entera
muestras_M1_full_n128_s42.meta.json  ← sin él, el análisis se niega a correr
muestras_M3_full_n128_s42.csv
muestras_M3_full_n128_s42.meta.json
```

Los índices, el informe y los CSV de comparación se recalculan de ellos en segundos.

---

## Dos cosas que no hay que hacer

- **No modificar `analysis/global_sensitivity.py`.** El GSA sintético se conserva a
  propósito: es la referencia de comparación y hay un *golden test* que depende de él.
- **No esperar que `main_simulation.py --data real --full` haga el GSA.** No lo hace, y lo
  rechaza explícitamente (`main_simulation.py:1505`). Ese es, literalmente, el problema que
  este módulo existe para resolver.
