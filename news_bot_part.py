from telethon.sync import TelegramClient
from telegram import Bot
import openai
from config import api_id, api_hash, telegram_bot_token, openai_api_key, FOLDER_NAME
from get_channels import get_channel_usernames_from_folder
import asyncio
from datetime import datetime, timedelta, timezone

SUBSCRIBERS_FILE = 'subscribers.txt'

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        print("[WARN] Файл с подписчиками не найден, список пуст")
        return []

def get_yesterday_range():
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    return start, end

channel_usernames = get_channel_usernames_from_folder(FOLDER_NAME)
print("Каналы для агрегации:", channel_usernames)

client = TelegramClient('anon_news', api_id, api_hash)
bot = Bot(token=telegram_bot_token)
client_ai = openai.OpenAI(api_key=openai_api_key)

async def get_news():
    all_news = []
    start, end = get_yesterday_range()
    print(f"[DEBUG] Диапазон фильтра: {start} ... {end}")
    for channel in channel_usernames:
        async for message in client.iter_messages(channel):  # reverse=False по умолчанию — от новых к старым
            msg_date = message.date

            # Нормализуем дату к UTC (если нужно) и убираем микросекунды
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            msg_date_norm = msg_date.replace(microsecond=0)

            print(f"[TRACE] {channel} | id={message.id} | дата={msg_date_norm} | тип: {type(msg_date_norm)}")

            if msg_date_norm < start:
                # Дошли до старых сообщений — выходим из перебора для этого канала
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
            active_subscribers.append(user_id)  # Сохраняем, если всё ок
        except Exception as e:
            print(f"[ERROR] Не удалось отправить сообщение пользователю {user_id}: {e}")
            # Тут можно проверить конкретный тип ошибки, например telegram.error.BotBlocked

    # Обновляем файл только с активными подписчиками
    with open(SUBSCRIBERS_FILE, 'w') as f:
        for user_id in active_subscribers:
            f.write(f"{user_id}\n")

async def main():
    await client.start()
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
