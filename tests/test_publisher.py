#!/usr/bin/env python3
"""
Тестовый скрипт для системы публикации
"""

import sys
from pathlib import Path

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent))

from publishers.pipeline_analyzer import PipelineAnalyzer
from publishers.llm_metadata_generator import LLMMetadataGenerator


def test_pipeline_analyzer():
    """Тестирует анализатор пайплайна"""
    print("🔍 Тестирование PipelineAnalyzer...")
    
    # Ищем первый доступный пайплайн
    pipeline_dirs = [d for d in Path('.').iterdir() if d.is_dir() and d.name.startswith('pipeline_')]
    
    if not pipeline_dirs:
        print("❌ Пайплайны не найдены")
        return False
    
    pipeline_path = pipeline_dirs[0]
    print(f"📁 Тестируем пайплайн: {pipeline_path}")
    
    try:
        analyzer = PipelineAnalyzer(str(pipeline_path))
        metadata = analyzer.analyze()
        
        print("✅ Анализ успешен")
        print(analyzer.get_summary())
        
        # Тестируем генерацию метаданных
        title = analyzer.suggest_title()
        description = analyzer.suggest_description()
        tags = analyzer.suggest_tags()
        
        print(f"\n📝 Предлагаемые метаданные:")
        print(f"Название: {title}")
        print(f"Описание: {description[:100]}...")
        print(f"Теги: {', '.join(tags[:5])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False


def test_llm_generator():
    """Тестирует генератор метаданных"""
    print("\n🤖 Тестирование LLMMetadataGenerator...")
    
    try:
        generator = LLMMetadataGenerator("config.publisher.env")
        
        # Тестовый контент
        test_content = """
        Это тестовый контент для проверки генерации метаданных.
        В нем содержатся основные идеи и концепции для создания видео.
        """
        
        title = generator.generate_title(test_content, "Тестовая книга", "Тестовый автор")
        description = generator.generate_description(test_content, "Тестовая книга", "Тестовый автор")
        tags = generator.generate_tags(test_content, "Тестовая книга", "Тестовый автор")
        
        print("✅ Генерация успешна")
        print(f"Название: {title}")
        print(f"Описание: {description[:100]}...")
        print(f"Теги: {', '.join(tags[:5])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ ПУБЛИКАЦИИ")
    print("=" * 50)
    
    success = True
    
    # Тестируем анализатор пайплайна
    if not test_pipeline_analyzer():
        success = False
    
    # Тестируем генератор метаданных
    if not test_llm_generator():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("\nДля публикации используйте:")
        print("python publisher.py <pipeline_path> --platforms youtube --dry-run")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("Проверьте конфигурацию и зависимости")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
