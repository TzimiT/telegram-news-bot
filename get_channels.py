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

async def get_channels_fullinfo_from_folder(client, folder_name):
    filters_resp = await client(GetDialogFiltersRequest())
    filters = None
    for attr in ['results', 'filters', 'dialog_filters']:
        if hasattr(filters_resp, attr):
            filters = getattr(filters_resp, attr)
            break
    if filters is None:
        raise Exception(f"Не найдено ни одно поле с фильтрами в {dir(filters_resp)}")

    result_channels = []
    for f in filters:
        title = ""
        if hasattr(f, "title"):
            if hasattr(f.title, "text"):
                title = f.title.text
            else:
                title = f.title
        elif hasattr(f, "text") and hasattr(f.text, "text"):
            title = f.text.text

        if title == folder_name:
            if hasattr(f, 'include_peers') and f.include_peers:
                for peer in f.include_peers:
                    try:
                        entity = await client.get_entity(peer)
                        # Сохраняем ВСЕ данные с сериализацией!
                        info = entity.to_dict() if hasattr(entity, "to_dict") else {}
                        info = serialize_for_json(info)
                        if hasattr(entity, "username") and entity.username:
                            info["username"] = entity.username
                        if hasattr(entity, "id"):
                            info["id"] = entity.id
                        if hasattr(entity, "title"):
                            info["title"] = entity.title
                        result_channels.append(info)
                    except Exception as e:
                        print(f"[WARN] Не смог получить инфу для peer {peer}: {e}")
            break

    # Читаем старый список каналов для сравнения
    old_channels = []
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                old_channels = old_data.get("channels", [])
        except:
            pass
    
    # Сохраняем новый список
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump({"channels": result_channels}, f, ensure_ascii=False, indent=2)

    # Анализируем изменения
    old_usernames = {ch.get('username') for ch in old_channels if ch.get('username')}
    new_usernames = {ch.get('username') for ch in result_channels if ch.get('username')}
    
    added = new_usernames - old_usernames
    removed = old_usernames - new_usernames
    
    if added:
        print(f"[LOG] ✅ Добавлены новые каналы: {list(added)}")
    if removed:
        print(f"[LOG] ❌ Удалены каналы: {list(removed)}")
    if not added and not removed and old_channels:
        print(f"[LOG] 📋 Список каналов не изменился ({len(result_channels)} шт.)")
    elif not old_channels:
        print(f"[LOG] 🆕 Создан новый список каналов ({len(result_channels)} шт.)")

    if not result_channels:
        print(f"[WARN] Папка '{folder_name}' не найдена или пуста")

    return result_channels

def load_channels_from_json():
    if not os.path.exists(CHANNELS_FILE):
        print(f"[WARN] Файл {CHANNELS_FILE} не найден.")
        return []
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("channels", [])
