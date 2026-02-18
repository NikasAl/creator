#!/usr/bin/env python3
"""
Базовый класс для всех процессоров проекта.

Предоставляет общую функциональность:
- Загрузка конфигурации
- Инициализация API клиентов
- Разбиение текста на чанки
- Обработка ошибок и логирование
- Отчёты о выполнении

Использование:
    from utils.base_processor import BaseProcessor

    class MyProcessor(BaseProcessor):
        def process(self, text: str) -> str:
            chunks = self.split_text(text)
            results = []
            for chunk in chunks:
                result = self.client.chat(chunk)
                results.append(result)
            return self.combine_results(results)
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod

from .config_loader import ConfigLoader, get_config
from .openrouter_client import OpenRouterClient, get_client
from .text_splitter import split_text_into_chunks, get_chunk_stats


@dataclass
class ProcessingReport:
    """Отчёт о выполнении обработки."""
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    input_size: int = 0
    output_size: int = 0
    chunks_processed: int = 0
    api_calls: int = 0
    tokens_used: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'input_file': self.input_file,
            'output_file': self.output_file,
            'input_size': self.input_size,
            'output_size': self.output_size,
            'chunks_processed': self.chunks_processed,
            'api_calls': self.api_calls,
            'tokens_used': self.tokens_used,
            'errors': self.errors,
            'duration_seconds': self.duration_seconds,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
        }


class BaseProcessor(ABC):
    """
    Базовый класс для всех процессоров проекта.

    Предоставляет:
    - Унифицированную инициализацию конфигурации
    - Готовый API клиент (OpenRouter)
    - Методы для разбиения текста
    - Логирование
    - Генерацию отчётов
    - Обработку ошибок с retry

    Examples:
        class SummaryProcessor(BaseProcessor):
            def __init__(self, config_file: str = None):
                super().__init__(config_file)
                self.style = self.config.get('SUMMARY_STYLE', default='educational')

            def process(self, text: str) -> str:
                prompt = self._build_prompt(text)
                return self.client.chat(prompt)

            def process_file(self, input_file: str, output_file: str) -> ProcessingReport:
                text = self.read_file(input_file)
                result = self.process(text)
                self.write_file(output_file, result)
                return self.create_report(input_file, output_file)
    """

    def __init__(
        self,
        config_file: Optional[str] = None,
        model: Optional[str] = None,
        model_preset: str = 'default',
        chunk_size: int = 3000,
        log_level: int = logging.INFO
    ):
        """
        Инициализация процессора.

        Args:
            config_file: Путь к файлу конфигурации
            model: Модель для использования (переопределяет preset)
            model_preset: Пресет модели ('default', 'budget', 'quality')
            chunk_size: Размер чанка для разбиения текста
            log_level: Уровень логирования
        """
        # Конфигурация
        self.config = get_config(config_file)

        # API клиент
        model_config = self.config.get_model(model_preset)
        self.model = model or model_config.name
        self.max_tokens = model_config.max_tokens
        self.temperature = model_config.temperature

        self.client = get_client(self.config)
        self.client.default_model = self.model

        # Параметры обработки
        self.chunk_size = chunk_size

        # Логирование
        self.logger = self._setup_logging(log_level)

        # Статистика
        self._report = ProcessingReport()

    def _setup_logging(self, level: int) -> logging.Logger:
        """Настраивает логирование."""
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(level)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    # === Методы для работы с текстом ===

    def split_text(
        self,
        text: str,
        max_chars: Optional[int] = None,
        preset: Optional[str] = None
    ) -> List[str]:
        """
        Разбивает текст на чанки.

        Args:
            text: Исходный текст
            max_chars: Макс. размер чанка (по умолчанию self.chunk_size)
            preset: Пресет разбиения

        Returns:
            Список чанков
        """
        max_chars = max_chars or self.chunk_size

        if preset:
            return split_text_into_chunks(text, preset=preset)

        return split_text_into_chunks(text, max_chars=max_chars)

    def read_file(self, file_path: str) -> str:
        """Читает текст из файла."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        self.logger.info(f"📖 Чтение файла: {file_path}")
        text = path.read_text(encoding='utf-8')
        self._report.input_file = str(path)
        self._report.input_size = len(text)

        return text

    def write_file(self, file_path: str, content: str) -> None:
        """Записывает текст в файл."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"💾 Запись файла: {file_path}")
        path.write_text(content, encoding='utf-8')
        self._report.output_file = str(path)
        self._report.output_size = len(content)

    # === Методы для API-вызовов ===

    def call_api(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        retry_count: int = 3
    ) -> str:
        """
        Выполняет API-вызов с retry-логикой.

        Args:
            prompt: Промпт для отправки
            system: Системный промпт (опционально)
            max_tokens: Максимум токенов
            temperature: Температура
            retry_count: Количество попыток

        Returns:
            Текст ответа
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        last_error = None

        for attempt in range(retry_count):
            try:
                if system:
                    result = self.client.chat_with_system(
                        system=system,
                        user=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                else:
                    result = self.client.chat(
                        user_message=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )

                self._report.api_calls += 1
                return result

            except Exception as e:
                last_error = e
                self.logger.warning(f"Ошибка API (попытка {attempt + 1}/{retry_count}): {e}")

                if attempt < retry_count - 1:
                    wait = 2 ** attempt  # Экспоненциальная задержка
                    self.logger.info(f"Повтор через {wait} секунд...")
                    time.sleep(wait)

        self._report.errors.append(str(last_error))
        raise last_error

    def process_chunks(
        self,
        chunks: List[str],
        process_func: Callable[[str], str],
        combine_func: Optional[Callable[[List[str]], str]] = None
    ) -> str:
        """
        Обрабатывает список чанков и объединяет результаты.

        Args:
            chunks: Список чанков
            process_func: Функция обработки одного чанка
            combine_func: Функция объединения результатов (по умолчанию join)

        Returns:
            Объединённый результат
        """
        results = []

        for i, chunk in enumerate(chunks, 1):
            self.logger.info(f"🔄 Обработка чанка {i}/{len(chunks)} ({len(chunk)} символов)...")

            try:
                result = process_func(chunk)
                results.append(result)
                self._report.chunks_processed += 1

                self.logger.info(f"✅ Чанк {i} обработан успешно")

            except Exception as e:
                self.logger.error(f"❌ Ошибка обработки чанка {i}: {e}")
                self._report.errors.append(f"Чанк {i}: {e}")
                # Можно добавить исходный текст или пропустить
                results.append(f"[Ошибка обработки: {e}]")

            # Пауза между запросами
            if i < len(chunks):
                time.sleep(0.5)

        # Объединение результатов
        if combine_func:
            return combine_func(results)

        return "\n\n".join(results)

    # === Методы для отчётов ===

    def create_report(
        self,
        input_file: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> ProcessingReport:
        """Создаёт отчёт о выполнении."""
        self._report.end_time = datetime.now()
        self._report.tokens_used = self.client.total_tokens

        if input_file:
            self._report.input_file = input_file
        if output_file:
            self._report.output_file = output_file

        return self._report

    def print_report(self) -> None:
        """Выводит отчёт в консоль."""
        report = self._report

        print("\n" + "=" * 50)
        print("📊 ОТЧЁТ О ВЫПОЛНЕНИИ")
        print("=" * 50)
        print(f"📁 Входной файл: {report.input_file or 'N/A'}")
        print(f"📁 Выходной файл: {report.output_file or 'N/A'}")
        print(f"📊 Размер входа: {report.input_size:,} символов")
        print(f"📊 Размер выхода: {report.output_size:,} символов")
        print(f"🔄 Обработано чанков: {report.chunks_processed}")
        print(f"🌐 API вызовов: {report.api_calls}")
        print(f"📝 Использовано токенов: {report.tokens_used:,}")
        print(f"⏱️ Время выполнения: {report.duration_seconds:.1f} сек")

        if report.errors:
            print(f"\n❌ Ошибки ({len(report.errors)}):")
            for error in report.errors:
                print(f"   - {error}")

        print("=" * 50)

    def save_report(self, report_file: str) -> None:
        """Сохраняет отчёт в JSON файл."""
        import json

        path = Path(report_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._report.to_dict(), f, indent=2, ensure_ascii=False)

        self.logger.info(f"📋 Отчёт сохранён: {report_file}")

    # === Абстрактные методы (должны быть реализованы в наследниках) ===

    @abstractmethod
    def process(self, text: str) -> str:
        """
        Обрабатывает текст.

        Должен быть реализован в наследниках.

        Args:
            text: Исходный текст

        Returns:
            Обработанный текст
        """
        pass

    def process_file(self, input_file: str, output_file: str, **kwargs) -> ProcessingReport:
        """
        Обрабатывает файл.

        Базовая реализация - может быть переопределена.

        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            **kwargs: Дополнительные параметры

        Returns:
            Отчёт о выполнении
        """
        self._report.start_time = datetime.now()

        # Читаем
        text = self.read_file(input_file)

        # Обрабатываем
        result = self.process(text, **kwargs)

        # Записываем
        self.write_file(output_file, result)

        # Создаём отчёт
        report = self.create_report(input_file, output_file)
        self.print_report()

        return report


# === Утилиты для CLI ===

def create_arg_parser(description: str, add_input_output: bool = True) -> 'argparse.ArgumentParser':
    """
    Создаёт базовый парсер аргументов для CLI.

    Args:
        description: Описание скрипта
        add_input_output: Добавить аргументы input/output

    Returns:
        Настроенный ArgumentParser
    """
    import argparse

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    if add_input_output:
        parser.add_argument('input_file', help='Входной файл')
        parser.add_argument('-o', '--output', required=True, help='Выходной файл')

    parser.add_argument('--config', help='Файл конфигурации')
    parser.add_argument('--model', help='Модель для использования')
    parser.add_argument('--model-preset', choices=['default', 'budget', 'quality'],
                       default='default', help='Пресет модели')
    parser.add_argument('--chunk-size', type=int, default=3000, help='Размер чанка')
    parser.add_argument('--verbose', '-v', action='store_true', help='Подробный вывод')

    return parser


if __name__ == "__main__":
    # Пример использования
    print("BaseProcessor - базовый класс для всех процессоров")
    print("См. документацию в коде для примеров использования")
