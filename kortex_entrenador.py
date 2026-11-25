"""Herramienta CLI para inspeccionar el predictor estadístico en vivo de Kortex v2.0.

En Kortex Nexus v2.0 ya no se requiere instalar pandas ni scikit-learn;
KortexPredictor procesa la telemetría de forma incremental con 0 dependencias pesadas.
"""

from __future__ import annotations

from kortex_core.predictor import KortexPredictor


def entrenar_completo():
    predictor = KortexPredictor()
    cargadas = predictor.cargar_historial()
    horizonte = predictor.predecir_horizonte()
    ram = horizonte["ram"]
    print("=" * 60)
    print("  KORTEX NEXUS v2.0 — MOTOR PREDICTIVO EN VIVO")
    print("=" * 60)
    print(f"Muestras cargadas : {cargadas}")
    print(f"Confianza actual  : {horizonte['confianza_pct']}%")
    print(f"RAM actual / 5m   : {ram['actual']}% -> {ram['5']}% ({ram['tendencia_min']:+.2f}%/min)")
    if ram["ttc_90_min"] is not None:
        print(f"TTC a 90%         : {ram['ttc_90_min']} min")
    else:
        print("TTC a 90%         : Estable / sin riesgo inmediato")


if __name__ == "__main__":
    entrenar_completo()
