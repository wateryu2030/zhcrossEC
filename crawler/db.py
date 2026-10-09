"""
爬虫与政策数据存储

MySQL：政策表、媒体热点表、政策分析表，支持按周/按日更新检测。
配置见 .env：MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
"""

import json
from contextlib import contextmanager
from typing import Any, Iterator

import pymysql
from pymysql.cursors import DictCursor

from config import settings


def _get_connection() -> pymysql.Connection:
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


@contextmanager
def get_db() -> Iterator[pymysql.Connection]:
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_policy_legal_columns(conn: pymysql.Connection) -> None:
    """为 policy 表增加法务维度列及 country（兼容已有库）"""
    with conn.cursor() as cur:
        cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'policy'", (settings.mysql_database,))
        names = {row["COLUMN_NAME"] for row in cur.fetchall()}
    for col, typ in [
        ("validity_level", "VARCHAR(64)"),
        ("risk_level", "VARCHAR(32)"),
        ("risk_points", "TEXT"),
        ("effective_date", "VARCHAR(32)"),
        ("repeal_date", "VARCHAR(32)"),
        ("country", "VARCHAR(64)"),
    ]:
        if col not in names:
            with conn.cursor() as cur:
                cur.execute(f"ALTER TABLE policy ADD COLUMN `{col}` {typ}")
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE INDEX idx_policy_country ON policy(country)")
    except Exception:
        pass
    conn.commit()


