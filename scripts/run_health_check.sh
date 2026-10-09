#!/bin/bash
# 在项目根目录执行配置自检 + 健康检查（不打开浏览器）
# 用法: 在项目根目录执行  bash scripts/run_health_check.sh  或  ./scripts/run_health_check.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -d ".venv" ]; then
  source .venv/bin/activate
else
  echo "未找到 .venv，使用当前 python3。若要创建虚拟环境: python3 -m venv .venv && source .venv/bin/activate"
fi

pip install -q -r requirements.txt 2>/dev/null || true
python3 scripts/ensure_config_and_run.py --no-open-pages
