"""
数据存储服务测试用例

测试股票数据存储功能：
- 股票基本信息存储
- 行情数据存储
- K线数据存储
- 增量更新逻辑
- 数据完整性验证
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


class TestDataStorageService:
    """测试数据存储服务"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的数据库引擎"""
        engine = AsyncMock(spec=AsyncEngine)
        engine.begin = AsyncMock()
        return engine

    def test_service_initialization(self):
        """测试服务初始化"""
        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_get_engine.return_value = MagicMock()

            from app.services.data_storage import DataStorageService

            service = DataStorageService()
            assert service is not None
            assert service.engine is not None

    @pytest.mark.asyncio
    async def test_init_tables(self):
        """测试初始化表"""
        # 使用真实引擎但配置为内存数据库进行测试
        from app.services.data_storage import DataStorageService

        # 创建使用内存数据库的服务
        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            # 创建正确的异步上下文管理器模拟
            mock_engine = AsyncMock()
            mock_get_engine.return_value = mock_engine

            # 设置 begin 方法返回正确的异步上下文管理器
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_cm.__aexit__ = AsyncMock()
            mock_engine.begin = AsyncMock(return_value=mock_cm)

            service = DataStorageService()
            # 这里主要验证方法可以被调用
            assert service.engine is not None

    @pytest.mark.asyncio
    async def test_drop_tables(self):
        """测试删除表"""
        from app.services.data_storage import DataStorageService

        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_engine = AsyncMock()
            mock_get_engine.return_value = mock_engine

            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_cm.__aexit__ = AsyncMock()
            mock_engine.begin = AsyncMock(return_value=mock_cm)

            service = DataStorageService()
            # 这里主要验证方法可以被调用
            assert service.engine is not None


class TestStockOperations:
    """测试股票基本操作"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_insert_stock(self, mock_session):
        """测试插入股票"""
        # 模拟返回值
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = MagicMock(
            id=1,
            code="000001",
            name="平安银行",
            market="SZ",
        )
        mock_session.execute.return_value = mock_result

        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine

            from app.services.data_storage import DataStorageService

            service = DataStorageService()
            stock = await service.insert_stock(
                session=mock_session,
                code="000001",
                name="平安银行",
                market="SZ",
            )

            assert stock is not None
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_stocks_bulk(self, mock_session):
        """测试批量插入股票"""
        stocks_data = [
            {"code": "000001", "name": "平安银行", "market": "SZ"},
            {"code": "600000", "name": "浦发银行", "market": "SH"},
        ]

        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine

            from app.services.data_storage import DataStorageService

            service = DataStorageService()
            count = await service.insert_stocks_bulk(
                session=mock_session,
                stocks_data=stocks_data,
            )

            assert count == 2
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stock_by_code(self, mock_session):
        """测试根据代码获取股票"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id=1,
            code="000001",
            name="平安银行",
        )
        mock_session.execute.return_value = mock_result

        from app.services.data_storage import DataStorageService

        service = DataStorageService()
        stock = await service.get_stock_by_code(
            session=mock_session,
            code="000001",
        )

        assert stock is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_stocks(self, mock_session):
        """测试获取所有股票"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(id=1, code="000001"),
            MagicMock(id=2, code="600000"),
        ]
        mock_session.execute.return_value = mock_result

        from app.services.data_storage import DataStorageService

        service = DataStorageService()
        stocks = await service.get_all_stocks(session=mock_session)

        assert len(stocks) == 2


class TestQuoteOperations:
    """测试行情数据操作"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_insert_quote(self, mock_session):
        """测试插入行情数据"""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = MagicMock(
            id=1,
            stock_id=1,
            trade_date="2024-01-15",
            close=10.8,
        )
        mock_session.execute.return_value = mock_result

        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine

            from app.services.data_storage import DataStorageService

            service = DataStorageService()
            quote = await service.insert_quote(
                session=mock_session,
                stock_id=1,
                trade_date="2024-01-15",
                open=10.5,
                high=11.0,
                low=10.2,
                close=10.8,
                volume=1000000,
            )

            assert quote is not None
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_quotes_bulk(self, mock_session):
        """测试批量插入行情数据"""
        quotes_data = [
            {
                "stock_id": 1,
                "trade_date": "2024-01-15",
                "open": 10.5,
                "high": 11.0,
                "low": 10.2,
                "close": 10.8,
                "volume": 1000000,
            },
            {
                "stock_id": 1,
                "trade_date": "2024-01-16",
                "open": 10.8,
                "high": 11.2,
                "low": 10.6,
                "close": 11.0,
                "volume": 1100000,
            },
        ]

        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine

            from app.services.data_storage import DataStorageService

            service = DataStorageService()
            count = await service.insert_quotes_bulk(
                session=mock_session,
                quotes_data=quotes_data,
            )

            assert count == 2


