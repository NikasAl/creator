#!/bin/bash

vd_step_html() {
    run_step "Шаг 6: Создание HTML" \
        "$OUTPUT_DIR/discussion.html" \
        python text_processors/markdown_to_html.py "$OUTPUT_DIR/discussion.txt" \
            -o "$OUTPUT_DIR/discussion.html" \
            --title "$TITLE"
}

vd_step_links() {
    log_header "Шаг 6.1: Ссылки на фрагменты"
    read -p "Добавить ссылки на таймкоды видео? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "$OUTPUT_DIR/discussion.txt" ] && [ -f "$OUTPUT_DIR/segments.json" ]; then
            python text_processors/discussion_link_inserter.py \
                --pipeline-dir "$OUTPUT_DIR" \
                --video-url "$VIDEO_URL" \
                --regenerate-html \
                --title "$TITLE"
        else
            echo "⚠️ Не хватает файлов для создания ссылок."
        fi
    fi
}

vd_step_promo() {
    run_step "Шаг 6.2: Генерация промо-описания" \
        "$OUTPUT_DIR/promo_description.txt" \
        python text_processors/promo_description_processor.py "$OUTPUT_DIR" \
            --source-file "$OUTPUT_DIR/discussion.txt" \
            --output "$OUTPUT_DIR/promo_description.txt" \
            --config config.env \
            --model "$MODEL_CHOICE" \
            --title "$TITLE" \
            --audience "$PROMO_AUDIENCE" \
            --tone "$PROMO_TONE" \
            --platform "$PROMO_PLATFORM" \
            --lang "$PROMO_LANG"
}

vd_step_promo_html() {
    if [ -f "$OUTPUT_DIR/promo_description.txt" ]; then
        run_step "Шаг 6.3: HTML промо" \
            "$OUTPUT_DIR/promo_description.html" \
            python text_processors/markdown_to_html.py "$OUTPUT_DIR/promo_description.txt" \
                -o "$OUTPUT_DIR/promo_description.html" \
                --title "$TITLE - Промо"
    fi
}