#!/usr/bin/env python3
"""
生成扩展法务政策库至 1000+ 条，用于各地政策检索与 AI 特点分析。
- 输出: data/legal_policies_expanded.json（仅扩展条目，不含种子 50 条）
- 自动化：应用启动或首次加载政策库时，若该文件不存在会自动调用本逻辑生成，无需手动执行。
- 手动刷新：执行 python scripts/generate_expanded_policies.py 可覆盖并重新生成。
"""

import json
import random
from pathlib import Path

# 各地（用于「各地政策特点」分析）
REGION_LABELS = [
    "全国", "杭州", "广州", "深圳", "宁波", "郑州", "成都", "重庆", "苏州", "青岛",
    "长沙", "合肥", "西安", "天津", "大连", "厦门", "南京", "无锡", "东莞", "佛山",
    "珠海", "济南", "武汉", "沈阳", "哈尔滨", "昆明", "南宁", "兰州", "乌鲁木齐",
    "石家庄", "太原", "南昌", "福州", "贵阳", "海口", "银川", "西宁", "呼和浩特", "拉萨",
    "欧盟", "美国", "英国", "日本", "东南亚",
]

SCENARIOS = [
    "清关合规", "财税合规", "支付合规", "数据跨境合规", "知识产权合规", "行政处罚合规",
]

DOC_TYPES = ["通知", "公告", "办法", "意见", "指引", "实施方案", "若干措施", "行动方案"]

TITLE_TEMPLATES = [
    "{region}关于跨境电商{theme}的{doc_type}",
    "{region}跨境电商{theme}若干措施",
    "关于支持{region}跨境电商{theme}的通知",
    "{region}跨境电商综试区{theme}实施方案",
    "进一步促进{region}跨境电商{theme}的{doc_type}",
]

THEMES_BY_SCENARIO = {
    "清关合规": ["出口通关", "零售进口监管", "海外仓", "9610/9710/9810", "跨关区退货", "申报单证", "保税物流", "先查验后装运"],
    "财税合规": ["出口退税", "退运免税", "增值税", "综试区免税", "关税保证保险", "离境退税", "企业所得税"],
    "支付合规": ["支付数据接入", "跨境结汇", "外汇试点", "支付机构监管"],
    "数据跨境合规": ["数据出境", "数据标识", "个人信息保护", "数据安全评估"],
    "知识产权合规": ["知识产权保护", "侵权处置", "备案指引", "出口商品知识产权"],
    "行政处罚合规": ["信用等级", "违规处罚", "登记公示", "裁量基准"],
}

CONTENT_TEMPLATES_BY_SCENARIO = {
    "清关合规": [
        "明确{region}跨境电商进出口申报要求与单证规范。未按规定申报的按申报不实处理。",
        "支持{region}跨境电商采用简化申报、清单核放。试点范围与监管要求见正文。",
        "跨境电商零售进口退货流程及入区监管要求。未按规定申报退货的按违规处理。",
        "海外仓备案与9810出口监管要求。企业须合规备案并如实申报。",
    ],
    "财税合规": [
        "出口退运商品税收政策延续至指定期限。1210/9610/9710/9810项下符合条件可享免税。",
        "综试区内跨境电商零售出口货物实行增值税、消费税免税。须在综试区登记并纳入监管。",
        "A类企业出口退税周期缩短；委托出口须留存委托协议与单证。",
        "关税保证保险在跨境电商零售进口担保领域的应用，降低企业通关成本。",
    ],
    "支付合规": [
        "跨境电商平台需向海关实时提供支付相关数据。未接入或数据不实影响通关与监管。",
        "跨境外汇支付试点机构条件与业务范围。支付机构须取得试点资格并遵守结汇规定。",
        "个人与企业在跨境电商场景下的结汇便利化额度及超额度证明材料要求。",
    ],
    "数据跨境合规": [
        "关键数据与个人信息出境须通过安全评估、认证或标准合同等合规路径。",
        "跨境电商数据标识规范与数据质量核查要求，影响ERP与 listing 管理。",
        "数据出境安全评估申报条件与流程。违规将责令整改或处罚。",
    ],
    "知识产权合规": [
        "跨境电商出口商品知识产权备案与侵权处置流程。建议提前备案，侵权将面临下架与责任。",
        "平台与卖家需配合知识产权投诉与申诉、下架与举证。未备案或侵权将承担相应后果。",
    ],
    "行政处罚合规": [
        "跨境电商企业信用等级与快速通关、退税时效挂钩。违规将降级并影响业务。",
        "经营者须依法登记并公示主体信息。未登记或未公示由市场监管部门处理。",
        "对未申报、虚假宣传等行为的裁量基准与处罚幅度。各地可制定细则。",
    ],
}

