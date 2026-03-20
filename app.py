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

def crear_imagen_texto_pro(texto, ancho_video):
    font_size = int(ancho_video * 0.12) 
    img = PIL.Image.new('RGBA', (ancho_video, font_size + 150), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(img)
    try:
        font = PIL.ImageFont.load_default() 
    except:
        font = None

    pos_x = ancho_video // 2
    pos_y = (font_size + 150) // 2

    # Borde grueso estilo TikTok
    stroke = 5
    for ox in range(-stroke, stroke + 1):
        for oy in range(-stroke, stroke + 1):
            draw.text((pos_x + ox, pos_y + oy), texto, fill="black", anchor="mm")

    draw.text((pos_x, pos_y), texto, fill="white", anchor="mm")
    temp_path = f"TEMP/tit_{random.randint(1000,9999)}.png"
    img.save(temp_path)
    return temp_path

def procesar_video(input_p, output_p, mode, texto=None, pos=None):
    # Usamos audio=False si no es necesario para ahorrar 50% de memoria
    with VideoFileClip(input_p) as clip:
        clip_final = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        if mode == "tit" and texto:
            img_path = crear_imagen_texto_pro(texto, clip.w)
            # Posiciones exactas de tus ejemplos
            y_map = {"arriba": 200, "medio": "center", "abajo": clip.h - 450}
            y_final = y_map.get(pos, "center")

            txt_overlay = (ImageClip(img_path)
                           .set_duration(clip.duration)
                           .set_position(("center", y_final))
                           .resize(width=clip.w * 0.85))
            
            clip_final = CompositeVideoClip([clip_final, txt_overlay])

        # Preset 'ultrafast' es CLAVE para que no se cierre el proceso
        clip_final.write_videofile(output_p, codec="libx264", audio_codec="aac", 
                                   threads=1, preset="ultrafast", logger=None)

@bot.message_handler(content_types=['video'])
def handle_video(message):
    user_data[message.chat.id] = {'file_id': message.video.file_id}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 Añadir Títulos TikTok", callback_data="btn_p"))
    bot.send_message(message.chat.id, "✅ Video listo. ¿Quieres ponerle títulos?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "btn_p")
def ask_for_text(call):
    user_data[call.message.chat.id]['step'] = 'waiting_text'
    bot.edit_message_text("✍️ Escribe el título ahora:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'waiting_text')
def start_processing(message):
    # Bloqueamos el estado inmediatamente para evitar duplicados
    user_data[message.chat.id]['step'] = 'processing'
    texto_usuario = message.text
    chat_id = message.chat.id
    
    status = bot.send_message(chat_id, "⏳ Generando las 3 versiones... no cierres el chat.")
    
    try:
        file_info = bot.get_file(user_data[chat_id]['file_id'])
        downloaded = bot.download_file(file_info.file_path)
        in_p = f"VIDEO/in_{chat_id}.mp4"
        with open(in_p, 'wb') as f: f.write(downloaded)

        # Procesamos uno por uno para no saturar la RAM
        for p in ["arriba", "medio", "abajo"]:
            out_p = f"US/{p}_{chat_id}.mp4"
            procesar_video(in_p, out_p, "tit", texto_usuario, p)
            with open(out_p, 'rb') as v:
                bot.send_video(chat_id, v, caption=f"📍 Posición: {p}")
            os.remove(out_p)
            
        os.remove(in_p)
        bot.send_message(chat_id, "🔥 ¡Todos los videos listos!")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
    finally:
        user_data[chat_id]['step'] = None # Reset
        bot.delete_message(chat_id, status.message_id)

st.title("🤖 OFM Triturador v3.8")
bot.infinity_polling()
