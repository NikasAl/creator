#!/bin/bash

# setup_poetry_manim_pipeline.sh
# Мастер настройки нового пайплайна для Poetry Manim

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🎭 Мастер создания пайплайна Poetry Manim${NC}"
echo "=================================================="

# 1. Название и папки
read -p "Введите название папки пайплайна (напр. моя_песня_1): " PIPELINE_NAME
if [ -z "$PIPELINE_NAME" ]; then
    echo -e "${RED}❌ Название не может быть пустым${NC}"
    exit 1
fi

PIPELINE_DIR="pipelines_poetry/$PIPELINE_NAME"
mkdir -p "$PIPELINE_DIR"
echo -e "${GREEN}📁 Создана директория: $PIPELINE_DIR${NC}"

# 2. Метаданные
read -p "Введите заголовок песни (TITLE): " TITLE
read -p "Введите автора (AUTHOR): " AUTHOR

# 3. Текст песни (song.txt)
SONG_FILE="$PIPELINE_DIR/song.txt"
echo -e "\n${YELLOW}📝 Введите текст песни${NC}"
echo "Открываем редактор для ввода текста песни..."

if command -v subl &> /dev/null; then
    touch "$SONG_FILE"
    echo "Открываем Sublime Text..."
    subl -w "$SONG_FILE"
    if [ ! -s "$SONG_FILE" ]; then
        echo -e "${RED}⚠️ Файл пуст. Вы ничего не сохранили?${NC}"
    fi
elif command -v nano &> /dev/null; then
    nano "$SONG_FILE"
elif command -v vim &> /dev/null; then
    vim "$SONG_FILE"
else
    echo "Ни один из поддерживаемых редакторов не найден. Введите текст вручную (END для конца):"
    > "$SONG_FILE"
    while IFS= read -r line; do
        [[ "$line" == "END" ]] && break
        echo "$line" >> "$SONG_FILE"
    done
fi

# 4. Выбор аудиофайла с использованием fzf
echo -e "\n${YELLOW}🎵 Выберите аудиофайл${NC}"
AUDIO_PATH=""
if command -v fzf &> /dev/null; then
    echo "Используем fzf для выбора аудиофайла из ~/Downloads..."
    AUDIO_PATH=$(find ~/Downloads -type f \( -iname "*.mp3" \) 2>/dev/null | fzf --height=40% --reverse --prompt="Выберите аудиофайл: ")
    
    if [ -n "$AUDIO_PATH" ] && [ -f "$AUDIO_PATH" ]; then
        echo -e "${GREEN}✅ Выбран аудиофайл: $AUDIO_PATH${NC}"
        # Копируем аудиофайл в папку пайплайна
        AUDIO_FILE="audio.mp3"
        mv "$AUDIO_PATH" "$PIPELINE_DIR/$AUDIO_FILE"
        echo -e "${GREEN}✅ Аудиофайл скопирован в $PIPELINE_DIR/$AUDIO_FILE${NC}"
        AUDIO_FILE_RELATIVE="$AUDIO_FILE"
    else
        echo -e "${YELLOW}⚠️ Аудиофайл не выбран, будет использован placeholder.${NC}"
        AUDIO_FILE_RELATIVE="audio.mp3"
        touch "$PIPELINE_DIR/$AUDIO_FILE_RELATIVE"
    fi
else
    echo -e "${YELLOW}⚠️ fzf не найден, установите его ${NC}"
    exit 1
fi

# 5. Создание конфига
CONFIG_DIR="configs/poetry"
mkdir -p "$CONFIG_DIR"
CONFIG_FILE="$CONFIG_DIR/${PIPELINE_NAME}.conf"

cat > "$CONFIG_FILE" << EOF
# Конфигурация для обработки поэзии

# Обязательные параметры
BASE_DIR="$PIPELINE_DIR"
TITLE="$TITLE"
AUTHOR="$AUTHOR"

# Необязательные параметры (будут использованы значения по умолчанию если не указаны)
# Все пути указываются относительно BASE_DIR
INPUT_FILE="song.txt"
AUDIO_FILE="$AUDIO_FILE_RELATIVE"
STYLE="Карикатурный рисунок цветными карандашами"
ERA="21 век"
REGION="Россия"
GENRE="Песня"
SETTING="По умолчанию"
SECONDS_PER_ILLUSTRATION="10"

# Необязательные параметры промо-описания (используются в process_poetry.sh)
# PROMO_PREFIX — фильтр файлов по последнему токену имени (например, "summary")
# PROMO_MODEL — one of: default | budget | quality
# PROMO_AUDIENCE — целевая аудитория
# PROMO_TONE — тональность текста
# PROMO_PLATFORM — платформа публикации (YouTube, VK, Telegram и т.д.)
# PROMO_LANG — язык результата
# PROMO_TITLE — заголовок (по умолчанию берется из TITLE)
# PROMO_SOURCE_FILE — путь к одному исходному .txt файлу для контекста (относительно BASE_DIR)
# Примеры (раскомментируйте и отредактируйте при необходимости):
# PROMO_PREFIX="summary"
# PROMO_MODEL="quality"
# PROMO_AUDIENCE="широкая аудитория"
# PROMO_TONE="вдохновляющий"
# PROMO_PLATFORM="YouTube"
# PROMO_LANG="русский"
# PROMO_TITLE="В тот год осенняя погода..."
PROMO_SOURCE_FILE="song.txt"

# Параметры редактирования изображений (необязательные)
# IMAGE_EDIT_MODEL — модель для редактирования изображений
# Поддерживаемые модели:
#   - "google/gemini-2.5-flash-image" — через OpenRouter (требует OPENROUTER_API_KEY)
#   - "qwen-image-edit-plus" или "Qwen-Image-Edit" — через Alibaba (требует ALIBABA_API_KEY)
#   - "none" или не указано — редактирование отключено
# Примеры (раскомментируйте и отредактируйте при необходимости):
# IMAGE_EDIT_MODEL="qwen-image-edit-plus"
# IMAGE_EDIT_MODEL="google/gemini-2.5-flash-image"
EOF

echo -e "\n${GREEN}🎉 Пайплайн настроен!${NC}"
echo "Для запуска: ./process_poetry_manim.sh $CONFIG_FILE"