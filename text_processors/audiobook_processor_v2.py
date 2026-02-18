#!/usr/bin/env python3
"""
Специализированный процессор для подготовки текста к созданию аудиокниги (рефакторенная версия).

Наследует от BaseProcessor для использования:
- Унифицированной загрузки конфигурации
- Готового API клиента
- Методов разбиения текста

Включает:
- Исправление форматирования
- Коррекцию синтаксиса
- Добавление аудио-тегов
- Разбивку на главы
- Подготовку метаданных
"""

import json
import time
import re
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from utils.base_processor import BaseProcessor, ProcessingReport


class AudioBookProcessor(BaseProcessor):
    """
    Процессор для подготовки текста к созданию аудиокниги.
    
    Функции:
    - Определение глав в тексте
    - Исправление форматирования и синтаксиса
    - Добавление аудио-тегов для TTS
    - Создание метаданных
    """
    
    # Паттерны для поиска глав
    CHAPTER_PATTERNS = [
        r'^ГЛАВА\s+\d+[.:]?\s*(.+?)$',
        r'^Chapter\s+\d+[.:]?\s*(.+?)$',
        r'^Часть\s+\d+[.:]?\s*(.+?)$',
        r'^Part\s+\d+[.:]?\s*(.+?)$',
        r'^\d+[.:]\s*(.+?)$',
        r'^[IVX]+[.:]\s*(.+?)$'
    ]
    
    # Аудио-теги для TTS
    AUDIO_TAGS = {
        'pause': '[PAUSE]',
        'emphasis_start': '[EMPHASIS]',
        'emphasis_end': '[/EMPHASIS]',
        'slow_start': '[SLOW]',
        'slow_end': '[/SLOW]',
        'background_music': '[BACKGROUND_MUSIC]',
        'sound_effect_start': '[SOUND_EFFECT]',
        'sound_effect_end': '[/SOUND_EFFECT]',
        'chapter_start': '[CHAPTER_START]',
        'chapter_end': '[CHAPTER_END]'
    }
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        model: Optional[str] = None,
        model_preset: str = 'quality',
        chunk_size: int = 2500
    ):
        """
        Инициализация процессора аудиокниги.
        
        Args:
            config_file: Путь к файлу конфигурации
            model: Модель для использования
            model_preset: Пресет модели ('default', 'budget', 'quality')
            chunk_size: Размер чанка (по умолчанию 2500 для аудио)
        """
        super().__init__(
            config_file=config_file,
            model=model,
            model_preset=model_preset,
            chunk_size=chunk_size
        )
        
        # Низкая температура для консистентности
        self.temperature = 0.2
        self.max_tokens = 4000
        
        # Статистика обработки
        self._chapter_stats: List[Dict] = []
    
    def process(self, text: str) -> str:
        """
        Обрабатывает текст для создания аудиокниги.
        
        Args:
            text: Исходный текст
            
        Returns:
            Обработанный текст с аудио-тегами
        """
        # Разбиваем на чанки
        chunks = self.split_text(text, preset='audiobook')
        
        self.logger.info(f"🔪 Разбито на {len(chunks)} частей")
        
        # Обрабатываем каждый чанк
        processed_chunks = []
        
        for i, chunk in enumerate(chunks, 1):
            self.logger.info(f"🔄 Обработка части {i}/{len(chunks)}...")
            
            try:
                processed = self._process_chunk(chunk, i, len(chunks))
                processed_chunks.append(processed)
                self._report.chunks_processed += 1
                self.logger.info(f"✅ Часть {i} обработана")
            except Exception as e:
                self.logger.error(f"❌ Ошибка обработки части {i}: {e}")
                processed_chunks.append(chunk)  # Оставляем исходный
                self._report.errors.append(f"Чанк {i}: {e}")
            
            if i < len(chunks):
                time.sleep(0.5)
        
        # Объединяем с паузами
        final_text = "\n\n[PAUSE]\n\n".join(processed_chunks)
        
        return final_text
    
    def process_file_with_metadata(
        self,
        input_file: str,
        output_file: str,
        metadata_file: Optional[str] = None
    ) -> ProcessingReport:
        """
        Обрабатывает файл и создает метаданные.
        
        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            metadata_file: Путь к файлу метаданных
            
        Returns:
            Отчёт о выполнении
        """
        self._report.start_time = datetime.now()
        
        # Читаем
        text = self.read_file(input_file)
        
        # Определяем главы
        chapters = self.detect_chapters(text)
        self.logger.info(f"📚 Найдено глав: {len(chapters)}")
        self._chapter_stats = chapters
        
        # Обрабатываем
        result = self.process(text)
        
        # Записываем
        self.write_file(output_file, result)
        
        # Создаем метаданные
        if metadata_file:
            self._create_metadata(input_file, chapters, metadata_file)
        
        # Создаем отчёт
        report = self.create_report(input_file, output_file)
        self.print_report()
        
        return report
    
    def detect_chapters(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Определяет главы в тексте.
        
        Args:
            text: Исходный текст
            
        Returns:
            Список кортежей (название_главы, начало, конец)
        """
        chapters = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            for pattern in self.CHAPTER_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    chapter_title = match.group(1).strip()
                    chapters.append((chapter_title, i, i))
                    break
        
        # Определяем конец каждой главы
        for i in range(len(chapters)):
            if i < len(chapters) - 1:
                chapters[i] = (chapters[i][0], chapters[i][1], chapters[i + 1][1])
            else:
                chapters[i] = (chapters[i][0], chapters[i][1], len(lines))
        
        return chapters
    
    def _process_chunk(self, chunk: str, chunk_number: int, total_chunks: int) -> str:
        """
        Обрабатывает часть текста с помощью LLM.
        
        Args:
            chunk: Часть текста
            chunk_number: Номер части
            total_chunks: Общее количество частей
            
        Returns:
            Обработанный текст
        """
        prompt = self._build_audiobook_prompt(chunk, chunk_number, total_chunks)
        return self.call_api(prompt, max_tokens=self.max_tokens)
    
    def _build_audiobook_prompt(self, text_chunk: str, chunk_number: int, total_chunks: int) -> str:
        """Строит промпт для обработки текста аудиокниги."""
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
    
    def _create_metadata(
        self,
        input_file: str,
        chapters: List[Tuple[str, int, int]],
        metadata_file: str
    ) -> None:
        """Создает метаданные для аудиокниги."""
        text = Path(input_file).read_text(encoding='utf-8')
        
        # Извлекаем название и автора
        title = Path(input_file).stem
        author = "Неизвестный автор"
        
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
        
        metadata = {
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
            "processing_stats": {
                "total_chunks": self._report.chunks_processed,
                "api_calls": self._report.api_calls,
                "errors": len(self._report.errors)
            },
            "audio_tags_used": list(self.AUDIO_TAGS.values())
        }
        
        Path(metadata_file).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        self.logger.info(f"📋 Метаданные сохранены: {metadata_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Подготовка текста для создания аудиокниги (рефакторенная версия)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python audiobook_processor_v2.py input.txt -o output.txt
  python audiobook_processor_v2.py input.txt -o output.txt --metadata metadata.json
  python audiobook_processor_v2.py input.txt -o output.txt --chunk-size 2000 --model-preset quality
        """
    )
    
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл')
    parser.add_argument('--metadata', help='Файл для сохранения метаданных')
    parser.add_argument('--config', help='Файл конфигурации')
    parser.add_argument('--model-preset', choices=['default', 'budget', 'quality'],
                       default='quality', help='Пресет модели')
    parser.add_argument('--chunk-size', type=int, default=2500,
                       help='Размер части текста для обработки')
    
    args = parser.parse_args()
    
    # Проверяем входной файл
    if not Path(args.input_file).exists():
        print(f"❌ Ошибка: Файл {args.input_file} не найден")
        return 1
    
    try:
        # Создаем процессор
        processor = AudioBookProcessor(
            config_file=args.config,
            model_preset=args.model_preset,
            chunk_size=args.chunk_size
        )
        
        # Обрабатываем
        processor.process_file_with_metadata(
            args.input_file,
            args.output,
            args.metadata
        )
        
        return 0
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
