#!/bin/bash
# process_audio_video.sh
# Пайплайн: аудио файл (mp3) → транскрибация → промпты иллюстраций → изображения → видео
#
# Использование: ./process_audio_video.sh [config_file]
# Без аргументов — интерактивное создание конфига.
#
# Типичный сценарий: NotebookLM подкаст → видео с иллюстрациями

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ROOT_DIR/lib/common/utils.sh"

TOTAL_STEPS=6

# ============================================
# 1. КОНФИГУРАЦИЯ
# ============================================

if [ $# -eq 0 ]; then
    log_header "Интерактивная настройка пайплайна audio → video"

    read -p "Путь к аудио файлу (mp3): " AUDIO_INPUT
    [ ! -f "$AUDIO_INPUT" ] && { log_error "Файл не найден: $AUDIO_INPUT"; exit 1; }
    AUDIO_INPUT="$(realpath "$AUDIO_INPUT")"

    read -p "Название проекта (для папки): " PROJECT_NAME
    PROJECT_NAME="${PROJECT_NAME:-audio_video_$(date +%Y%m%d_%H%M%S)}"

    read -p "Заголовок видео: " TITLE
    TITLE="${TITLE:-$PROJECT_NAME}"

    read -p "Автор (опционально): " AUTHOR
    AUTHOR="${AUTHOR:-}"

    read -p "Язык аудио (ru/en): " LANGUAGE
    LANGUAGE="${LANGUAGE:-ru}"

    read -p "Стиль иллюстраций (Реалистичный): " STYLE
    STYLE="${STYLE:-Реалистичный}"

    read -p "Эпоха (21 век): " ERA
    ERA="${ERA:-21 век}"

    read -p "Регион (Россия): " REGION
    REGION="${REGION:-Россия}"

    read -p "Жанр (Образовательное видео): " GENRE
    GENRE="${GENRE:-Образовательное видео}"

    read -p "Сеттинг (Современная обстановка): " SETTING
    SETTING="${SETTING:-Современная обстановка}"

    # Создаём конфиг
    OUTPUT_DIR="$ROOT_DIR/pipelines_scr/$PROJECT_NAME"
    CONFIG_FILE="$OUTPUT_DIR/config.conf"

    mkdir -p "$OUTPUT_DIR"

    cat > "$CONFIG_FILE" <<CONF
TITLE="$TITLE"
AUTHOR="$AUTHOR"
LANGUAGE="$LANGUAGE"
STYLE="$STYLE"
ERA="$ERA"
REGION="$REGION"
GENRE="$GENRE"
SETTING="$SETTING"
AUDIO_INPUT="$AUDIO_INPUT"
BASE_DIR="$OUTPUT_DIR"
CONF

    echo ""
    log_success "Конфиг создан: $CONFIG_FILE"
    echo "Для запуска: ./process_audio_video.sh $CONFIG_FILE"
    exit 0
else
    CONFIG_FILE="$1"
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Файл конфигурации не найден: $CONFIG_FILE"
        exit 1
    fi
fi

source "$CONFIG_FILE"

# Дефолты
TITLE="${TITLE:-Аудио видео}"
AUTHOR="${AUTHOR:-}"
LANGUAGE="${LANGUAGE:-ru}"
STYLE="${STYLE:-Реалистичный}"
ERA="${ERA:-21 век}"
REGION="${REGION:-Россия}"
GENRE="${GENRE:-Образовательное видео}"
SETTING="${SETTING:-Современная обстановка.}"
SECONDS_PER_ILLUSTRATION="${SECONDS_PER_ILLUSTRATION:-15}"
MODEL_CHOICE="${MODEL_CHOICE:-default}"
RESUME_MODE="${RESUME_MODE:-true}"

BASE_DIR="${BASE_DIR:-$(dirname "$CONFIG_FILE")}"
OUTPUT_DIR="$BASE_DIR"
AUDIO_FILE="$OUTPUT_DIR/audio.mp3"
TRANSCRIPT_JSON="$OUTPUT_DIR/transcript.json"
TRANSCRIPT_TXT="$OUTPUT_DIR/transcript.txt"
SEGMENTS_JSON="$OUTPUT_DIR/segments.json"
ILLUSTRATIONS_JSON="$OUTPUT_DIR/illustrations.json"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/images"

log_header "Пайплайн audio → video: $TITLE"
echo "📂 Директория: $OUTPUT_DIR"

# ============================================
# 2. ПОДГОТОВКА АУДИО
# ============================================

log_step 1 $TOTAL_STEPS "Подготовка аудио"

if [ ! -f "$AUDIO_FILE" ]; then
    if [ -n "$AUDIO_INPUT" ] && [ -f "$AUDIO_INPUT" ]; then
        cp "$AUDIO_INPUT" "$AUDIO_FILE"
        log_success "Аудио скопировано: $AUDIO_INPUT → $AUDIO_FILE"
    else
        # Ищем mp3 в директории пайплайна
        FOUND_AUDIO=$(find "$OUTPUT_DIR" -maxdepth 1 -name "*.mp3" | head -1)
        if [ -n "$FOUND_AUDIO" ]; then
            cp "$FOUND_AUDIO" "$AUDIO_FILE"
            log_success "Аудио найдено: $FOUND_AUDIO"
        else
            log_error "Аудио файл не найден. Положите mp3 в $OUTPUT_DIR или укажите AUDIO_INPUT в конфиге."
            exit 1
        fi
    fi
else
    log_success "Аудио уже на месте: $AUDIO_FILE"
fi

AUDIO_DURATION=$(get_audio_duration "$AUDIO_FILE")
echo "🎵 Длительность аудио: ${AUDIO_DURATION} сек"

# ============================================
# 3. ТРАНСКРИБАЦИЯ
# ============================================

log_step 2 $TOTAL_STEPS "Транскрибация аудио"

if [ "$RESUME_MODE" = "true" ] && [ -f "$TRANSCRIPT_TXT" ] && [ -f "$TRANSCRIPT_JSON" ]; then
    log_success "Транскрипция уже есть, пропуск."
else
    echo "  [1] Whisper (стандартный)"
    echo "  [2] WhisperX (whisper + wav2vec2 alignment)"
    read -p "  Режим транскрибации (1/2): " ts_choice

    if [ "$ts_choice" = "2" ]; then
        python "$ROOT_DIR/video_processors/sentence_transcriber_whisperx.py" \
            --audio "$AUDIO_FILE" \
            --output-dir "$OUTPUT_DIR" \
            --json-filename "sentence_timestamps.json" \
            --language "$LANGUAGE" \
            --model "medium" \
            --device "cpu" \
            --compute-type "int8"
    else
        python "$ROOT_DIR/video_processors/sentence_transcriber.py" \
            --audio "$AUDIO_FILE" \
            --output-dir "$OUTPUT_DIR" \
            --json-filename "sentence_timestamps.json" \
            --language "$LANGUAGE" \
            --readable
    fi

    # sentence_transcriber создаёт sentence_timestamps.json
    # Для text_segmenter нужен transcript.txt и transcript.json
    # Конвертируем формат
    if [ -f "$OUTPUT_DIR/sentence_timestamps.json" ]; then
        python3 -c "
import json
with open('$OUTPUT_DIR/sentence_timestamps.json') as f:
    data = json.load(f)
# Текст
with open('$TRANSCRIPT_TXT', 'w') as f:
    f.write(data.get('text', ''))
# JSON в формате video_transcriber
with open('$TRANSCRIPT_JSON', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f'✅ transcript.txt ({len(data.get(\"text\",\"\"))} символов) и transcript.json созданы')
"
    fi
fi

# ============================================
# 4. ПРОМПТЫ ИЛЛЮСТРАЦИЙ
# ============================================

log_step 3 $TOTAL_STEPS "Генерация промптов для иллюстраций"

if [ "$RESUME_MODE" = "true" ] && [ -f "$ILLUSTRATIONS_JSON" ]; then
    log_success "illustrations.json уже есть."
    read -p "  Перегенерировать? (y/n): " regen_ill
    if [[ ! "$regen_ill" =~ ^[Yy]$ ]]; then
        ILL_REGEN="false"
    else
        ILL_REGEN="true"
    fi
else
    ILL_REGEN="true"
fi

if [ "$ILL_REGEN" = "true" ]; then
    # Рассчитываем количество иллюстраций по длительности аудио
    if [ -n "$AUDIO_DURATION" ] && [ "$AUDIO_DURATION" -gt 0 ] 2>/dev/null; then
        CALC_PARTS=$(python3 -c "import math; print(max(4, math.ceil($AUDIO_DURATION / $SECONDS_PER_ILLUSTRATION)))")
    else
        CALC_PARTS=8
    fi

    BIBLE_ARG=""
    [ -f "$OUTPUT_DIR/bible.json" ] && BIBLE_ARG="--bible-in $OUTPUT_DIR/bible.json"

    python "$ROOT_DIR/video_processors/illustration_prompt_processor_v2.py" \
        "$TRANSCRIPT_TXT" \
        --parts "$CALC_PARTS" \
        --style "$STYLE" \
        -o "$ILLUSTRATIONS_JSON" \
        $BIBLE_ARG \
        --bible-out "$OUTPUT_DIR/bible.json" \
        --title "$TITLE" \
        --author "$AUTHOR" \
        --era "$ERA" \
        --region "$REGION" \
        --genre "$GENRE" \
        --setting "$SETTING" \
        --audio-duration "$AUDIO_DURATION" \
        --seconds-per-illustration "$SECONDS_PER_ILLUSTRATION"
fi

# ============================================
# 5. ИЛЛЮСТРАЦИИ
# ============================================

log_step 4 $TOTAL_STEPS "Получение иллюстраций"

ILL_COUNT=$(ls -1 "$OUTPUT_DIR/images/illustration_"*.png 2>/dev/null | wc -l)
ILL_COUNT=$((ILL_COUNT))

SEGMENT_COUNT=$(python3 -c "
import json
try:
    with open('$ILLUSTRATIONS_JSON') as f:
        data = json.load(f)
    print(len(data.get('illustrations', [])))
except:
    print(0)
" 2>/dev/null)

echo "  Нужно иллюстраций: $SEGMENT_COUNT"
[ "$ILL_COUNT" -gt 0 ] && echo "  Уже есть: $ILL_COUNT"

if [ "$ILL_COUNT" -ge "$SEGMENT_COUNT" ] && [ "$SEGMENT_COUNT" -gt 0 ]; then
    log_success "Все иллюстрации уже на месте ($ILL_COUNT/$SEGMENT_COUNT)."
else
    echo ""
    echo "  [1] AI генерация (Together/FLUX)"
    echo "  [2] Внешний сервис (промпт в буфер + мониторинг Downloads)"
    read -p "  Выберите вариант (1/2): " img_choice

    if [ "$img_choice" = "2" ]; then
        # --- Внешний сервис: промпт в буфер + inotifywait ---

        # Формируем промпт для чата из illustrations.json
        ILL_TEXT=$(python3 -c "
import json
with open('$ILLUSTRATIONS_JSON') as f:
    data = json.load(f)
ills = data.get('illustrations', [])
lines = []
for i, ill in enumerate(ills):
    lines.append(f'Иллюстрация {i+1}: {ill.get(\"title\", \"\")}')
    lines.append(f'Промпт: {ill.get(\"prompt\", \"\")}')
    lines.append('')
print('\n'.join(lines))
" 2>/dev/null)

        TRANSCRIPT_EXCERPT=$(head -c 2000 "$TRANSCRIPT_TXT" 2>/dev/null || echo "(нет транскрипции)")

        CHAT_PROMPT="Название: $TITLE
Автор: $AUTHOR

Текст обсуждения (начало):
$TRANSCRIPT_EXCERPT

---
Создай иллюстрации по следующим описаниям (по одной, в порядке номеров):

$ILL_TEXT

Размер: 1366x768, формат PNG. Скачивай последовательно."

        echo ""
        echo "📋 Промпт для чата (скопирован в буфер обмена):"
        echo "──────────────────────────────────────────────────────"
        echo "$CHAT_PROMPT"
        echo "──────────────────────────────────────────────────────"
        echo "$CHAT_PROMPT" | xclip -selection clipboard 2>/dev/null && \
            echo "✅ Скопировано в буфер обмена (Ctrl+V в чат)" || \
            echo "⚠️ Буфер обмена недоступен — скопируйте вручную"
        echo ""

        if command -v inotifywait &>/dev/null; then
            echo "👀 Мониторинг ~/Downloads/ на новые .png файлы..."
            echo "   Скачивайте изображения в нужном порядке — они будут"
            echo "   автоматически перемещаться и переименовываться."
            echo "   Нажмите [Enter] когда закончите."
            echo ""

            COUNTER_FILE=$(mktemp)
            echo "$ILL_COUNT" > "$COUNTER_FILE"

            (
                inotifywait -m -e close_write,moved_to \
                    --format '%w%f' ~/Downloads --include '\.png$' 2>/dev/null | \
                while IFS= read -r filepath; do
                    [ -z "$filepath" ] && continue
                    [[ "$(basename "$filepath")" == .* ]] && continue

                    sleep 0.3

                    [ -f "$filepath" ] || continue

                    cur=$(cat "$COUNTER_FILE")
                    new_name=$(printf "illustration_%02d.png" "$cur")
                    mv "$filepath" "$OUTPUT_DIR/images/$new_name"
                    echo "  ✅ $(basename "$filepath") -> $new_name"
                    echo $((cur + 1)) > "$COUNTER_FILE"

                    if [ "$SEGMENT_COUNT" -gt 0 ] && [ $((cur + 1)) -ge "$SEGMENT_COUNT" ]; then
                        echo ""
                        echo "🎉 Все $SEGMENT_COUNT изображений получены!"
                    fi
                done
            ) &
            WATCH_PID=$!

            read -r -p "Нажмите [Enter] когда закончите скачивание: "

            pkill -P "$WATCH_PID" 2>/dev/null
            kill "$WATCH_PID" 2>/dev/null
            wait "$WATCH_PID" 2>/dev/null
            rm -f "$COUNTER_FILE"
            echo ""
            log_success "Мониторинг остановлен."
        else
            # --- Ручной режим (fallback) ---
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
                        new_name=$(printf "illustration_%02d.png" "$ILL_COUNT")
                        mv "$file" "$OUTPUT_DIR/images/$new_name"
                        echo "  $(basename "$file") -> $new_name"
                        ((ILL_COUNT++))
                    done
                    unset IFS
                    break
                fi
            done
        fi

        # Итого
        FINAL_ILL_COUNT=$(ls -1 "$OUTPUT_DIR/images/illustration_"*.png 2>/dev/null | wc -l)
        FINAL_ILL_COUNT=$((FINAL_ILL_COUNT))
        echo ""
        echo "📥 Итого изображений: $FINAL_ILL_COUNT"
        if [ "$SEGMENT_COUNT" -gt 0 ] && [ "$FINAL_ILL_COUNT" -lt "$SEGMENT_COUNT" ]; then
            echo "⚠️ Не хватает $((SEGMENT_COUNT - FINAL_ILL_COUNT)) шт."
        fi
    else
        # --- AI генерация (через illustration_review_cli.py) ---
        while true; do
            echo ""
            echo "🔄 Генерация/Просмотр иллюстраций..."
            python "$ROOT_DIR/video_processors/illustration_review_cli.py" \
                --pipeline-dir "$OUTPUT_DIR" \
                --width 1366 --height 768 \
                --steps 4

            echo ""
            echo "👀 Проверьте изображения в: $OUTPUT_DIR/images"
            if command -v feh &>/dev/null; then
                feh "$OUTPUT_DIR/images/" &
            elif command -v pcmanfm &>/dev/null; then
                pcmanfm "$OUTPUT_DIR/images" &
            fi

            read -p "Все изображения устраивают? (y/n): " images_ok
            if [[ "$images_ok" =~ ^[Yy]$ ]]; then
                log_success "Иллюстрации подтверждены."
                break
            else
                echo "🔁 Продолжаем работу над иллюстрациями..."
            fi
        done
    fi
fi

# ============================================
# 6. СБОРКА ВИДЕО
# ============================================

log_step 5 $TOTAL_STEPS "Сборка финального видео"

if [ -f "$OUTPUT_DIR/video.mp4" ]; then
    log_success "Видео уже существует: $OUTPUT_DIR/video.mp4"
    read -p "  Пересобрать? (y/n): " rebuild
    if [[ ! "$rebuild" =~ ^[Yy]$ ]]; then
        log_header "Готово! Видео: $OUTPUT_DIR/video.mp4"
        exit 0
    fi
fi

echo ""
read -p "Тишина в начале (сек) [0]: " s_dur
read -p "Тишина в конце (сек) [0]: " e_dur
read -p "Включить плавный зум? (y/n) [n]: " zoom_yn
s_dur="${s_dur:-0}"
e_dur="${e_dur:-0}"
ZOOM_FLAG=""
[[ "$zoom_yn" =~ ^[Yy]$ ]] && ZOOM_FLAG="--enable-photo-motion"

python "$ROOT_DIR/video_processors/video_generator.py" \
    --pipeline-dir "$OUTPUT_DIR" \
    --output "$OUTPUT_DIR/video.mp4" \
    --silence-duration "$s_dur" \
    --ending-duration "$e_dur" \
    --fade-duration 0.5 \
    --quality medium \
    $ZOOM_FLAG

if [ -f "$OUTPUT_DIR/video.mp4" ]; then
    log_success "Видео создано: $OUTPUT_DIR/video.mp4"
else
    log_error "Видео не создано."
    exit 1
fi

# ============================================
# 7. ОБЛОЖКА И ПРОМО (опционально)
# ============================================

log_step 6 $TOTAL_STEPS "Обложка и промо (опционально)"

source "$ROOT_DIR/lib/manim/05_extra.sh"

if command -v export_cover &>/dev/null; then
    read -p "Создать обложку? (y/n): " do_cover
    if [[ "$do_cover" =~ ^[Yy]$ ]]; then
        export_cover "$OUTPUT_DIR" "$OUTPUT_DIR/video.mp4" "$OUTPUT_DIR/cover.jpg" "6"
    fi
fi

read -p "Создать промо описание? (y/n): " do_promo
if [[ "$do_promo" =~ ^[Yy]$ ]]; then
    manim_step_promo_exp "podcast" "$TRANSCRIPT_TXT" "$OUTPUT_DIR/promo_description.txt"
fi

# ============================================
# ГОТОВО
# ============================================

log_header "Пайплайн завершен!"
echo "🎬 Видео: $OUTPUT_DIR/video.mp4"
[ -f "$OUTPUT_DIR/cover.jpg" ] && echo "🖼️  Обложка: $OUTPUT_DIR/cover.jpg"
[ -f "$OUTPUT_DIR/promo_description.txt" ] && echo "📝 Промо: $OUTPUT_DIR/promo_description.txt"