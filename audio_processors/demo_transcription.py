#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования транскрибации
"""

import sys
import os
from pathlib import Path

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent.parent))

from audio_processors.audio_transcriber import AudioTranscriber


def demo_transcription():
    """Демонстрация транскрибации"""
    print("🎤 ДЕМОНСТРАЦИЯ ТРАНСКРИБАЦИИ")
    print("=" * 50)
    
    # Создаем тестовый текст
    test_text = """Фрагмент 1

Введение в психоанализ и шизоидные явления

Эта книга Гарри Гантрипа посвящена изучению шизоидных явлений и их связи с психоанализом. Автор исследует, как проблемы, возникающие в раннем детстве, влияют на формирование личности и создают трудности в психотерапии.

Фрагмент 2

Психоанализ: от Фрейда к целостному пониманию личности

Психоанализ, начавшийся с идей Зигмунда Фрейда, долгое время фокусировался на изучении влечений и механизмов психики. Однако со временем стало ясно, что для понимания человека важно рассматривать его как целостную личность.
"""
    
    # Сохраняем тестовый текст
    test_text_file = "demo_text.txt"
    with open(test_text_file, 'w', encoding='utf-8') as f:
        f.write(test_text)
    
    print(f"📝 Создан тестовый текст: {test_text_file}")
    
    # Создаем фиктивный аудио файл
    test_audio = "demo_audio.mp3"
    with open(test_audio, 'wb') as f:
        # Создаем минимальный MP3 файл (заголовок)
        f.write(b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    
    print(f"🎵 Создан тестовый аудио файл: {test_audio}")
    
    # Создаем транскрайбер
    transcriber = AudioTranscriber()
    
    print(f"\n🔧 Настройки транскрайбера:")
    print(f"   - OpenRouter API: {'✅' if transcriber.openrouter_api_key else '❌'}")
    print(f"   - Whisper API: {'✅' if transcriber.whisper_api_key else '❌'}")
    print(f"   - AssemblyAI: {'✅' if transcriber.assemblyai_key else '❌'}")
    
    # Пробуем транскрибацию
    print(f"\n🔄 Пробуем транскрибацию...")
    
    try:
        # Пробуем OpenRouter
        if transcriber.openrouter_api_key:
            print("🎤 Тестируем OpenRouter транскрибацию...")
            result = transcriber.transcribe_with_openrouter(test_audio)
            if result:
                print("✅ OpenRouter транскрибация работает!")
            else:
                print("❌ OpenRouter транскрибация не работает")
        
        # Пробуем Whisper API
        if transcriber.whisper_api_key:
            print("🎤 Тестируем Whisper API транскрибацию...")
            result = transcriber.transcribe_with_whisper_api(test_audio)
            if result:
                print("✅ Whisper API транскрибация работает!")
            else:
                print("❌ Whisper API транскрибация не работает")
        
        # Пробуем AssemblyAI
        if transcriber.assemblyai_key:
            print("🎤 Тестируем AssemblyAI транскрибацию...")
            result = transcriber.transcribe_with_assemblyai(test_audio)
            if result:
                print("✅ AssemblyAI транскрибация работает!")
            else:
                print("❌ AssemblyAI транскрибация не работает")
        
        # Тестируем синхронизацию
        print(f"\n🔄 Тестируем синхронизацию текста с аудио...")
        
        output_file = "demo_aligned.json"
        success = transcriber.align_text_with_audio(test_text_file, test_audio, output_file)
        
        if success:
            print(f"✅ Синхронизация завершена: {output_file}")
            
            # Показываем результат
            import json
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📊 Результат синхронизации:")
            print(f"   - Фрагментов: {len(data.get('aligned_content', []))}")
            print(f"   - Сегментов: {len(data.get('segments', []))}")
            print(f"   - Метод: {data.get('metadata', {}).get('transcription_method', 'unknown')}")
            
            # Показываем пример фрагмента
            if data.get('aligned_content'):
                fragment = data['aligned_content'][0]
                print(f"\n📋 Пример фрагмента:")
                print(f"   Номер: {fragment['fragment_number']}")
                print(f"   Время: {fragment['start_time']:.1f} - {fragment['end_time']:.1f} сек")
                print(f"   Длительность: {fragment['duration']:.1f} сек")
                print(f"   Текст: {fragment['text'][:100]}...")
            
            # Очищаем результат
            os.remove(output_file)
        else:
            print("❌ Синхронизация не удалась")
    
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
    
    # Очищаем тестовые файлы
    os.remove(test_text_file)
    os.remove(test_audio)
    
    print(f"\n🧹 Тестовые файлы удалены")


def demo_enhanced_pipeline():
    """Демонстрация улучшенного пайплайна"""
    print("\n🎬 ДЕМОНСТРАЦИЯ УЛУЧШЕННОГО ПАЙПЛАЙНА")
    print("=" * 50)
    
    # Создаем тестовые файлы
    test_summary = """Фрагмент 1

