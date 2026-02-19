import g4f
from gtts import gTTS
import os

class CerebroKortex:
    def __init__(self):
        # Modo Enjambre: sin proveedor fijo para evitar caídas
        pass

    def pensar(self, mensaje):
        """
        Envía el mensaje a la red neuronal buscando el primer servidor gratuito.
        """
        try:
            print("🧠 Kortex IA buscando nodos libres...")
            respuesta = g4f.ChatCompletion.create(
                model=g4f.models.gpt_4, 
                messages=[{"role": "user", "content": mensaje}]
            )
            return respuesta
            
        except Exception as e:
            return f"❌ Error neuronal: Red saturada o sin conexión. ({e})"

def generar_audio(texto):
    """
    Convierte la respuesta de la IA en un archivo de audio mp3.
    """
    try:
        archivo = "kortex_voz.mp3"
        
        # Limpiamos emojis y asteriscos para que la voz suene natural y no lea los símbolos
        texto_limpio = texto.replace("🧠", "").replace("🤖", "").replace("🔥", "").replace("❌", "").replace("*", "")
        
        # Generamos la voz en español (acento neutro/españa)
        tts = gTTS(text=texto_limpio, lang='es', tld='com')
        tts.save(archivo)
        
        # Devolvemos el nombre del archivo para que main.py lo reproduzca con mpv
        return archivo
        
    except Exception as e:
        print(f"⚠️ Advertencia TTS: No se pudo generar la voz ({e})")
        return None

# --- ZONA DE PRUEBAS ---
if __name__ == "__main__":
    print("🔥 Iniciando Pruebas de Kortex AI Engine...")
    ia = CerebroKortex()
    res = ia.pensar("Dime hola.")
    print(f"Respuesta: {res}")
    
    print("🔊 Generando prueba de audio...")
    ruta_audio = generar_audio(res)
    if ruta_audio:
        print(f"Audio guardado en: {ruta_audio}. Reproduciendo...")
        os.system(f"mpv --no-video {ruta_audio}")
