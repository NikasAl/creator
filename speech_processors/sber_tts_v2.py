#!/usr/bin/env python3
"""
Sber SaluteSpeech TTS провайдер (рефакторенная версия).

Наследует от BaseTTS для использования:
- Унифицированного разбиения текста на чанки
- Автоматического объединения аудио
- Общей обработки ошибок

Особенности:
- Поддержка маркеров пауз [[PAUSE:секунды]]
- Высокое качество русской речи
- Макс. 3500 символов на запрос

Пример:
  python speech_processors/sber_tts_v2.py text.txt --output audio.wav
  python speech_processors/sber_tts_v2.py text.txt --output audio.wav --voice Bys_24000
"""

import uuid
import re
import io
import argparse
import logging
from typing import Optional, List, Tuple

import requests
import numpy as np
import soundfile as sf

from speech_processors.base_tts import BaseTTS, register_engine, TTSResult
from utils.config_loader import get_config


@register_engine('sber')
class SberTTS(BaseTTS):
    """
    TTS провайдер на базе Sber SaluteSpeech.
    
    Особенности:
    - Поддержка маркеров пауз [[PAUSE:X]]
    - Высокое качество синтеза
    - Несколько голосов
    - Макс. 3500 символов на запрос
    """
    
    # Доступные голоса
    VOICES = [
        'Nec_24000', 'Bys_24000', 'May_24000',
        'Nec_16000', 'Bys_16000', 'May_16000'
    ]
    
    # URL API
    OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    SYNTHESIZE_URL = "https://smartspeech.sber.ru/rest/v1/text:synthesize"
    
    def __init__(
        self,
        config=None,
        voice: str = 'Nec_24000',
        **kwargs
    ):
        """
        Инициализация Sber TTS.
        
        Args:
            config: ConfigLoader
            voice: Голос диктора
        """
        self._access_token = None
        self._token_obtained = False
        
        super().__init__(
            config=config,
            voice=voice,
            language='ru',
            max_chars=3500,  # Sber лимит
            **kwargs
        )
    
    def _get_engine_name(self) -> str:
        return 'sber'
    
    def _check_availability(self) -> None:
        """Проверяет наличие ключа API."""
        self._auth_key = self.config.get('SBER_SPEECH_KEY')
        if not self._auth_key:
            raise ValueError(
                "SBER_SPEECH_KEY не найден в конфигурации. "
                "Добавьте ключ в config.env"
            )
    
    def _get_access_token(self) -> Optional[str]:
        """Получает access token для API."""
        if self._token_obtained and self._access_token:
            return self._access_token
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {self._auth_key}"
        }
        data = {"scope": "SALUTE_SPEECH_PERS"}
        
        try:
            response = requests.post(
                self.OAUTH_URL,
                headers=headers,
                data=data,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            self._access_token = response.json().get("access_token")
            self._token_obtained = True
            return self._access_token
            
        except Exception as e:
            self.logger.error(f"Ошибка получения токена: {e}")
            return None
    
    def _synthesize_chunk(self, text: str) -> Optional[bytes]:
        """
        Синтезирует один чанк текста.
        
        Args:
            text: Текст для синтеза
            
        Returns:
            Аудио-данные или None при ошибке
        """
        token = self._get_access_token()
        if not token:
            return None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/text"
        }
        params = {"voice": self.voice, "format": "wav16"}
        
        try:
            response = requests.post(
                self.SYNTHESIZE_URL,
                headers=headers,
                data=text.strip(),
                params=params,
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            self.logger.error(f"Ошибка синтеза чанка: {e}")
            return None
    
    def synthesize(
        self,
        text: str,
        output_file: str,
        add_pauses: bool = True
    ) -> TTSResult:
        """
        Синтезирует речь из текста.
        
        Поддерживает маркеры пауз [[PAUSE:секунды]].
        
        Args:
            text: Текст для синтеза
            output_file: Путь к выходному файлу
            add_pauses: Добавлять паузы между чанками
            
        Returns:
            TTSResult с результатом
        """
        import time
        
        result = TTSResult(success=False)
        start_time = time.time()
        
        try:
            # Получаем токен
            token = self._get_access_token()
            if not token:
                result.errors.append("Не удалось получить access token")
                return result
            
            # Обрабатываем маркеры пауз
            audio_parts = []
            sample_rate = 48000  # Дефолт
            
            parts = self._split_by_pause_markers(text)
            self.logger.info(f"Обработка {len(parts)} сегментов")
            
            for i, (is_pause, content) in enumerate(parts):
                if is_pause:
                    # Генерация тишины
                    seconds = float(content)
                    self.logger.info(f"⏳ Пауза: {seconds} сек")
                    num_samples = int(seconds * sample_rate)
                    silence = np.zeros(num_samples, dtype=np.float32)
                    audio_parts.append(silence)
                else:
                    # Синтез текста
                    sub_chunks = self._split_text_for_sber(content)
                    
                    for sub_chunk in sub_chunks:
                        self.logger.info(f"🎙 Синтез ({len(sub_chunk)} симв)...")
                        audio_data = self._synthesize_chunk(sub_chunk)
                        
                        if audio_data:
                            audio, sr = sf.read(io.BytesIO(audio_data))
                            if len(audio.shape) > 1:
                                audio = audio.mean(axis=1)
                            sample_rate = sr
                            audio_parts.append(audio)
                            result.chunks_processed += 1
                            result.characters_processed += len(sub_chunk)
                            
                            # Маленькая пауза между чанками
                            if add_pauses:
                                pause = np.zeros(int(0.1 * sr), dtype=np.float32)
                                audio_parts.append(pause)
                        else:
                            result.errors.append(f"Ошибка синтеза чанка {i}")
            
            # Объединяем
            if audio_parts:
                full_audio = np.concatenate(audio_parts)
                sf.write(output_file, full_audio, sample_rate)
                result.success = True
                result.output_file = output_file
                result.duration_seconds = len(full_audio) / sample_rate
                
        except Exception as e:
            self.logger.error(f"Ошибка синтеза: {e}")
            result.errors.append(str(e))
        
        return result
    
    def _split_by_pause_markers(self, text: str) -> List[Tuple[bool, str]]:
        """
        Разбивает текст по маркерам пауз.
        
        Args:
            text: Исходный текст
            
        Returns:
            Список кортежей (is_pause, content)
        """
        parts = re.split(r'(\[\[PAUSE:\s*[\d\.]+\]\])', text)
        result = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            pause_match = re.match(r'\[\[PAUSE:\s*([\d\.]+)\]\]', part)
            if pause_match:
                result.append((True, pause_match.group(1)))
            else:
                result.append((False, part))
        
        return result
    
    def _split_text_for_sber(self, text: str) -> List[str]:
        """Разбивает текст на чанки для Sber API."""
        from utils.text_splitter import split_text_into_chunks
        return split_text_into_chunks(text, preset='tts_sber')
    
    @classmethod
    def list_voices(cls) -> List[str]:
        """Возвращает список доступных голосов."""
        return cls.VOICES


def main():
    parser = argparse.ArgumentParser(
        description='Генерация речи с помощью Sber SaluteSpeech (рефакторенная версия)'
    )
    parser.add_argument('text_file', help='Путь к текстовому файлу')
    parser.add_argument('--output', '-o', default='output.wav',
                       help='Имя выходного аудиофайла')
    parser.add_argument('--voice', '-v', default='Nec_24000',
                       choices=SberTTS.VOICES,
                       help='Голос для синтеза')
    parser.add_argument('--config', help='Файл конфигурации')
    parser.add_argument('--list-voices', action='store_true',
                       help='Показать доступные голоса')
    
    args = parser.parse_args()
    
    if args.list_voices:
        print("Доступные голоса Sber:")
        for voice in SberTTS.list_voices():
            print(f"  - {voice}")
        return 0
    
    from pathlib import Path
    
    if not Path(args.text_file).exists():
        print(f"❌ Файл не найден: {args.text_file}")
        return 1
    
    try:
        tts = SberTTS(config=get_config(args.config), voice=args.voice)
        result = tts.synthesize_file(args.text_file, args.output)
        
        if result.success:
            print(f"✅ Аудио создано: {result.output_file}")
            print(f"   Длительность: {result.duration_seconds:.1f} сек")
            print(f"   Чанков: {result.chunks_processed}")
            if result.errors:
                print(f"   ⚠️ Ошибки: {len(result.errors)}")
            return 0
        else:
            print(f"❌ Ошибка синтеза: {result.errors}")
            return 1
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
