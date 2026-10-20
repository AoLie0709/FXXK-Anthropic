# 🤖 Antigravity × Codex × DeepSeek Harness (DSH) 多智能体交叉会审报告

> **编制**：三方会审专家委员会（Antigravity Lead Orchestrator, Codex Peer Reviewer, DeepSeek Harness Forensic Agent）  
> **数据源**：
> - `output/final-report/antigravity/antigravity-final-report.md`
> - `output/final-report/codex/codex-final-report.md`
> - `output/final-report/dsh/dsh-final-report.md`
> - `output/claude_full_endpoint_probe_matrix_20261020.md`
> - `output/reviews/peer-review-antigravity-codex.md`

---

## 一、 会审总决议：核心共识 (Consensus)

1. **绝对排斥“伪装路线”，全面倒向“真实自洽路线”**：
   - 三方智能体一致认定：**在现代反欺诈系统面前，安装防关联指纹插件、伪造 Canvas 噪点、篡改 User-Agent 是导致被封的最快途径。**
   - 客户端部署的“反篡改归一化器（Anti-Tampering Normalizers）”会将伪造检测结果（如 `screen_equals_viewport: false`, `ua_client_hints: match`）作为显式成绩单上报，伪造行为当场自曝。
2. **多终端多维图谱连坐（Graph Association）是封禁主因**：
   - 封号往往并非单一技术参数触发，而是**多端信号冲突**（如：macOS 存在 zh-CN 语言残留 + 代理走台湾节点 + Apple ID 曾用国内 Hide My Email + StoreKit 2 交易回执被标记）在后端积分制模型中突破临界值。
3. **StoreKit 2 底层交易主键不可逆**：
   - 一旦某个 Apple ID 在旧账号被封期间产生过订阅关联，其 `originalTransactionId` 永久进入 Anthropic 风险数据库。使用同一 Apple ID 购买新账号必定被连坐秒封。

---

## 二、 八大重大认知纠偏台账 (Disagreements & Corrections)

在本次三方会审前，社区和前序调查中流传着若干严重误导用户的“流言与都市传说”。三方智能体通过字节级二进制反汇编和源码审计，完成以下权威纠偏：

| # | 历史误传 / 社区流言 | 符号级 / 源码级事实核查 | 终审定论与影响 |
| :-: | :--- | :--- | :--- |
| **01** | **误传：桌面端包含 `readProcessTree` 全系统进程监控** | 对 `app.asar` 与原生模块执行全文 grep 与符号检查：**`readProcessTree` 命中为 0**！实际代码为门控 flag 的 `readProcessFootprints` 与 `isProcessRunning`。 | 纠偏：进程检测仅用于 Computer Use 桌面自动化时的内存保护与 IDE 联动，**不是常驻后门封号探针**。 |
| **02** | **误传：桌面端全天候常驻监控宿主机 VPN 与网络状态** | 逆向 `[networkDiagnostics]` 模块：确实存在 `/usr/sbin/scutil --nc list` 与 `utun` 扫描，但**仅在本地 Cowork VM 启动超时或无网络时条件触发**。 | 纠偏：正常使用时不执行网络嗅探，不必恐慌。 |
| **03** | **流言：修改 `ANTHROPIC_BASE_URL` 即可绕过官方遥测** | 逆向 GrowthBook 特性求值模块：客户端请求体携带 `apiBaseUrlHost` 属性；`event_logging` 硬编码 `api.anthropic.com`。 | 纠偏：自定义反代 BaseURL 不仅无法关闭遥测，反而会将代理主机域名作为特征明文上报。 |
| **04** | **纠偏：此前裁定“桌面端没有调用 Secure Enclave”被推翻** | 对 `claude-native-binding.node` 执行 `nm -u` 符号检查，确证导入了 `_kSecAttrTokenIDSecureEnclave`、`_SecKeyCreateRandomKey`、`_SecKeyCreateSignature`；命中 `Q6L2SF6YDW.com.anthropic.claude.hwkey`。 | **关键纠偏**：Secure Enclave 硬件公证真实存在！单纯删除本地配置文件无法消除 Enclave 硬件签名，换号不换系统沙盒存在硬件穿透风险。 |
| **05** | **误传：Statsig 仍是主要特性开关引擎** | CLI 2.1.241 与最新 Desktop 代码证实：Statsig 接口调用已为 0，全面切换为 **GrowthBook**（魔数 `CLF\x02` + gzip 缓存）。 | 纠偏：更新特性开关认知，避免针对不存在的 Statsig 端点做规则。 |
| **06** | **误传：客户端读取主板硬件序列号（IOPlatformSerialNumber）** | 对所有动态库与 asar 进行 IOKit 符号调用检查：**0 命中**。 | 纠偏：Anthropic 完全不读取 Mac 主板序列号，“修改电脑主板序列号防封”纯属黑产营销骗局。 |
| **07** | **误传：拔出手机物理 SIM 卡是防止风控的必备步骤** | iOS 16.0 起苹果官方已废弃 `CoreTelephony` 获取 IMSI/ICCID 的权限，沙盒应用调用统一返回 `nil`。 | 纠偏：手机端主要泄漏点是**蜂窝 IPv6 穿透**，只需在代理中禁用 IPv6，完全无需物理拔卡。 |
| **08** | **真相确认：官方受支持的“遥测全关闭”路径真实存在** | 官方白皮书与 asar 源码确认：在 `claude_desktop_config.json` 中配置 `disableNonessentialTelemetry: true` 等 6 项开关，可合规阻断除核心推理外的全部上报。 | 纠偏：不要用第三方工具 Hook，走官方支持的合法通道关闭。 |

---

## 三、 三方智能体执行路径建议

1. **Antigravity 团队**：负责全链路架构设计、Keychain 与 Enclave 硬件沙盒隔离、以及多设备标准化 SOP 编制；
2. **Codex 团队**：负责对每一次逆向结论进行证据分级（E1 实物、E2 代码、E3 规范、E4 推导），坚决收回无证据的激进推论；
3. **DeepSeek Harness (DSH) 团队**：负责 HAR 流量字节级解码、SSTable/WAL 本地取证、以及跨平台协议一致性对账。
