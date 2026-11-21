"""Invariancia al bit de las opciones de la revision r1 del articulo (AE-5 y
AE-4) cuando estan apagadas, y pruebas de sus piezas.

Actividades 2.2 y 3.3. Revision r1 del articulo (envio 11297), diseno en
`Documentos/articulo_latam/v2_es/revision_r1/diseno_mediciones_completas.md`
y decisiones del 2026-11-21 en `decisiones.md` («mediciones completas de AE-4
y AE-5»). Condicion fija del autor: opciones nuevas apagadas por defecto,
ningun defecto de SolverParams cambia, y una prueba de invariancia al bit.

Lo que se prueba:

1. **Frente a la base** (`R1_AE45_BASE`, por defecto `9436d0f`, el commit
   anterior al codigo nuevo; un git worktree temporal FUERA del repositorio,
   que se borra al terminar). Un dia de E0 y un dia de E3 (con corte), con la
   orden del canon (`matriz_reposo`): el almacen entero, cada hoja de los
   libros de `outputs/` (la de diagnostico sin la fecha, el commit y la
   orden), cada CSV de `outputs/` y `graficas/` y cada .mat son iguales al
   bit entre la base y el arbol. Ademas, con `--esquina p2p --corte-piso mes`
   escritos, el arbol da lo mismo que sin ellos.
2. **Las piezas**, sin datos del proyecto: `piso_esquina("p2p")` es
   `piso_residual` al bit; `GridParams` sin cargo y con `cargo_comprador=None`
   o con un cargo de ceros dan el motor al bit, y un cargo positivo cambia el
   mercado (la prueba no es vacia); la FIFO del saldo es el Anexo 4; la
   cadena por meses con la regla `fija` es `EMSP2P.run` al bit, en un proceso
   y en varios; las reglas del corte coinciden en las horas seguras; Shapley
   cierra.

Las corridas de la parte 1 escriben SOLO en carpetas temporales del sistema
(`--out-dir` y `--almacen`), nunca en `outputs/`, `graficas/` ni
`SALIDAS_SERVIDOR/`. Si faltan los datos (repositorio publico) o git, se
saltan con su razon. Unos cuatro minutos. Uso (solo este fichero):
    .venv/Scripts/python.exe -m pytest tests/test_invariancia_r1_ae45.py -q
"""
from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.shapley_factorial import desde_c4, shapley_dos
from core.corte_secuencial import (SaldoFIFO, liquida_fifo, marca_permuta,
                                   resuelve_iterado, resuelve_secuencial)
from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from core.opciones_externas import (deduccion_caso2, piso_colectivo,
                                    piso_esquina, piso_residual,
                                    reparto_anexo4)

RAIZ = Path(__file__).resolve().parents[1]
BASE_REF = os.environ.get("R1_AE45_BASE", "9436d0f")
MTE = RAIZ / "MedicionesMTE_v3"
CONTRATOS = next(iter(sorted((RAIZ / "data").glob(
    "XM_Energ*No Regulado.xlsx"))), None)
ORDEN = ["--data", "real", "--include-c5", "--no-regulado", "--metodo",
         "reposo", "--modo-presupuesto", "sigma", "--regla-precio",
         "uniforme", "--despacho-vendedores", "piso", "--analisis-ligero"]
DIAS = {"E0": ["--day", "2025-04-14"],
        "E3": ["--day", "2025-04-13", "--factor-generacion", "5.6"]}
VOLATILES_DIAG = ("generado", "git_hash", "comando", "mte_root")
# El reloj: los segundos de pared de cada hora (tabla `horas`) y la marca de
# tiempo de los metadatos de cada .mat. Lo demas se compara al bit.
VOLATILES_ALMACEN = ("segundos",)
VOLATILES_MAT = ("timestamp_bogota",)
EXCLUIDOS = ("segundos", "tr")


# ─── 1. frente a la base, con un git worktree temporal ────────────────────

def _git(*a, cwd=RAIZ):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def _hay_todo():
    if shutil.which("git") is None:
        return "sin git"
    if not MTE.is_dir():
        return "sin MedicionesMTE_v3 (datos del proyecto)"
    if CONTRATOS is None:
        return "sin la serie de contratos de XM en data/"
    if _git("rev-parse", "--verify", BASE_REF + "^{commit}").returncode != 0:
        return f"no esta el commit base {BASE_REF}"
    return None


