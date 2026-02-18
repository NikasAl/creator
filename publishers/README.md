# Система публикации видео

Модульная система для публикации видео на различные видеохостинги и платформы.

## Структура

- `base_publisher.py` - Базовый класс для всех публикаторов
- `youtube_publisher.py` - Публикатор для YouTube
- `vk_publisher.py` - Публикатор для VK Video/Audio
- `pipeline_analyzer.py` - Анализатор пайплайна для извлечения метаданных
- `llm_metadata_generator.py` - Генератор метаданных с использованием LLM

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Настройте конфигурацию:
```bash
cp config.publisher.env.example config.publisher.env
# Отредактируйте config.publisher.env
```

3. Настройте YouTube API:
   - Создайте проект в Google Cloud Console
   - Включите YouTube Data API v3
   - Создайте учетные данные OAuth 2.0
   - Скачайте файл `youtube_credentials.json`

4. Настройте VK API:
   - Создайте приложение в VK Developers
   - Получите CLIENT_ID и CLIENT_SECRET
   - Получите токен доступа с правами video, audio, wall
   - Укажите ID группы для публикации (опционально)

## Использование

### Базовое использование

```bash
python publisher.py pipeline_LemEng_87_111 --platforms youtube
python publisher.py pipeline_LemEng_87_111 --platforms vk
python publisher.py pipeline_LemEng_87_111 --platforms youtube vk
```

### С пользовательскими метаданными

```bash
python publisher.py pipeline_LemEng_87_111 \
  --platforms youtube \
  --title "Мое видео" \
  --description "Описание видео" \
  --tags "тег1" "тег2" "тег3" \
  --privacy public
```

### Пробный запуск (без публикации)

```bash
python publisher.py pipeline_LemEng_87_111 --platforms youtube --dry-run
python publisher.py pipeline_LemEng_87_111 --platforms vk --dry-run
python publisher.py pipeline_LemEng_87_111 --platforms youtube vk --dry-run
```

### Без использования LLM

```bash
python publisher.py pipeline_LemEng_87_111 --platforms youtube --no-llm
python publisher.py pipeline_LemEng_87_111 --platforms vk --no-llm
```

## Параметры

- `pipeline_path` - Путь к пайплайну
- `--platforms` - Платформы для публикации (по умолчанию: youtube)
- `--config` - Файл конфигурации .env
- `--title` - Пользовательское название видео
- `--description` - Пользовательское описание
- `--tags` - Пользовательские теги
- `--privacy` - Приватность видео (private/unlisted/public)
- `--no-llm` - Не использовать LLM для генерации метаданных
- `--output` - Файл для сохранения результатов
- `--dry-run` - Только анализ без публикации

## Поддерживаемые платформы

### YouTube
- Полная поддержка загрузки видео
- Автоматическая генерация метаданных
- Загрузка превью
- Настройка приватности

### VK Video/Audio
- Поддержка загрузки видео на VK Video
- Поддержка загрузки аудио на VK Audio
- Автоматическое определение типа контента (audio.mp3/video.mp4)
- Публикация в группу
- Настройка приватности

### Планируемые платформы
- Rutube
- Pikabu
- Dzen

## Расширение системы

Для добавления новой платформы:

1. Создайте новый класс, наследующий от `BasePublisher`
2. Реализуйте методы:
   - `authenticate()` - аутентификация
   - `upload_video()` - загрузка видео
   - `update_video_metadata()` - обновление метаданных
   - `get_upload_status()` - статус загрузки

3. Добавьте поддержку в `publisher.py`

## Примеры

### Анализ пайплайна

```python
from publishers.pipeline_analyzer import PipelineAnalyzer

analyzer = PipelineAnalyzer("pipeline_LemEng_87_111")
metadata = analyzer.analyze()
print(analyzer.get_summary())
```

### Генерация метаданных

```python
from publishers.llm_metadata_generator import LLMMetadataGenerator

generator = LLMMetadataGenerator("config.publisher.env")
title = generator.generate_title(content, book_title, book_author)
description = generator.generate_description(content, book_title, book_author)
tags = generator.generate_tags(content, book_title, book_author)
```

### Публикация на YouTube

```python
from publishers.youtube_publisher import YouTubePublisher
from publishers.base_publisher import VideoMetadata

publisher = YouTubePublisher("config.publisher.env")
publisher.authenticate()

metadata = VideoMetadata(
    title="Мое видео",
    description="Описание видео",
    tags=["тег1", "тег2"],
    video_path="video.mp4",
    privacy="private"
)

video_id = publisher.upload_video(metadata)
```

### Публикация на VK

```python
from publishers.vk_publisher import VKPublisher
from publishers.base_publisher import VideoMetadata

publisher = VKPublisher("config.publisher.env")
publisher.authenticate()

metadata = VideoMetadata(
    title="Мое видео",
    description="Описание видео",
    tags=["тег1", "тег2"],
    video_path="video.mp4",
    privacy="private"
)

# Загрузка только видео
video_id = publisher.upload_video(metadata)

# Загрузка только аудио
audio_id = publisher.upload_audio(metadata)

# Загрузка и видео, и аудио
results = publisher.upload_both(metadata)
video_id = results['video_id']
audio_id = results['audio_id']
```

## Устранение неполадок

### Ошибка аутентификации YouTube
- Проверьте файл `youtube_credentials.json`
- Убедитесь, что YouTube Data API v3 включен
- Проверьте права доступа к файлам

### Ошибка аутентификации VK
- Проверьте токен доступа в конфигурации
- Убедитесь, что токен имеет права `video`, `audio`, `wall`
- Проверьте ID группы (если используется)

### Ошибка генерации метаданных
- Проверьте `OPENROUTER_API_KEY` в конфигурации
- Убедитесь в доступности интернета
- Проверьте лимиты API

### Ошибка загрузки видео
- **YouTube:** Проверьте размер файла (лимит: 128GB)
- **VK:** Проверьте размер файла (лимит: 2GB для видео, 200MB для аудио)
- Убедитесь в корректности формата видео
- Проверьте права доступа к файлу
