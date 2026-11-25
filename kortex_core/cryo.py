"""Cámara Criogénica, Auto-Cryo por foco y Hyper-Focus reversible."""

from __future__ import annotations

import atexit
import os
import threading
import time
from typing import Any

import psutil

from kortex_core.config import SISTEMA
from kortex_core.platform_hal import obtener_pid_ventana_activa


# Procesos críticos del sistema y de sesión que JAMÁS deben suspenderse o estrangularse
PROCESOS_INTOCABLES: frozenset[str] = frozenset(
    {
        # Kortex y runtime
        "kortex",
        "kortexnexus",
        "kortex-logger-daemon",
        "python",
        "python3",
        # Windows core & input/shell
        "system",
        "system idle process",
        "registry",
        "smss",
        "csrss",
        "wininit",
        "winlogon",
        "services",
        "lsass",
        "svchost",
        "dwm",
        "explorer",
        "ctfmon",
        "textinputhost",
        "sihost",
        "fontdrvhost",
        "audiodg",
        "taskmgr",
        "conhost",
        "openconsole",
        "windowsterminal",
        "cmd",
        "powershell",
        "pwsh",
        "shellexperiencehost",
        "startmenuexperiencehost",
        # Linux kernel, init, display, audio, red y shells
        "systemd",
        "systemd-journald",
        "systemd-udevd",
        "systemd-logind",
        "init",
        "kthreadd",
        "kworker",
        "ksoftirqd",
        "rcu_sched",
        "migration",
        "watchdog",
        "xorg",
        "xwayland",
        "wayland",
        "kwin",
        "kwin_x11",
        "kwin_wayland",
        "gnome-shell",
        "mutter",
        "xfwm4",
        "openbox",
        "sway",
        "hyprland",
        "i3",
        "plasmashell",
        "cinnamon",
        "mate-panel",
        "lxsession",
        "lxqt-session",
        "dbus-daemon",
        "dbus-broker",
        "pulseaudio",
        "pipewire",
        "pipewire-pulse",
        "wireplumber",
        "networkmanager",
        "wpa_supplicant",
        "sshd",
        "sudo",
        "pkexec",
        "polkitd",
        "bash",
        "sh",
        "zsh",
        "fish",
        "login",
        "getty",
        "agetty",
    }
)

BLOATWARE_WINDOWS: frozenset[str] = frozenset(
    {
        "searchindexer",
        "compattelrunner",
        "onedrive",
        "widgets",
        "cortana",
        "yourphone",
        "phoneexperiencehost",
    }
)

BLOATWARE_LINUX: frozenset[str] = frozenset(
    {
        "tracker-miner-fs-3",
        "tracker-miner-fs",
        "tracker-extract-3",
        "baloo_file",
        "baloo_file_extractor",
        "updatedb",
        "packagekitd",
    }
)


def normalizar_nombre_proceso(nombre: str) -> str:
    """Normaliza nombre de ejecutable eliminando extensión .exe y espacios."""
    if not nombre:
        return ""
    base = nombre.strip().lower()
    if base.endswith(".exe"):
        base = base[:-4]
    return base


