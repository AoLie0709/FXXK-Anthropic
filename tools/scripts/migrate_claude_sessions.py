#!/usr/bin/env python3
"""
Claude Desktop & Claude Code 会话热重绑与跨账号无损迁移引擎 (Session Re-binding & Migration Engine)
Author: FXXK CLAUDE Team
Date: 2026-10-20
Version: 2.0.0

【背景与用户痛点】
当旧账号被 Anthropic 封禁（bad_standing / 403）后，用户更换新账号登录。
由于 Claude Desktop (Code tab) 将所有本地会话按 `<accountId>/<orgId>/local_<sessionId>.json` 严格分层隔离，
导致新账号登录后，客户端侧边栏空空如也，历史宝贵上下文全部“失踪”。
用户需要的不仅是导出 Markdown 离线文档，而是【登录新账号之后，客户端能直接看到会话，并无缝继续对话】！

【技术原理与全链路闭环】
1. 桌面端会话目录：`~/Library/Application Support/Claude/claude-code-sessions/<accountId>/<orgId>/local_<sessionId>.json`
2. 会话索引记录：`archived-sessions.idx` (标记归档会话)
3. 真实底层对话流：`~/.claude/projects/<slugified-project-path>/<cliSessionId>.jsonl`
4. 任务与快照：`scheduled-tasks.json`、`scratch-workspaces/<accountId>/<orgId>/`、`local-agent-mode-sessions/`
5. 纯净化重绑：
   - 提取源账号与目标账号/组织 UUID 与旧敏感邮箱（如 Apple 私密中转邮箱）
   - 将源账号下所有会话克隆并重定向至目标账号目录
   - 深度清洗 System Prompt 快照、userEmail 附件与对话元数据中的旧封禁 UUID 与旧邮箱
   - 建立 O(1) 预索引高速对齐底层 cliSessionId 和项目 jsonl 对话流
   - 完整迁移 local-agent-mode-sessions（含 rpm/manifest.json 等子目录与数据）
   - 自动生成 tar.gz 物理快照备份与 manifest 元数据，并支持一键无损 --rollback 回滚
"""

import os
import sys
import re
import json
import glob
import shutil
import argparse
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 路径常量
CLAUDE_APP_SUPPORT = os.path.expanduser("~/Library/Application Support/Claude")
CLAUDE_CODE_SESSIONS_DIR = os.path.join(CLAUDE_APP_SUPPORT, "claude-code-sessions")
LOCAL_AGENT_MODE_DIR = os.path.join(CLAUDE_APP_SUPPORT, "local-agent-mode-sessions")
SCRATCH_WORKSPACES_DIR = os.path.join(CLAUDE_APP_SUPPORT, "scratch-workspaces")
GIT_WORKTREES_FILE = os.path.join(CLAUDE_APP_SUPPORT, "git-worktrees.json")
DESKTOP_CONFIG_FILE = os.path.join(CLAUDE_APP_SUPPORT, "config.json")

CLAUDE_HOME = os.path.expanduser("~/.claude")
CLAUDE_PROJECTS_DIR = os.path.join(CLAUDE_HOME, "projects")
CLAUDE_JSON_FILE = os.path.expanduser("~/.claude.json")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))
BACKUP_ROOT = os.path.join(PROJECT_ROOT, "output/backups")

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


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


