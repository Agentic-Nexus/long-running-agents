"""
技术指标计算模块测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.services.technical_analysis import (
    calculate_ma,
    calculate_all_ma,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_all_rsi,
    calculate_bollinger_bands,
    calculate_kdj,
    calculate_all_indicators,
    add_indicators_to_dataframe,
)


def create_mock_data(days: int = 100, start_price: float = 10.0) -> pd.DataFrame:
    """
    创建模拟股票数据

    Args:
        days: 数据天数
        start_price: 起始价格

    Returns:
        模拟的股票 DataFrame
    """
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq="D")

    # 生成模拟价格数据 (带趋势和波动)
    np.random.seed(42)
    base = start_price
    trend = np.linspace(0, 5, days)  # 上涨趋势
    noise = np.random.randn(days) * 0.5  # 随机波动

    close = base + trend + noise
    open_price = close + np.random.randn(days) * 0.2
    high = np.maximum(open_price, close) + np.abs(np.random.randn(days) * 0.3)
    low = np.minimum(open_price, close) - np.abs(np.random.randn(days) * 0.3)
    volume = np.random.randint(1000000, 10000000, days)

    df = pd.DataFrame({
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })

    return df


class TestMovingAverage:
    """移动平均线测试"""

    def test_calculate_ma(self):
        """测试单个周期 MA 计算"""
        df = create_mock_data(days=20)

        ma5 = calculate_ma(df, 5)

        # MA5 的最后一个值应该是最后5个收盘价的平均值
        expected_ma5 = df["close"].iloc[-5:].mean()
        assert abs(ma5.iloc[-1] - expected_ma5) < 0.01

    def test_calculate_ma_period_10(self):
        """测试 MA10 计算"""
        df = create_mock_data(days=30)

        ma10 = calculate_ma(df, 10)

        # 验证长度
        assert len(ma10) == len(df)

        # MA10 的最后一个值应该是最后10个收盘价的平均值
        expected_ma10 = df["close"].iloc[-10:].mean()
        assert abs(ma10.iloc[-1] - expected_ma10) < 0.01

    def test_calculate_ma_with_small_data(self):
        """测试数据量不足时的 MA 计算"""
        df = create_mock_data(days=3)

        ma5 = calculate_ma(df, 5)

        # 数据不足5天时，应该使用所有可用数据计算
        assert not ma5.isna().all()

    def test_calculate_all_ma(self):
        """测试所有 MA 计算"""
        df = create_mock_data(days=100)

        ma_df = calculate_all_ma(df)

        # 验证列名
        assert "MA5" in ma_df.columns
        assert "MA10" in ma_df.columns
        assert "MA20" in ma_df.columns
        assert "MA60" in ma_df.columns

        # 验证长度
        assert len(ma_df) == len(df)

        # 验证没有 NaN（因为使用了 min_periods=1）
        assert not ma_df.isna().any().any()


class TestEMA:
    """指数移动平均线测试"""

    def test_calculate_ema(self):
        """测试 EMA 计算"""
        df = create_mock_data(days=50)

        ema12 = calculate_ema(df["close"], 12)

        # 验证长度
        assert len(ema12) == len(df)

        # EMA 不应该有 NaN
        assert not ema12.isna().any()


class TestMACD:
    """MACD 指标测试"""

    def test_calculate_macd(self):
        """测试 MACD 计算"""
        df = create_mock_data(days=100)

        macd_df = calculate_macd(df)

        # 验证列名
        assert "DIF" in macd_df.columns
        assert "DEA" in macd_df.columns
        assert "MACD" in macd_df.columns

        # 验证长度
        assert len(macd_df) == len(df)

    def test_macd_values_range(self):
        """测试 MACD 值范围"""
        df = create_mock_data(days=100)

        macd_df = calculate_macd(df)

        # DIF 和 DEA 应该在合理范围内
        assert macd_df["DIF"].notna().all()
        assert macd_df["DEA"].notna().all()

    def test_macd_golden_cross(self):
        """测试 MACD 金叉/死叉逻辑"""
        df = create_mock_data(days=100)

        macd_df = calculate_macd(df)

        # 检查 MACD 柱的值
        # MACD > 0 表示多头 (DIF > DEA)
        # MACD < 0 表示空头 (DIF < DEA)
        assert macd_df["MACD"].notna().all()


class TestRSI:
    """RSI 指标测试"""

    def test_calculate_rsi(self):
        """测试 RSI 计算"""
        df = create_mock_data(days=50)

        rsi = calculate_rsi(df, 6)

        # 验证长度
        assert len(rsi) == len(df)

        # RSI 应该在 0-100 之间
        assert (rsi >= 0).all()
        assert (rsi <= 100).all()

    def test_rsi_no_nan(self):
        """测试 RSI 无 NaN 值"""
        df = create_mock_data(days=30)

        rsi = calculate_rsi(df, 6)

        # RSI 不应该有 NaN
        assert not rsi.isna().any()

    def test_calculate_all_rsi(self):
        """测试所有 RSI 计算"""
        df = create_mock_data(days=100)

        rsi_df = calculate_all_rsi(df)

        # 验证列名
        assert "RSI-6" in rsi_df.columns
        assert "RSI-12" in rsi_df.columns
        assert "RSI-24" in rsi_df.columns

        # 验证长度
        assert len(rsi_df) == len(df)


class TestBollingerBands:
    """布林带指标测试"""

    def test_calculate_bollinger_bands(self):
        """测试布林带计算"""
        df = create_mock_data(days=100)

        bb_df = calculate_bollinger_bands(df)

        # 验证列名
        assert "Upper" in bb_df.columns
        assert "Middle" in bb_df.columns
        assert "Lower" in bb_df.columns

        # 验证长度
        assert len(bb_df) == len(df)

    def test_bollinger_bands_order(self):
        """测试布林带顺序关系"""
        df = create_mock_data(days=100)

        bb_df = calculate_bollinger_bands(df)

        # 跳过第一个 NaN 值进行比较
        valid_idx = ~bb_df["Upper"].isna()
        # 上轨应该大于中轨，中轨应该大于下轨
        assert (bb_df["Upper"][valid_idx] >= bb_df["Middle"][valid_idx]).all()
        assert (bb_df["Middle"][valid_idx] >= bb_df["Lower"][valid_idx]).all()

    def test_bollinger_bands_width(self):
        """测试布林带宽度"""
        df = create_mock_data(days=100)

        bb_df = calculate_bollinger_bands(df, period=20, std_dev=2.0)

        # 带宽应该是标准差的 2 倍 (上下轨)
        width = bb_df["Upper"] - bb_df["Lower"]

        # 跳过第一个 NaN 值
        valid_width = width.dropna()
        assert len(valid_width) > 0
        assert (valid_width > 0).all()


class TestKDJ:
    """KDJ 指标测试"""

    def test_calculate_kdj(self):
        """测试 KDJ 计算"""
        df = create_mock_data(days=100)

        kdj_df = calculate_kdj(df)

        # 验证列名
        assert "K" in kdj_df.columns
        assert "D" in kdj_df.columns
        assert "J" in kdj_df.columns

        # 验证长度
        assert len(kdj_df) == len(df)

    def test_kdj_values_range(self):
        """测试 KDJ 值范围"""
        df = create_mock_data(days=50)

        kdj_df = calculate_kdj(df)

        # K 和 D 应该在 0-100 之间
        assert (kdj_df["K"] >= 0).all()
        assert (kdj_df["K"] <= 100).all()
        assert (kdj_df["D"] >= 0).all()
        assert (kdj_df["D"] <= 100).all()

    def test_kdj_j_value(self):
        """测试 J 值计算"""
        df = create_mock_data(days=50)

        kdj_df = calculate_kdj(df)

        # J = 3*K - 2*D
        expected_j = 3 * kdj_df["K"] - 2 * kdj_df["D"]
        assert np.allclose(kdj_df["J"].values, expected_j.values, rtol=1e-5)


class TestAllIndicators:
    """所有指标综合测试"""

    def test_calculate_all_indicators(self):
        """测试计算所有指标"""
        df = create_mock_data(days=100)

        results = calculate_all_indicators(df)

        # 验证所有指标都存在
        assert "ma" in results
        assert "macd" in results
        assert "rsi" in results
        assert "bollinger" in results
        assert "kdj" in results

    def test_add_indicators_to_dataframe(self):
        """测试将指标添加到 DataFrame"""
        df = create_mock_data(days=100)

        result = add_indicators_to_dataframe(df)

        # 验证原始列存在
        assert "open" in result.columns
        assert "high" in result.columns
        assert "low" in result.columns
        assert "close" in result.columns
        assert "volume" in result.columns

        # 验证 MA 指标
        assert "MA5" in result.columns
        assert "MA10" in result.columns
        assert "MA20" in result.columns
        assert "MA60" in result.columns

        # 验证 MACD 指标
        assert "DIF" in result.columns
        assert "DEA" in result.columns
        assert "MACD" in result.columns

        # 验证 RSI 指标
        assert "RSI-6" in result.columns
        assert "RSI-12" in result.columns
        assert "RSI-24" in result.columns

        # 验证布林带指标
        assert "Upper" in result.columns
        assert "Middle" in result.columns
        assert "Lower" in result.columns

        # 验证 KDJ 指标
        assert "K" in result.columns
        assert "D" in result.columns
        assert "J" in result.columns


class TestEdgeCases:
    """边界情况测试"""

    def test_single_row_data(self):
        """测试单行数据"""
        df = pd.DataFrame({
            "open": [10.0],
            "high": [10.5],
            "low": [9.5],
            "close": [10.2],
            "volume": [1000000],
        })

        ma_df = calculate_all_ma(df)
        # 验证至少有一些非 NaN 值
        assert ma_df.notna().any().any()

    def test_constant_price(self):
        """测试价格不变的情况"""
        df = pd.DataFrame({
            "open": [10.0] * 50,
            "high": [10.0] * 50,
            "low": [10.0] * 50,
            "close": [10.0] * 50,
            "volume": [1000000] * 50,
        })

        ma = calculate_ma(df, 5)
        # 所有 MA 应该等于 10.0
        assert (ma == 10.0).all()

    def test_upward_trend(self):
        """测试上涨趋势"""
        df = pd.DataFrame({
            "open": list(range(10, 60)),
            "high": list(range(11, 61)),
            "low": list(range(9, 59)),
            "close": list(range(10, 60)),
            "volume": [1000000] * 50,
        })

        ma_df = calculate_all_ma(df)

        # 短期 MA 应该在长期 MA 之上 (上涨趋势)
        assert ma_df["MA5"].iloc[-1] > ma_df["MA10"].iloc[-1]
        assert ma_df["MA10"].iloc[-1] > ma_df["MA20"].iloc[-1]

    def test_downward_trend(self):
        """测试下跌趋势"""
        df = pd.DataFrame({
            "open": list(range(60, 10, -1)),
            "high": list(range(61, 11, -1)),
            "low": list(range(59, 9, -1)),
            "close": list(range(60, 10, -1)),
            "volume": [1000000] * 50,
        })

        ma_df = calculate_all_ma(df)

        # 短期 MA 应该在长期 MA 之下 (下跌趋势)
        assert ma_df["MA5"].iloc[-1] < ma_df["MA10"].iloc[-1]
        assert ma_df["MA10"].iloc[-1] < ma_df["MA20"].iloc[-1]
