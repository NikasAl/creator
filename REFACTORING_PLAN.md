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
**Заменяет дублирование в 10+ файлах.**

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

## 📋 Следующие шаги

### Фаза 2: Миграция существующих процессоров

1. **Обновить text_processors/:**
   - Наследовать от `BaseProcessor`
   - Использовать `split_text_into_chunks`
   - Использовать `ConfigLoader`

2. **Обновить speech_processors/:**
   - Создать базовый класс `BaseTTS`
   - Использовать `split_text_into_chunks` с пресетами

3. **Обновить video_processors/:**
   - Использовать `ConfigLoader`
   - Использовать `OpenRouterClient`

### Фаза 3: Миграция bash-скриптов

1. **Обновить lib/manim/:**
   - Заменить `log_step()` на общий из `lib/common/utils.sh`
   - Использовать `lib/common/tts.sh`

2. **Обновить lib/vd/:**
   - Убрать кросс-импорт с lib/manim/
   - Использовать общие функции

3. **Обновить process_*.sh:**
   - Подключать `lib/common/` вместо дублирования

---

## 📊 Ожидаемый результат

| Метрика | До | После |
|---------|-----|-------|
| Дублирование `split_text` | 8 файлов | 1 файл |
| Дублирование `load_config` | 10+ файлов | 1 файл |
| Кросс-зависимости | 2 цикла | 0 |
| Базовые классы | 0 | 2+ |

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
