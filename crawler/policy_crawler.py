"""
政府政策爬虫

从全国各地政府站点采集「跨境电商」相关管理政策，入库；以周为单位定时检查更新。
参考：中国政府网、商务部、海关、税务、各省市商务/综试区。
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from agents.policy_legal import infer_scenario_from_text, infer_validity_level
from crawler.db import get_db, init_db, policy_upsert

logger = logging.getLogger(__name__)

# 全国政府政策源：中央 + 主要综试区/省市
GOV_POLICY_SOURCES = [
    # 中央
    {"name": "中国政府网政策", "region": "中央", "url": "https://www.gov.cn/zhengce/zuixin.htm", "keywords": ["跨境", "电商", "出口", "退税", "海外仓"]},
    {"name": "商务部政策发布", "region": "中央", "url": "https://www.mofcom.gov.cn/zwgk/zcfb/index.html", "keywords": ["跨境", "电商"]},
    {"name": "商务部电子商务司", "region": "中央", "url": "https://dzsws.mofcom.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "海关总署", "region": "中央", "url": "http://www.customs.gov.cn/", "keywords": ["跨境", "电商", "9610", "9710", "9810"]},
    {"name": "税务总局", "region": "中央", "url": "https://www.chinatax.gov.cn/", "keywords": ["跨境", "出口退税"]},
    # 省市 / 综试区（示例，可扩展）
    {"name": "浙江省商务厅", "region": "浙江", "url": "https://zcom.zj.gov.cn/col/col1228997562/index.html", "keywords": ["跨境"]},
    {"name": "广东省商务厅", "region": "广东", "url": "http://com.gd.gov.cn/", "keywords": ["跨境"]},
    {"name": "深圳市商务局", "region": "深圳", "url": "http://commerce.sz.gov.cn/", "keywords": ["跨境"]},
    {"name": "广州市商务局", "region": "广州", "url": "http://sw.gz.gov.cn/", "keywords": ["跨境"]},
    {"name": "杭州市商务局", "region": "杭州", "url": "http://sww.hangzhou.gov.cn/", "keywords": ["跨境"]},
    {"name": "郑州市商务局", "region": "郑州", "url": "http://zzsw.zhengzhou.gov.cn/", "keywords": ["跨境"]},
    {"name": "成都市商务局", "region": "成都", "url": "http://sww.chengdu.gov.cn/", "keywords": ["跨境"]},
]

KEYWORDS_CROSS_BORDER = re.compile("跨境|电商|出口|退税|海外仓|9610|9710|9810|综试区|保税")


def _normalize_url(base: str, href: str) -> str:
    if not href or href.startswith("#") or href.lower().startswith("javascript:"):
        return ""
    if href.startswith("http"):
        return href
    return urljoin(base, href)


def _extract_links_and_titles(html: str, base_url: str) -> list[tuple[str, str]]:
    """从 HTML 中提取链接与标题（a 标签）"""
    out = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{4,200})</a>', html, re.I):
        href, text = m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()
        url = _normalize_url(base_url, href)
        if url and text and len(text) >= 4:
            out.append((url, text))
    return out


def _infer_risk(title: str, snippet: str) -> tuple[str, list[str]]:
    """根据标题与摘要推断风险等级与风险点（法务标引）"""
    text = (title + " " + (snippet or "")).strip()
    points: list[str] = []
    if "处罚" in text or "违规" in text or "未申报" in text or "禁止" in text:
        points.extend([p for p in ["处罚", "违规", "未申报", "禁止"] if p in text])
        return "高", points[:3]
    if "备案" in text or "申报" in text or "需按规定" in text or "时效" in text:
        if "备案" in text:
            points.append("需关注备案要求")
        if "申报" in text:
            points.append("申报合规")
        if "时效" in text:
            points.append("注意时效")
        return "中", points[:3] if points else ["合规与时效需关注"]
    if "退税" in text or "补贴" in text:
        return "中", ["关注政策适用条件"]
    return "低", []


def _extract_date_from_text(text: str) -> str:
    """从标题或正文提取日期 YYYY-MM"""
    m = re.search(r"20\d{2}[-./年]\s*\d{1,2}[-./月]?", text)
    if m:
        s = m.group(0).replace("年", "-").replace("月", "").replace(".", "-").replace("/", "-")
        parts = re.findall(r"\d+", s)
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1].zfill(2)}"
    return ""


def _hash_content(title: str, url: str, snippet: str) -> str:
    return hashlib.sha256((title + url + (snippet or "")).encode()).hexdigest()[:32]


async def _crawl_one_source(source: dict[str, Any]) -> list[dict[str, Any]]:
    """爬取单个政策源，返回符合关键词的条目"""
    items = []
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            r = await client.get(source["url"])
            if r.status_code != 200:
                return items
            html = r.text[:150000]
            base = source["url"]
            keywords = source.get("keywords", ["跨境", "电商"])
            for url, title in _extract_links_and_titles(html, base):
                if not KEYWORDS_CROSS_BORDER.search(title):
                    continue
                if not any(kw in title for kw in keywords):
                    continue
                if "gov.cn" not in url and "mofcom" not in url and "customs" not in url and "chinatax" not in url:
                    if not url.startswith("http"):
                        continue
                publish_date = _extract_date_from_text(title)
                category = infer_scenario_from_text(title, "", [])
                validity = infer_validity_level(source["name"], title)
                risk_level, risk_points = _infer_risk(title, "")
                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                items.append({
                    "source_org": source["name"],
                    "region": source.get("region", ""),
                    "title": title[:300],
                    "url": url,
                    "content_snippet": title[:500],
                    "publish_date": publish_date,
                    "category": category,
                    "validity_level": validity,
                    "risk_level": risk_level,
                    "risk_points": risk_points,
                    "crawled_at": now,
                    "raw_hash": _hash_content(title, url, title),
                })
    except Exception as e:
        logger.warning("policy crawl %s failed: %s", source.get("url"), e)
    return items


async def run_policy_crawl() -> int:
    """
    执行一轮政府政策爬取并标引（合规场景/效力/风险），结果写入数据库。
    1）政府站爬取；2）全网搜索（Perplexity/官网）结果合并入库。
    """
    init_db()
    total = 0
    async with httpx.AsyncClient() as _:
        for src in GOV_POLICY_SOURCES:
            items = await _crawl_one_source(src)
            with get_db() as conn:
                for row in items:
                    try:
                        policy_upsert(conn, row)
                        total += 1
                    except Exception as e:
                        logger.warning("policy_upsert error: %s", e)

        # 全网政策搜索（政策库+官网抓取）合并入库并标引
        try:
            from agents.policy_agent import fetch_policy_updates
            updates = await fetch_policy_updates()
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for u in updates:
                title = (u.get("title") or "")[:300]
                url = (u.get("url") or "").strip()
                if not url or not title:
                    continue
                source_org = u.get("source") or u.get("source_org") or "搜索"
                content = (u.get("content") or u.get("summary") or "")[:500]
                publish_date = u.get("publish_date") or u.get("date") or ""
                category = u.get("applicable_scenario") or u.get("category") or infer_scenario_from_text(title, content, [])
                validity_level = u.get("validity_level") or infer_validity_level(source_org, title)
                risk_level, risk_points = _infer_risk(title, content)
                row = {
                    "source_org": source_org,
                    "region": "",
                    "title": title,
                    "url": url,
                    "content_snippet": content,
                    "publish_date": publish_date,
                    "category": category,
                    "validity_level": validity_level,
                    "risk_level": risk_level,
                    "risk_points": risk_points,
                    "crawled_at": now,
                    "raw_hash": _hash_content(title, url, content),
                }
                with get_db() as conn:
                    try:
                        policy_upsert(conn, row)
                        total += 1
                    except Exception as e:
                        logger.warning("policy_upsert search item error: %s", e)
        except Exception as e:
            logger.warning("fetch_policy_updates merge failed: %s", e)

    logger.info("policy_crawl done: %d items", total)
    return total
