# 数据库说明

## SQLite（爬虫与媒体热点）

- **路径**: `data/crawler.db`
- **初始化**: 应用启动时自动执行 `crawler.db.init_db()`，无需手动建表。

### 表结构

#### policy（政府政策）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| source_org | TEXT | 来源机构 |
| region | TEXT | 地区 |
| title | TEXT | 标题 |
| url | TEXT | 链接（UNIQUE，插入时冲突则更新） |
| content_snippet | TEXT | 摘要 |
| publish_date | TEXT | 发布日期 |
| category | TEXT | 分类 |
| crawled_at | TEXT | 爬取时间 |
| updated_at | TEXT | 更新时间 |
| raw_hash | TEXT | 原始内容哈希 |

索引：`url`、`crawled_at`、`region`。

#### media_hot（媒体热点）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| platform | TEXT | 平台（如 news/dy/ks/weibo） |
| title | TEXT | 标题 |
| url | TEXT | 链接 |
| author | TEXT | 作者/来源 |
| publish_date | TEXT | 发布日期 |
| content_snippet | TEXT | 摘要 |
| keywords | TEXT | 关键词 |
| heat_score | INTEGER | 热度分 |
| crawled_at | TEXT | 爬取时间 |

索引：`platform`、`crawled_at`。

## 媒体链接（JSON）

- **路径**: `data/media_links.json`（可由 `MEDIA_LINKS_FILE` 配置）
- **格式**: `[{"platform","url","title","added_at"}, ...]`
- 不写入 SQLite，由 `GET /api/v1/media_hot` 在返回结果前部合并展示。

## MongoDB（可选）

- 配置项：`MONGODB_URI`
- 当前版本未在核心流程中使用，仅作预留。
