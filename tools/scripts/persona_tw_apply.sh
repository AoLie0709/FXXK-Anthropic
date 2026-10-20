#!/usr/bin/env bash
# ==============================================================================
# FXXK CLAUDE - 台湾人格 OS 层对齐脚本（默认 dry-run，只有加 --apply 才执行）
# ==============================================================================
# 做的事：
#   1. 区域 = TW，语言 = 繁體中文（第一）→ 影响 navigator.language / Intl / Desktop UI
#   2. 时区 = Asia/Taipei（UTC+8，与大陆同偏移，作息钟点不变）
#   3. 主机名 = 通用英文（去除品牌/拼音痕迹）
#   4. DNS = 1.1.1.1 / 8.8.8.8（清掉 114.114.114.114）
#   5. IPv6 = 关闭（Wi-Fi）
# 注意：
#   - 语言/区域改动需要注销或重启才完全生效
#   - 时区设置需要 sudo
#   - 本脚本不触碰 Claude 数据、不删除任何凭据
# ==============================================================================

set -uo pipefail
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1
HOSTNAME_NEW="${HOSTNAME_NEW:-MacBook-Pro}"

C_R="\033[0m"; C_B="\033[1m"; C_Y="\033[33m"; C_G="\033[32m"
echo -e "\n${C_B}台湾人格 · OS 层对齐${C_R}"
echo -e "${C_B}============================================================${C_R}"

CMDS=(
  "defaults write -g AppleLocale -string zh_TW"
  "defaults write -g AppleLanguages -array zh-Hant-TW zh-Hant en-US en"
  "sudo systemsetup -settimezone Asia/Taipei"
  "sudo scutil --set ComputerName '${HOSTNAME_NEW}'"
  "sudo scutil --set LocalHostName '${HOSTNAME_NEW}'"
  "sudo scutil --set HostName '${HOSTNAME_NEW}'"
  "networksetup -setdnsservers Wi-Fi 1.1.1.1 8.8.8.8"
  "networksetup -setv6off Wi-Fi"
)

if [[ "$APPLY" -eq 0 ]]; then
  echo -e "${C_Y}DRY-RUN：以下命令不会执行。确认无误后加 --apply 运行。${C_R}\n"
  for c in "${CMDS[@]}"; do echo "  $c"; done
  echo -e "\n${C_Y}提醒：若使用 TUN 模式，DNS 可能由代理接管；此时 networksetup 的 DNS 仅作兜底。${C_R}"
  echo -e "${C_Y}IPv6 关闭后需确认代理仍可正常工作。${C_R}\n"
  exit 0
fi

echo -e "${C_G}开始执行（时区/主机名需要输入 sudo 密码）...${C_R}\n"
for c in "${CMDS[@]}"; do
  echo -e "${C_B}→ ${c}${C_R}"
  if ! eval "$c"; then
    echo -e "  \033[31m失败：${c}\033[0m"
  fi
done

echo -e "\n${C_G}完成。请注销并重新登录（或重启），使语言与区域完全生效。${C_R}"
echo -e "随后运行：tools/scripts/persona_tw_verify.sh\n"
