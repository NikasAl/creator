#!/usr/bin/env python3
"""
Процессор для создания промо-описания и статей для видео на основе текстов пайплайна

Функции:
- Сканирует каталог пайплайна и собирает .txt файлы
- Формирует контекст и отправляет запрос в LLM через OpenRouter
- Генерирует контент адаптированный под платформу (YouTube, Pikabu и т.д.)
"""

import os
import sys
import argparse
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv


class PromoDescriptionProcessor:
    def __init__(self, config_file: str = None):
        """Инициализация процессора с загрузкой конфигурации"""
        self.load_config(config_file)
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/promo-description-processor",
            "X-Title": "Promo Description Processor"
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
        self.temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.7")) # Чуть выше для креатива
        self.max_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "3000"))
        self.budget_model = os.getenv("BUDGET_MODEL", "meta-llama/llama-3.1-8b-instruct")
        self.quality_model = os.getenv("QUALITY_MODEL", "openai/gpt-4o")
        self.max_context_chars = int(os.getenv("PROMO_MAX_CONTEXT_CHARS", "15000"))

    def find_text_files(self, pipeline_dir: Path, prefix: Optional[str]) -> List[Path]:
        """Возвращает список .txt файлов из каталога пайплайна с учетом префикса."""
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
        """Собирает контекст из содержимого файлов"""
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

    def create_prompt(self, context: str, title: Optional[str], audience: str, tone: str, platform: str, lang: str) -> str:
        """Создает промпт для генерации контента в зависимости от платформы"""
        title_line = f"Название/тема: {title}" if title else "Название/тема: (определи по контексту)"

        # === ЛОГИКА ДЛЯ PIKABU ===
        if platform.lower() == "pikabu":
            return f"""
Ты — популярный автор на Pikabu (или Habr), который пишет увлекательные образовательные статьи и истории о решении задач.
Твоя задача: Написать пост-лонгрид на основе предоставленного материала.

ПАРАМЕТРЫ:
- Язык: {lang}
- Платформа: Пикабу (Pikabu)
- Аудитория: {audience} (люди, любящие научпоп, IT, математику, студенты, гики)
- Тональность: {tone} (используй юмор, иронию, живой язык, избегай канцеляризмов).

СТРУКТУРА ПОСТА:
1. **Заголовок**: Кликбейтный, но честный. Смешной или интригующий.
2. **Введение (Лид)**: Опиши "боль" или проблему. Как автор столкнулся с этой задачей? Почему это сложно/интересно? Используй "Я-повествование".
3. **Основная часть**:
   - Краткое объяснение сути задачи (без перегруза формулами, "на пальцах").
   - Как мы это визуализировали (упомяни, что это сделано с помощью Manim/Python, если есть в контексте).
   - Интересные моменты решения, "подводные камни".
4. **Заключение**: Чему мы научились? Ироничный вывод.
5. **Призыв**: Ненавязчиво предложи посмотреть полное видео (оставь плейсхолдер [ССЫЛКА НА ВИДЕО]).

ФОРМАТИРОВАНИЕ:
- Используй Markdown (жирный шрифт, цитаты).
- Разбивай текст на короткие абзацы.
- Добавь места для картинок (например: [КАРТИНКА: график функции]).

{title_line}

КОНТЕКСТ (Материалы урока/видео):
{context}

ТЕКСТ СТАТЬИ:
""".strip()

        # === СТАНДАРТНАЯ ЛОГИКА (YouTube/Rutube) ===
        return f"""
Ты — опытный маркетолог и редактор видеоописаний. На основе предоставленного контекста создай сильное, цепляющее промо-описание для видео.

ТРЕБОВАНИЯ:
- Язык: {lang}
- Платформа: {platform} (учитывай лучшие практики оформления)
- Аудитория: {audience}
- Тональность: {tone}
- Длина: около 3000-5000 символов
- Структура:
  1) Короткий hook (1–2 предложения) — раскрывает интригу/ценность
  2) Основные преимущества/темы выпуска — 3–6 строк кратко и по делу
  3) Призыв к действию: подписка/лайк/комментарий
  4) Хэштеги в строку, разделенные через пробел и начинающиеся с # (5–10, уместные и несложные)
- Не используй сложный маркдаун (только базовый). Пиши естественно.
- Избегай клише и воды. Максимум конкретики.

{title_line}

КОНТЕКСТ:
{context}

ОПИСАНИЕ:
""".strip()

    def generate_description(self, context: str, model_choice: str = "default") -> Optional[str]:
        """Отправляет запрос к LLM и возвращает сгенерированное описание"""
        model = self.model
        if model_choice == "budget":
            model = self.budget_model
        elif model_choice == "quality":
            model = self.quality_model

        print(f"🔍 Используемая модель: {model}")
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": context}
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
                          audience: str, tone: str, platform: str, lang: str,
                          model_choice: str = "default", title: Optional[str] = None,
                          source_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
        """Основной метод: собирает контекст и генерирует описание"""
        pdir = Path(pipeline_dir)
        if source_file:
            sf = Path(source_file)
            if not sf.exists() or not sf.is_file():
                print(f"❌ Указанный исходный файл не найден: {sf}")
                return False, None
            txt_files = [sf]
        else:
            txt_files = self.find_text_files(pdir, prefix)

        if not txt_files:
            print("❌ Не найдены .txt файлы в каталоге пайплайна (с учетом фильтра)")
            return False, None

        print(f"🗂 Найдено txt файлов: {len(txt_files)}")
        if prefix:
            print(f"🔎 Префикс-фильтр: {prefix}")

        context = self.build_context(txt_files)
        print(f"📊 Размер контекста: {len(context)} символов")

        prompt = self.create_prompt(context, title, audience, tone, platform, lang)
        description = self.generate_description(prompt, model_choice)
        if not description:
            print("❌ Ошибка генерации контента")
            return False, None

        if not output_file:
            output_path = pdir / "promo_description.txt"
        else:
            output_path = Path(output_file)

        output_path.write_text(description, encoding="utf-8")
        print(f"✅ Результат сохранен: {output_path}")
        return True, output_path


def main():
    parser = argparse.ArgumentParser(
        description="Создание промо и статей для видео на основе текстов пайплайна",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("pipeline_dir", help="Каталог пайплайна с .txt файлами")
    parser.add_argument("-o", "--output", help="Путь к выходному файлу")
    parser.add_argument("--config", help="Путь к .env файлу с конфигурацией")
    parser.add_argument("--prefix", help="Фильтр префикса для выбора .txt файлов")
    parser.add_argument("--model", choices=["default", "budget", "quality"], default="default", help="Выбор модели")
    parser.add_argument("--audience", default="широкая аудитория", help="Описание аудитории")
    parser.add_argument("--tone", default="дружелюбный и информативный", help="Тональность текста")
    parser.add_argument("--platform", default="YouTube", help="Платформа (YouTube, Pikabu, VK...)")
    parser.add_argument("--lang", default="русский", help="Язык результата")
    parser.add_argument("--title", help="Название/тема видео")
    parser.add_argument("--source-file", help="Путь к конкретному исходному файлу (например, script.txt)")

    args = parser.parse_args()

    try:
        processor = PromoDescriptionProcessor(args.config)
        ok, out = processor.process_pipeline(
            pipeline_dir=args.pipeline_dir,
            output_file=args.output,
            prefix=args.prefix,
            audience=args.audience,
            tone=args.tone,
            platform=args.platform,
            lang=args.lang,
            model_choice=args.model,
            title=args.title,
            source_file=args.source_file
        )
        return 0 if ok else 1
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__": {
    sys.exit(main())
}