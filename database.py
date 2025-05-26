
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import sqlite3

class PostgresDatabase:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("❌ DATABASE_URL не найден в переменных окружения")
        
        # Модификация URL для connection pooling
        self.pool_url = self.database_url.replace('.us-east-2', '-pooler.us-east-2')
        self.init_database()
    
    def _get_connection(self):
        """Получить подключение к PostgreSQL"""
        try:
            conn = psycopg2.connect(self.pool_url)
            return conn
        except Exception as e:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            # Fallback на обычный URL
            return psycopg2.connect(self.database_url)
    
    def init_database(self):
        """Инициализация PostgreSQL базы данных и создание таблиц"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    full_name VARCHAR(511),
                    language_code VARCHAR(10),
                    is_bot BOOLEAN DEFAULT false,
                    is_premium BOOLEAN DEFAULT false,
                    added_via_link BOOLEAN DEFAULT false,
                    can_join_groups BOOLEAN,
                    can_read_all_group_messages BOOLEAN,
                    supports_inline_queries BOOLEAN,
                    is_verified BOOLEAN DEFAULT false,
                    is_restricted BOOLEAN DEFAULT false,
                    is_scam BOOLEAN DEFAULT false,
                    is_fake BOOLEAN DEFAULT false,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT true,
                    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_data JSONB
                )
            ''')
            
            # Таблица для статистики пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    messages_received INTEGER DEFAULT 0,
                    last_message_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    commands_used JSONB DEFAULT '{}',
                    UNIQUE(user_id)
                )
            ''')
            
            # Таблица для рекомендаций каналов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channel_recommendations (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    recommendation TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'pending',
                    admin_notes TEXT
                )
            ''')
            
            # Таблица для каналов (источников новостей)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_channels (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT UNIQUE,
                    username VARCHAR(255),
                    title VARCHAR(500),
                    description TEXT,
                    participants_count INTEGER,
                    is_active BOOLEAN DEFAULT true,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP,
                    channel_data JSONB
                )
            ''')
            
            # Таблица для новостей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_posts (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT REFERENCES news_channels(channel_id),
                    message_id BIGINT,
                    content TEXT,
                    post_date TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    included_in_digest BOOLEAN DEFAULT false,
                    digest_date DATE,
                    UNIQUE(channel_id, message_id)
                )
            ''')
            
            # Таблица для дайджестов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_digests (
                    id SERIAL PRIMARY KEY,
                    digest_date DATE UNIQUE,
                    content TEXT,
                    summary TEXT,
                    posts_count INTEGER DEFAULT 0,
                    subscribers_sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP
                )
            ''')
            
            # Таблица для рассылок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS newsletter_sends (
                    id SERIAL PRIMARY KEY,
                    digest_id INTEGER REFERENCES news_digests(id),
                    user_id BIGINT REFERENCES users(user_id),
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivery_status VARCHAR(50) DEFAULT 'sent',
                    error_message TEXT
                )
            ''')
            
            # Индексы для оптимизации
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_last_interaction ON users(last_interaction)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_channel_recommendations_created ON channel_recommendations(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_posts_date ON news_posts(post_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_posts_digest ON news_posts(digest_date)')
            
            conn.commit()
            print("✅ PostgreSQL база данных инициализирована")
            
        except Exception as e:
            print(f"❌ Ошибка инициализации базы данных: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None, user_data: dict = None) -> bool:
        """Добавить пользователя в базу с расширенной информацией"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Извлекаем данные из user_data если переданы
            if user_data:
                language_code = user_data.get('language_code')
                is_bot = user_data.get('is_bot', False)
                is_premium = user_data.get('is_premium', False)
                added_via_link = user_data.get('added_via_link', False)
                can_join_groups = user_data.get('can_join_groups')
                can_read_all_group_messages = user_data.get('can_read_all_group_messages')
                supports_inline_queries = user_data.get('supports_inline_queries')
                is_verified = user_data.get('is_verified', False)
                is_restricted = user_data.get('is_restricted', False)
                is_scam = user_data.get('is_scam', False)
                is_fake = user_data.get('is_fake', False)
            else:
                language_code = None
                is_bot = False
                is_premium = False
                added_via_link = False
                can_join_groups = None
                can_read_all_group_messages = None
                supports_inline_queries = None
                is_verified = False
                is_restricted = False
                is_scam = False
                is_fake = False
            
            # Формируем полное имя
            full_name = f"{first_name or ''} {last_name or ''}".strip()
            
            cursor.execute('''
                INSERT INTO users (
                    user_id, username, first_name, last_name, full_name, 
                    language_code, is_bot, is_premium, added_via_link,
                    can_join_groups, can_read_all_group_messages, supports_inline_queries,
                    is_verified, is_restricted, is_scam, is_fake,
                    added_at, is_active, last_interaction, user_data
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    full_name = EXCLUDED.full_name,
                    language_code = EXCLUDED.language_code,
                    is_bot = EXCLUDED.is_bot,
                    is_premium = EXCLUDED.is_premium,
                    can_join_groups = EXCLUDED.can_join_groups,
                    can_read_all_group_messages = EXCLUDED.can_read_all_group_messages,
                    supports_inline_queries = EXCLUDED.supports_inline_queries,
                    is_verified = EXCLUDED.is_verified,
                    is_restricted = EXCLUDED.is_restricted,
                    is_scam = EXCLUDED.is_scam,
                    is_fake = EXCLUDED.is_fake,
                    is_active = true,
                    last_interaction = CURRENT_TIMESTAMP,
                    user_data = EXCLUDED.user_data
            ''', (
                user_id, username or "-", first_name or "-", last_name or "-", full_name,
                language_code, is_bot, is_premium, added_via_link,
                can_join_groups, can_read_all_group_messages, supports_inline_queries,
                is_verified, is_restricted, is_scam, is_fake,
                datetime.now(), True, datetime.now(), json.dumps(user_data) if user_data else None
            ))
            
            # Добавляем статистику для пользователя
            cursor.execute('''
                INSERT INTO user_stats (user_id, messages_received, last_message_date)
                VALUES (%s, 0, %s)
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id, datetime.now()))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления пользователя {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def remove_user(self, user_id: int):
        """Удалить пользователя (деактивировать)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('UPDATE users SET is_active = false WHERE user_id = %s', (user_id,))
            conn.commit()
        except Exception as e:
            print(f"❌ Ошибка удаления пользователя {user_id}: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def get_active_users(self) -> List[int]:
        """Получить список активных пользователей"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT user_id FROM users WHERE is_active = true')
            users = [row[0] for row in cursor.fetchall()]
            return users
        except Exception as e:
            print(f"❌ Ошибка получения активных пользователей: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Получить полную информацию о пользователе"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT user_id, username, first_name, last_name, full_name,
                       language_code, is_bot, is_premium, added_via_link,
                       can_join_groups, can_read_all_group_messages, supports_inline_queries,
                       is_verified, is_restricted, is_scam, is_fake,
                       added_at, is_active, last_interaction, user_data
                FROM users WHERE user_id = %s
            ''', (user_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"❌ Ошибка получения информации о пользователе {user_id}: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def update_user_interaction(self, user_id: int):
        """Обновить время последнего взаимодействия"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET last_interaction = %s WHERE user_id = %s
            ''', (datetime.now(), user_id))
            
            cursor.execute('''
                UPDATE user_stats SET 
                    messages_received = messages_received + 1, 
                    last_message_date = %s 
                WHERE user_id = %s
            ''', (datetime.now(), user_id))
            
            conn.commit()
        except Exception as e:
            print(f"❌ Ошибка обновления взаимодействия пользователя {user_id}: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def add_channel_recommendation(self, user_id: int, recommendation: str):
        """Добавить рекомендацию канала"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO channel_recommendations (user_id, recommendation)
                VALUES (%s, %s)
            ''', (user_id, recommendation))
            
            conn.commit()
        except Exception as e:
            print(f"❌ Ошибка добавления рекомендации: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def get_channel_recommendations(self) -> List[Dict]:
        """Получить все рекомендации каналов"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT cr.id, cr.user_id, cr.recommendation, cr.created_at, cr.status, cr.admin_notes,
                       u.username, u.first_name, u.last_name
                FROM channel_recommendations cr
                LEFT JOIN users u ON cr.user_id = u.user_id
                ORDER BY cr.created_at DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ Ошибка получения рекомендаций: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def add_news_channel(self, channel_data: Dict):
        """Добавить канал для агрегации новостей"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO news_channels 
                (channel_id, username, title, description, participants_count, channel_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (channel_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    participants_count = EXCLUDED.participants_count,
                    channel_data = EXCLUDED.channel_data,
                    last_checked = CURRENT_TIMESTAMP
            ''', (
                channel_data.get('id'),
                channel_data.get('username'),
                channel_data.get('title'),
                channel_data.get('description'),
                channel_data.get('participants_count'),
                json.dumps(channel_data)
            ))
            
            conn.commit()
        except Exception as e:
            print(f"❌ Ошибка добавления канала: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def get_user_stats(self) -> Dict:
        """Получить общую статистику пользователей"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_active = true')
            active_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM users')
            total_count = cursor.fetchone()['count']
            
            # Последние активные пользователи
            cursor.execute('''
                SELECT username, first_name, last_name, last_interaction 
                FROM users WHERE is_active = true 
                ORDER BY last_interaction DESC LIMIT 5
            ''')
            recent_users = cursor.fetchall()
            
            return {
                'active_users': active_count,
                'total_users': total_count,
                'recent_users': recent_users
            }
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {'active_users': 0, 'total_users': 0, 'recent_users': []}
        finally:
            cursor.close()
            conn.close()
    
    def migrate_from_sqlite(self):
        """Миграция данных из SQLite в PostgreSQL"""
        print("🔄 Начинаю миграцию из SQLite в PostgreSQL...")
        
        sqlite_db = "users.db"
        if not os.path.exists(sqlite_db):
            print("❌ SQLite база данных не найдена")
            return
        
        try:
            # Подключение к SQLite
            sqlite_conn = sqlite3.connect(sqlite_db)
            sqlite_conn.row_factory = sqlite3.Row
            sqlite_cursor = sqlite_conn.cursor()
            
            # Миграция пользователей
            sqlite_cursor.execute('SELECT * FROM users')
            users = sqlite_cursor.fetchall()
            
            for user in users:
                self.add_user(
                    user['user_id'],
                    user['username'],
                    user['first_name'],
                    user['last_name']
                )
            
            print(f"✅ Мигрировано {len(users)} пользователей")
            
            # Миграция рекомендаций
            sqlite_cursor.execute('SELECT * FROM channel_recommendations')
            recommendations = sqlite_cursor.fetchall()
            
            for rec in recommendations:
                self.add_channel_recommendation(rec['user_id'], rec['recommendation'])
            
            print(f"✅ Мигрировано {len(recommendations)} рекомендаций")
            
            sqlite_conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка миграции из SQLite: {e}")
    
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
        
        # Миграция каналов из channels.json
        if os.path.exists("channels.json"):
            try:
                with open("channels.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    channels = data.get('channels', [])
                
                for channel in channels:
                    self.add_news_channel(channel)
                
                print(f"✅ Мигрировано {len(channels)} каналов из channels.json")
            except Exception as e:
                print(f"❌ Ошибка миграции channels.json: {e}")

# Глобальный экземпляр базы данных
db = PostgresDatabase()

if __name__ == "__main__":
    # Миграция данных
    db.migrate_from_sqlite()
    db.migrate_from_json()
    
    stats = db.get_user_stats()
    print(f"\n📊 Статистика PostgreSQL:")
    print(f"   Активных пользователей: {stats['active_users']}")
    print(f"   Всего пользователей: {stats['total_users']}")
    
    if stats['recent_users']:
        print(f"\n👥 Последние активные пользователи:")
        for user in stats['recent_users']:
            username = user['username']
            first_name = user['first_name']
            last_name = user['last_name']
            last_interaction = user['last_interaction']
            name = f"{first_name} {last_name}".strip()
            print(f"   @{username} ({name}) - {last_interaction}")
