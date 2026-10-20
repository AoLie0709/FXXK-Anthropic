#!/usr/bin/env bash
# ==============================================================================
# Claude Desktop 定向语言伪装（零系统改动，可一键回滚）
# ==============================================================================
# 做三件事（只影响 Claude.app，不影响系统与其他 App）：
#   1. config.json 的 locale: zh-Hans → zh-Hant（应用持久化语言）
#   2. per-app defaults：com.anthropic.claudefordesktop 的 AppleLanguages/AppleLocale
#   3. 可选 --clean-account：清掉 lastKnownAccountUuid 与 oauth 缓存（换号前用）
#
# 用法：
#   ./desktop_locale_spoof.sh                 # dry-run，只显示将做什么
#   ./desktop_locale_spoof.sh --apply         # 执行（会退出并重启 Claude.app）
#   ./desktop_locale_spoof.sh --apply --clean-account
#   ./desktop_locale_spoof.sh --revert        # 回滚到最近一次备份
# ==============================================================================

set -uo pipefail
BUNDLE="com.anthropic.claudefordesktop"
APP_NAME="Claude"
CFG="$HOME/Library/Application Support/Claude/config.json"
ACTION="dry"; CLEAN=0
for a in "$@"; do
  case "$a" in
    --apply) ACTION="apply" ;;
    --revert) ACTION="revert" ;;
    --clean-account) CLEAN=1 ;;
  esac
done

C_R="\033[0m"; C_B="\033[1m"; C_G="\033[32m"; C_Y="\033[33m"
echo -e "\n${C_B}Claude Desktop 定向语言伪装${C_R}"
echo -e "${C_B}============================================================${C_R}"

quit_app() { osascript -e "tell application \"$APP_NAME\" to quit" >/dev/null 2>&1 || true; sleep 2; }
open_app() { open -a "$APP_NAME" >/dev/null 2>&1 || true; }

if [[ "$ACTION" == "revert" ]]; then
  LAST="$(ls -t "$CFG".bak-* 2>/dev/null | head -1)"
  if [[ -z "$LAST" ]]; then echo "没有找到备份"; exit 1; fi
  quit_app
  cp -p "$LAST" "$CFG" && echo -e "${C_G}已恢复：$LAST${C_R}"
  defaults delete "$BUNDLE" AppleLanguages 2>/dev/null || true
  defaults delete "$BUNDLE" AppleLocale 2>/dev/null || true
  open_app
  echo -e "已重启 Claude.app\n"; exit 0
fi

if [[ "$ACTION" == "dry" ]]; then
  echo -e "${C_Y}DRY-RUN：加 --apply 才会执行${C_R}\n"
  echo "  1) 备份 $CFG"
  echo "  2) config.json: locale → zh-Hant$([[ $CLEAN -eq 1 ]] && echo '（并清除 lastKnownAccountUuid / oauth 缓存）')"
  echo "  3) defaults write $BUNDLE AppleLanguages -array zh-Hant-TW zh-Hant en-US en"
  echo "  4) defaults write $BUNDLE AppleLocale -string zh_TW"
  echo "  5) 重启 Claude.app"
  echo -e "\n${C_Y}注意：不要点击「生成诊断报告 → 发送」，该报告会写入 System Locale（当前 zh_CN）。${C_R}\n"
  exit 0
fi

# ---- apply ----
[[ -f "$CFG" ]] || { echo "未找到 $CFG（Claude.app 尚未运行过？）"; exit 1; }
quit_app
TS="$(date +%Y%m%d-%H%M%S)"
BAK="$CFG.bak-$TS"
cp -p "$CFG" "$BAK" && chmod 600 "$BAK"
echo -e "  备份: ${C_G}$BAK${C_R}"

python3 - "$CFG" "$CLEAN" <<'PY'
import json,sys
p=sys.argv[1]; clean=sys.argv[2]=='1'
d=json.load(open(p))
before=d.get('locale')
d['locale']='zh-Hant'
removed=[]
if clean:
    for k in ['lastKnownAccountUuid','oauth:tokenCacheV2','oauth:tokenCache']:
        if k in d:
            del d[k]; removed.append(k)
json.dump(d,open(p,'w'),ensure_ascii=False,indent=2)
print(f"  locale: {before} → zh-Hant")
if removed: print("  已清除: " + ", ".join(removed))
PY

defaults write "$BUNDLE" AppleLanguages -array zh-Hant-TW zh-Hant en-US en
defaults write "$BUNDLE" AppleLocale -string zh_TW
echo -e "  per-app 语言覆盖已写入 ${C_G}$BUNDLE${C_R}"

open_app
echo -e "\n${C_G}完成。请确认 Claude.app 界面已变为繁體中文。${C_R}"
echo -e "若界面未变：用回滚 → 改用启动参数方式（见方案文档 §4 的 fallback）。"
echo -e "回滚命令：$0 --revert\n"
