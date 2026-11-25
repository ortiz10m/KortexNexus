"""Shim de compatibilidad hacia kortex_core.sentinel."""

from __future__ import annotations

from kortex_core.sentinel import KortexSentinel


class KortexCentinela(KortexSentinel):
    """Alias compatible con firmas previas de KortexCentinela."""

    def __init__(self, predictor=None, optimizador=None, logger=None, on_log=None, on_modelo_cargado=None):
        super().__init__(
            optimizer=optimizador,
            predictor=predictor,
            on_log=on_log,
        )
        self.logger = logger
        self.on_modelo_cargado = on_modelo_cargado


__all__ = ["KortexCentinela", "KortexSentinel"]
