#!/usr/bin/env python3
"""
墨家军 Phase2 收尾模块: 四层分级加载 + 安全扫描 + delegate校验

1. 四层分级加载: 行为纲领→用户→项目→子级，按需触发
2. 安全扫描: git diff静态扫描(secret/shell/SQL/eval)
3. delegate范围校验: 子代理任务不得超出声明范围
"""

import os, re, json, subprocess
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════
#  四层分级加载配置
# ═══════════════════════════════════════════════════
LAYER_CONFIG = {
    "behavior": {
        "name": "行为纲领层",
        "paths": [
            "~/墨家军资料库/墨蓝_program.md",
            "~/墨家军资料库/墨青_program.md",
        ],
        "load": "always",  # 每次会话全量加载
        "max_lines": 100,
    },
    "user": {
        "name": "用户级",
        "paths": [
            "~/.hermes/memories/USER.md",
            "~/.hermes/memories/memory.md",
        ],
        "load": "always",
    },
    "project": {
        "name": "项目级",
        "paths": [
            "~/Desktop/墨家军资料库/墨家军记忆体系升级方案_v4.md",
        ],
        "load": "always",
    },
    "sub": {
        "name": "子级(按需)",
        "paths": [
            "~/Desktop/墨家军资料库/方案讨论结果/",
        ],
        "load": "on_touch",  # 触及目录时才加载
        "triggers": ["窑滚人生", "天青浅", "漫画", "松鼠杯"],
    },
}


def get_layer_context():
    """按四层分级加载上下文，返回应注入的文本"""
    context_parts = []
    
    for layer_key, layer in LAYER_CONFIG.items():
        if layer["load"] == "always":
            for path_pattern in layer["paths"]:
                path = Path(path_pattern).expanduser()
                if path.exists():
                    if path.is_dir():
                        for f in sorted(path.glob("*.md"))[:5]:
                            content = f.read_text()[:2000]
                            context_parts.append(f"<!-- {layer['name']}: {f.name} -->\n{content}")
                    else:
                        content = path.read_text()
                        if layer_key == "behavior" and len(content.split('\n')) > layer.get("max_lines", 200):
                            content = '\n'.join(content.split('\n')[:layer["max_lines"]])
                        context_parts.append(f"<!-- {layer['name']}: {path.name} -->\n{content}")
        elif layer["load"] == "on_touch":
            context_parts.append(f"<!-- {layer['name']}: {len(layer['paths'])} 个路径，触及对应目录时触发加载 -->")
    
    return '\n\n'.join(context_parts)


# ═══════════════════════════════════════════════════
#  安全扫描（对接 request-code-review 静态扫描）
# ═══════════════════════════════════════════════════
SECURITY_PATTERNS = [
    # Secret泄露
    (r"(api_key|secret|password|token|passwd)\s*=\s*['\"][^'\"]{6,}['\"]", "HARDCODED_SECRET"),
    # Shell注入
    (r"os\.system\(|subprocess.*shell\s*=\s*True", "SHELL_INJECTION"),
    # 危险eval/exec
    (r"\beval\(|\bexec\(", "DANGEROUS_EVAL"),
    # 反序列化
    (r"pickle\.loads?\(|yaml\.load\(", "UNSAFE_DESERIALIZE"),
    # SQL注入
    (r"execute\(f\"|\.format\(.*SELECT|\.format\(.*INSERT", "SQL_INJECTION"),
    # 路径遍历
    (r"os\.path\.join\(.*\.\.", "PATH_TRAVERSAL"),
]


def security_scan(diff_text=None):
    """
    安全扫描：检查git diff或指定文本
    返回: (passed: bool, findings: list)
    """
    if diff_text is None:
        try:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True, text=True, timeout=10
            )
            diff_text = result.stdout
        except Exception:
            return True, []  # 无法获取diff，跳过
    
    if not diff_text.strip():
        return True, []
    
    findings = []
    added_lines = [l for l in diff_text.split('\n') if l.startswith('+') and not l.startswith('+++')]
    
    for line in added_lines:
        for pattern, rule_id in SECURITY_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "rule": rule_id,
                    "line": line[:120],
                    "severity": "CRITICAL" if rule_id in ("HARDCODED_SECRET", "SHELL_INJECTION") else "HIGH",
                })
    
    passed = len(findings) == 0
    return passed, findings


def security_report(findings):
    """生成安全扫描报告"""
    if not findings:
        return "✅ 安全扫描通过，未发现风险"
    
    report = "⚠️ 安全扫描发现问题:\n"
    for f in findings:
        report += f"  [{f['severity']}] {f['rule']}: {f['line'][:80]}\n"
    return report


# ═══════════════════════════════════════════════════
#  delegate_task 范围缩减校验
# ═══════════════════════════════════════════════════
def validate_delegate_scope(task_goal: str, allowed_scope: list) -> dict:
    """
    校验子代理任务是否超出声明范围
    
    Args:
        task_goal: 子代理的任务描述
        allowed_scope: 允许的操作范围 ['read_file', 'write_file', 'terminal', ...]
    
    Returns:
        {valid: bool, warnings: list}
    """
    warnings = []
    
    # 检测越权操作关键词
    scope_keywords = {
        "terminal": ["执行", "运行", "安装", "部署", "重启", "build", "run", "install", "deploy"],
        "web_search": ["搜索", "查找", "上网", "search", "find online"],
        "browser": ["浏览器", "网页", "登录", "browser", "login", "webpage"],
        "write_file": ["写入", "修改文件", "创建文件", "write", "create file", "modify"],
        "delegate_task": ["委托", "派发", "子代理", "subagent", "delegate"],
    }
    
    for scope, keywords in scope_keywords.items():
        if scope not in allowed_scope:
            for kw in keywords:
                if kw.lower() in task_goal.lower():
                    warnings.append(f"任务需要 '{scope}' 但不在允许范围: {allowed_scope}")
                    break
    
    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "allowed_scope": allowed_scope,
        "task_preview": task_goal[:100],
    }


# ═══════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="墨家军 Phase2 收尾工具")
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("context", help="生成四层分级加载的上下文")
    
    p_scan = sub.add_parser("scan", help="安全扫描")
    p_scan.add_argument("--text", default=None, help="要扫描的文本(默认git diff --cached)")
    
    p_delegate = sub.add_parser("delegate", help="校验delegate范围")
    p_delegate.add_argument("--goal", required=True, help="子代理任务描述")
    p_delegate.add_argument("--scope", required=True, help="允许范围(逗号分隔)")
    
    args = parser.parse_args()
    
    if args.cmd == "context":
        ctx = get_layer_context()
        print(f"四层加载上下文: {len(ctx)} 字符")
        print(ctx[:1000])
    elif args.cmd == "scan":
        passed, findings = security_scan(args.text)
        print(security_report(findings))
    elif args.cmd == "delegate":
        scope = [s.strip() for s in args.scope.split(",")]
        result = validate_delegate_scope(args.goal, scope)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
