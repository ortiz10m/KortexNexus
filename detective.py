import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Sin clave en .env")
    exit()

client = genai.Client(api_key=api_key)

print("🕵️  BUSCANDO MODELOS DISPONIBLES PARA TI...")
print("-" * 50)

try:
    # Le pedimos a Google la lista oficial
    # (Usamos el cliente HTTP interno para ver la lista cruda si el método falla)
    # Pero probaremos primero iterando nombres comunes
    
    candidatos = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-1.0-pro",
        "gemini-pro"
    ]
    
    encontrado = False
    
    for modelo in candidatos:
        print(f"👉 Probando conexión con: {modelo}...", end=" ")
        try:
            response = client.models.generate_content(
                model=modelo, 
                contents="Hola"
            )
            print("✅ ¡ÉXITO!")
            print(f"\n🎉 ¡TENEMOS UN GANADOR! El nombre correcto es: '{modelo}'")
            print(f"🤖 Kortex respondió: {response.text}")
            encontrado = True
            break # Dejamos de buscar
        except Exception as e:
            if "404" in str(e):
                print("❌ (No existe)")
            elif "429" in str(e):
                print("⚠️ (Existe pero sin cuota/saldo)")
            else:
                print(f"❌ Error raro: {e}")

    if not encontrado:
        print("-" * 50)
        print("😓 Ninguno funcionó. Tu API Key podría tener permisos limitados o ser de un proyecto viejo.")

except Exception as e:
    print(f"Error fatal: {e}")
