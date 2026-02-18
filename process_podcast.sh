#!/bin/bash

# Usage: ./process_podcast.sh <folder_name_inside_pipelines_scr>
# Example: ./process_podcast.sh game_20251020_1230

set -e

# === НАСТРОЙКА ПУТЕЙ ===
# Скрипт должен запускаться из корня проекта (там где speech_processors, config.env и т.д.)
ROOT_DIR="$PWD"
PROJECT_NAME="$1"
DATA_DIR="$ROOT_DIR/pipelines_scr/$PROJECT_NAME" # Здесь лежат медиафайлы
REC_DIR="$HOME/Videos/recordings"
CONFIG_FILE="$ROOT_DIR/config.env"

# Проверка, что мы в корне (наличие папки speech_processors как маркер)
if [ ! -d "$ROOT_DIR/speech_processors" ]; then
    echo "⚠️ Внимание: Похоже, скрипт запущен не из корня проекта."
    echo "Текущая директория: $PWD"
    echo "Ожидалась папка speech_processors внутри."
    # Можно раскомментировать exit 1, если нужна строгость
fi

if [ -z "$PROJECT_NAME" ]; then
    echo "❌ Ошибка: Не указано имя проекта."
    echo "Использование: $0 <имя_папки>"
    exit 1
fi

# --- АВТОМАТИЧЕСКИЙ ИМПОРТ ФАЙЛОВ ---
if [ ! -d "$DATA_DIR" ]; then
    echo "📂 Папка проекта не найдена. Создаем: $DATA_DIR"
    mkdir -p "$DATA_DIR"

    echo "🔍 Поиск последней пары записи (game_*.mp4 + mic.mp3) в $REC_DIR..."

    # Находим самый свежий mp4 файл
    LATEST_VIDEO=$(ls -t "$REC_DIR"/game_*.mp4 2>/dev/null | head -n 1)

    if [ -z "$LATEST_VIDEO" ]; then
        echo "❌ Ошибка: В папке $REC_DIR не найдено видео файлов game_*.mp4"
        rmdir "$DATA_DIR"
        exit 1
    fi

    BASENAME=$(basename "$LATEST_VIDEO" .mp4)
    LATEST_AUDIO="$REC_DIR/${BASENAME}_mic.mp3"

    if [ ! -f "$LATEST_AUDIO" ]; then
        echo "❌ Ошибка: Найдено видео $BASENAME.mp4, но нет аудио файла ${BASENAME}_mic.mp3"
        rmdir "$DATA_DIR"
        exit 1
    fi

    echo "✅ Обнаружены файлы:"
    echo "   📹 Видео: $(basename "$LATEST_VIDEO")"
    echo "   🎙️ Аудио: $(basename "$LATEST_AUDIO")"

    echo "📦 Перемещаем файлы в рабочий каталог..."
    # Используем абсолютные пути
    mv "$LATEST_VIDEO" "$DATA_DIR/"
    mv "$LATEST_AUDIO" "$DATA_DIR/"
else
    echo "📂 Папка проекта существует. Работаем с файлами внутри: $DATA_DIR"
fi

# ВАЖНО: Мы НЕ делаем cd "$DATA_DIR". Мы остаемся в ROOT_DIR.

# 1. Поиск исходников внутри DATA_DIR
VIDEO_SRC=$(find "$DATA_DIR" -maxdepth 1 -name "game_*.mp4" | head -n 1)
AUDIO_SRC=$(find "$DATA_DIR" -maxdepth 1 -name "game_*_mic.mp3" | head -n 1)

if [[ -z "$VIDEO_SRC" || -z "$AUDIO_SRC" ]]; then
    echo "❌ Не найдены исходные файлы mp4 или mp3 (game_*) в $DATA_DIR"
    exit 1
fi

echo "🎥 Видео: $VIDEO_SRC"
echo "🎤 Аудио: $AUDIO_SRC"

# 2. Транскрибация исходного голоса
echo "=========================================="
echo "📝 ШАГ 1: Транскрибация исходника..."
echo "=========================================="
TRANSCRIPT_JSON="$DATA_DIR/source_timestamps.json"
TRANSCRIPTER="$ROOT_DIR/video_processors/sentence_transcriber.py"

