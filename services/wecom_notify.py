"""
企业微信通知：新政策、政策分析等与飞书并列推送

需在 .env 配置：
- WECOM_CORP_ID：企业 ID（管理后台「我的企业」- 企业信息）
- WECOM_AGENT_ID：应用 ID（应用详情页）
- WECOM_AGENT_SECRET：应用 Secret
- WECOM_TO_USER：接收人，默认 @all；可填指定 userid，多个用 | 分隔

API 文档：https://developer.work.weixin.qq.com/document/path/91039（token）、94677（发送消息）
"""

import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

WECOM_API = "https://qyapi.weixin.qq.com/cgi-bin"


def get_access_token() -> Optional[str]:
    """获取企业微信应用 access_token。"""
    cid = (settings.wecom_corp_id or "").strip()
    secret = (settings.wecom_agent_secret or "").strip()
    if not cid or not secret:
        return None
    try:
        r = httpx.get(
            f"{WECOM_API}/gettoken",
            params={"corpid": cid, "corpsecret": secret},
            timeout=10.0,
        )
        data = r.json()
        if data.get("errcode") == 0:
            return data.get("access_token")
        logger.warning("wecom token failed: errcode=%s errmsg=%s", data.get("errcode"), data.get("errmsg"))
        return None
    except Exception as e:
        logger.warning("wecom token error: %s", e)
        return None


def send_text(content: str) -> bool:
    """
    发送文本应用消息。接收人由 WECOM_TO_USER 控制（默认 @all）。
    """
    token = get_access_token()
    if not token:
        return False
    agent_id = (settings.wecom_agent_id or "").strip()
    if not agent_id:
        logger.warning("WECOM_AGENT_ID 未配置")
        return False
    to_user = (settings.wecom_to_user or "").strip() or "@all"
    # 企业微信文本 content 最长 2048 字节（非字符）
    try:
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > 2048:
            content = content_bytes[:2048].decode("utf-8", errors="ignore")
    except Exception:
        content = content[:680]
    try:
        body = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": int(agent_id) if agent_id.isdigit() else agent_id,
            "text": {"content": content},
            "safe": 0,
        }
        r = httpx.post(
            f"{WECOM_API}/message/send",
            params={"access_token": token},
            json=body,
            timeout=10.0,
        )
        data = r.json()
        if data.get("errcode") == 0:
            logger.info("wecom notify sent to %s", to_user)
            return True
        logger.warning("wecom send failed: errcode=%s errmsg=%s", data.get("errcode"), data.get("errmsg"))
        return False
    except Exception as e:
        logger.warning("wecom send error: %s", e)
        return False


def notify_new_policies(count: int, sample_titles: list[str], dashboard_url: str = "http://localhost:8000") -> bool:
    """新政策入库后推送（与飞书逻辑一致）。"""
    lines = [f"CPG-Hub 新增 {count} 条政策，请查看。", f"预览：{dashboard_url}"]
    if sample_titles:
        lines.append("部分标题：")
        for t in sample_titles[:5]:
            lines.append(f"・{(t or '')[:60]}")
    return send_text("\n".join(lines))


def notify_policy_analysis(
    summary: str,
    directions: list[str],
    action_items: list[str],
    dashboard_url: str = "http://localhost:8000",
) -> bool:
    """将政策 AI 分析结果推送到企业微信（与飞书逻辑一致）。"""
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
    return send_text(text[:2048])
