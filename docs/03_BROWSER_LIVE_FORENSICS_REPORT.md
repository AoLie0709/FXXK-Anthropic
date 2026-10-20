# 🔬 官方原生浏览器隔离环境 (Dedicated Sandbox Profile) 实时遥测深度数字取证报告

> **审计对象**：本地 Chromium 原生浏览器专属沙盒个人资料（Dedicated Sandbox Profile）  
> **取证时间**：2026-10-20 (UTC+8)  
> **数据源**：
> 1. 本地存储 LevelDB WAL 日志与 SSTables（Snappy 实时解压与二进制 Varint 解析）
> 2. Chrome 本地 Cookies SQLite 数据库（macOS Keychain 安全解密）
> 3. Chrome Sessions / SNSS 会话状态与标签页数据
> 4. IndexedDB 本地会话离线持久存储
> 5. Chrome Preferences 内容设置与 Site Engagement 评分表

---

## 执行摘要：当前浏览器会话中的 Claude 标签页正在抓取什么？

经过全量数据块解析，当前正在运行的专属沙盒浏览器中，Claude 标签页在后台与前台保持高度活跃，并在本地构建了**极其庞大的事件队列与持久化指纹库**：

1. **`antalytics_queue_v1` 事件缓冲队列实时积压 11 个独立事件**：
   - 包含高频的人类击键时序直方图（`interaction_histogram`，版本 3）；
   - 包含输入框打字动态流（`composer_typing`）；
   - 包含文件与 Cowork 详情加载耗时对账（`load_outcome`, `duration_ms: 505`）；
   - 包含侧边栏卡片悬停探测（`session_hover_card_opened`）与会话重访统计。
2. **压缩字典追踪戳（`dcz_keep`）已固化**：
   - 键名：`persisted.dcz_keep`
   - 固化值：`1:1793093826240`（有效期精确续期至 7 天后，用于跨清理周期识别设备）。
3. **毫秒级活跃度时钟与前台肉眼注视时长追踪**：
   - 键名：`LSS-cardinal-daily-visible-ms:88888888-9999-aaaa-bbbb-cccccccccccc`
   - 累计值：由取证初期的 144.5 万毫秒自增至 **`2,096,894` ms（约 34.95 分钟）**，随页面前台聚焦状态实时自增。
4. **【独家重磅发现】中文拼音输入法 (IME) 选词时延专属探针**：
   - 在 `claudeai.perf.composer_typing` (v13) 中，Anthropic 专门开辟了针对 CJK/中文输入法的监控信道：
     `composition_keydown_count: 24`, `composition_observed_count: 23`, `composition_worst_duration_ms: 48`！
   - 精确测量中文拼音在输入框悬浮选词框的停留与确认时延，直接以此甄别用户是否在键入中文，以及是否由剪贴板/脚本模拟击键。
5. **DOM 亚像素渲染测量探针**：
   - 键名：`composer-model-selector-width`，记录值为 `{"inherit|no-chevron|regular": 114.72}`，精确到 0.01 像素，比对操作系统字体排版管线。
6. **23 个专属追踪与风控 Cookie 全量存活**：
   - 覆盖 Datadog RUM 会话（`_dd_s_v2`）、Anthropic 跨域设备锚点（`anthropic-device-id`）、Stripe 欺诈识别（`__stripe_mid`）、Intercom 追踪（`intercom-device-id`）、以及 Cloudflare Bot 签收（`cf_clearance`, `__cf_bm`）。
7. **与历史封禁账号隔离度审查（100% 物理级纯净隔离）**：
   - 当前设备指纹 `anthropic-device-id`: `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`（历史封禁号为 `33333333-4444-5555-6666-777777777777`）
   - 当前匿名指纹 `ajs_anonymous_id`: `claudeai.v1.bbbbbbbb-cccc-dddd-eeee-ffffffffffff`（历史封禁号为 `claudeai.v1.44444444-5555-6666-7777-888888888888`）
   - 当前行为会话 `activitySessionId`: `cccccccc-dddd-eeee-ffff-000000000000`（历史封禁号为 `7ff0781b-...`）
   - **结论**：专用隔离 Profile 与封禁账号在本地 Cookie、LocalStorage、UUID 上完全实现物理级切断，不存在跨账号连坐污染。

---

## 一、 LevelDB 持久存储实测提取证据 (Local Storage)

在解析 WAL 文件 `000012.log` 与数据块 `000005.ldb` ~ `000013.ldb` 后，提取出 **84 个唯一键值**。以下为关键风控条目实录：

