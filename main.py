"""
大模型驱动的股票分析系统 - 主入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging
from app.utils.logger import setup_logger
from app.api import router as api_router
from app.api import health, stocks, chat, analysis, export, websocket, auth, alert, metrics, news, toplist, portfolio
from app.api.metrics import track_request

# 配置日志
logger = setup_logger("stock_analyzer", level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting LLM Stock Analyzer...")
    yield
    # 关闭时
    logger.info("Shutting down LLM Stock Analyzer...")


# 创建 FastAPI 应用
app = FastAPI(
    title="LLM Stock Analyzer",
    description="基于大模型的智能股票分析系统",
    version="0.1.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 自定义指标跟踪中间件
class MetricsMiddleware(BaseHTTPMiddleware):
    """指标收集中间件"""

    async def dispatch(self, request: Request, call_next):
        from app.api.metrics import (
            REQUEST_COUNT,
            REQUEST_LATENCY,
            ACTIVE_CONNECTIONS,
            ERROR_COUNT
        )
        import time

        start_time = time.time()
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
            ACTIVE_CONNECTIONS.dec()


# 添加指标中间件
app.add_middleware(MetricsMiddleware)

# 注册路由
app.include_router(api_router, prefix="/api/v1")
app.include_router(health.router, tags=["health"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(export.router, prefix="/api/v1/stocks", tags=["export"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
app.include_router(alert.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(news.router, prefix="/api/v1", tags=["news"])
app.include_router(toplist.router, prefix="/api/v1/toplist", tags=["toplist"])
app.include_router(portfolio.router, prefix="/api/v1/portfolios", tags=["portfolios"])


@app.get("/")
async def root():
    """根路由"""
    return {
        "message": "LLM Stock Analyzer API",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
