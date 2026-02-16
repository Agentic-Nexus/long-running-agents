"""
技术指标计算模块

实现常用的股票技术指标计算：
- 移动平均线 (MA5, MA10, MA20, MA60)
- MACD 指标 (DIF, DEA, MACD柱)
- RSI 指标 (RSI-6, RSI-12, RSI-24)
- 布林带指标 (Upper, Middle, Lower)
- KDJ 指标 (K, D, J)
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_ma(df: pd.DataFrame, period: int) -> pd.Series:
    """
    计算移动平均线 (Moving Average)

    Args:
        df: 包含 close 列的 DataFrame
        period: 移动平均周期

    Returns:
        移动平均线 Series
    """
    return df["close"].rolling(window=period, min_periods=1).mean()


def calculate_all_ma(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有常用移动平均线 (MA5, MA10, MA20, MA60)

    Args:
        df: 包含 close 列的 DataFrame

    Returns:
        包含 MA5, MA10, MA20, MA60 的 DataFrame
    """
    result = pd.DataFrame(index=df.index)
    result["MA5"] = calculate_ma(df, 5)
    result["MA10"] = calculate_ma(df, 10)
    result["MA20"] = calculate_ma(df, 20)
    result["MA60"] = calculate_ma(df, 60)
    return result


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    计算指数移动平均线 (Exponential Moving Average)

    Args:
        series: 数据序列
        period: 周期

    Returns:
        EMA Series
    """
    return series.ewm(span=period, adjust=False, min_periods=1).mean()


def calculate_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> pd.DataFrame:
    """
    计算 MACD 指标

    Args:
        df: 包含 close 列的 DataFrame
        fast_period: 快线周期，默认 12
        slow_period: 慢线周期，默认 26
        signal_period: 信号线周期，默认 9

    Returns:
        包含 DIF, DEA, MACD (柱状图) 的 DataFrame
    """
    # 计算快速和慢速 EMA
    ema_fast = calculate_ema(df["close"], fast_period)
    ema_slow = calculate_ema(df["close"], slow_period)

    # DIF = 快速EMA - 慢速EMA
    dif = ema_fast - ema_slow

    # DEA = DIF 的 EMA (信号线)
    dea = calculate_ema(dif, signal_period)

    # MACD柱 = (DIF - DEA) * 2
    macd_hist = (dif - dea) * 2

    result = pd.DataFrame(index=df.index)
    result["DIF"] = dif
    result["DEA"] = dea
    result["MACD"] = macd_hist

    return result


def calculate_rsi(df: pd.DataFrame, period: int = 6) -> pd.Series:
    """
    计算 RSI 指标 (Relative Strength Index)

    Args:
        df: 包含 close 列的 DataFrame
        period: RSI 周期，默认 6

    Returns:
        RSI Series
    """
    # 计算价格变化
    delta = df["close"].diff()

    # 分离上涨和下跌
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # 计算平均上涨和下跌 (使用 EMA)
    avg_gain = gain.ewm(span=period, adjust=False, min_periods=1).mean()
    avg_loss = loss.ewm(span=period, adjust=False, min_periods=1).mean()

    # 计算相对强度
    rs = avg_gain / avg_loss

    # 计算 RSI
    rsi = 100 - (100 / (1 + rs))

    # 处理无穷大和 NaN
    rsi = rsi.replace([np.inf, -np.inf], np.nan).fillna(50)

    return rsi


def calculate_all_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有常用 RSI 指标 (RSI-6, RSI-12, RSI-24)

    Args:
        df: 包含 close 列的 DataFrame

    Returns:
        包含 RSI-6, RSI-12, RSI-24 的 DataFrame
    """
    result = pd.DataFrame(index=df.index)
    result["RSI-6"] = calculate_rsi(df, 6)
    result["RSI-12"] = calculate_rsi(df, 12)
    result["RSI-24"] = calculate_rsi(df, 24)
    return result


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0
) -> pd.DataFrame:
    """
    计算布林带指标 (Bollinger Bands)

    Args:
        df: 包含 close 列的 DataFrame
        period: 移动平均周期，默认 20
        std_dev: 标准差倍数，默认 2.0

    Returns:
        包含 Upper, Middle, Lower 的 DataFrame
    """
    # 中轨 = MA(close, period)
    middle = df["close"].rolling(window=period, min_periods=1).mean()

    # 标准差
    std = df["close"].rolling(window=period, min_periods=1).std()

    # 上轨 = Middle + std_dev * std
    upper = middle + std_dev * std

    # 下轨 = Middle - std_dev * std
    lower = middle - std_dev * std

    result = pd.DataFrame(index=df.index)
    result["Upper"] = upper
    result["Middle"] = middle
    result["Lower"] = lower

    return result


