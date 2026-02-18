#!/bin/bash

# Скрипт для записи аудио с bluetooth устройства или встроенных динамиков в Linux
# Требует: pulseaudio, ffmpeg, parec
# Поддерживает:
# - Запись с bluetooth устройств
# - Запись с встроенных динамиков ноутбука
# - Автоматический выбор устройства

OUTPUT_DIR="./recordings"
mkdir -p "$OUTPUT_DIR"

# Функция для проверки наличия звука
check_audio_playback() {
    local sink_inputs=$(pactl list sink-inputs | grep -c "media.name = \"Playback\"")
    [ "$sink_inputs" -gt 0 ]
}

# Функция для поиска встроенных динамиков
find_speaker_sink() {
    # Ищем встроенные динамики (обычно это не bluetooth устройства)
    local speaker_sink=$(pactl list sinks | grep -E "Name:.*(alsa_output|pci-|usb-)" | grep -v "bluez" | head -1 | cut -d: -f2 | tr -d ' ')
    
    # Если не найдено, берем первое доступное устройство
    if [ -z "$speaker_sink" ]; then
        speaker_sink=$(pactl list sinks | grep "Name:" | head -1 | cut -d: -f2 | tr -d ' ')
    fi
    
    echo "$speaker_sink"
}

# Функция для выбора устройства записи
select_recording_device() {
    echo "Выберите устройство для записи:"
    echo "1) Bluetooth устройство"
    echo "2) Встроенные динамики ноутбука"
    echo "3) Автоматический выбор"
    echo -n "Введите номер (1-3): "
    read choice
    
    case $choice in
        1)
            return 1
            ;;
        2)
            return 2
            ;;
        3)
            return 3
            ;;
        *)
            return 3
            ;;
    esac
}

