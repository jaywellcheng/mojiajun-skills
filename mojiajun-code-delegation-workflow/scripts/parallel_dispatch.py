#!/usr/bin/env python3
"""
墨家军代码分派工作流 v2 — 并行分派脚本

同时向 AS1 和 AS2 分派独立任务，等待全部完成后汇总结果。

使用方式：
    from parallel_dispatch import parallel_dispatch

    tasks = [
        {
            "agent": "AS1",
            "file": "local/module_a.py",
            "goal": "添加健康检查端点",
            "template": "health-check",
            "slot_fills": {
                "目标文件": "module_a.py",
                "改动描述": "添加 /health 端点返回 {\"status\":\"ok\"}",
                "额外约束": "仅用 flask stdlib",
            },
        },
        {
            "agent": "AS2",
            "file": "remote/deploy.py",
            "goal": "修复部署脚本超时bug",
            "template": "fix-bug",
            "slot_fills": {
                "目标文件": "deploy.py",
                "改动描述": "subprocess.run 增加 timeout=30 参数",
                "额外约束": "",
            },
        },
    ]

    results = parallel_dispatch(tasks, max_parallel=2, timeout_per_task=600)
"""

import subprocess
import threading
import time
import os
import sys
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# 配置
# ============================================================
AS1_WORKSPACE = os.path.expanduser("~/cc1-workspace")
AS2_SSH_HOST = "ubuntu@159.75.12.11"
AS2_WORKSPACE = "~/as2-workspace"
AS2_WRAPPER = "~/as2-wrapper.sh"

AIDER_FLAGS = "--no-auto-commits --yes --model openai/deepseek-v4-pro"

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "templates",
)

# ============================================================
# 数据结构
# ============================================================


@dataclass
class DispatchTask:
    """单个分派任务"""

    agent: str  # "AS1" | "AS2"
    file: str  # 目标文件路径
    goal: str  # 任务目标
    template: Optional[str] = None  # 模板名称（不含 .md）
    slot_fills: Dict[str, str] = field(default_factory=dict)


@dataclass
class DispatchResult:
    """分派结果"""

    agent: str
    file: str
    success: bool
    output: str  # aider 输出
    error: Optional[str] = None
    elapsed_seconds: float = 0.0
    review_verdict: Optional[str] = None  # 墨码审核结果（后续填充）


# ============================================================
# 核心逻辑
# ============================================================


def load_template(template_name: str) -> str:
    """
    加载预置模板并填充槽位。

    Args:
        template_name: 模板文件名（不含 .md）。

    Returns:
        填充后的完整 prompt 文本。
    """
    template_path = os.path.join(TEMPLATES_DIR, f"{template_name}.md")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板不存在: {template_path}")

    with open(template_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    return content


def build_prompt(task: DispatchTask) -> str:
    """
    根据任务生成 aider prompt。

    优先使用预置模板，否则用默认 prompt 结构。

    Returns:
        UTF-8 编码的 prompt 字符串。
    """
    if task.template:
        try:
            template = load_template(task.template)
            # 填充 [FILL] 槽位
            for key, value in task.slot_fills.items():
                template = template.replace(f"[FILL]", value, 1)
            # 构建最终的 aider message
            return _extract_prompt_from_template(template, task)
        except FileNotFoundError as e:
            print(f"⚠️ {e}，回退到默认 prompt")

    # 默认 prompt 结构
    return _build_default_prompt(task)


def _extract_prompt_from_template(template: str, task: DispatchTask) -> str:
    """
    从预置模板中提取【任务】和【目标文件】等关键段落，
    组装成 aider 可用的单行/多行 prompt。
    """
    # 简单策略：将模板中自动生成区的关键段落拼接
    # 查找【任务】标记
    lines = template.split("\n")
    task_lines = []
    capture = False
    for line in lines:
        if "【任务】" in line or "【目标文件】" in line or "【具体改动】" in line:
            capture = True
        if capture:
            task_lines.append(line)
        if "【验收标准】" in line:
            break

    if task_lines:
        return "\n".join(task_lines)
    # 回退：直接用 goal
    return f"【任务】{task.goal}\n【目标文件】{task.file}"


def _build_default_prompt(task: DispatchTask) -> str:
    """
    构建默认的 AS prompt（非模板场景）。
    """
    return (
        f"【任务】{task.goal}\n"
        f"【目标文件】{task.file}\n"
        f"【约束】\n"
        f"- 代码简洁不超100行\n"
        f"- 只用stdlib除非指定\n"
        f"- 异常处理完整\n"
        f"【验收标准】\n"
        f"- python3 直接运行不报错\n"
        f"- 功能符合描述\n"
    )


def dispatch_as1(prompt: str, timeout: int = 600) -> DispatchResult:
    """
    向 AS1（本地 macOS）分派任务。

    Args:
        prompt: aider --message 内容。
        timeout: 超时秒数。

    Returns:
        DispatchResult。
    """
    start = time.time()
    cmd = (
        f"cd {AS1_WORKSPACE} && "
        f'aider --message "{prompt}" {AIDER_FLAGS}'
    )

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            cwd=AS1_WORKSPACE,
        )
        elapsed = time.time() - start
        output = proc.stdout + proc.stderr
        success = proc.returncode == 0
        return DispatchResult(
            agent="AS1",
            file="",
            success=success,
            output=output,
            error=None if success else f"exit_code={proc.returncode}",
            elapsed_seconds=elapsed,
        )
    except subprocess.TimeoutExpired:
        return DispatchResult(
            agent="AS1",
            file="",
            success=False,
            output="",
            error=f"超时 ({timeout}s)",
            elapsed_seconds=time.time() - start,
        )
    except Exception as exc:
        return DispatchResult(
            agent="AS1",
            file="",
            success=False,
            output="",
            error=str(exc),
            elapsed_seconds=time.time() - start,
        )


