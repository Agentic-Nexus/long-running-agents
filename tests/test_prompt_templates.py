"""
股票分析 Prompt 模板测试用例

测试 Prompt 模板功能：
- 系统提示词测试
- 技术分析提示生成测试
- 基本面分析提示生成测试
- 投资建议提示生成测试
- 综合分析提示生成测试
- PromptTemplateBuilder 构建器测试
"""

import pytest
from typing import Dict, List, Any, Optional

from app.services.prompt_templates import (
    PromptTemplate,
    PromptTemplateBuilder,
    StockAnalysisContext,
    AnalysisType,
    create_stock_analysis_prompt,
)


class TestSystemPrompt:
    """系统提示词测试"""

    def test_get_system_prompt_not_empty(self):
        """测试系统提示词不为空"""
        prompt = PromptTemplate.get_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0

    def test_get_system_prompt_contains_key_elements(self):
        """测试系统提示词包含关键元素"""
        prompt = PromptTemplate.get_system_prompt()

        # 检查核心原则
        assert "客观分析" in prompt
        assert "风险提示" in prompt
        assert "数据驱动" in prompt
        assert "结构化输出" in prompt

        # 检查分析框架
        assert "技术面分析" in prompt
        assert "基本面分析" in prompt
        assert "综合研判" in prompt

        # 检查重要声明
        assert "不构成投资建议" in prompt
        assert "投资有风险" in prompt


