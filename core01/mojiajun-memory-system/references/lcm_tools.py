#!/usr/bin/env python3
"""
墨家军 LCM 记忆工具 — lcm_expand / lcm_describe / lcm_compact
基于 LCM 论文 + v4 升级方案，提供 DAG 节点的展开、描述和压缩能力。

调用方式:
  python3 lcm_tools.py expand <node_id>         # 展开摘要节点到原始内容
  python3 lcm_tools.py describe <node_id>        # 查看节点元数据
  python3 lcm_tools.py compact --threshold 100000 # 手动触发上下文压缩
  python3 lcm_tools.py stats                      # DAG统计
"""

import os, sys, json, re, hashlib, pymysql, time
from datetime import datetime

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "ceramic_2026",
    "database": "ceramic_db",
    "charset": "utf8mb4",
}

# 四级压缩阈值
LEVEL_THRESHOLDS = {
    0: 0,        # 每次调用前
    1: 8000,     # 8K token → Level 1
    2: 16000,    # 16K token → Level 2  
    3: 32000,    # 32K token → Level 3
}

def get_db():
    return pymysql.connect(**DB_CONFIG)


# ═══════════════════════════════════════════════════
#  lcm_expand: 展开摘要节点到原始内容
# ═══════════════════════════════════════════════════
def expand(node_id):
    """从摘要节点递归展开到原始内容"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # 查当前节点
    cur.execute("SELECT * FROM dag_nodes WHERE id = %s", (node_id,))
    node = cur.fetchone()
    
    if not node:
        cur.close()
        conn.close()
        return {"error": f"Node {node_id} not found"}
    
    # 如果是原始节点，直接返回
    if node["node_type"] == "original":
        # 更新访问计数
        cur.execute("""
            UPDATE dag_nodes SET access_count = access_count + 1, 
            last_accessed_at = NOW() WHERE id = %s
        """, (node_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {
            "node_id": node_id,
            "type": "original",
            "content": node["content"],
            "token_count": node["token_count"],
        }
    
    # 摘要节点：递归展开到原始节点
    expanded = _expand_recursive(cur, node, depth=0)
    
    # 更新访问计数
    cur.execute("""
        UPDATE dag_nodes SET access_count = access_count + 1,
        last_accessed_at = NOW() WHERE id = %s
    """, (node_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        "node_id": node_id,
        "type": node["node_type"],
        "level": node["dag_level"],
        "expanded_from": node["content"][:200] if node["content"] else None,
        "original_sources": expanded,
        "total_tokens": sum(e.get("token_count", 0) for e in expanded if e),
    }


def _expand_recursive(cur, node, depth=0, max_depth=5):
    """递归展开节点"""
    if depth > max_depth:
        return [{"warning": "max recursion depth reached", "node_id": node["id"]}]
    
    if node["node_type"] == "original":
        return [{
            "node_id": node["id"],
            "content": node["content"],
            "token_count": node["token_count"] or len(node["content"] or "") // 4,
        }]
    
    # 摘要/探索摘要/截断节点：找子节点
    cur.execute("SELECT * FROM dag_nodes WHERE parent_id = %s", (node["id"],))
    children = cur.fetchall()
    
    if not children:
        return [{"node_id": node["id"], "content": node["content"], "is_leaf": True}]
    
    results = []
    for child in children:
        results.extend(_expand_recursive(cur, child, depth + 1, max_depth))
    return results


# ═══════════════════════════════════════════════════
#  lcm_describe: 查看节点元数据
# ═══════════════════════════════════════════════════
def describe(node_id):
    """查看节点元数据（不展开内容）"""
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    cur.execute("""
        SELECT id, parent_id, dag_level, node_type, 
               token_count, schema_validated, source_table, source_id,
               access_count, last_accessed_at, created_at,
               LEFT(content, 200) as content_preview
        FROM dag_nodes WHERE id = %s
    """, (node_id,))
    node = cur.fetchone()
    
    if not node:
        cur.close()
        conn.close()
        return {"error": f"Node {node_id} not found"}
    
    # 查子节点
    cur.execute("SELECT id, dag_level, node_type FROM dag_nodes WHERE parent_id = %s", (node_id,))
    children = cur.fetchall()
    
    # 查父节点链
    lineage = []
    current_parent = node["parent_id"]
    while current_parent and len(lineage) < 10:
        cur.execute("SELECT id, dag_level, node_type FROM dag_nodes WHERE id = %s", (current_parent,))
        parent = cur.fetchone()
        if parent:
            lineage.append(parent)
            current_parent = None  # parent表没有递归查parent_id的列
            break
        break
    
    cur.close()
    conn.close()
    
    return {
        "node_id": node_id,
        "dag_level": node["dag_level"],
        "node_type": node["node_type"],
        "token_count": node["token_count"],
        "schema_validated": node["schema_validated"],
        "access_count": node["access_count"],
        "last_accessed": str(node["last_accessed_at"]) if node["last_accessed_at"] else None,
        "created": str(node["created_at"]),
        "children_count": len(children),
        "children": [{"id": c["id"], "level": c["dag_level"], "type": c["node_type"]} for c in children[:10]],
        "content_preview": node["content_preview"],
        "source": f"{node['source_table']}#{node['source_id']}" if node["source_table"] else None,
    }


# ═══════════════════════════════════════════════════
#  lcm_compact: 手动触发压缩
# ═══════════════════════════════════════════════════
def compact(source_table, source_id, content, current_tokens):
    """手动触发上下文压缩，按四级协议升级"""
    conn = get_db()
    cur = conn.cursor()
    
    # 判断当前层级
    if current_tokens <= LEVEL_THRESHOLDS[1]:
        level = 0
    elif current_tokens <= LEVEL_THRESHOLDS[2]:
        level = 1
    elif current_tokens <= LEVEL_THRESHOLDS[3]:
        level = 2
    else:
        level = 3
    
    # 生成节点ID — 用微秒级时间戳防止碰撞
    ts = int(time.time() * 1000000)
    node_id = f"dag_{ts % 1000000}_{hashlib.sha256(content[:100].encode()).hexdigest()[:8]}"
    
    # 创建原始节点（如果还不存在）
    parent_id = None
    cur.execute("SELECT id FROM dag_nodes WHERE source_table=%s AND source_id=%s AND node_type='original' LIMIT 1",
                (source_table, source_id))
    existing = cur.fetchone()
    if existing:
        parent_id = existing[0]
    else:
        ts2 = int(time.time() * 1000000)
        parent_id = f"dag_{ts2}_{hashlib.sha256(content[:100].encode()).hexdigest()[:8]}"
        cur.execute("""
            INSERT INTO dag_nodes (id, dag_level, node_type, content, token_count, source_table, source_id)
            VALUES (%s, 0, 'original', %s, %s, %s, %s)
        """, (parent_id, content, current_tokens, source_table, source_id))
    
    # 创建压缩节点
    if level == 3:
        truncated = content[:2000] + f"\n\n[截断: 原文{current_tokens}tokens, 展示前2000字符]"
        compressed = truncated
        compacted_tokens = 512
    else:
        compressed = content
        compacted_tokens = current_tokens // (2 if level == 2 else 1)
    
    cur.execute("""
        INSERT INTO dag_nodes (id, parent_id, dag_level, node_type, content, token_count, source_table, source_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (node_id, parent_id, level, 
          "truncated" if level == 3 else "summary",
          compressed, compacted_tokens, source_table, source_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        "node_id": node_id,
        "parent_id": parent_id,
        "level": level,
        "original_tokens": current_tokens,
        "compacted_tokens": compacted_tokens,
        "saved_tokens": current_tokens - compacted_tokens,
        "saved_pct": round((1 - compacted_tokens / max(1, current_tokens)) * 100, 1),
    }



# ═══════════════════════════════════════════════════
#  大文件探索摘要（>25K tokens）
# ═══════════════════════════════════════════════════
def explore_file(file_path, file_type=None):
    """生成类型感知的探索摘要，不加载全文"""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    size = os.path.getsize(file_path)
    estimated_tokens = size // 4
    
    if estimated_tokens <= 25000:
        return {"action": "load_directly", "size": size, "tokens": estimated_tokens}
    
    # 自动检测类型
    if file_type is None:
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {
            '.sql': 'sql', '.db': 'sql',
            '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
            '.py': 'code', '.js': 'code', '.ts': 'code', '.go': 'code', '.rs': 'code',
            '.md': 'text', '.txt': 'text',
        }
        file_type = type_map.get(ext, 'text')
    
    # 生成探索摘要
    summary = {"file": file_path, "size": size, "estimated_tokens": estimated_tokens, "type": file_type}
    
    try:
        with open(file_path) as f:
            head = ''.join(f.readline() for _ in range(200))
        
        if file_type == 'sql':
            # 提取表名和字段
            tables = re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', head, re.IGNORECASE)
            cols = re.findall(r'^\s+(\w+)\s+\w+', head, re.MULTILINE)
            summary["tables"] = tables[:20]
            summary["columns"] = cols[:50]
            summary["preview"] = f"{len(tables)} tables, {len(cols)} columns detected"
        
        elif file_type in ('json', 'yaml'):
            # 提取顶层键
            if file_type == 'json':
                data = json.loads(open(file_path).read()[:100000])
            else:
                import yaml
                data = yaml.safe_load(open(file_path).read()[:100000])
            if isinstance(data, dict):
                summary["top_keys"] = list(data.keys())[:30]
            elif isinstance(data, list):
                summary["array_length"] = len(data)
                if data and isinstance(data[0], dict):
                    summary["item_keys"] = list(data[0].keys())[:20]
            summary["preview"] = f"顶层结构: {list(data.keys())[:5] if isinstance(data, dict) else f'数组({len(data)}项)'}"
        
        elif file_type == 'code':
            # 提取函数/类签名
            funcs = re.findall(r'^\s*(?:async\s+)?def\s+(\w+)', head, re.MULTILINE)
            classes = re.findall(r'^\s*class\s+(\w+)', head, re.MULTILINE)
            imports = re.findall(r'^(?:from\s+\S+\s+)?import\s+(.+)', head, re.MULTILINE)
            summary["functions"] = funcs[:30]
            summary["classes"] = classes[:10]
            summary["imports"] = imports[:15]
            summary["preview"] = f"{len(funcs)} functions, {len(classes)} classes"
        
        else:
            # 非结构化文本：前200行作预览
            summary["preview"] = head[:500]
    
    except Exception as e:
        summary["error"] = str(e)
    
    return summary


# ═══════════════════════════════════════════════════
#  统计
# ═══════════════════════════════════════════════════
def stats():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT dag_level, node_type, COUNT(*) FROM dag_nodes GROUP BY dag_level, node_type ORDER BY dag_level")
    print(f"{'Level':<8} {'Type':<15} {'Count':>6}")
    print("-" * 32)
    for row in cur.fetchall():
        print(f"L{row[0]:<7} {row[1]:<15} {row[2]:>6}")
    
    cur.execute("SELECT COUNT(*) as total, SUM(token_count) as total_tokens FROM dag_nodes WHERE node_type='original'")
    total = cur.fetchone()
    print(f"\n原始节点: {total[0]} 个, 总计 {total[1] or 0} tokens")
    
    cur.execute("""
        SELECT COUNT(*) FROM dag_nodes 
        WHERE dag_level >= 1 AND node_type IN ('summary','truncated')
    """)
    comp = cur.fetchone()[0]
    print(f"压缩节点: {comp} 个")
    
    cur.close()
    conn.close()


# ═══════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="墨家军 LCM 记忆工具")
    sub = parser.add_subparsers(dest="cmd")
    
    p_expand = sub.add_parser("expand", help="展开摘要节点到原始内容")
    p_expand.add_argument("node_id")
    
    p_desc = sub.add_parser("describe", help="查看节点元数据")
    p_desc.add_argument("node_id")
    
    p_compact = sub.add_parser("compact", help="手动触发压缩")
    p_compact.add_argument("--source-table", default="memory")
    p_compact.add_argument("--source-id", type=int, default=1)
    p_compact.add_argument("--content", default="")
    p_compact.add_argument("--tokens", type=int, default=100000)
    
    p_explore = sub.add_parser("explore", help="生成大文件探索摘要")
    p_explore.add_argument("file_path")
    p_explore.add_argument("--type", default=None)
    
    sub.add_parser("stats", help="DAG统计")
    
    args = parser.parse_args()
    
    if args.cmd == "explore":
        result = explore_file(args.file_path, args.type)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "expand":
        result = expand(args.node_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "describe":
        result = describe(args.node_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "compact":
        result = compact(args.source_table, args.source_id, args.content, args.tokens)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "stats":
        stats()
    else:
        parser.print_help()
