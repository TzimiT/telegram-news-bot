# get_channels.py

from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from config import api_id, api_hash, FOLDER_NAME

def get_channel_usernames_from_folder(folder_name=FOLDER_NAME):
    with TelegramClient('anon', api_id, api_hash) as temp_client:
        filters = temp_client(GetDialogFiltersRequest())
        target_filter = None
        for f in filters.filters:
            if hasattr(f, 'title') and f.title.text == folder_name:
                target_filter = f
                break
        if not target_filter:
            print(f"Папка '{folder_name}' не найдена.")
            return []
        usernames = []
        for peer in target_filter.include_peers:
            entity = temp_client.get_entity(peer)
            if hasattr(entity, 'username') and entity.username:
                usernames.append(entity.username)
        return usernames

# Для ручного теста:
if __name__ == "__main__":
    print(get_channel_usernames_from_folder())