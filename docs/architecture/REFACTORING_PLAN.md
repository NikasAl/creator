# План рефакторинга проекта creator

> Анализ выполнен: 2026-04-18

## Сводка проблем

| Критичность | Количество | Описание |
|---|---|---|
| HIGH | 8 | Конфликты имён функций, 8 дубликатов split_text, 17 пар old/v2 файлов, 3 версии summary_processor |
| MEDIUM | 7 | Старые/новые определения логирования, encode_image дубли, сломанный source path |
| LOW | 2 | Мелкие дубли base64-кодирования |

---

## Этап 1. Устранение конфликтов функций (HIGH)

### 1.1 `common_step_add_music()` — 4 конкурирующих определения

**Проблема:** Функция определена в `lib/common/audio.sh` (строка 219) и `lib/common/music.sh` (строка 16) с одинаковым именем но разной сигнатурой. Какой вариант используется -- зависит от порядка `source`. Кроме того, `lib/vd/06_music.sh` и `lib/manim/04_render.sh` содержат свои standalone-копии `vd_step_add_music()` и `manim_step_add_music()`.

**Решение:**
- Удалить `common_step_add_music()` из `lib/common/audio.sh` -- оставить только в `lib/common/music.sh` (более полная версия с `step_num` и нормализацией путей)
- `lib/common/music.sh` уже содержит `vd_step_add_music()` и `manim_step_add_music()` как обёртки -- это правильный подход
- Удалить `lib/vd/06_music.sh` целиком -- заменить sourcing `lib/vd/06_music.sh` на `lib/common/music.sh` в `process_vd.sh`
- Удалить standalone `manim_step_add_music()` из `lib/manim/04_render.sh` -- она уже есть в `music.sh`

**Затронутые файлы:**
- `lib/common/audio.sh` -- удалить функцию (строки 218-251)
- `lib/vd/06_music.sh` -- удалить файл
- `lib/manim/04_render.sh` -- удалить локальную `manim_step_add_music()`
- `process_vd.sh` -- заменить `source lib/vd/06_music.sh` на `source lib/common/music.sh`
- `process_manim.sh` -- убедиться что `lib/common/music.sh` подключена после `audio.sh`

### 1.2 `check_required_vars()` -- 2 определения с разным поведением

**Проблема:** В `lib/common/utils.sh` функция возвращает код ошибки без `exit`, а старая версия (которая была в `lib/vd/utils.sh` до перезаписи) вызывала `exit 1`.

**Решение:** Оставить текущую реализацию в `lib/common/utils.sh` (возврат кода без exit). Это более правильный подход -- вызывающий код сам решает, выйти или продолжить. Если нужно -- добавить `|| exit 1` в местах вызова.

---

## Этап 2. Консолидация `split_text_into_chunks()` (HIGH)

**Проблема:** Функция разбивки текста на чанки реализована в 8 местах с разными лимитами:

| Файл | Лимит символов |
|---|---|
| `utils/text_splitter.py` (канонический) | настраиваемый |
| `speech_processors/alibaba_tts.py` | 500 |
| `speech_processors/silero.py` | 800 |
| `speech_processors/sber_api_synth.py` | 3500 |
| `text_processors/audiobook_processor.py` | 2500 |
| `text_processors/summary_processor.py` | -- |
| `text_processors/text_segmenter.py` | -- |
| `text_processors/text_processor.py` | -- |

**Решение:**
1. Убедиться что `utils/text_splitter.py` покрывает все use cases (параметр `max_chars`)
2. Заменить локальные реализации на импорт из `utils/text_splitter.py`:
   - В speech-процессорах: `from utils.text_splitter import split_text_into_chunks`
   - В text-процессорах: аналогично
3. Лимиты передавать как параметры вызова, а не хардкодить в каждой копии

---

## Этап 3. Удаление v2-дубликатов (HIGH)

**Проблема:** 17 файлов имеют пары old/v2. Старые версии не удалены, новые не полностью интегрированы.

### 3.1 Shell-библиотеки

