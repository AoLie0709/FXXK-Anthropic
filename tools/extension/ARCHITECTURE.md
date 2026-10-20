# 运行时伪装层：Claude Shield 扩展架构与高级反指纹工程

> **所属防线**: **Tier 3 - Runtime Cloaking & Anti-Fingerprinting**  
> **核心组件**: 本项目 `extension/` 目录源码 (Claude Shield v1.2.1 Stealth Edition)  
> **核心使命**: 抹平浏览器前端 JavaScript 与 DOM 层的指纹特征，对抗 Cloudflare Turnstile 启发式扫描与 WebRTC 穿透探针。

---

## 📑 目录

1. [扩展架构全景图 (Manifest V3 Stealth Edition)](#1-扩展架构全景图-manifest-v3-stealth-edition)
2. [毫秒级出口网络感知与动态时区对齐](#2-毫秒级出口网络感知与动态时区对齐)
3. [原生函数防篡改与 `[native code]` 原生签名保持](#3-原生函数防篡改与-native-code-原生签名保持)
4. [原型链层级 Navigator 隔离机制](#4-原型链层级-navigator-隔离机制)
5. [安全离屏 Canvas 微噪与 Apple M2 视网膜硬件仿真](#5-安全离屏-canvas-微噪与-apple-m2-视网膜硬件仿真)
6. [WebRTC 深度阻断与 SDP 候选清洗](#6-webrtc-深度阻断与-sdp-候选清洗)
7. [网络底层 Referer 与 Tracking 参数剥离](#7-网络底层-referer-与-tracking-参数剥离)

---

## 1. 扩展架构全景图 (Manifest V3 Stealth Edition)

`extension/` 严格遵循 Google Chrome Manifest V3 现代扩展规范构建：

```
extension/
├── manifest.json         # MV3 声明文件，申请最小必要权限 (declarativeNetRequest, privacy, storage)
├── background.js         # Service Worker，负责后台 IP/时区三级探测、热广播与 WebRTC 策略配置
├── content.js            # 内容脚本，在 document_start 阶段将 inject.js 注入到页面主世界
├── inject.js             # 核心注入层，直接接管页面 JS 运行时原型链 (Date, Intl, Canvas, WebGL, WebRTC)
├── rules.json            # 声明式网络请求规则 (DNR)，在底层网络栈剥离 Referer 与追踪标记
├── popup.html / js / css # 用户交互控制台，支持自动对齐与固定时区切换
└── icons/                # 扩展图标资产
```

---

## 2. 毫秒级出口网络感知与动态时区对齐

很多用户在使用 VPN 或代理时，节点可能在不同国家或城市之间切换。传统硬编码插件会导致「节点已切换至东京，但浏览器 Date 依然返回洛杉矶」，瞬间触发时区与 IP 不一致报警。

### 三级冗余智能感知流程
`background.js` 内置高可用冗余网络探测机制：
1. **Tier 1 (首选)**: 向 `https://ipwho.is/` 发起轻量 JSON 探测，提取 IANA 标准时区（如 `Asia/Taipei`）、国家代码与城市。
2. **Tier 2 (备用)**: 降级调用 `https://freeipapi.com/api/json`。
3. **Tier 3 (兜底 CDN 边缘)**: 向 `https://1.1.1.1/cdn-cgi/trace` 获取 Cloudflare 边缘节点代码（Colo Airport Code），内置映射表将 `SJC/LAX` 自动归类为 `America/Los_Angeles`，`TPE` 归类为 `Asia/Taipei`，`NRT/KIX` 归类为 `Asia/Tokyo`。

探测完成后，Service Worker 通过 `chrome.tabs.sendMessage` 向正在运行的 Claude 标签页广播新环境配置，前端无感毫秒级完成时区与语言对齐。

---

## 3. 原生函数防篡改与 `[native code]` 原生签名保持

### 为什么朴素的 JavaScript Hook 会被瞬时识破？
Cloudflare Turnstile 与 CreepJS 等现代化反指纹检测库，会检查被 Hook 函数的字符串表示：
```javascript
// 朴素的篡改方式：
Date.prototype.getTimezoneOffset = function() { return -480; };

// 此时风控脚本运行测试：
console.log(Date.prototype.getTimezoneOffset.toString());
// 输出: "function() { return -480; }"  <-- 致命漏洞！真实浏览器必须输出 "[native code]"！
```

### Claude Shield 的闭包 WeakMap 防御方案
在 `inject.js` 中，扩展重写了 `Function.prototype.toString`，并通过弱引用 Map 映射所有被接管的方法：
```javascript
const nativeToString = Function.prototype.toString;
const hookedFunctions = new WeakMap();

function registerNativeHook(hookedFn, originalFn, customName) {
  const name = customName || originalFn.name;
  hookedFunctions.set(hookedFn, `function ${name}() { [native code] }`);
  return hookedFn;
}

Function.prototype.toString = function() {
  if (hookedFunctions.has(this)) {
    return hookedFunctions.get(this);
  }
  return nativeToString.call(this);
};
// 保证 Function.prototype.toString 自身的 toString 也返回原生签名
hookedFunctions.set(Function.prototype.toString, 'function toString() { [native code] }');
```
经过此加固，无论 Turnstile 如何调用 `.toString()` 或检查原型链，均严格返回 ECMAScript 规范的原生方法体，彻底消除篡改特征。

---

## 4. 原型链层级 Navigator 隔离机制

自动化爬虫与劣质插件往往直接在 `window.navigator` 实例上覆写属性：
```javascript
// 错误写法：
Object.defineProperty(navigator, 'language', { value: 'zh-TW' });
// 漏洞特征：
navigator.hasOwnProperty('language') === true; // 原生浏览器中该属性位于原型链，自身应为 false！
```

Claude Shield 将所有伪装属性严格挂载在 `Navigator.prototype` 上：
```javascript
const navProto = Object.getPrototypeOf(navigator);
Object.defineProperties(navProto, {
  language: { get: () => currentConfig.language, configurable: true, enumerable: true },
  languages: { get: () => currentConfig.languages, configurable: true, enumerable: true },
  webdriver: { get: () => false, configurable: true, enumerable: true }
});
// 检验：
navigator.hasOwnProperty('language'); // 恒为 false，与纯净原生浏览器 100% 行为一致
```

---

## 5. 安全离屏 Canvas 微噪与 Apple M2 视网膜硬件仿真

### 栈溢出修复（无递归死循环）
早期指纹伪装插件在 Hook `toDataURL` 和 `toBlob` 时，常在内部再次调用 `this.toDataURL()`，导致在高频绘图应用中触发 `Maximum call stack size exceeded` 报错崩溃。

Claude Shield 严格缓存原始原生函数的引用 `origToDataURL`，通过在隔离的内存离屏画布中对像素点引入不可见（$\pm 1$ 色阶微幅扰动）的微噪，在不破坏页面图像渲染真实度的同时，破坏画布哈希指纹的跨站聚合能力。

### WebGL 视网膜渲染器仿真
接管 `WebGLRenderingContext.prototype.getParameter`：
- `UNMASKED_VENDOR_WEBGL` -> `Apple Inc.`
- `UNMASKED_RENDERER_WEBGL` -> `Apple M2`
模拟真实高质量 macOS 设备的图形环境。

---

## 6. WebRTC 深度阻断与 SDP 候选清洗

WebRTC 是导致真实公网 IP 或局域网内网拓扑外泄的最高危途径。

### 双重阻断模型
1. **浏览器底层隐私策略**：
   在 `background.js` 中调用：
   ```javascript
   chrome.privacy.network.webRTCIPHandlingPolicy.set({
     value: 'disable_non_proxied_udp'
   });
   ```
   强制 Chrome 禁用非代理直连的 UDP 绑定。
2. **SDP / ICE 候选运行时清洗**：
   在 `inject.js` 中代理 `RTCPeerConnection.prototype.createOffer` 与 `addIceCandidate`，深度过滤：
   - 私网 IPv4 (`10.x.x.x`, `192.168.x.x`, `172.16.x.x`)
   - 所有全量 IPv6 与零压缩 IPv6 地址（如 `240e:...`, `fe80:...`, `::1` 等）
   - Host 候选，仅允许已认证的代理中继候选（Relay Candidate）通过。

---

## 7. 网络底层 Referer 与 Tracking 参数剥离

### Declarative Net Request (DNR) 标头清洗
在 `rules.json` 中配置原生网络层规则，对于向 `claude.ai` 和 `anthropic.com` 发起的请求：
- 剥离外站来源的 `Referer` 标头，防止第三方国内邮箱或搜索引擎 URL 泄漏；
- 瞬时剥离 URL Query 中附带的追踪标记（如 `utm_source`, `utm_medium`, `fbclid`, `gclid`, `_hsenc` 等），防止因携带脏追踪 ID 触发历史风控连带处罚。

---

## 8. 纯内存隔离与 WebIDL 原型保全 (零 LocalStorage 污染 & 零 Storage 原型篡改)

早期防指纹脚本常见的致命缺陷是在目标域名的 `localStorage` 中持久化扩展数据，并通过篡改 `Storage.prototype.getItem`、`key` 和 `length` 试图掩盖。

### 为什么必须坚决杜绝篡改 `Storage.prototype`？
1. **Turnstile 原型链审计**：现代反爬虫引擎会深度探测 `Object.getOwnPropertyDescriptor(Storage.prototype, 'key')`，篡改原生 WebIDL 原型会导致不可消除的特征暴露；
2. **读写行为不一致特征**：如果 `localStorage.getItem('__c_shld_s__')` 返回 `null`，但通过属性访问 `localStorage['__c_shld_s__']` 仍能取到值，此种状态不一致是风控系统判定「浏览器环境受篡改」的绝佳启发式依据；
3. **索引偏移死循环风险**：在 `Storage.prototype.key(i)` 中进行索引过滤极易引入 Off-by-one 键名重复 Bug。

### Claude Shield 的终极纯净解：
- **零存储污染**：扩展状态全生命周期驻留在 JavaScript 闭包内存中，绝不在目标域名 `localStorage` 写入任何配置；
- **零原型干预**：完全保留 `Storage.prototype` 100% 原生纯净度，不作任何 Hook；
- **隐形运行时加锁**：主世界防重入锁使用不可枚举的 `Symbol.for('__cs_runtime_active__')`，杜绝在全局 `window` 暴露明文属性特征。

