# Política de Seguridad — Kortex Nexus

## Garantías de privacidad y diseño seguro

Kortex Nexus está diseñado para operar **100% offline** y sin superficie de ataque innecesaria:

- **Cero conexiones salientes:** el núcleo (`kortex_core/`) y la interfaz (`kortex_ui/`) no importan ni utilizan librerías de red o HTTP (`requests`, `urllib`, `http`, `socket`, `aiohttp`, `httpx`).
- **Cero ejecución dinámica insegura:** no se utilizan `eval()`, `exec()`, `pickle.load()`, `os.system()` ni `subprocess(..., shell=True)`.
- **Protección de archivos y papelera:**
  - Bloqueo estricto de rutas críticas del sistema (`/etc`, `/usr`, `/proc`, `/sys`, `C:\Windows\System32`, etc.).
  - Rechazo sistemático de enlaces simbólicos (*symlinks*) durante escaneo y limpieza.
  - Defensa contra *path traversal* al mover archivos a la papelera interna (`~/.kortex_nexus/papelera/`).
  - En sistemas POSIX/Linux, la carpeta `~/.kortex_nexus` se crea con permisos `0700` (solo lectura/escritura para el propietario).
- **Seguridad en suspensión de procesos (`CryoEngine`):**
  - Lista blanca de procesos críticos de Windows y Linux, el PID propio de Kortex y toda su cadena de ancestros.
  - Restauración garantizada (`atexit` y cierre limpio) para evitar que cualquier aplicación quede suspendida.

## Verificación automatizada

El repositorio incluye auditoría estática por AST y pruebas de defensas en [`tests/test_security.py`](tests/test_security.py):

```bash
python -m unittest tests/test_security.py -v
```

## Reporte de vulnerabilidades

Si encuentras un fallo de seguridad o comportamiento inesperado en el manejo de archivos o privilegios, abre un *Issue* detallado en [github.com/ortiz10m/KortexNexus/issues](https://github.com/ortiz10m/KortexNexus/issues) indicando sistema operativo, versión y pasos para reproducirlo.
