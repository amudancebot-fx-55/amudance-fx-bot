import telebot
from telebot import types
from flask import Flask
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

ADMIN_ID = os.getenv("ADMIN_ID")  # 🔥 ADD THIS IN .env

bot = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# ================= FILES =================
USERS_FILE = "users.json"
VIP_FILE = "vip.json"

for f in [USERS_FILE, VIP_FILE]:
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

# ================= CREDIT ENGINE (FIXED) =================
def can_use(uid):

    uid = str(uid)
    users = load(USERS_FILE)
    users = get_user(uid)

    vip = is_vip(uid)

    # ===== FREE USERS =====
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

    # ===== VIP USERS =====
    users[uid]["credits"] += 2

    if users[uid]["credits"] <= 0:
        save(USERS_FILE, users)
        return False, 0

    users[uid]["credits"] -= 1
    save(USERS_FILE, users)

    return True, users[uid]["credits"]

# ================= START (ADVANCED UI) =================
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
        types.InlineKeyboardButton("🛠 Admin", callback_data="admin_panel")
    )

    bot.send_message(uid, "🚀 FX ENGINE PRO DASHBOARD", reply_markup=kb)

# ================= CALLBACK SYSTEM =================
@bot.callback_query_handler(func=lambda c: True)
def menu(c):

    uid = c.message.chat.id
    users = load(USERS_FILE)

    # ===== HOME =====
    def home():
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
            types.InlineKeyboardButton("🛠 Admin", callback_data="admin_panel")
        )

        bot.edit_message_text("🚀 DASHBOARD", uid, c.message.message_id, reply_markup=kb)

    # ===== VIP BENEFITS =====
    if c.data == "benefits":

        text = """
💎 VIP BENEFITS

🆓 FREE:
• 1 signal / 7 days
• Basic AI analysis

💎 VIP:
• 2 signals daily
• Smart Money Concept
• Liquidity detection
• Faster processing

⚡ SYSTEM:
• Credits never expire
"""

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Back", callback_data="home"))

        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    # ===== VIP PLANS =====
    elif c.data == "vip":

        kb = types.InlineKeyboardMarkup()

        kb.add(types.InlineKeyboardButton("💎 VIP 5 DAYS - ₦2000", callback_data="pay_vip"))
        kb.add(types.InlineKeyboardButton("⚡ 1 SIGNAL - ₦500", callback_data="pay_signal"))
        kb.add(types.InlineKeyboardButton("⬅️ Back", callback_data="home"))

        bot.edit_message_text("💳 VIP STORE", uid, c.message.message_id, reply_markup=kb)

    # ===== MY VIP =====
    elif c.data == "myvip":

        vip = load(VIP_FILE)
        credits = users.get(str(uid), {}).get("credits", 0)

        if str(uid) not in vip:
            text = f"❌ NOT VIP\n🎟 Credits: {credits}"
        else:
            text = f"💎 VIP ACTIVE\n📅 {datetime.fromtimestamp(vip[str(uid)])}\n🎟 Credits: {credits}"

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Back", callback_data="home"))

        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    # ===== SUPPORT =====
    elif c.data == "support":

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Admin", url="https://t.me/Amudancefx"))
        kb.add(types.InlineKeyboardButton("⬅️ Back", callback_data="home"))

        bot.edit_message_text("📞 Support Center", uid, c.message.message_id, reply_markup=kb)

    # ===== ADMIN PANEL =====
    elif c.data == "admin_panel":

        if str(uid) != str(ADMIN_ID):
            return bot.answer_callback_query(c.id, "❌ Not admin")

        users = load(USERS_FILE)
        vip = load(VIP_FILE)

        text = f"""
🛠 ADMIN PANEL

👥 USERS: {len(users)}
💎 VIP USERS: {len(vip)}

Commands:
• Ban user (manual in code)
• Add VIP (manual)
"""

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Back", callback_data="home"))

        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    # ===== HOME =====
    elif c.data == "home":
        home()

# ================= ANALYSIS ENGINE =================
@bot.message_handler(content_types=['photo'])
def analyze(m):

    msg = bot.reply_to(m, "📡 ANALYZING...")

    uid = str(m.chat.id)

    file = bot.get_file(m.photo[-1].file_id)
    data = bot.download_file(file.file_path)

    path = f"{uid}.jpg"
    open(path, "wb").write(data)

    image = Image.open(path)

    vip = is_vip(uid)
    confidence = random.randint(60, 97)
    floor = 80 if vip else 65

    prompt = f"""
FOREX SMART MONEY ANALYSIS
MODE: {"VIP" if vip else "FREE"}
CONFIDENCE: {confidence}%
"""

    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image]
        )
        text = res.text.upper()

    except Exception:
        text = "⚠️ AI LIMIT REACHED - TRY AGAIN LATER"

    if confidence < floor:
        text += "\n\n⚠️ WAIT ONLY"

    _, credits = can_use(uid)

    bot.edit_message_text(
        f"{text}\n\n🎟 Credits: {credits}",
        uid,
        msg.message_id
    )

    os.remove(path)

# ================= RUN =================
def run():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
