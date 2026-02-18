#!/usr/bin/env python3
"""
Alibaba Cloud TTS - реестровая версия.

РЕФАКТОРИНГ: Использует BaseTTS для унификации интерфейса.
Удалено ~50 строк дублированного кода разбиения текста.

Использование:
    from speech_processors.alibaba_tts_v2 import AlibabaTTS
    
    tts = AlibabaTTS()
    tts.synthesize(text, "output.wav")
"""

import os
import io
import dashscope
import requests
import numpy as np
import soundfile as sf
from typing import Optional

from speech_processors.base_tts import BaseTTS, register_engine
from utils.config_loader import get_config


@register_engine('alibaba')
class AlibabaTTS(BaseTTS):
    """
    TTS через Alibaba Cloud Qwen TTS.
    
    Голоса:
    - Cherry (женский, рекомендуемый)
    - Ethan (мужской)
    - Luna (женский)
    - Marcus (мужской)
    """
    
    AVAILABLE_VOICES = ['Cherry', 'Ethan', 'Luna', 'Marcus', 
                       'zhichu', 'zhitian', 'zhiyan', 'zhiwei']
    
    def __init__(
        self,
        config=None,
        voice: str = 'Cherry',
        language: str = 'Auto',
        **kwargs
    ):
        """
        Инициализация Alibaba TTS.
        
        Args:
            config: ConfigLoader
            voice: Голос для синтеза
            language: Язык ('Auto', 'ru', 'en', 'zh')
        """
        self.config = config or get_config()
        
        # Загружаем API ключ
        self.api_key = self.config.get('ALIBABA_API_KEY')
        if not self.api_key:
            raise ValueError("ALIBABA_API_KEY не найден в конфигурации")
        
        # Настраиваем dashscope
        base_url = self.config.get('ALIBABA_BASE_URL', 
                                   default='https://dashscope-intl.aliyuncs.com/api/v1')
        dashscope.base_http_api_url = base_url
        
        # Инициализируем базовый класс
        # Alibaba имеет лимит 500 символов на запрос
        super().__init__(
            config=self.config,
            voice=voice,
            language=language,
            max_chars=500
        )
    
    def _get_engine_name(self) -> str:
        return 'alibaba'
    
    def _synthesize_chunk(self, text: str) -> Optional[bytes]:
        """Синтезирует один чанк текста через Alibaba API."""
        try:
            response = dashscope.MultiModalConversation.call(
                model="qwen3-tts-flash-2025-09-18",
                api_key=self.api_key,
                text=text,
                voice=self.voice,
                language_type=self.language,
                stream=False
            )
            
            if response.status_code == 200:
                # Получаем URL к аудиофайлу
                audio_url = response.output.audio.url
                
                # Скачиваем аудиофайл
                audio_response = requests.get(audio_url, timeout=30)
                audio_response.raise_for_status()
                
                return audio_response.content
            else:
                self.logger.error(f"Ошибка Alibaba TTS: {response.code} - {response.message}")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка Alibaba TTS: {e}")
            return None
    
    @classmethod
    def list_voices(cls) -> list:
        """Возвращает список доступных голосов."""
        return cls.AVAILABLE_VOICES


# === CLI для обратной совместимости ===

def synthesize_speech(text: str, voice: str, language: str, output_file: str) -> bool:
    """
    Функция для обратной совместимости с alibaba_tts.py
    
    Args:
        text: Текст для синтеза
        voice: Голос
        language: Язык
        output_file: Выходной файл
        
    Returns:
        True если успешно
    """
    tts = AlibabaTTS(voice=voice, language=language)
    result = tts.synthesize(text, output_file)
    return result.success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Alibaba Cloud TTS (рефакторинг)")
    parser.add_argument("text_file", help="Текстовый файл для синтеза")
    parser.add_argument("--voice", default="Cherry", help="Голос для синтеза")
    parser.add_argument("--language", default="Auto", help="Язык для синтеза")
    parser.add_argument("--output", default="output.wav", help="Выходной файл")
    parser.add_argument("--list-voices", action="store_true", help="Показать голоса")
    
    args = parser.parse_args()
    
    if args.list_voices:
        print("Доступные голоса Alibaba TTS:")
        for voice in AlibabaTTS.list_voices():
            print(f"  - {voice}")
        exit(0)
    
    try:
        # Читаем текст
        with open(args.text_file, "r", encoding="utf-8") as f:
            text = f.read()
        print(f"📄 Текст загружен ({len(text)} символов)")
        
        # Синтезируем
        tts = AlibabaTTS(voice=args.voice, language=args.language)
        result = tts.synthesize(text, args.output)
        
        if result.success:
            print(f"✅ Аудио создано: {result.output_file}")
            print(f"   Длительность: {result.duration_seconds:.1f} сек")
            print(f"   Обработано чанков: {result.chunks_processed}")
        else:
            print(f"❌ Ошибки: {result.errors}")
            exit(1)
            
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        exit(1)
    except FileNotFoundError:
        print(f"❌ Файл не найден: {args.text_file}")
        exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        exit(1)
