import os
import time
import requests
import psycopg2
import psycopg2.extras
import telebot
from threading import Thread
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# ⚙️ ASOSIY SOZLAMALAR
# ==========================================
TOKEN = "8804847521:AAGVqDdkmc0hHdrDVLgpGQ7WDDBsFrGWC5s"
ADMIN_ID = 6607270447
RENDER_URL = "https://open-budget-bot.onrender.com" 

# 🔥 PAROLINGIZ BILAN TAYYOR SUPABASE ULANISH HAVOLASI:
# (Parolingizdagi '?' belgisi ulanish xavfsizligi uchun '%3F' ga o'tkazildi)
SUPABASE_CONN_STRING = "postgresql://postgres:4-FFz2C5x%3Fs4MbL@db.fbbdoupcsabgrplmqdrk.supabase.co:5432/postgres?connect_timeout=10"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot va Masofaviy Baza faol ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    time.sleep(15)
    while True:
        try:
            requests.get(RENDER_URL)
            print("Keep-alive: Server muvaffaqiyatli 'ping' qilindi.")
        except Exception as e:
            print(f"Keep-alive xatolik: {e}")
        time.sleep(600)

# ==========================================
# 🗄 SUPABASE POSTGRESQL TIZIMI
# ==========================================
def get_db_connection():
    return psycopg2.connect(SUPABASE_CONN_STRING)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            balans INTEGER DEFAULT 0,
            referallar INTEGER DEFAULT 0,
            holat TEXT,
            karta TEXT,
            oxirgi_bonus REAL DEFAULT 0,
            inviter_id BIGINT,
            taklif_qilindi INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def get_user(user_id, username="Mavjud emas"):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT balans, referallar, holat, karta, oxirgi_bonus, inviter_id, taklif_qilindi FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute("INSERT INTO users (user_id, username, balans, referallar, oxirgi_bonus) VALUES (%s, %s, 0, 0, 0)", (user_id, username))
        conn.commit()
        row = [0, 0, None, None, 0, None, 0]
    
    cursor.close()
    conn.close()
    return {
        "balans": row[0],
        "referallar": row[1],
        "holat": row[2],
        "karta": row[3],
        "oxirgi_bonus": row[4],
        "inviter_id": row[5],
        "taklif_qilindi": bool(row[6])
    }

