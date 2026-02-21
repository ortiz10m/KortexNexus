import g4f
from gtts import gTTS
import os

class CerebroKortex:
    def __init__(self):
        # 🧠 EL HIPOCAMPO: Aquí guardamos la memoria de la conversación
        # Le inyectamos un "System Prompt" para darle su personalidad Dark/Focus
        self.historial = [
            {"role": "system", "content": "Eres Kortex Nexus, una IA de alto rendimiento, minimalista, precisa y directa. Respondes de forma concisa y profesional."}
        ]

    def pensar_en_vivo(self, mensaje):
        """
        Envía el historial completo a la red neuronal para mantener el contexto (Memoria).
        """
        # 1. Guardamos la nueva pregunta del usuario en la memoria
        self.historial.append({"role": "user", "content": mensaje})

        # 2. Control de RAM: Si la memoria crece mucho, borramos lo más viejo (sin borrar el System Prompt)
        if len(self.historial) > 11:
            self.historial.pop(1)

        try:
            print("🧠 Kortex IA conectando con historial en memoria...")
            
            # 3. Le enviamos TODA la lista de memoria, no solo el último mensaje
            respuesta = g4f.ChatCompletion.create(
                model=g4f.models.gpt_4, 
                messages=self.historial,
                stream=True 
            )
            
            respuesta_completa = ""
            for fragmento in respuesta:
                if fragmento and isinstance(fragmento, str): 
                    respuesta_completa += fragmento
                    yield fragmento
            
            # 4. Guardamos la respuesta final de Kortex en la memoria para que recuerde lo que dijo
            if respuesta_completa.strip():
                self.historial.append({"role": "assistant", "content": respuesta_completa})
                
        except Exception as e:
            # Si falla, sacamos la pregunta rota de la memoria para no corromper el historial
            self.historial.pop()
            yield f"❌ Error neuronal: Servidores saturados. ({e})"

def generar_audio(texto):
    try:
        archivo = "kortex_voz.mp3"
        texto_limpio = texto.replace("🧠", "").replace("🤖", "").replace("🔥", "").replace("❌", "").replace("*", "")
        tts = gTTS(text=texto_limpio, lang='es', tld='com')
        tts.save(archivo)
        return archivo
    except Exception as e:
        print(f"⚠️ Advertencia TTS: No se pudo generar la voz ({e})")
        return None
