import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timezone
import json
import os

SUBSCRIBERS_FILE = 'subscribers.json'

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return {"subscribers": []}
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка чтения {SUBSCRIBERS_FILE}: {e}")
        return {"subscribers": []}

def save_subscribers(subscribers_data):
    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscribers_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка записи {SUBSCRIBERS_FILE}: {e}")

def add_or_update_subscriber(user: Update.effective_user):
    data = load_subscribers()
    subscribers = data.get("subscribers", [])

    user_data = {
        "user_id": user.id,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": user.username or "",
        "added_at": datetime.now(timezone.utc).isoformat(),
        "language_code": getattr(user, "language_code", "")
    }

    # Проверка: если есть такой user_id — не добавляем заново, можно обновить инфу
    for sub in subscribers:
        if sub["user_id"] == user.id:
            # обновляем только данные, но не дату добавления
            sub.update({k: v for k, v in user_data.items() if k != "added_at"})
            break
    else:
        # Новый подписчик
        subscribers.append(user_data)
        logger.info(f"Добавлен новый подписчик: {user_data}")

    data["subscribers"] = subscribers
    save_subscribers(data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_subscriber(user)
    await update.message.reply_text(
        "Привет! Ты добавлен в рассылку новостей."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши любое сообщение, чтобы подписаться на рассылку.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_subscriber(user)
    await update.message.reply_text("Спасибо за сообщение! Ты подписан на рассылку.")

def main():
    import config
    app = ApplicationBuilder().token(config.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))
    print("Бот запущен, ожидает сообщений...")
    app.run_polling()

if __name__ == '__main__':
    main()
