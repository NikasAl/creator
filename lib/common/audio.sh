#!/bin/bash

# lib/common/audio.sh
# Общие функции для работы с аудио
# Устраняет кросс-зависимости между lib/manim/02_audio.sh и lib/vd/05_video.sh

# Подключаем общие утилиты
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/tts.sh"

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

# Дефолтные пути
AUDIO_FILE="${AUDIO_FILE:-$OUTPUT_DIR/audio.mp3}"
TTS_SCRIPT_FILE="${TTS_SCRIPT_FILE:-$OUTPUT_DIR/tts_text.txt}"

# ============================================
# ГЕНЕРАЦИЯ АУДИО
# ============================================

# Универсальный шаг создания аудио
# Автоматически выбирает TTS движок или ждёт ручного ввода
common_step_create_audio() {
    local tts_file="${1:-$TTS_SCRIPT_FILE}"
    local audio_file="${2:-$AUDIO_FILE}"
    local language="${LANGUAGE:-ru}"

    log_step "?" "Генерация или загрузка аудио..."

    if [ -f "$audio_file" ]; then
        log_success "Аудио файл уже существует: $audio_file"
        return 0
    fi

    echo -e "${YELLOW}🎙️ Аудио файл не найден. Выберите способ генерации:${NC}"
    echo "1) Silero (локально)"
    echo "2) Sber API (синхронный)"
    echo "3) Sber Async API (асинхронный)"
    echo "4) Alibaba Cloud Qwen TTS"
    echo "5) Ручной режим (ожидание файла)"
    read -p "Введите номер (1-5): " audio_choice

    # Временный файл для генерации аудио
    local temp_audio="${audio_file%.mp3}_temp_audio.wav"

    case $audio_choice in
        1)
            _select_silero_voice
            log_info "Используем Silero TTS с голосом '$voice'"
            python speech_processors/silero.py \
                --input "$tts_file" \
                --output "$temp_audio" \
                --speaker "$voice"
            ;;
        2)
            _select_sber_voice
            log_info "Используем Sber API с голосом '$voice'"
            python speech_processors/sber_api_synth.py \
                "$tts_file" \
                --voice "$voice" \
                --output "$temp_audio"
            ;;
        3)
            _select_sber_async_voice
            log_info "Используем Sber Async API с голосом '$voice'"
            python speech_processors/sber_synth_async_api.py \
                "$tts_file" \
                --voice "$voice" \
                --output "$temp_audio"
            ;;
        4)
            _select_alibaba_voice
            log_info "Используем Alibaba Cloud Qwen TTS с голосом '$voice'"
            python speech_processors/alibaba_tts.py \
                "$tts_file" \
                --voice "$voice" \
                --language "Auto" \
                --output "$temp_audio"
            ;;
        5)
            log_warning "Ручной режим: ожидание $audio_file"
            echo "🎙️ Пожалуйста, озвучьте текст из файла: $tts_file"
            echo "💾 Сохраните результат как $audio_file"
            read -p "Нажмите Enter, когда файл будет готов..."
            if [ ! -f "$audio_file" ]; then
                log_error "Файл $audio_file не найден"
                return 1
            fi
            return 0
            ;;
        *)
            log_error "Неверный выбор"
            return 1
            ;;
    esac

    # Проверяем, создан ли временный файл
    if [ ! -f "$temp_audio" ]; then
        log_error "Временный аудиофайл не был создан"
        return 1
    fi

    # Нормализуем громкость и конвертируем в mp3
    log_info "Нормализация и конвертация аудио в mp3..."
    if ffmpeg -i "$temp_audio" -af "loudnorm=I=-14:LRA=11:TP=-1.5" -vn -ar 48000 -ac 1 -b:a 128k -y "$audio_file" >/dev/null 2>&1; then
        rm "$temp_audio"
        log_success "Аудио успешно нормализовано и сконвертировано"
    else
        log_error "Ошибка при обработке аудио. Убедитесь, что ffmpeg установлен."
        rm -f "$temp_audio"
        return 1
    fi
}

# ============================================
# ВЫБОР ГОЛОСОВ (внутренние функции)
# ============================================

_select_silero_voice() {
    echo -e "${GREEN}Выберите голос Silero:${NC}"
    echo "1) aidar  2) baya  3) eugene  4) kseniya  5) xenia"
    read -p "Номер (1-5, по умолчанию 1): " voice_choice
    case $voice_choice in
        2|baya) voice="baya" ;;
        3|eugene) voice="eugene" ;;
        4|kseniya) voice="kseniya" ;;
        5|xenia) voice="xenia" ;;
        *) voice="aidar" ;;
    esac
}

