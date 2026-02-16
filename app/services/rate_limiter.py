"""
分布式限流服务

基于 Redis 的分布式请求限流机制，支持：
- 滑动窗口限流
- 按客户端 IP 或用户 ID 限流
- 连接失败时的内存降级
"""
import time
from typing import Optional, Dict, List
from threading import Lock

import redis
from redis import RedisError

from app.config import get_config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisRateLimiter:
    """基于 Redis 的分布式限流器"""

    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        key_prefix: str = "ratelimit"
    ):
        """
        初始化限流器

        Args:
            max_requests: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒）
            key_prefix: Redis 键前缀
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self._redis_client: Optional[redis.Redis] = None
        self._connected = False
        self._fallback_limiter = None
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
            self._redis_client.ping()
            self._connected = True
            logger.info("Rate limiter Redis connection established")
        except Exception as e:
            self._connected = False
            self._redis_client = None
            logger.warning(f"Rate limiter Redis connection failed, using fallback: {e}")
            # 使用内存限流器作为降级方案
            self._fallback_limiter = InMemoryRateLimiter(
                self.max_requests,
                self.window_seconds
            )

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

    def _get_key(self, client_id: str) -> str:
        """生成 Redis 键"""
        return f"{self.key_prefix}:{client_id}"

    def is_allowed(self, client_id: str) -> bool:
        """
        检查是否允许请求

        Args:
            client_id: 客户端标识

        Returns:
            是否允许请求
        """
        if self._fallback_limiter is not None:
            return self._fallback_limiter.is_allowed(client_id)

        try:
            key = self._get_key(client_id)
            current_time = time.time()
            window_start = current_time - self.window_seconds

            # 使用 Redis 事务
            pipe = self._redis_client.pipeline()
            # 删除窗口外的请求记录
            pipe.zremrangebyscore(key, 0, window_start)
            # 获取当前请求数
            pipe.zcard(key)
            # 添加当前请求
            pipe.zadd(key, {str(current_time): current_time})
            # 设置过期时间
            pipe.expire(key, self.window_seconds)
            results = pipe.execute()

            request_count = results[1]

            if request_count >= self.max_requests:
                # 超过限制，删除刚才添加的请求
                self._redis_client.zrem(key, str(current_time))
                return False

            return True

        except RedisError as e:
            logger.warning(f"Redis rate limiter error: {e}, using fallback")
            if self._fallback_limiter is None:
                self._fallback_limiter = InMemoryRateLimiter(
                    self.max_requests,
                    self.window_seconds
                )
            return self._fallback_limiter.is_allowed(client_id)

    def get_remaining(self, client_id: str) -> int:
        """
        获取剩余请求次数

        Args:
            client_id: 客户端标识

        Returns:
            剩余请求次数
        """
        if self._fallback_limiter is not None:
            return self._fallback_limiter.get_remaining(client_id)

        try:
            key = self._get_key(client_id)
            current_time = time.time()
            window_start = current_time - self.window_seconds

            # 清理过期的请求记录
            self._redis_client.zremrangebyscore(key, 0, window_start)
            # 获取当前请求数
            request_count = self._redis_client.zcard(key)

            return max(0, self.max_requests - request_count)

        except RedisError as e:
            logger.warning(f"Redis get remaining error: {e}")
            if self._fallback_limiter is not None:
                return self._fallback_limiter.get_remaining(client_id)
            return 0

    def reset(self, client_id: str) -> bool:
        """
        重置指定客户端的请求计数

        Args:
            client_id: 客户端标识

        Returns:
            是否重置成功
        """
        if self._fallback_limiter is not None:
            self._fallback_limiter.reset(client_id)
            return True

        try:
            key = self._get_key(client_id)
            self._redis_client.delete(key)
            return True
        except RedisError as e:
            logger.warning(f"Redis reset error: {e}")
            return False


class InMemoryRateLimiter:
    """内存限流器（降级方案）"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        current_time = time.time()

        with self._lock:
            if client_id not in self._requests:
                self._requests[client_id] = []

            # 清理过期的请求记录
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id]
                if current_time - req_time < self.window_seconds
            ]

            # 检查是否超过限制
            if len(self._requests[client_id]) >= self.max_requests:
                return False

            # 记录新请求
            self._requests[client_id].append(current_time)
            return True

    def get_remaining(self, client_id: str) -> int:
        current_time = time.time()

        with self._lock:
            if client_id not in self._requests:
                return self.max_requests

            # 清理过期的请求记录
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id]
                if current_time - req_time < self.window_seconds
            ]

            return max(0, self.max_requests - len(self._requests[client_id]))

    def reset(self, client_id: str) -> None:
        with self._lock:
            if client_id in self._requests:
                del self._requests[client_id]


# 全局限流器实例
_rate_limiter: Optional[RedisRateLimiter] = None


def get_rate_limiter(
    max_requests: int = 60,
    window_seconds: int = 60
) -> RedisRateLimiter:
    """获取全局限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds
        )
    return _rate_limiter


def reset_rate_limiter() -> None:
    """重置限流器实例（用于测试）"""
    global _rate_limiter
    _rate_limiter = None


# ============================================
# 限流配置
# ============================================

# API 限流配置
RATE_LIMIT_CONFIG = {
    "default": {"max_requests": 60, "window_seconds": 60},
    "quote": {"max_requests": 120, "window_seconds": 60},
    "kline": {"max_requests": 60, "window_seconds": 60},
    "technical": {"max_requests": 30, "window_seconds": 60},
    "fundamental": {"max_requests": 30, "window_seconds": 60},
    "chat": {"max_requests": 10, "window_seconds": 60},
    "search": {"max_requests": 30, "window_seconds": 60},
}


def get_rate_limit_for_endpoint(endpoint: str) -> Dict[str, int]:
    """获取端点的限流配置"""
    # 匹配端点类型
    for key, config in RATE_LIMIT_CONFIG.items():
        if key in endpoint.lower():
            return config
    return RATE_LIMIT_CONFIG["default"]
