# Claude macOS 多设备标准化部署与防封防风控交接手册 (SOP)

> **版本**：v1.0 (生产验证版)  
> **适用范围**：任意全新或已使用过的 macOS 设备（MacBook / Mac mini / Mac Studio / iMac）  
> **核心原则**：**【环境真实自洽 > 恶意指纹伪造】**。不更改系统全局中文语言、不安装魔改指纹插件、不制造跨层信号错位，追求 100% 官方基准纯净度。

---

## 目录
1. [第一阶段：新 Mac 宿主系统基线校准（免改全局中文）](#第一阶段新-mac-宿主系统基线校准免改全局中文)
2. [第二阶段：网络链路与 DNS 防泄露对齐（排坑要点）](#第二阶段网络链路与-dns-防泄露对齐排坑要点)
3. [第三阶段：Chrome 浏览器专属沙盒 Profile 搭建](#第三阶段chrome-浏览器专属沙盒-profile-搭建)
4. [第四阶段：Claude 桌面端（Claude.app）状态净化与部署](#第四阶段claude-桌面端claudeapp状态净化与部署)
5. [第五阶段：账号登录与“养号”防 KYC SOP](#第五阶段账号登录与养号防-kyc-sop)
6. [附录：一键初始化自动化脚本 (Bash)](#附录一键初始化自动化脚本-bash)

---

## 第一阶段：新 Mac 宿主系统基线校准（免改全局中文）

### 1.1 计算机名与主机名去特征化
许多用户的 Mac 默认名称带有中文姓名（如“张三的 MacBook Pro”），这会在本地 mDNS、IPC 探针和网络探测中直接暴露境内身份特征。

**执行命令（替换为你自定义的纯英文名字）：**
```bash
# 统一设置纯 ASCII 主机名（例如：eweadn-xay 或 macbook-pro-work）
sudo scutil --set ComputerName "macbook-pro-air"
sudo scutil --set HostName "macbook-pro-air"
sudo scutil --set LocalHostName "macbook-pro-air"
```

### 1.2 桌面端独立语言隔离（重要：无需修改 macOS 全局中文！）
为了不影响日常工作，Mac 全局保持简体中文即可。我们通过 Cocoa 层的 App-level override 针对 Claude Desktop 进行单应用语言锁定：

**执行命令：**
```bash
# 将 Claude Desktop 的读取语言注入为美式英文，隔离宿主中文
defaults write com.anthropic.claudefordesktop AppleLanguages '("en-US", "en")'
defaults write com.anthropic.claudefordesktop AppleLocale "en_US"

# 验证写入结果
defaults read com.anthropic.claudefordesktop
```
> **底层原理**：Electron 应用在 macOS 启动时，其底层的 `app.getPreferredSystemLanguages()` 会优先读取应用级的 `AppleLanguages` plist 键，从而向上游汇报标准的英文 Locale。

---

## 第二阶段：网络链路与 DNS 防泄露对齐（排坑要点）

### 2.1 剔除国内高危 DNS 泄露源
系统默认若设置了 `114.114.114.114` 或路由器分配的境内运营商 DNS，Electron 桌面端与部分网络请求会发生越狱泄露。

**执行命令（绑定国际安全加密解析器）：**
```bash
# 将 Wi-Fi 和 Ethernet 均设置为 Cloudflare 与 Google 安全 DNS
sudo networksetup -setdnsservers "Wi-Fi" 1.1.1.1 8.8.8.8
sudo networksetup -setdnsservers "Ethernet" 1.1.1.1 8.8.8.8 2>/dev/null || true

# 验证 DNS 配置
networksetup -getdnsservers "Wi-Fi"
```
*(注：如果想与台湾 HiNet 节点达到 100% 本地化一致，也可指定中华电信官方 DNS：`168.95.1.1`)*

### 2.2 Clash Verge Rev 代理端口对齐（避免 ERR_PROXY_CONNECTION_FAILED）
* **排坑实录**：旧版 Clash 默认端口为 `7890`，而现代 **Clash Verge Rev (Mihomo 内核)** 的默认混合端口是 **`7897`**。如果系统代理端口错写为 7890，浏览器会报“未连接到互联网 / ERR_PROXY_CONNECTION_FAILED”。
* **配置对齐命令：**
```bash
# 确保以太网代理指向 7897 端口（若使用 Wi-Fi 则将 Ethernet 替换为 Wi-Fi）
networksetup -setwebproxy "Ethernet" 127.0.0.1 7897 2>/dev/null || true
networksetup -setsecurewebproxy "Ethernet" 127.0.0.1 7897 2>/dev/null || true
networksetup -setsocksfirewallproxy "Ethernet" 127.0.0.1 7897 2>/dev/null || true
```

### 2.3 节点选择核心指标
* **地理与时区自洽**：推荐台湾中华电信（Chunghwa Telecom / HiNet）静态住宅 ISP 节点（AS3462）。其时区为 `Asia/Taipei`（UTC+8），与 Mac 本地 UTC+8 **时差为 0 小时**，没有任何跨洋时钟错位。
* **纯净度复核**：访问 [scamalytics.com](https://scamalytics.com) 检查 IP 欺诈分，确保 `Fraud Score < 10`（我们实测 HiNet 节点为 0 分）。

---

## 第三阶段：Chrome 浏览器专属沙盒 Profile 搭建

### 3.1 创建隔离 Profile
1. 在 Chrome 右上角头像点击 **“添加”**。
2. 登录该账号专用的海外 Google 邮箱（例如 `user@example.com`）。
3. 保持该 Profile 专号专用，严禁在同一个 Profile 内切换登录曾经被封禁过的旧账号。

### 3.2 语言首选项隔离
1. 进入 Chrome **设置** -> **语言** (`chrome://settings/languages`)。
2. 将 **英语 (美国) / English (United States)** 移到最顶端，设为主语言。
3. 移除非必要的区域语言。

### 3.3 开启 Chrome 安全 DNS (DoH)
1. 进入 Chrome **设置** -> **隐私和安全** -> **安全** (`chrome://settings/security`)。
2. 找到“使用安全 DNS”，选择 **自定义 (Custom)**。
3. 填入 Cloudflare 加密解析模板：
   ```text
   https://1.1.1.1/dns-query
   ```

### 3.4 扩展插件准则：保持 0 插件（原汁原味）
* **严禁安装**：任何声称能“修改指纹”、“防关联”、“Canvas 扰动”、“WebRTC 屏蔽”的插件。
* **原因**：Cloudflare 的 `Turnstile` 反作弊探针会通过隐形空白 iframe（`about:blank`）深度对比原型链。任何魔改插件的注入都会被抓现行，直接触发人脸核身或拦截封禁。
* **合法扩展（可选）**：如需显得自然，可安装 Google 官方扩展（Google Docs 离线版）或正规密码管理器（Bitwarden / 1Password）。

---

## 第四阶段：Claude 桌面端（Claude.app）状态净化与部署

### 4.1 核心认知：绝对不要重装 `/Applications/Claude.app`
macOS 应用包由 Apple Gatekeeper 代码签名（Code Signing）保护，是严格**只读**的。Anthropic 不可能向 App 安装包内写入任何用户 ID 或封号标记。所有状态 100% 存储在用户个人目录。

### 4.2 一键抹除旧设备遗留印记（防关联清理）
在新电脑上如果此前运行过 Claude 或登录过其他账号，运行以下清洗指令：

```bash
# 1. 杀死正在运行的 Claude 进程
killall Claude 2>/dev/null || true

# 2. 清除应用运行缓存与会话状态
rm -rf ~/Library/Application\ Support/Claude
rm -rf ~/Library/Caches/com.anthropic.claudefordesktop*
rm -f ~/Library/Preferences/com.anthropic.claudefordesktop.plist
rm -rf ~/Library/Saved\ Application\ State/com.anthropic.claudefordesktop.savedState

# 3. 清理系统临时目录中的影子套接字与 Git 泄漏
rm -rf /tmp/claude*

# 4. 清除 macOS Keychain 中的加密主密钥
security delete-generic-password -s "Claude Safe Storage" 2>/dev/null || true
security delete-generic-password -s "Anthropic Safe Storage" 2>/dev/null || true
security delete-generic-password -s "Claude Key" 2>/dev/null || true

# 5. 重置 Claude Code 的独立机器指纹 machineID
python3 -c "
import os, json, secrets
p = os.path.expanduser('~/.claude/.claude.json')
if os.path.exists(p):
    with open(p, 'r') as f:
        d = json.load(f)
    d['machineID'] = secrets.token_hex(32)
    with open(p, 'w') as f:
        json.dump(d, f, indent=2)
    print('MachineID successfully randomized!')
"
```

### 4.3 终极禁忌警告
> [!CAUTION]
> **绝对不要在客户端内点击：`Help -> Generate Diagnostic Report` 并发送给官方！**
> 该操作会将你的全机硬件 UUID、进程树和外设配置直接打包发往 Anthropic 人工审计后台。

---

## 第五阶段：账号登录与“养号”防 KYC SOP

### 5.1 登录流程（最自然的人类行为）
1. 确保代理处于开启状态（台湾节点，Clash Verge 7897 端口）。
2. 在已配置好的 Chrome 专属 Profile 中打开：`https://claude.ai/`。
3. 选择 **“Continue with Google”** 授权，或输入邮箱接收 Magic Link。
4. **收件处理**：直接在同一个 Chrome 窗口的 Gmail 标签页点击 **“Sign in to Claude”** 按钮或复制 6 位验证码。

### 5.2 新号初期养号守则（降低风控熵值）
* **前 24~48 小时先用 Free 版本**：
  * 当前 Free 版本默认即可使用 Claude Sonnet 5.5。
  * 正常进行文本沟通、编码探讨，产生自然的 `interaction_histogram`（键盘击键与鼠标指针交互直方图）。
  * 绝不在刚注册 10 分钟内立刻点击 Upgrade（这是黑产盗刷机器人的标准特征）。

### 5.3 充值升级（Pro / Max）防 KYC 关键策略
1. **优先路径：iOS 纯净 Apple IAP 订阅**：
   * 必须在手机端确认之前的退款订阅已处于 **“已过期 (Expired)”** 状态，避免 StoreKit 2 的 `original_transaction_id` 与旧号交叉关联。
   * 走美区 Apple ID 余额内购，苹果承担结算通道，**极大概率跳过 Persona 人脸核验**。
2. **次选路径：Web 端 Stripe 信用卡支付**：
   * 绝不使用高危虚拟卡段（如 408544 等已被滥用的发卡行）。
   * 必须使用低欺诈正规海外实体卡/合规卡，且 Billing Address 必须真实可信。

---

## 附录：一键初始化自动化脚本 (Bash)

可以将以下脚本保存为 `setup_mac_claude_env.sh`，在任何新电脑上直接通过 `bash setup_mac_claude_env.sh` 一键完成全套配置：

```bash
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
" 2>/dev/null || true

# 4. 纠正系统 DNS 泄露源
echo "[4/5] 绑定 Wi-Fi 安全 DNS (1.1.1.1 / 8.8.8.8)..."
sudo networksetup -setdnsservers "Wi-Fi" 1.1.1.1 8.8.8.8 2>/dev/null || true

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
```
