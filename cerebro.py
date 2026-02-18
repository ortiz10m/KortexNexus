import os
from google import genai
from dotenv import load_dotenv
from gtts import gTTS # <--- NUEVA IMPORTACIÓN

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Error cliente: {e}")

def preguntar_a_gemini(pregunta):
    if not client:
        return "❌ Error: Sin API Key."
    try:
        # Prompt: Pedimos respuesta corta para que no hable 3 horas
        prompt = "Eres Kortex. Responde de forma breve, útil y directa (máximo 2 párrafos). "
        
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=f"{prompt}\nUsuario: {pregunta}"
        )
        return response.text
    except Exception as e:
        return f"❌ Error: {str(e)}"

def generar_audio(texto):
    """Convierte texto a un archivo MP3 temporal"""
    try:
        # Lang='es' es Español. Tld='com.mx' es acento latino (México)
        tts = gTTS(text=texto, lang='es', tld='com.mx')
        archivo = "respuesta_kortex.mp3"
        tts.save(archivo)
        return archivo
    except Exception as e:
        print(f"Error audio: {e}")
        return None