class TestTechnicalAnalysisPrompt:
    """技术分析提示词测试"""

    @pytest.fixture
    def sample_kline_data(self) -> List[Dict[str, Any]]:
        """示例K线数据"""
        return [
            {"date": "2024-01-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000},
            {"date": "2024-01-02", "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.5, "volume": 1200000},
            {"date": "2024-01-03", "open": 10.5, "high": 11.0, "low": 10.3, "close": 10.8, "volume": 1500000},
        ]

    @pytest.fixture
    def sample_technical_indicators(self) -> Dict[str, Any]:
        """示例技术指标"""
        return {
            "ma5": 10.5,
            "ma10": 10.3,
            "ma20": 10.0,
            "ma60": 9.5,
            "macd_dif": 0.5,
            "macd_dea": 0.3,
            "macd_histogram": 0.2,
            "rsi6": 70.5,
            "rsi12": 65.0,
            "rsi24": 60.0,
            "kdj_k": 75.0,
            "kdj_d": 70.0,
            "kdj_j": 85.0,
            "boll_upper": 11.5,
            "boll_mid": 10.5,
            "boll_lower": 9.5,
        }

    def test_get_technical_analysis_prompt_basic(self):
        """测试技术分析提示词基本功能"""
        context = StockAnalysisContext(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=2.5,
            analysis_type=AnalysisType.TECHNICAL,
        )

        prompt = PromptTemplate.get_technical_analysis_prompt(context)

        assert prompt is not None
        assert len(prompt) > 0
        assert "000001" in prompt
        assert "平安银行" in prompt
        assert "10.5" in prompt

    def test_get_technical_analysis_prompt_with_kline(self, sample_kline_data):
        """测试带K线数据的技术分析提示词"""
        context = StockAnalysisContext(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=2.5,
            analysis_type=AnalysisType.TECHNICAL,
            kline_data=sample_kline_data,
        )

        prompt = PromptTemplate.get_technical_analysis_prompt(context)

        assert "K线数据" in prompt or "kline" in prompt.lower()
        assert "2024-01-01" in prompt
        assert "2024-01-03" in prompt

    def test_get_technical_analysis_prompt_with_indicators(self, sample_technical_indicators):
        """测试带技术指标的技术分析提示词"""
        context = StockAnalysisContext(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=2.5,
            analysis_type=AnalysisType.TECHNICAL,
            technical_indicators=sample_technical_indicators,
        )

        prompt = PromptTemplate.get_technical_analysis_prompt(context)

        assert "MA" in prompt
        assert "MACD" in prompt
        assert "RSI" in prompt
        assert "KDJ" in prompt
        assert "布林带" in prompt or "BOLL" in prompt

    def test_get_technical_analysis_prompt_structure(self):
        """测试技术分析提示词包含正确的结构"""
        context = StockAnalysisContext(
            stock_code="600000",
            stock_name="浦发银行",
            current_price=8.0,
            change_percent=-1.2,
            analysis_type=AnalysisType.TECHNICAL,
        )

        prompt = PromptTemplate.get_technical_analysis_prompt(context)

        # 检查分析要求
        assert "趋势分析" in prompt
        assert "均线分析" in prompt
        assert "MACD分析" in prompt
        assert "RSI分析" in prompt
        assert "KDJ分析" in prompt
        assert "成交量分析" in prompt

        # 检查输出格式
        assert "趋势判断" in prompt
        assert "支撑位" in prompt
        assert "压力位" in prompt
        assert "风险提示" in prompt


class TestFundamentalAnalysisPrompt:
    """基本面分析提示词测试"""

    @pytest.fixture
    def sample_stock_info(self) -> Dict[str, Any]:
        """示例股票基本信息"""
        return {
            "code": "600519",
            "name": "贵州茅台",
            "industry": "白酒",
            "listing_date": "2001-08-27",
            "total_shares": 97000,
            "circulating_shares": 97000,
            "market": "上海证券交易所",
        }

    def test_get_fundamental_analysis_prompt_basic(self):
        """测试基本面分析提示词基本功能"""
        context = StockAnalysisContext(
            stock_code="600519",
            stock_name="贵州茅台",
            current_price=1800.0,
            change_percent=1.5,
            analysis_type=AnalysisType.FUNDAMENTAL,
        )

        prompt = PromptTemplate.get_fundamental_analysis_prompt(context)

        assert prompt is not None
        assert len(prompt) > 0
        assert "600519" in prompt
        assert "贵州茅台" in prompt

    def test_get_fundamental_analysis_prompt_with_stock_info(self, sample_stock_info):
        """测试带股票信息的基本面分析提示词"""
        context = StockAnalysisContext(
            stock_code="600519",
            stock_name="贵州茅台",
            current_price=1800.0,
            change_percent=1.5,
            analysis_type=AnalysisType.FUNDAMENTAL,
            stock_info=sample_stock_info,
        )

        prompt = PromptTemplate.get_fundamental_analysis_prompt(context)

        assert "白酒" in prompt
        assert "2001-08-27" in prompt
        assert "上海证券交易所" in prompt

    def test_get_fundamental_analysis_prompt_structure(self):
        """测试基本面分析提示词包含正确的结构"""
        context = StockAnalysisContext(
            stock_code="000858",
            stock_name="五粮液",
            current_price=150.0,
            change_percent=0.8,
            analysis_type=AnalysisType.FUNDAMENTAL,
        )

        prompt = PromptTemplate.get_fundamental_analysis_prompt(context)

        # 检查分析要求
        assert "行业分析" in prompt
        assert "估值分析" in prompt
        assert "财务分析" in prompt
        assert "股本结构" in prompt
        assert "分红送转" in prompt
        assert "风险因素" in prompt

        # 检查输出格式
        assert "公司概况" in prompt
        assert "风险提示" in prompt


class TestInvestmentAdvicePrompt:
    """投资建议提示词测试"""

    def test_get_investment_advice_prompt_basic(self):
        """测试投资建议提示词基本功能"""
        context = StockAnalysisContext(
            stock_code="300750",
            stock_name="宁德时代",
            current_price=200.0,
            change_percent=3.5,
            analysis_type=AnalysisType.INVESTMENT_ADVICE,
        )

        prompt = PromptTemplate.get_investment_advice_prompt(context)

        assert prompt is not None
        assert len(prompt) > 0
        assert "300750" in prompt
        assert "宁德时代" in prompt

    def test_get_investment_advice_prompt_structure(self):
        """测试投资建议提示词包含正确的结构"""
        context = StockAnalysisContext(
            stock_code="601318",
            stock_name="中国平安",
            current_price=50.0,
            change_percent=-0.5,
            analysis_type=AnalysisType.INVESTMENT_ADVICE,
        )

        prompt = PromptTemplate.get_investment_advice_prompt(context)

        # 检查分析要求
        assert "行情研判" in prompt
        assert "操作建议" in prompt
        assert "仓位建议" in prompt
        assert "风险评估" in prompt
        assert "持有周期" in prompt

        # 检查输出格式
        assert "短期" in prompt
        assert "中期" in prompt
        assert "长期" in prompt
        assert "风险等级" in prompt

    def test_get_investment_advice_prompt_with_extra_context(self):
        """测试带额外上下文的投资建议提示词"""
        extra_context = "近期市场情绪较好，北向资金持续流入"

        context = StockAnalysisContext(
            stock_code="000333",
            stock_name="美的集团",
            current_price=60.0,
            change_percent=2.0,
            analysis_type=AnalysisType.INVESTMENT_ADVICE,
            extra_context=extra_context,
        )

        prompt = PromptTemplate.get_investment_advice_prompt(context)

        assert extra_context in prompt


class TestComprehensiveAnalysisPrompt:
    """综合分析提示词测试"""

    @pytest.fixture
    def sample_context_data(self) -> StockAnalysisContext:
        """示例完整上下文"""
        kline_data = [
            {"date": "2024-01-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000},
        ]
        stock_info = {
            "code": "000001",
            "name": "平安银行",
            "industry": "银行",
            "market": "深圳证券交易所",
        }
        technical_indicators = {
            "ma5": 10.5,
            "ma10": 10.3,
            "macd_dif": 0.5,
            "rsi6": 65.0,
        }

        return StockAnalysisContext(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=2.0,
            analysis_type=AnalysisType.COMPREHENSIVE,
            kline_data=kline_data,
            stock_info=stock_info,
            technical_indicators=technical_indicators,
        )

    def test_get_comprehensive_analysis_prompt(self, sample_context_data):
        """测试综合分析提示词"""
        prompt = PromptTemplate.get_comprehensive_analysis_prompt(sample_context_data)

        assert prompt is not None
        assert len(prompt) > 0

        # 应该包含技术分析和基本面分析的内容
        assert "趋势分析" in prompt
        assert "行业分析" in prompt

        # 应该包含综合分析部分
        assert "综合研判" in prompt
        assert "综合评分" in prompt


class TestPromptTemplateGenerate:
    """Prompt模板生成测试"""

    def test_generate_technical_prompt(self):
        """测试生成技术分析Prompt"""
        context = StockAnalysisContext(
            stock_code="600000",
            stock_name="浦发银行",
            current_price=8.0,
            change_percent=1.0,
            analysis_type=AnalysisType.TECHNICAL,
        )

        prompt = PromptTemplate.generate_prompt(context)

        assert prompt is not None
        # 应该包含系统提示词
        assert "股票分析师" in prompt or "分析" in prompt

    def test_generate_fundamental_prompt(self):
        """测试生成基本面分析Prompt"""
        context = StockAnalysisContext(
            stock_code="600519",
            stock_name="贵州茅台",
            current_price=1800.0,
            change_percent=2.0,
            analysis_type=AnalysisType.FUNDAMENTAL,
        )

        prompt = PromptTemplate.generate_prompt(context)

        assert prompt is not None

    def test_generate_comprehensive_prompt(self):
        """测试生成综合分析Prompt"""
        context = StockAnalysisContext(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=1.5,
            analysis_type=AnalysisType.COMPREHENSIVE,
        )

        prompt = PromptTemplate.generate_prompt(context)

        assert prompt is not None


class TestPromptTemplateBuilder:
    """Prompt模板构建器测试"""

    def test_builder_basic(self):
        """测试构建器基本功能"""
        builder = PromptTemplateBuilder()
        prompt = builder.set_stock("000001", "平安银行", 10.5, 2.0).build()

        assert prompt is not None
        assert "000001" in prompt
        assert "平安银行" in prompt
        assert "10.5" in prompt

    def test_builder_with_analysis_type(self):
        """测试构建器设置分析类型"""
        builder = PromptTemplateBuilder()
        prompt = (
            builder
            .set_stock("600519", "贵州茅台", 1800.0, 1.0)
            .set_analysis_type(AnalysisType.FUNDAMENTAL)
            .build()
        )

        assert "基本面" in prompt or "FUNDAMENTAL" in prompt or "fundamental" in prompt.lower()

    def test_builder_with_kline_data(self):
        """测试构建器设置K线数据"""
        kline_data = [
            {"date": "2024-01-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000},
        ]

        builder = PromptTemplateBuilder()
        prompt = (
            builder
            .set_stock("000001", "平安银行", 10.5, 2.0)
            .set_kline_data(kline_data)
            .build()
        )

        assert "2024-01-01" in prompt

    def test_builder_with_technical_indicators(self):
        """测试构建器设置技术指标"""
        indicators = {
            "ma5": 10.5,
            "ma10": 10.3,
            "macd_dif": 0.5,
        }

        builder = PromptTemplateBuilder()
        prompt = (
            builder
            .set_stock("000001", "平安银行", 10.5, 2.0)
            .set_technical_indicators(indicators)
            .build()
        )

        assert "MA" in prompt or "ma" in prompt.lower()

    def test_builder_with_stock_info(self):
        """测试构建器设置股票信息"""
        stock_info = {
            "code": "600519",
            "name": "贵州茅台",
            "industry": "白酒",
        }

        builder = PromptTemplateBuilder()
        prompt = (
            builder
            .set_stock("600519", "贵州茅台", 1800.0, 1.0)
            .set_stock_info(stock_info)
            .build()
        )

        assert "白酒" in prompt

    def test_builder_with_extra_context(self):
        """测试构建器设置额外上下文"""
        builder = PromptTemplateBuilder()
        prompt = (
            builder
            .set_stock("000001", "平安银行", 10.5, 2.0)
            .set_extra_context("近期银行板块走势强劲")
            .build()
        )

        assert "银行板块" in prompt

    def test_builder_error_without_stock(self):
        """测试构建器未设置股票时的错误"""
        builder = PromptTemplateBuilder()

        with pytest.raises(ValueError):
            builder.build()


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_create_stock_analysis_prompt_basic(self):
        """测试便捷函数基本功能"""
        prompt = create_stock_analysis_prompt(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=2.0,
        )

        assert prompt is not None
        assert "000001" in prompt
        assert "平安银行" in prompt

    def test_create_stock_analysis_prompt_with_all_params(self):
        """测试便捷函数带所有参数"""
        kline_data = [
            {"date": "2024-01-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000},
        ]
        stock_info = {
            "code": "000001",
            "name": "平安银行",
            "industry": "银行",
        }
        technical_indicators = {
            "ma5": 10.5,
            "rsi6": 65.0,
        }

        prompt = create_stock_analysis_prompt(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=2.0,
            analysis_type=AnalysisType.COMPREHENSIVE,
            kline_data=kline_data,
            stock_info=stock_info,
            technical_indicators=technical_indicators,
            extra_context="测试额外上下文",
        )

        assert prompt is not None
        assert "2024-01-01" in prompt
        assert "银行" in prompt
        assert "测试额外上下文" in prompt


class TestStockAnalysisContext:
    """股票分析上下文测试"""

    def test_context_creation(self):
        """测试上下文创建"""
        context = StockAnalysisContext(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=2.0,
        )

        assert context.stock_code == "000001"
        assert context.stock_name == "平安银行"
        assert context.current_price == 10.5
        assert context.change_percent == 2.0
        assert context.analysis_type == AnalysisType.COMPREHENSIVE  # 默认值

    def test_context_with_all_fields(self):
        """测试带所有字段的上下文"""
        kline_data = [{"date": "2024-01-01", "close": 10.0}]
        stock_info = {"code": "000001", "name": "平安银行"}
        indicators = {"ma5": 10.5}

        context = StockAnalysisContext(
            stock_code="000001",
            stock_name="平安银行",
            current_price=10.5,
            change_percent=2.0,
            analysis_type=AnalysisType.TECHNICAL,
            kline_data=kline_data,
            stock_info=stock_info,
            technical_indicators=indicators,
        )

        assert context.kline_data == kline_data
        assert context.stock_info == stock_info
        assert context.technical_indicators == indicators


class TestAnalysisType:
    """分析类型枚举测试"""

    def test_analysis_type_values(self):
        """测试分析类型枚举值"""
        assert AnalysisType.TECHNICAL.value == "technical"
        assert AnalysisType.FUNDAMENTAL.value == "fundamental"
        assert AnalysisType.COMPREHENSIVE.value == "comprehensive"
        assert AnalysisType.INVESTMENT_ADVICE.value == "investment_advice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
