"""
预警数据模型

定义预警规则、预警记录等数据库模型。
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List

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


class AlertType(str, Enum):
    """预警类型枚举"""
    PRICE_ABOVE = "price_above"      # 价格高于
    PRICE_BELOW = "price_below"      # 价格低于
    CHANGE_UP = "change_up"          # 涨幅高于
    CHANGE_DOWN = "change_down"      # 跌幅高于
    VOLUME_SPIKE = "volume_spike"    # 成交量异动
    TURNOVER_SPIKE = "turnover_spike"  # 换手率异动


class AlertStatus(str, Enum):
    """预警状态枚举"""
    ACTIVE = "active"        # 生效中
    TRIGGERED = "triggered"  # 已触发
    PAUSED = "paused"        # 已暂停
    EXPIRED = "expired"      # 已过期


class AlertRule(Base):
    """
    预警规则模型

    存储用户配置的预警规则。
    """

    __tablename__ = "alert_rules"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 预警名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 股票代码
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # 预警类型
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # 阈值 (JSON格式存储不同类型的阈值)
    # price_above/below: {"price": 100.0}
    # change_up/down: {"change_percent": 5.0}
    # volume_spike: {"volume_ratio": 2.0, "days": 5}
    # turnover_spike: {"turnover_ratio": 1.5, "days": 5}
    threshold: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 用户ID (可选，用于多用户场景)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # 预警状态
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AlertStatus.ACTIVE.value)

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
    alerts: Mapped[List["AlertRecord"]] = relationship(
        "AlertRecord", back_populates="rule", cascade="all, delete-orphan"
    )

    # 复合索引
    __table_args__ = (
        Index("ix_alert_rule_stock_status", "stock_code", "status"),
    )

    def __repr__(self) -> str:
        return f"<AlertRule(id={self.id}, name={self.name}, stock_code={self.stock_code}, type={self.alert_type})>"


class AlertRecord(Base):
    """
    预警记录模型

    存储预警触发记录。
    """

    __tablename__ = "alert_records"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联预警规则
    rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 触发时的股票价格
    trigger_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 触发时的涨跌幅
    trigger_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 触发时的成交量
    trigger_volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 触发时的换手率
    trigger_turnover_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 预警消息
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # 是否已读
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 是否已处理
    is_handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 触发时间
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 处理时间
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联关系
    rule: Mapped["AlertRule"] = relationship("AlertRule", back_populates="alerts")

    # 复合索引
    __table_args__ = (
        Index("ix_alert_record_rule_triggered", "rule_id", "triggered_at"),
    )

    def __repr__(self) -> str:
        return f"<AlertRecord(id={self.id}, rule_id={self.rule_id}, triggered_at={self.triggered_at})>"


# 模型列表，用于创建表
MODELS = [AlertRule, AlertRecord]