def update_user(user_id, data):
    conn = get_db_connection()
    cursor = conn.cursor()
    for key, value in data.items():
        if key == "taklif_qilindi":
            value = 1 if value else 0
        cursor.execute(f"UPDATE users SET {key} = %s WHERE user_id = %s", (value, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_total_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count

def get_all_user_ids():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return ids

# Bazani tekshirish va jadvallarni ochish
try:
    init_db()
    print("Muvaffaqiyatli: Supabase jadvallari yaratildi/tekshirildi.")
except Exception as database_error:
    print(f"Baza bilan bog'lanishda xatolik: {database_error}")

# ==========================================
# 📊 BOT SOZLAMALARI VA MENYULAR
# ==========================================
bot_settings = {
    "majburiy_kanal": None,  
    "majburiy_guruh": None,  
    "description": (
        "🤖 *Open Budget Botiga Xush Kelibsiz!*\n\n"
        "Ushbu bot orqali siz sport tashabbuslariga ovoz berib, pul ishlashingiz mumkin.\n\n"
        "🔥 *Imkoniyatlar:*\n"
        "— Har bir to'g'ri berilgan ovoz uchun: 45 000 so'm\n"
        "— Taklif qilingan har bir faol do'stingiz uchun: 1 000 so'm\n"
        "— Minimal pul yechish: 6 000 so'm\n\n"
        "👇 Boshlash uchun pastdagi tugmalardan foydalaning!"
    )
}

def asosiy_menyu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(KeyboardButton("🗳 Ovoz berish"))
    markup.row(KeyboardButton("💰 Balans"), KeyboardButton("📩 Pulni yechib olish"))
    markup.row(KeyboardButton("🔗 Referal ssilka"))
    markup.row(KeyboardButton("🎉 Aksiyalar"), KeyboardButton("💸 To'lovlar isboti"))
    return markup

def admin_panel_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📊 Foydalanuvchilar soni", callback_data="admin_stats"))
    markup.row(InlineKeyboardButton("📢 Reklama (Har qanday media)", callback_data="admin_send_reklama"))
    markup.row(InlineKeyboardButton("📢 Kanal Sozlamalari", callback_data="admin_manage_channel"))
    markup.row(InlineKeyboardButton("💬 Guruh Sozlamalari", callback_data="admin_manage_group"))
    markup.row(InlineKeyboardButton("📝 Tavsifni o'zgartirish", callback_data="admin_edit_desc"))
    return markup

def check_sub(user_id):
    if bot_settings["majburiy_kanal"]:
        try:
            status = bot.get_chat_member(bot_settings["majburiy_kanal"], user_id).status
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
            
    if bot_settings["majburiy_guruh"]:
        try:
            status = bot.get_chat_member(bot_settings["majburiy_guruh"], user_id).status
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ==========================================
# 🛡 AMALLAR VA COMMAND KODLARI
# ==========================================
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.reply_to_message)
def admin_reply_to_user(message):
    try:
        target_id = None
        text_lines = message.reply_to_message.text.split('\n')
        for line in text_lines:
            if "ID:" in line:
                target_id = int(line.split(":")[1].strip())
        
        if target_id:
            bot.send_message(target_id, f"💬 *Admin:* {message.text}", parse_mode="Markdown")
            bot.reply_to(message, "✅ Xabaringiz foydalanuvchiga yetkazildi.")
        else:
            bot.reply_to(message, "❌ Xabarda foydalanuvchi ID raqami topilmadi.")
    except Exception as e:
        bot.reply_to(message, f"❌ Xatolik: {str(e)}")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "🛠 *Mukammal Admin Panelga xush kelibsiz!*\nQuyidagi amallardan birini tanlang:", reply_markup=admin_panel_markup(), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ Bu buyruq faqat bot admini uchun!")

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    username = message.from_user.username or "Mavjud emas"
    user = get_user(user_id, username)
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id and user["inviter_id"] is None:
            update_user(user_id, {"inviter_id": referrer_id})
            user["inviter_id"] = referrer_id

    if not check_sub(user_id):
        markup = InlineKeyboardMarkup()
        if bot_settings["majburiy_kanal"]:
            k_link = bot_settings["majburiy_kanal"].replace("@", "")
            markup.add(InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=f"https://t.me/{k_link}"))
        if bot_settings["majburiy_guruh"]:
            g_link = bot_settings["majburiy_guruh"].replace("@", "")
            markup.add(InlineKeyboardButton("💬 Guruhga qo'shish", url=f"https://t.me/{g_link}"))
            
        markup.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub_again"))
        bot.send_message(user_id, "⚠️ Botdan foydalanish uchun homiy kanal va guruhimizga a'zo bo'lishingiz shart!", reply_markup=markup)
        return

    if user["inviter_id"] and not user["taklif_qilindi"]:
        ref_id = user["inviter_id"]
        ref_user = get_user(ref_id)
        update_user(ref_id, {"referallar": ref_user["referallar"] + 1, "balans": ref_user["balans"] + 1000})
        update_user(user_id, {"taklif_qilindi": True})
        try:
            bot.send_message(ref_id, "🎉 Do'stingiz botga qo'shildi! Balansingizga +1000 so'm qo'shildi.")
        except: pass

    bot.send_message(user_id, bot_settings["description"], reply_markup=asosiy_menyu(), parse_mode="Markdown")

