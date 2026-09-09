"""
El almacen de la corrida: todo lo que hoy se tira.

POR QUE EXISTE. `_run_hour_worker` obtiene, para cada hora, la trayectoria
completa de la integracion con sus multiplicadores ya calculados, y **se queda
con dos matrices y un escalar**. Todo lo demas muere al salir de la funcion.
La consecuencia es que ninguna figura de convergencia puede dibujarse sin
volver a simular, y que ninguna via de produccion devuelve la trayectoria de
una hora elegida: la que las guarda escoge las horas sola y solo dos.

QUE GUARDA. Cuatro tablas, todas con la cobertura, la hora y la fecha como
llave, de modo que se pueda pedir cualquier hora, dia o mes despues:

  horas         una fila por hora: papeles, banda de cada agente, precio,
                volumen, retirados, iteraciones, residuo, bienestar,
                excedente, equidad, reparto, factura y el tramo de cada
                vendedor.
  flujos        una fila por hora, vendedor y comprador. SIN filtrar los
                pares de energia casi nula, que hoy se pierden en el
                desglose y con ellos la prueba de que el par existio.
  trayectorias  una fila por hora y paso de integracion: tiempo, precio por
                comprador, potencia por par, bienestar de los dos lados y
                **los cuatro multiplicadores**, que son los que dicen que
                restriccion esta mordiendo.
  escenarios    una fila por hora, escenario y agente: lo que ese mecanismo
                le liquida a ese agente en esa hora (C-165).
  agentes       una fila por hora y agente (C-166): su demanda, su
                generacion, su autoconsumo, lo que compra y vende a la RED,
                su techo, su piso y **el papel que jugo** esa hora. Es lo que
                la liquidacion por institucion necesita y lo unico que
                permite dibujar un dia entero con quien entra y quien se
                retira.

CUANTO OCUPA, medido antes de escribir una linea: las trayectorias de las
2.937 horas activas de las dos fronteras, con multiplicadores, son 95 MB en
precision sencilla y de 16 a 24 comprimidas. Cabe guardarlo todo.

POR QUE PARQUET Y POR PARTES. El formato ya se usa en el analisis de
sensibilidad, de modo que no se introduce una dependencia nueva. Y se escribe
**por partes**, un fichero cada N horas, por la leccion que este proyecto ya
pago dos veces: una medicion larga que solo escribe al final cuesta la tanda
entera cuando algo se cae. Leer una carpeta de partes es transparente.

LAS DOS GUARDAS, que vienen de fallos reales:
  · una hora que no resuelve se anota como NO resuelta con su motivo, igual
    que hace la recogida de las sondas;
  · una solucion no finita **nunca** se anota como resuelta, porque las sumas
    descartan esos valores en silencio y el resultado saldria sesgado sin que
    nada lo dijera. Ver C-160.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

TABLAS = ("horas", "flujos", "trayectorias", "escenarios", "agentes")

# Cada cuantas horas se vuelca una parte. Con 6.144 horas salen unas doce
# partes por tabla, que es un compromiso entre no perder trabajo y no llenar
# la carpeta de ficheros diminutos.
POR_PARTE = 500


def _comprueba_motor(comprimir: str = "zstd") -> None:
    """Que se puede escribir parquet, ANTES de calcular nada (C-171).

    POR QUE EXISTE. En el servidor faltaba la biblioteca que escribe parquet, y
    el fallo no se descubrio al arrancar: se descubrio **trece minutos
    despues**, cuando el primer volcado por partes intento escribir. La corrida
    entera se perdio, y con ella se cayeron en cascada la liquidacion, la
    equidad y las figuras que leen del almacen.

    Una comprobacion que cuesta milisegundos y que ahorra una corrida entera no
    es una precaucion: es donde tenia que estar desde el principio. Escribe una
    tabla de una fila en memoria y la lee de vuelta.

    Se comprueba tambien la COMPRESION, y no solo el motor: no todas las
    instalaciones traen el mismo juego de compresores, y descubrir eso al
    volcar cuesta lo mismo que descubrir que falta el motor.
    """
    import io as _io

    try:
        b = _io.BytesIO()
        pd.DataFrame({"x": [1.0]}).to_parquet(b, index=False,
                                              compression=comprimir)
        b.seek(0)
        pd.read_parquet(b)
    except Exception as exc:                              # noqa: BLE001
        raise RuntimeError(
            "el almacen no puede escribir parquet con compresion "
            f"{comprimir!r}: {exc}" + chr(10) +
            "Instalalo antes de correr, o la corrida entera se perdera al "
            "primer volcado:" + chr(10) +
            "    .venv/bin/pip install pyarrow" + chr(10) +
            "Esta comprobacion existe porque eso ya paso una vez, y costo una "
            "corrida de las dos fronteras. Ver C-171.") from exc


def _finito(*arrays) -> bool:
    """Cierto solo si TODO lo que se le pasa es numerico y finito."""
    for a in arrays:
        if a is None:
            continue
        v = np.asarray(a, dtype=float)
        if v.size and not np.all(np.isfinite(v)):
            return False
    return True


@dataclass
class Almacen:
    """Acumula las cuatro tablas de una cobertura y las vuelca por partes.

    Uso::

        alm = Almacen(destino, cobertura="m1", inicio="2025-04-04")
        alm.anota_hora(k, ...)
        alm.anota_flujos(k, ...)
        alm.anota_trayectoria(k, tr, sids, bids)
        alm.cierra()
    """

    destino: Path
    cobertura: str
    inicio: str = "2025-04-04"
    paso_horas: float = 1.0
    comprimir: str = "zstd"

    _buf: dict = field(default_factory=lambda: {t: [] for t in TABLAS})
    _partes: dict = field(default_factory=lambda: {t: 0 for t in TABLAS})
    _t0: Optional[pd.Timestamp] = None
    # Las horas que ya tienen fila. El invariante es una por hora.
    _vistas: set = field(default_factory=set)

    def __post_init__(self):
        self.destino = Path(self.destino)
        self._t0 = pd.Timestamp(self.inicio)
        _comprueba_motor(self.comprimir)
        for t in TABLAS:
            (self.destino / self.cobertura / t).mkdir(parents=True,
                                                      exist_ok=True)

    # ── la llave, que es lo que permite pedir cualquier hora o mes ────────
    def _llave(self, k: int) -> dict:
        fecha = self._t0 + pd.Timedelta(hours=float(k) * self.paso_horas)
        return dict(cobertura=self.cobertura, hora=int(k),
                    fecha=fecha, mes=fecha.strftime("%Y-%m"),
                    hora_del_dia=int(fecha.hour),
                    dia_semana=int(fecha.dayofweek))

    # ── las cuatro anotaciones ────────────────────────────────────────────
    def anota_hora(self, k: int, **campos) -> None:
        """Una hora, UNA fila. Y ninguna hora no finita como resuelta.

        C-173. La guarda de C-160 vivia en la anotacion de los FLUJOS, y la
        corrida llama antes a esta: cuando la guarda saltaba, la fila que dice
        «resuelta» ya estaba escrita. El resultado eran DOS filas para la misma
        hora, una afirmando que resolvio con el volumen y el precio vacios y
        otra diciendo que no. Doce horas de 6.144 en la corrida oficial.

        Quien contara horas resueltas las contaba dos veces, y quien promediara
        arrastraba los huecos. Aqui la guarda esta donde tiene que estar.
        """
        numeros = [v for v in campos.values()
                   if isinstance(v, (int, float, np.floating, np.integer))
                   and not isinstance(v, (bool, np.bool_))]
        if campos.get("resuelta") and not _finito(*numeros):
            return self.sin_resolver(k, "solucion no finita")
        self._anota_una(k, campos)

    def sin_resolver(self, k: int, motivo: str) -> None:
        """Una hora que no resuelve ES UN DATO. Se anota con su motivo."""
        self._anota_una(k, dict(resuelta=False, motivo=motivo))

    def _anota_una(self, k: int, campos: dict) -> None:
        """Escribe la fila de esa hora si no hay ya una.

        El invariante de la tabla de horas es **una fila por hora**. Sin el,
        cualquier recuento y cualquier promedio salen mal, y salen mal en
        silencio: una tabla con filas de mas se lee igual de bien que una
        correcta.
        """
        if k in self._vistas:
            return
        self._vistas.add(int(k))
        self._empuja("horas", dict(self._llave(k), **campos))

    def anota_flujos(self, k: int, P, pi, sids, bids, nombres,
                     techo_i=None, piso_j=None) -> None:
        """Una fila por par. **Sin filtrar los de energia casi nula.**

        El desglose de produccion los descarta bajo un umbral, y con ellos se
        pierde la prueba de que el par existio y de que el mercado los
        considero. Aqui entran todos y el que lea decide.
        """
        P = np.asarray(P, dtype=float)
        pi = np.asarray(pi, dtype=float)
        if not _finito(P, pi):
            return self.sin_resolver(k, "solucion no finita")
        base = self._llave(k)
        for a, j in enumerate(sids):
            for b, i in enumerate(bids):
                e = float(P[a, b])
                p = float(pi[b])
                fila = dict(base, vendedor=nombres[j], comprador=nombres[i],
                            kwh=e, precio=p, valor=e * p)
                if techo_i is not None:
                    fila["techo_comprador"] = float(techo_i[b])
                    fila["ahorro_comprador"] = (float(techo_i[b]) - p) * e
                if piso_j is not None:
                    fila["piso_vendedor"] = float(piso_j[a])
                    fila["prima_vendedor"] = (p - float(piso_j[a])) * e
                self._empuja("flujos", fila)

    def anota_trayectoria(self, k: int, tr, sids, bids, nombres) -> None:
        """Una fila por paso de integracion, con los multiplicadores.

        Sin ellos se ve el precio detenerse sin poder decir por que se
        detiene ahi, que es justamente lo que una figura de convergencia
        tiene que explicar.
        """
        if tr is None or getattr(tr, "t", None) is None:
            return
        t = np.asarray(tr.t, dtype=float)
        if not _finito(t, tr.pi_t, tr.P_t):
            return self.sin_resolver(k, "trayectoria no finita")
        base = self._llave(k)
        J, I = len(sids), len(bids)
        for n in range(len(t)):
            fila = dict(base, paso=n, t=float(t[n]))
            for b in range(I):
                fila[f"precio_{nombres[bids[b]]}"] = float(tr.pi_t[b, n])
            for a in range(J):
                for b in range(I):
                    fila[f"P_{nombres[sids[a]]}_{nombres[bids[b]]}"] = \
                        float(tr.P_t[a, b, n])
            for nom, v in (("W", "W_t"), ("W_vendedor", "Wj_t"),
                           ("W_comprador", "Wi_t")):
                arr = getattr(tr, v, None)
                if arr is not None:
                    fila[nom] = float(np.asarray(arr, dtype=float)[n])
            # Los multiplicadores, si se pidieron. Son opt-in en el nucleo.
            for nom, v, ids in (("lam", "lam_t", sids), ("bet", "bet_t", bids),
                                ("lam_filt", "lam_filt_t", sids),
                                ("bet_filt", "bet_filt_t", bids)):
                arr = getattr(tr, v, None)
                if arr is None:
                    continue
                arr = np.asarray(arr, dtype=float)
                for q, idx in enumerate(ids):
                    fila[f"{nom}_{nombres[idx]}"] = float(arr[q, n])
            self._empuja("trayectorias", fila)

    def anota_escenarios(self, k: int, por_escenario: dict,
                         nombres) -> None:
        """Una fila por escenario y agente: lo que ese mecanismo le liquida."""
        base = self._llave(k)
        for esc, valores in por_escenario.items():
            v = np.asarray(valores, dtype=float)
            for n in range(len(v)):
                self._empuja("escenarios",
                             dict(base, escenario=esc, agente=nombres[n],
                                  valor=float(v[n])))

    def anota_agentes(self, k: int, nombres, D_k, G_k, techo_k, piso_k,
                      sids=(), bids=(), retirados=(),
                      compra_p2p=None, vende_p2p=None) -> None:
        """Una fila por agente: su energia, su banda y su papel en esa hora.

        POR QUE HACIA FALTA. Las otras tablas describen el MERCADO —quien
        transo con quien, a que precio, como convergio—, pero ninguna describe
        al AGENTE. Sin esto no se puede decir cuanto le cobra la red a una
        institucion por lo que importa ni a cuanto le paga lo que exporta, que
        es literalmente lo que el asesor pidio ver.

        EL PAPEL se anota como texto porque es lo que se lee en una figura:
        vendedor, comprador, retirado o inactivo. Un vendedor retirado por el
        criterio de participacion NO es lo mismo que uno que no tenia
        excedente, y confundirlos borra el efecto que ese criterio produce.
        """
        base = self._llave(k)
        D_k = np.asarray(D_k, dtype=float)
        G_k = np.asarray(G_k, dtype=float)
        te = np.asarray(techo_k, dtype=float)
        pi_ = np.asarray(piso_k, dtype=float)
        cp = (np.zeros(len(D_k)) if compra_p2p is None
              else np.asarray(compra_p2p, dtype=float))
        vp = (np.zeros(len(D_k)) if vende_p2p is None
              else np.asarray(vende_p2p, dtype=float))
        sids, bids, retirados = set(sids), set(bids), set(retirados)

        for n in range(len(D_k)):
            auto = float(min(max(G_k[n], 0.0), max(D_k[n], 0.0)))
            sobra = max(float(G_k[n]) - float(D_k[n]), 0.0)
            falta = max(float(D_k[n]) - float(G_k[n]), 0.0)
            if n in retirados:
                papel = "retirado"
            elif n in sids:
                papel = "vendedor"
            elif n in bids:
                papel = "comprador"
            else:
                papel = "inactivo"
            self._empuja("agentes", dict(
                base, agente=nombres[n], papel=papel,
                demanda=float(D_k[n]), generacion=float(G_k[n]),
                autoconsumo=auto, sobrante=sobra, faltante=falta,
                # Lo que de verdad cruza la frontera con la red, que es el
                # sobrante o el faltante MENOS lo que se resolvio dentro.
                vende_red=max(sobra - float(vp[n]), 0.0),
                compra_red=max(falta - float(cp[n]), 0.0),
                vende_p2p=float(vp[n]), compra_p2p=float(cp[n]),
                techo=float(te[n]), piso=float(pi_[n])))

    # ── volcado ───────────────────────────────────────────────────────────
    def _empuja(self, tabla: str, fila: dict) -> None:
        self._buf[tabla].append(fila)
        if len(self._buf[tabla]) >= POR_PARTE * 40:
            self._vuelca(tabla)

    def _vuelca(self, tabla: str) -> None:
        filas = self._buf[tabla]
        if not filas:
            return
        n = self._partes[tabla]
        ruta = self.destino / self.cobertura / tabla / f"parte_{n:04d}.parquet"
        d = pd.DataFrame(filas)
        # A precision sencilla: la mitad de espacio y muy por encima de lo que
        # cualquier figura necesita.
        for col in d.columns:
            if d[col].dtype == "float64":
                d[col] = d[col].astype("float32")
        d.to_parquet(ruta, index=False, compression=self.comprimir)
        self._partes[tabla] = n + 1
        self._buf[tabla] = []

    def cierra(self) -> dict:
        """Vuelca lo que quede y deja la nota de procedencia."""
        for t in TABLAS:
            self._vuelca(t)
        resumen = {t: self._partes[t] for t in TABLAS}
        nota = dict(cobertura=self.cobertura, inicio=self.inicio,
                    paso_horas=self.paso_horas, partes=resumen,
                    generado=str(pd.Timestamp.now()))
        (self.destino / self.cobertura / "almacen.json").write_text(
            json.dumps(nota, indent=2, ensure_ascii=False), encoding="utf-8")
        return resumen


# ── lectura ───────────────────────────────────────────────────────────────
def lee(destino, cobertura: str, tabla: str) -> pd.DataFrame:
    """Lee una tabla entera. Las partes son transparentes al lector."""
    if tabla not in TABLAS:
        raise ValueError(f"tabla {tabla!r}; hay {TABLAS}")
    carpeta = Path(destino) / cobertura / tabla
    partes = sorted(carpeta.glob("parte_*.parquet"))
    if not partes:
        raise FileNotFoundError(f"no hay partes en {carpeta}")
    d = pd.concat([pd.read_parquet(p) for p in partes], ignore_index=True)

    # C-173: los almacenes escritos ANTES de esta correccion pueden traer dos
    # filas para la misma hora, una diciendo «resuelta» con los numeros vacios
    # y otra diciendo que no resolvio. Aqui se normaliza al leer, y **se avisa**.
    #
    # Se conserva la fila que NO dice resuelta, porque es la verdadera: si la
    # solucion no era finita, esa hora no resolvio. Quedarse con la otra seria
    # contar como buena una hora sin volumen ni precio.
    #
    # Esto es un remiendo de lectura y esta declarado como tal. Existe porque la
    # corrida oficial de nueve meses ya estaba escrita cuando se encontro el
    # defecto, y volver a correrla cuesta horas. En cuanto haya una corrida
    # posterior a C-173, esta rama no encuentra nada que hacer.
    if tabla == "horas" and "hora" in d.columns and d["hora"].duplicated().any():
        antes = len(d)
        d = (d.sort_values("resuelta", na_position="first")
               .drop_duplicates("hora", keep="first")
               .sort_values("hora").reset_index(drop=True))
        print(f"    [C-173] el almacen de {cobertura} traia {antes - len(d)} "
              f"hora(s) con dos filas; se conserva la que dice que no resolvio")
    return d


def hora(destino, cobertura: str, k: int) -> dict:
    """Todo lo que el almacen sabe de UNA hora, para dibujarla sin simular."""
    out = {}
    for t in TABLAS:
        try:
            d = lee(destino, cobertura, t)
        except FileNotFoundError:
            continue
        out[t] = d[d.hora == int(k)].reset_index(drop=True)
    return out
