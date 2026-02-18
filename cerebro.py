import os
from google import genai
from dotenv import load_dotenv

# --- CONFIGURACIÓN INICIAL ---
# 1. Cargar las llaves secretas del archivo .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 2. Configurar el Cliente de Google (Nueva versión 2026)
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Error al iniciar el cliente de IA: {e}")

def preguntar_a_gemini(pregunta):
    """
    Función que recibe texto y devuelve la respuesta de la IA.
    Está optimizada para no gastar recursos.
    """
    if not client:
        return "❌ ERROR: No se encontró la API Key en el archivo .env"

    try:
        # Prompt del Sistema: Le decimos cómo comportarse para ahorrar texto
        prompt_sistema = (
            "Eres Kortex, un asistente de terminal Linux ultra-eficiente. "
            "El usuario tiene recursos limitados (1.8GB RAM). "
            "Responde de forma breve, directa, técnica y sin relleno. "
            "Usa formato Markdown si es necesario."
        )

        # 3. CONECTANDO CON EL MODELO (Usamos el 2.5 Flash que encontramos)
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=f"{prompt_sistema}\n\nPregunta del usuario: {pregunta}"
        )
        
        # Devolvemos solo el texto limpio
        return response.text

    except Exception as e:
        # Si algo falla (internet, cuota, etc), devolvemos el error bonito
        return f"❌ Error de Conexión: {str(e)}"

# --- BLOQUE DE PRUEBA ---
# Esto solo se ejecuta si corres "python3 cerebro.py" directamente
if __name__ == "__main__":
    print("-" * 40)
    print("🧠 PROBANDO MÓDULO CEREBRO (Gemini 2.5 Flash)...")
    print("-" * 40)
    
    respuesta = preguntar_a_gemini("Explica qué es la memoria RAM en una frase corta.")
    
    print(f"🤖 KORTEX DICE:\n{respuesta}")
    print("-" * 40)
