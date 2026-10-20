#!/usr/bin/env python3
import os
import sys
import base64
import urllib.request
import hashlib
import yaml
import time
import socket
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

SUB_URL = "https://v1.xdollar.top/link/qBpApyv9Wbi76z0I32XLnM9eLCIxyqonkdQD?clash=2"
PASSWORD = "Dazhi@2026"

def find_app_dirs():
    candidates = [
        os.path.expanduser("~/Library/Application Support/io.github.fqfqgo.clash-verge-for-v2free"),
        os.path.expanduser("~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"),
        os.path.expanduser("~/.config/clash-verge-rev"),
    ]
    existing = [d for d in candidates if os.path.exists(d)]
    if not existing:
        default_dir = candidates[0]
        os.makedirs(default_dir, exist_ok=True)
        return [default_dir]
    return existing

def fetch_and_decrypt():
    print("[*] 正在拉取 v2free 加密订阅...")
    resp = None
    proxies_to_try = [None]
    if os.environ.get("http_proxy") or os.environ.get("all_proxy"):
        proxies_to_try.insert(0, "env")
    for test_port in [7897, 7890]:
        try:
            with socket.create_connection(("127.0.0.1", test_port), timeout=0.3):
                proxies_to_try.insert(0, f"http://127.0.0.1:{test_port}")
                break
        except Exception:
            pass

    for proxy in proxies_to_try:
        try:
            if proxy and proxy != "env":
                handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
                opener = urllib.request.build_opener(handler)
            else:
                opener = urllib.request.build_opener()
            req = urllib.request.Request(SUB_URL, headers={"User-Agent": "ClashVerge/1.3.8"})
            with opener.open(req, timeout=12) as response:
                resp = response.read().decode("utf-8").strip()
            if resp:
                print(f"[✓] 成功通过 {'本地代理 ' + proxy if proxy else '直连'} 获取到加密订阅！")
                break
        except Exception:
            continue

    if not resp:
        return None

    print("[*] 正在执行 AES-128-CBC 解密...")
    try:
        b64_str = resp.replace("\r", "").replace("\n", "").replace(" ", "").replace("_", "/").replace("-", "+")
        pad_len = (4 - len(b64_str) % 4) % 4
        b64_str += "=" * pad_len
        raw_bytes = base64.b64decode(b64_str)

        key = hashlib.md5(PASSWORD.encode("utf-8")).digest()
        iv = raw_bytes[:16]
        ciphertext = raw_bytes[16:]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        return yaml.safe_load(decrypted.decode("utf-8"))
    except Exception as e:
        print(f"[!] AES 解密订阅失败: {e}")
        return None

