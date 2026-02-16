# KORTEX NEXUS (Alpha v1.5)

> **"El navegador es el sistema operativo... pero es demasiado pesado."**

Kortex Nexus es una interfaz de terminal (TUI) diseñada para **equipos de bajos recursos** (enfocado en hardware con < 2GB RAM). Permite buscar y reproducir contenido multimedia de YouTube sin la sobrecarga de un navegador web convencional.

## 🚀 Características
* **Ultra Ligero:** Consume ~60MB de RAM (vs 800MB de Chrome).
* **Motor TUI:** Interfaz gráfica en terminal usando Python + Textual.
* **Privacidad:** Sin anuncios, sin rastreadores, sin algoritmos de distracción.
* **Optimización 480p:** Fuerza la reproducción en SD para salvar CPU en máquinas antiguas.

## 🛠️ Tecnologías
* **Core:** Python 3.11
* **UI:** Textual (TUI Framework)
* **Media:** MPV + yt-dlp
* **System:** Linux (LocOS/Debian)

## 📦 Instalación
```bash
git clone [https://github.com/TU_USUARIO/KortexNexus.git](https://github.com/TU_USUARIO/KortexNexus.git)
cd KortexNexus
python3 -m venv venv
source venv/bin/activate
pip install textual yt-dlp psutil
sudo apt install mpv
python3 main.py
