#!/bin/bash

# lib/common/promo.sh
# Общие функции для создания промо-описаний и статей
# Устраняет дублирование между пайплайнами

# Подключаем общие утилиты
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

# ============================================
# ПРОМО-ОПИСАНИЯ
# ============================================

# Генерация промо-описания
generate_promo() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local source_file="${2:-}"
    local platform="${PROMO_PLATFORM:-YouTube}"
    local audience="${PROMO_AUDIENCE:-широкая аудитория}"
    local tone="${PROMO_TONE:-дружелюбный и информативный}"
    local lang="${PROMO_LANG:-русский}"
    local title="${PROMO_TITLE:-$TITLE}"
    local model="${PROMO_MODEL:-default}"
    
    log_step "?" "Создание промо-описания..."
    
    local cmd="python text_processors/promo_description_processor.py \"$output_dir\" \
        --config config.env \
        --model \"$model\" \
        --audience \"$audience\" \
        --tone \"$tone\" \
        --platform \"$platform\" \
        --lang \"$lang\" \
        --title \"$title\""
    
    if [ -n "$PROMO_PREFIX" ]; then
        cmd="$cmd --prefix \"$PROMO_PREFIX\""
    fi
    
    if [ -n "$source_file" ]; then
        cmd="$cmd --source-file \"$source_file\""
    fi
    
    local output_file="$output_dir/promo_description.txt"
    cmd="$cmd -o \"$output_file\""
    
    eval $cmd
    
    if [ $? -eq 0 ]; then
        log_success "Промо-описание создано: $output_file"
        return 0
    else
        log_error "Ошибка создания промо-описания"
        return 1
    fi
}

# Генерация расширенного промо (экспериментальное)
generate_promo_experimental() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local style="${2:-creative}"
    local source_file="${3:-}"
    local output_file="${4:-$output_dir/promo_experimental.txt}"
    
    log_step "?" "Создание экспериментального промо..."
    
    # Используем функцию из manim если доступна
    if type manim_step_promo_exp &>/dev/null; then
        manim_step_promo_exp "$style" "$source_file" "$output_file"
    else
        # Базовая реализация
        python text_processors/promo_description_processor.py "$output_dir" \
            --config config.env \
            --model "quality" \
            --style "$style" \
            -o "$output_file"
    fi
    
    if [ $? -eq 0 ]; then
        log_success "Промо создано: $output_file"
        return 0
    else
        log_error "Ошибка создания промо"
        return 1
    fi
}

# ============================================
# СТАТЬИ ДЛЯ ПИКАБУ
# ============================================

# Генерация статьи для Пикабу
generate_pikabu_article() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local source_file="${2:-}"
    local output_file="${3:-$output_dir/pikabu_article.txt}"
    
    log_step "?" "Создание статьи для Пикабу..."
    
    # Используем lesson_generator.py с action=pikabu
    if [ -f "$source_file" ]; then
        python text_processors/lesson_generator.py \
            --action pikabu \
            --input "$source_file" \
            --output "$output_file" \
            --config config.env
    else
        log_warning "Исходный файл не указан, используемpromo_description"
        if [ -f "$output_dir/promo_description.txt" ]; then
            python text_processors/lesson_generator.py \
                --action pikabu \
                --input "$output_dir/promo_description.txt" \
                --output "$output_file" \
                --config config.env
        else
            log_error "Нет исходного файла для генерации статьи"
            return 1
        fi
    fi
    
    if [ $? -eq 0 ]; then
        log_success "Статья для Пикабу создана: $output_file"
        return 0
    else
        log_error "Ошибка создания статьи"
        return 1
    fi
}

# ============================================
# HTML ЭКСПОРТ
# ============================================

# Конвертация в HTML
export_to_html() {
    local input_file="$1"
    local output_file="${2:-${input_file%.*}.html}"
    local title="${3:-$TITLE}"
    
    log_step "?" "Экспорт в HTML..."
    
    python text_processors/markdown_to_html.py \
        "$input_file" \
        -o "$output_file" \
        --title "$title"
    
    if [ $? -eq 0 ]; then
        log_success "HTML создан: $output_file"
        return 0
    else
        log_error "Ошибка экспорта в HTML"
        return 1
    fi
}

# ============================================
# КОРРЕКТУРА
# ============================================

# Корректура текста
correct_text() {
    local input_file="$1"
    local output_file="${2:-$input_file}"
    local title="${3:-$TITLE}"
    
    log_step "?" "Корректура текста..."
    
    python text_processors/correction_processor.py \
        "$input_file" \
        -o "$output_file" \
        --config config.env \
        --export-html \
        --html-title "$title"
    
    if [ $? -eq 0 ]; then
        log_success "Корректура выполнена: $output_file"
        return 0
    else
        log_warning "Корректура не выполнена"
        return 1
    fi
}

# ============================================
# ПОЛНЫЙ ПАЙПЛАЙН ПРОМО
# ============================================

# Полный пайплайн создания промо-материалов
promo_pipeline() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local source_file="${2:-}"
    
    # 1. Промо-описание
    if ask_yes_no "Создать промо-описание?"; then
        generate_promo "$output_dir" "$source_file"
    fi
    
    # 2. Статья для Пикабу
    if ask_yes_no "Создать статью для Пикабу?"; then
        generate_pikabu_article "$output_dir" "$source_file"
    fi
    
    # 3. HTML экспорт промо
    if [ -f "$output_dir/promo_description.txt" ]; then
        if ask_yes_no "Экспортировать промо в HTML?"; then
            export_to_html "$output_dir/promo_description.txt" \
                "$output_dir/promo_description.html" \
                "$TITLE"
        fi
    fi
}
