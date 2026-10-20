#!/usr/bin/env python3
# ==============================================================================
# FXXK CLAUDE - 24-Hour Taiwan Residential IP Stability & Jitter Monitor
# ==============================================================================
# 监控台湾 1 ~ 6 物理出口住宅节点 24 小时连续表现
# 指标包含：可用率 (Uptime %)、平均延迟、抖动标准差、丢包超时次数、连续断连时长、综合稳定评分
# ==============================================================================

import os
import sys
import time
import json
import math
import socket
import urllib.parse
from datetime import datetime

# 探测周期与时长配置
INTERVAL_SECONDS = 60            # 采样频率：每 60 秒探测一次
TOTAL_HOURS = 24                 # 监控总时长：24 小时
TOTAL_DURATION = TOTAL_HOURS * 3600

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output/monitoring")
os.makedirs(OUTPUT_DIR, exist_ok=True)

JSONL_LOG = os.path.join(OUTPUT_DIR, "tw_nodes_24h.jsonl")
SUMMARY_JSON = os.path.join(OUTPUT_DIR, "summary.json")
REPORT_MD = os.path.join(OUTPUT_DIR, "LIVE_REPORT.md")

# 监控目标：台湾 1 ~ 6 核心物理落地出口
TARGET_NODES = [
    {
        "id": "TW3",
        "name": "🇹🇼 台湾3-VIP88-谷歌学术",
        "ip": "61.222.202.168",
        "isp": "中华电信 HiNet (AS3462)",
        "proto": "Hysteria2 (UDP)"
    },
    {
        "id": "TW4",
        "name": "🇹🇼 台湾4-VIP88",
        "ip": "61.222.202.169",
        "isp": "中华电信 HiNet (AS3462)",
        "proto": "Hysteria2 (UDP)"
    },
    {
        "id": "TW6",
        "name": "🇹🇼 台湾6-VIP88",
        "ip": "61.222.202.182",
        "isp": "中华电信 HiNet (AS3462)",
        "proto": "Hysteria2 (UDP)"
    },
    {
        "id": "TW2",
        "name": "🇹🇼 台湾2-VIP88-谷歌学术",
        "ip": "61.222.202.238",
        "isp": "中华电信 HiNet (AS3462)",
        "proto": "Hysteria2 (UDP)"
    },
    {
        "id": "TW1",
        "name": "🇹🇼 台湾1-VIP88-谷歌学术",
        "ip": "61.222.202.235",
        "isp": "中华电信 HiNet (AS3462)",
        "proto": "Hysteria2 (UDP)"
    },
    {
        "id": "TW5",
        "name": "🇹🇼 台湾5-VIP88-0.8倍率-谷歌学术",
        "ip": "36.232.17.221",
        "isp": "中华电信 HiNet (AS3462)",
        "proto": "Hysteria2 (UDP)"
    },
    # 附带监控 3 号与 4 号的 TCP 备用协议（用于比对同出口协议稳定性）
    {
        "id": "TW3-AnyTLS",
        "name": "🇹🇼 台湾3-VIP88a-谷歌学术",
        "ip": "61.222.202.168",
        "isp": "中华电信 HiNet (AS3462)",
        "proto": "AnyTLS (TCP)"
    },
    {
        "id": "TW4-AnyTLS",
        "name": "🇹🇼 台湾4-VIP88a",
        "ip": "61.222.202.169",
        "isp": "中华电信 HiNet (AS3462)",
        "proto": "AnyTLS (TCP)"
    }
]

SOCKET_CANDIDATES = [
    f"/var/run/clash-verge-service/users/{os.getuid()}/verge-mihomo.sock",
    "/var/run/clash-verge-service/users/501/verge-mihomo.sock",
    "/tmp/verge/verge-mihomo.sock"
]

def find_active_socket():
    for p in SOCKET_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

def probe_node_delay(sock_path, node_name, timeout_ms=4000):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(6.0)
        s.connect(sock_path)
        encoded_node = urllib.parse.quote(node_name)
        url = f"/proxies/{encoded_node}/delay?url=https://cp.cloudflare.com/generate_204&timeout={timeout_ms}"
        req = f"GET {url} HTTP/1.1\r\nHost: localhost\r\n\r\n"
        s.sendall(req.encode("utf-8"))
        res = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            res += chunk
            if b"\r\n\r\n" in res:
                break
        s.close()
        text = res.decode("utf-8", errors="ignore")
        body = text.split("\r\n\r\n")[-1] if "\r\n\r\n" in text else text
        data = json.loads(body.strip())
        if "delay" in data:
            return True, data["delay"], None
        else:
            return False, 0, data.get("message", "Unknown error")
    except Exception as e:
        return False, 0, str(e)

