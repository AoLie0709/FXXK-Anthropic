# Claude 网页端 × 桌面端「封号探针」防御性逆向

> **日期**：2026-10-19
> **方法**：三份 claude.ai HAR（WebInspector 导出）实测 + 本机 `Claude.app` 的 `app.asar` 只读副本静态逆向 + GitHub REA 工具链 + 公开逆向资料交叉验证
> **约束**：全程未修改 `/Applications` 下任何文件、未改全局 npm/系统配置、未执行目标应用代码
> **脱敏**：所有 UUID 仅保留前 8 位，邮箱/组织名打码；原始值不落盘于本报告
> **定位**：防御性研究 —— 目标不是"绕过判定"，而是**识别判定面 → 消除不一致 → 让环境真实且自洽**

---

## 0. 结论摘要

1. **探针分四层，不是一层**：**基础**（身份/设备属性）、**攻击**（挑战与封禁判定）、**静默**（后台读取、从不询问）、**防御**（反自动化/反伪造/反篡改）。真正决定成败的是后两层——静默层你感知不到，防御层会把你"修过的痕迹"反过来当证据。
2. **网页端最"攻击性"的探针是客户端证明**：hCaptcha invisible 覆盖登录 / 注册 / 删号 / 建 API Key / 加入组织 / 支付 / 魔法链接 / 申诉，token 内嵌 `visibility`、`focus`、`hiddenSinceAsk`、`mintWaitMs`、`challengeShown`、`account_switched` 六类元数据。
3. **静默层读了什么，已逐项定位**：硬件并发与内存、`userAgentData` 高熵值、网络质量（`effectiveType`/`downlink`/`rtt`/`saveData`）、时区日历（`timeZone`/`calendar`/`numberingSystem`/`hourCycle`）、外设与权限、存储配额、视口健康分级（`too_small`/`below_target`/`ok`）。
4. **但平台不做重度浏览器指纹**：WebGL 渲染器、AudioContext、Canvas 哈希、字体枚举在 178 个 bundle 里**全部零命中**；也没有任何第三方指纹 SDK（FingerprintJS / Forter / Kasada / DataDome / Arkose 全阴性）。深度指纹由 hCaptcha 与 Cloudflare 承担。
5. **防御层是"归一化器"，不是"采集器"**：`tY()` 判 UA 形态（6 态）、`PM()` 校验 UA 与 Client Hints 一致、`q1()` 判视口恒等、`hz()` 判自动化三态、`hidden_at_load` 判后台加载。它们只问一件事：**你的值彼此对得上吗**。
6. **改指纹在这个平台是负收益**：你改的每一项平台自己都没在采，但改的过程必然产生 `ua_client_hints: mismatch`、`unreduced_version`、`unreduced_platform` 这类**新矛盾**。
7. **封禁是组织级连坐**：`banned_orgs[]` 实证同一身份下 consumer org 与 api org 同时被封（`ban_category: other`），`review_eta_days: 10` 给出申诉窗口。
8. **桌面端有独立身份与跨端缝合线**：`ant-did`（安装级 UUID，与登录无关）+ `_cross_domain_anonymous_id`（1 年 cookie，写入 claude.ai）+ GrowthBook 事件的 `device_id & anonymous_id`。
9. **桌面端独有探针**：CCD 文件系统边界（符号链接越界 / 硬链接读取）、macOS TCC 权限状态、`vm_network_mode` / `nest_local_user`（虚拟化检测）、Chrome Safe Storage 导入（`deriveBrowserSafeStorageKey`）。
10. **交付了一个可自查的工具**：`tools/web/consistency-audit.html` 把上述判定逻辑移植到本地，六项核心判定 + 全部静默字段 + 出口一致性矩阵；已用 headless Chrome 验证判定准确（正确识别 `ua_headless`）。

---

## 1. 取证方法与证据等级

| 等级 | 含义 | 本报告用法 |
| :--- | :--- | :--- |
| **E1 实测** | HAR / 本机文件直接可见 | 结论主体，标注来源 |
| **E2 代码** | 本机 asar 静态逆向出的实现 | 判定逻辑与开关 |
| **E3 交叉** | 公开逆向资料与实测吻合 | 补充传播链路 |
| **E4 推断** | 基于架构常识的高置信外推 | 明确标注"未直接观测" |

证据产物：

- `output/har_analysis/summary.md` / `summary.json` / `telemetry_events.json`（脚本：`tools/scripts/audit_har_probes.py`）
- `output/desktop_analysis/probe_report.md` / `probe_hits.json`（脚本：`tools/scripts/scan_desktop_probes.py`）
- `scratch/claude_desktop_asar/`（asar 副本 + 解包，只读源；脚本：`tools/scripts/extract_asar_readonly.py`）
- `scratch/rea-toolchain/`（REA 隔离安装 + Evidence）
- `scratch/web_assets/`（178 个前端 bundle，20.6 MB，从 HAR 提取 URL 后下载；脚本：`tools/scripts/scan_web_probes.py`）
- `output/web_analysis/web_probes.json`（四类探针全量命中表）

三份 HAR 的场景：

| 文件 | 请求数 | 场景 |
| :--- | ---: | :--- |
| `claude.ai.har` | 216 | 封禁后访问 `/restricted/submit` 申诉页，`app_start` 返回 403 |
| `claude.ai-2.har` | 204 | 封禁态完整会话：standing / current_appeal / event_logging / client-health |
| `claude.ai-3.har` | 17 | 短会话，仅 Datadog RUM 上报 |

---

## 2. 网页端探针面（6 层，E1 实测）

### 2.1 L1 身份标识层（每个 API 请求都带）

实测请求头（`claude.ai.har` L1362–L1432）：

| 头 | 实测值形态 | 作用 |
| :--- | :--- | :--- |
| `anthropic-device-id` | UUIDv4（`33333333-…`） | **浏览器侧设备身份**，跨会话稳定 |
| `anthropic-anonymous-id` | `claudeai.v1.<uuid>` | 匿名期身份，登录前即存在 |
| `x-activity-session-id` | UUID（`7ff0781b-…`） | 会话级活动标识 |
| `anthropic-client-platform` | `web_claude_ai` | 客户端类型 |
| `anthropic-client-version/build/sha` | `1.0.0` / `1792386525` / `f83619f0…` | **构建指纹**，与页面 `data-build-id` 同源 |
| `anthropic-client-capabilities` | `mfa_sms_v1, mfa_email_v1` | 能力声明，可反推账号安全态 |
| `x-app-locale` | `zh-Hant` | 应用语言 |
| `accept-language` | `zh-CN,zh;q=0.9`（HAR-2）vs `zh-Hant, zh-TW;q=0.9, …`（HAR-1） | **同一设备出现两种语言形态** |
| `sec-ch-ua` | `"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"` | Client Hints |
| `sec-ch-ua-platform` | `"macOS"` | 平台 |
| `user-agent` | Chrome/154 / macOS 10_15_7 | UA |

**关键点**：三份 HAR 中 `anthropic-device-id`、`anonymous-id`、`x-activity-session-id` 各只有 **1 个取值且跨文件一致**（见 `har_analysis/summary.md` §2）。这说明它们不随页面刷新轮换，属于**持久设备身份**，是账号关联图谱的第一锚点。

