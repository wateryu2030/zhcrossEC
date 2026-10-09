# 终端一键执行：OpenClaw 自主迭代并完成后续工作

在终端中**直接复制整段执行**即可，无需改路径（已按项目路径写好）。

**系统是否支持 OpenClaw 自行迭代、进化？**  
**支持。** 当前已具备：配置自检（self-improve）、就绪后自动启动（--then-start）、服务启动后每 15 分钟持续积累 + 每周政策爬虫 + 每日媒体爬虫；要「停止 → 杀进程 → 重启」见下方「停止服务与重启」一节。

**「OpenClaw 控制本机、自我迭代后续工作」是什么？**

- **配置自检 + 启动**：`self-improve --loop --then-start` 会循环自检直到就绪，然后执行 `start` 启动 CPG-Hub 服务。
- **后续工作**：服务启动后，**在后台自动**执行：
  - **每 15 分钟**：持续积累（政策同步 + 热销 + 关键词轮询，首屏数据会增多）
  - **每周**：政策爬虫（政府站 + 全网），新政策触发 AI 周报与飞书推送
  - **每日**：媒体热点爬虫（亿邦/雨果/36氪/虎嗅/百度资讯 + 抖音/快手热点通过搜索 API 补充）
  这些就是「自我迭代」的后续工作，无需再在终端重复执行。
- **立刻执行一轮并看到输出**：若想在本机终端里看到一轮执行结果，可执行 `iterate-now`（见下方）。

**项目持续完善（自动化改进）**  
- **政策展示**：列表按地域/国家标签、日期、分类展示；支持分页与「按省市快速查看」；每条政策可点「AI 解读」获取面向卖家的简要解读。
- **媒体抓取**：除资讯站外，已增加 36氪、虎嗅；抖音/快手通过 Perplexity/OpenRouter 搜索「跨境电商」相关热点入库（需配置相应 API Key）。
- **政策解读**：周报式「方向与行动建议」+ 分省市要点；单条政策支持「AI 解读」接口与前端按钮。

---

## 方式一：一条命令（推荐）

自我迭代直到就绪，并自动后台启动服务；若有未配置项会先打开注册页（仅第一轮）。

```bash
cd /Users/zhonglian/ec && ( [ -d .venv ] && source .venv/bin/activate; python3 scripts/openclaw_control.py self-improve --loop --interval 60 --then-start --open-pages )
```

- **--loop**：未就绪时每 60 秒重试（配置自检 + 健康检查）。
- **--then-start**：就绪后自动执行 `start`，后台跑 CPG-Hub。
- **--open-pages**：第一轮对未配置项打开注册/获取 Key 页面；补齐后保存 `.env`，下一轮会自动通过。

执行后保持终端不关，直到看到「自我迭代完成，服务已就绪」或「已启动 PID xxx，访问 http://localhost:8000」。若需停止服务，新开终端执行下面的「停止服务」命令。

---

## 方式二：分步执行（便于观察每步）

```bash
# 1. 进入项目并激活虚拟环境（若有）
cd /Users/zhonglian/ec
[ -d .venv ] && source .venv/bin/activate

# 2. 自主迭代直到就绪（缺配置时会打开注册页，补齐 .env 后会自动通过）
python3 scripts/openclaw_control.py self-improve --loop --interval 60 --open-pages

# 3. 就绪后启动后台服务（若上一步已自动 then-start 可跳过）
python3 scripts/openclaw_control.py start
```

---

## 后台常驻（关终端不影响）

需要「连接 OpenClaw、自我迭代完善 + 服务在后台跑，关闭本终端窗口也不退出」时，可用 `nohup` 把自我迭代与启动放到后台：

```bash
cd /Users/zhonglian/ec
mkdir -p logs
nohup bash -c 'cd /Users/zhonglian/ec && ( [ -d .venv ] && source .venv/bin/activate ); python3 scripts/openclaw_control.py self-improve --loop --interval 60 --then-start' >> logs/openclaw-loop.log 2>&1 &
echo "后台自我迭代已启动，PID: $!"
```

- 自我迭代会循环自检，就绪后自动执行 `start` 启动 CPG-Hub，服务以后台进程运行（`start_new_session`），关终端不会杀进程。
- 日志在 `logs/openclaw-loop.log`，查看：`tail -f logs/openclaw-loop.log`。
- 若服务尚未就绪，可再单独执行一次：`python3 scripts/openclaw_control.py start`。

---

## 常用控制命令

```bash
cd /Users/zhonglian/ec
[ -d .venv ] && source .venv/bin/activate

# 查看状态（配置项 + 服务是否在跑）
python3 scripts/openclaw_control.py status

# 停止服务（先按 PID 文件杀，无则按端口 8000 杀）
python3 scripts/openclaw_control.py stop

# 若 stop 无效，强制杀占用 8000 端口的进程（可选）
lsof -ti :8000 | xargs kill -9

# 重启服务（停止后再执行）
python3 scripts/openclaw_control.py start

# 仅自检一轮（不循环、不打开浏览器）
python3 scripts/openclaw_control.py self-improve

# 立即执行一轮「后续工作」：政策+热销积累 + 政策/媒体爬虫（终端可见输出，刷新 localhost:8000 可见新数据）
python3 scripts/openclaw_control.py iterate-now
```

