#!/usr/bin/env python3
"""
Скрипт для настройки аутентификации VK
"""

import os
import json
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Основная функция настройки VK аутентификации"""
    
    # Загружаем конфигурацию
    config_file = "config.publisher.env"
    if Path(config_file).exists():
        load_dotenv(config_file)
    
    client_id = os.getenv('VK_CLIENT_ID', '52506614')
    client_secret = os.getenv('VK_CLIENT_SECRET', '')
    
    print("🔧 Настройка VK аутентификации")
    print("=" * 50)
    
    print(f"📱 Client ID: {client_id}")
    if client_secret:
        print(f"🔑 Client Secret: {'*' * len(client_secret)}")
    else:
        print("🔑 Client Secret: НЕ ТРЕБУЕТСЯ (плагин-приложение)")
    
    # Формируем URL для получения токена
    redirect_uri = "https://oauth.vk.com/blank.html"
    scope = "groups,video"  # Права доступа (только видео, аудио и публикация в группу недоступны для плагин-приложений)
    
    auth_url = (
        f"https://oauth.vk.com/authorize?"
        f"client_id={client_id}&"
        f"display=page&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scope}&"
        f"response_type=token&"
        f"v=5.131"
    )
    
    print("\n🌐 Открываем браузер для авторизации...")
    print(f"URL: {auth_url}")
    
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"⚠️  Не удалось открыть браузер: {e}")
        print("Откройте URL вручную:")
        print(auth_url)
    
    print("\n📋 Инструкции:")
    print("1. Войдите в свой аккаунт VK")
    print("2. Разрешите доступ приложению")
    print("3. Скопируйте токен из адресной строки браузера")
    print("4. Вставьте токен ниже")
    
    # Запрашиваем токен у пользователя
    access_token = input("\n🔑 Введите токен доступа: ").strip()
    
    if not access_token:
        print("❌ Токен не введен")
        return 1
    
    # Запрашиваем ID группы (опционально)
    group_id = input("\n👥 Введите ID группы для публикации (опционально): ").strip()
    
    # Сохраняем токен
    token_data = {
        'access_token': access_token,
        'group_id': group_id,
        'timestamp': os.path.getmtime(config_file) if Path(config_file).exists() else 0
    }
    
    token_file = os.getenv('VK_TOKEN_PATH', 'vk_token.json')
    
    try:
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Токен сохранен в {token_file}")
        
        # Проверяем токен
        print("\n🔍 Проверка токена...")
        from publishers.vk_publisher import VKPublisher
        
        publisher = VKPublisher(config_file)
        if publisher.authenticate():
            print("✅ Аутентификация успешна!")
            
            if group_id:
                group_info = publisher.get_group_info()
                if group_info:
                    print(f"📊 Группа: {group_info['name']} (ID: {group_info['id']})")
                    print(f"👥 Участников: {group_info['members_count']}")
        else:
            print("❌ Ошибка аутентификации")
            return 1
            
    except Exception as e:
        print(f"❌ Ошибка сохранения токена: {e}")
        return 1
    
    print("\n🎉 Настройка VK аутентификации завершена!")
    print("\n📝 Примеры использования:")
    print("python publisher.py pipeline_LemEng_87_111 --platforms vk")
    print("python publisher.py pipeline_LemEng_87_111 --platforms youtube vk")
    
    return 0

if __name__ == "__main__":
    exit(main())

