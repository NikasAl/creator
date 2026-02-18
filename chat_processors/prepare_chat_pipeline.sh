#!/bin/bash

# Скрипт для подготовки пайплайна из чата с ИИ
# Использование: ./chat_processors/prepare_chat_pipeline.sh [json_file]

# По умолчанию используем первый JSON файл из pipelines_chat
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIPELINES_CHAT_DIR="$SCRIPT_DIR/pipelines_chat"
CONFIGS_CHAT_DIR="$SCRIPT_DIR/configs/chat"

# Определяем JSON файл
if [ $# -gt 0 ]; then
    JSON_FILE="$1"
else
    # Ищем первый JSON файл в pipelines_chat
    JSON_FILE=$(find "$PIPELINES_CHAT_DIR" -name "chat-export-*.json" -type f | head -1)
    if [ -z "$JSON_FILE" ]; then
        echo "❌ Не найден JSON файл с экспортом чатов"
        echo "Использование: $0 [json_file]"
        exit 1
    fi
fi

if [ ! -f "$JSON_FILE" ]; then
    echo "❌ JSON файл не найден: $JSON_FILE"
    exit 1
fi

echo "📋 Подготовка пайплайна из чата"
echo "======================================"
echo "📄 JSON файл: $JSON_FILE"
echo ""

# Создаем директорию для конфигов если не существует
mkdir -p "$CONFIGS_CHAT_DIR"

# Используем Python для парсинга JSON и проверки статусов
python3 - "$JSON_FILE" "$PIPELINES_CHAT_DIR" "$CONFIGS_CHAT_DIR" << 'PYTHON_SCRIPT'
import sys
import json
from pathlib import Path

try:
    json_file = sys.argv[1]
    pipelines_chat_dir = sys.argv[2]
    configs_chat_dir = sys.argv[3]
except IndexError:
    print("❌ Ошибка: недостаточно аргументов")
    sys.exit(1)

# Парсим JSON
try:
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    print(f"❌ Ошибка чтения JSON файла: {e}")
    sys.exit(1)

chats = data.get('data', [])

if not chats:
    print("❌ Не найдено чатов в JSON файле")
    sys.exit(1)

# Функция для проверки статуса чата
def check_chat_status(chat_id, chat_title):
    # Генерируем имя директории из title
    safe_title = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title.replace(' ', '_')
    pipeline_dir = Path(pipelines_chat_dir) / f"pipeline_{safe_title}"
    
    status = "NEW"
    status_desc = "новый"
    
    if not pipeline_dir.exists():
        return status, status_desc, None
    
    # Проверяем маркер .processing
    processing_file = pipeline_dir / ".processing"
    video_file = pipeline_dir / "video.mp4"
    article_file = pipeline_dir / "article.txt"
    illustrations_file = pipeline_dir / "illustrations.json"
    
    if video_file.exists():
        status = "READY"
        status_desc = "готов (есть видео)"
    elif processing_file.exists():
        status = "PROCESSING"
        status_desc = "в обработке"
    elif article_file.exists() or illustrations_file.exists():
        status = "PARTIAL"
        status_desc = "частично обработан"
    
    return status, status_desc, pipeline_dir

# Показываем список чатов со статусами
print("📋 Доступные чаты:\n")
for i, chat in enumerate(chats, 1):
    chat_id = chat.get('id', 'N/A')
    title = chat.get('title', 'Без названия')
    
    status, status_desc, pipeline_dir = check_chat_status(chat_id, title)
    
    # Форматируем статус
    status_symbol = {
        'NEW': '[NEW]',
        'PROCESSING': '[PROCESSING]',
        'READY': '[READY]',
        'PARTIAL': '[PARTIAL]'
    }.get(status, '[?]')
    
    print(f"{i:3d}. {status_symbol} {title}")
    if pipeline_dir:
        print(f"     └─ {pipeline_dir}")

print("\nВведите номер чата для обработки (или 'q' для выхода): ", end='', flush=True)
PYTHON_SCRIPT

read -r chat_number

if [[ "$chat_number" =~ ^[Qq]$ ]]; then
    echo "Выход"
    exit 0
fi

if ! [[ "$chat_number" =~ ^[0-9]+$ ]]; then
    echo "❌ Неверный номер чата"
    exit 1
fi

# Получаем информацию о выбранном чате
CHAT_INFO=$(python3 - "$JSON_FILE" "$chat_number" << 'PYTHON_SCRIPT'
import json
import sys

json_file = sys.argv[1]
try:
    chat_num = int(sys.argv[2])
except (ValueError, IndexError):
    print("ERROR")
    sys.exit(1)

try:
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chats = data.get('data', [])
    if not chats:
        print("ERROR")
        sys.exit(1)
    
    if chat_num < 1 or chat_num > len(chats):
        print("ERROR")
        sys.exit(1)

    chat = chats[chat_num - 1]
    chat_id = chat.get('id', '')
    title = chat.get('title', '')

    # Генерируем безопасное имя для директории
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title.replace(' ', '_')

    print(f"{chat_id}|{title}|{safe_title}")
except Exception as e:
    print("ERROR")
    sys.exit(1)
PYTHON_SCRIPT
)

if [[ "$CHAT_INFO" == "ERROR" ]]; then
    echo "❌ Неверный номер чата"
    exit 1
fi

IFS='|' read -r CHAT_ID CHAT_TITLE SAFE_TITLE <<< "$CHAT_INFO"

echo ""
echo "✅ Выбран чат: $CHAT_TITLE"
echo "   ID: $CHAT_ID"
echo ""

PIPELINE_DIR="$PIPELINES_CHAT_DIR/pipeline_${SAFE_TITLE}"
PROCESSING_FILE="$PIPELINE_DIR/.processing"
METADATA_FILE="$PIPELINE_DIR/chat_metadata.json"
CHAT_TXT_FILE="$PIPELINE_DIR/chat.txt"
CONFIG_FILE="$CONFIGS_CHAT_DIR/${SAFE_TITLE}.conf"

# Проверяем статус
if [ -f "$PIPELINE_DIR/video.mp4" ]; then
    echo "ℹ️  Чат уже обработан (есть финальное видео)"
    read -p "Пересоздать пайплайн? (y/n): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Выход"
        exit 0
    fi
elif [ -f "$PROCESSING_FILE" ]; then
    echo "ℹ️  Чат в процессе обработки"
    read -p "Продолжить обработку? (y/n): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Выход"
        exit 0
    fi
elif [ -f "$PIPELINE_DIR/article.txt" ] || [ -f "$PIPELINE_DIR/illustrations.json" ]; then
    echo "ℹ️  Чат частично обработан"
    read -p "Пересоздать или продолжить? (r - пересоздать, c - продолжить, n - отмена): " -r
    if [[ $REPLY =~ ^[Rr]$ ]]; then
        echo "🔄 Пересоздаём пайплайн..."
    elif [[ $REPLY =~ ^[Cc]$ ]]; then
        echo "🔄 Продолжаем обработку..."
    else
        echo "Выход"
        exit 0
    fi
fi

# Создаем директорию пайплайна
mkdir -p "$PIPELINE_DIR"

# Конвертируем чат в текстовый формат (если не существует или перезаписываем)
if [ ! -f "$CHAT_TXT_FILE" ] || [[ "$REPLY" =~ ^[Rr]$ ]]; then
    echo ""
    echo "📝 Конвертация чата в текстовый формат..."
    python3 "$SCRIPT_DIR/chat_processors/chat_json_parser.py" \
        "$JSON_FILE" \
        --chat-id "$CHAT_ID" \
        --output "$CHAT_TXT_FILE"
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка конвертации чата"
        exit 1
    fi
    echo "✅ Чат конвертирован: $CHAT_TXT_FILE"
else
    echo "ℹ️  Используем существующий chat.txt"
fi

# Создаем метаданные
echo ""
echo "📝 Создание метаданных..."
cat > "$METADATA_FILE" << EOF
{
    "chat_id": "$CHAT_ID",
    "original_title": "$CHAT_TITLE",
    "pipeline_name": "$SAFE_TITLE",
    "status": "processing",
    "created_at": $(date +%s)
}
EOF
echo "✅ Метаданные созданы: $METADATA_FILE"

# Создаем конфиг (не перезаписываем существующий без подтверждения)
if [ -f "$CONFIG_FILE" ]; then
    echo ""
    echo "⚠️  Конфиг уже существует: $CONFIG_FILE"
    read -p "Перезаписать? (y/n): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "ℹ️  Используем существующий конфиг"
    else
        CREATE_CONFIG=true
    fi
else
    CREATE_CONFIG=true
fi

if [ "$CREATE_CONFIG" = true ]; then
    echo ""
    echo "📝 Создание конфига..."
    
    # Запрашиваем название для видео (по умолчанию из чата)
    read -p "Введите название для видео (Enter для '$CHAT_TITLE'): " VIDEO_TITLE
    VIDEO_TITLE="${VIDEO_TITLE:-$CHAT_TITLE}"
    
    cat > "$CONFIG_FILE" << EOF
# Конфигурация для обработки чата в видео
# Сгенерировано автоматически для чата: $CHAT_TITLE

# Обязательные параметры
BASE_DIR="$PIPELINE_DIR"
TITLE="$VIDEO_TITLE"
AUTHOR="AI Assistant"

# Необязательные параметры
INPUT_FILE="article.txt"
AUDIO_FILE="audio.mp3"
STYLE="Реалистичный"
ERA="21 век"
REGION="Россия"
GENRE="Статья"
SETTING="Современная обстановка."
SECONDS_PER_ILLUSTRATION="8"

# Параметры для генерации статьи
ARTICLE_MODEL="default"  # default, budget, quality
ARTICLE_INSTRUCTIONS=""  # путь к файлу с дополнительными инструкциями (относительно BASE_DIR)

# Параметры промо-описания
PROMO_PREFIX=""
PROMO_MODEL="default"
PROMO_AUDIENCE="широкая аудитория"
PROMO_TONE="дружелюбный и информативный"
PROMO_PLATFORM="YouTube"
PROMO_LANG="русский"
PROMO_TITLE="$VIDEO_TITLE"
PROMO_SOURCE_FILE="article.txt"
EOF
    
    echo "✅ Конфиг создан: $CONFIG_FILE"
fi

# Создаем маркер обработки
echo ""
echo "📝 Создание маркера обработки..."
cat > "$PROCESSING_FILE" << EOF
{
    "chat_id": "$CHAT_ID",
    "chat_title": "$CHAT_TITLE",
    "status": "processing",
    "started_at": $(date +%s),
    "config_file": "$CONFIG_FILE"
}
EOF
echo "✅ Маркер создан: $PROCESSING_FILE"

echo ""
echo "✅ Пайплайн подготовлен!"
echo "📁 Директория: $PIPELINE_DIR"
echo "⚙️  Конфиг: $CONFIG_FILE"
echo ""
echo "📝 Следующий шаг: запустите обработку"
echo "   ./process_chat.sh $CONFIG_FILE"

