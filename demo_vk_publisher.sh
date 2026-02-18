#!/bin/bash
# Демонстрационный скрипт для публикации на VK

echo "🎬 Демонстрация публикации на VK"
echo "================================="

# Проверяем наличие пайплайна
PIPELINE="pipeline_LemEng_87_111"
if [ ! -d "$PIPELINE" ]; then
    echo "❌ Пайплайн $PIPELINE не найден"
    echo "Создайте пайплайн или укажите существующий"
    exit 1
fi

echo "📁 Используем пайплайн: $PIPELINE"

# Проверяем конфигурацию
if [ ! -f "config.publisher.env" ]; then
    echo "❌ Файл конфигурации config.publisher.env не найден"
    echo "Скопируйте config.publisher.env.example в config.publisher.env и настройте"
    exit 1
fi

echo "✅ Конфигурация найдена"

# Проверяем VK токен
if [ ! -f "vk_token.json" ]; then
    echo "⚠️  VK токен не найден"
    echo "Запустите: python setup_vk_auth.py"
    exit 1
fi

echo "✅ VK токен найден"

echo ""
echo "🔍 Пробный запуск (анализ без публикации)"
echo "----------------------------------------"
python publisher.py "$PIPELINE" --platforms vk --dry-run

if [ $? -eq 0 ]; then
    echo ""
    echo "🚀 Публикация на VK"
    echo "-------------------"
    python publisher.py "$PIPELINE" --platforms vk --privacy private
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 Демонстрация завершена успешно!"
        echo ""
        echo "📝 Дополнительные примеры:"
        echo "python publisher.py $PIPELINE --platforms vk --title 'Мое видео'"
        echo "python publisher.py $PIPELINE --platforms vk --no-llm"
        echo "python publisher.py $PIPELINE --platforms youtube vk"
    else
        echo "❌ Ошибка публикации"
        exit 1
    fi
else
    echo "❌ Ошибка анализа пайплайна"
    exit 1
fi

