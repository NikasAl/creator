#!/usr/bin/env python3
"""
Text segmenter for thematic analysis of transcribed text.
Uses LLM to split text into meaningful thematic blocks.
"""

import os
import json
import time
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dotenv import load_dotenv


class TextSegmenter:
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize text segmenter
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.load_config()
        
        # Statistics
        self.stats = {
            'api_calls': 0,
            'total_tokens_used': 0,
            'segments_created': 0
        }
    
    def load_config(self):
        """Load configuration from environment or config file"""
        try:
            # Сначала загружаем базовый config.env (если существует)
            base_config = Path('config.env')
            if base_config.exists():
                load_dotenv(base_config, override=False)
            
            # Затем загружаем конфиг задания (если указан), переопределяя значения
            if self.config_file:
                config_path = Path(self.config_file)
                if config_path.exists():
                    load_dotenv(config_path, override=True)
            
            # Если конфиг не указан, пытаемся загрузить .env в текущей директории
            if not self.config_file:
                load_dotenv(override=False)
        except ImportError:
            pass
        
        # API configuration
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        
        # Model configuration
        self.model = os.getenv('DEFAULT_MODEL', 'anthropic/claude-3.5-sonnet')
        self.budget_model = os.getenv('BUDGET_MODEL', 'meta-llama/llama-3.1-8b-instruct')
        self.quality_model = os.getenv('QUALITY_MODEL', 'openai/gpt-4o')
        
        # Processing parameters
        self.temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.3'))
        self.max_tokens = int(os.getenv('DEFAULT_MAX_TOKENS', '4000'))
        # Максимальное количество токенов для входного текста при сегментации
        # Если текст превышает этот лимит, он будет разбит на части
        self.max_input_tokens = int(os.getenv('MAX_TOKENS', '30000'))
        
        # Headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/bookreader",
            "X-Title": "Text Segmenter"
        }
    
    def _call_llm(self, prompt: str, system: Optional[str] = None, 
                  model: Optional[str] = None, retry_count: int = 3,
                  max_tokens: Optional[int] = None) -> Optional[str]:
        """
        Call LLM API with retry logic
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            model: Model to use (optional)
            retry_count: Number of retry attempts
            max_tokens: Maximum tokens for response (optional, defaults to self.max_tokens)
            
        Returns:
            LLM response or None
        """
        payload = {
            "model": model or self.model,
            "messages": [],
            "temperature": self.temperature,
            "max_tokens": max_tokens or self.max_tokens
        }
        
        if system:
            payload["messages"].append({"role": "system", "content": system})
        payload["messages"].append({"role": "user", "content": prompt})
        
        for attempt in range(retry_count):
            try:
                self.stats["api_calls"] += 1
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=120
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    
                    # Update token usage statistics
                    if "usage" in data:
                        self.stats["total_tokens_used"] += data["usage"].get("total_tokens", 0)
                    
                    return content
                elif response.status_code == 429:
                    wait_time = 2 ** (attempt + 1)
                    print(f"⏳ Rate limit, ожидание {wait_time} секунд...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Ошибка API (попытка {attempt + 1}): {response.status_code}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)
                        
            except Exception as e:
                print(f"❌ Ошибка запроса (попытка {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def estimate_tokens(self, text: str) -> int:
        """
        Оценивает количество токенов в тексте
        Примерно 1 токен ≈ 4 символа для русского текста
        
        Args:
            text: Текст для оценки
            
        Returns:
            Приблизительное количество токенов
        """
        # Грубая оценка: ~4 символа на токен для русского текста
        return len(text) // 4
    
    def load_transcript_json(self, transcript_json_path: str) -> Optional[Dict[str, Any]]:
        """
        Загружает transcript.json для получения таймстемпов
        
        Args:
            transcript_json_path: Путь к transcript.json
            
        Returns:
            Данные транскрипции или None
        """
        try:
            path = Path(transcript_json_path)
            if not path.exists():
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем, что есть сегменты с таймстемпами
            if 'segments' in data and len(data['segments']) > 0:
                if 'start' in data['segments'][0] and 'end' in data['segments'][0]:
                    print(f"✅ Загружен transcript.json с таймстемпами: {len(data['segments'])} сегментов")
                    return data
            
            return None
            
        except Exception as e:
            print(f"⚠️ Не удалось загрузить transcript.json: {e}")
            return None
    
    def find_text_position_in_transcript(self, search_text: str, transcript_data: Dict[str, Any]) -> Optional[tuple]:
        """
        Находит позицию текста в транскрипции и возвращает start и end времена
        
        Args:
            search_text: Текст для поиска (может быть частью)
            transcript_data: Данные транскрипции из transcript.json
            
        Returns:
            Кортеж (start_time, end_time) в секундах или None
        """
        if not transcript_data or 'segments' not in transcript_data:
            return None
        
        segments = transcript_data['segments']
        full_text = transcript_data.get('text', '')
        
        # Нормализуем текст для поиска (убираем лишние пробелы)
        search_text_normalized = ' '.join(search_text.split())
        full_text_normalized = ' '.join(full_text.split())
        
        # Ищем начало текста
        start_pos = full_text_normalized.find(search_text_normalized)
        if start_pos == -1:
            # Пробуем найти по первым словам
            first_words = ' '.join(search_text_normalized.split()[:10])
            start_pos = full_text_normalized.find(first_words)
            if start_pos == -1:
                return None
        
        # Вычисляем относительную позицию
        text_ratio_start = start_pos / len(full_text_normalized) if len(full_text_normalized) > 0 else 0
        text_ratio_end = (start_pos + len(search_text_normalized)) / len(full_text_normalized) if len(full_text_normalized) > 0 else 0
        
        # Находим общее время транскрипции
        if not segments:
            return None
        
        # Находим первое и последнее время
        first_start = segments[0].get('start', 0)
        last_end = segments[-1].get('end', 0)
        
        # Вычисляем время на основе пропорции текста
        total_duration = last_end - first_start
        
        start_time = first_start + (text_ratio_start * total_duration)
        end_time = first_start + (text_ratio_end * total_duration)
        
        return (start_time, end_time)
    
    def format_time(self, seconds: float) -> str:
        """
        Форматирует время в формат HH:MM:SS
        
        Args:
            seconds: Время в секундах
            
        Returns:
            Строка формата HH:MM:SS
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def assign_timestamps_to_segments(self, segments: List[Dict[str, Any]], 
                                      transcript_data: Optional[Dict[str, Any]],
                                      full_text: str) -> List[Dict[str, Any]]:
        """
        Назначает таймстемпы сегментам на основе transcript.json
        
        Args:
            segments: Список сегментов с текстом
            transcript_data: Данные транскрипции из transcript.json
            full_text: Полный текст транскрипции
            
        Returns:
            Список сегментов с заполненными start_time и end_time
        """
        if not transcript_data:
            return segments
        
        print("🕐 Вычисляем таймстемпы для сегментов...")
        
        # Создаем индекс текста для более точного поиска
        full_text_normalized = ' '.join(full_text.split())
        current_pos = 0
        
        for segment in segments:
            content = segment.get('content', '')
            if not content:
                continue
            
            # Ищем позицию контента в полном тексте
            content_normalized = ' '.join(content.split())
            
            # Ищем от текущей позиции
            search_start = full_text_normalized.find(content_normalized, current_pos)
            
            if search_start == -1:
                # Пробуем найти по первым словам
                first_words = ' '.join(content_normalized.split()[:5])
                search_start = full_text_normalized.find(first_words, current_pos)
            
            if search_start == -1:
                # Не нашли - пропускаем
                continue
            
            # Вычисляем относительную позицию
            text_ratio_start = search_start / len(full_text_normalized) if len(full_text_normalized) > 0 else 0
            text_ratio_end = (search_start + len(content_normalized)) / len(full_text_normalized) if len(full_text_normalized) > 0 else 0
            
            # Находим общее время из transcript
            transcript_segments = transcript_data.get('segments', [])
            if not transcript_segments:
                continue
            
            first_start = transcript_segments[0].get('start', 0)
            last_end = transcript_segments[-1].get('end', 0)
            total_duration = last_end - first_start
            
            # Вычисляем время
            start_time_seconds = first_start + (text_ratio_start * total_duration)
            end_time_seconds = first_start + (text_ratio_end * total_duration)
            
            # Форматируем время
            segment['start_time'] = self.format_time(start_time_seconds)
            segment['end_time'] = self.format_time(end_time_seconds)
            
            # Обновляем текущую позицию для следующего поиска
            current_pos = search_start + len(content_normalized)
        
        return segments
    
    def split_text_into_chunks(self, text: str, estimated_prompt_tokens: int = 500) -> List[str]:
        """
        Разбивает текст на части, если он превышает max_input_tokens
        
        Args:
            text: Текст для разбиения
            estimated_prompt_tokens: Оценочное количество токенов в промпте (без текста)
            
        Returns:
            Список частей текста
        """
        text_tokens = self.estimate_tokens(text)
        # Учитываем размер промпта при расчете
        available_tokens = self.max_input_tokens - estimated_prompt_tokens
        
        if text_tokens <= available_tokens:
            return [text]
        
        print(f"📊 Текст превышает лимит ({text_tokens} токенов > {available_tokens} доступных)")
        print(f"   Разбиваем на части по ~{available_tokens} токенов...")
        
        chunks = []
        # Приблизительный размер части в символах
        chunk_size_chars = available_tokens * 4  # ~4 символа на токен
        
        # Разбиваем на части с небольшим перекрытием для контекста
        overlap_chars = chunk_size_chars // 10  # 10% перекрытие
        
        # Точки разрыва текста (в порядке приоритета)
        break_points = ['\n\n', '. ', '; ', '! ', '? ', ' ']
        
        start = 0
        while start < len(text):
            # Определяем конец текущей части
            ideal_end = start + chunk_size_chars
            end = min(ideal_end, len(text))
            
            # Если это последняя часть, берем весь остаток
            if end >= len(text):
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break
            
            # Ищем оптимальное место для разрыва (предпочтительно на границе предложения)
            chunk_text = text[start:ideal_end + overlap_chars]
            best_break = ideal_end - start
            
            # Ищем последнее подходящее место для разрыва
            for break_point in break_points:
                # Ищем разрыв в последних 20% части
                search_start = int(len(chunk_text) * 0.8)
                break_pos = chunk_text.rfind(break_point, search_start)
                if break_pos > 0:
                    best_break = break_pos + len(break_point)
                    break
            
            # Извлекаем часть текста
            chunk = text[start:start + best_break].strip()
            if chunk:
                chunks.append(chunk)
            
            # Для следующей части начинаем с небольшого отката для перекрытия
            if start + best_break < len(text):
                # Откатываемся немного назад для перекрытия контекста
                overlap_start = max(start, start + best_break - overlap_chars)
                # Ищем начало предложения для перекрытия
                for break_point in break_points:
                    overlap_break = text[overlap_start:start + best_break].find(break_point)
                    if overlap_break > 0:
                        overlap_start += overlap_break + len(break_point)
                        break
                start = overlap_start
            else:
                start = start + best_break
        
        print(f"   ✅ Разбито на {len(chunks)} частей")
        return chunks
    
    def merge_segments(self, all_segments: List[List[Dict[str, Any]]], original_text_length: int) -> List[Dict[str, Any]]:
        """
        Объединяет сегменты из разных частей текста
        
        Args:
            all_segments: Список списков сегментов (по одному на каждую часть)
            original_text_length: Длина оригинального текста
            
        Returns:
            Объединенный список сегментов
        """
        if not all_segments:
            return []
        
        if len(all_segments) == 1:
            return all_segments[0]
        
        merged = []
        current_index = 1
        
        for part_segments in all_segments:
            for segment in part_segments:
                # Обновляем индекс сегмента
                segment_copy = segment.copy()
                segment_copy['index'] = current_index
                merged.append(segment_copy)
                current_index += 1
        
        # Проверяем покрытие
        total_content_length = sum(len(seg.get('content', '')) for seg in merged)
        coverage = (total_content_length / original_text_length * 100) if original_text_length > 0 else 0
        
        print(f"📊 Объединено сегментов: {len(merged)}")
        print(f"📊 Покрытие текста: {coverage:.1f}%")
        
        if coverage < 80:
            print(f"⚠️ Внимание: покрытие текста менее 80% ({coverage:.1f}%)")
        
        return merged
    
    def create_segmentation_prompt(self, text: str, segments_count: int) -> str:
        """
        Create prompt for text segmentation
        
        Args:
            text: Text to segment
            segments_count: Desired number of segments
            
        Returns:
            Formatted prompt
        """
        text_length = len(text)
        estimated_chars_per_segment = text_length // segments_count
        
        return f"""Ты — эксперт по анализу текста и структурированию информации.

ЗАДАЧА: Раздели предоставленный текст на {segments_count} тематических блоков.

ТРЕБОВАНИЯ:
- Каждый блок должен содержать логически связанную информацию
- Блоки должны быть примерно равной длины (~{estimated_chars_per_segment} символов на блок)
- Сохраняй хронологический порядок, если это важно
- Каждый блок должен иметь краткое, но информативное название
- Не разрывай предложения между блоками
- Блоки должны быть самодостаточными для понимания
- ВАЖНО: Обработай ВЕСЬ предоставленный текст от начала до конца! Не останавливайся на середине.

ФОРМАТ ОТВЕТА — строго JSON:
{{
  "segments": [
    {{
      "index": 1,
      "title": "Название блока",
      "content": "Текст блока...",
      "start_time": "00:00:00",
      "end_time": "00:05:30"
    }},
    {{
      "index": 2,
      "title": "Название блока",
      "content": "Текст блока...",
      "start_time": "00:05:30",
      "end_time": "00:10:15"
    }}
  ]
}}

КРИТИЧЕСКИ ВАЖНО: 
- Верни ТОЛЬКО корректный JSON без дополнительных пояснений
- Поля start_time и end_time можно оставить пустыми (они будут вычислены автоматически)
- ОБЯЗАТЕЛЬНО обработай ВЕСЬ текст от начала до конца - все {segments_count} сегментов должны покрывать весь предоставленный текст без пропусков
- Последний сегмент должен заканчиваться на последнем предложении предоставленного текста

ТЕКСТ ДЛЯ АНАЛИЗА (всего {text_length} символов):
{text}

JSON ОТВЕТ (должен содержать ровно {segments_count} сегментов, покрывающих весь текст):"""
    
    def check_text_coverage(self, segments: List[Dict[str, Any]], full_text: str, 
                           min_coverage: float = 0.90) -> Tuple[bool, float, str]:
        """
        Проверяет покрытие текста сегментами
        
        Args:
            segments: Список сегментов
            full_text: Полный текст
            min_coverage: Минимальное покрытие в процентах (0.0-1.0)
            
        Returns:
            Кортеж (покрытие достаточное, процент покрытия, текст после последнего сегмента)
        """
        if not segments:
            return False, 0.0, full_text
        
        # Собираем весь контент из сегментов
        segments_content = ' '.join([seg.get('content', '') for seg in segments])
        
        # Нормализуем тексты для сравнения (убираем лишние пробелы)
        segments_normalized = ' '.join(segments_content.split())
        full_normalized = ' '.join(full_text.split())
        
        # Ищем позицию последнего сегмента в тексте
        last_segment_content = segments[-1].get('content', '')
        if not last_segment_content:
            return False, 0.0, full_text
        
        last_segment_normalized = ' '.join(last_segment_content.split())
        last_pos = full_normalized.find(last_segment_normalized)
        
        if last_pos >= 0:
            text_after = full_normalized[last_pos + len(last_segment_normalized):].strip()
        else:
            # Если не нашли точно, пытаемся найти по первым словам
            first_words = ' '.join(last_segment_normalized.split()[:10])
            last_pos = full_normalized.find(first_words)
            if last_pos >= 0:
                text_after = full_normalized[last_pos + len(first_words):].strip()
            else:
                text_after = full_normalized
        
        # Вычисляем покрытие
        covered_length = len(full_normalized) - len(text_after)
        coverage = covered_length / len(full_normalized) if len(full_normalized) > 0 else 0.0
        
        return coverage >= min_coverage, coverage, text_after
    
    def segment_text_chunk(self, text: str, segments_count: int, 
                          model_choice: str = "default", chunk_info: str = "") -> Optional[List[Dict[str, Any]]]:
        """
        Сегментирует одну часть текста
        
        Args:
            text: Текст для сегментации
            segments_count: Количество сегментов для создания в этой части
            model: Модель для использования
            chunk_info: Информация о части (для логирования)
            
        Returns:
            Список сегментов или None при ошибке
        """
        if not text or not text.strip():
            return None
        
        # Select model
        model = self.model
        if model_choice == "budget":
            model = self.budget_model
        elif model_choice == "quality":
            model = self.quality_model
        
        # Create prompt
        prompt = self.create_segmentation_prompt(text, segments_count)
        
        # Рассчитываем необходимое количество токенов для ответа
        # Примерно: текст / 4 (токены на символ) + промпт + запас для JSON структуры
        # Для сегментов: примерно 100-200 токенов на сегмент (заголовок + контент + JSON)
        estimated_response_tokens = segments_count * 200 + 500  # Запас для структуры JSON
        
        # Call LLM с увеличенным max_tokens
        response = self._call_llm(prompt, model=model, max_tokens=max(self.max_tokens, estimated_response_tokens))
        if not response:
            print(f"❌ Не удалось получить ответ от LLM {chunk_info}")
            return None
        
        # Parse JSON response
        try:
            # Clean response (remove code fences if present)
            if response.startswith("```") and response.endswith("```"):
                lines = response.splitlines()
                if len(lines) >= 2:
                    response = "\n".join(lines[1:-1])
            
            data = json.loads(response)
            segments = data.get("segments", [])
            
            if not segments:
                print(f"❌ LLM не создал сегменты {chunk_info}")
                return None
            
            # Validate segments
            for i, segment in enumerate(segments):
                if not isinstance(segment, dict):
                    print(f"❌ Неверный формат сегмента {i} {chunk_info}")
                    return None
                
                required_fields = ["index", "title", "content"]
                for field in required_fields:
                    if field not in segment:
                        print(f"❌ Отсутствует поле '{field}' в сегменте {i} {chunk_info}")
                        return None
            
            # Проверяем покрытие текста
            is_covered, coverage, text_after = self.check_text_coverage(segments, text, min_coverage=0.85)
            
            if not is_covered:
                remaining_chars = len(text_after)
                print(f"⚠️ Внимание {chunk_info}: покрытие текста составляет {coverage*100:.1f}% (ожидалось ≥85%)")
                print(f"   Необработанный текст: {remaining_chars} символов")
                if remaining_chars > 100:
                    print(f"   Начало необработанного текста: {text_after[:200]}...")
                    print(f"   Количество полученных сегментов: {len(segments)}, ожидалось: {segments_count}")
                    
                    # Пытаемся добавить недостающий сегмент
                    if remaining_chars > 50 and len(segments) < segments_count * 2:  # Защита от бесконечного цикла
                        print(f"   Пытаемся создать дополнительный сегмент для оставшегося текста...")
                        # Создаем дополнительный сегмент из оставшегося текста
                        additional_prompt = self.create_segmentation_prompt(text_after, 1)
                        additional_response = self._call_llm(additional_prompt, model=model, max_tokens=2000)
                        
                        if additional_response:
                            try:
                                # Очистка ответа
                                if additional_response.startswith("```") and additional_response.endswith("```"):
                                    lines = additional_response.splitlines()
                                    if len(lines) >= 2:
                                        additional_response = "\n".join(lines[1:-1])
                                
                                additional_data = json.loads(additional_response)
                                additional_segments = additional_data.get("segments", [])
                                
                                if additional_segments:
                                    # Обновляем индексы дополнительных сегментов
                                    for additional_seg in additional_segments:
                                        additional_seg['index'] = len(segments) + 1
                                    segments.extend(additional_segments)
                                    print(f"   ✅ Добавлен дополнительный сегмент")
                                    
                                    # Проверяем покрытие еще раз
                                    is_covered, coverage, _ = self.check_text_coverage(segments, text, min_coverage=0.85)
                                    if is_covered:
                                        print(f"   ✅ Покрытие улучшено до {coverage*100:.1f}%")
                                    else:
                                        print(f"   ⚠️ Покрытие все еще недостаточное: {coverage*100:.1f}%")
                            except Exception as e:
                                print(f"   ⚠️ Не удалось добавить дополнительный сегмент: {e}")
            
            return segments
            
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON {chunk_info}: {e}")
            print(f"Ответ LLM: {response[:200]}...")
            return None
        except Exception as e:
            print(f"❌ Неожиданная ошибка {chunk_info}: {e}")
            return None
    
    def segment_text(self, text: str, segments_count: int, 
                    model_choice: str = "default",
                    transcript_data: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Segment text into thematic blocks
        Разбивает текст на части, если он превышает max_input_tokens
        
        Args:
            text: Text to segment
            segments_count: Number of segments to create
            model_choice: Model to use (default/budget/quality)
            transcript_data: Данные транскрипции для вычисления таймстемпов
            
        Returns:
            List of segments or None if failed
        """
        if not text or not text.strip():
            print("❌ Пустой текст для сегментации")
            return None
        
        # Select model
        model = self.model
        if model_choice == "budget":
            model = self.budget_model
        elif model_choice == "quality":
            model = self.quality_model
        
        print(f"🔍 Используемая модель: {model}")
        print(f"📊 Создаем {segments_count} тематических блоков...")
        
        # Разбиваем текст на части, если он превышает лимит
        chunks = self.split_text_into_chunks(text)
        
        if len(chunks) == 1:
            # Короткий текст - обрабатываем как раньше
            segments = self.segment_text_chunk(chunks[0], segments_count, model_choice)
            if segments:
                # Назначаем таймстемпы
                segments = self.assign_timestamps_to_segments(segments, transcript_data, text)
                self.stats["segments_created"] = len(segments)
                print(f"✅ Создано {len(segments)} тематических блоков")
            return segments
        else:
            # Длинный текст - обрабатываем по частям
            print(f"📦 Обрабатываем текст по частям ({len(chunks)} частей)...")
            
            all_segments = []
            # Распределяем количество сегментов между частями
            segments_per_chunk = max(1, segments_count // len(chunks))
            remaining_segments = segments_count - (segments_per_chunk * len(chunks))
            
            for i, chunk in enumerate(chunks):
                chunk_segments_count = segments_per_chunk
                if i < remaining_segments:
                    chunk_segments_count += 1
                
                chunk_info = f"(часть {i+1}/{len(chunks)})"
                print(f"🔄 Обрабатываем часть {i+1}/{len(chunks)}: ~{chunk_segments_count} сегментов...")
                
                chunk_segments = self.segment_text_chunk(chunk, chunk_segments_count, model_choice, chunk_info)
                
                if chunk_segments:
                    all_segments.append(chunk_segments)
                    print(f"✅ Часть {i+1} обработана: создано {len(chunk_segments)} сегментов")
                else:
                    print(f"⚠️ Часть {i+1} не обработана")
                
                # Небольшая задержка между запросами
                if i < len(chunks) - 1:
                    time.sleep(1)
            
            if not all_segments:
                print("❌ Не удалось обработать ни одну часть текста")
                return None
            
            # Объединяем сегменты из всех частей
            merged_segments = self.merge_segments(all_segments, len(text))
            
            # Назначаем таймстемпы после объединения
            merged_segments = self.assign_timestamps_to_segments(merged_segments, transcript_data, text)
            
            self.stats["segments_created"] = len(merged_segments)
            print(f"✅ Всего создано {len(merged_segments)} тематических блоков")
            
            return merged_segments
    
    def save_segments(self, segments: List[Dict[str, Any]], output_file: str) -> bool:
        """
        Save segments to JSON file
        
        Args:
            segments: List of segments
            output_file: Output file path
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create output data
            output_data = {
                "metadata": {
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "segments_count": len(segments),
                    "model_used": self.model,
                    "api_calls": self.stats["api_calls"],
                    "tokens_used": self.stats["total_tokens_used"]
                },
                "segments": segments
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Сегменты сохранены: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения сегментов: {e}")
            return False
    
    def process_text_file(self, input_file: str, output_file: str, 
                         segments_count: int, model_choice: str = "default",
                         transcript_json: Optional[str] = None) -> bool:
        """
        Process text file and create segments
        
        Args:
            input_file: Input text file
            output_file: Output JSON file
            segments_count: Number of segments
            model_choice: Model choice
            transcript_json: Optional path to transcript.json for timestamps
            
        Returns:
            True if successful
        """
        try:
            # Read input file
            input_path = Path(input_file)
            if not input_path.exists():
                print(f"❌ Файл не найден: {input_path}")
                return False
            
            text = input_path.read_text(encoding='utf-8')
            if not text.strip():
                print("❌ Файл пуст")
                return False
            
            print(f"📄 Загружен текст: {len(text):,} символов")
            
            # Загружаем transcript.json если не указан явно, пытаемся найти в той же директории
            transcript_data = None
            if transcript_json:
                transcript_data = self.load_transcript_json(transcript_json)
            else:
                # Ищем transcript.json в той же директории, что и input_file
                input_dir = input_path.parent
                transcript_path = input_dir / "transcript.json"
                if transcript_path.exists():
                    transcript_data = self.load_transcript_json(str(transcript_path))
            
            # Если transcript.json загружен, используем текст из него для более точного сопоставления
            # Иначе используем текст из input_file
            text_for_segmentation = text
            if transcript_data and 'text' in transcript_data:
                text_for_segmentation = transcript_data['text']
                print("📄 Используем текст из transcript.json для сегментации")
            
            # Segment text
            segments = self.segment_text(text_for_segmentation, segments_count, model_choice, transcript_data)
            if not segments:
                return False
            
            # Save segments
            success = self.save_segments(segments, output_file)
            if success:
                print(f"📊 Статистика:")
                print(f"   - Создано сегментов: {len(segments)}")
                print(f"   - API вызовов: {self.stats['api_calls']}")
                print(f"   - Токенов использовано: {self.stats['total_tokens_used']}")
            
            return success
            
        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Сегментация текста на тематические блоки")
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument('--output', '-o', required=True, help='Выходной JSON файл')
    parser.add_argument('--segments', '-s', type=int, default=10, help='Количество сегментов')
    parser.add_argument('--config', help='Файл конфигурации')
    parser.add_argument('--model', choices=['default', 'budget', 'quality'], 
                       default='default', help='Выбор модели')
    parser.add_argument('--transcript-json', help='Путь к transcript.json для таймстемпов')
    
    args = parser.parse_args()
    
    segmenter = TextSegmenter(args.config)
    
    success = segmenter.process_text_file(
        args.input_file,
        args.output,
        args.segments,
        args.model,
        args.transcript_json
    )
    
    if success:
        print("✅ Сегментация завершена успешно")
        return 0
    else:
        print("❌ Сегментация не удалась")
        return 1


if __name__ == "__main__":
    exit(main())