def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """
    计算 KDJ 随机指标

    Args:
        df: 包含 high, low, close 列的 DataFrame
        n: RSV 周期，默认 9
        m1: K 值的平滑因子，默认 3
        m2: D 值的平滑因子，默认 3

    Returns:
        包含 K, D, J 的 DataFrame
    """
    # 计算 n 日 RSV (Raw Stochastic Value)
    low_n = df["low"].rolling(window=n, min_periods=1).min()
    high_n = df["high"].rolling(window=n, min_periods=1).max()

    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    rsv = rsv.replace([np.inf, -np.inf], 50).fillna(50)

    # 计算 K, D, J
    # K = (m1-1)/m1 * 前一日K + 1/m1 * RSV
    # D = (m2-1)/m2 * 前一日D + 1/m2 * K
    # J = 3*K - 2*D

    k = pd.Series(index=df.index, dtype=float)
    d = pd.Series(index=df.index, dtype=float)

    # 初始化
    k.iloc[0] = 50
    d.iloc[0] = 50

    # 递归计算 K 和 D
    for i in range(1, len(df)):
        k.iloc[i] = (m1 - 1) / m1 * k.iloc[i - 1] + 1 / m1 * rsv.iloc[i]
        d.iloc[i] = (m2 - 1) / m2 * d.iloc[i - 1] + 1 / m2 * k.iloc[i]

    # J = 3*K - 2*D
    j = 3 * k - 2 * d

    result = pd.DataFrame(index=df.index)
    result["K"] = k
    result["D"] = d
    result["J"] = j

    return result


def calculate_all_indicators(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    计算所有技术指标

    Args:
        df: 包含 open, high, low, close, volume 列的 DataFrame

    Returns:
        包含所有技术指标的字典
    """
    logger.info("开始计算技术指标...")

    results = {
        "ma": calculate_all_ma(df),
        "macd": calculate_macd(df),
        "rsi": calculate_all_rsi(df),
        "bollinger": calculate_bollinger_bands(df),
        "kdj": calculate_kdj(df),
    }

    logger.info("技术指标计算完成")

    return results


def add_indicators_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    将所有技术指标添加到原始 DataFrame

    Args:
        df: 包含 open, high, low, close, volume 列的 DataFrame

    Returns:
        包含所有技术指标的 DataFrame
    """
    # 创建副本避免修改原数据
    result = df.copy()

    # 添加 MA 指标
    ma_df = calculate_all_ma(df)
    for col in ma_df.columns:
        result[col] = ma_df[col]

    # 添加 MACD 指标
    macd_df = calculate_macd(df)
    for col in macd_df.columns:
        result[col] = macd_df[col]

    # 添加 RSI 指标
    rsi_df = calculate_all_rsi(df)
    for col in rsi_df.columns:
        result[col] = rsi_df[col]

    # 添加布林带指标
    bb_df = calculate_bollinger_bands(df)
    for col in bb_df.columns:
        result[col] = bb_df[col]

    # 添加 KDJ 指标
    kdj_df = calculate_kdj(df)
    for col in kdj_df.columns:
        result[col] = kdj_df[col]

    return result
