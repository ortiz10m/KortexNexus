"""Sistema de comandos de Kortex Nexus (conectado a kortex_core)."""

from __future__ import annotations

import subprocess
import threading

from kortex_core.config import SISTEMA, SUBPROCESS_FLAGS
from kortex_core.cryo import CryoEngine
from kortex_core.files import KortexArchivos
from kortex_core.modes import ModeManager
from kortex_core.optimizer import KernelOptimizer
from kortex_core.platform_hal import leer_metricas_memoria


COMANDOS = {
    "purga_ram": [
        "purga la ram", "purga ram", "purga memoria", "purga la memoria",
        "libera ram", "libera memoria", "limpia la ram", "limpia memoria",
        "purga el sistema", "purga",
    ],
    "acelera_red": [
        "acelera internet", "acelera la red", "acelera red",
        "mejora internet", "mejora la red", "activa bbr",
        "activa bbr ctcp", "acelera la conexion",
    ],
    "ultra_rendimiento": [
        "ultra rendimiento", "modo ultra", "ultra modo",
        "optimizacion completa", "optimiza todo", "optimización total",
        "maximo rendimiento", "rendimiento maximo",
    ],
    "modo_supervivencia": [
        "modo supervivencia", "activa modo supervivencia", "supervivencia",
    ],
    "modo_gaming": [
        "modo gaming", "activa modo gaming",
    ],
    "modo_streaming": [
        "modo streaming", "activa modo streaming",
    ],
    "modo_trabajo": [
        "modo trabajo", "activa modo trabajo",
    ],
    "desactivar_modo": [
        "desactiva modo", "desactivar modo", "quita el modo", "apaga modo",
    ],
    "descongela_todo": [
        "descongela todo", "descongelar todo", "reanuda todo",
    ],
    "congela_app": [
        "congela ", "congelar ", "criogeniza ", "criogenizar ",
    ],
    "descongela_app": [
        "descongela ", "descongelar ",
    ],
    "abre_thorium": [
        "abre thorium", "abrir thorium", "lanza thorium", "lanza el navegador",
        "abre el navegador", "abrir el navegador", "abre navegador",
    ],
    "cierra_thorium": [
        "cierra thorium", "cerrar thorium", "cierra el navegador",
        "cerrar el navegador", "cierra navegador",
    ],
    "diagnostica": [
        "diagnostica mi pc", "diagnostica el pc", "diagnostica el sistema",
        "analiza mi pc", "analiza el sistema", "revisa mi pc",
        "revisa el sistema", "diagnostico", "diagnóstico",
    ],
    "detecta_basura": [
        "detecta basura", "busca basura", "analiza basura",
        "cuanta basura tengo", "cuánta basura tengo", "escanea basura",
    ],
    "escanea_disco": [
        "escanea el disco", "escanea disco", "analiza el disco",
        "analiza disco", "espacio en disco",
    ],
    "lista_apps": [
        "lista apps", "lista aplicaciones", "lista programas",
        "muestra apps", "muestra aplicaciones", "apps instaladas",
    ],
    "info_sistema": [
        "info del sistema", "informacion del sistema", "información del sistema",
        "estado del sistema", "estado de mi pc",
    ],
}

FRASES_PREGUNTA = (
    "qué es", "que es", "significa", "explicame", "explícame",
    "cómo funciona", "como funciona", "para qué sirve", "para que sirve",
)


def detectar_comando(mensaje: str) -> str | None:
    texto = mensaje.lower().strip()
    if not texto:
        return None
    if texto.startswith(("?", "¿")):
        return None
    for palabra in ("qué ", "que ", "cómo ", "como ", "cuál ", "cual ", "cuándo ", "cuando "):
        if texto.startswith(palabra):
            return None
    for frase in FRASES_PREGUNTA:
        if frase in texto:
            return None

    for comando, patrones in COMANDOS.items():
        for patron in patrones:
            if patron in texto:
                return comando
    return None