def inject_rules_into_cfg(cfg):
    print("[*] 正在注入定制化分流规则体系...")
    cfg["mixed-port"] = 7897
    cfg["allow-lan"] = False
    cfg["mode"] = "rule"
    cfg["log-level"] = "info"
    cfg["ipv6"] = False
    cfg["unified-delay"] = True
    cfg["tcp-concurrent"] = True
    cfg["find-process-mode"] = "strict"

    cfg["dns"] = {
        "enable": True,
        "ipv6": False,
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "use-hosts": True,
        "fake-ip-filter": [
            "+.lan",
            "+.local",
            "+.market.xiaomi.com",
            "localhost.ptlogin2.qq.com"
        ],
        "default-nameserver": ["223.5.5.5", "119.29.29.29"],
        "nameserver": ["223.5.5.5", "119.29.29.29"],
        "proxy-server-nameserver": ["223.5.5.5", "119.29.29.29"]
    }

    cfg["tun"] = {
        "enable": True,
        "stack": "mixed",
        "dns-hijack": ["any:53", "tcp://any:53"],
        "auto-route": True,
        "auto-detect-interface": True,
        "strict-route": True,
        "route-exclude-address": [
            "192.168.0.0/16",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "127.0.0.0/8",
            "169.254.0.0/16"
        ]
    }

    all_proxies = cfg.get("proxies", [])
    all_proxy_names = set(p["name"] for p in all_proxies if isinstance(p, dict) and "name" in p)

    # 1. Claude专属代理列表：严格只保留 3 号母机全部协议（出口 100% 死锁 61.222.202.168，同一出口不同协议容灾）
    tw_candidates = [
        "🇹🇼 台湾3-VIP88-谷歌学术",     # Hysteria2 (UDP · 极速主力 · 出口 61.222.202.168)
        "🇹🇼 台湾3-VIP88a-谷歌学术",    # AnyTLS (TCP 协议 · 出口 61.222.202.168 零跳变)
        "🇹🇼 台湾3-VIP88b-谷歌学术",    # VLESS xhttp (TCP 协议 · 出口 61.222.202.168 零跳变)
        "🇹🇼 台湾3-VIP88d-谷歌学术",    # VLESS (TCP 协议 · 出口 61.222.202.168 零跳变)
    ]
    valid_tw = [p for p in tw_candidates if p in all_proxy_names]
    if not valid_tw:
        valid_tw = [p["name"] for p in all_proxies if isinstance(p, dict) and ("台湾" in p.get("name", "") or "TW" in p.get("name", "").upper())]
    if not valid_tw and all_proxies:
        valid_tw = [all_proxies[0]["name"]]

    # 2. 美国专属代理列表校验与智能兜底
    us_candidates = ["🇺🇸 美国独享-817180-xa", "🇺🇸 美国独享-817180-xb"]
    valid_us = [p for p in us_candidates if p in all_proxy_names]
    if not valid_us:
        valid_us = [p["name"] for p in all_proxies if isinstance(p, dict) and ("美国" in p.get("name", "") or "US" in p.get("name", "").upper())]
    if not valid_us and all_proxies:
        valid_us = [all_proxies[0]["name"]]

    groups = [g for g in cfg.get("proxy-groups", []) if g.get("name") not in ["🇹🇼 Claude专属", "🍎 Apple专属", "🇺🇸 Muse专属"]]

    for g in groups:
        if g.get("name") == "🔰节点选择":
            px = g.get("proxies", [])
            for tw_node in valid_tw:
                if tw_node in px:
                    px.remove(tw_node)
                    px.insert(0, tw_node)

    claude_group = {
        "name": "🇹🇼 Claude专属",
        "type": "fallback",
        "url": "https://cp.cloudflare.com/generate_204",
        "interval": 300,
        "timeout": 3000,
        "lazy": True,
        "proxies": valid_tw
    }

    muse_proxies = valid_us.copy()
    muse_proxies.append("DIRECT")

    muse_group = {
        "name": "🇺🇸 Muse专属",
        "type": "select",
        "proxies": muse_proxies
    }

    groups.insert(0, claude_group)
    groups.insert(0, muse_group)
    cfg["proxy-groups"] = groups

    custom_rules = [
        "AND,((NETWORK,UDP),(DST-PORT,443)),REJECT-DROP",
        "IP-CIDR,1.14.183.69/32,DIRECT,no-resolve",
        "DST-PORT,22,DIRECT",
        "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
        "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
        "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
        "IP-CIDR,127.0.0.0/8,DIRECT,no-resolve",
        "IP-CIDR,224.0.0.0/4,DIRECT,no-resolve",
        "DST-PORT,5353,DIRECT",
        "DOMAIN-SUFFIX,local,DIRECT",
        "PROCESS-NAME,Muse,🇺🇸 Muse专属",
        "PROCESS-NAME,EndoCrashpadHandler,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,muse.ai,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,meta.ai,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,meta.com,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,facebook.com,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,facebook.net,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,fbcdn.net,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,fbsbx.com,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,fb.me,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,instagram.com,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,cdninstagram.com,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,threads.net,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,multimango.com,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,internalfb.com,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,metaaiusercontent.com,🇺🇸 Muse专属",
        "DOMAIN-SUFFIX,ecto1usercontent.com,🇺🇸 Muse专属",
        "DOMAIN-KEYWORD,muse,🇺🇸 Muse专属",
        "GEOSITE,meta,🇺🇸 Muse专属",
        "GEOSITE,facebook,🇺🇸 Muse专属",
        "GEOSITE,instagram,🇺🇸 Muse专属",
        "AND,((NETWORK,UDP),(DST-PORT,3478)),REJECT-DROP",
        "AND,((NETWORK,UDP),(DST-PORT,5349)),REJECT-DROP",
        "DOMAIN-SUFFIX,youclaude.com,🇹🇼 Claude专属",
        "DOMAIN-KEYWORD,youclaude,🇹🇼 Claude专属",
        "DOMAIN-SUFFIX,claude.ai,🇹🇼 Claude专属",
        "DOMAIN-SUFFIX,claude.com,🇹🇼 Claude专属",
        "DOMAIN-SUFFIX,anthropic.com,🇹🇼 Claude专属",
        "DOMAIN-SUFFIX,anthropic.ai,🇹🇼 Claude专属",
        "DOMAIN-SUFFIX,claudeusercontent.com,🇹🇼 Claude专属",
        "DOMAIN-SUFFIX,statsig.com,REJECT",
        "DOMAIN-SUFFIX,statsigapi.net,REJECT",
        "DOMAIN-SUFFIX,featuregates.org,REJECT",
        "DOMAIN-SUFFIX,usefathom.com,REJECT",
        "DOMAIN-SUFFIX,segment.io,REJECT",
        "DOMAIN-SUFFIX,sentry.io,REJECT",
        "DOMAIN-SUFFIX,datadoghq.com,REJECT",
        "DOMAIN,telemetry.anthropic.com,REJECT",
        "DOMAIN-SUFFIX,stripe.com,🇹🇼 Claude专属",
        "DOMAIN-SUFFIX,stripe.network,🇹🇼 Claude专属",
        "DOMAIN-KEYWORD,anthropic,🇹🇼 Claude专属",
        "DOMAIN-KEYWORD,claude,🇹🇼 Claude专属"
    ]

    base_rules = [r for r in cfg.get("rules", []) if r not in custom_rules]
    cfg["rules"] = custom_rules + base_rules
    return cfg, valid_tw

