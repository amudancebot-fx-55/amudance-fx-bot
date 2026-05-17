import telebot
from telebot import types
from flask import Flask, request
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

if not BOT_TOKEN or not GEMINI_API_KEY or not PAYSTACK_SECRET:
    raise Exception("Missing ENV variables")

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
        with open(f, "r") as x:
            return json.load(x)
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
# CREDIT SYSTEM (FIXED)
# =========================
def can_use(uid):

    uid = str(uid)
    usage = load(USAGE_FILE)

    if uid not in usage:
        usage[uid] = {
            "last_free_use": None,
            "vip_credits": 0,
            "vip_last_reset": str(date.today()),
            "signal_credits": 0
        }

    today = str(date.today())
    vip = is_vip(uid)

    # =========================
    # FREE USERS (STRICT 7 DAYS COOLDOWN)
    # =========================
    if not vip:

        last = usage[uid]["last_free_use"]

        if last:
            last_date = datetime.strptime(last, "%Y-%m-%d").date()
            days = (date.today() - last_date).days

            if days < 7:
                return False, 0, usage

        usage[uid]["last_free_use"] = today
        save(USAGE_FILE, usage)

        return True, 0, usage

    # =========================
    # VIP USERS (2 DAILY)
    # =========================
    last_reset = datetime.strptime(
        usage[uid]["vip_last_reset"],
        "%Y-%m-%d"
    ).date()

    days_passed = (date.today() - last_reset).days

    if days_passed >= 1:
        usage[uid]["vip_credits"] += days_passed * 2
        usage[uid]["vip_last_reset"] = today
        save(USAGE_FILE, usage)

    if usage[uid]["vip_credits"] <= 0:
        return False, 0, usage

    usage[uid]["vip_credits"] -= 1
    save(USAGE_FILE, usage)

    return True, usage[uid]["vip_credits"], usage

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    if is_banned(m.chat.id):
        return bot.send_message(m.chat.id, "⛔ BANNED")

    add_user(m.chat.id)

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("📊 Analyze Chart", "💎 VIP Plans")
    kb.add("💎 VIP Benefits", "👤 My VIP")
    kb.add("📞 Support")

    bot.send_message(
        m.chat.id,
        "🚀 FX SIGNAL ENGINE PRO",
        reply_markup=kb
    )

# =========================
# MENU
# =========================
@bot.message_handler(content_types=['text'])
def menu(m):

    if is_banned(m.chat.id):
        return

    add_user(m.chat.id)

    if m.text == "📊 Analyze Chart":

        allowed, credits, _ = can_use(m.chat.id)

        if not allowed:
            return bot.reply_to(
                m,
                "❌ NO SIGNAL CREDITS\n\n🆓 Free: 1 per 7 days\n⚡ ₦500 = 1 signal\n💎 VIP: 2 daily"
            )

        bot.reply_to(m, f"📤 SEND CHART\n🎟 Credits: {credits}")

    elif m.text == "💎 VIP Plans":

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💎 VIP 5 DAYS - ₦2000", callback_data="pay_vip"))
        kb.add(types.InlineKeyboardButton("⚡ 1 SIGNAL - ₦500", callback_data="pay_signal"))

        bot.send_message(m.chat.id, "💎 STORE", reply_markup=kb)

# =========================
# ANALYSIS ENGINE
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def analyze(m):

    if is_banned(m.chat.id):
        return

    msg = bot.reply_to(m, "📡 ANALYZING...")

    file = bot.get_file(m.photo[-1].file_id if m.photo else m.document.file_id)
    data = bot.download_file(file.file_path)

    path = f"{m.chat.id}.jpg"
    open(path, "wb").write(data)

    image = Image.open(path)

    vip = is_vip(m.chat.id)

    confidence = random.randint(60, 97)
    floor = 80 if vip else 65

    prompt = f"""
FOREX SMART MONEY ANALYSIS
MODE: {"VIP" if vip else "FREE"}
CONFIDENCE: {confidence}%
"""

    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image]
    )

    text = res.text.upper()

    if confidence < floor:
        text += "\n\n⚠️ WAIT ONLY"

    _, credits, _ = can_use(m.chat.id)

    bot.edit_message_text(
        f"{text}\n\n🎟 Credits: {credits}",
        m.chat.id,
        msg.message_id
    )

    os.remove(path)

# =========================
# PAYSTACK
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def pay(c):

    plans = {
        "pay_vip": {"amount": 2000, "type": "vip", "days": 5},
        "pay_signal": {"amount": 500, "type": "signal", "credits": 1}
    }

    plan = plans[c.data]
    amount = plan["amount"]

    res = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers={"Authorization": f"Bearer {PAYSTACK_SECRET}"},
        json={
            "email": f"user{c.message.chat.id}@gmail.com",
            "amount": amount * 100,
            "metadata": {
                "user_id": c.message.chat.id,
                "type": plan["type"],
                "days": plan.get("days", 0),
                "credits": plan.get("credits", 0)
            }
        }
    ).json()

    link = res["data"]["authorization_url"]
    ref = res["data"]["reference"]

    tx = load(TX_FILE)
    tx[ref] = {"user": c.message.chat.id, "plan": plan}
    save(TX_FILE, tx)

    bot.send_message(c.message.chat.id, f"PAY HERE: {link}")

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():

    event = request.json

    if event["event"] != "charge.success":
        return "OK"

    data = event["data"]
    ref = data["reference"]

    tx = load(TX_FILE)
    if ref not in tx:
        return "OK"

    user = str(tx[ref]["user"])
    plan = tx[ref]["plan"]

    usage = load(USAGE_FILE)

    if plan["type"] == "vip":
        add_vip(user, plan["days"])
        usage[user]["vip_credits"] += 2

    else:
        usage[user]["signal_credits"] += 1

    save(USAGE_FILE, usage)

    tx[ref]["paid"] = True
    save(TX_FILE, tx)

    bot.send_message(int(user), "✅ PAYMENT SUCCESSFUL")

    return "OK"

# =========================
# RUN
# =========================
def run():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
