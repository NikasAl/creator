#!/usr/bin/env python3
"""
Утилита для определения длительности аудио файлов
"""

import os
import argparse
from pathlib import Path
from typing import Optional

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

def get_audio_duration_librosa(audio_path: str) -> Optional[float]:
    """Получить длительность аудио через librosa"""
    try:
        duration = librosa.get_duration(path=audio_path)
        return duration
    except Exception as e:
        print(f"⚠️ Ошибка librosa: {e}")
        return None

def get_audio_duration_pydub(audio_path: str) -> Optional[float]:
    """Получить длительность аудио через pydub"""
    try:
        audio = AudioSegment.from_file(audio_path)
        duration = len(audio) / 1000.0  # pydub возвращает миллисекунды
        return duration
    except Exception as e:
        print(f"⚠️ Ошибка pydub: {e}")
        return None

def get_audio_duration_ffprobe(audio_path: str) -> Optional[float]:
    """Получить длительность аудио через ffprobe (если доступен)"""
    try:
        import subprocess
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', audio_path
        ], capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        print(f"⚠️ Ошибка ffprobe: {e}")
        return None

def get_audio_duration(audio_path: str) -> Optional[float]:
    """Получить длительность аудио файла любым доступным способом"""
    if not os.path.exists(audio_path):
        print(f"❌ Файл не найден: {audio_path}")
        return None
    
    # Пробуем разные методы
    methods = []
    
    if LIBROSA_AVAILABLE:
        methods.append(("librosa", get_audio_duration_librosa))
    
    if PYDUB_AVAILABLE:
        methods.append(("pydub", get_audio_duration_pydub))
    
    methods.append(("ffprobe", get_audio_duration_ffprobe))
    
    for method_name, method_func in methods:
        duration = method_func(audio_path)
        if duration is not None:
            return duration
    
    print("❌ Не удалось определить длительность аудио ни одним способом")
    return None

def main():
    parser = argparse.ArgumentParser(description="Определение длительности аудио файла")
    parser.add_argument("audio_file", help="Путь к аудио файлу")
    parser.add_argument("--format", choices=["seconds", "minutes", "mm:ss"], 
                       default="seconds", help="Формат вывода")
    
    args = parser.parse_args()
    
    duration = get_audio_duration(args.audio_file)
    if duration is None:
        return 1
    
    # Форматируем вывод
    if args.format == "seconds":
        print(f"{duration:.2f}")
    elif args.format == "minutes":
        print(f"{duration / 60:.2f}")
    elif args.format == "mm:ss":
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        print(f"{minutes:02d}:{seconds:02d}")
    
    return 0

if __name__ == "__main__":
    exit(main())
