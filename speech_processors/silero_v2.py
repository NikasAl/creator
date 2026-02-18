#!/usr/bin/env python3
"""
Silero TTS провайдер (рефакторенная версия).

Наследует от BaseTTS для использования:
- Унифицированного разбиения текста на чанки
- Автоматического объединения аудио
- Общей обработки ошибок

Пример:
  python speech_processors/silero_v2.py --input text.txt --output audio.wav
  python speech_processors/silero_v2.py --input text.txt --output audio.wav --speaker aidar
"""

import argparse
import logging
from typing import Optional, List

from speech_processors.base_tts import BaseTTS, register_engine, TTSResult


@register_engine('silero')
class SileroTTS(BaseTTS):
    """
    TTS провайдер на базе Silero.
    
    Особенности:
    - Локальная работа (без API)
    - Высокое качество русской речи
    - Несколько голосов
    - Макс. 800 символов на запрос
    """
    
    # Доступные голоса
    VOICES = ['xenia', 'aidar', 'baya', 'kseniya', 'eugene']
    
    # Частоты дискретизации
    SAMPLE_RATES = [8000, 16000, 24000, 48000]
    
    def __init__(
        self,
        config=None,
        voice: str = 'aidar',
        sample_rate: int = 48000,
        **kwargs
    ):
        """
        Инициализация Silero TTS.
        
        Args:
            config: ConfigLoader
            voice: Голос диктора
            sample_rate: Частота дискретизации
        """
        self.sample_rate = sample_rate
        self._model = None
        self._model_loaded = False
        
        super().__init__(
            config=config,
            voice=voice,
            language='ru',
            max_chars=800,  # Silero лимит
            **kwargs
        )
    
    def _get_engine_name(self) -> str:
        return 'silero'
    
    def _check_availability(self) -> None:
        """Проверяет доступность Silero."""
        try:
            from silero import silero_tts
            self.logger.debug("Silero доступен")
        except ImportError:
            raise ImportError(
                "Silero не установлен. Установите: pip install silero"
            )
    
    def _load_model(self):
        """Ленивая загрузка модели."""
        if not self._model_loaded:
            self.logger.info("Загрузка модели Silero TTS...")
            from silero import silero_tts
            self._model, _ = silero_tts(
                language='ru',
                speaker='v5_1_ru',
                put_accent=True,
                put_yo=True,
                put_stress_homo=True,
                put_yo_homo=True
            )
            self._model_loaded = True
            self.logger.info("Модель Silero загружена")
        
        return self._model
    
    def _synthesize_chunk(self, text: str) -> Optional[bytes]:
        """
        Синтезирует один чанк текста.
        
        Args:
            text: Текст для синтеза
            
        Returns:
            Аудио-данные или None при ошибке
        """
        try:
            model = self._load_model()
            
            audio = model.apply_tts(
                text=text,
                speaker=self.voice,
                sample_rate=self.sample_rate
            )
            
            # Конвертируем в bytes
            import io
            import soundfile as sf
            
            buffer = io.BytesIO()
            sf.write(buffer, audio, self.sample_rate, format='WAV')
            buffer.seek(0)
            return buffer.read()
            
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
        
        Переопределено для использования numpy конкатенации.
        
        Args:
            text: Текст для синтеза
            output_file: Путь к выходному файлу
            add_pauses: Добавлять паузы между чанками
            
        Returns:
            TTSResult с результатом
        """
        import numpy as np
        import soundfile as sf
        import time
        
        result = TTSResult(success=False)
        start_time = time.time()
        
        try:
            # Загружаем модель
            model = self._load_model()
            
            # Если текст короткий - синтезируем напрямую
            if len(text) <= self.max_chars:
                audio = model.apply_tts(
                    text=text,
                    speaker=self.voice,
                    sample_rate=self.sample_rate
                )
                sf.write(output_file, audio, self.sample_rate)
                result.success = True
                result.characters_processed = len(text)
                result.chunks_processed = 1
            else:
                # Разбиваем на чанки через BaseTTS
                from utils.text_splitter import split_text_into_chunks
                chunks = split_text_into_chunks(text, preset='tts_silero')
                
                self.logger.info(f"Текст разбит на {len(chunks)} частей")
                
                audio_chunks = []
                pause_duration = int(0.3 * self.sample_rate)
                
                for i, chunk in enumerate(chunks, 1):
                    self.logger.info(f"Синтез части {i}/{len(chunks)} ({len(chunk)} символов)...")
                    
                    try:
                        audio = model.apply_tts(
                            text=chunk,
                            speaker=self.voice,
                            sample_rate=self.sample_rate
                        )
                        audio_chunks.append(audio)
                        result.chunks_processed += 1
                        result.characters_processed += len(chunk)
                        
                        # Пауза между частями
                        if add_pauses and i < len(chunks):
                            pause = np.zeros(pause_duration, dtype=np.float32)
                            audio_chunks.append(pause)
                            
                    except Exception as e:
                        self.logger.error(f"Ошибка синтеза части {i}: {e}")
                        result.errors.append(f"Часть {i}: {e}")
                
                # Объединяем
                if audio_chunks:
                    full_audio = np.concatenate(audio_chunks)
                    sf.write(output_file, full_audio, self.sample_rate)
                    result.success = True
            
            if result.success:
                result.output_file = output_file
                result.duration_seconds = len(sf.read(output_file)[0]) / self.sample_rate
                
        except Exception as e:
            self.logger.error(f"Ошибка синтеза: {e}")
            result.errors.append(str(e))
        
        return result
    
    @classmethod
    def list_voices(cls) -> List[str]:
        """Возвращает список доступных голосов."""
        return cls.VOICES


def main():
    parser = argparse.ArgumentParser(
        description='Генерация речи с помощью Silero TTS (рефакторенная версия)'
    )
    parser.add_argument('--input', '-i', required=True,
                       help='Путь к текстовому файлу')
    parser.add_argument('--output', '-o', default='output.wav',
                       help='Путь для сохранения аудио')
    parser.add_argument('--speaker', '-s', default='aidar',
                       choices=SileroTTS.VOICES,
                       help='Голос диктора')
    parser.add_argument('--sample-rate', '-r', type=int, default=48000,
                       choices=SileroTTS.SAMPLE_RATES,
                       help='Частота дискретизации')
    parser.add_argument('--list-voices', action='store_true',
                       help='Показать доступные голоса')
    
    args = parser.parse_args()
    
    if args.list_voices:
        print("Доступные голоса Silero:")
        for voice in SileroTTS.list_voices():
            print(f"  - {voice}")
        return 0
    
    from pathlib import Path
    
    if not Path(args.input).exists():
        print(f"❌ Файл не найден: {args.input}")
        return 1
    
    try:
        tts = SileroTTS(voice=args.speaker, sample_rate=args.sample_rate)
        result = tts.synthesize_file(args.input, args.output)
        
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
