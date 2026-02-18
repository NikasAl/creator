#!/bin/bash

set -e

# process_manim_v2.sh
# РЕФАКТОРИНГ: Использует lib/common/ вместо дублирования
# Версия Modular (spec_id: m5)

# ============================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================

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

# ============================================
# ПОДКЛЮЧЕНИЕ БИБЛИОТЕК (РЕФАКТОРИНГ)
# ============================================

# Общие модули (новые)
source "lib/common/utils.sh"
source "lib/common/audio.sh"
source "lib/common/music.sh"

# Manim-специфичные модули (обновлённые)
source "lib/manim/utils_v2.sh"
source "lib/manim/01_text.sh"
source "lib/manim/02_audio_v2.sh"
source "lib/manim/03_code.sh"
source "lib/manim/04_render.sh"
source "lib/manim/05_extra.sh"
source "lib/manim/copy_files.sh"

# ============================================
# ЗАПУСК ПАЙПЛАЙНА
# ============================================

log_header "🚀 Запуск пайплайна: $TITLE"
echo "📂 Директория: $OUTPUT_DIR"

# 1. Текст и Сценарий
manim_step_text_gen

# 2. Аудио (Human in the loop) и Транскрибация
manim_step_create_audio
manim_step_transcribe

# Опциональная коррекция транскрипции текста
check_and_correct_transcription

# 3. Код Manim
manim_step_code_draft
manim_step_compile_draft_loop # Интерактивный цикл
manim_step_code_sync

# 4. Рендеринг и Сборка
manim_step_render_sync_loop

# 5. Опциональный HQ Ререндер
manim_step_hq_rerun

# X. Фоновая музыка (опционально)
common_step_add_music "$OUTPUT_DIR" "$OUTPUT_VIDEO_FILE"

# 6. Маркетинг и Обложка
manim_step_promo
manim_step_pikabu
manim_step_cover

# 7. Копирование файлов (опционально)
manim_step_copy_files

log_success "🎉 Готово!"
