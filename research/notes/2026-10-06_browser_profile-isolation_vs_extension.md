> 📌 专题笔记（2026-10-06）：针对具体问题的时间点结论，可能过时。方向性原则见 [docs/](../../docs/00_PRINCIPLES.md)。

# 浏览器沙箱与扩展权限边界深度剖析：为什么无法单靠插件屏蔽账号污染？

> **核心提问**：*“这个（Chrome 登录态/账号关联/环境污染）不能通过插件进行屏蔽吗？”*  
> **核心结论**：**绝对不能**。在 Chromium 的安全与沙箱架构中，浏览器扩展（Chrome Extension API）与浏览器底层原生 C++ 账户子系统（Gaia / Sync）处于完全不同的特权层级。试图单靠前端插件屏蔽浏览器级账号污染，无异于在沙盒内试图干预宿主机内核。  
> **终极解法**：**必须实施物理级 Chrome Profile 隔离**（即新建独立的「不登录账号」个人资料）。这是零成本、物理级切断关联的唯一可行途径。

---

## 📑 目录

1. [Chromium 架构权限层级：扩展能做什么，不能做什么](#1-chromium-架构权限层级扩展能做什么不能做什么)
2. [Chrome Profile 账号污染的四大底层泄漏机制](#2-chrome-profile-账号污染的四大底层泄漏机制)
3. [为什么浏览器扩展对 Gaia ID 束手无策？](#3-为什么浏览器扩展对-gaia-id-束手无策)
4. [物理 Profile 隔离 vs 插件伪装：能力边界对比矩阵](#4-物理-profile-隔离-vs-插件伪装能力边界对比矩阵)
5. [实操方案：3 步打造零污染物理隔离工作区](#5-实操方案3-步打造零污染物理隔离工作区)
6. [一键自动化隔离启动脚本](#6-一键自动化隔离启动脚本)

---

## 1. Chromium 架构权限层级：扩展能做什么，不能做什么

为了理解为何插件无法屏蔽账号污染，必须先看 Chromium 的分层架构：

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Chromium Native C++ Core (特权核心层)                 │
│  - IdentityManager / OAuth2TokenService / GaiaCookieManager            │
│  - Chrome Sync Engine (跨设备同步书签、历史、表单、凭据)                │
│  - Variations Service (原生注入 X-Client-Data 实验特征)                 │
│  - Network Service (底层 TLS ClientHello / Socket / QUIC 连接)         │
│  - 物理 SQLite 存储: ~/Library/Application Support/Google/Chrome/      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 强制权限隔离与管控
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Chrome Extension API (沙箱扩展层)                   │
│  - DeclarativeNetRequest (有限的 HTTP 标头修改与请求阻断)               │
│  - Isolated World Content Script (独立的 DOM / JS 执行上下文)          │
│  - 权限被严格约束：无法篡改 Google 核心认证请求，无法访问 Native 登录态 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ DOM 注入与原型链 Hook
┌───────────────────────────────────▼────────────────────────────────────┐
│                       Page JavaScript Context (页面层)                 │
│  - Claude.ai 前端代码 / Cloudflare Turnstile 验证码                    │
│  - Statsig 遥测 / 第三方风控 SDK                                       │
└────────────────────────────────────────────────────────────────────────┘
```

### 扩展的沙盒本质
在 Chrome Manifest V3 体系下：
- **Content Scripts** 运行在 **Isolated World**（隔离世界）。虽然它们共享同一个 DOM 树，但其 JavaScript 变量空间与页面主世界是物理隔离的。
- 扩展能修改的仅仅是**页面可感知的环境**（例如 `Intl.DateTimeFormat`、`Date.prototype`、`HTMLCanvasElement` 等）。
- 扩展**完全没有权限**干预浏览器 Native 进程层级的身份管理模块（`//chrome/browser/signin`）。

---

## 2. Chrome Profile 账号污染的四大底层泄漏机制

当你在一个日常使用或曾经登录过个人 Google 账号的 Chrome Profile 中访问 Claude 时，以下 4 个通道会产生不可逆的致命关联：

### ① Gaia ID 与 Chromium 账户状态的全局渗透
- 在 Chrome 中登录 Google 账号后，Google 统一身份标识符（**Gaia ID**，一串形如 `108392817294829104` 的唯一数字）会被固化在当前 Profile 的 `Preferences` 文件及底层安全密钥链中。
- Chromium 内部的 `GaiaCookieManagerService` 会持续维持 `accounts.google.com` 的会话，并分发 `SAPISID`、`APISID`、`SSID`、`HSID` 等高信誉持久化 Cookie。
- **关联风险**：当你使用 Google SSO 登录 Claude 时，Anthropic 直接获取经过 Google 认证的固定 Sub/Gaia ID。如果该 Gaia ID 曾绑定过中国大陆手机号、曾在高危网络环境下登录、或曾关联过其他被封禁的 Anthropic 账号，**风控系统在 0.1 秒内即可完成图谱合并并执行封杀**。

### ② Chromium 原生 `X-Client-Data` 标头注入
- Chromium 核心的 `VariationsService` 会为每个 Chrome 实例生成一组实验 ID 与设备特征种子，并在向所有 Google 域名（包括 Google OAuth、Google APIs、gstatic、google-analytics）发起请求时，于底层 C++ 网络栈直接附加 `X-Client-Data` HTTP 标头。
- **扩展无法剥离**：Chrome 安全策略明确禁止扩展通过 `declarativeNetRequest` 或 `webRequest` 拦截或篡改浏览器核心发送给 Google 自身域名的关键安全/系统标头。

### ③ 物理 SQLite 缓存与持久化存储残留
- Chrome 的每个 Profile 拥有独立的持久化数据库集群：
  - `Cookies` (SQLite)
  - `History` (SQLite)
  - `Login Data` (SQLite)
  - `IndexedDB` & `Service Worker Cache`
- 如果你在日常 Profile 中使用 Claude，即使你清除了 `claude.ai` 的 Cookie，第三方风控探针依然可以通过跨域缓存（HSTS Supercookie、Font Cache 指纹、Favicon Cache 等）比对出该浏览器实例的历史特征。

### ④ 扩展自身环境的混杂污染
- 你的日常 Profile 中通常安装了油猴脚本（Tampermonkey）、各类广告拦截器、国内翻译插件、购物助手等。
- 这些插件在页面中注入的变量、CSS 特征、DOM 节点会被 Cloudflare Turnstile 与 CreepJS 深度扫描。只要发现异常的 DOM 篡改，即被判定为「高风险非真人浏览器环境」。

---

## 3. 为什么浏览器扩展对 Gaia ID 束手无策？

很多开发者会问：*“我写一个插件，把所有 Google 相关的 Header 删掉，把 Cookie 删掉不行吗？”*

答案是：**行不通，且会引发更严重的风控反弹**。

1. **特权保护拒绝拦截**：  
   Chrome 官方为了防止恶意扩展劫持用户的 Google 账户，在 Chromium 源码中对 `*.google.com` 的特定认证请求设置了硬编码白名单/保护层。扩展试图在扩展层阻断 Google 内部认证，通常会被静默忽略或直接报错。
2. **Google SSO 登录必须依赖真实 Auth Token**：  
   如果你要在 Claude 上使用「Sign in with Google」，前端就必须与 Google OAuth 2.0 端点交互。如果插件强行抹除会话，你将直接无法登录；如果不抹除，Gaia ID 就会自然暴露。
3. **“此地无银三百两”的反指纹特征**：  
   如果一个插件试图在 JS 层拦截所有全局属性，破坏了 `Function.prototype.toString` 或篡改了原生对象的原型链，Cloudflare Turnstile 会通过原型链完整性校验（Prototype Integrity Check）直接触发验证码死循环，甚至标记为自动化机器人。

---

## 4. 物理 Profile 隔离 vs 插件伪装：能力边界对比矩阵

防封体系不是单点技术，而是层次分明的立体防线。下表清晰展示了各层级的实际能力边界：

| 防御维度 | 浏览器扩展 (`Claude Shield`) | 物理隔离 Profile (`Continue without account`) | 结论与权责 |
| :--- | :---: | :---: | :--- |
| **Gaia ID / 个人 Google 关联** | ❌ 无法拦截 | 🟢 **100% 物理隔绝 (无账号)** | **必须由 Profile 隔离负责** |
| **Chrome Sync 跨设备同步追踪** | ❌ 无法干预 | 🟢 **100% 完全不存在同步** | **必须由 Profile 隔离负责** |
| **日常浏览历史/旧 Cookie 污染** | ❌ 无法清理系统库 | 🟢 **100% 纯净全新 SQLite 库** | **必须由 Profile 隔离负责** |
| **混杂插件干扰 (油猴/翻译等)** | ❌ 无法阻止其他插件运行 | 🟢 **100% 独占纯净扩展环境** | **必须由 Profile 隔离负责** |
| **WebRTC STUN 私网/真实 IP 泄露** | 🟢 **100% 底层阻断与 SDP 清洗** | ❌ 默认有暴露风险 | **由 Claude Shield 负责** |
| **时区 (Intl / Date) 动态对齐** | 🟢 **100% 毫秒级对齐节点时区** | ❌ 默认跟随 macOS 系统时区 | **由 Claude Shield 负责** |
| **Canvas / WebGL 硬件去重微噪** | 🟢 **100% 离屏渲染微噪** | ❌ 默认返回真实硬件指纹 | **由 Claude Shield 负责** |
| **IPv6 (AAAA) 本地电信宽带泄露** | ❌ 扩展层无法彻底拦截 DNS | ❌ 依赖系统/网络层 | **由 sing-box DNS 规则负责** |

> 💡 **黄金法则**：  
> **物理 Profile 隔离**解决的是**「身份层与存储层的物理清白」**；  
> **Claude Shield 扩展**解决的是**「运行时的指纹拟真与网络特征对齐」**；  
> **sing-box TUN** 解决的是**「出口 IP 纯净度与 IPv6 物理阻断」**。  
> 三者环环相扣，缺一不可！

---

## 5. 实操方案：3 步打造零污染物理隔离工作区

创建一个完全干净、与个人日常完全隔离的 Chrome Profile 极其简单，**无需第三方指纹浏览器（如比特、AdsPower 等需要付费且本身有特征的商业软件）**，原生 Chrome 仅需 1 分钟：

### 第一步：创建独立个人资料（不登录账号）
1. 打开当前正在使用的 Google Chrome。
2. 点击右上角你的**个人资料头像**图标（位于右上角三个点左侧）。
3. 在下拉面板最底部，点击 **「添加」 (+ Add)**。
4. 在弹出的「设置新的 Chrome 个人资料」页面中，**务必点击**：
   👉 **「在不登录账号的情况下继续」 (Continue without an account)**。
5. 命名为：`Claude-Secure`，挑选一个独特的颜色主题（例如深紫色或纯黑），勾选「创建桌面快捷方式」，点击「完成」。

### 第二步：在新个人资料中仅加载专用护盾扩展
1. Chrome 会自动打开一个全新的、没有任何历史记录和任何插件的纯净窗口。
2. 在新窗口地址栏输入：`chrome://extensions/` 并回车。
3. 开启右上角 **「开发者模式」**。
4. 点击 **「加载已解压的扩展程序」**，选择目录：
   `/Users/mac/FXXK CLAUDE/tools/extension`
5. 确认扩展加载成功，并在扩展选项中选择「⚡ 智能对齐当前 VPN」或「🇹🇼 固定台湾专线」。

### 第三步：从此专号专用
- **严禁**在该隔离窗口中登录任何国内百度、知乎、淘宝、QQ、163 等账号。
- **严禁**在该窗口中登录你日常使用的个人主力 Google 账号。
- 仅用于登录通过安全途径（iOS 免短信渠道）注册的专用 Gmail，并直达 `claude.ai`。

---

## 6. 一键自动化隔离启动脚本

为了进一步提升便利性，我们在本项目 `scripts/` 目录中提供了专用的命令行沙箱启动脚本：
[launch_isolated_chrome.sh](file:///Users/mac/FXXK%20CLAUDE/tools/scripts/launch_isolated_chrome.sh)

该脚本通过指定专属 `--user-data-dir` 启动一个物理文件隔离的 Chrome 实例，彻底切断与 macOS 系统中默认 Chrome 目录的任何数据交换：

```bash
cd "/Users/mac/FXXK CLAUDE/tools/scripts"
./launch_isolated_chrome.sh
```

此命令会在本地专属安全隔离目录 `/Users/mac/.claude_isolated_profile` 中初始化独立的数据库，天然保证零污染、零 Gaia ID 绑定。
