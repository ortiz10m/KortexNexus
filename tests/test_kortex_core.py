"""Suite de pruebas unitarias para Kortex Nexus v2.0."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from kortex_core.config import KortexConfig
from kortex_core.cryo import CryoEngine
from kortex_core.files import KortexArchivos
from kortex_core.modes import ModeManager
from kortex_core.optimizer import KernelOptimizer
from kortex_core.platform_hal import (
    detectar_perfil_hardware,
    evaluar_nivel_presion,
    leer_metricas_memoria,
    parsear_psi_memory,
)
from kortex_core.predictor import KortexPredictor


class TestConfig(unittest.TestCase):
    def test_persistencia_atomica_y_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            cfg = KortexConfig(ruta_archivo=cfg_path)
            self.assertTrue(cfg.get("auto_cryo_activo"))
            self.assertTrue(cfg.get("recolectar_datos"))

            cfg.set("auto_cryo_activo", False)
            cfg.set("auto_cryo_idle_seg", 99)

            cfg2 = KortexConfig(ruta_archivo=cfg_path)
            self.assertFalse(cfg2.get("auto_cryo_activo"))
            self.assertEqual(cfg2.get("auto_cryo_idle_seg"), 99)


class TestPlatformHAL(unittest.TestCase):
    def test_ram_usa_available_y_no_free(self):
        fake_vmem = SimpleNamespace(
            total=2000 * 1024 * 1024,
            available=1000 * 1024 * 1024,
            free=100 * 1024 * 1024,
            percent=50.0,
        )
        fake_swap = SimpleNamespace(percent=10.0, used=100 * 1024 * 1024, total=1000 * 1024 * 1024)
        with patch("kortex_core.platform_hal.psutil.virtual_memory", return_value=fake_vmem), \
             patch("kortex_core.platform_hal.psutil.swap_memory", return_value=fake_swap):
            m = leer_metricas_memoria()
            self.assertEqual(m["ram_pct"], 50.0)
            self.assertAlmostEqual(m["ram_disponible_mb"], 1000.0, places=0)
            self.assertAlmostEqual(m["ram_usada_mb"], 1000.0, places=0)

    def test_parsear_psi_memory(self):
        contenido = (
            "some avg10=18.50 avg60=12.10 avg300=4.00 total=123456\n"
            "full avg10=11.25 avg60=3.40 avg300=1.10 total=45678\n"
        )
        psi = parsear_psi_memory(contenido)
        self.assertTrue(psi["psi_disponible"])
        self.assertEqual(psi["psi_some_10"], 18.5)
        self.assertEqual(psi["psi_full_10"], 11.25)

        presion = evaluar_nivel_presion(
            {"ram_pct": 70.0, "ram_disponible_mb": 600.0, "ram_total_mb": 2048.0, "swap_pct": 20.0},
            psi,
        )
        self.assertEqual(presion["nivel"], "critica")

    def test_perfiles_hardware(self):
        self.assertEqual(detectar_perfil_hardware(1024)["nombre"], "ULTRA_LOW")
        self.assertEqual(detectar_perfil_hardware(2048)["nombre"], "LOW_END")
        self.assertEqual(detectar_perfil_hardware(4096)["nombre"], "MID_LOW")
        self.assertEqual(detectar_perfil_hardware(8192)["nombre"], "MID_HIGH")
        self.assertEqual(detectar_perfil_hardware(16384)["nombre"], "HIGH_END")


class TestPredictor(unittest.TestCase):
    def test_proyeccion_creciente_con_timestamps_irregulares(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred = KortexPredictor(archivo_csv=Path(tmp) / "no_existe.csv")
            base_ts = time.time() - 600
            # +1.0% por minuto aprox (de 50% a 60% en 10 min)
            for i in range(11):
                pred.registrar_muestra(ram_pct=50.0 + i, cpu_pct=20.0 + i * 0.5, ts=base_ts + i * 60)

            self.assertTrue(pred.disponible)
            serie = pred.predecir_serie("ram", 60.0)
            self.assertGreater(serie["5"], 60.0)
            self.assertGreater(serie["15"], serie["5"])
            self.assertGreater(serie["tendencia_min"], 0.5)
            self.assertIsNotNone(serie["ttc_90_min"])

    def test_carga_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "datos.csv"
            csv_path.write_text(
                "timestamp,ram_pct,cpu_pct,swap_pct\n"
                "2026-01-01 10:00:00,40.0,10.0,0.0\n"
                "2026-01-01 10:01:00,42.0,15.0,0.0\n"
                "2026-01-01 10:02:00,44.0,20.0,0.0\n",
                encoding="utf-8",
            )
            pred = KortexPredictor(archivo_csv=csv_path)
            self.assertEqual(pred.total_muestras, 3)
            self.assertIsNotNone(pred.predecir_ram_futura())


class TestCryoEngine(unittest.TestCase):
    def test_proteccion_estricta_whitelist_y_pid_propio(self):
        cryo = CryoEngine()
        for nombre in ("explorer.exe", "svchost.exe", "systemd", "dwm.exe", "TextInputHost.exe", "python.exe"):
            res = cryo.criogenizar_proceso(nombre)
            self.assertFalse(res["success"])
            self.assertIn("protegido", res["message"].lower())

        res_self = cryo.criogenizar_proceso(os.getpid())
        self.assertFalse(res_self["success"])

    def test_descongelar_todo_limpia_registro(self):
        cryo = CryoEngine()
        fake_proc = unittest.mock.MagicMock()
        cryo._congelados[999999] = {"pid": 999999, "nombre": "dummy", "motivo": "manual", "desde": time.time(), "ram_mb": 50.0}
        with patch("kortex_core.cryo.psutil.Process", return_value=fake_proc):
            res = cryo.descongelar_todo()
        self.assertTrue(res["success"])
        self.assertEqual(res["reactivados"], 1)
        self.assertEqual(len(cryo._congelados), 0)
        fake_proc.resume.assert_called_once()


class TestArchivosYPapelera(unittest.TestCase):
    def test_papelera_segura_y_restauracion_exacta(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            boveda = tmp_path / "boveda"
            trabajo = tmp_path / "origen"
            trabajo.mkdir()
            archivo = trabajo / "temporal_prueba.tmp"
            archivo.write_text("contenido importante de prueba", encoding="utf-8")

            gestor = KortexArchivos(carpeta_boveda=boveda)
            res = gestor.limpiar_archivos_sync([str(archivo)])

            self.assertEqual(res["eliminados"], 1)
            self.assertFalse(archivo.exists())

            items = gestor.listar_papelera()
            self.assertEqual(len(items), 1)
            item_id = items[0]["id"]
            self.assertTrue((gestor.carpeta_papelera / item_id).exists())

            restaurado = gestor.restaurar_de_papelera(item_id)
            self.assertTrue(restaurado)
            self.assertTrue(archivo.exists())
            self.assertEqual(archivo.read_text(encoding="utf-8"), "contenido importante de prueba")
            self.assertEqual(len(gestor.listar_papelera()), 0)

    def test_no_duplica_sys_executable_en_elevacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            gestor = KortexArchivos(carpeta_boveda=Path(tmp) / "boveda")
            with patch("kortex_core.files.ejecutar_kortex_elevado", return_value=True) as mock_elev:
                gestor.limpiar_archivos_como_admin(["C:/Temp/a.tmp"])
            args_pasados = mock_elev.call_args[0][0]
            self.assertEqual(args_pasados[0], "--clean-admin")
            self.assertNotEqual(args_pasados[0], sys.executable)

    def test_protege_rutas_intocables(self):
        with tempfile.TemporaryDirectory() as tmp:
            gestor = KortexArchivos(carpeta_boveda=Path(tmp) / "boveda")
            objetivo = "C:\\Windows\\System32" if os.name == "nt" else "/etc"
            res = gestor.limpiar_archivos_sync([objetivo])
            self.assertEqual(res["eliminados"], 0)
            self.assertTrue(res["errores"])


class TestModosYComandos(unittest.TestCase):
    def test_modos_activar_y_desactivar(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = KortexConfig(ruta_archivo=Path(tmp) / "cfg.json")
            cryo = CryoEngine()
            opt = KernelOptimizer(cryo=cryo)
            mgr = ModeManager(config=cfg, optimizer=opt, cryo=cryo)

            with patch.object(opt, "activar_expansion_memoria", return_value=True), \
                 patch.object(opt, "activar_jaulas_jerarquicas", return_value=2), \
                 patch.object(opt, "revertir_jaulas", return_value=2), \
                 patch.object(cryo, "activar_hyper_focus", return_value={"success": True, "message": "ok"}), \
                 patch.object(cryo, "revertir_hyper_focus", return_value={"reactivados": 1, "restaurados": 1, "message": "ok"}):
                res = mgr.activar("supervivencia")
                self.assertTrue(res["success"])
                self.assertEqual(mgr.modo_activo, "supervivencia")

                res_off = mgr.desactivar()
                self.assertTrue(res_off["success"])
                self.assertIsNone(mgr.modo_activo)

    def test_deteccion_comandos_y_desktop_exec(self):
        from kortex_comandos import detectar_comando
        from kortex_ui.tabs.launcher import limpiar_comando_desktop

        self.assertEqual(detectar_comando("modo supervivencia"), "modo_supervivencia")
        self.assertEqual(detectar_comando("congela discord"), "congela_app")
        self.assertEqual(detectar_comando("descongela todo"), "descongela_todo")
        self.assertIsNone(detectar_comando("¿qué es la ram?"))

        self.assertEqual(limpiar_comando_desktop("/usr/bin/firefox --new-window %u"), "/usr/bin/firefox")
        self.assertEqual(limpiar_comando_desktop('env GDK_BACKEND=wayland "/opt/app/bin" %F'), "/opt/app/bin")

    def test_shims_importables(self):
        import kortex_archivos
        import kortex_centinela
        import kortex_logger
        import kortex_predictor
        import motor_nuclear
        import optimizador

        self.assertIsNotNone(optimizador.KernelInterface)
        self.assertIsNotNone(motor_nuclear.KortexDaemon)
        self.assertIsNotNone(kortex_centinela.KortexCentinela)
        self.assertIsNotNone(kortex_logger.KortexLogger)
        self.assertIsNotNone(kortex_predictor.KortexPredictor)
        self.assertIsNotNone(kortex_archivos.KortexArchivos)


if __name__ == "__main__":
    unittest.main()
