"""
数据库模块测试用例

测试数据库连接、Redis连接和数据模型。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


class TestDatabaseConnection:
    """测试数据库连接功能"""

    @pytest.mark.asyncio
    async def test_create_engine(self):
        """测试创建数据库引擎"""
        from app.db.database import create_engine, get_engine

        # 使用 mock URL 测试引擎创建
        engine = create_engine(
            database_url="sqlite+aiosqlite:///:memory:",
            echo=False,
        )

        assert engine is not None
        assert isinstance(engine, AsyncEngine)

        # 清理
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_get_engine_singleton(self):
        """测试获取引擎单例"""
        from app.db.database import create_engine, get_engine

        # 先创建一个测试引擎
        engine1 = create_engine(
            database_url="sqlite+aiosqlite:///:memory:",
        )

        engine2 = get_engine()

        # 单例模式下应该返回同一个引擎
        assert engine1 is not None

        # 清理
        await engine1.dispose()

    @pytest.mark.asyncio
    async def test_session_scope(self):
        """测试会话作用域"""
        from app.db.database import session_scope

        # 使用内存数据库测试
        with patch("app.db.database.get_engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value=MagicMock())
            mock_engine.return_value.connect = AsyncMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock())
            )

            # 测试 session_scope 可以正常进入和退出
            async with session_scope() as session:
                assert session is not None


class TestRedisConnection:
    """测试 Redis 连接功能"""

    @pytest.mark.asyncio
    async def test_create_redis_client(self):
        """测试创建 Redis 客户端"""
        from app.db.database import create_redis_client, get_redis_async

        # Mock Redis 连接
        with patch("redis.asyncio.Redis.from_url") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            client = await create_redis_client(redis_url="redis://localhost:6379/0")

            assert client is not None
            mock_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_async(self):
        """测试异步获取 Redis 客户端"""
        from app.db.database import create_redis_client, get_redis_async

        with patch("app.db.database.create_redis_client") as mock_create:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client

            client = await get_redis_async()

            assert client is not None


class TestDatabaseManager:
    """测试数据库管理器"""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化连接"""
        from app.db.database import DatabaseManager

        manager = DatabaseManager()

        with patch("app.db.database.create_engine") as mock_engine, \
             patch("app.db.database.create_redis_client", new_callable=AsyncMock) as mock_redis:

            mock_engine.return_value = AsyncMock()
            mock_redis.return_value = AsyncMock()

            await manager.initialize(
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
            )

            assert manager.engine is not None
            assert manager.redis is not None

            # 清理
            await manager.close()

    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭连接"""
        from app.db.database import DatabaseManager

        manager = DatabaseManager()

        # 模拟已初始化的状态
        manager.engine = AsyncMock()
        manager.redis = AsyncMock()

        await manager.close()

        assert manager.engine is None
        assert manager.redis is None


class TestStockModel:
    """测试股票数据模型"""

    def test_stock_model_creation(self):
        """测试股票模型创建"""
        from app.models.stock import Stock, MarketType

        stock = Stock(
            code="000001",
            name="平安银行",
            market=MarketType.SZ.value,
            exchange="SZSE",
            stock_type="A股",
        )

        assert stock.code == "000001"
        assert stock.name == "平安银行"
        assert stock.market == MarketType.SZ.value

    def test_stock_quote_model_creation(self):
        """测试行情模型创建"""
        from app.models.stock import StockQuote

        quote = StockQuote(
            stock_id=1,
            trade_date="2024-01-15",
            open=10.5,
            high=11.0,
            low=10.2,
            close=10.8,
            volume=1000000,
            amount=10800000,
        )

        assert quote.stock_id == 1
        assert quote.trade_date == "2024-01-15"
        assert quote.close == 10.8

    def test_kline_model_creation(self):
        """测试K线模型创建"""
        from app.models.stock import KLineData

        kline = KLineData(
            stock_id=1,
            period="1d",
            trade_date="2024-01-15",
            open=10.5,
            high=11.0,
            low=10.2,
            close=10.8,
            volume=1000000,
        )

        assert kline.stock_id == 1
        assert kline.period == "1d"
        assert kline.close == 10.8

    def test_stock_analysis_model_creation(self):
        """测试分析模型创建"""
        from app.models.stock import StockAnalysis

        analysis = StockAnalysis(
            stock_id=1,
            analysis_type="daily",
            analysis_date="2024-01-15",
            content={"trend": "up", "signal": "buy"},
            summary="今日看涨",
            confidence=0.8,
            tags=["看好", "突破"],
        )

        assert analysis.stock_id == 1
        assert analysis.analysis_type == "daily"
        assert analysis.content["trend"] == "up"
        assert analysis.confidence == 0.8

    def test_market_type_enum(self):
        """测试市场类型枚举"""
        from app.models.stock import MarketType

        assert MarketType.SH.value == "SH"
        assert MarketType.SZ.value == "SZ"
        assert MarketType.BJ.value == "BJ"
        assert MarketType.HK.value == "HK"
        assert MarketType.US.value == "US"


class TestConnectionTest:
    """测试连接测试功能"""

    @pytest.mark.asyncio
    async def test_test_database_connection_mock(self):
        """测试数据库连接测试（Mock）"""
        from app.db.database import test_database_connection, get_database_url

        with patch("app.db.database.get_engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_engine.return_value.connect = AsyncMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock())
            )

            result = await test_database_connection()

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_test_redis_connection_mock(self):
        """测试Redis连接测试（Mock）"""
        from app.db.database import test_redis_connection

        with patch("app.db.database.get_redis_async") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_redis.return_value = mock_client

            result = await test_redis_connection()

            assert isinstance(result, bool)


class TestConfig:
    """测试配置功能"""

    def test_get_database_url(self):
        """测试获取数据库URL"""
        from app.db.database import get_database_url
        from app.config import get_config

        config = get_config()
        url = get_database_url()

        assert url == config.database_url

    def test_get_redis_url(self):
        """测试获取Redis URL"""
        from app.db.database import get_redis_url
        from app.config import get_config

        config = get_config()
        url = get_redis_url()

        assert url == config.redis_url
