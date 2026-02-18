#!/usr/bin/env python3
"""
Умный процессор текста для создания аудиокниг
Использует dotenv для конфигурации и OpenRouter API для обработки
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
import re
from datetime import datetime


class SmartTextProcessor:
    def __init__(self, config_file: str = None):
        """
        Инициализация процессора с загрузкой конфигурации
        
        Args:
            config_file: Путь к файлу конфигурации .env
        """
        # Загружаем конфигурацию
        self.load_config(config_file)
        
        # Проверяем обязательные параметры
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")
        
        # Настройка API
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/smart-text-processor",
            "X-Title": "Smart Text Processor"
        }
        
        # Статистика
        self.stats = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'failed_chunks': 0,
            'total_characters': 0,
            'total_tokens_used': 0,
            'processing_time': 0,
            'api_calls': 0
        }
    
    def load_config(self, config_file: str = None):
        """Загружает конфигурацию из .env файла"""
        # Пытаемся загрузить конфигурацию
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            # Ищем .env файл в текущей директории
            env_files = ['.env', 'config.env', 'settings.env']
            for env_file in env_files:
                if Path(env_file).exists():
                    load_dotenv(env_file)
                    break
        
        # Загружаем параметры
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('DEFAULT_MODEL', 'anthropic/claude-3.5-sonnet')
        self.chunk_size = int(os.getenv('DEFAULT_CHUNK_SIZE', '2500'))
        self.temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.2'))
        self.max_tokens = int(os.getenv('DEFAULT_MAX_TOKENS', '4000'))
        
        # Альтернативные модели
        self.budget_model = os.getenv('BUDGET_MODEL', 'meta-llama/llama-3.1-8b-instruct')
        self.quality_model = os.getenv('QUALITY_MODEL', 'openai/gpt-4o')
        
        print(f"✅ Конфигурация загружена:")
        print(f"   Модель: {self.model}")
        print(f"   Размер части: {self.chunk_size}")
        print(f"   Температура: {self.temperature}")
    
    def create_smart_prompt(self, text_chunk: str, chunk_number: int, total_chunks: int) -> str:
        """
        Создает умный промпт для обработки текста
        
        Args:
            text_chunk: Часть текста
            chunk_number: Номер части
            total_chunks: Общее количество частей
            
        Returns:
            Промпт для нейросети
        """
        return f"""Ты - эксперт по подготовке текста для создания профессиональных аудиокниг. Обработай часть {chunk_number} из {total_chunks}.

ЗАДАЧИ:

1. ФОРМАТИРОВАНИЕ:
   - Убери переносы строк в середине предложений
   - Склей разорванные слова (например: "психо-анализ" → "психоанализ")
   - Исправь лишние пробелы и переносы
   - Сохрани структуру абзацев

2. СИНТАКСИС И ПУНКТУАЦИЯ:
   - Исправь грамматические ошибки
   - Добавь недостающие знаки препинания
   - Исправь регистр букв где нужно
   - Улучши читаемость для озвучивания

3. АУДИО-ТЕГИ (добавляй умеренно и уместно):
   - [PAUSE] - пауза между абзацами
   - [EMPHASIS]важный текст[/EMPHASIS] - выделение ключевых концепций
   - [SLOW]сложный текст[/SLOW] - замедление для сложных терминов
   - [BACKGROUND_MUSIC] - где уместна фоновая музыка (в начале/конце глав)
   - [SOUND_EFFECT]описание[/SOUND_EFFECT] - звуковые эффекты (редко)
   - [CHAPTER_START] - начало новой главы
   - [CHAPTER_END] - конец главы

4. СТИЛЬ И СОХРАНЕНИЕ:
   - Сохрани научный/академический тон
   - Не меняй смысл и терминологию
   - Сделай текст более плавным для чтения вслух
   - Оставь нумерацию и заголовки

ИСХОДНЫЙ ТЕКСТ:
{text_chunk}

