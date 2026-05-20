import telebot
from telebot import types
from flask import Flask
import os
import json
import time
import base64
import threading
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
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# =========================
# FILES
# =========================
FILES = [
    "users.json",
    "credits.json",
    "free_trial.json",
    "pending_payments.json"
]

for f in FILES:
    if not os.path.exists(f):
        with open(f, "w") as x:
            json.dump({}, x)

# =========================
# GEMINI MODEL
# =========================
GEMINI_MODEL = "gemini-2.5-flash"

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
# SAVE USERS
# =========================
def save_user(user):

    users = load("users.json")

    uid = str(user.id)

    users[uid] = {
        "id": user.id,
        "name": user.first_name,
        "username": user.username
    }

    save("users.json", users)

# =========================
# MAIN MENU
# =========================
def main_menu():

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row(
        "📊 Analyze Market",
        "💳 Buy Credits"
    )

    markup.row(
        "💰 My Balance",
        "📞 Support"
    )

    markup.row(
        "📢 Broadcast"
    )

    return markup

# =========================
# LIMIT MESSAGE
# =========================
def limit_message():
    return (
        "⚠️ Server busy or analysis limit reached.\n\n"
        "Please wait a few minutes and try again."
    )

# =========================
# CREDIT SYSTEM
# =========================
def get_credit(uid):

    d = load("credits.json")

    return d.get(str(uid), 0)

def add_credit(uid, amt):

    d = load("credits.json")

    uid = str(uid)

    d[uid] = d.get(uid, 0) + amt

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
# FREE TRIAL SYSTEM
# ONLY FIRST TIME EVER
# =========================
FREE_LIMIT = 2

def get_free_used(uid):

    d = load("free_trial.json")

    return d.get(str(uid), 0)

def can_use_free(uid):

    return get_free_used(uid) < FREE_LIMIT

def use_free(uid):

    d = load("free_trial.json")

    uid = str(uid)

    d[uid] = d.get(uid, 0) + 1

    save("free_trial.json", d)

# =========================
# HUMAN DELAY
# =========================
def human_delay(chat_id, sec=1):

    bot.send_chat_action(chat_id, "typing")

    time.sleep(sec)

# =========================
# SPLIT LONG MESSAGE
# =========================
def send_long_message(chat_id, text):

    limit = 4000

    for i in range(0, len(text), limit):

        bot.send_message(
            chat_id,
            text[i:i + limit]
        )

# =========================
# SAFE GEMINI CALL
# =========================
def call_gemini(prompt, image_base64):

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
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

        if response.text:
            return response.text

    except Exception as e:

        print("Gemini Error:", e)

    return None

# =========================
# AI ANALYSIS
# =========================
def analyze_market(message, file_info):

    try:

        file = bot.download_file(
            file_info.file_path
        )

        path = f"chart_{message.chat.id}.jpg"

        with open(path, "wb") as f:
            f.write(file)

        prompt = """
You are an elite institutional forex trader and Smart Money Concepts expert.

Analyze this forex chart professionally.

FORMAT STRICTLY:

━━━━━━━━━━━━━━━━━━
🚀 AMUDANCE FX
━━━━━━━━━━━━━━━━━━

📈 MARKET ANALYSIS

1️⃣ Trend Direction
2️⃣ Market Structure (BOS / CHoCH)
3️⃣ Key Support & Resistance
4️⃣ Liquidity Zones
5️⃣ Institutional Bias
6️⃣ Best Entry
7️⃣ Stop Loss
8️⃣ Take Profit Targets
9️⃣ Risk Level
🔟 Final Recommendation

RULES:
- Use professional emojis
- Make formatting very clean
- Make analysis easy to read
- Sound like a premium institutional analyst
- Avoid confusion
- Avoid overly long explanations
- Be accurate and realistic
- Use modern trading terminology
- Add spacing properly

End with:

━━━━━━━━━━━━━━━━━━
⚠️ Trade responsibly
━━━━━━━━━━━━━━━━━━
"""

        # LOADING
        bot.send_message(
            message.chat.id,
            "📡 Upload received..."
        )

        human_delay(message.chat.id)

        bot.send_message(
            message.chat.id,
            "🧠 Analyzing market structure..."
        )

        human_delay(message.chat.id)

        bot.send_message(
            message.chat.id,
            "📊 Detecting liquidity zones..."
        )

        human_delay(message.chat.id)

        bot.send_message(
            message.chat.id,
            "🏦 Tracking institutional activity..."
        )

        human_delay(message.chat.id)

        with open(path, "rb") as f:

            image_bytes = f.read()

        image_base64 = base64.b64encode(
            image_bytes
        ).decode()

        result = call_gemini(
            prompt,
            image_base64
        )

        if not result:

            bot.send_message(
                message.chat.id,
                limit_message()
            )

            return

        final_text = f"""
✅ <b>ANALYSIS COMPLETE</b>

{result}
"""

        send_long_message(
            message.chat.id,
            final_text
        )

        try:
            os.remove(path)
        except:
            pass

    except Exception as e:

        print("Analysis Error:", e)

        bot.send_message(
            message.chat.id,
            "⚠️ Unable to analyze chart right now.\nPlease try again later."
        )

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    save_user(m.from_user)

    bot.send_message(
        m.chat.id,
        f"""
━━━━━━━━━━━━━━━━━━
🚀 <b>AMUDANCE FX</b>
━━━━━━━━━━━━━━━━━━

📊 Professional Market Analysis

💎 Credits:
<b>{get_credit(m.chat.id)}</b>

🎁 Free Trial Left:
<b>{FREE_LIMIT - get_free_used(m.chat.id)}</b>

Choose an option below 👇
""",
        reply_markup=main_menu()
    )

