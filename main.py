"""
大模型驱动的股票分析系统 - 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="LLM Stock Analyzer",
    description="基于大模型的智能股票分析系统",
    version="0.1.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路由"""
    return {
        "message": "LLM Stock Analyzer API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# TODO: 后续功能逐步实现
# 1. 股票数据获取模块 (app/services/stock_service.py)
# 2. LLM 集成模块 (app/services/llm_service.py)
# 3. API 路由 (app/api/)
# 4. 数据模型 (app/models/)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
