# Mediciones del modelo base — montaje en el servidor

Léelo entero antes de empezar: son cuatro pasos y el orden importa.

**Contexto en una frase.** Hay que decidir qué fuente del modelo base se
traduce, porque el modelo publicado y el modelo programado **no son el mismo
modelo**, y la medición que lo decide es cara: cada hora de mercado cuesta
unos 47 segundos por la vía acoplada. El detalle está en `HALLAZGOS.md`,
hallazgos H-39 a H-42, y la decisión en `docs/adr/0049-…`.

---

## Qué se mide, y qué decide cada cosa

| Acción | Cuesta | Qué decide |
|---|---|---|
| `compuertas` | segundos | Que el código llegó entero. Si falla algo, para. |
| `caso` | ~5 min | Cuántas de las doce afirmaciones del artículo reproduce cada una de las tres formas. **No necesita los datos del MTE.** |
| `eficiencia` | ~1 h por frontera | Cuánto del ahorro alcanzable captura el mercado, con muestra grande |
| `competencia` | ~2 h por frontera | **La que decide.** Si la forma publicada deja los precios pegados a las cotas con datos reales |

La cuestión que `competencia` resuelve es esta: la forma publicada es la
única que reproduce el caso del artículo, pero allí sus precios cayeron
pegados a las cotas, que es justo el defecto que la vía acoplada venía a
corregir. Si con datos reales pasa lo mismo, no sirve, y estaríamos
cambiando un defecto por otro.

---

## Qué necesita, y de dónde sale cada cosa

| Pieza | Tamaño | De dónde |
|---|---|---|
| Código del proyecto | ~15 MB | **GitHub**, rama `feature/cal43-depuracion-fase-a` |
| `MedicionesMTE/` | 1,7 GB · 73 CSV | **Copiar a mano** (nunca se commitea, por diseño) |
| `data/ASC_pdfs/` | 1,8 MB | **Opcional**, y solo si se van a reextraer tarifas. El CSV derivado sí viene del repositorio |

La acción `caso` no necesita nada de eso: el caso publicado trae sus propios
datos, en las tablas del artículo. Si solo quieres la respuesta rápida,
corre esa.

---

## Paso 1 — Clonar y montar el entorno

```bash
cd /home/brayan_lopez
git clone https://github.com/Bura-hub/Optimalidad-p2p-col.git sistemabl
cd sistemabl
git checkout feature/cal43-depuracion-fase-a
git log --oneline -1

bash modelo_base/run_servidor.sh entorno
```

El lanzador detecta `.venv/bin/python` por su cuenta; no hace falta
activarlo.

## Paso 2 — Copiar las mediciones

Desde tu máquina:

```bash
rsync -av --progress MedicionesMTE/ servidor:/home/brayan_lopez/sistemabl/MedicionesMTE/
```

Y en el servidor, antes de medir:

```bash
export MTE_ROOT=/home/brayan_lopez/sistemabl/MedicionesMTE
```

## Paso 3 — Medir

```bash
bash modelo_base/run_servidor.sh compuertas     # primero, siempre
bash modelo_base/run_servidor.sh caso           # barato, y ya responde bastante
bash modelo_base/run_servidor.sh todo 60        # lo demás, ~6 h
```

Cada sonda escribe su log fechado en `modelo_base/logs/` y su tabla en
`reformateo/documento/scripts/sonda/salidas/`. Las tablas se guardan **hora a
hora**, de modo que si algo se corta no se pierde lo hecho.

**Aviso sobre el costo.** La vía acoplada no tiene cota de tiempo por hora:
sobre el caso base hay una hora que no termina en 420 segundos mientras otra
igual resuelve en 47. Si un log lleva más de quince minutos sin línea nueva,
no es un cuelgue del sistema, es esa patología. Anótalo y sigue.

Con `nohup` para que sobreviva a la sesión:

```bash
nohup bash modelo_base/run_servidor.sh todo 60 > modelo_base/logs/todo.log 2>&1 &
tail -f modelo_base/logs/todo.log
```

## Paso 4 — Traer los resultados

```bash
bash modelo_base/run_servidor.sh recoger
```

Deja un `modelo_base/resultados_<fecha>.tar.gz` con las tablas y los logs.
Tráelo y descomprímelo en la raíz del repositorio, en tu máquina.

---

## Qué mirar al recibirlos

1. **`caso_*.log`** — cuántas de las doce afirmaciones reproduce cada forma.
   Medido en local: agregada 8, publicada 11. Si el servidor da otra cosa,
   eso es un hallazgo.
2. **`competencia_*.csv`** — las columnas `pegados` y `pos_media`. Si la
   forma publicada pega los precios a las cotas mucho más que la agregada,
   **no se adopta** y hay que buscar otra salida.
3. **`eficiencia_*.csv`** — la columna `efvol_aco` debe salir 100 % en todas
   las horas, las dos formas. Si no, es un hallazgo.

---

## Lo que este paquete NO hace

- **No corre el horizonte completo.** La corrida canónica tiene siete
  motivos acumulados que la obligan, pero uno de ellos es justo la decisión
  que estas mediciones resuelven. Primero se decide, luego se corre.
- **No toca el canon.** Ninguna cifra publicada cambia con esto.
