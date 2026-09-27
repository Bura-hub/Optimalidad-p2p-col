"""Pruebas de la accion `gsa_directo` de `modelo_base/run_servidor.sh` (T7).

Actividad 4.1. Todo en SECO: el lanzador imprime las ordenes y no toca el
disco, y la prueba lo comprueba con el listado de `modelo_base/` y
`SALIDAS_SERVIDOR/` antes y despues (regla del lanzador, 2026-09-14).
Segundos. Se salta si no hay bash (en Windows se busca el de Git, nunca el
de WSL).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
LANZADOR = RAIZ / "modelo_base" / "run_servidor.sh"
MATRIZ = ("SALIDAS_SERVIDOR/entrega_matriz_reposo_2026-09-19/"
          "SALIDAS_SERVIDOR/matriz_reposo")
SIN_CORRIDAS = "modelo_base/_seco_sin_corridas/gsa_directo"
# Las variables que la accion lee (ronda 2, R-2). En el servidor, el paso 2
# corre ESTAS pruebas dentro de la accion y pytest hereda lo que el operador
# puso delante de `bash` (SOLO_HUMO=1 CASOS="E0 E2" el 3 de octubre): cada
# prueba parte de un entorno sin ninguna y pone solo las suyas.
VARIABLES_DE_LA_ACCION = (
    "SOLO_HUMO", "NBASE", "NBASE_RESTO", "TOPE_NOCHE_H", "FORZAR",
    "DETERMINISTAS", "OMITIR_SIN_REFERENCIA", "RESERVA_OK", "PARA_EN_FALLO",
    "TOLERA_FALLOS", "CASOS", "DESDE", "MATRIZ_CANON", "EXTRA", "PASOS",
    "LENTAS", "ETAPA2", "SIGMAS", "ALMACENES", "GRUPOS", "OPTS",
    "PALANCAS_ARGS", "TOPE_GLOBAL_S", "TOPE_MEDICION", "TOPE_M_C",
    "TOPE_M_E", "TOPE_M_G", "SONDA_DIR", "SIN_LINGER_OK", "GSA_DIR_PRUEBA")


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
    for v in VARIABLES_DE_LA_ACCION:
        e.pop(v, None)
    # C-205: una carpeta de salidas que no existe, para que el resultado no
    # dependa de los casos que ya corrieron en la maquina (en el servidor, E0
    # a 2 048 hacia fallar la prueba de NBASE). Solo vale en seco.
    e.update(SECO="1", MTE_ROOT=str(RAIZ / "MedicionesMTE_v3"), PROCS="4",
             MATRIZ_CANON=MATRIZ, GSA_DIR_PRUEBA=SIN_CORRIDAS)
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


def test_seco_no_escribe_y_da_las_ordenes_del_diseno():
    antes = _listado()
    rc, out = _corre("gsa_directo")
    assert _listado() == antes
    assert rc == 0, out
    for paso in range(1, 8):
        assert f"--- {paso}/7" in out
    assert f"gsa_directo/compuerta_punto_base.py --matriz {MATRIZ}" in out
    assert "gsa_directo/correr.py --caso E0 --humo 32" in out
    assert "-k not\\ lenta" in out or "-k 'not lenta'" in out
    for caso, n in (("E0", 2048), ("E2", 2048), ("E4", 2048), ("K1", 512),
                    ("SINU", 512)):
        assert (f"gsa_directo/correr.py --caso {caso} --n-base {n} "
                f"--procesos 4 --reanudar") in out
        assert f"gsa_directo/analizar.py --caso {caso} --n-base {n}" in out
    # Un solo esperador por caso: el `timeout` de GNU (coreutils).
    assert "timeout --kill-after=300" in out
    # I-1: CV2 no corre el Sobol (sigue en la compuerta).
    assert "--caso CV2" not in out
    assert "gsa_directo/replica.py" in out
    assert "gsa_directo/deterministas.py" in out
    assert "[SECO] tar czf" in out


def test_casos_y_desde():
    rc, out = _corre("gsa_directo", CASOS="E4 E1 E3", DESDE="E1")
    assert rc == 0, out
    assert "salta E4 (DESDE=E1)" in out
    assert "--caso E4 --n-base" not in out
    assert "--caso E1 --n-base 512" in out and "--caso E3 --n-base 512" in out


@pytest.mark.parametrize("env,texto", [
    ({"CASOS": "E0 X9"}, "no es ninguno de los trece"),
    ({"CASOS": "E0 E2", "DESDE": "E4"}, "no es ninguno de los casos pedidos"),
    ({"NBASE": "3000"}, "potencias de dos"),
    ({"CASOS": "E0 CV2"}, "no corre el Sobol"),
])
def test_rechazos_en_voz_alta(env, texto):
    rc, out = _corre("gsa_directo", **env)
    assert rc == 2 and texto in out


def test_nbase_llega_a_los_casos_de_diseno():
    rc, out = _corre("gsa_directo", CASOS="E0 K1", NBASE="4096",
                     NBASE_RESTO="256")
    assert rc == 0, out
    assert "--caso E0 --n-base 4096" in out
    assert "--caso K1 --n-base 256" in out


def test_solo_humo_no_lanza_el_sobol():
    rc, out = _corre("gsa_directo", SOLO_HUMO="1")
    assert rc == 0, out
    assert "gsa_directo/correr.py --caso E0 --humo 32" in out
    assert "--reanudar" not in out and "--- 5/7" not in out


def test_recoger_en_seco():
    antes = _listado()
    rc, out = _corre("recoger", "gsa_directo", CASOS="E0")
    assert _listado() == antes
    assert rc == 0, out
    assert "recogiendo la corrida: gsa_directo" in out
    assert "gsa_directo/base/punto_base.csv" in out


def test_matriz_canon_explicita():
    """M-8: sin MATRIZ_CANON la accion no arranca; en seco lo dice y sigue
    con un marcador, para ver las ordenes."""
    rc, out = _corre("gsa_directo", MATRIZ_CANON="")
    assert rc == 0, out
    assert "MATRIZ_CANON no esta definido" in out
    assert "[SECO] se sigue con '<MATRIZ_CANON>'" in out
    assert "gsa_directo/compuerta_punto_base.py --matriz" in out



def _orden_del_3_de_octubre():
    """La orden de dia del 3 de octubre, tal cual la escribe MONTAJE."""
    import shlex
    texto = (RAIZ / "modelo_base" / "MONTAJE_SERVIDOR.md").read_text(
        encoding="utf-8")
    lineas = [ln.strip() for ln in texto.splitlines()
              if ln.strip().startswith("SOLO_HUMO=1")
              and "gsa_directo" in ln]
    assert len(lineas) == 1, lineas
    partes = shlex.split(lineas[0])
    env = dict(p.split("=", 1) for p in partes if "=" in p
               and not p.startswith(("bash", "modelo_base")))
    assert partes[-2:] == ["modelo_base/run_servidor.sh", "gsa_directo"]
    return env


def test_la_orden_del_3_de_octubre_en_seco():
    """R-2: la orden exacta de MONTAJE para el 3 de octubre, en seco, hace
    los pasos 1 a 4 y no lanza el Sobol, sin escribir nada."""
    env = _orden_del_3_de_octubre()
    assert env == {"SOLO_HUMO": "1", "CASOS": "E0 E2"}
    antes = _listado()
    rc, out = _corre("gsa_directo", **env)
    assert _listado() == antes
    assert rc == 0, out
    for paso in (1, 2, 3, 4):
        assert f"--- {paso}/7" in out
    assert "--- 5/7" not in out and "SOLO_HUMO=1" in out


@pytest.mark.skipif(os.environ.get("GSA_PRUEBA_ANIDADA") == "1",
                    reason="ya dentro de la prueba de herencia")
def test_el_paso_2_no_hereda_las_variables_de_la_accion():
    """R-2: el paso 2 de la accion corre estas pruebas con lo que el operador
    puso delante de bash. Con las variables de la orden del 3 de octubre y
    las demas de la accion en el entorno, las pruebas del lanzador pasan."""
    env = dict(os.environ, GSA_PRUEBA_ANIDADA="1", SOLO_HUMO="1",
               CASOS="E0 E2", NBASE="4096", NBASE_RESTO="256",
               TOPE_NOCHE_H="1", FORZAR="1", DETERMINISTAS="0",
               OMITIR_SIN_REFERENCIA="1", TOLERA_FALLOS="1", DESDE="E2",
               RESERVA_OK="1", PARA_EN_FALLO="1",
               MATRIZ_CANON="no/es/la/matriz")
    r = subprocess.run([sys.executable, "-m", "pytest", str(Path(__file__)),
                        "-q", "-p", "no:cacheprovider"],
                       cwd=RAIZ, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]


def test_no_depende_de_las_corridas_de_la_maquina():
    """C-205: con un E0 ya empezado a otro n en la carpeta de salidas, el
    lanzador retoma con ese n (lo correcto); las pruebas no deben verlo."""
    assert not (RAIZ / SIN_CORRIDAS).exists()
    rc, out = _corre("gsa_directo", CASOS="E0")
    assert rc == 0, out
    assert f"salidas    = {SIN_CORRIDAS}" in out
    assert "ya empezo con n" not in out


def test_tolera_fallos_llega_a_correr():
    """R-1: TOLERA_FALLOS=1 en la accion pasa --tolera-fallos a correr.py."""
    rc, out = _corre("gsa_directo", CASOS="E0", TOLERA_FALLOS="1")
    assert rc == 0, out
    assert "--caso E0 --n-base 2048 --procesos 4 --reanudar" in out
    assert "--tolera-fallos" in out
    rc, out = _corre("gsa_directo", CASOS="E0")
    assert "--tolera-fallos" not in out
