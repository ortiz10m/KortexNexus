"""Sistema experto de Kortex Nexus.

Base de conocimiento técnico, detección de intención y acciones
de IA local (resumir, mejorar, explicar) para responder sin
depender de APIs externas ni LLMs.
"""

import re


# --- Detección de intención ---

PALABRAS_COMANDO = {
    "abre", "abrir", "cierra", "cerrar", "mata", "matar",
    "purga", "purgar", "limpia", "limpiar", "libera", "liberar",
    "optimiza", "optimizar", "acelera", "acelerar",
    "diagnostica", "diagnosticar", "analiza", "analizar",
    "busca", "buscar", "escanea", "escanear",
    "activa", "activar", "desactiva", "desactivar",
    "congela", "congelar", "descongela", "descongelar",
}

PALABRAS_PREGUNTA = {
    "qué", "que", "cómo", "como", "cuál", "cual", "cuándo", "cuando",
    "dónde", "donde", "por qué", "porque", "quién", "quien",
    "explícame", "explica", "dime", "cuéntame", "cuentame",
    "significa", "es", "son",
}

PALABRAS_DIAGNOSTICO = {
    "lento", "lenta", "caliente", "calor", "problema", "falla",
    "error", "no funciona", "se traba", "trabado", "congela",
    "va mal", "va lenta", "tarda", "pesado", "pesada",
    "no responde", "reinicia", "crash", "crashea", "se cae",
}


def detectar_intencion(mensaje: str) -> str:
    """Detecta la intención del mensaje del usuario.

    Devuelve: 'comando', 'diagnostico', 'pregunta' o 'desconocido'.
    """
    if not mensaje:
        return "desconocido"

    texto = mensaje.lower().strip()

    for palabra in PALABRAS_DIAGNOSTICO:
        if palabra in texto:
            return "diagnostico"

    for palabra in PALABRAS_COMANDO:
        if texto.startswith(palabra) or f" {palabra} " in f" {texto} ":
            return "comando"

    if "?" in texto or "¿" in texto:
        return "pregunta"
    for palabra in PALABRAS_PREGUNTA:
        if palabra in texto.split()[:3]:
            return "pregunta"

    return "desconocido"


# --- Base de conocimiento técnica ---

