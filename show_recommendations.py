
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import db
from datetime import datetime
import sys

def show_recommendations():
    """Показать все рекомендации каналов от пользователей"""
    print("📢 Рекомендации каналов от пользователей\n")
    print("=" * 80)
    
    try:
        recommendations = db.get_channel_recommendations()
        
        if not recommendations:
            print("❌ Рекомендаций пока нет")
            return
        
        print(f"📊 Всего рекомендаций: {len(recommendations)}\n")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"🔹 Рекомендация #{i}")
            print(f"   📅 Дата: {rec['created_at']}")
            print(f"   👤 Пользователь: @{rec['username']} ({rec['first_name']} {rec['last_name']})")
            print(f"   🆔 User ID: {rec['user_id']}")
            print(f"   📝 Рекомендация: {rec['recommendation']}")
            print(f"   📊 Статус: {rec['status']}")
            
            if rec['admin_notes']:
                print(f"   📝 Заметки админа: {rec['admin_notes']}")
            
            print("-" * 60)
        
    except Exception as e:
        print(f"❌ Ошибка получения рекомендаций: {e}")

def show_recent_recommendations(limit=5):
    """Показать последние рекомендации"""
    print(f"📢 Последние {limit} рекомендаций каналов\n")
    print("=" * 60)
    
    try:
        recommendations = db.get_channel_recommendations()
        
        if not recommendations:
            print("❌ Рекомендаций пока нет")
            return
        
        recent = recommendations[:limit]
        
        for i, rec in enumerate(recent, 1):
            print(f"🔸 #{i} от @{rec['username']}")
            print(f"   📅 {rec['created_at']}")
            print(f"   📝 {rec['recommendation']}")
            print()
        
    except Exception as e:
        print(f"❌ Ошибка получения рекомендаций: {e}")

def show_statistics():
    """Показать статистику рекомендаций"""
    print("📊 Статистика рекомендаций\n")
    print("=" * 40)
    
    try:
        recommendations = db.get_channel_recommendations()
        
        if not recommendations:
            print("❌ Рекомендаций пока нет")
            return
        
        total = len(recommendations)
        pending = len([r for r in recommendations if r['status'] == 'pending'])
        approved = len([r for r in recommendations if r['status'] == 'approved'])
        rejected = len([r for r in recommendations if r['status'] == 'rejected'])
        
        print(f"📈 Всего рекомендаций: {total}")
        print(f"⏳ Ожидают рассмотрения: {pending}")
        print(f"✅ Одобрены: {approved}")
        print(f"❌ Отклонены: {rejected}")
        
        # Топ пользователей по количеству рекомендаций
        user_counts = {}
        for rec in recommendations:
            username = rec['username'] or 'Неизвестно'
            user_counts[username] = user_counts.get(username, 0) + 1
        
        if user_counts:
            print(f"\n👥 Топ пользователей по рекомендациям:")
            sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
            for username, count in sorted_users[:5]:
                print(f"   @{username}: {count}")
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "recent":
                limit = 10 if len(sys.argv) < 3 else int(sys.argv[2])
                show_recent_recommendations(limit)
            elif command == "stats":
                show_statistics()
            elif command == "help":
                print("📋 Использование:")
                print("  python show_recommendations.py           - все рекомендации")
                print("  python show_recommendations.py recent    - последние 10")
                print("  python show_recommendations.py recent 5  - последние 5")
                print("  python show_recommendations.py stats     - статистика")
            else:
                print("❌ Неизвестная команда. Используйте 'help' для справки")
        else:
            show_recommendations()
        
        # Пауза для чтения результатов
        print("\n" + "="*60)
        print("💡 Нажмите Enter для завершения или Ctrl+C для выхода...")
        input()
        
    except KeyboardInterrupt:
        print("\n👋 Выход из программы")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Нажмите Enter для завершения...")
        input()
