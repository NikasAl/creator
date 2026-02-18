#!/usr/bin/env python3
"""
Анализатор пайплайна для извлечения метаданных видео
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class PipelineMetadata:
    """Метаданные из пайплайна"""
    pipeline_name: str
    video_path: str
    promo_description: Optional[str] = None
    illustrations: Optional[List[Dict]] = None
    clean_text: Optional[str] = None
    summary_text: Optional[str] = None
    short_summary: Optional[str] = None
    book_title: Optional[str] = None
    book_author: Optional[str] = None
    page_range: Optional[str] = None
    
    def has_video(self) -> bool:
        """Проверяет наличие видеофайла"""
        return Path(self.video_path).exists() if self.video_path else False
    
    def has_promo_description(self) -> bool:
        """Проверяет наличие промо-описания"""
        return bool(self.promo_description and self.promo_description.strip())
    
    def has_illustrations(self) -> bool:
        """Проверяет наличие иллюстраций"""
        return bool(self.illustrations and len(self.illustrations) > 0)


class PipelineAnalyzer:
    """Анализатор пайплайна для извлечения метаданных"""
    
    def __init__(self, pipeline_path: str):
        """
        Инициализация анализатора
        
        Args:
            pipeline_path: Путь к директории пайплайна
        """
        self.pipeline_path = Path(pipeline_path)
        self.metadata = None
        
    def analyze(self) -> PipelineMetadata:
        """
        Анализирует пайплайн и извлекает метаданные
        
        Returns:
            Метаданные пайплайна
        """
        if not self.pipeline_path.exists():
            raise FileNotFoundError(f"Директория пайплайна не найдена: {self.pipeline_path}")
        
        # Извлекаем название пайплайна из пути
        pipeline_name = self.pipeline_path.name
        
        # Ищем основные файлы
        video_path = self._find_video_file()
        promo_description = self._read_promo_description()
        illustrations = self._read_illustrations()
        clean_text = self._read_clean_text()
        summary_text = self._read_summary_text()
        short_summary = self._read_short_summary()
        
        # Извлекаем информацию о книге из названия пайплайна
        book_title, book_author, page_range = self._extract_book_info(pipeline_name)
        
        self.metadata = PipelineMetadata(
            pipeline_name=pipeline_name,
            video_path=str(video_path) if video_path else "",
            promo_description=promo_description,
            illustrations=illustrations,
            clean_text=clean_text,
            summary_text=summary_text,
            short_summary=short_summary,
            book_title=book_title,
            book_author=book_author,
            page_range=page_range
        )
        
        return self.metadata
    
    def _find_video_file(self) -> Optional[Path]:
        """Ищет видеофайл в пайплайне"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        
        for ext in video_extensions:
            video_file = self.pipeline_path / f"video{ext}"
            if video_file.exists():
                return video_file
        
        return None
    
    def _read_promo_description(self) -> Optional[str]:
        """Читает промо-описание"""
        promo_file = self.pipeline_path / "promo_description.txt"
        
        if promo_file.exists():
            try:
                with open(promo_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"⚠️  Ошибка чтения промо-описания: {e}")
        
        return None
    
    def _read_illustrations(self) -> Optional[List[Dict]]:
        """Читает информацию об иллюстрациях"""
        illustrations_file = self.pipeline_path / "illustrations.json"
        
        if illustrations_file.exists():
            try:
                with open(illustrations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('illustrations', [])
            except Exception as e:
                print(f"⚠️  Ошибка чтения иллюстраций: {e}")
        
        return None
    
    def _read_clean_text(self) -> Optional[str]:
        """Читает очищенный текст"""
        clean_files = list(self.pipeline_path.glob("*_clean.txt"))
        
        if clean_files:
            try:
                with open(clean_files[0], 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"⚠️  Ошибка чтения очищенного текста: {e}")
        
        return None
    
    def _read_summary_text(self) -> Optional[str]:
        """Читает текст пересказа"""
        summary_files = list(self.pipeline_path.glob("*_summary_*.txt"))
        
        if summary_files:
            try:
                with open(summary_files[0], 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"⚠️  Ошибка чтения пересказа: {e}")
        
        return None
    
    def _read_short_summary(self) -> Optional[str]:
        """Читает краткую сводку"""
        short_summary_files = list(self.pipeline_path.glob("*_short_summary.txt"))
        
        if short_summary_files:
            try:
                with open(short_summary_files[0], 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"⚠️  Ошибка чтения краткой сводки: {e}")
        
        return None
    
    def _extract_book_info(self, pipeline_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Извлекает информацию о книге из названия пайплайна
        
        Args:
            pipeline_name: Название пайплайна
            
        Returns:
            Кортеж (название_книги, автор, диапазон_страниц)
        """
        book_title = None
        book_author = None
        page_range = None
        
        # Ищем диапазон страниц в конце названия
        page_match = re.search(r'_(\d+)_(\d+)$', pipeline_name)
        if page_match:
            start_page, end_page = page_match.groups()
            page_range = f"{start_page}-{end_page}"
            # Убираем диапазон страниц из названия для дальнейшего анализа
            pipeline_name = pipeline_name[:page_match.start()]
        
        # Пытаемся извлечь название книги и автора из оставшейся части
        # Формат может быть разным, например:
        # pipeline_LemEng_87_111 -> LemEng
        # pipeline_Gantrip_G_-_Shizoidnye_yavlenia_obektnye_otnoshenia_i_samost_61_90
        
        # Убираем префикс "pipeline_"
        if pipeline_name.startswith("pipeline_"):
            pipeline_name = pipeline_name[9:]  # убираем "pipeline_"
        
        # Если есть подчеркивания, пытаемся разделить на части
        parts = pipeline_name.split('_')
        
        if len(parts) >= 2:
            # Первая часть может быть автором или частью названия
            potential_author = parts[0]
            
            # Если вторая часть начинается с заглавной буквы, это может быть название
            if len(parts) > 1 and parts[1][0].isupper():
                book_title = ' '.join(parts[1:])
                book_author = potential_author
            else:
                # Иначе вся строка может быть названием
                book_title = ' '.join(parts)
        
        return book_title, book_author, page_range
    
    def get_available_thumbnails(self) -> List[Path]:
        """Получает список доступных превью"""
        images_dir = self.pipeline_path / "images"
        
        if not images_dir.exists():
            return []
        
        # Ищем изображения, которые могут служить превью
        thumbnail_extensions = ['.png', '.jpg', '.jpeg', '.webp']
        thumbnails = []
        
        for ext in thumbnail_extensions:
            thumbnails.extend(images_dir.glob(f"*{ext}"))
        
        return sorted(thumbnails)
    
    def suggest_title(self, max_length: int = 100) -> str:
        """
        Предлагает название для видео на основе метаданных
        
        Args:
            max_length: Максимальная длина названия
            
        Returns:
            Предлагаемое название
        """
        if not self.metadata:
            return "Видео из пайплайна"
        
        # Если есть название книги, используем его
        if self.metadata.book_title:
            title = self.metadata.book_title
            if self.metadata.book_author:
                title = f"{self.metadata.book_author} - {title}"
        else:
            # Используем название пайплайна
            title = self.metadata.pipeline_name.replace('_', ' ').title()
        
        # Обрезаем до максимальной длины
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        return title
    
    def suggest_description(self, max_length: int = 5000) -> str:
        """
        Предлагает описание для видео
        
        Args:
            max_length: Максимальная длина описания
            
        Returns:
            Предлагаемое описание
        """
        if not self.metadata:
            return ""
        
        # Используем промо-описание если есть
        if self.metadata.promo_description:
            description = self.metadata.promo_description
        elif self.metadata.short_summary:
            description = self.metadata.short_summary
        elif self.metadata.summary_text:
            description = self.metadata.summary_text
        else:
            description = "Видео создано из пайплайна обработки текста."
        
        # Обрезаем до максимальной длины
        if len(description) > max_length:
            description = description[:max_length-3] + "..."
        
        return description
    
    def suggest_tags(self, max_tags: int = 15) -> List[str]:
        """
        Предлагает теги для видео
        
        Args:
            max_tags: Максимальное количество тегов
            
        Returns:
            Список предлагаемых тегов
        """
        if not self.metadata:
            return []
        
        tags = []
        
        # Добавляем теги на основе названия книги
        if self.metadata.book_title:
            # Разбиваем название на слова и добавляем как теги
            words = re.findall(r'\b\w+\b', self.metadata.book_title.lower())
            tags.extend([word for word in words if len(word) > 3])
        
        # Добавляем теги на основе автора
        if self.metadata.book_author:
            tags.append(self.metadata.book_author.lower())
        
        # Добавляем общие теги
        general_tags = [
            "аудиокнига", "пересказ", "образование", "наука", 
            "философия", "литература", "анализ", "обзор"
        ]
        tags.extend(general_tags)
        
        # Убираем дубликаты и ограничиваем количество
        unique_tags = []
        for tag in tags:
            if tag and tag not in unique_tags and len(tag) > 2:
                unique_tags.append(tag)
        
        return unique_tags[:max_tags]
    
    def get_summary(self) -> str:
        """Получает краткую сводку о пайплайне"""
        if not self.metadata:
            return "Пайплайн не проанализирован"
        
        summary_parts = []
        
        summary_parts.append(f"📁 Пайплайн: {self.metadata.pipeline_name}")
        
        if self.metadata.book_title:
            summary_parts.append(f"📚 Книга: {self.metadata.book_title}")
            if self.metadata.book_author:
                summary_parts.append(f"👤 Автор: {self.metadata.book_author}")
        
        if self.metadata.page_range:
            summary_parts.append(f"📄 Страницы: {self.metadata.page_range}")
        
        summary_parts.append(f"🎬 Видео: {'✅' if self.metadata.has_video() else '❌'}")
        summary_parts.append(f"📝 Промо-описание: {'✅' if self.metadata.has_promo_description() else '❌'}")
        summary_parts.append(f"🖼️  Иллюстрации: {'✅' if self.metadata.has_illustrations() else '❌'}")
        
        if self.metadata.has_illustrations():
            summary_parts.append(f"   Количество: {len(self.metadata.illustrations)}")
        
        return "\n".join(summary_parts)
