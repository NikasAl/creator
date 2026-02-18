#!/bin/bash

# lib/manim/02_audio.sh

manim_step_create_audio() {
    log_step "2" "Генерация или загрузка аудио..."

    if [ -f "$AUDIO_FILE" ]; then
        echo "✅ Аудио файл $AUDIO_FILE уже существует."
        return 0
    fi

    echo -e "${YELLOW}🎙️ Аудио файл $AUDIO_FILE не найден. Выберите способ генерации:${NC}"
    echo "1) Silero (локально)"
    echo "2) Sber API (синхронный)"
    echo "3) Sber Async API (асинхронный)"
    echo "4) Alibaba Cloud Qwen TTS"
    echo "5) Ручной режим (ожидание файла)"
    read -p "Введите номер (1-5): " audio_choice

    # Временный файл для генерации аудио
    TEMP_AUDIO="${AUDIO_FILE%.mp3}_temp_audio.wav"

    case $audio_choice in
        1)
            echo -e "${GREEN}Выберите голос Silero:${NC}"
            echo "1) aidar"
            echo "2) baya"
            echo "3) eugene"
            echo "4) kseniya"
            echo "5) xenia"
            read -p "Введите номер голоса (1-5, по умолчанию 1): " voice_choice
            case $voice_choice in
                1|""|aidar) speaker="aidar" ;;
                2|baya) speaker="baya" ;;
                3|eugene) speaker="eugene" ;;
                4|kseniya) speaker="kseniya" ;;
                5|xenia) speaker="xenia" ;;
                *) echo "❌ Неверный выбор голоса. Используем aidar."; speaker="aidar" ;;
            esac
            echo -e "${GREEN}Используем Silero TTS с голосом '$speaker'${NC}"
            python speech_processors/silero.py \
                --input "$TTS_SCRIPT_FILE" \
                --output "$TEMP_AUDIO" \
                --speaker "$speaker"
            ;;
        2)
            echo -e "${GREEN}Выберите голос Sber API:${NC}"
            echo "1) Bys_24000"
            echo "2) May_24000"
            echo "3) Tur_24000"
            echo "4) Nec_24000"
            echo "5) Ost_24000"
            echo "6) Pon_24000"
            echo "7) Kin_24000"
            echo "8) Kma_24000"
            echo "9) Rma_24000"
            echo "10) Nur_24000"
            echo "11) Rnu_24000"
