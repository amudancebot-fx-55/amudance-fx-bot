import telebot
from telebot import types
from flask import Flask, request
import os
import json
import requests
import threading
import time
import random
from datetime import datetime, timedelta
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

# =========================
# CHECK ENV
# =========================
if not BOT_TOKEN:
    raise Exception("BOT_TOKEN missing")

if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY missing")

if not PAYSTACK_SECRET:
    raise Exception("PAYSTACK_SECRET_KEY missing")

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
SIGNAL_FILE = "signals.json"

# =========================
# CREATE FILES IF MISSING
# =========================
for file in [VIP_FILE, USER_FILE, SIGNAL_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

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
# VIP SYSTEM
# =========================
def add_vip(user_id, days):

    data = load(VIP_FILE)

    current = datetime.now().timestamp()

    if str(user_id) in data:
        old_expiry = data[str(user_id)]

        if old_expiry > current:
            expiry = old_expiry + (days * 86400)
        else:
            expiry = current + (days * 86400)

    else:
        expiry = current + (days * 86400)

    data[str(user_id)] = expiry

    save(VIP_FILE, data)

def is_vip(user_id):

    data = load(VIP_FILE)

    uid = str(user_id)

    if uid not in data:
        return False

    expiry = data[uid]

    if datetime.now().timestamp() > expiry:
        del data[uid]
        save(VIP_FILE, data)
        return False

    return True

# =========================
# USERS
# =========================
def add_user(uid):

    data = load(USER_FILE)

    if str(uid) not in data:

        data[str(uid)] = {
            "joined": str(datetime.now())
        }

        save(USER_FILE, data)

# =========================
# RATE LIMIT
# =========================
last_time = {}

def rate_limit(uid):

    now = time.time()

    if uid in last_time:

        if now - last_time[uid] < 8:
            return False

    last_time[uid] = now

    return True

# =========================
# SIMPLE SMC ENGINE
# =========================
def smc_engine():

    structure = random.choice([
        "Bullish structure with higher highs",
        "Bearish structure with lower lows",
        "Sideways consolidation"
    ])

    liquidity = random.choice([
        "Liquidity resting above highs",
        "Liquidity resting below lows",
        "Balanced liquidity"
    ])

    return structure, liquidity

# =========================
# START MENU
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    add_user(m.chat.id)

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    btn1 = types.KeyboardButton("📊 Analyze Chart")
    btn2 = types.KeyboardButton("💎 VIP Plans")
    btn3 = types.KeyboardButton("👤 My VIP")
    btn4 = types.KeyboardButton("📞 Support")

    markup.add(btn1, btn2)
    markup.add(btn3, btn4)

    text = (
        "🚀 AMUDANCE FX BOT\n\n"
        "AI Smart Money Concepts Analysis\n\n"
        "Send chart screenshot for instant analysis."
    )

    bot.send_message(
        m.chat.id,
        text,
        reply_markup=markup
    )

# =========================
# VIP MENU
# =========================
@bot.message_handler(func=lambda m: m.text == "💎 VIP Plans")
def vip_menu(m):

    markup = types.InlineKeyboardMarkup()

    b1 = types.InlineKeyboardButton(
        "7 Days - ₦2000",
        callback_data="pay_7"
    )

    b2 = types.InlineKeyboardButton(
        "30 Days - ₦5000",
        callback_data="pay_30"
    )

    b3 = types.InlineKeyboardButton(
        "90 Days - ₦12000",
        callback_data="pay_90"
    )

    markup.add(b1)
    markup.add(b2)
    markup.add(b3)

    bot.send_message(
        m.chat.id,
        "💎 Choose VIP Plan",
        reply_markup=markup
    )

# =========================
# PAYMENT CALLBACK
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def payment_callback(c):

    try:

        days = int(c.data.split("_")[1])

        if days == 7:
            amount = 2000

        elif days == 30:
            amount = 5000

        else:
            amount = 12000

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

        response = requests.post(
            url,
            json=payload,
            headers=headers
        )

        res = response.json()

        print("PAYSTACK:", res)

        if not res.get("status"):

            return bot.answer_callback_query(
                c.id,
                "Payment Error"
            )

        pay_link = (
            res.get("data", {})
            .get("authorization_url")
        )

        markup = types.InlineKeyboardMarkup()

        pay_btn = types.InlineKeyboardButton(
            "💳 PAY NOW",
            url=pay_link
        )

        markup.add(pay_btn)

        bot.send_message(
            c.message.chat.id,
            f"💎 VIP PLAN\n\n"
            f"Plan: {days} Days\n"
            f"Amount: ₦{amount}",
            reply_markup=markup
        )

    except Exception as e:

        print("PAY ERROR:", e)

        bot.send_message(
            c.message.chat.id,
            f"❌ ERROR:\n{e}"
        )

# =========================
# MY VIP
# =========================
@bot.message_handler(func=lambda m: m.text == "👤 My VIP")
def myvip(m):

    data = load(VIP_FILE)

    uid = str(m.chat.id)

    if uid not in data:
        return bot.reply_to(
            m,
            "❌ VIP inactive"
        )

    expiry = datetime.fromtimestamp(data[uid])

    bot.reply_to(
        m,
        f"💎 VIP ACTIVE\n\nExpires:\n{expiry}"
    )

# =========================
# SUPPORT
# =========================
@bot.message_handler(func=lambda m: m.text == "📞 Support")
def support(m):

    bot.reply_to(
        m,
        "📞 Contact Admin:\n@yourusername"
    )

# =========================
# ANALYZE BUTTON
# =========================
@bot.message_handler(func=lambda m: m.text == "📊 Analyze Chart")
def analyze_button(m):

    bot.reply_to(
        m,
        "📸 Send chart screenshot now"
    )

# =========================
# AI ANALYSIS
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def analyze(m):

    try:

        if not rate_limit(m.chat.id):

            return bot.reply_to(
                m,
                "⛔ Slow down"
            )

        loading = bot.reply_to(
            m,
            "📊 Analyzing market..."
        )

        # DOWNLOAD IMAGE
        if m.photo:

            file_info = bot.get_file(
                m.photo[-1].file_id
            )

        else:

            file_info = bot.get_file(
                m.document.file_id
            )

        downloaded = bot.download_file(
            file_info.file_path
        )

        path = f"chart_{m.chat.id}.jpg"

        with open(path, "wb") as f:
            f.write(downloaded)

        image = Image.open(path)

        vip = is_vip(m.chat.id)

        structure, liquidity = smc_engine()

        confidence = (
            random.randint(85, 97)
            if vip
            else random.randint(60, 80)
        )

        prompt = f"""
You are a professional Smart Money Concepts trader.

Follow this structure:

Market Structure:
{structure}

Liquidity:
{liquidity}

Analyze chart and return:

📊 Trend
📉 Structure
💧 Liquidity
📍 Entry
🛑 Stop Loss
🎯 Take Profit
📈 Bias
⚠ Risk
🔥 Confidence: {confidence}%

If unclear, say:
Uncertain market condition

User:
{'VIP' if vip else 'FREE'}
"""

        # GEMINI
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image]
        )

        result = res.text

        # SAVE SIGNAL
        signals = load(SIGNAL_FILE)

        signals[str(time.time())] = result

        save(SIGNAL_FILE, signals)

        # SEND RESULT
        bot.edit_message_text(
            chat_id=m.chat.id,
            message_id=loading.message_id,
            text=result
        )

        # REMOVE IMAGE
        os.remove(path)

    except Exception as e:

        print("ANALYSIS ERROR:", e)

        bot.reply_to(
            m,
            f"❌ ERROR:\n{e}"
        )

