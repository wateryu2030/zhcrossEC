#!/bin/bash
# CPG-Hub API Key 配置助手
# 使用 wateryu2030@gmail.com 注册以下服务并获取 Key，填入 .env
# 推荐先运行: python3 scripts/ensure_config_and_run.py  （会自检缺失项并打开对应注册页，最后做健康检查）

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=========================================="
echo "CPG-Hub API Key 配置（wateryu2030@gmail.com）"
echo "=========================================="
echo ""
echo "1. OMKAR_CLOUD_API_KEY - 海外热销与选品（Amazon 数据）"
echo "   注册: https://omkar.cloud/auth/sign-up"
echo "   获取 Key: https://omkar.cloud/api-key"
echo "   免费: 5000 次/月"
echo ""
echo "2. OPENROUTER_API_KEY - 政策自动搜索（Perplexity 全网检索）"
echo "   注册: https://openrouter.ai/sign-up"
echo "   获取 Key: https://openrouter.ai/keys"
echo ""
echo "3. OPENCLAW_API_KEY - 百度优选（商品检索、比价）"
echo "   申请: https://www.clawhub.com/"
echo ""
echo "正在打开注册/申请页面..."
echo ""

# 打开浏览器（仅打开未配置项可由 ensure_config_and_run.py 做）
if command -v open &>/dev/null; then
  open "https://omkar.cloud/auth/sign-up"
  sleep 2
  open "https://openrouter.ai/sign-up"
  sleep 2
  open "https://www.clawhub.com/"
elif command -v xdg-open &>/dev/null; then
  xdg-open "https://omkar.cloud/auth/sign-up"
  sleep 2
  xdg-open "https://openrouter.ai/sign-up"
  sleep 2
  xdg-open "https://www.clawhub.com/"
fi

echo "注册完成后，将 Key 填入项目根目录 .env："
echo "  OMKAR_CLOUD_API_KEY=你的omkar_key"
echo "  OPENROUTER_API_KEY=sk-or-你的openrouter_key"
echo "  OPENCLAW_API_KEY=你的clawhub_key"
echo ""
echo "保存后重启: ./stop_daemon.sh && ./run_daemon.sh"
echo "或再次运行自检与健康检查: python3 scripts/ensure_config_and_run.py --no-open-pages"
echo ""
