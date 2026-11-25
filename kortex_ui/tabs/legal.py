"""Pestaña Legal de Kortex Nexus."""

from __future__ import annotations

import customtkinter as ctk

from kortex_ui import tema


VERSION = "2.0.0"

TEXTO_PRIVACIDAD = """POLÍTICA DE PRIVACIDAD — KORTEX NEXUS

Fecha de vigencia: 2026

Kortex Nexus es una aplicación de escritorio diseñada para ejecutarse de forma completamente local. No cuenta con servidores propios, cuentas de usuario, analítica ni sistemas de telemetría.

1. Información que no se recopila
   La aplicación no transmite ni comparte información fuera de tu equipo. No se recopilan datos personales, identificadores de hardware, direcciones IP, nombres de archivos, notas ni historial de uso.

2. Almacenamiento local
   Para operar, Kortex Nexus guarda archivos de configuración y registro exclusivamente en tu carpeta de usuario (~/.kortex_nexus/):
   - config.json: preferencias seleccionadas en Ajustes.
   - kortex_datos.csv: registro local de uso de RAM, CPU y Swap (puede desactivarse en Ajustes).
   - papelera/: elementos movidos por el limpiador con su registro de recuperación.
   - chat_historial.json: historial local de consultas (puede desactivarse en Ajustes).
   - notas/: notas creadas por el usuario en formato Markdown.
   - launcher_apps.json: accesos directos configurados en el Launcher.

   En sistemas Linux, esta carpeta se crea con permisos restringidos al propietario (0700).

3. Eliminación de datos
   Puedes borrar cualquier archivo local desde Ajustes -> Resetear Datos o eliminando manualmente la carpeta ~/.kortex_nexus/.
"""

TEXTO_TERMINOS = """TÉRMINOS DE USO Y LICENCIA — KORTEX NEXUS

Copyright (c) 2026 David Santiago Ortiz Rincón. Todos los derechos reservados.

Al instalar o utilizar Kortex Nexus aceptas las siguientes condiciones:

1. Licencia y propiedad intelectual
   Kortex Nexus y su código fuente son propiedad intelectual de David Santiago Ortiz Rincón. Se otorga una licencia gratuita, personal y no transferible para instalar y utilizar el software en equipos propios. No se permite la redistribución comercial, modificación no autorizada ni venta sin consentimiento previo por escrito del autor.

2. Permisos del sistema
   El programa funciona con permisos estándar de usuario. Ciertas acciones de optimización del sistema operativo (configuración de ZRAM, parámetros TCP, plan de energía o limpieza de archivos temporales del sistema) requieren privilegios de administrador o root y quedan a criterio del usuario.

3. Gestión de procesos y limpieza de archivos
   La suspensión automática de procesos en segundo plano excluye procesos críticos del sistema y la ventana activa, y reanuda los procesos suspendidos al volver a ellos o al cerrar la aplicación.
   Los archivos limpiados por el usuario se envían a una papelera interna con opción de restauración por 30 días. Aun así, es responsabilidad del usuario revisar lo seleccionado y mantener respaldos de sus archivos importantes.

4. Limitación de responsabilidad
   El software se entrega "tal cual", sin garantías expresas ni implícitas de funcionamiento ininterrumpido o idoneidad para un propósito particular. El autor no asume responsabilidad por pérdida de datos, incompatibilidades con software de terceros o uso indebido de permisos elevados.

5. Ley aplicable
   Estos términos se rigen por las leyes de la República de Colombia.
"""


