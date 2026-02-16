"""
限流服务测试

测试基于 Redis 的分布式限流功能。
"""
import pytest
from unittest.mock import MagicMock, patch
import time

from app.services.rate_limiter import (
    RedisRateLimiter,
    InMemoryRateLimiter,
    get_rate_limiter,
    reset_rate_limiter,
    RATE_LIMIT_CONFIG,
    get_rate_limit_for_endpoint
)


class TestRateLimitConfig:
    """限流配置测试"""

    def test_default_config(self):
        """测试默认限流配置"""
        config = RATE_LIMIT_CONFIG["default"]
        assert config["max_requests"] == 60
        assert config["window_seconds"] == 60

    def test_quote_config(self):
        """测试行情接口限流配置"""
        config = RATE_LIMIT_CONFIG["quote"]
        assert config["max_requests"] == 120

    def test_technical_config(self):
        """测试技术分析限流配置"""
        config = RATE_LIMIT_CONFIG["technical"]
        assert config["max_requests"] == 30

    def test_chat_config(self):
        """测试问答接口限流配置"""
        config = RATE_LIMIT_CONFIG["chat"]
        assert config["max_requests"] == 10

    def test_get_rate_limit_for_endpoint(self):
        """测试根据端点获取限流配置"""
        assert get_rate_limit_for_endpoint("/quote/") == RATE_LIMIT_CONFIG["quote"]
        assert get_rate_limit_for_endpoint("/kline/") == RATE_LIMIT_CONFIG["kline"]
        assert get_rate_limit_for_endpoint("/technical/") == RATE_LIMIT_CONFIG["technical"]
        assert get_rate_limit_for_endpoint("/unknown/") == RATE_LIMIT_CONFIG["default"]


class TestInMemoryRateLimiter:
    """内存限流器测试"""

    def setup_method(self):
        """每个测试前创建新的限流器"""
        self.limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)

    def test_allows_requests_under_limit(self):
        """测试限制内的请求被允许"""
        for i in range(5):
            assert self.limiter.is_allowed(f"client_{i}") is True

    def test_blocks_requests_over_limit(self):
        """测试超出限制的请求被阻止"""
        # 发送 5 个请求（达到限制）
        for i in range(5):
            self.limiter.is_allowed("client")

        # 第 6 个请求应该被阻止
        assert self.limiter.is_allowed("client") is False

    def test_get_remaining(self):
        """测试获取剩余请求次数"""
        self.limiter.is_allowed("client")
        self.limiter.is_allowed("client")

        remaining = self.limiter.get_remaining("client")
        assert remaining == 3  # 5 - 2 = 3

    def test_reset(self):
        """测试重置限流"""
        for i in range(5):
            self.limiter.is_allowed("client")

        # 超出限制
        assert self.limiter.is_allowed("client") is False

        # 重置
        self.limiter.reset("client")

        # 应该允许请求
        assert self.limiter.is_allowed("client") is True

    def test_time_window_expiry(self):
        """测试时间窗口过期"""
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=1)

        limiter.is_allowed("client")
        limiter.is_allowed("client")
        assert limiter.is_allowed("client") is False

        # 等待过期
        time.sleep(1.1)

        # 应该允许请求
        assert limiter.is_allowed("client") is True


class TestRedisRateLimiter:
    """Redis 限流器测试"""

    def setup_method(self):
        """每个测试前重置限流器"""
        reset_rate_limiter()

    @patch('redis.from_url')
    def test_initialization(self, mock_redis):
        """测试限流器初始化"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client

        limiter = RedisRateLimiter(max_requests=10, window_seconds=60)
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60

    @patch('redis.from_url')
    def test_fallback_to_memory(self, mock_redis):
        """测试 Redis 连接失败时降级到内存限流"""
        mock_redis.side_effect = Exception("Connection failed")

        limiter = RedisRateLimiter(max_requests=5, window_seconds=60)
        # 应该使用内存限流器
        assert limiter._fallback_limiter is not None

        # 测试限流功能
        for i in range(5):
            assert limiter.is_allowed("client") is True

        assert limiter.is_allowed("client") is False

    @patch('redis.from_url')
    def test_is_allowed_with_redis(self, mock_redis):
        """测试 Redis 限流器允许请求"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        # 模拟 zremrangebyscore, zcard, zadd, expire 返回值
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [0, 0, 1, True]
        mock_client.pipeline.return_value = mock_pipeline

        mock_redis.return_value = mock_client

        limiter = RedisRateLimiter(max_requests=5, window_seconds=60)
        result = limiter.is_allowed("client")

        assert result is True

    @patch('redis.from_url')
    def test_is_allowed_blocks_over_limit(self, mock_redis):
        """测试 Redis 限流器阻止超限请求"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        # 模拟请求数已达到限制
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [0, 5, 1, True]
        mock_client.pipeline.return_value = mock_pipeline

        mock_redis.return_value = mock_client

        limiter = RedisRateLimiter(max_requests=5, window_seconds=60)
        result = limiter.is_allowed("client")

        # 超过限制，应该返回 False
        assert result is False

    @patch('redis.from_url')
    def test_get_remaining(self, mock_redis):
        """测试获取剩余请求次数"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.zremrangebyscore.return_value = 0
        mock_client.zcard.return_value = 3
        mock_redis.return_value = mock_client

        limiter = RedisRateLimiter(max_requests=5, window_seconds=60)
        remaining = limiter.get_remaining("client")

        assert remaining == 2  # 5 - 3 = 2

    @patch('redis.from_url')
    def test_reset(self, mock_redis):
        """测试重置限流"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client

        limiter = RedisRateLimiter(max_requests=5, window_seconds=60)
        limiter.reset("client")

        mock_client.delete.assert_called_once()


class TestGetRateLimiter:
    """获取限流器测试"""

    def setup_method(self):
        """每个测试前重置限流器"""
        reset_rate_limiter()

    def test_get_rate_limiter_singleton(self):
        """测试限流器单例模式"""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    def test_get_rate_limiter_with_custom_config(self):
        """测试自定义配置"""
        limiter = get_rate_limiter(max_requests=100, window_seconds=30)

        assert limiter.max_requests == 100
        assert limiter.window_seconds == 30
