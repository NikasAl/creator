#!/usr/bin/env python3
"""
Редактор изображений через OpenRouter API с использованием google/gemini-2.5-flash-image.
Редактирует изображение, используя второе изображение как шаблон и текстовый промпт.
"""

import argparse
import base64
import io
import os
import time
from pathlib import Path
from typing import Optional, Tuple
import requests
from PIL import Image
from dotenv import load_dotenv


class ImageEditorOpenRouter:
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
        
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.model = os.getenv('IMAGE_EDIT_MODEL', 'google/gemini-2.5-flash-image')
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY не найден в конфигурации")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/bookreader",
            "X-Title": "Image Editor OpenRouter",
        }
        
        print(f"✅ Конфигурация загружена:")
        print(f"   OpenRouter API: {self.base_url}")
        print(f"   Модель: {self.model}")
    
    def encode_image(self, image_path: Path, max_side: int = 2048, quality: int = 95) -> str:
        """Кодирует изображение в base64 data URL"""
        try:
            img = Image.open(image_path)
            
            # Изменяем размер если нужно
            width, height = img.size
            scale = min(1.0, max_side / max(width, height))
            if scale < 1.0:
                img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
            
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Кодируем в base64
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{b64}"
            
        except Exception as e:
            raise Exception(f"Ошибка кодирования изображения {image_path}: {e}")
    
    def edit_image(self, base_image_path: Path, reference_image_path: Optional[Path], 
                   edit_prompt: str, max_retries: int = 3) -> Optional[bytes]:
        """Редактирует изображение через OpenRouter API"""
        
        try:
            # Кодируем базовое изображение
            print(f"🖼️  Кодирование базового изображения: {base_image_path.name}")
            base_image_data = self.encode_image(base_image_path)
            
            # Формируем контент сообщения
            content = [
                {
                    "type": "image_url",
                    "image_url": {"url": base_image_data}
                }
            ]
            
            # Добавляем референсное изображение если есть
            if reference_image_path and reference_image_path.exists():
                print(f"🖼️  Кодирование референсного изображения: {reference_image_path.name}")
                ref_image_data = self.encode_image(reference_image_path)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": ref_image_data}
                })
                # Добавляем текст о референсном изображении
                text_prompt = f"Используй второе изображение как шаблон. {edit_prompt}"
            else:
                text_prompt = edit_prompt
            
            content.append({
                "type": "text",
                "text": text_prompt
            })
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            }
            
            # Некоторые модели поддерживают response_format для изображений
            # Пробуем добавить, если модель это поддерживает
            if "gemini" in self.model.lower() or "flash-image" in self.model.lower():
                payload["response_format"] = {"type": "image"}
            
            print(f"🎨 Отправка запроса на редактирование изображения...")
            print(f"   Модель: {self.model}")
            print(f"   Промпт: {edit_prompt[:100]}...")
            
            # Отправляем запрос с повторными попытками
            for attempt in range(max_retries):
                try:
                    self.stats['api_calls'] += 1
                    response = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=payload,
                        timeout=180
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Извлекаем изображение из ответа
                        # Gemini может вернуть изображение в разных форматах
                        if 'choices' in result and len(result['choices']) > 0:
                            choice = result['choices'][0]
                            if 'message' in choice:
                                message = choice['message']
                                
                                # Проверяем content (может быть строка или массив)
                                if 'content' in message:
                                    content_data = message['content']
                                    
                                    # Если content - строка
                                    if isinstance(content_data, str):
                                        # Может быть base64 строка или data URL
                                        if content_data.startswith('data:image'):
                                            # Извлекаем base64 часть
                                            b64_data = content_data.split(',')[1]
                                            image_bytes = base64.b64decode(b64_data)
                                            print(f"✅ Изображение получено успешно")
                                            self.stats['images_edited'] += 1
                                            return image_bytes
                                        elif len(content_data) > 100:
                                            # Попробуем декодировать как base64
                                            try:
                                                image_bytes = base64.b64decode(content_data)
                                                # Проверяем что это действительно изображение
                                                if len(image_bytes) > 100:
                                                    print(f"✅ Изображение получено успешно")
                                                    self.stats['images_edited'] += 1
                                                    return image_bytes
                                            except:
                                                pass
                                    
                                    # Если content - массив, ищем изображение
                                    if isinstance(content_data, list):
                                        for item in content_data:
                                            if isinstance(item, dict):
                                                # Проверяем image_url
                                                if 'image_url' in item:
                                                    img_url = item['image_url'].get('url', '')
                                                    if img_url.startswith('data:image'):
                                                        b64_data = img_url.split(',')[1]
                                                        image_bytes = base64.b64decode(b64_data)
                                                        print(f"✅ Изображение получено успешно")
                                                        self.stats['images_edited'] += 1
                                                        return image_bytes
                                                # Проверяем прямой base64
                                                if 'image' in item:
                                                    img_b64 = item['image']
                                                    image_bytes = base64.b64decode(img_b64)
                                                    print(f"✅ Изображение получено успешно")
                                                    self.stats['images_edited'] += 1
                                                    return image_bytes
                                
                                # Проверяем альтернативные поля
                                if 'image' in message:
                                    img_data = message['image']
                                    if isinstance(img_data, str):
                                        if img_data.startswith('data:image'):
                                            b64_data = img_data.split(',')[1]
                                            image_bytes = base64.b64decode(b64_data)
                                            print(f"✅ Изображение получено успешно")
                                            self.stats['images_edited'] += 1
                                            return image_bytes
                        
                        # Если не нашли в стандартном формате, выводим отладочную информацию
                        print(f"⚠️  Неожиданный формат ответа")
                        print(f"   Структура ответа: {list(result.keys())}")
                        if 'choices' in result:
                            print(f"   Choices: {str(result['choices'])[:300]}...")
                        
                    elif response.status_code == 429:
                        wait_time = (attempt + 1) * 2
                        print(f"⏳ Rate limit, ожидание {wait_time}с...")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                        print(f"❌ Ошибка API: {error_msg}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        else:
                            raise Exception(error_msg)
                            
                except requests.exceptions.Timeout:
                    print(f"⏰ Таймаут запроса (попытка {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise
                        
                except Exception as e:
                    print(f"❌ Ошибка запроса: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка редактирования изображения: {e}")
            self.stats['errors'] += 1
            return None
    
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
    parser = argparse.ArgumentParser(description="Редактирование изображений через OpenRouter (Gemini)")
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
        editor = ImageEditorOpenRouter(args.config)
        
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

