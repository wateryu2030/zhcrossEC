#!/bin/bash
# 启动 CPG-Hub（本平台独立运行）
# macOS 上 5000 常被 ControlCenter/AirPlay 占用，默认 8000；若被占用则依次尝试 5002、5003
# 使用: ./scripts/run.sh  或  ./scripts/run.sh 5002

set -e
cd "$(dirname "$0")/.."

if [ -n "$PORT" ]; then
  PORTS="$PORT"
elif [ -n "$1" ]; then
  PORTS="$1"
else
  PORTS="8000 5002 5003 5004 5005"
fi

for PORT in $PORTS; do
  echo "Trying http://0.0.0.0:$PORT ..."
  if python -m uvicorn main:app --host 0.0.0.0 --port "$PORT" 2>&1; then
    exit 0
  fi
  # 用户显式指定了端口时，失败即退出；未指定时尝试下一个
  if [ -n "$1" ]; then
    echo "Port $PORT in use or failed, exiting."
    exit 1
  fi
  echo "Port $PORT in use, trying next..."
done
echo "No port available from: $PORTS"
exit 1
