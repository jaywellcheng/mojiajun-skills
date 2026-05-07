---
name: mojiajun-cost-tracker
description: 墨家军API费用追踪 — 按引擎/日/月统计AI调用费用，支持记录、汇总、明细查询
version: 1.0.0
tags: [mojiajun, cost-tracker, api-cost, billing]
---

# 墨家军 cost-tracker API费用追踪

## 概述

追踪墨家军各AI引擎的API调用费用。写入MySQL `mojiajun.api_costs` 表。

## 引擎单价

| 引擎 | 单价 (USD/次) |
|------|:---:|
| mj (Midjourney) | $0.035 |
| tt_api | $0.035 |
| gpt | $0.02 |
| crun | $0.02 |
| siliconflow | $0.01 |
| flux / fal | $0.008 |

## 统计维度

| 维度 | 函数 | 说明 |
|------|------|------|
| 单次 | `record()` | 记录一次API调用 |
| 日 | `daily_summary(date)` | 按engine分组：调用次数、总费用、图片数 |
| 月 | `total_summary(days=30)` | 同上，按费用降序 |
| 明细 | `recent(N)` | 最近N条原始记录 |

## 关键函数

| 函数 | 作用 |
|------|------|
| `record(engine, cost, images, note)` | 记账 |
| `daily_summary(date)` | 日汇总 |
| `total_summary(days)` | 月汇总 |
| `backfill_0428()` | 特殊：扫描图片文件名反推引擎，补录历史费用 |

## 使用示例

```python
from api_cost_tracker import record, daily_summary, total_summary

record("mj", 0.035, 4, "松鼠杯4格漫画")
summary = daily_summary("2026-04-28")
# {"mj": {"calls": 5, "total_cost": 0.175, "images": 20}, ...}
```

## 闭环费用分析方法论

### 数据来源（两类）
1. **task_queue 表** — Agent任务走队列，有 cost_cny 字段，直接查
2. **代码推算** — autoDream/extractMemories 直调DeepSeek不走队列，从代码中读 prompt 结构+token 估算

### 查询模板

```bash
# 按天汇总所有任务费用
docker exec -i ceramic-mysql mysql -u root -pceramic_2026 \
  --default-character-set=utf8mb4 mojiajun -e "
SELECT DATE(created_at) as day, COUNT(*) as tasks, 
       ROUND(SUM(cost_cny),2) as total_cost,
       ROUND(AVG(cost_cny),2) as avg_cost
FROM task_queue 
WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY day ORDER BY day;
"

# 最近N条明细
SELECT id, task_type, target_agent, cost_cny, created_at
FROM task_queue ORDER BY id DESC LIMIT 30;
```

### Token 估算公式（DeepSeek chat）
- 输入：字符数/2 ≈ token 数，¥0.001/1K tokens
- 输出：输出长度/1.5 ≈ token 数，¥0.002/1K tokens
- 典型 autoDream：5K in + 1.5K out ≈ ¥0.008/次
- 典型 extractMemories：4K in + 1.5K out ≈ ¥0.007/次
- Agent 多轮任务（读库→分析→写结果）：¥0.21-0.61/次

### 闭环日费构成
```
autoDream(4次×¥0.008) + extractMemories(6次×¥0.007) + orchestrator派发(1轮×¥1.43)
= ¥0.032 + ¥0.042 + ¥1.43
= ¥1.50/天 → ¥45/月（仅闭环核心）
```

实际全天含墨青出图等：月费约 ¥120。

## 代码位置

CORE-01: `/home/ubuntu/mojiajun-queue/agent_outputs/mohong/api_cost_tracker.py` (129行)