---

## 停止服务与重启（复制到终端执行）

按顺序执行：先停止现有服务，必要时强杀进程，再启动。

```bash
cd /Users/zhonglian/ec
[ -d .venv ] && source .venv/bin/activate

# 1. 停止现有服务
python3 scripts/openclaw_control.py stop

# 2. 若仍有进程占 8000 端口，强杀（可选）
lsof -ti :8000 | xargs kill -9

# 3. 重启服务
python3 scripts/openclaw_control.py start
```

---

## 政策与商务部国家对比：整体执行命令

若「政策」页按国家筛选没有数据，需先跑国内政策爬虫 + 丝路电商 36 国政策入库。**整段复制到终端执行**（不要复制以 # 开头的行）。

**方式 A：一键脚本（推荐）**

```bash
cd /Users/zhonglian/ec
[ -d .venv ] && source .venv/bin/activate
bash scripts/run_policy_full_sync.sh
```

**方式 B：逐条执行（便于看每步输出）**

```bash
cd /Users/zhonglian/ec
[ -d .venv ] && source .venv/bin/activate
python3 scripts/openclaw_control.py stop
lsof -ti :8000 | xargs kill -9
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from crawler.policy_crawler import run_policy_crawl
n = asyncio.run(run_policy_crawl())
print('国内政策入库:', n, '条')
"
python3 scripts/fetch_silk_road_policies.py
python3 scripts/openclaw_control.py start
```

说明：
- 国内政策：商务部、发改委、各省市商务站 + 全网搜索，写入 `policy` 表（region=中央/省/市）。
- 丝路电商 36 国：需在 `.env` 配置 `OPENROUTER_API_KEY` 或 `PERPLEXITY_API_KEY`，写入时带 `country=该国`。
- 执行完成后打开 http://localhost:8000 → 政策 → 点「从数据库加载」→ 国家下拉选某国即可看到该国政策。

---

## OpenClaw 迭代是否正常：自检清单

- **服务在跑**：`python3 scripts/openclaw_control.py status` 显示「服务: 运行中 http://localhost:8000」。
- **定时任务**：服务启动后自动跑「每 15 分钟积累」与「每周政策爬虫 / 每日媒体爬虫」；立刻执行一轮：`python3 scripts/openclaw_control.py iterate-now`。
- **政策数据**：浏览器打开政策页 → 点「从数据库加载」→ 有数据且「最后更新」有时间即表示爬虫在写 MySQL；若为空则执行 `bash scripts/run_policy_full_sync.sh`。
- **政策筛选**：分类 = 合规场景（清关/财税/支付/数据跨境/知识产权/行政处罚/综合），与法务政策库一致；详见 `docs/CURSOR_POLICY_DATA.md`。

---

## 首屏数据不更新（政策 0、媒体 -）自检

若首屏统计条显示「政策 0」「媒体 -」「均价差 -」等一直不更新，可先查实际数据来源：

```bash
cd /Users/zhonglian/ec && ( [ -d .venv ] && source .venv/bin/activate; python3 scripts/check_db_stats.py )
```

脚本会输出：MySQL 中 `policy` / `media_hot` 表条数、政策最后爬取时间、同步缓存中的热销/均价差/热门类目。根据输出可判断：
- **政策 0**：多为 `policy` 表为空，需执行政策爬虫或全量同步（如 `bash scripts/run_policy_full_sync.sh`）；接口已改为优先用 DB 条数，若 DB 为 0 会回退显示法务政策库条数。
- **媒体 -**：`media_hot` 表为空或未跑媒体爬虫时，执行 `python3 scripts/run_crawl.py media`。
- **热销品/均价差/热门类目**：来自同步缓存，由「每 15 分钟持续积累」或 `iterate-now` 写入，未跑过则为空或 `-`。

---

## 飞书与企业微信通知

- **飞书**：配置 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_NOTIFY_OPEN_ID` 后，新政策入库与政策 AI 分析周报会推送到指定用户。
- **企业微信**：配置 `WECOM_CORP_ID`、`WECOM_AGENT_ID`、`WECOM_AGENT_SECRET` 后，同上推送会同时发到企业微信应用；`WECOM_TO_USER` 默认为 `@all`，可改为指定 userid（多个用 `|` 分隔）。与飞书并列，二者可同时配置。

---

## 说明

- **数据库**：主数据使用 **MySQL**（政策、媒体、政策分析）。请在 `.env` 中配置 `MYSQL_HOST`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`；首次启动会自动建库建表，详见 `docs/DATABASE.md`。
- 项目路径固定为 `/Users/zhonglian/ec`，若你克隆到别处，把命令里的路径改成你的项目根目录即可。
- 未配置项（如 OMKAR_CLOUD_API_KEY、OPENCLAW_API_KEY）为可选；不配置也能通过健康检查并启动，只是对应功能不可用。
- 迭代过程中若你补全了 `.env` 并保存，下一轮（约 60 秒后）会自动检测到并继续，无需重新执行命令。
- **服务跑起来后**：后台会每 15 分钟做「持续积累」、每周/每日做爬虫；要**立刻跑一轮并在终端看到**，执行 `iterate-now`。
