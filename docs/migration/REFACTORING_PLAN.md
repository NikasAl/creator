# План рефакторинга проекта Creator

## 📊 Найденные проблемы

### 🔴 Критические

| Проблема | Файлов | Строк дублированного кода |
|----------|--------|---------------------------|
| `split_text_into_chunks` | 8+ | ~200 |
| `load_config` | 10+ | ~150 |
| API-клиент OpenRouter | 8+ | ~100 |

### 🟡 Высокий приоритет

| Проблема | Описание |
|----------|----------|
| Кросс-зависимости | `lib/vd/05_video.sh` импортирует `lib/manim/02_audio.sh` |
| Нет базовых классов | Каждый процессор реализует свою логику |
| Разные стили логирования | `log_header()` vs `log_step()` |

---

## ✅ Созданные модули

### Python модули в `utils/`

#### 1. `text_splitter.py`
**Заменяет дублирование в 8 файлах:**
- `speech_processors/sber_api_synth.py`
- `speech_processors/silero.py`
- `speech_processors/alibaba_tts.py`
- `text_processors/text_processor.py`
- `text_processors/summary_processor.py`
- `text_processors/correction_processor.py`
- `text_processors/audiobook_processor.py`
- `text_processors/text_segmenter.py`

**Использование:**
```python
from utils.text_splitter import split_text_into_chunks

# С пресетом
chunks = split_text_into_chunks(text, preset='tts_alibaba')

# С кастомными параметрами
chunks = split_text_into_chunks(text, max_chars=500)
```

**Пресеты:**
- `tts_alibaba` — max_chars=500
- `tts_sber` — max_chars=3500
- `tts_silero` — max_chars=800
- `llm_processing` — max_chars=10000
- `audiobook` — max_chars=2500

---

#### 2. `config_loader.py`
**Заменяет дублирование в 10+ файлов.**

**Использование:**
```python
from utils.config_loader import ConfigLoader, get_config

# Глобальный экземпляр
config = get_config()
api_key = config.get('OPENROUTER_API_KEY')

# С указанным файлом
config = ConfigLoader('config.env')

# Модели
model_config = config.get_model('quality')
print(model_config.name)  # модель
print(model_config.max_tokens)

# Готовые конфигурации
or_config = config.get_openrouter_config()
alibaba_config = config.get_alibaba_config()
```

---

#### 3. `openrouter_client.py`
**Унифицированный клиент для OpenRouter API.**

**Использование:**
```python
from utils.openrouter_client import OpenRouterClient, get_client

client = get_client()

# Простой запрос
response = client.chat("Привет!")

# С системным промптом
response = client.chat_with_system(
    system="Ты эксперт по Python",
    user="Как работают декораторы?"
)

# Потоковый вывод
for chunk in client.chat_stream("Напиши стих"):
    print(chunk, end='')
```

---

#### 4. `base_processor.py`
**Базовый класс для всех процессоров.**

**Использование:**
```python
from utils.base_processor import BaseProcessor

class MyProcessor(BaseProcessor):
    def __init__(self, config_file=None):
        super().__init__(config_file, model_preset='quality')
    
    def process(self, text: str) -> str:
        chunks = self.split_text(text)
        results = []
        for chunk in chunks:
            result = self.call_api(chunk)
            results.append(result)
        return '\n\n'.join(results)
    
    def process_file(self, input_file: str, output_file: str):
        text = self.read_file(input_file)
        result = self.process(text)
        self.write_file(output_file, result)
        return self.create_report()
```

---

### Bash модули в `lib/common/`

#### `utils.sh`
Общие утилиты для всех пайплайнов:
- `log_header()`, `log_step()`, `log_success()`, `log_error()`
- `check_file_exists()`, `check_required_vars()`
- `wait_for_file()`, `is_file_fresh()`
- `ask_yes_no()`, `ask_select()`

#### `tts.sh`
Унифицированный синтез речи:
- `synthesize_speech()` — автоматический выбор движка
- `synthesize_alibaba()`, `synthesize_silero()`, `synthesize_sber()`
- `wait_for_user_audio()`, `ensure_audio_exists()`

#### `video.sh`
Генерация видео:
- `generate_illustration_prompts()`
- `generate_illustrations()`
- `generate_final_video()`
- `generate_cover()`
- `create_short()`, `interactive_create_shorts()`

#### `promo.sh`
Промо-материалы:
- `generate_promo()`
- `generate_pikabu_article()`
- `export_to_html()`
- `correct_text()`

---

## ✅ Фаза 2: Прогресс миграции

### Созданные примеры миграции

#### 1. `text_processors/summary_processor_refactored.py`
**До:** 689 строк с дублированным кодом
**После:** ~350 строк, использует BaseProcessor

**Удалено:**
- `load_config()` → ConfigLoader (~35 строк)
- `split_text_into_chunks()` → utils.text_splitter (~30 строк)
- API-вызовы → OpenRouterClient (~50 строк)

#### 2. `speech_processors/base_tts.py`
Базовый класс для всех TTS-провайдеров:
- Унифицированный интерфейс
- Автоматическое разбиение на чанки
- Объединение аудио
- Регистр движков

