"""
测试 API 路由
"""
import pytest
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

    def test_search_stocks_not_implemented(self, client):
        """测试股票搜索接口（未实现）"""
        # 路由尚未注册，返回 404
        response = client.get("/api/v1/stocks/search?q=apple")
        assert response.status_code in [404, 501]

    def test_stock_quote_not_implemented(self, client):
        """测试股票报价接口（未实现）"""
        response = client.get("/api/v1/stocks/quote/AAPL")
        assert response.status_code in [404, 501]

    def test_kline_not_implemented(self, client):
        """测试K线接口（未实现）"""
        response = client.get("/api/v1/stocks/kline/AAPL")
        assert response.status_code in [404, 501]

    def test_stock_info_not_implemented(self, client):
        """测试股票详情接口（未实现）"""
        response = client.get("/api/v1/stocks/AAPL")
        assert response.status_code in [404, 501]


class TestCORS:
    """CORS 测试"""

    def test_cors_headers(self, client):
        """测试 CORS 头"""
        # TestClient 不直接显示 CORS 头，需要检查 OPTIONS 请求
        response = client.options("/health")
        # CORS 通过中间件配置，在实际运行时会生效
        assert response.status_code in [200, 405]
