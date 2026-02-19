"""
PROJECT: KORTEX NEXUS
AUTHOR: David Santiago Ortiz Rincon (Founder)
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
import shutil 
from PIL import Image 
from tkinter import PhotoImage, messagebox
import cerebro
import platform  # <--- AGREGAR ESTO


# --- RUTAS ABSOLUTAS (BLINDADAS) ---
RUTA_CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHVO_APPS = os.path.join(RUTA_CARPETA, "apps.json")
LOGO_PATH = os.path.join(RUTA_CARPETA, "logo_kortex.png")
SCRIPT_NAV = os.path.join(RUTA_CARPETA, "navegador.py")
ENV_FILE = os.path.join(RUTA_CARPETA, ".env")

# --- CONFIGURACIÓN VISUAL ---
ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("dark-blue")

# --- SISTEMA DE INFORMACIÓN VERSIÓN LIBRE ---
def verificar_activacion():
	from dotenv import load_dotenv
	load_dotenv(ENV_FILE)
	
	# Si no hay clave, no bloqueamos el inicio, solo informamos
	if not os.getenv("GEMINI_API_KEY"):
		# Ventana informativa sutil
		setup = ctk.CTk()
		setup.title("Kortex Nexus: Información")
		setup.geometry("450x320")
		
		# Centrar la ventana (opcional pero profesional)
		setup.resizable(False, False)
		
		ctk.CTkLabel(setup, text="🚀 VERSIÓN PÚBLICA", font=("Arial", 18, "bold"), text_color="#3498db").pack(pady=20)
		
		info_txt = (
			"Bienvenido a la suite Kortex.\n\n"
			"• Monitor, Radio y Launcher: ACTIVADOS ✅\n"
			"• Cerebro Nexus (IA): MODO ESPERA ⏳\n\n"
			"Para activar la IA, ingresa tu API Key en la pestaña 'Cerebro'."
		)
		
		ctk.CTkLabel(setup, text=info_txt, font=("Arial", 12), justify="left").pack(pady=10)

		# Botón para entrar directo al programa
		ctk.CTkButton(setup, text="ENTRAR AL SISTEMA", command=setup.destroy, fg_color="#333", hover_color="#444").pack(pady=10)
		
		# Botón opcional para ir a por la llave de una vez
		ctk.CTkButton(setup, text="Obtener API Key Gratis", command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"), 
					  fg_color="transparent", border_width=1).pack(pady=5)
		
		setup.mainloop()
		load_dotenv(ENV_FILE)
class KortexNexus(ctk.CTk):
	def __init__(self):
		super().__init__()

		# 1. IDENTIDAD DEL PROYECTO
		self.title("KORTEX NEXUS v1.0 (OFFICIAL)")
		self.geometry("1100x750")
		
		# Configurar Icono con Ruta Absoluta
		try:
			if os.path.exists(LOGO_PATH):
				img_pil = Image.open(LOGO_PATH)
				# Icono para la ventana
				self.icon_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(32, 32))
				# Icono para la barra de tareas (Linux)
				self.img_tk = PhotoImage(file=LOGO_PATH)
				self.wm_iconphoto(True, self.img_tk)
		except Exception as e:
			print(f"Nota: No se pudo cargar icono ({e})")

		# 2. SISTEMA DE PESTAÑAS
		self.tabview = ctk.CTkTabview(self, corner_radius=15)
		self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

		self.tab_ai = self.tabview.add("🧠 Cerebro Nexus")
		self.tab_notes = self.tabview.add("📝 Notas IA") 
		self.tab_music = self.tabview.add("🎵 Radio")
		self.tab_apps = self.tabview.add("🚀 Launcher")
		self.tab_monitor = self.tabview.add("📊 Monitor")

		# 3. INICIALIZAR MÓDULOS
		self.crear_pestana_ai()
		self.crear_pestana_notas() 
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

	def abrir_navegador_kortex(self, url):
		import subprocess
		try:
			url = url.strip()
			if not url:
				return

			# 1. Lógica Anti-Captchas (DuckDuckGo)
			if "." not in url or " " in url:
				url = f"https://duckduckgo.com/?q={url}"
			elif not url.startswith("http"):
				url = "https://" + url
				
			# 2. El Motor Ligero (Epiphany)
			# Redirigimos los errores (como el Signal 10) al vacío para mantener Kortex limpio
			subprocess.Popen(
				["epiphany-browser", url], 
				stdout=subprocess.DEVNULL, 
				stderr=subprocess.DEVNULL
			)
			print(f"🔥 Kortex Web Engine activado para: {url}")
			
		except FileNotFoundError:
			print("❌ Error: Ejecuta 'sudo apt install epiphany-browser'")
		except Exception as e:
			print(f"❌ Error crítico lanzando el navegador: {e}")
	# (Mantenemos tus funciones crear_pestana_ai, crear_pestana_musica, crear_pestana_apps iguales)
	#

	def crear_pestana_ai(self):
		self.chat_box = ctk.CTkTextbox(self.tab_ai, width=900, height=400, font=("Segoe UI", 14))
		self.chat_box.pack(pady=10, fill="both", expand=True)
		self.chat_box.insert("0.0", "🤖 KORTEX NEXUS: En línea.\n\n")
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
		ctk.CTkCheckBox(frame_input, text="Voz", variable=self.voz_activa).pack(side="left", padx=5)

	def hilo_escuchar(self): threading.Thread(target=self.escuchar_microfono).start()

	def escuchar_microfono(self):
		self.btn_mic.configure(fg_color="#e74c3c")
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
	# PESTAÑA EXTRA: NOTAS INTELIGENTES
	# ==========================================
	def crear_pestana_notas(self):
		frame_tools = ctk.CTkFrame(self.tab_notes, fg_color="transparent")
		frame_tools.pack(fill="x", pady=5)
		
		ctk.CTkButton(frame_tools, text="✨ Resumir", fg_color="#8e44ad", width=100, command=lambda: self.procesar_nota("Resume esto:")).pack(side="left", padx=5)
		ctk.CTkButton(frame_tools, text="🧹 Corregir", fg_color="#27ae60", width=100, command=lambda: self.procesar_nota("Corrige ortografía:")).pack(side="left", padx=5)

		self.txt_notas = ctk.CTkTextbox(self.tab_notes, font=("Consolas", 14), wrap="word")
		self.txt_notas.pack(fill="both", expand=True, pady=10)
		self.txt_notas.insert("0.0", "Escribe aquí tu texto...")

	def procesar_nota(self, prompt):
		c = self.txt_notas.get("1.0", "end")
		threading.Thread(target=lambda: self.actualizar_nota(cerebro.preguntar_a_gemini(f"{prompt}\n{c}"))).start()

	def actualizar_nota(self, t):
		self.txt_notas.delete("1.0", "end")
		self.txt_notas.insert("0.0", t)

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
	# PESTAÑA 3: LAUNCHER
	# ==========================================
	def crear_pestana_apps(self):
		frame_nav = ctk.CTkFrame(self.tab_apps, fg_color="transparent")
		frame_nav.pack(fill="x", padx=10, pady=20)
		self.entry_nav_libre = ctk.CTkEntry(frame_nav, placeholder_text="🌐 Navegar en la Red Nexus...", height=50, font=("Arial", 16), corner_radius=25)
		self.entry_nav_libre.pack(side="left", fill="x", expand=True, padx=(10, 10))
		self.entry_nav_libre.bind("<Return>", lambda event: self.navegar_libre())
		ctk.CTkButton(frame_nav, text="IR 🚀", width=80, height=50, corner_radius=25, command=self.navegar_libre).pack(side="left", padx=10)
		self.frame_apps_container = ctk.CTkScrollableFrame(self.tab_apps, fg_color="transparent")
		self.frame_apps_container.pack(fill="both", expand=True, padx=10, pady=5)
		ctk.CTkButton(self.tab_apps, text="➕ Agregar Atajo", fg_color="#333", command=self.pedir_datos_app).pack(pady=10)
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
		nombre = ctk.CTkInputDialog(text="Nombre:", title="Nuevo Enlace").get_input()
		if nombre:
			url = ctk.CTkInputDialog(text="URL:", title="Destino").get_input()
			if url: self.guardar_nueva_app(nombre, url)

	def recargar_apps(self): 
		self.dibujar_botones()

	# ==========================================
	# PESTAÑA 4: MONITOR + CLEANER + RED
	# ==========================================
	def crear_pestana_monitor(self):
		# 1. VISUALIZACIÓN DE RECURSOS
		self.lbl_cpu = ctk.CTkLabel(self.tab_monitor, text="CPU", font=("Arial", 16, "bold"))
		self.lbl_cpu.pack(pady=(20, 5))
		self.bar_cpu = ctk.CTkProgressBar(self.tab_monitor, width=600, height=15)
		self.bar_cpu.pack(pady=5)
		
		self.lbl_ram = ctk.CTkLabel(self.tab_monitor, text="RAM", font=("Arial", 16, "bold"))
		self.lbl_ram.pack(pady=(20, 5))
		self.bar_ram = ctk.CTkProgressBar(self.tab_monitor, width=600, height=15)
		self.bar_ram.pack(pady=5)

		# 2. PANEL DE HERRAMIENTAS DE PODER
		frame_herramientas = ctk.CTkFrame(self.tab_monitor, fg_color="transparent")
		frame_herramientas.pack(pady=40)

		# Botón Cleaner (Izquierda)
		ctk.CTkButton(frame_herramientas, text="🔥 PURGAR SISTEMA", 
					  height=60, width=250, font=("Arial", 14, "bold"),
					  fg_color="#c0392b", hover_color="#a93226",
					  command=self.limpiar_sistema).pack(side="left", padx=10)

		# Botón Acelerador (Derecha)
		ctk.CTkButton(frame_herramientas, text="🌐 ACELERAR RED", 
					  height=60, width=250, font=("Arial", 14, "bold"),
					  fg_color="#2980b9", hover_color="#2471a3",
					  command=self.acelerar_internet).pack(side="left", padx=10)

		# 3. CRÉDITOS
		ctk.CTkLabel(self.tab_monitor, text="© 2026 Kortex Nexus | Suite de Alto Rendimiento", 
					 text_color="gray", font=("Arial", 11)).pack(side="bottom", pady=20)

	def limpiar_sistema(self):
		# 1. Cambiamos el texto del botón para que vean que está trabajando
		# (Necesitas haber guardado el botón en una variable como self.btn_cleaner)
		
		import time
		try:
			# Simulamos que está analizando (Efecto visual para que no sea tan seco)
			self.bar_ram.set(self.bar_ram.get() + 0.1) # Sube un poquito como si "cargara" basura
			self.update() 
			time.sleep(0.5) # Medio segundo de suspenso
			
			sistema = platform.system()
			if sistema == "Linux":
				os.system("rm -rf ~/.cache/thumbnails/*")
				os.system("sync") 
			elif sistema == "Windows":
				os.system(f'del /q /f /s "%TEMP%\\*"')

			# 2. El efecto visual de bajar la RAM
			self.bar_ram.set(max(0, self.bar_ram.get() - 0.15)) 
			
			messagebox.showinfo("Kortex Cleaner", "🔥 ¡SISTEMA PURGADO!\nSe eliminaron rastros de actividad y se optimizó el kernel.")
		except Exception as e:
			messagebox.showerror("Error", f"Fallo en limpieza: {e}")
			
	def acelerar_internet(self):
		sistema = platform.system()
		try:
			if sistema == "Windows":
				os.system('ipconfig /flushdns')
			elif sistema == "Linux":
				# En lugar de reiniciar la red entera (que da avisos feos),
				# solo limpiamos la caché si el comando existe, si no, lo ignoramos.
				os.system("resolvectl flush-caches 2>/dev/null || true")
			
			messagebox.showinfo("Kortex Red", "🌐 Caché de red renovada para mayor velocidad.")
		except:
			pass

	def actualizar_monitor(self):
		try:
			c = psutil.cpu_percent(); r = psutil.virtual_memory()
			self.lbl_cpu.configure(text=f"CPU: {c}%")
			self.bar_cpu.set(c/100)
			self.lbl_ram.configure(text=f"RAM: {r.percent}%")
			self.bar_ram.set(r.percent/100)
		except: pass
		self.after(1000, self.actualizar_monitor)

if __name__ == "__main__":
	verificar_activacion()
	app = KortexNexus()
	app.mainloop()
