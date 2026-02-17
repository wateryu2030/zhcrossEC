"""
选品逻辑引擎

公式: Score = (Overseas_Price * 0.7 - Domestic_Price) * User_Reputation_Score

当 Score > Threshold 且符合当前 Policy 导向时，推送到前端看板。
"""

from typing import Any, Optional

from agents.baidu_agent import (
    get_price_comparison,
    get_user_reviews_analysis,
    search_products,
)
from services.overseas_scraper import get_amazon_product


async def run_selection_pipeline(
    amazon_asin: str,
    threshold: float = 0.0,
) -> list[dict[str, Any]]:
    """
    选品流水线：Amazon 商品 → 国内同款 → 得分 → 推荐列表
    """
    product = await get_amazon_product(amazon_asin)
    if product.get("error"):
        return []
    overseas_price = float(
        product.get("current_price") or product.get("price") or 0
    )
    title = product.get("product_name") or product.get("title") or ""

    search_result = await search_products(title, limit=5)
    products = search_result.get("products", [])

    recommendations = []
    for p in products:
        pid = p.get("id", "")
        domestic_price = float(p.get("price", 0))
        rev = await get_user_reviews_analysis(pid)
        rep_score = float(rev.get("score", 0.8))
        score = calculate_selection_score(
            overseas_price, domestic_price, rep_score
        )
        if should_recommend(score, threshold):
            recommendations.append(
                {
                    **p,
                    "selection_score": round(score, 2),
                    "overseas_price": overseas_price,
                    "reputation_summary": rev.get("summary", ""),
                }
            )

    return sorted(
        recommendations, key=lambda x: x.get("selection_score", 0), reverse=True
    )


def calculate_selection_score(
    overseas_price: float,
    domestic_price: float,
    user_reputation_score: float,
) -> float:
    """
    计算选品得分。

    Args:
        overseas_price: 海外售价
        domestic_price: 国内采购价
        user_reputation_score: 口碑得分 (0~1)

    Returns:
        选品得分
    """
    return (overseas_price * 0.7 - domestic_price) * user_reputation_score


def should_recommend(
    score: float,
    threshold: float = 0.0,
    policy_aligned: bool = True,
) -> bool:
    """
    判断是否应推送到前端看板。

    Args:
        score: 选品得分
        threshold: 得分阈值
        policy_aligned: 是否符合当前政策导向

    Returns:
        是否推荐
    """
    return score > threshold and policy_aligned