#### 3. `speech_processors/alibaba_tts_v2.py`
**До:** 221 строка с дублированием
**После:** ~120 строк, использует BaseTTS

**Удалено:**
- `split_text_into_chunks()` → BaseTTS (~55 строк)
- Объединение аудио → BaseTTS (~30 строк)

---

### ✅ Фаза 2: Завершённые миграции

#### 4. `text_processors/correction_processor_v2.py`
**До:** 376 строк с дублированием
**После:** ~280 строк, использует BaseProcessor

**Удалено:**
- `load_config()` → ConfigLoader (~15 строк)
- `split_text()` → utils.text_splitter (~15 строк)
- Прямые API-вызовы → OpenRouterClient (~40 строк)

#### 5. `text_processors/audiobook_processor_v2.py`
**До:** 435 строк с дублированием
**После:** ~280 строк, использует BaseProcessor

**Удалено:**
- `split_text_into_chunks()` → utils.text_splitter (~55 строк)
- Прямые API-вызовы → OpenRouterClient (~50 строк)
- Общая логика процессора → BaseProcessor (~50 строк)

#### 6. `speech_processors/silero_v2.py`
**До:** 183 строк с дублированием
**После:** ~140 строк, использует BaseTTS

**Удалено:**
- `split_text_into_chunks()` → BaseTTS (~55 строк)
- Объединение аудио → BaseTTS (~30 строк)

#### 7. `speech_processors/sber_tts_v2.py`
**До:** 173 строк с дублированием
**После:** ~180 строк, использует BaseTTS

**Удалено:**
- `split_text_into_chunks()` → utils.text_splitter (~30 строк)
- Общая логика → BaseTTS (~40 строк)

---

## 📋 Оставшиеся задачи

### Фаза 2 (завершение)

1. **text_processors/:**
   - [x] `summary_processor_refactored.py` — пример миграции
   - [x] `correction_processor_v2.py` — миграция
   - [x] `audiobook_processor_v2.py` — миграция
   - [ ] Миграция остальных процессоров (опционально)

2. **speech_processors/:**
   - [x] `base_tts.py` — базовый класс
   - [x] `alibaba_tts_v2.py` — миграция
   - [x] `silero_v2.py` — миграция
   - [x] `sber_tts_v2.py` — миграция

3. **video_processors/:**
   - [ ] Миграция на ConfigLoader
   - [ ] Миграция на OpenRouterClient

### ✅ Фаза 3: Миграция bash-скриптов (завершена)

1. **lib/common/ — новые общие модули:**
   - [x] `audio.sh` — унифицированные функции TTS и транскрибации
   - [x] `music.sh` — добавление фоновой музыки

2. **lib/manim/ — обновлённые модули:**
   - [x] `utils_v2.sh` — делегирует в `lib/common/utils.sh`
   - [x] `02_audio_v2.sh` — использует `lib/common/audio.sh`

3. **lib/vd/ — обновлённые модули:**
   - [x] `utils_v2.sh` — делегирует в `lib/common/utils.sh`
   - [x] `05_video_v2.sh` — убран кросс-импорт с lib/manim/

4. **Пайплайн-скрипты:**
   - [x] `process_manim_v2.sh` — использует lib/common/
   - [x] `process_vd_v2.sh` — использует lib/common/

**Устранено:**
- Кросс-импорт `lib/vd/05_video.sh` → `lib/manim/02_audio.sh`
- Дублирование функций `log_step()`, `log_header()`, `check_file_exists()`
- Дублирование выбора TTS-движка

---

## 📊 Результат (Фазы 1-3)

| Метрика | До | После |
|---------|-----|-------|
| Дублирование `split_text` | 8 файлов | 1 файл |
| Дублирование `load_config` | 10+ файлов | 1 файл |
| Кросс-зависимости bash | 2 цикла | 0 |
| Базовые классы Python | 0 | 2 |
| Общие bash-модули | 1 | 4 |

---

## 🚀 Как начать использовать

### В новых процессорах

```python
from utils import ConfigLoader, OpenRouterClient, split_text_into_chunks

config = ConfigLoader()
client = OpenRouterClient(config)

def process_text(text: str) -> str:
    chunks = split_text_into_chunks(text, preset='llm_processing')
    results = [client.chat(chunk) for chunk in chunks]
    return '\n\n'.join(results)
```

### В новых bash-скриптах

```bash
#!/bin/bash
source lib/common/utils.sh
source lib/common/tts.sh
source lib/common/video.sh

log_header "Мой пайплайн"
# ... код ...
```

### Использование TTS

```python
from speech_processors import get_tts_engine, list_engines

# Показать доступные движки
print(list_engines())  # ['alibaba', 'silero', 'sber']

# Создать TTS инстанс
tts = get_tts_engine('alibaba', voice='Cherry')

# Синтезировать файл
result = tts.synthesize_file('input.txt', 'output.wav')
if result.success:
    print(f"Аудио создано: {result.output_file}")
    print(f"Длительность: {result.duration_seconds:.1f} сек")
```
