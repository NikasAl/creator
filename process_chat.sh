#!/bin/bash

# Скрипт для обработки чата с автоматическим определением длительности аудио
# Использование: ./process_chat.sh config_file

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "Использование: $0 <config_file>"
    echo "Пример: $0 configs/chat/example.conf"
    exit 1
fi

CONFIG_FILE="$1"

# Проверка существования конфигурационного файла
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Ошибка: конфигурационный файл $CONFIG_FILE не найден"
    exit 1
fi

# Загрузка конфигурации
source "$CONFIG_FILE"

# Проверка обязательных параметров
if [ -z "$BASE_DIR" ] || [ -z "$TITLE" ]; then
    echo "Ошибка: не все обязательные параметры заданы в конфигурационном файле"
    echo "Обязательные параметры: BASE_DIR, TITLE"
    exit 1
fi

# Установка значений по умолчанию для необязательных параметров
INPUT_FILE="${INPUT_FILE:-article.txt}"
OUTPUT_DIR="$BASE_DIR"
AUDIO_FILE="${AUDIO_FILE:-audio.mp3}"
STYLE="${STYLE:-Реалистичный}"
ERA="${ERA:-21 век}"
REGION="${REGION:-Россия}"
GENRE="${GENRE:-Статья}"
SETTING="${SETTING:-Современная обстановка.}"
SECONDS_PER_ILLUSTRATION="${SECONDS_PER_ILLUSTRATION:-8}"
AUTHOR="${AUTHOR:-AI Assistant}"

# Параметры генерации статьи (необязательные)
ARTICLE_MODEL="${ARTICLE_MODEL:-default}"
ARTICLE_INSTRUCTIONS="${ARTICLE_INSTRUCTIONS:-}"

# Параметры промо-описания (необязательные)
PROMO_PREFIX="${PROMO_PREFIX:-}"
PROMO_MODEL="${PROMO_MODEL:-default}"
PROMO_AUDIENCE="${PROMO_AUDIENCE:-широкая аудитория}"
PROMO_TONE="${PROMO_TONE:-дружелюбный и информативный}"
PROMO_PLATFORM="${PROMO_PLATFORM:-YouTube}"
PROMO_LANG="${PROMO_LANG:-русский}"
PROMO_TITLE="${PROMO_TITLE:-$TITLE}"
PROMO_SOURCE_FILE="${PROMO_SOURCE_FILE:-$INPUT_FILE}"

# Формируем полные пути относительно BASE_DIR
INPUT_FILE_PATH="$BASE_DIR/$INPUT_FILE"
CHAT_FILE="$BASE_DIR/chat.txt"
AUDIO_FILE_PATH="$BASE_DIR/$AUDIO_FILE"

# Получаем абсолютный путь к корневой директории проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📱 Обработка чата в видео: $TITLE"
echo "======================================"
echo "📁 Базовая директория: $BASE_DIR"
echo "📄 Файл чата: $CHAT_FILE"
echo "📝 Выходной файл статьи: $INPUT_FILE_PATH"
echo "🎵 Аудио файл: $AUDIO_FILE_PATH"
echo "👤 Автор: $AUTHOR"
echo "🎨 Стиль: $STYLE"
echo "⏱️ Секунд на иллюстрацию: $SECONDS_PER_ILLUSTRATION"
echo ""

# Проверка входного файла чата
if [ ! -f "$CHAT_FILE" ]; then
    echo "❌ Файл чата не найден: $CHAT_FILE"
    exit 1
fi

# Создание выходного каталога
mkdir -p "$OUTPUT_DIR"

# Проверка маркера обработки
PROCESSING_FILE="$OUTPUT_DIR/.processing"
if [ -f "$PROCESSING_FILE" ]; then
    echo "ℹ️  Обнаружен маркер обработки: $PROCESSING_FILE"
else
    echo "⚠️  Маркер обработки не найден, создаем..."
    cat > "$PROCESSING_FILE" << EOF
{
    "status": "processing",
    "started_at": $(date +%s),
    "config_file": "$CONFIG_FILE"
}
EOF
fi

# Шаг 1: Преобразование чата в статью
echo ""
echo "📝 Шаг 1: Преобразование чата в статью..."

if [ "$RESUME_MODE" = "true" ] && [ -f "$INPUT_FILE_PATH" ]; then
    echo "⏭️ Пропуск: обнаружен существующий article.txt"
