#!/usr/bin/env python3
"""
Summary Summarizer - создает краткую сводку из summary файлов

Этот скрипт:
1. Извлекает начало summary до первого слова "Фрагмент"
2. Находит все заголовки "Фрагмент" и берет по несколько строк из каждого
3. Создает новый файл со сводкой
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Tuple


class SummarySummarizer:
    def __init__(self, summary_file_path: str):
        self.summary_file_path = Path(summary_file_path)
        self.content = ""
        self.fragments = []
        
    def load_summary(self) -> bool:
        """Загружает содержимое summary файла"""
        try:
            with open(self.summary_file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            return True
        except Exception as e:
            print(f"Ошибка при чтении файла {self.summary_file_path}: {e}")
            return False
    
    def extract_introduction(self) -> str:
        """Извлекает введение до первого слова 'Фрагмент'"""
        # Ищем первое вхождение "Фрагмент" (с номером)
        fragment_match = re.search(r'Фрагмент\s+\d+', self.content)
        
        if fragment_match:
            # Берем текст до первого фрагмента
            introduction = self.content[:fragment_match.start()].strip()
            return introduction
        else:
            # Если фрагменты не найдены, возвращаем весь текст
            return self.content.strip()
    
    def find_fragments(self) -> List[Tuple[int, int, str]]:
        """Находит все фрагменты и их позиции"""
        fragments = []
        
        # Ищем все вхождения "Фрагмент N"
        fragment_pattern = r'Фрагмент\s+\d+'
        matches = list(re.finditer(fragment_pattern, self.content))
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            
            # Определяем конец фрагмента (начало следующего или конец файла)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(self.content)
            
            fragment_text = self.content[start_pos:end_pos].strip()
            fragments.append((start_pos, end_pos, fragment_text))
        
        return fragments
    
    def extract_fragment_summary(self, fragment_text: str, lines_count: int = 5) -> str:
        """Извлекает краткую сводку из фрагмента (первые несколько строк)"""
        lines = fragment_text.split('\n')
        
        # Убираем пустые строки в начале
        while lines and not lines[0].strip():
            lines.pop(0)
        
        # Убираем заголовок "Фрагмент N" если он есть
        if lines and re.match(r'^\s*Фрагмент\s+\d+\s*$', lines[0].strip()):
            lines.pop(0)
        
        # Берем первые несколько непустых строк
        summary_lines = []
        non_empty_count = 0
        
        for line in lines:
            if line.strip():
                summary_lines.append(line)
                non_empty_count += 1
                if non_empty_count >= lines_count:
                    break
            else:
                summary_lines.append(line)
        
        return '\n'.join(summary_lines)
    
    def create_summary(self, output_file: str = None, lines_per_fragment: int = 5) -> str:
        """Создает сводку из summary"""
        if not self.load_summary():
            return ""
        
        # Извлекаем введение
        introduction = self.extract_introduction()
        
        # Находим все фрагменты
        fragments = self.find_fragments()
        
        # Создаем сводку
        summary_lines = []
        
        # Добавляем введение
        summary_lines.append(introduction)
        summary_lines.append("Содержание")
        summary_lines.append("\n")
        
        # Добавляем краткую информацию по каждому фрагменту
        for i, (start, end, fragment_text) in enumerate(fragments, 1):
            summary_lines.append(f"\n--- Фрагмент {i} ---")
            
            # Извлекаем краткую сводку из фрагмента
            fragment_summary = self.extract_fragment_summary(fragment_text, lines_per_fragment)
            summary_lines.append(fragment_summary)
            
        
        # Объединяем все строки
        full_summary = '\n'.join(summary_lines)
        
        # Определяем имя выходного файла
        if output_file is None:
            base_name = self.summary_file_path.stem
            output_file = self.summary_file_path.parent / f"{base_name}_summary.txt"
        
        # Сохраняем файл
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_summary)
            print(f"Сводка сохранена в файл: {output_file}")
        except Exception as e:
            print(f"Ошибка при сохранении файла {output_file}: {e}")
            return ""
        
        return full_summary
    
    def get_statistics(self) -> dict:
        """Возвращает статистику по summary файлу"""
        if not self.content:
            if not self.load_summary():
                return {}
        
        fragments = self.find_fragments()
        
        stats = {
            'total_fragments': len(fragments),
            'total_length': len(self.content),
            'introduction_length': len(self.extract_introduction()),
            'fragments_info': []
        }
        
        for i, (start, end, fragment_text) in enumerate(fragments, 1):
            fragment_stats = {
                'fragment_number': i,
                'start_position': start,
                'end_position': end,
                'length': len(fragment_text),
                'lines': len(fragment_text.split('\n'))
            }
            stats['fragments_info'].append(fragment_stats)
        
        return stats


def main():
    parser = argparse.ArgumentParser(description='Создает краткую сводку из summary файла')
    parser.add_argument('summary_file', help='Путь к summary файлу')
    parser.add_argument('-o', '--output', help='Путь к выходному файлу (по умолчанию: summary_summary.txt)')
    parser.add_argument('-l', '--lines', type=int, default=5, 
                       help='Количество строк для извлечения из каждого фрагмента (по умолчанию: 5)')
    parser.add_argument('-s', '--stats', action='store_true', 
                       help='Показать статистику по файлу')
    
    args = parser.parse_args()
    
    # Проверяем существование файла
    if not os.path.exists(args.summary_file):
        print(f"Ошибка: файл {args.summary_file} не найден")
        return
    
    # Создаем экземпляр summarizer
    summarizer = SummarySummarizer(args.summary_file)
    
    # Показываем статистику, если запрошено
    if args.stats:
        stats = summarizer.get_statistics()
        print(f"\nСтатистика по файлу {args.summary_file}:")
        print(f"Всего фрагментов: {stats['total_fragments']}")
        print(f"Общая длина: {stats['total_length']} символов")
        print(f"Длина введения: {stats['introduction_length']} символов")
        print("\nИнформация по фрагментам:")
        for frag_info in stats['fragments_info']:
            print(f"  Фрагмент {frag_info['fragment_number']}: {frag_info['lines']} строк, "
                  f"{frag_info['length']} символов")
    
    # Создаем сводку
    print(f"\nСоздание сводки из файла: {args.summary_file}")
    print(f"Строк на фрагмент: {args.lines}")
    
    summary = summarizer.create_summary(args.output, args.lines)
    
    if summary:
        print(f"Сводка успешно создана! Длина: {len(summary)} символов")


if __name__ == "__main__":
    main()
