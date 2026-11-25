"""Contexto del sistema para Kortex Nexus (conectado a kortex_core)."""

from __future__ import annotations

import shutil
from datetime import datetime

import psutil

from kortex_core.config import SISTEMA, obtener_disco_principal
from kortex_core.platform_hal import (
    leer_metricas_memoria,
    leer_presion_memoria,
    obtener_temperatura_cpu,
)


NAVEGADORES_CONOCIDOS = {
    "thorium", "thorium.exe",
    "chrome", "chrome.exe", "google-chrome",
    "chromium", "chromium.exe",
    "firefox", "firefox.exe",
    "brave", "brave.exe", "brave-browser",
    "opera", "opera.exe", "opera_gx",
    "edge", "msedge.exe",
    "vivaldi", "vivaldi.exe",
    "epiphany", "falkon",
}


def obtener_contexto() -> dict:
    """Recolecta el estado completo y preciso del sistema."""
    return {
        "sistema_operativo": SISTEMA,
        "hora": datetime.now().strftime("%H:%M"),
        "ram": _info_ram(),
        "presion": leer_presion_memoria(),
        "cpu": _info_cpu(),
        "disco": _info_disco(),
        "procesos": _info_procesos(),
        "temperatura": obtener_temperatura_cpu(),
        "uptime": _info_uptime(),
    }


def _info_ram() -> dict:
    try:
        m = leer_metricas_memoria()
        return {
            "porcentaje": round(m["ram_pct"], 1),
            "total_gb": round(m["ram_total_mb"] / 1024, 2),
            "usado_gb": round(m["ram_usada_mb"] / 1024, 2),
            "libre_gb": round(m["ram_disponible_mb"] / 1024, 2),
            "swap_pct": round(m["swap_pct"], 1),
        }
    except Exception:
        return {"porcentaje": 0, "total_gb": 0, "usado_gb": 0, "libre_gb": 0, "swap_pct": 0}


def _info_cpu() -> dict:
    try:
        return {
            "porcentaje": round(psutil.cpu_percent(interval=0.2), 1),
            "nucleos_fisicos": psutil.cpu_count(logical=False) or 0,
            "nucleos_logicos": psutil.cpu_count(logical=True) or 0,
        }
    except Exception:
        return {"porcentaje": 0, "nucleos_fisicos": 0, "nucleos_logicos": 0}


def _info_disco() -> dict:
    try:
        uso = shutil.disk_usage(obtener_disco_principal())
        return {
            "porcentaje": round((uso.used / uso.total) * 100, 1),
            "total_gb": round(uso.total / (1024 ** 3), 1),
            "usado_gb": round(uso.used / (1024 ** 3), 1),
            "libre_gb": round(uso.free / (1024 ** 3), 1),
        }
    except Exception:
        return {"porcentaje": 0, "total_gb": 0, "usado_gb": 0, "libre_gb": 0}


def _info_procesos() -> dict:
    pesados = []
    navegadores = set()
    zombies = 0
    total = 0

    try:
        for proc in psutil.process_iter(["name", "memory_info", "status"]):
            try:
                total += 1
                nombre = proc.info.get("name") or ""
                nombre_lower = nombre.lower()
                if proc.info.get("status") == psutil.STATUS_ZOMBIE:
                    zombies += 1
                    continue
                if nombre_lower in NAVEGADORES_CONOCIDOS:
                    navegadores.add(nombre.split(".")[0].capitalize())
                mem_info = proc.info.get("memory_info")
                if mem_info:
                    uso_mb = mem_info.rss / (1024 * 1024)
                    if uso_mb >= 80:
                        pesados.append((nombre, round(uso_mb, 1)))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        pesados.sort(key=lambda x: x[1], reverse=True)
        pesados = pesados[:5]
    except Exception:
        pass

    return {
        "total": total,
        "zombies": zombies,
        "pesados": pesados,
        "navegadores": sorted(navegadores),
    }


def _info_uptime() -> str:
    try:
        segundos = int(datetime.now().timestamp() - psutil.boot_time())
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        return f"{horas}h {minutos}m"
    except Exception:
        return "desconocido"


def formatear_contexto(contexto: dict) -> str:
    ram = contexto["ram"]
    cpu = contexto["cpu"]
    disco = contexto["disco"]
    proc = contexto["procesos"]
    presion = contexto.get("presion", {})
    temp = contexto.get("temperatura")

    lineas = [
        "ESTADO ACTUAL DEL SISTEMA:",
        f"- Sistema operativo: {contexto['sistema_operativo']}",
        f"- Hora: {contexto['hora']}",
        f"- Uptime: {contexto['uptime']}",
        "",
        f"- RAM: {ram['porcentaje']}% ({ram['usado_gb']} GB de {ram['total_gb']} GB)",
        f"- Presión de memoria: {presion.get('nivel', 'desconocida')}",
        f"- CPU: {cpu['porcentaje']}% ({cpu['nucleos_fisicos']} núcleos físicos, {cpu['nucleos_logicos']} lógicos)",
        f"- Disco: {disco['porcentaje']}% usado ({disco['libre_gb']} GB libres de {disco['total_gb']} GB)",
    ]

    if temp is not None:
        lineas.append(f"- Temperatura CPU: {temp}°C")
    lineas.append(f"- Procesos activos: {proc['total']}")
    if proc["zombies"] > 0:
        lineas.append(f"- Procesos zombies: {proc['zombies']}")
    if proc["pesados"]:
        lineas.append("\nPROCESOS PESADOS (>80 MB):")
        for nombre, mb in proc["pesados"]:
            lineas.append(f"- {nombre}: {mb} MB")
    if proc["navegadores"]:
        lineas.append(f"\nNAVEGADORES ABIERTOS: {', '.join(proc['navegadores'])}")
    return "\n".join(lineas)
