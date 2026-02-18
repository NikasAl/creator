# Speech processors package
"""
TTS-провайдеры для синтеза речи.

Доступные движки:
- AlibabaTTS: Облачный TTS от Alibaba
- SileroTTS: Локальный TTS на базе Silero
- SberTTS: Облачный TTS от Сбер (SaluteSpeech)

Использование:
    from speech_processors import get_tts_engine, list_engines
    
    tts = get_tts_engine('alibaba')
    result = tts.synthesize_file('text.txt', 'output.wav')
"""

from .base_tts import (
    BaseTTS,
    TTSConfig,
    TTSResult,
    get_tts_engine,
    list_engines,
    register_engine
)

# Рефакторенные версии (рекомендуются)
from .alibaba_tts_v2 import AlibabaTTS
from .silero_v2 import SileroTTS
from .sber_tts_v2 import SberTTS

__all__ = [
    # Базовый класс
    'BaseTTS',
    'TTSConfig',
    'TTSResult',
    # Фабричные функции
    'get_tts_engine',
    'list_engines',
    'register_engine',
    # Рефакторенные движки
    'AlibabaTTS',
    'SileroTTS',
    'SberTTS',
]
