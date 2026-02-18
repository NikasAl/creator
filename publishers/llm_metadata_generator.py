#!/usr/bin/env python3
"""
Генератор метаданных с использованием LLM
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Конфигурация для LLM"""
    api_key: str
    model: str = "meituan/longcat-flash-chat:free"
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 2000
    temperature: float = 0.3


class LLMMetadataGenerator:
    """Генератор метаданных с использованием LLM"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Инициализация генератора
        
        Args:
            config_file: Путь к файлу конфигурации .env
        """
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> LLMConfig:
        """Загружает конфигурацию LLM"""
        if self.config_file and os.path.exists(self.config_file):
            from dotenv import load_dotenv
            load_dotenv(self.config_file)
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY не найден в конфигурации")
        
        return LLMConfig(
            api_key=api_key,
            model=os.getenv('DEFAULT_MODEL', 'meituan/longcat-flash-chat:free'),
            max_tokens=int(os.getenv('DEFAULT_MAX_TOKENS', '2000')),
            temperature=float(os.getenv('DEFAULT_TEMPERATURE', '0.3'))
        )
    
    def generate_title(self, content: str, book_title: Optional[str] = None, 
                       book_author: Optional[str] = None, max_length: int = 100) -> str:
        """
        Генерирует название видео на основе контента
        
        Args:
            content: Текст контента
            book_title: Название книги
            book_author: Автор книги
            max_length: Максимальная длина названия
            
        Returns:
            Сгенерированное название
        """
        prompt = f"""Создай привлекательное название для видео на основе следующего контента.

Контент:
{content[:2000]}

Дополнительная информация:
- Название книги: {book_title or 'не указано'}
- Автор: {book_author or 'не указан'}

Верни ответ СТРОГО в JSON-формате без каких-либо пояснений, только JSON.
Схема ответа:
{{
  "title": "строка, не длиннее {max_length} символов, без кавычек и лишних символов"
}}"""

        try:
            response = self._call_llm(prompt)
            title = self._parse_json_field(response, 'title') or response.strip()
            
            # Обрезаем до максимальной длины
            if len(title) > max_length:
                title = title[:max_length-3] + "..."
            
            return title
            
        except Exception as e:
            print(f"⚠️  Ошибка генерации названия: {e}")
            # Возвращаем базовое название
            if book_title:
                return f"{book_title} - Обзор и анализ"
            return "Интересный обзор и анализ"
    
    def generate_description(self, content: str, book_title: Optional[str] = None,
                           book_author: Optional[str] = None, max_length: int = 5000) -> str:
        """
        Генерирует описание видео
        
        Args:
            content: Текст контента
            book_title: Название книги
            book_author: Автор книги
            max_length: Максимальная длина описания
            
        Returns:
            Сгенерированное описание
        """
        prompt = f"""Создай подробное описание для видео на основе следующего контента.

Контент:
{content[:3000]}

Дополнительная информация:
- Название книги: {book_title or 'не указано'}
- Автор: {book_author or 'не указан'}

Требования к описанию:
- Подробное и информативное
- Привлекает внимание зрителей
- Содержит ключевые моменты из контента
- Длина не более {max_length} символов
- На русском языке
- Включает призыв к действию (подписка, лайк, комментарий)

Верни ответ СТРОГО в JSON-формате без пояснений. Схема ответа:
{{
  "description": "строка-описание не длиннее {max_length} символов"
}}"""

        try:
            response = self._call_llm(prompt)
            description = self._parse_json_field(response, 'description') or response.strip()
            
            # Обрезаем до максимальной длины
            if len(description) > max_length:
                description = description[:max_length-3] + "..."
            
            return description
            
        except Exception as e:
            print(f"⚠️  Ошибка генерации описания: {e}")
            # Возвращаем базовое описание
            base_desc = f"Подробный разбор и анализ"
            if book_title:
                base_desc += f" книги '{book_title}'"
            if book_author:
                base_desc += f" автора {book_author}"
            return base_desc
    
    def generate_tags(self, content: str, book_title: Optional[str] = None,
                     book_author: Optional[str] = None, max_tags: int = 15) -> List[str]:
        """
        Генерирует теги для видео
        
        Args:
            content: Текст контента
            book_title: Название книги
            book_author: Автор книги
            max_tags: Максимальное количество тегов
            
        Returns:
            Список тегов
        """
        prompt = f"""Создай список тегов для видео на основе следующего контента.

Контент:
{content[:2000]}

Дополнительная информация:
- Название книги: {book_title or 'не указано'}
- Автор: {book_author or 'не указан'}

Требования к тегам:
- Релевантные содержанию
- Популярные и поисковые
- На русском языке
- Без пробелов (используй подчеркивания)
- Не более {max_tags} тегов
- Включай общие теги: аудиокнига, пересказ, образование

Верни ответ СТРОГО в JSON-формате без пояснений. Схема ответа:
{{
  "tags": ["тег1", "тег2", "..."]
}}"""

        try:
            response = self._call_llm(prompt)
            tags = self._parse_json_array(response, 'tags')
            if not tags:
                # Фоллбек: парсим как CSV, если LLM вернул текст
                tags_text = response.strip()
                tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
            
            # Ограничиваем количество
            return tags[:max_tags]
            
        except Exception as e:
            print(f"⚠️  Ошибка генерации тегов: {e}")
            # Возвращаем базовые теги
            base_tags = ["аудиокнига", "пересказ", "образование", "анализ", "обзор"]
            if book_title:
                # Добавляем слова из названия книги
                words = book_title.lower().split()
                base_tags.extend([word for word in words if len(word) > 3])
            return base_tags[:max_tags]
    
    def generate_thumbnail_prompt(self, content: str, book_title: Optional[str] = None,
                               book_author: Optional[str] = None) -> str:
        """
        Генерирует промпт для создания превью
        
        Args:
            content: Текст контента
            book_title: Название книги
            book_author: Автор книги
            
        Returns:
            Промпт для генерации превью
        """
        prompt = f"""Создай детальный промпт для генерации превью видео на основе следующего контента.

Контент:
{content[:1500]}

Дополнительная информация:
- Название книги: {book_title or 'не указано'}
- Автор: {book_author or 'не указан'}

Требования к промпту:
- Детальное описание визуального стиля
- Учитывает тематику контента
- Привлекательное и профессиональное
- Подходит для превью видео
- На английском языке (для AI генерации изображений)
- Включает стиль, освещение, композицию

Промпт:"""

        try:
            response = self._call_llm(prompt)
            thumbnail_prompt = response.strip()
            return thumbnail_prompt
            
        except Exception as e:
            print(f"⚠️  Ошибка генерации промпта превью: {e}")
            # Возвращаем базовый промпт
            base_prompt = "Professional book cover design, modern typography, elegant composition"
            if book_title:
                base_prompt += f", featuring {book_title}"
            return base_prompt
    
    def enhance_existing_metadata(self, title: str, description: str, tags: List[str],
                               content: str, book_title: Optional[str] = None,
                               book_author: Optional[str] = None) -> Dict[str, Any]:
        """
        Улучшает существующие метаданные
        
        Args:
            title: Существующее название
            description: Существующее описание
            tags: Существующие теги
            content: Контент для анализа
            book_title: Название книги
            book_author: Автор книги
            
        Returns:
            Словарь с улучшенными метаданными
        """
        enhanced = {
            'title': title,
            'description': description,
            'tags': tags,
            'suggestions': {}
        }
        
        try:
            # Анализируем существующие метаданные
            analysis_prompt = f"""Проанализируй и улучши следующие метаданные видео:

Название: {title}
Описание: {description[:1000]}
Теги: {', '.join(tags)}

Контент видео:
{content[:2000]}

Дополнительная информация:
- Название книги: {book_title or 'не указано'}
- Автор: {book_author or 'не указан'}

Предложи улучшения:
1. Более привлекательное название
2. Более подробное описание
3. Дополнительные релевантные теги
4. Призыв к действию для описания

Ответ в формате JSON:
{{
    "improved_title": "новое название",
    "improved_description": "улучшенное описание",
    "additional_tags": ["тег1", "тег2"],
    "call_to_action": "призыв к действию"
}}"""

            response = self._call_llm(analysis_prompt + "\n\nОтвет СТРОГО в JSON, без пояснений.")
            
            # Пытаемся распарсить JSON ответ (включая извлечение из текста)
            suggestions = self._parse_json_object(response)
            if suggestions:
                enhanced['suggestions'] = suggestions
            else:
                enhanced['suggestions'] = {'raw_response': response}
                
        except Exception as e:
            print(f"⚠️  Ошибка улучшения метаданных: {e}")
        
        return enhanced
    
    def _call_llm(self, prompt: str) -> str:
        """
        Вызывает LLM API
        
        Args:
            prompt: Промпт для LLM
            
        Returns:
            Ответ от LLM
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }
        
        try:
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise ValueError("Неожиданный формат ответа от LLM")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка запроса к LLM: {e}")
        except Exception as e:
            raise Exception(f"Ошибка обработки ответа LLM: {e}")
    
    def _extract_json_snippet(self, text: str) -> Optional[str]:
        """Пытается извлечь JSON-объект/массив из произвольного текста"""
        # Удаляем markdown-кодблоки, если есть
        if '```' in text:
            parts = text.split('```')
            # Ищем участок, который начинается с { или [
            for part in parts:
                part_stripped = part.strip()
                if part_stripped.startswith('{') or part_stripped.startswith('['):
                    return part_stripped
        
        # Ищем первую скобку и последнюю закрывающую
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        
        return None
    
    def _parse_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """Парсит JSON-объект из текста (с извлечением при необходимости)"""
        try:
            return json.loads(text)
        except Exception:
            snippet = self._extract_json_snippet(text)
            if snippet:
                try:
                    return json.loads(snippet)
                except Exception:
                    return None
        return None
    
    def _parse_json_field(self, text: str, field: str) -> Optional[str]:
        """Извлекает строковое поле из JSON-ответа; возвращает None при неудаче"""
        obj = self._parse_json_object(text)
        if isinstance(obj, dict) and isinstance(obj.get(field), str):
            return obj[field].strip()
        return None
    
    def _parse_json_array(self, text: str, field: str) -> List[str]:
        """Извлекает массив строк из JSON-ответа; возвращает [] при неудаче"""
        obj = self._parse_json_object(text)
        if isinstance(obj, dict) and isinstance(obj.get(field), list):
            items = [str(x).strip().replace(' ', '_') for x in obj[field] if str(x).strip()]
            # фильтруем дубликаты и пустые
            unique: List[str] = []
            for it in items:
                if it and it not in unique:
                    unique.append(it)
            return unique
        return []
    
    def log_info(self, message: str):
        """Логирует информационное сообщение"""
        print(f"ℹ️  {message}")
    
    def log_success(self, message: str):
        """Логирует сообщение об успехе"""
        print(f"✅ {message}")
    
    def log_error(self, message: str):
        """Логирует сообщение об ошибке"""
        print(f"❌ {message}")
