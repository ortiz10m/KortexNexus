import sys
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QLineEdit, 
                             QPushButton, QWidget, QVBoxLayout)
from PyQt6.QtWebEngineWidgets import QWebEngineView

# --- DISEÑO "APPLE DARK" (Premium) ---
ESTILO_MODERNO = """
QMainWindow {
    background-color: #1e1e1e; /* Gris oscuro elegante */
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
    border-radius: 8px; /* Bordes suaves */
    color: #e0e0e0;
    padding: 6px 12px;
    font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #007AFF; /* Azul Apple al enfocar */
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
    background-color: #3e3e42; /* Efecto hover sutil */
    color: white;
}
QPushButton:pressed {
    background-color: #007AFF; /* Azul al presionar */
    color: white;
}
"""

class KortexBrowser(QMainWindow):
    def __init__(self, url_inicial="https://www.google.com"):
        super().__init__()
        self.setWindowTitle("Kortex Pro Browser")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(ESTILO_MODERNO)

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
        self.crear_boton("<", self.navegar_atras)
        self.crear_boton(">", self.navegar_adelante)
        self.crear_boton("↻", self.recargar)

        # Barra URL
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("🔍 Buscar o escribir URL...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.navbar.addWidget(self.url_bar)
        
        # Botón Ir
        self.crear_boton("➔", self.navigate_to_url)

        # Motor Web
        self.browser = QWebEngineView()
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
        url = self.url_bar.text()
        if not url.startswith("http"):
            if "." not in url:
                url = f"https://www.google.com/search?q={url}" # Búsqueda directa
            else:
                url = "https://" + url
        self.browser.setUrl(QUrl(url))

    def update_url(self, q):
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def navegar_atras(self): self.browser.back()
    def navegar_adelante(self): self.browser.forward()
    def recargar(self): self.browser.reload()
    def carga_terminada(self): self.setWindowTitle(f"{self.browser.title()} - Kortex Pro")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    url = "https://www.google.com"
    if len(sys.argv) > 1: url = sys.argv[1]
    window = KortexBrowser(url)
    window.show()
    sys.exit(app.exec())
