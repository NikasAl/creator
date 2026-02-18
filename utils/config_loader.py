#!/usr/bin/env python3
"""
Унифицированный загрузчик конфигурации.

Используется всеми процессорами проекта вместо дублирования кода.
Поддерживает загрузку из .env файлов с fallback и дефолтными значениями.

Использование:
    from utils.config_loader import ConfigLoader

    config = ConfigLoader('config.env')
    api_key = config.get('OPENROUTER_API_KEY')
    model = config.get('DEFAULT_MODEL', default='anthropic/claude-3.5-sonnet')
"""

import os
from pathlib import Path
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class ModelConfig:
    """Конфигурация модели LLM."""
    name: str
    max_tokens: int = 4000
    temperature: float = 0.7


# Предустановленные модели
MODEL_PRESETS = {
    'default': ModelConfig('anthropic/claude-3.5-sonnet', max_tokens=4000, temperature=0.7),
    'budget': ModelConfig('google/gemini-2.5-flash-lite', max_tokens=4000, temperature=0.7),
    'quality': ModelConfig('anthropic/claude-3.5-sonnet', max_tokens=8000, temperature=0.5),
    'fast': ModelConfig('meta-llama/llama-3.1-8b-instruct', max_tokens=4000, temperature=0.7),
}


class ConfigLoader:
    """
    Унифицированный загрузчик конфигурации.

    Заменяет дублированный код загрузки .env в 10+ файлах проекта.
    Поддерживает:
    - Загрузку из указанного файла
    - Автоматический поиск конфигурационных файлов
    - Дефолтные значения
    - Кастинг типов (int, float, bool)
    - Модели с пресетами

    Examples:
        # Простейшее использование
        config = ConfigLoader()
        api_key = config.get('OPENROUTER_API_KEY')

        # С указанным файлом
        config = ConfigLoader('config.env')

        # С дефолтным значением
        model = config.get('DEFAULT_MODEL', default='anthropic/claude-3.5-sonnet')

        # Получение модели с пресетом
        model_config = config.get_model('quality')

        # Получение всех настроек OpenRouter
        or_config = config.get_openrouter_config()
    """

    # Файлы конфигурации в порядке приоритета поиска
    DEFAULT_CONFIG_FILES = [
        'config.env',
        '.env',
        'config.local.env',
        'settings.env',
    ]

    def __init__(
        self,
        config_file: Optional[str] = None,
        auto_load: bool = True,
        defaults: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализация загрузчика.

        Args:
            config_file: Путь к файлу конфигурации (опционально)
            auto_load: Автоматически загружать конфигурацию при инициализации
            defaults: Словарь с дефолтными значениями
        """
        self._config: Dict[str, str] = {}
        self._defaults = defaults or {}
        self._loaded_from: Optional[str] = None

        if auto_load:
            self.load(config_file)

    def load(self, config_file: Optional[str] = None) -> bool:
        """
        Загружает конфигурацию из файла.

        Args:
            config_file: Путь к файлу (опционально, если None - автопоиск)

        Returns:
            True если конфигурация загружена успешно
        """
        loaded = False

        # Если указан конкретный файл
        if config_file and Path(config_file).exists():
            load_dotenv(config_file, override=True)
            self._loaded_from = config_file
            loaded = True
        else:
            # Автопоиск файла конфигурации
            for env_file in self.DEFAULT_CONFIG_FILES:
                if Path(env_file).exists():
                    load_dotenv(env_file, override=True)
                    self._loaded_from = env_file
                    loaded = True
                    break

        # Загружаем все переменные окружения в локальный кеш
        self._config = dict(os.environ)

        return loaded

    def get(
        self,
        key: str,
        default: Any = None,
        cast_type: Optional[type] = None
    ) -> Any:
        """
        Получает значение конфигурации.

        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию
            cast_type: Тип для приведения (int, float, bool, str)

        Returns:
            Значение конфигурации или дефолт
        """
        # Сначала проверяем локальный кеш
        value = self._config.get(key)

        # Затем переменные окружения
        if value is None:
            value = os.getenv(key)

        # Затем дефолты
        if value is None:
            value = self._defaults.get(key, default)

        # Если значение всё ещё None - возвращаем как есть
        if value is None:
            return None

        # Приведение типа
        if cast_type:
            try:
                if cast_type == bool:
                    if isinstance(value, str):
                        return value.lower() in ('true', '1', 'yes', 'on')
                    return bool(value)
                return cast_type(value)
            except (ValueError, TypeError):
                return default

        return value

    def get_int(self, key: str, default: int = 0) -> int:
        """Получает значение как int."""
        return self.get(key, default=default, cast_type=int)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Получает значение как float."""
        return self.get(key, default=default, cast_type=float)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Получает значение как bool."""
        return self.get(key, default=default, cast_type=bool)

    def get_list(self, key: str, default: Optional[List[str]] = None, separator: str = ',') -> List[str]:
        """
        Получает значение как список (разделённый separator).

        Пример: "model1,model2,model3" -> ['model1', 'model2', 'model3']
        """
        value = self.get(key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]

    def get_model(self, preset: str = 'default') -> ModelConfig:
        """
        Получает конфигурацию модели по пресету.

        Args:
            preset: Имя пресета ('default', 'budget', 'quality', 'fast')

        Returns:
            ModelConfig с настройками модели
        """
        if preset in MODEL_PRESETS:
            preset_config = MODEL_PRESETS[preset]
            # Переопределяем из конфига если указано
            model_name = self.get(f'{preset.upper()}_MODEL', default=preset_config.name)
            max_tokens = self.get_int(f'{preset.upper()}_MAX_TOKENS', default=preset_config.max_tokens)
            temperature = self.get_float(f'{preset.upper()}_TEMPERATURE', default=preset_config.temperature)
            return ModelConfig(model_name, max_tokens, temperature)

        # Кастомная модель
        return ModelConfig(
            name=self.get('DEFAULT_MODEL', default='anthropic/claude-3.5-sonnet'),
            max_tokens=self.get_int('DEFAULT_MAX_TOKENS', default=4000),
            temperature=self.get_float('DEFAULT_TEMPERATURE', default=0.7)
        )

    def get_openrouter_config(self) -> Dict[str, Any]:
        """
        Получает полную конфигурацию для OpenRouter API.

        Returns:
            Словарь с api_key, base_url, headers и настройками моделей
        """
        return {
            'api_key': self.get('OPENROUTER_API_KEY'),
            'base_url': self.get('OPENROUTER_BASE_URL', default='https://openrouter.ai/api/v1'),
            'default_model': self.get_model('default'),
            'budget_model': self.get_model('budget'),
            'quality_model': self.get_model('quality'),
            'headers': {
                'Content-Type': 'application/json',
                'HTTP-Referer': self.get('HTTP_REFERER', default='https://github.com/NikasAl/creator'),
                'X-Title': self.get('X_TITLE', default='Creator Video Generator'),
            }
        }

    def get_alibaba_config(self) -> Dict[str, Any]:
        """
        Получает конфигурацию для Alibaba Cloud API.

        Returns:
            Словарь с api_key, base_url и моделями
        """
        return {
            'api_key': self.get('ALIBABA_API_KEY'),
            'base_url': self.get('ALIBABA_BASE_URL', default='https://dashscope-intl.aliyuncs.com/compatible-mode/v1'),
            'video_model': self.get('ALIBABA_VIDEO_MODEL', default='wan2.1-i2v-turbo'),
            'image_model': self.get('ALIBABA_IMAGE_MODEL', default='wan2.5-t2i-preview'),
            'tts_model': self.get('ALIBABA_TTS_MODEL', default='qwen3-tts-flash'),
            'prompt_model': self.get('ALIBABA_PROMPT_MODEL', default='qwen/qwen3-30b-a3b:free'),
        }

    def get_sber_config(self) -> Dict[str, str]:
        """Получает конфигурацию для Sber API."""
        return {
            'api_key': self.get('SBER_API_KEY'),
            'client_id': self.get('SBER_CLIENT_ID'),
            'client_secret': self.get('SBER_CLIENT_SECRET'),
        }

    def get_vk_config(self) -> Dict[str, str]:
        """Получает конфигурацию для VK API."""
        return {
            'client_id': self.get('VK_CLIENT_ID'),
            'client_secret': self.get('VK_CLIENT_SECRET'),
            'access_token': self.get('VK_ACCESS_TOKEN'),
            'group_id': self.get('VK_GROUP_ID'),
        }

    def get_youtube_config(self) -> Dict[str, str]:
        """Получает конфигурацию для YouTube API."""
        return {
            'credentials_path': self.get('YOUTUBE_CREDENTIALS_PATH', default='youtube_credentials.json'),
            'token_path': self.get('YOUTUBE_TOKEN_PATH', default='youtube_token.json'),
        }

    @property
    def loaded_from(self) -> Optional[str]:
        """Возвращает путь к загруженному файлу конфигурации."""
        return self._loaded_from

    def reload(self) -> bool:
        """Перезагружает конфигурацию."""
        return self.load(self._loaded_from)

    def set(self, key: str, value: Any) -> None:
        """Устанавливает значение в локальном кеше."""
        self._config[key] = str(value)

    def as_dict(self) -> Dict[str, str]:
        """Возвращает всю конфигурацию как словарь."""
        return dict(self._config)

    def __repr__(self) -> str:
        return f"ConfigLoader(loaded_from={self._loaded_from!r})"


# Глобальный экземпляр для удобства
_global_config: Optional[ConfigLoader] = None


def get_config(config_file: Optional[str] = None, reload: bool = False) -> ConfigLoader:
    """
    Получает глобальный экземпляр конфигурации.

    Args:
        config_file: Путь к файлу (только при первом вызове или reload)
        reload: Принудительно перезагрузить

    Returns:
        Глобальный экземпляр ConfigLoader
    """
    global _global_config

    if _global_config is None or reload:
        _global_config = ConfigLoader(config_file)

    return _global_config


# === CLI интерфейс для отладки ===
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Проверка конфигурации")
    parser.add_argument("--config-file", help="Путь к файлу конфигурации")
    parser.add_argument("--key", help="Получить конкретный ключ")
    parser.add_argument("--openrouter", action="store_true", help="Показать OpenRouter конфиг")
    parser.add_argument("--alibaba", action="store_true", help="Показать Alibaba конфиг")
    parser.add_argument("--all", action="store_true", help="Показать всю конфигурацию")

    args = parser.parse_args()

    config = ConfigLoader(args.config_file)

    print(f"📁 Загружено из: {config.loaded_from or 'не найдено'}")
    print()

    if args.key:
        value = config.get(args.key)
        print(f"{args.key} = {value!r}")
    elif args.openrouter:
        or_config = config.get_openrouter_config()
        print("🔗 OpenRouter конфигурация:")
        print(json.dumps(or_config, indent=2, default=str))
    elif args.alibaba:
        alibaba_config = config.get_alibaba_config()
        print("☁️ Alibaba конфигурация:")
        print(json.dumps(alibaba_config, indent=2, default=str))
    elif args.all:
        print("📋 Вся конфигурация:")
        for key, value in sorted(config.as_dict().items()):
            # Скрываем секреты
            if any(s in key.upper() for s in ['KEY', 'SECRET', 'TOKEN', 'PASSWORD']):
                value = '***скрыто***'
            print(f"  {key} = {value!r}")
    else:
        print("Используйте --key, --openrouter, --alibaba или --all")
