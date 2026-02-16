"""
股票服务模块测试
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.services.stock_service import (
    StockService,
    StockCache,
    get_stock_service,
    clear_cache,
)


class TestStockCache:
    """缓存层测试"""

    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache = StockCache(ttl=60)

        # 设置缓存
        cache.set("test_key", {"value": "test_value"})

        # 获取缓存
        result = cache.get("test_key")

        assert result is not None
        assert result["value"] == "test_value"

    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = StockCache(ttl=60)

        result = cache.get("nonexistent_key")

        assert result is None

    def test_cache_expiration(self):
        """测试缓存过期"""
        cache = StockCache(ttl=1)

        cache.set("expiring_key", "value")

        # 等待缓存过期
        time.sleep(1.1)

        result = cache.get("expiring_key")

        assert result is None

    def test_cache_clear(self):
        """测试清空缓存"""
        cache = StockCache(ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_remove(self):
        """测试删除指定缓存"""
        cache = StockCache(ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.remove("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"


class TestStockService:
    """股票服务测试"""

    def setup_method(self):
        """每个测试方法前清空缓存"""
        clear_cache()
        self.service = StockService(use_cache=True)

    def test_normalize_symbol_sh(self):
        """测试上海股票代码标准化"""
        assert self.service._normalize_symbol("600000") == "sh600000"
        assert self.service._normalize_symbol("sh600000") == "sh600000"

    def test_normalize_symbol_sz(self):
        """测试深圳股票代码标准化"""
        assert self.service._normalize_symbol("000001") == "sz000001"
        assert self.service._normalize_symbol("sz000001") == "sz000001"

    def test_normalize_symbol_bj(self):
        """测试北京股票代码标准化"""
        assert self.service._normalize_symbol("830799") == "bj830799"
        assert self.service._normalize_symbol("bj830799") == "bj830799"

    def test_get_market(self):
        """测试市场识别"""
        assert self.service._get_market("sh600000") == "上海证券交易所"
        assert self.service._get_market("sz000001") == "深圳证券交易所"
        assert self.service._get_market("bj830799") == "北京证券交易所"
        assert self.service._get_market("unknown") == "未知"

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        key1 = self.service._get_cache_key("test", a=1, b=2)
        key2 = self.service._get_cache_key("test", b=2, a=1)

        # 相同参数应生成相同键
        assert key1 == key2

        # 不同参数应生成不同键
        key3 = self.service._get_cache_key("test", a=1, b=3)
        assert key1 != key3

    def test_get_cache_key_prefix(self):
        """测试缓存键前缀"""
        key = self.service._get_cache_key("stock_info", symbol="600000")

        assert key.startswith("stock_info:")

    def test_service_init_with_cache(self):
        """测试服务初始化（使用缓存）"""
        service = StockService(use_cache=True)

        assert service.use_cache is True
        assert service.cache is not None

    def test_service_init_without_cache(self):
        """测试服务初始化（不使用缓存）"""
        service = StockService(use_cache=False)

        assert service.use_cache is False

    @patch("app.services.stock_service.ak.stock_individual_info_em")
    def test_get_stock_info_success(self, mock_ak_func):
        """测试获取股票信息成功"""
        import pandas as pd
        # 模拟 AkShare 返回数据
        mock_ak_func.return_value = pd.DataFrame({
            "item": ["股票简称", "所属行业", "上市时间"],
            "value": ["平安银行", "银行", "1991-04-03"],
        })

        result = self.service.get_stock_info("000001")

        assert result is not None
        assert result["code"] == "sz000001"
        assert result["name"] == "平安银行"
        assert result["industry"] == "银行"

    @patch("app.services.stock_service.ak.stock_zh_a_spot_em")
    def test_get_stock_quote_success(self, mock_ak_func):
        """测试获取股票行情成功"""
        import pandas as pd
        # 模拟 AkShare 返回数据
        mock_ak_func.return_value = pd.DataFrame({
            "代码": ["000001"],
            "名称": ["平安银行"],
            "最新价": [12.34],
            "涨跌幅": [1.23],
            "成交量": [1000000],
            "成交额": [12345678],
        })

        result = self.service.get_stock_quote("000001")

        assert result is not None
        assert result["code"] == "sz000001"
        assert result["name"] == "平安银行"
        assert result["price"] == 12.34

    @patch("app.services.stock_service.ak.stock_zh_a_hist")
    def test_get_kline_data_daily(self, mock_ak_func):
        """测试获取日K线数据"""
        import pandas as pd
        mock_df = pd.DataFrame({
            "日期": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            "开盘": [10.0, 10.5],
            "最高": [10.8, 11.0],
            "最低": [9.8, 10.3],
            "收盘": [10.5, 10.8],
            "成交量": [1000000, 1100000],
            "成交额": [10000000, 11000000],
        })

        mock_ak_func.return_value = mock_df

        result = self.service.get_kline_data("600000", period="daily", start_date="20240101", end_date="20240110")

        assert result is not None
        assert len(result) == 2
        assert result[0]["code"] == "sh600000"
        assert result[0]["open"] == 10.0
        assert result[0]["close"] == 10.5

    def test_get_stock_info_uses_cache(self):
        """测试股票信息使用缓存"""
        # 先设置缓存
        cached_data = {
            "code": "sh600000",
            "name": "测试股票",
            "market": "上海证券交易所",
            "industry": "测试行业",
        }
        cache_key = self.service._get_cache_key("stock_info", symbol="600000")
        self.service.cache.set(cache_key, cached_data)

        # 再次获取应该从缓存读取
        result = self.service.get_stock_info("600000")

        assert result == cached_data

    def test_clear_cache_function(self):
        """测试全局清空缓存函数"""
        service = get_stock_service()

        service.cache.set("test_key", "test_value")

        clear_cache()

        assert service.cache.get("test_key") is None

    def test_get_stock_service_singleton(self):
        """测试获取服务单例"""
        service1 = get_stock_service()
        service2 = get_stock_service()

        assert service1 is service2


class TestStockServiceIntegration:
    """集成测试（需要网络）"""

    @pytest.mark.integration
    def test_search_stocks(self):
        """测试股票搜索功能"""
        service = StockService(use_cache=False)

        # 这个测试需要网络连接
        try:
            results = service.search_stocks("平安")
            assert isinstance(results, list)
            # 可能找到平安银行、平安保险等
        except Exception as e:
            pytest.skip(f"网络不可用或API变更: {e}")

    @pytest.mark.integration
    def test_get_kline_data_integration(self):
        """测试获取K线数据集成测试"""
        service = StockService(use_cache=False)

        try:
            result = service.get_kline_data(
                "000001",
                period="daily",
                start_date=(datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d")
            )
            assert result is not None
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"网络不可用或API变更: {e}")
