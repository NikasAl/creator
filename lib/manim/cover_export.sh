#!/bin/bash

# cover_export.sh
# Функции для экспорта обложки видео

# === Вспомогательная функция: определить Wayland или X11 ===
_is_wayland() {
    [ -n "$WAYLAND_DISPLAY" ] || [ -n "$XDG_SESSION_TYPE" ] && [ "$XDG_SESSION_TYPE" = "wayland" ]
}

# === Вспомогательная функция: получить изображение из буфера обмена ===
_paste_from_clipboard() {
    local output_file="$1"

    if _is_wayland; then
        # Wayland: wl-paste
        if command -v wl-paste >/dev/null 2>&1; then
            wl-paste --type image/png > "$output_file" 2>/dev/null && return 0
        fi
    fi

    # X11: xclip
    if command -v xclip >/dev/null 2>&1; then
        xclip -selection clipboard -t image/png -o > "$output_file" 2>/dev/null && return 0
    fi

    return 1
}

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
    if [[ ! "$create_cover" =~ ^[Yy] ]]; then
        echo "ℹ️  Пропуск создания обложки."
        return 0
    fi

    if [ ! -f "$output_video_file" ]; then
        echo -e "${RED}❌ Финальное видео не найдено: $output_video_file${NC}"
        echo "Пожалуйста, сначала завершите синхронизацию видео."
        return 1
    fi

    # Определяем доступные инструменты скриншота
    if _is_wayland; then
        if ! command -v grim >/dev/null 2>&1; then
            echo -e "${RED}❌ grim не найден. Установите: sudo apt install grim${NC}"
            return 1
        fi
        if ! command -v wl-paste >/dev/null 2>&1; then
            echo -e "${RED}❌ wl-paste не найден. Установите: sudo apt install wl-clipboard${NC}"
            return 1
        fi
        echo -e "${GREEN}ℹ️  Обнаружен Wayland. Используются grim + wl-paste.${NC}"
    else
        if ! command -v maim >/dev/null 2>&1; then
            echo -e "${RED}❌ maim не найден. Установите: sudo apt install maim${NC}"
            return 1
        fi
        if ! command -v xclip >/dev/null 2>&1; then
            echo -e "${RED}❌ xclip не найден. Установите: sudo apt install xclip${NC}"
            return 1
        fi
        echo -e "${GREEN}ℹ️  Обнаружен X11. Используются maim + xclip.${NC}"
    fi

    echo ""
    echo -e "${GREEN}🎬 Открывается видео в mpv.${NC}"
    echo -e "${YELLOW}📋 Инструкция:${NC}"
    if _is_wayland; then
        echo "   1. В mpv нажмите 's' для скриншота текущего кадра"
        echo "      (сохранится в ~/Pictures/ или текущую директорию)"
        echo "   2. ЛИБО нажмите PrintScreen для скриншота всей области"
        echo "   3. Закройте mpv"
    else
        echo "   1. В mpv нажмите 's' для скриншота текущего кадра"
        echo "      (сохранится в ~/Pictures/ или текущую директорию)"
        echo "   2. ЛИБО выполните в другом терминале:"
        echo "      maim -s | xclip -selection clipboard -t image/png"
        echo "   3. Закройте mpv"
    fi
    echo ""

    mpv --loop-file=no -- "$output_video_file"

    # Спросим пользователя — есть ли скриншот в буфере?
    read -p "Сделали скриншот в буфер обмена? (y/n): " has_clipboard
    if [[ "$has_clipboard" =~ ^[Yy] ]]; then
        CLIPBOARD_IMG="$output_dir/clipboard_image.png"
        if _paste_from_clipboard "$CLIPBOARD_IMG" && [ -s "$CLIPBOARD_IMG" ]; then
            _convert_to_cover "$CLIPBOARD_IMG" "$cover_file" "$output_dir"
            return $?
        else
            echo -e "${YELLOW}⚠️ Не удалось получить изображение из буфера обмена.${NC}"
        fi
    fi

    # Попробуем найти скриншот от mpv (создаётся при нажатии 's')
    echo -e "${YELLOW}🔍 Ищем скриншот от mpv...${NC}"
    MPV_SHOT=$(find ~/Pictures /tmp "$output_dir" -maxdepth 1 -name "mpv-shot*.png" -newer "$output_video_file" 2>/dev/null | head -1)
    if [ -n "$MPV_SHOT" ] && [ -f "$MPV_SHOT" ]; then
        echo -e "${GREEN}✅ Найден скриншот mpv: $MPV_SHOT${NC}"
        _convert_to_cover "$MPV_SHOT" "$cover_file" "$output_dir"
        return $?
    fi

    # Fallback: дать пользователю указать файл вручную
    echo -e "${YELLOW}⚠️ Автоматически не найдено. Укажите путь к файлу изображения:${NC}"
    read -p "Путь к файлу (Enter для пропуска): " manual_path
    if [ -n "$manual_path" ] && [ -f "$manual_path" ]; then
        _convert_to_cover "$manual_path" "$cover_file" "$output_dir"
        return $?
    fi

    echo -e "${YELLOW}⚠️ Обложка не создана.${NC}"
    return 1
}

# === Вспомогательная: конвертация PNG→JPG ===
_convert_to_cover() {
    local src="$1"
    local cover_file="$2"
    local output_dir="$3"

    if command -v magick >/dev/null 2>&1; then
        magick "$src" "$cover_file"
    elif command -v convert >/dev/null 2>&1; then
        convert "$src" "$cover_file"
    else
        echo -e "${RED}❌ ImageMagick не найден. Установите: sudo apt install imagemagick${NC}"
        return 1
    fi

    # Удаляем временный файл только если он не пользовательский
    case "$src" in
        */clipboard_image.png|*/mpv-shot*.png)
            rm -f "$src"
            ;;
    esac

    if [ -f "$cover_file" ]; then
        echo -e "${GREEN}✅ Обложка сохранена: $cover_file${NC}"
        return 0
    else
        echo -e "${RED}❌ Ошибка при конвертации обложки${NC}"
        return 1
    fi
}
