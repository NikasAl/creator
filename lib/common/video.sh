#!/bin/bash

# lib/common/video.sh
# Общие функции для генерации видео
# Устраняет дублирование между lib/manim/ и lib/vd/

# Подключаем общие утилиты
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

# ============================================
# ГЕНЕРАЦИЯ ИЛЛЮСТРАЦИЙ
# ============================================

# Генерация описаний иллюстраций
generate_illustration_prompts() {
    local text_file="$1"
    local output_dir="${2:-$OUTPUT_DIR}"
    local parts="${PARTS:-12}"
    local style="${STYLE:-Реалистичный}"
    
    log_step "?" "Создание описаний иллюстраций..."
    
    local cmd="python video_processors/illustration_prompt_processor_v2.py \
        \"$text_file\" \
        --parts \"$parts\" \
        --style \"$style\" \
        -o \"$output_dir/illustrations.json\" \
        --bible-out \"$output_dir/bible.json\" \
        --title \"${TITLE:-}\" \
        --author \"${AUTHOR:-}\" \
        --era \"${ERA:-}\" \
        --region \"${REGION:-}\" \
        --genre \"${GENRE:-}\" \
        --setting \"${SETTING:-}\""
    
    # Если bible.json существует, используем её
    if [ -f "$output_dir/bible.json" ]; then
        cmd="$cmd --bible-in \"$output_dir/bible.json\""
        log_info "Используем существующую bible.json"
    fi
    
    # Добавляем длительность аудио если доступна
    if [ -n "$AUDIO_DURATION" ]; then
        cmd="$cmd --audio-duration \"$AUDIO_DURATION\" --seconds-per-illustration ${SECONDS_PER_ILLUSTRATION:-8}"
    fi
    
    eval $cmd
    
    if [ $? -eq 0 ]; then
        log_success "Описания иллюстраций созданы"
        return 0
    else
        log_error "Ошибка создания описаний"
        return 1
    fi
}

# Генерация изображений
generate_illustrations() {
    local output_dir="${1:-$OUTPUT_DIR}"
    
    log_step "?" "Генерация изображений..."
    
    python video_processors/illustration_review_cli.py --pipeline-dir "$output_dir"
    
    if [ $? -eq 0 ]; then
        log_success "Изображения созданы"
        return 0
    else
        log_error "Ошибка генерации изображений"
        return 1
    fi
}

# Перегенерация через Alibaba
regenerate_alibaba_images() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local indices="$2"
    
    if [ -z "$indices" ]; then
        log_warning "Не указаны индексы изображений"
        return 1
    fi
    
    log_step "?" "Перегенерация изображений через Alibaba Cloud..."
    
    python video_processors/alibaba_image_generator.py \
        --pipeline-dir "$output_dir" \
        --indices "$indices" \
        --size "1360*768" \
        --n 1
    
    return $?
}

# ============================================
# ГЕНЕРАЦИЯ ВИДЕО
# ============================================

# Генерация финального видео
generate_final_video() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local silence_duration="${2:-0}"
    local ending_duration="${3:-0}"
    
    log_step "?" "Создание финального видео..."
    
    python video_processors/video_generator.py \
        --pipeline-dir "$output_dir" \
        --silence-duration "$silence_duration" \
        --ending-duration "$ending_duration" \
        --fade-duration 0.5 \
        --quality medium
    
    if [ $? -eq 0 ]; then
        log_success "Видео создано: $output_dir/video.mp4"
        return 0
    else
        log_error "Ошибка создания видео"
        return 1
    fi
}

# Генерация видео из одного изображения (Alibaba)
generate_video_from_image() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local image_index="$2"
    local duration="${3:-5}"
    local resolution="${4:-720P}"
    
    log_step "?" "Создание видео из изображения $image_index..."
    
    python video_processors/alibaba_video_generator.py \
        --pipeline-dir "$output_dir" \
        --image-index "$image_index" \
        --duration "$duration" \
        --resolution "$resolution"
    
    return $?
}

# ============================================
# ОБЛОЖКИ
# ============================================

# Создание обложки
generate_cover() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local video_file="${2:-$output_dir/video.mp4}"
    local cover_file="${3:-$output_dir/cover.jpg}"
    local timestamp="${4:-6}"
    
    log_step "?" "Создание обложки..."
    
    # Проверяем наличие директории images
    if [ -d "$output_dir/images" ]; then
        python image_generators/make_cover.py "$output_dir"
    else
        # Извлекаем кадр из видео
        ffmpeg -y -ss "00:00:$timestamp" -i "$video_file" -vframes 1 -q:v 2 "$cover_file" 2>/dev/null
    fi
    
    if [ -f "$cover_file" ]; then
        log_success "Обложка создана: $cover_file"
        return 0
    else
        log_warning "Не удалось создать обложку"
        return 1
    fi
}

