#!/bin/bash

# lib/manim/04_render.sh

manim_step_render_final() {
    log_step "5" "Рендеринг финального Manim ($QUALITY)..."
    
    # 1. Параметризация: определяем целевой файл
    local TARGET_VIDEO="${MANIM_VIDEO_FILE:-$OUTPUT_DIR/manim_video.mp4}"
    
    # --- FIX START: Делаем путь абсолютным ---
    # Это нужно, потому что дальше мы делаем cd, и относительный путь сломается.
    if [[ "$TARGET_VIDEO" != /* ]]; then
        TARGET_VIDEO="$PWD/$TARGET_VIDEO"
    fi
    # --- FIX END ---

    if [ ! -f "$TARGET_VIDEO" ]; then
        # Получаем имя класса сцены
        SCENE_CLASS=$(grep -E "^class.*Scene" "$MANIM_CODE_FILE" | head -1 | awk '{print $2}' | sed 's/\(.*\):/\1/')
        MANIM_FILE_NAME=$(basename "$MANIM_CODE_FILE")

        # Настройка качества
        case "$QUALITY" in
            low) QFLAG="-ql";; medium) QFLAG="-qm";; high) QFLAG="-qh";; 4k) QFLAG="-qk";; *) QFLAG="-ql";;
        esac

        # Заходим в папку для рендера
        cd "$OUTPUT_DIR" || exit 1
        
        # Очистка каталога сборки
        rm -Rf manim_media
        
        # Запуск рендера
        # Мы используем || exit 1, чтобы не продолжать при ошибке
        if ! manim render "$MANIM_FILE_NAME" "$SCENE_CLASS" "$QFLAG" --media_dir "manim_media"; then
            echo -e "${RED}❌ Ошибка при финальном рендере Manim${NC}"
            cd - > /dev/null # Возвращаемся назад перед выходом
            exit 1
        fi

        # Поиск результата
        VIDEO_FOUND=$(find manim_media/videos -name "*.mp4" -type f ! -path "*partial*" | head -1)
        
        if [ -f "$VIDEO_FOUND" ]; then
            # Теперь TARGET_VIDEO абсолютный, поэтому копирование сработает из любой папки
            cp "$VIDEO_FOUND" "$TARGET_VIDEO"
            echo "✅ Видео отреендерено и сохранено как: $(basename "$TARGET_VIDEO")"
        else
            echo -e "${RED}❌ Видео не найдено после рендера${NC}"
            cd - > /dev/null
            exit 1
        fi
        
        # Возвращаемся в исходную директорию
        cd - > /dev/null
    else
        echo "✅ $(basename "$TARGET_VIDEO") уже существует."
    fi
}

manim_step_video_sync() {
    log_step "6" "Склейка видео и аудио (FFmpeg)..."
    
    local SOURCE_VIDEO="${MANIM_VIDEO_FILE:-$OUTPUT_DIR/manim_video.mp4}"
    local SOURCE_AUDIO="${AUDIO_FILE:-$OUTPUT_DIR/audio.mp3}"
    local TARGET_FINAL="${OUTPUT_VIDEO_FILE:-$OUTPUT_DIR/video.mp4}"

    # Делаем пути абсолютными на всякий случай, хотя здесь cd не используется
    if [[ "$SOURCE_VIDEO" != /* ]]; then SOURCE_VIDEO="$PWD/$SOURCE_VIDEO"; fi
    if [[ "$TARGET_FINAL" != /* ]]; then TARGET_FINAL="$PWD/$TARGET_FINAL"; fi

    if [ ! -f "$TARGET_FINAL" ]; then
        
        # python скрипт запускается из текущей папки (корня проекта), поэтому пути должны быть валидны оттуда
        # Но так как мы сделали их абсолютными выше, это сработает железобетонно.
        python manim_processors/manim_video_synchronizer.py \
            --pipeline-dir "$OUTPUT_DIR" \
            --timestamps-file "$TIMESTAMPS_FILE" \
            --output "$(basename "$TARGET_FINAL")" \
            --manim-video "$(basename "$SOURCE_VIDEO")" \
            --audio-source "$(basename "$SOURCE_AUDIO")"

        echo "✅ Финальное видео: $TARGET_FINAL"
    else
        echo "✅ $(basename "$TARGET_FINAL") уже существует."
    fi
}

manim_step_render_sync_loop() {
    while true; do
        manim_step_render_final
        manim_step_video_sync
        mpv "$OUTPUT_VIDEO_FILE"
        echo -e "\n${YELLOW}Повторить рендер и синхронизацию? (y/n)${NC}"
        read -p "Выберите (y/n) >> " repeat_render
        if [[ ! "$repeat_render" =~ ^[Yy]$ ]]; then
            break
        fi
        echo "Удаляем файлы... "
        rm "$MANIM_VIDEO_FILE"
        rm "$OUTPUT_VIDEO_FILE"
    done
}


manim_step_hq_rerun() {
    local TARGET_VIDEO="${MANIM_VIDEO_FILE:-$OUTPUT_DIR/manim_video.mp4}"
    local TARGET_FINAL="${OUTPUT_VIDEO_FILE:-$OUTPUT_DIR/video.mp4}"

    # Абсолютные пути для корректного удаления
    if [[ "$TARGET_VIDEO" != /* ]]; then TARGET_VIDEO="$PWD/$TARGET_VIDEO"; fi
    if [[ "$TARGET_FINAL" != /* ]]; then TARGET_FINAL="$PWD/$TARGET_FINAL"; fi

    echo -e "\n${YELLOW}[HQ] Создание финального видео высокого качества?${NC}"
    echo "Это удалит текущие видео и запустит рендер в High Quality."
    read -p "Пропустить? (y/n) >> " skip_final_video
    
    if [[ ! "$skip_final_video" =~ ^[Yy] ]]; then
        echo "♻️  Перезапуск в высоком качестве..."
        
        [ -f "$TARGET_VIDEO" ] && rm "$TARGET_VIDEO"
        [ -f "$TARGET_FINAL" ] && rm "$TARGET_FINAL"
        
        cd "$OUTPUT_DIR" || exit 1
        rm -Rf manim_media
        cd - > /dev/null

        export QUALITY="high"
        
        manim_step_render_final
        manim_step_video_sync
    fi
}


manim_step_add_music() {
    log_step "10" "Добавление фоновой музыки..."
    echo -e "\n${YELLOW} Добавить фоновую музыку?${NC}"
    echo "Это создаст отдельный файл с музыкой, не изменяя исходное видео."
    read -p "Пропустить? (y/n) >> " skip_add_music
    if [[ "$skip_add_music" =~ ^[Yy] ]]; then
        return 0
    fi

    local TARGET_VIDEO="${OUTPUT_VIDEO_FILE:-$OUTPUT_DIR/video.mp4}"
    if [[ "$TARGET_VIDEO" != /* ]]; then TARGET_VIDEO="$PWD/$TARGET_VIDEO"; fi

    if [ ! -f "$TARGET_VIDEO" ]; then
        echo "⚠️ Видео файл не найден: $TARGET_VIDEO"
        return 0
    fi

    MUSIC_FILES=$(find "$OUTPUT_DIR" -maxdepth 1 -name "music_*.mp3" 2>/dev/null | wc -l)
    if [ "$MUSIC_FILES" -eq 0 ]; then
        echo "ℹ️ Файлы music_*.mp3 не найдены"
        return 0
    fi

    echo "🎵 Найдено файлов музыки: $MUSIC_FILES"

    # Спросим offset у пользователя (опционально)
    read -p "На сколько дБ музыка должна быть тише голоса? (по умолчанию 12.5, попробуй 6–8 для громче): " music_offset
    music_offset=${music_offset:-12.5}

    # Запускаем Python-скрипт
    python manim_processors/manim_music_mixer.py \
        --pipeline-dir "$OUTPUT_DIR" \
        --video "$(basename "$TARGET_VIDEO")" \
        --music-offset "$music_offset"

    if [ $? -eq 0 ]; then
        echo "✅ Файл с музыкой создан"
    else
        echo -e "${YELLOW}⚠️ Не удалось добавить музыку${NC}"
    fi
}