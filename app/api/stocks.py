"""
股票相关 API 路由

提供股票搜索、实时行情、历史K线和股票详情等接口。
"""
import time
import asyncio
from collections import defaultdict
from threading import Lock
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.services.stock_service import StockService, get_stock_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================
# 请求/响应模型
# ============================================

class StockInfo(BaseModel):
    """股票信息"""
    code: str
    name: str
    market: str
    industry: Optional[str] = None
    listing_date: Optional[str] = None
    total_shares: Optional[str] = None
    circulating_shares: Optional[str] = None


class StockSearchResult(BaseModel):
    """股票搜索结果"""
    code: str
    name: str
    market: str
    price: Optional[float] = None
    change: Optional[float] = None


class StockQuote(BaseModel):
    """股票报价"""
    code: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    amount: float
    timestamp: str


class KLineData(BaseModel):
    """K线数据"""
    code: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None


# ============================================
# 请求频率限制
# ============================================

class RateLimiter:
    """简单的请求频率限制器"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """
        初始化频率限制器

        Args:
            max_requests: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        """
        检查是否允许请求

        Args:
            client_id: 客户端标识

        Returns:
            是否允许请求
        """
        current_time = time.time()

        with self._lock:
            # 清理过期的请求记录
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id]
                if current_time - req_time < self.window_seconds
            ]

            # 检查是否超过限制
            if len(self._requests[client_id]) >= self.max_requests:
                return False

            # 记录新请求
            self._requests[client_id].append(current_time)
            return True

    def get_remaining(self, client_id: str) -> int:
        """
        获取剩余请求次数

        Args:
            client_id: 客户端标识

        Returns:
            剩余请求次数
        """
        current_time = time.time()

        with self._lock:
            # 清理过期的请求记录
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id]
                if current_time - req_time < self.window_seconds
            ]

            return max(0, self.max_requests - len(self._requests[client_id]))

    def reset(self, client_id: str) -> None:
        """
        重置指定客户端的请求计数

        Args:
            client_id: 客户端标识
        """
        with self._lock:
            if client_id in self._requests:
                del self._requests[client_id]


# 全局限流器实例
_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


def get_rate_limiter() -> RateLimiter:
    """获取频率限制器实例"""
    return _rate_limiter


# ============================================
# 辅助函数
# ============================================

def _get_client_id_from_request() -> str:
    """
    从请求中获取客户端标识
    在实际应用中，这里可以从请求头、IP等获取
    为了简单起见，使用固定的默认标识
    """
    return "default"


async def _handle_rate_limit_check():
    """检查频率限制，如果超过限制则抛出异常"""
    client_id = _get_client_id_from_request()
    limiter = get_rate_limiter()

    if not limiter.is_allowed(client_id):
        remaining = limiter.get_remaining(client_id)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"请求过于频繁，请稍后再试。当前窗口剩余请求次数: {remaining}",
                "retry_after": 60
            }
        )


# ============================================
# API 端点
# ============================================

@router.get("/search", response_model=List[StockSearchResult])
async def search_stocks(
    q: str = Query(..., min_length=1, max_length=50, description="搜索关键词（股票代码或名称）"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量限制")
):
    """
    股票搜索接口

    根据关键词搜索股票，支持按股票代码或名称模糊搜索。

    Args:
        q: 搜索关键词
        limit: 返回结果数量限制

    Returns:
        匹配的股票列表
    """
    # 检查频率限制
    await _handle_rate_limit_check()

    logger.info(f"搜索股票: {q}")

    try:
        service = get_stock_service()
        results = service.search_stocks(q)

        # 限制返回数量
        results = results[:limit]

        return [
            StockSearchResult(
                code=stock["code"],
                name=stock["name"],
                market=stock.get("market", ""),
                price=stock.get("price"),
                change=stock.get("change")
            )
            for stock in results
        ]

    except Exception as e:
        logger.error(f"股票搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"股票搜索失败: {str(e)}")


@router.get("/quote/{code}", response_model=StockQuote)
async def get_stock_quote(code: str):
    """
    获取股票实时行情

    Args:
        code: 股票代码（如 600000, 000001）

    Returns:
        股票实时报价信息
    """
    # 检查频率限制
    await _handle_rate_limit_check()

    logger.info(f"获取股票行情: {code}")

    try:
        service = get_stock_service()
        quote = service.get_stock_quote(code)

        if quote is None:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")

        return StockQuote(**quote)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票行情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取股票行情失败: {str(e)}")


@router.get("/kline/{code}", response_model=List[KLineData])
async def get_kline(
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYYMMDD)"),
    period: str = Query("daily", description="周期类型 (daily/weekly/monthly)"),
    adjust: str = Query("qfq", description="复权类型 (qfq/hfq/空字符串)")
):
    """
    获取股票历史K线数据

    Args:
        code: 股票代码
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD
        period: 周期类型，可选 daily(日线), weekly(周线), monthly(月线)
        adjust: 复权类型，可选 qfq(前复权), hfq(后复权), 空字符串(不复权)

    Returns:
        K线数据列表
    """
    # 检查频率限制
    await _handle_rate_limit_check()

    # 验证周期参数
    valid_periods = ["daily", "weekly", "monthly"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"无效的周期类型: {period}。支持的类型: {valid_periods}"
        )

    logger.info(f"获取K线数据: {code}, 周期: {period}, 复权: {adjust}")

    try:
        service = get_stock_service()
        kline_data = service.get_kline_data(
            symbol=code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )

        if kline_data is None or len(kline_data) == 0:
            raise HTTPException(status_code=404, detail=f"未找到K线数据: {code}")

        return [KLineData(**kline) for kline in kline_data]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取K线数据失败: {str(e)}")


@router.get("/{code}", response_model=StockInfo)
async def get_stock_info(code: str):
    """
    获取股票详细信息

    Args:
        code: 股票代码

    Returns:
        股票详细信息
    """
    # 检查频率限制
    await _handle_rate_limit_check()

    logger.info(f"获取股票信息: {code}")

    try:
        service = get_stock_service()
        info = service.get_stock_info(code)

        if info is None:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")

        return StockInfo(
            code=info.get("code", code),
            name=info.get("name", ""),
            market=info.get("market", ""),
            industry=info.get("industry"),
            listing_date=info.get("listing_date"),
            total_shares=info.get("total_shares"),
            circulating_shares=info.get("circulating_shares")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取股票信息失败: {str(e)}")


# ============================================
# 额外的辅助端点
# ============================================

@router.get("/")
async def stocks_root():
    """
    股票API根路由

    返回API的基本信息和使用说明。
    """
    return {
        "message": "Stock API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/v1/stocks/search?q=<keyword> - 搜索股票",
            "quote": "/api/v1/stocks/quote/<code> - 获取实时行情",
            "kline": "/api/v1/stocks/kline/<code> - 获取历史K线",
            "info": "/api/v1/stocks/<code> - 获取股票详情"
        },
        "rate_limit": {
            "max_requests": 60,
            "window_seconds": 60
        }
    }


@router.get("/rate_limit/status")
async def get_rate_limit_status():
    """
    获取当前频率限制状态

    Returns:
        频率限制信息
    """
    client_id = _get_client_id_from_request()
    limiter = get_rate_limiter()

    return {
        "client_id": client_id,
        "max_requests": limiter.max_requests,
        "window_seconds": limiter.window_seconds,
        "remaining_requests": limiter.get_remaining(client_id)
    }
