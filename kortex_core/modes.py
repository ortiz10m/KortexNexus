"""Gestor de Modos reales y reversibles de Kortex Nexus."""

from __future__ import annotations

import threading
from typing import Any, Callable

import psutil

from kortex_core.config import SISTEMA, KortexConfig
from kortex_core.cryo import CryoEngine, normalizar_nombre_proceso
from kortex_core.optimizer import KernelOptimizer


MODOS_INFO: dict[str, dict[str, str]] = {
    "supervivencia": {
        "titulo": "Supervivencia (1-2 GB)",
        "descripcion": "Compresión de memoria, suspensión de apps inactivas y límites a procesos pesados.",
        "color": "#FF6B00",
    },
    "gaming": {
        "titulo": "Gaming",
        "descripcion": "Prioriza red (BBR/CTCP), rendimiento de CPU y suspende indexadores en segundo plano.",
        "color": "#EF4444",
    },
    "streaming": {
        "titulo": "Streaming",
        "descripcion": "Optimiza estabilidad de red, prioriza OBS/Streamlabs y limita procesos de fondo.",
        "color": "#3B82F6",
    },
    "trabajo": {
        "titulo": "Trabajo",
        "descripcion": "Auto-suspensión equilibrada preservando editores, IDE y apps de videollamada.",
        "color": "#10B981",
    },
}


