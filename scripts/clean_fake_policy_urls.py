#!/usr/bin/env python3
"""
删除「查看原文」指向 example.com 等占位域名的政策，并重新生成扩展政策库（不再含假链接）。

- MySQL policy 表：删除 url 含 example.com/example.org/example.net 的记录。
- data/legal_policies_expanded.json：重新生成，扩展条目的 url 改为空（不再用 example.com）。

用法（项目根目录）:
  python3 scripts/clean_fake_policy_urls.py
  python3 scripts/clean_fake_policy_urls.py --db-only   # 仅删 MySQL，不重新生成 JSON
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="删除占位域名政策并可选重新生成扩展库")
    ap.add_argument("--db-only", action="store_true", help="仅删除 MySQL 中假 URL 记录，不重新生成 JSON")
    args = ap.parse_args()

    from crawler.db import delete_policies_with_fake_urls

    n = delete_policies_with_fake_urls()
    print(f"已从 MySQL policy 表删除 {n} 条占位域名（example.com 等）记录。")

    if not args.db_only:
        from scripts.generate_expanded_policies import generate_and_save

        data_dir = ROOT / "data"
        out_path = data_dir / "legal_policies_expanded.json"
        data_dir.mkdir(parents=True, exist_ok=True)
        generate_and_save(out_path)
        print(f"已重新生成扩展政策库 -> {out_path}（扩展条目 url 为空，不再使用 example.com）。")
        try:
            from agents import policy_legal
            setattr(policy_legal, "_EXPANDED_CACHE", None)
            print("已清除政策库缓存，下次加载将使用新数据。")
        except Exception:
            pass

    print("建议执行一次政策全量同步以用真实数据补充：bash scripts/run_policy_full_sync.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
