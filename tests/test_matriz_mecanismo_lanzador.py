"""Pruebas de la accion `matriz_mecanismo` de `modelo_base/run_servidor.sh`
(2026-10-05, H2): la matriz de trece casos con el piso del vendedor de H1 o
de H2.

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
CASOS = ("E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU")
# Las variables que la accion lee: cada prueba parte de un entorno sin
# ninguna y pone solo las suyas.
VARIABLES_DE_LA_ACCION = ("PISO_MECANISMO", "MECANISMO_SALIDAS",
                          "MECANISMO_DIR_PRUEBA", "MATRIZ_CANON", "DESDE", "PARA_EN_FALLO",
                          "CONTENCION")


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
    e.update(SECO="1", MTE_ROOT=str(RAIZ / "MedicionesMTE_v3"), PROCS="4")
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


@pytest.mark.parametrize("piso", ["h1", "h2", "p2pcom"])
def test_seco_no_escribe_y_corre_los_trece_casos_con_su_piso(piso):
    antes = _listado()
    rc, out = _corre("matriz_mecanismo", PISO_MECANISMO=piso)
    assert _listado() == antes
    assert rc == 0, out
    for paso in range(1, 4):
        assert f"--- {paso}/3" in out
    assert "test_piso_mecanismo" in out
    assert "tests/test_piso_mecanismo_trece.py" in out
    assert out.count(f"--piso-mecanismo {piso}") == len(CASOS)
    for caso in CASOS:
        assert f"SALIDAS_SERVIDOR/matriz_{piso}/{caso}/almacen" in out
        assert f"compuertas_matriz_reposo.py SALIDAS_SERVIDOR/matriz_{piso}/{caso}/almacen" in out
    assert "--factor-generacion 7" in out and "--excluir-agente Udenar" in out
    # nunca la matriz del canon
    assert "SALIDAS_SERVIDOR/matriz_reposo/" not in out
    assert f"[SECO] {piso} > SALIDAS_SERVIDOR/matriz_{piso}/MECANISMO" in out
    assert "recogiendo la corrida: matriz_mecanismo" in out
    assert "[SECO] tar czf" in out


def test_desde_retoma_en_ese_caso():
    rc, out = _corre("matriz_mecanismo", PISO_MECANISMO="h2", DESDE="P1")
    assert rc == 0, out
    assert "salta E4 (DESDE=P1)" in out
    assert "matriz_h2/E4/almacen --factor" not in out
    assert out.count("--piso-mecanismo h2") == len(CASOS) - CASOS.index("P1")


def test_otra_carpeta_de_salidas():
    rc, out = _corre("matriz_mecanismo", PISO_MECANISMO="h2",
                     MECANISMO_SALIDAS="SALIDAS_SERVIDOR/matriz_h2_2026-10-05")
    assert rc == 0, out
    assert "SALIDAS_SERVIDOR/matriz_h2_2026-10-05/E0/almacen" in out


@pytest.mark.parametrize("env,texto", [
    ({}, "PISO_MECANISMO tiene que ser h1, h2 o p2pcom"),
    ({"PISO_MECANISMO": "c1"}, "PISO_MECANISMO tiene que ser h1, h2 o p2pcom"),
    ({"PISO_MECANISMO": "h2",
      "MECANISMO_SALIDAS": "SALIDAS_SERVIDOR/matriz_reposo"}, "no se pisa"),
    ({"PISO_MECANISMO": "h2", "MECANISMO_SALIDAS": "outputs/matriz_h2"},
     "dentro de"),
    ({"PISO_MECANISMO": "h2",
      "MECANISMO_SALIDAS": "SALIDAS_SERVIDOR/../matriz_h2"}, "dentro de"),
    ({"PISO_MECANISMO": "h2", "DESDE": "X9"}, "no es ninguno de los trece"),
])
def test_rechazos_en_voz_alta(env, texto):
    antes = _listado()
    rc, out = _corre("matriz_mecanismo", **env)
    assert _listado() == antes
    assert rc == 2 and texto in out, out
    assert "--- 1/3" not in out


def test_no_retoma_una_carpeta_corrida_con_el_otro_piso(tmp_path):
    (tmp_path / "MECANISMO").write_text("h1\n", encoding="utf-8")
    rc, out = _corre("matriz_mecanismo", PISO_MECANISMO="h2",
                     MECANISMO_DIR_PRUEBA=tmp_path.as_posix())
    assert rc == 2 and "se corrio con el piso 'h1'" in out, out
    rc, out = _corre("matriz_mecanismo", PISO_MECANISMO="h1",
                     MECANISMO_DIR_PRUEBA=tmp_path.as_posix())
    assert rc == 0, out


def test_recoger_en_seco():
    antes = _listado()
    rc, out = _corre("recoger", "matriz_mecanismo", PISO_MECANISMO="h2")
    assert _listado() == antes
    assert rc == 0, out
    assert "recogiendo la corrida: matriz_mecanismo" in out
    assert "SALIDAS_SERVIDOR/matriz_h2/SINU/almacen" in out
    assert "matriz_h2_compuerta_E0" in out
    rc, out = _corre("recoger", "matriz_mecanismo")
    assert rc == 2 and "PISO_MECANISMO" in out
