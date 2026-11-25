"""Kortex Nexus v2.0 — Suite Anti-Freeze para hardware de bajos recursos.

Soporta modo daemon ultraligero (`--daemon`, sin cargar Tk/CustomTkinter)
y modo GUI bajo demanda multiplataforma (Windows + todas las distros Linux).
"""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import signal
import sys
import threading
import time

import psutil

from kortex_core.config import (
    SISTEMA,
    KortexConfig,
    es_admin,
    es_congelado,
    obtener_dir_recursos,
    obtener_disco_principal,
)

# En builds PyInstaller windowed (console=False) stdout/stderr pueden ser None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
from kortex_core.cryo import CryoEngine
from kortex_core.modes import ModeManager
from kortex_core.optimizer import KernelOptimizer
from kortex_core.platform_hal import leer_metricas_memoria, leer_presion_memoria
from kortex_core.predictor import KortexPredictor
from kortex_core.sentinel import KortexSentinel


def _preguntar_admin_windows() -> bool:
    try:
        resultado = ctypes.windll.user32.MessageBoxW(
            0,
            "Kortex puede optimizar al 100% con permisos de administrador.\n\n"
            "Permite:\n"
            "• Compresión y purga de memoria\n"
            "• Aceleración TCP/red global\n"
            "• Limpieza de rutas del sistema\n\n"
            "¿Reiniciar Kortex como administrador?",
            "Kortex Nexus — Permisos",
            0x04 | 0x20,
        )
        return resultado == 6
    except Exception:
        return False


def _relanzar_admin_windows() -> bool:
    args = [a for a in sys.argv[1:] if a != "--no-admin-prompt"]
    try:
        import subprocess

        if es_congelado():
            params = subprocess.list2cmdline(args)
        else:
            script = os.path.abspath(sys.argv[0])
            params = subprocess.list2cmdline([script] + args)
        res = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        if int(res) > 32:
            return True
    except Exception as e:
        print(f"[Kortex] No se pudo elevar privilegios: {e}")
    return False


def ejecutar_daemon(test_seconds: float | None = None):
    """Modo daemon sin UI (<20 MB RAM): solo telemetría, Auto-Cryo y protección anti-freeze."""
    config = KortexConfig()
    cryo = CryoEngine()
    optimizer = KernelOptimizer(cryo=cryo)
    predictor = KortexPredictor()
    sentinel = KortexSentinel(config=config, optimizer=optimizer, cryo=cryo, predictor=predictor)

    optimizer.proteger_proceso(es_daemon=True)
    if optimizer.es_root:
        optimizer.activar_expansion_memoria()

    detener_ev = threading.Event()

    def _parar(_sig, _frame):
        detener_ev.set()

    signal.signal(signal.SIGINT, _parar)
    signal.signal(signal.SIGTERM, _parar)

    sentinel.iniciar()
    print(f"[Kortex Daemon] Activo | OS: {SISTEMA} | Perfil: {optimizer.perfil['nombre']}")

    try:
        if test_seconds is not None and test_seconds > 0:
            detener_ev.wait(timeout=test_seconds)
        else:
            while not detener_ev.is_set():
                detener_ev.wait(timeout=1.0)
    finally:
        sentinel.detener()
        cryo.descongelar_todo()
        print("[Kortex Daemon] Detenido limpiamente.")


