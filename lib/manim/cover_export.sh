#!/bin/bash

# cover_export.sh
# Функции для экспорта обложки видео

# === ФУНКЦИЯ ЭКСПОРТА ОБЛОЖКИ ===
export_cover() {
    local output_dir="$1"
    local output_video_file="$2"
    local cover_file="$3"
    local total_steps="$4"

    echo -e "\n${YELLOW}[8/$total_steps] Создание обложки...${NC}"

    if [ -f "$cover_file" ]; then
        echo "✅ Обложка уже существует: $cover_file"
        return 0
    fi

    read -p "Обложка не найдена. Создать обложку? (y/n): " create_cover
    if [[ "$create_cover" =~ ^[Yy] ]]; then
        if [ ! -f "$output_video_file" ]; then
            echo -e "${RED}❌ Финальное видео не найдено: $output_video_file${NC}"
            echo "Пожалуйста, сначала завершите синхронизацию видео."
            return 1
        else
            echo -e "${GREEN}ℹ️  Открывается видео в mpv. Используйте PrintScreen для создания скриншота.${NC}"
            echo -e "${GREEN}ℹ️  Для этого вам понадобится maim и xclip.${NC}"
            echo -e "${GREEN}ℹ️  После создания скриншота закройте mpv.${NC}"

            # Проверяем наличие необходимых утилит
            if ! command -v maim >/dev/null 2>&1; then
                echo -e "${RED}❌ maim не найден. Установите его: sudo apt install maim${NC}"
                return 1
            elif ! command -v xclip >/dev/null 2>&1; then
                echo -e "${RED}❌ xclip не найден. Установите его: sudo apt install xclip${NC}"
                return 1
            else
                # Открываем видео в mpv
                echo -e "${GREEN}ℹ️  Управление: перемещайтесь по видео, затем закройте окно.${NC}"
                echo -e "${YELLOW}ℹ️  После закрытия mpv создайте скриншот нужного кадра с помощью PrintScreen или команды:${NC}"
                echo -e "${YELLOW}maim -s | xclip -selection clipboard -t image/png${NC}"

                mpv --loop-file=no -- "$output_video_file"

                # Теперь пользователь должен создать скриншот нужного кадра
                echo -e "${YELLOW}ℹ️  Создайте скриншот нужного кадра командой:${NC}"
                echo -e "${YELLOW}maim -s | xclip -selection clipboard -t image/png${NC}"
                echo -e "${YELLOW}ℹ️  Или используйте клавишу PrintScreen, если она настроена в вашей системе.${NC}"
                read -p "Нажмите Enter после создания скриншота в буфер обмена..."

                # Пытаемся получить изображение из буфера обмена, созданное через maim + xclip
                if xclip -selection clipboard -t image/png -o > "$output_dir/clipboard_image.png" 2>/dev/null; then
                    if [ -s "$output_dir/clipboard_image.png" ]; then
                        # Convert PNG to JPG using ImageMagick convert
                        if command -v magick >/dev/null 2>&1; then
                            magick "$output_dir/clipboard_image.png" "$cover_file"
                            rm "$output_dir/clipboard_image.png"  # Clean up temporary PNG file
                            echo -e "${GREEN}✅ Обложка сохранена из буфера обмена: $cover_file${NC}"
                        else
                            echo -e "${RED}❌ convert не найден. Установите ImageMagick: sudo apt install imagemagick${NC}"
                            rm -f "$output_dir/clipboard_image.png"
                            return 1
                        fi
                    else
                        echo -e "${RED}❌ Изображение в буфере обмена пустое${NC}"
                        rm -f "$output_dir/clipboard_image.png"

                        # Альтернативный способ: запросить у пользователя создание скриншота области напрямую
                        echo -e "${YELLOW}Попробуйте создать скриншот сами${NC}"
                        return 1
                    fi
                else
                    # Альтернативный способ: запросить у пользователя создание скриншота области напрямую
                    echo -e "${YELLOW}Попробуйте создать скриншот сами${NC}"
                    return 1
                fi
            fi
        fi
    else
        echo "ℹ️  Пропуск создания обложки."
    fi
}