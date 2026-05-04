#!/usr/bin/env python3
"""
墨家军 系统级Eval — 每次系统变更后14天回头看"到底有没有变好"
基于大威「自我进化」方法论：Eval不是事后诸葛亮，而是系统必需

调用方式:
  python3 sys_eval.py log "改了Memory写入规则" --type memory_update --source "自我进化文章"
  python3 sys_eval.py report           # 本周到期变更的Eval报告
  python3 sys_eval.py judge <id> yes   # 标记变更有效
  python3 sys_eval.py judge <id> no    # 标记变更无效，建议回滚
  python3 sys_eval.py stats            # 变更统计
"""

import os, sys, json, pymysql
from datetime import datetime, date, timedelta

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "ceramic_2026",
    "database": "ceramic_db",
    "charset": "utf8mb4",
}

EVAL_DAYS = 14  # 变更后14天评估

def get_db():
    return pymysql.connect(**DB_CONFIG)


# ═══════════════════════════════════════════════════
#  记录变更
# ═══════════════════════════════════════════════════
def log_change(change_type, change_desc, trigger_source=None,
               related_insight_id=None, related_skill=None):
    """记录一次系统变更"""
    conn = get_db()
    cur = conn.cursor()
    
    due_date = date.today() + timedelta(days=EVAL_DAYS)
    
    cur.execute("""
        INSERT INTO system_change_log
        (change_type, change_desc, trigger_source, related_insight_id, 
         related_skill, eval_due_date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (change_type, change_desc, trigger_source, related_insight_id,
          related_skill, due_date))
    
    change_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"📋 变更 #{change_id}: [{change_type}] {change_desc[:50]}...")
    print(f"   评估截止: {due_date} (14天后)")
    return change_id


# ═══════════════════════════════════════════════════
#  生成Eval周报
# ═══════════════════════════════════════════════════
def generate_report():
    """查看到期+即将到期的变更，生成评估报告"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # 到期未评估的
    cur.execute("""
        SELECT id, change_type, change_desc, trigger_source,
               usage_count, created_at, eval_due_date
        FROM system_change_log
        WHERE eval_due_date <= CURDATE()
          AND verdict IS NULL
        ORDER BY eval_due_date
    """)
    overdue = cur.fetchall()
    
    # 即将到期的（7天内）
    cur.execute("""
        SELECT id, change_type, change_desc, trigger_source,
               usage_count, created_at, eval_due_date
        FROM system_change_log
        WHERE eval_due_date > CURDATE() AND eval_due_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
          AND verdict IS NULL
        ORDER BY eval_due_date
    """)
    upcoming = cur.fetchall()
    
    # 已评估的统计
    cur.execute("""
        SELECT verdict, COUNT(*) as cnt
        FROM system_change_log
        WHERE verdict IS NOT NULL
        GROUP BY verdict
    """)
    verdict_stats = {row['verdict']: row['cnt'] for row in cur.fetchall()}
    
    cur.close()
    conn.close()
    
    # 打印报告
    print("=" * 60)
    print("  墨家军 系统Eval 周报")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if overdue:
        print(f"\n🔴 到期待评估 ({len(overdue)} 项):")
        print(f"  {'ID':<5} {'类型':<18} {'描述':<40} {'创建':<12} {'命中'}")
        print(f"  {'-'*80}")
        for c in overdue:
            desc = (c['change_desc'] or '')[:38]
            print(f"  {c['id']:<5} {c['change_type']:<18} {desc:<40} "
                  f"{str(c['created_at'])[:10]:<12} {c['usage_count']}")
    else:
        print("\n🟢 无到期待评估项")
    
    if upcoming:
        print(f"\n🟡 即将到期 ({len(upcoming)} 项):")
        for c in upcoming:
            desc = (c['change_desc'] or '')[:45]
            print(f"  #{c['id']} [{c['change_type']}] {desc}")
            print(f"    到期: {c['eval_due_date']} | 命中: {c['usage_count']}")
    
    if verdict_stats:
        print(f"\n📊 历史Eval统计:")
        for v, cnt in sorted(verdict_stats.items()):
            print(f"  {v}: {cnt}")
    
    # 输出可执行建议
    if overdue:
        print(f"\n💡 建议: 对上面 {len(overdue)} 项到期变更执行评估:")
        for c in overdue:
            print(f"   python3 sys_eval.py judge {c['id']} [yes|no|uncertain] "
                  f"--notes \"原因\"")
    
    return {"overdue": len(overdue), "upcoming": len(upcoming)}


# ═══════════════════════════════════════════════════
#  判定变更
# ═══════════════════════════════════════════════════
def judge_change(change_id, verdict, notes=None):
    """对变更做出判定：保留/修改/删除"""
    conn = get_db()
    cur = conn.cursor()
    
    verdict_map = {
        "yes": ("保留", "yes"),
        "no": ("删除", "no"),
        "uncertain": ("修改", "uncertain"),
    }
    
    if verdict not in verdict_map:
        print(f"❌ 无效判定: {verdict}，可选: yes/no/uncertain")
        cur.close()
        conn.close()
        return False
    
    v_label, v_improved = verdict_map[verdict]
    
    cur.execute("""
        UPDATE system_change_log
        SET output_improved = %s, verdict = %s, eval_notes = %s, eval_at = NOW()
        WHERE id = %s
    """, (v_improved, v_label, notes, change_id))
    
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    if affected:
        print(f"✅ 变更 #{change_id} → {v_label} | {notes or ''}")
    else:
        print(f"❌ 变更 #{change_id} 不存在")
    
    return affected > 0


# ═══════════════════════════════════════════════════
#  自动同步：temp_insight 升级时记录变更
# ═══════════════════════════════════════════════════
def on_insight_upgraded(insight_id, insight_content):
    """temp_insight升级到核心库时自动记录变更"""
    return log_change(
        change_type="insight_upgrade",
        change_desc=f"临时区insight升级: {insight_content[:100]}",
        trigger_source="temp_insight_verify",
        related_insight_id=insight_id,
    )


# ═══════════════════════════════════════════════════
#  统计
# ═══════════════════════════════════════════════════
def show_stats():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT change_type, COUNT(*) FROM system_change_log GROUP BY change_type")
    print("变更类型分布:")
    for row in cur.fetchall():
        print(f"  {row[0]:<25} {row[1]:>4}")
    
    cur.execute("""
        SELECT verdict, COUNT(*) FROM system_change_log 
        WHERE verdict IS NOT NULL GROUP BY verdict
    """)
    print("\nEval判定分布:")
    for row in cur.fetchall():
        print(f"  {row[0]:<25} {row[1]:>4}")
    
    cur.execute("""
        SELECT COUNT(*) FROM system_change_log 
        WHERE verdict IS NULL AND eval_due_date <= CURDATE()
    """)
    overdue = cur.fetchone()[0]
    print(f"\n🔴 到期未评估: {overdue}")
    
    cur.close()
    conn.close()


# ═══════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="墨家军 系统级Eval")
    sub = parser.add_subparsers(dest="cmd")
    
    p_log = sub.add_parser("log", help="记录系统变更")
    p_log.add_argument("desc", help="变更描述")
    p_log.add_argument("--type", default="memory_update", 
                       choices=["memory_add","memory_update","skill_update",
                               "filter_adjust","insight_upgrade"])
    p_log.add_argument("--source", default=None)
    p_log.add_argument("--insight-id", type=int, default=None)
    p_log.add_argument("--skill", default=None)
    
    sub.add_parser("report", help="生成Eval周报")
    
    p_judge = sub.add_parser("judge", help="判定变更")
    p_judge.add_argument("change_id", type=int)
    p_judge.add_argument("verdict", choices=["yes","no","uncertain"])
    p_judge.add_argument("--notes", default=None)
    
    sub.add_parser("stats", help="变更统计")
    
    args = parser.parse_args()
    
    if args.cmd == "log":
        log_change(args.type, args.desc, args.source, args.insight_id, args.skill)
    elif args.cmd == "report":
        generate_report()
    elif args.cmd == "judge":
        judge_change(args.change_id, args.verdict, args.notes)
    elif args.cmd == "stats":
        show_stats()
    else:
        parser.print_help()
