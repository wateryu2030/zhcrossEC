# 数据库说明

## MySQL（主数据库）

政策、媒体热点、政策分析等均存储在 **MySQL** 中，便于备份、权限与生产环境统一管理。

- **配置**: `.env` 中 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`
- **初始化**: 应用启动时执行 `crawler.db.init_db()`；若库不存在会自动创建，再创建表及索引。

### 表结构

#### policy（政府政策 / 丝路电商伙伴国政策）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 自增主键 |
| source_org | VARCHAR(255) | 来源机构 |
| region | VARCHAR(128) | 地区（省市） |
| title | VARCHAR(500) | 标题 |
| url | VARCHAR(1024) | 链接（UNIQUE，插入冲突则 ON DUPLICATE KEY UPDATE） |
| content_snippet | TEXT | 摘要 |
| publish_date | VARCHAR(64) | 发布日期 |
| category | VARCHAR(128) | 分类 |
| crawled_at | VARCHAR(64) | 爬取时间 |
| updated_at | VARCHAR(64) | 更新时间 |
| raw_hash | VARCHAR(64) | 原始内容哈希 |
| country | VARCHAR(64) | 丝路电商伙伴国（可选） |
| validity_level, risk_level, risk_points, effective_date, repeal_date | 法务维度 |

索引：`uk_url`、`idx_policy_crawled`、`idx_policy_region`、`idx_policy_country`。

#### media_hot（媒体热点）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 自增主键 |
| platform | VARCHAR(64) | 平台 |
| title | VARCHAR(500) | 标题 |
| url | VARCHAR(1024) | 链接 |
| author | VARCHAR(128) | 作者/来源 |
| publish_date | VARCHAR(64) | 发布日期 |
| content_snippet | TEXT | 摘要 |
| keywords | VARCHAR(255) | 关键词 |
| heat_score | INT | 热度分 |
| crawled_at | VARCHAR(64) | 爬取时间 |

索引：`idx_media_platform`、`idx_media_crawled`。

#### policy_analysis（政策洞察）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 自增主键 |
| scope | VARCHAR(128) | 范围 |
| summary | TEXT | 摘要 |
| directions | TEXT | 方向（JSON 数组） |
| action_items | TEXT | 行动项（JSON 数组） |
| source | VARCHAR(255) | 来源 |
| created_at | VARCHAR(64) | 创建时间 |

### 首次部署

1. 安装 MySQL 5.7+ 或 8.0，并启动服务。
2. 在 `.env` 中配置 `MYSQL_*`；若 `MYSQL_DATABASE` 所指库不存在，首次调用 `init_db()` 时会自动建库。
3. 启动应用或执行 `python3 -c "from crawler.db import init_db; init_db()"` 完成建表。

## 媒体链接（JSON）

- **路径**: `data/media_links.json`（可由 `MEDIA_LINKS_FILE` 配置）
- **格式**: `[{"platform","url","title","added_at"}, ...]`
- 不写入 MySQL，由 `GET /api/v1/media_hot` 在返回结果前部合并展示。

## MongoDB（可选）

- 配置项：`MONGODB_URI`
- 当前版本未在核心流程中使用，仅作预留。
