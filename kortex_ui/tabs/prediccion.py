"""Pestaña de Predicción en vivo de Kortex Nexus (EWMA + Regresión Temporal)."""

from __future__ import annotations

import shutil
import threading

import customtkinter as ctk
import psutil

from kortex_core.config import obtener_disco_principal
from kortex_core.optimizer import KernelOptimizer
from kortex_core.platform_hal import leer_metricas_memoria
from kortex_core.predictor import KortexPredictor
from kortex_ui import tema


class TabPrediccion(ctk.CTkFrame):
    """Pestaña de predicción de cuellos de botella con 0 dependencias pesadas."""

    def __init__(
        self,
        master,
        predictor: KortexPredictor | None = None,
        optimizer: KernelOptimizer | None = None,
        sentinel=None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self.predictor = predictor or KortexPredictor()
        self.optimizer = optimizer or KernelOptimizer()
        self.sentinel = sentinel
        self.actualizando = False
        self._activo = False
        self._after_id = None

        self._construir_header()
        self._construir_estado()
        self._construir_predicciones()
        self._construir_acciones()

    def al_mostrar(self):
        if self._activo:
            return
        self._activo = True
        self._actualizar_ahora()
        self._programar_ciclo()

    def al_ocultar(self):
        self._activo = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _programar_ciclo(self):
        if not self._activo or not self.winfo_exists():
            return
        self._after_id = self.after(15000, self._ciclo)

    def _ciclo(self):
        if not self._activo or not self.winfo_exists():
            return
        self._actualizar_ahora()
        self._programar_ciclo()

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XL, tema.ESP_MD))

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left")

        ctk.CTkLabel(
            info, text="Predicción en Vivo",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H1),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            info,
            text="Proyección por timestamps reales (EWMA + regresión ponderada) y tiempo hasta saturación.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
        ).pack(anchor="w")

        self.lbl_modo = ctk.CTkLabel(
            header, text="Motor: EWMA en Vivo",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO, "bold"),
            text_color=tema.COLOR_EXITO,
        )
        self.lbl_modo.pack(side="right")

    def _construir_estado(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))

        self.card_estado = ctk.CTkFrame(
            contenedor, fg_color=tema.COLOR_SUPERFICIE,
            corner_radius=tema.RADIO_MD, border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        self.card_estado.pack(fill="x")

        info = ctk.CTkFrame(self.card_estado, fg_color="transparent")
        info.pack(fill="x", padx=tema.ESP_LG, pady=tema.ESP_MD)

        self.lbl_estado = ctk.CTkLabel(
            info, text="Analizando tendencia del sistema...",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H3),
            text_color=tema.COLOR_TEXTO, anchor="w",
        )
        self.lbl_estado.pack(anchor="w")

        self.lbl_subestado = ctk.CTkLabel(
            info, text="Esperando muestras en vivo.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
        )
        self.lbl_subestado.pack(anchor="w", pady=(tema.ESP_XS, 0))

    def _construir_predicciones(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))
        contenedor.grid_columnconfigure((0, 1, 2), weight=1, uniform="pred")

        self.tarjetas = {}
        self._tarjeta_prediccion(contenedor, 0, "ram", "RAM", tema.COLOR_INFO)
        self._tarjeta_prediccion(contenedor, 1, "cpu", "CPU", tema.COLOR_ERROR)
        self._tarjeta_prediccion(contenedor, 2, "disco", "Disco", tema.COLOR_ADVERTENCIA)

    def _tarjeta_prediccion(self, padre, columna: int, clave: str, titulo: str, color: str):
        card = ctk.CTkFrame(
            padre, fg_color=tema.COLOR_SUPERFICIE,
            corner_radius=tema.RADIO_MD, border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        card.grid(row=0, column=columna, padx=(0, tema.ESP_MD) if columna < 2 else (0, 0), sticky="nsew")

        ctk.CTkLabel(
            card, text=titulo,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
        ).pack(anchor="w", padx=tema.ESP_LG, pady=(tema.ESP_MD, 0))

        valor = ctk.CTkLabel(
            card, text="—",
            font=(tema.FUENTE_TITULO, 26),
            text_color=color, anchor="w",
        )
        valor.pack(anchor="w", padx=tema.ESP_LG)

        meta = ctk.CTkLabel(
            card, text="tendencia: —",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
        )
        meta.pack(anchor="w", padx=tema.ESP_LG, pady=(0, tema.ESP_SM))

        pred5 = ctk.CTkLabel(card, text="→ 5 min: —", font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO), text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w")
        pred5.pack(anchor="w", padx=tema.ESP_LG)
        pred15 = ctk.CTkLabel(card, text="→ 15 min: —", font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO), text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w")
        pred15.pack(anchor="w", padx=tema.ESP_LG)
        pred30 = ctk.CTkLabel(card, text="→ 30 min: —", font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO), text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w")
        pred30.pack(anchor="w", padx=tema.ESP_LG, pady=(0, tema.ESP_MD))

        self.tarjetas[clave] = {"valor": valor, "meta": meta, "pred5": pred5, "pred15": pred15, "pred30": pred30}

    def _construir_acciones(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))

        self.btn_prevenir = ctk.CTkButton(
            contenedor, text="Prevenir ahora",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_NAV, "bold"),
            fg_color=tema.COLOR_PRIMARIO,
            hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            height=42, width=180,
            command=self._prevenir,
            state="disabled",
        )
        self.btn_prevenir.pack(side="left", padx=(0, tema.ESP_SM))

        ctk.CTkButton(
            contenedor, text="Actualizar",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            fg_color="transparent",
            border_width=1,
            border_color=tema.COLOR_BORDE_FUERTE,
            hover_color=tema.COLOR_ELEVADO_HOVER,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            height=42, width=130,
            command=self._actualizar_ahora,
        ).pack(side="left")

        self.consola = ctk.CTkTextbox(
            self, font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO),
            fg_color=tema.COLOR_SUPERFICIE, text_color=tema.COLOR_EXITO,
            corner_radius=tema.RADIO_MD, border_width=1,
            border_color=tema.COLOR_BORDE, height=110,
        )
        self.consola.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_XL))
        self.consola.insert("0.0", ">>> Listo.\n")
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

    def _actualizar_ahora(self):
        if self.actualizando:
            return
        self.actualizando = True
        threading.Thread(target=self._calcular_prediccion, daemon=True).start()

    def _calcular_prediccion(self):
        try:
            mem = leer_metricas_memoria()
            ram_actual = mem["ram_pct"]
            cpu_actual = psutil.cpu_percent(interval=0.2)
            disco_actual = self._disco_pct()

            # Registrar observación en vivo si el predictor tiene pocas muestras
            self.predictor.registrar_muestra(ram_actual, cpu_actual, mem["swap_pct"])
            horizonte = self.predictor.predecir_horizonte(ram_actual, cpu_actual)

            pred_disco = {"actual": disco_actual, "5": disco_actual, "15": disco_actual, "30": disco_actual, "tendencia_min": 0.0, "ttc_90_min": None}

            self.after(0, lambda: self._actualizar_ui(
                ram_actual, cpu_actual, disco_actual,
                horizonte["ram"], horizonte["cpu"], pred_disco,
                horizonte["muestras"], horizonte["confianza_pct"],
            ))
        except Exception as e:
            self._log(f"Error calculando predicción: {e}")
        finally:
            self.actualizando = False

    def _disco_pct(self) -> float:
        try:
            uso = shutil.disk_usage(obtener_disco_principal())
            return round((uso.used / uso.total) * 100, 1)
        except Exception:
            return 0.0

    def _actualizar_ui(self, ram_actual, cpu_actual, disco_actual, pred_ram, pred_cpu, pred_disco, muestras, confianza):
        if not self.winfo_exists():
            return

        if muestras >= 3:
            self.lbl_modo.configure(
                text=f"Motor: EWMA ({muestras} muestras · {confianza:.0f}% conf.)",
                text_color=tema.COLOR_EXITO,
            )
        else:
            self.lbl_modo.configure(
                text=f"Recolectando ({muestras}/3 muestras)",
                text_color=tema.COLOR_ADVERTENCIA,
            )

        self._actualizar_tarjeta("ram", ram_actual, pred_ram)
        self._actualizar_tarjeta("cpu", cpu_actual, pred_cpu)
        self._actualizar_tarjeta("disco", disco_actual, pred_disco)
        self._actualizar_estado(disco_actual, pred_ram, pred_cpu)

    def _actualizar_tarjeta(self, clave: str, actual: float, pred: dict):
        t = self.tarjetas[clave]
        t["valor"].configure(text=f"{actual:.1f}%")
        if clave == "disco":
            t["meta"].configure(text="almacenamiento principal")
        else:
            ttc = pred.get("ttc_90_min")
            ttc_txt = f" · TTC 90%: {ttc:.0f}m" if ttc is not None else ""
            t["meta"].configure(text=f"{pred.get('tendencia_min', 0.0):+.2f}%/min{ttc_txt}")
        t["pred5"].configure(text=f"→ 5 min:  {pred['5']:.1f}%")
        t["pred15"].configure(text=f"→ 15 min: {pred['15']:.1f}%")
        t["pred30"].configure(text=f"→ 30 min: {pred['30']:.1f}%")

    def _actualizar_estado(self, disco, pred_ram, pred_cpu):
        problemas = []
        color_estado = tema.COLOR_EXITO

        if pred_ram["15"] >= 85 or pred_ram["30"] >= 88:
            problemas.append(f"RAM proyectada al {max(pred_ram['15'], pred_ram['30']):.1f}%")
            color_estado = tema.COLOR_ERROR
        elif pred_ram["30"] >= 80:
            problemas.append(f"RAM en ascenso ({pred_ram['30']:.1f}% en 30m)")
            color_estado = tema.COLOR_ADVERTENCIA

        if pred_cpu["30"] >= 85:
            problemas.append(f"CPU sostenido al {pred_cpu['30']:.1f}%")
            if color_estado != tema.COLOR_ERROR:
                color_estado = tema.COLOR_ADVERTENCIA

        if disco >= 90:
            problemas.append(f"Disco al {disco:.1f}% (crítico)")
            color_estado = tema.COLOR_ERROR
        elif disco >= 82:
            problemas.append(f"Disco al {disco:.1f}%")
            if color_estado == tema.COLOR_EXITO:
                color_estado = tema.COLOR_ADVERTENCIA

        if problemas:
            self.lbl_estado.configure(text=f"⚠️ {len(problemas)} alerta(s) temprana(s)", text_color=color_estado)
            self.lbl_subestado.configure(text=" | ".join(problemas), text_color=tema.COLOR_TEXTO_SECUNDARIO)
            self.btn_prevenir.configure(state="normal")
        else:
            self.lbl_estado.configure(text="✓ Tendencia estable", text_color=tema.COLOR_EXITO)
            self.lbl_subestado.configure(text="No se detectan cuellos de botella próximos.", text_color=tema.COLOR_TEXTO_TERCIARIO)
            self.btn_prevenir.configure(state="disabled")

    def _prevenir(self):
        self._log("Ejecutando acción preventiva Anti-Freeze...")
        threading.Thread(target=self._prevenir_hilo, daemon=True).start()

    def _prevenir_hilo(self):
        try:
            ram_antes = leer_metricas_memoria()["ram_pct"]
            jaulas = self.optimizer.activar_jaulas_jerarquicas()
            if jaulas:
                self._log(f"✓ {jaulas} procesos pesados puestos en jaula.")
            ok = self.optimizer.force_memory_purge(agresiva=False)
            if ok:
                if self.sentinel:
                    self.sentinel.registrar_purga()
                ram_nueva = leer_metricas_memoria()["ram_pct"]
                self._log(f"✓ Memoria estabilizada: {ram_antes:.1f}% → {ram_nueva:.1f}%")
            else:
                self._log("⚠ Purga parcial (algunas rutas requieren admin/root).")
            self.after(0, lambda: self.winfo_exists() and self._actualizar_ahora())
        except Exception as e:
            self._log(f"Error en prevención: {e}")
