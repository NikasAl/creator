#!/usr/bin/env python3
"""
Vision OCR processor: recognizes text from PDF pages using a vision-capable LLM via OpenRouter.

- Renders PDF pages to images (png) using pdfplumber and Pillow
- Sends images to a configurable vision model
- Includes retry logic and detailed logging
"""

import os
import io
import base64
import time
from pathlib import Path
from typing import Optional, Tuple, List

import pdfplumber
from PIL import Image
import requests
from dotenv import load_dotenv


class VisionOCRProcessor:
    def __init__(self, config_file: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None):
        self._load_config(config_file)
        self.model = model or os.getenv("VISION_MODEL", os.getenv("QUALITY_MODEL", os.getenv("DEFAULT_MODEL", "openai/gpt-4o")))
        self.temperature = float(temperature if temperature is not None else os.getenv("DEFAULT_TEMPERATURE", "0.2"))
        self.max_tokens = int(max_tokens if max_tokens is not None else os.getenv("DEFAULT_MAX_TOKENS", "1200"))
        
        # Retry configuration
        self.max_retries = int(os.getenv("OCR_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("OCR_RETRY_DELAY", "2.0"))

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/bookreader",
            "X-Title": "Vision OCR Processor",
        }
        
        # Statistics
        self.stats = {
            'pages_processed': 0,
            'pages_successful': 0,
            'pages_failed': 0,
            'total_retries': 0,
            'total_api_calls': 0,
            'total_processing_time': 0.0
        }
        
        print(f"🔍 VisionOCRProcessor initialized:")
        print(f"   Model: {self.model}")
        print(f"   Max retries: {self.max_retries}")
        print(f"   Retry delay: {self.retry_delay}s")

    def _load_config(self, config_file: Optional[str]):
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            for env_name in [".env", "config.env", "settings.env"]:
                if Path(env_name).exists():
                    load_dotenv(env_name)
                    break
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for VisionOCRProcessor")

    def _encode_image(self, image: Image.Image, max_side: int = 1600, quality: int = 92) -> str:
        # Resize preserving aspect ratio to avoid huge payloads
        width, height = image.size
        scale = min(1.0, max_side / max(width, height))
        if scale < 1.0:
            image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    def _vision_request(self, image_data_url: str, page_num: int) -> Optional[str]:
        """Make vision request with retry logic and detailed logging"""
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an accurate OCR assistant. Read the page image and output clean Russian text exactly as printed. Preserve paragraphs. Do not add commentary.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Распознай текст на изображении страницы. Верни только текст без комментариев."},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                },
            ],
        }
        
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                print(f"   📡 OCR запрос для страницы {page_num} (попытка {attempt + 1}/{self.max_retries + 1})")
                start_time = time.time()
                
                resp = requests.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=120)
                self.stats['total_api_calls'] += 1
                
                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        text = data["choices"][0]["message"]["content"].strip()
                        processing_time = time.time() - start_time
                        self.stats['total_processing_time'] += processing_time
                        
                        if text:
                            print(f"   ✅ Страница {page_num}: распознано {len(text)} символов за {processing_time:.1f}s")
                            return text
                        else:
                            print(f"   ⚠️  Страница {page_num}: пустой ответ от модели")
                            last_error = "Empty response from model"
                    except (KeyError, IndexError) as e:
                        print(f"   ❌ Страница {page_num}: ошибка парсинга ответа: {e}")
                        last_error = f"Response parsing error: {e}"
                else:
                    error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    print(f"   ❌ Страница {page_num}: HTTP ошибка {resp.status_code}")
                    last_error = error_msg
                    
            except requests.exceptions.Timeout:
                print(f"   ⏰ Страница {page_num}: таймаут запроса (попытка {attempt + 1})")
                last_error = "Request timeout"
            except requests.exceptions.RequestException as e:
                print(f"   🌐 Страница {page_num}: ошибка сети: {e}")
                last_error = f"Network error: {e}"
            except Exception as e:
                print(f"   💥 Страница {page_num}: неожиданная ошибка: {e}")
                last_error = f"Unexpected error: {e}"
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries:
                print(f"   ⏳ Ожидание {self.retry_delay}s перед повтором...")
                time.sleep(self.retry_delay)
                self.stats['total_retries'] += 1
        
        print(f"   ❌ Страница {page_num}: все попытки исчерпаны. Последняя ошибка: {last_error}")
        return None

    def ocr_pdf_page(self, pdf: pdfplumber.PDF, page_index_zero_based: int) -> Optional[str]:
        """OCR a single PDF page with detailed logging"""
        page_num = page_index_zero_based + 1
        self.stats['pages_processed'] += 1
        
        try:
            page = pdf.pages[page_index_zero_based]
            print(f"🖼️  Обработка страницы {page_num}...")
            
            # Render page to raster image
            try:
                im = page.to_image(resolution=220).original
            except Exception as e:
                print(f"   ⚠️  Страница {page_num}: ошибка рендеринга с высоким разрешением: {e}")
                try:
                    im = page.to_image(resolution=200).original
                except Exception as e2:
                    print(f"   ❌ Страница {page_num}: критическая ошибка рендеринга: {e2}")
                    self.stats['pages_failed'] += 1
                    return None
            
            # Encode image
            try:
                image_data_url = self._encode_image(im)
                print(f"   📷 Страница {page_num}: изображение закодировано ({len(image_data_url)} символов)")
            except Exception as e:
                print(f"   ❌ Страница {page_num}: ошибка кодирования изображения: {e}")
                self.stats['pages_failed'] += 1
                return None
            
            # Make vision request
            text = self._vision_request(image_data_url, page_num)
            
            if text:
                # Normalize whitespace
                text = text.replace('\r', '').strip()
                self.stats['pages_successful'] += 1
                return text
            else:
                self.stats['pages_failed'] += 1
                return None
                
        except Exception as e:
            print(f"   💥 Страница {page_num}: критическая ошибка: {e}")
            self.stats['pages_failed'] += 1
            return None

    def ocr_pdf_range(self, pdf_path: str, start_page: int, end_page: int) -> List[Tuple[int, str]]:
        """OCR a range of PDF pages with progress tracking"""
        results: List[Tuple[int, str]] = []
        print(f"🔍 Начинаем OCR для диапазона страниц {start_page}-{end_page}")
        
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            start_idx = max(0, start_page - 1)
            end_idx = min(total, end_page if end_page is not None else total)
            
            print(f"📊 Всего страниц в PDF: {total}, обрабатываем: {start_idx + 1}-{end_idx}")
            
            for i in range(start_idx, end_idx):
                page_num = i + 1
                print(f"\n📄 Прогресс: {page_num - start_idx}/{end_idx - start_idx} (страница {page_num})")
                
                text = self.ocr_pdf_page(pdf, i)
                if text:
                    results.append((page_num, text))
                    print(f"✅ Страница {page_num} добавлена в результаты")
                else:
                    print(f"❌ Страница {page_num} пропущена")
        
        # Print final statistics
        self.print_statistics()
        return results
    
    def print_statistics(self):
        """Print OCR processing statistics"""
        print(f"\n📊 Статистика OCR:")
        print(f"   Обработано страниц: {self.stats['pages_processed']}")
        print(f"   Успешно: {self.stats['pages_successful']}")
        print(f"   Неудачно: {self.stats['pages_failed']}")
        print(f"   Всего API вызовов: {self.stats['total_api_calls']}")
        print(f"   Всего повторов: {self.stats['total_retries']}")
        print(f"   Общее время: {self.stats['total_processing_time']:.1f}s")
        
        if self.stats['pages_processed'] > 0:
            success_rate = (self.stats['pages_successful'] / self.stats['pages_processed']) * 100
            print(f"   Процент успеха: {success_rate:.1f}%")