_select_sber_voice() {
    echo -e "${GREEN}Выберите голос Sber API:${NC}"
    echo "1) Bys_24000  2) May_24000  3) Tur_24000  4) Nec_24000"
    echo "5) Ost_24000  6) Pon_24000  7) Kin_24000"
    read -p "Номер (1-7, по умолчанию 1): " voice_choice
    case $voice_choice in
        2|May) voice="May_24000" ;;
        3|Tur) voice="Tur_24000" ;;
        4|Nec) voice="Nec_24000" ;;
        5|Ost) voice="Ost_24000" ;;
        6|Pon) voice="Pon_24000" ;;
        7|Kin) voice="Kin_24000" ;;
        *) voice="Bys_24000" ;;
    esac
}

_select_sber_async_voice() {
    echo -e "${GREEN}Выберите голос Sber Async API:${NC}"
    echo "1) Bys_24000  2) May_24000  3) Ost_24000  4) Zah_24000"
    echo "5) lexcy_24000  6) natasha_24000  7) rachel_24000"
    read -p "Номер (1-7, по умолчанию 1): " voice_choice
    case $voice_choice in
        2|May) voice="May_24000" ;;
        3|Ost) voice="Ost_24000" ;;
        4|Zah) voice="Zah_24000" ;;
        5|lexcy) voice="lexcy_24000" ;;
        6|natasha) voice="natasha_24000" ;;
        7|rachel) voice="rachel_24000" ;;
        *) voice="Bys_24000" ;;
    esac
}

_select_alibaba_voice() {
    echo -e "${GREEN}Выберите голос Alibaba Cloud Qwen TTS:${NC}"
    echo "1) Cherry  2) Serena  3) Ethan  4) Chelsie  5) Momo"
    echo "6) Kai  7) Maia  8) Nofish  9) Ryan  10) Katerina"
    read -p "Номер (1-10, по умолчанию 1): " voice_choice
    case $voice_choice in
        2|Serena) voice="Serena" ;;
        3|Ethan) voice="Ethan" ;;
        4|Chelsie) voice="Chelsie" ;;
        5|Momo) voice="Momo" ;;
        6|Kai) voice="Kai" ;;
        7|Maia) voice="Maia" ;;
        8|Nofish) voice="Nofish" ;;
        9|Ryan) voice="Ryan" ;;
        10|Katerina) voice="Katerina" ;;
        *) voice="Cherry" ;;
    esac
}

# ============================================
# ТРАНСКРИБАЦИЯ
# ============================================

# Универсальный шаг транскрибации
common_step_transcribe() {
    local audio_file="${1:-$AUDIO_FILE}"
    local output_dir="${2:-$OUTPUT_DIR}"
    local language="${LANGUAGE:-ru}"
    local timestamps_file="${3:-sentence_timestamps.json}"

    log_step "?" "Транскрибация..."

    local timestamps_path="$output_dir/$timestamps_file"

    if [ -f "$timestamps_path" ]; then
        log_success "Таймстампы существуют: $timestamps_path"
        return 0
    fi

    python video_processors/sentence_transcriber.py \
        --audio "$audio_file" \
        --output-dir "$output_dir" \
        --json-filename "$timestamps_file" \
        --language "$language" \
        --config config.env
}

# ============================================
# ДОБАВЛЕНИЕ МУЗЫКИ
# ============================================

# Универсальный шаг добавления фоновой музыки
common_step_add_music() {
    local output_dir="${1:-$OUTPUT_DIR}"
    local video_file="${2:-$output_dir/video.mp4}"

    log_step "?" "Добавление фоновой музыки..."

    echo -e "\n${YELLOW}Добавить фоновую музыку?${NC}"
    echo "Это создаст отдельный файл с музыкой, не изменяя исходное видео."
    read -p "Пропустить? (y/n) >> " skip_add_music
    if [[ "$skip_add_music" =~ ^[Yy] ]]; then
        return 0
    fi

    if [ ! -f "$video_file" ]; then
        log_warning "Видео файл не найден: $video_file"
        return 0
    fi

    # Спросим offset у пользователя
    read -p "На сколько дБ музыка должна быть тише голоса? (по умолчанию 12.5): " music_offset
    music_offset=${music_offset:-12.5}

    python manim_processors/manim_music_mixer.py \
        --pipeline-dir "$output_dir" \
        --video "$(basename "$video_file")" \
        --music-offset "$music_offset"

    if [ $? -eq 0 ]; then
        log_success "Файл с музыкой создан"
    else
        log_warning "Не удалось добавить музыку"
    fi
}
