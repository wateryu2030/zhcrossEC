"""
爬虫数据存储

SQLite：政策表、媒体热点表，支持按周/按日更新检测。
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "crawler.db"


def _get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_policy_legal_columns(conn: sqlite3.Connection) -> None:
    """为 policy 表增加法务维度列（兼容已有库）"""
    cur = conn.execute("PRAGMA table_info(policy)")
    names = {row[1] for row in cur.fetchall()}
    for col, typ in [
        ("validity_level", "TEXT"),
        ("risk_level", "TEXT"),
        ("risk_points", "TEXT"),
        ("effective_date", "TEXT"),
        ("repeal_date", "TEXT"),
    ]:
        if col not in names:
            conn.execute(f"ALTER TABLE policy ADD COLUMN {col} {typ}")
    conn.commit()


def init_db() -> None:
    """创建政策表、媒体热点表，并确保法务字段存在"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS policy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_org TEXT NOT NULL,
                region TEXT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content_snippet TEXT,
                publish_date TEXT,
                category TEXT,
                crawled_at TEXT NOT NULL,
                updated_at TEXT,
                raw_hash TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_policy_url ON policy(url);
            CREATE INDEX IF NOT EXISTS idx_policy_crawled ON policy(crawled_at);
            CREATE INDEX IF NOT EXISTS idx_policy_region ON policy(region);

            CREATE TABLE IF NOT EXISTS media_hot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                title TEXT,
                url TEXT,
                author TEXT,
                publish_date TEXT,
                content_snippet TEXT,
                keywords TEXT,
                heat_score INTEGER,
                crawled_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_media_platform ON media_hot(platform);
            CREATE INDEX IF NOT EXISTS idx_media_crawled ON media_hot(crawled_at);

            CREATE TABLE IF NOT EXISTS policy_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                summary TEXT NOT NULL,
                directions TEXT,
                action_items TEXT,
                source TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_policy_analysis_created ON policy_analysis(created_at);
        """)
        _ensure_policy_legal_columns(conn)


def policy_upsert(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    """插入或更新政策（以 url 为唯一键），支持法务字段 validity_level/risk_level/risk_points/effective_date/repeal_date"""
    risk_points_raw = row.get("risk_points")
    risk_points_str = json.dumps(risk_points_raw, ensure_ascii=False) if isinstance(risk_points_raw, list) else (risk_points_raw or "")
    conn.execute(
        """
        INSERT INTO policy (source_org, region, title, url, content_snippet, publish_date, category, crawled_at, updated_at, raw_hash,
            validity_level, risk_level, risk_points, effective_date, repeal_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title,
            content_snippet=excluded.content_snippet,
            publish_date=excluded.publish_date,
            category=excluded.category,
            updated_at=excluded.crawled_at,
            raw_hash=excluded.raw_hash,
            validity_level=excluded.validity_level,
            risk_level=excluded.risk_level,
            risk_points=excluded.risk_points,
            effective_date=excluded.effective_date,
            repeal_date=excluded.repeal_date
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
        ),
    )


def media_insert(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    """插入媒体热点（按日全量可去重由调用方控制）"""
    conn.execute(
        """
        INSERT INTO media_hot (platform, title, url, author, publish_date, content_snippet, keywords, heat_score, crawled_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def list_policies(
    limit: int = 100,
    region: str | None = None,
    category: str | None = None,
) -> list[dict]:
    """从数据库读取政策列表，支持按 region、category（合规场景）筛选"""
    with get_db() as conn:
        sql = "SELECT * FROM policy"
        params: list[Any] = []
        if region:
            sql += " WHERE region = ?"
            params.append(region)
        if category:
            sql += " WHERE category = ?" if not region else " AND category = ?"
            params.append(category)
        sql += " ORDER BY crawled_at DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(sql, params)
        rows = [dict(zip(r.keys(), r)) for r in cur.fetchall()]
        for r in rows:
            if r.get("risk_points") and isinstance(r["risk_points"], str):
                try:
                    r["risk_points"] = json.loads(r["risk_points"])
                except Exception:
                    r["risk_points"] = []
        return rows


def list_media_hot(limit: int = 50, platform: str | None = None) -> list[dict]:
    """从数据库读取媒体热点"""
    with get_db() as conn:
        if platform:
            cur = conn.execute(
                "SELECT * FROM media_hot WHERE platform = ? ORDER BY crawled_at DESC LIMIT ?",
                (platform, limit),
            )
        else:
            cur = conn.execute("SELECT * FROM media_hot ORDER BY crawled_at DESC LIMIT ?", (limit,))
        return [dict(zip(r.keys(), r)) for r in cur.fetchall()]


def save_policy_analysis(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    """写入一条政策洞察（方向与行动建议）"""
    directions_raw = row.get("directions")
    directions_str = json.dumps(directions_raw, ensure_ascii=False) if isinstance(directions_raw, list) else (directions_raw or "[]")
    action_raw = row.get("action_items")
    action_str = json.dumps(action_raw, ensure_ascii=False) if isinstance(action_raw, list) else (action_raw or "[]")
    conn.execute(
        """
        INSERT INTO policy_analysis (scope, summary, directions, action_items, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
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
        cur = conn.execute(
            "SELECT * FROM policy_analysis ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = [dict(zip(r.keys(), r)) for r in cur.fetchall()]
        for r in rows:
            for key in ("directions", "action_items"):
                if r.get(key) and isinstance(r[key], str):
                    try:
                        r[key] = json.loads(r[key])
                    except Exception:
                        r[key] = []
        return rows
