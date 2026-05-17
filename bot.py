import telebot
from telebot import types
from flask import Flask
import os, json, requests, threading, time, random
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from PIL import Image

# =========================
# ENV
# =========================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise Exception("Missing ENV")

# =========================
# INIT
# =========================
bot = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# =========================
# FILES
# =========================
VIP_FILE = "vip_data.json"
USER_FILE = "users.json"
TX_FILE = "transactions.json"
BAN_FILE = "banned.json"

for f in [VIP_FILE, USER_FILE, TX_FILE, BAN_FILE]:
    if not os.path.exists(f):
        with open(f, "w") as x:
            json.dump({}, x)

# =========================
# HELPERS
# =========================
def load(f):
    try:
        return json.load(open(f))
    except:
        return {}

def save(f, d):
    with open(f, "w") as x:
        json.dump(d, x, indent=4)

# =========================
# USER + BAN
# =========================
def is_banned(uid):
    return str(uid) in load(BAN_FILE)

def add_user(uid):
    d = load(USER_FILE)
    uid = str(uid)
    if uid not in d:
        d[uid] = {"joined": str(datetime.now())}
        save(USER_FILE, d)

# =========================
# VIP SYSTEM
# =========================
def add_vip(uid, days):
    d = load(VIP_FILE)
    uid = str(uid)
    now = datetime.now().timestamp()

    current = d.get(uid, 0)

    expiry = current + days * 86400 if current > now else now + days * 86400
    d[uid] = expiry
    save(VIP_FILE, d)

def is_vip(uid):
    d = load(VIP_FILE)
    uid = str(uid)

    if uid not in d:
        return False

    if datetime.now().timestamp() > d[uid]:
        del d[uid]
        save(VIP_FILE, d)
        return False

    return True

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    if is_banned(m.chat.id):
        return bot.send_message(m.chat.id, "⛔ Banned")

    add_user(m.chat.id)

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        types.KeyboardButton("📊 Analyze Chart"),
        types.KeyboardButton("💎 VIP Plans"),
        types.KeyboardButton("👤 My VIP"),
        types.KeyboardButton("📞 Support")
    )

    bot.send_message(m.chat.id, "🚀 FX SIGNAL ENGINE PRO", reply_markup=kb)

# =========================
# MENU
# =========================
@bot.message_handler(content_types=['text'])
def menu(m):

    if is_banned(m.chat.id):
        return

    add_user(m.chat.id)

    if m.text == "📊 Analyze Chart":
        bot.reply_to(m, "Send chart image")

    elif m.text == "💎 VIP Plans":
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("7 Days - ₦2000", callback_data="pay_7"),
            types.InlineKeyboardButton("30 Days - ₦5000", callback_data="pay_30"),
            types.InlineKeyboardButton("90 Days - ₦12000", callback_data="pay_90")
        )
        bot.send_message(m.chat.id, "VIP PLANS", reply_markup=kb)

    elif m.text == "👤 My VIP":
        d = load(VIP_FILE)
        uid = str(m.chat.id)

        if uid not in d:
            bot.reply_to(m, "❌ No VIP")
        else:
            bot.reply_to(m, f"VIP ACTIVE\nExpires: {datetime.fromtimestamp(d[uid])}")

    elif m.text == "📞 Support":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Admin", url="https://t.me/Amudancefx"))
        bot.send_message(m.chat.id, "Support", reply_markup=kb)

# =========================
# 🔥 ANALYSIS ENGINE (REAL SIGNAL PROMPT)
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def analyze(m):

    if is_banned(m.chat.id):
        return

    msg = bot.reply_to(m, "Analyzing market structure...")

    file = bot.get_file(m.photo[-1].file_id if m.photo else m.document.file_id)
    data = bot.download_file(file.file_path)

    path = f"{m.chat.id}.jpg"
    open(path, "wb").write(data)

    image = Image.open(path)

    confidence = random.randint(75, 95)

    # =========================
    # 🔥 ULTRA CLEAN FOREX PROMPT
    # =========================
    prompt = f"""
You are a PROFESSIONAL FOREX TRADING SIGNAL ENGINE.

Analyze ANY forex chart (ANY PAIR, ANY TIMEFRAME).

Return ONLY this format:

PAIR:
TIMEFRAME:

SIGNAL: BUY / SELL / WAIT

ENTRY:
STOP LOSS:
TAKE PROFIT:

STRUCTURE:
LIQUIDITY:
REASON:

RULES:
- If market is sideways → WAIT
- If unclear → WAIT
- If confidence < 75% → WAIT
- Always give realistic SL/TP based on structure
"""

    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image]
    )

    final_output = f"""
📊 FOREX SIGNAL ENGINE

{res.text}

━━━━━━━━━━━━━━
📡 Confidence: {confidence}%
━━━━━━━━━━━━━━
"""

    bot.edit_message_text(final_output, m.chat.id, msg.message_id)

    os.remove(path)

# =========================
# RUN BOT
# =========================
def run_bot():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except:
            time.sleep(5)

if __name__ == "__main__":

    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
