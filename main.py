import subprocess
import psutil
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, Log, DataTable
from textual.containers import Container
from textual.reactive import reactive

class MonitorSistema(Static):
    """Monitor de CPU/RAM en tiempo real"""
    texto_info = reactive("Iniciando sensores...")

    def on_mount(self) -> None:
        self.set_interval(1.0, self.update_stats)

    def update_stats(self) -> None:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        # Alertas de color si la RAM o CPU sufren
        color_ram = "red" if ram > 90 else "magenta"
        color_cpu = "red" if cpu > 90 else "cyan"
        
        self.texto_info = f"[bold {color_cpu}]CPU: {cpu}%[/]  |  [bold {color_ram}]RAM: {ram}%[/]"

    def render(self) -> str:
        return self.texto_info

class KortexNexus(App):
    """
    KORTEX NEXUS v1.5 - Stable Edition
    Sistema de Búsqueda y Reproducción Optimizado (1.8GB RAM)
    """

    CSS = """
    Screen { align: center middle; background: #000; }
    
    #caja_principal {
        width: 95%; height: 95%;
        border: heavy #00ff00; background: #111; padding: 1;
    }

    .titulo { text-align: center; text-style: bold; color: #00ff00; margin-bottom: 1; }
    MonitorSistema { text-align: center; border: solid #333; background: #222; margin-bottom: 1; }
    Input { dock: top; margin: 0 0 1 0; border: solid #00ff00; background: #000; color: #0f0; }
    
    DataTable { 
        height: 1fr; 
        border: solid cyan; 
        background: #000; 
        color: white; 
    }
    
    Log { height: 6; border: solid yellow; background: black; color: white; dock: bottom; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="caja_principal"):
            yield Static("👁️ KORTEX NEXUS [SISTEMA ESTABLE]", classes="titulo")
            yield MonitorSistema()
            yield Input(placeholder="Escribe el nombre del video y dale ENTER...")
            yield DataTable(cursor_type="row")
            yield Log(id="log_sistema")
        yield Footer()

    def on_mount(self) -> None:
        """Configuramos las columnas de la tabla al iniciar."""
        table = self.query_one(DataTable)
        table.add_columns("ID", "DURACIÓN", "TÍTULO")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Procesa lo que escribe el usuario."""
        comando = event.value.strip()
        log = self.query_one(Log)
        input_box = self.query_one(Input)
        table = self.query_one(DataTable)

        if not comando: return
        input_box.value = ""

        # --- COMANDOS DE SISTEMA ---
        if comando == "salir":
            self.exit()
            return
        
        elif comando == "stop":
            log.write_line("🛑 Deteniendo reproducción...")
            subprocess.run(["pkill", "mpv"])
            return

        # --- AUTO-SEARCH (Búsqueda Automática) ---
        log.write_line(f"🔍 Buscando: '{comando}'...")
        table.clear()

        try:
            # Usamos yt-dlp para obtener datos sin descargar (super rápido)
            resultado = subprocess.check_output(
                [
                    "yt-dlp", 
                    f"ytsearch5:{comando}", 
                    "--print", "%(id)s|%(duration_string)s|%(title)s",
                    "--flat-playlist"
                ],
                text=True
            )
            
            # Llenamos la tabla con los resultados
            for linea in resultado.strip().split("\n"):
                if "|" in linea:
                    vid_id, duracion, titulo = linea.split("|", 2)
                    table.add_row(vid_id, duracion, titulo)
            
            log.write_line("✅ Resultados listos. Selecciona con ENTER.")
            table.focus()

        except Exception as e:
            log.write_line(f"❌ Error buscando: {e}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Reproduce el video seleccionado de forma segura."""
        log = self.query_one(Log)
        
        # Obtenemos los datos de la fila seleccionada
        fila = self.query_one(DataTable).get_row(event.row_key)
        video_id = fila[0]
        titulo = fila[2]

        log.write_line(f"🚀 Lanzando: {titulo}")

        try:
            # AQUÍ ESTÁ EL FIX ANTI-CRASH
            # stdin=subprocess.DEVNULL: Evita que MPV robe el teclado
            # start_new_session=True: Lo separa del proceso principal
            subprocess.Popen(
                [
                    "mpv", 
                    f"https://www.youtube.com/watch?v={video_id}", 
                    "--ytdl-format=bestvideo[height<=480]+bestaudio/best[height<=480]", 
                    "--fs", 
                    "--force-window=immediate"
                ], 
                stdin=subprocess.DEVNULL, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                start_new_session=True 
            )
        except Exception as e:
            log.write_line(f"❌ Error al reproducir: {e}")

if __name__ == "__main__":
    app = KortexNexus()
    app.run()
