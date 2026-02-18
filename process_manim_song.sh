#!/bin/bash

set -e

# process_manim_song.sh
# Пайплайн для создания музыкального клипа (Modular Version)

# 1. Инициализация и конфиг
if [ $# -eq 0 ]; then
    echo "Использование: $0 <config_file>"
    exit 1
fi

CONFIG_FILE="$1"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Ошибка: файл конфигурации $CONFIG_FILE не найден"
    exit 1
fi

source "$CONFIG_FILE"

# 2. Подключение базовых утилит
source "lib/manim/utils.sh"

# ==========================================
# ПЕРЕОПРЕДЕЛЕНИЕ ПЕРЕМЕННЫХ (CONTEXT SWITCH)
# ==========================================
# Мы подменяем стандартные пути на пути для песни, 
# чтобы переиспользовать функции ожидания аудио, компиляции и рендера.

TOTAL_STEPS="5"
AUDIO_FILE="$OUTPUT_DIR/song_audio.mp3"
SCRIPT_FILE="$OUTPUT_DIR/song_lyrics.txt"   # Теперь "сценарий" — это текст песни
TIMESTAMPS_FILE="song_timestamps.json"
FULL_TIMESTAMPS_PATH="$OUTPUT_DIR/$TIMESTAMPS_FILE"

MANIM_DRAFT_FILE="$OUTPUT_DIR/song_manim_draft.py"
MANIM_CODE_FILE="$OUTPUT_DIR/song_manim_final.py"
MANIM_VIDEO_FILE="$OUTPUT_DIR/song_manim_video.mp4"
OUTPUT_VIDEO_FILE="$OUTPUT_DIR/song_video.mp4"
PIKABU_FILE="$OUTPUT_DIR/song_pikabu_article.txt"
COVER_FILE="$OUTPUT_DIR/song_cover.jpg"

# 3. Подключение библиотек
source "lib/manim/02_audio.sh"  # Берем manim_step_create_audio
source "lib/manim/03_code.sh"   # Берем manim_step_compile_draft_loop и manim_step_code_sync
source "lib/manim/04_render.sh" # Берем manim_step_render_final
source "lib/manim/05_extra.sh"  # функции промо и обложки
source "lib/manim/song_logic.sh" # Уникальные функции для песни

echo -e "${PURPLE}🎸 Запуск МУЗЫКАЛЬНОГО пайплайна: $TITLE${NC}"
echo "📂 Директория: $OUTPUT_DIR"

# ==========================================
# ЗАПУСК ПАЙПЛАЙНА
# ==========================================

# 1. Генерация текста песни (Уникальная функция)
song_step_lyrics

# 2. Ожидание аудио (Переиспользуем стандартную функцию, она теперь смотрит на song_audio.mp3)
manim_step_create_audio

# 3. Транскрибация (Уникальная функция, так как нужен hint-file)
song_step_transcribe

if [ -f "$SCRIPT_FILE" ] && [ -f "$FULL_TIMESTAMPS_PATH" ]; then
    NOW=$(date +%s)
    FILE_TIME=$(stat -c %Y "$FULL_TIMESTAMPS_PATH")
    AGE=$((NOW - FILE_TIME))
    THRESHOLD=5
    
    if [ "$AGE" -lt "$THRESHOLD" ]; then
        echo ""
        echo "🆕 Файл транскрипции свежий (создан $AGE сек назад)."
        echo "🔧 Запуск корректора текста (LLM)..."
        python text_processors/transcription_corrector.py \
            --json "$FULL_TIMESTAMPS_PATH" \
            --reference "$SCRIPT_FILE"
    else
        echo ""
        echo "⏳ Файл транскрипции старый. Пропускаем коррекцию."
    fi
fi


# 4. Код Manim
song_step_code_draft            # Уникальная (флаг --style music_video)
manim_step_compile_draft_loop   # Стандартная (работает с переопределенным MANIM_DRAFT_FILE)
manim_step_code_sync            # Стандартная (работает с переопределенными путями)

# 5. Рендеринг и Сборка
#manim_step_render_final         # Стандартная (рендерит переопределенный MANIM_CODE_FILE)
#song_step_video_sync            # Уникальная (явно передает аудио для надежности)
manim_step_render_sync_loop


# сборка в высоком разрешении
manim_step_hq_rerun

# генерация промо и статей
# 6. Маркетинг и Обложка
manim_step_promo "$OUTPUT_DIR/song_promo_description.txt"
manim_step_promo_exp "song_pikabu" "$SCRIPT_FILE" "$OUTPUT_DIR/song_pikabu_article.txt"

QUALITY="high"
manim_step_cover

echo -e "\n${PURPLE}🎉 Музыкальный клип готов!${NC}"
