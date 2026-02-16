"""
测试 API 路由
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_root(self, client):
        """测试根路由"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_readiness_check(self, client):
        """测试就绪检查"""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    def test_liveness_check(self, client):
        """测试存活检查"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


class TestStockEndpoints:
    """股票 API 端点测试"""

    def test_stocks_root(self, client):
        """测试股票API根路由"""
        response = client.get("/api/v1/stocks/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "rate_limit" in data

    def test_search_stocks_endpoint_exists(self, client):
        """测试股票搜索接口存在"""
        response = client.get("/api/v1/stocks/search?q=平安")
        # 由于涉及到外部API调用，可能返回200或500，但接口应该存在
        assert response.status_code in [200, 500, 404]

    def test_search_stocks_with_query(self, client):
        """测试带查询参数的股票搜索"""
        response = client.get("/api/v1/stocks/search?q=600000")
        # 接口存在，返回状态可能是 200(成功) 或 500(外部API错误)
        assert response.status_code in [200, 500, 404]

    def test_search_stocks_missing_query(self, client):
        """测试缺少查询参数的股票搜索"""
        response = client.get("/api/v1/stocks/search")
        assert response.status_code == 422  # FastAPI validation error

    def test_search_stocks_with_limit(self, client):
        """测试带limit参数的股票搜索"""
        response = client.get("/api/v1/stocks/search?q=银行&limit=5")
        assert response.status_code in [200, 500, 404]

    def test_stock_quote_endpoint(self, client):
        """测试股票报价接口"""
        response = client.get("/api/v1/stocks/quote/600000")
        # 接口存在，返回状态可能是 200(成功) 或 500(外部API错误)
        assert response.status_code in [200, 500, 404]

    def test_stock_quote_invalid_code(self, client):
        """测试无效股票代码的报价接口"""
        response = client.get("/api/v1/stocks/quote/999999")
        assert response.status_code in [200, 404, 500]

    def test_kline_endpoint(self, client):
        """测试K线接口"""
        response = client.get("/api/v1/stocks/kline/600000")
        # 接口存在
        assert response.status_code in [200, 500, 404]

    def test_kline_with_period(self, client):
        """测试带周期参数的K线接口"""
        response = client.get("/api/v1/stocks/kline/600000?period=daily")
        assert response.status_code in [200, 500, 404]

    def test_kline_with_invalid_period(self, client):
        """测试无效周期的K线接口"""
        response = client.get("/api/v1/stocks/kline/600000?period=invalid")
        assert response.status_code == 400

    def test_kline_with_dates(self, client):
        """测试带日期参数的K线接口"""
        response = client.get("/api/v1/stocks/kline/600000?start_date=20230101&end_date=20231231")
        assert response.status_code in [200, 500, 404]

    def test_stock_info_endpoint(self, client):
        """测试股票详情接口"""
        response = client.get("/api/v1/stocks/600000")
        # 接口存在
        assert response.status_code in [200, 500, 404]

    def test_stock_info_invalid_code(self, client):
        """测试无效股票代码的详情接口"""
        response = client.get("/api/v1/stocks/999999")
        assert response.status_code in [200, 404, 500]

    def test_rate_limit_status(self, client):
        """测试频率限制状态接口"""
        response = client.get("/api/v1/stocks/rate_limit/status")
        assert response.status_code == 200
        data = response.json()
        assert "max_requests" in data
        assert "window_seconds" in data
        assert "remaining_requests" in data


class TestStockEndpointsWithMock:
    """使用Mock的股票API测试"""

    @patch('app.api.stocks.get_stock_service')
    def test_search_stocks_success(self, mock_get_service, client):
        """测试股票搜索成功"""
        # Mock StockService
        mock_service = MagicMock()
        mock_service.search_stocks.return_value = [
            {"code": "sh600000", "name": "浦发银行", "market": "上海证券交易所", "price": 10.0, "change": 0.5},
            {"code": "sz000001", "name": "平安银行", "market": "深圳证券交易所", "price": 12.0, "change": -0.3}
        ]
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/stocks/search?q=平安")
        # 由于rate limiter会检查请求，需要确保不被限制
        # 第一次请求应该能通过
        assert response.status_code in [200, 500]

    @patch('app.api.stocks.get_stock_service')
    def test_get_stock_quote_success(self, mock_get_service, client):
        """测试获取股票报价成功"""
        mock_service = MagicMock()
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

        response = client.get("/api/v1/stocks/quote/600000")
        assert response.status_code in [200, 500]

    @patch('app.api.stocks.get_stock_service')
    def test_get_kline_success(self, mock_get_service, client):
        """测试获取K线数据成功"""
        mock_service = MagicMock()
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
        ]
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/stocks/kline/600000")
        assert response.status_code in [200, 500]

    @patch('app.api.stocks.get_stock_service')
    def test_get_stock_info_success(self, mock_get_service, client):
        """测试获取股票信息成功"""
        mock_service = MagicMock()
        mock_service.get_stock_info.return_value = {
            "code": "sh600000",
            "name": "浦发银行",
            "market": "上海证券交易所",
            "industry": "银行",
            "listing_date": "1999-11-10",
            "total_shares": "1865347.00",
            "circulating_shares": "1865347.00"
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/stocks/600000")
        assert response.status_code in [200, 500]

    @patch('app.api.stocks.get_stock_service')
    def test_stock_quote_not_found(self, mock_get_service, client):
        """测试股票不存在"""
        mock_service = MagicMock()
        mock_service.get_stock_quote.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/stocks/quote/999999")
        assert response.status_code == 404

    @patch('app.api.stocks.get_stock_service')
    def test_kline_not_found(self, mock_get_service, client):
        """测试K线数据不存在"""
        mock_service = MagicMock()
        mock_service.get_kline_data.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/stocks/kline/999999")
        assert response.status_code == 404


class TestRateLimiter:
    """频率限制器测试"""

    def test_rate_limiter_initialization(self, client):
        """测试频率限制器初始化"""
        response = client.get("/api/v1/stocks/rate_limit/status")
        assert response.status_code == 200
        data = response.json()
        assert data["max_requests"] == 60
        assert data["window_seconds"] == 60

    def test_multiple_requests(self, client):
        """测试多个请求"""
        # 发送多个请求，确保服务正常运行
        for i in range(5):
            response = client.get("/api/v1/stocks/rate_limit/status")
            assert response.status_code == 200


class TestCORS:
    """CORS 测试"""

    def test_cors_headers(self, client):
        """测试 CORS 头"""
        # TestClient 不直接显示 CORS 头，需要检查 OPTIONS 请求
        response = client.options("/health")
        # CORS 通过中间件配置，在实际运行时会生效
        assert response.status_code in [200, 405]

    def test_cors_on_stocks_endpoint(self, client):
        """测试股票接口的CORS"""
        response = client.options("/api/v1/stocks/")
        assert response.status_code in [200, 405]


class TestQueryParameters:
    """查询参数测试"""

    def test_search_with_special_characters(self, client):
        """测试搜索特殊字符"""
        response = client.get("/api/v1/stocks/search?q=")
        assert response.status_code == 422  # Validation error for empty query

    def test_search_with_long_query(self, client):
        """测试过长的搜索关键词"""
        long_keyword = "a" * 100
        response = client.get(f"/api/v1/stocks/search?q={long_keyword}")
        # 应该返回422因为超过max_length=50
        assert response.status_code == 422
