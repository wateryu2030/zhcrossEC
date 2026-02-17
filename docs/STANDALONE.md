# 独立运行说明

本系统支持**完全在本平台内独立运行**，不依赖本机其他目录或外部服务。

## 本平台内包含的内容

| 类型 | 位置 | 说明 |
|------|------|------|
| 配置 | 项目根目录 `.env` | 仅读取此文件，不读取 `~/.openclaw` |
| 数据库 | `data/crawler.db` | SQLite，政策表、媒体热点表 |
| 演示/缓存 | `data/sample_baidu.json` | 首屏与趋势展示（可无此文件，有内置兜底） |
| 媒体链接 | `data/media_links.json` | 用户保存的抖音/快手/财新/微博链接 |
| 知识缓存 | `data/learned_knowledge.json` | 同步任务生成（可选） |
| 前端 | `static/` | 页面、JS、CSS |
| 爬虫数据 | 同上 SQLite | 政策与媒体热点均由本地爬虫写入 |

## 独立运行方式

1. **仅用项目内配置**  
   复制 `.env.example` 为 `.env`，按需填写；不配置任何 Key 也可启动，首屏使用本地/内置数据。

2. **持续积累内容**  
   `SYNC_ACCUMULATE_INTERVAL_MINUTES=15`（默认）时，每 15 分钟执行一次「政策 + 热销 + OpenClaw/百度优选关键词轮询」，结果追加到 `data/sample_baidu.json`，首屏内容会不断增多。设为 0 可关闭。全量同步（含知识学习）由 `SYNC_INTERVAL_MINUTES` 控制，默认 0。

3. **启动**  
   ```bash
   cd /path/to/crossEC
   pip install -r requirements.txt
   ./scripts/run.sh
   # 或指定端口: ./scripts/run.sh 5002
   ```
   默认端口 **8000**（macOS 上 5000 常被系统 AirPlay 占用）。访问 `http://localhost:8000`。

4. **可选：需要自动同步时**  
   在 `.env` 中设置 `SYNC_INTERVAL_MINUTES=30` 并配置相应 API Key，后台会按间隔拉取政策与热销并更新 `data/`。

## 数据流（独立运行）

- **首屏 /demo**：来自 `data/sample_baidu.json`，缺失时使用内置最小结构。
- **政策**：`/api/v1/policies/db` 从本地 `data/crawler.db` 的 `policy` 表读取；爬虫任务会写入该表。
- **媒体热点**：`/api/v1/media_hot` 从 `media_hot` 表读取，并合并 `data/media_links.json` 中的「我的媒体链接」。

无需 MongoDB、无需 `~/.openclaw`，所有内容均在项目目录内。
