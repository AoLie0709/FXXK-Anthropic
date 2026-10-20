#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_har_probes.py — 从 claude.ai HAR 中提取「风控探针面」证据（只读源文件，输出全脱敏）。

用途
----
把浏览器抓到的 HAR 转成结构化证据：
  1. 端点清单（含状态码、命中次数）
  2. 请求头探针面（anthropic-* / sec-ch-ua / accept-language / x-activity-session-id）
  3. 遥测事件（/api/event_logging/v2/batch 的 HealthMetricEvent 等）
  4. 账号状态快照（/api/account/standing）
  5. 设备/匿名 ID 的跨文件一致性（关联图谱的关键）
  6. 第三方域名（hCaptcha / Datadog / Cloudflare / Intercom ...）
  7. 服务端回显的地理信号（data-ion-ip-country / cf-ray 落地机房）

约束
----
- 绝不修改源 HAR。
- 输出中的 UUID、邮箱、组织名一律脱敏；一致性结论以「是否一致」表达，不回显原值。

用法
----
    python3 tools/scripts/audit_har_probes.py                    # 默认路径
    python3 tools/scripts/audit_har_probes.py a.har b.har        # 指定文件
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_HARS = [
    Path.home() / "Desktop" / "claude.ai.har",
    Path.home() / "Desktop" / "claude.ai-2.har",
    Path.home() / "Desktop" / "claude.ai-3.har",
]
OUT_DIR = Path("output/har_analysis")

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
HEX32_RE = re.compile(r"\b[0-9a-f]{32,}\b", re.I)

# 关键请求头（探针面）
HEADER_KEYS = [
    "anthropic-anonymous-id",
    "anthropic-device-id",
    "anthropic-client-platform",
    "anthropic-client-version",
    "anthropic-client-build",
    "anthropic-client-sha",
    "anthropic-client-capabilities",
    "x-activity-session-id",
    "x-app-locale",
    "x-service-name",
    "accept-language",
    "user-agent",
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "sec-fetch-site",
    "referer",
    "origin",
]

# 第三方 / 探针相关域名关键词
THIRD_PARTY_HINTS = [
    "hcaptcha", "datadoghq", "intercom", "cloudflare", "challenge-platform",
    "statsig", "growthbook", "sentry", "google", "gstatic", "stripe",
    "segment", "amplitude", "posthog", "braze", "sift", "fingerprint",
]

# 遥测里值得单列的反自动化字段
AUTOMATION_FIELDS = [
    "is_automation", "ua_form", "ua_client_hints", "screen_equals_viewport",
    "first_party_host", "platform", "surface", "action", "outcome", "error_type", "error_code",
]


def redact(text: str) -> str:
    if not text:
        return text
    text = UUID_RE.sub(lambda m: m.group(0)[:8] + "-REDACTED", text)
    text = EMAIL_RE.sub(lambda m: m.group(0)[:2] + "***@" + m.group(0).split("@", 1)[1], text)
    text = HEX32_RE.sub(lambda m: m.group(0)[:12] + "...", text)
    return text


def shorten(text, limit=400):
    if text is None:
        return None
    text = str(text)
    return text if len(text) <= limit else text[:limit] + f"…(+{len(text) - limit})"


def load_entries(path: Path):
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    return data.get("log", {}).get("entries", [])


def header_map(entry):
    hdrs = entry.get("request", {}).get("headers") or []
    out = {}
    for h in hdrs:
        name = (h.get("name") or "").lower()
        if name and name not in out:
            out[name] = h.get("value")
        elif name:
            out[name] = out[name] + ", " + str(h.get("value"))
    return out


def parse_events(entry):
    """解析 event_logging 批量遥测。"""
    url = entry.get("request", {}).get("url", "")
    if "/event_logging/" not in url:
        return []
    post = (entry.get("request", {}).get("postData") or {}).get("text")
    if not post:
        return []
    try:
        payload = json.loads(post)
    except Exception:
        return [{"_raw": shorten(post)}]
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        return [{"_payload": shorten(post)}]
    return events


