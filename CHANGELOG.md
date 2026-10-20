# CHANGELOG

记录项目结构、方案与运行环境的变更。格式：日期 · 类型（结构 / 方案 / 环境 / 工具 / 研究）· 内容。

## 2026-10-20

- **研究/修正**：新增 [diagnostics/agents/deepseek/deepseek_report_v2_addendum_2026-10-20.md](diagnostics/agents/deepseek/deepseek_report_v2_addendum_2026-10-20.md)。撤回 v1「新建 macOS 用户」默认步骤，改回项目既有 `--purge-risks` + 卸载重装路线；补入 hwkey 位于 data-protection keychain、CLI 不可见、原生模块无删除接口的证据；补入 Shield 三处自曝、桌面端语言定向伪装、客户端 RTT/TLS 实测。
- **方案**：桌面端语言改为 per-app 定向覆盖（`config.json` `locale` + `com.anthropic.claudefordesktop` 的 `AppleLanguages`/`AppleLocale`），不动系统设置；新增 `tools/scripts/desktop_locale_spoof.sh`（可回滚）。
- **工具**：新增 `tools/scripts/launch_isolated_chrome_tw.sh`（零扩展）、`tools/scripts/persona_tw_verify.sh`（只读体检）、`tools/scripts/persona_tw_apply.sh`（默认 dry-run）、`tools/shield-lite/`（无内容脚本、无头改写）。
- **环境（待处理）**：实测系统代理 HTTP/HTTPS/SOCKS 均为 `127.0.0.1:7897`（ON），与 `playbooks/CURRENT_SETUP.md` 的"系统代理保持 OFF、仅 TUN"不一致；已记录，未擅自改动。

## 2026-10-19

- **研究**：完成「网页端 × 桌面端封号探针」防御性逆向，产出 [research/notes/2026-10-19_claude-web-desktop_probe-reverse.md](research/notes/2026-10-19_claude-web-desktop_probe-reverse.md)。三份 HAR + 本机 `app.asar` 静态逆向（REA）双向取证。核心结论：网页端最激进探针为 hCaptcha Client Attestation（token 内嵌 `visibility/focus/mintWaitMs/challengeShown/account_switched`）与 `HealthMetricEvent` 反伪造字段组（`ua_client_hints`、`screen_equals_viewport`、`is_automation`、`ua_form`）；桌面端 `ant-did` 为安装级 UUIDv4（与登录无关），经 `_cross_domain_anonymous_id` 与网页端跨端关联；**"改指纹"在该平台是负收益**，防御最优解是环境自洽 + 少动。
- **工具**：新增 `tools/scripts/audit_har_probes.py`（HAR 探针取证，源只读、输出脱敏）、`tools/scripts/extract_asar_readonly.py`（零依赖 asar 解包，兼容非标准 16 字节头）、`tools/scripts/scan_desktop_probes.py`（桌面端探针关键词全量扫描）。
- **环境**：REA（`rea-agents@6.7.0`）以 `--prefix scratch/rea-toolchain` 隔离安装，未写全局 npm、未动 `~/.npmrc`、未执行 `rea setup`；对 `app.asar` 副本执行 `analyze-javascript-application`，产出 218 MB Evidence（430 JS / 7.3M AST / 0 解析失败 / 0 完整性矛盾 / 1531 IPC 操作）。`/Applications/Claude.app` 全程未被修改。

