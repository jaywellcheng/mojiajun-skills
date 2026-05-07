#!/usr/bin/env python3
"""
墨家军 MEMORY.md 200行截断模块
基于 v4 方案：前200行加载到上下文，超出部分存入 memdir + DAG

调用方式:
  python3 memory_truncate.py check          # 检查当前状态
  python3 memory_truncate.py split           # 拆分超限条目到memdir
  python3 memory_truncate.py expand <id>     # 按需展开被截断的条目
"""

import os, sys, json, re, pymysql, hashlib
from pathlib import Path
from datetime import datetime

# 配置
MEMORY_DIR = Path.home() / ".hermes" / "memories"
MEMDIR_DIR = MEMORY_DIR / "memdir"
MEMORY_FILE = MEMORY_DIR / "memory.md"
USER_FILE = MEMORY_DIR / "USER.md"
MAX_LINES = 200
MAX_BYTES = 25 * 1024  # 25KB

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "ceramic_2026",
    "database": "ceramic_db",
    "charset": "utf8mb4",
}


def get_db():
    return pymysql.connect(**DB_CONFIG)


def check():
    """检查 memory.md 状态"""
    if not MEMORY_FILE.exists():
        print("❌ memory.md not found")
        return

    lines = MEMORY_FILE.read_text().split('\n')
    chars = len('\n'.join(lines))
    
    print(f"MEMORY.md: {len(lines)} 行 / {chars} 字符")
    print(f"上限: {MAX_LINES} 行 / {MAX_BYTES} 字符")
    
    if len(lines) > MAX_LINES:
        print(f"⚠️ 超过行数上限! 超出 {len(lines) - MAX_LINES} 行")
    elif chars > MAX_BYTES:
        print(f"⚠️ 超过字节上限! 超出 {chars - MAX_BYTES} 字节")
    else:
        pct_lines = len(lines) / MAX_LINES * 100
        print(f"✅ 在安全范围内 ({pct_lines:.0f}% 行, {chars/MAX_BYTES*100:.0f}% 字节)")
    
    # 检查 memdir 状态
    if MEMDIR_DIR.exists():
        files = list(MEMDIR_DIR.glob("*.md"))
        print(f"\nmemdir: {len(files)} 个文件")
    else:
        print("\nmemdir: 未创建")


def split():
    """将 memory.md 超限部分拆入 memdir，保留前200行"""
    if not MEMORY_FILE.exists():
        print("❌ memory.md not found")
        return

    content = MEMORY_FILE.read_text()
    lines = content.split('\n')
    
    if len(lines) <= MAX_LINES:
        print(f"✅ {len(lines)} 行，未超 {MAX_LINES} 行上限，无需拆分")
        return

    # 按 § 分隔符拆分条目
    sections = re.split(r'\n(?=## )', content)  # 按 ## 标题拆分
    if len(sections) < 2:
        sections = content.split('§\n')  # 按 § 分隔符拆分
    
    # 前200行保留
    kept = '\n'.join(lines[:MAX_LINES])
    
    # 超出部分存入 memdir
    MEMDIR_DIR.mkdir(parents=True, exist_ok=True)
    overflow = '\n'.join(lines[MAX_LINES:])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    overflow_file = MEMDIR_DIR / f"memory_overflow_{timestamp}.md"
    overflow_file.write_text(overflow)
    
    # 更新 INDEX.md
    index_file = MEMDIR_DIR / "INDEX.md"
    index_entries = []
    if index_file.exists():
        index_entries = index_file.read_text().split('\n')
    
    entry = f"- [{overflow_file.name}]({overflow_file.name}) — {len(overflow.split(chr(10)))} 行 — {datetime.now().strftime('%Y-%m-%d')}"
    index_entries.append(entry)
    index_file.write_text('\n'.join(index_entries))
    
    # 写入 DAG 节点
    try:
        conn = get_db()
        cur = conn.cursor()
        ts = int(datetime.now().timestamp() * 1000000)
        node_id = f"dag_{ts}_{hashlib.sha256(overflow[:100].encode()).hexdigest()[:8]}"
        cur.execute("""
            INSERT INTO dag_nodes (id, dag_level, node_type, content, token_count, source_table, source_id)
            VALUES (%s, 0, 'original', %s, %s, 'memory_overflow', %s)
        """, (node_id, overflow, len(overflow) // 4, ts))
        conn.commit()
        cur.close()
        conn.close()
        print(f"  DAG节点: {node_id}")
    except Exception as e:
        print(f"  ⚠️ DAG写入失败: {e}")
    
    # 更新 memory.md
    MEMORY_FILE.write_text(kept + f"\n\n<!-- 超出部分已存入 memdir/{overflow_file.name}，通过 lcm_expand 按需展开 -->")
    
    print(f"✅ 拆分完成:")
    print(f"  保留: {len(kept.split(chr(10)))} 行 (~{len(kept)} 字符)")
    print(f"  移出: {len(overflow.split(chr(10)))} 行 → memdir/{overflow_file.name}")
    print(f"  INDEX: {len(index_entries)} 个条目")


def expand(entry_id):
    """按需展开被截断的记忆条目
    
    entry_id 可以是:
    - memdir 文件名 (如 memory_overflow_20260504_120000.md)
    - DAG 节点 ID (如 dag_676758_6e5d2541)
    """
    # 先尝试 memdir
    if MEMDIR_DIR.exists():
        target = MEMDIR_DIR / entry_id
        if target.exists():
            return target.read_text()
    
    # 再尝试 DAG
    try:
        conn = get_db()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT content FROM dag_nodes WHERE id = %s AND node_type = 'original'", (entry_id,))
        node = cur.fetchone()
        cur.close()
        conn.close()
        if node:
            return node["content"]
    except Exception:
        pass
    
    return f"❌ 未找到条目: {entry_id}"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="墨家军 MEMORY 200行截断")
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("check", help="检查 memory.md 状态")
    sub.add_parser("split", help="拆分超限条目到 memdir")
    
    p_expand = sub.add_parser("expand", help="按需展开截断条目")
    p_expand.add_argument("entry_id", help="memdir文件名 或 DAG节点ID")
    
    args = parser.parse_args()
    
    if args.cmd == "check":
        check()
    elif args.cmd == "split":
        split()
    elif args.cmd == "expand":
        print(expand(args.entry_id))
    else:
        parser.print_help()
