"""
股票分析 Prompt 模板模块

提供专业的股票分析提示词模板：
- 系统提示词 (system prompt)
- 技术分析提示 (MA, MACD, RSI, KDJ等指标)
- 基本面分析提示 (财报、PE、PB等)
- 投资建议生成提示
- 结构化分析报告生成
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisType(Enum):
    """分析类型枚举"""
    TECHNICAL = "technical"           # 技术分析
    FUNDAMENTAL = "fundamental"       # 基本面分析
    COMPREHENSIVE = "comprehensive"    # 综合分析
    INVESTMENT_ADVICE = "investment_advice"  # 投资建议


@dataclass
class StockAnalysisContext:
    """股票分析上下文"""
    stock_code: str           # 股票代码
    stock_name: str           # 股票名称
    current_price: float      # 当前价格
    change_percent: float     # 涨跌幅
    analysis_type: AnalysisType = AnalysisType.COMPREHENSIVE

    # K线数据 (技术分析用)
    kline_data: Optional[List[Dict[str, Any]]] = None

    # 基本面数据
    stock_info: Optional[Dict[str, Any]] = None

    # 技术指标
    technical_indicators: Optional[Dict[str, Any]] = None

    # 附加上下文
    extra_context: Optional[str] = None


class PromptTemplate:
    """Prompt 模板基类"""

    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示词"""
        return """你是一位专业、资深的股票分析师助手。你的职责是帮助用户进行专业的股票分析，提供客观、准确、有深度的投资参考。

## 核心原则
1. **客观分析**：基于数据事实进行分析，不掺杂个人情感偏好
2. **风险提示**：始终提醒投资风险，声明不构成投资建议
3. **数据驱动**：依赖实际数据进行分析，避免主观臆断
4. **结构化输出**：按照标准格式输出分析报告，便于用户理解

## 分析框架
- 技术面分析：关注价格趋势、成交量、技术指标
- 基本面分析：关注财务数据、估值水平、行业地位
- 综合研判：结合技术面和基本面给出综合判断

## 输出要求
1. 使用清晰的结构化格式
2. 关键数据用表格或列表展示
3. 结论部分要明确、有依据
4. 必须包含风险提示免责声明

## 重要声明
- 本分析仅供参考，不构成任何投资建议
- 投资有风险，入市需谨慎
- 过去的业绩不代表未来表现"""

    @staticmethod
    def get_technical_analysis_prompt(context: StockAnalysisContext) -> str:
        """获取技术分析提示词"""
        kline_info = ""
        if context.kline_data and len(context.kline_data) > 0:
            # 取最近30天的数据
            recent_data = context.kline_data[-30:]
            kline_table = "\n".join([
                f"| {d.get('date', '')} | {d.get('open', 0):.2f} | {d.get('high', 0):.2f} | "
                f"{d.get('low', 0):.2f} | {d.get('close', 0):.2f} | {d.get('volume', 0):,} |"
                for d in recent_data
            ])
            kline_info = f"""
### 近期K线数据 (最近30个交易日)
| 日期 | 开盘 | 最高 | 最低 | 收盘 | 成交量 |
|------|------|------|------|------|--------|
| {kline_table}
"""

        indicators_info = ""
        if context.technical_indicators:
            ind = context.technical_indicators
            indicators_info = f"""
### 技术指标数据
- **MA (移动平均线)**:
  - MA5: {ind.get('ma5', 'N/A')}
  - MA10: {ind.get('ma10', 'N/A')}
  - MA20: {ind.get('ma20', 'N/A')}
  - MA60: {ind.get('ma60', 'N/A')}

- **MACD**:
  - DIF: {ind.get('macd_dif', 'N/A')}
  - DEA: {ind.get('macd_dea', 'N/A')}
  - MACD: {ind.get('macd_histogram', 'N/A')}

- **RSI**:
  - RSI6: {ind.get('rsi6', 'N/A')}
  - RSI12: {ind.get('rsi12', 'N/A')}
  - RSI24: {ind.get('rsi24', 'N/A')}

- **KDJ**:
  - K: {ind.get('kdj_k', 'N/A')}
  - D: {ind.get('kdj_d', 'N/A')}
  - J: {ind.get('kdj_j', 'N/A')}

- **布林带 (BOLL)**:
  - 上轨: {ind.get('boll_upper', 'N/A')}
  - 中轨: {ind.get('boll_mid', 'N/A')}
  - 下轨: {ind.get('boll_lower', 'N/A')}
"""

        prompt = f"""## 股票技术分析任务

### 基本信息
- 股票代码: {context.stock_code}
- 股票名称: {context.stock_name}
- 当前价格: {context.current_price:.2f} 元
- 涨跌幅: {context.change_percent:+.2f}%

{kline_info}
{indicators_info}

### 分析要求

请进行以下技术分析：

1. **趋势分析**
   - 判断当前价格趋势（上涨/下跌/震荡）
   - 分析短期、中期、长期趋势一致性
   - 识别关键支撑位和压力位

2. **均线分析**
   - 分析MA5、MA10、MA20、MA60的排列状态
   - 判断均线金叉/死叉情况
   - 评估均线支撑/压力效果

3. **MACD分析**
   - 分析DIF与DEA的位置关系
   - 判断MACD柱状图变化趋势
   - 识别潜在的买卖信号

4. **RSI分析**
   - 判断RSI是否处于超买/超卖区域
   - 分析RSI背离情况

5. **KDJ分析**
   - 判断K、D、J值位置
   - 识别超买超卖信号
   - 分析金叉死叉信号

6. **成交量分析**
   - 分析成交量与价格配合情况
   - 识别放量/缩量特征

### 输出格式

请按以下结构输出技术分析报告：

```
## 技术分析报告 - {context.stock_name}({context.stock_code})

### 一、趋势判断
[趋势判断及依据]

### 二、关键技术信号
| 指标 | 数值 | 信号判断 |
|------|------|----------|
| MA排列 | ... | ... |
| MACD | ... | ... |
| RSI | ... | ... |
| KDJ | ... | ... |

### 三、支撑位与压力位
- 支撑位: ...
- 压力位: ...

### 四、成交量分析
[成交量分析]

### 五、综合技术判断
[综合判断]

### 六、风险提示
⚠️ 风险提示：本分析仅供参考，不构成投资建议。技术分析存在局限性，请结合其他因素综合判断。
```

请基于以上数据进行分析。"""

        return prompt

    @staticmethod
    def get_fundamental_analysis_prompt(context: StockAnalysisContext) -> str:
        """获取基本面分析提示词"""
        stock_info = ""
        if context.stock_info:
            si = context.stock_info
            stock_info = f"""
### 公司基本信息
- 股票代码: {si.get('code', '')}
- 股票名称: {si.get('name', '')}
- 所属行业: {si.get('industry', 'N/A')}
- 上市时间: {si.get('listing_date', 'N/A')}
- 总股本: {si.get('total_shares', 'N/A')} 万股
- 流通股本: {si.get('circulating_shares', 'N/A')} 万股
- 所属市场: {si.get('market', 'N/A')}
"""

        prompt = f"""## 股票基本面分析任务

{stock_info}

### 估值指标
- 当前价格: {context.current_price:.2f} 元
- 涨跌幅: {context.change_percent:+.2f}%

### 分析要求

请进行以下基本面分析：

1. **行业分析**
   - 分析公司所属行业特点
   - 评估行业景气度
   - 比较行业内公司地位

2. **估值分析**
   - 分析市盈率 (PE) 水平
   - 分析市净率 (PB) 水平
   - 与行业平均估值对比

3. **财务分析** (如数据可用)
   - 营收增长情况
   - 净利润增长情况
   - 毛利率、净利率水平
   - 资产负债情况

4. **股本结构**
   - 总股本与流通股本
   - 大股东持股情况
   - 限售股解禁情况

5. **分红送转**
   - 历史分红情况
   - 送转股历史

6. **风险因素**
   - 经营风险
   - 行业风险
   - 政策风险
   - 市场风险

### 输出格式

请按以下结构输出基本面分析报告：

```
## 基本面分析报告 - {context.stock_name}({context.stock_code})

### 一、公司概况
[公司基本信息及业务介绍]

### 二、行业分析
[行业特点及公司地位]

### 三、估值分析
| 指标 | 数值 | 行业对比 | 评估 |
|------|------|----------|------|
| PE | ... | ... | ... |
| PB | ... | ... | ... |

### 四、财务分析
[财务数据摘要]

### 五、风险因素
[主要风险点]

### 六、综合基本面判断
[综合评价]

### 七、风险提示
⚠️ 风险提示：本分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
```

请基于以上数据进行基本面分析。"""

        return prompt

    @staticmethod
    def get_investment_advice_prompt(context: StockAnalysisContext) -> str:
        """获取投资建议提示词"""
        prompt = f"""## 股票投资建议生成任务

### 基本信息
- 股票代码: {context.stock_code}
- 股票名称: {context.stock_name}
- 当前价格: {context.current_price:.2f} 元
- 涨跌幅: {context.change_percent:+.2f}%

{context.extra_context if context.extra_context else ""}

### 分析要求

请综合技术面和基本面分析，生成投资建议：

1. **行情研判**
   - 短期行情判断 (1-5个交易日)
   - 中期行情判断 (1-3个月)
   - 长期行情判断 (3-12个月)

2. **操作建议**
   - 是否建议买入
   - 建议买入价位
   - 建议卖出价位
   - 止盈止损建议

3. **仓位建议**
   - 建议仓位比例
   - 建仓策略

4. **风险评估**
   - 主要风险点
   - 风险等级 (低/中/高)

5. **持有周期**
   - 建议持有周期
   - 关键观察时点

### 输出格式

请按以下结构输出投资建议：

```
## 投资建议报告 - {context.stock_name}({context.stock_code})

### 一、行情研判
| 周期 | 判断 | 依据 |
|------|------|------|
| 短期 | ... | ... |
| 中期 | ... | ... |
| 长期 | ... | ... |

### 二、操作建议
- 买入建议: [是/否/观望]
- 建议价位: ...
- 目标价位: ...
- 止损价位: ...

### 三、仓位建议
- 建议仓位: ...
- 建仓策略: ...

### 四、风险评估
- 风险等级: [低/中/高]
- 主要风险: ...

### 五持有周期建议
- 建议持有周期: ...
- 关键观察时点: ...

### 六、风险提示
⚠️ 重要声明：
1. 本分析仅供参考，不构成任何投资建议
2. 投资有风险，入市需谨慎
3. 投资者应根据自身风险承受能力做出投资决策
4. 过去的业绩不代表未来表现
5. 请务必做好止损措施，控制投资风险

```

请基于分析生成投资建议。"""

        return prompt

    @staticmethod
    def get_comprehensive_analysis_prompt(context: StockAnalysisContext) -> str:
        """获取综合分析提示词（技术面+基本面）"""
        technical_prompt = PromptTemplate.get_technical_analysis_prompt(context)
        fundamental_prompt = PromptTemplate.get_fundamental_analysis_prompt(context)

        # 添加额外上下文
        extra_context = ""
        if context.extra_context:
            extra_context = f"\n### 附加上下文\n{context.extra_context}\n"

        # 合并两个分析，并添加综合判断部分
        comprehensive_prompt = f"""{technical_prompt}

---

{fundamental_prompt}

{extra_context}
---

## 综合分析要求

请在完成技术分析和基本面分析后，添加以下综合分析部分：

### 综合研判

1. **技术面与基本面共振**
   - 技术面信号与基本面是否一致
   - 哪些因素形成合力
   - 哪些因素存在矛盾

2. **优势分析**
   - 该股票的核心优势
   - 潜在利好因素

3. **劣势分析**
   - 该股票的风险点
   - 潜在利空因素

4. **综合评分** (1-10分)
   - 技术面评分: _
   - 基本面评分: _
   - 综合评分: _

5. **最终结论**
   - 综合判断
   - 操作建议

### 输出格式

请在技术分析和基本面分析之后，添加综合分析部分：

```
### 七、综合研判

#### 技术面与基本面共振
[分析]

#### 优势分析
[列出主要优势]

#### 劣势分析
[列出主要风险]

#### 综合评分
- 技术面评分: X/10
- 基本面评分: X/10
- 综合评分: X/10

#### 最终结论
[综合判断]

### 八、风险提示
⚠️ 重要声明：
1. 本分析仅供参考，不构成任何投资建议
2. 投资有风险，入市需谨慎
3. 投资者应根据自身风险承受能力做出投资决策
4. 过去的业绩不代表未来表现
5. 请务必做好止损措施，控制投资风险
```

请完成完整的综合分析报告。"""

        return comprehensive_prompt

    @classmethod
    def generate_prompt(cls, context: StockAnalysisContext) -> str:
        """
        根据分析类型生成对应的Prompt

        Args:
            context: 股票分析上下文

        Returns:
            格式化后的提示词
        """
        logger.info(f"Generating prompt for {context.stock_code}, type: {context.analysis_type.value}")

        # 先返回系统提示
        system_prompt = cls.get_system_prompt()

        # 根据分析类型生成对应的用户提示
        if context.analysis_type == AnalysisType.TECHNICAL:
            user_prompt = cls.get_technical_analysis_prompt(context)
        elif context.analysis_type == AnalysisType.FUNDAMENTAL:
            user_prompt = cls.get_fundamental_analysis_prompt(context)
        elif context.analysis_type == AnalysisType.INVESTMENT_ADVICE:
            user_prompt = cls.get_investment_advice_prompt(context)
        else:  # COMPREHENSIVE
            user_prompt = cls.get_comprehensive_analysis_prompt(context)

        # 组合系统提示和用户提示
        full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

        return full_prompt


