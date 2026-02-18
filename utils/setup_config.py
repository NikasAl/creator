#!/usr/bin/env python3
"""
Интерактивный скрипт для настройки конфигурации
Создает .env файл с настройками для обработки текста
"""

import os
from pathlib import Path


def get_user_input(prompt: str, default: str = "") -> str:
    """Получает ввод от пользователя"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()


def create_config_file():
    """Создает конфигурационный файл .env"""
    
    print("🔧 НАСТРОЙКА КОНФИГУРАЦИИ ДЛЯ ОБРАБОТКИ ТЕКСТА")
    print("=" * 50)
    print()
    
    # Получаем API ключ
    print("📋 Шаг 1: Настройка API")
    print("-" * 30)
    api_key = get_user_input("Введите ваш API ключ OpenRouter")
    
    if not api_key:
        print("❌ API ключ обязателен!")
        return False
    
    # Выбираем модель
    print("\n🤖 Шаг 2: Выбор модели")
    print("-" * 30)
    print("Доступные модели:")
    print("1. anthropic/claude-3.5-sonnet (рекомендуется, лучшее качество)")
    print("2. openai/gpt-4o (альтернатива)")
    print("3. meta-llama/llama-3.1-8b-instruct (бюджетный вариант)")
    
    model_choice = get_user_input("Выберите модель (1-3)", "1")
    
    models = {
        "1": "anthropic/claude-3.5-sonnet",
        "2": "openai/gpt-4o", 
        "3": "meta-llama/llama-3.1-8b-instruct"
    }
    
    default_model = models.get(model_choice, "anthropic/claude-3.5-sonnet")
    
    # Настройки обработки
    print("\n⚙️ Шаг 3: Настройки обработки")
    print("-" * 30)
    
    chunk_size = get_user_input("Размер части текста (символов)", "2500")
    temperature = get_user_input("Температура (0.0-1.0, 0.2 для консистентности)", "0.2")
    max_tokens = get_user_input("Максимум токенов на ответ", "4000")
    
    # Создаем содержимое .env файла
    env_content = f"""# OpenRouter API Configuration
OPENROUTER_API_KEY={api_key}

# Model Configuration
DEFAULT_MODEL={default_model}

# Processing Configuration
DEFAULT_CHUNK_SIZE={chunk_size}
DEFAULT_TEMPERATURE={temperature}
DEFAULT_MAX_TOKENS={max_tokens}

# Alternative models for different use cases
BUDGET_MODEL=meta-llama/llama-3.1-8b-instruct
QUALITY_MODEL=openai/gpt-4o
"""
    
    # Сохраняем файл
    env_file = Path(".env")
    
    if env_file.exists():
        overwrite = get_user_input("Файл .env уже существует. Перезаписать? (y/N)", "N")
        if overwrite.lower() != 'y':
            print("❌ Настройка отменена")
            return False
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"\n✅ Конфигурация сохранена в файл: {env_file}")
    print("\n📋 Созданные настройки:")
    print(f"   API ключ: {'*' * (len(api_key) - 4) + api_key[-4:]}")
    print(f"   Модель: {default_model}")
    print(f"   Размер части: {chunk_size}")
    print(f"   Температура: {temperature}")
    print(f"   Максимум токенов: {max_tokens}")
    
    return True


def main():
    print("🎯 Настройка конфигурации для обработки текста")
    print("Этот скрипт создаст файл .env с вашими настройками")
    print()
    
    # Проверяем, есть ли уже .env файл
    if Path(".env").exists():
        print("⚠️  Файл .env уже существует")
        choice = get_user_input("Показать текущие настройки? (y/N)", "N")
        
        if choice.lower() == 'y':
            with open(".env", 'r', encoding='utf-8') as f:
                content = f.read()
                print("\nТекущие настройки:")
                print("-" * 30)
                print(content)
                print("-" * 30)
        
        recreate = get_user_input("Создать новые настройки? (y/N)", "N")
        if recreate.lower() != 'y':
            print("Настройка отменена")
            return 0
    
    # Создаем конфигурацию
    if create_config_file():
        print("\n🎉 Настройка завершена!")
        print("\nТеперь вы можете использовать скрипты:")
        print("  python smart_text_processor.py input.txt -o output.txt")
        print("  python demo_processor.py")
        print("  python full_pipeline.py your_file.pdf")
    else:
        print("\n❌ Настройка не завершена")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 