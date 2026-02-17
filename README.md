# CPG-Hub: 跨境电商政策与全球商品集成平台

## 项目愿景

构建一个基于 OpenClaw 框架的智能选品与政策监控平台。利用「百度优选」的国内供应链优势，对标 TikTok/Amazon 海外热度，实现「情报错位」竞争。

---

## 开发逻辑总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CPG-Hub 实现框架                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│  │ 海外电商数据采集   │    │ 国内供应链数据    │    │ 政策监控与摘要    │     │
│  │ (选品数据源)      │    │ (百度优选 Skill)  │    │ (Playwright+LLM)  │     │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘     │
│           │                       │                       │                │
│           │  omkarcloud/          │  OpenClaw              │  mofcom.gov   │
│           │  amazon-scraper       │  search_products       │  customs.gov  │
│           │  dfreelon/pyktok      │  get_price_comparison  │  ahmadluay9/   │
│           │  (TikTok 热度)         │  get_user_reviews      │  Ecommerce-   │
│           │                       │                        │  Recommendation│
│           └───────────┬───────────┴───────────┬───────────┘                │
│                       │                       │                             │
│                       ▼                       ▼                             │
│              ┌─────────────────────────────────────────┐                     │
│              │         选品逻辑引擎 (analyzer.py)       │                     │
│              │  Score = (Overseas*0.7 - Domestic)     │                     │
│              │            * User_Reputation_Score      │                     │
│              └─────────────────────┬───────────────────┘                     │
│                                  │                                          │
│                                  ▼                                          │
│              ┌─────────────────────────────────────────┐                     │
│              │  API / 前端看板                           │                     │
│              │  /trending  /policies  /analyze           │                     │
│              └─────────────────────────────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 框架 | Python 3.10+, FastAPI | API 服务 |
| AI | OpenClaw + 百度优选 Skill | 国内商品检索、比价、口碑 |
| 海外数据 | omkarcloud/amazon-scraper, pyktok | Amazon/TikTok 热销与趋势 |
| 政策 | Playwright + LLM (百度千帆) | 政府官网采集 + AI 摘要 |
| 数据库 | MongoDB | 政策与商品快照 |
| 参考 | brightdata/amazon-product-analyzer | 趋势分析看板设计 |
| 参考 | ahmadluay9/Ecommerce-Product-Recommendation-ChatGPT | LLM 处理文本生成摘要 |

---

## 核心模块实现要求

### 模块 1: 海外电商数据采集 (`/services/overseas_scraper.py`)

**不自己写爬虫**，直接引用 GitHub 成熟工具：

