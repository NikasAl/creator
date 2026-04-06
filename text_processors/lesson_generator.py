#!/usr/bin/env python3
import argparse
import os
import base64
import requests
import subprocess
from dotenv import load_dotenv

def encode_image(image_path):
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_prompts(action, input_text):
    if action == "generate":
        return f"""
    ТЫ: Опытный репетитор по математике/физике.
    ЗАДАЧА: Написать текст закадрового голоса для видео-урока на основе заметок пользователя.
    
    ВВОДНЫЕ ДАННЫЕ (Заметки и ход решения):
    {input_text}
    
    СТРУКТУРА СЦЕНАРИЯ:
    1. Формулировка проблемы и ошибки ученика.
    2. Разбор решения (пошагово).
    3. Выводы и чему мы научились.
    
    ТРЕБОВАНИЯ К ТЕКСТУ:
    - Разговорный стиль, как в хорошем науч-поп видео.
    - Обязательно используй LaTeX для формул (например, $\\frac{{a}}{{b}}$), это нужно для анимации.
    - Разбей текст на абзацы для удобства чтения.
    """
    elif action == "adapt":
        return f"""
    ТЫ: Редактор текста для диктора и систем синтеза речи (TTS).
    ЗАДАЧА: Адаптировать текст урока для озвучивания.
    
    ИСХОДНЫЙ ТЕКСТ УРОКА:
    {input_text}
    
    ТРЕБОВАНИЯ К АДАПТАЦИИ:
    1. Убери весь LaTeX. Замени формулы на то, как они читаются словами (фонетически).
       Пример: $\\int_0^1 x dx$ -> "интеграл от нуля до единицы икс дэ икс".
    2. Замени все цифры и числа словами.
       Пример: "5 яблок" -> "пять яблок", "в 1990 году" -> "в тысяча девятьсот девяностом году".
    3. Убери любые markdown-теги (жирный шрифт, заголовки), оставь только чистый текст для чтения.
    4. Сохрани структуру абзацев, чтобы паузы были естественными.
    """
    elif action == "podcast":
            return f"""
    ТЫ: Профессиональный монтажер и сценарист YouTube-роликов.
    ЗАДАЧА: Превратить транскрипт записи экрана c таймстампами в четкий, динамичный закадровый текст с указанием пауз между блоками текста
    в формате [[PAUSE:<количество секунд>]] так чтобы сохранилась синхронизации времени между исходным видео и синтезированным текстом.

    ТРАНСКРИБАЦИЯ (Слова автора во время записи):
    {input_text}

    ЦЕЛЬ:
    Создать текст, который будет озвучен поверх этого же видео. Текст должен совпадать по смыслу с происходящим, но быть умнее и профессиональнее.

    ТРЕБОВАНИЯ:
    1. Сохрани хронологию событий (это важно для синхронизации с видео).
    2. Убери слова-паразиты, паузы, мычание.
    3. Стиль: Дружелюбный, экспертный, динамичный.
    4. Не используй заголовки и маркдаун, только текст для озвучки. Разбей на абзацы по смысловым сценам.
    5. Вставляй паузы между абзацами в формате [[PAUSE:<количество секунд>]]
    6. Для расчета длительности пауз используй следующую скорость чтения (12 символов в секунду ~ 740 символов в минуту. Это получено из оценки, что 3325 символов текста озвучено в 270 секундный mp3 файл).
    7. Старайся уравнять длину полученного текста и пауз с длиной исходной транскрипции. Если не получается, то можно сделать общую длину транскрипции сохранив пропорции между длинами фрагментов. Это сработает так как при наложении видео оно будет ускорено/замедленно так, что бы длительность закадрового голоса в точности совпала с длительностью видео.
    ВАЖНО! Если получаются паузы более 3х сек между фрагментами, то увеличим количество текста, добавив подходящих мыслей и рассуждений так чтобы не оказалось больших пауз. 
    """
    return ""

def process_request(action, input_file, image_path, output_path, model, config_file):
    if config_file: load_dotenv(config_file)
    else: load_dotenv()

    # Читаем входной файл
    if not os.path.exists(input_file):
        print(f"❌ Ошибка: Входной файл не найден: {input_file}")
        exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()

    prompt_text = get_prompts(action, input_text)

    # === РЕЖИМ CUSTOM (РУЧНОЙ) ===
    if model == "custom":
        step_name = "ГЕНЕРАЦИЯ СЦЕНАРИЯ" if action == "generate" else "АДАПТАЦИЯ ДЛЯ TTS"
        print("\n" + "="*60)
        print(f"🤖 РЕЖИМ CUSTOM MODEL: {step_name}")
        print("="*60)
        print(f"1. Скопируйте промпт ниже и отправьте его в чат (ChatGPT/Claude).")
        
        if action == "generate" and image_path:
             print(f"2. 📎 ПРИКРЕПИТЕ КАРТИНКУ: {image_path}")
        
        print("-" * 60)
        print(prompt_text)
        print("-" * 60)
        
        # Создаем пустой файл, если нет
        if not os.path.exists(output_path):
            open(output_path, 'w').close()
            
        print(f"3. Открывается Sublime Text: {output_path}")
        print("4. Вставьте результат генерации в файл, сохраните и закройте вкладку редактора.")
        
        try:
            subprocess.run(["subl", "-w", output_path], check=True)
            print(f"✅ Файл сохранен (Custom): {output_path}")
        except FileNotFoundError:
            print("❌ Sublime Text (subl) не найден. Отредактируйте файл вручную.")
            input("Нажмите Enter, когда сохраните файл...")
        return

    # === РЕЖИМ API ===
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Ошибка: Не задан OPENROUTER_API_KEY")
        exit(1)

    messages = [{"role": "system", "content": "Ты — помощник по созданию образовательного контента."}]
    user_content = [{"type": "text", "text": prompt_text}]

    # Картинку добавляем только на этапе генерации
    if action == "generate" and image_path:
        base64_image = encode_image(image_path)
        if base64_image:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

    messages.append({"role": "user", "content": user_content})

    print(f"🧠 Запрос к LLM ({model})... Действие: {action}")
    
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o" if model == "quality" else model,
                "messages": messages
            }
        )

        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Результат сохранен: {output_path}")
        else:
            print(f"❌ Ошибка API: {resp.status_code} - {resp.text}")
            exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка запроса: {e}")
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["generate", "adapt", "podcast"], required=True, help="generate: создание урока, adapt: подготовка для TTS")
    parser.add_argument("--input", required=True, help="Путь к файлу с вводными данными (spec.txt или lesson_script.txt)")
    parser.add_argument("--image", help="Путь к изображению (только для action=generate)")
    parser.add_argument("--output", required=True, help="Путь к выходному файлу")
    parser.add_argument("--model", default="custom", help="Модель LLM или 'custom'")
    parser.add_argument("--config", help="Путь к config.env")
    
    args = parser.parse_args()
    process_request(args.action, args.input, args.image, args.output, args.model, args.config)
