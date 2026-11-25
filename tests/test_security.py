"""Pruebas automatizadas de seguridad, cero fugas de datos y defensas del sistema."""

from __future__ import annotations

import ast
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kortex_core.config import KortexConfig
from kortex_core.cryo import CryoEngine
from kortex_core.files import KortexArchivos


ROOT = Path(__file__).resolve().parent.parent

MODULOS_RED_PROHIBIDOS = {
    "requests",
    "urllib",
    "urllib3",
    "http",
    "socket",
    "aiohttp",
    "httpx",
    "ftplib",
    "smtplib",
    "xmlrpc",
    "g4f",
    "yt_dlp",
}


def _archivos_runtime() -> list[Path]:
    rutas: list[Path] = []
    for base in (ROOT / "kortex_core", ROOT / "kortex_ui"):
        rutas.extend(sorted(base.rglob("*.py")))
    for nombre in (
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
    ):
        p = ROOT / nombre
        if p.exists():
            rutas.append(p)
    return rutas


class TestSeguridadYPrivacidad(unittest.TestCase):
    def test_cero_imports_de_red_o_telemetria(self):
        """Garantiza 0 librerías de red/HTTP/sockets en el núcleo y la UI (cero fugas)."""
        violaciones: list[str] = []
        for archivo in _archivos_runtime():
            tree = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in MODULOS_RED_PROHIBIDOS:
                            violaciones.append(f"{archivo.name}:{node.lineno} import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    if top in MODULOS_RED_PROHIBIDOS:
                        violaciones.append(f"{archivo.name}:{node.lineno} from {node.module}")
        self.assertEqual(violaciones, [], f"Se detectaron imports de red prohibidos: {violaciones}")

    def test_cero_eval_exec_pickle_os_system_ni_shell_true(self):
        """Garantiza ausencia de eval, exec, pickle.load, os.system y subprocess(..., shell=True)."""
        violaciones: list[str] = []
        for archivo in _archivos_runtime():
            tree = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # eval(...) / exec(...)
                    if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                        violaciones.append(f"{archivo.name}:{node.lineno} {node.func.id}()")
                    # os.system(...) / pickle.load(...) / pickle.loads(...)
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ("system", "popen") and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                            violaciones.append(f"{archivo.name}:{node.lineno} os.{node.func.attr}()")
                        if node.func.attr in ("load", "loads") and isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle":
                            violaciones.append(f"{archivo.name}:{node.lineno} pickle.{node.func.attr}()")
                    # shell=True en cualquier llamada
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            violaciones.append(f"{archivo.name}:{node.lineno} shell=True")
        self.assertEqual(violaciones, [], f"Se detectaron llamadas inseguras: {violaciones}")

    def test_anti_path_traversal_en_papelera(self):
        """Verifica que ningún nombre malicioso pueda sacar archivos fuera de la papelera."""
        with tempfile.TemporaryDirectory() as tmp:
            gestor = KortexArchivos(carpeta_boveda=Path(tmp) / "boveda")
            for nombre_malicioso in ("../../etc/passwd", "..\\..\\Windows\\win.ini", "archivo_normal.tmp"):
                item_id, destino = gestor._generar_ruta_papelera(Path(nombre_malicioso))
                self.assertIn(gestor.carpeta_papelera.resolve(), destino.resolve().parents)
                self.assertNotIn("..", item_id)

    def test_symlinks_siempre_ignorados_en_limpieza(self):
        """Verifica que KortexArchivos rechaza symlinks para evitar borrado fuera de alcance."""
        with tempfile.TemporaryDirectory() as tmp:
            boveda = Path(tmp) / "boveda"
            objetivo = Path(tmp) / "link_simulado.tmp"
            objetivo.write_text("dummy", encoding="utf-8")
            gestor = KortexArchivos(carpeta_boveda=boveda)
            with patch.object(Path, "is_symlink", return_value=True):
                res = gestor.limpiar_archivos_sync([str(objetivo)])
            self.assertEqual(res["eliminados"], 0)
            self.assertTrue(any("symlink" in e.lower() for e in res["errores"]))
            self.assertTrue(objetivo.exists())

    def test_cryo_nunca_congela_padre_ni_procesos_criticos(self):
        cryo = CryoEngine()
        self.assertFalse(cryo.criogenizar_proceso("")["success"])
        self.assertFalse(cryo.criogenizar_proceso(os.getppid())["success"])
        self.assertFalse(cryo.criogenizar_proceso(os.getpid())["success"])
        self.assertTrue(cryo.es_intocable("csrss.exe"))
        self.assertTrue(cryo.es_intocable("systemd"))

    def test_config_resiliente_ante_json_corrupto(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            ruta.write_text("{json corrupto!!!", encoding="utf-8")
            cfg = KortexConfig(ruta_archivo=ruta)
            self.assertTrue(cfg.get("auto_cryo_activo"))
            self.assertTrue(cfg.get("guardar_historial_chat"))


if __name__ == "__main__":
    unittest.main()
