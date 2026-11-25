"""Shim de compatibilidad hacia kortex_core.sentinel."""

from __future__ import annotations

from kortex_core.sentinel import COLUMNAS, KortexSentinel


class KortexLogger:
    """Adaptador ligero sobre KortexSentinel para compatibilidad."""

    def __init__(self, sentinel: KortexSentinel | None = None):
        self._sentinel = sentinel or KortexSentinel()

    def iniciar(self):
        self._sentinel.iniciar()

    def detener(self):
        self._sentinel.detener()

    def registrar_purga(self):
        self._sentinel.registrar_purga()

    def contar_filas(self) -> int:
        return self._sentinel.contar_filas()

    def estado(self) -> dict:
        filas = self.contar_filas()
        return {
            "corriendo": self._sentinel._corriendo,
            "filas_registradas": filas,
            "intervalo_seg": self._sentinel.intervalo_logger,
            "listo_para_entrenar": filas >= 3,
            "archivo": str(self._sentinel.archivo_csv),
        }


__all__ = ["KortexLogger", "COLUMNAS"]
