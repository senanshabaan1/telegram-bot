import logging
import sqlite3
from telegram import Update, ForceReply, Bot, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# التوكن و ID الأدمن
TOKEN = '7659349563:AAFkQofuiz07HfrNSQRtMFqqv2HNHIXLrqk'
ADMIN_ID = 394895560

# إعداد اللوج
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قاعدة البيانات
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    user_type TEXT,
    coins INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0,
    voice_note TEXT
)
''')
conn.commit()

# مراحل التسجيل
REGISTER_GENDER, REGISTER_VOICE = range(2)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("أهلاً بك! للتسجيل استخدم /register")

def register(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("هل أنت 'male' أم 'female'؟")
    return REGISTER_GENDER

def register_gender(update: Update, context: CallbackContext) -> int:
    gender = update.message.text.lower()
    if gender not in ['male', 'female']:
        update.message.reply_text("الرجاء كتابة 'male' أو 'female'")
        return REGISTER_GENDER

    user = update.effective_user
    cursor.execute("INSERT OR REPLACE INTO users (user_id, username, user_type) VALUES (?, ?, ?)",
                   (user.id, user.username, gender))
    conn.commit()
    update.message.reply_text("الآن أرسل رسالة صوتية قصيرة.")
    return REGISTER_VOICE

def register_voice(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    voice = update.message.voice
    if not voice:
        update.message.reply_text("أرسل رسالة صوتية فقط.")
        return REGISTER_VOICE

    cursor.execute("UPDATE users SET voice_note = ?, verified = 0 WHERE user_id = ?",
                   (voice.file_id, user.id))
    conn.commit()

    # إرسال إشعار للأدمن
    context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"👤 مستخدم جديد سجّل:\n"
             f"ID: {user.id}\n"
             f"Username: @{user.username}\n"
             f"Type: {cursor.execute('SELECT user_type FROM users WHERE user_id=?', (user.id,)).fetchone()[0]}",
        parse_mode=ParseMode.HTML
    )
    context.bot.send_voice(chat_id=ADMIN_ID, voice=voice.file_id, caption=f"للموافقة: /approve {user.id}")

    update.message.reply_text("تم التسجيل بنجاح! سيتم مراجعته من قبل الإدارة.")
    return ConversationHandler.END

def approve(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ غير مصرح لك باستخدام هذا الأمر.")
        return

    if len(context.args) != 1:
        update.message.reply_text("استخدم الأمر هكذا: /approve USER_ID")
        return

    user_id = int(context.args[0])
    cursor.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

    context.bot.send_message(chat_id=user_id, text="✅ تم تفعيل حسابك من قبل الإدارة!")
    update.message.reply_text("✅ تم التفعيل.")

def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        update.message.reply_text(f"💰 رصيدك: {row[0]} كوينز")
    else:
        update.message.reply_text("❌ لم يتم العثور على حسابك. استخدم /register للتسجيل.")

def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            REGISTER_GENDER: [MessageHandler(Filters.text & ~Filters.command, register_gender)],
            REGISTER_VOICE: [MessageHandler(Filters.voice, register_voice)],
        },
        fallbacks=[],
    )

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("رصيدي", balance))
    dispatcher.add_handler(CommandHandler("approve", approve))
    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
