#!/usr/bin/env python3
"""
Унифицированный модуль для разбиения текста на чанки.

Используется всеми процессорами проекта вместо дублирования кода.
Поддерживает различные стратегии разбиения с сохранением семантических границ.

Использование:
    from utils.text_splitter import split_text_into_chunks

    chunks = split_text_into_chunks(text, max_chars=3000)
"""

import re
from typing import List, Optional, Callable
from dataclasses import dataclass


@dataclass
class SplitConfig:
    """Конфигурация разбиения текста."""
    max_chars: int = 3000
    preserve_paragraphs: bool = True
    split_pattern: str = r'\n\s*\n'  # Паттерн для разделения абзацев
    sentence_pattern: str = r'(?<=[.!?])\s+'  # Паттерн для разделения предложений
    respect_word_boundaries: bool = True


# Предустановленные конфигурации для разных использвей
PRESETS = {
    'default': SplitConfig(max_chars=3000),
    'tts_alibaba': SplitConfig(max_chars=500, preserve_paragraphs=True),
    'tts_sber': SplitConfig(max_chars=3500, preserve_paragraphs=True),
    'tts_silero': SplitConfig(max_chars=800, preserve_paragraphs=True),
    'llm_processing': SplitConfig(max_chars=10000, preserve_paragraphs=True),
    'audiobook': SplitConfig(max_chars=2500, preserve_paragraphs=True),
    'summary': SplitConfig(max_chars=6000, preserve_paragraphs=True),
}


