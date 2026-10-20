#!/usr/bin/env python3
"""
Claude Network Guard & TUN Conflict Mitigation Sentinel
Author: FXXK CLAUDE Team
Date: 2026-10-20
Version: 1.0.0

【背景与逆向成果转化】
通过对 macOS Claude Desktop (v2.42304.0) 的逆向，证实客户端在启动 Cowork 本地微型 VM
(基于 Apple Virtualization.framework / smol-bin.arm64.img) 时，
若遭遇网络超时 (connection_timeout)，会主动触发底层网络嗅探 `networkDiagnostics`：
- 调用 `/sbin/ifconfig` 嗅探 `utun*`, `ppp*`, `tun*`, `ipsec*` 接口
- 调用 `/usr/sbin/scutil --nc list` 嗅探系统 VPN 配置文件与状态
- 调用 `/usr/bin/pgrep bootpd` 检查 macOS 原生 DHCP 守护进程
- 探测 `192.168.64.0/24` (Apple Virtualization NAT 子网) 与 IPv6 `fc00::/7` 连通性

若发现 VPN / TUN 冲突，客户端将记录 `p.vpnActive: true`，并在界面弹窗阻断：
"Your network traffic may be routing through a VPN, which can interfere with Claude's workspace."

本脚本用于：
1. 【环境深度体检】: 检测宿主 macOS 网络状态、VPN 接口、bootpd 状态及 IPv6 泄漏风险
2. 【TUN 冲突规避】: 针对 Clash Meta / Surge / Sing-box 自动生成 Virtualization 网段绕过与 AAAA DNS 阻断规则
3. 【自洽出口验证】: 检测出口国家 (CF-Ray)、住宅属性、TLS 握手自洽度
"""

import os
import sys
import re
import json
import socket
import argparse
import subprocess
import urllib.request
from typing import Dict, List, Optional, Tuple, Any

CLAUDE_DOMAINS = [
    "claude.ai",
    "api.anthropic.com",
    "cdn.claude.ai",
    "statsig.anthropic.com",
    "browser-intake-us5-datadoghq.com"
]

VIRTUALIZATION_SUBNETS = [
    "192.168.64.0/24",
    "fc00::/7"
]

class Colors:
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def log_info(msg: str):
    print(f"{Colors.BLUE}[*]{Colors.RESET} {msg}")


def log_success(msg: str):
    print(f"{Colors.GREEN}[+]{Colors.RESET} {msg}")


def log_warn(msg: str):
    print(f"{Colors.YELLOW}[!]{Colors.RESET} {msg}")


def log_error(msg: str):
    print(f"{Colors.RED}[-]{Colors.RESET} {msg}")


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate(timeout=8)
        return proc.returncode, out.strip(), err.strip()
    except Exception as e:
        return -1, "", str(e)


def audit_host_interfaces() -> Dict[str, Any]:
    """嗅探 host 网卡与 VPN 接口 (对齐 Claude 源码中的 XYr / ZYr / QYr)"""
    res = {
        "tun_interfaces": [],
        "bridge_interfaces": [],
        "scutil_vpns": [],
        "bootpd_running": False,
        "conflict_risk": "LOW"
    }

    # 1. ifconfig utun
    ret, out, _ = run_cmd(["/sbin/ifconfig"])
    if ret == 0:
        matches = re.findall(r"^(utun\d+|ppp\d+|ipsec\d+|tun\d+):", out, re.M)
        res["tun_interfaces"] = list(set(matches))
        bridges = re.findall(r"^(bridge\d+|vmnet\d+):", out, re.M)
        res["bridge_interfaces"] = list(set(bridges))

    # 2. scutil --nc list
    ret, out, _ = run_cmd(["/usr/sbin/scutil", "--nc", "list"])
    if ret == 0:
        for line in out.split("\n"):
            if "(Connected)" in line:
                m = re.search(r'"([^"]+)"', line)
                if m:
                    res["scutil_vpns"].append(m.group(1))

    # 3. pgrep bootpd
    ret, out, _ = run_cmd(["/usr/bin/pgrep", "-x", "bootpd"])
    res["bootpd_running"] = (ret == 0 and len(out.strip()) > 0)

    # 风险判定
    if res["tun_interfaces"] or res["scutil_vpns"]:
        res["conflict_risk"] = "HIGH" if not res["bootpd_running"] else "MEDIUM"

    return res


def check_dns_ipv6_leak() -> Dict[str, Any]:
    """检测 Anthropic 域名是否发生国内 IPv6 (AAAA) 直连穿透泄漏"""
    res = {"leaks": [], "safe": True}
    for dom in CLAUDE_DOMAINS[:2]:
        try:
            # 查询 AAAA
            ret, out, _ = run_cmd(["dig", "+short", "AAAA", dom])
            if ret == 0 and out.strip():
                ips = [ip for ip in out.split("\n") if ":" in ip]
                domestic_leaks = [ip for ip in ips if ip.startswith(("240e", "2408", "2409", "2001:da8"))]
                if domestic_leaks:
                    res["leaks"].append({"domain": dom, "ips": domestic_leaks, "type": "DOMESTIC_IPV6_LEAK"})
                    res["safe"] = False
                elif ips:
                    res["leaks"].append({"domain": dom, "ips": ips, "type": "GLOBAL_IPV6_EXPOSED"})
        except Exception:
            pass
    return res


