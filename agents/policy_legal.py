"""
跨境电商法务自用政策法规知识库 - 常量与分类

围绕「自用合规知识库」：精准性、溯源性、实用性、排他性。
- 一级分类：按合规场景（法务研判导向）
- 二级：目标国/地区；各地（region_label）用于 AI 特点分析
- 数据量：种子 50 + 扩展库 1000+ → 千条以上
"""

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EXPANDED_POLICY_PATH = DATA_DIR / "legal_policies_expanded.json"
_EXPANDED_CACHE: list[dict[str, Any]] | None = None

# 一、合规场景（一级分类，法务工作流导向）
COMPLIANCE_SCENARIOS = [
    ("清关合规", "海关申报、通关单证、9610/9710/9810、海外仓备案、跨关区退货"),
    ("财税合规", "出口退税、增值税、关税保证保险、退运免税、A类企业退税周期"),
    ("支付合规", "支付数据接入海关、跨境支付监管、结汇"),
    ("数据跨境合规", "数据出境、数据标识规范、个人信息保护"),
    ("知识产权合规", "备案、侵权处置、出口商品知识产权保护"),
    ("行政处罚合规", "信用等级、处罚条款、未申报处罚、违规后果"),
]

COMPLIANCE_SCENARIO_IDS = [s[0] for s in COMPLIANCE_SCENARIOS]

# 关键词 → 合规场景（用于自动标引）
SCENARIO_KEYWORDS: dict[str, list[str]] = {
    "清关合规": ["海关", "申报", "通关", "9610", "9710", "9810", "海外仓", "备案", "退货", "单证", "先查验后装运"],
    "财税合规": ["退税", "增值税", "关税", "税务", "退运", "免税", "A类", "申报退税", "离境"],
    "支付合规": ["支付", "数据接入", "结汇", "外汇"],
    "数据跨境合规": ["数据", "出境", "标识", "个人信息", "ERP", "数据质量"],
    "知识产权合规": ["知识产权", "备案", "侵权", "商标", "专利"],
    "行政处罚合规": ["处罚", "信用", "违规", "未申报", "监管", "公告"],
}

# 二、效力层级（法务溯源）
VALIDITY_LEVELS = ["法律", "行政法规", "部门规章", "通知", "公告", "指引", "规范性文件"]

# 三、风险等级（法务风险预判）
RISK_LEVELS = ["高", "中", "低"]
RISK_TAG_EXAMPLES = ["需备案", "需申报", "处罚条款", "时效要求", "违规处罚", "高风险-未申报处罚", "中风险-备案时效"]

# 效力判定关键词库（机器初判 + 法务复核用）
VALIDITY_KEYWORDS = {
    "施行": ["自XX日起施行", "本通知自", "本办法自", "本公告自", "自发布之日起施行"],
    "废止": ["废止", "同时废止", "原XX规定同时废止", "失效", "不再执行"],
    "修订": ["修订", "予以修订", "作如下修订", "修订背景", "因XX政策调整"],
}

# 目标国/地区（二级分类，法务检索用）
TARGET_REGIONS = ["中国", "欧盟", "美国", "其他"]
TARGET_REGION_IDS = ["中国", "欧盟", "美国", "其他"]

# 各地（用于「各地政策特点」AI 分析，与扩展库一致）
REGION_LABELS = [
    "全国", "杭州", "广州", "深圳", "宁波", "郑州", "成都", "重庆", "苏州", "青岛",
    "长沙", "合肥", "西安", "天津", "大连", "厦门", "南京", "无锡", "东莞", "佛山",
    "珠海", "济南", "武汉", "沈阳", "哈尔滨", "昆明", "南宁", "兰州", "乌鲁木齐",
    "石家庄", "太原", "南昌", "福州", "贵阳", "海口", "银川", "西宁", "呼和浩特", "拉萨",
    "欧盟", "美国", "英国", "日本", "东南亚",
]

# 四、数据源分层（法务级权威）
SOURCE_TIER_CORE = "核心强制"      # 海关/商务部/税务总局等，可作为合规依据
SOURCE_TIER_REFERENCE = "合规参考"  # 综试区、行业协会
SOURCE_TIER_AUX = "辅助研判"        # 白皮书、解读

