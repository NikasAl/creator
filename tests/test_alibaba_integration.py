#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции Alibaba Video Generator с существующим video_generator.py
"""

import sys
from pathlib import Path

# Добавляем путь к модулям проекта
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from video_processors.alibaba_video_generator import AlibabaVideoGenerator
from video_processors.video_generator import VideoGenerator


def test_integration(pipeline_dir: str, image_index: int = 1):
    """Тестирует интеграцию между генераторами"""
    
    pipeline_path = Path(pipeline_dir)
    
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ")
    print("=" * 50)
    
    # Проверяем наличие файлов
    print("📁 Проверка файлов пайплайна...")
    
    required_files = [
        pipeline_path / "song.txt",
        pipeline_path / "illustrations.json",
        pipeline_path / "images",
        pipeline_path / "audio.mp3"
    ]
    
    for file_path in required_files:
        if file_path.exists():
            print(f"✅ {file_path.name}")
        else:
            print(f"❌ {file_path.name} - НЕ НАЙДЕН")
            return False
    
    # Проверяем наличие изображения
    image_file = pipeline_path / "images" / f"illustration_{image_index:02d}.png"
    if image_file.exists():
        print(f"✅ Изображение {image_file.name}")
    else:
        print(f"❌ Изображение {image_file.name} - НЕ НАЙДЕНО")
        return False
    
    print("\n🔧 Проверка генераторов...")
    
    try:
        # Тестируем Alibaba Video Generator
        print("📹 Тестирование AlibabaVideoGenerator...")
        alibaba_gen = AlibabaVideoGenerator()
        print("✅ AlibabaVideoGenerator инициализирован")
        
        # Тестируем загрузку данных пайплайна
        song_text, illustrations, script = alibaba_gen.load_pipeline_data(pipeline_path)
        print(f"✅ Данные пайплайна загружены: {len(illustrations)} иллюстраций")
        
        # Тестируем генерацию промпта
        video_prompt = alibaba_gen.generate_video_prompt(image_index, song_text, illustrations, script)
        print(f"✅ Промпт сгенерирован: {video_prompt[:50]}...")
        
    except Exception as e:
        print(f"❌ Ошибка AlibabaVideoGenerator: {e}")
        return False
    
    try:
        # Тестируем VideoGenerator
        print("\n🎬 Тестирование VideoGenerator...")
        video_gen = VideoGenerator(pipeline_path)
        print("✅ VideoGenerator инициализирован")
        
        # Проверяем список изображений
        images = video_gen.get_images_list()
        print(f"✅ Найдено изображений: {len(images)}")
        
        # Проверяем готовые видео клипы
        video_clips = video_gen.get_video_clips_list()
        print(f"✅ Найдено готовых видео клипов: {len(video_clips)}")
        
        # Проверяем аудио
        audio_duration = video_gen.get_audio_duration()
        print(f"✅ Длительность аудио: {audio_duration:.2f} сек")
        
    except Exception as e:
        print(f"❌ Ошибка VideoGenerator: {e}")
        return False
    
    print("\n🎉 ИНТЕГРАЦИЯ УСПЕШНА!")
    print("=" * 50)
    print("📋 РЕКОМЕНДАЦИИ:")
    print("1. Убедитесь, что ALIBABA_API_KEY настроен в config.env")
    print("2. Используйте --image-index для генерации видео конкретного изображения")
    print("3. После генерации видео используйте video_generator.py для создания финального видео")
    print("4. Готовые видео клипы будут автоматически использованы в финальном видео")
    
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование интеграции генераторов видео")
    parser.add_argument("--pipeline-dir", required=True, help="Каталог пайплайна для тестирования")
    parser.add_argument("--image-index", type=int, default=1, help="Номер изображения для тестирования")
    
    args = parser.parse_args()
    
    success = test_integration(args.pipeline_dir, args.image_index)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
