#!/usr/bin/env python3
"""
autoDream — 墨家军自主学习系统
借鉴 Claude Code autoDream 设计：
  时间门 → 数据门 → 互斥锁 → Fork子Agent → 回顾→提炼→写memdir

部署: CORE-01 /home/ubuntu/mojiajun-queue/
触发: 作为 agent_worker.py 的 post-task hook 或 cron
"""

import os
import sys
import json
import time
import fcntl
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 配置
# ============================================================
KNOWLEDGE_ROOT = Path("/home/ubuntu/mojiajun-queue/knowledge")
LOCK_FILE = Path("/tmp/mojiajun_autodream.lock")
STATE_FILE = Path("/home/ubuntu/mojiajun-queue/autodream_state.json")

# 时间门：距离上次dream至少多少小时
MIN_HOURS = 6  # 初期6小时，稳定后改24

# 数据门：新增数据至少多少条
MIN_NEW_ITEMS = 5

# 扫描节流：数据门没过时，多久不重复扫描（秒）
SCAN_THROTTLE_SEC = 10 * 60  # 10分钟

# Dream Agent配置
DREAM_MODEL = "deepseek/deepseek-v4-pro"
DREAM_MAX_TURNS = 8  # 最多8轮工具调用
DREAM_TIMEOUT = 600  # 10分钟超时


# ============================================================
# 门控逻辑（借鉴 Claude Code gate order: cheapest first）
# ============================================================
def load_state():
    """加载autoDream状态"""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "last_dream_at": None,
        "last_scan_at": None,
        "dream_count": 0,
        "total_files_updated": 0,
        "cursor_markers": {}  # 各数据源的cursor
    }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def is_gate_open(state):
    """检查三道门是否全开"""

    # === Gate 1: 时间门 ===
    if state["last_dream_at"]:
        hours_since = (time.time() - state["last_dream_at"]) / 3600
        if hours_since < MIN_HOURS:
            print(f"[autoDream] ⏰ Time gate CLOSED: {hours_since:.1f}h since last dream (need {MIN_HOURS}h)")
            return False, f"time:{hours_since:.1f}h"
    else:
        hours_since = float('inf')

    # === Gate 2: 扫描节流 ===
    if state["last_scan_at"]:
        since_scan = time.time() - state["last_scan_at"]
        if since_scan < SCAN_THROTTLE_SEC:
            print(f"[autoDream] 🔍 Scan throttle: {since_scan/60:.0f}m since last scan")
            return False, f"throttle:{since_scan/60:.0f}m"

    state["last_scan_at"] = time.time()
    save_state(state)

    # === Gate 3: 数据门 ===
    new_items = count_new_data(state)
    if new_items < MIN_NEW_ITEMS:
        print(f"[autoDream] 📊 Data gate CLOSED: {new_items} new items (need {MIN_NEW_ITEMS})")
        return False, f"data:{new_items}"

    # === Gate 4: 互斥锁 ===
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[autoDream] 🔒 Lock gate CLOSED: another dream is running")
        return False, "locked"

    return True, {"hours": hours_since, "items": new_items, "lock_fd": lock_fd}


def acquire_lock():
    """获取互斥锁，防止并发dream"""
    try:
        fd = open(LOCK_FILE, 'w')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
        fd.flush()
        return fd
    except (IOError, OSError):
        return None


def release_lock(fd):
    """释放锁"""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
    except:
        pass
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


