#!/bin/bash

# Скрипт для обработки стихов с автоматическим определением длительности аудио
# Использование: ./process_poetry.sh [config_file]
# Если config_file не указан, запускается интерактивный режим создания.

# Функция для интерактивного создания конфига
create_interactive_config() {
    echo "=========================================="
    echo "✨ Мастер создания новой конфигурации ✨"
    echo "=========================================="

    # 1. Имя файла конфигурации
    while true; do
        read -p "Введите имя для файла конфига (например, my_song): " conf_name
        if [ -n "$conf_name" ]; then
            break
        fi
        echo "❌ Имя не может быть пустым."
    done

    # Убираем расширение .conf если пользователь его ввел случайно
    conf_name="${conf_name%.conf}"
    CONFIG_DIR="configs/poetry"
    mkdir -p "$CONFIG_DIR"
    NEW_CONFIG_PATH="$CONFIG_DIR/${conf_name}.conf"

    echo ""
    echo "📂 Параметры проекта:"

    # 2. Базовая директория
    default_base="pipelines_poetry/$conf_name"
    read -p "Папка проекта (по умолчанию: $default_base): " input_base
    BASE_DIR="${input_base:-$default_base}"

    # 3. Заголовок
    read -p "Название произведения (TITLE): " input_title
    TITLE="${input_title:-$conf_name}"

    # 4. Автор
    read -p "Автор (AUTHOR) (по умолчанию: Gemini): " input_author
    AUTHOR="${input_author:-Gemini}"

    echo ""
    echo "🎨 Настройки стиля:"

    # 5. Стиль
    read -p "Стиль иллюстраций (по умолчанию: Реалистичный): " input_style
    STYLE="${input_style:-Реалистичный}"

    # 6. Эпоха
    read -p "Эпоха (по умолчанию: Современность): " input_era
    ERA="${input_era:-Современность}"

    # 7. Жанр
    read -p "Жанр (по умолчанию: Песня): " input_genre
    GENRE="${input_genre:-Песня}"

    # 8. Сеттинг
    read -p "Сеттинг/Атмосфера (по умолчанию: Яркие цвета, жизнь): " input_setting
    SETTING="${input_setting:-Яркие цвета, жизнь}"

echo ""
    echo "⚙️  Подготовка файлов:"

    # Создаем директорию проекта прямо сейчас, чтобы положить туда файлы
    if [ ! -d "$BASE_DIR" ]; then
        mkdir -p "$BASE_DIR"
        echo "   📁 Создана папка: $BASE_DIR"
    fi

    # 9. Текстовый файл (Hardcoded song.txt + Sublime)
    INPUT_FILE_NAME="song.txt"
    TEXT_FILE_PATH="$BASE_DIR/$INPUT_FILE_NAME"

    echo "   📝 Открываю Sublime Text для ввода текста..."
    # Создаем пустой файл, чтобы Sublime мог его открыть
    touch "$TEXT_FILE_PATH"

    # Пробуем открыть в subl, если нет - fallback на nano или просто сообщение
    if command -v subl >/dev/null; then
        subl "$TEXT_FILE_PATH"
        echo "      👉 Вставьте текст песни в открывшееся окно и сохраните файл."
        read -p "      Нажмите [Enter], когда закончите редактирование..." dummy
    else
        echo "      ⚠️ Sublime Text (subl) не найден."
        echo "      Пожалуйста, создайте файл $TEXT_FILE_PATH вручную."
        read -p "      Нажмите [Enter] для продолжения..." dummy
    fi

    # 10. Аудио файл (Hardcoded audio.mp3 + fzf из Downloads)
    AUDIO_FILE_NAME="audio.mp3"
    AUDIO_FILE_PATH="$BASE_DIR/$AUDIO_FILE_NAME"

    echo ""
    echo "   🎵 Выбор аудиофайла..."

    if command -v fzf >/dev/null; then
        echo "      Ищу MP3 файлы в ~/Downloads..."
        # Ищем mp3 в загрузках, сортируем по времени (новые сверху) и даем выбрать через fzf
        SELECTED_MP3=$(find ~/Downloads -maxdepth 2 -name "*.mp3" -type f -printf "%T@ %p\n" 2>/dev/null | sort -rn | cut -d' ' -f2- | fzf --prompt="Выберите трек > " --height=15 --layout=reverse)

        if [ -n "$SELECTED_MP3" ]; then
            echo "      ✅ Выбран файл: $(basename "$SELECTED_MP3")"
            cp "$SELECTED_MP3" "$AUDIO_FILE_PATH"
            echo "      📋 Скопирован в: $AUDIO_FILE_PATH"
        else
            echo "      ⚠️ Файл не выбран. Вам придется добавить audio.mp3 в папку проекта вручную."
        fi
    else
        echo "      ⚠️ Утилита fzf не установлена. Автоматический выбор невозможен."
        echo "      Пожалуйста, скопируйте нужный mp3 файл в $AUDIO_FILE_PATH вручную."
    fi

    # Генерация содержимого файла
    cat > "$NEW_CONFIG_PATH" <<EOF
# Конфигурация: $TITLE
# Создана: $(date)

# Обязательные параметры
BASE_DIR="$BASE_DIR"
TITLE="$TITLE"
AUTHOR="$AUTHOR"

# Необязательные параметры
INPUT_FILE="$INPUT_FILE_NAME"
AUDIO_FILE="$AUDIO_FILE_NAME"
STYLE="$STYLE"
ERA="$ERA"
REGION="Россия"
GENRE="$GENRE"
SETTING="$SETTING"
SECONDS_PER_ILLUSTRATION="10"

# Параметры промо (примеры)
# PROMO_MODEL="default"
# PROMO_PLATFORM="YouTube"
PROMO_SOURCE_FILE="$INPUT_FILE_NAME"

# Параметры редактирования изображений
# IMAGE_EDIT_MODEL="none"
EOF

    echo ""
    echo "✅ Конфигурация сохранена: $NEW_CONFIG_PATH"
    echo "📁 Не забудьте положить файлы '$INPUT_FILE_NAME' и '$AUDIO_FILE_NAME' в папку: $BASE_DIR"
    echo "   (Скрипт создаст папку, если она не существует, но файлы нужно добавить вручную)"
    echo "------------------------------------------"
    echo ""

    # Возвращаем путь к новому файлу
    echo "$NEW_CONFIG_PATH"
}

