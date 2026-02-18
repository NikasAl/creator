#!/bin/bash
set -e  # Прерывать выполнение при любой ошибке

# Проверка аргументов
if [[ $# -lt 1 ]]; then
    echo "Использование: $0 <название> [--skip-sync]"
    echo "  --skip-sync: пропустить rsync файлов (только скопировать конфиг и запустить обработку)"
    exit 1
fi

CONFIG_NAME="$1"
REMOTE_USER="nikas"
REMOTE_HOST="diffusion"
REMOTE_PATH="/home/nikas/prjs/bookreader"
FULL_SYNC=true

# Обработка флага --skip-sync
if [[ $# -gt 1 && "$2" == "--skip-sync" ]]; then
    FULL_SYNC=false
fi

CONFIG_FILE="configs/vd/${CONFIG_NAME}.conf"
REMOTE_CONFIG_FILE="${REMOTE_PATH}/configs/vd/${CONFIG_NAME}.conf"

# Шаг 0: Полная синхронизация проекта (если не пропущена)
if $FULL_SYNC; then
    echo "🔄 Синхронизация проекта с сервером..."
    rsync -avz --delete \
        --exclude='.git/' \
        --exclude='.env' \
        --exclude='*.log' \
        --exclude='tmp/' \
	--exclude='pipelines*/' \
	--exclude='venv/' \
        ./ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"
    echo "✅ Проект синхронизирован"
else
    # Шаг 1: Копирование только конфига (если пропущен полный rsync)
    echo "⬆️ Копирование конфига на сервер..."
    scp "${CONFIG_FILE}" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_CONFIG_FILE}"
    echo "✅ Конфиг скопирован"
fi

# Шаг 2: Запуск обработки на сервере
echo "⚙️ Запуск обработки на сервере..."
#ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH} && act_env && ./process_vd.sh configs/vd/${CONFIG_NAME}.conf"
ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH} && bash -i -c 'act_env && ./process_vd.sh configs/vd/${CONFIG_NAME}.conf'"
echo "✅ Обработка завершена"

# Шаг 3: Обратная синхронизация результатов
echo "⬇️ Скачивание результатов..."
rsync -avz --prune-empty-dirs \
    --include='pipelines_vd/' \
    --include="pipelines_vd/${CONFIG_NAME}/***" \
    --exclude='*' \
    "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/" "./"
echo "✅ Результаты получены"

echo -e "\n✨ Все операции успешно выполнены для ${CONFIG_NAME}"