def ejecutar_comando(
    comando: str,
    mensaje: str,
    contexto: dict,
    optimizer: KernelOptimizer | None = None,
    cryo: CryoEngine | None = None,
    modes: ModeManager | None = None,
) -> str:
    cryo_srv = cryo or (optimizer.cryo if optimizer else CryoEngine())
    opt_srv = optimizer or KernelOptimizer(cryo=cryo_srv)
    mode_srv = modes or ModeManager(optimizer=opt_srv, cryo=cryo_srv)

    try:
        if comando == "purga_ram":
            return _ejecutar_purga_ram(opt_srv)
        if comando == "acelera_red":
            return _ejecutar_acelera_red(opt_srv)
        if comando == "ultra_rendimiento":
            return _ejecutar_ultra_rendimiento(opt_srv, cryo_srv)
        if comando in ("modo_supervivencia", "modo_gaming", "modo_streaming", "modo_trabajo"):
            clave = comando.replace("modo_", "")
            res = mode_srv.activar(clave)
            pasos = "\n".join(f"• {p}" for p in res.get("pasos", []))
            return f"✅ {res.get('message', '')}\n\n{pasos}" if pasos else res.get("message", "")
        if comando == "desactivar_modo":
            res = mode_srv.desactivar()
            return f"✅ {res.get('message', 'Modo desactivado.')}"
        if comando == "descongela_todo":
            res = cryo_srv.descongelar_todo()
            return f"☀️ {res.get('message', 'Procesos reanudados.')}"
        if comando == "congela_app":
            objetivo = _extraer_argumento(mensaje, COMANDOS["congela_app"])
            if not objetivo:
                return "Indica qué aplicación congelar. Ejemplo: 'congela discord'."
            res = cryo_srv.criogenizar_proceso(objetivo)
            return ("❄️ " if res.get("success") else "⚠️ ") + res.get("message", "")
        if comando == "descongela_app":
            objetivo = _extraer_argumento(mensaje, COMANDOS["descongela_app"])
            if not objetivo:
                return "Indica qué aplicación descongelar. Ejemplo: 'descongela discord'."
            res = cryo_srv.descongelar_proceso(objetivo)
            return ("☀️ " if res.get("success") else "⚠️ ") + res.get("message", "")
        if comando == "abre_thorium":
            return _ejecutar_abrir_thorium()
        if comando == "cierra_thorium":
            return _ejecutar_cerrar_thorium()
        if comando == "diagnostica":
            from kortex_experto import diagnosticar
            return diagnosticar(contexto)
        if comando == "detecta_basura":
            return _ejecutar_detectar_basura()
        if comando == "escanea_disco":
            return _ejecutar_escanear_disco()
        if comando == "lista_apps":
            return _ejecutar_listar_apps()
        if comando == "info_sistema":
            return _ejecutar_info_sistema(contexto)
    except Exception as e:
        return f"Error ejecutando '{comando}': {e}"

    return "Comando reconocido, pero aún no implementado."


def _extraer_argumento(mensaje: str, prefijos: list[str]) -> str:
    lower = mensaje.lower().strip()
    for p in prefijos:
        if p in lower:
            idx = lower.find(p) + len(p)
            return mensaje.strip()[idx:].strip(" .\"'")
    return ""


def _ejecutar_purga_ram(kernel: KernelOptimizer) -> str:
    ram_antes = leer_metricas_memoria()["ram_pct"]
    resultado = kernel.force_memory_purge(agresiva=False)
    ram_despues = leer_metricas_memoria()["ram_pct"]
    if resultado:
        liberado = max(0.0, ram_antes - ram_despues)
        return (
            f"✅ Purga completada.\n\n"
            f"- Antes: {ram_antes:.1f}%\n"
            f"- Después: {ram_despues:.1f}%\n"
            f"- Liberado: {liberado:.1f}%"
        )
    return "No se pudo purgar completamente. Puede requerir permisos de administrador."


def _ejecutar_acelera_red(kernel: KernelOptimizer) -> str:
    if kernel.acelerar_internet():
        if SISTEMA == "Windows":
            return "✅ Control de congestión TCP (CTCP/CUBIC) optimizado mediante Windows TCP Stack."
        return "✅ TCP BBR (algoritmo de congestión de Google) + fq activados en Linux."
    return "No se pudo activar la aceleración de red. Verifica permisos de administrador/root."


