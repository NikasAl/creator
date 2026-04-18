#!/usr/bin/env python3
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("❌ Библиотека deep-translator не установлена")
    print("💡 Установите её: pip install deep-translator")
    sys.exit(1)


def translate_text(text, source_lang, target_lang, max_retries=3):
    """
    Надёжный переводчик с экспоненциальной задержкой при ошибках
    """
    if not text or not text.strip():
        return text
    
    for attempt in range(max_retries):
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            result = translator.translate(text)
            if result and result.strip() != text.strip():
                return result
            print(f"⚠️ Подозрительный результат перевода (попытка {attempt+1})")
        except Exception as e:
            error_str = str(e).lower()
            if "too many requests" in error_str or "quota" in error_str:
                wait_time = 2 ** (attempt + 1)
                print(f"⏳ Превышен лимит запросов. Пауза {wait_time} сек...")
                time.sleep(wait_time)
            elif "not supported" in error_str:
                print(f"❌ Неподдерживаемая комбинация языков: {source_lang}->{target_lang}")
                return text
            else:
                print(f"🌐 Ошибка перевода (попытка {attempt+1}/{max_retries}): {str(e)}")
        
        if attempt < max_retries - 1:
            time.sleep(1.5 * (attempt + 1))
    
    print("❌ Не удалось перевести текст. Используем оригинальную версию.")
    return text


def edit_with_sublime(text, original_text=None):
    """
    Редактирование текста через Sublime Text с ожиданием закрытия файла
    """
    # Создаём временный файл с правильным расширением для подсветки
    with tempfile.NamedTemporaryFile(
        mode='w+', 
        suffix='.md',  # Markdown для лучшей подсветки художественных текстов
        delete=False,
        encoding='utf-8'
    ) as tmpfile:
        tmpfile.write(text)
        tmpfile_path = tmpfile.name
    
    print("\n" + "="*70)
    print("РЕДАКТИРОВАНИЕ В SUBLIME TEXT")
    print("• ОТКРОЕТСЯ ОКНО Sublime Text с переводом")
    print("• ВНЕСИТЕ ИЗМЕНЕНИЯ И СОХРАНИТЕ ФАЙЛ (Ctrl+S / Cmd+S)")
    print("• ЗАКРОЙТЕ ФАЙЛ И ОКНО Sublime (Ctrl+W / Cmd+W)")
    print("• СКРИПТ АВТОМАТИЧЕСКИ ПРОДОЛЖИТ РАБОТУ ПОСЛЕ ЗАКРЫТИЯ")
    print(f"• Редактируемый файл: {tmpfile_path}")
    print("="*70)
    
    input("\nНажмите Enter, чтобы открыть Sublime Text...")
    
    # Запускаем Sublime с ожиданием закрытия файла
    editor_cmd = ["subl", "-w", "--stay", tmpfile_path]
    
    try:
        print(f"🚀 Запускаем: {' '.join(shlex.quote(str(arg)) for arg in editor_cmd)}")
        subprocess.run(editor_cmd, check=True)
    except FileNotFoundError:
        print("❌ Команда 'subl' не найдена. Убедитесь, что Sublime Text установлен и добавлен в PATH")
        print("💡 Как добавить в PATH:")
        print("   Для macOS: ln -s /Applications/Sublime\\ Text.app/Contents/SharedSupport/bin/subl /usr/local/bin/subl")
        print("   Для Linux: sudo ln -s /opt/sublime_text/sublime_text /usr/bin/subl")
        os.unlink(tmpfile_path)
        return original_text if original_text is not None else text
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Sublime Text завершился с кодом {e.returncode}. Продолжаем с текущим текстом.")
    
    # Читаем результат после закрытия
    try:
        with open(tmpfile_path, 'r', encoding='utf-8') as tmpfile:
            edited_text = tmpfile.read()
    except Exception as e:
        print(f"❌ Ошибка чтения файла после редактирования: {str(e)}")
        os.unlink(tmpfile_path)
        return original_text if original_text is not None else text
    
    # Удаляем временный файл
    try:
        os.unlink(tmpfile_path)
    except Exception as e:
        print(f"⚠️ Не удалось удалить временный файл: {str(e)}")
    
    # Проверяем изменения
    if edited_text.strip() == text.strip():
        print("\nℹ️ Текст не был изменён в Sublime Text")
        return text
    
    # Проверка на отмену (пустой файл)
    if not edited_text.strip():
        print("\n↩️ Все изменения отменены (файл сохранён пустым)")
        return original_text if original_text is not None else text
    
    print(f"\n✅ Изменения приняты. Новая длина текста: {len(edited_text)} символов")
    return edited_text