# 法务级权威数据源清单：名称、URL、更新频率建议、效力层级、适用合规场景
LEGAL_DATA_SOURCES: list[dict[str, Any]] = [
    {"name": "海关总署", "url": "http://www.customs.gov.cn/", "tier": SOURCE_TIER_CORE, "scenarios": ["清关合规", "支付合规", "行政处罚合规"], "update": "触发+日检"},
    {"name": "商务部政策发布", "url": "https://www.mofcom.gov.cn/zwgk/zcfb/index.html", "tier": SOURCE_TIER_CORE, "scenarios": ["清关合规", "数据跨境合规", "行政处罚合规"], "update": "触发+日检"},
    {"name": "税务总局", "url": "https://www.chinatax.gov.cn/", "tier": SOURCE_TIER_CORE, "scenarios": ["财税合规"], "update": "触发+日检"},
    {"name": "中国政府网政策", "url": "https://www.gov.cn/zhengce/zuixin.htm", "tier": SOURCE_TIER_CORE, "scenarios": ["清关合规", "财税合规", "数据跨境合规", "知识产权合规"], "update": "日检"},
    {"name": "商务部电子商务司", "url": "https://dzsws.mofcom.gov.cn/", "tier": SOURCE_TIER_REFERENCE, "scenarios": ["数据跨境合规", "清关合规"], "update": "日检"},
    {"name": "国家知识产权局", "url": "https://www.cnipa.gov.cn/", "tier": SOURCE_TIER_CORE, "scenarios": ["知识产权合规"], "update": "周检"},
]


def infer_scenario_from_text(title: str, content: str, tags: list[str]) -> str:
    """根据标题、正文、标签推断合规场景（一级分类）"""
    text = (title + " " + content + " " + " ".join(tags or []))
    for scenario, kws in SCENARIO_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return scenario
    return "清关合规"  # 默认与跨境最相关


def infer_validity_level(source: str, title: str) -> str:
    """根据发布机构与标题推断效力层级"""
    t = (source or "") + (title or "")
    if "法" in t and ("条例" in t or "法律" in t):
        return "法律"
    if "条例" in t or "办法" in t:
        return "行政法规"
    if "公告" in t:
        return "公告"
    if "通知" in t:
        return "通知"
    if "指引" in t or "规范" in t:
        return "指引"
    if "总署" in t or "总局" in t or "部" in t:
        return "部门规章"
    return "规范性文件"


