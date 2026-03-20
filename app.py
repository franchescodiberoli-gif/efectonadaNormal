import os, telebot, random
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


# ─────────────────────────────────────────────
#  GENERADOR DE IMAGEN DE TEXTO ESTILO TIKTOK
# ─────────────────────────────────────────────
def crear_imagen_texto(texto, ancho_video, alto_video):
    """
    Genera PNG transparente con texto estilo TikTok:
    - Blanco Bold MAYÚSCULAS + borde negro grueso
    - Word-wrap real en píxeles
    - Tamaño = 14 % del ALTO del video (siempre grande en 9:16)
    """

    # --- Fuente ---
    font_size = max(60, int(alto_video * 13))

    FONT_PATHS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
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

    # --- Word-wrap por píxeles ---
    texto_up = texto.upper()
    max_px   = int(ancho_video * 0.90)

    _tmp = PIL.Image.new('RGBA', (1, 1))
    _d   = PIL.ImageDraw.Draw(_tmp)

    def txt_w(t):
        bb = _d.textbbox((0, 0), t, font=font)
        return bb[2] - bb[0]

    def txt_h(t):
        bb = _d.textbbox((0, 0), t, font=font)
        return bb[3] - bb[1]

    words = texto_up.split()
    lines = []
    linea = ""
    for word in words:
        prueba = (linea + " " + word).strip()
        if txt_w(prueba) <= max_px:
            linea = prueba
        else:
            if linea:
                lines.append(linea)
            linea = word
    if linea:
        lines.append(linea)

    # --- Canvas ---
    una_h    = txt_h("Ag")
    espaciado = int(una_h * 0.20)
    stroke    = max(8, font_size // 8)
    pad_v     = stroke + 10

    bloque_h = una_h * len(lines) + espaciado * (len(lines) - 1)
    img_h    = bloque_h + pad_v * 2
    img_w    = ancho_video

    img  = PIL.Image.new('RGBA', (img_w, img_h), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(img)

    # --- Dibujar líneas ---
    for i, linea in enumerate(lines):
        x = img_w // 2
        y = pad_v + i * (una_h + espaciado) + una_h // 2

        # Borde negro
        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox * ox + oy * oy <= stroke * stroke:
                    draw.text((x + ox, y + oy), linea,
                              fill=(0, 0, 0, 255), font=font, anchor="mm")
        # Texto blanco
        draw.text((x, y), linea,
                  fill=(255, 255, 255, 255), font=font, anchor="mm")

    return img


# ─────────────────────────────────────────────
#  PROCESADOR DE VIDEO
# ─────────────────────────────────────────────
def procesar_video(in_path, out_path, texto, posicion):
    with VideoFileClip(in_path) as clip:
        W, H = clip.w, clip.h

        img_texto = crear_imagen_texto(texto, W, H)
        tmp_png   = f"TEMP/t_{random.randint(10000,99999)}.png"
        img_texto.save(tmp_png)

        img_h = img_texto.height

        margen_top    = int(H * 0.04)
        margen_bottom = int(H * 0.20)

        if posicion == "arriba":
            pos_y = margen_top
        elif posicion == "abajo":
            pos_y = H - img_h - margen_bottom
        else:
            pos_y = (H - img_h) // 2

        pos_y = max(0, min(pos_y, H - img_h))

        txt_clip = (ImageClip(tmp_png)
                    .set_duration(clip.duration)
                    .set_position(("center", pos_y)))

        final = CompositeVideoClip([clip, txt_clip], size=(W, H))
        final.write_videofile(
            out_path,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            preset="ultrafast",
            logger=None,
        )

        if os.path.exists(tmp_png):
            os.remove(tmp_png)


# ─────────────────────────────────────────────
#  HANDLERS TELEGRAM
# ─────────────────────────────────────────────

@bot.message_handler(commands=['start'])
def cmd_start(m):
    user_data[m.chat.id] = {}
    bot.send_message(
        m.chat.id,
        "👋 ¡Hola! Soy tu bot de reciclaje de contenido.\n\n📤 *Sube tu video* para empezar.",
        parse_mode="Markdown"
    )


@bot.message_handler(content_types=['video', 'document'])
def recibir_video(m):
    cid = m.chat.id
    file_id = m.video.file_id if m.content_type == 'video' else m.document.file_id
    user_data[cid] = {'video_id': file_id, 'step': 'menu'}

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 AÑADIR TÍTULO (3 posiciones)", callback_data="accion_titulo"),
    )
    bot.send_message(
        cid,
        "✅ *¡Video recibido!*\n\n¿Qué quieres hacer con él?",
        parse_mode="Markdown",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data == "accion_titulo")
def cb_titulo(c):
    cid = c.message.chat.id
    bot.answer_callback_query(c.id)
    if 'video_id' not in user_data.get(cid, {}):
        bot.send_message(cid, "❌ Primero sube un video.")
        return
    user_data[cid]['step'] = 'esperando_titulo'
    bot.send_message(cid, "🖊️ Escribe el *TÍTULO* que quieres poner en el video:",
                     parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "nuevo_video")
def cb_nuevo(c):
    cid = c.message.chat.id
    bot.answer_callback_query(c.id)
    user_data[cid] = {}
    bot.send_message(cid, "📤 Envía tu nuevo video:")


@bot.message_handler(
    func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'esperando_titulo'
)
def procesar_titulo(m):
    cid   = m.chat.id
    texto = m.text.strip() if m.text else ""

    if not texto or texto.startswith('/'):
        bot.send_message(cid, "⚠️ Escribe un título válido.")
        return

    user_data[cid]['step'] = 'procesando'
    status = bot.send_message(
        cid,
        f"⏳ Procesando 3 versiones con:\n*{texto.upper()}*\n\nEspera un momento...",
        parse_mode="Markdown"
    )

    try:
        info = bot.get_file(user_data[cid]['video_id'])
        raw  = bot.download_file(info.file_path)
        in_p = f"VIDEO/in_{cid}.mp4"
        with open(in_p, 'wb') as f:
            f.write(raw)

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

        try:
            bot.delete_message(cid, status.message_id)
        except Exception:
            pass

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📝 Otro título", callback_data="accion_titulo"),
            types.InlineKeyboardButton("📤 Nuevo video", callback_data="nuevo_video"),
        )
        user_data[cid]['step'] = 'menu'
        bot.send_message(cid, "✅ ¡Listo! ¿Qué más quieres hacer?", reply_markup=markup)

    except Exception as e:
        bot.send_message(cid, f"❌ Error: {str(e)}")
        user_data[cid]['step'] = 'menu'


# ─────────────────────────────────────────────
#  STREAMLIT
# ─────────────────────────────────────────────
st.title("🤖 OFM Pro — Bot activo ✅")
st.caption("El bot está corriendo. No cierres esta pestaña.")

bot.infinity_polling()
