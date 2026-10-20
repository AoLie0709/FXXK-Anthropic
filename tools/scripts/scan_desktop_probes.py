#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_desktop_probes.py — 对解包后的 Claude Desktop 代码做一次性探针面扫描。

输出（全部脱敏、只读源）：
  output/desktop_analysis/probe_hits.json   —— 每个关键词的命中文件/次数/上下文窗口
  output/desktop_analysis/probe_report.md   —— 人读汇总

用法：
  python3 tools/scripts/scan_desktop_probes.py <extracted_dir> [out_dir]
"""

import json
import re
import sys
from pathlib import Path

# 探针主题 → 关键词
KEYWORD_GROUPS = {
    "identity": ["ant-did", "device_id", "deviceId", "install_id", "installId",
                 "anonymous_id", "anonymousId", "machine_id", "machineId", "hardware_uuid"],
    "telemetry": ["event_logging", "/api/event_logging", "telemetry", "analytics",
                  "ProductAnalyticsEvent", "HealthMetricEvent", "install_id"],
    "error_reporting": ["sentry", "dsn", "ingest.", "breadcrumb"],
    "flags": ["growthbook", "statsig", "segment", "amplitude", "disableEssentialTelemetry",
              "disableNonessentialTelemetry", "DISABLE_TELEMETRY"],
    "attestation": ["attestation", "hcaptcha", "client_attestation", "challenge"],
    "automation": ["webdriver", "headless", "automation", "isAutomation", "puppeteer",
                   "playwright", "devtools"],
    "env_fingerprint": ["os_version", "osVersion", "arch", "cpu", "cpu_model",
                        "total_memory", "screen_", "display_", "timezone", "locale"],
    "secrets": ["safeStorage", "keychain", "encryptString", "decryptString", "os_crypt"],
    "fs_boundary": ["desktop_ccd_", "below_boundary", "hardlinkedFileRead", "symlink",
                    "file_index", "transcript", "audit.jsonl", "bridge-state"],
    "network": ["api.anthropic.com", "claude.ai/api", "device_id=", "update?",
                "downloads.claude.ai", "statsig.anthropic"],
    "permissions": ["accessibility", "screen_recording", "screenRecording",
                    "input_monitoring", "tcc", "AXIsProcessTrusted"],
}

TEXT_EXTS = {".js", ".mjs", ".cjs", ".json", ".plist", ".html", ".css", ".yaml", ".yml", ".txt", ".md"}
MAX_CONTEXTS_PER_KEYWORD = 12
WINDOW = 110


def redact(text: str) -> str:
    text = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                  lambda m: m.group(0)[:8] + "-REDACTED", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
                  lambda m: m.group(0)[:2] + "***@" + m.group(0).split("@", 1)[1], text)
    return text


def iter_text_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            yield p


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = Path(argv[1]).resolve()
    out_dir = Path(argv[2]) if len(argv) > 2 else Path("output/desktop_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)

    hits = {}
    files_scanned = 0
    bytes_scanned = 0

    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        files_scanned += 1
        bytes_scanned += len(text)
        rel = str(path.relative_to(root))

        for group, keywords in KEYWORD_GROUPS.items():
            for kw in keywords:
                if kw not in text:
                    continue
                entry = hits.setdefault(kw, {"group": group, "files": {}, "count": 0})
                entry["count"] += text.count(kw)
                store = entry["files"].setdefault(rel, [])
                if len(store) >= 3:
                    continue
                start = 0
                while len(store) < 3:
                    idx = text.find(kw, start)
                    if idx < 0:
                        break
                    lo = max(0, idx - WINDOW)
                    hi = min(len(text), idx + len(kw) + WINDOW)
                    store.append(redact(text[lo:hi].replace("\n", " ⏎ ")))
                    start = idx + len(kw)

    payload = {
        "root": str(root),
        "files_scanned": files_scanned,
        "bytes_scanned": bytes_scanned,
        "keywords": {k: {"group": v["group"], "count": v["count"], "files": v["files"]}
                     for k, v in sorted(hits.items(), key=lambda kv: -kv[1]["count"])},
    }
    (out_dir / "probe_hits.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# Claude Desktop 探针面扫描（自动生成，已脱敏）\n",
          f"- 扫描根目录：`{root}`",
          f"- 文本文件：{files_scanned}，累计字符：{bytes_scanned:,}\n",
          "## 关键词命中总表\n", "| 关键词 | 组 | 命中次数 | 文件数 |", "| :--- | :--- | ---: | ---: |"]
    for kw, v in sorted(hits.items(), key=lambda kv: -kv[1]["count"]):
        md.append(f"| `{kw}` | {v['group']} | {v['count']} | {len(v['files'])} |")

    md.append("\n## 上下文样本\n")
    for kw, v in sorted(hits.items(), key=lambda kv: -kv[1]["count"]):
        md.append(f"### `{kw}`（{v['group']}，{v['count']} 次）\n")
        for rel, samples in list(v["files"].items())[:3]:
            md.append(f"- `{rel}`")
            for s in samples[:2]:
                md.append(f"  - …{s}…")
        md.append("")

    (out_dir / "probe_report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"scanned files={files_scanned} bytes={bytes_scanned} keywords_hit={len(hits)}")
    print(f"written: {out_dir/'probe_report.md'}, {out_dir/'probe_hits.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