`referer: https://claude.ai/restricted/submit`（L1395）出现在 `app_start` 请求上——封禁态下前端仍会带完整身份头去请求 bootstrap，只是被 403 拒绝（L1457）。

### 2.2 L2 客户端证明层（Client Attestation）★ 最"攻击性"

这是本次逆向最重要的发现：**Anthropic 不只依赖被动指纹，而是主动发起隐形挑战**。

实测证据链：

1. 页面加载 hCaptcha：`https://js.hcaptcha.com/1/api.js?render=explicit&recaptchacompat=off&onload=__antClientAttestationHcaptchaInvisibleReady`（HAR 内联脚本）
   - 回调名 `__antClientAttestationHcaptchaInvisibleReady` = Anthropic 自有的客户端证明命名空间；
   - `invisible` = 无交互挑战，用户无感。
2. `api.hcaptcha.com/checksiteconfig?host=claude.ai&sitekey=527a7444-0eb8-4b1c-942a-41941a06869c&sc=1&swa=1&spst=1` —— 站点配置校验。
3. 证明引擎代码（HAR 内联 JS 模块 `client_attestation_engine`）：

```
tier: "T2", onChunkError: "fail-open",
mint timeout: 20000ms, gate: "hcaptcha_mint_timeout", "cai_fluttering_balloon",
hcaptcha_held_token_age_limit,
error codes: no_widget, gate_off, timeout, timeout_sitekey_pending,
  timeout_load_deferred, timeout_script_loading, timeout_executing,
  timeout_challenge_open, pending_*, script_load_error, script_load_timeout,
  render_error, execute_error, token_expired, challenge_expired,
  challenge_closed, challenge_dismissed, widget_reset, widget_unmounted,
  late_token_dropped, stale_discarded, execute_restarted, vendor_error_*
```

4. 每个 token 的上报元数据（关键）：

```
visibilityAtAsk, visibilityAtEnd, focusedAtAsk, hiddenSinceAsk,
challengeShown, mintWaitMs, reuseHeldToken, requestKind, channel,
surface, ageLimit, expectedSurfaces
```

5. **账号切换检测**：`if (currentAccount !== capturedAccount) return {status:"cancelled", cause:"account_switched"}` —— token 绑定发起时的账号，**防止"切号复用证明"**。
6. 失败后果：`missing_client_attestation` → 前端文案 `"We couldn't verify your browser."`；`browserNotVerified` 错误类型。
7. 覆盖动作（growthbook 开关名实测）：
   - `claude_ai_login_hcaptcha_frontend_enabled`
   - `console_login_hcaptcha_frontend_enabled`
   - `admin_login_hcaptcha_frontend_enabled`
   - `auth_login_hcaptcha_frontend_enabled`
   - `claude_ai_payments_hcaptcha_desktop_enabled`（**桌面端支付也走 attestation**）
   - `claude_ai_send_magic_link_hcaptcha_more_pages_enabled`
   - `claude_ai_org_join_hcaptcha_sitekey`
   - `claude_ai_key_create_hcaptcha_dismiss_aborts_submit`
   - 账号自删除同样要求 attestation（`account_self_deletion`）

**判读**：`visibility/focus/hiddenSinceAsk` 四字段是**反无头、反后台自动化**的直接设计。`mintWaitMs` 与 `challengeShown` 让服务端能区分"真人瞬间通过"与"脚本 20 秒超时"。`reuseHeldToken` 用来识别 token 复放。

封禁态下服务端还会下发 `restricted_hcaptcha_sitekey` + `restricted_hcaptcha_mode: "collect"`（见 §2.5），即申诉入口强制采集证明。

### 2.3 L3 反自动化遥测（HealthMetricEvent）★ 反伪造核心

实测遥测体（`claude.ai-2.har` L52539）：

```json
{"events":[{"event_type":"HealthMetricEvent","event_data":{
  "action":"app.bootstrap","surface":"app","outcome":"failure",
  "error_type":"user_error","error_code":"account_banned",
  "app_version":"f83619f0c3","platform":"web","first_party_host":true,
  "is_automation":false,"ua_form":"reduced",
  "ua_client_hints":"match","screen_equals_viewport":false
}}]}
```

字段判读：

| 字段 | 取值 | 判定含义 |
| :--- | :--- | :--- |
| `is_automation` | false | `navigator.webdriver` / CDP 痕迹检测结果 |
| `ua_form` | `reduced` | UA 处于 Chrome UA-Reduction 精简形态（正常） |
| `ua_client_hints` | `match` | **UA 字符串与 `Sec-CH-UA` 一致**；篡改 UA 但没改 CH 会变 `mismatch` |
| `screen_equals_viewport` | false | `screen.width === innerWidth` 为真 = 无头/固定视口特征 |
| `first_party_host` | true | 请求是否落在 `claude.ai` 一方域 |
| `platform` / `surface` | web / app | 端与面 |
| `error_code` | `account_banned` | **服务端已判定**的账号状态 |

同一个 `event_logging/v2/batch` 端点（`x-service-name: claude_ai_web`）还承载 `ProductAnalyticsEvent`。

> 这是"攻击性探针"的典型结构：**不是问"你是什么"，而是问"你的答案彼此矛盾吗"**。

### 2.4 L4 行为节奏层

实测 `claudeai.perf.interaction_histogram`（三个采样窗口）：

```json
{"version":3,"bucket_bounds_ms":[200,500,1000],
 "key_nav":[0,0,0,0],"key_non_nav":[0,0,0,0],
 "key_send_non_nav":[0,0,0,0],"key_paste_non_nav":[0,0,0,0],
 "pointer_nav":[0,0,0,0],"pointer_non_nav":[0,1,0,0],
 "total_interactions":46,"hidden_excluded":0}
```

- **分桶**：<200ms / 200–500ms / 500–1000ms / >1000ms；
- **通道**：键盘导航键、普通按键、发送键、粘贴、指针导航、指针普通；
- **`hidden_excluded`**：页面不可见期间的交互被排除（与 attestation 的 visibility 口径一致）。

它不采集轨迹坐标，但**分布形状**是稳定的个体特征；脚本的极端集中分布（大量 <200ms）在统计上很明显。

### 2.5 L5 风控状态与封禁语义（服务端明文）

实测 `GET /api/account/standing` → 200（`claude.ai-2.har` L27931–L27934）：

```json
{"standing":"bad_standing","banned_at":"2026-10-19T07:33:20Z",
 "org_type":"consumer","prev_plan_tier":"claude_pro",
 "ban_category":"other","hide_steps_card":false,"age_verification_url":null,
 "export_policy":"allow",
 "restricted_hcaptcha_sitekey":"527a7444-…","restricted_hcaptcha_mode":"collect",
 "restricted_actions_hcaptcha_sitekey":null,
 "banned_orgs":[
   {"name":"528w…@privaterelay.appleid.com's Organization","org_type":"consumer","ban_category":"other"},
   {"name":"傲…'s Individual Org","org_type":"api","ban_category":"other"}],
 "has_active_org":false,"native_appeal_form_enabled":false,"review_eta_days":10}
```

