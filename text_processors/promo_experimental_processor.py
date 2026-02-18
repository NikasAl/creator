#!/usr/bin/env python3
"""
Экспериментальный процессор для создания промо-описания и статей для видео на основе текстов пайплайна

Функции:
- Сканирует каталог пайплайна и собирает .txt файлы
- Формирует контекст и отправляет запрос в LLM через OpenRouter
- Генерирует контент с помощью экспериментальных промптов без параметров
"""

import os
import sys
import argparse
import time
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv


class PromoExperimentalProcessor:
    def __init__(self, config_file: str = None):
        """Инициализация экспериментального процессора с загрузкой конфигурации"""
        self.load_config(config_file)
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/promo-experimental-processor",
            "X-Title": "Promo Experimental Processor"
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

    def create_prompt(self, context: str, experiment_type: str) -> str:
        """Создает экспериментальный промпт без параметров, в зависимости от типа эксперимента"""
        if experiment_type == "creative":
            return f"""
Вот контекст из образовательного видео/урока:

{context}

Теперь создай креативное промо-описание для этого контента. Не используй шаблоны и параметры, просто напиши увлекательный текст, который заинтересует аудиторию. Сделай это в творческом, нетривиальном стиле.
"""
        elif experiment_type == "song_pikabu":
            return f"""
На основе текста песни:

{context}

Напиши краткое, искреннее промо-описание для Pikabu на основе моего видео. В нем песня созданная по моему видео-уроку.

Стиль: лаконичный, без пафоса, без клише вроде «вы в шоке!», «никто не ожидал!».
Тональность: спокойная, немного рефлексивная, с долей самоиронии, но без излишней скромности.

Обязательно включи:
— что за задача или тема (конкретно: например, «рациональное уравнение с корнем в знаменателе и многочленом 4-й степени в числителе»),
— какой формат использован (анимация, разбор, песня и т.д.),
— в чём была трудность (не техническая, а мыслительная: хаос, ложный след, страх ошибиться и т.п.),
— что помогло выйти из тупика (даже если это просто «вернуться к методу»).

Не рекламируй напрямую. Лучше расскажи, как будто другу, зачем ты этим занялся и что в этом оказалось неожиданно полезным или красивым.

Для Pikabu — до 1500 символов, можно включить текст стихов ниже как цитату.

"""
        elif experiment_type == "poetry_promo":
            return f"""
Ты — опытный маркетолог и редактор видеоописаний. На основе предоставленного контекста создай сильное, цепляющее промо-описание для видео.

Вот стихи песни по которой создано видео:

{context}
---

ТРЕБОВАНИЯ:
- Структура:
  1) Короткий hook (1–2 предложения) — раскрывает интригу/ценность
  2) Основные преимущества/темы выпуска — 3–6 строк кратко и по делу
  3) Призыв к действию: подписка/лайк/комментарий
  4) Хэштеги в строку, разделенные через пробел и начинающиеся с # (5–10, уместные и несложные)
- Не используй маркдаун. Пиши естественно.
- Избегай клише и воды. Максимум конкретики.
"""
        elif experiment_type == "storytelling":
            return f"""
Вот материалы урока/видео:

{context}

Преврати это в увлекательную историю. Расскажи так, как будто это личный опыт или интересная история. Не используй формальные параметры, просто создай захватывающий повествовательный текст.
"""
        elif experiment_type == "conversational":
            return f"""
Контекст:

{context}

Напиши промо-описание в разговорном стиле, как если бы ты объяснял это другу. Без формальных параметров, просто естественно и дружелюбно.
"""
        elif experiment_type == "technical":
            return f"""
Материалы:

{context}

Создай технически точное промо-описание. Сосредоточься на сути и ключевых моментах. Без параметров, но с акцентом на техническую точность.
"""
        else:  # default
            return f"""
Контекст:

{context}

Создай промо-описание для этого контента. Просто естественный, увлекательный текст.
"""

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
                          experiment_type: str, model_choice: str = "default",
                          source_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
        """Основной метод: собирает контекст и генерирует описание с экспериментальным промптом"""
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

        prompt = self.create_prompt(context, experiment_type)

        # === РЕЖИМ CUSTOM ===
        if model_choice == "custom":
            print("\n" + "="*60)
            print("🎨 ЭКСПЕРИМЕНТАЛЬНЫЙ ПРОМО-ГЕНЕРАТОР")
            print("="*60)
            print(prompt)
            print("-" * 60)

            if not output_file:
                output_path = pdir / f"promo_exp_{experiment_type}.txt"
            else:
                output_path = Path(output_file)

            # Создаем файл, если его нет
            if not output_path.exists():
                output_path.touch()

            print(f"1. Скопируйте промпт в LLM.")
            print(f"2. Сохраните результат в: {output_path}")

            try:
                subprocess.run(["subl", "-w", output_path], check=True)
                print(f"✅ Промо-описание сохранено: {output_path}")
            except FileNotFoundError:
                input("Нажмите Enter, когда сохраните файл...")
            return True, output_path

        description = self.generate_description(prompt, model_choice)
        if not description:
            print("❌ Ошибка генерации контента")
            return False, None

        if not output_file:
            output_path = pdir / f"promo_exp_{experiment_type}.txt"
        else:
            output_path = Path(output_file)

        output_path.write_text(description, encoding="utf-8")
        print(f"✅ Результат экспериментального промта '{experiment_type}' сохранен: {output_path}")
        return True, output_path


def main():
    parser = argparse.ArgumentParser(
        description="Экспериментальный процессор промо-описаний для видео на основе текстов пайплайна",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("pipeline_dir", help="Каталог пайплайна с .txt файлами")
    parser.add_argument("-o", "--output", help="Путь к выходному файлу")
    parser.add_argument("--config", help="Путь к .env файлу с конфигурацией")
    parser.add_argument("--prefix", help="Фильтр префикса для выбора .txt файлов")
    parser.add_argument("--model", choices=["default", "budget", "quality", "custom"], default="default", help="Выбор модели")
    parser.add_argument("--experiment-type", choices=["creative", "poetry_promo", "song_pikabu", "storytelling", "conversational", "technical"],
                       default="creative", help="Тип экспериментального промта")
    parser.add_argument("--source-file", help="Путь к конкретному исходному файлу (например, script.txt)")

    args = parser.parse_args()

    try:
        processor = PromoExperimentalProcessor(args.config)
        ok, out = processor.process_pipeline(
            pipeline_dir=args.pipeline_dir,
            output_file=args.output,
            prefix=args.prefix,
            experiment_type=args.experiment_type,
            model_choice=args.model,
            source_file=args.source_file
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