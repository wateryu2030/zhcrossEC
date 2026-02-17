"""
跨境政策动态监控 · 法务自用知识库

- 合规场景导向：清关/财税/支付/数据跨境/知识产权/行政处罚
- 权威数据源分层：核心强制、合规参考、辅助研判
- 自动搜索 + 多源采集 + 法务维度标引（效力、风险点、溯源性）
"""

import json
import re
from typing import Any

import httpx

from agents.policy_legal import (
    COMPLIANCE_SCENARIOS,
    get_full_policy_library,
    LEGAL_DATA_SOURCES,
    infer_scenario_from_text,
    infer_validity_level,
)
from services.llm_service import chat_completion
from services.policy_search import search_policies_and_news

# 兼容旧逻辑：category 与合规场景映射
POLICY_CATEGORIES = {s[0]: [] for s in COMPLIANCE_SCENARIOS}
POLICY_CATEGORIES["综合"] = []
# 对外暴露：种子 + 扩展库 1000+，兼容字段 category = applicable_scenario
def _build_policy_library() -> list[dict[str, Any]]:
    return [{**p, "category": p.get("applicable_scenario", "清关合规")} for p in get_full_policy_library()]


POLICY_LIBRARY: list[dict[str, Any]] = _build_policy_library()

# 多源政策页面（与法务数据源一致，用于爬虫）
POLICY_SOURCES = [{"name": s["name"], "url": s["url"]} for s in LEGAL_DATA_SOURCES]


def _categorize_policy(title: str, content: str) -> str:
    """按法务合规场景标引（一级分类）"""
    return infer_scenario_from_text(title, content, [])


async def fetch_policy_updates() -> list[dict[str, Any]]:
    """
    自动搜索全国政策及新闻，多源采集，集中展示。
    """
    results: list[dict[str, Any]] = []

    # 1. Perplexity/OpenRouter 搜索（覆盖全国政策与新闻）
    search_results = await search_policies_and_news()
    for r in search_results:
        if r.get("title") and r.get("url"):
            results.append(r)

    # 2. 官网抓取补充
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        for src in POLICY_SOURCES:
            try:
                r = await client.get(src["url"])
                if r.status_code == 200:
                    text = r.text[:12000]
                    links = re.findall(
                        r'<a[^>]+href="([^"]+)"[^>]*>([^<]{8,100})</a>',
                        text,
                    )
                    keywords = ["跨境", "电商", "出口", "退税", "海关", "商务", "保税", "海外仓"]
                    for href, link_text in links:
                        if any(kw in link_text for kw in keywords):
                            full_url = href if href.startswith("http") else src["url"].rstrip("/") + "/" + href.lstrip("/")
                            if not any(x.get("url") == full_url for x in results):
                                scenario = _categorize_policy(link_text, "")
                                results.append({
                                    "id": f"crawl-{len(results)}",
                                    "title": link_text.strip()[:80],
                                    "source": src["name"],
                                    "url": full_url,
                                    "publish_date": "",
                                    "category": scenario,
                                    "applicable_scenario": scenario,
                                    "validity_level": infer_validity_level(src["name"], link_text),
                                    "content": link_text[:300],
                                    "tags": [],
                                })
            except Exception:
                pass

    # 3. 合并政策库（去重）
    seen = {(p.get("title", ""), p.get("url", "")) for p in results}
    for p in POLICY_LIBRARY:
        key = (p.get("title", ""), p.get("url", ""))
        if key not in seen:
            results.append(p)
            seen.add(key)

    # 4. 按日期排序
    def sort_key(x):
        d = x.get("publish_date", "") or "0000"
        return d.replace("-", "")[::-1]

    results.sort(key=sort_key, reverse=True)
    return results[:25]


async def analyze_policy_impact(policy_content: str) -> dict[str, Any]:
    """LLM 跨境卖家侧影响分析（结合领域知识）"""
    from knowledge.domain_knowledge import get_policy_context

    context = get_policy_context()
    prompt = f"""你是一名跨境电商政策分析师。请结合以下领域知识，对政策做「跨境卖家侧」影响分析。

【领域知识】
{context}

【输出格式】纯 JSON：
{{"summary":"150字内","impact_points":["影响1","影响2","影响3"],"suggestions":["建议1","建议2"],"risk_level":"低/中/高"}}

【政策原文】
{policy_content[:2500]}

只返回 JSON，不要其他文字。"""
    try:
        r = await chat_completion([{"role": "user", "content": prompt}])
        if "{" in r:
            start, end = r.find("{"), r.rfind("}") + 1
            return json.loads(r[start:end])
    except Exception:
        pass
    return {
        "summary": "建议关注出口退税、物流补贴及合规要求。",
        "impact_points": ["出口退税率", "物流成本", "合规备案"],
        "suggestions": ["关注政策更新", "提前调整供应链"],
        "risk_level": "中",
    }


async def get_policy_categories() -> list[dict[str, Any]]:
    """政策分类列表（法务合规场景 + 数量，数量含扩展库 1000+）"""
    all_policies = get_full_policy_library()
    counts: dict[str, int] = {}
    for p in all_policies:
        c = p.get("applicable_scenario", "清关合规")
        counts[c] = counts.get(c, 0) + 1
    return [
        {"id": sid, "name": sid, "description": desc, "count": counts.get(sid, 0)}
        for sid, desc in COMPLIANCE_SCENARIOS
    ]