要点：

- `standing: bad_standing` —— 账号信誉分档（有明确档位语义）；
- `banned_orgs[]` —— **组织级连坐**：consumer org 与 api org 同时 `ban_category: other`；org 名称里出现 **Apple 私密转发邮箱**（`@privaterelay.appleid.com`），说明该身份用 Apple 登录且被记录；
- `prev_plan_tier: claude_pro` —— 付费层级被记录，付费不豁免；
- `review_eta_days: 10` —— 申诉复核 SLA；
- `restricted_hcaptcha_mode: "collect"` —— 受限页强制采集证明；
- `export_policy: "allow"` —— 数据导出仍开放。

相关端点：`/api/account/current_appeal`、`/api/account/deletion-allowed`、`/edge-api/client-health/check?platform=web&bundle=…&locale=zh-TW`（健康检查，返回 `{}`）。

封禁的直接技术表现：`GET /edge-api/bootstrap/…/app_start` → **403**（L1457），前端据此降级到 `/restricted`。

### 2.6 L6 基础设施与第三方

| 组件 | 实测端点 | 观察 |
| :--- | :--- | :--- |
| Cloudflare Bot Management | `claude.ai/cdn-cgi/challenge-platform/scripts/jsd/main.js`、`/h/b/jsd/oneshot/d2d3316b…` | 非交互式 JS 检测 + 一次性挑战 |
| Cloudflare 边缘 | `cf-ray: …-TPE`、`data-ion-ip-country="TW"`、`data-ion-served-at` | **服务端把 IP 国家注入 HTML** |
| Datadog RUM | `browser-intake-us5-datadoghq.com/api/v2/rum`、`/api/v2/rum` | 公开 app key `pub71869dceb…`，SDK 7.6.0 |
| GrowthBook + Statsig | `/edge-api/bootstrap/…/app_start?statsig_hashing_algorithm=djb2&growthbook_format=sdk` | 下发特性开关/实验（含上述 hCaptcha 开关与风控阈值） |
| Intercom | `js.intercomcdn.com` 等（CSP 白名单） | 客服侧会话 |
| hCaptcha 资产 | `newassets.hcaptcha.com`、`*.w.hcaptcha.com`、`api.hcaptcha.com` | 证明与 PoW（`hsw.js`） |

**代理痕迹**：HAR 中 `serverIPAddress: 198.18.0.245`（`198.18.0.0/15` 为 benchmark 保留段）——本地 TUN/fake-IP 代理的典型指纹。这类地址不会出现在真实用户流量里，若随请求元数据上行即是强信号（需验证：通常 `serverIPAddress` 只存在于 HAR，不上行；但"出口 IP 是否数据中心段/是否跳变"必然可判）。

**地区不一致实测组合**：出口 `TW`（`data-ion-ip-country`、`cf-ray -TPE`）、页面 `locale=zh-TW`、`x-app-locale=zh-Hant`，但 `accept-language: zh-CN,zh;q=0.9`。三者中有一个不跟随。

### 2.7 未直接观测但高置信的探针（E4，明确标注）

| 探针 | 置信度 | 依据 |
| :--- | :--- | :--- |
| TLS/JA4/JA3 握手指纹 | 高 | Cloudflare 在链路上，JA4 是 2026 标准 |
| HTTP/2 SETTINGS 指纹 | 高 | 同上 |
| `cf_clearance` / `__cf_bm` cookie 生命周期 | 高 | Cloudflare 标准机制 |
| WebRTC 本地 IP 泄漏 | 中高 | 浏览器默认行为，Claude 无需自采即可在服务端关联 |
| Canvas/WebGL/Audio 指纹 | 中 | Anthropic 自身未见证据，但 hCaptcha/Cloudflare 会采 |
| 时区/IP/语言三方一致性 | 高 | 已有 `data-ion-ip-country` 与 locale 双通道 |
| 账号图谱（同设备多号、同支付、同邮箱域） | 高 | `banned_orgs[]` 连坐实证 |
| 剪贴板能力探测 | 中 | 页面有粘贴统计，权限态可测 |
| 代理/VPN 出口信誉（ASN、数据中心段） | 高 | 商业风控标准输入 |

### 2.8 静默探针：后台读取、从不询问你的属性（E1 实测，178 bundle / 20.6 MB）

这一层最容易被忽略——它不报警、不弹验证，但每次页面加载都会读一遍。

| 类别 | 实测读取点 | 命中 |
| :--- | :--- | ---: |
| 硬件 | `navigator.hardwareConcurrency`、`navigator.deviceMemory`、`performance.memory` | 1 / 1 / 1 |
| 平台 | `navigator.platform`、`navigator.vendor`、`navigator.maxTouchPoints` | 9 / 4 / 23 |
| 屏幕 | `screen.width/height/availWidth/availHeight`、`devicePixelRatio`、`matchMedia` | 2/2/36/85 |
| UA 高熵 | `userAgentData.getHighEntropyValues`（arch/bitness/platformVersion/fullVersionList） | 24 / 6 |
| 网络质量 | `navigator.connection`（`effectiveType`/`downlink`/`rtt`/`saveData`） | 16 / 9 / 9 / 14 / 10 |
| 时区日历 | `Intl.DateTimeFormat().resolvedOptions()`（`timeZone`/`calendar`/`numberingSystem`/`hourCycle`） | 15 / 59 / 36 / 7 / 12 |
| 外设 | `mediaDevices`、`getUserMedia`、`enumerateDevices` | 9 / 6 / 1 |
| 权限 | `permissions.query`、`geolocation`、`Notification.permission` | 3 / 8 / 7 |
| 存储 | `indexedDB`、`quota`、`persist` | 17 / 22 / 473 |

#### 视口健康分级（完整实现，`c431f1c9a`）

```js
function u(){return{
  outerWidth:window.outerWidth, outerHeight:window.outerHeight,
  innerWidth:window.innerWidth, innerHeight:window.innerHeight,
  screenAvailWidth:window.screen.availWidth, screenAvailHeight:window.screen.availHeight,
  devicePixelRatio:window.devicePixelRatio, ...}}
function p(e=u()){return{
  outer_width:Math.round(e.outerWidth), outer_height:Math.round(e.outerHeight),
  viewport_width:Math.round(e.innerWidth), viewport_height:Math.round(e.innerHeight),
  screen_avail_width:..., screen_avail_height:..., device_pixel_ratio:...}}
// 分级：too_small / below_target / ok
var a={width:480,height:640}, o={width:320,height:400},
    s={shortSide:.5, longSide:.4}, c=480, l=250;
```

**判读**：平台会把窗口尺寸分档上报（`ok` / `below_target` / `too_small`），并用 `shortSide: .5`、`longSide: .4` 的比例做辅助判断。窗口长期小于 480×640 或比例异常，是"非真人操作环境"的直接证据。

#### 明确不存在的采集（反证同样重要）

在 178 个 bundle 里**零命中**：

