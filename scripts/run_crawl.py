#!/usr/bin/env python3
"""
爬虫手动执行脚本

用法:
  python scripts/run_crawl.py policy   # 政府政策爬虫（周任务）
  python scripts/run_crawl.py media    # 媒体热点爬虫（日任务）
  python scripts/run_crawl.py          # 两者都执行
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main() -> None:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if cmd == "policy":
        from crawler.policy_crawler import run_policy_crawl
        n = await run_policy_crawl()
        print(f"政府政策爬虫完成: {n} 条")
    elif cmd == "media":
        from crawler.media_crawler import run_media_crawl
        n = await run_media_crawl()
        print(f"媒体热点爬虫完成: {n} 条")
    else:
        from crawler.policy_crawler import run_policy_crawl
        from crawler.media_crawler import run_media_crawl
        np = await run_policy_crawl()
        nm = await run_media_crawl()
        print(f"政策: {np} 条, 媒体热点: {nm} 条")


if __name__ == "__main__":
    asyncio.run(main())
