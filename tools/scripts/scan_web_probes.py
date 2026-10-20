#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_web_probes.py — 对前端/桌面端 JS 做四类探针全量扫描。

四类：
  S 静默采集（silent）    —— 不打扰用户、后台悄悄读取的环境属性
  D 防御反篡改（defensive）—— 完整性校验、反调试、反 hook、原生函数校验
  A 攻击挑战（attack）    —— 人机验证、风控挑战、封禁/限制判定
  T 遥测上报（telemetry） —— 事件通道、第三方 SDK、标识符

用法：
  python3 tools/scripts/scan_web_probes.py <dir> [out_json]
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

GROUPS = {
    "S_silent": [
        # 硬件 / 性能
        "hardwareConcurrency", "deviceMemory", "performance.memory", "jsHeapSizeLimit",
        # 屏幕
        "availWidth", "availHeight", "colorDepth", "pixelDepth", "devicePixelRatio",
        "screen.orientation", "matchMedia",
        # 平台 / 语言
        "navigator.platform", "navigator.vendor", "maxTouchPoints", "doNotTrack",
        "cookieEnabled", "pdfViewerEnabled", "userAgentData", "getHighEntropyValues",
        # 网络
        "navigator.connection", "effectiveType", "downlink", "saveData", "rtt",
        # 外设
        "enumerateDevices", "mediaDevices", "getUserMedia", "getBattery", "battery",
        "speechSynthesis", "getVoices", "plugins", "mimeTypes",
        # 时区 / 日历
        "resolvedOptions", "timeZone", "numberingSystem", "hourCycle", "calendar",
        # 存储
        "indexedDB", "storage.estimate", "persist", "quota",
        # 图形 / 音频
        "WEBGL_debug_renderer_info", "UNMASKED_VENDOR_WEBGL", "UNMASKED_RENDERER_WEBGL",
        "getSupportedExtensions", "getShaderPrecisionFormat", "toDataURL", "getImageData",
        "OfflineAudioContext", "createOscillator", "createAnalyser", "measureText",
        "fonts.check", "font", "canvas",
        # 权限 / 位置
        "permissions.query", "geolocation", "Notification.permission",
    ],
    "D_defensive": [
        "integrity", "subresource", "sha384-", "sha256-", "nonce",
        "debugger", "prepareStackTrace", "captureStackTrace", "[native code]",
        "toString", "defineProperty", "getOwnPropertyDescriptor", "Object.freeze",
        "webdriver", "callPhantom", "domAutomation", "cdc_", "__selenium",
        "__playwright", "__puppeteer", "__nightmare",
        "outerWidth", "outerHeight", "console.profile", "console.clear", "Console",
        "Proxy", "Reflect", "MutationObserver", "crypto.subtle", "getRandomValues",
        "trustedTypes", "report-to", "report-uri", "Content-Security-Policy",
        "sandbox", "allow-scripts", "Cross-Origin-Opener-Policy",
        "timing", "Date.now", "performance.now", "setTimeout(fn", "requestAnimationFrame",
    ],
    "A_attack": [
        "hcaptcha", "attestation", "challenge", "turnstile", "recaptcha",
        "client_attestation", "AttestedSurface", "mint", "sitekey",
        "risk", "fraud", "abuse", "banned", "restricted", "suspicious", "anomaly",
        "rate_limit", "rateLimit", "too_many_requests", "captcha",
    ],
    "T_telemetry": [
        "event_logging", "statssig", "statsig", "growthbook", "datadog", "sentry",
        "segment", "amplitude", "beacon", "sendBeacon", "keepalive",
        "anonymous_id", "device_id", "session_id", "install_id", "user_id",
        "track(", "identify(", "page(", "capture(", "flush(",
    ],
    "B_behavior": [
        "mousemove", "pointerdown", "pointermove", "keydown", "keyup", "keypress",
        "visibilitychange", "focus", "blur", "beforeunload", "idle",
        "interaction", "histogram", "paste", "clipboard", "typing", "keystroke",
    ],
}

TEXT_EXTS = {".js", ".mjs", ".css", ".json", ".html"}
WINDOW = 100
MAX_CTX = 2
MAX_FILES_PER_KW = 4


def redact(t: str) -> str:
    t = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
               lambda m: m.group(0)[:8] + "-REDACTED", t)
    t = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", lambda m: m.group(0)[:2] + "***@" + m.group(0).split("@", 1)[1], t)
    return t


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    root = Path(argv[1]).resolve()
    out = Path(argv[2]) if len(argv) > 2 else Path("output/web_analysis/web_probes.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    hits = {}
    files = 0
    total_bytes = 0

    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        files += 1
        total_bytes += len(text)
        rel = str(p.relative_to(root))

        for group, kws in GROUPS.items():
            for kw in kws:
                idx = text.find(kw)
                if idx < 0:
                    continue
                e = hits.setdefault(kw, {"group": group, "count": 0, "files": {}})
                e["count"] += text.count(kw)
                store = e["files"].setdefault(rel, [])
                start = 0
                while len(store) < MAX_CTX:
                    i = text.find(kw, start)
                    if i < 0:
                        break
                    lo, hi = max(0, i - WINDOW), min(len(text), i + len(kw) + WINDOW)
                    store.append(redact(text[lo:hi].replace("\n", " ")))
                    start = i + len(kw)

    ordered = sorted(hits.items(), key=lambda kv: (kv[1]["group"], -kv[1]["count"]))
    payload = {
        "root": str(root), "files": files, "chars": total_bytes,
        "groups": {g: sum(1 for k, v in hits.items() if v["group"] == g) for g in GROUPS},
        "hits": {k: {"group": v["group"], "count": v["count"],
                     "files": {f: c for f, c in list(v["files"].items())[:MAX_FILES_PER_KW]}}
                 for k, v in ordered},
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 终端摘要
    print(f"files={files} chars={total_bytes:,} keywords_hit={len(hits)}")
    for g in GROUPS:
        ks = [(k, v) for k, v in hits.items() if v["group"] == g]
        print(f"\n== {g} ({len(ks)} kw) ==")
        for k, v in sorted(ks, key=lambda kv: -kv[1]["count"])[:25]:
            top = list(v["files"].items())[0]
            print(f"  {k:34s} {v['count']:6d}  {top[0][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
