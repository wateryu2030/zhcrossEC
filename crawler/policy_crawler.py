"""
政府政策爬虫

从全国各地政府站点采集「跨境电商」相关管理政策，入库；以周为单位定时检查更新。
参考：中国政府网、商务部、海关、税务、各省市商务/综试区。
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from agents.policy_legal import infer_scenario_from_text, infer_validity_level
from crawler.db import get_db, init_db, policy_get_existing_urls, policy_upsert

logger = logging.getLogger(__name__)

# 全国政府政策源：中央（商务部、发改委、国资委、海关、税务）+ 31省及地级市以上跨境电商综试区/商务主管部门
# 持续进化：OpenClaw 自动采集全国政策与网络热点，自我完成进化
GOV_POLICY_SOURCES = [
    # 中央：商务部、发改委、国资委、海关、税务
    {"name": "中国政府网政策", "region": "中央", "url": "https://www.gov.cn/zhengce/zuixin.htm", "keywords": ["跨境", "电商", "出口", "退税", "海外仓"]},
    {"name": "商务部政策发布", "region": "中央", "url": "https://www.mofcom.gov.cn/zwgk/zcfb/index.html", "keywords": ["跨境", "电商"]},
    {"name": "商务部电子商务司", "region": "中央", "url": "https://dzsws.mofcom.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "商务部丝路电商", "region": "中央", "url": "https://www.mofcom.gov.cn/", "keywords": ["丝路电商", "跨境", "电商", "合作"]},
    {"name": "国家发展改革委", "region": "中央", "url": "https://www.ndrc.gov.cn/", "keywords": ["跨境", "电商", "数字经济", "出口"]},
    {"name": "国务院国资委", "region": "中央", "url": "https://www.sasac.gov.cn/", "keywords": ["跨境", "电商", "外贸", "出口"]},
    {"name": "海关总署", "region": "中央", "url": "http://www.customs.gov.cn/", "keywords": ["跨境", "电商", "9610", "9710", "9810"]},
    {"name": "税务总局", "region": "中央", "url": "https://www.chinatax.gov.cn/", "keywords": ["跨境", "出口退税"]},
    # 直辖市
    {"name": "北京市商务局", "region": "北京", "url": "http://sw.beijing.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "天津市商务局", "region": "天津", "url": "http://sw.tj.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "上海市商务委", "region": "上海", "url": "http://sww.sh.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "重庆市商务委", "region": "重庆", "url": "http://sww.cq.gov.cn/", "keywords": ["跨境", "电商"]},
    # 各省商务厅
    {"name": "河北省商务厅", "region": "河北", "url": "http://swt.hebei.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "山西省商务厅", "region": "山西", "url": "http://swt.shanxi.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "辽宁省商务厅", "region": "辽宁", "url": "http://swt.ln.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "吉林省商务厅", "region": "吉林", "url": "http://swt.jl.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "黑龙江省商务厅", "region": "黑龙江", "url": "http://sswt.hlj.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "江苏省商务厅", "region": "江苏", "url": "http://swt.jiangsu.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "浙江省商务厅", "region": "浙江", "url": "https://zcom.zj.gov.cn/col/col1228997562/index.html", "keywords": ["跨境"]},
    {"name": "安徽省商务厅", "region": "安徽", "url": "http://swt.ah.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "福建省商务厅", "region": "福建", "url": "http://swt.fujian.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "江西省商务厅", "region": "江西", "url": "http://swt.jiangxi.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "山东省商务厅", "region": "山东", "url": "http://commerce.shandong.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "河南省商务厅", "region": "河南", "url": "http://hnsswt.henan.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "湖北省商务厅", "region": "湖北", "url": "http://swt.hubei.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "湖南省商务厅", "region": "湖南", "url": "http://swt.hunan.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "广东省商务厅", "region": "广东", "url": "http://com.gd.gov.cn/", "keywords": ["跨境"]},
    {"name": "广西商务厅", "region": "广西", "url": "http://swt.gxzf.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "海南省商务厅", "region": "海南", "url": "http://dofcom.hainan.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "四川省商务厅", "region": "四川", "url": "http://swt.sc.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "贵州省商务厅", "region": "贵州", "url": "http://swt.guizhou.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "云南省商务厅", "region": "云南", "url": "http://swt.yn.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "陕西省商务厅", "region": "陕西", "url": "http://swt.shaanxi.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "甘肃省商务厅", "region": "甘肃", "url": "http://swt.gansu.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "青海省商务厅", "region": "青海", "url": "http://swt.qinghai.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "内蒙古商务厅", "region": "内蒙古", "url": "http://swt.nmg.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "西藏商务厅", "region": "西藏", "url": "http://swt.xizang.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "宁夏商务厅", "region": "宁夏", "url": "http://swt.nx.gov.cn/", "keywords": ["跨境", "电商"]},
    {"name": "新疆商务厅", "region": "新疆", "url": "http://swt.xinjiang.gov.cn/", "keywords": ["跨境", "电商"]},
    # 地级市以上综试区/商务局（跨境电商重点城市）
    {"name": "深圳市商务局", "region": "深圳", "url": "http://commerce.sz.gov.cn/", "keywords": ["跨境"]},
    {"name": "广州市商务局", "region": "广州", "url": "http://sw.gz.gov.cn/", "keywords": ["跨境"]},
    {"name": "杭州市商务局", "region": "杭州", "url": "http://sww.hangzhou.gov.cn/", "keywords": ["跨境"]},
    {"name": "宁波市商务局", "region": "宁波", "url": "http://swj.ningbo.gov.cn/", "keywords": ["跨境"]},
    {"name": "郑州市商务局", "region": "郑州", "url": "http://zzsw.zhengzhou.gov.cn/", "keywords": ["跨境"]},
    {"name": "成都市商务局", "region": "成都", "url": "http://sww.chengdu.gov.cn/", "keywords": ["跨境"]},
    {"name": "苏州市商务局", "region": "苏州", "url": "http://swj.suzhou.gov.cn/", "keywords": ["跨境"]},
    {"name": "青岛市商务局", "region": "青岛", "url": "http://commerce.qingdao.gov.cn/", "keywords": ["跨境"]},
    {"name": "长沙市商务局", "region": "长沙", "url": "http://sww.changsha.gov.cn/", "keywords": ["跨境"]},
    {"name": "合肥市商务局", "region": "合肥", "url": "http://swj.hefei.gov.cn/", "keywords": ["跨境"]},
    {"name": "西安市商务局", "region": "西安", "url": "http://swj.xa.gov.cn/", "keywords": ["跨境"]},
    {"name": "天津市商务局", "region": "天津", "url": "http://sw.tj.gov.cn/", "keywords": ["跨境"]},
    {"name": "大连市商务局", "region": "大连", "url": "http://swj.dl.gov.cn/", "keywords": ["跨境"]},
    {"name": "厦门市商务局", "region": "厦门", "url": "http://sw.xm.gov.cn/", "keywords": ["跨境"]},
    {"name": "南京市商务局", "region": "南京", "url": "http://swj.nanjing.gov.cn/", "keywords": ["跨境"]},
    {"name": "无锡市商务局", "region": "无锡", "url": "http://swj.wuxi.gov.cn/", "keywords": ["跨境"]},
    {"name": "东莞市商务局", "region": "东莞", "url": "http://dgboc.dg.gov.cn/", "keywords": ["跨境"]},
    {"name": "佛山市商务局", "region": "佛山", "url": "http://www.fscom.foshan.gov.cn/", "keywords": ["跨境"]},
    {"name": "珠海市商务局", "region": "珠海", "url": "http://swj.zhuhai.gov.cn/", "keywords": ["跨境"]},
    {"name": "济南市商务局", "region": "济南", "url": "http://swj.jinan.gov.cn/", "keywords": ["跨境"]},
    {"name": "武汉市商务局", "region": "武汉", "url": "http://sw.wuhan.gov.cn/", "keywords": ["跨境"]},
    {"name": "沈阳市商务局", "region": "沈阳", "url": "http://swj.shenyang.gov.cn/", "keywords": ["跨境"]},
    {"name": "哈尔滨市商务局", "region": "哈尔滨", "url": "http://swj.harbin.gov.cn/", "keywords": ["跨境"]},
    {"name": "昆明市商务局", "region": "昆明", "url": "http://swj.km.gov.cn/", "keywords": ["跨境"]},
    {"name": "南宁市商务局", "region": "南宁", "url": "http://swj.nanning.gov.cn/", "keywords": ["跨境"]},
    {"name": "兰州市商务局", "region": "兰州", "url": "http://swj.lanzhou.gov.cn/", "keywords": ["跨境"]},
    {"name": "乌鲁木齐市商务局", "region": "乌鲁木齐", "url": "http://swj.urumqi.gov.cn/", "keywords": ["跨境"]},
    {"name": "石家庄市商务局", "region": "石家庄", "url": "http://swj.sjz.gov.cn/", "keywords": ["跨境"]},
    {"name": "太原市商务局", "region": "太原", "url": "http://swj.taiyuan.gov.cn/", "keywords": ["跨境"]},
    {"name": "南昌市商务局", "region": "南昌", "url": "http://swj.nanchang.gov.cn/", "keywords": ["跨境"]},
    {"name": "福州市商务局", "region": "福州", "url": "http://swj.fuzhou.gov.cn/", "keywords": ["跨境"]},
    {"name": "贵阳市商务局", "region": "贵阳", "url": "http://swj.guiyang.gov.cn/", "keywords": ["跨境"]},
    {"name": "海口市商务局", "region": "海口", "url": "http://swj.haikou.gov.cn/", "keywords": ["跨境"]},
]

KEYWORDS_CROSS_BORDER = re.compile("跨境|电商|出口|退税|海外仓|9610|9710|9810|综试区|保税")

# 有内文过滤：标题过短视为无实际内容；可选拉取详情页校验正文长度
MIN_TITLE_LEN = 10
MIN_BODY_LEN_IF_FETCH = 80
# 为 True 时会请求每条政策的详情页并过滤正文过短的（请求量大、耗时长）
ENABLE_FETCH_DETAIL_TO_FILTER = False


def _normalize_title_for_dedup(title: str) -> str:
    """规范化标题用于同轮去重（去空格、小写）。"""
    if not title:
        return ""
    return re.sub(r"\s+", " ", title.strip()).lower()


def _normalize_url(base: str, href: str) -> str:
    if not href or href.startswith("#") or href.lower().startswith("javascript:"):
        return ""
    if href.startswith("http"):
        return href
    return urljoin(base, href)


def _extract_links_and_titles(html: str, base_url: str) -> list[tuple[str, str]]:
    """从 HTML 中提取链接与标题（a 标签），标题过短的不收（视为无实际内容）。"""
    out = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{4,200})</a>', html, re.I):
        href, text = m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()
        url = _normalize_url(base_url, href)
        if url and text and len(text.strip()) >= MIN_TITLE_LEN:
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


# 单源超时（秒），避免慢站拖死整轮
_CRAWL_SOURCE_TIMEOUT = 8.0
_DETAIL_PAGE_TIMEOUT = 6.0


async def _fetch_body_length(client: httpx.AsyncClient, url: str) -> int:
    """请求详情页并返回正文长度（strip 标签后字符数），失败或超时返回 0。"""
    try:
        r = await asyncio.wait_for(client.get(url), timeout=_DETAIL_PAGE_TIMEOUT)
        if r.status_code != 200:
            return 0
        html = r.text[:200000]
        # 去掉 script/style，再 strip 标签，取正文
        html = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
        html = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", html, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return len(text)
    except Exception:
        return 0


def _classify_crawl_error(e: Exception) -> str:
    """将异常归类为 DNS / timeout / other，便于汇总统计。"""
    err_str = str(e).lower()
    if "nodename nor servname" in err_str or "getaddrinfo" in err_str or "errno 8" in err_str:
        return "DNS"
    if "timeout" in err_str or "timed out" in err_str:
        return "timeout"
    if "connection" in err_str or "refused" in err_str or "attempts failed" in err_str:
        return "connection"
    return "other"


async def _crawl_one_source(source: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """爬取单个政策源，返回 (符合关键词的条目, 错误类型或 None)。"""
    items = []
    try:
        async with httpx.AsyncClient(timeout=_CRAWL_SOURCE_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(source["url"])
            if r.status_code != 200:
                return items, None
            html = r.text[:150000]
            base = source["url"]
            keywords = source.get("keywords", ["跨境", "电商"])
            for url, title in _extract_links_and_titles(html, base):
                if not KEYWORDS_CROSS_BORDER.search(title):
                    continue
                if not any(kw in title for kw in keywords):
                    continue
                allowed_domains = ("gov.cn", "mofcom", "customs", "chinatax", "ndrc.gov.cn", "sasac.gov.cn")
                if not any(d in url for d in allowed_domains) and not url.startswith("http"):
                    continue
                # 无内文过滤：可选请求详情页，正文过短则跳过
                if ENABLE_FETCH_DETAIL_TO_FILTER:
                    body_len = await _fetch_body_length(client, url)
                    if body_len < MIN_BODY_LEN_IF_FETCH:
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
        return items, None
    except Exception as e:
        kind = _classify_crawl_error(e)
        logger.debug("policy crawl %s failed [%s]: %s", source.get("url"), kind, e)
        return items, kind


async def _run_insights_then_done(insights_fn):
    """后台执行政策分析（方向与行动建议），完成后自动发飞书；不阻塞爬虫返回。"""
    try:
        await insights_fn()
    except Exception as e:
        logger.warning("policy_insights task error: %s", e)


async def run_policy_crawl() -> int:
    """
    执行一轮政府政策爬取并标引（合规场景/效力/风险），结果写入数据库。
    1）政府站爬取；2）全网搜索（Perplexity/官网）结果合并入库。
    有新增政策时会后台触发 AI 分析并写 policy_analysis、发飞书给余为军。
    失败源按类型汇总输出，避免单条刷屏。
    """
    init_db()
    total = 0
    n_sources = len(GOV_POLICY_SOURCES)
    failures: dict[str, list[str]] = {"DNS": [], "timeout": [], "connection": [], "other": []}
    seen_titles: set[str] = set()  # 同轮按规范化标题去重，避免重复政策
    with get_db() as conn:
        existing_urls = policy_get_existing_urls(conn)
    new_count = 0
    new_sample_titles: list[str] = []
    async with httpx.AsyncClient() as _:
        for i, src in enumerate(GOV_POLICY_SOURCES):
            if (i + 1) % 15 == 0 or i == 0:
                logger.info("policy_crawl progress: %d/%d", i + 1, n_sources)
            items, err_kind = await _crawl_one_source(src)
            if err_kind and err_kind in failures:
                failures[err_kind].append(src.get("url", ""))
            with get_db() as conn:
                for row in items:
                    norm_title = _normalize_title_for_dedup(row.get("title", ""))
                    if norm_title and norm_title in seen_titles:
                        continue
                    if norm_title:
                        seen_titles.add(norm_title)
                    url = (row.get("url") or "").strip()
                    is_new = url and url not in existing_urls
                    try:
                        policy_upsert(conn, row)
                        total += 1
                        if is_new:
                            existing_urls.add(url)
                            new_count += 1
                            if len(new_sample_titles) < 10:
                                new_sample_titles.append((row.get("title") or "")[:80])
                    except Exception as e:
                        logger.warning("policy_upsert error: %s", e)

        # 全网政策搜索（政策库+官网抓取）合并入库并标引
        try:
            from agents.policy_agent import fetch_policy_updates
            updates = await fetch_policy_updates()
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for u in updates:
                title = (u.get("title") or "").strip()[:300]
                url = (u.get("url") or "").strip()
                if not url or not title or len(title) < MIN_TITLE_LEN:
                    continue
                norm_title = _normalize_title_for_dedup(title)
                if norm_title and norm_title in seen_titles:
                    continue
                if norm_title:
                    seen_titles.add(norm_title)
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
                url = row.get("url", "").strip()
                is_new = url and url not in existing_urls
                with get_db() as conn:
                    try:
                        policy_upsert(conn, row)
                        total += 1
                        if is_new:
                            existing_urls.add(url)
                            new_count += 1
                            if len(new_sample_titles) < 10:
                                new_sample_titles.append((row.get("title") or "")[:80])
                    except Exception as e:
                        logger.warning("policy_upsert search item error: %s", e)
        except Exception as e:
            logger.warning("fetch_policy_updates merge failed: %s", e)

    if new_count > 0:
        try:
            from config import settings as s
            if s.feishu_app_id and s.feishu_app_secret and s.feishu_notify_open_id:
                from services.feishu_notify import notify_new_policies
                notify_new_policies(new_count, new_sample_titles)
        except Exception as e:
            logger.warning("feishu notify failed: %s", e)
        try:
            from config import settings as s
            if s.wecom_corp_id and s.wecom_agent_id and s.wecom_agent_secret:
                from services.wecom_notify import notify_new_policies as wecom_notify_new
                wecom_notify_new(new_count, new_sample_titles)
        except Exception as e:
            logger.warning("wecom notify failed: %s", e)
        try:
            from jobs.policy_analysis_job import run_policy_insights
            asyncio.create_task(_run_insights_then_done(run_policy_insights))
        except Exception as e:
            logger.warning("policy_insights task schedule failed: %s", e)

    failed_counts = {k: len(v) for k, v in failures.items() if v}
    if failed_counts:
        summary = "; ".join(f"{k}: {c}" for k, c in failed_counts.items())
        logger.info("policy_crawl done: %d items; %d sources failed (%s)", total, sum(failed_counts.values()), summary)
        if failed_counts.get("DNS", 0) > 5:
            logger.info("(DNS 失败多为本机无法解析政府域名，不影响已成功源与全网搜索合并结果)")
        if logger.isEnabledFor(logging.DEBUG):
            for k, urls in failures.items():
                for u in urls:
                    logger.debug("  %s %s", k, u)
    else:
        logger.info("policy_crawl done: %d items", total)
    return total
