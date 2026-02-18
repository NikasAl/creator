#!/bin/bash

# lib/vd/06_music.sh

vd_step_add_music() {
    log_step "10" "Добавление фоновой музыки..."
    echo -e "\n${YELLOW} Добавить фоновую музыку?${NC}"
    echo "Это создаст отдельный файл с музыкой, не изменяя исходное видео."
    read -p "Пропустить? (y/n) >> " skip_add_music
    if [[ "$skip_add_music" =~ ^[Yy] ]]; then
        return 0
    fi

    local TARGET_VIDEO="${OUTPUT_VIDEO_FILE:-$OUTPUT_DIR/video.mp4}"
    if [[ "$TARGET_VIDEO" != /* ]]; then TARGET_VIDEO="$PWD/$TARGET_VIDEO"; fi

    if [ ! -f "$TARGET_VIDEO" ]; then
        echo "⚠️ Видео файл не найден: $TARGET_VIDEO"
        return 0
    fi

    # Спросим offset у пользователя (опционально)
    read -p "На сколько дБ музыка должна быть тише голоса? (по умолчанию 12.5, попробуй 6–8 для громче): " music_offset
    music_offset=${music_offset:-12.5}

    # Запускаем Python-скрипт
    python manim_processors/manim_music_mixer.py \
        --pipeline-dir "$OUTPUT_DIR" \
        --video "$(basename "$TARGET_VIDEO")" \
        --music-offset "$music_offset"

    if [ $? -eq 0 ]; then
        echo "✅ Файл с музыкой создан"
    else
        echo -e "${YELLOW}⚠️ Не удалось добавить музыку${NC}"
    fi
}
