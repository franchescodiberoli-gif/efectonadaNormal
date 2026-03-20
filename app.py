import os, telebot, random, textwrap
import PIL.Image, PIL.ImageDraw, PIL.ImageFont
import streamlit as st
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from telebot import types

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)
user_data = {}

for folder in ['VIDEO', 'US', 'TEMP']:
    os.makedirs(folder, exist_ok=True)

# --- MOTOR DE TEXTO ESTILO TIKTOK ---
def crear_imagen_texto(texto, ancho_video):
    """
    Genera una imagen PNG transparente con texto estilo TikTok:
    - Blanco, Bold, Mayúsculas
    - Borde negro grueso
    - Word wrap automático para que no se corten palabras
    """
    font_size = int(ancho_video * 0.11)  # ~11% del ancho → grande pero legible

    FONT_PATHS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    font = None
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                font = PIL.ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue
    if font is None:
        font = PIL.ImageFont.load_default()

    texto_upper = texto.upper()

    # ---- Word wrap inteligente ----
    # Calculamos cuántos caracteres caben por línea
    # Usamos un lienzo temporal para medir texto real
    tmp_img = PIL.Image.new('RGBA', (ancho_video * 3, font_size * 2), (0, 0, 0, 0))
    tmp_draw = PIL.ImageDraw.Draw(tmp_img)

    max_w = int(ancho_video * 0.92)

    def get_text_width(t):
        bbox = tmp_draw.textbbox((0, 0), t, font=font)
        return bbox[2] - bbox[0]

    # Dividir en palabras y armar líneas sin exceder max_w
    words = texto_upper.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if get_text_width(test) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            # Si una sola palabra es demasiado ancha, igual la ponemos
            current = word
    if current:
        lines.append(current)

    # ---- Calcular tamaño del lienzo ----
    line_height = int(font_size * 1.25)
    padding_v = 30
    img_h = line_height * len(lines) + padding_v * 2
    img_w = ancho_video  # mismo ancho que el video

    img = PIL.Image.new('RGBA', (img_w, img_h), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(img)

    stroke = max(6, font_size // 9)  # grosor del borde proporcional

    for i, line in enumerate(lines):
        x = img_w // 2
        y = padding_v + i * line_height + line_height // 2

        # Borde negro (dibujamos la misma letra desplazada en todas direcciones)
        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox * ox + oy * oy <= stroke * stroke:
                    draw.text((x + ox, y + oy), line,
                              fill=(0, 0, 0, 255), font=font, anchor="mm")

        # Texto blanco encima
        draw.text((x, y), line, fill=(255, 255, 255, 255), font=font, anchor="mm")

    return img


# --- MOTOR DE VIDEO ---
def procesar_video(in_path, out_path, texto, posicion):
    with VideoFileClip(in_path) as clip:
        ancho = clip.w
        alto = clip.h

        img_texto = crear_imagen_texto(texto, ancho)
        temp_img = f"TEMP/t_{random.randint(10000, 99999)}.png"
        img_texto.save(temp_img)

        img_h = img_texto.height
        margen = int(alto * 0.04)              # 4% margen general
        safe_bottom = int(alto * 0.18)         # zona segura TikTok (evita UI del app)

        if posicion == "arriba":
            pos_y = margen
        elif posicion == "abajo":
            pos_y = alto - img_h - safe_bottom
        else:  # medio
            pos_y = (alto - img_h) // 2

        txt_clip = (ImageClip(temp_img)
                    .set_duration(clip.duration)
                    .set_position(("center", pos_y)))

        video_final = CompositeVideoClip([clip, txt_clip])
        video_final.write_videofile(
            out_path,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            preset="ultrafast",
            logger=None
        )

        if os.path.exists(temp_img):
            os.remove(temp_img)


# ---------- HANDLERS TELEGRAM ----------

@bot.message_handler(commands=['start'])
def cmd_start(m):
    user_data[m.chat.id] = {}
    bot.send_message(m.chat.id,
        "👋 ¡Hola! Soy tu bot de contenido.\n\n📤 *Sube tu video* para empezar.",
        parse_mode="Markdown")


@bot.message_handler(content_types=['video', 'document'])
def recibir_video(m):
    cid = m.chat.id
    file_id = m.video.file_id if m.content_type == 'video' else m.document.file_id

    user_data[cid] = {'video_id': file_id, 'step': 'menu'}

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔤 TÍTULO", callback_data="accion_titulo"),
        # Aquí puedes agregar más botones en el futuro
    )

    bot.send_message(cid,
        "✅ *¡Video recibido!*\n\n¿Qué quieres hacer con él?",
        parse_mode="Markdown",
        reply_markup=markup)


# --- Botón: TÍTULO ---
@bot.callback_query_handler(func=lambda c: c.data == "accion_titulo")
def cb_titulo(c):
    cid = c.message.chat.id
    bot.answer_callback_query(c.id)

    if 'video_id' not in user_data.get(cid, {}):
        bot.send_message(cid, "❌ Primero sube un video.")
        return

    user_data[cid]['step'] = 'esperando_titulo'
    bot.send_message(cid, "✍️ Escribe el *TÍTULO* que quieres agregar al video:",
                     parse_mode="Markdown")


# --- Nuevo video ---
@bot.callback_query_handler(func=lambda c: c.data == "nuevo_video")
def cb_nuevo(c):
    cid = c.message.chat.id
    bot.answer_callback_query(c.id)
    user_data[cid] = {}
    bot.send_message(cid, "📤 Envía tu nuevo video:")


# --- Recibir título y procesar ---
@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'esperando_titulo')
def procesar_titulo(m):
    cid = m.chat.id
    texto = m.text.strip()

    if not texto or texto.startswith('/'):
        bot.send_message(cid, "⚠️ Escribe un título válido.")
        return

    user_data[cid]['step'] = 'procesando'
    status_msg = bot.send_message(
        cid,
        f"⏳ Generando 3 versiones con:\n*{texto.upper()}*\n\nEsto puede tardar un momento...",
        parse_mode="Markdown"
    )

    try:
        # Descargar video original
        info = bot.get_file(user_data[cid]['video_id'])
        data_bytes = bot.download_file(info.file_path)
        in_p = f"VIDEO/in_{cid}.mp4"
        with open(in_p, 'wb') as f:
            f.write(data_bytes)

        posiciones = [
            ("arriba", "⬆️ Título ARRIBA"),
            ("medio",  "⏺️ Título AL CENTRO"),
            ("abajo",  "⬇️ Título ABAJO"),
        ]

        for pos, label in posiciones:
            out_p = f"US/{pos}_{cid}.mp4"
            procesar_video(in_p, out_p, texto, pos)
            with open(out_p, 'rb') as v:
                bot.send_video(cid, v, caption=label, supports_streaming=True)
            if os.path.exists(out_p):
                os.remove(out_p)

        if os.path.exists(in_p):
            os.remove(in_p)

        # Borrar mensaje de estado
        try:
            bot.delete_message(cid, status_msg.message_id)
        except Exception:
            pass

        # Menú post-proceso
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔤 Otro TÍTULO", callback_data="accion_titulo"),
            types.InlineKeyboardButton("📤 Nuevo video", callback_data="nuevo_video"),
        )
        user_data[cid]['step'] = 'menu'
        bot.send_message(cid, "✅ ¡Listo! ¿Qué más quieres hacer?", reply_markup=markup)

    except Exception as e:
        bot.send_message(cid, f"❌ Error al procesar: {str(e)}")
        user_data[cid]['step'] = 'menu'


# ---------- STREAMLIT UI ----------
st.title("🤖 OFM Pro — Bot activo ✅")
st.caption("El bot de Telegram está corriendo. No cierres esta pestaña.")

bot.infinity_polling()
