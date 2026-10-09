#!/bin/bash
# CPG-Hub 后台运行（锁屏、关终端后继续工作）
# 使用 nohup + caffeinate 防止休眠，确保 OpenClaw 与同步任务持续执行
# 也可用 OpenClaw 控制入口: python3 scripts/openclaw_control.py start

cd "$(dirname "$0")"
ROOT="$(pwd)"
LOG_DIR="${ROOT}/logs"
LOG="${LOG_DIR}/cpg-hub.log"
PID_FILE="${ROOT}/.cpg-hub.pid"

mkdir -p "$LOG_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

# 自动化执行：确保政策库千条以上（缺失则自动生成）
python scripts/ensure_policy_library.py || true

# macOS: caffeinate -i 防止系统休眠（锁屏不影响）
# -i: 阻止 idle sleep，保持进程运行
CAFFEINATE=""
if command -v caffeinate &>/dev/null; then
  CAFFEINATE="caffeinate -i"
fi

echo "CPG-Hub 后台启动中... 日志: $LOG"
echo "停止: kill \$(cat $PID_FILE)"

nohup $CAFFEINATE uvicorn main:app --host 0.0.0.0 --port 8000 \
  >> "$LOG" 2>&1 &
echo $! > "$PID_FILE"

sleep 2
if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
  echo "已启动 PID $(cat $PID_FILE)，访问 http://localhost:8000"
else
  echo "启动失败，请查看 $LOG"
  rm -f "$PID_FILE"
  exit 1
fi