def calculate_stats(node_records):
    total = len(node_records)
    if total == 0:
        return {}
    successes = [r["delay"] for r in node_records if r["success"]]
    failures = total - len(successes)
    uptime_pct = (len(successes) / total) * 100.0

    if successes:
        avg_delay = sum(successes) / len(successes)
        min_delay = min(successes)
        max_delay = max(successes)
        # 计算标准差 (抖动指标)
        variance = sum((x - avg_delay) ** 2 for x in successes) / len(successes)
        jitter = math.sqrt(variance)
    else:
        avg_delay = 0
        min_delay = 0
        max_delay = 0
        jitter = 0

    # 连续断线最长次数
    max_consecutive_fail = 0
    curr_fail = 0
    for r in node_records:
        if not r["success"]:
            curr_fail += 1
            if curr_fail > max_consecutive_fail:
                max_consecutive_fail = curr_fail
        else:
            curr_fail = 0

    # 综合稳定性评分计算公式 (满分 100 分)：
    # 1. 可用率占比 65 分：100% 得 65 分，跌破 90% 迅速扣分
    score_uptime = max(0, (uptime_pct - 50) / 50 * 65) if uptime_pct >= 50 else 0
    # 2. 延迟占比 20 分：<= 60ms 得 20 分，>= 300ms 得 0 分
    if successes and avg_delay > 0:
        score_delay = max(0, min(20, (300 - avg_delay) / 240 * 20))
    else:
        score_delay = 0
    # 3. 抖动占比 15 分：jitter <= 5ms 得 15 分，>= 50ms 得 0 分
    if successes:
        score_jitter = max(0, min(15, (50 - jitter) / 45 * 15))
    else:
        score_jitter = 0

    total_score = round(score_uptime + score_delay + score_jitter, 1)

    return {
        "total_probes": total,
        "success_probes": len(successes),
        "fail_probes": failures,
        "uptime_pct": round(uptime_pct, 2),
        "avg_delay": round(avg_delay, 1),
        "min_delay": min_delay,
        "max_delay": max_delay,
        "jitter": round(jitter, 1),
        "max_consecutive_fail": max_consecutive_fail,
        "stability_score": total_score
    }

