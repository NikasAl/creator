#!/usr/bin/env python3
import argparse
import os
import requests
import subprocess
from dotenv import load_dotenv

def generate_lyrics(input_spec, input_script, output_path, model, config_file):
    if config_file: load_dotenv(config_file)
    else: load_dotenv()

    # Читаем исходники урока
    context_text = ""
    if os.path.exists(input_spec):
        with open(input_spec, 'r', encoding='utf-8') as f: context_text += f"ТЕОРИЯ:\n{f.read()}\n\n"
    if os.path.exists(input_script):
        with open(input_script, 'r', encoding='utf-8') as f: context_text += f"ЛЕКЦИЯ:\n{f.read()}\n"

    prompt = f"""
    ТЫ: Гениальный поэт-сатирик с математическим уклоном (в стиле Пушкина).
    ЗАДАЧА: Написать текст песни (куплеты и припевы) на основе материала урока.
    
    ИСХОДНЫЙ МАТЕРИАЛ:
    {context_text}
    
    ТРЕБОВАНИЯ:
    1. Структура: [Куплет 1], [Припев], [Куплет 2], [Припев], [Бридж], [Финал].
    2. Стиль: Ироничный, высокий штиль, но с математическими терминами. Рифма должна быть идеальной.
    3. Содержание: Нужно пересказать суть формул, но весело. 
       Пример: "Квадрат суммы двух чисел есть квадрат первого, плюс удвоенное произведение..." должно звучать как поэзия.
    4. Для формул используй слова.
    5. Эмоция: Пафос, драма или безудержное веселье.
    """

    # === РЕЖИМ CUSTOM ===
    if model == "custom":
        print("\n" + "="*60)
        print("🎵 ГЕНЕРАЦИЯ ТЕКСТА ПЕСНИ")
        print("="*60)
        print(prompt)
        print("-" * 60)
        
        if not os.path.exists(output_path):
            open(output_path, 'w').close()
            
        print(f"1. Скопируйте промпт в LLM.")
        print(f"2. Сохраните результат в: {output_path}")
        
        try:
            subprocess.run(["subl", "-w", output_path], check=True)
            print(f"✅ Текст песни сохранен: {output_path}")
        except FileNotFoundError:
            input("Нажмите Enter, когда сохраните файл...")
        return

    # === РЕЖИМ API (если нужно) ===
    # (Здесь можно добавить код для API, аналогичный lesson_generator.py, если захочешь автоматику)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="custom")
    parser.add_argument("--config")
    
    args = parser.parse_args()
    generate_lyrics(args.spec, args.script, args.output, args.model, args.config)
