"""
健康检查路由
"""
from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查接口

    Returns:
        健康状态信息
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "LLM Stock Analyzer"
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    就绪检查接口

    Returns:
        就绪状态信息
    """
    # TODO: 检查数据库、缓存等依赖服务
    return {
        "ready": True,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    存活检查接口

    Returns:
        存活状态信息
    """
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat()
    }
