#!/usr/bin/env python3
"""
Тестовый скрипт для проверки VK аутентификации
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Основная функция тестирования VK аутентификации"""
    
    print("🔍 Тестирование VK аутентификации")
    print("=" * 50)
    
    # Загружаем конфигурацию
    config_file = "config.publisher.env"
    if Path(config_file).exists():
        load_dotenv(config_file)
        print(f"✅ Конфигурация загружена из {config_file}")
    else:
        print(f"⚠️  Файл конфигурации не найден: {config_file}")
    
    # Проверяем настройки
    client_id = os.getenv('VK_CLIENT_ID', '')
    client_secret = os.getenv('VK_CLIENT_SECRET', '')
    access_token = os.getenv('VK_ACCESS_TOKEN', '')
    group_id = os.getenv('VK_GROUP_ID', '')
    token_file = os.getenv('VK_TOKEN_PATH', 'vk_token.json')
    
    print(f"\n📋 Настройки:")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'НЕ ТРЕБУЕТСЯ (плагин-приложение)'}")
    print(f"Access Token: {'*' * len(access_token) if access_token else 'НЕ УСТАНОВЛЕН'}")
    print(f"Group ID: {group_id if group_id else 'НЕ УСТАНОВЛЕН'}")
    print(f"Token File: {token_file}")
    
    # Проверяем файл токена
    if Path(token_file).exists():
        try:
            with open(token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            print(f"✅ Файл токена найден: {token_file}")
            print(f"   Токен: {'*' * len(token_data.get('access_token', ''))}")
            print(f"   Группа: {token_data.get('group_id', 'НЕ УСТАНОВЛЕНА')}")
        except Exception as e:
            print(f"❌ Ошибка чтения файла токена: {e}")
    else:
        print(f"⚠️  Файл токена не найден: {token_file}")
    
    # Тестируем аутентификацию
    print(f"\n🔐 Тестирование аутентификации...")
    
    try:
        from publishers.vk_publisher import VKPublisher
        
        publisher = VKPublisher(config_file)
        
        if publisher.authenticate():
            print("✅ Аутентификация успешна!")
            
            # Получаем информацию о пользователе
            print(f"\n👤 Информация о пользователе:")
            try:
                import requests
                params = {
                    'access_token': publisher.access_token,
                    'v': publisher.API_VERSION
                }
                response = requests.get(f"{publisher.API_BASE_URL}/users.get", params=params)
                data = response.json()
                
                if 'response' in data and len(data['response']) > 0:
                    user = data['response'][0]
                    print(f"   Имя: {user['first_name']} {user['last_name']}")
                    print(f"   ID: {user['id']}")
                else:
                    print("   ❌ Не удалось получить информацию о пользователе")
            except Exception as e:
                print(f"   ❌ Ошибка получения информации о пользователе: {e}")
            
            # Получаем информацию о группе
            if publisher.group_id:
                print(f"\n👥 Информация о группе:")
                group_info = publisher.get_group_info()
                if group_info:
                    print(f"   Название: {group_info['name']}")
                    print(f"   ID: {group_info['id']}")
                    print(f"   Участников: {group_info['members_count']}")
                    print(f"   Описание: {group_info['description'][:100]}...")
                else:
                    print("   ❌ Не удалось получить информацию о группе")
            else:
                print(f"\n👥 Группа не указана")
            
            # Тестируем получение URL загрузки
            print(f"\n📤 Тестирование API...")
            try:
                upload_url = publisher._get_video_upload_url()
                if upload_url:
                    print("   ✅ URL загрузки видео получен")
                else:
                    print("   ❌ Не удалось получить URL загрузки видео")
            except Exception as e:
                print(f"   ❌ Ошибка получения URL загрузки: {e}")
            
            try:
                audio_upload_url = publisher._get_audio_upload_url()
                if audio_upload_url:
                    print("   ✅ URL загрузки аудио получен")
                else:
                    print("   ❌ Не удалось получить URL загрузки аудио")
            except Exception as e:
                print(f"   ❌ Ошибка получения URL загрузки аудио: {e}")
            
        else:
            print("❌ Ошибка аутентификации")
            return 1
            
    except ImportError as e:
        print(f"❌ Ошибка импорта VKPublisher: {e}")
        print("Убедитесь, что файл vk_publisher.py существует")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1
    
    print(f"\n🎉 Тестирование завершено успешно!")
    print(f"\n📝 Примеры использования:")
    print("python publisher.py pipeline_LemEng_87_111 --platforms vk --dry-run")
    print("python publisher.py pipeline_LemEng_87_111 --platforms vk")
    
    return 0

if __name__ == "__main__":
    exit(main())

