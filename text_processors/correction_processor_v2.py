#!/usr/bin/env python3
"""
Интерактивный корректор текста (рефакторенная версия).

Наследует от BaseProcessor для использования:
- Унифицированной загрузки конфигурации
- Готового API клиента
- Методов разбиения текста

Пример:
  python text_processors/correction_processor_v2.py input.txt -o corrected.txt
  python text_processors/correction_processor_v2.py input.txt -o corrected.txt --config config.env --model-preset budget
"""

import json
import time
import re
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from utils.base_processor import BaseProcessor, ProcessingReport, create_arg_parser


@dataclass
class Correction:
    """Единичная правка, предложенная моделью."""
    original: str
    replacement: str
    reason: str
    start: Optional[int] = None
    end: Optional[int] = None
    chunk_index: Optional[int] = None


class InteractiveCorrector(BaseProcessor):
    """
    Интерактивный корректор текста с использованием LLM.
    
    Функции:
    - Разбивает текст на части и отправляет в LLM запрос на поиск коррекций
    - Возвращает структурированный список правок в формате JSON
    - Проходит по правкам в терминале: применить, пропустить или отредактировать
    - Особый акцент на замену иностранных слов на русский эквивалент
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        model: Optional[str] = None,
        model_preset: str = 'default',
        chunk_size: int = 3000
    ):
        """
        Инициализация корректора.
        
        Args:
            config_file: Путь к файлу конфигурации
            model: Модель для использования
            model_preset: Пресет модели ('default', 'budget', 'quality')
            chunk_size: Размер чанка для разбиения текста
        """
        super().__init__(
            config_file=config_file,
            model=model,
            model_preset=model_preset,
            chunk_size=chunk_size
        )
        
        # Низкая температура для консистентности коррекций
        self.temperature = 0.2
    
    def process(self, text: str) -> str:
        """
        Обрабатывает текст и возвращает исправленную версию.
        
        Для интерактивной коррекции используйте run_interactive().
        
        Args:
            text: Исходный текст
            
        Returns:
            Исправленный текст
        """
        corrections = self._get_all_corrections(text)
        result_text = text
        
        # Автоматическое применение всех коррекций
        for hint_pos, corr in corrections:
            if self._is_effectively_identical(corr.original, corr.replacement):
                continue
            if self._looks_like_fragment_header(corr.original):
                continue
                
            pos = result_text.find(corr.original)
            if pos != -1:
                result_text = result_text[:pos] + corr.replacement + result_text[pos + len(corr.original):]
        
        return result_text
    
    def run_interactive(
        self,
        input_path: Path,
        output_path: Path,
        dry_run: bool = False
    ) -> bool:
        """
        Запускает интерактивную коррекцию текста.
        
        Args:
            input_path: Путь к входному файлу
            output_path: Путь к выходному файлу
            dry_run: Только просмотр, без сохранения
            
        Returns:
            True если успешно
        """
        try:
            text = input_path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.error(f"Не удалось прочитать файл: {e}")
            return False
        
        self._report.start_time = self._report.start_time or self._report.start_time
        
        # Разбиваем на чанки
        chunks = self.split_text(text, preset='llm_processing')
        self.logger.info(f"📄 Загружен текст: {len(text):,} символов, частей: {len(chunks)}")
        
        # Карта смещений чанков в общем тексте
        chunk_offsets = self._calculate_chunk_offsets(text, chunks)
        
        # Получаем все коррекции
        all_corrections = self._collect_corrections(chunks, chunk_offsets)
        
        # Сортируем по позиции
        all_corrections.sort(key=lambda x: x[0])
        
        self.logger.info(f"\nНайдено правок: {len(all_corrections)}")
        
        # Интерактивное применение
        current_text = text
        applied = 0
        skipped = 0
        
        for hint_pos, corr in all_corrections:
            # Фильтрация
            if self._is_effectively_identical(corr.original, corr.replacement):
                skipped += 1
                continue
            if self._looks_like_fragment_header(corr.original):
                skipped += 1
                continue
            
            # Поиск позиции
            pos = self._find_in_window(current_text, corr.original, hint_pos)
            if pos is None:
                pos = current_text.find(corr.original)
                if pos == -1:
                    skipped += 1
                    continue
            
            end = pos + len(corr.original)
            ctx = self._preview_context(current_text, pos, end)
            
            # Интерактивный выбор
            action, manual = self._prompt_user(corr, ctx)
            
            if action == 's':
                skipped += 1
                continue
            
            replacement = corr.replacement if action == 'a' else (manual if manual is not None else corr.replacement)
            
            if replacement == "":
                new_text = current_text[:pos] + current_text[end:]
            else:
                new_text = current_text[:pos] + replacement + current_text[end:]
            
            if not dry_run:
                current_text = new_text
            applied += 1
        
        self.logger.info(f"\n✅ Применено: {applied}, пропущено: {skipped}")
        
        if not dry_run:
            try:
                output_path.write_text(current_text, encoding='utf-8')
                self.logger.info(f"📦 Сохранено: {output_path}")
            except Exception as e:
                self.logger.error(f"Ошибка записи файла: {e}")
                return False
        
        return True
    
    def _calculate_chunk_offsets(self, text: str, chunks: List[str]) -> List[int]:
        """Вычисляет смещения чанков в общем тексте."""
        chunk_offsets = []
        offset = 0
        for ch in chunks:
            pos = text.find(ch, offset)
            if pos == -1:
                pos = offset
            chunk_offsets.append(pos)
            offset = pos + len(ch)
        return chunk_offsets
    
    def _collect_corrections(
        self,
        chunks: List[str],
        chunk_offsets: List[int]
    ) -> List[Tuple[int, Correction]]:
        """Собирает коррекции из всех чанков."""
        all_corrections = []
        
        for i, ch in enumerate(chunks, start=1):
            self.logger.info(f"🔎 Анализ части {i}/{len(chunks)}...")
            corrs = self._request_corrections(ch, i, len(chunks))
            base = chunk_offsets[i - 1]
            
            for c in corrs:
                hint = base + (c.start or 0)
                all_corrections.append((hint, c))
            
            self._report.chunks_processed += 1
            
            if i < len(chunks):
                time.sleep(0.5)
        
        return all_corrections
    
    def _request_corrections(
        self,
        chunk: str,
        idx: int,
        total: int
    ) -> List[Correction]:
        """Запрашивает коррекции у LLM для чанка."""
        prompt = self._build_correction_prompt(chunk, idx, total)
        
        try:
            response = self.call_api(prompt, max_tokens=3000)
            return self._parse_corrections(response, idx - 1)
        except Exception as e:
            self.logger.error(f"Ошибка запроса коррекций: {e}")
            return []
    
    def _build_correction_prompt(self, chunk: str, idx: int, total: int) -> str:
        """Строит промпт для коррекции."""
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
    
    def _parse_corrections(self, response: str, chunk_index: int) -> List[Correction]:
        """Парсит ответ LLM в список коррекций."""
        content = self._strip_code_fences(response)
        
        try:
            obj = json.loads(content)
        except json.JSONDecodeError:
            self.logger.warning("Не удалось распарсить JSON ответа")
            return []
        
        result = []
        for c in obj.get('corrections', []):
            original = c.get('original', '') or ''
            replacement = c.get('replacement', '') or ''
            
            # Фильтрация
            if self._is_effectively_identical(original, replacement):
                continue
            if self._looks_like_fragment_header(original):
                continue
            
            conf = c.get('confidence')
            if isinstance(conf, (int, float)) and conf < 0.7:
                continue
            
            result.append(Correction(
                original=original,
                replacement=replacement,
                reason=c.get('reason', ''),
                start=c.get('start'),
                end=c.get('end'),
                chunk_index=chunk_index
            ))
        
        return result
    
    def _strip_code_fences(self, s: str) -> str:
        """Удаляет code fences из ответа."""
        if s.startswith("```") and s.endswith("```"):
            lines = s.splitlines()
            if len(lines) >= 2:
                return "\n".join(lines[1:-1])
        return s
    
    def _is_effectively_identical(self, a: str, b: str) -> bool:
        """Проверяет идентичность строк с нормализацией."""
        def norm(x: str) -> str:
            return re.sub(r"\s+", " ", x or "").strip()
        return norm(a) == norm(b)
    
    def _looks_like_fragment_header(self, s: str) -> bool:
        """Проверяет, похожа ли строка на заголовок фрагмента."""
        s = (s or '').strip()
        if re.match(r"^#+\s", s):
            return True
        if re.match(r"^##\s*Фрагмент\s*\d+", s, flags=re.IGNORECASE):
            return True
        return False
    
    def _find_in_window(
        self,
        text: str,
        needle: str,
        expected_pos: int,
        window: int = 300
    ) -> Optional[int]:
        """Ищет подстроку в окне вокруг ожидаемой позиции."""
        if not needle:
            return None
        
        start = max(0, expected_pos - window)
        end = min(len(text), expected_pos + window)
        segment = text[start:end]
        rel = segment.find(needle)
        
        if rel == -1:
            compact = re.sub(r"\s+", " ", segment)
            rel2 = compact.find(re.sub(r"\s+", " ", needle))
            if rel2 == -1:
                return None
            pos = text.find(needle)
            return pos if pos != -1 else None
        
        return start + rel
    
    def _preview_context(
        self,
        text: str,
        start: int,
        end: int,
        max_ctx: int = 120
    ) -> str:
        """Создает превью контекста для правки."""
        left = max(0, start - max_ctx)
        right = min(len(text), end + max_ctx)
        before = text[left:start]
        target = text[start:end]
        after = text[end:right]
        return before + "<<" + target + ">>" + after
    
    def _prompt_user(
        self,
        corr: Correction,
        context: str
    ) -> Tuple[str, Optional[str]]:
        """Запрашивает действие у пользователя."""
        print()
        print("-" * 80)
        print("Причина:", corr.reason or "(не указано)")
        print("Контекст:")
        print(context)
        print()
        print(f"Заменить: '{corr.original}' → '{corr.replacement}'")
        choice = input("[a] применить  [s] пропустить  [e] отредактировать → ").strip().lower() or 'a'
        
        if choice == 'e':
            manual = input("Введите свой вариант замены (пусто чтобы оставить как есть): ")
            return 'e', manual
        if choice not in ('a', 's'):
            return 's', None
        return choice, None


def main():
    parser = argparse.ArgumentParser(
        description="Интерактивная корректура текста с помощью LLM (рефакторенная версия)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python text_processors/correction_processor_v2.py input.txt -o corrected.txt
  python text_processors/correction_processor_v2.py input.txt -o corrected.txt --config config.env --model-preset budget
        """
    )
    
    parser.add_argument('input_file', help='Входной текстовый файл для корректуры')
    parser.add_argument('-o', '--output', required=True, help='Выходной файл с исправлениями')
    parser.add_argument('--config', help='Путь к .env файлу с ключом и настройками')
    parser.add_argument('--model-preset', choices=['default', 'budget', 'quality'],
                       default='default', help='Выбор преднастроенной модели')
    parser.add_argument('--chunk-size', type=int, default=3000, help='Размер чанка')
    parser.add_argument('--dry-run', action='store_true', help='Не сохранять файл, только интерактивный просмотр')
    parser.add_argument('--export-html', action='store_true', help='Сгенерировать HTML из исправленного текста')
    parser.add_argument('--html-title', help='Заголовок HTML страницы')
    
    args = parser.parse_args()
    
    try:
        corrector = InteractiveCorrector(
            config_file=args.config,
            model_preset=args.model_preset,
            chunk_size=args.chunk_size
        )
        
        in_path = Path(args.input_file)
        if not in_path.exists():
            print(f"❌ Файл не найден: {in_path}")
            return 1
        
        out_path = Path(args.output)
        ok = corrector.run_interactive(in_path, out_path, dry_run=args.dry_run)
        
        if not ok:
            return 1
        
        if ok and args.export_html and not args.dry_run:
            try:
                from text_processors.markdown_to_html import markdown_to_html
                html_doc = markdown_to_html(
                    out_path.read_text(encoding='utf-8'),
                    title=args.html_title or out_path.stem
                )
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
    exit(main())
