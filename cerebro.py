import os
from google import genai
from dotenv import load_dotenv
from gtts import gTTS

# Función interna para obtener el cliente actualizado
def obtener_cliente():
    load_dotenv(override=True) # El override=True es clave para leer cambios nuevos en el .env
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            return genai.Client(api_key=api_key)
        except Exception as e:
            print(f"⚠️ Error inicializando cliente: {e}")
    return None

def preguntar_a_gemini(pregunta):
    client = obtener_cliente()
    if not client:
        return "❌ Error: Configura tu API Key primero."

    try:
        prompt = "Eres Kortex. Responde de forma breve y directa."
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=f"{prompt}\nUsuario: {pregunta}"
        )
        return response.text
    except Exception as e:
        # --- MANEJO PROFESIONAL DEL ERROR 429 ---
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return "⏳ Sistema saturado. Google nos pide esperar un minuto. Intenta de nuevo en un momento."
        return f"❌ Error inesperado: {error_msg}"

def generar_audio(texto):
    """Convierte texto a un archivo MP3 temporal"""
    try:
        # Lang='es' es Español. Tld='com.mx' es acento latino
        tts = gTTS(text=texto, lang='es', tld='com.mx')
        archivo = "respuesta_kortex.mp3"
        tts.save(archivo)
        return archivo
    except Exception as e:
        print(f"Error audio: {e}")
        return None