# =========================
# BUY MENU
# =========================
@bot.message_handler(
    func=lambda m:
    m.text == "💳 Buy Credits"
)
def buy(m):

    markup = types.InlineKeyboardMarkup()

    plans = [
        (500, 1),
        (1000, 2),
        (2000, 4),
        (3000, 6),
        (5000, 10),
        (10000, 20)
    ]

    for price, credits in plans:

        markup.add(
            types.InlineKeyboardButton(
                f"{credits} Credits - ₦{price}",
                callback_data=f"buy_{price}_{credits}"
            )
        )

    bot.send_message(
        m.chat.id,
        "💎 Choose your credit plan:",
        reply_markup=markup
    )

# =========================
# BUY CALLBACK
# =========================
@bot.callback_query_handler(
    func=lambda c:
    c.data.startswith("buy_")
)
def buy_callback(c):

    _, amount, credits = c.data.split("_")

    uid = str(c.message.chat.id)

    pending = load("pending_payments.json")

    pending[uid] = {
        "amount": int(amount),
        "credits": int(credits),
        "time": str(datetime.now())
    }

    save("pending_payments.json", pending)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ I HAVE PAID",
            callback_data=f"paid_{uid}"
        )
    )

    bot.send_message(
        uid,
        f"""
🏦 <b>PAYMENT DETAILS</b>

🏛 Bank:
<b>{BANK_NAME}</b>

💳 Account Number:
<code>{ACCOUNT_NUMBER}</code>

👤 Account Name:
<b>{ACCOUNT_NAME}</b>

💰 Amount:
<b>₦{amount}</b>

💎 Credits:
<b>{credits}</b>

⚠️ After payment click the button below.
""",
        reply_markup=markup
    )

# =========================
# USER PAID
# =========================
@bot.callback_query_handler(
    func=lambda c:
    c.data.startswith("paid_")
)
def user_paid(c):

    uid = c.data.split("_")[1]

    pending = load("pending_payments.json")

    if uid not in pending:

        return bot.answer_callback_query(
            c.id,
            "No pending payment found"
        )

    data = pending[uid]

    user = bot.get_chat(uid)

    username = (
        f"@{user.username}"
        if user.username
        else "No Username"
    )

    full_name = user.first_name

    markup = types.InlineKeyboardMarkup()

    markup.row(
        types.InlineKeyboardButton(
            "✅ APPROVE",
            callback_data=f"approve_{uid}"
        ),
        types.InlineKeyboardButton(
            "❌ REJECT",
            callback_data=f"reject_{uid}"
        )
    )

    bot.send_message(
        ADMIN_ID,
        f"""
💰 <b>PAYMENT REQUEST</b>

👤 Name:
<b>{full_name}</b>

🆔 User ID:
<code>{uid}</code>

📛 Username:
<b>{username}</b>

💵 Amount:
<b>₦{data['amount']}</b>

💎 Credits:
<b>{data['credits']}</b>

🕒 Time:
<b>{data['time']}</b>
""",
        reply_markup=markup
    )

    bot.answer_callback_query(
        c.id,
        "Payment sent for review ✅"
    )

