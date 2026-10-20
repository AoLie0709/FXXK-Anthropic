# 🔥 天下苦A÷久已！

# 🛡️ FXXK Anthropic: 全端风控探针解密、积分制机理与零篡改环境自洽终极白皮书

> **Definitive Anatomy of Anthropic / Claude Anti-Fraud Telemetry & The Environmental Consistency Architecture**  
> *基于 4 份全生命周期 HAR 网络报文（648 请求）、macOS 原生客户端 Mach-O 符号级反汇编、浏览器环境实时存储取证、及 Antigravity × Codex × DeepSeek Harness 多智能体交叉会审。*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Production Verified](https://img.shields.io/badge/Status-Production%20Verified-success.svg)]()
[![Probes Documented](https://img.shields.io/badge/Probes%20Audited-70%20Items-red.svg)]()
[![High Confidence](https://img.shields.io/badge/High%20Confidence-85.7%25-brightgreen.svg)]()

---

## 📢 开源宣言与初衷

无数合法、付费的全球 AI 开发者、科研人员和出海工程师，每天都在承受 Anthropic / Claude 毫无预警、毫无申诉容错的**机械式封号与组织连坐**。很多人尝试过购买“防关联指纹浏览器”、编写脚本 Hook 原型链、篡改 Canvas / WebGL 噪点去对抗，结果往往是**封得更快、死得更惨**。

**本项目旨在将我们数月以来对 Claude 全链路风控、遥测探针、与反作弊状态机的深度逆向成果彻底开源打包**，公之于众：
1. **扒光探针底细**：完整揭露 Claude 到底在 Web端、手机端、桌面端、封号受限端、邮箱端安装了多少令人触目惊心的探针；
2. **戳破对抗幻觉**：用真实的 AST 与解密报文证明——**为什么“写防御插件去伪造对抗”必死无疑**；
3. **建立终极认知**：阐明底层**风控积分制模型**与**全端真实环境一致性（Environmental Consistency）**的降维打击优势。

---

## 🎯 核心世界观与三大破局哲学

### 1. 风控积分制（Risk Scoring Engine）：弱信号累加与多维图谱
现代 SaaS 风控（Anthropic 自研 + Cloudflare Bot Management + Stripe Radar + Persona KYC）**绝不是单点 if-else 判定**，而是动态加权积分模型：
- **单项弱信号不致死**：偶尔的网络抖动、不常见的窗口尺寸仅扣 5~10 分，账号仍处于放行白区；
- **跨层信号冲突即绝杀**：大陆 DNS 泄漏（+20分） + 系统语言含 zh-CN 与繁中撕裂（+25分） + 复制粘贴长文本且无击键时序（+15分） + 首日暴冲充值（+20分） = **80分突破临界阈值，直接触发处决**；
- **延迟清算机制**：封号常发生在首扣款复核、异步 KYC 状态机返回或周末定时跑图批处理，让人误以为“昨天的环境伪造成功了”。

### 2. 防御悖论：为什么写防御插件去对抗反而死得更快？
- **反篡改归一化器（Anti-Tampering Normalizers）**：Anthropic 前端脚本将篡改测试结果作为显式成绩单（`is_automation: false`, `ua_client_hints: match`, `screen_equals_viewport`）直接上报服务端。伪造 UA 却无法伪造底层只读 Client Hints，当场被判 `"mismatch"`；
- **Cloudflare `jsd/oneshot` 空白 Iframe 夺舍**：Cloudflare 脚本同步创建 `about:blank` 隐藏 Iframe，在同一微秒内读取原生子 Realm 的 `o.navigator` 并立即销毁。浏览器插件根本来不及注入，直接暴露宿主真实 16GB 内存与 `zh-CN` 语言；
- **熵增悖论（Entropy Paradox）**：全球数亿真人用户的指纹高度集中在少数几个自然区间内。给浏览器加微噪、随机化硬件参数，反而让你在全球数据库中变成了**独一无二的“变异奇点”**，直接被风控算法重点标记。

### 3. 一致性绝对优于伪装度（Consistency > Spoofing）
```
┌────────────────────────────────────────────────────────────────────────┐
│                        为什么保持一致性是唯一解？                      │
├──────────────────────────────────┬─────────────────────────────────────┤
│ 路线 A：全端伪造 / 防指纹插件对抗 │ 路线 B：全端口真实环境自洽 (推荐)   │
├──────────────────────────────────┼─────────────────────────────────────┤
│ • 需在 5 大端口伪造上百个参数     │ • 0 伪造，全部保留真实物理机表现    │
│ • 复杂度：O(N^K) 指数级爆炸      │ • 复杂度：O(1) 常数级极简           │
│ • 极易产生空白 Iframe 与 JA4 撕裂│ • 与目标地区普通海外真人毫无二致     │
│ • 前端每次微调发版即刻失效暴露   │ • 零插件维护成本，稳定运行数年      │
└──────────────────────────────────┴─────────────────────────────────────┘
```
> **把 Web、手机、桌面、封号页、邮箱全部伪造成一致的假数据，在工程上是不可能的任务；  
> 但让这五个端全部原生指向同一个真实、自洽、稳定的环境，不仅简单，而且坚不可摧！**

---

## 🔍 Claude 全端 70 大风控探针全景矩阵 (按置信度分级)

> 🟢 **高置信度 (High)**：抓取到真实网络报文、本地 LevelDB/Keychain 落地存储、或经反汇编验证无条件执行；  
> 🟡 **中置信度 (Medium)**：逆向代码逻辑确证存在，但依赖条件触发或服务端为黑盒；  
> 🔴 **低置信度 (Low)**：业内常识性推断，客户端无独立计算项。

| 终端维度 | 探针编号与名称 | 监测机制与底层载荷 | 置信度 | 典型危害 / 触发场景 |
| :--- | :--- | :--- | :---: | :--- |
| **网页端** | **W-A1** 自证健康度五元组 | 上报 `is_automation` / `ua_client_hints` / `screen_equals_viewport` | 🟢 **高** | 插件伪造视口或修改 UA 当场自首 |
| **网页端** | **W-A2** 击键时序直方图 | 30 秒分桶统计 `key_nav` / `pointer_nav` / `key_paste_non_nav` | 🟢 **高** | 独立粘贴信道，无敲击直接粘贴被识别 |
| **网页端** | **W-A3** Datadog RUM 遥测 | 双通道（第一方代理 `/api/v2/rum` + 第三方直连）上报视图/错误/长任务 | 🟢 **高** | 分布式跟踪头缝合全会话行为 |
| **网页端** | **W-A5** 打字输入流动力学 | `claudeai.perf.composer_typing` 记录毫秒级打字连续流与停顿 | 🟢 **高** | 甄别脚本瞬时输入与生物人类敲击 |
| **网页端** | **W-S1** 设备持久标识符 | `anthropic-device-id`（请求头 + Cookie，跨日跨版本恒定） | 🟢 **高** | 跨账号连坐主键，单清 Cookie 无法逃逸 |
| **网页端** | **W-S5** 高熵 Client Hints | `sec-ch-ua` 平台/架构三件套（Chromium 154 / macOS / arm） | 🟢 **高** | 与 UA 强校验，伪造 Windows 瞬间露馅 |
| **网页端** | **W-S7** 压缩字典持久追踪 | `Accept: */*;dcz=keep` 并在 LocalStorage 写入 7 天有效期时间戳 | 🟢 **高** | RFC 压缩字典持久化设备粘性标识 |
| **网页端** | **W-P1** CF oneshot Iframe 夺舍 | 同步创建 `about:blank` 子 Iframe 读取原生 Realm，解密报文实锤 | 🟢 **高** | 瞬间穿透所有防指纹扩展，捕获真实语言/内存 |
| **手机端** | **M-A1** StoreKit 2 交易主键 | JWS 载荷中全局唯一递增的 `original_transaction_id` | 🟢 **高** | **致死死穴**：旧号被封，复用同一 Apple ID 秒死 |
| **手机端** | **M-A2** Persona KYC 活体生物 | `/kyc_status` 调起摄像头采集 3D 人脸、证件防伪与反光景深 | 🟢 **高** | 突变升级 Max 5x 触发，核验不通过自动秒封 |
| **手机端** | **M-S2** Apple 私密邮箱穿透 | `*@privaterelay.appleid.com` 在开发者后台 `sub` 保持固定 | 🟢 **高** | 以为换了私密邮箱是新号，实际连坐同一账户 |
| **手机端** | **M-S4** CFNetwork 协议栈 | iOS 底层原生 TLS Client Hello (JA4) 与 HTTP/2 帧序 | 🟢 **高** | 原生 Apple 协议栈特征，脚本无法伪造 |
| **手机端** | **M-S5** 蜂窝 IPv6 穿透泄露 | 蜂窝网卡分配大陆公网 IPv6，绕过部分代理直连 Cloudflare | 🟢 **高** | 手机端最大真实泄漏源，导致秒封 |
| **桌面端** | **D-S1** 安装级设备 UUID | `~/Library/Application Support/Claude/ant-did` (48B Base64) | 🟢 **高** | 桌面端设备级连坐锚点 |
| **桌面端** | **D-S4** Keychain 安全凭据面 | `Claude Safe Storage` / `Claude Key` / 会话 `.audit-key` | 🟢 **高** | macOS 钥匙串历史凭据残留导致跨会话关联 |
| **桌面端** | **D-S5** Secure Enclave 硬件公证 | `nm -u` 证实导入 `_kSecAttrTokenIDSecureEnclave` 与 `hwkey` | 🟢 **高** | 绑定物理主板安全芯片，普通删文件无法抹除 |
| **桌面端** | **D-S6** 主机名与家目录抓取 | `DeviceRegistry.uVi()` 读取 `ComputerName` 与 `os.homedir()` | 🟢 **高** | “张三的 MacBook Pro”直接暴露境内真实姓名 |
| **桌面端** | **D-A2** GrowthBook BaseURL 上报| `remoteEval` 请求体明文上传 `apiBaseUrlHost` 属性 | 🟢 **高** | 自建反代 BaseURL 被明文上报捕获 |
| **桌面端** | **D-P1** 桌面请求三件套校验 | 请求体字典序 + `cc_version` + Bun 内嵌 XXH64 `cch` 算法 | 🟢 **高** | 改装客户端或第三方 Harness 极难复现 |
| **封号页面**| **B-P1** 账号封禁档案查询 | `GET /api/account/standing` 下发 `ban_category: "other"` | 🟢 **高** | 同时连坐 Consumer 个人与 API 开发者组织 |
| **封号页面**| **B-P2** 申诉状态机终态驳回 | `GET /api/account/current_appeal` 切入 `status: "rejected"` | 🟢 **高** | 历经 18 小时终审驳回，页面锁定最后决定文案 |
| **封号页面**| **B-P3** 活跃计费账单锁 | `GET /api/account/deletion-allowed` 返回 `active_billing` | 🟢 **高** | 苹果 IAP 活跃期内强制锁死删号权限，防注销重练 |
| **封号页面**| **B-P5** 申诉页 hCaptcha 算力 | 下发 `hsw.js` (1.49MB WASM) 执行高安全等级 PoW 算力证明 | 🟢 **高** | 申诉前再次采集环境指纹，变异指纹无法提交 |
| **邮箱端** | **E-A1** 邮件客户端后台预检 | 国内邮件 App 自动爬虫预抓取 Magic Link 导致境内 IP 泄露 | 🟢 **高** | 登录链接在点击前已被大陆机房 IP 污染失效 |
| **邮箱端** | **E-S1** 邮件跳转 Referer 泄露| 从网页邮箱直接点击链接，附带 `Referer: mail.qq.com` | 🟢 **高** | 明确暴露邮件来源服务商地域 |
| **邮箱端** | **E-S2** 邮件服务商追踪重定向 | SendGrid 包装跳转域名与内嵌 1×1 追踪像素 | 🟢 **高** | 点击瞬间记录真实网络出口与 TLS 指纹 |

> 📚 查阅完整 70 项探针的底层代码、AST 函数名与参数字典：👉 [docs/01_CLAUDE_PROBE_CATALOG_MATRIX.md](docs/01_CLAUDE_PROBE_CATALOG_MATRIX.md)

---

## 🔬 本机 Chrome 专用隔离 Profile 实时遥测取证物证

在用户当前的 Google Chrome `专用隔离 Profile`（专用隔离 Profile）中，我们对正在运行的 Claude 标签页进行了全量数字取证：

1. **`antalytics_queue_v1` 实时缓冲队列提取**：
   - 本地 LevelDB 中实测截获 11 个待上传或周期性事件；
   - 提取到完整 JSON：`interaction_histogram`（版本 3，六信道按键分布）、`composer_typing`（流式键入停顿）、`conversation-revisits-device`（设备级会话重访计数）；
   - **【独家重磅发现】中文拼音输入法 (IME) 专属时延探针**：在 `composer_typing` 中实测捕获 `composition_keydown_count: 24`, `composition_observed_count: 23`, `composition_worst_duration_ms: 48`！Claude 正在毫秒级监测你的中文拼音选词框停顿，以此判定是真人打字还是剪贴板脚本灌入！
2. **压缩字典追踪戳 (`dcz_keep`) 固化**：
   - 键名：`persisted.dcz_keep` $\rightarrow$ 值为 `1:1793093826240`（有效期精确续期至 7 天后）；
3. **毫秒级活跃度时钟 (`LSS-cardinal-daily-visible-ms`)**：
   - 实时自增至 **`2,096,894` ms（约 34.95 分钟）** 前台真实肉眼可视停留；
4. **活跃 Cookies 凭据库与 100% 物理隔离**：
   - 包含 23 条存活 Cookie：`_dd_s_v2`（Datadog RUM）、`anthropic-device-id`、`__stripe_mid`（Stripe 欺诈识别）、`intercom-device-id`、`cf_clearance`；
   - **凭据隔离核实**：专用隔离 Profile 的 `anthropic-device-id` 为 `aaaaaaaa-...`，与历史封禁号 `33333333-4444-5555-6666-777777777777` 100% 物理级断开，未发生跨账号串号污染。

> 🔬 查阅完整浏览器本地取证代码与 SSTable 解析报告：👉 [docs/03_BROWSER_LIVE_FORENSICS_REPORT.md](docs/03_BROWSER_LIVE_FORENSICS_REPORT.md)

---

## 🤖 多智能体交叉会审与重大流言纠偏

由 Antigravity、Codex 与 DeepSeek Harness 共同完成的交叉会审，彻底推翻了前序调查与社区中的 **八大流言误传**：

1. ❌ **误传：桌面端包含 `readProcessTree` 常驻系统监控**  
   ✅ **真实现状**：asar 内命中为 0！实为门控 flag 的 `readProcessFootprints`，仅用于 Computer Use 桌面自动化时的内存防护，非直接封号探针；
2. ❌ **误传：桌面端全天候常驻监控宿主机 VPN**  
   ✅ **真实现状**：`[networkDiagnostics]` 模块仅在 Cowork 本地虚拟化 VM 启动超时时条件触发，非常驻嗅探；
3. ❌ **误传：修改 `ANTHROPIC_BASE_URL` 即可绕过遥测**  
   ✅ **真实现状**：BaseURL 属性作为 `apiBaseUrlHost` 明文上传 GrowthBook，自建反代反而自曝；
4. ❌ **纠偏：此前关于“无 Secure Enclave 硬件调用”的裁定被推翻**  
   ✅ **真实现状**：Mach-O `nm -u` 明确命中 `_kSecAttrTokenIDSecureEnclave` 与 `hwkey`，硬件安全芯片公证真实存在；
5. ❌ **误传：拔手机 SIM 卡可防封**  
   ✅ **真实现状**：iOS 16+ 已废弃读取 IMSI/ICCID 权限，手机端最大泄漏源是**蜂窝 IPv6 穿透**，关闭 IPv6 即可。

> 🤖 查阅完整三方智能体对质台账与修正清单：👉 [docs/04_MULTI_AGENT_CONSENSUS_AUDIT.md](docs/04_MULTI_AGENT_CONSENSUS_AUDIT.md)

---

## 🛠️ 全端零伪装自洽部署与换号重生 SOP

想要彻底远离封禁，必须将 **OS 宿主、网络传输、身份凭据、支付沙盒、客户端应用** 5 个端口全部收敛至同一个稳定实体（推荐：**台湾中华电信 HiNet 静态住宅** 画像，UTC+8 时区与北京时间 0 时差）：

### 1. 宿主系统基线校准（免改全局中文）
```bash
# 1. 主机名去特征化 (防御 uVi() 探针)
sudo scutil --set ComputerName "macbook-air"
sudo scutil --set HostName "macbook-air"
sudo scutil --set LocalHostName "macbook-air"

# 2. 桌面端单应用语言锁定为美式英文 (Cocoa App-level override，系统全局仍为中文)
defaults write com.anthropic.claudefordesktop AppleLanguages '("en-US", "en")'
defaults write com.anthropic.claudefordesktop AppleLocale "en_US"
```

### 2. 网络与 DNS 防泄露对齐
```bash
# 1. 绑定国际安全加密解析器 (彻底剔除 114 / 运营商泄露)
sudo networksetup -setdnsservers "Wi-Fi" 1.1.1.1 8.8.8.8

# 2. 物理关闭 IPv6 (防御蜂窝与公网 IPv6 穿透 Cloudflare)
sudo networksetup -setv6off "Wi-Fi"
```

### 3. 官方受支持的“遥测清零”配置
无需安装任何注入扩展，通过官方支持的配置文件合法关闭：  
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

### 4. 换号重生：五件套一次性物理重置
账号一旦被封，必须一次性完成以下五件套重置：
1. **删除设备 ID**：`~/Library/Application Support/Claude/ant-did` 与 `ant-device-registry.json`；
2. **清除 CLI 机器码**：`~/.claude/.claude.json`；
3. **清空钥匙串**：macOS 钥匙串中删除 `Claude Safe Storage`、`Claude Key`、`Claude Code-credentials` 与 `.audit-key`；
4. **新建干净浏览器 Profile**：新 Chrome Profile 保持 **0 第三方插件**，专号专用；
5. **废弃旧 Apple ID**：旧 Apple ID 因 `original_transaction_id` 已入黑图谱，必须使用全新境外 Apple ID + 正品 Gift Card。

> 💡 **终极优雅解**：在 macOS【系统设置】中**新建一个独立的标准用户（如 `WorkTW`）**。Keychain、Secure Enclave 上下文、沙盒与 Chrome 配置一次性物理级彻底重置，历史风险 100% 物理阻断！

> 🛠️ 查阅完整保姆级实操交接手册：👉 [docs/05_SURVIVAL_SOP_AND_DEPLOYMENT.md](docs/05_SURVIVAL_SOP_AND_DEPLOYMENT.md)

---

## 📂 项目知识库完整索引

```
FXXK CLAUDE/
├── README.md                                    # 🏛️ 项目终极总览与 GitHub 开源首页 (本文件)
├── CHANGELOG.md                                 # 📝 项目与环境变更记录
├── docs/                                        # 📚 核心体系知识库
│   ├── 01_CLAUDE_PROBE_CATALOG_MATRIX.md        # 🕵️‍♂️ 全端 70 大风控探针全量字典与置信度大典
│   ├── 02_RISK_SCORING_AND_CONSISTENCY_PHILOSOPHY.md # ⚖️ 风控积分制机理与真实自洽破局哲学
│   ├── 03_BROWSER_LIVE_FORENSICS_REPORT.md       # 🔬 浏览器环境实时遥测深度取证报告
│   ├── 04_MULTI_AGENT_CONSENSUS_AUDIT.md        # 🤖 三智能体 (Antigravity/Codex/DSH) 会审与纠偏
│   ├── 05_SURVIVAL_SOP_AND_DEPLOYMENT.md        # 🛠️ 全端防封部署与换号重生保姆级手册
│   ├── 00_PRINCIPLES.md                         # 🧭 五层防御世界观与核心原则
│   └── CLAUDE_MULTI_DEVICE_SETUP_HANDOVER.md    # 💻 多设备标准化部署交接白皮书
├── output/                                      # 📊 原始取证数据与最终会审报告
│   ├── claude_full_endpoint_probe_matrix_20261020.md # 500+ 行司法级全景矩阵交付原件
│   ├── 全探针清单与环境一致性最优解_2026-10-20.md  # 网页与桌面探针基线清单
│   ├── har_probe_audit.md                       # HAR 网络遥测取证报告 (21 项网页探针全表)
│   ├── github_rea_audit.md                      # GitHub REA 桌面端逆向报告 (32 项桌面探针)
│   └── final-report/                            # 各 AI 最终报告归档 (antigravity / codex / dsh)
└── tools/                                       # 🧰 自动化检测与环境体检脚本
    └── scripts/                                 # 痕迹审计、网络检查、隔离启动脚本
```

---

## 🤝 贡献与开源倡议

本白皮书所有数据、结论均经得起十六进制字节级复核。欢迎全球开发者提交 Issue 与 PR，共同补充逆向样本、修正风控演进模型，让更多人免受暗箱封号之苦。

**如果你觉得这份知识库对你有帮助，请给本项目点一个 ⭐️ Star 并分享给身边的出海与 AI 开发者！**
