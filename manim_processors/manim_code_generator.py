#!/usr/bin/env python3
import argparse
import json
import os
import requests
import subprocess
from dotenv import load_dotenv

class ManimGenerator:
    def __init__(self, config_file):
        if config_file: load_dotenv(config_file)
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        
    def generate(self, mode, spec_file, script_file, timestamps_file, example_file, input_code_file, output_file, model_choice, style="standard"):
        prompt = ""
        
        # === РЕЖИМ 1: ВИЗУАЛИЗАЦИЯ (VISUALS) ===
        if mode == "visuals":
            with open(spec_file, 'r', encoding='utf-8') as f: spec = f.read()
            with open(script_file, 'r', encoding='utf-8') as f: script = f.read()
            with open(example_file, 'r', encoding='utf-8') as f: example = f.read()

            # --- ЛОГИКА СТИЛЕЙ ---
            if style == "music_video":
                style_instructions = """
    !!! ЭТО МУЗЫКАЛЬНЫЙ КЛИП (MUSIC VIDEO) !!!
    Твоя цель — создать динамичное, ритмичное и зрелищное шоу.
    
    1. ВИЗУАЛ:
       - Используй яркие, неоновые цвета (TEAL, YELLOW, PINK, PURPLE, RED).
       - Фон не обязательно черный, можно темно-серый или с легкими геометрическими фигурами на заднем плане.
    
    2. КАМЕРА И ДВИЖЕНИЕ:
       - Камера НЕ должна стоять на месте. Используй `self.camera.frame.animate.move_to(...)` или `set(width=...)` для зума/панорамирования.
       - Объекты должны вылетать, крутиться, пульсировать. Используй `Indicate`, `Flash`, `Wiggle`, `ApplyWave`.
       - Избегай статики. Если формула написана, она может медленно дрейфовать или менять цвет.
    
    3. РИТМ:
       - Анимации должны быть быстрыми (`run_time=0.5` или `0.8`).
       - Используй `ShowPassingFlash` для эффектов обводки.
    """
            else:
                # Стандартный образовательный стиль
                style_instructions = """
    Твоя задача — создать КРАСИВУЮ и ПОНЯТНУЮ образовательную анимацию.
    Сосредоточься на ясности изложения, плавных переходах и академической строгости.
    """

            prompt = f"""
Ты — эксперт по Manim (Python). 
{style_instructions}

--- ИСХОДНЫЕ ДАННЫЕ ---
1. ТЕМА/ЗАДАЧА (SPEC):
{spec}

2. ТЕКСТ ПЕСНИ/СЦЕНАРИЯ (SCRIPT):
{script}

3. ОБРАЗЕЦ КОДА:
{example}
--- КОНЕЦ ДАННЫХ ---

ТРЕБОВАНИЯ К КОДУ:
1. Выдай ТОЛЬКО код Python (начинай с imports, создай класс Scene).
2. Используй Tex/MathTex для формул.
3. Используй self.next_section() для разделения смысловых блоков.
4. НЕ используй абсолютные пути к файлам.
"""

        # === РЕЖИМ 2: СИНХРОНИЗАЦИЯ (SYNC) ===
        elif mode == "sync":
            with open(input_code_file, 'r', encoding='utf-8') as f: draft_code = f.read()
            with open(timestamps_file, 'r', encoding='utf-8') as f: ts_data = json.load(f)
            
            segments_str = ""
            # Берем больше сегментов, так как в песне строк может быть много
            for i, seg in enumerate(ts_data.get("segments", [])): 
                segments_str += f"[{seg['start']:.2f}s - {seg['end']:.2f}s]: \"{seg['text']}\"\n"
            
            prompt = f"""
Ты — эксперт по Manim. Твоя задача — добавить динамические эффекты задержек в код, чтобы синхронизировать его с аудио.

--- ИСХОДНЫЕ ДАННЫЕ ---
1. КОД АНИМАЦИИ (DRAFT):
{draft_code}

2. ТАЙМИНГИ (СЕКУНДЫ):
{segments_str}

--- ЗАДАЧА ---
1. Вставь динамически эффекты задежки между анимациями.
2. Время ожидания нужно заполнить эффектами движением видимых элементов или камеры, периодическим изменением масштаба или покачиваниями.
3. Выдай полный готовый код Python.
"""

        # === ОБРАБОТКА ЗАПРОСА (без изменений логики, только вызов) ===
        if model_choice == "custom":
            print("\n" + "="*60)
            print(f"🤖 РЕЖИМ CUSTOM MODEL: [{mode.upper()}] Стиль: {style}")
            print("="*60)
            print("1. Скопируйте ВЕСЬ текст промпта ниже и отправьте в чат LLM.")
            print("-" * 60)
            print(prompt)
            print("-" * 60)
            
            if not os.path.exists(output_file):
                open(output_file, 'w').close()
            
            try:
                subprocess.run(["subl", "-w", output_file], check=True)
            except FileNotFoundError:
                input(f"Нажмите Enter после сохранения файла {output_file}...")
            return

        # Режим API
        model = os.getenv("QUALITY_MODEL", "openai/gpt-4o") if model_choice == "quality" else os.getenv("DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")
        
        print(f"🤖 Генерация ({mode}) через API ({model})... Стиль: {style}")
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7 if style == "music_video" else 0.5 # Больше креатива для музыки
                }
            )
            # ... (стандартная обработка ответа)
            resp.raise_for_status()
            code = resp.json()['choices'][0]['message']['content']
            code = code.replace("```python", "").replace("```", "").strip()
            with open(output_file, 'w', encoding='utf-8') as f: f.write(code)
            print(f"✅ Код сохранен: {output_file}")
            
        except Exception as e:
            print(f"❌ Ошибка генерации кода: {e}")
            exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=['visuals', 'sync'])
    parser.add_argument("--spec-file")
    parser.add_argument("--script-file")
    parser.add_argument("--example-file")
    parser.add_argument("--timestamps-file")
    parser.add_argument("--input-code-file")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="custom")
    parser.add_argument("--config")
    # НОВЫЙ АРГУМЕНТ
    parser.add_argument("--style", default="standard", choices=['standard', 'music_video'], help="Стиль анимации")
    
    args = parser.parse_args()
    
    gen = ManimGenerator(args.config)
    gen.generate(
        mode=args.mode,
        spec_file=args.spec_file,
        script_file=args.script_file,
        timestamps_file=args.timestamps_file,
        example_file=args.example_file,
        input_code_file=args.input_code_file,
        output_file=args.output,
        model_choice=args.model,
        style=args.style  # Передаем стиль
    )