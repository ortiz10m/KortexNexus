import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("-" * 50)
print("🔍 DIAGNÓSTICO DE LLAVE Y MODELOS")
print("-" * 50)

# 1. VERIFICAR LA LLAVE
if not api_key:
    print("❌ ERROR CRÍTICO: No se encontró ninguna llave en .env")
    exit()

# Mostramos solo el principio para ver si es la NUEVA
print(f"🔑 Llave leída: {api_key[:10]}...[OCULTO]") 
print("(Verifica si esos primeros caracteres coinciden con tu llave nueva)")

# 2. INTERROGAR A GOOGLE
try:
    client = genai.Client(api_key=api_key)
    
    print("\n📡 Conectando con Google para pedir la lista oficial...")
    
    # Esta es la función mágica que nos dice la verdad
    all_models = list(client.models.list())
    
    print(f"✅ ¡CONEXIÓN EXITOSA! Se encontraron {len(all_models)} modelos.")
    print("\n📝 LISTA DE MODELOS DISPONIBLES PARA TI:")
    
    encontrado_flash = False
    
    for m in all_models:
        # Filtramos solo los "gemini" para no llenar la pantalla de basura
        if "gemini" in m.name:
            print(f"   👉 {m.name}")
            if "flash" in m.name:
                encontrado_flash = True

    print("-" * 50)
    
    if encontrado_flash:
        print("🎉 ¡BUENAS NOTICIAS! Tienes acceso a Flash.")
        print("Usa EXACTAMENTE uno de los nombres de arriba en tu código.")
    else:
        print("⚠️ Tienes acceso a Gemini, pero no veo el modelo Flash.")

except Exception as e:
    print(f"\n❌ ERROR FATAL AL CONECTAR:")
    print(e)
    print("\nPOSIBLES CAUSAS:")
    print("1. La llave no sirve (¿copiaste todo el texto sin espacios extra?)")
    print("2. Tu internet bloquea la conexión a Google API.")
