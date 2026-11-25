"""Asistente gráfico de instalación de Kortex Nexus."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import customtkinter as ctk

from kortex_core.config import (
    SISTEMA,
    SUBPROCESS_FLAGS,
    configurar_autostart,
    es_congelado,
    obtener_dir_app,
    obtener_dir_recursos,
)
from kortex_ui import tema
from kortex_ui.tabs.legal import TEXTO_PRIVACIDAD, TEXTO_TERMINOS, VERSION


def _aplicar_icono_ventana(ventana: ctk.CTk):
    rec = obtener_dir_recursos()
    if SISTEMA == "Windows":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KortexNexus.Setup.2.0")
        except Exception:
            pass
        ico = rec / "icon.ico"
        if ico.exists():
            try:
                ventana.iconbitmap(str(ico))
                def _hd(p=str(ico)):
                    try:
                        user32 = ctypes.windll.user32
                        hwnd = user32.GetParent(ventana.winfo_id()) or ventana.winfo_id()
                        h_big = user32.LoadImageW(None, p, 1, 48, 48, 0x0010)
                        h_small = user32.LoadImageW(None, p, 1, 16, 16, 0x0010)
                        if h_big:
                            user32.SendMessageW(hwnd, 0x0080, 1, h_big)
                        if h_small:
                            user32.SendMessageW(hwnd, 0x0080, 0, h_small)
                    except Exception:
                        pass
                ventana.after(150, _hd)
            except Exception:
                pass
    else:
        png = rec / "logo_kortex.png"
        if png.exists():
            try:
                import tkinter as tk

                img = tk.PhotoImage(file=str(png))
                ventana.wm_iconphoto(True, img)
                ventana._icon_ref = img
            except Exception:
                pass


class KortexInstallerWizard(ctk.CTk):
    """Instalador nativo en 4 pasos con aceptación de términos y privacidad."""

    def __init__(self):
        super().__init__()
        self.title(f"Instalación de Kortex Nexus {VERSION}")
        self.geometry("640x500")
        self.resizable(False, False)
        self.configure(fg_color=tema.COLOR_FONDO)
        _aplicar_icono_ventana(self)

        self._paso_actual = 0
        self._instalando = False
        self._instalado = False

        local_app = os.environ.get("LOCALAPPDATA") or str(Path.home())
        self.var_destino = ctk.StringVar(value=str(Path(local_app) / "Programs" / "KortexNexus"))
        self.var_acepta = ctk.BooleanVar(value=False)
        self.var_escritorio = ctk.BooleanVar(value=True)
        self.var_menu_inicio = ctk.BooleanVar(value=True)
        self.var_autostart = ctk.BooleanVar(value=True)

        self._construir_chrome()
        self._mostrar_paso(0)

    def _cargar_logo(self, size: int = 64):
        ruta = obtener_dir_recursos() / "logo_kortex.png"
        if ruta.exists():
            try:
                from PIL import Image

                img = Image.open(ruta)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
            except Exception:
                return None
        return None

    def _construir_chrome(self):
        cabecera = ctk.CTkFrame(self, fg_color=tema.COLOR_SUPERFICIE, corner_radius=0, height=68)
        cabecera.pack(fill="x")
        cabecera.pack_propagate(False)

        self._logo_small = self._cargar_logo(36)
        if self._logo_small:
            ctk.CTkLabel(cabecera, text="", image=self._logo_small).pack(side="left", padx=(24, 12))

        titulos = ctk.CTkFrame(cabecera, fg_color="transparent")
        titulos.pack(side="left", pady=12)

        ctk.CTkLabel(
            titulos, text="Kortex Nexus",
            font=(tema.FUENTE_TITULO, 16), text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            titulos, text=f"Instalador · Versión {VERSION}",
            font=(tema.FUENTE_CUERPO, 11), text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
        ).pack(anchor="w")

        self.lbl_paso = ctk.CTkLabel(
            cabecera, text="1 / 4",
            font=(tema.FUENTE_MONO, 12), text_color=tema.COLOR_TEXTO_TERCIARIO,
        )
        self.lbl_paso.pack(side="right", padx=24)

        ctk.CTkFrame(self, fg_color=tema.COLOR_BORDE, height=1).pack(fill="x")

        self.cuerpo = ctk.CTkFrame(self, fg_color=tema.COLOR_FONDO, corner_radius=0)
        self.cuerpo.pack(fill="both", expand=True, padx=28, pady=22)

        ctk.CTkFrame(self, fg_color=tema.COLOR_BORDE, height=1).pack(fill="x")

        pie = ctk.CTkFrame(self, fg_color=tema.COLOR_SUPERFICIE, corner_radius=0, height=60)
        pie.pack(fill="x", side="bottom")
        pie.pack_propagate(False)

        self.btn_cancelar = ctk.CTkButton(
            pie, text="Cancelar", width=100, height=34,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE_FUERTE,
            hover_color=tema.COLOR_ELEVADO_HOVER, text_color=tema.COLOR_TEXTO_SECUNDARIO,
            command=self.destroy,
        )
        self.btn_cancelar.pack(side="left", padx=24, pady=13)

        self.btn_siguiente = ctk.CTkButton(
            pie, text="Siguiente", width=140, height=34,
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            font=(tema.FUENTE_CUERPO, 13, "bold"), text_color=tema.COLOR_TEXTO,
            command=self._siguiente,
        )
        self.btn_siguiente.pack(side="right", padx=(8, 24), pady=13)

        self.btn_atras = ctk.CTkButton(
            pie, text="Atrás", width=95, height=34,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE_FUERTE,
            hover_color=tema.COLOR_ELEVADO_HOVER, text_color=tema.COLOR_TEXTO,
            command=self._atras,
        )
        self.btn_atras.pack(side="right", pady=13)

    def _limpiar_cuerpo(self):
        for w in self.cuerpo.winfo_children():
            w.destroy()

    def _mostrar_paso(self, paso: int):
        self._paso_actual = paso
        self._limpiar_cuerpo()
        self.lbl_paso.configure(text=f"{paso + 1} / 4")

        if paso == 0:
            self._paso_bienvenida()
        elif paso == 1:
            self._paso_legal()
        elif paso == 2:
            self._paso_opciones()
        elif paso == 3:
            self._paso_progreso()

    def _paso_bienvenida(self):
        self.btn_atras.configure(state="disabled")
        self.btn_siguiente.configure(text="Siguiente", state="normal")

        self._logo_big = self._cargar_logo(88)
        if self._logo_big:
            ctk.CTkLabel(self.cuerpo, text="", image=self._logo_big).pack(pady=(18, 16))

        ctk.CTkLabel(
            self.cuerpo, text="Instalar Kortex Nexus",
            font=(tema.FUENTE_TITULO, 22), text_color=tema.COLOR_TEXTO,
        ).pack()

        ctk.CTkLabel(
            self.cuerpo,
            text=f"Este asistente instalará Kortex Nexus v{VERSION} en tu equipo.\n\n"
                 "Optimización local de memoria, procesos y almacenamiento\n"
                 "diseñada para equipos desde 1 GB de RAM. Sin conexión requerida.",
            font=(tema.FUENTE_CUERPO, 13), text_color=tema.COLOR_TEXTO_SECUNDARIO, justify="center",
        ).pack(pady=(10, 0))

    def _paso_legal(self):
        self.btn_atras.configure(state="normal")
        self.btn_siguiente.configure(
            text="Siguiente",
            state="normal" if self.var_acepta.get() else "disabled",
        )

        ctk.CTkLabel(
            self.cuerpo, text="Términos de uso y privacidad",
            font=(tema.FUENTE_TITULO, 16), text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        txt = ctk.CTkTextbox(
            self.cuerpo, font=(tema.FUENTE_CUERPO, 12),
            fg_color=tema.COLOR_SUPERFICIE, text_color=tema.COLOR_TEXTO,
            border_width=1, border_color=tema.COLOR_BORDE, wrap="word", height=240,
        )
        txt.pack(fill="both", expand=True)
        txt.insert("0.0", TEXTO_TERMINOS.strip() + "\n\n" + TEXTO_PRIVACIDAD.strip())
        txt.configure(state="disabled")

        ctk.CTkCheckBox(
            self.cuerpo,
            text="Acepto los términos de uso y la política de privacidad",
            variable=self.var_acepta,
            font=(tema.FUENTE_CUERPO, 12),
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            command=lambda: self.btn_siguiente.configure(
                state="normal" if self.var_acepta.get() else "disabled"
            ),
        ).pack(anchor="w", pady=(12, 0))

    def _paso_opciones(self):
        self.btn_atras.configure(state="normal")
        self.btn_siguiente.configure(text="Instalar", state="normal")

        ctk.CTkLabel(
            self.cuerpo, text="Opciones de instalación",
            font=(tema.FUENTE_TITULO, 16), text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(
            self.cuerpo, text="Carpeta de destino",
            font=(tema.FUENTE_CUERPO, 12), text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
        ).pack(anchor="w")

        ctk.CTkEntry(
            self.cuerpo, textvariable=self.var_destino, height=36,
            font=(tema.FUENTE_MONO, 12), fg_color=tema.COLOR_SUPERFICIE,
            border_color=tema.COLOR_BORDE, text_color=tema.COLOR_TEXTO,
        ).pack(fill="x", pady=(4, 18))

        card = ctk.CTkFrame(
            self.cuerpo, fg_color=tema.COLOR_SUPERFICIE, corner_radius=tema.RADIO_MD,
            border_width=1, border_color=tema.COLOR_BORDE,
        )
        card.pack(fill="x")

        for texto, var in (
            ("Crear acceso directo en el Escritorio", self.var_escritorio),
            ("Crear accesos directos en el Menú Inicio", self.var_menu_inicio),
            ("Iniciar servicio en segundo plano al encender Windows", self.var_autostart),
        ):
            ctk.CTkCheckBox(
                card, text=texto, variable=var,
                font=(tema.FUENTE_CUERPO, 12), fg_color=tema.COLOR_PRIMARIO,
                hover_color=tema.COLOR_PRIMARIO_HOVER,
            ).pack(anchor="w", padx=16, pady=10)

    def _paso_progreso(self):
        self.btn_atras.configure(state="disabled")
        self.btn_cancelar.configure(state="disabled")
        self.btn_siguiente.configure(text="Instalando...", state="disabled")

        self.lbl_prog = ctk.CTkLabel(
            self.cuerpo, text="Preparando archivos...",
            font=(tema.FUENTE_TITULO, 15), text_color=tema.COLOR_TEXTO, anchor="w",
        )
        self.lbl_prog.pack(anchor="w", pady=(4, 10))

        self.barra = ctk.CTkProgressBar(
            self.cuerpo, progress_color=tema.COLOR_PRIMARIO, fg_color=tema.COLOR_BORDE, height=10,
        )
        self.barra.pack(fill="x", pady=(0, 14))
        self.barra.set(0.05)

        self.log_box = ctk.CTkTextbox(
            self.cuerpo, font=(tema.FUENTE_MONO, 11),
            fg_color=tema.COLOR_SUPERFICIE, text_color=tema.COLOR_TEXTO_SECUNDARIO,
            border_width=1, border_color=tema.COLOR_BORDE, height=210,
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

        self._instalando = True
        threading.Thread(target=self._ejecutar_instalacion, daemon=True).start()

    def _log(self, msg: str, progreso: float | None = None):
        def _u():
            if not self.winfo_exists():
                return
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
            if progreso is not None:
                self.barra.set(progreso)
                self.lbl_prog.configure(text=msg)

        self.after(0, _u)

    def _ejecutar_instalacion(self):
        try:
            origen_dir = obtener_dir_app().resolve()
            destino_dir = Path(self.var_destino.get().strip()).resolve()
            exe_dest = destino_dir / "KortexNexus.exe"

            self._log(f"Carpeta destino: {destino_dir}", 0.15)

            if es_congelado() and origen_dir != destino_dir:
                self._log("Cerrando instancias anteriores...", 0.25)
                try:
                    import psutil

                    mi_pid = os.getpid()
                    for proc in psutil.process_iter(["pid", "name"]):
                        if proc.info["pid"] != mi_pid and (proc.info.get("name") or "").lower() == "kortexnexus.exe":
                            try:
                                proc.terminate()
                                proc.wait(timeout=3)
                            except Exception:
                                pass
                except Exception:
                    pass

                self._log("Copiando archivos del programa...", 0.45)
                destino_dir.mkdir(parents=True, exist_ok=True)
                for item in origen_dir.iterdir():
                    target = destino_dir / item.name
                    if item.is_dir():
                        if target.exists():
                            shutil.rmtree(target, ignore_errors=True)
                        shutil.copytree(item, target)
                    else:
                        shutil.copy2(item, target)

                uninst_src = origen_dir.parent / "uninstall_windows.bat"
                if uninst_src.exists():
                    shutil.copy2(uninst_src, destino_dir / "uninstall_windows.bat")
            else:
                exe_dest = Path(sys.executable) if es_congelado() else (origen_dir / "main.py")
                self._log("Usando directorio actual.", 0.45)

            self._log("Creando accesos directos...", 0.72)
            if SISTEMA == "Windows":
                self._crear_accesos_windows(destino_dir, exe_dest)

            if self.var_autostart.get():
                self._log("Configurando inicio automático del servicio...", 0.90)
                self._registrar_autostart_exe(exe_dest)

            self._log("Instalación completada.", 1.0)
            self._instalado = True
            self._exe_instalado = exe_dest

            def _fin():
                if not self.winfo_exists():
                    return
                self.btn_cancelar.configure(text="Cerrar", state="normal")
                self.btn_siguiente.configure(text="Abrir Kortex Nexus", state="normal")

            self.after(0, _fin)
        except Exception as e:
            self._log(f"Error durante la instalación: {e}", 1.0)
            self.after(0, lambda: self.winfo_exists() and self.btn_cancelar.configure(text="Cerrar", state="normal"))
        finally:
            self._instalando = False

    def _crear_accesos_windows(self, destino_dir: Path, exe_dest: Path):
        ico = destino_dir / "_internal" / "icon.ico"
        if not ico.exists():
            ico = destino_dir / "icon.ico"
        ico_str = str(ico) if ico.exists() else f"{exe_dest},0"

        comandos = ["$ws = New-Object -ComObject WScript.Shell;"]
        if self.var_escritorio.get():
            comandos.append(
                f"$d = [Environment]::GetFolderPath('Desktop'); "
                f"$s = $ws.CreateShortcut((Join-Path $d 'Kortex Nexus.lnk')); "
                f"$s.TargetPath = '{exe_dest}'; $s.WorkingDirectory = '{destino_dir}'; "
                f"$s.IconLocation = '{ico_str}'; $s.Description = 'Kortex Nexus'; $s.Save();"
            )
        if self.var_menu_inicio.get():
            comandos.append(
                f"$m = Join-Path ([Environment]::GetFolderPath('Programs')) 'Kortex Nexus'; "
                f"New-Item -ItemType Directory -Force -Path $m | Out-Null; "
                f"$s1 = $ws.CreateShortcut((Join-Path $m 'Kortex Nexus.lnk')); "
                f"$s1.TargetPath = '{exe_dest}'; $s1.WorkingDirectory = '{destino_dir}'; $s1.IconLocation = '{ico_str}'; $s1.Save(); "
                f"$s2 = $ws.CreateShortcut((Join-Path $m 'Kortex Daemon.lnk')); "
                f"$s2.TargetPath = '{exe_dest}'; $s2.Arguments = '--daemon'; $s2.WorkingDirectory = '{destino_dir}'; $s2.IconLocation = '{ico_str}'; $s2.Save();"
            )
            uninst = destino_dir / "uninstall_windows.bat"
            if uninst.exists():
                comandos.append(
                    f"$s3 = $ws.CreateShortcut((Join-Path $m 'Desinstalar Kortex Nexus.lnk')); "
                    f"$s3.TargetPath = '{uninst}'; $s3.WorkingDirectory = '{destino_dir}'; $s3.Save();"
                )

        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", " ".join(comandos)],
            capture_output=True, text=True, timeout=15, creationflags=SUBPROCESS_FLAGS,
        )

    def _registrar_autostart_exe(self, exe_dest: Path):
        if SISTEMA == "Windows" and exe_dest.suffix.lower() == ".exe":
            try:
                import winreg

                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE,
                ) as key:
                    winreg.SetValueEx(key, "KortexNexus", 0, winreg.REG_SZ, f'"{exe_dest}" --daemon')
                return
            except Exception:
                pass
        configurar_autostart(True)

    def _atras(self):
        if self._paso_actual > 0 and not self._instalando:
            self._mostrar_paso(self._paso_actual - 1)

    def _siguiente(self):
        if self._instalando:
            return
        if self._instalado:
            exe = getattr(self, "_exe_instalado", None)
            if exe and Path(exe).exists() and Path(exe).suffix.lower() == ".exe":
                subprocess.Popen([str(exe)], cwd=str(Path(exe).parent), creationflags=SUBPROCESS_FLAGS)
            self.destroy()
            return
        if self._paso_actual < 3:
            self._mostrar_paso(self._paso_actual + 1)


def ejecutar_instalador_gui():
    app = KortexInstallerWizard()
    app.mainloop()
