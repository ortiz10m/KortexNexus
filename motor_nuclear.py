"""Shim de compatibilidad hacia kortex_core.optimizer y kortex_core.cryo."""

from __future__ import annotations

import os
from typing import Any

from kortex_core.config import SISTEMA
from kortex_core.cryo import CryoEngine
from kortex_core.optimizer import KernelOptimizer


class KortexDaemon:
    """Adaptador compatible que delega en KernelOptimizer + CryoEngine."""

    def __init__(self, optimizer: KernelOptimizer | None = None, cryo: CryoEngine | None = None):
        self.os_type = SISTEMA
        self.mi_pid = os.getpid()
        self.cryo = cryo or CryoEngine()
        self.optimizer = optimizer or KernelOptimizer(cryo=self.cryo)

    def activar_inmortalidad(self) -> bool:
        return self.optimizer.proteger_proceso(es_daemon=False)

    def activar_expansion_memoria(self) -> bool:
        return self.optimizer.activar_expansion_memoria()

    def activar_jaulas_jerarquicas(self, objetivos: list | None = None) -> bool:
        self.optimizer.activar_jaulas_jerarquicas()
        return True

    def set_cpu_governor(self, modo: str = "auto") -> bool:
        return self.optimizer.set_cpu_governor(modo)

    def activar_hyper_focus_windows(self) -> dict[str, Any]:
        return self.cryo.activar_hyper_focus()

    def revertir_hyper_focus_windows(self) -> dict[str, Any]:
        return self.cryo.revertir_hyper_focus()

    def criogenizar_proceso(self, nombre_objetivo: str) -> dict[str, Any]:
        return self.cryo.criogenizar_proceso(nombre_objetivo)

    def descongelar_proceso(self, nombre_objetivo: str) -> dict[str, Any]:
        return self.cryo.descongelar_proceso(nombre_objetivo)

    def activar_purga_predictiva(self) -> bool:
        return True
