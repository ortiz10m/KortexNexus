"""Pestaña de Modos Reales de Kortex Nexus."""

from __future__ import annotations

import threading

import customtkinter as ctk

from kortex_core.modes import MODOS_INFO, ModeManager
from kortex_ui import notificaciones, tema


class TabModos(ctk.CTkFrame):
    """Pestaña con 4 modos de optimización real y reversible."""

    def __init__(self, master, modes: ModeManager | None = None, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self.modes = modes or ModeManager()
        self._tarjetas: dict[str, dict] = {}
        self._ocupado = False

        self._construir_header()
        self._construir_modos()
        self._construir_consola()

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XL, tema.ESP_MD))

        ctk.CTkLabel(
            header, text="Modos de Optimización",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H1),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Ajustes reales sobre ZRAM, red, prioridades y Auto-Cryo. Reversibles al instante.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
        ).pack(anchor="w")

    def _construir_modos(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))
        contenedor.grid_columnconfigure((0, 1), weight=1, uniform="modo")

        orden = ["supervivencia", "gaming", "streaming", "trabajo"]
        for idx, clave in enumerate(orden):
            info = MODOS_INFO[clave]
            self._tarjeta_modo(
                contenedor,
                fila=idx // 2,
                columna=idx % 2,
                clave=clave,
                titulo=info["titulo"],
                descripcion=info["descripcion"],
                color=info["color"],
            )

    def _tarjeta_modo(self, padre, fila: int, columna: int, clave: str, titulo: str, descripcion: str, color: str):
        card = ctk.CTkFrame(
            padre,
            fg_color=tema.COLOR_SUPERFICIE,
            corner_radius=tema.RADIO_MD,
            border_width=2,
            border_color=tema.COLOR_BORDE,
            height=175,
        )
        card.grid(
            row=fila,
            column=columna,
            padx=(0, tema.ESP_MD) if columna == 0 else (0, 0),
            pady=(0, tema.ESP_MD) if fila == 0 else (0, 0),
            sticky="nsew",
        )
        card.grid_propagate(False)

        ctk.CTkLabel(
            card, text=titulo,
            font=(tema.FUENTE_TITULO, tema.TAMANO_H3),
            text_color=color, anchor="w",
        ).pack(anchor="w", padx=tema.ESP_LG, pady=(tema.ESP_MD, tema.ESP_XS))

        ctk.CTkLabel(
            card, text=descripcion,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO,
            anchor="w", justify="left", wraplength=340,
        ).pack(anchor="w", padx=tema.ESP_LG, pady=(0, tema.ESP_SM))

        pie = ctk.CTkFrame(card, fg_color="transparent")
        pie.pack(fill="x", side="bottom", padx=tema.ESP_LG, pady=tema.ESP_MD)

        estado_label = ctk.CTkLabel(
            pie, text="● Inactivo",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO, "bold"),
            text_color=tema.COLOR_TEXTO_TERCIARIO,
            anchor="w",
        )
        estado_label.pack(side="left")

        boton = ctk.CTkButton(
            pie,
            text="Activar",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=color,
            hover_color=color,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            height=34,
            width=120,
            command=lambda c=clave: self._toggle_modo(c),
        )
        boton.pack(side="right")

        self._tarjetas[clave] = {
            "card": card,
            "boton": boton,
            "estado": estado_label,
            "color": color,
        }

    def _construir_consola(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_XL))

        ctk.CTkLabel(
            contenedor, text="Actividad del modo",
            font=(tema.FUENTE_TITULO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w", pady=(0, tema.ESP_XS))

        self.consola = ctk.CTkTextbox(
            contenedor,
            font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO),
            fg_color=tema.COLOR_SUPERFICIE,
            text_color=tema.COLOR_EXITO,
            corner_radius=tema.RADIO_MD,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            height=110,
        )
        self.consola.pack(fill="both", expand=True)
        self.consola.insert("0.0", ">>> Selecciona un modo para aplicar optimizaciones reales.\n")
        self.consola.configure(state="disabled")

    def _log(self, mensaje: str):
        def _escribir():
            if not self.winfo_exists():
                return
            self.consola.configure(state="normal")
            self.consola.insert("end", f">>> {mensaje}\n")
            self.consola.see("end")
            self.consola.configure(state="disabled")

        try:
            self.after(0, _escribir)
        except Exception:
            pass

    def _refrescar_tarjetas(self):
        if not self.winfo_exists():
            return
        activo = self.modes.modo_activo
        for clave, t in self._tarjetas.items():
            if clave == activo:
                t["card"].configure(border_color=t["color"])
                t["boton"].configure(text="Desactivar", fg_color="#333333", hover_color="#444444")
                t["estado"].configure(text="● Activo", text_color=t["color"])
            else:
                t["card"].configure(border_color=tema.COLOR_BORDE)
                t["boton"].configure(text="Activar", fg_color=t["color"], hover_color=t["color"])
                t["estado"].configure(text="● Inactivo", text_color=tema.COLOR_TEXTO_TERCIARIO)

    def _toggle_modo(self, clave: str):
        if self._ocupado:
            return
        self._ocupado = True

        def _worker():
            try:
                if self.modes.modo_activo == clave:
                    res = self.modes.desactivar(on_paso=lambda p: self._log(f"  ↺ {p}"))
                    self._log(res.get("message", f"Modo {clave} desactivado."))
                    self.after(0, lambda: notificaciones.notificar("info", "Modo desactivado", res.get("message", "")))
                else:
                    res = self.modes.activar(clave, on_paso=lambda p: self._log(f"  ✓ {p}"))
                    self._log(res.get("message", f"Modo {clave} activado."))
                    self.after(0, lambda: notificaciones.notificar("exito", f"Modo {clave.capitalize()}", res.get("message", "")))
            except Exception as e:
                self._log(f"Error aplicando modo: {e}")
            finally:
                self._ocupado = False
                self.after(0, self._refrescar_tarjetas)

        threading.Thread(target=_worker, daemon=True).start()
