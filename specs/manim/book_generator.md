У меня есть скрипт для создания аудиокниг run_pipeline.sh (использует генерированные иллюстрации как видеоряд) и скрипт для создания математических анимаций - коротких анимаций, где иллюстрируется некоторая тема формулами и схемами реализованными на manim. Хочу сделать скрипт, которым можно визуализировать книгу по математике или физике используя комбинацию этих подходов.

Экспортируется фрагмент книги, оцифровывается, распознается, разбивается на темы, создается tts текст для озвучивания и по ней аудио с озвучкой.

Затем по каждой теме создается manim код иллюстрирующий тему и затем код синхронизируется с аудио. Так как книга может быть длинной, а LLM не сможет сгененировать длинный код анимации без потери качества, то по каждому небольшому фрагменту анимации надо создавать отдельно. Поддерживать как создание самостоятельных анимаций по темам, так и создание объединение нескольких тем как в книге.

Давай подумаем как это сделать


---


Это отличная идея. Главная проблема при визуализации книг с помощью Manim — это **контекстное окно** и **сложность кода**. Если попросить LLM написать код для 30-минутной главы, она гарантированно начнет галлюцинировать, терять скобки или создавать некомпилируемый "спагетти-код".

Решение — архитектура **"Разделяй и Властвуй" (Divide and Conquer)**.

### Архитектура решения

Мы создадим новый пайплайн `run_book_manim.sh`, который будет работать как "Оркестратор".

1.  **Фаза "Библиотекарь" (Ingestion & Splitting):**

      * Берет полный текст (из PDF или txt).
      * Использует LLM (Python-скрипт) для интеллектуального разбиения текста на **Сцены**.
      * *Критерий разбиения:* Каждая сцена — это законченная мысль/формула/диаграмма, длительностью 1-3 минуты.
      * Создает файл-манифест `project_manifest.json`.

2.  **Фаза "Аниматор" (The Loop):**

      * Скрипт проходит по `project_manifest.json`.
      * Для каждой сцены создает подпапку (например, `01_introduction`, `02_newton_law`).
      * Запускает адаптированную логику из `process_manim.sh` для этой папки.
      * **Важно:** Мы передаем "Визуальный контекст" (Style Guide) в каждую сцену, чтобы стиль (цвета, шрифты) был единым.

3.  **Фаза "Монтажер" (Assembly):**

      * Собирает все отрендеренные MP4 файлы в один длинный фильм через FFmpeg.

-----

### 1\. Python-скрипт разбиения на сцены (`text_processors/book_segmenter.py`)

Этот скрипт превращает "стену текста" в структурированный план.

````python
import os
import json
import argparse
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv

# Загрузка конфига
load_dotenv("config.env")