| 常见指纹项 | 命中 | 结论 |
| :--- | ---: | :--- |
| `WEBGL_debug_renderer_info` / `UNMASKED_VENDOR_WEBGL` / `UNMASKED_RENDERER_WEBGL` | 0 | 不采 WebGL 渲染器 |
| `getSupportedExtensions` / `getShaderPrecisionFormat` | 0 | 不采着色器精度 |
| `OfflineAudioContext` / `createOscillator` | 0 | 不采音频指纹 |
| `measureText` / `fonts.check` | 0 | 不做字体枚举 |
| `colorDepth` / `pixelDepth` / `screen.orientation` | 0 | 不采色深/朝向 |
| `doNotTrack` / `cookieEnabled` / `pdfViewerEnabled` | 0 | 不采 DNT/PDF |
| `toDataURL` / `getImageData` | 2 / 2 | 仅图像功能，非指纹 |

> **这是本报告最有价值的否定结论**：Anthropic **不自研重度浏览器指纹**。深度指纹完全外包给 hCaptcha（attestation）与 Cloudflare（TLS/HTTP 指纹）。所以「装一堆指纹伪造扩展」在这里是**纯负收益**——你改的每一项，平台自己都没在采，但改的过程会产生 `ua_client_hints: mismatch` 这类**新的矛盾**。

### 2.9 防御性探针：反自动化 / 反伪造 / 反篡改（E1/RE 实测）

#### ① 自动化检测 `hz()`

```js
function hz(e){
  if(!e) return null;
  let t = typeof e.userAgent=="string" ? e.userAgent : "";
  return L1.test(t) && !pZ.test(t) ? "ua_bot"
       : lg.test(t) ? "ua_headless"
       : e.webdriver === true ? "webdriver"
       : null;
}
L1 = /bot(?:[^a-z0-9]|$)|crawl|spider|slurp|scrape|lighthouse|pagespeed|ptst\/|prerender|
      google(?:other|-inspectiontool|-read-aloud| favicon)|bingpreview|facebookexternalhit|
      datadogsynthetics|checkly/i
pZ = /cubot/i                      // 排除 Cubot 手机品牌，避免误伤
lg = /HeadlessChrome|PhantomJS/
var bz = hz(navigator), fx = bz !== null;
```

三类信号：`ua_bot` / `ua_headless` / `webdriver`。注意 `datadogsynthetics`、`checkly`、`lighthouse` 都在名单里——**监控/合成测试流量也会被标记**。

#### ② UA 形态分类 `tY()`（六态）

```js
function tY(e){
  if(typeof e!="string") return "other";
  if(YN.test(e) || Cc.test(e)) return "electron";            // Electron/ 或 Claude Nest|Gov/
  if(oD.test(e)) return "webview";                            // "; wv)"
  let t = tn(e);  if(!t) return "other";
  if(Number(t[0]) < ME) return "pre_reduction";               // ME = 113
  if(t[1]!=="0" || t[2]!=="0" || t[3]!=="0") return "unreduced_version";
  let n = Ho.exec(e)?.[1];
  return n !== void 0 && kD.test(n) ? "reduced" : "unreduced_platform";
}
```

| 返回值 | 触发条件 | 含义 |
| :--- | :--- | :--- |
| `electron` | `/Electron\//` 或 `/Claude(Nest|Gov)?\//` | 在桌面客户端 / Electron 壳里 |
| `webview` | `; wv)` | Android WebView |
| `pre_reduction` | Chrome < 113 | 版本过旧 |
| `unreduced_version` | Chrome 后三段非 `.0.0.0` | **UA 被手工改过** |
| `reduced` | 平台串在白名单 | 正常 |
| `unreduced_platform` | 平台串不在白名单 | **UA 平台串被篡改或不标准** |

#### ③ 平台串白名单 `kD`（只有 5 种合法值）

```js
kD = /^(?:Windows NT 10\.0(?:; Win64; x64|; WOW64)?
     |Macintosh; Intel Mac OS X 10_15_7
     |X11; Linux x86_64
     |X11; CrOS [a-z0-9_]+ 14541\.0\.0
     |Linux; Android 10; K)$/
```

> **macOS 只认 `Macintosh; Intel Mac OS X 10_15_7`**。这是 Chrome UA-Reduction 的冻结值：无论你的 Mac 跑 macOS 14 / 15 / 26，UA 里永远是 10_15_7。如果你看到自己的 UA 里写着真实系统版本（如 `Mac OS X 26_5_2`），那说明**UA 被改坏了**。

#### ④ Client Hints 一致性 `PM()`

```js
function PM(e){
  let t = e?.userAgentData;
  if(!e || t==null) return "absent";
  let n = (t.brands||[]).filter(合法 brand);
  if(n.length===0) return "empty";
  let r = P_(e.userAgent);                 // 从 UA 解析 Chromium 主版本
  return r!==void 0 && n.some(b => b.brand==="Chromium"
      && parseInt(b.version,10)===r) ? "match" : "mismatch";
}
```

**判据**：`UA 里的 Chrome 主版本` 必须**等于** `navigator.userAgentData.brands` 中 `Chromium` 的 `version` 主版本。
→ 只改 UA 字符串、不改 Client Hints（或反之）= `mismatch`，**直接暴露**。

#### ⑤ 视口恒等 `q1()`

```js
function q1(e){
  let {innerWidth:t, innerHeight:n} = e;
  return typeof t=="number" && typeof n=="number" && t>0 && n>0
      && e.screen?.width===t && e.screen?.height===n;
}
```

`screen.width === innerWidth && screen.height === innerHeight` → true = 无头/固定视口。

#### ⑥ 加载时隐藏 `hidden_at_load`

```js
var VD = document.visibilityState === "hidden";
var u3 = VD || (Yl()==="hidden" && znb()===null);
// Yl()：PerformanceObserver 的 visibility-state 条目
// znb()：performance.getEntriesByType("navigation")[0].activationStart
```

即：**页面一加载就是隐藏的，且不是正常的预渲染激活** → 后台加载特征。

#### ⑦ 客户端内运行检测

```js
function fg(){ return sl({
  userAgent: navigator.userAgent,
  hasClaudeAppBindings: !!window.claudeAppBindings,   // ← 是否在 Claude 客户端内
  pathname: window.location.pathname
}); }
```

#### ⑧ 错误堆栈归因（隐私清洗）

```js
function WH(e){ return e.includes("@") ? e.endsWith("[native code]") || /:\d+:\d+$/.test(e.slice(-32)) : false }
var JQ = "[redacted-third-party]";
function Mm(e,t,n){ if(e.includes("[native code]")) return; ... return "bundle"/"external"/"anonymous" }
```

Sentry 上报前会把第三方堆栈抹成 `[redacted-third-party]`。这是**隐私保护**，但也说明平台能区分"错误发生在自家 bundle 还是外部注入脚本"——**任何注入到页面里的第三方脚本，其堆栈都会被单独归类**。

#### ⑨ 完整性设施

`nonce` 151 处（CSP nonce）、`integrity` 19 处（SRI）、`subresource`、`Content-Security-Policy`。CSP 会拦截并上报未授权脚本——**扩展注入的脚本如果违反 CSP，本身就是一条可观测事件**。

### 2.10 第三方 SDK 排查：全部阴性（E1）

对 178 个 bundle 做关键词排查：

