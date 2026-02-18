#!/usr/bin/env python3
"""
Генератор видеофрагментов через Alibaba Cloud Model Studio WAN API.
Создает анимированные видео из статичных изображений с помощью image-to-video модели.

Использует LLM для генерации промптов на основе текста стихов и описаний иллюстраций.
"""

import argparse
import base64
import json
import os
import time
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv


class AlibabaVideoGenerator:
    def __init__(self, config_file: Optional[str] = None):
        """Инициализация генератора видео"""
        self.load_config(config_file)
        self.stats = {
            'videos_generated': 0,
            'api_calls': 0,
            'total_tokens_used': 0,
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
        self.alibaba_video_model = os.getenv('ALIBABA_VIDEO_MODEL', 'wan2.2-i2v-flash')
        self.alibaba_prompt_model = os.getenv('ALIBABA_PROMPT_MODEL', 'qwen/qwen3-30b-a3b:free')
        
        # Загружаем параметры для LLM промптов
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.openrouter_model = os.getenv('DEFAULT_MODEL', 'anthropic/claude-3.5-sonnet')
        self.openrouter_base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.3'))
        self.max_tokens = int(os.getenv('DEFAULT_MAX_TOKENS', '2000'))
        
        # Проверяем наличие обязательных ключей
        if not self.alibaba_api_key:
            raise ValueError("ALIBABA_API_KEY не найден в конфигурации")
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY не найден в конфигурации")
        
        print(f"✅ Конфигурация загружена:")
        print(f"   Alibaba API: {self.alibaba_base_url}")
        print(f"   Видео модель: {self.alibaba_video_model}")
        print(f"   Промпт модель: {self.alibaba_prompt_model}")
        print(f"   OpenRouter модель: {self.openrouter_model}")
    
    def load_pipeline_data(self, pipeline_dir: Path) -> Tuple[str, Dict, List[Dict]]:
        """Загружает данные пайплайна: текст стихов, иллюстрации и скрипт"""
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
        script = illustrations_data.get('script', [])
        
        print(f"📚 Загружены данные пайплайна:")
        print(f"   Текст стихов: {len(song_text)} символов")
        print(f"   Иллюстраций: {len(illustrations)}")
        print(f"   Скрипт: {len(script)} частей")
        
        return song_text, illustrations, script
    
    def generate_video_prompt(self, image_index: int, song_text: str, 
                            illustrations: List[Dict], script: List[Dict]) -> str:
        """Генерирует промпт для создания видео на основе LLM"""
        
        # Находим соответствующую иллюстрацию и скрипт
        illustration = None
        script_part = None
        
        for ill in illustrations:
            if ill.get('index') == image_index:
                illustration = ill
                break
        
        for part in script:
            if part.get('title') == illustration.get('title'):
                script_part = part
                break
        
        if not illustration:
            raise ValueError(f"Иллюстрация с индексом {image_index} не найдена")
        
        # Создаем промпт для LLM
        llm_prompt = f"""Ты эксперт по созданию промптов для генерации видео из изображений. 

ТЕКСТ СТИХОВ:
{song_text}

ОПИСАНИЕ ИЛЛЮСТРАЦИИ:
Название: {illustration.get('title', '')}
Описание: {illustration.get('summary', '')}
Полный промпт: {illustration.get('prompt', '')}

СКРИПТ:
{script_part.get('summary', '') if script_part else ''}

Создай краткий промпт для генерации видео (image-to-video) на основе этой иллюстрации. 
Промпт должен описывать:
1. Какое движение или анимацию нужно добавить к изображению
2. Как должна двигаться камера (zoom, pan, etc.)
3. Какие элементы должны анимироваться
4. Общую атмосферу и настроение

Промпт должен быть на русском языке, кратким (1-2 предложения) и конкретным.
Примеры хороших промптов:
- "Камера медленно приближается к окну, показывая, как снежинки танцуют в свете свечи"
- "Ветер колышет занавески, а тени от свечи создают таинственные узоры на стенах"
- "Буря за окном усиливается, молнии освещают лицо старушки, сидящей у окна"

ПРОМПТ ДЛЯ ВИДЕО:"""

        # Вызываем LLM для генерации промпта
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.openrouter_model,
            "messages": [
                {
                    "role": "user",
                    "content": llm_prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            self.stats['api_calls'] += 1
            response = requests.post(
                f"{self.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                video_prompt = result['choices'][0]['message']['content'].strip()
                
                # Обновляем статистику токенов
                if 'usage' in result:
                    self.stats['total_tokens_used'] += result['usage'].get('total_tokens', 0)
                
                print(f"✅ Промпт для видео сгенерирован:")
                print(f"   {video_prompt}")
                
                return video_prompt
            else:
                raise Exception(f"Ошибка LLM API: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка генерации промпта: {e}")
            # Возвращаем базовый промпт
            return f"Камера медленно движется, показывая детали изображения в атмосфере стихотворения"
    
    def encode_image_to_base64(self, image_path: Path) -> str:
        """Кодирует изображение в base64 с правильным MIME типом"""
        try:
            # Определяем MIME тип
            mime_type, _ = mimetypes.guess_type(str(image_path))
            if not mime_type or not mime_type.startswith("image/"):
                raise ValueError(f"Неподдерживаемый формат изображения: {image_path}")
            
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_string = base64.b64encode(image_data).decode('utf-8')
                return f"data:{mime_type};base64,{base64_string}"
        except Exception as e:
            raise Exception(f"Ошибка кодирования изображения {image_path}: {e}")
    
    def create_video_task(self, image_path: Path, video_prompt: str, 
                         duration: int = 5, resolution: str = "720P") -> Optional[str]:
        """Создает задачу генерации видео через Alibaba Cloud API"""
        
        try:
            # Кодируем изображение
            print(f"🖼️  Кодирование изображения: {image_path.name}")
            image_b64 = self.encode_image_to_base64(image_path)
            
            # Подготавливаем параметры запроса
            headers = {
                "X-DashScope-Async": "enable",
                "Authorization": f"Bearer {self.alibaba_api_key}",
                "Content-Type": "application/json"
            }
            
            # Определяем параметры в зависимости от модели
            parameters = {
                "resolution": resolution,
                "prompt_extend": True,
                "watermark": False
            }
            
            # Добавляем длительность только для поддерживаемых моделей
            if self.alibaba_video_model in ["wan2.5-i2v-preview", "wan2.1-i2v-turbo"]:
                parameters["duration"] = duration
            
            payload = {
                "model": self.alibaba_video_model,
                "input": {
                    "prompt": video_prompt,
                    "img_url": image_b64
                },
                "parameters": parameters
            }
            
            print(f"🎬 Отправка запроса на генерацию видео...")
            print(f"   Модель: {self.alibaba_video_model}")
            print(f"   Длительность: {duration}с")
            print(f"   Разрешение: {resolution}")
            print(f"   Промпт: {video_prompt}")
            
            # Отправляем запрос на создание задачи
            response = requests.post(
                f"{self.alibaba_base_url}/services/aigc/video-generation/video-synthesis",
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
    
    def poll_task_result(self, task_id: str, max_wait_time: int = 600) -> Optional[str]:
        """Ожидает завершения задачи и возвращает URL видео"""
        
        headers = {
            "Authorization": f"Bearer {self.alibaba_api_key}"
        }
        
        start_time = time.time()
        poll_interval = 15  # Интервал опроса в секундах
        
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
                    video_url = result["output"].get("video_url")
                    if video_url:
                        print(f"✅ Видео готово: {video_url}")
                        return video_url
                    else:
                        print("❌ URL видео не найден в ответе")
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
    
    def generate_video(self, image_path: Path, video_prompt: str, 
                      duration: int = 5, resolution: str = "720P") -> Optional[str]:
        """Генерирует видео через Alibaba Cloud API (асинхронно)"""
        
        # Создаем задачу
        task_id = self.create_video_task(image_path, video_prompt, duration, resolution)
        if not task_id:
            return None
        
        # Ожидаем завершения
        video_url = self.poll_task_result(task_id)
        return video_url
    
    def download_video(self, video_url: str, output_path: Path) -> bool:
        """Скачивает видео по URL"""
        try:
            print(f"📥 Скачивание видео: {video_url}")
            
            response = requests.get(video_url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Видео сохранено: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка скачивания видео: {e}")
            self.stats['errors'] += 1
            return False
    
    def generate_video_for_image(self, pipeline_dir: Path, image_index: int,
                               duration: int = 5, resolution: str = "720P",
                               confirm: bool = True) -> bool:
        """Генерирует видео для конкретного изображения"""
        
        pipeline_dir = Path(pipeline_dir)
        images_dir = pipeline_dir / "images"
        
        if not images_dir.exists():
            raise FileNotFoundError(f"Каталог images не найден в {pipeline_dir}")
        
        # Находим изображение
        image_file = images_dir / f"illustration_{image_index:02d}.png"
        if not image_file.exists():
            raise FileNotFoundError(f"Изображение {image_file} не найдено")
        
        # Загружаем данные пайплайна
        song_text, illustrations, script = self.load_pipeline_data(pipeline_dir)
        
        # Генерируем промпт для видео
        video_prompt = self.generate_video_prompt(image_index, song_text, illustrations, script)
        
        # Показываем детали генерации
        print(f"\n🎬 ДЕТАЛИ ГЕНЕРАЦИИ ВИДЕО:")
        print(f"=" * 50)
        print(f"📁 Пайплайн: {pipeline_dir}")
        print(f"🖼️  Изображение: {image_file.name}")
        print(f"📝 Промпт: {video_prompt}")
        print(f"⏱️  Длительность: {duration} секунд")
        print(f"📐 Разрешение: {resolution}")
        print(f"💰 Модель: {self.alibaba_video_model}")
        print(f"=" * 50)
        
        # Запрашиваем подтверждение
        if confirm:
            user_input = input("\n❓ Продолжить генерацию видео? (y/N): ").strip().lower()
            if user_input != 'y':
                print("❌ Генерация отменена пользователем")
                return False
        
        # Генерируем видео
        video_url = self.generate_video(image_file, video_prompt, duration, resolution)
        if not video_url:
            return False
        
        # Скачиваем видео
        output_path = images_dir / f"video_{image_index:02d}.mp4"
        success = self.download_video(video_url, output_path)
        
        if success:
            self.stats['videos_generated'] += 1
            print(f"\n🎉 ВИДЕО УСПЕШНО СОЗДАНО!")
            print(f"📁 Путь: {output_path}")
            print(f"📊 Статистика:")
            print(f"   Видео создано: {self.stats['videos_generated']}")
            print(f"   API вызовов: {self.stats['api_calls']}")
            print(f"   Токенов использовано: {self.stats['total_tokens_used']}")
            print(f"   Ошибок: {self.stats['errors']}")
        
        return success


def main():
    parser = argparse.ArgumentParser(description="Генерация видеофрагментов через Alibaba Cloud Model Studio")
    parser.add_argument("--pipeline-dir", required=True, help="Каталог пайплайна с images/ и song.txt")
    parser.add_argument("--image-index", type=int, required=True, help="Номер изображения для генерации видео")
    parser.add_argument("--duration", type=int, default=5, help="Длительность видео в секундах (3-10)")
    parser.add_argument("--resolution", default="720P", choices=["480P", "720P", "1080P"], help="Разрешение видео")
    parser.add_argument("--no-confirm", action="store_true", help="Не запрашивать подтверждение")
    parser.add_argument("--config", help="Путь к файлу конфигурации")
    
    args = parser.parse_args()
    
    try:
        # Создаем генератор
        generator = AlibabaVideoGenerator(args.config)
        
        # Генерируем видео
        success = generator.generate_video_for_image(
            pipeline_dir=args.pipeline_dir,
            image_index=args.image_index,
            duration=args.duration,
            resolution=args.resolution,
            confirm=not args.no_confirm
        )
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
