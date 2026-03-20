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

# --- FUNCIÓN PARA CREAR TEXTO FORMATO TÍTULO 1 ---
def crear_imagen_texto(texto, ancho_video):
    # Definimos un tamaño de fuente "Título 1" (10% del ancho del video)
    tamanio_fuente = int(ancho_video * 0.10)
    
    # Creamos una imagen transparente alta para dar espacio al texto grande
    img = PIL.Image.new('RGBA', (ancho_video, tamanio_fuente + 100), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(img)
    
    try:
        # Intentamos cargar la fuente por defecto
        font = PIL.ImageFont.load_default()
        # Nota: load_default() no permite cambiar tamaño en versiones viejas.
        # Si esto se ve pequeño, te recomendaré subir una fuente .ttf a tu GitHub.
    except:
        font = None

    # Dibujamos el texto en Blanco con un "borde" negro para que resalte (Título 1 Style)
    pos_x = ancho_video // 2
    pos_y = (tamanio_fuente + 100) // 2
    
    # Simulación de negrita/borde para legibilidad
    for adj in range(-3, 4):
        draw.text((pos_x + adj, pos_y), texto, fill="black", anchor="mm")
        draw.text((pos_x, pos_y + adj), texto, fill="black", anchor="mm")
    
    draw.text((pos_x, pos_y), texto, fill="white", anchor="mm")
    
    temp_path = f"TEMP/tit1_{random.randint(1000,9999)}.png"
    img.save(temp_path)
    return temp_path

# --- MOTOR DE EDICIÓN ---
def procesar_video(input_p, output_p, mode, texto=None, pos=None):
    with VideoFileClip(input_p) as clip:
        # 1. Triturado Base
        clip_final = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        # 2. Lógica TikTok
        if mode == "tk":
            fondo = ColorClip(size=(1080, 1920), color=(0, 102, 204)).set_duration(clip.duration)
            clip_res = clip_final.resize(width=1080).set_position('center')
            clip_final = CompositeVideoClip([fondo, clip_res])
        
        # 3. Lógica de Títulos Incrustados
        if mode == "tit" and texto:
            img_path = crear_imagen_texto(texto, clip.w)
            
            # Ajuste de coordenadas según posición
            if pos == "arriba":
                y_final = 150
            elif pos == "abajo":
                y_final = clip.h - 400
            else:
                y_final = "center"

            txt_overlay = (ImageClip(img_path)
                           .set_duration(clip.duration)
                           .set_position(("center", y_final))
                           .resize(width=clip.w * 0.9)) # Aseguramos que el título sea imponente
            
            clip_final = CompositeVideoClip([clip_final, txt_overlay])

        # Renderizado optimizado
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
    status = bot.send_message(chat_id, "⏳ Generando contenido... esto toma un momento.")
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
                    bot.send_video(chat_id, v, caption=f"✅ Título 1 - Posición: {p}")
                if os.path.exists(out_p): os.remove(out_p)
        else:
            out_p = f"US/res_{chat_id}.mp4"
            procesar_video(in_p, out_p, modo)
            with open(out_p, 'rb') as v:
                bot.send_video(chat_id, v, caption="🔥 ¡Listo!")
            if os.path.exists(out_p): os.remove(out_p)
        
        if os.path.exists(in_p):
