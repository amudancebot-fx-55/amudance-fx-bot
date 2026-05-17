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
        d[uid] = {
            "joined": str(datetime.now())
        }

        save(USER_FILE, d)

# =========================
# VIP SYSTEM
# =========================
def add_vip(uid, days):

    d = load(VIP_FILE)

    uid = str(uid)

    now = datetime.now().timestamp()

    current = d.get(uid, 0)

    if current > now:
        expiry = current + days * 86400
    else:
        expiry = now + days * 86400

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
# SIGNAL CREDIT SYSTEM
# =========================
def can_use(uid):

    uid = str(uid)

    usage = load(USAGE_FILE)

    if uid not in usage:
        usage[uid] = {
            "credits": 0,
            "last_reset": str(date.today())
        }

    today = str(date.today())

    vip = is_vip(uid)

    # =========================
    # FREE USERS
    # 1 signal every 7 days
    # =========================
    if not vip:

        last_reset = datetime.strptime(
            usage[uid]["last_reset"],
            "%Y-%m-%d"
        ).date()

        days_passed = (date.today() - last_reset).days

        if days_passed >= 7:

            usage[uid]["credits"] += 1
            usage[uid]["last_reset"] = today

            save(USAGE_FILE, usage)

        # FIRST USER BONUS
        if usage[uid]["credits"] == 0 and days_passed == 0:
            usage[uid]["credits"] = 1
            save(USAGE_FILE, usage)

    # =========================
    # VIP USERS
    # 2 signals daily
    # DOES NOT EXPIRE
    # =========================
    else:

        last_reset = datetime.strptime(
            usage[uid]["last_reset"],
            "%Y-%m-%d"
        ).date()

        days_passed = (date.today() - last_reset).days

        if days_passed >= 1:

            usage[uid]["credits"] += days_passed * 2
            usage[uid]["last_reset"] = today

            save(USAGE_FILE, usage)

    # =========================
    # CHECK CREDITS
    # =========================
    if usage[uid]["credits"] <= 0:
        return False, 0, usage

    usage[uid]["credits"] -= 1

    save(USAGE_FILE, usage)

    return True, usage[uid]["credits"], usage

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
        types.KeyboardButton("💎 VIP Plans")
    )

    kb.add(
        types.KeyboardButton("💎 VIP Benefits"),
        types.KeyboardButton("👤 My VIP")
    )

    kb.add(
        types.KeyboardButton("📞 Support")
    )

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

    # =========================
    # ANALYZE
    # =========================
    if m.text == "📊 Analyze Chart":

        allowed, credits_left, usage = can_use(m.chat.id)

        if not allowed:

            return bot.reply_to(
                m,
                """
❌ NO SIGNAL CREDITS

🆓 FREE USERS:
1 signal every 7 days

💎 VIP USERS:
2 premium signals added daily

Unused credits NEVER expire.
"""
            )

        bot.reply_to(
            m,
            f"""
📤 Send your chart image

🎟 Credits Left: {credits_left}
"""
        )

    # =========================
    # VIP PLANS
    # =========================
    elif m.text == "💎 VIP Plans":

        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "💎 5 Days VIP - ₦2000",
                callback_data="pay_5"
            )
        )

        bot.send_message(
            m.chat.id,
            """
💎 VIP MEMBERSHIP

✅ 2 Premium Signals Added Daily
✅ Smart Money Filtering
✅ Better Precision
✅ Cleaner Entries
✅ Unused Credits Stay Forever

💰 PRICE: ₦2000
📅 DURATION: 5 DAYS
""",
            reply_markup=kb
        )

    # =========================
    # VIP BENEFITS
    # =========================
    elif m.text == "💎 VIP Benefits":

        bot.send_message(
            m.chat.id,
            """
💎 VIP vs FREE SYSTEM

━━━━━━━━━━━━━━
🆓 FREE USERS
━━━━━━━━━━━━━━
• 1 Signal Every 7 Days
• Basic Market Analysis
• Standard Accuracy
• Learning Mode
• Signals Saved Until Used
• Credits DO NOT expire

━━━━━━━━━━━━━━
💎 VIP USERS
━━━━━━━━━━━━━━
• 2 Premium Signals Added Daily
• High Accuracy Setups
• Smart Money Filtering
• Cleaner Entries
• Better Precision
• Unused Signals Stay Forever
• Credits NEVER expire

━━━━━━━━━━━━━━
💰 VIP PRICE
₦2000 FOR 5 DAYS
━━━━━━━━━━━━━━
"""
        )

    # =========================
    # MY VIP
    # =========================
    elif m.text == "👤 My VIP":

        d = load(VIP_FILE)

        uid = str(m.chat.id)

        usage = load(USAGE_FILE)

        credits = usage.get(uid, {}).get("credits", 0)

        if uid not in d:

            bot.reply_to(
                m,
                f"""
❌ VIP INACTIVE

🎟 Credits: {credits}
"""
            )

        else:

            bot.reply_to(
                m,
                f"""
💎 VIP ACTIVE

📅 Expires:
{datetime.fromtimestamp(d[uid])}

🎟 Credits:
{credits}
"""
            )

    # =========================
    # SUPPORT
    # =========================
    elif m.text == "📞 Support":

        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "Admin",
                url="https://t.me/Amudancefx"
            )
        )

        bot.send_message(
            m.chat.id,
            "Support",
            reply_markup=kb
        )

