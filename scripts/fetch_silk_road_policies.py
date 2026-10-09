#!/usr/bin/env python3
"""
丝路电商伙伴国政策归集

根据商务部「与中国建立电子商务合作的 36 国」名单，通过 Perplexity/OpenRouter 搜索各国
电子商务与跨境电商政策，写入 policy 表并标记 country 维度，便于按国家查询。

用法（项目根目录）:
  python3 scripts/fetch_silk_road_policies.py           # 全量 36 国
  python3 scripts/fetch_silk_road_policies.py --dry-run # 仅试跑前 2 国
  python3 scripts/fetch_silk_road_policies.py 新加坡 越南 # 仅指定国家
"""

import argparse
import asyncio
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 商务部：与中国建立电子商务合作的国家（36 国）
SILK_ROAD_ECOUNTRIES = [
    "埃及", "孟加拉国", "肯尼亚", "塔吉克斯坦", "巴林", "塞尔维亚", "印度尼西亚", "菲律宾",
    "老挝", "泰国", "巴基斯坦", "新加坡", "白俄罗斯", "塞内加尔", "乌兹别克斯坦", "瓦努阿图",
    "萨摩亚", "哥伦比亚", "意大利", "巴拿马", "阿根廷", "冰岛", "卢旺达", "阿联酋", "科威特",
    "俄罗斯", "哈萨克斯坦", "奥地利", "匈牙利", "爱沙尼亚", "柬埔寨", "澳大利亚", "巴西",
    "越南", "新西兰", "智利",
]


def _hash_content(title: str, url: str, snippet: str) -> str:
    return hashlib.sha256((title + url + (snippet or "")).encode()).hexdigest()[:32]


async def main() -> int:
    parser = argparse.ArgumentParser(description="丝路电商伙伴国政策搜索并入库")
    parser.add_argument("--dry-run", action="store_true", help="仅跑前 2 国试运行")
    parser.add_argument("countries", nargs="*", help="仅处理指定国家（默认全量 36 国）")
    args = parser.parse_args()

    from crawler.db import init_db, get_db, policy_upsert, policy_get_existing_urls
    from services.policy_search import search_country_ecommerce_policy
    from agents.policy_legal import infer_scenario_from_text, infer_validity_level

    init_db()
    countries = args.countries if args.countries else SILK_ROAD_ECOUNTRIES
    if args.dry_run:
        countries = countries[:2]
        print(" dry-run: 仅处理", countries)

    total = 0
    with get_db() as conn:
        existing_urls = policy_get_existing_urls(conn)

    for i, country in enumerate(countries):
        print(f"[{i+1}/{len(countries)}] 搜索: {country} …")
        try:
            rows = await search_country_ecommerce_policy(country)
        except Exception as e:
            print(f"  搜索失败: {e}")
            continue
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for r in rows:
            title = (r.get("title") or "").strip()[:300]
            url = (r.get("url") or "").strip()
            if not url or not title or len(title) < 6:
                continue
            content = (r.get("content") or r.get("summary") or "")[:500]
            category = r.get("category") or infer_scenario_from_text(title, content, [])
            row = {
                "source_org": "丝路电商搜索",
                "region": "",
                "title": title,
                "url": url,
                "content_snippet": content,
                "publish_date": r.get("publish_date") or r.get("date") or "",
                "category": category,
                "validity_level": infer_validity_level(r.get("source") or "丝路电商", title),
                "risk_level": "",
                "risk_points": [],
                "crawled_at": now,
                "raw_hash": _hash_content(title, url, content),
                "country": country,
            }
            with get_db() as conn:
                try:
                    policy_upsert(conn, row)
                    total += 1
                except Exception as e:
                    print(f"  写入跳过 {title[:40]}...: {e}")
        await asyncio.sleep(1.5)
    print(f"完成，共写入/更新 {total} 条政策。")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
