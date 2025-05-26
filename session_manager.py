
from telethon import TelegramClient
from config import api_id, api_hash
import asyncio
import os

SESSION_FILE = 'news_session'

async def initialize_session():
    """Инициализирует сессию Telethon один раз"""
    print("Инициализация сессии Telegram...")
    
    # Проверяем, существует ли уже сессия
    if os.path.exists(f"{SESSION_FILE}.session"):
        print("Файл сессии уже существует. Проверяем подключение...")
    
    try:
        async with TelegramClient(SESSION_FILE, api_id, api_hash) as client:
            print("Подключение к Telegram...")
            await client.connect()
            
            if not await client.is_user_authorized():
                print("Требуется авторизация...")
                phone = input("Введите номер телефона: ")
                await client.send_code_request(phone)
                code = input("Введите код подтверждения: ")
                await client.sign_in(phone, code)
            
            me = await client.get_me()
            print(f"✅ Сессия успешно создана и сохранена!")
            print(f"Авторизован как: {me.first_name} {me.last_name or ''} (@{me.username or 'нет username'})")
            print(f"Файл сессии: {SESSION_FILE}.session")
            
    except Exception as e:
        print(f"❌ Ошибка инициализации сессии: {e}")

if __name__ == "__main__":
    asyncio.run(initialize_session())