def dispatch_as2(prompt: str, timeout: int = 600) -> DispatchResult:
    """
    向 AS2（远程 CORE-01）分派任务。

    Args:
        prompt: aider --message 内容。
        timeout: 超时秒数。

    Returns:
        DispatchResult。
    """
    start = time.time()
    # 通过 as2-wrapper.sh 调用
    inner_cmd = f'--message "{prompt}" {AIDER_FLAGS}'
    cmd = [
        "ssh",
        AS2_SSH_HOST,
        f"{AS2_WRAPPER} {inner_cmd}",
    ]

    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        elapsed = time.time() - start
        output = proc.stdout + proc.stderr
        success = proc.returncode == 0
        return DispatchResult(
            agent="AS2",
            file="",
            success=success,
            output=output,
            error=None if success else f"exit_code={proc.returncode}",
            elapsed_seconds=elapsed,
        )
    except subprocess.TimeoutExpired:
        return DispatchResult(
            agent="AS2",
            file="",
            success=False,
            output="",
            error=f"超时 ({timeout}s)",
            elapsed_seconds=time.time() - start,
        )
    except Exception as exc:
        return DispatchResult(
            agent="AS2",
            file="",
            success=False,
            output="",
            error=str(exc),
            elapsed_seconds=time.time() - start,
        )


# ============================================================
# 并行调度
# ============================================================


def parallel_dispatch(
    tasks: List[Dict[str, Any]],
    max_parallel: int = 2,
    timeout_per_task: int = 600,
) -> List[Dict]:
    """
    并行分派多个任务到 AS1/AS2。

    Args:
        tasks: 任务列表，每个任务为 dict:
               {"agent": "AS1"|"AS2", "file": str, "goal": str,
                "template": str (可选), "slot_fills": dict (可选)}
        max_parallel: 最大并行数（默认 2，对应 AS1+AS2）。
        timeout_per_task: 单任务超时秒数。

    Returns:
        结果列表，每项为 dict:
        {"agent": str, "success": bool, "output": str,
         "error": str|None, "elapsed_seconds": float}
    """
    dispatch_tasks = []
    for t in tasks:
        dt = DispatchTask(
            agent=t.get("agent", "AS1"),
            file=t.get("file", ""),
            goal=t.get("goal", ""),
            template=t.get("template"),
            slot_fills=t.get("slot_fills", {}),
        )
        dispatch_tasks.append(dt)

    print(f"🚀 并行分派 {len(dispatch_tasks)} 个任务 (max_parallel={max_parallel})")
    for dt in dispatch_tasks:
        tag = "📋" if dt.template else "📝"
        tmpl_info = f" [模板: {dt.template}]" if dt.template else ""
        print(f"  {tag} {dt.agent}: {dt.goal[:60]}...{tmpl_info}")

    results: List[Dict] = []
    lock = threading.Lock()

    def _run(dt: DispatchTask) -> DispatchResult:
        prompt = build_prompt(dt)
        print(f"\n▶ {dt.agent} 开始: {dt.goal[:50]}...")

        if dt.agent == "AS1":
            result = dispatch_as1(prompt, timeout=timeout_per_task)
        elif dt.agent == "AS2":
            result = dispatch_as2(prompt, timeout=timeout_per_task)
        else:
            result = DispatchResult(
                agent=dt.agent,
                file=dt.file,
                success=False,
                output="",
                error=f"未知 Agent: {dt.agent}",
            )

        result.file = dt.file
        status = "✅" if result.success else "❌"
        print(f"  {status} {dt.agent} 完成 ({result.elapsed_seconds:.1f}s): {dt.goal[:50]}")

        with lock:
            results.append(
                {
                    "agent": result.agent,
                    "file": result.file,
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                    "elapsed_seconds": result.elapsed_seconds,
                }
            )

        return result

    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = {executor.submit(_run, dt): dt for dt in dispatch_tasks}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                dt = futures[future]
                with lock:
                    results.append(
                        {
                            "agent": dt.agent,
                            "file": dt.file,
                            "success": False,
                            "output": "",
                            "error": str(exc),
                            "elapsed_seconds": 0,
                        }
                    )

    # 汇总
    total = len(results)
    ok = sum(1 for r in results if r["success"])
    total_time = sum(r["elapsed_seconds"] for r in results)
    print(f"\n📊 并行分派完成: {ok}/{total} 成功, 总耗时 {total_time:.1f}s")
    return results


# ============================================================
# CLI 入口（调试用）
# ============================================================
if __name__ == "__main__":
    # 快速自检 — 不实际调用 aider
    print("parallel_dispatch.py 语法检查通过")
    print(f"  AS1 workspace: {AS1_WORKSPACE}")
    print(f"  AS2 host:      {AS2_SSH_HOST}")
    print(f"  Templates:     {TEMPLATES_DIR}")

    # 测试 prompt 构建
    test_task = DispatchTask(
        agent="AS1",
        file="test.py",
        goal="添加 hello world 函数",
        template="health-check",
        slot_fills={
            "目标文件": "test.py",
            "改动描述": "添加 /health 端点",
            "额外约束": "仅用 stdlib",
        },
    )
    try:
        prompt = build_prompt(test_task)
        print(f"\n  测试 prompt 构建成功 ({len(prompt)} chars)")
    except Exception as e:
        print(f"\n  测试 prompt 构建失败: {e}")
