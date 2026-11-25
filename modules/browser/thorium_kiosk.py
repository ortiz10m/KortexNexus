"""Lanzador inteligente de navegador con detección automática y flags de ahorro de RAM."""

from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Any

import psutil

from kortex_core.config import SISTEMA, SUBPROCESS_FLAGS, obtener_dir_app
from kortex_core.platform_hal import cpu_soporta_avx2, obtener_entorno_usuario_grafico


class ThoriumKiosk:
    """Detecta Thorium portable o el navegador instalado y lo lanza optimizado por RAM."""

    def __init__(self, start_url: str = "https://www.google.com"):
        self.start_url = start_url
        self.process: subprocess.Popen | None = None
        self.system = SISTEMA.lower()
        self.navegador = self._detectar_navegador()
        self.thorium_path = self.navegador.get("ruta")
        self.bin_dir = os.path.dirname(self.thorium_path) if self.thorium_path else ""

    def _buscar_thorium_portable(self) -> str | None:
        sub = (
            Path("linux_bin") / "thorium"
            if self.system == "linux"
            else (Path("windows_bin") / "thorium.exe" if self.system == "windows" else None)
        )
        if sub is None:
            return None

        for base in (obtener_dir_app() / "modules" / "browser", Path(__file__).resolve().parent):
            candidato = base / sub
            if candidato.exists():
                if self.system == "windows":
                    ver_file = candidato.parent / "thor_ver"
                    es_avx2 = "avx2" in (
                        ver_file.read_text(encoding="utf-8", errors="ignore").lower()
                        if ver_file.exists()
                        else "avx2"
                    )
                    if es_avx2 and not cpu_soporta_avx2():
                        return None
                return str(candidato)
        return None

    def _detectar_navegador(self) -> dict[str, Any]:
        # 1. Thorium portable (si existe y es compatible con la CPU)
        thorium = self._buscar_thorium_portable()
        if thorium:
            return {"nombre": "Thorium", "ruta": thorium, "es_chromium": True, "es_thorium": True}

        # 2. Navegadores instalados en Windows
        if self.system == "windows":
            pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            pf86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            local = Path(os.environ.get("LOCALAPPDATA", ""))

            candidatos = [
                ("Brave", True, [
                    pf / "BraveSoftware/Brave-Browser/Application/brave.exe",
                    pf86 / "BraveSoftware/Brave-Browser/Application/brave.exe",
                    local / "BraveSoftware/Brave-Browser/Application/brave.exe",
                ]),
                ("Google Chrome", True, [
                    pf / "Google/Chrome/Application/chrome.exe",
                    pf86 / "Google/Chrome/Application/chrome.exe",
                    local / "Google/Chrome/Application/chrome.exe",
                ]),
                ("Microsoft Edge", True, [
                    pf86 / "Microsoft/Edge/Application/msedge.exe",
                    pf / "Microsoft/Edge/Application/msedge.exe",
                ]),
                ("Vivaldi", True, [local / "Vivaldi/Application/vivaldi.exe"]),
                ("Firefox", False, [
                    pf / "Mozilla Firefox/firefox.exe",
                    pf86 / "Mozilla Firefox/firefox.exe",
                ]),
            ]
            for nombre, es_chromium, rutas in candidatos:
                for r in rutas:
                    if str(r) and r.exists():
                        return {"nombre": nombre, "ruta": str(r), "es_chromium": es_chromium, "es_thorium": False}

        # 3. Navegadores instalados en Linux (todas las distros)
        if self.system == "linux":
            candidatos_linux = [
                ("Thorium", "thorium-browser", True),
                ("Brave", "brave-browser", True),
                ("Chromium", "chromium", True),
                ("Chromium", "chromium-browser", True),
                ("Google Chrome", "google-chrome", True),
                ("Epiphany", "epiphany", False),
                ("Falkon", "falkon", False),
                ("Firefox", "firefox", False),
            ]
            for nombre, cmd, es_chromium in candidatos_linux:
                binario = shutil.which(cmd)
                if binario:
                    return {"nombre": nombre, "ruta": binario, "es_chromium": es_chromium, "es_thorium": cmd == "thorium-browser"}

        return {"nombre": "Navegador del sistema", "ruta": None, "es_chromium": False, "es_thorium": False}

    def info_navegador(self) -> dict[str, Any]:
        return dict(self.navegador)

    def verificar_compatibilidad(self) -> tuple[bool, str]:
        if self.navegador.get("ruta"):
            return True, "OK"
        return False, "Se usará el navegador predeterminado del sistema."

    def _get_optimized_flags(self, url: str) -> list[str]:
        ruta = self.navegador["ruta"]
        if not self.navegador.get("es_chromium"):
            return [ruta, url]

        flags = [
            ruta,
            "--new-window",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-features=BackForwardCache,OptimizationGuideModelDownloading",
        ]

        if self.navegador.get("es_thorium"):
            flags.extend([
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-sync",
                "--disable-extensions",
                "--disable-async-dns",
                "--proxy-server=direct://",
                "--proxy-bypass-list=*",
            ])

        if self.system == "linux":
            flags.append("--ozone-platform-hint=auto")

        try:
            mem_gb = psutil.virtual_memory().total / (1024 ** 3)
            if mem_gb <= 2.2:
                flags.extend([
                    "--js-flags=--max-old-space-size=256",
                    "--disable-gpu",
                    "--num-raster-threads=1",
                    "--renderer-process-limit=2",
                ])
            elif mem_gb <= 4.2:
                flags.extend(["--js-flags=--max-old-space-size=512"])
            else:
                flags.extend(["--js-flags=--max-old-space-size=1024"])
        except Exception:
            flags.extend(["--js-flags=--max-old-space-size=512"])

        flags.append(url)
        return flags

    def launch(self, url: str | None = None, extra_flags: list[str] | None = None):
        target_url = url or self.start_url
        if not self.navegador.get("ruta"):
            try:
                webbrowser.open(target_url)
            except Exception:
                pass
            return None

        flags = self._get_optimized_flags(target_url)
        if extra_flags:
            flags.extend(extra_flags)

        try:
            cwd = self.bin_dir if self.navegador.get("es_thorium") and self.bin_dir else None
            if self.system == "linux" and hasattr(os, "geteuid") and os.geteuid() == 0:
                sudo_user = os.environ.get("SUDO_USER")
                env = obtener_entorno_usuario_grafico()
                if sudo_user:
                    cmd = ["sudo", "-u", sudo_user, "env", f"DISPLAY={env.get('DISPLAY', ':0')}", f"HOME={env.get('HOME', '')}"]
                    if env.get("WAYLAND_DISPLAY"):
                        cmd.append(f"WAYLAND_DISPLAY={env['WAYLAND_DISPLAY']}")
                    if env.get("XDG_RUNTIME_DIR"):
                        cmd.append(f"XDG_RUNTIME_DIR={env['XDG_RUNTIME_DIR']}")
                    if env.get("XAUTHORITY"):
                        cmd.append(f"XAUTHORITY={env['XAUTHORITY']}")
                    cmd.extend(flags)
                else:
                    cmd = flags
                self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, cwd=cwd, env=env)
            else:
                self.process = subprocess.Popen(
                    flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    cwd=cwd,
                    creationflags=SUBPROCESS_FLAGS,
                )
            return self.process
        except Exception:
            try:
                webbrowser.open(target_url)
            except Exception:
                pass
            return None

    def kill(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