class CryoEngine:
    """Motor de congelación segura de procesos en segundo plano."""

    def __init__(self):
        self._lock = threading.RLock()
        self._inicio_ts = time.time()
        self._mi_pid = os.getpid()
        self._congelados: dict[int, dict[str, Any]] = {}
        self._pids_hyper: set[int] = set()
        self._prioridades_hyper: dict[int, int] = {}
        self._ultimo_foco: dict[int, float] = {}
        self._atexit_registrado = False
        self._registrar_atexit()

    def _registrar_atexit(self):
        if not self._atexit_registrado:
            atexit.register(self.descongelar_todo)
            self._atexit_registrado = True

    def _ancestros_propios(self) -> set[int]:
        """Devuelve el PID actual y su cadena de ancestros para nunca autocongelarse."""
        protegidos = {self._mi_pid}
        try:
            proc = psutil.Process(self._mi_pid)
            for padre in proc.parents():
                protegidos.add(padre.pid)
        except Exception:
            pass
        return protegidos

    @staticmethod
    def es_intocable(nombre: str, pid: int | None = None, ancestros: set[int] | None = None) -> bool:
        """Comprueba si un proceso pertenece al núcleo protegido del SO o a Kortex."""
        if pid is not None:
            if pid <= 4:
                return True
            if ancestros and pid in ancestros:
                return True

        norm = normalizar_nombre_proceso(nombre)
        if not norm:
            return True
        if norm in PROCESOS_INTOCABLES:
            return True
        if norm.startswith(("kworker", "ksoftirqd", "systemd-", "migration/")):
            return True
        return False

    def _familia_activa(self, pid_activo: int | None) -> tuple[set[int], set[str]]:
        """Obtiene PIDs y nombres asociados a la ventana con foco actual."""
        pids: set[int] = set()
        nombres: set[str] = set()
        if not pid_activo:
            return pids, nombres

        pids.add(pid_activo)
        try:
            proc = psutil.Process(pid_activo)
            nombre = normalizar_nombre_proceso(proc.name())
            if nombre:
                nombres.add(nombre)
            for hijo in proc.children(recursive=True):
                pids.add(hijo.pid)
            padre = proc.parent()
            if padre and not self.es_intocable(padre.name(), padre.pid):
                nombre_padre = normalizar_nombre_proceso(padre.name())
                if nombre_padre == nombre:
                    pids.add(padre.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return pids, nombres

    # --- Criogenia manual ---

    def criogenizar_proceso(self, objetivo: str | int, motivo: str = "manual") -> dict[str, Any]:
        """Suspende un proceso (por nombre o PID) y sus hijos no protegidos."""
        ancestros = self._ancestros_propios()

        if isinstance(objetivo, str):
            norm_obj = normalizar_nombre_proceso(objetivo)
            if not norm_obj or self.es_intocable(norm_obj):
                return {"success": False, "message": f"Proceso protegido: {objetivo}", "pids": []}
        else:
            norm_obj = ""
            if objetivo in ancestros or objetivo <= 4:
                return {"success": False, "message": f"PID protegido: {objetivo}", "pids": []}

        pids_afectados: list[int] = []
        with self._lock:
            for proc in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    pid = proc.info["pid"]
                    nombre = proc.info.get("name") or ""
                    if self.es_intocable(nombre, pid, ancestros):
                        continue

                    coincide = (
                        pid == objetivo
                        if isinstance(objetivo, int)
                        else norm_obj in normalizar_nombre_proceso(nombre)
                    )
                    if not coincide:
                        continue

                    ram_mb = round((proc.info["memory_info"].rss / (1024 * 1024)), 1) if proc.info.get("memory_info") else 0.0

                    for hijo in proc.children(recursive=True):
                        try:
                            if not self.es_intocable(hijo.name(), hijo.pid, ancestros):
                                hijo.suspend()
                                self._congelados[hijo.pid] = {
                                    "pid": hijo.pid,
                                    "nombre": hijo.name(),
                                    "motivo": motivo,
                                    "desde": time.time(),
                                    "ram_mb": 0.0,
                                }
                                pids_afectados.append(hijo.pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue

                    proc.suspend()
                    self._congelados[pid] = {
                        "pid": pid,
                        "nombre": nombre,
                        "motivo": motivo,
                        "desde": time.time(),
                        "ram_mb": ram_mb,
                    }
                    pids_afectados.append(pid)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if pids_afectados:
            return {
                "success": True,
                "message": f"Criogenizado: {objetivo} ({len(pids_afectados)} procesos)",
                "pids": pids_afectados,
            }
        return {"success": False, "message": f"No encontrado o protegido: {objetivo}", "pids": []}

    def descongelar_proceso(self, objetivo: str | int) -> dict[str, Any]:
        """Reanuda un proceso criogenizado (por nombre o PID) y sus hijos."""
        pids_afectados: list[int] = []
        norm_obj = normalizar_nombre_proceso(str(objetivo)) if isinstance(objetivo, str) else ""

        with self._lock:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pid = proc.info["pid"]
                    nombre = proc.info.get("name") or ""
                    coincide = (
                        pid == objetivo
                        if isinstance(objetivo, int)
                        else bool(norm_obj and norm_obj in normalizar_nombre_proceso(nombre))
                    )
                    if not coincide:
                        continue

                    for hijo in proc.children(recursive=True):
                        try:
                            hijo.resume()
                            self._congelados.pop(hijo.pid, None)
                            pids_afectados.append(hijo.pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            self._congelados.pop(hijo.pid, None)

                    proc.resume()
                    self._congelados.pop(pid, None)
                    pids_afectados.append(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if pids_afectados:
            return {
                "success": True,
                "message": f"Descongelado: {objetivo} ({len(pids_afectados)} procesos)",
                "pids": pids_afectados,
            }
        return {"success": False, "message": f"No encontrado: {objetivo}", "pids": []}

    def descongelar_todo(self) -> dict[str, Any]:
        """Garantiza que todos los procesos congelados por Kortex vuelvan a ejecutarse."""
        reactivados = 0
        with self._lock:
            pids_objetivo = list(set(self._congelados.keys()) | set(self._pids_hyper))
            for pid in pids_objetivo:
                try:
                    psutil.Process(pid).resume()
                    reactivados += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self._congelados.clear()
            self._pids_hyper.clear()

            for pid, nice_orig in list(self._prioridades_hyper.items()):
                try:
                    psutil.Process(pid).nice(nice_orig)
                except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
                    pass
            self._prioridades_hyper.clear()

        return {
            "success": True,
            "reactivados": reactivados,
            "message": f"Todos los procesos restaurados ({reactivados} reanudados).",
        }

    def listar_congelados(self) -> list[dict[str, Any]]:
        """Devuelve la lista actual de procesos congelados aún vivos."""
        with self._lock:
            vivos: list[dict[str, Any]] = []
            muertos: list[int] = []
            for pid, info in self._congelados.items():
                if psutil.pid_exists(pid):
                    vivos.append(dict(info))
                else:
                    muertos.append(pid)
            for pid in muertos:
                self._congelados.pop(pid, None)
            return vivos

    # --- Auto-Cryo por foco ---

    def ciclo_auto_cryo(
        self,
        presion: dict[str, Any],
        ram_umbral_pct: float = 78.0,
        idle_seg: int = 150,
        habilitar: bool = True,
    ) -> list[str]:
        """Ciclo inteligente: descongela la app enfocada al instante y congela apps ociosas bajo presión."""
        eventos: list[str] = []
        ahora = time.time()
        pid_activo = obtener_pid_ventana_activa()
        pids_activos, nombres_activos = self._familia_activa(pid_activo)
        ancestros = self._ancestros_propios()

        with self._lock:
            # 1. Actualizar tracking de foco y descongelar inmediatamente lo que el usuario esté mirando
            for pid in pids_activos:
                self._ultimo_foco[pid] = ahora

            a_descongelar: list[int] = []
            for pid, info in list(self._congelados.items()):
                if info.get("motivo") != "auto_cryo":
                    continue
                nombre_norm = normalizar_nombre_proceso(info.get("nombre", ""))
                if pid in pids_activos or (nombre_norm and nombre_norm in nombres_activos):
                    a_descongelar.append(pid)

            for pid in a_descongelar:
                info = self._congelados.pop(pid, {})
                try:
                    proc = psutil.Process(pid)
                    proc.resume()
                    for hijo in proc.children(recursive=True):
                        try:
                            hijo.resume()
                            self._congelados.pop(hijo.pid, None)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    eventos.append(f"Auto-Cryo reanudó '{info.get('nombre', pid)}' al recuperar foco")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if not habilitar:
                return eventos

            nivel = presion.get("nivel", "baja")
            ram_pct = float(presion.get("ram_pct", 0.0))
            bajo_presion = nivel in ("alta", "critica") or ram_pct >= ram_umbral_pct
            if not bajo_presion:
                return eventos

            # 2. Buscar candidatos ociosos pesados en segundo plano
            ram_total_mb = max(512.0, float(presion.get("ram_total_mb") or 2048.0))
            min_rss_mb = max(40.0, ram_total_mb * 0.04)
            bloat_sistema = BLOATWARE_WINDOWS if SISTEMA == "Windows" else BLOATWARE_LINUX

            candidatos: list[tuple[float, psutil.Process, str]] = []
            for proc in psutil.process_iter(["pid", "name", "memory_info", "status"]):
                try:
                    pid = proc.info["pid"]
                    nombre = proc.info.get("name") or ""
                    if pid in self._congelados or pid in pids_activos:
                        continue
                    if self.es_intocable(nombre, pid, ancestros):
                        continue

                    nombre_norm = normalizar_nombre_proceso(nombre)
                    if nombre_norm in nombres_activos:
                        self._ultimo_foco[pid] = ahora
                        continue

                    if proc.info.get("status") == psutil.STATUS_STOPPED:
                        continue

                    mem_info = proc.info.get("memory_info")
                    if not mem_info:
                        continue
                    rss_mb = mem_info.rss / (1024 * 1024)
                    if rss_mb < min_rss_mb:
                        continue

                    # Si no se pudo detectar foco en Wayland sin compositor soportado,
                    # solo congelamos bloatware conocido en presión crítica para no tocar trabajo del usuario.
                    if pid_activo is None:
                        if nivel != "critica" or nombre_norm not in bloat_sistema:
                            continue
                    else:
                        ultimo = self._ultimo_foco.get(pid, self._inicio_ts)
                        if (ahora - ultimo) < idle_seg:
                            continue

                    candidatos.append((rss_mb, proc, nombre))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            candidatos.sort(key=lambda x: x[0], reverse=True)
            congelados_ciclo = 0
            for rss_mb, proc, nombre in candidatos:
                if congelados_ciclo >= 2:
                    break
                try:
                    for hijo in proc.children(recursive=True):
                        try:
                            if not self.es_intocable(hijo.name(), hijo.pid, ancestros):
                                hijo.suspend()
                                self._congelados[hijo.pid] = {
                                    "pid": hijo.pid,
                                    "nombre": hijo.name(),
                                    "motivo": "auto_cryo",
                                    "desde": ahora,
                                    "ram_mb": 0.0,
                                }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    proc.suspend()
                    self._congelados[proc.pid] = {
                        "pid": proc.pid,
                        "nombre": nombre,
                        "motivo": "auto_cryo",
                        "desde": ahora,
                        "ram_mb": round(rss_mb, 1),
                    }
                    congelados_ciclo += 1
                    eventos.append(
                        f"Auto-Cryo congeló '{nombre}' ({rss_mb:.0f} MB, inactivo)"
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        return eventos

    # --- Hyper-Focus Cross-Platform y Reversible ---

    def activar_hyper_focus(self) -> dict[str, Any]:
        """Suspende bloatware seguro en segundo plano y reduce prioridad temporalmente."""
        ancestros = self._ancestros_propios()
        bloatware = BLOATWARE_WINDOWS if SISTEMA == "Windows" else BLOATWARE_LINUX
        pid_activo = obtener_pid_ventana_activa()
        pids_activos, nombres_activos = self._familia_activa(pid_activo)

        congelados = 0
        prioridad_bajada = 0

        with self._lock:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pid = proc.info["pid"]
                    nombre = proc.info.get("name") or ""
                    if not nombre or self.es_intocable(nombre, pid, ancestros):
                        continue
                    if pid in pids_activos:
                        continue

                    norm = normalizar_nombre_proceso(nombre)
                    if norm in nombres_activos:
                        continue

                    if norm in bloatware:
                        if pid not in self._pids_hyper:
                            proc.suspend()
                            self._pids_hyper.add(pid)
                            congelados += 1
                        if pid not in self._prioridades_hyper:
                            self._prioridades_hyper[pid] = proc.nice()
                        if SISTEMA == "Windows":
                            proc.nice(psutil.IDLE_PRIORITY_CLASS)
                        else:
                            proc.nice(19)
                    else:
                        nice_actual = proc.nice()
                        if SISTEMA == "Windows" and nice_actual == psutil.NORMAL_PRIORITY_CLASS:
                            if pid not in self._prioridades_hyper:
                                self._prioridades_hyper[pid] = nice_actual
                            proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                            prioridad_bajada += 1
                        elif SISTEMA == "Linux" and nice_actual == 0:
                            if pid not in self._prioridades_hyper:
                                self._prioridades_hyper[pid] = nice_actual
                            proc.nice(5)
                            prioridad_bajada += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
                    continue

        return {
            "success": True,
            "congelados": congelados,
            "prioridad_bajada": prioridad_bajada,
            "message": (
                f"Hyper-Focus ({SISTEMA}): {congelados} bloatware suspendidos, "
                f"{prioridad_bajada} procesos en baja prioridad."
            ),
        }

    def revertir_hyper_focus(self) -> dict[str, Any]:
        """Reactiva bloatware suspendido y restaura exactamente las prioridades originales."""
        reactivados = 0
        restaurados = 0

        with self._lock:
            for pid in list(self._pids_hyper):
                try:
                    psutil.Process(pid).resume()
                    reactivados += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self._pids_hyper.clear()

            for pid, nice_orig in list(self._prioridades_hyper.items()):
                try:
                    psutil.Process(pid).nice(nice_orig)
                    restaurados += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
                    pass
            self._prioridades_hyper.clear()

        return {
            "success": True,
            "reactivados": reactivados,
            "restaurados": restaurados,
            "message": f"Hyper-Focus revertido: {reactivados} reanudados, {restaurados} prioridades restauradas.",
        }