- **研究（第二轮·四类探针全覆盖）**：从 HAR 提取并下载 **178 个前端 bundle（20.6 MB）**做静态逆向，补齐此前缺失的**静默探针**与**防御性探针**两类。关键产出：(a) 逆向出平台真实的自动化判定链 —— `tY()`（UA 形态 6 态）、`PM()`（UA 与 Client Hints 一致性）、`q1()`（视口恒等）、`hz()`（`ua_bot`/`ua_headless`/`webdriver` 三态）、`hidden_at_load`（`visibilityState` + `activationStart`）、平台串白名单 `kD`（macOS 只认 `10_15_7`）；(b) 证明**平台不自研重度浏览器指纹**（WebGL/Audio/Canvas/字体枚举全零命中），且**无任何第三方指纹 SDK**；(c) 定位视口健康分级（`too_small`/`below_target`/`ok`）与 `userAgentData` 高熵值采集。
- **工具**：新增 `tools/scripts/scan_web_probes.py`（四类探针全量扫描器）与 `tools/web/consistency-audit.html`（**本机环境一致性体检工具**，逆向移植平台判定逻辑，已在 headless Chrome 验证可正确识别 `ua_headless`）。
- **结论修订**：确认"改指纹/装伪造扩展"在该平台是**负收益** —— 平台未采集的项改了没用，改动本身却会触发 `ua_client_hints: mismatch` / `unreduced_version` / `unreduced_platform`。

## 2026-10-10

- **网络/方案**：全面迁移至 Clash Verge TUN 虚拟网卡全局接管；沉淀 `update_subscription.py` 与 `update_and_inject_clash_rules.sh` 自动化 AES 解密与防封分流注入管线；引入 `lazy: true` 粘性持久连接根除 Cloudflare Turnstile IP-Mismatch 验证抖动死循环。
- **高可用/容灾**：升级 `🇹🇼 Claude专属` 策略组为四级梯队防御架构（主力 3 号、同出口 AnyTLS/VLESS 零跳变兜底、同 C 段 4/6/2 号极速热备），彻底消除单点断网顾虑。
- **分流修正**：纠正对 Apple 域名的生硬全局 DIRECT 策略，完整继承订阅原生成熟分流（国内 CDN/固件与 iCloud 直连跑满千兆带宽，海外专属生态自然走节点代理）。
- **文档**：更新 `playbooks/CURRENT_SETUP.md` 反映 2026-10-10 最新落地状态。

## 2026-10-07

- **网络/工具**：升级 `apply_singbox_rules.py`，新增局域网组播（224.0.0.0/4、ff00::/8）与 mDNS（5353）放行逻辑，解决 macOS 与 iOS 跨设备剪贴板、隔空投送与接力（Handoff）受阻问题；不触碰任何公网代理与 Claude 规则。
- **环境/守护**：构建 sing-box 启动拦截守护层（`sing-box` wrapper -> `sing-box-core`），并在 `guiNConfig.json` 固化局域网排除网段；彻底解决 v2rayN 订阅更新、切换节点或重启服务时冲掉 Claude AAAA 拦截规则的隐患，实现开机与运行中 100% 永久自愈生效。

## 2026-10-06


- **结构**：重组目录为 `docs/`（原则）、`playbooks/`（方案）、`research/`（研究）、`tools/`（工具）、`output/`（产出）、`scratch/`（临时）。
- **结构**：原 `docs/01、02、04` 专题文档迁入 `research/notes/`；原 `docs/03` 迁为 `tools/extension/ARCHITECTURE.md`；原 `docs/05` 迁为 `research/intel/tavily_intel_report.md`。
- **结构**：`extension/`、`scripts/`、`configs/`、`templates/` 并入 `tools/`；`logs/` 改为 `output/`。
- **研究**：重写 `docs/` 为方向性原则文档（00–06），新增行为与运维、研究路线两篇。
- **工具**：所有脚本改为基于自身位置推导项目根目录，去除硬编码绝对路径。
- **方案**：确立当前方案（台湾 HiNet 住宅出口 + sing-box 定向 IPv6 屏蔽 + 隔离 Chrome + Claude Shield + 专用 Gmail + 应用内购），见 `playbooks/CURRENT_SETUP.md`。
- **环境**：出口检测通过（AS3462 / 家庭宽带 / 风险 0 / WebRTC 无泄漏）。
- **工具**：新增 `audit_claude_traces.py` 全链路痕迹审计脚本；破解终端 ANTHROPIC 环境变量来自 CC Switch 进程的注入源头；同步沉淀全局 Agent 技能 `claude-trace-auditor`。
