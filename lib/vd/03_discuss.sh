#!/bin/bash

vd_step_discussion() {
    run_step "Шаг 4: Создание $MODE" \
        "$OUTPUT_DIR/discussion.txt" \
        python text_processors/video_discussion_processor.py "$OUTPUT_DIR/segments.json" \
            --output "$OUTPUT_DIR/discussion.txt" \
            --mode "$MODE" \
            --title "$TITLE" \
            --author "$AUTHOR" \
            --config config.env \
            --model "$MODEL_CHOICE"
}

vd_step_correction() {
    log_header "Шаг 5: Опциональная корректура"
    read -p "Хотите выполнить корректуру текста? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python text_processors/correction_processor.py "$OUTPUT_DIR/discussion.txt" \
            -o "$OUTPUT_DIR/discussion.txt" \
            --config config.env \
            --export-html \
            --html-title "$TITLE"
        echo "✅ Корректура завершена."
    else
        echo "Пропущено."
    fi
}

vd_step_qa() {
    log_header "Шаг 5.1: Генерация вопросов (Q&A)"

    read -p "Хотите добавить вопросы и ответы? (y/n): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Пропущено."
        return 0
    fi

    local model="$MODEL_CHOICE"
    read -p "Хотите изменить модель на custom? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Модель custom - только печатает промпт"
        model="custom"
    fi

    while true; do
        local q_file="$OUTPUT_DIR/questions.txt"
        local a_file="$OUTPUT_DIR/answers.txt"

        [ ! -f "$q_file" ] && echo "Впишите вопросы сюда..." > "$q_file"

        echo "📝 Редактируем вопросы в $q_file..."
        if command -v subl &> /dev/null; then
            subl -w "$q_file"
        else
            echo "⚠️ Откройте $q_file вручную."
            read -p "Нажмите Enter, когда сохраните вопросы..."
        fi

        if [ -s "$q_file" ]; then
            python text_processors/questions_processor.py \
                --discussion "$OUTPUT_DIR/discussion.txt" \
                --questions "$q_file" \
                --output "$a_file" \
                --config config.env \
                --model "$model"

            # Дописываем в discussion.txt
            echo -e "\n---\n## Ответы на вопросы\n" >> "$OUTPUT_DIR/discussion.txt"
            cat "$a_file" >> "$OUTPUT_DIR/discussion.txt"
            echo "✅ Q&A добавлены в discussion.txt"
        fi

        echo ""
        read -p "Что делать дальше? Повторить Q&A (r), или продолжить (c)? (r/c): " -r
        echo ""
        if [[ ! $REPLY =~ ^[Rr]$ ]]; then
            # Continue to next step
            break
        else
            # Repeat the Q&A step - continue the while loop
            echo "Повторяем шаг Q&A..."
            # Remove the Q&A section from discussion.txt to prevent duplicates
            echo "Отредактирйте или удалите секцию с вопросами, она будет добавлена снова..."
        fi
    done
}