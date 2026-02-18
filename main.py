from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Input, DataTable, Static, Log
import subprocess
import threading
import cerebro  # <--- AQUÍ IMPORTAMOS TU NUEVO MÓDULO

class KortexNexus(App):
    CSS = """
    Screen {
        background: #0d1117;
        color: #00ff00;
    }
    Header {
        background: #161b22;
        color: #00ff00;
        dock: top;
    }
    Input {
        dock: top;
        margin: 1;
        border: solid #00ff00;
        background: #0d1117;
        color: white;
    }
    DataTable {
        height: 1fr;
        border: solid #30363d;
    }
    Log {
        height: 1fr;
        border: solid #30363d;
        background: #0d1117;
        color: #c9d1d9;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(placeholder="Escribe '/ai pregunta' o busca música...")
        yield Vertical(
            DataTable(),
            Log()
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Duración", "Título")
        table.cursor_type = "row"
        self.title = "KORTEX NEXUS v2.0 (AI POWERED)"

    def reproducir_audio(self, url):
        """Función que corre en segundo plano para no congelar la app"""
        try:
            subprocess.run(["mpv", "--no-video", url])
        except Exception as e:
            pass # Si falla, falla en silencio

    def on_input_submitted(self, event: Input.Submitted) -> None:
        comando = event.value.strip()
        log = self.query_one(Log)
        input_box = self.query_one(Input)
        table = self.query_one(DataTable)

        if not comando: return
        input_box.value = ""

        # --- COMANDO DE SALIDA ---
        if comando == "salir":
            self.exit()
            return

        # --- COMANDO DE PARADA (Música) ---
        elif comando == "stop":
            log.write_line("🛑 Deteniendo música...")
            subprocess.run(["pkill", "mpv"])
            return

        # --- MODO INTELIGENCIA ARTIFICIAL (/ai) ---
        # Ejemplo: /ai que es linux
        elif comando.startswith("/ai "):
            pregunta = comando[4:] # Quitamos el "/ai "
            
            log.write_line(f"🧠 Kortex pensando: '{pregunta}'...")
            
            # Llamamos a tu archivo cerebro.py
            respuesta = cerebro.preguntar_a_gemini(pregunta)
            
            log.write_line("\n🤖 RESPUESTA:")
            log.write_line(respuesta)
            log.write_line("-" * 50)
            return

        # --- MODO BÚSQUEDA (Por defecto: YouTube) ---
        log.write_line(f"🔍 Buscando en YouTube: '{comando}'...")
        table.clear()

        def buscar_segundo_plano():
            try:
                # Usamos yt-dlp para buscar rápido sin descargar
                resultado = subprocess.check_output(
                    [
                        "yt-dlp", 
                        f"ytsearch5:{comando}", 
                        "--print", "%(id)s|%(duration_string)s|%(title)s",
                        "--flat-playlist"
                    ],
                    text=True
                )
                
                # Actualizamos la tabla en el hilo principal
                def actualizar_tabla():
                    for linea in resultado.strip().split("\n"):
                        if "|" in linea:
                            parts = linea.split("|")
                            if len(parts) >= 3:
                                vid_id = parts[0]
                                duracion = parts[1]
                                titulo = parts[2]
                                table.add_row(vid_id, duracion, titulo)
                    log.write_line("✅ Resultados listos.")
                    table.focus()
                
                self.call_from_thread(actualizar_tabla)

            except Exception as e:
                self.call_from_thread(log.write_line, f"❌ Error: {e}")

        # Lanzamos la búsqueda en un hilo aparte para que no se trabe
        threading.Thread(target=buscar_segundo_plano).start()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        log = self.query_one(Log)
        row = event.data_table.get_row_at(event.cursor_row)
        vid_id = row[0]
        titulo = row[2]
        
        url = f"https://www.youtube.com/watch?v={vid_id}"
        log.write_line(f"🎵 Reproduciendo: {titulo}")
        
        # Lanzar MPV en un hilo separado
        hilo_audio = threading.Thread(target=self.reproducir_audio, args=(url,))
        hilo_audio.daemon = True
        hilo_audio.start()

if __name__ == "__main__":
    app = KortexNexus()
    app.run()
