#!/usr/bin/env python3
"""
Тестовый скрипт для проверки аутентификации YouTube
"""

import os
import sys
from pathlib import Path

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent))

from publishers.youtube_publisher import YouTubePublisher


def main():
    print("🧪 ТЕСТИРОВАНИЕ АУТЕНТИФИКАЦИИ YOUTUBE")
    print("=" * 50)
    
    try:
        # Создаем публикатор
        publisher = YouTubePublisher("config.publisher.env")
        
        print("🔑 Проверка аутентификации...")
        
        # Выполняем аутентификацию
        if publisher.authenticate():
            print("✅ Аутентификация успешна!")
            
            # Получаем информацию о канале
            channel_info = publisher.get_channel_info()
            if channel_info:
                print(f"📺 Канал: {channel_info.get('title', 'Неизвестно')}")
                print(f"👥 Подписчики: {channel_info.get('subscriber_count', '0')}")
                print(f"🎬 Видео: {channel_info.get('video_count', '0')}")
                print(f"👀 Просмотры: {channel_info.get('view_count', '0')}")
            
            # Получаем категории
            categories = publisher.get_video_categories()
            if categories:
                print(f"📂 Доступно категорий: {len(categories)}")
                print("Популярные категории:")
                for cat in categories[:5]:
                    print(f"  - {cat['title']} (ID: {cat['id']})")
            
            print("\n🎉 Система готова к работе!")
            return 0
        else:
            print("❌ Ошибка аутентификации")
            print("\nВозможные причины:")
            print("1. Токен истек - запустите setup_youtube_auth.py")
            print("2. Неправильные учетные данные")
            print("3. Недостаточно прав доступа")
            return 1
            
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
