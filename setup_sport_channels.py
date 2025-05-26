
import asyncio
from telethon import TelegramClient
from config import api_id, api_hash
from get_channels import get_channels_fullinfo_from_folder

async def setup_sport_channels():
    """Настройка спортивных каналов из папки Sport"""
    SESSION_FILE = 'sessions/news_session'
    async with TelegramClient(SESSION_FILE, api_id, api_hash) as client:
        try:
            await get_channels_fullinfo_from_folder(client, 'Sport', 'sport_channels.json')
            print('✅ Спортивные каналы настроены!')
        except Exception as e:
            print(f'❌ Ошибка настройки спортивных каналов: {e}')

if __name__ == "__main__":
    asyncio.run(setup_sport_channels())
