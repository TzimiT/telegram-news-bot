# 🤖 Telegram News Aggregator Bot

Многофункциональный бот для агрегации новостей из Telegram каналов с автоматической рассылкой подписчикам и сбором обратной связи.

## 🚀 Основные возможности

### 📰 Агрегация новостей
- Автоматический сбор новостей из настроенных Telegram каналов
- Ежедневная рассылка дайджеста в 09:00 UTC
- Обработка новостей с помощью OpenAI GPT для создания краткого содержания
- Отдельный сервис спортивных новостей для пользователя @avdovin (10:00 UTC)

### 👥 Управление подписчиками
- Автоматическая подписка пользователей через бота
- Хранение информации о пользователях в PostgreSQL
- Статистика активности и взаимодействий
- Система рекомендаций каналов от пользователей

### 🗄️ База данных
- PostgreSQL для надежного хранения данных
- Таблицы пользователей, новостей, дайджестов и рекомендаций
- Статистика рассылок и взаимодействий

## 📋 Структура проекта

```
telegram-news-bot/
├── main_service.py          # Главный сервис 24/7
├── news_bot_part.py         # Агрегация и рассылка новостей
├── sport_news_bot.py        # Спортивные новости для @avdovin
├── get_users.py             # Пользовательский бот
├── database.py              # Работа с PostgreSQL
├── session_manager.py       # Управление Telegram сессиями
├── setup_sport_channels.py  # Настройка спортивных каналов
├── show_recommendations.py  # Просмотр рекомендаций каналов
├── config_example.py        # Пример конфигурации
└── sessions/               # Папка для Telegram сессий
```

## ⚙️ Настройка и запуск

### 1. Конфигурация
Создайте файл `config.py` на основе `config_example.py`:

```python
api_id = YOUR_API_ID                    # Telegram API ID
api_hash = "YOUR_API_HASH"              # Telegram API Hash
openai_api_key = "sk-proj-YOUR_KEY"     # OpenAI API ключ
telegram_bot_token = "YOUR_BOT_TOKEN"   # Токен Telegram бота
FOLDER_NAME = "GPT"                     # Папка с каналами в Telegram
TARGET_CHAT_ID = "YOUR_CHAT_ID"         # ID канала для рассылки
```

### 2. Установка зависимостей
```bash
pip install telethon openai python-telegram-bot psycopg2-binary schedule
```

### 3. Первоначальная настройка
```bash
# Настройка Telegram сессии
python session_manager.py

# Настройка спортивных каналов (опционально)
python setup_sport_channels.py
```

### 4. Запуск основного сервиса
```bash
python main_service.py
```

## 🔧 Рабочие процессы (Workflows)

### Основные команды:
- **Main Service 24/7** - Запуск всех сервисов
- **Setup Session** - Настройка Telegram сессии
- **User Bot Active** - Запуск только пользовательского бота
- **Manual News Send** - Ручная отправка новостей
- **Test News Send** - Тестовая отправка
- **View Recommendations** - Просмотр рекомендаций каналов

### Команды разработки:
- **Development Mode** - Режим разработки
- **Dev Database Check** - Проверка базы данных
- **Manual Sport News Send** - Ручная отправка спортивных новостей

## 📊 Команды пользовательского бота

### Для подписчиков:
- `/start` - Подписаться на рассылку
- `/stop` - Отписаться от рассылки
- `/status` - Проверить статус подписки
- `/next` - Узнать время следующей рассылки
- `/recommend` - Рекомендовать канал для добавления

### Для администраторов:
- `/admin_stats` - Статистика пользователей
- `/admin_send` - Ручная отправка сообщения всем подписчикам

## 🛠️ Технические детали

### Используемые технологии:
- **Python 3.11+** - Основной язык программирования
- **Telethon** - Для работы с Telegram API
- **python-telegram-bot** - Для создания пользовательского бота
- **OpenAI API** - Для обработки и суммаризации новостей
- **PostgreSQL** - База данных
- **Schedule** - Планировщик задач

### Основные модули:
- `main_service.py` - Координатор всех сервисов
- `news_bot_part.py` - Агрегация новостей из основных каналов
- `sport_news_bot.py` - Агрегация спортивных новостей
- `get_users.py` - Telegram бот для взаимодействия с пользователями
- `database.py` - Работа с PostgreSQL базой данных
- `session_manager.py` - Управление авторизацией в Telegram

## 🔐 Безопасность

Проект настроен с учетом безопасности:
- Исключение конфиденциальных файлов через `.gitignore`
- Использование переменных окружения для чувствительных данных
- Защита от утечки сессий и пользовательских данных

## 📈 Мониторинг

- Логирование всех операций
- Статистика пользователей и рассылок
- Система рекомендаций каналов
- Автоматическое восстановление при ошибках

## 🚀 Развертывание

Проект готов к запуску на Replit с автоматическим управлением зависимостями и встроенной PostgreSQL базой данных.
```telegram-news-bot/
├── main_service.py          # Главный сервис 24/7
├── news_bot_part.py         # Агрегация и рассылка новостей
├── sport_news_bot.py        # Спортивные новости для @avdovin
├── get_users.py             # Пользовательский бот
├── database.py              # Работа с PostgreSQL
├── session_manager.py       # Управление Telegram сессиями
├── setup_sport_channels.py  # Настройка спортивных каналов
├── show_recommendations.py  # Просмотр рекомендаций каналов
├── config_example.py        # Пример конфигурации
└── sessions/               # Папка для Telegram сессий
```

## ⚙️ Настройка и запуск

### 1. Конфигурация
Создайте файл `config.py` на основе `config_example.py`:

```python
api_id = YOUR_API_ID                    # Telegram API ID
api_hash = "YOUR_API_HASH"              # Telegram API Hash
openai_api_key = "sk-proj-YOUR_KEY"     # OpenAI API ключ
telegram_bot_token = "YOUR_BOT_TOKEN"   # Токен Telegram бота
FOLDER_NAME = "GPT"                     # Папка с каналами в Telegram
TARGET_CHAT_ID = "YOUR_CHAT_ID"         # ID канала для рассылки
```

### 2. Установка зависимостей
```bash
pip install telethon openai python-telegram-bot psycopg2-binary schedule
```

### 3. Первоначальная настройка
```bash
# Настройка Telegram сессии
python session_manager.py

# Настройка спортивных каналов (опционально)
python setup_sport_channels.py
```

### 4. Запуск основного сервиса
```bash
python main_service.py