| SDK | 命中 | 结论 |
| :--- | ---: | :--- |
| FingerprintJS | 0 | 无第三方指纹库 |
| Forter / Riskified / Signifyd | 0 | 无第三方风控评分 |
| Kasada / PerimeterX / DataDome | 0 | 无 WAF 型 bot 管理 |
| Arkose / FunCaptcha / Turnstile | 0 | 人机验证只用 hCaptcha |
| Persona / Sumsub / Onfido | 0（`withpersona` 为假阳性） | 无第三方 KYC |
| Cloudflare | 3 | JSD 挑战脚本 |
| Stripe | 12 | 支付，非风控 |

> **结论**：Anthropic 的风控是**自研浅层采集 + hCaptcha + Cloudflare** 三件套，没有引入任何第三方设备指纹厂商。这意味着：**不存在"第三方指纹黑盒"**，你能看到的就是全部——这对防御方是极好的消息。

### 2.11 完整判定流水线（把上面串起来）

```js
// ① 模块加载时一次性求值并缓存
var es = tY(navigator.userAgent)          // ua_form
var QB = PM(navigator)                    // ua_client_hints
var bz = hz(navigator)                    // automation_signal
var fx = bz !== null                      // is_automation
var VD = document.visibilityState==="hidden"
var u3 = VD || (Yl()==="hidden" && znb()===null)   // hidden_at_load

// ② 绑定为全局遥测上下文
FOz("hidden_at_load", u3)
FOz("is_automation", fx)
bz !== null && FOz("automation_signal", bz)
FOz("ua_form", es)
FOz("ua_client_hints", QB)
FOz("screen_equals_viewport", hi())

// ③ 之后每一条遥测都自动携带
{ ...事件, app_version: is(), platform: y3(), first_party_host: n2(),
  is_automation: fx, ...bz!==null && {automation_signal: aB(bz)},
  ua_form: aB(es), ua_client_hints: aB(QB), screen_equals_viewport: hi() }
```

→ 与 §2.3 从 HAR 里实测到的 `HealthMetricEvent` 字段**完全对应**。代码 → 流量 → 服务端判定，闭环验证成功。

---

## 3. 桌面端探针面（E1/E2 实测，app.asar 静态逆向）

对象：`/Applications/Claude.app`，`@ant/desktop` **2.42304.0**，Electron（Node ≥22），asar 500 文件 / 72 MB，解包 42 MB / 460 文本文件。

### 3.1 `ant-did`：安装级设备身份

实测（`.vite/build/index.chunk-DX8d9Lyh.js`、`index.chunk-muI2IV6k.js`、`index.pre.js`）：

```js
const W = "ant-did";                       // 文件名常量
const T = /^[0-9a-f]{8}-[0-9a-f]{4}-[…]$/i; // UUID 格式校验
lstatSync(e); if (!isFile() || nlink > 1) throw "ant-did is not a plain file";  // 反硬链接
rmSync(e);                                  // 非法则删除重建
const t = randomUUID(); try { write(e, t) } catch (e) { if (e.code === "EEXIST") read(); }
```

- 位置：`<userData>/ant-did`（macOS `~/Library/Application Support/Claude/`）；
- 生成：首次需要时 `crypto.randomUUID()`，**与登录无关**；
- 防护：普通文件校验、硬链接数 >1 拒绝、`EEXIST` 竞态重读、非法内容删除重建（极端回退全零 UUID）；
- 传播（E3 公开资料 + E2 代码吻合）：Sentry `user.id`、一方事件 `install_id`、更新检查 URL `device_id=<uuid>`、诊断包 `installId`、CLI 子进程 `sha256(ant-did)` 作为 `userID`。

### 3.2 遥测双通道与事件族

实测：

```js
endpoints: [
  {host: anthropicHost, path: "/api/event_logging/", origin: "renderer",   purpose: "claude_ai_web"},
  {host: …,             path: "/api/event_logging/", origin: "subprocess", purpose: "Claude Code usage telemetry"}
]
POST ${base}/api/event_logging/v2/batch   // "[EventLogging] Flushing %d events"
```

- 与网页端**同一端点**，但 `x-service-name` 为桌面端标识；
- 事件族实测：`desktop_ccd_turn_scope`、`desktop_ccd_host_keep_awake`、`desktop_ccd_btw_child_open/close`、`desktop_ccd_chrome_import`、`desktop_ccd_below_boundary_symlink_refused`、`desktop_ccd_hardlinked_file_read`；
- 另有 `/api/account/cowork/session_deletions`（Cowork 会话删除事件，**不受 nonessential 开关约束**）。

### 3.3 跨端关联：一条 cookie + 一个实验事件

实测：

```js
e.SEGMENT_ANONYMOUS_ID = "ajs_anonymous_id";
e.ANALYTICS_SESSION_ID = "analytics_session_id";
e.SEGMENT_CROSS_DOMAIN_ANONYMOUS_ID = "_cross_domain_anonymous_id";
// 桌面端写入 claude.ai 域：
cookies.set({url: …, name: "_cross_domain_anonymous_id", value: r,
             path: "/", httpOnly: false, secure: true, sameSite: "lax",
             expirationDate: now + 31536e3 /* 1 年 */});
// GrowthBook 实验曝光：
{event_type:"GrowthbookExperimentEvent", event_data:{
  device_id: await get("anthropic-device-id", e),
  anonymous_id: await get("ajs_anonymous_id", e),
  timestamp, experiment_id, variation_id, environment:"production"}}
```

**判读**：桌面端与网页端共享 `_cross_domain_anonymous_id` 与 `ajs_anonymous_id`，再叠加 `ant-did` 与 `anthropic-device-id`，形成**至少四条可交叉验证的跨端标识**。所谓"网页端干净、桌面端随便"的策略在关联图谱上不成立。

### 3.4 环境指纹字段白名单（遥测 schema 实测）

```
app_version, commit_hash, platform, arch,
os_version, os_pretty_name, os_release, os_build,
linux_distro_id, linux_distro_version_id, linux_session_type, linux_desktop_environment,
cpu_model, app_session_id, organization_id,
vm_network_mode, nest_local_user,
error_code, error_kind, backend_error_code
```

- **`vm_network_mode` / `nest_local_user`**：虚拟机网络模式与"嵌套本地用户"——**明确为虚拟化/多开环境设计的检测字段**；
- `cpu_model` + `total_memory` + `os_version` 组合近似硬件指纹（macOS 上 `hw.model` 可区分机型）；
- `app_session_id` 区分进程生命周期，便于识别"高频重启/脚本拉起"。

### 3.5 反伪造归一化（遥测写入前的清洗）

实测：

```js
device_id:  e => e === undefined ? undefined
             : (typeof e === "string" && UUID_RE.test(e)) ? e : "<non-uuid>"
cf_ray:     e => e === … ? e : "<non-cf-ray>"
install_id / deployment_organization_uuid / source_organization_uuid /
account_uuid / hipaa_origin_organization_id: 统一 UUID 归一化
```

**含义**：服务端拿到的是"已标注合法性"的字段。一个格式异常的设备 ID 不会被丢弃，而是以 `<non-uuid>` 形式**显式上报**——伪造 ID 反而制造了一个明确的负面信号。

