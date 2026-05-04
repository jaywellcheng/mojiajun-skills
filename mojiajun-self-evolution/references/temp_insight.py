#!/usr/bin/env python3
"""
墨家军 临时验证区 — 新insight先试用7天，≥3次命中才升级核心库
基于大威「自我进化」方法论：Memory是筛子不是仓库

三个核心函数:
  add_insight()       — 新增insight到临时区
  record_hit(id)      — Agent调用时记录命中
  verify_and_upgrade() — 周检：命中≥3升级，0归档，1-2延长
  
调用方式:
  python3 temp_insight.py add "观点内容" --source-url "xxx" --source-title "xxx"
  python3 temp_insight.py hit <insight_id> --agent "molan"
  python3 temp_insight.py verify    # 周检升级/归档
  python3 temp_insight.py stats     # 查看统计
"""

import os, sys, json, hashlib, pymysql
from datetime import datetime, date, timedelta

# ── 数据库配置 ──────────────────────────────────
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "ceramic_2026",
    "database": "ceramic_db",
    "charset": "utf8mb4",
}

VERIFY_DAYS = 7         # 验证期天数
UPGRADE_THRESHOLD = 3   # 升级阈值：命中≥3次


def get_db():
    return pymysql.connect(**DB_CONFIG)


# ═══════════════════════════════════════════════════
#  核心函数1: 新增 insight 到临时区
# ═══════════════════════════════════════════════════
def add_insight(content, source_url=None, source_title=None, 
                taste_score=None, taste_verdict=None):
    """把新 insight 写入临时验证区，7天后评估"""
    conn = get_db()
    cur = conn.cursor()
    
    deadline = date.today() + timedelta(days=VERIFY_DAYS)
    
    cur.execute("""
        INSERT INTO temp_insights 
        (content, source_url, source_title, taste_score, taste_verdict,
         status, hit_count, verify_deadline)
        VALUES (%s, %s, %s, %s, %s, 'pending_verify', 0, %s)
    """, (content, source_url, source_title, taste_score, taste_verdict, deadline))
    
    insight_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"📝 临时区 #{insight_id}: {content[:60]}...")
    print(f"   验证截止: {deadline} (需命中≥{UPGRADE_THRESHOLD}次)")
    return insight_id


# ═══════════════════════════════════════════════════
#  核心函数2: Agent调用时记录命中
# ═══════════════════════════════════════════════════
def record_hit(insight_id, agent_name="unknown"):
    """Agent引用insight时+1命中"""
    conn = get_db()
    cur = conn.cursor()
    
    # 获取当前 hit_sources
    cur.execute("SELECT hit_sources, hit_count FROM temp_insights WHERE id=%s", (insight_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        print(f"⚠️ 临时区 #{insight_id} 不存在")
        return False
    
    current_sources = json.loads(row[0]) if row[0] else []
    if agent_name not in current_sources:
        current_sources.append(agent_name)
    
    cur.execute("""
        UPDATE temp_insights 
        SET hit_count = hit_count + 1,
            hit_sources = %s
        WHERE id = %s
    """, (json.dumps(current_sources), insight_id))
    
    new_count = row[1] + 1
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"🎯 临时区 #{insight_id} 命中 +1 (总计{new_count}次, 来源:{','.join(current_sources)})")
    return True


# ═══════════════════════════════════════════════════
#  核心函数3: 周检验证 → 升级/归档/延长
# ═══════════════════════════════════════════════════
def verify_and_upgrade():
    """检查验证期到期的insight，决定升级/归档/延长"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # 查到期且待验证的
    cur.execute("""
        SELECT id, content, source_url, source_title, hit_count, 
               status, verify_deadline
        FROM temp_insights
        WHERE status = 'pending_verify'
          AND verify_deadline <= CURDATE()
    """)
    expired = cur.fetchall()
    
    if not expired:
        print("📭 没有到期待验证的insight")
        cur.close()
        conn.close()
        return {"upgraded": 0, "archived": 0, "extended": 0}
    
    stats = {"upgraded": 0, "archived": 0, "extended": 0}
    
    for item in expired:
        sid = item["id"]
        hit = item["hit_count"]
        content_preview = (item["content"] or "")[:50]
        
        if hit >= UPGRADE_THRESHOLD:
            # ✅ 升级到核心知识库
            upgraded_id = _upgrade_to_core(conn, item)
            cur.execute("""
                UPDATE temp_insights 
                SET status='verified', upgraded_at=NOW(), upgraded_to_id=%s
                WHERE id=%s
            """, (upgraded_id, sid))
            stats["upgraded"] += 1
            print(f"⬆️  #{sid}: {content_preview} → 核心库 [{hit}次命中]")
            
        elif hit == 0:
            # ❌ 零命中，归档
            cur.execute("""
                UPDATE temp_insights 
                SET status='archived', archive_reason='验证期内零调用'
                WHERE id=%s
            """, (sid,))
            stats["archived"] += 1
            print(f"🗄️  #{sid}: {content_preview} → 归档 [零命中]")
            
        else:
            # ⚠️ 1-2次命中，延长7天
            new_deadline = date.today() + timedelta(days=VERIFY_DAYS)
            cur.execute("""
                UPDATE temp_insights 
                SET status='extended', verify_deadline=%s
                WHERE id=%s
            """, (new_deadline, sid))
            stats["extended"] += 1
            print(f"⏳ #{sid}: {content_preview} → 延长至 {new_deadline} [{hit}次命中]")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n📊 本轮: ⬆️升级{stats['upgraded']} 🗄️归档{stats['archived']} ⏳延长{stats['extended']}")
    return stats


def _upgrade_to_core(conn, item):
    """将临时区insight升级写入core_knowledge_items"""
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO core_knowledge_items 
        (category, title, content, source, status, reviewed_by)
        VALUES (%s, %s, %s, %s, 'active', 'temp_insight_auto')
    """, (
        "双轨洞察",
        (item["source_title"] or "临时区洞察")[:200],
        item["content"],
        item["source_url"] or "temp_insights",
    ))
    
    upgraded_id = cur.lastrowid
    cur.close()
    return upgraded_id


