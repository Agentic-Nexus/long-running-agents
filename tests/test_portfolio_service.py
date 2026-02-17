"""
投资组合服务测试用例

测试投资组合管理、持仓管理、交易记录和收益计算功能。
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.services.portfolio_service import PortfolioService
from app.models.portfolio import (
    Portfolio,
    Position,
    Transaction,
    PortfolioHistory,
    PortfolioStatus,
    PositionType,
    TransactionType,
)


class TestPortfolioService:
    """投资组合服务测试类"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        session.add = Mock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def portfolio_service(self, mock_session):
        """创建投资组合服务实例"""
        return PortfolioService(mock_session)

    def test_portfolio_status(self):
        """测试投资组合状态枚举"""
        assert PortfolioStatus.ACTIVE.value == "active"
        assert PortfolioStatus.CLOSED.value == "closed"
        assert PortfolioStatus.ARCHIVED.value == "archived"

    def test_position_type(self):
        """测试持仓类型枚举"""
        assert PositionType.LONG.value == "long"
        assert PositionType.SHORT.value == "short"

    def test_transaction_type(self):
        """测试交易类型枚举"""
        assert TransactionType.BUY.value == "buy"
        assert TransactionType.SELL.value == "sell"
        assert TransactionType.DIVIDEND.value == "dividend"
        assert TransactionType.SPLIT.value == "split"
        assert TransactionType.MERGE.value == "merge"

    @pytest.mark.asyncio
    async def test_create_portfolio(self, portfolio_service, mock_session):
        """测试创建投资组合"""
        # 模拟返回的 Portfolio 对象
        mock_portfolio = Portfolio(
            id=1,
            user_id=1,
            name="Test Portfolio",
            description="Test Description",
            initial_capital=100000.0,
            current_value=100000.0,
            status=PortfolioStatus.ACTIVE.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟 session.add
        mock_session.add = Mock()

        # 模拟 commit 和 refresh
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(side_effect=lambda x: setattr(x, '__dict__', mock_portfolio.__dict__))

        # 执行创建
        portfolio = await portfolio_service.create_portfolio(
            user_id=1,
            name="Test Portfolio",
            description="Test Description",
            initial_capital=100000.0,
        )

        assert portfolio.name == "Test Portfolio"
        assert portfolio.initial_capital == 100000.0

    @pytest.mark.asyncio
    async def test_get_portfolio(self, portfolio_service, mock_session):
        """测试获取投资组合"""
        # 模拟返回的 Portfolio 对象
        mock_portfolio = Portfolio(
            id=1,
            user_id=1,
            name="Test Portfolio",
            initial_capital=100000.0,
            current_value=100000.0,
            status=PortfolioStatus.ACTIVE.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟 execute 返回值
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_portfolio)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # 执行获取
        portfolio = await portfolio_service.get_portfolio(1, 1)

        assert portfolio is not None
        assert portfolio.id == 1

    @pytest.mark.asyncio
    async def test_get_portfolio_not_found(self, portfolio_service, mock_session):
        """测试获取不存在的投资组合"""
        # 模拟返回 None
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        portfolio = await portfolio_service.get_portfolio(999, 1)

        assert portfolio is None

    @pytest.mark.asyncio
    async def test_get_user_portfolios(self, portfolio_service, mock_session):
        """测试获取用户的所有投资组合"""
        # 模拟返回的 Portfolio 列表
        mock_portfolios = [
            Portfolio(
                id=1,
                user_id=1,
                name="Portfolio 1",
                initial_capital=100000.0,
                current_value=100000.0,
                status=PortfolioStatus.ACTIVE.value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Portfolio(
                id=2,
                user_id=1,
                name="Portfolio 2",
                initial_capital=50000.0,
                current_value=55000.0,
                status=PortfolioStatus.ACTIVE.value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        # 模拟 execute 返回值
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=mock_portfolios)))
        mock_session.execute = AsyncMock(return_value=mock_result)

        portfolios = await portfolio_service.get_user_portfolios(1)

        assert len(portfolios) == 2

    @pytest.mark.asyncio
    async def test_update_portfolio(self, portfolio_service, mock_session):
        """测试更新投资组合"""
        # 模拟返回的 Portfolio 对象
        mock_portfolio = Portfolio(
            id=1,
            user_id=1,
            name="Updated Portfolio",
            description="Updated Description",
            initial_capital=100000.0,
            current_value=100000.0,
            status=PortfolioStatus.ACTIVE.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟 execute 返回值
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_portfolio)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # 执行更新
        portfolio = await portfolio_service.update_portfolio(
            portfolio_id=1,
            user_id=1,
            name="Updated Portfolio",
            description="Updated Description",
        )

        assert portfolio.name == "Updated Portfolio"

    @pytest.mark.asyncio
    async def test_delete_portfolio(self, portfolio_service, mock_session):
        """测试删除投资组合"""
        # 模拟返回的 Portfolio 对象
        mock_portfolio = Portfolio(
            id=1,
            user_id=1,
            name="Test Portfolio",
            initial_capital=100000.0,
            current_value=100000.0,
            status=PortfolioStatus.ACTIVE.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟 execute 返回值
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_portfolio)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        # 执行删除
        success = await portfolio_service.delete_portfolio(1, 1)

        assert success is True

    @pytest.mark.asyncio
    async def test_get_position(self, portfolio_service, mock_session):
        """测试获取持仓"""
        # 模拟返回的 Position 对象
        mock_position = Position(
            id=1,
            portfolio_id=1,
            stock_code="600000",
            stock_name="浦发银行",
            quantity=1000.0,
            cost_price=10.0,
            total_cost=10000.0,
            position_type=PositionType.LONG.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟 execute 返回值
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_position)
        mock_session.execute = AsyncMock(return_value=mock_result)

        position = await portfolio_service.get_position(1, "600000")

        assert position is not None
        assert position.stock_code == "600000"

    @pytest.mark.asyncio
    async def test_add_transaction_buy(self, portfolio_service, mock_session):
        """测试添加买入交易"""
        # 模拟返回的 Transaction 对象
        mock_transaction = Transaction(
            id=1,
            portfolio_id=1,
            stock_code="600000",
            stock_name="浦发银行",
            transaction_type=TransactionType.BUY.value,
            quantity=1000.0,
            price=10.0,
            amount=10000.0,
            commission=10.0,
            trade_date="2024-01-01",
            created_at=datetime.utcnow(),
        )

        # 模拟 execute 返回值 (持仓不存在)
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # 执行添加交易
        transaction = await portfolio_service.add_transaction(
            portfolio_id=1,
            stock_code="600000",
            stock_name="浦发银行",
            transaction_type=TransactionType.BUY.value,
            quantity=1000.0,
            price=10.0,
            trade_date="2024-01-01",
            commission=10.0,
        )

        assert transaction.stock_code == "600000"

    @pytest.mark.asyncio
    async def test_calculate_returns(self, portfolio_service, mock_session):
        """测试计算收益"""
        # 模拟返回的 Portfolio 对象
        mock_portfolio = Portfolio(
            id=1,
            user_id=1,
            name="Test Portfolio",
            initial_capital=100000.0,
            current_value=120000.0,
            status=PortfolioStatus.ACTIVE.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟持仓列表
        mock_positions = [
            Position(
                id=1,
                portfolio_id=1,
                stock_code="600000",
                quantity=1000.0,
                cost_price=10.0,
                total_cost=10000.0,
                current_price=12.0,
                market_value=12000.0,
                profit_loss=2000.0,
                profit_loss_pct=20.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        # 先模拟获取组合
        mock_result_portfolio = Mock()
        mock_result_portfolio.scalar_one_or_none = Mock(return_value=mock_portfolio)
        mock_session.execute = AsyncMock(return_value=mock_result_portfolio)

        # 修改 mock 以支持多次调用
        call_count = [0]
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result_portfolio
            mock_result_positions = Mock()
            mock_result_positions.scalars = Mock(return_value=Mock(all=Mock(return_value=mock_positions)))
            return mock_result_positions

        mock_session.execute = AsyncMock(side_effect=execute_side_effect)

        # 执行计算收益
        returns = await portfolio_service.calculate_returns(1)

        assert "profit_loss" in returns
        assert "profit_loss_pct" in returns

    @pytest.mark.asyncio
    async def test_generate_portfolio_report(self, portfolio_service, mock_session):
        """测试生成投资组合报告"""
        # 模拟返回的 Portfolio 对象
        mock_portfolio = Portfolio(
            id=1,
            user_id=1,
            name="Test Portfolio",
            description="Test Description",
            initial_capital=100000.0,
            current_value=120000.0,
            status=PortfolioStatus.ACTIVE.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟持仓列表
        mock_positions = [
            Position(
                id=1,
                portfolio_id=1,
                stock_code="600000",
                stock_name="浦发银行",
                quantity=1000.0,
                cost_price=10.0,
                total_cost=10000.0,
                current_price=12.0,
                market_value=12000.0,
                profit_loss=2000.0,
                profit_loss_pct=20.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        # 模拟返回数据
        mock_portfolio_result = Mock()
        mock_portfolio_result.scalar_one_or_none = Mock(return_value=mock_portfolio)

        mock_positions_result = Mock()
        mock_positions_result.scalars = Mock(return_value=Mock(all=Mock(return_value=mock_positions)))

        mock_history_result = Mock()
        mock_history_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        call_count = [0]
        def execute_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_portfolio_result
            elif call_count[0] == 2:
                return mock_positions_result
            else:
                return mock_history_result

        mock_session.execute = AsyncMock(side_effect=execute_side_effect)

        # 执行生成报告
        report = await portfolio_service.generate_portfolio_report(1)

        assert "portfolio" in report
        assert "returns" in report
        assert "positions" in report
        assert report["total_positions"] == 1
