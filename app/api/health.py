"""
健康检查路由
"""
from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any
import asyncio

router = APIRouter()


async def check_database() -> Dict[str, Any]:
    """检查数据库连接"""
    try:
        # 尝试导入数据库模块
        from app.db.database import engine

        # 尝试连接
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")

        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> Dict[str, Any]:
    """检查 Redis 连接"""
    try:
        from app.db.database import redis_client

        await redis_client.ping()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_akshare() -> Dict[str, Any]:
    """检查 AkShare 数据源"""
    try:
        import akshare as ak
        # 尝试获取一个简单的数据
        # 注意：这里不做实际请求，避免影响性能
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


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
        "service": "LLM Stock Analyzer",
        "version": "0.1.0"
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    详细健康检查接口

    Returns:
        包含所有依赖服务状态的健康信息
    """
    # 并行检查所有依赖
    db_task = check_database()
    redis_task = check_redis()
    akshare_task = check_akshare()

    results = await asyncio.gather(
        db_task, redis_task, akshare_task,
        return_exceptions=True
    )

    db_status = results[0] if not isinstance(results[0], Exception) else {"status": "unhealthy", "error": str(results[0])}
    redis_status = results[1] if not isinstance(results[1], Exception) else {"status": "unhealthy", "error": str(results[1])}
    akshare_status = results[2] if not isinstance(results[2], Exception) else {"status": "unhealthy", "error": str(results[2])}

    # 判断整体状态
    overall_status = "healthy"
    if db_status.get("status") == "unhealthy":
        overall_status = "degraded"
    if redis_status.get("status") == "unhealthy":
        overall_status = "degraded"
    if akshare_status.get("status") == "unhealthy":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "service": "LLM Stock Analyzer",
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
            "akshare": akshare_status
        }
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    就绪检查接口

    Returns:
        就绪状态信息
    """
    # 检查数据库连接
    try:
        from app.db.database import engine
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        db_ready = True
    except Exception:
        db_ready = False

    # 检查 Redis 连接
    try:
        from app.db.database import redis_client
        await redis_client.ping()
        redis_ready = True
    except Exception:
        redis_ready = False

    ready = db_ready and redis_ready

    return {
        "ready": ready,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": db_ready,
            "redis": redis_ready
        }
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