同理 `device_id_kind: canonical | invalid`（`.vite/build/index.chunk-DDab7kkB.js`）与 `bound_device_id` 规范化相等校验，说明"设备绑定"是双向验真的。

### 3.6 CCD 文件系统边界探针（桌面端独有）

实测事件：`desktop_ccd_below_boundary_symlink_refused`、`desktop_ccd_hardlinked_file_read`、`desktop_ccd_chrome_import{stage, browser, sites}`、`desktop_ccd_turn_scope`、`desktop_ccd_host_keep_awake`、`desktop_ccd_btw_child_open/close`。

判读：这是 Cowork/CCD 能力在执行本地文件操作时的**安全与完整性事件**——符号链接越界、硬链接读取都会被单独记录并上报。它既是安全防护，也是"这个客户端是否在异常目录结构里运行"的信号。

### 3.7 macOS TCC 权限探针

实测：`tccState`、`tcc_not_granted`、`ensureOsPermissions()`、`accessibility`、`screenRecording`、`cu_watch_record_permission_blocked`、`desktop_ccd_host_keep_awake`。

判读：客户端读取辅助功能/录屏权限状态并在权限被拒时上报事件。**权限组合也是环境画像**（例如"有录屏权限但从不录制"与"无权限"在行为上不同）。

### 3.8 凭据与本地存储

实测：`safeStorage`（139 次）、`encryptString/decryptString`、`keychain`（37 次）、`deriveBrowserSafeStorageKey`、`os_crypt`、`v10` 前缀。

- 桌面端用 Electron `safeStorage`（macOS 上即 Keychain）加密 token；
- `deriveBrowserSafeStorageKey` 用于**读取 Chrome 的 Safe Storage**（浏览器数据导入场景）——这是账号关联的高风险入口：导入 Chrome 数据等于把 Google 账号、cookie、密码库一并纳入关联面。

### 3.9 桌面端 hCaptcha 门（与网页端同源）

实测开关族：

```
claude_ai_login_hcaptcha_frontend_enabled
claude_ai_popup_google_auth_hcaptcha_sitekey
claude_ai_accept_invite_hcaptcha_sitekey
claude_ai_org_join_hcaptcha_sitekey
claude_ai_delete_account_hcaptcha_sitekey
labs_url_verification_hcaptcha…
claude_ai_payments_hcaptcha_desktop_enabled
```

判读：Google 登录弹窗、接受邀请、加入组织、删号、labs URL 验证、桌面支付——**全部设有人机证明门**。这些门在生产环境是否开启由 GrowthBook 下发，因此"某个入口当时没弹验证"不代表没有判定面。

### 3.10 遥测开关矩阵（实测实现）

```js
// 真实判决函数
function Tte() {
  if (process.env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC) return "essential-traffic";
  if (process.env.DISABLE_TELEMETRY || isTruthy(process.env.DO_NOT_TRACK)) return "no-telemetry";
  return "default";
}
// 托管配置（readers: ["desktop","code"], scopes: ["3p"], availableInVersion: "1.2581.0"）
disableEssentialTelemetry / disableNonessentialTelemetry
// 特性开关
DISABLE_GROWTHBOOK, CLAUDE_CODE_MODEL_CATALOG
```

要点：

- `DISABLE_TELEMETRY` 在**桌面主进程不是一等公民**（子代理资料：0 命中于 Desktop 主进程），真正生效的是托管配置 `disableEssentialTelemetry` / `disableNonessentialTelemetry`；
- `disableNonessentialTelemetry` 只覆盖 "anthropic-telemetry" 一类端点，**Cowork 会话删除、更新检查不受其约束**；
- 环境变量白名单另含 `DISABLE_ERROR_REPORTING`、`DISABLE_FEEDBACK_COMMAND`、`ENABLE_TOOL_SEARCH`、`MAX_MCP_OUTPUT_TOKENS` 等。

结论：**"关遥测"只能减少非必要行为数据，不会关掉身份与更新检查**。把"关遥测"当成隐身手段是误解。

### 3.11 更新检查与设备绑定

实测：

```js
`device_id=${encodeURIComponent(getDeviceId())}&version=…&os_version=…`
```

——`ant-did` 以**明文 query 参数**出现在更新检查 URL 中，与登录无关、不可关闭（受托管配置约束）。

### 3.12 IPC 与权限边界（REA 实测）

REA 对 `app.asar` 做静态重建（`analyze-javascript-application`，7,319,048 个 AST 节点、430 个 JS 源、0 解析失败）：

| 指标 | 值 | 判读 |
| :--- | ---: | :--- |
| `browser_windows` | 3 | 主窗/快速窗/侧窗 |
| `context_bridge_apis` / `exposed_api_members` | 52 / 37 | renderer 可见的权限面 |
| `ipc.operations` | 1531 | 总 IPC 操作 |
| `ipc.literal_channels` | 9 | **仅 9 个字面量通道** |
| `ipc.dynamic_channel_operations` | 1522 | 其余 99% 为动态拼接 |
| `ipc.renderer_transmissions` / `renderer_listeners` | 1300 / 231 | 发送 / 监听 |
| `sender_validation_observations` | 56 | 主进程校验 renderer 来源的痕迹 |
| `native_addon_bindings` | 0 | 原生插件绑定在 `.unpacked`，未计入静态图 |

要点：

- 通道名被**刻意参数化**（1522 个动态构造），静态字符串检索无法穷举 IPC 面；
- 56 处 sender 校验说明主进程不信任 renderer 传入的 `event.senderFrame`；
- 52 个 contextBridge API 是"渲染进程能触达的能力清单"，也是本地能力的实际边界。

---

## 4. 判定链路重建（综合 E1–E4）

```
[连接层] Cloudflare
  ├─ TLS/JA4、HTTP2 指纹、IP 信誉/ASN/地区
  └─ JSD 非交互挑战（challenge-platform/scripts/jsd）
        │
[入口层] bootstrap / app_start
  ├─ 403 或 200 → 是否降级 /restricted
  └─ 下发 GrowthBook 开关（含 hCaptcha sitekey 与是否启用）
        │
[证明层] Client Attestation (hCaptcha invisible)
  ├─ visibility / focus / hiddenSinceAsk / mintWaitMs / reuseHeldToken
  ├─ account_switched 检测
  └─ 覆盖：login / signup / delete / key-create / org-join / payments / magic-link / appeal
        │
[身份层] anthropic-device-id + anonymous-id + activity-session-id
  ├─ 跨端：_cross_domain_anonymous_id + ant-did + ajs_anonymous_id
  └─ 归一化：<non-uuid> 标记
        │
[行为层] interaction_histogram（200/500/1000ms 分桶）
        │
[状态层] /api/account/standing
  ├─ standing / banned_at / ban_category / banned_orgs[]
  ├─ restricted_hcaptcha_mode
  └─ review_eta_days=10 → 申诉窗口
```

每一层都能独立触发降级；账号层再做**组织级连坐**与**跨端图谱合并**。

---

## 5. 环境一致性方案（本报告的核心交付）

