#!/usr/bin/env python3
"""
Процессор для очистки и улучшения текста из PDF
Фокусируется на фильтрации лишних элементов и выделение основного содержания
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


class CleanTextProcessor:
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
            "HTTP-Referer": "https://github.com/your-repo/clean-text-processor",
            "X-Title": "Clean Text Processor"
        }
        
        # Статистика
        self.stats = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'failed_chunks': 0,
            'total_characters': 0,
            'total_tokens_used': 0,
            'processing_time': 0,
            'api_calls': 0,
            'filtered_elements': 0
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
        self.chunk_size = int(os.getenv('DEFAULT_CHUNK_SIZE', '3000'))
        self.temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.1'))
        self.max_tokens = int(os.getenv('DEFAULT_MAX_TOKENS', '4000'))
        
        # Альтернативные модели
        self.budget_model = os.getenv('BUDGET_MODEL', 'meta-llama/llama-3.1-8b-instruct')
        self.quality_model = os.getenv('QUALITY_MODEL', 'openai/gpt-4o')
        
        print(f"✅ Конфигурация загружена:")
        print(f"   Модель: {self.model}")
        print(f"   Размер части: {self.chunk_size}")
        print(f"   Температура: {self.temperature}")
    
    def detect_book_info(self, text: str) -> Dict[str, str]:
        """
        Автоматически определяет информацию о книге из текста
        
        Args:
            text: Исходный текст
            
        Returns:
            Словарь с информацией о книге
        """
        book_info = {
            'title': 'Неизвестная книга',
            'author': 'Неизвестный автор',
            'topic': 'Общая тема'
        }
        
        # Ищем название книги (обычно в начале)
        lines = text.split('\n')[:20]  # Первые 20 строк
        
        # Паттерны для поиска названия
        title_patterns = [
            r'^([А-Я][А-Я\s,]+)$',  # Заглавные буквы
            r'^([А-Я][а-я\s,]+)$',  # Первая заглавная
            r'([А-Я][А-Я\s]+ЯВЛЕНИЯ[А-Я\s]+)',  # Шизоидные явления
        ]
        
        for line in lines:
            line = line.strip()
            for pattern in title_patterns:
                match = re.search(pattern, line)
                if match and len(line) > 10:
                    book_info['title'] = line
                    break
            if book_info['title'] != 'Неизвестная книга':
                break
        
        # Ищем автора
        author_patterns = [
            r'([А-Я][а-я]+\s+[А-Я][а-я]+)\s*[-–—]\s*автор',
            r'Автор[:\s]+([А-Я][а-я]+\s+[А-Я][а-я]+)',
            r'([А-Я][а-я]+\s+[А-Я][а-я]+)\s*[-–—]',
            r'Гарри\s+Гантрип',  # Специфично для этой книги
        ]
        
        for line in lines:
            for pattern in author_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    book_info['author'] = match.group(1) if match.groups() else match.group(0)
                    break
            if book_info['author'] != 'Неизвестный автор':
                break
        
        # Определяем тему по ключевым словам
        topic_keywords = {
            'психоанализ': 'Психоанализ и психология',
            'шизоид': 'Шизоидные явления в психологии',
            'психология': 'Психология и психиатрия',
            'терапия': 'Психотерапия',
            'личность': 'Психология личности'
        }
        
        text_lower = text.lower()
        for keyword, topic in topic_keywords.items():
            if keyword in text_lower:
                book_info['topic'] = topic
                break
        
        return book_info
    
    def create_clean_prompt(self, text_chunk: str, chunk_number: int, total_chunks: int, 
                           book_info: Dict[str, str]) -> str:
        """
        Создает промпт для очистки текста
        
        Args:
            text_chunk: Часть текста
            chunk_number: Номер части
            total_chunks: Общее количество частей
            book_info: Информация о книге
            
        Returns:
            Промпт для нейросети
        """
        return f"""Ты - эксперт по обработке текста для создания читаемых версий книг. Обработай часть {chunk_number} из {total_chunks}.

