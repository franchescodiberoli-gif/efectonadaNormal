import os
import telebot
import random
import streamlit as st
from telebot import types
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, vfx
import PIL.Image

# Parche de compatibilidad
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)
user_data = {}

for folder in ['VIDEO', 'US']:
    os.makedirs(folder, exist_ok=True)

# --- MOTOR DE EDICIÓN ---
def procesar_video(input_p, output_p, mode, texto=None, pos=None):
    with VideoFileClip(input_p) as clip:
        # Efecto base: Espejo + Rotación sutil
        clip_final = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        if mode == "tk":
            fondo = ColorClip(size=(1080, 1920), color=(0, 102, 204)).set_duration(clip.duration)
            clip_res = clip_final.resize(width=1080).set_position('center')
            clip_final = CompositeVideoClip([fondo, clip_res])
        
        if mode == "tit" and texto:
            from moviepy.video.VideoClip import TextClip
            try:
                # Nota: Requiere ImageMagick instalado (archivo packages.txt)
                txt = TextClip(texto, fontsize=70, color='white', font='Arial-Bold', method='caption', width=clip.w*0.8)
                positions = {"arriba": ("center", 50), "medio": ("center", "center"), "abajo": ("center", clip.h-150)}
                txt = txt.set_start(0).set_duration(clip.duration).set_position(positions[pos])
                clip_final = CompositeVideoClip([clip_final, txt])
            except:
                pass

        clip_final.write_videofile(output_p, codec="libx264", audio_codec="aac", logger=None, threads=4)

# --- MANEJADORES TELEGRAM ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "manda un video para comenzar")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    user_data[message.chat.id] = {'file_id': message.video.file_id, 'step': 'inicio'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Callback_data cortos para evitar el error 'BUTTON_DATA_INVALID'
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
        user_data[chat_id]['step'] = 'wait_txt'
        bot.send_message(chat_id, "✍️ Escribe el título que quieres poner:")
    else:
        # Mapeo de vuelta: 'n' -> 'norm', 't' -> 'tk'
        m = "norm" if call.data == "n" else "tk"
        ejecutar_proceso(chat_id, m)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'wait_txt')
def recibir_texto(message):
    user_data[message.chat.id]['step'] = 'proc'
    ejecutar_proceso(message.chat.id, "tit_3", message.text)

def ejecutar_proceso(chat_id, modo, texto=None):
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

st.title("🤖 Servidor Agencia v3.1")
bot.infinity_polling()