def ejecutar_gui():
    """Arranca la interfaz CustomTkinter compartiendo instancias con kortex_core."""
    import customtkinter as ctk

    from cerebro import CerebroKortex
    from kortex_core.files import KortexArchivos
    from kortex_ui import componentes, notificaciones, tema
    from kortex_ui.sidebar import Sidebar
    from kortex_ui.tabs.ajustes import TabAjustes
    from kortex_ui.tabs.archivos import TabArchivos
    from kortex_ui.tabs.cerebro import TabCerebro
    from kortex_ui.tabs.launcher import TabLauncher
    from kortex_ui.tabs.legal import TabLegal
    from kortex_ui.tabs.modos import TabModos
    from kortex_ui.tabs.monitor import TabMonitor
    from kortex_ui.tabs.notas import TabNotas
    from kortex_ui.tabs.prediccion import TabPrediccion

    class AplicacionKortex(ctk.CTk):
        def __init__(self):
            super().__init__()

            self.es_admin = es_admin()
            self.config = KortexConfig()
            self.cryo = CryoEngine()
            self.optimizer = KernelOptimizer(cryo=self.cryo)
            self.predictor = KortexPredictor()
            self.modes = ModeManager(config=self.config, optimizer=self.optimizer, cryo=self.cryo)
            self.archivos = KortexArchivos()
            self.cerebro = CerebroKortex(
                config=self.config, optimizer=self.optimizer, cryo=self.cryo, modes=self.modes
            )
            self.sentinel = KortexSentinel(
                config=self.config,
                optimizer=self.optimizer,
                cryo=self.cryo,
                predictor=self.predictor,
                on_log=lambda m: print(f"[Centinela] {m}"),
            )

            self._pestanas_cacheadas: dict[str, ctk.CTkFrame] = {}
            self.pestana_actual: str | None = None
            self._tarjetas_home: dict[str, dict] = {}
            self._home_after_id = None
            self._lbl_estado_home = None

            self.title("Kortex Nexus")
            rec = obtener_dir_recursos()
            if SISTEMA == "Windows":
                try:
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KortexNexus.App.2.0")
                except Exception:
                    pass
                icono = rec / "icon.ico"
                if icono.exists():
                    try:
                        self.iconbitmap(str(icono))
                        self.after(150, lambda p=str(icono): self._aplicar_icono_win32_hd(p))
                    except Exception:
                        pass
            else:
                logo_png = rec / "logo_kortex.png"
                if logo_png.exists():
                    try:
                        import tkinter as tk

                        self._icon_tk = tk.PhotoImage(file=str(logo_png))
                        self.wm_iconphoto(True, self._icon_tk)
                    except Exception:
                        pass
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            ancho = min(tema.VENTANA_ANCHO, max(tema.VENTANA_MIN_ANCHO, sw - 60))
            alto = min(tema.VENTANA_ALTO, max(tema.VENTANA_MIN_ALTO, sh - 80))
            self.geometry(f"{ancho}x{alto}")
            self.minsize(tema.VENTANA_MIN_ANCHO, tema.VENTANA_MIN_ALTO)
            self.configure(fg_color=tema.COLOR_FONDO)

            self._construir_layout()
            self.after(200, lambda: notificaciones.inicializar(self))
            self.protocol("WM_DELETE_WINDOW", self._al_cerrar)
            self.after(600, self._iniciar_sentinel)

        def _aplicar_icono_win32_hd(self, ruta_ico: str):
            """Carga ICON_BIG (48px) e ICON_SMALL (16px) vía Win32 para nitidez nativa en la barra de tareas."""
            try:
                user32 = ctypes.windll.user32
                hwnd = user32.GetParent(self.winfo_id()) or self.winfo_id()
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                WM_SETICON = 0x0080
                h_big = user32.LoadImageW(None, ruta_ico, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                h_small = user32.LoadImageW(None, ruta_ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                if h_big:
                    user32.SendMessageW(hwnd, WM_SETICON, 1, h_big)
                if h_small:
                    user32.SendMessageW(hwnd, WM_SETICON, 0, h_small)
            except Exception:
                pass

        def _construir_layout(self):
            self.sidebar = Sidebar(self, al_cambiar_pestana=self._cambiar_pestana)
            self.sidebar.pack(side="left", fill="y")

            self.contenido = ctk.CTkFrame(self, fg_color=tema.COLOR_FONDO, corner_radius=0)
            self.contenido.pack(side="right", fill="both", expand=True)

            self._cambiar_pestana("home")

        def _iniciar_sentinel(self):
            try:
                self.sentinel.iniciar()
            except Exception as e:
                print(f"[Kortex] Error iniciando centinela: {e}")

        def _al_cerrar(self):
            try:
                self._pausar_home()
                for tab in self._pestanas_cacheadas.values():
                    if hasattr(tab, "al_ocultar"):
                        tab.al_ocultar()
                self.sentinel.detener()
                if self.modes.modo_activo:
                    self.modes.desactivar()
                self.cryo.descongelar_todo()
            except Exception:
                pass
            try:
                self.destroy()
            except Exception:
                pass

        def _cambiar_pestana(self, clave: str):
            if self.pestana_actual == clave:
                return

            if self.pestana_actual:
                if self.pestana_actual == "home":
                    self._pausar_home()
                anterior = self._pestanas_cacheadas.get(self.pestana_actual)
                if anterior is not None:
                    if hasattr(anterior, "al_ocultar"):
                        anterior.al_ocultar()
                    anterior.pack_forget()

            if clave not in self._pestanas_cacheadas:
                tab = self._crear_pestana(clave)
                if tab is None:
                    return
                self._pestanas_cacheadas[clave] = tab

            actual = self._pestanas_cacheadas[clave]
            actual.pack(fill="both", expand=True)
            self.pestana_actual = clave
            self.sidebar.seleccionar_externo(clave)

            if clave == "home":
                self._reanudar_home()
            elif hasattr(actual, "al_mostrar"):
                actual.al_mostrar()

        def _crear_pestana(self, clave: str):
            try:
                if clave == "home":
                    return self._construir_home()
                if clave == "monitor":
                    return TabMonitor(
                        self.contenido,
                        config=self.config, optimizer=self.optimizer,
                        cryo=self.cryo, sentinel=self.sentinel,
                    )
                if clave == "modos":
                    return TabModos(self.contenido, modes=self.modes)
                if clave == "archivos":
                    return TabArchivos(self.contenido, gestor=self.archivos)
                if clave == "cerebro":
                    return TabCerebro(self.contenido, cerebro=self.cerebro)
                if clave == "notas":
                    return TabNotas(self.contenido)
                if clave == "prediccion":
                    return TabPrediccion(
                        self.contenido,
                        predictor=self.predictor, optimizer=self.optimizer, sentinel=self.sentinel,
                    )
                if clave == "launcher":
                    return TabLauncher(self.contenido)
                if clave == "ajustes":
                    return TabAjustes(self.contenido, config=self.config, optimizer=self.optimizer)
                if clave == "legal":
                    return TabLegal(self.contenido)
            except Exception as e:
                print(f"[Kortex] Error creando pestaña '{clave}': {e}")
            return None

        def _construir_home(self) -> ctk.CTkFrame:
            contenedor = ctk.CTkFrame(self.contenido, fg_color="transparent")
            contenedor.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=tema.ESP_XL)

            header = ctk.CTkFrame(contenedor, fg_color="transparent")
            header.pack(fill="x", pady=(0, tema.ESP_LG))

            ctk.CTkLabel(
                header, text="Inicio",
                font=(tema.FUENTE_TITULO, tema.TAMANO_H1),
                text_color=tema.COLOR_TEXTO, anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                header,
                text=f"Perfil {self.optimizer.perfil['nombre']} · {self.optimizer.ram_total_mb} MB RAM.",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
                text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
            ).pack(anchor="w", pady=(tema.ESP_XS, 0))

            if not self.es_admin:
                aviso = ctk.CTkFrame(
                    contenedor, fg_color="#3A2A00", corner_radius=tema.RADIO_MD,
                    border_width=1, border_color=tema.COLOR_ADVERTENCIA,
                )
                aviso.pack(fill="x", pady=(0, tema.ESP_MD))
                ctk.CTkLabel(
                    aviso,
                    text="Modo estándar: monitoreo, suspensión inteligente y limpieza de usuario activos. "
                         "Los ajustes de kernel y temporales del sistema requieren permisos de administrador.",
                    font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
                    text_color=tema.COLOR_ADVERTENCIA, anchor="w", justify="left", wraplength=740,
                ).pack(padx=tema.ESP_LG, pady=tema.ESP_SM)

            tarjetas = ctk.CTkFrame(contenedor, fg_color="transparent")
            tarjetas.pack(fill="x", pady=(0, tema.ESP_LG))
            tarjetas.grid_columnconfigure((0, 1, 2), weight=1, uniform="card")

            self._tarjeta_metrica(tarjetas, 0, "ram", "RAM", tema.COLOR_INFO)
            self._tarjeta_metrica(tarjetas, 1, "cpu", "CPU", tema.COLOR_ERROR)
            self._tarjeta_metrica(tarjetas, 2, "disco", "Disco", tema.COLOR_ADVERTENCIA)

            acciones = ctk.CTkFrame(contenedor, fg_color="transparent")
            acciones.pack(fill="x", pady=(0, tema.ESP_LG))

            ctk.CTkButton(
                acciones, text="Abrir Monitor",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_NAV, "bold"),
                fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
                text_color=tema.COLOR_TEXTO, corner_radius=tema.RADIO_MD, height=42, width=180,
                command=lambda: self._cambiar_pestana("monitor"),
            ).pack(side="left", padx=(0, tema.ESP_SM))

            ctk.CTkButton(
                acciones, text="Configurar Modos",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO, "bold"),
                fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE_FUERTE,
                hover_color=tema.COLOR_ELEVADO_HOVER,
                text_color=tema.COLOR_TEXTO, corner_radius=tema.RADIO_MD, height=42, width=180,
                command=lambda: self._cambiar_pestana("modos"),
            ).pack(side="left")

            ctk.CTkLabel(
                contenedor, text="Estado del sistema",
                font=(tema.FUENTE_TITULO, tema.TAMANO_H2),
                text_color=tema.COLOR_TEXTO, anchor="w",
            ).pack(anchor="w", pady=(0, tema.ESP_SM))

            card = componentes.Card(contenedor)
            card.pack(fill="x")

            self._lbl_estado_home = ctk.CTkLabel(
                card,
                text="Analizando memoria y presión del sistema...",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
                text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w", justify="left",
            )
            self._lbl_estado_home.pack(padx=tema.ESP_XL, pady=tema.ESP_LG, anchor="w")
            return contenedor

        def _tarjeta_metrica(self, padre, columna: int, clave: str, titulo: str, color: str):
            card = componentes.Card(padre)
            card.grid(row=0, column=columna, padx=(0, tema.ESP_MD) if columna < 2 else (0, 0), sticky="nsew")

            ctk.CTkLabel(
                card, text=titulo,
                font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
                text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
            ).pack(anchor="w", padx=tema.ESP_XL, pady=(tema.ESP_LG, 0))

            valor = ctk.CTkLabel(card, text="—", font=(tema.FUENTE_TITULO, 28), text_color=color, anchor="w")
            valor.pack(anchor="w", padx=tema.ESP_XL, pady=(tema.ESP_XS, tema.ESP_SM))

            barra = ctk.CTkProgressBar(
                card, progress_color=color, fg_color=tema.COLOR_BORDE,
                height=8, corner_radius=tema.RADIO_SM,
            )
            barra.pack(fill="x", padx=tema.ESP_XL, pady=(0, tema.ESP_LG))
            barra.set(0)

            self._tarjetas_home[clave] = {"valor": valor, "barra": barra}

        def _pausar_home(self):
            if self._home_after_id is not None:
                try:
                    self.after_cancel(self._home_after_id)
                except Exception:
                    pass
                self._home_after_id = None

        def _reanudar_home(self):
            self._pausar_home()
            self._home_after_id = self.after(100, self._actualizar_metricas_home)

        def _actualizar_metricas_home(self):
            if self.pestana_actual != "home" or not self.winfo_exists():
                self._home_after_id = None
                return

            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = leer_metricas_memoria()
                presion = leer_presion_memoria()

                try:
                    disco = shutil.disk_usage(obtener_disco_principal())
                    disco_pct = round((disco.used / disco.total) * 100, 1)
                except Exception:
                    disco_pct = 0.0

                if "cpu" in self._tarjetas_home:
                    self._tarjetas_home["cpu"]["valor"].configure(text=f"{cpu:.1f}%")
                    self._tarjetas_home["cpu"]["barra"].set(min(1.0, max(0.0, cpu / 100.0)))

                if "ram" in self._tarjetas_home:
                    self._tarjetas_home["ram"]["valor"].configure(text=f"{mem['ram_pct']:.1f}%")
                    self._tarjetas_home["ram"]["barra"].set(min(1.0, max(0.0, mem["ram_pct"] / 100.0)))

                if "disco" in self._tarjetas_home:
                    self._tarjetas_home["disco"]["valor"].configure(text=f"{disco_pct:.1f}%")
                    self._tarjetas_home["disco"]["barra"].set(min(1.0, max(0.0, disco_pct / 100.0)))

                if self._lbl_estado_home and self._lbl_estado_home.winfo_exists():
                    estado = self.sentinel.estado_vivo()
                    n_congelados = len(estado.get("congelados", []))
                    self._lbl_estado_home.configure(
                        text=(
                            f"• Presión: {presion['nivel'].upper()} ({mem['ram_disponible_mb']:.0f} MB libres)\n"
                            f"• Auto-Cryo: {'Activo' if estado.get('auto_cryo') else 'Pausado'} "
                            f"({n_congelados} proceso(s) congelado(s))\n"
                            f"• Muestras en predictor: {estado.get('muestras_predictor', 0)} · "
                            f"Modo activo: {self.modes.modo_activo or 'Ninguno'}"
                        )
                    )
            except Exception:
                pass

            self._home_after_id = self.after(2000, self._actualizar_metricas_home)

    def _signal_handler(_sig, _frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    app = AplicacionKortex()
    app.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Kortex Nexus v2.0 — Optimizador Anti-Freeze")
    parser.add_argument("--daemon", action="store_true", help="Ejecuta solo el daemon ligero sin interfaz gráfica")
    parser.add_argument("--install", action="store_true", help="Abre el asistente gráfico de instalación")
    parser.add_argument("--no-admin-prompt", action="store_true", help="No preguntar por elevación UAC al iniciar")
    parser.add_argument("--test-seconds", type=float, default=None, help="Duración máxima para pruebas de daemon")
    parser.add_argument("--clean-admin", nargs="+", default=None, help="Limpia rutas elevadas y termina")
    args = parser.parse_args()

    if args.clean_admin:
        from kortex_core.files import KortexArchivos

        KortexArchivos()._limpiar_como_admin_interno(args.clean_admin)
        return

    if args.install:
        from kortex_ui.installer_wizard import ejecutar_instalador_gui

        ejecutar_instalador_gui()
        return

    if args.daemon:
        ejecutar_daemon(test_seconds=args.test_seconds)
        return

    if SISTEMA == "Windows" and not args.no_admin_prompt and not es_admin():
        if _preguntar_admin_windows() and _relanzar_admin_windows():
            return

    ejecutar_gui()


if __name__ == "__main__":
    main()
