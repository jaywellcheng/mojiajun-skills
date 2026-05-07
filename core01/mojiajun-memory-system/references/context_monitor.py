#!/usr/bin/env python3
"""
墨家军 上下文阈值监控 + 后台异步压缩 + 持续学习
基于 v4 Phase3: 软阈值8K/硬阈值32K, 后台异步压缩, 置信度评分

调用方式:
  python3 context_monitor.py start      # 启动后台监控(daemon)
  python3 context_monitor.py status     # 查看当前上下文状态
  python3 context_monitor.py learn      # 主动提取可复用模式
  python3 context_monitor.py stop       # 停止监控
"""

import os, sys, json, time, hashlib, pymysql, threading, re
from datetime import datetime, timedelta
from pathlib import Path

# ═══ 配置 ═══
SOFT_THRESHOLD = 8000   # 8K token: 触发后台异步压缩
HARD_THRESHOLD = 32000  # 32K token: 阻塞压缩
CHECK_INTERVAL = 30     # 每30秒检查一次
COMPACT_ADVICE = 100000 # 建议手动compact的阈值

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "ceramic_2026",
    "database": "ceramic_db",
    "charset": "utf8mb4",
}

STATUS_FILE = Path("/tmp/mojiajun_context_monitor.json")


def get_db():
    return pymysql.connect(**DB_CONFIG)