def scan_existing_accounts() -> List[Dict[str, Any]]:
    """扫描现有 claude-code-sessions 目录下的所有账号与组织"""
    results = []
    if not os.path.exists(CLAUDE_CODE_SESSIONS_DIR):
        return results

    for account_dir in os.listdir(CLAUDE_CODE_SESSIONS_DIR):
        acc_path = os.path.join(CLAUDE_CODE_SESSIONS_DIR, account_dir)
        if not os.path.isdir(acc_path) or not UUID_REGEX.match(account_dir):
            continue

        for org_dir in os.listdir(acc_path):
            org_path = os.path.join(acc_path, org_dir)
            if not os.path.isdir(org_path) or not UUID_REGEX.match(org_dir):
                continue

            session_files = glob.glob(os.path.join(org_path, "local_*.json"))
            idx_file = os.path.join(org_path, "archived-sessions.idx")
            archived_count = 0
            if os.path.exists(idx_file):
                try:
                    with open(idx_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        archived_count = len(data.get("archived", []))
                except Exception:
                    pass

            results.append({
                "account_id": account_dir,
                "org_id": org_dir,
                "path": org_path,
                "total_sessions": len(session_files),
                "archived_sessions": archived_count,
                "active_sessions": max(0, len(session_files) - archived_count),
                "mtime": os.path.getmtime(org_path)
            })
    return results


def detect_account_state() -> Dict[str, Any]:
    """深度探测系统各处登记的账号信息，智能辨别新旧账号"""
    state = {
        "cli_account": None,
        "desktop_account": None,
        "existing_session_accounts": scan_existing_accounts(),
        "inferred_source": None,
        "inferred_target": None
    }

    # 1. 探测 ~/.claude.json
    if os.path.exists(CLAUDE_JSON_FILE):
        try:
            with open(CLAUDE_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            oauth = data.get("oauthAccount", {})
            acc = oauth.get("accountUuid")
            org = oauth.get("organizationUuid")
            email = oauth.get("emailAddress")
            name = oauth.get("displayName")
            if acc and org and UUID_REGEX.match(acc) and UUID_REGEX.match(org):
                state["cli_account"] = {
                    "account_id": acc,
                    "org_id": org,
                    "email": email or "",
                    "display_name": name or "",
                    "source": "~/.claude.json"
                }
        except Exception:
            pass

    # 2. 探测 Desktop config.json
    if os.path.exists(DESKTOP_CONFIG_FILE):
        try:
            with open(DESKTOP_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            acc = data.get("lastKnownAccountUuid")
            org = None
            for k in data.keys():
                if k.startswith("dxt:allowlistEnabled:"):
                    candidate = k.split("dxt:allowlistEnabled:")[1]
                    if UUID_REGEX.match(candidate):
                        org = candidate
                        break
            if acc and org and UUID_REGEX.match(acc) and UUID_REGEX.match(org):
                state["desktop_account"] = {
                    "account_id": acc,
                    "org_id": org,
                    "email": "",
                    "display_name": "",
                    "source": "Claude Desktop config.json"
                }
        except Exception:
            pass

    # 3. 智能推导 source 与 target
    # 拥有最多会话的账号推导为 source
    session_accs = state["existing_session_accounts"]
    if session_accs:
        sorted_by_sessions = sorted(session_accs, key=lambda x: x["total_sessions"], reverse=True)
        if sorted_by_sessions[0]["total_sessions"] > 0:
            state["inferred_source"] = sorted_by_sessions[0]

    # 推导 target:
    # 优先看 desktop 或 cli 中不同于 inferred_source 的账号
    src_acc_id = state["inferred_source"]["account_id"] if state["inferred_source"] else None
    
    # 检查 desktop_account 是否是新账号
    if state["desktop_account"] and state["desktop_account"]["account_id"] != src_acc_id:
        state["inferred_target"] = state["desktop_account"]
    elif state["cli_account"] and state["cli_account"]["account_id"] != src_acc_id:
        state["inferred_target"] = state["cli_account"]
    else:
        # 检查是否有总会话为 0 的新目录
        empty_accs = [a for a in session_accs if a["total_sessions"] == 0 and a["account_id"] != src_acc_id]
        if empty_accs:
            state["inferred_target"] = {
                "account_id": empty_accs[0]["account_id"],
                "org_id": empty_accs[0]["org_id"],
                "email": "",
                "display_name": "",
                "source": "新创建的空会话目录"
            }

    return state


def sanitize_session_data(raw_data: Any, old_acc: str, new_acc: str, old_org: str, new_org: str, old_email: str = "", new_email: str = "") -> Any:
    """递归纯净化替换 session 中的旧账号/组织 UUID、旧工作区路径与旧敏感邮箱"""
    raw_str = json.dumps(raw_data, ensure_ascii=False)
    
    # 替换路径引用
    if old_acc and new_acc and old_org and new_org:
        raw_str = raw_str.replace(f"scratch-workspaces/{old_acc}/{old_org}", f"scratch-workspaces/{new_acc}/{new_org}")

    # 替换 UUID
    if old_acc and new_acc:
        raw_str = raw_str.replace(old_acc, new_acc)
    if old_org and new_org:
        raw_str = raw_str.replace(old_org, new_org)
        
    # 脱敏旧邮箱
    target_email = new_email if new_email else "developer@migrated.local"
    if old_email and "@" in old_email:
        raw_str = raw_str.replace(old_email, target_email)
        
    sanitized = json.loads(raw_str)
    return sanitized


def sanitize_transcript_file(
    transcript_path: str,
    old_acc: str,
    new_acc: str,
    old_org: str,
    new_org: str,
    old_email: str = "",
    new_email: str = "",
    dry_run: bool = False
) -> Tuple[int, int, int]:
    """
    检查并纯净化 project jsonl 对话历史。
    返回值: (total_lines, total_replacements, email_replacements)
    """
    if not os.path.exists(transcript_path):
        return 0, 0, 0

    modified = False
    new_lines = []
    replace_count = 0
    email_replace_count = 0
    total_lines = 0
    target_email = new_email if new_email else "developer@migrated.local"

    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                total_lines += 1
                curr = line
                if old_acc and old_acc in curr:
                    occ = curr.count(old_acc)
                    curr = curr.replace(old_acc, new_acc)
                    replace_count += occ
                if old_org and old_org in curr:
                    occ = curr.count(old_org)
                    curr = curr.replace(old_org, new_org)
                    replace_count += occ
                if old_email and old_email in curr:
                    occ = curr.count(old_email)
                    curr = curr.replace(old_email, target_email)
                    replace_count += occ
                    email_replace_count += occ
                new_lines.append(curr)

        if replace_count > 0:
            modified = True
            if not dry_run:
                # 备份原始文件
                bak_path = transcript_path + ".migrated.bak"
                if not os.path.exists(bak_path):
                    shutil.copy2(transcript_path, bak_path)
                with open(transcript_path, "w", encoding="utf-8") as out:
                    out.writelines(new_lines)
    except Exception as e:
        log_error(f"处理对话流 {transcript_path} 失败: {e}")
        return 0, 0, 0

    return total_lines, replace_count, email_replace_count


class ClaudeSessionMigrator:
    def __init__(
        self,
        source_acc: str,
        source_org: str,
        target_acc: str,
        target_org: str,
        old_email: str = "",
        new_email: str = "",
        dry_run: bool = False
    ):
        self.source_acc = source_acc.strip()
        self.source_org = source_org.strip()
        self.target_acc = target_acc.strip()
        self.target_org = target_org.strip()
        self.old_email = old_email.strip()
        self.new_email = new_email.strip()
        self.dry_run = dry_run

        self.source_dir = os.path.join(CLAUDE_CODE_SESSIONS_DIR, self.source_acc, self.source_org)
        self.target_dir = os.path.join(CLAUDE_CODE_SESSIONS_DIR, self.target_acc, self.target_org)
        self.transcript_index = self._build_transcript_index()

    def _build_transcript_index(self) -> Dict[str, str]:
        """建立 O(1) 检索的 cliSessionId -> jsonl 映射表"""
        index = {}
        if not os.path.exists(CLAUDE_PROJECTS_DIR):
            return index

        for proj in os.listdir(CLAUDE_PROJECTS_DIR):
            p_dir = os.path.join(CLAUDE_PROJECTS_DIR, proj)
            if not os.path.isdir(p_dir):
                continue
            for f in os.listdir(p_dir):
                if f.endswith(".jsonl"):
                    cli_id = f[:-6]
                    index[cli_id] = os.path.join(p_dir, f)
        return index

    def validate(self) -> bool:
        if not UUID_REGEX.match(self.source_acc):
            log_error(f"源账号 UUID 格式无效: {self.source_acc}")
            return False
        if not UUID_REGEX.match(self.source_org):
            log_error(f"源组织 UUID 格式无效: {self.source_org}")
            return False
        if not UUID_REGEX.match(self.target_acc):
            log_error(f"目标账号 UUID 格式无效: {self.target_acc}")
            return False
        if not UUID_REGEX.match(self.target_org):
            log_error(f"目标组织 UUID 格式无效: {self.target_org}")
            return False

        if not os.path.exists(self.source_dir):
            log_error(f"源会话目录不存在: {self.source_dir}")
            return False

        if self.source_acc == self.target_acc and self.source_org == self.target_org:
            log_error("源账号/组织与目标账号/组织完全相同，无需迁移！")
            return False

        return True

    def create_backup(self) -> str:
        """迁移前创建完整时间戳物理快照备份与 manifest"""
        os.makedirs(BACKUP_ROOT, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_ROOT, f"sessions_backup_{self.source_acc[:8]}_{ts}.tar.gz")
        manifest_file = os.path.join(BACKUP_ROOT, f"sessions_backup_{self.source_acc[:8]}_{ts}.manifest.json")

        log_info(f"正在为源会话生成安全备份: {backup_file}")
        if not self.dry_run:
            try:
                subprocess.run(
                    ["tar", "-czf", backup_file, "-C", os.path.join(CLAUDE_CODE_SESSIONS_DIR, self.source_acc), self.source_org],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                # 写入 manifest
                manifest = {
                    "timestamp": ts,
                    "source_account": self.source_acc,
                    "source_org": self.source_org,
                    "target_account": self.target_acc,
                    "target_org": self.target_org,
                    "old_email": self.old_email,
                    "new_email": self.new_email,
                    "backup_tar": backup_file
                }
                with open(manifest_file, "w", encoding="utf-8") as mf:
                    json.dump(manifest, mf, ensure_ascii=False, indent=2)
                log_success(f"快照备份与元数据生成完毕: {backup_file}")
            except Exception as e:
                log_error(f"生成快照备份失败: {e}")
        else:
            log_info(f"[DRY-RUN] 将打包备份 {self.source_dir} -> {backup_file}")
        return backup_file

    def migrate(
        self,
        active_only: bool = False,
        filter_cwd: Optional[str] = None,
        filter_title: Optional[str] = None,
        sanitize_jsonl: bool = True
    ) -> Dict[str, Any]:
        """执行会话重绑与深度热迁移"""
        stats = {
            "scanned": 0,
            "migrated": 0,
            "skipped": 0,
            "transcripts_found": 0,
            "transcripts_sanitized": 0,
            "email_replacements": 0,
            "archived_count": 0
        }

        # 检查源归档列表
        source_idx_file = os.path.join(self.source_dir, "archived-sessions.idx")
        source_archived_set = set()
        if os.path.exists(source_idx_file):
            try:
                with open(source_idx_file, "r", encoding="utf-8") as f:
                    source_archived_set = set(json.load(f).get("archived", []))
            except Exception:
                pass

        # 扫描源 session 文件
        session_files = glob.glob(os.path.join(self.source_dir, "local_*.json"))
        stats["scanned"] = len(session_files)

        if not self.dry_run:
            os.makedirs(self.target_dir, exist_ok=True)

        target_archived_list = []
        target_idx_file = os.path.join(self.target_dir, "archived-sessions.idx")
        if os.path.exists(target_idx_file):
            try:
                with open(target_idx_file, "r", encoding="utf-8") as f:
                    target_archived_list = json.load(f).get("archived", [])
            except Exception:
                pass
        target_archived_set = set(target_archived_list)

        log_info(f"开始迁移: 源账号 [{self.source_acc[:8]}...] -> 目标账号 [{self.target_acc[:8]}...]")
        if self.old_email:
            log_info(f"清洗目标邮箱: [{self.old_email}] -> [{self.new_email or 'developer@migrated.local'}]")
        log_info(f"共发现 {len(session_files)} 个源会话文件，索引了 {len(self.transcript_index)} 个项目对话流")

        for sfile in session_files:
            s_name = os.path.basename(sfile)
            s_id = s_name.replace(".json", "")

            # 过滤逻辑
            is_archived = s_id in source_archived_set
            if active_only and is_archived:
                stats["skipped"] += 1
                continue

            try:
                with open(sfile, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
            except Exception as e:
                log_warn(f"跳过损坏的 JSON 会话文件 {s_name}: {e}")
                stats["skipped"] += 1
                continue

            cwd = sdata.get("cwd", "")
            title = sdata.get("title", "")
            cli_id = sdata.get("cliSessionId", "")

            if filter_cwd and filter_cwd.lower() not in cwd.lower():
                stats["skipped"] += 1
                continue

            if filter_title and filter_title.lower() not in title.lower():
                stats["skipped"] += 1
                continue

            # 纯净化重绑
            sanitized_sdata = sanitize_session_data(
                sdata,
                old_acc=self.source_acc,
                new_acc=self.target_acc,
                old_org=self.source_org,
                new_org=self.target_org,
                old_email=self.old_email,
                new_email=self.new_email
            )

            # 写入目标目录
            target_sfile = os.path.join(self.target_dir, s_name)
            if not self.dry_run:
                with open(target_sfile, "w", encoding="utf-8") as out:
                    json.dump(sanitized_sdata, out, ensure_ascii=False, indent=2)

            if is_archived:
                target_archived_set.add(s_id)
                stats["archived_count"] += 1

            stats["migrated"] += 1

            # 检查底层 cli 对话流 (O(1) 查表)
            if cli_id and cli_id in self.transcript_index:
                t_path = self.transcript_index[cli_id]
                stats["transcripts_found"] += 1
                if sanitize_jsonl:
                    _, rep_cnt, email_rep_cnt = sanitize_transcript_file(
                        t_path,
                        old_acc=self.source_acc,
                        new_acc=self.target_acc,
                        old_org=self.source_org,
                        new_org=self.target_org,
                        old_email=self.old_email,
                        new_email=self.new_email,
                        dry_run=self.dry_run
                    )
                    if rep_cnt > 0:
                        stats["transcripts_sanitized"] += 1
                    stats["email_replacements"] += email_rep_cnt

        # 写入目标 archived-sessions.idx
        if not self.dry_run:
            idx_payload = {
                "v": 1,
                "archived": sorted(list(target_archived_set))
            }
            with open(target_idx_file, "w", encoding="utf-8") as f:
                json.dump(idx_payload, f, ensure_ascii=False)

            # 迁移 scheduled-tasks.json
            src_sched = os.path.join(self.source_dir, "scheduled-tasks.json")
            tgt_sched = os.path.join(self.target_dir, "scheduled-tasks.json")
            if os.path.exists(src_sched):
                try:
                    with open(src_sched, "r", encoding="utf-8") as sf:
                        sched_data = json.load(sf)
                    clean_sched = sanitize_session_data(
                        sched_data,
                        self.source_acc,
                        self.target_acc,
                        self.source_org,
                        self.target_org,
                        self.old_email,
                        self.new_email
                    )
                    with open(tgt_sched, "w", encoding="utf-8") as tf:
                        json.dump(clean_sched, tf, ensure_ascii=False, indent=2)
                except Exception as e:
                    log_warn(f"迁移 scheduled-tasks.json 失败: {e}")

        # 递归迁移并纯净化 local-agent-mode-sessions
        src_agent_dir = os.path.join(LOCAL_AGENT_MODE_DIR, self.source_acc, self.source_org)
        tgt_agent_dir = os.path.join(LOCAL_AGENT_MODE_DIR, self.target_acc, self.target_org)
        if os.path.exists(src_agent_dir):
            if not self.dry_run:
                os.makedirs(tgt_agent_dir, exist_ok=True)
                for root, dirs, files in os.walk(src_agent_dir):
                    rel = os.path.relpath(root, src_agent_dir)
                    dest_root = os.path.join(tgt_agent_dir, rel) if rel != "." else tgt_agent_dir
                    os.makedirs(dest_root, exist_ok=True)
                    for file in files:
                        s_f = os.path.join(root, file)
                        d_f = os.path.join(dest_root, file)
                        if file.endswith(".json"):
                            try:
                                with open(s_f, "r", encoding="utf-8") as jf:
                                    j_content = json.load(jf)
                                clean_j = sanitize_session_data(
                                    j_content,
                                    self.source_acc,
                                    self.target_acc,
                                    self.source_org,
                                    self.target_org,
                                    self.old_email,
                                    self.new_email
                                )
                                with open(d_f, "w", encoding="utf-8") as jout:
                                    json.dump(clean_j, jout, ensure_ascii=False, indent=2)
                            except Exception:
                                shutil.copy2(s_f, d_f)
                        else:
                            shutil.copy2(s_f, d_f)
            log_info(f"同步迁移 Agent Mode 会话环境: {src_agent_dir} -> {tgt_agent_dir}")

        # 递归迁移并纯净化 scratch-workspaces
        src_scratch = os.path.join(SCRATCH_WORKSPACES_DIR, self.source_acc, self.source_org)
        tgt_scratch = os.path.join(SCRATCH_WORKSPACES_DIR, self.target_acc, self.target_org)
        if os.path.exists(src_scratch):
            if not self.dry_run:
                os.makedirs(tgt_scratch, exist_ok=True)
                for s_dir in os.listdir(src_scratch):
                    s_path = os.path.join(src_scratch, s_dir)
                    t_path = os.path.join(tgt_scratch, s_dir)
                    if os.path.isdir(s_path) and not os.path.exists(t_path):
                        shutil.copytree(s_path, t_path)
                        # 清洗 scratch 中可能内嵌的 json/jsonl 文件
                        for r, _, fs in os.walk(t_path):
                            for f in fs:
                                fp = os.path.join(r, f)
                                if f.endswith(".json"):
                                    try:
                                        with open(fp, "r", encoding="utf-8") as jf:
                                            jdata = json.load(jf)
                                        clean_jd = sanitize_session_data(
                                            jdata,
                                            self.source_acc,
                                            self.target_acc,
                                            self.source_org,
                                            self.target_org,
                                            self.old_email,
                                            self.new_email
                                        )
                                        with open(fp, "w", encoding="utf-8") as out:
                                            json.dump(clean_jd, out, ensure_ascii=False, indent=2)
                                    except Exception:
                                        pass
            log_info(f"同步迁移 Scratch Workspaces: {src_scratch} -> {tgt_scratch}")

        # 修复 git-worktrees.json 路径指针 (带自动备份)
        if os.path.exists(GIT_WORKTREES_FILE) and not self.dry_run:
            try:
                bak_gw = GIT_WORKTREES_FILE + ".bak"
                if not os.path.exists(bak_gw):
                    shutil.copy2(GIT_WORKTREES_FILE, bak_gw)

                with open(GIT_WORKTREES_FILE, "r", encoding="utf-8") as gf:
                    gw_data = json.load(gf)
                clean_gw = sanitize_session_data(
                    gw_data,
                    self.source_acc,
                    self.target_acc,
                    self.source_org,
                    self.target_org,
                    self.old_email,
                    self.new_email
                )
                with open(GIT_WORKTREES_FILE, "w", encoding="utf-8") as gf:
                    json.dump(clean_gw, gf, ensure_ascii=False, indent=2)
                log_success("已同步校正 git-worktrees.json 中的工作区路径引用 (已建 .bak 备份)")
            except Exception as e:
                log_warn(f"更新 git-worktrees.json 失败: {e}")

        return stats


def rollback_migration(backup_tar_path: Optional[str] = None):
    """一键无损回滚迁移：从快照压缩包还原会话，还原 .migrated.bak，恢复 git-worktrees.json"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}=== 启动 Claude 会话迁移回滚程序 ==={Colors.RESET}\n")

    # 1. 查找备份文件
    if not backup_tar_path:
        tar_files = sorted(glob.glob(os.path.join(BACKUP_ROOT, "sessions_backup_*.tar.gz")), reverse=True)
        if not tar_files:
            log_error(f"在 {BACKUP_ROOT} 中未找到任何可用快照备份！无法回滚。")
            return
        backup_tar_path = tar_files[0]

    if not os.path.exists(backup_tar_path):
        log_error(f"指定的备份文件不存在: {backup_tar_path}")
        return

    log_info(f"选定恢复快照: {backup_tar_path}")

    # 读取 manifest
    manifest_path = backup_tar_path.replace(".tar.gz", ".manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            pass

    src_acc = manifest.get("source_account")
    src_org = manifest.get("source_org")
    tgt_acc = manifest.get("target_account")
    tgt_org = manifest.get("target_org")

    # 2. 还原 claude-code-sessions
    if src_acc and src_org:
        dest_dir = os.path.join(CLAUDE_CODE_SESSIONS_DIR, src_acc)
        os.makedirs(dest_dir, exist_ok=True)
        try:
            subprocess.run(["tar", "-xzf", backup_tar_path, "-C", dest_dir], check=True)
            log_success(f"已恢复源会话目录: {os.path.join(dest_dir, src_org)}")
        except Exception as e:
            log_error(f"解压恢复快照失败: {e}")

    # 3. 还原 ~/.claude/projects/ 下的 *.migrated.bak
    restored_transcripts = 0
    if os.path.exists(CLAUDE_PROJECTS_DIR):
        for root, _, files in os.walk(CLAUDE_PROJECTS_DIR):
            for file in files:
                if file.endswith(".migrated.bak"):
                    bak_file = os.path.join(root, file)
                    target_file = bak_file[:-13]  # remove .migrated.bak
                    shutil.move(bak_file, target_file)
                    restored_transcripts += 1
    log_success(f"已恢复 {restored_transcripts} 处项目对话流原始文件 (.migrated.bak -> .jsonl)")

    # 4. 还原 git-worktrees.json.bak
    if os.path.exists(GIT_WORKTREES_FILE + ".bak"):
        shutil.move(GIT_WORKTREES_FILE + ".bak", GIT_WORKTREES_FILE)
        log_success("已恢复 git-worktrees.json 原始文件")

    # 5. 提示目标目录状态
    if tgt_acc and tgt_org:
        tgt_dir = os.path.join(CLAUDE_CODE_SESSIONS_DIR, tgt_acc, tgt_org)
        if os.path.exists(tgt_dir):
            log_warn(f"注意：目标账号目录依然存在 ({tgt_dir})。如需完全抹除，可手动执行: rm -rf '{tgt_dir}'")

    print(f"\n{Colors.BOLD}{Colors.GREEN}[+] 回滚完成！本地会话与对话历史已完全还原至迁移前状态。{Colors.RESET}\n")


def print_account_list():
    """打印格式化账号列表看板"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== Claude 本地会话存储看板 ==={Colors.RESET}\n")
    state = detect_account_state()
    accounts = state["existing_session_accounts"]
    inferred_source = state["inferred_source"]
    inferred_target = state["inferred_target"]

    if not accounts:
        print("未在本地找到任何 Claude 会话目录。")
    else:
        for idx, acc in enumerate(accounts, 1):
            is_src = inferred_source and acc["account_id"] == inferred_source["account_id"]
            tag = f" {Colors.YELLOW}[历史会话源账号]{Colors.RESET}" if is_src else ""
            print(f"{idx}. Account UUID: {Colors.BOLD}{acc['account_id']}{Colors.RESET}{tag}")
            print(f"   Org UUID    : {acc['org_id']}")
            print(f"   会话统计    : 总计 {Colors.CYAN}{acc['total_sessions']}{Colors.RESET} | 活跃 {Colors.GREEN}{acc['active_sessions']}{Colors.RESET} | 归档 {Colors.YELLOW}{acc['archived_sessions']}{Colors.RESET}")
            print(f"   路径        : {acc['path']}\n")

    print(f"{Colors.BOLD}【运行态账号识别】:{Colors.RESET}")
    if state["cli_account"]:
        print(f"  • Claude Code CLI (~/.claude.json): Account={Colors.GREEN}{state['cli_account']['account_id']}{Colors.RESET}, Org={state['cli_account']['org_id']}")
        if state["cli_account"].get("email"):
            print(f"    Email: {state['cli_account']['email']} (Name: {state['cli_account'].get('display_name')})")
    else:
        print(f"  • Claude Code CLI: 未登录或未配置")

    if state["desktop_account"]:
        print(f"  • Claude Desktop (config.json): Account={Colors.GREEN}{state['desktop_account']['account_id']}{Colors.RESET}, Org={state['desktop_account']['org_id']}")
    else:
        print(f"  • Claude Desktop: 未检测到配置信息")

    print(f"\n{Colors.BOLD}【智能迁移推导建议】:{Colors.RESET}")
    if inferred_source:
        print(f"  • 建议源账号 (旧封号) : {Colors.YELLOW}{inferred_source['account_id']}{Colors.RESET} ({inferred_source['total_sessions']} 个会话)")
    else:
        print(f"  • 建议源账号 : 未发现包含会话的历史账号")

    if inferred_target:
        print(f"  • 建议目标账号 (新号) : {Colors.GREEN}{inferred_target['account_id']}{Colors.RESET} (来源: {inferred_target.get('source')})")
    else:
        print(f"  • 建议目标账号 : 未能自动发现新账号，请在 Claude Desktop 登录新号后重试，或手动传参 --target-account")
    print()


def main():
    parser = argparse.ArgumentParser(description="Claude Desktop & CLI 会话热重绑与跨账号无损迁移引擎 (v2.0)")
    parser.add_argument("--list", action="store_true", help="列出本地所有存在的账号、组织及会话统计看板")
    parser.add_argument("--auto", action="store_true", help="自动检测已登录的新账号与老账号，全自动迁移重绑")
    parser.add_argument("--source-account", type=str, help="源账号 UUID (被封账号)")
    parser.add_argument("--source-org", type=str, help="源组织 UUID")
    parser.add_argument("--target-account", type=str, help="目标新账号 UUID")
    parser.add_argument("--target-org", type=str, help="目标新组织 UUID")
    parser.add_argument("--old-email", type=str, help="旧账号敏感邮箱 (如 Apple 私密邮箱，自动清洗)")
    parser.add_argument("--new-email", type=str, help="新账号邮箱 (替换旧邮箱，缺省为 developer@migrated.local)")
    parser.add_argument("--active-only", action="store_true", help="仅迁移活跃中的会话，跳过归档会话")
    parser.add_argument("--filter-cwd", type=str, help="仅迁移指定工作目录下的会话 (模糊匹配)")
    parser.add_argument("--filter-title", type=str, help="仅迁移匹配标题的会话 (模糊匹配)")
    parser.add_argument("--dry-run", action="store_true", help="试运行预览，不实际修改或写入磁盘")
    parser.add_argument("--no-backup", action="store_true", help="跳过自动创建压缩包快照备份")
    parser.add_argument("--no-sanitize-jsonl", action="store_true", help="不清洗 ~/.claude/projects/ 下的 jsonl 对话流")
    parser.add_argument("--rollback", action="store_true", help="一键回滚最近一次迁移，完全恢复原始状态")
    parser.add_argument("--restore-backup", type=str, help="指定特定 tar.gz 快照文件进行回滚恢复")

    args = parser.parse_args()

    if args.list:
        print_account_list()
        return

    if args.rollback or args.restore_backup:
        rollback_migration(args.restore_backup)
        return

    state = detect_account_state()
    source_acc = args.source_account
    source_org = args.source_org
    target_acc = args.target_account
    target_org = args.target_org
    old_email = args.old_email
    new_email = args.new_email or ""

    # 尝试自动补齐
    if args.auto:
        if not state["inferred_target"]:
            log_error("未能自动检测到已登录的新账号！请先在客户端登录新号，或使用 --target-account / --target-org 手动指定。")
            return
        if not state["inferred_source"]:
            log_error("未在本地找到包含历史会话的源账号！")
            return

        source_acc = state["inferred_source"]["account_id"]
        source_org = state["inferred_source"]["org_id"]
        target_acc = state["inferred_target"]["account_id"]
        target_org = state["inferred_target"]["org_id"]
        log_info(f"自动锁定迁移路径: 老账号 [{source_acc[:8]}...] -> 新账号 [{target_acc[:8]}...]")

    # 如果指定了 target 但没指定 source，且本地仅有一个老账号源
    if target_acc and target_org and not (source_acc and source_org):
        if state["inferred_source"]:
            source_acc = state["inferred_source"]["account_id"]
            source_org = state["inferred_source"]["org_id"]
            log_info(f"自动补齐唯一源账号: [{source_acc[:8]}...]")

    # 自动探测 old_email
    if not old_email and state["cli_account"] and state["cli_account"].get("email"):
        if state["cli_account"]["account_id"] == source_acc:
            old_email = state["cli_account"]["email"]
            log_info(f"从配置中自动检测到被封邮箱: {old_email}")

    # 校验参数
    if not (source_acc and source_org and target_acc and target_org):
        log_error("缺少必要参数！请使用 --auto 或显式指定 --source-account, --source-org, --target-account, --target-org。")
        print("\n使用示例:")
        print("  1. 查看看板: python3 migrate_claude_sessions.py --list")
        print("  2. 自动迁移: python3 migrate_claude_sessions.py --auto")
        print("  3. 预演测试: python3 migrate_claude_sessions.py --auto --dry-run")
        print("  4. 目标重绑: python3 migrate_claude_sessions.py --target-account <newUuid> --target-org <newOrg>")
        print("  5. 一键回滚: python3 migrate_claude_sessions.py --rollback")
        return

    migrator = ClaudeSessionMigrator(
        source_acc=source_acc,
        source_org=source_org,
        target_acc=target_acc,
        target_org=target_org,
        old_email=old_email or "",
        new_email=new_email,
        dry_run=args.dry_run
    )

    if not migrator.validate():
        return

    # 执行前备份
    if not args.no_backup:
        migrator.create_backup()

    # 执行迁移
    stats = migrator.migrate(
        active_only=args.active_only,
        filter_cwd=args.filter_cwd,
        filter_title=args.filter_title,
        sanitize_jsonl=not args.no_sanitize_jsonl
    )

    # 结果汇报
    mode_str = f"{Colors.YELLOW}[DRY-RUN 试运行]{Colors.RESET}" if args.dry_run else f"{Colors.GREEN}[正式迁移完成]{Colors.RESET}"
    print(f"\n{Colors.BOLD}{mode_str} 迁移统计报告:{Colors.RESET}")
    print(f"  • 扫描源会话总数  : {stats['scanned']}")
    print(f"  • 成功重绑迁移会话: {Colors.GREEN}{stats['migrated']}{Colors.RESET}")
    print(f"  • 保持归档状态会话: {stats['archived_count']}")
    print(f"  • 过滤跳过会话    : {stats['skipped']}")
    print(f"  • 对齐底层对话流  : {stats['transcripts_found']}")
    print(f"  • 纯净化对话流文件: {stats['transcripts_sanitized']}")
    print(f"  • 抹除旧邮箱记录数: {Colors.GREEN}{stats['email_replacements']}{Colors.RESET}")
    print(f"\n{Colors.BOLD}{Colors.CYAN}【如何在新账号下使用】:{Colors.RESET}")
    print(f"  1. 退出并彻底重启 Claude.app (或运行 `pkill -9 -i claude`)")
    print(f"  2. 打开 Claude Desktop -> 进入 'Code' 标签页，所有历史对话将即刻出现在左侧边栏！")
    print(f"  3. 点击任意历史对话，可以直接继续发送消息与提问，模型将完美继承上下文并继续工作。")
    print(f"  4. 在终端中使用 Claude Code CLI 时，直接进入对应工程目录，`claude resume` 亦可无缝识别！")
    print(f"  5. 若遇到任何问题，可随时运行 `python3 migrate_claude_sessions.py --rollback` 瞬间恢复初始状态。\n")


if __name__ == "__main__":
    main()
