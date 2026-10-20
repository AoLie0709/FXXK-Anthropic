#!/usr/bin/env bash
# ==============================================================================
# FXXK CLAUDE - Node Purity & Risk Audit Tool (节点纯净度与欺诈风险审计)
# ==============================================================================
# Usage:
#   ./check_node_purity.sh              # 自动检测当前网络（TUN 或当前默认）
#   ./check_node_purity.sh 10811        # 指定本地 SOCKS5 端口（如 10811）
# ==============================================================================

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$DIR/../.." && pwd)"
LOGS_DIR="$PROJECT_ROOT/output/audits"
mkdir -p "$LOGS_DIR"
export FXC_AUDIT_DIR="$LOGS_DIR"

# 颜色定义
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_RED="\033[31m"
C_YELLOW="\033[33m"
C_CYAN="\033[36m"
C_BLUE="\033[34m"
C_MAGENTA="\033[35m"

SOCKS_PORT="${1:-}"
PROXY_ARG=""

if [[ -n "$SOCKS_PORT" ]]; then
  PROXY_ARG="--socks5-hostname 127.0.0.1:$SOCKS_PORT"
  echo -e "${C_CYAN}ℹ 使用指定代理: socks5://127.0.0.1:$SOCKS_PORT${C_RESET}"
elif [[ -n "${ALL_PROXY:-}" ]]; then
  PROXY_ARG="--proxy $ALL_PROXY"
  echo -e "${C_CYAN}ℹ 使用系统 ALL_PROXY: $ALL_PROXY${C_RESET}"
elif [[ -n "${http_proxy:-}" ]]; then
  PROXY_ARG="--proxy $http_proxy"
  echo -e "${C_CYAN}ℹ 使用系统 http_proxy: $http_proxy${C_RESET}"
else
  # 探测常见 v2rayN 端口
  if nc -z 127.0.0.1 7897 2>/dev/null; then
  PROXY_PORT="7897"
elif nc -z 127.0.0.1 10811 2>/dev/null; then
    PROXY_ARG="--socks5-hostname 127.0.0.1:10811"
    echo -e "${C_CYAN}ℹ 自动检测到 v2rayN 本地 SOCKS 端口 10811，自动启用${C_RESET}"
  elif nc -z 127.0.0.1 7897 2>/dev/null; then
  PROXY_PORT="7897"
elif nc -z 127.0.0.1 10808 2>/dev/null; then
    PROXY_ARG="--socks5-hostname 127.0.0.1:10808"
    echo -e "${C_CYAN}ℹ 自动检测到 v2rayN 本地 SOCKS 端口 10808，自动启用${C_RESET}"
  else
    echo -e "${C_YELLOW}ℹ 未指定代理端口，使用当前系统路由（TUN 虚拟网卡模式）${C_RESET}"
  fi
fi

echo -e "\n${C_BOLD}================================================================${C_RESET}"
echo -e "${C_BOLD}🛡️  FXXK CLAUDE - 出口节点纯净度与欺诈风险审计${C_RESET}"
echo -e "${C_BOLD}================================================================${C_RESET}\n"

echo -e "正在向多源 IP 数据库与 Cloudflare 边缘节点发起探测..."

# 1. 查询 ipwho.is
IPWHO_RAW=$(curl -sS --max-time 8 $PROXY_ARG "https://ipwho.is/" 2>/dev/null || echo "{}")

# 2. 查询 Cloudflare CDN trace
CF_TRACE=$(curl -sS --max-time 6 $PROXY_ARG "https://1.1.1.1/cdn-cgi/trace" 2>/dev/null || echo "")

# 解析 Cloudflare trace
CF_IP=$(echo "$CF_TRACE" | grep '^ip=' | cut -d'=' -f2 || true)
CF_COLO=$(echo "$CF_TRACE" | grep '^colo=' | cut -d'=' -f2 || true)
CF_LOC=$(echo "$CF_TRACE" | grep '^loc=' | cut -d'=' -f2 || true)

# 使用 Python 解析详细 JSON 数据
python3 - "$IPWHO_RAW" "$CF_IP" "$CF_COLO" "$CF_LOC" << 'PYEOF'
import sys, json

raw_json = sys.argv[1]
cf_ip = sys.argv[2]
cf_colo = sys.argv[3]
cf_loc = sys.argv[4]

try:
    data = json.loads(raw_json)
except Exception:
    data = {"success": False, "message": "无法连接到 ipwho.is"}

success = data.get("success", False)
ip = data.get("ip", cf_ip or "未知")
country = data.get("country", cf_loc or "未知")
country_code = data.get("country_code", cf_loc or "未知")
city = data.get("city", "未知")
region = data.get("region", "未知")
timezone = data.get("timezone", {}).get("id", "未知")
tz_utc = data.get("timezone", {}).get("utc", "未知")
isp = data.get("connection", {}).get("isp", "未知")
asn = data.get("connection", {}).get("asn", "未知")
org = data.get("connection", {}).get("org", "未知")

