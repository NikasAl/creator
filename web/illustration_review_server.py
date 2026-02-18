#!/usr/bin/env python3
"""
Локальный веб-UI для обзора и (пере)генерации изображений по illustrations.json.

Функции:
- Показывает сеткой все иллюстрации: миниатюры, названия, текущий prompt
- Позволяет редактировать prompt/negative_prompt и сгенерировать/перегенерировать одну карточку
- Сохраняет отредактированные prompt в исходный JSON

Запуск:
  python web/illustration_review_server.py --json pipeline_X/illustrations.json --images-dir pipeline_X/images --config config.env --width 1366 --height 768 --steps 4

Затем откройте http://127.0.0.1:5000/
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from flask import Flask, request, redirect, url_for, render_template_string, flash

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from image_generators.together_image_generator import TogetherImageGenerator, ImageParams


HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>Illustrations Review</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 16px; }
    header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 12px; background: #fafafa; }
    .thumb { width: 100%; height: auto; border-radius: 8px; background: #eee; display: block; }
    .meta { font-size: 12px; color: #666; margin-top: 6px; }
    textarea { width: 100%; min-height: 120px; resize: vertical; font-family: monospace; }
    input[type="text"] { width: 100%; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .actions { display: flex; gap: 8px; margin-top: 8px; }
    .success { color: #0a0; }
    .error { color: #a00; }
    .topline { font-size: 14px; color: #333; }
  </style>
</head>
<body>
  <header>
    <h2>Illustrations Review</h2>
    <div class="topline">JSON: {{ json_name }} | Images dir: {{ images_dir_name }} | Model spacing ~{{ spacing }}s</div>
  </header>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      <ul>
      {% for category, message in messages %}
        <li class="{{ category }}">{{ message }}</li>
      {% endfor %}
      </ul>
    {% endif %}
  {% endwith %}

  <div class="grid">
    {% for item in illustrations %}
      <div class="card">
        <div class="meta">#{{ item.index }} — {{ item.title }}</div>
        {% if item.image_exists %}
          <img class="thumb" src="/image/{{ item.filename }}?t={{ item.mtime }}" alt="thumb" />
        {% else %}
          <div class="thumb" style="display:flex;align-items:center;justify-content:center;height:200px;color:#888;">no image</div>
        {% endif %}
        <form method="post" action="{{ url_for('generate', idx=item.index) }}">
          <div class="meta">Prompt</div>
          <textarea name="prompt">{{ item.prompt }}</textarea>
          <div class="row">
            <div>
              <div class="meta">Negative prompt</div>
              <input type="text" name="negative" value="{{ item.negative }}" />
            </div>
            <div>
              <div class="meta">Size WxH</div>
              <input type="text" name="width" value="{{ width }}" />
              <input type="text" name="height" value="{{ height }}" />
              <div class="meta">Steps: <input type="text" name="steps" value="{{ steps }}" style="width:56px;" /> Seed: <input type="text" name="seed" value="" style="width:80px;" /></div>
            </div>
          </div>
          <div class="actions">
            <button type="submit">Generate</button>
            {% if item.image_exists %}<a href="/image/{{ item.filename }}" download>Download</a>{% endif %}
          </div>
        </form>
      </div>
    {% endfor %}
  </div>
</body>
</html>
"""


