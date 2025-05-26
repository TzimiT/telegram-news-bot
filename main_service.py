import asyncio
import logging
from datetime import datetime
import sys

# Импортируем функции из существующих модулей
from news_bot_part import run_continuous as news_service
from get_users import main as user_bot
from database import db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_service.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Главный сервис 24/7 который объединяет все боты"""
    logger.info("🚀 Запуск Main Service 24/7")
    logger.info("📊 Проверка PostgreSQL подключения...")

    # Проверяем базу данных
    try:
        stats = db.get_user_stats()
        logger.info(f"✅ PostgreSQL работает: {stats['active_users']} активных пользователей")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return

    # Создаем задачи для параллельного выполнения
    tasks = []

    # 1. Запускаем сервис новостей (работает по расписанию)
    logger.info("📰 Запуск News Aggregator Service...")
    news_task = asyncio.create_task(news_service())
    tasks.append(news_task)

    # 2. Запускаем пользовательский бот как асинхронную задачу
    logger.info("👥 Запуск User Collection Bot...")
    async def run_user_bot_async():
        try:
            import subprocess
            import sys
            
            # Запускаем пользовательский бот как отдельный процесс
            process = subprocess.Popen(
                [sys.executable, "get_users.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info("✅ User Collection Bot запущен как отдельный процесс")
            
            # Ожидаем завершения процесса (он будет работать бесконечно)
            await asyncio.create_task(asyncio.to_thread(process.wait))
        except Exception as e:
            logger.error(f"❌ Ошибка запуска User Bot: {e}")

    user_bot_task = asyncio.create_task(run_user_bot_async())
    tasks.append(user_bot_task)
    
    # Небольшая задержка для корректного запуска
    await asyncio.sleep(2)

    logger.info("✅ Все сервисы запущены и работают 24/7")
    logger.info("📋 Активные сервисы:")
    logger.info("   - 📰 News Aggregator (рассылка в 09:00 UTC)")
    logger.info("   - 👥 User Collection Bot (обработка команд)")
    logger.info("   - 🗄️ PostgreSQL Database")

    # Ожидаем завершения всех задач
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в Main Service: {e}")
    finally:
        logger.info("🛑 Main Service 24/7 остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Необработанная ошибка: {e}")