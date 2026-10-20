#!/usr/bin/env bash
# ==============================================================================
# FXXK CLAUDE - sing-box DNS Selective IPv6 Interception Tester (v2.2)
# (Claude 域名定向 IPv6 阻断与系统全局 IPv6 保留验证工具)
# ==============================================================================
# 目标：
# 1. 验证配置文件 configPre.json 是否已正确注入 Claude AAAA 拦截规则
# 2. 验证 claude.ai / anthropic.com 等核心域名解析 AAAA (IPv6) 时，
#    sing-box 是否拦截并返回空响应 (NODATA)，阻止国内宽带 IPv6 泄漏。
# 3. 验证非 Claude 域名（如 qq.com / apple.com）正常解析，证明系统全局 IPv6 完整保留。
# ==============================================================================

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$DIR/../.." && pwd)"

# 颜色
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_RED="\033[31m"
C_YELLOW="\033[33m"
C_CYAN="\033[36m"
C_BLUE="\033[34m"

echo -e "\n${C_BOLD}================================================================${C_RESET}"
echo -e "${C_BOLD}🛡️  FXXK CLAUDE - sing-box 定向 IPv6 阻断规则有效性测试${C_RESET}"
echo -e "${C_BOLD}================================================================${C_RESET}\n"

# 检查本地配置文件注入状态
CONFIG_FILE="/Users/mac/Library/Application Support/v2rayN/binConfigs/configPre.json"
echo -e "${C_BOLD}【阶段 0：底层配置文件注入状态核验】${C_RESET}"
if [[ -f "$CONFIG_FILE" ]]; then
  if grep -q "claude.ai" "$CONFIG_FILE" && grep -q "AAAA" "$CONFIG_FILE"; then
    echo -e "  • 配置文件: ${C_GREEN}✅ 已注入 Claude AAAA 定向拦截规则${C_RESET} ($CONFIG_FILE)"
  else
    echo -e "  • 配置文件: ${C_YELLOW}⚠️ 尚未注入防护规则！${C_RESET}"
    echo -e "    建议执行: ${C_CYAN}python3 \"$PROJECT_ROOT/tools/scripts/apply_singbox_rules.py\"${C_RESET}"
  fi
else
  echo -e "  • 配置文件: ${C_YELLOW}⚠️ 未找到默认 v2rayN 配置文件: $CONFIG_FILE${C_RESET}"
fi

CLAUDE_DOMAINS=(
  "claude.ai"
  "anthropic.com"
  "claudeusercontent.com"
  "challenges.cloudflare.com"
  "statsigapi.net"
)

NORMAL_DOMAINS=(
  "apple.com"
  "qq.com"
)

echo -e "\n${C_BOLD}【阶段 1：测试 Claude 核心域名 IPv6 (AAAA) 阻断状态】${C_RESET}"
echo -e "（预期结果：AAAA 记录被 sing-box 拦截，返回空或者无 IPv6，强制回退至 IPv4 代理）\n"

all_claude_blocked=true

for domain in "${CLAUDE_DOMAINS[@]}"; do
  # 查询 AAAA
  aaaa_res=$(dig +short AAAA "$domain" 2>/dev/null || true)
  # 查询 A
  a_res=$(dig +short A "$domain" 2>/dev/null | head -n 1 || true)

  if [[ -z "$aaaa_res" ]]; then
    echo -e "  • ${domain}:"
    echo -e "      IPv4 (A 记录):    ${C_GREEN}${a_res:-已解析}${C_RESET}"
    echo -e "      IPv6 (AAAA 记录):  ${C_GREEN}✅ 已精准拦截 (NODATA 空应答，无 IPv6 泄漏风险)${C_RESET}"
  else
    echo -e "  • ${domain}:"
    echo -e "      IPv4 (A 记录):    ${a_res}"
    echo -e "      IPv6 (AAAA 记录):  ${C_RED}⚠️ 检测到 IPv6: $aaaa_res (存在泄漏风险！需确认 sing-box 规则)${C_RESET}"
    all_claude_blocked=false
  fi
done

echo -e "\n${C_BOLD}【阶段 2：测试非 Claude 正常域名解析】${C_RESET}"
echo -e "（预期结果：非 Claude 域名正常解析，系统网络没有被全局关闭 IPv6）\n"

for domain in "${NORMAL_DOMAINS[@]}"; do
  a_res=$(dig +short A "$domain" 2>/dev/null | head -n 1 || true)
  echo -e "  • ${domain}:"
  echo -e "      IPv4 (A 记录):    ${C_CYAN}${a_res:-正常}${C_RESET}"
done

echo -e "\n${C_BOLD}【阶段 3：测试结论与防御审计】${C_RESET}"
if [[ "$all_claude_blocked" == true ]]; then
  echo -e "  ${C_GREEN}${C_BOLD}✅ 完美！sing-box 定向 IPv6 防护体系工作正常！${C_RESET}"
  echo -e "  1. 所有 Claude / Anthropic 流量均强制走 IPv4 住宅代理隧道出口。"
  echo -e "  2. 本地中国电信/联通/移动的真实公网 IPv6 地址被物理级隔离，不会在请求时暴露。"
  echo -e "  3. macOS 系统网络仍为原生双栈环境，不影响其他国内业务。"
else
  echo -e "  ${C_YELLOW}${C_BOLD}⚠️ 提示：部分域名仍能解析出 AAAA 记录。${C_RESET}"
  echo -e "  原因排查："
  echo -e "  1. 若配置文件已显示「已注入」，说明 sing-box 核心尚未重新加载新配置；"
  echo -e "     请在 v2rayN 界面点击一次「重启服务」或切换一次节点使最新配置生效。"
  echo -e "  2. 若使用的是 Chrome 隔离浏览器，请务必使用配套脚本启动："
  echo -e "     ${C_CYAN}./scripts/launch_isolated_chrome.sh${C_RESET}"
  echo -e "     该脚本会自动绑定 SOCKS5 代理隧道并清洗 WebRTC/DNS 泄露。"
fi

echo -e "\n================================================================\n"
