#!/bin/bash

# Скрипт для обработки видео (Modular Version)
# Использование: ./process_vd.sh config_file

# 1. Инициализация и конфиг
if [ $# -eq 0 ]; then
    echo "Конфигурационный файл не указан. Запускаем интерактивное создание конфигурации..."
    
    # Подключаем скрипт настройки
    if [ -f "lib/vd/setup.sh" ]; then
        source "lib/vd/setup.sh"
    else
        echo "Ошибка: не найден скрипт настройки lib/vd/setup.sh"
        exit 1
    fi
    
    # Запускаем интерактивное создание конфига
    CONFIG_FILE=$(setup_vd_config)
    if [ -z "$CONFIG_FILE" ]; then
        echo "Ошибка при создании конфигурационного файла"
        exit 1
    fi
    echo "Конфигурационный файл успешно создан: $CONFIG_FILE"
    echo "Для запуска пайплайна выполните команду:"
    echo "./process_vd.sh $CONFIG_FILE"
    exit 0
else
    CONFIG_FILE="$1"
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Ошибка: файл конфигурации $CONFIG_FILE не найден"
        exit 1
    fi
fi

source "$CONFIG_FILE"

# 2. Подключение библиотек
source "lib/vd/utils.sh"
source "lib/vd/01_download.sh"
source "lib/vd/02_text.sh"
source "lib/vd/03_discuss.sh"
source "lib/vd/04_web.sh"
source "lib/vd/04_tts.sh"
source "lib/vd/05_video.sh"
source "lib/vd/06_music.sh"

# 3. Проверка и Дефолтные значения
check_required_vars "VIDEO_URL" "BASE_DIR" "TITLE" "LANGUAGE" "MODE"

# Установка значений по умолчанию (если не заданы в конфиге)
AUTHOR="${AUTHOR:-Неизвестный автор}"
SEGMENTS_COUNT="${SEGMENTS_COUNT:-10}"
USE_ORIGINAL_VIDEO="${USE_ORIGINAL_VIDEO:-false}"
STYLE="${STYLE:-Реалистичный}"
ERA="${ERA:-21 век}"
REGION="${REGION:-Россия}"
GENRE="${GENRE:-Образовательное видео}"
SETTING="${SETTING:-Современная обстановка.}"
SECONDS_PER_ILLUSTRATION="${SECONDS_PER_ILLUSTRATION:-8}"
MODEL_CHOICE="${MODEL_CHOICE:-default}"
VIDEO_STRATEGY="${VIDEO_STRATEGY:-cut}"
PROMO_AUDIENCE="${PROMO_AUDIENCE:-широкая аудитория}"
PROMO_TONE="${PROMO_TONE:-дружелюбный и информативный}"
PROMO_PLATFORM="${PROMO_PLATFORM:-YouTube}"
PROMO_LANG="${PROMO_LANG:-русский}"

RESUME_MODE="${RESUME_MODE:-true}"
FORCE_REDO="${FORCE_REDO:-false}"

# Глобальные пути
OUTPUT_DIR="$BASE_DIR"
mkdir -p "$OUTPUT_DIR"

echo "🎬 Обработка видео: $TITLE"
echo "📂 Директория: $OUTPUT_DIR"
echo "📝 Режим: $MODE | Модель: $MODEL_CHOICE"

# ==========================================
# ЗАПУСК ПАЙПЛАЙНА
# ==========================================

# Шаг 1: Видео исходники
vd_step_download
vd_step_trim

# Шаг 2: Текст
vd_step_transcribe
vd_step_segment

# Шаг 3: Контент и Обсуждение
vd_step_discussion
vd_step_correction # Интерактивный
vd_step_qa         # Интерактивный

# Шаг 4: Адаптация текста для TTS
vd_step_adapt_for_tts

# Шаг 5: Веб и Промо
vd_step_html
vd_step_links      # Интерактивный
vd_step_promo
vd_step_promo_html

# Шаг 6: Медиа и Финальная сборка
vd_step_create_audio
vd_step_timestamps

if [ "$USE_ORIGINAL_VIDEO" = "true" ]; then
    vd_step_final_original_video
else
    vd_step_generate_illustrations
    vd_step_alibaba_refine   # Интерактивный
    vd_step_make_cover       # Интерактивный
    vd_step_final_gen_video  # Интерактивный
fi

# X. Фоновая музыка (опционально)
vd_step_add_music

log_header "🎉 Пайплайн завершен!"
echo "Результаты в: $OUTPUT_DIR"