class PromptTemplateBuilder:
    """Prompt 模板构建器"""

    def __init__(self):
        self._context: Optional[StockAnalysisContext] = None

    def set_stock(self, code: str, name: str, price: float, change: float) -> "PromptTemplateBuilder":
        """设置股票基本信息"""
        self._context = StockAnalysisContext(
            stock_code=code,
            stock_name=name,
            current_price=price,
            change_percent=change
        )
        return self

    def set_analysis_type(self, analysis_type: AnalysisType) -> "PromptTemplateBuilder":
        """设置分析类型"""
        if self._context:
            self._context.analysis_type = analysis_type
        return self

    def set_kline_data(self, kline_data: List[Dict[str, Any]]) -> "PromptTemplateBuilder":
        """设置K线数据"""
        if self._context:
            self._context.kline_data = kline_data
        return self

    def set_stock_info(self, stock_info: Dict[str, Any]) -> "PromptTemplateBuilder":
        """设置股票基本信息"""
        if self._context:
            self._context.stock_info = stock_info
        return self

    def set_technical_indicators(self, indicators: Dict[str, Any]) -> "PromptTemplateBuilder":
        """设置技术指标"""
        if self._context:
            self._context.technical_indicators = indicators
        return self

    def set_extra_context(self, context: str) -> "PromptTemplateBuilder":
        """设置额外上下文"""
        if self._context:
            self._context.extra_context = context
        return self

    def build(self) -> str:
        """构建Prompt"""
        if not self._context:
            raise ValueError("Stock context not set")
        return PromptTemplate.generate_prompt(self._context)


# 便捷函数
def create_stock_analysis_prompt(
    stock_code: str,
    stock_name: str,
    current_price: float,
    change_percent: float,
    analysis_type: AnalysisType = AnalysisType.COMPREHENSIVE,
    kline_data: Optional[List[Dict[str, Any]]] = None,
    stock_info: Optional[Dict[str, Any]] = None,
    technical_indicators: Optional[Dict[str, Any]] = None,
    extra_context: Optional[str] = None,
) -> str:
    """
    创建股票分析Prompt的便捷函数

    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        current_price: 当前价格
        change_percent: 涨跌幅
        analysis_type: 分析类型
        kline_data: K线数据
        stock_info: 股票基本信息
        technical_indicators: 技术指标
        extra_context: 额外上下文

    Returns:
        格式化后的Prompt
    """
    context = StockAnalysisContext(
        stock_code=stock_code,
        stock_name=stock_name,
        current_price=current_price,
        change_percent=change_percent,
        analysis_type=analysis_type,
        kline_data=kline_data,
        stock_info=stock_info,
        technical_indicators=technical_indicators,
        extra_context=extra_context,
    )
    return PromptTemplate.generate_prompt(context)
