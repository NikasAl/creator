#!/bin/bash

# lib/manim/02_audio.sh
# Функции для работы с аудио в Manim пайплайне
#
# РЕФАКТОРИНГ: Делегирует общую логику в lib/common/audio.sh
# Оставляет только специфичные для Manim функции

# Подключаем общие модули
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/utils.sh"
source "$SCRIPT_DIR/../common/audio.sh"

# ============================================
# ШАГИ MANIM ПАЙПЛАЙНА
# ============================================

manim_step_create_audio() {
    # Используем общую функцию создания аудио
    common_step_create_audio "$TTS_SCRIPT_FILE" "$AUDIO_FILE"
}

manim_step_transcribe() {
    log_step "3" "Транскрибация..."

    if [ -f "$FULL_TIMESTAMPS_PATH" ]; then
        log_success "Таймстампы существуют."
        return 0
    fi

    python video_processors/sentence_transcriber.py \
        --audio "$AUDIO_FILE" \
        --output-dir "$OUTPUT_DIR" \
        --json-filename "$TIMESTAMPS_FILE" \
        --language "$LANGUAGE" \
        --config config.env
}

# ============================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

# Проверка свежести транскрипции и коррекция
check_and_correct_transcription() {
    local tts_file="${1:-$TTS_SCRIPT_FILE}"
    local timestamps_file="${2:-$FULL_TIMESTAMPS_PATH}"

    if [ -f "$tts_file" ] && [ -f "$timestamps_file" ]; then
        local now=$(date +%s)
        local file_time=$(stat -c %Y "$timestamps_file" 2>/dev/null || stat -f %m "$timestamps_file" 2>/dev/null)
        local age=$((now - file_time))
        local threshold=15

        if [ "$age" -lt "$threshold" ]; then
            log_info "Файл транскрипции свежий (создан $age сек назад)."
            log_info "Запуск корректора текста (LLM)..."
            python text_processors/transcription_corrector.py \
                --json "$timestamps_file" \
                --reference "$tts_file"
        else
            log_info "Файл транскрипции старый. Пропускаем коррекцию."
        fi
    fi
}