# 风险特征评估
security = data.get("security", {})
is_proxy = security.get("proxy", False)
is_vpn = security.get("vpn", False)
is_tor = security.get("tor", False)
is_hosting = security.get("hosting", False)

# 住宅识别
is_hinet = "hinet" in isp.lower() or "chunghwa" in isp.lower() or str(asn) == "3462"
is_residential = not is_hosting and (is_hinet or "telecom" in isp.lower() or "broadband" in isp.lower() or "cable" in isp.lower())

# 计算综合风险评分 (0-100，越低越好，对应 Bewild 评分体系)
risk_score = 0
reasons = []

if country_code in ["CN", "IR", "KP", "RU", "SY"]:
    risk_score += 100
    reasons.append("高危国家/受限制司法管辖区 (直接封禁)")
elif country_code not in ["US", "TW", "JP", "SG", "GB", "DE", "FR", "CA", "AU"]:
    risk_score += 20
    reasons.append(f"非主流支持国家 ({country_code})")

if is_hosting:
    risk_score += 45
    reasons.append("机房托管/数据中心 IP (Data Center / Hosting)")
else:
    reasons.append("家庭住宅/宽带 IP (Residential / ISP)")

if is_tor:
    risk_score += 50
    reasons.append("Tor 出口节点")
if is_proxy or is_vpn:
    risk_score += 25
    reasons.append("公共 VPN/代理网段标记")

if is_hinet:
    risk_score = max(0, risk_score - 20)
    reasons.append("★ 台湾中华电信 (Chunghwa Telecom AS3462) 顶级住宅白名单信誉")

risk_score = min(100, max(0, risk_score))

# 终端输出
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[32m"
C_RED = "\033[31m"
C_YELLOW = "\033[33m"
C_CYAN = "\033[36m"

print(f"{C_BOLD}【1. 出口网络基础信息】{C_RESET}")
print(f"  • 公网 IPv4:        {C_CYAN}{ip}{C_RESET}")
print(f"  • 国家/地区:        {country} ({country_code})")
print(f"  • 城市/省份:        {city}, {region}")
print(f"  • 标准 IANA 时区:   {C_CYAN}{timezone}{C_RESET} ({tz_utc})")
print(f"  • 运营商 (ISP):     {isp}")
print(f"  • 自治系统 (ASN):   AS{asn} ({org})")
print(f"  • Cloudflare 边缘:  {cf_colo} (Airport Code: {cf_colo or '直连'})")

print(f"\n{C_BOLD}【2. 纯净度与欺诈特征扫描】{C_RESET}")
print(f"  • IP 类型判定:      {'🏠 家庭宽带 / 住宅 IP (Residential)' if is_residential else '🏢 机房 / 数据中心 (Data Center)'}")
print(f"  • VPN / 代理标记:   {'⚠️ 命中' if (is_proxy or is_vpn) else '✅ 干净 (未标记)'}")
print(f"  • 数据中心托管:     {'⚠️ 是 (机房 IP)' if is_hosting else '✅ 否 (原生民用 ISP)'}")
print(f"  • Tor 匿名节点:     {'⚠️ 是' if is_tor else '✅ 否'}")

print(f"\n{C_BOLD}【3. Bewild / Anthropic 综合风控评级】{C_RESET}")
if risk_score <= 10:
    badge = f"{C_GREEN}{C_BOLD}[0~10 / 100 极佳 - 顶级住宅专线]{C_RESET}"
    verdict = f"{C_GREEN}✅ 极度安全！极力推荐用于 Claude 注册与订阅。{C_RESET}"
elif risk_score <= 35:
    badge = f"{C_YELLOW}{C_BOLD}[{risk_score} / 100 良好 - 普通民用/优质节点]{C_RESET}"
    verdict = f"{C_YELLOW}⚡ 风险较低，可配合 Claude Shield 正常使用。{C_RESET}"
else:
    badge = f"{C_RED}{C_BOLD}[{risk_score} / 100 高危 - 机房/脏 IP]{C_RESET}"
    verdict = f"{C_RED}❌ 高危警告！强烈建议更换为台湾中华电信 (HiNet) 等原生住宅节点！{C_RESET}"

print(f"  • 预测风险指数:     {badge}")
print(f"  • 判定建议:         {verdict}")
print(f"  • 关键特征依据:")
for r in reasons:
    print(f"      - {r}")

# 保存审计日志
report = {
    "ip": ip,
    "country": country,
    "country_code": country_code,
    "city": city,
    "timezone": timezone,
    "isp": isp,
    "asn": asn,
    "cloudflare_colo": cf_colo,
    "is_residential": is_residential,
    "is_hosting": is_hosting,
    "risk_score": risk_score,
    "reasons": reasons
}

import time
import os
logs_dir = sys.argv[1] if len(sys.argv) > 5 else "logs"
ts = time.strftime("%Y%m%d_%H%M%S")
log_path = os.path.join(os.environ.get("FXC_AUDIT_DIR", "."), f"node_audit_{ts}.json")
try:
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n{C_CYAN}📄 审计结果已保存至: {log_path}{C_RESET}")
except Exception as e:
    pass

PYEOF

echo -e "\n================================================================\n"
