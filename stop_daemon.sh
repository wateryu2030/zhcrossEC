#!/bin/bash
# 停止 CPG-Hub 后台进程

cd "$(dirname "$0")"
PID_FILE="$(pwd)/.cpg-hub.pid"

if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "已停止 CPG-Hub (PID $PID)"
  else
    echo "进程已不存在"
  fi
  rm -f "$PID_FILE"
else
  echo "未找到 PID 文件，尝试按端口查找..."
  P=$(lsof -ti:8000 2>/dev/null)
  if [ -n "$P" ]; then
    kill $P
    echo "已停止占用 8000 端口的进程"
  else
    echo "未发现运行中的服务"
  fi
fi
