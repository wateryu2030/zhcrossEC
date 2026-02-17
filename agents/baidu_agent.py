"""
百度优选官方电商 Skill 集成

OpenClaw 百度优选 API 未公开时，使用 LLM 模拟国内商品检索与口碑分析。
接入真实 API 后替换实现即可。
"""

import json
from typing import Any, Optional

from services.llm_service import chat_completion


async def search_products(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    检索 CPS 商品库。当前用 LLM 模拟国内同款（结合选品领域知识）。
    """
    from knowledge.domain_knowledge import get_selection_context

    context = get_selection_context()
    prompt = f"""你是跨境电商选品助手。根据领域知识，为海外热销品寻找国内同款货源。

【选品知识】
{context}

【任务】根据海外商品关键词，列出 3-5 个国内电商（京东/天猫/拼多多）可能的同款，价格要合理。
关键词：{query}

【输出格式】纯 JSON：
{{"products":[{{"id":"p1","name":"商品名","price":99.9,"platform":"京东","url":"#","rating":4.5}}]}}
只返回 JSON。"""
    try:
        r = await chat_completion([{"role": "user", "content": prompt}])
        # 尝试解析 JSON
        if "{" in r:
            start = r.find("{")
            obj = json.loads(r[start : r.rfind("}") + 1])
            prods = obj.get("products", [])
            return {"source": "百度优选", "products": prods[:limit]}
    except Exception:
        pass
    # 默认模拟数据（标注来源：百度优选 Skill）
    return {
        "source": "百度优选",
        "products": [
            {"id": "p1", "name": f"{query} 同款 A", "price": 89.9, "platform": "京东", "url": "#"},
            {"id": "p2", "name": f"{query} 同款 B", "price": 79.9, "platform": "拼多多", "url": "#"},
            {"id": "p3", "name": f"{query} 同款 C", "price": 95.0, "platform": "天猫", "url": "#"},
        ]
    }


async def get_price_comparison(product_id: str) -> dict[str, Any]:
    """
    获取 SPU 在全网价格曲线。当前模拟。
    """
    return {
        "platforms": [
            {"name": "京东", "price": 89.9, "trend": "stable", "url": "#"},
            {"name": "天猫", "price": 92.0, "trend": "up", "url": "#"},
            {"name": "拼多多", "price": 79.9, "trend": "down", "url": "#"},
        ],
        "summary": "拼多多价格最低",
        "lowest_price": 79.9,
    }


async def get_user_reviews_analysis(product_id: str) -> dict[str, Any]:
    """
    AI 生成优缺点摘要。使用 LLM（结合选品知识）。
    """
    from knowledge.domain_knowledge import get_selection_context

    context = get_selection_context()
    prompt = f"""你是跨境电商选品助手。对商品做口碑分析，判断是否适合出海。

【选品知识】
{context}

【任务】对商品 ID {product_id} 做简短口碑分析。

【输出格式】纯 JSON：
{{"pros":["优点1","优点2"],"cons":["缺点1"],"score":0.85,"summary":"一句话总结，是否适合出海"}}
只返回 JSON。"""
    try:
        r = await chat_completion([{"role": "user", "content": prompt}])
        if "{" in r:
            start = r.find("{")
            return json.loads(r[start : r.rfind("}") + 1])
    except Exception:
        pass
    return {
        "pros": ["性价比高", "发货快"],
        "cons": ["部分评价提到包装一般"],
        "score": 0.82,
        "summary": "整体口碑良好，适合小批量试销。",
    }
