# ⚖️ 风控积分制机理与「真实环境自洽」终极破局哲学

> **核心命题**：
> 1. 为什么“写防御探针去对抗、伪造指纹”必死无疑？
> 2. 为什么保持五个端口原生一致性的难度，远低于将五个端口伪造成一套假数据的难度？
> 3. Anthropic 的风控引擎底层究竟是如何通过“多信号打分积分制”对账号进行审判的？

---

## 一、 风控系统的核心骨架：多信号打分积分制 (Risk Scoring Engine)

不要把封号想象成“某一个 if-else 规则触发就立刻拔电源”。现代成熟的 SaaS 反欺诈与合规系统（包括 Anthropic 自身风控、Cloudflare Bot Management、Stripe Radar、Persona KYC）采用的是**动态风险积分累加模型（Cumulative Risk Scoring）**。

```
                  ┌────────────────── 多源信号输入层 ──────────────────┐
                  │ • 网络层：ASN 信誉、IP 类型 (ISP/DataCenter)、DoH/DNS 泄漏、IPv6     │
                  │ • 硬件层：Secure Enclave 硬件公证、Keychain 历史、Mac 年代画像          │
                  │ • 宿主层：OS 语言、系统时区、scutil 主机名、defaults 环境变量          │
                  │ • 浏览器：CF oneshot Iframe 夺舍、WebGL/Canvas 签名、Client Hints 对齐   │
                  │ • 行为层：interaction_histogram 键鼠时序、打字停顿、停留毫秒数           │
                  │ • 支付层：Apple StoreKit 2 历史回执、original_transaction_id 黑图谱    │
                  │ • 身份层：邮箱信誉、Team-Scoped Hide My Email、组织关联图谱            │
                  └─────────────────────────┬──────────────────────────┘
                                            │
                                            ▼
                  ┌────────────────── 动态加权积分评估引擎 ───────────────┐
                  │                 总风险分 = Σ (信号权重 × 异常系数)    │
                  │              + 历史风险沉积 (Historical Residue)       │
                  │              + 关联黑名单惩罚 (Graph Association)      │
                  └─────────────────────────┬──────────────────────────┘
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         ▼                                  ▼                                  ▼
   【白区：0 ~ 25 分】              【灰区：26 ~ 75 分】               【黑区：76 ~ 100+ 分】
      🟢 正常放行                     🟡 观察与递进质询                   🔴 立即封禁与连坐
 • 正常流式补全                   • 静默下发 hCaptcha 算力 PoW        • 下发 bad_standing
 • 正常功能权限                   • 降频与速率限制 (Rate Limit)       • ban_category: "other"
 • 无感背景监控                   • 触发 Persona KYC 证件核验         • Consumer + API 组织连坐
                                  • 延迟至首扣款/周末批处理处决       • StoreKit 2 回执加入黑图谱
```

### 1.1 积分制运作的三大核心定律

#### 定律一：弱信号累加效应 (Weak Signal Accumulation)
- 单个孤立的弱信号（例如偶尔在公共 Wi-Fi 断流、或者使用了稍冷门的浏览器窗口分辨率）**通常不足以封号**，系统只扣 5~10 分，账号仍处于白区；
- 但如果：**大陆出口 DNS 泄露（+20分） + 系统语言含 zh-CN 与繁中撕裂（+25分） + 复制粘贴长文本且无敲击时序（+15分） + 刚注册就暴冲充值（+20分） = 80分** $\rightarrow$ 瞬间越过安全阈值！

#### 定律二：时间衰减与延迟清算机制 (Delayed Purge & Settlement)
- 用户常有的错觉是：“我今天这么配，注册成功了，用了一天没封，说明我的防关联环境完美了！”
- **事实残酷相反**：风控系统为了防止黑产通过“试错法”快速探测其规则边界，往往采用**延迟处决**机制：
  1. **首扣款复核点**：升级订阅支付的瞬间，风控权重由 0.2 飙升至 1.0；
  2. **KYC 状态机异步审计**：Persona 图像质量后台复核（对焦反光、景深不自然）完成后触发；
  3. **周末/凌晨定时清算批处理**：后台离线跑图计算，将共享相同设备、支付凭据的关联簇一次性拔除。

#### 定律三：硬性致命红线 (Hard Killswitches - 一击必杀)
在积分制之外，存在若干条无论其他维度多高分，一旦触碰直接判 100 分秒杀的硬性红线：
1. **StoreKit 2 黑图谱连坐**：使用充值过被封账号的 Apple ID 再次为新账号付费（`original_transaction_id` 命中已封存历史记录）；
2. **Secure Enclave / ant-did 设备锚点命中**：未清理系统底层 Keychain 与设备注册公钥散列，直接同机登录；
3. **反篡改归一化器明文判伪**：检测到 `is_automation: true`、或修改了 User-Agent 却与 `sec-ch-ua` 架构冲突（`ua_client_hints: mismatch`）。

