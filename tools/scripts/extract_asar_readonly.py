#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_asar_readonly.py — 零依赖解析 Electron app.asar（只读）。

背景
----
Claude Desktop 是 Electron 应用，业务代码打包在 app.asar（Chromium Pickle 格式）。
本项目要求「不改动本机环境」，因此本脚本：
  - 只读取源 asar（可用副本），绝不写回；
  - 不依赖 npm / asar CLI（避免污染全局或用户级缓存）；
  - 解包产物只写到指定输出目录。

格式
----
    UInt32(4) | UInt32(header_payload_size) | UInt32(json_size) | JSON(json_size) | [files...]
    文件数据起始偏移 = 8 + header_payload_size

用法
----
    python3 tools/scripts/extract_asar_readonly.py <app.asar> <out_dir> [--list-only] [--max-bytes N]
"""

import json
import struct
import sys
from pathlib import Path


def parse_header(asar_path: Path):
    data = asar_path.read_bytes()
    size_field = struct.unpack_from("<I", data, 0)[0]
    if size_field != 4:
        raise ValueError(f"unexpected size field {size_field}")
    header_payload_size = struct.unpack_from("<I", data, 4)[0]
    base_offset = 8 + header_payload_size

    # 标准 asar: JSON 始于 12；部分构建器（含 Claude Desktop）多一个字段，始于 16。
    if data[12:13] == b"{":
        json_start, json_size = 12, struct.unpack_from("<I", data, 8)[0]
    elif data[16:17] == b"{":
        json_start, json_size = 16, struct.unpack_from("<I", data, 12)[0]
    else:
        raise ValueError("cannot locate asar JSON header (neither @12 nor @16 starts with '{')")

    header = json.loads(data[json_start:json_start + json_size].decode("utf-8"))
    return data, header, base_offset


def walk(node, prefix, data, base_offset, out_dir, list_only, limit_bytes, stats):
    for name, meta in (node.get("files") or {}).items():
        rel = f"{prefix}/{name}" if prefix else name
        if "files" in meta:
            walk(meta, rel, data, base_offset, out_dir, list_only, limit_bytes, stats)
            continue

        size = int(meta.get("size", 0))
        unpacked = bool(meta.get("unpacked"))
        link = meta.get("link")
        stats["files"] += 1
        stats["bytes"] += size

        if list_only:
            flag = " [unpacked]" if unpacked else ""
            flag += " [link]" if link else ""
            print(f"{size:>10}  {rel}{flag}")
            continue

        if unpacked:
            stats["skipped_unpacked"] += 1
            return
        if link:
            stats["skipped_link"] += 1
            return
        if size > limit_bytes:
            stats["skipped_large"] += 1
            return

        offset = int(meta.get("offset", 0))
        blob = data[base_offset + offset: base_offset + offset + size]
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        stats["written"] += 1


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    asar_path = Path(argv[1])
    out_dir = Path(argv[2])
    list_only = "--list-only" in argv
    limit_bytes = 64 * 1024 * 1024
    if "--max-bytes" in argv:
        limit_bytes = int(argv[argv.index("--max-bytes") + 1])

    data, header, base_offset = parse_header(asar_path)
    stats = {"files": 0, "bytes": 0, "written": 0,
             "skipped_unpacked": 0, "skipped_link": 0, "skipped_large": 0}
    out_dir.mkdir(parents=True, exist_ok=True)
    walk(header, "", data, base_offset, out_dir, list_only, limit_bytes, stats)

    print(f"asar={asar_path} base_offset={base_offset} files={stats['files']} bytes={stats['bytes']}")
    if not list_only:
        print(f"written={stats['written']} skipped_unpacked={stats['skipped_unpacked']} "
              f"skipped_link={stats['skipped_link']} skipped_large={stats['skipped_large']} -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
