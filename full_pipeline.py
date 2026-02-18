#!/usr/bin/env python3
"""
Полный пайплайн обработки PDF для создания аудиокниги и пересказа
Объединяет все процессоры: извлечение, очистку, обработку и пересказ
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent))

# Импортируем все процессоры
from text_processors.pdf_text_extractor_advanced import PDFTextExtractor
from text_processors.vision_ocr_processor import VisionOCRProcessor
from text_processors.clean_text_processor import CleanTextProcessor
from text_processors.smart_text_processor import SmartTextProcessor
from text_processors.summary_processor import SummaryProcessor
from text_processors.summary_summarizer import SummarySummarizer
from video_processors.illustration_prompt_processor import IllustrationPromptProcessor


class FullPipeline:
    def __init__(self, config_file: str = None):
        """
        Инициализация полного пайплайна
        
        Args:
            config_file: Путь к файлу конфигурации .env
        """
        self.config_file = config_file
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_time': 0,
            'files_created': [],
            'errors': []
        }
    
    def run_pipeline(self, pdf_file: str, output_dir: str = "output", 
                    create_summary: bool = True, summary_style: str = 'educational',
                    book_title: str = None, book_author: str = None,
                    page_range: str = None,
                    create_illustrations: bool = False,
                    illustrations_from: str = 'summary',
                    illustrations_parts: int = 8,
                    illustrations_style: str = None) -> bool:
        """
        Запускает полный пайплайн обработки
        
        Args:
            pdf_file: Путь к PDF файлу
            output_dir: Директория для результатов
            create_summary: Создавать ли пересказ
            summary_style: Стиль пересказа
            book_title: Название книги
            book_author: Автор книги
            
        Returns:
            True если пайплайн выполнен успешно
        """
        self.stats['start_time'] = time.time()
        
        try:
            # Создаем выходную директорию
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            print("🚀 ЗАПУСК ПОЛНОГО ПАЙПЛАЙНА")
            print("=" * 60)
            print(f"📁 Входной файл: {pdf_file}")
            print(f"📁 Выходная директория: {output_dir}")
            print(f"📝 Создание пересказа: {'Да' if create_summary else 'Нет'}")
            if create_summary:
                print(f"🎨 Стиль пересказа: {summary_style}")
            if page_range:
                print(f"📄 Диапазон страниц: {page_range}")
            if create_illustrations:
                print(f"🖼️  Генерация иллюстраций: Да (источник: {illustrations_from}, частей: {illustrations_parts})")
            
            # Этап 1: Извлечение текста из PDF
            print("\n📖 ЭТАП 1: Извлечение текста из PDF")
            print("-" * 40)
            
            raw_text_file = output_path / f"{Path(pdf_file).stem}_raw.txt"
            
            # Проверяем, есть ли уже извлеченный текст
            if raw_text_file.exists():
                print(f"✅ Файл уже существует, пропускаем извлечение: {raw_text_file}")
                self.stats['files_created'].append(str(raw_text_file))
            else:
                extractor = PDFTextExtractor(pdf_file)
                
                # Открываем PDF
                if not extractor.open_pdf():
                    self.stats['errors'].append("Ошибка открытия PDF файла")
                    return False
                
                # Парсим диапазон страниц
                start_page = 1
                end_page = None
                if page_range:
                    try:
                        if '-' in page_range:
                            start_page, end_page = map(int, page_range.split('-'))
                        else:
                            end_page = int(page_range)
                    except ValueError:
                        self.stats['errors'].append("Неверный формат диапазона страниц. Используйте формат '1-30' или '30'")
                        extractor.close()
                        return False
                
                # Извлекаем текст
                extracted_text = extractor.extract_text_range(start_page, end_page, include_page_numbers=False)

                # Если текст пуст или малоуспешный (например, очень мало символов), пробуем OCR через vision LLM
                need_ocr = (not extracted_text) or (len(extracted_text.strip()) < 20) or ("[Текст не найден]" in extracted_text)
                if need_ocr:
                    print("⚠️  Похоже, что в PDF отсутствует текстовый слой. Запускаем OCR через vision модель...")
                    print(f"🔍 Модель OCR: {os.getenv('VISION_MODEL', 'не задана')}")
                    
                    try:
                        ocr = VisionOCRProcessor(self.config_file)
                        # Открытый pdf уже есть в extractor.pdf; используем диапазон и добавляем разделители
                        start_idx = max(0, (start_page or 1) - 1)
                        end_idx = (end_page if end_page is not None else extractor.stats['total_pages'])
                        
                        print(f"📄 OCR диапазон: страницы {start_idx + 1}-{end_idx}")
                        
                        parts = []
                        successful_pages = 0
                        failed_pages = 0
                        
                        for i in range(start_idx, end_idx):
                            page_num = i + 1
                            print(f"\n🔄 OCR страница {page_num}/{end_idx}...")
                            
                            try:
                                text_page = ocr.ocr_pdf_page(extractor.pdf, i)
                                if text_page and text_page.strip():
                                    parts.append(text_page.strip() + "\n\n")
                                    successful_pages += 1
                                    print(f"✅ Страница {page_num}: OCR успешен ({len(text_page)} символов)")
                                else:
                                    parts.append("\n")
                                    failed_pages += 1
                                    print(f"❌ Страница {page_num}: OCR не удался")
                            except Exception as page_error:
                                parts.append("\n")
                                failed_pages += 1
                                print(f"💥 Страница {page_num}: критическая ошибка OCR: {page_error}")
                        
                        extracted_text = "".join(parts)
                        
                        print(f"\n📊 Результаты OCR:")
                        print(f"   Успешно обработано: {successful_pages} страниц")
                        print(f"   Неудачно: {failed_pages} страниц")
                        print(f"   Всего символов извлечено: {len(extracted_text)}")
                        
                        # Если большинство страниц не удалось обработать, это проблема
                        if failed_pages > successful_pages:
                            error_msg = f"OCR неудачен: {failed_pages} из {successful_pages + failed_pages} страниц не обработаны"
                            self.stats['errors'].append(error_msg)
                            print(f"❌ {error_msg}")
                            
                    except Exception as e:
                        error_msg = f"Критическая ошибка OCR: {e}"
                        self.stats['errors'].append(error_msg)
                        print(f"💥 {error_msg}")
                        extractor.close()
                        return False

                if not extracted_text or len(extracted_text.strip()) == 0:
                    self.stats['errors'].append("Ошибка извлечения текста из PDF (включая OCR)")
                    extractor.close()
                    return False
                
                # Сохраняем текст
                if not extractor.save_text(extracted_text, str(raw_text_file)):
                    self.stats['errors'].append("Ошибка сохранения извлеченного текста")
                    extractor.close()
                    return False
                
                extractor.close()
                self.stats['files_created'].append(str(raw_text_file))
                print(f"✅ Текст извлечен: {raw_text_file}")
            
            # Этап 2: Очистка текста
            print("\n🧹 ЭТАП 2: Очистка текста")
            print("-" * 40)
            
            clean_text_file = output_path / f"{Path(pdf_file).stem}_clean.txt"
            
            # Проверяем, есть ли уже очищенный текст
            if clean_text_file.exists():
                print(f"✅ Файл уже существует, пропускаем очистку: {clean_text_file}")
                self.stats['files_created'].append(str(clean_text_file))
            else:
                cleaner = CleanTextProcessor(self.config_file)
                
                success = cleaner.process_text_file(
                    str(raw_text_file), 
                    str(clean_text_file),
                    book_title,
                    book_author
                )
                if not success:
                    self.stats['errors'].append("Ошибка очистки текста")
                    return False
                
                self.stats['files_created'].append(str(clean_text_file))
                print(f"✅ Текст очищен: {clean_text_file}")
            
            # Этап 3: Обработка для аудиокниги (не используется в текущей версии)
            # print("\n🎧 ЭТАП 3: Обработка для аудиокниги")
            # print("-" * 40)
            
            # processor = SmartTextProcessor(self.config_file)
            # audiobook_file = output_path / f"{Path(pdf_file).stem}_audiobook.txt"
            
            # success = processor.process_text_file(str(clean_text_file), str(audiobook_file))
            # if not success:
            #     self.stats['errors'].append("Ошибка обработки для аудиокниги")
            #     return False
            
            # self.stats['files_created'].append(str(audiobook_file))
            # print(f"✅ Аудиокнига готова: {audiobook_file}")
            
            # Этап 3: Создание пересказа (опционально)
            summary_file = None
            if create_summary:
                print(f"\n📝 ЭТАП 3: Создание пересказа ({summary_style})")
                print("-" * 40)
                
                summary_file = output_path / f"{Path(pdf_file).stem}_summary_{summary_style}.txt"
                
                # Проверяем, есть ли уже пересказ
                if summary_file.exists():
                    print(f"✅ Файл уже существует, пропускаем создание пересказа: {summary_file}")
                    self.stats['files_created'].append(str(summary_file))
                else:
                    summarizer = SummaryProcessor(self.config_file, book_title=book_title)
                    
                    success = summarizer.process_text_file(
                        str(clean_text_file), 
                        str(summary_file),
                        summary_style
                    )
                    if not success:
                        self.stats['errors'].append("Ошибка создания пересказа")
                        return False
                    
                    self.stats['files_created'].append(str(summary_file))
                    print(f"✅ Пересказ создан: {summary_file}")
                
                # Создаем краткую сводку из summary
                print(f"\n📋 Создание краткой сводки из пересказа")
                print("-" * 40)
                
                short_summary_file = output_path / f"{Path(pdf_file).stem}_short_summary.txt"
                
                # Проверяем, есть ли уже краткая сводка
                if short_summary_file.exists():
                    print(f"✅ Файл уже существует, пропускаем создание краткой сводки: {short_summary_file}")
                    self.stats['files_created'].append(str(short_summary_file))
                else:
                    summarizer = SummarySummarizer(str(summary_file))
                    
                    success = summarizer.create_summary(str(short_summary_file), lines_per_fragment=3)
                    if not success:
                        self.stats['errors'].append("Ошибка создания краткой сводки")
                        return False
                    
                    self.stats['files_created'].append(str(short_summary_file))
                    print(f"✅ Краткая сводка создана: {short_summary_file}")

            # Этап 4: Генерация промптов иллюстраций (опционально)
            if create_illustrations:
                print("\n🖼️  ЭТАП 4: Генерация промптов для иллюстраций")
                print("-" * 40)
                source_file = None
                if illustrations_from == 'summary' and summary_file and Path(summary_file).exists():
                    source_file = summary_file
                else:
                    source_file = clean_text_file

                print(f"📄 Источник: {source_file}")

                illust_out = output_path / f"{Path(pdf_file).stem}_illustrations.json"
                ill_processor = IllustrationPromptProcessor(self.config_file)
                ok = ill_processor.generate_illustrations(
                    input_file=str(source_file),
                    output_file=str(illust_out),
                    parts=illustrations_parts,
                    style=illustrations_style,
                    model_choice='default',
                    book_title=book_title,
                    book_author=book_author,
                )
                if not ok:
                    self.stats['errors'].append("Ошибка генерации промптов иллюстраций")
                    return False
                self.stats['files_created'].append(str(illust_out))
                print(f"✅ Промпты иллюстраций сохранены: {illust_out}")
            
            # Создаем отчет
            self.create_report(output_path, pdf_file, create_summary, summary_style, page_range)
            
            self.stats['end_time'] = time.time()
            self.stats['total_time'] = self.stats['end_time'] - self.stats['start_time']
            
            # Выводим итоговую статистику
            self.print_final_stats()
            
            return True
            
        except Exception as e:
            self.stats['errors'].append(f"Неожиданная ошибка: {e}")
            print(f"❌ Ошибка пайплайна: {e}")
            return False
    
    def create_report(self, output_path: Path, pdf_file: str, 
                     create_summary: bool, summary_style: str, page_range: str = None):
        """Создает отчет о выполненной работе"""
        report_file = output_path / f"{Path(pdf_file).stem}_report.txt"
        
        report_content = f"""# Отчет о полной обработке PDF

