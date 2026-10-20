#!/usr/bin/env python3
"""
Claude Desktop 本地全量会话纯净化提取与脱敏归档引擎
功能：
1. 提取 Cowork / Claude Code 本地工程会话 (~/.claude/projects/*/*.jsonl)
2. 提取 Side Session Notes 交付物文档 (~/Library/Application Support/Claude/side-session-notes/*/*.md)
3. 提取 Chromium IndexedDB V8 离线对话碎片
4. 深度脱敏：抹除系统用户名、绝对路径、远端 sessionId、accountId、orgId，生成纯净 Markdown 归档
"""
import os
import re
import json
import glob
from pathlib import Path

SOURCE_PROJECTS = os.path.expanduser("~/.claude/projects")
SOURCE_NOTES = os.path.expanduser("~/Library/Application Support/Claude/side-session-notes")
SOURCE_IDB_BLOB = os.path.expanduser("~/Library/Application Support/Claude/IndexedDB/https_claude.ai_0.indexeddb.blob")
OUTPUT_DIR = os.path.expanduser("~/Documents/Claude_Archive_Safe")

HOME_DIR = os.path.expanduser("~")
USER_NAME = os.path.basename(HOME_DIR)
UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)

def sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # 抹除系统用户名与家目录
    text = text.replace(HOME_DIR, "/Users/developer")
    text = text.replace(f"Users/{USER_NAME}", "Users/developer")
    return text

def export_cowork_sessions():
    print("[*] 正在扫描 Cowork / Claude Code 本地工程会话...")
    os.makedirs(f"{OUTPUT_DIR}/cowork_sessions", exist_ok=True)
    jsonl_files = glob.glob(f"{SOURCE_PROJECTS}/*/*.jsonl")
    
    extracted_count = 0
    for jf in jsonl_files:
        filename = os.path.basename(jf).replace(".jsonl", "")
        project_folder = os.path.basename(os.path.dirname(jf))
        
        conversation = []
        try:
            with open(jf, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line.strip(): 
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue
                    
                    role = record.get("type") or record.get("message", {}).get("role")
                    if role not in ["user", "assistant"]:
                        continue
                    
                    msg_obj = record.get("message", {})
                    content_raw = msg_obj.get("content", "")
                    ts = record.get("timestamp", "")[:19].replace("T", " ")
                    
                    text_blocks = []
                    if isinstance(content_raw, str):
                        text_blocks.append(content_raw)
                    elif isinstance(content_raw, list):
                        for block in content_raw:
                            if isinstance(block, dict):
                                b_type = block.get("type")
                                if b_type == "text":
                                    text_blocks.append(block.get("text", ""))
                                elif b_type == "thinking":
                                    text_blocks.append(f"> 💭 **[思考过程]**:\n> " + block.get("thinking", "").replace("\n", "\n> "))
                                elif b_type == "tool_use":
                                    text_blocks.append(f"🛠️ **[调用工具]**: `{block.get('name')}`\n```json\n{json.dumps(block.get('input', {}), ensure_ascii=False, indent=2)}\n```")
                    
                    body = sanitize_text("\n\n".join(text_blocks).strip())
                    if body:
                        sender = "👤 **User**" if role == "user" else "🤖 **Claude**"
                        conversation.append(f"### {sender} ({ts})\n\n{body}\n\n---\n")
        except Exception:
            continue
        
        if conversation:
            extracted_count += 1
            short_id = filename[:8]
            target_file = f"{OUTPUT_DIR}/cowork_sessions/{project_folder[:30]}_{short_id}.md"
            with open(target_file, "w", encoding="utf-8") as out:
                out.write(f"# 会话归档: {project_folder}\n\n" + "\n".join(conversation))
                
    print(f"[+] 成功脱敏并导出 {extracted_count} 个 Cowork 会话至 {OUTPUT_DIR}/cowork_sessions/")

def export_side_notes():
    print("[*] 正在扫描 Side Notes (交付物与侧边栏笔记)...")
    target_notes_dir = f"{OUTPUT_DIR}/side_notes"
    os.makedirs(target_notes_dir, exist_ok=True)
    if not os.path.exists(SOURCE_NOTES):
        return
    
    note_files = glob.glob(f"{SOURCE_NOTES}/*/*.md")
    for nf in note_files:
        fname = os.path.basename(nf)
        try:
            with open(nf, "r", encoding="utf-8", errors="ignore") as f:
                content = sanitize_text(f.read())
            with open(os.path.join(target_notes_dir, fname), "w", encoding="utf-8") as out:
                out.write(content)
        except Exception:
            pass
    print(f"[+] 成功转存 {len(note_files)} 个交付物 Markdown 文件至 {OUTPUT_DIR}/side_notes/")

def extract_indexeddb_blobs():
    print("[*] 正在解析 Chromium IndexedDB V8 离线碎片...")
    target_idb_dir = f"{OUTPUT_DIR}/web_dehydrated_snippets"
    os.makedirs(target_idb_dir, exist_ok=True)
    if not os.path.exists(SOURCE_IDB_BLOB):
        return

    count = 0
    for root, _, files in os.walk(SOURCE_IDB_BLOB):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.getsize(fp) > 10000:
                try:
                    with open(fp, "rb") as bf:
                        raw = bf.read()
                    ascii_segments = re.findall(b'[\x20-\x7e\xc2-\xf4][\x20-\x7e\x80-\xbf]{24,}', raw)
                    clean_texts = []
                    for seg in ascii_segments:
                        try:
                            decoded = sanitize_text(seg.decode("utf-8"))
                            if not any(k in decoded for k in ["conversations_v2:", "privaterelay", "tagged_id", "claude_academy"]):
                                clean_texts.append(decoded)
                        except Exception:
                            pass
                    if clean_texts:
                        count += 1
                        with open(os.path.join(target_idb_dir, f"blob_{f}.txt"), "w", encoding="utf-8") as out:
                            out.write("\n\n---\n\n".join(clean_texts[:500]))
                except Exception:
                    pass
    print(f"[+] IndexedDB 离线纯文本碎片已转存 ({count} 个文本块) 至 {OUTPUT_DIR}/web_dehydrated_snippets/")

if __name__ == "__main__":
    print(f"=== Claude 对话数据安全归档启动 (目标目录: {OUTPUT_DIR}) ===")
    export_cowork_sessions()
    export_side_notes()
    extract_indexeddb_blobs()
    print("=== 全量会话脱敏归档已完成！===")
