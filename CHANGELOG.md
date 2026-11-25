# Changelog

## v2.0.0 — 2026-11-25
- Nueva arquitectura modular `kortex_core/` desacoplada de la interfaz gráfica.
- Modo `--daemon` ligero sin cargar `customtkinter`.
- Medición real de RAM (`mem.available`) y presión de memoria (`PSI` en Linux).
- Motor de suspensión inteligente por foco (`CryoEngine`) con restauración garantizada al cerrar.
- ZRAM adaptativo (`zstd`/`lz4`), TCP BBR/CTCP moderno y purga segura sin thrashing en HDD.
- Predictor estadístico en tiempo real (EWMA + regresión temporal) sin `pandas` ni `scikit-learn`.
- Modos reales y reversibles (`Supervivencia`, `Gaming`, `Streaming`, `Trabajo`).
- Papelera interna segura con `manifest.json` y soporte de apps multi-distro (`dpkg`, `pacman`, `rpm`, `apk`, `flatpak`) y Windows (`HKLM`/`HKCU`).
- Asistente gráfico de instalación para Windows, instalador universal para Linux (systemd y SysVinit/autostart), logo HD e iconos vectoriales alineados.
- Suite de pruebas funcionales y de seguridad (`tests/test_kortex_core.py` y `tests/test_security.py`).
