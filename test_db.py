
#!/usr/bin/env python3
"""
Простой тест для проверки подключения и работы с PostgreSQL
"""

import os
from database import db

def test_database():
    print("🔍 Тестирование PostgreSQL подключения...")
    
    # 1. Проверяем переменные окружения
    database_url = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL найден: {bool(database_url)}")
    if database_url:
        print(f"DATABASE_URL длина: {len(database_url)} символов")
    
    # 2. Проверяем подключение
    try:
        conn = db._get_connection()
        print("✅ Подключение к PostgreSQL успешно")
        
        cursor = conn.cursor()
        
        # 3. Проверяем таблицы
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"📋 Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"   - {table[0]}")
        
        # 4. Проверяем таблицу users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Пользователей в таблице users: {user_count}")
        
        # 5. Тестируем добавление пользователя
        test_user_id = 999999999
        print(f"🧪 Тестируем добавление пользователя {test_user_id}...")
        
        success = db.add_user(
            test_user_id,
            "test_user",
            "Test", 
            "User",
            {"language_code": "ru", "is_premium": False}
        )
        
        print(f"Результат добавления: {success}")
        
        if success:
            # Проверяем что пользователь добавился
            user_info = db.get_user_info(test_user_id)
            print(f"Информация о тестовом пользователе: {user_info}")
            
            # Удаляем тестового пользователя
            cursor.execute("DELETE FROM users WHERE user_id = %s", (test_user_id,))
            conn.commit()
            print("✅ Тестовый пользователь удален")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database()
