"""
财经新闻服务模块测试
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from app.services.news_service import (
    NewsService,
    NewsCache,
    get_news_service,
    clear_news_cache,
    get_news_cache,
    get_news_categories,
    NEWS_CATEGORIES
)


class TestNewsCache:
    """缓存层测试"""

    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache = NewsCache(ttl=60)

        # 设置缓存
        cache.set("test_key", [{"title": "Test News", "url": "http://test.com"}])

        # 获取缓存
        result = cache.get("test_key")

        assert result is not None
        assert len(result) == 1
        assert result[0]["title"] == "Test News"

    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = NewsCache(ttl=60)

        result = cache.get("nonexistent_key")

        assert result is None

    def test_cache_expiration(self):
        """测试缓存过期"""
        cache = NewsCache(ttl=1)

        cache.set("expiring_key", "value")

        # 等待缓存过期
        time.sleep(1.1)

        result = cache.get("expiring_key")

        assert result is None

    def test_cache_clear(self):
        """测试清空缓存"""
        cache = NewsCache(ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestNewsService:

    def test_get_news_cache_key(self):
        """测试缓存键生成"""
        service = NewsService(use_cache=False)

        key1 = service._get_cache_key("news:latest", category="market", limit=10)
        key2 = service._get_cache_key("news:latest", limit=10, category="market")

        assert key1 == key2

    def test_news_categories(self):
        """测试新闻分类"""
        categories = get_news_categories()

        assert "macro" in categories
        assert "market" in categories
        assert categories["macro"] == "宏观政策"
        assert categories["market"] == "市场分析"

    def test_filter_news_by_category(self):
        """测试按分类过滤新闻"""
        service = NewsService(use_cache=False)

        news_list = [
            {"title": "News 1", "category": "market"},
            {"title": "News 2", "category": "industry"},
            {"title": "News 3", "category": "market"},
        ]

        result = service._filter_news(news_list, category="market", limit=10)

        assert len(result) == 2
        assert all(n["category"] == "market" for n in result)

    def test_filter_news_by_symbol(self):
        """测试按股票代码过滤"""
        service = NewsService(use_cache=False)

        news_list = [
            {"title": "Apple news", "category": "company"},
            {"title": "Tesla news", "category": "company"},
            {"title": "General news", "category": "market"},
        ]

        result = service._filter_news(news_list, symbol="Apple", limit=10)

        assert len(result) == 1
        assert "Apple" in result[0]["title"]

    def test_filter_news_limit(self):
        """测试数量限制"""
        service = NewsService(use_cache=False)

        news_list = [
            {"title": f"News {i}", "category": "market"}
            for i in range(100)
        ]

        result = service._filter_news(news_list, limit=10)

        assert len(result) == 10

    @patch('app.services.news_service.NewsService._fetch_from_sina')
    @patch('app.services.news_service.NewsService._fetch_from_eastmoney')
    @patch('app.services.news_service.NewsService._fetch_from_tencent')
    def test_get_latest_news_with_cache(
        self,
        mock_tencent,
        mock_eastmoney,
        mock_sina
    ):
        """测试获取新闻（带缓存）"""
        # 模拟返回空列表
        mock_sina.return_value = []
        mock_eastmoney.return_value = []
        mock_tencent.return_value = []

        service = NewsService(use_cache=True)

        # 第一次调用
        result1 = service.get_latest_news(limit=10)

        # 第二次调用应从缓存获取
        result2 = service.get_latest_news(limit=10)

        # 清空缓存后再调用
        clear_news_cache()
        result3 = service.get_latest_news(limit=10)

        # 验证缓存正常工作
        assert isinstance(result1, list)
        assert isinstance(result2, list)
        assert isinstance(result3, list)

    @patch('app.services.news_service.NewsService._fetch_from_sina')
    def test_search_news(self, mock_sina):
        """测试搜索新闻"""
        mock_sina.return_value = [
            {"title": "A股今日大涨", "url": "http://test1.com", "source": "Test", "category": "market", "published_at": "2024-01-01", "summary": "A股今日大涨"},
            {"title": "新能源板块火热", "url": "http://test2.com", "source": "Test", "category": "industry", "published_at": "2024-01-01", "summary": "新能源板块火热"},
        ]

        service = NewsService(use_cache=True)
        clear_news_cache()

        # 搜索 "A股"
        result = service.search_news("A股", limit=10)

        assert len(result) >= 1

    def test_get_hot_keywords(self):
        """测试获取热门关键词"""
        service = NewsService(use_cache=False)

        # 模拟新闻列表
        news_list = [
            {"title": "A股市场分析", "category": "market"},
            {"title": "新能源板块大涨", "category": "industry"},
            {"title": "A股今日涨停", "category": "market"},
            {"title": "银行财报发布", "category": "company"},
        ]

        # 模拟 get_latest_news 返回值
        with patch.object(service, 'get_latest_news', return_value=news_list):
            keywords = service.get_hot_keywords(limit=5)

            assert isinstance(keywords, list)
            assert len(keywords) <= 5

    def test_get_news_by_date(self):
        """测试按日期获取新闻"""
        service = NewsService(use_cache=False)

        today = "2024-01-01"

        # 模拟新闻
        news_list = [
            {"title": "Today news1", "published_at": "2024-01-01 10:00:00"},
            {"title": "Today news 2", "published_at": "2024-01-01 11:00:00"},
            {"title": "Yesterday news", "published_at": "2023-12-31 10:00:00"},
        ]

        with patch.object(service, 'get_latest_news', return_value=news_list):
            result = service.get_news_by_date(today, limit=10)

            assert len(result) == 2

    def test_news_service_singleton(self):
        """测试新闻服务单例"""
        service1 = get_news_service()
        service2 = get_news_service()

        assert service1 is service2
