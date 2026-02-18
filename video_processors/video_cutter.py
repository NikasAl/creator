#!/usr/bin/env python3
"""
Video cutter for editing original video with new audio track.
Supports cutting/skipping parts or speeding up video to match new audio duration.
"""

import os
import subprocess
import argparse
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
import math


class VideoCutter:
    def __init__(self, pipeline_dir: str):
        """
        Initialize video cutter
        
        Args:
            pipeline_dir: Pipeline directory containing video and audio files
        """
        self.pipeline_dir = Path(pipeline_dir)
        self.original_video = self.pipeline_dir / "original_video.mp4"
        self.new_audio = self.pipeline_dir / "audio.mp3"
        
        # Check required files
        if not self.original_video.exists():
            raise ValueError(f"Исходное видео не найдено: {self.original_video}")
        if not self.new_audio.exists():
            raise ValueError(f"Новый аудио файл не найден: {self.new_audio}")
    
    def get_video_duration(self, video_path: Path) -> float:
        """
        Get video duration in seconds
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds
        """
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            raise RuntimeError(f"Не удалось получить длительность видео: {e}")
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """
        Get audio duration in seconds
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds
        """
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(audio_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            raise RuntimeError(f"Не удалось получить длительность аудио: {e}")
    
    def get_video_resolution(self, video_path: Path) -> Tuple[int, int]:
        """
        Get video resolution
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (width, height)
        """
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
            "-of", "csv=p=0", str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            width, height = result.stdout.strip().split(',')
            return int(width), int(height)
        except (subprocess.CalledProcessError, ValueError) as e:
            raise RuntimeError(f"Не удалось получить разрешение видео: {e}")
    
    def cut_video_proportional(self, output_path: Path, target_duration: float) -> bool:
        """
        Cut video proportionally to match target duration
        
        Args:
            output_path: Output video path
            target_duration: Target duration in seconds
            
        Returns:
            True if successful
        """
        try:
            original_duration = self.get_video_duration(self.original_video)
            
            if target_duration >= original_duration:
                print(f"⚠️ Целевая длительность ({target_duration:.2f}с) больше или равна исходной ({original_duration:.2f}с)")
                print("Будет использован весь исходный видео с повторением последнего кадра")
                return self._extend_video(output_path, target_duration)
            
            # Calculate cut ratio
            cut_ratio = target_duration / original_duration
            print(f"📊 Исходная длительность: {original_duration:.2f}с")
            print(f"📊 Целевая длительность: {target_duration:.2f}с")
            print(f"📊 Коэффициент обрезки: {cut_ratio:.3f}")
            
            # Use ffmpeg to cut video proportionally
            cmd = [
                "ffmpeg", "-y",
                "-i", str(self.original_video),
                "-i", str(self.new_audio),
                "-t", str(target_duration),
                "-c:v", "libx264",
                "-crf", "23",
                "-preset", "fast",
                "-c:a", "aac",
                "-map", "0:v:0",  # Video from first input
                "-map", "1:a:0",  # Audio from second input
                "-shortest",  # End when shortest stream ends
                "-movflags", "+faststart",
                str(output_path)
            ]
            
            print("🎬 Обрезаем видео пропорционально...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✅ Видео обрезано успешно")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка обрезки видео: {e}")
            if e.stderr:
                print(f"Детали ошибки: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return False
    
    def speed_up_video(self, output_path: Path, target_duration: float) -> bool:
        """
        Speed up video to match target duration
        
        Args:
            output_path: Output video path
            target_duration: Target duration in seconds
            
        Returns:
            True if successful
        """
        try:
            original_duration = self.get_video_duration(self.original_video)
            
            if target_duration >= original_duration:
                print(f"⚠️ Целевая длительность ({target_duration:.2f}с) больше или равна исходной ({original_duration:.2f}с)")
                print("Будет использован весь исходный видео с повторением последнего кадра")
                return self._extend_video(output_path, target_duration)
            
            # Calculate speed factor
            speed_factor = original_duration / target_duration
            print(f"📊 Исходная длительность: {original_duration:.2f}с")
            print(f"📊 Целевая длительность: {target_duration:.2f}с")
            print(f"📊 Коэффициент ускорения: {speed_factor:.3f}")
            
            # Limit speed factor to reasonable range
            if speed_factor > 4.0:
                print("⚠️ Коэффициент ускорения слишком большой (>4x), ограничиваем до 4x")
                speed_factor = 4.0
            
            # Use ffmpeg to speed up video
            cmd = [
                "ffmpeg", "-y",
                "-i", str(self.original_video),
                "-i", str(self.new_audio),
                "-filter_complex", f"[0:v]setpts={1/speed_factor}*PTS[v];[0:a]atempo={speed_factor}[a]",
                "-map", "[v]",
                "-map", "1:a:0",  # Audio from second input
                "-c:v", "libx264",
                "-crf", "23",
                "-preset", "fast",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(output_path)
            ]
            
            print("🎬 Ускоряем видео...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✅ Видео ускорено успешно")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка ускорения видео: {e}")
            if e.stderr:
                print(f"Детали ошибки: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return False
    
    def _extend_video(self, output_path: Path, target_duration: float) -> bool:
        """
        Extend video by repeating last frame to match target duration
        
        Args:
            output_path: Output video path
            target_duration: Target duration in seconds
            
        Returns:
            True if successful
        """
        try:
            original_duration = self.get_video_duration(self.original_video)
            extension_duration = target_duration - original_duration
            
            print(f"📊 Расширяем видео на {extension_duration:.2f}с повторением последнего кадра")
            
            # Create extended video
            cmd = [
                "ffmpeg", "-y",
                "-i", str(self.original_video),
                "-i", str(self.new_audio),
                "-filter_complex", f"[0:v]tpad=stop_mode=clone:stop_duration={extension_duration}[v]",
                "-map", "[v]",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-crf", "23",
                "-preset", "fast",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✅ Видео расширено успешно")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка расширения видео: {e}")
            if e.stderr:
                print(f"Детали ошибки: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return False
    
    def create_final_video(self, output_path: Path, strategy: str = "cut") -> bool:
        """
        Create final video with new audio track
        
        Args:
            output_path: Output video path
            strategy: Strategy to use ("cut" or "speed")
            
        Returns:
            True if successful
        """
        try:
            # Get durations
            video_duration = self.get_video_duration(self.original_video)
            audio_duration = self.get_audio_duration(self.new_audio)
            
            print(f"📊 Длительность исходного видео: {video_duration:.2f}с")
            print(f"📊 Длительность нового аудио: {audio_duration:.2f}с")
            
            # Choose strategy based on duration difference
            if strategy == "cut":
                return self.cut_video_proportional(output_path, audio_duration)
            elif strategy == "speed":
                return self.speed_up_video(output_path, audio_duration)
            else:
                print(f"❌ Неизвестная стратегия: {strategy}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка создания финального видео: {e}")
            return False
    
    def preview_strategies(self) -> None:
        """
        Preview both strategies and show duration differences
        """
        try:
            video_duration = self.get_video_duration(self.original_video)
            audio_duration = self.get_audio_duration(self.new_audio)
            
            print(f"📊 Анализ длительностей:")
            print(f"   Исходное видео: {video_duration:.2f}с")
            print(f"   Новое аудио: {audio_duration:.2f}с")
            print(f"   Разница: {abs(video_duration - audio_duration):.2f}с")
            
            if audio_duration < video_duration:
                cut_ratio = audio_duration / video_duration
                print(f"📊 Стратегия 'cut': обрезать до {cut_ratio:.1%} от исходной длины")
            else:
                speed_factor = video_duration / audio_duration
                print(f"📊 Стратегия 'speed': ускорить в {speed_factor:.2f} раза")
                
        except Exception as e:
            print(f"❌ Ошибка анализа: {e}")


def main():
    parser = argparse.ArgumentParser(description="Обрезка и редактирование видео с новым аудио")
    parser.add_argument('pipeline_dir', help='Директория пайплайна')
    parser.add_argument('--output', '-o', help='Выходной файл (по умолчанию: video.mp4)')
    parser.add_argument('--strategy', choices=['cut', 'speed'], default='cut',
                       help='Стратегия обработки: cut (обрезать) или speed (ускорить)')
    parser.add_argument('--preview', action='store_true', help='Только показать анализ длительностей')
    
    args = parser.parse_args()
    
    try:
        cutter = VideoCutter(args.pipeline_dir)
        
        if args.preview:
            cutter.preview_strategies()
            return 0
        
        output_path = Path(args.output) if args.output else Path(args.pipeline_dir) / "video.mp4"
        
        success = cutter.create_final_video(output_path, args.strategy)
        if success:
            print(f"✅ Финальное видео создано: {output_path}")
            return 0
        else:
            return 1
            
    except ValueError as e:
        print(f"❌ Ошибка инициализации: {e}")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
