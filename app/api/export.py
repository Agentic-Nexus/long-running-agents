"""
数据导出 API 路由

提供股票数据导出接口，支持 CSV 和 Excel 格式。
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
from enum import Enum

from app.services.export_service import (
    ExportService,
    ExportFormat,
    ExportDataType,
    get_export_service
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class DataTypeQuery(str, Enum):
    """导出的数据类型查询参数"""
    INFO = "info"
    KLINE = "kline"
    TECHNICAL = "technical"
    ALL = "all"


class FormatQuery(str, Enum):
    """导出格式查询参数"""
    CSV = "csv"
    EXCEL = "excel"


@router.get("/export/{code}")
async def export_stock_data(
    code: str,
    data_type: DataTypeQuery = Query(
        DataTypeQuery.ALL,
        description="数据类型: info(基本信息), kline(K线), technical(技术分析), all(全部)"
    ),
    format: FormatQuery = Query(
        FormatQuery.CSV,
        description="导出格式: csv, excel"
    ),
    start_date: Optional[str] = Query(
        None,
        description="开始日期 (YYYYMMDD)"
    ),
    end_date: Optional[str] = Query(
        None,
        description="结束日期 (YYYYMMDD)"
    ),
    period: str = Query(
        "daily",
        description="周期: daily(日线), weekly(周线), monthly(月线)"
    ),
    adjust: str = Query(
        "qfq",
        description="复权类型: qfq(前复权), hfq(后复权), 空字符串(不复权)"
    )
):
    """
    导出股票数据

    支持导出股票基本信息、历史K线数据和技术分析指标。
    返回文件下载流。

    Args:
        code: 股票代码 (如 600000, 000001)
        data_type: 导出的数据类型
        format: 导出格式
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        period: 周期类型
        adjust: 复权类型

    Returns:
        文件下载流
    """
    # 验证周期参数
    valid_periods = ["daily", "weekly", "monthly"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"无效的周期类型: {period}。支持的类型: {valid_periods}"
        )

    # 验证复权类型
    valid_adjusts = ["qfq", "hfq", ""]
    if adjust not in valid_adjusts:
        raise HTTPException(
            status_code=400,
            detail=f"无效的复权类型: {adjust}。支持的类型: {valid_adjusts}"
        )

    logger.info(f"导出股票数据: {code}, 类型: {data_type}, 格式: {format}")

    try:
        service = get_export_service()

        # 导出数据
        data = service.export_stock_data(
            symbol=code,
            data_type=ExportDataType(data_type.value),
            format=ExportFormat(format.value),
            start_date=start_date,
            end_date=end_date,
            period=period,
            adjust=adjust
        )

        # 确定文件扩展名和媒体类型
        if format == FormatQuery.CSV:
            file_ext = "csv"
            media_type = "text/csv"
        else:
            file_ext = "xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # 生成文件名
        filename = f"stock_{code}_{data_type.value}_{period}.{file_ext}"

        # 返回流式响应
        return StreamingResponse(
            iter([data]),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(data))
            }
        )

    except ValueError as e:
        logger.error(f"数据导出失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"数据导出失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据导出失败: {str(e)}")


@router.get("/export/formats")
async def get_export_formats():
    """
    获取支持的导出格式

    Returns:
        支持的导出格式列表
    """
    return {
        "formats": [
            {"value": "csv", "name": "CSV", "description": "逗号分隔值文件"},
            {"value": "excel", "name": "Excel", "description": "Microsoft Excel 文件"}
        ],
        "data_types": [
            {"value": "info", "name": "基本信息", "description": "股票基本信息"},
            {"value": "kline", "name": "K线数据", "description": "历史K线数据"},
            {"value": "technical", "name": "技术分析", "description": "技术分析指标"},
            {"value": "all", "name": "全部数据", "description": "包含所有数据类型"}
        ],
        "periods": [
            {"value": "daily", "name": "日线"},
            {"value": "weekly", "name": "周线"},
            {"value": "monthly", "name": "月线"}
        ]
    }
