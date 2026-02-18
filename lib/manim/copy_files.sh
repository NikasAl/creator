#!/bin/bash

# Функция для копирования файлов в директорию ../pipelines/manim/
manim_step_copy_files() {
    local OUTPUT_DIR_NAME=$(basename "$OUTPUT_DIR")
    local TARGET_DIR="../pipelines/manim/$OUTPUT_DIR_NAME"
    
    if [ -d "$TARGET_DIR" ]; then
        echo -e "\n${YELLOW}📁 Целевая директория $TARGET_DIR уже существует${NC}"
    else
        echo -e "\n${YELLOW}📁 Создание директории $TARGET_DIR${NC}"
        mkdir -p "$TARGET_DIR"
    fi
    
    # Копируем файлы с явным указанием путей в кавычках
    cp -f "$OUTPUT_DIR"/*.py "$TARGET_DIR/" 2>/dev/null || true
    cp -f "$OUTPUT_DIR"/*.md "$TARGET_DIR/" 2>/dev/null || true
    cp -f "$OUTPUT_DIR"/*.jpg "$TARGET_DIR/" 2>/dev/null || true
    
    cd ../pipelines/
    git add .
    git commit -m "$OUTPUT_DIR_NAME"
    git push -u origin master

    echo -e "${GREEN}📋 Файлы скопированы в $TARGET_DIR${NC}"
}