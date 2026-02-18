#!/bin/bash

vd_step_transcribe() {
    if [ -n "$USE_TRANSCRIPT_FILE" ] && [ -f "$USE_TRANSCRIPT_FILE" ]; then
        log_header "Шаг 2: Копирование готового транскрипта"
        cp "$USE_TRANSCRIPT_FILE" "$OUTPUT_DIR/transcript.txt"
        echo "✅ Файл скопирован."
        return 0
    fi

    run_step "Шаг 2: Транскрипция аудио" \
        "$OUTPUT_DIR/transcript.txt" \
        python video_processors/video_transcriber.py "$OUTPUT_DIR/original_audio.mp3" \
            --output-dir "$OUTPUT_DIR" \
            --language "$LANGUAGE" \
            --config config.env
}

vd_step_segment() {
    # Подготовка аргументов (если есть transcript.json)
    local extra_args=""
    if [ -f "$OUTPUT_DIR/transcript.json" ]; then
        extra_args="--transcript-json $OUTPUT_DIR/transcript.json"
    fi

    run_step "Шаг 3: Сегментация текста" \
        "$OUTPUT_DIR/segments.json" \
        python text_processors/text_segmenter.py "$OUTPUT_DIR/transcript.txt" \
            --output "$OUTPUT_DIR/segments.json" \
            --segments "$SEGMENTS_COUNT" \
            --config "$CONFIG_FILE" \
            --model "$MODEL_CHOICE" \
            $extra_args
}
