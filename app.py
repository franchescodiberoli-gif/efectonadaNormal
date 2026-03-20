import os
import telebot
import random
import streamlit as st
from telebot import types
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, vfx
import PIL.Image

# Parche para compatibilidad de imágenes
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)
user_data = {}

# Crear carpetas si no existen
for folder in ['VIDEO', 'US']:
    os.makedirs(folder, exist_ok=True)

# --- MOTOR DE EDICIÓN ---
def procesar_video(input_p, output_p, mode, texto=None, pos=None):
    with VideoFileClip(input_p) as clip:
        # Efecto base: Espejo + Rotación
        clip_final = clip.fx(vfx.mirror_x).rotate(random.choice([-2.5, 2.5]))
        
        if mode == "tk":
            fondo = ColorClip(size=(1080, 1920), color=(0, 102, 204)).set_duration(clip.duration)
            clip_res = clip_final.resize(width=1080).set_position('center')
            clip_final = CompositeVideoClip([fondo, clip_res])
        
        # Lógica de Títulos (Requiere ImageMagick en el servidor)
        if mode == "titulo" and texto:
            from moviepy.video.VideoClip import TextClip
            try:
                txt = TextClip(texto, fontsize=70, color='white', font='Arial-Bold', method='caption', width=clip.w*0.8)
                positions = {"arriba": ("center", 50), "medio": ("center", "center"), "abajo": ("center", clip.h-150)}
                txt = txt.set_start(0).set_duration(clip.duration).set_position(positions[pos])
                clip_final = CompositeVideoClip([clip_final, txt])
            except Exception as e:
                print(f"Error en TextClip: {e}")

        clip_final.write_videofile(output_p, codec="libx264", audio_codec="aac", logger=None, threads=4)

# --- FUNCIONES DE AYUDA ---
def ejecutar_proceso(chat_id, modo, texto=None):
    status = bot.send_message(chat_id, f"⏳ Procesando... espera un poco.")
    try:
        file_info = bot.get_file(user_data[chat_id]['file_id'])
        downloaded = bot.download_file(file_info.file_path)
        in_p = f"VIDEO/in_{chat_id}.mp4"
        
        with open(in_p, 'wb') as f:
            f.write(downloaded)

        if modo == "modo_titulo":
            for p in ["arriba", "medio", "abajo"]:
                out_p = f"US/{p}_{chat_id}.mp4"
                procesar_video(in_p, out_p, "titulo", texto, p)
                with open(out_p, 'rb') as
