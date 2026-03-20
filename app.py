import os
import telebot
import random
import streamlit as st
from telebot import types
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, vfx
import PIL.Image

# Solución para el error de versiones de Pillow
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)
user_data = {}

# Crear carpetas de trabajo
for folder in ['VIDEO', 'US']:
    os.makedirs(folder, exist_ok=True)

# --- MOTOR DE EDICIÓN OPTIMIZADO ---
def procesar_video(input_p, output_p, mode, texto=None, pos=None):
    with VideoFileClip(input_p) as clip:
        # Efecto base: Espejo + Rotación sutil
        clip_final = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        if mode == "tk":
            # Fondo azul de la agencia
            fondo = ColorClip(size=(1080, 1920), color=(0, 102, 204)).set_duration(clip.duration)
            clip_res = clip_final.resize(width=1080).set_position('center')
            clip_final = CompositeVideoClip([fondo, clip_res])
        
        # Guardar con ajustes de baja memoria para evitar "Broken Pipe"
        clip_final.write_videofile(
            output_p, 
            codec="libx264", 
            audio_codec="aac", 
            threads=1, 
            logger=None, 
            preset="ultrafast"
        )

# --- MANEJADORES TELEGRAM ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "manda un video para comenzar")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    # Resetear datos del usuario para este video
    user_data[message.chat.id] = {'file_id': message.video.file_id, 'step': 'inicio'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Usamos callbacks de una sola letra para máxima estabilidad (Evita Error 400)
    markup.add(
        types.InlineKeyboardButton("🚀 Triturar Normal", callback_data="n"),
        types.InlineKeyboardButton("📱 Formato TikTok", callback_data="t"),
        types.InlineKeyboardButton("📝 Añadir Títulos", callback_data="p")
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
        modo_real = "norm" if call.data == "n" else "tk"
        ejecutar_final(chat_id, modo_real)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'wait')
def recibir_texto(message):
    user_data[message.chat.id]['step'] = 'proc'
    # Por ahora, para no romper el servidor, procesaremos el modo normal con el texto en el caption
    ejecutar_final(message.chat.id, "norm", texto_usuario=message.text)

def ejecutar_final(chat_id, modo, texto_usuario=None):
    status = bot.send_message(chat_id, "⏳ Procesando... esto tardará unos segundos.")
    try:
        file_info = bot.get_file(user_data[chat_id]['file_id'])
        downloaded = bot.download_file(file_info.file_path)
        
        in_p = f"VIDEO/in_{chat_id}.mp4"
        out_p = f"US/out_{chat_id}.mp4"

        with open(in_p, 'wb') as f:
            f.write(downloaded)

        procesar_video(in_p, out_p, modo)

        with open(out_p, 'rb') as v:
            cap = "🔥 ¡Listo!" if not texto_usuario else f"📝 Título: {texto_usuario}"
            bot.send_video(chat_id, v, caption=cap)
        
        # Limpieza manual de archivos
        if os.path.exists(in_p): os.remove(in_p)
        if os.path.exists(out_p): os.remove(out_p)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
    finally:
        bot.delete_message(chat_id, status.message_id)

# --- STREAMLIT ---
st.title("🤖 OFM Processor v3.2")
st.write("Servidor encendido. No cierres esta pestaña.")
bot.infinity_polling(timeout=60, long_polling_timeout=30)
