"""
数据导出服务模块

提供股票数据导出功能，支持 CSV 和 Excel 格式：
- 股票基本信息导出
- 历史K线数据导出
- 技术分析指标导出
"""

import io
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

import pandas as pd

from app.services.stock_service import StockService, get_stock_service
from app.services.technical_analysis import add_indicators_to_dataframe
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExportFormat(str, Enum):
    """导出格式枚举"""
    CSV = "csv"
    EXCEL = "excel"


class ExportDataType(str, Enum):
    """导出的数据类型枚举"""
    INFO = "info"           # 股票基本信息
    KLINE = "kline"         # K线数据
    TECHNICAL = "technical" # 技术分析指标
    ALL = "all"             # 全部数据


class ExportService:
    """数据导出服务类"""

    def __init__(self):
        """初始化导出服务"""
        self.stock_service = get_stock_service()

    def _create_stock_info_dataframe(self, symbol: str) -> pd.DataFrame:
        """
        创建股票信息 DataFrame

        Args:
            symbol: 股票代码

        Returns:
            股票信息 DataFrame
        """
        info = self.stock_service.get_stock_info(symbol)
        if info is None:
            return pd.DataFrame()

        # 转换为 DataFrame
        df = pd.DataFrame([info])
        return df

    def _create_kline_dataframe(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        创建K线数据 DataFrame

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期 (daily/weekly/monthly)
            adjust: 复权类型 (qfq/hfq/"")

        Returns:
            K线数据 DataFrame
        """
        kline_data = self.stock_service.get_kline_data(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )

        if kline_data is None or len(kline_data) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(kline_data)
        return df

    def _create_technical_dataframe(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        创建技术分析数据 DataFrame

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期 (daily/weekly/monthly)
            adjust: 复权类型 (qfq/hfq/"")

        Returns:
            技术分析数据 DataFrame
        """
        # 获取K线数据
        kline_data = self.stock_service.get_kline_data(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )

        if kline_data is None or len(kline_data) == 0:
            return pd.DataFrame()

        # 转换为 DataFrame 并添加技术指标
        df = pd.DataFrame(kline_data)

        # 重命名列为英文（与 technical_analysis 模块兼容）
        df = df.rename(columns={
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume"
        })

        # 添加技术指标
        df = add_indicators_to_dataframe(df)

        return df

    def export_stock_data(
        self,
        symbol: str,
        data_type: ExportDataType = ExportDataType.ALL,
        format: ExportFormat = ExportFormat.CSV,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> bytes:
        """
        导出股票数据

        Args:
            symbol: 股票代码
            data_type: 导出的数据类型
            format: 导出格式
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期 (daily/weekly/monthly)
            adjust: 复权类型 (qfq/hfq/"")

        Returns:
            导出的二进制数据
        """
        logger.info(f"开始导出股票数据: {symbol}, 类型: {data_type}, 格式: {format}")

        # 根据数据类型获取数据
        if data_type == ExportDataType.INFO:
            df = self._create_stock_info_dataframe(symbol)
            sheet_name = "股票信息"
        elif data_type == ExportDataType.KLINE:
            df = self._create_kline_dataframe(symbol, start_date, end_date, period, adjust)
            sheet_name = "K线数据"
        elif data_type == ExportDataType.TECHNICAL:
            df = self._create_technical_dataframe(symbol, start_date, end_date, period, adjust)
            sheet_name = "技术分析"
        elif data_type == ExportDataType.ALL:
            # 导出所有数据到不同的 sheet
            dfs = {}

            # 股票信息
            info_df = self._create_stock_info_dataframe(symbol)
            if not info_df.empty:
                dfs["股票信息"] = info_df

            # K线数据
            kline_df = self._create_kline_dataframe(symbol, start_date, end_date, period, adjust)
            if not kline_df.empty:
                dfs["K线数据"] = kline_df

            # 技术分析
            tech_df = self._create_technical_dataframe(symbol, start_date, end_date, period, adjust)
            if not tech_df.empty:
                dfs["技术分析"] = tech_df

            if not dfs:
                raise ValueError(f"未获取到任何数据: {symbol}")

            # 生成 Excel 文件
            return self._export_to_excel(dfs)

        else:
            raise ValueError(f"不支持的数据类型: {data_type}")

        if df.empty:
            raise ValueError(f"未获取到数据: {symbol}")

        # 根据格式导出
        if format == ExportFormat.CSV:
            return self._export_to_csv(df)
        else:
            return self._export_to_excel({sheet_name: df})

    def _export_to_csv(self, df: pd.DataFrame) -> bytes:
        """
        导出为 CSV 格式

        Args:
            df: 数据 DataFrame

        Returns:
            CSV 二进制数据
        """
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
        return output.getvalue()

    def _export_to_excel(self, dfs: Dict[str, pd.DataFrame]) -> bytes:
        """
        导出为 Excel 格式

        Args:
            dfs: 数据字典，key 为 sheet 名称，value 为 DataFrame

        Returns:
            Excel 二进制数据
        """
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sheet_name, df in dfs.items():
                # 限制 sheet 名称长度（Excel 限制 31 字符）
                sheet_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        output.seek(0)
        return output.getvalue()


# 全局服务实例
_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """获取导出服务实例"""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service
