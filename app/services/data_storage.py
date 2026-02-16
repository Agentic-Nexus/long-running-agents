"""
数据存储服务模块

提供股票数据的持久化存储功能：
- 股票基本信息存储
- 行情数据存储
- K线数据存储
- 增量更新逻辑
- 数据完整性验证
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.database import get_engine, session_scope
from app.models.stock import Stock, StockQuote, KLineData, StockAnalysis, Base, MarketType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataStorageService:
    """数据存储服务类"""

    def __init__(self):
        """初始化数据存储服务"""
        self.engine = get_engine()

    async def init_tables(self) -> None:
        """
        初始化数据库表

        创建所有股票相关的数据库表。
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")

    async def drop_tables(self) -> None:
        """
        删除所有数据库表

        注意：此操作会删除所有数据，请谨慎使用。
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("Database tables dropped")

    # ==================== 股票基本信息操作 ====================

    async def insert_stock(
        self,
        session: AsyncSession,
        code: str,
        name: str,
        market: str = MarketType.SZ.value,
        exchange: str = "SZSE",
        stock_type: str = "A股",
        is_listed: bool = True,
        list_date: Optional[str] = None,
        industry: Optional[str] = None,
        sector: Optional[str] = None,
        extra_data: Optional[Dict] = None,
    ) -> Stock:
        """
        插入股票基本信息

        Args:
            session: 数据库会话
            code: 股票代码
            name: 股票名称
            market: 市场类型
            exchange: 交易所代码
            stock_type: 股票类型
            is_listed: 是否上市
            list_date: 上市日期
            industry: 行业
            sector: 板块
            extra_data: 额外数据

        Returns:
            Stock 对象
        """
        # 使用 upsert 逻辑：存在则更新，不存在则插入
        stmt = pg_insert(Stock).values(
            code=code,
            name=name,
            market=market,
            exchange=exchange,
            stock_type=stock_type,
            is_listed=is_listed,
            list_date=list_date,
            industry=industry,
            sector=sector,
            extra_data=extra_data,
            updated_at=datetime.utcnow(),
        ).on_conflict_do_update(
            index_elements=["code"],
            set_={
                "name": name,
                "market": market,
                "exchange": exchange,
                "stock_type": stock_type,
                "is_listed": is_listed,
                "list_date": list_date,
                "industry": industry,
                "sector": sector,
                "extra_data": extra_data,
                "updated_at": datetime.utcnow(),
            },
        ).returning(Stock)

        result = await session.execute(stmt)
        await session.commit()
        stock = result.scalar_one()
        logger.debug(f"Stock upserted: {stock.code} - {stock.name}")
        return stock

    async def insert_stocks_bulk(
        self,
        session: AsyncSession,
        stocks_data: List[Dict[str, Any]],
    ) -> int:
        """
        批量插入股票信息

        Args:
            session: 数据库会话
            stocks_data: 股票数据列表

        Returns:
            插入/更新的股票数量
        """
        if not stocks_data:
            return 0

        # 准备批量数据
        now = datetime.utcnow()
        values = []
        for data in stocks_data:
            values.append({
                "code": data.get("code"),
                "name": data.get("name"),
                "market": data.get("market", MarketType.SZ.value),
                "exchange": data.get("exchange", "SZSE"),
                "stock_type": data.get("stock_type", "A股"),
                "is_listed": data.get("is_listed", True),
                "list_date": data.get("list_date"),
                "industry": data.get("industry"),
                "sector": data.get("sector"),
                "extra_data": data.get("extra_data"),
                "updated_at": now,
            })

        # 使用 PostgreSQL upsert
        insert_stmt = pg_insert(Stock).values(values)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={
                "name": insert_stmt.excluded.name,
                "market": insert_stmt.excluded.market,
                "exchange": insert_stmt.excluded.exchange,
                "stock_type": insert_stmt.excluded.stock_type,
                "is_listed": insert_stmt.excluded.is_listed,
                "list_date": insert_stmt.excluded.list_date,
                "industry": insert_stmt.excluded.industry,
                "sector": insert_stmt.excluded.sector,
                "extra_data": insert_stmt.excluded.extra_data,
                "updated_at": insert_stmt.excluded.updated_at,
            },
        )

        await session.execute(stmt)
        await session.commit()
        logger.info(f"Bulk upserted {len(stocks_data)} stocks")
        return len(stocks_data)

    async def get_stock_by_code(
        self,
        session: AsyncSession,
        code: str,
    ) -> Optional[Stock]:
        """
        根据股票代码获取股票信息

        Args:
            session: 数据库会话
            code: 股票代码

        Returns:
            Stock 对象或 None
        """
        stmt = select(Stock).where(Stock.code == code)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_stocks(
        self,
        session: AsyncSession,
        market: Optional[str] = None,
        is_listed: Optional[bool] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Stock]:
        """
        获取股票列表

        Args:
            session: 数据库会话
            market: 市场类型过滤
            is_listed: 上市状态过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            Stock 对象列表
        """
        stmt = select(Stock)

        conditions = []
        if market is not None:
            conditions.append(Stock.market == market)
        if is_listed is not None:
            conditions.append(Stock.is_listed == is_listed)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.limit(limit).offset(offset).order_by(Stock.code)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 行情数据操作 ====================

    async def insert_quote(
        self,
        session: AsyncSession,
        stock_id: int,
        trade_date: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        amount: Optional[float] = None,
        change_pct: Optional[float] = None,
        change: Optional[float] = None,
        turnover_rate: Optional[float] = None,
        pe: Optional[float] = None,
        pb: Optional[float] = None,
        total_market_cap: Optional[float] = None,
        float_market_cap: Optional[float] = None,
    ) -> StockQuote:
        """
        插入股票行情数据

        Args:
            session: 数据库会话
            stock_id: 股票 ID
            trade_date: 交易日期
            open: 开盘价
            high: 最高价
            low: 最低价
            close: 收盘价
            volume: 成交量
            amount: 成交额
            change_pct: 涨跌幅
            change: 涨跌额
            turnover_rate: 换手率
            pe: 市盈率
            pb: 市净率
            total_market_cap: 总市值
            float_market_cap: 流通市值

        Returns:
            StockQuote 对象
        """
        stmt = pg_insert(StockQuote).values(
            stock_id=stock_id,
            trade_date=trade_date,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
            change=change,
            turnover_rate=turnover_rate,
            pe=pe,
            pb=pb,
            total_market_cap=total_market_cap,
            float_market_cap=float_market_cap,
        ).on_conflict_do_update(
            index_elements=["stock_id", "trade_date"],
            set_={
                "open": open,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "amount": amount,
                "change_pct": change_pct,
                "change": change,
                "turnover_rate": turnover_rate,
                "pe": pe,
                "pb": pb,
                "total_market_cap": total_market_cap,
                "float_market_cap": float_market_cap,
            },
        ).returning(StockQuote)

        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()

    async def insert_quotes_bulk(
        self,
        session: AsyncSession,
        quotes_data: List[Dict[str, Any]],
    ) -> int:
        """
        批量插入行情数据

        Args:
            session: 数据库会话
            quotes_data: 行情数据列表

        Returns:
            插入/更新的行情数量
        """
        if not quotes_data:
            return 0

        values = []
        for data in quotes_data:
            values.append({
                "stock_id": data.get("stock_id"),
                "trade_date": data.get("trade_date"),
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "close": data.get("close"),
                "volume": data.get("volume"),
                "amount": data.get("amount"),
                "change_pct": data.get("change_pct"),
                "change": data.get("change"),
                "turnover_rate": data.get("turnover_rate"),
                "pe": data.get("pe"),
                "pb": data.get("pb"),
                "total_market_cap": data.get("total_market_cap"),
                "float_market_cap": data.get("float_market_cap"),
            })

        insert_stmt = pg_insert(StockQuote).values(values)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["stock_id", "trade_date"],
            set_={
                "open": insert_stmt.excluded.open,
                "high": insert_stmt.excluded.high,
                "low": insert_stmt.excluded.low,
                "close": insert_stmt.excluded.close,
                "volume": insert_stmt.excluded.volume,
                "amount": insert_stmt.excluded.amount,
                "change_pct": insert_stmt.excluded.change_pct,
                "change": insert_stmt.excluded.change,
                "turnover_rate": insert_stmt.excluded.turnover_rate,
                "pe": insert_stmt.excluded.pe,
                "pb": insert_stmt.excluded.pb,
                "total_market_cap": insert_stmt.excluded.total_market_cap,
                "float_market_cap": insert_stmt.excluded.float_market_cap,
            },
        )

        await session.execute(stmt)
        await session.commit()
        logger.info(f"Bulk upserted {len(quotes_data)} quotes")
        return len(quotes_data)

    async def get_quotes_by_stock(
        self,
        session: AsyncSession,
        stock_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000,
    ) -> List[StockQuote]:
        """
        获取指定股票的行情数据

        Args:
            session: 数据库会话
            stock_id: 股票 ID
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制

        Returns:
            StockQuote 列表
        """
        stmt = select(StockQuote).where(StockQuote.stock_id == stock_id)

        if start_date:
            stmt = stmt.where(StockQuote.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(StockQuote.trade_date <= end_date)

        stmt = stmt.order_by(StockQuote.trade_date.desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ==================== K线数据操作 ====================

    async def insert_kline(
        self,
        session: AsyncSession,
        stock_id: int,
        period: str,
        trade_date: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        amount: Optional[float] = None,
        change_pct: Optional[float] = None,
        change: Optional[float] = None,
        turnover_rate: Optional[float] = None,
        amplitude: Optional[float] = None,
        pre_close: Optional[float] = None,
    ) -> KLineData:
        """
        插入K线数据

        Args:
            session: 数据库会话
            stock_id: 股票 ID
            period: K线周期
            trade_date: 交易日期
            open: 开盘价
            high: 最高价
            low: 最低价
            close: 收盘价
            volume: 成交量
            amount: 成交额
            change_pct: 涨跌幅
            change: 涨跌额
            turnover_rate: 换手率
            amplitude: 振幅
            pre_close: 前收

        Returns:
            KLineData 对象
        """
        stmt = pg_insert(KLineData).values(
            stock_id=stock_id,
            period=period,
            trade_date=trade_date,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
            change=change,
            turnover_rate=turnover_rate,
            amplitude=amplitude,
            pre_close=pre_close,
        ).on_conflict_do_update(
            index_elements=["stock_id", "period", "trade_date"],
            set_={
                "open": open,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "amount": amount,
                "change_pct": change_pct,
                "change": change,
                "turnover_rate": turnover_rate,
                "amplitude": amplitude,
                "pre_close": pre_close,
            },
        ).returning(KLineData)

        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()

    async def insert_klines_bulk(
        self,
        session: AsyncSession,
        klines_data: List[Dict[str, Any]],
    ) -> int:
        """
        批量插入K线数据

        Args:
            session: 数据库会话
            klines_data: K线数据列表

        Returns:
            插入/更新的K线数量
        """
        if not klines_data:
            return 0

        values = []
        for data in klines_data:
            values.append({
                "stock_id": data.get("stock_id"),
                "period": data.get("period", "1d"),
                "trade_date": data.get("trade_date"),
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "close": data.get("close"),
                "volume": data.get("volume"),
                "amount": data.get("amount"),
                "change_pct": data.get("change_pct"),
                "change": data.get("change"),
                "turnover_rate": data.get("turnover_rate"),
                "amplitude": data.get("amplitude"),
                "pre_close": data.get("pre_close"),
            })

        insert_stmt = pg_insert(KLineData).values(values)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["stock_id", "period", "trade_date"],
            set_={
                "open": insert_stmt.excluded.open,
                "high": insert_stmt.excluded.high,
                "low": insert_stmt.excluded.low,
                "close": insert_stmt.excluded.close,
                "volume": insert_stmt.excluded.volume,
                "amount": insert_stmt.excluded.amount,
                "change_pct": insert_stmt.excluded.change_pct,
                "change": insert_stmt.excluded.change,
                "turnover_rate": insert_stmt.excluded.turnover_rate,
                "amplitude": insert_stmt.excluded.amplitude,
                "pre_close": insert_stmt.excluded.pre_close,
            },
        )

        await session.execute(stmt)
        await session.commit()
        logger.info(f"Bulk upserted {len(klines_data)} klines")
        return len(klines_data)

    async def get_klines_by_stock(
        self,
        session: AsyncSession,
        stock_id: int,
        period: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000,
    ) -> List[KLineData]:
        """
        获取指定股票的K线数据

        Args:
            session: 数据库会话
            stock_id: 股票 ID
            period: K线周期
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制

        Returns:
            KLineData 列表
        """
        stmt = select(KLineData).where(
            and_(
                KLineData.stock_id == stock_id,
                KLineData.period == period,
            )
        )

        if start_date:
            stmt = stmt.where(KLineData.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(KLineData.trade_date <= end_date)

        stmt = stmt.order_by(KLineData.trade_date.desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 增量更新逻辑 ====================

    async def get_latest_quote_date(
        self,
        session: AsyncSession,
        stock_id: int,
    ) -> Optional[str]:
        """
        获取指定股票的最新行情日期

        Args:
            session: 数据库会话
            stock_id: 股票 ID

        Returns:
            最新交易日期或 None
        """
        stmt = (
            select(StockQuote.trade_date)
            .where(StockQuote.stock_id == stock_id)
            .order_by(StockQuote.trade_date.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_kline_date(
        self,
        session: AsyncSession,
        stock_id: int,
        period: str = "1d",
    ) -> Optional[str]:
        """
        获取指定股票的最新K线日期

        Args:
            session: 数据库会话
            stock_id: 股票 ID
            period: K线周期

        Returns:
            最新交易日期或 None
        """
        stmt = (
            select(KLineData.trade_date)
            .where(
                and_(
                    KLineData.stock_id == stock_id,
                    KLineData.period == period,
                )
            )
            .order_by(KLineData.trade_date.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== 数据完整性验证 ====================

    async def verify_data_integrity(
        self,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        验证数据完整性

        检查：
        - 股票数据完整性
        - 行情数据关联性
        - K线数据关联性

        Args:
            session: 数据库会话

        Returns:
            验证结果字典
        """
        results = {
            "stocks_count": 0,
            "quotes_count": 0,
            "klines_count": 0,
            "orphan_quotes": 0,
            "orphan_klines": 0,
            "is_valid": True,
            "errors": [],
        }

        # 统计股票数量
        stmt = select(func.count(Stock.id))
        result = await session.execute(stmt)
        results["stocks_count"] = result.scalar()

        # 统计行情数量
        stmt = select(func.count(StockQuote.id))
        result = await session.execute(stmt)
        results["quotes_count"] = result.scalar()

        # 统计K线数量
        stmt = select(func.count(KLineData.id))
        result = await session.execute(stmt)
        results["klines_count"] = result.scalar()

        # 检查孤儿行情数据（stock_id 不存在）
        stmt = text("""
            SELECT COUNT(*)
            FROM stock_quotes sq
            LEFT JOIN stocks s ON sq.stock_id = s.id
            WHERE s.id IS NULL
        """)
        result = await session.execute(stmt)
        results["orphan_quotes"] = result.scalar()

        # 检查孤儿K线数据
        stmt = text("""
            SELECT COUNT(*)
            FROM kline_data kd
            LEFT JOIN stocks s ON kd.stock_id = s.id
            WHERE s.id IS NULL
        """)
        result = await session.execute(stmt)
        results["orphan_klines"] = result.scalar()

        # 判断数据是否有效
        if results["orphan_quotes"] > 0:
            results["is_valid"] = False
            results["errors"].append(f"Found {results['orphan_quotes']} orphan quotes")

        if results["orphan_klines"] > 0:
            results["is_valid"] = False
            results["errors"].append(f"Found {results['orphan_klines']} orphan klines")

        logger.info(f"Data integrity check: {results}")
        return results

    async def get_data_statistics(
        self,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        获取数据统计信息

        Args:
            session: 数据库会话

        Returns:
            统计数据字典
        """
        stats = {}

        # 按市场统计股票数量
        stmt = (
            select(Stock.market, func.count(Stock.id))
            .group_by(Stock.market)
        )
        result = await session.execute(stmt)
        stats["stocks_by_market"] = {
            row[0]: row[1] for row in result.all()
        }

        # 按周期统计K线数量
        stmt = (
            select(KLineData.period, func.count(KLineData.id))
            .group_by(KLineData.period)
        )
        result = await session.execute(stmt)
        stats["klines_by_period"] = {
            row[0]: row[1] for row in result.all()
        }

        # 统计有行情数据的股票数量
        stmt = text("""
            SELECT COUNT(DISTINCT stock_id) FROM stock_quotes
        """)
        result = await session.execute(stmt)
        stats["stocks_with_quotes"] = result.scalar()

        # 统计有K线数据的股票数量
        stmt = text("""
            SELECT COUNT(DISTINCT stock_id) FROM kline_data
        """)
        result = await session.execute(stmt)
        stats["stocks_with_klines"] = result.scalar()

        return stats


# 全局数据存储服务实例
_storage_service: Optional[DataStorageService] = None


def get_storage_service() -> DataStorageService:
    """
    获取全局数据存储服务实例

    Returns:
        DataStorageService 实例
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = DataStorageService()
    return _storage_service