def _ejecutar_ultra_rendimiento(kernel: KernelOptimizer, cryo: CryoEngine) -> str:
    pasos = []
    if kernel.proteger_proceso(es_daemon=False):
        pasos.append("✅ Prioridad de Kortex ajustada")
    if kernel.activar_expansion_memoria():
        pasos.append("✅ Compresión/expansión de memoria activada")
    if kernel.set_cpu_governor("auto"):
        pasos.append("✅ Governor / plan de CPU optimizado")
    hf = cryo.activar_hyper_focus()
    if hf.get("success"):
        pasos.append(f"✅ {hf['message']}")
    jaulas = kernel.activar_jaulas_jerarquicas()
    if jaulas:
        pasos.append(f"✅ {jaulas} procesos pesados limitados en jaulas")

    if not pasos:
        return "Ultra Rendimiento ejecutado, pero ningún paso pudo aplicarse por permisos."
    return "Ultra Rendimiento completado:\n\n" + "\n".join(pasos)


def _ejecutar_abrir_thorium() -> str:
    try:
        from modules.browser.thorium_kiosk import ThoriumKiosk

        kiosk = ThoriumKiosk()
        proc = kiosk.launch()
        if proc:
            return "✅ Thorium optimizado abierto."
        return "✅ Navegador ligero del sistema abierto (Thorium no disponible o incompatible con esta CPU)."
    except Exception as e:
        return f"Error al abrir navegador: {e}"


def _ejecutar_cerrar_thorium() -> str:
    try:
        if SISTEMA == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/IM", "thorium.exe"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=SUBPROCESS_FLAGS,
            )
        else:
            subprocess.run(["pkill", "-f", "thorium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "✅ Thorium cerrado."
    except Exception as e:
        return f"Error al cerrar Thorium: {e}"


def _ejecutar_detectar_basura() -> str:
    gestor = KortexArchivos()
    resultado = []
    evento = threading.Event()

    def _callback(basura):
        resultado.extend(basura)
        evento.set()

    gestor.detectar_basura(on_completo=_callback)
    if not evento.wait(timeout=30):
        return "El escaneo tardó demasiado. Intenta desde la pestaña 'Archivos'."
    if not resultado:
        return "✅ No encontré archivos basura. Tu sistema está limpio."
    total_mb = sum(x["tamano_bytes"] for x in resultado) / (1024 * 1024)
    return (
        f"Encontré {len(resultado)} archivos basura ({total_mb:.1f} MB).\n\n"
        f"Puedes limpiarlos desde 'Archivos' → 'Basura' con recuperación en papelera."
    )


def _ejecutar_escanear_disco() -> str:
    info = KortexArchivos().info_disco()
    if "error" in info:
        return f"Error leyendo disco: {info['error']}"
    return (
        f"Estado del disco principal:\n\n"
        f"- Total: {info['total_human']}\n"
        f"- Usado: {info['usado_human']} ({info['porcentaje']}%)\n"
        f"- Libre: {info['libre_human']}"
    )


def _ejecutar_listar_apps() -> str:
    return (
        "Puedes ver la lista completa de apps instaladas (con soporte para Windows y todas las distros Linux) "
        "en la pestaña 'Archivos' → 'Apps'."
    )


def _ejecutar_info_sistema(contexto: dict) -> str:
    ram = contexto.get("ram", {})
    cpu = contexto.get("cpu", {})
    disco = contexto.get("disco", {})
    proc = contexto.get("procesos", {})
    presion = contexto.get("presion", {})

    lineas = [
        "Información del sistema:\n",
        f"- Sistema operativo: {contexto.get('sistema_operativo', 'Desconocido')}",
        f"- Uptime: {contexto.get('uptime', 'desconocido')}",
        f"- RAM: {ram.get('porcentaje', 0)}% ({ram.get('usado_gb', 0)} GB de {ram.get('total_gb', 0)} GB)",
        f"- Presión de memoria: {presion.get('nivel', 'desconocida')}",
        f"- CPU: {cpu.get('porcentaje', 0)}% ({cpu.get('nucleos_fisicos', 0)} núcleos)",
        f"- Disco: {disco.get('porcentaje', 0)}% usado",
        f"- Procesos activos: {proc.get('total', 0)}",
    ]
    if contexto.get("temperatura") is not None:
        lineas.append(f"- Temperatura CPU: {contexto['temperatura']}°C")
    return "\n".join(lineas)
