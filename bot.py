import telebot
from telebot import types
from flask import Flask, request
import os, json, requests, threading, time, random
from datetime import datetime, date
from dotenv import load_dotenv
from google import genai
from PIL import Image

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY")
ADMIN_ID = str(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# ================= FILES =================
USERS_FILE = "users.json"
VIP_FILE = "vip.json"
TX_FILE = "tx.json"

for f in [USERS_FILE, VIP_FILE, TX_FILE]:
    if not os.path.exists(f):
        json.dump({}, open(f, "w"))

# ================= SAFE LOAD =================
def load(f):
    try:
        return json.load(open(f))
    except:
        return {}

def save(f, d):
    tmp = f + ".tmp"
    json.dump(d, open(tmp, "w"), indent=4)
    os.replace(tmp, f)

# ================= USER =================
def get_user(uid):
    uid = str(uid)
    users = load(USERS_FILE)

    if uid not in users:
        users[uid] = {
            "free_used": None,
            "credits": 0
        }
        save(USERS_FILE, users)

    return users

# ================= VIP =================
def is_vip(uid):
    vip = load(VIP_FILE)
    uid = str(uid)

    if uid not in vip:
        return False

    if datetime.now().timestamp() > vip[uid]:
        del vip[uid]
        save(VIP_FILE, vip)
        return False

    return True

def add_vip(uid, days):
    vip = load(VIP_FILE)
    uid = str(uid)

    now = datetime.now().timestamp()
    current = vip.get(uid, 0)

    vip[uid] = current + days * 86400 if current > now else now + days * 86400
    save(VIP_FILE, vip)

# ================= CREDIT SYSTEM =================
def can_use(uid):
    uid = str(uid)
    users = load(USERS_FILE)
    users = get_user(uid)

    vip = is_vip(uid)

    if not vip:
        last = users[uid]["free_used"]

        if last:
            last_date = datetime.strptime(last, "%Y-%m-%d").date()
            if (date.today() - last_date).days < 7:
                save(USERS_FILE, users)
                return False, 0

        users[uid]["free_used"] = str(date.today())
        save(USERS_FILE, users)
        return True, 0

    users[uid]["credits"] += 2

    if users[uid]["credits"] <= 0:
        save(USERS_FILE, users)
        return False, 0

    users[uid]["credits"] -= 1
    save(USERS_FILE, users)

    return True, users[uid]["credits"]

# ================= START =================
@bot.message_handler(commands=['start'])
def start(m):

    uid = m.chat.id
    get_user(uid)

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton("📊 Analyze", callback_data="analyze"),
        types.InlineKeyboardButton("💎 VIP Plans", callback_data="vip")
    )

    kb.add(
        types.InlineKeyboardButton("💎 Benefits", callback_data="benefits"),
        types.InlineKeyboardButton("👤 My VIP", callback_data="myvip")
    )

    kb.add(
        types.InlineKeyboardButton("📞 Support", callback_data="support"),
        types.InlineKeyboardButton("🛠 Admin", callback_data="admin")
    )

    bot.send_message(uid, "🚀 FX ENGINE PRO DASHBOARD", reply_markup=kb)

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: True)
def menu(c):

    uid = str(c.message.chat.id)

    if c.data == "home":
        return start(c.message)

    # ===== ANALYZE BUTTON FIX =====
    if c.data == "analyze":
        allowed, credits = can_use(uid)

        if not allowed:
            return bot.answer_callback_query(c.id, "❌ NO CREDITS")

        bot.send_message(uid, "📤 SEND YOUR CHART IMAGE NOW")
        return

    # ===== VIP =====
    if c.data == "vip":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💎 VIP 5 DAYS - ₦2000", callback_data="pay_vip"))
        kb.add(types.InlineKeyboardButton("⚡ 1 SIGNAL - ₦500", callback_data="pay_signal"))
        kb.add(types.InlineKeyboardButton("⬅️ BACK", callback_data="home"))
        bot.edit_message_text("💎 VIP STORE", uid, c.message.message_id, reply_markup=kb)

    # ===== BENEFITS =====
    if c.data == "benefits":
        text = """
💎 VIP BENEFITS

🆓 FREE:
• 1 signal / 7 days

💎 VIP:
• 2 signals daily
• Smart Money Analysis
• Better accuracy
"""
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ BACK", callback_data="home"))
        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    # ===== MY VIP =====
    if c.data == "myvip":
        vip = load(VIP_FILE)
        users = load(USERS_FILE)

        credits = users.get(uid, {}).get("credits", 0)

        if uid not in vip:
            text = f"❌ NOT VIP\n🎟 Credits: {credits}"
        else:
            text = f"💎 VIP ACTIVE\n📅 {datetime.fromtimestamp(vip[uid])}\n🎟 Credits: {credits}"

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ BACK", callback_data="home"))

        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    # ===== SUPPORT =====
    if c.data == "support":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("ADMIN", url="https://t.me/Amudancefx"))
        kb.add(types.InlineKeyboardButton("⬅️ BACK", callback_data="home"))
        bot.edit_message_text("📞 SUPPORT", uid, c.message.message_id, reply_markup=kb)

    # ===== ADMIN PANEL =====
    if c.data == "admin":
        if uid != ADMIN_ID:
            return bot.answer_callback_query(c.id, "❌ NOT ADMIN")

        users = load(USERS_FILE)
        vip = load(VIP_FILE)

        text = f"""
🛠 ADMIN PANEL

👥 USERS: {len(users)}
💎 VIP: {len(vip)}
"""

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ BACK", callback_data="home"))
        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    # ===== PAYSTACK (SIMPLIFIED) =====
    if c.data in ["pay_vip", "pay_signal"]:
        bot.send_message(uid, "💳 PAYMENT SYSTEM NOT YET HOOKED TO LIVE KEY\nUse manual activation for now")

# ================= ANALYSIS ENGINE FIXED =================
@bot.message_handler(content_types=['photo'])
def analyze(m):

    uid = str(m.chat.id)

    msg = bot.reply_to(m, "📡 ANALYZING...")

    allowed, credits = can_use(uid)

    if not allowed:
        return bot.edit_message_text("❌ NO CREDITS", uid, msg.message_id)

    file = bot.get_file(m.photo[-1].file_id)
    data = bot.download_file(file.file_path)

    path = f"{uid}.jpg"
    open(path, "wb").write(data)

    image = Image.open(path)

    vip = is_vip(uid)
    confidence = random.randint(60, 97)

    prompt = f"FOREX ANALYSIS MODE: {'VIP' if vip else 'FREE'} CONFIDENCE: {confidence}%"

    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image]
        )
        text = res.text.upper()
    except:
        text = "⚠️ GEMINI ERROR - TRY AGAIN"

    bot.edit_message_text(
        f"{text}\n\n🎟 Credits Left: {credits}",
        uid,
        msg.message_id
    )

    os.remove(path)

# ================= RUN =================
def run():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(e)
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
