"""
政策与新闻自动搜索

通过 OpenRouter/Perplexity 搜索全国跨境电商相关政策及新闻，集中展示。
"""

import json
import re
from typing import Any

from config import settings

# OpenRouter 兼容 OpenAI API
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
PERPLEXITY_MODEL = "perplexity/sonar-pro"


async def search_policies_and_news(query: str = "中国跨境电商 政策 新闻 2024 2025 最新") -> list[dict[str, Any]]:
    """
    使用 Perplexity/OpenRouter 搜索政策与新闻，返回结构化列表。
    """
    api_key = settings.perplexity_api_key or settings.openrouter_api_key
    if not api_key:
        return []

    prompt = f"""请搜索并列出中国最新的跨境电商相关政策及网络热点新闻（2024-2025年）。

要求：
1. 政策：覆盖全国各省（31省）及地级市以上综试区、国务院、商务部、海关总署、税务总局、财政部等来源
2. 热点：亿邦动力、雨果跨境、36氪、虎嗅、财新等媒体上的跨境电商行业热点
3. 返回 15-25 条，政策与新闻混合
每条必须包含：title（标题）、source（来源机构/省份/媒体）、url（官方或媒体链接）、date（发布日期）、summary（50字内摘要）、category（出口退税/物流/合规/补贴/监管/综合 之一

严格按以下 JSON 数组格式返回，不要其他文字：
[
  {{"title":"","source":"","url":"","date":"","summary":"","category":""}},
  ...
]"""

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE,
        )
        r = await client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        text = r.choices[0].message.content or ""
        return _parse_search_result(text)
    except Exception:
        return []


def _parse_search_result(text: str) -> list[dict[str, Any]]:
    """从 LLM 返回中解析 JSON 数组"""
    try:
        # 提取 [...]
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            arr = json.loads(text[start:end])
            if isinstance(arr, list):
                return [
                    {
                        "id": f"search-{i}",
                        "title": str(x.get("title", ""))[:100],
                        "source": str(x.get("source", "")),
                        "url": str(x.get("url", "")),
                        "publish_date": str(x.get("date", "")),
                        "category": str(x.get("category", "综合")),
                        "content": str(x.get("summary", "")),
                        "tags": [],
                    }
                    for i, x in enumerate(arr)
                    if x.get("title")
                ]
    except Exception:
        pass
    return []


async def search_country_ecommerce_policy(country: str) -> list[dict[str, Any]]:
    """
    搜索指定国家/地区的电子商务/跨境电商政策（丝路电商伙伴国等），返回结构化列表。
    """
    api_key = settings.perplexity_api_key or settings.openrouter_api_key
    if not api_key:
        return []

    prompt = f"""请搜索「{country}」的电子商务、跨境电商相关法律、法规、政策与监管动态（中英文来源均可）。

要求：
1. 该国/地区官方或权威媒体发布的电商法、跨境电商监管、数字贸易、消费者保护等政策
2. 返回 5-15 条，每条必须包含：title（标题）、source（来源机构/媒体）、url（可访问的链接）、date（发布日期或年份）、summary（80字内摘要）、category（清关合规/财税合规/支付合规/数据跨境/知识产权/监管/综合 之一）
3. 若为外文标题可保留原文并附简短中文说明

严格按以下 JSON 数组格式返回，不要其他文字：
[
  {{"title":"","source":"","url":"","date":"","summary":"","category":""}},
  ...
]"""

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE)
        r = await client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        text = r.choices[0].message.content or ""
        rows = _parse_search_result(text)
        for x in rows:
            x["country"] = country
        return rows
    except Exception:
        return []


async def search_media_douyin_kuaishou() -> list[dict[str, Any]]:
    """
    通过 Perplexity/OpenRouter 搜索「抖音」「快手」上与跨境电商相关的热点标题与链接，
    供媒体爬虫入库，标记为 platform=douyin / kuaishou（无需 Playwright）。
    """
    api_key = settings.perplexity_api_key or settings.openrouter_api_key
    if not api_key:
        return []

    prompt = """请搜索近期抖音、快手上与「跨境电商」「跨境出口」「海外仓」「Temu」「Shein」相关的热门视频或话题。

要求：
1. 返回 8–15 条，每条必须包含：title（视频/话题标题或描述）、source（抖音或快手）、url（可访问的链接，可为搜索页或视频页）、date（发布日期或「近期」）、summary（50字内摘要）
2. title 和 summary 需为中文或可理解的中文描述
3. 若无法获取真实链接，url 可填抖音搜索页 https://www.douyin.com/search/跨境电商 或快手搜索页 https://www.kuaishou.com/search/跨境电商

严格按以下 JSON 数组格式返回，不要其他文字：
[
  {"title":"","source":"抖音","url":"","date":"","summary":""},
  {"title":"","source":"快手","url":"","date":"","summary":""},
  ...
]"""

    try:
        from openai import AsyncOpenAI
        from datetime import datetime, timezone
        client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE)
        r = await client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        text = r.choices[0].message.content or ""
        start, end = text.find("["), text.rfind("]") + 1
        if start < 0 or end <= start:
            return []
        arr = json.loads(text[start:end])
        if not isinstance(arr, list):
            return []
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out = []
        for x in arr:
            title = str(x.get("title", "")).strip()[:200]
            source = str(x.get("source", "")).strip()
            platform = "douyin" if "抖音" in source else "kuaishou" if "快手" in source else "news"
            url = str(x.get("url", "")).strip() or ("https://www.douyin.com/search/跨境电商" if platform == "douyin" else "https://www.kuaishou.com/search/跨境电商")
            summary = str(x.get("summary", ""))[:500]
            if not title:
                continue
            out.append({
                "platform": platform,
                "title": title,
                "url": url,
                "author": source,
                "publish_date": str(x.get("date", ""))[:20],
                "content_snippet": summary or title[:500],
                "keywords": "跨境电商",
                "heat_score": 0,
                "crawled_at": now,
            })
        return out
    except Exception:
        return []