ИНФОРМАЦИЯ О КНИГЕ:
- Название: {book_info['title']}
- Автор: {book_info['author']}
- Тема: {book_info['topic']}

ЗАДАЧИ:

1. ФОРМАТИРОВАНИЕ:
   - Убери переносы строк в середине предложений
   - Склей разорванные слова (например: "психо-анализ" → "психоанализ")
   - Исправь лишние пробелы и переносы
   - Сохрани структуру абзацев

2. ФИЛЬТРАЦИЯ (УДАЛИ):
   - ISBN номера (например: "ISBN 978-5-88230-251-0")
   - Номера страниц (например: "<номер страницы> <автор/название книги>")
   - Библиографические данные (УДК, ББК, издательства)
   - Предупреждения об авторских правах (©, Copyright)
   - Благодарности и предисловия
   - Технические пометки и форматирование

3. УЛУЧШЕНИЕ:
   - Исправь грамматические ошибки
   - Добавь недостающие знаки препинания
   - Исправь регистр букв
   - Сделай текст более читаемым

4. ВЫДЕЛЕНИЕ СОДЕРЖАНИЯ:
   - Сохрани все важные идеи и концепции
   - Подчеркни ключевые термины и определения
   - Сохрани научный стиль и точность

5. СТИЛЬ:
   - Сохрани стиль автора
   - Не меняй смысл и терминологию
   - Сделай текст более плавным для чтения
   - Убери технические артефакты PDF

ИСХОДНЫЙ ТЕКСТ:
{text_chunk}

ОЧИЩЕННЫЙ ТЕКСТ:"""
    
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
                               total_chunks: int, book_info: Dict[str, str], 
                               retry_count: int = 5) -> Optional[str]:
        """
        Обрабатывает часть текста с повторными попытками
        
        Args:
            text_chunk: Часть текста
            chunk_number: Номер части
            total_chunks: Общее количество частей
            book_info: Информация о книге
            retry_count: Количество попыток
            
        Returns:
            Обработанный текст или None
        """
        prompt = self.create_clean_prompt(text_chunk, chunk_number, total_chunks, book_info)
        
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
                         book_title: str = None, book_author: str = None) -> bool:
        """
        Обрабатывает текстовый файл
        
        Args:
            input_file: Входной файл
            output_file: Выходной файл
            book_title: Название книги (опционально)
            book_author: Автор книги (опционально)
            
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
            
            # Определяем информацию о книге
            book_info = self.detect_book_info(text)
            if book_title:
                book_info['title'] = book_title
            if book_author:
                book_info['author'] = book_author
            
            print(f"📚 Информация о книге:")
            print(f"   Название: {book_info['title']}")
            print(f"   Автор: {book_info['author']}")
            print(f"   Тема: {book_info['topic']}")
            
            # Разбиваем на части
            chunks = self.split_text_intelligently(text)
            self.stats['total_chunks'] = len(chunks)
            print(f"🔪 Разбито на {len(chunks)} частей")
            
            # Обрабатываем каждую часть
            processed_chunks = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"🔄 Обрабатываю часть {i}/{len(chunks)} ({len(chunk)} символов)...")
                
                processed_chunk = self.process_chunk_with_retry(chunk, i, len(chunks), book_info)
                
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
            final_text = "\n\n".join(processed_chunks)
            
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
        description="Процессор для очистки и улучшения текста из PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python clean_text_processor.py input.txt -o output.txt
  python clean_text_processor.py input.txt -o output.txt --title "Название книги" --author "Автор"
  python clean_text_processor.py input.txt -o output.txt --config config.env
        """
    )
    
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл')
    parser.add_argument('--config', help='Файл конфигурации .env')
    parser.add_argument('--title', help='Название книги')
    parser.add_argument('--author', help='Автор книги')
    parser.add_argument('--model', choices=['default', 'budget', 'quality'], 
                       default='default', help='Модель для использования')
    
    args = parser.parse_args()
    
    try:
        # Создаем процессор
        processor = CleanTextProcessor(args.config)
        
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
        success = processor.process_text_file(
            args.input_file, 
            args.output,
            args.title,
            args.author
        )
        
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