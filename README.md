# Kortex Nexus v2.0

Optimizador y suite de mantenimiento de escritorio para equipos con recursos limitados (desde **1 GB – 2 GB de RAM**), compatible con **Windows (7/8/10/11)** y **todas las distribuciones de Linux** (Debian/Ubuntu, Loc-OS, Arch, Fedora, openSUSE, Alpine y Void — X11 y Wayland).

100% offline. Sin cuentas, sin telemetría y sin conexiones externas.

---

## Instalación rápida

### Linux (todas las distros — Debian, Ubuntu, Loc-OS, Arch, Fedora, openSUSE, Alpine, Void)
```bash
wget https://github.com/ortiz10m/KortexNexus/releases/download/v2.0.0/KortexNexus-v2.0.0-Linux.tar.gz
tar -xzf KortexNexus-v2.0.0-Linux.tar.gz
cd KortexNexus-v2.0.0-Linux
sudo ./install_linux.sh
```
*Instalación solo para tu usuario (sin `sudo`): ejecuta `./install_linux.sh`.*

Comandos disponibles tras instalar:
- `kortex-nexus` — abre la interfaz gráfica.
- `kortex-daemon` — ejecuta solo el servicio ligero en segundo plano (<20 MB RAM).

### Windows (7 / 8 / 10 / 11)
1. Descarga `KortexNexus-v2.0.0-Windows.zip` desde la sección [Releases](https://github.com/ortiz10m/KortexNexus/releases/tag/v2.0.0).
2. Descomprime la carpeta completa.
3. Ejecuta `install_windows.bat` para abrir el asistente gráfico de instalación (o abre directo `KortexNexus\KortexNexus.exe`).

---

## Características principales

- **Monitor real de memoria y presión:** mide RAM disponible real (`available`, no `free`), Swap/ZRAM y presión del kernel (`/proc/pressure/memory` PSI en Linux).
- **Suspensión inteligente por foco (Auto-Cryo):** detecta procesos pesados inactivos en segundo plano bajo presión de memoria, los suspende temporalmente y los reanuda al instante al volver a su ventana o al cerrar Kortex.
- **ZRAM y red real sin placebo:** configura ZRAM (`zstd`/`lz4`) + `vm.page-cluster=0` en Linux, evita `drop_caches=3` en discos HDD lentos, y optimiza congestión TCP (`BBR` en Linux / `Set-NetTCPSetting` en Windows).
- **Modos reversibles:** `Supervivencia (1-2 GB)`, `Gaming`, `Streaming` y `Trabajo`. Todas las prioridades y procesos se restauran al desactivar el modo o cerrar la aplicación.
- **Predicción en vivo sin dependencias pesadas:** proyección a 5, 15 y 30 minutos + tiempo estimado a saturación (TTC) usando EWMA y regresión temporal en Python puro (sin `pandas` ni `scikit-learn`).
- **Archivos y papelera recuperable:** escaneo de carpetas, limpieza de temporales multi-distro, duplicados por MD5, listado de apps (`HKLM`/`HKCU` en Windows; `dpkg`, `pacman`, `rpm`, `apk` y `flatpak` en Linux) y papelera interna con `manifest.json` y restauración exacta.
- **Modo servicio (`--daemon`):** corre en segundo plano sin importar la interfaz gráfica.

---

## Desarrollo y pruebas

```bash
python -m venv venv
# Windows: .\venv\Scripts\pip install -r requirements.txt
# Linux:   ./venv/bin/pip install -r requirements.txt

# Ejecutar pruebas funcionales y de seguridad (cero fugas de datos)
python -m unittest discover -s tests -v

# Generar paquetes de distribución (release/)
python packaging/build_releases.py
```

---

## Licencia y derechos de autor

**Copyright (c) 2026 David Santiago Ortiz Rincón. Todos los derechos reservados.**

Este software y su código fuente son propiedad intelectual exclusiva de su autor. El repositorio se publica con fines de auditoría de seguridad, transparencia y portafolio. Queda prohibida la copia, modificación, redistribución comercial o venta sin autorización previa y por escrito del autor.