ОБРАБОТАННЫЙ ТЕКСТ:"""
    
    def split_text_intelligently(self, text: str) -> List[str]:
        """
        Умное разбиение текста на части
        
        Args:
            text: Исходный текст
            
        Returns:
            Список частей текста
        """
        # Сначала разбиваем по абзацам
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Если параграф слишком большой, разбиваем его по предложениям
            if len(paragraph) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Разбиваем большой параграф
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                temp_chunk = ""
                
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) > self.chunk_size and temp_chunk:
                        chunks.append(temp_chunk.strip())
                        temp_chunk = sentence
                    else:
                        if temp_chunk:
                            temp_chunk += " " + sentence
                        else:
                            temp_chunk = sentence
                
                if temp_chunk:
                    current_chunk = temp_chunk
            else:
                # Проверяем, не превысит ли добавление параграфа лимит
                if len(current_chunk) + len(paragraph) > self.chunk_size and current_chunk:
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
    
    def process_chunk_with_retry(self, text_chunk: str, chunk_number: int, 
                               total_chunks: int, retry_count: int = 3) -> Optional[str]:
        """
        Обрабатывает часть текста с повторными попытками
        
        Args:
            text_chunk: Часть текста
            chunk_number: Номер части
            total_chunks: Общее количество частей
            retry_count: Количество попыток
            
        Returns:
            Обработанный текст или None
        """
        prompt = self.create_smart_prompt(text_chunk, chunk_number, total_chunks)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        for attempt in range(retry_count):
            try:
                self.stats['api_calls'] += 1
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=90
                )
                
                if response.status_code == 200:
                    result = response.json()
                    processed_text = result['choices'][0]['message']['content'].strip()
                    
                    # Обновляем статистику токенов
                    if 'usage' in result:
                        self.stats['total_tokens_used'] += result['usage']['total_tokens']
                    
                    return processed_text
                else:
                    print(f"❌ Ошибка API (попытка {attempt + 1}): {response.status_code}")
                    if response.status_code == 429:  # Rate limit
                        wait_time = 2 ** (attempt + 1)
                        print(f"⏳ Ожидание {wait_time} секунд...")
                        time.sleep(wait_time)
                    elif attempt < retry_count - 1:
                        time.sleep(2 ** attempt)
                        
            except Exception as e:
                print(f"❌ Ошибка запроса (попытка {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def process_text_file(self, input_file: str, output_file: str, 
                         progress_callback=None) -> bool:
        """
        Обрабатывает текстовый файл
        
        Args:
            input_file: Входной файл
            output_file: Выходной файл
            progress_callback: Функция для отображения прогресса
            
        Returns:
            True если обработка успешна
        """
        start_time = time.time()
        
        try:
            # Читаем исходный файл
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            print(f"📖 Загружен файл: {input_file}")
            print(f"📊 Размер текста: {len(text):,} символов")
            
            # Разбиваем на части
            chunks = self.split_text_intelligently(text)
            self.stats['total_chunks'] = len(chunks)
            print(f"🔪 Разбито на {len(chunks)} частей")
            
            # Обрабатываем каждую часть
            processed_chunks = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"🔄 Обрабатываю часть {i}/{len(chunks)} ({len(chunk)} символов)...")
                
                if progress_callback:
                    progress_callback(i, len(chunks))
                
                processed_chunk = self.process_chunk_with_retry(chunk, i, len(chunks))
                
                if processed_chunk:
                    processed_chunks.append(processed_chunk)
                    self.stats['processed_chunks'] += 1
                    self.stats['total_characters'] += len(processed_chunk)
                    print(f"✅ Часть {i} обработана успешно")
                else:
                    print(f"❌ Ошибка обработки части {i}")
                    processed_chunks.append(chunk)  # Оставляем исходный текст
                    self.stats['failed_chunks'] += 1
                
                # Пауза между запросами
                if i < len(chunks):
                    time.sleep(1.5)
            
            # Объединяем обработанные части
            final_text = "\n\n[PAUSE]\n\n".join(processed_chunks)
            
            # Сохраняем результат
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_text)
            
            # Обновляем статистику времени
            self.stats['processing_time'] = time.time() - start_time
            
            # Выводим статистику
            self.print_statistics()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            return False
    
    def print_statistics(self):
        """Выводит статистику обработки"""
        print("\n" + "="*50)
        print("📊 СТАТИСТИКА ОБРАБОТКИ")
        print("="*50)
        print(f"Всего частей: {self.stats['total_chunks']}")
        print(f"Обработано успешно: {self.stats['processed_chunks']}")
        print(f"Ошибок: {self.stats['failed_chunks']}")
        print(f"API вызовов: {self.stats['api_calls']}")
        print(f"Использовано токенов: {self.stats['total_tokens_used']:,}")
        print(f"Время обработки: {self.stats['processing_time']:.1f} сек")
        print(f"Размер результата: {self.stats['total_characters']:,} символов")
        
        if self.stats['total_chunks'] > 0:
            success_rate = (self.stats['processed_chunks'] / self.stats['total_chunks']) * 100
            print(f"Процент успешного извлечения: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Умный процессор текста для создания аудиокниг",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python smart_text_processor.py input.txt -o output.txt
  python smart_text_processor.py input.txt -o output.txt --config config.env
  python smart_text_processor.py input.txt -o output.txt --model budget
        """
    )
    
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл')
    parser.add_argument('--config', help='Файл конфигурации .env')
    parser.add_argument('--model', choices=['default', 'budget', 'quality'], 
                       default='default', help='Модель для использования')
    
    args = parser.parse_args()
    
    try:
        # Создаем процессор
        processor = SmartTextProcessor(args.config)
        
        # Выбираем модель если указана
        if args.model == 'budget':
            processor.model = processor.budget_model
        elif args.model == 'quality':
            processor.model = processor.quality_model
        
        print(f"🤖 Используется модель: {processor.model}")
        
        # Проверяем входной файл
        if not Path(args.input_file).exists():
            print(f"❌ Ошибка: Файл {args.input_file} не найден")
            return 1
        
        # Обрабатываем файл
        success = processor.process_text_file(args.input_file, args.output)
        
        if success:
            print(f"\n✅ Обработка завершена!")
            print(f"📄 Результат сохранен в: {args.output}")
        else:
            print("❌ Ошибка при обработке")
            return 1
        
        return 0
        
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("Создайте файл .env или config.env с вашим API ключом")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 