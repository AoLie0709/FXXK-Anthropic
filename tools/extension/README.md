# Claude 隐私护盾 (Claude Shield v1.2.1 Stealth Edition)

专为 **Claude.ai** 打造的智能防关联、防指纹、防泄漏与环境热对齐 Chrome 扩展（Manifest V3 架构）。支持**自动识别当前 VPN 节点出口 IP** 并毫秒级动态对齐时区与语言；配合 sing-box DNS 规则实现**仅针对 Claude/Anthropic 屏蔽 IPv6**（无需全局关闭系统 IPv6），实现极高稳定性的安全访问。

---

## 🌟 核心特性与深度加固

### 1. ⚡ 全自动识别当前 VPN 节点
- **多级冗余探测引擎**：三级冗余（ipwho.is -> freeipapi.com -> 1.1.1.1/cloudflare CDN-cgi trace），毫秒级探测出口公网 IP、归属国、城市、ASN。
- **环境毫秒级热对齐**：根据节点出口位置自动适配 IANA 标准时区与语言列表，热广播至正在运行的 Claude 标签页。
- **动态 Airport Colo 映射**：针对 Cloudflare 边缘节点（如 SJC/LAX 美西、ORD 美中、IAD/JFK 美东等）精准映射到真实经度时区，消除静态全美默认 New York 的偏差。

### 2. 🎯 精准定向 IPv6 阻断（系统全局 IPv6 完整保留）
- **系统 IPv6 完整保留**：macOS 系统网络（Wi-Fi / 以太网）维持 `Automatic` 状态，不影响国内高校、PT 下载、NAS 与国内直连应用。
- **sing-box DNS AAAA 精准拦截**：针对 `claude.ai`、`anthropic.com`、`claudeusercontent.com`、`anthropic.ai`、`claudecdn.com`、`challenges.cloudflare.com` 的 AAAA (IPv6) 解析返回 `predefined NOERROR`（NODATA 空应答），系统无缝秒级回退至 IPv4 代理，杜绝国内宽带 IPv6 泄漏。
- **sing-box 路由层兜底**：上述域名如果产生 IPv6 流量，直接由 sing-box 路由层 `reject` 拦截。
- **WebRTC 双重阻断**：启用 Chrome 底层 `disable_non_proxied_udp` 隐私策略，并于注入层深度清洗 SDP 与 ICE 候选中的私网 IPv4、全量 IPv6（包括 `::` 压缩格式）以及 Host 候选，杜绝 STUN 探针外泄。

### 3. 🛡️ 原生级函数防检测伪装 (Anti-Tamper & Native Function Cloaking)
- **`[native code]` 原生签名保持**：通过底层 `Function.prototype.toString` 闭包弱引用映射，所有被拦截或篡改的原生方法（`Date.prototype.getTimezoneOffset`、`Intl.DateTimeFormat`、`CanvasRenderingContext2D.prototype.getImageData` 等）在受到 Cloudflare Turnstile / CreepJS / BotD 扫描时，均严格返回规范的原生方法体 `function <name>() { [native code] }`，杜绝篡改检测。
- **完整 Date & Intl 原生引擎**：全面接管 `getFullYear`、`getMonth`、`getDate`、`getDay`、`getHours`、`getMinutes`、`getSeconds`、`getTimezoneOffset`、`toString`、`toDateString`、`toTimeString`；对 `new Date(NaN)` 等非法输入严格返回 `NaN` 与 `Invalid Date`（符合 ECMAScript 规范）；构造 `Intl.DateTimeFormat` 时保留调用方显式指定的 `timeZone: 'UTC'` 等参数。
- **原型链层级 Navigator 隔离**：将 `language`、`languages`、`platform`、`webdriver` 属性定义于 `Navigator.prototype` 上，确保 `navigator.hasOwnProperty('language')` 恒为 `false`，彻底修复因实例属性泄漏被识别的特征。
- **存储零污染与 WebIDL 纯净性 (Pure In-Memory Cloaking)**：清除所有旧版本留存的明文探测缓存键，完全杜绝在目标域名 `localStorage` 中持久化扩展数据，完全不触碰 `Storage.prototype` 原生原型，保留 100% 原生 WebIDL 完整性，防范 Turnstile 针对修改内置原型的特征审计。

### 4. 🎨 无递归安全画布微噪与硬件隐蔽
- **栈溢出保护**：彻底修复旧版本在 `toDataURL` 和 `toBlob` 中由于调用自身引发的 `Maximum call stack size exceeded` 递归死循环，采用内部原始原型方法渲染离屏微噪。
- **Apple M2 视网膜硬件仿真**：伪装 WebGL 渲染器与厂商为 `Apple Inc. / Apple M2`。

### 5. 🔗 来源追踪与 Magic Link 净化
- **DNR 请求标头清洗**：在网络底层阻断出站 Referer 标头，避免 Claude 探测到国内邮箱域名。
- **URL 追踪参数剥离**：瞬时剥离 URL 中常见的跟踪标记（`utm_*`, `fbclid`, `gclid`, `_hsenc`, `_hsmi`, `tracking_id` 等）。

---

## 🚀 安装使用指南

### 第一步：在 Chrome 中加载扩展
1. 打开 Chrome 浏览器，在地址栏输入：`chrome://extensions/` 并回车。
2. 在右上角开启 **「开发者模式」 (Developer mode)** 开关。
3. 点击左上角的 **「加载已解压的扩展程序」 (Load unpacked)** 按钮。
4. 在弹出的文件选择器中，定位并选中本目录：
   `/Users/mac/FXXK CLAUDE/tools/extension`
5. 若此前已加载过旧版，请点击扩展卡片右下角的 **🔄 重新加载** 按钮。

### 第二步：选择伪装模式
点击浏览器工具栏上的扩展盾牌图标 🛡️：
- **⚡ 智能对齐当前 VPN（推荐）**：自动检测当前出口 IP 并动态对齐最佳环境，无需手动切换。
- **🇹🇼 固定台湾专线**：Asia/Taipei (UTC+8) · 繁体中文 (zh-TW)。
- **🇺🇸 固定美国原生**：America/Los_Angeles (UTC-7) · 英文 (en-US)。
- **🔄 重新识别**：节点切换后点击一键刷新。

---

## 🛡️ sing-box 定向拦截 Claude IPv6 规则解析

配置文件位置：`/Users/mac/Library/Application Support/v2rayN/binConfigs/configPre.json`

规则片段：
```json
{
  "dns": {
    "rules": [
      {
        "domain_suffix": [
          "claude.ai",
          "anthropic.com",
          "claudeusercontent.com",
          "anthropic.ai",
          "claudecdn.com",
          "statsig.com",
          "statsigapi.net",
          "challenges.cloudflare.com"
        ],
        "query_type": ["AAAA"],
        "action": "predefined",
        "rcode": "NOERROR"
      }
    ]
  },
  "route": {
    "rules": [
      {
        "domain_suffix": [
          "claude.ai",
          "anthropic.com",
          "claudeusercontent.com",
          "anthropic.ai",
          "claudecdn.com",
          "statsig.com",
          "statsigapi.net",
          "challenges.cloudflare.com"
        ],
        "ip_version": 6,
        "action": "reject"
      }
    ]
  }
}
```

> **提示**：v2rayN 切换节点或重载 TUN 时会自动使用此配置启动 sing-box。若要手动使新规则生效，只需在 v2rayN 客户端中轻点一次「重启服务」或切换一次节点即可。
