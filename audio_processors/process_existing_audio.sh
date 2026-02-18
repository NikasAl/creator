#!/bin/bash

# Скрипт для постобработки существующих аудио файлов
# Выполняет нормализацию звука и обрезку тишины
# Использование: ./process_existing_audio.sh input_file.mp3 [output_file.mp3]

# Функция для проверки зависимостей
check_dependencies() {
    local missing_deps=()
    
    if ! command -v ffmpeg &> /dev/null; then
        missing_deps+=("ffmpeg")
    fi
    
    if ! command -v ffprobe &> /dev/null; then
        missing_deps+=("ffprobe")
    fi
    
    if ! command -v bc &> /dev/null; then
        missing_deps+=("bc")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "Ошибка: не установлены необходимые зависимости:"
        printf '%s\n' "${missing_deps[@]}"
        echo "Установите их через ваш пакетный менеджер"
        exit 1
    fi
}

# Функция для постобработки аудио: нормализация и обрезка тишины
postprocess_audio() {
    local input_file="$1"
    local output_file="$2"
    local timestamp="$3"
    
    # Создаем временный WAV файл
    local temp_wav="/tmp/process_audio_${timestamp}.wav"
    
    echo "Конвертация в WAV для обработки..."
    ffmpeg -i "$input_file" "$temp_wav" -y 2>/dev/null
    
    if [ ! -f "$temp_wav" ]; then
        echo "Ошибка: Не удалось конвертировать файл в WAV"
        return 1
    fi
    
    echo "Анализ уровня звука..."
    # Первый проход - анализ звука для нормализации
    ffmpeg -i "$temp_wav" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2> /tmp/stats_$timestamp.txt
    
    # Извлекаем параметры нормализации
    local measured_i=$(grep -o '"input_i" : "[^"]*' /tmp/stats_$timestamp.txt | cut -d'"' -f4)
    local measured_tp=$(grep -o '"input_tp" : "[^"]*' /tmp/stats_$timestamp.txt | cut -d'"' -f4)
    local measured_lra=$(grep -o '"input_lra" : "[^"]*' /tmp/stats_$timestamp.txt | cut -d'"' -f4)
    local measured_thresh=$(grep -o '"input_thresh" : "[^"]*' /tmp/stats_$timestamp.txt | cut -d'"' -f4)
    
    echo "Обнаружение участков тишины..."
    # Анализируем тишину в начале и конце записи
    local silence_start=$(ffmpeg -i "$temp_wav" -af silencedetect=noise=-30dB:duration=0.5 -f null - 2>&1 | grep -o "silence_start: [0-9.]*" | head -1 | cut -d: -f2 | tr -d ' ')
    local silence_end=$(ffmpeg -i "$temp_wav" -af silencedetect=noise=-30dB:duration=0.5 -f null - 2>&1 | grep -o "silence_end: [0-9.]*" | tail -1 | cut -d: -f2 | tr -d ' ')
    
    # Получаем общую длительность файла
    local total_duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$temp_wav")
    
    # Определяем точки начала и конца для обрезки
    local trim_start="0"
    local trim_end="$total_duration"
    
    # Если найдена тишина в начале, оставляем максимум 2 секунды
    if [ -n "$silence_start" ]; then
        # Находим конец первой тишины
        local first_silence_end=$(ffmpeg -i "$temp_wav" -af silencedetect=noise=-30dB:duration=0.5 -f null - 2>&1 | grep -o "silence_end: [0-9.]*" | head -1 | cut -d: -f2 | tr -d ' ')
        if [ -n "$first_silence_end" ]; then
            local silence_duration=$(echo "$first_silence_end" | bc -l 2>/dev/null || echo "$first_silence_end")
            if (( $(echo "$silence_duration > 2" | bc -l 2>/dev/null || echo "0") )); then
                trim_start=$(echo "$silence_duration - 2" | bc -l 2>/dev/null || echo "2")
            fi
        fi
    fi
    
    # Если найдена тишина в конце, оставляем максимум 2 секунды
    if [ -n "$silence_end" ]; then
        # Находим начало последней тишины
        local last_silence_start=$(ffmpeg -i "$temp_wav" -af silencedetect=noise=-30dB:duration=0.5 -f null - 2>&1 | grep -o "silence_start: [0-9.]*" | tail -1 | cut -d: -f2 | tr -d ' ')
        if [ -n "$last_silence_start" ]; then
            local silence_duration=$(echo "$total_duration - $last_silence_start" | bc -l 2>/dev/null || echo "0")
            if (( $(echo "$silence_duration > 2" | bc -l 2>/dev/null || echo "0") )); then
                trim_end=$(echo "$last_silence_start + 2" | bc -l 2>/dev/null || echo "$last_silence_start")
            fi
        fi
    fi
    
    # Проверяем, что обрезка имеет смысл (минимум 1 секунда аудио)
    local trimmed_duration=$(echo "$trim_end - $trim_start" | bc -l 2>/dev/null || echo "0")
    if (( $(echo "$trimmed_duration < 1" | bc -l 2>/dev/null || echo "0") )); then
        echo "Предупреждение: Обрезка тишины может привести к слишком короткой записи, пропускаем обрезку"
        trim_start="0"
        trim_end="$total_duration"
        trimmed_duration="$total_duration"
    fi
    
    echo "Нормализация звука и обрезка тишины..."
    # Применяем нормализацию и обрезку тишины
    ffmpeg -i "$temp_wav" \
           -ss "$trim_start" \
           -t "$trimmed_duration" \
           -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=$measured_i:measured_TP=$measured_tp:measured_LRA=$measured_lra:measured_thresh=$measured_thresh:linear=true:print_format=summary" \
           -codec:a libmp3lame -qscale:a 2 \
           "$output_file" 2>/dev/null
    
    # Удаляем временные файлы
    rm -f "$temp_wav" "/tmp/stats_$timestamp.txt"
    
    # Выводим информацию об обрезке
    if [ "$trim_start" != "0" ] || [ "$trim_end" != "$total_duration" ]; then
        echo "Обрезка тишины: начало с ${trim_start}с, конец до ${trim_end}с"
        echo "Исходная длительность: ${total_duration}с, итоговая: ${trimmed_duration}с"
    fi
}

