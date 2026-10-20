# 🛠️ Claude 全端自洽防封标准化部署与换号重生 SOP

> **核心法则**：**【真实环境自洽 > 恶意指纹伪造】**。  
> 不修改系统全局中文、不安装第三方魔改指纹插件、不使用非官方客户端。通过标准系统配置与官方受支持开关，实现 100% 官方基准纯净度。

---

## 目录
1. [阶段一：macOS 宿主系统基线校准 (免改全局中文)](#阶段一macos-宿主系统基线校准-免改全局中文)
2. [阶段二：网络链路与 DNS 防泄露对齐](#阶段二网络链路与-dns-防泄露对齐)
3. [阶段三：Chrome 专属沙盒 Profile 搭建 (零插件准则)](#阶段三chrome-专属沙盒-profile-搭建-零插件准则)
4. [阶段四：桌面端 (Claude.app) 官方遥测清零与净化](#阶段四桌面端-claudeapp-官方遥测清零与净化)
5. [阶段五：换号重生五件套一次性物理重置](#阶段五换号重生五件套一次性物理重置)
6. [阶段六：iOS 手机端纯净避坑指南](#阶段六ios-手机端纯净避坑指南)

---

## 阶段一：macOS 宿主系统基线校准 (免改全局中文)

### 1.1 主机名去中文化 (防御 `uVi()` 探针)
默认的“张三的 MacBook Pro”会被桌面端 `uVi()` 函数直接抓取并作为 `displayName` 上报，瞬间暴露境内身份。

```bash
# 统一设置纯 ASCII 英文主机名 (可自定义，如 macbook-work 或 air-m2)
sudo scutil --set ComputerName "macbook-air"
sudo scutil --set HostName "macbook-air"
sudo scutil --set LocalHostName "macbook-air"
```

### 1.2 桌面端单应用语言隔离 (无需修改系统全局中文)
全局保持简体中文不影响日常使用。利用 Cocoa 层的 App-level override 针对 Claude Desktop 单独注入英文环境：

```bash
# 将 Claude Desktop 的读取语言注入为美式英文，隔离宿主中文
defaults write com.anthropic.claudefordesktop AppleLanguages '("en-US", "en")'
defaults write com.anthropic.claudefordesktop AppleLocale "en_US"

# 验证写入结果
defaults read com.anthropic.claudefordesktop
```

---

## 阶段二：网络链路与 DNS 防泄露对齐

### 2.1 剔除国内高危 DNS (防御 114 / 运营商泄露)
```bash
# 将 Wi-Fi 和以太网均设置为 Cloudflare 与 Google 安全 DNS
sudo networksetup -setdnsservers "Wi-Fi" 1.1.1.1 8.8.8.8
sudo networksetup -setdnsservers "Ethernet" 1.1.1.1 8.8.8.8 2>/dev/null || true

# 验证当前 DNS
networksetup -getdnsservers "Wi-Fi"
```
*(注：如果使用台湾住宅节点，亦可配置中华电信官方 DNS：`168.95.1.1`)*

### 2.2 物理禁用 IPv6 (防御蜂窝与公网 IPv6 穿透)
国内运营商分配的公网 IPv6 会绕过部分 TUN 代理直连 Cloudflare，暴露境内 ISP 归属。
```bash
# 物理关闭 Wi-Fi IPv6
sudo networksetup -setv6off "Wi-Fi"
sudo networksetup -setv6off "Ethernet" 2>/dev/null || true
```

### 2.3 代理软件三纪律
1. **必须开启 TUN 模式 / 增强模式**：确保非 HTTP 流量与 DNS 劫持生效；
2. **严禁开启 HTTPS 抓包解密 (MITM)**：避免自签名 CA 破坏原生的 TLS JA4 密码套件握手指纹；
3. **节点选择自洽**：推荐台湾中华电信 HiNet（AS3462）静态住宅，时区 `Asia/Taipei`（UTC+8）与北京时间时差为 0 小时，Scamalytics 欺诈分为 0。

---

## 阶段三：Chrome 专属沙盒 Profile 搭建 (零插件准则)

### 3.1 独立 Profile 专号专用
1. 打开 Chrome，右上角头像点击 **“添加”** 创建新个人资料（如 `独立专用 Profile`）；
2. 登录专用的海外 Gmail 账号；
3. **铁律**：严禁在该 Profile 中登录或切换曾经被封禁过的旧账号！

### 3.2 启用 Chrome 加密 DNS (DoH)
1. 进入 Chrome **设置** -> **隐私和安全** -> **安全** (`chrome://settings/security`)；
2. 找到“使用安全 DNS”，选择 **自定义 (Custom)**；
3. 填入 Cloudflare DoH 模板：`https://1.1.1.1/dns-query`。

### 3.3 扩展插件准则：保持 0 插件
- **绝不安装任何“防指纹”、“随机 Canvas”、“伪造 UA”的扩展**；
- 插件的注入不仅破坏 V8 原型链，还会触发 Anthropic 前端 `app.document_gutted` 警报与 Cloudflare 空白 Iframe 夺舍反噬。原生 Chrome 即是最高防御。

---

## 阶段四：桌面端 (Claude.app) 官方遥测清零与净化

Anthropic 官方在白皮书中明确支持企业与隐私配置。**用官方合法参数关闭遥测，远胜于用第三方工具 Hook 拦截！**

编辑或创建配置文件：
`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "disableNonessentialTelemetry": true,
  "disableEssentialTelemetry": true,
  "disableNonessentialServices": true,
  "disableAutoUpdates": true,
  "modelCatalogEnabled": false,
  "skipWebFetchPreflight": true
}
```

CLI 命令行环境配置（写入 `~/.zshrc`）：
```bash
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export DISABLE_TELEMETRY=1
export DISABLE_ERROR_REPORTING=1
export DO_NOT_TRACK=1
```

---

## 阶段五：换号重生五件套一次性物理重置

若账号遭遇封禁，绝对不能仅清 Cookie 就登录新号。必须一次性完成以下五件套重置：

```
┌────────────────────────────────────────────────────────┐
│ ① ant-did 与设备注册表                                 │
│    rm -rf ~/Library/Application\ Support/Claude/ant-did│
│    rm -rf ~/Library/Application\ Support/Claude/ant-*  │
├────────────────────────────────────────────────────────┤
│ ② CLI 机器标识缓存                                    │
│    rm -rf ~/.claude/.claude.json                       │
├────────────────────────────────────────────────────────┤
│ ③ macOS 钥匙串凭据                                     │
│    打开【钥匙串访问】(Keychain Access)，搜索并删除：     │
│    • Claude Safe Storage                               │
│    • Claude Key                                        │
│    • Claude Code-credentials                           │
│    • .audit-key                                        │
├────────────────────────────────────────────────────────┤
│ ④ 浏览器隔离 Profile                                   │
│    彻底删除旧 Chrome Profile，新建全新干净 Profile     │
├────────────────────────────────────────────────────────┤
│ ⑤ 支付身份与 Apple ID                                  │
│    彻底报废充值过被封账号的 Apple ID，全新注册境外 ID  │
└────────────────────────────────────────────────────────┘
```

> **终极绝招：新建 macOS 系统用户**  
> 如果不想逐项清理钥匙串与底层沙盒，可在 macOS 【系统设置】$\rightarrow$【用户与群组】中**新建一个标准用户（例如 `WorkTW`）**。该新用户天生拥有全新的 Keychain 沙盒、独立的 Secure Enclave 签名上下文和纯净的 Chrome 配置，一键彻底物理断绝历史关联！

---

## 阶段六：iOS 手机端纯净避坑指南

1. **绝对不要用旧 Apple ID 充值**：StoreKit 2 的 `original_transaction_id` 终生锁死，复用必封；
2. **Apple 账号分离**：系统主 iCloud 保持国内 ID 不动，仅在 App Store 的【媒体与购买项目】中单登境外 Apple ID；
3. **资金链安全**：仅使用官方渠道购买的 App Store Gift Card 充值余额；
4. **定位权限**：进入 iOS 设置 -> 隐私与安全 -> 定位服务 -> Claude -> 设为 **“永不”**；
5. **禁用蜂窝网络直接访问**：在外部无代理 Wi-Fi 环境下，建议关闭 Claude 的蜂窝网络开关，防止无意触发直连。
