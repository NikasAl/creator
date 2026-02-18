#!/usr/bin/env python3
"""
Процессор для создания пересказа основных идей из фрагментов текста.
Фокусируется на изложении сложных концепций простым языком для неподготовленного читателя.

РЕФАКТОРИНГ: Использует унифицированные модули из utils/
- ConfigLoader для загрузки конфигурации
- OpenRouterClient для API-вызовов
- split_text_into_chunks для разбиения текста
- BaseProcessor как базовый класс
"""

import os
import sys
import json
import time
import argparse
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import locale

# Импортируем унифицированные модули
from utils.config_loader import ConfigLoader, get_config
from utils.openrouter_client import OpenRouterClient, get_client
from utils.text_splitter import split_text_into_chunks, get_chunk_stats
from utils.base_processor import BaseProcessor, ProcessingReport, create_arg_parser


# Устанавливаем русскую локаль для форматирования дат
try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU')
    except:
        pass


@dataclass
class ContextInfo:
    """Информация о контексте текста."""
    topic: str = 'Общая тема'
    complexity: str = 'средняя'
    target_audience: str = 'неподготовленный читатель'
    style: str = 'обучающий'


class SummaryProcessor(BaseProcessor):
    """
    Процессор для создания пересказа текста.
    
    РЕФАКТОРИНГ: Наследует от BaseProcessor, использует унифицированные модули.
    
    Удалено ~150 строк дублированного кода:
    - load_config() → ConfigLoader
    - split_text_into_chunks() → utils.text_splitter
    - API-вызовы → OpenRouterClient
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        book_title: Optional[str] = None,
        model_preset: str = 'default'
    ):
        """
        Инициализация процессора.
        
        Args:
            config_file: Путь к файлу конфигурации
            book_title: Название книги для документа
            model_preset: Пресет модели ('default', 'budget', 'quality')
        """
        # Инициализируем базовый класс
        super().__init__(
            config_file=config_file,
            model_preset=model_preset,
            chunk_size=10000  # Больший размер для summary
        )
        
        # Специфичные настройки
        self.book_title = book_title
        
        # Загружаем модели из конфига
        self.summary_model = self.config.get('SUMMARY_MODEL', default=self.model)
        self.image_model = self.config.get('IMAGE_MODEL', default='FLUX')
        self.vision_model = self.config.get('VISION_MODEL', default='')
        
        # Контекст текста
        self.context = ContextInfo()
        
        self.logger.info(f"Модель для пересказа: {self.summary_model}")
        self.logger.info(f"Модель для изображений: {self.image_model}")
    
    # === Методы определения контекста ===
    
    def detect_topic_with_llm(self, text_sample: str) -> ContextInfo:
        """
        Определяет тему и контекст текста с помощью LLM.
        
        Args:
            text_sample: Образец текста для анализа
            
        Returns:
            ContextInfo с информацией о теме
        """
        prompt = f"""Проанализируй следующий фрагмент текста и определи его тему и характеристики.

ЗАДАЧИ:
1. Определи основную тему текста (1-2 предложения)
2. Оцени сложность изложения (низкая/средняя/высокая)
3. Определи целевую аудиторию
4. Предложи стиль изложения для пересказа

ФРАГМЕНТ ТЕКСТА:
{text_sample[:2000]}...

