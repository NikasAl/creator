#!/usr/bin/env python3
import argparse
import os
import json
import re
from dotenv import load_dotenv

def extract_keywords(text, limit=220):
    """
    Превращает связный текст в список уникальных ключевых слов.
    """
    if not text:
        return None

    clean_text = re.sub(r"\"", "", text)
    words = re.findall(r"\b\w+\b", clean_text)
    unique_words = set(words)
    priority_words = sorted([w for w in unique_words if w[0].isupper() or len(w) > 4])
    prompt_str = "Словарь: " + ", ".join(priority_words)

    return prompt_str[:limit]

def format_time(seconds):
    """Преобразует секунды (float) в формат HH:MM:SS"""
    seconds = int(round(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"

def create_readable_log(segments, output_path, pause_threshold=2.0):
    """
    Генерирует читаемый лог с объединением блоков и метками пауз.
    """
    if not segments:
        return

    lines = []

    # Инициализируем первый блок
    current_start = segments[0]['start']
    current_end = segments[0]['end']
    current_text = segments[0]['text'].strip()

    for i in range(1, len(segments)):
        seg = segments[i]
        start = seg['start']
        end = seg['end']
        text = seg['text'].strip()

        # Вычисляем паузу между концом предыдущего и началом текущего
        gap = start - current_end

        if gap < pause_threshold:
            # Если пауза маленькая, объединяем с текущим блоком
            current_end = end # Продлеваем конец
            current_text += " " + text
        else:
            # Если пауза большая, записываем накопленный блок
            time_tag = f"[{format_time(current_start)}-{format_time(current_end)}]"
            lines.append(f"{time_tag} {current_text}")

            # Добавляем маркер паузы
            lines.append(f"[[PAUSE:{int(gap)}]]")

            # Начинаем новый блок
            current_start = start
            current_end = end
            current_text = text

    # Записываем последний блок
    time_tag = f"[{format_time(current_start)}-{format_time(current_end)}]"
    lines.append(f"{time_tag} {current_text}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"📝 Читаемый лог сохранен: {output_path}")

def transcribe_segments(audio_path, output_dir, json_name, language, config_file, hint_text="", make_readable=False):
    if config_file: load_dotenv(config_file)

    use_local = os.getenv("USE_LOCAL_WHISPER", "true").lower() == "true"

    final_data = {
        "text": "",
        "segments": []
    }

    initial_prompt = extract_keywords(hint_text)

    if initial_prompt:
        print(f"💡 Сформирована безопасная подсказка (ключевые слова):")
        print(f"   {initial_prompt}...")

    if use_local:
        try:
            import whisper
            print("🎤 Запуск локального Whisper...")
            model_name = os.getenv("WHISPER_MODEL", "small")
            model = whisper.load_model(model_name)

            transcribe_options = {"language": language, "verbose": True}
            if initial_prompt:
                transcribe_options["initial_prompt"] = initial_prompt

            result = model.transcribe(audio_path, **transcribe_options)

            final_data["text"] = result["text"]
            for seg in result["segments"]:
                final_data["segments"].append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })

        except ImportError:
            print("❌ Whisper не установлен. pip install openai-whisper")
            exit(1)
    else:
        # API Whisper
        import requests
        print("🎤 Запуск Whisper API...")
        api_key = os.getenv("WHISPER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ Нет API ключа для Whisper")
            exit(1)

        data_payload = {
            "model": "whisper-1",
            "response_format": "verbose_json",
            "language": language
        }
        if initial_prompt:
            data_payload["prompt"] = initial_prompt

        with open(audio_path, "rb") as f:
            resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": f},
                data=data_payload
            )

        if resp.status_code != 200:
            print(f"❌ Ошибка API: {resp.text}")
            exit(1)

        data = resp.json()
        final_data["text"] = data["text"]
        for seg in data["segments"]:
             final_data["segments"].append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })

    # Сохраняем JSON
    out_path = os.path.join(output_dir, json_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Таймстампы сохранены: {out_path}")

    # Постпроцессинг (создание txt файла)
    if make_readable:
        txt_filename = os.path.splitext(json_name)[0] + "_readable.txt"
        txt_path = os.path.join(output_dir, txt_filename)
        create_readable_log(final_data["segments"], txt_path, pause_threshold=2.0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json-filename", default="sentence_timestamps.json")
    parser.add_argument("--language", default="ru")
    parser.add_argument("--config")
    parser.add_argument("--hint-file", help="Файл с текстом песни/урока для улучшения качества распознавания")
    parser.add_argument("--readable", action="store_true", help="Создать дополнительный текстовый файл с объединенными блоками и паузами")

    args = parser.parse_args()

    hint_content = ""
    if args.hint_file and os.path.exists(args.hint_file):
        with open(args.hint_file, 'r', encoding='utf-8') as f:
            hint_content = f.read().replace('\n', ' ')

    transcribe_segments(
        args.audio,
        args.output_dir,
        args.json_filename,
        args.language,
        args.config,
        hint_text=hint_content,
        make_readable=args.readable
    )