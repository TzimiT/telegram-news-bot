# news_bot_part.py

from telethon.sync import TelegramClient
from telegram import Bot
import openai
from config import api_id, api_hash, telegram_bot_token, openai_api_key, TARGET_CHAT_ID, FOLDER_NAME
from get_channels import get_channel_usernames_from_folder
from datetime import datetime, timedelta, timezone

def get_yesterday_range():
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    return start, end

async def debug_show_dates(channel):
    print(f"\n[DEBUG] Даты последних 10 сообщений в {channel}:")
    async for message in client.iter_messages(channel, limit=10):
        print(f"{message.id}: {message.date}  |  {message.text[:50]}")

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
        async for message in client.iter_messages(channel, limit=50):  # Убираем offset_date, reverse
            print(f"[DEBUG] {channel} | id={message.id} | дата={message.date}")
            if start <= message.date < end:
                if message.text:
                    all_news.append(f"{message.text}\nИсточник: https://t.me/{channel}/{message.id}\n")
            elif message.date < start:
                break
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
    try:
        result = await bot.send_message(chat_id=TARGET_CHAT_ID, text=summary)
        print(f"[LOG] Сообщение успешно отправлено в chat_id={TARGET_CHAT_ID}, message_id={result.message_id}")
    except Exception as e:
        print(f"[ERROR] Не удалось отправить сообщение: {e}")

async def main():
    await client.start()
    await debug_show_dates('swimcup')
    news = await get_news()
    print(f"[LOG] Собрано {len(news)} сообщений за вчера")
    if news:
        print(f"[LOG] Первый пост:\n{news[0][:200]}")
    else:
        print("[LOG] Нет постов за вчерашний день")
        print("[LOG] Нет новостей за вчера. Прерываю рассылку.")
        return
    summary = summarize_news(news)
    await send_news(summary)

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
