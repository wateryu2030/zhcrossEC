#!/bin/bash
# 安装 ClawHub 技能（解决 macOS 上 npx clawhub 报错 mkdir '/home/node'）
# 用法: bash scripts/install_clawhub_skill.sh [技能名]
# 例:   bash scripts/install_clawhub_skill.sh tavily-web-search

set -e
SKILL="${1:-tavily-web-search}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OPENCLAW_SKILLS="$HOME/.openclaw/skills"
mkdir -p "$OPENCLAW_SKILLS"

# ClawHub 上 Tavily 可能叫 tavily-search，脚本自动重试
SKILL_ALT=""
case "$SKILL" in
  tavily-web-search) SKILL_ALT="tavily-search" ;;
  tavily-search)      SKILL_ALT="tavily" ;;
esac

install_via_docker() {
  local name="$1"
  echo "通过 Docker 安装（容器内）: $name …"
  docker run --rm \
    -v "$HOME/.openclaw:/root/.openclaw" \
    -w /root \
    node:20-alpine \
    sh -c "npx clawhub@latest install $name"
}

install_via_npx() {
  echo "正在安装技能: $SKILL"
  npx clawhub@latest install "$SKILL"
}

if command -v docker &>/dev/null; then
  if install_via_docker "$SKILL"; then
    echo "安装完成。若需配置 API Key，请编辑 ~/.openclaw/openclaw.json 或 .env"
    exit 0
  fi
  if [ -n "$SKILL_ALT" ]; then
    echo "尝试备用技能名: $SKILL_ALT"
    if install_via_docker "$SKILL_ALT"; then
      echo "安装完成（技能名: $SKILL_ALT）。若需配置 API Key，请编辑 ~/.openclaw/openclaw.json 或 .env"
      exit 0
    fi
  fi
  # Docker 已尝试但失败，不再在本机执行 npx（macOS 会报 /home/node）
  echo ""
  echo "Docker 内安装未成功。建议改用手动安装（页面 Download .zip）："
  echo ""
  if [ "$SKILL" = "tavily-web-search" ] || [ "$SKILL" = "tavily-search" ]; then
    echo "  Tavily Web Search: https://clawhub.ai/skill-8887/tavily-search"
    echo "  1) 在浏览器打开上述链接，点击「Download .zip」"
    echo "  2) 解压到: $OPENCLAW_SKILLS/tavily-search/"
    echo "  3) 在 https://tavily.com 申请 TAVILY_API_KEY，填入项目 .env 或 ~/.openclaw/.env"
    echo ""
  fi
  echo "  其他技能: 在 clawhub.ai 搜索并打开技能页，用 Download .zip 解压到 $OPENCLAW_SKILLS/<技能名>/"
  echo "  若报 EAI_AGAIN，为容器内网络问题，可稍后重试或用手动下载。"
  echo ""
  exit 1
fi

# 无 Docker 时再尝试本机 npx（仅 Linux 等可能成功）
if install_via_npx; then
  echo "安装完成。若需配置 API Key，请编辑 ~/.openclaw/openclaw.json 或 .env"
  exit 0
fi

echo ""
echo "当前环境无法完成 npx clawhub 安装（macOS 不支持创建 /home/node）。"
echo "请安装 Docker Desktop 后重试，或见下方手动方案。"
echo ""
echo "可选方案："
echo "  1) Docker 安装: bash $0 $SKILL  或  bash $0 tavily-search"
echo "  2) 在 clawhub.ai 打开技能页，下载/克隆到: $OPENCLAW_SKILLS/<技能名>/"
echo "  3) 本仓库百度优选: cp -r $ROOT/skills/baidu-preferred $OPENCLAW_SKILLS/"
echo ""
exit 1
