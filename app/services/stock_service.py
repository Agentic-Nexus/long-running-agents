"""
股票数据服务模块

集成 AkShare API 实现股票数据获取功能：
- 股票基本信息查询
- 历史K线数据获取
- 实时行情获取
- 简单的内存缓存层
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from functools import lru_cache
import pandas as pd

import akshare as ak
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockCache:
    """简单的内存缓存层"""

    def __init__(self, ttl: int = 300):
        """
        初始化缓存

        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self._ttl:
                logger.debug(f"Cache hit: {key}")
                return entry["data"]
            else:
                del self._cache[key]
                logger.debug(f"Cache expired: {key}")
        return None

    def set(self, key: str, data: Any) -> None:
        """设置缓存"""
        self._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        logger.debug(f"Cache set: {key}")

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("Cache cleared")

    def remove(self, key: str) -> None:
        """删除指定缓存"""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache removed: {key}")


# 全局缓存实例
_stock_cache = StockCache(ttl=300)


def get_cache() -> StockCache:
    """获取全局缓存实例"""
    return _stock_cache


def clear_cache() -> None:
    """清空所有缓存"""
    _stock_cache.clear()


class StockService:
    """股票数据服务类"""

    def __init__(self, use_cache: bool = True):
        """
        初始化股票服务

        Args:
            use_cache: 是否使用缓存
        """
        self.use_cache = use_cache
        self.cache = _stock_cache

    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        params = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{prefix}:{params}"

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码，如 '000001' 或 '600000'

        Returns:
            股票基本信息字典，包含 code, name, market, industry 等字段
        """
        cache_key = self._get_cache_key("stock_info", symbol=symbol)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        try:
            # 使用 AkShare 获取股票信息
            # 股票代码需要转换为正确格式
            symbol_normalized = self._normalize_symbol(symbol)

            # 获取股票基本信息
            stock_info_df = ak.stock_individual_info_em(symbol=symbol_normalized)

            # 转换为字典格式
            if stock_info_df is not None and not stock_info_df.empty:
                info_dict = {}
                for _, row in stock_info_df.iterrows():
                    info_dict[row.get("item", "")] = row.get("value", "")

                # 构建标准格式的股票信息
                result = {
                    "code": symbol_normalized,
                    "name": info_dict.get("股票简称", info_dict.get("公司名称", "")),
                    "market": self._get_market(symbol_normalized),
                    "industry": info_dict.get("所属行业", ""),
                    "listing_date": info_dict.get("上市时间", ""),
                    "total_shares": info_dict.get("总股本(万股)", ""),
                    "circulating_shares": info_dict.get("流通股本(万股)", ""),
                }

                # 设置缓存
                if self.use_cache:
                    self.cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.error(f"获取股票信息失败 {symbol}: {e}")
            raise

        return None

    def _normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码格式

        Args:
            symbol: 原始股票代码

        Returns:
            标准化后的股票代码
        """
        # 移除空格
        symbol = symbol.strip()

        # 如果没有前缀，根据规则添加
        if not symbol.startswith(("sh", "sz", "bj")):
            # 上海证券交易所: 6 开头
            # 深圳证券交易所: 0, 3 开头
            # 北京证券交易所: 8, 4 开头
            if symbol.startswith("6"):
                symbol = f"sh{symbol}"
            elif symbol.startswith(("0", "3")):
                symbol = f"sz{symbol}"
            elif symbol.startswith(("8", "4")):
                symbol = f"bj{symbol}"

        return symbol

    def _get_market(self, symbol: str) -> str:
        """根据代码获取市场"""
        if symbol.startswith("sh"):
            return "上海证券交易所"
        elif symbol.startswith("sz"):
            return "深圳证券交易所"
        elif symbol.startswith("bj"):
            return "北京证券交易所"
        return "未知"

    def get_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取股票实时行情

        Args:
            symbol: 股票代码

        Returns:
            实时行情字典
        """
        cache_key = self._get_cache_key("stock_quote", symbol=symbol)

        # 尝试从缓存获取（行情缓存时间较短）
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        try:
            symbol_normalized = self._normalize_symbol(symbol)

            # 获取实时行情
            stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()

            # 筛选目标股票
            stock_data = stock_zh_a_spot_em_df[
                stock_zh_a_spot_em_df["代码"] == symbol_normalized.replace("sh", "").replace("sz", "").replace("bj", "")
            ]

            if not stock_data.empty:
                row = stock_data.iloc[0]

                # 计算涨跌幅
                close = float(row.get("最新价", 0) or 0)
                change = float(row.get("涨跌幅", 0) or 0)

                result = {
                    "code": symbol_normalized,
                    "name": row.get("名称", ""),
                    "price": close,
                    "change": change,
                    "change_percent": change,  # 涨跌幅已经是百分比
                    "volume": int(row.get("成交量", 0) or 0),
                    "amount": float(row.get("成交额", 0) or 0),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                # 设置缓存
                if self.use_cache:
                    # 行情缓存时间较短，30秒
                    self.cache._ttl = 30
                    self.cache.set(cache_key, result)
                    # 恢复默认 TTL
                    self.cache._ttl = 300

                return result

        except Exception as e:
            logger.error(f"获取股票行情失败 {symbol}: {e}")
            raise

        return None

    def get_kline_data(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取股票历史K线数据

        Args:
            symbol: 股票代码
            period: 周期类型，可选 'daily', 'weekly', 'monthly'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            adjust: 复权类型，可选 'qfq' (前复权), 'hfq' (后复权), '' (不复权)

        Returns:
            K线数据列表
        """
        cache_key = self._get_cache_key(
            "kline", symbol=symbol, period=period, start_date=start_date, end_date=end_date, adjust=adjust
        )

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        try:
            symbol_normalized = self._normalize_symbol(symbol)

            # 设置默认日期范围
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            # 根据周期选择接口
            if period == "daily":
                df = ak.stock_zh_a_hist(
                    symbol=symbol_normalized,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )
            elif period == "weekly":
                df = ak.stock_zh_a_hist(
                    symbol=symbol_normalized,
                    period="weekly",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )
            elif period == "monthly":
                df = ak.stock_zh_a_hist(
                    symbol=symbol_normalized,
                    period="monthly",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )
            else:
                raise ValueError(f"不支持的周期类型: {period}")

            if df is not None and not df.empty:
                # 转换为字典列表
                result = []
                for _, row in df.iterrows():
                    result.append({
                        "code": symbol_normalized,
                        "date": row.get("日期", "").strftime("%Y-%m-%d") if isinstance(row.get("日期"), datetime) else str(row.get("日期", "")),
                        "open": float(row.get("开盘", 0) or 0),
                        "high": float(row.get("最高", 0) or 0),
                        "low": float(row.get("最低", 0) or 0),
                        "close": float(row.get("收盘", 0) or 0),
                        "volume": int(row.get("成交量", 0) or 0),
                        "amount": float(row.get("成交额", 0) or 0),
                    })

                # 设置缓存
                if self.use_cache:
                    self.cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            raise

        return None

    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的股票列表
        """
        try:
            # 获取A股实时行情作为搜索数据源
            stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()

            # 模糊匹配
            mask = (
                stock_zh_a_spot_em_df["代码"].astype(str).str.contains(keyword, na=False) |
                stock_zh_a_spot_em_df["名称"].astype(str).str.contains(keyword, na=False)
            )

            results = stock_zh_a_spot_em_df[mask].head(20)

            stocks = []
            for _, row in results.iterrows():
                code_with_prefix = row.get("代码", "")
                # 添加市场前缀
                if code_with_prefix.startswith("6"):
                    code = f"sh{code_with_prefix}"
                else:
                    code = f"sz{code_with_prefix}"

                stocks.append({
                    "code": code,
                    "name": row.get("名称", ""),
                    "market": self._get_market(code),
                    "price": float(row.get("最新价", 0) or 0),
                    "change": float(row.get("涨跌幅", 0) or 0),
                })

            return stocks

        except Exception as e:
            logger.error(f"搜索股票失败 {keyword}: {e}")
            raise


# 创建全局服务实例
_default_service: Optional[StockService] = None


def get_stock_service() -> StockService:
    """获取默认的股票服务实例"""
    global _default_service
    if _default_service is None:
        _default_service = StockService(use_cache=True)
    return _default_service
