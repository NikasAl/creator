#!/usr/bin/env python3
"""
Генератор изображений через Alibaba Cloud Model Studio WAN API.
Создает изображения из текстовых промптов с помощью text-to-image модели.

Использует промпты из illustrations.json для генерации новых изображений
с помощью различных моделей Alibaba Cloud.
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv


class AlibabaImageGenerator:
    def __init__(self, config_file: Optional[str] = None):
        """Инициализация генератора изображений"""
        self.load_config(config_file)
        self.stats = {
            'images_generated': 0,
            'api_calls': 0,
            'total_images_used': 0,
            'errors': 0
        }
    
    def load_config(self, config_file: Optional[str] = None):
        """Загружает конфигурацию из .env файла"""
        # Пытаемся загрузить конфигурацию
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            # Ищем .env файл в текущей директории
            env_files = ['.env', 'config.env', 'settings.env']
            for env_file in env_files:
                if Path(env_file).exists():
                    load_dotenv(env_file)
                    break
        
        # Загружаем параметры Alibaba Cloud
        self.alibaba_api_key = os.getenv('ALIBABA_API_KEY')
        self.alibaba_base_url = os.getenv('ALIBABA_BASE_URL', 'https://dashscope-intl.aliyuncs.com/api/v1')
        self.alibaba_image_model = os.getenv('ALIBABA_IMAGE_MODEL', 'wan2.5-t2i-preview')
        
        # Проверяем наличие обязательных ключей
        if not self.alibaba_api_key:
            raise ValueError("ALIBABA_API_KEY не найден в конфигурации")
        
        print(f"✅ Конфигурация загружена:")
        print(f"   Alibaba API: {self.alibaba_base_url}")
        print(f"   Изображение модель: {self.alibaba_image_model}")
    
    def load_pipeline_data(self, pipeline_dir: Path) -> Tuple[str, List[Dict]]:
        """Загружает данные пайплайна: текст стихов и иллюстрации"""
        pipeline_dir = Path(pipeline_dir)
        
        # Загружаем текст стихов
        song_file = pipeline_dir / "song.txt"
        if not song_file.exists():
            raise FileNotFoundError(f"Файл song.txt не найден в {pipeline_dir}")
        
        with open(song_file, 'r', encoding='utf-8') as f:
            song_text = f.read().strip()
        
        # Загружаем иллюстрации
        illustrations_file = pipeline_dir / "illustrations.json"
        if not illustrations_file.exists():
            raise FileNotFoundError(f"Файл illustrations.json не найден в {pipeline_dir}")
        
        with open(illustrations_file, 'r', encoding='utf-8') as f:
            illustrations_data = json.load(f)
        
        illustrations = illustrations_data.get('illustrations', [])
        
        print(f"📚 Загружены данные пайплайна:")
        print(f"   Текст стихов: {len(song_text)} символов")
        print(f"   Иллюстраций: {len(illustrations)}")
        
        return song_text, illustrations
    
    def create_image_task(self, prompt: str, negative_prompt: str = "", 
                         size: str = "1024*1024", n: int = 1, 
                         prompt_extend: bool = False, watermark: bool = False,
                         seed: Optional[int] = None) -> Optional[str]:
        """Создает задачу генерации изображения через Alibaba Cloud API"""
        
        try:
            # Подготавливаем параметры запроса
            headers = {
                "X-DashScope-Async": "enable",
                "Authorization": f"Bearer {self.alibaba_api_key}",
                "Content-Type": "application/json"
            }
            
            # Подготавливаем параметры
            parameters = {
                "size": size,
                "n": n,
                "prompt_extend": prompt_extend,
                "watermark": watermark
            }
            
            # Добавляем seed если указан
            if seed is not None:
                parameters["seed"] = seed
            
            # Подготавливаем input
            input_data = {
                "prompt": prompt
            }
            
            # Добавляем negative_prompt если указан
            if negative_prompt:
                input_data["negative_prompt"] = negative_prompt
            
            payload = {
                "model": self.alibaba_image_model,
                "input": input_data,
                "parameters": parameters
            }
            
            print(f"🎨 Отправка запроса на генерацию изображения...")
            print(f"   Модель: {self.alibaba_image_model}")
            print(f"   Размер: {size}")
            print(f"   Количество: {n}")
            print(f"   Промпт: {prompt[:100]}...")
            if negative_prompt:
                print(f"   Негативный промпт: {negative_prompt[:100]}...")
            
            # Отправляем запрос на создание задачи
            response = requests.post(
                f"{self.alibaba_base_url}/services/aigc/text2image/image-synthesis",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Ошибка API: {response.status_code} - {response.text}")
            
            result = response.json()
            
            if "output" not in result or "task_id" not in result["output"]:
                raise Exception(f"Неожиданный формат ответа: {result}")
            
            task_id = result["output"]["task_id"]
            print(f"✅ Задача создана: {task_id}")
            
            return task_id
            
        except Exception as e:
            print(f"❌ Ошибка создания задачи: {e}")
            self.stats['errors'] += 1
            return None
    
    def poll_task_result(self, task_id: str, max_wait_time: int = 900) -> Optional[List[Dict]]:
        """Ожидает завершения задачи и возвращает результаты"""
        
        headers = {
            "Authorization": f"Bearer {self.alibaba_api_key}"
        }
        
        start_time = time.time()
        poll_interval = 10  # Интервал опроса в секундах
        
        print(f"⏳ Ожидание завершения задачи {task_id}...")
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(
                    f"{self.alibaba_base_url}/tasks/{task_id}",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    print(f"⚠️  Ошибка запроса статуса: {response.status_code}")
                    time.sleep(poll_interval)
                    continue
                
                result = response.json()
                
                if "output" not in result:
                    print(f"⚠️  Неожиданный формат ответа: {result}")
                    time.sleep(poll_interval)
                    continue
                
                task_status = result["output"].get("task_status", "UNKNOWN")
                
                print(f"📊 Статус задачи: {task_status}")
                
                if task_status == "SUCCEEDED":
                    results = result["output"].get("results", [])
                    if results:
                        print(f"✅ Изображения готовы: {len(results)} шт.")
                        return results
                    else:
                        print("❌ Результаты не найдены в ответе")
                        return None
                
                elif task_status == "FAILED":
                    error_msg = result.get("message", "Неизвестная ошибка")
                    print(f"❌ Задача завершилась с ошибкой: {error_msg}")
                    return None
                
                elif task_status in ["PENDING", "RUNNING"]:
                    print(f"⏳ Задача выполняется, ожидание {poll_interval}с...")
                    time.sleep(poll_interval)
                    continue
                
                else:
                    print(f"⚠️  Неизвестный статус: {task_status}")
                    time.sleep(poll_interval)
                    continue
                    
            except Exception as e:
                print(f"⚠️  Ошибка опроса статуса: {e}")
                time.sleep(poll_interval)
                continue
        
        print(f"⏰ Превышено время ожидания ({max_wait_time}с)")
        return None
    
    def generate_image(self, prompt: str, negative_prompt: str = "", 
                      size: str = "1024*1024", n: int = 1, 
                      prompt_extend: bool = False, watermark: bool = False,
                      seed: Optional[int] = None) -> Optional[List[Dict]]:
        """Генерирует изображение через Alibaba Cloud API (асинхронно)"""
        
        # Создаем задачу
        task_id = self.create_image_task(
            prompt, negative_prompt, size, n, prompt_extend, watermark, seed
        )
        if not task_id:
            return None
        
        # Ожидаем завершения
        results = self.poll_task_result(task_id)
        return results
    
    def download_image(self, image_url: str, output_path: Path) -> bool:
        """Скачивает изображение по URL"""
        try:
            print(f"📥 Скачивание изображения: {image_url}")
            
            response = requests.get(image_url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Изображение сохранено: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка скачивания изображения: {e}")
            self.stats['errors'] += 1
            return False
    
    def generate_images_for_indices(self, pipeline_dir: Path, image_indices: List[int],
                                  size: str = "1024*1024", n: int = 1,
                                  prompt_extend: bool = False, watermark: bool = False,
                                  seed: Optional[int] = None, confirm: bool = True) -> bool:
        """Генерирует изображения для указанных индексов"""
        
        pipeline_dir = Path(pipeline_dir)
        images_dir = pipeline_dir / "images"
        
        if not images_dir.exists():
            raise FileNotFoundError(f"Каталог images не найден в {pipeline_dir}")
        
        # Загружаем данные пайплайна
        song_text, illustrations = self.load_pipeline_data(pipeline_dir)
        
        # Находим соответствующие иллюстрации
        illustrations_to_generate = []
        for index in image_indices:
            illustration = None
            for ill in illustrations:
                if ill.get('index') == index:
                    illustration = ill
                    break
            
            if not illustration:
                print(f"⚠️  Иллюстрация с индексом {index} не найдена")
                continue
            
            illustrations_to_generate.append((index, illustration))
        
        if not illustrations_to_generate:
            print("❌ Не найдено ни одной иллюстрации для генерации")
            return False
        
        # Показываем детали генерации
        print(f"\n🎨 ДЕТАЛИ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ:")
        print(f"=" * 50)
        print(f"📁 Пайплайн: {pipeline_dir}")
        print(f"🖼️  Изображений для генерации: {len(illustrations_to_generate)}")
        print(f"📐 Размер: {size}")
        print(f"🔢 Количество на промпт: {n}")
        print(f"💰 Модель: {self.alibaba_image_model}")
        print(f"🔧 Prompt extend: {prompt_extend}")
        print(f"🏷️  Watermark: {watermark}")
        if seed is not None:
            print(f"🌱 Seed: {seed}")
        print(f"=" * 50)
        
        # Запрашиваем подтверждение
        if confirm:
            user_input = input("\n❓ Продолжить генерацию изображений? (y/N): ").strip().lower()
            if user_input != 'y':
                print("❌ Генерация отменена пользователем")
                return False
        
        success_count = 0
        
        # Генерируем изображения для каждой иллюстрации
        for index, illustration in illustrations_to_generate:
            print(f"\n🎨 Генерация изображения {index}...")
            print(f"   Название: {illustration.get('title', '')}")
            print(f"   Промпт: {illustration.get('prompt', '')[:100]}...")
            
            # Генерируем изображение
            results = self.generate_image(
                prompt=illustration.get('prompt', ''),
                negative_prompt=illustration.get('negative_prompt', ''),
                size=size,
                n=n,
                prompt_extend=prompt_extend,
                watermark=watermark,
                seed=seed
            )
            
            if not results:
                print(f"❌ Не удалось сгенерировать изображение {index}")
                continue
            
            # Скачиваем изображения
            for i, result in enumerate(results):
                if n == 1:
                    output_path = images_dir / f"illustration_{index:02d}_alibaba.png"
                else:
                    output_path = images_dir / f"illustration_{index:02d}_alibaba_{i+1}.png"
                
                success = self.download_image(result['url'], output_path)
                if success:
                    success_count += 1
                    print(f"✅ Изображение {index} сохранено: {output_path}")
                    
                    # Обновляем статистику
                    self.stats['images_generated'] += 1
                    self.stats['total_images_used'] += 1
        
        print(f"\n🎉 ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
        print(f"📊 Статистика:")
        print(f"   Изображений создано: {success_count}")
        print(f"   API вызовов: {self.stats['api_calls']}")
        print(f"   Всего изображений использовано: {self.stats['total_images_used']}")
        print(f"   Ошибок: {self.stats['errors']}")
        
        return success_count > 0


def main():
    parser = argparse.ArgumentParser(description="Генерация изображений через Alibaba Cloud Model Studio")
    parser.add_argument("--pipeline-dir", required=True, help="Каталог пайплайна с images/ и song.txt")
    parser.add_argument("--indices", required=True, help="Номера изображений для генерации (через запятую, например: 1,3,5)")
    parser.add_argument("--size", default="1024*1024", help="Размер изображения (например: 1024*1024, 1280*720)")
    parser.add_argument("--n", type=int, default=1, help="Количество изображений на промпт (1-4)")
    parser.add_argument("--prompt-extend", action="store_true", help="Включить расширение промпта")
    parser.add_argument("--watermark", action="store_true", help="Добавить водяной знак")
    parser.add_argument("--seed", type=int, help="Seed для воспроизводимости результатов")
    parser.add_argument("--no-confirm", action="store_true", help="Не запрашивать подтверждение")
    parser.add_argument("--config", help="Путь к файлу конфигурации")
    
    args = parser.parse_args()
    
    try:
        # Парсим индексы
        try:
            image_indices = [int(x.strip()) for x in args.indices.split(',')]
        except ValueError:
            print("❌ Ошибка: индексы должны быть числами, разделенными запятыми")
            return 1
        
        # Создаем генератор
        generator = AlibabaImageGenerator(args.config)
        
        # Генерируем изображения
        success = generator.generate_images_for_indices(
            pipeline_dir=args.pipeline_dir,
            image_indices=image_indices,
            size=args.size,
            n=args.n,
            prompt_extend=args.prompt_extend,
            watermark=args.watermark,
            seed=args.seed,
            confirm=not args.no_confirm
        )
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
