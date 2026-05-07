#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
墨家军 Agent 能力名片系统

给8个Agent每人一张"能力名片"，结构化描述：
- 我是谁（name, role, description）
- 我能干嘛（intent_keywords, task_types）
- 我吃什么吐什么（input_formats, output_formats）
- 我挂了找谁（backup）

核心函数：
- route_by_intent()   → 根据自然语言意图找Agent
- get_task_agent()    → 根据task_type反查Agent
- validate_cards()    → 校验名片完整性
- get_backup_agent()  → 获取替补Agent

用法：
    from agent_cards import route_by_intent, get_agent_card
    agent = route_by_intent("帮我分析天青浅的笔记表现")
    # → "moyuan"
"""

from typing import Optional

# ============================================================
# Agent 能力名片定义
# ============================================================

AGENT_CARDS: dict = {
    "moyuan": {
        "name": "墨渊",
        "role": "数据科学家",
        "description": "分析采集数据、运行学习循环、维护洞察引擎",
        "intent_keywords": ["分析", "评估", "表现", "对比", "数据", "洞察", "报告", "趋势", "诊断"],
        "input_formats": ["SQL查询结果", "数据表名", "分析需求描述"],
        "output_formats": ["分析报告", "洞察摘要", "策略建议", "数据可视化"],
        "task_types": [
            "sample_analysis", "data_analysis", "v2_insight", "dual_cycle",
            "code_reviewer", "heartbeat_reporter", "personality_report",
            "glm_ocr", "glm_vision", "add_watermark",
            "breaker_stats", "plugin_list", "metrics_report", "config_get",
            "v2_learning_cycle",
        ],
        "backup": "mocheng",
    },
    "molan": {
        "name": "墨蓝",
        "role": "内容创作者",
        "description": "基于双轨洞察创作小红书笔记，维护标题库，产出真实有调侃感的内容",
        "intent_keywords": ["写", "创作", "笔记", "文案", "内容", "标题", "发", "帖子"],
        "input_formats": ["策略brief", "主题关键词", "产品信息", "双轨洞察"],
        "output_formats": ["小红书笔记", "标题候选", "正文草稿", "话题标签"],
        "task_types": [
            "xiaohongshu_note", "v2_story_note",
            "log_collector", "xiaohongshu_publish",
        ],
        "backup": "mochuang",
    },
    "moqing": {
        "name": "墨青",
        "role": "视觉设计师",
        "description": "封面方案设计、AI图片生成（MJ/FLUX/Kolors）、风格指南匹配",
        "intent_keywords": ["图", "封面", "生成图", "画", "配图", "视觉", "设计", "MJ", "生图"],
        "input_formats": ["画面需求描述", "风格参考", "尺寸比例"],
        "output_formats": ["MJ Prompt", "生成图片URL", "封面方案"],
        "task_types": [
            "image_generator", "image_processor",
            "gen_image", "gen_image_mj", "gen_image_flux",
            "gen_image_crun", "gen_image_kolors", "gen_ideogram",
            "gen_video", "img_to_img", "make_cover",
            "tavily_search", "mojiajun_collect",
            "v2_cover_plan",
        ],
        "backup": "mohong",
    },
    "mohong": {
        "name": "墨红",
        "role": "质检员",
        "description": "产出质量审核、风格一致性检查、发布前把关、红线检查",
        "intent_keywords": ["审核", "检查", "质检", "把关", "验证", "审计", "红线"],
        "input_formats": ["待审核内容", "风格指南", "发布红线规则"],
        "output_formats": ["审核结果", "修改建议", "通过/驳回标记"],
        "task_types": [
            "quality_audit", "pre_publish_check", "build_style_library",
            "style_audit", "task_retry_engine",
            "tool_registry", "aiohttp_request", "aiohttp_batch", "aiohttp_health",
        ],
        "backup": "mozi",
    },
    "mochuang": {
        "name": "墨创",
        "role": "策略参谋",
        "description": "内容日历规划、系列策划、发布节奏管理",
        "intent_keywords": ["策略", "规划", "日历", "排期", "计划", "系列", "节奏", "方案"],
        "input_formats": ["品牌目标", "历史数据", "时间范围"],
        "output_formats": ["内容日历", "系列策划", "发布排期"],
        "task_types": [
            "strategy_plan", "publish_schedule", "content_planner",
            "report_generator",
        ],
        "backup": "molan",
    },
    "mocheng": {
        "name": "墨橙",
        "role": "反馈协调员",
        "description": "数据采集同步、外部数据导入、反馈录入、每日摘要",
        "intent_keywords": ["采集", "收集", "同步", "导入", "抓取", "反馈", "摘要", "汇总", "爬"],
        "input_formats": ["数据源URL", "采集任务描述", "表名"],
        "output_formats": ["采集数据", "每日摘要", "同步状态"],
        "task_types": [
            "data_check", "data_collector", "feedback_sync", "daily_summary",
            "queue_health",
            "crawl4ai_crawl", "crawl4ai_extract",
            "scrapling_parse", "scrapling_fetch", "scrapling_batch",
            "book_insight", "book_match",
        ],
        "backup": "moyuan",
    },
    "mozi": {
        "name": "墨子",
        "role": "仪表盘",
        "description": "学习进度展示、报告可视化、趋势图生成",
        "intent_keywords": ["看板", "仪表盘", "可视化", "进度", "展示", "图表", "报告汇总"],
        "input_formats": ["统计数据", "时间范围"],
        "output_formats": ["HTML看板", "趋势图", "汇总报告"],
        "task_types": [
            "dashboard_report", "dashboard_generator", "report_assembler",
        ],
        "backup": "mohong",
    },
    "mojin": {
        "name": "墨金",
        "role": "创新引擎",
        "description": "新热点发现、兴趣缺口探查、反套路内容驱动",
        "intent_keywords": ["热点", "趋势", "创新", "挖掘", "新方向", "风口", "缺口"],
        "input_formats": ["话题关键词", "数据源"],
        "output_formats": ["热点报告", "缺口分析", "创新建议"],
        "task_types": [
            "topic_miner", "trend_mining",
            "sync_agent_tags", "camoufox_fetch", "camoufox_screenshot",
        ],
        "backup": "mochuang",
    },
}


# ============================================================
# 核心函数
# ============================================================

def route_by_intent(user_message: str) -> Optional[str]:
    """
    根据用户消息里的关键词匹配Agent。

    遍历所有Agent的intent_keywords，统计命中数，
    返回命中数最多的agent_id。如果没有命中任何关键词，返回None。

    Args:
        user_message: 用户的自然语言消息，如"帮我分析天青浅的笔记表现"

    Returns:
        匹配的agent_id，或None

    Example:
        >>> route_by_intent("帮我分析数据")
        'moyuan'
        >>> route_by_intent("写一篇陶瓷笔记")
        'molan'
        >>> route_by_intent("今天天气不错")
        None
    """
    msg_lower = user_message.lower()
    scores: dict[str, int] = {}

    for agent_id, card in AGENT_CARDS.items():
        keywords = card["intent_keywords"]
        # 加权匹配：排前面的关键词权重更高（第1个权重=len，最后1个=1）
        weight = 0
        for i, kw in enumerate(keywords):
            if kw in msg_lower:
                weight += len(keywords) - i  # 第1个权重最高
        if weight > 0:
            scores[agent_id] = weight

    if not scores:
        return None

    # 排序：优先第一个匹配位置靠前的（"审核"比"笔记"更有辨识度），
    # 同位置时加权分高的胜出
    def sort_key(agent_id: str) -> tuple:
        keywords = AGENT_CARDS[agent_id]["intent_keywords"]
        first_match_pos = min(
            (i for i, kw in enumerate(keywords) if kw in msg_lower),
            default=len(keywords),
        )
        # 位置越小越好 → 取负，分数越高越好 → 取正
        return (-first_match_pos, scores[agent_id])

    return max(scores, key=sort_key)


def get_agent_card(agent_id: str) -> Optional[dict]:
    """
    根据agent_id返回对应名片。

    Args:
        agent_id: Agent的ID，如"moyuan"

    Returns:
        名片字典，找不到返回None
    """
    return AGENT_CARDS.get(agent_id)


def list_all_agents() -> list[dict]:
    """
    返回所有Agent的摘要列表。

    Returns:
        每个Agent的id、name、role、description
    """
    return [
        {
            "agent_id": aid,
            "name": card["name"],
            "role": card["role"],
            "description": card["description"],
        }
        for aid, card in AGENT_CARDS.items()
    ]


def get_task_agent(task_type: str) -> Optional[str]:
    """
    根据task_type反查应该派给哪个Agent。

    Args:
        task_type: 任务类型，如"sample_analysis"

    Returns:
        agent_id，找不到返回None
    """
    for agent_id, card in AGENT_CARDS.items():
        if task_type in card["task_types"]:
            return agent_id
    return None


def get_backup_agent(agent_id: str) -> Optional[str]:
    """
    返回指定Agent的替补Agent id。

    Args:
        agent_id: Agent的ID

    Returns:
        替补Agent的ID，找不到返回None
    """
    card = AGENT_CARDS.get(agent_id)
    if card:
        return card.get("backup")
    return None


def validate_cards() -> dict:
    """
    校验所有名片数据的完整性和一致性。

    检查项：
    1. 每个Agent是否有name/role/description
    2. 每个Agent的task_types是否非空
    3. backup指向的Agent是否存在
    4. 没有重复的agent_id（字典天然保证）

    Returns:
        {'valid': bool, 'issues': list[str]}
    """
    issues: list[str] = []
    required_fields = ["name", "role", "description"]

    for agent_id, card in AGENT_CARDS.items():
        # 检查必填字段
        for field in required_fields:
            if field not in card or not card[field]:
                issues.append(f"{agent_id}: 缺少必填字段 '{field}'")

        # 检查task_types非空
        if "task_types" not in card or len(card["task_types"]) == 0:
            issues.append(f"{agent_id}: task_types 为空")

        # 检查backup存在性
        backup = card.get("backup")
        if backup and backup not in AGENT_CARDS:
            issues.append(f"{agent_id}: backup '{backup}' 不存在于名片中")

        # 检查intent_keywords非空
        if "intent_keywords" not in card or len(card["intent_keywords"]) == 0:
            issues.append(f"{agent_id}: intent_keywords 为空")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


# ============================================================
# 自测
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("墨家军 Agent 能力名片 — 自测")
    print("=" * 60)

    # 1. 测试 route_by_intent
    print("\n[1] route_by_intent 测试")
    tests = [
        ("帮我分析天青浅4篇笔记的表现", "moyuan"),
        ("写一篇关于景德镇冷粉的笔记", "molan"),
        ("生成一张松鼠杯的封面图", "moqing"),
        ("审核一下这篇笔记能不能发", "mohong"),
        ("规划下周的内容发布日历", "mochuang"),
        ("采集小红书上的爆款数据", "mocheng"),
        ("生成一个学习进度看板", "mozi"),
        ("挖掘最近的陶瓷话题热点", "mojin"),
        ("今天天气不错", None),  # 无匹配
    ]
    all_pass = True
    for msg, expected in tests:
        result = route_by_intent(msg)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_pass = False
        print(f"  {status} '{msg[:30]}...' → {result} (期望: {expected})")

    # 2. 测试 get_agent_card
    print("\n[2] get_agent_card 测试")
    card = get_agent_card("moyuan")
    print(f"  moyuan → {card['name']} ({card['role']})")
    assert card["name"] == "墨渊"
    assert get_agent_card("nonexistent") is None
    print("  ✅ 通过")

    # 3. 测试 list_all_agents
    print("\n[3] list_all_agents 测试")
    agents = list_all_agents()
    print(f"  共 {len(agents)} 个Agent:")
    for a in agents:
        print(f"    {a['agent_id']}: {a['name']} - {a['role']}")
    assert len(agents) == 8
    print("  ✅ 通过")

    # 4. 测试 get_task_agent
    print("\n[4] get_task_agent 测试")
    assert get_task_agent("sample_analysis") == "moyuan"
    assert get_task_agent("xiaohongshu_note") == "molan"
    assert get_task_agent("gen_image_mj") == "moqing"
    assert get_task_agent("nonexistent_task") is None
    print("  ✅ 通过")

    # 5. 测试 get_backup_agent
    print("\n[5] get_backup_agent 测试")
    assert get_backup_agent("moyuan") == "mocheng"
    assert get_backup_agent("molan") == "mochuang"
    assert get_backup_agent("nonexistent") is None
    print("  ✅ 通过")

    # 6. 测试 validate_cards
    print("\n[6] validate_cards 测试")
    result = validate_cards()
    if result["valid"]:
        print("  ✅ 所有名片校验通过，无问题")
    else:
        print(f"  ❌ 发现问题: {result['issues']}")

    # 汇总
    print("\n" + "=" * 60)
    if all_pass and result["valid"]:
        print("🎉 全部测试通过！Agent能力名片系统就绪。")
    else:
        print("⚠️  存在失败项，请检查。")
    print("=" * 60)
