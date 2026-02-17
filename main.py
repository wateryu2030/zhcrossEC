"""
CPG-Hub: 跨境电商政策与全球商品集成平台

FastAPI 入口，支持移动端响应式前端、后台自动化同步
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化数据库与数据目录 + 启动后台同步 + 周/日爬虫调度器"""
    from config import settings
    from crawler.db import init_db

    # 启动时确保本平台数据目录与 SQLite 表存在（一切在项目内独立运行）
    init_db()
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 政策库：若扩展 JSON 不存在则自动生成（千条以上），并预加载以加速首请求
    try:
        from agents.policy_legal import get_full_policy_library
        get_full_policy_library()
    except Exception:
        pass

    tasks = []
    if settings.sync_interval_minutes > 0:
        from jobs.scheduler import start_background_scheduler
        tasks.append(start_background_scheduler())
    if settings.sync_accumulate_interval_minutes > 0:
        from jobs.scheduler import start_accumulate_scheduler
        tasks.append(start_accumulate_scheduler())
    from jobs.crawl_jobs import start_crawl_schedulers
    tasks.extend(start_crawl_schedulers())
    yield
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
        except Exception:
            pass


app = FastAPI(
    title="CPG-Hub",
    description="跨境电商政策与全球商品集成平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """返回前端页面"""
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "CPG-Hub API", "docs": "/docs"}


@app.get("/favicon.ico")
async def favicon():
    """favicon，避免 404"""
    fav = static_dir / "favicon.svg"
    if fav.exists():
        return FileResponse(fav, media_type="image/svg+xml")
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/health")
@app.get("/api/v1/health")
async def health():
    """健康检查，用于部署与监控"""
    return {"ok": True, "service": "CPG-Hub", "version": "0.1.0"}
