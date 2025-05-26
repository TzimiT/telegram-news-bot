
from telethon import TelegramClient
from telegram import Bot
import openai
from config import api_id, api_hash, telegram_bot_token, openai_api_key
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import logging

from get_channels import get_channels_fullinfo_from_folder, load_channels_from_json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sport_news_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Пользователь @avdovin для спортивной рассылки
SPORT_USER_ID = None  # Нужно будет получить user_id для @avdovin
SPORT_FOLDER_NAME = "Спорт"  # Измените на правильное название папки
SPORT_CHANNELS_FILE = "sport_channels.json"

def load_sport_channels():
    """Загрузить список каналов для спортивных новостей"""
    if os.path.exists(SPORT_CHANNELS_FILE):
        with open(SPORT_CHANNELS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('channels', [])
    return []

def get_yesterday_range():
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    return start, end

def summarize_sport_news(news_list):
    """Суммаризация спортивных новостей с фокусом на спорт"""
    text = "\n\n".join(news_list)
    client_ai = openai.OpenAI(api_key=openai_api_key)
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Сделай краткую сводку спортивных новостей за сутки по этим выдержкам, обязательно указывай источники. Если несколько новостей про одно и то же событие - кластеризуй в один пункт. Группируй новости по видам спорта. Подробнее освещай важные спортивные события, результаты матчей, трансферы и турниры."},
            {"role": "user", "content": text}
        ],
        max_tokens=3000,
        temperature=0.7
    )
    return response.choices[0].message.content

async def get_sport_news(client, channels):
    """Получение спортивных новостей за вчера"""
    all_news = []
    start, end = get_yesterday_range()
    print(f"[DEBUG] Диапазон фильтра спортивных новостей: {start} ... {end}")
    
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
                print(f"[DEBUG] SPORT {username} | id={message.id} | дата={msg_date_norm} - добавлено")
    
    return all_news

async def send_sport_news(summary, user_id):
    """Отправка спортивных новостей конкретному пользователю"""
    if not user_id:
        logger.warning("[WARN] User ID для спортивной рассылки не указан.")
        return

    bot = Bot(token=telegram_bot_token)
    
    logger.info(f"[INFO] Отправляю спортивные новости пользователю {user_id}")

    try:
        # Добавляем заголовок для спортивной рассылки
        sport_summary = f"🏆 **СПОРТИВНЫЕ НОВОСТИ ЗА ВЧЕРА**\n\n{summary}"
        
        result = await bot.send_message(chat_id=user_id, text=sport_summary, parse_mode='Markdown')
        logger.info(f"[SUCCESS] Спортивные новости отправлены пользователю {user_id}, message_id={result.message_id}")
        return True
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[FAILED] Не удалось отправить спортивные новости пользователю {user_id}: {error_msg}")
        return False

SESSION_FILE = 'sessions/news_session'

async def main_sport():
    """Основная функция для спортивной рассылки"""
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
        device_model="Replit Sport News Bot v1.0",
        system_version="Linux Replit", 
        app_version="1.0.0",
        lang_code="ru",
        system_lang_code="ru",
        use_ipv6=False,
        proxy=None
    ) as client:
        # Проверяем авторизацию
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Сессия не авторизована! Запустите workflow 'Setup Session'.")
            return

        # Получаем user_id для @avdovin если еще не знаем
        global SPORT_USER_ID
        if not SPORT_USER_ID:
            try:
                avdovin_user = await client.get_entity('@avdovin')
                SPORT_USER_ID = avdovin_user.id
                logger.info(f"[INFO] Найден пользователь @avdovin с ID: {SPORT_USER_ID}")
            except Exception as e:
                logger.error(f"[ERROR] Не удалось найти пользователя @avdovin: {e}")
                return

        # Шаг 1: Получить каналы из папки "Sport"
        print(f"[LOG] Проверяю спортивные каналы в папке '{SPORT_FOLDER_NAME}'...")
        await get_channels_fullinfo_from_folder(client, SPORT_FOLDER_NAME, SPORT_CHANNELS_FILE)

        # Шаг 2: Загрузить спортивные каналы
        channels = load_sport_channels()
        print(f"[LOG] Спортивные каналы для агрегации ({len(channels)} шт.): {[ch.get('username','?') for ch in channels]}")

        if not channels:
            print(f"[ERROR] Не найдено спортивных каналов в папке '{SPORT_FOLDER_NAME}'.")
            return

        # Шаг 3: Собрать спортивные новости
        news = await get_sport_news(client, channels)
        print(f"[LOG] Количество найденных спортивных новостей за вчера: {len(news)}")
        
        if not news:
            print("[LOG] Нет спортивных новостей за вчера. Прерываю рассылку.")
            return

        # Шаг 4: Суммаризация и отправка
        summary = summarize_sport_news(news)
        success = await send_sport_news(summary, SPORT_USER_ID)
        
        if success:
            print("[LOG] ✅ Спортивная рассылка успешно отправлена!")
        else:
            print("[LOG] ❌ Ошибка отправки спортивной рассылки.")

async def run_sport_continuous():
    """Непрерывная работа службы спортивных новостей"""
    logger.info("🏆 Служба спортивных новостей для @avdovin запущена")
    logger.info("📅 Рассылка запланирована на 10:00 UTC каждый день")

    while True:
        try:
            # Время рассылки спортивных новостей - 10:00 UTC (на час позже основных)
            now = datetime.now(timezone.utc)
            next_run = now.replace(hour=10, minute=0, second=0, microsecond=0)

            if now >= next_run:
                next_run += timedelta(days=1)

            wait_time = (next_run - now).total_seconds()
            wait_hours = wait_time / 3600

            logger.info(f"⏰ Следующая спортивная рассылка: {next_run}")
            logger.info(f"⏱️ Ожидание: {wait_hours:.1f} часов")

            await asyncio.sleep(wait_time)

            logger.info("🏆 Время спортивной рассылки! Запускаю агрегацию...")
            await main_sport()

        except Exception as e:
            logger.error(f"❌ Ошибка в службе спортивных новостей: {e}")
            await asyncio.sleep(3600)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Sport News Bot для @avdovin')
    parser.add_argument('--once', action='store_true', help='Запустить один раз')
    args = parser.parse_args()

    if args.once:
        asyncio.run(main_sport())
    else:
        asyncio.run(run_sport_continuous())