# Функция для проверки зависимостей
check_dependencies() {
    local missing_deps=()
    
    if ! command -v ffmpeg &> /dev/null; then
        missing_deps+=("ffmpeg")
    fi
    
    if ! command -v pactl &> /dev/null; then
        missing_deps+=("pulseaudio")
    fi
    
    if ! command -v parec &> /dev/null; then
        missing_deps+=("parec (pulseaudio-utils)")
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
    local input_wav="$1"
    local output_mp3="$2"
    local timestamp="$3"
    
    echo "Анализ уровня звука..."
    # Первый проход - анализ звука для нормализации
    ffmpeg -i "$input_wav" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2> /tmp/stats_$timestamp.txt
    
    # Извлекаем параметры нормализации
    local measured_i=$(grep -o '"input_i" : "[^"]*' /tmp/stats_$timestamp.txt | cut -d'"' -f4)
    local measured_tp=$(grep -o '"input_tp" : "[^"]*' /tmp/stats_$timestamp.txt | cut -d'"' -f4)
    local measured_lra=$(grep -o '"input_lra" : "[^"]*' /tmp/stats_$timestamp.txt | cut -d'"' -f4)
    local measured_thresh=$(grep -o '"input_thresh" : "[^"]*' /tmp/stats_$timestamp.txt | cut -d'"' -f4)
    
    echo "Обнаружение участков тишины..."
    # Получаем общую длительность файла
    local total_duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$input_wav")
    
    # Используем более консервативные настройки для обнаружения тишины
    # Более высокий порог шума (-40dB вместо -30dB) и более длительная тишина (1.0с вместо 0.5с)
    local silence_detection=$(ffmpeg -i "$input_wav" -af silencedetect=noise=-40dB:duration=1.0 -f null - 2>&1)
    
    # Определяем точки начала и конца для обрезки
    local trim_start="0"
    local trim_end="$total_duration"
    
    # Анализируем тишину в начале записи
    local silence_starts=$(echo "$silence_detection" | grep -o "silence_start: [0-9.]*" | cut -d: -f2 | tr -d ' ')
    local silence_ends=$(echo "$silence_detection" | grep -o "silence_end: [0-9.]*" | cut -d: -f2 | tr -d ' ')
    
    # Обрезка в начале: ищем первую значительную тишину (более 3 секунд)
    if [ -n "$silence_starts" ]; then
        local first_silence_start=$(echo "$silence_starts" | head -1)
        local first_silence_end=$(echo "$silence_ends" | head -1)
        
        if [ -n "$first_silence_start" ] && [ -n "$first_silence_end" ]; then
            local silence_duration=$(echo "$first_silence_end - $first_silence_start" | bc -l 2>/dev/null || echo "0")
            # Обрезаем только если тишина в начале длится более 3 секунд
            if (( $(echo "$silence_duration > 3" | bc -l 2>/dev/null || echo "0") )); then
                # Оставляем только 1 секунду тишины в начале
                trim_start=$(echo "$first_silence_end - 1" | bc -l 2>/dev/null || echo "1")
            fi
        fi
    fi
    
    # Обрезка в конце: ищем последнюю значительную тишину (более 3 секунд)
    if [ -n "$silence_starts" ]; then
        local last_silence_start=$(echo "$silence_starts" | tail -1)
        local last_silence_end=$(echo "$silence_ends" | tail -1)
        
        if [ -n "$last_silence_start" ] && [ -n "$last_silence_end" ]; then
            local silence_duration=$(echo "$last_silence_end - $last_silence_start" | bc -l 2>/dev/null || echo "0")
            # Обрезаем только если тишина в конце длится более 3 секунд
            if (( $(echo "$silence_duration > 3" | bc -l 2>/dev/null || echo "0") )); then
                # Оставляем только 1 секунду тишины в конце
                trim_end=$(echo "$last_silence_start + 1" | bc -l 2>/dev/null || echo "$last_silence_start")
            fi
        fi
    fi
    
    # Проверяем, что обрезка имеет смысл (минимум 5 секунд аудио)
    local trimmed_duration=$(echo "$trim_end - $trim_start" | bc -l 2>/dev/null || echo "0")
    if (( $(echo "$trimmed_duration < 5" | bc -l 2>/dev/null || echo "0") )); then
        echo "Предупреждение: Обрезка тишины может привести к слишком короткой записи, пропускаем обрезку"
        trim_start="0"
        trim_end="$total_duration"
    fi
    
    # Дополнительная проверка: не обрезаем более 50% от общей длительности
    local max_trim_duration=$(echo "$total_duration * 0.5" | bc -l 2>/dev/null || echo "$total_duration")
    if (( $(echo "$trimmed_duration < $max_trim_duration" | bc -l 2>/dev/null || echo "0") )); then
        echo "Предупреждение: Обрезка слишком агрессивна (остается менее 50% от оригинала), пропускаем обрезку"
        trim_start="0"
        trim_end="$total_duration"
        trimmed_duration="$total_duration"
    fi
    
    echo "Нормализация звука и обрезка тишины..."
    # Применяем нормализацию и обрезку тишины
    ffmpeg -i "$input_wav" \
           -ss "$trim_start" \
           -t "$trimmed_duration" \
           -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=$measured_i:measured_TP=$measured_tp:measured_LRA=$measured_lra:measured_thresh=$measured_thresh:linear=true:print_format=summary" \
           -codec:a libmp3lame -qscale:a 2 \
           "$output_mp3" 2>/dev/null
    
    # Удаляем временные файлы
    rm -f "/tmp/stats_$timestamp.txt"
    
    # Выводим информацию об обрезке
    if [ "$trim_start" != "0" ] || [ "$trim_end" != "$total_duration" ]; then
        echo "Обрезка тишины: начало с ${trim_start}с, конец до ${trim_end}с"
        echo "Исходная длительность: ${total_duration}с, итоговая: ${trimmed_duration}с"
        local saved_time=$(echo "$total_duration - $trimmed_duration" | bc -l 2>/dev/null || echo "0")
        echo "Сэкономлено времени: ${saved_time}с"
    else
        echo "Обрезка тишины не применена (тишина слишком короткая или отсутствует)"
    fi
}

