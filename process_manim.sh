#!/bin/bash

set -e

# process_manim.sh
# Версия Modular (spec_id: m5)

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

# 2. Подключение библиотек
source "lib/manim/utils.sh"
source "lib/manim/01_text.sh"
source "lib/manim/02_audio.sh"
source "lib/manim/03_code.sh"
source "lib/manim/04_render.sh"
source "lib/manim/05_extra.sh"
source "lib/vd/06_music.sh"
source "lib/manim/copy_files.sh"

echo -e "${GREEN}🚀 Запуск пайплайна: $TITLE${NC}"
echo "📂 Директория: $OUTPUT_DIR"

# ==========================================
# ЗАПУСК ПАЙПЛАЙНА
# ==========================================

# 1. Текст и Сценарий
manim_step_text_gen

# 2. Аудио (Human in the loop) и Транскрибация
manim_step_create_audio
manim_step_transcribe

# Опциональная коррекция транскрипции текста
if [ -f "$TTS_SCRIPT_FILE" ] && [ -f "$FULL_TIMESTAMPS_PATH" ]; then
    NOW=$(date +%s)
    FILE_TIME=$(stat -c %Y "$FULL_TIMESTAMPS_PATH")
    AGE=$((NOW - FILE_TIME))
    THRESHOLD=15

    if [ "$AGE" -lt "$THRESHOLD" ]; then
        echo ""
        echo "🆕 Файл транскрипции свежий (создан $AGE сек назад)."
        echo "🔧 Запуск корректора текста (LLM)..."
        python text_processors/transcription_corrector.py \
            --json "$FULL_TIMESTAMPS_PATH" \
            --reference "$TTS_SCRIPT_FILE"
    else
        echo ""
        echo "⏳ Файл транскрипции старый. Пропускаем коррекцию."
    fi
fi

# 3. Код Manim
manim_step_code_draft
manim_step_compile_draft_loop # Интерактивный цикл
manim_step_code_sync

# 4. Рендеринг и Сборка
manim_step_render_sync_loop

# 5. Опциональный HQ Ререндер
manim_step_hq_rerun

# X. Фоновая музыка (опционально)
vd_step_add_music


# 6. Маркетинг и Обложка
manim_step_promo
manim_step_pikabu
manim_step_cover

# 7. Копирование файлов (опционально)
manim_step_copy_files

echo -e "\n${GREEN}🎉 Готово!${NC}"