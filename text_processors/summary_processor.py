#!/usr/bin/env python3
"""
Процессор для создания пересказа основных идей из фрагментов текста
Фокусируется на изложении сложных концепций простым языком для неподготовленного читателя
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
import locale

# Устанавливаем русскую локаль для форматирования дат
try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU')
    except:
        pass


class SummaryProcessor:
    def __init__(self, config_file: str = None, book_title: str = None):
        """
        Инициализация процессора с загрузкой конфигурации
        
        Args:
            config_file: Путь к файлу конфигурации .env
            book_title: Название книги для использования в документах
        """
        # Сначала загружаем базовую конфигурацию
        self.load_config(config_file)
        
        # Затем загружаем конфиг задания (если есть)
        self.load_task_config()
        
        # Сохраняем название книги
        self.book_title = book_title
        
        # Проверяем обязательные параметры
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")
        
        # Настройка API
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/summary-processor",
            "X-Title": "Summary Processor"
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
            'topic_detection_calls': 0,
            'summaries_created': 0
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
        self.chunk_size = int(os.getenv('DEFAULT_CHUNK_SIZE', '10000'))
        self.temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.3'))
        self.max_tokens = int(os.getenv('DEFAULT_MAX_TOKENS', '4000'))
        
        # Альтернативные модели
        self.budget_model = os.getenv('BUDGET_MODEL', 'meta-llama/llama-3.1-8b-instruct')
        self.quality_model = os.getenv('QUALITY_MODEL', 'openai/gpt-4o')
        
        # Модели из конфига задания (переопределяют базовые)
        self.summary_model = os.getenv('SUMMARY_MODEL', self.model)
        self.vision_model = os.getenv('VISION_MODEL', os.getenv('VISION_MODEL', ''))
        self.image_model = os.getenv('IMAGE_MODEL', 'FLUX')
        
        print(f"✅ Конфигурация загружена:")
        print(f"   Модель: {self.model}")
        print(f"   Модель для пересказа: {self.summary_model}")
        print(f"   Модель для изображений: {self.image_model}")
        print(f"   Размер фрагмента: {self.chunk_size}")
        print(f"   Температура: {self.temperature}")
    
    def load_task_config(self):
        """Загружает переменные конфига задания из окружения"""
        # Проверяем, есть ли переменные из конфига задания
        task_summary_model = os.getenv('SUMMARY_MODEL')
        task_vision_model = os.getenv('VISION_MODEL')
        task_image_model = os.getenv('IMAGE_MODEL')
        
        # Переопределяем модели из конфига задания, если они заданы
        if task_summary_model:
            self.summary_model = task_summary_model
            self.model = task_summary_model  # Используем для пересказа
            print(f"   Модель переопределена конфигом задания: {task_summary_model}")
        
        if task_vision_model:
            self.vision_model = task_vision_model
            print(f"   Модель зрения переопределена конфигом задания: {task_vision_model}")
        
        if task_image_model:
            self.image_model = task_image_model
            print(f"   Модель изображений переопределена конфигом задания: {task_image_model}")
    
    def detect_topic_with_llm(self, text_sample: str) -> Dict[str, str]:
        """
        Определяет тему и контекст текста с помощью LLM
        
        Args:
            text_sample: Образец текста для анализа (первый фрагмент)
            
        Returns:
            Словарь с информацией о теме и контексте
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

        # Используем бюджетную модель для определения темы
        topic_model = self.budget_model if hasattr(self, 'budget_model') else self.model
        
        payload = {
            "model": topic_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Низкая температура для более точного анализа
            "max_tokens": 500
        }
        
        try:
            self.stats['api_calls'] += 1
            self.stats['topic_detection_calls'] += 1
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result['choices'][0]['message']['content'].strip()
                
                # Обновляем статистику токенов
                if 'usage' in result:
                    self.stats['total_tokens_used'] += result['usage']['total_tokens']
                
                # Парсим ответ
                context_info = self.parse_topic_analysis(analysis)
                return context_info
            else:
                print(f"❌ Ошибка определения темы: {response.status_code}")
                return self.get_default_context()
                
        except Exception as e:
            print(f"❌ Ошибка при определении темы: {e}")
            return self.get_default_context()
    
    def parse_topic_analysis(self, analysis: str) -> Dict[str, str]:
        """
        Парсит ответ LLM для извлечения информации о теме
        
        Args:
            analysis: Ответ от LLM
            
        Returns:
            Словарь с информацией о теме и контексте
        """
        context_info = {
            'topic': 'Общая тема',
            'complexity': 'средняя',
            'target_audience': 'неподготовленный читатель',
            'style': 'обучающий'
        }
        
        lines = analysis.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('ТЕМА:'):
                context_info['topic'] = line.replace('ТЕМА:', '').strip()
            elif line.startswith('СЛОЖНОСТЬ:'):
                complexity = line.replace('СЛОЖНОСТЬ:', '').strip().lower()
                if complexity in ['низкая', 'средняя', 'высокая']:
                    context_info['complexity'] = complexity
            elif line.startswith('АУДИТОРИЯ:'):
                context_info['target_audience'] = line.replace('АУДИТОРИЯ:', '').strip()
            elif line.startswith('СТИЛЬ:'):
                context_info['style'] = line.replace('СТИЛЬ:', '').strip()
        
        return context_info
    
    def get_default_context(self) -> Dict[str, str]:
        """
        Возвращает контекст по умолчанию при ошибке
        
        Returns:
            Словарь с контекстом по умолчанию
        """
        return {
            'topic': 'Общая тема',
            'complexity': 'средняя',
            'target_audience': 'неподготовленный читатель',
            'style': 'обучающий'
        }
    
    def get_style_russian_name(self, style: str) -> str:
        """
        Возвращает русское название стиля изложения
        
        Args:
            style: Английское название стиля
            
        Returns:
            Русское название стиля
        """
        style_mapping = {
            'educational': 'познавательный',
            'simple': 'простой',
            'detailed': 'подробный'
        }
        return style_mapping.get(style, style)

    def detect_topic_and_context(self, text: str) -> Dict[str, str]:
        """
        Автоматически определяет тему и контекст фрагмента
        
        Args:
            text: Исходный текст
            
        Returns:
            Словарь с информацией о теме и контексте
        """
        print("🔍 Определяю тему текста с помощью LLM...")
        
        # Берем первый фрагмент для анализа темы
        chunks = self.split_text_into_chunks(text)
        if chunks:
            sample_text = chunks[0]
            context_info = self.detect_topic_with_llm(sample_text)
            print(f"✅ Тема определена: {context_info['topic']}")
        else:
            context_info = self.get_default_context()
        
        return context_info
    
    def create_summary_prompt(self, text_chunk: str, chunk_number: int, total_chunks: int, 
                             context_info: Dict[str, str], style: str = 'educational') -> str:
        """
        Создает промпт для создания пересказа
        
        Args:
            text_chunk: Фрагмент текста
            chunk_number: Номер фрагмента
            total_chunks: Общее количество фрагментов
            context_info: Информация о контексте
            style: Стиль изложения ('educational', 'simple', 'detailed')
            
        Returns:
            Промпт для нейросети
        """
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
- Тема: {context_info['topic']}
- Сложность исходного текста: {context_info['complexity']}
- Целевая аудитория: {context_info['target_audience']}

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