BASE_CONOCIMIENTO = {
    "ram": (
        "La RAM es la memoria de trabajo de tu PC. Es donde se cargan "
        "los programas mientras los usas.\n\n"
        "Piénsalo así:\n"
        "- Disco (SSD/HDD) = tu mochila (guarda cosas a largo plazo)\n"
        "- RAM = tu escritorio (lo que estás usando ahora)\n\n"
        "Cuanta más RAM tengas, más programas puedes abrir sin que el PC "
        "se ralentice. Cuando la RAM se llena, el sistema empieza a usar "
        "el disco como memoria, y eso es MUY lento."
    ),
    "cpu": (
        "El CPU (procesador) es el cerebro de tu PC. Ejecuta las "
        "instrucciones de todos los programas.\n\n"
        "Cuanto más potente sea, más rápido procesa las tareas. "
        "Pero si le pides demasiado al mismo tiempo, se satura y "
        "todo va lento.\n\n"
        "Kortex puede aliviar la carga del CPU con Jaulas Jerárquicas: "
        "baja la prioridad de procesos pesados sin cerrarlos."
    ),
    "disco": (
        "El disco es donde se guardan tus archivos permanentemente.\n\n"
        "Hay dos tipos:\n"
        "- HDD (disco duro tradicional) = lento pero barato\n"
        "- SSD (unidad de estado sólido) = MUY rápido pero más caro\n\n"
        "Si tu PC tarda en abrir programas, probablemente sea el disco. "
        "Kortex adapta su estrategia de limpieza según el tipo de disco."
    ),
    "swap": (
        "El swap (o archivo de paginación) es un espacio en el disco "
        "que Windows/Linux usa como extensión de la RAM.\n\n"
        "Cuando la RAM se llena, el sistema mueve datos al swap. "
        "El problema es que el disco es MUCHO más lento que la RAM, "
        "por eso el PC se siente lento cuando empieza a usar swap.\n\n"
        "Kortex monitorea el swap y purga RAM antes de que se llene."
    ),
    "optimizar": (
        "Optimizar tu PC significa hacer que funcione mejor sin "
        "cambiar hardware.\n\n"
        "Kortex hace varias cosas:\n"
        "- Purga RAM (libera caché innecesaria)\n"
        "- Jaulas CPU (baja prioridad de procesos pesados)\n"
        "- Hyper-Focus (suspende bloatware en Windows)\n"
        "- Acelera red (activa TCP BBR en Linux o CTCP en Windows)\n"
        "- Limpia archivos basura\n\n"
        "Todo desde un solo lugar, con un clic."
    ),
    "purga": (
        "La purga de RAM libera la memoria caché que el sistema "
        "guarda para acelerar tareas repetitivas.\n\n"
        "¿Es seguro? Sí. La caché se regenera automáticamente cuando "
        "algún programa la necesita.\n\n"
        "¿Para qué sirve? Si tu RAM está al 80%+, la purga baja ese "
        "número inmediatamente. El efecto es temporal (vuelve a subir), "
        "pero ayuda cuando necesitas abrir algo pesado."
    ),
    "basura": (
        "La 'basura' son archivos temporales que los programas crean y "
        "se olvidan de borrar:\n\n"
        "- Archivos .tmp, .cache, .log viejos\n"
        "- Reportes de crash (.dmp)\n"
        "- Caché de navegadores\n"
        "- Instaladores olvidados\n\n"
        "En tu PC puede haber 500 MB a 2 GB de basura acumulada. "
        "Kortex la detecta y la mueve a una papelera interna (no la "
        "borra permanentemente)."
    ),
    "jaulas": (
        "Las Jaulas Jerárquicas son una técnica de Kortex para "
        "controlar procesos pesados sin cerrarlos.\n\n"
        "¿Cómo funciona? Detecta procesos que consumen más del 5% de "
        "tu RAM y les BAJA la prioridad. El proceso sigue corriendo, "
        "pero el sistema le da menos CPU.\n\n"
        "¿Para qué sirve? Si tienes Chrome usando 1.2 GB, Kortex lo "
        "pone en una 'jaula' para que no asfixie al resto."
    ),
    "criogenia": (
        "La Cámara Criogénica congela procesos inactivos temporalmente.\n\n"
        "¿Cómo funciona? Suspende procesos pesados en segundo plano (no los mata) "
        "para liberar CPU y evitar que saturen la RAM.\n\n"
        "Con Auto-Cryo, cuando vuelves a la ventana de esa app, Kortex la "
        "descongela al instante y sigues exactamente donde estabas."
    ),
    "hyperfocus": (
        "Hyper-Focus funciona tanto en Windows como en Linux.\n\n"
        "Suspende temporalmente indexadores y servicios en segundo plano no esenciales "
        "y baja prioridades de procesos de fondo.\n\n"
        "Al desactivar el modo o cerrar Kortex, todo se reanuda y recupera su prioridad original."
    ),
    "bbr": (
        "TCP BBR es el algoritmo de control de congestión desarrollado por Google para Linux.\n\n"
        "En Windows, Kortex configura CTCP/CUBIC (algoritmos de Microsoft/Linux stack moderno) "
        "mediante Set-NetTCPSetting y netsh para reducir latencia y mejorar estabilidad."
    ),
    "thorium": (
        "Thorium es un navegador basado en Chromium optimizado para rendimiento.\n\n"
        "Kortex lo lanza con límites de memoria ajustados a tu RAM física. Si tu CPU "
        "no soporta AVX2 o falta el binario, Kortex abre automáticamente el navegador "
        "ligero disponible en tu sistema."
    ),
    "kortex": (
        "Kortex Nexus v2.0 es una suite Anti-Freeze diseñada para revivir equipos de 1–2 GB de RAM.\n\n"
        "- Mide presión real de memoria (PSI / RAM disponible real)\n"
        "- Configura ZRAM y compresión real sin placebo\n"
        "- Auto-Cryo: congela apps pesadas inactivas y las reanuda al volver a ellas\n"
        "- Predice tendencia de RAM en tiempo real sin dependencias pesadas\n"
        "- Funciona 100% offline en Windows y todas las distros Linux."
    ),
    "prediccion": (
        "Kortex usa un motor estadístico en tiempo real (EWMA + regresión temporal) "
        "sin dependencias pesadas como pandas o scikit-learn.\n\n"
        "Desde los primeros minutos calcula la pendiente de consumo y estima cuántos "
        "minutos faltan para alcanzar nivel crítico (TTC), activando Auto-Cryo o purga "
        "antes de que el sistema se congele."
    ),
    "privacidad": (
        "Kortex Nexus NO envía tus datos a ningún servidor.\n\n"
        "- No tiene telemetría ni cuentas\n"
        "- Funciona 100% offline\n\n"
        "Tus registros y configuración viven en ~/.kortex_nexus/."
    ),
    "windows": (
        "Kortex funciona en Windows y en todas las distros Linux (Debian, Arch, Fedora, openSUSE, Alpine).\n\n"
        "En Windows usa Memory Compression, Set-NetTCPSetting, registro HKLM/HKCU y Win32 focus tracking.\n"
        "En Linux usa ZRAM (zstd/lz4), PSI (/proc/pressure/memory), TCP BBR, cpufreq y gestores locales."
    ),
    "diferencia": (
        "¿En qué se diferencia Kortex de CCleaner, Advanced SystemCare "
        "y otros?\n\n"
        "1. NO envía tus datos a ningún lado\n"
        "2. NO tiene premium ni publicidad\n"
        "3. Aprende de TU PC con machine learning\n"
        "4. Tiene navegador integrado (Thorium)\n"
        "5. Purga RAM con papelera de recuperación\n"
        "6. Funciona 100% offline\n\n"
        "Y por si fuera poco: es gratis. Sin trampa."
    ),
}


