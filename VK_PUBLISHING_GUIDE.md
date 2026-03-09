# Инструкция по публикации видео в VK Video

## 📋 Обзор

Эта инструкция описывает процесс публикации видео из пайплайна в VK Video (vkvideo.ru) с использованием существующих скриптов проекта Creator.

## 📁 Требуемые файлы из пайплайна

Для публикации необходимы следующие файлы в папке пайплайна:

```
pipelines_scr/lezhandr_scr/
├── video.mp4              # Основное видео (обязательно)
├── promo_description.txt  # Описание для публикации (опционально)
├── cover.jpg              # Обложка (опционально)
└── audio.mp3              # Аудио (опционально, для VK Audio)
```

---

## 🔧 Шаг 1: Настройка аутентификации VK

### 1.1 Создание приложения VK

1. Перейдите на [VK Developers](https://vk.com/editapp?act=create)
2. Выберите тип **"Standalone"** (рекомендуется) или **"Плагин для сайта"**
3. Запишите `client_id` (ID приложения)

> **Важно:** 
> - Для **Standalone-приложений** доступны все права (видео, группа, стена)
> - Для **Плагин-приложений** доступны только права `groups` и `video`

### 1.2 Настройка конфигурации

Создайте файл `config.publisher.env`:

```bash
cp config.publisher.env.example config.publisher.env
```

Отредактируйте файл:

```env
# OpenRouter API для генерации метаданных через LLM
OPENROUTER_API_KEY=your_openrouter_api_key_here

# VK настройки
VK_CLIENT_ID=YOUR_CLIENT_ID
VK_TOKEN_PATH=vk_token.json

# Модель для генерации метаданных
DEFAULT_MODEL=anthropic/claude-3.5-sonnet
DEFAULT_MAX_TOKENS=2000
DEFAULT_TEMPERATURE=0.3
```

### 1.3 Получение токена VK

**Способ А: Через setup_vk_auth.py (рекомендуется)**

```bash
python setup_vk_auth.py
```

Скрипт:
1. Откроет браузер для авторизации VK
2. Попросит разрешить доступ приложению
3. Запросит токен из адресной строки
4. Сохранит токен в `vk_token.json`

**Способ Б: Вручную через браузер**

1. Сформируйте URL (замените YOUR_CLIENT_ID):

```
https://oauth.vk.com/authorize?client_id=YOUR_CLIENT_ID&display=page&redirect_uri=https://oauth.vk.com/blank.html&scope=groups,video,wall&response_type=token&v=5.131
```

2. Разрешите доступ
3. Скопируйте `access_token` из URL перенаправления
4. Создайте файл `vk_token.json`:

```json
{
  "access_token": "ваш_токен_здесь",
  "group_id": "",
  "timestamp": 0
}
```

### 1.4 Проверка аутентификации

```bash
python tests/test_vk_auth.py
```

Ожидаемый вывод:
```
✅ Аутентификация успешна!
👤 Информация о пользователе:
   Имя: Иван Иванов
   ID: 123456789
```

---

## 🚀 Шаг 2: Публикация видео

### 2.1 Пробный запуск (dry-run)

Проверьте, что все файлы найдены:

```bash
python publisher.py pipelines_scr/lezhandr_scr --platforms vk --dry-run
```

Ожидаемый вывод:
```
📊 Анализ пайплайна:
📁 Пайплайн: lezhandr_scr
🎬 Видео: ✅
📝 Промо-описание: ✅

📋 Метаданные видео:
Название: ...
Описание: ...
Теги: ...

✅ Пробный запуск завершен
```

### 2.2 Публикация видео

```bash
python publisher.py pipelines_scr/lezhandr_scr --platforms vk
```

### 2.3 С пользовательскими метаданными

```bash
python publisher.py pipelines_scr/lezhandr_scr \
  --platforms vk \
  --title "Название видео" \
  --description "Описание видео" \
  --privacy private
```

### 2.4 Публикация без генерации через LLM

```bash
python publisher.py pipelines_scr/lezhandr_scr --platforms vk --no-llm
```

---

## 📊 Результат публикации

При успешной публикации:

```
✅ Публикатор vk настроен успешно
✅ Видео сохранено. ID: 123456789
✅ vk видео: https://vk.com/video123456_123456789
```

---

## 🎯 Скрипт быстрой публикации

Создайте файл `publish_to_vk.sh`:

```bash
#!/bin/bash
# Публикация видео в VK Video

PIPELINE_PATH="${1:-pipelines_scr/lezhandr_scr}"

if [ ! -d "$PIPELINE_PATH" ]; then
    echo "❌ Пайплайн не найден: $PIPELINE_PATH"
    exit 1
fi

echo "🎬 Публикация видео в VK"
echo "📁 Пайплайн: $PIPELINE_PATH"

# Проверяем наличие токена
if [ ! -f "vk_token.json" ]; then
    echo "❌ VK токен не найден. Запустите: python setup_vk_auth.py"
    exit 1
fi

# Проверяем наличие видео
if [ ! -f "$PIPELINE_PATH/video.mp4" ]; then
    echo "❌ Видео не найдено: $PIPELINE_PATH/video.mp4"
    exit 1
fi

# Пробный запуск
echo "🔍 Пробный запуск..."
python publisher.py "$PIPELINE_PATH" --platforms vk --dry-run

if [ $? -ne 0 ]; then
    echo "❌ Ошибка анализа пайплайна"
    exit 1
fi

# Публикация
echo "🚀 Публикация..."
python publisher.py "$PIPELINE_PATH" --platforms vk

echo "✅ Готово!"
```

Использование:

```bash
chmod +x publish_to_vk.sh
./publish_to_vk.sh pipelines_scr/lezhandr_scr
```

---

## ⚠️ Известные ограничения

### Для плагин-приложений (по умолчанию):
- ❌ Недоступна публикация в группу
- ❌ Недоступна загрузка аудио
- ✅ Доступна загрузка видео в личный профиль

### Для Standalone-приложений:
- ✅ Доступна публикация в группу
- ✅ Доступна загрузка аудио
- ✅ Все возможности

---

## 🔍 Устранение неполадок

### Ошибка: "Токен доступа VK не найден"

```bash
# Проверьте файл токена
ls -la vk_token.json

# Если не существует, получите токен
python setup_vk_auth.py
```

### Ошибка: "Токен доступа VK недействителен или истек"

Токены VK имеют ограниченный срок действия. Получите новый токен:

```bash
python setup_vk_auth.py
```

### Ошибка: "Не найдены файлы audio.mp3 или video.mp4"

```bash
# Проверьте структуру папки
ls -la pipelines_scr/lezhandr_scr/

# Должен быть video.mp4
```

### Ошибка: "Ошибка VK API: Access denied"

Недостаточно прав у токена. Получите токен с правами:

```
scope=groups,video,wall
```

### Ошибка: "Config file not found"

```bash
# Создайте конфигурацию
cp config.publisher.env.example config.publisher.env

# Отредактируйте
nano config.publisher.env
```

---

## 📁 Структура файлов проекта

```
creator/
├── publisher.py              # Главный скрипт публикации
├── setup_vk_auth.py          # Настройка аутентификации VK
├── config.publisher.env      # Конфигурация публикации
├── vk_token.json             # Токен VK (создаётся автоматически)
├── tests/
│   ├── test_vk_auth.py       # Тест аутентификации VK
│   └── test_publisher.py     # Тест системы публикации
└── publishers/
    ├── base_publisher.py     # Базовый класс
    ├── vk_publisher.py       # Публикатор VK
    ├── pipeline_analyzer.py  # Анализатор пайплайна
    └── llm_metadata_generator.py  # Генератор метаданных
```

---

## 📝 Краткая шпаргалка

```bash
# 1. Настройка
python setup_vk_auth.py

# 2. Проверка
python tests/test_vk_auth.py

# 3. Пробный запуск
python publisher.py pipelines_scr/lezhandr_scr --platforms vk --dry-run

# 4. Публикация
python publisher.py pipelines_scr/lezhandr_scr --platforms vk

# 5. Свои метаданные
python publisher.py pipelines_scr/lezhandr_scr \
  --platforms vk \
  --title "Моё видео" \
  --description "Описание видео" \
  --privacy public
```