| Старый файл | Новый файл | Действие |
|---|---|---|
| `lib/manim/utils.sh` (self-contained) | `lib/common/utils.sh` | Мигрировать точки входа на `lib/common/utils.sh`, затем удалить старый |
| `lib/manim/utils_v2.sh` | `lib/common/utils.sh` | Удалить `_v2` -- он просто реэкспортирует common |
| `lib/vd/utils.sh` (self-contained) | `lib/common/utils.sh` | Уже перезаписан новым содержимым -- оставить как есть |
| `lib/vd/utils_v2.sh` | `lib/vd/utils.sh` | Удалить `_v2` |
| `lib/manim/02_audio.sh` (194 строки, inline TTS) | `lib/common/audio.sh` | Мигрировать точки входа, удалить старый |
| `lib/manim/02_audio_v2.sh` | `lib/common/audio.sh` | Удалить `_v2` |
| `lib/vd/05_video.sh` (cross-imports) | `lib/vd/05_video_v2.sh` | Переименовать `_v2` в основное имя |
| `lib/manim/05_extra.sh` | `lib/common/promo.sh` | Перенести нужные функции в common/promo.sh |

**Порядок миграции:**
1. Убедиться что `process_manim.sh` работает с `lib/common/audio.sh` вместо `lib/manim/02_audio.sh`
2. Убедиться что `process_manim_song.sh` работает с `lib/common/audio.sh`
3. Убедиться что `process_podcast.sh` работает с `lib/common/audio.sh`
4. Удалить `lib/manim/02_audio.sh`, `lib/manim/02_audio_v2.sh`
5. Удалить `lib/manim/utils_v2.sh`, `lib/vd/utils_v2.sh`
6. Переименовать `lib/vd/05_video_v2.sh` в `lib/vd/05_video.sh`

### 3.2 Точки входа (process_*.sh)

| Старый | Новый | Действие |
|---|---|---|
| `process_vd.sh` (использует старые lib) | `process_vd_v2.sh` | Мигрировать, затем удалить `_v2` |
| `process_manim.sh` (использует старые lib) | `process_manim_v2.sh` | Мигрировать, затем удалить `_v2` |

### 3.3 Python-процессоры

| Файл | Действие | Причина |
|---|---|---|
| `text_processors/summary_processor.py` | Удалить | Заменён на `_v2` |
| `text_processors/summary_processor_refactored.py` | Удалить | Промежуточный шаг, заменён на `_v2` |
| `text_processors/summary_processor_v2.py` | Переименовать в `summary_processor.py` | Стать основным |
| `text_processors/correction_processor.py` | Удалить | Заменён на `_v2` |
| `text_processors/correction_processor_v2.py` | Переименовать в `correction_processor.py` | Стать основным |
| `text_processors/audiobook_processor.py` | Удалить | Заменён на `_v2` |
| `text_processors/audiobook_processor_v2.py` | Переименовать в `audiobook_processor.py` | Стать основным |
| `speech_processors/alibaba_tts.py` | Удалить после миграции | Заменён на `_v2` |
| `speech_processors/alibaba_tts_v2.py` | Переименовать в `alibaba_tts.py` | Стать основным |
| `speech_processors/silero.py` | Удалить после миграции | Заменён на `_v2` |
| `speech_processors/silero_v2.py` | Переименовать в `silero.py` | Стать основным |
| `speech_processors/sber_api_synth.py` | Удалить | Заменён на `sber_tts_v2` |
| `speech_processors/sber_synth_async_api.py` | Удалить | Заменён на `sber_tts_v2` |
| `speech_processors/sber_tts_v2.py` | Переименовать в `sber_tts.py` | Стать основным |
| `video_processors/illustration_prompt_processor.py` | Удалить | Заменён на `_v2` |
| `video_processors/illustration_prompt_processor_v2.py` | Переименовать в `illustration_prompt_processor.py` | Стать основным |

---

## Этап 4. Миграция process_poetry.sh и process_chat.sh (HIGH)

**Проблема:** Эти скрипты -- standalone (~800 и ~560 строк) с полностью inline логикой пайплайна. Не используют `lib/common/`. Содержат значительное дублирование с `process_vd.sh` и `lib/common/video.sh`.

**Решение:**
1. Вынести общую логику из `process_poetry.sh` в библиотеку `lib/poetry/`:
   - `lib/poetry/01_text.sh` -- подготовка текста
   - `lib/poetry/02_illustrations.sh` -- генерация и проверка иллюстраций
   - `lib/poetry/03_video.sh` -- сборка видео
2. Вынести общую логику из `process_chat.sh` в `lib/chat/`:
   - Аналогичная структура
3. Использовать общие функции из `lib/common/` для video, audio, promo
4. Итог: `process_poetry.sh` и `process_chat.sh` станут короткими оркестраторами (~50-80 строк)

---

## Этап 5. Мелкие дубли и чистка (MEDIUM)

