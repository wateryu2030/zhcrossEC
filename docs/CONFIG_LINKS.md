# 完善配置的具体链接

将以下 Key 填入项目根目录 `.env`（可复制 `.env.example` 为 `.env` 后编辑）。首屏会根据**真实配置状态**展示：
- **已配置**：当前已生效的 Key（如 OPENROUTER_API_KEY、LLM 等）
- **配置提示**：仅对未配置项给出提示
- **完善配置**：仅列出尚未配置项及对应申请/获取 Key 链接

---

## 1. OMKAR_CLOUD_API_KEY（海外热销与选品详情）

- **用途**：Amazon 热销数据、选品详情，5000 次/月免费。
- **注册**：https://omkar.cloud/auth/sign-up  
- **获取 Key**：https://omkar.cloud/api-key  
- **填入**：`OMKAR_CLOUD_API_KEY=你的key`

---

## 2. 政策自动搜索（PERPLEXITY / OPENROUTER 二选一即可）

### OpenRouter（推荐，可调用 Perplexity 模型）

- **注册**：https://openrouter.ai/sign-up  
- **获取 Key**：https://openrouter.ai/keys  
- **填入**：`OPENROUTER_API_KEY=sk-or-你的key`

### Perplexity 直连

- **设置/API**：https://www.perplexity.ai/settings  
- **获取 Key**：https://perplexity.ai/account/api  
- **填入**：`PERPLEXITY_API_KEY=你的key`

---

## 3. LLM（选品分析与政策 AI，任选其一）

- **智谱清言**：https://open.bigmodel.cn/ → 创建 API Key，填入 `ZHIPU_API_KEY`  
- **百度千帆**：https://console.bce.baidu.com/ → 千帆大模型平台，填入 `BAIDU_API_KEY`  
- **OpenAI**：https://platform.openai.com/api-keys → 填入 `OPENAI_API_KEY`

---

## 4. OPENCLAW_API_KEY（百度优选 Skill）

- **申请**：https://www.clawhub.com/  
- **用途**：商品检索、比价、口碑分析。

---

## 自动化执行

在项目根目录执行（会尝试用系统默认浏览器打开注册页）：

```bash
bash scripts/setup_api_keys.sh
```

若环境无图形界面，可直接用上面链接在浏览器中打开并完成注册与 Key 获取，再将 Key 写入 `.env`。保存后重启服务：`./stop_daemon.sh && ./run_daemon.sh`。
