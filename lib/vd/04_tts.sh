#!/bin/bash

# lib/vd/04_tts.sh

vd_step_adapt_for_tts() {
    log_step "4" "Адаптация текста для TTS..."

    if [ -f "$OUTPUT_DIR/discussion_tts.txt" ]; then
        echo "✅ Адаптированный текст $OUTPUT_DIR/discussion_tts.txt уже существует."
        return 0
    fi

    echo "🎙️ Подготавливаем текст из discussion.txt для озвучки..."
    python text_processors/discussion_to_tts.py \
        --input "$OUTPUT_DIR/discussion.txt" \
        --output "$OUTPUT_DIR/discussion_tts.txt" \
        --context "news_summary" \
        --config config.env
#        --model "$MODEL_CHOICE"

    if [ $? -eq 0 ] && [ -f "$OUTPUT_DIR/discussion_tts.txt" ]; then
        echo "✅ Текст успешно адаптирован для TTS."
    else
        echo "❌ Ошибка при адаптации текста для TTS."
        exit 1
    fi
}
