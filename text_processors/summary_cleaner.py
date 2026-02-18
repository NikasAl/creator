#!/usr/bin/env python3
"""
Скрипт для очистки summary файлов от символов # для совместимости с озвучивателями
"""

import re
import argparse
from pathlib import Path


class SummaryCleaner:
    def __init__(self):
        self.replacements = {
            '#': '',  # Убираем все #
            '**': '',  # Убираем жирный текст
            '*': '',   # Убираем курсив
        }
    
    def clean_summary(self, input_file: str, output_file: str = None) -> bool:
        """
        Очищает summary файл от символов форматирования
        
        Args:
            input_file: Входной файл summary
            output_file: Выходной файл (если не указан, создается автоматически)
            
        Returns:
            True если очистка успешна
        """
        try:
            # Читаем исходный файл
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"📖 Загружен файл: {input_file}")
            print(f"📊 Размер: {len(content):,} символов")
            
            # Очищаем контент
            cleaned_content = self.clean_content(content)
            
            # Определяем выходной файл
            if not output_file:
                input_path = Path(input_file)
                output_file = str(input_path.parent / f"{input_path.stem}_clean{input_path.suffix}")
            
            # Сохраняем результат
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            print(f"✅ Очищенный файл сохранен: {output_file}")
            print(f"📊 Новый размер: {len(cleaned_content):,} символов")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка очистки: {e}")
            return False
    
    def clean_content(self, content: str) -> str:
        """
        Очищает контент от символов форматирования
        
        Args:
            content: Исходный контент
            
        Returns:
            Очищенный контент
        """
        # Убираем заголовки с #
        content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
        
        # Убираем жирный текст
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        
        # Убираем курсив
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        
        # Убираем оставшиеся #
        content = content.replace('#', '')
        
        # Убираем лишние пустые строки
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Убираем лишние пробелы в начале строк
        content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)
        
        return content.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Очистка summary файлов от символов форматирования для озвучивания",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python summary_cleaner.py summary.txt
  python summary_cleaner.py summary.txt -o summary_clean.txt
  python summary_cleaner.py summary.txt --output summary_for_audio.txt
        """
    )
    
    parser.add_argument('input_file', help='Входной summary файл')
    parser.add_argument('-o', '--output', help='Выходной файл (опционально)')
    
    args = parser.parse_args()
    
    # Проверяем входной файл
    if not Path(args.input_file).exists():
        print(f"❌ Ошибка: Файл {args.input_file} не найден")
        return 1
    
    try:
        # Создаем очиститель
        cleaner = SummaryCleaner()
        
        # Очищаем файл
        success = cleaner.clean_summary(args.input_file, args.output)
        
        if success:
            print("✅ Очистка завершена успешно!")
        else:
            print("❌ Ошибка при очистке")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 