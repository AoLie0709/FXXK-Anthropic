#!/usr/bin/env bash
# ==============================================================================
# FXXK CLAUDE - 台湾人格 · 零扩展隔离 Chrome 启动器 (Consistency v3)
# ==============================================================================
# 与旧版 (Stealth v2.2) 的区别：
#   1. ❌ 不再 --load-extension：扩展注入是 document_gutted / added_extension_url_count 的来源
#   2. ❌ 不再改写 Accept-Language 请求头：语言由 OS + 原生 --lang/--accept-lang 决定
#   3. ❌ 不再 --disable-blink-features=AutomationControlled：真实浏览器无收益，徒增刻意痕迹
#   4. ✅ WebRTC 由原生开关关闭（无需扩展）
#   5. ✅ 语言、时区、地区三件套与 macOS 系统设置保持一致
# ==============================================================================
# 用法：
#   ./launch_isolated_chrome_tw.sh            # 自动探测本地代理端口
#   ./launch_isolated_chrome_tw.sh 7890       # 指定 socks5 端口
#   PROFILE_DIR=/path ./launch_isolated_chrome_tw.sh
# ==============================================================================

set -uo pipefail

PROFILE_DIR="${PROFILE_DIR:-$HOME/.claude_tw_profile}"
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TARGET_URL="${TARGET_URL:-https://claude.ai}"

C_RESET="\033[0m"; C_BOLD="\033[1m"; C_GREEN="\033[32m"; C_CYAN="\033[36m"; C_YELLOW="\033[33m"

# ---- 前置检查：系统语言必须是繁体中文，否则原生 CH / Intl / x-app-locale 会互相矛盾 ----
OS_LOCALE="$(defaults read -g AppleLocale 2>/dev/null || echo unknown)"
OS_LANGS="$(defaults read -g AppleLanguages 2>/dev/null | tr -d '\n ' || echo '')"

echo -e "\n${C_BOLD}============================================================${C_RESET}"
echo -e "${C_BOLD} 台湾人格 · 零扩展隔离 Chrome${C_RESET}"
echo -e "${C_BOLD}============================================================${C_RESET}"
echo -e "  • 数据目录 : ${C_CYAN}${PROFILE_DIR}${C_RESET}"
echo -e "  • 语言     : zh-TW / zh-Hant（原生）"
echo -e "  • 扩展     : 无（0 个）"
echo -e "  • 目标     : ${C_CYAN}${TARGET_URL}${C_RESET}"

if [[ "$OS_LOCALE" != zh_TW && "$OS_LOCALE" != zh-Hant-TW ]]; then
  echo -e "\n${C_YELLOW}⚠️  系统区域当前为 ${OS_LOCALE}，与台湾人格不一致。${C_RESET}"
  echo -e "${C_YELLOW}    建议先执行 tools/scripts/persona_tw_apply.sh 或手动：${C_RESET}"
  echo -e "${C_YELLOW}    defaults write -g AppleLocale -string zh_TW${C_RESET}"
  echo -e "${C_YELLOW}    defaults write -g AppleLanguages -array zh-Hant-TW zh-Hant en-US en${C_RESET}"
  echo -e "${C_YELLOW}    （浏览器端仍会按 --lang 呈现 zh-TW，但 Desktop 端会跟随系统语言）${C_RESET}\n"
fi

mkdir -p "$PROFILE_DIR"

# ---- 代理探测：TUN 模式优先，其次常见 socks5 端口 ----
PROXY_ARG=""
PROXY_INFO="TUN / 系统默认路由"
CUSTOM="${1:-}"
if [[ -n "$CUSTOM" && "$CUSTOM" =~ ^[0-9]+$ ]]; then
  PROXY_ARG="--proxy-server=socks5://127.0.0.1:${CUSTOM}"
  PROXY_INFO="指定 socks5://127.0.0.1:${CUSTOM}"
else
  for p in 7897 10811 10808 7890 1080; do
    if nc -z 127.0.0.1 "$p" 2>/dev/null; then
      PROXY_ARG="--proxy-server=socks5://127.0.0.1:${p}"
      PROXY_INFO="自动探测 socks5://127.0.0.1:${p}"
      break
    fi
  done
fi
echo -e "  • 出口     : ${C_GREEN}${PROXY_INFO}${C_RESET}\n"

CHROME_FLAGS=(
  "--user-data-dir=${PROFILE_DIR}"
  "--lang=zh-TW"
  "--accept-lang=zh-TW,zh;q=0.9,en-US;q=0.8,en"
  "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"
  "--no-first-run"
  "--no-default-browser-check"
  "--disable-sync"
  "--disable-features=OptimizationGuideModelDownloading,OptimizationHintsUI,DialMediaRouteProvider"
)

if [[ -n "$PROXY_ARG" ]]; then
  CHROME_FLAGS+=("$PROXY_ARG")
fi

CHROME_FLAGS+=("$TARGET_URL")

if [[ ! -x "$CHROME_BIN" ]]; then
  echo -e "${C_YELLOW}未找到 Chrome：${CHROME_BIN}${C_RESET}"
  exit 1
fi

exec "$CHROME_BIN" "${CHROME_FLAGS[@]}"
