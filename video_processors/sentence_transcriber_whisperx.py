#!/usr/bin/env python3
"""
sentence_transcriber_whisperx.py
Транскрибатор на основе WhisperX: whisper + wav2vec2 alignment.

Ключевые преимущества перед обычным whisper:
- Точная привязка к слову (~50мс вместо ~1с у обычного whisper)
- Лучшее распознавание начала аудио (меньше пропусков первых фраз)
- Слово-уровневые таймстампы с последующей агрегацией в сегменты

Использует ту же модель whisper (medium по умолчанию), плюс лёгкую
wav2vec2 модель для выравнивания (~300MB дополнительно).

Выходной формат совместим с sentence_transcriber.py (sentence_timestamps.json).
"""

import argparse
import os
import sys
import json
import subprocess
import re


def ensure_whisperx():
    """Проверяет и при необходимости устанавливает whisperx."""
    try:
        import whisperx
        return whisperx
    except ImportError:
        print("📦 WhisperX не установлен. Устанавливаем...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "whisperx"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        # Также устанавливаем transformers если нет (нужен для alignment)
        try:
            import transformers
        except ImportError:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "transformers"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        import whisperx
        return whisperx


def format_time(seconds):
    """Преобразует секунды (float) в формат HH:MM:SS."""
    seconds = int(round(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"


def extract_keywords(text, limit=220):
    """
    Превращает связный текст в список уникальных ключевых слов.
    Используется как initial_prompt для улучшения распознавания.
    """
    if not text:
        return None
    clean_text = re.sub(r"\"", "", text)
    words = re.findall(r"\b\w+\b", clean_text)
    unique_words = set(words)
    priority_words = sorted([w for w in unique_words if w[0].isupper() or len(w) > 4])
    prompt_str = ", ".join(priority_words)
    return prompt_str[:limit]


def create_readable_log(segments, output_path, pause_threshold=2.0):
    """Генерирует читаемый лог с объединением блоков и метками пауз."""
    if not segments:
        return

    lines = []
    current_start = segments[0]['start']
    current_end = segments[0]['end']
    current_text = segments[0]['text'].strip()

    for i in range(1, len(segments)):
        seg = segments[i]
        start = seg['start']
        end = seg['end']
        text = seg['text'].strip()
        gap = start - current_end

        if gap < pause_threshold:
            current_end = end
            current_text += " " + text
        else:
            time_tag = f"[{format_time(current_start)}-{format_time(current_end)}]"
            lines.append(f"{time_tag} {current_text}")
            lines.append(f"[[PAUSE:{int(gap)}]]")
            current_start = start
            current_end = end
            current_text = text

    time_tag = f"[{format_time(current_start)}-{format_time(current_end)}]"
    lines.append(f"{time_tag} {current_text}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"📝 Читаемый лог сохранен: {output_path}")


def transcribe_whisperx(audio_path, output_dir, json_name, language,
                         hint_text="", model_name="medium", device="cpu",
                         compute_type="int8", make_readable=False):
    """
    Транскрибация через WhisperX с wav2vec2 alignment.

    WhisperX pipeline:
    1. Загрузка whisper модели (та же что в обычном whisper)
    2. Транскрибация (аналогично whisper.transcribe)
    3. wav2vec2 forced alignment — точная привязка слов к аудио (~50мс)
    4. Агрегация слово-уровневых таймстампов в сегменты (как у обычного whisper)
    """
    whisperx = ensure_whisperx()

    print(f"🎤 WhisperX: загрузка модели '{model_name}' на {device}...")
    print(f"   compute_type={compute_type}")

    # 1. Загрузка модели
    model = whisperx.load_model(
        model_name,
        device,
        compute_type=compute_type,
        language=language
    )

    # 2. Транскрибация
    print("🎤 WhisperX: транскрибация...")
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=16)

    # 3. Alignment — ключевое преимущество WhisperX
    print("🔗 WhisperX: wav2vec2 alignment (точная привязка слов)...")
    try:
        align_model, align_metadata = whisperx.load_align_model(
            language_code=language,
            device=device
        )
        result = whisperx.align(
            result["segments"],
            align_model,
            align_metadata,
            audio,
            device,
            return_char_alignments=False
        )
        aligned = True
        print("✅ Alignment выполнен успешно")
    except Exception as e:
        print(f"⚠️ Alignment не удался ({e}), используем raw whisper таймстампы")
        aligned = False

    # 4. Формируем совместимый output (start/end/text сегменты)
    final_segments = []

    if aligned and "word_segments" in str(type(result)):
        # WhisperX возвращает segments с word-level данными
        for seg in result.get("segments", []):
            # У WhisperX сегменты могут содержать слова с точными таймстампами
            text = seg.get("text", "").strip()
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)

            # Если есть слова — берём таймстампы от первого/последнего слова
            words = seg.get("words", [])
            if words:
                start = words[0].get("start", start)
                end = words[-1].get("end", end)

            if text:
                final_segments.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "text": text
                })
    else:
        # Fallback — берём сегменты как есть
        for seg in result.get("segments", []):
            text = seg.get("text", "").strip()
            if text:
                final_segments.append({
                    "start": round(seg.get("start", 0.0), 2),
                    "end": round(seg.get("end", 0.0), 2),
                    "text": text
                })

    # Полный текст
    full_text = " ".join(s["text"] for s in final_segments)

    final_data = {
        "text": full_text,
        "segments": final_segments,
        "whisperx_aligned": aligned
    }

    # Сохраняем JSON
    out_path = os.path.join(output_dir, json_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Таймстампы сохранены: {out_path}")
    print(f"   Сегментов: {len(final_segments)}")
    if aligned:
        print(f"   Alignment: ✅ (точность ~50мс на уровне слов)")

    # Читаемый лог
    if make_readable and final_segments:
        txt_filename = os.path.splitext(json_name)[0] + "_readable.txt"
        txt_path = os.path.join(output_dir, txt_filename)
        create_readable_log(final_segments, txt_path, pause_threshold=2.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="WhisperX транскрибатор с wav2vec2 alignment"
    )
    parser.add_argument("--audio", required=True, help="Путь к аудио файлу")
    parser.add_argument("--output-dir", required=True, help="Директория для выхода")
    parser.add_argument("--json-filename", default="sentence_timestamps.json")
    parser.add_argument("--language", default="ru")
    parser.add_argument("--model", default="medium",
                        help="Модель whisper: tiny, base, small, medium, large")
    parser.add_argument("--device", default="cpu",
                        help="Устройство: cpu или cuda")
    parser.add_argument("--compute-type", default="int8",
                        help="Тип вычислений: int8, float16, float32")
    parser.add_argument("--hint-file", help="Файл с текстом для улучшения распознавания")
    parser.add_argument("--readable", action="store_true",
                        help="Создать текстовый файл с блоками и паузами")

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    hint_text = ""
    if args.hint_file and os.path.exists(args.hint_file):
        with open(args.hint_file, 'r', encoding='utf-8') as f:
            hint_text = f.read().replace('\n', ' ')

    transcribe_whisperx(
        audio_path=args.audio,
        output_dir=args.output_dir,
        json_name=args.json_filename,
        language=args.language,
        hint_text=hint_text,
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        make_readable=args.readable
    )