---

## 二、 防御悖论：为什么写防御探针去对抗反而死得更快？

在对抗初期，几乎所有极客或安全工程师的第一反应都是：**“写一个插件，把所有探针都给 Hook 掉、拦截掉、或者伪造成全假数据！”**

用户自述中的血泪经验印证了这一安全领域的铁律：**在反欺诈博弈中，防御性篡改（Defensive Spoofing）是一条通往必封的绝路。**

### 2.1 反噬漏洞一：归一化器（Anti-Tampering Normalizers）的自证陷阱
Anthropic 前端部署的 `@ant/o11y` 遥测核心，根本不依赖外部猜测你有没有伪造，它直接把**篡改检测作为成绩单显式上报**：
- 当你的指纹插件 Hook 了 `navigator.userAgent`，将其伪造成 Windows Chrome；
- 但是原生的 Chromium `navigator.userAgentData.getHighEntropyValues(["architecture"])` 依然由 C++ 引擎底层直接返回 `arm`（Apple Silicon）；
- 前端脚本一比对，立即向服务端 `POST /api/event_logging/v2/batch` 上报：
  ```json
  {
    "ua_form": "reduced",
    "ua_client_hints": "mismatch", // 👈 插件伪造自曝！
    "is_automation": false
  }
  ```
- **后果**：你以为你在伪装，服务端直接拿到了你伪造失败的供词。

### 2.2 反噬漏洞二：Cloudflare `jsd/oneshot` 的空白 Iframe 同步夺舍
在 HAR-1 与 HAR-2 的全量逆向中，我们揭开了最震撼的反欺诈实证：
```javascript
// Cloudflare jsd/main.js 函数 B() 核心源码
R = document.createElement("iframe");
R.style = "display: none";
document.body.appendChild(R);
o = R.contentWindow; // 👈 同步获取空白 Iframe 的崭新原生 Realm！
J = vUAjb0(o, o.navigator, "n.", J); // 采集子 iframe 未污染的原生 navigator！
document.body.removeChild(R); // 同一毫秒内销毁！
```
- **反噬过程**：即便你在当前主窗口把 `window.navigator.language` 焊死成了 `zh-TW`，把内存伪造成了 `8GB`；
- 但 `appendChild` 与读取 `contentWindow` 是**在同一个微任务周期内同步执行**的，Chrome 扩展脚本根本无法在两行同步 JS 之间注入子 iframe；
- Cloudflare 直接在空白子 Realm 中抓取到了未被污染的真实底层数据：`zh-CN`、`deviceMemory: 16`、`outerWidth: 1920`！
- **后果**：解密的 16,547 字节报文中同时出现了 `zh-TW` 与 `zh-CN`，**主从 Realm 矛盾直接判定为恶意环境欺诈**。

### 2.3 反噬漏洞三：原型链投毒与 `Function.prototype.toString` 暴露
当你尝试使用 `Object.defineProperty` 覆写某个原生属性（如 WebGL renderer、Canvas、时区）：
1. **原型链脱落**：反作弊代码执行 `Object.getOwnPropertyDescriptor(Navigator.prototype, 'language')`，检查该属性是否位于原型上，还是被直接赋给了实例对象；
2. **toString 投毒检测**：执行 `Function.prototype.toString.call(navigator.userAgent)`，原生函数会返回 `function userAgent() { [native code] }`。如果被闭包包裹，一旦 `toString` 没有做到 100% 严丝合缝的伪装，或者 `toString` 本身被 Hook，只需一行 `eval("toString")` 即可识破；
3. **性能时延指纹**：每次属性访问被 Proxy 或 Hook 拦截，执行耗时往往是原生 C++ 绑定的 10~50 倍。前端时序直方图分析（Interaction Histogram）能清晰看到异常的微秒级调用抖动。

### 2.4 反噬漏洞四：网络栈指纹（TLS JA4 / HTTP/2）与应用层伪装的致命撕裂
- 即使你在应用层把浏览器伪造成了 Windows 上的 Edge 浏览器；
- 但是在网络传输层，macOS 系统的 TCP 初始窗口大小（Window Size）、TCP Options 顺序、TLS Client Hello 中的密码套件偏好列表（JA3 / JA4 签名）、以及 HTTP/2 帧的 Settings 序列，全部是 **macOS Darwin 内核与原生 Chrome 的固有特征**；
- Cloudflare 边缘节点在 TCP 握手完成的第 1 毫秒，就已经给你的底层网络栈打上了 `os: macos, browser: chrome` 的标签。当它看到 HTTP 载荷里宣称自己是 Windows 时，**跨层撕裂度达到 100%，直接加满风险分**。