# Функция записи с динамиков
record_speakers() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local output_file="$OUTPUT_DIR/speakers_${timestamp}.mp3"
    local temp_wav="/tmp/temp_audio_${timestamp}.wav"
    
    echo "Поиск встроенных динамиков..."
    
    # Находим встроенные динамики
    local speaker_sink=$(find_speaker_sink)
    
    if [ -z "$speaker_sink" ]; then
        echo "Встроенные динамики не найдены"
        echo "Проверьте, что звуковая система работает корректно"
        return 1
    fi
    
    local speaker_monitor="${speaker_sink}.monitor"
    local device_description=$(pactl list sinks | grep -A1 "Name: $speaker_sink" | grep "Description" | cut -d: -f2 | tr -d ' ')
    
    echo "Найдено устройство: $device_description"
    echo "Используется источник записи: $speaker_monitor"
    echo "Выходной файл: $output_file"
    
    # Настраиваем громкость монитора
    echo "Настройка уровня записи..."
    pactl set-source-volume "$speaker_monitor" 100%
    
    echo "Ожидание начала воспроизведения звука..."
    local waiting_dots=""
    local audio_detected=false
    
    # Запускаем процесс анимации ожидания
    (
        while ! $audio_detected; do
            waiting_dots="${waiting_dots}."
            if [ ${#waiting_dots} -gt 3 ]; then
                waiting_dots="."
            fi
            echo -ne "\rОжидание звука${waiting_dots}   "
            sleep 0.5
        done
    ) &
    local animation_pid=$!
    
    # Ждем появления звука
    while ! check_audio_playback; do
        sleep 0.1
        if read -t 0.1 -N 1; then
            echo -e "\nПрервать ожидание? (y/n): "
            read -n 1 answer
            if [ "$answer" = "y" ]; then
                kill $animation_pid 2>/dev/null
                wait $animation_pid 2>/dev/null
                echo -e "\nОжидание прервано"
                return 1
            fi
        fi
    done
    
    # Звук обнаружен, останавливаем анимацию
    audio_detected=true
    kill $animation_pid 2>/dev/null
    wait $animation_pid 2>/dev/null
    echo -e "\nЗвук обнаружен! Начинаем запись... (нажмите Enter для остановки)"
    
    # Запись с помощью parec в WAV
    parec --channels=2 --rate=44100 --format=s16le \
          --device="$speaker_monitor" \
          --volume=150000 \
          --file-format=wav \
          "$temp_wav" &
    local record_pid=$!
    
    # Показываем время записи
    local start_time=$(date +%s)
    local duration=0
    
    (
        while kill -0 $record_pid 2>/dev/null; do
            current_time=$(date +%s)
            duration=$((current_time - start_time))
            echo -ne "\rДлительность записи: ${duration} сек"
            sleep 1
        done
    ) &
    local display_pid=$!
    
    # Ждем нажатия Enter
    read
    
    # Останавливаем запись и отображение времени
    kill $record_pid 2>/dev/null
    kill $display_pid 2>/dev/null
    wait $record_pid 2>/dev/null
    wait $display_pid 2>/dev/null
    echo -e "\nЗапись остановлена"
    
    # Постобработка аудио: нормализация и обрезка тишины
    postprocess_audio "$temp_wav" "$output_file" "$timestamp"
    
    # Удаляем временный WAV файл
    rm -f "$temp_wav"
    
    if [ -f "$output_file" ]; then
        local filesize=$(du -h "$output_file" | cut -f1)
        echo "Запись завершена: $output_file"
        echo "Размер файла: $filesize"
        echo "Длительность записи: ${duration} сек"
        
        # Проверяем размер файла
        local size_in_bytes=$(stat -c %s "$output_file")
        if [ "$size_in_bytes" -lt 1024 ]; then
            echo "Предупреждение: Файл записи слишком маленький, возможно, звук не был записан"
            echo "Проверьте, что на устройство передается звук"
        fi
        
        # Предлагаем прослушать запись
        echo "Хотите проверить запись? (y/n): "
        read check_playback
        if [ "$check_playback" = "y" ]; then
            echo "Воспроизведение записи..."
            ffplay -nodisp -autoexit "$output_file" 2>/dev/null
        fi
    else
        echo "Ошибка при записи звука"
    fi
}

# Основная функция записи с bluetooth
record_bluetooth() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local output_file="$OUTPUT_DIR/bluetooth_${timestamp}.mp3"
    local temp_wav="/tmp/temp_audio_${timestamp}.wav"
    
    echo "Поиск bluetooth устройства..."
    
    # Находим первое bluetooth устройство
    local bluetooth_sink=$(pactl list sinks | grep -m1 "Name:.*bluez" | cut -d: -f2 | tr -d ' ')
    
    if [ -z "$bluetooth_sink" ]; then
        echo "Bluetooth устройство не найдено"
        echo "Проверьте, что устройство подключено и на него передается звук"
        return 1
    fi
    
    local bluetooth_monitor="${bluetooth_sink}.monitor"
    local device_description=$(pactl list sinks | grep -A1 "Name: $bluetooth_sink" | grep "Description" | cut -d: -f2 | tr -d ' ')
    
    echo "Найдено устройство: $device_description"
    echo "Используется источник записи: $bluetooth_monitor"
    echo "Выходной файл: $output_file"
    
    # Настраиваем громкость монитора
    echo "Настройка уровня записи..."
    pactl set-source-volume "$bluetooth_monitor" 100%
    
    echo "Ожидание начала воспроизведения звука..."
    local waiting_dots=""
    local audio_detected=false
    
    # Запускаем процесс анимации ожидания
    (
        while ! $audio_detected; do
            waiting_dots="${waiting_dots}."
            if [ ${#waiting_dots} -gt 3 ]; then
                waiting_dots="."
            fi
            echo -ne "\rОжидание звука${waiting_dots}   "
            sleep 0.5
        done
    ) &
    local animation_pid=$!
    
    # Ждем появления звука
    while ! check_audio_playback; do
        sleep 0.1
        if read -t 0.1 -N 1; then
            echo -e "\nПрервать ожидание? (y/n): "
            read -n 1 answer
            if [ "$answer" = "y" ]; then
                kill $animation_pid 2>/dev/null
                wait $animation_pid 2>/dev/null
                echo -e "\nОжидание прервано"
                return 1
            fi
        fi
    done
    
    # Звук обнаружен, останавливаем анимацию
    audio_detected=true
    kill $animation_pid 2>/dev/null
    wait $animation_pid 2>/dev/null
    echo -e "\nЗвук обнаружен! Начинаем запись... (нажмите Enter для остановки)"
    
    # Запись с помощью parec в WAV
    parec --channels=2 --rate=44100 --format=s16le \
          --device="$bluetooth_monitor" \
          --volume=150000 \
          --file-format=wav \
          "$temp_wav" &
    local record_pid=$!
    
    # Показываем время записи
    local start_time=$(date +%s)
    local duration=0
    
    (
        while kill -0 $record_pid 2>/dev/null; do
            current_time=$(date +%s)
            duration=$((current_time - start_time))
            echo -ne "\rДлительность записи: ${duration} сек"
            sleep 1
        done
    ) &
    local display_pid=$!
    
    # Ждем нажатия Enter
    read
    
    # Останавливаем запись и отображение времени
    kill $record_pid 2>/dev/null
    kill $display_pid 2>/dev/null
    wait $record_pid 2>/dev/null
    wait $display_pid 2>/dev/null
    echo -e "\nЗапись остановлена"
    
    # Постобработка аудио: нормализация и обрезка тишины
    postprocess_audio "$temp_wav" "$output_file" "$timestamp"
    
    # Удаляем временный WAV файл
    rm -f "$temp_wav"
    
    if [ -f "$output_file" ]; then
        local filesize=$(du -h "$output_file" | cut -f1)
        echo "Запись завершена: $output_file"
        echo "Размер файла: $filesize"
        echo "Длительность записи: ${duration} сек"
        
        # Проверяем размер файла
        local size_in_bytes=$(stat -c %s "$output_file")
        if [ "$size_in_bytes" -lt 1024 ]; then
            echo "Предупреждение: Файл записи слишком маленький, возможно, звук не был записан"
            echo "Проверьте, что на устройство передается звук"
        fi
        
        # Предлагаем прослушать запись
        echo "Хотите проверить запись? (y/n): "
        read check_playback
        if [ "$check_playback" = "y" ]; then
            echo "Воспроизведение записи..."
            ffplay -nodisp -autoexit "$output_file" 2>/dev/null
        fi
    else
        echo "Ошибка при записи звука"
    fi
}

# Функция автоматического выбора устройства
auto_select_device() {
    # Сначала проверяем bluetooth
    local bluetooth_sink=$(pactl list sinks | grep -m1 "Name:.*bluez" | cut -d: -f2 | tr -d ' ')
    
    if [ -n "$bluetooth_sink" ]; then
        echo "bluetooth"
    else
        echo "speakers"
    fi
}

# Основная функция запуска записи
main() {
    echo "=== Скрипт записи аудио ==="
    echo
    
    # Проверяем зависимости
    check_dependencies
    
    # Выбираем устройство
    select_recording_device
    local device_type=$?
    
    echo
    case $device_type in
        1)
            echo "Запуск записи с bluetooth устройства..."
            record_bluetooth
            ;;
        2)
            echo "Запуск записи с встроенных динамиков..."
            record_speakers
            ;;
        3)
            local auto_device=$(auto_select_device)
            case $auto_device in
                "bluetooth")
                    echo "Автоматически выбран bluetooth..."
                    record_bluetooth
                    ;;
                "speakers")
                    echo "Автоматически выбраны динамики..."
                    record_speakers
                    ;;
            esac
            ;;
        *)
            echo "Неверный выбор, используем автоматический выбор..."
            local auto_device=$(auto_select_device)
            case $auto_device in
                "bluetooth")
                    echo "Автоматически выбран bluetooth..."
                    record_bluetooth
                    ;;
                "speakers")
                    echo "Автоматически выбраны динамики..."
                    record_speakers
                    ;;
            esac
            ;;
    esac
}

# Запускаем основную функцию только если скрипт выполняется напрямую
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi 