#!/usr/bin/env python3
"""
Процессор для создания статей для соцсетей на основе текстов чата

Функции:
- Парсит файл чата с форматом ### USER / ### ASSISTANT
- Загружает дополнительные инструкции пользователя
- Генерирует познавательную статью для Pikabu/Dzen/VK
- Использует LLM через OpenRouter API
"""

import os
import sys
import argparse
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv

# Импортируем парсер для работы с JSON чатами
try:
    from chat_processors.chat_json_parser import ChatJsonParser
except ImportError:
    # Если импорт не удался (возможно, мы внутри модуля)
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from chat_processors.chat_json_parser import ChatJsonParser


class ChatArticleProcessor:
    def __init__(self, config_file: str = None):
        self.load_config(config_file)
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/chat-article-processor",
            "X-Title": "Chat Article Processor"
        }

    def load_config(self, config_file: str = None):
        """Загружает конфигурацию из файла окружения"""
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            for env_file in [".env", "config.env", "settings.env"]:
                if Path(env_file).exists():
                    load_dotenv(env_file)
                    break

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("DEFAULT_MODEL", "deepseek/deepseek-v3.2-exp")
        self.temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "4000"))
        self.budget_model = os.getenv("BUDGET_MODEL", "google/gemini-2.5-flash-lite-preview-09-2025")
        self.quality_model = os.getenv("QUALITY_MODEL", "deepseek/deepseek-v3.2-exp")
        self.max_context_chars = int(os.getenv("CHAT_MAX_CONTEXT_CHARS", "30000"))

    def parse_chat_file(self, chat_path: Path) -> List[Dict]:
        """Парсит файл чата с разделителями ### USER и ### ASSISTANT"""
        if not chat_path.exists():
            raise FileNotFoundError(f"Файл чата не найден: {chat_path}")

        try:
            content = chat_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ValueError(f"Ошибка чтения файла чата: {e}")

        messages = []
        current_message = None
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('### USER'):
                if current_message:
                    messages.append(current_message)
                current_message = {
                    'role': 'user',
                    'content': ''
                }
            elif line.startswith('### ASSISTANT'):
                if current_message:
                    messages.append(current_message)
                current_message = {
                    'role': 'assistant',
                    'content': ''
                }
            elif current_message and line:
                if current_message['content']:
                    current_message['content'] += '\n' + line
                else:
                    current_message['content'] = line

        if current_message:
            messages.append(current_message)

        # Фильтруем пустые сообщения
        messages = [msg for msg in messages if msg['content'].strip()]
        
        return messages

    def load_instructions(self, instructions_path: Optional[Path]) -> str:
        """Загружает дополнительные инструкции из текстового файла"""
        if not instructions_path or not instructions_path.exists():
            return ""

        try:
            return instructions_path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception as e:
            print(f"⚠️ Ошибка чтения файла инструкций: {e}")
            return ""

    def build_chat_context(self, messages: List[Dict]) -> str:
        """Строит контекст из сообщений чата с учетом лимита символов"""
        context_parts = []
        total_chars = 0
        
        # Берем последние сообщения (актуальная дискуссия)
        for message in reversed(messages):
            role_label = "Пользователь" if message['role'] == 'user' else "Ассистент"
            message_text = f"{role_label}: {message['content']}\n\n"
            
            if total_chars + len(message_text) > self.max_context_chars:
                break
                
            context_parts.insert(0, message_text)
            total_chars += len(message_text)

        return "".join(context_parts).strip()

    def create_article_prompt(self, messages: List[Dict], instructions: str) -> str:
        """Создает промпт для генерации статьи"""
        chat_context = self.build_chat_context(messages)
        
        instructions_section = ""
        if instructions:
            instructions_section = f"""
ДОПОЛНИТЕЛЬНЫЕ ИНСТРУКЦИИ ПОЛЬЗОВАТЕЛЯ:
{instructions}

"""

        return f"""Ты — опытный автор познавательных статей для социальных сетей (Pikabu, Dzen, VK). Напиши интересную и полезную статью на основе обсуждения в чате.

ТРЕБОВАНИЯ К СТАТЬЕ:
- Формат: заголовок + текст статьи (с markdown разметкой)
- Стиль: познавательный, популярный или технический (в зависимости от темы)
- Объем: около 1500-2500 слов
- Структура:
  * Привлекательный заголовок
  * Краткое введение с контекстом
  * Основная часть с примерами и объяснениями
  * Практические советы или выводы
- Обязательные элементы:
  * Примеры кода (если применимо)
  * Формулы или цитаты (если применимо)
  * Практическая ценность для читателя
  * Понятные объяснения сложных концепций

{instructions_section}КОНТЕКСТ ЧАТА:
{chat_context}

СТАТЬЯ:
""".strip()

    def generate_article(self, prompt: str, model_choice: str = "default") -> Optional[Tuple[str, str]]:
        """Генерирует статью через OpenRouter API"""
        model = self.model
        if model_choice == "budget":
            model = self.budget_model
        elif model_choice == "quality":
            model = self.quality_model

        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=180
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    
                    # Парсим заголовок и текст статьи
                    return self.parse_article_response(content)
                else:
                    print(f"Ошибка API (попытка {attempt + 1}): {resp.status_code}")
                    if resp.status_code == 429:
                        time.sleep(2 ** (attempt + 1))
                    elif attempt < 2:
                        time.sleep(2 ** attempt)
                        
            except Exception as e:
                print(f"Ошибка запроса (попытка {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    
        return None

    def parse_article_response(self, content: str) -> Tuple[str, str]:
        """Парсит ответ LLM и извлекает заголовок и текст статьи"""
        lines = content.split('\n')
        
        # Ищем заголовок (первая непустая строка или строка с ===)
        title = ""
        content_start = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Если строка содержит только символы =, это разделитель заголовка
            if re.match(r'^=+$', line):
                if i > 0:
                    title = lines[i-1].strip()
                    content_start = i + 1
                break
            elif not title and line:
                # Первая непустая строка - заголовок
                title = line
                content_start = i + 1
                break
        
        # Если заголовок не найден, используем первую строку
        if not title:
            title = lines[0].strip() if lines else "Статья"
            content_start = 1
        
        # Объединяем оставшиеся строки в текст статьи
        article_content = '\n'.join(lines[content_start:]).strip()
        
        return title, article_content

    def process_json_chat(
        self,
        json_path: str,
        chat_id: str,
        output_file: Optional[str],
        instructions_file: Optional[str],
        model_choice: str
    ) -> Tuple[bool, Optional[Path]]:
        """
        Обрабатывает чат из JSON экспорта
        
        Args:
            json_path: Путь к JSON файлу с экспортом
            chat_id: ID чата в экспорте
            output_file: Путь для сохранения статьи
            instructions_file: Путь к файлу с инструкциями
            model_choice: Выбор модели (default/budget/quality)
            
        Returns:
            Кортеж (успех, путь к выходному файлу)
        """
        json_file = Path(json_path)
        if not json_file.exists():
            print(f"❌ JSON файл не найден: {json_file}")
            return False, None
        
        try:
            # Используем парсер для извлечения и конвертации чата
            parser = ChatJsonParser()
            chats = parser.parse_export_file(json_file)
            
            # Ищем нужный чат
            chat_data = None
            for chat in chats:
                if chat.get('id') == chat_id:
                    chat_data = chat
                    break
            
            if not chat_data:
                print(f"❌ Чат с ID {chat_id} не найден в экспорте")
                return False, None
            
            # Конвертируем чат в текстовый формат во временный файл
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            temp_path = Path(temp_file.name)
            
            text_content = parser.convert_to_text_format(parser.extract_chat_tree(chat_data))
            temp_path.write_text(text_content, encoding='utf-8')
            temp_file.close()
            
            try:
                # Используем стандартную обработку
                result = self.process_chat(str(temp_path), output_file, instructions_file, model_choice)
                return result
            finally:
                # Удаляем временный файл
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            print(f"❌ Ошибка обработки JSON чата: {e}")
            return False, None
    
    def process_chat(self, chat_path: str, output_file: Optional[str], 
                    instructions_file: Optional[str], model_choice: str) -> Tuple[bool, Optional[Path]]:
        """Главный метод обработки чата"""
        chat_file = Path(chat_path)
        instructions_path = Path(instructions_file) if instructions_file else None
        
        # Парсим чат
        try:
            messages = self.parse_chat_file(chat_file)
            print(f"📱 Найдено сообщений в чате: {len(messages)}")
        except Exception as e:
            print(f"❌ Ошибка парсинга чата: {e}")
            return False, None

        # Загружаем инструкции
        instructions = self.load_instructions(instructions_path)
        if instructions:
            print(f"📋 Загружены инструкции: {len(instructions)} символов")

        # Создаем промпт и генерируем статью
        prompt = self.create_article_prompt(messages, instructions)
        print(f"📊 Размер промпта: {len(prompt)} символов")
        
        result = self.generate_article(prompt, model_choice)
        if not result:
            print("❌ Ошибка генерации статьи")
            return False, None

        title, content = result
        
        # Определяем путь для сохранения
        if not output_file:
            output_path = chat_file.parent / "article.txt"
        else:
            output_path = Path(output_file)

        # Сохраняем результат
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"{title}\n")
                f.write("=" * len(title) + "\n\n")
                f.write(content)
            
            print(f"✅ Статья сохранена: {output_path}")
            print(f"📝 Заголовок: {title}")
            print(f"📄 Размер статьи: {len(content)} символов")
            
            return True, output_path
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return False, None


