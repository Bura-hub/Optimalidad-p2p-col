"""Las acciones de la revisión r1 de `modelo_base/run_servidor.sh`
(`matriz_esquina`, `matriz_corte`, `revision_r1_resuelta`, y el punto fijo de la
esquina solo1 de B1), en SECO: imprimen las órdenes y no tocan el disco.

Actividad 3.3. M1 de la auditoría del 2026-11-21. Se comprueba con el listado
de `modelo_base/` y `SALIDAS_SERVIDOR/` antes y después (regla del lanzador,
2026-09-14). Segundos. Se salta si no hay bash.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
LANZADOR = RAIZ / "modelo_base" / "run_servidor.sh"
VARIABLES = ("ESQUINA", "CORTE", "ESQUINA_CORTE", "ESQUINA_SALIDAS", "CORTE_SALIDAS", "CASOS", "DESDE", "HASTA",
             "RETOMA_PASO", "RETOMA_CASO", "SIN_COMPUERTAS", "SIN_RECOGER", "PARA_EN_FALLO", "CONTENCION",
             "ESQUINA_DIR_PRUEBA", "CORTE_DIR_PRUEBA", "R1_INICIO")


def _bash():
    if sys.platform == "win32":
        for c in (os.environ.get("BASH_GIT"), r"C:\Program Files\Git\bin\bash.exe",
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
    e.update(SECO="1", MTE_ROOT=str(RAIZ / "MedicionesMTE_v3"), PROCS="4")
    e.update({k: str(v) for k, v in env.items()})
    r = subprocess.run([BASH, str(LANZADOR), *args], cwd=RAIZ, env=e, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
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


def test_la_noche_entera_son_81_corridas_sin_escribir():
    antes = _listado()
    rc, out = _corre("revision_r1_resuelta", HASTA="05:30")
    assert _listado() == antes
    assert rc == 0, out[-2000:]
    assert out.count("main_simulation.py") == 81
    assert out.count("compuerta_r1.py") == 81 and out.count("--canon") == 81


def test_el_punto_fijo_de_solo1_va_a_su_carpeta():
    antes = _listado()
    rc, out = _corre("matriz_esquina", ESQUINA="solo1", ESQUINA_CORTE="iterado", CASOS="E3 E1 N1")
    assert _listado() == antes
    assert rc == 0, out[-2000:]
    assert out.count("--esquina solo1 --corte-piso iterado") == 3
    assert "SALIDAS_SERVIDOR/matriz_esquina_solo1_iterado/E3/almacen" in out
    assert "solo1+iterado > SALIDAS_SERVIDOR/matriz_esquina_solo1_iterado/ESQUINA" in out
    assert "correria el otro estado" in out
    assert "SALIDAS_SERVIDOR/matriz_esquina_solo1/E3" not in out


def test_el_retome_salta_lo_que_esta_en_verde():
    rc, out = _corre("revision_r1_resuelta", HASTA="05:30", SIN_COMPUERTAS="1",
                     RETOMA_PASO="ESQUINA=solo1", RETOMA_CASO="E0")
    assert rc == 0, out[-2000:]
    assert out.count("main_simulation.py") == 73
    assert "salta E3 (DESDE=E0)" in out


@pytest.mark.parametrize("accion,env,texto", [
    ("matriz_esquina", {"ESQUINA": "malo"}, "ESQUINA tiene que ser"),
    ("matriz_esquina", {"ESQUINA": "solo2", "ESQUINA_CORTE": "iterado"}, "ESQUINA_CORTE solo admite"),
    ("matriz_esquina", {"ESQUINA": "solo1", "ESQUINA_SALIDAS": "SALIDAS_SERVIDOR/matriz_reposo"}, "no se pisa"),
    ("matriz_corte", {"CORTE": "mes"}, "CORTE tiene que ser"),
    ("matriz_esquina", {"ESQUINA": "solo1", "CASOS": "E9"}, "no es ninguno de los trece"),
    ("revision_r1_resuelta", {"RETOMA_PASO": "ESQUINA=nada"}, "no es ningun paso"),
])
def test_rechazos_en_voz_alta(accion, env, texto):
    antes = _listado()
    rc, out = _corre(accion, **env)
    assert _listado() == antes
    assert rc == 2 and texto in out, out[-1500:]


def test_hasta_vencido_sale_con_4():
    rc, out = _corre("matriz_esquina", ESQUINA="solo1", CASOS="E3", R1_INICIO="0000", HASTA="00:01")
    assert rc == 4 and "ya paso" in out