### 2.5 反噬漏洞五：熵增悖论（The Entropy Paradox）
- 全球有数以亿计的普通用户在使用 Mac、iPhone、Chrome 正常访问 Claude；
- 这些真实用户的指纹哈希高度集中在几十个标准分布区间内；
- 当你给浏览器装上防指纹插件、随机化 Canvas 噪点、伪造音频上下文、修改硬件核心数时——**你的指纹在全球数据库中变成了一个独一无二的“变异奇点”（Unique Fingerprint）**！
- **防指纹插件不但没有让你“隐入尘烟”，反而像在黑夜中打出了一道探照灯。**

---

## 三、 破局哲学：全端真实环境一致性（True Environmental Consistency）

### 3.1 核心数学逻辑：为什么保持一致性是唯一解？

让我们进行一次严谨的复杂度对比：

| 对比维度 | 路线 A：全端伪造/防御探针对抗（Spoofing） | 路线 B：全端真实自洽一致性（Consistency） |
| :--- | :--- | :--- |
| **涵盖终端** | Web、手机 iOS、桌面 Electron、封号页、邮箱验证 | 同样的 5 大终端 |
| **需要伪造的面** | 硬件 Enclave、Keychain、TCP/TLS JA4、子 Iframe Realm、键鼠微秒曲线、StoreKit 2 回执、WebRTC、MCC/MNC、邮件 Referer、系统 Hostname | **0 个**（全部保留原生真实物理表现） |
| **实现的复杂度** | **$O(N^K)$ 指数级爆炸**（5 端 $\times$ 50 个探针面，任何一个端点出现 1 个字节的不一致，即刻触发风控图谱撕裂） | **$O(1)$ 常数级极简**（只需锚定一个真实的目标身份与自洽网络，所有端口自然对齐） |
| **被抓概率** | **接近 100%**（无法解决空白 Iframe 夺舍、Enclave 硬件签名与 JA4 协议栈撕裂） | **趋近于 0**（行为和特征与目标地区的普通海外真人毫无二致） |
| **维护成本** | 平台前端每次发版更新混淆代码，所有 Hook 插件全部失效并暴露；每日提心吊胆 | 部署完成后零维护；不依赖任何第三方插件，原生稳定运行数年 |

> **关键真理**：  
> **把这五个端全部伪造成一模一样的假环境，在工程上是不可能的任务；  
> 但让这五个端全部原生指向同一个真实、自洽、稳定的环境，不仅简单，而且坚不可摧！**

---

## 四、 五端口自洽终极架构规范 (The 5-Port Consistency Architecture)

为了实现绝对自洽，必须将以下 5 个端口严格锚定在同一个物理现实中（以最推荐的 **台湾中华电信 HiNet 静态住宅 ISP** 为基准画像）：

```
┌────────────────────────────────────────────────────────────────────────┐
│                      🎯 目标统一画像：台湾住宅普通用户                      │
│                (IP: 台北 HiNet / 时区: Asia/Taipei / 语言: 繁体中文)          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
      ┌──────────────┬─────────────┼──────────────┬──────────────┐
      ▼              ▼             ▼              ▼              ▼
  【① 操作系统层】 【② 网络传输层】 【③ 身份凭据层】 【④ 支付沙盒层】 【⑤ 客户端应用层】
  • 纯英文主机名  • 台湾住宅出口  • 纯海外 Gmail  • 全新境外 Apple ID • 官方客户端零修改
  • Asia/Taipei  • 全程远端 DoH   • 专号独立环境  • 官方正品礼品卡  • 官方受支持关闭遥测
  • 移除大陆时区  • 关闭 IPv6 泄漏 • 彻底弃绝国内  • 绝不复用旧收据  • 换号五件套一次性
  • 系统语言自洽  • 阻断 WebRTC    Apple ID/中继  • 渐进使用积累时序  彻底物理清空
```

### 4.1 第一端口：操作系统层（OS Layer - macOS）
- **主机名去中文化**：许多人 Mac 默认计算机名为“张三的 MacBook Pro”。桌面端 `uVi()` 无条件抓取主机名，直接暴毙。必须通过 `sudo scutil --set ComputerName "macbook-air"` 设为纯 ASCII 英文名；
- **时区物理对齐**：台湾时区为 `Asia/Taipei`（UTC+8）。选择台湾的最大优势在于：**与北京时间时差为 0 小时**！无需牺牲日常生活将 Mac 改成美西时间；
- **语言隔离不扰民**：无需修改整个 macOS 的全局中文。通过 Cocoa 层的 App-level override 针对 Claude 单独注入：
  ```bash
  defaults write com.anthropic.claudefordesktop AppleLanguages '("en-US", "en")'
  defaults write com.anthropic.claudefordesktop AppleLocale "en_US"
  ```
  底层 Electron 的 `app.getPreferredSystemLanguages()` 即向服务端返回标准英文。

