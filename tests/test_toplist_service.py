"""
龙虎榜服务模块测试
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd

from app.services.toplist_service import (
    TopListService,
    TopListCache,
    get_toplist_service,
)


class TestTopListCache:
    """缓存层测试"""

    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache = TopListCache(ttl=60)

        cache.set("test_key", {"value": "test_value"})

        result = cache.get("test_key")

        assert result is not None
        assert result["value"] == "test_value"

    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = TopListCache(ttl=60)

        result = cache.get("nonexistent_key")

        assert result is None

    def test_cache_expiration(self):
        """测试缓存过期"""
        cache = TopListCache(ttl=1)

        cache.set("expiring_key", "value")

        time.sleep(1.1)

        result = cache.get("expiring_key")

        assert result is None


class TestTopListService:
    """龙虎榜服务测试"""

    def setup_method(self):
        """每个测试方法前创建新服务实例"""
        self.service = TopListService(use_cache=True)

    def test_normalize_symbol_sh(self):
        """测试上海股票代码标准化"""
        assert self.service._normalize_symbol("sh600000") == "600000"
        assert self.service._normalize_symbol("600000") == "600000"

    def test_normalize_symbol_sz(self):
        """测试深圳股票代码标准化"""
        assert self.service._normalize_symbol("sz000001") == "000001"
        assert self.service._normalize_symbol("000001") == "000001"

    def test_normalize_symbol_bj(self):
        """测试北京股票代码标准化"""
        assert self.service._normalize_symbol("bj830799") == "830799"
        assert self.service._normalize_symbol("830799") == "830799"

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        key1 = self.service._get_cache_key("test", a=1, b=2)
        key2 = self.service._get_cache_key("test", b=2, a=1)

        assert key1 == key2

        key3 = self.service._get_cache_key("test", a=1, b=3)
        assert key1 != key3

    def test_service_init_with_cache(self):
        """测试服务初始化（使用缓存）"""
        service = TopListService(use_cache=True)

        assert service.use_cache is True
        assert service.cache is not None

    def test_service_init_without_cache(self):
        """测试服务初始化（不使用缓存）"""
        service = TopListService(use_cache=False)

        assert service.use_cache is False

    @patch("app.services.toplist_service.ak.stock_lhb_em")
    def test_get_daily_toplist_success(self, mock_ak_func):
        """测试获取每日龙虎榜成功"""
        mock_ak_func.return_value = pd.DataFrame({
            "代码": ["600000", "000001"],
            "名称": ["浦发银行", "平安银行"],
            "收盘价": [10.5, 12.3],
            "涨跌幅": [1.2, -0.5],
            "龙虎榜净买额": [10000000, -5000000],
            "龙虎榜买入额": [20000000, 8000000],
            "龙虎榜卖出额": [10000000, 13000000],
            "上榜原因": ["日涨幅偏离值达7%", "日振幅值达15%"],
            "成交额": [500000000, 300000000],
        })

        result = self.service.get_daily_toplist()

        assert result is not None
        assert len(result) == 2
        assert result[0]["code"] == "600000"
        assert result[0]["name"] == "浦发银行"
        assert result[0]["net_buy"] == 10000000

    @patch("app.services.toplist_service.ak.stock_lhb_detail_em")
    def test_get_stock_toplist_success(self, mock_ak_func):
        """测试获取个股龙虎榜成功"""
        mock_ak_func.return_value = pd.DataFrame({
            "交易日期": ["20240115", "20240110"],
            "股票代码": ["600000", "600000"],
            "收盘价": [10.5, 10.2],
            "涨跌幅": [1.2, -0.8],
            "龙虎榜买入额": [20000000, 15000000],
            "龙虎榜卖出额": [10000000, 18000000],
            "龙虎榜净买额": [10000000, -3000000],
            "上榜原因": ["日涨幅偏离值达7%", "日振幅值达15%"],
            "龙虎榜买入席位": ["机构专用", "券商营业部"],
            "龙虎榜卖出席位": ["券商营业部", "机构专用"],
        })

        result = self.service.get_stock_toplist("600000")

        assert result is not None
        assert len(result) == 2
        assert result[0]["code"] == "600000"
        assert result[0]["net_buy"] == 10000000

    def test_analyze_institutional_seats(self):
        """测试机构席位分析"""
        toplist_data = [
            {
                "date": "20240115",
                "net_buy": 10000000,
                "buy_amount": 20000000,
                "sell_amount": 10000000,
            },
            {
                "date": "20240110",
                "net_buy": -5000000,
                "buy_amount": 8000000,
                "sell_amount": 13000000,
            },
        ]

        result = self.service._analyze_institutional_seats(toplist_data)

        assert len(result) == 2
        assert result[0]["date"] == "20240115"
        assert result[0]["net_buy"] == 10000000
        assert result[1]["net_buy"] == -5000000

    def test_generate_alert_no_orders(self):
        """测试无大单时的预警"""
        alerts = self.service._generate_alert([])

        assert "近期无大单交易" in alerts

    def test_generate_alert_buy_streak(self):
        """测试连续买入预警"""
        large_orders = [
            {"date": "20240115", "net_buy": 20000000, "order_type": "买入"},
            {"date": "20240114", "net_buy": 15000000, "order_type": "买入"},
            {"date": "20240113", "net_buy": 10000000, "order_type": "买入"},
        ]

        alerts = self.service._generate_alert(large_orders)

        assert any("连续" in a and "买入" in a for a in alerts)

    def test_generate_alert_sell_orders(self):
        """测试大单卖出预警"""
        large_orders = [
            {"date": "20240115", "net_buy": -20000000, "order_type": "卖出"},
            {"date": "20240114", "net_buy": -15000000, "order_type": "卖出"},
        ]

        alerts = self.service._generate_alert(large_orders)

        assert any("卖出" in a for a in alerts)

    def test_generate_alert_net_outflow(self):
        """测试净流出预警"""
        large_orders = [
            {"date": "20240115", "net_buy": -10000000, "order_type": "卖出"},
            {"date": "20240114", "net_buy": -15000000, "order_type": "卖出"},
            {"date": "20240113", "net_buy": -20000000, "order_type": "卖出"},
            {"date": "20240112", "net_buy": -20000000, "order_type": "卖出"},
        ]

        alerts = self.service._generate_alert(large_orders)

        assert any("净流出" in a for a in alerts)

    def test_get_toplist_service_singleton(self):
        """测试获取服务单例"""
        service1 = get_toplist_service()
        service2 = get_toplist_service()

        assert service1 is service2


class TestTopListServiceIntegration:
    """集成测试（需要网络）"""

    @pytest.mark.integration
    def test_get_daily_toplist_integration(self):
        """测试获取每日龙虎榜集成测试"""
        service = TopListService(use_cache=False)

        try:
            result = service.get_daily_toplist()
            assert isinstance(result, list)
            # 龙虎榜数据可能为空（节假日等情况）
        except Exception as e:
            pytest.skip(f"网络不可用或API变更: {e}")

    @pytest.mark.integration
    @pytest.mark.skip(reason="需要特定股票有龙虎榜数据")
    def test_get_stock_toplist_integration(self):
        """测试获取个股龙虎榜集成测试"""
        service = TopListService(use_cache=False)

        try:
            # 尝试获取历史上常有龙虎榜的股票
            result = service.get_stock_toplist("600000", "20240101", "20240131")
            assert isinstance(result, list)
        except Exception as e:
            pytest.skip(f"网络不可用或API变更: {e}")

    @pytest.mark.integration
    @pytest.mark.skip(reason="需要特定股票有龙虎榜数据")
    def test_get_institutional_tracking_integration(self):
        """测试机构席位追踪集成测试"""
        service = TopListService(use_cache=False)

        try:
            result = service.get_institutional_tracking("600000", days=30)
            assert result is not None
            assert "institutional_summary" in result
        except Exception as e:
            pytest.skip(f"网络不可用或API变更: {e}")
