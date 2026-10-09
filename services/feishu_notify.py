"""
飞书通知：新政策时通知指定用户（如 余为军）

需在 .env 配置：
- FEISHU_APP_ID / FEISHU_APP_SECRET（应用凭证）
- FEISHU_NOTIFY_OPEN_ID（接收人的 open_id，可在飞书开放平台或「获取用户 ID」文档中查到）
"""

import json
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

FEISHU_API = "https://open.feishu.cn/open-apis"


def get_tenant_access_token() -> Optional[str]:
    """获取 tenant_access_token。"""
    if not settings.feishu_app_id or not settings.feishu_app_secret:
        return None
    try:
        r = httpx.post(
            f"{FEISHU_API}/auth/v3/tenant_access_token/internal",
            json={
                "app_id": settings.feishu_app_id,
                "app_secret": settings.feishu_app_secret,
            },
            timeout=10.0,
        )
        data = r.json()
        if data.get("code") == 0:
            return data.get("tenant_access_token")
        logger.warning("feishu token failed: %s", data)
        return None
    except Exception as e:
        logger.warning("feishu token error: %s", e)
        return None


def send_text_to_user(receive_id: str, text: str) -> bool:
    """
    发送文本消息给指定用户。receive_id 可为 open_id（以 ou_ 开头）或 user_id。
    文档: https://open.feishu.cn/document/server-docs/im-v1/message/create
    """
    token = get_tenant_access_token()
    if not token:
        return False
    if not receive_id:
        logger.warning("FEISHU_NOTIFY_OPEN_ID 未配置")
        return False
    receive_id_type = "open_id" if receive_id.strip().lower().startswith("ou_") else "user_id"
    try:
        r = httpx.post(
            f"{FEISHU_API}/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "receive_id": receive_id.strip(),
                "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
            timeout=10.0,
        )
        data = r.json()
        if data.get("code") == 0:
            logger.info("feishu notify sent to %s (%s)", receive_id[:8] + "...", receive_id_type)
            return True
        code = data.get("code")
        msg = data.get("msg") or str(data)
        logger.warning("feishu send failed: %s", data)
        if code == 99992351 or "open_id" in msg.lower() or "not exist" in msg.lower() or "invalid" in msg.lower():
            logger.warning(
                "飞书接收人 ID 无效或不存在，请确认 .env 中 FEISHU_NOTIFY_OPEN_ID 为余为军的 open_id（ou_ 开头）或 user_id（如 8db735f2）。"
            )
        return False
    except Exception as e:
        logger.warning("feishu send error: %s", e)
        return False


def notify_new_policies(count: int, sample_titles: list[str], dashboard_url: str = "http://localhost:8000") -> bool:
    """新政策入库后通知接收人（余为军等）。FEISHU_NOTIFY_OPEN_ID 可填 open_id（ou_ 开头）或 user_id（如 8db735f2）。"""
    receive_id = (settings.feishu_notify_open_id or "").strip()
    if not receive_id:
        return False
    lines = [f"CPG-Hub 新增 {count} 条政策，请查看。", f"预览：{dashboard_url}"]
    if sample_titles:
        lines.append("部分标题：")
        for t in sample_titles[:5]:
            lines.append(f"・{(t or '')[:60]}")
    text = "\n".join(lines)
    return send_text_to_user(receive_id, text)


def notify_policy_analysis(
    summary: str,
    directions: list[str],
    action_items: list[str],
    dashboard_url: str = "http://localhost:8000",
) -> bool:
    """将政策 AI 分析结果（方向与行动建议）发送给接收人（余为军 8db735f2）。"""
    receive_id = (settings.feishu_notify_open_id or "").strip()
    if not receive_id:
        return False
    lines = ["【CPG-Hub 政策分析】", f"预览：{dashboard_url}", ""]
    if summary:
        s = summary.strip()
        max_len = 3500
        if len(s) > max_len:
            s = s[:max_len] + "\n\n...(完整版请查看 CPG-Hub 政策分析页)"
        lines.append(s)
        lines.append("")
    if directions:
        lines.append("■ 方向性思考")
        for d in directions[:6]:
            lines.append(f"・{(d or '').strip()}")
        lines.append("")
    if action_items:
        lines.append("■ 行动建议")
        for a in action_items[:6]:
            lines.append(f"・{(a or '').strip()}")
    text = "\n".join(lines)
    return send_text_to_user(receive_id, text)
