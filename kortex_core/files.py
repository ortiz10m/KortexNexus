"""Gestor seguro de archivos, basura multi-distro, duplicados, apps y papelera con manifiesto."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from kortex_core.config import SISTEMA, es_admin, obtener_carpeta_boveda, obtener_disco_principal, obtener_home_usuario_real
from kortex_core.platform_hal import ejecutar_kortex_elevado


EXTENSIONES_BASURA = {
    ".tmp", ".temp", ".log", ".bak", ".old", ".cache",
    ".dmp", ".crdownload", ".part", ".swp", ".swo",
}

RUTAS_INTOCABLES = {
    "/proc", "/sys", "/dev", "/run",
    "/boot", "/etc", "/bin", "/sbin", "/lib", "/lib64",
    "/usr", "/var/lib", "/root",
    "C:\\Windows\\System32",
    "C:\\Windows\\SysWOW64",
    "C:\\Windows\\WinSxS",
    "C:\\Windows\\Fonts",
    "C:\\Windows\\Boot",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\System Volume Information",
}

RUTAS_PROTEGIDAS = {
    "/",
    "/home",
    "/var",
    "C:\\",
    "C:\\Users",
    "C:\\Windows",
    "C:\\ProgramData",
}

DIAS_PAPELERA = 30


def _env_path(var_name: str, *subparts: str) -> Path | None:
    valor = os.environ.get(var_name, "").strip()
    if not valor:
        return None
    ruta = Path(valor)
    for parte in subparts:
        ruta = ruta / parte
    return ruta


class KortexArchivos:
    """Gestor de disco y limpieza segura con papelera basada en manifest.json."""

    def __init__(self, carpeta_boveda: Path | None = None):
        self.boveda = Path(carpeta_boveda) if carpeta_boveda else obtener_carpeta_boveda()
        self.carpeta_papelera = self.boveda / "papelera"
        self.archivo_manifest = self.carpeta_papelera / "manifest.json"
        self.archivo_operaciones = self.boveda / "operaciones.log"

        self.boveda.mkdir(parents=True, exist_ok=True)
        self.carpeta_papelera.mkdir(parents=True, exist_ok=True)

        self.sistema = SISTEMA
        self._cancelar = False
        self._manifest_lock = threading.RLock()

    # --- Manifest de papelera ---

    def _cargar_manifest(self) -> list[dict[str, Any]]:
        with self._manifest_lock:
            if not self.archivo_manifest.exists():
                return []
            try:
                data = json.loads(self.archivo_manifest.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except Exception:
                return []

    def _guardar_manifest(self, entradas: list[dict[str, Any]]):
        with self._manifest_lock:
            tmp = self.archivo_manifest.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(entradas, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.archivo_manifest)

    # --- Escaneo de disco ---

    def escanear_disco(
        self,
        ruta_raiz: str | None = None,
        on_progreso: Callable[[str], None] | None = None,
        on_completo: Callable[[list[dict[str, Any]]], None] | None = None,
        profundidad_max: int = 3,
    ):
        if ruta_raiz is None:
            ruta_raiz = str(obtener_home_usuario_real()) if self.sistema == "Linux" else obtener_disco_principal()

        self._cancelar = False

        def _escanear():
            resultado: list[dict[str, Any]] = []
            try:
                resultado = self._escanear_recursivo(Path(ruta_raiz), profundidad_max, 0, on_progreso)
                resultado.sort(key=lambda x: x["tamano_bytes"], reverse=True)
            except Exception as e:
                print(f"[Archivos] Error en escaneo: {e}")
            finally:
                if on_completo:
                    on_completo(resultado)

        threading.Thread(target=_escanear, daemon=True).start()

    def _escanear_recursivo(
        self,
        ruta: Path,
        profundidad_max: int,
        profundidad_actual: int,
        on_progreso: Callable[[str], None] | None = None,
    ) -> list[dict[str, Any]]:
        if self._cancelar:
            return []

        resultado: list[dict[str, Any]] = []
        try:
            if on_progreso:
                on_progreso(str(ruta))

            tamano_total = 0
            num_archivos = 0
            subcarpetas: list[dict[str, Any]] = []

            for elemento in ruta.iterdir():
                if self._cancelar:
                    break
                try:
                    if elemento.is_symlink():
                        continue
                    if elemento.is_file():
                        tamano_total += elemento.stat().st_size
                        num_archivos += 1
                    elif elemento.is_dir():
                        if self._es_ruta_intocable(elemento):
                            continue
                        if profundidad_actual < profundidad_max:
                            hijos = self._escanear_recursivo(
                                elemento, profundidad_max, profundidad_actual + 1, on_progreso
                            )
                            if hijos:
                                subcarpetas.extend(hijos)
                                tamano_total += sum(
                                    h["tamano_bytes"] for h in hijos if h["profundidad"] == profundidad_actual + 1
                                )
                        else:
                            tamano_total += self._calcular_tamano_carpeta(elemento)
                except (PermissionError, OSError):
                    continue

            entrada = {
                "ruta": str(ruta),
                "nombre": ruta.name or str(ruta),
                "tamano_bytes": tamano_total,
                "tamano_human": self._formatear_tamano(tamano_total),
                "num_archivos": num_archivos,
                "profundidad": profundidad_actual,
                "tipo": "carpeta",
                "hijos": subcarpetas,
            }
            resultado.append(entrada)
            resultado.extend(subcarpetas)
        except (PermissionError, OSError):
            pass

        return resultado

    def _calcular_tamano_carpeta(self, ruta: Path) -> int:
        total = 0
        try:
            for elemento in ruta.rglob("*"):
                if elemento.is_symlink():
                    continue
                try:
                    if elemento.is_file():
                        total += elemento.stat().st_size
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        return total

    # --- Detección de basura multi-distro ---

    def _rutas_usuario(self) -> list[Path]:
        if self.sistema == "Linux":
            home = obtener_home_usuario_real()
            return [
                home / ".cache",
                home / ".thumbnails",
                home / ".local" / "share" / "Trash" / "files",
                Path("/tmp"),
                Path("/var/tmp"),
            ]

        candidatos = [
            _env_path("TEMP"),
            _env_path("LOCALAPPDATA", "Microsoft", "Windows", "INetCache"),
            _env_path("LOCALAPPDATA", "Microsoft", "Windows", "Explorer"),
            _env_path("LOCALAPPDATA", "CrashDumps"),
            _env_path("LOCALAPPDATA", "Microsoft", "Windows", "WER"),
            _env_path("APPDATA", "Microsoft", "Windows", "Recent"),
        ]
        return [r for r in candidatos if r is not None]

    def _rutas_admin(self) -> list[Path]:
        if self.sistema == "Linux":
            candidatos = [
                Path("/var/log"),
                Path("/var/cache/apt/archives"),
                Path("/var/cache/pacman/pkg"),
                Path("/var/cache/dnf"),
                Path("/var/cache/zypp/packages"),
                Path("/var/cache/apk"),
            ]
            return [p for p in candidatos if p.exists()]

        win_dir = _env_path("SystemRoot") or Path("C:\\Windows")
        prog_data = _env_path("ProgramData") or Path("C:\\ProgramData")
        return [
            win_dir / "Temp",
            win_dir / "Prefetch",
            win_dir / "SoftwareDistribution" / "Download",
            win_dir / "Logs",
            prog_data / "Microsoft" / "Windows" / "WER",
        ]

    def _detectar_rutas_navegadores(self) -> list[Path]:
        rutas: list[Path] = []
        if self.sistema == "Linux":
            base = obtener_home_usuario_real() / ".cache"
            for nombre in ("google-chrome", "chromium", "brave", "opera", "vivaldi", "thorium"):
                ruta = base / nombre
                if ruta.exists():
                    rutas.append(ruta)
            firefox = obtener_home_usuario_real() / ".mozilla" / "firefox"
            if firefox.exists():
                for perfil in firefox.glob("*.default*"):
                    cache = perfil / "cache2"
                    if cache.exists():
                        rutas.append(cache)
            return rutas

        if self.sistema == "Windows":
            local = _env_path("LOCALAPPDATA")
            roaming = _env_path("APPDATA")
            if local:
                chromium_based = [
                    local / "Google" / "Chrome" / "User Data",
                    local / "Microsoft" / "Edge" / "User Data",
                    local / "BraveSoftware" / "Brave-Browser" / "User Data",
                    local / "Thorium" / "User Data",
                    local / "Vivaldi" / "User Data",
                    local / "Chromium" / "User Data",
                    local / "Opera Software" / "Opera Stable",
                    local / "Opera Software" / "Opera GX Stable",
                ]
                for base in chromium_based:
                    if not base.exists():
                        continue
                    for sub in ("Default/Cache",):
                        c = base / sub
                        if c.exists():
                            rutas.append(c)
                    for perfil in base.glob("Profile *"):
                        c = perfil / "Cache"
                        if c.exists():
                            rutas.append(c)

            if roaming:
                ff = roaming / "Mozilla" / "Firefox" / "Profiles"
                if ff.exists():
                    for perfil in ff.glob("*.default*"):
                        c = perfil / "cache2"
                        if c.exists():
                            rutas.append(c)
        return rutas

    def detectar_basura(
        self,
        incluir_admin: bool = False,
        on_progreso: Callable[[str], None] | None = None,
        on_completo: Callable[[list[dict[str, Any]]], None] | None = None,
    ):
        self._cancelar = False

        def _detectar():
            basura: list[dict[str, Any]] = []
            try:
                basura = self._buscar_basura(on_progreso, incluir_admin)
                basura.sort(key=lambda x: x["tamano_bytes"], reverse=True)
            except Exception as e:
                print(f"[Archivos] Error detectando basura: {e}")
            finally:
                if on_completo:
                    on_completo(basura)

        threading.Thread(target=_detectar, daemon=True).start()

    def _buscar_basura(self, on_progreso: Callable[[str], None] | None = None, incluir_admin: bool = False) -> list[dict[str, Any]]:
        basura: list[dict[str, Any]] = []
        vistos: set[str] = set()
        hace_30_dias = datetime.now() - timedelta(days=30)

        rutas = self._rutas_usuario()
        if incluir_admin:
            rutas = rutas + self._rutas_admin()
        rutas = rutas + self._detectar_rutas_navegadores()

        for carpeta in rutas:
            if self._cancelar:
                break
            if not carpeta or not carpeta.exists() or self._es_ruta_intocable(carpeta):
                continue
            if on_progreso:
                on_progreso(f"Escaneando {carpeta}")

            try:
                for archivo in carpeta.rglob("*"):
                    if self._cancelar:
                        break
                    try:
                        if archivo.is_symlink() or not archivo.is_file():
                            continue
                        if self._es_ruta_intocable(archivo):
                            continue

                        ruta_res = str(archivo.resolve())
                        if ruta_res in vistos:
                            continue
                        vistos.add(ruta_res)

                        stat = archivo.stat()
                        extension = archivo.suffix.lower()
                        modificado = datetime.fromtimestamp(stat.st_mtime)
                        categoria = self._categorizar(archivo, extension, modificado, hace_30_dias)
                        if not categoria:
                            continue

                        basura.append({
                            "ruta": str(archivo),
                            "nombre": archivo.name,
                            "tamano_bytes": stat.st_size,
                            "tamano_human": self._formatear_tamano(stat.st_size),
                            "categoria": categoria,
                            "modificado": modificado.strftime("%Y-%m-%d"),
                            "seguro": True,
                            "requiere_admin": self._requiere_admin(archivo),
                        })
                    except (PermissionError, OSError):
                        continue
            except (PermissionError, OSError):
                continue

        return basura

    def _categorizar(self, archivo: Path, extension: str, modificado: datetime, hace_30_dias: datetime) -> str | None:
        ruta_str = str(archivo)
        ruta_lower = ruta_str.lower()

        if extension in EXTENSIONES_BASURA:
            if extension == ".log" and modificado >= hace_30_dias:
                return None
            return "Archivo temporal"
        if ".cache" in ruta_lower or "/cache/" in ruta_lower or "\\cache\\" in ruta_lower:
            return "Caché de aplicación"
        if "trash" in ruta_lower:
            return "Papelera del SO"
        if "inetcache" in ruta_lower:
            return "Caché de Internet"
        if "crashdumps" in ruta_lower:
            return "Reporte de crash"
        if "\\wer\\" in ruta_lower or "/wer/" in ruta_lower:
            return "Reporte de errores"
        if "\\recent\\" in ruta_lower or "/recent/" in ruta_lower:
            return "Archivos recientes"
        return None

    def _requiere_admin(self, archivo: Path) -> bool:
        try:
            ruta_str = str(archivo.resolve())
        except (OSError, RuntimeError):
            return False

        for admin_ruta in self._rutas_admin():
            try:
                admin_res = str(admin_ruta.resolve())
            except (OSError, RuntimeError):
                continue
            if ruta_str == admin_res or ruta_str.startswith(admin_res + os.sep):
                return True
        return False

    # --- Duplicados ---

    def buscar_duplicados(
        self,
        ruta_busqueda: str | None = None,
        tamano_minimo_mb: float = 1.0,
        on_progreso: Callable[[str], None] | None = None,
        on_completo: Callable[[list[dict[str, Any]]], None] | None = None,
    ):
        if ruta_busqueda is None:
            ruta_busqueda = str(obtener_home_usuario_real())

        self._cancelar = False
        tamano_minimo = int(tamano_minimo_mb * 1024 * 1024)

        def _buscar():
            duplicados: list[dict[str, Any]] = []
            try:
                duplicados = self._encontrar_duplicados(Path(ruta_busqueda), tamano_minimo, on_progreso)
            except Exception as e:
                print(f"[Archivos] Error buscando duplicados: {e}")
            finally:
                if on_completo:
                    on_completo(duplicados)

        threading.Thread(target=_buscar, daemon=True).start()

    def _encontrar_duplicados(self, ruta: Path, tamano_minimo: int, on_progreso: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
        hashes: dict[str, list[Path]] = {}
        duplicados: list[dict[str, Any]] = []
        archivos_por_tamano: dict[int, list[Path]] = {}

        for archivo in ruta.rglob("*"):
            if self._cancelar:
                break
            try:
                if archivo.is_symlink() or not archivo.is_file():
                    continue
                if self._es_ruta_intocable(archivo):
                    continue
                # No incluir la propia papelera de Kortex en búsqueda de duplicados
                if self.carpeta_papelera in archivo.parents:
                    continue
                tamano = archivo.stat().st_size
                if tamano < tamano_minimo:
                    continue
                archivos_por_tamano.setdefault(tamano, []).append(archivo)
            except (PermissionError, OSError):
                continue

        for _tamano, archivos in archivos_por_tamano.items():
            if len(archivos) < 2:
                continue
            for archivo in archivos:
                if self._cancelar:
                    break
                if on_progreso:
                    on_progreso(f"Verificando: {archivo.name}")
                h = self._hash_archivo(archivo)
                if h:
                    hashes.setdefault(h, []).append(archivo)

        for hash_val, archivos in hashes.items():
            if len(archivos) > 1:
                tamano = archivos[0].stat().st_size
                duplicados.append({
                    "hash": hash_val,
                    "tamano_bytes": tamano,
                    "tamano_human": self._formatear_tamano(tamano),
                    "copias": [str(a) for a in archivos],
                    "ahorro_posible": self._formatear_tamano(tamano * (len(archivos) - 1)),
                })

        duplicados.sort(key=lambda x: x["tamano_bytes"] * len(x["copias"]), reverse=True)
        return duplicados

    def _hash_archivo(self, ruta: Path) -> str | None:
        try:
            md5 = hashlib.md5()
            with open(ruta, "rb") as f:
                for bloque in iter(lambda: f.read(65536), b""):
                    md5.update(bloque)
            return md5.hexdigest()
        except (PermissionError, OSError):
            return None

    # --- Apps instaladas (Todas las distros Linux + Windows HKLM/HKCU) ---

    def listar_apps(
        self,
        on_progreso: Callable[[str], None] | None = None,
        on_completo: Callable[[list[dict[str, Any]]], None] | None = None,
    ):
        def _listar():
            apps: list[dict[str, Any]] = []
            try:
                if self.sistema == "Linux":
                    apps = self._listar_apps_linux(on_progreso)
                elif self.sistema == "Windows":
                    apps = self._listar_apps_windows(on_progreso)
                apps.sort(key=lambda x: x.get("tamano_bytes", 0), reverse=True)
            except Exception as e:
                print(f"[Archivos] Error listando apps: {e}")
            finally:
                if on_completo:
                    on_completo(apps)

        threading.Thread(target=_listar, daemon=True).start()

    def _listar_apps_linux(self, on_progreso: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
        apps: list[dict[str, Any]] = []

        if shutil.which("dpkg-query"):
            if on_progreso:
                on_progreso("Consultando dpkg...")
            apps.extend(self._apps_dpkg())
        elif shutil.which("pacman"):
            if on_progreso:
                on_progreso("Consultando pacman...")
            apps.extend(self._apps_pacman())
        elif shutil.which("rpm"):
            if on_progreso:
                on_progreso("Consultando rpm...")
            apps.extend(self._apps_rpm())
        elif shutil.which("apk"):
            if on_progreso:
                on_progreso("Consultando apk...")
            apps.extend(self._apps_apk())

        if shutil.which("flatpak"):
            if on_progreso:
                on_progreso("Consultando flatpak...")
            apps.extend(self._apps_flatpak())

        return apps

    def _apps_dpkg(self) -> list[dict[str, Any]]:
        apps = []
        try:
            res = subprocess.run(
                ["dpkg-query", "-W", "-f=${Package}\t${Installed-Size}\t${Version}\t${Description}\n"],
                capture_output=True, text=True, timeout=15,
            )
            for linea in res.stdout.splitlines():
                partes = linea.split("\t")
                if len(partes) >= 2 and partes[0].strip():
                    nombre = partes[0].strip()
                    kb = int(partes[1].strip() or 0)
                    apps.append({
                        "nombre": nombre,
                        "version": partes[2].strip() if len(partes) > 2 else "",
                        "descripcion": partes[3].strip()[:80] if len(partes) > 3 else "",
                        "tamano_bytes": kb * 1024,
                        "tamano_human": self._formatear_tamano(kb * 1024),
                        "cmd_desinstalar": f"apt remove --purge {nombre} -y",
                        "origen": "dpkg",
                    })
        except Exception:
            pass
        return apps

    def _apps_pacman(self) -> list[dict[str, Any]]:
        apps = []
        try:
            res = subprocess.run(["pacman", "-Qi"], capture_output=True, text=True, timeout=15)
            actual: dict[str, str] = {}
            for linea in res.stdout.splitlines():
                if not linea.strip():
                    if actual.get("Name"):
                        apps.append(self._parsear_bloque_pacman(actual))
                    actual = {}
                elif ":" in linea and not linea.startswith(" "):
                    k, v = linea.split(":", 1)
                    actual[k.strip()] = v.strip()
            if actual.get("Name"):
                apps.append(self._parsear_bloque_pacman(actual))
        except Exception:
            pass
        return apps

    def _parsear_bloque_pacman(self, bloque: dict[str, str]) -> dict[str, Any]:
        nombre = bloque.get("Name", "")
        size_raw = bloque.get("Installed Size", "0 B")
        tamano = self._parsear_tamano_texto(size_raw)
        return {
            "nombre": nombre,
            "version": bloque.get("Version", ""),
            "descripcion": bloque.get("Description", "")[:80],
            "tamano_bytes": tamano,
            "tamano_human": self._formatear_tamano(tamano),
            "cmd_desinstalar": f"pacman -Rns --noconfirm {nombre}",
            "origen": "pacman",
        }

    def _apps_rpm(self) -> list[dict[str, Any]]:
        apps = []
        gestor = "dnf remove -y" if shutil.which("dnf") else ("zypper remove -y" if shutil.which("zypper") else "rpm -e")
        try:
            res = subprocess.run(
                ["rpm", "-qa", "--qf", "%{NAME}\t%{SIZE}\t%{VERSION}\t%{SUMMARY}\n"],
                capture_output=True, text=True, timeout=15,
            )
            for linea in res.stdout.splitlines():
                partes = linea.split("\t")
                if len(partes) >= 2 and partes[0].strip():
                    nombre = partes[0].strip()
                    size_b = int(partes[1].strip() or 0)
                    apps.append({
                        "nombre": nombre,
                        "version": partes[2].strip() if len(partes) > 2 else "",
                        "descripcion": partes[3].strip()[:80] if len(partes) > 3 else "",
                        "tamano_bytes": size_b,
                        "tamano_human": self._formatear_tamano(size_b),
                        "cmd_desinstalar": f"{gestor} {nombre}",
                        "origen": gestor.split()[0],
                    })
        except Exception:
            pass
        return apps

    def _apps_apk(self) -> list[dict[str, Any]]:
        apps = []
        try:
            res = subprocess.run(["apk", "info", "-s"], capture_output=True, text=True, timeout=10)
            for linea in res.stdout.splitlines():
                if " installed size:" in linea:
                    # Formato: "<pkg>-<ver> installed size:"
                    nombre = linea.split(" installed size:")[0].strip()
                    apps.append({
                        "nombre": nombre,
                        "version": "",
                        "descripcion": "",
                        "tamano_bytes": 0,
                        "tamano_human": "—",
                        "cmd_desinstalar": f"apk del {nombre}",
                        "origen": "apk",
                    })
        except Exception:
            pass
        return apps

    def _apps_flatpak(self) -> list[dict[str, Any]]:
        apps = []
        try:
            res = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application,size,version,description"],
                capture_output=True, text=True, timeout=10,
            )
            for linea in res.stdout.splitlines():
                partes = linea.split("\t")
                if partes and partes[0].strip():
                    app_id = partes[0].strip()
                    size_b = self._parsear_tamano_texto(partes[1]) if len(partes) > 1 else 0
                    apps.append({
                        "nombre": app_id,
                        "version": partes[2].strip() if len(partes) > 2 else "",
                        "descripcion": partes[3].strip()[:80] if len(partes) > 3 else "",
                        "tamano_bytes": size_b,
                        "tamano_human": self._formatear_tamano(size_b) if size_b else "Flatpak",
                        "cmd_desinstalar": f"flatpak uninstall -y {app_id}",
                        "origen": "flatpak",
                    })
        except Exception:
            pass
        return apps

    @staticmethod
    def _parsear_tamano_texto(texto: str) -> int:
        try:
            partes = texto.strip().replace(",", ".").split()
            if not partes:
                return 0
            num = float(partes[0])
            unidad = partes[1].upper() if len(partes) > 1 else "B"
            factores = {
                "B": 1,
                "KB": 1024, "KIB": 1024,
                "MB": 1024 ** 2, "MIB": 1024 ** 2,
                "GB": 1024 ** 3, "GIB": 1024 ** 3,
            }
            return int(num * factores.get(unidad, 1))
        except Exception:
            return 0

    def _listar_apps_windows(self, on_progreso: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
        apps: list[dict[str, Any]] = []
        vistos: set[str] = set()
        try:
            import winreg

            fuentes = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]

            for hive, ruta in fuentes:
                if on_progreso:
                    on_progreso("Consultando registro de Windows...")
                try:
                    with winreg.OpenKey(hive, ruta) as llave:
                        total_sub = winreg.QueryInfoKey(llave)[0]
                        for i in range(total_sub):
                            try:
                                sub_nombre = winreg.EnumKey(llave, i)
                                with winreg.OpenKey(llave, sub_nombre) as sub_llave:
                                    nombre = self._leer_reg(winreg, sub_llave, "DisplayName")
                                    if not nombre or str(nombre).strip().lower() in vistos:
                                        continue
                                    vistos.add(str(nombre).strip().lower())
                                    tamano_kb = int(self._leer_reg(winreg, sub_llave, "EstimatedSize") or 0)
                                    apps.append({
                                        "nombre": str(nombre).strip(),
                                        "version": str(self._leer_reg(winreg, sub_llave, "DisplayVersion") or ""),
                                        "descripcion": "",
                                        "tamano_bytes": tamano_kb * 1024,
                                        "tamano_human": self._formatear_tamano(tamano_kb * 1024),
                                        "cmd_desinstalar": str(self._leer_reg(winreg, sub_llave, "UninstallString") or ""),
                                        "origen": "registro",
                                    })
                            except Exception:
                                continue
                except Exception:
                    continue
        except ImportError:
            pass

        return apps

    @staticmethod
    def _leer_reg(winreg, clave, valor: str) -> Any:
        try:
            return winreg.QueryValueEx(clave, valor)[0]
        except Exception:
            return ""

    # --- Limpieza segura + Papelera con manifest.json ---

    def limpiar_archivos(
        self,
        rutas: list[str],
        on_progreso: Callable[[str], None] | None = None,
        on_completo: Callable[[dict[str, Any]], None] | None = None,
    ):
        def _limpiar():
            resultado = self.limpiar_archivos_sync(rutas, on_progreso=on_progreso)
            if on_completo:
                on_completo(resultado)

        threading.Thread(target=_limpiar, daemon=True).start()

    def limpiar_archivos_sync(
        self,
        rutas: list[str],
        on_progreso: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Versión síncrona (útil también para pruebas) que mueve archivos a papelera segura."""
        movidos = 0
        bytes_movidos = 0
        errores: list[str] = []
        admin_actual = es_admin()

        with self._manifest_lock:
            manifest = self._cargar_manifest()

            for ruta_str in rutas:
                if self._cancelar:
                    break
                ruta = Path(ruta_str)

                if self._es_ruta_intocable(ruta) or self._es_ruta_protegida(ruta):
                    errores.append(f"Protegida/Intocable: {ruta}")
                    continue
                if ruta.is_symlink():
                    errores.append(f"Symlink ignorado: {ruta}")
                    continue
                if not ruta.exists():
                    errores.append(f"No existe: {ruta}")
                    continue
                if self._requiere_admin(ruta) and not admin_actual:
                    errores.append(f"Requiere admin: {ruta}")
                    continue

                if on_progreso:
                    on_progreso(f"Enviando a papelera: {ruta.name}")

                try:
                    tamano = ruta.stat().st_size if ruta.is_file() else self._calcular_tamano_carpeta(ruta)
                    ruta_original_abs = str(ruta.resolve())
                    item_id, destino = self._generar_ruta_papelera(ruta)

                    shutil.move(str(ruta), str(destino))
                    manifest.append({
                        "id": item_id,
                        "nombre_original": ruta.name,
                        "ruta_original": ruta_original_abs,
                        "fecha": datetime.now().isoformat(),
                        "tamano_bytes": tamano,
                    })
                    bytes_movidos += tamano
                    movidos += 1
                    self._log_operacion("MOVER", ruta, destino, tamano)
                except (PermissionError, OSError) as e:
                    errores.append(f"{ruta.name}: {e}")

            self._guardar_manifest(manifest)

        return {
            "eliminados": movidos,
            "bytes_liberados": bytes_movidos,
            "espacio_liberado": self._formatear_tamano(bytes_movidos),
            "errores": errores,
        }

    def listar_papelera(self) -> list[dict[str, Any]]:
        """Lista los elementos recuperables presentes en la papelera interna."""
        with self._manifest_lock:
            manifest = self._cargar_manifest()
            activos = []
            for item in manifest:
                ruta_p = self.carpeta_papelera / item.get("id", "")
                if ruta_p.exists():
                    copia = dict(item)
                    copia["tamano_human"] = self._formatear_tamano(int(item.get("tamano_bytes", 0)))
                    activos.append(copia)
            return activos

    def restaurar_de_papelera(self, item_id_o_nombre: str) -> bool:
        """Restaura un archivo o carpeta desde la papelera a su ruta original exacta."""
        with self._manifest_lock:
            manifest = self._cargar_manifest()
            indice = None
            for idx, item in enumerate(manifest):
                if item.get("id") == item_id_o_nombre or item.get("nombre_original") == item_id_o_nombre:
                    indice = idx
                    break

            if indice is None:
                return False

            entrada = manifest[indice]
            origen_papelera = self.carpeta_papelera / entrada["id"]
            destino_original = Path(entrada["ruta_original"])

            if not origen_papelera.exists():
                manifest.pop(indice)
                self._guardar_manifest(manifest)
                return False

            if self._es_ruta_intocable(destino_original) or self._es_ruta_protegida(destino_original):
                return False

            try:
                destino_original.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(origen_papelera), str(destino_original))
                manifest.pop(indice)
                self._guardar_manifest(manifest)
                self._log_operacion("RESTAURAR", destino_original, origen_papelera, entrada.get("tamano_bytes", 0))
                return True
            except (PermissionError, OSError):
                return False

    def vaciar_papelera(self, forzar_todo: bool = False) -> dict[str, Any]:
        """Elimina archivos expirados (> DIAS_PAPELERA) o toda la papelera si forzar_todo=True."""
        eliminados = 0
        bytes_liberados = 0
        limite = datetime.now() - timedelta(days=DIAS_PAPELERA)

        with self._manifest_lock:
            manifest = self._cargar_manifest()
            restantes: list[dict[str, Any]] = []

            for item in manifest:
                ruta_p = self.carpeta_papelera / item.get("id", "")
                if not ruta_p.exists():
                    continue
                try:
                    fecha_item = datetime.fromisoformat(item["fecha"])
                except Exception:
                    fecha_item = datetime.fromtimestamp(ruta_p.stat().st_mtime)

                if forzar_todo or fecha_item < limite:
                    try:
                        tam = int(item.get("tamano_bytes", 0))
                        if ruta_p.is_file() or ruta_p.is_symlink():
                            ruta_p.unlink(missing_ok=True)
                        elif ruta_p.is_dir():
                            shutil.rmtree(ruta_p, ignore_errors=True)
                        bytes_liberados += tam
                        eliminados += 1
                    except (PermissionError, OSError):
                        restantes.append(item)
                else:
                    restantes.append(item)

            self._guardar_manifest(restantes)

        return {
            "eliminados": eliminados,
            "espacio_liberado": self._formatear_tamano(bytes_liberados),
        }

    # --- Limpieza elevada (corregido doble sys.executable) ---

    def limpiar_archivos_como_admin(
        self,
        rutas: list[str],
        on_completo: Callable[[dict[str, Any]], None] | None = None,
    ):
        exito = ejecutar_kortex_elevado(["--clean-admin"] + rutas)
        if on_completo:
            on_completo({
                "exito": exito,
                "mensaje": "Limpieza elevada ejecutada." if exito else "Elevación cancelada o fallida.",
            })

    def _limpiar_como_admin_interno(self, rutas: list[str]):
        for ruta_str in rutas:
            ruta = Path(ruta_str)
            if not ruta.exists() or ruta.is_symlink():
                continue
            if self._es_ruta_intocable(ruta) or self._es_ruta_protegida(ruta):
                continue
            try:
                if ruta.is_file():
                    ruta.unlink()
                elif ruta.is_dir():
                    shutil.rmtree(ruta, ignore_errors=True)
                self._log_operacion("ELIMINAR_ADMIN", ruta, ruta, 0)
            except (PermissionError, OSError):
                continue

    # --- Desinstalar apps ---

    def desinstalar_app(self, app: dict[str, Any], on_completo: Callable[[dict[str, Any]], None] | None = None):
        def _desinstalar():
            exito = False
            mensaje = ""
            try:
                cmd = str(app.get("cmd_desinstalar", "")).strip()
                nombre = str(app.get("nombre", "")).strip()
                origen = app.get("origen", "")
                if not cmd:
                    mensaje = "No hay comando de desinstalación disponible."
                elif self.sistema == "Linux":
                    if origen == "flatpak":
                        args = ["flatpak", "uninstall", "-y", nombre]
                    else:
                        elevador = ["pkexec"] if (not es_admin() and shutil.which("pkexec")) else []
                        if origen == "pacman":
                            base = ["pacman", "-Rns", "--noconfirm", nombre]
                        elif origen == "dnf":
                            base = ["dnf", "remove", "-y", nombre]
                        elif origen == "zypper":
                            base = ["zypper", "remove", "-y", nombre]
                        elif origen == "apk":
                            base = ["apk", "del", nombre]
                        else:
                            base = ["apt", "remove", "--purge", nombre, "-y"]
                        args = elevador + base
                    res = subprocess.run(args, capture_output=True, text=True, timeout=90)
                    exito = res.returncode == 0
                    mensaje = f"{'Desinstalado' if exito else 'Error'}: {nombre}"
                elif self.sistema == "Windows":
                    args_win = shlex.split(cmd, posix=False)
                    args_win = [a.strip('"') for a in args_win if a.strip('"')]
                    if not args_win:
                        mensaje = "Comando de desinstalación inválido."
                    else:
                        res = subprocess.run(args_win, shell=False, capture_output=True, timeout=90)
                        exito = res.returncode == 0
                        mensaje = f"{'Desinstalado' if exito else 'Error'}: {nombre}"
            except subprocess.TimeoutExpired:
                mensaje = "Tiempo de espera agotado."
            except Exception as e:
                mensaje = f"Error: {e}"

            if on_completo:
                on_completo({"exito": exito, "mensaje": mensaje})

        threading.Thread(target=_desinstalar, daemon=True).start()

    # --- Info de disco y utilidades ---

    def info_disco(self) -> dict[str, Any]:
        try:
            uso = shutil.disk_usage(obtener_disco_principal())
            return {
                "total_bytes": uso.total,
                "usado_bytes": uso.used,
                "libre_bytes": uso.free,
                "total_human": self._formatear_tamano(uso.total),
                "usado_human": self._formatear_tamano(uso.used),
                "libre_human": self._formatear_tamano(uso.free),
                "porcentaje": round((uso.used / uso.total) * 100, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def cancelar(self):
        self._cancelar = True

    def _es_ruta_intocable(self, ruta: Path) -> bool:
        try:
            ruta_res = os.path.normcase(str(ruta.resolve()))
        except (OSError, RuntimeError):
            return True

        for intocable in RUTAS_INTOCABLES:
            try:
                intocable_res = os.path.normcase(str(Path(intocable).resolve()))
            except (OSError, RuntimeError):
                continue
            if ruta_res == intocable_res or ruta_res.startswith(intocable_res + os.sep):
                return True
        return False

    def _es_ruta_protegida(self, ruta: Path) -> bool:
        try:
            ruta_res = os.path.normcase(str(ruta.resolve()))
        except (OSError, RuntimeError):
            return True

        for protegida in RUTAS_PROTEGIDAS:
            try:
                protegida_res = os.path.normcase(str(Path(protegida).resolve()))
            except (OSError, RuntimeError):
                continue
            if ruta_res == protegida_res:
                return True
        return False

    def _generar_ruta_papelera(self, ruta: Path) -> tuple[str, Path]:
        """Genera un nombre único estrictamente dentro de self.carpeta_papelera (anti path-traversal)."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        nombre_limpio = Path(ruta.name).name.replace("..", "_").replace("/", "_").replace("\\", "_")
        item_id = f"{timestamp}_{uuid.uuid4().hex[:8]}_{nombre_limpio}"
        destino = (self.carpeta_papelera / item_id).resolve()
        if self.carpeta_papelera.resolve() not in destino.parents:
            raise ValueError("Intento de path traversal bloqueado.")
        return item_id, destino

    def _log_operacion(self, accion: str, origen: Path, destino: Path, tamano: int):
        try:
            with open(self.archivo_operaciones, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} | {accion} | {origen} -> {destino} | {tamano} bytes\n")
        except (PermissionError, OSError):
            pass

    @staticmethod
    def _formatear_tamano(bytes_val: int) -> str:
        if bytes_val < 1024:
            return f"{bytes_val} B"
        if bytes_val < 1024 ** 2:
            return f"{bytes_val / 1024:.1f} KB"
        if bytes_val < 1024 ** 3:
            return f"{bytes_val / (1024 ** 2):.1f} MB"
        return f"{bytes_val / (1024 ** 3):.2f} GB"
