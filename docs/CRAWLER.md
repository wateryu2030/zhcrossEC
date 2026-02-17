# CPG-Hub 爬虫说明

参考设计：[ahotnews](https://github.com/wateryu2030/ahotnews)（BettaFish 微舆 · 多智能体舆情与关键词检索）

## 1. 政府政策爬虫（周更）

- **目标**：全国各地政府有关跨境电商的管理政策，汇集到数据库并定时检查更新。
- **数据源**：中国政府网、商务部、海关总署、税务总局、各省市商务/综试区（见 `crawler/policy_crawler.py` 中 `GOV_POLICY_SOURCES`）。
- **策略**：抓取列表页中的链接与标题，过滤含「跨境/电商/出口/退税/海外仓/9610/9710/9810/综试区」等关键词的条目，以 `url` 唯一键写入 SQLite，已有则更新。
- **调度**：启动应用后 2 分钟执行首次，之后**每周**执行一次。
- **手动执行**：`python scripts/run_crawl.py policy`
- **API**：`GET /api/v1/policies/db`、`POST /api/v1/crawl/policy`

## 2. 媒体热点爬虫（日更）

- **目标**：抖音、快手等媒体上与跨境电商相关的热点内容，按日检索入库。
- **数据源**：资讯站（亿邦动力、雨果跨境等）+ 抖音/快手（当前为占位，可接 Playwright 或开放平台 API）。
- **策略**：抓取资讯站列表页中与「跨境/电商」相关的标题与链接；抖音/快手需 Cookie 或官方 API，见 `crawler/media_crawler.py` 中 `_fetch_douyin_hot`、`_fetch_kuaishou_hot`。
- **调度**：启动应用后 5 分钟执行首次，之后**每日**执行一次。
- **手动执行**：`python scripts/run_crawl.py media`
- **API**：`GET /api/v1/media_hot`、`POST /api/v1/crawl/media`

## 3. 数据库

- **路径**：`data/crawler.db`（SQLite）
- **表**：
  - `policy`：政策（source_org, region, title, url, content_snippet, publish_date, category, crawled_at, updated_at）
  - `media_hot`：媒体热点（platform, title, url, author, publish_date, content_snippet, keywords, heat_score, crawled_at）
- **初始化**：首次调用 `run_policy_crawl` 或 `run_media_crawl` 时自动执行 `init_db()`。

## 4. 扩展抖音/快手

在 `crawler/media_crawler.py` 中：

- **抖音**：接入 [抖音开放平台](https://open.douyin.com/) 搜索 API，或在有 Cookie 的前提下用 Playwright 访问 `https://www.douyin.com/search/跨境电商` 解析结果。
- **快手**：同理，使用快手开放接口或 Playwright 模拟搜索。

可参考 ahotnews 的 MindSpider / MediaCrawler 实现（Playwright + 平台爬虫）。

## 5. ahotnews（MindSpider）集成

使用 [ahotnews](https://github.com/wateryu2030/ahotnews) 按关键词（如「跨境电商」）在抖音、快手、微博等平台爬取，结果同步到本库 `media_hot`。

### 5.1 安装 ahotnews

```bash
./scripts/setup_ahotnews.sh
```

将克隆仓库到 `vendor/ahotnews`。随后：

1. 在 `vendor/ahotnews` 根目录复制 `.env.example` 为 `.env`，配置数据库及 `MINDSPIDER_API_KEY`、`MINDSPIDER_BASE_URL`、`MINDSPIDER_MODEL_NAME`。
2. 安装依赖：`pip install -r requirements.txt`，`playwright install chromium`。
3. 初始化 MindSpider：`cd MindSpider && python main.py --setup`。

### 5.2 CPG-Hub 配置

在项目根目录 `.env` 中增加：

- `AHOTNEWS_ENABLED=true`
- `AHOTNEWS_PATH=vendor/ahotnews`
- `AHOTNEWS_DB_HOST`、`AHOTNEWS_DB_PORT`、`AHOTNEWS_DB_USER`、`AHOTNEWS_DB_PASSWORD`、`AHOTNEWS_DB_NAME`（与 ahotnews 使用的数据库一致，默认 MindSpider 使用 MySQL）
- `AHOTNEWS_DB_DIALECT=mysql`（或 `postgresql`，当前种子关键词仅实现 MySQL）

### 5.3 使用方式

- **API**：`POST /api/v1/crawl/ahotnews?platforms=dy,ks,wb`，执行「写入关键词 → MindSpider 深度爬取 → 同步到 media_hot」。
- **前端**：媒体热点 tab 中点击「从 ahotnews 同步」即可触发。

平台代码：`dy` 抖音、`ks` 快手、`wb` 微博、`xhs` 小红书等（见 ahotnews MindSpider 文档）。

## 6. 我的媒体链接

用户可保存抖音、快手、财新、微博等链接，与爬虫结果一起展示。

- **存储**：`data/media_links.json`（由 `MEDIA_LINKS_FILE` 配置）。
- **API**：`GET /api/v1/media_links` 列表，`POST /api/v1/media_links` 添加（body: `platform`, `url`, `title`），`DELETE /api/v1/media_links?url=...` 删除。
- **与爬虫关系**：`GET /api/v1/media_hot` 会在返回结果前部合并「我的媒体链接」，与库内热点统一展示；链接不写入 `media_hot`，避免重复。