if [ ! -f "$TRANSCRIPT_JSON" ]; then
    python "$TRANSCRIPTER" \
        --audio "$AUDIO_SRC" \
        --output-dir "$DATA_DIR" \
        --json-filename "source_timestamps.json" \
        --language "ru" \
        --readable \
        --config "$CONFIG_FILE"
else
    echo "✅ Транскрипция уже есть."
fi

# Извлекаем текст из source_timestamps.json в формате (опция --readable в sentence_transcriber.py)
# [00:00:00-00:01:00] текст
# [[PAUSE:12]]
# [00:01:30-00:02:00] текст
# ...
SOURCE_TEXT_FILE="$DATA_DIR/source_timestamps_readable.txt"
#jq -r '.text' "$TRANSCRIPT_JSON" > "$SOURCE_TEXT_FILE"

# 3. Генерация сценария подкаста (LLM)
echo "=========================================="
echo "🧠 ШАГ 2: Генерация умного сценария (LLM)..."
echo "=========================================="
PODCAST_SCRIPT="$DATA_DIR/podcast_script.txt"
GENERATOR="$ROOT_DIR/text_processors/lesson_generator.py"

if [ ! -f "$PODCAST_SCRIPT" ]; then
    python "$GENERATOR" \
        --action podcast \
        --input "$SOURCE_TEXT_FILE" \
        --output "$PODCAST_SCRIPT" \
        --model custom \
        --config "$CONFIG_FILE"
else
    echo "✅ Сценарий уже есть."
fi

# 5. Синтез речи
echo "=========================================="
echo "🗣️ ШАГ 3: Синтез речи..."
echo "=========================================="
FINAL_VOICE="$DATA_DIR/podcast_voice.mp3"

# Экспортируем ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ для 02_audio.sh (абсолютные пути)
source "$ROOT_DIR/lib/manim/utils.sh"
# Подключаем функции
# Теперь, когда мы в ROOT_DIR, путь к 02_audio.sh корректен относительно корня
source "$ROOT_DIR/lib/manim/02_audio.sh"


export AUDIO_FILE="$FINAL_VOICE"
export TTS_SCRIPT_FILE="$PODCAST_SCRIPT"
export OUTPUT_DIR="$DATA_DIR"
# Таймстампы нового голоса (если понадобятся)
export TIMESTAMPS_FILE="podcast_timestamps.json"
# Внимание: sentence_transcriber внутри 02_audio.sh захочет писать в OUTPUT_DIR
export FULL_TIMESTAMPS_PATH="$DATA_DIR/$TIMESTAMPS_FILE"
export LANGUAGE="ru"

# ВАЖНО: 02_audio.sh вызывает "python speech_processors/silero.py".
manim_step_create_audio

# Опционально: создаем транскрипцию синтезированного голоса (функция из 02_audio.sh)
#manim_step_transcribe

# 6. Финальная сборка
echo "=========================================="
echo "🎬 ШАГ 4: Сборка видео..."
echo "=========================================="
FINAL_VIDEO="$DATA_DIR/video.mp4"
RETIMER="$ROOT_DIR/video_processors/video_retimer.py"

# Передаем абсолютные пути в ретаймер
if [ ! -f "$FINAL_VIDEO" ]; then
  python "$RETIMER" \
      --video "$VIDEO_SRC" \
      --audio "$FINAL_VOICE" \
      --output "$FINAL_VIDEO" \
      --background-vol 1.2
else
    echo "✅ Видео уже есть."
fi

# 7. Создание промо
echo "=========================================="
echo "📝 ШАГ 5: Создание промо..."
echo "=========================================="
source "$ROOT_DIR/lib/manim/05_extra.sh"
manim_step_promo_exp "creative" "$PODCAST_SCRIPT" "$DATA_DIR/promo_description.txt"

# 8. Экспорт обложки
echo "=========================================="
echo "🖼️ ШАГ 6: Создание обложки..."
echo "=========================================="
#manim_step_cover
COVER_FILE="$DATA_DIR/cover.jpg"
export_cover "$DATA_DIR" "$FINAL_VIDEO" "$COVER_FILE" "6"

echo "=========================================="
echo "🎉 Готово! Подкаст сохранен в: $FINAL_VIDEO"
echo "=========================================="

