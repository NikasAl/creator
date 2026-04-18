# Настройка и первый запуск

## 1. Получение API ключа OpenRouter

### Шаг 1: Регистрация
1. Перейдите на [openrouter.ai](https://openrouter.ai)
2. Нажмите "Sign Up" и создайте аккаунт
3. Подтвердите email

### Шаг 2: Создание API ключа
1. Войдите в аккаунт
2. Перейдите в раздел "API Keys"
3. Нажмите "Create API Key"
4. Скопируйте созданный ключ

### Шаг 3: Установка ключа
```bash
# Временная установка (только для текущей сессии)
export OPENROUTER_API_KEY='ваш_ключ_здесь'

# Постоянная установка (добавьте в ~/.bashrc или ~/.zshrc)
echo 'export OPENROUTER_API_KEY="ваш_ключ_здесь"' >> ~/.bashrc
source ~/.bashrc
```

## 2. Установка зависимостей

```bash
# Установка Python пакетов
pip install -r requirements.txt

# Проверка установки
python -c "import pdfplumber, requests; print('✅ Зависимости установлены')"
```

## 3. Первый запуск

### Тестирование демо
```bash
# Запустите демонстрацию на небольшом фрагменте
python demo_processor.py
```

### Обработка вашего PDF
```bash
# Полный цикл обработки
python full_pipeline.py "ваш_файл.pdf"

# Или по этапам:
# 1. Извлечение текста
python extract_all.py "ваш_файл.pdf"

# 2. Обработка для аудиокниги
python audiobook_processor.py "ваш_файл_full_text.txt" -o "audiobook_ready.txt"
```

## 4. Доступные модели

### Рекомендуемые модели:
- `anthropic/claude-3.5-sonnet` (по умолчанию) - лучшее качество
- `openai/gpt-4o` - альтернатива
- `meta-llama/llama-3.1-8b-instruct` - бюджетный вариант

### Использование другой модели:
```bash
python text_processor.py input.txt -o output.txt --model "openai/gpt-4o"
```

## 5. Настройка размера частей

### Для больших файлов:
```bash
# Уменьшите размер части для экономии токенов
python text_processor.py input.txt -o output.txt --chunk-size 1500
```

### Для качественной обработки:
```bash
# Увеличьте размер для лучшего контекста
python text_processor.py input.txt -o output.txt --chunk-size 4000
```

## 6. Мониторинг использования

### Проверка баланса:
1. Войдите в аккаунт OpenRouter
2. Перейдите в "Usage"
3. Следите за расходом токенов

### Примерные расходы:
- 1M символов ≈ $0.50-2.00 (зависит от модели)
- Ваш PDF (1.1M символов) ≈ $0.55-2.20

## 7. Устранение проблем

### Ошибка "API key not found":
```bash
# Проверьте переменную окружения
echo $OPENROUTER_API_KEY

# Если пусто, установите заново
export OPENROUTER_API_KEY='ваш_ключ'
```

### Ошибка "Rate limit exceeded":
- Подождите несколько минут
- Уменьшите размер частей
- Используйте менее дорогую модель

### Ошибка "Connection timeout":
- Проверьте интернет-соединение
- Попробуйте позже
- Увеличьте timeout в коде

## 8. Оптимизация

### Для экономии токенов:
1. Используйте меньшие части текста
2. Выберите более дешевую модель
3. Обрабатывайте только нужные страницы

### Для лучшего качества:
1. Используйте Claude 3.5 Sonnet
2. Увеличьте размер частей
3. Обрабатывайте весь текст целиком

## 9. Примеры команд

### Быстрый тест:
```bash
# Демонстрация на небольшом фрагменте
python demo_processor.py
```

### Обработка небольшого PDF:
```bash
# Полный цикл
python full_pipeline.py "small_book.pdf"
```

### Обработка большого PDF:
```bash
# С настройками для экономии
python full_pipeline.py "large_book.pdf" \
    --model "meta-llama/llama-3.1-8b-instruct" \
    --chunk-size 1500
```

### Обработка по частям:
```bash
# Извлечь только первые 10 страниц
python pdf_text_extractor_advanced.py "book.pdf" -s 1 -e 10 -o "part1.txt"

# Обработать часть
python text_processor.py "part1.txt" -o "part1_processed.txt"
```

## 10. Результаты

После обработки вы получите:
- `*_raw.txt` - извлеченный текст из PDF
- `*_audiobook_ready.txt` - обработанный текст с аудио-тегами
- `*_metadata.json` - метаданные для аудиокниги
- `*_report.txt` - отчет о обработке

Теперь вы можете использовать обработанный текст с TTS системами для создания аудиокниги! 