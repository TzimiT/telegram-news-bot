
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

DATABASE_FILE = "users.db"

class UserDatabase:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER,
                messages_received INTEGER DEFAULT 0,
                last_message_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица для рекомендаций каналов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                recommendation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Добавить пользователя в базу"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, added_at, is_active, last_interaction)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            ''', (user_id, username or "-", first_name or "-", last_name or "-", 
                  datetime.now(), datetime.now()))
            
            # Добавляем статистику для нового пользователя
            cursor.execute('''
                INSERT OR IGNORE INTO user_stats (user_id, messages_received, last_message_date)
                VALUES (?, 0, ?)
            ''', (user_id, datetime.now()))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления пользователя {user_id}: {e}")
            return False
        finally:
            conn.close()
    
    def remove_user(self, user_id: int):
        """Удалить пользователя (деактивировать)"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET is_active = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def get_active_users(self) -> List[int]:
        """Получить список активных пользователей"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE is_active = 1')
        users = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return users
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о пользователе"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, added_at, is_active, last_interaction
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'added_at': row[4],
                'is_active': row[5],
                'last_interaction': row[6]
            }
        
        conn.close()
        return None
    
    def update_user_interaction(self, user_id: int):
        """Обновить время последнего взаимодействия"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET last_interaction = ? WHERE user_id = ?
        ''', (datetime.now(), user_id))
        
        cursor.execute('''
            UPDATE user_stats SET messages_received = messages_received + 1, 
                   last_message_date = ? WHERE user_id = ?
        ''', (datetime.now(), user_id))
        
        conn.commit()
        conn.close()
    
    def add_channel_recommendation(self, user_id: int, recommendation: str):
        """Добавить рекомендацию канала"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO channel_recommendations (user_id, recommendation)
            VALUES (?, ?)
        ''', (user_id, recommendation))
        
        conn.commit()
        conn.close()
    
    def get_user_stats(self) -> Dict:
        """Получить общую статистику пользователей"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Общее количество пользователей
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        active_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_count = cursor.fetchone()[0]
        
        # Последние активные пользователи
        cursor.execute('''
            SELECT username, first_name, last_name, last_interaction 
            FROM users WHERE is_active = 1 
            ORDER BY last_interaction DESC LIMIT 5
        ''')
        recent_users = cursor.fetchall()
        
        conn.close()
        
        return {
            'active_users': active_count,
            'total_users': total_count,
            'recent_users': recent_users
        }
    
    def migrate_from_json(self):
        """Миграция данных из старых JSON файлов"""
        print("🔄 Начинаю миграцию из JSON файлов...")
        
        # Миграция из subscribers.json
        if os.path.exists("subscribers.json"):
            try:
                with open("subscribers.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    subscribers = data.get('subscribers', [])
                
                for sub in subscribers:
                    if isinstance(sub, dict):
                        self.add_user(
                            sub.get('user_id'),
                            sub.get('username'),
                            sub.get('first_name'),
                            sub.get('last_name')
                        )
                    elif isinstance(sub, int):
                        self.add_user(sub)
                
                print(f"✅ Мигрировано {len(subscribers)} пользователей из subscribers.json")
            except Exception as e:
                print(f"❌ Ошибка миграции subscribers.json: {e}")
        
        # Миграция из subscribers_old.json
        if os.path.exists("subscribers_old.json"):
            try:
                with open("subscribers_old.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    old_subscribers = data.get('subscribers', [])
                
                for user_id in old_subscribers:
                    if isinstance(user_id, int):
                        self.add_user(user_id)
                
                print(f"✅ Мигрировано {len(old_subscribers)} пользователей из subscribers_old.json")
            except Exception as e:
                print(f"❌ Ошибка миграции subscribers_old.json: {e}")
        
        print("✅ Миграция завершена")

# Глобальный экземпляр базы данных
db = UserDatabase()

if __name__ == "__main__":
    # Тестирование базы данных
    db.migrate_from_json()
    
    stats = db.get_user_stats()
    print(f"\n📊 Статистика:")
    print(f"   Активных пользователей: {stats['active_users']}")
    print(f"   Всего пользователей: {stats['total_users']}")
    
    if stats['recent_users']:
        print(f"\n👥 Последние активные пользователи:")
        for user in stats['recent_users']:
            username, first_name, last_name, last_interaction = user
            name = f"{first_name} {last_name}".strip()
            print(f"   @{username} ({name}) - {last_interaction}")
