"""
政策洞察任务：基于政策库与爬虫数据生成「方向性思考与行动建议」并入库
"""

import json
import logging
from datetime import datetime, timezone

from agents.policy_legal import get_full_policy_library
from crawler.db import get_db, init_db, save_policy_analysis, list_policies
from services.llm_service import chat_completion

logger = logging.getLogger(__name__)


async def run_policy_insights() -> dict | None:
    """
    聚合政策数据（DB + 法务库），调用 LLM 生成方向与建议，写入 policy_analysis 表。
    返回最新一条洞察或 None。
    """
    init_db()
    # 数据库政策
    db_policies = list_policies(limit=200)
    # 法务库政策（与 DB 按 url 去重）
    seen_urls = {p.get("url", "").strip() for p in db_policies if p.get("url")}
    library = get_full_policy_library()
    combined = list(db_policies)
    for p in library[:400]:
        url = (p.get("url") or "").strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            combined.append({
                "title": p.get("title", ""),
                "category": p.get("applicable_scenario", p.get("category", "")),
                "risk_level": p.get("risk_level", ""),
                "content_snippet": (p.get("content") or "")[:200],
            })

    if not combined:
        logger.warning("policy_insights: no policies to analyze")
        return None

    lines = []
    for i, p in enumerate(combined[:250], 1):
        title = p.get("title", "")
        scenario = p.get("category", p.get("applicable_scenario", ""))
        risk = p.get("risk_level", "")
        snippet = (p.get("content_snippet") or p.get("content") or "")[:120]
        lines.append(f"{i}. [{scenario}] {title}（风险{risk}） {snippet}")

    text = "\n".join(lines)
    prompt = f"""你是一位跨境电商政策与合规专家。根据以下政策列表（含合规场景与风险），给出「方向性的思考结果」与「行动建议」，供企业决策参考。

【政策列表】
{text[:14000]}

请严格按以下 JSON 格式输出，不要其他文字：
{{
  "summary": "200字内：当前政策环境整体方向与趋势概括",
  "directions": ["方向性思考1", "方向性思考2", "方向性思考3"],
  "action_items": ["行动建议1", "行动建议2", "行动建议3", "行动建议4"]
}}"""

    try:
        resp = await chat_completion([{"role": "user", "content": prompt}])
        if "{" not in resp:
            logger.warning("policy_insights: no JSON in response")
            return None
        start, end = resp.find("{"), resp.rfind("}") + 1
        data = json.loads(resp[start:end])
        summary = data.get("summary", "")
        directions = data.get("directions", [])
        action_items = data.get("action_items", [])
        if not summary and not directions and not action_items:
            return None
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = {
            "scope": "all",
            "summary": summary,
            "directions": directions if isinstance(directions, list) else [],
            "action_items": action_items if isinstance(action_items, list) else [],
            "source": "pipeline",
            "created_at": now,
        }
        with get_db() as conn:
            save_policy_analysis(conn, row)
        logger.info("policy_insights: saved analysis at %s", now)
        return row
    except Exception as e:
        logger.exception("policy_insights failed: %s", e)
        return None
