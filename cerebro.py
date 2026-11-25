"""Cerebro de Kortex Nexus (orquestador local 100% offline)."""

from __future__ import annotations

import json
from pathlib import Path

from kortex_comandos import detectar_comando, ejecutar_comando
from kortex_contexto import obtener_contexto
from kortex_core.config import KortexConfig, obtener_carpeta_boveda
from kortex_core.cryo import CryoEngine
from kortex_core.modes import ModeManager
from kortex_core.optimizer import KernelOptimizer
from kortex_experto import responder as responder_experto


class CerebroKortex:
    """Cerebro local de Kortex: comandos reales + sistema experto + contexto del SO."""

    def __init__(
        self,
        config: KortexConfig | None = None,
        optimizer: KernelOptimizer | None = None,
        cryo: CryoEngine | None = None,
        modes: ModeManager | None = None,
    ):
        self.config = config or KortexConfig()
        self.cryo = cryo or CryoEngine()
        self.optimizer = optimizer or KernelOptimizer(cryo=self.cryo)
        self.modes = modes or ModeManager(config=self.config, optimizer=self.optimizer, cryo=self.cryo)
        self.historial: list[dict[str, str]] = []
        self._ruta_historial: Path = obtener_carpeta_boveda() / "chat_historial.json"
        self.system_prompt = (
            "Eres Kortex Nexus, asistente técnico Anti-Freeze para optimización de PCs "
            "de bajos recursos. Respondes en español, directo y con acciones reales."
        )
        self._cargar_historial_disco()

    def _cargar_historial_disco(self):
        if not self.config.get("guardar_historial_chat", True):
            return
        if self._ruta_historial.exists():
            try:
                data = json.loads(self._ruta_historial.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.historial = data[-20:]
            except Exception:
                self.historial = []

    def pensar(self, mensaje: str) -> str:
        if not mensaje or not mensaje.strip():
            return "No recibí ningún mensaje. ¿Puedes repetirlo?"

        mensaje = mensaje.strip()
        self._guardar_historial("user", mensaje)

        try:
            contexto = obtener_contexto()
        except Exception:
            contexto = {}

        comando = detectar_comando(mensaje)
        if comando:
            try:
                respuesta = ejecutar_comando(
                    comando,
                    mensaje,
                    contexto,
                    optimizer=self.optimizer,
                    cryo=self.cryo,
                    modes=self.modes,
                )
            except Exception as e:
                respuesta = f"Error ejecutando comando: {e}"
            self._guardar_historial("assistant", respuesta)
            return respuesta

        try:
            respuesta = responder_experto(mensaje, contexto)
        except Exception as e:
            respuesta = f"Error en el sistema experto: {e}"

        self._guardar_historial("assistant", respuesta)
        return respuesta

    def pensar_en_vivo(self, mensaje: str):
        respuesta = self.pensar(mensaje)
        for char in respuesta:
            yield char

    def _guardar_historial(self, rol: str, contenido: str):
        self.historial.append({"rol": rol, "contenido": contenido})
        if len(self.historial) > 20:
            self.historial = self.historial[-20:]

        if self.config.get("guardar_historial_chat", True):
            try:
                self._ruta_historial.parent.mkdir(parents=True, exist_ok=True)
                self._ruta_historial.write_text(
                    json.dumps(self.historial, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def limpiar_historial(self):
        self.historial = []
        if self._ruta_historial.exists():
            try:
                self._ruta_historial.unlink()
            except Exception:
                pass

    def estado(self) -> dict:
        from kortex_comandos import COMANDOS

        return {
            "modo": "local",
            "historial_entradas": len(self.historial),
            "comandos_disponibles": len(COMANDOS),
        }
