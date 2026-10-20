// Claude Shield Lite — 零足迹护盾
// 设计原则：
//   1. 不注入任何页面脚本（无 content_scripts / 无 MAIN world / 无原型链改写）
//   2. 不改写任何请求头（Accept-Language / Referer / UA 一律交给系统与浏览器原生逻辑）
//   3. 不做任何指纹 Hook 或噪声（canvas / WebGL / audio / 硬件参数全部保持原生）
//   4. 只使用浏览器级隐私 API：WebRTC 禁止非代理 UDP，防止本地/公网 IP 经 ICE 候选泄漏
// 如果启动参数里已使用 --force-webrtc-ip-handling-policy=disable_non_proxied_udp，
// 则本扩展可以完全不安装 —— 零扩展是最干净的形态。

const POLICY = 'disable_non_proxied_udp';

function applyWebRtcPolicy() {
  if (!chrome.privacy?.network?.webRTCIPHandlingPolicy) return;
  chrome.privacy.network.webRTCIPHandlingPolicy.set({ value: POLICY }, () => {
    if (chrome.runtime.lastError) {
      console.warn('[ShieldLite] WebRTC 策略设置失败:', chrome.runtime.lastError.message);
    } else {
      console.log('[ShieldLite] WebRTC 策略已生效:', POLICY);
    }
  });
}

chrome.runtime.onInstalled.addListener(applyWebRtcPolicy);
chrome.runtime.onStartup.addListener(applyWebRtcPolicy);

// 只保留一个可自查的状态读取入口，不采集任何环境信息
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg === 'status') {
    chrome.privacy.network.webRTCIPHandlingPolicy.get({}, (r) => {
      sendResponse({ webRTCIPHandlingPolicy: r.value });
    });
    return true;
  }
});
