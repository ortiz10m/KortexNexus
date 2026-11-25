"""Predictor estadístico ligero (0 dependencias externas, <1 MB RAM).

Usa ventana deslizante con timestamps reales, suavizado EWMA y regresión lineal
ponderada para proyectar RAM y CPU a 5, 15 y 30 minutos y estimar TTC.
"""

from __future__ import annotations

import csv
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

from kortex_core.config import obtener_carpeta_boveda
from kortex_core.platform_hal import leer_metricas_memoria


MAX_MUESTRAS = 180


class KortexPredictor:
    """Predictor en vivo basado en tendencias temporales reales sin pandas/sklearn."""

    def __init__(self, archivo_csv: Path | None = None):
        self._lock = threading.RLock()
        self.archivo_csv = archivo_csv or (obtener_carpeta_boveda() / "kortex_datos.csv")
        self._muestras: deque[dict[str, float]] = deque(maxlen=MAX_MUESTRAS)
        self.cargar_historial()

    def cargar_historial(self) -> int:
        """Carga las últimas muestras desde kortex_datos.csv usando solo stdlib."""
        if not self.archivo_csv.exists():
            return 0
        cargadas = 0
        try:
            with self._lock:
                with open(self.archivo_csv, "r", encoding="utf-8") as f:
                    filas = list(csv.DictReader(f))[-MAX_MUESTRAS:]
                self._muestras.clear()
                for fila in filas:
                    try:
                        ts_str = fila.get("timestamp", "")
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp() if ts_str else time.time()
                        ram = float(fila.get("ram_pct", 0.0))
                        cpu = float(fila.get("cpu_pct", 0.0))
                        swap = float(fila.get("swap_pct", 0.0))
                        self._muestras.append({"ts": ts, "ram": ram, "cpu": cpu, "swap": swap})
                        cargadas += 1
                    except (ValueError, TypeError):
                        continue
        except Exception:
            return 0
        return cargadas

    def registrar_muestra(self, ram_pct: float, cpu_pct: float, swap_pct: float = 0.0, ts: float | None = None):
        """Añade una observación en vivo a la ventana deslizante."""
        with self._lock:
            self._muestras.append({
                "ts": float(ts if ts is not None else time.time()),
                "ram": float(ram_pct),
                "cpu": float(cpu_pct),
                "swap": float(swap_pct),
            })

    @property
    def total_muestras(self) -> int:
        with self._lock:
            return len(self._muestras)

    @property
    def disponible(self) -> bool:
        """True desde que haya al menos 3 muestras válidas."""
        return self.total_muestras >= 3

    @property
    def precision(self) -> float:
        """Nivel de confianza del modelo según cobertura de muestras recientes (0-100)."""
        n = self.total_muestras
        if n < 3:
            return 0.0
        # Satura cerca del 95% al tener ~60+ muestras (~20-30 min de historia)
        return round(min(95.0, 55.0 + (min(n, 60) / 60.0) * 40.0), 1)

    def recargar_si_actualizado(self) -> bool:
        """Compatibilidad con versión anterior; recarga desde CSV si está vacío."""
        if self.total_muestras < 3 and self.archivo_csv.exists():
            return self.cargar_historial() >= 3
        return False

    def _regresion_ponderada(self, clave: str, valor_actual: float) -> tuple[float, float]:
        """Calcula (nivel_suavizado, pendiente_por_minuto) usando timestamps reales."""
        with self._lock:
            muestras = list(self._muestras)

        if len(muestras) < 3:
            return float(valor_actual), 0.0

        # Usar los últimos 30 puntos como máximo para capturar tendencia reciente sin ruido viejo
        ventana = muestras[-30:]
        t_fin = ventana[-1]["ts"]
        span_seg = t_fin - ventana[0]["ts"]
        if span_seg < 5.0:
            return float(valor_actual), 0.0

        # EWMA para suavizar picos momentáneos (alpha=0.35)
        ewma = ventana[0][clave]
        for m in ventana[1:]:
            ewma = 0.35 * m[clave] + 0.65 * ewma

        # Regresión lineal ponderada (más peso a muestras recientes) sobre tiempo en minutos
        xs: list[float] = []
        ys: list[float] = []
        ws: list[float] = []
        n = len(ventana)
        for idx, m in enumerate(ventana):
            x_min = (m["ts"] - t_fin) / 60.0  # negativo hasta 0
            xs.append(x_min)
            ys.append(m[clave])
            ws.append(1.0 + (idx / max(1, n - 1)))  # peso 1.0 -> 2.0

        sum_w = sum(ws)
        mean_x = sum(w * x for w, x in zip(ws, xs)) / sum_w
        mean_y = sum(w * y for w, y in zip(ws, ys)) / sum_w

        num = sum(w * (x - mean_x) * (y - mean_y) for w, x, y in zip(ws, xs, ys))
        den = sum(w * ((x - mean_x) ** 2) for w, x in zip(ws, xs))
        pendiente = (num / den) if den > 1e-9 else 0.0

        # Amortiguar pendientes extremas para evitar proyecciones absurdas por picos de 10s
        pendiente = max(-6.0, min(6.0, pendiente))
        base = 0.6 * valor_actual + 0.4 * ewma
        return base, pendiente

    def predecir_serie(self, clave: str, valor_actual: float) -> dict[str, Any]:
        """Proyecta una métrica a 5, 15 y 30 minutos con amortiguación temporal."""
        base, pendiente_min = self._regresion_ponderada(clave, valor_actual)

        def _proyectar(minutos: float) -> float:
            # Amortiguación suave en horizontes largos para evitar extrapolación lineal infinita
            factor = minutos if minutos <= 5 else (5.0 + (minutos - 5.0) * 0.65)
            val = base + pendiente_min * factor
            return round(max(0.0, min(100.0, val)), 1)

        ttc_min: float | None = None
        if pendiente_min > 0.05 and valor_actual < 90.0:
            ttc_min = round((90.0 - valor_actual) / pendiente_min, 1)

        return {
            "actual": round(valor_actual, 1),
            "5": _proyectar(5.0),
            "15": _proyectar(15.0),
            "30": _proyectar(30.0),
            "tendencia_min": round(pendiente_min, 2),
            "ttc_90_min": ttc_min,
        }

    def predecir_horizonte(
        self,
        ram_actual: float | None = None,
        cpu_actual: float | None = None,
    ) -> dict[str, Any]:
        """Retorna el reporte completo de predicción para RAM y CPU."""
        if ram_actual is None:
            ram_actual = leer_metricas_memoria()["ram_pct"]
        if cpu_actual is None:
            import psutil

            cpu_actual = psutil.cpu_percent(interval=None)

        ram_pred = self.predecir_serie("ram", float(ram_actual))
        cpu_pred = self.predecir_serie("cpu", float(cpu_actual))
        return {
            "ram": ram_pred,
            "cpu": cpu_pred,
            "muestras": self.total_muestras,
            "confianza_pct": self.precision,
            "motor": "EWMA + Regresión Temporal",
        }

    def predecir_ram_futura(self) -> float | None:
        """Retorna la RAM proyectada a 5 minutos (compatible con API previa)."""
        if not self.disponible:
            return None
        ram_actual = leer_metricas_memoria()["ram_pct"]
        return self.predecir_serie("ram", ram_actual)["5"]
