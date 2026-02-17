"""
ahotnews (BettaFish 微舆) 集成桥接

使用 https://github.com/wateryu2030/ahotnews 的 MindSpider 按关键词（跨境电商等）
在抖音(dy)、快手(ks)、微博(wb) 等平台爬取热点，并同步到 CPG-Hub 的 media_hot 表。
支持先写入 daily_topics 再执行深度爬取，或仅同步已有爬取结果。
"""

import json
import logging
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from config import settings
from crawler.db import get_db, init_db, media_insert

logger = logging.getLogger(__name__)

# 跨境电商相关关键词，写入 ahotnews daily_topics 用于爬取
CROSS_BORDER_KEYWORDS = [
    "跨境电商", "跨境出口", "海外仓", "Temu", "Shein",
    "亚马逊 中国卖家", "9610", "9710", "9810", "综试区", "保税",
]

PLATFORM_MAP = {"dy": "douyin", "ks": "kuaishou", "wb": "weibo", "xhs": "xiaohongshu", "bili": "bilibili", "zhihu": "zhihu", "tieba": "tieba"}


def get_ahotnews_root() -> Path | None:
    """返回 ahotnews 项目根目录（MindSpider 的上级）"""
    p = Path(settings.ahotnews_path)
    if not p.is_absolute():
        p = Path(__file__).parent.parent / p
    mindspider = p / "MindSpider"
    if mindspider.exists() and (mindspider / "main.py").exists():
        return p
    return None


def seed_keywords_to_ahotnews() -> bool:
    """
    向 ahotnews 的 daily_topics 表写入今日话题与关键词，供 MindSpider 深度爬取使用。
    要求配置 AHOTNEWS_DB_* 且与 ahotnews 使用同一数据库。
    """
    if not all([settings.ahotnews_db_host, settings.ahotnews_db_user, settings.ahotnews_db_password]):
        logger.warning("ahotnews DB not configured, skip seed_keywords")
        return False
    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.ahotnews_db_host,
            port=settings.ahotnews_db_port,
            user=settings.ahotnews_db_user,
            password=settings.ahotnews_db_password,
            database=settings.ahotnews_db_name,
            charset="utf8mb4",
        )
        try:
            today = date.today().isoformat()
            topic_id = "cpg_hub_cross_border"
            keywords_json = json.dumps(CROSS_BORDER_KEYWORDS, ensure_ascii=False)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO daily_topics (topic_id, topic_name, topic_description, keywords, extract_date, processing_status, add_ts, last_modify_ts)
                    VALUES (%s, %s, %s, %s, %s, 'completed', %s, %s)
                    ON DUPLICATE KEY UPDATE keywords = VALUES(keywords), last_modify_ts = VALUES(last_modify_ts)
                    """,
                    (topic_id, "跨境电商政策与热点", "CPG-Hub 定制关键词", keywords_json, today, int(datetime.now().timestamp()), int(datetime.now().timestamp())),
                )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as e:
        logger.warning("seed_keywords_to_ahotnews (mysql) failed: %s", e)
    return False


def run_mindspider_deep_sentiment(platforms: list[str] | None = None) -> bool:
    """在 ahotnews 目录下执行 MindSpider 深度情感爬取。"""
    root = get_ahotnews_root()
    if not root:
        logger.warning("ahotnews not found at %s", settings.ahotnews_path)
        return False
    mindspider = root / "MindSpider"
    platforms = platforms or ["dy", "ks", "wb"]
    cmd = [sys.executable, "main.py", "--deep-sentiment", "--platforms"] + platforms + ["--max-keywords", "20", "--max-notes", "30"]
    try:
        r = subprocess.run(cmd, cwd=mindspider, timeout=3600, capture_output=True, text=True)
        if r.returncode != 0:
            logger.warning("MindSpider exit %s: %s", r.returncode, r.stderr[:500] if r.stderr else "")
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning("MindSpider timeout")
        return False
    except Exception as e:
        logger.warning("run_mindspider_deep_sentiment error: %s", e)
        return False


def sync_ahotnews_results_to_media_hot() -> int:
    """
    从 ahotnews 数据库的 MediaCrawler 结果表（如 douyin_aweme, kuaishou_video, weibo_note）
    读取最近爬取内容，写入 CPG-Hub 的 media_hot 表。
    需要 AHOTNEWS_DB_* 与 ahotnews 使用同一 DB。
    """
    if not all([settings.ahotnews_db_host, settings.ahotnews_db_user]):
        return 0
    init_db()
    count = 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.ahotnews_db_host,
            port=settings.ahotnews_db_port,
            user=settings.ahotnews_db_user,
            password=settings.ahotnews_db_password,
            database=settings.ahotnews_db_name,
            charset="utf8mb4",
        )
        try:
            # MediaCrawler 表名与字段可能因版本不同，这里做兼容查询
            tables_query = [
                ("douyin_aweme", "douyin", "title", "aweme_id", "desc"),
                ("kuaishou_video", "kuaishou", "title", "video_id", "desc"),
                ("weibo_note", "weibo", "content", "note_id", "content"),
            ]
            for table, platform, title_col, id_col, snippet_col in tables_query:
                try:
                    with conn.cursor() as cur:
                        cur.execute(f"SELECT {id_col}, {title_col}, {snippet_col} FROM {table} ORDER BY add_ts DESC LIMIT 50")
                        rows = cur.fetchall()
                except Exception as e:
                    logger.debug("ahotnews table %s: %s", table, e)
                    continue
                for row in rows:
                    try:
                        rid, title, snippet = (row[0], row[1], row[2]) if len(row) >= 3 else (row[0], row[1] if len(row) > 1 else "", "")
                        title = (title or snippet or str(rid))[:300]
                        snippet = (snippet or title or "")[:500]
                        with get_db() as cpg_conn:
                            media_insert(cpg_conn, {
                                "platform": platform,
                                "title": title,
                                "url": f"https://{platform}.com/{rid}",
                                "author": "",
                                "publish_date": "",
                                "content_snippet": snippet,
                                "keywords": "跨境电商",
                                "heat_score": 0,
                                "crawled_at": now,
                            })
                        count += 1
                    except Exception as e:
                        logger.debug("insert one ahotnews row: %s", e)
        finally:
            conn.close()
    except Exception as e:
        logger.warning("sync_ahotnews_results_to_media_hot failed: %s", e)
    logger.info("sync_ahotnews_results_to_media_hot: %d items", count)
    return count


def run_ahotnews_crawl(platforms: list[str] | None = None) -> dict[str, Any]:
    """
    完整流程：写入关键词 -> 执行 MindSpider 深度爬取 -> 同步结果到 media_hot。
    若未配置 ahotnews 或 DB，仅返回 status。调用方可用 asyncio.to_thread 避免阻塞。
    """
    if not settings.ahotnews_enabled:
        return {"ok": False, "reason": "AHOTNEWS_ENABLED=false"}
    root = get_ahotnews_root()
    if not root:
        return {"ok": False, "reason": "ahotnews not found, run scripts/setup_ahotnews.sh"}

    seeded = seed_keywords_to_ahotnews()
    run_ok = run_mindspider_deep_sentiment(platforms=platforms)
    synced = sync_ahotnews_results_to_media_hot()
    return {"ok": True, "seeded": seeded, "run_ok": run_ok, "synced_count": synced}
