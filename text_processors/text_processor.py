#!/usr/bin/env python3
"""
Скрипт для постобработки извлеченного из PDF текста
Использует нейросеть через OpenRouter API для:
- Исправления форматирования (переносы строк)
- Коррекции синтаксиса и пунктуации
- Добавления тегов для аудиоэффектов
"""

import os
import json
import time
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional
import re


class TextProcessor:
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        """
        Инициализация процессора текста
        
        Args:
            api_key: API ключ для OpenRouter
            model: Модель для использования
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/text-processor",
            "X-Title": "PDF Text Processor"
        }
    
    def split_text_into_chunks(self, text: str, max_chunk_size: int = 3000) -> List[str]:
        """
        Разбивает текст на части для обработки нейросетью
        
        Args:
            text: Исходный текст
            max_chunk_size: Максимальный размер части в символах
            
        Returns:
            Список частей текста
        """
        # Разбиваем по абзацам
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Если добавление параграфа превысит лимит
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Добавляем последний чанк
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def create_processing_prompt(self, text_chunk: str) -> str:
        """
        Создает промпт для обработки текста
        
        Args:
            text_chunk: Часть текста для обработки
            
        Returns:
            Промпт для нейросети
        """
        return f"""Ты - эксперт по обработке текста для создания аудиокниг. Обработай следующий текст:

1. ИСПРАВЬ ФОРМАТИРОВАНИЕ:
   - Убери неправильные переносы строк в середине предложений
   - Объедини разорванные слова
   - Сохрани правильную структуру абзацев

2. КОРРЕКТИРУЙ СИНТАКСИС И ПУНКТУАЦИЮ:
   - Исправь грамматические ошибки
   - Добавь недостающие знаки препинания
   - Исправь регистр букв где нужно

3. ДОБАВЬ ТЕГИ ДЛЯ АУДИОЭФФЕКТОВ:
   - [PAUSE] - для пауз между абзацами
   - [EMPHASIS]текст[/EMPHASIS] - для выделения важных моментов
   - [SLOW]текст[/SLOW] - для замедления речи
   - [BACKGROUND_MUSIC] - где может звучать фоновая музыка
   - [SOUND_EFFECT]описание[/SOUND_EFFECT] - для звуковых эффектов

4. СОХРАНИ СТРУКТУРУ:
   - Не меняй смысл текста
   - Сохрани научный/академический стиль
   - Оставь нумерацию и заголовки

ИСХОДНЫЙ ТЕКСТ:
{text_chunk}

ОБРАБОТАННЫЙ ТЕКСТ:"""
    
    def process_chunk_with_ai(self, text_chunk: str, retry_count: int = 3) -> Optional[str]:
        """
        Обрабатывает часть текста с помощью нейросети
        
        Args:
            text_chunk: Часть текста для обработки
            retry_count: Количество попыток при ошибке
            
        Returns:
            Обработанный текст или None при ошибке
        """
        prompt = self.create_processing_prompt(text_chunk)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }
        
        for attempt in range(retry_count):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    print(f"Ошибка API (попытка {attempt + 1}): {response.status_code}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)  # Экспоненциальная задержка
                        
            except Exception as e:
                print(f"Ошибка запроса (попытка {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def process_text_file(self, input_file: str, output_file: str, chunk_size: int = 3000) -> bool:
        """
        Обрабатывает весь текстовый файл
        
        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            chunk_size: Размер части для обработки
            
        Returns:
            True если обработка прошла успешно
        """
        try:
            # Читаем исходный файл
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            print(f"📖 Загружен файл: {input_file}")
            print(f"📊 Размер текста: {len(text):,} символов")
            
            # Разбиваем на части
            chunks = self.split_text_into_chunks(text, chunk_size)
            print(f"🔪 Разбито на {len(chunks)} частей")
            
            # Обрабатываем каждую часть
            processed_chunks = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"🔄 Обрабатываю часть {i}/{len(chunks)} ({len(chunk)} символов)...")
                
                processed_chunk = self.process_chunk_with_ai(chunk)
                
                if processed_chunk:
                    processed_chunks.append(processed_chunk)
                    print(f"✅ Часть {i} обработана успешно")
                else:
                    print(f"❌ Ошибка обработки части {i}")
                    # Добавляем исходный текст если обработка не удалась
                    processed_chunks.append(chunk)
                
                # Пауза между запросами
                if i < len(chunks):
                    time.sleep(1)
            
            # Объединяем обработанные части
            final_text = "\n\n[PAUSE]\n\n".join(processed_chunks)
            
            # Сохраняем результат
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_text)
            
            print(f"✅ Обработка завершена!")
            print(f"📄 Результат сохранен в: {output_file}")
            print(f"📊 Размер обработанного текста: {len(final_text):,} символов")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Обработка текста из PDF с помощью нейросети",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python text_processor.py input.txt -o output.txt
  python text_processor.py input.txt -o output.txt --chunk-size 2000
  python text_processor.py input.txt -o output.txt --model anthropic/claude-3.5-sonnet
        """
    )
    
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл')
    parser.add_argument('--api-key', help='API ключ OpenRouter (или переменная OPENROUTER_API_KEY)')
    parser.add_argument('--model', default='anthropic/claude-3.5-sonnet', 
                       help='Модель для использования')
    parser.add_argument('--chunk-size', type=int, default=3000,
                       help='Размер части текста для обработки')
    
    args = parser.parse_args()
    
    # Получаем API ключ
    api_key = args.api_key or os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ Ошибка: Не указан API ключ OpenRouter")
        print("Укажите через --api-key или установите переменную OPENROUTER_API_KEY")
        return 1
    
    # Проверяем входной файл
    if not Path(args.input_file).exists():
        print(f"❌ Ошибка: Файл {args.input_file} не найден")
        return 1
    
    # Создаем процессор и обрабатываем
    processor = TextProcessor(api_key, args.model)
    
    success = processor.process_text_file(
        args.input_file, 
        args.output, 
        args.chunk_size
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 