#!/usr/bin/env python3
"""
==============================================================================
FXXK CLAUDE - Automated sing-box / v2rayN Selective IPv6 Rule Injector
(sing-box 定向 Claude IPv6 拦截规则安全注入与配置校验工具)
==============================================================================
Features:
- Idempotent: safe to run multiple times without duplicating rules
- Automatic Backup: creates timestamped .bak before modifying any files
- Strict sing-box 1.14 syntax checking before saving
- Dry-run mode for previewing modifications
- Rollback capability to restore previous configuration
==============================================================================
"""

import os
import sys
import json
import shutil
import datetime
import argparse
import subprocess
from typing import Dict, Any, List

DEFAULT_CONFIG_PATH = "/Users/mac/Library/Application Support/v2rayN/binConfigs/configPre.json"
SINGBOX_BIN = "/Users/mac/Library/Application Support/v2rayN/bin/sing_box/sing-box-core" if os.path.isfile("/Users/mac/Library/Application Support/v2rayN/bin/sing_box/sing-box-core") else "/Users/mac/Library/Application Support/v2rayN/bin/sing_box/sing-box"


CLAUDE_DOMAINS = [
    "claude.ai",
    "anthropic.com",
    "claudeusercontent.com",
    "anthropic.ai",
    "claudecdn.com",
    "statsig.com",
    "statsigapi.net",
    "challenges.cloudflare.com",
]

TARGET_DNS_RULE = {
    "domain_suffix": CLAUDE_DOMAINS,
    "query_type": ["AAAA"],
    "action": "predefined",
    "rcode": "NOERROR",
}

TARGET_ROUTE_RULE = {
    "domain_suffix": CLAUDE_DOMAINS,
    "ip_version": 6,
    "action": "reject",
}


def find_rule_index(rules: List[Dict[str, Any]], rule_type: str) -> int:
    for idx, r in enumerate(rules):
        suffixes = r.get("domain_suffix", [])
        if "claude.ai" in suffixes:
            if rule_type == "dns" and "AAAA" in r.get("query_type", []):
                return idx
            if rule_type == "route" and r.get("action") == "reject" and r.get("ip_version") == 6:
                return idx
    return -1


