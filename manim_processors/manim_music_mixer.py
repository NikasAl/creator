#!/usr/bin/env python3
"""
Music mixer for manim videos.
Adds background music from music_*.mp3 files to video.mp4.
Automatically adjusts music volume to be 10-15 dB quieter than voice.
"""

import os
import argparse
import subprocess
import sys
import re
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class ManimMusicMixer:
    def __init__(self, pipeline_dir: str, video_path: Optional[str] = None):
        self.pipeline_dir = Path(pipeline_dir)

        # Настройка пути к видео
        if video_path:
            self.video_file = Path(video_path) if Path(video_path).is_absolute() else self.pipeline_dir / video_path
        else:
            self.video_file = self.pipeline_dir / "video.mp4"

    def find_music_files(self) -> List[Path]:
        """
        Find all music_*.mp3 files in pipeline directory.
        If no music files are found, offer interactive selection from ~/Музыка/Фон using fzf with preview.
        """
        # 1. Сначала ищем уже существующие файлы в папке проекта
        music_files = sorted(self.pipeline_dir.glob("music_*.mp3"))
        if music_files:
            return music_files

        # 2. Если файлов нет, запускаем интерактивный выбор
        print("ℹ️ Файлы music_*.mp3 не найдены в директории пайплайна")

        music_source_dir = Path("~/Музыка/Фон").expanduser()
        if not music_source_dir.exists():
            print(f"⚠️ Папка с музыкой не найдена: {music_source_dir}")
            return []

        print(f"💡 Открываем выбор музыки из: {music_source_dir}")
        print("   (TAB - выбрать несколько, ENTER - подтвердить, ESC - отмена)")
        print("   (Для превью используется mpv, убедитесь, что звук включен)")

        try:
            # --- ВАЖНЫЕ ИЗМЕНЕНИЯ ---

            # 1. Команда для превью.
            # Мы убираем --quiet, чтобы видеть ошибки, если они есть.
            # Используем одинарные кавычки внутри, поэтому снаружи будем оборачивать аккуратно.
            # {q} - это placeholder fzf для пути к файлу (экранированный)
            preview_cmd = "mpv --no-video --msg-level=all=warn --volume=60 --start=0% --length=60 {}"

            # 2. Сборка команды fzf.
            # Используем shlex.quote (хотя тут мы формируем строку для shell=True, делаем экранирование вручную для надежности)
            # В Python f-string двойные фигурные скобки {{}} превращаются в одну {}
            # Обратите внимание на экранирование кавычек \".

            # find command
            find_part = f"find '{music_source_dir}' -type f -iname '*.mp3' -print0"

            # fzf command
            # --preview принимает строку команды. Мы передаем ей '{}' (fzf подставит файл).
            fzf_part = (
                f"fzf --multi --read0 --print0 "
                f"--preview \"{preview_cmd}\" "
                f"--preview-window='up:1' "
                f"--prompt='🎧 Выбор (TAB/Enter)> '"
            )

            full_cmd = f"{find_part} | {fzf_part}"

            # 3. Запуск subprocess
            # ВАЖНО: stderr=None позволяет fzf писать интерфейс прямо в терминал пользователя.
            # stdout=subprocess.PIPE позволяет нам перехватить выбранные пути.
            result = subprocess.run(
                full_cmd,
                shell=True,
                stdout=subprocess.PIPE,  # Читаем выбор
                stderr=None,             # Оставляем интерфейс fzf и ошибки mpv видимыми
                check=True
            )

            # Декодируем вывод (разделен \x00 из-за --print0)
            raw_paths = result.stdout.split(b'\x00')
            # Фильтруем пустые строки
            selected_paths = [Path(p.decode('utf-8')) for p in raw_paths if p]

            if not selected_paths:
                print("❌ Выбор пуст (возможно, нажали Enter без выбора).")
                return []

            copied_files = []
            print(f"✅ Выбрано файлов: {len(selected_paths)}")

            for i, src_file in enumerate(selected_paths, 1):
                if not src_file.exists():
                    print(f"⚠️ Файл не найден: {src_file}")
                    continue

                dst_name = f"music_{i:02d}.mp3"
                dst_file = self.pipeline_dir / dst_name

                print(f"📎 Копируем {src_file.name} -> {dst_name}")
                shutil.copy2(src_file, dst_file)
                copied_files.append(dst_file)

            return copied_files

        except subprocess.CalledProcessError:
            # Обычно возникает, если нажали ESC (fzf возвращает код 130)
            print("\n❌ Выбор отменён пользователем.")
            return []
        except Exception as e:
            print(f"\n❌ Ошибка при выборе музыки: {e}")
            return []

    def get_audio_duration(self, audio_file: Path) -> float:
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
            print(f"❌ Ошибка определения длительности аудио ({audio_file.name}): {e}")
            return 0.0

    def get_video_duration(self, video_file: Path) -> float:
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

    def measure_rms_volume(self, audio_file: Path) -> Optional[float]:
        try:
            cmd = [
                "ffmpeg", "-i", str(audio_file),
                "-af", "volumedetect",
                "-f", "null", "-"
            ]
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, check=False
            )

            match = re.search(r'mean_volume:\s*([-\d.]+)\s*dB', result.stdout)
            if match: return float(match.group(1))

            match = re.search(r'mean_volume:\s*([-\d.]+)', result.stdout)
            if match: return float(match.group(1))

            return None
        except Exception as e:
            print(f"❌ Ошибка измерения громкости ({audio_file.name}): {e}")
            return None

    def concatenate_music_files(self, music_files: List[Path], output_file: Path) -> bool:
        if not music_files: return False

        if len(music_files) == 1:
            shutil.copy2(music_files[0], output_file)
            return True

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for music_file in music_files:
                # Экранирование одинарных кавычек для ffmpeg concat списка
                escaped_path = str(music_file).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        try:
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-map", "0:a", "-c", "copy", str(output_file)
            ]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка склейки музыки: {e.stderr}")
            return False
        finally:
            if os.path.exists(concat_file):
                os.unlink(concat_file)

    def prepare_music_track(self, music_file: Path, video_duration: float,
                           volume_db: float, output_file: Path) -> bool:
        music_duration = self.get_audio_duration(music_file)
        if music_duration <= 0: return False

        # Используем m4a как промежуточный формат для стабильности aac кодирования
        output_file_m4a = output_file.with_suffix('.m4a')

        filters = []
        filters.append(f"volume={volume_db}dB")

        fade_duration = min(2.0, video_duration * 0.1)
        fade_start = max(0, video_duration - fade_duration)
        filters.append(f"afade=t=out:st={fade_start:.2f}:d={fade_duration:.2f}")
        filters.append(f"atrim=0:{video_duration:.2f}")

        filter_complex = ",".join(filters)

        try:
            cmd_args = ["ffmpeg", "-y"]

            if music_duration < video_duration:
                loops_needed = int(video_duration / music_duration) + 1
                cmd_args.extend(["-stream_loop", str(loops_needed)])

            cmd_args.extend([
                "-i", str(music_file),
                "-map", "0:a",
                "-af", filter_complex,
                "-c:a", "aac", "-b:a", "192k",
                str(output_file_m4a)
            ])

            subprocess.run(cmd_args, capture_output=True, text=True, check=True)

            # Конвертируем в конечный формат, если нужно (например, обратно в mp3)
            if output_file.suffix.lower() == '.mp3':
                convert_cmd = [
                    "ffmpeg", "-y", "-i", str(output_file_m4a),
                    "-c:a", "libmp3lame", "-b:a", "192k", str(output_file)
                ]
                subprocess.run(convert_cmd, capture_output=True, text=True, check=True)
                output_file_m4a.unlink()
            elif output_file_m4a != output_file:
                shutil.move(str(output_file_m4a), str(output_file))

            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка подготовки трека: {e.stderr}")
            if output_file_m4a.exists(): output_file_m4a.unlink()
            return False

    def mix_music_with_video(self, video_file: Path, music_file: Path, output_file: Path) -> bool:
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_file),
                "-i", str(music_file),
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[a]",
                "-map", "0:v:0", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", str(output_file)
            ]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка сведения: {e.stderr}")
            return False

    def process(self, output_file: str, music_offset: float = 12.5) -> bool:
        if not self.video_file.exists():
            print(f"❌ Видео файл не найден: {self.video_file}")
            return False

        music_files = self.find_music_files()
        if not music_files:
            return False

        # Измеряем громкость голоса
        voice_volume = self.measure_rms_volume(self.video_file)
        if voice_volume is None:
            print("⚠️ Не удалось измерить громкость голоса, используем default -20 dB")
            voice_volume = -20.0

        # Склеиваем музыку во временный файл
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            temp_music_file = Path(tmp.name)

        try:
            if not self.concatenate_music_files(music_files, temp_music_file):
                return False

            music_volume = self.measure_rms_volume(temp_music_file) or -15.0

            # Расчет поправки громкости
            target_music_volume = voice_volume - music_offset
            volume_adjustment = target_music_volume - music_volume

            print(f"🎚️ Баланс: Голос {voice_volume:.1f}dB | Музыка {music_volume:.1f}dB")
            print(f"🎚️ Коррекция музыки: {volume_adjustment:+.1f} dB (Цель: {target_music_volume:.1f}dB)")

            video_duration = self.get_video_duration(self.video_file)

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp2:
                temp_prepared_file = Path(tmp2.name)

            if not self.prepare_music_track(temp_music_file, video_duration,
                                          volume_adjustment, temp_prepared_file):
                return False

            output_path = self.pipeline_dir / output_file
            temp_output = self.pipeline_dir / f"{output_path.stem}_tmp{output_path.suffix}"

            if self.mix_music_with_video(self.video_file, temp_prepared_file, temp_output):
                shutil.move(str(temp_output), str(output_path))
                print(f"✅ Готово: {output_path.name}")
                return True
            return False

        finally:
            if temp_music_file.exists(): temp_music_file.unlink()
            if 'temp_prepared_file' in locals() and temp_prepared_file.exists():
                temp_prepared_file.unlink()

def main():
    parser = argparse.ArgumentParser(description="Добавление фоновой музыки в manim видео")
    parser.add_argument('--pipeline-dir', '-d', required=True, help='Директория пайплайна')
    parser.add_argument('--video', '-v', default="video.mp4", help='Имя входного видео')
    parser.add_argument('--output', '-o', default=None, help='Имя выходного файла')
    parser.add_argument('--music-offset', type=float, default=12.5, help='Смещение громкости (dB)')

    args = parser.parse_args()
    pipeline_dir = Path(args.pipeline_dir).resolve()

    mixer = ManimMusicMixer(str(pipeline_dir), args.video)

    output_name = args.output or f"{Path(args.video).stem}_with_music{Path(args.video).suffix}"

    if mixer.process(output_name, music_offset=args.music_offset):
        return 0
    return 1

if __name__ == "__main__":
    exit(main())