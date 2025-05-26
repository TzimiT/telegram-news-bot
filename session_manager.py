
from telethon import TelegramClient
from config import api_id, api_hash
import asyncio

async def initialize_session():
    """Инициализирует сессию Telethon один раз"""
    async with TelegramClient('news_session.session', api_id, api_hash) as client:
        print("Сессия успешно создана и сохранена!")
        me = await client.get_me()
        print(f"Авторизован как: {me.first_name} {me.last_name or ''} (@{me.username or 'нет username'})")

if __name__ == "__main__":
    print("Инициализация сессии Telegram...")
    asyncio.run(initialize_session())
