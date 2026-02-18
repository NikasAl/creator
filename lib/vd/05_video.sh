#!/bin/bash

vd_step_create_audio() {
    # Импортируем функции из manim/audio.sh
    source "lib/manim/02_audio.sh"

    # Устанавливаем переменные для совместимости с manim скриптом
    TTS_SCRIPT_FILE="$OUTPUT_DIR/discussion_tts.txt"
    AUDIO_FILE="$OUTPUT_DIR/audio.mp3"

    manim_step_create_audio
}

vd_step_timestamps() {
    # Пропускаем, если таймстампы уже есть в тексте (грубая проверка grep)
    if [ "$RESUME_MODE" = "true" ] && grep -q "^[0-9][0-9]:[0-9][0-9]:" "$OUTPUT_DIR/discussion.txt" 2>/dev/null; then
         echo "⏭️ Таймстампы, похоже, уже есть."
         return 0
    fi

    run_step "Шаг 7.1: Добавление таймстампов" \
        "NONE" \
        python text_processors/discussion_timestamps_processor.py \
            --pipeline-dir "$OUTPUT_DIR" \
            --audio-file "$OUTPUT_DIR/audio.mp3" \
            --language "$LANGUAGE" \
            --config config.env
}

# --- Ветка ORIGINAL VIDEO ---
vd_step_final_original_video() {
    log_header "Шаг 8: Сборка с исходным видео"
    python video_processors/video_cutter.py "$OUTPUT_DIR" --preview
    
    read -p "Стратегия (cut/speed) [cut]: " strategy
    strategy="${strategy:-cut}"
    
    python video_processors/video_cutter.py "$OUTPUT_DIR" \
        --output "$OUTPUT_DIR/video.mp4" \
        --strategy "$strategy"
}

# --- Ветка ILLUSTRATIONS ---
vd_step_generate_illustrations() {
    log_header "Шаг 8a: Генерация промптов для иллюстраций"
    
    # Расчет частей
    local parts=10
    if [ -n "$AUDIO_DURATION" ]; then
        local calc=$(python -c "import math; print(max(4, math.ceil($AUDIO_DURATION / $SECONDS_PER_ILLUSTRATION)))")
        parts=$((calc < 8 ? 8 : calc))
    fi
    echo "📊 Иллюстраций: $parts"

    local bible_arg=""
    [ -f "$OUTPUT_DIR/bible.json" ] && bible_arg="--bible-in $OUTPUT_DIR/bible.json"

    run_step "Создание промптов" \
        "$OUTPUT_DIR/illustrations.json" \
        python video_processors/illustration_prompt_processor_v2.py \
            "$OUTPUT_DIR/discussion.txt" \
            --parts "$parts" \
            --style "$STYLE" \
            -o "$OUTPUT_DIR/illustrations.json" \
            $bible_arg \
            --bible-out "$OUTPUT_DIR/bible.json" \
            --title "$TITLE" \
            --author "$AUTHOR" \
            --era "$ERA" \
            --region "$REGION" \
            --genre "$GENRE" \
            --setting "$SETTING"

    # Цикл ревью
    while true; do
        echo "🎨 Генерация/Просмотр иллюстраций..."
        python video_processors/illustration_review_cli.py --pipeline-dir "$OUTPUT_DIR"
        feh "$OUTPUT_DIR/images/"
        read -p "Пересоздать иллюстрации? (y/n): " -r
        [[ ! $REPLY =~ ^[Yy]$ ]] && break
    done
}

vd_step_make_cover() {
    echo ""
    read -p "Создать обложку? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python image_generators/make_cover.py "$OUTPUT_DIR"
    fi
}

vd_step_alibaba_refine() {
    echo ""
    read -p "Перегенерировать через Alibaba Cloud? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        while true; do
            ls -la "$OUTPUT_DIR/images/" | head -10
            read -p "Номера картинок (1,3,5): " indices
            [ -n "$indices" ] && python video_processors/alibaba_image_generator.py \
                --pipeline-dir "$OUTPUT_DIR" --indices "$indices" --size "1360*768" --n 1
            
            read -p "Ещё? (y/n): " -r
            [[ ! $REPLY =~ ^[Yy]$ ]] && break
        done
    fi
}

vd_step_final_gen_video() {
    echo ""
    read -p "Создать финальное видео? (y/n): " -r
    [[ ! $REPLY =~ ^[Yy]$ ]] && return 0

    read -p "Тишина в начале (сек) [0]: " s_dur
    read -p "Тишина в конце (сек) [0]: " e_dur
    s_dur="${s_dur:-0}"
    e_dur="${e_dur:-0}"

    python video_processors/video_generator.py \
        --pipeline-dir "$OUTPUT_DIR" \
        --silence-duration "$s_dur" \
        --ending-duration "$e_dur" \
        --fade-duration 0.5 \
        --quality medium
}