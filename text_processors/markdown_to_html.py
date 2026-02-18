#!/usr/bin/env python3
"""
Простой конвертер Markdown -> HTML без внешних зависимостей.
Поддержка: заголовки #/##/###, жирный **text**, параграфы, базовые переносы.

Примеры:
  python text_processors/markdown_to_html.py input.md -o output.html --title "Заголовок"
  python text_processors/markdown_to_html.py input.txt
"""

import argparse
import html
from pathlib import Path
import re
from typing import List


CSS = """
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.6; color: #222; max-width: 760px; margin: 32px auto; padding: 0 16px; }
h1, h2, h3 { line-height: 1.25; margin: 1.2em 0 0.6em; }
h1 { font-size: 2rem; }
h2 { font-size: 1.5rem; }
h3 { font-size: 1.25rem; }
p { margin: 0.8em 0; white-space: normal; }
strong { font-weight: 700; }
hr { border: 0; border-top: 1px solid #ddd; margin: 24px 0; }
pre { background: #f6f8fa; padding: 12px; overflow: auto; border-radius: 6px; border: 1px solid #e1e4e8; }
code { background: #f6f8fa; padding: 2px 4px; border-radius: 3px; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; }
pre code { background: transparent; padding: 0; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }
blockquote { border-left: 3px solid #ddd; margin: 16px 0; padding: 8px 16px; color: #555; background: #fafafa; }
""".strip()


def apply_inline_markdown(text: str) -> str:
    # Экранируем HTML, затем применяем инлайновые замены
    text = html.escape(text)
    # Ссылки: [text](url) - обрабатываем до других замен
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # Жирный: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Курсив: *text* или _text_ (избегаем конфликта с **)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    # Подчистим двойные пробелы
    text = re.sub(r"\s{2,}", " ", text)
    return text


def lines_to_blocks(lines: List[str]) -> List[str]:
    blocks: List[str] = []
    buf: List[str] = []
    for line in lines:
        if line.strip() == "":
            if buf:
                blocks.append("\n".join(buf))
                buf = []
        else:
            buf.append(line.rstrip())
    if buf:
        blocks.append("\n".join(buf))
    return blocks


