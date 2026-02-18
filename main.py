"""
PROJECT: KORTEX NEXUS
AUTHOR: David (Founder)
YEAR: 2026
LICENSE: Proprietary / MIT
DESCRIPTION: AI-Powered Productivity Suite for Low-End Hardware.
"""

import customtkinter as ctk
import threading
import subprocess
import psutil
import speech_recognition as sr
import os
import sys
import json
from PIL import Image # Necesario para el icono
import cerebro

# --- CONFIGURACIÓN VISUAL ---
ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("dark-blue")

ARCHVO_APPS = "apps.json"
LOGO_PATH = "logo_kortex.png" # Asegúrate de haber generado el logo

class KortexNexus(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. IDENTIDAD DEL PROYECTO
        self.title("KORTEX NEXUS v1.0 (OFFICIAL)")
        self.geometry("1100x750")
        
        # Configurar Icono de Ventana (Funciona en Linux y Windows)
        try:
            if os.path.exists(LOGO_PATH):
                imagen_icono = Image.open(LOGO_PATH)
                self.iconphoto(False, ctk.CTkImage(imagen_icono))
        except Exception as e:
            print(f"Nota: No se pudo cargar icono ({e})")

        # 2. SISTEMA DE PESTAÑAS
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_ai = self.tabview.add("🧠 Cerebro Nexus")
        self.tab_music = self.tabview.add("🎵 Radio")
        self.tab_apps = self.tabview.add("🚀 Launcher")
        self.tab_monitor = self.tabview.add("📊 Monitor")

        # 3. INICIALIZAR MÓDULOS
        self.crear_pestana_ai()
        self.crear_pestana_musica()
        self.crear_pestana_apps()
        self.crear_pestana_monitor()
        
        self.actualizar_monitor()

    # ==========================================
    # SISTEMA: BASE DE DATOS Y NAVEGADOR
    # ==========================================
    def cargar_apps_db(self):
        if not os.path.exists(ARCHVO_APPS):
            datos_default = [
                {"nombre": "Google", "url": "google.com", "color": "#4285F4"},
                {"nombre": "YouTube", "url": "youtube.com", "color": "#FF0000"}
            ]
            with open(ARCHVO_APPS, "w") as f:
                json.dump(datos_default, f)
            return datos_default
        try:
            with open(ARCHVO_APPS, "r") as f:
                return json.load(f)
        except: return []

    def guardar_nueva_app(self, nombre, url):
        apps = self.cargar_apps_db()
        apps.append({"nombre": nombre, "url": url, "color": "#333333"})
        with open(ARCHVO_APPS, "w") as f:
            json.dump(apps, f)
        self.recargar_apps()

    def abrir_navegador_kortex(self, url):
        """Lanza el navegador Kortex Pro en proceso independiente"""
        try:
            if not url.startswith("http") and not url.startswith("www"):
                url = f"https://www.google.com/search?q={url}"
            elif not url.startswith("http"):
                url = "https://" + url
                
            subprocess.Popen([sys.executable, "navegador.py", url])
        except Exception as e:
            print(f"Error lanzando browser: {e}")

    # ==========================================
    # PESTAÑA 1: CEREBRO NEXUS
    # ==========================================
    def crear_pestana_ai(self):
        self.chat_box = ctk.CTkTextbox(self.tab_ai, width=900, height=400, font=("Segoe UI", 14))
        self.chat_box.pack(pady=10, fill="both", expand=True)
        self.chat_box.insert("0.0", "🤖 KORTEX NEXUS: En línea. Esperando instrucciones.\n\n")
        self.chat_box.configure(state="disabled")

        frame_input = ctk.CTkFrame(self.tab_ai, fg_color="transparent")
        frame_input.pack(pady=10, fill="x", padx=10)
        
        self.btn_mic = ctk.CTkButton(frame_input, text="🎤", width=50, fg_color="#333", command=self.hilo_escuchar)
        self.btn_mic.pack(side="left", padx=5)

        self.input_ai = ctk.CTkEntry(frame_input, placeholder_text="Habla con Nexus...", height=40, corner_radius=20)
        self.input_ai.pack(side="left", fill="x", expand=True, padx=5)
        self.input_ai.bind("<Return>", lambda event: self.hilo_preguntar_ia())
        
        self.btn_send_ai = ctk.CTkButton(frame_input, text="Enviar", width=80, height=40, corner_radius=20, command=self.hilo_preguntar_ia)
        self.btn_send_ai.pack(side="left", padx=5)
        
        self.voz_activa = ctk.BooleanVar(value=True)
        self.chk_voz = ctk.CTkCheckBox(frame_input, text="Voz", variable=self.voz_activa)
        self.chk_voz.pack(side="left", padx=5)

    def hilo_escuchar(self): threading.Thread(target=self.escuchar_microfono).start()

    def escuchar_microfono(self):
        self.btn_mic.configure(fg_color="#e74c3c")
        self.input_ai.delete(0, "end")
        self.input_ai.insert(0, "Escuchando...")
        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source)
                audio = r.listen(source, timeout=5)
                texto = r.recognize_google(audio, language="es-ES")
                self.input_ai.delete(0, "end")
                self.input_ai.insert(0, texto)
                self.hilo_preguntar_ia()
        except: 
            self.input_ai.delete(0, "end")
            self.input_ai.insert(0, "...")
        self.btn_mic.configure(fg_color="#333")

    def hilo_preguntar_ia(self):
        texto = self.input_ai.get()
        if not texto or texto == "Escuchando...": return
        self.input_ai.delete(0, "end")
        self.log_chat(f"👤 TÚ: {texto}")
        
        cmd = texto.lower()
        if "abrir" in cmd:
            app = cmd.replace("abrir", "").strip()
            self.hablar_kortex(f"Iniciando módulo: {app}")
            self.abrir_navegador_kortex(app)
            return
        elif "reproduce" in cmd:
            song = cmd.replace("reproduce", "").strip()
            self.hablar_kortex(f"Sintonizando: {song}")
            self.tabview.set("🎵 Radio")
            self.input_music.delete(0, "end")
            self.input_music.insert(0, song)
            self.hilo_buscar_musica()
            return
            
        threading.Thread(target=self.conectar_cerebro, args=(texto,)).start()

    def conectar_cerebro(self, txt):
        res = cerebro.preguntar_a_gemini(txt)
        self.hablar_kortex(res)

    def hablar_kortex(self, texto):
        self.log_chat(f"🤖 NEXUS: {texto}\n" + "-"*50)
        if self.voz_activa.get() and "❌" not in texto:
            archivo = cerebro.generar_audio(texto)
            if archivo: subprocess.run(["mpv", "--no-video", archivo])

    def log_chat(self, t):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"\n{t}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    # ==========================================
    # PESTAÑA 2: MÚSICA
    # ==========================================
    def crear_pestana_musica(self):
        self.lbl_music = ctk.CTkLabel(self.tab_music, text="Radio Nexus", font=("Arial", 20, "bold"))
        self.lbl_music.pack(pady=20)
        
        self.input_music = ctk.CTkEntry(self.tab_music, placeholder_text="Buscar frecuencia...", width=400, height=40, corner_radius=20)
        self.input_music.pack(pady=10)
        
        frame_ctl = ctk.CTkFrame(self.tab_music, fg_color="transparent")
        frame_ctl.pack(pady=10)
        
        ctk.CTkButton(frame_ctl, text="▶ Play", width=100, command=self.hilo_buscar_musica).pack(side="left", padx=10)
        ctk.CTkButton(frame_ctl, text="⏹ Stop", width=100, fg_color="#e74c3c", command=lambda: subprocess.run(["pkill","mpv"])).pack(side="left", padx=10)
        
        self.status_music = ctk.CTkLabel(self.tab_music, text="En espera...", text_color="gray")
        self.status_music.pack(pady=20)

    def hilo_buscar_musica(self):
        q = self.input_music.get()
        self.status_music.configure(text=f"🔎 Buscando '{q}'...", text_color="#3498db")
        threading.Thread(target=lambda: self.run_music(q)).start()

    def run_music(self, q):
        subprocess.run(["pkill", "mpv"])
        cmd = f'yt-dlp "ytsearch1:{q}" -o - | mpv - --no-video'
        self.status_music.configure(text=f"▶ Transmitiendo: {q}", text_color="#2ecc71")
        subprocess.Popen(cmd, shell=True)

    # ==========================================
    # PESTAÑA 3: LAUNCHER (NAVEGACIÓN LIBRE)
    # ==========================================
    def crear_pestana_apps(self):
        frame_nav = ctk.CTkFrame(self.tab_apps, fg_color="transparent")
        frame_nav.pack(fill="x", padx=10, pady=20)

        self.entry_nav_libre = ctk.CTkEntry(frame_nav, placeholder_text="🌐 Navegar en la Red Nexus...", height=50, font=("Arial", 16), corner_radius=25)
        self.entry_nav_libre.pack(side="left", fill="x", expand=True, padx=(10, 10))
        self.entry_nav_libre.bind("<Return>", lambda event: self.navegar_libre())

        btn_ir = ctk.CTkButton(frame_nav, text="IR 🚀", width=80, height=50, corner_radius=25, command=self.navegar_libre)
        btn_ir.pack(side="left", padx=10)

        ctk.CTkLabel(self.tab_apps, text="ACCESOS DIRECTOS", font=("Arial", 12, "bold"), text_color="gray").pack(pady=10)

        self.frame_apps_container = ctk.CTkScrollableFrame(self.tab_apps, fg_color="transparent")
        self.frame_apps_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        btn_add = ctk.CTkButton(self.tab_apps, text="➕ Agregar Atajo", fg_color="#333", command=self.pedir_datos_app)
        btn_add.pack(pady=10)

        self.dibujar_botones()

    def navegar_libre(self):
        busqueda = self.entry_nav_libre.get()
        if busqueda:
            self.abrir_navegador_kortex(busqueda)
            self.entry_nav_libre.delete(0, "end")

    def dibujar_botones(self):
        for widget in self.frame_apps_container.winfo_children(): widget.destroy()
        apps = self.cargar_apps_db()
        cols = 3
        for i, app in enumerate(apps):
            btn = ctk.CTkButton(self.frame_apps_container, text=app["nombre"], fg_color=app.get("color", "#333"), 
                                height=80, font=("Arial", 14, "bold"), corner_radius=15,
                                command=lambda u=app["url"]: self.abrir_navegador_kortex(u))
            btn.grid(row=i//cols, column=i%cols, padx=10, pady=10, sticky="ew")
        for c in range(cols): self.frame_apps_container.grid_columnconfigure(c, weight=1)

    def pedir_datos_app(self):
        dialog = ctk.CTkInputDialog(text="Nombre:", title="Nuevo Enlace")
        nombre = dialog.get_input()
        if nombre:
            dialog2 = ctk.CTkInputDialog(text="URL:", title="Destino")
            url = dialog2.get_input()
            if url: self.guardar_nueva_app(nombre, url)

    def recargar_apps(self): self.dibujar_botones()

    # ==========================================
    # PESTAÑA 4: MONITOR
    # ==========================================
    def crear_pestana_monitor(self):
        self.lbl_cpu = ctk.CTkLabel(self.tab_monitor, text="CPU", font=("Arial", 16)); self.lbl_cpu.pack(pady=10)
        self.bar_cpu = ctk.CTkProgressBar(self.tab_monitor, width=500); self.bar_cpu.pack()
        self.lbl_ram = ctk.CTkLabel(self.tab_monitor, text="RAM", font=("Arial", 16)); self.lbl_ram.pack(pady=10)
        self.bar_ram = ctk.CTkProgressBar(self.tab_monitor, width=500); self.bar_ram.pack()
        
        # COPYRIGHT FOOTER (IMPORTANTE)
        ctk.CTkLabel(self.tab_monitor, text="© 2026 Kortex Nexus Dev Team - All Rights Reserved", 
                     text_color="gray", font=("Arial", 10)).pack(side="bottom", pady=20)

    def actualizar_monitor(self):
        try:
            c = psutil.cpu_percent(); r = psutil.virtual_memory()
            self.lbl_cpu.configure(text=f"CPU: {c}%")
            self.bar_cpu.set(c/100)
            self.lbl_ram.configure(text=f"RAM: {r.percent}%")
            self.bar_ram.set(r.percent/100)
            self.bar_ram.configure(progress_color="red" if r.percent > 85 else "#1f6aa5")
        except: pass
        self.after(1000, self.actualizar_monitor)

if __name__ == "__main__":
    app = KortexNexus()
    app.mainloop()
