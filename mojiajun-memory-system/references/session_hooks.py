#!/usr/bin/env python3
"""
墨家军 会话钩子 — session_start / session_end 自动持久化
基于 v4 §4.8: session_end保存摘要→SQLite, session_start自动恢复

调用方式:
  python3 session_hooks.py save --project mojiajun --session xxx --summary "..." --decisions '["a","b"]' --tasks '["x","y"]'
  python3 session_hooks.py load --project mojiajun                    # 加载最近一次摘要
  python3 session_hooks.py load --project mojiajun --session xxx      # 加载指定会话
  python3 session_hooks.py list --project mojiajun                    # 列出历史会话
  python3 session_hooks.py cleanup --days 30                           # 清理30天前
"""

import os, sys, json, pymysql
from datetime import datetime, timedelta

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


def save(project_name, session_id, summary_content, key_decisions=None, open_tasks=None, token_used=0):
    """session_end: 保存会话摘要"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO session_summaries 
        (project_name, session_id, summary_content, key_decisions, open_tasks, token_used)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        project_name,
        session_id,
        summary_content,
        json.dumps(key_decisions) if key_decisions else None,
        json.dumps(open_tasks) if open_tasks else None,
        token_used,
    ))
    
    sid = cur.lastrowid
    conn.commit()
    
    # 检查是否需要压缩旧会话（保留最近30天，超过的降级）
    cutoff = datetime.now() - timedelta(days=30)
    cur.execute("""
        UPDATE session_summaries 
        SET summary_level = 3, summary_content = CONCAT(LEFT(summary_content, 200), '...[30天自动降级]')
        WHERE created_at < %s AND summary_level < 3
    """, (cutoff,))
    conn.commit()
    
    cur.close()
    conn.close()
    
    print(f"💾 会话 #{sid} 已保存 ({len(summary_content)} 字符)")
    return sid


def load(project_name, session_id=None):
    """session_start: 加载最近一次会话摘要"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    if session_id:
        cur.execute("""
            SELECT * FROM session_summaries 
            WHERE project_name = %s AND session_id = %s
            ORDER BY created_at DESC LIMIT 1
        """, (project_name, session_id))
    else:
        cur.execute("""
            SELECT * FROM session_summaries 
            WHERE project_name = %s
            ORDER BY created_at DESC LIMIT 1
        """, (project_name,))
    
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row:
        return {"found": False, "message": "无历史会话"}
    
    return {
        "found": True,
        "session_id": row["session_id"],
        "summary": row["summary_content"],
        "key_decisions": json.loads(row["key_decisions"]) if row["key_decisions"] else [],
        "open_tasks": json.loads(row["open_tasks"]) if row["open_tasks"] else [],
        "saved_at": str(row["created_at"]),
        "token_used": row["token_used"],
    }


def list_sessions(project_name, limit=10):
    """列出历史会话"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    cur.execute("""
        SELECT id, session_id, summary_level, 
               LEFT(summary_content, 100) as preview,
               token_used, created_at
        FROM session_summaries 
        WHERE project_name = %s
        ORDER BY created_at DESC LIMIT %s
    """, (project_name, limit))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"{'ID':<6} {'会话ID':<25} {'预览':<50} {'Token':>8}")
    print("-" * 95)
    for r in rows:
        sid = (r["session_id"] or "")[:24]
        preview = (r["preview"] or "")[:48]
        print(f"{r['id']:<6} {sid:<25} {preview:<50} {r['token_used'] or 0:>8}")
    
    return rows


def cleanup(days=30):
    """清理旧会话（>N天的降级为 Level 3 摘要）"""
    conn = get_db()
    cur = conn.cursor()
    
    cutoff = datetime.now() - timedelta(days=days)
    cur.execute("""
        UPDATE session_summaries 
        SET summary_level = 3,
            summary_content = CONCAT('[归档] ', LEFT(COALESCE(summary_content, ''), 200))
        WHERE created_at < %s AND summary_level < 3
    """, (cutoff,))
    
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"📦 {count} 个旧会话降级为 Level 3")
    return count


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="墨家军 会话钩子")
    sub = parser.add_subparsers(dest="cmd")
    
    p_save = sub.add_parser("save", help="保存会话摘要 (session_end)")
    p_save.add_argument("--project", default="mojiajun")
    p_save.add_argument("--session", required=True)
    p_save.add_argument("--summary", required=True)
    p_save.add_argument("--decisions", default=None)
    p_save.add_argument("--tasks", default=None)
    p_save.add_argument("--tokens", type=int, default=0)
    
    p_load = sub.add_parser("load", help="加载会话摘要 (session_start)")
    p_load.add_argument("--project", default="mojiajun")
    p_load.add_argument("--session", default=None)
    
    p_list = sub.add_parser("list", help="列出历史会话")
    p_list.add_argument("--project", default="mojiajun")
    p_list.add_argument("--limit", type=int, default=10)
    
    p_clean = sub.add_parser("cleanup", help="清理旧会话")
    p_clean.add_argument("--days", type=int, default=30)
    
    args = parser.parse_args()
    
    if args.cmd == "save":
        save(args.project, args.session, args.summary,
             json.loads(args.decisions) if args.decisions else None,
             json.loads(args.tasks) if args.tasks else None,
             args.tokens)
    elif args.cmd == "load":
        result = load(args.project, args.session)
        if result["found"]:
            print(f"📋 上次会话: {result['session_id']}")
            print(f"   保存时间: {result['saved_at']}")
            print(f"   Token消耗: {result['token_used']}")
            print(f"   关键决策: {len(result['key_decisions'])} 条")
            print(f"   未完成任务: {len(result['open_tasks'])} 条")
            print(f"\n--- 摘要 ---\n{result['summary'][:500]}")
        else:
            print(result["message"])
    elif args.cmd == "list":
        list_sessions(args.project, args.limit)
    elif args.cmd == "cleanup":
        cleanup(args.days)
    else:
        parser.print_help()