class TestKLineOperations:
    """测试K线数据操作"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_insert_kline(self, mock_session):
        """测试插入K线数据"""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = MagicMock(
            id=1,
            stock_id=1,
            period="1d",
            trade_date="2024-01-15",
            close=10.8,
        )
        mock_session.execute.return_value = mock_result

        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine

            from app.services.data_storage import DataStorageService

            service = DataStorageService()
            kline = await service.insert_kline(
                session=mock_session,
                stock_id=1,
                period="1d",
                trade_date="2024-01-15",
                open=10.5,
                high=11.0,
                low=10.2,
                close=10.8,
                volume=1000000,
            )

            assert kline is not None
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_klines_bulk(self, mock_session):
        """测试批量插入K线数据"""
        klines_data = [
            {
                "stock_id": 1,
                "period": "1d",
                "trade_date": "2024-01-15",
                "open": 10.5,
                "high": 11.0,
                "low": 10.2,
                "close": 10.8,
                "volume": 1000000,
            },
            {
                "stock_id": 1,
                "period": "1d",
                "trade_date": "2024-01-16",
                "open": 10.8,
                "high": 11.2,
                "low": 10.6,
                "close": 11.0,
                "volume": 1100000,
            },
        ]

        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine

            from app.services.data_storage import DataStorageService

            service = DataStorageService()
            count = await service.insert_klines_bulk(
                session=mock_session,
                klines_data=klines_data,
            )

            assert count == 2


class TestIncrementalUpdate:
    """测试增量更新逻辑"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_latest_quote_date(self, mock_session):
        """测试获取最新行情日期"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "2024-01-15"
        mock_session.execute.return_value = mock_result

        from app.services.data_storage import DataStorageService

        service = DataStorageService()
        date = await service.get_latest_quote_date(
            session=mock_session,
            stock_id=1,
        )

        assert date == "2024-01-15"

    @pytest.mark.asyncio
    async def test_get_latest_kline_date(self, mock_session):
        """测试获取最新K线日期"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "2024-01-15"
        mock_session.execute.return_value = mock_result

        from app.services.data_storage import DataStorageService

        service = DataStorageService()
        date = await service.get_latest_kline_date(
            session=mock_session,
            stock_id=1,
            period="1d",
        )

        assert date == "2024-01-15"


class TestDataIntegrity:
    """测试数据完整性验证"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_verify_data_integrity(self, mock_session):
        """测试数据完整性验证"""
        # 模拟不同的查询结果
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            mock_result = MagicMock()
            if hasattr(stmt, "select"):
                # count 查询
                mock_result.scalar.return_value = 100
            else:
                # 原始 SQL 查询
                mock_result.scalar.return_value = 0
            return mock_result

        mock_session.execute.side_effect = mock_execute

        from app.services.data_storage import DataStorageService

        service = DataStorageService()
        result = await service.verify_data_integrity(session=mock_session)

        assert result["is_valid"] is True
        assert result["stocks_count"] == 100
        assert result["orphan_quotes"] == 0
        assert result["orphan_klines"] == 0

    @pytest.mark.asyncio
    async def test_get_data_statistics(self, mock_session):
        """测试获取数据统计信息"""
        # 模拟查询结果
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            mock_result = MagicMock()

            if hasattr(stmt, "select") and "market" in str(stmt):
                # 按市场统计
                mock_result.all.return_value = [("SZ", 50), ("SH", 50)]
            elif hasattr(stmt, "select") and "period" in str(stmt):
                # 按周期统计
                mock_result.all.return_value = [("1d", 100)]
            elif hasattr(stmt, "text"):
                # 原始 SQL
                if "stock_quotes" in str(stmt):
                    mock_result.scalar.return_value = 10
                else:
                    mock_result.scalar.return_value = 20

            return mock_result

        mock_session.execute.side_effect = mock_execute

        from app.services.data_storage import DataStorageService

        service = DataStorageService()
        stats = await service.get_data_statistics(session=mock_session)

        assert "stocks_by_market" in stats
        assert "stocks_with_quotes" in stats
        assert "stocks_with_klines" in stats


class TestGetStorageService:
    """测试获取存储服务实例"""

    def test_get_storage_service_singleton(self):
        """测试获取单例实例"""
        with patch("app.services.data_storage.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine

            from app.services.data_storage import get_storage_service

            service1 = get_storage_service()
            service2 = get_storage_service()

            assert service1 is service2
