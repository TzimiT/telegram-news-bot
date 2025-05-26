from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from config import api_id, api_hash
import json
import os
import asyncio

CHANNELS_FILE = "channels.json"
# Используем ту же изолированную сессию что и в session_manager
SESSION_FILE = 'sessions/news_session'

# Папка sessions уже создается в session_manager.py

async def main():
    """Основная функция для получения каналов"""
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
        channels = await get_channels_fullinfo_from_folder(client, "GPT")
        print(f"Найдено каналов: {len(channels)}")
        for ch in channels:
            print(f"- {ch.get('title', '?')} (@{ch.get('username', '?')})")

if __name__ == "__main__":
    asyncio.run(main())

def serialize_for_json(obj):
    """
    Рекурсивно приводит объект к сериализуемому виду (байты -> hex, ...).
    """
    if isinstance(obj, bytes):
        return obj.hex()  # Или obj.decode(errors='ignore'), если нужны строки
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    elif isinstance(obj, dict):
        return {serialize_for_json(k): serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [serialize_for_json(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return serialize_for_json(vars(obj))
    else:
        return str(obj)

async def get_channels_fullinfo_from_folder(client, folder_name, output_file=None):
    """Получает полную информацию о каналах из указанной папки Telegram"""
    if output_file is None:
        output_file = CHANNELS_FILE

    print(f"[LOG] Получаем информацию о каналах из папки '{folder_name}' -> {output_file}...")

    # Получаем все папки (фильтры диалогов)
    try:
        filters = await client(GetDialogFiltersRequest())
        target_filter = None

        for filter_obj in filters.filters:
            # Проверяем разные типы title (строка или TextWithEntities)
            filter_title = None
            if hasattr(filter_obj, 'title'):
                if hasattr(filter_obj.title, 'text'):
                    # TextWithEntities объект
                    filter_title = filter_obj.title.text
                else:
                    # Обычная строка
                    filter_title = filter_obj.title
            
            if filter_title == folder_name:
                target_filter = filter_obj
                break

        if not target_filter:
            print(f"[ERROR] Папка '{folder_name}' не найдена!")
            return []

        print(f"[LOG] Найдена папка '{folder_name}' с {len(target_filter.include_peers)} каналами")

        # Получаем полную информацию о каждом канале
        channels_info = []
        for peer in target_filter.include_peers:
            try:
                # Получаем полную информацию о канале
                entity = await client.get_entity(peer)

                # Конвертируем в JSON-совместимый формат
                channel_data = {
                    "id": entity.id,
                    "title": getattr(entity, 'title', None),
                    "username": getattr(entity, 'username', None),
                    "description": getattr(entity, 'about', None),
                    "participants_count": getattr(entity, 'participants_count', None),
                    "date": str(getattr(entity, 'date', None)),
                    "verified": getattr(entity, 'verified', False),
                    "scam": getattr(entity, 'scam', False),
                    "fake": getattr(entity, 'fake', False),
                    "access_hash": getattr(entity, 'access_hash', None),
                }

                channels_info.append(channel_data)
                print(f"[DEBUG] Добавлен канал: @{channel_data.get('username', 'unknown')} - {channel_data.get('title', 'No title')}")

            except Exception as e:
                print(f"[WARN] Не удалось получить информацию о канале {peer}: {e}")
                continue

        # Сохраняем в JSON файл
        data = {"channels": channels_info}
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[LOG] ✅ Сохранено {len(channels_info)} каналов в {output_file}")
        return channels_info

    except Exception as e:
        print(f"[ERROR] Ошибка получения каналов из папки: {e}")
        return []

def load_channels_from_json(filename=None):
    """Загружает каналы из JSON файла"""
    if filename is None:
        filename = CHANNELS_FILE

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('channels', [])
    except FileNotFoundError:
        print(f"[WARN] Файл {filename} не найден")
        return []
    except Exception as e:
        print(f"[ERROR] Ошибка чтения {filename}: {e}")
        return []