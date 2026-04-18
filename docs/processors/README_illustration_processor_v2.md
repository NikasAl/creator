# Illustration Prompt Processor V2

## Обзор

`IllustrationPromptProcessorV2` - это обновленная система для создания согласованных иллюстраций к текстам. Вместо механического деления текста на части, система создает единый сценарий с общей идеей для всех иллюстраций.

## Архитектура

### 1. Создание библии сущностей
- **Персонажи**: извлекаются с полным описанием внешности, роли, характерных черт
- **Объекты**: важные предметы с описанием внешнего вида и символики
- **Локации**: места действия с атмосферой и описанием
- **Визуальные профили**: детальные описания внешности персонажей

### 2. Генерация сценария
- Создается последовательность из 4-8 ключевых сцен
- Каждая сцена имеет:
  - Название
  - Краткое описание (1-2 предложения)
  - Ссылки на персонажей/объекты из библии
  - Временную позицию (начало, середина, кульминация, конец)
- Сцены связаны общей сюжетной линией

### 3. Создание промптов для иллюстраций
- Каждая сцена преобразуется в детальный промпт для FLUX
- Используется библия для согласованности внешности персонажей
- Промпты включают контекст из сценария
- Добавляются стилистические указания

## Преимущества новой архитектуры

✅ **Согласованность**: Все иллюстрации следуют единому сценарию
✅ **Консистентность**: Персонажи выглядят одинаково во всех сценах
✅ **Сюжетность**: Иллюстрации рассказывают историю, а не просто иллюстрируют текст
✅ **Качество**: Лучшие промпты благодаря контексту сценария

## Использование

### Базовый вызов
```bash
python video_processors/illustration_prompt_processor_v2.py \
    input.txt \
    -o illustrations.json \
    --bible-out bible.json \
    --parts 6 \
    --style folk
```

### С дополнительными параметрами
```bash
python video_processors/illustration_prompt_processor_v2.py \
    input.txt \
    -o illustrations.json \
    --bible-out bible.json \
    --parts 8 \
    --style "pixar" \
    --title "Название книги" \
    --author "Автор" \
    --era "19th century" \
    --region "Russian village" \
    --genre "folk tale" \
    --setting "Деревенская жизнь"
```

### В скрипте pipeline
```bash
# Обновленный run_full_pipeline.sh уже использует V2
./run_full_pipeline.sh
```

## Выходные файлы

### illustrations.json
```json
{
  "metadata": {
    "source_file": "input.txt",
    "generated_at": "2024-01-01T12:00:00",
    "model": "anthropic/claude-3.5-sonnet",
    "style": "folk",
    "requested_parts": 6,
    "created_parts": 6,
    "book": {"title": "Название", "author": "Автор"},
    "api_calls": 15,
    "tokens_used": 5000
  },
  "illustrations": [
    {
      "index": 1,
      "title": "Название сцены",
      "prompt": "Детальный промпт для FLUX...",
      "negative_prompt": "text, watermark, logo...",
      "summary": "Описание сцены",
      "present_entities": ["character_id1", "object_id1"],
      "timing": "beginning",
      "source_excerpt": "Исходный текст сцены"
    }
  ],
  "bible_ref": "bible.json",
  "script": [
    {
      "title": "Название сцены",
      "summary": "Описание сцены",
      "entities": ["character_id1", "object_id1"],
      "timing": "beginning"
    }
  ]
}
```

### bible.json
```json
{
  "metadata": {
    "source_file": "input.txt",
    "generated_at": "2024-01-01T12:00:00",
    "model": "anthropic/claude-3.5-sonnet",
    "style": "folk"
  },
  "style_guide": {
    "visual_style": "folk",
    "illustration_rules": [
      "Avoid logos, text, and watermarks",
      "Keep historical consistency of clothing and artifacts"
    ]
  },
  "characters": [
    {
      "id": "character_id1",
      "canonical_name": "Иван",
      "role": "мудрый старик",
      "appearance": "пожилой мужчина с длинной бородой",
      "visual_profile": {
        "age": "elderly",
        "gender": "male",
        "face_features": "длинная седая борода, мудрые глаза",
        "clothing": "простая крестьянская одежда",
        "signature_colors": ["brown", "gray"]
      }
    }
  ],
  "objects": [...],
  "locations": [...],
  "state": {
    "inventory": {},
    "relationships": {},
    "timeline": []
  }
}
```

## Тестирование

Запустите тестовый скрипт для проверки работы:
```bash
python test_illustration_processor.py
```

## Конфигурация

Создайте файл `.env` или `config.env`:
```env
OPENROUTER_API_KEY=your_api_key_here
DEFAULT_MODEL=anthropic/claude-3.5-sonnet
DEFAULT_TEMPERATURE=0.2
DEFAULT_MAX_TOKENS=1400
BUDGET_MODEL=meta-llama/llama-3.1-8b-instruct
QUALITY_MODEL=openai/gpt-4o
```

## Модели

- **default**: `anthropic/claude-3.5-sonnet` (баланс качества и стоимости)
- **budget**: `meta-llama/llama-3.1-8b-instruct` (экономичный вариант)
- **quality**: `openai/gpt-4o` (высокое качество)

## Отладка

Для анализа работы системы:
1. Проверьте `bible.json` - правильно ли извлечены сущности
2. Изучите `script` в выходном файле - логичен ли сценарий
3. Проанализируйте промпты - достаточно ли деталей для FLUX
4. Проверьте статистику API вызовов и токенов
