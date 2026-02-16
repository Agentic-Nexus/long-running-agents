"""
数据导出服务模块测试
"""

import pytest
import io
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.services.export_service import (
    ExportService,
    ExportFormat,
    ExportDataType,
    get_export_service,
)


class TestExportFormat:
    """导出格式枚举测试"""

    def test_export_format_values(self):
        """测试导出格式枚举值"""
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.EXCEL.value == "excel"


class TestExportDataType:
    """数据类型枚举测试"""

    def test_export_data_type_values(self):
        """测试数据类型枚举值"""
        assert ExportDataType.INFO.value == "info"
        assert ExportDataType.KLINE.value == "kline"
        assert ExportDataType.TECHNICAL.value == "technical"
        assert ExportDataType.ALL.value == "all"


class TestExportService:
    """导出服务测试"""

    def setup_method(self):
        """每个测试方法前设置"""
        self.service = ExportService()

    def test_service_init(self):
        """测试服务初始化"""
        assert self.service.stock_service is not None

    def test_get_export_service_singleton(self):
        """测试获取服务单例"""
        service1 = get_export_service()
        service2 = get_export_service()

        assert service1 is service2

    @patch("app.services.export_service.ExportService._create_stock_info_dataframe")
    def test_export_stock_info_csv(self, mock_info_df):
        """测试导出股票信息为 CSV 格式"""
        # 模拟返回的 DataFrame
        mock_info_df.return_value = pd.DataFrame({
            "code": ["sh600000"],
            "name": ["浦发银行"],
            "market": ["上海证券交易所"],
            "industry": ["银行"],
        })

        result = self.service.export_stock_data(
            symbol="600000",
            data_type=ExportDataType.INFO,
            format=ExportFormat.CSV
        )

        assert result is not None
        assert isinstance(result, bytes)
        # CSV 内容应该包含数据
        content = result.decode("utf-8-sig")
        assert "sh600000" in content
        assert "浦发银行" in content

    @patch("app.services.export_service.ExportService._create_stock_info_dataframe")
    def test_export_stock_info_excel(self, mock_info_df):
        """测试导出股票信息为 Excel 格式"""
        mock_info_df.return_value = pd.DataFrame({
            "code": ["sh600000"],
            "name": ["浦发银行"],
            "market": ["上海证券交易所"],
        })

        result = self.service.export_stock_data(
            symbol="600000",
            data_type=ExportDataType.INFO,
            format=ExportFormat.EXCEL
        )

        assert result is not None
        assert isinstance(result, bytes)
        # Excel 文件以 PK 开头（ZIP 格式）
        assert result[:2] == b"PK"

    @patch("app.services.export_service.ExportService._create_kline_dataframe")
    def test_export_kline_csv(self, mock_kline_df):
        """测试导出K线数据为 CSV 格式"""
        mock_kline_df.return_value = pd.DataFrame({
            "code": ["sh600000", "sh600000"],
            "date": ["2024-01-01", "2024-01-02"],
            "open": [10.0, 10.5],
            "high": [10.8, 11.0],
            "low": [9.8, 10.3],
            "close": [10.5, 10.8],
            "volume": [1000000, 1100000],
            "amount": [10000000, 11000000],
        })

        result = self.service.export_stock_data(
            symbol="600000",
            data_type=ExportDataType.KLINE,
            format=ExportFormat.CSV
        )

        assert result is not None
        assert isinstance(result, bytes)
        content = result.decode("utf-8-sig")
        assert "sh600000" in content

    @patch("app.services.export_service.ExportService._create_technical_dataframe")
    def test_export_technical_csv(self, mock_tech_df):
        """测试导出技术分析数据为 CSV 格式"""
        mock_tech_df.return_value = pd.DataFrame({
            "date": ["2024-01-01"],
            "open": [10.0],
            "high": [10.8],
            "low": [9.8],
            "close": [10.5],
            "volume": [1000000],
            "MA5": [10.2],
            "MA10": [10.0],
            "RSI-6": [60.0],
        })

        result = self.service.export_stock_data(
            symbol="600000",
            data_type=ExportDataType.TECHNICAL,
            format=ExportFormat.CSV
        )

        assert result is not None
        assert isinstance(result, bytes)

    @patch("app.services.export_service.ExportService._create_stock_info_dataframe")
    @patch("app.services.export_service.ExportService._create_kline_dataframe")
    @patch("app.services.export_service.ExportService._create_technical_dataframe")
    def test_export_all_data_excel(self, mock_tech_df, mock_kline_df, mock_info_df):
        """测试导出全部数据为 Excel 格式"""
        mock_info_df.return_value = pd.DataFrame({
            "code": ["sh600000"],
            "name": ["浦发银行"],
        })

        mock_kline_df.return_value = pd.DataFrame({
            "date": ["2024-01-01"],
            "close": [10.5],
        })

        mock_tech_df.return_value = pd.DataFrame({
            "date": ["2024-01-01"],
            "close": [10.5],
            "MA5": [10.2],
        })

        result = self.service.export_stock_data(
            symbol="600000",
            data_type=ExportDataType.ALL,
            format=ExportFormat.EXCEL
        )

        assert result is not None
        assert isinstance(result, bytes)
        assert result[:2] == b"PK"

    def test_export_with_empty_data(self):
        """测试导出空数据"""
        with patch("app.services.export_service.ExportService._create_kline_dataframe") as mock_kline_df:
            mock_kline_df.return_value = pd.DataFrame()

            with pytest.raises(ValueError) as exc_info:
                self.service.export_stock_data(
                    symbol="600000",
                    data_type=ExportDataType.KLINE,
                    format=ExportFormat.CSV
                )

            assert "未获取到数据" in str(exc_info.value)

    def test_export_invalid_data_type(self):
        """测试无效的数据类型"""
        with pytest.raises(ValueError) as exc_info:
            self.service.export_stock_data(
                symbol="600000",
                data_type="invalid_type",  # type: ignore
                format=ExportFormat.CSV
            )

        assert "不支持的数据类型" in str(exc_info.value)

    def test_export_to_csv(self):
        """测试 CSV 导出方法"""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["a", "b", "c"]
        })

        result = self.service._export_to_csv(df)

        assert result is not None
        assert isinstance(result, bytes)
        content = result.decode("utf-8-sig")
        assert "col1" in content
        assert "col2" in content

    def test_export_to_excel(self):
        """测试 Excel 导出方法"""
        dfs = {
            "Sheet1": pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]}),
            "Sheet2": pd.DataFrame({"col3": [3, 4], "col4": ["c", "d"]})
        }

        result = self.service._export_to_excel(dfs)

        assert result is not None
        assert isinstance(result, bytes)
        assert result[:2] == b"PK"

    def test_export_to_excel_long_sheet_name(self):
        """测试 Excel 导出时 sheet 名称过长"""
        dfs = {
            "这是一个非常长的sheet名称超过三十一个字符": pd.DataFrame({"col1": [1]})
        }

        result = self.service._export_to_excel(dfs)

        assert result is not None
        assert isinstance(result, bytes)

    def test_export_with_date_parameters(self):
        """测试带日期参数的导出"""
        with patch("app.services.export_service.ExportService._create_kline_dataframe") as mock_kline_df:
            mock_kline_df.return_value = pd.DataFrame({
                "date": ["2024-01-01"],
                "close": [10.5],
            })

            result = self.service.export_stock_data(
                symbol="600000",
                data_type=ExportDataType.KLINE,
                format=ExportFormat.CSV,
                start_date="20240101",
                end_date="20240131"
            )

            mock_kline_df.assert_called_once_with(
                "600000", "20240101", "20240131", "daily", "qfq"
            )
            assert result is not None


class TestExportServiceMocked:
    """使用 Mock 的导出服务测试"""

    @patch("app.services.export_service.get_stock_service")
    def test_service_uses_stock_service(self, mock_get_stock_service):
        """测试导出服务使用股票服务"""
        mock_stock_service = MagicMock()
        mock_get_stock_service.return_value = mock_stock_service

        service = ExportService()

        assert service.stock_service is not None

    def test_export_csv_with_unicode(self):
        """测试导出包含中文的 CSV"""
        service = ExportService()

        df = pd.DataFrame({
            "股票代码": ["600000", "000001"],
            "股票名称": ["浦发银行", "平安银行"],
            "收盘价": [10.5, 12.3]
        })

        result = service._export_to_csv(df)

        content = result.decode("utf-8-sig")
        assert "股票代码" in content
        assert "浦发银行" in content
        assert "平安银行" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