def process_menu_logic(message):
    user_id = message.chat.id
    username = message.from_user.username or "Mavjud emas"
    user = get_user(user_id, username)
    text = message.text

    if text == "🗳 Ovoz berish":
        update_user(user_id, {"holat": "kutish_telefon"})
        bot.send_message(user_id, "📞 Ovoz berish uchun telefon raqamni kiriting:\n\nFormat: +998991234567 yoki 991234567")

    elif text == "💰 Balans":
        karta_matn = user["karta"] if user["karta"] else "Kiritilmagan"
        matn = f"💰 Hisobingiz: {user['balans']} so'm\n👥 Referallaringiz: {user['referallar']} ta\n💳 Karta: {karta_matn}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📩 Pulni yechib olish", callback_data="yechish_inline"))
        bot.send_message(user_id, matn, reply_markup=markup)

    elif text == "📩 Pulni yechib olish":
        if user["balans"] < 6000:
            bot.send_message(user_id, f"❌ Pul yechish uchun minimal summa 6 000 so'm!\nSizda: {user['balans']} so'm bor.")
        else:
            update_user(user_id, {"holat": "kutish_karta"})
            bot.send_message(user_id, "💳 Pulni yechish uchun plastik karta raqamingizni yoki telefon raqamingizni kiriting:")

    elif text == "🔗 Referal ssilka":
        bot_info = bot.get_me()
        referal_link = f"https://t.me/{bot_info.username}?start={user_id}"
        matn = f"🤝 *Referral tizimi*\n\nDo'stlarni taklif qilib *1 000 so'm* oling.\n\n🔗 Havolangiz:\n`{referal_link}`"
        share_text = f"🔥 Open Budget botida ovoz berib pul ishlang! Kirish uchun bosing: {referal_link}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Do'stlarga ulashish", switch_inline_query=share_text))
        bot.send_message(user_id, matn, reply_markup=markup, parse_mode="Markdown")

    elif text == "🎉 Aksiyalar":
        joriy_vaqt = time.time()
        farq = joriy_vaqt - user["oxirgi_bonus"]
        if farq >= 86400:
            update_user(user_id, {"balans": user["balans"] + 500, "oxirgi_bonus": joriy_vaqt})
            bot.send_message(user_id, "🎁 *Kunlik bonus 500 so'm qo'shildi!*", parse_mode="Markdown")
        else:
            qolgan = int(86400 - farq)
            bot.send_message(user_id, f"❌ Siz bugun bonus olgansiz! Yana {qolgan//3600} soatdan keyin urinib ko'ring.")

    elif text == "💸 To'lovlar isboti":
        bot.send_message(user_id, "✅ To'lovlar isboti kanali:\n👉 https://t.me/openbudgetisbot")

    elif user["holat"] == "kutish_telefon":
        admin_matn = f"📱 Yangi raqam!\nFoydalanuvchi: @{username}\nID: {user_id}\nRaqam: {text}"
        bot.send_message(ADMIN_ID, admin_matn)
        update_user(user_id, {"holat": "kutish_sms"})
        bot.send_message(user_id, "📩 Telefon raqamingizga SMS kod yuborildi. Uni botga yuboring:")

    elif user["holat"] == "kutish_sms":
        admin_matn = f"🔑 SMS Kod keldi!\nFoydalanuvchi: @{username}\nID: {user_id}\nKod: {text}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ 45 000 so'm qo'shish", callback_data=f"add_45000_{user_id}"))
        markup.add(InlineKeyboardButton("❌ Kod noto'g'ri", callback_data=f"wrong_code_{user_id}"))
        bot.send_message(ADMIN_ID, admin_matn, reply_markup=markup)
        update_user(user_id, {"holat": None})
        bot.send_message(user_id, "⏳ Rahmat! Kod ko'rib chiqilmoqda.")

    elif user["holat"] == "kutish_karta":
        current_balance = user['balans']
        update_user(user_id, {"karta": text, "holat": None, "balans": 0})
        admin_matn = f"💰 Pul yechish!\nFoydalanuvchi: @{username}\nID: {user_id}\nSumma: {current_balance} so'm\nKarta: {text}"
        bot.send_message(ADMIN_ID, admin_matn)
        bot.send_message(user_id, "✅ So'rov adminga yuborildi.")

