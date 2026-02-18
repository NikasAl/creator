# Utils package
# Унифицированные утилиты для всего проекта

from .text_splitter import (
    split_text_into_chunks,
    split_by_sentences,
    get_chunk_stats,
    SplitConfig,
    PRESETS as SPLIT_PRESETS,
)

from .config_loader import (
    ConfigLoader,
    ModelConfig,
    get_config,
)

from .openrouter_client import (
    OpenRouterClient,
    ChatMessage,
    ChatResponse,
    get_client,
)

from .base_processor import (
    BaseProcessor,
    ProcessingReport,
    create_arg_parser,
)

__all__ = [
    # Text splitting
    'split_text_into_chunks',
    'split_by_sentences',
    'get_chunk_stats',
    'SplitConfig',
    'SPLIT_PRESETS',
    
    # Configuration
    'ConfigLoader',
    'ModelConfig',
    'get_config',
    
    # OpenRouter API
    'OpenRouterClient',
    'ChatMessage',
    'ChatResponse',
    'get_client',
    
    # Base processor
    'BaseProcessor',
    'ProcessingReport',
    'create_arg_parser',
]
