"""Carga de fuentes custom para Kortex Nexus.

Registra la fuente Lucide (iconos vectoriales) al iniciar la app
para que se vea consistente en Windows, Linux y macOS.
"""

import ctypes
import platform
from pathlib import Path


from kortex_core.config import obtener_dir_recursos


RUTA_LUCIDE = obtener_dir_recursos() / "kortex_ui" / "fuentes" / "Lucide.ttf"
FUENTE_LUCIDE = "Lucide"
FR_PRIVATE = 0x10


def cargar_fuente_lucide() -> bool:
    """Registra la fuente Lucide en el sistema en tiempo de ejecución.

    En Windows usa la API de GDI. En Linux y macOS se asume que
    la fuente ya está disponible vía fontconfig o el gestor del sistema.
    Devuelve True si la carga fue exitosa.
    """
    if not RUTA_LUCIDE.exists():
        print(f"[Fuentes] No se encontró Lucide.ttf en {RUTA_LUCIDE}")
        return False

    sistema = platform.system()

    if sistema == "Windows":
        try:
            resultado = ctypes.windll.gdi32.AddFontResourceExW(
                str(RUTA_LUCIDE),
                FR_PRIVATE,
                0,
            )
            if resultado:
                print(f"[Fuentes] Lucide cargada correctamente ({resultado} fuentes).")
                return True
            print("[Fuentes] Windows no pudo registrar Lucide.")
            return False
        except Exception as e:
            print(f"[Fuentes] Error cargando Lucide en Windows: {e}")
            return False

    if sistema in ("Linux", "Darwin"):
        print("[Fuentes] En Linux/macOS se asume Lucide disponible vía fontconfig.")
        return True

    return False