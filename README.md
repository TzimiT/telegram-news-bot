
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
SUBSCRIBERS_FILE = "subscribers.json"   # Файл подписчиков
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
- `/start` - Подписаться на рассылку новостей
- `/stop` - Отписаться от рассылки
- `/recommend_channel` - Предложить новый канал для агрегации
- `/help` - Справка по командам
- `/stats` - Статистика бота

### Расписание рассылок:
- **Новости AI**: ежедневно в 09:00 UTC
- **Спортивные новости**: ежедневно в 10:00 UTC (только для @avdovin)

## 🗃️ База данных

### Основные таблицы:
- `users` - Информация о пользователях
- `user_stats` - Статистика активности
- `news_channels` - Каналы для агрегации
- `news_posts` - Собранные новости
- `news_digests` - Созданные дайджесты
- `channel_recommendations` - Рекомендации от пользователей

## 🔒 Безопасность данных

### Защищенные файлы (.gitignore):
- Файлы конфигурации (`config.py`)
- Базы данных (`.db`, `.dump`)
- Логи с пользовательскими данными (`.log`)
- Telegram сессии (`sessions/`)
- Экспорты данных (`.csv`, `.xlsx`)
- Резервные копии (`*.backup`, `*.bak`)

## 📈 Мониторинг и логирование

### Логи сохраняются в файлы:
- `main_service.log` - Основной сервис
- `users.log` - Пользовательские взаимодействия

### Статистика доступна через:
```bash
python -c "from database import db; print(db.get_user_stats())"
python show_recommendations.py stats
```

## 🛠️ Техническое обслуживание

### Просмотр рекомендаций:
```bash
python show_recommendations.py           # Все рекомендации
python show_recommendations.py recent    # Последние 10
python show_recommendations.py stats     # Статистика
```

### Очистка тестовых данных:
```bash
python cleanup_test_data.py
```

### Проверка Telegram папок:
```bash
python check_folders.py
```

## 🌐 Развертывание

Проект настроен для работы на Replit с автоматическим управлением зависимостями и 24/7 режимом работы.

### Переменные окружения:
- Все чувствительные данные должны быть в `config.py`
- Используйте Replit Secrets для хранения токенов
- PostgreSQL база данных настраивается автоматически

## 📝 Лицензия

Проект разработан для внутреннего использования. При использовании соблюдайте требования Telegram API и OpenAI API.

## 🤝 Поддержка

Для вопросов и предложений создавайте issues в репозитории или обращайтесь к разработчику.

---

**Версия**: 2.1.0  
**Последнее обновление**: 2025-05-26