requiere_datos = pytest.mark.skipif(_hay_todo() is not None,
                                    reason=str(_hay_todo()))


def _corre(cwd: Path, caso: str, destino: Path, extra=()):
    env = dict(os.environ, MTE_ROOT=str(MTE), PYTHONUNBUFFERED="1")
    destino.mkdir(parents=True, exist_ok=True)
    orden = [sys.executable, "-u", "main_simulation.py", *ORDEN, *DIAS[caso],
             *extra, "--almacen", str(destino / "almacen"),
             "--out-dir", str(destino)]
    with open(destino.with_suffix(".log"), "w", encoding="utf-8") as log:
        r = subprocess.run(orden, cwd=cwd, env=env, stdout=log,
                           stderr=subprocess.STDOUT, timeout=900)
    assert r.returncode == 0, f"{caso} en {cwd} salio con {r.returncode}"
    return destino


@pytest.fixture(scope="module")
def corridas():
    tmp = Path(tempfile.mkdtemp(prefix="r1_ae45_"))
    wt = tmp / "base"
    r = _git("worktree", "add", "--detach", str(wt), BASE_REF)
    assert r.returncode == 0, r.stderr
    try:
        shutil.copy2(CONTRATOS, wt / "data" / CONTRATOS.name)
        out = {}
        for caso in DIAS:
            out[caso] = dict(
                base=_corre(wt, caso, tmp / f"base_{caso}"),
                arbol=_corre(RAIZ, caso, tmp / f"arbol_{caso}"),
                explicito=_corre(RAIZ, caso, tmp / f"explicito_{caso}",
                                 ["--esquina", "p2p", "--corte-piso", "mes"]))
        yield out
    finally:
        _git("worktree", "remove", "--force", str(wt))
        _git("worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)


def _tablas_almacen(d: Path) -> dict:
    out = {}
    for t in sorted((d / "almacen" / "m1").iterdir()):
        if t.is_dir():
            partes = sorted(t.glob("parte_*.parquet"))
            df = (pd.concat([pd.read_parquet(p) for p in partes],
                            ignore_index=True) if partes else None)
            if df is not None:
                df = df.drop(columns=[c for c in VOLATILES_ALMACEN if c in df])
            out[t.name] = df
    return out


def _difs(a: Path, b: Path) -> list:
    """Lo que difiere entre dos corridas; vacio es igual al bit."""
    malas = []
    ta, tb = _tablas_almacen(a), _tablas_almacen(b)
    if sorted(ta) != sorted(tb):
        malas.append(f"tablas del almacen {sorted(ta)} / {sorted(tb)}")
    for t in ta:
        x, y = ta[t], tb.get(t)
        if (x is None) != (y is None) or (x is not None and not x.equals(y)):
            malas.append(f"almacen/{t}")
    for xa in sorted((a / "outputs").glob("*.xlsx")):
        xb = b / "outputs" / xa.name
        if not xb.exists():
            malas.append(f"falta {xa.name}")
            continue
        # Con `with`: un libro abierto en Windows impide borrar la carpeta.
        with pd.ExcelFile(xa) as la, pd.ExcelFile(xb) as lb:
            if la.sheet_names != lb.sheet_names:
                malas.append(f"{xa.name}: hojas distintas")
                continue
            for h in la.sheet_names:
                da, db = pd.read_excel(la, h), pd.read_excel(lb, h)
                if h == "Diagnostico":
                    da = da.drop(columns=[c for c in VOLATILES_DIAG if c in da])
                    db = db.drop(columns=[c for c in VOLATILES_DIAG if c in db])
                if not da.equals(db):
                    malas.append(f"{xa.name}/{h}")
    for sub in ("outputs", "graficas"):
        fa = sorted(p.name for p in (a / sub).glob("*.csv"))
        fb = sorted(p.name for p in (b / sub).glob("*.csv"))
        if fa != fb:
            malas.append(f"{sub}: CSV distintos")
        for n in fa:
            if (a / sub / n).read_bytes() != (b / sub / n).read_bytes():
                malas.append(f"{sub}/{n}")
    from scipy.io import loadmat
    for ma in sorted((a / "graficas").glob("*.mat")):
        x, y = loadmat(ma), loadmat(b / "graficas" / ma.name)
        ks = sorted(k for k in x if not k.startswith("__"))
        if ks != sorted(k for k in y if not k.startswith("__")):
            malas.append(f"graficas/{ma.name}: claves")
            continue
        for k in ks:
            if not _mat_igual(x[k], y[k]):
                malas.append(f"graficas/{ma.name}:{k}")
    return malas


def _mat_igual(x, y) -> bool:
    """Igualdad al bit de lo que devuelve `loadmat`, con estructuras y celdas
    (arrays de objetos) recorridas elemento a elemento."""
    x, y = np.asarray(x), np.asarray(y)
    if x.shape != y.shape or x.dtype.names != y.dtype.names:
        return False
    if x.dtype.names:
        return all(_mat_igual(x[n], y[n]) for n in x.dtype.names
                   if n not in VOLATILES_MAT)
    if x.dtype == object or y.dtype == object:
        return all(_mat_igual(a, b) for a, b in zip(x.ravel(), y.ravel()))
    if x.dtype.kind in "fc":
        return np.array_equal(x, y, equal_nan=True)
    return np.array_equal(x, y)


@requiere_datos
@pytest.mark.parametrize("caso", list(DIAS))
def test_frente_a_la_base_igual_al_bit(corridas, caso):
    c = corridas[caso]
    malas = _difs(c["base"], c["arbol"])
    assert not malas, f"{caso}: el arbol difiere de {BASE_REF} en {malas}"


@requiere_datos
@pytest.mark.parametrize("caso", list(DIAS))
def test_defectos_escritos_igual_al_bit(corridas, caso):
    c = corridas[caso]
    malas = _difs(c["arbol"], c["explicito"])
    assert not malas, f"{caso}: --esquina p2p --corte-piso mes difiere en {malas}"


@requiere_datos
def test_el_dia_de_E3_tiene_corte(corridas):
    """Que el caso «con corte» lo sea: alguna hora-vendedor en bolsa."""
    a = _tablas_almacen(corridas["E3"]["arbol"])["agentes"]
    vende = a[a.sobrante > 1e-9]
    assert ((vende.techo - vende.piso) > 0).all()
    assert vende.piso.nunique() > 1 and (vende.piso < 300).any(), \
        "el dia de E3 no tiene horas-vendedor desde el corte"


# ─── 2. las piezas, sin datos del proyecto ─────────────────────────────────

def _comunidad(T=96, N=5, semilla=7):
    r = np.random.default_rng(semilla)
    h = np.arange(T) % 24
    sol = np.clip(np.sin((h - 6) / 12 * np.pi), 0, None)
    G = sol[None, :] * r.uniform(5, 30, (N, 1)) * r.uniform(0.6, 1.2, (N, T))
    D = r.uniform(3, 15, (N, T))
    mes = np.repeat(np.arange(T // 48 + 1), 48)[:T]
    cu = np.repeat(r.uniform(700, 800, (N, 1)), T, axis=1)
    cv = np.repeat(r.uniform(30, 180, (N, 1)), T, axis=1)
    th = np.repeat(r.uniform(150, 300, (N, 1)), T, axis=1)
    bolsa = r.uniform(90, 250, T)
    return G, D, mes, cu, cv, th, bolsa


def _motor(G, D, cu, piso, cargo=None, sin_campo=False):
    N = G.shape[0]
    agents = AgentParams(N=N, a=np.zeros(N), b=np.full(N, 150.0),
                         c=np.zeros(N), lam=np.full(N, 100.0),
                         theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    if sin_campo:
        grid = GridParams(pi_gs=750.0, pi_gb=180.0, pi_gs_agente=cu,
                          pi_gb_agente=piso)
    else:
        grid = GridParams(pi_gs=750.0, pi_gb=180.0, pi_gs_agente=cu,
                          pi_gb_agente=piso, cargo_comprador=cargo)
    solver = SolverParams(
        tau=0.001, t_span=(0.0, 0.005), n_points=150, stackelberg_iters=2,
        parallel=False, metodo="reposo", t_span_acoplado=0.05,
        rtol_acoplado=1e-6, arranque_acoplado="factible",
        modo_presupuesto="sigma", sigma_nivel=None, regla_precio="uniforme",
        despacho_vendedores="piso", mu_cuantal=1.0,
        buyer_competition="aggregate", plazo_hora_s=None)
    return EMSP2P(agents, grid, solver)


def _iguales(r1, r2) -> list:
    malas = []
    for a, b in zip(r1, r2):
        for f in dataclasses.fields(a):
            if f.name in EXCLUIDOS:
                continue
            x, y = getattr(a, f.name), getattr(b, f.name)
            if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
                ok = (x is None and y is None) or (
                    x is not None and y is not None and
                    np.array_equal(np.asarray(x), np.asarray(y),
                                   equal_nan=True))
            else:
                try:
                    ok = bool(x == y) or (x != x and y != y)
                except ValueError:
                    ok = np.array_equal(np.asarray(x), np.asarray(y))
            if not ok:
                malas.append((a.k, f.name))
    return malas


@lru_cache(maxsize=1)
def _caso():
    G, D, mes, cu, cv, th, bolsa = _comunidad()
    piso, ep = piso_residual(G, D, cu, cv, bolsa, mes)
    return G, D, mes, cu, cv, th, bolsa, piso, ep


def test_piso_esquina_p2p_es_piso_residual_al_bit():
    G, D, mes, cu, cv, th, bolsa, piso, ep = _caso()
    p, e, cargo = piso_esquina("p2p", G, D, cu, cv, cv + th, bolsa, mes)
    assert np.array_equal(p, piso) and np.array_equal(e, ep) and cargo is None
    p1, e1, c1 = piso_esquina("solo1", G, D, cu, cv, cv + th, bolsa, mes)
    assert np.array_equal(p1, piso) and np.array_equal(c1, cv + th)
    for esq, base in (("solo2", "residual"), ("ninguno", "bruta")):
        p2, e2, c2 = piso_esquina(esq, G, D, cu, cv, cv + th, bolsa, mes)
        q, f = piso_colectivo(G, D, cu, cv + th, bolsa, mes, base=base)
        assert np.array_equal(p2, q) and np.array_equal(e2, f)
        assert (c2 is None) == (esq == "solo2")
    assert np.array_equal(deduccion_caso2(cv, th), cv + th)


def test_sin_cargo_igual_al_bit_y_cargo_cambia_el_mercado():
    G, D, mes, cu, cv, th, bolsa, piso, ep = _caso()
    r0, gk0, ds0 = _motor(G, D, cu, piso, sin_campo=True).run(D, G)
    r1, gk1, ds1 = _motor(G, D, cu, piso, cargo=None).run(D, G)
    r2, gk2, ds2 = _motor(G, D, cu, piso, cargo=np.zeros_like(cu)).run(D, G)
    assert not _iguales(r0, r1) and not _iguales(r0, r2)
    for g in (gk1, gk2):
        assert np.array_equal(g, gk0)
    r3, gk3, _ = _motor(G, D, cu, piso, cargo=cv + th).run(D, G)
    assert np.array_equal(gk3, gk0), "el cargo no puede tocar el limite de generacion"
    assert _iguales(r0, r3), "un cargo positivo no cambio nada: prueba vacia"
    v0 = sum(float(np.sum(r.P_star)) for r in r0 if r.P_star is not None)
    v3 = sum(float(np.sum(r.P_star)) for r in r3 if r.P_star is not None)
    assert v3 < v0
    # single_hour honra el mismo cargo
    e3 = _motor(G, D, cu, piso, cargo=cv + th)
    for r in r3[::7]:
        assert not _iguales([r], [e3.run_single_hour(r.k, D, G)])


def test_cargo_invalido_falla_en_voz_alta():
    G, D, mes, cu, cv, th, bolsa, piso, ep = _caso()
    for malo in (np.zeros((2, 3)), -np.ones_like(cu), cu * 2.0,
                 np.full_like(cu, np.nan)):
        with pytest.raises(ValueError):
            _motor(G, D, cu, piso, cargo=malo).run(D, G)


def test_fifo_es_el_anexo4():
    r = np.random.default_rng(3)
    for _ in range(40):
        N, T = 4, 120
        sr = np.where(r.random((N, T)) < 0.4, r.uniform(0, 5, (N, T)), 0.0)
        dr = np.where((sr == 0) & (r.random((N, T)) < 0.6),
                      r.uniform(0, 5, (N, T)), 0.0)
        mes = np.repeat([0, 1, 2], 40)
        cr, ex = liquida_fifo(sr, dr, mes)
        cr4, ex4, _ = reparto_anexo4(sr, dr, mes)
        assert np.abs(ex - ex4).max() <= 1e-9
        assert np.abs(cr - cr4).max() <= 1e-9
        assert np.array_equal(ex > 1e-9, ex4 > 1e-9)


def test_saldo_fifo_estado():
    s = SaldoFIFO(1)
    s.actualiza(0, np.array([0.0]), np.array([3.0]))
    s.actualiza(1, np.array([5.0]), np.array([0.0]))
    assert s.pendiente[0] == 0.0 and s.exceso_provisional()[0] == 2.0
    s.actualiza(2, np.array([4.0]), np.array([0.0]))
    s.actualiza(3, np.array([0.0]), np.array([3.0]))   # cubre primero la hora 1
    assert [list(x) for x in s.cola[0]] == [[2, 3.0]]
    assert np.array_equal(s.cierra(4)[0], [0, 0, 3.0, 0])


@pytest.mark.parametrize("procesos", [1, 2])
def test_cadena_fija_es_el_motor(procesos):
    G, D, mes, cu, cv, th, bolsa, piso, ep = _caso()
    e = _motor(G, D, cu, piso)
    r0, _, _ = e.run(D, G)
    r1, p1, m1, seg = resuelve_secuencial(e, D, G, cu, cv, bolsa, mes,
                                          regla="fija", procesos=procesos)
    assert not _iguales(r0, r1)
    assert np.array_equal(p1, piso)


def test_reglas_coinciden_en_las_horas_seguras():
    G, D, mes, cu, cv, th, bolsa, piso, ep = _caso()
    e = _motor(G, D, cu, piso)
    rp, pp, mp, _ = resuelve_secuencial(e, D, G, cu, cv, bolsa, mes,
                                        regla="secuencial_pronostico",
                                        procesos=1)
    rs, ps, ms, _ = resuelve_secuencial(e, D, G, cu, cv, bolsa, mes,
                                        regla="secuencial_saldo", procesos=1)
    # el saldo conocido nunca da permuta donde el pronostico da bolsa
    assert not np.any(ms & ~mp)
    for res, pis, mar in ((rp, pp, mp), (rs, ps, ms)):
        vende = np.maximum(G - D, 0.0) > 1e-9
        assert np.array_equal(pis[vende], np.where(mar, cu - cv,
                                                   bolsa[None, :])[vende])
        assert all(r.k == k for k, r in enumerate(res))


def test_marca_permuta():
    s = SaldoFIFO(2)
    s.actualiza(0, np.zeros(2), np.array([4.0, 1.0]))
    m = marca_permuta("secuencial_saldo", s, np.array([3.0, 3.0]),
                      np.zeros(2), 2, 10)
    assert m.tolist() == [True, False]
    m = marca_permuta("secuencial_pronostico", s, np.array([3.0, 3.0]),
                      np.zeros(2), 2, 10)     # R_hat = 5 * R
    assert m.tolist() == [True, True]


def test_iterado_corre_y_registra():
    G, D, mes, cu, cv, th, bolsa, piso, ep = _caso()
    e = _motor(G, D, cu, piso)
    res, gk, ds, p, hist = resuelve_iterado(e, D, G, cu, cv, bolsa, mes, ep)
    assert hist and len(res) == G.shape[1]
    assert hist[-1]["convergio"] or hist[-1]["ciclo"] or len(hist) == 8
    assert np.array_equal(e.grid.pi_gb_agente, piso), "no puede tocar la rejilla"


def test_shapley_cierra():
    sh = shapley_dos(1.0, 3.0, 4.0, 7.0)
    assert sh["shapley_s1"] + sh["shapley_s2"] == sh["total"] == 6.0
    assert sh["interaccion"] == (7.0 - 4.0) - (3.0 - 1.0)
    c4 = desde_c4(sh, 1.0, 1.5)
    assert c4["shapley_s1"] + c4["shapley_s2"] == 7.0 - 1.5
