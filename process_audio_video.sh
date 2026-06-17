#!/bin/bash
# process_audio_video.sh
# Пайплайн: аудио (mp3/m4a) → транскрибация → сегментация → промпты иллюстраций →
#          скачивание иллюстраций (внешний сервис) → сборка видео
#
# Типичный сценарий: NotebookLM подкаст (два ведущих обсуждают тему) → видео с иллюстрациями
#
# Использование:
#   ./process_audio_video.sh                    # интерактивный выбор файла из ~/Downloads
#   ./process_audio_video.sh /path/to/audio.mp3 # явное указание файла
#   ./process_audio_video.sh configs/audio_video/example.conf

set -eo pipefail

# ============================================================
# 1. Определение исходного аудио файла и конфигурации
# ============================================================

CONFIG_FILE=""
AUDIO_FILE=""
FROM_CONFIG=false

if [ $# -ge 1 ]; then
    ARG="$1"
    # Если аргумент — конфигурационный файл
    if [ -f "$ARG" ] && [[ "$ARG" == *.conf ]]; then
        CONFIG_FILE="$ARG"
        source "$CONFIG_FILE"
        FROM_CONFIG=true
    elif [ -f "$ARG" ]; then
        # Явно передан аудио файл
        AUDIO_FILE="$ARG"
    else
        echo "❌ Файл не найден: $ARG"
        exit 1
    fi
fi

# Если AUDIO_FILE ещё не задан — интерактивный выбор через fzf
if [ -z "$AUDIO_FILE" ]; then
    if ! command -v fzf &>/dev/null; then
        echo "❌ fzf не установлен. Установите: sudo apt install fzf"
        echo "   Или передайте аудио файл явно: ./process_audio_video.sh /path/to/audio.mp3"
        exit 1
    fi

    # Ищем mp3 и m4a файлы в ~/Downloads
    AUDIO_FILE=$(find ~/Downloads -maxdepth 1 -type f \( -iname '*.mp3' -o -iname '*.m4a' \) -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn \
        | cut -d' ' -f2- \
        | fzf --prompt="Выберите аудио файл (mp3/m4a): " \
              --preview='ffprobe -v quiet -show_entries format=duration -of csv=p=0 {} 2>/dev/null | xargs -I{} echo "Длительность: {} сек"')

    if [ -z "$AUDIO_FILE" ]; then
        echo "❌ Файл не выбран"
        exit 1
    fi
fi

if [ ! -f "$AUDIO_FILE" ]; then
    echo "❌ Аудио файл не найден: $AUDIO_FILE"
    exit 1
fi

# ============================================================
# 2. Настройка параметров пайплайна
# ============================================================

# Базовые настройки (можно переопределить в конфиге или интерактивно)
BASE_DIR="${BASE_DIR:-pipelines_audio_video/$(basename "${AUDIO_FILE%.*}")}"
TITLE="${TITLE:-$(basename "${AUDIO_FILE%.*}")}"
LANGUAGE="${LANGUAGE:-ru}"
SEGMENTS_COUNT="${SEGMENTS_COUNT:-10}"
STYLE="${STYLE:-Реалистичный}"
SECONDS_PER_ILLUSTRATION="${SECONDS_PER_ILLUSTRATION:-20}"

OUTPUT_DIR="$BASE_DIR"
CONFIG_PATH="$OUTPUT_DIR/pipeline.conf"

# Если конфиг пайплайна уже существует — загружаем из него
if [ -f "$CONFIG_PATH" ] && [ "$FROM_CONFIG" = false ]; then
    echo "📂 Найден конфиг пайплайна: $CONFIG_PATH"
    source "$CONFIG_PATH"
    OUTPUT_DIR="$BASE_DIR"
fi

# Если запущен без конфига — предлагаем отредактировать параметры
if [ "$FROM_CONFIG" = false ]; then
    echo ""
    echo "⚙️  Параметры пайплайна:"
    echo "  [1] TITLE:                       $TITLE"
    echo "  [2] LANGUAGE:                     $LANGUAGE"
    echo "  [3] SEGMENTS_COUNT:              $SEGMENTS_COUNT"
    echo "  [4] STYLE:                       $STYLE"
    echo "  [5] SECONDS_PER_ILLUSTRATION:    $SECONDS_PER_ILLUSTRATION"
    echo "  [6] BASE_DIR:                    $BASE_DIR"
    echo ""
    read -p "Изменить параметры? (y/n): " edit_params
    if [[ "$edit_params" =~ ^[Yy] ]]; then
        read -p "  TITLE [$TITLE]: " new_val; TITLE="${new_val:-$TITLE}"
        read -p "  LANGUAGE [$LANGUAGE]: " new_val; LANGUAGE="${new_val:-$LANGUAGE}"
        read -p "  SEGMENTS_COUNT [$SEGMENTS_COUNT]: " new_val; SEGMENTS_COUNT="${new_val:-$SEGMENTS_COUNT}"
        read -p "  STYLE [$STYLE]: " new_val; STYLE="${new_val:-$STYLE}"
        read -p "  SECONDS_PER_ILLUSTRATION [$SECONDS_PER_ILLUSTRATION]: " new_val; SECONDS_PER_ILLUSTRATION="${new_val:-$SECONDS_PER_ILLUSTRATION}"
        read -p "  BASE_DIR [$BASE_DIR]: " new_val; BASE_DIR="${new_val:-$BASE_DIR}"
        OUTPUT_DIR="$BASE_DIR"
    fi

    # Сохраняем конфиг пайплайна
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR/images"
    cat > "$CONFIG_PATH" <<CONF
AUDIO_FILE="$AUDIO_FILE"
BASE_DIR="$BASE_DIR"
TITLE="$TITLE"
LANGUAGE="$LANGUAGE"
SEGMENTS_COUNT="$SEGMENTS_COUNT"
STYLE="$STYLE"
SECONDS_PER_ILLUSTRATION="$SECONDS_PER_ILLUSTRATION"
CONF
    echo "✅ Конфиг сохранён: $CONFIG_PATH"
else
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR/images"
fi

# Пересчитываем OUTPUT_DIR после возможного изменения BASE_DIR
OUTPUT_DIR="$BASE_DIR"
mkdir -p "$OUTPUT_DIR/images"

# Копируем аудио в каталог пайплайна (конвертируем m4a → mp3 если нужно)
PIPELINE_AUDIO="$OUTPUT_DIR/audio.mp3"
if [ ! -f "$PIPELINE_AUDIO" ]; then
    if [[ "$AUDIO_FILE" == *.mp3 ]]; then
        cp "$AUDIO_FILE" "$PIPELINE_AUDIO"
        echo "✅ Аудио скопировано: $PIPELINE_AUDIO"
    else
        echo "🔄 Конвертация → mp3..."
        ffmpeg -y -i "$AUDIO_FILE" -vn -c:a libmp3lame -q:a 2 "$PIPELINE_AUDIO" 2>/dev/null
        echo "✅ Аудио сконвертировано: $PIPELINE_AUDIO"
    fi
else
    echo "✅ Аудио уже на месте"
fi

TIMESTAMPS_FILE="$OUTPUT_DIR/sentence_timestamps.json"
TRANSCRIPT_FILE="$OUTPUT_DIR/transcript.txt"

# ============================================================
# Печать заголовка
# ============================================================

AUDIO_DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$PIPELINE_AUDIO" 2>/dev/null || echo "?")
echo ""
echo "🎙️  Аудио → Видео пайплайн"
echo "======================================"
echo "  Аудио:   $AUDIO_FILE"
echo "  Длительность: ${AUDIO_DURATION} сек"
echo "  Каталог: $OUTPUT_DIR"
echo "  Тема:    $TITLE"
echo "  Стиль:   $STYLE"
echo "  Иллюстраций: ~$(python3 -c "print(max(4, int(${AUDIO_DURATION} / ${SECONDS_PER_ILLUSTRATION})))" 2>/dev/null || echo "?") шт. (по ${SECONDS_PER_ILLUSTRATION}с)"
echo ""

# ============================================================
# 3. Транскрибация (Тайминги)
# ============================================================

if [ -f "$TIMESTAMPS_FILE" ]; then
    echo "✅ Таймстампы найдены, пропускаем транскрибацию."
else
    echo "🎤 Транскрибация аудио..."
    echo "  [1] Whisper (стандартный)"
    echo "  [2] WhisperX (whisper + wav2vec2 alignment, точнее на ~50мс)"
    read -p "Выберите режим транскрибации (1/2): " ts_choice

    if [ "$ts_choice" = "2" ]; then
        echo "🔗 Запуск WhisperX транскрибатора..."
        python video_processors/sentence_transcriber_whisperx.py \
            --audio "$PIPELINE_AUDIO" \
            --output-dir "$OUTPUT_DIR" \
            --json-filename "sentence_timestamps.json" \
            --language "$LANGUAGE" \
            --model "medium" \
            --device "cpu" \
            --compute-type "int8"
    else
        python video_processors/sentence_transcriber.py \
            --audio "$PIPELINE_AUDIO" \
            --output-dir "$OUTPUT_DIR" \
            --json-filename "sentence_timestamps.json" \
            --language "$LANGUAGE"
    fi
fi

# ============================================================
# 4. Извлечение текста из транскрипции
# ============================================================

if [ ! -f "$TRANSCRIPT_FILE" ]; then
    echo ""
    echo "📝 Извлечение текста из транскрипции..."
    python3 -c "
import json, sys
with open('$TIMESTAMPS_FILE', 'r', encoding='utf-8') as f:
    data = json.load(f)
# Собираем текст из сегментов
if 'segments' in data:
    text = ' '.join(s.get('text', '') for s in data['segments'])
elif 'text' in data:
    text = data['text']
else:
    print('❌ Не удалось извлечь текст', file=sys.stderr)
    sys.exit(1)
with open('$TRANSCRIPT_FILE', 'w', encoding='utf-8') as f:
    f.write(text.strip())
print(f'✅ Текст сохранен: $TRANSCRIPT_FILE ({len(text)} символов)')
"
else
    echo "✅ Текст транскрипции найден."
fi

# Предлагаем открыть текст для проверки
echo ""
read -p "🔧 Открыть transcript.txt для просмотра/коррекции? (y/n): " edit_ts
if [[ "$edit_ts" =~ ^[Yy] ]]; then
    if command -v subl &>/dev/null; then
        subl -w "$TRANSCRIPT_FILE"
    elif command -v nano &>/dev/null; then
        nano "$TRANSCRIPT_FILE"
    fi
fi

# ============================================================
# 5. Сегментация текста на тематические блоки
# ============================================================

SEGMENTS_JSON="$OUTPUT_DIR/segments.json"
regen_seg="n"

if [ -f "$SEGMENTS_JSON" ]; then
    echo ""
    echo "✅ Сегменты найдены."
    read -p "Перегенерировать сегменты? (y/n): " regen_seg
    if [[ ! "$regen_seg" =~ ^[Yy] ]]; then
        SEGMENTS_COUNT=$(python3 -c "import json; d=json.load(open('$SEGMENTS_JSON')); print(len(d.get('segments',[])))" 2>/dev/null || echo "$SEGMENTS_COUNT")
    fi
fi

if [ ! -f "$SEGMENTS_JSON" ] || [[ "$regen_seg" =~ ^[Yy] ]]; then
    echo ""
    echo "✂️  Сегментация текста на $SEGMENTS_COUNT тематических блоков..."
    python text_processors/text_segmenter.py \
        "$TRANSCRIPT_FILE" \
        --output "$SEGMENTS_JSON" \
        --segments "$SEGMENTS_COUNT" \
        --transcript-json "$TIMESTAMPS_FILE"
fi

# ============================================================
# 6. Генерация промптов для иллюстраций
# ============================================================

ILLUSTRATIONS_JSON="$OUTPUT_DIR/illustrations.json"
regen_prompts="n"

if [ -f "$ILLUSTRATIONS_JSON" ]; then
    echo ""
    echo "✅ Промпты иллюстраций найдены."
    read -p "Перегенерировать промпты? (y/n): " regen_prompts
fi

if [ ! -f "$ILLUSTRATIONS_JSON" ] || [[ "$regen_prompts" =~ ^[Yy] ]]; then
    echo ""
    echo "🎨 Генерация промптов для иллюстраций..."

    # Рассчитываем количество иллюстраций на основе длительности аудио
    AUDIO_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$PIPELINE_AUDIO" 2>/dev/null || echo "300")
    CALCULATED_ILLUSTRATIONS=$(python3 -c "print(max(4, int($AUDIO_DUR / $SECONDS_PER_ILLUSTRATION)))")

    python video_processors/illustration_prompt_processor_v2.py \
        "$TRANSCRIPT_FILE" \
        -o "$ILLUSTRATIONS_JSON" \
        --bible-out "$OUTPUT_DIR/bible.json" \
        --parts "$CALCULATED_ILLUSTRATIONS" \
        --style "$STYLE" \
        --audio-duration "$AUDIO_DUR" \
        --seconds-per-illustration "$SECONDS_PER_ILLUSTRATION" \
        --no-enrich-characters
fi

# ============================================================
# 7. Иллюстрации: AI генерация или скачивание из внешнего сервиса
# ============================================================

echo ""
echo "🎨 Подготовка иллюстраций"
echo "  [1] Сгенерировать AI (Together/FLUX)"
echo "  [2] Скопировать скачанные изображения из ~/Downloads/"
read -p "Выберите вариант (1/2): " img_choice

if [ "$img_choice" = "2" ]; then
    # --- Копирование скачанных изображений с мониторингом ~/Downloads ---

    TRANSCRIPT_TEXT=$(cat "$TRANSCRIPT_FILE" 2>/dev/null || echo "(файл не найден)")
    ILLUSTRATIONS_TEXT=$(cat "$ILLUSTRATIONS_JSON" 2>/dev/null || echo "(файл не найден)")

    # Количество сегментов в сценарии
    segment_count="?"
    if [ -f "$ILLUSTRATIONS_JSON" ]; then
        segment_count=$(python3 -c "import json; d=json.load(open('$ILLUSTRATIONS_JSON')); print(len(d.get('illustrations',[])))" 2>/dev/null || echo "?")
    fi

    # Текущее количество изображений (чтобы продолжить нумерацию)
    count=$(find "$OUTPUT_DIR/images" -maxdepth 1 -name 'illustration_*.png' 2>/dev/null | wc -l)
    count=$((count))

    # Печатаем промпт для чата + копируем в буфер обмена
    CHAT_PROMPT="Тема обсуждения: $TITLE

Транскрипция подкаста:
$TRANSCRIPT_TEXT
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
        echo "📊 Иллюстраций в сценарии: $segment_count"
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
            found_files=($(ls -1v ~/Downloads/$file_mask 2>/dev/null || true))
            unset IFS
            fc=${#found_files[@]}

            [ "$fc" -eq 0 ] && { echo "❌ Файлы не найдены. Попробуйте другую маску."; continue; }

            echo "Найдено: $fc"
            for f in "${found_files[@]}"; do echo "  - $(basename "$f")"; done

            read -p "Переместить в $OUTPUT_DIR/images/? (y/n): " do_copy
            if [[ "$do_copy" =~ ^[Yy] ]]; then
                IFS=$'\n'
                for file in $(ls -1v ~/Downloads/$file_mask 2>/dev/null || true); do
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
    final_count=$(find "$OUTPUT_DIR/images" -maxdepth 1 -name 'illustration_*.png' 2>/dev/null | wc -l)
    final_count=$((final_count))
    echo ""
    echo "📥 Итого изображений в images/: $final_count"
    if [ "$segment_count" != "?" ] && [ "$final_count" -lt "$segment_count" ]; then
        echo "⚠️ Не хватает $((segment_count - final_count)) шт."
    fi

    # Просмотр и подтверждение
    echo ""
    echo "👀 Проверьте изображения: $OUTPUT_DIR/images"
    if command -v pcmanfm &>/dev/null; then
        pcmanfm "$OUTPUT_DIR/images" &
    fi
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
        if command -v pcmanfm &>/dev/null; then
            pcmanfm "$OUTPUT_DIR/images" &
        fi
        read -p "Все изображения устраивают? (y/n): " images_ok
        if [[ "$images_ok" =~ ^[Yy] ]]; then
            echo "✅ Все иллюстрации подтверждены. Переход к сборке видео..."
            break
        else
            echo "🔁 Продолжаем работу над иллюстрациями..."
        fi

        read -p "Хотите скорректировать промпты генерации? (y/n): " prompts_ok
        if [[ "$prompts_ok" =~ ^[Yy] ]]; then
            echo "🔧 Запуск корректора промптов (перевод en↔ru, Sublime Text)..."
            python text_processors/illustrations_corrector.py "$OUTPUT_DIR"
            if [ $? -ne 0 ]; then
                echo "⚠️ Ошибка при редактировании промптов. Продолжаем..."
            fi
        fi
    done
fi

# ============================================================
# 8. Сборка видео
# ============================================================

echo ""
if [ -f "$OUTPUT_DIR/video.mp4" ]; then
    echo "✅ Видео '$OUTPUT_DIR/video.mp4' уже существует."
    read -p "Пересобрать видео? (y/n): " rebuild
    if [[ ! "$rebuild" =~ ^[Yy] ]]; then
        echo "⏭️ Пропуск сборки видео."
        echo ""
        echo "🎉 Готово! Видео: $OUTPUT_DIR/video.mp4"
        exit 0
    fi
fi

echo "🎥 Сборка видео из иллюстраций и аудио..."
python video_processors/video_generator.py \
    --pipeline-dir "$OUTPUT_DIR" \
    --output "$OUTPUT_DIR/video.mp4" \
    --fade-duration 0.5 \
    --enable-photo-motion

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Видео готово: $OUTPUT_DIR/video.mp4"
else
    echo "❌ Ошибка при сборке видео"
    exit 1
fi

# ============================================================
# 9. Обложка (опционально)
# ============================================================

if command -v python3 &>/dev/null && [ -f "lib/manim/utils.sh" ]; then
    source "lib/manim/utils.sh" 2>/dev/null || true
    if type export_cover &>/dev/null; then
        echo ""
        read -p "🖼️ Создать обложку? (y/n): " do_cover
        if [[ "$do_cover" =~ ^[Yy] ]]; then
            export_cover "$OUTPUT_DIR" "$OUTPUT_DIR/video.mp4" "$OUTPUT_DIR/cover.jpg" "6"
        fi
    fi
fi

echo ""
echo "🎉 Пайплайн завершён!"
echo "  Видео:    $OUTPUT_DIR/video.mp4"
[ -f "$OUTPUT_DIR/cover.jpg" ] && echo "  Обложка:  $OUTPUT_DIR/cover.jpg"
echo "  Каталог:  $OUTPUT_DIR"