def main():
    app_dirs = find_app_dirs()
    cfg = fetch_and_decrypt()

    for app_dir in app_dirs:
        profiles_dir = os.path.join(app_dir, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        target_profile = os.path.join(profiles_dir, "v2free_main.yaml")
        active_config = os.path.join(app_dir, "clash-verge.yaml")

        print(f"[*] 目标应用目录: {app_dir}")
        curr_cfg = cfg
        if not curr_cfg:
            if os.path.exists(target_profile):
                print(f"  • [ℹ] 在线拉取暂未成功，检测到本地预置配置文件: {target_profile}")
                try:
                    with open(target_profile, "r", encoding="utf-8") as f:
                        curr_cfg = yaml.safe_load(f)
                except Exception as e:
                    print(f"  • [!] 读取本地配置失败: {e}")
            if not curr_cfg:
                print("  • [!] 无可用配置，请检查网络后重试。")
                continue

        processed_cfg, valid_tw = inject_rules_into_cfg(curr_cfg)

        with open(target_profile, "w", encoding="utf-8") as f:
            yaml.dump(processed_cfg, f, allow_unicode=True, sort_keys=False)
        print(f"  • [✓] 订阅与分流规则更新完成！已写入: {target_profile}")

        try:
            with open(active_config, "w", encoding="utf-8") as f:
                yaml.dump(processed_cfg, f, allow_unicode=True, sort_keys=False)
            print(f"  • [✓] 同时同步至激活配置: {active_config}")
        except Exception as e:
            print(f"  • [!] 写入激活配置时出现警告: {e}")

        # 确保 profiles.yaml 存在
        profiles_meta_path = os.path.join(app_dir, "profiles.yaml")
        if not os.path.exists(profiles_meta_path):
            profiles_meta = {
                "current": "v2free_main",
                "items": [
                    {"uid": "Merge", "type": "merge", "name": None, "file": "Merge.yaml", "updated": int(time.time())},
                    {"uid": "Script", "type": "script", "name": None, "file": "Script.js", "updated": int(time.time())},
                    {
                        "uid": "v2free_main",
                        "type": "local",
                        "name": "v2free专属定制分流",
                        "file": "v2free_main.yaml",
                        "selected": [{"name": "🇹🇼 Claude专属", "now": valid_tw[0]}],
                        "updated": int(time.time())
                    }
                ]
            }
            try:
                with open(profiles_meta_path, "w", encoding="utf-8") as f:
                    yaml.dump(profiles_meta, f, allow_unicode=True, sort_keys=False)
                print(f"  • [✓] 自动初始化 Profile 元数据: {profiles_meta_path}")
            except Exception as e:
                print(f"  • [!] 写入 profiles.yaml 警告: {e}")

    # 尝试通知热重载（兼容 Sidecar 模式与系统服务模式 socket）
    candidate_socks = [
        f"/var/run/clash-verge-service/users/{os.getuid()}/verge-mihomo.sock",
        "/var/run/clash-verge-service/users/501/verge-mihomo.sock",
        "/tmp/verge/verge-mihomo.sock"
    ]
    reloaded = False
    for sock_path in candidate_socks:
        if os.path.exists(sock_path):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(sock_path)
                req_data = b"PUT /configs?force=true HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: 11\r\n\r\n{\"path\":\"\"}"
                s.sendall(req_data)
                s.close()
                print(f"[✓] 已成功向 Mihomo 发送热重载信号 ({sock_path})！")
                reloaded = True
                break
            except Exception:
                pass

if __name__ == "__main__":
    main()
