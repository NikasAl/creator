#!/bin/bash

# lib/common/music.sh
# Общие функции для добавления фоновой музыки
# Используется в обоих пайплайнах: Manim и Video Discussion

# Подключаем общие утилиты
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

# ============================================
# ДОБАВЛЕНИЕ ФОНОВОЙ МУЗЫКИ
# ============================================

# Универсальный шаг добавления фоновой музыки
common_step_add_music() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local video_file="${2:-$output_dir/video.mp4}"
    local step_num="${3:-10}"

    log_step "$step_num" "Добавление фоновой музыки..."

    echo -e "\n${YELLOW}Добавить фоновую музыку?${NC}"
    echo "Это создаст отдельный файл с музыкой, не изменяя исходное видео."
    read -p "Пропустить? (y/n) >> " skip_add_music
    if [[ "$skip_add_music" =~ ^[Yy] ]]; then
        return 0
    fi

    # Нормализуем путь
    if [[ "$video_file" != /* ]]; then
        video_file="$PWD/$video_file"
    fi

    if [ ! -f "$video_file" ]; then
        log_warning "Видео файл не найден: $video_file"
        return 0
    fi

    # Спросим offset у пользователя
    read -p "На сколько дБ музыка должна быть тише голоса? (по умолчанию 12.5, попробуй 6–8 для громче): " music_offset
    music_offset=${music_offset:-12.5}

    # Запускаем Python-скрипт
    python manim_processors/manim_music_mixer.py \
        --pipeline-dir "$output_dir" \
        --video "$(basename "$video_file")" \
        --music-offset "$music_offset"

    if [ $? -eq 0 ]; then
        log_success "Файл с музыкой создан"
    else
        log_warning "Не удалось добавить музыку"
    fi
}

# ============================================
# СОВМЕСТИМОСТЬ СО СТАРЫМИ СКРИПТАМИ
# ============================================

# Для обратной совместимости с lib/vd/06_music.sh
vd_step_add_music() {
    common_step_add_music "$OUTPUT_DIR" "${OUTPUT_VIDEO_FILE:-$OUTPUT_DIR/video.mp4}"
}

# Для обратной совместимости с lib/manim/
manim_step_add_music() {
    common_step_add_music "$OUTPUT_DIR" "$OUTPUT_VIDEO_FILE"
}
