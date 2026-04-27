"""
Configuración global de pytest.

Forza UTF-8 en stdout para Windows: el modo `--capture=no` (fijado en
pytest.ini para evitar el bug de captura de pytest 9.0.2 + Python 3.13.7)
expone los caracteres Unicode (█, ░) que la barra de progreso de
`core/ems_p2p.py` escribe a stdout. Sin este guard, el codec cp1252
predeterminado en Windows trunca con UnicodeEncodeError.

Mismo patrón aplicado en main_simulation.py:28-30.
"""
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
