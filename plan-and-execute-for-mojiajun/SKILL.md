---
name: plan-and-execute-for-mojiajun
description: 【已升级到v2】墨家军Plan-and-Execute流程。v1版（手动出计划）已废弃，请使用 mojiajun-plan-execute-system 技能。v2新增：Agent能力名片自动路由、needs_plan自动判断、plan_to_subtasks自动拆分、task_batcher批量派发。
version: 1.0.0
deprecated: true
superseded_by: mojiajun-plan-execute-system
---

# 墨家军 Plan-and-Execute 流程

## 问题场景

大威布置分析/创作任务后，Agent直接开干。可能出现：
- 方向偏了，做了无用功
- 做的内容和大威想的不是一回事
- 改来改去，浪费时间

## 核心原则

**需要人工确认的环节，不要放在自动化流水线里。**

Agent走task_queue是异步无人值守的，但"大威确认计划"需要交互。所以Plan步骤不走CORE-01的worker代码，而是在小川本地完成。

## 流程

```
大威下任务
  → 小川调 plan_generator.py 出一份计划（Markdown格式）
  → 发给大威看
  → 大威确认 / 调整
  → 小川派正式任务到 task_queue
```

## plan_generator.py 用法

文件位置：`/Users/jaywell/Desktop/墨家军资料库/05_模块代码/小川本地/plan_generator.py`

三种模板自动匹配：

| 任务关键词 | 模板 |
|-----------|------|
| "分析"/"评估"/"表现" | 笔记分析模板（先查数据→再对比→再出建议） |
| "创作"/"写"/"产" | 内容创作模板（先回顾数据→再找素材→再写内容） |
| "策略"/"规划" | 策略规划模板（先查状态→再结合洞察→再出行动） |

### 直接调用

```python
from plan_generator import quick_plan

# 自动判断类型
plan = quick_plan(
    "天青浅4篇笔记表现分析",
    "评估发布的4篇小红书笔记的流量表现差异"
)
print(plan)
```

### 自定义步骤

```python
from plan_generator import generate_plan

plan = generate_plan(
    "松鼠杯发布策略",
    "策略规划",
    "制定50只松鼠杯的发布节奏",
    custom_steps=[
        "确认生产进度",
        "回顾已发布笔记的粉丝反馈",
        "规划预热内容",
        "制定发布当天内容组合",
        "72小时评论回复策略"
    ]
)
```

### 输出的计划格式

```
## 执行计划

**生成时间**：2026-04-27 19:33
**任务名称**：xxx

**任务目标**：xxx

**分析框架**：
  step 1. 第一步做什么 — 原因
  step 2. 第二步做什么 — 原因
  step 3. ...

**数据需求**：
  - 需要查哪些表
  - 需要结合哪些知识

**预估耗时**：约 15-25 分钟

---

*请大威确认方向后再开干 ✅*
```

## 适用场景

- 数据分析任务（大威说"帮我分析"）
- 内容创作任务（大威说"写一篇笔记"）
- 策略规划任务（大威说"搞个方案"）

## 不适用的场景（直接开干即可）

- 运维修复任务（"帮我重启XXX"）
- 工具配置任务（"帮我装个包"）
- 数据查询任务（"查一下这个表"）

## 边界规则

1. 计划长度控制在10-15行，不啰嗦
2. 必须有"请大威确认方向后再开干"这句话
3. 大威确认前不执行后续步骤
4. 大威可以调整步骤、顺序、删除/新增步骤
5. 确认后正式派发task_queue任务，不再问第二遍

## 历史经验

**设计决策**：刚开始考虑过在CORE-01的agent_worker里加Plan生成逻辑，但发现"等大威确认"在异步worker里无法实现。正确做法是把需要交互的环节留在本地，自动化流水线只跑不需要人类确认的步骤。
