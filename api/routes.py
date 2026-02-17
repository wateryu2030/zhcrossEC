"""
API 路由

- GET /api/v1/demo: 百度优选 + OpenClaw 演示数据（首屏展示）
- GET /api/v1/trending: 百度优选热销与海外趋势重合产品
- GET /api/v1/policies: 最新跨境电商相关政策摘要
- POST /api/v1/analyze: 输入 Amazon 链接，寻找国内同款并对比
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.baidu_agent import search_products as baidu_search_products
from agents.policy_agent import POLICY_LIBRARY, get_policy_categories
from agents.policy_legal import REGION_LABELS, TARGET_REGIONS, get_legal_policies, get_full_policy_library
from services.llm_service import chat_completion
from core.analyzer import run_selection_pipeline
from services.compare_service import compare_amazon_with_domestic
from services.overseas_scraper import search_amazon

router = APIRouter(prefix="/api/v1", tags=["api"])


class AnalyzeRequest(BaseModel):
    """分析请求体"""

    amazon_url: str  # Amazon 链接或 ASIN


def _policy_to_search_keywords(category: str, tags: list, impact: dict) -> str:
    """从政策提取百度优选检索关键词（兼容合规场景与旧 category）"""
    mapping = {
        "清关合规": "跨境物流 海外仓 通关 商品",
        "财税合规": "电子产品 出口 退税",
        "支付合规": "跨境支付 商品",
        "数据跨境合规": "跨境电商 数据 合规",
        "知识产权合规": "跨境电商 知识产权 商品",
        "行政处罚合规": "跨境电商 合规 监管",
        "出口退税": "电子产品 出口",
        "物流": "跨境物流 海外仓 商品",
        "合规": "跨境电商 合规 商品",
        "补贴": "消费品 出口",
        "监管": "跨境电商 热销",
        "综合": "跨境电商 选品",
    }
    kw = mapping.get(category, "跨境电商 选品")
    if tags:
        kw = " ".join(tags[:2]) + " " + kw
    imp_pts = (impact or {}).get("impact_points", [])
    if imp_pts and "退税" in str(imp_pts):
        kw = "出口 电子产品 " + kw
    return kw[:50]


# 真实数据缓存（同步任务写入），不再使用任何 example/sample 文件
SYNC_CACHE_PATH = Path(__file__).parent.parent / "data" / "sync_cache.json"


def _load_sync_cache() -> dict:
    """仅加载同步任务写入的真实数据缓存；无则返回空结构。若存在旧 sample 文件则一次性迁移到 sync_cache。"""
    if SYNC_CACHE_PATH.exists():
        try:
            with open(SYNC_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    # 一次性迁移：旧示范文件 sample_baidu.json → sync_cache.json
    legacy = Path(__file__).parent.parent / "data" / "sample_baidu.json"
    if legacy.exists():
        try:
            with open(legacy, encoding="utf-8") as f:
                data = json.load(f)
            SYNC_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SYNC_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            legacy.unlink()
            return data
        except Exception:
            pass
    return {}


def _policy_row_to_demo(p: dict) -> dict:
    """将政策行（DB 或 LEGAL_POLICY_LIBRARY）转为首屏展示格式，含法务溯源性与废止/修订字段"""
    category = p.get("category", "综合")
    scenario = p.get("applicable_scenario", category)
    content = (p.get("content") or p.get("content_snippet") or "")[:300]
    return {
        "id": str(p.get("id", p.get("url", ""))),
        "title": (p.get("title") or "")[:200],
        "source": p.get("source") or p.get("source_org", ""),
        "url": p.get("url", ""),
        "category": category,
        "applicable_scenario": scenario,
        "target_region": p.get("target_region", "中国"),
        "publish_date": p.get("publish_date", ""),
        "effective_date": p.get("effective_date", ""),
        "repeal_date": p.get("repeal_date", ""),
        "revision_notes": p.get("revision_notes", ""),
        "validity_note": p.get("validity_note", ""),
        "validity_level": p.get("validity_level", ""),
        "risk_level": p.get("risk_level", ""),
        "risk_points": p.get("risk_points", []),
        "impact": {"summary": content},
        "is_repealed": bool(p.get("repeal_date")),
        "baidu_related": {"source": "百度优选", "products": []},
    }


@router.get("/demo")
async def get_demo():
    """
    首屏数据：全部来自真实数据（政策库/DB/同步缓存/媒体库），无 example/sample 示范数据。
    """
    from config import settings
    from crawler.db import list_policies, list_media_hot

    cache = _load_sync_cache()
    warnings: list[str] = []

    # 政策：优先数据库（爬虫），其次法务政策库
    policies_real: list[dict] = []
    try:
        db_policies = list_policies(limit=30)
        if db_policies:
            policies_real = [_policy_row_to_demo({
                "id": r.get("id"), "title": r.get("title"), "source_org": r.get("source_org"),
                "url": r.get("url"), "category": r.get("category"), "publish_date": r.get("publish_date"),
                "content_snippet": r.get("content_snippet"),
                "effective_date": r.get("effective_date"), "validity_level": r.get("validity_level"),
                "risk_level": r.get("risk_level"), "risk_points": r.get("risk_points"),
            }) for r in db_policies]
    except Exception:
        pass
    if not policies_real:
        policies_real = [_policy_row_to_demo(p) for p in POLICY_LIBRARY[:50]]

    # 媒体数量（真实）
    media_count = 0
    try:
        media_count = len(list_media_hot(limit=50))
    except Exception:
        pass

    # 统计：政策数为库总量，其余来自真实
    stats = cache.get("stats", {}) or {}
    try:
        stats["policy_count"] = len(get_full_policy_library())
    except Exception:
        stats["policy_count"] = len(policies_real)
    stats["media_count"] = media_count
    stats.setdefault("updated_at", "真实环境")

    # 热销 / 热门类目 / 行业资讯：仅来自同步缓存（真实）
    trending = cache.get("trending", [])
    hot_categories = cache.get("hot_categories", [])
    industry_news = cache.get("industry_news", [])
    if not trending:
        warnings.append("热销暂无数据：可配置 OMKAR_CLOUD_API_KEY 后到「热销」tab 刷新")
    if not industry_news:
        try:
            media = list_media_hot(limit=10)
            industry_news = [
                {"title": m.get("title", ""), "source": m.get("platform", ""), "date": m.get("publish_date", ""), "summary": (m.get("content_snippet") or "")[:150]}
                for m in media
            ]
        except Exception:
            pass

    # 选品分析示例：仅来自同步缓存，无则空
    analyze_samples = cache.get("analyze_samples", [])
    if not analyze_samples and cache.get("analyze_sample"):
        analyze_samples = [cache["analyze_sample"]]

    # 配置提示
    if not settings.omkar_cloud_api_key:
        warnings.append("可选：配置 OMKAR_CLOUD_API_KEY 可启用海外热销与选品详情（.env）")
    if not (settings.zhipu_api_key or settings.baidu_api_key or settings.openai_api_key):
        warnings.append("未配置 LLM：选品分析与政策 AI 将不可用，请配置 .env")
    if not (settings.perplexity_api_key or settings.openrouter_api_key):
        warnings.append("未配置 PERPLEXITY/OPENROUTER：政策自动搜索不可用，当前为政策库与爬虫")

    data_source = "real" if (policies_real or trending or hot_categories or industry_news) else "mixed" if warnings else "real"

    return {
        "source": "CPG-Hub 真实数据",
        "data_source": data_source,
        "warnings": warnings,
        "stats": stats,
        "hot_categories": hot_categories,
        "industry_news": industry_news,
        "trending": trending,
        "policies": policies_real,
        "analyze_sample": analyze_samples[0] if analyze_samples else {},
        "analyze_samples": analyze_samples,
    }


def _extract_asin(url: str) -> str:
    s = str(url).strip()
    if "amazon" in s.lower() and "/dp/" in s:
        parts = s.split("/dp/")
        if len(parts) >= 2:
            return parts[1].split("/")[0].split("?")[0]
    if "amazon" in s.lower() and "/gp/product/" in s:
        parts = s.split("/gp/product/")
        if len(parts) >= 2:
            return parts[1].split("/")[0].split("?")[0]
    return s


@router.get("/trending")
async def get_trending():
    """返回海外热销 + 百度优选国内同款的重合产品（需配置 OMKAR_CLOUD_API_KEY）。"""
    try:
        # 1. 获取 Amazon 热销（未配置或失败时返回 error）
        data = await search_amazon("best seller", sort_by="best_sellers")
        if data.get("error"):
            return {"items": [], "source": "amazon+百度优选", "error": data["error"]}
        overseas = data.get("results", [])[:5]

        # 2. 对每个热销品，用百度优选找国内同款
        items = []
        for o in overseas:
            title = o.get("title", "")
            price = float(o.get("price") or o.get("current_price") or 0)
            # 提取核心关键词（去掉品牌等）
            kw = title[:30] if title else "热销商品"
            baidu_res = await baidu_search_products(kw, limit=3)
            domestic = baidu_res.get("products", [])
            baidu_source = baidu_res.get("source", "百度优选")
            min_domestic = min((p.get("price") or 0 for p in domestic), default=0)
            price_diff = price - min_domestic if price else 0
            items.append(
                {
                    "overseas": o,
                    "baidu_domestic": {
                        "source": baidu_source,
                        "products": domestic,
                    },
                    "price_diff": round(price_diff, 2),
                    "overseas_price": price,
                }
            )
        return {"items": items, "source": "amazon+百度优选"}
    except Exception as e:
        return {"items": [], "error": str(e)}


@router.get("/policies")
async def get_policies(
    scenario: str | None = None,
    target_region: str | None = None,
    region_label: str | None = None,
    risk_level: str | None = None,
    include_repealed: bool = False,
    limit: int = 300,
):
    """法务自用政策列表：合规场景+目标国+各地+风险等级，千条库检索。返回 total_count 供前端展示「共 N 条」。"""
    try:
        categories = await get_policy_categories()
        # 先取足量以得到匹配总数，再截取当前页
        all_matching = get_legal_policies(
            scenario=scenario,
            target_region=target_region,
            region_label=region_label,
            risk_level=risk_level,
            include_repealed=include_repealed,
            limit=10000,
        )
        total_count = len(all_matching)
        policies = all_matching[:limit]
        out = []
        for p in policies:
            content = (p.get("content") or p.get("title") or "")[:400]
            out.append({
                "id": p.get("id", ""),
                "title": p.get("title", ""),
                "source": p.get("source", ""),
                "url": p.get("url", ""),
                "publish_date": p.get("publish_date", ""),
                "effective_date": p.get("effective_date", ""),
                "repeal_date": p.get("repeal_date", ""),
                "revision_notes": p.get("revision_notes", ""),
                "validity_note": p.get("validity_note", ""),
                "category": p.get("applicable_scenario", "清关合规"),
                "applicable_scenario": p.get("applicable_scenario", "清关合规"),
                "target_region": p.get("target_region", "中国"),
                "region_label": p.get("region_label", "全国"),
                "validity_level": p.get("validity_level", ""),
                "risk_level": p.get("risk_level", ""),
                "risk_points": p.get("risk_points", []),
                "tags": p.get("tags", []),
                "source_tier": p.get("source_tier", ""),
                "impact": {"summary": content, "impact_points": [], "suggestions": [], "risk_level": p.get("risk_level", "")},
                "is_repealed": bool(p.get("repeal_date")),
            })
        return {
            "policies": out,
            "total_count": total_count,
            "categories": categories,
            "target_regions": TARGET_REGIONS,
            "region_labels": REGION_LABELS,
        }
    except Exception as e:
        return {"policies": [], "total_count": 0, "categories": [], "target_regions": [], "region_labels": [], "error": str(e)}


class AnalyzeRegionsRequest(BaseModel):
    """各地政策特点分析请求"""
    region: str = "全部"  # 全部 | 全国 | 杭州 | 广州 | ... 欧盟 | 美国


@router.post("/policies/analyze-regions")
async def analyze_regions_policy(body: AnalyzeRegionsRequest):
    """AI 分析：根据政策库总结指定地区（或全部）政策特点（侧重场景、风险点、差异）。"""
    try:
        region = (body.region or "全部").strip()
        if region == "全部":
            policies = get_full_policy_library()[:500]
            region_desc = "全国各综试区及境外（欧盟/美国等）"
        else:
            policies = get_legal_policies(region_label=region, limit=400)
            region_desc = region
        if not policies:
            return {"region": region_desc, "summary": "暂无该地区政策数据。", "highlights": [], "risk_focus": [], "comparison": ""}
        # 聚合标题与摘要供 LLM
        lines = []
        for i, p in enumerate(policies[:200], 1):
            title = p.get("title", "")
            scenario = p.get("applicable_scenario", "")
            risk = p.get("risk_level", "")
            content = (p.get("content") or "")[:150]
            lines.append(f"{i}. [{scenario}] {title}（风险{risk}） {content}")
        text = "\n".join(lines)
        prompt = f"""你是一位跨境电商法务专家。根据以下政策列表，总结「{region_desc}」的政策特点。

