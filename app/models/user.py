"""
用户认证模型

定义用户、角色和 API 密钥的数据库模型。
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.stock import Base


class UserRole(str, Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    PREMIUM = "premium"
    BASIC = "basic"
    GUEST = "guest"


class User(Base):
    """
    用户账户模型

    存储用户的基本信息和认证凭证。
    """

    __tablename__ = "users"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 用户名 (唯一)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # 邮箱 (唯一)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # 密码哈希
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # 显示名称
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 用户角色
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.BASIC.value)

    # 是否激活
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 是否验证邮箱
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 头像 URL
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # API 调用配额 (每月)
    api_quota: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)

    # 已使用配额
    api_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 最后登录时间
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

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
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )

    # 复合索引
    __table_args__ = (
        Index("ix_user_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class APIKey(Base):
    """
    API 密钥模型

    存储用户的 API 密钥。
    """

    __tablename__ = "api_keys"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联用户
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 密钥名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # API 密钥 (哈希存储)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # 密钥前缀 (用于显示)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)

    # 是否启用
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 最后使用时间
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 过期时间
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, user_id={self.user_id})>"


class UserSession(Base):
    """
    用户会话模型

    存储用户的登录会话信息。
    """

    __tablename__ = "user_sessions"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联用户
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 会话令牌 (JWT ID)
    jti: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # 设备信息
    device_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # IP 地址
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # 是否有效
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, jti={self.jti})>"


# 模型列表，用于创建表
USER_MODELS = [User, APIKey, UserSession]
