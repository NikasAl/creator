#!/bin/bash

# lib/vd/utils.sh
# Общие утилиты для Video Discussion пайплайна
#
# РЕФАКТОРИНГ: Теперь делегирует общие функции в lib/common/utils.sh
# Оставляет только специфичные для VD настройки и функции

# Подключаем общие утилиты
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/utils.sh"

# ============================================
# СПЕЦИФИЧНЫЕ ДЛЯ VD ФУНКЦИИ
# ============================================

# Универсальная функция запуска шага с проверкой существования файлов
# Использование: run_step "Название шага" "целевой_файл_для_проверки" команда аргументы...
# Если "целевой_файл_для_проверки" равен "NONE", проверка файла пропускается
run_step() {
    local step_name="$1"
    local target_file="$2"
    shift 2
    local command=("$@")

    log_header "$step_name"

    # Логика пропуска
    if [ "$FORCE_REDO" = "true" ]; then
        log_info "Режим FORCE_REDO: Выполняем заново..."
    elif [ "$RESUME_MODE" = "true" ] && [ "$target_file" != "NONE" ] && [ -f "$target_file" ]; then
        log_success "Пропуск: обнаружен файл $target_file"
        return 0
    fi

    # Выполнение команды
    log_info "Запуск: ${command[*]}"
    "${command[@]}"

    local status=$?
    if [ $status -ne 0 ]; then
        log_error "Ошибка при выполнении шага: $step_name"
        exit $status
    else
        log_success "Шаг выполнен успешно!"
    fi
}

# Проверка режима работы
is_resume_mode() {
    [ "$RESUME_MODE" = "true" ]
}

is_force_redo() {
    [ "$FORCE_REDO" = "true" ]
}

# Проверка использования оригинального видео
use_original_video() {
    [ "$USE_ORIGINAL_VIDEO" = "true" ]
}

# ============================================
# СПЕЦИФИЧНЫЕ ДЛЯ VD НАСТРОЙКИ ПУТЕЙ
# ============================================

# Инициализация путей VD пайплайна
init_vd_paths() {
    OUTPUT_DIR="$BASE_DIR"
    DISCUSSION_FILE="$OUTPUT_DIR/discussion.txt"
    TTS_SCRIPT_FILE="$OUTPUT_DIR/discussion_tts.txt"
    AUDIO_FILE="$OUTPUT_DIR/audio.mp3"
    TIMESTAMPS_FILE="$OUTPUT_DIR/sentence_timestamps.json"

    # Создаём директорию
    mkdir -p "$OUTPUT_DIR"
}

# Проверка обязательных переменных для VD пайплайна
check_vd_required_vars() {
    check_required_vars "VIDEO_URL" "BASE_DIR" "TITLE" "LANGUAGE" "MODE"
}
