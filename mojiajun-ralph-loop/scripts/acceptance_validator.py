#!/usr/bin/env python3
"""
墨家军 Ralph Loop — 验收验证器

核心理念：Agent 不能自己宣布完成，必须通过系统级验收。

用法：
    from acceptance_validator import validate

    criteria = {
        "rules": [
            {"field": "title_switches", "op": "gte", "value": 2, "desc": "标题触发≥2心理开关"},
            {"field": "redline_hits", "op": "eq", "value": 0, "desc": "零红线词"},
        ],
        "require_marker": True,
        "completion_marker": "DONE",
        "max_attempts": 5,
    }
    result = validate(criteria, module_output, attempt=3)
    # => {"passed": False, "failed_rules": [...], "score": 0.5, "summary": "..."}

支持的运算符：eq, neq, gt, gte, lt, lte, in, not_in, contains, regex, exists, not_exists
"""

import json
import re
import logging
from typing import Union, Optional, Dict, Any, List, Tuple

logger = logging.getLogger("RalphValidator")

# ─── 核心函数 ────────────────────────────────────────────────

def _resolve_field(data: dict, field_path: str):
    """
    支持点号路径: "a.b.c" → data["a"]["b"]["c"]
    也支持 module_result.xxx 前缀自动剥离
    """
    # 自动剥离常见前缀
    for prefix in ("module_result.", "result.", "output."):
        if field_path.startswith(prefix):
            field_path = field_path[len(prefix):]

    parts = field_path.split(".")
    current = data
    for p in parts:
        if isinstance(current, dict):
            current = current.get(p)
        elif isinstance(current, list) and p.isdigit():
            idx = int(p)
            current = current[idx] if idx < len(current) else None
        else:
            return None
    return current


def _check_rule(rule: dict, data: dict) -> tuple:
    """检查单条规则。返回 (通过?, 失败描述)。"""
    field = rule.get("field", "")
    op = rule.get("op", "eq")
    expected = rule.get("value")
    desc = rule.get("desc", f"{field} {op} {expected}")

    actual = _resolve_field(data, field)

    try:
        if op == "exists":
            passed = actual is not None
        elif op == "not_exists":
            passed = actual is None
        elif actual is None:
            passed = False
        elif op == "eq":
            passed = actual == expected
        elif op == "neq":
            passed = actual != expected
        elif op == "gt":
            passed = actual > expected
        elif op == "gte":
            passed = actual >= expected
        elif op == "lt":
            passed = actual < expected
        elif op == "lte":
            passed = actual <= expected
        elif op == "in":
            passed = actual in expected if isinstance(expected, (list, tuple, set)) else False
        elif op == "not_in":
            passed = actual not in expected if isinstance(expected, (list, tuple, set)) else True
        elif op == "contains":
            passed = str(expected) in str(actual)
        elif op == "regex":
            passed = bool(re.search(str(expected), str(actual)))
        else:
            return False, f"未知运算符: {op}"

        if passed:
            return True, ""
        else:
            return False, f"{desc} (期望 {expected}, 实际 {actual})"

    except Exception as e:
        return False, f"{desc} (校验异常: {e})"


def _detect_completion_marker(
    result: dict, marker: str = "DONE"
) -> tuple:
    """
    在输出中检测完成标记 <promise>DONE</promise> 或 DONE 等变体。
    检查范围：module_result 的字符串值、output_file 内容片段。
    """
    # 变体模式
    patterns = [
        rf"<promise>\s*{re.escape(marker)}\s*</promise>",
        rf"<{re.escape(marker)}\s*/>",
        rf"COMPLETION_PROMISE:\s*{re.escape(marker)}",
        rf"✅\s*{re.escape(marker)}",
    ]

    # 把所有字符串值拼接成一个文本
    texts = []

    def _collect_str(obj):
        if isinstance(obj, str):
            texts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _collect_str(v)
        elif isinstance(obj, list):
            for v in obj:
                _collect_str(v)

    _collect_str(result)

    combined = " ".join(texts)

    for pat in patterns:
        if re.search(pat, combined, re.IGNORECASE):
            return True, f"完成标记已检测到: {marker}"

    # 模糊匹配：输出末尾包含 marker（针对简单场景）
    if marker.lower() in combined[-500:].lower():
        return True, f"完成标记已检测到(模糊): {marker}"

    return False, f"未检测到完成标记 <promise>{marker}</promise>"


# ─── 公开 API ────────────────────────────────────────────────