def split_book_into_scenes(text_content, model_name="gpt-4o"):
    llm = ChatOpenAI(model=model_name, temperature=0.4)
    
    system_prompt = """
    You are an expert educational director visualizing a technical book (Math/Physics) using Manim (Python animation library).
    
    Your goal: Split the provided text into a series of logical "Scenes".
    
    Rules for splitting:
    1. Each scene must be focused on ONE specific concept, formula derivation, or diagram.
    2. Estimated duration of a scene should be between 30 seconds and 3 minutes.
    3. If the text contains a long derivation, split it into steps.
    
    Output Format: JSON list.
    [
        {
            "id": "01",
            "title": "Short_Title_Snake_Case",
            "description": "Visual summary of what happens",
            "raw_text": " The exact text from the book covering this part..."
        },
        ...
    ]
    IMPORTANT: Do not rewrite the 'raw_text', keep it faithful to the source unless it requires minor cleaning for TTS.
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Here is the book chapter content:\n\n{text_content}")
    ]

    print("🤖 Analyzing text structure and splitting into scenes...")
    response = llm.invoke(messages)
    
    # Cleaning the response to ensure valid JSON
    content = response.content.strip()
    if content.startswith("```json"):
        content = content.replace("```json", "").replace("```", "")
    
    try:
        scenes = json.loads(content)
        return scenes
    except json.JSONDecodeError:
        print("❌ Error: LLM did not return valid JSON.")
        print(content)
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Path to text file")
    parser.add_argument("--output-dir", help="Project output directory")
    args = parser.parse_args()

    with open(args.input_file, "r", encoding="utf-8") as f:
        text = f.read()

    scenes = split_book_into_scenes(text)
    
    manifest_path = os.path.join(args.output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Manifest created with {len(scenes)} scenes at {manifest_path}")
````

### 2\. Главный скрипт оркестратор (`run_book_manim.sh`)

Этот скрипт заменяет ручной ввод. Он берет функции из ваших существующих библиотек (`lib/manim/*.sh`), но меняет контекст выполнения (переменную `OUTPUT_DIR`) в цикле.

```bash
#!/bin/bash

# run_book_manim.sh
set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <book_text.txt> <output_dir>"
    exit 1
fi

INPUT_TEXT="$1"
PROJECT_ROOT="$2"
CONFIG_FILE="config.env"

# 1. Загрузка конфигурации и библиотек
# Мы не сорсим библиотеки сразу, чтобы не засорять глобальные переменные, 
# либо делаем это аккуратно. В данном дизайне мы будем вызывать под-скрипт для каждой сцены,
# чтобы изолировать окружение.

source "$CONFIG_FILE"
mkdir -p "$PROJECT_ROOT"

echo -e "${GREEN}📚 Start Book Visualization Pipeline${NC}"
echo "Input: $INPUT_TEXT"
echo "Root: $PROJECT_ROOT"

# 2. Сегментация (Если манифеста нет)
MANIFEST_FILE="$PROJECT_ROOT/manifest.json"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "🔍 Splitting book into scenes..."
    python text_processors/book_segmenter.py "$INPUT_TEXT" --output-dir "$PROJECT_ROOT"
else
    echo "✅ Manifest found, skipping segmentation."
fi

# 3. Чтение манифеста и запуск цикла
# Используем jq для парсинга JSON (убедитесь, что jq установлен: sudo apt install jq)
SCENE_COUNT=$(jq '. | length' "$MANIFEST_FILE")

echo "🎬 Found $SCENE_COUNT scenes. Starting processing..."

for ((i=0; i<SCENE_COUNT; i++)); do
    # Извлекаем данные сцены
    ID=$(jq -r ".[$i].id" "$MANIFEST_FILE")
    TITLE=$(jq -r ".[$i].title" "$MANIFEST_FILE")
    RAW_TEXT=$(jq -r ".[$i].raw_text" "$MANIFEST_FILE")
    
    # Формируем имя папки: 01_Title
    SCENE_DIR="$PROJECT_ROOT/${ID}_${TITLE}"
    mkdir -p "$SCENE_DIR"
    
    echo -e "\n${YELLOW}▶ Processing Scene $((i+1))/$SCENE_COUNT: ${ID}_${TITLE}${NC}"
    
    # Создаем spec.txt (в данном случае это текст книги)
    echo "$RAW_TEXT" > "$SCENE_DIR/spec.txt"
    
    # Проверка: если видео уже есть, пропускаем
    if [ -f "$SCENE_DIR/video.mp4" ]; then
        echo "✅ Scene finished, skipping."
        continue
    fi

    # === ЗАПУСК МИНИ-ПАЙПЛАЙНА ДЛЯ СЦЕНЫ ===
    # Мы вызываем специальный wrapper, передавая ему папку сцены
    ./process_scene_wrapper.sh "$CONFIG_FILE" "$SCENE_DIR"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error processing scene $ID. Stopping pipeline.${NC}"
        exit 1
    fi
done

# 4. Сборка финального видео
echo -e "\n${GREEN}🎞️ Concatenating all scenes...${NC}"
CONCAT_LIST="$PROJECT_ROOT/concat_list.txt"
rm -f "$CONCAT_LIST"

# Находим все финальные video.mp4 в подпапках и сортируем их
find "$PROJECT_ROOT" -mindepth 2 -maxdepth 2 -name "video.mp4" | sort > "$PROJECT_ROOT/videos.tmp"

while read video; do
    echo "file '$video'" >> "$CONCAT_LIST"
done < "$PROJECT_ROOT/videos.tmp"
rm "$PROJECT_ROOT/videos.tmp"

FINAL_BOOK_VIDEO="$PROJECT_ROOT/full_book_movie.mp4"
ffmpeg -f concat -safe 0 -i "$CONCAT_LIST" -c copy "$FINAL_BOOK_VIDEO" -y

echo -e "${GREEN}🎉 Book visualization complete: $FINAL_BOOK_VIDEO${NC}"
```

### 3\. Обертка для обработки одной сцены (`process_scene_wrapper.sh`)

Нам нужен этот скрипт, чтобы переиспользовать логику `process_manim.sh`, но с одним важным отличием: **генерация текста**.
В `process_manim.sh` шаг `manim_step_text_gen` генерирует сценарий с нуля.
В случае книги нам нужно **адаптировать** существующий текст (из `spec.txt`) для TTS и скрипта, а не придумывать новый.

```bash
#!/bin/bash

# process_scene_wrapper.sh
# Запускает pipeline для одной конкретной папки
# Использование: ./process_scene_wrapper.sh config.env path/to/scene_dir

CONFIG_FILE="$1"
TARGET_SCENE_DIR="$2"

# 1. Переопределяем OUTPUT_DIR перед загрузкой конфига
export OUTPUT_DIR="$TARGET_SCENE_DIR"

# Загружаем конфиг (он может переопределить переменные, но мы надеемся, что он не хардкодит OUTPUT_DIR)
source "$CONFIG_FILE"
# Принудительно возвращаем OUTPUT_DIR, если конфиг его перезаписал
export OUTPUT_DIR="$TARGET_SCENE_DIR"

# Переопределяем базовые имена файлов относительно новой папки
export SPEC_FILE="$OUTPUT_DIR/spec.txt"
export SCRIPT_FILE="$OUTPUT_DIR/lesson_script.txt"
export TTS_SCRIPT_FILE="$OUTPUT_DIR/lesson_tts.txt"
export AUDIO_FILE="$OUTPUT_DIR/audio.mp3"
export MANIM_DRAFT_FILE="$OUTPUT_DIR/manim_draft.py"
export MANIM_CODE_FILE="$OUTPUT_DIR/manim_lesson.py"
export OUTPUT_VIDEO_FILE="$OUTPUT_DIR/video.mp4"
export TIMESTAMPS_FILE="sentence_timestamps.json"
export FULL_TIMESTAMPS_PATH="$OUTPUT_DIR/$TIMESTAMPS_FILE"

# Подключаем библиотеки
source "lib/manim/utils.sh"
source "lib/manim/01_text.sh"
source "lib/manim/02_audio.sh"
source "lib/manim/03_code.sh"
source "lib/manim/04_render.sh"

# === ИЗМЕНЕННЫЙ ШАГ ТЕКСТА ===
# Вместо manim_step_text_gen (который генерирует), делаем адаптацию
manim_step_book_adapt() {
    log_step "1" "Адаптация текста книги для Manim..."
    if [ ! -f "$SCRIPT_FILE" ] || [ ! -f "$TTS_SCRIPT_FILE" ]; then
        # Используем существующий processor, но с новым флагом или промптом
        # Предположим, что мы добавили action 'book_adapt' в lesson_generator.py
        python text_processors/lesson_generator.py \
            --action book_adapt \
            --input "$SPEC_FILE" \
            --output-script "$SCRIPT_FILE" \
            --output-tts "$TTS_SCRIPT_FILE" \
            --config config.env
    else
        echo "✅ Сценарии уже адаптированы."
    fi
}

# === ЗАПУСК ШАГОВ ===

# 1. Текст
manim_step_book_adapt

# 2. Аудио
# Тут важно: для полной автоматизации нам нужен AUTO-TTS, а не ручная запись.
# Если вы используете OpenAI TTS или ElevenLabs, добавьте этот шаг.
if [ ! -f "$AUDIO_FILE" ]; then
    log_step "2" "Генерация TTS (Auto)..."
    python text_processors/tts_generator.py \
        --input "$TTS_SCRIPT_FILE" \
        --output "$AUDIO_FILE" \
        --model "openai" # или system/elevenlabs
fi
# Если TTS нет, скрипт остановится на manim_step_wait_audio из utils

manim_step_transcribe

# 3. Код
manim_step_code_draft
manim_step_compile_draft_loop # В автоматическом режиме лучше убрать Loop или ограничить попытки
manim_step_code_sync

# 4. Рендер
export QUALITY="medium" # Для книг лучше medium, чтобы быстрее
manim_step_render_final
manim_step_video_sync

echo "✅ Scene processed: $(basename "$OUTPUT_DIR")"
```

### Необходимые доработки в Python-коде

Вам нужно добавить режим `book_adapt` в файл `text_processors/lesson_generator.py`.

Логика `book_adapt`:

1.  **Input:** Сырой текст параграфа из книги.
2.  **Prompt:** "Перепиши этот текст в формат сценария для Manim.
      * `lesson_tts.txt`: Текст для диктора. Слегка упрости сложные обороты, сделай более разговорным, но сохрани все термины.
      * `lesson_script.txt`: Разбей на логические фразы и опиши, что должно происходить на экране в этот момент (формулы, графики)."

### Резюме изменений

1.  **Новый скрипт `run_book_manim.sh`**: Управляет процессом, разбивает книгу на сцены.
2.  **Новый скрипт `text_processors/book_segmenter.py`**: Использует LLM для умной нарезки книги на JSON-манифест.
3.  **Враппер `process_scene_wrapper.sh`**: Позволяет запускать Manim-пайплайн изолированно для каждой папки-сцены.
4.  **Автоматизация TTS**: В `process_manim.sh` был шаг "Wait Audio" (человек в контуре). Для книги это нереально. Нужно добавить скрипт `tts_generator.py` (через OpenAI API или локальный Silero/Coqui), который будет генерировать озвучку автоматически внутри враппера.

Хотите, я напишу код для `lesson_generator.py` (режим book\_adapt) или для `tts_generator.py`?