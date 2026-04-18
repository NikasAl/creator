#!/bin/bash
# process_poetry_manim.sh
# Генератор видеоклипов на основе Manim и AI Director

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "Конфигурационный файл не указан. Запускаем интерактивное создание..."
    echo ""
    rm -f /tmp/.last_poetry_config
    ./setup_poetry_manim_pipeline.sh

    if [ -f /tmp/.last_poetry_config ]; then
        CONFIG_FILE=$(cat /tmp/.last_poetry_config)
        rm -f /tmp/.last_poetry_config
        echo ""
        echo "📎 Используем созданный конфиг: $CONFIG_FILE"
    else
        echo "❌ Не удалось получить конфигурационный файл после настройки"
        exit 1
    fi
else
    CONFIG_FILE="$1"
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "❌ Файл конфигурации не найден: $CONFIG_FILE"
        exit 1
    fi
fi

source "lib/manim/utils.sh"
source "lib/manim/05_extra.sh"
source "$CONFIG_FILE"

# Пути
BASE_DIR="${BASE_DIR:-.}"
OUTPUT_DIR="$BASE_DIR"
INPUT_FILE="$BASE_DIR/${INPUT_FILE:-song.txt}"
AUDIO_FILE="$BASE_DIR/${AUDIO_FILE:-audio.mp3}"
TIMESTAMPS_FILE="$OUTPUT_DIR/sentence_timestamps.json"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/images"

echo "🎭 Обработка через Manim Poetry: $TITLE"
echo "======================================"

# 1. Текст и Аудио
if [ ! -f "$AUDIO_FILE" ]; then
    echo "❌ Нет аудио файла: $AUDIO_FILE. Положите файл и запустите снова."
    exit 1
fi

# 2. Транскрибация (Тайминги)
echo ""
if [ ! -f "$TIMESTAMPS_FILE" ]; then
    echo "🎤 Транскрибация аудио..."
    python video_processors/sentence_transcriber.py \
        --audio "$AUDIO_FILE" \
        --output-dir "$OUTPUT_DIR" \
        --json-filename "sentence_timestamps.json" \
        --language "ru" \
        --hint-file "$INPUT_FILE"
else
    echo "✅ Таймстампы найдены."
fi

# === ЭТАП 2.5: Коррекция ошибок транскрибации ===
if [ -f "$INPUT_FILE" ] && [ -f "$TIMESTAMPS_FILE" ]; then
    NOW=$(date +%s)
    FILE_TIME=$(stat -c %Y "$TIMESTAMPS_FILE")
    AGE=$((NOW - FILE_TIME))
    THRESHOLD=5
    
    if [ "$AGE" -lt "$THRESHOLD" ]; then
        echo ""
        echo "🆕 Файл транскрипции свежий (создан $AGE сек назад)."
        echo "🔧 Запуск корректора текста (LLM)..."
        python text_processors/transcription_corrector.py \
            --json "$TIMESTAMPS_FILE" \
            --reference "$INPUT_FILE"
    else
        echo ""
        echo "⏳ Файл транскрипции старый. Пропускаем коррекцию."
    fi
fi
# ======================================================================

# 3. AI Режиссер (Director Agent)
echo ""
echo "🎬 Запуск AI Режиссера..."

# Функция для запуска режиссера с учетом стиля
run_director() {
    python text_processors/director_agent.py \
        --text "$INPUT_FILE" \
        --timestamps "$TIMESTAMPS_FILE" \
        --output-dir "$OUTPUT_DIR" \
        --style "$STYLE" \
        --era "$ERA" \
        --region "$REGION" \
        --genre "$GENRE" \
        --setting "$SETTING"
}

if [ ! -f "$OUTPUT_DIR/screenplay.json" ]; then
    run_director
else
    echo "✅ Сценарий (screenplay.json) уже существует."
    read -p "Перегенерировать сценарий? (y/n): " regen_script
    if [[ "$regen_script" =~ ^[Yy] ]]; then
         run_director
    fi
fi

# 4. Циклическая генерация и проверка иллюстраций
echo ""
echo "🎨 Запуск циклической генерации и проверки иллюстраций..."

while true; do
    echo ""
    echo "🔄 Проверка и генерация иллюстраций (шаг: просмотр/перегенерация)..."
    python video_processors/illustration_review_cli.py \
        --pipeline-dir "$OUTPUT_DIR" \
        --width 1366 --height 768 \
        --steps 4

    echo ""
    echo "👀 Проверьте изображения в: $OUTPUT_DIR/images и удалите плохие"
    feh $OUTPUT_DIR/images
    read -p "Все изображения устраивают? (y/n): " images_ok
    if [[ "$images_ok" =~ ^[Yy]$ ]]; then
        echo "✅ Все иллюстрации подтверждены. Переход к сборке видео..."
        break
    else
        echo "🔁 Продолжаем работу над иллюстрациями..."
    fi
    
    read -p "Хотите скорректировать промпты генерации? (y/n): " prompts_ok
    if [[ "$prompts_ok" =~ ^[Yy]$ ]]; then
        echo "🔧 Запуск корректора промптов (перевод en↔ru, Sublime Text)..."
        python text_processors/illustrations_corrector.py "$OUTPUT_DIR"
        if [ $? -ne 0 ]; then
            echo "⚠️ Ошибка при редактировании промптов. Продолжаем..."
        fi
    fi
done

# 5. Сборка в Manim
echo ""
if [ -f "$OUTPUT_DIR/video.mp4" ]; then
    echo "✅ Видео '$OUTPUT_DIR/video.mp4' уже существует."
    echo "⏭️ Пропуск рендеринга Manim."
else
    echo "🎥 Рендеринг видео в Manim..."
    cd "$OUTPUT_DIR" || exit
    # Очистка каталога сборки
    rm -Rf media
    # Запуск Manim
    manim -ql --disable_caching ../../manim_processors/manim_poetry_player.py PoetryScene

    # можно использовать fzf для выбора результата (тогда убрать очистку сборки)
    VIDEO_RESULT=$(find media/videos -type f -name "PoetryScene.mp4" | head -1)

    if [ -n "$VIDEO_RESULT" ] && [ -f "$VIDEO_RESULT" ]; then
        cp "$VIDEO_RESULT" video.mp4
        echo ""
        echo "🎉 Видео готово: $OUTPUT_DIR/video.mp4"
    else
        echo "❌ Ошибка: видео не найдено."
    fi
    cd - > /dev/null
fi

# 6. Маркетинг и Обложка
# manim_step_promo
# manim_step_pikabu
manim_step_promo_exp "poetry_promo" "$INPUT_FILE" "$OUTPUT_DIR/promo_description.txt"
export_cover "$OUTPUT_DIR" "$OUTPUT_DIR/video.mp4" "$OUTPUT_DIR/cover.jpg" "6"