class ModeManager:
    """Aplica y revierte perfiles reales del sistema operativo."""

    def __init__(
        self,
        config: KortexConfig | None = None,
        optimizer: KernelOptimizer | None = None,
        cryo: CryoEngine | None = None,
    ):
        self.config = config or KortexConfig()
        self.cryo = cryo or CryoEngine()
        self.optimizer = optimizer or KernelOptimizer(cryo=self.cryo)
        self._lock = threading.RLock()
        self.modo_activo: str | None = None
        self._backup_config: dict[str, Any] = {}
        self._prioridades_elevadas: dict[int, int] = {}

    def activar(self, clave: str, on_paso: Callable[[str], None] | None = None) -> dict[str, Any]:
        """Activa un modo real revirtiendo primero cualquier modo previo."""
        if clave not in MODOS_INFO:
            return {"success": False, "message": f"Modo desconocido: {clave}", "pasos": []}

        log_paso = on_paso or (lambda _: None)

        with self._lock:
            if self.modo_activo:
                self.desactivar(on_paso=log_paso)

            self._backup_config = {
                "auto_cryo_activo": self.config.get("auto_cryo_activo"),
                "auto_cryo_idle_seg": self.config.get("auto_cryo_idle_seg"),
                "auto_cryo_ram_umbral_pct": self.config.get("auto_cryo_ram_umbral_pct"),
            }

            pasos: list[str] = []

            if clave == "supervivencia":
                self.config.actualizar({
                    "auto_cryo_activo": True,
                    "auto_cryo_idle_seg": 60,
                    "auto_cryo_ram_umbral_pct": 70.0,
                    "modo_activo": clave,
                })
                pasos.append("Auto-Cryo agresivo activado (umbral 70%, 60s inactividad)")
                log_paso(pasos[-1])

                if self.optimizer.activar_expansion_memoria():
                    pasos.append("Compresión / expansión de memoria aplicada")
                    log_paso(pasos[-1])

                hf = self.cryo.activar_hyper_focus()
                pasos.append(hf["message"])
                log_paso(pasos[-1])

                jaulas = self.optimizer.activar_jaulas_jerarquicas(umbral_ram_pct=4.0)
                pasos.append(f"Jaulas jerárquicas: {jaulas} procesos pesados limitados")
                log_paso(pasos[-1])

            elif clave == "gaming":
                if self.optimizer.acelerar_internet():
                    pasos.append("Aceleración de red (BBR/CTCP) activada")
                    log_paso(pasos[-1])

                if self.optimizer.set_cpu_governor("performance"):
                    pasos.append("CPU ajustada a rendimiento máximo")
                    log_paso(pasos[-1])

                hf = self.cryo.activar_hyper_focus()
                pasos.append(hf["message"])
                log_paso(pasos[-1])

                jaulas = self.optimizer.activar_jaulas_jerarquicas(umbral_ram_pct=5.0)
                pasos.append(f"Procesos pesados en 2º plano limitados ({jaulas})")
                log_paso(pasos[-1])
                self.config.set("modo_activo", clave)

            elif clave == "streaming":
                if self.optimizer.acelerar_internet():
                    pasos.append("Congestión TCP optimizada para estabilidad de subida")
                    log_paso(pasos[-1])

                elevados = self._elevar_apps({"obs", "obs64", "streamlabs", "ffmpeg"})
                pasos.append(f"Apps de streaming priorizadas: {elevados}")
                log_paso(pasos[-1])

                jaulas = self.optimizer.activar_jaulas_jerarquicas(
                    umbral_ram_pct=5.0,
                    excluir_nombres={"obs", "obs64", "streamlabs", "ffmpeg"},
                )
                pasos.append(f"Procesos de fondo limitados: {jaulas}")
                log_paso(pasos[-1])
                self.config.set("modo_activo", clave)

            elif clave == "trabajo":
                self.config.actualizar({
                    "auto_cryo_activo": True,
                    "auto_cryo_idle_seg": 120,
                    "auto_cryo_ram_umbral_pct": 75.0,
                    "modo_activo": clave,
                })
                pasos.append("Auto-Cryo equilibrado activado (umbral 75%, 120s)")
                log_paso(pasos[-1])

                herramientas_trabajo = {"code", "pycharm", "idea", "obsidian", "notion", "zoom", "teams", "slack"}
                jaulas = self.optimizer.activar_jaulas_jerarquicas(
                    umbral_ram_pct=5.0,
                    excluir_nombres=herramientas_trabajo,
                )
                pasos.append(f"Apps no esenciales limitadas ({jaulas}) preservando herramientas de trabajo")
                log_paso(pasos[-1])

            self.modo_activo = clave
            return {
                "success": True,
                "modo": clave,
                "pasos": pasos,
                "message": f"Modo {clave} activado ({len(pasos)} ajustes reales).",
            }

    def desactivar(self, on_paso: Callable[[str], None] | None = None) -> dict[str, Any]:
        """Revierte prioridades, bloatware suspendido y configuración temporal del modo."""
        log_paso = on_paso or (lambda _: None)
        with self._lock:
            anterior = self.modo_activo
            pasos: list[str] = []

            hf = self.cryo.revertir_hyper_focus()
            if hf.get("reactivados") or hf.get("restaurados"):
                pasos.append(hf["message"])
                log_paso(pasos[-1])

            rest_jaulas = self.optimizer.revertir_jaulas()
            if rest_jaulas:
                pasos.append(f"Jaulas revertidas ({rest_jaulas} procesos restaurados)")
                log_paso(pasos[-1])

            rest_elev = self._restaurar_elevados()
            if rest_elev:
                pasos.append(f"Prioridades elevadas restauradas ({rest_elev})")
                log_paso(pasos[-1])

            if anterior == "gaming":
                if self.optimizer.set_cpu_governor("auto"):
                    pasos.append("Governor/plan de energía devuelto a automático")
                    log_paso(pasos[-1])

            if self._backup_config:
                self.config.actualizar(self._backup_config, guardar=False)
                self._backup_config.clear()

            self.config.set("modo_activo", None)
            self.modo_activo = None
            return {
                "success": True,
                "modo_anterior": anterior,
                "pasos": pasos,
                "message": f"Modo {anterior or ''} desactivado y estado restaurado.",
            }

    def _elevar_apps(self, nombres: set[str]) -> int:
        count = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                norm = normalizar_nombre_proceso(proc.info.get("name") or "")
                if norm not in nombres:
                    continue
                pid = proc.info["pid"]
                if pid not in self._prioridades_elevadas:
                    self._prioridades_elevadas[pid] = proc.nice()
                if SISTEMA == "Windows":
                    proc.nice(psutil.HIGH_PRIORITY_CLASS)
                else:
                    proc.nice(-5)
                count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
                continue
        return count

    def _restaurar_elevados(self) -> int:
        count = 0
        for pid, orig in list(self._prioridades_elevadas.items()):
            try:
                psutil.Process(pid).nice(orig)
                count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
                pass
        self._prioridades_elevadas.clear()
        return count
