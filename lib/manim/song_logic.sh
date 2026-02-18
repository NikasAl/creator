#!/bin/bash

# lib/manim/song_logic.sh
# Уникальная логика для музыкального клипа

# Переопределяем цвет для музыки
PURPLE='\033[0;35m'
COLOR_PREFIX="${PURPLE}"

song_step_lyrics() {
    log_step "1" "Пишем хитовый текст..."
    if [ ! -f "$SCRIPT_FILE" ]; then # В контексте песни SCRIPT_FILE - это текст песни
        python text_processors/lyrics_generator.py \
            --spec "$OUTPUT_DIR/spec.txt" \
            --script "$OUTPUT_DIR/lesson_script.txt" \
            --output "$SCRIPT_FILE" \
            --model "$SCRIPT_MODEL" \
            --config config.env
    else
        echo "✅ Текст песни уже готов: $SCRIPT_FILE"
    fi
}

# Специализированная транскрибация с подсказкой (hint-file)
song_step_transcribe() {
    log_step "3" "Синхронизация ритма (Транскрибация с подсказкой)..."
    if [ ! -f "$FULL_TIMESTAMPS_PATH" ]; then
        python video_processors/sentence_transcriber.py \
            --audio "$AUDIO_FILE" \
            --output-dir "$OUTPUT_DIR" \
            --json-filename "$TIMESTAMPS_FILE" \
            --language "$LANGUAGE" \
            --hint-file "$SCRIPT_FILE" \
            --config config.env
    else
        echo "✅ Таймстампы песни готовы."
    fi
}

# Специализированная генерация кода с флагом --style music_video
song_step_code_draft() {
    log_step "4" "Режиссура клипа (Manim + Music Style)..."

    # 4.1 Визуал (Draft)
    if [ ! -f "$MANIM_DRAFT_FILE" ]; then
        echo "🎨 Создаем динамичный визуал..."
        python manim_processors/manim_code_generator.py \
            --mode visuals \
            --style music_video \
            --spec-file "$OUTPUT_DIR/spec.md" \
            --script-file "$SCRIPT_FILE" \
            --example-file "$EXAMPLE_FILE" \
            --output "$MANIM_DRAFT_FILE" \
            --model "$CODE_MODEL" \
            --config config.env
    else
        echo "✅ Черновик кода есть."
    fi
}

# Специализированная склейка (передаем аудио явно)
song_step_video_sync() {
    log_step "5" "Склейка с музыкой..."
    if [ ! -f "$OUTPUT_VIDEO_FILE" ]; then
        python manim_processors/manim_video_synchronizer.py \
            --pipeline-dir "$OUTPUT_DIR" \
            --timestamps-file "$TIMESTAMPS_FILE" \
            --output "$(basename "$OUTPUT_VIDEO_FILE")" \
            --manim-video "$(basename "$MANIM_VIDEO_FILE")" \
            --audio-source "$AUDIO_FILE" 
        
        echo "🎉 КЛИП ГОТОВ: $OUTPUT_VIDEO_FILE"
    else
        echo "✅ Файл $(basename "$OUTPUT_VIDEO_FILE") уже существует."
    fi
}

