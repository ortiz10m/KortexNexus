"""HAL (Hardware Abstraction Layer) universal para Windows y todas las distros Linux."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import psutil

from kortex_core.config import (
    SISTEMA,
    SUBPROCESS_FLAGS,
    es_admin,
    es_congelado,
    obtener_dir_app,
    obtener_home_usuario_real,
)


def leer_metricas_memoria() -> dict[str, float]:
    """Lee métricas reales de memoria usando mem.available / mem.percent (nunca mem.free)."""
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        total_mb = mem.total / (1024 * 1024)
        disponible_mb = mem.available / (1024 * 1024)
        usada_mb = max(0.0, total_mb - disponible_mb)
        return {
            "ram_pct": round(float(mem.percent), 2),
            "ram_total_mb": round(total_mb, 1),
            "ram_disponible_mb": round(disponible_mb, 1),
            "ram_usada_mb": round(usada_mb, 1),
            "swap_pct": round(float(swap.percent), 2),
            "swap_usado_mb": round(swap.used / (1024 * 1024), 1),
            "swap_total_mb": round(swap.total / (1024 * 1024), 1),
        }
    except Exception:
        return {
            "ram_pct": 0.0,
            "ram_total_mb": 0.0,
            "ram_disponible_mb": 0.0,
            "ram_usada_mb": 0.0,
            "swap_pct": 0.0,
            "swap_usado_mb": 0.0,
            "swap_total_mb": 0.0,
        }


def parsear_psi_memory(contenido: str) -> dict[str, Any]:
    """Parsea /proc/pressure/memory de Linux (some avg10 / full avg10)."""
    resultado: dict[str, Any] = {
        "psi_disponible": False,
        "psi_some_10": 0.0,
        "psi_full_10": 0.0,
    }
    if not contenido:
        return resultado

    encontrado = False
    for linea in contenido.splitlines():
        linea = linea.strip()
        if not (linea.startswith("some ") or linea.startswith("full ")):
            continue
        partes = linea.split()
        tipo = partes[0]
        for token in partes[1:]:
            if token.startswith("avg10="):
                try:
                    val = float(token.split("=", 1)[1])
                    if tipo == "some":
                        resultado["psi_some_10"] = round(val, 2)
                    elif tipo == "full":
                        resultado["psi_full_10"] = round(val, 2)
                    encontrado = True
                except ValueError:
                    pass
    resultado["psi_disponible"] = encontrado
    return resultado


def evaluar_nivel_presion(
    mem_info: dict[str, float],
    psi_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evalúa presión real de memoria combinando PSI, RAM disponible absoluta y Swap."""
    psi = psi_info or {"psi_disponible": False, "psi_some_10": 0.0, "psi_full_10": 0.0}
    ram_pct = float(mem_info.get("ram_pct", 0.0))
    ram_total_mb = float(mem_info.get("ram_total_mb", 0.0))
    ram_disp_mb = float(mem_info.get("ram_disponible_mb", 0.0))
    swap_pct = float(mem_info.get("swap_pct", 0.0))
    psi_some = float(psi.get("psi_some_10", 0.0))
    psi_full = float(psi.get("psi_full_10", 0.0))

    es_baja_ram = 0 < ram_total_mb <= 2560
    nivel = "baja"
    razon = "Memoria holgada"

    if (
        psi_full >= 10.0
        or (es_baja_ram and ram_disp_mb < 180)
        or ram_pct >= 92.0
        or swap_pct >= 85.0
    ):
        nivel = "critica"
        razon = "Presión crítica: riesgo inmediato de congelamiento"
    elif (
        psi_some >= 15.0
        or (es_baja_ram and ram_disp_mb < 350)
        or ram_pct >= 82.0
        or swap_pct >= 65.0
    ):
        nivel = "alta"
        razon = "Presión alta: conviene liberar o criogenizar apps inactivas"
    elif psi_some >= 5.0 or ram_pct >= 68.0 or swap_pct >= 40.0:
        nivel = "media"
        razon = "Carga moderada"

    return {
        "nivel": nivel,
        "razon": razon,
        "ram_pct": ram_pct,
        "ram_disponible_mb": ram_disp_mb,
        "ram_total_mb": ram_total_mb,
        "swap_pct": swap_pct,
        "psi_disponible": bool(psi.get("psi_disponible", False)),
        "psi_some_10": psi_some,
        "psi_full_10": psi_full,
    }


def leer_presion_memoria() -> dict[str, Any]:
    """Obtiene el diagnóstico de presión real del kernel/SO en este instante."""
    mem_info = leer_metricas_memoria()
    psi_info: dict[str, Any] | None = None
    if SISTEMA == "Linux":
        psi_path = Path("/proc/pressure/memory")
        if psi_path.exists():
            try:
                psi_info = parsear_psi_memory(psi_path.read_text(encoding="utf-8"))
            except Exception:
                psi_info = None
    return evaluar_nivel_presion(mem_info, psi_info)


