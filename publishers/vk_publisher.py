#!/usr/bin/env python3
"""
Публикатор для VK Video и VK Audio
"""

import os
import json
import requests
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlencode

from .base_publisher import BasePublisher, VideoMetadata


class VKPublisher(BasePublisher):
    """Публикатор для VK Video и VK Audio"""
    
    # VK API версия
    API_VERSION = "5.131"
    
    # Базовые URL для VK API
    API_BASE_URL = "https://api.vk.com/method"
    OAUTH_BASE_URL = "https://oauth.vk.com"
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Инициализация VK публикатора
        
        Args:
            config_file: Путь к файлу конфигурации .env
        """
        super().__init__(config_file)
        self.client_id = os.getenv('VK_CLIENT_ID', '52506614')
        self.client_secret = os.getenv('VK_CLIENT_SECRET', '')  # Не требуется для плагин-приложений
        self.access_token = os.getenv('VK_ACCESS_TOKEN', '')
        self.group_id = os.getenv('VK_GROUP_ID', '')  # ID группы для публикации
        self.token_file = os.getenv('VK_TOKEN_PATH', 'vk_token.json')
        
        # Загружаем токен из файла если есть
        self._load_token()
        
    def _load_token(self):
        """Загружает токен из файла"""
        if Path(self.token_file).exists():
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get('access_token', '')
                    self.group_id = token_data.get('group_id', '')
            except Exception as e:
                self.log_warning(f"Ошибка загрузки токена VK: {e}")
    
    def _save_token(self):
        """Сохраняет токен в файл"""
        try:
            token_data = {
                'access_token': self.access_token,
                'group_id': self.group_id,
                'timestamp': time.time()
            }
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_warning(f"Ошибка сохранения токена VK: {e}")
    
    def authenticate(self) -> bool:
        """
        Аутентификация на VK
        
        Returns:
            True если аутентификация успешна
        """
        try:
            if not self.access_token:
                self.log_error("Токен доступа VK не найден")
                self.log_info("Получите токен доступа через VK API или установите VK_ACCESS_TOKEN в конфигурации")
                self.log_info("Для плагин-приложений используйте: python setup_vk_auth.py")
                return False
            
            # Проверяем токен
            if not self._check_token_validity():
                self.log_error("Токен доступа VK недействителен или истек")
                self.log_info("Обновите токен через: python setup_vk_auth.py")
                return False
            
            # Получаем информацию о пользователе
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION
            }
            
            response = requests.get(f"{self.API_BASE_URL}/users.get", params=params)
            data = response.json()
            
            if 'error' in data:
                self.log_error(f"Ошибка VK API: {data['error']['error_msg']}")
                return False
            
            if 'response' in data and len(data['response']) > 0:
                user = data['response'][0]
                self.log_success(f"Аутентификация VK успешна. Пользователь: {user['first_name']} {user['last_name']}")
                return True
            else:
                self.log_error("Не удалось получить информацию о пользователе")
                return False
                
        except Exception as e:
            self.log_error(f"Ошибка аутентификации VK: {e}")
            return False
    
    def _check_token_validity(self) -> bool:
        """
        Проверяет валидность токена
        
        Returns:
            True если токен валиден
        """
        try:
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION
            }
            
            response = requests.get(f"{self.API_BASE_URL}/users.get", params=params)
            data = response.json()
            
            if 'error' in data:
                error_code = data['error'].get('error_code', 0)
                if error_code in [5, 27]:  # Invalid token или Access denied
                    return False
                return True  # Другие ошибки не связаны с токеном
            
            return 'response' in data and len(data['response']) > 0
            
        except Exception:
            return False
    
    def upload_video(self, metadata: VideoMetadata) -> Optional[str]:
        """
        Загружает видео на VK Video
        
        Args:
            metadata: Метаданные видео
            
        Returns:
            ID загруженного видео или None при ошибке
        """
        if not self.access_token:
            self.log_error("Токен доступа VK не найден")
            return None
        
        # Валидируем метаданные
        errors = self.validate_metadata(metadata)
        if errors:
            for error in errors:
                self.log_error(error)
            return None
        
        try:
            # Получаем адрес сервера для загрузки
            upload_url = self._get_video_upload_url()
            if not upload_url:
                return None
            
            # Загружаем видео файл
            video_id = self._upload_video_file(upload_url, metadata.video_path)
            if not video_id:
                return None
            
            # Сохраняем видео
            saved_video_id = self._save_video(video_id, metadata)
            if not saved_video_id:
                return None
            
            # Публикуем в группу если указана (отключено для плагин-приложений)
            if self.group_id:
                self.log_warning("Публикация в группу недоступна для плагин-приложений VK")
                self.log_info("Используйте Standalone-приложение для публикации в группу")
                # post_id = self._publish_to_group(saved_video_id, metadata)
                # if post_id:
                #     self.log_success(f"Видео опубликовано в группу. Пост ID: {post_id}")
            
            return saved_video_id
            
        except Exception as e:
            self.log_error(f"Неожиданная ошибка при загрузке видео: {e}")
            return None
    
    def upload_audio(self, metadata: VideoMetadata) -> Optional[str]:
        """
        Загружает аудио на VK Audio
        
        Args:
            metadata: Метаданные аудио (используем video_path для аудиофайла)
            
        Returns:
            ID загруженного аудио или None при ошибке
        """
        # Плагин-приложения VK не поддерживают загрузку аудио через API
        self.log_warning("Загрузка аудио в VK недоступна для плагин-приложений")
        self.log_info("Используйте Standalone-приложение для загрузки аудио или загружайте только видео")
        return None
    
    def upload_both(self, metadata: VideoMetadata) -> Dict[str, Optional[str]]:
        """
        Загружает и видео, и аудио
        
        Args:
            metadata: Метаданные
            
        Returns:
            Словарь с ID видео и аудио
        """
        results = {
            'video_id': None,
            'audio_id': None
        }
        
        # Загружаем видео
        video_id = self.upload_video(metadata)
        results['video_id'] = video_id
        
        # Загружаем аудио (отключено для плагин-приложений)
        audio_id = self.upload_audio(metadata)
        results['audio_id'] = audio_id
        
        return results
    
    def _get_video_upload_url(self) -> Optional[str]:
        """Получает URL для загрузки видео"""
        try:
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION,
                'group_id': self.group_id if self.group_id else None
            }
            
            # Убираем None значения
            params = {k: v for k, v in params.items() if v is not None}
            
            response = requests.get(f"{self.API_BASE_URL}/video.save", params=params)
            data = response.json()
            
            if 'error' in data:
                self.log_error(f"Ошибка получения URL загрузки видео: {data['error']['error_msg']}")
                return None
            
            if 'response' in data and 'upload_url' in data['response']:
                return data['response']['upload_url']
            else:
                self.log_error("Не удалось получить URL загрузки видео")
                return None
                
        except Exception as e:
            self.log_error(f"Ошибка получения URL загрузки видео: {e}")
            return None
    
    def _get_audio_upload_url(self) -> Optional[str]:
        """Получает URL для загрузки аудио"""
        try:
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION
            }
            
            response = requests.get(f"{self.API_BASE_URL}/audio.getUploadServer", params=params)
            data = response.json()
            
            if 'error' in data:
                self.log_error(f"Ошибка получения URL загрузки аудио: {data['error']['error_msg']}")
                return None
            
            if 'response' in data and 'upload_url' in data['response']:
                return data['response']['upload_url']
            else:
                self.log_error("Не удалось получить URL загрузки аудио")
                return None
                
        except Exception as e:
            self.log_error(f"Ошибка получения URL загрузки аудио: {e}")
            return None
    
    def _upload_video_file(self, upload_url: str, video_path: str) -> Optional[str]:
        """Загружает видео файл"""
        try:
            with open(video_path, 'rb') as f:
                files = {'video_file': f}  # Правильное имя поля для VK API
                response = requests.post(upload_url, files=files)
            
            data = response.json()
            
            if 'error' in data:
                self.log_error(f"Ошибка загрузки видео файла: {data['error']['error_msg']}")
                return None
            
            if 'video_id' in data:
                return str(data['video_id'])
            elif 'video_hash' in data and 'video_id' in data:
                # Сервер может вернуть video_hash и video_id
                return str(data['video_id'])
            else:
                self.log_error("Не удалось получить ID загруженного видео")
                self.log_error(f"Ответ сервера: {data}")
                return None
                
        except Exception as e:
            self.log_error(f"Ошибка загрузки видео файла: {e}")
            return None
    
    def _upload_audio_file(self, upload_url: str, audio_path: str, metadata: VideoMetadata) -> Optional[str]:
        """Загружает аудио файл"""
        try:
            with open(audio_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(upload_url, files=files)
            
            data = response.json()
            
            if 'error' in data:
                self.log_error(f"Ошибка загрузки аудио файла: {data['error']['error_msg']}")
                return None
            
            if 'audio' in data and 'id' in data['audio']:
                return str(data['audio']['id'])
            else:
                self.log_error("Не удалось получить ID загруженного аудио")
                return None
                
        except Exception as e:
            self.log_error(f"Ошибка загрузки аудио файла: {e}")
            return None
    
    def _save_video(self, video_id: str, metadata: VideoMetadata) -> Optional[str]:
        """Сохраняет видео с метаданными"""
        try:
            # Используем video.edit для обновления метаданных
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION,
                'video_id': video_id,
                'name': self.truncate_text(metadata.title, 128),
                'description': self.truncate_text(metadata.description, 2048),
                'is_private': 1 if metadata.privacy == 'private' else 0
            }
            
            # Добавляем owner_id если это видео группы
            if self.group_id:
                params['owner_id'] = f"-{self.group_id}"
            
            response = requests.post(f"{self.API_BASE_URL}/video.edit", data=params)
            
            if not response.text:
                self.log_error("Пустой ответ от сервера при сохранении видео")
                return None
                
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                self.log_error(f"Ошибка парсинга JSON ответа: {e}")
                self.log_error(f"Ответ сервера: {response.text}")
                return None
            
            if 'error' in data:
                self.log_error(f"Ошибка сохранения видео: {data['error']['error_msg']}")
                return None
            
            if 'response' in data and data['response'] == 1:
                self.log_success(f"Видео сохранено. ID: {video_id}")
                return str(video_id)
            else:
                self.log_error("Не удалось сохранить видео")
                self.log_error(f"Ответ API: {data}")
                return None
                
        except Exception as e:
            self.log_error(f"Ошибка сохранения видео: {e}")
            return None
    
    def _publish_to_group(self, video_id: str, metadata: VideoMetadata) -> Optional[str]:
        """Публикует видео в группу"""
        try:
            # Формируем текст поста
            post_text = f"{metadata.title}\n\n{metadata.description}"
            
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION,
                'owner_id': f"-{self.group_id}",
                'message': self.truncate_text(post_text, 4096),
                'attachments': f"video-{self.group_id}_{video_id}",
                'from_group': 1
            }
            
            response = requests.get(f"{self.API_BASE_URL}/wall.post", params=params)
            data = response.json()
            
            if 'error' in data:
                self.log_error(f"Ошибка публикации в группу: {data['error']['error_msg']}")
                return None
            
            if 'response' in data and 'post_id' in data['response']:
                return str(data['response']['post_id'])
            else:
                self.log_error("Не удалось опубликовать в группу")
                return None
                
        except Exception as e:
            self.log_error(f"Ошибка публикации в группу: {e}")
            return None
    
    def update_video_metadata(self, video_id: str, metadata: VideoMetadata) -> bool:
        """
        Обновляет метаданные видео
        
        Args:
            video_id: ID видео
            metadata: Новые метаданные
            
        Returns:
            True если обновление успешно
        """
        try:
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION,
                'video_id': video_id,
                'name': self.truncate_text(metadata.title, 128),
                'description': self.truncate_text(metadata.description, 2048),
                'is_private': 1 if metadata.privacy == 'private' else 0
            }
            
            response = requests.get(f"{self.API_BASE_URL}/video.edit", params=params)
            data = response.json()
            
            if 'error' in data:
                self.log_error(f"Ошибка обновления метаданных видео: {data['error']['error_msg']}")
                return False
            
            if 'response' in data and data['response'] == 1:
                self.log_success(f"Метаданные видео {video_id} обновлены")
                return True
            else:
                self.log_error("Не удалось обновить метаданные видео")
                return False
                
        except Exception as e:
            self.log_error(f"Ошибка обновления метаданных видео: {e}")
            return False
    
    def get_upload_status(self, video_id: str) -> Dict[str, Any]:
        """
        Получает статус загрузки видео
        
        Args:
            video_id: ID видео
            
        Returns:
            Словарь со статусом загрузки
        """
        try:
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION,
                'videos': f"{self.group_id}_{video_id}" if self.group_id else video_id
            }
            
            response = requests.get(f"{self.API_BASE_URL}/video.get", params=params)
            data = response.json()
            
            if 'error' in data:
                return {'error': f"Ошибка VK API: {data['error']['error_msg']}"}
            
            if 'response' in data and 'items' in data['response'] and len(data['response']['items']) > 0:
                video = data['response']['items'][0]
                return {
                    'video_id': video_id,
                    'title': video.get('title', ''),
                    'description': video.get('description', ''),
                    'duration': video.get('duration', 0),
                    'views': video.get('views', 0),
                    'status': 'processed' if video.get('processing') == 0 else 'processing',
                    'error': None
                }
            else:
                return {'error': 'Видео не найдено'}
                
        except Exception as e:
            return {'error': f'Неожиданная ошибка: {e}'}
    
    def get_group_info(self) -> Dict[str, Any]:
        """
        Получает информацию о группе
        
        Returns:
            Информация о группе
        """
        if not self.group_id:
            return {}
        
        try:
            params = {
                'access_token': self.access_token,
                'v': self.API_VERSION,
                'group_id': self.group_id,
                'fields': 'name,description,members_count'
            }
            
            response = requests.get(f"{self.API_BASE_URL}/groups.getById", params=params)
            data = response.json()
            
            if 'error' in data:
                self.log_error(f"Ошибка получения информации о группе: {data['error']['error_msg']}")
                return {}
            
            if 'response' in data and len(data['response']) > 0:
                group = data['response'][0]
                return {
                    'id': group['id'],
                    'name': group['name'],
                    'description': group.get('description', ''),
                    'members_count': group.get('members_count', 0)
                }
            else:
                return {}
                
        except Exception as e:
            self.log_error(f"Ошибка получения информации о группе: {e}")
            return {}
    
    def validate_metadata(self, metadata: VideoMetadata) -> List[str]:
        """
        Валидирует метаданные для VK
        
        Args:
            metadata: Метаданные для проверки
            
        Returns:
            Список ошибок валидации
        """
        errors = super().validate_metadata(metadata)
        
        # Дополнительные проверки для VK
        if len(metadata.title) > 128:
            errors.append("Название видео не может быть длиннее 128 символов")
        
        # Проверка длины описания не нужна, так как truncate_text обрезает его автоматически
        # if len(metadata.description) > 2048:
        #     errors.append("Описание видео не может быть длиннее 2048 символов")
        
        return errors

