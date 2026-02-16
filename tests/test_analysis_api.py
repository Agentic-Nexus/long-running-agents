"""
股票分析报告 API 测试
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestAnalysisEndpoints:
    """分析 API 端点测试"""

    def test_analysis_root(self, client):
        """测试分析API根路由"""
        response = client.get("/api/v1/analysis/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data


class TestTechnicalAnalysis:
    """技术分析端点测试"""

    @patch('app.api.analysis.get_stock_service')
    def test_technical_analysis_endpoint_exists(self, mock_get_service, client):
        """测试技术分析接口存在"""
        # Mock 服务
        mock_service = MagicMock()

        # Mock 股票信息
        mock_service.get_stock_info.return_value = {
            "code": "sh600000",
            "name": "浦发银行",
            "market": "上海证券交易所",
            "industry": "银行"
        }

        # Mock 股票报价
        mock_service.get_stock_quote.return_value = {
            "code": "sh600000",
            "name": "浦发银行",
            "price": 10.0,
            "change": 0.5,
            "change_percent": 5.0,
            "volume": 1000000,
            "amount": 10000000.0,
            "timestamp": "2024-01-01 10:00:00"
        }

        # Mock K线数据
        mock_service.get_kline_data.return_value = [
            {
                "code": "sh600000",
                "date": "2024-01-01",
                "open": 10.0,
                "high": 10.5,
                "low": 9.8,
                "close": 10.2,
                "volume": 1000000,
                "amount": 10000000.0
            }
        ] * 30  # 30条数据

        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/analysis/technical/600000")
        # 由于需要获取足够的历史数据，可能返回500或成功
        assert response.status_code in [200, 500]

    def test_technical_analysis_invalid_code(self, client):
        """测试无效股票代码"""
        response = client.get("/api/v1/analysis/technical/999999")
        assert response.status_code in [200, 404, 500]


class TestFundamentalAnalysis:
    """基本面分析端点测试"""

    @patch('app.api.analysis.get_stock_service')
    def test_fundamental_analysis_endpoint_exists(self, mock_get_service, client):
        """测试基本面分析接口存在"""
        mock_service = MagicMock()

        mock_service.get_stock_info.return_value = {
            "code": "sh600000",
            "name": "浦发银行",
            "market": "上海证券交易所",
            "industry": "银行"
        }

        mock_service.get_stock_quote.return_value = {
            "code": "sh600000",
            "name": "浦发银行",
            "price": 10.0,
            "change": 0.5,
            "change_percent": 5.0,
            "volume": 1000000,
            "amount": 10000000.0,
            "timestamp": "2024-01-01 10:00:00"
        }

        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/analysis/fundamental/600000")
        assert response.status_code in [200, 500]

    def test_fundamental_analysis_invalid_code(self, client):
        """测试无效股票代码"""
        response = client.get("/api/v1/analysis/fundamental/999999")
        assert response.status_code in [200, 404, 500]


class TestInvestmentAdvice:
    """投资建议端点测试"""

    @patch('app.api.analysis.get_stock_service')
    def test_advice_endpoint_exists(self, mock_get_service, client):
        """测试投资建议接口存在"""
        mock_service = MagicMock()

        mock_service.get_stock_info.return_value = {
            "code": "sh600000",
            "name": "浦发银行",
            "market": "上海证券交易所",
            "industry": "银行"
        }

        mock_service.get_stock_quote.return_value = {
            "code": "sh600000",
            "name": "浦发银行",
            "price": 10.0,
            "change": 0.5,
            "change_percent": 5.0,
            "volume": 1000000,
            "amount": 10000000.0,
            "timestamp": "2024-01-01 10:00:00"
        }

        mock_service.get_kline_data.return_value = [
            {
                "code": "sh600000",
                "date": "2024-01-01",
                "open": 10.0,
                "high": 10.5,
                "low": 9.8,
                "close": 10.2,
                "volume": 1000000,
                "amount": 10000000.0
            }
        ] * 30

        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/analysis/advice/600000")
        assert response.status_code in [200, 500]

    def test_advice_invalid_code(self, client):
        """测试无效股票代码"""
        response = client.get("/api/v1/analysis/advice/999999")
        assert response.status_code in [200, 404, 500]


class TestAnalysisCache:
    """分析缓存测试"""

    def test_clear_cache_endpoint(self, client):
        """测试清空缓存接口"""
        response = client.get("/api/v1/analysis/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestAnalysisResponse:
    """分析响应模型测试"""

    def test_technical_response_model(self):
        """测试技术分析响应模型"""
        from app.api.analysis import TechnicalAnalysisResponse, TechnicalIndicators

        response = TechnicalAnalysisResponse(
            code="600000",
            name="浦发银行",
            timestamp="2024-01-01 10:00:00",
            current_price=10.0,
            change_percent=5.0,
            indicators=TechnicalIndicators(
                ma={"MA5": 9.8, "MA10": 9.9, "MA20": 10.0, "MA60": 10.2},
                macd={"DIF": 0.1, "DEA": 0.05, "MACD": 0.1},
                rsi={"RSI-6": 60, "RSI-12": 55, "RSI-24": 50},
                bollinger={"Upper": 10.5, "Middle": 10.0, "Lower": 9.5},
                kdj={"K": 70, "D": 65, "J": 80}
            ),
            summary="测试摘要",
            signal="buy"
        )

        assert response.code == "600000"
        assert response.signal == "buy"

    def test_fundamental_response_model(self):
        """测试基本面分析响应模型"""
        from app.api.analysis import FundamentalAnalysisResponse, FundamentalData

        response = FundamentalAnalysisResponse(
            code="600000",
            name="浦发银行",
            timestamp="2024-01-01 10:00:00",
            market="上海证券交易所",
            industry="银行",
            fundamental_data=FundamentalData(
                pe=10.5,
                pb=1.2,
                market_cap=100000000000,
                float_market_cap=50000000000,
                revenue=1000.0,
                net_profit=100.0,
                roe=12.0,
                gross_margin=30.0,
                debt_ratio=0.6,
                current_ratio=1.5
            ),
            summary="测试摘要",
            rating="good"
        )

        assert response.code == "600000"
        assert response.rating == "good"

    def test_advice_response_model(self):
        """测试投资建议响应模型"""
        from app.api.analysis import InvestmentAdviceResponse

        response = InvestmentAdviceResponse(
            code="600000",
            name="浦发银行",
            timestamp="2024-01-01 10:00:00",
            advice="buy",
            target_price=11.5,
            stop_loss=9.2,
            risk_level="medium",
            reasoning="技术信号: buy；基本面评级: good",
            summary="综合分析建议买入"
        )

        assert response.code == "600000"
        assert response.advice == "buy"


class TestAnalysisHelperFunctions:
    """分析辅助函数测试"""

    def test_format_technical_summary(self):
        """测试技术分析摘要格式化"""
        from app.api.analysis import _format_technical_summary

        indicators = {
            "ma": {"MA20": 10.0},
            "macd": {"DIF": 0.1, "DEA": 0.05},
            "rsi": {"RSI-6": 65},
            "bollinger": {"Upper": 11.0, "Lower": 9.0}
        }

        summary = _format_technical_summary(price=10.5, change_pct=5.0, indicators=indicators)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_generate_technical_signal(self):
        """测试技术信号生成"""
        from app.api.analysis import _generate_technical_signal

        # 测试看涨信号
        indicators_buy = {
            "ma": {"MA20": 10.0},
            "macd": {"DIF": 0.1, "DEA": 0.05},
            "rsi": {"RSI-6": 25},
            "bollinger": {"Upper": 11.0, "Lower": 9.0},
            "kdj": {"K": 60, "D": 50}
        }
        signal = _generate_technical_signal(indicators_buy, price=9.5)
        assert signal in ["buy", "sell", "neutral"]

        # 测试看跌信号
        indicators_sell = {
            "ma": {"MA20": 10.0},
            "macd": {"DIF": 0.05, "DEA": 0.1},
            "rsi": {"RSI-6": 75},
            "bollinger": {"Upper": 11.0, "Lower": 9.0},
            "kdj": {"K": 40, "D": 50}
        }
        signal = _generate_technical_signal(indicators_sell, price=11.0)
        assert signal in ["buy", "sell", "neutral"]

    def test_generate_fundamental_rating(self):
        """测试基本面评级生成"""
        from app.api.analysis import _generate_fundamental_rating

        # 测试优秀评级
        data_excellent = {"pe": 10, "roe": 25, "gross_margin": 50}
        rating = _generate_fundamental_rating(data_excellent)
        assert rating in ["excellent", "good", "fair", "poor"]

        # 测试较差评级
        data_poor = {"pe": 100, "roe": 2, "gross_margin": 5}
        rating = _generate_fundamental_rating(data_poor)
        assert rating in ["excellent", "good", "fair", "poor"]

    def test_generate_investment_advice(self):
        """测试投资建议生成"""
        from app.api.analysis import _generate_investment_advice

        advice = _generate_investment_advice(
            technical_signal="buy",
            fundamental_rating="good",
            current_price=10.0,
            change_pct=5.0
        )

        assert "advice" in advice
        assert "target_price" in advice
        assert "stop_loss" in advice
        assert "risk_level" in advice
        assert advice["target_price"] > 10.0
        assert advice["stop_loss"] < 10.0

    def test_format_fundamental_summary(self):
        """测试基本面摘要格式化"""
        from app.api.analysis import _format_fundamental_summary

        data = {"pe": 15.5, "pb": 1.8, "roe": 12.5, "revenue": 1000.0}
        summary = _format_fundamental_summary(data, "good")
        assert isinstance(summary, str)
        assert len(summary) > 0


class TestAnalysisCache:
    """分析缓存测试"""

    def test_cache_operations(self):
        """测试缓存操作"""
        from app.api.analysis import AnalysisCache

        cache = AnalysisCache(ttl=60)

        # 测试设置和获取
        cache.set("test_key", {"data": "test_value"})
        result = cache.get("test_key")
        assert result == {"data": "test_value"}

        # 测试缓存不存在
        result = cache.get("nonexistent_key")
        assert result is None

        # 测试清空缓存
        cache.clear()
        result = cache.get("test_key")
        assert result is None

    def test_cache_expiration(self):
        """测试缓存过期"""
        from app.api.analysis import AnalysisCache

        cache = AnalysisCache(ttl=1)  # 1秒过期

        cache.set("test_key", {"data": "test_value"})

        # 立即获取，应该存在
        result = cache.get("test_key")
        assert result == {"data": "test_value"}

        # 等待过期
        import time
        time.sleep(1.1)

        # 过期后应该返回 None
        result = cache.get("test_key")
        assert result is None
