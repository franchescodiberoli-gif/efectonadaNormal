import os
import telebot
import random
import streamlit as st
from telebot import types
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, vfx, ImageClip
import PIL.Image, PIL.ImageDraw, PIL.ImageFont

# Parche de compatibilidad
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)
user_data = {}

for folder in ['VIDEO', 'US', 'TEMP']:
    os.makedirs(folder, exist_ok=True)

# --- FUNCIÓN PARA CREAR IMAGEN DE TEXTO (Sin ImageMagick) ---
def crear_imagen_texto(texto, ancho_video, color="white"):
    # Creamos una imagen transparente
    img = PIL.Image.new('RGBA', (ancho_video, 200), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(img)
    
    # Intentar cargar una fuente básica
    try:
        font = PIL.ImageFont.load_default() # Puedes subir una .ttf a tu repo y cargarla aquí
    except:
        font = None
        
    # Dibujar el texto en el centro de la imagen
    draw.text((ancho_video//2, 100), texto, fill=color, anchor="mm")
    
    temp_path = f"TEMP/txt_{random.randint(0,1000)}.png"
    img.save(temp_path)
    return temp_path

# --- MOTOR DE EDICIÓN ---
def procesar_video(input_p, output_p, mode, texto=None, pos=None):
    with VideoFileClip(input_p) as clip:
        # Efecto Espejo + Rotación (Triturado base)
        clip_final = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        if mode == "tk":
            fondo = ColorClip(size=(1080, 1920), color=(0, 102, 204)).set_duration(clip.duration)
            clip_res = clip_final.resize(width=1080).set_position('center')
            clip_final = CompositeVideoClip([fondo, clip_res])
        
        if mode == "tit" and texto:
            img_path = crear_imagen_texto(texto, clip.w)
            txt_overlay = (ImageClip(img_path)
                           .set_duration(clip.duration)
                           .set_position(("center", pos_map[pos] if pos in pos_map else "center")))
            
            # Mapeo de posiciones dentro del video
            pos_map = {"arriba": 50, "medio": "center", "abajo": clip.h - 250}
            
            clip_final = CompositeVideoClip([clip_final, txt_overlay])

        clip_final.write_videofile(output_p, codec="libx264", audio_codec="aac", threads=1, preset="ultrafast", logger=None)

# --- MANEJADORES TELEGRAM ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "manda un video para comenzar")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    user_data[message.chat.id] = {'file_id': message.video.file_id, 'step': 'inicio'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Callbacks cortos para evitar error 400
    markup.add(
        types.InlineKeyboardButton("🚀 Triturar Normal", callback_data="n"),
        types.InlineKeyboardButton("📱 Formato TikTok", callback_data="t"),
        types.InlineKeyboardButton("📝 Añadir Títulos (3 Posiciones)", callback_data="p")
    )
    bot.send_message(message.chat.id, "video recibido. elige el modo:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "p":
        user_data[chat_id]['step'] = 'wait'
        bot.send_message(chat_id, "✍️ Escribe el título que quieres poner:")
    else:
        m = "norm" if call.data == "n" else "tk"
        ejecutar(chat_id, m)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'wait')
def recibir_texto(message):
    user_data[message.chat.id]['step'] = 'proc'
    ejecutar(message.chat.id, "tit_3", texto=message.text)

def ejecutar(chat_id, modo, texto=None):
    status = bot.send_message(chat_id, "⏳ Procesando... ten paciencia.")
    try:
        file_info = bot.get_file(user_data[chat_id]['file_id'])
        downloaded = bot.download_file(file_info.file_path)
        in_p = f"VIDEO/in_{chat_id}.mp4"
        with open(in_p, 'wb') as f: f.write(downloaded)

        if modo == "tit_3":
            for p in ["arriba", "medio", "abajo"]:
                out_p = f"US/{p}_{chat_id}.mp4"
                procesar_video(in_p, out_p, "tit", texto, p)
                with open(out_p, 'rb') as v:
                    bot.send_video(chat_id, v, caption=f"✅ Posición: {p}")
                os.remove(out_p)
        else:
            out_p = f"US/res_{chat_id}.mp4"
            procesar_video(in_p, out_p, modo)
            with open(out_p, 'rb') as v:
                bot.send_video(chat_id, v, caption="🔥 ¡Listo!")
            os.remove(out_p)
        
        os.remove(in_p)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
    finally:
        bot.delete_message(chat_id, status.message_id)

st.title("🤖 OFM Processor v3.3")
bot.infinity_polling()