def main(pipeline_path):
    illustrations_path = Path(pipeline_path) / "illustrations.json"
    
    # Проверка существования файла
    if not illustrations_path.exists():
        print(f"❌ Файл не найден: {illustrations_path.absolute()}")
        print("Проверьте правильность пути к pipeline")
        sys.exit(1)
    
    # Загрузка данных
    try:
        with open(illustrations_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения JSON: {str(e)}")
        sys.exit(1)
    
    illustrations = data.get("illustrations", [])
    if not illustrations:
        print("⚠️ В файле нет иллюстраций для редактирования")
        sys.exit(0)
    
    print(f"\n✨ Найдено иллюстраций: {len(illustrations)}")
    print(f"📚 Данные будут сохраняться в: {illustrations_path}")
    
    # Проверка наличия Sublime Text
    if not shutil.which("subl"):
        print("\n" + "!"*70)
        print("⚠️  CRITICAL: Sublime Text не найден в системе!")
        print("   Для работы скрипта требуется команда 'subl' в PATH")
        print("!"*70)
        print("\n💡 ИНСТРУКЦИЯ ПО УСТАНОВКЕ:")
        print("1. macOS:")
        print("   ln -s /Applications/Sublime\\ Text.app/Contents/SharedSupport/bin/subl /usr/local/bin/subl")
        print("2. Ubuntu/Debian:")
        print("   sudo apt install sublime-text")
        print("3. Arch Linux:")
        print("   sudo pacman -S sublime-text")
        print("4. Windows:")
        print("   Добавьте папку установки Sublime в PATH (обычно C:\\Program Files\\Sublime Text)")
        sys.exit(1)
    
    print("\n✅ Sublime Text обнаружен и готов к работе")
    
    # Основной цикл
    while True:
        print("\n" + "="*70)
        print("СПИСОК ИЛЛЮСТРАЦИЙ:")
        for i, ill in enumerate(illustrations, 1):
            length_status = "🟢" if len(ill['prompt']) < 800 else "🟡" if len(ill['prompt']) < 1500 else "🔴"
            print(f"{i:2d}. [{length_status}] {ill['title']}")
        print("="*70)

        choice = input("\nВыберите номер для редактирования (0 для выхода): ").strip()
        if choice == "0":
            break

        # Валидация выбора
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(illustrations)):
                raise ValueError
            current_ill = illustrations[idx]
        except (ValueError, TypeError):
            print(f"❌ Неверный номер. Введите число от 1 до {len(illustrations)}")
            continue
        
        # Редактирование выбранной иллюстрации
        print(f"\n🎯 Редактирование: {current_ill['title']}")
        print(f"🔤 Длина оригинального prompt: {len(current_ill['prompt'])} символов")
        
        # Перевод на русский
        print("\n⏳ Перевод на русский через Google Translate...")
        ru_prompt = translate_text(current_ill['prompt'], "en", "ru")
        
        # Редактирование через Sublime
        edited_ru = edit_with_sublime(ru_prompt, original_text=ru_prompt)
        if edited_ru == ru_prompt:
            print("\nℹ️ Перевод не изменён. Пропускаем сохранение.")
            continue
        
        # Перевод обратно на английский
        print("\n⏳ Перевод обратно на английский...")
        new_prompt = translate_text(edited_ru, "ru", "en")
        
        # Предпросмотр изменений
        print("\n" + "-"*70)
        print("СРАВНЕНИЕ ВЕРСИЙ:")
        print(f"Оригинал ({len(current_ill['prompt'])} симв.):")
        print(f"  {current_ill['prompt'][:100]}{'...' if len(current_ill['prompt']) > 100 else ''}")
        print(f"\nНовый вариант ({len(new_prompt)} симв.):")
        print(f"  {new_prompt[:100]}{'...' if len(new_prompt) > 100 else ''}")
        print("-"*70)
        
        # Подтверждение изменений
        # confirm = input("\n💾 Сохранить изменения? (y/n/отмена): ").strip().lower()
        confirm = "y"
        if confirm.startswith('y'):
            # Создание резервной копии
            backup_path = illustrations_path.with_suffix('.json.bak')
            illustrations_path.rename(backup_path)
            
            # Сохранение изменений
            current_ill['prompt'] = new_prompt
            with open(illustrations_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ Успешно сохранено! Резервная копия: {backup_path.name}")
            print(f"✨ Новая длина prompt: {len(new_prompt)} символов")
        elif confirm.startswith('о') or confirm == '!':
            print("\n↩️ Изменения отменены")
        else:
            print("\n❌ Изменения не сохранены")
    
    print("\n🎉 Работа завершена! Все изменения сохранены в файл.")


if __name__ == "__main__":
    import shutil  # Импорт здесь для доступности в main()
    
    # Проверка аргументов
    if len(sys.argv) != 2:
        print("Использование: python illustrator_corrector.py <путь_к_pipeline>")
        print("Пример: python illustrator_corrector.py pipelines_poetry/ТебяЯВзглядомПровожаю")
        sys.exit(1)
    
    pipeline_path = sys.argv[1]
    if not Path(pipeline_path).is_dir():
        print(f"❌ Директория не существует: {pipeline_path}")
        sys.exit(1)
    
    # Проверка версии библиотеки
    import deep_translator
    print(f"🌐 Используется deep-translator v{deep_translator.__version__}")
    
    main(pipeline_path)