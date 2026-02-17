"""
自动化同步任务

- 政策：拉取 fetch_policy_updates，合并到缓存
- 热销：拉取 trending API + OpenClaw/百度优选，更新 sample 缓存
- 持续积累：按间隔追加政策与热销，使内容不断增多
- 深度学习：从政策与热销中提取关键词，更新 knowledge
"""

import asyncio
import json
import logging
from pathlib import Path

from agents.policy_agent import fetch_policy_updates
from api.routes import _load_sync_cache, SYNC_CACHE_PATH
from services.overseas_scraper import search_amazon

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
KNOWLEDGE_PATH = DATA_DIR / "learned_knowledge.json"

# 内容上限：持续积累时保留更多条
POLICY_CAP = 25
TRENDING_CAP = 24
# 关键词轮询（OpenClaw/百度优选），用于持续积累热销与选品内容
ACCUMULATE_KEYWORDS = ["跨境电商 热销", "出口 选品", "海外仓 爆款"]


async def run_sync_policies() -> int:
    """同步政策数据，返回新增/更新数量"""
    try:
        policies = await fetch_policy_updates()
        data = _load_sync_cache()
        existing = {p.get("id") for p in data.get("policies", [])}
        new_count = sum(1 for p in policies if p.get("id") not in existing)
        # 合并：保留已有，补充新政策，上限 POLICY_CAP
        merged = data.get("policies", [])[:POLICY_CAP]
        for p in policies:
            if p.get("id") not in {x.get("id") for x in merged} and len(merged) < POLICY_CAP:
                merged.append({
                    "id": p.get("id", ""),
                    "title": p.get("title", ""),
                    "source": p.get("source", ""),
                    "url": p.get("url", ""),
                    "category": p.get("category", "综合"),
                    "publish_date": p.get("publish_date", ""),
                    "impact": {"summary": p.get("content", "")[:200]},
                    "baidu_related": {"source": "百度优选", "products": []},
                })
        data["policies"] = merged
        data["stats"] = data.get("stats", {}) | {"policy_count": len(merged)}
        _save_sync_cache(data)
        logger.info("sync_policies: %d policies, %d new", len(merged), new_count)
        return len(merged)
    except Exception as e:
        logger.warning("sync_policies failed: %s", e)
        return 0


def _is_mock_trending_item(o: dict) -> bool:
    """判断是否为 mock 数据，避免覆盖优质 demo"""
    title = (o.get("title") or "").lower()
    return "mock" in title or "sample" in title or not o.get("title")


async def run_sync_trending() -> int:
    """同步热销趋势，调用 Amazon + 百度优选。mock 数据不覆盖现有优质 demo。"""
    try:
        data = await search_amazon("best seller", sort_by="best_sellers")
        results = data.get("results", [])[:6]
        if not results:
            return 0

        # 若全部为 mock，不覆盖
        if all(_is_mock_trending_item(o) for o in results):
            logger.info("sync_trending: skip, all mock data")
            return 0

        from agents.baidu_agent import search_products

        items = []
        for o in results:
            if _is_mock_trending_item(o):
                continue
            title = o.get("title", "")
            price = float(o.get("price") or o.get("current_price") or 0)
            kw = (title[:40] if title else "热销商品").strip()
            baidu_res = await search_products(kw, limit=3)
            domestic = baidu_res.get("products", [])
            min_domestic = min((float(p.get("price") or 0) for p in domestic), default=0)
            price_diff = round(price - min_domestic, 2) if price else 0
            profit = "高" if price_diff > 15 else "中" if price_diff > 5 else "低"
            items.append({
                "overseas": {
                    "title": title,
                    "price": price,
                    "rating": o.get("rating"),
                    "reviews": o.get("reviews"),
                    "sales_volume": o.get("sales_volume", ""),
                    "link": o.get("link", "#"),
                    "badge": o.get("badge"),
                },
                "baidu_domestic": {"source": "百度优选", "products": domestic},
                "price_diff": price_diff,
                "overseas_price": price,
                "profit_potential": profit,
                "note": f"海外价 ${price}，国内最低 ¥{min_domestic}",
            })
            await asyncio.sleep(0.3)  # 限流

        if not items:
            return 0

        sample = _load_sync_cache()
        existing = sample.get("trending", [])
        # 保留非 mock 的现有项，新数据前置，上限 TRENDING_CAP
        existing_ok = [x for x in existing if not _is_mock_trending_item(x.get("overseas", {}))]
        sample["trending"] = (items + existing_ok)[:TRENDING_CAP]
        sample["stats"] = sample.get("stats", {}) | {
            "trending_count": len(sample["trending"]),
            "updated_at": "自动同步",
        }
        _save_sync_cache(sample)
        logger.info("sync_trending: %d items", len(items))
        return len(items)
    except Exception as e:
        logger.warning("sync_trending failed: %s", e)
        return 0


