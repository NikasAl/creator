#!/usr/bin/env python3
"""
Парсер для работы с JSON экспортом чатов

Функции:
- Парсит JSON файл с экспортом чатов
- Извлекает дерево сообщений из чата
- Конвертирует дерево в линейный текстовый формат (### USER / ### ASSISTANT)
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any


class ChatJsonParser:
    """Парсер для работы с JSON экспортом чатов"""
    
    def __init__(self):
        pass
    
    def parse_export_file(self, json_path: Path) -> List[Dict[str, Any]]:
        """
        Парсит JSON экспорт чатов
        
        Args:
            json_path: Путь к JSON файлу с экспортом
            
        Returns:
            Список словарей с информацией о чатах:
            [{"id": "...", "title": "...", "user_id": "...", "chat": {...}}, ...]
        """
        if not json_path.exists():
            raise FileNotFoundError(f"JSON файл не найден: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'data' not in data:
                raise ValueError("Неверный формат JSON: отсутствует поле 'data'")
            
            chats = data.get('data', [])
            if not isinstance(chats, list):
                raise ValueError("Поле 'data' должно быть списком")
            
            return chats
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON: {e}")
        except Exception as e:
            raise ValueError(f"Ошибка чтения файла: {e}")
    
    def extract_chat_tree(self, chat_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Извлекает дерево сообщений из чата
        
        Args:
            chat_data: Данные чата из JSON экспорта
            
        Returns:
            Словарь сообщений {message_id: message_data}
        """
        try:
            messages = chat_data.get('chat', {}).get('history', {}).get('messages', {})
            if not isinstance(messages, dict):
                raise ValueError("Неверный формат: messages должно быть словарем")
            return messages
        except (KeyError, AttributeError) as e:
            raise ValueError(f"Ошибка извлечения дерева сообщений: {e}")
    
    def extract_assistant_content(self, message: Dict[str, Any]) -> str:
        """
        Извлекает content из assistant сообщения
        
        Обрабатывает content_list: берет последний элемент с phase == "answer",
        или первый элемент, если нет answer
        
        Args:
            message: Словарь с данными сообщения
            
        Returns:
            Текст сообщения
        """
        # Если есть прямое поле content и оно не пустое
        if message.get('content'):
            return message['content']
        
        # Обрабатываем content_list
        content_list = message.get('content_list', [])
        if not content_list or not isinstance(content_list, list):
            return ""
        
        # Ищем элемент с phase == "answer"
        answer_content = None
        for item in content_list:
            if isinstance(item, dict) and item.get('phase') == 'answer':
                answer_content = item.get('content', '')
                break
        
        # Если нашли answer - используем его
        if answer_content:
            return answer_content
        
        # Иначе берем первый элемент
        if len(content_list) > 0 and isinstance(content_list[0], dict):
            return content_list[0].get('content', '')
        
        return ""
    
    def find_root_messages(self, messages_dict: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Находит корневые сообщения (parentId == null)
        
        Args:
            messages_dict: Словарь всех сообщений
            
        Returns:
            Список ID корневых сообщений
        """
        root_ids = []
        for msg_id, msg_data in messages_dict.items():
            parent_id = msg_data.get('parentId')
            if parent_id is None:
                root_ids.append(msg_id)
        return root_ids
    
    def build_linear_sequence(
        self, 
        root_message_id: str, 
        messages_dict: Dict[str, Dict[str, Any]],
        visited: Optional[set] = None
    ) -> List[Dict[str, str]]:
        """
        Строит линейную последовательность сообщений из дерева
        
        Args:
            root_message_id: ID корневого сообщения
            messages_dict: Словарь всех сообщений
            visited: Множество уже посещенных ID (для защиты от циклов)
            
        Returns:
            Список словарей [{"role": "user", "content": "..."}, ...]
        """
        if visited is None:
            visited = set()
        
        if root_message_id in visited or root_message_id not in messages_dict:
            return []
        
        visited.add(root_message_id)
        sequence = []
        current_id = root_message_id
        
        # Проходим по цепочке сообщений через childrenIds
        while current_id and current_id in messages_dict:
            message = messages_dict[current_id]
            role = message.get('role')
            
            if role == 'user':
                content = message.get('content', '').strip()
                if content:
                    sequence.append({"role": "user", "content": content})
            elif role == 'assistant':
                content = self.extract_assistant_content(message)
                if content.strip():
                    sequence.append({"role": "assistant", "content": content})
            
            # Переходим к следующему сообщению
            children_ids = message.get('childrenIds', [])
            if children_ids and len(children_ids) > 0:
                # Берем первого ребенка (основная ветка диалога)
                current_id = children_ids[0]
            else:
                break
        
        return sequence
    
    def convert_to_text_format(
        self, 
        messages_tree: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Конвертирует дерево сообщений в линейный текстовый формат
        
        Формат: ### USER\nтекст\n\n### ASSISTANT\nтекст\n\n...
        
        Args:
            messages_tree: Словарь сообщений {message_id: message_data}
            
        Returns:
            Текст в формате ### USER / ### ASSISTANT
        """
        # Находим корневые сообщения
        root_ids = self.find_root_messages(messages_tree)
        
        if not root_ids:
            return ""
        
        # Сортируем корневые сообщения по timestamp для правильного порядка
        root_messages = []
        for root_id in root_ids:
            if root_id in messages_tree:
                msg = messages_tree[root_id]
                timestamp = msg.get('timestamp', 0)
                root_messages.append((timestamp, root_id))
        
        root_messages.sort(key=lambda x: x[0])
        
        # Строим последовательности для каждого корня
        all_sequences = []
        visited = set()
        
        for _, root_id in root_messages:
            sequence = self.build_linear_sequence(root_id, messages_tree, visited)
            if sequence:
                all_sequences.append(sequence)
        
        # Объединяем все последовательности
        result_lines = []
        for sequence in all_sequences:
            for msg in sequence:
                if msg['role'] == 'user':
                    result_lines.append("### USER")
                    result_lines.append(msg['content'])
                    result_lines.append("")
                elif msg['role'] == 'assistant':
                    result_lines.append("### ASSISTANT")
                    result_lines.append(msg['content'])
                    result_lines.append("")
        
        return "\n".join(result_lines)
    
    def convert_chat_to_text(
        self, 
        chat_data: Dict[str, Any], 
        output_path: Optional[Path] = None
    ) -> str:
        """
        Конвертирует чат из JSON в текстовый формат
        
        Args:
            chat_data: Данные чата из JSON экспорта
            output_path: Опциональный путь для сохранения (если None - только возвращает)
            
        Returns:
            Текст в формате ### USER / ### ASSISTANT
        """
        # Извлекаем дерево сообщений
        messages_tree = self.extract_chat_tree(chat_data)
        
        # Конвертируем в текстовый формат
        text_content = self.convert_to_text_format(messages_tree)
        
        # Сохраняем если указан путь
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text_content, encoding='utf-8')
        
        return text_content