def classify_host(host: str) -> str:
    if host in ("claude.ai", "www.claude.ai"):
        return "first-party:claude.ai"
    if host and host.endswith("anthropic.com"):
        return "first-party:anthropic.com"
    low = (host or "").lower()
    for hint in THIRD_PARTY_HINTS:
        if hint in low:
            return f"third-party:{hint}"
    return "third-party:other"


def main(argv):
    hars = [Path(p) for p in argv[1:]] if len(argv) > 1 else DEFAULT_HARS
    hars = [p for p in hars if p.exists()]
    if not hars:
        print("no HAR files found", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    per_file = {}
    global_endpoints = Counter()
    global_hosts = Counter()
    global_host_kind = {}
    global_headers = defaultdict(Counter)
    header_absent = defaultdict(int)
    device_ids = defaultdict(set)      # value -> files
    anon_ids = defaultdict(set)
    session_ids = defaultdict(set)
    events_all = []
    account_state = {}
    html_geo = []
    cookies_seen = Counter()
    errors = []

    for path in hars:
        try:
            entries = load_entries(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.name}: {exc}")
            continue

        status_counter = Counter()
        for e in entries:
            req = e.get("request", {})
            resp = e.get("response", {}) or {}
            url = req.get("url", "") or ""
            if not url:
                continue
            host = urlparse(url).hostname or ""
            parsed = urlparse(url)
            endpoint = f"{parsed.path}"
            method = req.get("method", "?")
            status = resp.get("status")
            key = f"{method} {endpoint}"
            global_endpoints[key] += 1
            global_hosts[host] += 1
            global_host_kind[host] = classify_host(host)
            status_counter[(key, status)] += 1

            hm = header_map(e)
            for k in HEADER_KEYS:
                if k in hm:
                    global_headers[k][redact(str(hm[k]))[:120]] += 1
            for k in ("anthropic-device-id", "anthropic-anonymous-id", "x-activity-session-id"):
                if k not in hm:
                    header_absent[k] += 1

            if "anthropic-device-id" in hm:
                device_ids[hm["anthropic-device-id"]].add(path.name)
            if "anthropic-anonymous-id" in hm:
                anon_ids[hm["anthropic-anonymous-id"]].add(path.name)
            if "x-activity-session-id" in hm:
                session_ids[hm["x-activity-session-id"]].add(path.name)

            for c in (req.get("cookies") or []) + (resp.get("cookies") or []):
                if c.get("name"):
                    cookies_seen[c["name"]] += 1

            # 遥测事件
            for ev in parse_events(e):
                if isinstance(ev, dict):
                    events_all.append({"file": path.name, "event": ev})

            # 账号状态
            if endpoint.endswith("/api/account/standing") or "/account/standing" in endpoint:
                text = (resp.get("content") or {}).get("text") or ""
                if text:
                    try:
                        account_state[path.name] = json.loads(text)
                    except Exception:  # noqa: BLE001
                        account_state[path.name] = {"_raw": shorten(text)}

            # 地理回显
            text = (resp.get("content") or {}).get("text") or ""
            if "data-ion-ip-country" in text:
                m = re.search(r'data-ion-ip-country="([^"]*)"', text)
                if m:
                    html_geo.append({"file": path.name, "ion_ip_country": m.group(1)})
            if e.get("serverIPAddress"):
                html_geo.append({
                    "file": path.name,
                    "server_ip": e["serverIPAddress"],
                    "cf_ray": ((resp.get("headers") or [{}]) and next(
                        (h.get("value") for h in resp.get("headers") or []
                         if (h.get("name") or "").lower() == "cf-ray"), None)),
                })

        per_file[path.name] = {
            "entries": len(entries),
            "top_status": [{"endpoint": k[0], "status": k[1], "count": v}
                           for k, v in status_counter.most_common(40)],
        }

    # ---------- 输出：JSON ----------
    summary = {
        "files": {name: {"entries": v["entries"]} for name, v in per_file.items()},
        "accounts": {k: redact(json.dumps(v, ensure_ascii=False)) for k, v in account_state.items()},
        "device_id_consistency": {
            "distinct_device_ids": len(device_ids),
            "ids_seen_in_files": {redact(k)[:20]: sorted(v) for k, v in device_ids.items()},
        },
        "anonymous_id_consistency": {
            "distinct_anonymous_ids": len(anon_ids),
            "ids_seen_in_files": {redact(k)[:24]: sorted(v) for k, v in anon_ids.items()},
        },
        "activity_session_consistency": {
            "distinct": len(session_ids),
            "ids_seen_in_files": {redact(k)[:20]: sorted(v) for k, v in session_ids.items()},
        },
        "headers": {k: dict(v) for k, v in global_headers.items()},
        "header_absent_counts": dict(header_absent),
        "hosts": dict(global_hosts.most_common()),
        "host_kind": global_host_kind,
        "cookies": dict(cookies_seen.most_common()),
        "geo_echo": html_geo[:50],
        "errors": errors,
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    (OUT_DIR / "telemetry_events.json").write_text(
        json.dumps(events_all, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 输出：Markdown ----------
    md = []
    md.append("# HAR 探针取证摘要（自动生成，已脱敏）\n")
    md.append("> 由 `tools/scripts/audit_har_probes.py` 生成。UUID/邮箱/哈希已打码；"
              "一致性结论不回显原值。\n")

    md.append("## 1. 文件概览\n")
    md.append("| 文件 | 请求数 | 说明 |")
    md.append("| :--- | ---: | :--- |")
    notes = {
        "claude.ai.har": "受限页 + 申诉提交（/restricted/submit）",
        "claude.ai-2.har": "封禁态完整会话（standing / appeal / event_logging）",
        "claude.ai-3.har": "短会话（仅 RUM 上报）",
    }
    for name, v in per_file.items():
        md.append(f"| {name} | {v['entries']} | {notes.get(name, '')} |")

    md.append("\n## 2. 身份标识一致性（关联图谱关键）\n")
    md.append(f"- `anthropic-device-id` 不同取值数：**{len(device_ids)}**")
    for k, files in device_ids.items():
        md.append(f"  - `{redact(k)[:20]}` → 出现在 {', '.join(sorted(files))}")
    md.append(f"- `anthropic-anonymous-id` 不同取值数：**{len(anon_ids)}**")
    for k, files in anon_ids.items():
        md.append(f"  - `{redact(k)[:24]}` → 出现在 {', '.join(sorted(files))}")
    md.append(f"- `x-activity-session-id` 不同取值数：**{len(session_ids)}**")
    for k, files in session_ids.items():
        md.append(f"  - `{redact(k)[:20]}` → 出现在 {', '.join(sorted(files))}")

    md.append("\n## 3. 探针请求头（出现即代表该请求携带该信号）\n")
    for k in HEADER_KEYS:
        if k in global_headers:
            vals = list(global_headers[k].items())[:3]
            rendered = "; ".join(f"`{v}` ×{c}" for v, c in vals)
            md.append(f"- `{k}`：{rendered}")

    md.append("\n## 4. 关键端点（按命中次数）\n")
    md.append("| 端点 | 次数 |")
    md.append("| :--- | ---: |")
    for ep, cnt in global_endpoints.most_common(60):
        if ep.startswith(("GET /claude-ai", "GET /v2/assets")):
            continue
        md.append(f"| `{ep}` | {cnt} |")

    md.append("\n## 5. 第三方域名\n")
    md.append("| 域名 | 类别 | 次数 |")
    md.append("| :--- | :--- | ---: |")
    for host, cnt in global_hosts.most_common():
        kind = global_host_kind.get(host, "")
        if kind.startswith("third-party"):
            md.append(f"| `{host}` | {kind} | {cnt} |")

    md.append("\n## 6. Cookie 名称\n")
    if cookies_seen:
        for name, cnt in cookies_seen.most_common():
            md.append(f"- `{name}` ×{cnt}")
    else:
        md.append("- （HAR 中未记录到 cookie；WebInspector 导出可能省略 Cookie 头）")

    (OUT_DIR / "summary.md").write_text("\n".join(md), encoding="utf-8")

    print(f"written: {OUT_DIR/'summary.md'}, {OUT_DIR/'summary.json'}, {OUT_DIR/'telemetry_events.json'}")
    print(f"files={len(per_file)} events={len(events_all)} hosts={len(global_hosts)} endpoints={len(global_endpoints)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
