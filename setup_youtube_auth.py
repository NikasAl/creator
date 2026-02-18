#!/usr/bin/env python3
"""
Скрипт для настройки аутентификации YouTube
"""

import os
import sys
from pathlib import Path

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent))

from publishers.youtube_publisher import YouTubePublisher


def main():
    print("🔐 НАСТРОЙКА АУТЕНТИФИКАЦИИ YOUTUBE")
    print("=" * 50)
    
    # Проверяем наличие файла учетных данных
    credentials_file = "youtube_credentials.json"
    if not Path(credentials_file).exists():
        print(f"❌ Файл {credentials_file} не найден")
        print("Создайте файл youtube_credentials.json с данными из Google Cloud Console")
        return 1
    
    try:
        # Создаем публикатор
        publisher = YouTubePublisher("config.publisher.env")
        
        print("🔑 Запуск аутентификации...")
        print("Откроется браузер для авторизации")
        print("После авторизации токен будет сохранен автоматически")
        
        # Выполняем аутентификацию
        if publisher.authenticate():
            print("✅ Аутентификация успешна!")
            print("Теперь вы можете использовать систему публикации")
            return 0
        else:
            print("❌ Ошибка аутентификации")
            return 1
            
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
