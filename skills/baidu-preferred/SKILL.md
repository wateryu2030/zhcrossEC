---
name: baidu-preferred
description: 百度优选官方电商 Skill - CPS 商品库检索、跨平台比价、口碑分析。用于跨境电商选品，对接国内供应链。
metadata: {"openclaw":{"emoji":"🛒","homepage":"https://www.clawhub.com/","requires":{"env":[]}}}
---

# 百度优选 · 跨境电商选品 Skill

基于 OpenClaw + ClawHub 的百度优选官方电商能力，为 CPG-Hub 平台提供：

- **search_products**: 检索 CPS 商品库（京东/天猫/拼多多）
- **get_price_comparison**: SPU 跨平台比价
- **get_user_reviews_analysis**: AI 口碑摘要

## 安装

```bash
clawhub install baidu-preferred
```

或复制本目录到 OpenClaw 工作区 `/skills` 或 `~/.openclaw/skills`。

## 与 CPG-Hub 集成

CPG-Hub 通过 `agents/baidu_agent.py` 调用本 Skill 能力，实现：

- 选品分析：Amazon 链接 → 百度优选找同款 → 差价对比
- 热销趋势：海外热销 + 百度优选国内货源
- 政策选品：政策分类 → 百度优选相关商品