# Функция для генерации имени выходного файла
generate_output_filename() {
    local input_file="$1"
    local base_name=$(basename "$input_file" | sed 's/\.[^.]*$//')
    local extension="${input_file##*.}"
    local dir_name=$(dirname "$input_file")
    
    echo "${dir_name}/${base_name}_processed.${extension}"
}

# Основная функция
main() {
    echo "=== Скрипт постобработки аудио файлов ==="
    echo
    
    # Проверяем зависимости
    check_dependencies
    
    # Проверяем аргументы
    if [ $# -lt 1 ]; then
        echo "Использование: $0 input_file.mp3 [output_file.mp3]"
        echo
        echo "Примеры:"
        echo "  $0 audio.mp3                    # Создаст audio_processed.mp3"
        echo "  $0 audio.mp3 output.mp3         # Создаст output.mp3"
        exit 1
    fi
    
    local input_file="$1"
    local output_file="$2"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    
    # Проверяем существование входного файла
    if [ ! -f "$input_file" ]; then
        echo "Ошибка: Файл '$input_file' не найден!"
        exit 1
    fi
    
    # Генерируем имя выходного файла, если не указано
    if [ -z "$output_file" ]; then
        output_file=$(generate_output_filename "$input_file")
    fi
    
    # Получаем информацию об исходном файле
    local original_duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$input_file")
    local original_size=$(du -h "$input_file" | cut -f1)
    
    echo "Исходный файл: $input_file"
    echo "Выходной файл: $output_file"
    echo "Исходная длительность: ${original_duration} секунд"
    echo "Исходный размер: $original_size"
    echo
    
    # Выполняем постобработку
    postprocess_audio "$input_file" "$output_file" "$timestamp"
    
    # Проверяем результат
    if [ -f "$output_file" ]; then
        local new_duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$output_file")
        local new_size=$(du -h "$output_file" | cut -f1)
        local saved_time=$(echo "$original_duration - $new_duration" | bc -l 2>/dev/null || echo "0")
        
        echo
        echo "=== Результаты обработки ==="
        echo "Исходная длительность: ${original_duration} секунд"
        echo "Новая длительность: ${new_duration} секунд"
        echo "Сэкономлено времени: ${saved_time} секунд"
        echo "Исходный размер: $original_size"
        echo "Новый размер: $new_size"
        echo "Обработанный файл: $output_file"
        
        # Проверяем участки тишины в новом файле
        echo
        echo "=== Анализ тишины в обработанном файле ==="
        echo "Тишина в начале:"
        ffmpeg -i "$output_file" -af silencedetect=noise=-30dB:duration=0.5 -f null - 2>&1 | grep -E "(silence_start|silence_end)" | head -3
        
        echo "Тишина в конце:"
        ffmpeg -i "$output_file" -af silencedetect=noise=-30dB:duration=0.5 -f null - 2>&1 | grep -E "(silence_start|silence_end)" | tail -3
        
    else
        echo "Ошибка: Не удалось создать обработанный файл"
        exit 1
    fi
    
    echo
    echo "Обработка завершена успешно!"
}

# Запускаем основную функцию только если скрипт выполняется напрямую
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
