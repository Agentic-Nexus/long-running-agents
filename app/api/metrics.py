"""
Prometheus 指标路由
"""
from fastapi import APIRouter, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from datetime import datetime
from typing import Dict, Any
import time

router = APIRouter()

# 请求计数器
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

# 请求延迟直方图
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# 活跃连接数
ACTIVE_CONNECTIONS = Gauge(
    'http_active_connections',
    'Number of active HTTP connections'
)

# 业务指标 - 股票查询
STOCK_QUERIES = Counter(
    'stock_queries_total',
    'Total stock queries',
    ['query_type']
)

# 业务指标 - LLM 调用
LLM_REQUESTS = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['model', 'status']
)

LLM_LATENCY = Histogram(
    'llm_request_duration_seconds',
    'LLM request latency in seconds',
    ['model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# 业务指标 - 错误统计
ERROR_COUNT = Counter(
    'error_count_total',
    'Total errors',
    ['error_type', 'endpoint']
)

# 数据库连接池
DB_POOL_SIZE = Gauge(
    'database_pool_size',
    'Database connection pool size'
)

DB_POOL_FREE = Gauge(
    'database_pool_free',
    'Free database connections'
)

# 缓存命中率
CACHE_HIT = Counter(
    'cache_hits_total',
    'Total cache hits'
)

CACHE_MISS = Counter(
    'cache_misses_total',
    'Total cache misses'
)


@router.get("/metrics")
async def metrics():
    """
    Prometheus 指标端点

    Returns:
        Prometheus 格式的指标数据
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/metrics/internal")
async def internal_metrics() -> Dict[str, Any]:
    """
    内部指标端点（JSON 格式）

    Returns:
        JSON 格式的内部指标
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "requests": {
            "total": sum(REQUEST_COUNT._value.values()) if REQUEST_COUNT._value else 0
        },
        "active_connections": ACTIVE_CONNECTIONS._value.get() if ACTIVE_CONNECTIONS._value else 0,
        "cache": {
            "hits": CACHE_HIT._value.get() if CACHE_HIT._value else 0,
            "misses": CACHE_MISS._value.get() if CACHE_MISS._value else 0
        }
    }


# 中间件函数
async def track_request(request: Request, call_next):
    """请求跟踪中间件"""
    start_time = time.time()

    # 增加活跃连接数
    ACTIVE_CONNECTIONS.inc()

    try:
        response = await call_next(request)

        # 记录请求
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()

        # 记录延迟
        duration = time.time() - start_time
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response
    except Exception as e:
        # 记录错误
        ERROR_COUNT.labels(
            error_type=type(e).__name__,
            endpoint=request.url.path
        ).inc()
        raise
    finally:
        # 减少活跃连接数
        ACTIVE_CONNECTIONS.dec()