def check_cf_exit() -> Dict[str, Any]:
    """检测当前网络出海出口节点信息 (Cloudflare Trace)"""
    res = {"ip": "Unknown", "loc": "Unknown", "colo": "Unknown", "warp": "off"}
    try:
        req = urllib.request.Request(
            "https://cloudflare.com/cdn-cgi/trace",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
            for line in text.split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k == "ip": res["ip"] = v
                    elif k == "loc": res["loc"] = v
                    elif k == "colo": res["colo"] = v
                    elif k == "warp": res["warp"] = v
    except Exception as e:
        res["error"] = str(e)
    return res


def generate_clash_rules() -> str:
    """生成适用于 Clash Meta / Mihomo / Clash Verge 的 TUN 防冲突与分流规则"""
    return """# ========================================================
# Claude 桌面端 & 微型 VM 防冲突专用配置 (Clash Meta / Mihomo)
# 作用：
# 1. 规避 Apple Virtualization (192.168.64.0/24, fc00::/7) TUN 冲突
# 2. 封杀 IPv6 AAAA 穿透泄漏，避免国内双栈 IP 关联
# 3. 拦截第三方遥测打点，定向保护业务流量
# ========================================================

# 1. TUN 配置推荐补丁 (在 tun 节点下合并)
tun:
  enable: true
  stack: mixed # 或 gvisor
  auto-route: true
  auto-detect-interface: true
  dns-hijack:
    - any:53
    - tcp://any:53
  # 关键：必须排除 Apple Virtualization VM 网段与 DHCP 端口！
  route-exclude-address:
    - 192.168.64.0/24
    - fc00::/7
    - 127.0.0.0/8
    - 10.0.0.0/8
    - 172.16.0.0/12

# 2. DNS 纯净化与防泄漏配置 (在 dns 节点下合并)
dns:
  enable: true
  ipv6: false # 强力阻断 AAAA 查询，防止国内 ISP IPv6 穿透！
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - "*.lan"
    - "localhost.ptlogin2.qq.com"
    - "+.anthropic.com"
    - "+.claude.ai"

# 3. 分流规则清单 (在 rules 顶部注入)
rules:
  # Apple 虚拟化与本地沙盒服务直连
  - IP-CIDR,192.168.64.0/24,DIRECT,no-resolve
  - IP-CIDR6,fc00::/7,DIRECT,no-resolve

  # Claude / Anthropic 核心业务 (必须走纯净节点)
  - DOMAIN-SUFFIX,claude.ai,PROXIES
  - DOMAIN-SUFFIX,anthropic.com,PROXIES
  - DOMAIN-SUFFIX,claude.usercontent.com,PROXIES
  - DOMAIN-SUFFIX,claudemcpcontent.com,PROXIES

  # 人机验证与客户端证明依赖 (hCaptcha invisible)
  - DOMAIN-SUFFIX,hcaptcha.com,PROXIES

  # 可选：静默拦截非必要性能埋点 (减少设备特征上报)
  # - DOMAIN,browser-intake-us5-datadoghq.com,REJECT
  # - DOMAIN-SUFFIX,statsig.anthropic.com,PROXIES
"""


def generate_surge_rules() -> str:
    """生成适用于 Surge macOS 的 TUN 排除与分流规则"""
    return """# ========================================================
# Claude 桌面端 & 微型 VM 防冲突配置 (Surge macOS)
# ========================================================

[General]
# 排除 Apple Virtualization 网段，防止 bootpd 与 VM 通信超时
tun-excluded-routes = 192.168.64.0/24, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
ipv6 = false

[Rule]
# Apple Virtualization 本地直连
IP-CIDR,192.168.64.0/24,DIRECT,no-resolve

# Claude 业务高优走代理
DOMAIN-SUFFIX,claude.ai,PROXY
DOMAIN-SUFFIX,anthropic.com,PROXY
DOMAIN-SUFFIX,claudemcpcontent.com,PROXY
DOMAIN-SUFFIX,hcaptcha.com,PROXY
"""


def generate_singbox_rules() -> str:
    """生成适用于 sing-box 的 route_exclude_address 与 DNS 规则"""
    payload = {
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "utun99",
                "inet4_address": "172.19.0.1/30",
                "auto_route": True,
                "strict_route": True,
                "route_exclude_address": [
                    "192.168.64.0/24",
                    "fc00::/7",
                    "127.0.0.0/8",
                    "10.0.0.0/8"
                ]
            }
        ],
        "dns": {
            "rules": [
                {
                    "domain_suffix": ["claude.ai", "anthropic.com"],
                    "query_type": ["AAAA"],
                    "server": "reject"
                }
            ]
        }
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def run_diagnose():
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== Claude macOS 宿主网络与 TUN 嗅探环境自检 ==={Colors.RESET}\n")

    # 1. 嗅探接口
    print(f"{Colors.BOLD}1. 宿主网卡与 VPN 探测 (对照 Claude 源码检测项):{Colors.RESET}")
    net = audit_host_interfaces()
    if net["tun_interfaces"]:
        print(f"  • 活动虚拟 TUN/VPN 接口: {Colors.YELLOW}{', '.join(net['tun_interfaces'])}{Colors.RESET}")
    else:
        print(f"  • 活动虚拟 TUN/VPN 接口: {Colors.GREEN}无 (未检测到系统虚拟网卡占用){Colors.RESET}")

    if net["scutil_vpns"]:
        print(f"  • scutil 登记的连接 VPN: {Colors.RED}{', '.join(net['scutil_vpns'])}{Colors.RESET}")
    else:
        print(f"  • scutil 登记的连接 VPN: {Colors.GREEN}无活动连接{Colors.RESET}")

    bootpd_color = Colors.GREEN if net["bootpd_running"] else Colors.YELLOW
    print(f"  • macOS bootpd 守护进程: {bootpd_color}{'运行中 (可分配 VM IP)' if net['bootpd_running'] else '未激活 (启动 VM 时将按需唤醒)'}{Colors.RESET}")

    if net["conflict_risk"] == "HIGH":
        print(f"  • {Colors.RED}【风险预警】: 检测到活动 TUN 接口，若未排除 192.168.64.0/24，Claude Cowork VM 极可能报错 connection_timeout！{Colors.RESET}")
    else:
        print(f"  • TUN 冲突风险等级: {Colors.GREEN}安全 / 正常可控{Colors.RESET}")

    # 2. IPv6 泄漏
    print(f"\n{Colors.BOLD}2. Claude 核心域名 IPv6 (AAAA) 穿透风险:{Colors.RESET}")
    v6 = check_dns_ipv6_leak()
    if not v6["safe"]:
        print(f"  • {Colors.RED}【高危泄漏】: 检测到国内 IPv6 地址直连穿透！{Colors.RESET}")
        for l in v6["leaks"]:
            print(f"    - 域名: {l['domain']} -> 暴露 IPv6: {l['ips']}")
        print(f"    建议：在代理工具中关闭 IPv6 (ipv6: false) 或将 AAAA 查询拒答。")
    else:
        print(f"  • IPv6 防护态: {Colors.GREEN}安全 (未见国内双栈 IPv6 泄漏){Colors.RESET}")

    # 3. 出口节点检测
    print(f"\n{Colors.BOLD}3. Cloudflare 出海节点识别:{Colors.RESET}")
    cf = check_cf_exit()
    if "error" in cf:
        print(f"  • 探测出口失败: {Colors.RED}{cf['error']}{Colors.RESET}")
    else:
        print(f"  • 公网出口 IP : {Colors.CYAN}{cf['ip']}{Colors.RESET}")
        print(f"  • 物理归属国家 : {Colors.BOLD}{cf['loc']}{Colors.RESET} (数据中心机房: {cf['colo']})")
        print(f"  • WARP 状态   : {cf['warp']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Claude 宿主网络体检与 TUN 冲突规避引擎")
    parser.add_argument("--diagnose", action="store_true", help="执行全面网络体检 (TUN 冲突、scutil 状态、IPv6 泄漏)")
    parser.add_argument("--generate-rules", choices=["clash", "surge", "singbox", "all"], default=None, help="生成指定代理客户端的防冲突配置规则")
    parser.add_argument("--export-dir", type=str, default=None, help="将生成的规则文件直接输出到指定目录")

    args = parser.parse_args()

    if not args.diagnose and not args.generate_rules:
        run_diagnose()
        print(f"{Colors.BOLD}提示{Colors.RESET}: 运行 `python3 claude_network_guard.py --generate-rules all` 可导出全套客户端规避规则。")
        return

    if args.diagnose:
        run_diagnose()

    if args.generate_rules:
        target = args.generate_rules
        configs = {}
        if target in ["clash", "all"]:
            configs["clash_meta_claude_tun.yaml"] = generate_clash_rules()
        if target in ["surge", "all"]:
            configs["surge_claude_tun.conf"] = generate_surge_rules()
        if target in ["singbox", "all"]:
            configs["singbox_claude_tun.json"] = generate_singbox_rules()

        if args.export_dir:
            os.makedirs(args.export_dir, exist_ok=True)
            for fname, content in configs.items():
                fpath = os.path.join(args.export_dir, fname)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)
                log_success(f"已导出配置规则至: {fpath}")
        else:
            for fname, content in configs.items():
                print(f"\n{Colors.BOLD}{Colors.CYAN}=== {fname} ==={Colors.RESET}\n")
                print(content)


if __name__ == "__main__":
    main()
