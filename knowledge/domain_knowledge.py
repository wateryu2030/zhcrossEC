"""
跨境电商领域知识

- 监管代码：9610/9710/9810/1210 含义
- 政策术语：出口退税、海外仓、综试区等
- 选品经验：高潜力品类、价差判断
"""

from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
LEARNED_PATH = DATA_DIR / "learned_knowledge.json"

# 静态领域知识（深度学习基础）
POLICY_KNOWLEDGE = """
跨境电商监管代码：9610=零售出口B2C，9710=B2B出口，9810=海外仓出口，1210=保税进口。
出口退税：9610/9710/9810模式下六个月内退货可免征进口税；9810离境即退税；A类企业45天退税。
综试区：杭州、广州、深圳、郑州、成都、宁波、重庆等165个城市，有海外仓补贴、物流补贴。
海外仓：取消备案要求；先查验后装运试点12关；跨关区退货20关。
合规：数据标识规范、碳排放证明、知识产权备案。
"""

SELECTION_KNOWLEDGE = """
选品公式：Score = (Overseas*0.7 - Domestic) * Reputation。海外价低于国内同款有利润空间。
高潜力品类：消费电子(耳机/充电宝)、家居(台灯/收纳)、美妆工具、厨房小件、运动健身。
价差判断：差价>15美元高潜力，5-15美元中等，<5美元观望。拼多多常为国内最低价。
"""


def _load_learned() -> dict:
    """加载学习到的知识"""
    if LEARNED_PATH.exists():
        try:
            import json
            with open(LEARNED_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_policy_context() -> str:
    """政策分析时的领域上下文"""
    learned = _load_learned()
    cats = learned.get("policy_categories", [])
    tags = learned.get("policy_tags", [])
    extra = ""
    if cats:
        extra += f"\n近期政策分类: {', '.join(cats)}"
    if tags:
        extra += f"\n相关标签: {', '.join(tags[:20])}"
    return POLICY_KNOWLEDGE + extra


def get_selection_context() -> str:
    """选品分析时的领域上下文"""
    return SELECTION_KNOWLEDGE
