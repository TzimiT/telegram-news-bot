from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon import TelegramClient
from config import api_id, api_hash

async def get_channel_usernames_from_folder(folder_name):
    async with TelegramClient('anon', api_id, api_hash) as temp_client:
        filters_resp = await temp_client(GetDialogFiltersRequest())
        # autodetect field with filters list
        filters = None
        for attr in ['results', 'filters', 'dialog_filters']:
            if hasattr(filters_resp, attr):
                filters = getattr(filters_resp, attr)
                break
        if filters is None:
            raise Exception(f"Не найдено ни одно поле с фильтрами в {dir(filters_resp)}")
        
        found = False
        channel_usernames = []
        for f in filters:
            # Для Telethon 1.40 f.title иногда TextWithEntities!
            title = ""
            if hasattr(f, "title"):
                if hasattr(f.title, "text"):
                    title = f.title.text
                else:
                    title = f.title
            elif hasattr(f, "text") and hasattr(f.text, "text"):
                title = f.text.text

            if title == folder_name:
                found = True
                if hasattr(f, 'include_peers') and f.include_peers:
                    for peer in f.include_peers:
                        try:
                            entity = await temp_client.get_entity(peer)
                            if hasattr(entity, 'username') and entity.username:
                                channel_usernames.append(entity.username)
                        except Exception as e:
                            print(f"[WARN] Не смог получить username для peer {peer}: {e}")
                break

        if not found:
            print(f"[WARN] Папка '{folder_name}' не найдена")
        return channel_usernames
