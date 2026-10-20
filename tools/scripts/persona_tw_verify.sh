#!/usr/bin/env bash
# ==============================================================================
# FXXK CLAUDE - 台湾人格一致性体检 (只读，不做任何修改)
# ==============================================================================
# 检查项：区域 / 语言 / 时区 / 主机名 / DNS / IPv6 / 代理 / hosts / 浏览器 Profile /
#         Claude Desktop 配置 / CLI 身份文件
# 用法：
#   ./persona_tw_verify.sh           # 本地检查
#   ./persona_tw_verify.sh --online  # 追加出口 IP 归属检查（需要联网）
# ==============================================================================

set -uo pipefail
ONLINE=0
[[ "${1:-}" == "--online" ]] && ONLINE=1

PASS=0; FAIL=0; WARN=0
C_R="\033[0m"; C_G="\033[32m"; C_RD="\033[31m"; C_Y="\033[33m"; C_B="\033[1m"

ok()   { printf "  ${C_G}✅ PASS${C_R}  %s\n" "$1"; PASS=$((PASS+1)); }
bad()  { printf "  ${C_RD}❌ FAIL${C_R}  %s\n" "$1"; FAIL=$((FAIL+1)); }
warn() { printf "  ${C_Y}⚠️  WARN${C_R}  %s\n" "$1"; WARN=$((WARN+1)); }

echo -e "\n${C_B}台湾人格一致性体检 · $(date '+%Y-%m-%d %H:%M:%S %Z%z')${C_R}"
echo -e "${C_B}============================================================${C_R}"

# ---------- 1. 区域 ----------
LOC="$(defaults read -g AppleLocale 2>/dev/null || echo unknown)"
case "$LOC" in
  zh_TW|zh-Hant-TW) ok "AppleLocale = $LOC" ;;
  *) bad "AppleLocale = ${LOC}（期望 zh_TW）" ;;
esac

# ---------- 2. 语言 ----------
LANGS="$(defaults read -g AppleLanguages 2>/dev/null | tr -d '\n' | tr -s ' ')"
if echo "$LANGS" | grep -q "zh-Hant-TW"; then
  ok "AppleLanguages 含 zh-Hant-TW"
else
  bad "AppleLanguages 缺少 zh-Hant-TW → $LANGS"
fi
if echo "$LANGS" | grep -q "zh-Hans"; then
  warn "AppleLanguages 仍含简体中文（zh-Hans），会污染 navigator/Intl 语言链"
fi

# ---------- 3. 时区 ----------
TZ_LINK="$(readlink /etc/localtime 2>/dev/null || true)"
if echo "$TZ_LINK" | grep -q "Asia/Taipei"; then
  ok "系统时区 = Asia/Taipei"
else
  CURRENT_TZ="$(echo "$TZ_LINK" | sed 's#.*zoneinfo/##')"
  bad "系统时区 = ${CURRENT_TZ:-unknown}（期望 Asia/Taipei）"
fi

# ---------- 4. 主机名 ----------
CN="$(scutil --get ComputerName 2>/dev/null || echo unknown)"
if echo "$CN" | LC_ALL=C grep -q '[^ -~]'; then
  bad "ComputerName 含非 ASCII：$CN"
elif echo "$CN" | grep -qiE 'eweadn|xiaomi|huawei|lenovo|thinkpad|redmi'; then
  warn "ComputerName 含品牌/机型痕迹：${CN}（建议改为 MacBook-Pro）"
else
  ok "ComputerName = $CN"
fi

# ---------- 5. DNS ----------
DNS_LIST="$(networksetup -listallnetworkservices 2>/dev/null | tail -n +2 | while IFS= read -r svc; do
  d="$(networksetup -getdnsservers "$svc" 2>/dev/null | tr '\n' ' ')"
  [[ -n "$d" && "$d" != *"aren't any"* ]] && echo "$svc: $d"
done)"
if echo "$DNS_LIST" | grep -qE '114\.114\.114\.114|223\.5\.5\.5|119\.29\.29\.29|180\.76\.76\.76'; then
  bad "检测到大陆 DNS（会泄漏真实地区）：$(echo "$DNS_LIST" | grep -E '114\.114|223\.5\.5\.5|119\.29|180\.76' | head -2 | tr '\n' ' ')"
elif echo "$DNS_LIST" | grep -qE '1\.1\.1\.1|8\.8\.8\.8|9\.9\.9\.9'; then
  ok "DNS 使用境外公共解析：$(echo "$DNS_LIST" | head -2 | tr '\n' ' ')"
elif [[ -z "$DNS_LIST" ]]; then
  warn "未读取到自定义 DNS（TUN 模式下由代理接管，需另做 DNS 泄漏测试）"
else
  warn "DNS 配置非标准：$(echo "$DNS_LIST" | head -2 | tr '\n' ' ')"
fi

# ---------- 6. IPv6 ----------
V6="$(networksetup -getinfo Wi-Fi 2>/dev/null | grep -i '^IPv6' || echo 'IPv6: unknown')"
case "$V6" in
  *"Automatic"*) warn "Wi-Fi IPv6 = Automatic（建议 networksetup -setv6off Wi-Fi）" ;;
  *"none"*|*"Off"*|*"off"*) ok "Wi-Fi IPv6 已关闭（${V6}）" ;;
  *) warn "Wi-Fi IPv6 状态未知：$V6" ;;