def detectar_perfil_hardware(ram_total_mb: int | None = None) -> dict[str, Any]:
    """Calcula umbrales y parámetros de kernel óptimos según RAM física."""
    if ram_total_mb is None:
        ram_total_mb = int(psutil.virtual_memory().total // (1024 * 1024))

    if ram_total_mb <= 1536:
        zram_mb = max(512, ram_total_mb)
        return {
            "nombre": "ULTRA_LOW",
            "zram_mb": zram_mb,
            "zram_size": f"{zram_mb}M",
            "swappiness": 100,
            "dirty_background_ratio": 3,
            "dirty_ratio": 8,
            "intervalo_logger": 20,
            "auto_cryo_umbral": 72.0,
            "auto_cryo_idle": 90,
            "umbral_predictivo": 78.0,
            "umbral_reactivo": 85.0,
            "umbral_swap": 55.0,
            "cooldown": 45,
        }
    if ram_total_mb <= 2560:
        zram_mb = max(768, int(ram_total_mb * 0.75))
        return {
            "nombre": "LOW_END",
            "zram_mb": zram_mb,
            "zram_size": f"{zram_mb}M",
            "swappiness": 100,
            "dirty_background_ratio": 4,
            "dirty_ratio": 10,
            "intervalo_logger": 20,
            "auto_cryo_umbral": 78.0,
            "auto_cryo_idle": 150,
            "umbral_predictivo": 80.0,
            "umbral_reactivo": 87.0,
            "umbral_swap": 60.0,
            "cooldown": 60,
        }
    if ram_total_mb <= 4608:
        zram_mb = min(2048, max(1024, int(ram_total_mb * 0.5)))
        return {
            "nombre": "MID_LOW",
            "zram_mb": zram_mb,
            "zram_size": f"{zram_mb}M",
            "swappiness": 80,
            "dirty_background_ratio": 5,
            "dirty_ratio": 12,
            "intervalo_logger": 25,
            "auto_cryo_umbral": 82.0,
            "auto_cryo_idle": 240,
            "umbral_predictivo": 82.0,
            "umbral_reactivo": 89.0,
            "umbral_swap": 65.0,
            "cooldown": 90,
        }
    if ram_total_mb <= 8704:
        zram_mb = min(2048, int(ram_total_mb * 0.25))
        return {
            "nombre": "MID_HIGH",
            "zram_mb": zram_mb,
            "zram_size": f"{zram_mb}M",
            "swappiness": 60,
            "dirty_background_ratio": 8,
            "dirty_ratio": 15,
            "intervalo_logger": 30,
            "auto_cryo_umbral": 86.0,
            "auto_cryo_idle": 300,
            "umbral_predictivo": 85.0,
            "umbral_reactivo": 91.0,
            "umbral_swap": 75.0,
            "cooldown": 120,
        }

    return {
        "nombre": "HIGH_END",
        "zram_mb": 2048,
        "zram_size": "2048M",
        "swappiness": 20,
        "dirty_background_ratio": 10,
        "dirty_ratio": 20,
        "intervalo_logger": 30,
        "auto_cryo_umbral": 90.0,
        "auto_cryo_idle": 600,
        "umbral_predictivo": 88.0,
        "umbral_reactivo": 94.0,
        "umbral_swap": 80.0,
        "cooldown": 180,
    }


def detectar_tipo_disco() -> str:
    """Detecta si el almacenamiento principal es SSD o HDD en Linux y Windows."""
    if SISTEMA == "Linux":
        try:
            block_dir = Path("/sys/block")
            if block_dir.exists():
                for disco in sorted(block_dir.iterdir()):
                    nombre = disco.name
                    if any(nombre.startswith(p) for p in ("loop", "ram", "dm-", "zram", "sr")):
                        continue
                    rot_path = disco / "queue" / "rotational"
                    if rot_path.exists():
                        valor = rot_path.read_text(encoding="utf-8").strip()
                        return "HDD" if valor == "1" else "SSD"
        except Exception:
            pass
        return "UNKNOWN"

    if SISTEMA == "Windows":
        try:
            res = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-PhysicalDisk | Select-Object -First 1 -ExpandProperty MediaType",
                ],
                capture_output=True,
                text=True,
                timeout=4,
                creationflags=SUBPROCESS_FLAGS,
            )
            media = res.stdout.strip().upper()
            if "SSD" in media or "NVME" in media:
                return "SSD"
            if "HDD" in media:
                return "HDD"
        except Exception:
            pass
    return "UNKNOWN"


