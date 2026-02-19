import sys
import os

# --- 🚨 MODO TANQUE (OBLIGATORIO PARA INTERNET EN LOCOS) ---
# Sin esto, el navegador se queda en blanco o no conecta en Linux ligeros.
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu --disable-setuid-sandbox --ignore-certificate-errors"

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QLineEdit, 
                             QPushButton, QWidget, QVBoxLayout)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon # Necesario para el logo

# --- TU DISEÑO "APPLE DARK" (Intacto) ---
ESTILO_MODERNO = """
QMainWindow {
    background-color: #1e1e1e;
}
QToolBar {
    background: #252526;
    border-bottom: 1px solid #333;
    padding: 8px;
    spacing: 12px;
}
QLineEdit {
    background-color: #3c3c3c;
    border: 1px solid #484848;
    border-radius: 8px;
    color: #e0e0e0;
    padding: 6px 12px;
    font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #007AFF;
    background-color: #454545;
}
QPushButton {
    background-color: transparent;
    color: #cccccc;
    border-radius: 4px;
    padding: 6px;
    font-weight: bold;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #3e3e42;
    color: white;
}
QPushButton:pressed {
    background-color: #007AFF;
    color: white;
}
"""

# RUTA DEL LOGO (Para que la ventana tenga tu marca)
RUTA_BASE = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(RUTA_BASE, "logo_kortex.png")

class KortexBrowser(QMainWindow):
    def __init__(self, url_inicial="https://www.google.com"):
        super().__init__()
        self.setWindowTitle("Kortex Pro Browser")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(ESTILO_MODERNO)

        # --- CARGAR LOGO ---
        if os.path.exists(LOGO_PATH):
            self.setWindowIcon(QIcon(LOGO_PATH))

        # Layout Principal
        contenido = QWidget()
        self.setCentralWidget(contenido)
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Barra de Herramientas
        self.navbar = QToolBar()
        self.navbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.navbar)

        # Botones Minimalistas
        self.crear_boton("<", self.browser_back)
        self.crear_boton(">", self.browser_forward)
        self.crear_boton("↻", self.browser_reload)

        # Barra URL
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("🔍 Buscar o escribir URL...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.navbar.addWidget(self.url_bar)
        
        # Botón Ir
        self.crear_boton("➔", self.navigate_to_url)

        # Motor Web
        self.browser = QWebEngineView()
        
        # --- PERMISOS PARA QUE CARGUE BIEN ---
        # Esto ayuda a que las páginas modernas funcionen mejor
        self.browser.settings().setAttribute(self.browser.settings().WebAttribute.JavascriptEnabled, True)
        self.browser.settings().setAttribute(self.browser.settings().WebAttribute.LocalStorageEnabled, True)
        
        self.browser.setUrl(QUrl(url_inicial))
        layout.addWidget(self.browser)

        # Eventos
        self.browser.urlChanged.connect(self.update_url)
        self.browser.loadFinished.connect(self.carga_terminada)

    def crear_boton(self, texto, funcion):
        btn = QPushButton(texto)
        btn.setFixedSize(35, 30)
        btn.clicked.connect(funcion)
        self.navbar.addWidget(btn)

    def navigate_to_url(self):
        texto = self.url_bar.text().strip()
        
        # LÓGICA DE BÚSQUEDA MEJORADA
        # Si escribes "hola mundo" (con espacio) o "python" (sin punto), busca en Google.
        if " " in texto or "." not in texto:
            url = f"https://www.google.com/search?q={texto}"
        # Si escribes "youtube.com", añade https://
        elif not texto.startswith("http"):
            url = "https://" + texto
        else:
            url = texto
            
        self.browser.setUrl(QUrl(url))

    def update_url(self, q):
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    # Funciones wrapper para conectar con los botones
    def browser_back(self): self.browser.back()
    def browser_forward(self): self.browser.forward()
    def browser_reload(self): self.browser.reload()
    
    def carga_terminada(self): 
        self.setWindowTitle(f"{self.browser.title()} - Kortex Pro")

if __name__ == "__main__":
    # Inyección de argumentos para asegurar compatibilidad
    args = sys.argv + ["--no-sandbox", "--disable-gpu"]
    app = QApplication(args)
    
    # Icono a nivel aplicación
    if os.path.exists(LOGO_PATH):
        app.setWindowIcon(QIcon(LOGO_PATH))

    # Recibir URL desde main.py
    url = "https://www.google.com"
    if len(sys.argv) > 1:
        # Filtrar argumentos propios de Qt/Chromium
        for arg in sys.argv[1:]:
            if not arg.startswith("--"):
                url = arg
                break
                
    window = KortexBrowser(url)
    window.show()
    sys.exit(app.exec())
