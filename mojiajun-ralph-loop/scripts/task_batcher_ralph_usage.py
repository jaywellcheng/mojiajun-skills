#!/usr/bin/env python3
"""
墨家军 Task Batcher — 带 Ralph Loop 验收标准支持

与旧版区别：insert_task() 新增 acceptance_criteria 参数。
如果提供了验收标准，Agent完成时会自动验证，不达标自动重试。
"""
# (完整代码见 ~/.hermes/skills/mojiajun/mojiajun-workflow-rework-loop/scripts/task_batcher.py)
# 
# 新增参数: acceptance_criteria: Optional[dict] = None
# 格式: {"rules": [...], "require_marker": true, "max_attempts": 5}
# 
# 使用示例:
#   task_id = insert_task(
#       target_agent="molan",
#       task_type="xiaohongshu_note",
#       payload={"topic": "冷粉"},
#       acceptance_criteria={
#           "rules": [
#               {"field": "title_switches", "op": "gte", "value": 2, "desc": "标题触发≥2心理开关"},
#           ],
#           "require_marker": True,
#           "max_attempts": 5,
#       }
#   )
