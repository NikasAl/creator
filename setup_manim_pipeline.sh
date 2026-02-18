#!/bin/bash

# setup_manim_pipeline.sh
# Мастер настройки нового пайплайна для Manim (Problem Solving Workflow)

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🎬 Мастер создания пайплайна Manim (Задача -> Решение)${NC}"
echo "============================================================"

# 1. Название и папки
read -p "Введите название папки пайплайна (напр. math_geometry_1): " PIPELINE_NAME
if [ -z "$PIPELINE_NAME" ]; then
    echo -e "${RED}❌ Название не может быть пустым${NC}"
    exit 1
fi

PIPELINE_DIR="pipelines_manim/$PIPELINE_NAME"
mkdir -p "$PIPELINE_DIR"
echo -e "${GREEN}📁 Создана директория: $PIPELINE_DIR${NC}"

# 2. Метаданные
read -p "Введите заголовок урока (TITLE): " TITLE
read -p "Введите автора (AUTHOR): " AUTHOR

# 3. Спецификация (Spec) через Sublime
SPEC_FILE="$PIPELINE_DIR/spec.md"
echo -e "\n${YELLOW}📝 Шаг 1: Описание задачи (spec.md)${NC}"
echo "Опишите задачу, ваши затруднения и ход мыслей."

if command -v subl &> /dev/null; then
    touch "$SPEC_FILE"
    echo "Открываем Sublime Text..."
    subl -w "$SPEC_FILE"
    if [ ! -s "$SPEC_FILE" ]; then
        echo -e "${RED}⚠️ Файл пуст. Вы ничего не сохранили?${NC}"
    fi
else
    echo "Sublime Text не найден. Введите текст вручную (END для конца):"
    > "$SPEC_FILE"
    while IFS= read -r line; do
        [[ "$line" == "END" ]] && break
        echo "$line" >> "$SPEC_FILE"
    done
fi

# 4. Изображение задачи
echo -e "\n${YELLOW}🖼️ Шаг 2: Изображение задачи (spec.jpg/png)${NC}"
read -p "Путь к файлу (Enter чтобы пропустить): " IMG_PATH
if [ -n "$IMG_PATH" ]; then
    IMG_PATH=$(echo "$IMG_PATH" | tr -d "'\"") # Удаляем кавычки
    if [ -f "$IMG_PATH" ]; then
        EXT="${IMG_PATH##*.}"
        cp "$IMG_PATH" "$PIPELINE_DIR/spec.$EXT"
        echo -e "${GREEN}✅ Изображение скопировано${NC}"
    else
        echo -e "${RED}❌ Файл не найден${NC}"
    fi
fi

# 5. Референсный код (Style Reference)
echo -e "\n${YELLOW}🧬 Шаг 3: Пример стиля (Reference Code)${NC}"
SOLUTIONS_DIR="manim_processors/solutions"
EXAMPLE_DEST="$PIPELINE_DIR/manim_example.py"

if [ -d "$SOLUTIONS_DIR" ]; then
    echo "Выберите файл-пример из $SOLUTIONS_DIR:"
    select filename in "$SOLUTIONS_DIR"/*.py; do
        if [ -n "$filename" ]; then
            cp "$filename" "$EXAMPLE_DEST"
            echo -e "${GREEN}✅ Референс скопирован: $(basename "$filename")${NC}"
            break
        else
            echo "Неверный выбор"
        fi
    done
else
    echo -e "${YELLOW}Папка решений не найдена, создаем пустой пример.${NC}"
    touch "$EXAMPLE_DEST"
fi

# 6. Создание конфига
CONFIG_DIR="configs/manim"
mkdir -p "$CONFIG_DIR"
CONFIG_FILE="$CONFIG_DIR/${PIPELINE_NAME}.conf"

cat > "$CONFIG_FILE" << EOF
# Config for: $TITLE
BASE_DIR="$PIPELINE_DIR"
TITLE="$TITLE"
AUTHOR="$AUTHOR"
LANGUAGE="ru"

# Модели
SCRIPT_MODEL="custom"    # Генерация текста урока (GPT-4o / Claude 3.5)
CODE_MODEL="custom"      # Генерация кода Manim
PROMO_MODEL="default"     # Генерация промо

# Флаги рендеринга
QUALITY="low"             # low, medium, high, 4k
EOF

echo -e "\n${GREEN}🎉 Пайплайн настроен!${NC}"
echo "Для запуска: ./process_manim.sh $CONFIG_FILE"