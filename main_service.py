
import asyncio
import logging
from datetime import datetime, timedelta, timezone
import json
import os
from telethon import TelegramClient
from telegram import Bot, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
import openai

from config import api_id, api_hash, telegram_bot_token, openai_api_key, FOLDER_NAME
from get_channels import get_channels_fullinfo_from_folder, load_channels_from_json
from database import db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Константы для ConversationHandler
RECOMMEND_WAIT_INPUT = 1
SESSION_FILE = 'sessions/news_session'

class MainService:
    def __init__(self):
        self.telegram_app = None
        self.news_task = None
        self.bot_task = None
        
    async def start_services(self):
        """Запуск всех сервисов"""
        logger.info("🚀 Запуск объединенного сервиса 24/7...")
        
        # Запускаем Telegram бота для пользователей
        await self.start_user_bot()
        
        # Запускаем задачу агрегации новостей
        self.news_task = asyncio.create_task(self.news_aggregator_service())
        
        logger.info("✅ Все сервисы запущены!")
        
        # Ждем завершения задач
        await asyncio.gather(
            self.news_task,
            return_exceptions=True
        )
    
    async def start_user_bot(self):
        """Запуск Telegram бота для взаимодействия с пользователями"""
        try:
            app = ApplicationBuilder().token(telegram_bot_token).build()
            
            # Основные команды
            app.add_handler(CommandHandler("start", self.start_command))
            app.add_handler(CommandHandler("help", self.help_command))
            app.add_handler(CommandHandler("stop", self.stop_command))
            app.add_handler(CommandHandler("status", self.status_command))
            app.add_handler(CommandHandler("channels", self.channels_command))
            app.add_handler(CommandHandler("admin_stats", self.admin_stats_command))
            
            # Conversation handler для рекомендации каналов
            recommend_conv_handler = ConversationHandler(
                entry_points=[CommandHandler("recommend_channel", self.recommend_channel_start)],
                states={
                    RECOMMEND_WAIT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.recommend_channel_receive)]
                },
                fallbacks=[CommandHandler("cancel", self.recommend_channel_cancel)]
            )
            app.add_handler(recommend_conv_handler)
            
            # Обработчик всех остальных сообщений
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))
            
            logger.info("🤖 Telegram бот для пользователей запущен...")
            
            # Запускаем бота в отдельной задаче
            self.bot_task = asyncio.create_task(app.run_polling())
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска пользовательского бота: {e}")
    
    async def news_aggregator_service(self):
        """Сервис агрегации новостей с расписанием"""
        logger.info("📰 Служба агрегации новостей запущена")
        logger.info("📅 Рассылка запланирована на 09:00 UTC каждый день")
        
        while True:
            try:
                # Получаем текущее время UTC
                now = datetime.now(timezone.utc)
                target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
                
                # Если время уже прошло сегодня, планируем на завтра
                if now >= target_time:
                    target_time += timedelta(days=1)
                
                # Вычисляем время до следующего запуска
                sleep_seconds = (target_time - now).total_seconds()
                
                logger.info(f"⏰ Следующая рассылка: {target_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                logger.info(f"⏱️ Ожидание: {sleep_seconds/3600:.1f} часов")
                
                # Спим до времени рассылки
                await asyncio.sleep(sleep_seconds)
                
                # Выполняем рассылку
                logger.info("🚀 Запуск рассылки новостей...")
                await self.send_daily_news()
                
            except Exception as e:
                logger.error(f"❌ Ошибка в службе агрегации новостей: {e}")
                logger.exception("Полная трассировка ошибки:")
                await asyncio.sleep(300)  # ждем 5 минут при ошибке
    
    async def send_daily_news(self):
        """Основная функция отправки новостей"""
        try:
            # Проверяем наличие файла сессии
            if not os.path.exists(f"{SESSION_FILE}.session"):
                logger.error(f"❌ Файл сессии {SESSION_FILE}.session не найден!")
                logger.error("Запустите workflow 'Setup Session' для создания сессии.")
                return
            
            async with TelegramClient(
                SESSION_FILE, 
                api_id, 
                api_hash,
                device_model="Replit News Bot v2.1",
                system_version="Linux Replit", 
                app_version="2.1.0",
                lang_code="ru",
                system_lang_code="ru",
                use_ipv6=False,
                proxy=None
            ) as client:
                # Проверяем авторизацию
                await client.connect()
                if not await client.is_user_authorized():
                    logger.error("❌ Сессия не авторизована! Запустите workflow 'Setup Session'.")
                    return
                
                # Обновляем каналы
                logger.info(f"[LOG] Проверяю обновления каналов в папке '{FOLDER_NAME}'...")
                await get_channels_fullinfo_from_folder(client, FOLDER_NAME)
                
                # Загружаем каналы
                channels = load_channels_from_json()
                logger.info(f"[LOG] Каналы для агрегации ({len(channels)} шт.): {[ch.get('username','?') for ch in channels]}")
                
                if not channels:
                    logger.error(f"[ERROR] Не найдено каналов в папке '{FOLDER_NAME}'.")
                    return
                
                # Собираем новости
                news = await self.get_news(client, channels)
                logger.info(f"[LOG] Количество найденных новостей за вчера: {len(news)}")
                
                if not news:
                    logger.info("[LOG] Нет новостей за вчера. Пропускаем рассылку.")
                    return
                
                # Суммаризация и рассылка
                summary = self.summarize_news(news)
                await self.send_news(summary)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в отправке новостей: {e}")
            logger.exception("Полная трассировка ошибки:")
    
    async def get_news(self, client, channels):
        """Получение новостей за вчера"""
        all_news = []
        start, end = self.get_yesterday_range()
        logger.debug(f"[DEBUG] Диапазон фильтра: {start} ... {end}")
        
        for channel_info in channels:
            username = channel_info.get("username")
            if not username:
                continue
            try:
                async for message in client.iter_messages(username):
                    msg_date = message.date
                    if msg_date.tzinfo is None:
                        msg_date = msg_date.replace(tzinfo=timezone.utc)
                    msg_date_norm = msg_date.replace(microsecond=0)
                    if msg_date_norm < start:
                        break
                    if start <= msg_date_norm < end and message.text:
                        all_news.append(f"{message.text}\nИсточник: https://t.me/{username}/{message.id}\n")
                        logger.debug(f"[DEBUG] {username} | id={message.id} | дата={msg_date_norm} - добавлено")
            except Exception as e:
                logger.warning(f"[WARN] Ошибка получения сообщений из {username}: {e}")
        
        return all_news
    
    def get_yesterday_range(self):
        """Получить временной диапазон за вчера"""
        today = datetime.now(timezone.utc).date()
        start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        return start, end
    
    def summarize_news(self, news_list):
        """Суммаризация новостей через OpenAI"""
        text = "\n\n".join(news_list)
        client_ai = openai.OpenAI(api_key=openai_api_key)
        response = client_ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Сделай краткую сводку новостей за сутки по этим выдержкам, обязательно указывай источники. Если несколько новостей про одно и то же - кластеризуй в один пункт. Подробнее освещай всё про AI."},
                {"role": "user", "content": text}
            ],
            max_tokens=3000,
            temperature=0.7
        )
        return response.choices[0].message.content
    
    async def send_news(self, summary):
        """Отправка новостей подписчикам"""
        subscribers = db.get_active_users()
        if not subscribers:
            logger.warning("[WARN] Нет активных подписчиков для рассылки.")
            return
        
        bot = Bot(token=telegram_bot_token)
        successful_sends = 0
        failed_subscribers = []
        
        logger.info(f"[INFO] Начинаю рассылку для {len(subscribers)} активных подписчиков")
        
        for user_id in subscribers:
            try:
                result = await bot.send_message(chat_id=user_id, text=summary)
                logger.info(f"[SUCCESS] Сообщение отправлено пользователю {user_id}, message_id={result.message_id}")
                db.update_user_interaction(user_id)
                successful_sends += 1
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[FAILED] Не удалось отправить сообщение пользователю {user_id}: {error_msg}")
                failed_subscribers.append(user_id)
                
                # Деактивируем пользователя при ошибках чата
                if "Chat not found" in error_msg or "Forbidden: bot was blocked" in error_msg:
                    db.remove_user(user_id)
                    logger.info(f"[INFO] Пользователь {user_id} деактивирован из-за недоступности чата")
        
        logger.info(f"[INFO] Рассылка завершена: успешно={successful_sends}, неудачно={len(failed_subscribers)}")
    
    # ============ КОМАНДЫ ПОЛЬЗОВАТЕЛЬСКОГО БОТА ============
    
    def save_subscriber(self, user):
        """Сохранить подписчика в базу данных"""
        existing_user = db.get_user_info(user.id)
        if not existing_user or not existing_user['is_active']:
            success = db.add_user(user.id, user.username, user.first_name, user.last_name)
            if success:
                logger.info(f"Добавлен новый подписчик: {user.id} (@{user.username})")
                return True
        else:
            db.update_user_interaction(user.id)
        return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        was_added = self.save_subscriber(user)
        await update.message.reply_text(
            "🤖 Привет! Ты добавлен в рассылку агрегации новостей про AI." if was_added else "✅ Ты уже в списке рассылки агрегации новостей про AI."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        was_added = self.save_subscriber(user)
        if was_added:
            await update.message.reply_text("🤖 Спасибо за сообщение! Ты добавлен в рассылку агрегации новостей про AI.")
        else:
            await update.message.reply_text("Ты уже подписан на рассылку.")
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db.remove_user(user.id)
        logger.info(f"Пользователь {user.id} удалён из подписчиков.")
        await update.message.reply_text("😢 Ты отписан от рассылки агрегации новостей про AI. Возвращайся, если что!")
    
    async def recommend_channel_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📢 Пожалуйста, отправьте ссылку на канал или username (@example) про AI, который вы хотите предложить для рассылки.\n\n"
            "💡 Можно добавить комментарий, почему этот канал стоит добавить.\n\n"
            "Отправьте /cancel для отмены."
        )
        return RECOMMEND_WAIT_INPUT
    
    async def recommend_channel_receive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text.strip()
        
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
    
    async def recommend_channel_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Рекомендация отменена.")
        return ConversationHandler.END
    
    async def channels_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
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

async def main():
    """Главная функция запуска сервиса"""
    service = MainService()
    try:
        await service.start_services()
    except KeyboardInterrupt:
        logger.info("⏹️ Сервис остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка сервиса: {e}")
        logger.exception("Полная трассировка ошибки:")

if __name__ == "__main__":
    asyncio.run(main())
