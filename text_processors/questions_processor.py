#!/usr/bin/env python3
"""
Процессор для генерации ответов на вопросы по тексту обсуждения.
"""

import os
import sys
import argparse
import time
import requests
import subprocess
from pathlib import Path
from dotenv import load_dotenv

class QuestionsProcessor:
    def __init__(self, config_file: str = None):
        """Инициализация процессора с загрузкой конфигурации"""
        self.load_config(config_file)
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/video-discussion",
            "X-Title": "Questions Processor"
        }

    def load_config(self, config_file: str = None):
        """Загружает конфигурацию из .env файла"""
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            for env_file in [".env", "config.env", "settings.env"]:
                if Path(env_file).exists():
                    load_dotenv(env_file)
                    break

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")
        self.temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.5"))
        self.max_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "2000"))
        self.budget_model = os.getenv("BUDGET_MODEL", "meta-llama/llama-3.1-8b-instruct")
        self.quality_model = os.getenv("QUALITY_MODEL", "openai/gpt-4o")

    def create_prompt(self, discussion_text: str, questions_text: str) -> str:
        """Создает промпт для генерации ответов"""
        return f"""
Ты — эксперт и внимательный собеседник. Тебе предоставлен текст обсуждения и список вопросов, возникших у читателя.

ТВОЯ ЗАДАЧА:
Дать развернутые, понятные и точные ответы на вопросы пользователя, основываясь на своих знаниях как эксперта в обсуждаемой области.

ФОРМАТ ОТВЕТА:
- Используй Markdown.
- Для каждого вопроса используй заголовок уровня 3 (### Вопрос).
- Сразу под заголовком пиши ответ.

ТЕКСТ ОБСУЖДЕНИЯ:
{discussion_text}

ВОПРОСЫ ПОЛЬЗОВАТЕЛЯ:
{questions_text}

ОТВЕТЫ:
""".strip()

    def generate_answers(self, prompt: str, model_choice: str = "default") -> str:
        """Отправляет запрос к LLM"""
        model = self.model
        if model_choice == "budget":
            model = self.budget_model
        elif model_choice == "quality":
            model = self.quality_model

        print(f"🔍 Используемая модель: {model}")

        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=120
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return content
                else:
                    print(f"⚠️ Ошибка API {resp.status_code}: {resp.text}")
                    if resp.status_code == 429:
                        time.sleep(2 ** (attempt + 1))
            except Exception as e:
                print(f"⚠️ Ошибка соединения: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
        
        raise RuntimeError("Не удалось получить ответ от LLM после 3 попыток")

    def process(self, discussion_path: str, questions_path: str, output_path: str, model_choice: str):
        d_path = Path(discussion_path)
        q_path = Path(questions_path)
        o_path = Path(output_path)

        if not d_path.exists():
            raise FileNotFoundError(f"Файл обсуждения не найден: {d_path}")
        if not q_path.exists():
            raise FileNotFoundError(f"Файл вопросов не найден: {q_path}")

        discussion_text = d_path.read_text(encoding="utf-8")
        questions_text = q_path.read_text(encoding="utf-8").strip()

        if not questions_text:
            print("⚠️ Файл вопросов пуст. Генерация пропущена.")
            return

        print(f"⏳ Генерация ответов на вопросы...")
        prompt = self.create_prompt(discussion_text, questions_text)

        # === РЕЖИМ CUSTOM (РУЧНОЙ) ===
        if model_choice == "custom":
            print("\n" + "="*60)
            print("🤖 РЕЖИМ CUSTOM MODEL: ГЕНЕРАЦИЯ ОТВЕТОВ НА ВОПРОСЫ")
            print("="*60)
            print("1. Скопируйте промпт ниже и отправьте его в чат (ChatGPT/Claude).")
            print("-" * 60)
            print(prompt)
            print("-" * 60)

            # Создаем пустой файл, если нет
            if not o_path.exists():
                o_path.write_text("", encoding="utf-8")

            print(f"2. Открывается Sublime Text: {output_path}")
            print("3. Вставьте результат генерации в файл, сохраните и закройте вкладку редактора.")

            try:
                subprocess.run(["subl", "-w", output_path], check=True)
                print(f"✅ Файл сохранен (Custom): {output_path}")
            except FileNotFoundError:
                print("❌ Sublime Text (subl) не найден. Отредактируйте файл вручную.")
                input("Нажмите Enter, когда сохраните файл...")
            return

        answers = self.generate_answers(prompt, model_choice)

        o_path.write_text(answers, encoding="utf-8")
        print(f"✅ Ответы сохранены в: {o_path}")

def main():
    parser = argparse.ArgumentParser(description="Генерация ответов на вопросы по обсуждению")
    parser.add_argument("--discussion", required=True, help="Путь к файлу обсуждения (discussion.txt)")
    parser.add_argument("--questions", required=True, help="Путь к файлу с вопросами (questions.txt)")
    parser.add_argument("--output", required=True, help="Путь для сохранения ответов (answers.txt)")
    parser.add_argument("--config", help="Путь к конфигу .env")
    parser.add_argument("--model", default="default", choices=["default", "budget", "quality", "custom"], help="Выбор модели")

    args = parser.parse_args()

    try:
        processor = QuestionsProcessor(args.config)
        processor.process(args.discussion, args.questions, args.output, args.model)
        return 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
