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

# --- FUNCIÓN DE TÍTULO ESTILO TIKTOK ---
def crear_imagen_texto_pro(texto, ancho_video):
    # Tamaño de fuente masivo para "Título 1"
    font_size = int(ancho_video * 0.12) 
    
    # Creamos un lienzo transparente
    img = PIL.Image.new('RGBA', (ancho_video, font_size + 150), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(img)
    
    try:
        # Intenta usar una fuente del sistema, si no, usa la básica
        # Si quieres una fuente específica como 'Arial Bold', súbela a tu repo
        font = PIL.ImageFont.load_default() 
    except:
        font = None

    pos_x = ancho_video // 2
    pos_y = (font_size + 150) // 2

    # EFECTO TIKTOK: Contorno negro grueso (Stroke)
    stroke_width = 6
    for offset_x in range(-stroke_width, stroke_width + 1):
        for offset_y in range(-stroke_width, stroke_width + 1):
            draw.text((pos_x + offset_x, pos_y + offset_y), texto, fill="black", anchor="mm")

    # Texto principal en blanco arriba
    draw.text((pos_x, pos_y), texto, fill="white", anchor="mm")
    
    temp_path = f"TEMP/tit_{random.randint(1000,9999)}.png"
    img.save(temp_path)
    return temp_path

# --- MOTOR DE EDICIÓN ---
def procesar_video(input_p, output_p, mode, texto=None, pos=None):
    with VideoFileClip(input_p) as clip:
        clip_final = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        if mode == "tk":
            fondo = ColorClip(size=(1080, 1920), color=(0, 102, 204)).set_duration(clip.duration)
            clip_res = clip_final.resize(width=1080).set_position('center')
            clip_final = CompositeVideoClip([fondo, clip_res])
        
        if mode == "tit" and texto:
            img_path = crear_imagen_texto_pro(texto, clip.w)
            
            # Ajuste de posiciones según tus 5 ejemplos
            if pos == "arriba":
                y_final = 180 # Cerca del top pero con margen
            elif pos == "abajo":
                y_final = clip.h - 450 # Arriba de los botones de la app
            else:
                y_final = "center"

            txt_overlay = (ImageClip(img_path)
                           .set_duration(clip.duration)
                           .set_position(("center", y_final))
                           .resize(width=clip.w * 0.85)) # Que se vea imponente
            
            clip_final = CompositeVideoClip([clip_final, txt_overlay])

        clip_final.write_videofile(output_p, codec="libx264", audio_codec="aac", threads=1, preset="ultrafast", logger=None)

# --- RESTO DEL CÓDIGO (Igual al anterior) ---
@bot.message_handler(content_types=['video'])
def handle_video(message):
    user_data[message.chat.id] = {'file_id': message.video.file_id, 'step': 'inicio'}
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚀 Triturar Normal", callback_data="n"),
        types.InlineKeyboardButton("📱 Formato TikTok", callback_data="t"),
        types.InlineKeyboardButton("📝 Añadir Títulos (TikTok Style)", callback_data="p")
    )
    bot.send_message(message.chat.id, "Video recibido. Selecciona modo:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "p":
        user_data[call.message.chat.id]['step'] = 'wait'
        bot.send_message(call.message.chat.id, "✍️ Escribe el título:")
    else:
        ejecutar(call.message.chat.id, "norm" if call.data == "n" else "tk")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'wait')
def recibir_texto(message):
    user_data[message.chat.id]['step'] = 'proc'
    ejecutar(message.chat.id, "tit_3", texto=message.text)

def ejecutar(chat_id, modo, texto=None):
    status = bot.send_message(chat_id, "⏳ Procesando estilo Título 1...")
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
                    bot.send_video(chat_id, v, caption=f"🎬 Formato: {p}")
                os.remove(out_p)
        else:
            out_p = f"US/res_{chat_id}.mp4"
            procesar_video(in_p, out_p, modo)
            with open(out_p, 'rb') as v:
                bot.send_video(chat_id, v)
            os.remove(out_p)
        
        os.remove(in_p)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
    finally:
        bot.delete_message(chat_id, status.message_id)

st.title("🤖 OFM Processor v3.7")
bot.infinity_polling()