def count_new_data(state):
    """统计自上次dream以来的新数据量"""
    total = 0

    # 统计MySQL中的新数据
    try:
        cursor_marker = state["cursor_markers"].get("hot_list", "")
        result = subprocess.run(
            ["mysql", "-h", "127.0.0.1", "-u", "xiaochuan", "-pxiaochuan_2026_mjj", "mojiajun",
             "-e", f"SELECT COUNT(*) as cnt FROM hotspot_data WHERE created_at > '{cursor_marker or '1970-01-01'}'",
             "--default-character-set=utf8mb4"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                total += int(lines[1])
    except Exception as e:
        print(f"[autoDream] MySQL count error: {e}")

    # 统计knowledge目录中最近修改的文件
    since = state.get("last_dream_at") or (time.time() - 86400)  # 默认24小时
    since_str = datetime.fromtimestamp(since).strftime('%Y-%m-%d')
    try:
        for cat_dir in KNOWLEDGE_ROOT.iterdir():
            if not cat_dir.is_dir():
                continue
            for f in cat_dir.glob("*.md"):
                if f.stat().st_mtime > since:
                    total += 1
    except Exception as e:
        print(f"[autoDream] file count error: {e}")

    return total


# ============================================================
# 数据采集（Python预采集，避免AI无工具可用）
# ============================================================
def collect_context(state):
    """采集当前数据快照，作为AI分析的上下文"""
    context_parts = []
    
    # 1. memdir当前状态
    index_path = KNOWLEDGE_ROOT / "INDEX.md"
    if index_path.exists():
        context_parts.append(f"## 现有知识索引\n```markdown\n{index_path.read_text(encoding='utf-8')[:3000]}\n```")
    
    # 2. MySQL数据采样
    queries = {
        "hotspot_data": "SELECT title, source, engagement, created_at FROM hotspot_data ORDER BY created_at DESC LIMIT 10",
        "daily_ai_news": "SELECT title, summary, created_at FROM daily_ai_news ORDER BY created_at DESC LIMIT 5",
        "xhs_sample_library": "SELECT title, likes, collects, comments, note_type, created_at FROM xhs_sample_library ORDER BY created_at DESC LIMIT 15",
    }
    
    for table, query in queries.items():
        try:
            result = subprocess.run(
                ["mysql", "-h", "127.0.0.1", "-u", "xiaochuan", "-pxiaochuan_2026_mjj", 
                 "mojiajun", "-e", query, "--default-character-set=utf8mb4"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    context_parts.append(f"## {table} ({len(lines)-1} rows)\n```\n{chr(10).join(lines[:16])}\n```")
        except Exception as e:
            context_parts.append(f"## {table}: Error - {e}")
    
    return '\n\n'.join(context_parts)


# ============================================================
# Dream Agent 核心逻辑
# ============================================================
def build_dream_prompt(state, context_data):
    """构建dream提示词——上下文数据+分析指令"""
    hours_since = "首次运行"
    if state["last_dream_at"]:
        hours_since = f"{(time.time() - state['last_dream_at'])/3600:.1f}小时"
    
    return f"""# 墨家军自主学习任务 (autoDream #{state['dream_count']+1})

你是墨家军的自主学习Agent。以下是最近{hours_since}的数据快照和现有知识。

{context_data}

## 你的任务

分析以上数据，提炼洞察并按以下格式输出：

### 发现
用2-3句话总结最重要的发现。

### 新增知识（如果需要）
如果有值得记录的新知识，请以以下格式输出每条：
```
KNOWLEDGE: category|filename|title|content
```
其中 category 是 content/user/system/market 之一。

### 需更新知识（如果需要）
```
UPDATE: category/filename.md|修改说明
```

### 无需更新
如果数据中没有值得记录的新发现，只需回复"无需更新"。

## 约束
- 用中文，简洁务实
- 只记录经过验证的模式，不要猜测
- 空数据或质量差就说无需更新
"""


def call_deepseek(prompt: str) -> str:
    """直接调用DeepSeek API进行自主学习分析"""
    import urllib.request, urllib.error
    
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        env_file = Path("/home/ubuntu/mojiajun-queue/.env")
        if env_file.exists():
            for line in env_file.read_text().split('\n'):
                if line.startswith('DEEPSEEK_API_KEY='):
                    api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
    
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not found")
    
    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是墨家军自主学习Agent。分析数据、提炼洞察、输出结构化结果。用中文回复，简洁务实。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.3
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        raise RuntimeError(f"DeepSeek API error {e.code}: {error_body[:500]}")


def execute_dream(state):
    """执行dream任务——采集数据→AI分析→提取动作→执行"""
    
    print(f"[autoDream] 🌙 Starting dream #{state['dream_count']+1}...")
    start_time = time.time()
    files_before = set()
    
    for cat_dir in KNOWLEDGE_ROOT.iterdir():
        if not cat_dir.is_dir():
            continue
        for f in cat_dir.glob("*.md"):
            files_before.add(str(f))
    
    try:
        # 阶段1: Python采集数据
        print("[autoDream] 📊 Collecting context data...")
        context_data = collect_context(state)
        print(f"[autoDream] 📊 Context: {len(context_data)} chars")
        
        # 阶段2: AI分析
        prompt = build_dream_prompt(state, context_data)
        print(f"[autoDream] 📝 Prompt: {len(prompt)} chars")
        print("[autoDream] 🤖 Calling DeepSeek for analysis...")
        
        analysis = call_deepseek(prompt)
        output_file = Path("/tmp/autodream_output.md")
        output_file.write_text(analysis, encoding='utf-8')
        print(f"[autoDream] 📄 Analysis: {len(analysis)} chars")
        
        # 阶段3: 提取并执行KNOWLEDGE/UPDATE指令
        knowledge_items = []
        update_items = []
        
        for line in analysis.split('\n'):
            line = line.strip()
            if line.startswith('KNOWLEDGE:'):
                parts = line[10:].strip().split('|', 3)
                if len(parts) >= 4:
                    knowledge_items.append({
                        "category": parts[0].strip(),
                        "filename": parts[1].strip(),
                        "title": parts[2].strip(),
                        "content": parts[3].strip()
                    })
            elif line.startswith('UPDATE:'):
                parts = line[7:].strip().split('|', 1)
                if len(parts) >= 2:
                    update_items.append({"file": parts[0].strip(), "note": parts[1].strip()})
        
        # 执行知识写入
        for item in knowledge_items:
            try:
                cat = item["category"]
                if cat not in ["content", "user", "system", "market"]:
                    cat = "content"
                fname = item["filename"]
                if not fname.endswith('.md'):
                    fname += '.md'
                
                print(f"[autoDream] 📝 Writing {cat}/{fname}: {item['title'][:50]}")
                subprocess.run(
                    ["python3", "memdir_manager.py", "add", cat, fname, item["title"], item["content"]],
                    capture_output=True, text=True, timeout=15,
                    cwd="/home/ubuntu/mojiajun-queue"
                )
            except Exception as e:
                print(f"[autoDream] ⚠️ Write failed for {item.get('title', '?')}: {e}")
        
        # 检测新文件
        files_after = set()
        for cat_dir in KNOWLEDGE_ROOT.iterdir():
            if not cat_dir.is_dir():
                continue
            for f in cat_dir.glob("*.md"):
                files_after.add(str(f))
        files_updated = list(files_after - files_before)
        
        # 重建索引
        subprocess.run(
            ["python3", "memdir_manager.py", "rebuild"],
            capture_output=True, timeout=15,
            cwd="/home/ubuntu/mojiajun-queue"
        )
        
        # 提取总结
        summary = "无需更新"
        for line in analysis.split('\n'):
            line = line.strip()
            if line.startswith('### 发现') or line.startswith('## 发现'):
                continue
            if len(line) > 15 and not line.startswith('#') and not line.startswith('```') and '无需更新' not in line:
                summary = line[:200]
                break
        
        if knowledge_items:
            summary = f"新增{len(knowledge_items)}条知识: {', '.join(i['title'][:20] for i in knowledge_items[:3])}"
        
        duration = time.time() - start_time
        print(f"[autoDream] ⏱️ {duration:.0f}s | Knowledge: {len(knowledge_items)} | Updates: {len(update_items)}")
        
        return {
            "success": True,
            "summary": summary,
            "knowledge_added": len(knowledge_items),
            "updates_noted": len(update_items),
            "files_updated": files_updated,
            "duration": duration
        }
        
    except Exception as e:
        print(f"[autoDream] ❌ Error: {e}")
        return {
            "success": False,
            "summary": f"Error: {str(e)[:200]}",
            "files_updated": [],
            "duration": time.time() - start_time
        }


# ============================================================
# 主入口
# ============================================================
def run_autodream():
    """主函数——在agent_worker空闲时调用"""
    state = load_state()
    
    is_open, gate_info = is_gate_open(state)
    if not is_open:
        return {"status": "skipped", "gate": gate_info}
    
    lock_fd = gate_info.get("lock_fd")
    
    try:
        result = execute_dream(state)
        
        # 更新状态
        state["last_dream_at"] = time.time()
        state["dream_count"] += 1
        state["total_files_updated"] += len(result.get("files_updated", []))
        
        # 更新数据cursor
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        state["cursor_markers"]["hot_list"] = now_str
        
        save_state(state)
        
        # 重建索引
        subprocess.run(
            ["python3", "memdir_manager.py", "rebuild"],
            cwd="/home/ubuntu/mojiajun-queue",
            capture_output=True, timeout=15
        )
        
        print(f"[autoDream] ✅ Dream #{state['dream_count']} completed: {result['summary']}")
        print(f"[autoDream] 📁 Files updated: {result['files_updated']}")
        
        return {
            "status": "completed",
            "dream_number": state["dream_count"],
            "summary": result["summary"],
            "files_updated": result["files_updated"]
        }
        
    except Exception as e:
        print(f"[autoDream] ❌ Error: {e}")
        # Don't update last_dream_at on failure, so it retries next time
        return {"status": "error", "error": str(e)}
        
    finally:
        if lock_fd:
            release_lock(lock_fd)


if __name__ == "__main__":
    result = run_autodream()
    print(json.dumps(result, indent=2, ensure_ascii=False))
