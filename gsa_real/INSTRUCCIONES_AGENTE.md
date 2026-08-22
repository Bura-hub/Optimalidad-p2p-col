# Instrucciones para el agente que supervisa la corrida

**Tu trabajo es vigilar una corrida de ~10 h, no mejorarla.** Léelas enteras antes de
actuar. Si algo no está aquí, pregunta en vez de decidir.

---

## Qué está corriendo y por qué importa

Un análisis global de sensibilidad (Sobol/Saltelli) de 896 evaluaciones sobre los datos
reales del MTE, en `gsa_real/`. Cada evaluación resuelve un mercado P2P sobre 6 144 horas.
El contexto completo está en `gsa_real/LEEME.md` y `gsa_real/MONTAJE_SERVIDOR.md`.

El resultado alimenta correcciones a una tesis y a un artículo enviado a revista. **Un
número equivocado que llegue a publicarse cuesta mucho más que una corrida perdida.** De
ahí que casi todo abajo sea una prohibición.

---

## Lo que NO puedes hacer

Ninguna de estas tiene excepción. Si crees haber encontrado un motivo para saltártela,
para y pregunta.

1. **No modifiques ningún fichero de `core/`, `scenarios/`, `data/` ni `analysis/`.**
   Ese es el núcleo numérico, validado contra el programa MATLAB original. Un cambio ahí
   invalida la trazabilidad de la tesis entera, aunque "solo" sea una optimización.
2. **No modifiques `analysis/global_sensitivity.py`.** El GSA sintético se conserva a
   propósito: es la referencia de comparación y hay un *golden test* que depende de él.
3. **No modifiques los guiones de `gsa_real/`.** Pasaron cuatro rondas de auditoría
   independiente. Si detectas un fallo, repórtalo; no lo arregles a mitad de corrida.
4. **No borres ni edites nada de `gsa_real/salidas/`.** El `.csv` de muestras es el activo
   real: regenerarlo cuesta la corrida entera. El `.meta.json` que lo acompaña es
   imprescindible — sin él, el análisis se niega a correr.
5. **No lances una segunda corrida en paralelo.** Compiten por los mismos núcleos y no se
   gana nada. M1 y M3 van en secuencia.
6. **No "optimices" nada.** Ni el número de workers hacia arriba, ni el solucionador, ni
   la GPU. Con 30 workers sobre 32 núcleos y BLAS fijado a un hilo, la máquina ya está en
   su óptimo práctico: los arreglos del integrador son de ~30 flotantes y cualquier
   paralelismo adicional solo añade sincronización.

## Lo que SÍ puedes hacer, sin preguntar

```bash
tail -f gsa_real/salidas/run_gsa_<TAG>_n128_s42.log
wc -l  gsa_real/salidas/muestras_<TAG>_n128_s42.csv     # progreso
grep -c '\[xm_csv\]' gsa_real/salidas/workers/*.log     # debe ser ~0
free -g ; uptime ; pgrep -fc 2_correr_gsa.py
```

Ese `grep` comprueba que la caché funciona. **Si sale un número grande, para la corrida**:
significa que cada evaluación está releyendo 1,7 GB de disco y algo va mal.

---

## Si corres dentro de un contenedor (lee esto primero)

Puede que no tengas `ps`, `pgrep` ni CLI de docker, y que la corrida viva en **otro**
espacio de PIDs — el host, o el servicio `gsa`. Compruébalo:

```bash
command -v pgrep ps docker || echo "sin herramientas de proceso"
ls /proyecto/gsa_real/salidas/ 2>/dev/null || ls gsa_real/salidas/
```

Si es tu caso, **tu vigilancia es por FICHEROS, no por procesos**, y cambia lo siguiente:

- **Avance** = crecimiento del CSV, no presencia de un PID:
  ```bash
  wc -l gsa_real/salidas/muestras_<TAG>_n128_s42.csv    # dos veces, con 20 min entre medias
  date -r gsa_real/salidas/muestras_<TAG>_n128_s42.csv  # mtime: cuándo se escribió la última fila
  ```
