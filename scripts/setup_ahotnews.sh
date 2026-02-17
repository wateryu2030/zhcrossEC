#!/bin/bash
# 克隆并初始化 ahotnews (BettaFish 微舆) 到 vendor/ahotnews
# 用于按关键词在抖音、快手、微博等平台爬取跨境电商相关热点
# 文档: https://github.com/wateryu2030/ahotnews

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/vendor"
AHOTNEWS="$VENDOR/ahotnews"

mkdir -p "$VENDOR"
if [ -d "$AHOTNEWS/.git" ]; then
  echo "ahotnews 已存在，更新..."
  (cd "$AHOTNEWS" && git pull --rebase || true)
else
  echo "克隆 ahotnews..."
  git clone --depth 1 https://github.com/wateryu2030/ahotnews.git "$AHOTNEWS"
fi

echo "请完成以下步骤："
echo "1. 在 ahotnews 项目根目录配置 .env（数据库、MINDSPIDER_API_KEY 等）"
echo "   参考: $AHOTNEWS/.env.example"
echo "2. 在 CPG-Hub .env 中配置："
echo "   AHOTNEWS_ENABLED=true"
echo "   AHOTNEWS_PATH=vendor/ahotnews"
echo "   AHOTNEWS_DB_HOST=...  （与 ahotnews MindSpider 使用同一数据库）"
echo "   AHOTNEWS_DB_USER=... AHOTNEWS_DB_PASSWORD=... AHOTNEWS_DB_NAME=mindspider"
echo "3. 安装 ahotnews 依赖: cd $AHOTNEWS && pip install -r requirements.txt && playwright install chromium"
echo "4. 初始化 MindSpider: cd $AHOTNEWS/MindSpider && python main.py --setup"
echo ""
echo "完成后可调用 POST /api/v1/crawl/ahotnews 触发爬取。"
