import os
import telebot
import random
import streamlit as st
from telebot import types
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, vfx, ImageClip
import PIL.Image, PIL.ImageDraw, PIL.ImageFont

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)
user_data = {}

for folder in ['VIDEO', 'US', 'TEMP']:
    os.makedirs(folder, exist_ok=True)

# --- FUNCIÓN DE TÍTULO TIKTOK REAL ---
def crear_imagen_texto_pro(texto, ancho_video):
    # Tamaño de letra GIGANTE (15% del ancho del video)
    font_size = int(ancho_video * 0.15) 
    
    # Creamos un lienzo transparente
    img = PIL.Image.new('RGBA', (ancho_video, font_size + 150), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(img)
    
    # Intentar cargar una fuente gruesa del sistema o usar la básica
    try:
        # En la mayoría de servidores linux de Streamlit, esta ruta funciona
        font = PIL.ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = PIL.ImageFont.load_default()

    pos_x = ancho_video // 2
    pos_y = (font_size + 150) // 2

    # EFECTO TIKTOK: Contorno negro muy grueso para legibilidad total
    stroke = 8
    for ox in range(-stroke, stroke + 1):
        for oy in range(-stroke, stroke + 1):
            draw.text((pos_x + ox, pos_y + oy), texto.upper(), fill="black", font=font, anchor="mm")

    # Texto principal en blanco
    draw.text((pos_x, pos_y), texto.upper(), fill="white", font=font, anchor="mm")
    
    temp_path = f"TEMP/tit_{random.randint(1000,9999)}.png"
    img.save(temp_path)
    return temp_path

# --- MOTOR DE EDICIÓN ---
def procesar_video(input_p, output_p, modo_titulo, texto=None, posicion=None):
    with VideoFileClip(input_p) as clip:
        # 1. Espejo y rotación (Triturado)
        clip_base = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        # 2. Aplicar Título
        img_path = crear_imagen_texto_pro(texto, clip_base.w)
        
        # COORDENADAS FIJAS (Píxeles reales desde el borde)
        if posicion == "arriba":
            # Literalmente en el borde superior con un pequeño margen
            y_final = 80 
        elif posicion == "abajo":
            # En el borde inferior, arriba de los botones de TikTok
            y_final = clip_base.h - 400
        else:
            y_final = "center"

        txt_overlay = (ImageClip(img_path)
                       .set_duration(clip_base.duration)
                       .set_position(("center", y_final))
                       .resize(width=clip_base.w * 0.95)) # Casi todo el ancho

        clip_final = CompositeVideoClip([clip_base, txt_overlay])

        # Exportar
        clip_final.write_videofile(output_p, codec="libx264", audio_codec="aac", threads=1, preset="ultrafast", logger=None)

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    user_data[message.chat.id] = {}
    bot.send_message(message.chat.id, "✅ Bot listo. Envíame el video.")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    user_data[message.chat.id] = {'file_id': message.video.file_id}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 Poner Títulos Título 1", callback_data="p"))
    bot.send_message(message.chat.id, "Video recibido. ¿Quieres los títulos?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "p")
def ask_text(call):
    user_data[call.message.chat.id]['step'] = 'wait'
    bot.send_message(call.message.chat.id, "✍️ Escribe el título (Ej: GANO EL AMERICA):")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'wait')
def run_all(message):
    chat_id = message.chat.id
    texto = message.text
    user_data[chat_id]['step'] = 'processing'
    
    status = bot.send_message(chat_id, "⏳ Generando las 3 versiones (Arriba, Centro, Abajo)...")
    
    try:
        file_info = bot.get_file(user_data[chat_id]['file_id'])
        downloaded = bot.download_file(file_info.file_path)
        in_p = f"VIDEO/in_{chat_id}.mp4"
        with open(in_p, 'wb') as f: f.write(downloaded)

        for p in ["arriba", "medio", "abajo"]:
            out_p = f"US/{p}_{chat_id}.mp4"
            procesar_video(in_p, out_p, True, texto, p)
            with open(out_p, 'rb') as v:
                bot.send_video(chat_id, v, caption=f"📍 Posición: {p}")
            os.remove(out_p)
            
        os.remove(in_p)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
    finally:
        user_data[chat_id]['step
