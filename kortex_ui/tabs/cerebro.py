"""Pestaña de Cerebro de Kortex Nexus (conectada a instancias compartidas de kortex_core)."""

from __future__ import annotations

import threading

import customtkinter as ctk

from kortex_ui import tema


class TabCerebro(ctk.CTkFrame):
    """Pestaña de chat local con el cerebro de Kortex."""

    def __init__(self, master, cerebro=None, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self.cerebro = cerebro
        if self.cerebro is None:
            self._cargar_cerebro()

        self._construir_header()
        self._construir_chat()
        self._construir_input()
        self._mensaje_inicial()

    def _cargar_cerebro(self):
        try:
            from cerebro import CerebroKortex

            self.cerebro = CerebroKortex()
        except Exception as e:
            print(f"[Cerebro] Error cargando cerebro: {e}")
            self.cerebro = None

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XL, tema.ESP_MD))

        ctk.CTkLabel(header, text="Cerebro", font=(tema.FUENTE_TITULO, tema.TAMANO_H1), text_color=tema.COLOR_TEXTO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(header, text="Comandos reales y diagnóstico local. 100% offline.", font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO), text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w").pack(anchor="w")

    def _construir_chat(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))

        self.chat_area = ctk.CTkScrollableFrame(
            contenedor, fg_color=tema.COLOR_SUPERFICIE,
            corner_radius=tema.RADIO_MD, border_width=1, border_color=tema.COLOR_BORDE,
        )
        self.chat_area.pack(fill="both", expand=True)

    def _mensaje_inicial(self):
        self._agregar_mensaje(
            "Kortex",
            "Hola. Soy Kortex v2.0, tu asistente Anti-Freeze local.\n\n"
            "Prueba comandos reales como:\n"
            "- \"diagnostica mi pc\"\n"
            "- \"purga la ram\" / \"acelera internet\"\n"
            "- \"modo supervivencia\" / \"modo gaming\" / \"desactiva modo\"\n"
            "- \"congela discord\" / \"descongela todo\"\n"
            "- \"qué es la criogenia\" / \"qué es el swap\"",
        )

    def _agregar_mensaje(self, autor: str, texto: str):
        if not self.winfo_exists():
            return
        es_usuario = autor == "Tú"

        fila = ctk.CTkFrame(self.chat_area, fg_color="transparent")
        fila.pack(fill="x", pady=tema.ESP_SM, padx=tema.ESP_MD)

        burbuja = ctk.CTkFrame(
            fila,
            fg_color=tema.COLOR_PRIMARIO if es_usuario else tema.COLOR_ELEVADO,
            corner_radius=tema.RADIO_LG,
        )
        burbuja.pack(anchor="e" if es_usuario else "w")

        ctk.CTkLabel(
            burbuja, text=autor,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO, "bold"),
            text_color=tema.COLOR_TEXTO_DESHABILITADO if es_usuario else tema.COLOR_PRIMARIO,
            anchor="w",
        ).pack(anchor="w", padx=tema.ESP_LG, pady=(tema.ESP_SM, 0))

        ctk.CTkLabel(
            burbuja, text=texto,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            text_color=tema.COLOR_TEXTO, anchor="w", justify="left", wraplength=640,
        ).pack(anchor="w", padx=tema.ESP_LG, pady=(tema.ESP_XS, tema.ESP_MD))

        self.after(50, lambda: self.winfo_exists() and self.chat_area._parent_canvas.yview_moveto(1.0))

    def _construir_input(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_XL))

        sugerencias = ctk.CTkFrame(contenedor, fg_color="transparent")
        sugerencias.pack(fill="x", pady=(0, tema.ESP_SM))

        for texto in ["Diagnostica mi PC", "Modo supervivencia", "Purga la RAM", "Info del sistema"]:
            ctk.CTkButton(
                sugerencias, text=texto,
                font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
                fg_color="transparent", hover_color=tema.COLOR_ELEVADO_HOVER,
                text_color=tema.COLOR_TEXTO_TERCIARIO, border_width=1, border_color=tema.COLOR_BORDE,
                corner_radius=tema.RADIO_SM, height=28,
                command=lambda t=texto: self._enviar_sugerencia(t),
            ).pack(side="left", padx=(0, tema.ESP_XS))

        fila = ctk.CTkFrame(contenedor, fg_color="transparent")
        fila.pack(fill="x")

        self.entrada = ctk.CTkEntry(
            fila, placeholder_text="Escribe un mensaje o comando...",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            fg_color=tema.COLOR_ELEVADO, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, placeholder_text_color=tema.COLOR_TEXTO_TERCIARIO,
            corner_radius=tema.RADIO_MD, height=44,
        )
        self.entrada.pack(side="left", fill="x", expand=True, padx=(0, tema.ESP_SM))
        self.entrada.bind("<Return>", lambda e: self._enviar())

        self.boton_enviar = ctk.CTkButton(
            fila, text="Enviar", font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO, "bold"),
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO, corner_radius=tema.RADIO_MD, height=44, width=105,
            command=self._enviar,
        )
        self.boton_enviar.pack(side="right")

    def _enviar_sugerencia(self, texto: str):
        self.entrada.delete(0, "end")
        self.entrada.insert(0, texto)
        self._enviar()

    def _enviar(self):
        mensaje = self.entrada.get().strip()
        if not mensaje:
            return
        self.entrada.delete(0, "end")
        self._agregar_mensaje("Tú", mensaje)
        self.boton_enviar.configure(state="disabled", text="...")
        threading.Thread(target=self._procesar, args=(mensaje,), daemon=True).start()

    def _procesar(self, mensaje: str):
        if not self.cerebro:
            self.after(0, lambda: (self._agregar_mensaje("Kortex", "El cerebro no está disponible."), self._reactivar_boton()))
            return
        try:
            respuesta = self.cerebro.pensar(mensaje)
        except Exception as e:
            respuesta = f"Error procesando el mensaje: {e}"
        self.after(0, lambda r=respuesta: (self._agregar_mensaje("Kortex", r), self._reactivar_boton()))

    def _reactivar_boton(self):
        if self.winfo_exists():
            self.boton_enviar.configure(state="normal", text="Enviar")
