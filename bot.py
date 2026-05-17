import telebot
from telebot import types
from flask import Flask, request
import os
import json
import requests
import threading
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from PIL import Image

# =========================
# LOAD ENV
# =========================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN or not GEMINI_API_KEY or not PAYSTACK_SECRET:
    raise Exception("Missing environment variables")

# =========================
# INIT
# =========================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# =========================
# FILES
# =========================
VIP_FILE = "vip_data.json"
USER_FILE = "users.json"
SIGNAL_FILE = "signals.json"

for f in [VIP_FILE, USER_FILE, SIGNAL_FILE]:
    if not os.path.exists(f):
        with open(f, "w") as x:
            json.dump({}, x)

# =========================
# HELPERS
# =========================
def load(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# USERS
# =========================
def add_user(uid):
    data = load(USER_FILE)
    if str(uid) not in data:
        data[str(uid)] = {"joined": str(datetime.now())}
        save(USER_FILE, data)

# =========================
# VIP SYSTEM
# =========================
def add_vip(user_id, days):
    data = load(VIP_FILE)
    now = datetime.now().timestamp()

    if str(user_id) in data and data[str(user_id)] > now:
        expiry = data[str(user_id)] + days * 86400
    else:
        expiry = now + days * 86400

    data[str(user_id)] = expiry
    save(VIP_FILE, data)

def is_vip(user_id):
    data = load(VIP_FILE)
    uid = str(user_id)

    if uid not in data:
        return False

    if datetime.now().timestamp() > data[uid]:
        del data[uid]
        save(VIP_FILE, data)
        return False

    return True

# =========================
# RATE LIMIT
# =========================
last_time = {}

def rate_limit(uid):
    now = time.time()
    if uid in last_time and now - last_time[uid] < 8:
        return False
    last_time[uid] = now
    return True

# =========================
# SMC ENGINE
# =========================
def smc_engine():
    return (
        random.choice([
            "Bullish structure with higher highs",
            "Bearish structure with lower lows",
            "Sideways consolidation"
        ]),
        random.choice([
            "Liquidity above highs",
            "Liquidity below lows",
            "Balanced liquidity"
        ])
    )

# =========================
# START MENU
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    add_user(m.chat.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    markup.add(
        types.KeyboardButton("📊 Analyze Chart"),
        types.KeyboardButton("💎 VIP Plans"),
        types.KeyboardButton("👤 My VIP"),
        types.KeyboardButton("📞 Support")
    )

    bot.send_message(
        m.chat.id,
        "🚀 AMUDANCE FX BOT\n\nSend chart screenshot for analysis.",
        reply_markup=markup
    )

# =========================
# MENU ROUTER (FIXED SAFE)
# =========================
@bot.message_handler(content_types=['text'])
def menu_router(m):

    add_user(m.chat.id)

    text = m.text

    if text == "📊 Analyze Chart":
        bot.reply_to(m, "📸 Send your chart screenshot now")

    elif text == "💎 VIP Plans":

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("7 Days - ₦2000", callback_data="pay_7"),
            types.InlineKeyboardButton("30 Days - ₦5000", callback_data="pay_30"),
            types.InlineKeyboardButton("90 Days - ₦12000", callback_data="pay_90")
        )

        bot.send_message(m.chat.id, "💎 Choose VIP Plan", reply_markup=markup)

    elif text == "👤 My VIP":

        data = load(VIP_FILE)
        uid = str(m.chat.id)

        if uid not in data:
            bot.reply_to(m, "❌ VIP inactive")
        else:
            expiry = datetime.fromtimestamp(data[uid])
            bot.reply_to(m, f"💎 VIP ACTIVE\nExpires: {expiry}")

    elif text == "📞 Support":

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📩 Contact Admin",
                url="https://t.me/Amudancefx"
            )
        )

        bot.send_message(
            m.chat.id,
            "📞 Support Center",
            reply_markup=markup
        )

    else:
        bot.reply_to(m, "Use the menu buttons 👇")

# =========================
# ANALYZE IMAGE
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def analyze(m):

    if not rate_limit(m.chat.id):
        return bot.reply_to(m, "⛔ Slow down")

    msg = bot.reply_to(m, "📊 Analyzing...")

    file = bot.get_file(m.photo[-1].file_id if m.photo else m.document.file_id)
    data = bot.download_file(file.file_path)

    path = f"chart_{m.chat.id}.jpg"
    with open(path, "wb") as f:
        f.write(data)

    image = Image.open(path)

    structure, liquidity = smc_engine()
    vip = is_vip(m.chat.id)

    confidence = random.randint(85, 97) if vip else random.randint(60, 80)

    prompt = f"""
Market Structure: {structure}
Liquidity: {liquidity}

Return:
Trend, Entry, SL, TP, Bias, Risk, Confidence {confidence}%
User: {'VIP' if vip else 'FREE'}
"""

    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image]
    )

    bot.edit_message_text(
        res.text,
        m.chat.id,
        msg.message_id
    )

    os.remove(path)

# =========================
# PAYSTACK CALLBACK
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def pay(c):

    days = int(c.data.split("_")[1])
    amount = {7:2000, 30:5000, 90:12000}[days]

    url = "https://api.paystack.co/transaction/initialize"

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}",
        "Content-Type": "application/json"
    }

    payload = {
        "email": f"user{c.message.chat.id}@mail.com",
        "amount": amount * 100,
        "metadata": {
            "user_id": c.message.chat.id,
            "days": days
        }
    }

    r = requests.post(url, json=payload, headers=headers).json()

    if not r.get("status"):
        return bot.answer_callback_query(c.id, "Error")

    link = r["data"]["authorization_url"]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 PAY NOW", url=link))

    bot.send_message(c.message.chat.id, f"VIP {days} DAYS - ₦{amount}", reply_markup=markup)

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():

    event = request.json

    if event["event"] == "charge.success":

        meta = event["data"]["metadata"]

        add_vip(meta["user_id"], meta["days"])

        bot.send_message(meta["user_id"], "🎉 VIP ACTIVATED")
        bot.send_message(ADMIN_ID, f"New VIP: {meta['user_id']}")

    return "OK"

# =========================
# RUN BOT (FIXED - NO CONFLICT)
# =========================
def run_bot():
    while True:
        try:
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True
            )
        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(5)

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    threading.Thread(target=run_bot, daemon=True).start()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
