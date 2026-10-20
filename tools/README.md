# tools · 工具索引

所有脚本都基于自身位置推导项目根目录，可在任意目录下调用。产出统一写入 `output/`。

## scripts/

| 脚本 | 层 | 作用 | 产出 |
| :--- | :--- | :--- | :--- |
| `migrate_claude_sessions.py [--auto\|--list\|--target-account\|--rollback]` | 会话资产 | 跨账号会话热重绑与无损迁移（支持旧邮箱清洗、O(1)索引、工作区同步与一键无损回滚） | 迁移至目标账号目录 + 物理快照 + manifest |
| `claude_network_guard.py [--diagnose\|--generate-rules]` | 网络防封 | 宿主网卡/VPN接口/bootpd体检，自动生成 Clash/Surge/Sing-box 规避配置 | 终端报告 / `tools/configs/` |
| `export_and_sanitize_claude_chats.py` | 资产归档 | 离线纯净化提取 Cowork/CLI 对话与 Side Notes，导出脱敏 Markdown | `~/Documents/Claude_Archive_Safe/` |
| `audit_claude_traces.py [--json\|--markdown]` | 系统/环境 | 深度扫描 Claude 本地残留、环境变量脱敏、浏览器 IndexedDB、CC Switch 状态 | 终端输出 / `output/audits/` |
| `verify_environment.sh` | 综合 | 代理进程、出口、时区一致性、IPv6/WebRTC 风险的综合体检 | 终端输出 |
| `tavily_intel_gatherer.py` | 研究 | 多 Key 轮询的 Tavily 情报采集 | `output/intel/*.json` + `research/intel/tavily_intel_report.md` |
| `audit_har_probes.py [har...]` | 取证 | 解析 claude.ai HAR：端点、身份请求头、遥测事件、账号状态、跨文件 ID 一致性（源只读、输出脱敏） | `output/har_analysis/` |
| `extract_asar_readonly.py <asar> <out_dir>` | 取证 | 零依赖只读解析 Electron `app.asar`（兼容标准 12 字节与非标准 16 字节 JSON 头），不写回源 | 指定输出目录 |
| `scan_desktop_probes.py <extracted_dir> [out_dir]` | 取证 | 桌面端解包目录的探针关键词全量扫描：身份 / 遥测 / 反伪造 / 权限 / 文件边界 | `output/desktop_analysis/` |
| `scan_web_probes.py <dir> [out_json]` | 取证 | 四类探针全量扫描：**S** 静默采集 / **D** 防御反篡改 / **A** 攻击挑战 / **T** 遥测上报、**B** 行为；适用于前端 bundle 与桌面端解包目录 | `output/web_analysis/` |

## web/

| 文件 | 说明 |
| :--- | :--- |
| `consistency-audit.html` | **环境一致性体检工具**。单文件、纯本地、不写 Cookie、不上传数据。判定引擎逆向移植自 claude.ai 前端（`tY`/`PM`/`q1`/`hz`/`hidden_at_load`），输出六项核心判定 + 全部静默采集字段 + 出口时区语言三方一致性矩阵。双击用 Chrome 打开即可。 |

## configs/

| 文件 | 说明 |
| :--- | :--- |
| `singbox_sample_config.json` | sing-box 完整示例配置 |
| `singbox_claude_dns_rules.json` | 可合并的 DNS 定向规则片段 |

## extension/

Claude Shield（MV3）浏览器扩展。使用说明见 [extension/README.md](extension/README.md)，实现原理见 [extension/ARCHITECTURE.md](extension/ARCHITECTURE.md)。

## 新增工具的流程

1. 在 `scratch/` 中开发和验证；
2. 确认长期有用后移入 `tools/` 对应子目录；
3. 用 `PROJECT_ROOT` 相对路径，不硬编码绝对路径；产出写入 `output/`；
4. 在本文件登记，并在 `CHANGELOG.md` 记录。
