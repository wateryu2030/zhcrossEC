#!/usr/bin/env python3
"""
删除数据库中正文过短的记录（policy / media_hot 的 content_snippet 为空或不足 200 字）。

使用与主应用相同的 MySQL 配置（.env 中 MYSQL_*）。

用法（在项目根目录）:
  python3 scripts/delete_empty_content.py          # 执行删除并打印条数
  python3 scripts/delete_empty_content.py --dry-run # 仅统计，不删除
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MIN_CONTENT_LEN = 200


def main():
    ap = argparse.ArgumentParser(description="删除正文为空或不足 200 字的 policy / media_hot 记录")
    ap.add_argument("--dry-run", action="store_true", help="仅统计，不执行删除")
    args = ap.parse_args()

    from crawler.db import count_policies_with_short_content, delete_policies_with_short_content

    policy_count, media_count = count_policies_with_short_content(MIN_CONTENT_LEN)
    print(f"政策 (policy): 正文不足 {MIN_CONTENT_LEN} 字的记录数 = {policy_count}")
    print(f"媒体热点 (media_hot): 正文不足 {MIN_CONTENT_LEN} 字的记录数 = {media_count}")

    if args.dry_run:
        print("(当前为 --dry-run，未执行删除；去掉该参数将真正删除)")
        return 0

    if policy_count == 0 and media_count == 0:
        return 0

    policy_deleted, media_deleted = delete_policies_with_short_content(MIN_CONTENT_LEN)
    print(f"  已删除 policy {policy_deleted} 条, media_hot {media_deleted} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
