#!/usr/bin/env python3
"""
检查当前数据库与同步缓存状态，输出与首屏统计条、/api/v1/demo 接口完全一致的数据。

用法：
  python scripts/check_db_stats.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    print("=== CPG-Hub 数据状态自检 ===\n")

    # 与 get_demo 一致：先取 DB 与缓存，再算出接口实际返回的 stats
    db_policy_count = 0
    db_media_count = 0
    latest_crawled = ""
    library_count = 0

    try:
        from crawler.db import (
            init_db,
            count_policies,
            count_media_hot,
            get_policy_latest_crawled_at,
        )
        init_db()
        db_policy_count = count_policies()
        db_media_count = count_media_hot()
        latest_crawled = get_policy_latest_crawled_at() or ""
    except Exception as e:
        print("【MySQL】连接或查询失败:", e)
        print("  → 请确认 MySQL 已启动且 .env 中 MYSQL_* 配置正确。\n")

    try:
        from agents.policy_legal import get_full_policy_library
        library_count = len(get_full_policy_library())
    except Exception:
        pass

    cache_path = ROOT / "data" / "sync_cache.json"
    cache = {}
    if cache_path.exists():
        try:
            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            pass

    # 与 api/routes.py get_demo 完全相同的 stats 计算逻辑
    stats = cache.get("stats", {}) or {}
    stats["policy_count"] = db_policy_count
    if db_policy_count == 0 and library_count > 0:
        stats["policy_count"] = library_count
    stats["media_count"] = db_media_count
    stats.setdefault("updated_at", "真实环境")
    trending = cache.get("trending", [])
    if "trending_count" not in stats and trending:
        stats["trending_count"] = len(trending)

    # 首屏统计条将显示的值（与 static/js/app.js renderStatsStrip 一致）
    trending_count = stats.get("trending_count") or 0
    policy_count = stats.get("policy_count") or 0
    media_count = stats.get("media_count") or 0
    avg_price_diff = stats.get("avg_price_diff")
    hot_category = stats.get("hot_category")

    print("【首屏统计条将显示】（与 /api/v1/demo 及页面一致）")
    print(f"  热销品:   {trending_count}")
    print(f"  政策:     {policy_count}")
    print(f"  媒体:     {media_count}")
    print(f"  均价差:   {avg_price_diff if avg_price_diff is not None and avg_price_diff != '' else '-'}")
    print(f"  热门类目: {hot_category if hot_category is not None and hot_category != '' else '-'}")

    print("\n【数据来源】")
    print(f"  MySQL policy 表条数:     {db_policy_count}")
    print(f"  MySQL media_hot 表条数:  {db_media_count}")
    print(f"  政策最后爬取时间:        {latest_crawled or '(无)'}")
    print(f"  同步缓存 trending 条数: {len(trending)}")
    if db_policy_count == 0 and policy_count == library_count:
        print(f"  法务政策库条数（政策=0 时回退）: {library_count}")

    if db_policy_count == 0 and policy_count == 0:
        print("\n  → 政策为 0：请执行 bash scripts/run_policy_full_sync.sh 或 python3 scripts/run_crawl.py policy")
    if db_media_count == 0:
        print("  → 媒体为 0：可执行 python3 scripts/run_crawl.py media")
    if (avg_price_diff is None or avg_price_diff == "") and (hot_category is None or hot_category == ""):
        print("  → 均价差/热门类目：由定时同步或 iterate-now 写入，未跑过则显示 -")

    print("\n=== 自检结束 ===")


if __name__ == "__main__":
    main()
