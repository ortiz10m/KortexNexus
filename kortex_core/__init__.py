"""Núcleo de Kortex Nexus v2.0 — Arquitectura Anti-Freeze multiplataforma."""

__version__ = "2.0.0"

from kortex_core.config import (
    SISTEMA,
    SUBPROCESS_FLAGS,
    DEFAULT_CONFIG,
    KortexConfig,
    configurar_autostart,
    es_admin,
    obtener_carpeta_boveda,
    obtener_disco_principal,
)

__all__ = [
    "__version__",
    "SISTEMA",
    "SUBPROCESS_FLAGS",
    "DEFAULT_CONFIG",
    "KortexConfig",
    "configurar_autostart",
    "es_admin",
    "obtener_carpeta_boveda",
    "obtener_disco_principal",
]
