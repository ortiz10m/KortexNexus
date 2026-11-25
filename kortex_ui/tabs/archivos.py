"""Pestaña de Archivos de Kortex Nexus (100% thread-safe + Papelera y Multi-Distro)."""

from __future__ import annotations

import threading

import customtkinter as ctk

from kortex_core.files import KortexArchivos
from kortex_ui import notificaciones, tema


class TabArchivos(ctk.CTkFrame):
    """Pestaña de gestión de archivos, basura, duplicados, apps y papelera."""

    def __init__(self, master, gestor: KortexArchivos | None = None, **kwargs):
        kwargs.setdefault("fg_color", tema.COLOR_FONDO)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self.gestor = gestor or KortexArchivos()
        self._basura_detectada = []
        self._checks_basura = []

        self._construir_header()
        self._construir_tabs()
        self._construir_consola()

        self._actualizar_info_disco()
        self._refrescar_papelera()

    def _ui(self, fn):
        try:
            self.after(0, lambda: self.winfo_exists() and fn())
        except Exception:
            pass

    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=tema.ESP_XXXL, pady=(tema.ESP_XL, tema.ESP_MD))

        ctk.CTkLabel(
            header, text="Archivos y Limpieza",
            font=(tema.FUENTE_TITULO, tema.TAMANO_H1),
            text_color=tema.COLOR_TEXTO, anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Escanea espacio en disco, limpia basura con papelera recuperable y gestiona apps.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            text_color=tema.COLOR_TEXTO_SECUNDARIO, anchor="w",
        ).pack(anchor="w")

        disco = ctk.CTkFrame(self, fg_color="transparent")
        disco.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))
        disco.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="disco")

        self.lbl_total = self._mini_metrica(disco, 0, "Total", "—")
        self.lbl_usado = self._mini_metrica(disco, 1, "Usado", "—")
        self.lbl_libre = self._mini_metrica(disco, 2, "Libre", "—")

        self.barra_disco = ctk.CTkProgressBar(
            disco, progress_color=tema.COLOR_PRIMARIO, fg_color=tema.COLOR_BORDE,
            height=9, corner_radius=tema.RADIO_SM,
        )
        self.barra_disco.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(tema.ESP_SM, 0))
        self.barra_disco.set(0)

    def _mini_metrica(self, padre, columna: int, titulo: str, valor: str) -> ctk.CTkLabel:
        bloque = ctk.CTkFrame(padre, fg_color="transparent")
        bloque.grid(row=0, column=columna, sticky="w", padx=tema.ESP_SM)

        ctk.CTkLabel(
            bloque, text=titulo,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
        ).pack(anchor="w")

        lbl = ctk.CTkLabel(
            bloque, text=valor,
            font=(tema.FUENTE_TITULO, tema.TAMANO_H3),
            text_color=tema.COLOR_TEXTO, anchor="w",
        )
        lbl.pack(anchor="w")
        return lbl

    def _actualizar_info_disco(self):
        try:
            info = self.gestor.info_disco()
            if "error" not in info:
                self.lbl_total.configure(text=info["total_human"])
                self.lbl_usado.configure(text=info["usado_human"])
                self.lbl_libre.configure(text=info["libre_human"])
                self.barra_disco.set(min(1.0, max(0.0, info["porcentaje"] / 100.0)))
        except Exception:
            pass

    def _construir_tabs(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=tema.ESP_XXXL, pady=(0, tema.ESP_MD))

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

        self.tabs.add("Carpetas")
        self.tabs.add("Basura")
        self.tabs.add("Duplicados")
        self.tabs.add("Apps")
        self.tabs.add("Papelera")

        self._construir_tab_carpetas()
        self._construir_tab_basura()
        self._construir_tab_duplicados()
        self._construir_tab_apps()
        self._construir_tab_papelera()

    def _construir_tab_carpetas(self):
        tab = self.tabs.tab("Carpetas")
        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=tema.ESP_SM)

        self.entrada_ruta = ctk.CTkEntry(
            barra,
            placeholder_text="Ruta a escanear (vacío = carpeta del usuario)",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            fg_color=tema.COLOR_ELEVADO,
            border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO,
            height=36,
        )
        self.entrada_ruta.pack(side="left", fill="x", expand=True, padx=(0, tema.ESP_SM))

        ctk.CTkButton(
            barra, text="Escanear",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            corner_radius=tema.RADIO_MD, height=36, width=110,
            command=self._escanear_carpetas,
        ).pack(side="right")

        self.lista_carpetas = ctk.CTkScrollableFrame(tab, fg_color=tema.COLOR_FONDO, corner_radius=tema.RADIO_MD)
        self.lista_carpetas.pack(fill="both", expand=True, pady=(tema.ESP_XS, 0))

    def _construir_tab_basura(self):
        tab = self.tabs.tab("Basura")
        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=tema.ESP_SM)

        ctk.CTkButton(
            barra, text="Detectar basura",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            corner_radius=tema.RADIO_MD, height=36,
            command=self._detectar_basura,
        ).pack(side="left", padx=(0, tema.ESP_SM))

        ctk.CTkButton(
            barra, text="Enviar a Papelera",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_ERROR, hover_color="#DC2626",
            corner_radius=tema.RADIO_MD, height=36,
            command=self._limpiar_basura,
        ).pack(side="left", padx=(0, tema.ESP_SM))

        self.var_incluir_admin = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra, text="Incluir rutas de sistema (Admin)",
            variable=self.var_incluir_admin,
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            fg_color=tema.COLOR_PRIMARIO,
        ).pack(side="left", padx=tema.ESP_SM)

        ctk.CTkButton(
            barra, text="Seleccionar todo",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE_FUERTE,
            hover_color=tema.COLOR_ELEVADO_HOVER,
            corner_radius=tema.RADIO_MD, height=34,
            command=self._seleccionar_toda_basura,
        ).pack(side="right")

        self.lbl_basura_estado = ctk.CTkLabel(
            tab, text="Presiona 'Detectar basura' para analizar el sistema.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
        )
        self.lbl_basura_estado.pack(fill="x", pady=(0, tema.ESP_XS))

        self.lista_basura = ctk.CTkScrollableFrame(tab, fg_color=tema.COLOR_FONDO, corner_radius=tema.RADIO_MD)
        self.lista_basura.pack(fill="both", expand=True)

    def _construir_tab_duplicados(self):
        tab = self.tabs.tab("Duplicados")
        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=tema.ESP_SM)

        ctk.CTkButton(
            barra, text="Buscar duplicados",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            corner_radius=tema.RADIO_MD, height=36,
            command=self._buscar_duplicados,
        ).pack(side="left")

        self.lbl_duplicados_estado = ctk.CTkLabel(
            tab, text="Busca archivos repetidos (>= 1 MB) por hash MD5.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
        )
        self.lbl_duplicados_estado.pack(fill="x", pady=(0, tema.ESP_XS))

        self.lista_duplicados = ctk.CTkScrollableFrame(tab, fg_color=tema.COLOR_FONDO, corner_radius=tema.RADIO_MD)
        self.lista_duplicados.pack(fill="both", expand=True)

    def _construir_tab_apps(self):
        tab = self.tabs.tab("Apps")
        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=tema.ESP_SM)

        ctk.CTkButton(
            barra, text="Listar apps instaladas",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            corner_radius=tema.RADIO_MD, height=36,
            command=self._listar_apps,
        ).pack(side="left")

        self.lbl_apps_estado = ctk.CTkLabel(
            tab, text="Compatible con Windows y gestores de paquetes Linux.",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
        )
        self.lbl_apps_estado.pack(fill="x", pady=(0, tema.ESP_XS))

        self.lista_apps = ctk.CTkScrollableFrame(tab, fg_color=tema.COLOR_FONDO, corner_radius=tema.RADIO_MD)
        self.lista_apps.pack(fill="both", expand=True)

    def _construir_tab_papelera(self):
        tab = self.tabs.tab("Papelera")
        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=tema.ESP_SM)

        ctk.CTkButton(
            barra, text="Refrescar",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE_FUERTE,
            corner_radius=tema.RADIO_MD, height=34,
            command=self._refrescar_papelera,
        ).pack(side="left", padx=(0, tema.ESP_SM))

        ctk.CTkButton(
            barra, text="Vaciar papelera",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
            fg_color=tema.COLOR_ERROR, hover_color="#DC2626",
            corner_radius=tema.RADIO_MD, height=34,
            command=self._vaciar_papelera,
        ).pack(side="right")

        self.lbl_papelera_estado = ctk.CTkLabel(
            tab, text="Archivos movidos por Kortex (recuperables hasta 30 días).",
            font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
            text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w",
        )
        self.lbl_papelera_estado.pack(fill="x", pady=(0, tema.ESP_XS))

        self.lista_papelera = ctk.CTkScrollableFrame(tab, fg_color=tema.COLOR_FONDO, corner_radius=tema.RADIO_MD)
        self.lista_papelera.pack(fill="both", expand=True)

    def _construir_consola(self):
        self.consola = ctk.CTkTextbox(
            self,
            font=(tema.FUENTE_MONO, tema.TAMANO_PEQUENO),
            fg_color=tema.COLOR_SUPERFICIE,
            text_color=tema.COLOR_EXITO,
            corner_radius=tema.RADIO_MD,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            height=85,
        )
        self.consola.pack(fill="x", padx=tema.ESP_XXXL, pady=(0, tema.ESP_XL))
        self.consola.insert("0.0", ">>> Listo.\n")
        self.consola.configure(state="disabled")

    def _log(self, mensaje: str):
        self._ui(lambda: self._escribir_consola(mensaje))

    def _escribir_consola(self, mensaje: str):
        self.consola.configure(state="normal")
        self.consola.insert("end", f">>> {mensaje}\n")
        self.consola.see("end")
        self.consola.configure(state="disabled")

    # --- Carpetas ---

    def _escanear_carpetas(self):
        ruta = self.entrada_ruta.get().strip() or None
        self._log(f"Escaneando: {ruta or 'carpeta del usuario'}")
        self.gestor.escanear_disco(
            ruta_raiz=ruta,
            on_progreso=lambda p: self._log(f"  → {p}"),
            on_completo=lambda r: self._ui(lambda: self._mostrar_carpetas(r)),
        )

    def _mostrar_carpetas(self, resultado: list):
        for w in self.lista_carpetas.winfo_children():
            w.destroy()
        items = [r for r in resultado if r.get("profundidad", 0) <= 1][:50]
        for item in items:
            fila = ctk.CTkFrame(self.lista_carpetas, fg_color="transparent")
            fila.pack(fill="x", pady=1)
            ctk.CTkLabel(fila, text=f"📁  {item['nombre']}", font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO), text_color=tema.COLOR_TEXTO, anchor="w").pack(side="left", padx=tema.ESP_SM)
            ctk.CTkLabel(fila, text=f"{item['tamano_human']} · {item.get('num_archivos', 0)} archivos", font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO), text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="e").pack(side="right", padx=tema.ESP_SM)
        self._log(f"Escaneo completado: {len(resultado)} carpetas.")

    # --- Basura ---

    def _detectar_basura(self):
        self._log("Detectando basura...")
        self.lbl_basura_estado.configure(text="Detectando...")
        self.gestor.detectar_basura(
            incluir_admin=bool(self.var_incluir_admin.get()),
            on_progreso=lambda p: self._ui(lambda msg=str(p)[:80]: self.lbl_basura_estado.configure(text=msg)),
            on_completo=lambda b: self._ui(lambda: self._mostrar_basura(b)),
        )

    def _mostrar_basura(self, basura: list):
        for w in self.lista_basura.winfo_children():
            w.destroy()

        self._basura_detectada = basura
        self._checks_basura = []

        for item in basura[:200]:
            fila = ctk.CTkFrame(self.lista_basura, fg_color="transparent")
            fila.pack(fill="x", pady=1)

            var = ctk.BooleanVar(value=True)
            self._checks_basura.append({"var": var, "ruta": item["ruta"], "requiere_admin": item.get("requiere_admin", False)})

            ctk.CTkCheckBox(
                fila, text="", variable=var, width=20, checkbox_width=18, checkbox_height=18,
                fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
            ).pack(side="left", padx=(0, tema.ESP_SM))

            etiqueta = f"[Admin] {item['nombre']}" if item.get("requiere_admin") else item["nombre"]
            ctk.CTkLabel(fila, text=etiqueta[:58], font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO), text_color=tema.COLOR_TEXTO, anchor="w").pack(side="left")
            ctk.CTkLabel(fila, text=item["tamano_human"], font=(tema.FUENTE_MONO, tema.TAMANO_MICRO), text_color=tema.COLOR_ADVERTENCIA, anchor="e").pack(side="right", padx=tema.ESP_SM)

        total_mb = sum(x["tamano_bytes"] for x in basura) / (1024 * 1024)
        self.lbl_basura_estado.configure(text=f"{len(basura)} archivos detectados · {total_mb:.1f} MB liberables")
        self._log(f"Basura detectada: {len(basura)} archivos ({total_mb:.1f} MB).")

    def _seleccionar_toda_basura(self):
        if not self._checks_basura:
            return
        estado_actual = self._checks_basura[0]["var"].get()
        for item in self._checks_basura:
            item["var"].set(not estado_actual)

    def _limpiar_basura(self):
        if not self._checks_basura:
            self._log("No hay archivos seleccionados.")
            return

        rutas_normales = [i["ruta"] for i in self._checks_basura if i["var"].get() and not i["requiere_admin"]]
        rutas_admin = [i["ruta"] for i in self._checks_basura if i["var"].get() and i["requiere_admin"]]

        if not rutas_normales and not rutas_admin:
            self._log("Selecciona al menos un archivo.")
            return

        if rutas_normales:
            self._log(f"Moviendo {len(rutas_normales)} archivos a papelera segura...")
            self.gestor.limpiar_archivos(
                rutas=rutas_normales,
                on_progreso=lambda p: self._ui(lambda msg=str(p)[:80]: self.lbl_basura_estado.configure(text=msg)),
                on_completo=lambda res: self._ui(lambda: self._basura_limpiada(res)),
            )

        if rutas_admin:
            self._log(f"Solicitando elevación para limpiar {len(rutas_admin)} rutas de sistema...")
            threading.Thread(
                target=lambda: self.gestor.limpiar_archivos_como_admin(
                    rutas_admin,
                    on_completo=lambda res: self._ui(lambda: self._log(res.get("mensaje", ""))),
                ),
                daemon=True,
            ).start()

    def _basura_limpiada(self, resultado: dict):
        self._log(
            f"Listo: {resultado['eliminados']} archivos movidos a papelera ({resultado['espacio_liberado']})."
        )
        self.lbl_basura_estado.configure(
            text=f"✅ {resultado['eliminados']} movidos a papelera · {resultado['espacio_liberado']}"
        )
        self._actualizar_info_disco()
        self._refrescar_papelera()

    # --- Duplicados ---

    def _buscar_duplicados(self):
        self._log("Buscando duplicados...")
        self.lbl_duplicados_estado.configure(text="Buscando...")
        self.gestor.buscar_duplicados(
            tamano_minimo_mb=1.0,
            on_progreso=lambda p: self._ui(lambda msg=str(p)[:80]: self.lbl_duplicados_estado.configure(text=msg)),
            on_completo=lambda d: self._ui(lambda: self._mostrar_duplicados(d)),
        )

    def _mostrar_duplicados(self, duplicados: list):
        for w in self.lista_duplicados.winfo_children():
            w.destroy()
        if not duplicados:
            self.lbl_duplicados_estado.configure(text="✅ No se encontraron duplicados.")
            return

        for grupo in duplicados[:50]:
            bloque = ctk.CTkFrame(self.lista_duplicados, fg_color=tema.COLOR_ELEVADO, corner_radius=tema.RADIO_SM)
            bloque.pack(fill="x", pady=2, padx=2)
            ctk.CTkLabel(
                bloque,
                text=f"👥 {len(grupo['copias'])} copias · {grupo['tamano_human']} c/u · ahorro: {grupo['ahorro_posible']}",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO, "bold"),
                text_color=tema.COLOR_TEXTO, anchor="w",
            ).pack(anchor="w", padx=tema.ESP_SM, pady=(tema.ESP_SM, 0))
            for copia in grupo["copias"][:3]:
                ctk.CTkLabel(bloque, text=f"   {copia[-70:]}", font=(tema.FUENTE_MONO, tema.TAMANO_MICRO), text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="w").pack(anchor="w", padx=tema.ESP_SM)

        self.lbl_duplicados_estado.configure(text=f"{len(duplicados)} grupos encontrados.")
        self._log(f"Duplicados encontrados: {len(duplicados)} grupos.")

    # --- Apps ---

    def _listar_apps(self):
        self._log("Listando apps instaladas...")
        self.lbl_apps_estado.configure(text="Consultando gestor de paquetes / registro...")
        self.gestor.listar_apps(
            on_progreso=lambda p: self._ui(lambda msg=str(p)[:80]: self.lbl_apps_estado.configure(text=msg)),
            on_completo=lambda a: self._ui(lambda: self._mostrar_apps(a)),
        )

    def _mostrar_apps(self, apps: list):
        for w in self.lista_apps.winfo_children():
            w.destroy()

        for app in apps[:200]:
            fila = ctk.CTkFrame(self.lista_apps, fg_color="transparent")
            fila.pack(fill="x", pady=1)

            ctk.CTkLabel(
                fila, text=f"📦  {app['nombre'][:48]} ({app.get('origen', '')})",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_PEQUENO),
                text_color=tema.COLOR_TEXTO, anchor="w",
            ).pack(side="left")

            if app.get("cmd_desinstalar"):
                ctk.CTkButton(
                    fila, text="Desinstalar",
                    font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
                    fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE_FUERTE,
                    hover_color=tema.COLOR_ERROR, width=82, height=24,
                    command=lambda a=app: self._desinstalar_app(a),
                ).pack(side="right", padx=tema.ESP_XS)

            ctk.CTkLabel(
                fila, text=app.get("tamano_human", "—"),
                font=(tema.FUENTE_MONO, tema.TAMANO_MICRO),
                text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="e",
            ).pack(side="right", padx=tema.ESP_SM)

        self.lbl_apps_estado.configure(text=f"{len(apps)} apps encontradas.")
        self._log(f"Apps listadas: {len(apps)}.")

    def _desinstalar_app(self, app: dict):
        self._log(f"Desinstalando {app.get('nombre', '')}...")
        self.gestor.desinstalar_app(
            app,
            on_completo=lambda res: self._ui(lambda: self._post_desinstalar(res)),
        )

    def _post_desinstalar(self, res: dict):
        msg = res.get("mensaje", "")
        self._log(msg)
        notificaciones.notificar("exito" if res.get("exito") else "advertencia", "Apps", msg)
        if res.get("exito"):
            self._listar_apps()

    # --- Papelera ---

    def _refrescar_papelera(self):
        for w in self.lista_papelera.winfo_children():
            w.destroy()

        items = self.gestor.listar_papelera()
        self.lbl_papelera_estado.configure(text=f"{len(items)} elemento(s) en la papelera de recuperación.")

        for item in items[:150]:
            fila = ctk.CTkFrame(self.lista_papelera, fg_color="transparent")
            fila.pack(fill="x", pady=1)

            ctk.CTkLabel(
                fila, text=f"♻️  {item['nombre_original'][:45]}",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO),
                text_color=tema.COLOR_TEXTO, anchor="w",
            ).pack(side="left")

            ctk.CTkButton(
                fila, text="Restaurar",
                font=(tema.FUENTE_CUERPO, tema.TAMANO_MICRO, "bold"),
                fg_color=tema.COLOR_PRIMARIO, hover_color=tema.COLOR_PRIMARIO_HOVER,
                width=78, height=24,
                command=lambda item_id=item["id"]: self._restaurar_item(item_id),
            ).pack(side="right", padx=tema.ESP_XS)

            ctk.CTkLabel(
                fila, text=item.get("tamano_human", "—"),
                font=(tema.FUENTE_MONO, tema.TAMANO_MICRO),
                text_color=tema.COLOR_TEXTO_TERCIARIO, anchor="e",
            ).pack(side="right", padx=tema.ESP_SM)

    def _restaurar_item(self, item_id: str):
        ok = self.gestor.restaurar_de_papelera(item_id)
        if ok:
            self._log("Archivo restaurado a su ubicación original.")
            self._refrescar_papelera()
            self._actualizar_info_disco()
        else:
            self._log("No se pudo restaurar el archivo.")

    def _vaciar_papelera(self):
        res = self.gestor.vaciar_papelera(forzar_todo=True)
        self._log(f"Papelera vaciada: {res['eliminados']} elementos ({res['espacio_liberado']}).")
        self._refrescar_papelera()
        self._actualizar_info_disco()
