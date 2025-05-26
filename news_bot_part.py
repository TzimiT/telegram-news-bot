from telethon.sync import TelegramClient
from telegram import Bot
import openai
from config import api_id, api_hash, telegram_bot_token, openai_api_key, FOLDER_NAME
from get_channels import get_channel_usernames_from_folder
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os

SUBSCRIBERS_FILE = 'subscribers.json'

def load_subscribers():
    """ Загружает user_id всех активных подписчиков из JSON. """
    if not os.path.exists(SUBSCRIBERS_FILE):
        print("[WARN] Файл с подписчиками не найден, список пуст")
        return []
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Обработка случая старого формата (просто список int)
        if isinstance(data, list):
            # Переписываем файл в новый формат
            new_data = {"subscribers": [{"user_id": uid} for uid in data]}
            with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as fw:
                json.dump(new_data, fw, ensure_ascii=False, indent=2)
            data = new_data

        subscribers = []
        for sub in data.get("subscribers", []):
            if isinstance(sub, dict) and sub.get("user_id"):
                subscribers.append(sub["user_id"])
            elif isinstance(sub, int):  # fallback, если формат вдруг сломан
                subscribers.append(sub)
        return subscribers
    except Exception as e:
        print(f"[ERROR] Ошибка чтения {SUBSCRIBERS_FILE}: {e}")
        return []

def get_yesterday_range():
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    return start, end

client = TelegramClient('anon_news', api_id, api_hash)
bot = Bot(token=telegram_bot_token)
client_ai = openai.OpenAI(api_key=openai_api_key)

async def update_channels():
    global channel_usernames
    channel_usernames = await get_channel_usernames_from_folder(FOLDER_NAME)
    print(f"[LOG] Обновлён список каналов: {channel_usernames}")

async def get_news():
    all_news = []
    start, end = get_yesterday_range()
    print(f"[DEBUG] Диапазон фильтра: {start} ... {end}")
    for channel in channel_usernames:
        async for message in client.iter_messages(channel):
            msg_date = message.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            msg_date_norm = msg_date.replace(microsecond=0)
            if msg_date_norm < start:
                break
            if start <= msg_date_norm < end:
                if message.text:
                    all_news.append(f"{message.text}\nИсточник: https://t.me/{channel}/{message.id}\n")
                    print(f"[DEBUG] {channel} | id={message.id} | дата={msg_date_norm} - добавлено")
    return all_news

def summarize_news(news_list):
    text = "\n\n".join(news_list)
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Сделай краткую сводку новостей за сутки по этим выдержкам, обязательно указывай источники."},
            {"role": "user", "content": text}
        ],
        max_tokens=1000,
        temperature=0.7
    )
    return response.choices[0].message.content

async def send_news(summary):
    subscribers = load_subscribers()
    if not subscribers:
        print("[WARN] Нет подписчиков для рассылки.")
        return

    active_subscribers = []
    for user_id in subscribers:
        try:
            result = await bot.send_message(chat_id=user_id, text=summary)
            print(f"[LOG] Сообщение успешно отправлено пользователю {user_id}, message_id={result.message_id}")
            active_subscribers.append(user_id)
        except Exception as e:
            print(f"[ERROR] Не удалось отправить сообщение пользователю {user_id}: {e}")

async def main():
    await client.start()
    await update_channels()
    news = await get_news()
    print(f"[LOG] Количество найденных новостей за вчера: {len(news)}")
    if not news:
        print("[LOG] Нет новостей за вчера. Прерываю рассылку.")
        return
    summary = summarize_news(news)
    await send_news(summary)

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
