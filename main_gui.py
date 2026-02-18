import customtkinter as ctk
import threading
import subprocess
import webbrowser
import psutil  # <--- NUEVA IMPORTACIÓN PARA EL MONITOR
import time
import cerebro

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class KortexApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KORTEX NEXUS v4.0 (SYSTEM MONITOR)")
        self.geometry("850x650")

        # Pestañas
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_ai = self.tabview.add("🧠 Cerebro")
        self.tab_music = self.tabview.add("🎵 Radio")
        self.tab_apps = self.tabview.add("🚀 Launcher")
        self.tab_monitor = self.tabview.add("📊 Monitor PC") # <--- NUEVA PESTAÑA

        self.crear_pestana_ai()
        self.crear_pestana_musica()
        self.crear_pestana_apps()
        self.crear_pestana_monitor() # <--- INICIAMOS EL MONITOR

        # Iniciar el ciclo de actualización del monitor (cada 1 segundo)
        self.actualizar_monitor()

    # ==========================================
    # PESTAÑA 4: MONITOR DE RECURSOS (NUEVO)
    # ==========================================
    def crear_pestana_monitor(self):
        self.lbl_mon = ctk.CTkLabel(self.tab_monitor, text="ESTADO DEL SISTEMA (HUD)", font=("Arial", 20, "bold"))
        self.lbl_mon.pack(pady=20)

        # Frame para organizar
        self.frame_stats = ctk.CTkFrame(self.tab_monitor)
        self.frame_stats.pack(fill="both", expand=True, padx=20, pady=10)

        # --- CPU ---
        self.lbl_cpu = ctk.CTkLabel(self.frame_stats, text="CPU: 0%", font=("Consolas", 16))
        self.lbl_cpu.pack(pady=5)
        self.bar_cpu = ctk.CTkProgressBar(self.frame_stats, width=400, progress_color="#00ff00") # Verde
        self.bar_cpu.pack(pady=5)
        self.bar_cpu.set(0)

        # --- RAM ---
        self.lbl_ram = ctk.CTkLabel(self.frame_stats, text="RAM: 0%", font=("Consolas", 16))
        self.lbl_ram.pack(pady=5)
        self.bar_ram = ctk.CTkProgressBar(self.frame_stats, width=400, progress_color="#ffa500") # Naranja
        self.bar_ram.pack(pady=5)
        self.bar_ram.set(0)

        # --- BATERÍA (Solo si aplica) ---
        self.lbl_bat = ctk.CTkLabel(self.frame_stats, text="Batería: --%", font=("Consolas", 16))
        self.lbl_bat.pack(pady=20)

    def actualizar_monitor(self):
        """Función que se llama a sí misma cada 1000ms (1 segundo)"""
        try:
            # 1. CPU
            cpu_val = psutil.cpu_percent()
            self.lbl_cpu.configure(text=f"CPU Uso: {cpu_val}%")
            self.bar_cpu.set(cpu_val / 100) # La barra va de 0.0 a 1.0

            # 2. RAM
            ram = psutil.virtual_memory()
            self.lbl_ram.configure(text=f"RAM Uso: {ram.percent}% ({round(ram.used/1024/1024/1024, 1)}GB)")
            self.bar_ram.set(ram.percent / 100)

            # Cambiar color de RAM si es crítico (>85%)
            if ram.percent > 85:
                self.bar_ram.configure(progress_color="red")
            else:
                self.bar_ram.configure(progress_color="#ffa500")

            # 3. Batería
            bat = psutil.sensors_battery()
            if bat:
                self.lbl_bat.configure(text=f"🔋 Batería: {bat.percent}% {'(Cargando)' if bat.power_plugged else ''}")
        
        except Exception as e:
            print(f"Error monitor: {e}")

        # Programar la próxima actualización en 1 segundo
        self.after(1000, self.actualizar_monitor)

    # ==========================================
    # CÓDIGO ANTERIOR (Resumido para que quepa)
    # ==========================================
    def crear_pestana_ai(self):
        self.chat_box = ctk.CTkTextbox(self.tab_ai, width=700, height=350)
        self.chat_box.pack(pady=10)
        self.chat_box.insert("0.0", "🤖 KORTEX: Monitor activado. ¿Preguntas?\n\n")
        self.chat_box.configure(state="disabled")
        
        frame_input = ctk.CTkFrame(self.tab_ai)
        frame_input.pack(pady=10)
        
        self.input_ai = ctk.CTkEntry(frame_input, placeholder_text="Pregunta aquí...", width=400)
        self.input_ai.pack(side="left", padx=10)
        self.btn_send_ai = ctk.CTkButton(frame_input, text="Enviar", command=self.hilo_preguntar_ia)
        self.btn_send_ai.pack(side="left")
        self.input_ai.bind("<Return>", lambda event: self.hilo_preguntar_ia())

    def crear_pestana_musica(self):
        self.lbl_music = ctk.CTkLabel(self.tab_music, text="Radio Lofi / Buscador", font=("Arial", 16))
        self.lbl_music.pack(pady=10)
        self.input_music = ctk.CTkEntry(self.tab_music, placeholder_text="Buscar música...", width=400)
        self.input_music.pack(pady=5)
        self.btn_buscar = ctk.CTkButton(self.tab_music, text="▶ Reproducir", command=self.hilo_buscar_musica)
        self.btn_buscar.pack(pady=10)
        self.btn_stop = ctk.CTkButton(self.tab_music, text="🛑 DETENER", fg_color="red", command=self.detener_musica)
        self.btn_stop.pack(pady=10)
        self.status_music = ctk.CTkLabel(self.tab_music, text="...", text_color="gray")
        self.status_music.pack()

    def crear_pestana_apps(self):
        self.frame_apps = ctk.CTkFrame(self.tab_apps)
        self.frame_apps.pack(pady=20, padx=20, fill="both")
        
        # Botones (puedes agregar más)
        btns = [
            ("🎨 Canva", "https://www.canva.com", "#333"),
            ("🎓 FET/Q10", "https://fet.edu.co", "green"),
            ("💬 WhatsApp", "https://web.whatsapp.com", "#25D366"),
            ("📧 Gmail", "https://gmail.com", "#EA4335"),
            ("🎵 YouTube", "https://youtube.com", "red")
        ]
        
        for i, (txt, url, color) in enumerate(btns):
            btn = ctk.CTkButton(self.frame_apps, text=txt, fg_color=color, command=lambda u=url: webbrowser.open(u))
            btn.grid(row=i//2, column=i%2, padx=20, pady=20, sticky="ew")

    # --- LÓGICA ---
    def hilo_preguntar_ia(self):
        p = self.input_ai.get()
        if not p: return
        self.input_ai.delete(0, "end")
        self.log_chat(f"👤 TÚ: {p}")
        threading.Thread(target=self.conectar_cerebro, args=(p,)).start()

    def conectar_cerebro(self, p):
        r = cerebro.preguntar_a_gemini(p)
        self.log_chat(f"🤖 KORTEX: {r}\n" + "-"*40)

    def log_chat(self, t):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"\n{t}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def hilo_buscar_musica(self):
        q = self.input_music.get()
        if not q: return
        self.status_music.configure(text=f"🔎 Buscando {q}...", text_color="yellow")
        threading.Thread(target=lambda: self.run_music(q)).start()

    def run_music(self, q):
        try:
            subprocess.run(["pkill", "mpv"])
            cmd = f'yt-dlp "ytsearch1:{q}" -o - | mpv - --no-video'
            self.status_music.configure(text=f"▶ Sonando: {q}", text_color="green")
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            self.status_music.configure(text="Error", text_color="red")

    def detener_musica(self):
        subprocess.run(["pkill", "mpv"])
        self.status_music.configure(text="🛑 Detenido", text_color="gray")

if __name__ == "__main__":
    app = KortexApp()
    app.mainloop()