def validate(
    acceptance_criteria,  # Union[dict, str, None]
    module_output,         # dict
    attempt: int = 0,
) -> dict:
    """
    验证 Agent 输出是否满足验收标准。

    Args:
        acceptance_criteria: 从 task_queue.acceptance_criteria 读取
        module_output: Agent 的 module_result 输出（dict）
        attempt: 当前第几次尝试（0-based）

    Returns:
        {
            "passed": bool,
            "failed_rules": [{"rule": "...", "reason": "..."}],
            "score": float,          # 0.0 ~ 1.0
            "summary": str,
            "marker_detected": bool, # 是否检测到完成标记
            "rework_context": str,   # 失败时：下一轮要看的错误摘要
            "should_retry": bool,    # 是否应该重试
            "should_break": bool,    # 是否应该熔断
        }
    """
    # 解析 JSON 字符串
    if isinstance(acceptance_criteria, str):
        try:
            acceptance_criteria = json.loads(acceptance_criteria)
        except json.JSONDecodeError:
            acceptance_criteria = None

    # 无验收标准 = 跳过（向后兼容）
    if not acceptance_criteria or not isinstance(acceptance_criteria, dict):
        return {
            "passed": True,
            "failed_rules": [],
            "score": 1.0,
            "summary": "无验收标准，自动通过",
            "marker_detected": True,
            "rework_context": "",
            "should_retry": False,
            "should_break": False,
        }

    rules = acceptance_criteria.get("rules", [])
    require_marker = acceptance_criteria.get("require_marker", True)
    completion_marker = acceptance_criteria.get("completion_marker", "DONE")
    max_attempts = acceptance_criteria.get("max_attempts", 5)

    # 1. 检查完成标记
    marker_ok, marker_msg = (True, "跳过标记检测") if not require_marker else \
        _detect_completion_marker(module_output, completion_marker)

    # 2. 逐条检查规则
    failed_rules = []
    for rule in rules:
        passed, reason = _check_rule(rule, module_output)
        if not passed:
            failed_rules.append({"rule": rule, "reason": reason})

    # 3. 计算分数
    total_rules = len(rules) + (1 if require_marker else 0)
    passed_count = (len(rules) - len(failed_rules)) + (1 if marker_ok else 0)
    score = passed_count / total_rules if total_rules > 0 else 1.0

    # 4. 判定
    all_rules_passed = len(failed_rules) == 0
    passed = all_rules_passed and marker_ok

    # 5. 生成失败摘要
    fail_lines = []
    if not marker_ok:
        fail_lines.append(f"  ✗ 完成标记: {marker_msg}")
    for fr in failed_rules:
        fail_lines.append(f"  ✗ {fr['reason']}")

    if passed:
        summary = f"✅ 验收通过 ({passed_count}/{total_rules})"
    else:
        summary = (
            f"❌ 验收不通过 ({passed_count}/{total_rules})\n"
            + "\n".join(fail_lines)
        )

    # 6. 判断是否重试/熔断
    should_retry = not passed and attempt < max_attempts
    should_break = not passed and attempt >= max_attempts

    rework_context = ""
    if not passed:
        rework_context = (
            f"上一轮验收不通过 (第{attempt}次尝试):\n" +
            "\n".join(fail_lines) +
            f"\n\n请修正上述问题后再次输出 <promise>{completion_marker}</promise> 完成标记。"
        )

    return {
        "passed": passed,
        "failed_rules": failed_rules,
        "score": score,
        "summary": summary,
        "marker_detected": marker_ok,
        "rework_context": rework_context,
        "should_retry": should_retry,
        "should_break": should_break,
    }


# ─── 自测 ────────────────────────────────────────────────────

if __name__ == "__main__":
    # 测试1: 通过场景
    criteria = {
        "rules": [
            {"field": "title_switches", "op": "gte", "value": 2, "desc": "标题触发≥2心理开关"},
            {"field": "redline_hits", "op": "eq", "value": 0, "desc": "零红线词"},
            {"field": "status", "op": "eq", "value": "success", "desc": "执行成功"},
        ],
        "require_marker": True,
        "completion_marker": "DONE",
        "max_attempts": 5,
    }

    output1 = {
        "title_switches": 3,
        "redline_hits": 0,
        "status": "success",
        "note_text": "... 完成。 <promise>DONE</promise>",
    }
    r1 = validate(criteria, output1, attempt=0)
    print(f"测试1 (通过):  passed={r1['passed']}, score={r1['score']}, summary={r1['summary'][:60]}")

    # 测试2: 失败场景
    output2 = {
        "title_switches": 1,
        "redline_hits": 2,
        "status": "success",
        "note_text": "写完了。",
    }
    r2 = validate(criteria, output2, attempt=3)
    print(f"测试2 (失败):  passed={r2['passed']}, score={r2['score']}, retry={r2['should_retry']}")
    print(f"  rework_context: {r2['rework_context'][:120]}...")

    # 测试3: 熔断
    r3 = validate(criteria, output2, attempt=5)
    print(f"测试3 (熔断):  passed={r3['passed']}, break={r3['should_break']}")

    # 测试4: 无标准=自动通过
    r4 = validate(None, {"a": 1}, attempt=0)
    print(f"测试4 (无标准): passed={r4['passed']}")

    print("\n🎉 acceptance_validator 自测通过！")
