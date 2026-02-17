#!/usr/bin/env python3
"""
政策全流水线：政策库校验 → 政策抓取与标引 → 方向与行动建议分析 → 入库。

建议在「任务完成前禁止锁屏」时使用：
  caffeinate -i python scripts/run_full_policy_pipeline.py

macOS 上 caffeinate -i 会阻止系统休眠与锁屏，直至本进程结束。
"""

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> int:
    # 1) 确保政策扩展库可用（千条+）
    try:
        from agents.policy_legal import get_full_policy_library
        lib = get_full_policy_library()
        logger.info("policy library: %d items", len(lib))
    except Exception as e:
        logger.warning("policy library check: %s", e)

    # 2) 政策抓取 + 标引（政府站 + 全网搜索），写入 crawler.db
    try:
        from crawler.policy_crawler import run_policy_crawl
        n = await run_policy_crawl()
        logger.info("policy crawl done: %d items", n)
    except Exception as e:
        logger.exception("policy crawl failed: %s", e)
        return 1

    # 3) 方向与行动建议分析，写入 policy_analysis 表
    try:
        from jobs.policy_analysis_job import run_policy_insights
        out = await run_policy_insights()
        if out:
            logger.info("policy insights saved: scope=%s", out.get("scope", ""))
        else:
            logger.warning("policy insights returned none (no data or LLM error)")
    except Exception as e:
        logger.exception("policy insights failed: %s", e)
        return 1

    logger.info("full policy pipeline finished")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
