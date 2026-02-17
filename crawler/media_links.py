"""
媒体链接管理

存储并读取用户提供的抖音、快手、财新、微博等媒体链接，用于展示与检索。
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


def _path() -> Path:
    p = Path(settings.media_links_file)
    if not p.is_absolute():
        p = Path(__file__).parent.parent / p
    return p


def load_media_links() -> list[dict[str, Any]]:
    """加载媒体链接列表"""
    path = _path()
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("load_media_links failed: %s", e)
        return []


def save_media_links(links: list[dict[str, Any]]) -> bool:
    """保存媒体链接列表"""
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.warning("save_media_links failed: %s", e)
        return False


def add_media_link(platform: str, url: str, title: str = "") -> dict[str, Any]:
    """新增一条媒体链接"""
    links = load_media_links()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "platform": platform.strip(),
        "url": url.strip(),
        "title": (title or "").strip()[:500],
        "added_at": now,
    }
    links.append(entry)
    save_media_links(links)
    return entry


def remove_media_link(url: str) -> bool:
    """按 url 删除一条"""
    links = load_media_links()
    before = len(links)
    links = [x for x in links if (x.get("url") or "").strip() != url.strip()]
    if len(links) < before:
        save_media_links(links)
        return True
    return False
