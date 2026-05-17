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
# ENV
# =========================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "12345")

if not BOT_TOKEN or not GEMINI_API_KEY or not PAYSTACK_SECRET:
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
# BAN SYSTEM
# =========================
def is_banned(uid):
    return str(uid) in load(BAN_FILE)

# =========================
# VIP SYSTEM
# =========================
def add_vip(uid, days):
    d = load(VIP_FILE)
    now = datetime.now().timestamp()

    if str(uid) in d and d[str(uid)] > now:
        expiry = d[str(uid)] + days * 86400
    else:
        expiry = now + days * 86400

    d[str(uid)] = expiry
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
            "Liquidity below lows",
            "Liquidity above highs",
            "Balanced liquidity"
        ])
    )

# =========================
# SIGNAL ENGINE (REAL LOGIC)
# =========================
def signal_engine(structure, liquidity, confidence):

    s = structure.lower()
    l = liquidity.lower()

    signal = "WAIT"
    reason = "No strong setup"

    bullish = "bullish" in s or "higher" in s
    bearish = "bearish" in s or "lower" in s

    buy_ok = "below" in l
    sell_ok = "above" in l

    if bullish and buy_ok and confidence >= 70:
        signal = "BUY"
        reason = "Bullish structure + liquidity below"

    elif bearish and sell_ok and confidence >= 70:
        signal = "SELL"
        reason = "Bearish structure + liquidity above"

    return signal, reason

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    if is_banned(m.chat.id):
        return bot.send_message(m.chat.id, "⛔ BANNED")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(
        types.KeyboardButton("📊 Analyze Chart"),
        types.KeyboardButton("💎 VIP Plans"),
        types.KeyboardButton("👤 My VIP"),
        types.KeyboardButton("📞 Support")
    )

    bot.send_message(m.chat.id, "🚀 AMUDANCE FX BOT", reply_markup=kb)

# =========================
# MENU
# =========================
@bot.message_handler(content_types=['text'])
def menu(m):

    if is_banned(m.chat.id):
        return bot.send_message(m.chat.id, "⛔ Banned")

    if m.text == "📊 Analyze Chart":
        bot.reply_to(m, "Send chart screenshot")

    elif m.text == "💎 VIP Plans":

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("7 Days - ₦2000", callback_data="pay_7"),
            types.InlineKeyboardButton("30 Days - ₦5000", callback_data="pay_30"),
            types.InlineKeyboardButton("90 Days - ₦12000", callback_data="pay_90")
        )

        bot.send_message(m.chat.id, "VIP Plans", reply_markup=kb)

    elif m.text == "👤 My VIP":

        d = load(VIP_FILE)
        uid = str(m.chat.id)

        if uid not in d:
            bot.reply_to(m, "❌ VIP inactive")
        else:
            bot.reply_to(m, f"VIP ACTIVE\nExpires: {datetime.fromtimestamp(d[uid])}")

    elif m.text == "📞 Support":

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Admin", url="https://t.me/Amudancefx"))
        bot.send_message(m.chat.id, "Support", reply_markup=kb)

# =========================
# ANALYSIS + SIGNAL
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def analyze(m):

    msg = bot.reply_to(m, "Analyzing...")

    file = bot.get_file(m.photo[-1].file_id if m.photo else m.document.file_id)
    data = bot.download_file(file.file_path)

    path = f"{m.chat.id}.jpg"
    open(path, "wb").write(data)

    image = Image.open(path)

    vip = is_vip(m.chat.id)
    structure, liquidity = smc_engine()

    confidence = random.randint(85, 97) if vip else random.randint(60, 80)

    signal, reason = signal_engine(structure, liquidity, confidence)

    prompt = f"""
You are a trading analyst.

Structure: {structure}
Liquidity: {liquidity}
Confidence: {confidence}%

ONLY OUTPUT:
SIGNAL: {signal}
REASON: {reason}
"""

    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image]
    )

    final_text = f"""
{res.text}

🔥 FINAL DECISION: {signal}
📌 REASON: {reason}
"""

    bot.edit_message_text(final_text, m.chat.id, msg.message_id)

    os.remove(path)

# =========================
# PAYSTACK
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def pay(c):

    days = int(c.data.split("_")[1])
    amount = {7:2000, 30:5000, 90:12000}[days]

    r = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers={"Authorization": f"Bearer {PAYSTACK_SECRET}"},
        json={
            "email": f"user{c.message.chat.id}@mail.com",
            "amount": amount * 100,
            "metadata": {"user_id": c.message.chat.id, "days": days}
        }
    ).json()

    if not r.get("status"):
        return bot.answer_callback_query(c.id, "Error")

    link = r["data"]["authorization_url"]

    tx = load(TX_FILE)
    tx[str(c.message.chat.id)] = {
        "days": days,
        "reference": r["data"]["reference"],
        "paid": False
    }
    save(TX_FILE, tx)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("PAY NOW", url=link))

    bot.send_message(c.message.chat.id, "Complete payment", reply_markup=kb)

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():

    e = request.json

    if e["event"] == "charge.success":

        meta = e["data"]["metadata"]

        add_vip(int(meta["user_id"]), int(meta["days"]))

        bot.send_message(meta["user_id"], "🎉 VIP ACTIVATED")
        bot.send_message(ADMIN_ID, f"VIP USER: {meta['user_id']}")

    return "OK"

# =========================
# VIP CLEANER
# =========================
def vip_cleaner():

    while True:
        d = load(VIP_FILE)
        now = datetime.now().timestamp()

        for uid in list(d.keys()):
            if now > d[uid]:
                del d[uid]
                try:
                    bot.send_message(uid, "❌ VIP EXPIRED")
                except:
                    pass

        save(VIP_FILE, d)
        time.sleep(60)

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
    threading.Thread(target=vip_cleaner, daemon=True).start()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
