#!/usr/bin/env python3
"""
Базовый класс для публикации видео на видеохостинги
"""

import os
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class VideoMetadata:
    """Метаданные видео для публикации"""
    title: str
    description: str
    tags: List[str]
    category: Optional[str] = None
    privacy: str = "private"  # private, unlisted, public
    thumbnail_path: Optional[str] = None
    video_path: str = ""
    duration: Optional[int] = None  # в секундах
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует метаданные в словарь"""
        return {
            'title': self.title,
            'description': self.description,
            'tags': self.tags,
            'category': self.category,
            'privacy': self.privacy,
            'thumbnail_path': self.thumbnail_path,
            'video_path': self.video_path,
            'duration': self.duration
        }


class BasePublisher(ABC):
    """Базовый класс для публикации видео"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Инициализация издателя
        
        Args:
            config_file: Путь к файлу конфигурации .env
        """
        self.config_file = config_file
        self.load_config()
        
    def load_config(self):
        """Загружает конфигурацию из файла"""
        if self.config_file and Path(self.config_file).exists():
            from dotenv import load_dotenv
            load_dotenv(self.config_file)
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Аутентификация на платформе
        
        Returns:
            True если аутентификация успешна
        """
        pass
    
    @abstractmethod
    def upload_video(self, metadata: VideoMetadata) -> Optional[str]:
        """
        Загружает видео на платформу
        
        Args:
            metadata: Метаданные видео
            
        Returns:
            ID загруженного видео или None при ошибке
        """
        pass
    
    @abstractmethod
    def update_video_metadata(self, video_id: str, metadata: VideoMetadata) -> bool:
        """
        Обновляет метаданные уже загруженного видео
        
        Args:
            video_id: ID видео
            metadata: Новые метаданные
            
        Returns:
            True если обновление успешно
        """
        pass
    
    @abstractmethod
    def get_upload_status(self, video_id: str) -> Dict[str, Any]:
        """
        Получает статус загрузки видео
        
        Args:
            video_id: ID видео
            
        Returns:
            Словарь со статусом загрузки
        """
        pass
    
    def validate_metadata(self, metadata: VideoMetadata) -> List[str]:
        """
        Валидирует метаданные видео
        
        Args:
            metadata: Метаданные для проверки
            
        Returns:
            Список ошибок валидации
        """
        errors = []
        
        if not metadata.title or len(metadata.title.strip()) == 0:
            errors.append("Название видео не может быть пустым")
        
        if not metadata.description or len(metadata.description.strip()) == 0:
            errors.append("Описание видео не может быть пустым")
        
        if not metadata.video_path or not Path(metadata.video_path).exists():
            errors.append("Файл видео не найден")
        
        if metadata.thumbnail_path and not Path(metadata.thumbnail_path).exists():
            errors.append("Файл превью не найден")
        
        return errors
    
    def prepare_tags(self, tags: List[str], max_tags: int = 10) -> List[str]:
        """
        Подготавливает теги для публикации
        
        Args:
            tags: Исходные теги
            max_tags: Максимальное количество тегов
            
        Returns:
            Обработанные теги
        """
        if not tags:
            return []
        
        # Убираем пустые теги и ограничиваем длину
        processed_tags = []
        for tag in tags:
            if tag and tag.strip():
                tag = tag.strip()[:50]  # Ограничиваем длину тега
                if tag not in processed_tags:
                    processed_tags.append(tag)
        
        return processed_tags[:max_tags]
    
    def truncate_text(self, text: str, max_length: int) -> str:
        """
        Обрезает текст до максимальной длины
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина
            
        Returns:
            Обрезанный текст
        """
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        # Обрезаем до последнего пробела перед максимальной длиной
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # Если пробел не слишком далеко
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."
    
    def get_video_duration(self, video_path: str) -> Optional[int]:
        """
        Получает длительность видео в секундах
        
        Args:
            video_path: Путь к видеофайлу
            
        Returns:
            Длительность в секундах или None
        """
        try:
            import subprocess
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'csv=p=0', video_path
            ], capture_output=True, text=True, check=True)
            
            duration = float(result.stdout.strip())
            return int(duration)
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
            return None
    
    def log_info(self, message: str):
        """Логирует информационное сообщение"""
        print(f"ℹ️  {message}")
    
    def log_success(self, message: str):
        """Логирует сообщение об успехе"""
        print(f"✅ {message}")
    
    def log_error(self, message: str):
        """Логирует сообщение об ошибке"""
        print(f"❌ {message}")
    
    def log_warning(self, message: str):
        """Логирует предупреждение"""
        print(f"⚠️  {message}")
