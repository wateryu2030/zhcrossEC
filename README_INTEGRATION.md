# OpenClaw + 百度优选 Skill 集成说明

## 架构

```
CPG-Hub 平台
    │
    ├── skills/baidu-preferred/     ← OpenClaw Skill 结构
    │   └── SKILL.md
    │
    ├── agents/baidu_agent.py      ← 调用百度优选能力
    ├── data/sample_baidu.json     ← 演示数据（首屏展示）
    │
    └── static/                    ← 前端（标注百度优选来源）
```

## 首屏展示

启动后访问 http://localhost:8000，页面自动加载：

- **选品分析**：百度优选选品示例（海外 vs 国内同款）
- **热销趋势**：3 条海外热销 + 百度优选国内同款
- **政策动态**：2 条政策 + 百度优选相关选品

数据来自 `data/sample_baidu.json`，通过 `GET /api/v1/demo` 提供。

## 接入真实百度优选

1. **安装 Skill**（若 ClawHub 已上架）：
   ```bash
   clawhub install baidu-preferred
   ```

2. **或复制到 OpenClaw 工作区**：
   ```bash
   cp -r skills/baidu-preferred ~/.openclaw/skills/
   ```

3. **配置 API Key**：在 `~/.openclaw/openclaw.json` 的 `skills.entries` 中配置百度优选所需 Key。

4. **平台调用**：`agents/baidu_agent.py` 当前使用 LLM 模拟，接入真实 API 后替换实现即可。
