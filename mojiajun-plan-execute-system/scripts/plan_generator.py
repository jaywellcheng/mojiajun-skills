#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plan Generator - Plan-and-Execute 计划生成器

在小川本地运行，当大威下达分析/创作任务时：
1. 小川调这个模块出一份计划
2. 把计划发给大威确认
3. 大威确认后，小川再派任务到task_queue

用法：
    from plan_generator import generate_plan, PLAN_TEMPLATE
    plan = generate_plan("分析天青浅4篇笔记表现")
    print(plan)
"""

from datetime import datetime

# ============================================================
# 分析框架模板 - 针对不同类型的任务
# ============================================================

ANALYSIS_TEMPLATES = {
    "笔记分析": {
        "steps": [
            "提取目标笔记的互动数据（点赞/收藏/评论/曝光）— 先摸清基础表现",
            "提取笔记的标题结构、正文风格、标签组合 — 对比分析差异点",
            "从xhs_sample_library取同类低粉爆款做横向对比 — 看差距在哪",
            "关联双轨洞察中的历史结论 — 避免重复分析",
            "输出优化建议 — 告诉大威下一轮笔记怎么改",
        ],
        "data_sources": [
            "xhs_sample_library（天青浅笔记+低粉爆款对比）",
            "双轨洞察中的术轨道分析结果",
        ],
    },
    "内容创作": {
        "steps": [
            "回顾历史笔记的数据和用户反馈 — 提炼什么风格被喜欢",
            "从知识库提取素材（美食/文化/工艺等）",
            "用标题库公式组合标题 — 至少3个候选",
            "创作正文（真人口吻+调侃感，不用煽情词）",
            "自检：是否符合发布红线、风格指南、负面清单",
        ],
        "data_sources": [
            "双轨洞察中的术轨道结果（标题公式/风格指南）",
            "双轨洞察中的道轨道结果（书籍精华）",
            "shared/training/目录下的风格指南和标题库",
        ],
    },
    "策略规划": {
        "steps": [
            "从MySQL查相关数据，了解当前状态",
            "提取历史分析中的关键结论 — 避免重复造轮子",
            "结合双轨洞察中的道轨道指导方向",
            "制定可执行的下一步计划（3-5条具体行动）",
            "标明每个行动的执行人和预估耗时",
        ],
        "data_sources": [
            "MySQL各数据表的最新数据",
            "双轨洞察中的历史分析结论",
            "核心知识库中的策略资料",
        ],
    },
}


def generate_plan(task_name: str, task_type: str = "分析",
                  task_description: str = "",
                  custom_steps: list[str] = None) -> str:
    """
    生成一份Plan-and-Execute计划。
    
    Args:
        task_name: 任务名称，如"天青浅4篇笔记表现分析"
        task_type: 任务类型，可选"笔记分析"/"内容创作"/"策略规划"
        task_description: 任务描述，一句话说清楚要做什么
        custom_steps: 自定义步骤，覆盖模板
    
    Returns:
        str: Markdown格式的计划
        
    Example:
        plan = generate_plan(
            task_name="天青浅4篇笔记表现分析",
            task_type="笔记分析",
            task_description="评估4篇笔记表现差异，找出爆款原因和失败原因"
        )
    """
    # 找到匹配的模板
    template = None
    for key, val in ANALYSIS_TEMPLATES.items():
        if key in task_type or task_type in key:
            template = val
            break
    if template is None:
        # 默认用笔记分析模板
        template = ANALYSIS_TEMPLATES["笔记分析"]

    steps = custom_steps if custom_steps else template["steps"]
    data_sources = template["data_sources"]

    # 构建计划
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = []
    lines.append(f"## 执行计划")
    lines.append("")
    lines.append(f"**生成时间**：{now}")
    lines.append(f"**任务名称**：{task_name}")
    lines.append("")
    if task_description:
        lines.append(f"**任务目标**：{task_description}")
        lines.append("")
    
    lines.append("**分析框架**：")
    for i, step in enumerate(steps, 1):
        lines.append(f"  step {i}. {step}")
    lines.append("")
    
    lines.append("**数据需求**：")
    for ds in data_sources:
        lines.append(f"  - {ds}")
    lines.append("")
    
    lines.append("**预估耗时**：约 15-25 分钟")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*请大威确认方向后再开干 ✅*")
    
    return "\n".join(lines)


# ============================================================
# 快捷入口 - 大威布置任务时直接调用
# ============================================================

def quick_plan(task_name: str, task_description: str = "",
               custom_steps: list[str] = None) -> str:
    """
    快捷生成计划 - 自动根据任务名称判断类型。
    """
    tn_lower = task_name.lower()
    if "创作" in task_name or "写" in task_name or "产" in task_name:
        task_type = "内容创作"
    elif "分析" in task_name or "评估" in task_name or "表现" in tn_lower:
        task_type = "笔记分析"
    elif "策略" in task_name or "规划" in task_name:
        task_type = "策略规划"
    else:
        task_type = "笔记分析"
    
    return generate_plan(task_name, task_type, task_description, custom_steps)


# ============================================================
# Phase 2 新增：自动判断 + 子任务拆分
# ============================================================

def needs_plan(task_name: str) -> bool:
    """
    判断任务是否需要生成执行计划。

    需要 Plan：分析、创作、策略类任务
    不需要 Plan：运维修复、工具配置、简单查询

    Args:
        task_name: 任务名称，如"分析天青浅笔记表现"

    Returns:
        True=需要生成计划，False=直接执行

    Examples:
        >>> needs_plan("帮我分析数据")
        True
        >>> needs_plan("重启一下worker")
        False
        >>> needs_plan("查一下task_queue状态")
        False
    """
    SKIP_KEYWORDS = [
        "重启", "装包", "安装", "配置工具", "查一下",
        "看下", "状态", "连接", "测试连通",
    ]
    PLAN_KEYWORDS = [
        "分析", "写", "创作", "策略", "规划", "方案",
        "评估", "报告", "笔记", "内容", "发布",
    ]

    tn_lower = task_name.lower()

    # 跳过关键词优先判断
    for kw in SKIP_KEYWORDS:
        if kw in tn_lower:
            return False

    for kw in PLAN_KEYWORDS:
        if kw in tn_lower:
            return True

    # 默认不需要计划
    return False


def plan_to_subtasks(
    plan_steps: list[str],
    task_name: str = "",
) -> list[dict]:
    """
    将计划的每个 step 拆成一个 task_queue 子任务。

    路由逻辑使用 agent_cards.py 的 get_task_agent() 自动匹配。

    Args:
        plan_steps: 步骤描述列表，如 [
            "提取目标笔记的互动数据",
            "对比分析标题结构和正文风格",
            "输出优化建议",
        ]
        task_name: 原始任务名（用于日志）

    Returns:
        子任务列表，每个格式：
        {
            "step": "步骤描述",
            "target_agent": "moyuan",
            "task_type": "data_analysis",
            "payload": {"description": "...", "task_name": "..."},
        }

    Example:
        >>> subtasks = plan_to_subtasks(
        ...     ["提取笔记互动数据", "对比分析标题", "输出优化建议"],
        ...     "天青浅笔记表现分析"
        ... )
        >>> len(subtasks)
        3
    """
    try:
        from agent_cards import get_task_agent
    except ImportError:
        # fallback：手动映射
        def get_task_agent(task_type):
            mapping = {
                "data_analysis": "moyuan",
                "sample_analysis": "moyuan",
                "v2_insight": "moyuan",
                "dual_cycle": "moyuan",
                "xiaohongshu_note": "molan",
                "v2_story_note": "molan",
                "quality_audit": "mohong",
                "pre_publish_check": "mohong",
                "strategy_plan": "mochuang",
                "content_planner": "mochuang",
                "data_check": "mocheng",
                "dashboard_report": "mozi",
            }
            return mapping.get(task_type)

    # 步骤类型推断规则
    def infer_task_type(step: str) -> str:
        step_lower = step.lower()
        if any(kw in step_lower for kw in ["数据", "提取", "查询", "统计"]):
            return "data_analysis"
        if any(kw in step_lower for kw in ["对比", "差异", "横向"]):
            return "sample_analysis"
        if any(kw in step_lower for kw in ["洞察", "学习", "双轨"]):
            return "dual_cycle"
        if any(kw in step_lower for kw in ["创作", "写", "标题", "正文", "笔记"]):
            return "xiaohongshu_note"
        if any(kw in step_lower for kw in ["审核", "检查", "质检", "红线"]):
            return "quality_audit"
        if any(kw in step_lower for kw in ["策略", "规划", "日历", "排期"]):
            return "strategy_plan"
        if any(kw in step_lower for kw in ["采集", "收集", "同步", "导入"]):
            return "data_check"
        if any(kw in step_lower for kw in ["看板", "可视化", "展示"]):
            return "dashboard_report"
        if any(kw in step_lower for kw in ["生图", "封面", "配图", "MJ"]):
            return "gen_image"
        # 默认数据分析
        return "data_analysis"

    subtasks = []
    for i, step in enumerate(plan_steps):
        task_type = infer_task_type(step)
        target_agent = get_task_agent(task_type) if get_task_agent else "moyuan"

        subtasks.append({
            "step": step,
            "target_agent": target_agent,
            "task_type": task_type,
            "payload": {
                "description": step,
                "task_name": task_name,
                "step_index": i + 1,
                "total_steps": len(plan_steps),
            },
            "priority": 2,  # Plan-and-Execute 子任务默认优先级2
        })

    return subtasks


if __name__ == "__main__":
    # ======== 新功能测试 ========
    print("=" * 60)
    print("plan_generator v2 — 自测")
    print("=" * 60)

    # 1. needs_plan 测试
    print("\n[1] needs_plan 测试")
    tests = [
        ("帮我分析天青浅笔记表现", True),
        ("写一篇陶瓷笔记", True),
        ("规划下周内容发布日历", True),
        ("重启一下worker进程", False),
        ("查一下task_queue状态", False),
        ("装个pandas包", False),
    ]
    all_pass = True
    for msg, expected in tests:
        result = needs_plan(msg)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_pass = False
        print(f"  {status} '{msg[:30]}' → {result} (期望: {expected})")

    # 2. 计划生成测试
    print("\n[2] generate_plan 测试")
    plan = quick_plan(
        "天青浅4篇笔记表现分析",
        "评估发布的4篇小红书笔记的流量表现差异"
    )
    print(plan)

    # 3. plan_to_subtasks 测试
    print("\n[3] plan_to_subtasks 测试")
    steps = [
        "提取目标笔记的互动数据",
        "对比分析标题结构和正文风格差异",
        "输出优化建议和下一步行动",
    ]
    subtasks = plan_to_subtasks(steps, "天青浅笔记表现分析")
    for st in subtasks:
        print(f"  → {st['target_agent']}/{st['task_type']}: {st['step'][:40]}")
    assert len(subtasks) == 3
    print(f"  ✅ 拆出 {len(subtasks)} 个子任务")

    print("\n" + "=" * 60)
    if all_pass:
        print("🎉 全部测试通过！plan_generator v2 就绪。")
    else:
        print("⚠️  部分测试失败，请检查。")
    print("=" * 60)
