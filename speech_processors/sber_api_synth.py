import uuid
import requests
import argparse
from dotenv import load_dotenv
import os
import re
import tempfile
import soundfile as sf
import numpy as np
import io

# === Загрузка переменных окружения ===
load_dotenv('config.env')

AUTHORIZATION_KEY = os.getenv("SBER_SPEECH_KEY")
RQ_UID = str(uuid.uuid4())

if not AUTHORIZATION_KEY:
    raise ValueError("❌ Не найден AUTHORIZATION_KEY в config.env")

# === Аргументы командной строки ===
def parse_args():
    parser = argparse.ArgumentParser(description="Синтез речи с поддержкой пауз [[PAUSE:секунды]]")
    parser.add_argument("text_file", help="Путь к текстовому файлу для синтеза")
    parser.add_argument("--voice", default="Bys_24000", help="Голос для синтеза")
    parser.add_argument("--output", default="output.wav", help="Имя выходного аудиофайла")
    return parser.parse_args()

# === Получение Access Token ===
def get_access_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": RQ_UID,
        "Authorization": f"Basic {AUTHORIZATION_KEY}"
    }
    data = {"scope": "SALUTE_SPEECH_PERS"}

    try:
        response = requests.post(url, headers=headers, data=data, verify=False)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print("❌ Ошибка при получении токена:", e)
        return None

# === Логика разбиения текста (оставлена ваша логика для длинных текстов) ===
def split_text_into_chunks(text, max_chars=3500):
    text = text.strip()
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph: continue

        if len(paragraph) > max_chars:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence: continue
                if len(current_chunk) + len(sentence) + 1 <= max_chars:
                    current_chunk += " " + sentence if current_chunk else sentence
                else:
                    if current_chunk: chunks.append(current_chunk)
                    current_chunk = sentence
        else:
            if len(current_chunk) + len(paragraph) + 2 <= max_chars:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
            else:
                if current_chunk: chunks.append(current_chunk)
                current_chunk = paragraph

    if current_chunk: chunks.append(current_chunk)
    return chunks

# === Синтез куска текста ===
def synthesize_speech_chunk(token, text, voice):
    url = "https://smartspeech.sber.ru/rest/v1/text:synthesize"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/text" # Для явного SSML можно использовать application/ssml, но text тоже работает
    }
    params = {"voice": voice, "format": "wav16"}

    # Автоматически оборачиваем в speak, если есть теги, но лучше всегда для надежности
    # Но если мы шлем чистый текст, speak не повредит
    payload = text.strip()

    try:
        response = requests.post(
            url, headers=headers, data=payload, params=params, stream=True,
            verify="/etc/ssl/certs/ca-certificates.crt"
            # verify=False # Раскомментируйте, если проблемы с SSL
        )
        response.raise_for_status()
        audio_data, sample_rate = sf.read(io.BytesIO(response.content))
        if len(audio_data.shape) > 1: audio_data = audio_data.mean(axis=1)
        return audio_data, sample_rate
    except Exception as e:
        print(f"❌ Ошибка синтеза фрагмента: {e}")
        return None, None

# === ГЛАВНАЯ НОВАЯ ФУНКЦИЯ ===
def process_text_with_pauses(token, text, voice):
    """
    Разбивает текст по маркерам [[PAUSE:X]], синтезирует текст и генерирует тишину.
    """
    # Регулярка ищет [[PAUSE:число]] или [[PAUSE:число.число]]
    # Группа захвата (r'...') позволяет re.split сохранить разделители в списке
    parts = re.split(r'(\[\[PAUSE:\s*[\d\.]+\]\])', text)

    full_audio_parts = []
    sample_rate = 48000 # Дефолт, обновится после первого синтеза или останется таким для тишины

    print(f"🔄 Обработка текста: найдено {len(parts)} сегментов (текст + паузы)")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Проверка: это маркер паузы?
        pause_match = re.match(r'\[\[PAUSE:\s*([\d\.]+)\]\]', part)

        if pause_match:
            # === ГЕНЕРАЦИЯ ТИШИНЫ ===
            seconds = float(pause_match.group(1))
            print(f"⏳ Генерация паузы: {seconds} сек.")
            num_samples = int(seconds * sample_rate)
            silence = np.zeros(num_samples, dtype=np.float32)
            full_audio_parts.append(silence)
        else:
            # === СИНТЕЗ ТЕКСТА ===
            # Если текст внутри сегмента слишком длинный, используем старый сплиттер
            sub_chunks = split_text_into_chunks(part)

            for sub_chunk in sub_chunks:
                print(f"🎙 Синтез текста ({len(sub_chunk)} симв)...")
                audio, sr = synthesize_speech_chunk(token, sub_chunk, voice)
                if audio is not None:
                    sample_rate = sr # Обновляем SR от реального ответа API
                    full_audio_parts.append(audio)
                    # Маленькая техническая пауза между склейками текста (0.1с), чтобы не глотались окончания
                    full_audio_parts.append(np.zeros(int(0.1 * sr), dtype=np.float32))

    if not full_audio_parts:
        return None, None

    return np.concatenate(full_audio_parts), sample_rate

# === Основной запуск ===
if __name__ == "__main__":
    args = parse_args()

    try:
        with open(args.text_file, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"❌ Ошибка файла: {e}")
        exit(1)

    token = get_access_token()
    if token:
        print("🚀 Начинаем обработку...")
        final_audio, sr = process_text_with_pauses(token, text, args.voice)

        if final_audio is not None:
            sf.write(args.output, final_audio, sr)
            print(f"✅ Готово! Файл сохранен: {args.output}")
        else:
            print("❌ Не удалось создать аудио.")