"""
CPG-Hub 自动化任务

- sync_policies: 定期拉取政策并缓存
- sync_trending: 定期拉取热销趋势
- sync_all: 全量同步
"""

from jobs.sync_jobs import run_sync_all, run_sync_policies, run_sync_trending

__all__ = ["run_sync_all", "run_sync_policies", "run_sync_trending"]