> **目标**：让设备处于「真实、自洽、稳定」的状态——不是伪装成另一个环境，而是**把真实环境调理到没有矛盾**。
> **原则**：一致性 > 伪装度，隔离 > 清理，少改 > 多改，稳定 > 完美。

### 5.1 先明确：这五类"归一化器"绝对不能碰

| 探针 | 平台函数 | 触碰后果 |
| :--- | :--- | :--- |
| `ua_client_hints` | `PM()` | 改 UA 不改 Client Hints（或反之）→ `mismatch` |
| `ua_form` | `tY()` + `kD` | 版本后三段非 `.0.0.0` → `unreduced_version`；平台串不在白名单 → `unreduced_platform` |
| `screen_equals_viewport` | `q1()` | 强改 `screen`/`innerWidth` 造假 → 与其他窗口指标矛盾 |
| `device_id_kind` / `<non-uuid>` | 归一化器 | 伪造 device id → 显式标记为非法 |
| `is_automation` / `automation_signal` | `hz()` | 任何伪装成 bot/headless 的 UA 会被直接命中 |

**共同点**：这五个不是"值采集器"，而是**一致性校验器**。它们不关心你的值是什么，只关心**你的值彼此是否对得上**。
所以对付它们的唯一正解是：**别制造矛盾**，而不是"再改一个值去圆前一个谎"。

### 5.2 一致性体检工具（当场可用）

**[tools/web/consistency-audit.html](tools/web/consistency-audit.html)** —— 单文件、纯本地、不写 Cookie、不上传数据。

用法：

1. 双击用 Chrome 打开（或拖进 Chrome 窗口）；
2. 立刻看到六项核心判定 + 全部静默采集字段；
3. 点「检查出口 IP / 地区」拉一次公开 IP 库，生成时区/语言/地区三方一致性矩阵。

判定引擎是**从 bundle 里逆向移植过来的**，与平台同源：

| 工具显示字段 | 对应平台函数 | 期望值 |
| :--- | :--- | :--- |
| `ua_form` | `tY()` | `reduced` |
| `ua_client_hints` | `PM()` | `match` |
| `screen_equals_viewport` | `q1()` | `false` |
| `is_automation` / `automation_signal` | `hz()` | `false` / `null` |
| `hidden_at_load` | `VD` + `znb()` | `false` |

**已验证**：用 headless Chrome 打开时，工具准确输出 `automation_signal: ua_headless` 并标红（评分 50），非 headless 浏览器则全绿——说明判定逻辑与平台一致。

### 5.3 一致性自检矩阵（每次环境变更后跑一遍）

| 维度 | 检查项 | 通过判据 | 修正方式 |
| :--- | :--- | :--- | :--- |
| **UA 形态** | `ua_form` | 必须是 `reduced` | 别改 UA；用原版 Chrome |
| **Client Hints** | `ua_client_hints` | 必须是 `match` | 同上，且不要装改 UA 的扩展 |
| **视口** | `screen` vs `innerWidth` | 必须**不相等** | 窗口别开成整屏/无头尺寸 |
| 语言 | `navigator.language` / `Accept-Language` / 页面 locale / 输入法 | 四者同源 | 统一系统语言 + 浏览器语言 + 站点语言 |
| 时区 | 系统时区 / `Intl` / 出口 IP 时区 | 三者一致 | 改系统时区，而不是改浏览器 |
| 地区 | 出口 IP 国家 / `data-ion-ip-country` / 账号注册地 / 支付卡国家 | 一致或可解释 | 换出口，不要换身份 |
| 设备 | UA 主版本 / `Sec-CH-UA` / 实际浏览器 | 一致 | 不伪造 |
| 屏幕 | `screen.*` / 视口 / `devicePixelRatio` | 无矛盾组合 | 用真实分辨率 |
| 网络 | 出口 ASN 类型 / IP 跳变频率 / IPv6 / WebRTC 泄漏 | 住宅或移动、稳定、无泄漏 | 见 `playbooks/CURRENT_SETUP.md` |
| 身份 | 浏览器 profile 与账号 | 一 profile 一账号 | 隔离而非清理 |
| 桌面端 | `ant-did` 与 `anthropic-device-id` 的关系 | 明确、不制造矛盾 | 见 5.4 |

### 5.4 桌面端残留处置（隔离优先，清理其次）

1. **一账号一机一路径**：不为不同账号复用同一 `userData` 目录；
2. **换号前**确认 `ant-did` 与 `_cross_domain_anonymous_id` 是否已随旧账号绑定 —— 若旧账号被 `ban_category: other`，继续沿用同一安装 ID 等于**主动把新号接进旧图谱**；
3. **不要用"删 ant-did 文件"当常规手段**：代码里有 `lstat` / `nlink` 校验与重建逻辑，删除会被识别为"身份重置"；只在"彻底重装 + 全新环境"时做一次性处理；
4. Chrome Safe Storage 导入是高关联动作（`deriveBrowserSafeStorageKey` 可解密 Chrome 凭据），非必要不做；
5. 审计产物（`audit.jsonl`、`bridge-state.json`）是**本地明文**，含会话映射与全文，敏感环境不要留存。

### 5.5 遥测开关的正确理解

- 想减少非必要行为上报：用托管配置 `disableNonessentialTelemetry=true`；
- `DISABLE_TELEMETRY` / `DO_NOT_TRACK` 对桌面端覆盖有限，且 `DISABLE_TELEMETRY` 会连带影响 GrowthBook（有公开 issue 记录），可能触发"特性异常"而非"隐身"；
- **关遥测不能改变身份标识**：`ant-did`、`_cross_domain_anonymous_id`、更新检查 `device_id` 依然存在；
- 结论：把遥测开关当隐私 hygiene（减少暴露面），不要当风控规避手段。

### 5.6 注册与使用的实操顺序（对应"能正常注册和使用"）

**注册前**

1. 用体检工具跑一遍，**六项核心判定全绿**再动手；
2. 出口固定：一个住宅/移动 IP，国家与时区对齐，注册后**至少 24 小时不换**；
3. 浏览器：全新 profile，**不装任何改 UA / 改指纹 / 改 screen 的扩展**（平台不采这些，装了只会造矛盾）；
4. 语言三处对齐：系统语言、浏览器语言、站点 `locale`。

**注册时**

5. 别在"刚换出口的 10 分钟内"注册——新 IP 的信誉还没建立；
6. 注册全程**用一个窗口**，不要中途开关 DevTools（`outerWidth-innerWidth` 差值会变）；
7. 邮箱：用一个**没有历史**的邮箱，别和被封过的身份有任何关联（同域、同恢复邮箱都算）。

**使用中**

8. 保持同一出口、同一设备、同一浏览器 profile；
9. 桌面端与网页端**同一台机器、同一个网络**——`_cross_domain_anonymous_id` 会把它们缝在一起，跨网络反而是矛盾；
10. 不要短时间在多设备上同时登录新号。

**出事后**

11. **不要立刻原地开新号**——同一 `ant-did` / `device-id` / 出口会被图谱直接连回去；
12. 先做体检 → 换隔离环境（新 profile + 新出口 + 必要时新机器）→ 再考虑新号；
13. 用 `/api/account/standing` 的 `review_eta_days`（实测 10 天）判断申诉窗口。

