# 政策数据与筛选（Cursor 自我进化用）

本说明供 Cursor/开发者在修改政策相关功能时保持行为一致。

## 合规场景（分类）统一命名

- **唯一标准**：`agents/policy_legal.py` 中 `COMPLIANCE_SCENARIOS`。
- **取值**：`清关合规`、`财税合规`、`支付合规`、`数据跨境合规`、`知识产权合规`、`行政处罚合规`；未匹配时用 `综合`。
- **别称**：其他 UI 若出现「海关合规」应视为「清关合规」；标引与筛选均用上述 6+1，不混用「银行合规」「新型贸易合规」等。

## 数据流

1. **国内政策**：`crawler/policy_crawler.py` 抓取政府站 + 全网搜索 → `policy_upsert` 写入 MySQL `policy` 表，`region`=中央/省/市，`category`=`infer_scenario_from_text(...)`。
2. **丝路电商 36 国**：`scripts/fetch_silk_road_policies.py` 调用 Perplexity/OpenRouter 按国搜索 → 写入 `policy` 表，`country`=该国，`source_org`=丝路电商搜索。
3. **前端「从数据库加载」**：`GET /api/v1/policies/db?region=&category=&country=&limit=` → `list_policies(region, category, country)`，返回列表 + `regions/categories/countries` 供下拉；分类筛选为 **精确匹配** `WHERE category = ?`。

## 政策选择不对时检查

- 前端「分类」下拉选项来自 **数据库** `list_policy_categories()`（即表中已出现的 category），若库内多为「综合」或旧值，可跑 `run_policy_full_sync.sh` 重新抓取并标引。
- 筛选不生效：确认请求 URL 带 `category=`、`region=`、`country=`；后端 `list_policies` 仅在有值时加 WHERE。
- 与法务政策库（千条+）不一致：法务政策库来自 `get_full_policy_library()` 与搜索 API；「从数据库加载」来自 MySQL 爬虫。两者数据源不同，筛选逻辑独立。

## 数据更新不对时检查

- 政策表最新时间：`get_policy_latest_crawled_at()`；前端从 `latest_crawled_at` 展示「最后更新」。
- 未更新：确认 MySQL 可连、爬虫周任务已跑（`jobs/crawl_jobs.py` 的 `scheduler_weekly_loop`）或手动执行 `bash scripts/run_policy_full_sync.sh`。
- 服务启动时：`main.py` lifespan 会启动 `start_accumulate_scheduler`（每 15 分钟）和 `start_crawl_schedulers`（每周政策、每日媒体），若 `sync_interval_minutes=0` 则仅积累与爬虫在跑。

## 修改时的约定

- 增删合规场景：只改 `policy_legal.py` 的 `COMPLIANCE_SCENARIOS` 与 `SCENARIO_KEYWORDS`，并确保 `infer_scenario_from_text` 返回值在此集合内。
- 增删筛选维度：改 `list_policies` 参数与 SQL、`GET /policies/db` 查询参数、前端下拉与 `loadPoliciesFromDb` 的 params。
- 新增数据源：若仍写入 `policy` 表，保持 `region`/`country`/`category` 含义一致；若新表，需在 API 层合并或前端分 tab。