ОТВЕТЬ В СЛЕДУЮЩЕМ ФОРМАТЕ:
ТЕМА: [краткое описание основной темы]
СЛОЖНОСТЬ: [низкая/средняя/высокая]
АУДИТОРИЯ: [описание целевой аудитории]
СТИЛЬ: [рекомендуемый стиль изложения]"""

        try:
            # Используем budget модель для определения темы
            response = self.client.chat_with_system(
                system="Ты аналитик текстов. Отвечай кратко и точно в указанном формате.",
                user=prompt,
                model=self.config.get_model('budget').name,
                max_tokens=500,
                temperature=0.1
            )
            
            return self._parse_topic_analysis(response)
            
        except Exception as e:
            self.logger.warning(f"Ошибка определения темы: {e}")
            return ContextInfo()
    
    def _parse_topic_analysis(self, analysis: str) -> ContextInfo:
        """Парсит ответ LLM для извлечения информации о теме."""
        context = ContextInfo()
        
        for line in analysis.split('\n'):
            line = line.strip()
            if line.startswith('ТЕМА:'):
                context.topic = line.replace('ТЕМА:', '').strip()
            elif line.startswith('СЛОЖНОСТЬ:'):
                complexity = line.replace('СЛОЖНОСТЬ:', '').strip().lower()
                if complexity in ['низкая', 'средняя', 'высокая']:
                    context.complexity = complexity
            elif line.startswith('АУДИТОРИЯ:'):
                context.target_audience = line.replace('АУДИТОРИЯ:', '').strip()
            elif line.startswith('СТИЛЬ:'):
                context.style = line.replace('СТИЛЬ:', '').strip()
        
        return context
    
    def detect_topic_and_context(self, text: str) -> ContextInfo:
        """Автоматически определяет тему и контекст текста."""
        self.logger.info("Определение темы текста...")
        
        # Берем первый чанк для анализа
        chunks = self.split_text(text, max_chars=2000)
        if chunks:
            self.context = self.detect_topic_with_llm(chunks[0])
            self.logger.info(f"Тема определена: {self.context.topic}")
        else:
            self.context = ContextInfo()
        
        return self.context
    
    # === Основные методы обработки ===
    
    def create_summary_prompt(
        self,
        text_chunk: str,
        chunk_number: int,
        total_chunks: int,
        style: str = 'educational'
    ) -> str:
        """Создает промпт для пересказа."""
        
        style_instructions = {
            'educational': """
СТИЛЬ ИЗЛОЖЕНИЯ:
- Используй простой, понятный язык
- Объясняй сложные термины простыми словами
- Структурируй информацию логично
- Добавляй примеры и аналогии
- Делай акцент на практическом применении
- Используй активный залог и короткие предложения""",
            
            'simple': """
СТИЛЬ ИЗЛОЖЕНИЯ:
- Максимально простой язык
- Избегай сложных терминов
- Короткие предложения
- Четкая структура
- Основные факты и выводы""",
            
            'detailed': """
СТИЛЬ ИЗЛОЖЕНИЯ:
- Подробное объяснение концепций
- Сохранение научной точности
- Детальные примеры
- Исторический контекст
- Связи с другими теориями"""
        }
        
        return f"""Ты - эксперт по созданию понятных пересказов сложных текстов. Создай пересказ фрагмента {chunk_number} из {total_chunks}.

КОНТЕКСТ:
- Тема: {self.context.topic}
- Сложность исходного текста: {self.context.complexity}
- Целевая аудитория: {self.context.target_audience}

ЗАДАЧИ:

1. ВЫДЕЛЕНИЕ ГЛАВНОГО:
   - Определи ключевые идеи и концепции
   - Выдели основные факты и аргументы
   - Найди центральную мысль фрагмента
   - Исключи второстепенную информацию

2. УПРОЩЕНИЕ:
   - Переведи сложные термины на простой язык
   - Объясни абстрактные концепции через конкретные примеры
   - Разбей сложные предложения на простые
   - Используй активный залог

3. СТРУКТУРИРОВАНИЕ:
   - Создай логичную структуру изложения
   - Группируй связанные идеи
   - Добавь переходы между частями

{style_instructions.get(style, style_instructions['educational'])}

5. ФОРМАТ ВЫВОДА:
   - Начни с краткого введения к теме
   - Основная часть с ключевыми идеями
   - Практические выводы
   - Длина: примерно 1/3 от исходного текста
   - Используй маркдаун разметку

ИСХОДНЫЙ ФРАГМЕНТ:
{text_chunk}