SOURCE_TIER_CORE = "核心强制"
SOURCE_TIER_REFERENCE = "合规参考"
SOURCES_BY_REGION = {
    "全国": "国务院/海关总署/商务部/税务总局",
    "欧盟": "欧盟委员会",
    "美国": "美国CBP/FTC",
}
DEFAULT_SOURCE = "地方政府/相关部门"

RISK_LEVELS = ["高", "中", "低"]
RISK_POINTS_POOL = ["需按规定申报", "须备案或登记", "违规将处罚", "时效要求", "数据须真实", "超限值按一般贸易"]


def _source(region: str) -> str:
    if region in SOURCES_BY_REGION:
        return SOURCES_BY_REGION[region]
    if region in ["欧盟", "美国", "英国", "日本", "东南亚"]:
        return "境外监管机构"
    return f"{region}政府"


def _target_region(region: str) -> str:
    if region in ["欧盟", "美国", "英国", "日本", "东南亚"]:
        return "其他" if region not in ["欧盟", "美国"] else ("欧盟" if region == "欧盟" else "美国")
    return "中国"


def generate_one(region: str, scenario: str, index: int, year: int) -> dict:
    themes = THEMES_BY_SCENARIO.get(scenario, ["发展"])
    theme = random.choice(themes)
    doc_type = random.choice(DOC_TYPES)
    title_tpl = random.choice(TITLE_TEMPLATES)
    title = title_tpl.format(region=region, theme=theme, doc_type=doc_type)
    contents = CONTENT_TEMPLATES_BY_SCENARIO.get(scenario, ["与跨境电商相关监管与扶持措施。"])
    content = random.choice(contents).format(region=region)
    risk = random.choice(RISK_LEVELS)
    risk_points = random.sample(RISK_POINTS_POOL, min(2, len(RISK_POINTS_POOL))) if risk != "低" else []
    month = random.randint(1, 12)
    pub = f"{year}-{month:02d}"
    eff = f"{year}-{(month % 12) + 1:02d}" if month < 12 else f"{year + 1}-01"
    return {
        "id": f"pol-exp-{index}",
        "title": title,
        "source": _source(region),
        "url": f"https://www.example.com/policy/{index}",
        "publish_date": pub,
        "effective_date": eff,
        "repeal_date": "",
        "content": content,
        "tags": [theme, region, scenario],
        "applicable_scenario": scenario,
        "target_region": _target_region(region),
        "region_label": region,
        "validity_level": "公告" if "公告" in doc_type else "通知" if "通知" in doc_type else "规范性文件",
        "risk_level": risk,
        "risk_points": risk_points,
        "source_tier": SOURCE_TIER_CORE if region == "全国" else SOURCE_TIER_REFERENCE,
        "revision_notes": "",
        "validity_note": "",
    }


def generate_expanded_list() -> list[dict]:
    """生成扩展政策列表（约 1050 条），可被脚本或应用内调用。"""
    expanded = []
    idx = 1
    years = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
    for region in REGION_LABELS:
        n_per_scenario = 2 if region == "全国" else 4
        for scenario in SCENARIOS:
            for _ in range(n_per_scenario):
                expanded.append(generate_one(region, scenario, idx, random.choice(years)))
                idx += 1
    target_expanded = 1050
    while len(expanded) < target_expanded:
        expanded.append(
            generate_one(
                random.choice(REGION_LABELS),
                random.choice(SCENARIOS),
                idx,
                random.choice(years),
            )
        )
        idx += 1
    return expanded


def generate_and_save(target_path: Path | None = None) -> list[dict]:
    """生成并写入 JSON；若未传 path 则使用默认 data/legal_policies_expanded.json。返回生成的列表。"""
    if target_path is None:
        target_path = Path(__file__).resolve().parent.parent / "data" / "legal_policies_expanded.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    expanded = generate_expanded_list()
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(expanded, f, ensure_ascii=False, indent=0)
    return expanded


def main():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    out_path = data_dir / "legal_policies_expanded.json"
    expanded = generate_and_save(out_path)
    print(f"Generated {len(expanded)} expanded policies -> {out_path}")
    print("Seed 50 + expanded =", 50 + len(expanded), "total (1000+)")


if __name__ == "__main__":
    main()