def _ensure_database() -> None:
    """若 MySQL 中不存在配置的数据库则创建（仅首次部署需建库）"""
    conn = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` DEFAULT CHARSET utf8mb4")
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """创建政策表、媒体热点表、政策分析表，并确保法务/国家字段存在"""
    _ensure_database()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS policy (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    source_org VARCHAR(255) NOT NULL,
                    region VARCHAR(128),
                    title VARCHAR(500) NOT NULL,
                    url VARCHAR(1024) NOT NULL,
                    content_snippet TEXT,
                    publish_date VARCHAR(64),
                    category VARCHAR(128),
                    crawled_at VARCHAR(64) NOT NULL,
                    updated_at VARCHAR(64),
                    raw_hash VARCHAR(64),
                    country VARCHAR(64),
                    validity_level VARCHAR(64),
                    risk_level VARCHAR(32),
                    risk_points TEXT,
                    effective_date VARCHAR(32),
                    repeal_date VARCHAR(32),
                    UNIQUE KEY uk_url (url(500)),
                    KEY idx_policy_crawled (crawled_at),
                    KEY idx_policy_region (region)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS media_hot (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    platform VARCHAR(64) NOT NULL,
                    title VARCHAR(500),
                    url VARCHAR(1024),
                    author VARCHAR(128),
                    publish_date VARCHAR(64),
                    content_snippet TEXT,
                    keywords VARCHAR(255),
                    heat_score INT,
                    crawled_at VARCHAR(64) NOT NULL,
                    KEY idx_media_platform (platform),
                    KEY idx_media_crawled (crawled_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS policy_analysis (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    scope VARCHAR(128) NOT NULL,
                    summary TEXT NOT NULL,
                    directions TEXT,
                    action_items TEXT,
                    source VARCHAR(255),
                    created_at VARCHAR(64) NOT NULL,
                    KEY idx_policy_analysis_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        _ensure_policy_legal_columns(conn)


def policy_get_existing_urls(conn: pymysql.Connection, limit: int = 20000) -> set[str]:
    """返回已入库的政策 URL 集合，供调用方判断是否为新政策。"""
    with conn.cursor() as cur:
        cur.execute("SELECT url FROM policy WHERE url IS NOT NULL AND url != '' LIMIT %s", (limit,))
        return {row["url"] for row in cur.fetchall()}


def policy_upsert(conn: pymysql.Connection, row: dict[str, Any]) -> None:
    """插入或更新政策（以 url 为唯一键），支持法务字段及 country（丝路电商伙伴国）"""
    risk_points_raw = row.get("risk_points")
    risk_points_str = json.dumps(risk_points_raw, ensure_ascii=False) if isinstance(risk_points_raw, list) else (risk_points_raw or "")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policy (source_org, region, title, url, content_snippet, publish_date, category, crawled_at, updated_at, raw_hash,
                validity_level, risk_level, risk_points, effective_date, repeal_date, country)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                content_snippet = VALUES(content_snippet),
                publish_date = VALUES(publish_date),
                category = VALUES(category),
                updated_at = VALUES(updated_at),
                raw_hash = VALUES(raw_hash),
                validity_level = VALUES(validity_level),
                risk_level = VALUES(risk_level),
                risk_points = VALUES(risk_points),
                effective_date = VALUES(effective_date),
                repeal_date = VALUES(repeal_date),
                country = VALUES(country)
            """,
            (
                row.get("source_org", ""),
                row.get("region", ""),
                row.get("title", ""),
                row.get("url", ""),
                row.get("content_snippet", ""),
                row.get("publish_date", ""),
                row.get("category", row.get("applicable_scenario", "综合")),
                row.get("crawled_at", ""),
                row.get("crawled_at", ""),
                row.get("raw_hash", ""),
                row.get("validity_level") or "",
                row.get("risk_level") or "",
                risk_points_str,
                row.get("effective_date") or "",
                row.get("repeal_date") or "",
                row.get("country") or "",
            ),
        )


def media_get_existing_urls(conn: pymysql.Connection, limit: int = 5000) -> set[str]:
    """返回最近已入库的媒体 URL 集合，供调用方做跨轮去重。"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT url FROM media_hot WHERE url IS NOT NULL AND url != '' ORDER BY crawled_at DESC LIMIT %s",
            (limit,),
        )
        return {row["url"] for row in cur.fetchall()}


def media_insert(conn: pymysql.Connection, row: dict[str, Any]) -> None:
    """插入媒体热点（按日全量可去重由调用方控制）"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO media_hot (platform, title, url, author, publish_date, content_snippet, keywords, heat_score, crawled_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row.get("platform", ""),
                row.get("title", ""),
                row.get("url", ""),
                row.get("author", ""),
                row.get("publish_date", ""),
                row.get("content_snippet", ""),
                row.get("keywords", ""),
                row.get("heat_score") or 0,
                row.get("crawled_at", ""),
            ),
        )


def _policy_where_clause(
    region: str | None,
    category: str | None,
    country: str | None,
) -> tuple[str, list[Any]]:
    """构建 policy 筛选条件，返回 (WHERE 子句, params)。"""
    sql = ""
    params: list[Any] = []
    if region:
        sql += " WHERE region = %s"
        params.append(region)
    if category:
        sql += " WHERE category = %s" if not params else " AND category = %s"
        params.append(category)
    if country:
        sql += " WHERE country = %s" if not params else " AND country = %s"
        params.append(country)
    return sql, params


def count_policies_filtered(
    region: str | None = None,
    category: str | None = None,
    country: str | None = None,
) -> int:
    """按省市/分类/国家筛选后的政策总数，用于分页。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            where, params = _policy_where_clause(region, category, country)
            cur.execute("SELECT COUNT(*) AS n FROM policy" + where, params)
            row = cur.fetchone()
            return (row and row.get("n")) or 0


def list_policies(
    limit: int = 100,
    offset: int = 0,
    region: str | None = None,
    category: str | None = None,
    country: str | None = None,
) -> list[dict]:
    """从数据库读取政策列表，支持按 region（省市）、category（合规场景）、country（丝路电商伙伴国）筛选，支持分页。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            where, params = _policy_where_clause(region, category, country)
            params.append(limit)
            params.append(offset)
            cur.execute(
                "SELECT * FROM policy" + where + " ORDER BY crawled_at DESC LIMIT %s OFFSET %s",
                params,
            )
            rows = list(cur.fetchall())
        for r in rows:
            if r.get("risk_points") and isinstance(r["risk_points"], str):
                try:
                    r["risk_points"] = json.loads(r["risk_points"])
                except Exception:
                    r["risk_points"] = []
        return rows


def list_policy_regions() -> list[str]:
    """返回政策表中出现过的 region（省市）列表，用于筛选维度。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT region FROM policy WHERE region IS NOT NULL AND TRIM(region) != '' ORDER BY region"
            )
            return [row["region"] for row in cur.fetchall()]


def list_policy_categories() -> list[str]:
    """返回政策表中出现过的 category（合规场景）列表。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT category FROM policy WHERE category IS NOT NULL AND TRIM(category) != '' ORDER BY category"
            )
            return [row["category"] for row in cur.fetchall()]


def list_policy_countries() -> list[str]:
    """返回政策表中出现过的 country（丝路电商伙伴国等）列表。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT country FROM policy WHERE country IS NOT NULL AND TRIM(country) != '' ORDER BY country"
            )
            return [row["country"] for row in cur.fetchall()]


def get_policy_latest_crawled_at() -> str:
    """返回 policy 表最近一次爬取时间，用于前端「最后更新」展示。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(crawled_at) AS t FROM policy")
            row = cur.fetchone()
            return (row and row.get("t")) or ""


def list_media_hot(limit: int = 50, platform: str | None = None) -> list[dict]:
    """从数据库读取媒体热点"""
    with get_db() as conn:
        with conn.cursor() as cur:
            if platform:
                cur.execute(
                    "SELECT * FROM media_hot WHERE platform = %s ORDER BY crawled_at DESC LIMIT %s",
                    (platform, limit),
                )
            else:
                cur.execute("SELECT * FROM media_hot ORDER BY crawled_at DESC LIMIT %s", (limit,))
            return list(cur.fetchall())


def count_policies() -> int:
    """政策表总条数，用于首屏「政策」统计。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM policy")
            row = cur.fetchone()
            return (row and row.get("n")) or 0


def count_media_hot() -> int:
    """媒体热点表总条数，用于首屏「媒体」统计。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM media_hot")
            row = cur.fetchone()
            return (row and row.get("n")) or 0


def save_policy_analysis(conn: pymysql.Connection, row: dict[str, Any]) -> None:
    """写入一条政策洞察（方向与行动建议）"""
    directions_raw = row.get("directions")
    directions_str = json.dumps(directions_raw, ensure_ascii=False) if isinstance(directions_raw, list) else (directions_raw or "[]")
    action_raw = row.get("action_items")
    action_str = json.dumps(action_raw, ensure_ascii=False) if isinstance(action_raw, list) else (action_raw or "[]")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policy_analysis (scope, summary, directions, action_items, source, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                row.get("scope", "all"),
                row.get("summary", ""),
                directions_str,
                action_str,
                row.get("source", ""),
                row.get("created_at", ""),
            ),
        )


def get_latest_policy_analysis(limit: int = 1) -> list[dict]:
    """读取最新政策洞察"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM policy_analysis ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = list(cur.fetchall())
        for r in rows:
            for key in ("directions", "action_items"):
                if r.get(key) and isinstance(r[key], str):
                    try:
                        r[key] = json.loads(r[key])
                    except Exception:
                        r[key] = []
        return rows


def delete_policies_with_short_content(min_length: int = 200) -> tuple[int, int]:
    """
    删除正文过短的政策与媒体热点记录，返回 (policy_deleted, media_deleted)。
    用于脚本/维护，与 MySQL 实现统一。
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM policy WHERE content_snippet IS NULL OR CHAR_LENGTH(TRIM(COALESCE(content_snippet, ''))) < %s",
                (min_length,),
            )
            policy_deleted = cur.rowcount
            cur.execute(
                "DELETE FROM media_hot WHERE content_snippet IS NULL OR CHAR_LENGTH(TRIM(COALESCE(content_snippet, ''))) < %s",
                (min_length,),
            )
            media_deleted = cur.rowcount
    return policy_deleted, media_deleted


def delete_policies_with_fake_urls() -> int:
    """
    删除 policy 表中 URL 为 example.com / example.org / example.net 等占位域名的记录。
    返回删除条数。
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM policy WHERE (url LIKE %s OR url LIKE %s OR url LIKE %s)",
                ("%example.com%", "%example.org%", "%example.net%"),
            )
            return cur.rowcount


def count_policies_with_short_content(min_length: int = 200) -> tuple[int, int]:
    """统计正文过短的政策与媒体热点条数，返回 (policy_count, media_count)。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM policy WHERE content_snippet IS NULL OR CHAR_LENGTH(TRIM(COALESCE(content_snippet, ''))) < %s",
                (min_length,),
            )
            policy_count = cur.fetchone()["n"]
            cur.execute(
                "SELECT COUNT(*) AS n FROM media_hot WHERE content_snippet IS NULL OR CHAR_LENGTH(TRIM(COALESCE(content_snippet, ''))) < %s",
                (min_length,),
            )
            media_count = cur.fetchone()["n"]
    return policy_count, media_count
