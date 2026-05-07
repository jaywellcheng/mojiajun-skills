#!/usr/bin/env python3
"""
墨家军 LLM-Map 并行处理引擎 — 16路 Worker Pool
基于 LCM 论文 + v4 §4.6: 每条独立调LLM → Schema校验 → 自动重试 → 写入DAG

调用方式:
  python3 lcm_map.py run --input data.jsonl --prompt "提取实体" --schema entity_schema.json
  python3 lcm_map.py agentic --input tasks.jsonl  # agentic_map: 每条启动子代理
"""

import os, sys, json, time, hashlib, pymysql
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

# 配置
MAX_WORKERS = 16
MAX_RETRIES = 3

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "ceramic_2026",
    "database": "ceramic_db",
    "charset": "utf8mb4",
}

# DeepSeek API 配置
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com"


def get_db():
    return pymysql.connect(**DB_CONFIG)


# ═══════════════════════════════════════════════════
#  LLM 调用
# ═══════════════════════════════════════════════════
def call_llm(prompt: str, item: str, schema: Optional[dict] = None) -> dict:
    """单次LLM调用，带Schema校验和重试"""
    import requests
    
    system_prompt = prompt
    if schema:
        system_prompt += f"\n\n输出必须符合以下JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}"
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                f"{DEEPSEEK_BASE}/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": item},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2048,
                    "response_format": {"type": "json_object"} if schema else None,
                },
                timeout=60,
            )
            
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                # Schema校验
                if schema:
                    from jsonschema import validate, ValidationError
                    try:
                        data = json.loads(content.strip().lstrip("```json").rstrip("```").strip())
                        validate(instance=data, schema=schema)
                        return {"success": True, "data": data, "attempts": attempt}
                    except (json.JSONDecodeError, ValidationError) as e:
                        if attempt < MAX_RETRIES:
                            continue  # 重试
                        return {"success": False, "error": f"Schema validation failed after {MAX_RETRIES} attempts: {e}"}
                else:
                    try:
                        data = json.loads(content.strip().lstrip("```json").rstrip("```").strip())
                        return {"success": True, "data": data, "attempts": attempt}
                    except json.JSONDecodeError:
                        return {"success": True, "data": {"raw": content}, "attempts": attempt}
            else:
                if attempt < MAX_RETRIES:
                    time.sleep(1 * attempt)
                    continue
                return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(1 * attempt)
                continue
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "Max retries exceeded"}


# ═══════════════════════════════════════════════════
#  lcm_map: 16路并行处理
# ═══════════════════════════════════════════════════
def run_map(input_file: str, prompt: str, schema_file: str = None, concurrency: int = MAX_WORKERS):
    """
    LLM-Map: 16路并行处理JSONL数据
    
    Args:
        input_file: JSONL输入文件（每行一个JSON对象）
        prompt: LLM系统提示词
        schema_file: 可选的JSON Schema文件路径
        concurrency: 并发数（默认16）
    """
    # 加载Schema
    schema = None
    if schema_file and os.path.exists(schema_file):
        schema = json.load(open(schema_file))
    
    # 加载输入
    items = []
    with open(input_file) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(line)
    
    print(f"📊 LLM-Map: {len(items)} 条, {concurrency} 路并发")
    start = time.time()
    
    results = []
    ok_count = 0
    fail_count = 0
    
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(call_llm, prompt, item, schema): i for i, item in enumerate(items)}
        
        for future in as_completed(futures):
            idx = futures[future]
            result = future.result()
            result["index"] = idx
            results.append(result)
            
            if result["success"]:
                ok_count += 1
            else:
                fail_count += 1
    
    elapsed = time.time() - start
    
    # 写入DAG（非阻塞，失败不影响结果返回）
    dag_id = None
    try:
        dag_id = _save_to_dag(input_file, prompt, results, ok_count, fail_count, elapsed)
    except Exception as e:
        print(f"  ⚠️ DAG写入跳过: {e}")
    
    summary = {
        "dag_node_id": dag_id,
        "total": len(items),
        "success": ok_count,
        "failed": fail_count,
        "elapsed_seconds": round(elapsed, 1),
        "throughput": round(len(items) / max(0.1, elapsed), 1),
        "results": results,
    }
    
    print(f"✅ {ok_count}/{len(items)} 成功, {fail_count} 失败, {elapsed:.1f}s "
          f"({len(items)/max(0.1, elapsed):.1f} 条/秒)")
    
    return summary


def _save_to_dag(input_file, prompt, results, ok, fail, elapsed):
    """将LLM-Map结果写入DAG"""
    conn = get_db()
    cur = conn.cursor()
    
    ts = int(time.time() * 1000000)
    node_id = f"dag_{ts}_{hashlib.sha256(input_file.encode()).hexdigest()[:8]}"
    
    summary_content = json.dumps({
        "prompt": prompt[:200],
        "input_file": input_file,
        "total": len(results),
        "success": ok,
        "failed": fail,
        "elapsed": elapsed,
    }, ensure_ascii=False)
    
    cur.execute("""
        INSERT INTO dag_nodes (id, dag_level, node_type, content, token_count, source_table, source_id)
        VALUES (%s, 1, 'summary', %s, %s, 'lcm_map', 0)
    """, (node_id, summary_content, len(summary_content) // 4))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return node_id


# ═══════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="墨家军 LLM-Map 并行引擎")
    sub = parser.add_subparsers(dest="cmd")
    
    p_map = sub.add_parser("run", help="运行 lcm_map")
    p_map.add_argument("--input", required=True, help="JSONL输入文件")
    p_map.add_argument("--prompt", required=True, help="LLM系统提示词")
    p_map.add_argument("--schema", default=None, help="JSON Schema文件")
    p_map.add_argument("--concurrency", type=int, default=MAX_WORKERS)
    
    args = parser.parse_args()
    
    if args.cmd == "run":
        result = run_map(args.input, args.prompt, args.schema, args.concurrency)
        print(json.dumps({k: v for k, v in result.items() if k != "results"}, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
