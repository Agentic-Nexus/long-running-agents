"""
数据库连接配置模块

提供 PostgreSQL 和 Redis 连接管理，支持异步操作。
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import redis.asyncio as redis

from app.config import get_config


# 全局引擎和连接池
_engine: Optional[AsyncEngine] = None
_redis_client: Optional[redis.Redis] = None


def get_database_url() -> str:
    """
    获取数据库连接 URL

    Returns:
        数据库连接 URL
    """
    config = get_config()
    return config.database_url


def get_redis_url() -> str:
    """
    获取 Redis 连接 URL

    Returns:
        Redis 连接 URL
    """
    config = get_config()
    return config.redis_url


def create_engine(
    database_url: Optional[str] = None,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> AsyncEngine:
    """
    创建数据库引擎

    Args:
        database_url: 数据库连接 URL，默认从配置获取
        echo: 是否打印 SQL 语句
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数

    Returns:
        SQLAlchemy 异步引擎
    """
    global _engine
    if _engine is not None:
        return _engine

    url = database_url or get_database_url()

    # 使用 NullPool 以便更好地控制连接生命周期
    # 对于异步应用，使用 NullPool 并手动管理连接
    _engine = create_async_engine(
        url,
        echo=echo,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={
            "server_settings": {"application_name": "stock_analyzer"},
            "timeout": 30,
        },
    )

    return _engine


def get_engine() -> AsyncEngine:
    """
    获取数据库引擎（单例）

    Returns:
        SQLAlchemy 异步引擎
    """
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


async def create_redis_client(
    redis_url: Optional[str] = None,
    decode_responses: bool = True,
) -> redis.Redis:
    """
    创建 Redis 客户端

    Args:
        redis_url: Redis 连接 URL，默认从配置获取
        decode_responses: 是否自动解码响应

    Returns:
        Redis 异步客户端
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    url = redis_url or get_redis_url()

    _redis_client = redis.from_url(
        url,
        decode_responses=decode_responses,
        encoding="utf-8",
        encoding_errors="ignore",
    )

    return _redis_client


def get_redis() -> redis.Redis:
    """
    获取 Redis 客户端（单例）

    Returns:
        Redis 异步客户端
    """
    global _redis_client
    if _redis_client is None:
        # 注意：这是一个同步调用，返回的是协程
        # 实际使用时需要在 async 上下文中
        raise RuntimeError(
            "Redis client not initialized. Use create_redis_client() or get_redis_async()"
        )


async def get_redis_async() -> redis.Redis:
    """
    获取 Redis 客户端（异步初始化）

    Returns:
        Redis 异步客户端
    """
    global _redis_client
    if _redis_client is None:
        await create_redis_client()
    return _redis_client


# 异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=get_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的异步生成器

    Yields:
        异步数据库会话

    Example:
        async with get_session() as session:
            result = await session.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的上下文管理器

    Yields:
        异步数据库会话

    Example:
        async with session_scope() as session:
            result = await session.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def test_database_connection() -> bool:
    """
    测试数据库连接

    Returns:
        连接是否成功
    """
    try:
        async with get_engine().connect() as conn:
            await conn.execute(
                "SELECT 1" if "sqlite" in get_database_url() else "SELECT 1"
            )
        return True
    except Exception:
        return False


async def test_redis_connection() -> bool:
    """
    测试 Redis 连接

    Returns:
        连接是否成功
    """
    try:
        client = await get_redis_async()
        await client.ping()
        return True
    except Exception:
        return False


async def close_connections() -> None:
    """
    关闭所有数据库连接
    """
    global _engine, _redis_client

    if _engine is not None:
        await _engine.dispose()
        _engine = None

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


async def init_connections(
    database_url: Optional[str] = None,
    redis_url: Optional[str] = None,
) -> None:
    """
    初始化所有连接

    Args:
        database_url: 数据库连接 URL
        redis_url: Redis 连接 URL
    """
    create_engine(database_url)
    await create_redis_client(redis_url)


class DatabaseManager:
    """
    数据库连接管理器

    提供连接的生命周期管理功能。
    """

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.redis: Optional[redis.Redis] = None

    async def initialize(
        self,
        database_url: Optional[str] = None,
        redis_url: Optional[str] = None,
    ) -> None:
        """
        初始化连接

        Args:
            database_url: 数据库连接 URL
            redis_url: Redis 连接 URL
        """
        self.engine = create_engine(database_url)
        self.redis = await create_redis_client(redis_url)

    async def close(self) -> None:
        """关闭所有连接"""
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None

        if self.redis is not None:
            await self.redis.close()
            self.redis = None

    async def test_connections(self) -> dict:
        """
        测试所有连接

        Returns:
            测试结果字典
        """
        results = {
            "database": False,
            "redis": False,
        }

        if self.engine is not None:
            try:
                async with self.engine.connect() as conn:
                    await conn.execute("SELECT 1")
                results["database"] = True
            except Exception:
                pass

        if self.redis is not None:
            try:
                await self.redis.ping()
                results["redis"] = True
            except Exception:
                pass

        return results


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器实例

    Returns:
        数据库管理器
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
