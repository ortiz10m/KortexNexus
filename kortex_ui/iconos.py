"""Iconos vectoriales minimalistas renderizados con Pillow (alineación exacta, sin emojis)."""

from __future__ import annotations

import customtkinter as ctk
from PIL import Image, ImageDraw

# Fallback textual sobrio para compatibilidad
TABS = {
    "home": "",
    "cerebro": "",
    "monitor": "",
    "modos": "",
    "archivos": "",
    "prediccion": "",
    "notas": "",
    "launcher": "",
    "ajustes": "",
    "legal": "",
}


def _hex_a_rgba(color_hex: str) -> tuple[int, int, int, int]:
    c = color_hex.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)


def crear_icono_sidebar(clave: str, color_hex: str, size: int = 18) -> ctk.CTkImage:
    """Genera un icono monocromo nítido de trazo fino con supersampling 4x."""
    S = 72
    W = 6
    col = _hex_a_rgba(color_hex)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if clave == "home":
        d.line([(12, 34), (36, 12), (60, 34)], fill=col, width=W, joint="curve")
        d.line([(18, 30), (18, 58), (54, 58), (54, 30)], fill=col, width=W, joint="curve")
    elif clave == "cerebro":
        # Terminal / asistente
        d.rounded_rectangle([10, 14, 62, 58], radius=10, outline=col, width=W)
        d.line([(22, 30), (32, 38), (22, 46)], fill=col, width=W)
        d.line([(38, 46), (50, 46)], fill=col, width=W)
    elif clave == "monitor":
        # Pulso / actividad
        d.line([(8, 38), (20, 38), (28, 16), (40, 56), (48, 38), (64, 38)], fill=col, width=W, joint="curve")
    elif clave == "modos":
        # Sliders de control
        for y, cx in ((20, 26), (36, 46), (52, 30)):
            d.line([(10, y), (62, y)], fill=col, width=5)
            d.ellipse([cx - 7, y - 7, cx + 7, y + 7], fill=col)
    elif clave == "archivos":
        # Carpeta
        d.line([(10, 20), (28, 20), (34, 26), (62, 26), (62, 56), (10, 56), (10, 20)], fill=col, width=W, joint="curve")
    elif clave == "prediccion":
        # Gráfica tendencia
        d.line([(12, 14), (12, 58), (60, 58)], fill=col, width=W)
        d.line([(20, 48), (34, 34), (44, 40), (58, 20)], fill=col, width=W, joint="curve")
    elif clave == "notas":
        # Documento
        d.rounded_rectangle([16, 10, 56, 62], radius=6, outline=col, width=W)
        d.line([(25, 26), (47, 26)], fill=col, width=5)
        d.line([(25, 38), (47, 38)], fill=col, width=5)
        d.line([(25, 50), (39, 50)], fill=col, width=5)
    elif clave == "launcher":
        # Cuadrícula de apps
        for x0, y0 in ((14, 14), (40, 14), (14, 40), (40, 40)):
            d.rounded_rectangle([x0, y0, x0 + 18, y0 + 18], radius=4, outline=col, width=5)
    elif clave == "ajustes":
        # Engranaje minimalista (anillo + 4 muescas)
        d.ellipse([20, 20, 52, 52], outline=col, width=W)
        d.ellipse([31, 31, 41, 41], fill=col)
        for p1, p2 in (((36, 8), (36, 18)), ((36, 54), (36, 64)), ((8, 36), (18, 36)), ((54, 36), (64, 36))):
            d.line([p1, p2], fill=col, width=6)
    elif clave == "legal":
        # Escudo
        d.polygon([(36, 10), (58, 18), (56, 40), (36, 62), (16, 40), (14, 18)], outline=col, width=W)
    else:
        d.ellipse([26, 26, 46, 46], fill=col)

    final = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=final, dark_image=final, size=(size, size))
