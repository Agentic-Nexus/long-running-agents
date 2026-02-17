"""
投资组合服务模块

提供投资组合管理功能：
- 投资组合的 CRUD 操作
- 持仓管理
- 交易记录
- 收益计算
- 历史记录追踪
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.portfolio import (
    Portfolio,
    Position,
    Transaction,
    PortfolioHistory,
    PortfolioStatus,
    PositionType,
    TransactionType,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioService:
    """投资组合服务类"""

    def __init__(self, db: AsyncSession):
        """
        初始化投资组合服务

        Args:
            db: 数据库会话
        """
        self.db = db

    # ============================================
    # 投资组合操作
    # ============================================

    async def create_portfolio(
        self,
        user_id: int,
        name: str,
        initial_capital: float,
        description: Optional[str] = None,
    ) -> Portfolio:
        """
        创建投资组合

        Args:
            user_id: 用户ID
            name: 组合名称
            initial_capital: 初始资金
            description: 组合描述

        Returns:
            创建的投资组合
        """
        portfolio = Portfolio(
            user_id=user_id,
            name=name,
            description=description,
            initial_capital=initial_capital,
            current_value=initial_capital,
            status=PortfolioStatus.ACTIVE.value,
        )
        self.db.add(portfolio)
        await self.db.commit()
        await self.db.refresh(portfolio)
        logger.info(f"Created portfolio: {portfolio.id} for user {user_id}")
        return portfolio

    async def get_portfolio(self, portfolio_id: int, user_id: int) -> Optional[Portfolio]:
        """
        获取投资组合

        Args:
            portfolio_id: 组合ID
            user_id: 用户ID

        Returns:
            投资组合，如果不存在返回 None
        """
        stmt = select(Portfolio).where(
            and_(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_portfolios(self, user_id: int, status: Optional[str] = None) -> List[Portfolio]:
        """
        获取用户的所有投资组合

        Args:
            user_id: 用户ID
            status: 状态过滤

        Returns:
            投资组合列表
        """
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        if status:
            stmt = stmt.where(Portfolio.status == status)
        stmt = stmt.order_by(Portfolio.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_portfolio(
        self,
        portfolio_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Portfolio]:
        """
        更新投资组合

        Args:
            portfolio_id: 组合ID
            user_id: 用户ID
            name: 组合名称
            description: 组合描述
            status: 状态

        Returns:
            更新后的投资组合
        """
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        if name is not None:
            portfolio.name = name
        if description is not None:
            portfolio.description = description
        if status is not None:
            portfolio.status = status

        await self.db.commit()
        await self.db.refresh(portfolio)
        logger.info(f"Updated portfolio: {portfolio_id}")
        return portfolio

    async def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        """
        删除投资组合

        Args:
            portfolio_id: 组合ID
            user_id: 用户ID

        Returns:
            是否成功删除
        """
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False

        await self.db.delete(portfolio)
        await self.db.commit()
        logger.info(f"Deleted portfolio: {portfolio_id}")
        return True

    # ============================================
    # 持仓操作
    # ============================================

    async def get_position(self, portfolio_id: int, stock_code: str) -> Optional[Position]:
        """
        获取持仓

        Args:
            portfolio_id: 组合ID
            stock_code: 股票代码

        Returns:
            持仓信息
        """
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.stock_code == stock_code
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_portfolio_positions(self, portfolio_id: int) -> List[Position]:
        """
        获取组合的所有持仓

        Args:
            portfolio_id: 组合ID

        Returns:
            持仓列表
        """
        stmt = select(Position).where(Position.portfolio_id == portfolio_id)
        stmt = stmt.order_by(Position.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_position(
        self,
        portfolio_id: int,
        stock_code: str,
        quantity: float,
        cost_price: float,
        stock_name: Optional[str] = None,
    ) -> Position:
        """
        更新持仓

        Args:
            portfolio_id: 组合ID
            stock_code: 股票代码
            quantity: 持仓数量
            cost_price: 成本价
            stock_name: 股票名称

        Returns:
            持仓信息
        """
        position = await self.get_position(portfolio_id, stock_code)

        if position:
            position.quantity = quantity
            position.cost_price = cost_price
            position.total_cost = quantity * cost_price
            if stock_name:
                position.stock_name = stock_name
        else:
            position = Position(
                portfolio_id=portfolio_id,
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                cost_price=cost_price,
                total_cost=quantity * cost_price,
                position_type=PositionType.LONG.value,
            )
            self.db.add(position)

        await self.db.commit()
        await self.db.refresh(position)
        return position

    async def delete_position(self, portfolio_id: int, stock_code: str) -> bool:
        """
        删除持仓

        Args:
            portfolio_id: 组合ID
            stock_code: 股票代码

        Returns:
            是否成功删除
        """
        position = await self.get_position(portfolio_id, stock_code)
        if not position:
            return False

        await self.db.delete(position)
        await self.db.commit()
        return True

    # ============================================
    # 交易操作
    # ============================================

    async def add_transaction(
        self,
        portfolio_id: int,
        stock_code: str,
        transaction_type: str,
        quantity: float,
        price: float,
        trade_date: str,
        stock_name: Optional[str] = None,
        commission: float = 0.0,
        notes: Optional[str] = None,
    ) -> Transaction:
        """
        添加交易记录

        Args:
            portfolio_id: 组合ID
            stock_code: 股票代码
            transaction_type: 交易类型
            quantity: 交易数量
            price: 交易价格
            trade_date: 交易日期
            stock_name: 股票名称
            commission: 手续费
            notes: 备注

        Returns:
            交易记录
        """
        amount = quantity * price
        transaction = Transaction(
            portfolio_id=portfolio_id,
            stock_code=stock_code,
            stock_name=stock_name,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            amount=amount,
            commission=commission,
            trade_date=trade_date,
            notes=notes,
        )
        self.db.add(transaction)

        # 更新持仓
        position = await self.get_position(portfolio_id, stock_code)

        if transaction_type == TransactionType.BUY.value:
            if position:
                # 买入，增加持仓
                new_quantity = position.quantity + quantity
                new_total_cost = position.total_cost + amount + commission
                position.cost_price = new_total_cost / new_quantity if new_quantity > 0 else 0
                position.quantity = new_quantity
                position.total_cost = new_total_cost
            else:
                # 新建持仓
                position = Position(
                    portfolio_id=portfolio_id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    quantity=quantity,
                    cost_price=(amount + commission) / quantity,
                    total_cost=amount + commission,
                    position_type=PositionType.LONG.value,
                )
                self.db.add(position)

        elif transaction_type == TransactionType.SELL.value:
            if position:
                # 卖出，减少持仓
                position.quantity -= quantity
                if position.quantity <= 0:
                    await self.db.delete(position)
                else:
                    # 调整成本
                    cost_per_share = position.total_cost / (position.quantity + quantity)
                    position.total_cost = position.quantity * cost_per_share
                    position.cost_price = cost_per_share

        await self.db.commit()
        await self.db.refresh(transaction)
        logger.info(f"Added transaction: {transaction.id} for portfolio {portfolio_id}")
        return transaction

    async def get_portfolio_transactions(
        self,
        portfolio_id: int,
        stock_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Transaction]:
        """
        获取交易记录

        Args:
            portfolio_id: 组合ID
            stock_code: 股票代码过滤
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易记录列表
        """
        stmt = select(Transaction).where(Transaction.portfolio_id == portfolio_id)

        if stock_code:
            stmt = stmt.where(Transaction.stock_code == stock_code)
        if start_date:
            stmt = stmt.where(Transaction.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(Transaction.trade_date <= end_date)

        stmt = stmt.order_by(Transaction.trade_date.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ============================================
    # 收益计算
    # ============================================

    async def calculate_returns(self, portfolio_id: int) -> Dict[str, Any]:
        """
        计算投资组合收益

        Args:
            portfolio_id: 组合ID

        Returns:
            收益信息
        """
        portfolio = await self.get_portfolio(portfolio_id, 0)
        if not portfolio:
            return {}

        # 获取所有持仓
        positions = await self.get_portfolio_positions(portfolio_id)

        # 计算总市值和总成本
        total_market_value = 0.0
        total_cost = 0.0

        for position in positions:
            if position.market_value:
                total_market_value += position.market_value
            total_cost += position.total_cost

        # 当前价值 = 现金余额 + 持仓市值
        current_value = portfolio.current_value - total_cost + total_market_value

        # 计算收益
        profit_loss = current_value - portfolio.initial_capital
        profit_loss_pct = (profit_loss / portfolio.initial_capital * 100) if portfolio.initial_capital > 0 else 0

        return {
            "initial_capital": portfolio.initial_capital,
            "current_value": current_value,
            "cash_balance": portfolio.current_value - total_cost,
            "position_value": total_market_value,
            "total_cost": total_cost,
            "profit_loss": profit_loss,
            "profit_loss_pct": profit_loss_pct,
        }

    async def update_portfolio_value(self, portfolio_id: int) -> Portfolio:
        """
        更新投资组合价值

        Args:
            portfolio_id: 组合ID

        Returns:
            更新后的投资组合
        """
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            return None

        positions = await self.get_portfolio_positions(portfolio_id)

        total_market_value = 0.0
        for position in positions:
            if position.current_price and position.quantity > 0:
                position.market_value = position.current_price * position.quantity
                position.profit_loss = position.market_value - position.total_cost
                position.profit_loss_pct = (position.profit_loss / position.total_cost * 100) if position.total_cost > 0 else 0
                total_market_value += position.market_value

        # 假设现金余额 = 当前价值 - 持仓成本
        cash_balance = portfolio.current_value - sum(p.total_cost for p in positions)
        portfolio.current_value = cash_balance + total_market_value

        await self.db.commit()
        await self.db.refresh(portfolio)
        return portfolio

    # ============================================
    # 历史记录
    # ============================================

    async def add_history(
        self,
        portfolio_id: int,
        total_value: float,
        cash_balance: float,
        position_value: float,
        total_cost: float,
        profit_loss: float,
        profit_loss_pct: float,
        record_date: Optional[str] = None,
    ) -> PortfolioHistory:
        """
        添加历史记录

        Args:
            portfolio_id: 组合ID
            total_value: 总资产
            cash_balance: 现金余额
            position_value: 持仓市值
            total_cost: 总成本
            profit_loss: 总盈亏
            profit_loss_pct: 盈亏比例
            record_date: 记录日期

        Returns:
            历史记录
        """
        if record_date is None:
            record_date = date.today().strftime("%Y-%m-%d")

        history = PortfolioHistory(
            portfolio_id=portfolio_id,
            total_value=total_value,
            cash_balance=cash_balance,
            position_value=position_value,
            total_cost=total_cost,
            profit_loss=profit_loss,
            profit_loss_pct=profit_loss_pct,
            record_date=record_date,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def get_portfolio_history(
        self,
        portfolio_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[PortfolioHistory]:
        """
        获取历史记录

        Args:
            portfolio_id: 组合ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            历史记录列表
        """
        stmt = select(PortfolioHistory).where(PortfolioHistory.portfolio_id == portfolio_id)

        if start_date:
            stmt = stmt.where(PortfolioHistory.record_date >= start_date)
        if end_date:
            stmt = stmt.where(PortfolioHistory.record_date <= end_date)

        stmt = stmt.order_by(PortfolioHistory.record_date.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ============================================
    # 组合分析报告
    # ============================================

    async def generate_portfolio_report(self, portfolio_id: int) -> Dict[str, Any]:
        """
        生成投资组合分析报告

        Args:
            portfolio_id: 组合ID

        Returns:
            分析报告
        """
        portfolio = await self.get_portfolio(portfolio_id, 0)
        if not portfolio:
            return {}

        positions = await self.get_portfolio_positions(portfolio_id)
        returns = await self.calculate_returns(portfolio_id)
        history = await self.get_portfolio_history(portfolio_id)

        # 计算持仓分布
        position_distribution = []
        total_market_value = returns.get("position_value", 0)

        for position in positions:
            if position.market_value:
                weight = (position.market_value / total_market_value * 100) if total_market_value > 0 else 0
                position_distribution.append({
                    "stock_code": position.stock_code,
                    "stock_name": position.stock_name,
                    "quantity": position.quantity,
                    "current_price": position.current_price,
                    "market_value": position.market_value,
                    "cost": position.total_cost,
                    "profit_loss": position.profit_loss,
                    "profit_loss_pct": position.profit_loss_pct,
                    "weight": weight,
                })

        # 按市值排序
        position_distribution.sort(key=lambda x: x["market_value"], reverse=True)

        return {
            "portfolio": {
                "id": portfolio.id,
                "name": portfolio.name,
                "description": portfolio.description,
                "initial_capital": portfolio.initial_capital,
                "status": portfolio.status,
                "created_at": portfolio.created_at.isoformat(),
            },
            "returns": returns,
            "positions": position_distribution,
            "total_positions": len(positions),
            "history_count": len(history),
        }


# 获取服务实例的依赖函数
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service(db: AsyncSession) -> PortfolioService:
    """
    获取投资组合服务实例

    Args:
        db: 数据库会话

    Returns:
        投资组合服务实例
    """
    return PortfolioService(db)
