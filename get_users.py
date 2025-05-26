import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
import json
import os
from datetime import datetime, timedelta, timezone
from database import db

RECOMMEND_WAIT_INPUT = 1

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def get_next_news_time():
    """Получить время следующей рассылки новостей"""
    now = datetime.now(timezone.utc)
    next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)

    # Если время уже прошло сегодня, планируем на завтра
    if now >= next_run:
        next_run += timedelta(days=1)

    time_diff = next_run - now
    hours_left = int(time_diff.total_seconds() // 3600)
    minutes_left = int((time_diff.total_seconds() % 3600) // 60)

    return {
        'datetime': next_run,
        'hours': hours_left,
        'minutes': minutes_left,
        'formatted': next_run.strftime('%d.%m.%Y в %H:%M UTC')
    }

def get_channels_list():
    """Получить список каналов для агрегации"""
    try:
        with open("channels.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            channels = data.get("channels", [])

        if not channels:
            return "📭 Список каналов временно пуст"

        channel_names = []
        for channel in channels:
            if channel.get('username'):
                channel_names.append(f"@{channel['username']}")
            elif channel.get('title'):
                channel_names.append(channel['title'])

        return "\n".join([f"• {name}" for name in channel_names[:10]]) + \
               (f"\n• и ещё {len(channel_names) - 10} каналов..." if len(channel_names) > 10 else "")
    except Exception as e:
        logger.error(f"Ошибка загрузки каналов: {e}")
        return "📭 Ошибка загрузки списка каналов"

def save_subscriber(user: Update.effective_user):
    """Сохранить подписчика в базу данных"""
    existing_user = db.get_user_info(user.id)
    if not existing_user or not existing_user['is_active']:
        success = db.add_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name
        )
        if success:
            logger.info(f"Добавлен новый подписчик: {user.id} (@{user.username})")
            return True
    else:
        # Обновляем время взаимодействия
        db.update_user_interaction(user.id)
    return False

def remove_subscriber(user_id):
    """Удалить подписчика из базы данных"""
    db.remove_user(user_id)
    logger.info(f"Пользователь {user_id} удалён из подписчиков.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    was_added = save_subscriber(user)

    next_news = get_next_news_time()
    channels_list = get_channels_list()

    if was_added:
        await update.message.reply_text(
            "🤖 Привет! Ты добавлен в рассылку агрегации новостей про AI.\n\n"
            f"Следующая рассылка: {next_news['formatted']}\n"
            f"Каналы для агрегации:\n{channels_list}"
        )
    else:
        await update.message.reply_text("✅ Ты уже в списке рассылки агрегации новостей про AI.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Бот агрегации новостей про AI**\n\n"
        "📰 Напиши любое сообщение, чтобы подписаться на рассылку.\n\n"
        "**Доступные команды:**\n"
        "/start — подписаться на рассылку агрегации новостей про AI\n"
        "/stop — отписаться от рассылки\n"
        "/recommend_channel — предложить новый источник новостей/канал в телеге про AI\n"
        "/channels — список каналов для агрегации\n"
        "/status — твой статус подписки\n"
        "/help — показать это сообщение",
        parse_mode='Markdown'
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    was_added = save_subscriber(user)

    next_news = get_next_news_time()
    channels_list = get_channels_list()

    if was_added:
        await update.message.reply_text(
            "🤖 Спасибо за сообщение! Ты добавлен в рассылку агрегации новостей про AI.\n\n"
            f"Следующая рассылка: {next_news['formatted']}\n"
            f"Каналы для агрегации:\n{channels_list}"
        )
    else:
        await update.message.reply_text("Ты уже подписан на рассылку.")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    remove_subscriber(user.id)
    await update.message.reply_text("😢 Ты отписан от рассылки агрегации новостей про AI. Возвращайся, если что!")

# --- Recommend Channel Conversation ---

async def recommend_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 Пожалуйста, отправьте ссылку на канал или username (@example) про AI, который вы хотите предложить для рассылки.\n\n"
        "💡 Можно добавить комментарий, почему этот канал стоит добавить.\n\n"
        "Отправьте /cancel для отмены."
    )
    return RECOMMEND_WAIT_INPUT

async def recommend_channel_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # Сохраняем в базу данных
    db.add_channel_recommendation(user.id, text)

    # Также сохраняем в текстовый файл для совместимости
    rec_info = (
        f"date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"user_id: {user.id} | username: @{user.username or '-'} | "
        f"name: {user.first_name or '-'} {user.last_name or '-'} | "
        f"recommend: {text}\n"
    )
    with open("channel_recommendations.txt", "a", encoding="utf-8") as f:
        f.write(rec_info)

    await update.message.reply_text("Спасибо! Ваша рекомендация отправлена администратору.")
    return ConversationHandler.END

async def recommend_channel_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Рекомендация отменена.")
    return ConversationHandler.END

# --- /channels: показать список каналов (читает channels.json) ---
async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("channels.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            channels = data.get("channels", [])
        if not channels:
            await update.message.reply_text("Список каналов пуст.")
            return
        msg = "Список каналов для агрегации:\n" + "\n".join(
            f"@{c['username']}" if c.get('username') else c.get('title', '-') for c in channels
        )
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Не удалось получить список каналов: {e}")

# --- /status: статус подписки ---
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = db.get_user_info(user.id)

    if user_info and user_info['is_active']:
        stats = db.get_user_stats()
        await update.message.reply_text(
            f"✅ **Статус подписки:** Ты подписан на рассылку агрегации новостей про AI\n\n"
            f"📊 Всего активных подписчиков: {stats['active_users']}\n"
            f"📅 Дата подписки: {user_info['added_at']}\n"
            f"🕐 Последняя активность: {user_info['last_interaction']}"
        )
    else:
        await update.message.reply_text(
            "❌ **Статус подписки:** Ты НЕ подписан на рассылку агрегации новостей про AI\n\n"
            "Напиши /start чтобы подписаться!"
        )

# --- /admin_stats: статистика для админов ---
async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Простая проверка на админа (можете добавить список админов в config)
    admin_ids = [94598500]  # Замените на ваши ID

    if user.id not in admin_ids:
        await update.message.reply_text("❌ У вас нет прав для просмотра статистики.")
        return

    stats = db.get_user_stats()

    message = f"""
📊 **Статистика пользователей базы данных:**

👥 Активных пользователей: {stats['active_users']}
📋 Всего пользователей: {stats['total_users']}

🕐 **Последние активные пользователи:**
"""

    for user_data in stats['recent_users']:
        username, first_name, last_name, last_interaction = user_data
        name = f"{first_name} {last_name}".strip()
        message += f"• @{username} ({name}) - {last_interaction}\n"

    await update.message.reply_text(message)



def main():
    import config  # импортирует telegram_bot_token из твоего конфига

    app = ApplicationBuilder().token(config.telegram_bot_token).build()

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("channels", channels_command))
    app.add_handler(CommandHandler("admin_stats", admin_stats_command))

    # Conversation handler для рекомендации каналов
    recommend_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("recommend_channel", recommend_channel_start)],
        states={
            RECOMMEND_WAIT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, recommend_channel_receive)]
        },
        fallbacks=[CommandHandler("cancel", recommend_channel_cancel)]
    )
    app.add_handler(recommend_conv_handler)

    # Обработчик всех остальных сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()