【政策列表】（仅标题与摘要）
{text[:12000]}

请用 JSON 格式输出，不要其他文字：
{{
  "summary": "200字内总结该地区政策侧重哪些合规场景、主要扶持与约束、整体风格",
  "highlights": ["特点1", "特点2", "特点3"],
  "risk_focus": ["主要风险点1", "主要风险点2"],
  "comparison": "与其它地区相比的差异或特色（100字内）"
}}"""
        resp = await chat_completion([{"role": "user", "content": prompt}])
        out = {"region": region_desc, "summary": "", "highlights": [], "risk_focus": [], "comparison": ""}
        if "{" in resp:
            start, end = resp.find("{"), resp.rfind("}") + 1
            try:
                parsed = json.loads(resp[start:end])
                out["summary"] = parsed.get("summary", "")
                out["highlights"] = parsed.get("highlights", [])
                out["risk_focus"] = parsed.get("risk_focus", [])
                out["comparison"] = parsed.get("comparison", "")
            except json.JSONDecodeError:
                out["summary"] = resp[:800]
        else:
            out["summary"] = resp[:800]
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_product(body: AnalyzeRequest):
    """
    输入一个 Amazon 链接，自动调用百度优选寻找国内同款货源并对比参数。
    """
    try:
        result = await compare_amazon_with_domestic(str(body.amazon_url))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{asin}")
async def analyze_by_asin(asin: str):
    """按 ASIN 分析选品推荐。"""
    try:
        recs = await run_selection_pipeline(asin)
        return {"recommendations": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def trigger_sync(mode: str = "all"):
    """
    手动触发自动化同步。
    mode: all | policies | trending
    """
    from jobs.sync_jobs import run_sync_all, run_sync_policies, run_sync_trending

    try:
        if mode == "policies":
            n = await run_sync_policies()
            return {"ok": True, "policies": n}
        if mode == "trending":
            n = await run_sync_trending()
            return {"ok": True, "trending": n}
        result = await run_sync_all()
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 爬虫：政府政策入库 + 媒体热点 ----------

@router.get("/policies/db")
async def get_policies_from_db(region: str | None = None, limit: int = 100):
    """从数据库读取政府政策（爬虫采集，周更）"""
    try:
        from crawler.db import list_policies
        rows = list_policies(limit=limit, region=region)
        return {"policies": rows, "source": "crawler_db"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policies/insights")
async def get_policy_insights(limit: int = 1):
    """政策方向与行动建议（爬虫+分析流水线写入）"""
    try:
        from crawler.db import get_latest_policy_analysis
        rows = get_latest_policy_analysis(limit=limit)
        if not rows:
            return {"insights": [], "message": "暂无洞察，请先运行政策流水线：caffeinate -i python scripts/run_full_policy_pipeline.py"}
        return {"insights": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media_hot")
async def get_media_hot(platform: str | None = None, limit: int = 50):
    """从数据库读取媒体热点，并合并「我的媒体链接」统一展示"""
    try:
        from crawler.db import list_media_hot
        from crawler.media_links import load_media_links
        rows = list_media_hot(limit=limit, platform=platform)
        # 合并用户保存的媒体链接（抖音/快手/财新/微博等），插入到列表前部
        for link in load_media_links():
            rows.insert(0, {
                "platform": link.get("platform", "link"),
                "title": link.get("title", "") or link.get("url", ""),
                "url": link.get("url", ""),
                "author": "我的链接",
                "publish_date": (link.get("added_at") or "")[:10],
                "content_snippet": (link.get("title") or link.get("url", ""))[:500],
                "keywords": "跨境电商",
                "heat_score": 0,
                "crawled_at": link.get("added_at", ""),
            })
        return {"items": rows, "source": "crawler_db"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl/policy")
async def trigger_policy_crawl():
    """手动触发政府政策爬虫（周任务）"""
    try:
        from crawler.policy_crawler import run_policy_crawl
        n = await run_policy_crawl()
        return {"ok": True, "count": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl/media")
async def trigger_media_crawl():
    """手动触发媒体热点爬虫（日任务）"""
    try:
        from crawler.media_crawler import run_media_crawl
        n = await run_media_crawl()
        return {"ok": True, "count": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 媒体链接（抖音/快手/财新/微博等）----------

@router.get("/media_links")
async def get_media_links():
    """获取用户保存的媒体链接列表"""
    try:
        from crawler.media_links import load_media_links
        return {"items": load_media_links()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MediaLinkBody(BaseModel):
    platform: str  # douyin | kuaishou | weibo | caixin | other
    url: str
    title: str = ""


@router.post("/media_links")
async def add_media_link(body: MediaLinkBody):
    """添加一条媒体链接（抖音/快手/财新/微博等）"""
    try:
        from crawler.media_links import add_media_link as do_add
        entry = do_add(body.platform.strip(), body.url.strip(), body.title.strip())
        return {"ok": True, "entry": entry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/media_links")
async def delete_media_link(url: str):
    """按 URL 删除一条媒体链接"""
    try:
        from crawler.media_links import remove_media_link
        ok = remove_media_link(url)
        return {"ok": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- ahotnews 集成 ----------

@router.post("/crawl/ahotnews")
async def trigger_ahotnews_crawl(platforms: str = "dy,ks,wb"):
    """
    使用 ahotnews (MindSpider) 按关键词「跨境电商」爬取抖音、快手、微博等，并同步到 media_hot。
    需先配置 AHOTNEWS_ENABLED=1、AHOTNEWS_PATH、AHOTNEWS_DB_* 并执行 scripts/setup_ahotnews.sh。
    """
    import asyncio
    try:
        from crawler.ahotnews_bridge import run_ahotnews_crawl
        platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
        result = await asyncio.to_thread(run_ahotnews_crawl, platform_list or None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
