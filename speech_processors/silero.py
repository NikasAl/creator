# Silero TTS для длинных текстов с чтением из файла
from silero import silero_tts
import soundfile as sf
import numpy as np
import re
import argparse
import os
import sys

def read_text_from_file(file_path, encoding='utf-8'):
    """
    Читает текст из файла с обработкой различных кодировок.
    """
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            return file.read()
    except UnicodeDecodeError:
        # Пробуем другие кодировки, если utf-8 не сработал
        encodings_to_try = ['cp1251', 'koi8-r', 'iso-8859-5', 'utf-8-sig']
        for enc in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=enc) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        raise Exception(f"Не удалось прочитать файл '{file_path}' с поддерживаемыми кодировками")

def split_text_into_chunks(text, max_chars=800):
    """
    Разбивает текст на чанки с сохранением семантических границ.
    Максимальная длина чанка - 800 символов (безопасный лимит для Silero).
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

def generate_speech_for_long_text(text, model, speaker='xenia', sample_rate=48000):
    """
    Генерирует речь для длинного текста, разбивая его на чанки.
    """
    chunks = split_text_into_chunks(text)
    print(f"Текст разбит на {len(chunks)} частей:")
    for i, chunk in enumerate(chunks):
        print(f"Часть {i+1}: {len(chunk)} символов")
        print(f"\"{chunk[:100]}{'...' if len(chunk) > 100 else ''}\"\n")
    
    audio_chunks = []
    pause_duration = int(0.3 * sample_rate)  # 0.3 секунды паузы между частями
    
    for i, chunk in enumerate(chunks):
        try:
            print(f"Генерация аудио для части {i+1}/{len(chunks)}...")
            audio_chunk = model.apply_tts(
                text=chunk,
                speaker=speaker,
                sample_rate=sample_rate
            )
            audio_chunks.append(audio_chunk)
            
            # Добавляем паузу между частями (кроме последней)
            if i < len(chunks) - 1:
                pause = np.zeros(pause_duration, dtype=np.float32)
                audio_chunks.append(pause)
                
        except Exception as e:
            print(f"Ошибка при генерации части {i+1}: {str(e)}")
            print(f"Проблемный текст (первые 200 символов): {chunk[:200]}")
            raise
    
    # Объединяем все аудио чанки
    if audio_chunks:
        full_audio = np.concatenate(audio_chunks)
        return full_audio
    else:
        raise Exception("Не удалось сгенерировать аудио ни для одной части текста")

def main():
    parser = argparse.ArgumentParser(description='Генерация речи из текстового файла с помощью Silero TTS')
    parser.add_argument('--input', '-i', type=str, required=True,
                        help='Путь к текстовому файлу для озвучки')
    parser.add_argument('--output', '-o', type=str, default='output.wav',
                        help='Путь для сохранения аудио файла (по умолчанию: output.wav)')
    parser.add_argument('--speaker', '-s', type=str, default='aidar',
                        choices=['xenia', 'aidar', 'baya', 'kseniya', 'eugene'],
                        help='Голос диктора (по умолчанию: xenia)')
    parser.add_argument('--sample_rate', '-r', type=int, default=48000,
                        choices=[8000, 16000, 24000, 48000],
                        help='Частота дискретизации (по умолчанию: 48000)')
    parser.add_argument('--encoding', '-e', type=str, default='utf-8',
                        help='Кодировка текстового файла (по умолчанию: utf-8)')
    
    args = parser.parse_args()
    
    # Проверяем существование входного файла
    if not os.path.exists(args.input):
        print(f"Ошибка: Файл '{args.input}' не существует!")
        sys.exit(1)
    
    # Проверяем расширение выходного файла
    if not args.output.lower().endswith('.wav'):
        args.output += '.wav'
        print(f"Предупреждение: Добавлено расширение .wav к выходному файлу. Сохранение как: {args.output}")
    
    print(f"Загрузка текста из файла: {args.input}")
    text = read_text_from_file(args.input, args.encoding)
    
    if not text.strip():
        print("Ошибка: Текстовый файл пуст!")
        sys.exit(1)
    
    print(f"Длина текста: {len(text)} символов")
    
    print("Загрузка модели Silero TTS...")
    model, _ = silero_tts(language='ru', speaker='v5_1_ru', put_accent=True, put_yo=True, put_stress_homo=True, put_yo_homo=True)
    
    print("Начинаем генерацию речи...")
    audio = generate_speech_for_long_text(
        text=text,
        model=model,
        speaker=args.speaker,
        sample_rate=args.sample_rate
    )
    
    # Создаем директорию для выходного файла, если её нет
    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Создана директория: {output_dir}")
    
    print(f"Сохранение аудио файла: {args.output}")
    sf.write(args.output, audio, args.sample_rate)
    print(f"Готово! Аудио файл успешно сохранен в: {args.output}")
    print(f"Длительность аудио: примерно {len(audio) / args.sample_rate:.1f} секунд")

if __name__ == "__main__":
    main()
