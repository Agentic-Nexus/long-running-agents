"""
财经新闻 API 路由

提供财经新闻相关接口：
- 最新新闻列表
- 新闻搜索
- 新闻分类
- 热门关键词
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from app.services.news_service import (
    NewsService,
    get_news_service,
    get_news_categories,
    NEWS_CATEGORIES
)
from app.services.cache_service import get_cache, CACHE_TTL
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================
# 请求/响应模型
# ============================================

class NewsItem(BaseModel):
    """新闻条目"""
    title: str
    url: str
    source: str
    category: str
    published_at: str
    summary: str


class NewsListResponse(BaseModel):
    """新闻列表响应"""
    total: int
    news: List[NewsItem]
    categories: dict


class NewsSearchRequest(BaseModel):
    """新闻搜索请求"""
    keyword: str
    limit: int = 50


class HotKeyword(BaseModel):
    """热门关键词"""
    keyword: str
    count: int


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None


# ============================================
# API 端点
# ============================================

@router.get("/news", response_model=NewsListResponse)
async def get_news(
    category: Optional[str] = Query(None, description="新闻分类"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    symbol: Optional[str] = Query(None, description="股票代码")
):
    """
    获取最新财经新闻

    Args:
        category: 新闻分类 (macro/industry/company/market/economy/forex/commodity/crypto/other)
        limit: 返回数量限制
        symbol: 股票代码

    Returns:
        新闻列表
    """
    try:
        news_service = get_news_service()
        news_list = news_service.get_latest_news(
            category=category,
            limit=limit,
            symbol=symbol
        )

        return NewsListResponse(
            total=len(news_list),
            news=[NewsItem(**news) for news in news_list],
            categories=NEWS_CATEGORIES
        )

    except Exception as e:
        logger.error(f"Failed to get news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/search", response_model=List[NewsItem])
async def search_news(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制")
):
    """
    搜索财经新闻

    Args:
        keyword: 搜索关键词
        limit: 返回数量限制

    Returns:
        匹配的新闻列表
    """
    try:
        news_service = get_news_service()
        news_list = news_service.search_news(
            keyword=keyword,
            limit=limit
        )

        return [NewsItem(**news) for news in news_list]

    except Exception as e:
        logger.error(f"Failed to search news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/categories")
async def get_categories():
    """
    获取新闻分类

    Returns:
        新闻分类列表
    """
    return {
        "categories": NEWS_CATEGORIES
    }


@router.get("/news/keywords/hot", response_model=List[HotKeyword])
async def get_hot_keywords(
    limit: int = Query(10, ge=1, le=50, description="返回数量限制")
):
    """
    获取热门关键词

    Args:
        limit: 返回数量限制

    Returns:
        热门关键词列表
    """
    try:
        news_service = get_news_service()
        keywords = news_service.get_hot_keywords(limit=limit)

        return [HotKeyword(**kw) for kw in keywords]

    except Exception as e:
        logger.error(f"Failed to get hot keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/date/{date}", response_model=List[NewsItem])
async def get_news_by_date(
    date: str = Path(..., description="日期，格式 YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制")
):
    """
    获取指定日期的新闻

    Args:
        date: 日期，格式 YYYY-MM-DD
        limit: 返回数量限制

    Returns:
        指定日期的新闻列表
    """
    try:
        # 验证日期格式
        from datetime import datetime
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        news_service = get_news_service()
        news_list = news_service.get_news_by_date(
            date=date,
            limit=limit
        )

        return [NewsItem(**news) for news in news_list]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get news by date: {e}")
        raise HTTPException(status_code=500, detail=str(e))
