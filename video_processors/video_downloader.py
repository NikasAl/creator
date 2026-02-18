#!/usr/bin/env python3
"""
Video downloader using yt-dlp for downloading videos from various platforms.
Supports YouTube, Rutube, and other platforms supported by yt-dlp.
"""

import os
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import json
import tempfile


class VideoDownloader:
    def __init__(self, output_dir: str = "output"):
        """
        Initialize video downloader
        
        Args:
            output_dir: Directory to save downloaded files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Check if yt-dlp is available
        self._check_yt_dlp()
    
    def _check_yt_dlp(self) -> bool:
        """Check if yt-dlp is installed and available"""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ yt-dlp доступен: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ yt-dlp не найден. Установите: pip install yt-dlp")
            return False
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get video information without downloading
        
        Args:
            url: Video URL
            
        Returns:
            Video metadata or None if failed
        """
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                url
            ]
            
            print(f"🔍 Получаем информацию о видео: {url}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            info = json.loads(result.stdout)
            return info
            
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"❌ Ошибка получения информации о видео: {e}")
            return None
    
    def download_video(self, url: str, video_filename: str = "original_video.mp4", 
                      audio_filename: str = "original_audio.mp3") -> Tuple[Optional[Path], Optional[Path]]:
        """
        Download video and extract audio
        
        Args:
            url: Video URL to download
            video_filename: Name for downloaded video file
            audio_filename: Name for extracted audio file
            
        Returns:
            Tuple of (video_path, audio_path) or (None, None) if failed
        """
        video_path = self.output_dir / video_filename
        audio_path = self.output_dir / audio_filename
        
        try:
            # Download video
            print(f"📥 Скачиваем видео: {url}")
            cmd = [
                'yt-dlp',
                '-f', 'best[height<=1080]',  # Limit to 1080p max
                '-o', str(video_path.with_suffix('.%(ext)s')),
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✅ Видео скачано успешно")
            
            # Find the actual downloaded file (yt-dlp might change extension)
            downloaded_files = list(self.output_dir.glob(f"{video_path.stem}.*"))
            if downloaded_files:
                actual_video = downloaded_files[0]
                if actual_video != video_path:
                    actual_video.rename(video_path)
            else:
                print("❌ Скачанный файл не найден")
                return None, None
            
            # Extract audio
            print("🎵 Извлекаем аудио дорожку...")
            audio_cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-vn',  # No video
                '-acodec', 'mp3',
                '-ab', '128k',  # Audio bitrate
                str(audio_path)
            ]
            
            result = subprocess.run(audio_cmd, capture_output=True, text=True, check=True)
            print("✅ Аудио извлечено успешно")
            
            return video_path, audio_path
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка скачивания: {e}")
            if e.stderr:
                print(f"Детали ошибки: {e.stderr}")
            return None, None
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return None, None
    
    def download_audio_only(self, url: str, audio_filename: str = "original_audio.mp3") -> Optional[Path]:
        """
        Download only audio track
        
        Args:
            url: Video URL
            audio_filename: Name for audio file
            
        Returns:
            Path to audio file or None if failed
        """
        audio_path = self.output_dir / audio_filename
        
        try:
            print(f"🎵 Скачиваем только аудио: {url}")
            cmd = [
                'yt-dlp',
                '-x',  # Extract audio
                '--audio-format', 'mp3',
                '--audio-quality', '128K',
                '-o', str(audio_path.with_suffix('.%(ext)s')),
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✅ Аудио скачано успешно")
            
            # Find the actual downloaded file
            downloaded_files = list(self.output_dir.glob(f"{audio_path.stem}.*"))
            if downloaded_files:
                actual_audio = downloaded_files[0]
                if actual_audio != audio_path:
                    actual_audio.rename(audio_path)
                return audio_path
            else:
                print("❌ Скачанный аудио файл не найден")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка скачивания аудио: {e}")
            if e.stderr:
                print(f"Детали ошибки: {e.stderr}")
            return None
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="Скачивание видео с помощью yt-dlp")
    parser.add_argument('url', help='URL видео для скачивания')
    parser.add_argument('--output-dir', '-o', default='output', help='Директория для сохранения')
    parser.add_argument('--video-only', action='store_true', help='Скачать только видео')
    parser.add_argument('--audio-only', action='store_true', help='Скачать только аудио')
    parser.add_argument('--info-only', action='store_true', help='Только получить информацию о видео')
    
    args = parser.parse_args()
    
    downloader = VideoDownloader(args.output_dir)
    
    if args.info_only:
        info = downloader.get_video_info(args.url)
        if info:
            print(f"📺 Название: {info.get('title', 'Неизвестно')}")
            print(f"👤 Автор: {info.get('uploader', 'Неизвестно')}")
            print(f"⏱️ Длительность: {info.get('duration', 'Неизвестно')} сек")
            print(f"📊 Разрешение: {info.get('width', '?')}x{info.get('height', '?')}")
        return 0
    
    if args.audio_only:
        audio_path = downloader.download_audio_only(args.url)
        if audio_path:
            print(f"✅ Аудио сохранено: {audio_path}")
            return 0
        else:
            return 1
    
    if args.video_only:
        video_path, _ = downloader.download_video(args.url)
        if video_path:
            print(f"✅ Видео сохранено: {video_path}")
            return 0
        else:
            return 1
    
    # Download both video and audio
    video_path, audio_path = downloader.download_video(args.url)
    if video_path and audio_path:
        print(f"✅ Видео сохранено: {video_path}")
        print(f"✅ Аудио сохранено: {audio_path}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
