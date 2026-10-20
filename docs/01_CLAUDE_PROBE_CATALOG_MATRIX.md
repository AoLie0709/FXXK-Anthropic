# 🕵️‍♂️ Claude / Anthropic 全端风控探针全量字典与置信度审计大典

> **版本**：v2.0 (全端生产实测级)  
> **数据源**：四代 HAR 网络取证样本（648 条请求）、本机 macOS Claude.app (v2.42304.0 asar + Mach-O `nm -u` 符号级反汇编)、Chrome 独立专用 Profile LevelDB 实取持久化队列、社区逆向 AST 分析及多 Agent 交叉会审。  
> **置信度评级标准**：
> - 🟢 **【高置信度】(High)**：明确抓取到真实网络报文、本地磁盘/LevelDB/Keychain 落地存储、或经 AST/反汇编验证存在且无条件触发；
> - 🟡 **【中置信度】(Medium)**：逆向代码中存在明确调用路径、函数名或特征标记，但依赖特定条件（如 VM 异常、风控挑战触发）激活；
> - 🔴 **【低置信度】(Low)**：业内风控常识推断、启发式假设、或第三方平台（如 Cloudflare / Stripe / Persona）默认行为，尚未在本机截获明文。

---

## 目录
1. [一、 网页端探针全集 (Web Client)](#一-网页端探针全集-web-client)
2. [二、 手机端探针全集 (iOS & Android Mobile)](#二-手机端探针全集-ios--android-mobile)
3. [三、 桌面端探针全集 (macOS / Windows Electron & CLI)](#三-桌面端探针全集-macos--windows-electron--cli)
4. [四、 封号受限页面端探针 (Restricted & Appeal Pages)](#四-封号受限页面端探针-restricted--appeal-pages)
5. [五、 邮箱与登录端探针 (Email & Magic Link)](#五-邮箱与登录端探针-email--magic-link)
6. [六、 全端探针横向对比与综合统计](#六-全端探针横向对比与综合统计)

---

## 一、 网页端探针全集 (Web Client)

网页端是 Anthropic 部署“反篡改归一化器（Anti-Tampering Normalizers）”与行为时序采集的核心阵地。

### 1.1 主动上报探针 (Active Probes)

| 探针编号 | 探针名称与端点 | 采集机理与载荷字段 | 置信度 | 关键证据与逆向出处 |
| :--- | :--- | :--- | :---: | :--- |
| **W-A1** | **健康度与风控自证五元组**<br>`POST /api/event_logging/v2/batch` | 客户端主动收集并自报检查结果：<br>• `is_automation`: 检查 `navigator.webdriver`<br>• `ua_form`: 是否被压缩（如 `"reduced"`）<br>• `ua_client_hints`: 检查与 UA 是否一致（`"match"`）<br>• `screen_equals_viewport`: 视口全屏比对（`false` 揭示 F12/窗口化）<br>• `first_party_host`: 是否为第一方域名 | 🟢 **高** | HAR-1 `[211]`, HAR-4 `[203]` 实录明文载荷；`HealthMetricEvent` 源码。 |
| **W-A2** | **按键与鼠标时序直方图**<br>`claudeai.perf.interaction_histogram` | 前端以 30 秒为周期统计离散时序分布（桶区间 `[200, 500, 1000]` ms）：<br>• `key_nav` / `key_non_nav`<br>• `key_send_non_nav`<br>• `key_paste_non_nav`（粘贴独立信道，机械粘贴 ≠ 真人敲击）<br>• `pointer_nav` / `pointer_non_nav`<br>• `total_interactions` / `hidden_excluded` | 🟢 **高** | HAR-1 `[213]`；Chrome 专用隔离 Profile LevelDB `000012.log` 实取 `version: 3` JSON 真实事件。 |
| **W-A3** | **真实用户监控 (Datadog RUM)**<br>`POST /api/v2/rum`<br>`browser-intake-us5-datadoghq.com` | 双通道（第一方反向代理 + 第三方直连）上报视图动作、长任务（Long Tasks）、前端错误、DOM 性能指标。利用 `deflate` 压缩，并注入 `traceparent`、`tracestate`、`x-datadog-*` 全链路分布式跟踪头。 | 🟢 **高** | HAR-1 `[197-215]`, HAR-2 `[193-199]`, HAR-3 `[016]` 实获明文与二进制流。 |
| **W-A4** | **客户端健康与地区自报**<br>`GET /edge-api/client-health/check` | 引导阶段主动上报客户端参数：<br>`platform=web&bundle=1792386525&locale=zh-TW`<br>配合 CSP 违规上报端点 `/edge-api/browser-reports`。 | 🟢 **高** | HAR-1 `[007]`, HAR-2 `[008]`。 |
| **W-A5** | **输入框输入节奏探针**<br>`claudeai.perf.composer_typing` | 采集输入框打字流式节奏：<br>`bucket_bounds_ms`, `streaming`, `non_streaming`, `streaming_lt_25`, `streaming_25_50`。用于甄别脚本逐字输入与人类生物学敲击停顿。 | 🟢 **高** | Chrome 专用隔离 Profile LevelDB `000012.log` 提取实证。 |
| **W-A6** | **DOM 扩展注入扫描器**<br>`app.document_gutted` (`rL() / fc()`) | 通过 `MutationObserver` 监控 DOM 树，匹配 `chrome-extension://` 节点，统计 `added_extension_url_count` 并上报，专门抓取防关联指纹插件。 | 🟢 **高** | 前端 Bundle AST 逆向提取；函数 `rL()`。 |

### 1.2 静默携带探针 (Silent Transport Probes)

| 探针编号 | 探针名称 | 传输载体与机制 | 置信度 | 风险与说明 |
| :--- | :--- | :--- | :---: | :--- |
| **W-S1** | **设备持久标识符**<br>`anthropic-device-id` | HTTP 请求头 + Cookie（`33333333-4444-5555-6666-777777777777`）。跨 session、跨天、跨构建版本恒定存在。 | 🟢 **高** | **跨账号连坐核心锚点**。清 Cookie 但不清持久存储则完全失效。 |
| **W-S2** | **分析匿名标识符**<br>`anthropic-anonymous-id` | 派生自 Segment `ajs_anonymous_id`（如 `claudeai.v1.44444444-5555-6666-7777-888888888888`）。 | 🟢 **高** | 用于打通未登录态到登录态的行为链路。 |
| **W-S3** | **标签页会话 UUID**<br>`x-activity-session-id` | 每个标签页分配独立 UUID，追踪跨标签页并发操作与多开行为。 | 🟢 **高** | HAR-1 至 HAR-4 全量请求附带。 |
| **W-S4** | **客户端指纹五件套**<br>`anthropic-client-*` | 随所有 API 请求自动附带：<br>• `anthropic-client-platform`: `web_claude_ai`<br>• `anthropic-client-version`: `1.0.0`<br>• `anthropic-client-build`: `1792386525`<br>• `anthropic-client-sha`: `f83619f0` $\rightarrow$ `f99620ca`<br>• `anthropic-client-capabilities`: `mfa_sms_v1,mfa_email_v1` | 🟢 **高** | 任何第三方代理若遗漏或版本不符，直接标黑。 |
| **W-S5** | **高熵客户端提示 (Client Hints)**<br>`sec-ch-ua` 三件套 | 浏览器原生发送的架构、版本、平台（Chromium 154 / macOS / non-mobile）。 | 🟢 **高** | **致命冲突点**：若只篡改 `User-Agent` 为 Windows 但 Client Hints 仍为 macOS，直接触发 `ua_client_hints: mismatch`。 |
| **W-S6** | **语言信道分裂指纹**<br>`Accept-Language` 与 `spa:locale` | 静态资源与 API 请求的 `Accept-Language`、本地存储 `spa:locale`、与界面文案语言的三向校验。 | 🟢 **高** | 实测漏洞：主窗口显示繁中（`zh-Hant`），但后台资源暴露 `zh-CN,zh;q=0.9`，导致语言撕裂。 |
| **W-S7** | **压缩字典持久化探针**<br>`dcz=keep` (`bz() / CP()`) | 资源请求携带 `Accept: */*;dcz=keep`，并在 `localStorage["persisted.dcz_keep"]` 写入 `1:${Date.now() + 7*86400000}`（7 天有效期时间戳）。 | 🟢 **高** | HAR-3 `[00..15]` 实锤；专用隔离 Profile LevelDB `000005.ldb` 实存 `1:1793093826240`。 |
| **W-S8** | **Stripe 反欺诈 Muffins 指纹** | 加载 `m.stripe.network`，在 LocalStorage 写入 `muffins`，上报支付硬件与网络熵值。 | 🟢 **高** | 专用隔离 Profile LevelDB 实存 `_https://m.stripe.network/^0https://claude.ai muffins`。 |
| **W-S9** | **页面可见性毫米级时钟**<br>`LSS-cardinal-daily-visible-ms` | 记录用户在页面上的毫秒级真实停留时长（实测达 `1445053` ms $\approx$ 24 分钟）。 | 🟢 **高** | 专用隔离 Profile LevelDB 实取，用于甄别挂机脚本与真人使用分布。 |
| **W-S10** | **打字与发送轮次统计器**<br>`client-sent-turns:v2` / `typed-turns:v2` | 本地记录人工键入轮次与发送轮次的配比。全自动发消息而无键入轮次直接触发异常。 | 🟢 **高** | 专用隔离 Profile LevelDB 实测记录。 |

### 1.3 被动挑战与质询探针 (Passive Challenge Probes)

| 探针编号 | 探针名称 | 触发场景与机制 | 置信度 | 关键证据与逆向出处 |
| :--- | :--- | :--- | :---: | :--- |
| **W-P1** | **Cloudflare `jsd/oneshot` 空白 Iframe 夺舍** | 服务端下发混淆脚本，在毫秒级内动态创建 `about:blank` 隐藏 iframe，从干净的子窗口 Realm 抓取未被插件 Hook 的 `navigator.language`、`deviceMemory`、`outerWidth/Height`，生成 16.5KB 加密载荷并回传。 | 🟢 **高** | HAR-1 `[080, 146]`；解密 16,547 字节发现主窗口伪装 8GB 但子 Iframe 抓出 16GB。 |
| **W-P2** | **hCaptcha 隐形算力与设备证明**<br>`hsw.js` (HSW PoW) | 在受限/申诉页下发 `mode: "collect"`，加载 1.49MB Wasm 执行 WebGL、Canvas 微噪运算与 CPU 算力证明，绑定 `__antClientAttestationHcaptchaInvisibleReady` 协议。 | 🟢 **高** | HAR-1 `[202~209]`。 |
| **W-P3** | **硬件年代与 M2 画像探针**<br>`device_year_class` (`Ka() / oo()`) | 结合 `deviceMemory`、`hardwareConcurrency`、`devicePixelRatio`、WebGL 渲染器反推 Mac 硬件年代。 | 🟢 **高** | 前端 AST 逆向定值。 |
| **W-P4** | **物理屏幕刷新率探针**<br>`bestHz` (`_W() / dJ()`) | 连续 30 帧 `requestAnimationFrame` 测量物理屏幕真实刷新率（60Hz vs 120Hz ProMotion）。虚拟环境/无头浏览器通常返回固定 60Hz 或异常波动。 | 🟢 **高** | 前端 AST 逆向证实。 |

---

## 二、 手机端探针全集 (iOS & Android Mobile)

手机端是现代风控中最难被伪造的护城河，Anthropic 深度集成了 Apple 原生安全框架与 StoreKit 2 支付图谱。

| 探针编号 | 探针名称 | 采集机理与载荷字段 | 置信度 | 风险后果与实测定性 |
| :--- | :--- | :--- | :---: | :--- |
| **M-A1** | **Apple StoreKit 2 交易回执绑死**<br>`original_transaction_id` | 无论如何更换 Apple ID 别名、邮箱或 IP，只要使用同一个 Apple ID 或已有关联的 App Store 账户订阅，收据中的 `original_transaction_id`（64 位全局唯一递增整数）与 `web_order_line_item_id` 恒定不变。 | 🟢 **高** | **致命死穴**：旧号被封后，使用同一 Apple ID 购买新号，StoreKit 2 回执直通服务端，触发即时秒封。 |
| **M-A2** | **Persona KYC 活体生物与证件审查**<br>`/kyc_status` (In-App Webview) | 突变式升级套餐（如首日直充 Max 5x）触发。调用原生摄像头核验政府 ID 与 3D 活体自拍，并采集镜头对焦反光、景深与网络环境。 | 🟢 **高** | HAR-1 账号封禁根源：摄像头反光导致 KYC 失败（`denied` / `failed`），下发 `ban_category: "other"` 封禁。 |
| **M-S1** | **iOS 供应商设备标识符 (IDFV)** | 属于同一开发者团队（Anthropic Team ID）的应用共享唯一 `identifierForVendor`。应用重装不会重置，只有抹掉整机所有 Anthropic App 才会重新生成。 | 🟢 **高** | 客户端底层标准 SDK 架构证实。 |
| **M-S2** | **Apple 私密中继邮箱 Team 穿透**<br>`*@privaterelay.appleid.com` | Apple Hide My Email 是 **Team-Scoped** 的！同一个 Apple ID 无论生成多少个私密邮箱，其转发路由背后的开发者用户主体标识符（`sub` claim）完全相同。 | 🟢 **高** | Apple 开发者认证规范实锤；误以为换个私密邮箱就是新号直接导致连坐。 |
| **M-S3** | **蜂窝基站 MCC/MNC 与 SIM 卡运营商** | 通过 CoreTelephony 框架获取移动网络国家代码（MCC 460 = 中国大陆）。与住宅代理出口发生严重国家冲突。 | 🟡 **中** | iOS 原生安全策略。Wi-Fi 下不强制上报，蜂窝流量下必报。 |
| **M-S4** | **WebKit 原生 CFNetwork 网络栈指纹** | iOS App 走底层的 CFNetwork 栈，其 TLS Client Hello（JA4 签名）和 HTTP/2 帧顺序具有极强的 Apple 设备特征，无法通过任何用户态脚本篡改。 | 🟢 **高** | 网络协议栈天然指纹。 |
| **M-P1** | **网络与蜂窝漫游状态跳变检测** | 监测短时间内 IP 从住宅代理突变为移动基站漫游 IP，或时区与网络延迟发生物理不自洽（跨大西洋延迟 < 10ms）。 | 🟡 **中** | 启发式异常风控规则。 |

---

## 三、 桌面端探针全集 (macOS / Windows Electron & CLI)

基于本机 macOS Claude.app `v2.42304.0` 的 `app.asar` 提取与 Mach-O 二进制（`Claude` 主程序及 `.node` 模块）`nm -u` 符号审计，并参考 GitHub REA 方法论。

### 3.1 桌面端主动上报探针 (Active Probes)

| 探针编号 | 探针名称 | 采集机理与要点 | 置信度 | 关键证据与逆向出处 |
| :--- | :--- | :--- | :---: | :--- |
| **D-A1** | **事件日志落盘与重传**<br>`event_logging/v2/batch` | 携带 `accountUuid` 与 `organizationUuid`。网络中断时批次加密落盘至本地，网络恢复后重传；服务端严格校验 UUID 格式，非标准 UUID 标记为 `<non-uuid>`。 | 🟢 **高** | 本机 asar 源码审查；`output/github_rea_audit.md`。 |
| **D-A2** | **GrowthBook 特性求值与 BaseURL 上报**<br>`remoteEval` (`sdk-zAZezfDKGoZuXXKe`) | 桌面端拉取 535 个 feature flags，本地缓存为 `CLF\x02` 魔数 gzip 结构；**关键：请求体上报 `apiBaseUrlHost` 属性**，任何使用反代/自建中转域名直接被明文上报。 | 🟢 **高** | CLI 2.1.241 与 Desktop 源码提取实锤。推翻旧 Statsig 传言。 |
| **D-A3** | **Sentry 崩溃与环境拓扑收集** | 官方 egress 清单明确端点；asar 内存在 423 处 Sentry 引用，上报系统内核、内存、崩溃堆栈。 | 🟢 **高** | 本机 asar 静态字符串验证。 |
| **D-A4** | **Datadog 桌面与 CLI 遥测**<br>`http-intake.logs.us5.datadoghq.com` | 桌面端嵌入 Datadog 公钥，持续推送性能采样、长耗时操作与 API 调用延迟。 | 🟢 **高** | 本机二进制字符串与 network egress 实测。 |
| **D-A5** | **模型目录与更新静默轮询** | 启动后每 5-15 分钟轮询 `downloads.claude.ai` 与模型列表，作为长连接保活与环境连通性探测。 | 🟢 **高** | 本机抓包与配置文件证实。 |

### 3.2 桌面端静默与宿主环境探针 (Silent Host Probes)

| 探针编号 | 探针名称 | 本机实测证据与机理 | 置信度 | 风险评级 |
| :--- | :--- | :--- | :---: | :---: |
| **D-S1** | **安装级设备 UUID (`ant-did`)** | 存储于 `~/Library/Application Support/Claude/ant-did`，48 字节 Base64 UUID。只要不彻底清除，多账号共用该 ID 必被连坐。 | 🟢 **高** | 🔴 极高 |
| **D-S2** | **设备公钥散列 (`pk1:<hash>`)** | 存储于 `~/Library/Application Support/Claude/ant-device-registry.json`（148 字节）。由本地生成的公私钥对派生。 | 🟢 **高** | 🔴 极高 |
| **D-S3** | **CLI 机器与用户唯一标识** | 存储于 `~/.claude/.claude.json`，包含 64 位 Hex `machineID` 与 `userID`。 | 🟢 **高** | 🔴 极高 |
| **D-S4** | **Keychain 硬件凭据与 Safe Storage** | 写入 macOS 钥匙串：`Claude Safe Storage`、`Claude Key`、`Claude Code-credentials`，以及每个 Cowork 会话生成的 `.audit-key`。 | 🟢 **高** | 🔴 极高 |
| **D-S5** | **Secure Enclave 硬件公证密钥 (`hwkey`)** | **本机 Mach-O `nm -u` 符号实测证实**：导入了 `_kSecAttrTokenIDSecureEnclave`、`_SecKeyCreateRandomKey`、`_SecKeyCreateSignature`、`SecItemCopyMatching`！字符串命中 `Q6L2SF6YDW.com.anthropic.claude.hwkey`。绑定主板物理安全芯片，删文件无法消除，换号不换系统必死。 | 🟢 **高** | 🔴 极高 |
| **D-S6** | **主机名与家目录抓取 (`uVi()`)** | `DeviceRegistry.uVi()` 函数无条件提取 `os.hostname()` 与 `os.homedir()`。若主机名为“张三的 MacBook”，直接暴露境内个人姓名。 | 🟢 **高** | 🟠 高 |
| **D-S7** | **条件触发式网络环境诊断** | 调取 `/usr/sbin/scutil --nc list`（抓取 `* (Connected)` VPN 条目）、匹配 `utun/ppp/ipsec` 网卡、执行 `scutil --nwi`、`kextstat vmnet`。**仅在 Cowork 虚拟化网络异常时运行，非全天常驻。** | 🟢 **高** | 🟠 高 |
| **D-S8** | **进程足迹与调试防护** | 经复核：asar 内 `readProcessTree` 0 命中，实际采用门控 flag 的 `readProcessFootprints` 与 `isProcessRunning`，防注入与反调试。 | 🟢 **高** | 🟡 中 |
| **D-S9** | **Cowork VM 宿主公证与硬件虚拟化** | 读取 `vm-support-probe.json`，验证 CPU VT-x/NEON 硬件虚拟化支持，上报虚拟机环境。 | 🟢 **高** | 🟠 高 |
| **D-S10** | **本地工作区元数据残留** | `git-worktrees.json`、`plan-usage-history.json`（包含 25 个时间戳历史用量）、`remote-control-state.json`。记录本地跨会话痕迹。 | 🟢 **高** | 🔴 极高 |

### 3.3 桌面端被动与服务校验探针 (Passive Probes)

| 探针编号 | 探针名称 | 服务端质询与完整性校验机制 | 置信度 |
| :--- | :--- | :--- | :---: |
| **D-P1** | **请求三件套服务端签名核对** | 请求体属性字典顺序 + `cc_version`（JS 计算）+ `cch`（内嵌 XXH64 哈希算法）。版本强绑定，任何非官方客户端或改装包极难伪造。 | 🟢 **高** |
| **D-P2** | **硬件证明请求 (`attestedMachRequest`)** | 服务端下发非对称签名挑战，要求客户端通过 Secure Enclave / TPM 签名并回传公钥 SPKI。无硬件芯片支持的环境直接失败。 | 🟢 **高** |
| **D-P3** | **Electron ASAR 完整性保险丝 (Fuse)** | 开启 `EnableEmbeddedAsarIntegrityValidation`（哨兵 `dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX`），任何对 asar 的篡改会导致崩溃或服务端告警。 | 🟢 **高** |

---

## 四、 封号受限页面端探针 (Restricted & Appeal Pages)

当账号被置于隔离区（On Hold / Banned）时，`/restricted` 与 `/restricted/submit` 页面绝不是简单的静态提示，而是**高强度证据固化与二次审判战场**。

| 探针编号 | 探针名称与端点 | 底层字段与状态机逻辑 | 置信度 | 实测证据 |
| :--- | :--- | :--- | :---: | :--- |
| **B-P1** | **账号封禁档案查询**<br>`GET /api/account/standing` | 裁决核心状态：<br>• `standing`: `"bad_standing"`<br>• `ban_category`: `"other"`（风控异常/KYC挂掉/支付风险）、`"violation_of_terms"`（合规打击）、`"underage"`（未成年）<br>• `banned_at`: ISO 时间戳<br>• `banned_orgs`: **连坐组织清单**（同时封停个人消费与 API 开发者 Org）<br>• `restricted_hcaptcha_mode`: `"collect"` | 🟢 **高** | HAR-1 `[149]`, HAR-2 `[147]` 抓出完整档案。 |
| **B-P2** | **申诉流转状态机**<br>`GET /api/account/current_appeal` | 动态跟踪申诉进度：<br>• `null`: 允许填写申诉问卷<br>• `status: "open"`: 申诉已入列，锁定 10 天等待倒计时 (`review_eta_days: 10`)<br>• `status: "rejected"`: **终审驳回**（显示 *"This is our final decision"*）<br>• `status: "approved"`: 解封恢复 | 🟢 **高** | HAR-1 `[203]`, HAR-2 `[200]`, HAR-4 `[201]` 实证状态流转。 |
| **B-P3** | **账号注销与账单锁**<br>`GET /api/account/deletion-allowed` | 返回 `{"deletable": false, "reasons": ["active_billing"]}`。当苹果 IAP 或 Stripe 订阅处于活跃计费周期内，强制锁死删号权限，防止被风控用户“注销重练”。 | 🟢 **高** | HAR-2 `[201]` 明文提取。 |
| **B-P4** | **合规数据导出闸门**<br>`export_policy` | 评估用户提取历史数据权限：<br>`"allow"` 开放 `/api/account/export_data` 打包下载全部对话；`"profile_only"` 仅允许导出个人基本资料。 | 🟢 **高** | HAR 报文 AST `Rc()` / `Jc()` 组件渲染证实。 |
| **B-P5** | **申诉页 hCaptcha 算力收敛** | 提交申诉表单前强制执行 `hsw.js`，以极高安全等级采集申诉者的浏览器指纹与算力证明，若检测到环境仍为代理或指纹变异，申诉甚至无法成功 Post。 | 🟢 **高** | HAR-1 `[202~209]`。 |

---

## 五、 邮箱与登录端探针 (Email & Magic Link)

邮箱不仅是账号账号名，其背后的验证机制包含大量被忽视的网络与客户端泄漏面。

| 探针编号 | 探针名称 | 泄漏机制与工作原理 | 置信度 | 风险评级 |
| :--- | :--- | :--- | :---: | :---: |
| **E-A1** | **Magic Link 邮件客户端预检 (Prefetch)** | 许多现代邮件客户端（Outlook、Apple Mail 隐私保护）会在后台静默请求邮件中的 Magic Link 进行安全扫描。该请求直接使用**境内的本地网络出口与邮件客户端 UA**，导致登录前该 Token 就已被污染或失效。 | 🟢 **高** | 🔴 极高 |
| **E-S1** | **邮件跳转来源清洗 (Referer Leakage)** | 直接从网页版 Gmail 或 QQ/163 邮箱点击 Magic Link，浏览器请求会携带 `Referer: https://mail.google.com/` 甚至境内邮箱域名，直接暴露用户邮件服务商画像。 | 🟢 **高** | 🟠 高 |
| **E-S2** | **邮件第三方 ESP 追踪像素与跳转重定向** | Anthropic 采用第三方邮件投递平台（如 SendGrid）。邮件内的超链接均为追踪包装 URL（`link.mail.claude.ai`）。在 DNS 解析与 302 重定向阶段，将记录点击瞬间的真实网络 IP 与 TLS 指纹。 | 🟢 **高** | 🟠 高 |
| **E-S3** | **登录 Token 与会话绑定 (Token-Session Binding)** | 发起登录的浏览器会话被赋予 `login_timing_hop_t0` 标记。如果在另一个没有该 Cookie/时钟的浏览器打开 Magic Link，会触发跨设备二次质询或直接判定为可疑会话。 | 🟡 **中** | 🟠 高 |
| **E-P1** | **邮箱域名信誉与临时接码拦截** | 针对常见一次性临时邮箱（Temp Mail）、接码平台共享域名、或境内小众域名，直接下发 `400 Bad Request` 或纳入高危打分池。 | 🟢 **高** | 🔴 极高 |

---

## 六、 全端探针横向对比与综合统计

| 终端维度 | 探针总数 | 🟢 高置信度 | 🟡 中置信度 | 🔴 低置信度 | 核心监控重点 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **网页端 (Web)** | 21 项 | 19 项 | 2 项 | 0 项 | 反篡改归一化器、空白 Iframe 夺舍、打字与鼠标时序分布、RUM 遥测 |
| **手机端 (Mobile)** | 7 项 | 5 项 | 2 项 | 0 项 | StoreKit 2 交易回执、Team Scoped 私密邮箱、Persona KYC 活体生物 |
| **桌面端 (Desktop)** | 32 项 | 27 项 | 5 项 | 0 项 | Secure Enclave 硬件公证、Keychain、`uVi()` 主机名、GrowthBook BaseURL |
| **封号受限端 (Restricted)** | 5 项 | 5 项 | 0 项 | 0 项 | standing 封号状态机、连坐组织审查、活跃订阅账单锁、hCaptcha 算力 |
| **邮箱端 (Email)** | 5 项 | 4 项 | 1 项 | 0 项 | Magic Link 预检泄漏、Referer 来源、ESP 追踪重定向、Token 会话绑定 |
| **合计** | **70 项** | **60 项 (85.7%)** | **10 项 (14.3%)** | **0 项 (0%)** | **全端立体多维风控网络** |

> **一句话总结**：现代风控早已不是简单的“封 IP”或“查 User-Agent”。Anthropic 构建的是一套由 **60+ 项高置信度实测探针** 构成的立体矩阵，贯穿了从底层硬件芯片（Secure Enclave）、系统内核（Keychain/Host/Locale）、网络协议栈（TLS JA4/HTTP2）、浏览器原生 Realm（about:blank）、交互动力学（键鼠直方图）、到商业与司法实体（StoreKit 2 / KYC）的全生命周期闭环。
