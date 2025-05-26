import logging
import json
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
import config

SUBSCRIBERS_FILE = "subscribers.json"

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("subscribers", [])
    except FileNotFoundError:
        logger.warning("Файл с подписчиками не найден, создаём новый.")
        return []
    except Exception as e:
        logger.error(f"Ошибка чтения {SUBSCRIBERS_FILE}: {e}")
        return []

def save_subscribers(subscribers):
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"subscribers": subscribers}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка записи {SUBSCRIBERS_FILE}: {e}")

def find_subscriber(subscribers, user_id):
    return next((user for user in subscribers if user["user_id"] == user_id), None)

def add_subscriber(user):
    subscribers = load_subscribers()
    if find_subscriber(subscribers, user["user_id"]) is None:
        subscribers.append(user)
        save_subscribers(subscribers)
        logger.info(f"[NEW SUBSCRIBER] {user}")
        return True
    return False

def remove_subscriber(user_id):
    subscribers = load_subscribers()
    new_subs = [user for user in subscribers if user["user_id"] != user_id]
    if len(new_subs) < len(subscribers):
        save_subscribers(new_subs)
        logger.info(f"[UNSUBSCRIBED] user_id={user_id}")
        return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_obj = {
        "user_id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "joined": datetime.utcnow().isoformat()
    }
    if add_subscriber(user_obj):
        await update.message.reply_text("Привет! Ты добавлен в рассылку новостей.")
    else:
        await update.message.reply_text("Ты уже подписан на рассылку.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши любое сообщение, чтобы подписаться на рассылку.\nКоманда /stop — отписаться от рассылки.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_obj = {
        "user_id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "joined": datetime.utcnow().isoformat()
    }
    if add_subscriber(user_obj):
        await update.message.reply_text("Спасибо за сообщение! Ты подписан на рассылку.")
    else:
        await update.message.reply_text("Ты уже подписан на рассылку.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if remove_subscriber(user_id):
        await update.message.reply_text("Вы успешно отписались от рассылки.")
    else:
        await update.message.reply_text("Вы не были в списке подписчиков.")

def main():
    app = ApplicationBuilder().token(config.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))
    logger.info("Бот запущен, ожидает сообщений...")
    app.run_polling()

if __name__ == '__main__':
    main()
