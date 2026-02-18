#!/bin/bash

# lib/manim/utils.sh
# Общие утилиты и конфигурация путей

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Дефолтные значения
LANGUAGE="${LANGUAGE:-ru}"
MODEL_CHOICE="${CODE_MODEL:-custom}" 
SCRIPT_MODEL="${SCRIPT_MODEL:-custom}"
QUALITY="${QUALITY:-low}"
TOTAL_STEPS="10"

# Пути
OUTPUT_DIR="$BASE_DIR"
SPEC_FILE="$OUTPUT_DIR/spec.md"
SCRIPT_FILE="$OUTPUT_DIR/lesson_script.txt"
TTS_SCRIPT_FILE="$OUTPUT_DIR/lesson_tts.txt"
AUDIO_FILE="$OUTPUT_DIR/audio.mp3"
TIMESTAMPS_FILE="sentence_timestamps.json"
FULL_TIMESTAMPS_PATH="$OUTPUT_DIR/$TIMESTAMPS_FILE"

# Manim файлы
MANIM_DRAFT_FILE="$OUTPUT_DIR/manim_draft.py"
MANIM_CODE_FILE="$OUTPUT_DIR/manim_lesson.py"
MANIM_VIDEO_FILE="$OUTPUT_DIR/manim_video.mp4"
EXAMPLE_FILE="$OUTPUT_DIR/manim_example.py"
OUTPUT_VIDEO_FILE="$OUTPUT_DIR/video.mp4"
PROMO_FILE="$OUTPUT_DIR/promo_description.txt"
PIKABU_FILE="$OUTPUT_DIR/pikabu_article.txt"
COVER_FILE="$OUTPUT_DIR/cover.jpg"

check_file_exists() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}❌ Файл $1 не найден.${NC}"
        return 1
    fi
    return 0
}

log_step() {
    echo -e "\n${YELLOW}[$1/$TOTAL_STEPS] $2${NC}"
}
