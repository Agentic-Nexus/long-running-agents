"""
K线形态识别测试

使用模拟数据进行形态识别测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.services.pattern_recognition import (
    recognize_pattern,
    detect_hammer,
    detect_hanging_man,
    detect_doji,
    detect_morning_star,
    detect_evening_star,
    detect_three_white_soldiers,
    detect_three_black_crows,
    detect_head_and_shoulders,
    detect_double_top,
    detect_double_bottom,
    analyze_volume,
    detect_trend,
    detect_gravestone_doji,
    detect_dragonfly_doji,
    detect_shooting_star,
    detect_inverted_hammer,
    Signal
)


def create_dataframe(candles):
    """创建K线DataFrame"""
    return pd.DataFrame(candles)


class TestSingleCandlePatterns:
    """单根K线形态测试"""

    def test_hammer_bullish(self):
        """测试锤子线 - 看涨信号"""
        # 下影线 >= 实体 * 2, 上影线 <= 实体 * 0.1
        # open=10, close=11, high=11.05, low=8
        # body=1, upper_shadow=0.05, lower_shadow=2
        candle = pd.Series({
            "open": 10.0,
            "high": 11.05,
            "low": 8.0,
            "close": 11.0
        })
        df = pd.DataFrame([candle])

        result = detect_hammer(df, 0)
        assert result == "hammer"

    def test_hanging_man_bearish(self):
        """测试吊颈线 - 看跌信号"""
        # 与锤子线相同逻辑，上影线要非常短
        candle = pd.Series({
            "open": 10.0,
            "high": 10.05,
            "low": 8.0,
            "close": 10.5
        })
        df = pd.DataFrame([candle])

        result = detect_hanging_man(df, 0)
        assert result == "hanging_man"

    def test_doji(self):
        """测试十字星"""
        # 实体 < 整体振幅 * 5%
        candle = pd.Series({
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "close": 10.0
        })
        df = pd.DataFrame([candle])

        result = detect_doji(df, 0)
        assert result == "doji"

    def test_gravestone_doji(self):
        """测试墓碑十字"""
        candle = pd.Series({
            "open": 10.0,
            "high": 11.0,
            "low": 10.0,
            "close": 10.0
        })
        df = pd.DataFrame([candle])

        result = detect_gravestone_doji(df, 0)
        assert result == "gravestone_doji"

    def test_dragonfly_doji(self):
        """测试蜻蜓十字"""
        candle = pd.Series({
            "open": 10.0,
            "high": 10.0,
            "low": 9.0,
            "close": 10.0
        })
        df = pd.DataFrame([candle])

        result = detect_dragonfly_doji(df, 0)
        assert result == "dragonfly_doji"

    def test_shooting_star_bearish(self):
        """测试射击之星"""
        # 上影线 >= 实体 * 2, 下影线 <= 实体 * 0.1
        # open=10, close=10.1, high=12, low=10.0
        # body=0.1, upper_shadow=1.9, lower_shadow=0.0
        candle = pd.Series({
            "open": 10.0,
            "high": 12.0,
            "low": 10.0,
            "close": 10.1
        })
        df = pd.DataFrame([candle])

        result = detect_shooting_star(df, 0)
        assert result == "shooting_star"

    def test_inverted_hammer_bullish(self):
        """测试倒锤子线"""
        candle = pd.Series({
            "open": 10.0,
            "high": 12.0,
            "low": 10.0,
            "close": 10.1
        })
        df = pd.DataFrame([candle])

        result = detect_inverted_hammer(df, 0)
        assert result == "inverted_hammer"


class TestMultiCandlePatterns:
    """多根K线形态测试"""

    def test_morning_star_bullish(self):
        """测试早晨之星"""
        c1 = {"open": 10.0, "high": 10.5, "low": 9.0, "close": 9.5, "volume": 1000000}
        c2 = {"open": 9.6, "high": 9.8, "low": 9.0, "close": 9.7, "volume": 800000}
        c3 = {"open": 9.8, "high": 10.8, "low": 9.7, "close": 10.5, "volume": 1200000}

        df = create_dataframe([c1, c2, c3])

        result = detect_morning_star(df, 2)
        assert result == "morning_star"

    def test_evening_star_bearish(self):
        """测试黄昏之星"""
        c1 = {"open": 9.5, "high": 10.5, "low": 9.0, "close": 10.0, "volume": 1000000}
        c2 = {"open": 10.1, "high": 10.3, "low": 9.5, "close": 10.2, "volume": 800000}
        c3 = {"open": 10.0, "high": 10.2, "low": 9.0, "close": 9.3, "volume": 1200000}

        df = create_dataframe([c1, c2, c3])

        result = detect_evening_star(df, 2)
        assert result == "evening_star"


class TestVolumeAnalysis:
    """成交量分析测试"""

    def test_volume_analysis(self):
        """测试成交量分析"""
        candles = []
        for i in range(25):
            candles.append({
                "open": 10.0 + i * 0.1,
                "high": 10.5 + i * 0.1,
                "low": 9.5 + i * 0.1,
                "close": 10.2 + i * 0.1,
                "volume": 1000000 + i * 50000
            })

        df = create_dataframe(candles)
        result = analyze_volume(df)

        assert "volume_trend" in result
        assert result["volume_trend"] == "increasing"


class TestTrendDetection:
    """趋势判断测试"""

    def test_uptrend(self):
        """测试上升趋势"""
        candles = []
        base_price = 10.0
        for i in range(25):
            candles.append({
                "open": base_price + i * 0.2,
                "high": base_price + i * 0.2 + 0.5,
                "low": base_price + i * 0.2 - 0.3,
                "close": base_price + i * 0.2 + 0.2,
                "volume": 1000000
            })

        df = create_dataframe(candles)
        result = detect_trend(df)

        assert result["trend"] == "uptrend"
        assert result["price_change_pct"] > 5

    def test_downtrend(self):
        """测试下降趋势"""
        candles = []
        base_price = 15.0
        for i in range(25):
            candles.append({
                "open": base_price - i * 0.2,
                "high": base_price - i * 0.2 + 0.3,
                "low": base_price - i * 0.2 - 0.5,
                "close": base_price - i * 0.2 - 0.2,
                "volume": 1000000
            })

        df = create_dataframe(candles)
        result = detect_trend(df)

        assert result["trend"] == "downtrend"
        assert result["price_change_pct"] < -5

    def test_sideways(self):
        """测试横盘整理"""
        candles = []
        for i in range(25):
            candles.append({
                "open": 10.0 + (i % 5) * 0.1,
                "high": 10.5,
                "low": 9.5,
                "close": 10.0 + (i % 5) * 0.1,
                "volume": 1000000
            })

        df = create_dataframe(candles)
        result = detect_trend(df)

        assert result["trend"] == "sideways"


class TestFullPatternRecognition:
    """完整形态识别测试"""

    def test_full_recognition_with_patterns(self):
        """测试完整识别 - 十字星"""
        candles = [
            {"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0, "volume": 1000000},
        ]

        df = create_dataframe(candles)
        result = recognize_pattern(df)

        assert "patterns" in result
        assert "volume_analysis" in result
        assert "trend_analysis" in result

    def test_full_recognition_with_trend(self):
        """测试完整识别 - 上升趋势"""
        candles = []
        base_price = 10.0
        for i in range(30):
            candles.append({
                "open": base_price + i * 0.15,
                "high": base_price + i * 0.15 + 0.5,
                "low": base_price + i * 0.15 - 0.3,
                "close": base_price + i * 0.15 + 0.2,
                "volume": 1000000 + i * 10000
            })

        df = create_dataframe(candles)
        result = recognize_pattern(df)

        assert "trend_analysis" in result
        assert result["trend_analysis"]["trend"] == "uptrend"
        assert result["summary"]["overall_signal"] in [Signal.BULLISH, Signal.NEUTRAL]

    def test_empty_dataframe(self):
        """测试空数据"""
        df = pd.DataFrame()
        result = recognize_pattern(df)

        assert result["patterns"] == []
        assert result["volume_analysis"] == {}

    def test_insufficient_data(self):
        """测试数据不足"""
        candles = [
            {"open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000},
        ]

        df = create_dataframe(candles)
        result = recognize_pattern(df)

        assert "summary" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
