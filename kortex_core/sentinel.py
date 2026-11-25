"""Centinela y Logger unificado de Kortex Nexus."""

from __future__ import annotations

import csv
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import psutil

from kortex_core.config import KortexConfig, obtener_carpeta_boveda
from kortex_core.cryo import CryoEngine, normalizar_nombre_proceso
from kortex_core.optimizer import KernelOptimizer
from kortex_core.platform_hal import (
    detectar_perfil_hardware,
    leer_metricas_memoria,
    leer_presion_memoria,
)
from kortex_core.predictor import KortexPredictor


MAX_FILAS = 20160

LISTA_BLANCA_LOG = {
    "kortex", "python", "python3", "systemd", "systemd-journald",
    "kworker", "kthreadd", "ksoftirqd", "xorg", "bash", "sh",
    "dbus-daemon", "pulseaudio", "pipewire", "pipewire-pulse",
    "networkmanager", "wpa_supplicant", "sshd", "crond", "atd",
    "sudo", "login", "getty", "agetty", "lxsession", "openbox",
    "svchost", "system", "smss", "csrss", "winlogon", "services",
    "lsass", "dwm", "explorer", "taskhostw", "runtimebroker",
}

NAVEGADORES = {
    "thorium", "thorium-browser", "chrome", "google-chrome",
    "chromium", "firefox", "brave", "brave-browser", "epiphany", "msedge",
}

COLUMNAS = [
    "timestamp", "hora", "dia_semana",
    "ram_pct", "ram_libre_mb",
    "swap_pct", "swap_usado_mb",
    "cpu_pct", "load_avg_1m",
    "io_read_mb", "io_write_mb",
    "num_procesos", "total_procesos",
    "procesos_zombie", "navegador_activo",
    "procesos", "ram_pct_1min", "tendencia_ram", "evento",
]