esac

# ---------- 7. 系统代理 ----------
PROXY_CFG="$(scutil --proxy 2>/dev/null)"
if echo "$PROXY_CFG" | grep -q "SOCKSEnable : 1\|HTTPEnable : 1\|HTTPSEnable : 1"; then
  warn "系统代理已启用（TUN 模式通常不需要；请确认不会形成双层代理）"
else
  ok "系统代理未启用（TUN / 直连模式）"
fi

# ---------- 8. hosts 污染 ----------
HITS="$(grep -iE 'anthropic|claude\.ai|hcaptcha' /etc/hosts 2>/dev/null | grep -v '^#' | head -5)"
if [[ -n "$HITS" ]]; then
  bad "/etc/hosts 存在 Claude 相关条目（会制造请求异常）：$(echo "$HITS" | head -1)"
else
  ok "/etc/hosts 无 Claude 相关条目"
fi

# ---------- 9. 浏览器 Profile 语言 ----------
PREF="$HOME/.claude_tw_profile/Default/Preferences"
if [[ -f "$PREF" ]]; then
  python3 - "$PREF" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception as e:
    print(f"  \033[33m⚠️  WARN\033[0m  无法解析 Chrome Preferences: {e}"); raise SystemExit
il=d.get('intl',{})
al=il.get('accept_languages','')
loc=il.get('app_locale','')
msg=[]
if al: msg.append(f"accept_languages={al}")
if loc: msg.append(f"app_locale={loc}")
if not msg:
    print("  \033[33m⚠️  WARN\033[0m  Preferences 未找到语言字段（Profile 可能尚未初始化）")
elif 'zh-TW' in al or 'zh-TW' in loc:
    print("  \033[32m✅ PASS\033[0m  Chrome Profile 语言为 zh-TW: " + ", ".join(msg))
else:
    print("  \033[31m❌ FAIL\033[0m  Chrome Profile 语言非 zh-TW: " + ", ".join(msg))
PY
else
  warn "未找到 ${PREF}（尚未用零扩展脚本启动过）"
fi

# ---------- 10. 扩展数量 ----------
EXT_DIR="$HOME/.claude_tw_profile/Default/Extensions"
if [[ -d "$EXT_DIR" ]]; then
  N=$(find "$EXT_DIR" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$N" -eq 0 ]]; then ok "隔离 Profile 扩展数 = 0"; else bad "隔离 Profile 仍有 $N 个扩展（注入即特征）"; fi
else
  ok "隔离 Profile 无扩展目录"
fi

# ---------- 11. Claude Desktop 配置 ----------
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [[ -f "$CFG" ]]; then
  python3 - "$CFG" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception as e:
    print(f"  \033[33m⚠️  WARN\033[0m  Desktop 配置无法解析: {e}"); raise SystemExit
keys=["disableNonessentialTelemetry","disableEssentialTelemetry","disableNonessentialServices","disableAutoUpdates","modelCatalogEnabled","skipWebFetchPreflight"]
on=[k for k in keys if d.get(k) is True]
if on:
    print("  \033[32m✅ PASS\033[0m  遥测开关已显式设置: " + ", ".join(on))
else:
    print("  \033[33m⚠️  WARN\033[0m  未设置任何遥测开关（默认全开；如需少报请用官方开关，勿伪造）")
PY
else
  warn "未找到 Desktop 配置（未安装或未启动过）"
fi

# ---------- 12. 桌面身份锚点 ----------
for f in "$HOME/Library/Application Support/Claude/ant-did" \
         "$HOME/Library/Application Support/Claude/ant-device-registry.json"; do
  if [[ -f "$f" ]]; then
    warn "存在设备锚点 $(basename "$f")（换号前需随新用户一并重置，不要手改内容）"
  fi
done
if [[ -f "$HOME/.claude/.claude.json" ]]; then
  warn "存在 CLI 身份文件 ~/.claude/.claude.json（machineID 未打印）"
fi

# ---------- 13. 出口归属（可选） ----------
if [[ "$ONLINE" == "1" ]]; then
  echo -e "\n${C_B}出口 IP 检查${C_R}"
  J="$(curl -s --max-time 8 https://ipinfo.io/json 2>/dev/null || true)"
  if [[ -n "$J" ]]; then
    C="$(echo "$J" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("country","?"))' 2>/dev/null)"
    T="$(echo "$J" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("timezone","?"))' 2>/dev/null)"
    O="$(echo "$J" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("org","?"))' 2>/dev/null)"
    if [[ "$C" == "TW" ]]; then ok "出口国家 = TW（${O}）"; else bad "出口国家 = ${C}（期望 TW；${O}）"; fi
    if [[ "$T" == "Asia/Taipei" ]]; then ok "出口时区 = Asia/Taipei"; else warn "出口时区 = $T"; fi
  else
    warn "联网检查失败（可能 TUN 未就绪）"
  fi
fi

# ---------- 汇总 ----------
echo -e "\n${C_B}结果：PASS=$PASS  FAIL=$FAIL  WARN=$WARN${C_R}"
[[ "$FAIL" -gt 0 ]] && echo -e "${C_RD}存在 FAIL：先修复再注册/登录/申诉。${C_R}\n" && exit 2
echo -e "${C_G}没有 FAIL。${C_R}\n"
exit 0
