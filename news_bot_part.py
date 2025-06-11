from telethon import TelegramClient
from telegram import Bot
import openai
from config import api_id, api_hash, telegram_bot_token, openai_api_key, FOLDER_NAME
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from get_channels import get_channels_fullinfo_from_folder, load_channels_from_json

SUBSCRIBERS_FILE = "subscribers.json"
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        print("[WARN] Файл с подписчиками не найден, список пуст")
        return []
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [item['user_id'] for item in data.get('subscribers',[])]
    except Exception as e:
        print(f"[ERROR] Ошибка чтения {SUBSCRIBERS_FILE}: {e}")
        return []

def get_yesterday_range():
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    return start, end

def summarize_news(news_list):
    text = "\n\n".join(news_list)
    client_ai = openai.OpenAI(api_key=openai_api_key)
    response = client_ai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Сделай краткую сводку новостей за сутки по этим выдержкам, обязательно указывай источники. Если несколько новостей про одно и то же - кластеризуй в один пункт. Подробнее освещай всё про AI."},
            {"role": "user", "content": text}
        ],
        max_tokens=3000,
        temperature=0.7
    )
    return response.choices[0].message.content

async def get_news(client, channels):
    all_news = []
    start, end = get_yesterday_range()
    print(f"[DEBUG] Диапазон фильтра: {start} ... {end}")
    for channel_info in channels:
        username = channel_info.get("username")
        if not username:
            continue
        async for message in client.iter_messages(username):
            msg_date = message.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            msg_date_norm = msg_date.replace(microsecond=0)
            if msg_date_norm < start:
                break
            if start <= msg_date_norm < end and message.text:
                all_news.append(f"{message.text}\nИсточник: https://t.me/{username}/{message.id}\n")
                print(f"[DEBUG] {username} | id={message.id} | дата={msg_date_norm} - добавлено")
    return all_news

def split_message(text, max_length=TELEGRAM_MAX_MESSAGE_LENGTH):
    """
    Разбивает текст на части не длиннее max_length символов.
    Разделяет по абзацам, чтобы не резать посреди предложения.
    Если абзац длиннее лимита — делит тупо на куски.
    """
    paragraphs = text.split('\n\n')
    messages = []
    current_message = ""
    for para in paragraphs:
        if len(current_message) + len(para) + 2 <= max_length:
            if current_message:
                current_message += "\n\n" + para
            else:
                current_message = para
        else:
            if current_message:
                messages.append(current_message)
            if len(para) <= max_length:
                current_message = para
            else:
                # если параграф длиннее лимита, делим его тупо на куски
                for i in range(0, len(para), max_length):
                    messages.append(para[i:i+max_length])
                current_message = ""
    if current_message:
        messages.append(current_message)
    return messages

async def send_news(summary):
    subscribers = load_subscribers()
    if not subscribers:
        print("[WARN] Нет подписчиков для рассылки.")
        return

    bot = Bot(token=telegram_bot_token)
    active_subscribers = []

    # Разбиваем summary на части не длиннее 4096 символов
    message_chunks = split_message(summary)

    for user_id in subscribers:
        try:
            for idx, chunk in enumerate(message_chunks):
                # Можно добавить нумерацию частей если сообщений больше одного
                if len(message_chunks) > 1:
                    part_text = f"Часть {idx+1}/{len(message_chunks)}\n\n{chunk}"
                else:
                    part_text = chunk
                result = await bot.send_message(chat_id=user_id, text=part_text)
                print(f"[LOG] Сообщение успешно отправлено пользователю {user_id}, message_id={result.message_id}")
                # Рекомендуется сделать небольшую паузу между отправками частей
                await asyncio.sleep(0.1)
            active_subscribers.append(user_id)
        except Exception as e:
            print(f"[ERROR] Не удалось отправить сообщение пользователю {user_id}: {e}")

    # Оставляем в файле только активных подписчиков
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        new_subs = [sub for sub in data.get('subscribers',[]) if sub['user_id'] in active_subscribers]
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"subscribers": new_subs}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Ошибка обновления активных подписчиков: {e}")

async def main():
    async with TelegramClient('anon_news', api_id, api_hash) as client:
        # Шаг 1: Получить и сохранить полную инфу о каналах из папки
        await get_channels_fullinfo_from_folder(client, FOLDER_NAME)
        # Шаг 2: Загрузить полную инфу о каналах для рассылки
        channels = load_channels_from_json()
        print(f"[LOG] Каналы для агрегации: {[ch.get('username','?') for ch in channels]}")

        # Шаг 3: Собрать новости
        news = await get_news(client, channels)
        print(f"[LOG] Количество найденных новостей за вчера: {len(news)}")
        if not news:
            print("[LOG] Нет новостей за вчера. Прерываю рассылку.")
            return

        # Шаг 4: Суммаризация и рассылка
        summary = summarize_news(news)
        await send_news(summary)

if __name__ == "__main__":
    asyncio.run(main())
