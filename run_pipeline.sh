#!/bin/bash

# Единый скрипт для запуска pipeline с конфигурационным файлом
# Использование: ./run_pipeline.sh config_file

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "Использование: $0 <config_file>"
    echo "Пример: $0 configs/stalin.conf"
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

# Экспортируем переменные моделей в окружение
export SUMMARY_MODEL="${SUMMARY_MODEL:-}"
export VISION_MODEL="${VISION_MODEL:-}"
export IMAGE_MODEL="${IMAGE_MODEL:-FLUX}"

# Проверка обязательных параметров
if [ -z "$PDF_FILE" ] || [ -z "$OUTPUT_DIR" ] || [ -z "$PAGE_RANGE" ] || [ -z "$TITLE" ] || [ -z "$AUTHOR" ]; then
    echo "Ошибка: не все обязательные параметры заданы в конфигурационном файле"
    echo "Обязательные параметры: PDF_FILE, OUTPUT_DIR, PAGE_RANGE, TITLE, AUTHOR"
    exit 1
fi

# Установка значений по умолчанию для необязательных параметров
SUMMARY_STYLE="${SUMMARY_STYLE:-educational}"
PARTS="${PARTS:-40}"
STYLE="${STYLE:-Реалистичный}"
PLATFORM="${PLATFORM:-YouTube}"

# Проверка существования PDF файла
if [ ! -f "$PDF_FILE" ]; then
    echo "Ошибка: файл $PDF_FILE не найден"
    exit 1
fi

# Создание выходного каталога если не существует
mkdir -p "$OUTPUT_DIR"

echo "Запуск полного pipeline:"
echo "PDF: $PDF_FILE"
echo "Output: $OUTPUT_DIR"
echo "Pages: $PAGE_RANGE"
echo "Style: $SUMMARY_STYLE"
echo "Title: $TITLE"
echo "Author: $AUTHOR"
echo "Parts: $PARTS"
echo "Illustration style: $STYLE"
echo "Platform: $PLATFORM"
echo ""

# Получаем абсолютный путь к корневой директории проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Шаг 1: создание рабочего каталога и обработка текста
echo "Step 1: Обработка текста..."
python "$SCRIPT_DIR/full_pipeline.py" "$PDF_FILE" \
    --output "$OUTPUT_DIR" \
    --page-range "$PAGE_RANGE" \
    --summary-style "$SUMMARY_STYLE" \
    --title "$TITLE" \
    --author "$AUTHOR"

if [ $? -ne 0 ]; then
    echo "Ошибка на шаге обработки текста"
    exit 1
fi

# Дополнительный шаг 1: корректура пересказа
echo ""
echo "Доп. шаг 1: Корректура пересказа..."
read -p "Хотите выполнить корректуру пересказа? (y/n): " -r DO_CORRECTION
if [[ $DO_CORRECTION =~ ^[Yy]$ ]]; then
    # Определяем имя файла пересказа
    BASENAME=$(basename "$PDF_FILE" .pdf)
    SUMMARY_FILE="$OUTPUT_DIR/${BASENAME}_summary_${SUMMARY_STYLE}.txt"

    if [ -f "$SUMMARY_FILE" ]; then
        echo "Найден пересказ: $SUMMARY_FILE"
        
        # Цикл корректуры с возможностью повторения
        while true; do
            echo "Запускаем коррекцию..."
            PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH" python "$SCRIPT_DIR/text_processors/correction_processor.py" \
                "$SUMMARY_FILE" \
                -o "$SUMMARY_FILE" \
                --config "$SCRIPT_DIR/config.env"

            if [ $? -ne 0 ]; then
                echo "⚠️ Коррекция не выполнена. Продолжаем с исходным пересказом."
                break
            else
                echo "✅ Коррекция завершена: $SUMMARY_FILE"
            fi
            
            # Спрашиваем о необходимости повторной корректуры
            read -p "Хотите выполнить повторную корректуру? (y/n): " -r REPEAT_CORRECTION
            if [[ ! $REPEAT_CORRECTION =~ ^[Yy]$ ]]; then
                break
            fi
        done
    else
        echo "⚠️ Файл пересказа не найден: $SUMMARY_FILE"
    fi
else
    echo "Шаг корректуры пропущен."
fi

# Создание HTML из summary файла (выполняется всегда после корректуры)
echo ""
echo "Создание HTML из summary файла..."
BASENAME=$(basename "$PDF_FILE" .pdf)
SUMMARY_FILE="$OUTPUT_DIR/${BASENAME}_summary_${SUMMARY_STYLE}.txt"

if [ -f "$SUMMARY_FILE" ]; then
    echo "Создаем HTML файл из summary..."
    python "$SCRIPT_DIR/text_processors/markdown_to_html.py" \
        "$SUMMARY_FILE" \
        -o "${SUMMARY_FILE%.txt}.html" \
        --title "$TITLE"
    
    if [ $? -ne 0 ]; then
        echo "⚠️ Не удалось создать HTML файл"
    else
        echo "✅ HTML файл создан: ${SUMMARY_FILE%.txt}.html"
    fi
else
    echo "⚠️ Файл пересказа не найден: $SUMMARY_FILE. HTML не может быть создан."
fi

