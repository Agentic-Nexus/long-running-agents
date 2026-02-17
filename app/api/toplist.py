"""
龙虎榜数据 API 路由

提供龙虎榜数据、机构席位追踪、资金流向分析和大单监控接口。
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.toplist_service import TopListService, get_toplist_service
from app.services.cache_service import get_cache, CACHE_TTL
from app.services.rate_limiter import get_rate_limiter, get_rate_limit_for_endpoint
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================
# 请求/响应模型
# ============================================

class TopListItem(BaseModel):
    """龙虎榜单条数据"""
    code: str
    name: str
    close: float
    change_percent: float
    turnover: float
    turnover_rate: float
    buy_amount: float
    sell_amount: float
    net_buy: float
    reason: str
    trade_amount: float


class DailyToplistResponse(BaseModel):
    """每日龙虎榜响应"""
    date: str
    count: int
    data: List[TopListItem]


class StockToplistItem(BaseModel):
    """个股龙虎榜数据"""
    date: str
    code: str
    name: str
    close: float
    change_percent: float
    buy_amount: float
    sell_amount: float
    net_buy: float
    reason: str
    buy_seats: Optional[str] = None
    sell_seats: Optional[str] = None


class InstitutionalTrackingItem(BaseModel):
    """机构席位追踪项"""
    date: str
    net_buy: float
    buy_amount: float
    sell_amount: float
    times: int


class InstitutionalTrackingResponse(BaseModel):
    """机构席位追踪响应"""
    code: str
    name: str
    institutional_summary: List[InstitutionalTrackingItem]
    total_net_buy: float
    total_trades: int
    period_days: int
    latest_date: str


class MoneyFlowItem(BaseModel):
    """资金流向项"""
    date: str
    main_net_inflow: float
    super_net_inflow: float
    medium_net_inflow: float
    small_net_inflow: float


class MoneyFlowSummary(BaseModel):
    """资金流向汇总"""
    main_net_inflow: float
    super_net_inflow: float
    medium_net_inflow: float
    small_net_inflow: float


class MoneyFlowResponse(BaseModel):
    """资金流向响应"""
    code: str
    name: str
    period: str
    data: List[MoneyFlowItem]
    summary: MoneyFlowSummary


class LargeOrderItem(BaseModel):
    """大单监控项"""
    date: str
    code: str
    name: str
    close: float
    change_percent: float
    net_buy: float
    buy_amount: float
    sell_amount: float
    order_type: str
    reason: str


class LargeOrderSummary(BaseModel):
    """大单监控汇总"""
    total_count: int
    buy_count: int
    sell_count: int
    net_inflow: float


class LargeOrderResponse(BaseModel):
    """大单监控响应"""
    code: str
    name: str
    threshold: float
    large_orders: List[LargeOrderItem]
    summary: LargeOrderSummary
    alert: List[str]


class CapitalDistributionResponse(BaseModel):
    """资金分布响应"""
    code: str
    date: Optional[str] = None
    main_net_inflow: Optional[float] = None
    super_net_inflow: Optional[float] = None
    large_net_inflow: Optional[float] = None
    medium_net_inflow: Optional[float] = None
    small_net_inflow: Optional[float] = None
    main_ratio: Optional[float] = None
    super_ratio: Optional[float] = None
    large_ratio: Optional[float] = None
    medium_ratio: Optional[float] = None
    small_ratio: Optional[float] = None
    error: Optional[str] = None


# ============================================
# 辅助函数
# ============================================

async def _handle_rate_limit_check(request: Request, endpoint_type: str = "default"):
    """
    检查频率限制
    """
    # 简化处理，实际项目中应实现完整的限流逻辑
    pass


# ============================================
# API 端点
# ============================================

@router.get("/daily", response_model=DailyToplistResponse)
async def get_daily_toplist(
    request: Request,
    date: Optional[str] = Query(None, description="日期，格式 YYYYMMDD，默认最新日期")
):
    """
    获取每日龙虎榜数据

    返回当日龙虎榜上榜股票列表，包括买卖金额、涨跌幅等信息。
    """
    logger.info(f"获取每日龙虎榜: {date or '最新'}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"toplist:daily:{date or 'latest'}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Daily toplist cache hit: {cache_key}")
            return DailyToplistResponse(**cached_result)

        service = get_toplist_service()
        data = service.get_daily_toplist(date)

        # 获取日期
        if date:
            query_date = date
        else:
            query_date = data[0].get("date", "") if data else datetime.now().strftime("%Y%m%d")

        result = {
            "date": query_date,
            "count": len(data),
            "data": data
        }

        # 缓存结果
        cache.set(cache_key, result, CACHE_TTL.get("stock_info", 300))

        return DailyToplistResponse(**result)

    except Exception as e:
        logger.error(f"获取每日龙虎榜失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取每日龙虎榜失败: {str(e)}")


@router.get("/stock/{code}", response_model=List[StockToplistItem])
async def get_stock_toplist(
    request: Request,
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYYMMDD)")
):
    """
    获取个股历史龙虎榜数据

    返回指定股票的历史上榜记录。
    """
    logger.info(f"获取个股龙虎榜: {code}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"toplist:stock:{code}:{start_date or 'all'}:{end_date or 'all'}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Stock toplist cache hit: {cache_key}")
            return [StockToplistItem(**item) for item in cached_result]

        service = get_toplist_service()
        data = service.get_stock_toplist(code, start_date, end_date)

        # 缓存结果
        cache.set(cache_key, data, CACHE_TTL.get("stock_info", 300))

        return [StockToplistItem(**item) for item in data]

    except Exception as e:
        logger.error(f"获取个股龙虎榜失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取个股龙虎榜失败: {str(e)}")


@router.get("/institutional/{code}", response_model=InstitutionalTrackingResponse)
async def get_institutional_tracking(
    request: Request,
    code: str,
    days: int = Query(30, ge=1, le=90, description="追踪天数")
):
    """
    获取机构席位追踪

    分析股票近期机构买卖情况，追踪主力动向。
    """
    logger.info(f"获取机构席位追踪: {code}, 天数: {days}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"toplist:institutional:{code}:{days}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Institutional tracking cache hit: {cache_key}")
            return InstitutionalTrackingResponse(**cached_result)

        service = get_toplist_service()
        data = service.get_institutional_tracking(code, days)

        # 缓存结果
        cache.set(cache_key, data, CACHE_TTL.get("stock_info", 300))

        return InstitutionalTrackingResponse(**data)

    except Exception as e:
        logger.error(f"获取机构席位追踪失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取机构席位追踪失败: {str(e)}")


@router.get("/money_flow/{code}", response_model=MoneyFlowResponse)
async def get_money_flow(
    request: Request,
    code: str,
    period: str = Query("daily", description="周期类型 (daily/weekly/monthly)")
):
    """
    获取资金流向分析

    分析股票资金流入流出情况，包括主力、超大单、大单、中单、小单。
    """
    logger.info(f"获取资金流向: {code}, 周期: {period}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"toplist:money_flow:{code}:{period}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Money flow cache hit: {cache_key}")
            return MoneyFlowResponse(**cached_result)

        service = get_toplist_service()
        data = service.get_money_flow(code, period)

        # 缓存结果
        cache.set(cache_key, data, CACHE_TTL.get("stock_info", 300))

        return MoneyFlowResponse(**data)

    except Exception as e:
        logger.error(f"获取资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取资金流向失败: {str(e)}")


@router.get("/large_order/{code}", response_model=LargeOrderResponse)
async def get_large_order_monitoring(
    request: Request,
    code: str,
    threshold: float = Query(10000000, ge=1000000, description="大单阈值（金额）")
):
    """
    大单监控

    监控指定股票的大单交易情况，提供预警信息。
    """
    logger.info(f"获取大单监控: {code}, 阈值: {threshold}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"toplist:large_order:{code}:{threshold}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Large order cache hit: {cache_key}")
            return LargeOrderResponse(**cached_result)

        service = get_toplist_service()
        data = service.get_large_order_monitoring(code, threshold)

        # 缓存结果
        cache.set(cache_key, data, CACHE_TTL.get("stock_info", 300))

        return LargeOrderResponse(**data)

    except Exception as e:
        logger.error(f"获取大单监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取大单监控失败: {str(e)}")


@router.get("/capital/{code}", response_model=CapitalDistributionResponse)
async def get_capital_distribution(
    request: Request,
    code: str
):
    """
    获取主力资金分布

    返回当日各类型订单的资金流入情况。
    """
    logger.info(f"获取资金分布: {code}")

    try:
        # 尝试从缓存获取
        cache = get_cache()
        cache_key = f"toplist:capital:{code}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Capital distribution cache hit: {cache_key}")
            return CapitalDistributionResponse(**cached_result)

        service = get_toplist_service()
        data = service.get_capital_distribution(code)

        # 缓存结果
        cache.set(cache_key, data, CACHE_TTL.get("quote", 60))

        return CapitalDistributionResponse(**data)

    except Exception as e:
        logger.error(f"获取资金分布失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取资金分布失败: {str(e)}")


# ============================================
# 根路由
# ============================================

@router.get("/")
async def toplist_root():
    """
    龙虎榜API根路由

    返回API的基本信息和使用说明。
    """
    return {
        "message": "TopList API",
        "version": "1.0.0",
        "endpoints": {
            "daily": "/api/v1/toplist/daily - 每日龙虎榜",
            "stock": "/api/v1/toplist/stock/<code> - 个股龙虎榜",
            "institutional": "/api/v1/toplist/institutional/<code> - 机构席位追踪",
            "money_flow": "/api/v1/toplist/money_flow/<code> - 资金流向分析",
            "large_order": "/api/v1/toplist/large_order/<code> - 大单监控",
            "capital": "/api/v1/toplist/capital/<code> - 资金分布"
        }
    }


# 导入 datetime 用于默认日期
from datetime import datetime
