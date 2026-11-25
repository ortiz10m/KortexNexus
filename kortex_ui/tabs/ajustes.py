"""Pestaña de Ajustes de Kortex Nexus (persistencia real en config.json y autostart)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import customtkinter as ctk
import psutil

from kortex_core.config import (
    SISTEMA,
    KortexConfig,
    configurar_autostart,
    obtener_carpeta_boveda,
    obtener_disco_principal,
)
from kortex_core.optimizer import KernelOptimizer
from kortex_core.platform_hal import obtener_info_hardware
from kortex_ui import notificaciones, tema


VERSION = "2.0.0"


class TabAjustes(ctk.CTkFrame):
    """Pestaña de ajustes y configuración persistente."""

    def __init__(
        self,
        master,
        config: KortexConfig | None = None,
        optimizer: KernelOptimizer | None = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self.config = config or KortexConfig()
        self.optimizer = optimizer or KernelOptimizer()
        self.boveda = obtener_carpeta_boveda()

        self._construir_header()
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_XL))

        self._construir_info_sistema()
        self._construir_rutas()
        self._construir_configuracion()
        self._construir_reseteo()

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XL, tema.ESP_MD))

        ctk.CTkLabel(
            header, text="Ajustes",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H1),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header, text="Configuración general y diagnóstico de hardware.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
        ).pack(anchor="w")

    def _seccion_titulo(self, texto: str):
        ctk.CTkLabel(
            self.scroll, text=texto,
            font=(tema.FUENTE_TITULO, tema.TAMANO_H3),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w", pady=(tema.ESP_LG, tema.ESP_SM))

    def _seccion_card(self) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self.scroll,
            fg_color=tema.COLOR_SUPERFICIE,
            corner_radius=tema.RADIO_MD,
            border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        card.pack(fill="x", pady=(0, tema.ESP_SM))
        return card

    def _fila_info(self, padre, etiqueta: str, valor: str):
        fila = ctk.CTkFrame(padre, fg_color="transparent")
        fila.pack(fill="x", padx=tema.ESP_LG, pady=3)

        ctk.CTkLabel(
            fila, text=etiqueta,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_TERCIARIO,
            anchor="w", width=150,
        ).pack(side="left")

        ctk.CTkLabel(
            fila, text=valor,
            font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

    def _construir_info_sistema(self):
        self._seccion_titulo("Hardware y Sistema")
        card = self._seccion_card()
        ctk.CTkFrame(card, fg_color="transparent", height=tema.ESP_XS).pack()

        hw = obtener_info_hardware()
        self._fila_info(card, "Sistema:", f"{hw['distro']} ({hw['sesion_grafica']})")
        self._fila_info(
            card, "CPU:",
            f"{hw['modelo_cpu']} · {hw['nucleos_fisicos']}c/{hw['nucleos_logicos']}t · AVX2: {'Sí' if hw['avx2'] else 'No'}",
        )
        self._fila_info(
            card, "RAM y Perfil:",
            f"{hw['ram_total_mb']} MB ({hw['ram_disponible_mb']:.0f} MB disp.) · Perfil {hw['perfil']}",
        )
        try:
            uso = shutil.disk_usage(obtener_disco_principal())
            disco_txt = f"{round(uso.total / (1024 ** 3), 1)} GB · {round((uso.used / uso.total) * 100, 1)}% usado · Tipo: {hw['tipo_disco']}"
        except Exception:
            disco_txt = hw["tipo_disco"]
        self._fila_info(card, "Disco:", disco_txt)
        self._fila_info(card, "Privilegios:", "Administrador / Root" if hw["es_root"] else "Usuario estándar")
        self._fila_info(card, "Python / Kortex:", f"Python {sys.version.split()[0]} · Kortex v{VERSION}")

        ctk.CTkFrame(card, fg_color="transparent", height=tema.ESP_XS).pack()

    def _construir_rutas(self):
        self._seccion_titulo("Rutas de Datos")
        card = self._seccion_card()
        ctk.CTkFrame(card, fg_color="transparent", height=tema.ESP_XS).pack()

        rutas = [
            ("Bóveda:", self.boveda),
            ("Configuración:", self.config.ruta),
            ("Telemetría:", self.boveda / "kortex_datos.csv"),
            ("Papelera:", self.boveda / "papelera"),
        ]
        for etiqueta, ruta in rutas:
            self._fila_info(card, etiqueta, str(ruta))

        ctk.CTkButton(
            card,
            text="Abrir carpeta de datos",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_PRIMARIO,
            hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            height=36,
            command=self._abrir_carpeta_datos,
        ).pack(fill="x", padx=tema.ESP_LG, pady=(tema.ESP_SM, tema.ESP_MD))

    def _abrir_carpeta_datos(self):
        try:
            if SISTEMA == "Windows":
                os.startfile(str(self.boveda))
            else:
                subprocess.Popen(
                    ["xdg-open", str(self.boveda)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            print(f"[Ajustes] Error abriendo carpeta: {e}")

    def _construir_configuracion(self):
        self._seccion_titulo("Comportamiento")
        card = self._seccion_card()
        ctk.CTkFrame(card, fg_color="transparent", height=tema.ESP_XS).pack()

        self.var_historial = ctk.BooleanVar(value=bool(self.config.get("guardar_historial_chat", True)))
        self.var_datos = ctk.BooleanVar(value=bool(self.config.get("recolectar_datos", True)))
        self.var_auto_cryo = ctk.BooleanVar(value=bool(self.config.get("auto_cryo_activo", True)))
        self.var_auto_inicio = ctk.BooleanVar(value=bool(self.config.get("auto_inicio", False)))

        opciones = [
            ("Guardar historial de chat", self.var_historial, self._on_cambio_historial),
            ("Recolectar telemetría para predicción (CSV)", self.var_datos, self._on_cambio_datos),
            ("Auto-Cryo automático (congelar apps sin foco bajo presión)", self.var_auto_cryo, self._on_cambio_auto_cryo),
            ("Auto-iniciar daemon ligero (--daemon) con el sistema", self.var_auto_inicio, self._on_cambio_autostart),
        ]

        for texto, var, cmd in opciones:
            ctk.CTkCheckBox(
                card,
                text=texto,
                variable=var,
                command=cmd,
                font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
                text_color=tema.COLOR_TEXTO,
                fg_color=tema.COLOR_PRIMARIO,
                hover_color=tema.COLOR_PRIMARIO_HOVER,
                border_color=tema.COLOR_BORDE_FUERTE,
                corner_radius=tema.RADIO_SM,
            ).pack(anchor="w", padx=tema.ESP_LG, pady=tema.ESP_XS)

        ctk.CTkFrame(card, fg_color="transparent", height=tema.ESP_XS).pack()

    def _on_cambio_historial(self):
        self.config.set("guardar_historial_chat", bool(self.var_historial.get()))

    def _on_cambio_datos(self):
        self.config.set("recolectar_datos", bool(self.var_datos.get()))

    def _on_cambio_auto_cryo(self):
        self.config.set("auto_cryo_activo", bool(self.var_auto_cryo.get()))

    def _on_cambio_autostart(self):
        activar = bool(self.var_auto_inicio.get())
        ok, msg = configurar_autostart(activar)
        if ok:
            self.config.set("auto_inicio", activar)
            notificaciones.notificar("exito", "Auto-inicio", msg)
        else:
            self.var_auto_inicio.set(not activar)
            notificaciones.notificar("error", "Auto-inicio", msg)

    def _construir_reseteo(self):
        self._seccion_titulo("Resetear Datos")
        card = self._seccion_card()
        ctk.CTkFrame(card, fg_color="transparent", height=tema.ESP_XS).pack()

        self.var_reset_notas = ctk.BooleanVar(value=False)
        self.var_reset_datos = ctk.BooleanVar(value=False)
        self.var_reset_chat = ctk.BooleanVar(value=False)

        for texto, var in (
            ("Notas Markdown", self.var_reset_notas),
            ("Telemetría CSV del Centinela", self.var_reset_datos),
            ("Historial del chat", self.var_reset_chat),
        ):
            ctk.CTkCheckBox(
                card, text=texto, variable=var,
                font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
                text_color=tema.COLOR_TEXTO,
                fg_color=tema.COLOR_PRIMARIO,
                hover_color=tema.COLOR_PRIMARIO_HOVER,
                border_color=tema.COLOR_BORDE_FUERTE,
                corner_radius=tema.RADIO_SM,
            ).pack(anchor="w", padx=tema.ESP_LG, pady=tema.ESP_XS)

        ctk.CTkButton(
            card,
            text="Resetear seleccionados",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_ERROR,
            hover_color="#DC2626",
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            height=36,
            command=self._resetear,
        ).pack(fill="x", padx=tema.ESP_LG, pady=(tema.ESP_SM, tema.ESP_MD))

    def _resetear(self):
        borrados = []
        try:
            if self.var_reset_notas.get():
                carpeta_notas = self.boveda / "notas"
                if carpeta_notas.exists():
                    for archivo in carpeta_notas.glob("*.md"):
                        archivo.unlink(missing_ok=True)
                borrados.append("Notas")
            if self.var_reset_datos.get():
                for nombre in ("kortex_datos.csv", "kortex_modelo.pkl"):
                    (self.boveda / nombre).unlink(missing_ok=True)
                borrados.append("Telemetría")
            if self.var_reset_chat.get():
                (self.boveda / "chat_historial.json").unlink(missing_ok=True)
                borrados.append("Chat")

            if borrados:
                notificaciones.notificar("exito", "Reseteo completado", f"Eliminado: {', '.join(borrados)}")
            else:
                notificaciones.notificar("info", "Sin cambios", "Marca al menos una casilla.")
        except Exception as e:
            notificaciones.notificar("error", "Error reseteando", str(e)[:80])