# ==========================================
# 📭 REKLAMA VA MULTIMEDIA INTEGRATSIYASI
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'audio', 'video', 'voice', 'document', 'sticker'])
def handle_all_messages(message):
    user_id = message.chat.id
    username = message.from_user.username or "Mavjud emas"
    user = get_user(user_id, username)
    
    if user_id == ADMIN_ID and user.get("holat") == "kutish_reklama":
        update_user(ADMIN_ID, {"holat": None})
        bot.send_message(ADMIN_ID, "📢 Reklama yuborilmoqda...")
        success, failed = 0, 0
        for uid in get_all_user_ids():
            try:
                bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=message.message_id)
                success += 1
                time.sleep(0.05)
            except:
                failed += 1
        bot.send_message(ADMIN_ID, f"📢 Tugadi.\n✅ Yetkazildi: {success}\n❌ Bloklangan: {failed}")
        return

    if user_id == ADMIN_ID and user.get("holat") == "kutish_kanal":
        update_user(ADMIN_ID, {"holat": None})
        if message.text == "0":
            bot_settings["majburiy_kanal"] = None
            bot.send_message(ADMIN_ID, "✅ Kanal o'chirildi!")
        else:
            bot_settings["majburiy_kanal"] = message.text if message.text.startswith("@") else f"@{message.text}"
            bot.send_message(ADMIN_ID, f"✅ Kanal saqlandi: {bot_settings['majburiy_kanal']}")
        return

    if user_id == ADMIN_ID and user.get("holat") == "kutish_guruh":
        update_user(ADMIN_ID, {"holat": None})
        if message.text == "0":
            bot_settings["majburiy_guruh"] = None
            bot.send_message(ADMIN_ID, "✅ Guruh o'chirildi!")
        else:
            bot_settings["majburiy_guruh"] = message.text if message.text.startswith("@") else f"@{message.text}"
            bot.send_message(ADMIN_ID, f"✅ Guruh saqlandi: {bot_settings['majburiy_guruh']}")
        return

    if user_id == ADMIN_ID and user.get("holat") == "kutish_desc":
        update_user(ADMIN_ID, {"holat": None})
        bot_settings["description"] = message.text
        bot.send_message(ADMIN_ID, "✅ Bot tavsifi o'zgardi!")
        return

    if message.content_type == 'text':
        if not check_sub(user_id):
            start_command(message)
            return
            
        if user_id != ADMIN_ID and user["holat"] is None and message.text not in ["🗳 Ovoz berish", "💰 Balans", "📩 Pulni yechib olish", "🔗 Referal ssilka", "🎉 Aksiyalar", "💸 To'lovlar isboti"]:
            bot.send_message(ADMIN_ID, f"👤 Foydalanuvchidan xabar:\nID: {user_id}\nUsername: @{username}\n\nXabar: {message.text}")
            bot.send_message(user_id, "✉️ Xabaringiz adminga yuborildi.")
            return

        process_menu_logic(message)

# ==========================================
# ⚙️ CALLBACK OPERATORLARI
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.message.chat.id
    user = get_user(user_id)
    bot_info = bot.get_me()
    
    if call.data == "check_sub_again":
        bot.answer_callback_query(call.id)
        if check_sub(user_id):
            bot.delete_message(user_id, call.message.message_id)
            if user["inviter_id"] and not user["taklif_qilindi"]:
                ref_id = user["inviter_id"]
                ref_user = get_user(ref_id)
                update_user(ref_id, {"referallar": ref_user["referallar"] + 1, "balans": ref_user["balans"] + 1000})
                update_user(user_id, {"taklif_qilindi": True})
                try:
                    bot.send_message(ref_id, "🎉 Do'stingiz kanallarga a'zo bo'ldi! +1000 so'm qo'shildi.")
                except: pass
            bot.send_message(user_id, bot_settings["description"], reply_markup=asosiy_menyu(), parse_mode="Markdown")
        else:
            bot.send_message(user_id, "❌ Siz hali barcha homiy kanallarga a'zo bo'lmadingiz.")

    elif call.data == "yechish_inline":
        bot.answer_callback_query(call.id)
        call.message.text = "📩 Pulni yechib olish"
        process_menu_logic(call.message)
        
    elif call.data == "admin_stats":
        bot.answer_callback_query(call.id)
        bot.send_message(ADMIN_ID, f"📊 Jami foydalanuvchilar: {get_total_users()} ta")
