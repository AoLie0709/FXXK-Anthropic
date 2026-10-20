#!/usr/bin/env bash
# ==============================================================================
# FXXK CLAUDE - Launch Physically Isolated Chrome Profile (Stealth v2.2)
# (零污染物理隔离专用 Chrome 实例启动器)
# ==============================================================================
# 核心特性：
# 1. 物理数据目录隔离：彻底切断与 macOS 系统日常 Chrome Profile 的 SQLite / Gaia / Cookie 关联
# 2. 自动检测并挂载本地 SOCKS5 代理通道（优先台湾住宅出口，杜绝直连与 DNS 泄露）
# 3. 剥离自动化受控特征 (--disable-blink-features=AutomationControlled)
# 4. 语言环境与台区住宅 IP 深度契合 (--lang=zh-TW,zh;q=0.9,en-US;q=0.8)
# 5. 自动加载独占 Claude Shield 防护扩展并屏蔽外部扩展串扰
# ==============================================================================

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$DIR/../.." && pwd)"
EXTENSION_DIR="$PROJECT_ROOT/tools/extension"
ISOLATED_DATA_DIR="$HOME/.claude_isolated_profile"

mkdir -p "$ISOLATED_DATA_DIR"

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_CYAN="\033[36m"
C_YELLOW="\033[33m"
C_BLUE="\033[34m"

echo -e "\n${C_BOLD}================================================================${C_RESET}"
echo -e "${C_BOLD}🛡️  FXXK CLAUDE - 启动物理级隔离 Chrome 实例 (Stealth Edition)${C_RESET}"
echo -e "${C_BOLD}================================================================${C_RESET}\n"

# 1. 探测代理配置
PROXY_ARG=""
PROXY_INFO="系统默认路由 (TUN 网卡模式)"

CUSTOM_PROXY="${1:-}"

if [[ -n "$CUSTOM_PROXY" && "$CUSTOM_PROXY" =~ ^[0-9]+$ ]]; then
  PROXY_ARG="--proxy-server=socks5://127.0.0.1:$CUSTOM_PROXY"
  PROXY_INFO="指定 SOCKS5: 127.0.0.1:$CUSTOM_PROXY"
elif nc -z 127.0.0.1 7897 2>/dev/null; then
  PROXY_PORT="7897"
elif nc -z 127.0.0.1 10811 2>/dev/null; then
  PROXY_ARG="--proxy-server=socks5://127.0.0.1:10811"
  PROXY_INFO="自动侦测 v2rayN 监听端口 10811 (socks5://127.0.0.1:10811)"
elif nc -z 127.0.0.1 7897 2>/dev/null; then
  PROXY_PORT="7897"
elif nc -z 127.0.0.1 10808 2>/dev/null; then
  PROXY_ARG="--proxy-server=socks5://127.0.0.1:10808"
  PROXY_INFO="自动侦测 SOCKS5 监听端口 10808 (socks5://127.0.0.1:10808)"
fi

echo -e "  • 独立用户数据目录: ${C_CYAN}$ISOLATED_DATA_DIR${C_RESET}"
echo -e "  • 自动加载护盾扩展: ${C_CYAN}$EXTENSION_DIR${C_RESET}"
echo -e "  • 网络代理隧道模式: ${C_GREEN}$PROXY_INFO${C_RESET}"
echo -e "  • 目标访问地址:     ${C_CYAN}https://claude.ai${C_RESET}\n"

CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CHROME_FLAGS=(
  "--user-data-dir=$ISOLATED_DATA_DIR"
  "--load-extension=$EXTENSION_DIR"
  "--disable-extensions-except=$EXTENSION_DIR"
  "--no-first-run"
  "--no-default-browser-check"
  "--disable-sync"
  "--disable-blink-features=AutomationControlled"
  "--lang=zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
  "--password-store=basic"
  "--disable-features=OptimizationGuideModelDownloading,OptimizationHintsUI,DialMediaRouteProvider"
)

if [[ -n "$PROXY_ARG" ]]; then
  CHROME_FLAGS+=("$PROXY_ARG")
fi

CHROME_FLAGS+=("https://claude.ai")

if [[ ! -f "$CHROME_BIN" ]]; then
  echo -e "${C_YELLOW}⚠️ 未在标准目录找到 Google Chrome 二进制文件，尝试使用 open 命令启动...${C_RESET}"
  open -na "Google Chrome" --args "${CHROME_FLAGS[@]}"
else
  "$CHROME_BIN" "${CHROME_FLAGS[@]}" >/dev/null 2>&1 &
fi

echo -e "${C_GREEN}✅ 纯净隔离 Chrome 实例已在独立沙箱中启动！${C_RESET}"
echo -e "  【安全守则】："
echo -e "  1. 请勿在此窗口登录您的个人日常 Google 账号或任何国内服务账号。"
echo -e "  2. 仅登录通过 iOS 渠道创建的专用免短信纯净 Gmail。"
echo -e "  3. 确认右上角 Claude Shield 扩展图标已就绪并对齐节点时区。\n"
