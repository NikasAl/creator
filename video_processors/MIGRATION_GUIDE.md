# Руководство по миграции на Illustration Prompt Processor V2

## Что изменилось

### Старая версия (illustration_prompt_processor.py)
- Механическое деление текста на части
- Отсутствие единого сценария
- Плохая согласованность между иллюстрациями
- Простые промпты без контекста

### Новая версия (illustration_prompt_processor_v2.py)
- Создание библии сущностей (персонажи, объекты, локации)
- Генерация единого сценария с 4-8 сценами
- Согласованные промпты с использованием библии
- Лучшее качество иллюстраций

## Шаги миграции

### 1. Обновление скриптов
Замените вызовы старой версии на новую:

**Было:**
```bash
python video_processors/illustration_prompt_processor.py \
    input.txt \
    --parts 40 \
    --style pixar \
    -o illustrations.json
```

**Стало:**
```bash
python video_processors/illustration_prompt_processor_v2.py \
    input.txt \
    --parts 6 \
    --style pixar \
    -o illustrations.json \
    --bible-out bible.json \
    --title "Название книги" \
    --author "Автор"
```

### 2. Обновление pipeline скрипта
Файл `run_full_pipeline.sh` уже обновлен для использования V2.

### 3. Новые параметры
Добавьте новые параметры для лучшего качества:

```bash
--bible-out bible.json          # Сохранить библию сущностей
--title "Название"             # Название книги
--author "Автор"               # Автор книги
--era "19th century"           # Эпоха
--region "Russian village"     # Регион
--genre "folk tale"            # Жанр
--setting "Описание сеттинга"  # Краткое описание
```

### 4. Изменение количества частей
- **Старая версия**: 40+ частей (механическое деление)
- **Новая версия**: 4-8 частей (смысловые сцены)

Рекомендуется начинать с 6-8 частей для лучшего качества.

## Проверка миграции

### 1. Запустите тест
```bash
python test_illustration_processor.py
```

### 2. Проверьте выходные файлы
- `illustrations.json` - промпты для иллюстраций
- `bible.json` - библия сущностей
- В `illustrations.json` должен быть раздел `script` с описанием сцен

### 3. Сравните качество
- Персонажи должны выглядеть одинаково во всех сценах
- Сцены должны быть логически связаны
- Промпты должны быть более детальными

## Обратная совместимость

Старая версия `illustration_prompt_processor.py` остается доступной, но рекомендуется перейти на V2 для лучшего качества.

## Примеры использования

### Простой случай
```bash
python video_processors/illustration_prompt_processor_v2.py \
    summary.txt \
    -o illustrations.json \
    --bible-out bible.json \
    --parts 6 \
    --style "realistic"
```

### Детальная настройка
```bash
python video_processors/illustration_prompt_processor_v2.py \
    summary.txt \
    -o illustrations.json \
    --bible-out bible.json \
    --parts 8 \
    --style "pixar" \
    --title "Война и мир" \
    --author "Лев Толстой" \
    --era "19th century" \
    --region "Imperial Russia" \
    --genre "historical novel" \
    --setting "Россия во время наполеоновских войн"
```

## Устранение проблем

### Ошибка "API ключ не найден"
Проверьте файл `config.env` или `.env`:
```env
OPENROUTER_API_KEY=your_key_here
```

### Плохое качество промптов
- Уменьшите количество частей (parts)
- Добавьте больше контекста (era, region, genre)
- Используйте модель "quality" вместо "default"

### Несогласованность персонажей
- Проверьте `bible.json` - правильно ли извлечены сущности
- Убедитесь, что `--enrich-characters` включен (по умолчанию)
- Проверьте, что `--inline-entities` включен (по умолчанию)
