"""Pestaña de Launcher de Kortex Nexus (detección inteligente de navegador y apps)."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from kortex_core.config import SISTEMA, obtener_carpeta_boveda, obtener_dir_recursos, obtener_home_usuario_real
from kortex_ui import tema
from modules.browser.thorium_kiosk import ThoriumKiosk


CARPETA_KORTEX = obtener_carpeta_boveda()
ARCHIVO_APPS = CARPETA_KORTEX / "launcher_apps.json"


def limpiar_comando_desktop(exec_line: str) -> str:
    """Extrae el binario ejecutable real desde la línea Exec= de un archivo .desktop."""
    if not exec_line:
        return ""
    try:
        tokens = shlex.split(exec_line)
    except ValueError:
        tokens = exec_line.split()

    limpios = [t for t in tokens if not t.startswith("%")]
    if not limpios:
        return ""
    if limpios[0] == "env":
        for tok in limpios[1:]:
            if "=" not in tok:
                return tok
    return limpios[0]


def iniciales_para(nombre: str) -> str:
    """Genera un monograma limpio de 1-2 letras para tarjetas de apps (sin emojis)."""
    partes = [p for p in nombre.strip().split() if p and p[0].isalnum()]
    if not partes:
        return "A"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


class TabLauncher(ctk.CTkFrame):
    """Launcher con detección inteligente de navegador optimizado y grid de apps."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        CARPETA_KORTEX.mkdir(parents=True, exist_ok=True)
        self.apps = self._cargar_apps()
        self.kiosk = ThoriumKiosk()
        self._logo_nav = None

        self._construir_header()
        self._construir_busqueda()
        self._construir_navegador()
        self._construir_apps()

    def _cargar_apps(self) -> list:
        if not ARCHIVO_APPS.exists():
            return []
        try:
            data = json.loads(ARCHIVO_APPS.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _guardar_apps(self):
        try:
            ARCHIVO_APPS.write_text(json.dumps(self.apps, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XL, tema.ESP_MD))

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left")

        ctk.CTkLabel(info, text="Launcher", font=(tema.FUENTE_TITULO, tema.TAMANO_H1), text_color=tema.COLOR_TEXTO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text="Navegador optimizado por RAM y acceso directo a tus aplicaciones.", font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO), text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w").pack(anchor="w")

        botones = ctk.CTkFrame(header, fg_color="transparent")
        botones.pack(side="right")

        ctk.CTkButton(
            botones, text="Detectar apps", font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE_FUERTE,
            hover_color=tema.COLOR_ELEVADO_HOVER, text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD, height=36, width=120,
            command=self._detectar_apps,
        ).pack(side="left", padx=(0, tema.ESP_SM))

        ctk.CTkButton(
            botones, text="Añadir app", font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO, corner_radius=tema.RADIO_MD, height=36, width=120,
            command=self._añadir_app,
        ).pack(side="left")

    def _construir_busqueda(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))

        self.entrada_busqueda = ctk.CTkEntry(
            contenedor,
            placeholder_text="Buscar en internet o escribir una URL...",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            fg_color=tema.COLOR_ELEVADO, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, corner_radius=tema.RADIO_MD, height=42,
        )
        self.entrada_busqueda.pack(fill="x")
        self.entrada_busqueda.bind("<Return>", lambda e: self._buscar_en_thorium())

    def _construir_navegador(self):
        card = ctk.CTkFrame(
            self, fg_color=tema.COLOR_ELEVADO, corner_radius=tema.RADIO_LG,
            border_width=1, border_color=tema.COLOR_PRIMARIO,
        )
        card.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_LG))

        interior = ctk.CTkFrame(card, fg_color="transparent")
        interior.pack(fill="x", padx=tema.ESP_LG, pady=tema.ESP_LG)

        ruta_logo = obtener_dir_recursos() / "logo_kortex.png"
        if ruta_logo.exists():
            try:
                from PIL import Image

                img = Image.open(ruta_logo)
                self._logo_nav = ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
                ctk.CTkLabel(interior, text="", image=self._logo_nav).pack(side="left", padx=(0, tema.ESP_LG))
            except Exception:
                pass

        nav = self.kiosk.info_navegador()
        nombre_nav = nav.get("nombre", "Navegador del sistema")
        if nav.get("es_chromium"):
            subtexto = "Lanzamiento con límites de memoria V8 y procesos ajustados a tu RAM."
        else:
            subtexto = "Navegador detectado automáticamente en el sistema."

        info = ctk.CTkFrame(interior, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(info, text="Navegador optimizado", font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO, "bold"), text_color=tema.COLOR_PRIMARIO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=nombre_nav, font=(tema.FUENTE_TITULO, tema.TAMANO_H2), text_color=tema.COLOR_TEXTO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=subtexto, font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO), text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w").pack(anchor="w")

        self.btn_thorium = ctk.CTkButton(
            interior,
            text=f"Abrir {nombre_nav}" if len(nombre_nav) <= 14 else "Abrir navegador",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO, "bold"),
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO, corner_radius=tema.RADIO_MD,
            height=42, width=180,
            command=self._abrir_thorium,
        )
        self.btn_thorium.pack(side="right")

    def _construir_apps(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_XL))

        ctk.CTkLabel(contenedor, text="Tus aplicaciones", font=(tema.FUENTE_TITULO, tema.TAMANO_H3), text_color=tema.COLOR_TEXTO, anchor="w").pack(anchor="w", pady=(0, tema.ESP_SM))

        self.grid_apps = ctk.CTkScrollableFrame(contenedor, fg_color="transparent", corner_radius=0)
        self.grid_apps.pack(fill="both", expand=True)
        self.grid_apps.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="app")

        self._refrescar_grid()

    def _refrescar_grid(self):
        if not self.winfo_exists():
            return
        for w in self.grid_apps.winfo_children():
            w.destroy()

        if not self.apps:
            contenedor = ctk.CTkFrame(self.grid_apps, fg_color="transparent")
            contenedor.grid(row=0, column=0, columnspan=5, pady=30)
            ctk.CTkLabel(contenedor, text="Aún no hay aplicaciones añadidas.", font=(tema.FUENTE_TITULO, tema.TAMANO_H3), text_color=tema.COLOR_TEXTO).pack(pady=(tema.ESP_SM, tema.ESP_XS))
            ctk.CTkLabel(contenedor, text="Usa 'Detectar apps' o 'Añadir app' para crear tus accesos.", font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO), text_color=tema.COLOR_TEXTO_TERCIARIO).pack()
            return

        for i, app in enumerate(self.apps):
            self._tarjeta_app(self.grid_apps, i // 5, i % 5, app)

    def _tarjeta_app(self, padre, fila: int, columna: int, app: dict):
        card = ctk.CTkFrame(padre, fg_color=tema.COLOR_ELEVADO, corner_radius=tema.RADIO_MD, border_width=1, border_color=tema.COLOR_BORDE, height=112)
        card.grid(row=fila, column=columna, padx=tema.ESP_SM, pady=tema.ESP_SM, sticky="nsew")
        card.grid_propagate(False)

        monograma = iniciales_para(app.get("nombre", "App"))
        ctk.CTkButton(
            card, text=monograma, font=(tema.FUENTE_TITULO, 22),
            fg_color=tema.COLOR_SUPERFICIE, hover_color=tema.COLOR_ELEVADO_HOVER,
            text_color=tema.COLOR_PRIMARIO, corner_radius=tema.RADIO_SM, height=58,
            command=lambda a=app: self._abrir_app(a),
        ).pack(fill="x", padx=tema.ESP_SM, pady=(tema.ESP_SM, 0))

        ctk.CTkLabel(card, text=app.get("nombre", "")[:17], font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO, "bold"), text_color=tema.COLOR_TEXTO).pack(pady=(tema.ESP_XS, 0))

        ctk.CTkButton(
            card, text="x", font=(tema.FUENTE_CUERPO, 10), fg_color="transparent",
            hover_color=tema.COLOR_ERROR, text_color=tema.COLOR_TEXTO_TERCIARIO,
            width=18, height=18, corner_radius=9,
            command=lambda a=app: self._eliminar_app(a),
        ).place(relx=0.92, rely=0.11, anchor="center")

    # --- Acciones ---

    def _abrir_thorium(self, url: str | None = None):
        threading.Thread(target=lambda: self.kiosk.launch(url=url), daemon=True).start()

    def _buscar_en_thorium(self):
        texto = self.entrada_busqueda.get().strip()
        if not texto:
            return
        if texto.startswith(("http://", "https://")):
            url = texto
        elif "." in texto and " " not in texto:
            url = f"https://{texto}"
        else:
            url = f"https://www.google.com/search?q={texto.replace(' ', '+')}"
        self._abrir_thorium(url)
        self.entrada_busqueda.delete(0, "end")

    def _abrir_app(self, app: dict):
        ruta = app.get("ruta", "")
        if not ruta:
            return
        try:
            if SISTEMA == "Windows":
                if ruta.lower().endswith(".exe"):
                    subprocess.Popen([ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.startfile(ruta)
            else:
                subprocess.Popen([ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Launcher] Error abriendo {app.get('nombre')}: {e}")

    def _eliminar_app(self, app: dict):
        self.apps = [a for a in self.apps if a.get("ruta") != app.get("ruta")]
        self._guardar_apps()
        self._refrescar_grid()

    def _añadir_app(self):
        tipos = [("Ejecutables", "*.exe *.lnk *.bat *.cmd"), ("Todos los archivos", "*.*")] if SISTEMA == "Windows" else [("Todos los archivos", "*.*")]
        ruta = filedialog.askopenfilename(title="Selecciona una app", filetypes=tipos)
        if not ruta:
            return
        nombre = Path(ruta).stem
        self.apps.append({"nombre": nombre, "ruta": ruta})
        self._guardar_apps()
        self._refrescar_grid()

    def _detectar_apps(self):
        for w in self.grid_apps.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.grid_apps, text="Detectando aplicaciones...", font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO), text_color=tema.COLOR_TEXTO_TERCIARIO).grid(row=0, column=0, columnspan=5, pady=30)
        threading.Thread(target=self._detectar_en_hilo, daemon=True).start()

    def _detectar_en_hilo(self):
        try:
            apps = self._detectar_windows() if SISTEMA == "Windows" else (self._detectar_linux() if SISTEMA == "Linux" else [])
            rutas_existentes = {a.get("ruta") for a in self.apps}
            for app in apps:
                if app.get("ruta") not in rutas_existentes:
                    self.apps.append(app)
            self._guardar_apps()
        except Exception as e:
            print(f"[Launcher] Error detectando: {e}")
        self.after(0, self._refrescar_grid)

    def _detectar_windows(self) -> list:
        apps = []
        menus = [
            Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        ]
        ignorar = ("uninstall", "desinstalar", "readme", "help", "ayuda", "manual", "website", "release notes")
        for menu in menus:
            if not menu.exists():
                continue
            try:
                for lnk in menu.rglob("*.lnk"):
                    nombre = lnk.stem
                    if any(x in nombre.lower() for x in ignorar):
                        continue
                    apps.append({"nombre": nombre, "ruta": str(lnk)})
            except Exception:
                continue

        vistos = set()
        unicos = []
        for app in apps:
            if app["nombre"] not in vistos:
                vistos.add(app["nombre"])
                unicos.append(app)
        unicos.sort(key=lambda x: x["nombre"].lower())
        return unicos[:25]

    def _detectar_linux(self) -> list:
        apps = []
        home = obtener_home_usuario_real()
        rutas = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            home / ".local/share/applications",
            Path("/var/lib/flatpak/exports/share/applications"),
            home / ".local/share/flatpak/exports/share/applications",
        ]
        vistos = set()
        for ruta in rutas:
            if not ruta.exists():
                continue
            try:
                for archivo in ruta.glob("*.desktop"):
                    info = self._parsear_desktop(archivo)
                    if not info or info.get("NoDisplay", "").lower() == "true" or info.get("Type", "") != "Application":
                        continue
                    nombre = info.get("Name", "")
                    comando = limpiar_comando_desktop(info.get("Exec", ""))
                    if not nombre or not comando or nombre in vistos:
                        continue
                    vistos.add(nombre)
                    apps.append({"nombre": nombre, "ruta": comando})
            except Exception:
                continue
        apps.sort(key=lambda x: x["nombre"].lower())
        return apps[:25]

    def _parsear_desktop(self, ruta: Path) -> dict:
        try:
            info = {}
            in_entry = False
            for linea in ruta.read_text(encoding="utf-8", errors="ignore").splitlines():
                linea = linea.strip()
                if linea == "[Desktop Entry]":
                    in_entry = True
                    continue
                if linea.startswith("["):
                    in_entry = False
                    continue
                if in_entry and "=" in linea:
                    k, v = linea.split("=", 1)
                    info[k.strip()] = v.strip()
            return info
        except Exception:
            return {}