class KortexSentinel:
    """Daemon único que recolecta telemetría, evalúa presión real y ejecuta Auto-Cryo."""

    TICK_RAPIDO_SEG = 5

    def __init__(
        self,
        config: KortexConfig | None = None,
        optimizer: KernelOptimizer | None = None,
        cryo: CryoEngine | None = None,
        predictor: KortexPredictor | None = None,
        on_log: Callable[[str], None] | None = None,
        archivo_csv: Path | None = None,
    ):
        self.config = config or KortexConfig()
        self.cryo = cryo or CryoEngine()
        self.optimizer = optimizer or KernelOptimizer(cryo=self.cryo)
        self.boveda = obtener_carpeta_boveda()
        self.archivo_csv = archivo_csv or (self.boveda / "kortex_datos.csv")
        self.predictor = predictor or KortexPredictor(archivo_csv=self.archivo_csv)
        self.on_log = on_log or (lambda msg: print(f"[Centinela] {msg}"))

        mem = leer_metricas_memoria()
        self.perfil = detectar_perfil_hardware(int(mem["ram_total_mb"]))
        self.intervalo_logger = int(self.perfil["intervalo_logger"])
        self.cooldown = int(self.perfil["cooldown"])

        self._lock = threading.RLock()
        self._corriendo = False
        self._hilo: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._historial_ram: list[float] = []
        self._io_anterior = self._leer_io_actual()
        self._ultimo_log_ts = 0.0
        self._ultima_purga_ts = 0.0
        self._ultimo_estado: dict[str, Any] = {}
        self._purgas_sesion = 0

        self._inicializar_csv()

    # --- Gestión CSV ---

    def _inicializar_csv(self):
        self.archivo_csv.parent.mkdir(parents=True, exist_ok=True)
        if not self.archivo_csv.exists():
            with open(self.archivo_csv, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=COLUMNAS).writeheader()
            return

        try:
            with open(self.archivo_csv, "r", encoding="utf-8") as f:
                cabecera = f.readline().strip().split(",")
            if "swap_pct" not in cabecera:
                backup = self.archivo_csv.with_name("kortex_datos_v1_backup.csv")
                self.archivo_csv.replace(backup)
                with open(self.archivo_csv, "w", newline="", encoding="utf-8") as f:
                    csv.DictWriter(f, fieldnames=COLUMNAS).writeheader()
            else:
                self._rotar_csv()
        except Exception:
            pass

    def _rotar_csv(self):
        try:
            with open(self.archivo_csv, "r", encoding="utf-8") as f:
                filas = f.readlines()
            if len(filas) > MAX_FILAS + 1:
                with open(self.archivo_csv, "w", encoding="utf-8") as f:
                    f.writelines([filas[0]] + filas[-MAX_FILAS:])
        except Exception:
            pass

    # --- Telemetría ---

    def _leer_io_actual(self) -> tuple[int, int]:
        try:
            io = psutil.disk_io_counters()
            return (io.read_bytes, io.write_bytes) if io else (0, 0)
        except Exception:
            return (0, 0)

    def _calcular_io_delta(self) -> tuple[float, float]:
        io_actual = self._leer_io_actual()
        read_delta = max(0, io_actual[0] - self._io_anterior[0]) / (1024 * 1024)
        write_delta = max(0, io_actual[1] - self._io_anterior[1]) / (1024 * 1024)
        self._io_anterior = io_actual
        return (round(read_delta, 2), round(write_delta, 2))

    def _obtener_procesos_pesados(self) -> tuple[int, str, int, int]:
        encontrados: list[str] = []
        vistos: set[str] = set()
        zombies = 0
        nav_activo = 0

        try:
            for proc in psutil.process_iter(["name", "memory_info", "status"]):
                try:
                    nombre = proc.info.get("name")
                    if not nombre:
                        continue
                    if proc.info.get("status") == psutil.STATUS_ZOMBIE:
                        zombies += 1
                        continue
                    norm = normalizar_nombre_proceso(nombre)
                    if norm in NAVEGADORES:
                        nav_activo = 1
                    if norm in LISTA_BLANCA_LOG:
                        continue
                    mem_info = proc.info.get("memory_info")
                    if mem_info and (mem_info.rss / (1024 * 1024)) >= 30 and norm not in vistos:
                        encontrados.append(norm)
                        vistos.add(norm)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        encontrados.sort()
        return len(encontrados), "|".join(encontrados[:10]), nav_activo, zombies

    def tomar_muestra(self, evento: str = "normal") -> dict[str, Any]:
        ahora = datetime.now()
        mem = leer_metricas_memoria()
        cpu_pct = round(float(psutil.cpu_percent(interval=None)), 2)

        try:
            load_avg = round(os.getloadavg()[0], 2)
        except (AttributeError, OSError):
            load_avg = 0.0

        io_read, io_write = self._calcular_io_delta()
        try:
            total_proc = len(psutil.pids())
        except Exception:
            total_proc = 0

        num_proc, proc_str, nav_activo, zombies = self._obtener_procesos_pesados()

        ram_pct = mem["ram_pct"]
        ram_1min = self._historial_ram[0] if self._historial_ram else ram_pct
        self._historial_ram.append(ram_pct)
        if len(self._historial_ram) > 3:
            self._historial_ram.pop(0)
        tendencia = (
            round(self._historial_ram[-1] - self._historial_ram[0], 2)
            if len(self._historial_ram) >= 2
            else 0.0
        )

        if evento == "normal":
            if mem["swap_pct"] >= 80:
                evento = "swap_critico"
            elif ram_pct >= 90:
                evento = "ram_critica"

        return {
            "timestamp": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "hora": ahora.hour,
            "dia_semana": ahora.weekday(),
            "ram_pct": ram_pct,
            "ram_libre_mb": mem["ram_disponible_mb"],
            "swap_pct": mem["swap_pct"],
            "swap_usado_mb": mem["swap_usado_mb"],
            "cpu_pct": cpu_pct,
            "load_avg_1m": load_avg,
            "io_read_mb": io_read,
            "io_write_mb": io_write,
            "num_procesos": num_proc,
            "total_procesos": total_proc,
            "procesos_zombie": zombies,
            "navegador_activo": nav_activo,
            "procesos": proc_str,
            "ram_pct_1min": round(ram_1min, 2),
            "tendencia_ram": tendencia,
            "evento": evento,
        }

    def _escribir_muestra_csv(self, muestra: dict[str, Any]):
        try:
            with open(self.archivo_csv, "a", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=COLUMNAS).writerow(muestra)
        except Exception as e:
            self.on_log(f"Error escribiendo CSV: {e}")

    def registrar_purga(self):
        muestra = self.tomar_muestra(evento="purga_ejecutada")
        if self.config.get("recolectar_datos", True):
            self._escribir_muestra_csv(muestra)
        self._purgas_sesion += 1

    # --- Ciclo principal ---

    def iniciar(self):
        if self._corriendo:
            return
        self._corriendo = True
        self._stop_event.clear()
        self.on_log(
            f"Perfil {self.perfil['nombre']} ({self.optimizer.ram_total_mb} MB) | "
            f"Muestreo {self.intervalo_logger}s | Auto-Cryo {self.config.get('auto_cryo_activo', True)}"
        )
        self._hilo = threading.Thread(target=self._bucle, daemon=True, name="KortexSentinel")
        self._hilo.start()

    def detener(self):
        self._corriendo = False
        self._stop_event.set()
        if self._hilo and self._hilo.is_alive():
            self._hilo.join(timeout=2.0)

    def _bucle(self):
        # Primera lectura inmediata para tener métricas vivas desde segundo 0
        try:
            self.ejecutar_ciclo_rapido(forzar_telemetria=True)
        except Exception:
            pass

        while self._corriendo and not self._stop_event.is_set():
            self._stop_event.wait(self.TICK_RAPIDO_SEG)
            if not self._corriendo:
                break
            try:
                self.ejecutar_ciclo_rapido()
            except Exception:
                pass

    def ejecutar_ciclo_rapido(self, forzar_telemetria: bool = False):
        ahora = time.time()
        presion = leer_presion_memoria()
        auto_cryo_on = bool(self.config.get("auto_cryo_activo", True))
        umbral_cryo = float(self.config.get("auto_cryo_ram_umbral_pct", self.perfil["auto_cryo_umbral"]))
        idle_seg = int(self.config.get("auto_cryo_idle_seg", self.perfil["auto_cryo_idle"]))

        # 1. Auto-Cryo siempre corre en ciclo rápido (5s) para descongelamiento instantáneo al volver a una ventana
        eventos_cryo = self.cryo.ciclo_auto_cryo(
            presion=presion,
            ram_umbral_pct=umbral_cryo,
            idle_seg=idle_seg,
            habilitar=auto_cryo_on,
        )
        for ev in eventos_cryo:
            self.on_log(ev)

        # 2. Telemetría + predictor según intervalo configurado
        muestra = None
        if forzar_telemetria or (ahora - self._ultimo_log_ts >= self.intervalo_logger):
            muestra = self.tomar_muestra()
            self._ultimo_log_ts = ahora
            self.predictor.registrar_muestra(
                ram_pct=muestra["ram_pct"],
                cpu_pct=muestra["cpu_pct"],
                swap_pct=muestra["swap_pct"],
                ts=ahora,
            )
            if self.config.get("recolectar_datos", True):
                self._escribir_muestra_csv(muestra)

        # 3. Evaluación preventiva anti-freeze con cooldown
        self._evaluar_accion_preventiva(ahora, presion)

        with self._lock:
            self._ultimo_estado = {
                "presion": presion,
                "congelados": self.cryo.listar_congelados(),
                "auto_cryo": auto_cryo_on,
                "perfil": self.perfil["nombre"],
                "purgas_sesion": self._purgas_sesion,
                "muestras_predictor": self.predictor.total_muestras,
                "ultima_muestra": muestra,
                "actualizado": ahora,
            }

    def _evaluar_accion_preventiva(self, ahora: float, presion: dict[str, Any]):
        if (ahora - self._ultima_purga_ts) < self.cooldown:
            return

        nivel = presion.get("nivel", "baja")
        ram_pct = float(presion.get("ram_pct", 0.0))
        swap_pct = float(presion.get("swap_pct", 0.0))
        ram_pred_5 = self.predictor.predecir_ram_futura()

        razon = None
        if nivel == "critica":
            razon = f"Presión crítica ({ram_pct:.1f}% RAM, {presion.get('ram_disponible_mb', 0):.0f} MB disp.)"
        elif swap_pct >= self.perfil["umbral_swap"]:
            razon = f"Swap elevado ({swap_pct:.1f}%)"
        elif ram_pred_5 is not None and ram_pred_5 >= self.perfil["umbral_predictivo"]:
            razon = f"Predicción RAM a 5m: {ram_pred_5:.1f}%"

        if not razon:
            return

        # Solo purgar memoria si Auto-Cryo ya intentó aliviar o si la presión sigue crítica
        self.on_log(f"Acción preventiva: {razon}")
        self._ultima_purga_ts = ahora
        if self.optimizer.force_memory_purge(agresiva=False):
            self.registrar_purga()
            nueva = leer_metricas_memoria()
            self.on_log(f"Sistema estabilizado: {ram_pct:.1f}% → {nueva['ram_pct']:.1f}%")

    def estado_vivo(self) -> dict[str, Any]:
        with self._lock:
            if not self._ultimo_estado:
                presion = leer_presion_memoria()
                return {
                    "presion": presion,
                    "congelados": self.cryo.listar_congelados(),
                    "auto_cryo": bool(self.config.get("auto_cryo_activo", True)),
                    "perfil": self.perfil["nombre"],
                    "purgas_sesion": self._purgas_sesion,
                    "muestras_predictor": self.predictor.total_muestras,
                }
            return dict(self._ultimo_estado)

    # Compatibilidad con API de logger previa
    def contar_filas(self) -> int:
        try:
            with open(self.archivo_csv, "r", encoding="utf-8") as f:
                return max(0, sum(1 for _ in f) - 1)
        except Exception:
            return 0
