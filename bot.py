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
ADMIN_ID = os.getenv("ADMIN_ID")

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
FILES = {
    "vip": "vip_data.json",
    "users": "users.json",
    "tx": "transactions.json",
    "ban": "banned.json",
    "usage": "usage.json"
}

for f in FILES.values():
    if not os.path.exists(f):
        with open(f, "w") as x:
            json.dump({}, x)

# =========================
# SAFE JSON
# =========================
def load(f):
    try:
        with open(f, "r") as x:
            return json.load(x)
    except:
        return {}

def save(f, d):
    tmp = f + ".tmp"
    with open(tmp, "w") as x:
        json.dump(d, x, indent=4)
    os.replace(tmp, f)

# =========================
# ADMIN PANEL
# =========================
def is_admin(uid):
    return str(uid) == str(ADMIN_ID)

@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.chat.id):
        return

    users = load(FILES["users"])
    vip = load(FILES["vip"])

    bot.send_message(
        m.chat.id,
        f"""
🛠 ADMIN PANEL

👥 USERS: {len(users)}
💎 VIP USERS: {len(vip)}

Commands:
- /ban id
- /unban id
"""
    )

@bot.message_handler(commands=["ban"])
def ban(m):
    if not is_admin(m.chat.id):
        return

    try:
        uid = m.text.split()[1]
        data = load(FILES["ban"])
        data[uid] = True
        save(FILES["ban"], data)
        bot.send_message(m.chat.id, "BANNED")
    except:
        pass

@bot.message_handler(commands=["unban"])
def unban(m):
    if not is_admin(m.chat.id):
        return

    try:
        uid = m.text.split()[1]
        data = load(FILES["ban"])
        data.pop(uid, None)
        save(FILES["ban"], data)
        bot.send_message(m.chat.id, "UNBANNED")
    except:
        pass

# =========================
# VIP
# =========================
def add_vip(uid, days):
    vip = load(FILES["vip"])
    uid = str(uid)

    now = datetime.now().timestamp()
    current = vip.get(uid, 0)

    vip[uid] = current + days * 86400 if current > now else now + days * 86400
    save(FILES["vip"], vip)

def is_vip(uid):
    vip = load(FILES["vip"])
    uid = str(uid)

    if uid not in vip:
        return False

    if datetime.now().timestamp() > vip[uid]:
        del vip[uid]
        save(FILES["vip"], vip)
        return False

    return True

# =========================
# CREDIT SYSTEM FIXED
# =========================
def can_use(uid):
    uid = str(uid)
    usage = load(FILES["usage"])

    if uid not in usage:
        usage[uid] = {
            "last": None,
            "vip_credits": 0,
            "vip_last": str(date.today())
        }

    today = str(date.today())
    vip = is_vip(uid)

    if not vip:
        last = usage[uid]["last"]

        if last:
            last_date = datetime.strptime(last, "%Y-%m-%d").date()
            if (date.today() - last_date).days < 7:
                save(FILES["usage"], usage)
                return False, 0

        usage[uid]["last"] = today
        save(FILES["usage"], usage)
        return True, 0

    last_reset = datetime.strptime(
        usage[uid]["vip_last"], "%Y-%m-%d"
    ).date()

    days = (date.today() - last_reset).days

    if days >= 1:
        usage[uid]["vip_credits"] += days * 2
        usage[uid]["vip_last"] = today

    if usage[uid]["vip_credits"] <= 0:
        return False, 0

    usage[uid]["vip_credits"] -= 1
    save(FILES["usage"], usage)

    return True, usage[uid]["vip_credits"]

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(m):

    if str(m.chat.id) in load(FILES["ban"]):
        return bot.send_message(m.chat.id, "⛔ BANNED")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Analyze Chart", "💎 VIP Plans")
    kb.add("💎 VIP Benefits", "👤 My VIP")
    kb.add("📞 Support")

    bot.send_message(m.chat.id, "🚀 FX ENGINE", reply_markup=kb)

# =========================
# MENU
# =========================
@bot.message_handler(content_types=['text'])
def menu(m):

    if str(m.chat.id) in load(FILES["ban"]):
        return

    if m.text == "💎 VIP Benefits":
        bot.send_message(m.chat.id,
        "💎 VIP:\n2 signals daily\nBetter accuracy\n\n🆓 FREE:\n1 per 7 days")
        return

    if m.text == "👤 My VIP":
        vip = load(FILES["vip"])
        usage = load(FILES["usage"])
        uid = str(m.chat.id)

        credits = usage.get(uid, {}).get("vip_credits", 0)

        if uid not in vip:
            bot.send_message(m.chat.id, f"❌ NOT VIP\n🎟 {credits}")
        else:
            bot.send_message(m.chat.id,
            f"💎 VIP ACTIVE\n📅 {datetime.fromtimestamp(vip[uid])}\n🎟 {credits}")

# =========================
# ANALYSIS (SAFE + NO CRASH)
# =========================
@bot.message_handler(content_types=['photo'])
def analyze(m):

    msg = bot.reply_to(m, "📡 ANALYZING...")

    try:
        file = bot.get_file(m.photo[-1].file_id)
        data = bot.download_file(file.file_path)

        path = f"{m.chat.id}.jpg"
        open(path, "wb").write(data)

        image = Image.open(path)

        vip = is_vip(m.chat.id)

        prompt = f"""
FOREX ANALYSIS MODE: {"VIP" if vip else "FREE"}
"""

        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, image]
            )
            text = res.text.upper()

        except Exception:
            text = "⚠️ AI LIMIT REACHED — TRY AGAIN LATER"

        _, credits = can_use(m.chat.id)

        bot.edit_message_text(
            f"{text}\n\n🎟 Credits: {credits}",
            m.chat.id,
            msg.message_id
        )

        os.remove(path)

    except:
        bot.edit_message_text("❌ ERROR", m.chat.id, msg.message_id)

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
    threading.Thread(target=run, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