# 五、法务自用政策库（精准性、溯源性：发布机构+原文URL+效力+合规场景+风险点+目标国+废止/修订）
# 字段：id, title, source, url, publish_date, effective_date, repeal_date, content, tags,
#       applicable_scenario, target_region, validity_level, risk_level, risk_points, source_tier,
#       revision_notes(修订说明), validity_note(效力说明)
LEGAL_POLICY_LIBRARY: list[dict[str, Any]] = [
    # 清关合规 · 中国
    {"id": "pol-legal-001", "title": "海关总署公告2024年第167号（关于进一步促进跨境电商出口发展的公告）", "source": "海关总署",
     "url": "https://www.gov.cn/zhengce/zhengceku/202411/content_6989668.htm", "publish_date": "2024-11", "effective_date": "2024-11",
     "content": "取消海外仓备案、简化出口单证、扩大先查验后装运试点至12关、推广跨关区退货至20关。核心条款：跨境电商出口可采用简化申报。",
     "tags": ["海外仓", "9610", "9710", "9810", "先查验后装运"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["需按新单证要求申报", "跨关区退货需在试点关区"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-002", "title": "海关总署关于跨境电商零售进口商品退货有关监管事宜的公告", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2024-06", "effective_date": "2024-07",
     "content": "明确跨境电商零售进口退货流程、退货包裹入区要求及数据申报要求。未按规定申报退货的，按违规处理。",
     "tags": ["退货", "零售进口", "1210"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "高", "risk_points": ["需按规定申报退货", "违规将受处罚"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-003", "title": "海关总署公告2018年第179号（跨境电商平台支付数据接入）", "source": "海关总署",
     "url": "https://www.gov.cn/zhengce/zhengceku/2018-12/31/content_5447029.htm", "publish_date": "2018-12", "effective_date": "2019-01",
     "content": "跨境电商平台需通过API向海关实时提供支付相关原始数据。未接入或数据不实的，影响通关及后续监管。",
     "tags": ["数据接入", "支付"], "applicable_scenario": "支付合规", "validity_level": "公告",
     "risk_level": "高", "risk_points": ["需实时对接海关", "数据不实将承担后果"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-004", "title": "跨境电商企业信用等级管理办法", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2024-02", "effective_date": "2024-03",
     "content": "建立跨境电商企业信用等级（A/B/C等），A类企业享受快速通关、优先退税。信用等级与申报合规、历史违规挂钩。",
     "tags": ["信用", "A类", "通关"], "applicable_scenario": "行政处罚合规", "validity_level": "部门规章",
     "risk_level": "中", "risk_points": ["信用等级影响通关与退税时效", "违规将降级"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-005", "title": "郑州跨境电商综试区创新发展实施方案", "source": "河南省政府",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2024-03", "effective_date": "2024-04",
     "content": "依托郑州航空港，打造跨境电商物流枢纽，支持9610/9710/9810全模式。地方配套通关便利与补贴。",
     "tags": ["郑州", "综试区", "航空港"], "applicable_scenario": "清关合规", "validity_level": "规范性文件",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_REFERENCE},
    {"id": "pol-legal-006", "title": "宁波跨境电商综试区高质量发展若干措施", "source": "宁波市政府",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2024-07", "effective_date": "2024-08",
     "content": "支持宁波舟山港跨境电商出口，优化9610/9710通关流程。地方对海外仓、物流有补贴。",
     "tags": ["宁波", "舟山港", "9610"], "applicable_scenario": "清关合规", "validity_level": "规范性文件",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_REFERENCE},
    {"id": "pol-legal-007", "title": "广州跨境电商综试区高质量发展行动方案", "source": "广州市政府",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2024-05", "effective_date": "2024-06",
     "content": "推进保税展示、网购保税、直邮等模式，建设国际物流枢纽。涉及清关与保税监管。",
     "tags": ["综试区", "广州", "保税"], "applicable_scenario": "清关合规", "validity_level": "规范性文件",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_REFERENCE},
    # 财税合规
    {"id": "pol-legal-008", "title": "财政部 海关总署 税务总局关于延续实施跨境电子商务出口退运商品税收政策的公告", "source": "财政部、海关总署、税务总局",
     "url": "https://www.gov.cn/zhengce/zhengceku/202308/content_6901040.htm", "publish_date": "2023-08", "effective_date": "2023-08",
     "content": "出口退运商品税收政策延续至2025年12月31日。1210/9610/9710/9810项下退货免征进口税。核心条款：六个月内退运可享免税。",
     "tags": ["退运", "退税", "延续"], "applicable_scenario": "财税合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["时效：六个月", "需符合退运条件"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-009", "title": "国家税务总局关于支持跨境电商出口海外仓发展出口退（免）税有关事项的公告", "source": "国家税务总局",
     "url": "https://www.gov.cn/zhengce/202501/content_7001577.htm", "publish_date": "2025-01", "effective_date": "2025-02",
     "content": "9810出口海外仓货物离境即可申报退税；未销售货物按离境即退税、销售再核算处理。",
     "tags": ["9810", "海外仓", "退税"], "applicable_scenario": "财税合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["离境即退税", "需保留销售核算资料"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-010", "title": "关于优化跨境电商出口货物退税政策的公告", "source": "财政部、海关总署、税务总局",
     "url": "https://www.chinatax.gov.cn/", "publish_date": "2025-03", "effective_date": "2025-04",
     "content": "9610/9710/9810模式下六个月内退货可免征进口税并退税；A类企业45天退税。",
     "tags": ["9610", "9710", "9810", "退货"], "applicable_scenario": "财税合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["A类企业45天", "非A类2-4个月"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-011", "title": "出口商品国内环节税收管理优化公告", "source": "税务总局、财政部、商务部、海关总署",
     "url": "https://www.chinatax.gov.cn/", "publish_date": "2025-03", "effective_date": "2025-04",
     "content": "区分自营与委托出口，规范税务申报；标准退税周期2-4个月。委托出口需留存委托协议。",
     "tags": ["委托出口", "自营出口"], "applicable_scenario": "财税合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["委托出口需协议", "申报材料需完整"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-012", "title": "海关总署办公厅关于进一步优化海关税收服务 助力外贸质升量稳有关措施的通知", "source": "海关总署",
     "url": "https://www.gov.cn/zhengce/zhengceku/202409/content_7007182.htm", "publish_date": "2024-09", "effective_date": "2024-10",
     "content": "跨境电商零售进口担保领域应用关税保证保险，降低企业担保通关成本。",
     "tags": ["关税保证保险", "进口"], "applicable_scenario": "财税合规", "validity_level": "通知",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-013", "title": "离境退税政策优化以扩大入境消费", "source": "商务部等六部门",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2025-04", "effective_date": "2025-05",
     "content": "优化离境退税，扩大入境消费，涉及跨境电商进口便利化。",
     "tags": ["离境退税", "入境消费"], "applicable_scenario": "财税合规", "validity_level": "通知",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_CORE},
    # 数据跨境合规
    {"id": "pol-legal-014", "title": "《电子商务数据标识规范》行业标准征求意见", "source": "商务部电子商务司",
     "url": "https://dzsws.mofcom.gov.cn/gztz/", "publish_date": "2026-02", "effective_date": "",
     "content": "规范跨境电商数据标识与数据质量核查，影响ERP与listing管理。涉及数据出境场景的标识要求。",
     "tags": ["数据标识", "标准"], "applicable_scenario": "数据跨境合规", "validity_level": "指引",
     "risk_level": "中", "risk_points": ["数据标识需符合规范", "影响系统改造"], "source_tier": SOURCE_TIER_REFERENCE},
    {"id": "pol-legal-015", "title": "关于实施绿色消费推进行动的通知", "source": "商务部等9部门",
     "url": "https://www.mofcom.gov.cn/zwgk/", "publish_date": "2026-01", "effective_date": "2026-02",
     "content": "部分出口产品需提供碳排放合规证明，影响跨境供应链与包装。涉及出口数据与证明文件。",
     "tags": ["绿色消费", "碳排放"], "applicable_scenario": "数据跨境合规", "validity_level": "通知",
     "risk_level": "中", "risk_points": ["部分品类需合规证明"], "source_tier": SOURCE_TIER_CORE},
    # 知识产权合规
    {"id": "pol-legal-016", "title": "跨境电商出口商品知识产权保护指引", "source": "国家知识产权局",
     "url": "https://www.gov.cn/", "publish_date": "2024-05", "effective_date": "2024-06",
     "content": "规范跨境电商出口商品知识产权备案与侵权处置流程。未备案或侵权将面临下架及法律责任。",
     "tags": ["知识产权", "备案", "侵权"], "applicable_scenario": "知识产权合规", "validity_level": "指引",
     "risk_level": "高", "risk_points": ["建议提前备案", "侵权处置有时效要求"], "source_tier": SOURCE_TIER_CORE},
    # 行政处罚合规 / 综合
    {"id": "pol-legal-017", "title": "跨境电商零售进口商品清单调整", "source": "财政部等六部门",
     "url": "https://www.gov.cn/", "publish_date": "2024-01", "effective_date": "2024-02",
     "content": "扩大跨境电商零售进口商品清单，新增部分消费品类目。清单外商品不得以跨境电商零售进口方式进口。",
     "tags": ["进口", "清单", "消费品"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "高", "risk_points": ["清单外商品禁止进口", "违规将处罚"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-018", "title": "杭州跨境电商综试区创新发展若干措施", "source": "杭州市政府",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2024-06", "effective_date": "2024-07",
     "content": "支持海外仓建设、物流补贴、企业孵化等，打造跨境电商生态。地方配套，非全国强制。",
     "tags": ["综试区", "杭州", "海外仓"], "applicable_scenario": "清关合规", "validity_level": "规范性文件",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_REFERENCE},
    {"id": "pol-legal-019", "title": "深圳前海跨境电商扶持办法", "source": "深圳前海管理局",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2024-04", "effective_date": "2024-05",
     "content": "对跨境电商企业给予租金补贴、物流补贴、人才引进支持。适用前海范围内企业。",
     "tags": ["前海", "深圳", "补贴"], "applicable_scenario": "财税合规", "validity_level": "规范性文件",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_REFERENCE},
    {"id": "pol-legal-020", "title": "成都跨境电商综试区支持政策", "source": "成都市政府",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2024-08", "effective_date": "2024-09",
     "content": "对跨境电商企业给予物流补贴、海外仓建设补贴，支持中欧班列跨境出口。",
     "tags": ["成都", "综试区", "中欧班列"], "applicable_scenario": "清关合规", "validity_level": "规范性文件",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_REFERENCE},
    {"id": "pol-legal-021", "title": "重庆跨境电商综试区创新发展实施方案", "source": "重庆市政府",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2024-04", "effective_date": "2024-05",
     "content": "依托陆海新通道，打造西部跨境电商枢纽，支持9710/9810模式。",
     "tags": ["重庆", "陆海新通道", "西部"], "applicable_scenario": "清关合规", "validity_level": "规范性文件",
     "risk_level": "低", "risk_points": [], "source_tier": SOURCE_TIER_REFERENCE},
    # 补充：更多清关、财税、处罚类
    {"id": "pol-legal-022", "title": "海关总署关于跨境电商进出口申报事项的公告", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2024-01", "effective_date": "2024-02",
     "content": "明确跨境电商进出口申报项目、单证要求及申报时限。未按规定申报的，按申报不实处理。",
     "tags": ["申报", "单证", "时限"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "高", "risk_points": ["申报不实将处罚", "时限需遵守"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-023", "title": "税务总局关于跨境电商综合试验区零售出口货物免税管理办法", "source": "国家税务总局",
     "url": "https://www.chinatax.gov.cn/", "publish_date": "2023-06", "effective_date": "2023-07",
     "content": "综试区内跨境电商零售出口货物实行增值税、消费税免税。需在综试区登记并符合清单。",
     "tags": ["综试区", "免税", "零售出口"], "applicable_scenario": "财税合规", "validity_level": "部门规章",
     "risk_level": "中", "risk_points": ["仅限综试区", "需登记"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-024", "title": "商务部等关于跨境电商出口海外仓监管的公告", "source": "商务部、海关总署",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2023-03", "effective_date": "2023-04",
     "content": "9810模式下海外仓备案、货物出境及境外销售申报要求。未备案不得以9810方式出口。",
     "tags": ["9810", "海外仓", "备案"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "高", "risk_points": ["海外仓需备案", "未备案不得用9810"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-025", "title": "海关总署关于跨境电子商务企业境内代理人管理的公告", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2022-11", "effective_date": "2022-12",
     "content": "跨境电商进口企业应指定境内代理人，承担申报、税款等义务。未指定或代理人失责的，企业承担后果。",
     "tags": ["境内代理人", "进口"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "高", "risk_points": ["须指定境内代理人", "代理人责任连带"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-026", "title": "关于跨境电子商务零售进口商品条码应用的公告", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2024-03", "effective_date": "2024-04",
     "content": "跨境电商零售进口商品申报时需填报商品条码（GTIN）。未填报或填报错误的，可能影响通关。",
     "tags": ["条码", "GTIN", "零售进口"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["需填报条码", "错误影响通关"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-027", "title": "财政部 海关总署关于跨境电子商务零售进口税收政策的通知", "source": "财政部、海关总署",
     "url": "https://www.gov.cn/", "publish_date": "2016-03", "effective_date": "2016-04",
     "content": "跨境电商零售进口按货物征收关税、进口环节增值税、消费税；个人年度限值及单次限值。超限按一般贸易管理。",
     "tags": ["零售进口", "限值", "税收"], "applicable_scenario": "财税合规", "validity_level": "通知",
     "risk_level": "中", "risk_points": ["超限值按一般贸易", "需如实申报"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-028", "title": "市场监管总局关于跨境电商登记与公示的指导意见", "source": "市场监管总局",
     "url": "https://www.gov.cn/", "publish_date": "2023-09", "effective_date": "2023-10",
     "content": "跨境电商经营者应依法登记并公示主体信息。未登记或未公示的，由市场监管部门处理。",
     "tags": ["登记", "公示", "主体"], "applicable_scenario": "行政处罚合规", "validity_level": "指引",
     "risk_level": "中", "risk_points": ["须登记并公示", "未登记将处罚"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-029", "title": "外汇局关于跨境电子商务外汇支付试点的通知", "source": "外汇局",
     "url": "https://www.gov.cn/", "publish_date": "2013-09", "effective_date": "2013-09",
     "content": "开展跨境电商外汇支付试点机构条件及业务范围。支付机构需取得试点资格并遵守结汇规定。",
     "tags": ["外汇", "支付", "结汇"], "applicable_scenario": "支付合规", "validity_level": "通知",
     "risk_level": "高", "risk_points": ["需试点资格", "结汇须合规"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-030", "title": "海关总署关于跨境电商退货中心仓监管的公告", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2023-05", "effective_date": "2023-06",
     "content": "在综合保税区内设置退货中心仓的条件与监管要求。退货入区需申报并接受海关监管。",
     "tags": ["退货中心仓", "综保区"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["退货入区需申报", "限于综保区"], "source_tier": SOURCE_TIER_CORE},
    # 补充：清关/财税/支付/数据/知识产权/处罚，含欧盟·美国·废止示例
    {"id": "pol-legal-031", "title": "海关总署关于跨境电商统一版信息化系统接入的公告", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2023-08", "effective_date": "2023-09",
     "content": "跨境电商企业、平台、支付、物流等需接入海关统一版信息化系统，未接入不得开展业务。",
     "tags": ["信息化", "接入", "统一版"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "高", "risk_points": ["未接入不得开展业务", "数据需实时传输"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-032", "title": "海关总署关于跨境电商B2B出口监管试点公告", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2020-06", "effective_date": "2020-07",
     "content": "在部分海关开展9710、9810试点，企业可采用简化申报、清单核放。试点范围后扩大至全国。",
     "tags": ["9710", "9810", "B2B"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["需在试点关区申报", "符合监管条件"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-033", "title": "税务总局关于跨境电商综试区零售出口企业所得税核定征收的公告", "source": "国家税务总局",
     "url": "https://www.chinatax.gov.cn/", "publish_date": "2022-09", "effective_date": "2022-10",
     "content": "综试区内跨境电商零售出口企业符合条件可实行企业所得税核定征收，简化税务处理。",
     "tags": ["综试区", "核定征收", "企业所得税"], "applicable_scenario": "财税合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["仅限综试区", "需符合核定条件"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-034", "title": "个人外汇管理办法实施细则（跨境电商结汇相关）", "source": "外汇局",
     "url": "https://www.gov.cn/", "publish_date": "2007-01", "effective_date": "2007-02",
     "content": "个人结汇年度便利化额度及超额度证明材料。跨境电商卖家结汇需符合个人或企业外汇规定。",
     "tags": ["结汇", "个人外汇", "额度"], "applicable_scenario": "支付合规", "validity_level": "部门规章",
     "risk_level": "中", "risk_points": ["超额度需证明材料", "违规将纳入关注"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-035", "title": "网络安全法（数据出境与个人信息保护相关条款）", "source": "全国人大常委会",
     "url": "https://www.gov.cn/", "publish_date": "2016-11", "effective_date": "2017-06",
     "content": "关键信息基础设施运营者境内存储、出境安全评估；个人信息收集使用需合法正当必要。跨境电商涉及用户数据出境须评估。",
     "tags": ["数据出境", "安全评估", "个人信息"], "applicable_scenario": "数据跨境合规", "validity_level": "法律",
     "risk_level": "高", "risk_points": ["数据出境须安全评估", "违规处罚重"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-036", "title": "个人信息保护法（跨境提供个人信息）", "source": "全国人大常委会",
     "url": "https://www.gov.cn/", "publish_date": "2021-08", "effective_date": "2021-11",
     "content": "向境外提供个人信息需具备法定条件：安全评估、认证、标准合同等。跨境电商平台向境外传输用户信息须合规。",
     "tags": ["个人信息", "出境", "标准合同"], "applicable_scenario": "数据跨境合规", "validity_level": "法律",
     "risk_level": "高", "risk_points": ["出境须满足三选一机制", "违法高额罚款"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-037", "title": "关于跨境电商违规行为行政处罚裁量基准的指引", "source": "市场监管总局",
     "url": "https://www.gov.cn/", "publish_date": "2023-11", "effective_date": "2023-12",
     "content": "对跨境电商经营者未登记、未公示、虚假宣传等行为的裁量基准与处罚幅度。各地可制定细则。",
     "tags": ["裁量", "处罚", "违规"], "applicable_scenario": "行政处罚合规", "validity_level": "指引",
     "risk_level": "中", "risk_points": ["违规将按裁量处罚", "各地细则可能不同"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-038", "title": "海关总署关于跨境电子商务零售进口商品监管的公告（原2016年）", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2016-03", "effective_date": "2016-04", "repeal_date": "2018-12",
     "content": "原跨境电商零售进口监管办法，部分条款已被后续公告修订或替代。仅供历史溯源。",
     "tags": ["零售进口", "监管", "已修订"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "低", "risk_points": ["已废止，不可引用"], "source_tier": SOURCE_TIER_CORE,
     "revision_notes": "2018年《关于完善跨境电子商务零售进口监管的公告》等对零售进口监管作了调整；本公告部分内容已不再执行。", "validity_note": "部分条款已废止或由新规替代。"},
    {"id": "pol-legal-039", "title": "欧盟增值税规则（跨境电商B2C 2021）", "source": "欧盟委员会",
     "url": "https://ec.europa.eu/taxation_customs/", "publish_date": "2021-01", "effective_date": "2021-07",
     "content": "欧盟境内B2C电商销售增值税：一站式申报（OSS）、进口一站式（IOSS）、低值货物取消22欧元免税。",
     "tags": ["欧盟", "VAT", "IOSS", "OSS"], "applicable_scenario": "财税合规", "target_region": "欧盟",
     "validity_level": "规章", "risk_level": "高", "risk_points": ["未注册VAT将无法清关", "IOSS需指定税务代表"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-040", "title": "欧盟海关法典（UCC）跨境电商相关条款", "source": "欧盟委员会",
     "url": "https://ec.europa.eu/taxation_customs/", "publish_date": "2016-05", "effective_date": "2016-05",
     "content": "欧盟统一海关申报、预裁定、授权经济运营商（AEO）。跨境电商进口须完成海关申报并缴纳关税/增值税。",
     "tags": ["欧盟", "UCC", "海关", "AEO"], "applicable_scenario": "清关合规", "target_region": "欧盟",
     "validity_level": "规章", "risk_level": "高", "risk_points": ["须完成海关申报", "低值申报要求"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-041", "title": "欧盟DSA数字服务法（平台责任与合规）", "source": "欧盟委员会",
     "url": "https://digital-strategy.ec.europa.eu/", "publish_date": "2022-10", "effective_date": "2024-02",
     "content": "大型在线平台需履行风险管控、透明度、数据访问等义务。在欧盟经营的跨境电商平台可能适用。",
     "tags": ["欧盟", "DSA", "平台责任"], "applicable_scenario": "数据跨境合规", "target_region": "欧盟",
     "validity_level": "规章", "risk_level": "中", "risk_points": ["平台需合规义务", "违规罚款高"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-042", "title": "美国海关与边境保护局（CBP）电商进口要求", "source": "美国CBP",
     "url": "https://www.cbp.gov/", "publish_date": "2019-06", "effective_date": "2019-06",
     "content": "美国800美元以下小额豁免（de minimis）进口要求；电商货物需提供正确描述与价值。违规可能导致扣留或处罚。",
     "tags": ["美国", "CBP", "de minimis", "小额豁免"], "applicable_scenario": "清关合规", "target_region": "美国",
     "validity_level": "规章", "risk_level": "中", "risk_points": ["申报价值与描述须真实", "违规扣留或处罚"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-043", "title": "美国FTC电商与消费者保护规则", "source": "美国FTC",
     "url": "https://www.ftc.gov/", "publish_date": "2020-01", "effective_date": "2020-01",
     "content": "禁止虚假宣传、未履行发货、不正当竞争。跨境电商对美销售须遵守FTC消费者保护与广告规则。",
     "tags": ["美国", "FTC", "消费者保护", "广告"], "applicable_scenario": "行政处罚合规", "target_region": "美国",
     "validity_level": "规章", "risk_level": "高", "risk_points": ["虚假宣传将处罚", "发货与退换货须合规"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-044", "title": "美国关税法第321条小额豁免（Section 321）", "source": "美国CBP",
     "url": "https://www.cbp.gov/", "publish_date": "2016-02", "effective_date": "2016-02",
     "content": "单日单收件人800美元以下货物可适用简易通关。跨境电商直邮美国常走此通道，须如实申报。",
     "tags": ["美国", "321", "800美元", "直邮"], "applicable_scenario": "清关合规", "target_region": "美国",
     "validity_level": "法律", "risk_level": "中", "risk_points": ["超800或拆分申报将查", "如实申报"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-045", "title": "商务部关于跨境电商综合试验区零售出口货物税收政策的通知", "source": "商务部、财政部等",
     "url": "https://www.mofcom.gov.cn/", "publish_date": "2018-09", "effective_date": "2018-10",
     "content": "综试区跨境电商零售出口无票货物试行增值税、消费税免税。需在综试区注册并纳入联网监管。",
     "tags": ["综试区", "无票免税", "零售出口"], "applicable_scenario": "财税合规", "validity_level": "通知",
     "risk_level": "中", "risk_points": ["仅限综试区", "需纳入监管"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-046", "title": "海关总署关于跨境电子商务零售进口商品条码申报的公告（补充）", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2024-03", "effective_date": "2024-04",
     "content": "零售进口商品申报时优先填报全球唯一标识（GTIN）。未填报的，可能影响通关效率或后续核查。",
     "tags": ["条码", "GTIN", "零售进口"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["建议填报条码", "错误影响通关"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-047", "title": "国家知识产权局关于跨境电商领域知识产权保护的指引", "source": "国家知识产权局",
     "url": "https://www.cnipa.gov.cn/", "publish_date": "2024-05", "effective_date": "2024-06",
     "content": "出口商品知识产权备案、侵权投诉与申诉流程。平台与卖家需配合下架与举证。",
     "tags": ["知识产权", "备案", "侵权"], "applicable_scenario": "知识产权合规", "validity_level": "指引",
     "risk_level": "高", "risk_points": ["建议提前备案", "侵权下架与责任"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-048", "title": "数据出境安全评估办法", "source": "国家网信办",
     "url": "https://www.cac.gov.cn/", "publish_date": "2022-07", "effective_date": "2022-09",
     "content": "关键数据出境须申报安全评估；个人信息出境可通过评估、认证或标准合同。跨境电商平台数据出境须选一合规路径。",
     "tags": ["数据出境", "安全评估", "标准合同"], "applicable_scenario": "数据跨境合规", "validity_level": "部门规章",
     "risk_level": "高", "risk_points": ["关键数据须评估", "违规责令整改或处罚"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-049", "title": "海关总署关于跨境电商企业对企业出口试点的公告", "source": "海关总署",
     "url": "https://www.customs.gov.cn/", "publish_date": "2020-06", "effective_date": "2020-07",
     "content": "在北京、天津等10地海关开展跨境电商B2B出口试点（9710、9810），后扩大至全国。",
     "tags": ["9710", "9810", "B2B", "试点"], "applicable_scenario": "清关合规", "validity_level": "公告",
     "risk_level": "中", "risk_points": ["需在试点/全国关区申报", "符合监管条件"], "source_tier": SOURCE_TIER_CORE},
    {"id": "pol-legal-050", "title": "税务总局关于外贸综合服务企业代办退税的公告", "source": "国家税务总局",
     "url": "https://www.chinatax.gov.cn/", "publish_date": "2018-06", "effective_date": "2018-10",
     "content": "综服企业代办生产企业出口退税的条件与责任。委托综服企业出口的跨境电商需确保生产方资质与单证真实。",
     "tags": ["综服企业", "代办退税", "出口"], "applicable_scenario": "财税合规", "validity_level": "公告",
     "risk_level": "高", "risk_points": ["代办方承担连带责任", "单证真实"], "source_tier": SOURCE_TIER_CORE},
]
# 为每条政策补全法务维度默认值（目标国、废止、修订说明、效力说明、各地标签）
_REGION_FROM_TITLE = {"杭州": "杭州", "广州": "广州", "深圳": "深圳", "宁波": "宁波", "郑州": "郑州", "成都": "成都", "重庆": "重庆", "苏州": "苏州", "青岛": "青岛", "长沙": "长沙", "合肥": "合肥", "西安": "西安", "天津": "天津", "大连": "大连", "厦门": "厦门", "南京": "南京", "无锡": "无锡", "东莞": "东莞", "佛山": "佛山", "珠海": "珠海", "济南": "济南", "武汉": "武汉", "沈阳": "沈阳", "哈尔滨": "哈尔滨", "昆明": "昆明", "南宁": "南宁", "兰州": "兰州", "乌鲁木齐": "乌鲁木齐", "石家庄": "石家庄", "太原": "太原", "南昌": "南昌", "福州": "福州", "贵阳": "贵阳", "海口": "海口", "银川": "银川", "西宁": "西宁", "呼和浩特": "呼和浩特", "拉萨": "拉萨", "前海": "深圳"}
for _p in LEGAL_POLICY_LIBRARY:
    _p.setdefault("target_region", "中国")
    _p.setdefault("repeal_date", "")
    _p.setdefault("revision_notes", "")
    _p.setdefault("validity_note", "")
    if not _p.get("region_label"):
        for city, label in _REGION_FROM_TITLE.items():
            if city in (_p.get("title") or ""):
                _p["region_label"] = label
                break
        else:
            _p.setdefault("region_label", "全国")


def _ensure_expanded_policy_file() -> None:
    """扩展库文件不存在时自动生成（自动化执行，无需手动跑脚本）。"""
    if EXPANDED_POLICY_PATH.exists():
        return
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        from scripts.generate_expanded_policies import generate_and_save
        generate_and_save(EXPANDED_POLICY_PATH)
    except Exception:
        pass


def load_expanded_policy_library() -> list[dict[str, Any]]:
    """加载扩展政策库（约 1000 条），缓存于内存。若文件不存在则自动生成后加载。"""
    global _EXPANDED_CACHE
    if _EXPANDED_CACHE is not None:
        return _EXPANDED_CACHE
    if not EXPANDED_POLICY_PATH.exists():
        _ensure_expanded_policy_file()
    if EXPANDED_POLICY_PATH.exists():
        try:
            with open(EXPANDED_POLICY_PATH, encoding="utf-8") as f:
                _EXPANDED_CACHE = json.load(f)
        except Exception:
            _EXPANDED_CACHE = []
    else:
        _EXPANDED_CACHE = []
    return _EXPANDED_CACHE


def _is_fake_url(url: str) -> bool:
    """占位/示例域名（如 example.com）一律视为无效，不展示「查看原文」。"""
    if not url or not isinstance(url, str):
        return True
    u = url.strip().lower()
    return "example.com" in u or "example.org" in u or "example.net" in u


def get_full_policy_library() -> list[dict[str, Any]]:
    """种子 50 + 扩展库，合计 1000+ 条。排除 URL 为 example 等占位域名的条目。"""
    expanded = load_expanded_policy_library()
    all_policies = list(LEGAL_POLICY_LIBRARY) + list(expanded)
    return [p for p in all_policies if not _is_fake_url(p.get("url"))]


def get_legal_policies(
    scenario: str | None = None,
    target_region: str | None = None,
    region_label: str | None = None,
    risk_level: str | None = None,
    include_repealed: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """法务多维度检索：合规场景 + 目标国 + 各地 + 风险等级；默认排除已废止。"""
    policies = get_full_policy_library()
    if not include_repealed:
        policies = [p for p in policies if not p.get("repeal_date")]
    if scenario:
        policies = [p for p in policies if p.get("applicable_scenario") == scenario]
    if target_region:
        policies = [p for p in policies if p.get("target_region") == target_region]
    if region_label:
        policies = [p for p in policies if p.get("region_label") == region_label]
    if risk_level:
        policies = [p for p in policies if p.get("risk_level") == risk_level]
    def _date_key(p):
        d = p.get("effective_date") or p.get("publish_date") or "0000"
        return (d.replace("-", "") or "00000000")[::-1]
    policies.sort(key=_date_key, reverse=True)
    return policies[:limit]