# =========================
# PAYSTACK WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():

    try:

        event = request.json

        print("WEBHOOK:", event)

        if event["event"] == "charge.success":

            metadata = (
                event["data"]
                .get("metadata", {})
            )

            user_id = metadata.get("user_id")
            days = metadata.get("days")

            if user_id and days:

                add_vip(
                    int(user_id),
                    int(days)
                )

                bot.send_message(
                    user_id,
                    f"🎉 PAYMENT SUCCESSFUL\n\n"
                    f"VIP ACTIVE FOR {days} DAYS"
                )

                bot.send_message(
                    ADMIN_ID,
                    f"💰 NEW VIP USER\n\n"
                    f"User ID: {user_id}\n"
                    f"Days: {days}"
                )

        return "OK", 200

    except Exception as e:

        print("WEBHOOK ERROR:", e)

        return "ERROR", 500

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return "AMUDANCE FX BOT RUNNING"

# =========================
# BOT RUNNER
# =========================
def run_bot():

    while True:

        try:

            print("BOT STARTING...")

            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                skip_pending=True
            )

        except Exception as e:

            print("BOT ERROR:", e)

            time.sleep(10)

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    bot_thread = threading.Thread(
        target=run_bot
    )

    bot_thread.daemon = True
    bot_thread.start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
                               )