def _learn_from_data(sample: dict) -> dict:
    """从政策与热销数据中提取关键词，供 LLM 深度学习使用"""
    cats = set()
    tags = set()
    for p in sample.get("policies", []):
        cats.add(p.get("category", ""))
        for t in p.get("tags", []):
            tags.add(t)
    for t in sample.get("trending", []):
        o = t.get("overseas", {})
        title = (o.get("title") or "").lower()
        for kw in ["bluetooth", "wireless", "power bank", "led", "kitchen", "yoga", "makeup"]:
            if kw in title:
                tags.add(kw)
    return {
        "policy_categories": list(cats),
        "policy_tags": list(tags)[:50],
        "updated_at": __import__("datetime").datetime.now().isoformat()[:19],
    }


async def run_accumulate_content() -> dict:
    """
    持续积累内容：政策 + 热销 + OpenClaw/百度优选关键词轮询，追加到本地缓存，使首屏内容不断增多。
    """
    policies_count = await run_sync_policies()
    trending_count = await run_sync_trending()
    # 关键词轮询：用百度优选/OpenClaw 拉选品与热销，并入 trending
    added = 0
    try:
        from agents.baidu_agent import search_products
        sample = _load_sync_cache()
        existing = [x for x in sample.get("trending", []) if not _is_mock_trending_item(x.get("overseas", {}))]
        existing_titles = {str((t.get("overseas") or {}).get("title", "")).strip() for t in existing}
        new_items = []
        for kw in ACCUMULATE_KEYWORDS[:3]:
            try:
                res = await search_products(kw, limit=4)
                prods = (res.get("products") or [])[:4]
                for p in prods:
                    title = (p.get("name") or p.get("title") or "").strip()
                    if not title or title in existing_titles:
                        continue
                    existing_titles.add(title)
                    price = float(p.get("price") or 0)
                    new_items.append({
                        "overseas": {"title": title, "price": price, "link": p.get("url", "#"), "badge": "选品"},
                        "baidu_domestic": {"source": res.get("source", "百度优选"), "products": [p]},
                        "price_diff": 0,
                        "overseas_price": price,
                        "profit_potential": "中",
                        "note": f"关键词: {kw}",
                    })
                    added += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug("accumulate keyword %s: %s", kw, e)
        if new_items:
            sample = _load_sync_cache()
            existing = [x for x in sample.get("trending", []) if not _is_mock_trending_item(x.get("overseas", {}))]
            sample["trending"] = (new_items + existing)[:TRENDING_CAP]
            sample["stats"] = sample.get("stats", {}) | {
                "trending_count": len(sample["trending"]),
                "updated_at": "持续积累",
            }
            _save_sync_cache(sample)
            logger.info("accumulate_content: +%d from keywords, policies=%d, trending=%d", added, policies_count, trending_count)
    except Exception as e:
        logger.warning("run_accumulate_content keyword round: %s", e)
    return {"policies": policies_count, "trending": trending_count, "accumulated": True}


async def run_sync_all() -> dict:
    """全量同步：政策 + 热销 + 知识学习"""
    policies_count = await run_sync_policies()
    trending_count = await run_sync_trending()
    sample = _load_sync_cache()
    knowledge = _learn_from_data(sample)
    KNOWLEDGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, ensure_ascii=False, indent=2)
    logger.info("sync_all: policies=%d, trending=%d, knowledge updated", policies_count, trending_count)
    return {"policies": policies_count, "trending": trending_count, "knowledge": knowledge}


def _save_sync_cache(data: dict) -> None:
    """保存同步结果到真实数据缓存（合并保留 hot_categories、industry_news 等）"""
    SYNC_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_sync_cache()
    merged = {**existing, **data}
    for k in ("hot_categories", "industry_news", "analyze_samples"):
        if k in existing and k not in data:
            merged[k] = existing[k]
    with open(SYNC_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
