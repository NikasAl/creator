#!/usr/bin/env python3
"""
Редактор изображений через Alibaba Cloud API с использованием Qwen-Image-Edit.
Редактирует изображение, используя второе изображение как шаблон и текстовый промпт.
"""

import argparse
import base64
import io
import os
import time
from pathlib import Path
from typing import Optional
import requests
from PIL import Image
from dotenv import load_dotenv


class ImageEditorAlibaba:
    def __init__(self, config_file: Optional[str] = None):
        """Инициализация редактора изображений"""
        self.load_config(config_file)
        self.stats = {
            'images_edited': 0,
            'api_calls': 0,
            'errors': 0
        }
    
    def load_config(self, config_file: Optional[str] = None):
        """Загружает конфигурацию из .env файла"""
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            env_files = ['.env', 'config.env', 'settings.env']
            for env_file in env_files:
                if Path(env_file).exists():
                    load_dotenv(env_file)
                    break
        
        self.api_key = os.getenv('ALIBABA_API_KEY')
        self.base_url = os.getenv('ALIBABA_BASE_URL', 'https://dashscope-intl.aliyuncs.com/api/v1')
        self.model = os.getenv('IMAGE_EDIT_MODEL', 'qwen-image-edit-plus')
        
        if not self.api_key:
            raise ValueError("ALIBABA_API_KEY не найден в конфигурации")
        
        print(f"✅ Конфигурация загружена:")
        print(f"   Alibaba API: {self.base_url}")
        print(f"   Модель: {self.model}")
    
    def encode_image_to_base64(self, image_path: Path) -> str:
        """Кодирует изображение в base64"""
        try:
            img = Image.open(image_path)
            
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            return b64
            
        except Exception as e:
            raise Exception(f"Ошибка кодирования изображения {image_path}: {e}")
    
    def create_edit_task(self, base_image_path: Path, reference_image_path: Optional[Path],
                         edit_prompt: str) -> Optional[str]:
        """Создает задачу редактирования изображения через Alibaba Cloud API"""
        
        try:
            # Кодируем базовое изображение
            print(f"🖼️  Кодирование базового изображения: {base_image_path.name}")
            base_image_b64 = self.encode_image_to_base64(base_image_path)
            
            # Формируем сообщения
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": base_image_b64
                        },
                        {
                            "text": edit_prompt
                        }
                    ]
                }
            ]
            
            # Добавляем референсное изображение если есть
            if reference_image_path and reference_image_path.exists():
                print(f"🖼️  Кодирование референсного изображения: {reference_image_path.name}")
                ref_image_b64 = self.encode_image_to_base64(reference_image_path)
                messages[0]["content"].insert(1, {
                    "image": ref_image_b64
                })
                # Обновляем промпт
                messages[0]["content"][-1]["text"] = f"Используй второе изображение как шаблон. {edit_prompt}"
            
            headers = {
                "X-DashScope-Async": "enable",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "input": {
                    "messages": messages
                },
                "parameters": {
                    "n": 1,
                    "watermark": False
                }
            }
            
            print(f"🎨 Отправка запроса на редактирование изображения...")
            print(f"   Модель: {self.model}")
            print(f"   Промпт: {edit_prompt[:100]}...")
            
            response = requests.post(
                f"{self.base_url}/services/aigc/multimodal-generation/generation",
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
    
    def poll_task_result(self, task_id: str, max_wait_time: int = 600) -> Optional[bytes]:
        """Ожидает завершения задачи и возвращает результат"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        start_time = time.time()
        poll_interval = 10
        
        print(f"⏳ Ожидание завершения задачи {task_id}...")
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(
                    f"{self.base_url}/tasks/{task_id}",
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
                    # Извлекаем изображение из результатов
                    results = result["output"].get("results", [])
                    if results and len(results) > 0:
                        result_item = results[0]
                        
                        # Ищем изображение в разных возможных форматах
                        if "image" in result_item:
                            image_b64 = result_item["image"]
                            image_bytes = base64.b64decode(image_b64)
                            print(f"✅ Изображение получено успешно")
                            self.stats['images_edited'] += 1
                            return image_bytes
                        elif "url" in result_item:
                            # Скачиваем по URL
                            image_url = result_item["url"]
                            img_response = requests.get(image_url, timeout=300)
                            if img_response.status_code == 200:
                                print(f"✅ Изображение получено успешно")
                                self.stats['images_edited'] += 1
                                return img_response.content
                            else:
                                print(f"❌ Ошибка скачивания изображения: {img_response.status_code}")
                                return None
                        else:
                            print(f"❌ Неожиданный формат результата: {result_item}")
                            return None
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
    
    def edit_image(self, base_image_path: Path, reference_image_path: Optional[Path],
                   edit_prompt: str) -> Optional[bytes]:
        """Редактирует изображение через Alibaba Cloud API (асинхронно)"""
        
        # Создаем задачу
        task_id = self.create_edit_task(base_image_path, reference_image_path, edit_prompt)
        if not task_id:
            return None
        
        # Ожидаем завершения
        image_bytes = self.poll_task_result(task_id)
        return image_bytes
    
    def edit_and_save(self, base_image_path: Path, output_path: Path,
                     reference_image_path: Optional[Path] = None,
                     edit_prompt: str = "") -> bool:
        """Редактирует изображение и сохраняет результат"""
        
        image_bytes = self.edit_image(base_image_path, reference_image_path, edit_prompt)
        
        if not image_bytes:
            return False
        
        try:
            # Сохраняем изображение
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
            
            print(f"✅ Отредактированное изображение сохранено: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения изображения: {e}")
            self.stats['errors'] += 1
            return False


def main():
    parser = argparse.ArgumentParser(description="Редактирование изображений через Alibaba Cloud (Qwen)")
    parser.add_argument("--pipeline-dir", required=True, help="Каталог пайплайна с images/")
    parser.add_argument("--base-image-index", type=int, required=True, help="Номер базового изображения для редактирования")
    parser.add_argument("--reference-image-index", type=int, help="Номер референсного изображения (опционально)")
    parser.add_argument("--edit-prompt", required=True, help="Промпт с описанием редактирования")
    parser.add_argument("--output-suffix", default="_edited", help="Суффикс для выходного файла")
    parser.add_argument("--config", help="Путь к файлу конфигурации")
    
    args = parser.parse_args()
    
    try:
        pipeline_dir = Path(args.pipeline_dir)
        images_dir = pipeline_dir / "images"
        
        if not images_dir.exists():
            print(f"❌ Каталог images не найден в {pipeline_dir}")
            return 1
        
        # Находим базовое изображение
        base_image_pattern = f"illustration_{args.base_image_index:02d}*.png"
        base_images = list(images_dir.glob(base_image_pattern))
        if not base_images:
            print(f"❌ Изображение с индексом {args.base_image_index} не найдено")
            return 1
        
        base_image_path = base_images[0]  # Берем первое найденное
        
        # Находим референсное изображение если указано
        reference_image_path = None
        if args.reference_image_index is not None:
            ref_image_pattern = f"illustration_{args.reference_image_index:02d}*.png"
            ref_images = list(images_dir.glob(ref_image_pattern))
            if ref_images:
                reference_image_path = ref_images[0]
            else:
                print(f"⚠️  Референсное изображение с индексом {args.reference_image_index} не найдено, продолжаем без него")
        
        # Формируем путь для выходного файла
        base_name = base_image_path.stem
        output_path = images_dir / f"{base_name}{args.output_suffix}.png"
        
        # Создаем редактор
        editor = ImageEditorAlibaba(args.config)
        
        # Редактируем и сохраняем
        success = editor.edit_and_save(
            base_image_path=base_image_path,
            output_path=output_path,
            reference_image_path=reference_image_path,
            edit_prompt=args.edit_prompt
        )
        
        if success:
            print(f"\n🎉 РЕДАКТИРОВАНИЕ ЗАВЕРШЕНО!")
            print(f"📊 Статистика:")
            print(f"   Изображений отредактировано: {editor.stats['images_edited']}")
            print(f"   API вызовов: {editor.stats['api_calls']}")
            print(f"   Ошибок: {editor.stats['errors']}")
            return 0
        else:
            return 1
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

