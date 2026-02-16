"""
股票分析报告 API

提供技术分析、基本面分析和投资建议等接口。
"""
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from threading import Lock

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.stock_service import get_stock_service
from app.services.technical_analysis import calculate_all_indicators, add_indicators_to_dataframe
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================
# 缓存机制
# ============================================

class AnalysisCache:
    """分析结果缓存"""

    def __init__(self, ttl: int = 600):
        """
        初始化缓存

        Args:
            ttl: 缓存过期时间（秒），默认 10 分钟
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self._ttl:
                    logger.debug(f"Analysis cache hit: {key}")
                    return entry["data"]
                else:
                    del self._cache[key]
                    logger.debug(f"Analysis cache expired: {key}")
        return None

    def set(self, key: str, data: Any) -> None:
        """设置缓存"""
        with self._lock:
            self._cache[key] = {
                "data": data,
                "timestamp": time.time()
            }
            logger.debug(f"Analysis cache set: {key}")

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("Analysis cache cleared")


# 全局缓存实例
_analysis_cache = AnalysisCache(ttl=600)


def get_analysis_cache() -> AnalysisCache:
    """获取分析缓存实例"""
    return _analysis_cache


# ============================================
# 请求/响应模型
# ============================================

class TechnicalAnalysisRequest(BaseModel):
    """技术分析请求"""
    code: str
    period: str = "daily"
    adjust: str = "qfq"


class FundamentalData(BaseModel):
    """基本面数据"""
    pe: Optional[float] = None  # 市盈率
    pb: Optional[float] = None  # 市净率
    market_cap: Optional[float] = None  # 总市值
    float_market_cap: Optional[float] = None  # 流通市值
    revenue: Optional[float] = None  # 营业收入
    net_profit: Optional[float] = None  # 净利润
    roe: Optional[float] = None  # 净资产收益率
    gross_margin: Optional[float] = None  # 毛利率
    debt_ratio: Optional[float] = None  # 资产负债率
    current_ratio: Optional[float] = None  # 流动比率


class TechnicalIndicators(BaseModel):
    """技术指标"""
    ma: Optional[Dict[str, float]] = None  # 移动平均线
    macd: Optional[Dict[str, float]] = None  # MACD
    rsi: Optional[Dict[str, float]] = None  # RSI
    bollinger: Optional[Dict[str, float]] = None  # 布林带
    kdj: Optional[Dict[str, float]] = None  # KDJ


class TechnicalAnalysisResponse(BaseModel):
    """技术分析响应"""
    code: str
    name: str
    timestamp: str
    current_price: float
    change_percent: float
    indicators: TechnicalIndicators
    summary: str
    signal: str  # buy, sell, neutral


class FundamentalAnalysisResponse(BaseModel):
    """基本面分析响应"""
    code: str
    name: str
    timestamp: str
    market: str
    industry: Optional[str]
    fundamental_data: FundamentalData
    summary: str
    rating: str  # excellent, good, fair, poor


class InvestmentAdviceResponse(BaseModel):
    """投资建议响应"""
    code: str
    name: str
    timestamp: str
    advice: str  # strong_buy, buy, hold, sell, strong_sell
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_level: str  # low, medium, high
    reasoning: str
    summary: str


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None


# ============================================
# 辅助函数
# ============================================

def _format_technical_summary(
    price: float,
    change_pct: float,
    indicators: Dict[str, Any]
) -> str:
    """
    格式化技术分析摘要

    Args:
        price: 当前价格
        change_pct: 涨跌幅
        indicators: 技术指标

    Returns:
        摘要文本
    """
    summary_parts = []

    # 价格信息
    summary_parts.append(f"当前价格: {price:.2f}，涨跌幅: {change_pct:.2f}%")

    # MA 分析
    ma = indicators.get("ma", {})
    if ma:
        latest = list(ma.values())[0] if ma else None
        if latest:
            ma_status = "多头排列" if price > latest else "空头排列"
            summary_parts.append(f"MA20: {latest:.2f} ({ma_status})")

    # MACD 分析
    macd = indicators.get("macd", {})
    if macd:
        dif = macd.get("DIF", 0)
        dea = macd.get("DEA", 0)
        if dif > dea:
            summary_parts.append("MACD: 金叉信号，看涨")
        else:
            summary_parts.append("MACD: 死叉信号，看跌")

    # RSI 分析
    rsi = indicators.get("rsi", {})
    if rsi:
        rsi_6 = rsi.get("RSI-6", 50)
        if rsi_6 > 70:
            summary_parts.append(f"RSI-6: {rsi_6:.1f} (超买区域)")
        elif rsi_6 < 30:
            summary_parts.append(f"RSI-6: {rsi_6:.1f} (超卖区域)")
        else:
            summary_parts.append(f"RSI-6: {rsi_6:.1f} (中性区域)")

    # 布林带分析
    bb = indicators.get("bollinger", {})
    if bb:
        upper = bb.get("Upper", 0)
        lower = bb.get("Lower", 0)
        if price > upper:
            summary_parts.append("布林带: 突破上轨，注意回调风险")
        elif price < lower:
            summary_parts.append("布林带: 跌破下轨，可能存在反弹机会")

    return "；".join(summary_parts)


def _generate_technical_signal(indicators: Dict[str, Any], price: float) -> str:
    """
    生成技术信号

    Args:
        indicators: 技术指标
        price: 当前价格

    Returns:
        信号: buy, sell, neutral
    """
    score = 0

    # MACD 信号
    macd = indicators.get("macd", {})
    if macd.get("DIF", 0) > macd.get("DEA", 0):
        score += 1
    else:
        score -= 1

    # KDJ 信号
    kdj = indicators.get("kdj", {})
    k = kdj.get("K", 50)
    d = kdj.get("D", 50)
    if k > d and k < 80:
        score += 1
    elif k < d and k > 20:
        score -= 1

    # RSI 信号
    rsi = indicators.get("rsi", {})
    rsi_6 = rsi.get("RSI-6", 50)
    if rsi_6 < 30:
        score += 1  # 超卖，可能反弹
    elif rsi_6 > 70:
        score -= 1  # 超买，可能回调

    # 价格与均线关系
    ma = indicators.get("ma", {})
    ma20 = ma.get("MA20", price)
    if price > ma20:
        score += 1
    else:
        score -= 1

    # 布林带位置
    bb = indicators.get("bollinger", {})
    lower = bb.get("Lower", 0)
    upper = bb.get("Upper", 0)
    if price < lower:
        score += 1
    elif price > upper:
        score -= 1

    if score >= 2:
        return "buy"
    elif score <= -2:
        return "sell"
    else:
        return "neutral"


def _generate_fundamental_rating(fundamental_data: Dict[str, Any]) -> str:
    """
    生成基本面评级

    Args:
        fundamental_data: 基本面数据

    Returns:
        评级: excellent, good, fair, poor
    """
    score = 0

    # PE 估值
    pe = fundamental_data.get("pe")
    if pe is not None:
        if 0 < pe < 15:
            score += 2
        elif 15 <= pe < 30:
            score += 1
        elif pe >= 60:
            score -= 1

    # ROE
    roe = fundamental_data.get("roe")
    if roe is not None:
        if roe > 20:
            score += 2
        elif roe > 10:
            score += 1
        elif roe < 5:
            score -= 1

    # 毛利率
    gross_margin = fundamental_data.get("gross_margin")
    if gross_margin is not None:
        if gross_margin > 40:
            score += 1
        elif gross_margin < 10:
            score -= 1

    if score >= 3:
        return "excellent"
    elif score >= 1:
        return "good"
    elif score >= -1:
        return "fair"
    else:
        return "poor"


def _generate_investment_advice(
    technical_signal: str,
    fundamental_rating: str,
    current_price: float,
    change_pct: float
) -> Dict[str, Any]:
    """
    生成投资建议

    Args:
        technical_signal: 技术信号
        fundamental_rating: 基本面评级
        current_price: 当前价格
        change_pct: 涨跌幅

    Returns:
        投资建议字典
    """
    # 综合评分
    signal_score = {"buy": 2, "neutral": 0, "sell": -2}.get(technical_signal, 0)
    rating_score = {"excellent": 2, "good": 1, "fair": 0, "poor": -1}.get(fundamental_rating, 0)
    total_score = signal_score + rating_score

    # 生成建议
    if total_score >= 3:
        advice = "strong_buy"
        risk_level = "low"
    elif total_score >= 1:
        advice = "buy"
        risk_level = "medium"
    elif total_score >= -1:
        advice = "hold"
        risk_level = "medium"
    elif total_score >= -3:
        advice = "sell"
        risk_level = "high"
    else:
        advice = "strong_sell"
        risk_level = "high"

    # 目标价和止损价（基于技术分析）
    if advice in ["strong_buy", "buy"]:
        target_price = current_price * 1.15  # 15% 上涨空间
        stop_loss = current_price * 0.92  # 8% 止损
    elif advice == "hold":
        target_price = current_price * 1.08
        stop_loss = current_price * 0.95
    else:
        target_price = current_price * 0.9
        stop_loss = current_price * 1.05

    return {
        "advice": advice,
        "target_price": round(target_price, 2),
        "stop_loss": round(stop_loss, 2),
        "risk_level": risk_level
    }


def _format_fundamental_summary(fundamental_data: Dict[str, Any], rating: str) -> str:
    """
    格式化基本面分析摘要

    Args:
        fundamental_data: 基本面数据
        rating: 评级

    Returns:
        摘要文本
    """
    summary_parts = []

    # 估值分析
    pe = fundamental_data.get("pe")
    pb = fundamental_data.get("pb")
    if pe is not None:
        pe_status = "合理" if 15 <= pe < 30 else ("偏低" if pe < 15 else "偏高")
        summary_parts.append(f"市盈率(PE): {pe:.2f} ({pe_status})")
    if pb is not None:
        summary_parts.append(f"市净率(PB): {pb:.2f}")

    # 盈利能力
    roe = fundamental_data.get("roe")
    if roe is not None:
        roe_status = "优秀" if roe > 20 else ("良好" if roe > 10 else "一般")
        summary_parts.append(f"净资产收益率(ROE): {roe:.2f}% ({roe_status})")

    # 营收和利润
    revenue = fundamental_data.get("revenue")
    net_profit = fundamental_data.get("net_profit")
    if revenue is not None:
        summary_parts.append(f"营业收入: {revenue:.2f}亿元")
    if net_profit is not None:
        summary_parts.append(f"净利润: {net_profit:.2f}亿元")

    # 评级总结
    rating_text = {
        "excellent": "该股票基本面优秀，具有较强的竞争力和成长潜力",
        "good": "该股票基本面良好，具备一定的投资价值",
        "fair": "该股票基本面一般，需要进一步观察",
        "poor": "该股票基本面较差，投资需谨慎"
    }.get(rating, "")

    summary_parts.append(rating_text)

    return "；".join(summary_parts)


# ============================================
# API 端点
# ============================================

@router.get("/technical/{code}", response_model=TechnicalAnalysisResponse)
async def get_technical_analysis(
    code: str,
    period: str = Query("daily", description="周期类型 (daily/weekly/monthly)"),
    adjust: str = Query("qfq", description="复权类型 (qfq/hfq/空字符串)")
):
    """
    获取股票技术分析

    基于技术指标（MA、MACD、RSI、布林带、KDJ）进行技术分析，
    生成技术信号和摘要。

    Args:
        code: 股票代码
        period: 周期类型
        adjust: 复权类型

    Returns:
        技术分析结果
    """
    cache_key = f"technical:{code}:{period}:{adjust}"

    # 尝试从缓存获取
    cached = get_analysis_cache().get(cache_key)
    if cached:
        return cached

    logger.info(f"执行技术分析: {code}")

    try:
        # 获取股票服务
        service = get_stock_service()

        # 获取股票信息
        stock_info = service.get_stock_info(code)
        if stock_info is None:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")

        # 获取实时行情
        quote = service.get_stock_quote(code)
        if quote is None:
            raise HTTPException(status_code=404, detail=f"未找到股票行情: {code}")

        # 获取K线数据
        kline_data = service.get_kline_data(
            symbol=code,
            period=period,
            adjust=adjust,
            start_date=None,
            end_date=None
        )

        if kline_data is None or len(kline_data) < 30:
            raise HTTPException(status_code=400, detail=f"K线数据不足，无法进行技术分析")

        # 转换为 DataFrame
        df = pd.DataFrame(kline_data)

        # 计算技术指标
        indicators = calculate_all_indicators(df)
        df_with_indicators = add_indicators_to_dataframe(df)

        # 获取最新指标值
        latest = df_with_indicators.iloc[-1]

        # 提取 MA 指标
        ma_values = {}
        for col in ["MA5", "MA10", "MA20", "MA60"]:
            if col in latest and pd.notna(latest[col]):
                ma_values[col] = round(float(latest[col]), 2)

        # 提取 MACD 指标
        macd_values = {}
        for col in ["DIF", "DEA", "MACD"]:
            if col in latest and pd.notna(latest[col]):
                macd_values[col] = round(float(latest[col]), 4)

        # 提取 RSI 指标
        rsi_values = {}
        for col in ["RSI-6", "RSI-12", "RSI-24"]:
            if col in latest and pd.notna(latest[col]):
                rsi_values[col] = round(float(latest[col]), 2)

        # 提取布林带指标
        bb_values = {}
        for col in ["Upper", "Middle", "Lower"]:
            if col in latest and pd.notna(latest[col]):
                bb_values[col] = round(float(latest[col]), 2)

        # 提取 KDJ 指标
        kdj_values = {}
        for col in ["K", "D", "J"]:
            if col in latest and pd.notna(latest[col]):
                kdj_values[col] = round(float(latest[col]), 2)

        # 格式化指标为字典
        indicators_dict = {
            "ma": ma_values if ma_values else None,
            "macd": macd_values if macd_values else None,
            "rsi": rsi_values if rsi_values else None,
            "bollinger": bb_values if bb_values else None,
            "kdj": kdj_values if kdj_values else None
        }

        # 获取当前价格和涨跌幅
        current_price = quote.get("price", 0)
        change_percent = quote.get("change_percent", 0)

        # 生成摘要和信号
        summary = _format_technical_summary(current_price, change_percent, indicators_dict)
        signal = _generate_technical_signal(indicators_dict, current_price)

        # 构建响应
        response = TechnicalAnalysisResponse(
            code=code,
            name=stock_info.get("name", ""),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            current_price=current_price,
            change_percent=change_percent,
            indicators=TechnicalIndicators(**indicators_dict),
            summary=summary,
            signal=signal
        )

        # 缓存结果
        get_analysis_cache().set(cache_key, response.model_dump())

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"技术分析失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=f"技术分析失败: {str(e)}")


@router.get("/fundamental/{code}", response_model=FundamentalAnalysisResponse)
async def get_fundamental_analysis(code: str):
    """
    获取股票基本面分析

    基于股票财务数据进行分析，包括估值、盈利能力、成长性等指标。

    Args:
        code: 股票代码

    Returns:
        基本面分析结果
    """
    cache_key = f"fundamental:{code}"

    # 尝试从缓存获取
    cached = get_analysis_cache().get(cache_key)
    if cached:
        return cached

    logger.info(f"执行基本面分析: {code}")

    try:
        # 获取股票服务
        service = get_stock_service()

        # 获取股票信息
        stock_info = service.get_stock_info(code)
        if stock_info is None:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")

        # 获取实时行情（包含部分基本面数据）
        quote = service.get_stock_quote(code)
        if quote is None:
            raise HTTPException(status_code=404, detail=f"未找到股票行情: {code}")

        # 构建基本面数据（从行情中获取估值指标）
        fundamental_data = FundamentalData(
            pe=quote.get("pe"),  # 市盈率
            pb=quote.get("pb"),  # 市净率
            market_cap=quote.get("total_market_cap"),  # 总市值
            float_market_cap=quote.get("float_market_cap"),  # 流通市值
            revenue=None,  # 营业收入 - 需要额外API获取
            net_profit=None,  # 净利润 - 需要额外API获取
            roe=None,  # 净资产收益率 - 需要额外API获取
            gross_margin=None,  # 毛利率 - 需要额外API获取
            debt_ratio=None,  # 资产负债率 - 需要额外API获取
            current_ratio=None  # 流动比率 - 需要额外API获取
        )

        # 生成评级
        rating = _generate_fundamental_rating(fundamental_data.model_dump(exclude_none=True))

        # 格式化摘要
        summary = _format_fundamental_summary(fundamental_data.model_dump(exclude_none=True), rating)

        # 构建响应
        response = FundamentalAnalysisResponse(
            code=code,
            name=stock_info.get("name", ""),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            market=stock_info.get("market", ""),
            industry=stock_info.get("industry"),
            fundamental_data=fundamental_data,
            summary=summary,
            rating=rating
        )

        # 缓存结果
        get_analysis_cache().set(cache_key, response.model_dump())

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"基本面分析失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=f"基本面分析失败: {str(e)}")


@router.get("/advice/{code}", response_model=InvestmentAdviceResponse)
async def get_investment_advice(code: str):
    """
    获取投资建议

    综合技术分析和基本面分析，生成投资建议。

    Args:
        code: 股票代码

    Returns:
        投资建议
    """
    cache_key = f"advice:{code}"

    # 尝试从缓存获取
    cached = get_analysis_cache().get(cache_key)
    if cached:
        return cached

    logger.info(f"生成投资建议: {code}")

    try:
        # 获取技术分析
        technical = await get_technical_analysis(code)

        # 获取基本面分析
        fundamental = await get_fundamental_analysis(code)

        # 生成投资建议
        advice_data = _generate_investment_advice(
            technical_signal=technical.signal,
            fundamental_rating=fundamental.rating,
            current_price=technical.current_price,
            change_pct=technical.change_percent
        )

        # 构建推理过程
        reasoning_parts = [
            f"技术信号: {technical.signal}",
            f"基本面评级: {fundamental.rating}",
            f"当前价格: {technical.current_price}，涨跌幅: {technical.change_percent}%"
        ]

        # 汇总摘要
        summary = f"综合技术分析和基本面分析，建议{_get_advice_text(advice_data['advice'])}。" \
                  f"目标价: {advice_data['target_price']}，止损价: {advice_data['stop_loss']}，" \
                  f"风险等级: {advice_data['risk_level']}"

        # 构建响应
        response = InvestmentAdviceResponse(
            code=code,
            name=technical.name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            advice=advice_data["advice"],
            target_price=advice_data["target_price"],
            stop_loss=advice_data["stop_loss"],
            risk_level=advice_data["risk_level"],
            reasoning="；".join(reasoning_parts),
            summary=summary
        )

        # 缓存结果
        get_analysis_cache().set(cache_key, response.model_dump())

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成投资建议失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=f"生成投资建议失败: {str(e)}")


def _get_advice_text(advice: str) -> str:
    """获取建议文本"""
    advice_map = {
        "strong_buy": "强烈买入",
        "buy": "买入",
        "hold": "持有",
        "sell": "卖出",
        "strong_sell": "强烈卖出"
    }
    return advice_map.get(advice, "持有")


@router.get("/cache/clear")
async def clear_analysis_cache():
    """
    清空分析缓存

    手动清空所有缓存的分析数据。
    """
    get_analysis_cache().clear()
    return {"message": "Analysis cache cleared successfully"}


@router.get("/")
async def analysis_root():
    """
    分析API根路由

    返回API的基本信息和使用说明。
    """
    return {
        "message": "Stock Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "technical": "/api/v1/analysis/technical/<code> - 技术分析",
            "fundamental": "/api/v1/analysis/fundamental/<code> - 基本面分析",
            "advice": "/api/v1/analysis/advice/<code> - 投资建议",
            "cache_clear": "/api/v1/analysis/cache/clear - 清空缓存"
        },
        "cache_ttl": 600
    }