# Sinónimos para búsqueda en la base de conocimiento
SINONIMOS = {
    "memoria": "ram",
    "procesador": "cpu",
    "ssd": "disco",
    "hdd": "disco",
    "almacenamiento": "disco",
    "caché": "purga",
    "cache": "purga",
    "liberar": "purga",
    "temporal": "basura",
    "temporales": "basura",
    "jaula": "jaulas",
    "criogénica": "criogenia",
    "criogenica": "criogenia",
    "congelar": "criogenia",
    "hiper": "hyperfocus",
    "hyper": "hyperfocus",
    "navegador": "thorium",
    "internet": "bbr",
    "red": "bbr",
    "wifi": "bbr",
    "predecir": "prediccion",
    "predice": "prediccion",
    "privacidad": "privacidad",
    "datos": "privacidad",
    "diferencia": "diferencia",
    "ccleaner": "diferencia",
}


def buscar_conocimiento(mensaje: str) -> str | None:
    """Busca el tema más relevante en la base de conocimiento.

    Devuelve el texto de la respuesta, o None si no encuentra nada.
    """
    texto = mensaje.lower()

    for palabra, tema in SINONIMOS.items():
        if palabra in texto and tema in BASE_CONOCIMIENTO:
            return BASE_CONOCIMIENTO[tema]

    for tema, respuesta in BASE_CONOCIMIENTO.items():
        if tema in texto:
            return respuesta

    return None


# --- Diagnóstico basado en contexto ---

