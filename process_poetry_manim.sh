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
    echo "  [1] Whisper (стандартный)"
    echo "  [2] WhisperX (whisper + wav2vec2 alignment, точнее на ~50мс)"
    read -p "Выберите режим транскрибации (1/2): " ts_choice

    if [ "$ts_choice" = "2" ]; then
        echo "🔗 Запуск WhisperX транскрибатора..."
        python video_processors/sentence_transcriber_whisperx.py \
            --audio "$AUDIO_FILE" \
            --output-dir "$OUTPUT_DIR" \
            --json-filename "sentence_timestamps.json" \
            --language "ru" \
            --model "medium" \
            --device "cpu" \
            --compute-type "int8"
    else
        python video_processors/sentence_transcriber.py \
            --audio "$AUDIO_FILE" \
            --output-dir "$OUTPUT_DIR" \
            --json-filename "sentence_timestamps.json" \
            --language "ru"
    fi
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

    # Ручная коррекция таймстампов в Sublime Text
    echo ""
    read -p "🔧 Открыть sentence_timestamps.json для ручной коррекции? (y/n): " edit_ts
    if [[ "$edit_ts" =~ ^[Yy] ]]; then
        if command -v subl &> /dev/null; then
            subl -w "$TIMESTAMPS_FILE"
        elif command -v nano &> /dev/null; then
            nano "$TIMESTAMPS_FILE"
        fi
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

# 4. Иллюстрации: AI генерация или копирование скачанных
echo ""
echo "🎨 Подготовка иллюстраций"
echo "  [1] Сгенерировать AI (Together/FLUX)"
echo "  [2] Скопировать скачанные изображения из ~/Downloads/"
read -p "Выберите вариант (1/2): " img_choice

if [ "$img_choice" = "2" ]; then
    # --- Копирование скачанных изображений с мониторингом ~/Downloads ---

    # Собираем содержимое файлов для промпта
    SONG_TEXT=$(cat "$INPUT_FILE" 2>/dev/null || echo "(файл не найден)")
    ILLUSTRATIONS_TEXT=$(cat "$OUTPUT_DIR/illustrations.json" 2>/dev/null || echo "(файл не найден)")

    # Количество сегментов в сценарии
    segment_count="?"
    if [ -f "$OUTPUT_DIR/screenplay.json" ]; then
        segment_count=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_DIR/screenplay.json'))))" 2>/dev/null || echo "?")
    fi

    # Текущее количество изображений (чтобы продолжить нумерацию)
    count=$(ls -1 "$OUTPUT_DIR/images/illustration_"*.png 2>/dev/null | wc -l)
    count=$((count))

    # Печатаем промпт для чата + копируем в буфер обмена
    CHAT_PROMPT="Вот мои стихи:
$SONG_TEXT
---
Создадим иллюстрации одну за другой по описанию из json:
$ILLUSTRATIONS_TEXT"

    echo ""
    echo "📋 Промпт для чата (скопирован в буфер обмена):"
    echo "──────────────────────────────────────────────────────"
    echo "$CHAT_PROMPT"
    echo "──────────────────────────────────────────────────────"
    echo "$CHAT_PROMPT" | xclip -selection clipboard 2>/dev/null && \
        echo "✅ Скопировано в буфер обмена (Ctrl+V в чат)" || \
        echo "⚠️ Буфер обмена недоступен — скопируйте вручную"
    echo ""

    if [ "$segment_count" != "?" ]; then
        echo "📊 Сегментов в сценарии: $segment_count"
        [ "$count" -gt 0 ] && echo "   Уже есть изображений: $count (продолжим с #$count)"
    fi

    if command -v inotifywait &>/dev/null; then
        # --- Режим мониторинга: auto-копирование новых .png по мере скачивания ---
        echo ""
        echo "👀 Мониторинг ~/Downloads/ на новые .png файлы..."
        echo "   Скачивайте изображения в нужном порядке — они будут"
        echo "   автоматически перемещаться и переименовываться."
        echo "   Нажмите [Enter] когда закончите."
        echo ""

        COUNTER_FILE=$(mktemp)
        echo "$count" > "$COUNTER_FILE"

        (
            inotifywait -m -e close_write,moved_to \
                --format '%w%f' ~/Downloads --include '\.png$' 2>/dev/null | \
            while IFS= read -r filepath; do
                [ -z "$filepath" ] && continue
                [[ "$(basename "$filepath")" == .* ]] && continue

                sleep 0.3  # ждём завершения записи браузера

                [ -f "$filepath" ] || continue

                cur=$(cat "$COUNTER_FILE")
                new_name=$(printf "illustration_%02d.png" "$cur")
                mv "$filepath" "$OUTPUT_DIR/images/$new_name"
                echo "  ✅ $(basename "$filepath") -> $new_name"
                echo $((cur + 1)) > "$COUNTER_FILE"

                if [ "$segment_count" != "?" ] && [ $((cur + 1)) -ge "$segment_count" ]; then
                    echo ""
                    echo "🎉 Все $segment_count изображений получены!"
                fi
            done
        ) &
        WATCH_PID=$!

        read -r -p "Нажмите [Enter] когда закончите скачивание: "

        # Убиваем всю группу фоновых процессов (inotifywait + while)
        pkill -P "$WATCH_PID" 2>/dev/null
        kill "$WATCH_PID" 2>/dev/null
        wait "$WATCH_PID" 2>/dev/null
        rm -f "$COUNTER_FILE"
        echo ""
        echo "✅ Мониторинг остановлен."
    else
        # --- Ручной режим (fallback без inotifywait) ---
        echo ""
        echo "⚠️ inotifywait не установлен — ручной режим."
        echo "   Для авто-мониторинга: sudo apt install inotify-tools"
        echo ""

        while true; do
            read -p "Маска файлов в ~/Downloads/ (Enter для *.png): " file_mask
            file_mask="${file_mask:-*.png}"

            IFS=$'\n'
            found_files=($(ls -1v ~/Downloads/$file_mask 2>/dev/null))
            unset IFS
            fc=${#found_files[@]}

            [ "$fc" -eq 0 ] && { echo "❌ Файлы не найдены. Попробуйте другую маску."; continue; }

            echo "Найдено: $fc"
            for f in "${found_files[@]}"; do echo "  - $(basename "$f")"; done

            read -p "Переместить в $OUTPUT_DIR/images/? (y/n): " do_copy
            if [[ "$do_copy" =~ ^[Yy] ]]; then
                IFS=$'\n'
                for file in $(ls -1v ~/Downloads/$file_mask); do
                    new_name=$(printf "illustration_%02d.png" "$count")
                    mv "$file" "$OUTPUT_DIR/images/$new_name"
                    echo "  $(basename "$file") -> $new_name"
                    ((count++))
                done
                unset IFS
                break
            fi
        done
    fi

    # Итого
    final_count=$(ls -1 "$OUTPUT_DIR/images/illustration_"*.png 2>/dev/null | wc -l)
    final_count=$((final_count))
    echo ""
    echo "📥 Итого изображений в images/: $final_count"
    if [ "$segment_count" != "?" ] && [ "$final_count" -lt "$segment_count" ]; then
        echo "⚠️ Не хватает $((segment_count - final_count)) шт."
    fi

    # Просмотр и подтверждение
    echo ""
    echo "👀 Проверьте изображения: $OUTPUT_DIR/images"
    pcmanfm "$OUTPUT_DIR/images" &
    read -p "Изображения устраивают? (y/n): " images_ok
    if [[ ! "$images_ok" =~ ^[Yy]$ ]]; then
        echo "⚠️ Удалите ненужные файлы и запустите скрипт снова."
        exit 1
    fi
    echo "✅ Все иллюстрации подтверждены. Переход к сборке видео..."
else
    # --- AI генерация (оригинальный цикл) ---
    while true; do
        echo ""
        echo "🔄 Проверка и генерация иллюстраций (шаг: просмотр/перегенерация)..."
        python video_processors/illustration_review_cli.py \
            --pipeline-dir "$OUTPUT_DIR" \
            --width 1366 --height 768 \
            --steps 4

        echo ""
        echo "👀 Проверьте изображения в: $OUTPUT_DIR/images и удалите плохие"
        pcmanfm "$OUTPUT_DIR/images" &
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
fi

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

# 7. Публикация
echo ""
if [ -f "$OUTPUT_DIR/video.mp4" ]; then
    read -p "📢 Опубликовать видео? (y/n): " do_publish
    if [[ "$do_publish" =~ ^[Yy] ]]; then
        echo "📤 Запуск публикации..."
        python publisher.py "$OUTPUT_DIR" \
            --platforms vk \
            --title "$TITLE" \
            --privacy private

        # Предлагаем опубликовать статью в группу
        if [ -f "$OUTPUT_DIR/promo_description.txt" ]; then
            echo ""
            read -p "📝 Опубликовать статью в группу VK? (y/n): " do_article
            if [[ "$do_article" =~ ^[Yy] ]]; then
                echo "📤 Публикация статьи..."
                python -c "
import sys, json
sys.path.insert(0, '.')
from publishers.vk_publisher import VKPublisher
from publishers.pipeline_analyzer import PipelineAnalyzer
from publishers.base_publisher import VideoMetadata

analyzer = PipelineAnalyzer('$OUTPUT_DIR')
analyzer.analyze()
m = analyzer.metadata

vk = VKPublisher()
if not vk.authenticate():
    sys.exit(1)

md = VideoMetadata(
    title='$TITLE' or m.book_title or 'Публикация',
    description=m.promo_description or '',
    tags=[],
    privacy='private'
)
post_id = vk.publish_wall_article(md)
if post_id:
    print(f'✅ Статья: https://vk.com/wall-{vk.group_id}_{post_id}')
else:
    print('⚠️ Статья не опубликована')
"
            fi
        fi
    fi
else
    echo "⚠️ Видео не найдено, публикация пропущена."
fi
