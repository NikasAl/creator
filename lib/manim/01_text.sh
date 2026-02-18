#!/bin/bash

# lib/manim/01_text.sh

manim_step_text_gen() {
    log_step "1" "Работа с текстом урока..."

    # 1.1 Генерация основного сценария
    if [ ! -f "$SCRIPT_FILE" ]; then
        echo "   🔹 Генерация сценария (LaTeX, структура)..."
        SPEC_IMG=$(find "$OUTPUT_DIR" -maxdepth 1 -name "spec.*" ! -name "*.md" | head -n 1)
        
        CMD="python text_processors/lesson_generator.py \
            --action generate \
            --input \"$SPEC_FILE\" \
            --output \"$SCRIPT_FILE\" \
            --model \"$SCRIPT_MODEL\" \
            --config config.env"
            
        if [ -n "$SPEC_IMG" ]; then
            CMD="$CMD --image \"$SPEC_IMG\""
        fi
        
        eval $CMD
    else
        echo "✅ Сценарий урока уже существует."
    fi

    # 1.2 Адаптация для TTS
    if [ ! -f "$TTS_SCRIPT_FILE" ]; then
        echo "   🔹 Адаптация для озвучки..."
        python text_processors/lesson_generator.py \
            --action adapt \
            --input "$SCRIPT_FILE" \
            --output "$TTS_SCRIPT_FILE" \
            --model "$SCRIPT_MODEL" \
            --config config.env
    else
        echo "✅ Текст для озвучки (TTS) уже существует."
    fi
}