**Исходный файл:** {pdf_file}  
**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Время выполнения:** {self.stats['total_time']:.1f} секунд
"""
        
        if page_range:
            report_content += f"**Диапазон страниц:** {page_range}\n"
        
        report_content += f"""
## Созданные файлы:

1. **{Path(pdf_file).stem}_raw.txt** - Исходный текст, извлеченный из PDF
2. **{Path(pdf_file).stem}_clean.txt** - Очищенный текст без технических элементов
"""
        
        if create_summary:
            report_content += f"""3. **{Path(pdf_file).stem}_summary_{summary_style}.txt** - Пересказ основных идей ({summary_style})
4. **{Path(pdf_file).stem}_short_summary.txt** - Краткая сводка по фрагментам

## Описание этапов:

### Этап 1: Извлечение текста
- Использован продвинутый PDF экстрактор
- Сохранена структура и форматирование
- Добавлены разделители между страницами

### Этап 2: Очистка текста
- Удалены библиографические данные (ISBN, УДК, ББК)
- Убраны номера страниц и технические пометки
- Исправлены переносы строк и форматирование
- Удалены предупреждения об авторских правах

### Этап 3: Создание пересказа
- Выделены ключевые идеи и концепции
- Упрощены сложные термины
- Структурирована информация
- Стиль изложения: {summary_style}

