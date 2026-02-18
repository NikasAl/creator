#!/usr/bin/env python3
"""
Тестовый скрипт для проверки загрузки превью
"""

import os
import sys
from pathlib import Path

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent))

from publishers.youtube_publisher import YouTubePublisher


def test_mimetype_detection():
    """Тестирует определение MIME-типов"""
    print("🔍 Тестирование определения MIME-типов...")
    
    publisher = YouTubePublisher()
    
    test_files = [
        "test.jpg",
        "test.png", 
        "test.gif",
        "test.webp",
        "test.bmp",
        "test.tiff",
        "test.unknown"
    ]
    
    for filename in test_files:
        mimetype = publisher._get_image_mimetype(filename)
        print(f"  {filename} -> {mimetype}")
    
    print("✅ Тестирование MIME-типов завершено")


def test_thumbnail_upload():
    """Тестирует загрузку превью для существующего видео"""
    print("\n🖼️  Тестирование загрузки превью...")
    
    # Получаем ID последнего загруженного видео
    video_id = input("Введите ID видео для тестирования (или нажмите Enter для пропуска): ").strip()
    
    if not video_id:
        print("⏭️  Пропускаем тест загрузки превью")
        return
    
    # Ищем доступные изображения
    pipeline_dirs = [d for d in Path('.').iterdir() if d.is_dir() and d.name.startswith('pipeline_')]
    
    if not pipeline_dirs:
        print("❌ Пайплайны не найдены")
        return
    
    # Берем первый пайплайн с изображениями
    thumbnail_path = None
    for pipeline_dir in pipeline_dirs:
        images_dir = pipeline_dir / "images"
        if images_dir.exists():
            image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
            if image_files:
                thumbnail_path = str(image_files[0])
                break
    
    if not thumbnail_path:
        print("❌ Изображения для превью не найдены")
        return
    
    print(f"📁 Используем изображение: {thumbnail_path}")
    
    try:
        publisher = YouTubePublisher("config.publisher.env")
        
        if not publisher.authenticate():
            print("❌ Ошибка аутентификации")
            return
        
        # Тестируем загрузку превью
        success = publisher._upload_thumbnail(video_id, thumbnail_path)
        
        if success:
            print("✅ Превью успешно загружено!")
        else:
            print("❌ Ошибка загрузки превью")
            
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")


def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ ЗАГРУЗКИ ПРЕВЬЮ")
    print("=" * 50)
    
    # Тестируем определение MIME-типов
    test_mimetype_detection()
    
    # Тестируем загрузку превью
    test_thumbnail_upload()
    
    print("\n✅ Тестирование завершено")


if __name__ == "__main__":
    main()
