#!/usr/bin/env python3
"""
Утилита нарезки короткого фрагмента из видео конкретного пайплайна
с возможностью сделать вертикальную (9:16) версию из исходного горизонтального видео.

Примеры:
  1) Обрезать фрагмент:
     python3 video_processors/clip_pipeline_video.py \
       --pipeline-dir pipeline_Gorbunok \
       --start 00:00:10 --end 00:00:30 \
       --out gorbunok_clip.mp4

  2) Вертикальный ролик 1080x1920 (кроп по центру):
     python3 video_processors/clip_pipeline_video.py \
       --pipeline-dir pipeline_Gorbunok \
       --start 10 --end 30 \
       --vertical crop --vwidth 1080 --vheight 1920 \
       --out gorbunok_clip_vertical.mp4

  3) Вертикальный ролик с блюром (фон — размытие исходного), 720x1280:
     python3 video_processors/clip_pipeline_video.py \
       --pipeline-dir pipeline_Gorbunok \
       --start 00:00:05 --end 00:00:20 \
       --vertical blur --vwidth 720 --vheight 1280
"""

import argparse
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def parse_time_to_seconds(value: str) -> float:
    """Парсит время в секундах. Поддержка форматов:
    - "SS" (секунды)
    - "MM:SS"
    - "HH:MM:SS"
    - а также числа с плавающей точкой для секунд
    """
    text = str(value).strip()
    if not text:
        raise ValueError("Пустое значение времени")

    # Попытка как число секунд (float)
    try:
        return float(text)
    except ValueError:
        pass

    parts = text.split(":")
    if len(parts) == 2:  # MM:SS
        m, s = parts
        return int(m) * 60 + float(s)
    if len(parts) == 3:  # HH:MM:SS
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)

    raise ValueError(f"Неподдерживаемый формат времени: {value}")


def get_input_video(pipeline_dir: Path) -> Path:
    """Возвращает путь к входному видео внутри пайплайна.
    Приоритет: video.mp4, затем video.mov, затем первый *.mp4"""
    candidates = [
        pipeline_dir / "video.mp4",
        pipeline_dir / "video.mov",
    ]
    for c in candidates:
        if c.exists():
            return c
    mp4s = sorted(pipeline_dir.glob("*.mp4"))
    if mp4s:
        return mp4s[0]
    raise FileNotFoundError(
        f"Не найдено входное видео в {pipeline_dir}. Ожидалось 'video.mp4' или любой *.mp4"
    )


def build_vertical_filter(mode: str, target_w: int, target_h: int) -> str:
    """Возвращает ffmpeg -vf фильтр для вертикального кадра.
    - mode == 'crop': кроп по центру, с сохранением высоты
    - mode == 'blur': размытие фонового слоя с вписанным резким центром
    """
    if mode == "crop":
        # Вписываем по высоте, затем кропаем по ширине до target_w
        # Используем setsar=1 для корректного соотношения сторон
        return (
            f"setsar=1,scale=-1:{target_h}:force_original_aspect_ratio=decrease,"
            f"crop={target_w}:{target_h}:(in_w-out_w)/2:(in_h-out_h)/2"
        )

    if mode == "blur":
        # Два слоя: фон (размытый, растянутый под 9:16) и верхний слой с вписыванием с чёрными полями
        # 1) scale_bg: растягиваем под target_w x target_h, затем блюрим
        # 2) scale_fg: вписываем ролик без искажений, паддинг по центру, накладываем поверх
        return (
            f"[0:v]setsar=1,scale={target_w}:{target_h},boxblur=20:1[bg];"
            f"[0:v]setsar=1,scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )

    raise ValueError("vertical mode должен быть 'crop' или 'blur'")


def format_seconds_ffmpeg(seconds: float) -> str:
    """Форматирует секунды в HH:MM:SS.mmm для ffmpeg."""
    if seconds < 0:
        raise ValueError("Время не может быть отрицательным")
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"


def run_ffmpeg(cmd: list) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr or result.stdout}")


