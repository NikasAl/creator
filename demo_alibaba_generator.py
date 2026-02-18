#!/usr/bin/env python3
"""
Пример использования Alibaba Video Generator
"""

from pathlib import Path
from video_processors.alibaba_video_generator import AlibabaVideoGenerator


def demo_usage():
    """Демонстрация использования генератора"""
    
    print("🎬 ДЕМОНСТРАЦИЯ ALIBABA VIDEO GENERATOR")
    print("=" * 50)
    
    # Путь к пайплайну
    pipeline_dir = Path("pipeline_ЗимнийВечер2")
    
    try:
        # Создаем генератор
        generator = AlibabaVideoGenerator()
        
        # Загружаем данные пайплайна
        song_text, illustrations, script = generator.load_pipeline_data(pipeline_dir)
        
        print(f"\n📚 ДАННЫЕ ПАЙПЛАЙНА:")
        print(f"   Текст стихов: {len(song_text)} символов")
        print(f"   Иллюстраций: {len(illustrations)}")
        print(f"   Скрипт: {len(script)} частей")
        
        # Показываем доступные иллюстрации
        print(f"\n🖼️  ДОСТУПНЫЕ ИЛЛЮСТРАЦИИ:")
        for i, ill in enumerate(illustrations[:5]):  # Показываем первые 5
            print(f"   {ill.get('index', i+1):2d}. {ill.get('title', 'Без названия')}")
        
        if len(illustrations) > 5:
            print(f"   ... и еще {len(illustrations) - 5} иллюстраций")
        
        # Пример генерации промпта для первой иллюстрации
        print(f"\n🎬 ПРИМЕР ГЕНЕРАЦИИ ПРОМПТА:")
        image_index = 1
        illustration = illustrations[0]
        
        print(f"   Иллюстрация: {illustration.get('title', '')}")
        print(f"   Описание: {illustration.get('summary', '')}")
        
        # Создаем примерный промпт
        example_prompt = f"Камера медленно приближается к изображению, показывая детали в атмосфере зимнего вечера"
        print(f"   Примерный промпт: {example_prompt}")
        
        print(f"\n💡 КАК ИСПОЛЬЗОВАТЬ:")
        print(f"   1. Получите API ключ Alibaba Cloud Model Studio")
        print(f"   2. Добавьте его в config.env: ALIBABA_API_KEY=your_key_here")
        print(f"   3. Запустите генерацию:")
        print(f"      python video_processors/alibaba_video_generator.py \\")
        print(f"        --pipeline-dir {pipeline_dir} \\")
        print(f"        --image-index {image_index}")
        
        print(f"\n🎯 РЕЗУЛЬТАТ:")
        print(f"   Видео будет сохранено как: {pipeline_dir}/images/video_{image_index:02d}.mp4")
        print(f"   Затем используйте video_generator.py для создания финального видео")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    demo_usage()
