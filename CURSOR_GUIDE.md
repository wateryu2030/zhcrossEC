# Cursor 开发指令速查

本文档提供可直接在 Cursor 中使用的组合指令，用于快速实现 CPG-Hub 各模块。

---

## 文档引用（建议先配置）

在 Cursor 设置中将以下链接添加为 **Documentation 资源**：

- `https://github.com/omkarcloud/amazon-scraper`
- `https://github.com/dfreelon/pyktok`
- `https://github.com/ahmadluay9/Ecommerce-Product-Recommendation-ChatGPT`
- `https://docs.openclaw.ai`

---

## 组合指令示例

### 1. 对比函数（核心逻辑）

```
Cursor, 参考 omkarcloud/amazon-scraper 的数据结构，结合 openclaw 的百度优选 Skill，
帮我写一个对比函数。逻辑是：从 Amazon 抓取热销品 A 的价格，然后在百度优选里搜索同款，
并计算差价。函数放在 services/compare_service.py，输入为 Amazon 链接或 ASIN，
输出为 { overseas_price, domestic_price, price_diff, domestic_products[] }。
```

### 2. 海外数据采集封装

```
参考 dfreelon/pyktok 的用法，在 services/overseas_scraper.py 中封装 TikTok 热门标签
和视频元数据采集函数。支持按 hashtag 或 user 获取约 30 条数据，输出为结构化 JSON，
便于与百度优选热销做重合分析。
```

### 3. Amazon 数据封装

```
参考 omkarcloud/amazon-scraper 的 REST API 用法，在 services/overseas_scraper.py 中
封装 get_amazon_product(asin) 和 search_amazon(query) 函数。使用 OMKAR_CLOUD_API_KEY
环境变量，返回 price、rating、sales_volume、asin 等字段。
```

### 4. 政策摘要（LLM）

```
参考 ahmadluay9/Ecommerce-Product-Recommendation-ChatGPT 的 chatbot.py 逻辑，
在 agents/policy_agent.py 中实现 analyze_policy_impact(policy_content)。
使用 config.settings 中的百度千帆或 OpenAI，对政策原文生成「跨境卖家侧」影响分析，
返回 { summary, impact_points[], suggestions[] }。
```

### 5. 选品引擎集成

```
在 core/analyzer.py 中实现 run_selection_pipeline(amazon_asin)：
1. 调用 overseas_scraper 获取 Amazon 价格与评分
2. 调用 baidu_agent.search_products 用商品标题搜索国内同款
3. 对每个同款调用 get_price_comparison 和 get_user_reviews_analysis
4. 用公式 Score = (Overseas*0.7 - Domestic) * Reputation 计算得分
5. 返回 Score > Threshold 的推荐列表
```

---

## 分步开发建议

| 步骤 | 指令要点 |
|------|----------|
| 1 | 实现 `overseas_scraper.py`：封装 omkarcloud API 和 pyktok |
| 2 | 实现 `baidu_agent.py`：OpenClaw 百度优选 search/compare/reviews |
| 3 | 实现 `compare_service.py`：Amazon → 百度优选 对比函数 |
| 4 | 实现 `policy_agent.py`：Playwright 采集 + LLM 摘要 |
| 5 | 实现 `analyzer.py`：选品公式与推荐逻辑 |
| 6 | 实现 API 路由：/trending, /policies, /analyze |