def diagnosticar(contexto: dict) -> str:
    """Analiza el contexto y devuelve un diagnóstico en tono Kortex."""
    ram = contexto.get("ram", {})
    cpu = contexto.get("cpu", {})
    disco = contexto.get("disco", {})
    proc = contexto.get("procesos", {})
    temp = contexto.get("temperatura")

    ram_pct = ram.get("porcentaje", 0)
    cpu_pct = cpu.get("porcentaje", 0)
    disco_pct = disco.get("porcentaje", 0)
    pesados = proc.get("pesados", [])
    navegadores = proc.get("navegadores", [])

    problemas = []
    acciones = []

    if ram_pct >= 85:
        problemas.append(f"Tu RAM está al {ram_pct}%. Eso es crítico.")
        acciones.append("Purgar RAM ahora")
    elif ram_pct >= 70:
        problemas.append(f"Tu RAM está al {ram_pct}%. Empieza a notarse.")
        acciones.append("Purgar RAM cuando puedas")

    if cpu_pct >= 80:
        problemas.append(f"Tu CPU está al {cpu_pct}%. Está saturado.")
        acciones.append("Poner procesos pesados en jaulas")
    elif cpu_pct >= 60:
        problemas.append(f"Tu CPU está al {cpu_pct}%. Carga alta.")
        acciones.append("Revisar qué procesos consumen CPU")

    if disco_pct >= 90:
        problemas.append(f"Tu disco está al {disco_pct}%. Casi lleno.")
        acciones.append("Limpiar archivos basura")
    elif disco_pct >= 75:
        problemas.append(f"Tu disco está al {disco_pct}%. Conviene liberar espacio.")
        acciones.append("Detectar basura con Kortex")

    if temp is not None and temp >= 85:
        problemas.append(f"Tu CPU está a {temp}°C. Temperatura alta.")
        acciones.append("Reducir carga de CPU")

    if not problemas:
        return (
            "Revisé tu sistema y todo está en orden:\n\n"
            f"- RAM: {ram_pct}%\n"
            f"- CPU: {cpu_pct}%\n"
            f"- Disco: {disco_pct}%\n"
        )

    respuesta = "Diagnóstico rápido:\n\n"
    for p in problemas:
        respuesta += f"- {p}\n"

    if pesados:
        respuesta += "\nProcesos que más consumen:\n"
        for nombre, mb in pesados[:3]:
            respuesta += f"- {nombre}: {mb} MB\n"

    if navegadores:
        respuesta += f"\nNavegadores abiertos: {', '.join(navegadores)}\n"

    if acciones:
        respuesta += "\nPuedo hacer esto por ti:\n"
        for i, accion in enumerate(acciones, 1):
            respuesta += f"{i}. {accion}\n"
        respuesta += "\n¿Por dónde empiezo?"

    return respuesta


# --- Acciones de IA (Notas y otras pestañas) ---

def _accion_resumir(mensaje: str) -> str:
    """Analiza estructuralmente el texto para resumirlo."""
    contenido = _extraer_contenido(mensaje)
    if not contenido:
        return "No encontré contenido para resumir."

    lineas = [l.strip() for l in contenido.split("\n") if l.strip()]
    if len(lineas) <= 3:
        return "El texto es muy corto para resumir. Escribe algo más largo."

    palabras = len(contenido.split())
    caracteres = len(contenido)
    primer_parrafo = lineas[0][:120]

    return (
        f"Resumen de tu nota:\n\n"
        f"- Extensión: {palabras} palabras, {caracteres} caracteres\n"
        f"- Comienza con: \"{primer_parrafo}\"\n"
        f"- Líneas totales: {len(lineas)}\n\n"
        f"Nota: el resumen con IA real requiere un modelo de lenguaje. "
        f"Kortex funciona 100% offline, así que este es un análisis "
        f"estructural del texto.\n\n"
        f"Para resúmenes inteligentes necesitarías activar IA extendida "
        f"con Ollama (próximamente)."
    )


