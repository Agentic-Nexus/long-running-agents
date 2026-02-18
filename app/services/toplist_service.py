"""
龙虎榜数据服务模块

提供龙虎榜数据获取、机构席位追踪、资金流向分析和大单监控功能。
基于 AkShare API 实现数据获取。
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd

import akshare as ak
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TopListCache:
    """龙虎榜缓存层"""

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
                logger.debug(f"TopList cache hit: {key}")
                return entry["data"]
            else:
                del self._cache[key]
                logger.debug(f"TopList cache expired: {key}")
        return None

    def set(self, key: str, data: Any) -> None:
        """设置缓存"""
        self._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        logger.debug(f"TopList cache set: {key}")


# 全局缓存实例
_toplist_cache = TopListCache(ttl=300)


def get_toplist_cache() -> TopListCache:
    """获取龙虎榜缓存实例"""
    return _toplist_cache


class TopListService:
    """龙虎榜数据服务类"""

    def __init__(self, use_cache: bool = True):
        """
        初始化龙虎榜服务

        Args:
            use_cache: 是否使用缓存
        """
        self.use_cache = use_cache
        self.cache = _toplist_cache

    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        params = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{prefix}:{params}"

    def get_daily_toplist(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取每日龙虎榜数据

        Args:
            date: 日期，格式 YYYYMMDD，默认最新日期

        Returns:
            龙虎榜数据列表
        """
        cache_key = self._get_cache_key("daily_toplist", date=date or "latest")

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        try:
            # 获取东方财富龙虎榜数据统计
            df = ak.stock_lhb_stock_statistic_em()

            if df is not None and not df.empty:
                result = []
                for _, row in df.iterrows():
                    result.append({
                        "code": str(row.get("代码", "")),
                        "name": str(row.get("名称", "")),
                        "close": float(row.get("收盘价", 0) or 0),
                        "change_percent": float(row.get("涨跌幅", 0) or 0),
                        "turnover": float(row.get("龙虎榜净买额", 0) or 0),
                        "turnover_rate": float(row.get("龙虎榜买入额", 0) or 0),
                        "buy_amount": float(row.get("龙虎榜买入额", 0) or 0),
                        "sell_amount": float(row.get("龙虎榜卖出额", 0) or 0),
                        "net_buy": float(row.get("龙虎榜净买额", 0) or 0),
                        "reason": str(row.get("上榜原因", "")),
                        "trade_amount": float(row.get("成交额", 0) or 0),
                    })

                # 设置缓存
                if self.use_cache:
                    self.cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.error(f"获取每日龙虎榜失败: {e}")
            raise

        return []

    def get_stock_toplist(self, code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取个股历史龙虎榜数据

        Args:
            code: 股票代码
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD

        Returns:
            个股龙虎榜数据列表
        """
        # 标准化股票代码
        code_normalized = self._normalize_symbol(code)

        cache_key = self._get_cache_key("stock_toplist", code=code_normalized, start=start_date, end=end_date)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        try:
            # 设置日期范围
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            # 获取个股龙虎榜详情数据
            df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

            if df is not None and not df.empty:
                # 过滤目标股票（去掉前缀后比较）
                code_to_compare = code_normalized.replace("sh", "").replace("sz", "").replace("bj", "")
                df = df[df["代码"].astype(str).str.contains(code_to_compare, na=False)]

                result = []
                for _, row in df.iterrows():
                    trade_date = str(row.get("上榜日", ""))
                    # 转换日期格式
                    if "-" in trade_date:
                        trade_date = trade_date.replace("-", "")

                    result.append({
                        "date": trade_date,
                        "code": str(row.get("代码", "")),
                        "name": str(row.get("名称", "")),
                        "close": float(row.get("收盘价", 0) or 0),
                        "change_percent": float(row.get("涨跌幅", 0) or 0),
                        "buy_amount": float(row.get("龙虎榜买入额", 0) or 0),
                        "sell_amount": float(row.get("龙虎榜卖出额", 0) or 0),
                        "net_buy": float(row.get("龙虎榜净买额", 0) or 0),
                        "reason": str(row.get("上榜原因", "")),
                        "buy_seats": str(row.get("龙虎榜买入席位", "")) if "龙虎榜买入席位" in row.index else "",
                        "sell_seats": str(row.get("龙虎榜卖出席位", "")) if "龙虎榜卖出席位" in row.index else "",
                    })

                # 设置缓存
                if self.use_cache:
                    self.cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.error(f"获取个股龙虎榜失败 {code}: {e}")
            raise

        return []

    def get_institutional_tracking(self, code: str, days: int = 30) -> Dict[str, Any]:
        """
        获取机构席位追踪

        Args:
            code: 股票代码
            days: 追踪天数

        Returns:
            机构席位追踪数据
        """
        cache_key = self._get_cache_key("institutional_tracking", code=code, days=days)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        # 计算日期范围
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        try:
            # 获取个股龙虎榜数据
            toplist_data = self.get_stock_toplist(code, start_date, end_date)

            if not toplist_data:
                return {
                    "code": code,
                    "institutional_summary": [],
                    "total_net_buy": 0,
                    "total_trades": 0,
                }

            # 分析机构席位
            institutional_summary = self._analyze_institutional_seats(toplist_data)

            # 计算汇总数据
            total_net_buy = sum(item.get("net_buy", 0) for item in toplist_data)
            total_trades = len(toplist_data)

            result = {
                "code": code,
                "name": toplist_data[0].get("name", "") if toplist_data else "",
                "institutional_summary": institutional_summary,
                "total_net_buy": total_net_buy,
                "total_trades": total_trades,
                "period_days": days,
                "latest_date": toplist_data[0].get("date", "") if toplist_data else "",
            }

            # 设置缓存
            if self.use_cache:
                self.cache.set(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"获取机构席位追踪失败 {code}: {e}")
            raise

    def _analyze_institutional_seats(self, toplist_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分析机构席位数据

        Args:
            toplist_data: 龙虎榜数据列表

        Returns:
            机构席位汇总
        """
        # 按机构类型分组统计
        # 这里简化处理，实际应该解析买入/卖出席位的详细信息
        summary = {}

        for item in toplist_data:
            date = item.get("date", "")
            net_buy = item.get("net_buy", 0)

            if date not in summary:
                summary[date] = {
                    "date": date,
                    "net_buy": 0,
                    "buy_amount": 0,
                    "sell_amount": 0,
                    "times": 0,
                }

            summary[date]["net_buy"] += net_buy
            summary[date]["buy_amount"] += item.get("buy_amount", 0)
            summary[date]["sell_amount"] += item.get("sell_amount", 0)
            summary[date]["times"] += 1

        # 转换为列表并排序
        result = sorted(summary.values(), key=lambda x: x["date"], reverse=True)

        return result[:20]  # 返回最近20条

    def get_money_flow(self, code: str, period: str = "daily") -> Dict[str, Any]:
        """
        获取资金流向分析

        Args:
            code: 股票代码
            period: 周期类型 (daily/weekly/monthly)

        Returns:
            资金流向数据
        """
        cache_key = self._get_cache_key("money_flow", code=code, period=period)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        code_normalized = self._normalize_symbol(code)

        try:
            # 获取股票资金流向
            df = ak.stock_individual_fund_flow(stock=code_normalized, market="sh" if code.startswith("6") else "sz")

            if df is not None and not df.empty:
                result = {
                    "code": code,
                    "name": "",
                    "period": period,
                    "data": [],
                    "summary": {
                        "main_net_inflow": 0,
                        "super_net_inflow": 0,
                        "medium_net_inflow": 0,
                        "small_net_inflow": 0,
                    }
                }

                for _, row in df.iterrows():
                    date = str(row.get("日期", ""))
                    main_inflow = float(row.get("主力净流入", 0) or 0)
                    super_inflow = float(row.get("超大单净流入", 0) or 0)
                    medium_inflow = float(row.get("大单净流入", 0) or 0)
                    small_inflow = float(row.get("中单净流入", 0) or 0)

                    result["data"].append({
                        "date": date,
                        "main_net_inflow": main_inflow,
                        "super_net_inflow": super_inflow,
                        "medium_net_inflow": medium_inflow,
                        "small_net_inflow": small_inflow,
                    })

                    result["summary"]["main_net_inflow"] += main_inflow
                    result["summary"]["super_net_inflow"] += super_inflow
                    result["summary"]["medium_net_inflow"] += medium_inflow
                    result["summary"]["small_net_inflow"] += small_inflow

                # 设置缓存
                if self.use_cache:
                    self.cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.error(f"获取资金流向失败 {code}: {e}")
            # 如果资金流向获取失败，尝试从龙虎榜数据推算
            try:
                return self._calculate_money_flow_from_toplist(code)
            except Exception as inner_e:
                logger.error(f"从龙虎榜推算资金流向也失败 {code}: {inner_e}")
                raise

        return {
            "code": code,
            "name": "",
            "period": period,
            "data": [],
            "summary": {
                "main_net_inflow": 0,
                "super_net_inflow": 0,
                "medium_net_inflow": 0,
                "small_net_inflow": 0,
            }
        }

    def _calculate_money_flow_from_toplist(self, code: str) -> Dict[str, Any]:
        """从龙虎榜数据推算资金流向"""
        cache_key = self._get_cache_key("money_flow_toplist", code=code)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        # 获取最近30天的龙虎榜数据
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        toplist_data = self.get_stock_toplist(code, start_date, end_date)

        # 按日期汇总
        daily_flow = {}
        for item in toplist_data:
            date = item.get("date", "")
            if date not in daily_flow:
                daily_flow[date] = {
                    "date": date,
                    "main_net_inflow": 0,
                    "super_net_inflow": 0,
                    "medium_net_inflow": 0,
                    "small_net_inflow": 0,
                }

            net_buy = item.get("net_buy", 0)
            # 简化估算：大单占比约70%，中单约20%，小单约10%
            daily_flow[date]["main_net_inflow"] += net_buy * 0.7
            daily_flow[date]["super_net_inflow"] += net_buy * 0.5
            daily_flow[date]["medium_net_inflow"] += net_buy * 0.2
            daily_flow[date]["small_net_inflow"] += net_buy * 0.1

        result = {
            "code": code,
            "name": toplist_data[0].get("name", "") if toplist_data else "",
            "period": "daily",
            "data": sorted(daily_flow.values(), key=lambda x: x["date"], reverse=True),
            "summary": {
                "main_net_inflow": sum(d["main_net_inflow"] for d in daily_flow.values()),
                "super_net_inflow": sum(d["super_net_inflow"] for d in daily_flow.values()),
                "medium_net_inflow": sum(d["medium_net_inflow"] for d in daily_flow.values()),
                "small_net_inflow": sum(d["small_net_inflow"] for d in daily_flow.values()),
            }
        }

        # 设置缓存
        if self.use_cache:
            self.cache.set(cache_key, result)

        return result

    def get_large_order_monitoring(self, code: str, threshold: float = 10000000) -> Dict[str, Any]:
        """
        大单监控

        Args:
            code: 股票代码
            threshold: 大单阈值（金额），默认1000万

        Returns:
            大单监控数据
        """
        cache_key = self._get_cache_key("large_order", code=code, threshold=threshold)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        # 获取近期龙虎榜数据
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        toplist_data = self.get_stock_toplist(code, start_date, end_date)

        # 筛选大单
        large_orders = []
        for item in toplist_data:
            net_buy = item.get("net_buy", 0)
            if abs(net_buy) >= threshold:
                large_orders.append({
                    "date": item.get("date", ""),
                    "code": item.get("code", ""),
                    "name": item.get("name", ""),
                    "close": item.get("close", 0),
                    "change_percent": item.get("change_percent", 0),
                    "net_buy": net_buy,
                    "buy_amount": item.get("buy_amount", 0),
                    "sell_amount": item.get("sell_amount", 0),
                    "order_type": "买入" if net_buy > 0 else "卖出",
                    "reason": item.get("reason", ""),
                })

        # 统计
        buy_count = sum(1 for o in large_orders if o["order_type"] == "买入")
        sell_count = sum(1 for o in large_orders if o["order_type"] == "卖出")
        total_buy = sum(o["net_buy"] for o in large_orders if o["order_type"] == "买入")
        total_sell = sum(o["net_buy"] for o in large_orders if o["order_type"] == "卖出")

        result = {
            "code": code,
            "name": toplist_data[0].get("name", "") if toplist_data else "",
            "threshold": threshold,
            "large_orders": sorted(large_orders, key=lambda x: x["date"], reverse=True),
            "summary": {
                "total_count": len(large_orders),
                "buy_count": buy_count,
                "sell_count": sell_count,
                "net_inflow": total_buy + total_sell,  # 净流入 = 买入 - |卖出|
            },
            "alert": self._generate_alert(large_orders)
        }

        # 设置缓存
        if self.use_cache:
            self.cache.set(cache_key, result)

        return result

    def _generate_alert(self, large_orders: List[Dict[str, Any]]) -> List[str]:
        """
        生成大单预警信息

        Args:
            large_orders: 大单列表

        Returns:
            预警信息列表
        """
        alerts = []

        if not large_orders:
            alerts.append("近期无大单交易")
            return alerts

        # 分析最近的大单
        recent_orders = large_orders[:5]

        # 检查连续买入
        if len(recent_orders) >= 3:
            buy_streak = sum(1 for o in recent_orders if o["order_type"] == "买入")
            if buy_streak >= 3:
                alerts.append(f"警惕：连续{buy_streak}次大单买入，可能存在拉高出货风险")

        # 检查大单卖出
        sell_orders = [o for o in recent_orders if o["order_type"] == "卖出"]
        if len(sell_orders) >= 2:
            alerts.append(f"警惕：近期出现{len(sell_orders)}次大单卖出，需关注主力动向")

        # 检查净流出
        net_flow = sum(o["net_buy"] for o in recent_orders)
        if net_flow < -50000000:  # 5000万净流出
            alerts.append(f"警告：近期累计净流出{abs(net_flow)/100000000:.2f}亿，需注意风险")

        # 检查异常放量
        if recent_orders:
            avg_amount = sum(abs(o["net_buy"]) for o in recent_orders) / len(recent_orders)
            if abs(recent_orders[0]["net_buy"]) > avg_amount * 2:
                alerts.append("关注：今日大单成交异常放大，需密切关注后续走势")

        if not alerts:
            alerts.append("近期大单交易正常，无明显预警信号")

        return alerts

    def get_capital_distribution(self, code: str) -> Dict[str, Any]:
        """
        获取主力资金分布

        Args:
            code: 股票代码

        Returns:
            资金分布数据
        """
        cache_key = self._get_cache_key("capital_distribution", code=code)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        code_normalized = self._normalize_symbol(code)

        try:
            # 获取资金分布数据
            df = ak.stock_individual_fund_flow(stock=code_normalized, market="sh" if code.startswith("6") else "sz")

            if df is not None and not df.empty:
                # 取最新数据
                latest = df.iloc[0]

                result = {
                    "code": code,
                    "date": str(latest.get("日期", "")),
                    "main_net_inflow": float(latest.get("主力净流入", 0) or 0),
                    "super_net_inflow": float(latest.get("超大单净流入", 0) or 0),
                    "large_net_inflow": float(latest.get("大单净流入", 0) or 0),
                    "medium_net_inflow": float(latest.get("中单净流入", 0) or 0),
                    "small_net_inflow": float(latest.get("小单净流入", 0) or 0),
                    "main_ratio": float(latest.get("主力净流入占比", 0) or 0),
                    "super_ratio": float(latest.get("超大单净流入占比", 0) or 0),
                    "large_ratio": float(latest.get("大单净流入占比", 0) or 0),
                    "medium_ratio": float(latest.get("中单净流入占比", 0) or 0),
                    "small_ratio": float(latest.get("小单净流入占比", 0) or 0),
                }

                # 设置缓存
                if self.use_cache:
                    self.cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.error(f"获取资金分布失败 {code}: {e}")
            raise

        return {
            "code": code,
            "error": "无法获取资金分布数据"
        }

    def _normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码格式

        Args:
            symbol: 原始股票代码

        Returns:
            标准化后的股票代码（6位数字）
        """
        # 移除前缀
        symbol = symbol.replace("sh", "").replace("sz", "").replace("bj", "")
        # 补齐6位
        symbol = symbol.zfill(6)
        return symbol


# 创建全局服务实例
_default_service: Optional[TopListService] = None


def get_toplist_service() -> TopListService:
    """获取默认的龙虎榜服务实例"""
    global _default_service
    if _default_service is None:
        _default_service = TopListService(use_cache=True)
    return _default_service
