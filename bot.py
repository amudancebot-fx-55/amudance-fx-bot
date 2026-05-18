import telebot
from telebot import types
from flask import Flask
import os
import json
import threading
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
SIGNAL_FILE = "signals.json"
VIP_FILE = "vip_users.json"
REF_FILE = "referrals.json"

for f in [USER_FILE, CREDIT_FILE, FREE_FILE, PENDING_FILE, SIGNAL_FILE, VIP_FILE, REF_FILE]:
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
# USER
# =========================
def add_user(user):
    d = load(USER_FILE)
    uid = str(user.id)

    if uid not in d:
        d[uid] = {
            "username": user.username,
            "name": user.first_name,
            "joined": str(datetime.now())
        }
        save(USER_FILE, d)

# =========================
# CREDIT SYSTEM
# =========================
def get_credit(uid):
    return load(CREDIT_FILE).get(str(uid), 0)

def add_credit(uid, amt):
    d = load(CREDIT_FILE)
    d[str(uid)] = d.get(str(uid), 0) + amt
    save(CREDIT_FILE, d)

def remove_credit(uid, amt=1):
    d = load(CREDIT_FILE)
    if d.get(str(uid), 0) >= amt:
        d[str(uid)] -= amt
        save(CREDIT_FILE, d)
        return True
    return False

# =========================
# FREE SYSTEM
# =========================
FREE_LIMIT = 2

def get_free_used(uid):
    return load(FREE_FILE).get(str(uid), 0)

def free_left(uid):
    return max(0, FREE_LIMIT - get_free_used(uid))

def use_free(uid):
    d = load(FREE_FILE)
    d[str(uid)] = d.get(str(uid), 0) + 1
    save(FREE_FILE, d)

# =========================
# VIP
# =========================
def is_vip(uid):
    return str(uid) in load(VIP_FILE)

# =========================
# REFERRAL
# =========================
def add_ref(uid):
    d = load(REF_FILE)
    uid = str(uid)

    if uid not in d:
        d[uid] = {"count": 0}

    d[uid]["count"] += 1
    save(REF_FILE, d)

# =========================
# RATE LIMIT
# =========================
last_time = {}

def rate_limit(uid):
    now = time.time()
    if uid in last_time and now - last_time[uid] < 6:
        return False
    last_time[uid] = now
    return True

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    add_user(m.from_user)

    args = m.text.split()

    if len(args) > 1:
        ref = args[1]
        if ref != str(m.chat.id):
            add_ref(ref)
            add_credit(int(ref), 2)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Analyze Market", "💳 Buy Credits")
    markup.row("💰 My Balance", "👑 VIP Upgrade")
    markup.row("📞 Support")

    bot.send_message(
        m.chat.id,
        f"""
🚀 AMUDANCE FX AI

🎁 Free Left: {free_left(m.chat.id)}
💎 Credits: {get_credit(m.chat.id)}
👑 VIP: {"YES" if is_vip(m.chat.id) else "NO"}

Choose option 👇
""",
        reply_markup=markup
    )

# =========================
# BUY CREDITS
# =========================
@bot.message_handler(func=lambda m: m.text == "💳 Buy Credits")
def buy(m):

    markup = types.InlineKeyboardMarkup()

    plans = [
        (500, 1),
        (1000, 2),
        (2000, 4),
        (3000, 6),
        (5000, 10),
        (10000, 20),
    ]

    for price, credits in plans:
        markup.add(
            types.InlineKeyboardButton(
                f"🔥 {credits} Credits – ₦{price}",
                callback_data=f"buy_{price}_{credits}"
            )
        )

    bot.send_message(m.chat.id, "💎 Select plan:", reply_markup=markup)

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
💳 PAY NOW

🏦 {BANK_NAME}
🔢 {ACCOUNT_NUMBER}
👤 {ACCOUNT_NAME}

💰 ₦{amount}
💎 {credits} credits

Click "✅ I Paid"
"""
    )

# =========================
# I PAID
# =========================
@bot.message_handler(func=lambda m: m.text == "✅ I Paid")
def paid(m):

    pending = load(PENDING_FILE)

    if str(m.chat.id) not in pending:
        return bot.reply_to(m, "❌ No pending payment")

    bot.send_message(m.chat.id, "📸 Send screenshot")

# =========================
# PHOTO HANDLER
# =========================
@bot.message_handler(content_types=['photo'])
def photo(m):

    pending = load(PENDING_FILE)

    if str(m.chat.id) in pending:

        data = pending[str(m.chat.id)]

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{m.chat.id}_{data['credits']}"),
            types.InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{m.chat.id}")
        )

        bot.send_photo(
            ADMIN_ID,
            m.photo[-1].file_id,
            caption=f"Payment ₦{data['amount']} - {data['credits']} credits",
            reply_markup=markup
        )

        return bot.reply_to(m, "📤 Sent for approval")

    analyze(m)

# =========================
# APPROVE
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):

    _, uid, credits = c.data.split("_")
    uid = int(uid)
    credits = int(credits)

    add_credit(uid, credits)

    pending = load(PENDING_FILE)
    if str(uid) in pending:
        del pending[str(uid)]
        save(PENDING_FILE, pending)

    bot.send_message(uid, f"✅ Approved +{credits} credits")

# =========================
# REJECT
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

    bot.send_message(
        m.chat.id,
        f"💎 {get_credit(m.chat.id)} credits\n👑 VIP: {'YES' if is_vip(m.chat.id) else 'NO'}"
    )

# =========================
# VIP
# =========================
@bot.message_handler(func=lambda m: m.text == "👑 VIP Upgrade")
def vip(m):

    bot.send_message(
        m.chat.id,
        "👑 VIP = Unlimited analysis\nContact admin @Amudancefx"
    )

# =========================
# 🔥 FULL AI ANALYSIS RESTORED
# =========================
def analyze(m):

    try:

        if not rate_limit(m.chat.id):
            return bot.reply_to(m, "⛔ Slow down")

        vip = is_vip(m.chat.id)

        if not vip:

            if free_left(m.chat.id) > 0:
                use_free(m.chat.id)

            elif get_credit(m.chat.id) < 1:
                return bot.reply_to(m, "❌ Buy credits or VIP")
            else:
                remove_credit(m.chat.id, 1)

        loading = bot.reply_to(m, "📊 AI analyzing...")

        file = bot.get_file(m.photo[-1].file_id)
        img = bot.download_file(file.file_path)

        path = f"chart_{m.chat.id}_{int(time.time())}.jpg"

        with open(path, "wb") as f:
            f.write(img)

        image = Image.open(path)

        prompt = """
You are a professional Smart Money Concepts trader.

Analyze:
- Structure
- Liquidity
- BOS / CHoCH
- Entry, SL, TP
- Bias BUY or SELL only

If unclear: "No setup detected"

FORMAT CLEAN TRADING OUTPUT.
"""

        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image]
        )

        result = res.text

        if vip:
            result += "\n\n👑 VIP MODE"

        bot.edit_message_text(
            result,
            chat_id=m.chat.id,
            message_id=loading.message_id
        )

        os.remove(path)

    except Exception as e:
        bot.reply_to(m, f"❌ Error:\n{e}")

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
