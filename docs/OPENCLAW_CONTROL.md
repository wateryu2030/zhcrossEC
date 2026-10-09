# OpenClaw 控制 CPG-Hub：自我迭代与自我完善

通过统一入口 `scripts/openclaw_control.py`，可由 OpenClaw 或终端控制项目：启动/停止/状态/自我完善，并支持**自我迭代**（循环自检直到就绪）。

## 命令

在项目根目录执行（建议先 `source .venv/bin/activate`）：

| 命令 | 说明 |
|------|------|
| `python3 scripts/openclaw_control.py start` | 后台启动服务（等价 `./run_daemon.sh`） |
| `python3 scripts/openclaw_control.py stop` | 停止服务 |
| `python3 scripts/openclaw_control.py status` | 查看配置与运行状态 |
| `python3 scripts/openclaw_control.py self-improve` | 自检一轮：配置 + 健康检查 |
| `python3 scripts/openclaw_control.py self-improve --loop` | **自我迭代**：每 60 秒重试直到服务就绪 |
| `python3 scripts/openclaw_control.py self-improve --loop --interval 30` | 每 30 秒重试 |
| `python3 scripts/openclaw_control.py self-improve --loop --then-start` | 就绪后自动执行 `start` 启动后台服务 |
| `python3 scripts/openclaw_control.py self-improve --open-pages` | 对未配置项打开注册/获取 Key 页面 |

## 自我迭代流程

1. **配置自检**：读取 `.env` 与 `~/.openclaw/openclaw.json`，判断已配置/未配置项。
2. **可选打开注册页**：未配置项可自动打开对应申请链接（`--open-pages`，建议第一轮使用）。
3. **健康检查**：先检测本机 8000 端口是否已运行；若未运行则临时启动进程做一次健康检查。
4. **循环**（`--loop`）：若未就绪则等待 `--interval` 秒后重新执行 1～3，直到就绪或达到 `--max-rounds`。

适合在终端执行一次，让项目在配置不全时持续自我提示、补齐配置后自动通过健康检查；配合 `--then-start` 可在就绪后直接拉起后台服务。

## start 已运行时的行为

若服务已在运行（例如刚执行过 `self-improve` 或之前已 `start`），再次执行 `start` 会提示「服务已在运行，无需重复启动」，不会重复起进程或报错。需要重启时请先 `stop` 再 `start`。

## 与 run_daemon.sh 的关系

- `./run_daemon.sh`：传统方式，直接 nohup 启动 uvicorn。
- `python3 scripts/openclaw_control.py start`：同一行为的 Python 实现，便于 OpenClaw/cron 统一调用。

两种方式二选一即可；停止均可用 `python3 scripts/openclaw_control.py stop` 或 `./stop_daemon.sh`。

## ClawHub 技能安装（npx clawhub）

从 [ClawHub 技能站](https://clawhub.ai) 安装技能可使用：

```bash
npx clawhub@latest install <技能名>
```

**若在 macOS 上报错 `ENOENT: no such file or directory, mkdir '/home/node'`**：当前 `clawhub` npm 包会尝试创建 Linux 路径，macOS 上无法创建 `/home`，可选用：

1. **用脚本通过 Docker 安装**（推荐，需已安装 Docker Desktop）：
   ```bash
   bash scripts/install_clawhub_skill.sh tavily-web-search
   ```
   脚本会优先在容器内执行 `npx clawhub install`，技能会写入本机 `~/.openclaw/skills/`。

2. **本仓库自带技能**（无需 npx）：将 `skills/baidu-preferred/` 复制到 OpenClaw 工作区：
   ```bash
   mkdir -p ~/.openclaw/skills
   cp -r skills/baidu-preferred ~/.openclaw/skills/
   ```

3. **手动安装（推荐，避免 npx/Docker 问题）**：以 Tavily Web Search 为例：
   - 打开 [Tavily Web Search 技能页](https://clawhub.ai/skill-8887/tavily-search)，点击 **Download .zip**。
   - 解压到本机目录（目录名建议与技能一致）：
     ```bash
     mkdir -p ~/.openclaw/skills/tavily-search
     unzip ~/Downloads/tavily-search-*.zip -d /tmp/tavily-extract
     cp -r /tmp/tavily-extract/* ~/.openclaw/skills/tavily-search/
     ```
   - 配置 API Key：在 [tavily.com](https://tavily.com) 申请 `TAVILY_API_KEY`，写入项目根目录 `.env`：
     ```bash
     echo "TAVILY_API_KEY=你的key" >> /Users/zhonglian/ec/.env
     ```
   - 若 OpenClaw 从 `~/.openclaw` 读配置，也可在 `~/.openclaw/openclaw.json` 或 `~/.openclaw/.env` 中配置 `TAVILY_API_KEY`。
