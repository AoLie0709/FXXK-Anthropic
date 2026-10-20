#!/usr/bin/env bash
# ==============================================================================
# FXXK CLAUDE - 一键拉取最新订阅并强力重新注入防封规则 (Clash Verge)
# ==============================================================================

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$DIR/update_subscription.py"

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_CYAN="\033[36m"

echo -e "\n${C_BOLD}🔄 正在更新节点订阅并注入定制防封规则...${C_RESET}\n"

python3 "$SCRIPT_PATH"

echo -e "\n${C_GREEN}✅ 规则注入完成！若 Clash Verge 处于运行状态，已自动触发热重载。${C_RESET}\n"
