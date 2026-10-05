"""
hora_resuelta.py — Una hora de E0 resuelta paso a paso con la forma cerrada
===========================================================================
Actividad 1.1 de la propuesta (revisión del modelo base y forma cerrada).
Cálculo DERIVADO del canon: no simula. Lee las tablas `horas`, `flujos` y
`agentes` del almacén de E0 de la matriz del 19 de septiembre (con huella en
`Documentos/canon_2026-09/HUELLAS.csv`, vía `atribucion_supuestos.almacen`),
toma la hora 256 (14 de abril de 2025, 16:00), la de la Figura C.1 del anexo C
y de `fig_hora_E0`, y RECALCULA a mano cada paso de la forma cerrada para
comprobar que da lo que el motor guardó:

  1. roles: vendedores con sobrante y compradores con faltante;
  2. piso del juego: oferta O(p) y demanda D(p) en cada piso de vendedor, de
     menor a mayor; el piso del juego es el menor p que hace máxima
     mín(O(p), D(p));
  3. volumen: el lado corto de quienes entran; lo que vende cada vendedor y lo
     que compra cada comprador; el emparejamiento P_ji = v_j q_i / V;
  4. precios: el presupuesto (suma de los precios de reposo de los
     compradores), el precio uniforme que conserva el ingreso de los
     vendedores, lo que paga cada comprador (con tope en su tarifa);
  5. reparto: prima de cada vendedor sobre su piso, ahorro de cada comprador
     bajo su techo; renta inframarginal y parte del juego; la banda de
     negociación de cada par por su energía suma el ahorro del intercambio.

COMPUERTAS (falla en voz alta; ningún `except`): cada valor recalculado es el
del almacén (energía a 1e-4 kWh, precios a 1e-3 COP/kWh, pesos a 0,01 COP), y
la banda por la energía es la prima más el ahorro.

Escribe en SALIDAS_SERVIDOR/hora_resuelta_2026-10-05/:
    hora_E0_256.csv   una fila por magnitud (paso, magnitud, agente, valor, unidad)
    resumen.md        los cinco pasos con sus cifras
    procedencia.txt   commit, versiones, huellas y compuertas, sin fecha

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/hora_resuelta.py

Actividad 1.1.
"""
from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[4]
AQUI = Path(__file__).resolve().parent
for _p in (str(RAIZ), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import atribucion_supuestos as AS  # noqa: E402

SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "hora_resuelta_2026-10-05"
CASO, HORA = "E0", 256
NOMBRE = {"Udenar": "Udenar", "Mariana": "Unimar", "UCC": "UCC", "HUDN": "HUDN", "Cesmag": "Unicesmag"}
COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[hora] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[hora]   OK  {msg}")


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.strip()


def piso_del_juego(pisos: dict, techos: dict, s: dict, d: dict) -> tuple[float, list]:
    """(piso del juego, recorrido [(p, O, D, mín)]): el menor p de los pisos de
    los vendedores que hace máxima mín(O(p), D(p))."""
    recorrido = []
    for p in sorted(set(pisos.values())):
        O = sum(s[j] for j in s if pisos[j] <= p)
        D = sum(d[i] for i in d if techos[i] >= p)
        recorrido.append((p, O, D, min(O, D)))
    mejor = max(r[3] for r in recorrido)
    p_star = min(r[0] for r in recorrido if r[3] >= mejor - 1e-12)
    return p_star, recorrido


def main() -> int:
    A = AS.almacen(CASO, "agentes")
    A = A[A.hora == HORA].copy()
    H = AS.almacen(CASO, "horas")
    H = H[H.hora == HORA].iloc[0]
    F = AS.almacen(CASO, "flujos")
    F = F[F.hora == HORA].copy()
    exige(len(A) == 5 and len(F) > 0, "la hora no está completa en el almacén")
    fecha = str(H.fecha)

    # 1. roles
    vend = A[A.sobrante > 1e-9]
    comp = A[A.faltante > 1e-9]
    s = dict(zip(vend.agente, vend.sobrante.astype(float)))
    d = dict(zip(comp.agente, comp.faltante.astype(float)))
    pisos = dict(zip(vend.agente, vend.piso.astype(float)))
    techos = dict(zip(comp.agente, comp.techo.astype(float)))
    exige(int(H.vendedores) == len(s) and int(H.compradores) == len(d), "roles distintos de los del almacén")
    ok(f"roles: {len(s)} vendedores y {len(d)} compradores, los del almacén")

    # 2. piso del juego
    p_star, recorrido = piso_del_juego(pisos, techos, s, d)
    exige(abs(p_star - float(H.piso_juego)) <= 1e-3, f"piso del juego {p_star} ≠ {H.piso_juego}")
    ok(f"piso del juego recalculado = el del almacén ({p_star:.4f} COP/kWh)")

    # 3. volumen y emparejamiento
    J = [j for j in s if pisos[j] <= p_star]
    I = [i for i in d if techos[i] >= p_star]
    O, D = sum(s[j] for j in J), sum(d[i] for i in I)
    V = min(O, D)
    exige(abs(V - float(H.volumen)) <= 1e-4, f"volumen {V} ≠ {H.volumen}")
    v = F.groupby("vendedor").kwh.sum().astype(float).to_dict()
    q = F.groupby("comprador").kwh.sum().astype(float).to_dict()
    exige(abs(sum(v.values()) - V) <= 1e-4 and abs(sum(q.values()) - V) <= 1e-4, "lo vendido o comprado ≠ volumen")
    for _, r in F.iterrows():
        P = v[r.vendedor] * q[r.comprador] / V
        exige(abs(P - float(r.kwh)) <= 1e-4, f"P_ji de {r.vendedor}→{r.comprador}: {P} ≠ {r.kwh}")
    ok(f"volumen = lado corto de quienes entran ({V:.4f} kWh) y emparejamiento P_ji = v_j q_i / V en los {len(F)} pares")

    # 4. precios
    pr = F.groupby("comprador").precio_reposo.first().astype(float).to_dict()
    presupuesto = sum(pr[i] for i in I)
    exige(abs(presupuesto - float(H.presupuesto)) <= 1e-2, f"presupuesto {presupuesto} ≠ {H.presupuesto}")
    ingreso = sum(pr[i] * q[i] for i in q)
    pu = ingreso / V
    exige(abs(pu - float(H.precio_uniforme)) <= 1e-3, f"precio uniforme {pu} ≠ {H.precio_uniforme}")
    pago = {i: min(pu, techos[i]) for i in q}
    for _, r in F.iterrows():
        exige(abs(pago[r.comprador] - float(r.precio)) <= 1e-3, "precio pagado ≠ almacén")
    ok(f"presupuesto = suma de los precios de reposo ({presupuesto:.2f}); precio uniforme = ingreso de reposo / volumen "
       f"({pu:.4f}); cada comprador paga mín(uniforme, tarifa)")

    # 5. reparto y banda
    prima = {j: (pu - pisos[j]) * v[j] for j in v}
    ahorro = {i: (techos[i] - pago[i]) * q[i] for i in q}
    banda = sum((techos[r.comprador] - pisos[r.vendedor]) * float(r.kwh) for _, r in F.iterrows())
    exige(abs(sum(prima.values()) + sum(ahorro.values()) - banda) <= 1e-2, "prima + ahorro ≠ banda por energía")
    exige(abs(banda - float(H.excedente_optimo)) <= 1e-2, f"banda {banda} ≠ excedente del almacén {H.excedente_optimo}")
    exige(abs(sum(prima.values()) - float(F.prima_vendedor.astype(float).sum())) <= 1e-2, "prima ≠ almacén")
    renta = sum((p_star - pisos[j]) * v[j] for j in v)
    parte = (pu - p_star) * V
    exige(abs(renta - float(H.renta_inframarginal)) <= 1e-2 and abs(parte - float(H.parte_juego)) <= 1e-2,
          "renta inframarginal o parte del juego ≠ almacén")
    ok(f"prima + ahorro = banda por energía = {banda:.2f} COP; renta inframarginal {renta:.2f} y parte del juego {parte:.2f}")

    filas = []

    def f(paso, magnitud, agente, valor, unidad):
        filas.append(dict(paso=paso, magnitud=magnitud, agente=NOMBRE.get(agente, agente), valor=float(valor), unidad=unidad))

    for j in s:
        f("1 roles", "sobrante", j, s[j], "kWh")
        f("1 roles", "piso", j, pisos[j], "COP/kWh")
    for i in d:
        f("1 roles", "faltante", i, d[i], "kWh")
        f("1 roles", "techo", i, techos[i], "COP/kWh")
    for k, (p, O_, D_, m) in enumerate(recorrido, 1):
        f("2 piso del juego", f"prueba {k}: piso", "", p, "COP/kWh")
        f("2 piso del juego", f"prueba {k}: oferta", "", O_, "kWh")
        f("2 piso del juego", f"prueba {k}: demanda", "", D_, "kWh")
        f("2 piso del juego", f"prueba {k}: transable", "", m, "kWh")
    f("2 piso del juego", "piso del juego", "", p_star, "COP/kWh")
    f("3 volumen", "oferta de quienes entran", "", O, "kWh")
    f("3 volumen", "demanda de quienes entran", "", D, "kWh")
    f("3 volumen", "volumen", "", V, "kWh")
    for j in v:
        f("3 volumen", "vende", j, v[j], "kWh")
    for i in q:
        f("3 volumen", "compra", i, q[i], "kWh")
    for _, r in F.iterrows():
        f("3 volumen", f"entrega a {NOMBRE[r.comprador]}", r.vendedor, float(r.kwh), "kWh")
    for i in q:
        f("4 precios", "precio de reposo", i, pr[i], "COP/kWh")
    f("4 precios", "presupuesto", "", presupuesto, "COP/kWh")
    f("4 precios", "precio uniforme", "", pu, "COP/kWh")
    for j in v:
        f("5 reparto", "prima del vendedor", j, prima[j], "COP")
    for i in q:
        f("5 reparto", "ahorro del comprador", i, ahorro[i], "COP")
    f("5 reparto", "ahorro del intercambio (banda por energía)", "", banda, "COP")
    f("5 reparto", "renta inframarginal", "", renta, "COP")
    f("5 reparto", "parte del juego", "", parte, "COP")
    f("5 reparto", "parte del vendedor", "", sum(prima.values()) / banda, "fracción")
    T = pd.DataFrame(filas)
    exige(bool(np.isfinite(T.valor).all()), "valores no finitos")
    SALIDA.mkdir(parents=True, exist_ok=True)
    T.to_csv(SALIDA / "hora_E0_256.csv", index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    L = [f"# Una hora de E0 resuelta paso a paso ({fecha}, hora {HORA})", "",
         "Fuente: `hora_E0_256.csv` (guion `reformateo/documento/scripts/articulo/hora_resuelta.py`). Derivado del "
         "almacén de E0 de la matriz del 19 de septiembre; cada paso recalculado coincide con lo que guardó el motor.", "",
         "| Paso | Magnitud | Agente | Valor | Unidad |", "|---|---|---|---:|---|"]
    for _, r in T.iterrows():
        L.append(f"| {r.paso} | {r.magnitud} | {r.agente} | {r.valor:,.4f} | {r.unidad} |")
    (SALIDA / "resumen.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("hora_resuelta.py: una hora de E0 resuelta paso a paso con la forma cerrada, derivada del almacén\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write(f"caso {CASO}, hora {HORA} ({fecha})\n")
        fh.write(f"artefactos leídos con huella: {len(AS.LEIDOS)}\n")
        for g, r in AS.LEIDOS:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"compuertas: {len(COMPUERTAS)}, todas OK:\n")
        for c in COMPUERTAS:
            fh.write(f"  OK  {c}\n")
        fh.write(f"filas de hora_E0_256.csv: {len(T)}\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    print(f"[hora] {len(T)} filas; salida en {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
