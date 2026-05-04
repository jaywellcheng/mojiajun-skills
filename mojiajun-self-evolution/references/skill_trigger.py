#!/usr/bin/env python3
"""
墨家军 Skill主动更新触发 — 高频insight → Skill更新建议
基于大威「自我进化」方法论：反复有用的方法应该变成能力

调用方式:
  python3 skill_trigger.py          # 生成Skill更新建议
"""

import os, sys, pymysql
from datetime import datetime

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "ceramic_2026",
    "database": "ceramic_db",
    "charset": "utf8mb4",
}

# 现有Skill关键词映射（用于判断insight是否已被某个Skill覆盖）
SKILL_KEYWORDS = {
    "mojiajun-xiaohongshu": ["小红书", "笔记", "标题", "封面", "运营"],
    "mojiajun-comic": ["漫画", "窑滚人生", "四格", "搞笑"],
    "mojiajun-dual-track-learning-loop": ["双轨", "学习闭环", "术", "道", "爆款"],
    "mojiajun-core-knowledge": ["知识库", "核心库", "审核", "知识", "记忆", "Memory", "记忆管理"],
    "local-content-writing": ["内容", "写作", "本地", "文案"],
}

HIT_THRESHOLD = 3  # 命中≥3次才建议升级


def get_db():
    return pymysql.connect(**DB_CONFIG)


def generate_suggestions():
    """生成Skill更新建议"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    suggestions = []
    
    # 来源1: temp_insights 中已验证的高命中 insight
    cur.execute("""
        SELECT id, content, hit_count, source_title, source_url,
               DATEDIFF(NOW(), created_at) as age_days
        FROM temp_insights
        WHERE status = 'verified'
          AND hit_count >= %s
        ORDER BY hit_count DESC
    """, (HIT_THRESHOLD,))
    
    for row in cur.fetchall():
        matched_skills = _match_skills(row['content'])
        suggestions.append({
            "source": "temp_insights",
            "source_id": row['id'],
            "content": row['content'],
            "hit_count": row['hit_count'],
            "age_days": row['age_days'],
            "matched_skills": matched_skills,
            "action": "update" if matched_skills else "new_skill",
        })
    
    # 来源2: system_change_log 中已保留的高频变更
    cur.execute("""
        SELECT id, change_type, change_desc, usage_count, trigger_source
        FROM system_change_log
        WHERE verdict = '保留'
          AND usage_count >= 2
        ORDER BY usage_count DESC
    """)
    
    for row in cur.fetchall():
        matched_skills = _match_skills(row['change_desc'])
        suggestions.append({
            "source": "system_change_log",
            "source_id": row['id'],
            "content": row['change_desc'],
            "hit_count": row['usage_count'],
            "change_type": row['change_type'],
            "matched_skills": matched_skills,
            "action": "update" if matched_skills else "new_skill",
        })
    
    cur.close()
    conn.close()
    
    # 打印建议报告
    print("=" * 60)
    print("  墨家军 Skill更新建议")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if not suggestions:
        print("\n📭 暂无可升级为Skill的高频insight")
        print("   (需要 temp_insights 命中≥3 或 system_change 调用≥2)")
        return []
    
    # 按 hit_count 排序
    suggestions.sort(key=lambda x: x['hit_count'], reverse=True)
    
    for i, s in enumerate(suggestions, 1):
        content_preview = (s['content'] or '')[:70]
        action_label = "🔄 更新现有Skill" if s['action'] == 'update' else "🆕 新建Skill"
        skill_names = ', '.join(s['matched_skills']) if s['matched_skills'] else '无匹配'
        
        print(f"\n{'─'*60}")
        print(f"建议 #{i} | {action_label}")
        print(f"来源: {s['source']} #{s['source_id']} | 命中: {s['hit_count']}次")
        if s.get('age_days'):
            print(f"已验证: {s['age_days']}天")
        print(f"观点: {content_preview}")
        print(f"可能关联Skill: {skill_names}")
        
        if s['action'] == 'update':
            print(f"💡 建议: 打开对应Skill，将这个洞察补充到Skill的流程/规则中")
        else:
            print(f"💡 建议: 考虑将此洞察抽象为新的可复用Skill")
    
    print(f"\n{'='*60}")
    print(f"共 {len(suggestions)} 条建议，请大威审核后决定是否执行")
    
    return suggestions


def _match_skills(content):
    """根据内容关键词匹配已有Skill"""
    matched = []
    content_lower = (content or '').lower()
    for skill_name, keywords in SKILL_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in content_lower:
                matched.append(skill_name)
                break
    return matched


if __name__ == "__main__":
    generate_suggestions()
