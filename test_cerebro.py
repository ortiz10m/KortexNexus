import os
from google import genai
from dotenv import load_dotenv

# 1. Cargar claves
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: No hay clave en .env")
    exit()

# 2. Configurar Cliente
try:
    client = genai.Client(api_key=api_key)

    print("-" * 40)
    print("🧠 KORTEX 1.5: CONECTANDO...")
    print("-" * 40)

    # CAMBIO AQUÍ: Usamos la versión 1.5 que sí es pública
    response = client.models.generate_content(
        model="gemini-1.5-flash", 
        contents="Hola Kortex. ¿Qué versión eres?"
    )

    print(f"🤖 RESPUESTA:\n{response.text}")
    print("-" * 40)

except Exception as e:
    print(f"❌ ERROR: {e}")
