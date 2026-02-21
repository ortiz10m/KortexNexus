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
import platform
import webbrowser
import cerebro  # Tu nuevo cerebro POO de IA Gratuita

# --- RUTAS ABSOLUTAS (BLINDADAS) ---
RUTA_CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHVO_APPS = os.path.join(RUTA_CARPETA, "apps.json")
LOGO_PATH = os.path.join(RUTA_CARPETA, "logo_kortex.png")

# --- CONFIGURACIÓN VISUAL ---
ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("dark-blue")

class KortexNexus(ctk.CTk):
	def __init__(self):
		super().__init__()

		# 1. IDENTIDAD DEL PROYECTO
		self.title("KORTEX NEXUS v1.0 (OFFICIAL)")
		self.geometry("1100x750")
		
		# 2. INICIALIZAR EL CEREBRO IA
		self.ia = cerebro.CerebroKortex()
		
		# Configurar Icono
		try:
			if os.path.exists(LOGO_PATH):
				img_pil = Image.open(LOGO_PATH)
				self.icon_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(32, 32))
				self.img_tk = PhotoImage(file=LOGO_PATH)
				self.wm_iconphoto(True, self.img_tk)
		except Exception as e:
			print(f"Nota: No se pudo cargar icono ({e})")

		# 3. SISTEMA DE PESTAÑAS (Estructura Intacta)
		self.tabview = ctk.CTkTabview(self, corner_radius=15)
		self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

		self.tab_ai = self.tabview.add("🧠 Cerebro Nexus")
		self.tab_notes = self.tabview.add("📝 Notas IA") 
		self.tab_music = self.tabview.add("🎵 Radio")
		self.tab_apps = self.tabview.add("🚀 Launcher")
		self.tab_monitor = self.tabview.add("📊 Monitor")

		# 4. INICIALIZAR MÓDULOS
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

	def guardar_nueva_app(self, nombre, url):
		apps = self.cargar_apps_db()
		apps.append({"nombre": nombre, "url": url, "color": "#8e44ad"})
		with open(ARCHVO_APPS, "w") as f:
			json.dump(apps, f)
		self.dibujar_botones()

	def abrir_navegador_kortex(self, url):
		"""Lanza el navegador optimizado en 2do plano sin congelar la UI (Multi-Threading)"""
		
		# 1. Creamos la función interna que hará el trabajo sucio
		def _tarea_pesada():
			try:
				target_url = url.strip()
				if not target_url: return

				# Lógica Anti-Captchas (DuckDuckGo)
				if "." not in target_url or " " in target_url:
					target_url = f"https://duckduckgo.com/?q={target_url}"
				elif not target_url.startswith("http"):
					target_url = "https://" + target_url
					
				# Evaluación Multiplataforma
				if platform.system() == "Windows":
					webbrowser.open(target_url) 
				else:
					# En LocOS/Linux usa tu motor ligero Epiphany sin bordes
					subprocess.Popen(["epiphany-browser", target_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
				
				print(f"🔥 Kortex Web Engine activado para: {target_url} (En Hilo Secundario)")
				
			except Exception as e:
				print(f"❌ Error lanzando el navegador: {e}")

		# 2. LA MAGIA: Mandamos a ejecutar esa tarea en un Hilo paralelo
		hilo_navegador = threading.Thread(target=_tarea_pesada)
		hilo_navegador.start()
	# ==========================================
	# PESTAÑA 1: CEREBRO IA 
	# ==========================================
	def crear_pestana_ai(self):
		self.chat_box = ctk.CTkTextbox(self.tab_ai, width=900, height=400, font=("Segoe UI", 14))
		self.chat_box.pack(pady=10, fill="both", expand=True)
		self.chat_box.insert("0.0", "🤖 KORTEX NEXUS: En línea y conectado a la red neuronal libre.\n\n")
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

	def conectar_cerebro(self, txt: str) -> None:
		"""
		Procesa la entrada del usuario y actualiza la UI asíncronamente (Streaming).
		Incluye filtro estricto para ignorar metadatos (ProviderInfo) de g4f.
		"""
		print(f"\n[INFO] Kortex Engine - Consultando a la red: '{txt}'")
		respuesta_completa = ""
		
		# 1. Inyección segura inicial
		self.after(0, lambda: self.inyectar_letra_ui("\n🤖 NEXUS: "))
		
		try:
			# 2. Consumo del generador de streaming
			for fragmento in self.ia.pensar_en_vivo(txt):
				
				# MAGIA ANTI-ERRORES: Solo permitimos que pase TEXTO (str). 
				# Ignoramos ProviderInfo o cualquier otro metadato.
				if fragmento and isinstance(fragmento, str): 
					respuesta_completa += fragmento
					print(fragmento, end="", flush=True) 
					
					# Inyectamos a la interfaz visual
					self.after(0, lambda f=fragmento: self.inyectar_letra_ui(f))
					
			print() 
			
			# 3. SISTEMA ANTI-FALLOS
			if not respuesta_completa.strip():
				error_msg = "❌ Error: La red neuronal está saturada y no devolvió texto."
				self.after(0, lambda: self.inyectar_letra_ui(error_msg))
				respuesta_completa = error_msg
				print(f"\n[ALERTA] {error_msg}")
				
		except Exception as e:
			error_msg = f"❌ Error fatal de conexión: {e}"
			self.after(0, lambda: self.inyectar_letra_ui(error_msg))
			respuesta_completa = error_msg

		# 4. Cerramos el mensaje visualmente
		self.after(0, lambda: self.inyectar_letra_ui("\n" + "-"*50 + "\n"))
		
		# 5. Ejecución del motor de audio final
		self.hablar_kortex(respuesta_completa, stream_completado=True)
		
		
	def hablar_kortex(self, texto: str, stream_completado: bool = False) -> None:
		"""
		Genera y reproduce el audio de la respuesta.
		Incluye un 'Kill Switch' para evitar que las voces se superpongan.
		"""
		if not stream_completado:
			self.log_chat(f"🤖 NEXUS: {texto}\n" + "-"*50)
		
		if self.voz_activa.get() and "❌" not in texto:
			try:
				# 1. KILL SWITCH: Matamos cualquier voz de Kortex que esté sonando ahora mismo
				if platform.system() == "Linux":
					# Usamos -f para matar SOLO la voz, dejando la Radio Nexus intacta
					subprocess.run(["pkill", "-f", "kortex_voz.mp3"], stderr=subprocess.DEVNULL)
				elif platform.system() == "Windows":
					# En Windows es más complejo matar el 'start', pero lo intentamos con reproductores comunes
					os.system("taskkill /F /IM wmplayer.exe /T >nul 2>&1") 

				# 2. Generamos el archivo de audio con gTTS
				archivo = cerebro.generar_audio(texto)
				
				# 3. Reproducimos el nuevo audio
				if archivo: 
					if platform.system() == "Windows":
						os.system(f'start /min "" "{archivo}"') 
					else:
						subprocess.run(["mpv", "--no-video", archivo]) 
			except Exception as e:
				print(f"Nota: TTS fallando ({e})")

	def log_chat(self, t: str) -> None:
		"""
		Registra mensajes completos en el historial de la IA.
		"""
		self.chat_box.configure(state="normal")
		self.chat_box.insert("end", f"\n{t}\n")
		self.chat_box.see("end")
		self.chat_box.configure(state="disabled")

	def inyectar_letra_ui(self, letra: str) -> None:
		"""
		Inyecta un solo caracter en la caja de texto en tiempo real.
		Método seguro para interactuar con CustomTkinter desde un Hilo.
		"""
		self.chat_box.configure(state="normal")
		self.chat_box.insert("end", letra)
		self.chat_box.see("end")
		self.chat_box.configure(state="disabled")

	# ==========================================
	# PESTAÑA 2: NOTAS INTELIGENTES 
	# ==========================================
	def crear_pestana_notas(self):
		frame_tools = ctk.CTkFrame(self.tab_notes, fg_color="transparent")
		frame_tools.pack(fill="x", pady=5)
		
		ctk.CTkButton(frame_tools, text="✨ Resumir", fg_color="#8e44ad", width=100, command=lambda: self.procesar_nota("Resume esto de forma concisa:")).pack(side="left", padx=5)
		ctk.CTkButton(frame_tools, text="🧹 Corregir", fg_color="#27ae60", width=100, command=lambda: self.procesar_nota("Corrige la ortografía y redacción de este texto:")).pack(side="left", padx=5)

		self.txt_notas = ctk.CTkTextbox(self.tab_notes, font=("Consolas", 14), wrap="word")
		self.txt_notas.pack(fill="both", expand=True, pady=10)
		self.txt_notas.insert("0.0", "Escribe aquí tu texto...")

	def procesar_nota(self, prompt):
		c = self.txt_notas.get("1.0", "end").strip()
		if not c or c == "Escribe aquí tu texto...": return
		threading.Thread(target=lambda: self.actualizar_nota(self.ia.pensar(f"{prompt}\n\n{c}"))).start()

	def actualizar_nota(self, t):
		self.txt_notas.delete("1.0", "end")
		self.txt_notas.insert("0.0", t)

	# ==========================================
	# PESTAÑA 3: MÚSICA
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
		if not q: return
		self.status_music.configure(text=f"🔎 Buscando '{q}'...", text_color="#3498db")
		threading.Thread(target=lambda: self.run_music(q)).start()

	def run_music(self, q):
		subprocess.run(["pkill", "mpv"])
		cmd = f'yt-dlp "ytsearch1:{q}" -o - | mpv - --no-video'
		self.status_music.configure(text=f"▶ Transmitiendo: {q}", text_color="#2ecc71")
		subprocess.Popen(cmd, shell=True)

	# ==========================================
	# PESTAÑA 4: LAUNCHER
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

	# ==========================================
	# PESTAÑA 5: MONITOR + CLEANER
	# ==========================================
	def crear_pestana_monitor(self):
		self.lbl_cpu = ctk.CTkLabel(self.tab_monitor, text="CPU", font=("Arial", 16, "bold"))
		self.lbl_cpu.pack(pady=(20, 5))
		self.bar_cpu = ctk.CTkProgressBar(self.tab_monitor, width=600, height=15)
		self.bar_cpu.pack(pady=5)
		
		self.lbl_ram = ctk.CTkLabel(self.tab_monitor, text="RAM", font=("Arial", 16, "bold"))
		self.lbl_ram.pack(pady=(20, 5))
		self.bar_ram = ctk.CTkProgressBar(self.tab_monitor, width=600, height=15)
		self.bar_ram.pack(pady=5)

		frame_herramientas = ctk.CTkFrame(self.tab_monitor, fg_color="transparent")
		frame_herramientas.pack(pady=40)

		ctk.CTkButton(frame_herramientas, text="🔥 PURGAR SISTEMA", 
					  height=60, width=250, font=("Arial", 14, "bold"),
					  fg_color="#c0392b", hover_color="#a93226",
					  command=self.limpiar_sistema).pack(side="left", padx=10)

		ctk.CTkButton(frame_herramientas, text="🌐 ACELERAR RED", 
					  height=60, width=250, font=("Arial", 14, "bold"),
					  fg_color="#2980b9", hover_color="#2471a3",
					  command=self.acelerar_internet).pack(side="left", padx=10)

		ctk.CTkLabel(self.tab_monitor, text="© 2026 Kortex Nexus | Suite de Alto Rendimiento", 
					 text_color="gray", font=("Arial", 11)).pack(side="bottom", pady=20)

	def limpiar_sistema(self):
		"""Purga la caché del sistema y libera RAM inactiva de Python en 2do plano"""
		def _tarea_limpieza():
			import gc
			try:
				# 1. Purgamos la memoria interna de Kortex (Garbage Collector)
				gc.collect()

				# 2. Limpieza pesada del Sistema Operativo
				sistema = platform.system()
				if sistema == "Linux":
					os.system("rm -rf ~/.cache/thumbnails/*")
					os.system("sync") 
				elif sistema == "Windows":
					os.system(f'del /q /f /s "%TEMP%\\*" >nul 2>&1')

				# 3. Segunda purga profunda tras ejecutar los comandos
				gc.collect()

				messagebox.showinfo("Kortex Cleaner", "🔥 ¡SISTEMA PURGADO!\nSe eliminaron rastros y se obligó al sistema a liberar memoria.")
			except Exception as e:
				messagebox.showerror("Error", f"Fallo en limpieza: {e}")

		# Lanzamos al trabajador en segundo plano para NO congelar la interfaz
		hilo_limpieza = threading.Thread(target=_tarea_limpieza)
		hilo_limpieza.start()
			
	def acelerar_internet(self):
		sistema = platform.system()
		try:
			if sistema == "Windows":
				os.system('ipconfig /flushdns')
			elif sistema == "Linux":
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

# ==========================================
# PUNTO DE ARRANQUE DIRECTO (SIN SPLASH SCREEN)
# ==========================================
if __name__ == "__main__":
	app = KortexNexus()
	app.mainloop()