def split_text_into_chunks(
    text: str,
    max_chars: int = 3000,
    preserve_paragraphs: bool = True,
    split_pattern: Optional[str] = None,
    sentence_pattern: Optional[str] = None,
    preset: Optional[str] = None
) -> List[str]:
    """
    Разбивает текст на чанки с сохранением семантических границ.

    Это единая функция для всего проекта, заменяющая дублированный код
    в 8+ файлах (sber_api_synth.py, silero.py, alibaba_tts.py, etc.)

    Args:
        text: Исходный текст для разбиения
        max_chars: Максимальное количество символов в чанке
        preserve_paragraphs: Сохранять ли границы абзацев
        split_pattern: Кастомный паттерн для разделения (по умолчанию абзацы)
        sentence_pattern: Кастомный паттерн для разделения предложений
        preset: Имя предустановки ('tts_alibaba', 'tts_sber', 'llm_processing', etc.)
                Если указано, остальные параметры игнорируются

    Returns:
        Список чанков текста

    Examples:
        # Использование с пресетом
        chunks = split_text_into_chunks(text, preset='tts_alibaba')

        # Кастомные параметры
        chunks = split_text_into_chunks(text, max_chars=500)

        # Для LLM-обработки
        chunks = split_text_into_chunks(text, preset='llm_processing')
    """
    # Применяем пресет если указан
    if preset and preset in PRESETS:
        config = PRESETS[preset]
        max_chars = config.max_chars
        preserve_paragraphs = config.preserve_paragraphs
        split_pattern = split_pattern or config.split_pattern
        sentence_pattern = sentence_pattern or config.sentence_pattern

    # Убираем лишние пробелы
    text = text.strip()

    if not text:
        return []

    # Если текст меньше лимита - возвращаем как есть
    if len(text) <= max_chars:
        return [text]

    # Определяем паттерны
    para_pattern = split_pattern or r'\n\s*\n'
    sent_pattern = sentence_pattern or r'(?<=[.!?])\s+'

    chunks = []
    current_chunk = ""

    if preserve_paragraphs:
        # Разбиваем на абзацы
        paragraphs = re.split(para_pattern, text)

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Если абзац сам по себе слишком длинный
            if len(paragraph) > max_chars:
                # Разбиваем на предложения
                sentences = re.split(sent_pattern, paragraph)

                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    # Если предложение всё ещё слишком длинное - разбиваем жёстко
                    if len(sentence) > max_chars:
                        # Жёсткое разбиение с уважением границ слов
                        words = sentence.split()
                        temp_chunk = ""

                        for word in words:
                            if len(temp_chunk) + len(word) + 1 <= max_chars:
                                temp_chunk = f"{temp_chunk} {word}".strip()
                            else:
                                if temp_chunk:
                                    chunks.append(temp_chunk)
                                temp_chunk = word

                        if temp_chunk:
                            if len(current_chunk) + len(temp_chunk) + 1 <= max_chars:
                                current_chunk = f"{current_chunk} {temp_chunk}".strip()
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk)
                                current_chunk = temp_chunk
                    else:
                        # Предательство нормальной длины
                        if len(current_chunk) + len(sentence) + 1 <= max_chars:
                            if current_chunk:
                                current_chunk = f"{current_chunk} {sentence}"
                            else:
                                current_chunk = sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence
            else:
                # Абзац нормальной длины
                if len(current_chunk) + len(paragraph) + 2 <= max_chars:
                    if current_chunk:
                        current_chunk = f"{current_chunk}\n\n{paragraph}"
                    else:
                        current_chunk = paragraph
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = paragraph
    else:
        # Простое разбиение без сохранения абзацев
        words = text.split()
        for word in words:
            if len(current_chunk) + len(word) + 1 <= max_chars:
                if current_chunk:
                    current_chunk = f"{current_chunk} {word}"
                else:
                    current_chunk = word
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word

    # Добавляем последний чанк
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def split_by_sentences(
    text: str,
    max_chars: int = 1000,
    sentence_pattern: str = r'(?<=[.!?؟。])\s+'
) -> List[str]:
    """
    Разбивает текст строго по предложениям.

    Полезно для TTS, где важно не разрывать предложения.

    Args:
        text: Исходный текст
        max_chars: Максимальный размер чанка
        sentence_pattern: Паттерн для разделения предложений

    Returns:
        Список чанков, каждый из которых содержит целые предложения
    """
    sentences = re.split(sentence_pattern, text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            if current_chunk:
                current_chunk = f"{current_chunk} {sentence}"
            else:
                current_chunk = sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def get_chunk_stats(chunks: List[str]) -> dict:
    """
    Возвращает статистику по чанкам.

    Args:
        chunks: Список чанков

    Returns:
        Словарь со статистикой
    """
    if not chunks:
        return {'count': 0, 'total_chars': 0, 'avg_chars': 0, 'min_chars': 0, 'max_chars': 0}

    sizes = [len(c) for c in chunks]

    return {
        'count': len(chunks),
        'total_chars': sum(sizes),
        'avg_chars': sum(sizes) // len(sizes),
        'min_chars': min(sizes),
        'max_chars': max(sizes),
    }


# === CLI интерфейс для тестирования ===
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Разбиение текста на чанки")
    parser.add_argument("input_file", help="Входной файл с текстом")
    parser.add_argument("--max-chars", type=int, default=3000, help="Макс. символов в чанке")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Использовать пресет")
    parser.add_argument("--stats", action="store_true", help="Показать статистику")

    args = parser.parse_args()

    with open(args.input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    if args.preset:
        chunks = split_text_into_chunks(text, preset=args.preset)
    else:
        chunks = split_text_into_chunks(text, max_chars=args.max_chars)

    print(f"Разбито на {len(chunks)} чанков:")

    for i, chunk in enumerate(chunks, 1):
        print(f"\n--- Чанк {i} ({len(chunk)} символов) ---")
        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)

    if args.stats:
        stats = get_chunk_stats(chunks)
        print(f"\n📊 Статистика:")
        print(f"   Всего чанков: {stats['count']}")
        print(f"   Всего символов: {stats['total_chars']}")
        print(f"   Средний размер: {stats['avg_chars']}")
        print(f"   Мин. размер: {stats['min_chars']}")
        print(f"   Макс. размер: {stats['max_chars']}")
