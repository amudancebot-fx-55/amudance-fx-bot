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
# DATA FOLDER
# =========================
DATA_FOLDER = "data"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

FILES = [
    f"{DATA_FOLDER}/users.json",
    f"{DATA_FOLDER}/credits.json",
    f"{DATA_FOLDER}/free_trial.json",
    f"{DATA_FOLDER}/pending_payments.json"
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
# VIP USERS
# =========================
VIP_USERS = [
    ADMIN_ID
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
# LIMIT MESSAGE
# =========================
def limit_message():

    return """
⚠️ Bot is currently in cool mode.

Please try again in a few minutes or hr.

📞 Support:
@Amudancefx
"""

# =========================
# CREDIT SYSTEM
# =========================
def get_credit(uid):

    return load(
        f"{DATA_FOLDER}/credits.json"
    ).get(str(uid), 0)

def add_credit(uid, amt):

    d = load(f"{DATA_FOLDER}/credits.json")

    d[str(uid)] = d.get(str(uid), 0) + amt

    save(f"{DATA_FOLDER}/credits.json", d)

def use_credit(uid):

    d = load(f"{DATA_FOLDER}/credits.json")

    uid = str(uid)

    if d.get(uid, 0) > 0:

        d[uid] -= 1

        save(f"{DATA_FOLDER}/credits.json", d)

        return True

    return False

# =========================
# FREE TRIAL SYSTEM
# =========================
FREE_LIMIT = 2

def get_free_used(uid):

    data = load(
        f"{DATA_FOLDER}/free_trial.json"
    )

    return data.get(str(uid), 0)

def can_use_free(uid):

    used = get_free_used(uid)

    return used < FREE_LIMIT

def use_free(uid):

    data = load(
        f"{DATA_FOLDER}/free_trial.json"
    )

    uid = str(uid)

    data[uid] = data.get(uid, 0) + 1

    save(
        f"{DATA_FOLDER}/free_trial.json",
        data
    )

# =========================
# COOLDOWN SYSTEM
# =========================
last_used = {}

def cooldown(uid):

    now = time.time()

    if uid in last_used:

        if now - last_used[uid] < 15:
            return False

    last_used[uid] = now

    return True

# =========================
# SAFE LONG MESSAGE
# =========================
def send_long_message(chat_id, text):

    MAX_LENGTH = 4000

    for i in range(0, len(text), MAX_LENGTH):

        chunk = text[i:i + MAX_LENGTH]

        bot.send_message(chat_id, chunk)

# =========================
# GEMINI CALL
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

        # DOWNLOAD IMAGE
        file = bot.download_file(file_info.file_path)

        path = f"chart_{message.chat.id}.jpg"

        with open(path, "wb") as f:
            f.write(file)

        # LOADING
        loading = bot.send_message(
            message.chat.id,
            "📡 Upload received..."
        )

        steps = [
            "🧠 AI analyzing chart...",
            "📊 Processing structure...",
            "💹 Detecting liquidity...",
            "🏦 Tracking institutions...",
            "📈 Generating sniper setup...",
            "✅ Finalizing analysis..."
        ]

        for step in steps:

            time.sleep(1)

            try:
                bot.edit_message_text(
                    step,
                    message.chat.id,
                    loading.message_id
                )

            except:
                pass

        # READ IMAGE
        with open(path, "rb") as f:

            image_bytes = f.read()

        image_base64 = base64.b64encode(
            image_bytes
        ).decode()

        # PROMPT
        prompt = """
You are a world-class institutional forex trader.

Analyze this chart using:
- Smart Money Concepts
- ICT concepts
- Liquidity analysis
- BOS and CHoCH
- Order blocks
- Fair value gaps
- Premium and discount zones

Provide:
1. Trend direction
2. Market structure
3. Liquidity zones
4. Institutional bias
5. Best entry
6. Stop loss
7. Take profit targets
8. Risk level
9. Confidence level
10. Final recommendation

Rules:
- Be highly accurate
- Give sniper entries
- Use professional formatting
- Keep response clean
- Avoid vague explanations
"""

        # AI RESULT
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
━━━━━━━━━━━━━━━━━━
🚀 AMUDANCE FX AI
━━━━━━━━━━━━━━━━━━

{result}

━━━━━━━━━━━━━━━━━━
⚠️ Trade responsibly
"""

        send_long_message(
            message.chat.id,
            final_text
        )

        # DELETE FILE
        try:
            os.remove(path)

        except:
            pass

    except Exception as e:

        print("Analysis Error:", e)

        bot.send_message(
            message.chat.id,
            limit_message()
        )

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    # SAVE USER
    users = load(f"{DATA_FOLDER}/users.json")

    users[str(m.chat.id)] = {
        "name": m.from_user.first_name
    }

    save(
        f"{DATA_FOLDER}/users.json",
        users
    )

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "📊 Analyze Market",
            callback_data="analyze"
        ),

        types.InlineKeyboardButton(
            "💳 Buy Credits",
            callback_data="buy_menu"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💰 My Balance",
            callback_data="balance"
        ),

        types.InlineKeyboardButton(
            "📞 Support",
            url="https://t.me/Amudancefx"
        )
    )

    text = f"""
🚀 AMUDANCE FX AI

🤖 Powered ALL FX Strategy 

━━━━━━━━━━━━━━━━━━

🎁 Free Trial:
{FREE_LIMIT - get_free_used(m.chat.id)}

💎 Credits:
{get_credit(m.chat.id)}

━━━━━━━━━━━━━━━━━━

Choose an option below 👇
"""

    bot.send_message(
        m.chat.id,
        text,
        reply_markup=markup
    )

# =========================
# CALLBACK HANDLER
# =========================
@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):

    uid = str(c.message.chat.id)

    # ANALYZE
    if c.data == "analyze":

        bot.answer_callback_query(c.id)

        bot.send_message(
            uid,
            "📸 Send your chart screenshot for analysis."
        )

    # BALANCE
    elif c.data == "balance":

        bot.answer_callback_query(c.id)

        bot.send_message(
            uid,
            f"""
💎 Credits:
{get_credit(uid)}

🎁 Free Left:
{FREE_LIMIT - get_free_used(uid)}
"""
        )

    # BUY MENU
    elif c.data == "buy_menu":

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
            uid,
            "💎 Choose your credit plan:",
            reply_markup=markup
        )

    # BUY
    elif c.data.startswith("buy_"):

        _, amount, credits = c.data.split("_")

        pending = load(
            f"{DATA_FOLDER}/pending_payments.json"
        )

        pending[uid] = {
            "amount": int(amount),
            "credits": int(credits),
            "time": str(datetime.now())
        }

        save(
            f"{DATA_FOLDER}/pending_payments.json",
            pending
        )

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
🏦 PAYMENT DETAILS

Bank:
{BANK_NAME}

Account Number:
{ACCOUNT_NUMBER}

Account Name:
{ACCOUNT_NAME}

💰 Amount:
₦{amount}

💎 Credits:
{credits}

⚠️ After payment click the button below.
""",
            reply_markup=markup
        )

    # USER PAID
    elif c.data.startswith("paid_"):

        user_id = c.data.split("_")[1]

        pending = load(
            f"{DATA_FOLDER}/pending_payments.json"
        )

        if user_id not in pending:

            return bot.answer_callback_query(
                c.id,
                "No pending payment found"
            )

        data = pending[user_id]

        markup = types.InlineKeyboardMarkup()

        markup.row(
            types.InlineKeyboardButton(
                "✅ APPROVE",
                callback_data=f"approve_{user_id}"
            ),

            types.InlineKeyboardButton(
                "❌ REJECT",
                callback_data=f"reject_{user_id}"
            )
        )

        bot.send_message(
            ADMIN_ID,
            f"""
💰 PAYMENT REQUEST

👤 User:
{user_id}

💵 Amount:
₦{data['amount']}

💎 Credits:
{data['credits']}

🕒 Time:
{data['time']}
""",
            reply_markup=markup
        )

        bot.answer_callback_query(
            c.id,
            "Payment sent for review ✅"
        )

    # ADMIN APPROVE
    elif c.data.startswith("approve_"):

        if c.from_user.id != ADMIN_ID:

            return bot.answer_callback_query(
                c.id,
                "Not allowed"
            )

        user_id = c.data.split("_")[1]

        pending = load(
            f"{DATA_FOLDER}/pending_payments.json"
        )

        if user_id not in pending:

            return

        data = pending[user_id]

        add_credit(
            user_id,
            data["credits"]
        )

        bot.send_message(
            user_id,
            f"""
✅ PAYMENT APPROVED

🎉 {data['credits']} credits added successfully.
"""
        )

        del pending[user_id]

        save(
            f"{DATA_FOLDER}/pending_payments.json",
            pending
        )

        bot.answer_callback_query(
            c.id,
            "Approved"
        )

    # ADMIN REJECT
    elif c.data.startswith("reject_"):

        if c.from_user.id != ADMIN_ID:

            return bot.answer_callback_query(
                c.id,
                "Not allowed"
            )

        user_id = c.data.split("_")[1]

        pending = load(
            f"{DATA_FOLDER}/pending_payments.json"
        )

        if user_id not in pending:

            return

        bot.send_message(
            user_id,
            "❌ Payment rejected."
        )

        del pending[user_id]

        save(
            f"{DATA_FOLDER}/pending_payments.json",
            pending
        )

        bot.answer_callback_query(
            c.id,
            "Rejected"
        )

# =========================
# IMAGE HANDLER
# =========================
@bot.message_handler(
    content_types=['photo', 'document']
)
def handle_image(m):

    try:

        uid = str(m.chat.id)

        # COOLDOWN
        if not cooldown(uid):

            return bot.reply_to(
                m,
                "⏳ Wait 15 seconds before next analysis."
            )

        # PHOTO
        if m.content_type == "photo":

            file_info = bot.get_file(
                m.photo[-1].file_id
            )

        # DOCUMENT
        else:

            if not m.document.mime_type.startswith("image/"):

                return bot.reply_to(
                    m,
                    "❌ Only image files allowed."
                )

            file_info = bot.get_file(
                m.document.file_id
            )

        # VIP USER
        if int(uid) in VIP_USERS:

            analyze_market(
                m,
                file_info
            )

            return

        # PAID USER
        if get_credit(uid) > 0:

            if not use_credit(uid):

                return bot.reply_to(
                    m,
                    "❌ No credits left."
                )

            analyze_market(
                m,
                file_info
            )

            return

        # FREE USER
        if can_use_free(uid):

            use_free(uid)

            analyze_market(
                m,
                file_info
            )

            return

        # NO ACCESS
        bot.reply_to(
            m,
            """
❌ Free trial ended forever.

💳 Buy credits to continue.
"""
        )

    except Exception as e:

        print("Image Error:", e)

        bot.reply_to(
            m,
            limit_message()
        )

# =========================
# BROADCAST
# =========================
@bot.message_handler(commands=['broadcast'])
def broadcast(m):

    if m.chat.id != ADMIN_ID:
        return

    text = m.text.replace(
        "/broadcast ",
        ""
    )

    users = load(
        f"{DATA_FOLDER}/users.json"
    )

    count = 0

    for uid in users:

        try:

            bot.send_message(uid, text)

            count += 1

        except:
            pass

    bot.reply_to(
        m,
        f"✅ Sent to {count} users"
    )

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

    print("BOT STARTED")

    bot.infinity_polling(
        skip_pending=True
            )