Введение в психоанализ

Эта книга посвящена изучению психоаналитических концепций и их практическому применению в терапии.

Фрагмент 2

Основные принципы

Психоанализ основан на понимании бессознательных процессов и их влияния на поведение человека.
"""
    
    test_summary_file = "demo_summary.txt"
    with open(test_summary_file, 'w', encoding='utf-8') as f:
        f.write(test_summary)
    
    test_audio = "demo_audio.mp3"
    with open(test_audio, 'wb') as f:
        f.write(b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    
    print(f"📝 Создан тестовый summary: {test_summary_file}")
    print(f"🎵 Создан тестовый аудио: {test_audio}")
    
    # Импортируем и тестируем улучшенный пайплайн
    try:
        from video_processors.enhanced_video_pipeline import EnhancedVideoPipeline
        
        pipeline = EnhancedVideoPipeline()
        
        print(f"\n🚀 Запуск улучшенного пайплайна...")
        
        # Запускаем без транскрибации для демо
        success = pipeline.run_pipeline(
            test_summary_file,
            test_audio,
            "demo_enhanced_output",
            "artistic",
            False  # Без транскрибации
        )
        
        if success:
            print(f"✅ Улучшенный пайплайн завершен успешно!")
            
            # Показываем созданные файлы
            output_path = Path("demo_enhanced_output")
            if output_path.exists():
                for file_path in output_path.glob("*"):
                    size = file_path.stat().st_size
                    print(f"   📄 {file_path.name} ({size:,} байт)")
            
            # Очищаем результат
            import shutil
            shutil.rmtree("demo_enhanced_output")
        else:
            print("❌ Ошибка при выполнении пайплайна")
    
    except ImportError as e:
        print(f"⚠️  Не удалось импортировать EnhancedVideoPipeline: {e}")
        print("   Это нормально для демо-режима")
    
    # Очищаем тестовые файлы
    os.remove(test_summary_file)
    os.remove(test_audio)
    
    print(f"\n🧹 Тестовые файлы удалены")


def main():
    """Главная функция демонстрации"""
    print("🎤 ДЕМОНСТРАЦИЯ СИСТЕМЫ ТРАНСКРИБАЦИИ")
    print("=" * 60)
    print("Этот скрипт демонстрирует возможности транскрибации")
    print("и синхронизации текста с аудио для создания видео.")
    print()
    
    try:
        # Демонстрация транскрибации
        demo_transcription()
        
        # Демонстрация улучшенного пайплайна
        demo_enhanced_pipeline()
        
        print("\n" + "=" * 60)
        print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        print("Теперь вы можете использовать эти функции с реальными файлами:")
        print()
        print("1. Транскрибация и синхронизация:")
        print("   python audio_processors/audio_transcriber.py text.txt audio.mp3")
        print()
        print("2. Улучшенный видео-пайплайн:")
        print("   python video_processors/enhanced_video_pipeline.py summary.txt audio.mp3")
        print()
        print("3. Улучшенный пайплайн без транскрибации:")
        print("   python video_processors/enhanced_video_pipeline.py summary.txt audio.mp3 --no-transcription")
        
    except Exception as e:
        print(f"\n❌ Ошибка в демонстрации: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 