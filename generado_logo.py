from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

def crear_logo():
    size = (512, 512)
    # 1. Fondo (Degradado Azul Oscuro estilo Apple/Kortex)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Dibujar círculo de fondo (o cuadrado redondeado)
    # Color: Azul Profundo (#0f2027) a Azul (#203a43)
    draw.ellipse([10, 10, 502, 502], fill="#0f2027", outline="#007AFF", width=10)

    # 2. La "K" de Kortex (Estilo Tech)
    # Intentamos cargar una fuente del sistema, si no, usa la default
    try:
        # En Linux a veces las fuentes están en rutas específicas
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 300)
    except:
        font = ImageFont.load_default()

    # Sombra de la letra
    draw.text((160, 90), "K", font=font, fill="#000000") 
    
    # Letra Principal (Blanco Brillante)
    draw.text((150, 80), "K", font=font, fill="#FFFFFF")

    # 3. Guardar
    img.save("logo_kortex.png", "PNG")
    img.save("icon.ico", format='ICO') # Para el ejecutable de Windows
    print("✅ Logo creado: logo_kortex.png")

if __name__ == "__main__":
    crear_logo()