# --- Основная логика выбора конфига ---

if [ $# -eq 0 ]; then
    # Аргументов нет — запускаем интерактивный режим
    CONFIG_FILE=$(create_interactive_config | tail -n1)

    # Спрашиваем, хотим ли продолжить выполнение
    read -p "🚀 Хотите запустить обработку с этим конфигом прямо сейчас? (y/n): " run_now
    if [[ ! "$run_now" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo "Выход. Запустите позже командой: $0 $CONFIG_FILE"
        exit 0
    fi

    # Проверяем наличие входных файлов перед запуском, так как мы только что создали конфиг
    # Читаем BASE_DIR из только что созданного конфига (грубый парсинг для проверки)
    CHECK_BASE_DIR=$(grep '^BASE_DIR=' "$CONFIG_FILE" | cut -d'"' -f2)
    CHECK_INPUT=$(grep '^INPUT_FILE=' "$CONFIG_FILE" | cut -d'"' -f2)

    if [ ! -f "$CHECK_BASE_DIR/$CHECK_INPUT" ]; then
        echo ""
        echo "⚠️  Внимание: Файл с текстом не найден!"
        echo "   Ожидается: $CHECK_BASE_DIR/$CHECK_INPUT"
        echo "   Пожалуйста, создайте этот файл перед продолжением, иначе скрипт упадет."
        read -p "Нажмите Enter, когда файл будет добавлен, или Ctrl+C для отмены..." dummy
    fi

else
    CONFIG_FILE="$1"
fi

# Проверка существования конфигурационного файла
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Ошибка: конфигурационный файл $CONFIG_FILE не найден"
    exit 1
fi

# Загрузка конфигурации
source "$CONFIG_FILE"

# Проверка обязательных параметров
if [ -z "$BASE_DIR" ] || [ -z "$TITLE" ] || [ -z "$AUTHOR" ]; then
    echo "Ошибка: не все обязательные параметры заданы в конфигурационном файле"
    echo "Обязательные параметры: BASE_DIR, TITLE, AUTHOR"
    exit 1
fi

# Установка значений по умолчанию для необязательных параметров
INPUT_FILE="${INPUT_FILE:-song.txt}"
OUTPUT_DIR="$BASE_DIR"
AUDIO_FILE="${AUDIO_FILE:-audio.mp3}"
STYLE="${STYLE:-Реалистичный}"
ERA="${ERA:-19 век}"
REGION="${REGION:-Россия}"
GENRE="${GENRE:-Поэзия}"
SETTING="${SETTING:-Сказка.}"
SECONDS_PER_ILLUSTRATION="${SECONDS_PER_ILLUSTRATION:-8}"

# Параметры промо-описания (необязательные)
PROMO_PREFIX="${PROMO_PREFIX:-}"
PROMO_MODEL="${PROMO_MODEL:-default}"
PROMO_AUDIENCE="${PROMO_AUDIENCE:-широкая аудитория}"
PROMO_TONE="${PROMO_TONE:-дружелюбный и информативный}"
PROMO_PLATFORM="${PROMO_PLATFORM:-YouTube}"
PROMO_LANG="${PROMO_LANG:-русский}"
PROMO_TITLE="${PROMO_TITLE:-$TITLE}"
PROMO_SOURCE_FILE="${PROMO_SOURCE_FILE:-}"

# Параметры редактирования изображений (необязательные)
IMAGE_EDIT_MODEL="${IMAGE_EDIT_MODEL:-none}"

# Формируем полные пути относительно BASE_DIR
INPUT_FILE="$BASE_DIR/$INPUT_FILE"
AUDIO_FILE="$BASE_DIR/$AUDIO_FILE"

echo "🎭 Обработка бардовой песни: $TITLE"
echo "======================================"
echo "📁 Базовая директория: $BASE_DIR"
echo "📄 Входной файл: $INPUT_FILE"
echo "🎵 Аудио файл: $AUDIO_FILE"
echo "👤 Автор: $AUTHOR"
echo "🎨 Стиль: $STYLE"
echo "⏱️ Секунд на иллюстрацию: $SECONDS_PER_ILLUSTRATION"
if [ "$IMAGE_EDIT_MODEL" != "none" ]; then
    echo "🖼️ Модель редактирования изображений: $IMAGE_EDIT_MODEL"
fi
echo ""

# Проверка входного файла
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Входной файл не найден: $INPUT_FILE"
    exit 1
fi

# Создание выходного каталога
mkdir -p "$OUTPUT_DIR"

# Определение длительности аудио
if [ -f "$AUDIO_FILE" ]; then
    echo "🔍 Определяем длительность аудио..."
    AUDIO_DURATION=$(python utils/audio_duration.py "$AUDIO_FILE" --format seconds 2>/dev/null)

    if [ -n "$AUDIO_DURATION" ]; then
        echo "✅ Длительность аудио: ${AUDIO_DURATION} секунд"

        # Рассчитываем количество иллюстраций
        CALCULATED_PARTS=$(python -c "import math; print(max(4, math.ceil($AUDIO_DURATION / $SECONDS_PER_ILLUSTRATION)))")
        echo "📊 Рекомендуемое количество иллюстраций: $CALCULATED_PARTS (по ${SECONDS_PER_ILLUSTRATION}с)"

        # Используем рассчитанное количество, но не меньше 8
        PARTS=$((CALCULATED_PARTS < 8 ? 8 : CALCULATED_PARTS))
        echo "🎯 Финальное количество иллюстраций: $PARTS"
    else
        echo "⚠️ Не удалось определить длительность аудио, выход"
        exit
    fi
fi

echo ""
echo "📖 Создание описаний иллюстраций..."

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
else
    skip_illustration_gen=false
fi

# Выполняем генерацию только если не пропущена
if [ "$skip_illustration_gen" = false ]; then
    # Формируем команду для процессора
    ILLUSTRATION_CMD="python video_processors/illustration_prompt_processor_v2.py \
        \"$INPUT_FILE\" \
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
else
    # Если пропустили генерацию, успех всё равно считаем
    true
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
        ILLUSTRATION_COUNT=$(python -c "import json; data=json.load(open('$OUTPUT_DIR/illustrations.json')); print(len(data.get('illustrations', [])))")
        SCRIPT_COUNT=$(python -c "import json; data=json.load(open('$OUTPUT_DIR/illustrations.json')); print(len(data.get('script', [])))")
        echo ""
        echo "📊 Статистика:"
        echo "   - Создано иллюстраций: $ILLUSTRATION_COUNT"
        echo "   - Сценарий содержит: $SCRIPT_COUNT сцен"
    fi

    echo ""
    echo "🎬 Следующий шаг: создание иллюстраций"
    echo "python video_processors/illustration_review_cli.py --pipeline-dir $OUTPUT_DIR"

    # Шаг 1: Создание иллюстраций
    echo ""
    echo "🖼️ Хотите создать иллюстрации?"
    read -p "Введите 'y' или 'yes' для создания иллюстраций: " create_illustrations

    if [[ "$create_illustrations" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        while true; do
            echo ""
            echo "🎨 Создание иллюстраций..."
            python video_processors/illustration_review_cli.py --pipeline-dir "$OUTPUT_DIR"

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

    # Шаг 2: Опциональная перегенерация фото через Alibaba
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
                python video_processors/alibaba_image_generator.py \
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

    # Шаг 3: Редактирование изображений
    if [ "$IMAGE_EDIT_MODEL" != "none" ]; then
        echo ""
        echo "✏️ Хотите отредактировать изображения?"
        read -p "Введите 'y' или 'yes' для редактирования изображений: " edit_images

        if [[ "$edit_images" =~ ^[Yy]([Ee][Ss])?$ ]]; then
            while true; do
                echo ""
                echo "📋 Доступные изображения в $OUTPUT_DIR/images:"
                ls -la "$OUTPUT_DIR/images/illustration_*.png" 2>/dev/null | head -20

                echo ""
                read -p "Введите номер изображения для редактирования: " base_image_index

                if [ -z "$base_image_index" ] || [[ ! "$base_image_index" =~ ^[0-9]+$ ]]; then
                    echo "❌ Неверный номер изображения"
                else
                    echo ""
                    read -p "Введите номер референсного изображения (или Enter чтобы пропустить): " ref_image_index

                    echo ""
                    echo "Быстрые варианты редактирования:"
                    echo "  1) Заменить лицо"
                    echo "  2) Заменить человека"
                    echo "  3) Скопировать стиль со второй картинки"
                    echo "  4) Ввести свой промпт"
                    read -p "Выберите вариант (1-4): " prompt_choice

                    case "$prompt_choice" in
                        1)
                            if [ -n "$ref_image_index" ]; then
                                edit_prompt="Заменить лицо на изображении на лицо с референсного изображения"
                            else
                                edit_prompt="Заменить лицо на изображении"
                            fi
                            ;;
                        2)
                            if [ -n "$ref_image_index" ]; then
                                edit_prompt="Заменить человека на изображении на человека с референсного изображения"
                            else
                                edit_prompt="Заменить человека на изображении"
                            fi
                            ;;
                        3)
                            if [ -n "$ref_image_index" ]; then
                                edit_prompt="Скопировать стиль со второй картинки, сохранив композицию первой"
                            else
                                edit_prompt="Изменить стиль изображения"
                            fi
                            ;;
                        4)
                            echo ""
                            read -p "Введите промпт для редактирования: " edit_prompt
                            ;;
                        *)
                            echo "⚠️ Неверный выбор, используем стандартный промпт"
                            if [ -n "$ref_image_index" ]; then
                                edit_prompt="Отредактируй изображение согласно референсному изображению"
                            else
                                edit_prompt="Отредактируй изображение согласно описанию"
                            fi
                            ;;
                    esac

                    if [ -z "$edit_prompt" ]; then
                        if [ -n "$ref_image_index" ]; then
                            edit_prompt="Отредактируй изображение согласно референсному изображению"
                        else
                            edit_prompt="Отредактируй изображение согласно описанию"
                        fi
                    fi

                    echo ""
                    echo "🎨 Редактирование изображения $base_image_index..."
                    if [ -n "$ref_image_index" ]; then
                        echo "   Референсное изображение: $ref_image_index"
                    fi
                    echo "   Промпт: $edit_prompt"

                    # Определяем провайдер по модели
                    if [[ "$IMAGE_EDIT_MODEL" == *"gemini"* ]] || [[ "$IMAGE_EDIT_MODEL" == *"google"* ]]; then
                        # OpenRouter
                        EDIT_CMD=(
                            python image_generators/image_editor_openrouter.py
                            --pipeline-dir "$OUTPUT_DIR"
                            --base-image-index "$base_image_index"
                            --edit-prompt "$edit_prompt"
                        )
                        if [ -n "$ref_image_index" ]; then
                            EDIT_CMD+=(--reference-image-index "$ref_image_index")
                        fi
                    elif [[ "$IMAGE_EDIT_MODEL" == *"qwen"* ]] || [[ "$IMAGE_EDIT_MODEL" == *"Qwen"* ]]; then
                        # Alibaba
                        EDIT_CMD=(
                            python image_generators/image_editor_alibaba.py
                            --pipeline-dir "$OUTPUT_DIR"
                            --base-image-index "$base_image_index"
                            --edit-prompt "$edit_prompt"
                        )
                        if [ -n "$ref_image_index" ]; then
                            EDIT_CMD+=(--reference-image-index "$ref_image_index")
                        fi
                    else
                        echo "❌ Неизвестная модель редактирования: $IMAGE_EDIT_MODEL"
                        echo "   Поддерживаются модели: google/gemini-2.5-flash-image (OpenRouter) или Qwen-Image-Edit (Alibaba)"
                        break
                    fi

                    echo "🚀 Запуск команды:"
                    printf '%q ' "${EDIT_CMD[@]}"; echo
                    echo ""

                    "${EDIT_CMD[@]}"

                    if [ $? -eq 0 ]; then
                        echo "✅ Изображение отредактировано успешно!"
                    else
                        echo "❌ Ошибка при редактировании изображения"
                    fi
                fi

                echo ""
                read -p "Хотите отредактировать еще одно изображение? (y/n): " -r
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    break
                fi
            done
        fi
    fi

    # Шаг 4: Создание обложки
    echo ""
    echo "🖼️ Хотите создать обложку для ролика?"
    read -p "Введите 'y' или 'yes' для создания обложки: " create_cover

    if [[ "$create_cover" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo ""
        echo "🎨 Создание обложки..."

        # Проверяем наличие директории images
        if [ -d "$OUTPUT_DIR/images" ]; then
            # Запускаем make_cover.py в интерактивном режиме
            python image_generators/make_cover.py "$OUTPUT_DIR"

            if [ $? -eq 0 ]; then
                echo "✅ Обложка создана успешно!"
            else
                echo "❌ Ошибка при создании обложки"
            fi
        else
            echo "⚠️ Директория images не найдена в $OUTPUT_DIR"
            echo "Сначала создайте иллюстрации с помощью:"
            echo "python video_processors/illustration_review_cli.py --pipeline-dir $OUTPUT_DIR"
        fi
    fi


    # Шаг 5: Генерация видео по номеру иллюстрации
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
                python video_processors/alibaba_video_generator.py \
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

    # Шаг 6: Финальная генерация видео
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

        python video_processors/video_generator.py \
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

    # Шаг 7: Создание вертикальных шортов
    echo ""
    echo "🎞️ Хотите создать вертикальные шорты из финального видео?"
    read -p "Введите 'y' или 'yes' для создания шортов: " create_shorts

    if [[ "$create_shorts" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        FINAL_VIDEO_PATH="$OUTPUT_DIR/video.mp4"
        if [ -f "$FINAL_VIDEO_PATH" ]; then
            SHORTS_DIR="$OUTPUT_DIR/shorts"
            mkdir -p "$SHORTS_DIR"
            while true; do
                echo ""
                read -p "Введите начальное время (мм:сс) или оставьте пустым для выхода: " short_start
                if [ -z "$short_start" ]; then
                    break
                fi
                if [[ ! "$short_start" =~ ^[0-9]{1,2}:[0-9]{2}$ ]]; then
                    echo "❌ Неверный формат времени. Используйте формат мм:сс"
                    continue
                fi

                read -p "Введите конечное время (мм:сс): " short_end
                if [ -z "$short_end" ]; then
                    echo "❌ Конечное время не может быть пустым"
                    continue
                fi
                if [[ ! "$short_end" =~ ^[0-9]{1,2}:[0-9]{2}$ ]]; then
                    echo "❌ Неверный формат времени. Используйте формат мм:сс"
                    continue
                fi

                read -p "Введите имя файла шорта (без расширения, по умолчанию auto): " short_name
                if [ -z "$short_name" ]; then
                    start_safe=${short_start//:/-}
                    end_safe=${short_end//:/-}
                    short_name="short_${start_safe}_${end_safe}"
                fi
                short_output="$SHORTS_DIR/${short_name}.mp4"

                echo ""
                echo "🎬 Создание шорта $short_name..."
                echo "   Источник: $FINAL_VIDEO_PATH"
                echo "   Период: $short_start – $short_end"
                echo "   Выход: $short_output"
                ./video_processors/crop_vertical.sh "$FINAL_VIDEO_PATH" "$short_start" "$short_end" "$short_output"

                if [ $? -eq 0 ]; then
                    echo "✅ Шорт создан: $short_output"
                else
                    echo "❌ Ошибка при создании шорта"
                fi

                echo ""
                read -p "Хотите создать еще один шорт? (y/n): " -r
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    break
                fi
            done
        else
            echo "⚠️ Финальное видео не найдено: $FINAL_VIDEO_PATH"
            echo "   Сначала создайте финальное видео (Шаг 6)."
        fi
    fi

    # Шаг 8: Создание промо-описания
    echo ""
    echo "📝 Хотите создать промо-описание для публикации?"
    read -p "Введите 'y' или 'yes' для создания промо-описания: " create_promo

    if [[ "$create_promo" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo ""
        echo "🧩 Создание промо-описания..."
        # Формируем команду как массив для корректного экранирования аргументов
        PROMO_CMD=(
            python text_processors/promo_description_processor.py "$OUTPUT_DIR"
            --config config.env
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
            PROMO_CMD+=(--source-file "$PROMO_SOURCE_PATH")
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

else
    echo "❌ Ошибка при создании описаний иллюстраций"
    exit 1
fi
