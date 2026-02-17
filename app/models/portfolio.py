"""
投资组合模型

定义投资组合、持仓、交易记录等数据库模型。
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.stock import Base


class PortfolioStatus(str, Enum):
    """投资组合状态枚举"""

    ACTIVE = "active"  # 活跃
    CLOSED = "closed"  # 已关闭
    ARCHIVED = "archived"  # 已归档


class PositionType(str, Enum):
    """持仓类型枚举"""

    LONG = "long"  # 多头
    SHORT = "short"  # 空头


class TransactionType(str, Enum):
    """交易类型枚举"""

    BUY = "buy"  # 买入
    SELL = "sell"  # 卖出
    DIVIDEND = "dividend"  # 股息
    SPLIT = "split"  # 拆股
    MERGE = "merge"  # 合股


class Portfolio(Base):
    """
    投资组合模型

    存储投资组合的基本信息。
    """

    __tablename__ = "portfolios"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 用户ID
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 组合名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 组合描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 初始资金
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)

    # 当前总资产
    current_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 状态
    status: Mapped[str] = mapped_column(
        SQLEnum(PortfolioStatus),
        nullable=False,
        default=PortfolioStatus.ACTIVE.value
    )

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 关联关系
    positions: Mapped[list["Position"]] = relationship(
        "Position", back_populates="portfolio", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="portfolio", cascade="all, delete-orphan"
    )
    history: Mapped[list["PortfolioHistory"]] = relationship(
        "PortfolioHistory", back_populates="portfolio", cascade="all, delete-orphan"
    )

    # 复合索引
    __table_args__ = (
        Index("ix_portfolio_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name={self.name}, user_id={self.user_id})>"


class Position(Base):
    """
    持仓模型

    存储投资组合中的持仓信息。
    """

    __tablename__ = "positions"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 投资组合ID
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 股票代码
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # 股票名称
    stock_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 持仓类型
    position_type: Mapped[str] = mapped_column(
        SQLEnum(PositionType), nullable=False, default=PositionType.LONG.value
    )

    # 持仓数量
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    # 成本价
    cost_price: Mapped[float] = mapped_column(Float, nullable=False)

    # 当前价格
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 持仓成本
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # 当前市值
    market_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 持仓盈亏
    profit_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 盈亏比例
    profit_loss_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 关联关系
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")

    # 复合索引
    __table_args__ = (
        Index("ix_position_portfolio_stock", "portfolio_id", "stock_code", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Position(id={self.id}, stock_code={self.stock_code}, quantity={self.quantity})>"


class Transaction(Base):
    """
    交易记录模型

    存储投资组合的所有交易记录。
    """

    __tablename__ = "transactions"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 投资组合ID
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 股票代码
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # 股票名称
    stock_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 交易类型
    transaction_type: Mapped[str] = mapped_column(
        SQLEnum(TransactionType), nullable=False
    )

    # 交易数量
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    # 交易价格
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # 交易金额
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    # 手续费
    commission: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 交易日期
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 关联关系
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="transactions")

    # 复合索引
    __table_args__ = (
        Index("ix_transaction_portfolio_date", "portfolio_id", "trade_date"),
        Index("ix_transaction_stock_date", "stock_code", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, stock_code={self.stock_code}, type={self.transaction_type})>"


class PortfolioHistory(Base):
    """
    投资组合历史记录模型

    存储投资组合的历史快照，用于追踪组合价值变化。
    """

    __tablename__ = "portfolio_history"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 投资组合ID
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 总资产
    total_value: Mapped[float] = mapped_column(Float, nullable=False)

    # 现金余额
    cash_balance: Mapped[float] = mapped_column(Float, nullable=False)

    # 持仓市值
    position_value: Mapped[float] = mapped_column(Float, nullable=False)

    # 总成本
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # 总盈亏
    profit_loss: Mapped[float] = mapped_column(Float, nullable=False)

    # 盈亏比例
    profit_loss_pct: Mapped[float] = mapped_column(Float, nullable=False)

    # 记录日期
    record_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 关联关系
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="history")

    # 复合索引
    __table_args__ = (
        Index("ix_portfolio_history_portfolio_date", "portfolio_id", "record_date", unique=True),
    )

    def __repr__(self) -> str:
        return f"<PortfolioHistory(id={self.id}, portfolio_id={self.portfolio_id}, date={self.record_date})>"


# 模型列表，用于创建表
PORTFOLIO_MODELS = [Portfolio, Position, Transaction, PortfolioHistory]
