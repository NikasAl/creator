#!/bin/bash

# lib/common/utils.sh
# Общие утилиты для всех пайплайнов
# Используется для устранения дублирования между lib/manim/ и lib/vd/

# ============================================
# ЦВЕТА И ФОРМАТИРОВАНИЕ
# ============================================

# Экспортируем цвета для использования в других скриптах
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export NC='\033[0m' # No Color

# ============================================
# ЛОГИРОВАНИЕ
# ============================================

# Единая функция для заголовков (используется во всех пайплайнах)
log_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# Единая функция для шагов (с номером)
log_step() {
    local step_num="$1"
    local total_steps="${TOTAL_STEPS:-?}"
    local message="$2"
    echo -e "\n${YELLOW}[$step_num/$total_steps] $message${NC}"
}

# Единая функция для успеха
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Единая функция для ошибок
log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Единая функция для предупреждений
log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Единая функция для информации
log_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# ============================================
# ПРОВЕРКИ
# ============================================

# Проверка существования файла
check_file_exists() {
    local file="$1"
    local message="${2:-Файл не найден: $file}"
    
    if [ ! -f "$file" ]; then
        log_error "$message"
        return 1
    fi
    return 0
}

# Проверка существования директории
check_dir_exists() {
    local dir="$1"
    local message="${2:-Директория не найдена: $dir}"
    
    if [ ! -d "$dir" ]; then
        log_error "$message"
        return 1
    fi
    return 0
}

# Проверка обязательных переменных
check_required_vars() {
    local missing=()
    
    for var in "$@"; do
        if [ -z "${!var}" ]; then
            missing+=("$var")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Не заданы обязательные переменные: ${missing[*]}"
        return 1
    fi
    return 0
}

# ============================================
# РАБОТА С ФАЙЛАМИ
# ============================================

# Получение длительности аудио в секундах
get_audio_duration() {
    local audio_file="$1"
    
    if [ ! -f "$audio_file" ]; then
        echo "0"
        return 1
    fi
    
    python utils/audio_duration.py "$audio_file" --format seconds 2>/dev/null
}

# Ожидание появления файла (с таймаутом)
wait_for_file() {
    local file="$1"
    local timeout="${2:-300}"  # 5 минут по умолчанию
    local message="${3:-Ожидание файла: $file}"
    
    log_info "$message"
    
    local elapsed=0
    while [ ! -f "$file" ]; do
        if [ $elapsed -ge $timeout ]; then
            log_error "Таймаут ожидания файла: $file"
            return 1
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done
    echo ""
    log_success "Файл найден: $file"
    return 0
}

# Проверка свежести файла (для транскрипции)
is_file_fresh() {
    local file="$1"
    local threshold="${2:-15}"  # секунд
    
    if [ ! -f "$file" ]; then
        return 1
    fi
    
    local now=$(date +%s)
    local file_time=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null)
    local age=$((now - file_time))
    
    if [ "$age" -lt "$threshold" ]; then
        return 0
    fi
    return 1
}

# ============================================
# ИНТЕРАКТИВНОСТЬ
# ============================================

# Вопрос пользователю (да/нет)
ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    
    local default_hint
    if [ "$default" = "y" ]; then
        default_hint="[Y/n]"
    else
        default_hint="[y/N]"
    fi
    
    read -p "$prompt $default_hint: " -r
    local answer="${REPLY:-$default}"
    
    if [[ "$answer" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        return 0
    fi
    return 1
}

# Выбор из списка
ask_select() {
    local prompt="$1"
    shift
    local options=("$@")
    
    echo "$prompt"
    select opt in "${options[@]}"; do
        if [ -n "$opt" ]; then
            echo "$opt"
            return 0
        fi
        log_warning "Неверный выбор. Попробуйте снова."
    done
}

# ============================================
# СТАТИСТИКА
# ============================================

# Подсчёт строк в файле
count_lines() {
    local file="$1"
    if [ -f "$file" ]; then
        wc -l < "$file" | tr -d ' '
    else
        echo "0"
    fi
}

# Подсчёт слов в файле
count_words() {
    local file="$1"
    if [ -f "$file" ]; then
        wc -w < "$file" | tr -d ' '
    else
        echo "0"
    fi
}

# Размер файла в человекочитаемом формате
file_size_human() {
    local file="$1"
    if [ -f "$file" ]; then
        du -h "$file" | cut -f1
    else
        echo "N/A"
    fi
}

# ============================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================

# Вывод информации о пайплайне
print_pipeline_info() {
    log_header "🚀 Пайплайн: $TITLE"
    echo "📂 Директория: $OUTPUT_DIR"
    echo "👤 Автор: ${AUTHOR:-Неизвестный}"
    echo "🌐 Язык: ${LANGUAGE:-ru}"
    echo "🎨 Стиль: ${STYLE:-Реалистичный}"
    
    if [ -n "$MODEL_CHOICE" ]; then
        echo "🤖 Модель: $MODEL_CHOICE"
    fi
    
    if [ -n "$VIDEO_URL" ]; then
        echo "🎬 Видео: $VIDEO_URL"
    fi
}

# Создание директории пайплайна
init_pipeline_dir() {
    local dir="${1:-$OUTPUT_DIR}"
    
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        log_success "Создана директория: $dir"
    fi
}
