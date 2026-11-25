"""Pestaña de Notas de Kortex Nexus.

Editor markdown con preview en vivo, IA integrada, tags personalizables,
búsqueda, auto-guardado y exportación.
"""

import json
import re
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from kortex_ui import tema


CARPETA_NOTAS = Path.home() / ".kortex_nexus" / "notas"
ARCHIVO_META = Path.home() / ".kortex_nexus" / "notas_meta.json"


class TabNotas(ctk.CTkFrame):
    """Pestaña de notas con editor markdown y IA integrada."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self.cerebro = None
        self._cargar_cerebro()

        CARPETA_NOTAS.mkdir(parents=True, exist_ok=True)

        self.nota_actual = None
        self.notas = {}
        self._cambios_pendientes = False

        self._cargar_todas_las_notas()
        self._construir_header()
        self._construir_layout()
        self._iniciar_auto_guardado()

    def _cargar_cerebro(self):
        try:
            from cerebro import CerebroKortex
            self.cerebro = CerebroKortex()
        except Exception:
            self.cerebro = None

    def _cargar_todas_las_notas(self):
        self.notas = {}
        meta = {}
        if ARCHIVO_META.exists():
            try:
                with open(ARCHIVO_META, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}

        for archivo in CARPETA_NOTAS.glob("*.md"):
            nota_id = archivo.stem
            try:
                contenido = archivo.read_text(encoding="utf-8")
            except Exception:
                contenido = ""
            info = meta.get(nota_id, {})
            self.notas[nota_id] = {
                "titulo": info.get("titulo", nota_id),
                "tags": info.get("tags", []),
                "creada": info.get("creada", ""),
                "modificada": info.get("modificada", ""),
                "contenido": contenido,
                "ruta": archivo,
            }

    def _guardar_meta(self):
        meta = {}
        for nota_id, nota in self.notas.items():
            meta[nota_id] = {
                "titulo": nota["titulo"],
                "tags": nota["tags"],
                "creada": nota["creada"],
                "modificada": nota["modificada"],
            }
        try:
            ARCHIVO_META.parent.mkdir(parents=True, exist_ok=True)
            with open(ARCHIVO_META, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _guardar_nota(self, nota_id: str):
        if nota_id not in self.notas:
            return
        nota = self.notas[nota_id]
        try:
            nota["ruta"].write_text(nota["contenido"], encoding="utf-8")
            nota["modificada"] = datetime.now().isoformat()
            self._guardar_meta()
        except Exception as e:
            print(f"[Notas] Error guardando: {e}")

    def _crear_nota(self) -> str:
        ahora = datetime.now()
        nota_id = f"{ahora.strftime('%Y%m%d_%H%M%S')}_nueva"
        ruta = CARPETA_NOTAS / f"{nota_id}.md"
        ruta.write_text("", encoding="utf-8")
        self.notas[nota_id] = {
            "titulo": "Nueva nota",
            "tags": [],
            "creada": ahora.isoformat(),
            "modificada": ahora.isoformat(),
            "contenido": "",
            "ruta": ruta,
        }
        self._guardar_meta()
        return nota_id

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XXL, tema.ESP_LG))

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left")

        ctk.CTkLabel(
            info,
            text="Notas",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H1),
            text_color=tema.COLOR_TEXTO,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            info,
            text="Editor markdown con IA, tags y auto-guardado.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO,
            anchor="w",
        ).pack(anchor="w", pady=(tema.ESP_XS, 0))

        ctk.CTkButton(
            header,
            text="+ Nueva nota",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO, "bold"),
            fg_color=tema.COLOR_PRIMARIO,
            hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            height=40,
            width=140,
            command=self._nueva_nota,
        ).pack(side="right")

    def _construir_layout(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_XXL))
        contenedor.grid_columnconfigure(1, weight=1)
        contenedor.grid_rowconfigure(0, weight=1)

        self._construir_sidebar(contenedor)
        self._construir_editor(contenedor)

        if self.notas:
            primer_id = sorted(self.notas.keys(), reverse=True)[0]
            self._abrir_nota(primer_id)
        else:
            self._nueva_nota()

    def _construir_sidebar(self, padre):
        sidebar = ctk.CTkFrame(
            padre,
            fg_color=tema.COLOR_SUPERFICIE,
            corner_radius=tema.RADIO_MD,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            width=260,
        )
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, tema.ESP_MD))
        sidebar.grid_propagate(False)

        ctk.CTkEntry(
            sidebar,
            placeholder_text="🔍  Buscar...",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            fg_color=tema.COLOR_ELEVADO,
            border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_SM,
            height=36,
        ).pack(fill="x", padx=tema.ESP_MD, pady=(tema.ESP_MD, tema.ESP_SM))

        self.lista_notas = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            corner_radius=0,
        )
        self.lista_notas.pack(fill="both", expand=True, padx=tema.ESP_SM, pady=(0, tema.ESP_MD))

        self._refrescar_lista_notas()

    def _refrescar_lista_notas(self):
        for w in self.lista_notas.winfo_children():
            w.destroy()

        if not self.notas:
            ctk.CTkLabel(
                self.lista_notas,
                text="Sin notas todavía.",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
                text_color=tema.COLOR_TEXTO_TERCIARIO,
            ).pack(pady=tema.ESP_MD)
            return

        for nota_id in sorted(self.notas.keys(), reverse=True):
            nota = self.notas[nota_id]
            activa = nota_id == self.nota_actual

            boton = ctk.CTkButton(
                self.lista_notas,
                text=f"  📄  {nota['titulo'][:30]}",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
                anchor="w",
                height=36,
                corner_radius=tema.RADIO_SM,
                fg_color=tema.COLOR_ELEVADO if activa else "transparent",
                hover_color=tema.COLOR_ELEVADO_HOVER,
                text_color=tema.COLOR_PRIMARIO if activa else tema.COLOR_TEXTO_SECUNDARIO,
                command=lambda n=nota_id: self._abrir_nota(n),
            )
            boton.pack(fill="x", pady=2)

    def _construir_editor(self, padre):
        editor = ctk.CTkFrame(
            padre,
            fg_color=tema.COLOR_SUPERFICIE,
            corner_radius=tema.RADIO_MD,
            border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        editor.grid(row=0, column=1, sticky="nsew")

        self.entrada_titulo = ctk.CTkEntry(
            editor,
            placeholder_text="Título de la nota...",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H3),
            fg_color="transparent",
            border_width=0,
            text_color=tema.COLOR_TEXTO,
            height=44,
        )
        self.entrada_titulo.pack(fill="x", padx=tema.ESP_LG, pady=(tema.ESP_MD, tema.ESP_SM))
        self.entrada_titulo.bind("<KeyRelease>", self._on_titulo_cambio)

        ctk.CTkFrame(editor, fg_color=tema.COLOR_BORDE, height=1).pack(fill="x", padx=tema.ESP_LG)

        split = ctk.CTkFrame(editor, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=tema.ESP_LG, pady=tema.ESP_MD)
        split.grid_columnconfigure((0, 1), weight=1, uniform="split")
        split.grid_rowconfigure(0, weight=1)

        self.txt_editor = ctk.CTkTextbox(
            split,
            font=(tema.FUENTE_MONO, tema.TAMANO_CUERPO),
            fg_color=tema.COLOR_ELEVADO,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_SM,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            wrap="word",
        )
        self.txt_editor.grid(row=0, column=0, sticky="nsew", padx=(0, tema.ESP_SM))
        self.txt_editor.bind("<KeyRelease>", self._on_contenido_cambio)

        self.txt_preview = ctk.CTkTextbox(
            split,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            fg_color=tema.COLOR_ELEVADO,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_SM,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            wrap="word",
        )
        self.txt_preview.grid(row=0, column=1, sticky="nsew", padx=(tema.ESP_SM, 0))
        self.txt_preview.configure(state="disabled")

        barra = ctk.CTkFrame(editor, fg_color="transparent")
        barra.pack(fill="x", padx=tema.ESP_LG, pady=(0, tema.ESP_MD))

        ctk.CTkButton(
            barra,
            text="🤖  IA",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            fg_color=tema.COLOR_PRIMARIO,
            hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_SM,
            height=32,
            width=90,
            command=self._mostrar_menu_ia,
        ).pack(side="left", padx=(0, tema.ESP_SM))

        ctk.CTkButton(
            barra,
            text="📤  Exportar",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            fg_color="transparent",
            border_width=1,
            border_color=tema.COLOR_BORDE_FUERTE,
            hover_color=tema.COLOR_ELEVADO_HOVER,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_SM,
            height=32,
            width=120,
            command=self._exportar,
        ).pack(side="left", padx=(0, tema.ESP_SM))

        self.lbl_guardado = ctk.CTkLabel(
            barra,
            text="",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO,
        )
        self.lbl_guardado.pack(side="left")

        self.lbl_stats = ctk.CTkLabel(
            barra,
            text="",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO,
        )
        self.lbl_stats.pack(side="right")

    def _nueva_nota(self):
        self._guardar_si_cambiado()
        nota_id = self._crear_nota()
        self._abrir_nota(nota_id)
        self._refrescar_lista_notas()

    def _abrir_nota(self, nota_id: str):
        if nota_id not in self.notas:
            return

        self._guardar_si_cambiado()
        self.nota_actual = nota_id
        nota = self.notas[nota_id]

        self.entrada_titulo.delete(0, "end")
        self.entrada_titulo.insert(0, nota["titulo"])

        self.txt_editor.delete("1.0", "end")
        self.txt_editor.insert("1.0", nota["contenido"])

        self._actualizar_preview()
        self._actualizar_stats()
        self._refrescar_lista_notas()

    def _on_titulo_cambio(self, event=None):
        if not self.nota_actual:
            return
        nuevo = self.entrada_titulo.get().strip() or "Sin título"
        self.notas[self.nota_actual]["titulo"] = nuevo
        self._marcar_cambio()

    def _on_contenido_cambio(self, event=None):
        if not self.nota_actual:
            return
        contenido = self.txt_editor.get("1.0", "end-1c")
        self.notas[self.nota_actual]["contenido"] = contenido
        self._actualizar_preview()
        self._actualizar_stats()
        self._marcar_cambio()

    def _marcar_cambio(self):
        self._cambios_pendientes = True
        self.lbl_guardado.configure(text="● Cambios sin guardar", text_color=tema.COLOR_ADVERTENCIA)

    def _guardar_si_cambiado(self):
        if self._cambios_pendientes and self.nota_actual:
            self._guardar_nota(self.nota_actual)
            self._cambios_pendientes = False
            self.lbl_guardado.configure(text="✓ Guardado", text_color=tema.COLOR_EXITO)

    def _iniciar_auto_guardado(self):
        self._guardar_si_cambiado()
        self.after(5000, self._iniciar_auto_guardado)

    def _actualizar_preview(self):
        contenido = self.txt_editor.get("1.0", "end-1c")
        render = self._render_markdown(contenido)

        self.txt_preview.configure(state="normal")
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", render)
        self.txt_preview.configure(state="disabled")

    def _render_markdown(self, texto: str) -> str:
        """Convierte markdown a texto plano (render mínimo)."""
        lineas = texto.split("\n")
        resultado = []

        for linea in lineas:
            if linea.startswith("# "):
                resultado.append(linea[2:].upper())
                resultado.append("=" * len(linea[2:]))
            elif linea.startswith("## "):
                resultado.append(linea[3:])
                resultado.append("-" * len(linea[3:]))
            elif linea.startswith("### "):
                resultado.append(linea[4:])
            elif linea.startswith("- ") or linea.startswith("* "):
                resultado.append(f"  • {linea[2:]}")
            elif linea.startswith("> "):
                resultado.append(f"  │ {linea[2:]}")
            else:
                resultado.append(linea)

        texto_final = "\n".join(resultado)

        texto_final = re.sub(r"\*\*(.+?)\*\*", r"\1", texto_final)
        texto_final = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", texto_final)
        texto_final = re.sub(r"`(.+?)`", r"\1", texto_final)
        texto_final = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", texto_final)
        texto_final = re.sub(r"~~(.+?)~~", r"\1", texto_final)

        return texto_final

    def _actualizar_stats(self):
        contenido = self.txt_editor.get("1.0", "end-1c")
        palabras = len(contenido.split())
        caracteres = len(contenido)
        minutos = max(1, round(palabras / 200))
        self.lbl_stats.configure(
            text=f"{palabras} palabras · {caracteres} caracteres · {minutos} min de lectura"
        )

    def _mostrar_menu_ia(self):
        menu = ctk.CTkToplevel(self)
        menu.title("Acciones IA")
        menu.geometry("280x220")
        menu.configure(fg_color=tema.COLOR_FONDO)
        menu.resizable(False, False)
        menu.attributes("-topmost", True)

        ctk.CTkLabel(
            menu,
            text="¿Qué quieres hacer?",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H3),
            text_color=tema.COLOR_TEXTO,
        ).pack(pady=(tema.ESP_LG, tema.ESP_MD))

        for texto, accion in [
            ("Resumir", "resume"),
            ("Mejorar redacción", "mejora"),
            ("Explicar conceptos", "explica"),
        ]:
            ctk.CTkButton(
                menu,
                text=texto,
                font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
                fg_color=tema.COLOR_PRIMARIO,
                hover_color=tema.COLOR_PRIMARIO_HOVER,
                text_color=tema.COLOR_TEXTO,
                corner_radius=tema.RADIO_MD,
                height=36,
                command=lambda a=accion, m=menu: (m.destroy(), self._accion_ia(a)),
            ).pack(fill="x", padx=tema.ESP_LG, pady=tema.ESP_XS)

    def _accion_ia(self, accion: str):
        contenido = self.txt_editor.get("1.0", "end-1c").strip()
        if not contenido or not self.cerebro:
            return

        prompts = {
            "resume": f"Resume esto de forma concisa:\n\n{contenido}",
            "mejora": f"Mejora la redacción de este texto sin cambiar el significado:\n\n{contenido}",
            "explica": f"Explica los conceptos clave de este texto:\n\n{contenido}",
        }
        prompt = prompts.get(accion)
        if not prompt:
            return

        self.lbl_guardado.configure(text="🤖 Procesando...", text_color=tema.COLOR_PRIMARIO)

        def _procesar():
            try:
                respuesta = self.cerebro.pensar(prompt)
                self.after(0, lambda: self._mostrar_resultado_ia(respuesta))
            except Exception as e:
                self.after(0, lambda: self.lbl_guardado.configure(
                    text=f"Error: {e}", text_color=tema.COLOR_ERROR
                ))

        threading.Thread(target=_procesar, daemon=True).start()

    def _mostrar_resultado_ia(self, respuesta: str):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Respuesta de Kortex")
        ventana.geometry("600x400")
        ventana.configure(fg_color=tema.COLOR_FONDO)
        ventana.attributes("-topmost", True)

        ctk.CTkLabel(
            ventana,
            text="🤖  Kortex",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H3),
            text_color=tema.COLOR_PRIMARIO,
        ).pack(anchor="w", padx=tema.ESP_LG, pady=(tema.ESP_LG, tema.ESP_SM))

        txt = ctk.CTkTextbox(
            ventana,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            fg_color=tema.COLOR_ELEVADO,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            wrap="word",
        )
        txt.pack(fill="both", expand=True, padx=tema.ESP_LG, pady=(0, tema.ESP_MD))
        txt.insert("1.0", respuesta)

        ctk.CTkButton(
            ventana,
            text="Copiar al portapapeles",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_CUERPO),
            fg_color=tema.COLOR_PRIMARIO,
            hover_color=tema.COLOR_PRIMARIO_HOVER,
            text_color=tema.COLOR_TEXTO,
            corner_radius=tema.RADIO_MD,
            height=40,
            command=lambda: self._copiar_al_portapapeles(respuesta),
        ).pack(fill="x", padx=tema.ESP_LG, pady=(0, tema.ESP_LG))

        self.lbl_guardado.configure(text="✓ Listo", text_color=tema.COLOR_EXITO)

    def _copiar_al_portapapeles(self, texto: str):
        try:
            self.clipboard_clear()
            self.clipboard_append(texto)
        except Exception:
            pass

    def _exportar(self):
        contenido = self.txt_editor.get("1.0", "end-1c").strip()
        if not contenido:
            return

        try:
            escritorio = Path.home() / "Desktop"
            escritorio.mkdir(exist_ok=True)
            titulo = self.entrada_titulo.get().strip() or "nota"
            titulo_seguro = re.sub(r'[<>:"/\\|?*]', "_", titulo)
            ruta = escritorio / f"{titulo_seguro}.md"
            ruta.write_text(contenido, encoding="utf-8")
            self.lbl_guardado.configure(text=f"✓ Exportado a {ruta.name}", text_color=tema.COLOR_EXITO)
        except Exception as e:
            self.lbl_guardado.configure(text=f"Error: {e}", text_color=tema.COLOR_ERROR)