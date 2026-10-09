"""
政策洞察任务：基于数据库与法务政策库生成「方向性思考与行动建议」并入库、展示、飞书推送。

当有政策更新后，本任务会对数据库现有政策进行分析，给出建议：1）写入 policy_analysis 表供前端 AI 分析块展示；
2）通过飞书发送给 FEISHU_NOTIFY_OPEN_ID（如 8db735f2 余为军）。
"""

import json
import logging
from datetime import datetime, timezone

from agents.policy_legal import get_full_policy_library
from crawler.db import get_db, init_db, save_policy_analysis, list_policies
from services.llm_service import chat_completion

logger = logging.getLogger(__name__)

# 分析提示词：跨境电商政策分析专家（输出周报/日报格式，可微调数据范围与业务重点）
POLICY_INSIGHTS_PROMPT_TEMPLATE = """# 角色设定
你是一位资深的跨境电商战略与合规分析师。你有超过10年的行业经验，擅长从复杂的政策文本中提炼出对业务有直接影响的商业洞察。

# 任务背景
你需要基于我提供的数据库（以下简称「数据库」）中收集到的政策信息，进行自主分析。你的目标不是简单的翻译或摘要，而是**站在跨境电商卖家的角度**，分析这些政策对我们实际业务运营的影响。

# 数据来源
本次分析的数据源为：CPG-Hub 政策库（MySQL policy 表 + 法务政策库，含国内各省市及丝路电商伙伴国政策）。
数据范围涵盖：过去 3 个月内更新的所有政策文件。

# 分析任务与执行步骤
请严格按照以下步骤进行深度分析：

**第一步：政策分类与筛选**
1. 将数据库中的政策信息按地域（如：美国、欧盟、东南亚、拉美、中国各省市）进行分类。
2. 再按政策类型进行细分：关税变动、海关清关规则、增值税/消费税调整、产品合规认证（如CE/FCC/能效标签）、平台连带责任法案、环保税/包装法、数据隐私（如GDPR）、受限品类（如电子烟、锂电）等。

**第二步：关键变化识别**
1. 对比历史数据，识别出近期（如：最近1个月）发生了**实质性变化**的政策。
2. 特别关注：生效日在未来30-90天内的政策、惩罚性措施、以及针对中国卖家的特殊条款。

**第三步：业务影响评估**
针对上一步筛选出的关键变化，分析以下维度：
1. **成本影响**：是否会导致关税、税务成本或物流操作成本（如查验费）上升？
2. **运营合规风险**：是否需要更新产品标签、上传新的认证文件、调整海外仓库存？
3. **流量与转化**：政策变动是否会导致前台链接下架、隐藏发货时效或影响消费者信任度？
4. **机会洞察**：是否有政策变动（如某类目关税豁免）带来了新的市场机会？

# 数据输入（政策列表）
以下为数据库中的政策条目（标题、合规场景、风险等级及摘要），请基于此进行分析：

【政策列表】
{policy_list}

# 输出格式要求
请以 **【跨境电商业务提醒周报/日报】** 的形式输出，语言简洁干练，直接给出结论。格式如下：

---
### 📢 核心摘要
* **[一句话总结]**：本期共有X项政策变动需重点关注，其中Y项涉及成本增加，Z项涉及产品合规。

### ⚠️ 紧急行动清单（生效日 < 30天）
1. **[国家/地区] [政策名称]**：影响 [具体类目]。
   * **具体变化**：...
   * **必须执行的动作**：请在 [截止日期] 前完成 [上传认证/调整报价/更新标签]。
   * **业务建议**：...

### 🔍 重要趋势预警（生效日 30-90天）
1. **[国家/地区] [政策名称]**：
   * **走势分析**：...
   * **应对预案**：...

### 💡 长期战略提示
* **合规红利**：...
* **市场选择**：基于各国政策稳定性，建议重点关注哪个市场，或谨慎对待哪个市场。

### 📍 分省市/分国家要点（必填）
请按地域列出要点，便于用户快速按省市或目标国查询。格式示例：
* **中央/北京/上海/广东/浙江/…**：1–2 句该地近期政策侧重或风险提示。
* **欧盟/美国/东南亚/丝路伙伴国**：1–2 句该市场合规或关税要点。
若某地无数据，可写「暂无明显更新」。
---

# 特别指令
* 请务必区分「政策草案」和「已立法生效」的政策，不要引起不必要的恐慌。
* 如果数据不足或政策含义模糊，请直接指出「信息存疑，建议人工复核」，不要自行臆测。

请直接输出上述格式的周报内容，不要输出 JSON 或其他包装。"""


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

    text = "\n".join(lines)[:14000]
    prompt = POLICY_INSIGHTS_PROMPT_TEMPLATE.format(policy_list=text)

    try:
        resp = await chat_completion([{"role": "user", "content": prompt}])
        resp = (resp or "").strip()
        if not resp:
            logger.warning("policy_insights: empty response")
            return None
        summary = resp
        directions: list = []
        action_items: list = []
        if resp.startswith("{") and "}" in resp:
            try:
                start, end = resp.find("{"), resp.rfind("}") + 1
                data = json.loads(resp[start:end])
                summary = data.get("summary", resp)
                directions = data.get("directions", []) if isinstance(data.get("directions"), list) else []
                action_items = data.get("action_items", []) if isinstance(data.get("action_items"), list) else []
            except Exception:
                pass
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = {
            "scope": "all",
            "summary": summary[:50000],
            "directions": directions,
            "action_items": action_items,
            "source": "pipeline",
            "created_at": now,
        }
        with get_db() as conn:
            save_policy_analysis(conn, row)
        logger.info("policy_insights: saved analysis at %s", now)
        try:
            from config import settings as s
            if s.feishu_app_id and s.feishu_app_secret and s.feishu_notify_open_id:
                from services.feishu_notify import notify_policy_analysis
                notify_policy_analysis(
                    summary=row.get("summary", ""),
                    directions=row.get("directions") or [],
                    action_items=row.get("action_items") or [],
                )
        except Exception as fe:
            logger.warning("feishu policy_analysis notify failed: %s", fe)
        try:
            from config import settings as s
            if s.wecom_corp_id and s.wecom_agent_id and s.wecom_agent_secret:
                from services.wecom_notify import notify_policy_analysis as wecom_notify_analysis
                wecom_notify_analysis(
                    summary=row.get("summary", ""),
                    directions=row.get("directions") or [],
                    action_items=row.get("action_items") or [],
                )
        except Exception as we:
            logger.warning("wecom policy_analysis notify failed: %s", we)
        return row
    except Exception as e:
        logger.exception("policy_insights failed: %s", e)
        return None