4. ОБУЧАЮЩИЙ ПОДХОД:
   - Объясни "почему" и "как"
   - Добавь практические примеры
   - Свяжи с повседневной жизнью
   - Сделай материал запоминающимся

{style_instructions.get(style, style_instructions['educational'])}

5. ФОРМАТ ВЫВОДА:
   - Начни с краткого введения к теме
   - Основная часть с ключевыми идеями
   - Практические выводы
   - Длина: примерно 1/3 от исходного текста
   - Отделяй заголовки пустой строкой
   - Используй маркдаун разметку

ИСХОДНЫЙ ФРАГМЕНТ:
{text_chunk}

ПЕРЕСКАЗ:"""
    
    def split_text_into_chunks(self, text: str) -> List[str]:
        """
        Разбивает текст на фрагменты для обработки
        
        Args:
            text: Исходный текст
            
        Returns:
            Список фрагментов текста
        """
        # Разбиваем по абзацам
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Если добавление параграфа превысит лимит
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
                               total_chunks: int, context_info: Dict[str, str], 
                               style: str = 'educational', retry_count: int = 3) -> Optional[str]:
        """
        Обрабатывает фрагмент текста с повторными попытками
        
        Args:
            text_chunk: Фрагмент текста
            chunk_number: Номер фрагмента
            total_chunks: Общее количество фрагментов
            context_info: Информация о контексте
            style: Стиль изложения
            retry_count: Количество попыток
            
        Returns:
            Пересказ текста или None
        """
        prompt = self.create_summary_prompt(text_chunk, chunk_number, total_chunks, context_info, style)
        
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
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result['choices'][0]['message']['content'].strip()
                    
                    # Обновляем статистику токенов
                    if 'usage' in result:
                        self.stats['total_tokens_used'] += result['usage']['total_tokens']
                    
                    return summary
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
                         style: str = 'educational', chunk_size: int = None) -> bool:
        """
        Обрабатывает текстовый файл
        
        Args:
            input_file: Входной файл
            output_file: Выходной файл
            style: Стиль изложения ('educational', 'simple', 'detailed')
            chunk_size: Размер фрагмента (опционально)
            
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
            
            # Определяем контекст
            context_info = self.detect_topic_and_context(text)
            print(f"🎯 Контекст:")
            print(f"   Тема: {context_info['topic']}")
            print(f"   Сложность: {context_info['complexity']}")
            print(f"   Стиль: {style}")
            
            # Устанавливаем размер фрагмента
            if chunk_size:
                self.chunk_size = chunk_size
            
            # Разбиваем на фрагменты
            chunks = self.split_text_into_chunks(text)
            self.stats['total_chunks'] = len(chunks)
            print(f"🔪 Разбито на {len(chunks)} фрагментов")
            
            # Обрабатываем каждый фрагмент
            summaries = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"🔄 Обрабатываю фрагмент {i}/{len(chunks)} ({len(chunk)} символов)...")
                
                summary = self.process_chunk_with_retry(chunk, i, len(chunks), context_info, style)
                
                if summary:
                    summaries.append(f"## Фрагмент {i}\n\n{summary}")
                    self.stats['processed_chunks'] += 1
                    self.stats['total_characters'] += len(summary)
                    self.stats['summaries_created'] += 1
                    print(f"✅ Фрагмент {i} обработан успешно")
                else:
                    print(f"❌ Ошибка обработки фрагмента {i}")
                    self.stats['failed_chunks'] += 1
                
                # Пауза между запросами
                if i < len(chunks):
                    time.sleep(2)
            
            # Форматируем дату по-русски
            now = datetime.now()
            try:
                russian_date = now.strftime('%d %B %Y года')
            except:
                # Fallback: ручное форматирование
                months_ru = {
                    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
                    5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
                    9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
                }
                month_name = months_ru.get(now.month, 'месяца')
                russian_date = f"{now.day} {month_name} {now.year} года"
            
            # Получаем русское название стиля
            style_russian = self.get_style_russian_name(style)
            
            # Создаем блок с моделями
            models_block = f"**Распознавание текста** из сканов книги, **Пересказ** и **описания иллюстраций** созданы моделью: {self.summary_model}\nИллюстрации созданы моделью: {self.image_model}"
            
            # Определяем заголовок документа
            document_title = self.book_title if self.book_title else "Пересказ основных идей"
            
            # Создаем итоговый документ
            final_content = f"""# {document_title}

**Тема:** {context_info['topic']}  
**Стиль изложения:** {style_russian}  
**Количество фрагментов:** {len(chunks)}  
**Дата создания:** {russian_date}

{models_block}

---

{chr(10).join(summaries)}

---

*Пересказ создан нейросетевыми моделями ИИ.*
*Подпишитесь чтобы не пропустить новые выпуски.*
"""
            
            # Сохраняем результат
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
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
        print(f"Всего фрагментов: {self.stats['total_chunks']}")
        print(f"Обработано успешно: {self.stats['processed_chunks']}")
        print(f"Ошибок: {self.stats['failed_chunks']}")
        print(f"Создано пересказов: {self.stats['summaries_created']}")
        print(f"API вызовов (всего): {self.stats['api_calls']}")
        print(f"  - Определение темы: {self.stats['topic_detection_calls']}")
        print(f"  - Создание пересказов: {self.stats['api_calls'] - self.stats['topic_detection_calls']}")
        print(f"Использовано токенов: {self.stats['total_tokens_used']:,}")
        print(f"Время обработки: {self.stats['processing_time']:.1f} сек")
        print(f"Размер результата: {self.stats['total_characters']:,} символов")
        
        if self.stats['total_chunks'] > 0:
            success_rate = (self.stats['processed_chunks'] / self.stats['total_chunks']) * 100
            print(f"Процент успешного создания: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Процессор для создания пересказа основных идей из фрагментов текста",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python summary_processor.py input.txt -o summary.txt
  python summary_processor.py input.txt -o summary.txt --style simple
  python summary_processor.py input.txt -o summary.txt --style detailed --chunk-size 8000
  python summary_processor.py input.txt -o summary.txt --config config.env
        """
    )
    
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл')
    parser.add_argument('--config', help='Файл конфигурации .env')
    parser.add_argument('--title', help='Название для заголовка документа (по умолчанию: "Пересказ основных идей")')
    parser.add_argument('--style', choices=['educational', 'simple', 'detailed'], 
                       default='educational', help='Стиль изложения')
    parser.add_argument('--chunk-size', type=int, help='Размер фрагмента в символах')
    parser.add_argument('--model', choices=['default', 'budget', 'quality'], 
                       default='default', help='Модель для использования')
    
    args = parser.parse_args()
    
    try:
        # Создаем процессор
        processor = SummaryProcessor(args.config, book_title=args.title)
        
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
            args.style,
            args.chunk_size
        )
        
        if success:
            print(f"\n✅ Обработка завершена!")
            print(f"📄 Пересказ сохранен в: {args.output}")
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