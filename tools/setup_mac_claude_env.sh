#!/bin/bash
set -e

echo "=========================================="
echo "  Claude macOS 纯净环境一键标准化初始化脚本  "
echo "=========================================="

# 1. 净化 Claude 桌面端历史残留与 Keychain
echo "[1/5] 清理 Claude Desktop 历史痕迹与钥匙串..."
killall Claude 2>/dev/null || true
rm -rf ~/Library/Application\ Support/Claude
rm -rf ~/Library/Caches/com.anthropic.claudefordesktop*
rm -f ~/Library/Preferences/com.anthropic.claudefordesktop.plist
rm -rf ~/Library/Saved\ Application\ State/com.anthropic.claudefordesktop.savedState
rm -rf /tmp/claude*
security delete-generic-password -s "Claude Safe Storage" 2>/dev/null || true
security delete-generic-password -s "Anthropic Safe Storage" 2>/dev/null || true
security delete-generic-password -s "Claude Key" 2>/dev/null || true

# 2. 注入独立语言偏好（保持系统中文，仅桌面端设为英文）
echo "[2/5] 注入 Claude Desktop 语言隔离配置 (en-US)..."
defaults write com.anthropic.claudefordesktop AppleLanguages '("en-US", "en")'
defaults write com.anthropic.claudefordesktop AppleLocale "en_US"

# 3. 随机化 machineID
echo "[3/5] 随机化 ~/.claude/.claude.json machineID..."
python3 -c "
import os, json, secrets
p = os.path.expanduser('~/.claude/.claude.json')
if os.path.exists(p):
    with open(p, 'r') as f:
        d = json.load(f)
    d['machineID'] = secrets.token_hex(32)
    with open(p, 'w') as f:
        json.dump(d, f, indent=2)
    print('  -> MachineID successfully randomized!')
" 2>/dev/null || true

# 4. 纠正系统 DNS 泄露源
echo "[4/5] 绑定网络接口安全 DNS (1.1.1.1 / 8.8.8.8)..."
networksetup -setdnsservers "Wi-Fi" 1.1.1.1 8.8.8.8 2>/dev/null || true
networksetup -setdnsservers "Ethernet" 1.1.1.1 8.8.8.8 2>/dev/null || true

# 5. 校验代理端口连通性
echo "[5/5] 校验代理端口 7897..."
if curl -s -x http://127.0.0.1:7897 https://www.google.com -o /dev/null --connect-timeout 3; then
    echo ">> [SUCCESS] 代理端口 7897 握手成功！网络完全畅通！"
else
    echo ">> [WARNING] 请确认 Clash Verge 已经启动，且 mixed-port 为 7897！"
fi

echo "=========================================="
echo "  恭喜！本台 Mac 已完成全部安全加固与标准化部署！"
echo "=========================================="
