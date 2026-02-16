"""
K线形态识别模块

实现K线形态识别功能：
- 基本K线形态识别 (锤子线、吊颈线、十字星等)
- 组合形态识别 (头肩顶/底、双顶/底、三角形整理等)
- 成交量分析
- 趋势判断 (上升/下降/横盘)
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)


# 信号类型
class Signal:
    BULLISH = "bullish"  # 买入/看涨
    BEARISH = "bearish"  # 卖出/看跌
    NEUTRAL = "neutral"  # 中性


def _calculate_body(candle: pd.Series) -> float:
    """计算K线实体大小"""
    return abs(candle["close"] - candle["open"])


def _calculate_upper_shadow(candle: pd.Series) -> float:
    """计算上影线长度"""
    return candle["high"] - max(candle["open"], candle["close"])


def _calculate_lower_shadow(candle: pd.Series) -> float:
    """计算下影线长度"""
    return min(candle["open"], candle["close"]) - candle["low"]


def _calculate_full_range(candle: pd.Series) -> float:
    """计算K线整体振幅"""
    return candle["high"] - candle["low"]


def _is_bullish(candle: pd.Series) -> bool:
    """判断是否阳线"""
    return candle["close"] > candle["open"]


def _is_bearish(candle: pd.Series) -> bool:
    """判断是否阴线"""
    return candle["close"] < candle["open"]


def detect_hammer(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测锤子线 (Hammer)
    特征：下影线长度是实体2倍以上，上影线很短
    出现在下降趋势中，看涨信号
    """
    if idx < 0 or idx >= len(df):
        return None

    candle = df.iloc[idx]
    body = _calculate_body(candle)
    upper_shadow = _calculate_upper_shadow(candle)
    lower_shadow = _calculate_lower_shadow(candle)

    if body == 0:
        return None

    # 锤子线条件
    if lower_shadow >= body * 2 and upper_shadow <= body * 0.1:
        return "hammer"

    return None