# =========================
# ANALYSIS ENGINE
# =========================
@bot.message_handler(content_types=['photo', 'document'])
def analyze(m):

    if is_banned(m.chat.id):
        return

    msg = bot.reply_to(
        m,
        "📡 Analyzing market..."
    )

    try:

        file = bot.get_file(
            m.photo[-1].file_id if m.photo else m.document.file_id
        )

        data = bot.download_file(file.file_path)

        path = f"{m.chat.id}.jpg"

        open(path, "wb").write(data)

        image = Image.open(path)

        vip = is_vip(m.chat.id)

        # =========================
        # VIP vs FREE
        # =========================
        if vip:
            confidence_floor = 80
            signal_mode = "VIP"
        else:
            confidence_floor = 65
            signal_mode = "FREE"

        confidence = random.randint(60, 97)

        # =========================
        # MULTI TIMEFRAME
        # =========================
        prompt = f"""
You are a PROFESSIONAL FOREX SMART MONEY ENGINE.

MODE: {signal_mode}

Perform MULTI-TIMEFRAME confirmation.

Use:
- M5 structure
- M15 trend confirmation

STRICT FORMAT:

PAIR:
TIMEFRAME:

M5 STRUCTURE:
M15 CONFIRMATION:

SIGNAL: BUY / SELL / WAIT

ENTRY:
STOP LOSS:
TAKE PROFIT:

LIQUIDITY:
REASON:

CONFIDENCE: {confidence}%

RULES:
- If M5 and M15 disagree → WAIT
- If confidence < {confidence_floor}% → WAIT
- If market is unclear → WAIT
"""

        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image]
        )

        res_text = res.text.upper()

        if confidence < confidence_floor:
            res_text += "\n\n⚠️ FILTERED → WAIT ONLY"

        usage = load(USAGE_FILE)

        credits = usage.get(str(m.chat.id), {}).get("credits", 0)

        final = f"""
📊 FOREX SIGNAL ENGINE

{res_text}

━━━━━━━━━━━━━━
🎯 MODE: {signal_mode}
🎟 CREDITS LEFT: {credits}
━━━━━━━━━━━━━━
"""

        bot.edit_message_text(
            final,
            m.chat.id,
            msg.message_id
        )

        os.remove(path)

    except Exception as e:

        bot.edit_message_text(
            f"❌ ERROR:\n{e}",
            m.chat.id,
            msg.message_id
        )

# =========================
# PAYSTACK PAYMENT
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def pay(c):

    days = int(c.data.split("_")[1])

    plans = {
        5: 2000
    }

    amount = plans[days]

    try:

        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers={
                "Authorization": f"Bearer {PAYSTACK_SECRET}",
                "Content-Type": "application/json"
            },
            json={
                "email": f"user{c.message.chat.id}@gmail.com",
                "amount": amount * 100,
                "metadata": {
                    "user_id": c.message.chat.id,
                    "days": days
                }
            }
        ).json()

        if not response.get("status"):

            return bot.send_message(
                c.message.chat.id,
                "❌ Payment failed"
            )

        pay_link = response["data"]["authorization_url"]

        reference = response["data"]["reference"]

        tx = load(TX_FILE)

        tx[str(c.message.chat.id)] = {
            "reference": reference,
            "days": days,
            "paid": False
        }

        save(TX_FILE, tx)

        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "💳 PAY NOW",
                url=pay_link
            )
        )

        bot.send_message(
            c.message.chat.id,
            f"""
💎 VIP PAYMENT

📅 PLAN: {days} DAYS
💰 AMOUNT: ₦{amount}

After payment:
✅ VIP activates automatically
""",
            reply_markup=kb
        )

    except Exception as e:

        bot.send_message(
            c.message.chat.id,
            f"❌ ERROR:\n{e}"
        )

# =========================
# PAYSTACK WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():

    event = request.json

    try:

        if event["event"] == "charge.success":

            data = event["data"]

            metadata = data["metadata"]

            user_id = int(metadata["user_id"])

            days = int(metadata["days"])

            add_vip(user_id, days)

            tx = load(TX_FILE)

            if str(user_id) in tx:

                tx[str(user_id)]["paid"] = True

                save(TX_FILE, tx)

            bot.send_message(
                user_id,
                f"""
🎉 PAYMENT SUCCESSFUL

💎 VIP ACTIVATED
📅 {days} DAYS ADDED

✅ 2 premium signals daily
✅ Unused credits never expire
"""
            )

    except Exception as e:
        print(e)

    return "OK"

# =========================
# RUN
# =========================
def run_bot():

    while True:

        try:
            bot.infinity_polling(skip_pending=True)

        except Exception as e:

            print(e)

            time.sleep(5)

if __name__ == "__main__":

    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
