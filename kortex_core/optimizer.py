"""Motor de optimización real de Kernel y Sistema Operativo (Windows y Linux)."""

from __future__ import annotations

import ctypes
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import psutil

from kortex_core.config import SISTEMA, SUBPROCESS_FLAGS, es_admin
from kortex_core.cryo import CryoEngine, normalizar_nombre_proceso
from kortex_core.platform_hal import (
    detectar_gpu,
    detectar_modelo_cpu,
    detectar_perfil_hardware,
    detectar_tipo_disco,
    leer_metricas_memoria,
    obtener_info_hardware,
    obtener_pid_ventana_activa,
    obtener_temperatura_cpu,
)


log = logging.getLogger("KortexKernel")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s][KernelOptimizer] %(message)s")

SYSCTL_KORTEX = "/etc/sysctl.d/99-kortex.conf"


class KernelOptimizer:
    """Capa unificada de optimización real sin placebo para equipos de 1 GB+."""

    def __init__(self, cryo: CryoEngine | None = None):
        self.sistema = SISTEMA
        self.es_root = es_admin()
        self.cryo = cryo or CryoEngine()
        mem = leer_metricas_memoria()
        self.ram_total_mb = int(mem["ram_total_mb"])
        self.perfil = detectar_perfil_hardware(self.ram_total_mb)
        self.tipo_disco = detectar_tipo_disco()
        self.num_nucleos = psutil.cpu_count(logical=False) or 1
        self.nucleos_logicos = psutil.cpu_count(logical=True) or 1
        self.tiene_gpu = detectar_gpu()
        self.modelo_cpu = detectar_modelo_cpu()
        self._jaulas_previas: dict[int, int] = {}

    def obtener_info_hardware(self) -> dict[str, Any]:
        """Retorna el snapshot actualizado de hardware."""
        return obtener_info_hardware()

    def obtener_temperatura_cpu(self) -> float | None:
        return obtener_temperatura_cpu()

    # --- Protección de proceso (sin mlockall en GUI) ---

    def proteger_proceso(self, es_daemon: bool = False) -> bool:
        """Protege el daemon sin clavar la GUI en RAM física mediante mlockall."""
        pid = os.getpid()
        if self.sistema == "Linux":
            if not es_daemon or not self.es_root:
                return True
            ok, _ = self._escribir_kernel(f"/proc/{pid}/oom_score_adj", "-500")
            return ok

        if self.sistema == "Windows":
            try:
                clase = 0x00008000 if es_daemon else 0x00000020  # ABOVE_NORMAL o NORMAL
                kernel32 = ctypes.windll.kernel32
                kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), clase)
                return True
            except Exception:
                return False
        return False

    # --- Utilidades sysctl / procfs ---

    def _escribir_kernel(self, ruta: str, valor: str) -> tuple[bool, str]:
        try:
            path = Path(ruta)
            if not path.exists():
                return False, f"Ruta no existe: {ruta}"
            path.write_text(f"{valor}\n", encoding="utf-8")
            return True, "OK"
        except PermissionError:
            return False, f"PermissionError en {ruta}"
        except OSError as e:
            return False, f"Error escribiendo {ruta}: {e.strerror}"

    def _persistir_sysctl(self, parametros: dict[str, str]) -> bool:
        if self.sistema != "Linux" or not self.es_root:
            return False
        try:
            sysctl_path = Path(SYSCTL_KORTEX)
            sysctl_path.parent.mkdir(parents=True, exist_ok=True)
            existentes: dict[str, str] = {}
            if sysctl_path.exists():
                for linea in sysctl_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    linea = linea.strip()
                    if linea and not linea.startswith("#") and "=" in linea:
                        k, v = linea.split("=", 1)
                        existentes[k.strip()] = v.strip()
            existentes.update({k: str(v) for k, v in parametros.items()})
            lineas = ["# Kortex Nexus — Parámetros de optimización persistentes"]
            for k, v in existentes.items():
                lineas.append(f"{k} = {v}")
            sysctl_path.write_text("\n".join(lineas) + "\n", encoding="utf-8")
            return True
        except Exception:
            return False

    # --- Expansión de memoria real (ZRAM / Memory Compression) ---

    def activar_expansion_memoria(self) -> bool:
        """Configura compresión real de RAM (ZRAM zstd/lz4 en Linux, MMAgent/Trim selectivo en Windows)."""
        if self.sistema == "Linux":
            return self._expansion_linux()
        if self.sistema == "Windows":
            return self._expansion_windows()
        return False

    def _elegir_compresor_zram(self) -> str | None:
        comp_path = Path("/sys/block/zram0/comp_algorithm")
        if not comp_path.exists():
            return None
        try:
            disponibles = comp_path.read_text(encoding="utf-8").replace("[", "").replace("]", "").split()
            for favorito in ("zstd", "lz4", "lzo-rle", "lzo"):
                if favorito in disponibles:
                    return favorito
        except Exception:
            pass
        return None

    def _expansion_linux(self) -> bool:
        if not self.es_root:
            log.warning("Expansión ZRAM en Linux requiere permisos root.")
            return False

        p = self.perfil
        zram_bytes = int(p["zram_mb"]) * 1024 * 1024
        zram_activo = False

        try:
            swaps = Path("/proc/swaps")
            if swaps.exists() and "/dev/zram" in swaps.read_text(encoding="utf-8", errors="ignore"):
                zram_activo = True

            if not zram_activo:
                subprocess.run(["modprobe", "zram"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                disksize_path = Path("/sys/block/zram0/disksize")
                if disksize_path.exists():
                    self._escribir_kernel("/sys/block/zram0/reset", "1")
                    comp = self._elegir_compresor_zram()
                    if comp:
                        self._escribir_kernel("/sys/block/zram0/comp_algorithm", comp)
                    ok, _ = self._escribir_kernel("/sys/block/zram0/disksize", str(zram_bytes))
                    if ok:
                        subprocess.run(["mkswap", "/dev/zram0"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        res = subprocess.run(
                            ["swapon", "/dev/zram0", "-p", "32767"],
                            check=False,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        zram_activo = res.returncode == 0

            swappiness = int(p["swappiness"]) if zram_activo else 15
            sysctl_params = {
                "vm.swappiness": str(swappiness),
                "vm.page-cluster": "0" if zram_activo else "3",
                "vm.vfs_cache_pressure": "50",
                "vm.dirty_background_ratio": str(p["dirty_background_ratio"]),
                "vm.dirty_ratio": str(p["dirty_ratio"]),
            }
            for clave, valor in sysctl_params.items():
                ruta = "/proc/sys/" + clave.replace(".", "/")
                self._escribir_kernel(ruta, valor)
            self._persistir_sysctl(sysctl_params)
            return True
        except Exception as e:
            log.error(f"Error en expansión Linux: {e}")
            return False

    def _expansion_windows(self) -> bool:
        """Verifica Memory Compression de Windows y recorta working sets solo de procesos ociosos."""
        try:
            if self.es_root:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "Enable-MMAgent -MemoryCompression -ErrorAction SilentlyContinue",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    creationflags=SUBPROCESS_FLAGS,
                )
            purgados = self._trim_working_sets_windows(solo_inactivos=True)
            log.info(f"[WINDOWS] Memory Compression verificada · {purgados} procesos en 2º plano recortados")
            return True
        except Exception as e:
            log.error(f"Error en expansión Windows: {e}")
            return False

    def _trim_working_sets_windows(self, solo_inactivos: bool = True) -> int:
        if self.sistema != "Windows":
            return 0
        psapi = ctypes.windll.psapi
        kernel32 = ctypes.windll.kernel32
        pid_activo = obtener_pid_ventana_activa() if solo_inactivos else None
        ancestros = {os.getpid()}

        pids_purgados = 0
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                pid = proc.info["pid"]
                nombre = proc.info.get("name") or ""
                if pid == pid_activo or self.cryo.es_intocable(nombre, pid, ancestros):
                    continue
                mem_info = proc.info.get("memory_info")
                if not mem_info or mem_info.rss < 40 * 1024 * 1024:
                    continue

                h = kernel32.OpenProcess(0x0100 | 0x0400, False, pid)
                if h:
                    if psapi.EmptyWorkingSet(h):
                        pids_purgados += 1
                    kernel32.CloseHandle(h)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return pids_purgados

    # --- Purga inteligente de memoria (cero thrashing en HDD) ---

    def force_memory_purge(self, agresiva: bool = False) -> bool:
        """Libera memoria evitando vaciar caché agresivamente sobre discos HDD lentos."""
        temp = self.obtener_temperatura_cpu()
        if temp and temp >= 82:
            log.warning(f"Temperatura CPU elevada ({temp}°C) — liberando presión")

        if self.sistema == "Linux":
            return self._purga_linux(agresiva=agresiva)
        if self.sistema == "Windows":
            return self._purga_windows(agresiva=agresiva)
        return False

    def _purga_linux(self, agresiva: bool = False) -> bool:
        if not self.es_root:
            return False

        ok_count = 0
        try:
            subprocess.run(["sync"], check=True, timeout=10)
            ok_count += 1
        except Exception:
            pass

        # Nunca drop_caches=3 en HDD (causaría page thrashing severo). Solo nivel 1 seguro o 3 en SSD bajo pedido agresivo.
        nivel_drop = "3" if (agresiva and self.tipo_disco == "SSD") else "1"
        ok, _ = self._escribir_kernel("/proc/sys/vm/drop_caches", nivel_drop)
        if ok:
            ok_count += 1

        p = self.perfil
        ok_bg, _ = self._escribir_kernel("/proc/sys/vm/dirty_background_ratio", str(p["dirty_background_ratio"]))
        ok_dr, _ = self._escribir_kernel("/proc/sys/vm/dirty_ratio", str(p["dirty_ratio"]))
        if ok_bg or ok_dr:
            ok_count += 1

        for cmd in (["resolvectl", "flush-caches"], ["systemd-resolve", "--flush-caches"], ["nscd", "-i", "hosts"]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
                    break
                except Exception:
                    continue

        return ok_count >= 2

    def _purga_windows(self, agresiva: bool = False) -> bool:
        try:
            subprocess.run(
                ["ipconfig", "/flushdns"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS,
            )
        except Exception:
            pass

        # Limpiar temporales con antigüedad > 1 hora para no romper apps abiertas
        ahora = time.time()
        rutas = []
        if os.environ.get("TEMP"):
            rutas.append(Path(os.environ["TEMP"]))
        if self.es_root:
            rutas.append(Path(r"C:\Windows\Temp"))

        for base in rutas:
            if not base.exists():
                continue
            try:
                for item in base.iterdir():
                    try:
                        if (ahora - item.stat().st_mtime) < 3600:
                            continue
                        if item.is_file() or item.is_symlink():
                            item.unlink(missing_ok=True)
                        elif item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                    except Exception:
                        continue
            except Exception:
                continue

        if not self.es_root and not agresiva:
            # Sin admin en Windows aún podemos recortar working sets de procesos propios/usuario
            self._trim_working_sets_windows(solo_inactivos=True)
            return True

        self._trim_working_sets_windows(solo_inactivos=not agresiva)
        return True

    # --- Aceleración de red ---

    def acelerar_internet(self) -> bool:
        if self.sistema == "Linux":
            return self._activar_bbr_linux()
        if self.sistema == "Windows":
            return self._activar_tcp_windows()
        return False

    def _activar_bbr_linux(self) -> bool:
        if not self.es_root:
            log.warning("TCP BBR en Linux requiere root.")
            return False
        try:
            avail_path = Path("/proc/sys/net/ipv4/tcp_available_congestion_control")
            disponibles = avail_path.read_text(encoding="utf-8").split() if avail_path.exists() else []
            if "bbr" not in disponibles:
                subprocess.run(["modprobe", "tcp_bbr"], capture_output=True, text=True, timeout=5)
                disponibles = avail_path.read_text(encoding="utf-8").split() if avail_path.exists() else []
            if "bbr" not in disponibles:
                return False

            ok1, _ = self._escribir_kernel("/proc/sys/net/core/default_qdisc", "fq")
            ok2, _ = self._escribir_kernel("/proc/sys/net/ipv4/tcp_congestion_control", "bbr")
            if ok1 and ok2:
                self._persistir_sysctl({
                    "net.core.default_qdisc": "fq",
                    "net.ipv4.tcp_congestion_control": "bbr",
                })
                return True
        except Exception as e:
            log.error(f"Error activando BBR: {e}")
        return False

    def _activar_tcp_windows(self) -> bool:
        if not self.es_root:
            log.warning("Aceleración TCP en Windows requiere permisos de administrador.")
            return False

        # Windows 10/11 moderno: PowerShell Set-NetTCPSetting
        for provider in ("CTCP", "CUBIC"):
            try:
                res = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"Set-NetTCPSetting -SettingName Internet -CongestionProvider {provider} -AutoTuningLevelLocal Normal",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    creationflags=SUBPROCESS_FLAGS,
                )
                if res.returncode == 0:
                    log.info(f"[NET] Set-NetTCPSetting aplicado: {provider}")
                    return True
            except Exception:
                continue

        # Fallback para versiones anteriores de Windows
        try:
            subprocess.run(
                ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=SUBPROCESS_FLAGS,
            )
            for proveedor in ("ctcp", "cubic", "newreno"):
                ret = subprocess.run(
                    ["netsh", "int", "tcp", "set", "global", f"congestionprovider={proveedor}"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    creationflags=SUBPROCESS_FLAGS,
                )
                if ret.returncode == 0:
                    return True
        except Exception:
            pass
        return False

    # --- Governor CPU / Plan de energía ---

    def set_cpu_governor(self, modo: str = "auto") -> bool:
        """Ajusta governor en Linux o plan de energía en Windows."""
        if self.sistema == "Linux":
            return self._governor_linux(modo)
        if self.sistema == "Windows":
            return self._plan_energia_windows(modo)
        return False

    def _governor_linux(self, modo: str = "auto") -> bool:
        if modo == "auto":
            tiene_bat = Path("/sys/class/power_supply/BAT0").exists() or Path("/sys/class/power_supply/BAT1").exists()
            preferidos = ("schedutil", "ondemand", "conservative", "powersave") if tiene_bat else ("performance", "schedutil", "ondemand")
        else:
            preferidos = (modo, "schedutil", "ondemand")

        cambiados = 0
        for cpu_dir in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*")):
            gov_path = cpu_dir / "cpufreq" / "scaling_governor"
            avail_path = cpu_dir / "cpufreq" / "scaling_available_governors"
            if not gov_path.exists():
                continue
            try:
                disponibles = avail_path.read_text(encoding="utf-8").split() if avail_path.exists() else []
                elegido = next((g for g in preferidos if not disponibles or g in disponibles), None)
                if elegido:
                    gov_path.write_text(f"{elegido}\n", encoding="utf-8")
                    cambiados += 1
            except PermissionError:
                break
            except Exception:
                continue
        return cambiados > 0

    def _plan_energia_windows(self, modo: str = "auto") -> bool:
        # GUIDs estándar de Windows: Balanced / High Performance
        guid_balanced = "381b4222-f694-41f0-9685-ff5bb260df2e"
        guid_perf = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        objetivo = guid_perf if modo == "performance" else guid_balanced
        try:
            res = subprocess.run(
                ["powercfg", "/setactive", objetivo],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS,
            )
            return res.returncode == 0
        except Exception:
            return False

    # --- Jaulas jerárquicas reversibles ---

    def activar_jaulas_jerarquicas(self, umbral_ram_pct: float = 5.0, excluir_nombres: set[str] | None = None) -> int:
        """Reduce prioridad de procesos pesados (>umbral_ram_pct) excluyendo ventana activa y lista blanca."""
        pid_activo = obtener_pid_ventana_activa()
        ancestros = self.cryo._ancestros_propios()
        exclusiones = {normalizar_nombre_proceso(x) for x in (excluir_nombres or set())}
        ram_total = max(1, psutil.virtual_memory().total)
        capturados = 0

        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                pid = proc.info["pid"]
                nombre = proc.info.get("name") or ""
                if pid == pid_activo or self.cryo.es_intocable(nombre, pid, ancestros):
                    continue
                if normalizar_nombre_proceso(nombre) in exclusiones:
                    continue
                mem_info = proc.info.get("memory_info")
                if not mem_info:
                    continue
                if ((mem_info.rss / ram_total) * 100.0) <= umbral_ram_pct:
                    continue

                if pid not in self._jaulas_previas:
                    self._jaulas_previas[pid] = proc.nice()

                if self.sistema == "Linux":
                    proc.nice(12)
                    try:
                        proc.ionice(psutil.IOPRIO_CLASS_IDLE)
                    except Exception:
                        pass
                elif self.sistema == "Windows":
                    proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

                for hijo in proc.children(recursive=True):
                    try:
                        if self.cryo.es_intocable(hijo.name(), hijo.pid, ancestros):
                            continue
                        if hijo.pid not in self._jaulas_previas:
                            self._jaulas_previas[hijo.pid] = hijo.nice()
                        if self.sistema == "Linux":
                            hijo.nice(12)
                        elif self.sistema == "Windows":
                            hijo.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    except Exception:
                        continue

                capturados += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
                continue

        return capturados

    def revertir_jaulas(self) -> int:
        """Restaura prioridades modificadas por las jaulas jerárquicas."""
        restaurados = 0
        for pid, orig in list(self._jaulas_previas.items()):
            try:
                proc = psutil.Process(pid)
                proc.nice(orig)
                if self.sistema == "Linux":
                    try:
                        proc.ionice(psutil.IOPRIO_CLASS_NONE)
                    except Exception:
                        pass
                restaurados += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
                pass
        self._jaulas_previas.clear()
        return restaurados