def detect_inverted_hammer(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测倒锤子线 (Inverted Hammer)
    特征：上影线长度是实体2倍以上，下影线很短
    出现在下降趋势中，看涨信号
    """
    if idx < 0 or idx >= len(df):
        return None

    candle = df.iloc[idx]
    body = _calculate_body(candle)
    upper_shadow = _calculate_upper_shadow(candle)
    lower_shadow = _calculate_lower_shadow(candle)

    if body == 0:
        return None

    # 倒锤子线条件
    if upper_shadow >= body * 2 and lower_shadow <= body * 0.1:
        return "inverted_hammer"

    return None


def detect_hanging_man(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测吊颈线 (Hanging Man)
    特征：下影线长度是实体2倍以上，上影线很短
    出现在上升趋势中，看跌信号
    """
    if idx < 0 or idx >= len(df):
        return None

    candle = df.iloc[idx]
    body = _calculate_body(candle)
    upper_shadow = _calculate_upper_shadow(candle)
    lower_shadow = _calculate_lower_shadow(candle)

    if body == 0:
        return None

    # 吊颈线条件
    if lower_shadow >= body * 2 and upper_shadow <= body * 0.1:
        return "hanging_man"

    return None


def detect_shooting_star(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测流星线/射击之星 (Shooting Star)
    特征：上影线长度是实体2倍以上，下影线很短
    出现在上升趋势中，看跌信号
    """
    if idx < 0 or idx >= len(df):
        return None

    candle = df.iloc[idx]
    body = _calculate_body(candle)
    upper_shadow = _calculate_upper_shadow(candle)
    lower_shadow = _calculate_lower_shadow(candle)

    if body == 0:
        return None

    # 流星线条件
    if upper_shadow >= body * 2 and lower_shadow <= body * 0.1:
        return "shooting_star"

    return None


def detect_doji(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测十字星 (Doji)
    特征：实体非常小，接近于0
    可能表示趋势反转或中继
    """
    if idx < 0 or idx >= len(df):
        return None

    candle = df.iloc[idx]
    body = _calculate_body(candle)
    full_range = _calculate_full_range(candle)

    if full_range == 0:
        return None

    # 十字星条件：实体小于整体振幅的5%
    if body / full_range < 0.05:
        # 判断影线类型
        upper_shadow = _calculate_upper_shadow(candle)
        lower_shadow = _calculate_lower_shadow(candle)

        if upper_shadow > 0 and lower_shadow > 0:
            return "doji"

    return None


def detect_gravestone_doji(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测墓碑十字 (Gravestone Doji)
    特征：开盘价等于收盘价，只有上影线
    看跌信号
    """
    if idx < 0 or idx >= len(df):
        return None

    candle = df.iloc[idx]
    body = _calculate_body(candle)
    upper_shadow = _calculate_upper_shadow(candle)
    lower_shadow = _calculate_lower_shadow(candle)

    if body == 0 and upper_shadow > 0 and lower_shadow == 0:
        return "gravestone_doji"

    return None


def detect_dragonfly_doji(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测蜻蜓十字 (Dragonfly Doji)
    特征：开盘价等于收盘价，只有下影线
    看涨信号
    """
    if idx < 0 or idx >= len(df):
        return None

    candle = df.iloc[idx]
    body = _calculate_body(candle)
    upper_shadow = _calculate_upper_shadow(candle)
    lower_shadow = _calculate_lower_shadow(candle)

    if body == 0 and lower_shadow > 0 and upper_shadow == 0:
        return "dragonfly_doji"

    return None


def detect_morning_star(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测早晨之星/晨星 (Morning Star)
    特征：三根K线：第一根下跌，第二根小幅，第三根上涨
    看涨信号
    """
    if idx < 2 or idx >= len(df):
        return None

    # 需要至少3根K线
    prev2 = df.iloc[idx - 2]
    prev1 = df.iloc[idx - 1]
    current = df.iloc[idx]

    # 第一根：下跌趋势的阴线
    if prev2["close"] >= prev2["open"]:
        return None

    # 第二根：实体在第一根实体下方的小幅波动K线
    if prev1["high"] < prev2["low"]:
        return None

    # 第三根：上涨的阳线，收盘在第一根实体50%以上
    if current["close"] <= current["open"]:
        return None

    if current["close"] > (prev2["open"] + prev2["close"]) / 2:
        return "morning_star"

    return None


def detect_evening_star(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测黄昏之星/暮星 (Evening Star)
    特征：三根K线：第一根上涨，第二根小幅，第三根下跌
    看跌信号
    """
    if idx < 2 or idx >= len(df):
        return None

    prev2 = df.iloc[idx - 2]
    prev1 = df.iloc[idx - 1]
    current = df.iloc[idx]

    # 第一根：上涨趋势的阳线
    if prev2["close"] <= prev2["open"]:
        return None

    # 第二根：实体在第一根实体上方的小幅波动K线
    if prev1["low"] > prev2["high"]:
        return None

    # 第三根：下跌的阴线，收盘在第一根实体50%以下
    if current["close"] >= current["open"]:
        return None

    if current["close"] < (prev2["open"] + prev2["close"]) / 2:
        return "evening_star"

    return None


def detect_three_white_soldiers(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测三白兵/三阳开泰 (Three White Soldiers)
    特征：三根连续上涨的阳线，实体逐渐增大
    看涨信号
    """
    if idx < 2 or idx >= len(df):
        return None

    prev2 = df.iloc[idx - 2]
    prev1 = df.iloc[idx - 1]
    current = df.iloc[idx]

    # 三根都是阳线
    if not (_is_bullish(prev2) and _is_bullish(prev1) and _is_bullish(current)):
        return None

    body2 = _calculate_body(prev2)
    body1 = _calculate_body(prev1)
    body0 = _calculate_body(current)

    # 实体逐渐增大
    if body0 > body1 > body2:
        # 每根K线收盘价高于前一根
        if current["close"] > prev1["close"] and prev1["close"] > prev2["close"]:
            # 上影线都很短
            if (_calculate_upper_shadow(prev2) < body2 * 0.3 and
                _calculate_upper_shadow(prev1) < body1 * 0.3 and
                _calculate_upper_shadow(current) < body0 * 0.3):
                return "three_white_soldiers"

    return None


def detect_three_black_crows(df: pd.DataFrame, idx: int) -> Optional[str]:
    """
    检测三黑鸦 (Three Black Crows)
    特征：三根连续下跌的阴线，实体逐渐增大
    看跌信号
    """
    if idx < 2 or idx >= len(df):
        return None

    prev2 = df.iloc[idx - 2]
    prev1 = df.iloc[idx - 1]
    current = df.iloc[idx]

    # 三根都是阴线
    if not (_is_bearish(prev2) and _is_bearish(prev1) and _is_bearish(current)):
        return None

    body2 = _calculate_body(prev2)
    body1 = _calculate_body(prev1)
    body0 = _calculate_body(current)

    # 实体逐渐增大
    if body0 > body1 > body2:
        # 每根K线收盘价低于前一根
        if current["close"] < prev1["close"] and prev1["close"] < prev2["close"]:
            # 下影线都很短
            if (_calculate_lower_shadow(prev2) < body2 * 0.3 and
                _calculate_lower_shadow(prev1) < body1 * 0.3 and
                _calculate_lower_shadow(current) < body0 * 0.3):
                return "three_black_crows"

    return None


def detect_head_and_shoulders(df: pd.DataFrame, idx: int, lookback: int = 30) -> Optional[str]:
    """
    检测头肩顶 (Head and Shoulders)
    特征：左肩、头、右肩三个峰值，头最高
    看跌信号
    """
    if idx < lookback or idx >= len(df):
        return None

    start_idx = max(0, idx - lookback)
    window = df.iloc[start_idx:idx + 1].copy()

    if len(window) < 10:
        return None

    # 简化检测：寻找局部最高点
    highs = window["high"].values
    n = len(highs)

    # 寻找三个峰值
    peaks = []
    for i in range(1, n - 1):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            peaks.append((i, highs[i]))

    if len(peaks) < 3:
        return None

    # 找到三个最高的峰值
    peaks.sort(key=lambda x: x[1], reverse=True)
    top_peaks = peaks[:3]

    if len(top_peaks) < 3:
        return None

    # 按位置排序
    top_peaks.sort(key=lambda x: x[0])

    left_shoulder, head, right_shoulder = top_peaks

    # 头部最高
    if head[1] <= left_shoulder[1] or head[1] <= right_shoulder[1]:
        return None

    # 两肩高度相近（差距在20%以内）
    shoulder_diff = abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1]
    if shoulder_diff > 0.2:
        return None

    # 头部与肩部有一定距离
    if right_shoulder[0] - head[0] < 3 or head[0] - left_shoulder[0] < 3:
        return None

    # 颈线检测（两肩的连线）
    neckline = (left_shoulder[1] + right_shoulder[1]) / 2
    last_close = window.iloc[-1]["close"]

    # 收盘价跌破颈线
    if last_close < neckline:
        return "head_and_shoulders"

    return None


def detect_inverse_head_and_shoulders(df: pd.DataFrame, idx: int, lookback: int = 30) -> Optional[str]:
    """
    检测头肩底 (Inverse Head and Shoulders)
    特征：左肩、头、右肩三个谷底，头最低
    看涨信号
    """
    if idx < lookback or idx >= len(df):
        return None

    start_idx = max(0, idx - lookback)
    window = df.iloc[start_idx:idx + 1].copy()

    if len(window) < 10:
        return None

    lows = window["low"].values
    n = len(lows)

    # 寻找三个谷底
    troughs = []
    for i in range(1, n - 1):
        if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            troughs.append((i, lows[i]))

    if len(troughs) < 3:
        return None

    # 找到三个最低的谷底
    troughs.sort(key=lambda x: x[1])
    bottom_troughs = troughs[:3]

    if len(bottom_troughs) < 3:
        return None

    # 按位置排序
    bottom_troughs.sort(key=lambda x: x[0])

    left_shoulder, head, right_shoulder = bottom_troughs

    # 头部最低
    if head[1] >= left_shoulder[1] or head[1] >= right_shoulder[1]:
        return None

    # 两肩高度相近
    shoulder_diff = abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1]
    if shoulder_diff > 0.2:
        return None

    # 头部与肩部有一定距离
    if right_shoulder[0] - head[0] < 3 or head[0] - left_shoulder[0] < 3:
        return None

    # 颈线检测
    neckline = (left_shoulder[1] + right_shoulder[1]) / 2
    last_close = window.iloc[-1]["close"]

    # 收盘价突破颈线
    if last_close > neckline:
        return "inverse_head_and_shoulders"

    return None


def detect_double_top(df: pd.DataFrame, idx: int, lookback: int = 30) -> Optional[str]:
    """
    检测双顶 (Double Top)
    特征：两个相近的高点，中间有一个谷底
    看跌信号
    """
    if idx < lookback or idx >= len(df):
        return None

    start_idx = max(0, idx - lookback)
    window = df.iloc[start_idx:idx + 1].copy()

    if len(window) < 10:
        return None

    highs = window["high"].values
    n = len(highs)

    # 寻找两个局部最高点
    peaks = []
    for i in range(1, n - 1):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            peaks.append((i, highs[i]))

    if len(peaks) < 2:
        return None

    # 找到两个最高的峰值
    peaks.sort(key=lambda x: x[1], reverse=True)
    top_peaks = peaks[:2]

    if len(top_peaks) < 2:
        return None

    # 按位置排序
    top_peaks.sort(key=lambda x: x[0])

    peak1, peak2 = top_peaks

    # 两个峰值高度相近（差距在3%以内）
    height_diff = abs(peak1[1] - peak2[1]) / peak1[1]
    if height_diff > 0.03:
        return None

    # 两个峰值之间有一定距离
    if peak2[0] - peak1[0] < 5:
        return None

    # 找到两峰之间的最低点
    middle_section = window.iloc[peak1[0]:peak2[0] + 1]
    middle_low = middle_section["low"].min()

    # 收盘价跌破中间谷底
    last_close = window.iloc[-1]["close"]
    if last_close < middle_low:
        return "double_top"

    return None


def detect_double_bottom(df: pd.DataFrame, idx: int, lookback: int = 30) -> Optional[str]:
    """
    检测双底 (Double Bottom)
    特征：两个相近的低点，中间有一个峰顶
    看涨信号
    """
    if idx < lookback or idx >= len(df):
        return None

    start_idx = max(0, idx - lookback)
    window = df.iloc[start_idx:idx + 1].copy()

    if len(window) < 10:
        return None

    lows = window["low"].values
    n = len(lows)

    # 寻找两个局部最低点
    troughs = []
    for i in range(1, n - 1):
        if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            troughs.append((i, lows[i]))

    if len(troughs) < 2:
        return None

    # 找到两个最低的谷底
    troughs.sort(key=lambda x: x[1])
    bottom_troughs = troughs[:2]

    if len(bottom_troughs) < 2:
        return None

    # 按位置排序
    bottom_troughs.sort(key=lambda x: x[0])

    trough1, trough2 = bottom_troughs

    # 两个谷底高度相近（差距在3%以内）
    depth_diff = abs(trough1[1] - trough2[1]) / trough1[1]
    if depth_diff > 0.03:
        return None

    # 两个谷底之间有一定距离
    if trough2[0] - trough1[0] < 5:
        return None

    # 找到两谷之间的最高点
    middle_section = window.iloc[trough1[0]:trough2[0] + 1]
    middle_high = middle_section["high"].max()

    # 收盘价突破中间峰顶
    last_close = window.iloc[-1]["close"]
    if last_close > middle_high:
        return "double_bottom"

    return None


def detect_triangle(df: pd.DataFrame, idx: int, lookback: int = 20) -> Optional[str]:
    """
    检测三角形整理形态
    - 对称三角形：高点逐渐降低，低点逐渐抬高
    - 上升三角形：高点接近水平，低点逐渐抬高
    - 下降三角形：高点逐渐降低，低点接近水平
    """
    if idx < lookback or idx >= len(df):
        return None

    start_idx = max(0, idx - lookback)
    window = df.iloc[start_idx:idx + 1].copy()

    if len(window) < 10:
        return None

    highs = window["high"].values
    lows = window["low"].values

    # 简化的三角形检测
    # 计算趋势线
    high_slope = (highs[-1] - highs[0]) / len(highs)
    low_slope = (lows[-1] - lows[0]) / len(lows)

    # 对称三角形：高点和低点都向中点收敛
    if high_slope < 0 and low_slope > 0:
        return "symmetrical_triangle"

    # 上升三角形：低点抬高，高点水平
    if low_slope > 0 and abs(high_slope) < 0.01:
        return "ascending_triangle"

    # 下降三角形：高点降低，低点水平
    if high_slope < 0 and abs(low_slope) < 0.01:
        return "descending_triangle"

    return None


def analyze_volume(df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
    """
    成交量分析

    Args:
        df: 包含 volume 列的 DataFrame
        period: 分析周期

    Returns:
        成交量分析结果
    """
    if "volume" not in df.columns or len(df) < period:
        return {
            "avg_volume": 0,
            "volume_ratio": 1.0,
            "volume_trend": "neutral"
        }

    recent_volume = df["volume"].iloc[-period:]
    avg_volume = recent_volume.mean()
    current_volume = df["volume"].iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

    # 判断成交量趋势
    if len(df) >= 5:
        volume_ma5 = df["volume"].rolling(window=5, min_periods=1).mean().iloc[-1]
        volume_ma20 = df["volume"].rolling(window=20, min_periods=1).mean().iloc[-1]

        if volume_ma5 > volume_ma20:
            volume_trend = "increasing"
        elif volume_ma5 < volume_ma20:
            volume_trend = "decreasing"
        else:
            volume_trend = "stable"
    else:
        volume_trend = "stable"

    # 判断量价配合
    price_change = df["close"].iloc[-1] - df["close"].iloc[-2] if len(df) >= 2 else 0

    if price_change > 0 and volume_ratio > 1.2:
        volume_price = "bullish"  # 价涨量增，看涨
    elif price_change > 0 and volume_ratio < 0.8:
        volume_price = "bearish"  # 价涨量跌，量价背离
    elif price_change < 0 and volume_ratio > 1.2:
        volume_price = "bearish"  # 价跌量增，看跌
    elif price_change < 0 and volume_ratio < 0.8:
        volume_price = "bullish"  # 价跌量缩，可能见底
    else:
        volume_price = "neutral"

    return {
        "avg_volume": float(avg_volume),
        "current_volume": float(current_volume),
        "volume_ratio": float(volume_ratio),
        "volume_trend": volume_trend,
        "volume_price_analysis": volume_price
    }


def detect_trend(df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
    """
    趋势判断

    Args:
        df: 包含 close, high, low 列的 DataFrame
        period: 分析周期

    Returns:
        趋势分析结果
    """
    if len(df) < period:
        return {
            "trend": "neutral",
            "strength": 0.0,
            "support": 0.0,
            "resistance": 0.0
        }

    recent = df.iloc[-period:]

    # 计算移动平均线
    ma5 = df["close"].rolling(window=5, min_periods=1).mean().iloc[-1]
    ma20 = df["close"].rolling(window=20, min_periods=1).mean().iloc[-1]
    ma60 = df["close"].rolling(window=60, min_periods=1).mean().iloc[-1] if len(df) >= 60 else ma20

    # 判断趋势方向
    close_mean = recent["close"].mean()
    close_first = recent["close"].iloc[0]
    close_last = recent["close"].iloc[-1]

    price_change_pct = (close_last - close_first) / close_first * 100 if close_first != 0 else 0

    if price_change_pct > 5:
        trend = "uptrend"
    elif price_change_pct < -5:
        trend = "downtrend"
    else:
        trend = "sideways"

    # 判断趋势强度 (使用R平方)
    x = np.arange(len(recent))
    y = recent["close"].values
    correlation = np.corrcoef(x, y)[0, 1]
    strength = abs(correlation) if not np.isnan(correlation) else 0.0

    # 计算支撑位和阻力位
    support = recent["low"].min()
    resistance = recent["high"].max()

    # 均线支撑/阻力
    current_price = df["close"].iloc[-1]

    if current_price > ma20:
        ma_support = ma20
    else:
        ma_support = ma20 * 0.95  # 跌破均线，给予一定折扣

    if current_price < ma20:
        ma_resistance = ma20
    else:
        ma_resistance = ma20 * 1.05

    return {
        "trend": trend,
        "strength": float(strength),
        "price_change_pct": float(price_change_pct),
        "support": float(support),
        "resistance": float(resistance),
        "ma_support": float(ma_support),
        "ma_resistance": float(ma_resistance),
        "ma5": float(ma5),
        "ma20": float(ma20),
        "ma60": float(ma60)
    }


def detect_all_candle_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    检测所有基本K线形态

    Args:
        df: 包含 open, high, low, close 列的 DataFrame

    Returns:
        检测到的形态列表
    """
    patterns = []

    # 单根K线形态检测器
    single_patterns = [
        ("hammer", detect_hammer, Signal.BULLISH),
        ("inverted_hammer", detect_inverted_hammer, Signal.BULLISH),
        ("hanging_man", detect_hanging_man, Signal.BEARISH),
        ("shooting_star", detect_shooting_star, Signal.BEARISH),
        ("doji", detect_doji, Signal.NEUTRAL),
        ("gravestone_doji", detect_gravestone_doji, Signal.BEARISH),
        ("dragonfly_doji", detect_dragonfly_doji, Signal.BULLISH),
    ]

    # 多根K线形态检测器
    multi_patterns = [
        ("morning_star", detect_morning_star, Signal.BULLISH),
        ("evening_star", detect_evening_star, Signal.BEARISH),
        ("three_white_soldiers", detect_three_white_soldiers, Signal.BULLISH),
        ("three_black_crows", detect_three_black_crows, Signal.BEARISH),
    ]

    # 组合形态检测器
    complex_patterns = [
        ("head_and_shoulders", detect_head_and_shoulders, Signal.BEARISH),
        ("inverse_head_and_shoulders", detect_inverse_head_and_shoulders, Signal.BULLISH),
        ("double_top", detect_double_top, Signal.BEARISH),
        ("double_bottom", detect_double_bottom, Signal.BULLISH),
        ("symmetrical_triangle", lambda df, idx: detect_triangle(df, idx), Signal.NEUTRAL),
    ]

    # 检测每根K线
    for idx in range(len(df)):
        # 单根K线形态
        for pattern_name, detector, signal in single_patterns:
            result = detector(df, idx)
            if result:
                patterns.append({
                    "name": result,
                    "signal": signal,
                    "index": idx,
                    "type": "single"
                })

        # 多根K线形态
        if idx >= 2:
            for pattern_name, detector, signal in multi_patterns:
                result = detector(df, idx)
                if result:
                    patterns.append({
                        "name": result,
                        "signal": signal,
                        "index": idx,
                        "type": "multi"
                    })

        # 组合形态 (只检测最近的数据点)
        if idx >= 10:
            for pattern_name, detector, signal in complex_patterns:
                result = detector(df, idx)
                if result:
                    # 避免重复添加
                    if not any(p["name"] == result for p in patterns):
                        patterns.append({
                            "name": result,
                            "signal": signal,
                            "index": idx,
                            "type": "complex"
                        })

    return patterns


def recognize_pattern(df: pd.DataFrame) -> Dict[str, Any]:
    """
    完整的K线形态识别

    Args:
        df: 包含 open, high, low, close, volume 列的 DataFrame

    Returns:
        形态识别结果
    """
    if df is None or len(df) < 5:
        return {
            "patterns": [],
            "volume_analysis": {},
            "trend_analysis": {},
            "summary": {
                "bullish_signals": [],
                "bearish_signals": [],
                "neutral_signals": []
            }
        }

    logger.info(f"开始K线形态识别，数据长度: {len(df)}")

    # 1. 检测K线形态
    patterns = detect_all_candle_patterns(df)

    # 2. 成交量分析
    volume_analysis = analyze_volume(df)

    # 3. 趋势判断
    trend_analysis = detect_trend(df)

    # 4. 汇总信号
    bullish_signals = []
    bearish_signals = []
    neutral_signals = []

    for pattern in patterns:
        if pattern["signal"] == Signal.BULLISH:
            bullish_signals.append(pattern["name"])
        elif pattern["signal"] == Signal.BEARISH:
            bearish_signals.append(pattern["name"])
        else:
            neutral_signals.append(pattern["name"])

    # 添加成交量分析信号
    if volume_analysis.get("volume_price_analysis") == "bullish":
        bullish_signals.append("volume_bullish")
    elif volume_analysis.get("volume_price_analysis") == "bearish":
        bearish_signals.append("volume_bearish")

    # 添加趋势信号
    if trend_analysis.get("trend") == "uptrend":
        bullish_signals.append("uptrend")
    elif trend_analysis.get("trend") == "downtrend":
        bearish_signals.append("downtrend")

    # 去重
    bullish_signals = list(set(bullish_signals))
    bearish_signals = list(set(bearish_signals))
    neutral_signals = list(set(neutral_signals))

    result = {
        "patterns": patterns,
        "volume_analysis": volume_analysis,
        "trend_analysis": trend_analysis,
        "summary": {
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "neutral_signals": neutral_signals,
            "overall_signal": _determine_overall_signal(
                bullish_signals, bearish_signals, neutral_signals
            )
        }
    }

    logger.info(f"K线形态识别完成，发现 {len(patterns)} 个形态")

    return result


def _determine_overall_signal(
    bullish: List[str],
    bearish: List[str],
    neutral: List[str]
) -> str:
    """综合判断整体信号"""
    bullish_count = len(bullish)
    bearish_count = len(bearish)

    if bullish_count > bearish_count + 1:
        return Signal.BULLISH
    elif bearish_count > bullish_count + 1:
        return Signal.BEARISH
    elif bullish_count > 0 and bearish_count == 0:
        return Signal.BULLISH
    elif bearish_count > 0 and bullish_count == 0:
        return Signal.BEARISH
    else:
        return Signal.NEUTRAL