- **Carga** = `cat /proc/loadavg`. Con 30 workers debe rondar 30. Si cae a ~1 y el CSV no
  crece, la corrida murió.
- **NO puedes matar huérfanos ni relanzar.** El escenario B exige `pkill` en el espacio de
  PIDs correcto. Si detectas `POOL ROTO` en el log, **reporta y para**: dile al autor los
  comandos exactos que hay que ejecutar y en qué máquina, pero no los ejecutes a ciegas.

Un `pgrep` que no encuentra el proceso **no significa que la corrida haya muerto** si está
en otro contenedor. No confundas «no lo veo» con «no existe»: decídelo por el CSV y el
`loadavg`, nunca por la ausencia de PID.

## Los tres escenarios que tienes que saber resolver

### A · El proceso muere o el log se queda quieto más de una hora

Comprueba primero que de verdad está parado (`wc -l` del CSV dos veces separadas por
20 min). Si no avanza:

```bash
pgrep -f 2_correr_gsa.py          # ¿sigue vivo?
tail -50 gsa_real/salidas/run_gsa_<TAG>_n128_s42.log
```

Si murió, relanza tal cual — `reanudar` retoma lo que falta **y reintenta lo que falló**:

```bash
bash gsa_real/run_servidor.sh reanudar <COB> full 128 <mismo timeout>
```

### B · `POOL ROTO` en el log

Un worker murió (típicamente el OOM-killer). `ProcessPoolExecutor` **no reemplaza
workers**: se rompe el pool entero. Y hay un detalle que importa — el proceso *nieto* que
estaba calculando **sobrevive huérfano**, comiendo un núcleo, invisible al árbol del
principal.

```bash
pgrep -f 2_correr_gsa.py          # revisar y matar lo que quede
pkill -f 2_correr_gsa.py
rm -f gsa_real/salidas/.lock_*
WORKERS=20 bash gsa_real/run_servidor.sh reanudar <COB> full 128 <timeout>
```

Baja `WORKERS`, no lo subas. Si vuelve a romperse, baja más y avisa.

### C · Muchos `timeout` en la columna `motivo`

```bash
cut -d, -f11 gsa_real/salidas/muestras_<TAG>_n128_s42.csv | sort | uniq -c
```

Si los timeouts pasan del 10 % del diseño, los índices salen no concluyentes. Sube el
timeout y reanuda:

```bash
bash gsa_real/run_servidor.sh reanudar <COB> full 128 <timeout mayor>
```

---

## Códigos de salida: la señal legible por máquina

| Código de `correr` | Significa | Qué hacer |
|---|---|---|
| 0 | terminó completa | pasar a `analizar` |
| 4 | se rompió el pool | escenario B |
| 5 | quedó incompleta | `reanudar` con el mismo timeout |
| 6 | se interrumpió | `reanudar` |

| Código de `analizar` | Significa |
|---|---|
| 0 | la corrida cumple las condiciones de validez |
| 3 | hay alarmas o no las cumple — **leer el informe antes de citar nada** |
| 1 | abortó por procedencia: el fichero no corresponde al diseño |

**Un `analizar` que devuelva 3 no es un fallo tuyo ni hay que "arreglarlo".** Es el
módulo negándose a emitir un veredicto que los datos no sostienen. Reporta el informe tal
cual.

---

## Cuando termine

Reporta, sin interpretarlo:

1. El código de salida de cada paso.
2. Las últimas 30 líneas del log de cada corrida.
3. El recuento de `motivo` del CSV (el `cut ... | uniq -c` de arriba).
4. El `INFORME_<TAG>.md` completo de cada cobertura.
5. `ls -la gsa_real/salidas/`.

No saques conclusiones sobre los índices. Esa lectura la hace el autor contra la tesis y
el artículo, que es donde está el contexto para saber qué significan.
