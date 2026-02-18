#!/bin/bash

# lib/manim/03_code.sh

manim_step_code_draft() {
    log_step "4" "Генерация кода Manim (Draft)..."

    # 4.1 Генерация Черновика (Visuals)
    if [ ! -f "$MANIM_DRAFT_FILE" ]; then
        echo "🎨 Этап 1: Создание визуального черновика (без таймингов)..."
        python manim_processors/manim_code_generator.py \
            --mode visuals \
            --spec-file "$SPEC_FILE" \
            --script-file "$SCRIPT_FILE" \
            --example-file "$EXAMPLE_FILE" \
            --output "$MANIM_DRAFT_FILE" \
            --model "$MODEL_CHOICE" \
            --config config.env
        
        if [ $? -ne 0 ]; then echo "Ошибка генерации черновика"; exit 1; fi
    else
        echo "✅ Черновик кода (draft) уже существует."
    fi
}

manim_step_compile_draft_loop() {
    # 4.2 Автоматическая компиляция черновика
    if [ ! -f "$MANIM_CODE_FILE" ]; then
        while true; do
            # Извлекаем имя класса сцены
            SCENE_CLASS=$(grep -E "^class.*Scene" "$MANIM_DRAFT_FILE" | head -1 | awk '{print $2}' | sed 's/\(.*\):/\1/')
            if [ -z "$SCENE_CLASS" ]; then
                echo "❌ Не найден класс сцены в $MANIM_DRAFT_FILE"
                exit 1
            fi

            MANIM_FILE_NAME=$(basename "$MANIM_DRAFT_FILE")
            cd "$OUTPUT_DIR" || exit 1

            echo "🔄 Компиляция черновика..."
            if manim render "$MANIM_FILE_NAME" "$SCENE_CLASS" -ql --media_dir "manim_media"; then
                DRAFT_VIDEO=$(find manim_media/videos -name "*.mp4" -type f ! -path "*partial*" | head -1)
                if [ -n "$DRAFT_VIDEO" ]; then
                    echo "✅ Черновик успешно скомпилирован: $DRAFT_VIDEO"
                    if command -v mpv &> /dev/null; then
                        mpv "$DRAFT_VIDEO"
                    else
                        echo "⚠️ mpv не установлен, пропуск воспроизведения."
                    fi
                else
                    echo "⚠️ Видео не найдено после рендеринга."
                    cd - > /dev/null
                    break
                fi
            else
                echo "❌ Ошибка при компиляции Manim."
                cd - > /dev/null
                exit 1
            fi

            cd - > /dev/null

            echo
            read -p "🔁 Хотите перекомпилировать черновик? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                break
            fi
            echo
        done
    fi
}

manim_step_code_sync() {
    # 4.3 Генерация Финального кода (Sync)
    if [ ! -f "$MANIM_CODE_FILE" ]; then
        echo "⏱️  Этап 2: Синхронизация с таймстампами..."
        python manim_processors/manim_code_generator.py \
            --mode sync \
            --input-code-file "$MANIM_DRAFT_FILE" \
            --timestamps-file "$FULL_TIMESTAMPS_PATH" \
            --output "$MANIM_CODE_FILE" \
            --model "$MODEL_CHOICE" \
            --config config.env
            
        if [ $? -ne 0 ]; then echo "Ошибка синхронизации"; exit 1; fi
    else
        echo "✅ Финальный код Manim уже существует."
    fi
}

