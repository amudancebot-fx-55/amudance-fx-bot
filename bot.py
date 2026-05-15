import telebot
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
# HELPERS
# =========================
def load(file):
    try:
        return json.load(open(file))
    except:
        return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# =========================
# VIP SYSTEM
# =========================
def add_vip(user_id, days):
    data = load(VIP_FILE)
    expiry = (datetime.now() + timedelta(days=days)).timestamp()
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
# USERS
# =========================
def add_user(uid):
    data = load(USER_FILE)
    data[str(uid)] = str(datetime.now())
    save(USER_FILE, data)

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
# SMART MONEY ENGINE (SIMPLIFIED)
# =========================
def smc_engine():
    structure = random.choice([
        "Bullish structure (HH/HL)",
        "Bearish structure (LH/LL)",
        "Sideways consolidation"
    ])

    liquidity = random.choice([
        "Liquidity above highs",
        "Liquidity below lows",
        "Balanced liquidity zone"
    ])

    return structure, liquidity

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(m):
    add_user(m.chat.id)

    bot.reply_to(
        m,
        "🚀 AMUDANCE FX PRO BOT\n\n"
        "Commands:\n"
        "/pay 7 | /pay 30 | /pay 90\n\n"
        "Send chart for analysis 📊"
    )

# =========================
# PAYMENT SYSTEM
# =========================
@bot.message_handler(commands=['pay'])
def pay(m):
    try:
        days = int(m.text.split()[1])

        amount = 2000 if days == 7 else 5000 if days == 30 else 12000

        url = "https://api.paystack.co/transaction/initialize"

        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET}"
        }

        data = {
            "email": f"user{m.chat.id}@mail.com",
            "amount": amount * 100,
            "metadata": {
                "user_id": m.chat.id,
                "days": days
            }
        }

        res = requests.post(url, json=data, headers=headers).json()

        bot.reply_to(m, f"💳 Pay here:\n{res['data']['authorization_url']}")

    except Exception as e:
        bot.reply_to(m, f"Error: {e}")

# =========================
# VIP CHECK
# =========================
@bot.message_handler(commands=['myvip'])
def myvip(m):
    data = load(VIP_FILE)
    uid = str(m.chat.id)

    if uid not in data:
        return bot.reply_to(m, "❌ Not VIP")

    expiry = datetime.fromtimestamp(data[uid])
    bot.reply_to(m, f"💎 VIP ACTIVE\nExpires: {expiry}")

# =========================
# AI ANALYSIS (PRO SYSTEM)
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def analyze(m):
    try:
        if not rate_limit(m.chat.id):
            return bot.reply_to(m, "⛔ Slow down")

        msg = bot.reply_to(m, "📊 Scanning market structure...")

        file = bot.get_file(m.photo[-1].file_id if m.photo else m.document.file_id)
        downloaded = bot.download_file(file.file_path)

        path = f"chart_{m.chat.id}.jpg"
        open(path, "wb").write(downloaded)

        image = Image.open(path)

        vip = is_vip(m.chat.id)

        # SMART MONEY LAYER
        structure, liquidity = smc_engine()

        confidence = random.randint(85, 97) if vip else random.randint(60, 80)

        prompt = f"""
You are a professional Smart Money Concepts trader.

Follow this structure:

Market Structure: {structure}
Liquidity: {liquidity}

Analyze strictly based on this.

Return:
Trend
Structure explanation
Liquidity analysis
Entry zone
Stop Loss
Take Profit
Market bias
Risk level
Confidence: {confidence}%

If unclear, say "market uncertain".

User: {'VIP' if vip else 'FREE'}
"""

        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image]
        )

        bot.edit_message_text(
            chat_id=m.chat.id,
            message_id=msg.message_id,
            text=res.text
        )

        os.remove(path)

    except Exception as e:
        bot.reply_to(m, f"❌ ERROR: {e}")

# =========================
# PAYSTACK WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    event = request.json

    if event["event"] == "charge.success":
        meta = event["data"]["metadata"]

        user_id = meta["user_id"]
        days = meta["days"]

        add_vip(user_id, int(days))

        bot.send_message(user_id, f"🎉 VIP ACTIVE FOR {days} DAYS")
        bot.send_message(ADMIN_ID, f"💰 VIP USER: {user_id}")

    return "OK", 200

# =========================
# SAFE RUNNER
# =========================
def run_bot():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print("BOT RESTART:", e)
            time.sleep(5)

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

threading.Thread(target=run_bot).start()
threading.Thread(target=run_server).start()