def markdown_to_html(md: str, title: str = "") -> str:
    lines = md.splitlines()

    html_parts: List[str] = []
    if title:
        html_parts.append(f"<h1>{html.escape(title)}</h1>")

    # Состояния парсера
    current_list = None  # 'ul' | 'ol'
    list_open = False
    para_lines: List[str] = []

    def flush_list():
        nonlocal list_open, current_list
        if list_open and current_list:
            html_parts.append(f"</{current_list}>")
        list_open = False
        current_list = None

    def flush_para():
        nonlocal para_lines
        if not para_lines:
            return
        # поддержка переносов по двум пробелам в конце строки
        if any(re.search(r"\s\s$", ln) for ln in para_lines):
            parts = [apply_inline_markdown(ln.rstrip()) for ln in para_lines]
            para = "<br />".join(parts)
        else:
            para = " ".join([apply_inline_markdown(s.strip()) for s in para_lines])
        html_parts.append(f"<p>{para}</p>")
        para_lines = []

    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.rstrip("\n")
        st = s.strip()

        # Пустая строка: разделитель абзацев / закрытие списков
        if st == "":
            # Не разрываем текущий нумерованный/маркированный список пустой строкой,
            # так как автор может вставлять пустые строки между пунктами
            if current_list:
                # пропускаем пустую строку внутри списка
                i += 1
                continue
            flush_para()
            flush_list()
            i += 1
            continue

        # Заголовки в любой позиции
        m = re.match(r"^####\s+(.*)$", st)
        if m:
            flush_para(); flush_list()
            html_parts.append(f"<h4>{apply_inline_markdown(m.group(1))}</h4>")
            i += 1
            continue
        m = re.match(r"^###\s+(.*)$", st)
        if m:
            flush_para(); flush_list()
            html_parts.append(f"<h3>{apply_inline_markdown(m.group(1))}</h3>")
            i += 1
            continue
        m = re.match(r"^##\s+(.*)$", st)
        if m:
            flush_para(); flush_list()
            html_parts.append(f"<h2>{apply_inline_markdown(m.group(1))}</h2>")
            i += 1
            continue
        m = re.match(r"^#\s+(.*)$", st)
        if m:
            flush_para(); flush_list()
            html_parts.append(f"<h1>{apply_inline_markdown(m.group(1))}</h1>")
            i += 1
            continue

        # Горизонтальная линия
        if re.match(r"^---+$", st):
            flush_para(); flush_list()
            html_parts.append("<hr />")
            i += 1
            continue

        # Блочные цитаты: строки начинающиеся с '>' собираем в один блок
        if re.match(r"^>\s?", st):
            flush_para(); flush_list()
            quote_lines: List[str] = []
            while i < len(lines):
                qst = lines[i].strip()
                if qst.startswith('>'):
                    # удаляем префикс '>' и один пробел если есть
                    content = re.sub(r"^>\s?", "", qst, count=1)
                    quote_lines.append(content)
                    i += 1
                    continue
                # пустая строка внутри цитаты — сохраняем как разделитель абзацев
                if qst == "":
                    quote_lines.append("")
                    i += 1
                    continue
                break
            # Превратим quote_lines в параграфы
            # Разбиваем по пустым строкам
            paragraphs: List[List[str]] = []
            buf: List[str] = []
            for ln in quote_lines:
                if ln == "":
                    if buf:
                        paragraphs.append(buf)
                        buf = []
                else:
                    buf.append(ln)
            if buf:
                paragraphs.append(buf)
            html_parts.append("<blockquote>")
            for plines in paragraphs:
                if any(re.search(r"\s\s$", ln) for ln in plines):
                    parts = [apply_inline_markdown(ln.rstrip()) for ln in plines]
                    para = "<br />".join(parts)
                else:
                    para = " ".join([apply_inline_markdown(s.strip()) for s in plines])
                html_parts.append(f"  <p>{para}</p>")
            html_parts.append("</blockquote>")
            continue

        # Блоки кода: ```language или ```
        if re.match(r"^```", st):
            flush_para(); flush_list()
            # Определяем язык программирования
            language_match = re.match(r"^```(\w+)?", st)
            language = language_match.group(1) if language_match and language_match.group(1) else ""
            
            code_lines: List[str] = []
            i += 1  # пропускаем строку с ```
            while i < len(lines):
                if lines[i].strip() == "```":
                    break
                code_lines.append(lines[i])
                i += 1
            
            # Создаем блок кода
            code_content = "\n".join(code_lines)
            if language:
                html_parts.append(f'<pre><code class="language-{language}">{html.escape(code_content)}</code></pre>')
            else:
                html_parts.append(f'<pre><code>{html.escape(code_content)}</code></pre>')
            i += 1  # пропускаем закрывающий ```
            continue

        # Элементы списка
        if re.match(r"^[\-*]\s+.+$", st):
            flush_para()
            if current_list != 'ul':
                flush_list()
                current_list = 'ul'
                html_parts.append("<ul>")
                list_open = True
            item_text = re.sub(r"^[\-*]\s+", "", st, count=1)
            html_parts.append(f"  <li>{apply_inline_markdown(item_text)}</li>")
            i += 1
            continue
        if re.match(r"^\d+\.\s+.+$", st):
            flush_para()
            if current_list != 'ol':
                flush_list()
                current_list = 'ol'
                html_parts.append("<ol>")
                list_open = True
            item_text = re.sub(r"^\d+\.\s+", "", st, count=1)
            html_parts.append(f"  <li>{apply_inline_markdown(item_text)}</li>")
            i += 1
            continue

        # Иначе — часть параграфа
        para_lines.append(s)
        i += 1

    # Конец документа: сброс состояний
    flush_para()
    flush_list()

    body_html = "\n  ".join(html_parts)
    doc = f"""<!DOCTYPE html>
<html lang=\"ru\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{html.escape(title or 'Документ')}</title>
  <style>{CSS}</style>
</head>
<body>
{body_html}
</body>
</html>
"""
    return doc


def main():
    parser = argparse.ArgumentParser(description="Генерация HTML из простого Markdown без зависимостей")
    parser.add_argument('input_file', help='Входной текстовый/markdown файл')
    parser.add_argument('-o', '--output', help='Выходной HTML файл (по умолчанию: input.html)')
    parser.add_argument('--title', help='Заголовок HTML страницы', default='')
    args = parser.parse_args()

    in_path = Path(args.input_file)
    if not in_path.exists():
        print(f"❌ Файл не найден: {in_path}")
        return 1

    out_path = Path(args.output) if args.output else in_path.with_suffix('.html')

    try:
        content = in_path.read_text(encoding='utf-8')
        html_doc = markdown_to_html(content, title=args.title or in_path.stem)
        out_path.write_text(html_doc, encoding='utf-8')
        print(f"✅ HTML создан: {out_path}")
        return 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


