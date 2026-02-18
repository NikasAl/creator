#!/usr/bin/env python3
import json
import os
import argparse
import requests
from dotenv import load_dotenv

class TranscriptionCorrector:
    def __init__(self, config_file="config.env"):
        # Загрузка конфига
        if os.path.exists(config_file):
            load_dotenv(config_file)
        
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("DEFAULT_MODEL", "anthropic/claude-3.5-sonnet") 
        self.base_url = "https://openrouter.ai/api/v1"

        if not self.api_key:
            print("⚠️ Warning: OPENROUTER_API_KEY not found in config.")

    def _call_llm(self, prompt, system_prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
             "HTTP-Referer": "https://github.com/manim-poetry",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3  # Низкая температура для точности
        }
        
        try:
            resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            if resp.status_code != 200:
                print(f"❌ API Error: {resp.text}")
                return None
            
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            return None

    def correct_timestamps(self, json_path, reference_path):
        # 1. Чтение данных
        with open(json_path, 'r', encoding='utf-8') as f:
            ts_data = json.load(f)
        
        with open(reference_path, 'r', encoding='utf-8') as f:
            reference_text = f.read()

        segments = ts_data.get("segments", [])
        if not segments:
            print("⚠️ Нет сегментов для коррекции.")
            return

        # Извлекаем только текст, чтобы не сбить тайминги
        original_lines = [s["text"] for s in segments]
        
        print(f"🔧 Коррекция {len(original_lines)} сегментов по эталонному тексту...")

        # 2. Формируем промпт
        system_prompt = (
            "Ты — профессиональный редактор субтитров. Твоя задача — исправить ошибки транскрибации "
            "в сегментах, используя эталонный текст. "
            "ВАЖНО: Ты НЕ должен менять разбивку на сегменты. Количество сегментов на выходе "
            "должно СТРОГО совпадать с количеством сегментов на входе."
        )

        user_prompt = f"""
        У меня есть список фраз, полученных автоматической транскрибацией (с ошибками), 
        и оригинальный текст (эталон).

        ЭТАЛОННЫЙ ТЕКСТ:
        {reference_text}

        СЕГМЕНТЫ (для коррекции, если находятся ошибки):
        {json.dumps(original_lines, ensure_ascii=False)}

        ЗАДАЧА:
        1. Найди соответствующие куски текста в эталоне.
        2. Исправь орфографию и слова в сегментах, чтобы они совпадали с эталоном.
        3. Если Whisper разбил фразу посреди слова или предложения — сохрани этот разрыв. Не объединяй и не разделяй сегменты.
        4. Верни JSON с ключом "corrected_lines", содержащим список строк.

        Верни ТОЛЬКО JSON:
        {{
            "corrected_lines": ["строка 1", "строка 2", ...]
        }}
        """

        # 3. Запрос к LLM
        result = self._call_llm(user_prompt, system_prompt)
        
        if not result or "corrected_lines" not in result:
            print("❌ Не удалось получить корректный JSON от LLM.")
            return

        corrected_lines = result["corrected_lines"]

        # 4. Проверка и сохранение
        if len(corrected_lines) != len(segments):
            print(f"❌ Ошибка: Количество сегментов изменилось! Было {len(segments)}, стало {len(corrected_lines)}. Отмена сохранения.")
            print(f"{segments}")
            print("---")
            print(f"{corrected_lines}")
            # Можно добавить логику "попытаться спасти", но пока безопаснее не трогать
            return

        # Обновляем текст в исходной структуре
        for i, seg in enumerate(segments):
            # Можно вывести дифф для проверки
            # if seg["text"] != corrected_lines[i]:
            #     print(f"   Было: {seg['text']}\n   Стало: {corrected_lines[i]}")
            seg["text"] = corrected_lines[i]

        # Сохраняем обратно
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ts_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Успешно исправлено и сохранено: {json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Путь к sentence_timestamps.json")
    parser.add_argument("--reference", required=True, help="Путь к song.txt")
    args = parser.parse_args()
    
    corrector = TranscriptionCorrector()
    corrector.correct_timestamps(args.json, args.reference)