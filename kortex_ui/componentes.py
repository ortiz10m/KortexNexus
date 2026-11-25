"""Componentes reutilizables de Kortex Nexus.

Widgets custom que se usan en todas las pestañas
para mantener consistencia visual.
"""

import customtkinter as ctk

from kortex_ui import tema


class Card(ctk.CTkFrame):
    """Contenedor con fondo elevado, borde sutil y esquinas redondeadas."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_ELEVADO)
        kwargs.setdefault("corner_radius", tema.RADIO_LG)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", tema.COLOR_BORDE)
        super().__init__(master, **kwargs)


class BotonPrimario(ctk.CTkButton):
    """Botón principal: fondo naranja, texto blanco, esquinas redondeadas."""

    def __init__(self, master, texto: str, comando=None, **kwargs):
        super().__init__(
            master,
            text=texto,
            command=comando,
            fg_color=tema.COLOR_PRIMARIO,
            hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO, "bold"),
            corner_radius=tema.RADIO_MD,
            height=40,
            **kwargs,
        )


class BotonSecundario(ctk.CTkButton):
    """Botón secundario: fondo transparente, borde sutil."""

    def __init__(self, master, texto: str, comando=None, **kwargs):
        super().__init__(
            master,
            text=texto,
            command=comando,
            fg_color="transparent",
            hover_color=tema.COLOR_ELEVADO_HOVER,
            text_color=tema.COLOR_TEXTO,
            border_width=1,
            border_color=tema.COLOR_BORDE_FUERTE,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            corner_radius=tema.RADIO_MD,
            height=40,
            **kwargs,
        )


class BotonPeligro(ctk.CTkButton):
    """Botón de acción destructiva."""

    def __init__(self, master, texto: str, comando=None, **kwargs):
        super().__init__(
            master,
            text=texto,
            command=comando,
            fg_color=tema.COLOR_ERROR,
            hover_color="#DC2626",
            text_color=tema.COLOR_TEXTO,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO, "bold"),
            corner_radius=tema.RADIO_MD,
            height=40,
            **kwargs,
        )


class Titulo(ctk.CTkLabel):
    """Título de sección (H2)."""

    def __init__(self, master, texto: str, **kwargs):
        super().__init__(
            master,
            text=texto,
            font=(tema.FUENTE_TITULO, tema.TAMANO_H2),
            text_color=tema.COLOR_TEXTO,
            anchor="w",
            **kwargs,
        )


class Subtitulo(ctk.CTkLabel):
    """Subtítulo o texto secundario."""

    def __init__(self, master, texto: str, **kwargs):
        super().__init__(
            master,
            text=texto,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO,
            anchor="w",
            **kwargs,
        )


class TextoMicro(ctk.CTkLabel):
    """Texto pequeño para metadatos."""

    def __init__(self, master, texto: str, **kwargs):
        super().__init__(
            master,
            text=texto,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO,
            anchor="w",
            **kwargs,
        )


class IndicadorProgreso(ctk.CTkProgressBar):
    """Barra de progreso con el color primario."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("progress_color", tema.COLOR_PRIMARIO)
        kwargs.setdefault("fg_color", tema.COLOR_BORDE)
        kwargs.setdefault("corner_radius", tema.RADIO_SM)
        kwargs.setdefault("height", 8)
        super().__init__(master, **kwargs)
        self.set(0)


class Separador(ctk.CTkFrame):
    """Línea divisoria horizontal."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_BORDE)
        kwargs.setdefault("height", 1)
        super().__init__(master, **kwargs)