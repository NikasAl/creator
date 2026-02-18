#!/usr/bin/env python3
"""
Специализированный процессор для подготовки текста к созданию аудиокниги
Включает:
- Исправление форматирования
- Коррекцию синтаксиса
- Добавление аудио-тегов
- Разбивку на главы
- Подготовку метаданных
"""

import os
import json
import time
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime


class AudioBookProcessor:
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        """
        Инициализация процессора аудиокниги
        
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
            "HTTP-Referer": "https://github.com/your-repo/audiobook-processor",
            "X-Title": "AudioBook Text Processor"
        }
        
        # Статистика обработки
        self.stats = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'failed_chunks': 0,
            'total_characters': 0,
            'processing_time': 0
        }
    
    def detect_chapters(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Определяет главы в тексте
        
        Args:
            text: Исходный текст
            
        Returns:
            Список кортежей (название_главы, начало, конец)
        """
        chapters = []
        
        # Паттерны для поиска глав
        patterns = [
            r'^ГЛАВА\s+\d+[.:]?\s*(.+?)$',
            r'^Chapter\s+\d+[.:]?\s*(.+?)$',
            r'^Часть\s+\d+[.:]?\s*(.+?)$',
            r'^Part\s+\d+[.:]?\s*(.+?)$',
            r'^\d+[.:]\s*(.+?)$',
            r'^[IVX]+[.:]\s*(.+?)$'
        ]
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    chapter_title = match.group(1).strip()
                    chapters.append((chapter_title, i, i))
                    break
        
        # Определяем конец каждой главы
        for i in range(len(chapters)):
            if i < len(chapters) - 1:
                chapters[i] = (chapters[i][0], chapters[i][1], chapters[i+1][1])
            else:
                chapters[i] = (chapters[i][0], chapters[i][1], len(lines))
        
        return chapters
    
    def split_text_into_chunks(self, text: str, max_chunk_size: int = 2500) -> List[str]:
        """
        Разбивает текст на части с учетом структуры
        
        Args:
            text: Исходный текст
            max_chunk_size: Максимальный размер части
            
        Returns:
            Список частей текста
        """
        # Сначала разбиваем по абзацам
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Если параграф слишком большой, разбиваем его
            if len(paragraph) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Разбиваем большой параграф по предложениям
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                temp_chunk = ""
                
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) > max_chunk_size and temp_chunk:
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
    
    def create_audiobook_prompt(self, text_chunk: str, chunk_number: int, total_chunks: int) -> str:
        """
        Создает промпт для обработки текста аудиокниги
        
        Args:
            text_chunk: Часть текста
            chunk_number: Номер части
            total_chunks: Общее количество частей
            
        Returns:
            Промпт для нейросети
        """
        return f"""Ты - профессиональный редактор аудиокниг. Обработай часть {chunk_number} из {total_chunks} для создания качественной аудиокниги.

ЗАДАЧИ:

1. ФОРМАТИРОВАНИЕ:
   - Исправь переносы строк в середине предложений
   - Объедини разорванные слова
   - Убери лишние пробелы и переносы
   - Сохрани структуру абзацев

2. СИНТАКСИС И ПУНКТУАЦИЯ:
   - Исправь грамматические ошибки
   - Добавь недостающие знаки препинания
   - Исправь регистр букв
   - Улучши читаемость

3. АУДИО-ТЕГИ (добавляй умеренно):
   - [PAUSE] - пауза между абзацами
   - [EMPHASIS]важный текст[/EMPHASIS] - выделение ключевых моментов
   - [SLOW]медленный текст[/SLOW] - замедление для сложных понятий
   - [BACKGROUND_MUSIC] - где уместна фоновая музыка
   - [SOUND_EFFECT]описание[/SOUND_EFFECT] - звуковые эффекты
   - [CHAPTER_START] - начало новой главы
   - [CHAPTER_END] - конец главы

4. СТИЛЬ:
   - Сохрани научный/академический тон
   - Не меняй смысл и терминологию
   - Сделай текст более плавным для чтения вслух

ИСХОДНЫЙ ТЕКСТ:
{text_chunk}

ОБРАБОТАННЫЙ ТЕКСТ:"""
    
    def process_chunk_with_ai(self, text_chunk: str, chunk_number: int, total_chunks: int, retry_count: int = 3) -> Optional[str]:
        """
        Обрабатывает часть текста с помощью нейросети
        
        Args:
            text_chunk: Часть текста
            chunk_number: Номер части
            total_chunks: Общее количество частей
            retry_count: Количество попыток
            
        Returns:
            Обработанный текст или None
        """
        prompt = self.create_audiobook_prompt(text_chunk, chunk_number, total_chunks)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,  # Низкая температура для консистентности
            "max_tokens": 4000
        }
        
        for attempt in range(retry_count):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=90
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    print(f"❌ Ошибка API (попытка {attempt + 1}): {response.status_code}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)
                        
            except Exception as e:
                print(f"❌ Ошибка запроса (попытка {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def create_metadata(self, title: str, author: str, chapters: List[Tuple[str, int, int]]) -> Dict:
        """
        Создает метаданные для аудиокниги
        
        Args:
            title: Название книги
            author: Автор
            chapters: Список глав
            
        Returns:
            Словарь с метаданными
        """
        return {
            "title": title,
            "author": author,
            "processed_date": datetime.now().isoformat(),
            "total_chapters": len(chapters),
            "chapters": [
                {
                    "title": chapter[0],
                    "start_line": chapter[1],
                    "end_line": chapter[2]
                }
                for chapter in chapters
            ],
            "processing_stats": self.stats,
            "audio_tags_used": [
                "[PAUSE]", "[EMPHASIS]", "[SLOW]", 
                "[BACKGROUND_MUSIC]", "[SOUND_EFFECT]",
                "[CHAPTER_START]", "[CHAPTER_END]"
            ]
        }
    
    def process_text_file(self, input_file: str, output_file: str, 
                         metadata_file: str = None, chunk_size: int = 2500) -> bool:
        """
        Обрабатывает текстовый файл для создания аудиокниги
        
        Args:
            input_file: Входной файл
            output_file: Выходной файл
            metadata_file: Файл для метаданных
            chunk_size: Размер части
            
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
            
            # Определяем главы
            chapters = self.detect_chapters(text)
            print(f"📚 Найдено глав: {len(chapters)}")
            
            # Разбиваем на части
            chunks = self.split_text_into_chunks(text, chunk_size)
            self.stats['total_chunks'] = len(chunks)
            print(f"🔪 Разбито на {len(chunks)} частей")
            
            # Обрабатываем каждую часть
            processed_chunks = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"🔄 Обрабатываю часть {i}/{len(chunks)} ({len(chunk)} символов)...")
                
                processed_chunk = self.process_chunk_with_ai(chunk, i, len(chunks))
                
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
            
            # Создаем и сохраняем метаданные
            if metadata_file:
                # Извлекаем название и автора из текста
                title = Path(input_file).stem
                author = "Неизвестный автор"
                
                # Попытка найти автора в тексте
                author_patterns = [
                    r'Автор[:\s]+([^\n]+)',
                    r'Author[:\s]+([^\n]+)',
                    r'([А-Я][а-я]+\s+[А-Я][а-я]+)\s*[-–—]\s*автор'
                ]
                
                for pattern in author_patterns:
                    match = re.search(pattern, text[:2000], re.IGNORECASE)
                    if match:
                        author = match.group(1).strip()
                        break
                
                metadata = self.create_metadata(title, author, chapters)
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                print(f"📋 Метаданные сохранены в: {metadata_file}")
            
            # Обновляем статистику
            self.stats['processing_time'] = time.time() - start_time
            
            print(f"✅ Обработка завершена!")
            print(f"📄 Результат сохранен в: {output_file}")
            print(f"📊 Статистика:")
            print(f"   - Обработано частей: {self.stats['processed_chunks']}/{self.stats['total_chunks']}")
            print(f"   - Ошибок: {self.stats['failed_chunks']}")
            print(f"   - Время обработки: {self.stats['processing_time']:.1f} сек")
            print(f"   - Размер результата: {len(final_text):,} символов")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Подготовка текста для создания аудиокниги",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python audiobook_processor.py input.txt -o output.txt
  python audiobook_processor.py input.txt -o output.txt --metadata metadata.json
  python audiobook_processor.py input.txt -o output.txt --chunk-size 2000 --model anthropic/claude-3.5-sonnet
        """
    )
    
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл')
    parser.add_argument('--metadata', help='Файл для сохранения метаданных')
    parser.add_argument('--api-key', help='API ключ OpenRouter (или переменная OPENROUTER_API_KEY)')
    parser.add_argument('--model', default='anthropic/claude-3.5-sonnet', 
                       help='Модель для использования')
    parser.add_argument('--chunk-size', type=int, default=2500,
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
    processor = AudioBookProcessor(api_key, args.model)
    
    success = processor.process_text_file(
        args.input_file, 
        args.output, 
        args.metadata,
        args.chunk_size
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 