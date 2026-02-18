#!/usr/bin/env python3
import json
import os
import argparse
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

class DirectorAgent:
    def __init__(self, config_file="config.env"):
        load_dotenv(config_file)
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")
        # Для простых задач сценария можно использовать модель попроще, но для качества лучше оставить топ
        self.base_url = "https://openrouter.ai/api/v1"

    def _call_llm(self, prompt, system_prompt, retries=3):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/manim-poetry"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        
        for attempt in range(retries):
            try:
                resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=60)
                if resp.status_code != 200:
                    print(f"⚠️ Ошибка API ({resp.status_code}): {resp.text}")
                    time.sleep(2)
                    continue
                    
                content = resp.json()["choices"][0]["message"]["content"]
                return json.loads(content)
            except Exception as e:
                print(f"❌ Ошибка вызова LLM (попытка {attempt+1}): {e}")
                time.sleep(2)
        return None

    def _create_bible(self, text, preferences):
        """Этап 1: Создание Библии стиля и персонажей"""
        print("   🎨 Разработка визуального стиля и персонажей...")
        prompt = f"""
        Проанализируй текст и создай "Библию проекта".
        
        ПРЕДПОЧТЕНИЯ ЗАКАЗЧИКА:
        {preferences}
        
        ТЕКСТ ПРОИЗВЕДЕНИЯ:
        {text}
        
        ЗАДАЧА:
        1. Visual Style: Опиши стиль для Stable Diffusion (освещение, палитра, рендер, детализация).
        2. Characters: Выдели ВСЕХ действующих лиц. Дай каждому `tag_name` (например, "HERO_1") и ПОДРОБНОЕ визуальное описание (возраст, одежда, лицо, прическа), которое будет повторяться в каждом промпте для консистентности.
        
        Верни JSON:
        {{
            "visual_style": "подробное описание стиля...",
            "characters": {{
                "HERO_NAME": "мужчина 30 лет, грубое лицо, шрам, военная форма...",
                "ROBOT_NAME": "ржавый робот, круглые глаза, стимпанк..."
            }}
        }}
        """
        return self._call_llm(prompt, "Ты арт-директор киностудии. Твоя задача — зафиксировать стиль и внешность героев.")

    def _create_narrative_plan(self, segments, bible):
        """Этап 2: Сценарный план (без промптов)"""
        print("   📝 Написание режиссерского сценария (действия и события)...")
        
        # Упрощаем сегменты для подачи в контекст
        simple_segments = [{"id": i, "text": s["text"]} for i, s in enumerate(segments)]
        
        prompt = f"""
        Ты режиссер. У тебя есть текст (разбитый на сегменты) и описание героев.
        Твоя задача — написать ЛОГИКУ происходящего в кадре. НЕ пиши промпты для нейросети, пиши действия для актеров и оператора.
        
        ГЕРОИ:
        {json.dumps(bible.get('characters'), ensure_ascii=False)}
        
        СЕГМЕНТЫ:
        {json.dumps(simple_segments, ensure_ascii=False)}
        
        ИНСТРУКЦИИ:
        1. Для каждого сегмента опиши `action_description`: что делают герои? (Например: "Герой смотрит в окно", "Робот машет рукой").
        2. Определи `mood`: настроение кадра.
        3. Выбери `camera_move`: "zoom_in", "zoom_out", "pan_left", "pan_right", "static".
        4. Выбери `overlay`: "snow", "rain", "embers", "stars", "none".
        5. Определи `text_position`: "top", "center", "bottom".
        
        Следи за логической связностью соседних кадров!
        
        Верни JSON:
        {{
            "plan": [
                {{
                    "segment_id": 0,
                    "action_description": "Сергей стоит под снегом и хмуро смотрит в камеру.",
                    "mood": "мрачный",
                    "camera_move": "zoom_in",
                    "overlay": "snow",
                    "text_position": "bottom"
                }},
                ...
            ]
        }}
        """
        return self._call_llm(prompt, "Ты режиссер-постановщик. Твоя задача — придумать мизансцену.")

    def _generate_detail_prompt(self, segment_text, action_desc, bible):
        """Этап 3: Генерация промпта для конкретного кадра"""
        # Этот метод вызывается в цикле для каждого кадра
        
        char_desc_str = json.dumps(bible.get('characters'), ensure_ascii=False)
        style = bible.get('visual_style')
        
        prompt = f"""
        Твоя задача — написать ИДЕАЛЬНЫЙ промпт для генерации изображения (Stable Diffusion / Midjourney).
        
        КОНТЕКСТ КАДРА:
        - Стиль: {style}
        - Действие в кадре: {action_desc}
        - Текст озвучки (для настроения): "{segment_text}"
        
        ВНЕШНОСТЬ ПЕРСОНАЖЕЙ (ОБЯЗАТЕЛЬНО ИСПОЛЬЗУЙ ЭТИ ОПИСАНИЯ ЕСЛИ ПЕРСОНАЖ ЕСТЬ В КАДРЕ):
        {char_desc_str}
        
        ИНСТРУКЦИЯ:
        1. Составь промпт на английском языке.
        2. СТРУКТУРА: [Subject Description] + [Action/Pose] + [Environment/Background] + [Lighting/Mood] + [Style Tags].
        3. Если в `action_description` упомянут персонаж (например, "Сергей"), ОБЯЗАТЕЛЬНО вставь его полное визуальное описание из списка персонажей, а не просто имя.
        4. Промпт должен быть детализированным.
        
        Верни JSON:
        {{
            "image_prompt": "full prompt here...",
            "negative_prompt": "text, watermark, blurry, bad anatomy, deformed hands, extra limbs"
        }}
        """
        
        # Для ускорения можно использовать модель попроще, но для качества оставим главную
        return self._call_llm(prompt, "Ты эксперт по промпт-инжинирингу для нейросетей.")

    def create_screenplay(self, text_file, timestamps_file, output_dir, 
                          style="", era="", region="", genre="", setting=""):
        
        # 1. Загрузка
        with open(text_file, 'r', encoding='utf-8') as f: full_text = f.read()
        with open(timestamps_file, 'r', encoding='utf-8') as f:
            segments = json.load(f).get("segments", [])

        print("🎬 [Director] Запуск многоступенчатого процесса создания...")

        # Формируем предпочтения
        prefs = f"Style: {style}, Era: {era}, Region: {region}, Genre: {genre}, Setting: {setting}"

        # === ШАГ 1: БИБЛИЯ ===
        bible = self._create_bible(full_text, prefs)
        if not bible: return
        print(f"   ✅ Библия создана. Персонажей: {len(bible.get('characters', {}))}")

        # === ШАГ 2: СЦЕНАРНЫЙ ПЛАН ===
        narrative_json = self._create_narrative_plan(segments, bible)
        if not narrative_json: return
        plan = narrative_json.get("plan", [])
        print(f"   ✅ Сценарный план готов. Сцен: {len(plan)}")

        # === ШАГ 3: ДЕТАЛИЗАЦИЯ (ПРОМПТЫ) ===
        print("   🎨 Генерация детальных промптов для каждой сцены (это займет время)...")
        
        final_screenplay = []
        illustrations_for_generation = []
        
        for i, segment in enumerate(segments):
            # Находим план для этого сегмента
            scene_plan = next((p for p in plan if p.get("segment_id") == i), None)
            if not scene_plan: 
                # Фолбек, если LLM потеряла сегмент
                scene_plan = {"action_description": "Atmospheric shot matching the text", "mood": "neutral"}
                print(f"   ⚠️ Warning: Plan missing for segment {i}, using fallback.")

            print(f"      [{i+1}/{len(segments)}] Генерация промпта для: {scene_plan.get('action_description')[:40]}...")
            
            # Генерируем промпт отдельно для этого кадра
            prompt_data = self._generate_detail_prompt(
                segment["text"], 
                scene_plan.get("action_description"), 
                bible
            )
            
            if not prompt_data:
                image_prompt = f"{bible.get('visual_style')}, {scene_plan.get('action_description')}"
                negative_prompt = "bad quality"
            else:
                image_prompt = prompt_data.get("image_prompt")
                negative_prompt = prompt_data.get("negative_prompt", "bad quality")

            # Собираем данные для Manim (screenplay.json)
            # В screenplay.json нам нужно техническое описание движения и оверлеев из ШАГА 2
            screenplay_item = {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "image_path": f"images/illustration_{i:02d}.png",
                "camera_move": scene_plan.get("camera_move", "static"),
                "overlay": scene_plan.get("overlay", "none"),
                "text_position": scene_plan.get("text_position", "bottom")
            }
            final_screenplay.append(screenplay_item)

            # Собираем данные для генератора картинок (illustrations.json)
            # Сюда кладем мощный промпт из ШАГА 3
            illustrations_for_generation.append({
                "index": i,
                "title": segment["text"][:50],
                "action_context": scene_plan.get("action_description"), # Для справки
                "prompt": image_prompt,
                "negative_prompt": negative_prompt
            })

        # Сохранение
        sp_path = os.path.join(output_dir, "screenplay.json")
        with open(sp_path, 'w', encoding='utf-8') as f:
            json.dump(final_screenplay, f, ensure_ascii=False, indent=2)
            
        il_path = os.path.join(output_dir, "illustrations.json")
        with open(il_path, 'w', encoding='utf-8') as f:
            json.dump({"illustrations": illustrations_for_generation}, f, ensure_ascii=False, indent=2)

        print(f"✅ Готово! Сценарий: {sp_path}")
        print(f"✅ Готово! Задания на генерацию: {il_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--timestamps", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--style", default="")
    parser.add_argument("--era", default="")
    parser.add_argument("--region", default="")
    parser.add_argument("--genre", default="")
    parser.add_argument("--setting", default="")

    args = parser.parse_args()
    
    agent = DirectorAgent()
    agent.create_screenplay(
        text_file=args.text, 
        timestamps_file=args.timestamps, 
        output_dir=args.output_dir,
        style=args.style,
        era=args.era,
        region=args.region,
        genre=args.genre,
        setting=args.setting
    )
