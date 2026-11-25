"""Sistema de notificaciones nativas no bloqueantes para Kortex Nexus."""

from __future__ import annotations

import platform
import shutil
import subprocess
import threading

try:
    from plyer import notification as _plyer_notification

    PLYER_DISPONIBLE = True
except ImportError:
    PLYER_DISPONIBLE = False


SISTEMA = platform.system()

TIPOS = {
    "exito": {"titulo_prefijo": "✅", "timeout": 4},
    "advertencia": {"titulo_prefijo": "⚠️", "timeout": 5},
    "error": {"titulo_prefijo": "❌", "timeout": 6},
    "info": {"titulo_prefijo": "ℹ️", "timeout": 4},
}


class GestorNotificaciones:
    """Gestor de notificaciones nativas asíncronas del SO."""

    def __init__(self):
        self._ventana_raiz = None
        self._inicializado = False

    def inicializar(self, ventana_raiz):
        self._ventana_raiz = ventana_raiz
        self._inicializado = True

    def mostrar(self, tipo: str, titulo: str, mensaje: str = "", duracion: int = 4000):
        config = TIPOS.get(tipo, TIPOS["info"])
        titulo_completo = f"{config['titulo_prefijo']} {titulo}"
        timeout_seg = config["timeout"]
        cuerpo = mensaje or titulo

        print(f"[Notif] {titulo} — {mensaje}")

        def _enviar():
            if PLYER_DISPONIBLE:
                try:
                    _plyer_notification.notify(
                        title=titulo_completo,
                        message=cuerpo,
                        app_name="Kortex Nexus",
                        timeout=timeout_seg,
                    )
                    return
                except Exception:
                    pass

            if SISTEMA == "Linux" and shutil.which("notify-send"):
                try:
                    subprocess.Popen(
                        ["notify-send", "-t", str(timeout_seg * 1000), titulo_completo, cuerpo],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    pass

        threading.Thread(target=_enviar, daemon=True).start()


_gestor = GestorNotificaciones()


def inicializar(ventana_raiz):
    _gestor.inicializar(ventana_raiz)


def notificar(tipo: str, titulo: str, mensaje: str = "", duracion: int = 4000):
    _gestor.mostrar(tipo, titulo, mensaje, duracion)