# =========================
# ADMIN ACTION
# =========================
@bot.callback_query_handler(
    func=lambda c:
    c.data.startswith("approve_")
    or c.data.startswith("reject_")
)
def admin_action(c):

    if c.from_user.id != ADMIN_ID:

        return bot.answer_callback_query(
            c.id,
            "Not allowed"
        )

    action, uid = c.data.split("_")

    pending = load("pending_payments.json")

    if uid not in pending:

        return bot.answer_callback_query(
            c.id,
            "Already processed"
        )

    data = pending[uid]

    if action == "approve":

        add_credit(uid, data["credits"])

        bot.send_message(
            uid,
            f"""
✅ <b>PAYMENT APPROVED</b>

🎉 {data['credits']} credits added successfully.
""",
            reply_markup=main_menu()
        )

        bot.send_message(
            ADMIN_ID,
            "✅ Payment approved"
        )

    else:

        bot.send_message(
            uid,
            "❌ Payment rejected.\nContact support.",
            reply_markup=main_menu()
        )

        bot.send_message(
            ADMIN_ID,
            "❌ Payment rejected"
        )

    del pending[uid]

    save("pending_payments.json", pending)

    bot.answer_callback_query(
        c.id,
        "Done"
    )

# =========================
# BROADCAST
# =========================
broadcast_mode = {}

@bot.message_handler(
    func=lambda m:
    m.text == "📢 Broadcast"
)
def broadcast(m):

    if m.from_user.id != ADMIN_ID:

        return bot.reply_to(
            m,
            "❌ Admin only"
        )

    broadcast_mode[m.chat.id] = True

    bot.reply_to(
        m,
        "📢 Send broadcast message now."
    )

@bot.message_handler(
    func=lambda m:
    broadcast_mode.get(m.chat.id) == True
)
def send_broadcast(m):

    if m.from_user.id != ADMIN_ID:
        return

    users = load("users.json")

    success = 0
    failed = 0

    bot.reply_to(
        m,
        "📡 Broadcasting message..."
    )

    for uid in users:

        try:

            bot.send_message(
                uid,
                f"""
📢 <b>ANNOUNCEMENT</b>

{m.text}
"""
            )

            success += 1

        except:
            failed += 1

    broadcast_mode[m.chat.id] = False

    bot.send_message(
        m.chat.id,
        f"""
✅ Broadcast Complete

✔ Success: {success}
❌ Failed: {failed}
"""
    )

# =========================
# IMAGE HANDLER
# =========================
@bot.message_handler(
    content_types=['photo', 'document']
)
def handle_image(m):

    try:

        save_user(m.from_user)

        if m.content_type == "photo":

            file_info = bot.get_file(
                m.photo[-1].file_id
            )

        else:

            if not m.document.mime_type.startswith("image/"):

                return bot.reply_to(
                    m,
                    "❌ Only image files allowed"
                )

            file_info = bot.get_file(
                m.document.file_id
            )

        uid = str(m.chat.id)

        # PAID USER
        if get_credit(uid) > 0:

            if not use_credit(uid):

                return bot.reply_to(
                    m,
                    "❌ No credits left"
                )

            threading.Thread(
                target=analyze_market,
                args=(m, file_info)
            ).start()

            return

        # FREE USER
        if can_use_free(uid):

            use_free(uid)

            threading.Thread(
                target=analyze_market,
                args=(m, file_info)
            ).start()

            return

        bot.reply_to(
            m,
            """
❌ Free trial exhausted.

💳 Please buy credits to continue.
""",
            reply_markup=main_menu()
        )

    except Exception as e:

        print("Image Handler Error:", e)

        bot.reply_to(
            m,
            limit_message()
        )

# =========================
# BALANCE
# =========================
@bot.message_handler(
    func=lambda m:
    m.text == "💰 My Balance"
)
def balance(m):

    bot.reply_to(
        m,
        f"""
💎 <b>Credits:</b>
{get_credit(m.chat.id)}

🎁 <b>Free Trial Left:</b>
{FREE_LIMIT - get_free_used(m.chat.id)}
""",
        reply_markup=main_menu()
    )

# =========================
# SUPPORT
# =========================
@bot.message_handler(
    func=lambda m:
    m.text == "📞 Support"
)
def support(m):

    bot.reply_to(
        m,
        """
📞 Support:
@Amudancefx
""",
        reply_markup=main_menu()
    )

# =========================
# ANALYZE BUTTON
# =========================
@bot.message_handler(
    func=lambda m:
    m.text == "📊 Analyze Market"
)
def ask_chart(m):

    bot.reply_to(
        m,
        """
📸 Send your chart screenshot for analysis.
""",
        reply_markup=main_menu()
    )

# =========================
# FLASK
# =========================
@app.route("/")
def home():
    return "BOT RUNNING"

# =========================
# RUN BOT
# =========================
if __name__ == "__main__":

    print("BOT STARTED")

    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60
)
