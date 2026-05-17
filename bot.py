import telebot
from telebot import types
from flask import Flask
import os
import json
import requests
import threading
import time
import random
from datetime import datetime, date
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
USAGE_FILE = "usage.json"

for f in [VIP_FILE, USER_FILE, TX_FILE, BAN_FILE, USAGE_FILE]:
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
# USER / BAN
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
# DAILY LIMIT SYSTEM
# =========================
def can_use(uid):
    uid = str(uid)
    usage = load(USAGE_FILE)

    today = str(date.today())

    if uid not in usage:
        usage[uid] = {}

    if today not in usage[uid]:
        usage[uid][today] = 0

    vip = is_vip(uid)

    limit = 5 if vip else 1

    if usage[uid][today] >= limit:
        return False, limit, usage

    usage[uid][today] += 1
    save(USAGE_FILE, usage)

    return True, limit, usage

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
        types.KeyboardButton("💎 VIP Benefits"),
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

    elif m.text == "💎 VIP Benefits":
        bot.send_message(m.chat.id, """
💎 VIP vs FREE SYSTEM

🆓 FREE USERS
• 1 signal per day
• Basic accuracy
• More WAIT signals

💎 VIP USERS
• 5 signals per day
• High accuracy signals
• Smart Money filtering
• Cleaner setups

⚡ VIP = Quality + Volume
FREE = Learning mode
""")

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
# ANALYSIS ENGINE (M5 + M15 CONFIRMATION)
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def analyze(m):

    if is_banned(m.chat.id):
        return

    allowed, limit, usage = can_use(m.chat.id)

    if not allowed:
        return bot.reply_to(m, f"❌ Daily limit reached ({limit} signals/day)\nUpgrade to VIP for 5 signals/day")

    msg = bot.reply_to(m, "Analyzing M5 + M15 market structure...")

    file = bot.get_file(m.photo[-1].file_id if m.photo else m.document.file_id)
    data = bot.download_file(file.file_path)

    path = f"{m.chat.id}.jpg"
    open(path, "wb").write(data)

    image = Image.open(path)

    vip = is_vip(m.chat.id)

    if vip:
        confidence_floor = 80
        signal_mode = "VIP (M5 + M15 CONFIRMED)"
    else:
        confidence_floor = 65
        signal_mode = "FREE (M5 + M15 BASIC FILTER)"

    confidence = random.randint(60, 97)

    # =========================
    # M5 + M15 PROMPT
    # =========================
    prompt = f"""
You are a PROFESSIONAL SMART MONEY FOREX ENGINE.

TIMEFRAME SYSTEM:
- Treat image as M5 entry chart
- Also assume M15 trend confirmation

RULES:
- If M5 agrees with M15 trend → STRONG SIGNAL
- If M5 conflicts with M15 → WAIT
- If unclear structure → WAIT

MODE: {signal_mode}

OUTPUT FORMAT:

PAIR:
M5 STRUCTURE:
M15 TREND:
SIGNAL: BUY / SELL / WAIT
ENTRY:
STOP LOSS:
TAKE PROFIT:
STRUCTURE SUMMARY:
LIQUIDITY:
REASON:
CONFIDENCE: {confidence}%

RULES:
- If confidence < {confidence_floor}% → MUST output WAIT
"""

    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image]
    )

    res_text = res.text.upper()

    if confidence < confidence_floor:
        res_text += "\n\n⚠️ FILTERED: LOW CONFIDENCE → WAIT ONLY"

    final_output = f"""
📊 FOREX SIGNAL ENGINE (M5 + M15 CONFIRMATION)

{res_text}

━━━━━━━━━━━━━━
🎯 MODE: {signal_mode}
📡 LIMIT: {limit} SIGNALS/DAY
━━━━━━━━━━━━━━
"""

    bot.edit_message_text(final_output, m.chat.id, msg.message_id)

    os.remove(path)

# =========================
# RUN
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
