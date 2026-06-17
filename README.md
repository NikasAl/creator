# Creator — Мультирежимная система генерации видео-контента

**Creator** — это универсальная система автоматизированной генерации видео-контента с использованием AI. Проект объединяет множество пайплайнов для создания разнообразных форматов: от аудиокниг до музыкальных клипов, от образовательных уроков до пересказов видео с YouTube.

## Содержание

- [Возможности](#возможности)
- [Режимы работы](#режимы-работы)
- [Установка](#установка)
- [Конфигурация](#конфигурация)
- [Использование](#использование)
- [Структура проекта](#структура-проекта)
- [API и сервисы](#api-и-сервисы)
- [Расширение системы](#расширение-системы)

---

## Возможности

### Основные функции

- **Извлечение и обработка текста** — PDF, веб-страницы, чаты, видео
- **AI-обработка контента** — пересказы, суммаризации, обсуждения, статьи
- **Генерация изображений** — Alibaba Cloud, FLUX, OpenRouter
- **Синтез речи** — Alibaba TTS, Silero, Sber API
- **Анимации Manim** — математические и образовательные визуализации
- **Сборка видео** — FFmpeg с динамическими эффектами камеры
- **Публикация** — YouTube, VK Video, VK Audio

### Ключевые особенности

- **Модульная архитектура** — каждый пайплайн независим и переиспользует общие компоненты
- **Интерактивные режимы** — пошаговая работа с паузами для проверки и редактирования
- **Resume-режим** — продолжение прерванного пайплайна с места остановки
- **Конфигурационные файлы** — параметры каждого проекта в отдельном файле
- **Множество AI-провайдеров** — OpenRouter, Alibaba Cloud, локальные модели

---

## Режимы работы

### 1. 📚 Аудиокниги из PDF (BookReader)

Базовый режим проекта — создание аудиокниг и видео-пересказов из печатных текстов.

**Пайплайн:**
```
PDF → Извлечение текста → Очистка → Пересказ → TTS → Иллюстрации → Видео
```

**Использование:**
```bash
# Полный пайплайн с конфигурационным файлом
./run_pipeline.sh configs/books/lomonosov.conf

# Или отдельные шаги
python full_pipeline.py book.pdf --pages "1-30" --summary --style educational
python text_processors/summary_cleaner.py summary.txt
python video_processors/illustration_review_cli.py --pipeline-dir ./pipeline_output
```

**Конфигурация:**
```bash
# configs/books/example.conf
PDF_FILE="path/to/book.pdf"
OUTPUT_DIR="pipelines_books/book_name"
PAGE_RANGE="1-50"
SUMMARY_STYLE="educational"  # educational, story, folk, simple
TITLE="Название книги"
AUTHOR="Автор"
PARTS="12"
STYLE="Реалистичный"
PLATFORM="YouTube"
```

---

### 2. 🎓 Образовательные видео с Manim

Создание математических и образовательных видео-уроков с анимацией через библиотеку Manim.

**Пайплайн:**
```
Spec (задача) → Сценарий урока → TTS → Транскрибация → Manim код → Рендер → Синхронизация
```

**Использование:**
```bash
# Создание нового пайплайна (интерактивно)
./setup_manim_pipeline.sh

# Обработка
./process_manim.sh configs/manim/math_example.conf
```

**Структура файлов:**
```
pipelines_manim/PIPELINE_NAME/
├── spec.txt                    # Описание задачи и затруднений
├── spec.jpg                    # Изображение задачи (опционально)
├── manim_example.py            # Пример кода для стилизации
├── lesson_script.txt           # Сгенерированный текст урока
├── audio.mp3                   # Аудио дорожка
├── sentence_timestamps.json    # Таймстампы предложений
├── manim_lesson.py             # Сгенерированный Manim код
├── video.mp4                   # Финальное видео
├── cover.jpg                   # Обложка
└── promo_description.txt       # Промо-описание
```

**Параметры конфигурации:**
```bash
BASE_DIR="pipelines_manim/math_lesson"
TITLE="Решение уравнений"
AUTHOR="Автор"
LANGUAGE="ru"
SCRIPT_MODEL="custom"           # Модель для генерации текста
CODE_MODEL="custom"             # Модель для генерации кода
QUALITY="low"                   # low, medium, high, 4k
```

---

### 3. 🎬 Пересказ видео (Video Discussion)

Создание пересказов или обсуждений видео с видеохостингов (YouTube, Rutube, Vimeo).

**Пайплайн:**
```
URL видео → Скачивание → Транскрибация → Сегментация → Summary/Discussion → Видео
```

**Использование:**
```bash
# Интерактивное создание конфигурации
./process_vd.sh

# С готовым конфигом
./process_vd.sh configs/vd/example.conf
```

**Режимы:**
- `summary` — краткий пересказ содержания
- `discussion` — анализ с разных точек зрения

**Параметры конфигурации:**
```bash
VIDEO_URL="https://www.youtube.com/watch?v=..."
BASE_DIR="pipelines_vd/video_name"
TITLE="Название видео"
AUTHOR="Автор канала"
LANGUAGE="ru"
MODE="summary"                   # summary или discussion
SEGMENTS_COUNT="10"
USE_ORIGINAL_VIDEO="false"       # Использовать исходное видео
STYLE="Реалистичный"
VIDEO_STRATEGY="cut"             # cut или speed
```

---

### 4. 🎵 Поэзия и песни (Poetry/Songs)

Создание музыкальных клипов из текста песни с иллюстрациями и динамическими видеоэффектами.

**Пайплайн:**
```
Текст песни + Аудио → Bible сущностей → Иллюстрации → Видео с эффектами
```

**Использование:**
```bash
# Интерактивный режим
./process_poetry.sh

# С конфигурацией
./process_poetry.sh configs/poetry/example.conf
```

**Особенности:**
- Автоматический расчёт количества иллюстраций по длительности аудио
- Создание «Библии» персонажей и локаций для согласованности
- 12 эффектов движения камеры (zoom, pan, circular, bounce)
- Перегенерация изображений через Alibaba Cloud
- Редактирование изображений (замена лиц, стилизация)
- Создание вертикальных шортов

**Параметры конфигурации:**
```bash
BASE_DIR="pipelines_poetry/song_name"
TITLE="Название песни"
AUTHOR="Исполнитель"
INPUT_FILE="song.txt"
AUDIO_FILE="audio.mp3"
STYLE="Реалистичный"
ERA="19 век"
GENRE="Песня"
SECONDS_PER_ILLUSTRATION="10"
IMAGE_EDIT_MODEL="none"         # none, google/gemini-2.5-flash, Qwen-Image-Edit
```

---

### 5. 🎙️ Подкасты

Обработка игровых записей и создание подкастов с AI-голосом.

**Пайплайн:**
```
Запись (game_*.mp4 + mic.mp3) → Транскрибация → AI-сценарий → TTS → Сборка видео
```

**Использование:**
```bash
./process_podcast.sh project_name
```

**Автоматизация:**
- Поиск последних файлов записи в `~/Videos/recordings`
- Транскрибация с таймстампами
- Генерация «умного сценария» подкаста
- Синтез речи с фоновым звуком
- Ретайминг видео под новую аудио-дорожку

---

### 6. 💬 Чаты в видео (Chat to Article)

Преобразование чатов с AI в познавательные статьи и видео.

**Пайплайн:**
```
JSON экспорт чата → Парсинг → Статья → Корректура → HTML → Видео
```

**Использование:**
```bash
# Подготовка пайплайна из JSON
./chat_processors/prepare_chat_pipeline.sh chat-export.json

# Полный пайплайн
./process_chat.sh configs/chat/example.conf
```

**Форматы входного файла:**
- JSON экспорт чатов
- Текстовый формат `### USER` / `### ASSISTANT`

**Параметры конфигурации:**
```bash
BASE_DIR="pipelines_chat/topic_name"
TITLE="Тема статьи"
INPUT_FILE="article.txt"
ARTICLE_MODEL="default"         # default, budget, quality
ARTICLE_INSTRUCTIONS=""          # Файл с дополнительными инструкциями
```

---

### 7. 🎙️ Аудио → Видео (Audio to Video)

Создание видео с иллюстрациями из готового аудио файла. Идеально для NotebookLM подкастов, интервью, записей обсуждений — когда есть готовая аудио дорожка и нужно добавить визуальный ряд.

**Пайплайн:**
```
Аудио (mp3/m4a) → Транскрибация → Сегментация → Промпты иллюстраций → Скачивание/AI → Видео
```

**Использование:**
```bash
# Интерактивный выбор файла через fzf (mp3/m4a из ~/Downloads)
./process_audio_video.sh

# Явное указание аудио файла
./process_audio_video.sh /path/to/podcast.mp3

# С конфигурационным файлом
./process_audio_video.sh configs/audio_video/example.conf
```

**Особенности:**
- Интерактивный выбор аудио через **fzf** — ищет mp3/m4a в `~/Downloads` с предпросмотром длительности
- Автоматическая конвертация m4a → mp3 при необходимости
- Выбор транскрибатора: Whisper или WhisperX (wav2vec2 alignment)
- Тематическая сегментация текста через LLM с привязкой к таймстемпам
- Генерация промптов иллюстраций на основе «Библии» сущностей
- Поддержка внешнего сервиса: промпты копируются в буфер обмена, inotifywait мониторит `~/Downloads/` для автоматического перемещения скачанных изображений
- Альтернативная AI-генерация иллюстраций (FLUX/Alibaba Cloud)
- Сборка финального видео с эффектами фото-движения (zoom in/out)

**Параметры конфигурации:**
```bash
# configs/audio_video/example.conf
# AUDIO_FILE="/path/to/podcast.mp3"  # опционально — иначе fzf
BASE_DIR="pipelines_audio_video/my_podcast"
TITLE="Мой подкаст"
LANGUAGE="ru"
SEGMENTS_COUNT="10"
STYLE="Реалистичный"
SECONDS_PER_ILLUSTRATION="20"
```

**Структура файлов пайплайна:**
```
pipelines_audio_video/my_podcast/
├── audio.mp3                   # Аудио дорожка (сконвертированная)
├── sentence_timestamps.json    # Таймстампы транскрибации
├── transcript.txt              # Извлечённый текст
├── segments.json               # Тематические сегменты
├── illustrations.json          # Промпты для иллюстраций
├── bible.json                  # Библия сущностей
├── images/
│   ├── illustration_00.png
│   ├── illustration_01.png
│   └── ...
├── video.mp4                   # Финальное видео
└── cover.jpg                   # Обложка (опционально)
```

---

### 8. 🎸 Музыкальные клипы с Manim

Создание музыкальных клипов с визуализацией текста через Manim.

**Использование:**
```bash
./process_manim_song.sh configs/poetry/song.conf
```

**Отличия от обычного poetry-режима:**
- Генерация Manim-кода для визуализации текста песни
- Синхронизация анимации с аудио
- Рендер в высоком качестве

---

### 9. 📤 Публикация

Автоматическая публикация видео на видеохостинги.

**Поддерживаемые платформы:**
- **YouTube** — полная поддержка с OAuth 2.0
- **VK Video** — загрузка видео
- **VK Audio** — загрузка аудио-треков

**Использование:**
```bash
# Пробный запуск (без публикации)
python publisher.py pipeline_name --platforms youtube --dry-run

# Публикация на YouTube
python publisher.py pipeline_name --platforms youtube --privacy private

# Публикация на VK
python publisher.py pipeline_name --platforms vk

# Мульти-платформенная публикация
python publisher.py pipeline_name --platforms youtube vk
```

**Метаданные:**
- Автоматическая генерация через LLM
- Ручное указание title, description, tags
- Настройка приватности (private/unlisted/public)

---

## Установка

### 1. Клонирование

```bash
git clone https://github.com/NikasAl/creator.git
cd creator
```

### 2. Python-зависимости

```bash
pip install -r requirements.txt
```

### 3. Системные зависимости

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg

# macOS
brew install ffmpeg
```

### 4. Дополнительные компоненты

**Для Manim:**
```bash
pip install manim
# Дополнительно: LaTeX для математических формул
sudo apt install texlive-full
```

**Для транскрибации:**
```bash
pip install openai-whisper
```

**Для скачивания видео:**
```bash
pip install yt-dlp
```

**Для пайплайна Audio → Video (fzf + inotifywait):**
```bash
sudo apt install fzf inotify-tools xclip
```

### 5. Настройка конфигурации

```bash
cp config.env.example config.env
# Отредактируйте config.env, добавив свои API ключи
```

---

## Конфигурация

### Основной файл config.env

```env
# OpenRouter API (LLM)
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Модели по умолчанию
DEFAULT_MODEL=anthropic/claude-3.5-sonnet
BUDGET_MODEL=google/gemini-2.5-flash-lite
QUALITY_MODEL=anthropic/claude-3.5-sonnet

# Параметры обработки
DEFAULT_CHUNK_SIZE=2500
DEFAULT_TEMPERATURE=0.2
DEFAULT_MAX_TOKENS=4000

# Alibaba Cloud (изображения, видео, TTS)
ALIBABA_API_KEY=your_key_here
ALIBABA_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
ALIBABA_VIDEO_MODEL=wan2.1-i2v-turbo
ALIBABA_PROMPT_MODEL=qwen/qwen3-30b-a3b:free
```

### Файл конфигурации публикатора

```env
# config.publisher.env

# YouTube
YOUTUBE_CREDENTIALS_PATH=youtube_credentials.json
DEFAULT_PRIVACY=private

# VK
VK_CLIENT_ID=your_client_id
VK_CLIENT_SECRET=your_client_secret
VK_ACCESS_TOKEN=your_access_token
VK_GROUP_ID=your_group_id  # опционально
```

### Конфигурационные файлы пайплайнов

Каждый пайплайн имеет свой конфигурационный файл в соответствующей директории:
- `configs/books/` — аудиокниги
- `configs/manim/` — Manim-уроки
- `configs/vd/` — пересказы видео
- `configs/poetry/` — поэзия и песни
- `configs/audio_video/` — аудио → видео (NotebookLM подкасты)
- `configs/chat/` — чаты

---

## Использование

### Интерактивный режим

Большинство пайплайнов поддерживают интерактивный режим без указания конфигурационного файла:

```bash
# Запуск с интерактивным созданием конфигурации
./process_poetry.sh
./process_vd.sh
./process_audio_video.sh          # fzf выбор mp3/m4a из ~/Downloads
./setup_manim_pipeline.sh
```

### Пайплайн с конфигурацией

```bash
./process_poetry.sh configs/poetry/example.conf
./process_vd.sh configs/vd/example.conf
./process_manim.sh configs/manim/example.conf
```

### Resume-режим

Все пайплайны поддерживают продолжение прерванной работы:

```bash
# Добавьте в конфигурационный файл
RESUME_MODE="true"
```

### Отдельные процессоры

Можно запускать отдельные компоненты системы:

```bash
# Извлечение текста из PDF
python text_processors/pdf_text_extractor_advanced.py book.pdf --pages "1-50"

# Очистка текста
python text_processors/clean_text_processor.py input.txt output.txt

# Создание пересказа
python text_processors/summary_processor.py input.txt output.txt --style educational

# Генерация иллюстраций
python video_processors/illustration_review_cli.py --pipeline-dir ./pipeline

# Создание видео
python video_processors/video_generator.py --pipeline-dir ./pipeline

# Транскрибация
python audio_processors/free_transcriber.py text.txt audio.mp3
```

---

## Структура проекта

```
creator/
├── process_poetry.sh           # Пайплайн поэзии/песен
├── process_manim.sh            # Пайплайн Manim-уроков
├── process_vd.sh               # Пайплайн пересказа видео
├── process_podcast.sh          # Пайплайн подкастов (записи + TTS)
├── process_audio_video.sh      # Пайплайн: готовое аудио → видео с иллюстрациями
├── process_chat.sh             # Пайплайн чатов
├── process_manim_song.sh       # Пайплайн музыкальных клипов Manim
├── run_pipeline.sh             # Универсальный пайплайн аудиокниг
│
├── lib/                        # Библиотеки функций
│   ├── manim/                  # Функции Manim-пайплайна
│   │   ├── utils.sh            # Общие утилиты
│   │   ├── 01_text.sh          # Генерация текста
│   │   ├── 02_audio.sh         # Работа с аудио
│   │   ├── 03_code.sh          # Генерация кода
│   │   ├── 04_render.sh        # Рендеринг
│   │   ├── 05_extra.sh         # Промо и обложки
│   │   └── song_logic.sh       # Логика песен
│   └── vd/                     # Функции Video Discussion
│       ├── setup.sh            # Интерактивная настройка
│       ├── utils.sh            # Общие утилиты
│       ├── 01_download.sh      # Скачивание видео
│       ├── 02_text.sh          # Транскрибация
│       ├── 03_discuss.sh       # Создание контента
│       ├── 04_tts.sh           # Синтез речи
│       ├── 05_video.sh         # Генерация видео
│       └── 06_music.sh         # Фоновая музыка
│
├── text_processors/            # Обработка текста
│   ├── pdf_text_extractor_advanced.py
│   ├── clean_text_processor.py
│   ├── summary_processor.py
│   ├── audiobook_processor.py
│   ├── correction_processor.py
│   ├── video_discussion_processor.py
│   ├── promo_description_processor.py
│   ├── lesson_generator.py
│   └── ...
│
├── video_processors/           # Создание видео
│   ├── video_generator.py      # Генератор видео с эффектами
│   ├── illustration_prompt_processor_v2.py
│   ├── illustration_review_cli.py
│   ├── alibaba_video_generator.py
│   ├── alibaba_image_generator.py
│   ├── video_downloader.py
│   ├── video_cutter.py
│   └── video_retimer.py
│
├── speech_processors/          # Синтез и распознавание речи
│   ├── alibaba_tts.py          # Alibaba Qwen TTS
│   ├── silero.py               # Silero TTS
│   └── sber_api_synth.py       # Sber API
│
├── audio_processors/           # Обработка аудио
│   ├── audio_transcriber.py
│   ├── free_transcriber.py
│   ├── sentence_transcriber.py
│   └── sentence_transcriber_whisperx.py
│
├── image_generators/           # Генерация изображений
│   ├── make_cover.py           # Создание обложек
│   ├── together_image_generator.py
│   ├── image_editor_openrouter.py
│   └── image_editor_alibaba.py
│
├── chat_processors/            # Обработка чатов
│   ├── chat_article_processor.py
│   ├── chat_json_parser.py
│   └── prepare_chat_pipeline.sh
│
├── publishers/                 # Публикация
│   ├── base_publisher.py
│   ├── youtube_publisher.py
│   ├── vk_publisher.py
│   ├── pipeline_analyzer.py
│   └── llm_metadata_generator.py
│
├── manim_processors/           # Manim-компоненты
│   ├── manim_code_generator.py
│   ├── manim_video_synchronizer.py
│   └── solutions/              # Библиотека решений
│
├── configs/                    # Конфигурационные файлы
│   ├── books/
│   ├── manim/
│   ├── vd/
│   ├── poetry/
│   ├── audio_video/
│   └── chat/
│
├── specs/                      # Документация
│   └── docs/
│
└── utils/                      # Утилиты
    ├── audio_duration.py
    └── setup_config.py
```

---

## API и сервисы

### LLM через OpenRouter

| Модель | Назначение |
|--------|------------|
| `anthropic/claude-3.5-sonnet` | Качественная обработка текста |
| `google/gemini-2.5-flash` | Быстрая обработка |
| `deepseek/deepseek-v3` | Экономичный вариант |

### Alibaba Cloud

| Сервис | Назначение |
|--------|------------|
| `wan2.5-t2i-preview` | Генерация изображений |
| `wan2.1-i2v-turbo` | Анимация изображений в видео |
| `qwen3-tts-flash` | Синтез речи |

### TTS-провайдеры

| Провайдер | Особенности |
|-----------|-------------|
| Alibaba TTS | Высокое качество, русский язык |
| Silero | Локальный, быстрый |
| Sber API | Российский провайдер |

### Транскрибация

- **Whisper** (локально или через API) — основное решение
- **WhisperX** (Whisper + wav2vec2 forced alignment) — повышенная точность ~50мс на слово
- **OpenRouter** — для файлов до 25MB
- **Hugging Face** — бесплатные модели

---

## Расширение системы

### Добавление нового пайплайна

1. Создайте скрипт `process_newmode.sh`
2. Используйте существующие библиотеки из `lib/`
3. Создайте конфигурационные файлы в `configs/newmode/`

### Добавление новой платформы публикации

1. Создайте класс, наследующий от `BasePublisher`
2. Реализуйте методы:
   - `authenticate()`
   - `upload_video()`
   - `update_video_metadata()`
   - `get_upload_status()`
3. Добавьте поддержку в `publisher.py`

### Добавление новых эффектов видео

1. Добавьте эффект в enum `CameraEffect` в `video_generator.py`
2. Реализуйте логику в методе `create_single_clip`
3. Обновите документацию

---

## Лицензия

MIT License

---

## Благодарности

- OpenRouter за доступ к LLM
- Alibaba Cloud за генерацию изображений и видео
- Manim за библиотеку анимаций
- FFmpeg за мощную обработку медиа
- Whisper за качественную транскрибацию