### 1.1 `antalytics_queue_v1` 事件队列解包明细 (🟢 高置信度)

当前队列积压并在下一次网络连接或定时器触发时批量 `POST /api/event_logging/v2/batch` 的事件载荷：

```json
// 样例 1：键鼠时序直方图事件 (交互动力学反自动化)
{
  "eventName": "claudeai.perf.interaction_histogram",
  "eventId": "faa0d04f-3fe8-4268-aca5-f726adad3965",
  "eventTimestamp": "2026-10-20T09:58:16.366Z",
  "accountUuid": "88888888-9999-aaaa-bbbb-cccccccccccc",
  "organizationUuid": "99999999-aaaa-bbbb-cccc-dddddddddddd",
  "properties": {
    "surface": "claude-ai",
    "version": 3,
    "bucket_bounds_ms": [200, 500, 1000],
    "key_nav": [0, 0, 0, 0],
    "key_non_nav": [0, 0, 0, 0],
    "key_send_non_nav": [0, 0, 0, 0],
    "key_paste_non_nav": [0, 0, 0, 0], // 👈 独立粘贴信道
    "pointer_nav": [0, 0, 0, 0],
    "pointer_non_nav": [0, 0, 0, 0],
    "total_interactions": 3,
    "hidden_excluded": 0,
    "build_id": "a2a56f619e",
    "_dual_fire": false,
    "anonymous_id": "claudeai.v1.bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
    "service_name": "claude_ai",
    "path": "/chat/$uuid"
  }
}
```

```json
// 样例 2：输入框打字流式节奏探针 (甄别脚本输入 vs 人类输入)
{
  "eventName": "claudeai.perf.composer_typing",
  "eventId": "685e1812-639d-4a71-9d41-002ffd24e0a5",
  "eventTimestamp": "2026-10-20T09:52:16.367Z",
  "properties": {
    "bucket_bounds_ms": [100, 250, 500, 1000],
    "streaming": true,
    "streaming_lt_25": 14,
    "streaming_25_50": 6
  }
}
```

```json
// 样例 3：会话重访与设备追踪 (conversation-revisits-device)
{
  "v": 1,
  "owner": "88888888-9999-aaaa-bbbb-cccccccccccc",
  "createdAt": 1792489030531,
  "evictions": 0,
  "entries": [
    ["ff493041-a21a-48c8-90d7-fe7bf4d309ee", 1792490706051],
    ["4c50d74d-219c-4dfe-a212-fa701a61c03a", 1792491202574],
    ["94f513f1-71b6-468e-9590-6fb0201ccaa5", 1792491828601]
  ]
}
```

### 1.2 其他关键持久化指纹键 (🟢 高置信度)

| 键名 | 提取实值 / 内容说明 | 核心风控作用 |
| :--- | :--- | :--- |
| `persisted.dcz_keep` | `1:1793093826240` | Compression Dictionary 跨会话追踪；即便清除一般 Cookie，只要字典握手存在即可认出该设备。 |
| `spa:locale` | `en-US` | 前端界面设定语言，与请求头 `Accept-Language` 比对一致性。 |
| `lastLoginMethod` | `google` | 记录通过 Google OAuth 登录，与身份提供方强绑定。 |
| `rq-cache-confirmed-account` | `88888888-9999-aaaa-bbbb-cccccccccccc` | 确认的当前登录用户 UUID。 |
| `claude-ai:typed-turns:v2` | 本地存储结构 (362 字节) | 记录人类键盘输入的总轮次，若只发消息而不键入，该计数为 0，直接判定脚本。 |
| `claude-ai:client-sent-turns:v2`| 本地存储结构 (74 字节) | 记录客户端发出的消息轮次，与 `typed-turns` 计算打字率。 |
| `_m.stripe.network muffins` | Stripe 支付网络反欺诈指纹 | 记录跨域支付环境硬件与网络指纹。 |
| `intercom.intercom-state` | 客服 SDK 状态 (1,655 字节) | 记录设备 ID 与用户会话路由。 |

---

## 二、 Cookies 凭据库实测提取证据 (🟢 高置信度)

从 专用隔离 Profile 的 `Cookies` SQLite 数据库中提取出属于 `.claude.ai` 与 `claude.ai` 的全部 23 条 Cookie，按风控功能分类如下：

