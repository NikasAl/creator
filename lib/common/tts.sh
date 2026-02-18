#!/bin/bash

# lib/common/tts.sh
# Общие функции для синтеза речи
# Устраняет дублирование между lib/manim/02_audio.sh и lib/vd/04_tts.sh

# Подключаем общие утилиты
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

# ============================================
# КОНФИГУРАЦИЯ TTS
# ============================================

# Доступные TTS-движки
TTS_ENGINES=("alibaba" "silero" "sber")

# Дефолтный движок
DEFAULT_TTS_ENGINE="${TTS_ENGINE:-alibaba}"

# Голоса для разных движков
declare -A TTS_VOICES=(
    ["alibaba"]="Cherry"
    ["silero"]="aidar"
    ["sber"]="Nec_24000"
)

# ============================================
# ВЫБОР TTS ДВИЖКА
# ============================================

# Интерактивный выбор TTS движка
select_tts_engine() {
    local prompt="${1:-Выберите TTS движок:}"
    
    echo "$prompt"
    select engine in "${TTS_ENGINES[@]}"; do
        if [ -n "$engine" ]; then
            echo "$engine"
            return 0
        fi
        log_warning "Неверный выбор. Попробуйте снова."
    done
}

# Получить голос для движка
get_tts_voice() {
    local engine="${1:-$DEFAULT_TTS_ENGINE}"
    echo "${TTS_VOICES[$engine]}"
}

# ============================================
# СИНТЕЗ РЕЧИ
# ============================================

# Универсальная функция синтеза речи
# Автоматически выбирает движок на основе конфигурации
synthesize_speech() {
    local text_file="$1"
    local output_file="$2"
    local engine="${3:-$DEFAULT_TTS_ENGINE}"
    local voice="${4:-$(get_tts_voice "$engine")}"
    local language="${LANGUAGE:-ru}"
    
    log_info "Синтез речи через $engine (голос: $voice)"
    
    case "$engine" in
        alibaba)
            synthesize_alibaba "$text_file" "$output_file" "$voice" "$language"
            ;;
        silero)
            synthesize_silero "$text_file" "$output_file" "$voice"
            ;;
        sber)
            synthesize_sber "$text_file" "$output_file" "$voice"
            ;;
        *)
            log_error "Неизвестный TTS движок: $engine"
            return 1
            ;;
    esac
}

# Alibaba TTS
synthesize_alibaba() {
    local text_file="$1"
    local output_file="$2"
    local voice="${3:-Cherry}"
    local language="${4:-Auto}"
    
    if [ ! -f "$text_file" ]; then
        log_error "Файл не найден: $text_file"
        return 1
    fi
    
    log_step "?" "Синтез речи через Alibaba TTS..."
    
    python speech_processors/alibaba_tts.py "$text_file" \
        --voice "$voice" \
        --language "$language" \
        --output "$output_file"
    
    if [ $? -eq 0 ]; then
        log_success "Аудио создано: $output_file"
        return 0
    else
        log_error "Ошибка синтеза речи"
        return 1
    fi
}

# Silero TTS (локальный)
synthesize_silero() {
    local text_file="$1"
    local output_file="$2"
    local voice="${3:-aidar}"
    
    if [ ! -f "$text_file" ]; then
        log_error "Файл не найден: $text_file"
        return 1
    fi
    
    log_step "?" "Синтез речи через Silero (локальный)..."
    
    python speech_processors/silero.py "$text_file" \
        --voice "$voice" \
        --output "$output_file"
    
    if [ $? -eq 0 ]; then
        log_success "Аудио создано: $output_file"
        return 0
    else
        log_error "Ошибка синтеза речи"
        return 1
    fi
}

# Sber TTS
synthesize_sber() {
    local text_file="$1"
    local output_file="$2"
    local voice="${3:-Nec_24000}"
    
    if [ ! -f "$text_file" ]; then
        log_error "Файл не найден: $text_file"
        return 1
    fi
    
    log_step "?" "Синтез речи через Sber API..."
    
    python speech_processors/sber_api_synth.py "$text_file" \
        --voice "$voice" \
        --output "$output_file"
    
    if [ $? -eq 0 ]; then
        log_success "Аудио создано: $output_file"
        return 0
    else
        log_error "Ошибка синтеза речи"
        return 1
    fi
}

