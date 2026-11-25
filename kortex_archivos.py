"""Shim de compatibilidad hacia kortex_core.files."""

from kortex_core.config import SISTEMA, es_admin
from kortex_core.files import KortexArchivos
from kortex_core.platform_hal import ejecutar_elevado as ejecutar_como_admin

__all__ = ["KortexArchivos", "SISTEMA", "es_admin", "ejecutar_como_admin"]
