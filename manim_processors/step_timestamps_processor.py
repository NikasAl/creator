#!/usr/bin/env python3
"""
Processor for finding timestamps of "Шаг" (Step) words in audio transcription.
Matches steps from spec.txt and lecture.txt with audio timestamps.
"""

import os
import json
import re
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from video_processors.video_transcriber import VideoTranscriber


class StepTimestampsProcessor:
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize step timestamps processor
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.transcriber = VideoTranscriber(config_file)
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison (lowercase, remove punctuation, etc.)
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def count_steps_in_text(self, text: str) -> int:
        """
        Count occurrences of word "Шаг" (case-insensitive) in text
        
        Args:
            text: Text to search
            
        Returns:
            Number of step occurrences
        """
        # Find all occurrences of "Шаг" (case-insensitive)
        pattern = r'\bшаг\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        return len(matches)
    
    def find_step_timestamps_in_transcript(self, transcript_data: Dict) -> List[float]:
        """
        Find timestamps of "Шаг" word in transcript
        
        Args:
            transcript_data: Transcript data from JSON
            
        Returns:
            List of timestamps in seconds where "Шаг" appears
        """
        timestamps = []
        
        if 'segments' not in transcript_data:
            return timestamps
        
        segments = transcript_data.get('segments', [])
        
        for segment in segments:
            text = segment.get('text', '')
            start_time = segment.get('start', 0)
            
            # Check if "Шаг" appears in this segment
            if re.search(r'\bшаг\b', text, re.IGNORECASE):
                # If word-level timestamps are available, use them
                if 'words' in segment:
                    for word_info in segment['words']:
                        word_text = word_info.get('word', '')
                        word_start = word_info.get('start', start_time)
                        
                        # Normalize word text for comparison
                        word_normalized = self.normalize_text(word_text)
                        if 'шаг' in word_normalized:
                            timestamps.append(word_start)
                else:
                    # Fallback: use segment start time
                    timestamps.append(start_time)
        
        # Sort timestamps
        timestamps.sort()
        
        return timestamps
    
    def process_pipeline(self, pipeline_dir: str, audio_file: str, 
                        spec_file: str, lecture_file: str, 
                        language: str = "ru") -> Dict:
        """
        Complete processing pipeline
        
        Args:
            pipeline_dir: Pipeline directory
            audio_file: Path to audio.mp3
            spec_file: Path to spec.txt
            lecture_file: Path to lecture.txt
            language: Language code
            
        Returns:
            Dictionary with step timestamps and metadata
        """
        pipeline_path = Path(pipeline_dir)
        
        # Check required files
        if not Path(audio_file).exists():
            print(f"❌ Аудио файл не найден: {audio_file}")
            return {}
        
        if not Path(spec_file).exists():
            print(f"❌ Файл spec.txt не найден: {spec_file}")
            return {}
        
        if not Path(lecture_file).exists():
            print(f"❌ Файл lecture.txt не найден: {lecture_file}")
            return {}
        
        # Read spec.txt and lecture.txt
        print("📖 Читаем spec.txt и lecture.txt...")
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec_text = f.read()
        
        with open(lecture_file, 'r', encoding='utf-8') as f:
            lecture_text = f.read()
        
        # Count steps in spec and lecture
        spec_steps_count = self.count_steps_in_text(spec_text)
        lecture_steps_count = self.count_steps_in_text(lecture_text)
        
        print(f"📊 Найдено шагов в spec.txt: {spec_steps_count}")
        print(f"📊 Найдено шагов в lecture.txt: {lecture_steps_count}")
        
        # Transcribe audio.mp3
        print("🎤 Транскрибируем audio.mp3...")
        transcript_result = self.transcriber.transcribe(audio_file, language)
        
        if not transcript_result:
            print("❌ Не удалось транскрибировать audio.mp3")
            return {}
        
        # Save transcript
        transcript_file = pipeline_path / "transcript.json"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(transcript_result, f, ensure_ascii=False, indent=2)
        print(f"✅ Транскрипция сохранена: {transcript_file}")
        
        # Find step timestamps
        print("🕐 Ищем таймстампы шагов в транскрипции...")
        step_timestamps = self.find_step_timestamps_in_transcript(transcript_result)
        
        print(f"📊 Найдено шагов в аудио: {len(step_timestamps)}")
        
        # Validate step counts
        if len(step_timestamps) != spec_steps_count:
            print(f"⚠️ Предупреждение: количество шагов в аудио ({len(step_timestamps)}) не совпадает с spec.txt ({spec_steps_count})")
        
        if len(step_timestamps) != lecture_steps_count:
            print(f"⚠️ Предупреждение: количество шагов в аудио ({len(step_timestamps)}) не совпадает с lecture.txt ({lecture_steps_count})")
        
        # Calculate intro duration (time before first step)
        # If no steps found, use audio duration as intro
        if step_timestamps:
            intro_duration = step_timestamps[0]
        else:
            # No steps found, use entire audio as intro
            if 'segments' in transcript_result and transcript_result['segments']:
                last_segment = transcript_result['segments'][-1]
                intro_duration = last_segment.get('end', 0)
            else:
                intro_duration = 0
        
        # Calculate step durations
        step_durations = []
        if step_timestamps:
            for i in range(len(step_timestamps)):
                if i < len(step_timestamps) - 1:
                    duration = step_timestamps[i + 1] - step_timestamps[i]
                else:
                    # Last step: duration until end of audio
                    # Get audio duration from transcript
                    if 'segments' in transcript_result and transcript_result['segments']:
                        last_segment = transcript_result['segments'][-1]
                        audio_end = last_segment.get('end', step_timestamps[i] + 10)
                        duration = audio_end - step_timestamps[i]
                    else:
                        duration = 10  # Default fallback
                step_durations.append(duration)
        
        result = {
            'intro_duration': intro_duration,
            'step_timestamps': step_timestamps,
            'step_durations': step_durations,
            'step_count': len(step_timestamps),
            'spec_steps_count': spec_steps_count,
            'lecture_steps_count': lecture_steps_count,
            'transcript_file': str(transcript_file)
        }
        
        # Save result
        result_file = pipeline_path / "step_timestamps.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ Результаты сохранены: {result_file}")
        
        print("\n📋 Таймстампы шагов:")
        for i, timestamp in enumerate(step_timestamps, 1):
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            print(f"  Шаг {i}: {minutes:02d}:{seconds:02d} ({timestamp:.2f}с)")
        
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Поиск таймстампов шагов в транскрипции аудио"
    )
    parser.add_argument('--pipeline-dir', '-d', required=True,
                       help='Директория пайплайна')
    parser.add_argument('--audio-file', '-a', default='audio.mp3',
                       help='Путь к файлу audio.mp3')
    parser.add_argument('--spec-file', '-s', default='spec.txt',
                       help='Путь к файлу spec.txt')
    parser.add_argument('--lecture-file', '-l', default='lecture.txt',
                       help='Путь к файлу lecture.txt')
    parser.add_argument('--language', default='ru',
                       help='Язык транскрипции (ru, en, etc.)')
    parser.add_argument('--config', help='Файл конфигурации')
    
    args = parser.parse_args()
    
    # Handle file paths
    pipeline_dir = Path(args.pipeline_dir).resolve()
    
    # Helper function to resolve file paths
    def resolve_file_path(file_path_str: str, default_name: str) -> Path:
        """Resolve file path - check if absolute, if path contains pipeline_dir, or relative to pipeline_dir"""
        file_path = Path(file_path_str)
        
        # If absolute path, use as is
        if file_path.is_absolute():
            return file_path
        
        # Check if the path already contains the full pipeline_dir path
        # If file_path_str already starts with pipeline_dir, use it directly
        if str(file_path).startswith(str(pipeline_dir)):
            return file_path.resolve()
        
        # If file exists at the given path, use it
        if file_path.exists():
            return file_path.resolve()
        
        # Otherwise, make it relative to pipeline_dir (just use filename)
        # Extract just the filename if path contains directories
        filename = file_path.name if file_path.name else default_name
        return (pipeline_dir / filename).resolve()
    
    audio_file = resolve_file_path(args.audio_file, "audio.mp3")
    spec_file = resolve_file_path(args.spec_file, "spec.txt")
    lecture_file = resolve_file_path(args.lecture_file, "lecture.txt")
    
    processor = StepTimestampsProcessor(args.config)
    
    result = processor.process_pipeline(
        str(pipeline_dir),
        str(audio_file),
        str(spec_file),
        str(lecture_file),
        args.language
    )
    
    if result:
        print("\n✅ Обработка завершена успешно")
        return 0
    else:
        print("\n❌ Обработка не удалась")
        return 1


if __name__ == "__main__":
    exit(main())

