"""Sidebar lateral de Kortex Nexus con logo oficial e iconos vectoriales alineados."""

from __future__ import annotations

import customtkinter as ctk

from kortex_core.config import obtener_dir_recursos
from kortex_ui import iconos, tema


class Sidebar(ctk.CTkFrame):
    """Barra lateral de navegación con iconos monocromos de ancho uniforme."""

    def __init__(self, master, al_cambiar_pestana, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_SUPERFICIE)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("width", tema.SIDEBAR_ANCHO)
        super().__init__(master, **kwargs)

        self.pack_propagate(False)
        self.al_cambiar_pestana = al_cambiar_pestana
        self.pestana_activa = "home"
        self._botones: dict[str, ctk.CTkButton] = {}
        self._iconos_inactivos: dict[str, ctk.CTkImage] = {}
        self._iconos_activos: dict[str, ctk.CTkImage] = {}
        self._logo_img = None

        self._construir_logo()
        self._construir_separador()
        self._construir_menu()
        self._construir_footer()

    def _construir_logo(self):
        logo = ctk.CTkFrame(self, fg_color="transparent", height=tema.HEADER_ALTO)
        logo.pack(fill="x", padx=tema.SIDEBAR_PADDING, pady=(tema.ESP_XL, tema.ESP_MD))
        logo.pack_propagate(False)

        ruta_logo = obtener_dir_recursos() / "logo_kortex.png"
        if ruta_logo.exists():
            try:
                from PIL import Image

                img = Image.open(ruta_logo)
                self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(40, 40))
                ctk.CTkLabel(logo, text="", image=self._logo_img, width=42).pack(
                    side="left", padx=(0, tema.ESP_MD)
                )
            except Exception:
                pass

        info = ctk.CTkFrame(logo, fg_color="transparent")
        info.pack(side="left", fill="y", pady=12)

        ctk.CTkLabel(
            info,
            text="Kortex Nexus",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H3),
            text_color=tema.COLOR_TEXTO,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            info,
            text="v2.0",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO,
            anchor="w",
        ).pack(anchor="w", pady=(1, 0))

    def _construir_separador(self):
        sep = ctk.CTkFrame(self, fg_color=tema.COLOR_BORDE, height=1)
        sep.pack(fill="x", padx=tema.SIDEBAR_PADDING, pady=(0, tema.ESP_MD))

    def _construir_menu(self):
        menu = ctk.CTkFrame(self, fg_color="transparent")
        menu.pack(fill="both", expand=True, padx=tema.ESP_MD, pady=0)

        items = [
            ("home", "Inicio"),
            ("cerebro", "Cerebro"),
            ("monitor", "Monitor"),
            ("modos", "Modos"),
            ("archivos", "Archivos"),
            ("prediccion", "Predicción"),
            ("notas", "Notas"),
            ("launcher", "Launcher"),
        ]

        for clave, etiqueta in items:
            boton = self._crear_boton(menu, clave, etiqueta)
            boton.pack(fill="x", pady=2)
            self._botones[clave] = boton

        self._resaltar_activo()

    def _construir_footer(self):
        sep = ctk.CTkFrame(self, fg_color=tema.COLOR_BORDE, height=1)
        sep.pack(fill="x", padx=tema.SIDEBAR_PADDING, pady=(tema.ESP_MD, tema.ESP_MD))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=tema.ESP_MD, pady=(0, tema.ESP_LG))

        for clave, etiqueta in [("ajustes", "Ajustes"), ("legal", "Legal")]:
            boton = self._crear_boton(footer, clave, etiqueta)
            boton.pack(fill="x", pady=2)
            self._botones[clave] = boton

    def _crear_boton(self, padre, clave: str, etiqueta: str) -> ctk.CTkButton:
        ico_off = iconos.crear_icono_sidebar(clave, tema.COLOR_TEXTO_SECUNDARIO, size=17)
        ico_on = iconos.crear_icono_sidebar(clave, tema.COLOR_PRIMARIO, size=17)
        self._iconos_inactivos[clave] = ico_off
        self._iconos_activos[clave] = ico_on

        return ctk.CTkButton(
            padre,
            text=f"  {etiqueta}",
            image=ico_off,
            compound="left",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_NAV),
            anchor="w",
            height=tema.SIDEBAR_ITEM_ALTO,
            corner_radius=tema.SIDEBAR_ITEM_RADIO,
            fg_color="transparent",
            hover_color=tema.COLOR_ELEVADO_HOVER,
            text_color=tema.COLOR_TEXTO_SECUNDARIO,
            command=lambda c=clave: self._seleccionar(c),
        )

    def _seleccionar(self, clave: str):
        self.seleccionar_externo(clave)
        self.al_cambiar_pestana(clave)

    def seleccionar_externo(self, clave: str):
        self.pestana_activa = clave
        self._resaltar_activo()

    def _resaltar_activo(self):
        for clave, boton in self._botones.items():
            if clave == self.pestana_activa:
                boton.configure(
                    fg_color=tema.COLOR_ELEVADO,
                    text_color=tema.COLOR_PRIMARIO,
                    image=self._iconos_activos[clave],
                )
            else:
                boton.configure(
                    fg_color="transparent",
                    text_color=tema.COLOR_TEXTO_SECUNDARIO,
                    image=self._iconos_inactivos[clave],
                )
