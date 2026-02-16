"""
Redis 缓存服务

提供基于 Redis 的分布式缓存功能，支持：
- 缓存存储和读取
- 缓存失效策略
- 连接失败时的降级处理
"""
import json
import time
from typing import Any, Optional, Callable
from functools import wraps

import redis
from redis import RedisError

from app.config import get_config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis 缓存类"""

    def __init__(self):
        """初始化 Redis 缓存"""
        self._redis_client: Optional[redis.Redis] = None
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        """连接 Redis"""
        try:
            config = get_config()
            self._redis_client = redis.from_url(
                config.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self._redis_client.ping()
            self._connected = True
            logger.info("Redis connection established")
        except Exception as e:
            self._connected = False
            self._redis_client = None
            logger.warning(f"Redis connection failed, using fallback cache: {e}")

    def is_connected(self) -> bool:
        """检查 Redis 是否连接"""
        if not self._connected or self._redis_client is None:
            return False
        try:
            self._redis_client.ping()
            return True
        except Exception:
            self._connected = False
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期返回 None
        """
        if not self.is_connected():
            return None

        try:
            value = self._redis_client.get(key)
            if value is not None:
                logger.debug(f"Redis cache hit: {key}")
                return json.loads(value)
            return None
        except RedisError as e:
            logger.warning(f"Redis get error: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        if not self.is_connected():
            return False

        try:
            serialized = json.dumps(value, default=str)
            self._redis_client.setex(key, ttl, serialized)
            logger.debug(f"Redis cache set: {key} (TTL: {ttl}s)")
            return True
        except RedisError as e:
            logger.warning(f"Redis set error: {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.warning(f"JSON encode error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        if not self.is_connected():
            return False

        try:
            self._redis_client.delete(key)
            logger.debug(f"Redis cache deleted: {key}")
            return True
        except RedisError as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        根据模式删除缓存

        Args:
            pattern: 匹配模式（如 "quote:*"）

        Returns:
            删除的键数量
        """
        if not self.is_connected():
            return 0

        try:
            keys = self._redis_client.keys(pattern)
            if keys:
                deleted = self._redis_client.delete(*keys)
                logger.info(f"Redis cache cleared: {pattern} ({deleted} keys)")
                return deleted
            return 0
        except RedisError as e:
            logger.warning(f"Redis delete pattern error: {e}")
            return 0

    def clear_all(self) -> bool:
        """清空所有缓存"""
        if not self.is_connected():
            return False

        try:
            self._redis_client.flushdb()
            logger.info("Redis cache cleared: all")
            return True
        except RedisError as e:
            logger.warning(f"Redis flushdb error: {e}")
            return False

    def get_ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间

        Args:
            key: 缓存键

        Returns:
            剩余秒数，-1 表示无过期时间，-2 表示键不存在
        """
        if not self.is_connected():
            return -2

        try:
            return self._redis_client.ttl(key)
        except RedisError as e:
            logger.warning(f"Redis ttl error: {e}")
            return -2


# 全局缓存实例
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """获取全局缓存实例"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


def reset_cache() -> None:
    """重置缓存实例（用于测试）"""
    global _cache
    _cache = None


# ============================================
# 缓存装饰器
# ============================================

def cached(key_prefix: str, ttl: int = 300, get_key_params: bool = True):
    """
    缓存装饰器

    Args:
        key_prefix: 缓存键前缀
        ttl: 过期时间（秒）
        get_key_params: 是否从函数参数生成缓存键

    Example:
        @cached("quote", ttl=30)
        async def get_stock_quote(code: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            if get_key_params:
                # 从参数生成缓存键
                key_parts = [key_prefix]
                # 跳过 self/cls 参数
                start_idx = 1 if len(args) > 0 and callable(args[0]) else 0
                for arg in args[start_idx:]:
                    if isinstance(arg, (str, int, float)):
                        key_parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    if isinstance(v, (str, int, float)):
                        key_parts.append(f"{k}={v}")
                cache_key = ":".join(key_parts)
            else:
                cache_key = key_prefix

            # 尝试从缓存获取
            cache = get_cache()
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.info(f"Cache hit: {cache_key}")
                return cached_value

            # 执行函数
            result = await func(*args, **kwargs)

            # 存储到缓存
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            if get_key_params:
                key_parts = [key_prefix]
                start_idx = 1 if len(args) > 0 and callable(args[0]) else 0
                for arg in args[start_idx:]:
                    if isinstance(arg, (str, int, float)):
                        key_parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    if isinstance(v, (str, int, float)):
                        key_parts.append(f"{k}={v}")
                cache_key = ":".join(key_parts)
            else:
                cache_key = key_prefix

            # 尝试从缓存获取
            cache = get_cache()
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.info(f"Cache hit: {cache_key}")
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 存储到缓存
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        # 返回正确的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(prefix: str):
    """
    缓存失效装饰器（清除指定前缀的缓存）

    Args:
        prefix: 缓存键前缀

    Example:
        @invalidate_cache("quote")
        async def update_stock_quote(code: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # 清除缓存
            cache = get_cache()
            cache.delete_pattern(f"{prefix}:*")
            logger.info(f"Cache invalidated: {prefix}:*")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # 清除缓存
            cache = get_cache()
            cache.delete_pattern(f"{prefix}:*")
            logger.info(f"Cache invalidated: {prefix}:*")

            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================
# 缓存配置常量
# ============================================

# 缓存 TTL 配置（秒）
CACHE_TTL = {
    "quote": 30,        # 实时行情 - 30秒
    "kline": 300,       # K线数据 - 5分钟
    "technical": 900,   # 技术分析 - 15分钟
    "fundamental": 1800,  # 基本面分析 - 30分钟
    "advice": 900,      # 投资建议 - 15分钟
    "search": 60,       # 搜索结果 - 1分钟
    "stock_info": 300,  # 股票信息 - 5分钟
}


def get_cache_ttl(cache_type: str) -> int:
    """获取指定类型的缓存 TTL"""
    return CACHE_TTL.get(cache_type, 300)
