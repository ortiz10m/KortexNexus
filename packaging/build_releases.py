"""Generador automático de paquetes instalables para Windows y Linux."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RELEASE_DIR = ROOT / "release"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "2.0.0"

ARCHIVOS_RAIZ_LINUX = [
    "main.py",
    "cerebro.py",
    "kortex_comandos.py",
    "kortex_contexto.py",
    "kortex_experto.py",
    "optimizador.py",
    "motor_nuclear.py",
    "kortex_centinela.py",
    "kortex_logger.py",
    "kortex_predictor.py",
    "kortex_archivos.py",
    "kortex_entrenador.py",
    "requirements.txt",
    "VERSION",
    "LICENSE",
    "README.md",
    "logo_kortex.png",
    "icon.ico",
    "run.sh",
]

CARPETAS_LINUX = [
    "kortex_core",
    "kortex_ui",
]

ARCHIVOS_EXTRA_LINUX = [
    "modules/browser/thorium_kiosk.py",
]

EXTENSIONES_TEXTO_LF = {".sh", ".py", ".txt", ".md", ".json", ".desktop", ".service"}


def _agregar_archivo_tar(tar: tarfile.TarFile, origen: Path, arcname: str, ejecutable: bool = False):
    raw = origen.read_bytes()
    if origen.suffix.lower() in EXTENSIONES_TEXTO_LF or origen.name in ("VERSION", "LICENSE"):
        raw = raw.replace(b"\r\n", b"\n")

    info = tarfile.TarInfo(name=arcname)
    info.size = len(raw)
    info.mode = 0o755 if ejecutable else 0o644
    info.mtime = int(origen.stat().st_mtime)
    tar.addfile(info, io.BytesIO(raw))


def construir_linux() -> Path:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    nombre_base = f"KortexNexus-v{VERSION}-Linux"
    salida_tar = RELEASE_DIR / f"{nombre_base}.tar.gz"
    if salida_tar.exists():
        salida_tar.unlink()

    print(f"[Build Linux] Generando {salida_tar.name} ...")
    with tarfile.open(salida_tar, "w:gz") as tar:
        _agregar_archivo_tar(
            tar,
            ROOT / "packaging" / "linux" / "install_linux.sh",
            f"{nombre_base}/install_linux.sh",
            ejecutable=True,
        )
        _agregar_archivo_tar(
            tar,
            ROOT / "packaging" / "linux" / "uninstall_linux.sh",
            f"{nombre_base}/uninstall_linux.sh",
            ejecutable=True,
        )

        leeme = (
            f"Kortex Nexus v{VERSION} — Instalador Universal para Linux\n"
            "==========================================================\n\n"
            "Instalacion completa recomendada (con ZRAM, TCP BBR y servicio systemd):\n"
            "  sudo ./install_linux.sh\n\n"
            "Instalacion solo para tu usuario (sin sudo):\n"
            "  ./install_linux.sh\n\n"
            "Desinstalacion:\n"
            "  sudo /opt/kortex-nexus/uninstall_linux.sh  (o ~/.local/share/kortex-nexus/uninstall_linux.sh)\n"
        ).encode("utf-8")
        info_leeme = tarfile.TarInfo(name=f"{nombre_base}/LEEME_LINUX.txt")
        info_leeme.size = len(leeme)
        info_leeme.mode = 0o644
        tar.addfile(info_leeme, io.BytesIO(leeme))

        for rel in ARCHIVOS_RAIZ_LINUX:
            src = ROOT / rel
            if src.exists():
                _agregar_archivo_tar(
                    tar,
                    src,
                    f"{nombre_base}/app/{rel}",
                    ejecutable=(src.suffix == ".sh"),
                )

        for rel in ARCHIVOS_EXTRA_LINUX:
            src = ROOT / rel
            if src.exists():
                _agregar_archivo_tar(tar, src, f"{nombre_base}/app/{rel}", ejecutable=False)

        for carpeta in CARPETAS_LINUX:
            base = ROOT / carpeta
            if not base.exists():
                continue
            for item in sorted(base.rglob("*")):
                if not item.is_file():
                    continue
                if "__pycache__" in item.parts or item.suffix in (".pyc", ".pyo"):
                    continue
                rel_posix = item.relative_to(ROOT).as_posix()
                _agregar_archivo_tar(tar, item, f"{nombre_base}/app/{rel_posix}", ejecutable=False)

    tam_kb = salida_tar.stat().st_size / 1024
    print(f"[Build Linux] OK -> {salida_tar} ({tam_kb:.1f} KB)")
    return salida_tar


def construir_windows() -> Path:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    spec = ROOT / "packaging" / "kortex_windows.spec"
    dist_bundle = ROOT / "dist" / "KortexNexus"

    print("[Build Windows] Ejecutando PyInstaller...")
    res = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec)],
        cwd=str(ROOT),
    )
    if res.returncode != 0 or not (dist_bundle / "KortexNexus.exe").exists():
        raise RuntimeError("PyInstaller fallo al generar dist/KortexNexus/KortexNexus.exe")

    nombre_base = f"KortexNexus-v{VERSION}-Windows"
    carpeta_rel = RELEASE_DIR / nombre_base
    carpeta_rel.mkdir(parents=True, exist_ok=True)
    destino_app = carpeta_rel / "KortexNexus"
    if destino_app.exists():
        shutil.rmtree(destino_app, ignore_errors=True)
    shutil.copytree(dist_bundle, destino_app, dirs_exist_ok=True)
    # Los archivos .bat en Windows DEBEN tener saltos de linea CRLF (\r\n) para cmd.exe
    for bat_name in ("install_windows.bat", "uninstall_windows.bat"):
        src_bat = ROOT / "packaging" / "windows" / bat_name
        raw_bat = src_bat.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        (carpeta_rel / bat_name).write_bytes(raw_bat)

    leeme_win = (
        f"Kortex Nexus v{VERSION} — Instalador para Windows\n"
        "==================================================\n\n"
        "1. Extrae esta carpeta completa (no ejecutes dentro del ZIP).\n"
        "2. Haz doble clic en install_windows.bat para instalar Kortex Nexus\n"
        "   con accesos directos en Escritorio y Menu Inicio.\n"
        "3. Tambien puedes abrirlo portable directamente desde:\n"
        "   KortexNexus\\KortexNexus.exe\n"
        "4. Modo ultra ligero en segundo plano (ideal para 1-2 GB RAM):\n"
        "   KortexNexus\\KortexNexus.exe --daemon\n"
    )
    (carpeta_rel / "LEEME_WINDOWS.txt").write_text(leeme_win, encoding="utf-8")

    salida_zip = RELEASE_DIR / f"{nombre_base}.zip"
    if salida_zip.exists():
        salida_zip.unlink()

    print(f"[Build Windows] Comprimiendo {salida_zip.name} ...")
    with zipfile.ZipFile(salida_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for archivo in sorted(carpeta_rel.rglob("*")):
            if archivo.is_file():
                arc = archivo.relative_to(RELEASE_DIR).as_posix()
                zf.write(archivo, arcname=arc)

    tam_mb = salida_zip.stat().st_size / (1024 * 1024)
    print(f"[Build Windows] OK -> {salida_zip} ({tam_mb:.1f} MB)")
    return salida_zip


def main():
    solo_linux = "--linux-only" in sys.argv
    solo_windows = "--windows-only" in sys.argv

    if not solo_windows:
        construir_linux()
    if not solo_linux:
        if os.name == "nt":
            construir_windows()
        else:
            print("[Build Windows] Saltado (requiere ejecutarse en Windows para compilar .exe).")


if __name__ == "__main__":
    main()