def create_app(json_path: Path, images_dir: Path, config: Optional[str], width: int, height: int, steps: int):
    app = Flask(__name__)
    app.secret_key = "illustration_review_secret"

    # генератор (глобально на приложение)
    generator = TogetherImageGenerator(config)

    def load_data():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return data

    def save_data(data):
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @app.get("/")
    def index():
        data = load_data()
        illustrations = data.get("illustrations", [])

        cards = []
        for it in illustrations:
            idx = it.get("index")
            title = it.get("title", f"Part {idx}")
            prompt = it.get("prompt", "")
            negative = it.get("negative_prompt", "")
            filename = f"illustration_{idx:02d}.png"
            file_path = images_dir / filename
            exists = file_path.exists()
            mtime = int(file_path.stat().st_mtime) if exists else 0
            cards.append({
                "index": idx,
                "title": title,
                "prompt": prompt,
                "negative": negative,
                "filename": filename,
                "image_exists": exists,
                "mtime": mtime,
            })

        return render_template_string(
            HTML,
            illustrations=cards,
            json_name=json_path.name,
            images_dir_name=images_dir.name,
            width=width,
            height=height,
            steps=steps,
            spacing=getattr(generator, "_min_spacing_sec", 12.5),
        )

    @app.get("/image/<path:name>")
    def image(name: str):
        path = images_dir / name
        if not path.exists():
            return ("Not found", 404)
        # минимальный sendfile без x-sendfile
        data = path.read_bytes()
        return (data, 200, {"Content-Type": "image/png"})

    @app.post("/generate/<int:idx>")
    def generate(idx: int):
        data = load_data()
        illustrations = data.get("illustrations", [])
        item = next((x for x in illustrations if int(x.get("index")) == idx), None)
        if not item:
            flash(("error", f"Не найдена иллюстрация #{idx}"))
            return redirect(url_for("index"))

        # читаем поля формы
        new_prompt = request.form.get("prompt", "").strip()
        new_negative = request.form.get("negative", "").strip()
        try:
            w = int(request.form.get("width", str(width)))
            h = int(request.form.get("height", str(height)))
            st = int(request.form.get("steps", str(steps)))
        except ValueError:
            flash(("error", "Некорректные параметры размера/шагов"))
            return redirect(url_for("index"))
        seed_val = request.form.get("seed")
        seed = int(seed_val) if seed_val and seed_val.isdigit() else None

        # Обновляем JSON (сохраним отредактированные промпты)
        item["prompt"] = new_prompt
        item["negative_prompt"] = new_negative
        save_data(data)

        # Генерация
        try:
            images_dir.mkdir(parents=True, exist_ok=True)
            meta = generator.generate_and_save(
                prompt=new_prompt,
                negative_prompt=new_negative,
                params=ImageParams(width=w, height=h, steps=st, seed=seed),
                out_path=str(images_dir / f"illustration_{idx:02d}.png"),
            )
            flash(("success", f"Готово #{idx}: {meta['width']}x{meta['height']}, steps={meta['steps']}"))
        except Exception as e:
            flash(("error", f"Ошибка генерации #{idx}: {e}"))

        return redirect(url_for("index"))

    return app


def main():
    parser = argparse.ArgumentParser(description="Веб-UI для обзора и генерации иллюстраций")
    parser.add_argument("--pipeline-dir", help="Каталог пайплайна; внутри ожидаются illustrations.json и папка images/")
    parser.add_argument("--json", help="Путь к illustrations.json (переопределяет --pipeline-dir)")
    parser.add_argument("--images-dir", help="Каталог для изображений (переопределяет --pipeline-dir)")
    parser.add_argument("--config", default="config.env", help="Файл .env/config.env с TOGETHER_API_KEY (по умолчанию: config.env)")
    parser.add_argument("--width", type=int, default=1366)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    # Автоопределение путей по --pipeline-dir
    if args.pipeline_dir:
        p = Path(args.pipeline_dir)
        if not args.json:
            args.json = str(p / "illustrations.json")
        if not args.images_dir:
            args.images_dir = str(p / "images")

    # Если указан только один из путей — попробуем вывести второй из соседства
    if args.json and not args.images_dir:
        args.images_dir = str(Path(args.json).parent / "images")
    if args.images_dir and not args.json:
        args.json = str(Path(args.images_dir).parent / "illustrations.json")

    if not args.json or not args.images_dir:
        print("❌ Укажите --pipeline-dir или оба пути: --json и --images-dir")
        return 1

    json_path = Path(args.json)
    images_dir = Path(args.images_dir)
    if not json_path.exists():
        print(f"❌ JSON не найден: {json_path}")
        return 1

    app = create_app(json_path, images_dir, args.config, args.width, args.height, args.steps)
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


