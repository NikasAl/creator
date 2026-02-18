#!/bin/bash

# lib/manim/05_extra.sh
# Подключаем cover_export (убедитесь, что он есть по этому пути, или перенесите код сюда)
source "$(dirname "$0")/lib/manim/cover_export.sh" 2>/dev/null || true

manim_step_promo() {
    local output_file="$OUTPUT_DIR/promo_description.txt"

    # If a parameter is provided, use it as the output filename
    if [ -n "$1" ]; then
        output_file="$1"
    fi

    log_step "7" "Создание промо? (y/n)"
    if [ ! -f "$output_file" ]; then
        read -p ">> " create_promo
        if [[ "$create_promo" =~ ^[Yy] ]]; then
            python text_processors/promo_description_processor.py "$OUTPUT_DIR" \
                --config config.env \
                --model "$PROMO_MODEL" \
                --title "$TITLE" \
                --source-file "$SCRIPT_FILE" \
                -o "$output_file"
        fi
    else
        echo "✅ $(basename "$output_file") уже существует."
    fi

    # Создаем HTML из промо-описания?
    if [ -f "$output_file" ]; then
        log_step "7.1" "Создать HTML из промо-описания? (y/n)"
        read -p ">> " create_html
        if [[ "$create_html" =~ ^[Yy] ]]; then
            python text_processors/markdown_to_html.py "$output_file"
        fi
    fi
}

manim_step_promo_exp() {
    local experiment_type="$1"
    local source_file="$2"
    local output_file="$3"

    # Validate required parameters
    if [ -z "$experiment_type" ] || [ -z "$source_file" ] || [ -z "$output_file" ]; then
        echo "❌ Error: Missing required parameters for manim_step_promo_exp"
        echo "   Usage: manim_step_promo_exp <experiment_type> <source_file> <output_file>"
        return 1
    fi

    log_step "7" "Создание промо? В режиме $experiment_type (y/n)"
    if [ ! -f "$output_file" ]; then
        read -p ">> " create_promo
        if [[ "$create_promo" =~ ^[Yy] ]]; then
            # --model "$PROMO_MODEL" \
            python text_processors/promo_experimental_processor.py "$OUTPUT_DIR" \
                --config config.env \
                --model "custom" \
                --experiment-type "$experiment_type" \
                --source-file "$source_file" \
                -o "$output_file"
        fi
    else
        echo "✅ $(basename "$output_file") уже существует."
    fi

    # Создаем HTML из промо-описания?
    if [ -f "$output_file" ]; then
        log_step "7.1" "Создать HTML из промо-описания? (y/n)"
        read -p ">> " create_html
        if [[ "$create_html" =~ ^[Yy] ]]; then
            python text_processors/markdown_to_html.py "$output_file"
        fi
    fi

}



manim_step_pikabu() {
    local output_file="$PIKABU_FILE"

    # If a parameter is provided, use it as the output filename
    if [ -n "$1" ]; then
        output_file="$1"
    fi

    log_step "8" "Создание статьи для Pikabu? (y/n)"
    if [ ! -f "$output_file" ]; then
        read -p ">> " create_pikabu
        if [[ "$create_pikabu" =~ ^[Yy] ]]; then
            python text_processors/promo_description_processor.py "$OUTPUT_DIR" \
                --config config.env \
                --model "$PROMO_MODEL" \
                --title "$TITLE" \
                --platform "Pikabu" \
                --audience "любители математики и технари" \
                --tone "с юмором и иронией" \
                --source-file "$SCRIPT_FILE" \
                -o "$output_file"
        fi
    else
        echo "✅ $(basename "$output_file") уже существует."
    fi

    # Создаем HTML из статьи для Pikabu?
    if [ -f "$output_file" ]; then
        log_step "7.1" "Создать HTML из статьи для Pikabu? (y/n)"
        read -p ">> " create_html
        if [[ "$create_html" =~ ^[Yy] ]]; then
            python text_processors/markdown_to_html.py "$output_file"
        fi
    fi

}

manim_step_cover() {
    log_step "9" "Экспорт обложки..."
    # Проверяем, загружена ли функция из cover_export.sh
    if type export_cover &>/dev/null; then
            export_cover "$OUTPUT_DIR" "$OUTPUT_VIDEO_FILE" "$COVER_FILE" "$TOTAL_STEPS"
    else
            echo -e "${RED}⚠️ Функция export_cover не найдена (проверьте lib/manim/cover_export.sh)${NC}"
    fi
}
