#!/usr/bin/env python3
"""
Video transcriber using Whisper for audio transcription.
Supports both local Whisper and API-based transcription.
"""

import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class VideoTranscriber:
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize video transcriber
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.load_config()
        
        # Check available transcription methods
        self.local_whisper_available = self._check_local_whisper()
        self.api_available = self._check_api_availability()
    
    def load_config(self):
        """Load configuration from environment or config file"""
        try:
            from dotenv import load_dotenv
            if self.config_file:
                load_dotenv(self.config_file)
            else:
                load_dotenv()
        except ImportError:
            pass
        
        # API keys
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.whisper_api_key = os.getenv('WHISPER_API_KEY')
        self.huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
        
        # Models
        self.whisper_model = os.getenv('WHISPER_MODEL', 'small')
        # self.whisper_model = os.getenv('WHISPER_MODEL', 'medium')
        self.use_local_whisper = os.getenv('USE_LOCAL_WHISPER', 'true').lower() == 'true'
    
    def _check_local_whisper(self) -> bool:
        """Check if local Whisper is available"""
        try:
            import whisper
            print("✅ Локальный Whisper доступен")
            return True
        except ImportError:
            print("⚠️ Локальный Whisper не установлен")
            return False
    
    def _check_api_availability(self) -> bool:
        """Check if any API-based transcription is available"""
        if self.openrouter_api_key:
            print("✅ OpenRouter API доступен")
            return True
        if self.whisper_api_key:
            print("✅ Whisper API доступен")
            return True
        if self.huggingface_token:
            print("✅ Hugging Face API доступен")
            return True
        print("⚠️ API ключи не настроены")
        return False
    
    def transcribe_with_local_whisper(self, audio_file: str, language: str = "ru") -> Optional[Dict[str, Any]]:
        """
        Transcribe using local Whisper
        
        Args:
            audio_file: Path to audio file
            language: Language code (ru, en, etc.)
            
        Returns:
            Transcription result or None
        """
        if not self.local_whisper_available:
            print("❌ Локальный Whisper недоступен")
            return None
        
        try:
            import whisper
            
            print(f"🎤 Транскрибируем с локальным Whisper (модель: {self.whisper_model})...")
            
            # Load model
            model = whisper.load_model(self.whisper_model)
            
            # Transcribe
            result = model.transcribe(
                audio_file,
                language=language,
                verbose=True,
                word_timestamps=True
            )
            
            print("✅ Локальная транскрипция завершена")
            return result
            
        except Exception as e:
            print(f"❌ Ошибка локальной транскрипции: {e}")
            return None
    
    def transcribe_with_api(self, audio_file: str, language: str = "ru") -> Optional[Dict[str, Any]]:
        """
        Transcribe using API services
        
        Args:
            audio_file: Path to audio file
            language: Language code
            
        Returns:
            Transcription result or None
        """
        # Try OpenRouter first (if available)
        if self.openrouter_api_key:
            result = self._transcribe_with_openrouter(audio_file, language)
            if result:
                return result
        
        # Try Whisper API
        if self.whisper_api_key:
            result = self._transcribe_with_whisper_api(audio_file, language)
            if result:
                return result
        
        # Try Hugging Face
        if self.huggingface_token:
            result = self._transcribe_with_huggingface(audio_file, language)
            if result:
                return result
        
        print("❌ Все API методы недоступны")
        return None
    
    def _transcribe_with_openrouter(self, audio_file: str, language: str) -> Optional[Dict[str, Any]]:
        """Transcribe using OpenRouter API"""
        try:
            import requests
            
            print("🎤 Транскрибируем через OpenRouter API...")
            
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            # Use OpenRouter's whisper endpoint
            data = {
                "model": "openai/whisper-1",
                "audio": audio_data.hex(),  # Convert to hex string
                "language": language
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/audio/transcriptions",
                headers=headers,
                json=data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ OpenRouter транскрипция завершена")
                return result
            else:
                print(f"❌ Ошибка OpenRouter API: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка OpenRouter транскрипции: {e}")
            return None
    
    def _transcribe_with_whisper_api(self, audio_file: str, language: str) -> Optional[Dict[str, Any]]:
        """Transcribe using OpenAI Whisper API"""
        try:
            import requests
            
            print("🎤 Транскрибируем через Whisper API...")
            
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
                'language': language,
                'timestamp_granularities': ['word', 'segment']
            }
            
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Whisper API транскрипция завершена")
                return result
            else:
                print(f"❌ Ошибка Whisper API: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка Whisper API транскрипции: {e}")
            return None
    
    def _transcribe_with_huggingface(self, audio_file: str, language: str) -> Optional[Dict[str, Any]]:
        """Transcribe using Hugging Face API"""
        try:
            import requests
            
            print("🎤 Транскрибируем через Hugging Face API...")
            
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            headers = {
                "Authorization": f"Bearer {self.huggingface_token}"
            }
            
            response = requests.post(
                "https://api-inference.huggingface.co/models/openai/whisper-large-v2",
                headers=headers,
                data=audio_data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Hugging Face транскрипция завершена")
                return result
            else:
                print(f"❌ Ошибка Hugging Face API: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка Hugging Face транскрипции: {e}")
            return None
    
    def transcribe(self, audio_file: str, language: str = "ru", prefer_local: bool = True) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio file using available methods
        
        Args:
            audio_file: Path to audio file
            language: Language code
            prefer_local: Prefer local Whisper over API
            
        Returns:
            Transcription result or None
        """
        if not os.path.exists(audio_file):
            print(f"❌ Аудио файл не найден: {audio_file}")
            return None
        
        # Try local Whisper first if preferred and available
        if prefer_local and self.local_whisper_available:
            result = self.transcribe_with_local_whisper(audio_file, language)
            if result:
                return result
        
        # Fallback to API
        if self.api_available:
            result = self.transcribe_with_api(audio_file, language)
            if result:
                return result
        
        # Try local Whisper as last resort
        if not prefer_local and self.local_whisper_available:
            result = self.transcribe_with_local_whisper(audio_file, language)
            if result:
                return result
        
        print("❌ Не удалось выполнить транскрипцию")
        return None
    
    def save_transcript(self, result: Dict[str, Any], output_dir: str, 
                       transcript_filename: str = "transcript.txt",
                       json_filename: str = "transcript.json") -> bool:
        """
        Save transcription results to files
        
        Args:
            result: Transcription result
            output_dir: Output directory
            transcript_filename: Text transcript filename
            json_filename: JSON transcript filename
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Save text transcript
            text_file = output_path / transcript_filename
            if 'text' in result:
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(result['text'])
                print(f"✅ Текстовая транскрипция сохранена: {text_file}")
            
            # Save JSON transcript with timestamps
            json_file = output_path / json_filename
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON транскрипция сохранена: {json_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения транскрипции: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Транскрипция аудио с помощью Whisper")
    parser.add_argument('audio_file', help='Путь к аудио файлу')
    parser.add_argument('--output-dir', '-o', default='output', help='Директория для сохранения')
    parser.add_argument('--language', '-l', default='ru', help='Язык транскрипции (ru, en, etc.)')
    parser.add_argument('--config', help='Файл конфигурации')
    parser.add_argument('--prefer-api', action='store_true', help='Предпочитать API вместо локального Whisper')
    
    args = parser.parse_args()
    
    transcriber = VideoTranscriber(args.config)
    
    result = transcriber.transcribe(
        args.audio_file, 
        args.language, 
        prefer_local=not args.prefer_api
    )
    
    if result:
        success = transcriber.save_transcript(result, args.output_dir)
        if success:
            print("✅ Транскрипция завершена успешно")
            return 0
        else:
            return 1
    else:
        print("❌ Транскрипция не удалась")
        return 1


if __name__ == "__main__":
    exit(main())
