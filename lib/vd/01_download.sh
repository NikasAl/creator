#!/bin/bash

vd_step_download() {
    # Если есть внешний транскрипт - скачивание не обязательно (если только нам не нужно видео для нарезки)
    # Но следуя оригинальной логике, если USE_TRANSCRIPT_FILE есть, мы пропускаем этот шаг
    if [ -n "$USE_TRANSCRIPT_FILE" ] && [ -f "$USE_TRANSCRIPT_FILE" ]; then
        echo "⏭️ Использование готового транскрипта: скачивание видео пропущено."
        return 0
    fi

    # Особая проверка для full_original (из оригинала)
    if [ "$FORCE_REDO" = "true" ] && [ -f "$OUTPUT_DIR/full_original_audio.mp3" ]; then
         echo "⏭️ Найдены full_original файлы, используем их как исходник (скачивание пропущено)."
         cp "$OUTPUT_DIR/full_original_audio.mp3" "$OUTPUT_DIR/original_audio.mp3"
         [ -f "$OUTPUT_DIR/full_original_video.mp4" ] && cp "$OUTPUT_DIR/full_original_video.mp4" "$OUTPUT_DIR/original_video.mp4"
         return 0
    fi

    # # Если full файлы есть, и мы не форсируем — тоже пропускаем
    if [ -f "$OUTPUT_DIR/full_original_audio.mp3" ]; then
        echo "⏭️ Найдены full_original файлы. Пропуск скачивания."
        # Восстанавливаем original для работы, если его нет
        # [ ! -f "$OUTPUT_DIR/original_audio.mp3" ] && cp "$OUTPUT_DIR/full_original_audio.mp3" "$OUTPUT_DIR/original_audio.mp3"
        return 0
    fi

    run_step "Шаг 1: Скачивание видео" \
        "$OUTPUT_DIR/original_audio.mp3" \
        python video_processors/video_downloader.py "$VIDEO_URL" --output-dir "$OUTPUT_DIR"
}

vd_step_trim() {
    # Выполняется только если заданы тайминги и нет внешнего транскрипта
    if [ -z "$START_TIME" ] || [ -z "$END_TIME" ] || [ -n "$USE_TRANSCRIPT_FILE" ]; then
        return 0
    fi

    log_header "Шаг 1.1: Обрезка фрагмента ($START_TIME - $END_TIME)"

    # 1. Сохраняем полные версии, если их еще нет
    if [ ! -f "$OUTPUT_DIR/full_original_audio.mp3" ]; then
        if [ -f "$OUTPUT_DIR/original_audio.mp3" ]; then
            mv "$OUTPUT_DIR/original_audio.mp3" "$OUTPUT_DIR/full_original_audio.mp3"
            echo "📦 Аудио сохранено как full_original_audio.mp3"
        fi
        if [ -f "$OUTPUT_DIR/original_video.mp4" ]; then
            mv "$OUTPUT_DIR/original_video.mp4" "$OUTPUT_DIR/full_original_video.mp4"
            echo "📦 Видео сохранено как full_original_video.mp4"
        fi
    fi

    # 2. Режем (если FORCE_REDO или если нет обрезанного файла)
    if [ "$FORCE_REDO" = "true" ] || [ ! -f "$OUTPUT_DIR/original_audio.mp3" ]; then
        echo "✂️ Обрезка аудио..."
        ffmpeg -i "$OUTPUT_DIR/full_original_audio.mp3" -ss "$START_TIME" -to "$END_TIME" -c copy "$OUTPUT_DIR/original_audio.mp3" -y -hide_banner -loglevel error || exit 1
        
        if [ -f "$OUTPUT_DIR/full_original_video.mp4" ]; then
             echo "✂️ Обрезка видео..."
             ffmpeg -i "$OUTPUT_DIR/full_original_video.mp4" -ss "$START_TIME" -to "$END_TIME" -c:v libx264 -c:a aac "$OUTPUT_DIR/original_video.mp4" -y -hide_banner -loglevel error
        fi
        echo "✅ Обрезка завершена"
    else
        echo "⏭️ Фрагмент уже вырезан."
    fi
}