# ============================================
# ПОДГОТОВКА ТЕКСТА ДЛЯ TTS
# ============================================

# Подготовка текста для озвучивания
# Убирает markdown-разметку, специальные символы и т.д.
prepare_text_for_tts() {
    local input_file="$1"
    local output_file="$2"
    
    log_info "Подготовка текста для TTS..."
    
    python text_processors/summary_cleaner.py "$input_file" -o "$output_file"
    
    if [ $? -eq 0 ]; then
        log_success "Текст подготовлен: $output_file"
        return 0
    else
        log_error "Ошибка подготовки текста"
        return 1
    fi
}

# ============================================
# ПОЛНЫЙ ПАЙПЛАЙН TTS
# ============================================

# Полный пайплайн создания аудио
# 1. Подготовка текста
# 2. Синтез речи
# 3. Проверка результата
create_audio_pipeline() {
    local text_file="$1"
    local output_dir="${2:-.}"
    local engine="${3:-$DEFAULT_TTS_ENGINE}"
    
    local tts_file="$output_dir/tts_text.txt"
    local audio_file="$output_dir/audio.mp3"
    
    # Шаг 1: Подготовка текста
    if [ "$text_file" != "$tts_file" ]; then
        prepare_text_for_tts "$text_file" "$tts_file"
        if [ $? -ne 0 ]; then
            return 1
        fi
    else
        tts_file="$text_file"
    fi
    
    # Шаг 2: Синтез речи
    synthesize_speech "$tts_file" "$audio_file" "$engine"
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Шаг 3: Проверка
    if [ -f "$audio_file" ]; then
        local duration=$(get_audio_duration "$audio_file")
        log_success "Аудио готово: $audio_file (${duration} сек)"
        echo "$audio_file"
        return 0
    else
        log_error "Аудиофайл не создан"
        return 1
    fi
}

# ============================================
# ОЖИДАНИЕ ПОЛЬЗОВАТЕЛЬСКОГО АУДИО
# ============================================

# Ожидание, пока пользователь создаст аудио вручную
wait_for_user_audio() {
    local audio_file="${1:-$OUTPUT_DIR/audio.mp3}"
    local message="${2:-Поместите аудиофайл в:}"
    
    log_header "🎵 Ожидание аудиофайла"
    echo "$message"
    echo "   $audio_file"
    echo ""
    echo "Варианты:"
    echo "  1. Используйте TTS сервис и сохраните как audio.mp3"
    echo "  2. Запишите голос самостоятельно"
    echo "  3. Используйте существующий аудиофайл"
    echo ""
    
    while [ ! -f "$audio_file" ]; do
        read -p "Нажмите Enter когда файл будет готов (или 'q' для выхода)..." -r
        if [[ "$REPLY" =~ ^[Qq]$ ]]; then
            log_warning "Выход"
            return 1
        fi
    done
    
    log_success "Аудиофайл найден: $audio_file"
    
    # Показываем длительность
    local duration=$(get_audio_duration "$audio_file")
    log_info "Длительность: ${duration} секунд"
    
    return 0
}

# Проверка и создание аудио
ensure_audio_exists() {
    local audio_file="${1:-$AUDIO_FILE}"
    local text_file="${2:-$TTS_SCRIPT_FILE}"
    
    if [ -f "$audio_file" ]; then
        log_success "Аудио уже существует: $audio_file"
        return 0
    fi
    
    # Если есть текст - предлагаем TTS
    if [ -f "$text_file" ]; then
        if ask_yes_no "Создать аудио через TTS?" "y"; then
            local engine=$(select_tts_engine "Выберите TTS движок:")
            synthesize_speech "$text_file" "$audio_file" "$engine"
            return $?
        fi
    fi
    
    # Иначе ждём ручного создания
    wait_for_user_audio "$audio_file"
    return $?
}
