---
name: mojiajun-plan-execute-system
description: 墨家军Plan-and-Execute完整系统——包含Agent能力名片、智能计划生成、子任务拆分、批量派发四大模块。Mac重建后从此技能恢复全部功能。
version: 2.0.0
tags:
  - mojiajun
  - plan-execute
  - task-routing
  - task-batching
---

# 墨家军 Plan-and-Execute 完整系统 v2

## 概述

将大威下任务→执行的全流程自动化：
1. **Agent能力名片** → 智能路由：大威说"分析数据"自动找墨渊
2. **Plan生成器** → 自动出计划：分析/创作/策略任务自动生成执行框架
3. **子任务拆分** → 计划确认后自动拆成task_queue子任务
4. **批量派发** → 通过SSH写入CORE-01，串行/并行可选

## 文件清单

| 文件 | 用途 | 位置 |
|------|------|------|
| agent_cards.py | Agent能力名片+智能路由 | 小川本地 |
| plan_generator.py | 计划生成+子任务拆分 | 小川本地 |
| task_batcher.py | 批量派发+轮询等待 | 小川本地 |

## 完整流程

```
大威下任务
  → [agent_cards.route_by_intent] 自动识别意图
  → [plan_generator.needs_plan] 判断是否需要计划
      ├─ 不需要（运维/查询）→ 直接执行
      └─ 需要（分析/创作/策略）
          → [plan_generator.quick_plan] 生成计划
          → 展示给大威确认
          → 大威确认/调整
          → [plan_generator.plan_to_subtasks] 拆分子任务
          → [task_batcher.batch_dispatch] 批量写入CORE-01
          → 轮询等待结果 → 汇总给大威
```

## 使用示例

```python
from plan_generator import needs_plan, quick_plan, plan_to_subtasks
from task_batcher import batch_dispatch
from agent_cards import route_by_intent

# 大威说：
user_task = "帮我分析天青浅4篇笔记的表现差异"

# 1. 判断是否需要Plan
if needs_plan(user_task):
    # 2. 生成计划
    plan = quick_plan(user_task, "评估表现差异，找原因")
    print(plan)  # 展示给大威
    
    # 3. 大威确认后，拆子任务
    # （实际步骤从plan中提取，这里简化）
    steps = [
        "提取目标笔记的互动数据",
        "对比分析标题结构和风格差异",
        "关联双轨洞察中的历史结论",
        "输出优化建议",
    ]
    subtasks = plan_to_subtasks(steps, user_task)
    
    # 4. 批量派发
    result = batch_dispatch(subtasks, serial=True)
    print(f"完成: {result['completed']}/{result['dispatched']}")
```

## Agent名片路由规则

| 用户说了什么 | 路由到 | 原因 |
|-------------|--------|------|
| "帮我分析数据" | moyuan(墨渊) | 分析=墨渊第1关键词 |
| "写一篇笔记" | molan(墨蓝) | 写=墨蓝第1关键词 |
| "审核这篇" | mohong(墨红) | 审核=墨红第1关键词 |
| "规划内容日历" | mochuang(墨创) | 规划=墨创第1关键词 |
| "采集爆款数据" | mocheng(墨橙) | 采集=墨橙第1关键词 |

## 子任务类型推断规则

| 步骤关键词 | task_type | Agent |
|-----------|-----------|-------|
| 数据/提取/查询/统计 | data_analysis | moyuan |
| 对比/差异/横向 | sample_analysis | moyuan |
| 洞察/学习/双轨 | dual_cycle | moyuan |
| 创作/写/标题/正文/笔记 | xiaohongshu_note | molan |
| 审核/检查/质检/红线 | quality_audit | mohong |
| 策略/规划/日历/排期 | strategy_plan | mochuang |
| 采集/收集/同步/导入 | data_check | mocheng |
| 生图/封面/配图/MJ | gen_image | moqing |

## 串行vs并行

- **串行（默认）**：前一个子任务completed后才入下一个。适合有依赖关系的步骤（分析→对比→输出）
- **并行**：所有子任务同时入队。适合无依赖的独立步骤（同时采集多个数据源）

## 安全边界

1. 大威确认环节**不进入自动化流水线**——永远锁在小川本地
2. task_batcher 通过SSH操作CORE-01，不暴露MySQL端口
3. 所有SQL使用shlex.quote()防注入
4. 运维/查询类任务跳过Plan直接执行

## 备份恢复

Mac重建后恢复步骤：
1. 恢复 `墨家军资料库/05_模块代码/小川本地/` 目录
2. `hermes skills install mojiajun-plan-execute-system`
3. 验证：`cd 小川本地 && python3 plan_generator.py && python3 task_batcher.py`

## 依赖

- Python 3.10+
- SSH 到 CORE-01 (159.75.12.11)
- CORE-01 MySQL (task_queue表)
- agent_cards.py（已包含在技能中）
