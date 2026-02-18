#!/usr/bin/env python3
"""
Улучшенный скрипт для экспорта текстовых слоев из PDF в текст
Включает дополнительные возможности: статистика, форматирование, обработка ошибок
"""

import pdfplumber
import argparse
import sys
import os
import re
from pathlib import Path
from datetime import datetime


class PDFTextExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.pdf = None
        self.stats = {
            'total_pages': 0,
            'processed_pages': 0,
            'pages_with_text': 0,
            'pages_without_text': 0,
            'total_characters': 0,
            'total_words': 0
        }
    
    def open_pdf(self):
        """Открывает PDF файл"""
        try:
            self.pdf = pdfplumber.open(self.pdf_path)
            self.stats['total_pages'] = len(self.pdf.pages)
            print(f"✓ PDF файл открыт: {self.pdf_path}")
            print(f"✓ Количество страниц: {self.stats['total_pages']}")
            return True
        except Exception as e:
            print(f"✗ Ошибка при открытии PDF: {e}")
            return False
    
    def clean_text(self, text):
        """Очищает и форматирует извлеченный текст"""
        if not text:
            return ""
        
        # Удаляем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Удаляем лишние пробелы в начале и конце
        text = text.strip()
        
        return text
    
    def extract_page_text(self, page_num):
        """Извлекает текст с конкретной страницы"""
        try:
            page = self.pdf.pages[page_num]
            page_text = page.extract_text()
            
            if page_text:
                cleaned_text = self.clean_text(page_text)
                if cleaned_text:
                    self.stats['pages_with_text'] += 1
                    self.stats['total_characters'] += len(cleaned_text)
                    self.stats['total_words'] += len(cleaned_text.split())
                    return cleaned_text
                else:
                    self.stats['pages_without_text'] += 1
                    return None
            else:
                self.stats['pages_without_text'] += 1
                return None
                
        except Exception as e:
            print(f"✗ Ошибка при обработке страницы {page_num + 1}: {e}")
            self.stats['pages_without_text'] += 1
            return None
    
    def extract_text_range(self, start_page=None, end_page=None, include_page_numbers=True):
        """Извлекает текст из диапазона страниц"""
        if not self.pdf:
            print("✗ PDF файл не открыт")
            return None
        
        # Определяем диапазон страниц
        if start_page is None:
            start_page = 1
        if end_page is None:
            end_page = self.stats['total_pages']
        
        # Корректируем номера страниц (индексация с 0)
        start_idx = max(0, start_page - 1)
        end_idx = min(self.stats['total_pages'], end_page)
        
        print(f"📖 Извлекаем текст со страниц {start_page} по {end_idx}")
        print("=" * 50)
        
        extracted_pages = []
        
        for page_num in range(start_idx, end_idx):
            self.stats['processed_pages'] += 1
            
            page_text = self.extract_page_text(page_num)
            
            if page_text:
                if include_page_numbers:
                    page_content = f"\n{'='*20} СТРАНИЦА {page_num + 1} {'='*20}\n\n{page_text}\n"
                else:
                    page_content = page_text + "\n\n"
                
                extracted_pages.append(page_content)
                print(f"✓ Страница {page_num + 1}: {len(page_text)} символов")
            else:
                if include_page_numbers:
                    page_content = f"\n{'='*20} СТРАНИЦА {page_num + 1} {'='*20}\n\n[Текст не найден]\n"
                    extracted_pages.append(page_content)
                print(f"⚠ Страница {page_num + 1}: текст не найден")
        
        return "\n".join(extracted_pages)
    
    def save_text(self, text, output_path):
        """Сохраняет текст в файл"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"✓ Текст сохранен в файл: {output_path}")
            return True
        except Exception as e:
            print(f"✗ Ошибка при сохранении файла: {e}")
            return False
    
    def print_statistics(self):
        """Выводит статистику обработки"""
        print("\n" + "="*50)
        print("📊 СТАТИСТИКА ОБРАБОТКИ")
        print("="*50)
        print(f"Всего страниц в PDF: {self.stats['total_pages']}")
        print(f"Обработано страниц: {self.stats['processed_pages']}")
        print(f"Страниц с текстом: {self.stats['pages_with_text']}")
        print(f"Страниц без текста: {self.stats['pages_without_text']}")
        print(f"Всего символов: {self.stats['total_characters']:,}")
        print(f"Всего слов: {self.stats['total_words']:,}")
        
        if self.stats['processed_pages'] > 0:
            success_rate = (self.stats['pages_with_text'] / self.stats['processed_pages']) * 100
            print(f"Процент успешного извлечения: {success_rate:.1f}%")
    
    def close(self):
        """Закрывает PDF файл"""
        if self.pdf:
            self.pdf.close()


def main():
    parser = argparse.ArgumentParser(
        description="Улучшенный экспорт текстовых слоев из PDF в текст",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python pdf_text_extractor_advanced.py input.pdf
  python pdf_text_extractor_advanced.py input.pdf -o output.txt
  python pdf_text_extractor_advanced.py input.pdf -s 1 -e 10 -o output.txt
  python pdf_text_extractor_advanced.py input.pdf --no-page-numbers -o clean.txt
        """
    )
    
    parser.add_argument('pdf_file', help='Путь к PDF файлу')
    parser.add_argument('-o', '--output', help='Путь для сохранения текста')
    parser.add_argument('-s', '--start-page', type=int, help='Номер начальной страницы')
    parser.add_argument('-e', '--end-page', type=int, help='Номер конечной страницы')
    parser.add_argument('--no-page-numbers', action='store_true', 
                       help='Не добавлять номера страниц в вывод')
    parser.add_argument('--stats-only', action='store_true',
                       help='Показать только статистику без извлечения текста')
    
    args = parser.parse_args()
    
    # Проверяем существование файла
    if not os.path.exists(args.pdf_file):
        print(f"✗ Ошибка: Файл {args.pdf_file} не найден")
        sys.exit(1)
    
    # Создаем экстрактор
    extractor = PDFTextExtractor(args.pdf_file)
    
    # Открываем PDF
    if not extractor.open_pdf():
        sys.exit(1)
    
    # Если нужна только статистика
    if args.stats_only:
        # Обрабатываем все страницы для статистики
        extractor.extract_text_range()
        extractor.print_statistics()
        extractor.close()
        return
    
    # Если output не указан, создаем имя по умолчанию
    if not args.output:
        pdf_path = Path(args.pdf_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"{pdf_path.stem}_extracted_{timestamp}.txt"
    
    # Извлекаем текст
    text = extractor.extract_text_range(
        args.start_page, 
        args.end_page,
        not args.no_page_numbers
    )
    
    if text:
        # Сохраняем результат
        if extractor.save_text(text, args.output):
            print(f"\n✅ Извлечение завершено успешно!")
            print(f"📄 Размер извлеченного текста: {len(text):,} символов")
            
            # Выводим статистику
            extractor.print_statistics()
        else:
            print("❌ Не удалось сохранить текст")
            sys.exit(1)
    else:
        print("❌ Не удалось извлечь текст из PDF")
        sys.exit(1)
    
    extractor.close()


if __name__ == "__main__":
    main() 