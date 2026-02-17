#!/usr/bin/env python3
"""
自动化同步 CLI

用法:
  python scripts/run_sync.py          # 全量同步
  python scripts/run_sync.py policies # 仅政策
  python scripts/run_sync.py trending # 仅热销
"""

import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jobs.sync_jobs import run_sync_all, run_sync_policies, run_sync_trending

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main() -> None:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if cmd == "policies":
        n = await run_sync_policies()
        print(f"同步政策完成: {n} 条")
    elif cmd == "trending":
        n = await run_sync_trending()
        print(f"同步热销完成: {n} 条")
    else:
        result = await run_sync_all()
        print(f"全量同步完成: policies={result['policies']}, trending={result['trending']}")


if __name__ == "__main__":
    asyncio.run(main())
