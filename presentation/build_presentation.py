"""
Genera MTE_Avances_2026.pptx — Revisión de avances MTE, mayo 2026.
Ejecutar: python presentation/build_presentation.py
Output:   presentation/MTE_Avances_2026.pptx
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from utils import (
    set_background, add_textbox, add_title, add_image,
    add_speaker_note, add_rect,
    BG, TEXT_PRI, TEXT_SEC, TEXT_MUTE,
    BLUE, GREEN, YELLOW, ORANGE, PURPLE, RED_BG, GREEN_BG, DARK_BOX,
    W, H
)

FIGURES = Path(__file__).parent.parent / "outputs" / "paper"


def new_blank_slide(prs):
    """Agrega slide en blanco con fondo oscuro."""
    layout = prs.slide_layouts[6]   # blank layout
    slide = prs.slides.add_slide(layout)
    set_background(slide)
    return slide


# ──────────────────────────────────────────────
# BLOQUE 1 — GANCHO (slides 1–3)
# ──────────────────────────────────────────────

def slide_01_portada(prs):
    """Portada."""
    s = new_blank_slide(prs)
    # Línea decorativa superior
    add_rect(s, Inches(0), Inches(0), W, Inches(0.08), BLUE)
    # Título principal
    add_textbox(
        s, "Mercados P2P de Energía:\n¿Qué nos dicen los datos\nreales de Pasto?",
        Inches(1), Inches(1.2), Inches(11.3), Inches(2.8),
        font_size=40, color=TEXT_PRI, bold=True, align=PP_ALIGN.CENTER
    )
    # Autor
    add_textbox(
        s, "Brayan S. López-Mendez",
        Inches(1), Inches(4.2), Inches(11.3), Inches(0.5),
        font_size=22, color=BLUE, bold=True, align=PP_ALIGN.CENTER
    )
    # Institución y asesores
    add_textbox(
        s, "Maestría en Ingeniería Electrónica · Universidad de Nariño\n"
           "Asesores: Andrés Pantoja · Germán Obando",
        Inches(1), Inches(4.8), Inches(11.3), Inches(0.8),
        font_size=16, color=TEXT_MUTE, align=PP_ALIGN.CENTER
    )
    # Evento y fecha
    add_textbox(
        s, "Revisión de avances proyecto MTE · Mayo 2026",
        Inches(1), Inches(5.8), Inches(11.3), Inches(0.5),
        font_size=14, color=TEXT_MUTE, italic=True, align=PP_ALIGN.CENTER
    )
    # Línea decorativa inferior
    add_rect(s, Inches(0), H - Inches(0.08), W, Inches(0.08), BLUE)
    add_speaker_note(s,
        "Buenos días. Hoy les voy a contar qué pasa cuando cinco instituciones "
        "de Pasto comparten su energía solar — y qué nos dice eso sobre las "
        "reglas que rigen la energía en Colombia."
    )
    return s


def slide_02_pregunta_provocadora(prs):
    """La pregunta provocadora."""
    s = new_blank_slide(prs)
    add_title(s, "¿La regulación colombiana está lista para el solar de 2030?", color=TEXT_PRI)
    # Cita UPME
    add_rect(s, Inches(1.5), Inches(1.4), Inches(10.3), Inches(1.6), DARK_BOX)
    add_textbox(
        s, '"Colombia instalará 5× más solar entre 2025 y 2030."',
        Inches(1.7), Inches(1.5), Inches(9.9), Inches(0.9),
        font_size=24, color=YELLOW, bold=True, align=PP_ALIGN.CENTER
    )
    add_textbox(
        s, "— Plan de Expansión UPME 2025–2039",
        Inches(1.7), Inches(2.3), Inches(9.9), Inches(0.5),
        font_size=14, color=TEXT_MUTE, italic=True, align=PP_ALIGN.CENTER
    )
    # Pregunta central
    add_textbox(
        s, "¿Los mecanismos de liquidación de la CREG 174 y CREG 101 072\n"
           "están diseñados para aprovechar esa energía?",
        Inches(0.8), Inches(3.3), Inches(11.7), Inches(1.2),
        font_size=22, color=TEXT_PRI, align=PP_ALIGN.CENTER
    )
    # Respuesta anticipada
    add_rect(s, Inches(2.5), Inches(4.8), Inches(8.3), Inches(0.7), GREEN_BG)
    add_textbox(
        s, "Esta presentación responde esa pregunta con datos reales de Pasto.",
        Inches(2.7), Inches(4.85), Inches(7.9), Inches(0.6),
        font_size=16, color=GREEN, bold=True, align=PP_ALIGN.CENTER
    )
    add_speaker_note(s,
        "El Plan de Expansión proyecta 5 veces más paneles solares en 2030. Eso es "
        "enorme. Pero nadie ha respondido con datos reales de acá: ¿la regulación "
        "que tenemos hoy está diseñada para aprovechar esa energía? ¿Cuánto dinero "
        "se deja sobre la mesa?"
    )
    return s


def slide_03_mte_intro(prs):
    """El proyecto MTE — 5 instituciones."""
    s = new_blank_slide(prs)
    add_title(s, "5 instituciones · 744 horas · datos reales de Pasto", color=BLUE)
    # 5 instituciones en grid
    insts = [
        ("🏫 Udenar", "Universidad de Nariño"),
        ("🏫 U. Mariana", "Universidad Mariana"),
        ("🏫 UCC", "U. Cooperativa de Colombia"),
        ("🏥 HUDN", "Hospital Universitario Dpto. Nariño"),
        ("🏫 Cesmag", "Universidad Cesmag"),
    ]
    cols = [Inches(0.5), Inches(3.2), Inches(5.9), Inches(8.6), Inches(11.3)]
    for i, (icon_name, full) in enumerate(insts):
        x = cols[i] if i < 4 else Inches(5.9)
        y = Inches(1.5) if i < 4 else Inches(3.8)
        add_rect(s, x, y, Inches(2.5), Inches(1.6), DARK_BOX)
        add_textbox(s, icon_name, x + Inches(0.1), y + Inches(0.1),
                    Inches(2.3), Inches(0.6), font_size=18, color=BLUE, bold=True)
        add_textbox(s, full, x + Inches(0.1), y + Inches(0.65),
                    Inches(2.3), Inches(0.8), font_size=11, color=TEXT_SEC)
    # Stats
    add_textbox(
        s, "⚡  9.9 kW instalados     📊  1 medición cada 2 min     📅  Agosto 2025 completo",
        Inches(0.5), Inches(6.1), Inches(12.3), Inches(0.6),
        font_size=16, color=GREEN, align=PP_ALIGN.CENTER
    )
    add_textbox(
        s, "Datos medidos en campo — no estimaciones, no promedios nacionales.",
        Inches(0.5), Inches(6.75), Inches(12.3), Inches(0.5),
        font_size=13, color=TEXT_MUTE, italic=True, align=PP_ALIGN.CENTER
    )
    add_speaker_note(s,
        "El MTE instala sensores en cada institución que registran cuánta energía se "
        "consume y cuánta producen los paneles, cada dos minutos. Un mes completo. "
        "Agosto del año pasado. Eso nos da 744 horas de datos reales — no encuestas, "
        "no estimaciones, datos medidos acá en Pasto."
    )
    return s


if __name__ == "__main__":
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    slide_01_portada(prs)
    slide_02_pregunta_provocadora(prs)
    slide_03_mte_intro(prs)
    out = Path(__file__).parent / "MTE_Avances_2026.pptx"
    prs.save(out)
    print(f"Guardado: {out}  ({len(prs.slides)} slides)")
