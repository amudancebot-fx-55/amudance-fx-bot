import telebot
from telebot import types
from flask import Flask
import os
import json
import time
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
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN missing")

if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY missing")

# =========================
# BANK DETAILS
# =========================
BANK_NAME = "OPay"
ACCOUNT_NUMBER = "7048508048"
ACCOUNT_NAME = "AMUJO TIMILEHIN"

# =========================
# INIT
# =========================
bot = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# =========================
# FILES
# =========================
USER_FILE = "users.json"
CREDIT_FILE = "credits.json"
FREE_FILE = "free_trial.json"
PENDING_FILE = "pending_payments.json"

for f in [USER_FILE, CREDIT_FILE, FREE_FILE, PENDING_FILE]:
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
# CREDIT SYSTEM
# =========================
def get_credit(uid):
    return load(CREDIT_FILE).get(str(uid), 0)

def add_credit(uid, amt):
    d = load(CREDIT_FILE)
    d[str(uid)] = d.get(str(uid), 0) + amt
    save(CREDIT_FILE, d)

def use_credit(uid):
    d = load(CREDIT_FILE)
    uid = str(uid)
    if d.get(uid, 0) > 0:
        d[uid] -= 1
        save(CREDIT_FILE, d)
        return True
    return False

# =========================
# FREE SYSTEM
# =========================
FREE_LIMIT = 2

def get_free_used(uid):
    return load(FREE_FILE).get(str(uid), 0)

def can_use_free(uid):
    return get_free_used(uid) < FREE_LIMIT

def use_free(uid):
    d = load(FREE_FILE)
    d[str(uid)] = d.get(str(uid), 0) + 1
    save(FREE_FILE, d)

# =========================
# TYPING DELAY
# =========================
def human_delay(chat_id, sec=2):
    bot.send_chat_action(chat_id, "typing")
    time.sleep(sec)

# =========================
# AI ANALYSIS
# =========================
def analyze_market(message, file_info):
    try:
        file = bot.download_file(file_info.file_path)

        path = f"chart_{message.chat.id}.jpg"
        with open(path, "wb") as f:
            f.write(file)

        prompt = """
You are a professional Smart Money Concepts forex trader.

Analyze this chart:

1. Trend direction
2. Market structure (BOS / CHoCH)
3. Support & resistance
4. Liquidity zones
5. Best entry (BUY/SELL)
6. Stop loss
7. Take profit
8. Risk level

Be precise and structured.
"""

        with open(path, "rb") as img:

            bot.send_message(message.chat.id, "📡 Upload received...")
            human_delay(message.chat.id, 2)

            bot.send_message(message.chat.id, "🧠 AI analyzing market...")
            human_delay(message.chat.id, 2)

            bot.send_message(message.chat.id, "📊 Detecting structure...")
            human_delay(message.chat.id, 3)

            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[prompt, img]
            )

            human_delay(message.chat.id, 2)

            bot.send_message(
                message.chat.id,
                f"✅ ANALYSIS COMPLETE\n\n{response.text}"
            )

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ AI error: {e}")

# =========================
# START MENU
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Analyze Market", "💳 Buy Credits")
    markup.row("💰 My Balance", "📞 Support")

    bot.send_message(
        m.chat.id,
        f"""
🚀 AMUDANCE FX AI

💎 Credits: {get_credit(m.chat.id)}
🎁 Free Uses: {FREE_LIMIT - get_free_used(m.chat.id)}

Choose option 👇
""",
        reply_markup=markup
    )

# =========================
# BUY MENU
# =========================
@bot.message_handler(func=lambda m: m.text == "💳 Buy Credits")
def buy(m):

    markup = types.InlineKeyboardMarkup()
    plans = [(500,1),(1000,2),(2000,4),(3000,6),(5000,10),(10000,20)]

    for price, credits in plans:
        markup.add(
            types.InlineKeyboardButton(
                f"{credits} Credits - ₦{price}",
                callback_data=f"buy_{price}_{credits}"
            )
        )

    bot.send_message(m.chat.id, "💎 Choose plan:", reply_markup=markup)

# =========================
# BUY CALLBACK
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy_callback(c):

    _, amount, credits = c.data.split("_")

    pending = load(PENDING_FILE)
    pending[str(c.message.chat.id)] = {
        "amount": int(amount),
        "credits": int(credits),
        "time": str(datetime.now())
    }
    save(PENDING_FILE, pending)

    bot.send_message(
        c.message.chat.id,
        f"""
🏦 BANK DETAILS
{BANK_NAME}
{ACCOUNT_NUMBER}
{ACCOUNT_NAME}

💰 Amount: ₦{amount}
💎 Credits: {credits}
"""
    )

# =========================
# IMAGE HANDLER (AUTO FIX + LOGIC)
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def handle_image(m):

    if m.content_type == "photo":
        file_info = bot.get_file(m.photo[-1].file_id)

    elif m.content_type == "document":
        if not m.document.mime_type.startswith("image/"):
            return bot.reply_to(m, "❌ Only images allowed")
        file_info = bot.get_file(m.document.file_id)

    pending = load(PENDING_FILE)

    # =========================
    # PAYMENT USERS
    # =========================
    if str(m.chat.id) in pending:

        if not use_credit(m.chat.id):
            return bot.reply_to(m, "❌ No credits left. Buy more.")

        analyze_market(m, file_info)
        return

    # =========================
    # FREE USERS
    # =========================
    if can_use_free(m.chat.id):

        use_free(m.chat.id)
        analyze_market(m, file_info)
        return

    # =========================
    # BLOCKED USERS
    # =========================
    bot.reply_to(m, "❌ Free trial ended. Buy credits to continue.")

# =========================
# APPROVE PAYMENT
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):

    _, uid, credits = c.data.split("_")
    uid = int(uid)

    add_credit(uid, int(credits))

    pending = load(PENDING_FILE)
    if str(uid) in pending:
        del pending[str(uid)]
        save(PENDING_FILE, pending)

    bot.send_message(uid, f"✅ Approved +{credits} credits")

# =========================
# REJECT PAYMENT
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):

    _, uid = c.data.split("_")
    uid = int(uid)

    pending = load(PENDING_FILE)
    if str(uid) in pending:
        del pending[str(uid)]
        save(PENDING_FILE, pending)

    bot.send_message(uid, "❌ Payment rejected")

# =========================
# BALANCE
# =========================
@bot.message_handler(func=lambda m: m.text == "💰 My Balance")
def bal(m):
    bot.reply_to(m,
        f"💎 Credits: {get_credit(m.chat.id)}\n🎁 Free left: {FREE_LIMIT - get_free_used(m.chat.id)}"
    )

# =========================
# SUPPORT
# =========================
@bot.message_handler(func=lambda m: m.text == "📞 Support")
def support(m):
    bot.reply_to(m, "Contact: @Amudancefx")

# =========================
# ANALYZE BUTTON
# =========================
@bot.message_handler(func=lambda m: m.text == "📊 Analyze Market")
def ask(m):
    bot.reply_to(m, "📸 Send chart screenshot")

# =========================
# FLASK
# =========================
@app.route("/")
def home():
    return "BOT RUNNING"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