def detectar_modelo_cpu() -> str:
    """Devuelve el nombre del procesador sin bloquear el arranque."""
    try:
        if SISTEMA == "Windows":
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                valor, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                return str(valor).strip()[:50]

        if SISTEMA == "Linux":
            cpuinfo = Path("/proc/cpuinfo")
            if cpuinfo.exists():
                for linea in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if linea.lower().startswith(("model name", "hardware")):
                        return linea.split(":", 1)[1].strip()[:50]
    except Exception:
        pass
    return platform.processor()[:50] or "Desconocido"


def detectar_gpu() -> bool:
    """Detecta presencia de GPU en Windows y cualquier distro Linux."""
    try:
        if SISTEMA == "Linux":
            drm_dir = Path("/sys/class/drm")
            if drm_dir.exists():
                for entrada in drm_dir.iterdir():
                    if entrada.name.startswith("card") and "-" not in entrada.name:
                        return True
            if shutil.which("lspci"):
                res = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
                out = res.stdout.lower()
                return any(
                    k in out
                    for k in ("vga", "3d controller", "display controller", "nvidia", "radeon", "amd")
                )
        elif SISTEMA == "Windows":
            res = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object -First 1 -ExpandProperty Name",
                ],
                capture_output=True,
                text=True,
                timeout=4,
                creationflags=SUBPROCESS_FLAGS,
            )
            return bool(res.stdout.strip())
    except Exception:
        pass
    return False


def obtener_temperatura_cpu() -> float | None:
    """Lee temperatura CPU con fallback a /sys/class/thermal en Linux."""
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                for nombre in ("coretemp", "k10temp", "zenpower", "acpitz", "cpu_thermal"):
                    if nombre in temps and temps[nombre]:
                        return round(float(temps[nombre][0].current), 1)
                for entradas in temps.values():
                    if entradas:
                        return round(float(entradas[0].current), 1)
    except Exception:
        pass

    if SISTEMA == "Linux":
        try:
            for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")):
                raw = zone.read_text(encoding="utf-8").strip()
                if raw.isdigit():
                    val = int(raw)
                    temp = val / 1000.0 if val > 200 else float(val)
                    if 5.0 <= temp <= 125.0:
                        return round(temp, 1)
        except Exception:
            pass
    return None


def detectar_distro_linux() -> dict[str, Any]:
    """Detecta distribución Linux, gestores de paquetes disponibles y servidor gráfico."""
    info: dict[str, Any] = {
        "id": "unknown",
        "pretty_name": f"Linux {platform.release()}",
        "gestores": [],
        "sesion_grafica": "headless",
    }
    if SISTEMA != "Linux":
        return info

    os_release = Path("/etc/os-release")
    if os_release.exists():
        try:
            for linea in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                v = v.strip().strip('"')
                if k == "ID":
                    info["id"] = v.lower()
                elif k == "PRETTY_NAME":
                    info["pretty_name"] = v
        except Exception:
            pass

    gestores = []
    for candidato in ("dpkg-query", "apt", "pacman", "dnf", "rpm", "zypper", "apk", "flatpak", "snap"):
        if shutil.which(candidato):
            gestores.append(candidato)
    info["gestores"] = gestores

    if os.environ.get("WAYLAND_DISPLAY"):
        info["sesion_grafica"] = "wayland"
    elif os.environ.get("DISPLAY"):
        info["sesion_grafica"] = "x11"
    else:
        info["sesion_grafica"] = os.environ.get("XDG_SESSION_TYPE", "headless").lower()

    return info