| 工具 | 仓库 | 用途 | 输出 |
|------|------|------|------|
| **Amazon Scraper** | [omkarcloud/amazon-scraper](https://github.com/omkarcloud/amazon-scraper) | 产品价格、排名、详情 | JSON/CSV，含 `price`, `asin`, `rating`, `sales_volume` |
| **Pyktok** | [dfreelon/pyktok](https://github.com/dfreelon/pyktok) | TikTok 热门视频、标签、商品热度 | CSV，视频元数据、评论 |
| **参考** | [brightdata/amazon-product-analyzer](https://brightdata.com/blog/ai/amazon-product-analyzer) | 商品趋势分析、交互式看板 | 前端与算法设计参考 |

**omkarcloud/amazon-scraper 数据结构示例**（用于对比函数）：

```json
{
  "title": "Apple iPhone 15, 128GB, Black",
  "price": 403.0,
  "rating": 4.1,
  "reviews": 2769,
  "asin": "B0CMPMY9ZZ",
  "link": "https://www.amazon.com/dp/B0CMPMY9ZZ",
  "currency": "USD",
  "sales_volume": "2K+ bought in past month"
}
```

**组合指令示例**（给 Cursor）：

> "参考 omkarcloud/amazon-scraper 的数据结构，结合 OpenClaw 的百度优选 Skill，帮我写一个对比函数。逻辑是：从 Amazon 抓取热销品 A 的价格，然后在百度优选里搜索同款，并计算差价。"

---

### 模块 2: OpenClaw 百度优选集成 (`/agents/baidu_agent.py`)

| 能力 | 函数 | 用途 |
|------|------|------|
| 精准搜索 | `search_products` | 检索 CPS 商品库 |
| 多维比价 | `get_price_comparison` | 京东/天猫/拼多多价格曲线 |
| 口碑聚合 | `get_user_reviews_analysis` | AI 优缺点摘要 |

选品公式中的 `Domestic_Price` 来自 `get_price_comparison`，`User_Reputation_Score` 来自 `get_user_reviews_analysis`。

---

### 模块 3: 政策爬虫与 AI 摘要 (`/agents/policy_agent.py`)

1. **采集**：Playwright 抓取 `mofcom.gov.cn`、`customs.gov.cn`
2. **摘要**：参考 [ahmadluay9/Ecommerce-Product-Recommendation-ChatGPT](https://github.com/ahmadluay9/Ecommerce-Product-Recommendation-ChatGPT) 的 `chatbot.py` 逻辑，用 LLM（百度千帆/OpenAI）对政策原文做「跨境卖家侧」影响分析。

---

### 模块 4: 选品逻辑引擎 (`/core/analyzer.py`)

```
Score = (Overseas_Price * 0.7 - Domestic_Price) * User_Reputation_Score
```

当 `Score > Threshold` 且符合当前 `Policy` 导向时，推送到前端看板。

---

## 待实现 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/trending` | 百度优选热销与海外趋势重合产品 |
| GET | `/api/v1/policies` | 最新跨境电商相关政策摘要 |
| POST | `/api/v1/analyze` | 输入 Amazon 链接 → 百度优选找同款 → 对比参数与差价 |

---

## 如何让 Cursor 引用这些仓库

### 1. 添加 Documentation 资源

在 Cursor 设置中将以下链接添加为 Documentation 资源，便于实时阅读：

- `https://github.com/omkarcloud/amazon-scraper`
- `https://github.com/dfreelon/pyktok`
- `https://github.com/ahmadluay9/Ecommerce-Product-Recommendation-ChatGPT`
- `https://docs.openclaw.ai`

### 2. 组合指令示例

```
"Cursor, 参考 omkarcloud/amazon-scraper 的数据结构，结合 openclaw 的百度优选 Skill，
帮我写一个对比函数。逻辑是：从 Amazon 抓取热销品 A 的价格，然后在百度优选里搜索同款，
并计算差价。"
```

---

## 项目目录结构

```
crossEC/
├── README.md
├── CURSOR_GUIDE.md          # Cursor 开发指令速查
├── .env.example
├── requirements.txt
├── main.py
├── config.py
├── agents/
│   ├── baidu_agent.py       # 百度优选 Skill
│   └── policy_agent.py      # 政策监控 + LLM 摘要
├── services/
│   ├── overseas_scraper.py  # Amazon/TikTok 采集（封装 omkarcloud、pyktok）
│   └── compare_service.py   # 海外 vs 国内 对比逻辑
├── core/
│   └── analyzer.py          # 选品引擎
├── api/
│   └── routes.py
├── models/
└── ...
```

---

## 快速启动

```bash
./run.sh              # 开发模式（前台）
./run_daemon.sh       # 后台运行（锁屏后继续）
./stop_daemon.sh      # 停止后台
```

**锁屏后继续工作**：详见 [RUN_BACKGROUND.md](RUN_BACKGROUND.md)，支持 LaunchAgent 登录即启动。

**爬虫（政策周更 + 媒体日更）**：详见 [docs/CRAWLER.md](docs/CRAWLER.md)。政府政策入库 `data/crawler.db`，媒体热点同库；手动执行 `python scripts/run_crawl.py`。**政策全流水线（抓取+标引+方向与建议）**：`caffeinate -i python scripts/run_full_policy_pipeline.py`（任务完成前禁止锁屏时使用）。

**政策库（千条以上）**：启动时若 `data/legal_policies_expanded.json` 不存在会自动生成，无需手动执行。需重新生成时可运行 `python scripts/generate_expanded_policies.py`。

**上传 GitHub**：本地已初始化 Git 并完成首次提交。在 GitHub 新建仓库后执行：

```bash
git remote add origin https://github.com/你的用户名/仓库名.git
git branch -M main
git push -u origin main
```

注意：`.env`、`data/crawler.db`、`vendor/` 已忽略，不会推送；克隆后需复制 `.env.example` 为 `.env` 并填写 Key。

---

## 环境变量与 API Key

参照 `.env.example`。**补充资源**（可选）：

| 服务 | 用途 |
|------|------|
| **ScrapingAnt** | 开源爬虫建议配置，自动处理验证码和 IP 封禁 |
| **Apify** | 若本地跑爬虫不便，可调用 Apify 的现成 Actor 接口 |
| **omkar.cloud** | amazon-scraper 官方 API，5000 次/月免费 |
