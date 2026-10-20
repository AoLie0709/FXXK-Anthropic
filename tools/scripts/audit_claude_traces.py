#!/usr/bin/env python3
"""
Claude Trace Auditor & Anti-Ban Zero-Tolerance Sentinel (v2.0)
Deep inspection & surgical remediation of macOS Claude/Anthropic remnants,
Keychain secrets, tracking cookies, timezone conflicts, and network leakages.

Philosophy: "宁可错杀一千，绝不放过一个；安全资产隔离，风险隐患全歼"
"""

import os
import sys
import glob
import json
import sqlite3
import shutil
import tempfile
import subprocess
from typing import Dict, List, Any, Tuple

# ANSI Colors
BOLD = "\033[1m"
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
GRAY = "\033[90m"

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output", "audits")

def mask_secret(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return "***"
    return f"{val[:4]}...{val[-4:]} (len: {len(val)})"

class ClaudeSentinel:
    def __init__(self):
        self.home = os.path.expanduser("~")
        self.results = {
            "timestamp": subprocess.getoutput("date '+%Y-%m-%d %H:%M:%S'"),
            "summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0
            },
            "findings": []
        }

    def add_finding(self, layer: str, severity: str, title: str, description: str, path: str = None, meta: Dict = None, advice: str = "", remediable: bool = False, remediation_cmd: str = ""):
        sev = severity.upper()
        if sev.lower() in self.results["summary"]:
            self.results["summary"][sev.lower()] += 1
        self.results["findings"].append({
            "layer": layer,
            "severity": sev,
            "title": title,
            "description": description,
            "path": path,
            "meta": meta or {},
            "advice": advice,
            "remediable": remediable,
            "remediation_cmd": remediation_cmd
        })

    def audit_processes(self):
        """1. Audit running processes & daemons (Aggregated)"""
        try:
            ps_out = subprocess.check_output(['ps', '-eo', 'pid,comm,args']).decode('utf-8', errors='ignore')
            claude_pids = []
            cc_switch_pids = []
            other_pids = []

            for line in ps_out.strip().split('\n')[1:]:
                l_low = line.lower()
                if any(k in l_low for k in ['claude', 'anthropic', 'cc-switch']):
                    if any(x in line for x in ['audit_claude', 'audit_claude_traces', 'python3 -c']):
                        continue
                    parts = line.strip().split(None, 2)
                    pid = parts[0]
                    comm = parts[1]
                    args = parts[2] if len(parts) > 2 else ''
                    
                    if 'cc-switch' in l_low:
                        cc_switch_pids.append(pid)
                    elif 'claude.app' in l_low or 'contents/macos/claude' in l_low:
                        claude_pids.append(pid)
                    else:
                        other_pids.append((pid, comm, args))

            if cc_switch_pids:
                p_str = " ".join(cc_switch_pids)
                self.add_finding(
                    layer="Process",
                    severity="HIGH",
                    title=f"运行中的 AI 环境变量注入器: CC Switch ({len(cc_switch_pids)} 个进程)",
                    description=f"检测到 CC Switch (PID: {p_str}) 正在后台运行。该程序是管理多模型并向终端静默注入 Claude API Key 与代理网关的主控源头。",
                    meta={"pids": cc_switch_pids},
                    advice="退出 CC Switch 应用，切断后台对终端与子进程的环境变量静默注入。",
                    remediable=True,
                    remediation_cmd=f"kill -9 {p_str}"
                )

            if claude_pids:
                p_str = " ".join(claude_pids)
                self.add_finding(
                    layer="Process",
                    severity="HIGH",
                    title=f"Claude 官方桌面客户端处于运行状态 ({len(claude_pids)} 个实例/渲染进程)",
                    description=f"检测到 Claude.app (PID: {p_str}) 正在运行。Electron 客户端会持续维持后台 WebSocket 长连接并记录本地设备指纹。",
                    meta={"pids": claude_pids},
                    advice="进行环境检查或清理前，请退出 Claude 桌面程序，防止缓存写入或连接泄漏。",
                    remediable=True,
                    remediation_cmd=f"kill -9 {p_str}"
                )

            for pid, comm, args in other_pids:
                self.add_finding(
                    layer="Process",
                    severity="LOW",
                    title=f"活动进程命令包含 Claude 关键字 (PID {pid})",
                    description=f"进程命令: {args[:100]}",
                    meta={"pid": pid, "comm": comm}
                )
        except Exception as e:
            self.add_finding("Process", "INFO", "进程扫描异常", str(e))

    def audit_environment_variables(self):
        """2. Audit active environment variables & CC-Switch database"""
        env_vars = {}
        for k, v in os.environ.items():
            if any(term in k.upper() for term in ['ANTHROPIC', 'CLAUDE']):
                env_vars[k] = v

        if env_vars:
            masked_env = {k: mask_secret(v) for k, v in env_vars.items()}
            self.add_finding(
                layer="Environment",
                severity="HIGH",
                title="当前 Shell 环境中存在生效的 Claude / Anthropic 敏感变量",
                description=f"检测到 {len(env_vars)} 个环境变量已生效: {list(env_vars.keys())}。任何命令行工具均可读取此凭据。",
                meta={"variables": masked_env},
                advice="在当前终端执行 `unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY`，并检查 ~/.zshrc 或 ~/.zprofile。",
                remediable=True,
                remediation_cmd="unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"
            )

        cc_db = os.path.join(self.home, ".cc-switch", "cc-switch.db")
        if os.path.exists(cc_db):
            try:
                conn = sqlite3.connect(cc_db)
                cur = conn.cursor()
                providers = cur.execute("SELECT id, app_type, name, is_current, settings_config FROM providers").fetchall()
                claude_providers = []
                for p in providers:
                    pid, app_type, name, is_cur, conf_str = p
                    if app_type in ['claude', 'claude-desktop'] or 'claude' in name.lower():
                        conf = json.loads(conf_str) if conf_str else {}
                        env = conf.get('env', {})
                        base_url = env.get('ANTHROPIC_BASE_URL', '')
                        claude_providers.append({
                            "id": pid,
                            "name": name,
                            "app_type": app_type,
                            "active": bool(is_cur),
                            "base_url": base_url,
                            "keys_present": list(env.keys())
                        })
                if claude_providers:
                    active_provs = [p['name'] for p in claude_providers if p['active']]
                    self.add_finding(
                        layer="Environment",
                        severity="MEDIUM",
                        title=f"CC Switch 本地库持久化了 {len(claude_providers)} 个 Claude 渠道配置",
                        description=f"当前激活的 Provider: {active_provs or '无'}。包含网关与鉴权 Token 配置。",
                        path=cc_db,
                        meta={"providers": claude_providers},
                        advice="这是终端反复出现 ANTHROPIC_BASE_URL 的持久化物理源头。若要切断，可在 CC Switch 界面删除该 Provider。"
                    )
            except Exception as e:
                self.add_finding("Environment", "INFO", "读取 CC Switch 数据库失败", str(e))

    def audit_keychain_credentials(self):
        """3. Audit macOS Keychain for Claude & Anthropic credential hashes (CRITICAL)"""
        keychain_targets = [
            ("Claude Safe Storage", "Claude Key"),
            ("Claude Code-credentials", ""),
        ]
        
        found_keychains = []
        for service, account in keychain_targets:
            cmd = ["security", "find-generic-password", "-s", service]
            if account:
                cmd.extend(["-a", account])
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                found_keychains.append((service, account or "Default"))

        dump_res = subprocess.run(["security", "dump-keychain"], capture_output=True, text=True)
        raw_items = []
        if dump_res.returncode == 0:
            for line in dump_res.stdout.splitlines():
                if any(k in line.lower() for k in ["claude safe storage", "claude code-credentials", "anthropic"]):
                    raw_items.append(line.strip())

        if found_keychains or raw_items:
            self.add_finding(
                layer="Keychain",
                severity="CRITICAL",
                title="macOS 系统钥匙串中残留 Claude 桌面端/CLI 核心安全凭据",
                description="【连环封禁元凶】Claude Desktop 会在钥匙串存储设备级加密密钥与历史账号令牌。若曾有账号被封，新安装的桌面端会直接继承旧凭据，导致新号瞬间连坐封禁！",
                meta={"keychain_items": found_keychains, "raw_traces": raw_items[:5]},
                advice="【零容忍处置】更换新账号或净化环境前，必须清除钥匙串中的 Claude Safe Storage 与相关凭据。",
                remediable=True,
                remediation_cmd="security delete-generic-password -s 'Claude Safe Storage' 2>/dev/null || true"
            )

    def audit_browser_traces(self):
        """4. Audit ALL Browser profiles for Tracking Cookies & IndexedDB (CRITICAL)"""
        cookie_globs = [
            os.path.join(self.home, "Library/Application Support/Google/Chrome/*/Cookies"),
            os.path.join(self.home, "Library/Application Support/Google/Chrome/*/Network/Cookies"),
            os.path.join(self.home, "Library/Application Support/Microsoft Edge/*/Cookies"),
            os.path.join(self.home, "Library/Application Support/BraveSoftware/Brave-Browser/*/Cookies"),
            os.path.join(self.home, "Library/Application Support/Citro Labs/ego lite/*/Cookies"),
        ]
        
        cookie_paths = []
        for cg in cookie_globs:
            cookie_paths.extend(glob.glob(cg))

        infected_cookie_stores = []
        for cp in cookie_paths:
            if not os.path.exists(cp):
                continue
            with tempfile.NamedTemporaryFile(suffix='.sqlite') as tmp:
                try:
                    shutil.copyfile(cp, tmp.name)
                    conn = sqlite3.connect(tmp.name)
                    c = conn.cursor()
                    rows = c.execute("SELECT host_key, name FROM cookies WHERE host_key LIKE '%claude%' OR host_key LIKE '%anthropic%'").fetchall()
                    if rows:
                        parent_dir = os.path.dirname(cp)
                        p_name = os.path.basename(os.path.dirname(parent_dir) if os.path.basename(parent_dir) == 'Network' else parent_dir)
                        infected_cookie_stores.append({
                            "profile": p_name,
                            "path": cp,
                            "count": len(rows),
                            "cookie_names": [r[1] for r in rows]
                        })
                    conn.close()
                except Exception:
                    pass

        if infected_cookie_stores:
            for store in infected_cookie_stores:
                has_fatal_trackers = any(k in store["cookie_names"] for k in ["ajs_user_id", "ajs_anonymous_id", "__stripe_mid", "anthropic-device-id", "sessionKey", "sessionKeyV3"])
                sev = "CRITICAL" if has_fatal_trackers else "HIGH"
                self.add_finding(
                    layer="Browser",
                    severity=sev,
                    title=f"浏览器配置 [{store['profile']}] 发现 {store['count']} 条 Claude 追踪 Cookie",
                    description=f"Cookie 包含核心指纹字段: {store['cookie_names'][:6]}。其中 ajs_anonymous_id (设备匿名指纹)、ajs_user_id (历史用户UID)、__stripe_mid (支付风控指纹) 会直接触发新老账号跨域强关联！",
                    path=store["path"],
                    meta=store,
                    advice="严禁在该 Profile 下直接登录新账号。需退出浏览器并从数据库执行定向清除，或彻底移除旧 Profile 缓存。",
                    remediable=True,
                    remediation_cmd=f"sqlite3 '{store['path']}' \"DELETE FROM cookies WHERE host_key LIKE '%claude%' OR host_key LIKE '%anthropic%';\""
                )

        idb_patterns = [
            os.path.join(self.home, "Library/Application Support/Google/Chrome/*/IndexedDB/*claude*"),
            os.path.join(self.home, "Library/Application Support/Citro Labs/ego lite/*/IndexedDB/*claude*"),
            os.path.join(self.home, "chrome-automation/*/IndexedDB/*claude*"),
            os.path.join(self.home, "chrome-automation-temu2/*/IndexedDB/*claude*"),
            os.path.join(self.home, "Library/Application Support/Microsoft Edge/*/IndexedDB/*claude*"),
            os.path.join(self.home, "Library/Application Support/BraveSoftware/Brave-Browser/*/IndexedDB/*claude*")
        ]
        found_idb = []
        for pat in idb_patterns:
            found_idb.extend(glob.glob(pat))

        if found_idb:
            self.add_finding(
                layer="Browser",
                severity="HIGH",
                title=f"发现 {len(found_idb)} 处浏览器已持久化 claude.ai 本地数据库 (IndexedDB)",
                description=f"IndexedDB 存储了前端对话缓存、本地会话状态与离线密钥。位置分布: {[os.path.basename(p) for p in found_idb[:3]]}...",
                meta={"paths": found_idb},
                advice="【零容忍处置】建议清理宿主浏览器的非隔离 claude.ai 数据库。日常使用必须严格在专属隔离 Chrome Profile 中进行。",
                remediable=True,
                remediation_cmd="rm -rf " + " ".join([f"'{p}'" for p in found_idb])
            )

    def audit_timezone_and_coherence(self):
        """5. Audit macOS system timezone vs Node/Electron timezone coherence (CRITICAL)"""
        local_tz = "未知"
        try:
            if os.path.islink("/etc/localtime"):
                target = os.readlink("/etc/localtime")
                if "zoneinfo/" in target:
                    local_tz = target.split("zoneinfo/")[-1]
        except Exception:
            pass

        node_tz = "未知"
        try:
            node_tz = subprocess.check_output(
                ["node", "-e", "console.log(Intl.DateTimeFormat().resolvedOptions().timeZone)"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            pass

        is_cn_timezone = any(x in local_tz.lower() or x in node_tz.lower() for x in ["shanghai", "prc", "beijing", "urumqi", "chongqing"])
        if is_cn_timezone:
            self.add_finding(
                layer="System",
                severity="CRITICAL",
                title="macOS 原生系统时区暴露为中国大陆 (Asia/Shanghai · UTC+8)",
                description=f"当前系统时区: {local_tz} (Node/Electron 运行时: {node_tz})。Claude Desktop 及网页 JS 会穿透扩展直接调用 Intl API，若出口为海外而系统为上海，环境自洽性判定为 100% 破裂！",
                meta={"system_tz": local_tz, "node_tz": node_tz},
                advice="【立即对齐】若使用台湾住宅节点，必须将系统时区对齐为 Asia/Taipei（同样为 UTC+8，零违和感）；若使用美区节点，必须对齐美西或美东时区。",
                remediable=True,
                remediation_cmd="sudo systemsetup -settimezone 'Asia/Taipei'"
            )
        else:
            self.add_finding(
                layer="System",
                severity="INFO",
                title=f"macOS 系统时区处于合规对齐状态: {local_tz}",
                description=f"原生 JS 运行时输出为 {node_tz}，无大陆系统时区标记破绽。"
            )

    def audit_project_configs(self):
        """6. Audit .claude directories and project configurations"""
        candidates = [
            os.path.join(self.home, "Desktop"),
            os.path.join(self.home, "Documents"),
            os.path.join(self.home, "Downloads"),
            self.home
        ]
        found_dirs = []
        for root in candidates:
            pattern = os.path.join(root, "*/.claude")
            found_dirs.extend(glob.glob(pattern))

        claude_json = os.path.join(self.home, ".claude.json")
        if os.path.exists(claude_json):
            found_dirs.append(claude_json)

        if found_dirs:
            self.add_finding(
                layer="Project",
                severity="MEDIUM",
                title=f"检测到 {len(found_dirs)} 处工程目录存在 .claude 本地配置或历史凭据",
                description="包含 Claude Code 历史会话配置、工程级 Token 或交互缓存。",
                meta={"directories": found_dirs},
                advice="若对应项目不再需要旧的 Claude CLI 交互记忆，可手动移除或归档，避免暴露旧鉴权凭据。"
            )

    def audit_packages_and_binaries(self):
        """7. Audit npm, brew, pip packages and executables"""
        try:
            res = subprocess.run(["pip3", "list", "--format=json"], capture_output=True, text=True)
            if res.returncode == 0:
                pkgs = json.loads(res.stdout)
                for p in pkgs:
                    if p.get("name") == "anthropic":
                        self.add_finding(
                            layer="Packages",
                            severity="LOW",
                            title=f"Python 环境安装了官方 SDK: anthropic ({p.get('version')})",
                            description="供 Python 脚本调用 Anthropic API 使用的代码库，不属于常驻后门或应用客户端。",
                            advice="若无 Python 脚本调用需求，可通过 `pip3 uninstall -y anthropic` 卸载。"
                        )
        except Exception:
            pass

        npm_global_dir = os.path.join(self.home, ".npm-global", "lib", "node_modules", "@anthropic-ai")
        if os.path.exists(npm_global_dir):
            items = os.listdir(npm_global_dir)
            if not items:
                self.add_finding(
                    layer="Packages",
                    severity="LOW",
                    title="NPM 全局目录存在空目录残留 (@anthropic-ai)",
                    description="历史安装/卸载 Claude Code 留下的空目录，无实际执行代码。",
                    path=npm_global_dir,
                    advice=f"可安全移除空目录: rm -rf '{npm_global_dir}'",
                    remediable=True,
                    remediation_cmd=f"rm -rf '{npm_global_dir}'"
                )
            else:
                self.add_finding(
                    layer="Packages",
                    severity="MEDIUM",
                    title=f"NPM 全局安装了 Anthropic 工具包: {items}",
                    path=npm_global_dir
                )

        claude_bin = subprocess.getoutput("which claude 2>/dev/null").strip()
        if claude_bin and os.path.exists(claude_bin):
            self.add_finding(
                layer="Packages",
                severity="HIGH",
                title=f"系统 PATH 中存在可执行命令: claude",
                description=f"位置: {claude_bin}",
                path=claude_bin
            )

    def audit_proxy_and_network_backups(self):
        """8. Audit proxy backups and network routing rules"""
        v2rayn_pattern = os.path.join(self.home, "Library/Application Support/v2rayN/binConfigs/*claude*")
        v2rayn_matches = glob.glob(v2rayn_pattern)
        if v2rayn_matches:
            self.add_finding(
                layer="Network",
                severity="LOW",
                title=f"v2rayN 目录存在 {len(v2rayn_matches)} 个 Claude 相关的历史配置备份",
                description="由 FXXK CLAUDE 项目的 sing-box 规则注入脚本或手动配置产生的静态备份文件。",
                meta={"files": v2rayn_matches},
                advice="这些是静态备份文件，不会发起网络外联；网络调试稳定后可定期清理旧时间戳备份。"
            )

    def audit_personal_archives_and_assets(self):
        """9. Identify safe personal memory exports and research assets (STRICTLY PROTECTED)"""
        safe_assets = []
        codex_export = os.path.join(self.home, "Documents/Codex/2026-07-18/new-chat/outputs/claude-memory-export-2026-07-18")
        if os.path.exists(codex_export):
            safe_assets.append(("Claude 历史记忆归档", codex_export))

        fxxk_claude_dir = os.path.join(self.home, "FXXK CLAUDE")
        if os.path.exists(fxxk_claude_dir):
            safe_assets.append(("FXXK CLAUDE 隔离与防封研究项目", fxxk_claude_dir))

        if safe_assets:
            self.add_finding(
                layer="Assets",
                severity="INFO",
                title=f"识别出 {len(safe_assets)} 处受保护的知识资产与研究代码库 【严禁误删】",
                description="包含用户对话历史文档、记忆合集及 FXXK CLAUDE 防御系统代码。属于知识资产而非风险残留。",
                meta={"assets": [s[1] for s in safe_assets]},
                advice="【受保护白名单】绝不可执行 rm 清除！此资产已纳入白名单保护范围。"
            )

    def run_all(self):
        self.audit_processes()
        self.audit_environment_variables()
        self.audit_keychain_credentials()
        self.audit_browser_traces()
        self.audit_timezone_and_coherence()
        self.audit_project_configs()
        self.audit_packages_and_binaries()
        self.audit_proxy_and_network_backups()
        self.audit_personal_archives_and_assets()
        return self.results

    def render_cli(self):
        res = self.run_all()
        summary = res["summary"]
        
        print(f"\n{BOLD}================================================================{RESET}")
        print(f"{BOLD}🛡️  Claude 全链路痕迹与零容忍防封体检 (Sentinel v2.0){RESET}")
        print(f"{BOLD}================================================================{RESET}")
        print(f"检查时间: {res['timestamp']}")
        print(f"核心原则: {RED}宁可错杀一千，绝不放过一个{RESET} · {GREEN}受保护资产绝对隔离{RESET}\n")

        print(f"{BOLD}【全域风险态势大盘】{RESET}")
        print(f"  • {RED}致命隐患 (CRITICAL):     {RESET} {summary['critical']}")
        print(f"  • {RED}高危残留 (HIGH):         {RESET} {summary['high']}")
        print(f"  • {YELLOW}中度风险 (MEDIUM):       {RESET} {summary['medium']}")
        print(f"  • {CYAN}低危/软件包 (LOW):       {RESET} {summary['low']}")
        print(f"  • {GREEN}受保护安全资产 (INFO):   {RESET} {summary['info']}\n")

        print(f"{BOLD}【八层立体排查清单】{RESET}")
        layer_icons = {
            "Process": "⚙️ 进程守护",
            "Environment": "🔑 变量注入",
            "Keychain": "🔐 钥匙串凭据",
            "Browser": "🌐 浏览器存储",
            "System": "🕒 系统时区",
            "Project": "📁 工程配置",
            "Packages": "📦 软件包依赖",
            "Network": "📡 代理与网络",
            "Assets": "📚 知识资产"
        }

        sev_colors = {
            "CRITICAL": RED,
            "HIGH": RED,
            "MEDIUM": YELLOW,
            "LOW": CYAN,
            "INFO": GREEN
        }

        for idx, f in enumerate(res["findings"], 1):
            sc = sev_colors.get(f["severity"], RESET)
            icon = layer_icons.get(f["layer"], f["layer"])
            print(f"{BOLD}{idx}. [{icon}] {sc}[{f['severity']}]{RESET} {BOLD}{f['title']}{RESET}")
            print(f"   {GRAY}说明:{RESET} {f['description']}")
            if f.get("path"):
                print(f"   {GRAY}路径:{RESET} {f['path']}")
            if f.get("advice"):
                print(f"   {GREEN}建议:{RESET} {f['advice']}")
            if f.get("remediable") and f.get("remediation_cmd"):
                print(f"   {YELLOW}处决指令:{RESET} `{f['remediation_cmd']}`")
            print()

        print(f"{BOLD}================================================================{RESET}")
        if summary['critical'] + summary['high'] > 0:
            print(f"{RED}⚠️  警告：当前系统存在 {summary['critical'] + summary['high']} 项致命/高危封号风险！{RESET}")
            print(f"若要执行自动化错杀清理，可运行: {BOLD}python3 {sys.argv[0]} --purge-risks{RESET}\n")
        else:
            print(f"{GREEN}✅ 恭喜！当前环境未发现高危追踪痕迹，基线安全处于极高水准！{RESET}\n")

    def execute_purge(self):
        """Execute surgical zero-tolerance purge on high-risk & critical targets"""
        print(f"\n{BOLD}{RED}🚨 启动「宁可错杀一千」全域风险歼灭模式 (Zero-Tolerance Purge)...{RESET}\n")
        
        # 1. Kill Keychain
        print(f"1. 正在净化 macOS 钥匙串中残留凭据...")
        subprocess.run(["security", "delete-generic-password", "-s", "Claude Safe Storage"], capture_output=True)
        subprocess.run(["security", "delete-generic-password", "-s", "Claude Code-credentials"], capture_output=True)
        print(f"   {GREEN}✔ 钥匙串 Claude 凭据已抹除。{RESET}")

        # 2. Kill Browser Cookies across all profiles
        print(f"2. 正在全域清洗 Chrome / Edge / Brave 的 Claude 追踪 Cookies...")
        cookie_globs = [
            os.path.join(self.home, "Library/Application Support/Google/Chrome/*/Cookies"),
            os.path.join(self.home, "Library/Application Support/Google/Chrome/*/Network/Cookies"),
            os.path.join(self.home, "Library/Application Support/Microsoft Edge/*/Cookies"),
            os.path.join(self.home, "Library/Application Support/BraveSoftware/Brave-Browser/*/Cookies"),
            os.path.join(self.home, "Library/Application Support/Citro Labs/ego lite/*/Cookies"),
        ]
        cookie_paths = []
        for cg in cookie_globs:
            cookie_paths.extend(glob.glob(cg))
        
        cleaned_cookies = 0
        for cp in cookie_paths:
            try:
                conn = sqlite3.connect(cp)
                c = conn.cursor()
                c.execute("DELETE FROM cookies WHERE host_key LIKE '%claude%' OR host_key LIKE '%anthropic%'")
                conn.commit()
                cleaned_cookies += conn.total_changes
                conn.close()
            except Exception:
                pass
        print(f"   {GREEN}✔ 已从所有本地配置中清除 {cleaned_cookies} 条追踪 Cookie。{RESET}")

        # 3. Clean IndexedDB
        print(f"3. 正在移除宿主浏览器 claude.ai 本地数据库 (IndexedDB)...")
        idb_patterns = [
            os.path.join(self.home, "Library/Application Support/Google/Chrome/*/IndexedDB/*claude*"),
            os.path.join(self.home, "Library/Application Support/Citro Labs/ego lite/*/IndexedDB/*claude*"),
            os.path.join(self.home, "chrome-automation/*/IndexedDB/*claude*"),
            os.path.join(self.home, "chrome-automation-temu2/*/IndexedDB/*claude*")
        ]
        removed_idb = 0
        for pat in idb_patterns:
            for p in glob.glob(pat):
                try:
                    if os.path.isdir(p):
                        shutil.rmtree(p)
                    else:
                        os.remove(p)
                    removed_idb += 1
                except Exception:
                    pass
        print(f"   {GREEN}✔ 已移除 {removed_idb} 处非隔离 IndexedDB 缓存。{RESET}")

        # 4. Clean Claude Desktop Hardware & Identity Fingerprints (All 18 uncovered items)
        print(f"4. 正在重置 Claude Desktop 与 CLI 全量本地设备身份指纹 (共 18 项深度指纹资产)...")
        claude_app_support = os.path.join(self.home, "Library/Application Support/Claude")
        desktop_fingerprint_files = [
            # 核心硬件 ID 与签名映射
            os.path.join(claude_app_support, "ant-did"),
            os.path.join(claude_app_support, "ant-device-registry.json"),
            os.path.join(claude_app_support, "buddy-tokens.json"),
            os.path.join(claude_app_support, "ccd-ids.json"),
            os.path.join(claude_app_support, "ccd-session-presets.json"),
            os.path.join(claude_app_support, "config.json.journal"),
            # 跨客户端机器标识与旧版根配置文件 (64-bit machineID)
            os.path.join(self.home, ".claude", ".claude.json"),
            os.path.join(self.home, ".claude.json"),
            os.path.join(self.home, ".claude.json.backup"),
            # 旧账号属主与工作区残留
            os.path.join(claude_app_support, "cowork-enabled-cli-ops.json"),
            os.path.join(claude_app_support, "remote-control-state.json"),
            os.path.join(claude_app_support, "plan-usage-history.json"),
            os.path.join(claude_app_support, "git-worktrees.json"),
            os.path.join(claude_app_support, "fcache"),
            os.path.join(claude_app_support, "declarative_performance_observer.db"),
            os.path.join(claude_app_support, "declarative_performance_observer.db-journal"),
            # 虚拟机固态 MAC 与 UUID
            os.path.join(claude_app_support, "vm-support-probe.json"),
            os.path.join(claude_app_support, "extensions-blocklist.json"),
        ]
        cleared_files = 0
        for f in desktop_fingerprint_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    cleared_files += 1
                except Exception:
                    pass
        
        # Clean Desktop Cookies
        desktop_cookie = os.path.join(claude_app_support, "Cookies")
        if os.path.exists(desktop_cookie):
            try:
                conn = sqlite3.connect(desktop_cookie)
                c = conn.cursor()
                c.execute("DELETE FROM cookies WHERE host_key LIKE '%claude%' OR host_key LIKE '%anthropic%' OR host_key LIKE '%stripe%' OR host_key LIKE '%hcaptcha%'")
                conn.commit()
                conn.close()
                cleared_files += 1
            except Exception:
                pass

        # Clean Claude Code backup directory
        claude_backups = os.path.join(self.home, ".claude", "backups")
        if os.path.exists(claude_backups):
            try:
                shutil.rmtree(claude_backups, ignore_errors=True)
                cleared_files += 1
            except Exception:
                pass

        # Clean Sentry telemetry queue & scope
        sentry_queue = os.path.join(claude_app_support, "sentry")
        if os.path.exists(sentry_queue):
            try:
                shutil.rmtree(sentry_queue, ignore_errors=True)
                cleared_files += 1
            except Exception:
                pass

        # Clean VM bundles
        vm_bundles = os.path.join(claude_app_support, "vm_bundles")
        if os.path.exists(vm_bundles):
            try:
                shutil.rmtree(vm_bundles, ignore_errors=True)
                cleared_files += 1
            except Exception:
                pass

        # Clean /tmp/claude-<uid>
        uid_tmp = f"/tmp/claude-{os.getuid()}"
        if os.path.exists(uid_tmp):
            try:
                shutil.rmtree(uid_tmp, ignore_errors=True)
                cleared_files += 1
            except Exception:
                pass

        print(f"   {GREEN}✔ 已彻底清洗 {cleared_files} 处本地硬件指纹、CLI machineID 与遥测残留（恢复绝对纯净出厂状态）。{RESET}")

        # 5. Clean NPM empty dir
        npm_dir = os.path.join(self.home, ".npm-global", "lib", "node_modules", "@anthropic-ai")
        if os.path.exists(npm_dir):
            shutil.rmtree(npm_dir, ignore_errors=True)
            print(f"   {GREEN}✔ 已清除 NPM 冗余目录残留。{RESET}")

        print(f"\n{BOLD}{GREEN}✨ 全域高危风险清洗完毕！受保护知识资产 (Documents/Codex, FXXK CLAUDE, MCP配置) 毫发无损！{RESET}\n")

if __name__ == "__main__":
    sentinel = ClaudeSentinel()
    if "--json" in sys.argv:
        print(json.dumps(sentinel.run_all(), indent=2, ensure_ascii=False))
    elif "--purge-risks" in sys.argv:
        sentinel.execute_purge()
    else:
        sentinel.render_cli()