# ============================================
# ШОРТЫ
# ============================================

# Создание вертикального шорта
create_short() {
    local video_file="$1"
    local start_time="$2"  # формат мм:сс
    local end_time="$3"    # формат мм:сс
    local output_file="$4"
    
    log_info "Создание шорта: $start_time - $end_time"
    
    ./video_processors/crop_vertical.sh "$video_file" "$start_time" "$end_time" "$output_file"
    
    if [ $? -eq 0 ]; then
        log_success "Шорт создан: $output_file"
        return 0
    else
        log_error "Ошибка создания шорта"
        return 1
    fi
}

# Интерактивное создание шортов
interactive_create_shorts() {
    local video_file="${1:-$OUTPUT_DIR/video.mp4}"
    local shorts_dir="${2:-$OUTPUT_DIR/shorts}"
    
    mkdir -p "$shorts_dir"
    
    while true; do
        echo ""
        read -p "Введите начальное время (мм:сс) или Enter для выхода: " start_time
        
        if [ -z "$start_time" ]; then
            break
        fi
        
        if [[ ! "$start_time" =~ ^[0-9]{1,2}:[0-9]{2}$ ]]; then
            log_warning "Неверный формат времени. Используйте мм:сс"
            continue
        fi
        
        read -p "Введите конечное время (мм:сс): " end_time
        
        if [[ ! "$end_time" =~ ^[0-9]{1,2}:[0-9]{2}$ ]]; then
            log_warning "Неверный формат времени. Используйте мм:сс"
            continue
        fi
        
        local safe_start=${start_time//:/-}
        local safe_end=${end_time//:/-}
        local output="$shorts_dir/short_${safe_start}_${safe_end}.mp4"
        
        create_short "$video_file" "$start_time" "$end_time" "$output"
        
        if ! ask_yes_no "Создать ещё один шорт?"; then
            break
        fi
    done
}

# ============================================
# ПОЛНЫЕ ПАЙПЛАЙНЫ
# ============================================

# Полный пайплайн создания слайд-шоу
slideshow_pipeline() {
    local text_file="$1"
    local audio_file="$2"
    local output_dir="${3:-$OUTPUT_DIR}"
    
    # Определяем длительность аудио
    if [ -f "$audio_file" ]; then
        AUDIO_DURATION=$(get_audio_duration "$audio_file")
        log_info "Длительность аудио: ${AUDIO_DURATION} сек"
        
        # Рассчитываем количество иллюстраций
        local secs_per_img=${SECONDS_PER_ILLUSTRATION:-8}
        local calculated=$(python -c "import math; print(max(8, math.ceil($AUDIO_DURATION / $secs_per_img)))")
        PARTS=$calculated
        log_info "Количество иллюстраций: $PARTS"
    fi
    
    # 1. Генерация описаний
    generate_illustration_prompts "$text_file" "$output_dir"
    if [ $? -ne 0 ]; then return 1; fi
    
    # 2. Интерактивная генерация изображений
    if ask_yes_no "Создать иллюстрации?"; then
        while true; do
            generate_illustrations "$output_dir"
            
            if ! ask_yes_no "Пересоздать иллюстрации?"; then
                break
            fi
        done
    fi
    
    # 3. Опциональная перегенерация через Alibaba
    if ask_yes_no "Перегенерировать через Alibaba?"; then
        echo "Доступные изображения:"
        ls -la "$output_dir/images/illustration_*.png" 2>/dev/null | head -10
        
        read -p "Введите номера через запятую (например: 1,3,5): " indices
        if [ -n "$indices" ]; then
            regenerate_alibaba_images "$output_dir" "$indices"
        fi
    fi
    
    # 4. Создание обложки
    if ask_yes_no "Создать обложку?"; then
        generate_cover "$output_dir"
    fi
    
    # 5. Создание видео
    if ask_yes_no "Создать финальное видео?"; then
        read -p "Silence duration (сек, по умолчанию 0): " silence
        read -p "Ending duration (сек, по умолчанию 0): " ending
        
        generate_final_video "$output_dir" "${silence:-0}" "${ending:-0}"
    fi
    
    # 6. Создание шортов
    if ask_yes_no "Создать шорты?"; then
        interactive_create_shorts "$output_dir/video.mp4" "$output_dir/shorts"
    fi
}
