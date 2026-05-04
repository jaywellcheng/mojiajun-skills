---
name: mojiajun-agent-capability-cards
description: 墨家军8个Agent的能力名片系统——结构化描述每个Agent的能力、输入输出、关键词路由和替补机制。包含agent_cards.py和智能路由函数。
version: 1.0.0
tags:
  - mojiajun
  - agent-architecture
  - task-routing
  - capability-discovery
---

# 墨家军 Agent 能力名片系统

## 概述

给8个Agent每人一张结构化"能力名片"（Agent Card），解决三个问题：
1. **智能路由**：大威说"帮我分析数据" → 自动找到墨渊
2. **任务反查**：给定task_type → 自动找到对应Agent
3. **替补机制**：Agent宕机 → 自动找到backup

## 文件位置

```
小川本地: /Users/jaywell/Desktop/墨家军资料库/05_模块代码/小川本地/agent_cards.py
CORE-01:  无需部署（纯小川本地工具）
```

## 8个Agent名片

| Agent | 角色 | 签名关键词（第一个最重） | task_types数 | 替补 |
|-------|------|------------------------|-------------|------|
| moyuan 墨渊 | 数据科学家 | 分析、评估、表现、对比、数据 | 14 | mocheng |
| molan 墨蓝 | 内容创作者 | 写、创作、笔记、文案、内容 | 4 | mochuang |
| moqing 墨青 | 视觉设计师 | 图、封面、生成图、画、配图 | 12 | mohong |
| mohong 墨红 | 质检员 | 审核、检查、质检、把关、验证 | 9 | mozi |
| mochuang 墨创 | 策略参谋 | 策略、规划、日历、排期、计划 | 3 | molan |
| mocheng 墨橙 | 反馈协调员 | 采集、收集、同步、导入、抓取 | 10 | moyuan |
| mozi 墨子 | 仪表盘 | 看板、仪表盘、可视化、进度 | 3 | mohong |
| mojin 墨金 | 创新引擎 | 热点、趋势、创新、挖掘 | 5 | mochuang |

## 核心函数

### route_by_intent(user_message: str) -> str | None

根据自然语言意图自动路由到对应Agent。

算法：加权匹配 + 首位优先。
- 关键词在列表中的位置越靠前权重越高（第1个权重=len，最后1个=1）
- 多个Agent竞争时，**优先第一个匹配关键词位置更靠前的**（"审核"比"笔记"更有辨识度）

```python
from agent_cards import route_by_intent

route_by_intent("帮我分析天青浅笔记表现")  # → "moyuan"
route_by_intent("写一篇陶瓷笔记")          # → "molan"
route_by_intent("生成松鼠杯封面图")        # → "moqing"
route_by_intent("审核这篇笔记")            # → "mohong"
route_by_intent("今天天气不错")            # → None
```

### get_task_agent(task_type: str) -> str | None

根据task_type反查Agent：

```python
get_task_agent("sample_analysis")    # → "moyuan"
get_task_agent("gen_image_mj")       # → "moqing"
```

### get_backup_agent(agent_id: str) -> str | None

获取替补Agent：

```python
get_backup_agent("moyuan")  # → "mocheng"
get_backup_agent("molan")   # → "mochuang"
```

### validate_cards() -> dict

校验所有名片的完整性和一致性。返回 `{"valid": bool, "issues": list}`。

## 使用场景

### 场景1：大威下任务时自动路由

```python
agent = route_by_intent(user_message)
if agent:
    card = get_agent_card(agent)
    print(f"→ 派给 {card['name']}({card['role']})")
else:
    print("→ 无法自动判断，需人工确认")
```

### 场景2：Plan-and-Execute 子任务自动派发

```python
for step in plan_steps:
    task_type = infer_task_type(step)       # 根据步骤推断task_type
    agent = get_task_agent(task_type)       # 反查Agent
    dispatch(agent, task_type, payload)     # 入队
```

### 场景3：故障切换

```python
backup = get_backup_agent(failed_agent)
if backup:
    dispatch(backup, task_type, payload)
```

## 与 CORE-01 的关系

- agent_cards.py 的 task_types 字段必须与 CORE-01 module_dispatcher.py 的 TASK_MODULE_MAP 保持同步
- `validate_cards()` 会检查一致性
- 新增Agent时：先在 CORE-01 注册模块 → 再更新 agent_cards.py

## 后续升级方向（小墨建议）

当前纯关键词匹配，Agent多了可能有歧义。后续可升级为：
- 语义向量匹配（用Embedding计算意图相似度）
- 混合路由（关键词快速过滤 + 语义精确匹配）

现阶段8个Agent的关键词区分度足够。

## 备份

agent_cards.py 已纳入小川数据备份范围，位置：
```
/Users/jaywell/Desktop/墨家军资料库/05_模块代码/小川本地/agent_cards.py
```
Mac重建后从此路径恢复即可。
