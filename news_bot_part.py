# news_bot_part.py

from telethon.sync import TelegramClient
from telegram import Bot
import openai
from config import api_id, api_hash, telegram_bot_token, openai_api_key, FOLDER_NAME, SUBSCRIBERS_FILE
from get_channels import get_channel_usernames_from_folder
import asyncio
from datetime import datetime, timedelta, timezone

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        print("[WARN] Файл с подписчиками не найден, список пуст")
        return []

def save_subscriber(user_id):
    subscribers = set(load_subscribers())
    if user_id not in subscribers:
        subscribers.add(user_id)
        with open(SUBSCRIBERS_FILE, 'w') as f:
            for sub in subscribers:
                f.write(f"{sub}\n")
        print(f"[LOG] Добавлен новый подписчик: {user_id}")

async def update_subscribers():
    print("[LOG] Обновление подписчиков: ")

def get_yesterday_range():
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    return start, end

client = TelegramClient('anon_news', api_id, api_hash)
bot = Bot(token=telegram_bot_token)
client_ai = openai.OpenAI(api_key=openai_api_key)

async def get_news(channel_usernames):
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
        max_tokens=4096,
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

    with open(SUBSCRIBERS_FILE, 'w') as f:
        for user_id in active_subscribers:
            f.write(f"{user_id}\n")

async def main():
    await client.start()

    # 1) Обновляем подписчиков
    await update_subscribers()

    # 2) Обновляем список каналов из папки
    channel_usernames = await get_channel_usernames_from_folder(FOLDER_NAME)
    print(f"[LOG] Обновлён список каналов: {channel_usernames}")

    # 3) Собираем новости и рассылаем
    news = await get_news(channel_usernames)
    print(f"[LOG] Количество найденных новостей за вчера: {len(news)}")
    if not news:
        print("[LOG] Нет новостей за вчера. Прерываю рассылку.")
        return

    summary = summarize_news(news)
    await send_news(summary)

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