### 5.1 Python: `encode_image()` / `encode_image_to_base64()`

**Проблема:** 3 вариации в разных файлах.

**Решение:** Создать `utils/image_utils.py` с единой реализацией:
```python
def encode_image_to_base64(image_path: str, max_side: int = 2048, quality: int = 95) -> str:
    ...
```

Заменить импорты в:
- `text_processors/discussion_to_tts.py`
- `text_processors/lesson_generator.py`
- `image_generators/image_editor_openrouter.py`
- `image_generators/image_editor_alibaba.py`
- `video_processors/alibaba_video_generator.py`

### 5.2 Python: `get_access_token()` (Sber)

**Проблема:** Одинаковая функция в `sber_synth_async_api.py` и `sber_api_synth.py`.

**Решение:** После миграции на `sber_tts_v2.py` (этап 3.3) оба старых файла удалятся, проблема исчезнет.

### 5.3 Shell: сломанный source path в `lib/manim/05_extra.sh`

**Проблема:** Строка 5:
```bash
source "$(dirname "$0")/lib/manim/cover_export.sh" 2>/dev/null || true
```
`$(dirname "$0")` -- это директория вызывающего скрипта, а не файла `05_extra.sh`. При вызове из `process_manim.sh` (корень проекта) путь будет `/lib/manim/cover_export.sh` -- неверно. Ошибка тихо игнорируется (`2>/dev/null || true`).

**Решение:** Использовать `BASH_SOURCE`:
```bash
source "$(dirname "${BASH_SOURCE[0]}")/cover_export.sh" 2>/dev/null || true
```

---

## Этап 6. Документация (LOW)

### 6.1 Выполнено: консолидация .md файлов в docs/

Все документационные .md файлы перенесены из корня и specs/ в структурированный каталог `docs/`:
- `docs/guides/` -- руководства пользователя
- `docs/specs/` -- технические спецификации
- `docs/api/` -- документация по API/интеграциям
- `docs/migration/` -- миграции и планы
- `docs/processors/` -- документация по процессорам
- `docs/architecture/` -- архитектура и планы рефакторинга

В корне оставлены только `README.md`, `publishers/README.md` и `chat_processors/README.md` (рядом с кодом).

---

## Порядок выполнения

Рекомендуемая последовательность (каждый этап -- отдельный коммит):

| # | Этап | Сложность | Риск |
|---|---|---|---|
| 1 | Конфликты функций (1.1-1.2) | Низкая | Низкий -- точечные правки |
| 2 | `split_text_into_chunks` | Низкая | Низкий -- механическая замена |
| 3a | Shell v2-миграция (3.1, 3.2) | Средняя | Средний -- затрагивает точки входа |
| 3b | Python v2-миграция (3.3) | Низкая | Низкий -- переименования |
| 4 | process_poetry.sh / process_chat.sh | Высокая | Высокий -- крупная переработка |
| 5 | Мелкие дубли и чистка (5.1-5.3) | Низкая | Низкий |
| 6 | Документация | Низкая | Низкий |

---

## Целевая архитектура

```
lib/
  common/          # Общие функции для ВСЕХ пайплайнов
    utils.sh       # Логирование, проверки, интерактивность
    audio.sh       # TTS, транскрибация (БЕЗ common_step_add_music)
    music.sh       # Добавление музыки (ЕДИНСТВЕННОЕ место)
    video.sh       # Иллюстрации, видео, обложки, шорты
    promo.sh       # Промо, Pikabu, HTML
    tts.sh         # Общие TTS-утилиты
  manim/           # Специфика Manim-пайплайна
    01_text.sh
    03_code.sh
    04_render.sh
    cover_export.sh
  vd/              # Специфика Video Discussion
    01_download.sh
    02_text.sh
    03_discuss.sh
    04_web.sh
    04_tts.sh
    05_video.sh    # Только vd-специфика
  poetry/          # Специфика Poetry (NEW)
    setup.sh
    illustrations.sh
    video.sh
  chat/            # Специфика Chat (NEW)
    setup.sh
    processing.sh

process_manim.sh        # Оркестратор, ~50 строк
process_vd.sh           # Оркестратор, ~50 строк
process_poetry_manim.sh # Оркестратор, ~50 строк
process_poetry.sh       # Оркестратор, ~50 строк
process_chat.sh         # Оркестратор, ~50 строк
process_podcast.sh      # Оркестратор, ~50 строк
```
