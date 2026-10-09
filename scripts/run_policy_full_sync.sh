#!/bin/bash
# 政策数据全量同步：国内政府站爬虫 + 丝路电商 36 国政策搜索入库
# 执行后「政策」页的省市/分类/国家筛选会有数据，商务部国家维度可对比
set -e
cd /Users/zhonglian/ec
[ -d .venv ] && source .venv/bin/activate

echo "=========================================="
echo "1/3 国内政策爬虫（商务部、发改委、各省市）"
echo "=========================================="
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from crawler.policy_crawler import run_policy_crawl
n = asyncio.run(run_policy_crawl())
print('国内政策入库:', n, '条')
"

echo ""
echo "=========================================="
echo "2/3 丝路电商 36 国政策搜索入库（需 .env 中 OPENROUTER_API_KEY 或 PERPLEXITY_API_KEY）"
echo "=========================================="
python3 scripts/fetch_silk_road_policies.py || true

echo ""
echo "=========================================="
echo "3/3 完成。刷新 http://localhost:8000 政策页，点「从数据库加载」后按国家/省市/分类筛选即可查看"
echo "=========================================="
