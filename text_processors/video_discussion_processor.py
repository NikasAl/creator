#!/usr/bin/env python3
"""
Video discussion processor for creating summaries or discussions from segmented text.
Supports two modes: summary and discussion analysis.
"""

import os
import json
import time
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv


class VideoDiscussionProcessor:
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize video discussion processor
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.load_config()
        
        # Statistics
        self.stats = {
            'api_calls': 0,
            'total_tokens_used': 0,
            'segments_processed': 0
        }
    
    def load_config(self):
        """Load configuration from environment or config file"""
        try:
            if self.config_file:
                load_dotenv(self.config_file)
            else:
                load_dotenv()
        except ImportError:
            pass
        
        # API configuration
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        
        # Model configuration
        self.model = os.getenv('DEFAULT_MODEL', 'anthropic/claude-3.5-sonnet')
        self.budget_model = os.getenv('BUDGET_MODEL', 'meta-llama/llama-3.1-8b-instruct')
        self.quality_model = os.getenv('QUALITY_MODEL', 'openai/gpt-4o')
        
        # Processing parameters
        self.temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.3'))
        self.max_tokens = int(os.getenv('DEFAULT_MAX_TOKENS', '4000'))
        
        # Headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/bookreader",
            "X-Title": "Video Discussion Processor"
        }
    
    def _call_llm(self, prompt: str, system: Optional[str] = None, 
                  model: Optional[str] = None, retry_count: int = 3) -> Optional[str]:
        """
        Call LLM API with retry logic
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            model: Model to use (optional)
            retry_count: Number of retry attempts
            
        Returns:
            LLM response or None
        """
        payload = {
            "model": model or self.model,
            "messages": [],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        if system:
            payload["messages"].append({"role": "system", "content": system})
        payload["messages"].append({"role": "user", "content": prompt})
        
        for attempt in range(retry_count):
            try:
                self.stats["api_calls"] += 1
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=120
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    
                    # Update token usage statistics
                    if "usage" in data:
                        self.stats["total_tokens_used"] += data["usage"].get("total_tokens", 0)
                    
                    return content
                elif response.status_code == 429:
                    wait_time = 2 ** (attempt + 1)
                    print(f"⏳ Rate limit, ожидание {wait_time} секунд...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Ошибка API (попытка {attempt + 1}): {response.status_code}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)
                        
            except Exception as e:
                print(f"❌ Ошибка запроса (попытка {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def create_summary_prompt(self, segment: Dict[str, Any], segment_index: int, 
                            total_segments: int, title: str = "", author: str = "") -> str:
        """
        Create prompt for summary mode
        
        Args:
            segment: Segment data
            segment_index: Current segment index
            total_segments: Total number of segments
            title: Video title
            author: Video author
            
        Returns:
            Formatted prompt
        """
        context_info = ""
        if title:
            context_info += f"Название видео: {title}\n"
        if author:
            context_info += f"Автор: {author}\n"
        
        return f"""Ты — эксперт по созданию кратких и информативных пересказов.

ЗАДАЧА: Создай краткий пересказ предоставленного фрагмента текста.

КОНТЕКСТ:
{context_info}Фрагмент {segment_index} из {total_segments}

ТРЕБОВАНИЯ К ПЕРЕСКАЗУ:
- Сохрани все ключевые идеи и факты
- Используй простой и понятный язык
- Структурируй информацию логично
- Выдели главные моменты
- Длина: 2-4 абзаца
- Сохрани хронологию событий, если она важна

ФРАГМЕНТ ДЛЯ ПЕРЕСКАЗА:
**{segment.get('title', f'Фрагмент {segment_index}')}**

{segment.get('content', '')}

ПЕРЕСКАЗ:"""
    
    def create_discussion_prompt(self, segment: Dict[str, Any], segment_index: int, 
                               total_segments: int, title: str = "", author: str = "") -> str:
        """
        Create prompt for discussion mode
        
        Args:
            segment: Segment data
            segment_index: Current segment index
            total_segments: Total number of segments
            title: Video title
            author: Video author
            
        Returns:
            Formatted prompt
        """
        context_info = ""
        if title:
            context_info += f"Название видео: {title}\n"
        if author:
            context_info += f"Автор: {author}\n"
        
        return f"""Ты — эксперт по анализу контента и критическому мышлению.

ЗАДАЧА: Проанализируй предоставленный фрагмент и создай обсуждение с разными точками зрения.

КОНТЕКСТ:
{context_info}Фрагмент {segment_index} из {total_segments}

ТРЕБОВАНИЯ К ОБСУЖДЕНИЮ:
- Выдели основные тезисы и аргументы
- Рассмотри разные точки зрения на проблему
- Проанализируй логику и обоснованность утверждений
- Выскажи свое мнение как эксперта
- Укажи на сильные и слабые стороны аргументации
- Предложи альтернативные взгляды, если применимо
- Длина: 3-5 абзацев

ФРАГМЕНТ ДЛЯ АНАЛИЗА:
**{segment.get('title', f'Фрагмент {segment_index}')}**

{segment.get('content', '')}

АНАЛИЗ И ОБСУЖДЕНИЕ:"""
    
    def process_segment(self, segment: Dict[str, Any], mode: str, segment_index: int, 
                       total_segments: int, title: str = "", author: str = "", 
                       model_choice: str = "default") -> Optional[str]:
        """
        Process a single segment
        
        Args:
            segment: Segment data
            mode: Processing mode (summary/discussion)
            segment_index: Current segment index
            total_segments: Total number of segments
            title: Video title
            author: Video author
            model_choice: Model choice
            
        Returns:
            Processed text or None
        """
        # Select model
        model = self.model
        if model_choice == "budget":
            model = self.budget_model
        elif model_choice == "quality":
            model = self.quality_model
        
        # Create appropriate prompt
        if mode == "summary":
            prompt = self.create_summary_prompt(segment, segment_index, total_segments, title, author)
        elif mode == "discussion":
            prompt = self.create_discussion_prompt(segment, segment_index, total_segments, title, author)
        else:
            print(f"❌ Неизвестный режим: {mode}")
            return None
        
        # Call LLM
        response = self._call_llm(prompt, model=model)
        if response:
            self.stats["segments_processed"] += 1
        
        return response
    
    def process_segments(self, segments_file: str, mode: str, title: str = "", 
                       author: str = "", model_choice: str = "default") -> Optional[str]:
        """
        Process all segments and create final text
        
        Args:
            segments_file: Path to segments JSON file
            mode: Processing mode (summary/discussion)
            title: Video title
            author: Video author
            model_choice: Model choice
            
        Returns:
            Final processed text or None
        """
        try:
            # Load segments
            segments_path = Path(segments_file)
            if not segments_path.exists():
                print(f"❌ Файл сегментов не найден: {segments_path}")
                return None
            
            with open(segments_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            segments = data.get("segments", [])
            if not segments:
                print("❌ Сегменты не найдены в файле")
                return None
            
            print(f"📄 Обрабатываем {len(segments)} сегментов в режиме '{mode}'...")
            
            # Process each segment
            processed_parts = []
            for i, segment in enumerate(segments, 1):
                print(f"🔄 Обрабатываем сегмент {i}/{len(segments)}: {segment.get('title', f'Фрагмент {i}')}")
                
                processed_text = self.process_segment(
                    segment, mode, i, len(segments), title, author, model_choice
                )
                
                if processed_text:
                    # Add segment header
                    segment_title = segment.get('title', f'Фрагмент {i}')
                    processed_parts.append(f"## {segment_title}\n\n{processed_text}\n")
                else:
                    print(f"⚠️ Не удалось обработать сегмент {i}")
                    processed_parts.append(f"## {segment.get('title', f'Фрагмент {i}')}\n\n*[Ошибка обработки]*\n")
                
                # Small delay between requests
                if i < len(segments):
                    time.sleep(1)
            
            # Combine all parts
            final_text = self._create_final_text(processed_parts, mode, title, author)
            return final_text
            
        except Exception as e:
            print(f"❌ Ошибка обработки сегментов: {e}")
            return None
    
    def _create_final_text(self, processed_parts: List[str], mode: str, 
                          title: str = "", author: str = "") -> str:
        """
        Create final text with header and footer
        
        Args:
            processed_parts: List of processed segment texts
            mode: Processing mode
            title: Video title
            author: Video author
            
        Returns:
            Final formatted text
        """
        # Create header
        header_parts = []
        if title:
            header_parts.append(f"# {title}")
        if author:
            header_parts.append(f"**Автор:** {author}")
        
        mode_title = "Пересказ" if mode == "summary" else "Обсуждение"
        header_parts.append(f"**Режим:** {mode_title}")
        header_parts.append(f"**Дата создания:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        header = "\n".join(header_parts) + "\n\n---\n\n"
        
        # Add placeholder for timestamps
        timestamps_placeholder = "[content]\n\n"
        
        # Create footer
        footer = f"\n\n---\n\n*{mode_title} создан автоматически с помощью Video Discussion Processor*"
        
        # Combine everything
        return header + timestamps_placeholder + "\n".join(processed_parts) + footer
    
    def save_discussion(self, text: str, output_file: str) -> bool:
        """
        Save discussion text to file
        
        Args:
            text: Discussion text
            output_file: Output file path
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            print(f"✅ Обсуждение сохранено: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения обсуждения: {e}")
            return False
    
    def process_pipeline(self, segments_file: str, output_file: str, mode: str,
                        title: str = "", author: str = "", model_choice: str = "default") -> bool:
        """
        Complete processing pipeline
        
        Args:
            segments_file: Path to segments JSON file
            output_file: Output text file
            mode: Processing mode (summary/discussion)
            title: Video title
            author: Video author
            model_choice: Model choice
            
        Returns:
            True if successful
        """
        # Process segments
        final_text = self.process_segments(segments_file, mode, title, author, model_choice)
        if not final_text:
            return False
        
        # Save result
        success = self.save_discussion(final_text, output_file)
        if success:
            print(f"📊 Статистика:")
            print(f"   - Обработано сегментов: {self.stats['segments_processed']}")
            print(f"   - API вызовов: {self.stats['api_calls']}")
            print(f"   - Токенов использовано: {self.stats['total_tokens_used']}")
        
        return success


def main():
    parser = argparse.ArgumentParser(description="Создание пересказа или обсуждения из сегментированного текста")
    parser.add_argument('segments_file', help='JSON файл с сегментами')
    parser.add_argument('--output', '-o', required=True, help='Выходной текстовый файл')
    parser.add_argument('--mode', choices=['summary', 'discussion'], required=True, 
                       help='Режим обработки')
    parser.add_argument('--title', help='Название видео')
    parser.add_argument('--author', help='Автор видео')
    parser.add_argument('--config', help='Файл конфигурации')
    parser.add_argument('--model', choices=['default', 'budget', 'quality'], 
                       default='default', help='Выбор модели')
    
    args = parser.parse_args()
    
    processor = VideoDiscussionProcessor(args.config)
    
    success = processor.process_pipeline(
        args.segments_file,
        args.output,
        args.mode,
        args.title or "",
        args.author or "",
        args.model
    )
    
    if success:
        print("✅ Обработка завершена успешно")
        return 0
    else:
        print("❌ Обработка не удалась")
        return 1


if __name__ == "__main__":
    exit(main())
