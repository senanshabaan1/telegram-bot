
import logging
import sqlite3
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# إعداد اللوج
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# قاعدة بيانات SQLite
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

# إنشاء جدول المستخدمين
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    user_type TEXT,  -- 'male' or 'female'
    coins INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0,
    voice_note TEXT
)
''')
conn.commit()

# حالات التسجيل
REGISTER_GENDER, REGISTER_VOICE = range(2)

def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_text(
        f"أهلاً {user.first_name}! لتسجيل الدخول، استخدم /register"
    )

def register(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "هل أنت ولد أم بنت؟ أكتب 'male' أو 'female'"
    )
    return REGISTER_GENDER

def register_gender(update: Update, context: CallbackContext) -> int:
    gender = update.message.text.lower()
    if gender not in ['male', 'female']:
        update.message.reply_text("من فضلك اكتب 'male' أو 'female'")
        return REGISTER_GENDER

    user_id = update.effective_user.id
    username = update.effective_user.username

    cursor.execute("INSERT OR REPLACE INTO users (user_id, username, user_type) VALUES (?, ?, ?)",
                   (user_id, username, gender))
    conn.commit()

    update.message.reply_text(
        "الآن، أرسل رسالة صوتية قصيرة لتأكيد التسجيل."
    )
    return REGISTER_VOICE

def register_voice(update: Update, context: CallbackContext) -> int:
    voice = update.message.voice
    if not voice:
        update.message.reply_text("الرجاء إرسال رسالة صوتية فقط.")
        return REGISTER_VOICE

    user_id = update.effective_user.id
    file_id = voice.file_id

    cursor.execute("UPDATE users SET voice_note = ?, verified = 1 WHERE user_id = ?",
                   (file_id, user_id))
    conn.commit()

    update.message.reply_text("تم التسجيل بنجاح! في انتظار الموافقة من الإدارة.")

    return ConversationHandler.END

def balance(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        update.message.reply_text(f"رصيدك الحالي: {row[0]} كوينز")
    else:
        update.message.reply_text("أنت غير مسجل، استخدم /register للتسجيل.")

def main() -> None:
    TOKEN = '7010368994:AAHyerAeXdGl9VnzBnwnZ7t9JY2ogeIo1wg'
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
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex("^رصيدي$"), balance))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
