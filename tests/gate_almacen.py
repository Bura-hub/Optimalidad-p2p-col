"""
Compuerta del almacen de la corrida.

QUE PRUEBA, y la tercera es la que de verdad importa:

  1. Ida y vuelta. Lo que se escribe es lo que se lee, en las cuatro tablas.
  2. Los pares de energia casi nula SOBREVIVEN. El desglose de produccion los
     descarta bajo un umbral y con ellos se pierde la prueba de que el par
     existio; aqui tienen que estar.
  3. **Reproduccion cruzada.** Una hora sacada del almacen y la misma hora
     re-resuelta por la sonda coinciden. Es lo que prueba que el almacen
     describe la corrida y no otra cosa. Sin esta comprobacion, un almacen
     que mienta pasa desapercibido para siempre.
  4. Las dos guardas. Una hora sin resolver queda anotada con su motivo, y
     una solucion no finita NUNCA se anota como resuelta (C-160).
  5. Los multiplicadores llegan. Son opt-in en el nucleo y son los que dicen
     que restriccion muerde; si se pierden, la figura de convergencia enseña
     el precio deteniendose sin poder decir por que.

Uso:
    python tests/gate_almacen.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from core.almacen import Almacen, hora, lee  # noqa: E402

NOMBRES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


class _Traj:
    """Una trayectoria de juguete con la forma de la del nucleo."""

    def __init__(self, J, I, n_t):
        self.t = np.linspace(0.0, 0.05, n_t)
        self.pi_t = np.tile(np.linspace(300.0, 700.0, n_t), (I, 1))
        self.P_t = np.ones((J, I, n_t)) * 0.5
        self.Wj_t = np.linspace(-10.0, -5.0, n_t)
        self.Wi_t = np.linspace(5.0, 9.0, n_t)
        self.W_t = self.Wj_t + self.Wi_t
        self.lam_t = np.ones((J, n_t)) * 2.0
        self.bet_t = np.ones((I, n_t)) * 3.0
        self.lam_filt_t = np.ones((J, n_t)) * 2.5
        self.bet_filt_t = np.ones((I, n_t)) * 3.5


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="gate_almacen_"))
    fallos = []
    try:
        alm = Almacen(tmp, cobertura="m1", inicio="2025-04-04")
        sids, bids = [0, 1], [2, 3, 4]
        # Un par con energia CASI NULA a proposito: es el que produccion tira.
        P = np.array([[1.5, 0.8, 1e-12], [0.4, 2.1, 0.0]])
        pi = np.array([700.0, 690.0, 710.0])
        techo = np.array([731.1, 731.1, 777.2])
        piso = np.array([674.0, 596.1])

        alm.anota_hora(100, resuelta=True, volumen=float(P.sum()),
                       precio_medio=float(pi.mean()), retirados=0,
                       iteraciones=2, residuo=1e-7)
        alm.anota_flujos(100, P, pi, sids, bids, NOMBRES,
                         techo_i=techo, piso_j=piso)
        alm.anota_trayectoria(100, _Traj(2, 3, 25), sids, bids, NOMBRES)
        alm.anota_escenarios(100, {"P2P": np.arange(5.0),
                                   "C1": np.arange(5.0) * 2}, NOMBRES)
        alm.sin_resolver(101, "no resolvio en el plazo")
        # No finita: no debe entrar como resuelta.
        alm.anota_flujos(102, np.array([[np.nan]]), np.array([700.0]),
                         [0], [1], NOMBRES)
        alm.cierra()

        # 1 · ida y vuelta
        h = lee(tmp, "m1", "horas")
        f = lee(tmp, "m1", "flujos")
        t = lee(tmp, "m1", "trayectorias")
        e = lee(tmp, "m1", "escenarios")
        ok1 = len(h) == 3 and len(f) == 6 and len(t) == 25 and len(e) == 10
        print(f"  1 · ida y vuelta   horas {len(h)} · flujos {len(f)} · "
              f"trayectoria {len(t)} · escenarios {len(e)}   "
              f"{'ok' if ok1 else 'FALLA'}")
        if not ok1:
            fallos.append("las cuatro tablas no tienen las filas esperadas")

        # 2 · el par casi nulo sobrevive
        casi = f[(f.vendedor == "Udenar") & (f.comprador == "Cesmag")]
        ok2 = len(casi) == 1 and 0 <= float(casi.kwh.iloc[0]) < 1e-6
        print(f"  2 · el par de energia casi nula sobrevive   "
              f"{'ok' if ok2 else 'FALLA'}")
        if not ok2:
            fallos.append("el par de energia casi nula se perdio")

        # 3 · las guardas
        no_res = h[~h.resuelta.fillna(False)]
        ok3 = len(no_res) == 2 and set(no_res.hora) == {101, 102}
        print(f"  3 · las guardas   {len(no_res)} horas anotadas sin "
              f"resolver, {sorted(no_res.hora)}   {'ok' if ok3 else 'FALLA'}")
        if not ok3:
            fallos.append("las guardas no anotan lo que deben")
        if 102 in set(f.hora):
            fallos.append("una solucion no finita entro como flujo")

        # 3b · UNA FILA POR HORA, y ninguna no finita como resuelta (C-173).
        #
        # La corrida oficial escribio DOS filas para doce horas: una que decia
        # «resuelta» con el volumen y el precio vacios, y otra que decia que no
        # resolvia. Pasaba porque la guarda vivia en la anotacion de los flujos
        # y la corrida llama antes a la de la hora. Quien contara horas
        # resueltas las contaba dos veces.
        #
        # Se fuerza aqui el mismo orden que usa produccion: primero la hora
        # como resuelta con un valor no finito, y despues los flujos.
        alm2 = Almacen(tmp / "inv", cobertura="m1", inicio="2025-04-04")
        alm2.anota_hora(200, resuelta=True, vendedores=2, compradores=3,
                        volumen=float("nan"), precio_medio=700.0)
        alm2.anota_flujos(200, np.array([[float("nan")]]), np.array([700.0]),
                          [0], [1], NOMBRES)
        alm2.anota_hora(201, resuelta=True, vendedores=2, compradores=3,
                        volumen=5.0, precio_medio=700.0)
        alm2.anota_hora(201, resuelta=True, vendedores=9, compradores=9,
                        volumen=99.0, precio_medio=1.0)
        alm2.cierra()
        h2 = lee(tmp / "inv", "m1", "horas")
        rep = int(h2["hora"].duplicated().sum())
        mala = h2[(h2["resuelta"].fillna(False))
                  & (~np.isfinite(h2["volumen"].astype(float)))]
        ok3b = rep == 0 and len(mala) == 0 and len(h2) == 2
        print(f"  3b· una fila por hora   {len(h2)} filas, {rep} repetidas, "
              f"{len(mala)} resueltas con hueco   {'ok' if ok3b else 'FALLA'}")
        if not ok3b:
            fallos.append("la tabla de horas admite filas repetidas o huecos")

        # 4 · los multiplicadores llegan
        cols = set(t.columns)
        esperadas = {"lam_Udenar", "bet_UCC", "lam_filt_Mariana",
                     "bet_filt_Cesmag", "W", "W_vendedor", "W_comprador"}
        ok4 = esperadas <= cols
        print(f"  4 · multiplicadores y bienestar en la trayectoria   "
              f"{'ok' if ok4 else 'FALTAN ' + str(esperadas - cols)}")
        if not ok4:
            fallos.append("la trayectoria no trae los multiplicadores")

        # 5 · la llave permite pedir una hora, un dia o un mes
        uno = hora(tmp, "m1", 100)
        ok5 = (len(uno["flujos"]) == 6 and len(uno["trayectorias"]) == 25
               and str(h[h.hora == 100].mes.iloc[0]) == "2025-04")
        print(f"  5 · se puede pedir una hora concreta, y trae su mes   "
              f"{'ok' if ok5 else 'FALLA'}")
        if not ok5:
            fallos.append("no se puede recuperar una hora por su llave")

        print()
        if fallos:
            for x in fallos:
                print(f"  FALLA: {x}")
            return 1
        print("  ALMACEN EN VERDE: ida y vuelta, los pares casi nulos")
        print("  sobreviven, las guardas anotan, los multiplicadores llegan")
        print("  y cualquier hora se recupera por su llave.")
        print()
        print("  PENDIENTE, y es la comprobacion que de verdad importa: la")
        print("  reproduccion cruzada contra la sonda, que exige el motor")
        print("  cableado. Ver el plan, fase 2.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
