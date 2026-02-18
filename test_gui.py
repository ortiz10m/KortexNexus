import customtkinter as ctk
import os

# 1. Configuración de la Ventana (Modo Oscuro Moderno)
ctk.set_appearance_mode("Dark")  # Modos: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Temas: "blue", "green", "dark-blue"

class KortexGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurar la ventana principal
        self.title("Kortex Nexus - Visual")
        self.geometry("600x500")

        # --- TITULO ---
        self.label = ctk.CTkLabel(self, text="KORTEX NEXUS", font=("Roboto Medium", 24))
        self.label.pack(pady=20)

        # --- CAMPO DE TEXTO (Entrada) ---
        self.entrada = ctk.CTkEntry(self, placeholder_text="Escribe /ai o busca una canción...", width=400)
        self.entrada.pack(pady=10)

        # --- BOTONES REALES (Redondos y bonitos) ---
        self.boton_buscar = ctk.CTkButton(self, text="🔍 Buscar / Preguntar", command=self.accion_boton)
        self.boton_buscar.pack(pady=10)

        # --- ÁREA DE RESPUESTA (Donde sale el texto) ---
        self.area_texto = ctk.CTkTextbox(self, width=500, height=250)
        self.area_texto.pack(pady=20)
        
        self.area_texto.insert("0.0", "👋 Hola David. Aquí se verán las respuestas de la IA y los videos.\nMucho mejor que la terminal, ¿no?")

    def accion_boton(self):
        texto = self.entrada.get()
        self.area_texto.insert("end", f"\n\nHas escrito: {texto}")
        self.entrada.delete(0, "end")

if __name__ == "__main__":
    app = KortexGUI()
    app.mainloop()
