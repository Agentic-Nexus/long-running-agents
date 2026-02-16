"""
股票数据模型

定义股票、行情和K线数据的数据库模型。
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """数据库模型基类"""

    pass


class MarketType(str, Enum):
    """市场类型枚举"""

    SH = "SH"  # 上海
    SZ = "SZ"  # 深圳
    BJ = "BJ"  # 北京
    HK = "HK"  # 港股
    US = "US"  # 美股


class Stock(Base):
    """
    股票基本信息模型

    存储股票的基本信息，包括代码、名称、市场等。
    """

    __tablename__ = "stocks"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 股票代码 (如: 000001, 600000)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # 股票名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 市场类型
    market: Mapped[str] = mapped_column(String(10), nullable=False, default=MarketType.SZ.value)

    # 交易所代码
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)

    # 股票类型 (A股、港股、美股等)
    stock_type: Mapped[str] = mapped_column(String(20), nullable=False, default="A股")

    # 是否上市
    is_listed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 上市日期
    list_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # 退市日期 (如果已退市)
    delist_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # 行业
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 所属板块
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 元数据 (JSON格式，存储其他信息)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 关联关系
    quotes: Mapped[list["StockQuote"]] = relationship(
        "StockQuote", back_populates="stock", cascade="all, delete-orphan"
    )
    klines: Mapped[list["KLineData"]] = relationship(
        "KLineData", back_populates="stock", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Stock(code={self.code}, name={self.name}, market={self.market})>"


class StockQuote(Base):
    """
    股票行情快照模型

    存储股票的实时或历史行情数据。
    """

    __tablename__ = "stock_quotes"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联股票
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 交易日期
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # 开盘价
    open: Mapped[float] = mapped_column(Float, nullable=False)

    # 最高价
    high: Mapped[float] = mapped_column(Float, nullable=False)

    # 最低价
    low: Mapped[float] = mapped_column(Float, nullable=False)

    # 收盘价
    close: Mapped[float] = mapped_column(Float, nullable=False)

    # 成交量
    volume: Mapped[float] = mapped_column(Float, nullable=False)

    # 成交额
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 涨跌幅
    change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 涨跌额
    change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 换手率
    turnover_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 市盈率 (TTM)
    pe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 市净率
    pb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 总市值
    total_market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 流通市值
    float_market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 关联关系
    stock: Mapped["Stock"] = relationship("Stock", back_populates="quotes")

    # 复合索引
    __table_args__ = (
        Index("ix_stock_quote_stock_date", "stock_id", "trade_date", unique=True),
    )

    def __repr__(self) -> str:
        return f"<StockQuote(stock_id={self.stock_id}, date={self.trade_date}, close={self.close})>"


class KLineData(Base):
    """
    K线数据模型

    存储股票的K线数据（支持日线、周线、月线等）。
    """

    __tablename__ = "kline_data"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联股票
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # K线周期 (1d, 1w, 1m, 5m, 15m, 30m, 60m等)
    period: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")

    # 交易日期
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # 开盘价
    open: Mapped[float] = mapped_column(Float, nullable=False)

    # 最高价
    high: Mapped[float] = mapped_column(Float, nullable=False)

    # 最低价
    low: Mapped[float] = mapped_column(Float, nullable=False)

    # 收盘价
    close: Mapped[float] = mapped_column(Float, nullable=False)

    # 成交量
    volume: Mapped[float] = mapped_column(Float, nullable=False)

    # 成交额
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 涨跌幅
    change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 涨跌额
    change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 换手率
    turnover_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 振幅
    amplitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 前收 (前一交易日收盘价)
    pre_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 关联关系
    stock: Mapped["Stock"] = relationship("Stock", back_populates="klines")

    # 复合索引
    __table_args__ = (
        Index("ix_kline_stock_period_date", "stock_id", "period", "trade_date", unique=True),
        Index("ix_kline_period_date", "period", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<KLineData(stock_id={self.stock_id}, period={self.period}, date={self.trade_date})>"


class StockAnalysis(Base):
    """
    股票分析结果模型

    存储基于LLM的股票分析结果。
    """

    __tablename__ = "stock_analysis"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联股票
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 分析类型 (daily, weekly, monthly, custom)
    analysis_type: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")

    # 分析日期
    analysis_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # 分析内容 (JSON格式)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 分析摘要
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 置信度 (0-1)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 标签 (如: 看好, 看空, 观望)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 更新间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 复合索引
    __table_args__ = (
        Index("ix_stock_analysis_stock_type_date", "stock_id", "analysis_type", "analysis_date", unique=True),
    )

    def __repr__(self) -> str:
        return f"<StockAnalysis(stock_id={self.stock_id}, type={self.analysis_type}, date={self.analysis_date})>"


# 模型列表，用于创建表
MODELS = [Stock, StockQuote, KLineData, StockAnalysis]