def generate_report(stats_map, start_time, elapsed_sec):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
    progress_pct = min(100.0, round((elapsed_sec / TOTAL_DURATION) * 100, 1))

    # 按综合稳定性得分降序排序
    ranked_nodes = sorted(
        TARGET_NODES,
        key=lambda n: stats_map.get(n["name"], {}).get("stability_score", 0),
        reverse=True
    )

    md = []
    md.append("# 📊 台湾住宅 IP 24 小时稳定性与质量实时监控报告\n")
    md.append(f"> **监控启动时间**：`{start_str}` | **当前更新时间**：`{now_str}`")
    md.append(f"> **测试进度**：已运行 `{elapsed_sec // 3600}小时 {(elapsed_sec % 3600) // 60}分钟` / 共 24 小时（进度：`{progress_pct}%`）\n")
    md.append("---\n")
    md.append("## 🏆 实时综合稳定性排行榜 (按稳定性得分倒序)\n")
    md.append("| 排名 | 节点名称 | 出口 IP | 协议类型 | 可用率 (Uptime) | 平均延迟 | 抖动标准差 | 超时次数 | 综合稳定得分 | 状态评级 |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for rank, node in enumerate(ranked_nodes, 1):
        s = stats_map.get(node["name"], {})
        score = s.get("stability_score", 0)
        uptime = s.get("uptime_pct", 0)
        avg = s.get("avg_delay", 0)
        jit = s.get("jitter", 0)
        fails = s.get("fail_probes", 0)

        if score >= 90:
            badge = "🟢 极度稳定 (首选主力)"
        elif score >= 75:
            badge = "🟡 表现良好 (优质备用)"
        elif score >= 50:
            badge = "🟠 偶有波动"
        else:
            badge = "🔴 频繁断连/严重丢包"

        rank_medal = "🥇 1" if rank == 1 else ("🥈 2" if rank == 2 else ("🥉 3" if rank == 3 else f"{rank}"))

        md.append(f"| **{rank_medal}** | `{node['name']}` | `{node['ip']}` | {node['proto']} | **{uptime}%** | {avg} ms | ±{jit} ms | {fails} 次 | **{score}** / 100 | {badge} |")

    md.append("\n---\n")
    md.append("## 📌 核心评判标准与防封风控说明\n")
    md.append("1. **可用率权重最高（65%）**：节点一旦丢包或心跳超时，会导致浏览器与 Claude 发生 WebSocket 握手断开或重连。")
    md.append("2. **延迟与抖动权重（35%）**：平均延迟越低、标准差（Jitter）越小，代表宽带线路没有出现拥塞与 QoS 丢包。")
    md.append("3. **同出口验证**：3 系列与 4 系列不仅具备 Hysteria2 极速协议，还配备了同出口 AnyTLS TCP 备用链路，在面对复杂公网环境时容灾能力最强。")
    md.append("\n*本报告由后台守护进程每分钟自动采样并实时刷新生成，24 小时后将输出最终权威裁决。*")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

def main():
    print("=" * 65)
    print("🚀 启动 24 小时台湾住宅 IP 连续稳定性监控守护程序")
    print(f"• 监控总时长: {TOTAL_HOURS} 小时 ({TOTAL_DURATION} 秒)")
    print(f"• 采样间隔: 每 {INTERVAL_SECONDS} 秒探测一次全部节点")
    print(f"• 实时报告路径: {REPORT_MD}")
    print(f"• 原始日志流: {JSONL_LOG}")
    print("=" * 65)

    start_time = time.time()
    end_time = start_time + TOTAL_DURATION

    # 历史记录内存池: { node_name: [ {"timestamp": ..., "success": ..., "delay": ...} ] }
    history = {n["name"]: [] for n in TARGET_NODES}

    # 如果存在已有的 jsonl 历史，恢复数据
    if os.path.exists(JSONL_LOG):
        try:
            with open(JSONL_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        name = record.get("node")
                        if name in history:
                            history[name].append(record)
            print(f"[*] 成功恢复历史采样数据，当前已有数据点: {sum(len(v) for v in history.values())}")
        except Exception:
            pass

    probe_count = 0
    while time.time() < end_time:
        loop_start = time.time()
        elapsed = int(loop_start - start_time)
        probe_count += 1

        sock_path = find_active_socket()
        if not sock_path:
            print(f"[!] 警告: 未找到活跃的 Mihomo Unix Socket，等待下一次循环...")
            time.sleep(INTERVAL_SECONDS)
            continue

        ts_iso = datetime.now().isoformat()
        current_batch = []

        for node in TARGET_NODES:
            ok, delay, err = probe_node_delay(sock_path, node["name"])
            rec = {
                "timestamp": ts_iso,
                "node": node["name"],
                "ip": node["ip"],
                "proto": node["proto"],
                "success": ok,
                "delay": delay if ok else None,
                "error": err
            }
            history[node["name"]].append(rec)
            current_batch.append(rec)

        # 写入追加日志
        try:
            with open(JSONL_LOG, "a", encoding="utf-8") as f:
                for r in current_batch:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[!] 写入日志失败: {e}")

        # 计算并更新统计
        stats_map = {}
        for node in TARGET_NODES:
            stats_map[node["name"]] = calculate_stats(history[node["name"]])

        # 更新 summary.json
        try:
            with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
                json.dump({
                    "start_time": start_time,
                    "elapsed_sec": elapsed,
                    "total_duration": TOTAL_DURATION,
                    "last_updated": ts_iso,
                    "nodes": stats_map
                }, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # 实时生成并更新 Markdown 报告
        generate_report(stats_map, start_time, elapsed)

        # 控制台打印即时快报
        top_node = sorted(TARGET_NODES, key=lambda n: stats_map.get(n["name"], {}).get("stability_score", 0), reverse=True)[0]
        top_stats = stats_map.get(top_node["name"], {})
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 轮次 #{probe_count} (已测 {elapsed // 60}m) | 领先: {top_node['name'][:12]} (可用率: {top_stats.get('uptime_pct')}% | 均延: {top_stats.get('avg_delay')}ms | 评分: {top_stats.get('stability_score')})")

        # 补齐休眠时间
        cost = time.time() - loop_start
        sleep_dur = max(1.0, INTERVAL_SECONDS - cost)
        time.sleep(sleep_dur)

    print("\n✅ 24 小时连续监控圆满结束！最终权威评测报告已就绪: " + REPORT_MD)

if __name__ == "__main__":
    main()
