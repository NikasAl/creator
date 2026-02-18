#!/usr/bin/env python3
"""
Synchronizer for manim video with audio track.
Uses ffmpeg to synchronize video steps with audio timestamps.
"""

import os
import json
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class ManimVideoSynchronizer:
    def __init__(self, pipeline_dir: str, manim_video_path: Optional[str] = None, audio_path: Optional[str] = None):
        """
        Initialize video synchronizer
        
        Args:
            pipeline_dir: Pipeline directory
            manim_video_path: Optional path to manim video file (defaults to manim_video.mp4)
            audio_path: Optional path to audio file (defaults to audio.mp3)
        """
        self.pipeline_dir = Path(pipeline_dir)
        
        # Настройка пути к аудио
        if audio_path:
            self.audio_file = Path(audio_path) if Path(audio_path).is_absolute() else self.pipeline_dir / audio_path
        else:
            self.audio_file = self.pipeline_dir / "audio.mp3"

        # Настройка пути к видео
        if manim_video_path:
            self.manim_video = Path(manim_video_path) if Path(manim_video_path).is_absolute() else self.pipeline_dir / manim_video_path
        else:
            self.manim_video = self.pipeline_dir / "manim_video.mp4"
    
    def get_audio_duration(self, audio_file: Path) -> float:
        """
        Get audio duration in seconds
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"❌ Ошибка определения длительности аудио ({audio_file}): {e}")
            return 0.0
    
    def get_video_duration(self, video_file: Path) -> float:
        """
        Get video duration in seconds
        
        Args:
            video_file: Path to video file
            
        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"❌ Ошибка определения длительности видео: {e}")
            return 0.0
    
    def synchronize_video(self, step_timestamps: List[float],
                         step_durations: List[float],
                         intro_duration: float,
                         output_file: Path) -> bool:
        """
        Synchronize manim video with audio using step timestamps
        
        Args:
            step_timestamps: List of step start timestamps
            step_durations: List of step durations
            intro_duration: Duration of intro section
            output_file: Path to output synchronized video
            
        Returns:
            True if successful
        """
        if not self.audio_file.exists():
            print(f"❌ Аудио файл не найден: {self.audio_file}")
            return False
        
        if not self.manim_video.exists():
            print(f"❌ Manim видео не найдено: {self.manim_video}")
            return False
        
        # Get durations
        audio_duration = self.get_audio_duration(self.audio_file)
        video_duration = self.get_video_duration(self.manim_video)
        
        print(f"📊 Длительность аудио ({self.audio_file.name}): {audio_duration:.2f}с")
        print(f"📊 Длительность manim видео: {video_duration:.2f}с")
        
        # Calculate speed factor to match audio duration
        if video_duration > 0:
            speed_factor = video_duration / audio_duration
        else:
            print("❌ Не удалось определить длительность видео")
            return False
        
        print(f"📊 Коэффициент скорости: {speed_factor:.3f}")
        
        # If video is shorter than audio, we need to slow it down
        # If video is longer than audio, we need to speed it up
        if abs(speed_factor - 1.0) < 0.01:
            # Durations are very close, no need to adjust speed
            print("✅ Длительности совпадают, синхронизация не требуется")
            # Just combine audio and video
            cmd = [
                "ffmpeg", "-y",
                "-i", str(self.manim_video),
                "-i", str(self.audio_file),
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(output_file)
            ]
        else:
            # Adjust video speed to match audio duration
            print(f"⚙️ Применяем коэффициент скорости: {speed_factor:.3f}")
            
            # Use setpts filter to adjust speed
            # setpts=PTS/speed_factor means: if speed_factor > 1, video slows down
            # if speed_factor < 1, video speeds up
            cmd = [
                "ffmpeg", "-y",
                "-i", str(self.manim_video),
                "-i", str(self.audio_file),
                "-filter_complex",
                f"[0:v]setpts=PTS/{speed_factor}[v]",
                "-map", "[v]",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_file)
            ]
        
        print("🎬 Объединяем видео и аудио...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Видео синхронизировано: {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка ffmpeg: {e}")
            print(f"Stderr: {e.stderr}")
            return False
    
    def process_pipeline(self, timestamps_file: str, output_file: str) -> bool:
        """
        Complete synchronization pipeline
        
        Args:
            timestamps_file: Path to step_timestamps.json
            output_file: Path to output video file
            
        Returns:
            True if successful
        """
        # Load timestamps
        timestamps_path = Path(timestamps_file)
        if not timestamps_path.exists():
            print(f"❌ Файл таймстампов не найден: {timestamps_path}")
            return False
        
        with open(timestamps_path, 'r', encoding='utf-8') as f:
            timestamps_data = json.load(f)
        
        step_timestamps = timestamps_data.get('step_timestamps', [])
        step_durations = timestamps_data.get('step_durations', [])
        intro_duration = timestamps_data.get('intro_duration', 0)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return self.synchronize_video(
            step_timestamps,
            step_durations,
            intro_duration,
            output_path
        )


def main():
    parser = argparse.ArgumentParser(
        description="Синхронизация manim видео с аудио дорожкой"
    )
    parser.add_argument('--pipeline-dir', '-d', required=True,
                       help='Директория пайплайна')
    parser.add_argument('--timestamps-file', '-t', default='step_timestamps.json',
                       help='Путь к файлу с таймстампами')
    parser.add_argument('--output', '-o', default='video.mp4',
                       help='Путь к выходному видео файлу')
    parser.add_argument('--manim-video', '-m', default=None,
                       help='Путь к manim видео файлу (по умолчанию manim_video.mp4)')
    parser.add_argument('--audio-source', '-a', default=None,
                       help='Путь к аудио файлу (по умолчанию audio.mp3 в директории пайплайна)')
    
    args = parser.parse_args()
    
    # Handle paths
    pipeline_dir = Path(args.pipeline_dir).resolve()
    
    # Helper function to resolve file paths
    def resolve_file_path(file_path_str: str, default_name: str) -> Path:
        """Resolve file path - check if absolute, if path contains pipeline_dir, or relative to pipeline_dir"""
        file_path = Path(file_path_str)
        
        # If absolute path, use as is
        if file_path.is_absolute():
            return file_path
        
        # Check if the path already contains the full pipeline_dir path
        if str(file_path).startswith(str(pipeline_dir)):
            return file_path.resolve()
        
        # If file exists at the given path, use it
        if file_path.exists():
            return file_path.resolve()
        
        # Otherwise, make it relative to pipeline_dir (just use filename)
        filename = file_path.name if file_path.name else default_name
        return (pipeline_dir / filename).resolve()
    
    timestamps_file = resolve_file_path(args.timestamps_file, "step_timestamps.json")
    output_file = resolve_file_path(args.output, "video.mp4")
    manim_video_path = resolve_file_path(args.manim_video, "manim_video.mp4") if args.manim_video else None
    
    # Обрабатываем путь к аудио отдельно, так как он может быть None
    audio_source_path = None
    if args.audio_source:
        audio_source_path = resolve_file_path(args.audio_source, "audio.mp3")

    synchronizer = ManimVideoSynchronizer(
        str(pipeline_dir), 
        str(manim_video_path) if manim_video_path else None,
        str(audio_source_path) if audio_source_path else None
    )
    
    success = synchronizer.process_pipeline(str(timestamps_file), str(output_file))
    
    if success:
        print("\n✅ Синхронизация завершена успешно")
        return 0
    else:
        print("\n❌ Синхронизация не удалась")
        return 1


if __name__ == "__main__":
    exit(main())