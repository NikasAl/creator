#!/bin/bash

# lib/manim/utils.sh
# Общие утилиты и конфигурация путей для Manim пайплайна
#
# РЕФАКТОРИНГ: Теперь делегирует общие функции в lib/common/utils.sh
# Оставляет только специфичные для Manim настройки

# Подключаем общие утилиты
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/utils.sh"

# ============================================
# СПЕЦИФИЧНЫЕ ДЛЯ MANIM НАСТРОЙКИ
# ============================================

# Дефолтные значения
LANGUAGE="${LANGUAGE:-ru}"
MODEL_CHOICE="${CODE_MODEL:-custom}"
SCRIPT_MODEL="${SCRIPT_MODEL:-custom}"
QUALITY="${QUALITY:-low}"
TOTAL_STEPS="10"

# Пути
OUTPUT_DIR="$BASE_DIR"
SPEC_FILE="$OUTPUT_DIR/spec.md"
SCRIPT_FILE="$OUTPUT_DIR/lesson_script.txt"
TTS_SCRIPT_FILE="$OUTPUT_DIR/lesson_tts.txt"
AUDIO_FILE="$OUTPUT_DIR/audio.mp3"
TIMESTAMPS_FILE="sentence_timestamps.json"
FULL_TIMESTAMPS_PATH="$OUTPUT_DIR/$TIMESTAMPS_FILE"

# Manim файлы
MANIM_DRAFT_FILE="$OUTPUT_DIR/manim_draft.py"
MANIM_CODE_FILE="$OUTPUT_DIR/manim_lesson.py"
MANIM_VIDEO_FILE="$OUTPUT_DIR/manim_video.mp4"
EXAMPLE_FILE="$OUTPUT_DIR/manim_example.py"
OUTPUT_VIDEO_FILE="$OUTPUT_DIR/video.mp4"
PROMO_FILE="$OUTPUT_DIR/promo_description.txt"
PIKABU_FILE="$OUTPUT_DIR/pikabu_article.txt"
COVER_FILE="$OUTPUT_DIR/cover.jpg"

# ============================================
# СПЕЦИФИЧНЫЕ ДЛЯ MANIM ФУНКЦИИ
# ============================================

# Проверка существования Manim кода
check_manim_code() {
    local file="${1:-$MANIM_CODE_FILE}"
    if [ ! -f "$file" ]; then
        log_error "Manim код не найден: $file"
        return 1
    fi

    # Проверяем, что файл не пустой
    if [ ! -s "$file" ]; then
        log_error "Файл Manim кода пуст: $file"
        return 1
    fi

    return 0
}

# Проверка качества рендера
check_render_quality() {
    local video_file="${1:-$OUTPUT_VIDEO_FILE}"
    local min_duration="${2:-5}"  # минимум секунд

    if [ ! -f "$video_file" ]; then
        log_error "Видео не найдено: $video_file"
        return 1
    fi

    local duration=$(get_audio_duration "$video_file" 2>/dev/null || echo "0")
    if [ "$duration" -lt "$min_duration" ]; then
        log_warning "Видео слишком короткое: ${duration} сек"
        return 1
    fi

    log_success "Видео длительностью ${duration} сек"
    return 0
}
