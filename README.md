# 🚀 Kortex Nexus v1.0
**Suite de Productividad de Alto Rendimiento impulsada por IA para Hardware de Bajos Recursos.**

Kortex Nexus es una plataforma diseñada específicamente para revivir y potenciar equipos antiguos o con recursos limitados (<2GB RAM). A diferencia del software tradicional que asfixia tu memoria, Kortex utiliza una **arquitectura modular multiplataforma** que delega el trabajo pesado al sistema operativo, ofreciendo Inteligencia Artificial gratuita, automatización y navegación web sin colapsar tu PC.

## 🔥 Características Principales

* **🧠 Cerebro Nexus (IA Modo Enjambre):** Asistente de Inteligencia Artificial integrado que responde, resume y corrige textos usando un enrutamiento dinámico (g4f) **100% gratis y sin necesidad de API Keys**.
* **🗣️ Modo Jarvis (Voz y Oído):** Habla con tu PC y escucha las respuestas en tiempo real con integración nativa de STT (SpeechRecognition) y TTS (Google Text-to-Speech).
* **🌐 Kortex Web Engine:** Puente de navegación inteligente. En Linux utiliza `Epiphany` (motor ultraligero de GNOME) en "Modo App", y en Windows utiliza tu navegador nativo. Cero consumo extra de RAM en la suite.
* **🚀 Launcher Dinámico:** Panel de accesos directos personalizable. Tus web-apps favoritas a un clic, con protección anti-captchas (DuckDuckGo routing).
* **🎵 Radio Nexus:** Reproductor de música en segundo plano basado en terminal (yt-dlp + MPV). Escucha YouTube sin cargar el video, ahorrando hasta un 80% de CPU.
* **📊 Monitor & Cleaner:** Visualización en tiempo real de recursos y purga automática de caché del sistema operativo para evitar cuellos de botella.

## 🛠️ Stack Tecnológico

* **Core:** Python 3.x
* **UI:** CustomTkinter (Modern Dark GUI)
* **Motor de IA:** `g4f` (Red Neuronal Libre Autónoma)
* **Audio & Voz:** `gTTS`, `SpeechRecognition`, `mpv`
* **Motor Web:** `Epiphany-browser` (Linux) / `webbrowser` OS API (Windows)

## 📦 Instalación Rápida

### 1. Dependencias del Sistema (Para LocOS / Ubuntu / Debian)
Abre tu terminal y asegúrate de tener los motores ligeros instalados:

    sudo apt update
    sudo apt install epiphany-browser mpv python3-venv -y

### 2. Clonar y Configurar

    # Clonar el repositorio
    git clone https://github.com/ortiz10m/KortexNexus.git
    cd KortexNexus

    # Crear entorno virtual (Recomendado)
    python3 -m venv venv
    source venv/bin/activate

    # Instalar dependencias de Python
    pip install -r requirements.txt

### 3. Ejecutar Kortex
¡Listo! No necesitas configurar ninguna API Key ni crear cuentas. Simplemente lanza el sistema:

    python3 main.py

*(O utiliza el script de arranque `./run.sh` si lo tienes configurado).*

---

## 📄 Licencia y Copyright
**© 2026 David Santiago Ortiz Rincon (Founder). Todos los derechos reservados.**

Este proyecto es de código cerrado y propiedad intelectual exclusiva de su autor. El código fuente publicado en este repositorio tiene fines puramente demostrativos (Portafolio). Queda estrictamente prohibida la copia, modificación, distribución o uso comercial de este software sin autorización expresa, previa y por escrito del autor.
