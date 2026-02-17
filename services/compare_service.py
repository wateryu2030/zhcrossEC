"""
海外 vs 国内 对比服务

从 Amazon 抓取热销品价格，在百度优选搜索同款，计算差价。
"""

from typing import Any

from agents.baidu_agent import (
    get_price_comparison,
    get_user_reviews_analysis,
    search_products,
)
from services.overseas_scraper import get_amazon_product


def _extract_asin(url_or_asin: str) -> str:
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


async def compare_amazon_with_domestic(
    amazon_url_or_asin: str,
) -> dict[str, Any]:
    """
    输入 Amazon 链接或 ASIN，在百度优选找同款并对比。
    """
    asin = _extract_asin(amazon_url_or_asin)

    # 1. 获取海外价格（真实 API；未配置或失败时返回错误信息）
    overseas_data = await get_amazon_product(asin)
    if overseas_data.get("error"):
        return {
            "error": overseas_data.get("error"),
            "overseas": None,
            "domestic_products": [],
            "price_diff": 0,
            "recommendation": "请配置 OMKAR_CLOUD_API_KEY 后重试",
        }
    overseas_price = float(
        overseas_data.get("current_price")
        or overseas_data.get("price")
        or overseas_data.get("original_price")
        or 0
    )
    title = (
        overseas_data.get("product_name")
        or overseas_data.get("title")
        or "Unknown Product"
    )
    rating = float(overseas_data.get("rating") or 0)
    reviews = int(overseas_data.get("reviews") or 0)

    overseas = {
        "price": overseas_price,
        "title": title,
        "asin": asin,
        "rating": rating,
        "reviews": reviews,
        "link": overseas_data.get("link", f"https://www.amazon.com/dp/{asin}"),
        "currency": overseas_data.get("currency", "USD"),
    }

    # 2. 百度优选搜索同款
    search_result = await search_products(title, limit=5)
    domestic_products = search_result.get("products", [])

    # 3. 对每个同款取最低价
    domestic_prices = []
    for p in domestic_products:
        pid = p.get("id", "")
        price_val = p.get("price")
        if price_val is not None:
            domestic_prices.append(float(price_val))
        elif pid:
            pc = await get_price_comparison(pid)
            lp = pc.get("lowest_price")
            if lp is not None:
                domestic_prices.append(float(lp))

    min_domestic = min(domestic_prices) if domestic_prices else 0
    price_diff = overseas_price - min_domestic

    # 4. 口碑得分（取第一个同款）
    reputation_score = 0.8
    if domestic_products:
        rev = await get_user_reviews_analysis(domestic_products[0].get("id", "p1"))
        reputation_score = float(rev.get("score", 0.8))

    # 5. 推荐结论
    score = (overseas_price * 0.7 - min_domestic) * reputation_score
    if score > 20 and price_diff > 10:
        recommendation = "适合出海"
    elif price_diff > 0:
        recommendation = "有差价，可小批量试销"
    else:
        recommendation = "差价不足，建议观望"

    return {
        "overseas": overseas,
        "domestic_products": domestic_products,
        "baidu_source": "百度优选",  # 国内同款来自百度优选 Skill
        "price_diff": round(price_diff, 2),
        "min_domestic_price": min_domestic,
        "selection_score": round(score, 2),
        "recommendation": recommendation,
    }