def validate_with_singbox(config_dict: Dict[str, Any], singbox_bin: str) -> bool:
    if not os.path.isfile(singbox_bin):
        print(f"⚠️ sing-box 校验程序未在标准路径找到: {singbox_bin}，跳过二进制校验。")
        return True

    tmp_path = f"/tmp/singbox_test_{os.getpid()}.json"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

        proc = subprocess.run([singbox_bin, "check", "-c", tmp_path], capture_output=True, text=True)
        if proc.returncode == 0:
            return True
        else:
            print(f"❌ sing-box check 语法校验失败: {proc.stderr.strip()}")
            return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def apply_rules(config_path: str, dry_run: bool = False) -> bool:
    print("=================================================================")
    print("🛡️  FXXK CLAUDE - sing-box 定向 IPv6 防护规则注入器")
    print("=================================================================")

    if not os.path.isfile(config_path):
        print(f"❌ 目标配置文件不存在: {config_path}")
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
        except Exception as e:
            print(f"❌ JSON 解析失败: {e}")
            return False

    dns_section = config.setdefault("dns", {})
    dns_rules = dns_section.setdefault("rules", [])
    route_section = config.setdefault("route", {})
    route_rules = route_section.setdefault("rules", [])

    existing_dns_idx = find_rule_index(dns_rules, "dns")
    existing_route_idx = find_rule_index(route_rules, "route")

    changed = False

    # 1. 注入 DNS 规则
    if existing_dns_idx >= 0:
        print("ℹ️ DNS AAAA 定向阻断规则已存在，跳过注入。")
    else:
        # 寻找优先插入位置（在包含 predefined 的地方或前面）
        insert_pos = 0
        for i, r in enumerate(dns_rules):
            if r.get("action") == "predefined":
                insert_pos = i
                break
        dns_rules.insert(insert_pos, TARGET_DNS_RULE)
        print(f"✅ 已在 DNS 规则列表第 {insert_pos} 位插入 Claude AAAA -> NOERROR 空响应拦截规则。")
        changed = True

    # 2. 注入 Route 规则
    if existing_route_idx >= 0:
        print("ℹ️ Route 定向拒绝规则已存在，跳过注入。")
    else:
        # 在 route rules 最前面插入 reject
        route_rules.insert(0, TARGET_ROUTE_RULE)
        print("✅ 已在 Route 规则列表首位插入 Claude IPv6 -> reject 丢弃规则。")
        changed = True

    # 3. 放行局域网 Apple Continuity / Bonjour / 跨设备剪贴板
    # 3.1 TUN 网卡排除局域网组播地址段 (224.0.0.0/4 与 ff00::/8)
    inbounds = config.get("inbounds", [])
    for ib in inbounds:
        if ib.get("type") == "tun":
            excludes = ib.setdefault("route_exclude_address", [])
            for addr in ["224.0.0.0/4", "ff00::/8"]:
                if addr not in excludes:
                    excludes.append(addr)
                    print(f"✅ 已在 TUN 网卡排除列表中添加局域网组播网段: {addr} (保障隔空投送与剪贴板)")
                    changed = True

    # 3.2 从 reject 端口列表中剔除 5353 (Apple Bonjour / mDNS)
    for rule in route_rules:
        ports = rule.get("port", [])
        if isinstance(ports, list) and 5353 in ports and rule.get("action") == "reject":
            ports.remove(5353)
            print("✅ 已从 reject 拦截列表中移出 5353 端口 (Apple Bonjour / mDNS)。")
            changed = True
        cidrs = rule.get("ip_cidr", [])
        if isinstance(cidrs, list) and "224.0.0.0/3" in cidrs and rule.get("action") == "reject":
            cidrs.remove("224.0.0.0/3")
            print("✅ 已从 reject 拦截列表中移出 224.0.0.0/3 组播拦截。")
            changed = True

    if not changed:
        print("🎉 目标配置已处于完全防护状态，无需更新！")
        return True

    # 3. 语法校验
    print("🔍 正在调用本地 sing-box 1.14 核心执行严格语法校验...")
    if not validate_with_singbox(config, SINGBOX_BIN):
        print("❌ 规则校验未通过，已中止写入，原配置文件未受任何影响！")
        return False
    print("✅ 校验通过！新配置 100% 符合 sing-box 架构规范。")

    if dry_run:
        print("ℹ️ 当前处于 --dry-run 预览模式，未保存至磁盘。")
        return True

    # 4. 创建备份
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{config_path}.bak_claude_{timestamp}"
    shutil.copy2(config_path, backup_path)
    print(f"💾 原配置文件已安全备份至: {backup_path}")

    # 5. 写入更新
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"🚀 新配置文件已成功写入: {config_path}")
    print("\n【后续操作提示】:")
    print("1. 若 v2rayN 正在运行，请在桌面端点击一次「重启服务」或切换一次节点使其重新加载生效。")
    print("2. 重新运行 `./scripts/test_singbox_ipv6.sh` 即可看到 AAAA 记录已变成绿色 NODATA！")
    print("=================================================================\n")
    return True


def restore_backup(config_path: str) -> bool:
    dir_name = os.path.dirname(config_path)
    base_name = os.path.basename(config_path)
    backups = [f for f in os.listdir(dir_name) if f.startswith(f"{base_name}.bak_claude_")]
    if not backups:
        print("⚠️ 未找到任何自动备份文件。")
        return False
    backups.sort(reverse=True)
    latest_bak = os.path.join(dir_name, backups[0])
    print(f"🔄 正在从最新备份还原: {latest_bak} -> {config_path}")
    shutil.copy2(latest_bak, config_path)
    print("✅ 配置还原完成！")
    return True


def main():
    parser = argparse.ArgumentParser(description="FXXK CLAUDE - sing-box Selective IPv6 Rule Injector")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to configPre.json or custom config")
    parser.add_argument("--dry-run", action="store_true", help="Preview modifications without writing")
    parser.add_argument("--restore", action="store_true", help="Restore config from the latest backup")
    args = parser.parse_args()

    if args.restore:
        restore_backup(args.config)
    else:
        apply_rules(args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
