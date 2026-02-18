#!/bin/bash

# Интерактивный скрипт для создания конфигурационного файла
# Использование: source setup.sh или ./setup.sh

setup_vd_config() {
    local config_file="${1:-config.conf}"
    local base_dir_name
    local title
    
    echo "=== Создание конфигурации для видео-пайплайна ==="
    echo "Этот скрипт поможет вам создать конфигурационный файл для обработки видео."
    echo
    
    # Запрашиваем основные параметры
    read -p "Введите название пайплайна (например, VideoDiscussion_Example): " base_dir_name
    
    if [[ -z "$base_dir_name" ]]; then
        echo "Ошибка: название пайплайна не может быть пустым"
        return 1
    fi
    
    local base_dir="pipelines_vd/$base_dir_name"
    
    read -p "Введите заголовок видео (по умолчанию: Пример видео для анализа): " title
    title="${title:-Пример видео для анализа}"
    
    # Нормализуем название файла: удаляем недопустимые символы и заменяем пробелы на подчеркивания
    local filename_safe_title=$(echo "$title" | sed 's/[^a-zA-Z0-9а-яА-Я ]//g' | sed 's/ /_/g')
    config_file="configs/vd/${filename_safe_title}.conf"
    
    read -p "Введите автора (по умолчанию: Автор канала): " author
    author="${author:-Автор канала}"
    
    read -p "Введите язык (по умолчанию: ru): " language
    language="${language:-ru}"
    
    read -p "Введите режим (summary/discussion, по умолчанию: summary): " mode
    mode="${mode:-summary}"
    
    read -p "Введите количество сегментов (по умолчанию: 10): " segments_count
    segments_count="${segments_count:-10}"
    
    read -p "Введите стиль визуализации (по умолчанию: Реалистичный): " style
    style="${style:-Реалистичный}"
    
    read -p "Введите эпоху (по умолчанию: 21 век): " era
    era="${era:-21 век}"
    
    read -p "Введите регион (по умолчанию: Россия): " region
    region="${region:-Россия}"
    
    read -p "Введите жанр (по умолчанию: Образовательное видео): " genre
    genre="${genre:-Образовательное видео}"
    
    read -p "Введите сеттинг (по умолчанию: Современная обстановка.): " setting
    setting="${setting:-Современная обстановка.}"
    
    read -p "Введите продолжительность иллюстрации в секундах (по умолчанию: 8): " seconds_per_illustration
    seconds_per_illustration="${seconds_per_illustration:-8}"
    
    # Спрашиваем о готовом тексте
    echo
    echo "У вас есть готовый текст транскрипции?"
    select use_transcript in "Да" "Нет"; do
        case $use_transcript in
            Да ) 
                local transcript_available="true"
                break
                ;;
            Нет ) 
                local transcript_available="false"
                break
                ;;
        esac
    done
    
    # Создаем директорию
    mkdir -p "$base_dir"

    # Создаем директорию для конфигов, если ее нет
    mkdir -p "configs/vd"
    
    if [[ "$transcript_available" == "true" ]]; then
        local transcript_file="$base_dir/transcript.txt"
        # Создаем файл для транскрипции
        > "$transcript_file"
        
        echo "Открываем файл транскрипции в редакторе: $transcript_file"
        echo "Пожалуйста, введите текст транскрипции в открывшемся редакторе."
        echo "После завершения редактирования сохраните файл и закройте редактор."
        
        # Открываем файл в редакторе subl и ждем его закрытия
        subl -w "$transcript_file"
        
        # Проверяем, что файл не пустой
        if [[ ! -s "$transcript_file" ]]; then
            echo "Предупреждение: файл транскрипции пустой. Продолжение с пустым текстом."
        fi
        
        # Создаем конфиг без VIDEO_URL, но с USE_TRANSCRIPT_FILE
        cat > "$config_file" << EOF
# Конфигурация для обработки видео с созданием пересказа или обсуждения
BASE_DIR="$base_dir"
VIDEO_URL="none"
TITLE="$title"
AUTHOR="$author"
LANGUAGE="$language"
MODE="$mode"
SEGMENTS_COUNT="$segments_count"
STYLE="$style"
ERA="$era"
REGION="$region"
GENRE="$genre"
SETTING="$setting"
SECONDS_PER_ILLUSTRATION="$seconds_per_illustration"
USE_TRANSCRIPT_FILE="$base_dir/transcript.txt"

# Необязательные параметры по умолчанию
USE_ORIGINAL_VIDEO="false"
RESUME_MODE="true"
FORCE_REDO="false"

# Значения из example.conf
MAX_TOKENS="6000"
EOF
    
    else
        local video_url=""
        read -p "Введите URL видео (или оставьте пустым для ручного ввода): " video_url
        video_url=${video_url:-""}

        if [ -n "$video_url" ]; then
            echo "Используем видео: $video_url"
            read -p "Задать временные границы видео (START_TIME и END_TIME)? (y/n): " USE_TIMING
            if [[ "$USE_TIMING" == "y" || "$USE_TIMING" == "Y" ]]; then
                read -p "Введите начальное время (в формате ЧЧ:ММ:СС, по умолчанию 00:00:00): " START_TIME_INPUT
                START_TIME=${START_TIME_INPUT:-"00:00:00"}
                read -p "Введите конечное время (в формате ЧЧ:ММ:СС, по умолчанию до конца): " END_TIME_INPUT
                END_TIME=${END_TIME_INPUT:-""}
            fi
        else
            echo "Видео не задано. Будет использован только аудиофайл."
            video_url="none"
        fi
        
        # Создаем конфиг с VIDEO_URL
        cat > "$config_file" << EOF
# Конфигурация для обработки видео с созданием пересказа или обсуждения
VIDEO_URL="$video_url"
BASE_DIR="$base_dir"
TITLE="$title"
AUTHOR="$author"
LANGUAGE="$language"
MODE="$mode"
SEGMENTS_COUNT="$segments_count"
STYLE="$style"
ERA="$era"
REGION="$region"
GENRE="$genre"
SETTING="$setting"
SECONDS_PER_ILLUSTRATION="$seconds_per_illustration"

# Необязательные параметры по умолчанию
USE_ORIGINAL_VIDEO="false"
RESUME_MODE="true"
FORCE_REDO="false"

# Значения из example.conf
MAX_TOKENS="6000"
EOF

        # Добавляем временные метки, если они были заданы
        if [[ -n "$START_TIME" ]]; then
            echo "START_TIME=\"$START_TIME\"" >> "$config_file"
        fi
        
        if [[ -n "$END_TIME" ]]; then
            echo "END_TIME=\"$END_TIME\"" >> "$config_file"
        fi
    fi
    
    echo
    echo "Конфигурационный файл создан: $config_file"
    echo "Базовая директория: $base_dir"
    
    if [[ "$transcript_available" == "true" ]]; then
        echo "Текст транскрипции сохранен в: $base_dir/transcript.txt"
    fi
    
    echo "Пайплайн готов к запуску!"
    echo "Используйте: ./process_vd.sh $config_file"
    
    # Возвращаем путь к конфигурационному файлу в качестве результата
    echo "$config_file"
}

# Если скрипт запущен напрямую, а не sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    setup_vd_config "${1:-config.conf}"
fi