else
    # Формируем команду для процессора
    ARTICLE_CMD=(
        python "$SCRIPT_DIR/chat_processors/chat_article_processor.py" "$CHAT_FILE"
        --output "$INPUT_FILE_PATH"
        --config "$SCRIPT_DIR/config.env"
        --model "$ARTICLE_MODEL"
    )
    
    # Добавляем инструкции если указаны
    if [ -n "$ARTICLE_INSTRUCTIONS" ]; then
        # Если путь относительный — считаем его относительно BASE_DIR
        if [[ "$ARTICLE_INSTRUCTIONS" != /* ]]; then
            INSTRUCTIONS_PATH="$BASE_DIR/$ARTICLE_INSTRUCTIONS"
        else
            INSTRUCTIONS_PATH="$ARTICLE_INSTRUCTIONS"
        fi
        if [ -f "$INSTRUCTIONS_PATH" ]; then
            ARTICLE_CMD+=(--instructions "$INSTRUCTIONS_PATH")
            echo "📋 Используем инструкции: $INSTRUCTIONS_PATH"
        fi
    fi
    
    echo "🚀 Запуск команды:"
    printf '%q ' "${ARTICLE_CMD[@]}"; echo
    echo ""
    
    "${ARTICLE_CMD[@]}"
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при создании статьи"
        exit 1
    fi
    
    echo "✅ Статья создана успешно: $INPUT_FILE_PATH"
fi

# Шаг 2: Корректура статьи
echo ""
echo "✏️ Шаг 2: Корректура статьи..."

read -p "Хотите выполнить корректуру статьи? (y/n): " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    while true; do
        echo ""
        echo "🔍 Запуск корректуры и экспорта HTML..."
        PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH" python "$SCRIPT_DIR/text_processors/correction_processor.py" \
            "$INPUT_FILE_PATH" \
            -o "$INPUT_FILE_PATH" \
            --config "$SCRIPT_DIR/config.env" \
            --export-html \
            --html-title "$TITLE"
        
        if [ $? -eq 0 ]; then
            echo "✅ Корректура завершена: $INPUT_FILE_PATH"
        else
            echo "⚠️ Коррекция не выполнена. Продолжаем с исходной статьей."
            break
        fi
        
        # Спрашиваем о необходимости повторной корректуры
        read -p "Хотите выполнить повторную корректуру? (y/n): " -r REPEAT_CORRECTION
        if [[ ! $REPEAT_CORRECTION =~ ^[Yy]$ ]]; then
            break
        fi
    done
else
    echo "⏭️ Корректура пропущена"
fi

# Шаг 3: Создание HTML из статьи (если еще не создан)
if [ ! -f "$INPUT_FILE_PATH.html" ]; then
    echo ""
    echo "🌐 Шаг 3: Создание HTML версии статьи..."
    python "$SCRIPT_DIR/text_processors/markdown_to_html.py" \
        "$INPUT_FILE_PATH" \
        -o "$INPUT_FILE_PATH.html" \
        --title "$TITLE"
    
    if [ $? -eq 0 ]; then
        echo "✅ HTML файл создан: $INPUT_FILE_PATH.html"
    else
        echo "⚠️ Не удалось создать HTML файл"
    fi
else
    echo "ℹ️ HTML файл уже существует: $INPUT_FILE_PATH.html"
fi

# Определение длительности аудио
if [ -f "$AUDIO_FILE_PATH" ]; then
    echo ""
    echo "🔍 Определяем длительность аудио..."
    AUDIO_DURATION=$(python "$SCRIPT_DIR/utils/audio_duration.py" "$AUDIO_FILE_PATH" --format seconds 2>/dev/null)
    
    if [ -n "$AUDIO_DURATION" ]; then
        echo "✅ Длительность аудио: ${AUDIO_DURATION} секунд"
        
        # Рассчитываем количество иллюстраций
        CALCULATED_PARTS=$(python -c "import math; print(max(4, math.ceil($AUDIO_DURATION / $SECONDS_PER_ILLUSTRATION)))")
        echo "📊 Рекомендуемое количество иллюстраций: $CALCULATED_PARTS (по ${SECONDS_PER_ILLUSTRATION}с)"
        
        # Используем рассчитанное количество, но не меньше 8
        PARTS=$((CALCULATED_PARTS < 8 ? 8 : CALCULATED_PARTS))
        echo "🎯 Финальное количество иллюстраций: $PARTS"
    else
        echo "⚠️ Не удалось определить длительность аудио"
        echo "ℹ️ Используем количество по умолчанию: 12"
        PARTS=12
        AUDIO_DURATION=""
    fi
else
    echo "⚠️ Аудио файл не найден: $AUDIO_FILE_PATH"
    echo "ℹ️ Используем количество иллюстраций по умолчанию: 12"
    PARTS=12
    AUDIO_DURATION=""
fi

echo ""
echo "📖 Шаг 4: Создание описаний иллюстраций..."

# Проверка существования файлов
BIBLE_FILE="$OUTPUT_DIR/bible.json"
ILLUSTRATIONS_FILE="$OUTPUT_DIR/illustrations.json"
BIBLE_EXISTS=false
ILLUSTRATIONS_EXISTS=false

if [ -f "$BIBLE_FILE" ]; then
    BIBLE_EXISTS=true
    echo "📖 Найдена существующая bible.json"
fi

if [ -f "$ILLUSTRATIONS_FILE" ]; then
    ILLUSTRATIONS_EXISTS=true
    echo "🖼️ Найден существующий illustrations.json"
fi

# Если существуют оба файла, даем возможность выбора
skip_illustration_gen=false
if [ "$BIBLE_EXISTS" = true ] && [ "$ILLUSTRATIONS_EXISTS" = true ]; then
    echo ""
    echo "ℹ️ Обнаружены существующие файлы:"
    echo "   - Bible: $BIBLE_FILE"
    echo "   - Illustrations: $ILLUSTRATIONS_FILE"
    echo ""
    read -p "Пропустить генерацию illustrations.json? (y/n): " skip_generation
    
    if [[ "$skip_generation" =~ ^[Yy]$ ]]; then
        echo "⏭️ Генерация illustrations.json пропущена"
        skip_illustration_gen=true
    else
        echo "🔄 Перегенерируем illustrations.json..."
        skip_illustration_gen=false
    fi
fi

# Выполняем генерацию только если не пропущена
if [ "$skip_illustration_gen" = false ]; then
    # Формируем команду для процессора
    ILLUSTRATION_CMD="python $SCRIPT_DIR/video_processors/illustration_prompt_processor_v2.py \
        \"$INPUT_FILE_PATH\" \
        --parts \"$PARTS\" \
        --style \"$STYLE\" \
        -o \"$OUTPUT_DIR/illustrations.json\" \
        --bible-out \"$OUTPUT_DIR/bible.json\" \
        --title \"$TITLE\" \
        --author \"$AUTHOR\" \
        --era \"$ERA\" \
        --region \"$REGION\" \
        --genre \"$GENRE\" \
        --setting \"$SETTING\""
    
    # Если bible.json существует, используем её
    if [ "$BIBLE_EXISTS" = true ]; then
        ILLUSTRATION_CMD="$ILLUSTRATION_CMD --bible-in \"$BIBLE_FILE\""
        echo "📖 Используем существующую bible.json"
    fi
    
    # Добавляем длительность аудио если доступна
    if [ -n "$AUDIO_DURATION" ]; then
        ILLUSTRATION_CMD="$ILLUSTRATION_CMD --audio-duration \"$AUDIO_DURATION\" --seconds-per-illustration $SECONDS_PER_ILLUSTRATION"
    fi
    
    echo "🚀 Запуск команды:"
    echo "$ILLUSTRATION_CMD"
    echo ""
    
    # Выполняем команду
    eval $ILLUSTRATION_CMD
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при создании описаний иллюстраций"
        exit 1
    fi
fi

if [ $? -eq 0 ]; then
    echo ""
    if [ "$skip_illustration_gen" = true ]; then
        echo "✅ Использованы существующие описания иллюстраций"
    else
        echo "✅ Описания иллюстраций созданы успешно!"
    fi
    echo "📁 Результаты сохранены в: $OUTPUT_DIR"
    echo "📖 Bible: $OUTPUT_DIR/bible.json"
    echo "🖼️ Иллюстрации: $OUTPUT_DIR/illustrations.json"
    
    # Показываем краткую статистику
    if [ -f "$OUTPUT_DIR/illustrations.json" ]; then
        ILLUSTRATION_COUNT=$(python -c "import json; data=json.load(open('$OUTPUT_DIR/illustrations.json')); print(len(data.get('illustrations', [])))" 2>/dev/null || echo "0")
        SCRIPT_COUNT=$(python -c "import json; data=json.load(open('$OUTPUT_DIR/illustrations.json')); print(len(data.get('script', [])))" 2>/dev/null || echo "0")
        echo ""
        echo "📊 Статистика:"
        echo "   - Создано иллюстраций: $ILLUSTRATION_COUNT"
        echo "   - Сценарий содержит: $SCRIPT_COUNT сцен"
    fi
    
    echo ""
    echo "🎬 Следующий шаг: создание иллюстраций"
    echo "python $SCRIPT_DIR/video_processors/illustration_review_cli.py --pipeline-dir $OUTPUT_DIR"
    
    # Шаг 5: Создание иллюстраций
    echo ""
    echo "🖼️ Хотите создать иллюстрации?"
    read -p "Введите 'y' или 'yes' для создания иллюстраций: " create_illustrations
    
    if [[ "$create_illustrations" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        while true; do
            echo ""
            echo "🎨 Создание иллюстраций..."
            python "$SCRIPT_DIR/video_processors/illustration_review_cli.py" --pipeline-dir "$OUTPUT_DIR"
            
            if [ $? -eq 0 ]; then
                echo "✅ Иллюстрации созданы успешно!"
            else
                echo "❌ Ошибка при создании иллюстраций"
            fi
            
            echo ""
            echo "Проверьте иллюстрации в каталоге $OUTPUT_DIR/images и при необходимости удалите нежелательные."
            read -p "Хотите пересоздать иллюстрации? (y/n): " -r
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                break
            fi
        done
    fi
    
    # Шаг 6: Создание обложки
    echo ""
    echo "🖼️ Хотите создать обложку для ролика?"
    read -p "Введите 'y' или 'yes' для создания обложки: " create_cover
    
    if [[ "$create_cover" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo ""
        echo "🎨 Создание обложки..."
        
        # Проверяем наличие директории images
        if [ -d "$OUTPUT_DIR/images" ]; then
            # Запускаем make_cover.py в интерактивном режиме
            python "$SCRIPT_DIR/image_generators/make_cover.py" "$OUTPUT_DIR"
            
            if [ $? -eq 0 ]; then
                echo "✅ Обложка создана успешно!"
            else
                echo "❌ Ошибка при создании обложки"
            fi
        else
            echo "⚠️ Директория images не найдена в $OUTPUT_DIR"
            echo "Сначала создайте иллюстрации с помощью:"
            echo "python $SCRIPT_DIR/video_processors/illustration_review_cli.py --pipeline-dir $OUTPUT_DIR"
        fi
    fi
    
    # Шаг 7: Опциональная перегенерация фото через Alibaba
    echo ""
    echo "🔄 Хотите перегенерировать некоторые изображения через Alibaba Cloud?"
    read -p "Введите 'y' или 'yes' для перегенерации: " regenerate_alibaba
    
    if [[ "$regenerate_alibaba" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        while true; do
            echo ""
            echo "📋 Доступные изображения в $OUTPUT_DIR/images:"
            ls -la "$OUTPUT_DIR/images/illustration_*.png" 2>/dev/null | head -10
            
            echo ""
            read -p "Введите номера изображений для перегенерации через запятую (например: 1,3,5): " image_indices
            
            if [ -n "$image_indices" ]; then
                echo ""
                echo "🎨 Перегенерация изображений через Alibaba Cloud..."
                python "$SCRIPT_DIR/video_processors/alibaba_image_generator.py" \
                    --pipeline-dir "$OUTPUT_DIR" \
                    --indices "$image_indices" \
                    --size "1360*768" \
                    --n 1
                
                if [ $? -eq 0 ]; then
                    echo "✅ Изображения перегенерированы успешно!"
                else
                    echo "❌ Ошибка при перегенерации изображений"
                fi
            fi
            
            echo ""
            read -p "Хотите перегенерировать еще изображения? (y/n): " -r
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                break
            fi
        done
    fi
    
    # Шаг 8: Генерация видео по номеру иллюстрации
    echo ""
    echo "🎬 Хотите создать видео для конкретной иллюстрации?"
    read -p "Введите 'y' или 'yes' для создания видео: " create_video
    
    if [[ "$create_video" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        while true; do
            echo ""
            echo "📋 Доступные изображения в $OUTPUT_DIR/images:"
            ls -la "$OUTPUT_DIR/images/illustration_*.png" 2>/dev/null | head -10
            
            echo ""
            read -p "Введите номер изображения для создания видео: " image_index
            
            if [ -n "$image_index" ] && [[ "$image_index" =~ ^[0-9]+$ ]]; then
                echo ""
                echo "🎬 Создание видео для изображения $image_index..."
                python "$SCRIPT_DIR/video_processors/alibaba_video_generator.py" \
                    --pipeline-dir "$OUTPUT_DIR" \
                    --image-index "$image_index" \
                    --duration 5 \
                    --resolution "720P"
                
                if [ $? -eq 0 ]; then
                    echo "✅ Видео создано успешно!"
                else
                    echo "❌ Ошибка при создании видео"
                fi
            else
                echo "❌ Неверный номер изображения"
            fi
            
            echo ""
            read -p "Хотите создать видео для другого изображения? (y/n): " -r
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                break
            fi
        done
    fi
    
    # Шаг 9: Финальная генерация видео
    echo ""
    echo "🎬 Хотите создать финальное видео?"
    read -p "Введите 'y' или 'yes' для создания финального видео: " create_final_video
    
    if [[ "$create_final_video" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo ""
        echo "📝 Настройка параметров финального видео..."
        
        # Запрашиваем параметры silence-duration и ending-duration
        echo ""
        read -p "Введите время показа первого изображения до начала слов в секундах (по умолчанию 0): " silence_duration
        silence_duration="${silence_duration:-0}"
        
        echo ""
        read -p "Введите время показа последнего изображения после слов в секундах (по умолчанию 0): " ending_duration
        ending_duration="${ending_duration:-0}"
        
        echo ""
        echo "🎬 Создание финального видео с параметрами:"
        echo "   Silence duration: ${silence_duration}с"
        echo "   Ending duration: ${ending_duration}с"
        
        python "$SCRIPT_DIR/video_processors/video_generator.py" \
            --pipeline-dir "$OUTPUT_DIR" \
            --silence-duration "$silence_duration" \
            --ending-duration "$ending_duration" \
            --fade-duration 0.5 \
            --quality medium
        
        if [ $? -eq 0 ]; then
            echo "✅ Финальное видео создано успешно!"
            echo "📁 Видео сохранено: $OUTPUT_DIR/video.mp4"
        else
            echo "❌ Ошибка при создании финального видео"
        fi
    fi
    
    # Шаг 10: Создание промо-описания
    echo ""
    echo "📝 Хотите создать промо-описание для публикации?"
    read -p "Введите 'y' или 'yes' для создания промо-описания: " create_promo
    
    if [[ "$create_promo" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo ""
        echo "🧩 Создание промо-описания..."
        # Формируем команду как массив для корректного экранирования аргументов
        PROMO_CMD=(
            python "$SCRIPT_DIR/text_processors/promo_description_processor.py" "$OUTPUT_DIR"
            --config "$SCRIPT_DIR/config.env"
            --model "$PROMO_MODEL"
            --audience "$PROMO_AUDIENCE"
            --tone "$PROMO_TONE"
            --platform "$PROMO_PLATFORM"
            --lang "$PROMO_LANG"
            --title "$PROMO_TITLE"
        )

        # Необязательные параметры
        if [ -n "$PROMO_PREFIX" ]; then
            PROMO_CMD+=(--prefix "$PROMO_PREFIX")
        fi
        if [ -n "$PROMO_SOURCE_FILE" ]; then
            # Если путь относительный — считаем его относительно BASE_DIR
            if [[ "$PROMO_SOURCE_FILE" != /* ]]; then
                PROMO_SOURCE_PATH="$BASE_DIR/$PROMO_SOURCE_FILE"
            else
                PROMO_SOURCE_PATH="$PROMO_SOURCE_FILE"
            fi
            if [ -f "$PROMO_SOURCE_PATH" ]; then
                PROMO_CMD+=(--source-file "$PROMO_SOURCE_PATH")
            fi
        fi

        # Выходной файл по умолчанию внутри каталога пайплайна
        PROMO_OUTPUT_PATH="$OUTPUT_DIR/promo_description.txt"
        PROMO_CMD+=(-o "$PROMO_OUTPUT_PATH")

        echo "🚀 Запуск команды:"
        printf '%q ' "${PROMO_CMD[@]}"; echo
        echo ""

        "${PROMO_CMD[@]}"
        if [ $? -eq 0 ]; then
            echo "✅ Промо-описание создано: $PROMO_OUTPUT_PATH"
        else
            echo "❌ Ошибка при создании промо-описания"
        fi
    fi
    
    # Удаляем маркер обработки после успешного завершения
    if [ -f "$PROCESSING_FILE" ]; then
        echo ""
        echo "✅ Пайплайн завершен успешно!"
        read -p "Удалить маркер обработки? (y/n): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$PROCESSING_FILE"
            echo "🗑️ Маркер обработки удален"
        fi
    fi
    
else
    echo "❌ Ошибка при создании описаний иллюстраций"
    exit 1
fi

