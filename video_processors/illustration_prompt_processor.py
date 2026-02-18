#!/usr/bin/env python3
"""
Процессор для генерации промптов иллюстраций по частям исходного текста

Функции:
- Разбивает входной текст на заданное количество частей, стараясь сохранять абзацы
- Для каждой части запрашивает у LLM краткое и чёткое описание иллюстрации
- Собирает все описания в единый JSON для дальнейшей генерации изображений
"""

import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

import requests
from dotenv import load_dotenv


class IllustrationPromptProcessor:
    def __init__(self, config_file: Optional[str] = None):
        """Инициализация: загрузка конфигурации и настройка API"""
        self._load_config(config_file)

        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/illustration-prompt-processor",
            "X-Title": "Illustration Prompt Processor",
        }

        self.stats = {
            "parts_requested": 0,
            "parts_created": 0,
            "api_calls": 0,
            "total_tokens_used": 0,
            "processing_time": 0.0,
        }

    def _load_config(self, config_file: Optional[str]):
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            for env_name in [".env", "config.env", "settings.env"]:
                if Path(env_name).exists():
                    load_dotenv(env_name)
                    break

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")
        self.temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))
        # Токены для коротких JSON-ответов
        self.max_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "800"))

        # Альтернативные модели
        self.budget_model = os.getenv("BUDGET_MODEL", "meta-llama/llama-3.1-8b-instruct")
        self.quality_model = os.getenv("QUALITY_MODEL", "openai/gpt-4o")

    # ---------- Разбиение текста ----------
    def _split_into_n_parts(self, text: str, parts: int) -> List[str]:
        """Разбивает текст на N частей, стараясь делить по абзацам и предложениям."""
        if parts <= 1:
            return [text.strip()] if text.strip() else []

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        total_len = sum(len(p) for p in paragraphs) + 2 * max(0, len(paragraphs) - 1)
        target = max(1, total_len // parts)

        parts_accumulated: List[str] = []
        current = ""

        def push_current():
            nonlocal current
            if current.strip():
                parts_accumulated.append(current.strip())
            current = ""

        for idx, para in enumerate(paragraphs):
            sep = "\n\n" if current else ""
            candidate = current + (sep + para if para else "")

            # Если текущая часть уже достаточно велика и впереди ещё абзацы — фиксируем
            remaining_paragraphs = len(paragraphs) - (idx + 1)
            remaining_slots = max(0, parts - len(parts_accumulated) - 1)
            if len(candidate) >= target and remaining_paragraphs >= remaining_slots:
                current = candidate
                push_current()
            else:
                current = candidate

        # Хвост
        push_current()

        # Если частей получилось меньше запрошенного, пробуем дорезать самые длинные
        while len(parts_accumulated) < parts:
            if not parts_accumulated:
                break
            # выбираем самую длинную часть
            longest_i = max(range(len(parts_accumulated)), key=lambda i: len(parts_accumulated[i]))
            longest = parts_accumulated.pop(longest_i)
            # пытаемся делить по предложениям
            sentences = re.split(r"(?<=[.!?])\s+", longest)
            if len(sentences) < 2:
                # не получилось — возвращаем и выходим
                parts_accumulated.insert(longest_i, longest)
                break
            mid = max(1, len(sentences) // 2)
            left = " ".join(sentences[:mid]).strip()
            right = " ".join(sentences[mid:]).strip()
            if left and right:
                parts_accumulated.insert(longest_i, right)
                parts_accumulated.insert(longest_i, left)
            else:
                parts_accumulated.insert(longest_i, longest)
                break

        # Если частей больше, чем нужно, объединяем последние
        while len(parts_accumulated) > parts:
            a = parts_accumulated.pop()
            parts_accumulated[-1] = (parts_accumulated[-1] + "\n\n" + a).strip()

        return parts_accumulated

    # ---------- Промпт к LLM ----------
    def _build_llm_prompt(self, part_text: str, index: int, total: int, style: Optional[str],
                          book_title: Optional[str], book_author: Optional[str]) -> str:
        style_hint = ""
        if style:
            style_hint = f"\n- Visual style preference: {style}"

        book_hint = ""
        if book_title or book_author:
            title = book_title or "Unknown title"
            author = book_author or "Unknown author"
            book_hint = f"\n- Book context: '{title}' by {author}"

        return (
            f"You are an expert visual storyteller and prompt engineer for image generation.\n"
            f"Your task is to produce ONE concise image prompt that visually illustrates the essence of the given text fragment {index} of {total}.\n\n"
            "Requirements:\n"
            "- Output strictly valid JSON with keys: prompt (string), negative_prompt (string), title (string).\n"
            "- The prompt MUST be in English, 1-3 sentences, vivid, concrete, describing scene, subjects, setting, composition, mood, lighting, and key symbols.\n"
            "- Avoid quoting the source text; convert abstract ideas into visual metaphors.\n"
            "- Prefer third-person, present tense; avoid camera/brand names unless essential.\n"
            "- negative_prompt should include: text, watermark, logo, low quality, blurry, distorted, extra limbs, deformed, cropped, frame\n"
            f"{style_hint}{book_hint}\n\n"
            "JSON only. No extra commentary.\n\n"
            "SOURCE TEXT:\n"
            "\"\"\"\n"
            f"{part_text}\n"
            "\"\"\"\n"
        )

    def _call_llm(self, prompt: str, retry_count: int = 3) -> Optional[Dict[str, str]]:
        def _strip_code_fences(text: str) -> str:
            text = text.strip()
            if text.startswith("```") and text.endswith("```"):
                inner = text[3:-3]
                inner = inner.lstrip("\n").lstrip()
                if inner.lower().startswith("json\n"):
                    inner = inner[5:]
                return inner.strip()
            return text

        def _try_parse_json_from(content: str) -> Optional[Dict[str, str]]:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "prompt" in parsed:
                    return parsed
            except Exception:
                pass

            stripped = _strip_code_fences(content)
            if stripped != content:
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict) and "prompt" in parsed:
                        return parsed
                except Exception:
                    pass

            try:
                import re
                m = re.search(r"\{[\s\S]*?\}", content)
                start = 0
                while m:
                    candidate = m.group(0)
                    try:
                        obj = json.loads(candidate)
                        if isinstance(obj, dict) and "prompt" in obj:
                            return obj
                    except Exception:
                        pass
                    start += m.end()
                    m = re.search(r"\{[\s\S]*?\}", content[start:])
            except Exception:
                pass
            return None

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        for attempt in range(retry_count):
            try:
                self.stats["api_calls"] += 1
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=90,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    # учёт токенов, если есть
                    if "usage" in data:
                        self.stats["total_tokens_used"] += data["usage"].get("total_tokens", 0)

                    # Попытка распарсить JSON (устойчиво к markdown-код-блокам)
                    parsed = _try_parse_json_from(content)
                    if parsed is not None:
                        parsed.setdefault(
                            "negative_prompt",
                            "text, watermark, logo, low quality, blurry, distorted, extra limbs, deformed, cropped, frame",
                        )
                        parsed.setdefault("title", "Illustration")
                        if isinstance(parsed.get("prompt"), str):
                            parsed["prompt"] = _strip_code_fences(parsed["prompt"]).strip()
                        if isinstance(parsed.get("negative_prompt"), str):
                            parsed["negative_prompt"] = _strip_code_fences(parsed["negative_prompt"]).strip()
                        if isinstance(parsed.get("title"), str):
                            parsed["title"] = _strip_code_fences(parsed["title"]).strip() or "Illustration"
                        return parsed

                    # fallback: используем как prompt, очищая ограждения
                    clean_prompt = _strip_code_fences(content)
                    return {
                        "prompt": clean_prompt,
                        "negative_prompt": "text, watermark, logo, low quality, blurry, distorted, extra limbs, deformed, cropped, frame",
                        "title": "Illustration",
                    }
                else:
                    if resp.status_code == 429:
                        wait_s = 2 ** (attempt + 1)
                        time.sleep(wait_s)
                    elif attempt < retry_count - 1:
                        time.sleep(2 ** attempt)
            except Exception:
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        return None

    # ---------- Публичные методы ----------
    def generate_illustrations(self, input_file: str, output_file: str,
                                parts: int = 8, style: Optional[str] = None,
                                model_choice: str = "default",
                                book_title: Optional[str] = None,
                                book_author: Optional[str] = None) -> bool:
        """Читает файл, делит на части и генерирует JSON с промптами иллюстраций."""
        start = time.time()
        try:
            # модель
            if model_choice == "budget":
                self.model = self.budget_model
            elif model_choice == "quality":
                self.model = self.quality_model

            # входной текст
            if not Path(input_file).exists():
                print(f"❌ Файл не найден: {input_file}")
                return False

            with open(input_file, "r", encoding="utf-8") as f:
                text = f.read()

            self.stats["parts_requested"] = parts

            # делим на части
            text_parts = self._split_into_n_parts(text, parts)
            total = len(text_parts)
            if total == 0:
                print("❌ Пустой входной текст")
                return False

            print(f"🔪 Текст разбит на {total} частей (запрошено: {parts})")

            illustrations: List[Dict] = []
            for i, part in enumerate(text_parts, start=1):
                print(f"🔄 Генерация описания для части {i}/{total} ({len(part)} символов)...")
                prompt_str = self._build_llm_prompt(part, i, total, style, book_title, book_author)
                result = self._call_llm(prompt_str)
                if not result:
                    print(f"❌ Не удалось получить ответ для части {i}")
                    continue

                illustrations.append({
                    "index": i,
                    "title": result.get("title", f"Part {i}"),
                    "prompt": result.get("prompt", "").strip(),
                    "negative_prompt": result.get("negative_prompt", "").strip(),
                    "source_excerpt": part[:300].strip(),
                })

            # метаданные и сохранение
            data = {
                "metadata": {
                    "source_file": str(input_file),
                    "generated_at": datetime.now().isoformat(),
                    "model": self.model,
                    "style": style,
                    "requested_parts": parts,
                    "created_parts": len(illustrations),
                    "book": {"title": book_title, "author": book_author},
                    "api_calls": self.stats["api_calls"],
                    "tokens_used": self.stats["total_tokens_used"],
                },
                "illustrations": illustrations,
            }

            out_path = Path(output_file)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.stats["parts_created"] = len(illustrations)
            self.stats["processing_time"] = time.time() - start

            print(f"✅ Описания иллюстраций сохранены: {out_path}")
            print(f"📊 Частей создано: {self.stats['parts_created']}, API вызовов: {self.stats['api_calls']}")
            return True
        except Exception as e:
            print(f"❌ Ошибка генерации иллюстраций: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Генерация промптов иллюстраций из текстового файла",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python illustration_prompt_processor.py input.txt -o illustrations.json --parts 8 --style realistic
  python illustration_prompt_processor.py input.txt -o illustrations.json --parts 12 --model budget
        """,
    )
    parser.add_argument("input_file", help="Входной текстовый файл (clean или summary)")
    parser.add_argument("-o", "--output", required=True, help="Выходной JSON файл")
    parser.add_argument("--config", help="Файл конфигурации .env")
    parser.add_argument("--parts", type=int, default=8, help="Количество частей для разбиения")
    parser.add_argument("--style", help="Желаемый визуальный стиль (для подсказки LLM)")
    parser.add_argument(
        "--model",
        choices=["default", "budget", "quality"],
        default="default",
        help="Выбор пресета модели",
    )
    parser.add_argument("--title", help="Название книги (опционально)")
    parser.add_argument("--author", help="Автор книги (опционально)")

    args = parser.parse_args()

    try:
        proc = IllustrationPromptProcessor(args.config)
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("Создайте файл .env или config.env с вашим API ключом")
        return 1

    ok = proc.generate_illustrations(
        input_file=args.input_file,
        output_file=args.output,
        parts=args.parts,
        style=args.style,
        model_choice=args.model,
        book_title=args.title,
        book_author=args.author,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


