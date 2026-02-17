#!/bin/bash
# CPG-Hub 启动脚本（前台，带热重载）
# 执行期间防锁屏、确保项目一直可用：macOS 下自动使用 caffeinate -i；长期后台用 ./run_daemon.sh
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

# 自动化执行：确保政策库千条以上（缺失则自动生成）
python scripts/ensure_policy_library.py || true

# macOS: 防止运行期间锁屏/休眠导致进程中断
if command -v caffeinate &>/dev/null; then
  exec caffeinate -i uvicorn main:app --reload --host 0.0.0.0 --port 8000
fi
uvicorn main:app --reload --host 0.0.0.0 --port 8000
