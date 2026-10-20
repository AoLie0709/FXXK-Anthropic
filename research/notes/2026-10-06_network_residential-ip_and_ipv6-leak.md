> 📌 专题笔记（2026-10-06）：针对具体问题的时间点结论，可能过时。方向性原则见 [docs/](../../docs/00_PRINCIPLES.md)。

# 基础设施层：出口网络、台湾中华电信 HiNet 与 sing-box 定向 IPv6 阻断

> **所属防线**: **Tier 1 - Network & ISP Infrastructure**  
> **核心使命**: 打造零指纹破绽、零地理时区冲突、零国内公网 IPv6 泄漏的极高信誉度底层网络通道。

---

## 📑 目录

1. [住宅 IP vs 数据中心 IP：风控系统的判别逻辑](#1-住宅-ip-vs-数据中心-ip风控系统的判别逻辑)
2. [为什么台湾中华电信 HiNet (AS3462) 是访问 Claude 的终极解？](#2-为什么台湾中华电信-hinet-as3462-是访问-claude-的终极解)
3. [致命漏洞：国内宽带公网 IPv6 泄露与穿透机制](#3-致命漏洞国内宽带公网-ipv6-泄露与穿透机制)
4. [sing-box DNS 定向 AAAA 阻断架构（保留全局 IPv6）](#4-sing-box-dns-定向-aaaa-阻断架构保留全局-ipv6)
5. [v2rayN / sing-box 生产环境部署配置](#5-v2rayn--sing-box-生产环境部署配置)
6. [网络纯净度与规则验证实操](#6-网络纯净度与规则验证实操)

---

## 1. 住宅 IP vs 数据中心 IP：风控系统的判别逻辑

Anthropic 的防欺诈风控引擎（集成 Cloudflare Bot Management、Statsig 及主流 IP 信誉数据库如 MaxMind GeoIP2、Spur.us、IPQualityScore）对所有入站请求的出口 IP 进行第一道硬性初筛：

| 维度 | 机房/托管 IP (Hosting / Datacenter) | 原生住宅 IP (Residential / ISP) |
| :--- | :--- | :--- |
| **典型代表** | AWS, Google Cloud, Oracle, DigitalOcean, 搬瓦工 | 台湾中华电信 (Chunghwa Telecom), 台湾大哥大, AT&T, Comcast |
| **ASN 属性** | 商业托管服务商 (Hosting ASN) | 民用互联网服务提供商 (Consumer ISP ASN) |
| **欺诈评分 (Fraud Score)** | **70 ~ 100** (默认高危，极易触发人机验证) | **0 ~ 15** (原生白名单级别，几乎不触发验证) |
| **Anthropic 行为** | 频繁要求 Turnstile 验证码；订阅时直接砍单；高频封号 | 丝滑通行；直接放行 Google SSO；极大降低风控审计频率 |

---

## 2. 为什么台湾中华电信 HiNet (AS3462) 是访问 Claude 的终极解？

许多开发者直觉认为「访问美国 AI 就必须用美国 IP」，这在实际工程中是严重的误区。使用美国节点存在以下天然风控隐患：

1. **时钟昼夜节律倒错（Circadian Anomaly）**：
   - 当国内用户在白天（如北京时间 14:00）高频使用 Claude 时，对应的美国洛杉矶时间是凌晨 22:00 ~ 02:00（跨半夜）。
   - 风控行为模型长期观测到用户在当地深更半夜连续数小时活跃，且本地机器与出口网络存在 15~16 小时时差，极易被标记为自动化 Agent 或离岸外包账号。
2. **时区物理重合度**：
   - **台湾地区（Asia/Taipei）与中国大陆（Asia/Shanghai）同属 UTC+8 时区，物理时差为 0 小时！**
   - 机器本地时钟与出口节点物理时区 100% 吻合，无需强行在操作系统层调整时区。
3. **极低物理延迟**：
   - 东南沿海直连台湾 HiNet 延迟仅 30ms ~ 50ms，RTT（往返时延）特征与真人本地浏览完全吻合，杜绝了跨太平洋 200ms+ 延迟产生的 TCP 拥塞指纹异动。
4. **AS3462 国际顶级信誉**：
   - 中华电信（Chunghwa Telecom, AS3462）为台湾最大一级电信运营商，其动态/固定家庭光纤 IP 均为全球公认的纯正 Residential IP。

---

## 3. 致命漏洞：国内宽带公网 IPv6 泄露与穿透机制

### 泄漏发生的真实场景
目前中国电信、中国联通、中国移动已全网下发公网 IPv6 地址（前缀通常为 `240e:...`、`2408:...`、`2409:...`）。
现代操作系统（macOS / Windows / Linux）在双栈网络下，默认遵循 **RFC 8305 (Happy Eyeballs v2)** 算法：
- 浏览器在请求 `claude.ai` 时，会同时并发查询 IPv4 (A 记录) 与 IPv6 (AAAA 记录)。
- 如果当前代理客户端（如 v2rayN、Clash 等）配置不当，AAAA 查询穿透到了本地运营商 DNS，并解析出 Cloudflare 边缘的 IPv6 地址；
- 系统网络协议栈可能会优先尝试建立 IPv6 直连。这一握手**直接绕过了代理隧道，将中国大陆真实公网 IPv6 暴露给 Cloudflare 边缘节点！**
- **结果**：Anthropic 瞬间侦测到来自 CN 区域的直接握手，触发即时封禁（Error code 1020 或 Account Terminated）。

### 错误解法 vs 正确解法
- **❌ 错误解法（暴力关闭系统 IPv6）**：
  在 macOS 终端执行 `networksetup -setv6off Wi-Fi`。这会导致国内高校网络、内网穿透、NAS 访问、PT 下载与国内直连应用受阻，属于因噎废食。
- **🟢 正确解法（sing-box DNS 定向 AAAA 阻断）**：
  保持 macOS 系统全局 IPv6 完好。仅在代理核心（sing-box）的 DNS 拦截规则中，对 Claude 相关域名强制拦截 AAAA 查询，返回预定义的空应答（NODATA），迫使浏览器无缝回退至 IPv4 住宅代理隧道！

---

## 4. sing-box DNS 定向 AAAA 阻断架构（保留全局 IPv6）

```
                     用户发起访问: https://claude.ai
                                    │
                                    ▼
                     macOS 系统网络协议栈并发查询
                 ┌──────────────────┴──────────────────┐
                 │                                     │
          A 记录查询 (IPv4)                     AAAA 记录查询 (IPv6)
                 │                                     │
                 ▼                                     ▼
        sing-box DNS 规则匹配                 sing-box DNS 规则匹配
                 │                                     │
          [命中代理路由]                       [命中定向阻断规则]
                 │                                     │
      走代理隧道查询纯净 IPv4 IP               action: "predefined"
                 │                             rcode: "NOERROR" (空响应)
                 │                                     │
                 ▼                                     ▼
      返回台湾住宅出口 IPv4 IP                   返回 NODATA (无 IPv6)
                 │                                     │
                 └──────────────────┬──────────────────┘
                                    │
                                    ▼
                系统无缝通过 IPv4 隧道与 Claude.ai 建立 TLS
                 （本地真实 IPv6 得到 100% 物理级隐蔽）
```

---

## 5. v2rayN / sing-box 生产环境部署配置

在 macOS 下使用 v2rayN (sing-box 内核) 时，配置注入路径为：  
`/Users/mac/Library/Application Support/v2rayN/binConfigs/configPre.json`

### 核心配置规则（DNS 层 + 路由层双重拦截）

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

> **原理说明**：
> 1. `dns.rules`: 拦截 AAAA 查询，返回预设的空成功应答 (`NOERROR` + 0 条记录)。浏览器因此认定该域名没有 IPv6 地址，瞬间无感回退至 IPv4。
> 2. `route.rules`: 兜底策略。倘若操作系统因本地缓存或底层探针仍发起目标为上述域名的 IPv6 数据包，直接就地丢弃 (`reject`)，防止漏网之鱼。

---

## 6. 网络纯净度与规则验证实操

本项目提供了经过充分实战检验的自动化核验脚本：

### 1. 验证定向 IPv6 阻断是否生效
运行：
```bash
/Users/mac/FXXK\ CLAUDE/tools/scripts/test_singbox_ipv6.sh
```
**合格标志**：
- `claude.ai`、`anthropic.com` 的 AAAA 记录均显示 `✅ 已精准拦截 (NODATA 空应答)`。
- `apple.com`、`qq.com` 等普通域名 IPv4/IPv6 均正常解析，证明系统全局网络未受损。

### 2. 验证出口节点纯净度与 ASN
运行：
```bash
/Users/mac/FXXK\ CLAUDE/tools/scripts/check_node_purity.sh
```
**合格标志**：
- 出口运营商为 `Chunghwa Telecom` 或 `HiNet` (AS3462)。
- IP 类型为 `🏠 家庭宽带 / 住宅 IP (Residential)`。
- 风控评分 `<= 10`。
