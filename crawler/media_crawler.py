"""
媒体热点爬虫

按日检索抖音、快手等媒体上与「跨境电商」相关的热点内容，入库。
参考设计：https://github.com/wateryu2030/ahotnews (BettaFish MindSpider / MediaCrawler)
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, quote

import httpx

from crawler.db import get_db, init_db, media_get_existing_urls, media_insert

logger = logging.getLogger(__name__)

# 检索关键词
MEDIA_KEYWORDS = ["跨境电商", "跨境出口", "海外仓", "Temu", "Shein", "亚马逊 中国卖家", "9610", "9710", "9810"]

# 有内文过滤：标题过短视为无实际内容；同轮按 URL 去重
MIN_TITLE_LEN = 10

# 媒体源：资讯站 + 新闻媒体 + 百度资讯（抖音/快手通过搜索 API 补充）
MEDIA_SOURCES = [
    {"platform": "news", "name": "亿邦动力跨境电商", "url": "https://www.ebrun.com/", "keywords": ["跨境", "电商", "出口"]},
    {"platform": "news", "name": "雨果跨境", "url": "https://www.cifnews.com/", "keywords": ["跨境"]},
    {"platform": "news", "name": "36氪", "url": "https://www.36kr.com/", "keywords": ["跨境", "电商", "出海"]},
    {"platform": "news", "name": "虎嗅", "url": "https://www.huxiu.com/", "keywords": ["跨境", "电商"]},
    {"platform": "web", "name": "百度资讯聚合", "url": "https://www.baidu.com/s?wd=" + quote("跨境电商 最新"), "keywords": ["跨境"]},
]

# 抖音、快手：公开搜索页或开放平台 API（需 token 时在 config 中配置）
DOUYIN_SEARCH_URL = "https://www.douyin.com/search/"  # 需 Cookie/Playwright
KUAISHOU_SEARCH_URL = "https://www.kuaishou.com/search/"  # 同上


def _extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """提取链接与标题，标题过短的不收（视为无实际内容）。"""
    out = []
    pat = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{4,200})</a>'
    for m in re.finditer(pat, html, re.I):
        href = m.group(1).strip()
        text = re.sub(r"\s+", " ", m.group(2)).strip()
        if len(text) < MIN_TITLE_LEN:
            continue
        if href.startswith("http"):
            url = href
        else:
            url = urljoin(base_url, href)
        if url and text and ("跨境" in text or "电商" in text or "出口" in text):
            out.append((url, text[:300]))
    return out


async def _crawl_news_site(source: dict[str, Any]) -> list[dict[str, Any]]:
    """爬取资讯站列表页，提取与跨境电商相关的标题与链接"""
    items = []
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(source["url"], headers={"User-Agent": "Mozilla/5.0 (compatible; CPG-Hub/1.0)"})
            if r.status_code != 200:
                return items
            html = r.text[:200000]
            base = source["url"]
            for url, title in _extract_links(html, base):
                if not any(kw in title for kw in source.get("keywords", ["跨境"])):
                    continue
                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                items.append({
                    "platform": source["platform"],
                    "title": title[:200],
                    "url": url,
                    "author": source.get("name", ""),
                    "publish_date": "",
                    "content_snippet": title[:500],
                    "keywords": "跨境电商",
                    "heat_score": 0,
                    "crawled_at": now,
                })
    except Exception as e:
        logger.warning("media crawl %s failed: %s", source.get("url"), e)
    return items


async def _fetch_douyin_hot() -> list[dict[str, Any]]:
    """
    抖音热点检索。
    正式环境可接入：抖音开放平台 API、或 Playwright 模拟搜索「跨境电商」。
    """
    # 占位：无开放 API 时返回空；后续可接 Playwright 或官方接口
    logger.info("douyin hot: placeholder (use Playwright or Douyin Open API to implement)")
    return []


async def _fetch_kuaishou_hot() -> list[dict[str, Any]]:
    """
    快手热点检索。
    正式环境可接入：快手开放平台 或 Playwright 模拟搜索。
    """
    logger.info("kuaishou hot: placeholder (use Playwright or Kuaishou API to implement)")
    return []


async def run_media_crawl() -> int:
    """
    执行一轮媒体热点爬取（按日调用）。
    采集资讯站 + 用户媒体链接(抖音/快手/财新/微博等) + 抖音/快手占位；结果写入 media_hot 表。
    """
    init_db()
    total = 0
    all_items: list[dict[str, Any]] = []

    # 资讯站
    for src in MEDIA_SOURCES:
        items = await _crawl_news_site(src)
        for it in items:
            it["platform"] = src.get("platform", "web")
        all_items.extend(items)

    # 抖音 / 快手：优先通过搜索 API 获取热点（无需 Playwright）
    try:
        from services.policy_search import search_media_douyin_kuaishou
        dy_ks = await search_media_douyin_kuaishou()
        all_items.extend(dy_ks)
        if dy_ks:
            logger.info("media_crawl: +%d from douyin/kuaishou search", len(dy_ks))
    except Exception as e:
        logger.warning("douyin/kuaishou search error: %s", e)
    try:
        douyin = await _fetch_douyin_hot()
        for it in douyin:
            it["platform"] = "douyin"
        all_items.extend(douyin)
    except Exception as e:
        logger.warning("douyin fetch error: %s", e)
    try:
        kuaishou = await _fetch_kuaishou_hot()
        for it in kuaishou:
            it["platform"] = "kuaishou"
        all_items.extend(kuaishou)
    except Exception as e:
        logger.warning("kuaishou fetch error: %s", e)

    # 按 URL 去重（同轮内重复链接只保留一条；并排除库中已有 URL，避免跨轮重复）
    by_url: dict[str, dict[str, Any]] = {}
    for row in all_items:
        u = (row.get("url") or "").strip()
        if u:
            by_url[u] = row
    with get_db() as conn:
        existing = media_get_existing_urls(conn)
    all_items = [r for r in by_url.values() if (r.get("url") or "").strip() not in existing]

    with get_db() as conn:
        for row in all_items:
            try:
                media_insert(conn, row)
                total += 1
            except Exception as e:
                logger.warning("media_insert error: %s", e)

    logger.info("media_crawl done: %d items (after title/url filter)", total)
    return total
