"""
爬虫定时任务

- 政府政策爬虫：以周为单位执行，全国政府站点跨境电商政策入库并检查更新
- 媒体热点爬虫：以天为单位执行，抖音/快手等跨境电商相关热点入库
"""

import asyncio
import logging

from crawler.media_crawler import run_media_crawl
from crawler.policy_crawler import run_policy_crawl

logger = logging.getLogger(__name__)

# 周 = 7 * 24 * 60 分钟
WEEKLY_INTERVAL_MINUTES = 7 * 24 * 60
# 天 = 24 * 60 分钟
DAILY_INTERVAL_MINUTES = 24 * 60


# 单轮政策爬虫最长 10 分钟，避免卡死
POLICY_CRAWL_TIMEOUT = 600.0


async def run_policy_crawl_weekly() -> int:
    """政府政策爬虫：每周执行一次"""
    try:
        n = await asyncio.wait_for(run_policy_crawl(), timeout=POLICY_CRAWL_TIMEOUT)
        logger.info("crawl_jobs: policy_crawl_weekly done, count=%d", n)
        return n
    except asyncio.TimeoutError:
        logger.warning("policy_crawl_weekly timeout (%ds)", int(POLICY_CRAWL_TIMEOUT))
        return 0
    except Exception as e:
        logger.warning("policy_crawl_weekly error: %s", e)
        return 0


async def run_media_crawl_daily() -> int:
    """媒体热点爬虫：每日执行一次"""
    try:
        n = await run_media_crawl()
        logger.info("crawl_jobs: media_crawl_daily done, count=%d", n)
        return n
    except Exception as e:
        logger.warning("media_crawl_daily error: %s", e)
        return 0


async def scheduler_weekly_loop() -> None:
    """周任务循环：启动后 30 秒执行首次（快速启动进化），之后每 7 天一次"""
    await asyncio.sleep(30)
    while True:
        try:
            await run_policy_crawl_weekly()
        except Exception as e:
            logger.warning("scheduler_weekly error: %s", e)
        await asyncio.sleep(WEEKLY_INTERVAL_MINUTES * 60)


async def scheduler_daily_loop() -> None:
    """日任务循环：启动后 1 分钟执行首次（快速采集热点），之后每 24 小时一次"""
    await asyncio.sleep(60)
    while True:
        try:
            await run_media_crawl_daily()
        except Exception as e:
            logger.warning("scheduler_daily error: %s", e)
        await asyncio.sleep(DAILY_INTERVAL_MINUTES * 60)


def start_crawl_schedulers() -> list[asyncio.Task]:
    """启动周/日爬虫调度器"""
    t1 = asyncio.create_task(scheduler_weekly_loop())
    t2 = asyncio.create_task(scheduler_daily_loop())
    logger.info("crawl schedulers started: weekly (policy), daily (media)")
    return [t1, t2]
