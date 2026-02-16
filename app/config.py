"""
配置管理模块

从环境变量加载配置，提供配置访问接口。
支持 LLM API、数据库、Redis 等配置。
"""

import os
from typing import Optional, Dict, Any
from functools import lru_cache

from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()


class Config:
    """应用配置类"""

    def __init__(self):
        """初始化配置，从环境变量加载所有配置项"""
        # LLM 配置 - Anthropic Claude
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

        # LLM 配置 - OpenAI
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")

        # 数据库配置
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/stock_db"
        )

        # Redis 配置
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # 股票数据 API
        self.tushare_token: Optional[str] = os.getenv("TUSHARE_TOKEN")

        # 应用配置
        self.debug: bool = os.getenv("DEBUG", "true").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

        # 认证配置
        self.access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值或默认值
        """
        return getattr(self, key, default)

    def has_anthropic_key(self) -> bool:
        """检查是否配置了 Anthropic API 密钥"""
        return bool(self.anthropic_api_key)

    def has_openai_key(self) -> bool:
        """检查是否配置了 OpenAI API 密钥"""
        return bool(self.openai_api_key)

    def has_llm_provider(self) -> bool:
        """检查是否配置了至少一个 LLM 提供者"""
        return self.has_anthropic_key() or self.has_openai_key()

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典（隐藏敏感信息）"""
        config_dict = {}
        sensitive_keys = {"anthropic_api_key", "openai_api_key", "tushare_token", "secret_key"}

        for key, value in self.__dict__.items():
            if key in sensitive_keys and value:
                config_dict[key] = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            else:
                config_dict[key] = value

        return config_dict


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取全局配置实例（单例模式）

    Returns:
        配置实例
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """
    重新加载配置

    Returns:
        新的配置实例
    """
    global _config
    _config = Config()
    return _config


# 便捷访问函数
@lru_cache()
def get_anthropic_api_key() -> Optional[str]:
    """获取 Anthropic API 密钥"""
    return os.getenv("ANTHROPIC_API_KEY")


@lru_cache()
def get_openai_api_key() -> Optional[str]:
    """获取 OpenAI API 密钥"""
    return os.getenv("OPENAI_API_KEY")


@lru_cache()
def get_anthropic_model() -> str:
    """获取 Anthropic 模型名称"""
    return os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")


@lru_cache()
def get_openai_model() -> str:
    """获取 OpenAI 模型名称"""
    return os.getenv("OPENAI_MODEL", "gpt-4-turbo")
