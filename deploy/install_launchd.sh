#!/bin/bash
# 安装 CPG-Hub 为 macOS LaunchAgent（锁屏、休眠后继续运行）
# 安装后：登录即启动，锁屏不影响

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_SRC="$SCRIPT_DIR/com.cpghub.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.cpghub.plist"

# 替换 plist 中的路径为实际项目路径
mkdir -p "$ROOT/logs"
sed "s|/Users/apple/crossEC|$ROOT|g" "$PLIST_SRC" > "$PLIST_DEST"

echo "已安装 LaunchAgent: $PLIST_DEST"
echo ""
echo "启动: launchctl load $PLIST_DEST"
echo "停止: launchctl unload $PLIST_DEST"
echo ""
echo "立即启动？(y/n)"
read -r ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
  launchctl unload "$PLIST_DEST" 2>/dev/null || true
  launchctl load "$PLIST_DEST"
  echo "已启动，访问 http://localhost:8000"
fi