def _accion_mejorar(mensaje: str) -> str:
    """Analiza el texto y sugiere mejoras estructurales."""
    contenido = _extraer_contenido(mensaje)
    if not contenido:
        return "No encontré contenido para mejorar."

    sugerencias = []
    lineas = contenido.split("\n")

    if len(lineas) > 8 and not any(l.startswith("#") for l in lineas):
        sugerencias.append("- Añade un título con # para organizar")

    parrafos_largos = [l for l in lineas if len(l) > 400]
    if parrafos_largos:
        sugerencias.append("- Divide los párrafos largos en secciones más cortas")

    if "**" not in contenido and "*" not in contenido:
        sugerencias.append("- Usa **negrita** para destacar ideas clave")

    if not any(l.startswith("-") or l.startswith("*") for l in lineas):
        sugerencias.append("- Convierte listas en bullets con - o *")

    if not sugerencias:
        return "Tu texto está bien estructurado. No veo mejoras obvias."

    return (
        "Sugerencias para mejorar tu nota:\n\n"
        + "\n".join(sugerencias)
        + "\n\nNota: el análisis con IA real requiere un modelo de lenguaje. "
        "Kortex funciona 100% offline, así que este es un análisis "
        "estructural del texto."
    )


def _accion_explicar(mensaje: str) -> str:
    """Explica conceptos clave del texto."""
    contenido = _extraer_contenido(mensaje)
    if not contenido:
        return "No encontré contenido para explicar."

    temas_encontrados = []
    for tema in BASE_CONOCIMIENTO.keys():
        if tema in contenido.lower():
            temas_encontrados.append(tema)

    if temas_encontrados:
        temas_str = ", ".join(temas_encontrados[:5])
        return (
            f"Detecté estos temas técnicos en tu nota: {temas_str}\n\n"
            f"Puedes preguntarme específicamente sobre cualquiera de ellos "
            f"y te daré una explicación detallada.\n\n"
            f"Ejemplo: \"¿qué es la ram?\" o \"¿qué es la purga?\""
        )

    return (
        "No detecté conceptos técnicos específicos en tu nota.\n\n"
        "Si tu nota menciona RAM, CPU, disco, purga, jaulas, criogenia, "
        "hyper-focus u otros temas de Kortex, puedo explicártelos. "
        "Pregúntame directamente: \"¿qué es X?\""
    )


def _extraer_contenido(mensaje: str) -> str:
    """Extrae el contenido del mensaje (todo después del primer \\n\\n)."""
    partes = mensaje.split("\n\n", 1)
    if len(partes) > 1:
        return partes[1].strip()
    return ""


# --- Función principal ---

def responder(mensaje: str, contexto: dict) -> str:
    """Responde al mensaje usando la base de conocimiento y el contexto.

    Detecta acciones de IA (resumir, mejorar, explicar) antes de
    buscar en la base de conocimiento.
    """
    texto = mensaje.lower().strip()

    if texto.startswith("resume esto"):
        return _accion_resumir(mensaje)
    if texto.startswith("mejora la redacción") or texto.startswith("mejora la redaccion"):
        return _accion_mejorar(mensaje)
    if texto.startswith("explica los conceptos"):
        return _accion_explicar(mensaje)

    intencion = detectar_intencion(mensaje)

    if intencion == "diagnostico":
        return diagnosticar(contexto)

    if intencion == "pregunta":
        respuesta = buscar_conocimiento(mensaje)
        if respuesta:
            return respuesta

    if intencion == "comando":
        return (
            "No reconocí el comando exacto. Prueba con frases como:\n\n"
            "- 'diagnostica mi pc'\n"
            "- 'purga la ram'\n"
            "- 'acelera internet'\n"
            "- 'modo supervivencia' / 'modo gaming' / 'desactiva modo'\n"
            "- 'congela [app]' / 'descongela todo'\n"
            "- 'abre thorium' / 'detecta basura'"
        )

    respuesta = buscar_conocimiento(mensaje)
    if respuesta:
        return respuesta

    return (
        "No tengo información específica sobre eso en mi base de "
        "conocimiento local.\n\n"
        "Puedes preguntarme sobre:\n"
        "- RAM, CPU, disco, swap\n"
        "- Cómo optimizar el sistema\n"
        "- Purga, jaulas, criogenia, hyper-focus\n"
        "- Qué es Kortex y en qué se diferencia\n"
        "- Privacidad y datos\n\n"
        "También puedes decir 'diagnostica mi PC' y hago un análisis "
        "rápido del estado actual."
    )