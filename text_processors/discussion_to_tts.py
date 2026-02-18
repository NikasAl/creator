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


def get_prompts(context, input_text):
    context_prompts = {
        "news_summary": f"""
    ТЫ: Профессиональный диктор и журналист.
    ЗАДАЧА: Адаптировать текст новости для озвучки в подкасте.

    ИСХОДНЫЙ ТЕКСТ НОВОСТИ:
    {input_text}

    ТРЕБОВАНИЯ К АДАПТАЦИИ:
    1. Убери все markdown-теги (жирный шрифт, заголовки), оставь только чистый текст для чтения.
    2. Замени все цифры и числа словами.
       Пример: "5 человек" -> "пять человек", "в 2025 году" -> "в две тысячи двадцать пятом году".
    3. Убери ссылки, цитаты и технические пометки.
    4. Сохрани естественную структуру абзацев для удобных пауз при озвучке.
    5. Сделай стиль более разговорным, как в новостном подкасте.
    """,
        "educational": f"""
    ТЫ: Опытный репетитор по математике/физике.
    ЗАДАЧА: Адаптировать образовательный текст для озвучки.

    ИСХОДНЫЙ ТЕКСТ УРОКА:
    {input_text}

    ТРЕБОВАНИЯ К АДАПТАЦИИ:
    1. Убери весь LaTeX. Замени формулы на то, как они читаются словами (фонетически).
       Пример: $\\int_0^1 x dx$ -> "интеграл от нуля до единицы икс дэ икс".
    2. Замени все цифры и числа словами.
       Пример: "5 яблок" -> "пять яблок", "в 1990 году" -> "в тысяча девятьсот девяностом году".
    3. Убери любые markdown-теги (жирный шрифт, заголовки), оставь только чистый текст для чтения.
    4. Сохрани структуру абзацев, чтобы паузы были естественными.
    """,
        "general": f"""
    ТЫ: Профессиональный редактор.
    ЗАДАЧА: Адаптировать любой текст для системы синтеза речи (TTS).

    ИСХОДНЫЙ ТЕКСТ:
    {input_text}

    ТРЕБОВАНИЯ К АДАПТАЦИИ:
    1. Убери все markdown-теги (жирный шрифт, заголовки), оставь только чистый текст для чтения.
    2. Замени все цифры и числа словами.
       Пример: "5 раз" -> "пять раз", "в 2024 году" -> "в две тысячи двадцать четвертом году".
    3. Убери ссылки, цитаты и технические пометки.
    4. Сделай стиль более разговорным и естественным для озвучки.
    5. Сохрани структуру абзацев для естественных пауз при чтении.
    """
    }
    
    return context_prompts.get(context, context_prompts["general"])


def process_request(input_file, output_path, context, model, config_file):
    if config_file: 
        load_dotenv(config_file)
    else: 
        load_dotenv()

    # Читаем входной файл
    if not os.path.exists(input_file):
        print(f"❌ Ошибка: Входной файл не найден: {input_file}")
        exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()

    prompt_text = get_prompts(context, input_text)

    # === РЕЖИМ CUSTOM (РУЧНОЙ) ===
    if model == "custom":
        print("\n" + "="*60)
        print(f"🤖 РЕЖИМ CUSTOM MODEL: АДАПТАЦИЯ ДЛЯ TTS")
        print("="*60)
        print(f"1. Скопируйте промпт ниже и отправьте его в чат (ChatGPT/Claude).")
        
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

    messages = [{"role": "system", "content": "Ты — помощник по созданию контента для озвучки."}]
    user_content = [{"type": "text", "text": prompt_text}]

    messages.append({"role": "user", "content": user_content})

    print(f"🧠 Запрос к LLM ({model})... Адаптация текста для TTS")
    
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
    parser.add_argument("--input", required=True, help="Путь к входному файлу с текстом")
    parser.add_argument("--output", required=True, help="Путь к выходному файлу")
    parser.add_argument("--context", choices=["news_summary", "educational", "general"], default="general", 
                       help="Контекст адаптации текста")
    parser.add_argument("--model", default="custom", help="Модель LLM или 'custom'")
    parser.add_argument("--config", help="Путь к config.env")
    
    args = parser.parse_args()
    process_request(args.input, args.output, args.context, args.model, args.config)
