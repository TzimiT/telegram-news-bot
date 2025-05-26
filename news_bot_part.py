from telethon import TelegramClient
from telegram import Bot
import openai
from config import api_id, api_hash, telegram_bot_token, openai_api_key, FOLDER_NAME
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import logging

from get_channels import get_channels_fullinfo_from_folder, load_channels_from_json
from database import db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('subscribers_log.txt', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = 'subscribers.json'

def load_subscribers():
    """Загрузить список подписчиков из файла"""
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('subscribers', [])
        else:
            # Миграция из старого файла, если новый не существует
            return migrate_old_subscribers()
    except Exception as e:
        logger.error(f"[ERROR] Ошибка чтения {SUBSCRIBERS_FILE}: {e}")
        return []

def migrate_old_subscribers():
    OLD_SUBSCRIBERS_FILE = 'subscribers_id.txt'
    new_subscribers = []
    if os.path.exists(OLD_SUBSCRIBERS_FILE):
        try:
            with open(OLD_SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                old_ids = [line.strip() for line in f.readlines()]

            for user_id in old_ids:
                try:
                    user_id = int(user_id)
                    new_subscribers.append({
                        "user_id": user_id,
                        "subscribed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "migrated": True
                    })
                except ValueError:
                    continue

            if new_subscribers:
                with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"subscribers": new_subscribers}, f, ensure_ascii=False, indent=2)

                logger.info(f"[INFO] Мигрировано {len(new_subscribers)} подписчиков из старого файла")
            return new_subscribers
        except Exception as e:
            logger.error(f"[ERROR] Ошибка миграции старых подписчиков: {e}")
    return []

def get_yesterday_range():
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    return start, end

def summarize_news(news_list):
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

async def get_news(client, channels):
    all_news = []
    start, end = get_yesterday_range()
    print(f"[DEBUG] Диапазон фильтра: {start} ... {end}")
    for channel_info in channels:
        username = channel_info.get("username")
        if not username:
            continue
        async for message in client.iter_messages(username):
            msg_date = message.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            msg_date_norm = msg_date.replace(microsecond=0)
            if msg_date_norm < start:
                break
            if start <= msg_date_norm < end and message.text:
                all_news.append(f"{message.text}\nИсточник: https://t.me/{username}/{message.id}\n")
                print(f"[DEBUG] {username} | id={message.id} | дата={msg_date_norm} - добавлено")
    return all_news

async def send_news(summary):
    # Получаем только активных пользователей
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
            # Обновляем статистику взаимодействия
            db.update_user_interaction(user_id)
            successful_sends += 1
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[FAILED] Не удалось отправить сообщение пользователю {user_id}: {error_msg}")
            failed_subscribers.append(user_id)
            
            # Деактивируем пользователя только при определенных ошибках
            if "Chat not found" in error_msg or "Forbidden: bot was blocked" in error_msg:
                db.remove_user(user_id)
                logger.info(f"[INFO] Пользователь {user_id} деактивирован из-за недоступности чата")

    logger.info(f"[INFO] Рассылка завершена: успешно={successful_sends}, неудачно={len(failed_subscribers)}")

    if failed_subscribers:
        logger.warning(f"[INFO] Проблемы с отправкой {len(failed_subscribers)} пользователям")

SESSION_FILE = 'sessions/news_session'

async def main():
    # Проверяем наличие файла сессии
    if not os.path.exists(f"{SESSION_FILE}.session"):
        print(f"❌ Файл сессии {SESSION_FILE}.session не найден!")
        print("Запустите workflow 'Setup Session' для создания сессии.")
        return
    else:
        print(f"✅ Файл сессии {SESSION_FILE}.session найден")

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
        # Проверяем авторизацию без интерактивного ввода
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Сессия не авторизована! Запустите workflow 'Setup Session' для повторной авторизации.")
            return
        # Шаг 1: Получить и сохранить полную инфу о каналах из папки
        await get_channels_fullinfo_from_folder(client, FOLDER_NAME)
        # Шаг 2: Загрузить полную инфу о каналах для рассылки
        channels = load_channels_from_json()
        print(f"[LOG] Каналы для агрегации: {[ch.get('username','?') for ch in channels]}")

        # Шаг 3: Собрать новости
        news = await get_news(client, channels)
        print(f"[LOG] Количество найденных новостей за вчера: {len(news)}")
        if not news:
            print("[LOG] Нет новостей за вчера. Прерываю рассылку.")
            return

        # Шаг 4: Суммаризация и рассылка
        summary = summarize_news(news)
        await send_news(summary)

async def run_continuous():
    """Непрерывная работа с расписанием"""
    
    logger.info("🔄 Служба агрегации новостей запущена")
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
            await main()
            
        except KeyboardInterrupt:
            logger.info("⏹️ Служба остановлена пользователем")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в основном цикле: {e}")
            logger.exception("Полная трассировка ошибки:")
            await asyncio.sleep(300)  # ждем 5 минут при ошибке

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Запуск рассылки один раз (для тестирования)
        asyncio.run(main())
    else:
        # Постоянная работа с расписанием
        asyncio.run(run_continuous())