ПЕРЕСКАЗ:"""
    
    def process(self, text: str, style: str = 'educational') -> str:
        """
        Обрабатывает текст и создаёт пересказ.
        
        Args:
            text: Исходный текст
            style: Стиль изложения ('educational', 'simple', 'detailed')
            
        Returns:
            Пересказ текста
        """
        # Определяем контекст
        self.detect_topic_and_context(text)
        
        # Разбиваем на чанки
        chunks = self.split_text(text)
        self._report.chunks_processed = len(chunks)
        
        self.logger.info(f"Разбито на {len(chunks)} фрагментов")
        
        # Обрабатываем каждый чанк
        summaries = []
        
        for i, chunk in enumerate(chunks, 1):
            self.logger.info(f"Обработка фрагмента {i}/{len(chunks)} ({len(chunk)} символов)...")
            
            prompt = self.create_summary_prompt(chunk, i, len(chunks), style)
            
            try:
                summary = self.call_api(
                    prompt=prompt,
                    model=self.summary_model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                summaries.append(f"## Фрагмент {i}\n\n{summary}")
                self._report.chunks_processed += 1
                self._report.api_calls += 1
                
                self.logger.info(f"Фрагмент {i} обработан")
                
            except Exception as e:
                self.logger.error(f"Ошибка обработки фрагмента {i}: {e}")
                self._report.errors.append(f"Фрагмент {i}: {e}")
            
            # Пауза между запросами
            if i < len(chunks):
                time.sleep(1)
        
        return "\n\n".join(summaries)
    
    def process_file(
        self,
        input_file: str,
        output_file: str,
        style: str = 'educational',
        **kwargs
    ) -> ProcessingReport:
        """
        Обрабатывает файл и создаёт пересказ.
        
        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            style: Стиль изложения
            **kwargs: Дополнительные параметры (игнорируются)
            
        Returns:
            Отчёт о выполнении
        """
        self._report.start_time = datetime.now()
        
        # Читаем
        text = self.read_file(input_file)
        
        # Обрабатываем
        summaries = self.process(text, style)
        
        # Формируем документ
        final_content = self._format_output(summaries, style)
        
        # Записываем
        self.write_file(output_file, final_content)
        
        # Отчёт
        self._report.end_time = datetime.now()
        self._report.tokens_used = self.client.total_tokens
        self.print_report()
        
        return self._report
    
    def _format_output(self, summaries: str, style: str) -> str:
        """Форматирует итоговый документ."""
        now = datetime.now()
        
        try:
            russian_date = now.strftime('%d %B %Y года')
        except:
            months_ru = {
                1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
                5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
                9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
            }
            month_name = months_ru.get(now.month, 'месяца')
            russian_date = f"{now.day} {month_name} {now.year} года"
        
        style_russian = {
            'educational': 'познавательный',
            'simple': 'простой',
            'detailed': 'подробный'
        }.get(style, style)
        
        document_title = self.book_title or "Пересказ основных идей"
        
        models_block = f"**Распознавание текста** из сканов книги, **Пересказ** и **описания иллюстраций** созданы моделью: {self.summary_model}\nИллюстрации созданы моделью: {self.image_model}"
        
        return f"""# {document_title}

**Тема:** {self.context.topic}  
**Стиль изложения:** {style_russian}  
**Дата создания:** {russian_date}

{models_block}

---

{summaries}

---

*Пересказ создан нейросетевыми моделями ИИ.*
*Подпишитесь чтобы не пропустить новые выпуски.*
"""


# === CLI ===

def main():
    parser = argparse.ArgumentParser(
        description="Процессор для создания пересказа основных идей из фрагментов текста",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python summary_processor.py input.txt -o summary.txt
  python summary_processor.py input.txt -o summary.txt --style simple
  python summary_processor.py input.txt -o summary.txt --model quality --config config.env
        """
    )
    
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл')
    parser.add_argument('--config', help='Файл конфигурации .env')
    parser.add_argument('--title', help='Название для заголовка документа')
    parser.add_argument('--style', choices=['educational', 'simple', 'detailed'], 
                       default='educational', help='Стиль изложения')
    parser.add_argument('--model', choices=['default', 'budget', 'quality'], 
                       default='default', help='Модель для использования')
    parser.add_argument('--verbose', '-v', action='store_true', help='Подробный вывод')
    
    args = parser.parse_args()
    
    try:
        # Создаём процессор
        processor = SummaryProcessor(
            config_file=args.config,
            book_title=args.title,
            model_preset=args.model
        )
        
        # Проверяем входной файл
        if not Path(args.input_file).exists():
            print(f"❌ Файл не найден: {args.input_file}")
            return 1
        
        # Обрабатываем
        report = processor.process_file(
            args.input_file,
            args.output,
            args.style
        )
        
        if report.errors:
            print(f"\n⚠️ Были ошибки: {len(report.errors)}")
        
        print(f"\n✅ Пересказ сохранён: {args.output}")
        return 0
        
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return 1
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