### 4.2 第二端口：网络传输层（Network Layer）
- **出口纯净度**：选用商业 ISP / 住宅静态宽带（如 Chunghwa Telecom HiNet AS3462），Scamalytics 欺诈分保证为 0；
- **DNS 零境内泄露**：系统网络设置中彻底剔除 `114.114.114.114`，绑定 Cloudflare 加密解析器 `1.1.1.1` 或 HiNet 官方 DNS `168.95.1.1`，浏览器开启 DoH；
- **IPv6 物理断网**：国内运营商分配的 IPv6 地址会直接穿透代理并向 Cloudflare 暴露大陆运营商归属。必须执行 `networksetup -setv6off "Wi-Fi"`；
- **绝不开启 HTTPS 抓包解密**：代理软件开启 MITM 会重写 TLS Client Hello，摧毁原生的 JA4 指纹。必须保持端到端直通。

### 4.3 第三端口：身份凭据层（Identity Layer）
- **专号专环境**：严禁在同一个浏览器 Profile 或同一个 macOS 登录会话中切换新旧账号；
- **弃绝国内 Apple ID 与私密邮箱**：Apple 的 Hide My Email 是 **Team-Scoped** 的！无论生成多少个私密邮箱，其对应的底层主体 ID 相同，直接连坐；
- **纯净海外邮箱**：通过干净的 iOS 邮件原生通道注册免手机验证码的 Google 账号（Gmail），专号专用。

### 4.4 第四端口：支付生命周期层（Payment Sandbox Layer）
- **废弃旧 Apple ID**：只要这个 Apple ID 曾在旧账号上订阅过，其关联的 `original_transaction_id` 已经进入 Anthropic 的 StoreKit 2 连坐黑图谱。新账号必须使用全新注册的境外 Apple ID；
- **资金链纯正**：仅使用 Apple 官网或 Amazon 官方直营的 App Store Gift Card 充值，不绑定来历不明的虚拟信用卡；
- **节奏自然，拒绝暴冲**：不要第一天就直接升级 Max 5x，先在 Free / Pro 下正常对话几天，在 `antalytics_queue_v1` 中积累充分的人类 `interaction_histogram` 键鼠时序再逐步升级。

### 4.5 第五端口：客户端与遥测层（Client & Telemetry Layer）
- **零篡改插件**：不用任何防关联指纹插件，不用反代魔改客户端。保留原生 Chrome 与官方 Electron；
- **利用官方受支持配置关闭遥测**：Anthropic 官方在《Telemetry and egress》白皮书中支持合规关闭遥测。我们不是伪造数据，而是通过受支持的参数合法关闭：
  ```json
  // ~/Library/Application Support/Claude/claude_desktop_config.json
  {
    "disableNonessentialTelemetry": true,
    "disableEssentialTelemetry": true,
    "disableNonessentialServices": true,
    "disableAutoUpdates": true,
    "modelCatalogEnabled": false,
    "skipWebFetchPreflight": true
  }
  ```
  CLI 侧：配置 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`、`DO_NOT_TRACK=1`。关闭后只保留必需的推理与更新出口，干净利落。

---

## 五、 换号铁律：五件套一次性物理重置

如果账号已被封禁，绝对不能“只换个邮箱”或“只清一下 Cookie”就原机登录新号！根据前述探针字典，必须一次性完成以下五件套物理重置：

```
① ant-did + ant-device-registry.json        ── 彻底删除或在新系统用户下重新生成
② ~/.claude/.claude.json                    ── 清除 CLI machineID 与 userID
③ macOS 钥匙串 (Keychain)                   ── 清理 Claude Safe Storage / hwkey / .audit-key
④ 浏览器环境                                ── 彻底新建专属 Chrome Profile，弃用旧 Profile
⑤ 支付身份                                  ── 彻底更换全新境外 Apple ID，终生不再复用旧 ID
```

> **最彻底且最高雅的解法**：在 macOS 的【系统设置】$\rightarrow$【用户与群组】中**新建一个独立的标准用户（如 `WorkTW`）**。  
> 此时，macOS 系统会自动为该用户创建全新的 Keychain 沙盒、独立生成的 Secure Enclave 访问上下文、干净的 Home 目录和 Chrome 用户配置。所有旧号的历史残留被物理级隔离切断，成本极低，却具有终极安全性！
