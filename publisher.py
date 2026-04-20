#!/usr/bin/env python3
"""
Основной скрипт для публикации видео на видеохостинги
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent))

from publishers.base_publisher import VideoMetadata
from publishers.pipeline_analyzer import PipelineAnalyzer
from publishers.llm_metadata_generator import LLMMetadataGenerator
from publishers.vk_publisher import VKPublisher

# YouTube публикатор пока не реализован
# from publishers.youtube_publisher import YouTubePublisher


class VideoPublisher:
    """Основной класс для публикации видео"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Инициализация публикатора
        
        Args:
            config_file: Путь к файлу конфигурации .env
        """
        self.config_file = config_file
        self.pipeline_analyzer = None
        self.llm_generator = None
        self.publishers = {}
        
    def setup_publishers(self, platforms: List[str]) -> bool:
        """
        Настраивает публикаторы для указанных платформ
        
        Args:
            platforms: Список платформ для публикации
            
        Returns:
            True если настройка успешна
        """
        success = True
        
        for platform in platforms:
            try:
                if platform.lower() == 'youtube':
                    publisher = YouTubePublisher(self.config_file)
                    if publisher.authenticate():
                        self.publishers[platform] = publisher
                        print(f"✅ Публикатор {platform} настроен успешно")
                    else:
                        print(f"❌ Ошибка настройки публикатора {platform}")
                        success = False
                elif platform.lower() == 'vk':
                    publisher = VKPublisher(self.config_file)
                    if publisher.authenticate():
                        self.publishers[platform] = publisher
                        print(f"✅ Публикатор {platform} настроен успешно")
                    else:
                        print(f"❌ Ошибка настройки публикатора {platform}")
                        success = False
                else:
                    print(f"⚠️  Платформа {platform} пока не поддерживается")
                    
            except Exception as e:
                print(f"❌ Ошибка инициализации публикатора {platform}: {e}")
                success = False
        
        return success
    
    def analyze_pipeline(self, pipeline_path: str) -> bool:
        """
        Анализирует пайплайн
        
        Args:
            pipeline_path: Путь к пайплайну
            
        Returns:
            True если анализ успешен
        """
        try:
            self.pipeline_analyzer = PipelineAnalyzer(pipeline_path)
            self.pipeline_analyzer.analyze()
            
            print("📊 Анализ пайплайна:")
            print(self.pipeline_analyzer.get_summary())
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка анализа пайплайна: {e}")
            return False
    
    def generate_metadata(self, use_llm: bool = True, 
                         custom_title: Optional[str] = None,
                         custom_description: Optional[str] = None,
                         custom_tags: Optional[List[str]] = None) -> VideoMetadata:
        """
        Генерирует метаданные для видео
        
        Args:
            use_llm: Использовать ли LLM для генерации названия и тегов
            custom_title: Пользовательское название
            custom_description: Пользовательское описание
            custom_tags: Пользовательские теги
            
        Returns:
            Метаданные видео
            
        Note:
            Описание видео берётся напрямую из promo_description.txt (если есть),
            а НЕ генерируется через LLM — чтобы сохранить подготовленный текст.
        """
        if not self.pipeline_analyzer:
            raise ValueError("Пайплайн не проанализирован")
        
        metadata = self.pipeline_analyzer.metadata
        
        # Определяем название (LLM)
        if custom_title:
            title = custom_title
        elif use_llm and metadata.promo_description:
            try:
                if not self.llm_generator:
                    self.llm_generator = LLMMetadataGenerator(self.config_file)
                title = self.llm_generator.generate_title(
                    metadata.promo_description,
                    metadata.book_title,
                    metadata.book_author
                )
            except Exception as e:
                print(f"⚠️  Ошибка генерации названия через LLM: {e}")
                title = self.pipeline_analyzer.suggest_title()
        else:
            title = self.pipeline_analyzer.suggest_title()
        
        # Определяем описание — используем promo_description напрямую!
        if custom_description:
            description = custom_description
        elif metadata.promo_description:
            description = metadata.promo_description
        else:
            # Fallback: LLM или suggest
            if use_llm:
                try:
                    if not self.llm_generator:
                        self.llm_generator = LLMMetadataGenerator(self.config_file)
                    description = self.llm_generator.generate_description(
                        metadata.book_title or '',
                        metadata.book_title,
                        metadata.book_author
                    )
                except Exception as e:
                    print(f"⚠️  Ошибка генерации описания через LLM: {e}")
                    description = self.pipeline_analyzer.suggest_description()
            else:
                description = self.pipeline_analyzer.suggest_description()
        
        # Определяем теги (LLM)
        if custom_tags:
            tags = custom_tags
        elif use_llm and metadata.promo_description:
            try:
                if not self.llm_generator:
                    self.llm_generator = LLMMetadataGenerator(self.config_file)
                tags = self.llm_generator.generate_tags(
                    metadata.promo_description,
                    metadata.book_title,
                    metadata.book_author
                )
            except Exception as e:
                print(f"⚠️  Ошибка генерации тегов через LLM: {e}")
                tags = self.pipeline_analyzer.suggest_tags()
        else:
            tags = self.pipeline_analyzer.suggest_tags()
        
        # Выбираем превью
        thumbnails = self.pipeline_analyzer.get_available_thumbnails()
        thumbnail_path = str(thumbnails[0]) if thumbnails else None
        
        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            video_path=metadata.video_path,
            thumbnail_path=thumbnail_path,
            privacy="private"  # По умолчанию приватное
        )
    
    def publish_video(self, metadata: VideoMetadata, platforms: List[str]) -> Dict[str, Any]:
        """
        Публикует видео на указанных платформах
        
        Args:
            metadata: Метаданные видео
            platforms: Список платформ
            
        Returns:
            Результаты публикации
        """
        results = {}
        
        for platform in platforms:
            if platform not in self.publishers:
                results[platform] = {'error': 'Публикатор не настроен'}
                continue
            
            try:
                publisher = self.publishers[platform]
                
                # Для VK проверяем наличие аудио и видео файлов
                if platform.lower() == 'vk':
                    audio_path = metadata.video_path.replace('video.mp4', 'audio.mp3')
                    video_path = metadata.video_path
                    
                    has_audio = Path(audio_path).exists()
                    has_video = Path(video_path).exists()
                    
                    if has_audio and has_video:
                        # Загружаем и видео, и аудио
                        upload_results = publisher.upload_both(metadata)
                        results[platform] = {
                            'success': True,
                            'video_id': upload_results['video_id'],
                            'audio_id': upload_results['audio_id'],
                            'video_url': self._get_video_url(platform, upload_results['video_id']) if upload_results['video_id'] else None,
                            'audio_url': self._get_audio_url(platform, upload_results['audio_id']) if upload_results['audio_id'] else None
                        }
                    elif has_video:
                        # Загружаем только видео
                        video_id = publisher.upload_video(metadata)
                        results[platform] = {
                            'success': True,
                            'video_id': video_id,
                            'video_url': self._get_video_url(platform, video_id) if video_id else None
                        }
                    elif has_audio:
                        # Загружаем только аудио
                        audio_id = publisher.upload_audio(metadata)
                        results[platform] = {
                            'success': True,
                            'audio_id': audio_id,
                            'audio_url': self._get_audio_url(platform, audio_id) if audio_id else None
                        }
                    else:
                        results[platform] = {'error': 'Не найдены файлы audio.mp3 или video.mp4'}
                else:
                    # Для других платформ используем стандартную загрузку
                    video_id = publisher.upload_video(metadata)
                    
                    if video_id:
                        results[platform] = {
                            'success': True,
                            'video_id': video_id,
                            'url': self._get_video_url(platform, video_id)
                        }
                    else:
                        results[platform] = {'error': 'Ошибка загрузки видео'}
                    
            except Exception as e:
                results[platform] = {'error': str(e)}
        
        return results
    
    def _get_video_url(self, platform: str, video_id: str) -> str:
        """
        Получает URL видео на платформе
        
        Args:
            platform: Название платформы
            video_id: ID видео
            
        Returns:
            URL видео
        """
        if platform.lower() == 'youtube':
            return f"https://www.youtube.com/watch?v={video_id}"
        elif platform.lower() == 'vk':
            return f"https://vk.com/video{video_id}"
        else:
            return f"https://{platform}.com/video/{video_id}"
    
    def _get_audio_url(self, platform: str, audio_id: str) -> str:
        """
        Получает URL аудио на платформе
        
        Args:
            platform: Название платформы
            audio_id: ID аудио
            
        Returns:
            URL аудио
        """
        if platform.lower() == 'vk':
            return f"https://vk.com/audio{audio_id}"
        else:
            return f"https://{platform}.com/audio/{audio_id}"
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """
        Сохраняет результаты публикации
        
        Args:
            results: Результаты публикации
            output_file: Путь к файлу для сохранения
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"📄 Результаты сохранены в {output_file}")
        except Exception as e:
            print(f"⚠️  Ошибка сохранения результатов: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Публикация видео на видеохостинги",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python publisher.py pipeline_LemEng_87_111 --platforms youtube
  python publisher.py pipeline_LemEng_87_111 --platforms vk
  python publisher.py pipeline_LemEng_87_111 --platforms youtube vk
  python publisher.py pipeline_LemEng_87_111 --platforms youtube --title "Мое видео"
  python publisher.py pipeline_LemEng_87_111 --platforms youtube --no-llm
  python publisher.py pipeline_LemEng_87_111 --platforms youtube --privacy public
        """
    )
    
    parser.add_argument('pipeline_path', help='Путь к пайплайну')
    parser.add_argument('--platforms', nargs='+', default=['youtube'], 
                       help='Платформы для публикации')
    parser.add_argument('--config', help='Файл конфигурации .env')
    parser.add_argument('--title', help='Пользовательское название видео')
    parser.add_argument('--description', help='Пользовательское описание')
    parser.add_argument('--tags', nargs='+', help='Пользовательские теги')
    parser.add_argument('--privacy', choices=['private', 'unlisted', 'public'], 
                       default='private', help='Приватность видео')
    parser.add_argument('--no-llm', action='store_true', 
                       help='Не использовать LLM для генерации метаданных')
    parser.add_argument('--output', help='Файл для сохранения результатов')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Только анализ без публикации')
    
    args = parser.parse_args()
    
    # Проверяем путь к пайплайну
    if not Path(args.pipeline_path).exists():
        print(f"❌ Ошибка: Пайплайн не найден: {args.pipeline_path}")
        return 1
    
    # Определяем файл конфигурации
    config_file = args.config
    if not config_file:
        # Ищем config.publisher.env в текущей директории
        default_config = Path('config.publisher.env')
        if default_config.exists():
            config_file = str(default_config)
        else:
            # Ищем в директории скрипта
            script_dir = Path(__file__).parent
            script_config = script_dir / 'config.publisher.env'
            if script_config.exists():
                config_file = str(script_config)
    
    try:
        # Создаем публикатор
        publisher = VideoPublisher(config_file)
        
        # Анализируем пайплайн
        print("🔍 Анализ пайплайна...")
        if not publisher.analyze_pipeline(args.pipeline_path):
            return 1
        
        # Настраиваем публикаторы
        print(f"\n🔧 Настройка публикаторов для: {', '.join(args.platforms)}")
        if not publisher.setup_publishers(args.platforms):
            print("❌ Ошибка настройки публикаторов")
            return 1
        
        # Генерируем метаданные
        print("\n📝 Генерация метаданных...")
        metadata = publisher.generate_metadata(
            use_llm=not args.no_llm,
            custom_title=args.title,
            custom_description=args.description,
            custom_tags=args.tags
        )
        
        # Устанавливаем приватность
        metadata.privacy = args.privacy
        
        # Выводим метаданные
        print("\n📋 Метаданные видео:")
        print(f"Название: {metadata.title}")
        print(f"Описание: {metadata.description[:200]}...")
        print(f"Теги: {', '.join(metadata.tags[:10])}")
        print(f"Приватность: {metadata.privacy}")
        print(f"Видео: {metadata.video_path}")
        if metadata.thumbnail_path:
            print(f"Превью: {metadata.thumbnail_path}")
        
        # Если это пробный запуск, завершаем
        if args.dry_run:
            print("\n✅ Пробный запуск завершен")
            return 0
        
        # Публикуем видео
        print(f"\n🚀 Публикация на платформах: {', '.join(args.platforms)}")
        results = publisher.publish_video(metadata, args.platforms)
        
        # Выводим результаты
        print("\n📊 Результаты публикации:")
        for platform, result in results.items():
            if 'error' in result:
                print(f"❌ {platform}: {result['error']}")
            else:
                if platform.lower() == 'vk':
                    if 'video_url' in result and result['video_url']:
                        print(f"✅ {platform} видео: {result['video_url']}")
                    if 'audio_url' in result and result['audio_url']:
                        print(f"✅ {platform} аудио: {result['audio_url']}")
                else:
                    print(f"✅ {platform}: {result['url']}")
        
        # Сохраняем результаты
        if args.output:
            publisher.save_results(results, args.output)
        
        return 0
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
