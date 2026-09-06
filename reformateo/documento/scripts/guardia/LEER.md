# La medición del guardia físico

Es la condición previa que impone la decisión CAL-45: **medir qué marcaría el
guardia antes de fijarle ninguna banda**. Fijar un número y ver después qué
recoge es el error del piso del percentil que la decisión retira.

Se corre sobre el crudo de dos minutos de los veinte medidores en el horizonte
canónico, del 4 de abril al 16 de diciembre de 2025, es decir, 122.880
horas-serie y unos 3,6 millones de muestras.

## Cómo se vuelve a correr

Los tres pasos toman como argumento una carpeta de trabajo, donde el primero
deja una caché por medidor que los otros dos releen:

```powershell
python carga_crudo.py         <carpeta>   # ~26 s, 1,7 GB de CSV a 20 pickles
python analisis_guardia.py    <carpeta>   # primera pasada, bandas en kW y %
python analisis_guardia_2.py  <carpeta>   # segunda pasada, la buena
python diagnostico_anomalias.py <carpeta> # qué hay detrás de cada marca
```

La segunda pasada corrige dos supuestos de la primera y **es la que respalda las
cifras publicadas**. La primera se conserva porque es la que prueba que el factor
de potencia y la banda asimétrica de tensión no sirven.

## Qué corrige la segunda pasada

1. **El nominal de tensión se elige por muestra** entre 127, 220 y 440 V. La
   primera pasada lo elegía por medidor entre 127 y 120, y le asignaba 120 V al
   circuito secundario de Udenar, que mide a 220.
2. **La discrepancia de la suma de fases se mide en pasos del propio registro**
   del medidor, que van de 0,050 a 0,402 kW según el aparato, y no en kilovatios
   ni en porcentaje. Es lo que separa el ruido de cuantización del fallo: en
   porcentaje la comprobación marca el 90 % del horizonte, en pasos marca 50
   muestras.

## Las salidas

| Fichero | Qué tiene |
|---|---|
| `pasada2.txt` | La lectura completa de la segunda pasada, que es la que hay que leer primero |
| `censo2_por_medidor.csv` | Muestras y horas que marca cada banda en cada uno de los veinte medidores |
| `censo2_pipeline.csv` | Lo mismo restringido a las diez series que el modelo usa, por frontera |
| `detalle2_pipeline.csv` | Una fila por hora marcada, con la tensión, la frecuencia y la discrepancia que la marcó |
| `once_horas.csv` | Las once horas que el criterio viejo retira, bajo cada comprobación |
| `censo_total_20_medidores.csv` | Primera pasada. Es donde se ve que el factor de potencia marca 64.823 horas |
| `diagnostico.txt` | Qué hay detrás de cada marca: los episodios de tensión, las excursiones de frecuencia y el medidor con dos escalas de H-27 |

No se guarda el detalle muestra a muestra, que pesa 58 MB y se regenera con la
primera pasada.
