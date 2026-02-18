#!/usr/bin/env python3
"""
Унифицированный клиент для OpenRouter API.

Используется всеми процессорами проекта вместо дублирования кода.
Поддерживает retry, rate limiting и обработку ошибок.

Использование:
    from utils.openrouter_client import OpenRouterClient

    client = OpenRouterClient()
    response = client.chat("Привет, как дела?")
    response = client.chat_with_system("Ты помощник", "Вопрос")
"""

import os
import time
import json
import requests
from typing import Optional, Dict, List, Any, Generator
from dataclasses import dataclass
from pathlib import Path

from .config_loader import ConfigLoader, get_config


@dataclass
class ChatMessage:
    """Сообщение в чате."""
    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class ChatResponse:
    """Ответ от API."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    raw_response: Dict[str, Any]


class OpenRouterClient:
    """
    Унифицированный клиент для OpenRouter API.

    Заменяет дублированный код API-вызовов в 10+ файлах проекта.
    Поддерживает:
    - Прозрачную авторизацию
    - Retry с экспоненциальной задержкой
    - Rate limiting
    - Stream-режим
    - Подсчёт токенов и стоимости

    Examples:
        # Простейшее использование
        client = OpenRouterClient()
        response = client.chat("Расскажи о себе")

        # Системный промпт
        response = client.chat_with_system(
            system="Ты эксперт по Python",
            user="Как работают декораторы?"
        )

        # Потоковый вывод
        for chunk in client.chat_stream("Напиши стих"):
            print(chunk, end='', flush=True)

        # С историей сообщений
        messages = [
            ChatMessage(role="user", content="Привет"),
            ChatMessage(role="assistant", content="Привет! Чем помочь?"),
            ChatMessage(role="user", content="Расскажи о Python"),
        ]
        response = client.chat_messages(messages)
    """

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"
    DEFAULT_MAX_TOKENS = 4000
    DEFAULT_TEMPERATURE = 0.7
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # Базовая задержка в секундах

    def __init__(
        self,
        config: Optional[ConfigLoader] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Инициализация клиента.

        Args:
            config: Экземпляр ConfigLoader (если None - используется глобальный)
            api_key: API ключ (если None - из конфигурации)
            base_url: Base URL API (если None - из конфигурации)
            model: Модель по умолчанию
        """
        self.config = config or get_config()

        # Загружаем настройки
        or_config = self.config.get_openrouter_config()

        self.api_key = api_key or or_config['api_key']
        self.base_url = base_url or or_config['base_url']
        self.default_model = model or or_config['default_model'].name

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **or_config['headers']
        }

        # Статистика
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    def _make_request(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> requests.Response:
        """
        Выполняет запрос к API с retry-логикой.

        Args:
            messages: Список сообщений
            model: Модель для использования
            max_tokens: Максимум токенов
            temperature: Температура генерации
            stream: Потоковый режим
            **kwargs: Дополнительные параметры

        Returns:
            Response объект
        """
        model = model or self.default_model
        max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }

        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=120,
                    stream=stream
                )

                # Успешный ответ
                if response.status_code == 200:
                    self.total_requests += 1
                    return response

                # Обработка ошибок
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass

                # Rate limit - ждём дольше
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', 60)
                    wait_time = int(retry_after) if retry_after.isdigit() else 60
                    print(f"⚠️ Rate limited. Ждём {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue

                # Ошибка авторизации - не retry
                if response.status_code == 401:
                    raise ValueError(f"Ошибка авторизации: {error_data}")

                # Другие ошибки
                error_msg = error_data.get('error', {}).get('message', response.text)
                print(f"❌ Ошибка API (попытка {attempt + 1}/{self.MAX_RETRIES}): {response.status_code} - {error_msg}")

                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_DELAY * (2 ** attempt)  # Экспоненциальная задержка
                    print(f"   Повтор через {wait} секунд...")
                    time.sleep(wait)

                last_error = error_msg

            except requests.exceptions.Timeout:
                print(f"⏱️ Таймаут запроса (попытка {attempt + 1}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_DELAY * (2 ** attempt)
                    time.sleep(wait)
                last_error = "Timeout"

            except requests.exceptions.ConnectionError as e:
                print(f"🌐 Ошибка соединения (попытка {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_DELAY * (2 ** attempt)
                    time.sleep(wait)
                last_error = str(e)

        raise RuntimeError(f"Не удалось выполнить запрос после {self.MAX_RETRIES} попыток: {last_error}")

    def chat(
        self,
        user_message: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Простой чат-запрос.

        Args:
            user_message: Сообщение пользователя
            model: Модель (опционально)
            max_tokens: Максимум токенов
            temperature: Температура

        Returns:
            Текст ответа
        """
        messages = [{"role": "user", "content": user_message}]
        response = self._make_request(messages, model, max_tokens, temperature, **kwargs)

        data = response.json()
        content = data['choices'][0]['message']['content']

        # Обновляем статистику
        if 'usage' in data:
            self.total_tokens += data['usage'].get('total_tokens', 0)

        return content

    def chat_with_system(
        self,
        system: str,
        user: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Чат с системным промптом.

        Args:
            system: Системный промпт
            user: Сообщение пользователя
            model: Модель
            max_tokens: Максимум токенов
            temperature: Температура

        Returns:
            Текст ответа
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        response = self._make_request(messages, model, max_tokens, temperature, **kwargs)

        data = response.json()
        content = data['choices'][0]['message']['content']

        if 'usage' in data:
            self.total_tokens += data['usage'].get('total_tokens', 0)

        return content

    def chat_messages(
        self,
        messages: List[Any],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ChatResponse:
        """
        Чат с полной историей сообщений.

        Args:
            messages: Список сообщений (словари или ChatMessage объекты)
            model: Модель
            max_tokens: Максимум токенов
            temperature: Температура

        Returns:
            ChatResponse с полными данными
        """
        # Конвертируем ChatMessage в словари если нужно
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                formatted_messages.append({"role": msg.role, "content": msg.content})
            elif isinstance(msg, dict):
                formatted_messages.append(msg)
            else:
                raise ValueError(f"Неподдерживаемый тип сообщения: {type(msg)}")

        response = self._make_request(formatted_messages, model, max_tokens, temperature, **kwargs)
        data = response.json()

        content = data['choices'][0]['message']['content']
        usage = data.get('usage', {})
        finish_reason = data['choices'][0].get('finish_reason', 'unknown')
        response_model = data.get('model', model or self.default_model)

        if usage:
            self.total_tokens += usage.get('total_tokens', 0)

        return ChatResponse(
            content=content,
            model=response_model,
            usage=usage,
            finish_reason=finish_reason,
            raw_response=data
        )

    def chat_stream(
        self,
        user_message: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Потоковый чат.

        Yields:
            Чанки текста по мере генерации
        """
        messages = [{"role": "user", "content": user_message}]
        response = self._make_request(messages, model, max_tokens, temperature, stream=True, **kwargs)

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику использования."""
        return {
            'total_requests': self.total_requests,
            'total_tokens': self.total_tokens,
            'estimated_cost': self.total_cost,
        }

    def __repr__(self) -> str:
        return f"OpenRouterClient(model={self.default_model}, requests={self.total_requests})"


# Глобальный экземпляр для удобства
_global_client: Optional[OpenRouterClient] = None


def get_client(config: Optional[ConfigLoader] = None, reload: bool = False) -> OpenRouterClient:
    """
    Получает глобальный экземпляр клиента.

    Args:
        config: ConfigLoader (опционально)
        reload: Принудительно пересоздать

    Returns:
        Глобальный экземпляр OpenRouterClient
    """
    global _global_client

    if _global_client is None or reload:
        _global_client = OpenRouterClient(config)

    return _global_client


# === CLI интерфейс для тестирования ===
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Тестирование OpenRouter API")
    parser.add_argument("prompt", help="Промпт для отправки")
    parser.add_argument("--model", help="Модель для использования")
    parser.add_argument("--system", help="Системный промпт")
    parser.add_argument("--stream", action="store_true", help="Потоковый режим")
    parser.add_argument("--max-tokens", type=int, default=1000, help="Максимум токенов")
    parser.add_argument("--temperature", type=float, default=0.7, help="Температура")

    args = parser.parse_args()

    client = OpenRouterClient()

    print(f"🤖 Модель: {args.model or client.default_model}")
    print(f"📝 Промпт: {args.prompt[:100]}...")
    print()

    if args.stream:
        print("📤 Ответ (stream):")
        for chunk in client.chat_stream(
            args.prompt,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature
        ):
            print(chunk, end='', flush=True)
        print()
    elif args.system:
        print(f"📋 Системный промпт: {args.system[:100]}...")
        response = client.chat_with_system(
            system=args.system,
            user=args.prompt,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature
        )
        print(f"📤 Ответ:\n{response}")
    else:
        response = client.chat(
            args.prompt,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature
        )
        print(f"📤 Ответ:\n{response}")

    print()
    print(f"📊 Статистика: {client.get_stats()}")
