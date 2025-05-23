import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

SUBSCRIBERS_FILE = 'subscribers.txt'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_subscriber(user_id):
    subscribers = load_subscribers()
    if str(user_id) not in subscribers:
        with open(SUBSCRIBERS_FILE, 'a') as f:
            f.write(f"{user_id}\n")
        logger.info(f"Added new subscriber: {user_id}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_subscriber(user_id)
    await update.message.reply_text(
        "Привет! Ты добавлен в рассылку новостей."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши любое сообщение, чтобы подписаться на рассылку.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_subscriber(user_id)
    await update.message.reply_text("Спасибо за сообщение! Ты подписан на рассылку.")

def main():
    import config  # импортируем telegram_bot_token из твоего конфига

    app = ApplicationBuilder().token(config.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    print("Бот запущен, ожидает сообщений...")
    app.run_polling()

if __name__ == '__main__':
    main()