def main():
    """Пример использования парсера"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Конвертация чата из JSON в текстовый формат"
    )
    parser.add_argument("json_file", help="Путь к JSON файлу с экспортом чатов")
    parser.add_argument("--chat-id", help="ID чата для конвертации")
    parser.add_argument("--output", "-o", help="Путь для сохранения результата")
    
    args = parser.parse_args()
    
    parser_obj = ChatJsonParser()
    
    # Парсим экспорт
    chats = parser_obj.parse_export_file(Path(args.json_file))
    
    if args.chat_id:
        # Ищем конкретный чат
        chat_data = None
        for chat in chats:
            if chat.get('id') == args.chat_id:
                chat_data = chat
                break
        
        if not chat_data:
            print(f"❌ Чат с ID {args.chat_id} не найден")
            return 1
        
        # Конвертируем
        output_path = Path(args.output) if args.output else None
        text = parser_obj.convert_chat_to_text(chat_data, output_path)
        
        if not args.output:
            print(text)
        
        print(f"✅ Чат конвертирован успешно")
        if output_path:
            print(f"📁 Сохранено: {output_path}")
    else:
        # Показываем список чатов
        print(f"📋 Найдено чатов: {len(chats)}\n")
        for i, chat in enumerate(chats, 1):
            chat_id = chat.get('id', 'N/A')
            title = chat.get('title', 'Без названия')
            print(f"{i}. [{chat_id}] {title}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

