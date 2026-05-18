import telebot
from telebot import types
from flask import Flask
import os
import json
import time
import base64
from datetime import datetime
from dotenv import load_dotenv
from google import genai

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
FILES = ["users.json", "credits.json", "free_trial.json", "pending_payments.json"]

for f in FILES:
    if not os.path.exists(f):
        with open(f, "w") as x:
            json.dump({}, x)

# =========================
# GEMINI MODELS (AUTO FIX)
# =========================
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

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
# LIMIT MESSAGE (NEW)
# =========================
def limit_message():
    return (
        "⚠️ Bot is currently busy or limit reached.\n\n"
        "Please try again in 30 minutes or contact support."
    )

# =========================
# CREDIT SYSTEM
# =========================
def get_credit(uid):
    return load("credits.json").get(str(uid), 0)

def add_credit(uid, amt):
    d = load("credits.json")
    d[str(uid)] = d.get(str(uid), 0) + amt
    save("credits.json", d)

def use_credit(uid):
    d = load("credits.json")
    uid = str(uid)
    if d.get(uid, 0) > 0:
        d[uid] -= 1
        save("credits.json", d)
        return True
    return False

# =========================
# FREE SYSTEM
# =========================
FREE_LIMIT = 2

def get_free_used(uid):
    return load("free_trial.json").get(str(uid), 0)

def can_use_free(uid):
    return get_free_used(uid) < FREE_LIMIT

def use_free(uid):
    d = load("free_trial.json")
    d[str(uid)] = d.get(str(uid), 0) + 1
    save("free_trial.json", d)

# =========================
# TYPING DELAY
# =========================
def human_delay(chat_id, sec=2):
    bot.send_chat_action(chat_id, "typing")
    time.sleep(sec)

# =========================
# GEMINI SAFE CALL (FIXED)
# =========================
def call_gemini(prompt, image_base64):
    last_error = None

    for model in GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    prompt,
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            )
            return response.text
        except Exception as e:
            last_error = e

    return None

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
You are a Smart Money Concepts forex trader.

Analyze this chart:

1. Trend direction
2. Market structure (BOS / CHoCH)
3. Support & resistance
4. Liquidity zones
5. Best entry (BUY/SELL)
6. Stop loss
7. Take profit
8. Risk level
"""

        bot.send_message(message.chat.id, "📡 Upload received...")
        human_delay(message.chat.id, 1)

        bot.send_message(message.chat.id, "🧠 AI analyzing...")
        human_delay(message.chat.id, 1)

        bot.send_message(message.chat.id, "📊 Processing market structure...")
        human_delay(message.chat.id, 1)

        with open(path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()

        result = call_gemini(prompt, image_base64)

        if not result:
            bot.send_message(message.chat.id, limit_message())
            return

        bot.send_message(message.chat.id, f"✅ ANALYSIS COMPLETE\n\n{result}")

    except Exception:
        bot.send_message(message.chat.id, limit_message())

# =========================
# START
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
🎁 Free Left: {FREE_LIMIT - get_free_used(m.chat.id)}

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

    pending = load("pending_payments.json")
    uid = str(c.message.chat.id)

    pending[uid] = {
        "amount": int(amount),
        "credits": int(credits),
        "time": str(datetime.now())
    }
    save("pending_payments.json", pending)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ I HAVE PAID", callback_data=f"paid_{uid}")
    )

    bot.send_message(
        uid,
        f"""
🏦 BANK DETAILS
{BANK_NAME}
{ACCOUNT_NUMBER}
{ACCOUNT_NAME}

💰 Amount: ₦{amount}
💎 Credits: {credits}

⚠️ After payment click below
""",
        reply_markup=markup
    )

# =========================
# USER PAID
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("paid_"))
def user_paid(c):

    uid = c.data.split("_")[1]
    pending = load("pending_payments.json")

    if uid not in pending:
        return bot.answer_callback_query(c.id, "No pending payment")

    data = pending[uid]

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{uid}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{uid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"""
💰 PAYMENT REQUEST

User: {uid}
Amount: ₦{data['amount']}
Credits: {data['credits']}
Time: {data['time']}
""",
        reply_markup=markup
    )

    bot.answer_callback_query(c.id, "Sent for review")

# =========================
# ADMIN ACTION
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_") or c.data.startswith("reject_"))
def admin_action(c):

    if c.from_user.id != ADMIN_ID:
        return bot.answer_callback_query(c.id, "Not allowed")

    action, uid = c.data.split("_")
    pending = load("pending_payments.json")

    if uid not in pending:
        return bot.answer_callback_query(c.id, "Already processed")

    data = pending[uid]

    if action == "approve":
        add_credit(uid, data["credits"])
        bot.send_message(uid, f"✅ Approved!\n🎉 {data['credits']} credits added")
        bot.send_message(ADMIN_ID, "Approved")
    else:
        bot.send_message(uid, "❌ Rejected. Contact support.")
        bot.send_message(ADMIN_ID, "Rejected")

    del pending[uid]
    save("pending_payments.json", pending)

    bot.answer_callback_query(c.id, "Done")

# =========================
# IMAGE HANDLER
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def handle_image(m):

    try:
        if m.content_type == "photo":
            file_info = bot.get_file(m.photo[-1].file_id)
        else:
            if not m.document.mime_type.startswith("image/"):
                return bot.reply_to(m, "❌ Only images allowed")
            file_info = bot.get_file(m.document.file_id)

        uid = str(m.chat.id)
        pending = load("pending_payments.json")

        if uid in pending:
            if not use_credit(m.chat.id):
                return bot.reply_to(m, limit_message())
            analyze_market(m, file_info)
            return

        if can_use_free(m.chat.id):
            use_free(m.chat.id)
            analyze_market(m, file_info)
            return

        bot.reply_to(m, limit_message())

    except Exception:
        bot.reply_to(m, limit_message())

# =========================
# BALANCE
# =========================
@bot.message_handler(func=lambda m: m.text == "💰 My Balance")
def bal(m):
    bot.reply_to(m, f"💎 Credits: {get_credit(m.chat.id)}\n🎁 Free Left: {FREE_LIMIT - get_free_used(m.chat.id)}")

# =========================
# SUPPORT
# =========================
@bot.message_handler(func=lambda m: m.text == "📞 Support")
def support(m):
    bot.reply_to(m, "Contact: @Amudancefx")

# =========================
# ANALYZE
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
