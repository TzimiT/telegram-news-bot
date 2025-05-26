
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import db
import psycopg2
from psycopg2.extras import RealDictCursor

def cleanup_test_recommendations():
    """Удалить тестовые рекомендации каналов"""
    print("🧹 Очистка тестовых рекомендаций каналов...")
    
    try:
        conn = db._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем все рекомендации для анализа
        cursor.execute('''
            SELECT cr.id, cr.user_id, cr.recommendation, cr.created_at, cr.status,
                   u.username, u.first_name, u.last_name
            FROM channel_recommendations cr
            LEFT JOIN users u ON cr.user_id = u.user_id
            ORDER BY cr.created_at DESC
        ''')
        
        recommendations = cursor.fetchall()
        
        if not recommendations:
            print("❌ Рекомендаций не найдено")
            return
        
        print(f"📊 Найдено рекомендаций: {len(recommendations)}")
        print("\n📋 Список рекомендаций:")
        
        test_recommendations = []
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. ID: {rec['id']} | @{rec['username']} | {rec['recommendation'][:50]}...")
            
            # Определяем тестовые рекомендации по критериям:
            # - пользователь с тестовым ID (999999999)
            # - рекомендации содержащие "test", "тест", или от неизвестных пользователей
            username = rec['username'] or ''
            recommendation = rec['recommendation'].lower()
            
            if (rec['user_id'] == 999999999 or 
                'test' in username.lower() or 
                'test' in recommendation or 
                'тест' in recommendation or
                not rec['username']):
                test_recommendations.append(rec['id'])
                print(f"   ➤ ТЕСТОВАЯ (будет удалена)")
        
        if not test_recommendations:
            print("✅ Тестовых рекомендаций не найдено")
            return
        
        print(f"\n🗑️ Найдено {len(test_recommendations)} тестовых рекомендаций для удаления")
        
        # Удаляем тестовые рекомендации
        cursor.execute('''
            DELETE FROM channel_recommendations 
            WHERE id = ANY(%s)
        ''', (test_recommendations,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ Удалено {deleted_count} тестовых рекомендаций")
        
        # Показываем оставшиеся рекомендации
        cursor.execute('SELECT COUNT(*) as count FROM channel_recommendations')
        remaining = cursor.fetchone()['count']
        print(f"📊 Осталось рекомендаций: {remaining}")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def cleanup_test_users():
    """Удалить тестовых пользователей"""
    print("\n🧹 Очистка тестовых пользователей...")
    
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # Сначала удаляем связанные записи в user_stats
        cursor.execute('DELETE FROM user_stats WHERE user_id = %s', (999999999,))
        deleted_stats = cursor.rowcount
        
        # Затем удаляем пользователя
        cursor.execute('DELETE FROM users WHERE user_id = %s', (999999999,))
        deleted_users = cursor.rowcount
        
        conn.commit()
        
        if deleted_users > 0:
            print(f"✅ Удален тестовый пользователь (ID: 999999999)")
            print(f"✅ Удалена статистика пользователя")
        else:
            print("ℹ️ Тестовых пользователей не найдено")
        
    except Exception as e:
        print(f"❌ Ошибка при удалении тестовых пользователей: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    try:
        cleanup_test_recommendations()
        cleanup_test_users()
        
        print("\n" + "="*50)
        print("✨ Очистка завершена!")
        print("💡 Проверьте результат командой: python show_recommendations.py")
        
    except KeyboardInterrupt:
        print("\n👋 Очистка прервана пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