#           Bys_24000 May_24000 Tur_24000 Nec_24000 Ost_24000 Pon_24000 Kin_24000 Kma_24000
#           Rma_24000 Nur_24000 Rnu_24000
            read -p "Введите номер голоса (1-7, по умолчанию 1): " voice_choice
            case $voice_choice in
                1|""|Bys) voice="Bys_24000" ;;
                2|May) voice="May_24000" ;;
                3|Tur) voice="Tur_24000" ;;
                4|Nec) voice="Nec_24000" ;;
                5|Ost) voice="Ost_24000" ;;
                6|Pon) voice="Pon_24000" ;;
                7|Kin) voice="Kin_24000" ;;
                8|Kma) voice="Kma_24000" ;;
                9|Rma) voice="Rma_24000" ;;
                10|Nur) voice="Nur_24000" ;;
                11|Rnu) voice="Rnu_24000" ;;
                *) echo "❌ Неверный выбор голоса. Используем Bys_24000."; voice="Bys_24000" ;;
            esac
            echo -e "${GREEN}Используем Sber API с голосом '$voice'${NC}"
            python speech_processors/sber_api_synth.py \
                "$TTS_SCRIPT_FILE" \
                --voice "$voice" \
                --output "$TEMP_AUDIO"
            ;;
        3)
            echo -e "${GREEN}Выберите голос Sber Async API:${NC}"
            echo "1) Bys_24000"
            echo "2) May_24000"
            echo "3) Ost_24000"
            echo "4) Zah_24000"
            echo "5) lexcy_24000"
            echo "6) natasha_24000"
            echo "7) rachel_24000"
            read -p "Введите номер голоса (1-7, по умолчанию 1): " voice_choice
            case $voice_choice in
                1|""|Bys) voice="Bys_24000" ;;
                2|May) voice="May_24000" ;;
                3|Ost) voice="Ost_24000" ;;
                4|Zah) voice="Zah_24000" ;;
                5|lexcy) voice="lexcy_24000" ;;
                6|natasha) voice="natasha_24000" ;;
                7|rachel) voice="rachel_24000" ;;
                *) echo "❌ Неверный выбор голоса. Используем Bys_24000."; voice="Bys_24000" ;;
            esac
            echo -e "${GREEN}Используем Sber Async API с голосом '$voice'${NC}"
            python speech_processors/sber_synth_async_api.py \
                "$TTS_SCRIPT_FILE" \
                --voice "$voice" \
                --output "$TEMP_AUDIO"
            ;;
        4)
            echo -e "${GREEN}Выберите голос Alibaba Cloud Qwen TTS:${NC}"
            echo "1) Cherry"
            echo "2) Serena"
            echo "3) Ethan"
            echo "4) Chelsie"
            echo "5) Momo"
            echo "6) Kai"
            echo "7) Maia"
            echo "8) Nofish"
            echo "9) Ryan"
            echo "10) Katerina"
            echo "11) Ebona"
            echo "12) Sonrisa"
            read -p "Введите номер голоса (1-5, по умолчанию 1): " voice_choice
            case $voice_choice in
                1|""|Cherry) voice="Cherry" ;;
                2|Serena) voice="Serena" ;;
                3|Ethan) voice="Ethan" ;;
                4|Chelsie) voice="Chelsie" ;;
                5|Momo) voice="Momo" ;;
                6|Kai) voice="Kai" ;;
                7|Maia) voice="Maia" ;;
                8|Nofish) voice="Nofish" ;;
                9|Ryan) voice="Ryan" ;;
                10|Katerina) voice="Katerina" ;;
                11|Ebona) voice="Ebona" ;;
                12|Sonrisa) voice="Sonrisa" ;;
                *) echo "❌ Неверный выбор голоса. Используем Cherry."; voice="Cherry" ;;
            esac
            echo -e "${GREEN}Используем Alibaba Cloud Qwen TTS с голосом '$voice'${NC}"
            python speech_processors/alibaba_tts.py \
                "$TTS_SCRIPT_FILE" \
                --voice "$voice" \
                --language "Auto" \
                --output "$TEMP_AUDIO"
            ;;
        5)
            echo -e "${YELLOW}Ручной режим: ожидание $AUDIO_FILE${NC}"
            echo "🎙️ Пожалуйста, озвучьте текст из файла: $TTS_SCRIPT_FILE"
            echo "💾 Сохраните результат как $AUDIO_FILE"
            read -p "Нажмите Enter, когда файл будет готов..."
            if [ ! -f "$AUDIO_FILE" ]; then
                echo "❌ Файл $AUDIO_FILE не найден. Выход."
                exit 1
            fi
            return 0
            ;;
        *)
            echo "❌ Неверный выбор. Выход."
            exit 1
            ;;
    esac

    # Проверяем, создан ли временный файл
    if [ ! -f "$TEMP_AUDIO" ]; then
        echo "❌ Ошибка: временный аудиофайл $TEMP_AUDIO не был создан."
        exit 1
    fi

    # Нормализуем громкость и конвертируем в mp3
    echo "🔄 Нормализуем громкость и конвертируем аудио в mp3 с помощью ffmpeg..."
    if ffmpeg -i "$TEMP_AUDIO" -af "loudnorm=I=-14:LRA=11:TP=-1.5" -vn -ar 48000 -ac 1 -b:a 128k -y "$AUDIO_FILE" >/dev/null 2>&1; then
        rm "$TEMP_AUDIO"
        echo "✅ Аудио успешно нормализовано и сконвертировано в mp3."
    else
        echo "❌ Ошибка при обработке аудио. Убедитесь, что ffmpeg установлен."
        rm -f "$TEMP_AUDIO"
        exit 1
    fi
}

manim_step_transcribe() {
    log_step "3" "Транскрибация..."
    if [ ! -f "$FULL_TIMESTAMPS_PATH" ]; then
        python video_processors/sentence_transcriber.py \
            --audio "$AUDIO_FILE" \
            --output-dir "$OUTPUT_DIR" \
            --json-filename "$TIMESTAMPS_FILE" \
            --language "$LANGUAGE" \
            --config config.env
    else
        echo "✅ Таймстампы существуют."
    fi
}
