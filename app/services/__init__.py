"""
服务模块

提供各种业务服务：
- 股票数据服务
- LLM 服务
"""

from app.services.stock_service import (
    StockService,
    StockCache,
    get_stock_service,
    get_cache,
    clear_cache,
)

from app.services.llm_service import (
    # 数据类
    Message,
    LLMResponse,
    StreamChunk,
    # 枚举
    LLMProviderType,
    # 提供者
    LLMProvider,
    AnthropicProvider,
    OpenAIProvider,
    # 对话管理
    ConversationManager,
    # 工厂函数
    get_default_provider,
    get_conversation_manager,
    create_provider,
    reset_default_provider,
)

__all__ = [
    # Stock Service
    "StockService",
    "StockCache",
    "get_stock_service",
    "get_cache",
    "clear_cache",
    # LLM Service
    "Message",
    "LLMResponse",
    "StreamChunk",
    "LLMProviderType",
    "LLMProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "ConversationManager",
    "get_default_provider",
    "get_conversation_manager",
    "create_provider",
    "reset_default_provider",
]
