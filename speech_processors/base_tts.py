#!/usr/bin/env python3
"""
Базовый класс и абстракция для TTS-провайдеров.

Унифицирует интерфейс для всех TTS-движков:
- Alibaba TTS
- Silero (локальный)
- Sber API

Использование:
    from speech_processors.base_tts import get_tts_engine, list_engines

    # Автоматический выбор
    tts = get_tts_engine('alibaba')
    tts.synthesize(text, output_file)

    # С параметрами
    tts = get_tts_engine('silero', voice='aidar')
    tts.synthesize_file(input_file, output_file)
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from utils.config_loader import ConfigLoader, get_config
from utils.text_splitter import split_text_into_chunks


@dataclass
class TTSConfig:
    """Конфигурация TTS движка."""
    engine: str = 'alibaba'
    voice: str = 'default'
    language: str = 'ru'
    sample_rate: int = 48000
    max_chars_per_request: int = 500


@dataclass
class TTSResult:
    """Результат синтеза речи."""
    success: bool
    output_file: Optional[str] = None
    duration_seconds: float = 0.0
    characters_processed: int = 0
    chunks_processed: int = 0
    errors: List[str] = field(default_factory=list)


class BaseTTS(ABC):
    """
    Базовый класс для всех TTS-провайдеров.
    
    Определяет общий интерфейс и функциональность:
    - Разбиение текста на чанки
    - Объединение аудио
    - Логирование
    - Обработка ошибок
    
    Наследники должны реализовать:
    - _synthesize_chunk() - синтез одного чанка
    - _get_default_voice() - голос по умолчанию
    """
    
    # Конфигурации по умолчанию для разных движков
    ENGINE_CONFIGS = {
        'alibaba': TTSConfig(
            engine='alibaba',
            voice='Cherry',
            language='Auto',
            max_chars_per_request=500
        ),
        'silero': TTSConfig(
            engine='silero',
            voice='aidar',
            language='ru',
            max_chars_per_request=800
        ),
        'sber': TTSConfig(
            engine='sber',
            voice='Nec_24000',
            language='ru',
            max_chars_per_request=3500
        ),
    }
    
    def __init__(
        self,
        config: Optional[ConfigLoader] = None,
        voice: Optional[str] = None,
        language: str = 'ru',
        max_chars: Optional[int] = None
    ):
        """
        Инициализация TTS движка.
        
        Args:
            config: ConfigLoader (если None - используется глобальный)
            voice: Голос для синтеза
            language: Язык
            max_chars: Макс. символов на запрос
        """
        self.config = config or get_config()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Загружаем конфигурацию для движка
        engine_name = self._get_engine_name()
        engine_config = self.ENGINE_CONFIGS.get(engine_name, TTSConfig())
        
        self.voice = voice or engine_config.voice
        self.language = language or engine_config.language
        self.max_chars = max_chars or engine_config.max_chars_per_request
        
        # Проверяем доступность
        self._check_availability()
        
        self.logger.info(f"TTS движок: {engine_name}, голос: {self.voice}")
    
    @abstractmethod
    def _synthesize_chunk(self, text: str) -> Optional[bytes]:
        """
        Синтезирует один чанк текста.
        
        Args:
            text: Текст для синтеза
            
        Returns:
            Аудио-данные (bytes) или None при ошибке
        """
        pass
    
    @abstractmethod
    def _get_engine_name(self) -> str:
        """Возвращает имя движка."""
        pass
    
    def _check_availability(self) -> None:
        """Проверяет доступность движка. Переопределить при необходимости."""
        pass
    
    def _get_default_voice(self) -> str:
        """Возвращает голос по умолчанию для движка."""
        return self.ENGINE_CONFIGS.get(self._get_engine_name(), TTSConfig()).voice
    
    def synthesize(
        self,
        text: str,
        output_file: str,
        add_pauses: bool = True
    ) -> TTSResult:
        """
        Синтезирует речь из текста.
        
        Автоматически разбивает текст на чанки, синтезирует каждый,
        и объединяет результат.
        
        Args:
            text: Текст для синтеза
            output_file: Путь к выходному файлу
            add_pauses: Добавлять паузы между чанками
            
        Returns:
            TTSResult с результатом синтеза
        """
        result = TTSResult(success=False)
        start_time = time.time()
        
        try:
            # Если текст короткий - синтезируем напрямую
            if len(text) <= self.max_chars:
                audio_data = self._synthesize_chunk(text)
                if audio_data:
                    self._save_audio(audio_data, output_file)
                    result.success = True
                    result.characters_processed = len(text)
                    result.chunks_processed = 1
            else:
                # Разбиваем на чанки
                chunks = split_text_into_chunks(
                    text,
                    max_chars=self.max_chars,
                    preset=f'tts_{self._get_engine_name()}'
                )
                
                self.logger.info(f"Текст разбит на {len(chunks)} частей")
                
                audio_chunks = []
                
                for i, chunk in enumerate(chunks, 1):
                    self.logger.info(f"Синтез части {i}/{len(chunks)} ({len(chunk)} символов)...")
                    
                    try:
                        audio_data = self._synthesize_chunk(chunk)
                        if audio_data:
                            audio_chunks.append(audio_data)
                            result.chunks_processed += 1
                            result.characters_processed += len(chunk)
                        else:
                            result.errors.append(f"Чанк {i}: ошибка синтеза")
                    except Exception as e:
                        self.logger.error(f"Ошибка синтеза чанка {i}: {e}")
                        result.errors.append(f"Чанк {i}: {e}")
                    
                    # Пауза между запросами
                    if i < len(chunks):
                        time.sleep(0.5)
                
                # Объединяем аудио
                if audio_chunks:
                    self._concatenate_audio(audio_chunks, output_file, add_pauses)
                    result.success = True
            
            if result.success:
                result.output_file = output_file
                # Определяем длительность
                result.duration_seconds = self._get_audio_duration(output_file)
                
        except Exception as e:
            self.logger.error(f"Ошибка синтеза: {e}")
            result.errors.append(str(e))
        
        return result
    
    def synthesize_file(
        self,
        input_file: str,
        output_file: str,
        add_pauses: bool = True
    ) -> TTSResult:
        """
        Синтезирует речь из файла.
        
        Args:
            input_file: Путь к текстовому файлу
            output_file: Путь к выходному аудио-файлу
            add_pauses: Добавлять паузы между чанками
            
        Returns:
            TTSResult с результатом
        """
        path = Path(input_file)
        if not path.exists():
            return TTSResult(success=False, errors=[f"Файл не найден: {input_file}"])
        
        text = path.read_text(encoding='utf-8')
        return self.synthesize(text, output_file, add_pauses)
    
    def _save_audio(self, audio_data: bytes, output_file: str) -> None:
        """Сохраняет аудио-данные в файл."""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'wb') as f:
            f.write(audio_data)
    
    def _concatenate_audio(
        self,
        audio_chunks: List[bytes],
        output_file: str,
        add_pauses: bool = True
    ) -> None:
        """
        Объединяет аудио-чанки в один файл.
        
        Args:
            audio_chunks: Список аудио-данных
            output_file: Выходной файл
            add_pauses: Добавлять паузы
        """
        import numpy as np
        import soundfile as sf
        import io
        
        combined = []
        sample_rate = 48000  # По умолчанию
        
        for i, chunk_data in enumerate(audio_chunks):
            try:
                audio, sr = sf.read(io.BytesIO(chunk_data))
                sample_rate = sr
                
                # Конвертируем в моно если нужно
                if len(audio.shape) > 1:
                    audio = audio.mean(axis=1)
                
                combined.append(audio)
                
                # Добавляем паузу
                if add_pauses and i < len(audio_chunks) - 1:
                    pause_duration = int(0.3 * sr)
                    pause = np.zeros(pause_duration, dtype=np.float32)
                    combined.append(pause)
                    
            except Exception as e:
                self.logger.warning(f"Ошибка обработки чанка: {e}")
        
        if combined:
            full_audio = np.concatenate(combined)
            sf.write(output_file, full_audio, sample_rate)
            self.logger.info(f"Аудио сохранено: {output_file}")
    
    def _get_audio_duration(self, audio_file: str) -> float:
        """Возвращает длительность аудио в секундах."""
        try:
            import soundfile as sf
            info = sf.info(audio_file)
            return info.duration
        except:
            return 0.0
    
    @classmethod
    def list_voices(cls) -> List[str]:
        """Возвращает список доступных голосов."""
        return []


# === Реестр движков ===

_ENGINES: Dict[str, type] = {}


def register_engine(name: str):
    """Декоратор для регистрации TTS движка."""
    def decorator(cls):
        _ENGINES[name] = cls
        return cls
    return decorator


def get_tts_engine(
    engine: str = 'alibaba',
    config: Optional[ConfigLoader] = None,
    **kwargs
) -> BaseTTS:
    """
    Получает TTS движок по имени.
    
    Args:
        engine: Имя движка ('alibaba', 'silero', 'sber')
        config: ConfigLoader
        **kwargs: Дополнительные параметры
        
    Returns:
        Экземпляр TTS движка
        
    Raises:
        ValueError: Если движок не найден
    """
    if engine not in _ENGINES:
        available = list(_ENGINES.keys())
        raise ValueError(f"TTS движок '{engine}' не найден. Доступные: {available}")
    
    return _ENGINES[engine](config=config, **kwargs)


def list_engines() -> List[str]:
    """Возвращает список доступных TTS движков."""
    return list(_ENGINES.keys())


# === CLI ===

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Унифицированный TTS интерфейс")
    parser.add_argument("text_file", help="Текстовый файл для синтеза")
    parser.add_argument("--output", "-o", default="output.wav", help="Выходной файл")
    parser.add_argument("--engine", "-e", choices=['alibaba', 'silero', 'sber'],
                       default='alibaba', help="TTS движок")
    parser.add_argument("--voice", "-v", help="Голос")
    parser.add_argument("--language", "-l", default="ru", help="Язык")
    parser.add_argument("--list-voices", action="store_true", help="Показать голоса")
    
    args = parser.parse_args()
    
    if args.list_voices:
        print("Доступные движки:", list_engines())
        for engine in list_engines():
            voices = _ENGINES[engine].list_voices()
            if voices:
                print(f"  {engine}: {voices}")
        exit(0)
    
    try:
        tts = get_tts_engine(args.engine, voice=args.voice, language=args.language)
        result = tts.synthesize_file(args.text_file, args.output)
        
        if result.success:
            print(f"✅ Аудио создано: {result.output_file}")
            print(f"   Длительность: {result.duration_seconds:.1f} сек")
            print(f"   Чанков: {result.chunks_processed}")
        else:
            print(f"❌ Ошибка: {result.errors}")
            exit(1)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        exit(1)