def main():
    parser = argparse.ArgumentParser(
        description="Создание статьи для соцсетей на основе чата",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python chat_processors/chat_article_processor.py pipeline_chat_ШрифтыВArchlinux/chat.txt
  python chat_processors/chat_article_processor.py pipeline_chat_ШрифтыВArchlinux/chat.txt --instructions instructions.txt
  python chat_processors/chat_article_processor.py pipeline_chat_ШрифтыВArchlinux/chat.txt --model quality --output my_article.txt
        """
    )

    parser.add_argument("chat_file", nargs='?', help="Путь к файлу чата (chat.txt)")
    parser.add_argument("--json", help="Путь к JSON файлу с экспортом чатов")
    parser.add_argument("--chat-id", help="ID чата в JSON экспорте (требуется с --json)")
    parser.add_argument("-o", "--output", help="Путь к выходному файлу (по умолчанию: article.txt в той же папке)")
    parser.add_argument("--instructions", help="Путь к файлу с дополнительными инструкциями")
    parser.add_argument("--config", help="Путь к .env файлу с конфигурацией")
    parser.add_argument("--model", choices=["default", "budget", "quality"], default="default", 
                       help="Выбор модели для генерации")
    
    args = parser.parse_args()

    # Проверка аргументов
    if args.json:
        if not args.chat_id:
            print("❌ Требуется --chat-id при использовании --json")
            return 1
    elif not args.chat_file:
        print("❌ Требуется либо chat_file, либо --json с --chat-id")
        parser.print_help()
        return 1

    try:
        processor = ChatArticleProcessor(args.config)
        
        if args.json:
            # Обработка JSON чата
            success, output_path = processor.process_json_chat(
                json_path=args.json,
                chat_id=args.chat_id,
                output_file=args.output,
                instructions_file=args.instructions,
                model_choice=args.model
            )
        else:
            # Обработка текстового файла чата
            success, output_path = processor.process_chat(
                chat_path=args.chat_file,
                output_file=args.output,
                instructions_file=args.instructions,
                model_choice=args.model
            )
        
        return 0 if success else 1
        
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
