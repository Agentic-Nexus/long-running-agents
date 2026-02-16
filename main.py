"""
大模型驱动的股票分析系统 - 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.utils.logger import setup_logger
from app.api import router as api_router
from app.api import health, stocks, chat, analysis, export

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

# 注册路由
app.include_router(api_router, prefix="/api/v1")
app.include_router(health.router, tags=["health"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(export.router, prefix="/api/v1/stocks", tags=["export"])


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
