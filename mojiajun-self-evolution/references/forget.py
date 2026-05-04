#!/usr/bin/env python3
"""
墨家军 遗忘机制 — 30天休眠 / 60天建议删除
基于大威「自我进化」方法论：遗忘也是一种能力，适当的遗忘让系统更健壮

调用方式:
  python3 forget.py check          # 检查休眠/可清理项
  python3 forget.py touch <id>     # 标记一次访问(Agent调用时)
  python3 forget.py cleanup        # 生成清理建议清单
"""

import os, sys, pymysql
from datetime import datetime, date, timedelta

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "ceramic_2026",
    "database": "ceramic_db",
    "charset": "utf8mb4",
}

DORMANT_DAYS = 30    # 30天未访问 → 休眠
DELETE_DAYS = 60     # 60天未访问 → 建议删除


def get_db():
    return pymysql.connect(**DB_CONFIG)


def touch(item_id):
    """Agent调用核心库知识时记录访问"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE core_knowledge_items
        SET last_accessed_at = NOW(),
            access_count = access_count + 1
        WHERE id = %s
    """, (item_id,))
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if affected:
        print(f"👆 core_knowledge #{item_id} 访问 +1")
    else:
        print(f"⚠️ core_knowledge #{item_id} 不存在")
    return affected > 0


def check():
    """检查休眠和可清理的知识条目"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    dormant_date = date.today() - timedelta(days=DORMANT_DAYS)
    delete_date = date.today() - timedelta(days=DELETE_DAYS)
    
    # 休眠：30天未访问且状态为active
    cur.execute("""
        SELECT id, category, title, access_count, last_accessed_at, 
               DATEDIFF(CURDATE(), COALESCE(last_accessed_at, created_at)) as days_idle
        FROM core_knowledge_items
        WHERE status = 'active'
          AND COALESCE(last_accessed_at, created_at) <= %s
        ORDER BY days_idle DESC
        LIMIT 30
    """, (dormant_date,))
    dormant = cur.fetchall()
    
    # 建议删除：60天未访问
    cur.execute("""
        SELECT id, category, title, access_count, last_accessed_at,
               DATEDIFF(CURDATE(), COALESCE(last_accessed_at, created_at)) as days_idle
        FROM core_knowledge_items
        WHERE status IN ('active', 'dormant')
          AND COALESCE(last_accessed_at, created_at) <= %s
        ORDER BY days_idle DESC
        LIMIT 20
    """, (delete_date,))
    doomed = cur.fetchall()
    
    cur.close()
    conn.close()
    
    print("=" * 60)
    print("  墨家军 遗忘检查")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if dormant:
        print(f"\n😴 休眠知识 (>{DORMANT_DAYS}天未访问, {len(dormant)} 项):")
        print(f"  {'ID':<6} {'分类':<18} {'标题':<35} {'空闲天数':>8}")
        print(f"  {'-'*70}")
        for item in dormant:
            title = (item['title'] or '')[:33]
            print(f"  {item['id']:<6} {item['category']:<18} {title:<35} {item['days_idle']:>8}")
    else:
        print("\n🟢 无休眠知识")
    
    if doomed:
        print(f"\n💀 建议删除 (>{DELETE_DAYS}天未访问, {len(doomed)} 项):")
        print(f"  {'ID':<6} {'分类':<18} {'标题':<35} {'空闲天数':>8}")
        print(f"  {'-'*70}")
        for item in doomed:
            title = (item['title'] or '')[:33]
            print(f"  {item['id']:<6} {item['category']:<18} {title:<35} {item['days_idle']:>8}")
        
        print(f"\n💡 自动标记为休眠: python3 forget.py dormants")
        print(f"💡 手动清理: 大威审核后执行 DELETE")
    else:
        print("\n🟢 无可建议删除项")
    
    # 也检查 temp_insights 里已验证但90天未调用的
    conn2 = get_db()
    cur2 = conn2.cursor()
    cur2.execute("""
        SELECT COUNT(*) FROM temp_insights 
        WHERE status = 'verified' 
          AND upgraded_at < DATE_SUB(NOW(), INTERVAL 90 DAY)
    """)
    stale_temp = cur2.fetchone()[0]
    cur2.close()
    
    cur2.close()
    conn2.close()
    
    if stale_temp > 0:
        print(f"\n📦 临时区冗余: {stale_temp} 条已升级>90天，可清理temp_insights记录")
    
    return {"dormant": len(dormant), "doomed": len(doomed)}


def mark_dormant():
    """批量标记休眠"""
    conn = get_db()
    cur = conn.cursor()
    dormant_date = date.today() - timedelta(days=DORMANT_DAYS)
    cur.execute("""
        UPDATE core_knowledge_items
        SET status = 'dormant'
        WHERE status = 'active'
          AND (last_accessed_at IS NULL OR last_accessed_at <= %s)
    """, (dormant_date,))
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"😴 {count} 条知识标记为休眠")
    return count


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="墨家军 遗忘机制")
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("check", help="检查休眠/可清理知识")
    
    p_touch = sub.add_parser("touch", help="标记访问")
    p_touch.add_argument("item_id", type=int)
    
    sub.add_parser("dormants", help="批量标记休眠")
    
    args = parser.parse_args()
    
    if args.cmd == "check":
        check()
    elif args.cmd == "touch":
        touch(args.item_id)
    elif args.cmd == "dormants":
        mark_dormant()
    else:
        parser.print_help()
