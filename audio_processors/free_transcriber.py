#!/usr/bin/env python3
"""
Бесплатный транскрайбер с поддержкой различных бесплатных сервисов
"""

import os
import json
import time
import argparse
import requests
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime


class FreeTranscriber:
    def __init__(self, config_file: str = None):
        """
        Инициализация бесплатного транскрайбера
        
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
            
            # OpenRouter API (бесплатный лимит)
            self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
            self.openrouter_base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
            
            # Hugging Face API (бесплатный)
            self.huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
            
            # Локальные модели
            self.use_local_whisper = os.getenv('USE_LOCAL_WHISPER', 'false').lower() == 'true'
            
        except ImportError:
            print("⚠️  python-dotenv не установлен, используем переменные окружения")
    
    def transcribe_with_openrouter_free(self, audio_file: str) -> Optional[Dict]:
        """
        Транскрибация через OpenRouter (бесплатный лимит)
        
        Args:
            audio_file: Путь к аудио файлу
            
        Returns:
            Результат транскрибации или None
        """
        if not self.openrouter_api_key:
            print("❌ OPENROUTER_API_KEY не настроен")
            return None
        
        try:
            # Проверяем размер файла (бесплатный лимит обычно 25MB)
            file_size = Path(audio_file).stat().st_size
            if file_size > 25 * 1024 * 1024:  # 25MB
                print("⚠️  Файл слишком большой для бесплатного лимита OpenRouter")
                return None
            
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
            
            print("🎵 Отправляем аудио на транскрибацию (OpenRouter бесплатный)...")
            
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
            elif response.status_code == 402:
                print("❌ Превышен бесплатный лимит OpenRouter")
                return None
            else:
                print(f"❌ Ошибка транскрибации: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при транскрибации: {e}")
            return None
    
    def transcribe_with_huggingface(self, audio_file: str) -> Optional[Dict]:
        """
        Транскрибация через Hugging Face (бесплатный)
        
        Args:
            audio_file: Путь к аудио файлу
            
        Returns:
            Результат транскрибации или None
        """
        try:
            # Используем бесплатную модель Whisper через Hugging Face
            model_name = "openai/whisper-base"  # Меньшая модель для экономии ресурсов
            
            print("🎵 Отправляем аудио на транскрибацию (Hugging Face)...")
            
            # Используем API Hugging Face
            api_url = f"https://api-inference.huggingface.co/models/{model_name}"
            
            headers = {}
            if self.huggingface_token:
                headers["Authorization"] = f"Bearer {self.huggingface_token}"
            
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            response = requests.post(
                api_url,
                headers=headers,
                data=audio_data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Транскрибация завершена успешно")
                
                # Преобразуем в нужный формат
                return self.convert_huggingface_result(result)
            else:
                print(f"❌ Ошибка транскрибации: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при транскрибации: {e}")
            return None
    
    def convert_huggingface_result(self, result: Dict) -> Dict:
        """Преобразует результат Hugging Face в нужный формат"""
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        
        # Создаем простой формат с сегментами
        text = result.get('text', '')
        
        # Разбиваем на сегменты по 10 секунд
        words = text.split()
        segments = []
        words_per_segment = max(1, len(words) // 10)  # Примерно 10 сегментов
        
        for i in range(0, len(words), words_per_segment):
            segment_words = words[i:i + words_per_segment]
            segment_text = ' '.join(segment_words)
            
            segments.append({
                'start': i * 0.5,  # Примерное время
                'end': (i + len(segment_words)) * 0.5,
                'text': segment_text,
                'words': [{'word': word, 'start': j * 0.5, 'end': (j + 1) * 0.5} 
                         for j, word in enumerate(segment_words)]
            })
        
        return {
            'text': text,
            'segments': segments,
            'language': 'ru'
        }
    
    def transcribe_with_local_whisper(self, audio_file: str) -> Optional[Dict]:
        """
        Локальная транскрибация с Whisper (бесплатно)
        
        Args:
            audio_file: Путь к аудио файлу
            
        Returns:
            Результат транскрибации или None
        """
        try:
            print("🎵 Запускаем локальную транскрибацию с Whisper...")
            
            # Проверяем, установлен ли Whisper
            try:
                import whisper
            except ImportError:
                print("❌ Whisper не установлен. Установите: pip install openai-whisper")
                return None
            
            # Загружаем модель
            model = whisper.load_model("base")  # Используем base для экономии памяти
            
            # Транскрибируем
            result = model.transcribe(
                audio_file,
                language="ru",
                verbose=True,
                word_timestamps=True
            )
            
            print("✅ Локальная транскрибация завершена успешно")
            return result
            
        except Exception as e:
            print(f"❌ Ошибка при локальной транскрибации: {e}")
            return None
    
    def transcribe_with_web_services(self, audio_file: str) -> Optional[Dict]:
        """
        Транскрибация через бесплатные веб-сервисы
        
        Args:
            audio_file: Путь к аудио файлу
            
        Returns:
            Результат транскрибации или None
        """
        print("🌐 Пробуем бесплатные веб-сервисы...")
        
        # Список бесплатных сервисов для попытки
        services = [
            ("https://api.voicenotebook.com/transcribe", "VoiceNotebook"),
            ("https://api.speechmatics.com/v1/jobs", "Speechmatics"),
        ]
        
        for url, service_name in services:
            try:
                print(f"🔄 Пробуем {service_name}...")
                
                with open(audio_file, 'rb') as f:
                    audio_data = f.read()
                
                response = requests.post(
                    url,
                    files={'audio': audio_data},
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {service_name} транскрибация успешна")
                    return result
                else:
                    print(f"❌ {service_name} недоступен")
                    
            except Exception as e:
                print(f"❌ Ошибка {service_name}: {e}")
                continue
        
        return None
    
    def create_simple_segments(self, text: str, estimated_duration: float = 60.0) -> List[Dict]:
        """
        Создает простые сегменты на основе текста
        
        Args:
            text: Транскрибированный текст
            estimated_duration: Примерная длительность аудио в секундах
            
        Returns:
            Список сегментов
        """
        # Разбиваем текст на предложения
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return []
        
        # Оцениваем время на предложение
        time_per_sentence = estimated_duration / len(sentences)
        
        segments = []
        current_time = 0
        
        for i, sentence in enumerate(sentences):
            segment_duration = time_per_sentence * (len(sentence.split()) / 10)  # Примерно 10 слов в секунду
            
            segments.append({
                'start': current_time,
                'end': current_time + segment_duration,
                'text': sentence,
                'words': [{'word': word, 'start': current_time + j * 0.1, 'end': current_time + (j + 1) * 0.1} 
                         for j, word in enumerate(sentence.split())]
            })
            
            current_time += segment_duration
        
        return segments
    
    def align_text_with_audio(self, text_file: str, audio_file: str, 
                             output_file: str = None, method: str = "auto") -> bool:
        """
        Синхронизирует текст с аудио через транскрибацию
        
        Args:
            text_file: Файл с текстом
            audio_file: Аудио файл
            output_file: Выходной файл с таймстампами
            method: Метод транскрибации (auto/openrouter/huggingface/local/web)
            
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
            
            if method == "auto" or method == "openrouter":
                # 1. Пробуем OpenRouter (бесплатный лимит)
                if self.openrouter_api_key:
                    print("🔄 Пробуем транскрибацию через OpenRouter (бесплатный)...")
                    transcription = self.transcribe_with_openrouter_free(audio_file)
                    if transcription:
                        method = "openrouter"
            
            if not transcription and (method == "auto" or method == "huggingface"):
                # 2. Пробуем Hugging Face
                print("🔄 Пробуем транскрибацию через Hugging Face...")
                transcription = self.transcribe_with_huggingface(audio_file)
                if transcription:
                    method = "huggingface"
            
            if not transcription and (method == "auto" or method == "local"):
                # 3. Пробуем локальный Whisper
                if self.use_local_whisper:
                    print("🔄 Пробуем локальную транскрибацию...")
                    transcription = self.transcribe_with_local_whisper(audio_file)
                    if transcription:
                        method = "local"
            
            if not transcription and (method == "auto" or method == "web"):
                # 4. Пробуем веб-сервисы
                transcription = self.transcribe_with_web_services(audio_file)
                if transcription:
                    method = "web"
            
            if not transcription:
                print("❌ Не удалось выполнить транскрибацию ни одним методом")
                print("💡 Создаем простую синхронизацию на основе текста...")
                
                # Создаем простую синхронизацию
                estimated_duration = 60.0  # Предполагаем 1 минуту
                segments = self.create_simple_segments(text_content, estimated_duration)
                method = "simple"
            else:
                # Создаем сегменты из транскрибации
                segments = self.create_segments_from_transcription(transcription, method)
            
            if not segments:
                print("❌ Не удалось создать сегменты")
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
                    'total_fragments': len(text_fragments),
                    'free_service': True
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
            print(f"   - Метод: {method}")
            print(f"   - Сегментов: {len(segments)}")
            print(f"   - Фрагментов текста: {len(text_fragments)}")
            print(f"   - Длительность аудио: {result['statistics']['audio_duration']:.1f} сек")
            print(f"   - Время обработки: {result['statistics']['transcription_time']:.1f} сек")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
            return False
    
    def create_segments_from_transcription(self, transcription: Dict, method: str = "unknown") -> List[Dict]:
        """Создает сегменты из результата транскрибации"""
        segments = []
        
        if method == "openrouter" or method == "local":
            # OpenAI Whisper формат
            if 'segments' in transcription:
                for segment in transcription['segments']:
                    segments.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text'].strip(),
                        'words': segment.get('words', [])
                    })
            elif 'text' in transcription:
                # Создаем простые сегменты
                segments = self.create_simple_segments(transcription['text'])
        
        elif method == "huggingface":
            # Hugging Face формат
            if 'segments' in transcription:
                segments = transcription['segments']
            elif 'text' in transcription:
                segments = self.create_simple_segments(transcription['text'])
        
        return segments
    
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
        """Синхронизирует фрагменты текста с аудио сегментами"""
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
        description="Бесплатный транскрайбер с поддержкой различных бесплатных сервисов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python free_transcriber.py text.txt audio.mp3
  python free_transcriber.py text.txt audio.mp3 --method huggingface
  python free_transcriber.py text.txt audio.mp3 --method local
  python free_transcriber.py text.txt audio.mp3 -o aligned.json
        """
    )
    
    parser.add_argument('text_file', help='Файл с текстом')
    parser.add_argument('audio_file', help='Аудио файл')
    parser.add_argument('-o', '--output', help='Выходной файл с таймстампами')
    parser.add_argument('--method', choices=['auto', 'openrouter', 'huggingface', 'local', 'web'], 
                       default='auto', help='Метод транскрибации')
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
        transcriber = FreeTranscriber(args.config)
        
        # Выполняем синхронизацию
        success = transcriber.align_text_with_audio(
            args.text_file,
            args.audio_file,
            args.output,
            args.method
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