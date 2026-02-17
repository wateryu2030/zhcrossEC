# CPG-Hub 后台运行（锁屏后继续工作）

确保锁屏、关终端后，CPG-Hub 与 OpenClaw 同步任务持续执行。

## 方式一：run_daemon.sh（推荐）

```bash
./run_daemon.sh    # 后台启动，使用 nohup + caffeinate
./stop_daemon.sh   # 停止
```

- 使用 `caffeinate -i` 防止 macOS 休眠，锁屏不影响进程
- 日志输出到 `logs/cpg-hub.log`
- 关闭终端后进程继续运行

## 方式二：LaunchAgent（登录即启动）

```bash
chmod +x deploy/install_launchd.sh
./deploy/install_launchd.sh
```

安装后：
- 用户登录时自动启动 CPG-Hub
- 锁屏、休眠后自动恢复
- 停止：`launchctl unload ~/Library/LaunchAgents/com.cpghub.plist`
- 启动：`launchctl load ~/Library/LaunchAgents/com.cpghub.plist`

## 方式三：手动 nohup

```bash
nohup caffeinate -i uvicorn main:app --host 0.0.0.0 --port 8000 >> logs/app.log 2>&1 &
```

## 自动化同步

- 后台调度器：启动后每 30 分钟自动同步政策+热销（可配置 `SYNC_INTERVAL_MINUTES=0` 禁用）
- 手动同步：`python scripts/run_sync.py`
- API 触发：`POST /api/v1/sync?mode=all`
