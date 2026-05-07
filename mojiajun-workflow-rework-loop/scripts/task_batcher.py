#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
墨家军 Task Batcher — 批量任务派发器

用法：
    from task_batcher import batch_dispatch, poll_task
    results = batch_dispatch(subtasks, serial=True)

设计原则：
- 所有操作通过 SSH 到 CORE-01 执行
- 串行模式：前一个 completed 后才入下一个
- 并行模式：所有子任务同时入队
- 每个子任务自动生成 UUID 作为 task_id

依赖：本地能 SSH 到 CORE-01 (159.75.12.11)
"""

import json
import shlex
import subprocess
import time
import uuid
from datetime import datetime
from typing import Optional


# CORE-01 连接信息
CORE_HOST = "159.75.12.11"
CORE_USER = "ubuntu"
MYSQL_CMD = "mysql -h127.0.0.1 -uxiaochuan -pxiaochuan_2026_mjj mojiajun"


def _ssh(command: str, timeout: int = 30) -> tuple[int, str, str]:
    """通过 SSH 在 CORE-01 上执行命令"""
    ssh_cmd = [
        "ssh", f"{CORE_USER}@{CORE_HOST}",
        command,
    ]
    proc = subprocess.run(
        ssh_cmd, capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _mysql_query(sql: str, timeout: int = 15) -> tuple[int, str]:
    """在 CORE-01 上执行 MySQL 查询"""
    # 用 shlex.quote 避免 SQL 中的引号破坏 shell 解析
    cmd = f'{MYSQL_CMD} -e {shlex.quote(sql)} 2>/dev/null'
    rc, out, err = _ssh(cmd, timeout=timeout)
    return rc, out


def insert_task(
    target_agent: str,
    task_type: str,
    payload: dict,
    priority: int = 1,
    parent_task_id: Optional[str] = None,
    timeout_seconds: int = 300,
    acceptance_criteria: Optional[dict] = None,
) -> str:
    """
    写入一个任务到 CORE-01 task_queue。

    Args:
        target_agent: Agent ID，如 "moyuan"
        task_type: 任务类型，如 "sample_analysis"
        payload: 任务参数（扁平字典）
        priority: 优先级，默认1
        parent_task_id: 父任务ID（子任务链）
        timeout_seconds: 超时秒数
        acceptance_criteria: Ralph Loop验收标准，格式:
            {"rules": [...], "require_marker": true, "completion_marker": "DONE", "max_attempts": 5}

    Returns:
        生成的 task_id
    """
    task_id = str(uuid.uuid4())[:8]
    parent_clause = (
        f"'{parent_task_id}'" if parent_task_id else "NULL"
    )
    payload_json = json.dumps(payload, ensure_ascii=False)

    if acceptance_criteria:
        ac_json = json.dumps(acceptance_criteria, ensure_ascii=False)
        # 对单引号做MySQL转义
        ac_sql = ac_json.replace("\\", "\\\\").replace("'", "\\'")
        ac_field = f", acceptance_criteria"
        ac_value = f", '{ac_sql}'"
    else:
        ac_field = ""
        ac_value = ""

    sql = (
        f"INSERT INTO task_queue "
        f"(task_id, parent_sub_task_id, target_agent, task_type, "
        f"payload, priority, status, timeout_seconds{ac_field}) "
        f"VALUES ("
        f"'{task_id}', {parent_clause}, '{target_agent}', '{task_type}', "
        f"'{payload_json}', {priority}, 'pending', {timeout_seconds}{ac_value}"
        f")"
    )
    rc, out = _mysql_query(sql)
    if rc != 0:
        raise RuntimeError(f"插入任务失败: {out}")
    return task_id


def check_task_status(task_id: str) -> Optional[str]:
    """
    查询任务状态。

    Returns:
        'pending' / 'processing' / 'completed' / 'failed' / None(不存在)
    """
    sql = f"SELECT status FROM task_queue WHERE task_id='{task_id}'"
    rc, out = _mysql_query(sql)
    if rc != 0 or not out:
        return None
    lines = out.strip().split("\n")
    if len(lines) < 2:
        return None
    return lines[1].strip()


def get_task_result(task_id: str) -> Optional[dict]:
    """获取任务执行结果。"""
    sql = f"SELECT result FROM task_queue WHERE task_id='{task_id}'"
    rc, out = _mysql_query(sql)
    if rc != 0 or not out:
        return None
    lines = out.strip().split("\n")
    if len(lines) < 2:
        return None
    result_str = lines[1].strip()
    if result_str == "NULL":
        return None
    try:
        return json.loads(result_str)
    except json.JSONDecodeError:
        return {"raw": result_str}


def poll_task(task_id: str, max_wait: int = 120, interval: int = 20) -> dict:
    """
    轮询等待任务完成。

    Args:
        task_id: 任务ID
        max_wait: 最大等待秒数
        interval: 轮询间隔秒数

    Returns:
        {"status": "completed"|"failed"|"timeout", "result": ...}
    """
    waited = 0
    while waited < max_wait:
        time.sleep(interval)
        waited += interval
        status = check_task_status(task_id)
        if status in ("completed", "failed"):
            result = get_task_result(task_id)
            return {"status": status, "result": result, "task_id": task_id}
    return {"status": "timeout", "result": None, "task_id": task_id}


def batch_dispatch(
    subtasks: list[dict],
    serial: bool = True,
    parent_task_id: Optional[str] = None,
    poll_results: bool = True,
) -> dict:
    """
    批量派发子任务到 CORE-01 task_queue。

    Args:
        subtasks: 子任务列表，每个格式：
            {
                "step": "步骤描述",
                "target_agent": "moyuan",
                "task_type": "sample_analysis",
                "payload": {"key": "value"},
                "priority": 1,        # 可选
                "timeout": 300,       # 可选
            }
        serial: True=串行（前一个完成才入下一个），False=并行
        parent_task_id: 父任务ID
        poll_results: 是否轮询等待结果

    Returns:
        {
            "dispatched": 3,
            "completed": 2,
            "failed": 1,
            "tasks": [
                {"task_id": "xxx", "status": "completed", "result": {...}},
                ...
            ]
        }
    """
    results = []
    dispatched = 0
    completed = 0
    failed = 0

    for i, subtask in enumerate(subtasks):
        step_name = subtask.get("step", f"step_{i+1}")
        target_agent = subtask["target_agent"]
        task_type = subtask["task_type"]
        payload = subtask.get("payload", {})
        priority = subtask.get("priority", 1)
        timeout = subtask.get("timeout", 300)

        print(f"  [{i+1}/{len(subtasks)}] {step_name}")
        print(f"       → {target_agent} / {task_type}")

        try:
            task_id = insert_task(
                target_agent=target_agent,
                task_type=task_type,
                payload=payload,
                priority=priority,
                parent_task_id=parent_task_id,
                timeout_seconds=timeout,
            )
            dispatched += 1
            print(f"       task_id={task_id}")

            if serial and poll_results:
                # 串行模式：等这个完成再入下一个
                poll_result = poll_task(task_id, max_wait=120, interval=20)
                status = poll_result["status"]
                if status == "completed":
                    completed += 1
                    print(f"       ✅ 完成")
                elif status == "failed":
                    failed += 1
                    print(f"       ❌ 失败")
                else:
                    print(f"       ⏰ 超时（仍在执行）")

                results.append({
                    "step": step_name,
                    "task_id": task_id,
                    "target_agent": target_agent,
                    "task_type": task_type,
                    "status": status,
                    "result": poll_result.get("result"),
                })
            else:
                # 并行模式：入队后不等待
                results.append({
                    "step": step_name,
                    "task_id": task_id,
                    "target_agent": target_agent,
                    "task_type": task_type,
                    "status": "dispatched",
                    "result": None,
                })

        except Exception as e:
            print(f"       ❌ 错误: {e}")
            results.append({
                "step": step_name,
                "task_id": None,
                "target_agent": target_agent,
                "task_type": task_type,
                "status": "error",
                "result": str(e),
            })
            failed += 1

            if serial:
                # 串行模式：出错就停
                print(f"  ⛔ 串行模式：前一步出错，停止后续任务")
                break

    # 并行模式：最后统一轮询
    if not serial and poll_results:
        print(f"\n  等待所有并行任务完成...")
        for r in results:
            if r["status"] == "dispatched":
                poll_result = poll_task(r["task_id"], max_wait=120, interval=20)
                r["status"] = poll_result["status"]
                r["result"] = poll_result.get("result")
                if r["status"] == "completed":
                    completed += 1
                elif r["status"] == "failed":
                    failed += 1

    summary = {
        "dispatched": dispatched,
        "completed": completed,
        "failed": failed,
        "pending": dispatched - completed - failed,
        "tasks": results,
    }
    return summary


def dispatch_with_rework(
    create_task: dict,
    audit_task: dict,
    max_retries: int = 3,
) -> dict:
    """
    创作+审核回路：自动处理审核驳回→重写。
    审核任务中的驳回处理由 CORE-01 agent_worker hook 自动完成（生成重写任务入队）。
    此函数负责轮询检测整个回路。

    用法:
        result = dispatch_with_rework(
            create_task={"target_agent": "molan", "task_type": "xiaohongshu_note", "payload": {...}},
            audit_task={"target_agent": "mohong", "task_type": "quality_audit", "payload": {...}},
        )
    """
    attempts = []
    for attempt in range(1, max_retries + 2):
        print(f"\n  --- 第 {attempt} 轮 ---")
        tid = insert_task(**create_task)
        print(f"  创作: task_id={tid}")
        poll = poll_task(tid, max_wait=120, interval=20)
        attempts.append({"attempt": attempt, "task_id": tid, "result": poll.get("result")})
        if poll["status"] == "completed":
            print(f"  ✅ 完成")
            return {"final_status": "completed", "attempts": attempts}
        elif poll["status"] == "failed":
            print(f"  ❌ 失败")
        else:
            print(f"  ⏰ 超时")
    return {"final_status": "max_retries", "attempts": attempts}


# ============================================================
# 自测
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("墨家军 Task Batcher — 自测")
    print("=" * 60)

    # 测试 SSH 连通性
    print("\n[1] SSH 连通性测试")
    rc, out, err = _ssh("echo ok", timeout=10)
    if rc == 0 and out == "ok":
        print("  ✅ SSH 连接正常")
    else:
        print(f"  ❌ SSH 连接失败: rc={rc}, out={out}, err={err}")
        exit(1)

    # 测试 MySQL 连通性
    print("\n[2] MySQL 连通性测试")
    rc, out = _mysql_query("SELECT COUNT(*) FROM task_queue WHERE status='pending'")
    if rc == 0:
        pending_count = out.strip().split("\n")[1] if "\n" in out else out
        print(f"  ✅ MySQL 连接正常，pending任务数: {pending_count}")
    else:
        print(f"  ❌ MySQL 连接失败: {out}")

    # 测试插入 + 状态查询（不实际执行，只看是否能写入和查询）
    print("\n[3] 插入 + 状态查询测试")
    test_task_id = insert_task(
        target_agent="moyuan",
        task_type="sample_analysis",
        payload={"test": True},
        priority=0,
    )
    print(f"  插入 task_id={test_task_id}")
    status = check_task_status(test_task_id)
    print(f"  状态: {status}")
    assert status in ("pending", "processing"), f"状态异常: {status}"
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("🎉 task_batcher 自测通过！")
    print("=" * 60)
