"""
财经新闻服务模块

提供财经新闻数据获取功能：
- 多源财经新闻获取
- 新闻分类筛选
- 关键词搜索
- 新闻缓存
- 新闻摘要生成
"""

import time
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict

import requests
from app.services.cache_service import get_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NewsCache:
    """新闻缓存类"""

    def __init__(self, ttl: int = 600):
        """
        初始化新闻缓存

        Args:
            ttl: 缓存过期时间（秒），默认 10 分钟
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self._ttl:
                logger.debug(f"News cache hit: {key}")
                return entry["data"]
            else:
                del self._cache[key]
                logger.debug(f"News cache expired: {key}")
        return None

    def set(self, key: str, data: Any) -> None:
        """设置缓存"""
        self._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        logger.debug(f"News cache set: {key}")

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("News cache cleared")


# 全局缓存实例
_news_cache = NewsCache(ttl=600)


def get_news_cache() -> NewsCache:
    """获取全局新闻缓存实例"""
    return _news_cache


def clear_news_cache() -> None:
    """清空所有新闻缓存"""
    _news_cache.clear()


# 新闻分类
NEWS_CATEGORIES = {
    "macro": "宏观政策",
    "industry": "行业动态",
    "company": "公司新闻",
    "market": "市场分析",
    "economy": "经济数据",
    "forex": "外汇",
    "commodity": "大宗商品",
    "crypto": "加密货币",
    "other": "其他"
}


class NewsService:
    """财经新闻服务类"""

    def __init__(self, use_cache: bool = True):
        """
        初始化新闻服务

        Args:
            use_cache: 是否使用缓存
        """
        self.use_cache = use_cache
        self.cache = _news_cache
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        params = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{prefix}:{params}"

    def _fetch_from_sina(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        从新浪财经获取新闻

        Args:
            symbol: 股票代码（可选）

        Returns:
            新闻列表
        """
        news_list = []

        try:
            # 新浪财经新闻接口
            url = "https://finance.sina.com.cn/stock/"
            if symbol:
                # 个股新闻
                url = f"https://finance.sina.com.cn/stock/quote/{symbol}.html"

            # 使用财经新闻频道
            urls = [
                ("https://finance.sina.com.cn/stock/", "market"),
                ("https://finance.sina.com.cn/money/", "market"),
                ("https://finance.sina.com.cn/chanjing/", "industry"),
                ("https://finance.sina.com.cn/tech/", "industry"),
            ]

            for news_url, category in urls:
                try:
                    response = self._session.get(news_url, timeout=10)
                    if response.status_code == 200:
                        # 解析新闻（简化处理，实际需要更复杂的解析）
                        content = response.text
                        # 提取新闻标题和链接的正则
                        pattern = r'<a href="(https?://finance\.sina\.com\.cn/[^"]+)"[^>]*>([^<]+)</a>'
                        matches = re.findall(pattern, content)

                        for url, title in matches[:20]:
                            if "news" in title or "股" in title or "市" in title or "财" in title:
                                news_list.append({
                                    "title": title.strip(),
                                    "url": url,
                                    "source": "新浪财经",
                                    "category": category,
                                    "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "summary": title.strip()[:100]
                                })
                except Exception as e:
                    logger.warning(f"Failed to fetch from {news_url}: {e}")

        except Exception as e:
            logger.error(f"Failed to fetch from Sina: {e}")

        return news_list

    def _fetch_from_eastmoney(self) -> List[Dict[str, Any]]:
        """
        从东方财富获取新闻

        Returns:
            新闻列表
        """
        news_list = []

        try:
            # 东方财富财经新闻接口
            url = "https://news.eastmoney.com/"
            response = self._session.get(url, timeout=10)

            if response.status_code == 200:
                content = response.text
                # 提取新闻标题和链接
                pattern = r'<a href="(https?://news\.eastmoney\.com/[^"]+)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, content)

                for url, title in matches[:30]:
                    # 过滤有效新闻
                    if len(title) > 5 and ("股" in title or "市" in title or "财" in title or
                                           "经" in title or "经" in title or "策" in title or "数据" in title):
                        news_list.append({
                            "title": title.strip(),
                            "url": url,
                            "source": "东方财富",
                            "category": "market",
                            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "summary": title.strip()[:100]
                        })

        except Exception as e:
            logger.error(f"Failed to fetch from Eastmoney: {e}")

        return news_list

    def _fetch_from_tencent(self) -> List[Dict[str, Any]]:
        """
        从腾讯财经获取新闻

        Returns:
            新闻列表
        """
        news_list = []

        try:
            # 腾讯财经新闻接口
            url = "https://finance.qq.com/"
            response = self._session.get(url, timeout=10)

            if response.status_code == 200:
                content = response.text
                # 提取新闻标题和链接
                pattern = r'<a href="(https?://finance\.qq\.com/a/\d+[^"]+)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, content)

                for url, title in matches[:20]:
                    if len(title) > 5:
                        news_list.append({
                            "title": title.strip(),
                            "url": url,
                            "source": "腾讯财经",
                            "category": "market",
                            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "summary": title.strip()[:100]
                        })

        except Exception as e:
            logger.error(f"Failed to fetch from Tencent: {e}")

        return news_list

    def get_latest_news(
        self,
        category: Optional[str] = None,
        limit: int = 50,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取最新财经新闻

        Args:
            category: 新闻分类，可选值见 NEWS_CATEGORIES
            limit: 返回数量限制
            symbol: 股票代码（可选，获取该股票相关新闻）

        Returns:
            新闻列表
        """
        # 生成缓存键
        cache_key = self._get_cache_key(
            "news:latest",
            category=category or "all",
            limit=limit,
            symbol=symbol or "all"
        )

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                # 应用分类和数量限制
                return self._filter_news(cached_data, category, limit, symbol)

        # 从多个源获取新闻
        all_news = []

        # 并行获取各源新闻
        sina_news = self._fetch_from_sina(symbol)
        all_news.extend(sina_news)

        eastmoney_news = self._fetch_from_eastmoney()
        all_news.extend(eastmoney_news)

        tencent_news = self._fetch_from_tencent()
        all_news.extend(tencent_news)

        # 去重（基于标题）
        seen_titles = set()
        unique_news = []
        for news in all_news:
            title_hash = hashlib.md5(news["title"].encode()).hexdigest()
            if title_hash not in seen_titles:
                seen_titles.add(title_hash)
                unique_news.append(news)

        # 按时间排序
        unique_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        # 设置缓存
        if self.use_cache and unique_news:
            self.cache.set(cache_key, unique_news)

        # 应用过滤
        return self._filter_news(unique_news, category, limit, symbol)

    def _filter_news(
        self,
        news_list: List[Dict[str, Any]],
        category: Optional[str] = None,
        limit: int = 50,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        过滤新闻

        Args:
            news_list: 原始新闻列表
            category: 新闻分类
            limit: 返回数量
            symbol: 股票代码

        Returns:
            过滤后的新闻列表
        """
        filtered = news_list

        # 按分类过滤
        if category:
            filtered = [n for n in filtered if n.get("category") == category]

        # 按股票代码过滤（简单关键词匹配）
        if symbol:
            symbol_normalized = symbol.replace("sh", "").replace("sz", "").replace("bj", "")
            filtered = [
                n for n in filtered
                if symbol_normalized in n.get("title", "") or
                   symbol in n.get("title", "")
            ]

        return filtered[:limit]

    def search_news(
        self,
        keyword: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        搜索新闻

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            匹配的新闻列表
        """
        if not keyword or len(keyword) < 2:
            return []

        # 生成缓存键
        cache_key = self._get_cache_key("news:search", keyword=keyword, limit=limit)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data[:limit]

        # 获取最新新闻
        all_news = self.get_latest_news(limit=200)

        # 关键词匹配
        keyword_lower = keyword.lower()
        matching_news = [
            news for news in all_news
            if keyword_lower in news.get("title", "").lower() or
               keyword_lower in news.get("summary", "").lower()
        ]

        # 按相关度排序（标题中匹配越靠前越相关）
        matching_news.sort(
            key=lambda x: (
                0 if x.get("title", "").lower().startswith(keyword_lower) else 1,
                0 if keyword_lower in x.get("title", "").lower() else 1
            )
        )

        result = matching_news[:limit]

        # 设置缓存
        if self.use_cache:
            self.cache.set(cache_key, result)

        return result

    def get_hot_keywords(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门关键词

        Args:
            limit: 返回数量

        Returns:
            热门关键词列表
        """
        # 获取最新新闻，提取关键词
        news_list = self.get_latest_news(limit=100)

        # 简单的关键词提取
        word_count = defaultdict(int)

        # 常见的股票市场关键词
        keywords = [
            "A股", "股市", "大盘", "创业板", "科创板", "上证", "深证",
            "涨停", "跌停", "涨幅", "跌幅", "成交量", "成交额",
            "加息", "降息", "IPO", "上市", "退市", "并购", "重组",
            "财报", "业绩", "盈利", "亏损", "分红", "送股",
            "政策", "监管", "证监会", "银保监会", "央行",
            "新能源", "芯片", "人工智能", "医药", "银行", "房地产"
        ]

        for news in news_list:
            title = news.get("title", "")
            for kw in keywords:
                if kw in title:
                    word_count[kw] += 1

        # 转换为列表并排序
        hot_keywords = [
            {"keyword": k, "count": v}
            for k, v in word_count.items()
        ]
        hot_keywords.sort(key=lambda x: x["count"], reverse=True)

        return hot_keywords[:limit]

    def get_news_by_date(
        self,
        date: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取指定日期的新闻

        Args:
            date: 日期，格式 YYYY-MM-DD
            limit: 返回数量限制

        Returns:
            新闻列表
        """
        # 生成缓存键
        cache_key = self._get_cache_key("news:date", date=date, limit=limit)

        # 尝试从缓存获取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        # 获取新闻
        news_list = self.get_latest_news(limit=200)

        # 按日期过滤
        filtered = [
            news for news in news_list
            if news.get("published_at", "").startswith(date)
        ]

        result = filtered[:limit]

        # 设置缓存
        if self.use_cache:
            self.cache.set(cache_key, result)

        return result


# 全局服务实例
_default_service: Optional[NewsService] = None


def get_news_service() -> NewsService:
    """获取默认的新闻服务实例"""
    global _default_service
    if _default_service is None:
        _default_service = NewsService(use_cache=True)
    return _default_service


def get_news_categories() -> Dict[str, str]:
    """获取新闻分类映射"""
    return NEWS_CATEGORIES.copy()
