"""
Configuración global de pytest.

Forza UTF-8 en stdout para Windows: el modo `--capture=no` (fijado en
pytest.ini para evitar el bug de captura de pytest 9.0.2 + Python 3.13.7)
expone los caracteres Unicode (█, ░) de la barra de progreso de
`core/ems_p2p.py`; sin esto, el codec cp1252 trunca con UnicodeEncodeError.

CAL-39 (2026-06-10): se usa ``reconfigure()`` EN SITIO en lugar de
reemplazar ``sys.stdout`` con un TextIOWrapper nuevo. El reemplazo dejaba
huérfano al wrapper original; el recolector de basura cerraba el buffer
compartido y el terminal de pytest (que conserva la referencia original)
moría con "I/O operation on closed file" en un punto aleatorio de la
suite — por eso la suite completa nunca había podido correr de una sola
pasada en Windows.
"""
import sys

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
