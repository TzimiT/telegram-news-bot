from telethon import TelegramClient
from config import api_id, api_hash
import asyncio
import os

SESSION_FILE = 'news_session'
SESSION_DIR = 'sessions'  # Define a session directory

# Create the session directory if it doesn't exist
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)


async def initialize_session():
    """Инициализирует сессию Telethon один раз"""
    print("🚀 Инициализация изолированной сессии для News Aggregator...")
    print(f"📁 Папка сессий: {SESSION_DIR}")

    # Проверяем, существует ли уже сессия
    if os.path.exists(f"{SESSION_FILE}.session"):
        print("✅ Файл сессии найден. Проверяем авторизацию...")
    else:
        print("📱 Файл сессии не найден. Создаем новую изолированную сессию...")

    try:
        # Используем уникальные параметры для изоляции сессии
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
            print("🔗 Подключение к Telegram...")
            await client.connect()

            if not await client.is_user_authorized():
                print("🔐 Требуется авторизация...")
                phone = input("📞 Введите номер телефона: ")
                await client.send_code_request(phone)
                code = input("📟 Введите код подтверждения: ")
                await client.sign_in(phone, code)
            else:
                print("✅ Сессия уже авторизована!")

            me = await client.get_me()
            print(f"✅ Изолированная сессия успешно создана и сохранена!")
            print(f"👤 Авторизован как: {me.first_name} {me.last_name or ''} (@{me.username or 'нет username'})")
            print(f"💾 Файл сессии: {SESSION_FILE}.session")
            print(f"🔒 Эта сессия изолирована и не влияет на другие Telegram сессии")

    except Exception as e:
        print(f"❌ Ошибка инициализации сессии: {e}")

if __name__ == "__main__":
    asyncio.run(initialize_session())