"""
El precio de los contratos bilaterales, publicado por XM (CAL-51).

POR QUE EXISTE. El escenario del contrato bilateral no tenia precio propio: su
excedente se valoraba a la bolsa horaria, que es lo que hace el escenario de
mercado mayorista, y por eso los dos daban **el mismo resultado al ultimo
digito**. El articulo 23 numeral 2 literal a de la Resolucion CREG 174 dice
que en esa alternativa «el precio de venta es pactado libremente»: sin un
precio pactado no hay escenario, hay una copia del vecino.

DE DONDE SALE, y no hay que postularlo. XM publica el precio promedio
ponderado de los contratos por tipo de mercado. El asesor regulatorio lo
senalo en la reunion preparatoria del foro con su ruta exacta, y el fichero
**llevaba meses en el repositorio sin que ninguna linea lo leyera**.

Eso sustituye el postulado del factor de reparto, que era el parametro libre
mas atacable de la tesis, por una serie publica, mensual y citable.

QUE SE USA. La columna del **mercado no regulado**, porque el literal a exige
que la energia se destine a la atencion exclusiva de usuarios no regulados. En
el horizonte va de 283,3 a 295,2 COP/kWh.

GRANULARIDAD. Mensual, constante dentro del mes, igual que la tarifa. Es lo
que la fuente publica: un promedio ponderado del mes.

Y FALLA EN VOZ ALTA si falta un mes del horizonte. Es la leccion de H-50, el
fallo mas silencioso que este proyecto ha encontrado: un dato ausente que se
rellena solo produce una corrida entera de cifras inventadas con codigo de
salida cero.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
FUENTE = AQUI / ("XM_Energía y Precios transados en contratos con destino a "
                 "Mercado Regulado y No Regulado.xlsx")
COL_NO_REGULADO = "PPP Mercado No Regulado [COP/kWh]"
COL_REGULADO = "PPP Mercado Regulado [COP/kWh]"

# Banda de cordura para el horizonte de la tesis. No es una tolerancia: es un
# aviso de que la fuente cambio de unidades o de columna.
MINIMO, MAXIMO = 150.0, 600.0


def carga(ruta: Optional[Path] = None) -> pd.DataFrame:
    """La serie mensual, indexada por mes en formato de ano y mes.

    La hoja trae al final unas filas de filtros que no son datos; se descartan
    por no tener fecha valida.
    """
    f = Path(ruta) if ruta else FUENTE
    if not f.exists():
        raise FileNotFoundError(
            f"no esta la serie de contratos en {f}. La publica XM en su portal "
            f"de informacion: precios de contratos por tipo de mercado.")
    d = pd.read_excel(f)
    fechas = pd.to_datetime(d["Mes"], errors="coerce")
    d = d[fechas.notna()].copy()
    d["mes"] = pd.to_datetime(d["Mes"]).dt.strftime("%Y-%m")
    d = d[["mes", COL_NO_REGULADO, COL_REGULADO]].rename(columns={
        COL_NO_REGULADO: "no_regulado", COL_REGULADO: "regulado"})
    return d.sort_values("mes").reset_index(drop=True)


def cobertura(t_inicio: str, t_fin: str,
              ruta: Optional[Path] = None) -> dict:
    """Que meses del rango tiene la serie y cuales le faltan.

    Se llama ANTES de correr, no despues. Un mes ausente detiene la corrida.
    """
    d = carga(ruta)
    meses = pd.period_range(pd.Timestamp(t_inicio), pd.Timestamp(t_fin),
                            freq="M").strftime("%Y-%m").tolist()
    hay = set(d.mes)
    faltan = [m for m in meses if m not in hay]
    v = d[d.mes.isin(meses)]["no_regulado"].to_numpy(dtype=float)
    fuera = [float(x) for x in v if not (MINIMO <= x <= MAXIMO)]
    return dict(meses=meses, cargados=[m for m in meses if m in hay],
                faltan=faltan, fuera_de_banda=fuera,
                minimo=float(v.min()) if v.size else float("nan"),
                maximo=float(v.max()) if v.size else float("nan"))


def precio_horario(index, descuento: float = 1.0,
                   ruta: Optional[Path] = None) -> np.ndarray:
    """Vector (T,) con el precio de contrato de cada hora del indice.

    Constante dentro del mes, que es la granularidad de la fuente. Mismo
    patron que la tarifa mensual por agente.

    EL SUPUESTO QUE HAY QUE DECLARAR, y es el mas fragil de este modulo. La
    serie es el promedio ponderado de **los contratos que se transan en el
    mercado mayorista**, en su mayoria grandes generadores vendiendo a
    comercializadores. Usarla como el precio que recibiria una instalacion
    solar de escala institucional por su excedente es un supuesto, y
    probablemente generoso: nadie le paga a un autogenerador pequeno el mismo
    precio que a una central.

    Medido sobre el horizonte, con el descuento en uno:

        contrato   media 287,4   desviacion   3,6
        bolsa      media 181,8   desviacion 139,6

    y la bolsa solo supera al contrato en el 11,6 % de las horas. **El
    contrato domina a la bolsa por partida doble**, paga mas y varia menos, lo
    que deja el escenario de mercado mayorista trivialmente peor. Si
    contratar fuera siempre mejor, nadie se expondria al mercado.

    Por eso el `descuento` existe y por eso su valor **no se elige, se barre**:
    es el factor por el que un autogenerador negocia por debajo de la
    referencia del mercado. Con uno se usa la referencia tal cual, que es el
    caso mas favorable al contrato y el que hay que declarar como tal.

    **Va como consulta al asesor**, junto con la pregunta de si existe una
    referencia publicada para autogeneradores de pequena escala.
    """
    if not 0.0 < descuento <= 1.5:
        raise ValueError(f"descuento={descuento}; se espera un factor "
                         f"razonable sobre la referencia del mercado")
    idx = pd.DatetimeIndex(index)
    d = carga(ruta).set_index("mes")["no_regulado"]
    meses = idx.strftime("%Y-%m")
    faltan = sorted(set(meses) - set(d.index))
    if faltan:
        raise ValueError(
            f"la serie de contratos de XM no tiene {len(faltan)} mes(es) del "
            f"horizonte: {', '.join(faltan)}. Seguir rellenaria el hueco con "
            f"un valor inventado y la corrida saldria con cifras que nadie "
            f"podria rastrear. Reexporta el indicador. Ver H-50.")
    v = d.reindex(meses).to_numpy(dtype=float)
    malos = v[(v < MINIMO) | (v > MAXIMO)]
    if malos.size:
        raise ValueError(
            f"{malos.size} valores de contrato fuera de la banda de cordura "
            f"[{MINIMO:.0f}; {MAXIMO:.0f}] COP/kWh. Suele significar que la "
            f"fuente cambio de unidades o de columna.")
    return v * float(descuento)
