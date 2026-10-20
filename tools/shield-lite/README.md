# Shield Lite — 零足迹护盾（替代旧版 Claude Shield）

## 为什么退役旧版 Shield

旧版 `tools/extension/` 的三项设计在 2026 年的前端探针面前都是**自曝**：

| 旧设计 | 证据 | 后果 |
| :-- | :-- | :-- |
| `rules.json` 规则 3 强制改写 `Accept-Language: zh-TW` | 系统实际是 `zh_CN`；HAR 里 `accept-language` 出现 zh-CN / zh-Hant,zh-TW / zh-TW 三值混用 | 请求头与 `navigator.language` / `Intl` 时区本地化互相矛盾 |
| `inject.js`（59KB，MAIN world，all_frames） | 含 canvas `getImageData/toDataURL`、`WebGLRenderingContext`、`hardwareConcurrency`、`deviceMemory`、`webdriver` 遮蔽、`Function.prototype.toString` 改写 ×9、`defineProperty` ×18 | 反检测代码本身提高环境熵；`is_automation` / `document_gutted` / `ua_form` 正是抓这些 |
| 内容脚本覆盖 hCaptcha / Persona | `manifest.json` 的 `content_scripts` 匹配 `*.hcaptcha.com`、`*.withpersona.com` | 在第三方验证 iframe 内注入 → 验证链路污染，申诉/支付场景高危 |

## Shield Lite 做了什么

- **零内容脚本**：不向任何页面注入 JS，`document_gutted` 的扩展 URL 计数保持 0。
- **零请求头改写**：`Accept-Language` / `Referer` / `User-Agent` 全部交给系统与浏览器。
- **零指纹 Hook**：不碰 canvas / WebGL / audio / 硬件参数。
- **唯一功能**：`chrome.privacy.network.webRTCIPHandlingPolicy = disable_non_proxied_udp`。

## 什么时候可以完全不用它

启动参数已包含：

```
--force-webrtc-ip-handling-policy=disable_non_proxied_udp
```

（`tools/scripts/launch_isolated_chrome_tw.sh` 默认带了这一条）

则**不需要安装任何扩展**。零扩展是最干净的形态——因为「你的浏览器上装了什么」本身也在被观测。

## 临时加载方式

```
chrome://extensions → 打开「开发者模式」→ 加载已解压的扩展程序 → 选择 tools/shield-lite
```

仅建议在无法使用启动参数的场景（例如必须用日常 Chrome 实例）下临时使用；正式环境请用零扩展启动脚本。

## 自查

```js
// 页面控制台
chrome.privacy.network.webRTCIPHandlingPolicy.get({}, r => console.log(r.value));
// 期望：disable_non_proxied_udp
```

或访问 `chrome://webrtc-internals`，确认 ICE 候选中没有本地/真实公网地址。
