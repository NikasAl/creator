#!/usr/bin/env python3
"""
CLI для ручного обзора и генерации/перегенерации изображений по файлу иллюстраций.

Функционал:
- Загружает JSON c иллюстрациями (создаётся illustration_prompt_processor)
- Для каждого элемента генерирует изображение через Together API
- Позволяет указать подкаталог для результатов, размер, сид, шаги
- Создаёт HTML-галерею для визуального обзора

Примеры:
python illustration_review_cli.py --pipeline-dir pipeline_X --width 1366 --height 768 --steps 4
python illustration_review_cli.py pipeline_X/illustrations.json --out-dir pipeline_X/images --width 1366 --height 768 --steps 4
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from image_generators.together_image_generator import TogetherImageGenerator, ImageParams


def save_gallery_html(images_dir: Path, json_file: Path, html_out: Path):
    images = sorted(images_dir.glob("*.png"))
    items = []
    for img in images:
        items.append(f'<div class="item"><img src="{img.name}" /><div class="name">{img.name}</div></div>')
    body = "\n".join(items)
    html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>Illustration Review</title>
  <style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }}
    .item {{ border: 1px solid #ddd; padding: 8px; border-radius: 8px; background: #fafafa; }}
    img {{ width: 100%; height: auto; display: block; border-radius: 6px; }}
    .name {{ margin-top: 6px; font-size: 12px; color: #555; word-break: break-all; }}
    .meta {{ margin: 10px 0; color: #666; font-size: 14px; }}
  </style>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="generator" content="Illustration Review CLI" />
  <meta name="generated_at" content="{datetime.now().isoformat()}" />
  <meta name="source_json" content="{json_file.name}" />
  <meta name="images_dir" content="{images_dir.name}" />
  <link rel="preload" as="image" href="{images[0].name if images else ''}">
  <link rel="prefetch" href="{images[1].name if len(images) > 1 else ''}">
  <link rel="prefetch" href="{images[2].name if len(images) > 2 else ''}">
  <link rel="prefetch" href="{images[3].name if len(images) > 3 else ''}">
  <link rel="prefetch" href="{images[4].name if len(images) > 4 else ''}">
  <link rel="prefetch" href="{images[5].name if len(images) > 5 else ''}">
</head>
<body>
  <h1>Illustration Review</h1>
  <div class="meta">Source: {json_file.name} | Images dir: {images_dir.name}</div>
  <div class="grid">
    {body}
  </div>
</body>
</html>
"""
    html_out.write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Генерация изображений по JSON иллюстраций с ручным обзором")
    parser.add_argument("illustrations_json", nargs="?", help="Путь к illustrations.json")
    parser.add_argument("--pipeline-dir", help="Каталог пайплайна; внутри ожидаются illustrations.json и папка images/")
    parser.add_argument("--out-dir", help="Каталог для сохранения изображений (переопределяет --pipeline-dir)")
    parser.add_argument("--config", default="config.env", help="Файл конфигурации .env/config.env (по умолчанию: config.env)")
    parser.add_argument("--width", type=int, default=1366)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--index", type=int, help="Сгенерировать только указанную часть (index из JSON)")
    parser.add_argument("--regenerate", action="store_true", help="Перегенерировать даже если файл существует")
    args = parser.parse_args()

    # Автоопределение путей по --pipeline-dir
    if args.pipeline_dir:
        p = Path(args.pipeline_dir)
        if not args.illustrations_json:
            args.illustrations_json = str(p / "illustrations.json")
        if not args.out_dir:
            args.out_dir = str(p / "images")

    if not args.illustrations_json:
        print("❌ Укажите --pipeline-dir или путь к JSON")
        return 1
    if not args.out_dir:
        # если указали только JSON — выведем соседний images
        args.out_dir = str(Path(args.illustrations_json).parent / "images")

    json_path = Path(args.illustrations_json)
    if not json_path.exists():
        print(f"❌ Не найден файл: {json_path}")
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    illustrations = data.get("illustrations", [])
    if not illustrations:
        print("❌ В JSON нет иллюстраций")
        return 1

    try:
        generator = TogetherImageGenerator(args.config)
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("Добавьте TOGETHER_API_KEY в config.env/.env")
        return 1

    params = ImageParams(width=args.width, height=args.height, steps=args.steps, seed=args.seed)

    total = len(illustrations)
    for item in illustrations:
        idx = item.get("index")
        title = item.get("title", f"Part {idx}")
        prompt = item.get("prompt")
        negative = item.get("negative_prompt")

        if args.index is not None and idx != args.index:
            continue

        outfile = out_dir / f"illustration_{idx:02d}.png"
        if outfile.exists() and not args.regenerate:
            print(f"⏭️  Пропуск {outfile.name} (уже существует)")
            continue

        print(f"🎨 Генерация {idx}/{total}: {title[:60]}...")
        try:
            meta = generator.generate_and_save(prompt=prompt, negative_prompt=negative, params=params, out_path=str(outfile))
            print(f"✅ Сохранено: {outfile.name} ({meta['width']}x{meta['height']}, {meta['steps']} steps)")
        except Exception as e:
            print(f"❌ Ошибка генерации для части {idx}: {e}")

    # HTML галерея
    html_out = out_dir / "gallery.html"
    save_gallery_html(out_dir, json_path, html_out)
    print(f"📄 Галерея: {html_out}")

    print("🎉 Готово")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


