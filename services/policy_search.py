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

    prompt = f"""请搜索并列出中国最新的跨境电商相关政策及新闻（2024-2025年）。

要求：返回 15-20 条，覆盖国务院、商务部、海关总署、税务总局、财政部、各地综试区等来源。
每条必须包含：title（标题）、source（来源机构）、url（官方链接，优先 gov.cn/mofcom.gov.cn/customs.gov.cn/chinatax.gov.cn）、date（发布日期）、summary（50字内摘要）、category（出口退税/物流/合规/补贴/监管/综合 之一）。

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
