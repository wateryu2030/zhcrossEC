"""
LLM 服务：支持百度千帆、OpenAI
"""

import json
from typing import Any

from config import settings

# 尝试导入 openai
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


def _get_client() -> "AsyncOpenAI | None":
    if not AsyncOpenAI:
        return None
    if settings.llm_provider == "baidu" and settings.baidu_api_key:
        base = settings.baidu_api_base or "https://qianfan.baidubce.com/v2"
        return AsyncOpenAI(api_key=settings.baidu_api_key, base_url=base)
    if settings.llm_provider == "zhipu" and settings.zhipu_api_key:
        return AsyncOpenAI(
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_api_base or "https://open.bigmodel.cn/api/paas/v4",
        )
    if settings.openai_api_key:
        return AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base or "https://api.openai.com/v1",
        )
    return None


async def chat_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> str:
    """
    调用 LLM 生成回复。
    """
    client = _get_client()
    if not client:
        return _mock_response(messages)

    model = model or (
        settings.baidu_model_id
        if settings.llm_provider == "baidu"
        else settings.zhipu_model_id
        if settings.llm_provider == "zhipu"
        else "gpt-4o-mini"
    )
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return _mock_response(messages)


def _mock_response(messages: list[dict[str, str]]) -> str:
    """未配置 LLM 或调用失败时返回提示，不再返回示范内容。"""
    return json.dumps(
        {
            "summary": "未配置 LLM 或调用失败。请在 .env 中配置 ZHIPU_API_KEY、BAIDU_API_KEY 或 OPENAI_API_KEY 后重试。",
            "impact_points": [],
            "suggestions": ["配置 API Key 后可使用政策分析、各地特点 AI 分析等功能"],
        },
        ensure_ascii=False,
    )
