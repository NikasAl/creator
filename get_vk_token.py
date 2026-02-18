#!/usr/bin/env python3
"""
Простой скрипт для получения токена VK с расширенными правами
"""

import os
import webbrowser
from dotenv import load_dotenv

def main():
    """Получение токена VK с расширенными правами"""
    
    # Загружаем конфигурацию
    load_dotenv("config.publisher.env")
    
    client_id = os.getenv('VK_CLIENT_ID', '54231185')
    
    print("🔧 Получение токена VK с расширенными правами")
    print("=" * 50)
    print(f"📱 Client ID: {client_id}")
    
    # Формируем URL для получения токена
    auth_url = (
        f"https://oauth.vk.com/authorize?"
        f"client_id={client_id}&"
        f"display=page&"
        f"redirect_uri=https://oauth.vk.com/blank.html&"
        f"scope=groups,video&"
        f"response_type=token&"
        f"v=5.131"
    )
    
    print("\n🌐 Открываем браузер для авторизации...")
    print(f"URL: {auth_url}")
    
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"⚠️  Не удалось открыть браузер: {e}")
    
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
    
    # Обновляем конфигурацию
    config_file = "config.publisher.env"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Обновляем токен
        for i, line in enumerate(lines):
            if line.startswith('VK_ACCESS_TOKEN='):
                lines[i] = f'VK_ACCESS_TOKEN={access_token}\n'
                break
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ Токен обновлен в {config_file}")
        
        # Тестируем токен
        print("\n🔍 Проверка токена...")
        from publishers.vk_publisher import VKPublisher
        
        publisher = VKPublisher(config_file)
        if publisher.authenticate():
            print("✅ Аутентификация успешна!")
            
            # Тестируем получение URL загрузки
            upload_url = publisher._get_video_upload_url()
            if upload_url:
                print("✅ URL загрузки видео получен")
            else:
                print("❌ Не удалось получить URL загрузки видео")
        else:
            print("❌ Ошибка аутентификации")
            return 1
            
    except Exception as e:
        print(f"❌ Ошибка обновления токена: {e}")
        return 1
    
    print("\n🎉 Токен успешно обновлен!")
    print("\n📝 Теперь можно использовать:")
    print("python publisher.py pipeline_LemEng_87_111 --platforms vk --dry-run")
    print("python publisher.py pipeline_LemEng_87_111 --platforms vk")
    
    return 0

if __name__ == "__main__":
    exit(main())