def obtener_pid_ventana_activa() -> int | None:
    """Devuelve el PID de la ventana con foco actual si el entorno lo permite."""
    try:
        if SISTEMA == "Windows":
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return int(pid.value) if pid.value else None

        if SISTEMA == "Linux":
            if shutil.which("xdotool") and os.environ.get("DISPLAY"):
                res = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowpid"],
                    capture_output=True,
                    text=True,
                    timeout=1,
                )
                if res.returncode == 0 and res.stdout.strip().isdigit():
                    return int(res.stdout.strip())

            if shutil.which("xprop") and os.environ.get("DISPLAY"):
                root_res = subprocess.run(
                    ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                    capture_output=True,
                    text=True,
                    timeout=1,
                )
                if root_res.returncode == 0 and "0x" in root_res.stdout:
                    win_id = root_res.stdout.strip().split()[-1]
                    if win_id not in ("0x0", "0"):
                        pid_res = subprocess.run(
                            ["xprop", "-id", win_id, "_NET_WM_PID"],
                            capture_output=True,
                            text=True,
                            timeout=1,
                        )
                        if "=" in pid_res.stdout:
                            val = pid_res.stdout.split("=", 1)[1].strip()
                            if val.isdigit():
                                return int(val)

            if os.environ.get("WAYLAND_DISPLAY"):
                if shutil.which("hyprctl"):
                    res = subprocess.run(
                        ["hyprctl", "activewindow", "-j"],
                        capture_output=True,
                        text=True,
                        timeout=1,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        data = json.loads(res.stdout)
                        pid = data.get("pid")
                        return int(pid) if pid else None
                if shutil.which("swaymsg"):
                    res = subprocess.run(
                        ["swaymsg", "-t", "get_tree"],
                        capture_output=True,
                        text=True,
                        timeout=1,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        return _buscar_focused_sway(json.loads(res.stdout))
    except Exception:
        pass
    return None


def _buscar_focused_sway(nodo: dict[str, Any]) -> int | None:
    if nodo.get("focused") and nodo.get("pid"):
        return int(nodo["pid"])
    for hijo in nodo.get("nodes", []) + nodo.get("floating_nodes", []):
        encontrado = _buscar_focused_sway(hijo)
        if encontrado:
            return encontrado
    return None


def cpu_soporta_avx2() -> bool:
    """Comprueba si la CPU soporta instrucciones AVX2 (clave en PCs viejas de 1-2GB)."""
    try:
        if SISTEMA == "Windows":
            # PF_AVX2_INSTRUCTIONS_AVAILABLE = 40 (Windows 10+)
            return bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(40))
        if SISTEMA == "Linux":
            cpuinfo = Path("/proc/cpuinfo")
            if cpuinfo.exists():
                texto = cpuinfo.read_text(encoding="utf-8", errors="ignore").lower()
                return " avx2" in texto or "\tavx2" in texto
    except Exception:
        pass
    return True


def ejecutar_elevado(args_python: list[str]) -> bool:
    """Ejecuta `sys.executable` con argumentos elevados sin duplicar el binario."""
    if es_admin():
        try:
            res = subprocess.run(
                [sys.executable] + args_python,
                check=False,
                creationflags=SUBPROCESS_FLAGS,
            )
            return res.returncode == 0
        except Exception:
            return False

    if SISTEMA == "Windows":
        try:
            params = subprocess.list2cmdline(args_python)
            resultado = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                params,
                None,
                1,
            )
            return int(resultado) > 32
        except Exception:
            return False

    if SISTEMA == "Linux":
        elevador = shutil.which("pkexec") or shutil.which("sudo")
        if not elevador:
            return False
        try:
            res = subprocess.run([elevador, sys.executable] + args_python, check=False, timeout=120)
            return res.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    return False


def ejecutar_kortex_elevado(args_kortex: list[str]) -> bool:
    """Lanza el propio ejecutable de Kortex con privilegios elevados (compatible con PyInstaller y fuente)."""
    if es_congelado():
        return ejecutar_elevado(args_kortex)
    main_py = obtener_dir_app() / "main.py"
    return ejecutar_elevado([str(main_py)] + args_kortex)


def obtener_entorno_usuario_grafico() -> dict[str, str]:
    """Preserva variables reales de sesión gráfica (X11/Wayland) al lanzar apps desde sudo."""
    env = os.environ.copy()
    if SISTEMA == "Linux" and hasattr(os, "geteuid") and os.geteuid() == 0:
        home_real = str(obtener_home_usuario_real())
        env["HOME"] = home_real
        env.setdefault("DISPLAY", ":0")
        xauth = Path(home_real) / ".Xauthority"
        if xauth.exists() and "XAUTHORITY" not in env:
            env["XAUTHORITY"] = str(xauth)
        sudo_uid = os.environ.get("SUDO_UID")
        if sudo_uid and "XDG_RUNTIME_DIR" not in env:
            runtime_dir = Path(f"/run/user/{sudo_uid}")
            if runtime_dir.exists():
                env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    return env


def obtener_info_hardware() -> dict[str, Any]:
    """Snapshot completo del hardware y entorno del sistema."""
    mem = leer_metricas_memoria()
    perfil = detectar_perfil_hardware(int(mem["ram_total_mb"]))
    distro = detectar_distro_linux() if SISTEMA == "Linux" else {}
    return {
        "os": SISTEMA,
        "distro": distro.get("pretty_name", SISTEMA) if distro else f"Windows {platform.release()}",
        "sesion_grafica": distro.get("sesion_grafica", "win32") if distro else "win32",
        "ram_total_mb": int(mem["ram_total_mb"]),
        "ram_disponible_mb": mem["ram_disponible_mb"],
        "ram_pct": mem["ram_pct"],
        "perfil": perfil["nombre"],
        "tipo_disco": detectar_tipo_disco(),
        "nucleos_fisicos": psutil.cpu_count(logical=False) or 1,
        "nucleos_logicos": psutil.cpu_count(logical=True) or 1,
        "tiene_gpu": detectar_gpu(),
        "modelo_cpu": detectar_modelo_cpu(),
        "avx2": cpu_soporta_avx2(),
        "temperatura_cpu": obtener_temperatura_cpu(),
        "es_root": es_admin(),
    }
