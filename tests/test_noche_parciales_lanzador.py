"""Pruebas de las acciones del 2026-10-07 de `modelo_base/run_servidor.sh`:
`equidad_caja` (EQ), `dinamica_extrema` (DX), `caso_autora` (CA) y
`cierre_parciales`, que encadena las tres.

Actividades 1.1, 3.3 y 4.1. Todo en SECO: el lanzador imprime las ordenes y no
toca el disco, y la prueba lo comprueba con el listado de `modelo_base/` y
`SALIDAS_SERVIDOR/` antes y despues (regla del lanzador, 2026-09-14). Segundos.
Se salta si no hay bash (en Windows se busca el de Git, nunca el de WSL).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
LANZADOR = RAIZ / "modelo_base" / "run_servidor.sh"
VARIABLES = ("EQUIDAD_SALIDAS", "EXTREMA_SALIDAS", "AUTORA_SALIDAS",
             "GSA_REFERENCIA", "SIN_REFERENCIA_GSA", "EQUIDAD_NBASE", "CASOS",
             "REANUDAR", "TOPE_EQUIDAD_S", "EXTREMA_HORAS", "EXTREMA_TOPE_S",
             "EXTREMA_FUTILIDAD", "EXTREMA_REGIMENES", "EXTREMA_FAMILIAS",
             "EXTREMA_POR_CASO", "EXTREMA_PREVIOS", "AUTORA_PROCESOS",
             "AUTORA_TOPE_S", "RETOMA", "REHACE_MUESTRA", "TOPE_GLOBAL_S",
             "MATRIZ_CANON", "CONTENCION", "PARA_EN_FALLO",
             "MEMORIA_POR_PROCESO_GB", "DIA_OK", "AMPLIADA_SALIDAS")


def _bash():
    if sys.platform == "win32":
        for c in (os.environ.get("BASH_GIT"),
                  r"C:\Program Files\Git\bin\bash.exe",
                  r"C:\Program Files\Git\usr\bin\bash.exe"):
            if c and Path(c).exists():
                return c
        return None
    return shutil.which("bash")


BASH = _bash()
pytestmark = pytest.mark.skipif(BASH is None, reason="sin bash")


def _corre(*args, **env):
    e = dict(os.environ)
    for v in VARIABLES:
        e.pop(v, None)
    e.update(SECO="1", MTE_ROOT=str(RAIZ / "MedicionesMTE_v3"), PROCS="4",
             MATRIZ_CANON="SALIDAS_SERVIDOR/x")
    e.update({k: str(v) for k, v in env.items()})
    r = subprocess.run([BASH, str(LANZADOR), *args], cwd=RAIZ, env=e,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    return r.returncode, r.stdout + r.stderr


def _listado():
    out = []
    for base in ("modelo_base", "SALIDAS_SERVIDOR"):
        for p in sorted((RAIZ / base).rglob("*")):
            try:
                st = p.stat()
            except OSError:
                continue
            out.append((str(p), st.st_size, st.st_mtime_ns))
    return out


def test_sintaxis():
    r = subprocess.run([BASH, "-n", str(LANZADOR)], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stderr


def test_seco_cierre_parciales_no_escribe_y_reparte_los_procesos():
    antes = _listado()
    rc, out = _corre("cierre_parciales", AUTORA_PROCESOS="1",
                     EQUIDAD_SALIDAS="SALIDAS_SERVIDOR/eq_prueba",
                     EXTREMA_SALIDAS="SALIDAS_SERVIDOR/dx_prueba",
                     AUTORA_SALIDAS="SALIDAS_SERVIDOR/ca_prueba")
    assert _listado() == antes
    assert rc == 0, out
    # EQ: la compuerta del punto base y la caja con sus dos referencias.
    assert ("gsa_directo/compuerta_punto_base.py --matriz SALIDAS_SERVIDOR/x "
            "--salida SALIDAS_SERVIDOR/eq_prueba/base/punto_base.csv") in out
    assert "gsa_directo/equidad_caja.py --matriz SALIDAS_SERVIDOR/x" in out
    assert ("--referencia-base SALIDAS_SERVIDOR/eq_prueba/base/punto_base.csv"
            in out)
    assert "--referencia-gsa SALIDAS_SERVIDOR/gsa_directo_h1_2026-10-04" in out
    assert ("--casos E0 E2 E4 E1 E3 E5 P1 P2 K1 I1 N1 SINU --n-base 512 "
            "--procesos 4") in out
    assert "--casos E0 E2 E4 E1 E3 E5 P1 P2 K1 I1 N1 CV2" not in out
    # CA con AUTORA_PROCESOS y DX con el resto: nunca mas de PROCS.
    assert "--medicion medicion_autora" in out
    assert "--procesos 1 --tope-total" in out
    assert "--medicion medicion_extrema" in out
    assert "--procesos 3 --tope-total" in out
    assert "selecciona_extrema.py --familias bolsa4 tarifa_baja tarifa2" in out
    assert "lado_derecho_extremo.py --horas SALIDAS_SERVIDOR/dx_prueba" in out
    assert "veredicto.py SALIDAS_SERVIDOR/ca_prueba/m_g2.json" in out
    assert "lectura_extrema.py SALIDAS_SERVIDOR/dx_prueba/m_a2x.json" in out
    # Un solo esperador por corrida, y cada recogida sin la cache.
    assert out.count("timeout --kill-after=300") == 3
    assert "--exclude=SALIDAS_SERVIDOR/eq_prueba/cache" in out
    assert "--exclude=SALIDAS_SERVIDOR/dx_prueba/cache" in out
    assert "EQ=0 CA=0 DX=0" in out


def test_seco_dinamica_extrema_retoma():
    antes = _listado()
    rc, out = _corre("dinamica_extrema", RETOMA="57",
                     EXTREMA_SALIDAS="SALIDAS_SERVIDOR/dx_prueba")
    assert _listado() == antes
    assert rc == 0, out
    assert "--desde 57" in out and "m_a2x_desde57.json" in out


def test_seco_recoger_cierre_parciales():
    antes = _listado()
    rc, out = _corre("recoger", "cierre_parciales",
                     EQUIDAD_SALIDAS="SALIDAS_SERVIDOR/eq_prueba",
                     EXTREMA_SALIDAS="SALIDAS_SERVIDOR/dx_prueba",
                     AUTORA_SALIDAS="SALIDAS_SERVIDOR/ca_prueba")
    assert _listado() == antes
    assert rc == 0, out
    tar = [l for l in out.splitlines() if "[SECO] tar czf" in l]
    assert len(tar) == 1
    for d in ("eq_prueba", "dx_prueba", "ca_prueba"):
        assert f"SALIDAS_SERVIDOR/{d}" in tar[0]
    assert "--exclude=SALIDAS_SERVIDOR/eq_prueba/cache" in tar[0]
    assert " SALIDAS_SERVIDOR " not in tar[0] + " "


@pytest.mark.parametrize("accion,env,texto", [
    ("equidad_caja", {"EQUIDAD_NBASE": "300"}, "potencia de dos"),
    ("equidad_caja", {"CASOS": "E0 CV2"}, "doce casos del Sobol"),
    ("equidad_caja", {"EQUIDAD_SALIDAS": "/tmp/fuera"}, "dentro de"),
    ("dinamica_extrema", {"EXTREMA_FAMILIAS": "bolsa9"}, "no vale"),
    ("dinamica_extrema", {"EXTREMA_REGIMENES": "mixto"}, "no es un regimen"),
    ("dinamica_extrema", {"EXTREMA_HORAS": "4"}, "EXTREMA_HORAS"),
    ("dinamica_extrema", {"RETOMA": "x"}, "no es un indice"),
    ("caso_autora", {"AUTORA_PROCESOS": "0"}, "entero positivo"),
    ("cierre_parciales", {"AUTORA_PROCESOS": "4"}, "PROCS - 1"),
])
def test_rechazos_en_voz_alta(accion, env, texto):
    rc, out = _corre(accion, **env)
    assert rc == 2 and texto in out, out
