import os
import argparse
from dotenv import load_dotenv
import dashscope
import base64
import re
import tempfile
import soundfile as sf
import numpy as np

# === Загрузка переменных окружения ===
load_dotenv('config.env')

# === Ключи для Alibaba Cloud ===
ALIBABA_API_KEY = os.getenv("ALIBABA_API_KEY")
ALIBABA_BASE_URL = os.getenv("ALIBABA_BASE_URL", "https://dashscope-intl.aliyuncs.com/api/v1")

dashscope.base_http_api_url = ALIBABA_BASE_URL

if not ALIBABA_API_KEY:
    raise ValueError("❌ Не найден ALIBABA_API_KEY в config.env")

# === Аргументы командной строки ===
def parse_args():
    parser = argparse.ArgumentParser(description="Синтез речи с помощью Alibaba Cloud Qwen TTS")
    parser.add_argument("text_file", help="Путь к текстовому файлу для синтеза")
    parser.add_argument("--voice", default="Cherry", help="Голос для синтеза (по умолчанию: Cherry)")
    parser.add_argument("--language", default="Auto", help="Язык для синтеза (по умолчанию: Auto)")
    parser.add_argument("--output", default="output.wav", help="Имя выходного аудиофайла (по умолчанию: output.wav)")
    return parser.parse_args()

# === Синтез речи через Alibaba Cloud Qwen TTS ===
TEMP_DIR = os.path.join(tempfile.gettempdir(), "alibaba_tts")

# Создаем временную директорию при импорте
os.makedirs(TEMP_DIR, exist_ok=True)


def split_text_into_chunks(text, max_chars=500):
    """
    Разбивает текст на чанки с сохранением семантических границ.
    Максимальная длина чанка - 500 символов (безопасный лимит для Alibaba TTS).
    """
    # Убираем лишние пробелы и переносы в начале/конце
    text = text.strip()
    
    # Разбиваем на абзацы по пустым строкам
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # Если абзац сам по себе слишком длинный, разбиваем на предложения
        if len(paragraph) > max_chars:
            # Разбиваем на предложения, сохраняя знаки препинания
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                if len(current_chunk) + len(sentence) + 1 <= max_chars:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
        else:
            # Если текущий чанк + абзац не превышают лимит - добавляем
            if len(current_chunk) + len(paragraph) + 2 <= max_chars:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                # Сохраняем текущий чанк и начинаем новый
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
    
    # Не забываем добавить последний чанк
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def synthesize_speech_chunk(text, voice, language):
    """
    Синтезирует речь для одного чанка текста.
    
    Returns:
        numpy array audio data or None on failure
    """
    try:
        response = dashscope.MultiModalConversation.call(
            model="qwen3-tts-flash-2025-09-18",
            api_key=ALIBABA_API_KEY,
            text=text,
            voice=voice,
            language_type=language,
            stream=False
        )
        
        if response.status_code == 200:
            # Получаем URL к аудиофайлу
            audio_url = response.output.audio.url
            
            # Скачиваем аудиофайл
            import requests
            audio_response = requests.get(audio_url)
            audio_response.raise_for_status()
            
            # Загружаем аудио в память
            audio_data, sample_rate = sf.read(io.BytesIO(audio_response.content))
            
            # Убедимся, что аудио в правильном формате
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)  # моно
            
            return audio_data, sample_rate
        else:
            print(f"❌ Ошибка при синтезе речи для чанка: {response.code} - {response.message}")
            return None, None
            
    except Exception as e:
        print(f"❌ Ошибка при обращении к Alibaba Cloud API для чанка: {e}")
        return None, None


def synthesize_speech(text, voice, language, output_file):
    """
    Синтезирует речь с использованием Alibaba Cloud Qwen TTS с поддержкой длинных текстов.
    Текст разбивается на чанки, каждый из которых синтезируется отдельно, затем объединяется.
    
    Args:
        text: Текст для синтеза
        voice: Выбранный голос
        language: Язык синтеза
        output_file: Путь к выходному файлу
    """
    # Проверяем длину текста
    if len(text) <= 600:
        print(f"Текст короче 600 символов, используем прямой синтез...")
        return synthesize_speech_chunk(text, voice, language)[0] is not None
    
    # Разбиваем текст на чанки
    chunks = split_text_into_chunks(text, max_chars=500)
    print(f"Текст разбит на {len(chunks)} частей для синтеза")
    
    audio_chunks = []
    sample_rate = None
    pause_duration = int(0.3 * 48000)  # 0.3 секунды паузы между частями (48кГц)
    
    for i, chunk in enumerate(chunks):
        print(f"Синтез речи для части {i+1}/{len(chunks)} ({len(chunk)} символов)...")
        
        audio_data, sr = synthesize_speech_chunk(chunk, voice, language)
        
        if audio_data is None:
            print(f"❌ Не удалось синтезировать часть {i+1}")
            continue
        
        if sample_rate is None:
            sample_rate = sr
        
        audio_chunks.append(audio_data)
        
        # Добавляем паузу между частями (кроме последней)
        if i < len(chunks) - 1:
            pause = np.zeros(pause_duration, dtype=np.float32)
            audio_chunks.append(pause)
    
    # Объединяем все аудио чанки
    if audio_chunks:
        full_audio = np.concatenate(audio_chunks)
        
        # Сохраняем объединенное аудио
        try:
            sf.write(output_file, full_audio, sample_rate)
            print(f"✅ Аудио успешно синтезировано и сохранено как '{output_file}'")
            return True
        except Exception as e:
            print(f"❌ Ошибка при сохранении аудиофайла: {e}")
            return False
    else:
        print("❌ Не удалось синтезировать ни одну часть текста")
        return False

# === Основной запуск ===
if __name__ == "__main__":
    args = parse_args()

    # Читаем текст из файла
    try:
        with open(args.text_file, "r", encoding="utf-8") as f:
            text = f.read()
        print(f"📄 Текст загружен из '{args.text_file}' ({len(text)} символов)")
    except FileNotFoundError:
        print(f"❌ Файл '{args.text_file}' не найден.")
        exit(1)
    except Exception as e:
        print(f"❌ Ошибка при чтении файла: {e}")
        exit(1)

    # Добавляем импорт
    import io

    # Синтезируем речь
    success = synthesize_speech(text, args.voice, args.language, args.output)
    if not success:
        exit(1)
