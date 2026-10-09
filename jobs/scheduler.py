"""
后台调度器

- 全量同步：按 sync_interval_minutes 执行政策+热销+知识
- 持续积累：按 sync_accumulate_interval_minutes 执行政策+热销+OpenClaw 关键词轮询，使内容不断增多
"""

import asyncio
import logging

from config import settings
from jobs.sync_jobs import run_sync_all, run_accumulate_content

logger = logging.getLogger(__name__)


async def _scheduler_loop() -> None:
    """全量同步循环：首次延迟 60 秒，之后按 sync_interval_minutes 执行"""
    interval = max(1, settings.sync_interval_minutes)
    await asyncio.sleep(60)
    while True:
        try:
            result = await run_sync_all()
            logger.info("scheduler sync_all: %s", result)
        except Exception as e:
            logger.warning("scheduler error: %s", e)
        await asyncio.sleep(interval * 60)


async def _accumulate_loop() -> None:
    """持续积累循环：首次延迟 30 秒，之后按 sync_accumulate_interval_minutes 执行，让 OpenClaw 不断积累内容"""
    interval = max(1, settings.sync_accumulate_interval_minutes)
    await asyncio.sleep(30)
    while True:
        try:
            result = await asyncio.wait_for(run_accumulate_content(), timeout=180.0)
            logger.info("scheduler accumulate: %s", result)
        except asyncio.TimeoutError:
            logger.warning("accumulate timeout (180s), next run in %d min", interval)
        except Exception as e:
            logger.warning("accumulate error: %s", e)
        await asyncio.sleep(interval * 60)


def start_background_scheduler() -> asyncio.Task:
    """启动全量同步任务（政策+热销+知识）"""
    interval = max(1, settings.sync_interval_minutes)
    task = asyncio.create_task(_scheduler_loop())
    logger.info("background scheduler started, interval=%d min", interval)
    return task


def start_accumulate_scheduler() -> asyncio.Task:
    """启动持续积累任务（政策+热销+关键词轮询），使首屏内容不断增多"""
    interval = max(1, settings.sync_accumulate_interval_minutes)
    task = asyncio.create_task(_accumulate_loop())
    logger.info("accumulate scheduler started, interval=%d min", interval)
    return task
