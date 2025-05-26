
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from config import api_id, api_hash

async def check_folders():
    """Проверить все доступные папки в Telegram"""
    SESSION_FILE = 'sessions/news_session'
    async with TelegramClient(SESSION_FILE, api_id, api_hash) as client:
        try:
            filters = await client(GetDialogFiltersRequest())
            print('📁 Доступные папки в Telegram:')
            for i, filter_obj in enumerate(filters.filters, 1):
                if hasattr(filter_obj, 'title'):
                    print(f'{i}. {filter_obj.title} ({len(filter_obj.include_peers)} каналов)')
                    
            print('\n💡 Используйте одно из этих названий в SPORT_FOLDER_NAME')
        except Exception as e:
            print(f'❌ Ошибка: {e}')

if __name__ == "__main__":
    asyncio.run(check_folders())
