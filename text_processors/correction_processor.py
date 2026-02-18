#!/usr/bin/env python3
"""
Интерактивный корректор текста.

Функции:
- Разбивает выбранный текст на части и отправляет в LLM запрос на поиск коррекций
- Возвращает структурированный список правок в формате JSON (что заменить на что, с комментарием)
- Проходит по правкам в терминале: применить, пропустить или отредактировать вручную
- Особый акцент на замену вставленных иностранных слов на русский эквивалент, если есть уместный аналог

Пример:
  python text_processors/correction_processor.py input.txt -o corrected.txt
  python text_processors/correction_processor.py input.txt -o corrected.txt --config config.env --model budget
"""

import os
import sys
import json
import time
import argparse
import requests
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
import re


@dataclass
class Correction:
    """Единичная правка, предложенная моделью."""
    original: str
    replacement: str
    reason: str
    start: Optional[int] = None  # Позиция в чанке (относительная)
    end: Optional[int] = None
    chunk_index: Optional[int] = None  # Для отладки


class InteractiveCorrector:
    def __init__(self, config_file: Optional[str] = None):
        self.load_config(config_file)
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден. Установите OPENROUTER_API_KEY или используйте --config")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/bookreader",
            "X-Title": "Interactive Correction Processor"
        }

    def load_config(self, config_file: Optional[str]):
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            for env_file in ['.env', 'config.env', 'settings.env']:
                if Path(env_file).exists():
                    load_dotenv(env_file)
                    break

        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('DEFAULT_MODEL', 'anthropic/claude-3.5-sonnet')
        self.chunk_size = int(os.getenv('DEFAULT_CHUNK_SIZE', '3000'))
        self.temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.2'))
        self.max_tokens = int(os.getenv('DEFAULT_MAX_TOKENS', '3000'))

        # Альтернативные модели
        self.budget_model = os.getenv('BUDGET_MODEL', 'meta-llama/llama-3.1-8b-instruct')
        self.quality_model = os.getenv('QUALITY_MODEL', 'openai/gpt-4o')

    def split_text(self, text: str) -> List[str]:
        # Разбить по абзацам и собрать чанки до лимита
        paragraphs = [p for p in text.split('\n\n')]
        chunks: List[str] = []
        current = ''
        for p in paragraphs:
            if len(current) + len(p) + 2 > self.chunk_size and current:
                chunks.append(current)
                current = p
            else:
                current = (current + ('\n\n' if current else '') + p) if p else current
        if current:
            chunks.append(current)
        return chunks

    def build_prompt(self, chunk: str, idx: int, total: int) -> str:
        return (
            "Ты — опытный русскоязычный корректор. Задача — найти ТОЛЬКО реальные ошибки.\n"
            "Требования к правкам:\n"
            "- Исправляй орфографию, пунктуацию, грамматику.\n"
            "- Сохраняй смысл автора, не меняй стиль без необходимости.\n"
            "- Обязательно выявляй вставленные иностранные слова; если есть естественный русский аналог в этом контексте — предложи замену.\n"
            "- НЕ предлагай правки заголовков, меток и нумераторов разделов, например строк вида '## Фрагмент N', строк начинающихся с '#', а также корректных заглавий.\n"
            "- НЕ предлагай правок, если замена идентична исходному фрагменту.\n"
            "- Каждая правка должна соответствовать точной подстроке исходного текста.\n"
            "- Предлагай минимально достаточную замену, без переписывания предложений.\n\n"
            "Формат ответа — строго JSON со схемой:\n"
            "{ 'corrections': [\n"
            "    { 'original': 'ровно как в тексте', 'replacement': 'новый текст',\n"
            "      'reason': 'кратко', 'start': число_или_null, 'end': число_или_null,\n"
            "      'type': 'spelling|punctuation|grammar|foreign_word|typo|other', 'confidence': 0.0..1.0 }\n"
            "] }\n\n"
            f"Часть {idx} из {total}. Текст для анализа ниже между <TEXT>:</TEXT>\n"
            "<TEXT>\n" + chunk + "\n</TEXT>\n"
            "Верни ТОЛЬКО корректный JSON без пояснений. Если правок нет, верни {\"corrections\": []}."
        )

    def request_corrections(self, chunk: str, idx: int, total: int, model: Optional[str]) -> List[Correction]:
        prompt = self.build_prompt(chunk, idx, total)
        payload = {
            "model": model or self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        for attempt in range(3):
            try:
                resp = requests.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=90)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data['choices'][0]['message']['content'].strip()
                    # Попробуем распарсить JSON (возможно, окружен код-блоками)
                    content = self._strip_code_fences(content)
                    obj = json.loads(content)
                    result: List[Correction] = []
                    for c in obj.get('corrections', []):
                        original = c.get('original', '') or ''
                        replacement = c.get('replacement', '') or ''
                        # локальная фильтрация на уровне модели: отбрасываем идентичные
                        if self._is_effectively_identical(original, replacement):
                            continue
                        # отбрасываем заголовки вида '## Фрагмент N'
                        if self._looks_like_fragment_header(original):
                            continue
                        # фильтр по уверенности, если есть
                        conf = c.get('confidence')
                        if isinstance(conf, (int, float)) and conf < 0.7:
                            continue
                        result.append(Correction(
                            original=original,
                            replacement=replacement,
                            reason=c.get('reason', ''),
                            start=c.get('start'),
                            end=c.get('end'),
                            chunk_index=idx-1
                        ))
                    return result
                if resp.status_code == 429:
                    time.sleep(2 ** (attempt + 1))
                else:
                    time.sleep(1.0)
            except Exception:
                time.sleep(1.0)
        return []

    def _strip_code_fences(self, s: str) -> str:
        if s.startswith("```") and s.endswith("```"):
            # Удалим первую строку и последнюю
            lines = s.splitlines()
            if len(lines) >= 2:
                inner = "\n".join(lines[1:-1])
                return inner
        return s

    def _is_effectively_identical(self, a: str, b: str) -> bool:
        def norm(x: str) -> str:
            x = re.sub(r"\s+", " ", x or "").strip()
            return x
        return norm(a) == norm(b)

    def _looks_like_fragment_header(self, s: str) -> bool:
        s = (s or '').strip()
        if re.match(r"^#+\\s", s):
            return True
        if re.match(r"^##\\s*Фрагмент\\s*\d+", s, flags=re.IGNORECASE):
            return True
        return False

    def _find_in_window(self, text: str, needle: str, expected_pos: int, window: int = 300) -> Optional[int]:
        if not needle:
            return None
        start = max(0, expected_pos - window)
        end = min(len(text), expected_pos + window)
        segment = text[start:end]
        rel = segment.find(needle)
        if rel == -1:
            # fallback: try normalized spaces
            compact = re.sub(r"\s+", " ", segment)
            rel2 = compact.find(re.sub(r"\s+", " ", needle))
            if rel2 == -1:
                return None
            # Cannot easily remap to original indices; fall back to global search
            pos = text.find(needle)
            return pos if pos != -1 else None
        return start + rel

    def _preview_context(self, text: str, start: int, end: int, max_ctx: int = 120) -> str:
        left = max(0, start - max_ctx)
        right = min(len(text), end + max_ctx)
        before = text[left:start]
        target = text[start:end]
        after = text[end:right]
        return before + "<<" + target + ">>" + after

    def _prompt_user(self, corr: Correction, context: str) -> Tuple[str, Optional[str]]:
        print()
        print("-"*80)
        print("Причина:", corr.reason or "(не указано)")
        print("Контекст:")
        print(context)
        print()
        print(f"Заменить: '{corr.original}' → '{corr.replacement}'")
        choice = input("[a] применить  [s] пропустить  [e] отредактировать → ").strip().lower() or 'a'
        if choice == 'e':
            manual = input("Введите свой вариант замены (пусто чтобы оставить как есть): ")
            return 'e', manual
        if choice not in ('a','s'):
            return 's', None
        return choice, None

    def run(self, input_path: Path, output_path: Path, model_choice: Optional[str] = None, dry_run: bool = False) -> bool:
        try:
            text = input_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ Не удалось прочитать файл: {e}")
            return False

        chunks = self.split_text(text)
        print(f"📄 Загружен текст: {len(text):,} символов, частей: {len(chunks)}")

        # Карта смещений чанков в общем тексте
        chunk_offsets: List[int] = []
        offset = 0
        for ch in chunks:
            pos = text.find(ch, offset)
            if pos == -1:
                pos = offset
            chunk_offsets.append(pos)
            offset = pos + len(ch)

        all_corrections: List[Tuple[int, Correction]] = []  # (global_pos_hint, correction)
        for i, ch in enumerate(chunks, start=1):
            print(f"🔎 Анализ части {i}/{len(chunks)}...")
            corrs = self.request_corrections(ch, i, len(chunks), model_choice)
            base = chunk_offsets[i-1]
            for c in corrs:
                hint = base + (c.start or 0)
                all_corrections.append((hint, c))
            # небольшая пауза между запросами
            if i < len(chunks):
                time.sleep(1.2)

        # Сортируем по предполагаемой позиции для стабильности
        all_corrections.sort(key=lambda x: x[0])

        print(f"\nНайдено правок: {len(all_corrections)}")
        current_text = text
        applied = 0
        skipped = 0

        for hint_pos, corr in all_corrections:
            # Защита на этапе применения: идентичные правки и заголовки пропускаем
            if self._is_effectively_identical(corr.original, corr.replacement):
                skipped += 1
                continue
            if self._looks_like_fragment_header(corr.original):
                skipped += 1
                continue
            # Находим фактическую позицию по окну вокруг подсказки
            pos = self._find_in_window(current_text, corr.original, hint_pos)
            if pos is None:
                # fallback: глобальный поиск
                pos = current_text.find(corr.original)
                if pos == -1:
                    skipped += 1
                    continue
            end = pos + len(corr.original)
            ctx = self._preview_context(current_text, pos, end)

            action, manual = self._prompt_user(corr, ctx)
            if action == 's':
                skipped += 1
                continue
            replacement = corr.replacement if action == 'a' else (manual if manual is not None else corr.replacement)
            if replacement == "":
                # Удаление
                new_text = current_text[:pos] + current_text[end:]
            else:
                new_text = current_text[:pos] + replacement + current_text[end:]

            if not dry_run:
                current_text = new_text
            applied += 1

        print()
        print(f"✅ Применено: {applied}, пропущено: {skipped}")

        if not dry_run:
            try:
                output_path.write_text(current_text, encoding='utf-8')
                print(f"📦 Сохранено: {output_path}")
            except Exception as e:
                print(f"❌ Ошибка записи файла: {e}")
                return False

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Интерактивная корректура текста с помощью LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python text_processors/correction_processor.py input.txt -o corrected.txt
  python text_processors/correction_processor.py input.txt -o corrected.txt --config config.env --model budget
        """
    )

    parser.add_argument('input_file', help='Входной текстовый файл для корректуры')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл с исправлениями')
    parser.add_argument('--config', help='Путь к .env файлу с ключом и настройками')
    parser.add_argument('--model', choices=['default', 'budget', 'quality'], default='default', help='Выбор преднастроенной модели')
    parser.add_argument('--dry-run', action='store_true', help='Не сохранять файл, только интерактивный просмотр')
    parser.add_argument('--export-html', action='store_true', help='После сохранения также сгенерировать HTML из исправленного текста')
    parser.add_argument('--html-title', help='Заголовок HTML страницы при экспорте')

    args = parser.parse_args()

    try:
        corrector = InteractiveCorrector(args.config)
        model_choice = None
        if args.model == 'budget':
            model_choice = corrector.budget_model
        elif args.model == 'quality':
            model_choice = corrector.quality_model
        else:
            model_choice = corrector.model

        in_path = Path(args.input_file)
        if not in_path.exists():
            print(f"❌ Файл не найден: {in_path}")
            return 1

        out_path = Path(args.output)
        ok = corrector.run(in_path, out_path, model_choice=model_choice, dry_run=args.dry_run)
        if not ok:
            return 1
        if ok and (args.export_html and not args.dry_run):
            try:
                # Ленивая загрузка конвертера
                from text_processors.markdown_to_html import markdown_to_html
                html_doc = markdown_to_html(out_path.read_text(encoding='utf-8'), title=args.html_title or out_path.stem)
                html_path = out_path.with_suffix('.html')
                html_path.write_text(html_doc, encoding='utf-8')
                print(f"🌐 HTML экспортирован: {html_path}")
            except Exception as e:
                print(f"⚠️ Не удалось создать HTML: {e}")
        return 0
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⛔ Прервано пользователем")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


