"""Pestaña de Monitor de Kortex Nexus (thread-safe, pausable y con Cámara Criogénica)."""

from __future__ import annotations

import threading

import customtkinter as ctk
import psutil

from kortex_core.config import KortexConfig
from kortex_core.cryo import CryoEngine
from kortex_core.optimizer import KernelOptimizer
from kortex_core.platform_hal import leer_metricas_memoria, leer_presion_memoria
from kortex_ui import componentes, notificaciones, tema


COLOR_POR_NIVEL = {
    "baja": tema.COLOR_EXITO,
    "media": tema.COLOR_INFO,
    "alta": tema.COLOR_ADVERTENCIA,
    "critica": tema.COLOR_ERROR,
}


class TabMonitor(ctk.CTkFrame):
    """Pestaña de monitoreo real, acciones de kernel y Cámara Criogénica."""

    def __init__(
        self,
        master,
        config: KortexConfig | None = None,
        optimizer: KernelOptimizer | None = None,
        cryo: CryoEngine | None = None,
        sentinel=None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self.config = config or KortexConfig()
        self.cryo = cryo or CryoEngine()
        self.optimizer = optimizer or KernelOptimizer(cryo=self.cryo)
        self.sentinel = sentinel

        self._activo = False
        self._after_id = None

        self._construir_header()
        self._construir_metricas()
        self._construir_acciones()
        self._construir_crio()
        self._construir_consola()

    def al_mostrar(self):
        if self._activo:
            return
        self._activo = True
        self._programar_tick(50)

    def al_ocultar(self):
        self._activo = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _programar_tick(self, delay_ms: int = 1500):
        if not self._activo or not self.winfo_exists():
            return
        self._after_id = self.after(delay_ms, self._actualizar_metricas)

    # --- UI ---

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XL, tema.ESP_MD))

        izq = ctk.CTkFrame(header, fg_color="transparent")
        izq.pack(side="left")

        ctk.CTkLabel(
            izq, text="Monitor en Vivo",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H1),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            izq, text="Métricas reales de RAM disponible, Swap/ZRAM y Presión del Kernel.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
        ).pack(anchor="w")

        self.lbl_presion = ctk.CTkLabel(
            header,
            text="● PRESIÓN: BAJA",
            font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO, "bold"),
            text_color=tema.COLOR_EXITO,
        )
        self.lbl_presion.pack(side="right", anchor="s")

    def _construir_metricas(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))

        self.metricas = {}
        self._crear_barra(contenedor, "cpu", "CPU", tema.COLOR_ERROR)
        self._crear_barra(contenedor, "ram", "RAM Real", tema.COLOR_INFO)
        self._crear_barra(contenedor, "swap", "Swap / ZRAM", tema.COLOR_ADVERTENCIA)

    def _crear_barra(self, padre, clave: str, titulo: str, color: str):
        bloque = ctk.CTkFrame(padre, fg_color="transparent")
        bloque.pack(fill="x", pady=3)

        fila = ctk.CTkFrame(bloque, fg_color="transparent")
        fila.pack(fill="x")

        ctk.CTkLabel(
            fila, text=titulo,
            font=(tema.FUENTE_TITULO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(side="left")

        valor = ctk.CTkLabel(
            fila, text="0%",
            font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO, "bold"),
            text_color=color, anchor="e",
        )
        valor.pack(side="right")

        barra = ctk.CTkProgressBar(
            bloque, progress_color=color, fg_color=tema.COLOR_BORDE,
            height=9, corner_radius=tema.RADIO_SM,
        )
        barra.pack(fill="x", pady=(2, 0))
        barra.set(0)

        self.metricas[clave] = {"barra": barra, "valor": valor}

    def _actualizar_metricas(self):
        if not self._activo or not self.winfo_exists():
            return
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = leer_metricas_memoria()
            presion = leer_presion_memoria()

            self.metricas["cpu"]["barra"].set(min(1.0, max(0.0, cpu / 100.0)))
            self.metricas["cpu"]["valor"].configure(text=f"{cpu:.1f}%")

            self.metricas["ram"]["barra"].set(min(1.0, max(0.0, mem["ram_pct"] / 100.0)))
            self.metricas["ram"]["valor"].configure(
                text=f"{mem['ram_pct']:.1f}% ({mem['ram_disponible_mb']:.0f} MB libres)"
            )

            self.metricas["swap"]["barra"].set(min(1.0, max(0.0, mem["swap_pct"] / 100.0)))
            self.metricas["swap"]["valor"].configure(
                text=f"{mem['swap_pct']:.1f}% ({mem['swap_usado_mb']:.0f} MB)"
            )

            nivel = presion.get("nivel", "baja")
            psi_txt = (
                f" · PSI {presion['psi_some_10']:.1f}%"
                if presion.get("psi_disponible")
                else ""
            )
            self.lbl_presion.configure(
                text=f"● PRESIÓN: {nivel.upper()}{psi_txt}",
                text_color=COLOR_POR_NIVEL.get(nivel, tema.COLOR_TEXTO),
            )

            congelados = self.cryo.listar_congelados()
            if hasattr(self, "lbl_cryo_estado"):
                self.lbl_cryo_estado.configure(
                    text=f"{len(congelados)} proceso(s) suspendido(s)"
                )
        except Exception:
            pass

        self._programar_tick(1500)

    def _construir_acciones(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))
        contenedor.grid_columnconfigure((0, 1, 2), weight=1, uniform="accion")

        self._boton_accion(
            contenedor, 0,
            "Purgar Memoria",
            "Libera sin dañar caché en HDD",
            tema.COLOR_ERROR,
            self._accion_purgar,
        )
        self._boton_accion(
            contenedor, 1,
            "Acelerar Red",
            "TCP BBR (Linux) / CTCP (Win)",
            tema.COLOR_INFO,
            self._accion_red,
        )
        self._boton_accion(
            contenedor, 2,
            "Ultra Rendimiento",
            "ZRAM + Jaulas + Hyper-Focus",
            tema.COLOR_PRIMARIO,
            self._accion_ultra,
        )

    def _boton_accion(self, padre, columna: int, titulo: str, subtitulo: str, color: str, comando):
        card = componentes.Card(padre)
        card.grid(
            row=0, column=columna,
            padx=(0, tema.ESP_MD) if columna < 2 else (0, 0),
            sticky="nsew",
        )

        ctk.CTkButton(
            card,
            text=titulo,
            font=(tema.FUENTE_TITULO, tema.TAMANO_CUERPO),
            fg_color=color,
            hover_color=color,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            height=42,
            command=comando,
        ).pack(fill="x", padx=tema.ESP_MD, pady=(tema.ESP_MD, tema.ESP_XS))

        ctk.CTkLabel(
            card,
            text=subtitulo,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO,
            anchor="w",
        ).pack(anchor="w", padx=tema.ESP_MD, pady=(0, tema.ESP_MD))

    def _construir_crio(self):
        card = componentes.Card(self)
        card.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))

        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.pack(fill="x", padx=tema.ESP_LG, pady=tema.ESP_MD)

        self.var_auto_cryo = ctk.BooleanVar(value=bool(self.config.get("auto_cryo_activo", True)))
        ctk.CTkSwitch(
            fila,
            text="Auto-Cryo (congelar inactivas)",
            variable=self.var_auto_cryo,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            progress_color=tema.COLOR_PRIMARIO,
            command=self._toggle_auto_cryo,
        ).pack(side="left")

        self.lbl_cryo_estado = ctk.CTkLabel(
            fila,
            text="0 proceso(s) suspendido(s)",
            font=(tema.FUENTE_MONO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_cryo_estado.pack(side="left", padx=tema.ESP_LG)

        ctk.CTkButton(
            fila,
            text="Reanudar todo",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=tema.COLOR_BORDE_FUERTE,
            hover_color=tema.COLOR_ELEVADO_HOVER,
            height=30,
            width=125,
            command=self._descongelar_todo,
        ).pack(side="right")

        self.entry_cryo = ctk.CTkEntry(
            fila,
            placeholder_text="Proceso a suspender (ej: discord)",
            width=190,
            height=30,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            fg_color=tema.COLOR_FONDO,
            border_color=tema.COLOR_BORDE,
        )
        self.entry_cryo.pack(side="right", padx=(0, tema.ESP_SM))

        ctk.CTkButton(
            fila,
            text="Suspender",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO, "bold"),
            fg_color=tema.COLOR_INFO,
            height=30,
            width=92,
            command=self._congelar_manual,
        ).pack(side="right", padx=(0, tema.ESP_XS))

    def _construir_consola(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_XL))

        ctk.CTkLabel(
            contenedor,
            text="Registro del sistema",
            font=(tema.FUENTE_TITULO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO,
            anchor="w",
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
        self.consola.insert("0.0", ">>> Monitor listo.\n")
        self.consola.configure(state="disabled")

    def _log(self, mensaje: str):
        """Log 100% thread-safe: siempre programa escritura en el hilo principal."""
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

    # --- Acciones ---

    def _toggle_auto_cryo(self):
        activo = bool(self.var_auto_cryo.get())
        self.config.set("auto_cryo_activo", activo)
        self._log(f"Auto-Cryo {'activado' if activo else 'desactivado'}.")

    def _congelar_manual(self):
        nombre = self.entry_cryo.get().strip()
        if not nombre:
            self._log("Escribe el nombre del proceso a criogenizar.")
            return
        self.entry_cryo.delete(0, "end")

        def _run():
            res = self.cryo.criogenizar_proceso(nombre, motivo="manual")
            self._log(res.get("message", ""))

        threading.Thread(target=_run, daemon=True).start()

    def _descongelar_todo(self):
        def _run():
            res = self.cryo.descongelar_todo()
            self._log(res.get("message", "Procesos reanudados."))

        threading.Thread(target=_run, daemon=True).start()

    def _accion_purgar(self):
        self._log("Ejecutando purga inteligente de memoria...")
        threading.Thread(target=self._purgar_en_hilo, daemon=True).start()

    def _purgar_en_hilo(self):
        try:
            ram_antes = leer_metricas_memoria()["ram_pct"]
            resultado = self.optimizer.force_memory_purge(agresiva=False)
            if resultado:
                if self.sentinel:
                    self.sentinel.registrar_purga()
                ram_despues = leer_metricas_memoria()["ram_pct"]
                liberado = max(0.0, ram_antes - ram_despues)
                self._log(f"Purga completada: {ram_antes:.1f}% → {ram_despues:.1f}%")
                self.after(0, lambda: notificaciones.notificar(
                    "exito", "Purga completada", f"{ram_antes:.1f}% → {ram_despues:.1f}% · {liberado:.1f}% liberado"
                ))
            else:
                self._log("La purga requiere permisos de administrador/root.")
                self.after(0, lambda: notificaciones.notificar(
                    "advertencia", "Purga limitada", "Requiere permisos de administrador."
                ))
        except Exception as e:
            err = str(e)
            self._log(f"Error en purga: {err}")

    def _accion_red(self):
        self._log("Optimizando congestión de red...")
        threading.Thread(target=self._red_en_hilo, daemon=True).start()

    def _red_en_hilo(self):
        try:
            ok = self.optimizer.acelerar_internet()
            if ok:
                self._log("Aceleración de red (BBR / CTCP) activada.")
                self.after(0, lambda: notificaciones.notificar("exito", "Red acelerada", "TCP optimizado."))
            else:
                self._log("No se pudo modificar TCP global (requiere admin/root).")
                self.after(0, lambda: notificaciones.notificar(
                    "advertencia", "Red no modificada", "Requiere permisos de administrador."
                ))
        except Exception as e:
            self._log(f"Error en red: {e}")

    def _accion_ultra(self):
        self._log("Ejecutando Ultra Rendimiento...")
        threading.Thread(target=self._ultra_en_hilo, daemon=True).start()

    def _ultra_en_hilo(self):
        try:
            pasos = []
            if self.optimizer.proteger_proceso(es_daemon=False):
                self._log("✓ Prioridad de Kortex ajustada.")
                pasos.append("Prioridad")
            if self.optimizer.activar_expansion_memoria():
                self._log("✓ Expansión / compresión de memoria activa.")
                pasos.append("Memoria")
            if self.optimizer.set_cpu_governor("auto"):
                self._log("✓ Governor / Plan de energía optimizado.")
                pasos.append("CPU")
            hf = self.cryo.activar_hyper_focus()
            if hf.get("success"):
                self._log(f"✓ {hf['message']}")
                pasos.append("Hyper-Focus")
            jaulas = self.optimizer.activar_jaulas_jerarquicas()
            if jaulas:
                self._log(f"✓ {jaulas} procesos pesados en jaulas.")
                pasos.append("Jaulas")

            self._log(f"Ultra Rendimiento finalizado ({len(pasos)} ajustes).")
            self.after(0, lambda n=len(pasos): notificaciones.notificar(
                "exito", "Ultra Rendimiento", f"{n} optimizaciones aplicadas."
            ))
        except Exception as e:
            self._log(f"Error en Ultra Rendimiento: {e}")