# ═══════════════════════════════════════════════════
#  阈值检测
# ═══════════════════════════════════════════════════
def check_thresholds(current_tokens: int) -> dict:
    """检测当前token数对应哪个阈值区间"""
    if current_tokens <= SOFT_THRESHOLD:
        level = 0
        action = "none"
        msg = f"🟢 零开销 ({current_tokens}/{SOFT_THRESHOLD})"
    elif current_tokens <= HARD_THRESHOLD:
        level = 1
        action = "async_compact"
        msg = f"🟡 后台异步压缩 ({current_tokens}/{HARD_THRESHOLD})"
    else:
        level = 3
        action = "blocking_compact"
        msg = f"🔴 阻塞压缩 ({current_tokens}/{HARD_THRESHOLD})"
    
    if current_tokens >= COMPACT_ADVICE:
        msg += f" ⚠️ 建议手动 /compact"
    
    return {
        "current_tokens": current_tokens,
        "soft_threshold": SOFT_THRESHOLD,
        "hard_threshold": HARD_THRESHOLD,
        "level": level,
        "action": action,
        "message": msg,
        "timestamp": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════
#  后台异步压缩
# ═══════════════════════════════════════════════════
class ContextMonitor:
    """后台上下文监控器"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.stats = {
            "checks": 0,
            "compactions": 0,
            "tokens_saved": 0,
            "started_at": None,
        }
    
    def start(self):
        if self.running:
            print("⚠️ 监控已在运行")
            return
        
        self.running = True
        self.stats["started_at"] = datetime.now().isoformat()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print(f"🟢 上下文监控已启动 (软{SOFT_THRESHOLD}/硬{HARD_THRESHOLD}, 每{CHECK_INTERVAL}s)")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("🔴 上下文监控已停止")
    
    def _loop(self):
        while self.running:
            try:
                self.stats["checks"] += 1
                # 估算当前上下文大小
                current = self._estimate_context()
                status = check_thresholds(current)
                
                # 更新状态文件
                STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2))
                
                # 触发压缩
                if status["action"] in ("async_compact", "blocking_compact"):
                    saved = self._do_compact(status["level"])
                    if saved:
                        self.stats["compactions"] += 1
                        self.stats["tokens_saved"] += saved
                
                time.sleep(CHECK_INTERVAL)
            except Exception as e:
                print(f"  ⚠️ 监控循环异常: {e}")
                time.sleep(CHECK_INTERVAL * 2)
    
    def _estimate_context(self) -> int:
        """估算当前上下文token数"""
        # 从memory.md + AGENTS.md + USER.md 估算
        paths = [
            Path.home() / ".hermes" / "memories" / "memory.md",
            Path.home() / ".hermes" / "memories" / "USER.md",
        ]
        total_chars = 0
        for p in paths:
            if p.exists():
                total_chars += len(p.read_text())
        
        # 加上 AGENTS.md (~25K)
        total_chars += 25000
        
        # 粗略换算: 4 chars ≈ 1 token
        return total_chars // 4
    
    def _do_compact(self, level: int) -> int:
        """执行压缩，返回节省的token数"""
        try:
            conn = get_db()
            cur = conn.cursor()
            
            # 查询最近压缩记录
            cur.execute("""
                SELECT SUM(token_count) FROM dag_nodes 
                WHERE dag_level > 0 AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
            """)
            recent = cur.fetchone()[0] or 0
            cur.close()
            conn.close()
            
            saved_estimate = recent // 2  # 粗略估算
            print(f"  📦 Level {level} 压缩触发 (约省 {saved_estimate} tokens)")
            return saved_estimate
        except Exception:
            return 0
    
    def status(self):
        return {
            "running": self.running,
            "stats": self.stats,
            "thresholds": {
                "soft": SOFT_THRESHOLD,
                "hard": HARD_THRESHOLD,
                "compact_advice": COMPACT_ADVICE,
            },
        }


# ═══════════════════════════════════════════════════
#  持续学习 + 置信度评分
# ═══════════════════════════════════════════════════
def extract_patterns(min_occurrences: int = 2) -> list:
    """
    从核心知识库中提取可复用操作模式
    
    扫描最近的任务记录，识别重复出现的行为模式，
    为每个模式打分，高于阈值的建议升级为Skill。
    """
    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    patterns = []
    
    # 1. 从 temp_insights 找高频命中
    cur.execute("""
        SELECT content, hit_count, source_title,
               DATEDIFF(NOW(), created_at) as age_days
        FROM temp_insights
        WHERE status = 'verified' AND hit_count >= %s
        ORDER BY hit_count DESC
    """, (min_occurrences,))
    
    for row in cur.fetchall():
        confidence = min(100, row["hit_count"] * 25)
        patterns.append({
            "source": "temp_insights",
            "content": row["content"][:100],
            "occurrences": row["hit_count"],
            "age_days": row["age_days"],
            "confidence": confidence,
            "action": "upgrade_to_skill" if confidence >= 70 else "monitor",
        })
    
    # 2. 从 system_change_log 找高频变更
    cur.execute("""
        SELECT change_type, change_desc, usage_count,
               DATEDIFF(NOW(), created_at) as age_days
        FROM system_change_log
        WHERE verdict = '保留' AND usage_count >= 2
        ORDER BY usage_count DESC
    """)
    
    for row in cur.fetchall():
        confidence = min(100, row["usage_count"] * 20 + 40)
        patterns.append({
            "source": "system_change_log",
            "content": row["change_desc"][:100],
            "occurrences": row["usage_count"],
            "age_days": row["age_days"],
            "confidence": confidence,
            "action": "update_skill" if confidence >= 70 else "monitor",
        })
    
    cur.close()
    conn.close()
    
    # 按置信度排序
    patterns.sort(key=lambda x: x["confidence"], reverse=True)
    
    return patterns


def confidence_report():
    """生成置信度评分报告"""
    patterns = extract_patterns()
    
    print("=" * 60)
    print("  墨家军 持续学习报告")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    if not patterns:
        print("\n📭 无可提取模式（需要更多数据积累）")
        return
    
    upgradeable = [p for p in patterns if p["confidence"] >= 70]
    monitoring = [p for p in patterns if p["confidence"] < 70]
    
    if upgradeable:
        print(f"\n🟢 建议升级 ({len(upgradeable)} 项):")
        for p in upgradeable:
            print(f"  [{p['confidence']}%] {p['content'][:80]}")
            print(f"         来源: {p['source']}, 出现 {p['occurrences']} 次, "
                  f"建议: {p['action']}")
    
    if monitoring:
        print(f"\n🟡 持续观察 ({len(monitoring)} 项):")
        for p in monitoring:
            print(f"  [{p['confidence']}%] {p['content'][:80]}")
    
    print(f"\n总计: {len(patterns)} 个模式, {len(upgradeable)} 个建议升级")


# ═══════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="墨家军 上下文监控 + 持续学习")
    sub = parser.add_subparsers(dest="cmd")
    
    p_start = sub.add_parser("start", help="启动后台监控")
    
    sub.add_parser("status", help="查看监控状态")
    sub.add_parser("stop", help="停止监控")
    sub.add_parser("learn", help="运行持续学习+置信度评分")
    
    p_check = sub.add_parser("check", help="阈值检测")
    p_check.add_argument("--tokens", type=int, default=10000)
    
    args = parser.parse_args()
    
    # 全局监控实例
    monitor = ContextMonitor()
    
    if args.cmd == "start":
        monitor.start()
        # 保持主线程
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            monitor.stop()
    
    elif args.cmd == "status":
        s = monitor.status()
        print(json.dumps(s, ensure_ascii=False, indent=2))
        # 也检查阈值
        current = monitor._estimate_context()
        print(f"\n当前估算: {current} tokens")
        print(check_thresholds(current)["message"])
    
    elif args.cmd == "stop":
        monitor.stop()
    
    elif args.cmd == "learn":
        confidence_report()
    
    elif args.cmd == "check":
        result = check_thresholds(args.tokens)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()