### 5.7 可执行的检测脚本

```bash
# 1) HAR 探针面取证（只读源，输出脱敏）
python3 tools/scripts/audit_har_probes.py

# 2) 前端 bundle 四类探针扫描（静默/防御/攻击/遥测）
python3 tools/scripts/scan_web_probes.py scratch/web_assets output/web_analysis/web_probes.json

# 3) 桌面端 asar 只读解包（副本，不碰 /Applications）
cp "/Applications/Claude.app/Contents/Resources/app.asar" scratch/claude_desktop_asar/app.asar
python3 tools/scripts/extract_asar_readonly.py \
  scratch/claude_desktop_asar/app.asar scratch/claude_desktop_asar/extracted

# 4) 桌面端四类探针扫描
python3 tools/scripts/scan_web_probes.py scratch/claude_desktop_asar/extracted output/desktop_analysis/desktop_probes_v2.json

# 5) REA 静态重建（隔离安装，零后端，不执行目标代码）
./scratch/rea-toolchain/node_modules/.bin/rea analyze-javascript-application \
  "$PWD/scratch/claude_desktop_asar/app.asar" \
  --integrity-policy record-and-continue --json > scratch/rea-toolchain/out/app-evidence.json

# 6) 本机环境体检（浏览器打开，人眼看红绿）
open -a "Google Chrome" tools/web/consistency-audit.html
```

### 5.8 一句话策略

> 平台的全部反伪造设计都指向同一个判据：**你的答案是否彼此一致、是否跨端一致、是否随时间稳定**。
> 因此防御的最优解不是"更像真人"，而是**真的用一个一致的环境**——一账号、一设备、一出口、一套语言时区，然后**少动**。

---

## 6. 复现步骤（可审计）

1. 三份 HAR 放桌面，运行 `audit_har_probes.py` → 得到 §2 全部端点/头/事件/状态；
2. 复制 `app.asar` 副本 → `extract_asar_readonly.py` 解包（零依赖，兼容非标准 16 字节头）；
3. `scan_desktop_probes.py` 扫描 460 文本文件 / 3200 万字符 → 得到 §3 关键词面；
4. REA 隔离安装（`npm install --prefix scratch/rea-toolchain`）→ `analyze-javascript-application` 生成 Evidence；
5. 交叉核对公开资料（`B1anYu/claude-telemetry-audit`、pluto.security、cyberdom.blog）→ 标注 E3。

---

## 7. 开放问题

| # | 问题 | 现状 |
| :--- | :--- | :--- |
| 1 | `data-ion-ip-country` 之外，服务端还下发哪些判定结果？ | 只观测到国家/服务时间/clean-url-hop |
| 2 | hCaptcha token 的具体 server-side 评分权重？ | 不可观测 |
| 3 | `interaction_histogram` 是否进入封号判定，还是纯性能监控？ | 命名暗示性能（perf），但字段足以做行为判定 |
| 4 | 桌面端 `x-service-name` 的确切取值与事件名全量（公开资料称 722 个） | 需进一步提取事件名字面量 |
| 5 | `restricted_actions_hcaptcha_sitekey` 何时非 null？ | 本次为 null |
| 6 | 封禁是即时判定还是批量复核？`review_eta_days=10` 是 SLA 还是复核窗口？ | 未知 |
| 7 | 多端同时在线是否触发"设备数量"规则？ | 未观测到显式字段 |

---

## 附录 A · 证据索引

| 证据 | 位置 |
| :--- | :--- |
| 设备/匿名/会话 ID 一致性 | `output/har_analysis/summary.md` §2 |
| 探针请求头 | 同上 §3 |
| 端点命中 | 同上 §4 |
| 第三方域名 | 同上 §5 |
| 遥测事件原文 | `output/har_analysis/telemetry_events.json` |
| standing 响应 | `claude.ai-2.har` L27931–L27934 |
| HealthMetricEvent | `claude.ai-2.har` L52539 |
| attestation 引擎 | HAR 内联 JS（`client_attestation_engine`） |
| ant-did 实现 | `scratch/claude_desktop_asar/extracted/.vite/build/index.chunk-DX8d9Lyh.js` 等 |
| 环境指纹白名单 | 同上 `index.chunk-muI2IV6k.js` |
| 遥测开关 | 同上 `index.chunk-DNyequwM.js` / `index.chunk-muI2IV6k.js` |
| CCD 事件 | `index.chunk-B5tintml.js`、`index.chunk-1iyMx3P_.js`、`index.chunk-CDiepCgV.js` |
| 跨端 cookie | `index.chunk-muI2IV6k.js`（`_cross_domain_anonymous_id`） |
| 关键词扫描全表 | `output/desktop_analysis/probe_report.md` |
| 前端 bundle 四类探针命中表 | `output/web_analysis/web_probes.json` |
| 桌面端四类探针命中表 | `output/desktop_analysis/desktop_probes_v2.json` |
| 一致性体检工具 | `tools/web/consistency-audit.html` |

## 附录 B · REA 使用记录（实测，非引用）

- 版本：`rea-agents@6.7.0`，隔离安装于 `scratch/rea-toolchain/`（未写全局 npm、未动 `~/.npmrc`、未执行 `rea setup`——`setup` 会写用户级 dotfile，故跳过）；
- 约束：`analyze-javascript-application` 走静态 JS 通道，**不执行目标代码**，目标目录只读；产物写入 REA 自选临时目录；
- 参数：`--integrity-policy record-and-continue`（`--integrity-policy fail` 会因 `.asar.unpacked` 原生二进制签名哈希不匹配而中断）；
- `rea doctor` 结果：`healthy: false`，缺 Hopper / Ghidra / IDA / JADX —— **本任务不需要**，Electron/asar 走 JS 通道即可；
- 实际产出：

| 项 | 值 |
| :--- | :--- |
| Evidence 体积 | 218 MB（`scratch/rea-toolchain/out/app-evidence.json`） |
| `evidence_id` | 67 字符（封存哈希） |
| `relevant_files` / `parsed_javascript_files` | 454 / 430 |
| `skipped_javascript_files` / `parse_failures` | 6 / **0** |
| `visited_ast_nodes` | 7,319,048 |
| `findings` / `modules` | 9,294 / 72 |
| `integrity_contradictions` | **0** |
| `graph.nodes` / `edges` | 4,780 / 7,070 |
| `semantic_graph.nodes` / `relations` / `fingerprints` | 100,000 / 71,555 / 14,520 |

- **诚实标注的局限**：`limitations` 共 478 条，其中多数是 `Resource constraint … semantic analysis … was not started` —— 语义分析受节点预算约束，部分 `index.chunk-*.js` 只做了静态观测、未做完整语义重建。这意味着 §3 的探针结论来自"关键词面 + 关键文件精读 + REA 图统计"，**不是全量语义穷举**。
- REA 的价值定位：它给出的 IPC/contextBridge/sender-validation 边界（§3.12）是本报告唯一需要跨文件全局重建才能得到的结构，grep 无法替代。

---

> **合规声明**：本报告用于理解客户端遥测与风控信号、保护个人隐私与环境一致性。不构成对任何平台服务条款的规避指导；请遵守当地法律与平台政策。
