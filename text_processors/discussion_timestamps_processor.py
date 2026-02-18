#!/usr/bin/env python3
"""
Processor for adding timestamps to discussion.txt based on audio.mp3 transcription.
Finds timestamps for segment titles by matching them in the transcribed audio.
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


class DiscussionTimestampsProcessor:
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize discussion timestamps processor
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.transcriber = VideoTranscriber(config_file)
    
    def format_time(self, seconds: float) -> str:
        """
        Format seconds to HH:MM:SS format
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
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
        # Remove punctuation but keep spaces
        text = re.sub(r'[^\w\s]', '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def find_timestamp_in_transcript(self, title: str, transcript_data: Dict, segment_index: int = 0) -> Optional[float]:
        """
        Find timestamp for a title in the transcript
        
        Args:
            title: Title to find
            transcript_data: Transcript data from JSON
            segment_index: Index of the segment (used for ordering if exact match not found)
            
        Returns:
            Timestamp in seconds or None
        """
        # Normalize title for search
        normalized_title = self.normalize_text(title)
        
        # Extract key words from title (first few words, but at least 3)
        title_words = normalized_title.split()
        if len(title_words) < 2:
            # If title is too short, try to use it as is
            title_phrase = normalized_title
        else:
            # Take first 3-5 words for search
            title_phrase = ' '.join(title_words[:min(5, len(title_words))])
        
        # Try to find title in segments
        if 'segments' not in transcript_data:
            return None
        
        segments = transcript_data.get('segments', [])
        if not segments:
            return None
        
        # Strategy 1: Search for exact phrase match
        for segment in segments:
            segment_text = segment.get('text', '')
            normalized_segment = self.normalize_text(segment_text)
            
            # Check if title phrase appears in segment
            if title_phrase in normalized_segment:
                return segment.get('start')
        
        # Strategy 2: Search for word overlap
        best_match = None
        best_score = 0
        
        for segment in segments:
            segment_text = segment.get('text', '')
            normalized_segment = self.normalize_text(segment_text)
            
            # Count matching words
            segment_words = set(normalized_segment.split())
            title_words_set = set(title_words)
            matches = len(title_words_set & segment_words)
            
            if len(title_words_set) > 0:
                score = matches / len(title_words_set)
                
                if score > best_score:
                    best_score = score
                    best_match = segment
        
        # If we found a good match (at least 50% of words match), return its start time
        if best_match and best_score >= 0.5:
            return best_match.get('start')
        
        # Strategy 3: Use segment index to estimate position
        # If we can't find exact match, use proportional position based on index
        if segment_index > 0 and len(segments) > 0:
            # Estimate based on segment index in original video
            # This is a fallback - try to find segments in order
            estimated_position = min(segment_index - 1, len(segments) - 1)
            return segments[estimated_position].get('start')
        
        return None
    
    def find_title_in_discussion(self, discussion_text: str, title: str) -> bool:
        """
        Check if title appears in discussion text
        
        Args:
            discussion_text: Discussion text content
            title: Title to find
            
        Returns:
            True if title found
        """
        # Look for markdown headers with this title
        # Format: ## Title
        title_pattern = re.compile(r'##\s+' + re.escape(title) + r'\s*\n', re.IGNORECASE)
        return bool(title_pattern.search(discussion_text))
    
    def extract_titles_from_discussion(self, discussion_text: str) -> List[str]:
        """
        Extract all markdown titles (## Title) from discussion text
        
        Args:
            discussion_text: Discussion text content
            
        Returns:
            List of titles
        """
        # Find all markdown headers (## Title)
        pattern = r'##\s+(.+?)\s*\n'
        titles = re.findall(pattern, discussion_text)
        return titles
    
    def extract_titles_from_segments(self, segments_data: Dict) -> List[Tuple[int, str]]:
        """
        Extract titles from segments.json
        
        Args:
            segments_data: Segments JSON data
            
        Returns:
            List of (index, title) tuples
        """
        segments = segments_data.get('segments', [])
        titles = []
        
        for segment in segments:
            index = segment.get('index', 0)
            title = segment.get('title', '')
            if title:
                titles.append((index, title))
        
        return titles
    
    def generate_timestamps_block(self, segments_data: Dict, audio_transcript_data: Dict) -> str:
        """
        Generate timestamps block from segments and audio transcript
        
        Args:
            segments_data: Segments JSON data
            audio_transcript_data: Audio transcript JSON data
            
        Returns:
            Formatted timestamps block
        """
        segments = segments_data.get('segments', [])
        timestamps_lines = []
        
        for segment in segments:
            index = segment.get('index', 0)
            title = segment.get('title', '')
            
            if not title:
                continue
            
            # Find timestamp for this title in audio transcript
            timestamp = self.find_timestamp_in_transcript(title, audio_transcript_data, index)
            
            if timestamp is not None:
                formatted_time = self.format_time(timestamp)
                timestamps_lines.append(f"{formatted_time} {title}")
                print(f"  ✓ {formatted_time} - {title}")
            else:
                # No timestamp found
                print(f"  ⚠️ Не удалось найти таймстамп для '{title}' (сегмент {index})")
        
        return '\n'.join(timestamps_lines)
    
    def update_discussion_with_timestamps(self, discussion_file: str, timestamps_block: str) -> bool:
        """
        Update discussion.txt by replacing [content] with timestamps block
        
        Args:
            discussion_file: Path to discussion.txt
            timestamps_block: Generated timestamps block
            
        Returns:
            True if successful
        """
        try:
            discussion_path = Path(discussion_file)
            if not discussion_path.exists():
                print(f"❌ Файл discussion.txt не найден: {discussion_path}")
                return False
            
            # Read discussion file
            with open(discussion_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if [content] placeholder exists
            if '[content]' not in content:
                # Add [content] placeholder after the header and before the first section
                # Look for the pattern: header ---\n\n followed by content
                header_pattern = r'(.*?---\n\n)'
                match = re.search(header_pattern, content, re.DOTALL)
                
                if match:
                    # Insert [content] after header
                    header = match.group(1)
                    rest = content[match.end():]
                    content = header + "[content]\n\n" + rest
                    print("📝 Добавлен плейсхолдер [content] в discussion.txt")
                else:
                    # If no header pattern found, try to insert before first ##
                    first_header_pattern = r'(.*?)(##\s+.+?\n)'
                    match = re.search(first_header_pattern, content, re.DOTALL)
                    if match:
                        header = match.group(1)
                        rest = match.group(2) + content[match.end():]
                        content = header + "[content]\n\n" + rest
                        print("📝 Добавлен плейсхолдер [content] в discussion.txt")
                    else:
                        # Last resort: add at the beginning
                        content = content + "\n\n[content]\n\n"
                        print("📝 Добавлен плейсхолдер [content] в конец discussion.txt")
            
            # Replace [content] with timestamps block (replace only first occurrence)
            # Use regex to match [content] on its own line to avoid accidental replacements
            updated_content = re.sub(r'^\[content\]$', timestamps_block, content, flags=re.MULTILINE)
            
            # Write back
            with open(discussion_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"✅ Обновлен discussion.txt с таймстампами")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обновления discussion.txt: {e}")
            return False
    
    def process_pipeline(self, pipeline_dir: str, audio_file: str, language: str = "ru") -> bool:
        """
        Complete processing pipeline
        
        Args:
            pipeline_dir: Pipeline directory
            audio_file: Path to audio.mp3
            language: Language code
            
        Returns:
            True if successful
        """
        pipeline_path = Path(pipeline_dir)
        
        # Check required files
        segments_file = pipeline_path / "segments.json"
        discussion_file = pipeline_path / "discussion.txt"
        
        if not segments_file.exists():
            print(f"❌ Файл segments.json не найден: {segments_file}")
            return False
        
        if not discussion_file.exists():
            print(f"❌ Файл discussion.txt не найден: {discussion_file}")
            return False
        
        if not Path(audio_file).exists():
            print(f"❌ Аудио файл не найден: {audio_file}")
            return False
        
        # Transcribe audio.mp3
        print("🎤 Транскрибируем audio.mp3...")
        transcript_result = self.transcriber.transcribe(audio_file, language)
        
        if not transcript_result:
            print("❌ Не удалось транскрибировать audio.mp3")
            return False
        
        # Save transcript temporarily
        audio_transcript_file = pipeline_path / "audio_transcript.json"
        with open(audio_transcript_file, 'w', encoding='utf-8') as f:
            json.dump(transcript_result, f, ensure_ascii=False, indent=2)
        print(f"✅ Транскрипция audio.mp3 сохранена: {audio_transcript_file}")
        
        # Load segments.json
        print("📖 Загружаем segments.json...")
        with open(segments_file, 'r', encoding='utf-8') as f:
            segments_data = json.load(f)
        
        # Generate timestamps block
        print("🕐 Генерируем таймстампы...")
        timestamps_block = self.generate_timestamps_block(segments_data, transcript_result)
        
        if not timestamps_block:
            print("⚠️ Не удалось сгенерировать таймстампы")
            return False
        
        print("📋 Сгенерированные таймстампы:")
        print(timestamps_block)
        print()
        
        # Update discussion.txt
        print("📝 Обновляем discussion.txt...")
        success = self.update_discussion_with_timestamps(str(discussion_file), timestamps_block)
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description="Добавление таймстампов в discussion.txt на основе транскрипции audio.mp3"
    )
    parser.add_argument('--pipeline-dir', '-d', required=True, 
                       help='Директория пайплайна (где находятся segments.json и discussion.txt)')
    parser.add_argument('--audio-file', '-a', default='audio.mp3',
                       help='Путь к файлу audio.mp3 (по умолчанию audio.mp3 в pipeline-dir)')
    parser.add_argument('--language', '-l', default='ru',
                       help='Язык транскрипции (ru, en, etc.)')
    parser.add_argument('--config', help='Файл конфигурации')
    
    args = parser.parse_args()
    
    # Handle audio file path
    audio_file_str = args.audio_file
    pipeline_dir = Path(args.pipeline_dir)
    
    # If audio-file is absolute, use it as is
    if Path(audio_file_str).is_absolute():
        audio_file = Path(audio_file_str)
    # If audio-file path already contains pipeline_dir name, use it as is (avoid duplication)
    # Check if pipeline_dir name appears in the path (even if paths are different)
    elif pipeline_dir.name in audio_file_str and pipeline_dir.name != Path(audio_file_str).name:
        # Path already contains pipeline directory name, use as is to avoid duplication
        audio_file = Path(audio_file_str)
    # If the file exists at the given relative path, use it as is
    elif Path(audio_file_str).exists():
        audio_file = Path(audio_file_str)
    # Otherwise, make it relative to pipeline-dir (default behavior for just 'audio.mp3')
    else:
        audio_file = pipeline_dir / audio_file_str
    
    processor = DiscussionTimestampsProcessor(args.config)
    
    success = processor.process_pipeline(
        str(args.pipeline_dir),
        str(audio_file),
        args.language
    )
    
    if success:
        print("✅ Обработка завершена успешно")
        return 0
    else:
        print("❌ Обработка не удалась")
        return 1


if __name__ == "__main__":
    exit(main())

