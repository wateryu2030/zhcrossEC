"""
CPG-Hub 爬虫模块

- 政府政策爬虫：全国各地政府跨境电商管理政策，入库并周更
- 媒体热点爬虫：抖音、快手等跨境电商相关热点，按日检索
参考设计：https://github.com/wateryu2030/ahotnews
"""

from crawler.db import get_db, init_db
from crawler.policy_crawler import run_policy_crawl
from crawler.media_crawler import run_media_crawl

__all__ = ["get_db", "init_db", "run_policy_crawl", "run_media_crawl"]
