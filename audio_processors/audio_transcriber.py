#!/usr/bin/env python3
"""
Система транскрибации аудио с таймстампами для синхронизации с текстом
Поддерживает различные сервисы транскрибации
"""

import os
import json
import time
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime, timedelta


class AudioTranscriber:
    def __init__(self, config_file: str = None):
        """
        Инициализация транскрайбера
        
        Args:
            config_file: Путь к файлу конфигурации .env
        """
        self.config_file = config_file
        self.load_config()
        
        # Статистика обработки
        self.stats = {
            'audio_duration': 0,
            'transcription_time': 0,
            'segments_count': 0,
            'total_words': 0,
            'accuracy_estimate': 0
        }
    
    def load_config(self):
        """Загружает конфигурацию из .env файла"""
        try:
            from dotenv import load_dotenv
            if self.config_file:
                load_dotenv(self.config_file)
            else:
                load_dotenv()
            
            # OpenRouter API для Whisper
            self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
            self.openrouter_base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
            
            # Альтернативные сервисы
            self.whisper_api_key = os.getenv('WHISPER_API_KEY')
            self.assemblyai_key = os.getenv('ASSEMBLYAI_KEY')
            
            if not self.openrouter_api_key:
                print("⚠️  Предупреждение: OPENROUTER_API_KEY не найден в конфигурации")
                
        except ImportError:
            print("⚠️  python-dotenv не установлен, используем переменные окружения")
    
    def transcribe_with_openrouter(self, audio_file: str) -> Optional[Dict]:
        """
        Транскрибация через OpenRouter (Whisper)
        
        Args:
            audio_file: Путь к аудио файлу
            
        Returns:
            Результат транскрибации или None
        """
        if not self.openrouter_api_key:
            print("❌ OPENROUTER_API_KEY не настроен")
            return None
        
        try:
            # Читаем аудио файл
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "multipart/form-data"
            }
            
            # Используем Whisper через OpenRouter
            files = {
                'file': (Path(audio_file).name, audio_data, 'audio/mpeg')
            }
            
            data = {
                'model': 'openai/whisper-1',
                'response_format': 'verbose_json',
                'timestamp_granularities': ['word', 'segment']
            }
            
            print("🎵 Отправляем аудио на транскрибацию...")
            
            response = requests.post(
                f"{self.openrouter_base_url}/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Транскрибация завершена успешно")
                return result
            else:
                print(f"❌ Ошибка транскрибации: {response.status_code}")
                print(f"Ответ: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при транскрибации: {e}")
            return None
    
    def transcribe_with_whisper_api(self, audio_file: str) -> Optional[Dict]:
        """
        Транскрибация через OpenAI Whisper API
        
        Args:
            audio_file: Путь к аудио файлу
            
        Returns:
            Результат транскрибации или None
        """
        if not self.whisper_api_key:
            print("❌ WHISPER_API_KEY не настроен")
            return None
        
        try:
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            headers = {
                "Authorization": f"Bearer {self.whisper_api_key}"
            }
            
            files = {
                'file': (Path(audio_file).name, audio_data, 'audio/mpeg')
            }
            
            data = {
                'model': 'whisper-1',
                'response_format': 'verbose_json',
                'timestamp_granularities': ['word', 'segment']
            }
            
            print("🎵 Отправляем аудио на транскрибацию (Whisper API)...")
            
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Транскрибация завершена успешно")
                return result
            else:
                print(f"❌ Ошибка транскрибации: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при транскрибации: {e}")
            return None
    
    def transcribe_with_assemblyai(self, audio_file: str) -> Optional[Dict]:
        """
        Транскрибация через AssemblyAI
        
        Args:
            audio_file: Путь к аудио файлу
            
        Returns:
            Результат транскрибации или None
        """
        if not self.assemblyai_key:
            print("❌ ASSEMBLYAI_KEY не настроен")
            return None
        
        try:
            # Загружаем файл
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            headers = {
                "authorization": self.assemblyai_key,
                "content-type": "application/json"
            }
            
            # Сначала загружаем файл
            upload_url = "https://api.assemblyai.com/v2/upload"
            upload_response = requests.post(upload_url, headers=headers, data=audio_data)
            
            if upload_response.status_code != 200:
                print(f"❌ Ошибка загрузки файла: {upload_response.status_code}")
                return None
            
            upload_url = upload_response.json()["upload_url"]
            
            # Запускаем транскрибацию
            transcript_url = "https://api.assemblyai.com/v2/transcript"
            transcript_request = {
                "audio_url": upload_url,
                "word_boost": ["психоанализ", "шизоид", "личность", "терапия"],
                "punctuate": True,
                "format_text": True
            }
            
            transcript_response = requests.post(transcript_url, json=transcript_request, headers=headers)
            
            if transcript_response.status_code != 200:
                print(f"❌ Ошибка запуска транскрибации: {transcript_response.status_code}")
                return None
            
            transcript_id = transcript_response.json()["id"]
            polling_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
            
            # Ждем завершения
            print("⏳ Ожидаем завершения транскрибации...")
            while True:
                polling_response = requests.get(polling_url, headers=headers)
                polling_response = polling_response.json()
                
                if polling_response["status"] == "completed":
                    print("✅ Транскрибация завершена успешно")
                    return polling_response
                elif polling_response["status"] == "error":
                    print("❌ Ошибка транскрибации")
                    return None
                
                time.sleep(3)
                
        except Exception as e:
            print(f"❌ Ошибка при транскрибации: {e}")
            return None
    
    def create_segments_from_transcription(self, transcription: Dict, method: str = "openrouter") -> List[Dict]:
        """
        Создает сегменты из результата транскрибации
        
        Args:
            transcription: Результат транскрибации
            method: Метод транскрибации
            
        Returns:
            Список сегментов с таймстампами
        """
        segments = []
        
        if method == "openrouter" or method == "whisper":
            # OpenAI Whisper формат
            if 'segments' in transcription:
                for segment in transcription['segments']:
                    segments.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text'].strip(),
                        'words': segment.get('words', [])
                    })
            elif 'words' in transcription:
                # Группируем слова в сегменты по 10 секунд
                current_segment = {'start': 0, 'end': 0, 'text': '', 'words': []}
                
                for word in transcription['words']:
                    if word['end'] - current_segment['start'] > 10:
                        if current_segment['text']:
                            segments.append(current_segment)
                        current_segment = {
                            'start': word['start'],
                            'end': word['end'],
                            'text': word['word'],
                            'words': [word]
                        }
                    else:
                        current_segment['end'] = word['end']
                        current_segment['text'] += ' ' + word['word']
                        current_segment['words'].append(word)
                
                if current_segment['text']:
                    segments.append(current_segment)
        
        elif method == "assemblyai":
            # AssemblyAI формат
            if 'words' in transcription:
                current_segment = {'start': 0, 'end': 0, 'text': '', 'words': []}
                
                for word in transcription['words']:
                    if word['end'] - current_segment['start'] > 10:
                        if current_segment['text']:
                            segments.append(current_segment)
                        current_segment = {
                            'start': word['start'] / 1000,  # Конвертируем в секунды
                            'end': word['end'] / 1000,
                            'text': word['text'],
                            'words': [word]
                        }
                    else:
                        current_segment['end'] = word['end'] / 1000
                        current_segment['text'] += ' ' + word['text']
                        current_segment['words'].append(word)
                
                if current_segment['text']:
                    segments.append(current_segment)
        
        return segments
    
    def align_text_with_audio(self, text_file: str, audio_file: str, 
                             output_file: str = None) -> bool:
        """
        Синхронизирует текст с аудио через транскрибацию
        
        Args:
            text_file: Файл с текстом
            audio_file: Аудио файл
            output_file: Выходной файл с таймстампами
            
        Returns:
            True если синхронизация успешна
        """
        start_time = time.time()
        
        try:
            # Читаем текст
            with open(text_file, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            print(f"📖 Загружен текст: {text_file}")
            print(f"🎵 Аудио файл: {audio_file}")
            
            # Пробуем разные методы транскрибации
            transcription = None
            method = "unknown"
            
            # 1. Пробуем OpenRouter
            if self.openrouter_api_key:
                print("🔄 Пробуем транскрибацию через OpenRouter...")
                transcription = self.transcribe_with_openrouter(audio_file)
                if transcription:
                    method = "openrouter"
            
            # 2. Пробуем Whisper API
            if not transcription and self.whisper_api_key:
                print("🔄 Пробуем транскрибацию через Whisper API...")
                transcription = self.transcribe_with_whisper_api(audio_file)
                if transcription:
                    method = "whisper"
            
            # 3. Пробуем AssemblyAI
            if not transcription and self.assemblyai_key:
                print("🔄 Пробуем транскрибацию через AssemblyAI...")
                transcription = self.transcribe_with_assemblyai(audio_file)
                if transcription:
                    method = "assemblyai"
            
            if not transcription:
                print("❌ Не удалось выполнить транскрибацию ни одним методом")
                return False
            
            # Создаем сегменты
            segments = self.create_segments_from_transcription(transcription, method)
            
            if not segments:
                print("❌ Не удалось создать сегменты из транскрибации")
                return False
            
            # Разбиваем текст на фрагменты
            text_fragments = self.split_text_into_fragments(text_content)
            
            # Синхронизируем текст с сегментами
            aligned_content = self.sync_text_with_segments(text_fragments, segments)
            
            # Определяем выходной файл
            if not output_file:
                output_file = f"{Path(text_file).stem}_aligned.json"
            
            # Сохраняем результат
            result = {
                'metadata': {
                    'text_file': text_file,
                    'audio_file': audio_file,
                    'transcription_method': method,
                    'aligned_at': datetime.now().isoformat(),
                    'total_segments': len(segments),
                    'total_fragments': len(text_fragments)
                },
                'segments': segments,
                'aligned_content': aligned_content,
                'statistics': {
                    'audio_duration': segments[-1]['end'] if segments else 0,
                    'transcription_time': time.time() - start_time,
                    'segments_count': len(segments),
                    'total_words': sum(len(seg['text'].split()) for seg in segments)
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Синхронизация завершена: {output_file}")
            print(f"📊 Статистика:")
            print(f"   - Сегментов: {len(segments)}")
            print(f"   - Фрагментов текста: {len(text_fragments)}")
            print(f"   - Длительность аудио: {result['statistics']['audio_duration']:.1f} сек")
            print(f"   - Время обработки: {result['statistics']['transcription_time']:.1f} сек")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
            return False
    
    def split_text_into_fragments(self, text: str) -> List[str]:
        """Разбивает текст на фрагменты"""
        # Ищем фрагменты по паттерну "Фрагмент X"
        pattern = r'(?:##? )?Фрагмент \d+\s*\n(.*?)(?=\n(?:##? )?Фрагмент|\Z)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            return [match.strip() for match in matches]
        else:
            # Если фрагменты не найдены, разбиваем по абзацам
            paragraphs = text.split('\n\n')
            return [p.strip() for p in paragraphs if p.strip()]
    
    def sync_text_with_segments(self, text_fragments: List[str], 
                               segments: List[Dict]) -> List[Dict]:
        """
        Синхронизирует фрагменты текста с аудио сегментами
        
        Args:
            text_fragments: Фрагменты текста
            segments: Сегменты аудио с таймстампами
            
        Returns:
            Синхронизированный контент
        """
        aligned_content = []
        
        # Простая стратегия: распределяем фрагменты по времени
        total_duration = segments[-1]['end'] if segments else 0
        fragment_duration = total_duration / len(text_fragments) if text_fragments else 0
        
        for i, fragment in enumerate(text_fragments):
            start_time = i * fragment_duration
            end_time = (i + 1) * fragment_duration
            
            # Находим соответствующие сегменты
            matching_segments = [
                seg for seg in segments 
                if seg['start'] >= start_time and seg['end'] <= end_time
            ]
            
            aligned_content.append({
                'fragment_number': i + 1,
                'text': fragment,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'matching_segments': matching_segments,
                'transcribed_text': ' '.join(seg['text'] for seg in matching_segments)
            })
        
        return aligned_content


def main():
    parser = argparse.ArgumentParser(
        description="Транскрибация аудио и синхронизация с текстом",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python audio_transcriber.py text.txt audio.mp3
  python audio_transcriber.py text.txt audio.mp3 -o aligned.json
  python audio_transcriber.py text.txt audio.mp3 --config config.env
        """
    )
    
    parser.add_argument('text_file', help='Файл с текстом')
    parser.add_argument('audio_file', help='Аудио файл')
    parser.add_argument('-o', '--output', help='Выходной файл с таймстампами')
    parser.add_argument('--config', help='Файл конфигурации .env')
    
    args = parser.parse_args()
    
    # Проверяем входные файлы
    if not Path(args.text_file).exists():
        print(f"❌ Ошибка: Файл {args.text_file} не найден")
        return 1
    
    if not Path(args.audio_file).exists():
        print(f"❌ Ошибка: Файл {args.audio_file} не найден")
        return 1
    
    try:
        # Создаем транскрайбер
        transcriber = AudioTranscriber(args.config)
        
        # Выполняем синхронизацию
        success = transcriber.align_text_with_audio(
            args.text_file,
            args.audio_file,
            args.output
        )
        
        if success:
            print("✅ Синхронизация завершена успешно!")
        else:
            print("❌ Ошибка при синхронизации")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 