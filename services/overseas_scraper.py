"""
海外电商数据采集

- omkarcloud/amazon-scraper: REST API
- pyktok: TikTok（可选，需 playwright）
"""

from typing import Any, Optional

import httpx

from config import settings

AMAZON_SCRAPER_BASE = "https://amazon-scraper-api.omkar.cloud"


def _extract_asin(url_or_asin: str) -> str:
    """从 URL 或 ASIN 提取 ASIN"""
    s = url_or_asin.strip()
    if "amazon" in s.lower() and "/dp/" in s:
        parts = s.split("/dp/")
        if len(parts) >= 2:
            return parts[1].split("/")[0].split("?")[0]
    if "amazon" in s.lower() and "/gp/product/" in s:
        parts = s.split("/gp/product/")
        if len(parts) >= 2:
            return parts[1].split("/")[0].split("?")[0]
    if len(s) == 10 and s.isalnum():
        return s
    return s


async def get_amazon_product(
    asin: str,
    country_code: str = "US",
) -> dict[str, Any]:
    """
    获取 Amazon 产品详情（omkarcloud/amazon-scraper API）。
    """
    asin = _extract_asin(asin)
    key = settings.omkar_cloud_api_key
    if not key:
        return {"error": "未配置 OMKAR_CLOUD_API_KEY，请填写 .env 以获取真实商品详情", "asin": asin}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(
                f"{AMAZON_SCRAPER_BASE}/amazon/product-details",
                params={"asin": asin, "country_code": country_code},
                headers={"API-Key": key},
            )
            if r.status_code == 200:
                return r.json()
            return {"error": f"API 返回 {r.status_code}", "asin": asin}
        except Exception as e:
            return {"error": str(e), "asin": asin}


async def search_amazon(
    query: str,
    country_code: str = "US",
    sort_by: str = "best_sellers",
    page: int = 1,
) -> dict[str, Any]:
    """
    搜索 Amazon 产品。
    """
    key = settings.omkar_cloud_api_key
    if not key:
        return {"results": [], "error": "未配置 OMKAR_CLOUD_API_KEY，请填写 .env 以获取真实 Amazon 热销数据"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(
                f"{AMAZON_SCRAPER_BASE}/amazon/search",
                params={
                    "query": query,
                    "country_code": country_code,
                    "sort_by": sort_by,
                    "page": page,
                },
                headers={"API-Key": key},
            )
            if r.status_code == 200:
                return r.json()
            return {"results": [], "error": f"API 返回 {r.status_code}"}
        except Exception as e:
            return {"results": [], "error": str(e)}


def _mock_amazon_product(asin: str) -> dict[str, Any]:
    return {
        "asin": asin,
        "product_name": "Sample Product (Mock)",
        "current_price": 49.99,
        "original_price": 59.99,
        "rating": 4.5,
        "reviews": 1200,
        "link": f"https://www.amazon.com/dp/{asin}",
        "sales_volume": "1K+ bought in past month",
        "currency": "USD",
    }


def _mock_amazon_search(query: str) -> dict[str, Any]:
    return {
        "results": [
            {
                "title": f"{query} - Mock Result 1",
                "price": 39.99,
                "asin": "B0MOCK01",
                "rating": 4.3,
                "reviews": 500,
                "sales_volume": "500+ bought",
                "link": "https://www.amazon.com/dp/B0MOCK01",
            },
            {
                "title": f"{query} - Mock Result 2",
                "price": 29.99,
                "asin": "B0MOCK02",
                "rating": 4.0,
                "reviews": 200,
                "sales_volume": "200+ bought",
                "link": "https://www.amazon.com/dp/B0MOCK02",
            },
        ]
    }


async def get_tiktok_trending(
    hashtag: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """
    获取 TikTok 热门数据（pyktok）。可选，失败时返回空列表。
    """
    try:
        import pyktok as pyk
    except ImportError:
        return []

    try:
        import os
        import tempfile

        import pandas as pd

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            fn = f.name
        try:
            if hashtag:
                pyk.save_tiktok_multi_page(
                    hashtag,
                    ent_type="hashtag",
                    save_video=False,
                    metadata_fn=fn,
                )
            elif username:
                pyk.save_tiktok_multi_page(
                    username,
                    ent_type="user",
                    save_video=False,
                    metadata_fn=fn,
                )
            else:
                return []

            df = pd.read_csv(fn)
            return df.to_dict("records")
        finally:
            if os.path.exists(fn):
                os.unlink(fn)
    except Exception:
        return []