def clip_video(
    input_video: Path,
    output_video: Path,
    start_sec: float,
    end_sec: float,
    vertical: Optional[str] = None,
    vertical_size: Optional[Tuple[int, int]] = None,
    reencode_crf: int = 22,
    reencode_preset: str = "fast",
) -> None:
    if end_sec <= start_sec:
        raise ValueError("Время конца должно быть больше времени начала")

    duration = end_sec - start_sec
    ss = format_seconds_ffmpeg(start_sec)
    t = f"{duration:.3f}"

    if vertical:
        if not vertical_size:
            vertical_size = (1080, 1920)
        vw, vh = vertical_size
        vf = build_vertical_filter(vertical, vw, vh)
        cmd = [
            "ffmpeg", "-y",
            "-ss", ss,
            "-i", str(input_video),
            "-t", t,
            "-filter_complex" if "overlay=" in vf else "-vf", vf,
            "-c:v", "libx264",
            "-crf", str(reencode_crf),
            "-preset", reencode_preset,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_video),
        ]
    else:
        # Горизонтальная версия: пытаемся без перекодирования видео-потока, если возможно
        # Ставим -ss перед -i для быстрого seek, затем -t и копирование
        cmd = [
            "ffmpeg", "-y",
            "-ss", ss,
            "-i", str(input_video),
            "-t", t,
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_video),
        ]

    run_ffmpeg(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Нарезка фрагмента из видео пайплайна с опциональным вертикальным вариантом")
    parser.add_argument("--pipeline-dir", required=True, help="Путь к каталогу пайплайна (где лежит video.mp4)")
    parser.add_argument("--start", required=True, help="Время начала (SS | MM:SS | HH:MM:SS)")
    parser.add_argument("--end", required=True, help="Время конца (SS | MM:SS | HH:MM:SS)")
    parser.add_argument("--out", help="Выходной файл. По умолчанию: <pipeline>/clip_<start>_<end>.mp4")
    parser.add_argument("--vertical", choices=["crop", "blur"], help="Сделать вертикальный ролик: режим 'crop' или 'blur'")
    parser.add_argument("--vwidth", type=int, default=1080, help="Ширина вертикального видео (по умолчанию 1080)")
    parser.add_argument("--vheight", type=int, default=1920, help="Высота вертикального видео (по умолчанию 1920)")
    parser.add_argument("--crf", type=int, default=22, help="CRF при перекодировании (меньше — лучше качество)")
    parser.add_argument("--preset", default="fast", help="x264 preset при перекодировании (ultrafast..veryslow)")

    args = parser.parse_args()

    pipeline_dir = Path(args.pipeline_dir)
    if not pipeline_dir.exists():
        print(f"❌ Каталог пайплайна не найден: {pipeline_dir}")
        return 1

    try:
        start_sec = parse_time_to_seconds(args.start)
        end_sec = parse_time_to_seconds(args.end)
    except Exception as e:
        print(f"❌ Ошибка парсинга времени: {e}")
        return 1

    try:
        input_video = get_input_video(pipeline_dir)
    except Exception as e:
        print(f"❌ {e}")
        return 1

    if args.out:
        output_path = Path(args.out)
    else:
        start_tag = args.start.replace(":", "-")
        end_tag = args.end.replace(":", "-")
        suffix = "vertical" if args.vertical else "clip"
        output_path = pipeline_dir / f"{suffix}_{start_tag}_{end_tag}.mp4"

    try:
        vertical_size: Optional[Tuple[int, int]] = None
        if args.vertical:
            vertical_size = (int(args.vwidth), int(args.vheight))

        clip_video(
            input_video=input_video,
            output_video=output_path,
            start_sec=start_sec,
            end_sec=end_sec,
            vertical=args.vertical,
            vertical_size=vertical_size,
            reencode_crf=int(args.crf),
            reencode_preset=str(args.preset),
        )
        print(f"✅ Готово: {output_path}")
        return 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