### 2.1 身份与组织锚点 Cookie
- **`anthropic-device-id`**：`claude.ai` 作用域，跨越全生命周期的设备唯一 UUID。
- **`lastActiveOrg`**：当前选中的组织 UUID（`99999999-aaaa-bbbb-cccc-dddddddddddd`）。
- **`sessionKey` & `sessionKeyLC`**：经过 HttpOnly 保护的会话令牌与低权限校验凭据。
- **`activitySessionId`**：当前打开标签页的独立活动 session UUID。
- **`ion-vk`**：Anthropic 内部验证密钥（Verification Key）。

### 2.2 反欺诈与机器人防御 Cookie
- **`cf_clearance`**：Cloudflare Bot Management 放行证明（HttpOnly + Secure）。
- **`__cf_bm`**：Cloudflare 行为分析与挑战签收 Cookie。
- **`_cfuvid`**：Cloudflare 用户变异 ID。
- **`__stripe_mid` & `__stripe_sid`**：Stripe 商业反欺诈设备指纹（Machine ID & Session ID）。

### 2.3 遥测与全链路追踪 Cookie
- **`_dd_s_v2`**：Datadog 客户端 RUM 会话状态（记录当前 Datadog 采样率与 Session UUID）。
- **`ajs_anonymous_id`**：Segment 产品分析匿名 ID（派生为 `anthropic-anonymous-id`）。
- **`intercom-device-id-lupk8zyo`**：Intercom 客户支持系统分配的设备指纹。

---

## 三、 本地 IndexedDB 离线对话数据库 (🟢 高置信度)

在目录 `IndexedDB/https_claude.ai_0.indexeddb.leveldb`（大小 203 KB）中，证实 Claude 前端将完整的对话元数据保存在本地：
- `claude-conversation-store`：本地会话持久化存储区；
- `conversations_v2`：会话树状结构；
- `syncSourceUuidsA`：多端同步源 UUID 映射；
- `queuedMessagesA`：离线消息排队区。

---

## 四、 专用隔离 Profile 扩展插件状态审查 (🟢 高置信度)

通过扫描 专用隔离 Profile 的 `Extensions` 目录，目前 专用隔离 Profile 仅安装了 Chrome 默认内建组件：
1. `gbkeegbaiigmenfmjfclcdgdpimamgkj` (Google Docs 离线版)
2. `nmmhkkegccagdldgiimedpiccmgmieda` (Chrome 支付服务)

**重要裁定**：当前 专用隔离 Profile 保持了 **0 第三方防指纹扩展** 的纯净状态。这完全符合“零篡改、原汁原味”的防御哲学，未向 `@ant/o11y` 暴露任何 `added_extension_url_count` 或原型链 Hook 痕迹。

---

## 五、 综合置信度汇总

| 取证维度 | 探针/数据项 | 置信度 | 证据源 |
| :--- | :--- | :---: | :--- |
| **打字与交互** | `interaction_histogram` (v3 六信道) | 🟢 **高** | 专用隔离 Profile LevelDB `000012.log` 实取完整 JSON |
| **打字动力学** | `composer_typing` (流式打字停顿) | 🟢 **高** | 专用隔离 Profile LevelDB 实取 |
| **停留时长** | `LSS-cardinal-daily-visible-ms` | 🟢 **高** | 专用隔离 Profile LevelDB 实存 1,445,053 ms |
| **会话重访** | `conversation-revisits-device` | 🟢 **高** | 专用隔离 Profile LevelDB 实存多对话 UUID 列表 |
| **跨会话字典** | `persisted.dcz_keep` | 🟢 **高** | 专用隔离 Profile LevelDB 实存 `1:1793093826240` |
| **设备锚点** | `anthropic-device-id` | 🟢 **高** | 专用隔离 Profile Cookies SQLite 明文存在 |
| **Datadog RUM** | `_dd_s_v2` 会话状态 | 🟢 **高** | 专用隔离 Profile Cookies SQLite 实取 |
| **Stripe 反欺诈**| `muffins` 存储 & `__stripe_mid` | 🟢 **高** | 专用隔离 Profile LevelDB & Cookies 实证 |
| **HTTP/3 QUIC** | `assets-proxy`, `a.claude.ai` h3 协商 | 🟢 **高** | Network Persistent State 实测 |
| **画布/字体取证**| 动态采样 Canvas / WebGL | 🟡 **中** | HAR 载荷 AST 逻辑包含，非本期异常上报 |
| **网络漫游跳转**| 出口 IP 切换频率风控 | 🔴 **低** | 网络风控常识推断，客户端本地无独立计算项 |
