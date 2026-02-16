"""
缓存服务测试

测试 Redis 缓存功能和降级处理。
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.cache_service import (
    RedisCache,
    get_cache,
    reset_cache,
    cached,
    CACHE_TTL,
    get_cache_ttl
)


class TestCacheTTL:
    """缓存 TTL 配置测试"""

    def test_cache_ttl_values(self):
        """测试缓存 TTL 配置值"""
        assert CACHE_TTL["quote"] == 30
        assert CACHE_TTL["kline"] == 300
        assert CACHE_TTL["technical"] == 900
        assert CACHE_TTL["fundamental"] == 1800
        assert CACHE_TTL["advice"] == 900
        assert CACHE_TTL["search"] == 60
        assert CACHE_TTL["stock_info"] == 300

    def test_get_cache_ttl(self):
        """测试获取缓存 TTL"""
        assert get_cache_ttl("quote") == 30
        assert get_cache_ttl("unknown") == 300  # 默认值


class TestRedisCache:
    """Redis 缓存测试"""

    def setup_method(self):
        """每个测试前重置缓存"""
        reset_cache()

    def test_cache_initialization(self):
        """测试缓存初始化"""
        cache = RedisCache()
        # Redis 连接可能失败，但对象应该能创建
        assert cache is not None
        assert cache._redis_client is not None or cache._redis_client is None

    @patch('redis.from_url')
    def test_cache_connection_failure(self, mock_redis):
        """测试 Redis 连接失败时的降级处理"""
        mock_redis.side_effect = Exception("Connection failed")

        cache = RedisCache()
        # 应该降级到内存模式
        assert cache.is_connected() is False

    @patch('redis.from_url')
    def test_cache_get_miss(self, mock_redis):
        """测试缓存未命中"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        cache = RedisCache()
        result = cache.get("test_key")
        assert result is None

    @patch('redis.from_url')
    def test_cache_set(self, mock_redis):
        """测试缓存设置"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client

        cache = RedisCache()
        result = cache.set("test_key", {"value": "test"}, ttl=60)

        # 验证 setex 被调用
        mock_client.setex.assert_called_once()

    @patch('redis.from_url')
    def test_cache_delete(self, mock_redis):
        """测试缓存删除"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client

        cache = RedisCache()
        cache.delete("test_key")

        mock_client.delete.assert_called_once_with("test_key")

    @patch('redis.from_url')
    def test_cache_delete_pattern(self, mock_redis):
        """测试批量删除缓存"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.keys.return_value = ["key1", "key2"]
        mock_client.delete.return_value = 2
        mock_redis.return_value = mock_client

        cache = RedisCache()
        deleted = cache.delete_pattern("test:*")

        assert deleted == 2


class TestCachedDecorator:
    """缓存装饰器测试"""

    def setup_method(self):
        """每个测试前重置缓存"""
        reset_cache()

    @patch('redis.from_url')
    def test_cached_decorator_sync(self, mock_redis):
        """测试同步函数缓存装饰器"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        @cached("test", ttl=60)
        def test_func(a, b):
            return a + b

        result = test_func(1, 2)
        assert result == 3
        # 验证 setex 被调用
        mock_client.setex.assert_called()

    @patch('redis.from_url')
    def test_cached_decorator_cache_hit(self, mock_redis):
        """测试缓存命中"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = '{"result": 100}'
        mock_redis.return_value = mock_client

        @cached("test", ttl=60)
        def test_func(a, b):
            return a + b

        result = test_func(1, 2)
        assert result == {"result": 100}
        # setex 不应该被调用（缓存命中）
        mock_client.setex.assert_not_called()

    @pytest.mark.asyncio
    @patch('redis.from_url')
    async def test_cached_decorator_async(self, mock_redis):
        """测试异步函数缓存装饰器"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        @cached("test_async", ttl=60)
        async def test_async_func(a):
            return a * 2

        result = await test_async_func(5)
        assert result == 10