### Этап 4: Создание краткой сводки
- Извлечено введение до первого фрагмента
- Создана краткая сводка по каждому фрагменту (3 строки на фрагмент)
- Убраны дублирующиеся заголовки

## Рекомендации по использованию:

- **Для чтения:** Используйте файл `*_clean.txt`
- **Для изучения:** Используйте файл `*_summary_*.txt`
- **Для быстрого обзора:** Используйте файл `*_short_summary.txt`
- **Для анализа:** Используйте файл `*_raw.txt`

---
*Отчет создан автоматически с помощью Full Pipeline Processor*
"""
        else:
            report_content += """
## Описание этапов:

### Этап 1: Извлечение текста
- Использован продвинутый PDF экстрактор
- Сохранена структура и форматирование
- Добавлены разделители между страницами

### Этап 2: Очистка текста
- Удалены библиографические данные (ISBN, УДК, ББК)
- Убраны номера страниц и технические пометки
- Исправлены переносы строк и форматирование
- Удалены предупреждения об авторских правах

## Рекомендации по использованию:

- **Для чтения:** Используйте файл `*_clean.txt`
- **Для анализа:** Используйте файл `*_raw.txt`

---
*Отчет создан автоматически с помощью Full Pipeline Processor*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.stats['files_created'].append(str(report_file))
        print(f"📊 Отчет создан: {report_file}")
    
    def print_final_stats(self):
        """Выводит итоговую статистику"""
        print("\n" + "=" * 60)
        print("🎉 ПАЙПЛАЙН ЗАВЕРШЕН УСПЕШНО!")
        print("=" * 60)
        print(f"⏱️  Общее время: {self.stats['total_time']:.1f} секунд")
        print(f"📁 Создано файлов: {len(self.stats['files_created'])}")
        print(f"❌ Ошибок: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print("\n⚠️  Ошибки:")
            for error in self.stats['errors']:
                print(f"   - {error}")
        
        print("\n📁 Созданные файлы:")
        for file_path in self.stats['files_created']:
            size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            print(f"   📄 {Path(file_path).name} ({size:,} байт)")


def main():
    parser = argparse.ArgumentParser(
        description="Полный пайплайн обработки PDF для создания аудиокниги и пересказа",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python full_pipeline.py "book.pdf"
  python full_pipeline.py "book.pdf" --output "results" --no-summary
  python full_pipeline.py "book.pdf" --summary-style simple --title "Название" --author "Автор"
  python full_pipeline.py "book.pdf" --config config.env
  python full_pipeline.py "book.pdf" --page-range "1-30" --summary-style simple
  python full_pipeline.py "book.pdf" --page-range "50-80" --no-summary
        """
    )
    
    parser.add_argument('pdf_file', help='PDF файл для обработки')
    parser.add_argument('--output', '-o', default='output', help='Выходная директория')
    parser.add_argument('--config', help='Файл конфигурации .env')
    parser.add_argument('--vision-model', help='Модель для OCR (vision LLM), если нужно переопределить VISION_MODEL из env')
    parser.add_argument('--no-summary', action='store_true', help='Не создавать пересказ')
    parser.add_argument('--summary-style', choices=['educational', 'simple', 'detailed'], 
                       default='educational', help='Стиль пересказа')
    parser.add_argument('--title', help='Название книги')
    parser.add_argument('--author', help='Автор книги')
    parser.add_argument('--page-range', help='Диапазон страниц для обработки (например: "1-30" или "30" для первых 30 страниц)')
    # Иллюстрации
    parser.add_argument('--illustrations', action='store_true', help='Сгенерировать промпты для иллюстраций')
    parser.add_argument('--illustrations-from', choices=['clean', 'summary'], default='summary', help='Источник текста для иллюстраций')
    parser.add_argument('--illustrations-parts', type=int, default=8, help='Количество частей для иллюстраций')
    parser.add_argument('--illustrations-style', help='Желаемый визуальный стиль (подсказка LLM)')
    
    args = parser.parse_args()
    
    # Проверяем входной файл
    if not Path(args.pdf_file).exists():
        print(f"❌ Ошибка: Файл {args.pdf_file} не найден")
        return 1
    
    try:
        # Создаем пайплайн
        # Если указана vision-модель в флагах, экспортируем в переменную окружения на время процесса
        if args.vision_model:
            os.environ['VISION_MODEL'] = args.vision_model
        pipeline = FullPipeline(args.config)
        
        # Запускаем обработку
        success = pipeline.run_pipeline(
            args.pdf_file,
            args.output,
            not args.no_summary,
            args.summary_style,
            args.title,
            args.author,
            args.page_range,
            args.illustrations,
            args.illustrations_from,
            args.illustrations_parts,
            args.illustrations_style
        )
        
        if success:
            print(f"\n✅ Пайплайн завершен успешно!")
            print(f"📁 Результаты сохранены в: {args.output}")
        else:
            print("❌ Ошибка при выполнении пайплайна")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 