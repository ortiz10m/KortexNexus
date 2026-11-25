"""Configuración persistente, rutas de bóveda, privilegios y autostart."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


SISTEMA = platform.system()
SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def es_congelado() -> bool:
    """True cuando Kortex corre empaquetado como binario standalone (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def obtener_dir_recursos() -> Path:
    """Directorio de recursos internos (iconos, fuentes) en fuente o PyInstaller."""
    meipass = getattr(sys, "_MEIPASS", None)
    if es_congelado() and meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent.parent


def obtener_dir_app() -> Path:
    """Directorio donde reside la instalación/ejecutable principal."""
    if es_congelado():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

DEFAULT_CONFIG: dict[str, Any] = {
    "guardar_historial_chat": True,
    "recolectar_datos": True,
    "auto_inicio": False,
    "auto_cryo_activo": True,
    "auto_cryo_idle_seg": 150,
    "auto_cryo_ram_umbral_pct": 78.0,
    "modo_activo": None,
}


def obtener_home_usuario_real() -> Path:
    """Resuelve el home del usuario real incluso si corre bajo sudo/root en POSIX."""
    if os.name != "nt":
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            try:
                import pwd

                return Path(pwd.getpwnam(sudo_user).pw_dir)
            except Exception:
                pass

        home_env = os.environ.get("HOME")
        if home_env and home_env != "/root":
            return Path(home_env)

        if hasattr(os, "geteuid") and os.geteuid() == 0:
            try:
                home_root = Path("/home")
                if home_root.exists():
                    for usuario in sorted(home_root.iterdir()):
                        if usuario.is_dir():
                            return usuario
            except Exception:
                pass

    return Path.home()


def obtener_carpeta_boveda() -> Path:
    """Devuelve ~/.kortex_nexus del usuario real con permisos restrictivos (0700 en POSIX)."""
    carpeta = obtener_home_usuario_real() / ".kortex_nexus"
    carpeta.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(carpeta, 0o700)
        except OSError:
            pass
    return carpeta


def es_admin() -> bool:
    """Detecta privilegios de administrador/root de forma segura cross-platform."""
    try:
        if SISTEMA == "Windows":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        if hasattr(os, "geteuid"):
            return os.geteuid() == 0
    except Exception:
        return False
    return False


def obtener_disco_principal() -> str:
    """Devuelve la raíz del volumen principal del sistema operativo."""
    if SISTEMA == "Windows":
        drive = os.environ.get("SystemDrive", "C:").rstrip("\\/")
        return f"{drive}\\"
    return "/"


class KortexConfig:
    """Gestor thread-safe y atómico para ~/.kortex_nexus/config.json."""

    def __init__(self, ruta_archivo: Path | None = None):
        self._lock = threading.RLock()
        if ruta_archivo is None:
            self.ruta = obtener_carpeta_boveda() / "config.json"
        else:
            self.ruta = Path(ruta_archivo)
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._datos: dict[str, Any] = dict(DEFAULT_CONFIG)
        self.cargar()

    def cargar(self) -> dict[str, Any]:
        """Carga la configuración desde disco fusionando con valores por defecto."""
        with self._lock:
            datos = dict(DEFAULT_CONFIG)
            if self.ruta.exists():
                try:
                    contenido = json.loads(self.ruta.read_text(encoding="utf-8"))
                    if isinstance(contenido, dict):
                        for clave, valor in contenido.items():
                            datos[clave] = valor
                except Exception:
                    pass
            self._datos = datos
            return dict(self._datos)

    def guardar(self) -> bool:
        """Persiste la configuración de manera atómica."""
        with self._lock:
            try:
                self.ruta.parent.mkdir(parents=True, exist_ok=True)
                temporal = self.ruta.with_suffix(".json.tmp")
                temporal.write_text(
                    json.dumps(self._datos, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                os.replace(temporal, self.ruta)
                return True
            except Exception:
                return False

    def get(self, clave: str, default: Any = None) -> Any:
        with self._lock:
            return self._datos.get(clave, DEFAULT_CONFIG.get(clave, default))

    def set(self, clave: str, valor: Any, guardar: bool = True) -> bool:
        with self._lock:
            self._datos[clave] = valor
            if guardar:
                return self.guardar()
            return True

    def actualizar(self, cambios: dict[str, Any], guardar: bool = True) -> bool:
        with self._lock:
            self._datos.update(cambios)
            if guardar:
                return self.guardar()
            return True

    def como_dict(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._datos)


def configurar_autostart(activar: bool, main_path: Path | None = None) -> tuple[bool, str]:
    """Configura el auto-inicio del daemon ligero de Kortex en Windows y Linux."""
    if es_congelado():
        cmd_daemon = f'"{sys.executable}" --daemon'
    else:
        if main_path is None:
            main_path = Path(__file__).resolve().parent.parent / "main.py"
        cmd_daemon = f'"{sys.executable}" "{main_path}" --daemon'

    if SISTEMA == "Windows":
        try:
            import winreg

            clave_run = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                clave_run,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_READ,
            ) as key:
                if activar:
                    winreg.SetValueEx(key, "KortexNexus", 0, winreg.REG_SZ, cmd_daemon)
                    return True, "Auto-inicio registrado en el arranque de Windows."
                try:
                    winreg.DeleteValue(key, "KortexNexus")
                except FileNotFoundError:
                    pass
                return True, "Auto-inicio desactivado en Windows."
        except Exception as e:
            return False, f"No se pudo configurar auto-inicio en Windows: {e}"

    if SISTEMA == "Linux":
        try:
            autostart_dir = obtener_home_usuario_real() / ".config" / "autostart"
            desktop_file = autostart_dir / "kortex-nexus.desktop"
            if activar:
                autostart_dir.mkdir(parents=True, exist_ok=True)
                contenido = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=Kortex Nexus Daemon\n"
                    "Comment=Monitor y optimizador Anti-Freeze de Kortex Nexus\n"
                    f"Exec={cmd_daemon}\n"
                    "Terminal=false\n"
                    "X-GNOME-Autostart-enabled=true\n"
                )
                desktop_file.write_text(contenido, encoding="utf-8")
                return True, f"Auto-inicio configurado en {desktop_file}"
            if desktop_file.exists():
                desktop_file.unlink()
            return True, "Auto-inicio desactivado en Linux."
        except Exception as e:
            return False, f"No se pudo configurar auto-inicio en Linux: {e}"

    return False, f"Auto-inicio no soportado en {SISTEMA}."
