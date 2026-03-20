import os
import telebot
import random
import streamlit as st
from telebot import types
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, vfx, ImageClip
import PIL.Image, PIL.ImageDraw, PIL.ImageFont

# Parche de compatibilidad para Pillow
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)
user_data = {}

# Carpetas de trabajo
for folder in ['VIDEO', 'US', 'TEMP']:
    os.makedirs(folder, exist_ok=True)

# --- FUNCIÓN PARA CREAR IMAGEN DE TEXTO ---
def crear_imagen_texto(texto, ancho_video):
    img = PIL.Image.new('RGBA', (ancho_video, 250), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(img)
    try:
        font = PIL.ImageFont.load_default() 
    except:
        font = None
    draw.text((ancho_video // 2, 125), texto, fill="white", anchor="mm")
    temp_path = f"TEMP/txt_{random.randint(1000,9999)}.png"
    img.save(temp_path)
    return temp_path

# --- MOTOR DE EDICIÓN CORREGIDO ---
def procesar_video(input_p, output_p, mode, texto=None, pos=None):
    with VideoFileClip(input_p) as clip:
        # 1. Efecto Base
        clip_final = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        # 2. Lógica TikTok
        if mode == "tk":
            fondo = ColorClip(size=(1080, 1920), color=(0, 102, 204)).set_duration(clip.duration)
            clip_res = clip_final.resize(width=1080).set_position('center')
            clip_final = CompositeVideoClip([fondo, clip_res])
        
        # 3. Lógica de Títulos (CORREGIDA)
        if mode == "tit" and texto:
            img_path = crear_imagen_texto(texto, clip.w)
            
            # Definimos la posición directamente aquí para evitar errores de variable local
            if pos == "arriba":
                y_final = 100
            elif pos == "abajo":
                y_final = clip.h - 300
            else:
                y_final = "center"

            txt_overlay = (ImageClip(img_path)
                           .set_duration(clip.duration)
                           .set_position(("center", y_final)))
            
            clip_final = CompositeVideoClip([clip_final, txt_overlay])

        # Renderizado (threads=1 para no saturar Streamlit)
        clip_final.write_videofile(output_p, codec="libx264", audio_codec="aac", threads=1, preset="ultrafast", logger=None)

# --- MANEJADORES TELEGRAM ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "manda un video para comenzar")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    user_data[message.chat.id] = {'file_id': message.video.file_id, 'step': 'inicio'}
    markup = types.InlineKeyboardMarkup(row_width=1)
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
    status = bot.send_message(chat_id, "⏳ Procesando... espera un poco.")
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
                    bot.send_video(chat_id, v, caption=f"✅ Título {p}")
                if os.path.exists(out_p): os.remove(out_p)
        else:
            out_p = f"US/res_{chat_id}.mp4"
            procesar_video(in_p, out_p, modo)
            with open(out_p, 'rb') as v:
                bot.send_video(chat_id, v, caption="🔥 ¡Listo!")
            if os.path.exists(out_p): os.remove(out_p)
        
        if os.path.exists(in_p): os.remove(in_p)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
    finally:
        bot.delete_message(chat_id, status.message_id)

st.title("🤖 OFM Processor v3.5")
bot.infinity_polling()