# Дополнительный шаг 2: создание промо-описания
echo ""
echo "Доп. шаг 2: Создание промо-описания..."
read -p "Хотите создать промо-описание? (y/n): " -r DO_PROMO
if [[ $DO_PROMO =~ ^[Yy]$ ]]; then
    # Определяем имя файла пересказа
    BASENAME=$(basename "$PDF_FILE" .pdf)
    SUMMARY_FILE="$OUTPUT_DIR/${BASENAME}_summary_${SUMMARY_STYLE}.txt"

    if [ -f "$SUMMARY_FILE" ]; then
        echo "Создаем промо-описание..."
        python "$SCRIPT_DIR/text_processors/promo_description_processor.py" \
            "$OUTPUT_DIR" \
            --source-file "$SUMMARY_FILE" \
            --title "$TITLE" \
            --platform "$PLATFORM" \
            --lang "русский"

        if [ $? -ne 0 ]; then
            echo "⚠️ Не удалось создать промо-описание"
        else
            echo "✅ Промо-описание создано: $OUTPUT_DIR/promo_description.txt"
            
            # Пауза для редактирования промо-описания
            echo ""
            echo "📝 Промо-описание создано. Вы можете отредактировать файл $OUTPUT_DIR/promo_description.txt"
            read -p "Нажмите Enter после завершения редактирования для создания HTML файла..."
            
            # Создание HTML файла из промо-описания
            echo "Создаем HTML файл из промо-описания..."
            python "$SCRIPT_DIR/text_processors/markdown_to_html.py" \
                "$OUTPUT_DIR/promo_description.txt" \
                -o "$OUTPUT_DIR/promo_description.html" \
                --title "$TITLE"
            
            if [ $? -ne 0 ]; then
                echo "⚠️ Не удалось создать HTML файл"
            else
                echo "✅ HTML файл создан: $OUTPUT_DIR/promo_description.html"
            fi
        fi
    else
        echo "⚠️ Файл пересказа не найден: $SUMMARY_FILE. Промо-описание не может быть создано."
    fi
else
    echo "Шаг создания промо-описания пропущен."
fi

# Шаг 2: озвучка
echo ""
echo "Step 2: Озвучка"
echo "Пожалуйста, создайте аудио файл вручную и сохраните как $OUTPUT_DIR/audio.mp3"
read -p "Нажмите Enter после создания аудио..."

# Проверка существования аудио файла
if [ ! -f "$OUTPUT_DIR/audio.mp3" ]; then
    echo "Внимание: файл $OUTPUT_DIR/audio.mp3 не найден. Видео будет создано без озвучки"
    AUDIO_DURATION=""
else
    echo "Определяем длительность аудио..."
    AUDIO_DURATION=$(python "$SCRIPT_DIR/utils/audio_duration.py" "$OUTPUT_DIR/audio.mp3" --format seconds 2>/dev/null)
    if [ -n "$AUDIO_DURATION" ]; then
        echo "Длительность аудио: ${AUDIO_DURATION} секунд"
        # Рассчитываем количество иллюстраций (по 15 секунд на иллюстрацию)
        CALCULATED_PARTS=$(python -c "import math; print(max(4, math.ceil($AUDIO_DURATION / 45)))")
        echo "Рекомендуемое количество иллюстраций: $CALCULATED_PARTS"
        # Обновляем PARTS если рассчитанное значение больше текущего
        if [ "$CALCULATED_PARTS" -gt "$PARTS" ]; then
            echo "Обновляем количество иллюстраций с $PARTS на $CALCULATED_PARTS"
            PARTS=$CALCULATED_PARTS
        fi
    else
        echo "Не удалось определить длительность аудио, используем заданное количество: $PARTS"
        AUDIO_DURATION=""
    fi
fi

echo ""
# Запрашиваем у пользователя, нужен ли ему 3-й шаг (создание описания иллюстраций)
read -p "Хотите пропустить создание описаний иллюстраций? (y/n): " -r REPLY
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Step 3: Создание описания иллюстраций..."
    # Извлекаем имя файла без пути и расширения
    BASENAME=$(basename "$PDF_FILE" .pdf)

    python "$SCRIPT_DIR/video_processors/illustration_prompt_processor.py" \
        "$OUTPUT_DIR/${BASENAME}_summary_${SUMMARY_STYLE}.txt" \
        --parts "$PARTS" \
        --style "$STYLE" \
        -o "$OUTPUT_DIR/illustrations.json"

    if [ $? -ne 0 ]; then
        echo "Ошибка на шаге создания описаний иллюстраций"
        exit 1
    fi
else
    echo "Шаг 3 пропущен (создание описаний иллюстраций)"
fi

# Шаг 4: создание иллюстраций
echo ""
echo "Step 4: Создание иллюстраций..."
while true; do
    python "$SCRIPT_DIR/video_processors/illustration_review_cli.py" \
        --pipeline-dir "$OUTPUT_DIR"
    
    if [ $? -ne 0 ]; then
        echo "Ошибка на шаге создания иллюстраций"
        exit 1
    fi
    
    echo ""
    echo "Проверьте иллюстрации в каталоге $OUTPUT_DIR и при необходимости удалите нежелательные."
    read -p "Хотите пересоздать иллюстрации? (y/n): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        break
    fi
done

# Шаг 5: создание видео
echo ""
echo "Step 5: Создание видео..."
python "$SCRIPT_DIR/video_processors/video_generator.py" \
    --pipeline-dir "$OUTPUT_DIR" 

if [ $? -ne 0 ]; then
    echo "Ошибка на шаге создания видео"
    exit 1
fi

echo ""
echo "Pipeline завершен успешно!"
echo "Результаты в папке: $OUTPUT_DIR"
