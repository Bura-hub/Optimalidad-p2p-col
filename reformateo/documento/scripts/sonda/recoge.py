"""
Recogida de resultados con plazo y escritura incremental.

Nace de un incidente del 2026-09-07. Una medicion de 160 tareas resolvio 158
en 17,7 minutos y se quedo bloqueada en las dos ultimas, que consumieron 81
minutos de procesador cada una sin acabar. Los otros ocho procesos estaban
parados esperandolas. Como la sonda escribia el fichero SOLO AL FINAL, cortar
la corrida costaba las 158 horas ya resueltas.

Son dos defectos distintos y los dos se corrigen aqui:

  1. **No hay cota de tiempo.** La via acoplada no la tiene: sobre datos
     reales hay horas que resuelven en 47 segundos y horas que no acaban en
     3.500. Una hora que el integrador no resuelve **es un dato**, no un
     motivo para perder la medicion entera.

  2. **No hay escritura incremental.** Perder lo hecho porque falta lo ultimo
     es evitable con una linea.

  3. **El plazo era TOTAL, y eso no basta.** Anadido el 2026-09-08 tras una
     tanda de 240 tareas que resolvio 230 en 26 minutos y consumio otros 29
     esperando por TRES, con siete de los diez procesos ociosos. Lo que hace
     falta es un plazo POR TAREA, medido desde la ultima terminacion: mientras
     sigan llegando resultados hay trabajo sano, y en cuanto dejan de llegar
     lo que queda esta atascado. Con el, esa medicion habria cerrado en 26
     minutos en vez de 55.

Este modulo da las tres: recoge por terminacion, escribe cada fila en cuanto
llega, y cuando se agota cualquiera de los dos plazos devuelve lo que hay
anotando las tareas que no llegaron y diciendo cual de los dos corto. Nunca se
pierde nada y nunca se espera indefinidamente.
"""
from __future__ import annotations

import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Optional

import pandas as pd

LATIDO = 5.0   # cada cuanto se despierta el bucle a mirar los plazos


def recoge(funcion, tareas, procesos: int, destino: Path,
           plazo_min: float = 45.0, cada: int = 10,
           describe=lambda t: str(t),
           plazo_tarea_min: Optional[float] = None) -> pd.DataFrame:
    """Corre `funcion` sobre `tareas` y devuelve las filas que se obtuvieron.

    Hay DOS plazos y cortan por motivos distintos:

    `plazo_min` es el plazo TOTAL de la medicion.

    `plazo_tarea_min` corta cuando pasa ese tiempo **sin que termine ninguna
    tarea**. Es el que de verdad importa con la via acoplada, y se mide desde
    la ultima terminacion porque mientras sigan llegando resultados hay
    trabajo sano en curso.

    Sin el segundo, una sola hora atascada bloquea la medicion hasta el plazo
    total con los demas procesos ociosos: el 2026-09-08 una tanda de 240
    tareas resolvio 230 en 26 minutos y consumio otros 29 esperando por
    TRES, con siete procesos parados.

    En los dos casos, las tareas que no llegaron se anotan con
    `resuelta=False` y la medicion sigue adelante con lo que tiene.

    `destino` recibe las filas segun llegan, de modo que un corte no cuesta
    mas que la ultima.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    filas, t0 = [], time.time()
    limite = plazo_min * 60.0
    espera = plazo_tarea_min * 60.0 if plazo_tarea_min else float("inf")
    hechas, motivo = 0, None

    with ProcessPoolExecutor(max_workers=procesos) as ex:
        pend = {ex.submit(funcion, t): t for t in tareas}
        vivas, ultimo = set(pend), time.time()
        while vivas:
            ahora = time.time()
            if ahora - t0 >= limite:
                motivo = f"el plazo TOTAL de {plazo_min:.0f} min"
                break
            if ahora - ultimo >= espera:
                motivo = (f"el plazo POR TAREA de {plazo_tarea_min:.1f} min "
                          f"sin que termine ninguna")
                break
            listas, vivas = wait(vivas, timeout=LATIDO,
                                 return_when=FIRST_COMPLETED)
            if not listas:
                continue
            ultimo = time.time()
            for fut in listas:
                filas.extend(fut.result())
                hechas += 1
                if hechas % cada == 0 or hechas == len(tareas):
                    pd.DataFrame(filas).to_csv(destino, index=False)
                    seg = time.time() - t0
                    print(f"    {hechas}/{len(tareas)}  ({seg/60:.1f} min, "
                          f"faltan ~"
                          f"{seg/hechas*(len(tareas)-hechas)/60:.0f})",
                          flush=True)

        if motivo:
            colgadas = [pend[f] for f in vivas]
            print(flush=True)
            print(f"  CORTE por {motivo}, a los "
                  f"{(time.time()-t0)/60:.1f} min con {hechas} de "
                  f"{len(tareas)} tareas hechas.", flush=True)
            print(f"  {len(colgadas)} no resolvieron. No es un fallo del "
                  f"sistema: la via acoplada no tiene cota de tiempo por hora "
                  f"y unas pocas horas se le atragantan.", flush=True)
            for t in colgadas[:10]:
                print(f"    sin resolver: {describe(t)}", flush=True)
            for t in colgadas:
                filas.append(dict(zip(("cobertura", "hora"), t[:2]))
                             | {"resuelta": False,
                                "motivo": "no resolvio en el plazo"})
            # HAY QUE MATARLOS, y no basta con cancelar.
            #
            # Un trabajador atascado esta dentro del integrador, es decir en
            # codigo nativo, y no atiende la cancelacion. Con
            # `shutdown(wait=False, cancel_futures=True)` la sonda imprime su
            # resultado y **el proceso se queda colgado al salir**, porque al
            # cerrar el interprete se espera a los hijos vivos. Paso el
            # 2026-09-07: once procesos sobrevivieron a la medicion y dos
            # seguian moliendo la misma hora cuarenta minutos despues.
            #
            # Se toca la interioridad del ejecutor a proposito, porque no
            # expone otra via.
            for f in pend:
                f.cancel()
            for proc in list(getattr(ex, "_processes", {}).values()):
                if proc.is_alive():
                    proc.terminate()
            ex.shutdown(wait=False, cancel_futures=True)
            print(f"  {len(colgadas)} trabajadores cerrados a la brava.",
                  flush=True)

    d = pd.DataFrame(filas)
    d.to_csv(destino, index=False)
    return d