# ═══════════════════════════════════════════════════
#  辅助: 获取所有可用的临时区 insight（供Agent查询）
# ═══════════════════════════════════════════════════
def get_active_insights(limit=20):
    """获取验证期中+已验证的insight，供Agent调用"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("""
        SELECT id, content, source_title, hit_count, status, verify_deadline
        FROM temp_insights
        WHERE status IN ('pending_verify', 'verified', 'extended')
        ORDER BY hit_count DESC, created_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def show_stats():
    """展示临时区统计"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT status, COUNT(*) as cnt
        FROM temp_insights
        GROUP BY status
        ORDER BY cnt DESC
    """)
    print(f"{'Status':<20} {'Count':>6}")
    print("-" * 28)
    for row in cur.fetchall():
        print(f"{row[0]:<20} {row[1]:>6}")
    cur.close()
    conn.close()


# ═══════════════════════════════════════════════════
#  CLI入口
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="墨家军 临时验证区管理")
    sub = parser.add_subparsers(dest="cmd")
    
    # add
    p_add = sub.add_parser("add", help="新增insight到临时区")
    p_add.add_argument("content", help="观点内容")
    p_add.add_argument("--source-url", default=None)
    p_add.add_argument("--source-title", default=None)
    p_add.add_argument("--taste-score", type=int, default=None)
    p_add.add_argument("--taste-verdict", default=None)
    
    # hit
    p_hit = sub.add_parser("hit", help="记录命中")
    p_hit.add_argument("insight_id", type=int)
    p_hit.add_argument("--agent", default="unknown")
    
    # verify
    sub.add_parser("verify", help="执行周检验证(升级/归档/延长)")
    
    # stats
    sub.add_parser("stats", help="查看统计")
    
    # list
    sub.add_parser("list", help="列出活跃insight")
    
    args = parser.parse_args()
    
    if args.cmd == "add":
        add_insight(args.content, args.source_url, args.source_title,
                    args.taste_score, args.taste_verdict)
    elif args.cmd == "hit":
        record_hit(args.insight_id, args.agent)
    elif args.cmd == "verify":
        verify_and_upgrade()
    elif args.cmd == "stats":
        show_stats()
    elif args.cmd == "list":
        items = get_active_insights()
        for item in items:
            print(f"#{item['id']} [{item['status']}] {item['content'][:80]} "
                  f"(命中{item['hit_count']}次)")
    else:
        parser.print_help()