class TabLegal(ctk.CTkFrame):
    """Pestaña de documentación legal, privacidad y licencia."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self._construir_header()
        self._construir_tabs()

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XL, tema.ESP_MD))

        ctk.CTkLabel(
            header, text="Legal",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H1),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text=f"Kortex Nexus v{VERSION} · Privacidad, términos de uso y licencia.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
        ).pack(anchor="w")

    def _construir_tabs(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_XL))

        self.tabs = ctk.CTkTabview(
            contenedor,
            fg_color=tema.COLOR_SUPERFICIE,
            segmented_button_fg_color=tema.COLOR_ELEVADO,
            segmented_button_selected_color=tema.COLOR_PRIMARIO,
            segmented_button_selected_hover_color=tema.COLOR_PRIMARIO_HOVER,
            segmented_button_unselected_color=tema.COLOR_ELEVADO,
            segmented_button_unselected_hover_color=tema.COLOR_ELEVADO_HOVER,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
        )
        self.tabs.pack(fill="both", expand=True)

        self.tabs.add("Sobre Kortex")
        self.tabs.add("Guía")
        self.tabs.add("Privacidad")
        self.tabs.add("Términos")
        self.tabs.add("Licencia")

        self._llenar("Sobre Kortex", self._texto_sobre())
        self._llenar("Guía", self._texto_guia())
        self._llenar("Privacidad", TEXTO_PRIVACIDAD)
        self._llenar("Términos", TEXTO_TERMINOS)
        self._llenar("Licencia", self._texto_licencia())

    def _llenar(self, nombre_tab: str, contenido: str):
        txt = ctk.CTkTextbox(
            self.tabs.tab(nombre_tab),
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            fg_color=tema.COLOR_FONDO,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            wrap="word",
        )
        txt.pack(fill="both", expand=True, padx=tema.ESP_MD, pady=tema.ESP_MD)
        txt.insert("0.0", contenido.strip() + "\n")
        txt.configure(state="disabled")

    def _texto_sobre(self) -> str:
        return f"""Kortex Nexus v{VERSION}

Herramienta de optimización y mantenimiento para equipos con recursos limitados (desde 1 GB de RAM) en Windows y Linux.

Funciones incluidas:
- Monitor: lectura real de RAM disponible, Swap/ZRAM, presión de memoria y suspensión de procesos inactivos.
- Modos: perfiles reversibles para Supervivencia (1-2 GB), Gaming, Streaming y Trabajo.
- Predicción: estimación de tendencia de consumo de memoria y CPU en tiempo real.
- Archivos: análisis de carpetas, limpieza de temporales con papelera recuperable, búsqueda de duplicados y listado de aplicaciones instaladas.
- Modo servicio (--daemon): ejecución en segundo plano sin interfaz gráfica para minimizar el consumo de memoria.

Requisitos mínimos: 1 GB de RAM, Windows 7/8/10/11 o Linux (Debian/Ubuntu, Arch, Fedora, openSUSE, Alpine, Void).

Autor: David Santiago Ortiz Rincón.
"""

    def _texto_guia(self) -> str:
        return """Guía básica de uso

1. Modo ligero en segundo plano
   Para equipos de 1 a 2 GB de RAM, activa el auto-inicio del servicio en Ajustes o ejecuta "kortex-daemon" (Linux) / "KortexNexus.exe --daemon" (Windows). Así la protección permanece activa sin mantener abierta la interfaz gráfica.

2. Modos de trabajo
   Desde la pestaña Modos puedes activar perfiles según tu actividad. Al desactivar un modo o cerrar Kortex, las prioridades y procesos suspendidos vuelven a su estado normal.

3. Limpieza con papelera
   Los archivos limpiados desde Archivos -> Basura se mueven a la pestaña Papelera y pueden restaurarse a su carpeta original durante 30 días.

4. Asistente local
   En la pestaña Cerebro puedes escribir comandos directos como "diagnostica mi pc", "purga la ram", "acelera internet", "modo supervivencia" o "congela <proceso>".
"""

    def _texto_licencia(self) -> str:
        return f"""Copyright (c) 2026 David Santiago Ortiz Rincón
Todos los derechos reservados.

Este software y su documentación asociada son propiedad intelectual de David Santiago Ortiz Rincón. Queda prohibida su copia, modificación, distribución comercial o venta sin autorización previa por escrito.

Componentes de terceros incluidos:
- Python 3 (PSF License)
- CustomTkinter (MIT License)
- psutil (BSD 3-Clause License)
- Pillow (MIT-CMU License)
- Plyer (MIT License)
"""
