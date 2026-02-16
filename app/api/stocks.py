"""
股票相关 API 路由

提供股票搜索、实时行情、历史K线和股票详情等接口。
"""
import time
from collections import defaultdict
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.stock_service import StockService, get_stock_service
from app.services.cache_service import get_cache, cached, CACHE_TTL
from app.services.rate_limiter import get_rate_limiter, get_rate_limit_for_endpoint
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
# 辅助函数
# ============================================

def _get_client_id_from_request(request: Request) -> str:
    """
    从请求中获取客户端标识

    Args:
        request: FastAPI 请求对象

    Returns:
        客户端标识（优先使用用户ID，其次使用IP）
    """
    # 尝试从请求头获取用户ID
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user:{user_id}"

    # 使用客户端IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


async def _handle_rate_limit_check(request: Request, endpoint_type: str = "default"):
    """
    检查频率限制，如果超过限制则抛出异常

    Args:
        request: FastAPI 请求对象
        endpoint_type: 端点类型，用于获取对应的限流配置
    """
    client_id = _get_client_id_from_request(request)
    config = get_rate_limit_for_endpoint(endpoint_type)
    limiter = get_rate_limiter(
        max_requests=config["max_requests"],
        window_seconds=config["window_seconds"]
    )

    if not limiter.is_allowed(client_id):
        remaining = limiter.get_remaining(client_id)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"请求过于频繁，请稍后再试。当前窗口剩余请求次数: {remaining}",
                "retry_after": config["window_seconds"]
            }
        )


# ============================================
# API 端点
# ============================================

@router.get("/search", response_model=List[StockSearchResult])
async def search_stocks(
    request: Request,
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
    await _handle_rate_limit_check(request, "search")

    logger.info(f"搜索股票: {q}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"search:{q}:{limit}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Search cache hit: {cache_key}")
            return [StockSearchResult(**item) for item in cached_result]

        service = get_stock_service()
        results = service.search_stocks(q)

        # 限制返回数量
        results = results[:limit]

        response = [
            StockSearchResult(
                code=stock["code"],
                name=stock["name"],
                market=stock.get("market", ""),
                price=stock.get("price"),
                change=stock.get("change")
            )
            for stock in results
        ]

        # 缓存结果
        cache.set(cache_key, [r.model_dump() for r in response], CACHE_TTL["search"])

        return response

    except Exception as e:
        logger.error(f"股票搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"股票搜索失败: {str(e)}")


@router.get("/quote/{code}", response_model=StockQuote)
async def get_stock_quote(request: Request, code: str):
    """
    获取股票实时行情（缓存 30 秒）

    Args:
        code: 股票代码（如 600000, 000001）

    Returns:
        股票实时报价信息
    """
    # 检查频率限制
    await _handle_rate_limit_check(request, "quote")

    logger.info(f"获取股票行情: {code}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"quote:{code}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Quote cache hit: {cache_key}")
            return StockQuote(**cached_result)

        service = get_stock_service()
        quote = service.get_stock_quote(code)

        if quote is None:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")

        # 缓存结果（30秒）
        cache.set(cache_key, quote, CACHE_TTL["quote"])

        return StockQuote(**quote)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票行情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取股票行情失败: {str(e)}")


@router.get("/kline/{code}", response_model=List[KLineData])
async def get_kline(
    request: Request,
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYYMMDD)"),
    period: str = Query("daily", description="周期类型 (daily/weekly/monthly)"),
    adjust: str = Query("qfq", description="复权类型 (qfq/hfq/空字符串)")
):
    """
    获取股票历史K线数据（缓存 5 分钟）

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
    await _handle_rate_limit_check(request, "kline")

    # 验证周期参数
    valid_periods = ["daily", "weekly", "monthly"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"无效的周期类型: {period}。支持的类型: {valid_periods}"
        )

    logger.info(f"获取K线数据: {code}, 周期: {period}, 复权: {adjust}")

    try:
        # 尝试从缓存获取（仅缓存无日期参数的请求）
        cache = get_cache()
        cache_key = f"kline:{code}:{period}:{adjust}"
        cached_result = cache.get(cache_key)
        if cached_result is not None and start_date is None and end_date is None:
            logger.info(f"Kline cache hit: {cache_key}")
            return [KLineData(**item) for item in cached_result]

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

        # 缓存结果（5分钟，仅当查询参数为空时）
        if start_date is None and end_date is None:
            cache.set(cache_key, kline_data, CACHE_TTL["kline"])

        return [KLineData(**kline) for kline in kline_data]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取K线数据失败: {str(e)}")


@router.get("/{code}", response_model=StockInfo)
async def get_stock_info(request: Request, code: str):
    """
    获取股票详细信息（缓存 5 分钟）

    Args:
        code: 股票代码

    Returns:
        股票详细信息
    """
    # 检查频率限制
    await _handle_rate_limit_check(request, "default")

    logger.info(f"获取股票信息: {code}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"stock_info:{code}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Stock info cache hit: {cache_key}")
            return StockInfo(**cached_result)

        service = get_stock_service()
        info = service.get_stock_info(code)

        if info is None:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")

        result = StockInfo(
            code=info.get("code", code),
            name=info.get("name", ""),
            market=info.get("market", ""),
            industry=info.get("industry"),
            listing_date=info.get("listing_date"),
            total_shares=info.get("total_shares"),
            circulating_shares=info.get("circulating_shares")
        )

        # 缓存结果
        cache.set(cache_key, result.model_dump(), CACHE_TTL["stock_info"])

        return result

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


@router.get("/cache/status")
async def get_cache_status():
    """
    获取缓存状态

    返回缓存的连接状态和使用统计。
    """
    cache = get_cache()
    connected = cache.is_connected()
    return {
        "connected": connected,
        "backend": "redis" if connected else "memory (fallback)",
        "cache_ttl": {
            "quote": CACHE_TTL["quote"],
            "kline": CACHE_TTL["kline"],
            "search": CACHE_TTL["search"],
            "stock_info": CACHE_TTL["stock_info"]
        }
    }


@router.get("/rate_limit/status")
async def get_rate_limit_status(request: Request):
    """
    获取当前频率限制状态

    Returns:
        频率限制信息
    """
    client_id = _get_client_id_from_request(request)
    limiter = get_rate_limiter()

    return {
        "client_id": client_id,
        "max_requests": limiter.max_requests,
        "window_seconds": limiter.window_seconds,
        "remaining_requests": limiter.get_remaining(client_id)
    }
