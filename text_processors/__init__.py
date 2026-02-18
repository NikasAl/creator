# Text processors package
"""
Процессоры текста для различных задач.

Доступные процессоры:
- SummaryProcessor: Создание саммари текста
- CorrectionProcessor: Интерактивная коррекция текста
- AudioBookProcessor: Подготовка текста для аудиокниги
- TextProcessor: Базовый процессор текста
"""

# Оригинальные процессоры
from .summary_processor import SummaryProcessor
from .text_processor import TextProcessor

# Рефакторенные версии (рекомендуются для нового кода)
from .correction_processor_v2 import InteractiveCorrector
from .audiobook_processor_v2 import AudioBookProcessor

__all__ = [
    # Оригинальные
    'SummaryProcessor',
    'TextProcessor',
    # Рефакторенные
    'InteractiveCorrector',
    'AudioBookProcessor',
]
