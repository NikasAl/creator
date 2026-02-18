#!/usr/bin/env python3
"""
Процессор для создания статьи для блога на основе текстов пайплайна

Функции:
- Сканирует каталог пайплайна и собирает .txt файлы (с опциональным префикс-фильтром)
- Формирует контекст и отправляет запрос в LLM через OpenRouter
- Генерирует структурированную статью для блога
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from dotenv import load_dotenv


class BlogArticleProcessor:
    def __init__(self, config_file: str = None):
        self.load_config(config_file)
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/blog-article-processor",
            "X-Title": "Blog Article Processor"
        }

    def load_config(self, config_file: str = None):
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            for env_file in [".env", "config.env", "settings.env"]:
                if Path(env_file).exists():
                    load_dotenv(env_file)
                    break

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")
        self.temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.4"))
        self.max_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "4000"))
        self.budget_model = os.getenv("BUDGET_MODEL", "meta-llama/llama-3.1-8b-instruct")
        self.quality_model = os.getenv("QUALITY_MODEL", "openai/gpt-4o")
        self.max_context_chars = int(os.getenv("BLOG_MAX_CONTEXT_CHARS", "30000"))

    def find_text_files(self, pipeline_dir: Path, prefix: Optional[str]) -> List[Path]:
        if not pipeline_dir.exists() or not pipeline_dir.is_dir():
            raise FileNotFoundError(f"Каталог пайплайна не найден: {pipeline_dir}")
        txt_files = [p for p in sorted(pipeline_dir.glob("*.txt"))]
        if prefix:
            def _matches_prefix(path: Path) -> bool:
                stem = path.stem
                if "_" not in stem:
                    return False
                last_token = stem.split("_")[-1]
                return last_token == prefix

            txt_files = [p for p in txt_files if _matches_prefix(p)]
        return txt_files

    def build_context(self, files: List[Path]) -> str:
        parts: List[str] = []
        total = 0
        for fp in files:
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            header = f"\n===== ФАЙЛ: {fp.name} =====\n"
            chunk = header + text.strip() + "\n"
            if total + len(chunk) > self.max_context_chars:
                remaining = max(self.max_context_chars - total, 0)
                if remaining > 0:
                    parts.append(chunk[:remaining])
                    total += remaining
                break
            parts.append(chunk)
            total += len(chunk)
        return "".join(parts).strip()

    def create_prompt(self, context: str, title: Optional[str], audience: str, tone: str, lang: str) -> str:
        title_line = f"Заголовок статьи: {title}" if title else "Заголовок статьи: (предложи сам по контексту)"
        return f"""
Ты — опытный автор и редактор технических и образовательных блогов. Напиши цельную, логичную и читабельную статью на основе контекста.

ТРЕБОВАНИЯ:
- Язык: {lang}
- Аудитория: {audience}
- Тональность: {tone}
- Объем: 5–10 абзацев (примерно 1200–2500 слов)
- Структура:
  - Заголовок (без маркдауна, без #)
  - Короткое интро, задающее контекст и ценность материала
  - Основные разделы (2–5), каждый с четкой идеей и примерами
  - Заключение: выводы, перспективы, рекомендации
- Правила:
  - Не используй разметку markdown (#, *) и эмодзи
  - Пиши естественным, ясным языком; избегай клише
  - Сохраняй фактическую точность; не выдумывай детали вне контекста
  - Если контекст разнороден, выбери основную тему и согласуй терминологию

{title_line}

КОНТЕКСТ:
{context}

СТАТЬЯ:
""".strip()

    def generate_article(self, prompt: str, model_choice: str = "default") -> Optional[str]:
        model = self.model
        if model_choice == "budget":
            model = self.budget_model
        elif model_choice == "quality":
            model = self.quality_model

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
                    timeout=180
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    if resp.status_code == 429:
                        time.sleep(2 ** (attempt + 1))
                    elif attempt < 2:
                        time.sleep(2 ** attempt)
            except Exception:
                if attempt < 2:
                    time.sleep(2 ** attempt)
        return None

    def process_pipeline(self, pipeline_dir: str, output_file: Optional[str], prefix: Optional[str],
                          audience: str, tone: str, lang: str,
                          model_choice: str = "default", title: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
        pdir = Path(pipeline_dir)
        txt_files = self.find_text_files(pdir, prefix)
        if not txt_files:
            print("❌ Не найдены .txt файлы в каталоге пайплайна (с учетом фильтра)")
            return False, None

        print(f"🗂 Найдено txt файлов: {len(txt_files)}")
        if prefix:
            print(f"🔎 Префикс-фильтр: {prefix}")

        context = self.build_context(txt_files)
        print(f"📊 Размер контекста: {len(context)} символов (лимит {self.max_context_chars})")

        prompt = self.create_prompt(context, title, audience, tone, lang)
        article = self.generate_article(prompt, model_choice)
        if not article:
            print("❌ Ошибка генерации статьи")
            return False, None

        if not output_file:
            output_path = pdir / "blog_article.txt"
        else:
            output_path = Path(output_file)

        output_path.write_text(article, encoding="utf-8")
        print(f"✅ Статья сохранена: {output_path}")
        return True, output_path


def main():
    parser = argparse.ArgumentParser(
        description="Создание статьи для блога на основе текстов пайплайна",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python blog_article_processor.py /path/to/pipeline_dir
  python blog_article_processor.py /path/to/pipeline_dir --prefix notes_ -o article.txt
  python blog_article_processor.py /path/to/pipeline_dir --model quality --audience "широкая аудитория" --tone "нейтральный"
        """
    )

    parser.add_argument("pipeline_dir", help="Каталог пайплайна с .txt файлами")
    parser.add_argument("-o", "--output", help="Путь к выходному файлу (по умолчанию: blog_article.txt в каталоге пайплайна)")
    parser.add_argument("--config", help="Путь к .env файлу с конфигурацией")
    parser.add_argument("--prefix", help="Фильтр префикса для выбора .txt файлов")
    parser.add_argument("--model", choices=["default", "budget", "quality"], default="default", help="Выбор модели")
    parser.add_argument("--audience", default="широкая аудитория", help="Описание аудитории")
    parser.add_argument("--tone", default="информативный и дружелюбный", help="Тональность текста")
    parser.add_argument("--lang", default="русский", help="Язык результата")
    parser.add_argument("--title", help="Необязательный заголовок статьи")

    args = parser.parse_args()

    try:
        processor = BlogArticleProcessor(args.config)
        ok, out = processor.process_pipeline(
            pipeline_dir=args.pipeline_dir,
            output_file=args.output,
            prefix=args.prefix,
            audience=args.audience,
            tone=args.tone,
            lang=args.lang,
            model_choice=args.model,
            title=args.title
        )
        return 0 if ok else 1
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


