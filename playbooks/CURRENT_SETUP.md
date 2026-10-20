# 当前落地方案（Playbook）

> 这是**截至 2026-10-10 的具体实施方案**，已从旧版 v2rayN 全面迁移至 **Clash Verge TUN 虚拟网卡全局接管**。
> 节点、工具、渠道都可能变化——变化时更新本文件并在 [CHANGELOG.md](../CHANGELOG.md) 记录，原则文档无需改动。

---

## 方案概览

| 层 | 当前做法 | 对应原则 |
| :--- | :--- | :--- |
| 网络 | 台湾中华电信 HiNet（AS3462）住宅出口；**Clash Verge TUN 虚拟网卡全局接管**（系统代理保持关闭，杜绝断网与端口冲突）；策略组启用 **`lazy: true` 粘性持久连接**；全链路拦截 UDP 443 (QUIC) 与 WebRTC STUN (3478/5349)；遥测域名 REJECT；继承原生分流兼顾 Apple 境内 CDN 满速与海外代理 | 住宅出口、同时区减少伪装、Turnstile 防抖动、精准封堵泄漏、生态分流 |
| 浏览器 | 独立 user-data-dir 的隔离 Chrome，不登录任何个人账号；仅加载自研 Claude Shield 扩展 | 隔离 > 清理、少改 > 多改 |
| 身份 | 专用 Gmail（iOS 系统设置通道创建）或 Apple Privacy 隐藏邮箱（`@privaterelay.appleid.com`），Google SSO 登录 | 专号专用、来源自然、高信誉背书 |
| 支付 | 应用商店内购（美区 Apple ID 余额 + 礼品卡兑换）订阅，不在网页端直绑卡 | 减少金融信息暴露、零拒付封号风险 |
| 行为 | 与本地同时区，作息天然一致 | 作息自洽 |

---

## 执行步骤

### 1. 网络与订阅管线
```bash
# 一键解密拉取最新订阅并注入定制防封规则（lazy: true 粘性连接、遥测 REJECT、STUN/QUIC 阻断）
python3 tools/scripts/update_subscription.py
# 或使用快捷脚本
tools/scripts/update_and_inject_clash_rules.sh

# 出口质量审计（结果写入 output/audits/）
tools/scripts/check_node_purity.sh
```

**Clash Verge 设置关键核对**：
- **TUN 模式 (Tun Mode)**：保持 **开启 (ON)**。
- **系统代理 (System Proxy)**：保持 **关闭 (OFF)**！（TUN 模式接管虚拟网卡，不开系统代理就永远不会端口冲突或断网）。
- **节点选择**：自动锁定 **`🇹🇼 Claude专属`**（台湾 HiNet 住宅固定节点，启用 `lazy: true`）。
- **Apple 业务**：遵循订阅原生成熟分流（国内 CDN/固件与 iCloud 直连跑满千兆带宽，海外专属生态平滑走节点代理）。

### 2. 浏览器
```bash
tools/scripts/launch_isolated_chrome.sh
```
扩展路径：`tools/extension/`。

### 3. 身份与支付
详细操作见专题笔记：[iOS 通道 Gmail 与 Apple IAP](../research/notes/2026-10-06_identity_ios-gmail_and_apple-iap.md)。

### 4. 每次使用前环境核查
```bash
tools/scripts/verify_environment.sh
```

---

## 当前状态（2026-10-10）

- 出口检测：AS3462 Chunghwa Telecom（台湾中华电信住宅 IP），识别为家庭宽带，未命中代理库，风险评分 0，WebRTC 未泄漏，时区 `Asia/Taipei`（UTC+8）与本地系统时区 100% 重合。
- 防抖动保障：`🇹🇼 Claude专属` 策略组锁定存活 HiNet 节点并启用 `lazy: true`，彻底根除 Cloudflare Turnstile IP-Mismatch 验证死循环报错。
- 分流策略：
  - 核心 Claude/Anthropic/Stripe 流量强行锁定台湾住宅出口。
  - 遥测埋点（statsig, datadoghq, sentry 等）内核层 REJECT。
  - Apple 固件更新与 App Store CDN 继承原生直连，海外业务正常走代理。
